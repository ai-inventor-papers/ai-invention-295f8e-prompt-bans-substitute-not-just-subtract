#!/usr/bin/env python3
"""Steps 7-8: elicitation parsing, association objects, baseline objects, composed predictions."""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from typing import Any

import numpy as np

from common import CATALOGUE, MODES, OTHER, THRESHOLDS

# ------------------------------------------------------------------------------------------- rank parsing


def parse_ranking(text: str, n_opts: int) -> tuple[list[str] | None, str]:
    letters = [chr(ord("A") + i) for i in range(n_opts)]
    m = re.search(r"\[[^\[\]]*\]", text)
    if not m:
        return None, "no_list"
    raw = m.group(0)
    lst = None
    for cand in (raw, raw.replace("'", '"')):
        try:
            lst = json.loads(cand)
            break
        except json.JSONDecodeError:
            continue
    if lst is None:
        lst = re.findall(r"[A-Za-z]", raw)
    out = [str(x).strip().strip(".").upper() for x in lst]
    if sorted(out) != letters:
        return None, "not_permutation"
    return out, "ok"


# --------------------------------------------------------------------------------------- free-text mapping
ALIASES: dict[str, list[tuple[str, str]]] = {
    "t1": [("bibfs", r"bi-?directional\s+(?:bfs|breadth)|bidirectional\b(?!\s+(?:a\*|a-star|dijkstra))"),
           ("iddfs", r"iterative[\s-]+deepening|\biddfs\b|\bid-dfs\b"),
           ("astar_gbfs", r"\ba\s?\*|\ba-star\b|\ba star\b|best[\s-]first|\bgreedy\b"),
           ("dijkstra", r"dijkstra|uniform[\s-]cost"),
           ("bfs", r"breadth[\s-]first|\bbfs\b"),
           ("dfs", r"depth[\s-]first|\bdfs\b"),
           (OTHER, r"bellman|floyd|warshall|\bspfa\b|jump point|\bjps\b|beam search|random walk|flood fill|"
                   r"union[\s-]find|\bdial\b|bucket|lee algorithm|wavefront|hill climbing")],
    "t2": [("bidijkstra", r"bi-?directional\s+dijkstra|bidirectional\b(?!\s+(?:a\*|a-star|bfs|breadth))"),
           ("bf_spfa", r"bellman|\bspfa\b|shortest path faster"),
           ("floyd", r"floyd|warshall"),
           ("dial", r"\bdial'?s?\b|bucket"),
           ("dijkstra", r"dijkstra|uniform[\s-]cost"),
           (OTHER, r"\ba\s?\*|\ba-star\b|johnson|topolog|\bdag\b|breadth[\s-]first|\bbfs\b|depth[\s-]first|"
                   r"\bdfs\b|0-1 bfs|\bdp\b|dynamic programming|best[\s-]first|greedy")],
}


def map_freetext(task: str, x: str, text: str) -> str:
    """Mask every alias match of X itself (the echoed question), then take the earliest remaining alias,
    preferring bold segments. Returns a mode id, 'other', 'self' (answered X) or 'unmapped'."""
    low = text.lower()
    aliases = ALIASES[task]
    x_pats = [p for m, p in aliases if m == x]
    masked = low
    for p in x_pats:
        masked = re.sub(p, lambda mm: " " * len(mm.group(0)), masked)
    x_found = masked != low

    def earliest(segment: str) -> str | None:
        best = None
        for m, p in aliases:
            if m == x:
                continue
            mm = re.search(p, segment)
            if mm and (best is None or mm.start() < best[0]):
                best = (mm.start(), m)
        return best[1] if best else None

    for seg in re.findall(r"\*\*(.+?)(?:\*\*|$)", masked, flags=re.S):
        r = earliest(seg)
        if r:
            return r
    r = earliest(masked)
    if r:
        return r
    return "self" if x_found else "unmapped"


# ------------------------------------------------------------------------------------ association objects


def borda_winner(points: dict[str, float], firsts: dict[str, int]) -> str:
    return sorted(points, key=lambda y: (-points[y], -firsts.get(y, 0), y))[0]


def assoc_object(task: str, x: str, rankings: list[list[str]]) -> dict[str, Any]:
    """rankings: lists of mode ids over the K-1 others, most standard first."""
    others = [m for m in MODES[task] if m != x]
    K = len(MODES[task])
    m = len(rankings)
    pts = {y: 0.0 for y in others}
    firsts = {y: 0 for y in others}
    rank_sums = {y: 0.0 for y in others}
    for r in rankings:
        for p, y in enumerate(r):
            pts[y] += K - 2 - p
            rank_sums[y] += p + 1
        firsts[r[0]] += 1
    tot = sum(v + 1 for v in pts.values())
    A = {y: (pts[y] + 1) / tot for y in others}
    F = {y: (firsts[y] + 1) / (m + K - 1) for y in others}
    win = borda_winner(pts, firsts)
    a = (sum(1 for r in rankings if r[0] == win) / m) if m else float("nan")
    k1 = K - 1
    a_cc = (a - 1 / k1) / (1 - 1 / k1) if m else float("nan")
    n = k1
    S = sum((rank_sums[y] - m * (n + 1) / 2) ** 2 for y in others)
    W = 12 * S / (m * m * (n ** 3 - n)) if m else float("nan")
    shares = np.array([firsts[y] / m for y in others]) if m else np.zeros(len(others))
    nz = shares[shares > 0]
    H = float(-(nz * np.log2(nz)).sum()) if len(nz) else 0.0
    f_win = sorted(others, key=lambda y: (-firsts[y], -pts[y], y))[0]
    return {"x": x, "n_rankings": m, "borda_points": pts, "first_counts": firsts, "A": A, "F": F,
            "borda_winner": win, "first_winner": f_win, "clarity": a, "clarity_cc": a_cc, "kendall_w": W,
            "first_entropy_norm": H / math.log2(k1), "ambiguous": f_win != win,
            "tie_at_top": sorted(pts.values(), reverse=True)[:2][0] == sorted(pts.values(), reverse=True)[:2][-1]
            if len(pts) > 1 else False, "rankings": rankings}


def restricted(dist: dict[str, float], S: list[str]) -> dict[str, float]:
    tot = sum(max(0.0, dist.get(y, 0.0)) for y in S)
    if tot <= 0:
        return {y: 1.0 / len(S) for y in S}
    return {y: max(0.0, dist.get(y, 0.0)) / tot for y in S}


def restricted_winner_and_clarity(obj: dict[str, Any], S: list[str]) -> tuple[str, float]:
    pts = {y: obj["borda_points"][y] for y in S}
    tops = Counter()
    for r in obj["rankings"]:
        top = next((y for y in r if y in S), None)
        if top:
            tops[top] += 1
    win = sorted(S, key=lambda y: (-pts[y], -tops.get(y, 0), y))[0]
    m = len(obj["rankings"])
    return win, (tops.get(win, 0) / m if m else float("nan"))


# ------------------------------------------------------------------------------------- composition


def compose(p: dict[str, float], S: list[str]) -> dict[str, float]:
    """q(y) = 0.98 (0.95 p(y) + 0.05/|S|) for y in S; q(other) = 0.02."""
    mix, floor = THRESHOLDS["uniform_mix"], THRESHOLDS["other_floor"]
    pr = restricted(p, S)
    q = {y: (1 - floor) * ((1 - mix) * pr[y] + mix / len(S)) for y in S}
    q[OTHER] = floor
    return q


def nomination(p: dict[str, float], S: list[str]) -> dict[str, Any]:
    pr = restricted(p, S)
    mx = max(pr.values())
    top = sorted([y for y in S if abs(pr[y] - mx) < 1e-12])
    return {"top": top[0] if len(top) == 1 else None, "tied": top if len(top) > 1 else [], "is_tied": len(top) > 1}


def freq_from_labels(task: str, labels: list[str]) -> dict[str, Any]:
    c = Counter(labels)
    n = len(labels)
    f = {m: (c.get(m, 0) / n if n else 0.0) for m in MODES[task]}
    return {"n": n, "counts": dict(c), "f": f, "other_share": c.get(OTHER, 0) / n if n else 0.0}


def hill(labels: list[str]) -> float:
    if not labels:
        return float("nan")
    c = np.array(list(Counter(labels).values()), dtype=float)
    p = c / c.sum()
    return float(np.exp(-(p * np.log(p)).sum()))


def freq_stability(task: str, labels: list[str], S: list[str], point: dict[str, Any], n_boot: int = 1000,
                   seed: int = 0) -> float:
    if point["is_tied"] or point["top"] is None:
        return 0.0
    rng = np.random.default_rng(seed)
    arr = np.array(labels)
    hits = 0
    for _ in range(n_boot):
        bs = arr[rng.integers(0, len(arr), len(arr))]
        c = Counter(bs.tolist())
        vals = {y: c.get(y, 0) for y in S}
        mx = max(vals.values())
        tops = [y for y in S if vals[y] == mx]
        if len(tops) == 1 and tops[0] == point["top"] and mx > 0:
            hits += 1
    return hits / n_boot


def display(task: str, m: str) -> str:
    return CATALOGUE[task].get(m, m)
