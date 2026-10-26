"""4a PROMPT REACH: leave-one-survivor (LOS) ban lists on the bench tasks and two-step bans {D, R2} on all tasks,
plus the forecasts committed before them (S5): rung table, C3 cells, list-independence prediction (after walk
step 1) and the two-step forecasts WALK2 / ASSOCIATE / SNAPBACK (after walk step 2).
"""

from __future__ import annotations

import json
from collections import Counter
from typing import Any

from loguru import logger

from commit import commit_file, commit_json
from config import (BENCH_DIR, C3_CAN_MIN, C3_DISCONFIRM, C3_WILL_MAX, INPUTS, MAX_TOKENS_SHORT, N_PER_TEMPLATE,
                    N_TWO_STEP_PER_TEMPLATE, PRED, SRC, TASKS, W_IDS, read_jsonl, seed_los, seed_two_step, utc_now)
from programs import can, can_table
from prompts import ban_prompt, los_banned

PATH_SINGLE_BAN_SUBSTITUTE = {"T1": "dfs", "T2": "bf_spfa"}   # exp8/exp9 realised single-ban substitutes


def ban_jobs(task: str, arm: str, cond_id: str, banned: list[str], n_per_template: int, seed_fn) -> list[tuple]:
    jobs = []
    for wi, w in enumerate(W_IDS):
        bp = ban_prompt(task, w, banned)
        for j in range(n_per_template):
            i = wi * n_per_template + j
            s = seed_fn(i)
            meta = {"arm": arm, "task": task, "template": w, "i": i, "seed": s, "prompt_sha256": bp["prompt_sha256"],
                    "cond_id": cond_id, "condition": f"{arm}:{cond_id}", "meta_banned": banned,
                    "meta_segment": bp["segment"]}
            jobs.append((meta, {"prompt_ids": bp["ids"], "seed": s, "max_tokens": MAX_TOKENS_SHORT}))
    return jobs


def los_jobs(task: str) -> list[tuple]:
    jobs = []
    for s_idx, S in enumerate(TASKS[task]["analysis_set"]):
        jobs += ban_jobs(task, "los", f"LOS({S})", los_banned(task, S), N_PER_TEMPLATE,
                         lambda i, s_idx=s_idx: seed_los(task, s_idx, i))
    return jobs


def two_step_jobs(task: str, r2: str) -> list[tuple]:
    D = TASKS[task]["default"]
    return ban_jobs(task, "two_step", f"TWO({D},{r2})", [D, r2], N_TWO_STEP_PER_TEMPLATE,
                    lambda i: seed_two_step(task, i))


def association_modal(task: str, x: str) -> dict[str, Any]:
    if TASKS[task]["family"] != "bench":
        return {"label": None, "note": "no association answers exist for the path tasks"}
    rows = [r for r in read_jsonl(BENCH_DIR / TASKS[task]["task_id"] / "association.jsonl") if r.get("X") == x]
    c = Counter(r.get("mapped") for r in rows)
    if not c:
        return {"label": None, "note": "no rows"}
    lab, k = c.most_common(1)[0]
    return {"label": lab, "share": k / len(rows), "n": len(rows), "counts": dict(c)}


def r2_for(walk) -> dict[str, Any]:
    """R2 = the walk's rung 2 (modal non-vetoed landing at step 1); fallback chain when step 1 stalled."""
    if len(walk.rungs) >= 2 and walk.rungs[1]["label"] not in ("other", "invalid"):
        return {"R2": walk.rungs[1]["label"], "flagged": False, "source": "walk rung 2"}
    st1 = [h for h in walk.history if h["step"] == 1]
    if st1:
        land = Counter(st1[-1]["summary"]["landing"])
        for lab, k in land.most_common():
            if lab != TASKS[walk.task]["default"] and lab in TASKS[walk.task]["catalogue"] and k >= 5:
                return {"R2": lab, "flagged": True, "source": "modal non-default catalogue label at step 1 (>=5)"}
    if TASKS[walk.task]["family"] == "path":
        return {"R2": PATH_SINGLE_BAN_SUBSTITUTE[walk.task], "flagged": True,
                "source": "exp8/exp9 realised single-ban substitute"}
    a = association_modal(walk.task, TASKS[walk.task]["default"])
    return {"R2": a["label"], "flagged": True, "source": "association modal answer for D"}


def rung_table(walk) -> dict[str, Any]:
    t = walk.task
    r2 = r2_for(walk)
    table = {}
    for a in TASKS[t]["catalogue"]:
        if a == TASKS[t]["default"]:
            table[a] = 1
        elif a == r2["R2"]:
            table[a] = 2
        else:
            table[a] = ">=3"
    return {"task": t, "rungs": table, "R2": r2, "walk_status_after_step1": walk.status}


def exp9_los() -> dict[str, Any]:
    return json.loads((INPUTS / "exp9" / "results" / "los.json").read_text())


def c3_cells(walk) -> list[dict[str, Any]]:
    t = walk.task
    rt = rung_table(walk)["rungs"]
    cells = []
    if TASKS[t]["family"] == "bench":
        algos = TASKS[t]["analysis_set"]
    elif t == "T2":
        algos = TASKS[t]["catalogue"]
    else:
        return []
    for S in algos:
        cS = can(t, S)
        if t == "T2":  # exp9 LOS can fields are recomputed as labelled-and-correct from exp9/exp7 forced
            ct = can_table()[t][S]
            if (ct["primary"] or {}).get("n_plain", 0) == 0 and ct["by_source"].get("exp7"):
                cS = ct["by_source"]["exp7"]["can"]
        qualifies = rt.get(S) == ">=3" and cS is not None and cS >= C3_CAN_MIN
        cells.append({"task": t, "S": S, "rung": rt.get(S), "can": cS, "qualifies": qualifies,
                      "prediction": f"will({S}) <= {C3_WILL_MAX}" if qualifies else None,
                      "disconfirming": f"will({S}) >= {C3_DISCONFIRM}" if qualifies else None,
                      "will_source": "exp9 results/los.json (not re-run)" if t == "T2" else "this artifact's LOS"})
    return cells


def list_independence_groups(task: str, D: str, R2: str) -> list[str]:
    groups = [f"LOS({S})" for S in TASKS[task]["analysis_set"] if D in los_banned(task, S) and R2 in los_banned(task, S)]
    return groups + [f"TWO({D},{R2})"]


def commit_reach(walkers: list, group: str) -> dict[str, Any]:
    out = {"utc": utc_now(), "group": group, "tasks": {}}
    for w in walkers:
        rt = rung_table(w)
        cells = c3_cells(w)
        li = None
        if TASKS[w.task]["family"] == "bench" and rt["R2"]["R2"]:
            li = {"groups": list_independence_groups(w.task, w.D, rt["R2"]["R2"]),
                  "statistic": f"share of {w.D} among programs labelled {w.D} or {rt['R2']['R2']}",
                  "test": "permutation chi-square of homogeneity, 10,000 label permutations within task, seed 0",
                  "alpha": 0.05, "prediction": "p >= 0.05 (the reimplementation mix does not depend on the rest of "
                                               "the list)",
                  "descriptive_if": "fewer than 3 groups have >= 10 such programs"}
        out["tasks"][w.task] = {"rung_table": rt, "c3_cells": cells, "list_independence": li,
                                "walk_step1_landing": next((h["summary"]["landing"] for h in reversed(w.history)
                                                            if h["step"] == 1), None)}
    p = PRED / f"reach_forecasts_{group}.json"
    rec = commit_json(p, out, f"reach forecasts ({group}): rungs, C3 cells, list-independence")
    for f in ("analysis.py", "reach.py"):
        if (SRC / f).exists():
            commit_file(SRC / f, f"code sha256 {f} before {group} ban samples")
    logger.info(f"committed {p.name}: chain {rec['chain'][:12]}")
    return out


def commit_two_step(walkers: list, group: str) -> dict[str, Any]:
    out = {"utc": utc_now(), "group": group, "tasks": {}}
    for w in walkers:
        r2 = r2_for(w)["R2"]
        st2 = [h for h in w.history if h["step"] == 2]
        walk2 = st2[-1]["summary"]["landing"] if st2 else None
        walk2_status = "available" if walk2 else f"walk did not reach step 2 (status {w.status})"
        out["tasks"][w.task] = {
            "banned": [w.D, r2], "R2": r2_for(w),
            "WALK2": {"landing_counts": walk2, "status": walk2_status,
                      "top1": Counter(walk2).most_common(1)[0][0] if walk2 else None},
            "ASSOCIATE": {"for_R2": association_modal(w.task, r2), "for_D": association_modal(w.task, w.D)},
            "SNAPBACK": {"top1": w.D, "meaning": "ban failure: the default comes back"},
            "scoring": "frozen C1: mean log score per non-banned attempt (5% uniform over survivors, 2% shared "
                       "'other' floor) and top-1 hit; descriptive"}
    p = PRED / f"two_step_forecasts_{group}.json"
    commit_json(p, out, f"two-step forecasts ({group})")
    return out
