#!/usr/bin/env python3
"""Commit #2 (BEFORE ANY AV CALL on a task state): Y* per task, eligibility, the forced conditions read out, the
frozen alias lexicon, the judge prompts / models / calibration set, thresholds, the readout and edit-pool state lists,
the causal plan and cells, and the sha256 of the committed analysis code."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from loguru import logger

from cfg import (ADHERENT_MIN, CACHE_DIR, DOSES, FVE_PARTIAL, FVE_PASS, PRED_DIR, RESULTS_DIR, ROOT, TASKS,
                 read_json, read_jsonl, setup_logging, sha256_file)
from commit import commit
import prompts as PR

CAUSAL_PRIORITY = ("T2", "T1", "T10", "T03", "T05")
# fallback fill (deviation D-causal-tasks): when the priority list yields fewer than 4 tasks with an admissible Y,
# the remaining defaulted bench tasks fill the 4-task cap in bench order
CAUSAL_FILL = ("T06", "T04", "R6")
CELLS = {
    "PRE": [f"PRE_{k}_x{int(d)}" for k in ("EDIT", "RT", "UNREL", "RAND", "DIM") for d in DOSES],
    "GEN": ["GEN_EDIT_x1", "GEN_EDIT_x2", "GEN_RAND_x1", "GEN_RAND_x2"],
    "REV": ["REV_EDIT_x2", "REV_EDIT_x4", "REV_RAND_x2", "REV_RAND_x4"],
    "C0": "S3 TWIN rows of slots 0-5 (identity hook byte-identical, S2b); C0_ban = S3 BAN rows of slots 0-5",
}


def main() -> dict[str, Any]:
    setup_logging("commit2")
    from behaviour import per_task_report
    from judges import JUDGES, RUBRIC_VERSION, calibration_items, prompt_expl, prompt_predict

    rep = per_task_report()
    c1 = read_json(PRED_DIR / "commit1_defaults.json")
    rg = read_json(RESULTS_DIR / "regate.json")
    cal = read_json(RESULTS_DIR / "judge_calibration.json")
    idx = read_jsonl(CACHE_DIR / "states_index.jsonl")
    tasks: dict[str, Any] = {}
    for t in TASKS:
        R = rep["tasks"][t]
        D = c1["tasks"][t]["default"]
        rpass = rg["tasks"][t]["pass"]
        ys = R.get("Ystar")
        adh = {m: v["adherence"] for m, v in R["forced"].items() if v["adherence"] is not None}
        if D:
            modes = [D] + ([ys] if ys else [])
        else:
            tw = [m for m in R["twin"]["correct"] if m not in ("other", "invalid")]
            modes = tw[:2]
        others = sorted([m for m in adh if m not in modes], key=lambda m: -adh[m])
        if others:
            modes.append(others[0])
        tasks[t] = {"default": D, "Ystar": ys, "regate_pass": rpass, "eligible": bool(rpass and D and ys),
                    "ban_failure": bool(D and not ys), "forced_readout_modes": modes, "forced_adherence": adh,
                    "twin_mixed": c1["tasks"][t]["mixed"], "ban_mixed": R.get("ban_mixed")}
    # readout states: prefill twin / ban / 3 forced / seed; all generated; all random
    sel, pool = [], []
    for r in idx:
        t = r.get("task")
        if r["kind"] == "PREFILL":
            if r["condition"] == "forced" and r["mode"] not in tasks[t]["forced_readout_modes"]:
                continue
            sel.append(r["state_id"])
            if r["condition"] == "twin":
                pool.append(r["state_id"])
        elif r["kind"] in ("GEN", "RAND"):
            sel.append(r["state_id"])
    # causal plan
    plan = []
    for t in CAUSAL_PRIORITY + CAUSAL_FILL:
        v = tasks[t]
        if not v["default"] or not v["regate_pass"]:
            continue
        if v["Ystar"]:
            Y, src = v["Ystar"], "Ystar"
        else:
            twc = rep["tasks"][t]["twin"]["correct"]
            # tie-break on equal adherence: the model's own twin share of the mode
            cand = sorted([(a, twc.get(m, 0), m) for m, a in v["forced_adherence"].items()
                           if m != v["default"] and a >= ADHERENT_MIN], reverse=True)
            if not cand:
                continue
            Y, src = cand[0][2], "best_forced_adherent"
        plan.append({"task": t, "default": v["default"], "Y": Y, "Y_source": src})
    plan = plan[:4]
    lex = {t: {c["mode"]: sorted(set([c["display_name"]] + c["aliases"])) for c in PR.catalogue(t)} for t in TASKS}
    code = {p: sha256_file(ROOT / p) for p in ("analysis/readout.py", "analysis/causal.py", "analysis/stats.py",
                                               "src/judges.py", "src/nla_av.py", "src/nla_ar.py", "src/causal_gen.py")
            if (ROOT / p).exists()}
    obj = {"tasks": tasks, "eligible_tasks": [t for t, v in tasks.items() if v["eligible"]],
           "lexicon": lex, "readout_state_ids": sel, "edit_pool_state_ids": pool,
           "n_readout_states": len(sel), "n_explanations_planned": 3 * len(sel) + 3 * len(pool),
           "judges": cal["final"], "rubric_version": RUBRIC_VERSION,
           "judge_prompt_expl_example": prompt_expl("T2", "<TEXT>"), "judge_prompt_predict_example": prompt_predict("T2", "<TEXT>"),
           "calibration_synthetic": calibration_items(),
           "calibration_forced_rule": "the first 30 forced-state explanations (#1) in sorted state-id order are judged as "
                                      "the 30 forced items (reported, not gated; they do not exist before the AV runs)",
           "thresholds": {"N1_effect": 0.30, "alpha": 0.05, "N3": 0.7, "gate_pass": FVE_PASS, "gate_partial": FVE_PARTIAL,
                          "causal_excess": 0.20, "causal_over_controls": 0.10, "causal_tasks": 2},
           "causal_plan": plan, "causal_cells": CELLS, "analysis_code_sha256": code,
           "regate": {t: (v["agree"], v["n"], v["pass"]) for t, v in rg["tasks"].items()}}
    rec = commit("commit2_readout", obj)
    logger.info(f"commit2: eligible {obj['eligible_tasks']}; causal {plan}; {len(sel)} readout states; "
                f"{obj['n_explanations_planned']} explanations planned")
    return rec


if __name__ == "__main__":
    main()
