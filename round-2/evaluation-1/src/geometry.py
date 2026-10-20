#!/usr/bin/env python3
"""(0b) Geometry robustness of exp2's forced-prompt centroid geodesics.

Recipe identical to exp2 analysis/geometry.py (pca95 -> symmetric kNN graph with MST patch -> centroids attached as
leaves to their k nearest points -> centroid-to-centroid shortest paths). Reproduces exp2's committed matrices
(T1 L27 k=10, T2 L24 k=10) and the T2 sensitivity matrix first, then sweeps k x layer with 1000 paraphrase-level
subsamples (24 of 30 ids, same ids for every mode) that rebuild PCA, graph and centroids in every draw.

Usage: uv run geometry.py [--n-draws 1000] [--masked-draws 200]
"""
from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")  # one BLAS thread per worker: the container quota is ~7 CPUs

import argparse
import itertools
import multiprocessing as mp
import resource
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from loguru import logger
from scipy import stats
from scipy.sparse import coo_matrix, csr_matrix
from scipy.sparse.csgraph import connected_components, minimum_spanning_tree, shortest_path
from scipy.spatial.distance import cdist

from common import EXP, RES, TAB, clean, jdump, read_jsonl, setup_logging

CATS = {"t1": ["bfs", "dfs", "bidir_bfs", "iddfs", "astar", "dijkstra_unit"],
        "t2": ["dijkstra", "bellman_ford_spfa", "bidir_dijkstra", "floyd_warshall", "dial"]}
HNAME = {"bfs": "BFS", "dfs": "DFS", "bidir_bfs": "BIDIR_BFS", "iddfs": "IDDFS", "astar": "ASTAR",
         "dijkstra_unit": "UNIT_DIJKSTRA", "dijkstra": "DIJKSTRA", "bellman_ford_spfa": "BF_SPFA",
         "bidir_dijkstra": "BIDIR_DIJKSTRA", "floyd_warshall": "FW", "dial": "DIAL"}
LAYERS = {"t1": [24, 25, 26, 27, 28], "t2": [21, 22, 23, 24, 25, 26, 27]}
KS = [5, 10, 15, 20]
HEAD = {"t1": 27, "t2": 24}
REALISED = {"t1": "dfs", "t2": "bellman_ford_spfa"}


def pca95(X: np.ndarray, cap: int = 50, var: float = 0.95):
    mu = X.mean(0)
    Xc = X - mu
    U, S, Vt = np.linalg.svd(Xc, full_matrices=False)
    ev = S ** 2 / max(np.sum(S ** 2), 1e-12)
    k = int(np.searchsorted(np.cumsum(ev), var) + 1)
    k = max(2, min(k, cap, Vt.shape[0]))
    return mu, Vt[:k], ev[:k]


def knn_graph(P: np.ndarray, k: int):
    n = len(P)
    D = cdist(P, P)
    np.fill_diagonal(D, np.inf)
    k = min(k, n - 1)
    idx = np.argsort(D, axis=1)[:, :k]
    rows = np.repeat(np.arange(n), k)
    cols = idx.ravel()
    G = coo_matrix((D[rows, cols], (rows, cols)), shape=(n, n)).tocsr()
    G = G.maximum(G.T)
    ncomp, _ = connected_components(G, directed=False)
    mst_added = False
    if ncomp > 1:
        Df = D.copy()
        np.fill_diagonal(Df, 0)
        mst = minimum_spanning_tree(csr_matrix(Df)).tocsr()
        G = G.maximum(mst.maximum(mst.T))
        mst_added = True
    return G, {"n_components_knn": int(ncomp), "mst_added": mst_added}


def attach(G: csr_matrix, P: np.ndarray, Q: np.ndarray, k: int) -> csr_matrix:
    n, m = len(P), len(Q)
    D = cdist(Q, P)
    k = min(k, n)
    idx = np.argsort(D, axis=1)[:, :k]
    G2 = G.tocoo()
    r = [G2.row, np.repeat(np.arange(n, n + m), k), idx.ravel()]
    c = [G2.col, idx.ravel(), np.repeat(np.arange(n, n + m), k)]
    w = D[np.repeat(np.arange(m), k), idx.ravel()]
    v = [G2.data, w, w]
    return coo_matrix((np.concatenate(v), (np.concatenate(r), np.concatenate(c))), shape=(n + m, n + m)).tocsr()


def centroid_geodesics(X: np.ndarray, labels: np.ndarray, cat: list[str], k: int, Cfix: np.ndarray | None = None,
                       full: bool = False):
    mu, comps, ev = pca95(X)
    P = (X - mu) @ comps.T
    G, info = knn_graph(P, k)
    C = np.stack([X[labels == m].mean(0) for m in cat]) if Cfix is None else Cfix
    Q = (C - mu) @ comps.T
    GA = attach(G, P, Q, k)
    n = len(P)
    if full:
        Dall = shortest_path(GA, directed=False)
        return Dall[n:, n:], {"pca_dims": int(len(ev)), **info}, Dall, P, Q
    D = shortest_path(GA, directed=False, indices=np.arange(n, n + len(Q)))[:, n:]
    return D, {"pca_dims": int(len(ev)), **info}, Q


def load_points(task: str, layer: int, kind: str = "forced"):
    index = read_jsonl(EXP["exp2"] / "cache" / "hR_index.jsonl")
    H = np.load(EXP["exp2"] / "cache" / f"hR_layer{layer}.npy", mmap_mode="r")
    sel = [i for i, r in enumerate(index) if r["task"] == task and r["condition"].startswith(f"{kind}:")]
    X = np.asarray(H[sel], dtype=np.float64)
    lab = np.array([index[i]["condition"].split(":")[1] for i in sel])
    pid = np.array([int(index[i]["paraphrase_id"]) for i in sel])
    return X, lab, pid, sel, index


def kruskal_stress(D: np.ndarray, seed: int = 0) -> float:
    from sklearn.manifold import MDS
    try:
        mds = MDS(n_components=2, metric="precomputed", n_init=4, random_state=seed, init="random")
        Y = mds.fit_transform(D)
    except TypeError:
        mds = MDS(n_components=2, dissimilarity="precomputed", n_init=4, random_state=seed)
        Y = mds.fit_transform(D)
    d = cdist(Y, Y)
    iu = np.triu_indices(len(D), 1)
    return float(np.sqrt(((d[iu] - D[iu]) ** 2).sum() / (D[iu] ** 2).sum()))


def setting_job(args: tuple) -> dict:
    task, layer, kind, n_draws, seed = args
    cat = CATS[task]
    X, lab, pid, _, _ = load_points(task, layer, kind)
    ids = np.unique(pid)
    rng = np.random.default_rng(seed)
    draws = [np.sort(rng.choice(ids, 24, replace=False)) for _ in range(n_draws)]
    out = {}
    surv = cat[1:]
    for k in KS:
        D, info, Dall, P, Q = centroid_geodesics(X, lab, cat, k, full=True)
        row = D[0, 1:]
        order = [surv[i] for i in np.argsort(row)]
        # Euclidean nearest in PCA space (same projection)
        eu = np.linalg.norm(Q[1:] - Q[0], axis=1)
        eu_near = surv[int(np.argmin(eu))]
        stress = kruskal_stress(Dall) if kind == "forced" else None
        near = np.zeros(len(surv))
        ranks = np.zeros(len(surv))
        bf_vs_bidir = 0
        two_nearest = 0
        eu_agree = 0
        top1_same = 0
        mst_count = 0
        for dr in draws:
            m = np.isin(pid, dr)
            Dd, inf2, Qd = centroid_geodesics(X[m], lab[m], cat, k)
            r = Dd[0, 1:]
            rk = stats.rankdata(r, method="min")
            ranks += rk
            j = int(np.argmin(r))
            near[j] += 1
            top1_same += int(surv[j] == order[0])
            eud = np.linalg.norm(Qd[1:] - Qd[0], axis=1)
            eu_agree += int(int(np.argmin(eud)) == j)
            mst_count += int(inf2["mst_added"])
            if task == "t2":
                bf_vs_bidir += int(r[surv.index("bellman_ford_spfa")] < r[surv.index("bidir_dijkstra")])
            else:
                two = set(np.array(surv)[np.argsort(r)[:2]])
                two_nearest += int(two == {"dfs", "dijkstra_unit"})
        nd = len(draws)
        res = {"task": task, "layer": layer, "k": k, "kind": kind, "full_order": [HNAME[o] for o in order],
               "full_distances": {HNAME[s]: float(v) for s, v in zip(surv, row)},
               "graph": info, "share_nearest": {HNAME[s]: near[i] / nd for i, s in enumerate(surv)},
               "mean_rank": {HNAME[s]: ranks[i] / nd for i, s in enumerate(surv)},
               "top1_stability": top1_same / nd, "euclid_nearest_full": HNAME[eu_near],
               "geodesic_euclid_agree_full": bool(eu_near == order[0]), "geodesic_euclid_agree_share": eu_agree / nd,
               "kruskal_stress1_mds2": stress, "n_draws": nd, "mst_added_share": mst_count / nd,
               "realised_substitute_rank_full": order.index(REALISED[task]) + 1}
        if task == "t2":
            res.update({"P_BF_SPFA_nearest": near[surv.index("bellman_ford_spfa")] / nd,
                        "P_BF_SPFA_nearer_than_BIDIR_DIJKSTRA": bf_vs_bidir / nd,
                        "P_FW_nearest": near[surv.index("floyd_warshall")] / nd})
        else:
            res.update({"P_DFS_nearest": near[surv.index("dfs")] / nd,
                        "P_UNIT_DIJKSTRA_nearest": near[surv.index("dijkstra_unit")] / nd,
                        "P_DFS_UNIT_DIJKSTRA_two_nearest": two_nearest / nd})
        out[k] = res
    return out


def reproduce() -> dict:
    gb = __import__("json").loads((EXP["exp2"] / "results" / "geometry_b.json").read_text())
    ms = __import__("json").loads((EXP["exp2"] / "results" / "manipulation_sensitivity.json").read_text())
    out = {}
    for task in ("t1", "t2"):
        L = HEAD[task]
        X, lab, pid, sel, index = load_points(task, L)
        D, info, _ = centroid_geodesics(X, lab, CATS[task], 10)
        rep = np.array(gb[task]["centroid_geodesic"])
        diff = np.abs(np.round(D, 3) - np.round(rep, 3))
        out[task] = {"layer": L, "k": 10, "recomputed_row0": D[0].tolist(), "committed_row0": rep[0].tolist(),
                     "max_abs_diff": float(diff.max()), "match_at_exp2_tolerance_0.05": bool(diff.max() <= 0.05),
                     "pca_dims": info["pca_dims"], "committed_pca_dims": gb[task]["pca_dims"],
                     "source": "exp2/results/geometry_b.json#" + task + ".centroid_geodesic"}
        if task == "t2":
            # sensitivity: flagged modes' centroids from paraphrases whose forced sample was labelled X, same graph
            rowsA = read_jsonl(EXP["exp2"] / "data" / "samples_phaseA.jsonl")
            lab_of = {(r["condition"], int(r["paraphrase_id"])): r["label"] for r in rowsA
                      if r["task"] == task and r["condition"].startswith("forced:")}
            H = np.load(EXP["exp2"] / "cache" / f"hR_layer{L}.npy", mmap_mode="r")
            cat = CATS[task]
            C = np.stack([X[lab == m].mean(0) for m in cat])
            Cs = C.copy()
            kept = {}
            for m in ms[task]["flagged_modes"]:
                s2 = [i for i in sel if lab_of.get((index[i]["condition"], int(index[i]["paraphrase_id"]))) == m and
                      index[i]["condition"] == f"forced:{m}"]
                kept[m] = len(s2)
                if len(s2) >= 3:
                    Cs[cat.index(m)] = np.asarray(H[s2], dtype=np.float64).mean(0)
            D1, _, _ = centroid_geodesics(X, lab, cat, 10, Cfix=Cs)
            rep1 = np.array(ms[task]["centroid_geodesic_sensitivity"])
            d1 = np.abs(np.round(D1, 3) - np.round(rep1, 3))
            out[task]["sensitivity"] = {"recomputed_row0": D1[0].tolist(), "committed_row0": rep1[0].tolist(),
                                        "kept": kept, "committed_kept": ms[task]["n_paraphrases_kept"],
                                        "max_abs_diff": float(d1.max()), "match": bool(d1.max() <= 0.05),
                                        "dijkstra_row_named": {HNAME[m]: float(D1[0, j]) for j, m in enumerate(cat) if j},
                                        "nearest_survivor": HNAME[cat[1:][int(np.argmin(D1[0, 1:]))]],
                                        "source": "exp2/results/manipulation_sensitivity.json#t2.centroid_geodesic_sensitivity"}
    return out


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-draws", type=int, default=1000)
    ap.add_argument("--masked-draws", type=int, default=200)
    args = ap.parse_args()
    setup_logging("geometry")
    resource.setrlimit(resource.RLIMIT_AS, (30 * 1024 ** 3, 30 * 1024 ** 3))
    t0 = time.time()
    rep = reproduce()
    for t, r in rep.items():
        logger.info(f"reproduce {t}: max|diff|={r['max_abs_diff']:.4f} match={r['match_at_exp2_tolerance_0.05']}"
                    + (f"; sensitivity match={r['sensitivity']['match']}" if "sensitivity" in r else ""))
    jobs = [(t, L, "forced", args.n_draws, 100 + L) for t in ("t1", "t2") for L in LAYERS[t]]
    jobs += [(t, HEAD[t], "masked", args.masked_draws, 500) for t in ("t1", "t2")]
    with ProcessPoolExecutor(max_workers=6, mp_context=mp.get_context("spawn")) as ex:
        results = list(ex.map(setting_job, jobs))
    grid = [r for res in results for r in res.values()]
    logger.info(f"{len(grid)} settings in {time.time() - t0:.0f}s")
    summary = {}
    for t in ("t1", "t2"):
        cells = [g for g in grid if g["task"] == t and g["kind"] == "forced"]
        orders = {(c["layer"], c["k"]): [c["full_distances"][s] for s in sorted(c["full_distances"])] for c in cells}
        taus = []
        for a, b in itertools.combinations(sorted(orders), 2):
            taus.append(stats.kendalltau(orders[a], orders[b], variant="b").statistic)
        rk = [c["realised_substitute_rank_full"] for c in cells]
        summary[t] = {"n_settings": len(cells), "kendall_tau_b_mean": float(np.mean(taus)), "kendall_tau_b_min": float(np.min(taus)),
                      "share_settings_realised_rank": {str(r): float(np.mean([x == r for x in rk])) for r in (1, 2, 3)},
                      "realised_substitute": HNAME[REALISED[t]]}
    wording = ("consistent with geodesic proximity and with typicality; not separated on these events. On both tasks the "
               "realised substitute is also the latent runner-up (DFS on T1, BF_SPFA on T2), so no geometric result can "
               "separate the two accounts.")
    out = {"reproduce": rep, "grid": grid, "across_settings": summary, "wording": wording,
           "seconds": time.time() - t0}
    jdump(clean(out), RES / "geometry.json")
    import pandas as pd
    flat = []
    for g in grid:
        d = {k: v for k, v in g.items() if not isinstance(v, (dict, list))}
        d["full_order"] = ">".join(g["full_order"])
        for s, v in g["share_nearest"].items():
            d[f"share_nearest_{s}"] = v
        for s, v in g["mean_rank"].items():
            d[f"mean_rank_{s}"] = v
        for s, v in g["full_distances"].items():
            d[f"dist_{s}"] = v
        flat.append(d)
    pd.DataFrame(flat).to_csv(TAB / "geometry_stability.csv", index=False)
    logger.info("wrote results/geometry.json and tables/geometry_stability.csv")


if __name__ == "__main__":
    main()
