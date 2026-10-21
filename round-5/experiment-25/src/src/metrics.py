#!/usr/bin/env python3
"""Statistics used by the frozen analysis (committed at #0): Wilson intervals, rarefied Hill-1, Good's coverage,
Spearman / Kendall with exact permutation p, Poisson-binomial tail, the fixed log-score mixture, exact Wilcoxon."""

from __future__ import annotations

import itertools
import math
from collections import Counter
from typing import Any, Sequence

import numpy as np
from scipy import stats


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float | None, float | None]:
    if n <= 0:
        return (None, None)
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, c - h), min(1.0, c + h))


def shannon_hill1(labels: Sequence[str]) -> float:
    if not labels:
        return float("nan")
    c = np.array(list(Counter(labels).values()), dtype=float)
    p = c / c.sum()
    return float(np.exp(-(p * np.log(p)).sum()))


def hill1_rarefied(labels: Sequence[str], depth: int = 25, n_sub: int = 1000, seed: int = 0) -> dict[str, Any]:
    """Mean Hill-1 (exp Shannon) over n_sub subsamples of `depth` labels without replacement; below depth the full
    sample is used and flagged."""
    labs = list(labels)
    n = len(labs)
    if n == 0:
        return {"hill1": None, "depth": 0, "flag_below_depth": True, "n": 0}
    if n <= depth:
        return {"hill1": shannon_hill1(labs), "depth": n, "flag_below_depth": n < depth, "n": n}
    rng = np.random.default_rng(seed)
    arr = np.array(labs)
    vals = [shannon_hill1(list(arr[rng.choice(n, depth, replace=False)])) for _ in range(n_sub)]
    return {"hill1": float(np.mean(vals)), "depth": depth, "flag_below_depth": False, "n": n}


def goods_coverage(labels: Sequence[str]) -> float | None:
    if not labels:
        return None
    c = Counter(labels)
    f1 = sum(1 for v in c.values() if v == 1)
    return 1.0 - f1 / len(labels)


def rankdata(x: Sequence[float]) -> np.ndarray:
    return stats.rankdata(np.asarray(x, dtype=float), method="average")


def spearman(x: Sequence[float], y: Sequence[float]) -> float:
    x, y = np.asarray(x, float), np.asarray(y, float)
    if len(x) < 3:
        return float("nan")
    rx, ry = rankdata(x), rankdata(y)
    if np.std(rx) == 0 or np.std(ry) == 0:
        return float("nan")
    return float(np.corrcoef(rx, ry)[0, 1])


def kendall_b(x: Sequence[float], y: Sequence[float]) -> float:
    if len(x) < 3:
        return float("nan")
    r = stats.kendalltau(x, y, variant="b")
    return float(r.statistic) if r.statistic == r.statistic else float("nan")


def perm_p_spearman(x: Sequence[float], y: Sequence[float], n_random: int = 10000, seed: int = 0,
                    clusters: Sequence[Any] | None = None) -> dict[str, Any]:
    """One-sided (greater) permutation p of Spearman rho: all n! permutations of y when n <= 9, else n_random.
    clusters: permute whole clusters' y-vectors together (units of one cluster keep their joint assignment)."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    n = len(x)
    obs = spearman(x, y)
    if n < 3 or obs != obs:
        return {"rho": obs, "p": None, "n_perm": 0, "exact": False}
    if clusters is not None and len(set(clusters)) < n:
        # cluster-respecting: permute cluster labels among equal-size clusters only (conservative fallback)
        groups: dict[Any, list[int]] = {}
        for i, c in enumerate(clusters):
            groups.setdefault(c, []).append(i)
        keys = list(groups)
        rng = np.random.default_rng(seed)
        ge = 0
        for _ in range(n_random):
            perm = rng.permutation(len(keys))
            yy = np.empty(n)
            ok = True
            for gi, g in enumerate(keys):
                src = groups[keys[perm[gi]]]
                if len(src) != len(groups[g]):
                    ok = False
                    break
                yy[groups[g]] = y[src]
            if not ok:
                yy = y[rng.permutation(n)]
            ge += spearman(x, yy) >= obs - 1e-12
        return {"rho": obs, "p": (ge + 1) / (n_random + 1), "n_perm": n_random, "exact": False, "clustered": True}
    rx = rankdata(x) - rankdata(x).mean()
    ry = rankdata(y) - rankdata(y).mean()
    den = float(np.sqrt((rx ** 2).sum() * (ry ** 2).sum()))
    if n <= 9:  # all n! permutations (vectorised: ranks of a permuted vector are the permuted ranks)
        perms = np.array(list(itertools.permutations(range(n))), dtype=np.int8)
        r = (ry[perms] @ rx) / den
        ge = int((r >= obs - 1e-12).sum())
        return {"rho": obs, "p": ge / len(perms), "n_perm": int(len(perms)), "exact": True}
    rng = np.random.default_rng(seed)
    perms = np.argsort(rng.random((n_random, n)), axis=1)
    r = (ry[perms] @ rx) / den
    ge = int((r >= obs - 1e-12).sum())
    return {"rho": obs, "p": (ge + 1) / (n_random + 1), "n_perm": n_random, "exact": False}


def poisson_binomial_sf(h: int, ps: Sequence[float]) -> float:
    """P(H >= h) for H = sum of independent Bernoulli(p_i) (exact DP)."""
    dist = np.zeros(len(ps) + 1)
    dist[0] = 1.0
    for p in ps:
        dist[1:] = dist[1:] * (1 - p) + dist[:-1] * p
        dist[0] *= (1 - p)
    return float(dist[h:].sum()) if h <= len(ps) else 0.0


def binom_greater_p(k: int, n: int, p0: float) -> float:
    if n <= 0:
        return 1.0
    return float(stats.binomtest(int(k), int(n), float(p0), alternative="greater").pvalue)


def mixture_q(raw: dict[str, float] | None, survivors: list[str]) -> dict[str, float]:
    """q = 0.98 * [0.95 raw + 0.05 uniform over survivors] + 0.02 'other'; an undefined/empty raw is uniform."""
    K = len(survivors)
    if K == 0:
        return {"other": 1.0}
    tot = sum(max(0.0, (raw or {}).get(s, 0.0)) for s in survivors)
    if not raw or tot <= 0:
        base = {s: 1.0 / K for s in survivors}
    else:
        base = {s: max(0.0, raw.get(s, 0.0)) / tot for s in survivors}
    q = {s: 0.98 * (0.95 * base[s] + 0.05 / K) for s in survivors}
    q["other"] = 0.02
    return q


def log_score(q: dict[str, float], labels: Sequence[str]) -> float | None:
    """Mean natural-log probability of the realised labels (labels outside q count as 'other')."""
    if not labels:
        return None
    return float(np.mean([math.log(q.get(l, q.get("other", 1e-12))) for l in labels]))


def wilcoxon_exact(d: Sequence[float]) -> dict[str, Any]:
    d = [float(v) for v in d if v is not None and v == v]
    if len(d) == 0 or all(v == 0 for v in d):
        return {"n": len(d), "stat": None, "p_two_sided": None, "p_greater": None}
    try:
        r2 = stats.wilcoxon(d, method="exact", zero_method="wilcox")
        rg = stats.wilcoxon(d, method="exact", zero_method="wilcox", alternative="greater")
        return {"n": len(d), "stat": float(r2.statistic), "p_two_sided": float(r2.pvalue), "p_greater": float(rg.pvalue)}
    except ValueError as e:
        return {"n": len(d), "stat": None, "p_two_sided": None, "p_greater": None, "error": str(e)[:100]}


def js_divergence(a: dict[str, int], b: dict[str, int]) -> float:
    keys = sorted(set(a) | set(b))
    pa = np.array([a.get(k, 0) for k in keys], float)
    pb = np.array([b.get(k, 0) for k in keys], float)
    if pa.sum() == 0 or pb.sum() == 0:
        return float("nan")
    pa, pb = pa / pa.sum(), pb / pb.sum()
    m = 0.5 * (pa + pb)

    def kl(p, q):
        mask = p > 0
        return float((p[mask] * np.log2(p[mask] / q[mask])).sum())
    return 0.5 * kl(pa, m) + 0.5 * kl(pb, m)
