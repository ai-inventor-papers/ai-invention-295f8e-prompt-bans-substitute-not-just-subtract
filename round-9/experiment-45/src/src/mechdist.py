#!/usr/bin/env python3
"""N5 inputs (plan 1.12): mechanism and name distances between algorithms, and the committed rotated-set rule.

D_mech(a, b) = 0.5 * D_order + 0.25 * D_set + 0.25 * D_ds, averaged over the references of a and b and the 40 probes:
  D_order = normalised Kendall distance of the two expansion sequences (first occurrences) on commonly expanded cells
            (0.5 if fewer than 5 common cells); D_set = 1 - Jaccard of the expanded sets; D_ds = Hamming distance over
            {container, key, restarts, bidirectional} / 4.
D_name(a, b) = 1 - max over alias pairs of the term Jaccard after removing stopwords; any short-form regex
  cross-match counts as overlap 1.
SET RULE: candidates are the 125 five-sets containing BFS other than the literal set. Type M: some non-banned a has
  min_b D_mech(a, b) <= q25 of the off-diagonal D_mech AND min_b D_name(a, b) >= q75 of D_name. Type L: the reverse.
  Pick 3 type-M-only, 2 type-L-only and 1 more by greedy farthest-point selection on set Jaccard distance (seed 0,
  lexicographic tie-break); relax to terciles if too few qualify. R1..R6 in selection order.
"""

from __future__ import annotations

import itertools
import random
import re
from typing import Any

import numpy as np
from scipy.stats import kendalltau

from common import ALIAS_TABLE, CANON_ORDER, LITERAL5, SHORT_FORMS

REFS_OF = {"bfs": ["bfs_deque_parent", "bfs_listpop_pathcarry"], "dfs": ["dfs_recursive", "dfs_stack"],
           "bibfs": ["bibfs_deques", "bibfs_sets"], "iddfs": ["iddfs_iterative", "iddfs_recursive"],
           "astar": ["astar_fg"], "gbfs": ["gbfs_counter"], "dijkstra_unit": ["dijkstra_counter", "dijkstra_lazy"],
           "idastar": ["idastar"], "jps": ["jps4"], "biastar": ["biastar"]}
STOP = {"search", "algorithm", "a", "an", "the", "with", "run", "from", "both", "and", "at", "once", "on", "grid",
        "uniform-cost", "of", "s", "using", "edge"}
# Extended alias table for 'other' known algorithms (plan 1.11)
EXT_ALIASES: dict[str, list[str]] = {
    "wavefront": ["wavefront propagation", "flood fill", "Lee algorithm"],
    "spfa": ["SPFA", "Bellman-Ford", "label-correcting search"],
    "ucs": ["uniform-cost search", "Dijkstra's algorithm", "unit-weight Dijkstra"],
    "random_walk": ["random walk", "random walk with restarts", "randomised walk"],
    "beam": ["beam search", "local beam search", "beam-limited best-first"],
    "random_priority": ["random-priority search", "randomised frontier search", "random-order frontier search"],
}
EXT_SHORT: dict[str, list[str]] = {
    "wavefront": [r"wave[-_ ]?front", r"flood[-_ ]?fill", r"\blee\b"],
    "spfa": [r"\bspfa\b", r"bellman", r"label[-_ ]?correct"],
    "ucs": [r"uniform[-_ ]?cost", r"dijkstra"],
    "random_walk": [r"random[-_ ]?walk"],
    "beam": [r"\bbeam\b"],
    "random_priority": [r"random[-_ ]?(priority|order)", r"randomi[sz]ed frontier"],
}


def aliases(a: str) -> list[str]:
    return list(ALIAS_TABLE.get(a) or EXT_ALIASES[a])


def shorts(a: str) -> list[str]:
    return list(SHORT_FORMS.get(a) or EXT_SHORT[a])


def terms(s: str) -> set[str]:
    toks = re.findall(r"[a-z0-9*]+(?:-[a-z0-9*]+)*", s.lower())
    return {t for t in toks if t not in STOP}


def d_name(a: str, b: str) -> float:
    if a == b:
        return 0.0
    al, bl = aliases(a), aliases(b)
    for rx in shorts(a):
        if any(re.search(rx, x, re.IGNORECASE) for x in bl):
            return 0.0
    for rx in shorts(b):
        if any(re.search(rx, x, re.IGNORECASE) for x in al):
            return 0.0
    best = 0.0
    for x in al:
        for y in bl:
            tx, ty = terms(x), terms(y)
            if tx or ty:
                best = max(best, len(tx & ty) / len(tx | ty))
    return 1.0 - best


def _first_seq(seq: list[list[int]]) -> list[tuple[int, int]]:
    seen: set[tuple[int, int]] = set()
    out = []
    for c in seq:
        t = (c[0], c[1])
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def d_order(A: list[tuple[int, int]], B: list[tuple[int, int]]) -> float:
    ra = {c: i for i, c in enumerate(A)}
    rb = {c: i for i, c in enumerate(B)}
    common = [c for c in A if c in rb]
    if len(common) < 5:
        return 0.5
    tau = kendalltau([ra[c] for c in common], [rb[c] for c in common]).statistic
    if tau is None or not np.isfinite(tau):
        return 0.5
    return float((1.0 - tau) / 2.0)


def d_set(A: list[tuple[int, int]], B: list[tuple[int, int]]) -> float:
    sa, sb = set(A), set(B)
    if not sa and not sb:
        return 0.0
    return 1.0 - len(sa & sb) / len(sa | sb)


DS_KEYS = ("container", "key", "restarts", "bidirectional")


def d_ds(x: dict[str, Any], y: dict[str, Any]) -> float:
    return sum(int(x.get(k) != y.get(k)) for k in DS_KEYS) / len(DS_KEYS)


def program_distance(p: dict[str, Any], q: dict[str, Any]) -> float:
    """Mean over the probes both programs traced of 0.5*D_order + 0.25*D_set, plus 0.25*D_ds."""
    ps = {pr["i"]: _first_seq(pr.get("seq") or []) for pr in p["probes"]}
    qs = {pr["i"]: _first_seq(pr.get("seq") or []) for pr in q["probes"]}
    vals = []
    for i in sorted(set(ps) & set(qs)):
        A, B = ps[i], qs[i]
        if not A or not B:
            continue
        vals.append(0.5 * d_order(A, B) + 0.25 * d_set(A, B))
    base = float(np.mean(vals)) if vals else 0.75
    return base + 0.25 * d_ds(p.get("ds_signature") or {}, q.get("ds_signature") or {})


def mech_matrix(ref_traces: dict[str, dict[str, Any]], algs: list[str] | None = None) -> dict[str, Any]:
    algs = algs or list(CANON_ORDER)
    M = np.zeros((len(algs), len(algs)))
    for i, a in enumerate(algs):
        for j, b in enumerate(algs):
            if j < i:
                M[i, j] = M[j, i]
                continue
            pairs = [(x, y) for x in REFS_OF[a] for y in REFS_OF[b] if not (a == b and x == y)]
            if not pairs:
                M[i, j] = 0.0
                continue
            M[i, j] = float(np.mean([program_distance(ref_traces[x], ref_traces[y]) for x, y in pairs]))
    return {"algs": algs, "D_mech": M.tolist()}


def name_matrix(algs: list[str] | None = None) -> dict[str, Any]:
    algs = algs or list(CANON_ORDER)
    return {"algs": algs, "D_name": [[d_name(a, b) for b in algs] for a in algs]}


def offdiag(M: list[list[float]]) -> list[float]:
    n = len(M)
    return [M[i][j] for i in range(n) for j in range(n) if i != j]


def select_sets(Dm: dict[str, Any], Dn: dict[str, Any], seed: int = 0) -> dict[str, Any]:
    algs = Dm["algs"]
    M = np.array(Dm["D_mech"])
    N = np.array(Dn["D_name"])
    idx = {a: i for i, a in enumerate(algs)}
    lit = tuple(sorted(LITERAL5, key=CANON_ORDER.index))
    cands = [tuple(sorted(("bfs",) + c, key=CANON_ORDER.index))
             for c in itertools.combinations([a for a in CANON_ORDER if a != "bfs"], 4)]
    cands = [c for c in cands if c != lit]
    assert len(cands) == 125

    def classify(lo_q: float, hi_q: float) -> dict[tuple[str, ...], dict[str, Any]]:
        qm_lo, qm_hi = np.quantile(offdiag(M.tolist()), [lo_q, hi_q])
        qn_lo, qn_hi = np.quantile(offdiag(N.tolist()), [lo_q, hi_q])
        out = {}
        for S in cands:
            nb = [a for a in algs if a not in S]
            mins = {a: (min(M[idx[a], idx[b]] for b in S), min(N[idx[a], idx[b]] for b in S)) for a in nb}
            tm = [a for a, (m, n) in mins.items() if m <= qm_lo and n >= qn_hi]
            tl = [a for a, (m, n) in mins.items() if m >= qm_hi and n <= qn_lo]
            out[S] = {"type_M": tm, "type_L": tl, "min_dists": {a: [round(m, 4), round(n, 4)]
                                                                for a, (m, n) in mins.items()}}
        return out

    rule = "quartiles"
    info = classify(0.25, 0.75)
    m_only = sorted(S for S, v in info.items() if v["type_M"] and not v["type_L"])
    l_only = sorted(S for S, v in info.items() if v["type_L"] and not v["type_M"])
    if len(m_only) < 3 or len(l_only) < 2:
        rule = "terciles"
        info = classify(1 / 3, 2 / 3)
        m_only = sorted(S for S, v in info.items() if v["type_M"] and not v["type_L"])
        l_only = sorted(S for S, v in info.items() if v["type_L"] and not v["type_M"])

    def jd(a: tuple[str, ...], b: tuple[str, ...]) -> float:
        return 1.0 - len(set(a) & set(b)) / len(set(a) | set(b))

    rng = random.Random(seed)
    chosen: list[tuple[str, ...]] = []
    kinds: list[str] = []
    plan = [("M", m_only)] * 3 + [("L", l_only)] * 2 + [("any", sorted(cands))]
    for kind, pool in plan:
        avail = [S for S in pool if S not in chosen]
        if not avail:
            avail = [S for S in sorted(cands) if S not in chosen]
            kind = kind + " (pool empty -> any)"
        if not chosen:
            pick = rng.choice(avail)
        else:
            pick = sorted(avail, key=lambda S: (-min(jd(S, c) for c in chosen), S))[0]
        chosen.append(pick)
        kinds.append(kind)
    sets = {f"R{i + 1}": {"set": list(S), "type": kinds[i], **info[S]} for i, S in enumerate(chosen)}
    return {"rule": rule, "n_candidates": len(cands), "n_M_only": len(m_only), "n_L_only": len(l_only),
            "sets": sets, "literal": list(lit),
            "quantiles": {"D_mech_q": [float(x) for x in np.quantile(offdiag(M.tolist()), [0.25, 1 / 3, 2 / 3, 0.75])],
                          "D_name_q": [float(x) for x in np.quantile(offdiag(N.tolist()), [0.25, 1 / 3, 2 / 3, 0.75])]}}
