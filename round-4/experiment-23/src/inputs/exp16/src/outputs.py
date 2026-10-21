#!/usr/bin/env python3
"""S10 outputs: results/deviations.json and method_out.json (exp_gen_sol_out). One dataset per readout:
route_arms (one example per CRN slot; output = arm-a label; predict_<arm> = 'label|pass'), veto_sufficiency,
prefill, path_screen, controls. metadata carries every analysis summary and the deviations list."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from loguru import logger

from cfg import (MODEL_ID, MODEL_REVISION, PATH_DEFAULT, PATH_TASKS, PRED_DIR, RESULTS_DIR, ROOT, STAGE_A, TEMPLATE_IDS,
                 default_of, read_json, read_jsonl, write_json)

DEVIATIONS = [
    {"id": "D1", "what": "Hardware: one NVIDIA L4 (23 GB; about a third of the RTX 4090's memory bandwidth) instead of the "
     "planned RTX A4500. Measured decode latency was 89 ms/step at B=20 and 101 ms/step at B=40, so batches are B=40 rows "
     "instead of B=10.", "consequence": "Batch shape is constant within each shape class (task, cache length, first "
     "position); CRN partners of a slot always meet identical kernels (U1 = 1.00, U2 = 1.00)."},
    {"id": "D2", "what": "Rows of different templates with equal prompt length share a batch (cross-template packing); the "
     "last batch of a class is padded with discarded duplicate rows.", "consequence": "None on the estimates; rows never "
     "interact inside a batch."},
    {"id": "D3", "what": "V1 (one-shot veto) runs at N=100 (k 0-19) instead of N=50; VP (persistent veto) at N=100 on the "
     "path screen; route arms c/d also run on non-gated tasks at N=100 (descriptive, Q5 upgraded).", "consequence":
     "More precision at no extra batch cost (B=40 pairs b with V1, a with c, etc.)."},
    {"id": "D4", "what": "K0 is implemented by removing the condition span [p0, p1) from the cache instead of masking it "
     "(keys keep their RoPE rotation; generated queries keep positions P + step).", "consequence": "Exact for every "
     "generated query; checked in U3 against exp8's masked knockout (TV distance 1.2e-7 on the first generated position; "
     "eager attention mass on the span exactly 0 in all 36 layers). Lets every batch run stock SDPA with native GQA."},
    {"id": "D5", "what": "A row stops once its first fenced code block is closed (both labellers extract exactly that "
     "block).", "consequence": "Labels unchanged; generation shortened."},
    {"id": "D6", "what": "Memory guard: finished rows are pruned from a batch once it passes step 560 (B=40 would "
     "otherwise exceed the L4's memory at ~600 new tokens).", "consequence": "Only rows still running past step 560 "
     "change batch shape after that step; their CRN coupling is approximate after it (logged per row as pruned_at)."},
    {"id": "D7", "what": "Order: the ban-free arms (S4 b/V1, path screen round 1, twin-only controls pl/bB/K0b) ran before "
     "the analysis code was appended to commit #1, and before the T2 engine tests U1-U3/U9; no ban prompt of any task "
     "was sampled before commit #1 closed (asserted in code).", "consequence": "The decision rules and thresholds were "
     "already frozen in predictions/prereg.md (commit #1, first lines); the analysis code itself was committed after "
     "ban-free outputs existed."},
    {"id": "D8", "what": "Placebo splice (pl vs b under noun B) and K0b ran on the first three Stage-A tasks (T03, T04, "
     "T06) before the gate was known (the plan says the first three GATED tasks).", "consequence": "They are splice- "
     "and knockout-mechanics controls, valid whatever the gate."},
    {"id": "D9", "what": "Judge: the frozen bench judge j1 (gemini-2.5-flash-lite) hit transient HTTP 429 limits; failed "
     "calls are retried with backoff and rows left 'disputed' are re-judged when the label worker is idle (corrected rows "
     "appended; readers take the last row per uid). Caps: USD 0.15 per judge family (bench j1 + exp8 suite judge), "
     "total <= USD 0.30.", "consequence": "Rows still disputed at the end are excluded from shares (F7) and reported."},
    {"id": "D10", "what": "Proximity uses Zhang-Shasha (zss) on AST trees whose node labels are node types (user "
     "identifiers normalised; attribute names and constant types kept).", "consequence": "Used only in the secondary C1 rows."},
    {"id": "D11", "what": "U4-U6 (veto prefix identity, persistent-veto absence, prefill verbatim) are checked on all "
     "production rows by audit/rederive.py rather than on a separate 20-slot test.", "consequence": "Stronger check."},
    {"id": "D13", "what": "Label-worker restarts (to add judge retries and lower the judge caps) killed the wrapper "
     "subshell instead of the Python process, so from 18:50 to 20:16 UTC up to three label workers ran concurrently and "
     "each labelled the same rows. data/samples.jsonl therefore accumulated duplicate rows (24,924 lines for 13,030 "
     "uids); it was compacted to the last row per uid, which is the row every reader (GPU queue, commit #2, analysis, "
     "audit) used throughout.", "consequence": "Labels come from the same frozen labellers with code-hash caches, so "
     "duplicates agree up to judge nondeterminism on a few judge-labelled programs; the audit re-derives commit #2's V_t "
     "within 0.02 and finds 0 mismatches. Some judge calls were duplicated; total judge spend stayed at USD 0.105."},
    {"id": "D12", "what": "The bench pilot was generated with Qwen3-8B-FP8 in vLLM; this artifact samples bf16 weights in "
     "HF transformers (as planned).", "consequence": "Arm-b default shares are 0.95 (T03), 0.76 (R6), 0.92 (T14) instead of "
     "the pilot's ~1.0; the distinctive n-gram was frozen on the pilot programs."},
]


def _lab(r: dict[str, Any] | None) -> str:
    if r is None:
        return "not_run"
    return f"{r['label']}|{'pass' if r.get('passed') else 'fail'}"


def build_outputs() -> dict[str, Any]:
    rows = {}
    for r in read_jsonl(ROOT / "data" / "samples.jsonl"):
        rows[r["uid"]] = r
    an = read_json(RESULTS_DIR / "analysis.json")
    ngr = read_json(PRED_DIR / "ngrams.json")
    prompts = {(r["task"], r["w"], r["kind"]): r for r in read_jsonl(ROOT / "prompts" / "prompts.jsonl")}
    get = lambda t, a, w, k: rows.get(f"{t}|{a}|{w}|{k}")  # noqa: E731
    gated = set(an["gated"])
    ds_route, ds_veto, ds_pre, ds_path, ds_ctrl = [], [], [], [], []
    for t in STAGE_A:
        for w in TEMPLATE_IDS:
            ban_cond = prompts[(t, w, "ban")]["cond"]
            twin = prompts[(t, w, "twin_A")]["cond"]
            for k in range(20):
                a = get(t, "a", w, k)
                if a is None:
                    continue
                inp = f"task {t} | template {w} | slot k={k} | ban segment: {ban_cond!r} | neutral twin: {twin!r}"
                ex = {"input": inp, "output": a["label"], "metadata_task": t, "metadata_template": w, "metadata_k": k,
                      "metadata_default": default_of(t), "metadata_gated": t in gated,
                      "metadata_a_passed": bool(a.get("passed"))}
                for arm in ("b", "c", "d", "K0"):
                    ex[f"predict_{arm}"] = _lab(get(t, arm, w, k))
                ds_route.append(ex)
                b, v = get(t, "b", w, k), get(t, "V1", w, k)
                if b is not None and v is not None:
                    ds_veto.append({"input": f"task {t} | template {w} | slot k={k} | vetoed n-gram {ngr[t].get('text')!r}",
                                    "output": b["label"], "predict_V1": _lab(v),
                                    "predict_V1_fired": str(bool(v.get("veto_fired"))),
                                    "metadata_fire_step": v.get("fire_step"), "metadata_task": t, "metadata_template": w,
                                    "metadata_k": k, "metadata_default": default_of(t)})
                if k < 10 and get(t, "BAN+SIG", w, k) is not None:
                    ds_pre.append({"input": f"task {t} | template {w} | slot k={k} | prefills: signature + neutral",
                                   "output": a["label"],
                                   **{f"predict_{x.replace('+', '_')}": _lab(get(t, x, w, k))
                                      for x in ("BAN+SIG", "TWIN+SIG", "BAN+NEU", "TWIN+NEU")},
                                   "metadata_task": t, "metadata_template": w, "metadata_k": k})
                if k < 10 and get(t, "pl", w, k) is not None:
                    ds_ctrl.append({"input": f"task {t} | template {w} | slot k={k} | placebo splice twinA|twinB",
                                    "output": _lab(get(t, "bB", w, k)), "predict_pl": _lab(get(t, "pl", w, k)),
                                    "predict_K0b": _lab(get(t, "K0b", w, k)), "predict_b": _lab(b),
                                    "metadata_task": t, "metadata_template": w, "metadata_k": k})
    e8 = {(r["task"], r["condition"], r["template"], r["sample_id"]): r
          for r in read_jsonl(ROOT / "inputs" / "exp8" / "data" / "samples.jsonl")}
    for t in PATH_TASKS:
        for w in TEMPLATE_IDS:
            for k in range(20):
                arms = {x: get(t, x, w, k) for x in ("V1", "VP", "OPEN", "R2", "R3")}
                if not any(arms.values()):
                    continue
                ref = e8.get((t, "a", w, k))
                ds_path.append({"input": f"path task {t} (default {PATH_DEFAULT[t]}) | template {w} | slot k={k} | "
                                         "twin prompt with vetoes", "output": ref["label"] if ref else "not_available",
                                **{f"predict_{x}": _lab(r) for x, r in arms.items() if r is not None},
                                "metadata_task": t, "metadata_template": w, "metadata_k": k,
                                "metadata_output_source": "exp8 arm a (full ban) label for the same slot"})
    datasets = [{"dataset": n, "examples": ex} for n, ex in (("route_arms", ds_route), ("veto_sufficiency", ds_veto),
                                                             ("prefill", ds_pre), ("path_screen", ds_path),
                                                             ("controls_placebo_K0b", ds_ctrl)) if ex]
    write_json(RESULTS_DIR / "deviations.json", DEVIATIONS)
    rt = an["route"]
    meta = {
        "method_name": "Bench route test of prompt bans (CRN KV-splice arms, one-shot veto, prefill) in Qwen3-8B",
        "model": MODEL_ID, "model_revision": MODEL_REVISION, "dtype": "bfloat16", "thinking": False,
        "decoding": "T=1.0, top-p 1.0, no top-k, max 1024 new tokens, CRN inverse-CDF sampling",
        "hardware": "1 x NVIDIA L4 23 GB, 6 CPUs, 66 GB RAM",
        "baselines": "arm a (full ban) and arm b (token-length-matched neutral twin) in the same pipeline with the same "
                     "uniforms; placebo splice and knockout-mechanics controls",
        "gated_tasks": an["gated"], "gate": an["gate"],
        "C2a": {"verdict": rt.get("verdict"), "verdict_by_interval": rt.get("verdict_by_interval"),
                "point": rt.get("point"), "intervals": {k: {kk: vv for kk, vv in v.items() if kk != "jackknife_values"}
                                                        for k, v in (rt.get("intervals") or {}).items()},
                "p_boot_F_prompt_le_half": rt.get("p_boot_F_prompt_le_half"),
                "p_boot_F_direct_ge_third": rt.get("p_boot_F_direct_ge_third"),
                "per_task": rt.get("per_task"), "mixed_glm": rt.get("mixed_glm"),
                "leave_one_template_out": rt.get("leave_one_template_out")},
        "C2c": {k: v for k, v in an["c2c"].items()},
        "C2b_sensitivity": an["c2b_sensitivity"], "prefill": an["prefill"], "controls": an["controls"],
        "screen": {k: v for k, v in an["screen"].items() if k != "rounds"} | {"rounds": {
            t: {arm: {kk: vv for kk, vv in rd.items() if kk != "reemergence_surfaces"} if isinstance(rd, dict) else rd
                for arm, rd in r.items()} for t, r in an["screen"].get("rounds", {}).items()}},
        "lp_readout": an["lp_readout"].get("pooled_gated") if isinstance(an["lp_readout"], dict) else None,
        "shares": {t: {a: {k: v for k, v in s.items() if k != "per_template"} for a, s in x.items()}
                   for t, x in an["shares"].items()},
        "engine_validation": read_json(RESULTS_DIR / "engine_validation.json"),
        "labeller_recheck": {k: v for k, v in read_json(RESULTS_DIR / "labeller_recheck.json").items() if k != "bench"},
        "deviations": DEVIATIONS,
        "extras_replication_and_depth": ({k: v for k, v in read_json(RESULTS_DIR / "replication.json").items()
                                          if k in ("tasks", "pooled_r2", "per_task_main_vs_r2", "spearman_main_vs_r2",
                                                   "verdict_r2_same_rule", "controls_all", "prefill_depth_curve")}
                                         if (RESULTS_DIR / "replication.json").exists() else None),
        "supplementary": ({k: v for k, v in read_json(RESULTS_DIR / "supplementary.json").items()
                           if k in ("ban_failures", "label_sources", "n_disputed_final", "bench_judge_spend_usd",
                                    "path_judge_spend_usd", "finish_reasons", "pruned_rows")}
                          if (RESULTS_DIR / "supplementary.json").exists() else None),
        "audit": ({k: v for k, v in read_json(RESULTS_DIR / "rederive.json").items()
                   if k in ("n_mismatches", "U4_pass", "U5_pass", "U6_pass", "hash_chain_ok", "ordering", "placebo_shuffle")}
                  if (RESULTS_DIR / "rederive.json").exists() else None),
        "prereg_amendments": (read_json(RESULTS_DIR / "prereg_amendments.json")
                              if (RESULTS_DIR / "prereg_amendments.json").exists() else None),
        "files": {"samples": "data/samples.jsonl", "raw": "data/samples_raw.jsonl", "analysis": "results/analysis.json",
                  "commitments": "commitments.log", "predictions": "predictions/"},
    }
    out = {"metadata": meta, "datasets": datasets}
    write_json(ROOT / "method_out.json", out)
    logger.info(f"method_out.json: " + ", ".join(f"{d['dataset']}={len(d['examples'])}" for d in datasets))
    return out


if __name__ == "__main__":
    from cfg import setup_logging

    setup_logging("outputs")
    build_outputs()
    _ = Path
