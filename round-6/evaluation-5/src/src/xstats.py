"""Exact small-sample statistics used by eval.py (numpy/scipy). audit/rederive.py re-implements them in stdlib."""

from __future__ import annotations

import math
from itertools import combinations
from typing import Sequence

import numpy as np
from scipy import stats as st


# ----------------------------------------------------------------------------------------- proportions
def clopper_pearson(k: int, n: int, conf: float = 0.95) -> tuple[float, float]:
    if n == 0:
        return (math.nan, math.nan)
    a = 1 - conf
    lo = 0.0 if k == 0 else float(st.beta.ppf(a / 2, k, n - k + 1))
    hi = 1.0 if k == n else float(st.beta.ppf(1 - a / 2, k + 1, n - k))
    return (lo, hi)


def clopper_pearson_lower_one_sided(k: int, n: int, conf: float = 0.95) -> float:
    if k == 0:
        return 0.0
    return float(st.beta.ppf(1 - conf, k, n - k + 1))


def fisher(a: int, b: int, c: int, d: int, alternative: str = "two-sided") -> float:
    """2x2 [[a, b], [c, d]] with rows = groups, columns = (event, no event)."""
    return float(st.fisher_exact([[a, b], [c, d]], alternative=alternative)[1])


def katz_rr(k1: int, n1: int, k2: int, n2: int, conf: float = 0.95) -> dict:
    """Risk ratio (group1 / group2) with the Katz log interval; 0.5 added to every cell if any cell is zero."""
    a, b, c, d = k1, n1 - k1, k2, n2 - k2
    corr = 0.5 if min(a, b, c, d) == 0 else 0.0
    a, b, c, d = a + corr, b + corr, c + corr, d + corr
    rr = (a / (a + b)) / (c / (c + d))
    se = math.sqrt(1 / a - 1 / (a + b) + 1 / c - 1 / (c + d))
    z = float(st.norm.ppf(1 - (1 - conf) / 2))
    return {"rr": rr, "lo": math.exp(math.log(rr) - z * se), "hi": math.exp(math.log(rr) + z * se),
            "continuity_0.5": bool(corr)}


def binom_le_p(k: int, n: int, p: float) -> float:
    """P(X <= k) for X ~ Bin(n, p): exact one-sided test of a count against a rate from below."""
    return float(st.binom.cdf(k, n, p))


def mcnemar_exact(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    return float(min(1.0, 2 * st.binom.cdf(min(b, c), n, 0.5)))


def poisson_binomial_sf(k: int, probs: Sequence[float]) -> float:
    """P(X >= k) for a sum of independent Bernoulli(p_i), by exact convolution."""
    dist = np.array([1.0])
    for p in probs:
        dist = np.convolve(dist, [1 - p, p])
    return float(dist[k:].sum()) if k < len(dist) else 0.0


def holm(pvals: dict[str, float]) -> dict[str, float]:
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m = len(items)
    out, running = {}, 0.0
    for i, (k, p) in enumerate(items):
        running = max(running, min(1.0, (m - i) * p))
        out[k] = running
    return out


# ----------------------------------------------------------------------------------------- rank correlation
def spearman(x: Sequence[float], y: Sequence[float]) -> float:
    r = st.spearmanr(x, y).statistic
    return float(r) if np.isfinite(r) else math.nan


def _rank(a: np.ndarray) -> np.ndarray:
    return st.rankdata(a, axis=-1)


def spearman_perm_p(x: Sequence[float], y: Sequence[float], n_perm: int = 1_000_000, seed: int = 0,
                    alternative: str = "greater") -> dict:
    """Permutation p for Spearman with ties (mid-ranks). Exact enumeration when n! <= 2e6, else Monte Carlo."""
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    n = len(x)
    rx, ry = _rank(x), _rank(y)
    obs = spearman(x, y)
    if math.factorial(n) <= 2_000_000:
        from itertools import permutations
        perms = np.array(list(permutations(range(n))))
        method = "exact enumeration"
    else:
        rng = np.random.default_rng(seed)
        perms = np.argsort(rng.random((n_perm, n)), axis=1)
        method = f"Monte Carlo, {n_perm} permutations"
    ryp = ry[perms]
    rxc = rx - rx.mean()
    rypc = ryp - ryp.mean(axis=1, keepdims=True)
    den = np.sqrt((rxc ** 2).sum() * (rypc ** 2).sum(axis=1))
    rho = np.where(den > 0, (rypc * rxc).sum(axis=1) / np.where(den > 0, den, 1), 0.0)
    eps = 1e-12
    if alternative == "greater":
        p = float((rho >= obs - eps).mean())
    elif alternative == "less":
        p = float((rho <= obs + eps).mean())
    else:
        p = float((np.abs(rho) >= abs(obs) - eps).mean())
    if method.startswith("Monte"):
        p = (p * len(perms) + 1) / (len(perms) + 1)
    return {"rho": obs, "p": p, "method": method, "alternative": alternative}


def fisher_z_ci(r: float, n: int, se_kind: str = "plain", conf: float = 0.95) -> tuple[float, float]:
    z = math.atanh(max(min(r, 0.999999), -0.999999))
    if se_kind == "plain":
        se = 1 / math.sqrt(n - 3)
    elif se_kind == "fieller":
        se = math.sqrt(1.06 / (n - 3))
    elif se_kind == "bonett_wright":
        se = math.sqrt((1 + r * r / 2) / (n - 3))
    else:
        raise ValueError(se_kind)
    q = float(st.norm.ppf(1 - (1 - conf) / 2))
    return (math.tanh(z - q * se), math.tanh(z + q * se))


def bootstrap_spearman(x: Sequence[float], y: Sequence[float], n_boot: int = 10_000, seed: int = 0) -> dict:
    """Unit bootstrap: percentile and BCa intervals; degenerate resamples (constant margin) are dropped."""
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    n = len(x)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(n_boot, n))
    vals = np.array([_spearman_fast(x[i], y[i]) for i in idx])
    ok = np.isfinite(vals)
    v = vals[ok]
    obs = spearman(x, y)
    pct = (float(np.quantile(v, 0.025)), float(np.quantile(v, 0.975)))
    # BCa
    z0 = float(st.norm.ppf(max(min((v < obs).mean() + 0.5 * (v == obs).mean(), 1 - 1e-9), 1e-9)))
    jack = np.array([spearman(np.delete(x, i), np.delete(y, i)) for i in range(n)])
    jack = jack[np.isfinite(jack)]
    jm = jack.mean()
    num = ((jm - jack) ** 3).sum()
    den = 6 * (((jm - jack) ** 2).sum()) ** 1.5
    a = float(num / den) if den > 0 else 0.0
    out = []
    for q in (0.025, 0.975):
        zq = float(st.norm.ppf(q))
        adj = st.norm.cdf(z0 + (z0 + zq) / (1 - a * (z0 + zq)))
        out.append(float(np.quantile(v, min(max(adj, 0.0), 1.0))))
    return {"n_boot": n_boot, "n_valid": int(ok.sum()), "percentile": pct, "bca": tuple(out), "z0": z0, "a": a,
            "samples": vals}


def _spearman_fast(a: np.ndarray, b: np.ndarray) -> float:
    if np.all(a == a[0]) or np.all(b == b[0]):
        return math.nan
    ra, rb = _rank(a), _rank(b)
    ra = ra - ra.mean()
    rb = rb - rb.mean()
    return float((ra * rb).sum() / math.sqrt((ra ** 2).sum() * (rb ** 2).sum()))


def copula_power(x: Sequence[float], y: Sequence[float], rho_s: float, n: int, n_rep: int = 10_000,
                 alpha: float = 0.05, n_perm: int = 2000, seed: int = 0) -> dict:
    """Power of the one-sided permutation Spearman test under a Gaussian copula with empirical margins.

    Pearson r of the latent normals = 2 sin(pi * rho_s / 6); margins through the inverse empirical CDF (keeps ties).
    The permutation null is evaluated with n_perm permutations per replicate (shared permutation matrix)."""
    x = np.sort(np.asarray(x, float))
    y = np.sort(np.asarray(y, float))
    r = 2 * math.sin(math.pi * rho_s / 6)
    rng = np.random.default_rng(seed)
    cov = np.array([[1.0, r], [r, 1.0]])
    z = rng.multivariate_normal([0, 0], cov, size=(n_rep, n))
    u = st.norm.cdf(z)
    # inverse empirical CDF: ceil(u * m) - 1
    xi = np.minimum((u[..., 0] * len(x)).astype(int), len(x) - 1)
    yi = np.minimum((u[..., 1] * len(y)).astype(int), len(y) - 1)
    X, Y = x[xi], y[yi]
    perms = np.argsort(rng.random((n_perm, n)), axis=1)
    rej, rej2, n_def = 0, 0, 0
    for i in range(n_rep):
        a, b = X[i], Y[i]
        if np.all(a == a[0]) or np.all(b == b[0]):
            continue  # constant margin: test undefined, counted as non-rejection
        ra, rb = _rank(a), _rank(b)
        ra = ra - ra.mean()
        rbp = rb[perms]
        rbp = rbp - rbp.mean(axis=1, keepdims=True)
        rb0 = rb - rb.mean()
        dena = (ra ** 2).sum()
        obs = (ra * rb0).sum() / math.sqrt(dena * (rb0 ** 2).sum())
        null = (rbp * ra).sum(axis=1) / np.sqrt(dena * (rbp ** 2).sum(axis=1))
        p = ((null >= obs - 1e-12).sum() + 1) / (n_perm + 1)
        p2 = ((np.abs(null) >= abs(obs) - 1e-12).sum() + 1) / (n_perm + 1)
        n_def += 1
        rej += p <= alpha
        rej2 += p2 <= alpha
    return {"rho_s": rho_s, "pearson_latent": r, "n": n, "n_rep": n_rep, "n_defined": n_def,
            "power": rej / n_rep, "power_two_sided": rej2 / n_rep, "mc_se": math.sqrt(max(rej / n_rep * (1 - rej / n_rep), 1e-12) / n_rep)}


# ----------------------------------------------------------------------------------------- agreement
def cohen_kappa(a: Sequence[str], b: Sequence[str]) -> float:
    a, b = list(a), list(b)
    n = len(a)
    cats = sorted(set(a) | set(b))
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((a.count(c) / n) * (b.count(c) / n) for c in cats)
    if abs(1 - pe) < 1e-12:
        return math.nan
    return (po - pe) / (1 - pe)


def gwet_ac1(a: Sequence[str], b: Sequence[str], categories: Sequence[str] | None = None) -> float:
    a, b = list(a), list(b)
    n = len(a)
    cats = list(categories) if categories else sorted(set(a) | set(b))
    q = len(cats)
    if q < 2:
        return math.nan
    po = sum(x == y for x, y in zip(a, b)) / n
    pi = [(a.count(c) + b.count(c)) / (2 * n) for c in cats]
    pe = sum(p * (1 - p) for p in pi) / (q - 1)
    if abs(1 - pe) < 1e-12:
        return math.nan
    return (po - pe) / (1 - pe)


def fleiss_kappa(ratings: list[list[str]]) -> float:
    """ratings: one list of category labels per item (same number of raters per item)."""
    cats = sorted({c for r in ratings for c in r})
    m = len(ratings[0])
    N = len(ratings)
    if m < 2 or N == 0:
        return math.nan
    P_i, pj = [], {c: 0 for c in cats}
    for r in ratings:
        cnt = {c: r.count(c) for c in cats}
        for c in cats:
            pj[c] += cnt[c]
        P_i.append((sum(v * v for v in cnt.values()) - m) / (m * (m - 1)))
    Pbar = sum(P_i) / N
    pe = sum((v / (N * m)) ** 2 for v in pj.values())
    if abs(1 - pe) < 1e-12:
        return math.nan if abs(1 - Pbar) > 1e-12 else 1.0
    return (Pbar - pe) / (1 - pe)


def kappa_bootstrap(a: Sequence[str], b: Sequence[str], n_boot: int = 5000, seed: int = 0) -> tuple[float, float]:
    a, b = np.asarray(a), np.asarray(b)
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(n_boot):
        i = rng.integers(0, len(a), len(a))
        k = cohen_kappa(a[i].tolist(), b[i].tolist())
        if np.isfinite(k):
            vals.append(k)
    if not vals:
        return (math.nan, math.nan)
    return (float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975)))


def wilcoxon_exact_greater(d: Sequence[float]) -> float:
    d = [x for x in d if x != 0]
    if not d:
        return math.nan
    return float(st.wilcoxon(d, alternative="greater", method="exact").pvalue)


def exact_mcnemar_one_sided(b: int, c: int) -> float:
    """P(X >= b) for X ~ Bin(b + c, 0.5): b = first forecaster right, second wrong."""
    n = b + c
    if n == 0:
        return 1.0
    return float(st.binom.sf(b - 1, n, 0.5))


def all_subsets(n: int, k: int):
    return combinations(range(n), k)
