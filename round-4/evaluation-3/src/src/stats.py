"""Shared statistics (Section 1 of the plan). Unit-tested in tests/test_stats.py on hand-computed toy cells."""

from __future__ import annotations

import hashlib
import itertools
import math
from collections import Counter
from typing import Iterable, Sequence

import numpy as np
from scipy import stats as sps

MASTER_SEED = 20261021
DEPTH = 25
DEPTH_LOW = 10
N_RAREFY = 1000
N_BOOT = 1000
N_BOOT_RAREFY = 200


def cell_seed(cell_id: str) -> int:
    return int(hashlib.sha256(f"{MASTER_SEED}|{cell_id}".encode()).hexdigest()[:8], 16)


def hill1_counts(x: np.ndarray) -> float:
    x = np.asarray(x, float)
    x = x[x > 0]
    if x.sum() <= 0:
        return float("nan")
    q = x / x.sum()
    return float(math.exp(-(q * np.log(q)).sum()))


def _hill1_rows(draws: np.ndarray, depth: int) -> np.ndarray:
    q = draws / depth
    with np.errstate(divide="ignore", invalid="ignore"):
        h = np.where(q > 0, q * np.log(np.where(q > 0, q, 1.0)), 0.0).sum(axis=1)
    return np.exp(-h)


def rarefied_hill1(counts: Sequence[int], depth: int, n_draws: int, rng: np.random.Generator) -> float:
    c = np.asarray([int(v) for v in counts if int(v) > 0], np.int64)
    if c.sum() < depth or len(c) == 0:
        return float("nan")
    if len(c) == 1:
        return 1.0
    if c.sum() == depth:
        return hill1_counts(c)
    d = rng.multivariate_hypergeometric(c, depth, size=n_draws, method="marginals")
    return float(_hill1_rows(d, depth).mean())


def goods_coverage(counts: Sequence[int]) -> float:
    c = np.asarray([v for v in counts if v > 0])
    n = c.sum()
    if n == 0:
        return float("nan")
    f1 = int((c == 1).sum())
    return float(1 - f1 / n)


def expected_coverage_at(counts: Sequence[int], m: int) -> float:
    """Expected sample coverage of a size-m subsample (interpolation, Chao & Jost 2012 eq. 4a)."""
    c = np.asarray([v for v in counts if v > 0], float)
    n = int(c.sum())
    if m >= n:
        return goods_coverage(c)
    tot = 0.0
    for xi in c:
        if n - xi >= m:
            # C(n - xi, m) / C(n - 1, m)
            tot += (xi / n) * math.exp(math.lgamma(n - xi + 1) - math.lgamma(n - xi - m + 1)
                                       - math.lgamma(n) + math.lgamma(n - m))
    return float(1 - tot)


def coverage_standardised_hill1(counts: Sequence[int], target_cov: float, rng: np.random.Generator,
                                n_draws: int = 400) -> tuple[float, int]:
    """Hill-1 rarefied to the size m whose expected coverage first reaches target_cov (interpolation only)."""
    c = [int(v) for v in counts if v > 0]
    n = sum(c)
    if n == 0 or not np.isfinite(target_cov):
        return float("nan"), 0
    m_star = n
    for m in range(1, n + 1):
        if expected_coverage_at(c, m) >= target_cov - 1e-12:
            m_star = m
            break
    return rarefied_hill1(c, m_star, n_draws, rng), m_star


def h1r_cell(correct_labels: Sequence[str], templates: Sequence[str] | None, cell_id: str, depth: int = DEPTH,
             drop: Iterable[str] = (), n_boot: int = N_BOOT, n_boot_rarefy: int = N_BOOT_RAREFY,
             with_ci: bool = True) -> dict:
    """Correct-only rarefied Hill-1 for one cell; percentile CIs (template-cluster when eligible, and iid)."""
    drop = set(drop)
    keep = [i for i, l in enumerate(correct_labels) if l not in drop]
    labs = [correct_labels[i] for i in keep]
    tpls = [templates[i] for i in keep] if templates is not None else None
    cats = sorted(set(labs))
    idx = {c: i for i, c in enumerate(cats)}
    counts = np.zeros(len(cats), np.int64)
    for l in labs:
        counts[idx[l]] += 1
    n_c = int(counts.sum())
    rng = np.random.default_rng(cell_seed(f"{cell_id}|d{depth}|{'-'.join(sorted(drop))}"))
    out = {"n_c": n_c, "S_obs": int((counts > 0).sum()), "coverage": goods_coverage(counts),
           "value": rarefied_hill1(counts, depth, N_RAREFY, rng), "ci90": [float("nan")] * 2,
           "ci90_iid": [float("nan")] * 2, "ci_unit": None}
    if not with_ci or n_c < depth or len(cats) <= 1:
        if n_c >= depth and len(cats) == 1:
            out["ci90"] = [1.0, 1.0]
            out["ci90_iid"] = [1.0, 1.0]
            out["ci_unit"] = "degenerate"
        return out
    # iid program bootstrap
    probs = counts / n_c
    vals = np.full(n_boot, np.nan)
    for b in range(n_boot):
        cb = rng.multinomial(n_c, probs)
        vals[b] = rarefied_hill1(cb, depth, n_boot_rarefy, rng)
    out["ci90_iid"] = [float(np.nanquantile(vals, 0.05)), float(np.nanquantile(vals, 0.95))]
    out["ci90"] = list(out["ci90_iid"])
    out["ci_unit"] = "program"
    if tpls is not None:
        by_t: dict[str, np.ndarray] = {}
        for l, t in zip(labs, tpls):
            by_t.setdefault(str(t), np.zeros(len(cats), np.int64))[idx[l]] += 1
        tkeys = sorted(by_t)
        if len(tkeys) == 5 and all(by_t[t].sum() >= 5 for t in tkeys):
            mat = np.stack([by_t[t] for t in tkeys])
            tv = np.full(n_boot, np.nan)
            for b in range(n_boot):
                pick = rng.integers(0, len(tkeys), len(tkeys))
                tv[b] = rarefied_hill1(mat[pick].sum(0), depth, n_boot_rarefy, rng)
            if np.isfinite(tv).sum() > 0.5 * n_boot:
                out["ci90"] = [float(np.nanquantile(tv, 0.05)), float(np.nanquantile(tv, 0.95))]
                out["ci_unit"] = "template(5 clusters; few-cluster)"
    return out


def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if n <= 0:
        return float("nan"), float("nan")
    ph = k / n
    den = 1 + z * z / n
    c = (ph + z * z / (2 * n)) / den
    h = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / den
    return max(0.0, c - h), min(1.0, c + h)


def newcombe_diff(k1: int, n1: int, k2: int, n2: int) -> tuple[float, float, float]:
    """p1 - p2 with the Newcombe (1998, method 10) hybrid-score 95% interval."""
    if n1 <= 0 or n2 <= 0:
        return float("nan"), float("nan"), float("nan")
    p1, p2 = k1 / n1, k2 / n2
    l1, u1 = wilson(k1, n1)
    l2, u2 = wilson(k2, n2)
    d = p1 - p2
    return d, d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2), d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)


def poisson_binomial_sf(k: int, probs: Sequence[float]) -> float:
    """P(X >= k) for X = sum of independent Bernoulli(p_i), by dynamic programming."""
    dist = np.zeros(len(probs) + 1)
    dist[0] = 1.0
    for pi in probs:
        dist[1:] = dist[1:] * (1 - pi) + dist[:-1] * pi
        dist[0] *= (1 - pi)
    return float(dist[k:].sum())


def binom_sf(k: int, n: int, p0: float) -> float:
    return float(sps.binom.sf(k - 1, n, p0))


def _rank(a: np.ndarray) -> np.ndarray:
    return sps.rankdata(a)


def spearman_perm(x: Sequence[float], y: Sequence[float], n_perm: int = 1_000_000, seed: int = MASTER_SEED) -> dict:
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    ok = np.isfinite(x) & np.isfinite(y)
    x, y = x[ok], y[ok]
    n = len(x)
    if n < 3 or np.all(x == x[0]) or np.all(y == y[0]):
        return {"rho": float("nan"), "p_perm": float("nan"), "n": n, "method": "undefined"}
    rx, ry = _rank(x), _rank(y)
    rx = (rx - rx.mean()) / np.sqrt(((rx - rx.mean()) ** 2).sum())
    ry = (ry - ry.mean()) / np.sqrt(((ry - ry.mean()) ** 2).sum())
    rho = float((rx * ry).sum())
    if n <= 9:
        perms = np.array(list(itertools.permutations(range(n))))
        null = (rx[None, :] * ry[perms]).sum(1)
        method = f"exact enumeration ({len(perms)} permutations)"
    else:
        rng = np.random.default_rng(seed)
        null = np.empty(n_perm)
        chunk = 100_000
        for s in range(0, n_perm, chunk):
            m = min(chunk, n_perm - s)
            idx = np.argsort(rng.random((m, n)), axis=1)
            null[s:s + m] = (rx[None, :] * ry[idx]).sum(1)
        method = f"Monte Carlo permutation ({n_perm} draws)"
    p = float((np.abs(null) >= abs(rho) - 1e-12).mean())
    tau = sps.kendalltau(x, y)
    return {"rho": rho, "p_perm": p, "n": n, "method": method, "kendall_tau_b": float(tau.statistic),
            "kendall_p": float(tau.pvalue)}


def holm(pvals: Sequence[float]) -> list[float]:
    p = np.asarray(pvals, float)
    out = np.full(len(p), np.nan)
    ok = np.where(np.isfinite(p))[0]
    order = ok[np.argsort(p[ok])]
    m = len(order)
    run = 0.0
    for i, j in enumerate(order):
        run = max(run, min(1.0, (m - i) * p[j]))
        out[j] = run
    return out.tolist()


def jackknife_ci(theta: float, jack_vals: Sequence[float], level: float = 0.95) -> list[float]:
    j = np.asarray(jack_vals, float)
    n = len(j)
    if n < 3:
        return [float("nan"), float("nan")]
    se = math.sqrt((n - 1) / n * ((j - j.mean()) ** 2).sum())
    tq = sps.t.ppf(0.5 + level / 2, n - 1)
    return [theta - tq * se, theta + tq * se]


def cohen_kappa(a: Sequence[str], b: Sequence[str]) -> float:
    a, b = list(a), list(b)
    n = len(a)
    if n == 0:
        return float("nan")
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb.get(k, 0) for k in ca) / (n * n)
    return float((po - pe) / (1 - pe)) if pe < 1 else float("nan")


def kappa_boot_ci(a: Sequence[str], b: Sequence[str], n_boot: int = 2000, seed: int = MASTER_SEED) -> list[float]:
    a, b = list(a), list(b)
    n = len(a)
    if n < 3:
        return [float("nan"), float("nan")]
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(n_boot):
        ix = rng.integers(0, n, n)
        vals.append(cohen_kappa([a[i] for i in ix], [b[i] for i in ix]))
    v = np.asarray(vals, float)
    v = v[np.isfinite(v)]
    return [float(np.quantile(v, 0.025)), float(np.quantile(v, 0.975))] if len(v) else [float("nan")] * 2


def balanced_accuracy(pred: Sequence[int], truth: Sequence[int]) -> float:
    pred, truth = np.asarray(pred), np.asarray(truth)
    pos, neg = truth == 1, truth == 0
    if pos.sum() == 0 or neg.sum() == 0:
        return float("nan")
    return float(0.5 * ((pred[pos] == 1).mean() + (pred[neg] == 0).mean()))


def fisher_2x2(pred: Sequence[int], truth: Sequence[int], alternative: str = "two-sided") -> dict:
    pred, truth = np.asarray(pred), np.asarray(truth)
    tab = [[int(((pred == 1) & (truth == 1)).sum()), int(((pred == 1) & (truth == 0)).sum())],
           [int(((pred == 0) & (truth == 1)).sum()), int(((pred == 0) & (truth == 0)).sum())]]
    res = sps.fisher_exact(tab, alternative=alternative)
    return {"table": tab, "p": float(res.pvalue), "alternative": alternative}


def js_div2(p: np.ndarray, q: np.ndarray) -> float:
    """Base-2 Jensen-Shannon divergence (exp16 convention)."""
    p = np.asarray(p, float) / np.sum(p)
    q = np.asarray(q, float) / np.sum(q)
    m = 0.5 * (p + q)

    def kl(a, b):
        mask = a > 0
        return float((a[mask] * np.log2(a[mask] / b[mask])).sum())

    return 0.5 * kl(p, m) + 0.5 * kl(q, m)


def upper_bound_zero_of_k(k: int, level: float = 0.90) -> float:
    """One-sided upper bound on a per-direction escape probability when 0 of k escape."""
    return float(1 - (1 - level) ** (1 / k)) if k > 0 else float("nan")
