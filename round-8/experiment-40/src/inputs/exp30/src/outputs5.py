#!/usr/bin/env python3
"""method_out.json (exp_gen_sol_out schema) + full/mini/preview variants.

datasets:
  literal_cell     one example per literal-cell trace: input = slot, T and prompt hash; output = 'label|pass' of the
                   final code; predict_exp21_top_p1 = exp21's same-seed, same-T top-p-1 trace's 'label|pass'.
  knob_slots       one example per (task, template, slot): input = the slot and its CRN key; output = the TWIN's
                   'label|pass'; predict_<arm> = that arm's 'label|pass' at the same slot (same code-stage stream).
  engine_check     one example per engine-check row: output = this run's 'label|pass' (bf16); predict_exp19_fp8 =
                   exp19's 'label|pass' at the same key.
  dmd_calibration  one example per (task, alpha): output = the committed DMD temperature; metadata = K_PN, f_on, etc.
metadata: both verdicts, every analysis file, unit tests, labeller re-check, timing, costs, deviations, the
commitment chain and the not-run cells.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg import AUDIT_DIR, DATA_DIR, INPUTS, PRED_DIR, RESULTS_DIR, ROOT, read_json, read_jsonl, utc_now, write_json  # noqa: E402


def _maybe(p: Path) -> Any:
    try:
        return read_json(p)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def lp(r: dict[str, Any] | None) -> str:
    if not r:
        return "missing"
    return f"{r.get('label')}|{'pass' if r.get('passed') else 'fail'}"


def costs() -> dict[str, Any]:
    out = {}
    pj = _maybe(RESULTS_DIR / "openrouter_cost_paths.json") or {}
    out["path_disagreement_judge_usd"] = float(pj.get("total_usd", 0.0) or 0.0)
    out["bench_judge_usd"] = float(sum(r.get("cost", 0.0) or 0.0 for r in read_jsonl(ROOT / "logs" / "openrouter_spend.jsonl")))
    out["audits_usd"] = float(sum(r.get("cost", 0.0) or 0.0 for r in read_jsonl(AUDIT_DIR / "llm_spend.jsonl")))
    out["total_usd"] = out["path_disagreement_judge_usd"] + out["bench_judge_usd"] + out["audits_usd"]
    out["cap_usd"] = 1.00
    write_json(RESULTS_DIR / "costs.json", out)
    return out


def timing() -> dict[str, Any]:
    rows = read_jsonl(RESULTS_DIR / "timing_batches.jsonl")
    tv = _maybe(RESULTS_DIR / "timing_vllm.json") or {}
    out = {"hf_batches": len(rows), "hf_gpu_seconds": round(sum(r["seconds"] for r in rows), 1),
           "hf_rows": sum(r["B"] for r in rows), "vllm_literal_seconds": tv.get("F_total_seconds"),
           "hf_gpu_hours": round(sum(r["seconds"] for r in rows) / 3600, 3)}
    write_json(RESULTS_DIR / "timing_summary.json", out)
    return out


def build() -> dict[str, Any]:
    ds = []
    # ---------------------------------------------------------------- literal cell
    raw = {r["sample_id"]: r for r in read_jsonl(DATA_DIR / "literal_raw.jsonl")}
    lab = {r["sample_id"]: r for r in read_jsonl(DATA_DIR / "literal_labels.jsonl")}
    e21 = {}
    for r in read_jsonl(INPUTS / "exp21" / "data" / "samples.jsonl"):
        if r.get("task") == "T2" and str(r.get("arm", "")).startswith("THINK"):
            e21[(r["arm"], r["template"], int(r["sample_id"]))] = r
    from analysis_f import dijkstra_style
    ex = []
    for sid, r in sorted(raw.items(), key=lambda x: (x[1]["template"], x[1]["slot"], x[1]["arm"])):
        l = lab.get(sid, {})
        key = ("THINK_REP_T0.7" if r["repeat"] else f"THINK_T{float(r['temperature']):.1f}", r["template"], int(r["slot"]))
        ex.append({"input": f"T2|{r['template']}|k={r['slot']}|T={r['temperature']}|top_k=10|thinking=on|seed={r['seed']}"
                            f"|prompt_sha256={r['prompt_sha256']}",
                   "output": lp(l), "predict_exp21_top_p1": lp(e21.get(key)),
                   "metadata_arm": r["arm"], "metadata_temperature": r["temperature"], "metadata_repeat": r["repeat"],
                   "metadata_first_approach": r["first_approach"], "metadata_n_think_tokens": r["n_think_tokens"],
                   "metadata_completed": r["completed"], "metadata_forced": r["forced"],
                   "metadata_dijkstra_style": dijkstra_style(l.get("code")) if l.get("label") == "dijkstra" else None,
                   "metadata_engine": r["engine"], "metadata_model": f"{r['model']}@{r['model_revision'][:8]}"})
    if ex:
        ds.append({"dataset": "literal_cell", "examples": ex})
    # ---------------------------------------------------------------- knob slots
    labs = {r["sample_id"]: r for r in read_jsonl(DATA_DIR / "labels.jsonl")}
    slot = defaultdict(dict)
    meta_slot = {}
    for r in read_jsonl(DATA_DIR / "samples_raw.jsonl"):
        l = labs.get(r["sample_id"])
        if l is None:
            continue
        key = (r["task"], r["template"], int(r["slot"]))
        slot[key][r["arm"]] = l
        meta_slot.setdefault(key, r["crn_key"])
    ex = []
    for key in sorted(slot):
        arms = slot[key]
        e = {"input": f"{key[0]}|{key[1]}|k={key[2]}|crn_key={meta_slot[key]}", "output": lp(arms.get("TWIN")),
             "metadata_task": key[0], "metadata_template": key[1], "metadata_slot": key[2],
             "metadata_arms_present": sorted(arms)}
        for a, l in sorted(arms.items()):
            if a == "TWIN":
                continue
            e["predict_" + a.replace(".", "_")] = lp(l)
        ex.append(e)
    if ex:
        ds.append({"dataset": "knob_slots", "examples": ex})
    # ---------------------------------------------------------------- engine check
    e19 = {(r["task"], r["arm"], r["template"], int(r["slot"])): r
           for r in read_jsonl(INPUTS / "exp19" / "data" / "engine_check_labels.jsonl")}
    for r in read_jsonl(INPUTS / "exp19" / "data" / "samples.jsonl"):
        if r.get("arm") in ("T1.3", "TOPK10") and r.get("template") == "W1" and r.get("task") in ("T03", "T2"):
            e19[(r["task"], r["arm"], r["template"], int(r["slot"]))] = r
    ex = []
    for r in read_jsonl(DATA_DIR / "engine_check_labels.jsonl"):
        key = (r["task"], r["arm"], r["template"], int(r["slot"]))
        ex.append({"input": f"{key[0]}|{key[1]}|{key[2]}|k={key[3]}", "output": lp(r), "predict_exp19_fp8": lp(e19.get(key)),
                   "metadata_engine_this_run": "hf_bf16", "metadata_engine_exp19": "hf_fp8_w8a8"})
    if ex:
        ds.append({"dataset": "engine_check", "examples": ex})
    # ---------------------------------------------------------------- DMD calibration
    dmd = _maybe(PRED_DIR / "dmd_temperatures.json") or {}
    ex = []
    for t, d in dmd.items():
        for a, v in d.items():
            if not isinstance(v, dict):
                continue
            ex.append({"input": f"{t}|alpha={a}", "output": f"{v['T_dmd']:.4f}",
                       "predict_K_PN": f"{v['K_PN']:.6f}", "predict_f_on": f"{v['f_on']:.6f}",
                       "metadata_token_departure_PN": v["token_departure_PN"],
                       "metadata_token_departure_DMD": v["token_departure_DMD"], "metadata_flag": v.get("flag"),
                       "metadata_converged": v.get("converged"), "metadata_n_secant_updates": v.get("n_secant_updates"),
                       "metadata_kl_curve_PN": v.get("kl_curve_PN")})
    if ex:
        ds.append({"dataset": "dmd_calibration", "examples": ex})
    # ---------------------------------------------------------------- metadata
    lc = _maybe(RESULTS_DIR / "literal_cell.json") or {}
    cc = _maybe(RESULTS_DIR / "claim_c.json") or {}
    from commit import verify
    meta = {
        "title": "Plan noise against plan-first prompting (iteration 5) + the literal thinking-on cell",
        "model": "Qwen/Qwen3-8B@b968826d (thinking off unless stated); Qwen/Qwen3-8B-Base for BINT intents; "
                 "Qwen/Qwen3-8B-FP8@220b46e3 on vLLM 0.11 for the literal cell",
        "generated_utc": utc_now(),
        "verdict_F": {"C_T": (lc.get("C_T") or {}).get("n_change_final_label"),
                      "n_seeds": (lc.get("C_T") or {}).get("n_seeds_all4_completed"),
                      "clopper_pearson": (lc.get("C_T") or {}).get("clopper_pearson"),
                      "prediction_met": (lc.get("C_T") or {}).get("prediction_met")},
        "verdict_C": cc.get("verdict"), "claim_c": cc,
        "literal_cell": lc,
        "engine_check": _maybe(RESULTS_DIR / "engine_check.json"),
        "pn_vs_dmd": _maybe(RESULTS_DIR / "pn_vs_dmd.json"), "plain_vs_twin": _maybe(RESULTS_DIR / "plain_vs_twin.json"),
        "landings": _maybe(RESULTS_DIR / "landings.json"), "unit_ratio": _maybe(RESULTS_DIR / "unit_ratio.json"),
        "landings_harmonised_posthoc": _maybe(RESULTS_DIR / "landings_harmonised.json"),
        "incomplete_cells": _maybe(RESULTS_DIR / "incomplete_cells.json"),
        "restore_result": _maybe(RESULTS_DIR / "restore_result.json"),
        "knob_table": _maybe(RESULTS_DIR / "knob_table.json"), "defaults": _maybe(RESULTS_DIR / "defaults.json"),
        "cells": _maybe(RESULTS_DIR / "cells.json"),
        "dmd_temperatures": dmd, "format_pilot": _maybe(PRED_DIR / "format_pilot.json"),
        "format_pilot_v1": _maybe(PRED_DIR / "format_pilot_v1.json"),
        "unit_tests_gpu": _maybe(RESULTS_DIR / "unit_tests_gpu.json"), "tests_cpu": _maybe(RESULTS_DIR / "tests_cpu.json"),
        "u6_vllm": _maybe(RESULTS_DIR / "u6_vllm.json"), "labeller_recheck": _maybe(RESULTS_DIR / "labeller_recheck.json"),
        "seed_collisions": _maybe(RESULTS_DIR / "seed_collisions.json"),
        "precision_rule": _maybe(PRED_DIR / "precision_rule.json"),
        "timing": timing(), "timing_extrapolation": _maybe(RESULTS_DIR / "timing_extrapolation.json"),
        "queue_result": _maybe(RESULTS_DIR / "queue_result.json"), "costs": costs(),
        "audits": {"lexicon": _maybe(AUDIT_DIR / "lexicon_audit.json"), "style_regate": _maybe(AUDIT_DIR / "style_regate.json"),
                   "novelty": _maybe(AUDIT_DIR / "novelty_audit.json")},
        "rederive": _maybe(RESULTS_DIR / "rederive.json"),
        "deviations": read_jsonl(RESULTS_DIR / "deviations.jsonl"),
        "commitment_chain": verify(), "commitments": (ROOT / "commitments.log").read_text().splitlines(),
    }
    out = {"metadata": meta, "datasets": ds}
    write_json(ROOT / "method_out.json", out, indent=None)
    return {"datasets": {d["dataset"]: len(d["examples"]) for d in ds}}


if __name__ == "__main__":
    print(build())
