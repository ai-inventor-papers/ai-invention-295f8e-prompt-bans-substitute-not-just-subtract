"""Exact small-sample statistics used by the record repair (scipy where it is exact, closed forms otherwise)."""

from __future__ import annotations

import math
from typing import Sequence

import numpy as np
from scipy import stats as st


def clopper_pearson(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    lo = 0.0 if k == 0 else float(st.beta.ppf(alpha / 2, k, n - k + 1))
    hi = 1.0 if k == n else float(st.beta.ppf(1 - alpha / 2, k + 1, n - k))
    return (lo, hi)


def binom_two_sided(k: int, n: int, p0: float = 0.5) -> float:
    """Exact two-sided binomial test (minimum-likelihood method, as scipy.stats.binomtest)."""
    if n == 0:
        return 1.0
    return float(st.binomtest(k, n, p0, alternative="two-sided").pvalue)


def mcnemar_exact(b: int, c: int) -> float:
    """Exact McNemar: two-sided binomial test of b against b + c at 0.5."""
    return binom_two_sided(b, b + c, 0.5) if b + c else 1.0


def mcnemar_from_pairs(xs: Sequence[int], ys: Sequence[int]) -> dict:
    b = sum(1 for x, y in zip(xs, ys) if x == 1 and y == 0)
    c = sum(1 for x, y in zip(xs, ys) if x == 0 and y == 1)
    n = len(xs)
    return {"n": n, "b": b, "c": c, "p": mcnemar_exact(b, c),
            "effect": (sum(xs) - sum(ys)) / n if n else None}


def sign_test(diffs: Sequence[float]) -> dict:
    pos = sum(1 for d in diffs if d > 0)
    neg = sum(1 for d in diffs if d < 0)
    return {"n_pos": pos, "n_neg": neg, "n_zero": sum(1 for d in diffs if d == 0),
            "p": binom_two_sided(pos, pos + neg) if pos + neg else 1.0}


def sign_test_floor(n_clusters: int) -> float:
    """Smallest attainable two-sided p of an exact sign test over n clusters (all n in one direction)."""
    return min(1.0, 2.0 * 0.5 ** n_clusters)


def durkalski_mcnemar(clusters: dict[str, tuple[int, int]]) -> dict:
    """Durkalski et al. (2003) cluster-adjusted McNemar statistic.

    clusters maps a cluster id to (b_k, c_k), its counts of (x=1, y=0) and (x=0, y=1) pairs. The statistic is
    (B - C)^2 / sum_k (b_k - c_k)^2, referred to chi-square with 1 df (asymptotic; reported as a sensitivity).
    """
    B = sum(b for b, _ in clusters.values())
    C = sum(c for _, c in clusters.values())
    den = sum((b - c) ** 2 for b, c in clusters.values())
    if den == 0:
        return {"B": B, "C": C, "chi2": None, "p": None, "n_clusters": len(clusters)}
    chi2 = (B - C) ** 2 / den
    return {"B": B, "C": C, "chi2": chi2, "p": float(st.chi2.sf(chi2, 1)), "n_clusters": len(clusters)}


def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    ph = k / n
    den = 1 + z * z / n
    c = (ph + z * z / (2 * n)) / den
    h = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / den
    return (c - h, c + h)


def cohen_kappa(a: Sequence[str], b: Sequence[str]) -> float | None:
    if not a or len(a) != len(b):
        return None
    cats = sorted(set(a) | set(b))
    n = len(a)
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    pe = sum((sum(1 for x in a if x == c) / n) * (sum(1 for y in b if y == c) / n) for c in cats)
    if pe >= 1.0:
        return 1.0 if po == 1.0 else 0.0
    return (po - pe) / (1 - pe)


def cluster_bootstrap_mean_diff(units: list[dict], key: str = "task", n_boot: int = 2000,
                                seed: int = 20261022) -> list[float]:
    """Percentile interval of mean(x) - mean(y), resampling clusters with replacement (as the NLA artifact)."""
    clusters: dict = {}
    for u in units:
        clusters.setdefault(u[key], []).append(u)
    keys = sorted(clusters)
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(n_boot):
        pick = rng.choice(len(keys), size=len(keys), replace=True)
        s = [u for i in pick for u in clusters[keys[i]]]
        if s:
            vals.append(float(np.mean([u["x"] for u in s]) - np.mean([u["y"] for u in s])))
    return [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))]
