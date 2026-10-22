#!/usr/bin/env python3
"""method_out.json (exp_gen_sol_out schema) + data/samples6.jsonl.

Datasets:
  gemma_l1_events      one example per (unit, nudge, provenance) record: input = unit|nudge|provenance; output = the
                       modal landing ('no clear landing' / 'no event'); predict_base = r_u, predict_tail = t_u,
                       predict_qlik = q_lik top-1; metadata = composition, log scores, flags.
  gemma_pt_repertoire  every few-shot pt program (output = 'label|pass'; metadata family, exemplars, stage).
  gemma_twin_tail      every iteration-6 twin program (T 1.0 slots 10-39, T 1.3 slots 0-19; output = 'label|pass').
  gemma_qlik           one example per (unit, algorithm): output = mean per-token log-prob (norm) of the 48-token
                       openings; predict_qlik_rank = rank among the unit's non-default algorithms.
  gemma_push_fresh     every fresh push / PN / confirmation program (output = 'label|pass').
metadata: every analysis summary, commits, costs, timing, deviations.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg import DATA_DIR, IT_ID, IT_REV, PRED_DIR, PT_ID, PT_REV, RESULTS_DIR, ROOT, read_json, read_jsonl, write_json


def s(x: Any) -> str:
    return "None" if x is None else str(x)


def lab_out(r: dict[str, Any]) -> str:
    return f"{r.get('label')}|{'pass' if r.get('passed') else 'fail'}"


def safe(p: Path) -> Any:
    return read_json(p) if p.exists() else None


def main() -> None:
    labs = {r["row_id"]: r for r in read_jsonl(DATA_DIR / "labels.jsonl")}
    raw = {}
    for f in ("raw_twin6.jsonl", "raw_ptfs6.jsonl", "raw_push6.jsonl", "raw_confirm6.jsonl"):
        for r in read_jsonl(DATA_DIR / f):
            raw[r["row_id"]] = r
    fc = read_json(PRED_DIR / "forecasts_G6.json")["units"]
    ev = read_json(RESULTS_DIR / "events_G6.json")
    l1 = read_json(RESULTS_DIR / "l1_contest.json")
    ls_rows = {}
    for prov, key in (("pooled", "primary_pooled"), ("fresh", "split_fresh_only"), ("old", "split_old_only")):
        for r in (l1.get(key) or {}).get("logscore_table", []) or []:
            ls_rows[(r["unit"], r["nudge"], prov)] = r
    events = []
    for prov, rows in ev.items():
        for e in rows:
            out = e["landing"] if e.get("landing") else ("no clear landing" if e.get("event") else "no event")
            ls = ls_rows.get((e["unit"], e["nudge"], prov), {})
            events.append({"input": f"{e['unit']}|{e['nudge']}|{prov}", "output": out,
                           "predict_base": s(e.get("r_u")), "predict_tail": s(e.get("t_u")),
                           "predict_qlik": s(e.get("qlik_top1")),
                           "metadata_event": bool(e.get("event")), "metadata_composition": e.get("composition"),
                           "metadata_n_correct_offdefault_catalogue": e.get("n_correct_offdefault_catalogue"),
                           "metadata_n_correct_other": e.get("n_correct_other"),
                           "metadata_qualifying_cells": e.get("qualifying_cells"), "metadata_D": e.get("D"),
                           "metadata_K_u": e.get("K_u"), "metadata_chance": e.get("chance"),
                           "metadata_TAIL_EMPTY": e.get("TAIL_EMPTY"), "metadata_DISCORDANT": e.get("DISCORDANT"),
                           "metadata_TAIL_DISCORDANT": e.get("TAIL_DISCORDANT"), "metadata_AUDIT_FAIL": e.get("AUDIT_FAIL"),
                           "metadata_landing_margin": e.get("landing_margin"),
                           "metadata_logscores": {k: ls.get(k) for k in ("q_base", "q_tail", "q_lik", "q_lik_raw", "q_assoc")},
                           "metadata_provenance": prov, "metadata_replication": True})
    pt, twin, push = [], [], []
    for rid, r in raw.items():
        lab = labs.get(rid)
        if lab is None:
            continue
        base_meta = {"metadata_row_id": rid, "metadata_task": r["task"], "metadata_label": lab.get("label"),
                     "metadata_passed": bool(lab.get("passed")), "metadata_valid": bool(lab.get("valid")),
                     "metadata_labeller_source": lab.get("labeller_source"), "metadata_code_sha256": lab.get("code_sha256"),
                     "metadata_finish_reason": r.get("finish_reason"), "metadata_n_new_tokens": r.get("n_new_tokens"),
                     "metadata_temperature": r.get("temperature"), "metadata_precision": r.get("precision"),
                     "metadata_checkpoint": r.get("checkpoint"), "metadata_code": lab.get("code")}
        if r["stage"] == "ptfs6":
            pt.append({"input": f"{r['task']}|{r.get('family')}|draw {r['slot']}", "output": lab_out(lab),
                       "predict_it_default": s(fc[r["task"]]["D"]), "predict_base_runner_up": s(fc[r["task"]]["r_u"]),
                       **base_meta, "metadata_family": r.get("family"), "metadata_exemplars": r.get("exemplars"),
                       "metadata_ptfs_stage": r.get("ptfs_stage")})
        elif r["stage"] == "twin6":
            twin.append({"input": f"{r['task']}|{r['template']}|{r['arm']}|slot {r['slot']}", "output": lab_out(lab),
                         **base_meta, "predict_default": s(fc[r["task"]]["D"]), "metadata_arm": r["arm"]})
        elif r["stage"] in ("push6", "confirm6"):
            push.append({"input": f"{r['task']}|{r['template']}|{r['arm']}|slot {r['slot']}", "output": lab_out(lab),
                         **base_meta, "predict_base": s(fc[r["task"]]["r_u"]), "predict_tail": s(fc[r["task"]]["t_u"]),
                         "predict_qlik": s(fc[r["task"]]["qlik_top1"]), "metadata_arm": r["arm"],
                         "metadata_stage": r["stage"], "metadata_alpha": r.get("alpha"),
                         "metadata_direction_seed": r.get("direction_seed"), "metadata_hook_sha256": r.get("hook_sha256"),
                         "metadata_realised_disp": r.get("realised_disp")})
    qs = read_json(RESULTS_DIR / "qlik_scores.json")
    ql = []
    for t, per in qs.get("own", {}).items():
        nd = fc[t]["nondef"]
        rank = sorted([m for m in per if m in nd], key=lambda m: -per[m]["norm"])
        for m, v in per.items():
            ql.append({"input": f"{t}|{m}", "output": f"{v['norm']:.6f}",
                       "predict_qlik_rank": s(rank.index(m) + 1 if m in rank else None),
                       "metadata_raw": v["raw"], "metadata_n_programs": v["n_programs"], "metadata_sources": v["sources"],
                       "metadata_per_template_norm": v["per_template_norm"], "metadata_is_default": m == fc[t]["D"],
                       "metadata_qwen_only_norm": (qs.get("qwen_only", {}).get(t, {}).get(m) or {}).get("norm")})
    datasets = [{"dataset": "gemma_l1_events", "examples": events},
                {"dataset": "gemma_pt_repertoire", "examples": pt},
                {"dataset": "gemma_twin_tail", "examples": twin},
                {"dataset": "gemma_qlik", "examples": ql},
                {"dataset": "gemma_push_fresh", "examples": push}]
    datasets = [d for d in datasets if d["examples"]]
    meta = {"method_name": "Gemma: base runner-up vs the tuned model's tail (iteration 6, step 5; REPLICATION)",
            "models": {"it": f"{IT_ID}@{IT_REV}", "pt": f"{PT_ID}@{PT_REV}"},
            "commitments": [json.loads(l) for l in (ROOT / "commitments.log").read_text().splitlines() if l.strip()]}
    for name in ("l1_contest", "old_tally", "l2", "push_descriptives", "pt_repertoire", "l3", "pt_label_audit6",
                 "it_regate6", "novelty_audit6", "engine_check6", "tests_gpu_it6", "tests_cpu6", "clean_state_check",
                 "qlik_numerics", "qlik_selection", "rederive_l1", "costs6", "timing6", "deviations", "verdicts6"):
        d = safe(RESULTS_DIR / f"{name}.json")
        if d is None:
            continue
        if name == "l1_contest":
            d = {k: ({kk: vv for kk, vv in v.items() if kk != "logscore_table"} if isinstance(v, dict) else v)
                 for k, v in d.items()}
        if name in ("pt_label_audit6", "it_regate6"):
            d = {k: v for k, v in d.items() if not k.startswith("rows")}
        if name == "novelty_audit6":
            d = {k: ({kk: vv for kk, vv in v.items() if kk != "rows"} if isinstance(v, dict) else v) for k, v in d.items()}
        meta[name] = d
    write_json(ROOT / "method_out.json", {"metadata": meta, "datasets": datasets}, indent=None)
    print({d["dataset"]: len(d["examples"]) for d in datasets})


if __name__ == "__main__":
    main()
