#!/usr/bin/env python3
"""Statistics: normalised recovery with a two-way cluster bootstrap (source prompts x base prompts), Wilson
intervals, exact McNemar on CRN-paired outcomes, one-sided Wilcoxon, Spearman with permutation p."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from scipy import stats


def recovery(d_edit: np.ndarray, d_full: np.ndarray, src: list[str], base: list[str], n_boot: int = 2000,
             seed: int = 0, min_full: float = 1.0) -> dict[str, Any]:
    """recovery = mean(Delta_edit) / mean(Delta_full) over pairs with |Delta_full| >= min_full; CI by resampling
    source and base prompts independently (a pair enters with multiplicity count_src x count_base)."""
    d_edit = np.asarray(d_edit, float)
    d_full = np.asarray(d_full, float)
    ok = np.abs(d_full) >= min_full
    if ok.sum() == 0:
        return {"n": 0, "recovery": None}
    de, df = d_edit[ok], d_full[ok]
    s = np.array(src)[ok]
    b = np.array(base)[ok]
    us, ub = np.unique(s), np.unique(b)
    si = np.searchsorted(us, s)
    bi = np.searchsorted(ub, b)
    point = float(de.mean() / df.mean())
    rng = np.random.default_rng(seed)
    boots = []
    for _ in range(n_boot):
        cs = np.bincount(rng.integers(0, len(us), len(us)), minlength=len(us))
        cb = np.bincount(rng.integers(0, len(ub), len(ub)), minlength=len(ub))
        w = cs[si] * cb[bi]
        if w.sum() == 0 or (w * df).sum() == 0:
            continue
        boots.append(float((w * de).sum() / (w * df).sum()))
    lo, hi = (float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))) if boots else (None, None)
    return {"n": int(ok.sum()), "n_src": int(len(us)), "n_base": int(len(ub)), "recovery": point, "ci95": [lo, hi],
            "mean_delta_edit": float(de.mean()), "mean_delta_full": float(df.mean()),
            "iia_like_share_positive": float(np.mean(de > 0))}


def ratio_ci(num: np.ndarray, den_mean: float, src: list[str], base: list[str], n_boot: int = 2000, seed: int = 0
             ) -> dict[str, Any]:
    """mean(num) / den_mean with a two-way cluster bootstrap of the numerator (denominator held fixed)."""
    num = np.asarray(num, float)
    s, b = np.array(src), np.array(base)
    us, ub = np.unique(s), np.unique(b)
    si, bi = np.searchsorted(us, s), np.searchsorted(ub, b)
    rng = np.random.default_rng(seed)
    boots = []
    for _ in range(n_boot):
        cs = np.bincount(rng.integers(0, len(us), len(us)), minlength=len(us))
        cb = np.bincount(rng.integers(0, len(ub), len(ub)), minlength=len(ub))
        w = cs[si] * cb[bi]
        if w.sum():
            boots.append(float((w * num).sum() / w.sum() / den_mean))
    return {"ratio": float(num.mean() / den_mean) if den_mean else None,
            "ci95": [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))] if boots else None}


def wilson(k: int, n: int, z: float = 1.96) -> list[float | None]:
    if n == 0:
        return [None, None]
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [max(0.0, c - h), min(1.0, c + h)]


def mcnemar(a: list[bool], b: list[bool]) -> dict[str, Any]:
    """Exact two-sided McNemar on paired booleans (a vs b): discordant counts and p."""
    n10 = sum(1 for x, y in zip(a, b) if x and not y)
    n01 = sum(1 for x, y in zip(a, b) if y and not x)
    n = n10 + n01
    p = float(stats.binomtest(n10, n, 0.5).pvalue) if n else 1.0
    p1 = float(stats.binomtest(n10, n, 0.5, alternative="greater").pvalue) if n else 1.0
    return {"a_only": n10, "b_only": n01, "p_two_sided": p, "p_one_sided_a_gt_b": p1}


def wilcoxon_greater(x: np.ndarray, y: np.ndarray) -> float:
    d = np.asarray(x, float) - np.asarray(y, float)
    d = d[d != 0]
    if d.size < 3:
        return 1.0
    return float(stats.wilcoxon(d, alternative="greater").pvalue)


def cluster_wilcoxon_p(x: np.ndarray, y: np.ndarray, src: list[str], base: list[str], n_boot: int = 2000,
                       seed: int = 0) -> dict[str, Any]:
    """One-sided pair-level test of mean(x - y) > 0 with a two-way cluster bootstrap (p = share of resamples <= 0)."""
    d = np.asarray(x, float) - np.asarray(y, float)
    s, b = np.array(src), np.array(base)
    us, ub = np.unique(s), np.unique(b)
    si, bi = np.searchsorted(us, s), np.searchsorted(ub, b)
    rng = np.random.default_rng(seed)
    ms = []
    for _ in range(n_boot):
        cs = np.bincount(rng.integers(0, len(us), len(us)), minlength=len(us))
        cb = np.bincount(rng.integers(0, len(ub), len(ub)), minlength=len(ub))
        w = cs[si] * cb[bi]
        if w.sum():
            ms.append(float((w * d).sum() / w.sum()))
    ms = np.array(ms)
    return {"mean_diff": float(d.mean()), "p_cluster_boot": float((np.sum(ms <= 0) + 1) / (len(ms) + 1)),
            "p_wilcoxon_pairs": wilcoxon_greater(x, y)}


def spearman_perm(x: np.ndarray, y: np.ndarray, n_perm: int = 10000, seed: int = 0) -> dict[str, Any]:
    x, y = np.asarray(x, float), np.asarray(y, float)
    if len(x) < 4:
        return {"rho": None, "p_one_sided": None, "n": int(len(x))}
    rho = float(stats.spearmanr(x, y).statistic)
    rng = np.random.default_rng(seed)
    cnt = 0
    for _ in range(n_perm):
        r = stats.spearmanr(x, rng.permutation(y)).statistic
        if r >= rho:
            cnt += 1
    return {"rho": rho, "p_one_sided": (cnt + 1) / (n_perm + 1), "n": int(len(x))}


def partial_spearman(x: np.ndarray, y: np.ndarray, z: np.ndarray) -> float | None:
    """Spearman partial correlation of x and y controlling z (rank-residual method)."""
    if len(x) < 5:
        return None
    rx, ry, rz = (stats.rankdata(v) for v in (x, y, z))
    A = np.vstack([rz, np.ones_like(rz)]).T
    ex = rx - A @ np.linalg.lstsq(A, rx, rcond=None)[0]
    ey = ry - A @ np.linalg.lstsq(A, ry, rcond=None)[0]
    den = np.sqrt((ex ** 2).sum() * (ey ** 2).sum())
    return float((ex * ey).sum() / den) if den else None
