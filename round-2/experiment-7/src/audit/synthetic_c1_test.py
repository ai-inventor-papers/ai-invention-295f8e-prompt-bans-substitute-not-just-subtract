#!/usr/bin/env python3
"""Testing plan T0-5: the C1 decomposition, df noise correction and AIM null on SYNTHETIC gains with known structure.

Cases: pure ladder (G = lambda u + noise) -> SHARE ~ 0; pure X-specific (G orthogonal to u) -> SHARE ~ 1;
pure noise -> V_u + V_s ~ 0 (df correction unbiased); planted aim correlation detected, shuffled one not
(placebo p-values roughly uniform).
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from c1 import perm_null, row_stats, share_from_rows  # noqa: E402
from config import RESULTS, WS, write_json  # noqa: E402

JS = ["bfs", "dfs", "bibfs", "iddfs", "astar_gbfs", "dijkstra"]


class FakeCA:
    def __init__(self, conds):
        self.js = JS
        self.cidx = {c: i for i, c in enumerate(conds)}


class FakeCtx:
    """Ctx-compatible lookup over synthetic L arrays."""

    def __init__(self, table):
        conds = sorted({k[0] for k in table})
        self.ca = FakeCA(conds)
        self.table = table
        self.ess = None

    def v(self, cond, h="all"):
        return self.table.get((cond, h), np.full(len(JS), np.nan))

    def e(self, cond, h):
        return np.full(len(JS), 50.0)


def simulate(kind: str, rng: np.random.Generator, noise: float = 0.3, lam: float = 1.5):
    u = rng.normal(size=len(JS))
    table = {}
    rows = []
    for B in JS:
        S_idx = [i for i, j in enumerate(JS) if j != B]
        spec = np.zeros(len(JS))
        if kind == "xspecific":
            v = rng.normal(size=len(S_idx))
            uc = u[S_idx] - u[S_idx].mean()
            v = v - v.mean()
            v = v - (v @ uc) / (uc @ uc) * uc  # orthogonal to the ladder within the row
            spec[S_idx] = 1.5 * v
        for w in WS:
            for h, ns in (("h1", "A"), ("h2", "B")):
                base = rng.normal(size=len(JS))
                if kind == "ladder":
                    signal = lam * u
                elif kind == "xspecific":
                    signal = spec
                else:
                    signal = np.zeros(len(JS))
                table[(f"ban|{B}|{w}", h)] = base + signal + noise * rng.normal(size=len(JS))
                table[(f"neutral|{B}|{w}|{ns}", h)] = base
        ctx = FakeCtx(table)
        r = row_stats(ctx, B, u, WS, "neutral")
        rows.append(r)
    return rows


def main() -> None:
    rng = np.random.default_rng(0)
    out = {}
    for kind in ("ladder", "xspecific", "noise"):
        shares, vt = [], []
        for _ in range(200):
            rows = simulate(kind, rng)
            sh = share_from_rows(rows)
            shares.append(sh["SHARE"])
            vt.append(sh["V_tot"])
        out[kind] = {"SHARE_median": float(np.nanmedian(shares)), "SHARE_q05_q95":
                     [float(np.nanquantile(shares, 0.05)), float(np.nanquantile(shares, 0.95))],
                     "V_tot_mean": float(np.mean(vt)), "V_tot_sd": float(np.std(vt))}
    out["checks"] = {"ladder_share_below_0.5": out["ladder"]["SHARE_q05_q95"][1] < 0.5,
                     "xspecific_share_near_1": out["xspecific"]["SHARE_median"] > 0.9,
                     "noise_V_tot_unbiased": abs(out["noise"]["V_tot_mean"]) < 2 * out["noise"]["V_tot_sd"] / np.sqrt(200)
                     + 0.05 * out["noise"]["V_tot_sd"]}
    # AIM: planted vs shuffled
    def aim_case(planted: bool):
        pairs, vals = [], []
        for _ in range(6):
            s1 = rng.normal(size=5)
            pv = (s1 + 0.3 * rng.normal(size=5)) if planted else rng.normal(size=5)
            s2 = s1 + 0.3 * rng.normal(size=5) if planted else rng.normal(size=5)
            pv1 = (s2 + 0.3 * rng.normal(size=5)) if planted else rng.normal(size=5)
            from c1 import _spearman

            vals.append(np.nanmean([_spearman(s1, pv), _spearman(s2, pv1)]))
            pairs.append([(s1, pv), (s2, pv1)])
        null = perm_null(pairs, 4000, int(rng.integers(1e9)))
        aim = float(np.nanmean(vals))
        return aim, float(np.quantile(null, 0.95)), float((np.sum(null >= aim - 1e-12) + 1) / (len(null) + 1))

    a, p95, p = aim_case(True)
    out["aim_planted"] = {"aim": a, "null_p95": p95, "p": p, "detected": a > p95}
    ps = [aim_case(False)[2] for _ in range(200)]
    out["aim_placebo_p"] = {"mean": float(np.mean(ps)), "frac_below_0.05": float(np.mean(np.array(ps) < 0.05)),
                            "quartiles": [float(np.quantile(ps, q)) for q in (0.25, 0.5, 0.75)]}
    out["checks"]["aim_planted_detected"] = out["aim_planted"]["detected"]
    out["checks"]["aim_placebo_roughly_uniform"] = 0.0 <= out["aim_placebo_p"]["frac_below_0.05"] <= 0.12
    out["all_pass"] = all(out["checks"].values())
    write_json(RESULTS / "synthetic_c1_test.json", out)
    print(out["checks"], out["all_pass"])
    print({k: out[k] for k in ("ladder", "xspecific", "noise")})


if __name__ == "__main__":
    main()
