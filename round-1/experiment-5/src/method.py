#!/usr/bin/env python3
"""Did instruction tuning cause the algorithm-choice collapse? (alternate 4 screen, Qwen3-8B-Base vs Qwen3-8B)

Single entry point. Every GPU phase runs as its own subprocess (vLLM and HF are never resident together).

  .venv/bin/python method.py --all          # full pipeline (resumable: finished requests / rows are skipped)
  .venv/bin/python method.py --assemble     # rebuild runs/samples.jsonl + method_out.json from results on disk
  .venv/bin/python method.py --step <name>  # one step: prompts|tests|calibrate|gate|genA|genB|label|acts|predict|genC|
                                            #           steerS|steerR|steerX|genAEXT|analysis
Outputs: method_out.json (exp_gen_sol_out schema: metadata = all analyses, datasets = per-sample rows per task).
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

from loguru import logger

WS = Path(__file__).resolve().parent
sys.path.insert(0, str(WS / "src"))
from common import (CATALOGUE, DECODING, MB, MI, PRED, RESULTS, RUNS, TASK_NAMES, read_jsonl, setup_logging,  # noqa: E402
                    sha256_file, write_jsonl)

PY = str(WS / ".venv" / "bin" / "python")
STEPS = {
    "prompts": [PY, "src/prompts.py"],
    "tests": [PY, "src/tasks.py"],
    "calibrate": [PY, "src/calibrate.py"],
    "gate": [PY, "src/labeller_gate.py"],
    "genA": [PY, "src/gen_vllm.py", "--phase", "A"],
    "genB": [PY, "src/gen_vllm.py", "--phase", "B"],
    "label": [PY, "src/label_score.py"],
    "acts": None,  # two processes, see run_step
    "predict": [PY, "src/predict_commit.py"],
    "genC": [PY, "src/gen_vllm.py", "--phase", "C"],
    "steerS": [PY, "src/steer_hf.py", "--stage", "S"],
    "steerR": [PY, "src/steer_hf.py", "--stage", "R", "--cstar", "t1=0.5,t2=0.5"],
    "steerX": [PY, "src/steer_hf.py", "--stage", "X", "--extra",
               "sharpenR:1.0:None:10;randomR:1.0:1:10;single18:0.25:None:5;single18:0.5:None:5;single18:1.0:None:5"],
    "genAEXT": [PY, "src/gen_vllm.py", "--phase", "A_EXT"],
    "steerXNC": [PY, "src/steer_hf.py", "--stage", "X", "--nocutoff", "--extra", "sharpenR:1.0:None:2"],
    "analysis": [PY, "src/analysis.py", "--second_judge"],
    "report": [PY, "src/report.py"],
}
ORDER = ["prompts", "tests", "calibrate", "gate", "genA", "genB", "label", "acts", "predict", "genC", "steerS", "label",
         "steerR", "steerX", "genAEXT", "steerXNC", "label", "analysis", "report"]


def run_step(name: str) -> None:
    logger.info(f"=== step {name}")
    if name == "acts":
        for m in ("base", "instruct"):
            subprocess.run([PY, "src/acts_hf.py", "--model", m], cwd=WS, check=True)
        return
    subprocess.run(STEPS[name], cwd=WS, check=True)


def lib_versions() -> dict:
    out = {"python": platform.python_version()}
    for mod in ("torch", "vllm", "transformers", "numpy", "scipy", "openai"):
        try:
            out[mod] = __import__(mod).__version__
        except Exception as e:  # noqa: BLE001 - version probe only
            out[mod] = f"unavailable ({type(e).__name__})"
    return out


def hardware() -> dict:
    hw = {"gpu": None, "cpu_quota": None, "ram_limit_gb": None}
    try:
        hw["gpu"] = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"],
                                   capture_output=True, text=True, timeout=20).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    try:
        q = int(Path("/sys/fs/cgroup/cpu/cpu.cfs_quota_us").read_text())
        p = int(Path("/sys/fs/cgroup/cpu/cpu.cfs_period_us").read_text())
        hw["cpu_quota"] = q / p if q > 0 else None
        hw["ram_limit_gb"] = int(Path("/sys/fs/cgroup/memory/memory.limit_in_bytes").read_text()) / 1e9
    except (OSError, ValueError):
        pass
    return hw


def clean(x):
    """Strict JSON: NaN/inf -> None, tuples -> lists, recursively."""
    import math as _m
    if isinstance(x, float):
        return None if (_m.isnan(x) or _m.isinf(x)) else x
    if isinstance(x, dict):
        return {str(k): clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [clean(v) for v in x]
    return x


def gpu_cost() -> dict:
    """GPU time from time_log.json: sum of per-phase reported seconds and the wall-clock span of GPU phases."""
    import datetime as _dt
    tl = jload(WS / "time_log.json", []) or []
    secs = sum(float(e.get("seconds", 0) or 0) for e in tl if str(e.get("event", "")).endswith("_end"))
    ts = [_dt.datetime.strptime(e["utc"], "%Y-%m-%dT%H:%M:%SZ") for e in tl
          if any(str(e.get("event", "")).startswith(p) for p in ("gen_", "acts_", "steer_"))]
    span = (max(ts) - min(ts)).total_seconds() if ts else 0.0
    return {"gpu_hours_phase_sum": round(secs / 3600, 2), "gpu_wall_span_hours": round(span / 3600, 2),
            "gpu": "1x NVIDIA L4 23 GB"}


def jload(p: Path, default=None):
    try:
        return json.loads(p.read_text())
    except (OSError, json.JSONDecodeError):
        return default


def all_labelled() -> list[dict]:
    rows = []
    for f in sorted(RUNS.glob("labelled_*.jsonl")):
        rows.extend(read_jsonl(f))
    return rows


def shared_schema(r: dict) -> dict:
    return {"task": r["task"], "condition": r["condition"], "paraphrase_id": r["paraphrase_id"], "sample_id": r["sample_id"],
            "model": r["model"], "decoding": r.get("decoding", DECODING), "label": r.get("label"),
            "labeller_source": r.get("labeller_source"), "passed": bool(r.get("passed")), "wall_s": r.get("wall_s"),
            "code_sha256": r.get("code_sha256"), "code": r.get("code"),
            "arm": r["arm"], "template": r["template"], "steer": r.get("steer"), "prompt_id": r["prompt_id"],
            "seed": r.get("seed"), "engine": r.get("engine"), "stage": r.get("stage"), "finish_reason": r.get("finish_reason"),
            "n_tokens": r.get("n_tokens"), "parse_ok": r.get("parse_ok"), "format_ok_loose": r.get("format_ok_loose"),
            "format_ok_strict": r.get("format_ok_strict"), "refusal": r.get("refusal"), "degenerate": r.get("degenerate"),
            "chat_leak": r.get("chat_leak"), "runtime_label": r.get("runtime_label"), "ast_label": r.get("ast_label"),
            "judge_label": r.get("judge_label"), "fail_case": r.get("fail_case"), "error": r.get("error")}


def example_of(r: dict, prompt_text: str) -> dict:
    ex = {"input": prompt_text, "output": r.get("text", ""),
          "predict_algorithm_label": r.get("label") or "unparseable",
          "predict_passes_hidden_tests": "true" if r.get("passed") else "false"}
    for k, v in shared_schema(r).items():
        if k in ("code",):
            ex["metadata_program"] = v
            continue
        ex[f"metadata_{k}"] = v
    return ex


def assemble() -> None:
    from prompts import load_prompts
    prompts = load_prompts()
    rows = all_labelled()
    write_jsonl(RUNS / "samples.jsonl", [shared_schema(r) for r in rows])
    ptext = {}
    for tmpl in ("chat", "tf"):
        for task in ("t1", "t2"):
            for kind in ("baseline", "ban"):
                for p in prompts[tmpl][task][kind]:
                    ptext[(tmpl, task, kind, p["id"])] = p["text"]
    datasets = []
    for task in ("t1", "t2"):
        ex = []
        for r in rows:
            if r["task"] != task:
                continue
            kind = "baseline" if r["condition"] == "baseline" else "ban"
            ex.append(example_of(r, ptext[(r["template"], task, kind, r["prompt_id"])]))
        datasets.append({"dataset": TASK_NAMES[task], "examples": ex})
    an = jload(RESULTS / "analysis.json", {})
    sd = jload(RESULTS / "sharpening_direction.json", {})
    if sd:
        for t in sd.get("tasks", {}).values():
            t.pop("band_increment_norms", None)
    gen_meta = {ph: jload(RESULTS / f"gen_meta_{ph}.json") for ph in ("A", "B", "C", "A_EXT")}
    pred_file = PRED / "predict_modal_ban.json"
    meta = {
        "method_name": "post-training collapse screen: 2x2 weights-by-format decomposition + sharpening-direction steering + "
                       "hash-committed base-model forecast",
        "description": ("Qwen3-8B-Base vs Qwen3-8B (thinking off) on two path-search tasks (T1 unweighted grid path, T2 weighted "
                        "shortest path). Arms: base template-free, base chat-templated, instruct chat, instruct template-free "
                        "(2x2), modal-ban arms, and HF steering arms that subtract the paired instruct-minus-base residual "
                        "difference (band-incremental over layers 8-28, plus fallbacks). Every program is scored on >=44 hidden "
                        "tests and labelled by a runtime-signature + AST labeller with a blind LLM judge for disagreements."),
        "models": {"base": MB, "instruct": MI}, "decoding": DECODING,
        "library_versions": lib_versions(), "hardware": hardware(), "gen_engine_meta": gen_meta,
        "deviations": jload(RESULTS / "deviations.json", []),
        "time_log": jload(WS / "time_log.json", []),
        "tasks": {t: {"name": TASK_NAMES[t], "catalogue": CATALOGUE[t],
                      "n_hidden_tests": len(jload(WS / "data" / "tests" / f"{t}.json", {}).get("cases", []))} for t in ("t1", "t2")},
        "prompts_sha256": jload(WS / "data" / "prompts.json", {}).get("sha256_all"),
        "prompt_checks": jload(WS / "data" / "prompts.json", {}).get("checks"),
        "special_token_norms": {m: jload(RESULTS / f"special_token_norms_{m}.json") for m in ("base", "instruct")},
        "harness_calibration": jload(RESULTS / "harness_calibration.json"),
        "labeller_qa": an.get("labeller_qa"),
        "arms": an.get("arms"),
        "collapse_screen": an.get("collapse_screen"),
        "sharpening_direction": sd,
        "hook_tests": jload(RESULTS / "hook_tests.json"),
        "steering": an.get("steering"),
        "manipulation_gap_closed": an.get("manipulation"),
        "base_ban_obedience": an.get("base_ban_obedience"),
        "rows": an.get("rows"),
        "predict_commit": {"file": "predictions/predict_modal_ban.json",
                           "sha256_now": sha256_file(pred_file) if pred_file.exists() else None,
                           "hash_log": (PRED / "hash_log.txt").read_text().splitlines() if (PRED / "hash_log.txt").exists() else [],
                           "git_commit": (PRED / "git_commit.txt").read_text().strip() if (PRED / "git_commit.txt").exists() else None,
                           "guard_test": jload(RESULTS / "predict_guard_test.json")},
        "priors": an.get("priors"),
        "analysis_sanity_checks": an.get("sanity"),
        "costs": {"judge": jload(RESULTS / "judge_cost.json"), "gpu": gpu_cost()},
        "figures": an.get("figures"),
        "kept_artifacts": {"activations/": "per-model residual states at R and teacher-forced generated positions, deltas, "
                                           "band steering vectors (kept on the run volume; each file < 100 MB)",
                           "runs/": "raw generations, labelled per-sample rows, caches",
                           "predictions/": "hash-committed forecast + hash log + commit record"},
    }
    out = clean({"metadata": meta, "datasets": datasets})
    (WS / "method_out.json").write_text(json.dumps(out, indent=1, default=str, allow_nan=False))
    logger.info(f"method_out.json written: {sum(len(d['examples']) for d in datasets)} examples")


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--assemble", action="store_true")
    ap.add_argument("--step", choices=sorted(STEPS))
    a = ap.parse_args()
    setup_logging("method")
    os.chdir(WS)
    if a.all:
        for s in ORDER:
            run_step(s)
        assemble()
    elif a.step:
        run_step(a.step)
    if a.assemble:
        assemble()


if __name__ == "__main__":
    main()
