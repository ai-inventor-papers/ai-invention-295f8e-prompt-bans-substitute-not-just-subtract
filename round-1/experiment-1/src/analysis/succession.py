#!/usr/bin/env python3
"""Step 10: greedy cumulative-ban succession, lockstep across tasks (both advance one step per GPU round).

Step 1 = ban:modal from the single-ban arms (not re-run). realised(step) = modal compliant label if its share
leads the runner-up by >= 15 points, else 'no clear mode'. Next banned mode = realised mode, or (no clear mode)
the plurality compliant catalogue label (ties: higher baseline f, then alphabetical; flagged). A task stops after
4 steps, when survivors are exhausted, after two consecutive no-clear-mode steps, when the plurality compliant
label is 'other' (novelty event), or with < 20 compliant samples (ban failure). For every step k >= 2 the
predictions file is written and hash-chained BEFORE its samples are generated.
"""

from __future__ import annotations

import json
from typing import Any

from loguru import logger

from analysis.metrics import event_outcome
from analysis.stages import (ASSOC_FILE, BASELINE_FILE, RAW_SUCC, event_prediction, labelled_rows)
from common import MODES, OTHER, PRED_DIR, RESULTS_DIR, ROOT, TASKS, THRESHOLDS, commit_file, write_json

MAX_STEPS = 4


def _next_ban(task: str, out: dict[str, Any], base: dict[str, Any]) -> tuple[str | None, str]:
    if out["n_compliant"] < THRESHOLDS["min_compliant"]:
        return None, "ban_failure_lt20_compliant"
    if out["plurality"] == OTHER:
        return None, "novelty_other_plurality"
    if out["realised_mode"] not in ("no clear mode", OTHER):
        return out["realised_mode"], "realised"
    counts = out["realised_counts"]
    f = base[task]["baseline"]["freq"]["f"]
    cands = [y for y in out["survivors"] if counts.get(y, 0) > 0]
    if not cands:
        return None, "no_compliant_catalogue_label"
    mx = max(counts[y] for y in cands)
    tied = [y for y in cands if counts[y] == mx]
    pick = sorted(tied, key=lambda y: (-f.get(y, 0.0), y))[0]
    return pick, ("plurality_tiebreak" if len(tied) > 1 else "plurality_no_clear_mode")


def stage_succession() -> None:
    from gen.prompts import make_prompt, succession_segments
    from gen.run_vllm import run_requests
    from method import program_req
    from pipeline import stage_label

    assoc = json.loads(ASSOC_FILE.read_text())
    base = json.loads(BASELINE_FILE.read_text())
    state: dict[str, Any] = {}
    for task in TASKS:
        modal = base[task]["baseline"]["modal"]
        rows = labelled_rows({f"ban:{modal}"}, task)
        out = event_outcome(task, rows, [modal])
        nxt, why = _next_ban(task, out, base)
        state[task] = {"steps": [{"step": 1, "banned": [modal], "condition": f"ban:{modal}", "outcome": out,
                                  "next": nxt, "next_rule": why}],
                       "banned": [modal], "active": nxt is not None, "stop_reason": None if nxt else why,
                       "no_clear_streak": int(out["realised_mode"] == "no clear mode")}
        logger.info(f"{task} step 1 ban:{modal}: realised={out['realised_mode']} compliance={out['compliance']:.2f} "
                    f"n_compliant={out['n_compliant']} next={nxt} ({why})")
    for k in range(2, MAX_STEPS + 1):
        active = [t for t in TASKS if state[t]["active"]]
        if not active:
            break
        reqs = []
        for task in active:
            st = state[task]
            banned = st["banned"] + [st["steps"][-1]["next"]]
            S = [m for m in MODES[task] if m not in banned]
            if not S:
                st["active"] = False
                st["stop_reason"] = "survivors_exhausted"
                continue
            segs = succession_segments(task, banned)
            prompts = [make_prompt(task, s) for s in segs]
            pred = event_prediction(task, banned, assoc, base, f"{task}|succession:{k}")
            pred.update({"step": k, "contest_event": len(S) >= 2, "segments": segs, "prompts": prompts,
                         "kind": "succession_step"})
            p = PRED_DIR / f"{task}_succ_step{k}.json"
            p.write_text(json.dumps(pred, sort_keys=True, indent=1))
            commit_file(p, note=f"{task} succession step {k} predictions frozen before generation")
            st["pending"] = {"banned": banned, "S": S}
            for pid, pr in enumerate(prompts):
                reqs.append(program_req(task, f"succession:{k}", pid, "succession", pr, 10,
                                        extra={"step": k, "banned_set": banned}))
        if not reqs:
            break
        from analysis.stages import assert_committed

        for task in active:
            if state[task].get("pending"):
                assert_committed(PRED_DIR / f"{task}_succ_step{k}.json")
        stats = run_requests(reqs, RAW_SUCC, concurrency=24)
        logger.info(f"succession step {k}: generated {stats}")
        stage_label(str(RAW_SUCC.relative_to(ROOT)))
        for task in active:
            st = state[task]
            if not st.get("pending"):
                continue
            banned = st["pending"]["banned"]
            rows = labelled_rows({f"succession:{k}"}, task)
            out = event_outcome(task, rows, banned)
            nxt, why = (None, "max_steps") if k == MAX_STEPS else _next_ban(task, out, base)
            if len(out["survivors"]) <= 1 and why not in ("max_steps",):
                nxt, why = None, "survivors_exhausted_after_step"
            st["no_clear_streak"] = st["no_clear_streak"] + 1 if out["realised_mode"] == "no clear mode" else 0
            if st["no_clear_streak"] >= 2:
                nxt, why = None, "two_consecutive_no_clear_mode"
            st["steps"].append({"step": k, "banned": banned, "condition": f"succession:{k}", "outcome": out,
                                "next": nxt, "next_rule": why, "contest_event": len(out["survivors"]) >= 2})
            st["banned"] = banned
            st.pop("pending", None)
            if nxt is None:
                st["active"] = False
                st["stop_reason"] = why
            logger.info(f"{task} step {k} banned={banned}: realised={out['realised_mode']} "
                        f"compliance={out['compliance']:.2f} n_compliant={out['n_compliant']} next={nxt} ({why})")
        write_json(RESULTS_DIR / "succession_state.json", state)
    write_json(RESULTS_DIR / "succession_state.json", state)
