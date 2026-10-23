#!/usr/bin/env python3
"""EXPLORATORY (after COMMIT1; the D_beh sensitivity was dropped before COMMIT1 for time, deviation D11): a GRADED
behavioural distance. Each factorial program runs (seeded, instrument child) on 8 probe grids; its first-expansion
rank of every reachable free cell defines a behaviour vector; program distance = 1 - Spearman of those ranks,
averaged over grids; D_beh(cell a, cell b) = mean program distance. Tests: does the cell map follow graded behaviour
once container (and surface / length / dispersion) is controlled? Restricted permutation = cells permuted within
container. Program level: partial Spearman(geodesic, behaviour | AST surface, same-container). Writes
results/explore_dbeh.json."""

from __future__ import annotations

import itertools
import multiprocessing as mp
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np  # noqa: E402
from scipy.stats import rankdata, spearmanr  # noqa: E402

PROBE_IDX = None


def probe_set() -> list[int]:
    import orderclass

    P = orderclass.probes()
    want = ["open", "open", "maze", "maze", "rooms", "rooms", "utrap", "braided"]
    used, out = set(), []
    for fam in want:
        i = next(i for i, p in enumerate(P) if p["family"] == fam and i not in used)
        used.add(i)
        out.append(i)
    return out


def behaviour(args: tuple) -> tuple[str, list[list[float]] | None]:
    uid, code, idx = args
    import instrument
    import orderclass

    P = orderclass.probes()
    pre = orderclass.probe_pre()
    recs = instrument.run_child(code, [P[i] for i in idx], seed=0, timeout_s=60)
    vecs = []
    for j, i in enumerate(idx):
        cells = sorted(pre[i]["d_s"])
        rec = recs.get(j)
        u = instrument._useq(instrument._E(rec)) if rec else []
        pos = {c: k for k, c in enumerate(u)}
        vecs.append([float(pos.get(c, len(u))) for c in cells])
    return uid, vecs


def main() -> None:
    import analysis_g2 as A
    import geometry
    import run_analysis as RA
    from accept import jaccard, shingles
    from common import read_json
    from tpg2 import DATA, K_PRIMARY, RESULTS, write_json

    fr = read_json(DATA / "frames.json")
    items = {it["id"]: it for it in read_json(DATA / "state_items.json")["items"]}
    cells = [c["cell"] for c in fr["g1_cells"]]
    disc = {c["cell"]: c["disc"] for c in fr["g1_cells"]}
    cont = {c["cell"]: c["cont"] for c in fr["g1_cells"]}
    fact = [f for f in fr["factorial"] if f["cell"] in cells]
    ids = [f["id"] for f in fact]
    lab = np.array([f["cell"] for f in fact])
    idx = probe_set()
    with ProcessPoolExecutor(max_workers=6, mp_context=mp.get_context("spawn")) as ex:
        res = dict(ex.map(behaviour, [(u, items[u]["scrubbed"], idx) for u in ids], chunksize=4))
    n = len(ids)
    Bm = np.zeros((n, n))
    for g in range(len(idx)):
        V = np.stack([rankdata(res[u][g]) for u in ids])
        V = V - V.mean(1, keepdims=True)
        nrm = np.linalg.norm(V, axis=1)
        nrm[nrm == 0] = 1.0
        C = (V @ V.T) / np.outer(nrm, nrm)
        Bm += 1 - C
    Bm /= len(idx)
    groups = [np.where(lab == c)[0] for c in cells]
    Dbeh = np.zeros((len(cells), len(cells)))
    for i in range(len(cells)):
        for j in range(len(cells)):
            sub = Bm[np.ix_(groups[i], groups[j])]
            if i == j:
                sub = sub[~np.eye(len(sub), dtype=bool)]
            Dbeh[i, j] = sub.mean()
    Dd, Dc = A.cell_model_rdms(cells, disc, cont)
    sh = [shingles(items[u]["scrubbed"]) for u in ids]
    J = np.array([[1 - jaccard(a, b) for b in sh] for a in sh])
    out = {"label": "EXPLORATORY (post-COMMIT1)", "probes": idx,
           "spearman_Dbeh_Ddisc": float(spearmanr(A.upper(Dbeh), A.upper(Dd)).statistic),
           "spearman_Dbeh_Dcont": float(spearmanr(A.upper(Dbeh), A.upper(Dc)).statistic),
           "D_beh": Dbeh.tolist(), "cells": cells}
    # within-container permutations of cell identity for D_beh
    gr = {}
    for i, c in enumerate(cells):
        gr.setdefault(cont[c], []).append(i)
    perms = []
    for combo in itertools.product(*[list(itertools.permutations(g)) for g in gr.values()]):
        p = list(range(len(cells)))
        for g, pg in zip(gr.values(), combo):
            for a, b in zip(g, pg):
                p[a] = b
        perms.append(p)
    for tag in ("8b", "32b"):
        D_ = RA.load_all(tag)
        X = RA.X_new(D_, ids)
        geo, _ = geometry.geodesics(X, K_PRIMARY)
        Dm = geometry.class_matrix(geo, lab, cells)
        lens = np.array([D_["meta"][u]["n_code_tokens"] for u in ids], float)
        Ds = A.surface_cell_rdm(J, groups)
        Dl = A.len_cell_rdm(lens, groups)
        dg = np.diag(Dm)
        Dp = np.abs(dg[:, None] - dg[None, :])
        y = A.upper(Dm)
        r0 = float(spearmanr(y, A.upper(Dbeh)).statistic)
        rp = A.partial_spearman(y, A.upper(Dbeh), [A.upper(Dc)])
        rf = A.partial_spearman(y, A.upper(Dbeh), [A.upper(Dc), A.upper(Ds), A.upper(Dl), A.upper(Dp)])
        null = []
        for p in perms[:: max(1, len(perms) // 3000)]:
            Pb = Dbeh[np.ix_(p, p)]
            null.append(A.partial_spearman(y, A.upper(Pb), [A.upper(Dc)]))
        null = np.array(null)
        iu = np.triu_indices(n, 1)
        same_c = np.array([[cont[a] == cont[b] for b in lab] for a in lab], float)
        prog = A.partial_spearman(geo[iu], Bm[iu], [J[iu], same_c[iu]])
        prog0 = float(spearmanr(geo[iu], Bm[iu]).statistic)
        progJ = A.partial_spearman(geo[iu], J[iu], [Bm[iu], same_c[iu]])
        out[tag] = {"cell_level": {"spearman_D_Dbeh": r0, "partial_D_Dbeh_given_cont": rp,
                                   "partial_D_Dbeh_given_cont_surf_len_disp": rf,
                                   "p_within_container_perm": float(np.mean(null >= rp - 1e-12)), "n_perm": int(len(null))},
                    "program_level": {"spearman_geo_beh": prog0, "partial_geo_beh_given_surface_samecontainer": prog,
                                      "partial_geo_surface_given_beh_samecontainer": progJ, "n_pairs": int(len(iu[0]))}}
        print(tag, out[tag])
    write_json(RESULTS / "explore_dbeh.json", out)
    print("Dbeh~Ddisc", out["spearman_Dbeh_Ddisc"], "Dbeh~Dcont", out["spearman_Dbeh_Dcont"])


if __name__ == "__main__":
    main()
