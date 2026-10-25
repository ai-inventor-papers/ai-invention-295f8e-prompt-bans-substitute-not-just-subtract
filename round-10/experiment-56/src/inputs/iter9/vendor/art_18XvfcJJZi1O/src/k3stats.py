#!/usr/bin/env python3
"""Statistics for K3: exact sign-flip permutation test (chunked enumeration up to n = 25, else 10^6 Monte Carlo sign
flips), Holm, exact McNemar, Newcombe (1998, method 10) interval for a paired difference of proportions, Wilson
interval, rule-of-three bound."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from scipy.stats import binom, norm


def _half_sums(d: np.ndarray) -> np.ndarray:
    n = len(d)
    if n == 0:
        return np.zeros(1)
    idx = np.arange(1 << n, dtype=np.int64)
    signs = ((idx[:, None] >> np.arange(n, dtype=np.int64)[None]) & 1) * 2 - 1
    return signs @ d


def sign_flip_p(d: np.ndarray, n_mc: int = 1_000_000, seed: int = 0, exact_max: int = 40) -> float:
    """One-sided p for mean(d) > 0 under random sign flips: exact enumeration of all 2^n patterns by meet-in-the-middle
    (sums of the two halves, sorted, counted with searchsorted) for n <= exact_max, else n_mc Monte Carlo flips."""
    d = np.asarray(d, dtype=np.float64)
    n = len(d)
    if n == 0:
        return 1.0
    obs = d.sum()
    tol = 1e-9 * max(1.0, float(np.abs(d).sum()))
    if n <= exact_max:
        h = n // 2
        a = _half_sums(d[:h])
        b = np.sort(_half_sums(d[h:]))
        ge = 0
        for c0 in range(0, len(a), 1 << 16):
            ac = a[c0:c0 + (1 << 16)]
            ge += int((len(b) - np.searchsorted(b, obs - ac - tol, side="left")).sum())
        return ge / float(1 << n)
    rng = np.random.default_rng(seed)
    ge = 0
    done = 0
    while done < n_mc:
        m = min(100_000, n_mc - done)
        signs = rng.integers(0, 2, size=(m, n)) * 2 - 1
        ge += int((signs @ d >= obs - tol).sum())
        done += m
    return (ge + 1) / (n_mc + 1)


def holm(ps: list[float]) -> list[float]:
    m = len(ps)
    order = np.argsort(ps)
    adj = np.zeros(m)
    run = 0.0
    for r, i in enumerate(order):
        run = max(run, (m - r) * ps[i])
        adj[i] = min(1.0, run)
    return adj.tolist()


def mcnemar_exact(b: int, c: int, alternative: str = "greater") -> float:
    """b = discordant pairs favouring the first arm, c = favouring the second. One-sided (first > second) or two-sided
    exact binomial p."""
    n = b + c
    if n == 0:
        return 1.0
    if alternative == "greater":
        return float(binom.sf(b - 1, n, 0.5))
    p = 2 * min(binom.cdf(b, n, 0.5), binom.sf(b - 1, n, 0.5))
    return float(min(1.0, p))


def wilson(k: int, n: int, a: float = 0.05) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    z = norm.ppf(1 - a / 2)
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, c - h), min(1.0, c + h))


def newcombe_paired(a: int, b: int, c: int, d: int, alpha: float = 0.05) -> dict[str, float]:
    """Newcombe (1998) method 10 for theta = p1 - p2 from paired binary data: a = both 1, b = 1/0, c = 0/1, d = both 0."""
    n = a + b + c + d
    if n == 0:
        return {"diff": 0.0, "lo": -1.0, "hi": 1.0}
    p1, p2 = (a + b) / n, (a + c) / n
    l1, u1 = wilson(a + b, n, alpha)
    l2, u2 = wilson(a + c, n, alpha)
    theta = p1 - p2
    num = a * d - b * c
    den = math.sqrt((a + b) * (c + d) * (a + c) * (b + d)) if (a + b) * (c + d) * (a + c) * (b + d) > 0 else 0.0
    if den == 0:
        phi = 0.0
    else:
        phi = (max(num - n / 2, 0) if num > 0 else num) / den
    dl = math.sqrt(max(0.0, (p1 - l1) ** 2 - 2 * phi * (p1 - l1) * (u2 - p2) + (u2 - p2) ** 2))
    du = math.sqrt(max(0.0, (u1 - p1) ** 2 - 2 * phi * (u1 - p1) * (p2 - l2) + (p2 - l2) ** 2))
    return {"diff": theta, "lo": max(-1.0, theta - dl), "hi": min(1.0, theta + du)}


def rule_of_three(n: int) -> float:
    return 3.0 / n if n > 0 else 1.0


def spearman_pearson(a: np.ndarray, b: np.ndarray) -> dict[str, Any]:
    from scipy.stats import pearsonr, spearmanr

    a, b = np.asarray(a).ravel(), np.asarray(b).ravel()
    return {"spearman": float(spearmanr(a, b).statistic), "pearson": float(pearsonr(a, b).statistic),
            "mean_abs_err": float(np.abs(a - b).mean()), "mean_abs_exact": float(np.abs(b).mean()), "n": int(len(a))}
