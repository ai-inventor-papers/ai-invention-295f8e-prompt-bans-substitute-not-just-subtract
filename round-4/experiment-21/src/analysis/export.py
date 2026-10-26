#!/usr/bin/env python3
"""S10 outputs: data/samples.jsonl (one merged row per program), results/deviations.json, results/costs summary,
method_out.json (exp_gen_sol_out: datasets seed_coupled_off, seed_coupled_on, engine_check, fp8_crosscheck) and its
mini / preview variants."""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from loguru import logger

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / "src", ROOT / "analysis"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import core  # noqa: E402
from cfg import DATA_DIR, RESULTS_DIR, read_json, read_jsonl, utc_now, write_json  # noqa: E402
from cfg4 import TEMPS, fmt_t  # noqa: E402

SAMPLES = DATA_DIR / "samples.jsonl"
DROP_FIELDS = {"code"}


def _j(p: Path) -> Any:
    return read_json(p) if p.exists() else None


def pkey(arm: str) -> str:
    return "predict_" + re.sub(r"[^A-Za-z0-9_]", "_", arm)


def lp(r: dict[str, Any] | None) -> str:
    if not r:
        return "missing"
    return f"{r.get('label')}|{'pass' if r.get('passed') else 'fail'}"


def write_samples(rows: list[dict[str, Any]]) -> None:
    from cfg import write_jsonl
    think = {f"T2|{r['template']}|{r['arm']}|{r['sample_id']}": r for r in read_jsonl(DATA_DIR / "raw_thinking.jsonl")}
    out = []
    for r in rows:
        t = think.get(r["key"])
        rec = {k: v for k, v in r.items() if k not in ("token_ids",)}
        rec["token_ids"] = r.get("token_ids")
        if t:
            rec["n_think_tokens"] = t["n_think_tokens"]
            rec["first_approach"] = t["first_approach"]
            rec["completed"] = t["completed"]
            rec["forced"] = t["forced"]
            rec["think_text_head"] = t["think_text"][:1500]
        out.append(rec)
    write_jsonl(SAMPLES, out)
    logger.info(f"data/samples.jsonl: {len(out)} rows")


def deviations() -> list[dict[str, str]]:
    bs = _j(RESULTS_DIR / "batch_sizes.json") or {}
    unit = (_j(RESULTS_DIR / "screen.json") or {}).get("T03_unit_comparison", {})
    drops = (_j(RESULTS_DIR / "drop_decisions.json") or {}).get("drop", [])
    d = [
        {"id": "D1", "what": "Hardware: one 16 GB NVIDIA RTX 2000 Ada (CC 8.9), not the 20 GB A4500 the budget assumed. "
                            "Per the plan's S0/F2 branch for a 16 GB Ada card, the HF engine is exp17's FP8 W8A8 "
                            "loader (the screen's own precision and card), not bf16.",
         "consequence": "precision equals the screen's; bf16-specific statements are not made"},
        {"id": "D2", "what": "vLLM ran Qwen/Qwen3-8B-FP8 with weight-only FP8 Marlin kernels, eager, torch.compile off "
                            "(no C compiler on the machine, as in exp18).", "consequence": "the thinking-on arm and "
                            "the HF arms use different FP8 implementations; A8 bounds the difference on one cell"},
        {"id": "D3", "what": "The screen's escape rule ('N=10 rule') is not defined on the run volume; reconstructed as "
                            "excess >= 0.20 and pass ratio >= 0.85 on the k 0-9 slots (reproduces T03 7/15, T2 3/15; "
                            "excess-only reading gives T2 5/15, reported).", "consequence": "descriptive flag only"},
        {"id": "D4", "what": f"T03 unit: exp17's FP8 T03 norms are {unit.get('overall_median_ratio', float('nan')):.2f}x "
                            "(median) the protocol-v4 unit (exp13) used in the 2x2; alpha 1 on T03 is therefore a "
                            "weaker push than the screen's alpha 1 (the engine check uses exp17's unit).",
         "consequence": "the committed T03 power expectation is optimistic; a unit-adjusted sensitivity is in "
                        "results/expectations.json"},
        {"id": "D5", "what": "Unit sensitivity recomputed on the FP8 W8A8 engine (bf16 does not fit the card), "
                            "results/unit_sensitivity.json.", "consequence": "precision-matched, not bf16"},
        {"id": "D6", "what": "The first vLLM launch was stopped by this artifact's RAM watchdog, which counted page "
                            "cache; fixed to working set (usage - inactive file) before any decisive sample; only "
                            "engine load was lost.", "consequence": "none on data"},
        {"id": "D7", "what": "OpenRouter GET /key returns 403 through the proxy; spend is tracked from usage.cost "
                            "(results/costs.json, judge cost files).", "consequence": "none"},
        {"id": "D8", "what": "A8 FP8 cross-check compares vLLM FP8 (Marlin) with HF FP8 W8A8 (bf16 HF cannot load on "
                            "16 GB); exp18's FP8-vs-bf16 bound on T2 is cited.", "consequence": "weak precision check"},
        {"id": "D9", "what": "Figures rendered with matplotlib directly from the result dictionaries (not through the "
                            "aii-data-fig-gen spec renderer).", "consequence": "none on numbers"},
        {"id": "D10", "what": "Label 'disputed' (judge unavailable or over cap) is treated as 'unresolved' (excluded, "
                             "with sensitivities).", "consequence": "as specified"},
        {"id": "D11", "what": f"Batch sizes per task decided by the committed rule: {bs.get('B')}.",
         "consequence": "constant within task across all arms"},
        {"id": "D12", "what": f"Drop decisions applied: {drops or 'none from the extrapolation'}; optional arm (i) "
                             "(T1 thinking on, ~1.5 h) not run: less than 1.5 h of wall clock remained after G2.",
         "consequence": "T1 thinking-on statements are not made"},
        {"id": "D13", "what": "The plan's (ii) causal-masking identity (max |diff| = 0 between thinking-on and -off "
                             "clean S states) cannot hold bit-exactly under FP8 prefill of different lengths; the "
                             "measured difference is logged (results/tpn_causal_mask_check.json).",
         "consequence": "PN in (ii) is anchored to the thinking-on clean prefill"},
        {"id": "D14", "what": "Two venvs (.venv_hf, .venv_vllm) instead of one 'uv run': the vLLM script is run with "
                             ".venv_vllm/bin/python; every other stage with .venv_hf/bin/python method.py --stage.",
         "consequence": "none"},
    ]
    return d


def build_method_out(rows: list[dict[str, Any]]) -> dict[str, Any]:
    idx = core.index_rows(rows)
    c1 = _j(RESULTS_DIR / "c1seed.json") or {}
    prompts = {(r["task"], r["w"]): r for r in read_jsonl(ROOT / "prompts/prompts.jsonl") if r["kind"] == "twin"}
    by_seed: dict[tuple[str, str], dict[str, dict]] = defaultdict(dict)
    for r in rows:
        if r["arm"].startswith(("SMOKE",)):
            continue
        by_seed[(r["task"], f"{r['template']}|{int(r['sample_id'])}")][r["arm"]] = r
    off, on = [], []
    seeds = core.seeds_of()
    for task in ("T2", "T03", "T1"):
        for s in seeds:
            arms = by_seed.get((task, s), {})
            w, k = s.split("|")
            base = {"metadata_task": task, "metadata_template": w, "metadata_k": int(k),
                    "metadata_slot": f"{task}|{w}|{k}"}
            off_arms = {a: r for a, r in arms.items() if not a.startswith(("THINK", "FP8X", "TPN"))}
            if off_arms:
                ex = {"input": f"[{task} twin prompt {w}, token seed slot k={k}]\n" + prompts[(task, w)]["user_text"],
                      "output": lp(off_arms.get("NOPN_T1.0")), **base,
                      "metadata_coupling": "inverse-CDF CRN (GB_* rows: Gumbel-max)",
                      "metadata_changed_T": (c1.get("A1_C_T_off", {}).get(task, {}).get("primary", {})
                                             .get("changed_seeds") or []).count(s)}
                for a in sorted(off_arms):
                    ex[pkey(a)] = lp(off_arms[a])
                off.append(ex)
            th = {a: r for a, r in arms.items() if a.startswith("THINK")}
            if th:
                ex = {"input": f"[{task} twin prompt {w}, thinking on, request seed slot k={k}]\n" +
                               prompts[(task, w)]["user_text"],
                      "output": lp(th.get("THINK_T0.7")) + f"|completed={th.get('THINK_T0.7', {}).get('completed')}",
                      **base, "metadata_coupling": "vLLM exponential race (Gumbel-max)",
                      "metadata_n_think_tokens": {a: th[a].get("n_think_tokens") for a in sorted(th)}}
                for a in sorted(th):
                    ex[pkey(a)] = lp(th[a]) + f"|completed={th[a].get('completed')}"
                    ex[pkey(a + "_first_approach")] = str(th[a].get("first_approach"))
                on.append(ex)
    ec_ex = []
    scr = {f"{r['task']}|{r['template']}|{r['arm']}|{r['sample_id']}": r
           for r in read_jsonl(ROOT / "inputs/exp17/data/labels.jsonl") if r["task"] in ("T2", "T03")}
    raw_scr = {f"{r['task']}|{r['template']}|{r['arm']}|{r['sample_id']}": r for r in
               read_jsonl(ROOT / "inputs/exp17/data/samples_raw_enginecheck_subset.jsonl")}
    for r in rows:
        if not r["arm"].startswith("EC_"):
            continue
        sarm = "NEUTRAL" if "NEUTRAL" in r["arm"] else r["arm"][3:].replace("_T1.0", "")
        sk = f"{r['task']}|{r['template']}|{sarm}|{r['sample_id']}"
        s = scr.get(sk)
        sr = raw_scr.get(sk)
        ec_ex.append({"input": f"[engine check {r['task']} {r['template']} k={r['sample_id']} arm {r['arm']}]",
                      "output": lp(s), "predict_this_run": lp(r), "metadata_task": r["task"], "metadata_arm": r["arm"],
                      "metadata_byte_identical_to_screen": bool(sr and sr["token_ids"] == r.get("token_ids"))})
    fx = []
    for w in ("W1", "W2", "W3", "W4", "W5"):
        for k in range(10):
            v = idx.get(("T2", f"{w}|{k}", "FP8X_T1.0"))
            h = idx.get(("T2", f"{w}|{k}", "EC_NEUTRAL_T1.0"))
            if v or h:
                fx.append({"input": f"[T2 twin {w} k={k}, thinking off, T 1.0]", "output": lp(h),
                           "predict_vllm_fp8_marlin": lp(v), "metadata_template": w, "metadata_k": k})
    datasets = [{"dataset": n, "examples": e} for n, e in (("seed_coupled_off", off), ("seed_coupled_on", on),
                                                           ("engine_check", ec_ex), ("fp8_crosscheck", fx)) if e]
    from prereg import verify_chain
    meta = {"method_name": "same-seed 2x2: temperature vs plan noise (C1-seed)", "created_utc": utc_now(),
            "description": "Seed-coupled comparison on Qwen3-8B of temperature (NO-PN block) vs plan noise "
                           "(isotropic directions at task-spec states, blocks 12-23, prefill only) for T2/T1/T03; "
                           "thinking-on T2 under vLLM per-request seeds.",
            "verdict": c1.get("verdict"), "decision_inputs": c1.get("decision_inputs"),
            "holm_entry": c1.get("holm_entry"), "c1seed": c1, "phrasing_pooled": c1.get("A4_phrasing_pooled"),
            "thinking": _j(RESULTS_DIR / "thinking.json"), "engine_check": _j(RESULTS_DIR / "engine_check.json"),
            "determinism": _j(RESULTS_DIR / "determinism.json"), "fp8_crosscheck": _j(RESULTS_DIR / "fp8_crosscheck.json"),
            "unit_tests_gpu": _j(RESULTS_DIR / "unit_tests_gpu.json"), "u6_vllm": _j(RESULTS_DIR / "u6_vllm.json"),
            "tests_cpu": _j(RESULTS_DIR / "tests_cpu.json"), "screen_headline": (_j(RESULTS_DIR / "screen.json") or {})
            .get("headline_check"), "expectations": _j(RESULTS_DIR / "expectations.json"),
            "unit_sensitivity": _j(RESULTS_DIR / "unit_sensitivity.json"),
            "novelty_audit": {k: v for k, v in (_j(RESULTS_DIR / "novelty_audit.json") or {}).items() if k != "rows"},
            "first_approach_judge_audit": {k: v for k, v in (_j(RESULTS_DIR / "first_approach_judge_audit.json") or {})
                                           .items() if k != "rows"},
            "dependency_usage": _j(RESULTS_DIR / "dependency_usage.json"),
            "timing": {"vllm": _j(RESULTS_DIR / "timing_vllm.json"),
                       "extrapolation": _j(RESULTS_DIR / "timing_extrapolation.json"),
                       "gpu_hours": _j(RESULTS_DIR / "gpu_hours.json")},
            "costs": _j(RESULTS_DIR / "costs_summary.json"), "deviations": deviations(),
            "commitments": verify_chain(), "not_run": ["optional arm (i): T1 thinking on (wall clock)"]}
    return {"metadata": meta, "datasets": datasets}


def mini_preview(obj: dict[str, Any]) -> None:
    def trunc(x: Any) -> Any:
        if isinstance(x, str):
            return x[:200]
        if isinstance(x, list):
            return [trunc(v) for v in x[:3]]
        if isinstance(x, dict):
            return {k: trunc(v) for k, v in x.items()}
        return x
    mini = {"metadata": {k: obj["metadata"][k] for k in ("method_name", "description", "verdict", "holm_entry")},
            "datasets": [{"dataset": d["dataset"], "examples": d["examples"][:3]} for d in obj["datasets"]]}
    prev = {"metadata": trunc(mini["metadata"]),
            "datasets": [{"dataset": d["dataset"], "examples": [trunc(e) for e in d["examples"]]}
                         for d in mini["datasets"]]}
    (ROOT / "full_method_out.json").write_text(json.dumps(obj, indent=1, default=str))
    (ROOT / "mini_method_out.json").write_text(json.dumps(mini, indent=1, default=str))
    (ROOT / "preview_method_out.json").write_text(json.dumps(prev, indent=1, default=str))


def costs_summary() -> dict[str, Any]:
    led = _j(RESULTS_DIR / "costs.json") or {"usd": {}}
    path = _j(RESULTS_DIR / "openrouter_cost_paths.json") or {}
    bench = sum(float(r.get("cost") or 0) for r in read_jsonl(DATA_DIR / "judge_cache.jsonl")
                if r.get("utc", "9") >= "2026-10-21")
    path_usd = sum(float(v) for k, v in (path.get("by_purpose") or path).items() if isinstance(v, (int, float)))
    out = {"audits": led.get("usd"), "path_judge_cost_file": path, "path_judge_usd": path_usd,
           "bench_judge_usd_estimate": bench, "utc": utc_now()}
    out["total_usd"] = float(sum(led.get("usd", {}).values())) + path_usd + bench
    write_json(RESULTS_DIR / "costs_summary.json", out)
    return out


def gpu_hours() -> dict[str, Any]:
    tb = read_jsonl(RESULTS_DIR / "timing_batches.jsonl")
    tv = _j(RESULTS_DIR / "timing_vllm.json") or {}
    hf = sum(r["seconds"] for r in tb)
    vl = sum(v.get("seconds", 0) for v in tv.values() if isinstance(v, dict))
    out = {"hf_sampling_seconds": hf, "vllm_generation_seconds": vl, "gpu_hours_sampling": (hf + vl) / 3600,
           "n_hf_batches": len(tb)}
    write_json(RESULTS_DIR / "gpu_hours.json", out)
    return out


def run_export() -> dict[str, Any]:
    from report import load_rows

    rows = load_rows()
    write_samples(rows)
    write_json(RESULTS_DIR / "deviations.json", deviations())
    costs_summary()
    gpu_hours()
    obj = build_method_out(rows)
    (ROOT / "method_out.json").write_text(json.dumps(obj, indent=1, default=str))
    mini_preview(obj)
    logger.info(f"method_out.json: {[(d['dataset'], len(d['examples'])) for d in obj['datasets']]}")
    return obj
