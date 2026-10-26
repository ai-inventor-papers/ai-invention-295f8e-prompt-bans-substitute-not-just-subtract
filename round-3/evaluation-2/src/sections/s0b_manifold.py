"""(0b) Manifold: exp9 figures and implemented counts; geometry at the label-independent g16 position with nulls.

Re-derivation follows exp9 analysis/manifold.py and mb/sets.py exactly: forced programs in the 'base' context
(states/<task>/base/part_*.npz), PCA-50 per (layer, position), symmetric kNN graph (bridged to one component),
Dijkstra geodesics, centroid matrix = median geodesic between class point sets (diagonal = median within-class
distance), normalised by the median off-diagonal entry. Nulls: N1 global label permutation, N2 exchangeability
within the BFS + BiBFS pool, N3 Gaussian with matched mean/covariance. Persistent H1 by ripser; power by planted loops.
"""

from __future__ import annotations

import json
import math
import multiprocessing as mp
import shutil
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from typing import Any

import numpy as np
import pandas as pd
from loguru import logger

from common.paths import FIGS, RESULTS, SEED, TABLES, dep, read_json, src, write_json
from common.rows import iter_rows

LAYERS_ALL = list(range(20, 29))
POS = {"g8": 0, "g16": 1, "g32": 2, "pre": 3}
ALGS = {"t1": ["bfs", "dfs", "bibfs", "iddfs", "astar", "gbfs", "idastar"],
        "t2": ["dijkstra", "bf_spfa", "bidijkstra", "floyd", "dial"]}
K_SWEEP = (5, 10, 15, 20)
LAYERS_SUB = (20, 24, 28)
CHUNKS = 8   # random-number streams for the nulls and power runs are split into a FIXED number of chunks, so results
             # do not depend on the worker count


def load_forced(task: str, layers: tuple[int, ...], positions: tuple[str, ...]) -> tuple[dict, np.ndarray]:
    d = dep("exp9", f"states/{task}/base")
    Xs, metas = [], []
    for p in sorted(d.glob("part_*.npz")):
        z = np.load(p, allow_pickle=False)
        X = z["X"]
        li = [LAYERS_ALL.index(l) for l in layers]
        pi = [POS[q] for q in positions]
        Xs.append(X[:, li][:, :, pi].astype(np.float32))
        metas += json.loads(str(z["meta"]))
        del X, z
    X = np.concatenate(Xs)
    keep = [i for i, m in enumerate(metas) if m.get("kind") == "forced" and m.get("algorithm") in ALGS[task]]
    lab = np.array([metas[i]["algorithm"] for i in keep])
    out = {}
    for a, l in enumerate(layers):
        for b, q in enumerate(positions):
            out[(l, q)] = X[keep, a, b, :]
    return out, lab


def pca_fit(Y: np.ndarray, n: int = 50) -> tuple[np.ndarray, np.ndarray]:
    mu = Y.mean(axis=0, keepdims=True)
    _, _, Vt = np.linalg.svd(Y - mu, full_matrices=False)
    return mu, Vt[:min(n, Vt.shape[0])]


def knn_geodesic(Z: np.ndarray, k: int = 10) -> tuple[np.ndarray, dict[str, Any]]:
    from scipy.sparse import csr_matrix
    from scipy.sparse.csgraph import connected_components, shortest_path
    from scipy.spatial.distance import cdist

    n = Z.shape[0]
    E = cdist(Z, Z)
    k = min(k, n - 1)
    idx = np.argsort(E, axis=1)[:, 1:k + 1]
    W = np.zeros((n, n))
    rows = np.repeat(np.arange(n), k)
    W[rows, idx.ravel()] = E[rows, idx.ravel()]
    W = np.maximum(W, W.T)
    info = {"k": k, "n": n, "bridges": 0}
    ncomp, lab = connected_components(csr_matrix(W > 0), directed=False)
    while ncomp > 1:
        best = None
        for c in range(1, ncomp):
            a, b = np.where(lab == 0)[0], np.where(lab == c)[0]
            sub = E[np.ix_(a, b)]
            i, j = np.unravel_index(np.argmin(sub), sub.shape)
            if best is None or sub[i, j] < best[0]:
                best = (sub[i, j], a[i], b[j])
        W[best[1], best[2]] = W[best[2], best[1]] = best[0]
        info["bridges"] += 1
        ncomp, lab = connected_components(csr_matrix(W > 0), directed=False)
    G = shortest_path(csr_matrix(W), method="D", directed=False)
    return G, info


def centroid_matrix(G: np.ndarray, labels: np.ndarray, algs: list[str]) -> np.ndarray:
    K = len(algs)
    D = np.zeros((K, K))
    ids = {a: np.where(labels == a)[0] for a in algs}
    for i, a in enumerate(algs):
        for j, b in enumerate(algs):
            sub = G[np.ix_(ids[a], ids[b])]
            if i == j:
                m = sub[~np.eye(len(ids[a]), dtype=bool)] if len(ids[a]) > 1 else sub.ravel()
                D[i, j] = np.median(m) if m.size else 0.0
            else:
                D[i, j] = np.median(sub)
    off = D[~np.eye(K, dtype=bool)]
    return D / np.median(off)


def stress1(D: np.ndarray, seed: int = 0) -> float:
    from scipy.spatial.distance import pdist, squareform
    from sklearn.manifold import MDS

    Dm = D.copy()
    np.fill_diagonal(Dm, 0.0)
    m = MDS(n_components=2, dissimilarity="precomputed", n_init=8, random_state=seed, normalized_stress=False)
    Z = m.fit_transform(Dm)
    E = squareform(pdist(Z))
    iu = np.triu_indices_from(Dm, 1)
    return float(math.sqrt(((Dm[iu] - E[iu]) ** 2).sum() / (Dm[iu] ** 2).sum()))


def separability(D: np.ndarray) -> np.ndarray:
    diag = np.diag(D)
    S = np.zeros_like(D)
    for i in range(len(D)):
        for j in range(len(D)):
            S[i, j] = D[i, j] / max(1e-12, 0.5 * (diag[i] + diag[j]))
    return S


def _h1(P: np.ndarray, distance_matrix: bool = False) -> tuple[float, float]:
    from ripser import ripser

    dg = ripser(P, maxdim=1, distance_matrix=distance_matrix)["dgms"][1]
    if len(dg) == 0:
        return 0.0, 0.0
    life = np.sort(dg[:, 1] - dg[:, 0])[::-1]
    life = life[np.isfinite(life)]
    if len(life) == 0:
        return 0.0, 0.0
    return float(life[0]), float(life[0] / life[1]) if len(life) > 1 and life[1] > 0 else float("inf")


def _gauss_null_worker(args: tuple) -> list[float]:
    mean, cov, n, reps, seed = args
    rng = np.random.default_rng(seed)
    return [_h1(rng.multivariate_normal(mean, cov, size=n))[0] for _ in range(reps)]


def _planted_worker(args: tuple) -> list[float]:
    sizes, cov_w, radius, shape, reps, seed = args
    rng = np.random.default_rng(seed)
    K = len(sizes)
    d = cov_w.shape[0]
    out = []
    for _ in range(reps):
        if shape == "loop":
            ang = 2 * np.pi * np.arange(K) / K
            centres = np.zeros((K, d))
            centres[:, 0], centres[:, 1] = radius * np.cos(ang), radius * np.sin(ang)
        else:
            centres = np.zeros((K, d))
            centres[:, 0] = radius * (np.arange(K) - (K - 1) / 2)
        P = np.concatenate([rng.multivariate_normal(centres[i], cov_w, size=s) for i, s in enumerate(sizes)])
        out.append(_h1(P)[0])
    return out


_POOL: ProcessPoolExecutor | None = None


def _par(fn, jobs: list[tuple], workers: int) -> list:
    """Run jobs on one shared spawn-context pool (created once per section run; spawning per call is slow)."""
    global _POOL
    if _POOL is None:
        _POOL = ProcessPoolExecutor(max_workers=workers, mp_context=mp.get_context("spawn"))
    return [x for r in _POOL.map(fn, jobs) for x in r]


def implemented_counts(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    conds = ["baseline", "single:bfs", "multi:TOP", "multi:ARC", "multi:SCATTER", "multi:TOP5", "single:dijkstra",
             "los:dijkstra", "los:bf_spfa", "los:bidijkstra", "los:floyd", "los:dial"]
    for c in conds:
        for t in ("t1", "t2"):
            rs = [r for r in rows if r["exp"] == "exp9" and r["condition"] == c and r["task"] == t]
            if not rs:
                continue
            banned = set(rs[0]["banned_set"])
            rec = {"condition": c, "task": t, "n": len(rs), "banned_set": sorted(banned),
                   "flag": "default-only survivor" if c == "los:dijkstra" else ""}
            for a in ALGS[t] + ["other", "other_ext", "unparseable"]:
                def lab9(r):
                    if r["label_fine"] in ("astar", "gbfs"):
                        return r["label_fine"]
                    return r["label"]
                att = sum(lab9(r) == a for r in rs)
                cor = sum(lab9(r) == a and r["passed"] is True for r in rs)
                rec[f"{a}_attempted"] = att
                rec[f"{a}_correct"] = cor
                rec[f"{a}_banned"] = a in banned
            out.append(rec)
    return out


def run(n_perm: int = 500, n_null: int = 200, n_power: int = 200, workers: int = 6) -> dict[str, Any]:
    rng = np.random.default_rng(SEED)
    # figures
    figdir = FIGS / "exp9"
    figdir.mkdir(parents=True, exist_ok=True)
    found = sorted(dep("exp9", "figures").glob("fig_manifold_*.pdf")) + sorted(dep("exp9", "figures").glob("fig_kstab_*.pdf"))
    for p in found:
        for ext in (".pdf", ".png"):
            q = p.with_suffix(ext)
            if q.exists():
                shutil.copy2(q, figdir / q.name)
    n_manifold = len([p for p in found if p.name.startswith("fig_manifold_")])
    rows = list(iter_rows())
    counts = implemented_counts(rows)
    pd.DataFrame(counts).to_csv(TABLES / "manifold_implemented_counts.csv", index=False)
    top5 = next(r for r in counts if r["condition"] == "multi:TOP5")
    man = read_json(dep("exp9", "results/manifold.json"))
    pers = read_json(dep("exp9", "results/persistence.json"))
    res: dict[str, Any] = {"figures_found": {"fig_manifold": n_manifold, "claimed": 14,
                                             "fig_kstab": len(found) - n_manifold,
                                             "files": [p.name for p in found]},
                           "top5_banned_counts": {"bfs_attempted": top5["bfs_attempted"],
                                                  "dfs_attempted": top5["dfs_attempted"], "expected": [63, 36]},
                           "tasks": {}}
    for t in ("t1", "t2"):
        algs = ALGS[t]
        data, lab = load_forced(t, LAYERS_SUB, ("pre", "g16"))
        tres: dict[str, Any] = {"n_points": int(len(lab)), "class_sizes": dict(Counter(lab.tolist())), "grid": []}
        sweep = {(s["layer"], s["position"], s["k"]): s for s in man["tasks"][t]["sweep"]}
        Gs = {}
        for (l, q), Y in data.items():
            ok = ~np.isnan(Y).any(axis=1)
            mu, V = pca_fit(Y[ok])
            Z = (Y[ok] - mu) @ V.T
            for k in K_SWEEP:
                G, info = knn_geodesic(Z, k)
                D = centroid_matrix(G, lab[ok], algs)
                S = separability(D)
                st_s = sweep.get((l, q, k), {})
                nn = {a: algs[int(np.argsort(np.where(np.eye(len(algs), dtype=bool)[i], np.inf, D[i]))[0])]
                      for i, a in enumerate(algs)}
                rec = {"layer": l, "position": q, "k": k, "bridges": info["bridges"],
                       "stress1": st_s.get("stress1") if st_s else stress1(D),
                       "stress1_source": "exp9 sweep" if st_s else "recomputed",
                       "nearest": nn, "nearest_exp9_sweep": st_s.get("nearest"),
                       "nearest_matches_exp9": (st_s.get("nearest") == nn) if st_s else None, "D": D.tolist(),
                       "separability": S.tolist()}
                if t == "t1":
                    ib, jb = algs.index("bfs"), algs.index("bibfs")
                    order = [algs[x] for x in np.argsort(D[ib]) if x != ib]
                    rec["bfs_bibfs"] = {"distance": float(D[ib, jb]), "rank_among_bfs_neighbours": order.index("bibfs") + 1,
                                        "separability": float(S[ib, jb]), "within_bfs": float(D[ib, ib]),
                                        "within_bibfs": float(D[jb, jb])}
                tres["grid"].append(rec)
                if k == 10:
                    Gs[(l, q)] = (G, lab[ok], Z)
        # re-derivation check of exp9's stored primary_centroid_D at (24, pre, 10)
        Dp = next(r["D"] for r in tres["grid"] if r["layer"] == 24 and r["position"] == "pre" and r["k"] == 10)
        tres["rederive_primary_D_max_abs_diff"] = float(np.max(np.abs(np.array(Dp) - np.array(man["tasks"][t]["primary_centroid_D"]))))
        # nulls at (24, g16, 10) and (24, pre, 10)
        nulls = {}
        for q in ("g16", "pre"):
            G, labs, Z = Gs[(24, q)]
            D0 = centroid_matrix(G, labs, algs)
            nn0 = {a: algs[int(np.argsort(np.where(np.eye(len(algs), dtype=bool)[i], np.inf, D0[i]))[0])]
                   for i, a in enumerate(algs)}
            same = Counter()
            h1_perm = []
            for _ in range(n_perm):
                lp = rng.permutation(labs)
                Dpm = centroid_matrix(G, lp, algs)
                for i, a in enumerate(algs):
                    nnp = algs[int(np.argsort(np.where(np.eye(len(algs), dtype=bool)[i], np.inf, Dpm[i]))[0])]
                    same[a] += nnp == nn0[a]
                Dz = Dpm.copy()
                np.fill_diagonal(Dz, 0.0)
                h1_perm.append(_h1(Dz, distance_matrix=True)[0])
            D0z = D0.copy()
            np.fill_diagonal(D0z, 0.0)
            h1_obs = _h1(D0z, distance_matrix=True)
            nq = {"nearest": nn0, "N1_p_same_nearest": {a: (same[a] + 1) / (n_perm + 1) for a in algs},
                  "centroid_H1": {"max_lifetime": h1_obs[0], "ratio_to_second": h1_obs[1],
                                  "N1_null_mean": float(np.mean(h1_perm)),
                                  "N1_p": float((np.sum(np.array(h1_perm) >= h1_obs[0]) + 1) / (n_perm + 1))}}
            if t == "t1":
                ib, jb = algs.index("bfs"), algs.index("bibfs")
                pool = np.where((labs == "bfs") | (labs == "bibfs"))[0]
                obs_sep = separability(D0)[ib, jb]
                cnt = 0
                for _ in range(n_perm):
                    lp = labs.copy()
                    lp[pool] = rng.permutation(labs[pool])
                    Dx = centroid_matrix(G, lp, algs)
                    cnt += separability(Dx)[ib, jb] >= obs_sep
                nq["N2_bfs_bibfs"] = {"observed_separability": float(obs_sep), "p": (cnt + 1) / (n_perm + 1),
                                      "separable": bool((cnt + 1) / (n_perm + 1) < 0.05)}
                nq["bfs_bibfs_nearest_pair"] = bool(nn0["bfs"] == "bibfs" or nn0["bibfs"] == "bfs")
            nulls[q] = nq
        tres["nulls_layer24_k10"] = nulls
        # per-sample persistent H1: label-stratified subsample n=300 on 20 PCs vs Gaussian-matched null (N3)
        ph = {}
        for l in LAYERS_SUB:
            for q in ("g16", "pre"):
                Y = data[(l, q)]
                ok = ~np.isnan(Y).any(axis=1)
                labs = lab[ok]
                mu, V = pca_fit(Y[ok], 20)
                Z = (Y[ok] - mu) @ V.T
                n = min(300, len(Z))
                sel = []
                for a in algs:
                    ids = np.where(labs == a)[0]
                    m = int(round(n * len(ids) / len(labs)))
                    sel += list(rng.choice(ids, size=min(len(ids), max(1, m)), replace=False))
                P = Z[np.array(sel)]
                life, ratio = _h1(P)
                cov = np.cov(P.T)
                jobs = [(np.zeros(P.shape[1]), cov, len(P), n_null // CHUNKS + 1, SEED + 100 * l + i)
                        for i in range(CHUNKS)]
                null = np.array(_par(_gauss_null_worker, jobs, workers))[:n_null]
                ph[f"L{l}|{q}"] = {"n": int(len(P)), "max_lifetime": life, "ratio_to_second": ratio,
                                   "N3_null_mean": float(null.mean()), "N3_q95": float(np.quantile(null, 0.95)),
                                   "p": float((np.sum(null >= life) + 1) / (len(null) + 1)), "n_null": int(len(null))}
                if l == 24:
                    # power: planted K-gon at the observed median neighbour distance vs a line control
                    cents = np.array([P[np.array([labs[s] == a for s in sel])].mean(0) for a in algs])
                    from scipy.spatial.distance import cdist

                    Dc = cdist(cents, cents)
                    np.fill_diagonal(Dc, np.inf)
                    nn_d = float(np.median(Dc.min(axis=1)))
                    K = len(algs)
                    radius = nn_d / (2 * math.sin(math.pi / K))
                    resid = np.concatenate([P[np.array([labs[s] == a for s in sel])] - cents[i] for i, a in enumerate(algs)])
                    cov_w = np.cov(resid.T)
                    sizes = [int(np.sum(np.array([labs[s] == a for s in sel]))) for a in algs]
                    pw = {}
                    for shape, rad in (("loop", radius), ("line", nn_d), ("loop_radius0", 0.0)):
                        jobs = [(sizes, cov_w, rad, "loop" if shape.startswith("loop") else "line",
                                 n_power // CHUNKS + 1, SEED + 7 * i + len(shape)) for i in range(CHUNKS)]
                        lifes = np.array(_par(_planted_worker, jobs, workers))[:n_power]
                        # null for the synthetic clouds: Gaussian matched to a planted cloud's covariance
                        pw[shape] = lifes
                    # matched Gaussian null for the planted design (one reference cloud per shape)
                    rr = np.random.default_rng(SEED + 99)
                    ref = {}
                    for shape, rad in (("loop", radius), ("line", nn_d), ("loop_radius0", 0.0)):
                        Kc = np.zeros((K, P.shape[1]))
                        if shape.startswith("loop"):
                            ang = 2 * np.pi * np.arange(K) / K
                            Kc[:, 0], Kc[:, 1] = rad * np.cos(ang), rad * np.sin(ang)
                        else:
                            Kc[:, 0] = rad * (np.arange(K) - (K - 1) / 2)
                        Pc = np.concatenate([rr.multivariate_normal(Kc[i], cov_w, size=s) for i, s in enumerate(sizes)])
                        jobs = [(np.zeros(P.shape[1]), np.cov(Pc.T), len(Pc), n_null // CHUNKS + 1, SEED + 300 + i)
                                for i in range(CHUNKS)]
                        ref[shape] = float(np.quantile(np.array(_par(_gauss_null_worker, jobs, workers))[:n_null], 0.95))
                    power = {s: float(np.mean(pw[s] > ref[s])) for s in pw}
                    ph[f"L{l}|{q}"]["power"] = {"planted_loop_power": power["loop"], "line_control_rate": power["line"],
                                                "radius0_placebo_rate": power["loop_radius0"], "radius": radius,
                                                "median_neighbour_distance": nn_d, "n_runs": n_power,
                                                "null_q95": ref, "sizes": sizes}
                    P_obs = ph[f"L{l}|{q}"]
                    pwr = power["loop"]
                    P_obs["wording"] = (f"no loop (power {pwr:.2f})" if (pwr >= 0.8 and P_obs["p"] >= 0.05) else
                                        (f"loop detected (p={P_obs['p']:.3f}, power {pwr:.2f})" if P_obs["p"] < 0.05 else
                                         f"no evidence of a loop, at weak power ({pwr:.2f}), at {q}"))
        tres["persistence"] = ph
        tres["exp9_persistence_quoted"] = pers.get(t)
        res["tasks"][t] = tres
        del data, Gs
    # BFS-BiBFS verdict at g16
    g = res["tasks"]["t1"]["nulls_layer24_k10"]["g16"]
    surv = bool(g["bfs_bibfs_nearest_pair"] and g["N1_p_same_nearest"]["bfs"] < 0.05 and g["N2_bfs_bibfs"]["separable"])
    res["bfs_bibfs_verdict_g16"] = {"survives": surv, "nearest_pair": g["bfs_bibfs_nearest_pair"],
                                    "N1_p_bfs": g["N1_p_same_nearest"]["bfs"], "N2_p": g["N2_bfs_bibfs"]["p"],
                                    "N2_separable": g["N2_bfs_bibfs"]["separable"]}
    res["sources"] = [src("exp9", "states/<task>/base/part_*.npz"), src("exp9", "results/manifold.json"),
                      src("exp9", "results/persistence.json"), src("exp9", "analysis/manifold.py"),
                      src("exp9", "mb/sets.py"), src("exp9", "data/samples.jsonl")]
    global _POOL
    if _POOL is not None:
        _POOL.shutdown(wait=True)
        _POOL = None
    write_json(RESULTS / "manifold.json", res)
    grid_rows = []
    for t in ("t1", "t2"):
        for r in res["tasks"][t]["grid"]:
            grid_rows.append({"task": t, "layer": r["layer"], "position": r["position"], "k": r["k"],
                              "stress1": r["stress1"], "bridges": r["bridges"], "nearest": json.dumps(r["nearest"]),
                              "nearest_matches_exp9": r["nearest_matches_exp9"],
                              **({f"bfs_bibfs_{k}": v for k, v in r.get("bfs_bibfs", {}).items()})})
    pd.DataFrame(grid_rows).to_csv(TABLES / "manifold_grid.csv", index=False)
    logger.info(f"manifold done; BFS-BiBFS survives at g16: {surv}")
    return res
