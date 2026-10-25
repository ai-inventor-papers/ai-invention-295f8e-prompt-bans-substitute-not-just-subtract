#!/usr/bin/env python3
"""STEP 11.1-11.3 core (committed in #1): rarefied Hill numbers, the randomisation hull per (task, site), the prices
H5 / P15 / P20, and the frozen C1-site decision rule.

Rarefied Hill-1 at depth m (Chao et al. 2014 convention): mean over subsamples of size m drawn without replacement
from the correct programs of a cell of exp(Shannon entropy of the subsample's label composition).

Randomisation hull (Provost and Fawcett 2001 style randomisation between operating points): settings j in {twin
(alpha 0), alpha 1, alpha 2, alpha 4} of one site; mixture weights w on the simplex (grid 0.05, at most 3 non-zero);
cost(w) = pass_twin - sum_j w_j pass_j; Hill(w) by a two-stage draw: n_j ~ Multinomial(25, pi_j), pi_j proportional to
w_j pass_j, then n_j correct programs of setting j without replacement (with replacement beyond N_correct_j,
flagged); 1,000 draws under common random numbers across w. H5 = max Hill(w) s.t. cost <= 0.05;
P15 / P20 = min cost s.t. Hill(w) >= 1.5 / 2.0, else 'not reached' (inf).
"""

from __future__ import annotations

import itertools
import math
from typing import Any

import numpy as np

DEPTH = 25
GRID_STEP = 0.05
COST_BOUND = 0.05
HILL_TARGETS = (1.5, 2.0)


def hill1(counts: np.ndarray) -> np.ndarray:
    """exp(Shannon entropy) along the last axis of a count array."""
    c = np.asarray(counts, dtype=np.float64)
    n = c.sum(-1, keepdims=True)
    p = np.where(n > 0, c / np.maximum(n, 1e-12), 0.0)
    with np.errstate(divide="ignore", invalid="ignore"):
        h = -np.where(p > 0, p * np.log(p), 0.0).sum(-1)
    return np.exp(h)


def rarefied_hill(labels: list[str], depth: int = DEPTH, n_sub: int = 1000, seed: int = 0) -> dict[str, Any]:
    """Rarefied Hill-1; cells with fewer than `depth` correct programs report Hill at their own depth (flagged)."""
    n = len(labels)
    if n == 0:
        return {"hill": None, "depth": 0, "flag_own_depth": True, "n": 0}
    cats, inv = np.unique(np.array(labels), return_inverse=True)
    counts = np.bincount(inv, minlength=len(cats))
    m = min(depth, n)
    rng = np.random.default_rng(seed)
    sub = rng.multivariate_hypergeometric(counts, m, size=n_sub)
    return {"hill": float(hill1(sub).mean()), "depth": int(m), "flag_own_depth": bool(m < depth), "n": int(n)}


def simplex_grid(k: int, step: float = GRID_STEP, max_nonzero: int = 3) -> np.ndarray:
    m = int(round(1 / step))
    pts = []
    for comb in itertools.product(range(m + 1), repeat=k - 1):
        s = sum(comb)
        if s <= m:
            w = list(comb) + [m - s]
            if sum(1 for x in w if x > 0) <= max_nonzero:
                pts.append(w)
    return np.array(pts, dtype=np.float64) / m


class HullSampler:
    """Pre-draws the CRN randomness for one (task, site): per draw d, 25 uniforms (multinomial allocation by inverse
    CDF on pi(w)) and, per setting j, an ordered sequence of 25 correct programs (a random permutation, then draws with
    replacement beyond N_correct_j). C[j][d, n, :] = label counts among the first n programs of setting j in draw d."""

    def __init__(self, settings: list[dict[str, Any]], n_draws: int = 1000, depth: int = DEPTH, seed: int = 0):
        self.settings = settings
        self.depth = depth
        rng = np.random.default_rng(seed)
        cats = sorted({l for s in settings for l in s["correct_labels"]})
        self.cats = cats
        ci = {c: i for i, c in enumerate(cats)}
        K = max(len(cats), 1)
        self.U = rng.random((n_draws, depth))
        self.C = []
        self.with_replacement = []
        for s in settings:
            labs = np.array([ci[l] for l in s["correct_labels"]], dtype=np.int64)
            C = np.zeros((n_draws, depth + 1, K), dtype=np.int32)
            if len(labs):
                seqs = np.empty((n_draws, depth), dtype=np.int64)
                for d in range(n_draws):
                    if len(labs) >= depth:
                        seqs[d] = rng.permutation(labs)[:depth]
                    else:
                        extra = rng.choice(labs, size=depth - len(labs), replace=True)
                        seqs[d] = np.concatenate([rng.permutation(labs), extra])
                oh = np.zeros((n_draws, depth, K), dtype=np.int32)
                np.put_along_axis(oh, seqs[..., None], 1, axis=2)
                C[:, 1:] = np.cumsum(oh, axis=1)
            self.C.append(C)
            self.with_replacement.append(bool(0 < len(labs) < depth))
        self.pass_ = np.array([s["pass"] for s in settings], dtype=np.float64)
        self.n_correct = np.array([len(s["correct_labels"]) for s in settings])

    def hill_of(self, w: np.ndarray) -> float:
        a = w * self.pass_
        if a.sum() <= 0:
            return float("nan")
        pi = a / a.sum()
        cdf = np.cumsum(pi)
        cdf[-1] = 1.0
        j_of = np.searchsorted(cdf, self.U, side="right").clip(max=len(pi) - 1)  # [D, depth]
        comp = 0
        for j in range(len(pi)):
            nj = (j_of == j).sum(1)
            if pi[j] > 0:
                comp = comp + np.take_along_axis(self.C[j], nj[:, None, None], axis=1)[:, 0]
        return float(hill1(comp).mean())

    def cost_of(self, w: np.ndarray) -> float:
        return float(self.pass_[0] - (w * self.pass_).sum())


def hull_prices(settings: list[dict[str, Any]], n_draws: int = 1000, step: float = GRID_STEP, seed: int = 0,
                keep_frontier: bool = False) -> dict[str, Any]:
    """settings[0] must be the twin (alpha 0). Returns H5, P15, P20, the arg-max mixture and (optionally) the
    frontier (cost, Hill) points."""
    hs = HullSampler(settings, n_draws=n_draws, seed=seed)
    grid = simplex_grid(len(settings), step)
    costs = np.array([hs.cost_of(w) for w in grid])
    hills = np.array([hs.hill_of(w) for w in grid])
    ok = np.isfinite(hills)
    feas = ok & (costs <= COST_BOUND + 1e-12)
    h5 = float(hills[feas].max()) if feas.any() else float("nan")
    arg = grid[feas][int(np.argmax(hills[feas]))].tolist() if feas.any() else None
    out: dict[str, Any] = {"H5": h5, "H5_mixture": arg}
    for tgt in HILL_TARGETS:
        m = ok & (hills >= tgt)
        out[f"P{int(tgt * 10)}"] = float(costs[m].min()) if m.any() else math.inf
    out["with_replacement_flags"] = hs.with_replacement
    if keep_frontier:
        order = np.argsort(costs)
        fr, best = [], -1.0
        for i in order:
            if ok[i] and hills[i] > best:
                best = hills[i]
                fr.append([float(costs[i]), float(hills[i])])
        out["frontier"] = fr
    return out


# ------------------------------------------------------------------------------------------------ C1-site rule
def binom_tail(count: int, n: int = 6, p: float = 1 / 6) -> float:
    return float(sum(math.comb(n, k) * p ** k * (1 - p) ** (n - k) for k in range(count, n + 1)))


def best_site(h5: dict[str, float], p15: dict[str, float]) -> tuple[str | None, bool]:
    """argmax H5 rounded to 0.01; ties broken by lower P15 ('not reached' = inf); a remaining tie -> (None, True)."""
    vals = {s: round(v, 2) for s, v in h5.items() if v is not None and np.isfinite(v)}
    if not vals:
        return None, False
    top = max(vals.values())
    cand = [s for s, v in vals.items() if v == top]
    if len(cand) == 1:
        return cand[0], False
    pmin = min(p15.get(s, math.inf) for s in cand)
    cand2 = [s for s in cand if p15.get(s, math.inf) == pmin]
    if len(cand2) == 1:
        return cand2[0], False
    return None, True


def c1_decision(h5_by_task: dict[str, dict[str, float]], p15_by_task: dict[str, dict[str, float]]) -> dict[str, Any]:
    """Frozen rule: CONFIRMED if S0 is best on >= 4 of 6 tasks (raw p = P(X >= count | Bin(6, 1/6)));
    DISCONFIRMED (generic perturbation) if one other site has H5 >= H5(S0) on >= 4 of 6 tasks; otherwise PARTIAL."""
    best = {t: best_site(h5_by_task[t], p15_by_task[t]) for t in h5_by_task}
    n_t = len(h5_by_task)
    count = sum(1 for t, (b, _) in best.items() if b == "S0")
    others = sorted({s for t in h5_by_task for s in h5_by_task[t] if s != "S0"})
    ge = {s: sum(1 for t in h5_by_task if h5_by_task[t].get(s) is not None and h5_by_task[t].get("S0") is not None
                 and np.isfinite(h5_by_task[t][s]) and round(h5_by_task[t][s], 2) >= round(h5_by_task[t]["S0"], 2))
          for s in others}
    thr = 4 if n_t == 6 else math.ceil(2 * n_t / 3)
    if count >= thr:
        verdict = "CONFIRMED"
    elif any(v >= thr for v in ge.values()):
        verdict = "DISCONFIRMED (generic perturbation)"
    else:
        verdict = "PARTIAL"
    return {"best_site": {t: b for t, (b, _) in best.items()}, "unresolved_tie": {t: tie for t, (_, tie) in
                                                                                  best.items()},
            "count_S0_best": count, "n_tasks": n_t, "threshold": thr, "raw_p_binom": binom_tail(count, n_t, 1 / 6),
            "other_site_ge_S0_counts": ge, "verdict": verdict}
