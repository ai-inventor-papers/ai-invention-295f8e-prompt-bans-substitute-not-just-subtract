#!/usr/bin/env python3
"""9.6 5c (descriptive): geometry of early-generation states across arms.

Per task, at (mean of generated positions 1-3) and k=16, at block L* (C2e best block, else 20) and block 23
(= exp9's 'layer 24' in the hidden_states convention): per-sample points of every arm; k-NN graphs (k = 5, 10, 15) on
PCA-50 coordinates with geodesic (shortest-path) distances and connected components; per-(arm, label) centroids sized
by count; 2-D metric MDS of the centroid geodesic distances with Kruskal stress-1; persistent H1 (ripser, n <= 300,
PCA-20) against within-dimension coordinate permutations (max lifetime, q95)."""

from __future__ import annotations

import json
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor
from typing import Any

import numpy as np
from scipy.sparse.csgraph import connected_components, shortest_path
from sklearn.decomposition import PCA
from sklearn.manifold import MDS
from sklearn.neighbors import kneighbors_graph

import states_io
from cfg import DATA_DIR, SAMPLED_TASKS, STATES_DIR, read_jsonl

N_PERM_H1 = 100
MAX_PTS_H1 = 300


def _h1_max(X: np.ndarray) -> float:
    from ripser import ripser

    dg = ripser(X, maxdim=1)["dgms"][1]
    if len(dg) == 0:
        return 0.0
    life = dg[:, 1] - dg[:, 0]
    life = life[np.isfinite(life)]
    return float(life.max()) if len(life) else 0.0


def h1_test(X: np.ndarray, seed: int) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    if len(X) > MAX_PTS_H1:
        X = X[rng.choice(len(X), MAX_PTS_H1, replace=False)]
    Z = PCA(20, random_state=0).fit_transform(X)
    obs = _h1_max(Z)
    null = []
    for _ in range(N_PERM_H1):
        Zp = np.stack([rng.permutation(Z[:, j]) for j in range(Z.shape[1])], 1)
        null.append(_h1_max(Zp))
    return {"h1_max_lifetime": obs, "null_q95": float(np.quantile(null, 0.95)), "n_points": int(len(Z)),
            "exceeds_null": bool(obs > np.quantile(null, 0.95)), "n_perm": N_PERM_H1}


def load_cloud(task: str, block: int, pos: str) -> tuple[np.ndarray, list[str], list[str]]:
    labs = {r["key"]: r["label"] for r in read_jsonl(DATA_DIR / "labels.jsonl")}
    pts, arms, lbl = [], [], []
    for arm in ("BAN", "NEUTRAL"):
        if not states_io.exists(STATES_DIR / f"{task}_{arm}"):
            continue
        X = states_io.load(STATES_DIR / f"{task}_{arm}")
        blocks = json.load(open(STATES_DIR / f"{task}_{arm}_meta.json"))["blocks"]
        bi = blocks.index(block)
        x = np.asarray(X[:, 2:5, bi]).astype(np.float32).mean(1) if pos == "k1-3" else np.asarray(X[:, 10, bi]).astype(np.float32)
        idx = [json.loads(l) for l in open(STATES_DIR / f"{task}_{arm}_index.jsonl")]
        pts.append(x)
        arms += [arm] * len(idx)
        lbl += [labs.get(r["key"], "?") for r in idx]
    for p in sorted(STATES_DIR.glob(f"5c_{task}_*.npy")):
        arm = p.stem[len(f"5c_{task}_"):]
        meta = json.load(open(STATES_DIR / f"5c_{task}_{arm}_meta.json"))
        if block not in meta["blocks"]:
            continue
        bi = meta["blocks"].index(block)
        X = np.load(p, mmap_mode="r")  # positions: R, k1..k8, k16
        x = np.asarray(X[:, 1:4, bi]).astype(np.float32).mean(1) if pos == "k1-3" else np.asarray(X[:, 9, bi]).astype(np.float32)
        idx = [json.loads(l) for l in open(STATES_DIR / f"5c_{task}_{arm}_index.jsonl")]
        pts.append(x)
        arms += [arm] * len(idx)
        lbl += [labs.get(r["key"], "?") for r in idx]
    return (np.concatenate(pts) if pts else np.zeros((0, 4096))), arms, lbl


def geometry(X: np.ndarray, arms: list[str], lbl: list[str]) -> dict[str, Any]:
    Z = PCA(min(50, len(X) - 1), random_state=0).fit_transform((X - X.mean(0)) / (X.std(0) + 1e-6))
    groups: dict[str, list[int]] = {}
    for i, (a, l) in enumerate(zip(arms, lbl)):
        groups.setdefault(f"{a}|{l}", []).append(i)
    groups = {k: v for k, v in groups.items() if len(v) >= 3}
    out: dict[str, Any] = {"n_points": int(len(X)), "groups": {k: len(v) for k, v in groups.items()}, "knn": {}}
    for k in (5, 10, 15):
        G = kneighbors_graph(Z, k, mode="distance", include_self=False)
        G = G.maximum(G.T)
        ncomp, comp = connected_components(G, directed=False)
        D = shortest_path(G, directed=False)
        names = sorted(groups)
        C = np.zeros((len(names), len(names)))
        for i, a in enumerate(names):
            for j, b in enumerate(names):
                sub = D[np.ix_(groups[a], groups[b])]
                fin = sub[np.isfinite(sub)]
                C[i, j] = float(fin.mean()) if fin.size else np.nan
        Cs = np.where(np.isfinite(C), C, np.nanmax(C[np.isfinite(C)]) * 1.5 if np.isfinite(C).any() else 0)
        Cs = 0.5 * (Cs + Cs.T)
        np.fill_diagonal(Cs, 0)
        rec: dict[str, Any] = {"n_components": int(ncomp), "centroid_names": names,
                               "centroid_geodesic": np.round(C, 3).tolist()}
        if len(names) >= 3:
            mds = MDS(2, dissimilarity="precomputed", random_state=0, normalized_stress=False, n_init=4)
            Y = mds.fit_transform(Cs)
            dY = np.linalg.norm(Y[:, None] - Y[None], axis=-1)
            iu = np.triu_indices(len(names), 1)
            rec["mds_xy"] = np.round(Y, 3).tolist()
            rec["kruskal_stress1"] = float(np.sqrt(((dY[iu] - Cs[iu]) ** 2).sum() / max((dY[iu] ** 2).sum(), 1e-12)))
        # nearest centroid (geodesic) to the named-ban default and the neutral default
        near = {}
        for a in names:
            i = names.index(a)
            row = [(C[i, j], names[j]) for j in range(len(names)) if j != i and np.isfinite(C[i, j])]
            near[a] = sorted(row)[:3]
        rec["nearest_centroids"] = {a: [[n, round(float(d), 3)] for d, n in v] for a, v in near.items()}
        out["knn"][k] = rec
    return out


def _cloud_job(args: tuple) -> tuple[str, dict[str, Any]]:
    task, block, pos, seed = args
    X, arms, lbl = load_cloud(task, block, pos)
    if len(X) < 20:
        return f"{task}|{block}|{pos}", {"status": "too few points"}
    g = geometry(X, arms, lbl)
    g["h1"] = h1_test(X, seed)
    return f"{task}|{block}|{pos}", g


def run_manifold(lstar: dict[str, int]) -> dict[str, Any]:
    jobs = []
    for i, t in enumerate(SAMPLED_TASKS):
        for b in sorted({lstar.get(t, 20), 23}):
            for pos in ("k1-3", "k16"):
                jobs.append((t, b, pos, 1000 + i))
    out: dict[str, Any] = {"descriptive": True, "L_star": lstar, "clouds": {}}
    with ProcessPoolExecutor(3, mp_context=mp.get_context("spawn")) as ex:
        for k, v in ex.map(_cloud_job, jobs):
            out["clouds"][k] = v
    return out
