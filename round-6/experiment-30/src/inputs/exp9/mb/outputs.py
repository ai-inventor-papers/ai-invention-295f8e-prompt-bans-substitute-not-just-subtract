#!/usr/bin/env python3
"""S12 OUTPUTS: data/samples.jsonl (one row per sampled program, shared schema) and method_out.json in the
exp_gen_sol_out format (one example per sampled program: input = prompt, output = mechanism label; multi-ban rows carry
the committed top-1 survivor of every forecast as predict_*), with mini and preview variants."""

from __future__ import annotations

import copy
import json
import subprocess
from pathlib import Path
from typing import Any

from loguru import logger

from common import (DATA_DIR, DECODING, DECODING_TAG, LOG_DIR, MODEL_ID, MODEL_REVISION, RESULTS_DIR, ROOT,
                    TASK_DATASET_NAME, read_json, read_jsonl, write_json, write_jsonl)

SOURCES = ("smoke", "forced_rest", "session1", "session2")
PRED_KEYS = {"LADDER": "predict_ladder", "PRIME_AND_VETO": "predict_pnv", "PROXIMITY": "predict_proximity",
             "FRLP_BAN": "predict_frlp", "GENERIC": "predict_generic", "CORPUS": "predict_corpus"}


def _load(name: str) -> Any:
    p = RESULTS_DIR / name
    return read_json(p) if p.exists() else None


def sample_rows() -> list[dict[str, Any]]:
    out = []
    for src in SOURCES:
        raw = {(r["req_id"], r["sample_index"]): r for r in read_jsonl(DATA_DIR / f"raw_{src}.jsonl")}
        for r in read_jsonl(DATA_DIR / f"labelled_{src}.jsonl"):
            rr = raw.get((r["req_id"], r["sample_index"]), {})
            out.append({"task": r["task"], "condition": r["condition"], "template": r["template"],
                        "paraphrase_id": r["paraphrase_id"], "sample_id": r["sample_index"], "seed": r["seed"],
                        "stage": r["stage"], "model": MODEL_ID, "decoding": DECODING_TAG, "label": r["label"],
                        "labeller_source": r["labeller_source"], "runtime_label": r.get("runtime_label"),
                        "ast_label": r.get("ast_label"), "judge_label": r.get("judge_label"),
                        "passed": bool(r.get("passed")), "passed_small": bool(r.get("passed_small")),
                        "truncated": bool(r.get("truncated")), "extracted": bool(r.get("extracted")),
                        "code_sha256": r.get("code_sha256"), "code": r.get("code"), "prompt": rr.get("prompt"),
                        "text": r.get("text"), "source_file": f"raw_{src}.jsonl", "algorithm": r.get("algorithm"),
                        "variant": r.get("variant"), "banned": r.get("banned")})
    return out


DEFAULT = {"t1": "bfs", "t2": "dijkstra"}


def ladder_ranking() -> dict[str, list[str]]:
    """Analysis-catalogue algorithms ordered by the corrected FRLP base value L_j + log(as-requested share)."""
    import math

    keep = read_json(RESULTS_DIR / "catalogue_keep.json")
    cat = keep.get("analysis_catalogue_final", keep["analysis_catalogue"])
    out = {}
    for task in ("t1", "t2"):
        base = {r["algorithm"]: r["L"] for r in read_jsonl(RESULTS_DIR / "frlp_cells.jsonl")
                if r["task"] == task and r["condition"] == "base" and r["half"] == "all" and "variant" not in r}
        lc = {a: base[a] + math.log(max(keep["tasks"][task][a]["share"], 1e-9)) for a in cat[task] if a in base}
        out[task] = sorted(lc, key=lambda a: -lc[a])
    return out


def row_predictions(r: dict[str, Any], ladder: dict[str, list[str]], fcs: dict[str, Any]) -> dict[str, str]:
    """predict_default: the task's modal baseline algorithm (no-change baseline). predict_ladder: the highest-ranked
    non-banned algorithm by corrected FRLP base value (for multi-bans: the committed LADDER top-1). predict_requested:
    the requested algorithm of a forced prompt. Multi-ban rows also carry every committed top-1 survivor."""
    task = r["task"]
    banned = set(r.get("banned") or [])
    pred = {"predict_default": DEFAULT[task]}
    cand = [a for a in ladder[task] if a not in banned]
    if cand:
        pred["predict_ladder"] = cand[0]
    if r["condition"].startswith(("forced:", "forced_desc:")) and r.get("algorithm"):
        pred["predict_requested"] = str(r["algorithm"])
    if r["condition"].startswith("multi:"):
        fc = fcs.get(r["condition"].split(":", 1)[1])
        if fc:
            for f, key in PRED_KEYS.items():
                if f in fc["top1"]:
                    pred[key] = str(fc["top1"][f])
    return pred


def build_method_out(rows: list[dict[str, Any]]) -> dict[str, Any]:
    fcs = {p.stem.replace("forecasts_", ""): read_json(p) for p in sorted((ROOT / "predictions").glob("forecasts_*.json"))}
    ladder = ladder_ranking()
    ds: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        ex = {"input": r["prompt"] or "", "output": r["label"],
              "metadata_task": r["task"], "metadata_condition": r["condition"], "metadata_template": r["template"],
              "metadata_paraphrase_id": r["paraphrase_id"], "metadata_sample_id": r["sample_id"],
              "metadata_seed": r["seed"], "metadata_stage": r["stage"], "metadata_labeller_source": r["labeller_source"],
              "metadata_runtime_label": r["runtime_label"], "metadata_ast_label": r["ast_label"],
              "metadata_judge_label": r["judge_label"], "metadata_passed": r["passed"],
              "metadata_passed_small": r["passed_small"], "metadata_truncated": r["truncated"],
              "metadata_code_sha256": r["code_sha256"], "metadata_code": r["code"],
              "metadata_banned": r["banned"], "metadata_requested_algorithm": r["algorithm"],
              "metadata_prompt_variant": r["variant"]}
        ex.update(row_predictions(r, ladder, fcs))
        if r["condition"].startswith("multi:"):
            fc = fcs.get(r["condition"].split(":", 1)[1])
            if fc:
                ex["metadata_survivors"] = fc["survivors"]
        ex = {k: v for k, v in ex.items() if v is not None}
        ds.setdefault(TASK_DATASET_NAME[r["task"]], []).append(ex)
    meta = {
        "method_name": "Banning five path algorithms at once: mechanism-level landing of Qwen3-8B under multi-name "
                       "bans, forecast by FRLP cells hash-committed before sampling",
        "artifact_plan": "gen_plan_experiment_3_idx4", "model": MODEL_ID, "model_revision": MODEL_REVISION,
        "decoding": DECODING, "decoding_tag": DECODING_TAG,
        "gpu": "NVIDIA GeForce RTX 4090 (24 GB)", "vllm_version": "0.11.0", "transformers_version": "4.57.6",
        "catalogue_keep": _load("catalogue_keep.json"), "variant_decisions": read_json(DATA_DIR / "variant_decisions.json"),
        "labeller_recheck": _load("labeller_recheck.json"), "labeller_ext_validation": _load("labeller_ext_validation.json"),
        "labeller_ext_refs_summary": {k: v for k, v in (_load("labeller_ext_refs.json") or {}).items()
                                      if k not in ("references", "unit_probes")},
        "sets_and_geometry": {k: v for k, v in (_load("sets_and_geometry.json") or {}).items()
                              if k not in ("stability",)},
        "commit_summary": _load("commit_summary.json"), "landing": _load("landing.json"), "los": _load("los.json"),
        "manifold": _load("manifold.json"), "persistence": _load("persistence.json"), "checks": _load("checks.json"),
        "scoring_checks": _load("scoring_checks.json"), "scoring_diag": _load("scoring_diag.json"),
        "aux_datasets": _load("aux_datasets.json"), "placebo": _load("placebo.json"),
        "posthoc_mix_homogeneity": _load("posthoc_mix_homogeneity.json"),
        "independent_rederivation": _load("independent_rederivation.json"),
        "predictions": {"predict_default": "modal baseline algorithm of the task (no-change baseline)",
                        "predict_ladder": "highest non-banned algorithm by corrected FRLP base value (multi-bans: the "
                                          "committed LADDER top-1; other rows: computed after session 1, not committed)",
                        "predict_requested": "forced rows: the requested algorithm",
                        "predict_pnv/proximity/frlp/generic/corpus": "multi-ban rows: committed top-1 survivor"},
        "ladder_ranking": ladder,
        "gpu_hours": "about 1.0 (one RTX 4090: vLLM sessions about 0.45 h incl. server start-ups, HF scoring about 0.4 h, "
                     "plus model loads)",
        "deviations": _load("deviations.json"), "openrouter_cost": _load("openrouter_cost.json"),
        "timing": read_json(LOG_DIR / "timing.json") if (LOG_DIR / "timing.json").exists() else None,
        "frlp_cells_file": "results/frlp_cells.jsonl", "samples_file": "data/samples.jsonl",
        "states_dir": "states/ (kept on the run volume; not in the published repository)"}
    return {"metadata": meta, "datasets": [{"dataset": k, "examples": v} for k, v in ds.items()]}


def _truncate(o: Any, n: int = 200) -> Any:
    if isinstance(o, str):
        return o[:n]
    if isinstance(o, list):
        return [_truncate(x, n) for x in o]
    if isinstance(o, dict):
        return {k: _truncate(v, n) for k, v in o.items()}
    return o


def stage_outputs() -> None:
    rows = sample_rows()
    write_jsonl(DATA_DIR / "samples.jsonl", rows)
    mo = build_method_out(rows)
    out = ROOT / "method_out.json"
    write_json(out, mo, indent=None)
    mini = copy.deepcopy(mo)
    for d in mini["datasets"]:
        d["examples"] = d["examples"][:3]
    mini["metadata"] = {k: mo["metadata"][k] for k in ("method_name", "model", "decoding_tag", "catalogue_keep",
                                                       "commit_summary", "deviations")}
    write_json(ROOT / "mini_method_out.json", mini, indent=1)
    write_json(ROOT / "preview_method_out.json", _truncate(mini), indent=1)
    write_json(ROOT / "full_method_out.json", mo, indent=None)
    # optional schema validation with the aii-json skill (set AII_JSON_SKILL_DIR to its folder); skipped if absent
    import os

    sk = Path(os.environ.get("AII_JSON_SKILL_DIR", str(ROOT / ".aii_json_skill_absent")))
    py = sk.parent / ".ability_client_venv" / "bin" / "python"
    for f in (("method_out.json", "mini_method_out.json", "preview_method_out.json") if py.exists() else ()):
        r = subprocess.run([str(py), str(sk / "scripts" / "aii_json_validate_schema.py"), "--format", "exp_gen_sol_out",
                            "--file", str(ROOT / f)], capture_output=True, text=True, timeout=600)
        logger.info(f"validate {f}: {(r.stdout + r.stderr).strip().splitlines()[-1] if (r.stdout + r.stderr).strip() else r.returncode}")
    sizes = {f: (ROOT / f).stat().st_size / 1e6 for f in ("method_out.json", "full_method_out.json",
                                                        "mini_method_out.json", "preview_method_out.json")}
    logger.info(f"outputs: {len(rows)} sample rows; sizes MB {sizes}")
    write_json(RESULTS_DIR / "output_sizes.json", sizes)


__all__ = ["stage_outputs", "json"]
