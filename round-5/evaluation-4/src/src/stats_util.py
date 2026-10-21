"""Statistics shared by eval.py, rivals/compute_rivals.py and rivals/score_rivals.py (NOT by audit/rederive.py,
which re-implements everything with the standard library only).

Conventions (plan PART 0.5-0.6): numpy default_rng(20261021); bootstrap 10,000 replicates (percentile intervals);
permutation tests 200,000 Monte Carlo draws with the Monte Carlo SE; exact enumeration where feasible.
"""

from __future__ import annotations

import itertools
import math
from collections import Counter
from typing import Any, Iterable, Sequence

import numpy as np
from scipy import stats

SEED = 20261021
N_BOOT = 10_000
N_PERM = 200_000
NOT_ALT = ("other", "invalid", "disputed", "unknown", "unlabelled", None, "None", "")


# ------------------------------------------------------------------------------------------------ diversity
def hill1_raw(counts: dict[str, int]) -> float | None:
    c = np.array([v for v in counts.values() if v > 0], float)
    if c.sum() <= 0:
        return None
    p = c / c.sum()
    return float(np.exp(-(p * np.log(p)).sum()))


def _compositions(caps: list[int], total: int):
    """All vectors k with 0 <= k_i <= caps_i and sum k = total."""
    if len(caps) == 1:
        if total <= caps[0]:
            yield (total,)
        return
    rest = sum(caps[1:])
    for k in range(max(0, total - rest), min(caps[0], total) + 1):
        for tail in _compositions(caps[1:], total - k):
            yield (k,) + tail


def hill1_rarefied(counts: dict[str, int], depth: int = 25) -> dict[str, Any]:
    """Exact expected Hill-1 (exp Shannon) of a subsample of size `depth` drawn WITHOUT replacement (multivariate
    hypergeometric enumeration; the run's Monte-Carlo estimator has the same expectation).  Depth falls back to the
    number of programs when fewer are available (flagged)."""
    cs = [int(v) for v in counts.values() if v > 0]
    n = sum(cs)
    if n == 0:
        return {"hill": None, "depth": 0, "flag": "no programs"}
    d = min(depth, n)
    flag = None if d == depth else f"own depth {d}"
    if len(cs) == 1:
        return {"hill": 1.0, "depth": d, "flag": flag}
    log_denom = math.lgamma(n + 1) - math.lgamma(d + 1) - math.lgamma(n - d + 1)
    lg = [[math.lgamma(c + 1) - math.lgamma(k + 1) - math.lgamma(c - k + 1) for k in range(c + 1)] for c in cs]
    tot = 0.0
    for comp in _compositions(cs, d):
        lp = sum(lg[i][k] for i, k in enumerate(comp)) - log_denom
        h = -sum((k / d) * math.log(k / d) for k in comp if k > 0)
        tot += math.exp(lp) * math.exp(h)
    return {"hill": float(tot), "depth": d, "flag": flag}


# ------------------------------------------------------------------------------------------------ correlation
def ranks(x: Sequence[float]) -> np.ndarray:
    return stats.rankdata(np.asarray(x, float), method="average")


def spearman(x: Sequence[float], y: Sequence[float]) -> float | None:
    x, y = np.asarray(x, float), np.asarray(y, float)
    if len(x) < 3 or np.std(x) == 0 or np.std(y) == 0:
        return None
    return float(np.corrcoef(ranks(x), ranks(y))[0, 1])


def perm_spearman(x: Sequence[float], y: Sequence[float], n_perm: int = N_PERM, seed: int = SEED,
                  chunk: int = 20_000) -> dict[str, Any]:
    x, y = np.asarray(x, float), np.asarray(y, float)
    rho = spearman(x, y)
    if rho is None:
        return {"rho": None, "p_two_sided": None, "p_one_sided_ge": None, "mc_se_two_sided": None, "n": len(x),
                "n_perm": n_perm, "note": "constant input or n < 3"}
    rx, ry = ranks(x), ranks(y)
    rx = (rx - rx.mean()) / rx.std()
    ry = (ry - ry.mean()) / ry.std()
    rng = np.random.default_rng(seed)
    ge_abs = ge = 0
    done = 0
    while done < n_perm:
        m = min(chunk, n_perm - done)
        perm = np.argsort(rng.random((m, len(x))), axis=1)
        rp = (rx[None, :] * ry[perm]).mean(1)
        ge_abs += int(np.sum(np.abs(rp) >= abs(rho) - 1e-12))
        ge += int(np.sum(rp >= rho - 1e-12))
        done += m
    p2 = (ge_abs + 1) / (n_perm + 1)
    p1 = (ge + 1) / (n_perm + 1)
    return {"rho": rho, "p_two_sided": p2, "p_one_sided_ge": p1, "mc_se_two_sided": math.sqrt(p2 * (1 - p2) / n_perm),
            "n": len(x), "n_perm": n_perm}


def kendall_b(x: Sequence[float], y: Sequence[float]) -> float | None:
    if len(set(x)) < 2 or len(set(y)) < 2:
        return None
    return float(stats.kendalltau(x, y, variant="b").statistic)


def boot_spearman(x: Sequence[float], y: Sequence[float], n_boot: int = N_BOOT, seed: int = SEED) -> dict[str, Any]:
    x, y = np.asarray(x, float), np.asarray(y, float)
    rng = np.random.default_rng(seed + 7)
    vals = []
    for _ in range(n_boot):
        idx = rng.integers(0, len(x), len(x))
        r = spearman(x[idx], y[idx])
        if r is not None:
            vals.append(r)
    if not vals:
        return {"ci95": None, "n_valid": 0}
    return {"ci95": [float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975))], "n_valid": len(vals)}


def partial_spearman(x: Sequence[float], y: Sequence[float], z: np.ndarray | Sequence[float]) -> float | None:
    """Spearman correlation of x and y after removing (linear in ranks) one or more covariates z."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    z = np.asarray(z, float)
    if z.ndim == 1:
        z = z[:, None]
    if len(x) < 4 or np.std(x) == 0 or np.std(y) == 0:
        return None
    rz = np.column_stack([ranks(z[:, j]) for j in range(z.shape[1]) if np.std(z[:, j]) > 0] or [np.zeros(len(x))])
    X = np.column_stack([np.ones(len(x)), rz])
    rx, ry = ranks(x), ranks(y)
    ex = rx - X @ np.linalg.lstsq(X, rx, rcond=None)[0]
    ey = ry - X @ np.linalg.lstsq(X, ry, rcond=None)[0]
    if np.std(ex) < 1e-12 or np.std(ey) < 1e-12:
        return None
    return float(np.corrcoef(ex, ey)[0, 1])


def auc_exact(scores: Sequence[float], labels: Sequence[int]) -> dict[str, Any]:
    """AUC = P(score_pos > score_neg) + 0.5 P(tie); exact two-sided rank-sum p by enumerating every assignment of
    the observed number of positives to the units (C(15,5) = 3,003 splits for the full panel)."""
    s = np.asarray(scores, float)
    lab = np.asarray(labels, int)
    npos, n = int(lab.sum()), len(lab)
    if npos == 0 or npos == n:
        return {"auc": None, "p_exact_two_sided": None, "n_splits": 0}

    def auc_of(pos_idx: tuple[int, ...]) -> float:
        m = np.zeros(n, bool)
        m[list(pos_idx)] = True
        a, b = s[m], s[~m]
        gt = (a[:, None] > b[None, :]).sum()
        eq = (a[:, None] == b[None, :]).sum()
        return float((gt + 0.5 * eq) / (len(a) * len(b)))

    obs = auc_of(tuple(np.flatnonzero(lab)))
    null = [auc_of(c) for c in itertools.combinations(range(n), npos)]
    dev = abs(obs - 0.5)
    p = float(np.mean([abs(v - 0.5) >= dev - 1e-12 for v in null]))
    return {"auc": obs, "p_exact_two_sided": p, "n_splits": len(null)}


def holm(ps: dict[str, float | None]) -> dict[str, float | None]:
    items = sorted([(k, v) for k, v in ps.items() if v is not None], key=lambda kv: kv[1])
    m = len(items)
    out: dict[str, float | None] = {k: None for k in ps}
    run = 0.0
    for i, (k, p) in enumerate(items):
        run = max(run, min(1.0, (m - i) * p))
        out[k] = run
    return out


# ------------------------------------------------------------------------------------------------ classification
def balanced_accuracy(pred: Sequence[int], obs: Sequence[int]) -> dict[str, Any]:
    pred, obs = np.asarray(pred, int), np.asarray(obs, int)
    pos, neg = obs == 1, obs == 0
    out = {"n_pos": int(pos.sum()), "n_neg": int(neg.sum()), "n_pred_pos": int(pred.sum())}
    if pos.sum() == 0 or neg.sum() == 0:
        out.update(BA=None, TPR=None, TNR=None)
        return out
    tpr = float((pred[pos] == 1).mean())
    tnr = float((pred[neg] == 0).mean())
    out.update(BA=(tpr + tnr) / 2, TPR=tpr, TNR=tnr)
    return out


def fisher(pred: Sequence[int], obs: Sequence[int]) -> dict[str, Any]:
    pred, obs = np.asarray(pred, int), np.asarray(obs, int)
    tab = [[int(((pred == 1) & (obs == 1)).sum()), int(((pred == 1) & (obs == 0)).sum())],
           [int(((pred == 0) & (obs == 1)).sum()), int(((pred == 0) & (obs == 0)).sum())]]
    if pred.min() == pred.max() or obs.min() == obs.max():
        return {"table": tab, "p_two_sided": 1.0, "note": "degenerate margin"}
    return {"table": tab, "p_two_sided": float(stats.fisher_exact(tab, alternative="two-sided").pvalue)}


def boot_ba(pred: Sequence[int], obs: Sequence[int], n_boot: int = N_BOOT, seed: int = SEED) -> dict[str, Any]:
    pred, obs = np.asarray(pred, int), np.asarray(obs, int)
    rng = np.random.default_rng(seed + 11)
    vals = []
    for _ in range(n_boot):
        idx = rng.integers(0, len(pred), len(pred))
        r = balanced_accuracy(pred[idx], obs[idx])["BA"]
        if r is not None:
            vals.append(r)
    if not vals:
        return {"ci95": None, "n_valid": 0}
    return {"ci95": [float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975))], "n_valid": len(vals)}


def mcnemar_exact(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    return float(min(1.0, 2 * stats.binom.cdf(min(b, c), n, 0.5)))


def modal(counter: Counter | dict) -> tuple[str | None, int]:
    if not counter:
        return None, 0
    m = max(counter.values())
    best = sorted(k for k, v in counter.items() if v == m)
    return best[0], m


def quantiles(vals: Iterable[float]) -> dict[str, float | None]:
    v = np.asarray([x for x in vals if x is not None], float)
    if len(v) == 0:
        return {"min": None, "q25": None, "median": None, "q75": None, "max": None, "n": 0}
    return {"min": float(v.min()), "q25": float(np.quantile(v, 0.25)), "median": float(np.median(v)),
            "q75": float(np.quantile(v, 0.75)), "max": float(v.max()), "n": int(len(v))}
