#!/usr/bin/env python3
"""S6 SET SELECTION: TOP-5 from FRLP, ARC-5 / SCATTER-5 from the consensus geodesic matrix of algorithm centroids.

Geometry per (layer, position) in context 'base' (positions g16 and pre, layers 20-28): centre, PCA-50 on all T1
forced points, symmetric k-NN graph (k=10, Euclidean weights; disconnected components bridged by their shortest
Euclidean edge, logged), Dijkstra geodesics, D[a,b] = median geodesic over point pairs of a and b, normalised by its
median off-diagonal. Consensus Dbar = elementwise median over the 18 settings. Seriation = exact Held-Karp shortest
Hamiltonian path on Dbar.
"""

from __future__ import annotations

import itertools
import json
import math
from typing import Any

import numpy as np
from loguru import logger

from common import (CATALOGUE, LAYERS, RESULTS_DIR, read_json, read_jsonl, write_json)

POS_INDEX = {"g8": 0, "g16": 1, "g32": 2, "pre": 3}
PRIMARY_POS = ("g16", "pre")
K_SWEEP = (5, 10, 15, 20)


def pca(X: np.ndarray, n: int = 50) -> np.ndarray:
    Xc = X - X.mean(axis=0, keepdims=True)
    U, S, Vt = np.linalg.svd(Xc, full_matrices=False)
    n = min(n, Vt.shape[0])
    return Xc @ Vt[:n].T


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
    info["connected_without_bridges"] = info["bridges"] == 0
    G = shortest_path(csr_matrix(W), method="D", directed=False)
    return G, info


def centroid_matrix(G: np.ndarray, labels: np.ndarray, algs: list[str],
                    sel: dict[str, np.ndarray] | None = None) -> np.ndarray:
    K = len(algs)
    D = np.zeros((K, K))
    ids = {a: (sel[a] if sel is not None else np.where(labels == a)[0]) for a in algs}
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


def held_karp_path(D: np.ndarray) -> tuple[list[int], float]:
    """Exact shortest Hamiltonian path (free endpoints) by Held-Karp DP."""
    K = D.shape[0]
    INF = float("inf")
    dp = np.full((1 << K, K), INF)
    par = np.full((1 << K, K), -1, dtype=int)
    for i in range(K):
        dp[1 << i, i] = 0.0
    for mask in range(1 << K):
        for last in range(K):
            v = dp[mask, last]
            if v == INF or not (mask >> last) & 1:
                continue
            for nxt in range(K):
                if (mask >> nxt) & 1:
                    continue
                m2 = mask | (1 << nxt)
                c = v + D[last, nxt]
                if c < dp[m2, nxt]:
                    dp[m2, nxt] = c
                    par[m2, nxt] = last
    full = (1 << K) - 1
    last = int(np.argmin(dp[full]))
    cost = float(dp[full, last])
    path, mask = [], full
    while last != -1:
        path.append(last)
        p = par[mask, last]
        mask ^= 1 << last
        last = int(p)
    return path[::-1], cost


def brute_force_path(D: np.ndarray) -> float:
    K = D.shape[0]
    return min(sum(D[p[i], p[i + 1]] for i in range(K - 1)) for p in itertools.permutations(range(K)))


def pair_sum(D: np.ndarray, S: list[int]) -> float:
    return float(sum(D[a, b] for a, b in itertools.combinations(S, 2)))


def pair_min(D: np.ndarray, S: list[int]) -> float:
    return float(min(D[a, b] for a, b in itertools.combinations(S, 2)))


def select_sets(D: np.ndarray, algs: list[str], top: list[str], size: int) -> dict[str, Any]:
    path, cost = held_karp_path(D)
    K = len(algs)
    top_idx = sorted(algs.index(a) for a in top)
    wins = []
    for s in range(0, K - size + 1):
        w = sorted(path[s:s + size])
        if w == top_idx:
            continue
        wins.append((pair_sum(D, w), s, w))
    arc = min(wins)[2] if wins else None
    scat = None
    best = None
    for S in itertools.combinations(range(K), size):
        S = sorted(S)
        if S == top_idx or (arc is not None and S == arc):
            continue
        key = (pair_min(D, S), pair_sum(D, S))
        if best is None or key > best:
            best, scat = key, S
    return {"path": [algs[i] for i in path], "path_cost": cost,
            "ARC": [algs[i] for i in arc] if arc is not None else None,
            "SCATTER": [algs[i] for i in scat] if scat is not None else None}


def edge_opposite(D: np.ndarray, algs: list[str], banned: list[str]) -> dict[str, Any]:
    bi = [algs.index(b) for b in banned]
    surv = [a for a in algs if a not in banned]
    dmin = {a: float(min(D[algs.index(a), j] for j in bi)) for a in surv}
    dmean = {a: float(np.mean([D[algs.index(a), j] for j in bi])) for a in surv}
    order = sorted(surv, key=lambda a: (dmin[a], dmean[a], a))
    n2 = 1 if len(surv) == 2 else min(2, len(surv))
    return {"survivors": surv, "d_min": dmin, "d_mean": dmean, "EDGE": order[:n2], "OPPOSITE": order[::-1][:n2],
            "order_near_to_far": order}


def load_points(task: str, context: str, algs: list[str]) -> tuple[np.ndarray, np.ndarray, list[dict[str, Any]]]:
    from mb.score import load_states

    st = load_states(task, context)
    keep = [i for i, m in enumerate(st["meta"]) if m.get("kind") == "forced" and m.get("algorithm") in algs]
    X = st["X"][keep].astype(np.float32)
    labels = np.array([st["meta"][i]["algorithm"] for i in keep])
    return X, labels, [st["meta"][i] for i in keep]


def geometry(task: str, context: str, algs: list[str], k: int = 10, positions=PRIMARY_POS,
             layers=None) -> dict[str, Any]:
    X, labels, meta = load_points(task, context, algs)
    layers = layers or LAYERS
    mats, infos, settings, Gs = [], [], [], {}
    for li, l in enumerate(LAYERS):
        if l not in layers:
            continue
        for pos in positions:
            Y = X[:, li, POS_INDEX[pos], :]
            ok = ~np.isnan(Y).any(axis=1)
            Z = pca(Y[ok])
            G, info = knn_geodesic(Z, k)
            Dm = centroid_matrix(G, labels[ok], algs)
            mats.append(Dm)
            infos.append({"layer": l, "position": pos, **info, "n_points": int(ok.sum())})
            settings.append((l, pos))
            Gs[(l, pos)] = (G, labels[ok])
    Dbar = np.median(np.stack(mats), axis=0)
    return {"Dbar": Dbar, "mats": mats, "settings": settings, "infos": infos, "Gs": Gs, "labels": labels}


def frlp_base(task: str) -> dict[str, dict[str, float]]:
    rows = [r for r in read_jsonl(RESULTS_DIR / "frlp_cells.jsonl") if r["task"] == task and r["condition"] == "base"
            and r["half"] == "all" and "variant" not in r]
    return {r["algorithm"]: r for r in rows}


def corrected_L(task: str, L: dict[str, float]) -> dict[str, float]:
    """L_j + log(as-requested share of F_j): removes the P(j | F_j) < 1 bias in cross-algorithm comparisons."""
    keep = read_json(RESULTS_DIR / "catalogue_keep.json")["tasks"][task]
    return {a: L[a] + math.log(max(keep[a]["share"], 1e-9)) for a in L}


def stage_select() -> None:
    from mb.prompts import load_frozen, multi_ban_conditions

    keep = read_json(RESULTS_DIR / "catalogue_keep.json")
    algs = [a for a in keep["analysis_catalogue_final"]["t1"]]
    fb = frlp_base("t1")
    algs = [a for a in algs if a in fb]
    K = len(algs)
    L_raw = {a: fb[a]["L"] for a in algs}
    L_cor = corrected_L("t1", L_raw)
    size = 5 if K >= 8 else (4 if K == 7 else 5)
    top = sorted(algs, key=lambda a: -L_cor[a])[:size]
    geo = geometry("t1", "base", algs)
    Dbar = geo["Dbar"]
    sel = select_sets(Dbar, algs, top, size) if K > size else {"path": algs, "ARC": None, "SCATTER": None}
    sets = {"TOP": top}
    if sel.get("ARC"):
        sets["ARC"] = sel["ARC"]
    if sel.get("SCATTER"):
        sets["SCATTER"] = sel["SCATTER"]
    if size == 4 and K >= 7:
        # the literal request: the model's top FIVE in one prompt (added beside F4's TOP-4 / ARC-4 / SCATTER-4)
        sets["TOP5"] = sorted(algs, key=lambda a: -L_cor[a])[:5]
        from common import deviation

        deviation("D-top5-literal", "With K = 7 the plan's F4 runs TOP-4, ARC-4 and SCATTER-4 (3 survivors each); the "
                                    "literal five-name ban TOP5 (top five by corrected FRLP, 2 survivors) is added as a "
                                    "fourth sampled condition with the same templates, twins and committed forecasts.")
    med = float(np.median(Dbar[~np.eye(K, dtype=bool)]))
    eo = {s: edge_opposite(Dbar, algs, b) for s, b in sets.items()}
    # stability: every single (layer, position, k) setting and 200 program-bootstrap resamples
    stab = {"per_setting": [], "bootstrap": {}}
    X, labels, _ = load_points("t1", "base", algs)
    for k in K_SWEEP:
        gk = geometry("t1", "base", algs, k=k) if k != 10 else geo
        for (l, pos), Dm in zip(gk["settings"], gk["mats"]):
            s2 = select_sets(Dm, algs, top, size) if K > size else {}
            stab["per_setting"].append({"k": k, "layer": l, "position": pos, "ARC": s2.get("ARC"),
                                        "SCATTER": s2.get("SCATTER"),
                                        "EDGE": {s: edge_opposite(Dm, algs, b)["EDGE"] for s, b in sets.items()},
                                        "OPPOSITE": {s: edge_opposite(Dm, algs, b)["OPPOSITE"] for s, b in sets.items()}})
    rng = np.random.default_rng(0)
    agree = {s: {"EDGE": 0, "OPPOSITE": 0} for s in sets}
    arc_same = scat_same = 0
    for _ in range(200):
        mats = []
        for (l, pos), (G, lab) in geo["Gs"].items():
            selidx = {a: rng.choice(np.where(lab == a)[0], size=(lab == a).sum(), replace=True) for a in algs}
            mats.append(centroid_matrix(G, lab, algs, selidx))
        Db = np.median(np.stack(mats), axis=0)
        if K > size:
            s2 = select_sets(Db, algs, top, size)
            arc_same += int(s2["ARC"] is not None and sets.get("ARC") is not None and sorted(s2["ARC"]) == sorted(sets["ARC"]))
            scat_same += int(s2["SCATTER"] is not None and sets.get("SCATTER") is not None
                             and sorted(s2["SCATTER"]) == sorted(sets["SCATTER"]))
        for s, b in sets.items():
            e2 = edge_opposite(Db, algs, b)
            agree[s]["EDGE"] += int(e2["EDGE"] == eo[s]["EDGE"])
            agree[s]["OPPOSITE"] += int(e2["OPPOSITE"] == eo[s]["OPPOSITE"])
    stab["bootstrap"] = {"n": 200, "ARC_same": arc_same / 200, "SCATTER_same": scat_same / 200,
                         "EDGE_OPPOSITE_same": {s: {k2: v / 200 for k2, v in d.items()} for s, d in agree.items()}}
    # context sensitivity: 'forced' context and R of the forced prompts
    ctx = {}
    try:
        gf = geometry("t1", "forced", algs)
        sf = select_sets(gf["Dbar"], algs, top, size) if K > size else {}
        ctx["forced"] = {"Dbar": gf["Dbar"], "ARC": sf.get("ARC"), "SCATTER": sf.get("SCATTER"),
                         "EDGE": {s: edge_opposite(gf["Dbar"], algs, b)["EDGE"] for s, b in sets.items()}}
    except (ValueError, IndexError) as e:
        ctx["forced"] = {"error": str(e)}
    try:
        ctx["R_forced_prompts"] = r_geometry(algs, top, size, sets)
    except (ValueError, IndexError, KeyError) as e:
        ctx["R_forced_prompts"] = {"error": str(e)}

    def jac(a, b):
        if not a or not b:
            return None
        return len(set(a) & set(b)) / len(set(a) | set(b))

    for c in ctx.values():
        if "error" in c:
            continue
        c["jaccard"] = {"ARC": jac(c.get("ARC"), sets.get("ARC")), "SCATTER": jac(c.get("SCATTER"), sets.get("SCATTER"))}
        c["EDGE_same"] = {s: c["EDGE"].get(s) == eo[s]["EDGE"] for s in sets}
    # seriation check vs brute force on K = 7 (or K)
    kk = min(7, K)
    hk = held_karp_path(Dbar[:kk, :kk])[1]
    bf = brute_force_path(Dbar[:kk, :kk])
    out = {"task": "t1", "algorithms": algs, "K": K, "set_size": size, "L_base_raw": L_raw, "L_base_corrected": L_cor,
           "sets": sets, "seriation_path": sel.get("path"), "Dbar": Dbar, "median_offdiag": med,
           "edge_opposite": eo, "settings": [{"layer": l, "position": p} for l, p in geo["settings"]],
           "graph_info": geo["infos"], "stability": stab, "context_sensitivity": ctx,
           "held_karp_vs_bruteforce": {"K": kk, "held_karp": hk, "brute_force": bf, "match": abs(hk - bf) < 1e-9}}
    write_json(RESULTS_DIR / "sets_and_geometry.json", out)
    # planned conditions (frozen rule) for score1b and session 2
    fz = load_frozen()
    plan = {"t1": {}}
    for s, b in sets.items():
        plan["t1"][s] = {"banned": b, "survivors": [a for a in algs if a not in b],
                         "templates": multi_ban_conditions("t1", s, b, fz["neutral_nouns"]["t1"])}
    write_json(RESULTS_DIR / "planned_conditions.json", plan)
    logger.info(f"K={K} algorithms {algs}; L_cor {json.dumps({a: round(v, 2) for a, v in L_cor.items()})}")
    logger.info(f"sets: {sets}; path {sel.get('path')}")
    for s in sets:
        logger.info(f"  {s}: survivors {eo[s]['survivors']} EDGE {eo[s]['EDGE']} OPPOSITE {eo[s]['OPPOSITE']}")


def r_geometry(algs: list[str], top: list[str], size: int, sets: dict[str, list[str]]) -> dict[str, Any]:
    from mb.score import load_states

    st = load_states("t1", "forced")
    keys = [k for k in st["R"] if k.startswith("t1|forced:")]
    lab = np.array([k.split("|")[1].split(":")[1] for k in keys])
    keep = [i for i, a in enumerate(lab) if a in algs]
    R = np.stack([st["R"][keys[i]] for i in keep]).astype(np.float32)
    lab = lab[keep]
    mats = []
    for li, _l in enumerate(LAYERS):
        Z = pca(R[:, li, :], n=min(50, len(lab) - 1))
        G, _ = knn_geodesic(Z, k=5)
        mats.append(centroid_matrix(G, lab, algs))
    D = np.median(np.stack(mats), axis=0)
    s = select_sets(D, algs, top, size) if len(algs) > size else {}
    return {"Dbar": D, "ARC": s.get("ARC"), "SCATTER": s.get("SCATTER"),
            "EDGE": {k: edge_opposite(D, algs, b)["EDGE"] for k, b in sets.items()}, "k": 5,
            "note": "R = last prompt token of the 10 forced prompts per algorithm (carries the name)"}


__all__ = ["stage_select", "geometry", "pca", "knn_geodesic", "centroid_matrix", "held_karp_path", "edge_opposite",
           "CATALOGUE"]
