#!/usr/bin/env python3
"""Statistics used by every claim: JS over top-K supports + tail bucket (iteration-8 base_arm.js_div, verbatim), share of
the anchor gap (ratio of sums and mean of ratios), percentile bootstrap, exact two-sided McNemar, exact sign-flip test,
Holm, Wilson and Newcombe intervals."""

from __future__ import annotations

import itertools
import math
from typing import Sequence

import numpy as np


def js_div(ia: list[int], la: list[float], ib: list[int], lb: list[float]) -> float:
    """JS divergence (nats) between two distributions given by top-K supports; tail mass lumped into one bucket."""
    pa = {i: math.exp(l) for i, l in zip(ia, la)}
    pb = {i: math.exp(l) for i, l in zip(ib, lb)}
    keys = set(pa) | set(pb)
    ta = max(0.0, 1 - sum(pa.values()))
    tb = max(0.0, 1 - sum(pb.values()))
    js = 0.0
    for k in list(keys) + ["_tail"]:
        a = pa.get(k, 0.0) if k != "_tail" else ta
        b = pb.get(k, 0.0) if k != "_tail" else tb
        m = 0.5 * (a + b)
        if a > 0:
            js += 0.5 * a * math.log(a / m)
        if b > 0:
            js += 0.5 * b * math.log(b / m)
    return js


def share(m_I: Sequence[float], m_X: Sequence[float], m_B: Sequence[float]) -> float:
    """Ratio of sums: sum (m_I - m_X) / sum (m_I - m_B)."""
    num = float(np.sum(np.asarray(m_I) - np.asarray(m_X)))
    den = float(np.sum(np.asarray(m_I) - np.asarray(m_B)))
    return num / den if abs(den) > 1e-12 else float("nan")


def share_mean_of_ratios(m_I: Sequence[float], m_X: Sequence[float], m_B: Sequence[float]) -> float:
    r = [(a - x) / (a - b) for a, x, b in zip(m_I, m_X, m_B) if abs(a - b) > 1e-9]
    return float(np.mean(r)) if r else float("nan")


def boot_ci(fn, n: int, B: int = 10000, seed: int = 0, alpha: float = 0.05) -> tuple[float, float]:
    """Percentile bootstrap over n units: fn(idx array) -> statistic."""
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(B):
        idx = rng.integers(0, n, n)
        v = fn(idx)
        if v is not None and np.isfinite(v):
            vals.append(v)
    if not vals:
        return (float("nan"), float("nan"))
    return (float(np.percentile(vals, 100 * alpha / 2)), float(np.percentile(vals, 100 * (1 - alpha / 2))))


def boot_share_ci(m_I, m_X, m_B, B: int = 10000, seed: int = 0) -> tuple[float, float]:
    a, x, b = map(np.asarray, (m_I, m_X, m_B))
    return boot_ci(lambda idx: share(a[idx], x[idx], b[idx]), len(a), B, seed)


def boot_mean_ci(v, B: int = 10000, seed: int = 0) -> tuple[float, float]:
    v = np.asarray(v, dtype=float)
    return boot_ci(lambda idx: float(v[idx].mean()), len(v), B, seed)


def mcnemar_exact(b: int, c: int) -> float:
    """Exact two-sided McNemar p from the discordant counts b, c (binomial(b + c, 1/2))."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    p = sum(math.comb(n, i) for i in range(0, k + 1)) / 2 ** n
    return float(min(1.0, 2 * p))


def sign_flip_p(d: Sequence[float]) -> float:
    """Exact two-sided sign-flip test of mean(d) = 0 over all 2^n sign patterns (n <= 20)."""
    d = np.asarray(d, dtype=float)
    n = len(d)
    if n == 0:
        return float("nan")
    obs = abs(d.mean())
    cnt = 0
    tot = 0
    for signs in itertools.product((1.0, -1.0), repeat=n):
        tot += 1
        if abs((d * np.asarray(signs)).mean()) >= obs - 1e-12:
            cnt += 1
    return cnt / tot


def holm(ps: Sequence[float]) -> list[float]:
    ps = list(ps)
    m = len(ps)
    order = sorted(range(m), key=lambda i: (ps[i] if ps[i] == ps[i] else 1.0))
    adj = [0.0] * m
    run = 0.0
    for r, i in enumerate(order):
        p = ps[i] if ps[i] == ps[i] else 1.0
        run = max(run, min(1.0, (m - r) * p))
        adj[i] = run
    return adj


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, c - h), min(1.0, c + h))


def newcombe(k1: int, n1: int, k2: int, n2: int) -> tuple[float, float]:
    """Newcombe hybrid score interval for p1 - p2."""
    p1, p2 = k1 / n1, k2 / n2
    l1, u1 = wilson(k1, n1)
    l2, u2 = wilson(k2, n2)
    d = p1 - p2
    return (d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2), d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2))


def empirical_p_upper(x: float, null: Sequence[float]) -> float:
    """(1 + #null >= x) / (1 + n)."""
    null = np.asarray(null, dtype=float)
    return float((1 + np.sum(null >= x)) / (1 + len(null)))
