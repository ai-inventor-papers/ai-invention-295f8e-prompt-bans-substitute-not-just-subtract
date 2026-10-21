#!/usr/bin/env python3
"""The one-off steps that were run as inline snippets during the original run, kept verbatim as subcommands so the
sequence in reproducibility.md is complete:

  enqueue_initial   first GPU jobs (P0 tests + engine check, twins, novelty, states, base repertoire + plain completion)
  commit0           commit #0 (protocol constants, thresholds, seeds, analysis-code sha256) and commit #E (frozen screen)
  extension         render and audit the A8/A9 prompts (appended to data/prompts_new.jsonl) and enqueue their early draws
  ec_rerun          re-run the T2 twin cell of the engine check into data/raw/enginecheck_T2twin.jsonl

Usage: .venv/bin/python src/manual_steps.py <subcommand>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

UNITS7 = ["A1", "A2", "A3", "A4", "A5", "A6", "A7"]


def enqueue_initial() -> None:
    from jobs import base_job, enginecheck_jobs, enqueue, novelty_job, plainc_job, states_job, twin_job

    enqueue("P0_gputest_instruct_A1", 0, "instruct", "A1", kind="gputest")
    enginecheck_jobs()
    for u in UNITS7:
        twin_job(u, 1)
    for u in UNITS7:
        states_job(u, 2)
        novelty_job(u, 2)
    enqueue("P3_gputest_base_A1", 3, "base", "A1", kind="gputest")
    for u in UNITS7:
        base_job(u, 3)
    for u in UNITS7:
        plainc_job(u, 3)


def commit0() -> None:
    from cfg5 import (ALPHAS, BETA_MOVABLE, DEFAULT_SHARE, DEPTH, ESC_EXCESS, ESC_PASS_FRAC, ESC_SEEDS, EVAL3, ITER4_E,
                      KAPPA_GATE, MIN_CORRECT_BASE, MODELS, P_BINOM, PRED, RT_ADJ_GATE, SRC, V_BLOCKS, sha256_file,
                      utc_now, write_json)
    from commit5 import commit

    proto = {"utc": utc_now(), "panel": "A", "models": MODELS, "precision_rule_file": "predictions/precision_rule.json",
             "esc_seeds": ESC_SEEDS, "alphas": list(ALPHAS), "v_blocks": V_BLOCKS,
             "site": "spec positions, blocks 12-23, prefill only",
             "dose_unit": "ban-free n[l,p] = ||h_twin_clean[l,p]|| * r_Q(l) per template (exp23 units.r_at 'r_Q')",
             "pn_seed": "stable_seed('i5A','PN',task,alpha,w,k)",
             "crn": "u_stream(task, w, k) shared by arms and both models",
             "n": {"twin": 50, "base": 100, "plain": 50, "novelty": 30, "assoc": 20, "stage1": 10, "topup": 20,
                   "pn": 50, "t13": 50},
             "thresholds": {"BETA_MOVABLE": BETA_MOVABLE, "DEFAULT_SHARE": DEFAULT_SHARE, "ESC_EXCESS": ESC_EXCESS,
                            "ESC_PASS_FRAC": ESC_PASS_FRAC, "P_BINOM": P_BINOM, "MIN_CORRECT_BASE": MIN_CORRECT_BASE,
                            "DEPTH": DEPTH, "KAPPA_GATE": KAPPA_GATE, "RT_ADJ_GATE": RT_ADJ_GATE, "pooled_rho": 0.6,
                            "pooled_collapsed_immovable": 0.8, "alpha_one_sided": 0.01, "log_score_margin_nats": 0.10},
             "decision": "panel-level wording only (consistent / not consistent with the pooled thresholds); the "
                         "decision is pooled next round",
             "analysis_code_sha256": {f: sha256_file(SRC / f) for f in ("analysis_a1a2.py", "escape_rule.py",
                                                                        "metrics.py", "cfg5.py")}}
    write_json(PRED / "protocol_commit0.json", proto)
    commit([PRED / "protocol_commit0.json", PRED / "precision_rule.json", SRC / "cfg5.py", SRC / "analysis_a1a2.py",
            SRC / "escape_rule.py", SRC / "metrics.py"], "COMMIT0")
    ce = {"utc": utc_now(), "frozen_screen_file": "inputs/eval3/screen.json",
          "frozen_screen_sha256": sha256_file(EVAL3 / "screen.json"),
          "iteration4_E_t": {t: list(v) for t, v in ITER4_E.items()},
          "iteration4_note": "T03 0.30/0.63, T10 0.38/0.73, T2 0.18/0.20, T05 0/0.13, T1 0.05/0.13, 0 on the rest "
                             "(exp22 bench unit, ban unit)",
          "verdict_change_rule": "a task's verdict changes when MOVABLE_obs (E_t(ban-free, 8 directions x alpha {1,2}, "
                                 "two-stage confirmation) > 0) differs from the frozen screen's 'movable' flag; both "
                                 "directions of change are reported",
          "positive_control": "if T03 AND T10 both give E = 0 at alpha 2, new-unit pushes stop until the hook/unit is "
                              "debugged"}
    write_json(PRED / "commitE.json", ce)
    commit([PRED / "commitE.json", EVAL3 / "screen.json"], "COMMITE")


def extension() -> None:
    from cfg5 import RESULTS, read_jsonl, write_json, write_jsonl
    from jobs import base_job, enqueue, novelty_job, plainc_job, states_job, twin_job
    from specs5 import PROMPTS_EXISTING, PROMPTS_NEW, audit, build_unit_prompts, load_tokenizer, write_spec

    tok = load_tokenizer()
    rows = read_jsonl(PROMPTS_NEW)
    used = set(r.get("noun") for r in rows if r.get("noun"))
    for r in read_jsonl(PROMPTS_EXISTING):
        if r["kind"] == "twin" and r["segment"].startswith("Do not use"):
            used.add(r["segment"].split()[3].strip(".").lower())
    before = json.dumps(rows)
    new = []
    for u in ("A8", "A9"):
        if any(r["task"] == u for r in rows):
            continue
        write_spec(u)
        new += build_unit_prompts(tok, u, used)
    allrows = rows + new
    assert json.dumps(allrows[:len(rows)]) == before
    rep = audit(allrows)
    assert rep["all_pass"]
    write_jsonl(PROMPTS_NEW, allrows)
    write_json(RESULTS / "prompt_audit.json", rep)
    for u in ("A8", "A9"):
        twin_job(u, 1)
        states_job(u, 2)
        novelty_job(u, 2)
    enqueue("P3_gputest_base_A8", 3, "base", "A8", kind="gputest")
    for u in ("A8", "A9"):
        base_job(u, 3)
        plainc_job(u, 3)


def ec_rerun() -> None:
    from cfg5 import K_TWIN, TEMPLATE_IDS
    from jobs import enqueue

    b = [{"w": w, "spec": [("ECTWIN", K_TWIN)]} for w in TEMPLATE_IDS]
    enqueue("P0_enginecheck_T2_twin_rerun2", 0, "instruct", "T2", b, out_file="enginecheck_T2twin.jsonl")


if __name__ == "__main__":
    cmds = {"enqueue_initial": enqueue_initial, "commit0": commit0, "extension": extension, "ec_rerun": ec_rerun}
    if len(sys.argv) != 2 or sys.argv[1] not in cmds:
        print(__doc__)
        sys.exit(2)
    cmds[sys.argv[1]]()
