#!/usr/bin/env python3
"""Statistics for iteration 7 (numpy/scipy only): Spearman with permutation p and bootstrap CIs, the tie ceiling,
pooled within-task rank correlation, paired bootstrap of rho differences, binomial-GLM calibration with held-out
MAE, AUC, exact McNemar, exact binomial, Holm."""

from __future__ import annotations

import math
from typing import Any, Sequence

import numpy as np
from scipy import stats


def ranks(x: Sequence[float]) -> np.ndarray:
    return stats.rankdata(np.asarray(x, dtype=float), method="average")


def spearman(x: Sequence[float], y: Sequence[float]) -> float:
    x, y = np.asarray(x, float), np.asarray(y, float)
    ok = ~(np.isnan(x) | np.isnan(y))
    x, y = x[ok], y[ok]
    if len(x) < 3 or np.ptp(x) == 0 or np.ptp(y) == 0:
        return float("nan")
    rx, ry = ranks(x), ranks(y)
    return float(np.corrcoef(rx, ry)[0, 1])


def perm_p(x: Sequence[float], y: Sequence[float], n: int = 10000, seed: int = 0,
           alternative: str = "greater") -> float:
    x, y = np.asarray(x, float), np.asarray(y, float)
    ok = ~(np.isnan(x) | np.isnan(y))
    x, y = x[ok], y[ok]
    obs = spearman(x, y)
    if obs != obs:
        return float("nan")
    rx, ry = ranks(x), ranks(y)
    rx = (rx - rx.mean()) / rx.std()
    ry = (ry - ry.mean()) / ry.std()
    rng = np.random.default_rng(seed)
    null = np.array([np.mean(rx * ry[rng.permutation(len(ry))]) for _ in range(n)])
    if alternative == "greater":
        return float((1 + np.sum(null >= obs - 1e-12)) / (1 + n))
    if alternative == "less":
        return float((1 + np.sum(null <= obs + 1e-12)) / (1 + n))
    return float((1 + np.sum(np.abs(null) >= abs(obs) - 1e-12)) / (1 + n))


def tie_ceiling(y: Sequence[float]) -> float:
    """Spearman of y with a perfectly concordant untied predictor (ties of y broken arbitrarily)."""
    y = np.asarray(y, float)
    y = y[~np.isnan(y)]
    if len(y) < 3 or np.ptp(y) == 0:
        return float("nan")
    x = stats.rankdata(y, method="ordinal")
    return spearman(x, y)


def kendall(x: Sequence[float], y: Sequence[float]) -> float:
    x, y = np.asarray(x, float), np.asarray(y, float)
    ok = ~(np.isnan(x) | np.isnan(y))
    if ok.sum() < 3:
        return float("nan")
    return float(stats.kendalltau(x[ok], y[ok]).statistic)


def boot_ci(x: Sequence[float], y: Sequence[float], n: int = 10000, seed: int = 1) -> tuple[float, float]:
    x, y = np.asarray(x, float), np.asarray(y, float)
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(n):
        i = rng.integers(0, len(x), len(x))
        r = spearman(x[i], y[i])
        if r == r:
            vals.append(r)
    if not vals:
        return (float("nan"), float("nan"))
    return (float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5)))


def paired_boot_diff(xa: Sequence[float], xb: Sequence[float], y: Sequence[float], n: int = 10000,
                     seed: int = 2) -> dict[str, float]:
    """rho(xa, y) - rho(xb, y) over direction resamples; 95% percentile CI."""
    xa, xb, y = np.asarray(xa, float), np.asarray(xb, float), np.asarray(y, float)
    rng = np.random.default_rng(seed)
    d = []
    for _ in range(n):
        i = rng.integers(0, len(y), len(y))
        ra, rb = spearman(xa[i], y[i]), spearman(xb[i], y[i])
        if ra == ra and rb == rb:
            d.append(ra - rb)
    obs = spearman(xa, y) - spearman(xb, y)
    if not d:
        return {"diff": obs, "lo": float("nan"), "hi": float("nan"), "n_valid": 0}
    return {"diff": obs, "lo": float(np.percentile(d, 2.5)), "hi": float(np.percentile(d, 97.5)), "n_valid": len(d)}


def pooled_within(groups: list[tuple[Sequence[float], Sequence[float]]]) -> float:
    """Pearson correlation of within-task ranks (each task ranked separately, ranks scaled to [0, 1])."""
    xs, ys = [], []
    for x, y in groups:
        x, y = np.asarray(x, float), np.asarray(y, float)
        ok = ~(np.isnan(x) | np.isnan(y))
        x, y = x[ok], y[ok]
        if len(x) < 3:
            continue
        xs.append((ranks(x) - 1) / (len(x) - 1))
        ys.append((ranks(y) - 1) / (len(y) - 1))
    if not xs:
        return float("nan")
    X, Y = np.concatenate(xs), np.concatenate(ys)
    if np.ptp(X) == 0 or np.ptp(Y) == 0:
        return float("nan")
    return float(np.corrcoef(X, Y)[0, 1])


def pooled_perm_p(groups: list[tuple[Sequence[float], Sequence[float]]], n: int = 10000, seed: int = 3) -> float:
    obs = pooled_within(groups)
    rng = np.random.default_rng(seed)
    cnt = 0
    for _ in range(n):
        g2 = [(x, np.asarray(y)[rng.permutation(len(y))]) for x, y in groups]
        cnt += pooled_within(g2) >= obs - 1e-12
    return float((1 + cnt) / (1 + n))


def auc(score: Sequence[float], label: Sequence[int]) -> float:
    s, l = np.asarray(score, float), np.asarray(label, int)
    pos, neg = s[l == 1], s[l == 0]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    u = stats.mannwhitneyu(pos, neg, alternative="two-sided").statistic
    return float(u / (len(pos) * len(neg)))


def glm_fit(m: np.ndarray, k: np.ndarray, n: np.ndarray) -> tuple[float, float]:
    """Binomial GLM k ~ Bin(n, sigmoid(b0 + b1 m)) by Newton-Raphson (ridge 1e-6)."""
    X = np.column_stack([np.ones_like(m), m])
    b = np.zeros(2)
    for _ in range(100):
        p = 1 / (1 + np.exp(-(X @ b)))
        W = n * p * (1 - p)
        g = X.T @ (k - n * p)
        Hm = X.T @ (X * W[:, None]) + 1e-6 * np.eye(2)
        step = np.linalg.solve(Hm, g)
        b = b + step
        if np.abs(step).max() < 1e-10:
            break
    return float(b[0]), float(b[1])


def calibration(m: Sequence[float], k: Sequence[int], n: Sequence[int], strata: Sequence[str], n_splits: int = 10,
                seed: int = 4) -> dict[str, Any]:
    """Held-out MAE of the binomial-GLM fit over random half-splits stratified by `strata`."""
    m, k, n = np.asarray(m, float), np.asarray(k, float), np.asarray(n, float)
    strata = np.asarray(strata)
    ok = ~np.isnan(m)
    m, k, n, strata = m[ok], k[ok], n[ok], strata[ok]
    b0, b1 = glm_fit(m, k, n)
    rng = np.random.default_rng(seed)
    maes = []
    for _ in range(n_splits):
        tr = np.zeros(len(m), bool)
        for s in np.unique(strata):
            idx = np.where(strata == s)[0]
            idx = idx[rng.permutation(len(idx))]
            tr[idx[: (len(idx) + 1) // 2]] = True
        if tr.all() or (~tr).all():
            continue
        c0, c1 = glm_fit(m[tr], k[tr], n[tr])
        p = 1 / (1 + np.exp(-(c0 + c1 * m[~tr])))
        maes.append(float(np.mean(np.abs(p - k[~tr] / n[~tr]))))
    return {"b0": b0, "b1": b1, "mae_heldout_mean": float(np.mean(maes)) if maes else float("nan"),
            "mae_heldout_splits": maes, "n_cells": int(len(m))}


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar on discordant counts b (A only) and c (B only)."""
    n = b + c
    if n == 0:
        return 1.0
    return float(min(1.0, 2 * stats.binom.cdf(min(b, c), n, 0.5)))


def binom_greater(k: int, n: int, p0: float) -> float:
    if n == 0:
        return 1.0
    return float(stats.binomtest(int(k), int(n), min(max(p0, 1e-9), 1 - 1e-9), alternative="greater").pvalue)


def holm(pvals: dict[str, float]) -> dict[str, float]:
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m = len(items)
    out, run = {}, 0.0
    for i, (k, p) in enumerate(items):
        adj = min(1.0, (m - i) * p)
        run = max(run, adj)
        out[k] = run
    return out


def fisher_exact(a: int, b: int, c: int, d: int) -> float:
    return float(stats.fisher_exact([[a, b], [c, d]], alternative="greater").pvalue)


def logit(p: float, eps: float = 1e-12) -> float:
    p = min(max(p, eps), 1 - eps)
    return math.log(p) - math.log(1 - p)
