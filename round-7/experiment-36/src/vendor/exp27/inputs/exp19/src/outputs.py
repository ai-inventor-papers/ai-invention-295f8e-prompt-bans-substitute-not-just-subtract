#!/usr/bin/env python3
"""method_out.json (exp_gen_sol_out schema) + full/mini/preview variants.

datasets:
  knob_rows  one example per (task, arm): input = task | arm | prompt kind and decoding; output = the correct
             composition (JSON); predict_hill25 / predict_pass / predict_cost = the Step-0 Hill, pass rate, pass cost
  samples    one example per sample: input = task|arm|template|slot + prompt_sha256; output = label|pass;
             predict_twin_same_slot = the TWIN's label|pass at the same CRN slot
metadata: C1 (primary + sensitivities), engine check, labeller re-check, screen hash, R2 unit, timing, flips,
alpha sweep, PLAIN vs TWIN, forecast score, audits, costs, deviations, not-run cells and the commitment chain.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg import (AUDIT_DIR, DATA_DIR, PRED_DIR, RESULTS_DIR, ROOT, read_json, read_jsonl, setup_logging, utc_now,
                 write_json)


def _maybe(p: Path) -> Any:
    try:
        return read_json(p)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def costs() -> dict[str, Any]:
    """OpenRouter spend of this artifact (USD) from every ledger written by the judges and audits."""
    path_j = _maybe(RESULTS_DIR / "openrouter_cost_paths.json") or {}
    bench_j = sum(r.get("cost", 0.0) or 0.0 for r in read_jsonl(ROOT / "logs" / "openrouter_spend.jsonl"))
    aud = sum(r.get("cost", 0.0) or 0.0 for r in read_jsonl(AUDIT_DIR / "llm_spend.jsonl"))
    lv_path = (_maybe(AUDIT_DIR / "label_validity_path_cost.json") or {}).get("total_usd", 0.0)
    out = {"path_disagreement_judge_and_label_validity_bench_j2_usd": None,
           "path_disagreement_judge_usd": path_j.get("total_usd", 0.0),
           "bench_judge_ledger_usd (j1 disagreement + j2 label-validity)": bench_j,
           "novelty_audit_usd": aud, "label_validity_path_usd": lv_path}
    out["total_usd"] = float(out["path_disagreement_judge_usd"] + bench_j + aud + lv_path)
    out.pop("path_disagreement_judge_and_label_validity_bench_j2_usd")
    out["cap_usd"] = 1.00
    write_json(RESULTS_DIR / "costs.json", out)
    return out


def timing_summary() -> dict[str, Any]:
    rows = read_jsonl(RESULTS_DIR / "timing_batches.jsonl")
    by: dict[str, list] = {}
    for r in rows:
        k = ("path" if r["task"] in ("T1", "T2") else "bench") + ":" + "+".join(r["arms"])
        by.setdefault(k, []).append(r)
    out = {"n_batches": len(rows), "gpu_seconds_total": round(sum(r["seconds"] for r in rows), 1),
           "rows_generated": sum(r["B"] for r in rows),
           "cap_hit_rows": sum(r.get("n_length", 0) for r in rows),
           "by_batch_kind": {k: {"n": len(v), "mean_seconds": round(sum(x["seconds"] for x in v) / len(v), 2),
                                 "mean_steps": round(sum(x["steps"] for x in v) / len(v), 1),
                                 "seconds_per_row": round(sum(x["seconds"] for x in v) / sum(x["B"] for x in v), 3)}
                             for k, v in sorted(by.items())}}
    write_json(RESULTS_DIR / "timing_summary.json", out)
    return out


def build() -> dict[str, Any]:
    costs()
    timing_summary()
    samples = read_jsonl(DATA_DIR / "samples.jsonl")
    kr = read_jsonl(RESULTS_DIR / "knob_rows.jsonl")
    prompts = {r["prompt_sha256"]: r for r in read_jsonl(DATA_DIR / "prompts.jsonl")}
    ex_k = []
    for r in kr:
        ex_k.append({"input": f"{r['task']} | {r['arm']} | knob class {r['knob_class']} | engine {r['engine']} | "
                              f"reference {r['reference_arm']}",
                     "output": json.dumps(r["correct_comp"], sort_keys=True),
                     "predict_hill25": "" if r["hill25_step0"] is None else f"{r['hill25_step0']:.4f}",
                     "predict_pass": f"{r['pass']:.4f}",
                     "predict_cost": "" if r["pass_cost_pts"] is None else f"{r['pass_cost_pts']:.2f}",
                     "metadata_task": r["task"], "metadata_arm": r["arm"], "metadata_n": r["n"],
                     "metadata_n_correct": r["n_correct"], "metadata_ci90": r["ci90"],
                     "metadata_depth_flag": r["depth_flag"]})
    twin = {(r["task"], r["template"], r["slot"]): r for r in samples if r["arm"] == "TWIN"}
    ex_s = []
    for r in samples:
        tw = twin.get((r["task"], r["template"], r["slot"]))
        p = prompts.get(r["prompt_sha256"], {})
        ex_s.append({"input": f"{r['task']}|{r['arm']}|{r['template']}|{r['slot']} prompt_sha256={r['prompt_sha256']} "
                              f"T={r['temperature']} top_k={r['top_k']} min_p={r['min_p']} alpha={r['alpha']}",
                     "output": f"{r['label']}|{'pass' if r['passed'] else 'fail'}",
                     "predict_twin_same_slot": f"{tw['label']}|{'pass' if tw['passed'] else 'fail'}" if tw else "",
                     "metadata_task": r["task"], "metadata_arm": r["arm"], "metadata_knob_class": r["knob_class"],
                     "metadata_template": r["template"], "metadata_slot": r["slot"],
                     "metadata_direction_seed": r["direction_seed"], "metadata_crn_key": r["crn_key"],
                     "metadata_finish_reason": r["finish_reason"], "metadata_n_new_tokens": r["n_new_tokens"],
                     "metadata_labeller_source": r["labeller_source"], "metadata_code_sha256": r["code_sha256"],
                     "metadata_realised_disp": r["realised_disp"], "metadata_prompt_kind": r["prompt_kind"],
                     "metadata_segment": p.get("segment")})
    meta = {"method_name": "Pricing plan noise against temperature (iteration 4, Step 1 / Claim 1)",
            "description": "Fresh per-sample plan noise (PN) at the task-specification positions of blocks 12-23 "
                           "of Qwen3-8B (FP8 W8A8, thinking off), priced against temperature, top-k, prompt knobs "
                           "and reused signature vetoes by correct-only Hill-1 rarefied at depth 25 on each knob's "
                           "randomisation hull (H5, P15, P20), exact CRN coupling.",
            "model": "Qwen/Qwen3-8B@b968826d9c46dd6066d109eabc6255188de91218 (fp8 w8a8 dynamic)",
            "c1": _maybe(RESULTS_DIR / "c1.json"),
            "engine_check": _maybe(RESULTS_DIR / "engine_check.json"),
            "unit_tests_gpu": _maybe(RESULTS_DIR / "unit_tests_gpu.json"),
            "hull_unit_tests": _maybe(RESULTS_DIR / "hull_unit_tests.json"),
            "labeller_recheck": _maybe(RESULTS_DIR / "labeller_recheck.json"),
            "screen": {"sha256": (RESULTS_DIR / "screen.json.sha256").read_text().strip()
                       if (RESULTS_DIR / "screen.json.sha256").exists() else None,
                       "reconciliation": (_maybe(RESULTS_DIR / "screen.json") or {}).get("reconciliation")},
            "screen_forecast": _maybe(PRED_DIR / "screen_forecast.json"),
            "unit_r2": _maybe(RESULTS_DIR / "unit_r2.json"),
            "timing_plan": _maybe(RESULTS_DIR / "timing_plan.json"),
            "timing_summary": _maybe(RESULTS_DIR / "timing_summary.json"),
            "queue_result": _maybe(RESULTS_DIR / "queue_result.json"),
            "alpha_sweep": _maybe(RESULTS_DIR / "alpha_sweep.json"),
            "plain_vs_twin": _maybe(RESULTS_DIR / "plain_vs_twin.json"),
            "forecast_score": _maybe(RESULTS_DIR / "forecast_score.json"),
            "flips": _maybe(RESULTS_DIR / "flips.json"),
            "nonmovable": _maybe(RESULTS_DIR / "nonmovable.json"),
            "per_template": _maybe(RESULTS_DIR / "per_template.json"),
            "ideas_phrasings_file": "results/ideas_phrasings.json",
            "prices_file": "results/prices.json",
            "novelty_audit": {k: v for k, v in (_maybe(AUDIT_DIR / "novelty_audit.json") or {}).items()
                              if k != "records"},
            "label_validity": {k: v for k, v in (_maybe(AUDIT_DIR / "label_validity.json") or {}).items()
                               if k != "rows"},
            "dependency_usage": _maybe(RESULTS_DIR / "dependency_usage.json"),
            "costs": _maybe(RESULTS_DIR / "costs.json"),
            "deviations": read_jsonl(RESULTS_DIR / "deviations.jsonl"),
            "rederive": _maybe(RESULTS_DIR / "rederive.json"),
            "placebo_full_rule": {k: v for k, v in (_maybe(RESULTS_DIR / "placebo_full_rule.json") or {}).items()
                                  if k != "shuffles"},
            "vs_dispatch": _maybe(RESULTS_DIR / "vs_dispatch.json"),
            "manual_pass": {k: v for k, v in (_maybe(AUDIT_DIR / "manual_pass.json") or {}).items() if k != "records"},
            "commitments_log": (ROOT / "commitments.log").read_text().splitlines()
            if (ROOT / "commitments.log").exists() else [],
            "utc": utc_now()}
    return {"metadata": meta, "datasets": [{"dataset": "knob_rows", "examples": ex_k},
                                           {"dataset": "samples", "examples": ex_s}]}


def _trunc(o: Any, n: int = 200) -> Any:
    if isinstance(o, str):
        return o[:n]
    if isinstance(o, dict):
        return {k: _trunc(v, n) for k, v in o.items()}
    if isinstance(o, list):
        return [_trunc(v, n) for v in o]
    return o


def main() -> None:
    setup_logging("outputs")
    out = build()
    write_json(ROOT / "method_out.json", out, indent=None)
    write_json(ROOT / "full_method_out.json", out, indent=None)
    mini = {"metadata": out["metadata"], "datasets": [{"dataset": d["dataset"], "examples": d["examples"][:3]}
                                                      for d in out["datasets"]]}
    write_json(ROOT / "mini_method_out.json", mini)
    prev = {"metadata": _trunc({k: v for k, v in out["metadata"].items() if k in
                                ("method_name", "description", "model", "engine_check", "screen", "utc")}),
            "datasets": [{"dataset": d["dataset"], "examples": _trunc(d["examples"][:3])} for d in out["datasets"]]}
    c1 = out["metadata"].get("c1") or {}
    prev["metadata"]["c1_primary_verdict"] = (c1.get("primary") or {}).get("verdict")
    write_json(ROOT / "preview_method_out.json", prev)
    logger.info(f"method_out.json: {len(out['datasets'][0]['examples'])} knob rows, "
                f"{len(out['datasets'][1]['examples'])} samples")


if __name__ == "__main__":
    main()
