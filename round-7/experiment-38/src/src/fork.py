#!/usr/bin/env python3
"""S4 helpers: the partial-code labeller (lexical rules on a program prefix), binomial change-point segmentation
with a position-permutation null, and prefix bookkeeping (identical-prefix share, canonical prefix c*, fork token
sets B and D)."""

from __future__ import annotations

import itertools
import math
import re
from collections import Counter
from typing import Any

import numpy as np

BFS_RE = re.compile(r"\.popleft\s*\(|\.pop\s*\(\s*0\s*\)|\.get\s*\(\s*\)\s*$|\bqueue\.Queue\s*\(|\bSimpleQueue\s*\(", re.M)
STACK_RE = re.compile(r"\b(\w*stack\w*)\s*\.\s*pop\s*\(\s*\)|LifoQueue\s*\(", re.I)
HEAP_RE = re.compile(r"\bheappush\s*\(|\bheappop\s*\(|\bPriorityQueue\s*\(")
DEF_RE = re.compile(r"^([ \t]*)def\s+(\w+)\s*\(", re.M)


def _code(text: str) -> str:
    i = text.find("```")
    if i >= 0:
        j = text.find("\n", i)
        text = text[j + 1:] if j >= 0 else ""
    k = text.find("```")
    return text[:k] if k >= 0 else text


def recursion_pos(code: str) -> int | None:
    """Char position of the first self-call inside the body of a nested def (partial text allowed)."""
    best = None
    for m in DEF_RE.finditer(code):
        ind = len(m.group(1).expandtabs(4))
        name = m.group(2)
        if name == "solve" and ind == 0:
            continue
        body_start = code.find("\n", m.end())
        if body_start < 0:
            continue
        pos = body_start + 1
        for line in code[body_start + 1:].split("\n"):
            stripped = line.strip()
            if stripped:
                li = len(line) - len(line.lstrip())
                if li <= ind:
                    break
                mm = re.search(r"(?<![\w.])" + re.escape(name) + r"\s*\(", line)
                if mm and not stripped.startswith("def "):
                    cand = pos + mm.start()
                    best = cand if best is None else min(best, cand)
                    break
            pos += len(line) + 1
    return best


def evidence(text: str) -> dict[str, int | None]:
    code = _code(text)
    out: dict[str, int | None] = {}
    m = BFS_RE.search(code)
    out["bfs"] = m.start() if m else None
    m = STACK_RE.search(code)
    st = m.start() if m else None
    rc = recursion_pos(code)
    out["dfs"] = min([x for x in (st, rc) if x is not None], default=None)
    m = HEAP_RE.search(code)
    out["other"] = m.start() if m else None
    return out


def partial_label(text: str) -> str | None:
    """'bfs' | 'dfs' | 'other' at the first decisive evidence in the program prefix; None while undecided."""
    ev = evidence(text)
    cands = [(v, k) for k, v in ev.items() if v is not None]
    if not cands:
        return None
    return min(cands)[1]


def decided(text: str) -> bool:
    return partial_label(text) is not None


def map_full(label: str) -> str:
    return label if label in ("bfs", "dfs") else "other"


# ------------------------------------------------------------------------------------------------ change points
def best_segmentation(k: np.ndarray, n: np.ndarray, max_cp: int = 2) -> tuple[float, list[int]]:
    """Exhaustive binomial segmentation with up to max_cp change points (prefix sums); returns (log-likelihood gain
    over no change, minus a BIC-style 1.5 log N penalty per change point beyond the first, cps); cp = index i means a
    change between positions i-1 and i."""
    T = len(k)
    ck = [0.0]
    cn = [0.0]
    for a, b in zip(k, n):
        ck.append(ck[-1] + float(a))
        cn.append(cn[-1] + float(b))

    def ll(i: int, j: int) -> float:
        K, N = ck[j] - ck[i], cn[j] - cn[i]
        if N <= 0 or K <= 0 or K >= N:
            return 0.0
        p = K / N
        return K * math.log(p) + (N - K) * math.log(1 - p)
    base = ll(0, T)
    pen = 1.5 * math.log(max(cn[-1], 2.0))
    best = (0.0, [])
    for i in range(1, T):
        g = ll(0, i) + ll(i, T) - base
        if g > best[0] + 1e-12:
            best = (g, [i])
    if max_cp >= 2:
        for i in range(1, T - 1):
            li = ll(0, i)
            for j in range(i + 1, T):
                g = li + ll(i, j) + ll(j, T) - base - pen
                if g > best[0] + 1e-12:
                    best = (g, [i, j])
    return best


def change_points(k: list[int], n: list[int], n_perm: int = 1000, seed: int = 0) -> dict[str, Any]:
    k_a, n_a = np.asarray(k, float), np.asarray(n, float)
    gain, cps = best_segmentation(k_a, n_a)
    rng = np.random.default_rng(seed)
    null = []
    for _ in range(n_perm):
        o = rng.permutation(len(k_a))
        null.append(best_segmentation(k_a[o], n_a[o])[0])
    p = (1 + sum(g >= gain for g in null)) / (1 + n_perm)
    segs = []
    b = [0, *cps, len(k_a)]
    for i in range(len(b) - 1):
        kk, nn = k_a[b[i]:b[i + 1]].sum(), n_a[b[i]:b[i + 1]].sum()
        segs.append({"start_idx": b[i], "end_idx": b[i + 1], "p": float(kk / nn) if nn else None})
    return {"gain": gain, "cps": cps, "p_value": p, "segments": segs}


# ------------------------------------------------------------------------------------------------ prefixes
def lcp(a: list[int], b: list[int]) -> int:
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    return n


def identical_prefix_share(ids_by_template: dict[str, list[list[int]]], t: int) -> dict[str, float]:
    out = {}
    for w, L in ids_by_template.items():
        pairs = list(itertools.combinations(range(len(L)), 2))
        same = sum(1 for i, j in pairs if len(L[i]) >= t and len(L[j]) >= t and L[i][:t] == L[j][:t])
        out[w] = same / len(pairs) if pairs else float("nan")
    return out


def canonical_prefix(ids: list[list[int]], t: int) -> tuple[list[int], int]:
    c = Counter(tuple(x[:t]) for x in ids if len(x) >= t)
    pref, cnt = c.most_common(1)[0]
    return list(pref), cnt


def token_table(rows: list[dict[str, Any]], cstar: list[int], min_n: int = 3) -> dict[int, dict[str, Any]]:
    """rows: {ids (response), cls ('bfs'|'dfs'|'other')}; tokens right after c* among rows whose prefix is c*."""
    t = len(cstar)
    by: dict[int, list[str]] = {}
    for r in rows:
        ids = r["ids"]
        if len(ids) > t and ids[:t] == cstar:
            by.setdefault(int(ids[t]), []).append(r["cls"])
    out = {}
    for tok, cl in by.items():
        n_bd = sum(c in ("bfs", "dfs") for c in cl)
        out[tok] = {"n": len(cl), "n_bfs": sum(c == "bfs" for c in cl), "n_dfs": sum(c == "dfs" for c in cl),
                    "p_bfs": (sum(c == "bfs" for c in cl) / n_bd) if n_bd else None, "pooled": len(cl) < min_n}
    return out
