#!/usr/bin/env python3
"""Statistics for the iteration-9 analyses (committed in commit #1b): Wilson, Newcombe unpaired (method 10, hybrid
score) and paired (method 10 for paired proportions, Newcombe 1998b), exact McNemar, Jonckheere-Terpstra with a
Monte-Carlo exact p, Cochran-Armitage, configuration-cluster bootstrap, binomial tails."""

from __future__ import annotations

import math
from typing import Any, Sequence

import numpy as np

from common import newcombe_diff, wilson_ci

Z95 = 1.959963984540054


def newcombe_paired(a: int, b: int, c: int, d: int, z: float = Z95) -> tuple[float, float, float]:
    """95% CI for p1 - p2 from paired binary data: a = both 1, b = x1 & not x2, c = not x1 & x2, d = both 0.
    Newcombe (1998b) method 10: Wilson score limits of the two marginals combined with a continuity-corrected
    phi correlation."""
    n = a + b + c + d
    if n == 0:
        return (float("nan"), float("nan"), float("nan"))
    p1, p2 = (a + b) / n, (a + c) / n
    l1, u1 = wilson_ci(a + b, n, z)
    l2, u2 = wilson_ci(a + c, n, z)
    D = p1 - p2
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
    return (D, max(-1.0, D - dl), min(1.0, D + du))


def binom_cdf(k: int, n: int, p: float = 0.5) -> float:
    return float(sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(0, k + 1)))


def binom_sf(k: int, n: int, p: float) -> float:
    """P(X >= k)."""
    return float(sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k, n + 1)))


def mcnemar_exact(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    return min(1.0, 2.0 * binom_cdf(min(b, c), n, 0.5))


def jt_statistic_binary(groups: Sequence[Sequence[int]]) -> float:
    """Jonckheere-Terpstra J for ordered groups of 0/1 outcomes: sum over i < j of #(x_i < x_j) + 0.5 #(ties)."""
    J = 0.0
    zs = [sum(1 for v in g if v == 0) for g in groups]
    os_ = [sum(1 for v in g if v == 1) for g in groups]
    for i in range(len(groups)):
        for j in range(i + 1, len(groups)):
            J += zs[i] * os_[j] + 0.5 * (zs[i] * zs[j] + os_[i] * os_[j])
    return J


def jt_test_decreasing(groups: Sequence[Sequence[int]], n_perm: int = 100_000, seed: int = 0) -> dict[str, Any]:
    """One-sided JT (outcome decreasing along the group order) with a Monte-Carlo exact p from n_perm permutations
    of the pooled outcomes over the fixed group sizes (ties handled by the 0.5 rule); the normal approximation (no
    tie correction) is reported beside it."""
    sizes = [len(g) for g in groups]
    y = np.concatenate([np.asarray(g, dtype=np.int8) for g in groups]) if groups else np.zeros(0, np.int8)
    N = len(y)
    obs = jt_statistic_binary(groups)
    if N == 0 or y.min() == y.max():
        return {"J": obs, "p_mc": None, "degenerate": True, "sizes": sizes}
    rng = np.random.default_rng(seed)
    bounds = np.cumsum([0] + sizes)
    le = 0
    done = 0
    chunk = 5000
    while done < n_perm:
        m = min(chunk, n_perm - done)
        P = np.tile(y, (m, 1))
        P = rng.permuted(P, axis=1)
        ones = np.stack([P[:, bounds[g]:bounds[g + 1]].sum(axis=1) for g in range(len(sizes))], axis=1)
        zeros = np.array(sizes)[None, :] - ones
        J = np.zeros(m)
        for i in range(len(sizes)):
            for j in range(i + 1, len(sizes)):
                J += zeros[:, i] * ones[:, j] + 0.5 * (zeros[:, i] * zeros[:, j] + ones[:, i] * ones[:, j])
        le += int((J <= obs + 1e-9).sum())
        done += m
    # normal approximation
    mean = (N * N - sum(s * s for s in sizes)) / 4.0
    var = (N * N * (2 * N + 3) - sum(s * s * (2 * s + 3) for s in sizes)) / 72.0
    zval = (obs - mean) / math.sqrt(var) if var > 0 else float("nan")
    p_norm = 0.5 * math.erfc(-zval / math.sqrt(2)) if np.isfinite(zval) else None
    return {"J": obs, "E_J": mean, "z": zval, "p_mc": (le + 1) / (n_perm + 1), "p_normal": p_norm,
            "n_perm": n_perm, "sizes": sizes, "degenerate": False, "direction": "decreasing"}


def cochran_armitage_decreasing(groups: Sequence[Sequence[int]], scores: Sequence[float] | None = None) -> dict[str, Any]:
    n = [len(g) for g in groups]
    s = [sum(g) for g in groups]
    t = list(scores) if scores is not None else list(range(1, len(groups) + 1))
    N, S = sum(n), sum(s)
    if N == 0 or S in (0, N):
        return {"z": None, "p_one_sided": None, "degenerate": True}
    pbar = S / N
    T = sum(ti * (si - ni * pbar) for ti, si, ni in zip(t, s, n))
    var = pbar * (1 - pbar) * (sum(ti * ti * ni for ti, ni in zip(t, n)) - sum(ti * ni for ti, ni in zip(t, n)) ** 2 / N)
    z = T / math.sqrt(var) if var > 0 else float("nan")
    # decreasing trend: one-sided p = P(Z <= z) = Phi(z)
    return {"z": z, "p_one_sided": 0.5 * math.erfc(-z / math.sqrt(2)) if np.isfinite(z) else None,
            "degenerate": False}


def cluster_bootstrap_mean(vals: Sequence[float], B: int = 10_000, seed: int = 0) -> tuple[float, float, float]:
    v = np.asarray([x for x in vals if x is not None and np.isfinite(x)], float)
    if len(v) == 0:
        return (float("nan"), float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(v), size=(B, len(v)))
    means = v[idx].mean(axis=1)
    return (float(v.mean()), float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975)))


def rate(k: int, n: int) -> dict[str, Any]:
    lo, hi = wilson_ci(k, n) if n else (None, None)
    return {"k": k, "n": n, "rate": (k / n) if n else None, "wilson95": [lo, hi]}


def unpaired_diff(k1: int, n1: int, k2: int, n2: int) -> dict[str, Any]:
    d, lo, hi = newcombe_diff(k1, n1, k2, n2)
    return {"diff": d, "newcombe95": [lo, hi]}


def self_test() -> dict[str, Any]:
    """Textbook / brute-force checks (testing plan 3)."""
    out: dict[str, Any] = {}
    # Wilson: 15/148 -> (0.0624, 0.1605) (Newcombe 1998a, Table I example b)
    lo, hi = wilson_ci(15, 148)
    out["wilson_15_148"] = [round(lo, 4), round(hi, 4)]
    out["wilson_ok"] = abs(lo - 0.0624) < 6e-4 and abs(hi - 0.1605) < 6e-4
    # Newcombe unpaired method 10: 56/70 - 48/80 -> (0.0524, 0.3339) (Newcombe 1998a, example a)
    d, l2, h2 = newcombe_diff(56, 70, 48, 80)
    out["newcombe10_56_70_48_80"] = [round(l2, 4), round(h2, 4)]
    out["newcombe_unpaired_ok"] = abs(l2 - 0.0524) < 6e-4 and abs(h2 - 0.3339) < 6e-4
    # Newcombe paired method 10 against the published worked examples: Newcombe (1998b) Statistics in Medicine
    # 17:2635-2650, Table III (method 10 rows), cells (e, f, g, h) = (both, x only, y only, neither)
    table3 = [(36, 12, 2, 0, 0.0569, 0.3404), (20, 12, 2, 16, 0.0562, 0.3292), (18, 12, 2, 18, 0.0562, 0.3290),
              (36, 14, 0, 0, 0.1528, 0.4167), (35, 14, 0, 1, 0.1461, 0.4175), (18, 14, 0, 18, 0.1441, 0.3963),
              (2, 97, 1, 0, 0.8721, 0.9854), (1, 97, 1, 1, 0.8736, 0.9850)]
    rows3 = []
    for e, f, g, h, lo_p, hi_p in table3:
        _, lo3, hi3 = newcombe_paired(e, f, g, h)
        rows3.append({"cells": [e, f, g, h], "ours": [round(lo3, 4), round(hi3, 4)], "paper": [lo_p, hi_p],
                      "ok": abs(lo3 - lo_p) < 2e-4 and abs(hi3 - hi_p) < 2e-4})
    out["newcombe_paired_table3"] = rows3
    out["newcombe_paired_ok"] = all(r["ok"] for r in rows3)
    # JT vs brute-force exact enumeration on a tiny table
    import itertools

    groups = [[1, 1, 0], [1, 0, 0], [0, 0, 0]]
    y = sum(groups, [])
    obs = jt_statistic_binary(groups)
    vals = []
    for perm in set(itertools.permutations(y)):
        g = [list(perm[0:3]), list(perm[3:6]), list(perm[6:9])]
        vals.append(jt_statistic_binary(g))
    # each distinct arrangement of the multiset is equally likely under the permutation null
    exact = sum(1 for v in vals if v <= obs + 1e-9) / len(vals)
    mc = jt_test_decreasing(groups, n_perm=200_000, seed=1)["p_mc"]
    out["jt_tiny_exact"] = exact
    out["jt_tiny_mc"] = mc
    out["jt_ok"] = abs(exact - mc) < 0.01
    # JT vs normal approximation on a synthetic 5 x 50 table with a planted decline
    rng = np.random.default_rng(3)
    g5 = [list((rng.random(50) < p).astype(int)) for p in (0.8, 0.7, 0.6, 0.5, 0.4)]
    r5 = jt_test_decreasing(g5, n_perm=20_000)
    out["jt_5x50"] = {"p_mc": r5["p_mc"], "p_normal": r5["p_normal"]}
    out["jt_normal_agree"] = abs(r5["p_mc"] - r5["p_normal"]) < 0.02 or (r5["p_mc"] < 0.01 and r5["p_normal"] < 0.01)
    ca = cochran_armitage_decreasing(g5)
    out["ca_5x50"] = ca
    # McNemar exact: b=1, c=7 -> p = 0.0703
    out["mcnemar_1_7"] = round(mcnemar_exact(1, 7), 4)
    out["mcnemar_ok"] = abs(out["mcnemar_1_7"] - 0.0703) < 1e-3
    # planted-effect simulation for the paired gap: gap 0.5 detected; no gap ~5% rejections
    rej_eff = rej_null = 0
    for s in range(200):
        r = np.random.default_rng(100 + s)
        lex = r.random(50) < 0.9
        mech = r.random(50) < 0.4
        a = int((lex & mech).sum()); b = int((lex & ~mech).sum()); c = int((~lex & mech).sum()); d = int((~lex & ~mech).sum())
        rej_eff += int(newcombe_paired(a, b, c, d)[1] > 0)
        lex2 = r.random(50) < 0.6
        mech2 = r.random(50) < 0.6
        a = int((lex2 & mech2).sum()); b = int((lex2 & ~mech2).sum()); c = int((~lex2 & mech2).sum()); d = int((~lex2 & ~mech2).sum())
        lo_, hi_ = newcombe_paired(a, b, c, d)[1:]
        rej_null += int(lo_ > 0 or hi_ < 0)
    out["planted_gap_power"] = rej_eff / 200
    out["null_rejection_rate"] = rej_null / 200
    out["all_ok"] = bool(out["wilson_ok"] and out["newcombe_unpaired_ok"] and out["newcombe_paired_ok"]
                         and out["jt_ok"] and out["mcnemar_ok"]
                         and out["planted_gap_power"] > 0.9 and out["null_rejection_rate"] < 0.1)
    return out
