#!/usr/bin/env python3
"""T4 (iii) ADDENDUM (after COMMIT1): bootstrap coverage against each synthetic dataset's OWN expected rho_d (same
planted cell structure, 20 fresh noise draws), which is the estimand a within-cell program bootstrap targets. The
committed T4 compared CIs with the across-dataset mean (coverage 0.56), which includes cell-structure variability the
bootstrap cannot see. Writes results/t4b_bootstrap_coverage.json."""
import multiprocessing as mp
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np  # noqa: E402

import analysis_g2 as A  # noqa: E402
from common import read_json, utc_now  # noqa: E402
from tpg2 import DATA, K_PRIMARY, RESULTS, write_json  # noqa: E402

DIM = 256


def offsets(cells, disc, cont, a, b, s, seed):
    rng = np.random.default_rng(seed)
    ed = {d: rng.normal(size=DIM) / np.sqrt(DIM) for d in sorted(set(disc.values()))}
    ec = {c: rng.normal(size=DIM) / np.sqrt(DIM) for c in sorted(set(cont.values()))}
    return {c: a * ed[disc[c]] + b * ec[cont[c]] + s * rng.normal(size=DIM) / np.sqrt(DIM) for c in cells}


def draw(off, cells, counts, seed):
    rng = np.random.default_rng(seed)
    X = np.concatenate([off[c] + rng.normal(size=(counts[c], DIM)) / np.sqrt(DIM) for c in cells])
    lab = np.array([c for c in cells for _ in range(counts[c])])
    return X, lab


def rho(X, lab, cells, Dd, Dc):
    D, _, _ = A.geo_rdm(X, lab, cells, K_PRIMARY)
    return A.partial_spearman(A.upper(D), A.upper(Dd), [A.upper(Dc)])


def one(args):
    cells, disc, cont, counts, a, b, s, seed = args
    Dd, Dc = A.cell_model_rdms(cells, disc, cont)
    off = offsets(cells, disc, cont, a, b, s, seed)
    truth = float(np.mean([rho(*draw(off, cells, counts, seed * 100 + r), cells, Dd, Dc) for r in range(20)]))
    X, lab = draw(off, cells, counts, seed * 100 + 99)
    rng = np.random.default_rng(seed + 5)
    vals = []
    for _ in range(100):
        idx = A.boot_indices(lab, cells, rng)
        vals.append(rho(X[idx], lab[idx], cells, Dd, Dc))
    lo, hi = np.nanpercentile(vals, [2.5, 97.5])
    point = rho(X, lab, cells, Dd, Dc)
    return {"truth": truth, "point": point, "lo": float(lo), "hi": float(hi), "covers": bool(lo <= truth <= hi),
            "boot_mean": float(np.nanmean(vals))}


if __name__ == "__main__":
    fr = read_json(DATA / "frames.json")
    g1 = fr["g1_cells"]
    cells = [x["cell"] for x in g1]
    disc = {x["cell"]: x["disc"] for x in g1}
    cont = {x["cell"]: x["cont"] for x in g1}
    counts = {x["cell"]: x["n"] for x in g1}
    with ProcessPoolExecutor(max_workers=6, mp_context=mp.get_context("spawn")) as ex:
        res = list(ex.map(one, [(cells, disc, cont, counts, 0.9, 1.5, 0.5, 31000 + i) for i in range(50)]))
    cov = float(np.mean([r["covers"] for r in res]))
    bias = float(np.mean([r["boot_mean"] - r["point"] for r in res]))
    out = {"label": "T4 (iii) addendum, post-COMMIT1", "n_runs": 50, "B": 100, "a": 0.9, "b": 1.5, "s": 0.5,
           "coverage_vs_own_expected_value": cov, "mean_bootstrap_shift_boot_minus_point": bias,
           "mean_point_minus_truth": float(np.mean([r["point"] - r["truth"] for r in res])),
           "mean_ci_width": float(np.mean([r["hi"] - r["lo"] for r in res])), "runs": res, "utc": utc_now()}
    write_json(RESULTS / "t4b_bootstrap_coverage.json", out)
    print({k: v for k, v in out.items() if k != "runs"})
