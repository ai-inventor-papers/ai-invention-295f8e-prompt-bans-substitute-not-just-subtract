#!/usr/bin/env python3
"""Ban-free predictors (CPU): escape screen (stage 1 + binomial confirmation -> E_t, MOVABLE), rivals (twin modal
share, can_max, off-default shares of T 1.3 / novelty / PN alpha 1 / PN alpha 2, opening margin), and the four
landing forecasts (push-landing, opening ladder, association, proximity).

Label conventions: off-default = label not in {D, 'invalid', 'disputed'} over ALL attempts (catalogue survivors and
'other'; 'disputed' rows -- unresolved runtime/AST disagreements -- are never counted as off-default). Pass = hidden
tests all passed. Shares are over all attempts of the cell.
"""

from __future__ import annotations

import collections
import json
import re
import sys
from pathlib import Path
from typing import Any

import numpy as np
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg import (ALPHAS, BINOM_ALPHA, DATA_DIR, ESCAPE_EXCESS, ESCAPE_PASS_FRAC, ESCAPE_SEEDS, P0_FLOOR, PATH_TASKS,
                 PRED_DIR, RESULTS_DIR, read_json, read_jsonl)

NOT_OFF = ("invalid", "disputed")


def c1() -> dict[str, Any]:
    return read_json(PRED_DIR / "commit1.json")


def D_of(t: str) -> str:
    return c1()["pilot"][t]["D_g"]


_LAB: dict[str, Any] = {}


def labels(refresh: bool = False) -> dict[str, dict[str, Any]]:
    if refresh or "x" not in _LAB:
        _LAB["x"] = {r["row_id"]: r for r in read_jsonl(DATA_DIR / "labels.jsonl")}
    return _LAB["x"]


def rows(stage: str | None = None, task: str | None = None, arm: str | None = None,
         arm_prefix: str | None = None) -> list[dict[str, Any]]:
    out = []
    for r in labels().values():
        if stage and r.get("stage") != stage:
            continue
        if task and r.get("task") != task:
            continue
        if arm and r.get("arm") != arm:
            continue
        if arm_prefix and not str(r.get("arm", "")).startswith(arm_prefix):
            continue
        out.append(r)
    return out


def off_share(rr: list[dict[str, Any]], D: str) -> float:
    if not rr:
        return float("nan")
    return sum(1 for r in rr if r["label"] not in (D,) + NOT_OFF) / len(rr)


def pass_rate(rr: list[dict[str, Any]]) -> float:
    return sum(1 for r in rr if r.get("passed")) / len(rr) if rr else float("nan")


def twin_rows(t: str) -> list[dict[str, Any]]:
    return [r for r in rows("A", t, "twin")]


def D_final(t: str) -> dict[str, Any]:
    """After the full twin N=50: D = modal correct label; if it differs from D_g it is used for all analyses."""
    import prompts_gemma as PG

    tw = twin_rows(t)
    Dg = D_of(t)
    cat = set(PG.modes(t))
    # same rule as commit #1: D must be a catalogue mode (the ban names it) with >= 3 correct twin programs
    cnt = collections.Counter(r["label"] for r in tw if r.get("passed") and r["label"] in cat)
    if not cnt or max(cnt.values()) < 3:
        return {"D": Dg, "D_g": Dg, "changed": False, "n_correct": sum(cnt.values()), "counts": dict(cnt)}
    top = max(cnt.values())
    tops = sorted(m for m, c in cnt.items() if c == top)
    D = Dg if Dg in tops else tops[0]
    return {"D": D, "D_g": Dg, "changed": D != Dg, "n_correct": sum(cnt.values()), "counts": dict(cnt)}


def esc_rows(t: str, seed: int, alpha: float, stage: str | None = None) -> list[dict[str, Any]]:
    arm = f"esc{seed}_a{int(alpha)}"
    out = [r for r in rows("A", t, arm)]
    if stage is None or stage == "AB":
        out += [r for r in rows("B", t, arm)]
    return out


def stage1(t: str) -> dict[str, Any]:
    D = D_final(t)["D"]
    tw = twin_rows(t)
    p0, pt = off_share(tw, D), pass_rate(tw)
    cells, passing = {}, []
    for s in ESCAPE_SEEDS:
        for a in ALPHAS:
            rr = esc_rows(t, s, a, stage="A")
            sh, pr = off_share(rr, D), pass_rate(rr)
            ok = bool(rr) and (sh - p0 >= ESCAPE_EXCESS) and (pr >= ESCAPE_PASS_FRAC * pt)
            cells[f"{s}_a{int(a)}"] = {"n": len(rr), "off_share": sh, "excess": sh - p0, "pass": pr, "stage1_pass": ok}
            if ok:
                passing.append((s, a))
    return {"D": D, "p0": p0, "twin_pass": pt, "n_twin": len(tw), "cells": cells, "passing": passing}


def confirm(t: str) -> dict[str, Any]:
    st = stage1(t)
    D, p0, pt = st["D"], st["p0"], st["twin_pass"]
    conf = []
    cells = {}
    for (s, a) in st["passing"]:
        rr = esc_rows(t, s, a, stage="AB")
        n = len(rr)
        k = sum(1 for r in rr if r["label"] not in (D,) + NOT_OFF)
        sh, pr = (k / n if n else float("nan")), pass_rate(rr)
        pb = float(stats.binom.sf(k - 1, n, max(p0, P0_FLOOR))) if n else 1.0
        ok = n >= 30 and (sh - p0 >= ESCAPE_EXCESS) and (pr >= ESCAPE_PASS_FRAC * pt) and pb < BINOM_ALPHA
        cells[f"{s}_a{int(a)}"] = {"n": n, "k_off": k, "off_share": sh, "excess": sh - p0, "pass": pr,
                                   "binom_p": pb, "confirmed": ok}
        if ok:
            conf.append((s, a))
    E = {}
    for a in ALPHAS:
        E[f"a{int(a)}"] = sum(1 for (s, aa) in conf if aa == a) / len(ESCAPE_SEEDS)
    Et = max(E.values()) if E else 0.0
    kmax = int(round(Et * len(ESCAPE_SEEDS)))
    lo, hi = stats.binomtest(kmax, len(ESCAPE_SEEDS)).proportion_ci(method="exact") if True else (0, 0)
    return {**st, "confirm_cells": cells, "confirmed": conf, "E_alpha": E, "E_t": Et, "E_t_ci95": [lo, hi],
            "movable": Et > 0, "n_directions_run": len(ESCAPE_SEEDS)}


# ------------------------------------------------------------------------------------------------ rivals
def can_max(t: str, D: str) -> dict[str, Any]:
    rr = rows("D", t, "can")
    by = collections.defaultdict(list)
    for r in rr:
        by[r.get("mode")].append(r)
    sh = {m: sum(1 for r in v if r.get("passed") and r["label"] == m) / len(v) for m, v in by.items() if m != D}
    return {"can_max": max(sh.values()) if sh else None, "per_mode": sh, "n": len(rr)}


def rivals(t: str, D: str, ladder: dict[str, Any] | None) -> dict[str, Any]:
    tw = twin_rows(t)
    cnt = collections.Counter(r["label"] for r in tw)
    corr = [r for r in tw if r.get("passed")]
    cc = collections.Counter(r["label"] for r in corr)
    out = {"twin_modal_share": (cnt.most_common(1)[0][1] / len(tw)) if tw else None,
           "twin_modal_share_correct": (cc.most_common(1)[0][1] / len(corr)) if corr else None,
           "twin_default_share": (cnt.get(D, 0) / len(tw)) if tw else None}
    out.update({"can": can_max(t, D)})
    out["can_max"] = out["can"]["can_max"]
    for key, arm, stage in (("t13_off", "t13", "A"), ("pn_a1_off", "pn_a1", "A"), ("pn_a2_off", "pn_a2", "A"),
                            ("novelty_off", "novelty", "C")):
        rr = rows(stage, t, arm)
        out[key] = off_share(rr, D) if rr else None
        out[key.replace("_off", "_pass")] = pass_rate(rr) if rr else None
        out[key.replace("_off", "_n")] = len(rr)
    out["opening_margin"] = (ladder or {}).get("margin")
    return out


# ------------------------------------------------------------------------------------------------ forecasts
def survivors(t: str, D: str) -> list[str]:
    import prompts_gemma as PG

    return [m for m in PG.modes(t) if m != D]


def push_landing(t: str, conf: dict[str, Any]) -> dict[str, Any]:
    D = conf["D"]
    S = survivors(t, D)
    w = collections.Counter()
    for (s, a) in conf["confirmed"]:
        rr = esc_rows(t, s, a, stage="AB")
        ex = conf["confirm_cells"][f"{s}_a{int(a)}"]["excess"]
        c = collections.Counter(r["label"] for r in rr if r["label"] in S)
        for m, k in c.items():
            w[m] += ex * k
    src = "confirmed_escapes"
    if sum(w.values()) == 0:
        src = "fallback_all_push_rows"
        rr = [r for r in labels().values() if r["task"] == t and r.get("stage") in ("A", "B")
              and str(r.get("arm", "")).startswith(("esc", "pn_"))]
        w = collections.Counter(r["label"] for r in rr if r["label"] in S)
    tot = sum(w.values())
    if tot == 0:
        return {"defined": False, "source": "undefined", "distribution": {m: 1 / len(S) for m in S} if S else {},
                "top1": None}
    dist = {m: w.get(m, 0) / tot for m in S}
    return {"defined": True, "source": src, "distribution": dist, "top1": max(dist, key=dist.get)}


T12_LEX = {
    "T1": {"bfs": ["breadth-first", "breadth first", "bfs"], "dfs": ["depth-first", "depth first", "dfs"],
           "bibfs": ["bidirectional bfs", "bidirectional breadth", "bidirectional search", "bidirectional"],
           "iddfs": ["iterative deepening", "iddfs"], "astar_gbfs": ["a*", "a-star", "a star", "best-first", "greedy best"],
           "dijkstra": ["dijkstra"]},
    "T2": {"dijkstra": ["dijkstra"], "bf_spfa": ["bellman-ford", "bellman ford", "bellman", "spfa", "shortest path faster"],
           "bidijkstra": ["bidirectional dijkstra", "bidirectional"], "floyd": ["floyd", "warshall"],
           "dial": ["dial's", "dial ", "bucket queue", "bucket-queue", "bucket"]},
}


def mentions(t: str, text: str) -> dict[str, int]:
    if t in PATH_TASKS:
        low = (text or "").lower()
        pos = {}
        for m, ph in T12_LEX[t].items():
            for p in ph:
                for mm in re.finditer(r"(?<![a-z0-9])" + re.escape(p), low):
                    pos[m] = min(pos.get(m, 10 ** 9), mm.start())
        return pos
    from bench.common.order import mentions as bm

    return bm(t, text or "")


def association(t: str, D: str) -> dict[str, Any]:
    ans = [r for r in read_jsonl(DATA_DIR / "assoc_answers.jsonl") if r["task"] == t]
    S = survivors(t, D)
    mapped = []
    for r in ans:
        pos = mentions(t, r["text"])
        surv = {m: p for m, p in pos.items() if m != D and m in S}
        if surv:
            mapped.append(min(surv, key=surv.get))
        elif D in pos:
            mapped.append("names_D")
        else:
            mapped.append("unmapped")
    c = collections.Counter(mapped)
    cs = {m: c.get(m, 0) for m in S}
    tot = sum(cs.values()) + len(S)
    dist = {m: (cs[m] + 1) / tot for m in S}
    defined = sum(cs.values()) > 0
    top = max(cs, key=cs.get) if defined else None
    return {"defined": defined, "distribution": dist, "top1": top, "counts": dict(c), "n": len(ans)}


def proximity(t: str, D: str, max_each: int = 20, max_pairs: int = 120) -> dict[str, Any]:
    """Median Zhang-Shasha distance (identifier-normalised ASTs) between correct adherent forced programs of each
    survivor (bench forced_programs; T1/T2: exp8 references) and correct D-labelled twin programs of this model."""
    import random
    from concurrent.futures import ProcessPoolExecutor
    import multiprocessing as mp

    from cfg import BENCH, SUITE

    S = survivors(t, D)
    twin = [r["code"] for r in twin_rows(t) if r.get("passed") and r["label"] == D and r.get("code")][:max_each]
    forced: dict[str, list[str]] = collections.defaultdict(list)
    if t in PATH_TASKS:
        sub = {"T1": "t1_grid", "T2": "t2_wsp"}[t]
        pref = {"T1": [("bfs", "bfs"), ("bibfs", "bibfs"), ("dfs", "dfs"), ("iddfs", "iddfs"),
                       ("astar", "astar_gbfs"), ("gbfs", "astar_gbfs"), ("dijkstra", "dijkstra")],
                "T2": [("bellman", "bf_spfa"), ("spfa", "bf_spfa"), ("bidijkstra", "bidijkstra"), ("dial", "dial"),
                       ("dijkstra", "dijkstra"), ("floyd", "floyd")]}[t]
        for f in sorted((SUITE / "tasks" / sub / "references").glob("*.py")):
            m = next((mode for p, mode in pref if f.stem.startswith(p)), None)
            if m:
                forced[m].append(f.read_text())
    else:
        from bench.common.catalogue import TASKS

        for r in read_jsonl(BENCH / TASKS[t]["task_id"] / "forced_programs.jsonl"):
            if str(r.get("passed")) == "True" and r.get("label") == r.get("forced_mode") and r.get("code"):
                forced[r["forced_mode"]].append(r["code"])
    if not twin:
        return {"defined": False, "reason": "no correct D twin programs", "distribution": {m: 1 / len(S) for m in S},
                "top1": None}
    rng = random.Random(f"prox|{t}")
    jobs, owner = [], []
    for m in S:
        fs = forced.get(m, [])[:max_each]
        pairs = [(a, b) for a in fs for b in twin]
        rng.shuffle(pairs)
        for p in pairs[:max_pairs]:
            jobs.append(p)
            owner.append(m)
    from prox import zs_pair

    with ProcessPoolExecutor(max_workers=3, mp_context=mp.get_context("spawn")) as ex:
        ds = list(ex.map(zs_pair, [a for a, _ in jobs], [b for _, b in jobs], chunksize=8))
    by = collections.defaultdict(list)
    for m, d in zip(owner, ds):
        if d is not None:
            by[m].append(d)
    med = {m: float(np.median(v)) for m, v in by.items() if v}
    if not med:
        return {"defined": False, "reason": "no forced programs", "distribution": {m: 1 / len(S) for m in S},
                "top1": None}
    scale = float(np.median(list(med.values()))) or 1.0
    z = {m: -med[m] / scale for m in med}
    mx = max(z.values())
    e = {m: np.exp(z[m] - mx) for m in z}
    tot = sum(e.values())
    dist = {m: float(e.get(m, 0.0) / tot) for m in S}
    return {"defined": True, "median_distance": med, "distribution": dist, "top1": min(med, key=med.get),
            "n_pairs": {m: len(v) for m, v in by.items()}, "missing_modes": [m for m in S if m not in med]}
