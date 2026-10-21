#!/usr/bin/env python3
"""Randomisation hull of a knob class (plan 6.3), vectorised.

A knob class K has a reference arm 0 and settings S_K. Arm j has r_j = correct counts per idea category / N_j and a
pass rate pass_j. A mixture lambda on the simplex over {0} u S_K has r(lambda) = sum lambda_j r_j, pass(lambda) =
sum lambda_j pass_j, composition q = r / sum(r) and cost = 100 (pass_0 - pass(lambda)) in points (negative costs are
feasible). Hill on the hull = POPULATION-RAREFIED Hill-1 at depth 25: the mean of exp(Shannon) over n_sub
multinomial(25, q) draws made with ONE fixed uniform matrix U[n_sub, 25] (common random numbers across every
evaluation, so the objective is smooth in lambda). Search: every pairwise edge of the simplex on a 0.025 lambda grid,
plus the exact cost = 5 boundary point of each edge, then a golden-section refinement on the best edge.
H5 = max Hill over hull points with cost <= 5. P_thr = the smallest c >= 0 such that the max Hill at cost <= c
reaches thr (computed from the same grid, crossings refined by bisection on the edge), else None ('not reached').
"""

from __future__ import annotations

import itertools
import math
from typing import Any

import numpy as np

GRID = np.round(np.arange(0.0, 1.0 + 1e-9, 0.025), 6)


def fixed_uniforms(n_sub: int, depth: int = 25, seed: int = 20261021) -> np.ndarray:
    return np.random.default_rng(seed).random((n_sub, depth))


def pop_hill(Q: np.ndarray, U: np.ndarray) -> np.ndarray:
    """Q [G, C] compositions (rows sum to 1); U [n_sub, depth] -> [G] mean exp(Shannon) of multinomial(depth, q)."""
    G, C = Q.shape
    if C == 1:
        return np.ones(G)
    cdf = np.cumsum(Q, axis=1)
    cdf[:, -1] = 1.0 + 1e-12
    n_sub, depth = U.shape
    idx = np.empty((G, n_sub, depth), dtype=np.int16)
    flatU = U.ravel()
    for g in range(G):
        idx[g] = np.searchsorted(cdf[g], flatU, side="right").reshape(n_sub, depth)
    np.minimum(idx, C - 1, out=idx)
    H = np.zeros((G, n_sub))
    for c in range(C):
        cnt = (idx == c).sum(axis=2)
        pc = cnt / depth
        with np.errstate(divide="ignore", invalid="ignore"):
            H -= np.where(cnt > 0, pc * np.log(np.where(cnt > 0, pc, 1.0)), 0.0)
    return np.exp(H).mean(axis=1)


class Hull:
    """Vertices: R [m, C] (correct-idea rates), pas [m] (pass rates); vertex 0 is the reference."""

    def __init__(self, R: np.ndarray, pas: np.ndarray, U: np.ndarray, edges: str = "all"):
        self.R = np.asarray(R, float)
        self.pas = np.asarray(pas, float)
        self.U = U
        m = len(self.pas)
        self.m = m
        self.cost_v = 100.0 * (self.pas[0] - self.pas)
        if m == 1:
            self.edges = []
        elif edges == "twin":   # twin-segment-only hull (sensitivity s1)
            self.edges = [(0, j) for j in range(1, m)]
        else:
            self.edges = list(itertools.combinations(range(m), 2))
        self._grid = None

    def eval_lams(self, L: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """L [G, m] mixture weights -> (hill [G], cost [G]); a point with no correct mass has Hill nan."""
        r = L @ self.R
        tot = r.sum(axis=1)
        cost = 100.0 * (self.pas[0] - L @ self.pas)
        hill = np.full(len(L), np.nan)
        ok = tot > 0
        if ok.any():
            Q = r[ok] / tot[ok, None]
            keep = Q.max(axis=0) > 0
            hill[ok] = pop_hill(Q[:, keep] if keep.any() else Q, self.U)
        return hill, cost

    def _edge_points(self, i: int, j: int, lam: np.ndarray) -> np.ndarray:
        L = np.zeros((len(lam), self.m))
        L[:, i] = 1.0 - lam
        L[:, j] += lam
        return L

    def grid(self) -> list[dict[str, Any]]:
        """Evaluate every edge on the 0.025 grid (cached)."""
        if self._grid is not None:
            return self._grid
        out = []
        if not self.edges:
            h, c = self.eval_lams(np.ones((1, 1)))
            out.append({"edge": (0, 0), "lam": np.array([0.0]), "hill": h, "cost": c})
        else:
            Ls = [self._edge_points(i, j, GRID) for i, j in self.edges]
            h, c = self.eval_lams(np.vstack(Ls))
            n = len(GRID)
            for e, (i, j) in enumerate(self.edges):
                out.append({"edge": (i, j), "lam": GRID, "hill": h[e * n:(e + 1) * n], "cost": c[e * n:(e + 1) * n]})
        self._grid = out
        return out

    def best_at_cost(self, c_max: float, refine: bool = True) -> dict[str, Any]:
        """max Hill over hull points with cost <= c_max (grid + exact boundary points + golden refinement)."""
        best = {"hill": -np.inf, "cost": None, "edge": None, "lam": None}
        bnd_L, bnd_meta = [], []
        for g in self.grid():
            feas = g["cost"] <= c_max + 1e-9
            if feas.any():
                hh = np.where(feas & np.isfinite(g["hill"]), g["hill"], -np.inf)
                k = int(np.argmax(hh))
                if hh[k] > best["hill"]:
                    best = {"hill": float(hh[k]), "cost": float(g["cost"][k]), "edge": g["edge"],
                            "lam": float(g["lam"][k])}
            if g["edge"] != (0, 0):
                i, j = g["edge"]
                ci, cj = self.cost_v[i], self.cost_v[j]
                if (ci - c_max) * (cj - c_max) < 0:  # boundary crossing inside the edge
                    lam_b = (c_max - ci) / (cj - ci)
                    bnd_L.append(self._edge_points(i, j, np.array([lam_b]))[0])
                    bnd_meta.append((g["edge"], lam_b))
        if bnd_L:
            hb, cb = self.eval_lams(np.array(bnd_L))
            for (e, lb), h_, c_ in zip(bnd_meta, hb, cb):
                if np.isfinite(h_) and h_ > best["hill"]:
                    best = {"hill": float(h_), "cost": float(c_), "edge": e, "lam": float(lb)}
        if refine and best["edge"] not in (None, (0, 0)):
            best = self._golden(best, c_max)
        if not np.isfinite(best["hill"]):
            best["hill"] = None
        return best

    def _golden(self, best: dict[str, Any], c_max: float, iters: int = 14) -> dict[str, Any]:
        i, j = best["edge"]
        ci, cj = self.cost_v[i], self.cost_v[j]
        lo, hi = max(0.0, best["lam"] - 0.025), min(1.0, best["lam"] + 0.025)
        # restrict to the feasible part of the edge
        if cj != ci:
            lam_b = (c_max - ci) / (cj - ci)
            if cj > ci:
                hi = min(hi, lam_b)
            else:
                lo = max(lo, lam_b)
        elif ci > c_max + 1e-9:
            return best
        if hi <= lo:
            return best
        gr = (math.sqrt(5) - 1) / 2

        def f(x):
            h, c = self.eval_lams(self._edge_points(i, j, np.array([x])))
            return (h[0] if np.isfinite(h[0]) else -np.inf), c[0]

        a, b = lo, hi
        x1, x2 = b - gr * (b - a), a + gr * (b - a)
        f1, f2 = f(x1)[0], f(x2)[0]
        for _ in range(iters):
            if f1 > f2:
                b, x2, f2 = x2, x1, f1
                x1 = b - gr * (b - a)
                f1 = f(x1)[0]
            else:
                a, x1, f1 = x1, x2, f2
                x2 = a + gr * (b - a)
                f2 = f(x2)[0]
        xm = x1 if f1 > f2 else x2
        hm, cm = f(xm)
        if hm > best["hill"] and cm <= c_max + 1e-9:
            return {"hill": float(hm), "cost": float(cm), "edge": (i, j), "lam": float(xm)}
        return best

    def price(self, thr: float, tol: float = 0.1) -> float | None:
        """Smallest c >= 0 with max Hill at cost <= c >= thr (None if never reached on the hull)."""
        cands = []
        for g in self.grid():
            h, c, lam = g["hill"], g["cost"], g["lam"]
            ok = np.isfinite(h) & (h >= thr)
            if not ok.any():
                continue
            k = np.where(ok)[0]
            cands.append(float(np.min(c[k])))
            if g["edge"] == (0, 0):
                continue
            # refine crossings between neighbours where hill crosses thr and the crossing point is cheaper
            for a in range(len(lam) - 1):
                if (ok[a] != ok[a + 1]) and np.isfinite(h[a]) and np.isfinite(h[a + 1]):
                    lo_l, hi_l = (lam[a], lam[a + 1]) if ok[a + 1] else (lam[a + 1], lam[a])
                    i, j = g["edge"]
                    for _ in range(8):  # bisection on lambda: lo_l fails, hi_l passes
                        mid = 0.5 * (lo_l + hi_l)
                        hm, _ = self.eval_lams(self._edge_points(i, j, np.array([mid])))
                        if np.isfinite(hm[0]) and hm[0] >= thr:
                            hi_l = mid
                        else:
                            lo_l = mid
                    _, cc = self.eval_lams(self._edge_points(i, j, np.array([hi_l])))
                    cands.append(float(cc[0]))
        if not cands:
            return None
        return max(0.0, round(min(cands), 1))

    def summary(self, refine: bool = True, with_price: bool = True) -> dict[str, Any]:
        b5 = self.best_at_cost(5.0, refine=refine)
        out = {"H5": b5["hill"], "H5_cost": b5["cost"], "H5_edge": b5["edge"], "H5_lam": b5["lam"]}
        if with_price:
            out["P15"] = self.price(1.5)
            out["P20"] = self.price(2.0)
        return out


def slsqp_check(h: Hull, c_max: float = 5.0, n_starts: int = 6, seed: int = 0) -> float | None:
    """Full-simplex multistart SLSQP over 3-vertex faces; returns the best Hill found (point-estimate check)."""
    from scipy.optimize import minimize

    if h.m < 3:
        return None
    rng = np.random.default_rng(seed)
    best = -np.inf
    for tri in itertools.combinations(range(h.m), 3):
        for _ in range(n_starts):
            x0 = rng.dirichlet(np.ones(3))

            def f(x, tri=tri):
                L = np.zeros((1, h.m))
                L[0, list(tri)] = np.clip(x, 0, None) / max(np.clip(x, 0, None).sum(), 1e-12)
                v, _ = h.eval_lams(L)
                return -(v[0] if np.isfinite(v[0]) else 0.0)

            def con(x, tri=tri):
                L = np.zeros((1, h.m))
                L[0, list(tri)] = np.clip(x, 0, None) / max(np.clip(x, 0, None).sum(), 1e-12)
                return c_max - float(100.0 * (h.pas[0] - L @ h.pas))

            r = minimize(f, x0, method="SLSQP", bounds=[(0, 1)] * 3,
                         constraints=[{"type": "eq", "fun": lambda x: x.sum() - 1}, {"type": "ineq", "fun": con}],
                         options={"maxiter": 60})
            if r.success or True:
                x = np.clip(r.x, 0, None)
                if con(x) >= -1e-6:
                    best = max(best, -f(x))
    return float(best) if np.isfinite(best) else None


def dial_interp_h5(points: list[tuple[float, float]], c_max: float = 5.0) -> float | None:
    """Sensitivity s3: piecewise-linear Hill along the dial (points ordered by setting strength, starting at the
    reference): max interpolated Hill at cost <= c_max."""
    best = None
    pts = [(c, h) for c, h in points if h is not None and np.isfinite(h)]
    for (c0, h0), (c1, h1) in zip(pts[:-1], pts[1:]):
        for c, hv in ((c0, h0), (c1, h1)):
            if c <= c_max and (best is None or hv > best):
                best = hv
        if (c0 - c_max) * (c1 - c_max) < 0:
            t = (c_max - c0) / (c1 - c0)
            hv = h0 + t * (h1 - h0)
            if best is None or hv > best:
                best = hv
    if len(pts) == 1 and pts[0][0] <= c_max:
        best = pts[0][1]
    return best


# ------------------------------------------------------------------------------------------------ unit tests
def unit_tests() -> dict[str, Any]:
    U = fixed_uniforms(1000)
    res = {}
    # (a) twin all default, setting all alternative, equal pass -> max at lambda 0.5, Hill = rarefied (0.5, 0.5)
    h = Hull(np.array([[1.0, 0.0], [0.0, 1.0]]), np.array([1.0, 1.0]), U)
    s = h.summary()
    ref = pop_hill(np.array([[0.5, 0.5]]), U)[0]
    res["a_lam"] = s["H5_lam"]
    res["a_pass"] = abs(s["H5_lam"] - 0.5) < 0.03 and abs(s["H5"] - ref) < 0.01 and abs(s["H5_cost"]) < 1e-9
    # (b) the same with a 10-point pass cost -> optimum on the cost = 5 boundary
    h = Hull(np.array([[1.0, 0.0], [0.0, 0.9]]), np.array([1.0, 0.9]), U)
    s = h.summary()
    res["b_cost"] = s["H5_cost"]
    res["b_pass"] = abs(s["H5_cost"] - 5.0) < 0.05
    # (c) a knob identical to the twin -> H5 = the twin's Hill
    R0 = np.array([0.6, 0.3, 0.1])
    h = Hull(np.vstack([R0, R0]), np.array([1.0, 1.0]), U)
    s = h.summary()
    res["c_pass"] = abs(s["H5"] - pop_hill(R0[None] / R0.sum(), U)[0]) < 1e-9
    # (d) adding a setting never decreases H5
    rng = np.random.default_rng(3)
    ok = True
    for _ in range(20):
        R = rng.dirichlet(np.ones(4), size=3) * rng.uniform(0.6, 1.0, size=(3, 1))
        pas = R.sum(1)
        a = Hull(R[:2], pas[:2], U).summary(with_price=False)["H5"]
        b = Hull(R, pas, U).summary(with_price=False)["H5"]
        ok &= (b is not None and a is not None and b >= a - 1e-9)
    res["d_pass"] = bool(ok)
    # edge search vs full-simplex SLSQP on random 5-vertex cases (point-estimate check)
    gaps = []
    U2 = fixed_uniforms(300)
    for t in range(4):
        R = rng.dirichlet(np.ones(4) * 0.5, size=5) * rng.uniform(0.85, 1.0, size=(5, 1))
        hh = Hull(R, R.sum(1), U2)
        e = hh.summary(with_price=False)["H5"]
        q = slsqp_check(hh, n_starts=2, seed=t)
        gaps.append((q - e) if (q is not None and e is not None) else 0.0)
    res["slsqp_minus_edge_max"] = float(max(gaps))
    res["slsqp_pass"] = res["slsqp_minus_edge_max"] <= 0.02
    res["all_pass"] = all(res[k] for k in ("a_pass", "b_pass", "c_pass", "d_pass", "slsqp_pass"))
    return res


if __name__ == "__main__":
    import json

    print(json.dumps(unit_tests(), indent=1))
