#!/usr/bin/env python3
"""T4 SYNTHETIC VALIDATION of the G1 pipeline on the REALISED cell table and counts (before COMMIT #1).
Synthetic states: Gaussian noise per program (d = 256) + a planted cell offset a*e_disc + b*e_cont + s*e_cell
(e_disc per discipline, e_cont per container, e_cell per cell = surface term).
 (i)  a = 0, b > 0, 200 datasets: rejection rate of the within-container permutation test for rho_d at 0.05
      (type-I control, target [0.02, 0.08]); the naive full-matrix label permutation is run alongside.
 (ii) a calibrated so that the mean rho_d is about 0.3: power = share of 200 datasets with rho_d >= 0.3 and p < 0.05.
 (iii) bootstrap percentile CI coverage of the planted value (50 runs, B = 100 each).
 (iv) cross-validated vs plain Euclidean centroid distance on pure noise.
Writes results/t4_synthetic.json."""

from __future__ import annotations

import multiprocessing as mp
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np  # noqa: E402

import analysis_g2 as A  # noqa: E402
from common import read_json, utc_now, write_json  # noqa: E402
from tpg2 import DATA, K_PRIMARY, RESULTS  # noqa: E402

DIM = 256


def make(cells, disc, cont, counts, a, b, s, seed):
    rng = np.random.default_rng(seed)
    ed = {d: rng.normal(size=DIM) / np.sqrt(DIM) for d in sorted(set(disc.values()))}
    ec = {c: rng.normal(size=DIM) / np.sqrt(DIM) for c in sorted(set(cont.values()))}
    X, lab = [], []
    for c in cells:
        off = a * ed[disc[c]] + b * ec[cont[c]] + s * rng.normal(size=DIM) / np.sqrt(DIM)
        X.append(off + rng.normal(size=(counts[c], DIM)) / np.sqrt(DIM))
        lab += [c] * counts[c]
    return np.concatenate(X), np.array(lab)


def one(args):
    cells, disc, cont, counts, a, b, s, seed, perms_r, perms_naive = args
    X, lab = make(cells, disc, cont, counts, a, b, s, seed)
    D, _, _ = A.geo_rdm(X, lab, cells, K_PRIMARY)
    Dd, Dc = A.cell_model_rdms(cells, disc, cont)
    y, d, c = A.upper(D), A.upper(Dd), A.upper(Dc)
    rho = A.partial_spearman(y, d, [c])
    pr = A.perm_partial(y, perms_r, [c], len(cells))
    pn = A.perm_partial(y, perms_naive, [c], len(cells))
    return {"rho_d": rho, "p_restricted": A.perm_p(rho, pr)["p_greater"], "p_naive": A.perm_p(rho, pn)["p_greater"]}


def boot_cov(args):
    cells, disc, cont, counts, a, b, s, seed, truth = args
    X, lab = make(cells, disc, cont, counts, a, b, s, seed)
    Dd, Dc = A.cell_model_rdms(cells, disc, cont)
    rng = np.random.default_rng(seed + 7)
    vals = []
    for _ in range(100):
        idx = A.boot_indices(lab, cells, rng)
        D, _, _ = A.geo_rdm(X[idx], lab[idx], cells, K_PRIMARY)
        vals.append(A.partial_spearman(A.upper(D), A.upper(Dd), [A.upper(Dc)]))
    lo, hi = np.nanpercentile(vals, [2.5, 97.5])
    return {"lo": float(lo), "hi": float(hi), "covers": bool(lo <= truth <= hi)}


def main() -> None:
    fr = read_json(DATA / "frames.json")
    g1 = fr["g1_cells"]
    cells = [x["cell"] for x in g1]
    disc = {x["cell"]: x["disc"] for x in g1}
    cont = {x["cell"]: x["cont"] for x in g1}
    counts = {x["cell"]: x["n"] for x in g1}
    perms_r, exact, total = A.restricted_label_perms(cells, cont, disc)
    rng = np.random.default_rng(0)
    base = np.array([sorted(set(disc.values())).index(disc[c]) for c in cells])
    perms_naive = np.stack([base[rng.permutation(len(cells))] for _ in range(5000)]).astype(np.int16)
    out = {"cells": cells, "counts": counts, "restricted_perms": {"exact": exact, "total": total}, "dim": DIM}
    with ProcessPoolExecutor(max_workers=6, mp_context=mp.get_context("spawn")) as ex:
        # (i) type I
        b0 = 1.5
        res = list(ex.map(one, [(cells, disc, cont, counts, 0.0, b0, 0.5, 1000 + i, perms_r, perms_naive)
                                for i in range(200)]))
        rr = np.mean([r["p_restricted"] < 0.05 for r in res])
        rn = np.mean([r["p_naive"] < 0.05 for r in res])
        out["type1"] = {"a": 0.0, "b": b0, "s": 0.5, "n_datasets": 200, "reject_rate_restricted": float(rr),
                        "reject_rate_naive_full_matrix": float(rn), "pass": bool(0.02 <= rr <= 0.08),
                        "rho_d_mean_under_null": float(np.mean([r["rho_d"] for r in res]))}
        # (ii) calibrate a for mean rho_d ~ 0.3
        cal = {}
        for a in (0.3, 0.5, 0.7, 0.9, 1.2, 1.6):
            rs = list(ex.map(one, [(cells, disc, cont, counts, a, b0, 0.5, 5000 + i, perms_r[:2000], perms_naive[:200])
                                   for i in range(24)]))
            cal[a] = float(np.mean([r["rho_d"] for r in rs]))
        a_star = min(cal, key=lambda a: abs(cal[a] - 0.3))
        res2 = list(ex.map(one, [(cells, disc, cont, counts, a_star, b0, 0.5, 9000 + i, perms_r, perms_naive[:200])
                                 for i in range(200)]))
        power = np.mean([(r["rho_d"] >= 0.3) and (r["p_restricted"] < 0.05) for r in res2])
        truth = float(np.mean([r["rho_d"] for r in res2]))
        out["power"] = {"calibration_mean_rho_by_a": cal, "a": a_star, "mean_rho_d": truth, "n_datasets": 200,
                        "power_rho_ge_0.3_and_p_lt_0.05": float(power),
                        "power_p_lt_0.05_only": float(np.mean([r["p_restricted"] < 0.05 for r in res2])),
                        "known_limitation": bool(power < 0.5)}
        # (iii) bootstrap coverage
        cov = list(ex.map(boot_cov, [(cells, disc, cont, counts, a_star, b0, 0.5, 20000 + i, truth) for i in range(50)]))
        out["bootstrap_coverage"] = {"n_runs": 50, "B": 100, "truth_proxy": truth,
                                     "coverage": float(np.mean([c["covers"] for c in cov]))}
    # (iv) crossvalidated distance on noise
    Xn, labn = make(cells, disc, cont, counts, 0.0, 0.0, 0.0, 77)
    E = A.euclid_centroid_rdm(Xn, labn, cells)
    CV = A.crossval_centroid_rdm(Xn, labn, cells, n_split=50)
    out["crossval_noise"] = {"plain_euclid_sq_mean": float(np.mean(A.upper(E) ** 2)),
                             "crossval_sq_mean": float(np.mean(A.upper(CV))),
                             "crossval_sq_sd": float(np.std(A.upper(CV)))}
    out["utc"] = utc_now()
    write_json(RESULTS / "t4_synthetic.json", out)
    print({k: v for k, v in out.items() if k in ("type1", "power", "bootstrap_coverage", "crossval_noise")})


if __name__ == "__main__":
    main()
