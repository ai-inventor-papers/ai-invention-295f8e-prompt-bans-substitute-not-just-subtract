#!/usr/bin/env python3
"""9.3 C2f: mean-ablation of the three ban-attending heads (L21H17, L26H21, L26H25) at generated positions under the
full ban, against three layer-matched random head sets (CRN, k 0-9 slots); reference = the named ban's k 0-9 slots."""

from __future__ import annotations

from typing import Any

import numpy as np

from analysis.c2d import is_default
from analysis.common import by_slot, mcnemar_one_sided, mcnemar_two_sided, paired, rows_of, shares
from cfg import HEAD_RAND_SEEDS, HEAD_TARGET
from hooks import head_sets

K10 = list(range(10))
RAND_ARMS = [f"HEADS_rand{s}" for s in HEAD_RAND_SEEDS]


def analyse(rows: list[dict[str, Any]], task: str) -> dict[str, Any] | None:
    tgt = rows_of(rows, task, "HEADS_target", K10)
    if not tgt:
        return None
    ban = rows_of(rows, task, "BAN", K10)
    out: dict[str, Any] = {"arms": {"BAN_k0_9": shares(ban, task), "HEADS_target": shares(tgt, task)}}
    rnd = {a: rows_of(rows, task, a, K10) for a in RAND_ARMS}
    for a, rs in rnd.items():
        out["arms"][a] = shares(rs, task)
    bshare = {a: 1 - s["avoidance"] for a, s in out["arms"].items()}  # banned (default) share among attempted
    out["banned_share"] = bshare
    mr = [bshare[a] for a in RAND_ARMS if a in bshare]
    out["delta_vs_mean_random"] = bshare["HEADS_target"] - float(np.mean(mr)) if mr else None
    out["delta_vs_max_random"] = bshare["HEADS_target"] - float(np.max(mr)) if mr else None
    out["delta_vs_ban"] = bshare["HEADS_target"] - bshare["BAN_k0_9"]
    # exact paired tests (one-sided H1: target banned share > random banned share) and flip tables vs the ban
    tests = {}
    for a, rs in rnd.items():
        x, y = paired(tgt, rs, fn=is_default)
        tests[a] = mcnemar_one_sided(x, y)
    out["target_vs_random"] = tests
    flips = {}
    for a in ["HEADS_target"] + RAND_ARMS:
        x, y = paired(rows_of(rows, task, a, K10), ban, fn=is_default)
        flips[a] = mcnemar_two_sided(x, y)
    out["flip_vs_ban"] = flips
    # per-slot bootstrap of target - mean(random) (90% and 95% CIs)
    T, Rs = by_slot(tgt), [by_slot(rs) for rs in rnd.values()]
    diffs = []
    for s, r in T.items():
        a = is_default(r)
        rv = [is_default(R[s]) for R in Rs if s in R]
        rv = [v for v in rv if v is not None]
        if a is None or not rv:
            continue
        diffs.append(a - float(np.mean(rv)))
    if diffs:
        d = np.array(diffs)
        rng = np.random.default_rng(3)
        bs = d[rng.integers(0, len(d), (5000, len(d)))].mean(1)
        out["slot_delta"] = {"mean": float(d.mean()), "ci90": [float(np.quantile(bs, 0.05)), float(np.quantile(bs, 0.95))],
                             "ci95": [float(np.quantile(bs, 0.025)), float(np.quantile(bs, 0.975))], "n": len(d)}
    return out


def run_c2f(rows: list[dict[str, Any]]) -> dict[str, Any]:
    res = {t: analyse(rows, t) for t in ("T1", "T2")}
    out: dict[str, Any] = {"per_task": res, "head_sets": {"target": HEAD_TARGET, **head_sets(HEAD_RAND_SEEDS)},
                           "ablation": "mean-ablation of the o_proj-input slice of each head at generated positions "
                                       "(decode steps only), mean over the task's 100 NEUTRAL programs"}
    t1, t2 = res.get("T1"), res.get("T2")
    if t1 and t2:
        d1 = t1["delta_vs_mean_random"]
        sig = all(v["p_one_sided"] < 0.05 for v in t1["target_vs_random"].values())
        d2 = t2["delta_vs_mean_random"]
        out["verdict"] = "SUPPORTED" if (d1 is not None and d1 >= 0.15 and sig and d2 is not None and abs(d2) <= 0.10) \
            else "NOT SUPPORTED"
        out["delta_T1"] = d1
        out["delta_T2"] = d2
        out["t1_all_random_p_lt_005"] = sig
    else:
        out["verdict"] = "NOT RUN"
    return out
