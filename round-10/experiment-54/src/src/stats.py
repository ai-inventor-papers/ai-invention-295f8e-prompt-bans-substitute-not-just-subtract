#!/usr/bin/env python3
"""Statistics (frozen in commit #1): Wilson score intervals, Newcombe's hybrid-score interval for an unpaired
difference (method 10) and for a paired difference (Newcombe 1998b method 10, continuity-corrected phi), the
Jonckheere-Terpstra trend test (permutation p and tie-corrected normal approximation), Clopper-Pearson bounds, a
paired bootstrap and Holm's step-down adjustment."""
from __future__ import annotations

import math
from typing import Any, Sequence

import numpy as np
from scipy import stats as sps

Z95 = 1.959963984540054


def wilson(k: int, n: int, z: float = Z95) -> tuple[float, float]:
    if n <= 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, centre - half), min(1.0, centre + half))


def rate(k: int, n: int) -> dict[str, Any]:
    lo, hi = wilson(k, n) if n else (None, None)
    return {"k": int(k), "n": int(n), "rate": (k / n) if n else None, "wilson95": [lo, hi]}


def newcombe_unpaired(k1: int, n1: int, k2: int, n2: int) -> tuple[float, float, float]:
    """95% CI for p1 - p2 (independent samples): L = d - sqrt((p1-l1)^2 + (u2-p2)^2),
    U = d + sqrt((u1-p1)^2 + (p2-l2)^2)."""
    if n1 <= 0 or n2 <= 0:
        return (float("nan"), float("nan"), float("nan"))
    p1, p2 = k1 / n1, k2 / n2
    l1, u1 = wilson(k1, n1)
    l2, u2 = wilson(k2, n2)
    d = p1 - p2
    return (d, d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2), d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2))


def newcombe_paired(a: int, b: int, c: int, d: int) -> tuple[float, float, float]:
    """95% CI for p1 - p2 from paired binary data: a = (1,1), b = (1,0), c = (0,1), d = (0,0); p1 = (a+b)/n,
    p2 = (a+c)/n. phi = (ad - bc)/sqrt((a+b)(c+d)(a+c)(b+d)) with numerator max(ad - bc - n/2, 0) when ad > bc,
    phi = 0 if any margin is 0. L = gap - sqrt((p1-l1)^2 - 2 phi (p1-l1)(u2-p2) + (u2-p2)^2),
    U = gap + sqrt((u1-p1)^2 - 2 phi (u1-p1)(p2-l2) + (p2-l2)^2)."""
    n = a + b + c + d
    if n == 0:
        return (float("nan"), float("nan"), float("nan"))
    p1, p2 = (a + b) / n, (a + c) / n
    l1, u1 = wilson(a + b, n)
    l2, u2 = wilson(a + c, n)
    gap = p1 - p2
    den = (a + b) * (c + d) * (a + c) * (b + d)
    if den == 0:
        phi = 0.0
    else:
        num = a * d - b * c
        if num > 0:
            num = max(num - n / 2.0, 0.0)
        phi = num / math.sqrt(den)
    dl = math.sqrt(max(0.0, (p1 - l1) ** 2 - 2 * phi * (p1 - l1) * (u2 - p2) + (u2 - p2) ** 2))
    du = math.sqrt(max(0.0, (u1 - p1) ** 2 - 2 * phi * (u1 - p1) * (p2 - l2) + (p2 - l2) ** 2))
    return (gap, max(-1.0, gap - dl), min(1.0, gap + du))


def paired_bootstrap_gap(x1: Sequence[int], x2: Sequence[int], B: int = 10_000, seed: int = 20261026
                         ) -> tuple[float, float, float]:
    x1 = np.asarray(x1, float)
    x2 = np.asarray(x2, float)
    n = len(x1)
    if n == 0:
        return (float("nan"), float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(B, n))
    g = x1[idx].mean(axis=1) - x2[idx].mean(axis=1)
    return (float(x1.mean() - x2.mean()), float(np.quantile(g, 0.025)), float(np.quantile(g, 0.975)))


def jt_statistic(groups: Sequence[Sequence[float]]) -> float:
    """J = sum over pairs of groups i < j of [count(x_i > x_j) + 0.5 count(x_i == x_j)] (large J = decreasing)."""
    J = 0.0
    gs = [np.asarray(g, float) for g in groups]
    for i in range(len(gs)):
        for j in range(i + 1, len(gs)):
            if len(gs[i]) == 0 or len(gs[j]) == 0:
                continue
            d = gs[i][:, None] - gs[j][None, :]
            J += float((d > 0).sum()) + 0.5 * float((d == 0).sum())
    return J


def _jt_binary_vec(ones: np.ndarray, sizes: np.ndarray) -> np.ndarray:
    """Vectorised J for binary outcomes: ones is (m, G) counts of 1s per group."""
    zeros = sizes[None, :] - ones
    J = np.zeros(ones.shape[0])
    G = ones.shape[1]
    for i in range(G):
        for j in range(i + 1, G):
            J += ones[:, i] * zeros[:, j] + 0.5 * (ones[:, i] * ones[:, j] + zeros[:, i] * zeros[:, j])
    return J


def jt_normal(groups: Sequence[Sequence[float]]) -> dict[str, Any]:
    """Tie-corrected normal approximation (Hollander & Wolfe), one-sided for a decreasing trend (J large)."""
    sizes = np.array([len(g) for g in groups], float)
    y = np.concatenate([np.asarray(g, float) for g in groups]) if len(groups) else np.zeros(0)
    N = float(len(y))
    J = jt_statistic(groups)
    if N < 3:
        return {"J": J, "z": None, "p": None}
    _, t = np.unique(y, return_counts=True)
    t = t.astype(float)
    EJ = (N * N - float((sizes ** 2).sum())) / 4.0
    v1 = (N * (N - 1) * (2 * N + 5) - float((sizes * (sizes - 1) * (2 * sizes + 5)).sum())
          - float((t * (t - 1) * (2 * t + 5)).sum())) / 72.0
    v2 = float((sizes * (sizes - 1) * (sizes - 2)).sum()) * float((t * (t - 1) * (t - 2)).sum()) / \
        (36.0 * N * (N - 1) * (N - 2))
    v3 = float((sizes * (sizes - 1)).sum()) * float((t * (t - 1)).sum()) / (8.0 * N * (N - 1))
    var = v1 + v2 + v3
    if var <= 0:
        return {"J": J, "E_J": EJ, "var": var, "z": None, "p": None}
    z = (J - EJ) / math.sqrt(var)
    return {"J": J, "E_J": EJ, "var": var, "z": z, "p": float(sps.norm.sf(z))}


def jt_test(groups: Sequence[Sequence[int]], n_perm: int = 100_000, seed: int = 20261026) -> dict[str, Any]:
    """One-sided JT test of a decreasing trend over ordered groups of 0/1 outcomes: permutation p (pooled outcomes
    permuted over the fixed group sizes) = (#{J_perm >= J_obs} + 1) / (n_perm + 1); normal approximation beside it."""
    sizes = np.array([len(g) for g in groups], int)
    y = np.concatenate([np.asarray(g, np.int8) for g in groups]) if len(groups) else np.zeros(0, np.int8)
    obs = jt_statistic(groups)
    norm = jt_normal(groups)
    if len(y) == 0 or y.min() == y.max():
        return {"J": obs, "p_perm": None, "p_normal": norm.get("p"), "degenerate": True, "sizes": sizes.tolist()}
    rng = np.random.default_rng(seed)
    bounds = np.cumsum([0] + sizes.tolist())
    ge, done, chunk = 0, 0, 5000
    while done < n_perm:
        m = min(chunk, n_perm - done)
        P = rng.permuted(np.tile(y, (m, 1)), axis=1)
        ones = np.stack([P[:, bounds[g]:bounds[g + 1]].sum(axis=1) for g in range(len(sizes))], axis=1)
        J = _jt_binary_vec(ones.astype(float), sizes.astype(float))
        ge += int((J >= obs - 1e-9).sum())
        done += m
    return {"J": obs, "E_J": norm.get("E_J"), "z": norm.get("z"), "p_perm": (ge + 1) / (n_perm + 1),
            "p_normal": norm.get("p"), "n_perm": n_perm, "seed": seed, "sizes": sizes.tolist(), "degenerate": False,
            "direction": "decreasing"}


def clopper_pearson(k: int, n: int, alpha: float = 0.05) -> dict[str, Any]:
    if n <= 0:
        return {"upper_one_sided95": None, "two_sided95": [None, None]}
    up1 = 1.0 if k == n else float(sps.beta.ppf(1 - alpha, k + 1, n - k))
    lo2 = 0.0 if k == 0 else float(sps.beta.ppf(alpha / 2, k, n - k + 1))
    up2 = 1.0 if k == n else float(sps.beta.ppf(1 - alpha / 2, k + 1, n - k))
    return {"upper_one_sided95": up1, "two_sided95": [lo2, up2]}


def holm(pvals: dict[str, float | None]) -> dict[str, float | None]:
    items = sorted([(p, k) for k, p in pvals.items() if p is not None])
    m = len(items)
    out: dict[str, float | None] = {k: None for k in pvals}
    run = 0.0
    for i, (p, k) in enumerate(items):
        adj = min(1.0, (m - i) * p)
        run = max(run, adj)
        out[k] = run
    return out


def fisher_rxc_or_2x2(table: list[list[int]]) -> float | None:
    """Fisher exact p for a 2 x c table of (compliant, not) by template: exact for 2 x 2, otherwise a 20,000-draw
    Monte-Carlo permutation of the chi-square statistic (descriptive)."""
    t = np.asarray(table, float)
    if t.shape[0] < 2 or (t.sum(axis=1) == 0).any() or t.sum() == 0:
        return None
    if t.shape == (2, 2):
        return float(sps.fisher_exact(t.astype(int))[1])
    cols = t.sum(axis=0)
    if (cols == 0).any():
        t = t[:, cols > 0]
    rows = t.sum(axis=1)

    def chi(tt):
        e = np.outer(tt.sum(axis=1), tt.sum(axis=0)) / tt.sum()
        with np.errstate(divide="ignore", invalid="ignore"):
            return float(np.nansum((tt - e) ** 2 / np.where(e > 0, e, np.nan)))
    obs = chi(t)
    labels = np.repeat(np.arange(t.shape[0]), rows.astype(int))
    outcome = np.concatenate([np.repeat(np.arange(t.shape[1]), t[r].astype(int)) for r in range(t.shape[0])])
    rng = np.random.default_rng(7)
    ge = 0
    for _ in range(20_000):
        perm = rng.permutation(outcome)
        tt = np.zeros_like(t)
        np.add.at(tt, (labels, perm), 1)
        ge += chi(tt) >= obs - 1e-9
    return (ge + 1) / 20_001


def unit_test_u7() -> dict[str, Any]:
    from statsmodels.stats.proportion import confint_proportions_2indep, proportion_confint
    out: dict[str, Any] = {}
    w = []
    for k, n in [(0, 10), (3, 10), (15, 148), (50, 50), (37, 50)]:
        lo, hi = wilson(k, n)
        slo, shi = proportion_confint(k, n, method="wilson")
        w.append({"k": k, "n": n, "ours": [lo, hi], "statsmodels": [float(slo), float(shi)],
                  "ok": abs(lo - slo) < 1e-9 and abs(hi - shi) < 1e-9})
    out["wilson"] = w
    nu = []
    for k1, n1, k2, n2 in [(56, 70, 48, 80), (40, 50, 20, 50), (5, 50, 0, 50), (49, 50, 30, 50)]:
        d, lo, hi = newcombe_unpaired(k1, n1, k2, n2)
        slo, shi = confint_proportions_2indep(k1, n1, k2, n2, method="newcomb", compare="diff")
        nu.append({"cells": [k1, n1, k2, n2], "ours": [lo, hi], "statsmodels": [float(slo), float(shi)],
                   "ok": abs(lo - slo) < 1e-6 and abs(hi - shi) < 1e-6})
    out["newcombe_unpaired"] = nu
    # paired Newcombe vs published Table III of Newcombe (1998b), method 10
    table3 = [(36, 12, 2, 0, 0.0569, 0.3404), (20, 12, 2, 16, 0.0562, 0.3292), (18, 12, 2, 18, 0.0562, 0.3290),
              (36, 14, 0, 0, 0.1528, 0.4167), (35, 14, 0, 1, 0.1461, 0.4175), (18, 14, 0, 18, 0.1441, 0.3963)]
    t3 = []
    for e, f, g, h, lo_p, hi_p in table3:
        _, lo3, hi3 = newcombe_paired(e, f, g, h)
        t3.append({"cells": [e, f, g, h], "ours": [round(lo3, 4), round(hi3, 4)], "paper": [lo_p, hi_p],
                   "ok": abs(lo3 - lo_p) < 2e-4 and abs(hi3 - hi_p) < 2e-4})
    out["newcombe_paired_table3"] = t3
    # paired Newcombe vs 20,000-resample paired bootstrap on three synthetic tables
    bs = []
    # tables scaled to n = 200 so the bootstrap's 1/n quantile lattice (0.02 at n = 50) does not dominate the check
    for a, b, c, d in [(120, 60, 8, 12), (80, 80, 20, 20), (40, 100, 40, 20)]:
        x1 = [1] * a + [1] * b + [0] * c + [0] * d
        x2 = [1] * a + [0] * b + [1] * c + [0] * d
        g, lo, hi = newcombe_paired(a, b, c, d)
        _, blo, bhi = paired_bootstrap_gap(x1, x2, B=20_000, seed=1)
        bs.append({"cells": [a, b, c, d], "newcombe": [lo, hi], "bootstrap": [blo, bhi],
                   "ok": abs(lo - blo) <= 0.02 + 1e-9 and abs(hi - bhi) <= 0.02 + 1e-9})
    out["paired_vs_bootstrap"] = bs
    # JT: exact enumeration on a tiny set and normal approximation on a large synthetic set
    import itertools
    groups = [[1, 1, 0], [1, 0, 0], [0, 0, 0]]
    y = sum(groups, [])
    obs = jt_statistic(groups)
    vals = [jt_statistic([list(p[0:3]), list(p[3:6]), list(p[6:9])]) for p in itertools.permutations(y)]
    exact = sum(1 for v in vals if v >= obs - 1e-9) / len(vals)
    mc = jt_test(groups, n_perm=200_000, seed=1)["p_perm"]
    out["jt_tiny"] = {"exact": exact, "perm": mc, "ok": abs(exact - mc) < 0.01}
    rng = np.random.default_rng(3)
    g5 = [list((rng.random(200) < p).astype(int)) for p in (0.62, 0.6, 0.58, 0.56, 0.54)]
    r5 = jt_test(g5, n_perm=20_000)
    out["jt_large"] = {"p_perm": r5["p_perm"], "p_normal": r5["p_normal"],
                       "ok": abs(r5["p_perm"] - r5["p_normal"]) < 0.02}
    out["passed"] = bool(all(x["ok"] for x in w) and all(x["ok"] for x in nu) and all(x["ok"] for x in t3) and
                         all(x["ok"] for x in bs) and out["jt_tiny"]["ok"] and out["jt_large"]["ok"])
    return out
