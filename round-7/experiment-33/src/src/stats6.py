#!/usr/bin/env python3
"""Statistics for iteration 6 (numpy/scipy only): Firth bias-reduced logistic regression (Jeffreys-prior penalised
likelihood) with profile-penalised likelihood CIs and a cluster bootstrap; exact McNemar and sign tests;
Clopper-Pearson and Wilson intervals; Holm adjustment; Mantel-Haenszel odds ratio over strata."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from scipy import optimize, stats


# ------------------------------------------------------------------------------------------------ Firth
def _sig(eta: np.ndarray) -> np.ndarray:
    with np.errstate(over="ignore"):
        return 1 / (1 + np.exp(-eta))


def _pll(X: np.ndarray, y: np.ndarray, beta: np.ndarray) -> float:
    eta = X @ beta
    p = _sig(eta)
    p = np.clip(p, 1e-12, 1 - 1e-12)
    W = p * (1 - p)
    sign, logdet = np.linalg.slogdet(X.T @ (X * W[:, None]))
    ll = float(np.sum(y * np.log(p) + (1 - y) * np.log(1 - p)))
    return ll + 0.5 * float(logdet) if sign > 0 else -np.inf


def firth_fit(X: np.ndarray, y: np.ndarray, fixed: dict[int, float] | None = None, max_iter: int = 100,
              tol: float = 1e-8, beta0: np.ndarray | None = None) -> dict[str, Any]:
    """Firth logistic regression; `fixed` holds coefficients at given values (for the profile likelihood)."""
    n, k = X.shape
    fixed = fixed or {}
    free = np.array([j for j in range(k) if j not in fixed], dtype=int)
    beta = np.zeros(k) if beta0 is None else beta0.copy()
    for j, v in fixed.items():
        beta[j] = v
    pll = _pll(X, y, beta)
    converged = False
    for it in range(max_iter):
        eta = X @ beta
        p = np.clip(_sig(eta), 1e-12, 1 - 1e-12)
        W = p * (1 - p)
        info = X.T @ (X * W[:, None])
        try:
            inv = np.linalg.inv(info)
        except np.linalg.LinAlgError:
            inv = np.linalg.pinv(info)
        h = np.einsum("ij,jk,ik->i", X * np.sqrt(W)[:, None], inv, X * np.sqrt(W)[:, None])
        U = X.T @ (y - p + h * (0.5 - p))
        Uf = U[free]
        If = info[np.ix_(free, free)]
        try:
            step = np.linalg.solve(If, Uf)
        except np.linalg.LinAlgError:
            step = np.linalg.lstsq(If, Uf, rcond=None)[0]
        mx = np.abs(step).max() if step.size else 0.0
        if mx > 5:
            step = step * 5 / mx
        lam = 1.0
        while lam > 1e-6:
            nb = beta.copy()
            nb[free] += lam * step
            npll = _pll(X, y, nb)
            if npll >= pll - 1e-10:
                break
            lam /= 2
        beta, old = nb, pll
        pll = npll
        if np.abs(lam * step).max(initial=0.0) < tol or abs(pll - old) < 1e-12:
            converged = True
            break
    eta = X @ beta
    p = np.clip(_sig(eta), 1e-12, 1 - 1e-12)
    info = X.T @ (X * (p * (1 - p))[:, None])
    try:
        cov = np.linalg.inv(info)
    except np.linalg.LinAlgError:
        cov = np.linalg.pinv(info)
    return {"beta": beta, "pll": pll, "converged": converged, "iterations": it + 1, "cov": cov}


def firth_profile_ci(X: np.ndarray, y: np.ndarray, j: int, fit: dict[str, Any], level: float = 0.95,
                     span: float = 30.0) -> tuple[float, float]:
    """Profile-penalised likelihood CI for coefficient j (Heinze & Schemper 2002)."""
    crit = stats.chi2.ppf(level, 1) / 2
    b, pmax = fit["beta"][j], fit["pll"]

    def g(v: float) -> float:
        f = firth_fit(X, y, fixed={j: v}, beta0=fit["beta"])
        return (pmax - f["pll"]) - crit
    se = math.sqrt(max(fit["cov"][j, j], 1e-12))
    out = []
    for direction in (-1, 1):
        step = max(se, 0.1)
        lo, hi = b, b + direction * step
        ok = False
        for _ in range(40):
            if g(hi) > 0:
                ok = True
                break
            lo, hi = hi, hi + direction * step
            step *= 1.6
            if abs(hi - b) > span:
                break
        if not ok:
            out.append(-np.inf if direction < 0 else np.inf)
            continue
        try:
            out.append(float(optimize.brentq(g, min(lo, hi), max(lo, hi), xtol=1e-4)))
        except ValueError:
            out.append(float(hi))
    return out[0], out[1]


def cluster_bootstrap(X: np.ndarray, y: np.ndarray, clusters: np.ndarray, idx: list[int], n_boot: int = 2000,
                      seed: int = 20261022, strata: np.ndarray | None = None) -> dict[str, Any]:
    """Percentile CIs of coefficients idx from resampling clusters (CRN slots) with replacement within strata."""
    rng = np.random.default_rng(seed)
    strata = np.zeros(len(y), dtype=int) if strata is None else strata
    groups = {}
    for s in np.unique(strata):
        cl = np.unique(clusters[strata == s])
        groups[s] = {c: np.where((clusters == c) & (strata == s))[0] for c in cl}
    draws, fails = [], 0
    for _ in range(n_boot):
        rows = []
        for s, g in groups.items():
            keys = list(g)
            pick = rng.integers(0, len(keys), len(keys))
            for i in pick:
                rows.append(g[keys[i]])
        r = np.concatenate(rows)
        Xb, yb = X[r], y[r]
        if np.linalg.matrix_rank(Xb) < X.shape[1]:
            fails += 1
            continue
        f = firth_fit(Xb, yb, max_iter=60)
        if not f["converged"]:
            fails += 1
            continue
        draws.append(f["beta"][idx])
    d = np.array(draws)
    out = {"n_ok": len(draws), "n_failed": fails}
    if len(d):
        out["ci95"] = {int(j): [float(np.percentile(d[:, i], 2.5)), float(np.percentile(d[:, i], 97.5))]
                       for i, j in enumerate(idx)}
    return out


# ------------------------------------------------------------------------------------------------ exact tests
def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar p-value on b and c discordant pairs."""
    n = b + c
    if n == 0:
        return 1.0
    return float(min(1.0, stats.binomtest(min(b, c), n, 0.5, alternative="two-sided").pvalue))


def sign_one_sided(k: int, n: int) -> float:
    return float(stats.binomtest(k, n, 0.5, alternative="greater").pvalue) if n else float("nan")


def clopper_pearson(k: int, n: int, level: float = 0.95) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    a = 1 - level
    lo = stats.beta.ppf(a / 2, k, n - k + 1) if k > 0 else 0.0
    hi = stats.beta.ppf(1 - a / 2, k + 1, n - k) if k < n else 1.0
    return float(lo), float(hi)


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return float(max(0.0, c - h)), float(min(1.0, c + h))


def holm(pvals: dict[str, float]) -> dict[str, float]:
    items = sorted([(k, v) for k, v in pvals.items() if v is not None and not math.isnan(v)], key=lambda x: x[1])
    m = len(items)
    out, run = {}, 0.0
    for i, (k, p) in enumerate(items):
        run = max(run, min(1.0, (m - i) * p))
        out[k] = run
    return out


def mh_or(tables: list[np.ndarray]) -> dict[str, Any]:
    """Mantel-Haenszel common odds ratio over 2x2 strata [[a, b], [c, d]] with the RGB CI (statsmodels)."""
    from statsmodels.stats.contingency_tables import StratifiedTable

    tabs = [t.astype(float) for t in tables if t.sum() > 0 and (t[0].sum() > 0 and t[1].sum() > 0)]
    if not tabs:
        return {"or": None}
    try:
        st = StratifiedTable([t + 0.0 for t in tabs])
        lo, hi = st.oddsratio_pooled_confint()
        return {"or": float(st.oddsratio_pooled), "ci95": [float(lo), float(hi)],
                "p_null_or1": float(st.test_null_odds().pvalue), "n_strata": len(tabs)}
    except (ZeroDivisionError, ValueError, FloatingPointError) as e:
        return {"or": None, "error": str(e)[:120]}


def kl(p: np.ndarray, q: np.ndarray) -> float:
    p, q = np.asarray(p, float), np.asarray(q, float)
    m = p > 0
    return float(np.sum(p[m] * (np.log(p[m]) - np.log(q[m]))))


# ------------------------------------------------------------------------------------------------ CPU tests
def run_tests() -> dict[str, Any]:
    out: dict[str, Any] = {}
    # (1) Firth on a 2x2 table equals the log OR with 0.5 added to every cell (Firth 1993; Heinze-Schemper 2002)
    a, b, c, d = 7, 0, 3, 10  # complete separation in one cell
    y = np.array([1] * a + [0] * b + [1] * c + [0] * d, dtype=float)
    x = np.array([1] * (a + b) + [0] * (c + d), dtype=float)
    X = np.column_stack([np.ones_like(x), x])
    f = firth_fit(X, y)
    ref = math.log((a + .5) * (d + .5) / ((b + .5) * (c + .5)))
    out["firth_2x2_separated"] = {"beta": float(f["beta"][1]), "reference": ref,
                                  "pass": bool(abs(f["beta"][1] - ref) < 1e-4 and f["converged"])}
    lo, hi = firth_profile_ci(X, y, 1, f)
    out["firth_profile_ci_finite"] = {"ci": [lo, hi], "pass": bool(np.isfinite(lo) and np.isfinite(hi) and lo < ref < hi)}
    # (2) Firth ~ MLE on a large non-separated sample
    rng = np.random.default_rng(0)
    xx = rng.standard_normal(4000)
    yy = (rng.random(4000) < 1 / (1 + np.exp(-(0.3 + 0.8 * xx)))).astype(float)
    XX = np.column_stack([np.ones_like(xx), xx])
    fb = firth_fit(XX, yy)["beta"]
    import statsmodels.api as sm
    mb = sm.Logit(yy, XX).fit(disp=0).params
    out["firth_vs_mle_large_n"] = {"firth": fb.tolist(), "mle": [float(v) for v in mb],
                                   "pass": bool(np.abs(fb - mb).max() < 0.01)}
    # (3) exact McNemar and sign test against scipy.stats.binomtest
    out["mcnemar_6_0"] = {"p": mcnemar_exact(6, 0), "pass": abs(mcnemar_exact(6, 0) - 0.03125) < 1e-9}
    out["sign_5_5"] = {"p": sign_one_sided(5, 5), "pass": abs(sign_one_sided(5, 5) - 0.03125) < 1e-9}
    out["cp_3_30_upper"] = {"upper": clopper_pearson(3, 30)[1], "pass": abs(clopper_pearson(3, 30)[1] - 0.2653) < 1e-3}
    # (4) KL against an analytic example: KL(Bern(0.5) || Bern(0.25)) = 0.5 ln 2 + 0.5 ln(2/3)
    v = kl(np.array([.5, .5]), np.array([.25, .75]))
    out["kl_analytic"] = {"kl": v, "pass": abs(v - (0.5 * math.log(2) + 0.5 * math.log(2 / 3))) < 1e-12}
    out["all_pass"] = all(x.get("pass") for x in out.values() if isinstance(x, dict))
    return out


if __name__ == "__main__":
    import json
    print(json.dumps(run_tests(), indent=1))
