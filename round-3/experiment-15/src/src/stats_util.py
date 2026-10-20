#!/usr/bin/env python3
"""Small, dependency-light statistics: Wilson and Newcombe intervals, Hill numbers, rarefied Hill-1,
Fisher-Freeman-Halton Monte Carlo test, Jensen-Shannon divergence."""

from __future__ import annotations

import math
from collections import Counter
from typing import Iterable

import numpy as np


def wilson(k: float, n: float, z: float = 1.959963984540054) -> tuple[float, float]:
    if n <= 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, c - h), min(1.0, c + h))


def newcombe(k1: float, n1: float, k2: float, n2: float) -> tuple[float, float, float]:
    """Difference p1 - p2 with Newcombe's hybrid score interval (method 10)."""
    if n1 <= 0 or n2 <= 0:
        return (float("nan"),) * 3
    p1, p2 = k1 / n1, k2 / n2
    l1, u1 = wilson(k1, n1)
    l2, u2 = wilson(k2, n2)
    d = p1 - p2
    lo = d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2)
    hi = d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)
    return (d, lo, hi)


def hill1(counts: Iterable[float]) -> float:
    c = np.array([x for x in counts if x > 0], dtype=float)
    if c.sum() <= 0:
        return float("nan")
    p = c / c.sum()
    return float(math.exp(-(p * np.log(p)).sum()))


def rarefied_hill1(counts: dict, depth: int = 10, reps: int = 2000, seed: int = 0) -> float:
    items = [k for k, v in counts.items() for _ in range(int(v))]
    if len(items) < depth:
        return float("nan")
    rng = np.random.default_rng(seed)
    arr = np.array(items, dtype=object)
    vals = []
    for _ in range(reps):
        sub = rng.choice(len(arr), size=depth, replace=False)
        vals.append(hill1(Counter(arr[sub]).values()))
    return float(np.mean(vals))


def ffh_mc(labels_a: list[str], labels_b: list[str], draws: int = 100_000, seed: int = 0) -> dict:
    """Fisher-Freeman-Halton exact test for a 2 x K table, Monte Carlo over fixed margins (permute group labels).
    Statistic: sum log(n_ij!) (larger = less probable table); p = P(T_sim >= T_obs)."""
    from scipy.special import gammaln

    cats = sorted(set(labels_a) | set(labels_b))
    if len(cats) < 2 or not labels_a or not labels_b:
        return {"p": 1.0, "categories": cats, "n_a": len(labels_a), "n_b": len(labels_b), "draws": 0}
    idx = {c: i for i, c in enumerate(cats)}
    y = np.array([idx[c] for c in labels_a + labels_b])
    na = len(labels_a)
    K = len(cats)

    def stat_from_counts(ca: np.ndarray, call: np.ndarray) -> np.ndarray:
        cb = call[None, :] - ca
        return gammaln(ca + 1).sum(-1) + gammaln(cb + 1).sum(-1)

    call = np.bincount(y, minlength=K)
    ca_obs = np.bincount(y[:na], minlength=K)
    t_obs = float(stat_from_counts(ca_obs[None, :], call)[0])
    rng = np.random.default_rng(seed)
    hits = 0
    done = 0
    batch = 5000
    while done < draws:
        b = min(batch, draws - done)
        perm = np.argsort(rng.random((b, len(y))), axis=1)[:, :na]
        sel = y[perm]
        ca = np.stack([np.bincount(r, minlength=K) for r in sel])
        ts = stat_from_counts(ca, call)
        hits += int((ts >= t_obs - 1e-9).sum())
        done += b
    return {"p": (hits + 1) / (draws + 1), "categories": cats, "counts_a": ca_obs.tolist(),
            "counts_b": (call - ca_obs).tolist(), "n_a": na, "n_b": len(labels_b), "draws": draws, "seed": seed}


def jsd(p: dict, q: dict) -> float:
    keys = sorted(set(p) | set(q))
    a = np.array([p.get(k, 0.0) for k in keys], dtype=float)
    b = np.array([q.get(k, 0.0) for k in keys], dtype=float)
    if a.sum() <= 0 or b.sum() <= 0:
        return float("nan")
    a, b = a / a.sum(), b / b.sum()
    m = 0.5 * (a + b)

    def kl(x, y):
        mask = x > 0
        return float((x[mask] * np.log(x[mask] / y[mask])).sum())

    return 0.5 * kl(a, m) + 0.5 * kl(b, m)
