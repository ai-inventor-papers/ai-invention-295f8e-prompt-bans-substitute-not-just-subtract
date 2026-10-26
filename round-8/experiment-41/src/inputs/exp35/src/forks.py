#!/usr/bin/env python3
"""Fork location (Part C), pure functions.

C1 canonical opening: a token trie over the twin programs' generated ids; from the root follow the most populous child
   while its subtree still holds >= 2 programs of D and >= 2 of A_min. The trunk O ends at the first node whose children
   separate the classes (or where the condition fails). Opening clusters: other branches leaving the trunk that hold
   >= 15% of the programs get their own trunk O_c (same rule inside the branch).
C4 change points: per base path, a Bayesian single-change-point model over the scanned prefix lengths:
   Dirichlet(1)-multinomial segment likelihoods, a uniform prior on tau, prior 0.5 on change vs no change; a change is
   detected if P(change | data) >= 0.9 and the base path's own class share differs by >= 0.4 across tau (MAP).
   Recursion on each segment, at most 3 change points. Sensitivity: a permutation-calibrated max-share-jump statistic.
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Any

import numpy as np
from scipy.special import gammaln, logsumexp
from scipy.stats import fisher_exact


# ------------------------------------------------------------------------------------------------ C1 opening
def _walk(progs: list[tuple[list[int], str]], start: list[int], D: str, A: str) -> list[int]:
    path = list(start)
    sub = [(g, c) for g, c in progs if g[:len(path)] == path]
    while True:
        nxt = Counter(g[len(path)] for g, c in sub if len(g) > len(path))
        if not nxt:
            return path
        tok, _ = nxt.most_common(1)[0]
        child = [(g, c) for g, c in sub if len(g) > len(path) and g[len(path)] == tok]
        nD = sum(c == D for _, c in child)
        nA = sum(c == A for _, c in child)
        if nD >= 2 and nA >= 2:
            path.append(tok)
            sub = child
        else:
            return path


def opening(progs: list[tuple[list[int], str]], D: str, A: str, min_cluster: float = 0.15,
            max_clusters: int = 3) -> dict[str, Any]:
    """progs: (generated ids, label). Returns the trunk O, coverage and opening clusters."""
    n = len(progs)
    O = _walk(progs, [], D, A)
    cov = sum(g[:len(O)] == O for g, _ in progs) / n
    clusters = [{"id": "c0", "O": O, "n": int(round(cov * n)), "cov": cov}]
    if cov < 0.6:
        # branches leaving the trunk before its end with >= 15% of programs
        for i in range(len(O)):
            pre = O[:i]
            sub = [(g, c) for g, c in progs if g[:i] == pre and len(g) > i]
            for tok, m in Counter(g[i] for g, _ in sub).most_common():
                if tok == O[i] or m < min_cluster * n:
                    continue
                Oc = _walk(progs, pre + [tok], D, A)
                ccov = sum(g[:len(Oc)] == Oc for g, _ in progs) / n
                if ccov >= min_cluster and len(clusters) < max_clusters:
                    clusters.append({"id": f"c{len(clusters)}", "O": Oc, "n": int(round(ccov * n)), "cov": ccov})
    return {"O": O, "len_O": len(O), "cov": cov, "clusters": clusters}


def cluster_of(g: list[int], clusters: list[dict[str, Any]]) -> str | None:
    best = None
    for c in clusters:
        if g[:len(c["O"])] == c["O"] and (best is None or len(c["O"]) > len(best["O"])):
            best = c
    return best["id"] if best else None


# ------------------------------------------------------------------------------------------------ C4 change points
def dm_loglik(counts: np.ndarray, alpha: float = 1.0) -> float:
    counts = np.asarray(counts, dtype=float)
    C = len(counts)
    N = counts.sum()
    return float(gammaln(C * alpha) - gammaln(C * alpha + N) + np.sum(gammaln(alpha + counts) - gammaln(alpha)))


def single_cp(series: np.ndarray) -> dict[str, Any]:
    """series: [K, C] label counts per scanned position. Returns P(change), the tau posterior (tau = index of the
    first position of the second segment, 1..K-1) and the MAP tau."""
    K = series.shape[0]
    if K < 2:
        return {"p_change": 0.0, "tau": None, "post": []}
    tot = series.sum(0)
    ll0 = dm_loglik(tot)
    cums = np.cumsum(series, 0)
    lls = np.array([dm_loglik(cums[t - 1]) + dm_loglik(tot - cums[t - 1]) for t in range(1, K)])
    ll1 = logsumexp(lls) - math.log(K - 1)
    p = 1.0 / (1.0 + math.exp(min(700.0, ll0 - ll1)))
    post = np.exp(lls - logsumexp(lls))
    return {"p_change": p, "tau": int(np.argmax(post)) + 1, "post": post.tolist()}


def share(counts: np.ndarray, j: int) -> float:
    s = counts.sum()
    return float(counts[j] / s) if s > 0 else float("nan")


def change_points(series: np.ndarray, own: int, p_min: float = 0.9, jump_min: float = 0.4,
                  max_cp: int = 3) -> list[dict[str, Any]]:
    """Recursive single-change-point detection on [lo, hi) segments; returns detected change points with their
    absolute position index, posterior and own-class share before/after."""
    found: list[dict[str, Any]] = []

    def rec(lo: int, hi: int) -> None:
        if len(found) >= max_cp or hi - lo < 3:
            return
        r = single_cp(series[lo:hi])
        if r["tau"] is None:
            return
        t = lo + r["tau"]
        before = share(series[lo:t].sum(0), own)
        after = share(series[t:hi].sum(0), own)
        ok = r["p_change"] >= p_min and abs(after - before) >= jump_min
        if not ok:
            return
        found.append({"tau_idx": t, "p_change": r["p_change"], "share_before": before, "share_after": after,
                      "jump": after - before, "segment": [lo, hi], "post": r["post"]})
        rec(lo, t)
        rec(t, hi)
    rec(0, series.shape[0])
    return sorted(found, key=lambda d: d["tau_idx"])


def perm_stat(series: np.ndarray, own: int, n_perm: int = 500, seed: int = 0) -> dict[str, Any]:
    """Sensitivity: max over tau of |own share before - after|, calibrated by permuting individual continuation
    labels across positions (500 permutations, iteration-1 style)."""
    K, C = series.shape

    def stat(s: np.ndarray) -> float:
        best = 0.0
        cs = np.cumsum(s, 0)
        tot = s.sum(0)
        for t in range(1, K):
            a, b = cs[t - 1], tot - cs[t - 1]
            if a.sum() == 0 or b.sum() == 0:
                continue
            best = max(best, abs(a[own] / a.sum() - b[own] / b.sum()))
        return best
    obs = stat(series)
    labels = np.repeat(np.tile(np.arange(C), K), series.reshape(-1).astype(int))
    pos_sizes = series.sum(1).astype(int)
    rng = np.random.default_rng(seed)
    ge = 0
    for _ in range(n_perm):
        perm = rng.permutation(labels)
        s = np.zeros_like(series)
        i = 0
        for k, m in enumerate(pos_sizes):
            for c in perm[i:i + m]:
                s[k, c] += 1
            i += m
        ge += stat(s) >= obs - 1e-12
    return {"stat": obs, "p_perm": (ge + 1) / (n_perm + 1)}


# ------------------------------------------------------------------------------------------------ C5/C6
def jump_position(shares: dict[int, float]) -> int | None:
    """Largest absolute share jump between consecutive prefix lengths: returns j (prefix length after the jump)."""
    ks = sorted(shares)
    best, bj = -1.0, None
    for a, b in zip(ks, ks[1:]):
        if b != a + 1 or np.isnan(shares[a]) or np.isnan(shares[b]):
            continue
        d = abs(shares[b] - shares[a])
        if d > best:
            best, bj = d, b
    return bj


def confirm(n_pre: tuple[int, int], n_post: tuple[int, int], ctrl_pre: tuple[int, int] | None,
            ctrl_post: tuple[int, int] | None, jump_min: float = 0.5, p_max: float = 0.01,
            ctrl_max: float = 0.2) -> dict[str, Any]:
    """(own-class count, total) at f-1 and f, and at the controls f-9 (vs f-1) and f+8 (vs f)."""
    s_pre = n_pre[0] / max(n_pre[1], 1)
    s_post = n_post[0] / max(n_post[1], 1)
    p = fisher_exact([[n_pre[0], n_pre[1] - n_pre[0]], [n_post[0], n_post[1] - n_post[0]]])[1]
    c1 = abs(ctrl_pre[0] / max(ctrl_pre[1], 1) - s_pre) if ctrl_pre else None
    c2 = abs(ctrl_post[0] / max(ctrl_post[1], 1) - s_post) if ctrl_post else None
    ok_ctrl = all(c is None or c < ctrl_max for c in (c1, c2))
    return {"share_pre": s_pre, "share_post": s_post, "jump": s_post - s_pre, "fisher_p": float(p),
            "ctrl_pre_move": c1, "ctrl_post_move": c2,
            "confirmed": bool(abs(s_post - s_pre) >= jump_min and p < p_max and ok_ctrl)}


def jeffreys(k: int, n: int, a: float = 0.05) -> tuple[float, float]:
    from scipy.stats import beta
    lo = 0.0 if k == 0 else float(beta.ppf(a / 2, k + 0.5, n - k + 0.5))
    hi = 1.0 if k == n else float(beta.ppf(1 - a / 2, k + 0.5, n - k + 0.5))
    return lo, hi


def entropy_bits(p: np.ndarray) -> float:
    p = np.asarray(p, dtype=float)
    p = p[p > 0]
    return float(-(p * np.log2(p)).sum()) if len(p) else 0.0
