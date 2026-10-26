#!/usr/bin/env python3
"""Geometry of the plan states at the causal site (blocks 18 and 23), descriptive.

Points: 30 named + 30 masked S-mean states per algorithm, PCA to 50 dims fit on these points. kNN graph (k in
{5, 10, 15}), geodesic distances; Isomap 2-D (classical MDS on geodesics, with sklearn's out-of-sample transform)
and metric MDS (SMACOF) on the geodesic matrix with Kruskal stress-1 and trustworthiness (k = 10).
Out-of-sample: twins (W1-W5), modal bans (not R2), population pushed states (twin S-mean + realised displacement,
coloured by the arm's modal off-default landing) and targeted C2c arms at each dose (when states/disp_c2c exist).
Centroid implemented counts under twin / iteration-3 ban (exp13 landing) / push population / targeted 1 x b_t.
The geodesic path default -> runner-up (between the points nearest the two centroids) is returned.
Persistent H1 (ripser on the geodesic matrix, k = 10) vs a coordinate-permutation null (each PCA coordinate permuted
independently, N_NULL draws) and a planted-circle power check at matched n and noise.
"""

from __future__ import annotations

import time
from collections import Counter
from typing import Any

import numpy as np
from scipy.sparse.csgraph import shortest_path
from sklearn.decomposition import PCA
from sklearn.manifold import MDS, Isomap, trustworthiness
from sklearn.neighbors import kneighbors_graph

from cfg4 import DEFAULT4, E13, GEO_BLOCKS, MOVABLE, STATES_DIR, TEMPLATE_IDS, read_jsonl
from common import share
from screen import catalogue
import npz_parts

N_NULL = 200


def geodesic(X: np.ndarray, k: int) -> np.ndarray:
    G = kneighbors_graph(X, k, mode="distance")
    G = G.maximum(G.T)
    D = shortest_path(G, directed=False)
    if np.isinf(D).any():
        fin = D[np.isfinite(D)].max()
        D[np.isinf(D)] = 2 * fin
    return D


def h1_max(D: np.ndarray) -> float:
    from ripser import ripser
    dg = ripser(D, maxdim=1, distance_matrix=True)["dgms"][1]
    return float(np.max(dg[:, 1] - dg[:, 0])) if len(dg) else 0.0


def stress1(D: np.ndarray, Y: np.ndarray) -> float:
    from scipy.spatial.distance import pdist, squareform
    d = squareform(pdist(Y))
    iu = np.triu_indices_from(D, 1)
    return float(np.sqrt(np.sum((D[iu] - d[iu]) ** 2) / np.sum(D[iu] ** 2)))


def persistence_test(X: np.ndarray, k: int = 10, n_null: int | None = None, seed: int = 0) -> dict[str, Any]:
    n_null = n_null or N_NULL
    rng = np.random.default_rng(seed)
    obs = h1_max(geodesic(X, k))
    null = []
    for _ in range(n_null):
        Y = X.copy()
        for j in range(Y.shape[1]):
            Y[:, j] = rng.permutation(Y[:, j])
        null.append(h1_max(geodesic(Y, k)))
    # planted circle at matched n and noise: a circle of the data's top-2 PC scale + residual-scale noise
    n, dd = X.shape
    sd = X.std(0)
    th = rng.uniform(0, 2 * np.pi, n)
    C = np.zeros_like(X)
    C[:, 0] = np.cos(th) * 2 * sd[0]
    C[:, 1] = np.sin(th) * 2 * sd[0]
    C += rng.standard_normal(X.shape) * sd[None, :] * 0.5
    obs_c = h1_max(geodesic(C, k))
    null_c = []
    for _ in range(max(20, n_null // 5)):
        Y = C.copy()
        for j in range(Y.shape[1]):
            Y[:, j] = rng.permutation(Y[:, j])
        null_c.append(h1_max(geodesic(Y, k)))
    return {"h1_max": obs, "null_q95": float(np.quantile(null, 0.95)),
            "p": float((1 + sum(v >= obs for v in null)) / (1 + len(null))), "n_null": len(null),
            "planted_circle_h1": obs_c, "planted_null_q95": float(np.quantile(null_c, 0.95)),
            "planted_detected": bool(obs_c > np.quantile(null_c, 0.95))}


def run_task(t: str, prompts_meta: dict, esc: dict[str, Any], rows: list[dict[str, Any]], commit: dict[str, Any],
             do_persistence: bool = True) -> dict[str, Any]:
    z = npz_parts.load(STATES_DIR / f"states_{t}.npz")
    pids = [str(p) for p in z["pids"]]
    H = z["smean"][:]
    sub = np.load(STATES_DIR / f"subspace_{t}.npz")
    blocks = [int(b) for b in sub["blocks"]]
    meta = [prompts_meta[p] for p in pids]
    d = DEFAULT4[t]
    cat = catalogue(t)
    ru = commit["tasks"][t]["runner_up"]["runner_up"]
    out: dict[str, Any] = {"runner_up": ru}
    idx = [i for i, m in enumerate(meta) if m["kind"] in ("named", "masked")]
    labs = [meta[i]["X"] for i in idx]
    kinds = [meta[i]["kind"] for i in idx]
    tw = {m["template_id"]: i for i, m in enumerate(meta) if m["kind"] == "twin"}
    bans = [i for i, m in enumerate(meta) if m["kind"] == "ban"]
    _d = npz_parts.load(STATES_DIR / f"disp_{t}.npz")
    disp = {"delta": _d["delta"], "keys": _d["keys"]}
    dkeys = [str(k) for k in disp["keys"]]
    dc = STATES_DIR / f"disp_c2c_{t}.npz"
    dcz = None
    if dc.exists():
        _c = np.load(dc)
        dcz = {"delta": _c["delta"], "keys": _c["keys"]}
    # population landing per arm
    pop_land = {}
    by_arm: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        if r["task"] == t:
            by_arm.setdefault(r["arm"], []).append(r)
    for arm, rr in by_arm.items():
        if arm.startswith("POP_"):
            off = Counter(r["label"] for r in rr if r["label"] in cat and r["label"] != d)
            sh = share(rr, set(cat), d)["share"]
            pop_land[arm] = off.most_common(1)[0][0] if off and sh >= 0.2 else d
    for l in GEO_BLOCKS:
        bi = blocks.index(l)
        X = H[idx, bi].astype(np.float32)
        pca = PCA(n_components=min(50, len(X) - 1), random_state=0).fit(X)
        X50 = pca.transform(X)
        res: dict[str, Any] = {"n_points": len(X), "pca_var_explained": float(pca.explained_variance_ratio_.sum())}
        for k in (5, 10, 15):
            D = geodesic(X50, k)
            iso = Isomap(n_neighbors=k, n_components=2).fit(X50)
            Y = iso.embedding_
            mds = MDS(n_components=2, dissimilarity="precomputed", random_state=0, n_init=1, max_iter=200,
                      normalized_stress="auto")
            Ym = mds.fit_transform(D)
            res[f"k{k}"] = {"isomap_stress1": stress1(D, Y), "mds_stress1": stress1(D, Ym),
                            "isomap_trustworthiness": float(trustworthiness(X50, Y, n_neighbors=10)),
                            "mds_trustworthiness": float(trustworthiness(X50, Ym, n_neighbors=10))}
            if k == 10:
                emb = {"points": Y.tolist(), "labels": labs, "kinds": kinds}
                cents = {X_: Y[[i for i, lb in enumerate(labs) if lb == X_]].mean(0).tolist() for X_ in set(labs)}
                emb["centroids"] = cents
                # geodesic path default -> runner-up
                G = kneighbors_graph(X50, k, mode="distance")
                G = G.maximum(G.T)
                cd = X50[[i for i, lb in enumerate(labs) if lb == d]].mean(0)
                cr = X50[[i for i, lb in enumerate(labs) if lb == ru]].mean(0)
                a0 = int(np.argmin(((X50 - cd) ** 2).sum(1)))
                b0 = int(np.argmin(((X50 - cr) ** 2).sum(1)))
                Dm, pred = shortest_path(G, directed=False, indices=a0, return_predecessors=True)
                path, cur = [], b0
                while cur >= 0 and cur != a0 and len(path) < 500:
                    path.append(cur)
                    cur = pred[cur]
                path.append(a0)
                emb["geodesic_path"] = [Y[i].tolist() for i in path[::-1]]
                emb["geodesic_len"] = float(Dm[b0]) if np.isfinite(Dm[b0]) else None
                # out-of-sample projections
                oos: dict[str, Any] = {}
                tw_states = {w: H[i, bi].astype(np.float32) for w, i in tw.items()}
                oos["twin"] = iso.transform(pca.transform(np.stack(list(tw_states.values())))).tolist()
                if bans:
                    oos["ban"] = iso.transform(pca.transform(H[bans, bi].astype(np.float32))).tolist()
                pts, plab = [], []
                for j, key in enumerate(dkeys):
                    fam, s, a, w = key.split("|")
                    if fam != "POP":
                        continue
                    pts.append(tw_states[w] + disp["delta"][j][bi].astype(np.float32))
                    plab.append(pop_land.get(f"POP_d{s}_a{a}", "unsampled"))
                if pts:
                    oos["population"] = {"points": iso.transform(pca.transform(np.stack(pts))).tolist(), "landing": plab}
                if dcz is not None:
                    tg = {}
                    for j, key in enumerate([str(x) for x in dcz["keys"]]):
                        arm, w = key.split("|")
                        tg.setdefault(arm, []).append(tw_states[w] + dcz["delta"][j][bi].astype(np.float32))
                    oos["targeted"] = {arm: iso.transform(pca.transform(np.stack(v))).tolist() for arm, v in tg.items()}
                emb["oos"] = oos
                res["embedding_k10"] = emb
                if do_persistence:
                    t0 = time.time()
                    res["persistence"] = persistence_test(X50, k=10)
                    res["persistence"]["seconds"] = time.time() - t0
        out[str(l)] = res
    # implemented counts per centroid: twin / iteration-3 ban / push population / targeted 1 x b_t
    counts = {"twin": Counter(r["label"] for r in by_arm.get("TWIN", [])),
              "push_population": Counter(r["label"] for a, rr in by_arm.items() if a.startswith("POP_") for r in rr),
              "targeted_1xbt": Counter(r["label"] for r in by_arm.get("C2C_r_s0.5", []))}
    ev = [e for e in read_jsonl(E13 / "results" / "c1_events.jsonl") if e["task"] == t]
    counts["iter3_ban"] = Counter(ev[0]["landing_counts"]) if ev else Counter()
    out["implemented_counts"] = {k: dict(v) for k, v in counts.items()}
    return out


def run(rows: list[dict[str, Any]], commit: dict[str, Any], esc: dict[str, Any]) -> dict[str, Any]:
    from prompts4 import load_prompts4
    pm = load_prompts4()
    out = {"n_null": N_NULL, "tasks": {}}
    for t in MOVABLE:
        t0 = time.time()
        out["tasks"][t] = run_task(t, pm, esc, rows, commit)
        out["tasks"][t]["seconds"] = time.time() - t0
    return out
