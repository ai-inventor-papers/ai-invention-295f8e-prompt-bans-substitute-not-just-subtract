#!/usr/bin/env python3
"""Controller loop (CPU): keeps the GPU queue fed.
- Extra arm A (P6, requires COMMIT0 + COMMITE): fresh twin + escape stage 1 per existing task, T03 and T10 first.
- New units (P5, requires COMMIT0 + UNIT_<u>): escape stage 1, PN alpha 1 / 2; T 1.3 at P7.
- Escape top-ups: once a task's twin and stage-1 rows are all labelled, the frozen escape rule picks the screen
  passers and their k 2-5 top-up job is enqueued (same priority class as the task).
- Positive control: if T03 and T10 both show no stage-1 screen passer at alpha 2 and no confirmed escape, new-unit
  pushes are paused (queue/PAUSE_NEWPUSH) and the event is logged for debugging (never retuned).
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from loguru import logger  # noqa: E402

from cfg5 import (ALPHAS, ESC_SEEDS, EXISTING, EXISTING_DEFAULT, K_STAGE1, LAB_DIR, NEW_UNITS, PRED, QUEUE,  # noqa
                  RAW_DIR, RESERVE_UNITS, RESULTS, TEMPLATE_IDS, append_jsonl, read_json, read_jsonl, setup_logging,
                  utc_now)
from commit5 import tags  # noqa: E402
from jobs import escape_stage1_job, pn_job, t13_job, topup_job, twin_job  # noqa: E402


def labelled_ids(task: str) -> set[str]:
    return {r["sample_id"] for r in read_jsonl(LAB_DIR / f"{task}.jsonl")}


def raw_ids(task: str, pred) -> set[str]:
    return {r["sample_id"] for r in read_jsonl(RAW_DIR / f"{task}.jsonl") if pred(r)}


def stage1_complete(task: str) -> bool:
    n_expected = len(ESC_SEEDS) * len(ALPHAS) * len(K_STAGE1) * len(TEMPLATE_IDS)
    ids = raw_ids(task, lambda r: r["arm"].startswith("ESC_") and int(r["slot"]) in K_STAGE1)
    tw = raw_ids(task, lambda r: r["arm"] == "TWIN")
    if len(ids) < n_expected or len(tw) < 50:
        return False
    lab = labelled_ids(task)
    return ids <= lab and tw <= lab


def default_of(task: str) -> tuple[str | None, list[str]]:
    from analysis_a1a2 import catalogue

    if task in EXISTING_DEFAULT:
        return EXISTING_DEFAULT[task], catalogue(task)
    p = PRED / f"unit_{task}.json"
    if p.exists():
        j = read_json(p)
        return j.get("default"), j.get("catalogue") or catalogue(task)
    return None, catalogue(task)


def enqueue_topups(task: str, prio: int, req: list[str]) -> list:
    from analysis_a1a2 import labels, rows_of
    from escape_rule import escape_table

    d, cat = default_of(task)
    if d is None:
        return []
    rows = labels(task)
    tab = escape_table(rows_of(rows, prefix="ESC_", model="instruct"), rows_of(rows, "TWIN", "instruct"), ESC_SEEDS,
                       ALPHAS, set(cat), d)
    passers = tab["passers"]
    append_jsonl(RESULTS / "screen_passers.jsonl", [{"task": task, "utc": utc_now(), "passers": passers,
                                                       "twin": {k: tab["twin"][k] for k in ("share", "pass", "n")}}])
    if passers:
        topup_job(task, passers, prio, req)
    return passers


def positive_control_failed() -> bool | None:
    from analysis_a1a2 import labels, rows_of
    from escape_rule import escape_table

    res = []
    for t in ("T03", "T10"):
        if not stage1_complete(t):
            return None
        d, cat = default_of(t)
        rows = labels(t)
        tab = escape_table(rows_of(rows, prefix="ESC_"), rows_of(rows, "TWIN", "instruct"), ESC_SEEDS, ALPHAS,
                           set(cat), d)
        a2 = [c for c in tab["cells"] if c["alpha"] == 2.0]
        res.append(not any(c["screen_pass"] for c in a2))
    return all(res)


def tick(state: dict) -> None:
    tg = tags()
    if "COMMIT0" in tg and "COMMITE" in tg and not state.get("extra_enqueued"):
        for t in EXISTING:
            twin_job(t, 6, requires=["COMMIT0", "COMMITE"], tag="xa_twin")
            escape_stage1_job(t, 6, requires=["COMMIT0", "COMMITE"])
        state["extra_enqueued"] = True
        logger.info("Extra arm A enqueued (P6)")
    for u in NEW_UNITS + RESERVE_UNITS:
        if f"UNIT_{u}" in tg and u not in state.setdefault("unit_enqueued", []):
            if not (QUEUE / "PAUSE_NEWPUSH").exists():
                req = ["COMMIT0", f"UNIT_{u}"]
                escape_stage1_job(u, 5, req)
                pn_job(u, 1.0, 5, req)
                pn_job(u, 2.0, 5, req)
                t13_job(u, 7, req)
                state["unit_enqueued"].append(u)
                logger.info(f"{u}: push arms enqueued")
    for t in EXISTING + NEW_UNITS + RESERVE_UNITS:
        if t in state.setdefault("topped", []):
            continue
        is_new = t not in EXISTING
        if is_new and f"UNIT_{t}" not in tg:
            continue
        if not is_new and "COMMITE" not in tg:
            continue
        if stage1_complete(t):
            req = ["COMMIT0", f"UNIT_{t}"] if is_new else ["COMMIT0", "COMMITE"]
            ps = enqueue_topups(t, 5 if is_new else 6, req)
            state["topped"].append(t)
            logger.info(f"{t}: stage 1 complete; passers {ps}")
    if not state.get("pc_checked"):
        pc = positive_control_failed()
        if pc is not None:
            state["pc_checked"] = True
            append_jsonl(RESULTS / "positive_control.jsonl", [{"utc": utc_now(), "both_fail_alpha2_stage1": pc}])
            if pc:
                (QUEUE / "PAUSE_NEWPUSH").write_text(utc_now())
                logger.error("POSITIVE CONTROL FAILED: T03 and T10 show no alpha-2 screen passer; new pushes paused")


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--every", type=float, default=30.0)
    ap.add_argument("--once", action="store_true")
    args = ap.parse_args()
    setup_logging("controller")
    sp = RESULTS / "controller_state.json"
    state = read_json(sp) if sp.exists() else {}
    from cfg5 import write_json
    while True:
        try:
            tick(state)
        except Exception as e:  # noqa: BLE001 - keep the loop alive; the error is logged
            logger.exception(f"controller tick failed: {e}")
        write_json(sp, state)
        if args.once or (QUEUE / "STOP").exists():
            break
        time.sleep(args.every)


if __name__ == "__main__":
    main()
