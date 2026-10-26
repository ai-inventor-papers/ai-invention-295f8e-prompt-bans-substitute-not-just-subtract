"""Small statistics toolkit: Wilson / Newcombe intervals, Hill numbers (plug-in, Miller-Madow, rarefied),
Cohen's kappa, Kish ESS and the PSIS generalized-Pareto k-hat (Zhang & Stephens 2009, as used by Vehtari et al.)."""

from __future__ import annotations

import math
from collections import Counter
from typing import Iterable, Sequence

import numpy as np
from scipy.stats import norm


def wilson(k: int, n: int, conf: float = 0.95) -> tuple[float, float]:
    if n <= 0:
        return (math.nan, math.nan)
    z = norm.ppf(1 - (1 - conf) / 2)
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, c - h), min(1.0, c + h))


def newcombe_diff(k1: int, n1: int, k2: int, n2: int, conf: float = 0.95) -> tuple[float, float, float]:
    """Newcombe hybrid-score interval (method 10) for p1 - p2 of independent proportions. Returns (d, lo, hi)."""
    if n1 <= 0 or n2 <= 0:
        return (math.nan, math.nan, math.nan)
    p1, p2 = k1 / n1, k2 / n2
    l1, u1 = wilson(k1, n1, conf)
    l2, u2 = wilson(k2, n2, conf)
    d = p1 - p2
    lo = d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2)
    hi = d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)
    return (d, lo, hi)


def counts_of(labels: Iterable[str]) -> np.ndarray:
    c = Counter(labels)
    return np.array(sorted(c.values(), reverse=True), dtype=float)


def hill1(counts: Sequence[float]) -> float:
    c = np.asarray(counts, dtype=float)
    c = c[c > 0]
    n = c.sum()
    if n <= 0:
        return math.nan
    p = c / n
    return float(math.exp(-(p * np.log(p)).sum()))


def hill1_miller_madow(counts: Sequence[float]) -> float:
    c = np.asarray(counts, dtype=float)
    c = c[c > 0]
    n = c.sum()
    if n <= 0:
        return math.nan
    p = c / n
    h = -(p * np.log(p)).sum() + (len(c) - 1) / (2 * n)
    return float(math.exp(h))


def _hill_rows(M: np.ndarray) -> np.ndarray:
    n = M.sum(axis=1, keepdims=True)
    p = np.where(M > 0, M / np.maximum(n, 1), 1.0)
    return np.exp(-(np.where(M > 0, (M / np.maximum(n, 1)) * np.log(p), 0.0)).sum(axis=1))


def rarefied_hill1(counts: Sequence[float], depth: int, n_sub: int = 1000,
                   rng: np.random.Generator | None = None) -> float:
    """Mean over n_sub subsamples of size `depth` drawn WITHOUT replacement of exp(Shannon) of the subsample."""
    c = np.asarray(counts, dtype=np.int64)
    c = c[c > 0]
    if c.sum() < depth or depth <= 0:
        return math.nan
    if len(c) == 1:
        return 1.0
    rng = rng or np.random.default_rng(0)
    M = rng.multivariate_hypergeometric(c, depth, size=n_sub)
    return float(_hill_rows(M.astype(float)).mean())


def boot_rarefied_hill1(counts: Sequence[float], depth: int, n_boot: int = 2000, n_sub: int = 200,
                        rng: np.random.Generator | None = None, conf: float = 0.90) -> tuple[float, float]:
    """Percentile interval of rarefied Hill-1 over multinomial resamples of the row (programs resampled)."""
    c = np.asarray(counts, dtype=np.int64)
    c = c[c > 0]
    n = int(c.sum())
    if n < depth:
        return (math.nan, math.nan)
    rng = rng or np.random.default_rng(1)
    p = c / n
    vals = np.empty(n_boot)
    for b in range(n_boot):
        cb = rng.multinomial(n, p)
        cb = cb[cb > 0]
        if len(cb) == 1:
            vals[b] = 1.0
            continue
        M = rng.multivariate_hypergeometric(cb, depth, size=n_sub)
        vals[b] = _hill_rows(M.astype(float)).mean()
    a = (1 - conf) / 2
    return (float(np.quantile(vals, a)), float(np.quantile(vals, 1 - a)))


def cohen_kappa(a: Sequence[str], b: Sequence[str]) -> float:
    a, b = list(a), list(b)
    n = len(a)
    if n == 0:
        return math.nan
    cats = sorted(set(a) | set(b))
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[c] * cb[c] for c in cats) / (n * n)
    return float((po - pe) / (1 - pe)) if pe < 1 else (1.0 if po == 1 else math.nan)


def kish_ess(logw: np.ndarray) -> float:
    lw = np.asarray(logw, dtype=float)
    lw = lw[np.isfinite(lw)]
    if len(lw) == 0:
        return math.nan
    w = np.exp(lw - lw.max())
    return float(w.sum() ** 2 / (w * w).sum())


def psis_khat(logw: np.ndarray) -> float:
    """PSIS tail-shape diagnostic k-hat of importance log-weights (tail size M = min(0.2 S, 3 sqrt(S))),
    following the arviz `_psislw` / `_gpdfit` implementation (Vehtari, Simpson, Gelman, Yao & Gabry, JMLR 2024)."""
    lw = np.asarray(logw, dtype=float)
    lw = lw[np.isfinite(lw)]
    S = len(lw)
    if S < 10:
        return math.nan
    M = int(min(0.2 * S, 3 * math.sqrt(S)))
    if M < 5:
        return math.nan
    lw = np.sort(lw)
    mx = lw[-1]
    cutoff = lw[-M - 1]
    tail = np.exp(lw[-M:] - mx) - math.exp(cutoff - mx)
    tail = np.sort(tail[tail > 0])
    if len(tail) < 5:
        return math.nan
    return _gpdfit(tail)[0]


def _gpdfit(x: np.ndarray) -> tuple[float, float]:
    """Zhang & Stephens (2009) empirical-Bayes generalized-Pareto fit of sorted exceedances (arviz convention:
    k > 0 is a heavy tail; k > 0.7 means the importance-sampling estimate is unreliable)."""
    x = np.sort(np.asarray(x, dtype=float))
    n = len(x)
    prior_bs, prior_k = 3.0, 10.0
    m = 30 + int(math.sqrt(n))
    b = 1 - np.sqrt(m / (np.arange(1, m + 1, dtype=float) - 0.5))
    b /= prior_bs * x[max(0, int(n / 4 + 0.5) - 1)]
    b += 1 / x[-1]
    with np.errstate(invalid="ignore", divide="ignore", over="ignore"):
        k = np.log1p(-b[:, None] * x).mean(axis=1)
        L = n * (np.log(-(b / k)) - k - 1)
        w = 1 / np.exp(L - L[:, None]).sum(axis=1)
    ok = np.isfinite(w) & (w >= 10 * np.finfo(float).eps)
    if not ok.any():
        return (math.nan, math.nan)
    w, b = w[ok], b[ok]
    w = w / w.sum()
    bp = float((b * w).sum())
    kp = float(np.log1p(-bp * x).mean())
    sigma = -kp / bp
    kp = (n * kp + prior_k * 0.5) / (n + prior_k)
    return (kp, sigma)


def logsumexp(a: np.ndarray) -> float:
    a = np.asarray(a, dtype=float)
    a = a[np.isfinite(a)]
    if len(a) == 0:
        return -math.inf
    m = a.max()
    return float(m + math.log(np.exp(a - m).sum()))


def spearman(a: np.ndarray, b: np.ndarray) -> float:
    from scipy.stats import spearmanr

    a, b = np.asarray(a, float), np.asarray(b, float)
    if len(a) < 3 or np.ptp(a) == 0 or np.ptp(b) == 0:
        return math.nan
    return float(spearmanr(a, b).correlation)
