#!/usr/bin/env python3
"""Full-simplex randomisation hull (plan S8.3), built on exp20's CRN HullSampler (src/hull_exp20.py, verbatim).

settings[0] is the reference arm (TWIN). A mixture w on the simplex randomises between the class's settings
(Provost-Fawcett style operating-point mixing); cost(w) = pass_twin - sum_j w_j pass_j; Hill(w) = correct-only
Hill-1 rarefied at depth 25 under the two-stage CRN draw of exp20 (n_j ~ Multinomial(25, pi_j), pi_j proportional to
w_j pass_j, then n_j correct programs of setting j).
Grid (frozen): step 0.01 for k <= 3 settings, 0.02 for k = 4 and 0.05 for k = 5 (deviation: 0.02 at k = 5 is
316,251 points; 0.05 + the local refinement is used), max_nonzero = k (full simplex); then a local refinement at
step 0.0025 within +-0.04 of the best feasible point (k <= 3; k >= 4: step 0.01 within +-0.04 on the best point's
support). H5 = max Hill s.t. cost <= 0.05; P15 / P20 = min cost s.t. Hill >= 1.5 / 2.0 (inf = not reached); the
frontier (cost, best Hill so far) is kept. edge-restricted hull (sensitivity) = max_nonzero 2.
"""

from __future__ import annotations

import itertools
import math
from typing import Any

import numpy as np

from hull_exp20 import HullSampler, simplex_grid

COST_BOUND = 0.05
HILL_TARGETS = (1.5, 2.0)


def grid_step(k: int) -> float:
    return 0.01 if k <= 3 else (0.02 if k == 4 else 0.05)


def local_grid(w0: np.ndarray, step: float, radius: float, support_only: bool) -> np.ndarray:
    k = len(w0)
    idx = [j for j in range(k) if (w0[j] > 0 or not support_only)]
    if len(idx) <= 1:
        return w0[None]
    free = idx[:-1]
    offs = np.arange(-radius, radius + 1e-12, step)
    pts = []
    for d in itertools.product(offs, repeat=len(free)):
        w = w0.copy()
        for j, dj in zip(free, d):
            w[j] += dj
        w[idx[-1]] -= sum(d)
        if (w >= -1e-12).all():
            pts.append(np.clip(w, 0, None) / max(np.clip(w, 0, None).sum(), 1e-12))
    return np.array(pts) if pts else w0[None]


def _prices_on(hs: HullSampler, grid: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    costs = np.array([hs.cost_of(w) for w in grid])
    hills = np.array([hs.hill_of(w) for w in grid])
    return costs, hills


def hull_prices_full(settings: list[dict[str, Any]], n_draws: int = 1000, seed: int = 0, step: float | None = None,
                     max_nonzero: int | None = None, refine: bool = True, keep_frontier: bool = False,
                     refine_step: float | None = None) -> dict[str, Any]:
    k = len(settings)
    if k == 1:
        hs = HullSampler(settings, n_draws=n_draws, seed=seed)
        h = hs.hill_of(np.array([1.0]))
        return {"H5": h, "H5_mixture": [1.0], "P15": 0.0 if h >= 1.5 else math.inf,
                "P20": 0.0 if h >= 2.0 else math.inf, "frontier": [[0.0, h]] if keep_frontier else None}
    hs = HullSampler(settings, n_draws=n_draws, seed=seed)
    st = step or grid_step(k)
    grid = simplex_grid(k, st, max_nonzero=max_nonzero or k)
    costs, hills = _prices_on(hs, grid)
    ok = np.isfinite(hills)
    feas = ok & (costs <= COST_BOUND + 1e-12)
    out: dict[str, Any] = {"grid_step": st, "n_grid": int(len(grid)), "max_nonzero": int(max_nonzero or k)}
    if refine and feas.any():
        w0 = grid[feas][int(np.argmax(hills[feas]))]
        rs = refine_step or (0.0025 if k <= 3 else 0.01)
        lg = local_grid(w0, rs, 0.04, support_only=(k > 3))
        if max_nonzero is not None:
            lg = lg[(lg > 1e-12).sum(1) <= max_nonzero]
        if len(lg):
            c2, h2 = _prices_on(hs, lg)
            grid = np.vstack([grid, lg])
            costs = np.concatenate([costs, c2])
            hills = np.concatenate([hills, h2])
            ok = np.isfinite(hills)
            feas = ok & (costs <= COST_BOUND + 1e-12)
        out["n_refine"] = int(len(lg))
    out["H5"] = float(hills[feas].max()) if feas.any() else float("nan")
    out["H5_mixture"] = grid[feas][int(np.argmax(hills[feas]))].tolist() if feas.any() else None
    for tgt in HILL_TARGETS:
        m = ok & (hills >= tgt)
        out[f"P{int(tgt * 10)}"] = float(costs[m].min()) if m.any() else math.inf
    if keep_frontier:
        order = np.argsort(costs)
        fr, best = [], -1.0
        for i in order:
            if ok[i] and hills[i] > best + 1e-9:
                best = hills[i]
                fr.append([round(float(costs[i]), 4), round(float(hills[i]), 4)])
        out["frontier"] = fr
    out["with_replacement_flags"] = hs.with_replacement
    return out


def unit_tests() -> dict[str, Any]:
    """CPU unit tests (4): full == edge for 2 settings; full >= edge for 3-5; random 3-4 vertex cases within 0.01 of
    a 0.005 brute-force grid (same CRN sampler)."""
    rng = np.random.default_rng(7)
    res: dict[str, Any] = {}

    def rand_settings(k):
        cats = ["a", "b", "c", "d"]
        out = []
        for j in range(k):
            n = int(rng.integers(10, 50))
            p = rng.dirichlet(np.ones(4) * (0.3 if j else 0.1))
            labs = list(rng.choice(cats, size=n, p=p))
            out.append({"correct_labels": labs, "pass": float(rng.uniform(0.5, 1.0)) if j else 0.9})
        return out
    s2 = rand_settings(2)
    a = hull_prices_full(s2, n_draws=300, seed=1)
    b = hull_prices_full(s2, n_draws=300, seed=1, max_nonzero=2)
    res["two_setting_full_eq_edge"] = abs(a["H5"] - b["H5"]) < 1e-9
    ge = []
    for k in (3, 4, 5):
        s = rand_settings(k)
        f = hull_prices_full(s, n_draws=200, seed=2)
        e = hull_prices_full(s, n_draws=200, seed=2, max_nonzero=2, step=grid_step(k))
        ge.append(f["H5"] >= e["H5"] - 1e-9)
    res["full_ge_edge_3_4_5"] = all(ge)
    close = []
    for i in range(50):
        k = 3 if i % 2 == 0 else 4
        s = rand_settings(k)
        f = hull_prices_full(s, n_draws=100, seed=3)
        if k == 3:
            bf = hull_prices_full(s, n_draws=100, seed=3, step=0.005, refine=False)
        else:
            bf = hull_prices_full(s, n_draws=100, seed=3, step=0.02, refine=False)
        close.append(bool(f["H5"] >= bf["H5"] - 0.01))
    res["random_cases_within_0.01_of_fine_grid"] = f"{sum(close)}/50"
    res["pass"] = res["two_setting_full_eq_edge"] and res["full_ge_edge_3_4_5"] and sum(close) >= 48
    return res
