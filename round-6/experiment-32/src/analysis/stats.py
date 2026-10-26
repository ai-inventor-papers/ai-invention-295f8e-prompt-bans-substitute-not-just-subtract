#!/usr/bin/env python3
"""Shared statistics for the committed analyses (hashed in commit #2): exact McNemar, Wilson CI, Holm,
task-cluster bootstrap, Spearman."""

from __future__ import annotations

import math
from typing import Any, Callable, Sequence

import numpy as np
from scipy import stats as ss


def mcnemar_exact(x: Sequence[int], y: Sequence[int]) -> dict[str, Any]:
    """Paired binary outcomes. b = x=1,y=0; c = x=0,y=1; two-sided exact binomial p on b of b+c (p = 1 if b+c = 0)."""
    x = np.asarray(x, dtype=int)
    y = np.asarray(y, dtype=int)
    b = int(((x == 1) & (y == 0)).sum())
    c = int(((x == 0) & (y == 1)).sum())
    p = float(ss.binomtest(b, b + c, 0.5).pvalue) if b + c > 0 else 1.0
    return {"n": int(len(x)), "b": b, "c": c, "p": p, "mean_x": float(x.mean()) if len(x) else None,
            "mean_y": float(y.mean()) if len(y) else None, "effect": float(x.mean() - y.mean()) if len(x) else None}


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float | None, float | None]:
    if n == 0:
        return (None, None)
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, c - h), min(1.0, c + h))


def rate(xs: Sequence[int]) -> dict[str, Any]:
    k, n = int(sum(xs)), len(xs)
    lo, hi = wilson(k, n)
    return {"k": k, "n": n, "rate": (k / n) if n else None, "wilson95": [lo, hi]}


def holm(ps: dict[str, float]) -> dict[str, float]:
    items = sorted(ps.items(), key=lambda kv: kv[1])
    m = len(items)
    out, run = {}, 0.0
    for i, (k, p) in enumerate(items):
        adj = min(1.0, (m - i) * p)
        run = max(run, adj)
        out[k] = run
    return out


def cluster_bootstrap(units: list[dict[str, Any]], stat: Callable[[list[dict[str, Any]]], float | None],
                      cluster_key: str = "task", n_boot: int = 2000, seed: int = 20261022) -> dict[str, Any]:
    clusters: dict[Any, list[dict[str, Any]]] = {}
    for u in units:
        clusters.setdefault(u[cluster_key], []).append(u)
    keys = sorted(clusters)
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(n_boot):
        pick = rng.choice(len(keys), size=len(keys), replace=True)
        sample = [u for i in pick for u in clusters[keys[i]]]
        v = stat(sample)
        if v is not None:
            vals.append(v)
    if not vals:
        return {"ci95": [None, None], "n_clusters": len(keys)}
    return {"ci95": [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))], "n_clusters": len(keys),
            "n_boot": len(vals)}


def spearman(a: Sequence[float], b: Sequence[float]) -> dict[str, Any]:
    if len(a) < 3:
        return {"rho": None, "p": None, "n": len(a)}
    r = ss.spearmanr(a, b)
    rho = float(r.statistic) if np.isfinite(r.statistic) else None
    return {"rho": rho, "p": float(r.pvalue) if np.isfinite(r.pvalue) else None, "n": len(a)}


def kappa(a: Sequence[str], b: Sequence[str]) -> float | None:
    if not a:
        return None
    labs = sorted(set(a) | set(b))
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((sum(x == l for x in a) / n) * (sum(y == l for y in b) / n) for l in labs)
    return float((po - pe) / (1 - pe)) if pe < 1 else 1.0
