#!/usr/bin/env python3
"""S-d geometry (CPU): implemented counts, banned sets, push directions, push progress, forced-prompt manifold.

- Implemented counts per algorithm = CORRECT programs carrying that label, pooled over (a) earlier Qwen3-8B twin rows
  of the same task (exp19 FP8, exp25 ECTWIN bf16, exp24 bf16, exp27 bf16), (b) base-model correct programs (exp24
  BASE_CHAT + BASE_PLAIN, Qwen3-8B-Base) and (c) plan-noise rows of iterations 4-5 (exp19 PN FP8, exp27 PN bf16);
  the engine column is kept per source. This artifact's own twin is sampled after commit #1, so it cannot enter the
  committed sets; results/banned_sets_check.json re-derives the sets with it added.
- Banned sets: T03 top-5 = the 5 most implemented of 6 (ties: base count, then alphabetical); T03 top-3 = the 3 most
  implemented; T10 = all but the least implemented of 4; T1 = exp9's literal TOP5 (bfs, dfs, gbfs, iddfs, astar).
- Push directions u[l] = normalise(mean survivor centroid - mean banned centroid), blocks 12-23, centroids of the
  bf16 NAMED forced prompts' S-mean states (exp20 recipe). T1 uses exp20's committed directions/u_top5.npz.
- Push progress t(alpha) = <s_push - s_twin, v> / <c_S - s_twin, v>, v = unit(c_S - c_B), in a PCA-50 space fit on
  the forced points (named + masked) at block 18 (and 23).
- Manifold: symmetrised k-NN graph (k in 5/10/15, Euclidean weights; the smallest connecting k is used if one is
  disconnected), geodesics by scipy shortest_path, 2-D metric MDS on the geodesic matrix with Kruskal stress-1,
  Isomap as a cross-check, and the edge-vs-opposite random-survivor test.
"""

from __future__ import annotations

import itertools
import math
from collections import Counter
from typing import Any

import numpy as np
from loguru import logger

from cfg import (CACHE_DIR, DIR_DIR, E19, E20, E24, E25, E27, PLAN_BLOCKS, PRED_DIR, RESULTS_DIR, TEMPLATE_IDS,
                 read_json, read_jsonl, sha256_file, write_json)

CATALOGUE = {
    "T03": ["full_sort", "size_k_heap", "heapify_pop", "quickselect", "median_of_medians", "counting_sort"],
    "T10": ["bfs", "dfs", "union_find", "label_propagation"],
    "T1": ["bfs", "dfs", "bibfs", "iddfs", "astar", "gbfs", "dijkstra_unit", "idastar", "jps", "biastar"],
}
T1_TOP5 = ["bfs", "dfs", "gbfs", "iddfs", "astar"]
T1_SURV7 = ["bibfs", "idastar"]
T1_SURV_EXT = ["bibfs", "idastar", "dijkstra_unit", "jps", "biastar"]
BI = {l: j for j, l in enumerate(PLAN_BLOCKS)}


def _task_of(r: dict[str, Any]) -> str | None:
    if r.get("task"):
        return r["task"]
    u = str(r.get("unit") or "")
    return u.split(":", 1)[1] if u.startswith("existing:") else None


def implemented_counts(task: str) -> dict[str, Any]:
    src: dict[str, Counter] = {}

    def add(name: str, rows: list[dict[str, Any]], arm_ok) -> None:
        c = Counter()
        for r in rows:
            if _task_of(r) != task or not arm_ok(r):
                continue
            if r.get("passed") is True and r.get("label") in CATALOGUE[task]:
                c[r["label"]] += 1
        src[name] = c

    e19 = read_jsonl(E19 / "data" / "samples.jsonl")
    e27 = read_jsonl(E27 / "data" / "labels.jsonl")
    e24 = read_jsonl(E24 / "data" / "samples.jsonl")
    e25 = read_jsonl(E25 / "data" / "samples.jsonl")
    add("twin_exp19_fp8", e19, lambda r: r["arm"] == "TWIN")
    add("twin_exp27_bf16", e27, lambda r: r["arm"] == "TWIN")
    add("twin_exp24_bf16", e24, lambda r: r["arm"] == "TWIN" and r.get("model") == "Qwen/Qwen3-8B")
    add("twin_exp25_bf16_ECTWIN", e25, lambda r: r["arm"] == "ECTWIN")
    add("base_exp24_bf16", e24, lambda r: r["arm"] in ("BASE_CHAT", "BASE_PLAIN"))
    add("plan_noise_exp19_fp8", e19, lambda r: str(r["arm"]).startswith("PN_a"))
    add("plan_noise_exp27_bf16", e27, lambda r: str(r["arm"]).startswith("PN_a"))
    pooled = Counter()
    for c in src.values():
        pooled.update(c)
    base = src["base_exp24_bf16"]
    return {"by_source": {k: dict(v) for k, v in src.items()},
            "pooled": {a: int(pooled.get(a, 0)) for a in CATALOGUE[task]},
            "base": {a: int(base.get(a, 0)) for a in CATALOGUE[task]}}


def rank_algorithms(task: str, counts: dict[str, Any]) -> list[str]:
    return sorted(CATALOGUE[task], key=lambda a: (-counts["pooled"][a], -counts["base"][a], a))


def build_banned_sets() -> dict[str, Any]:
    out = PRED_DIR / "banned_sets.json"
    if out.exists():
        return read_json(out)
    res: dict[str, Any] = {}
    for t in ("T03", "T10"):
        c = implemented_counts(t)
        order = rank_algorithms(t, c)
        res[t] = {"counts": c, "rank": order}
    o3 = res["T03"]["rank"]
    o10 = res["T10"]["rank"]
    sets = {
        "T03|TOP5": {"banned": o3[:5], "survivors": o3[5:], "rule": "5 most implemented of 6"},
        "T03|TOP3": {"banned": o3[:3], "survivors": o3[3:], "rule": "3 most implemented (added variant)"},
        "T10|TOP5": {"banned": o10[:3], "survivors": o10[3:], "rule": "all but the least implemented of 4"},
        "T1|TOP5": {"banned": T1_TOP5, "survivors_k7": T1_SURV7, "survivors_ext": T1_SURV_EXT,
                    "survivors": T1_SURV7, "rule": "exp9 literal TOP5 (bfs, dfs, gbfs, iddfs, astar)"},
    }
    res["sets"] = sets
    res["note"] = ("implemented = correct programs with that label; pooled over earlier twin rows, base-model "
                   "programs and plan-noise rows (engine kept per source); ties by base count, then alphabetical")
    write_json(out, res)
    logger.info(f"banned sets: {{k: v['banned'] for k, v in sets.items()}} -> survivors "
                f"{ {k: v['survivors'] for k, v in sets.items()} }")
    return res


# ------------------------------------------------------------------------------------------------ forced states
def load_forced(task: str) -> dict[str, Any]:
    import torch

    z = torch.load(CACHE_DIR / f"forced_states_{task}.pt", weights_only=False)
    X = z["X"].float().numpy()
    tw = z["twin"].float().numpy()
    meta = z["meta"]
    return {"X": X, "twin": tw, "meta": meta, "algs": np.array([m["alg"] for m in meta]),
            "kinds": np.array([m["kind"] for m in meta])}


def centroids(F: dict[str, Any], kind: str | None = "named") -> dict[str, np.ndarray]:
    m = np.ones(len(F["algs"]), dtype=bool) if kind is None else (F["kinds"] == kind)
    return {a: F["X"][m & (F["algs"] == a)].mean(0) for a in sorted(set(F["algs"][m]))}


def _unit(v: np.ndarray) -> np.ndarray:
    return v / max(float(np.linalg.norm(v)), 1e-12)


def push_direction(F: dict[str, Any], banned: list[str], surv: list[str]) -> np.ndarray:
    c = centroids(F, "named")
    return np.stack([_unit(np.mean([c[s][j] for s in surv], 0) - np.mean([c[b][j] for b in banned], 0))
                     for j in range(len(PLAN_BLOCKS))]).astype(np.float32)


def build_push_directions() -> dict[str, Any]:
    bs = read_json(PRED_DIR / "banned_sets.json")["sets"]
    rep: dict[str, Any] = {}
    for key, site_file in (("T03|TOP5", "T03_TOP5"), ("T03|TOP3", "T03_TOP3"), ("T10|TOP5", "T10_TOP5")):
        t = key.split("|")[0]
        F = load_forced(t)
        u = push_direction(F, bs[key]["banned"], bs[key]["survivors"])
        np.savez(DIR_DIR / f"u_push_{site_file}.npz", u=u, blocks=np.array(PLAN_BLOCKS),
                 banned=np.array(bs[key]["banned"]), survivors=np.array(bs[key]["survivors"]))
        rep[key] = {"file": f"directions/u_push_{site_file}.npz", "cross_block_cos":
                    [float(u[j] @ u[j + 1]) for j in range(len(PLAN_BLOCKS) - 1)]}
    # T1: exp20's committed u_top5 (FP8 forced states) is the literal replication; the bf16 rebuild is reported
    z = np.load(E20 / "directions" / "u_top5.npz")
    u20 = z["u_top5"].astype(np.float32)
    np.savez(DIR_DIR / "u_push_T1_TOP5.npz", u=u20, blocks=np.array(PLAN_BLOCKS), banned=np.array(T1_TOP5),
             survivors=np.array(T1_SURV_EXT), source=np.array("exp20 directions/u_top5.npz key u_top5"))
    F1 = load_forced("T1")
    u_bf = push_direction(F1, T1_TOP5, T1_SURV_EXT)
    u_bf7 = push_direction(F1, T1_TOP5, T1_SURV7)
    np.savez(DIR_DIR / "u_push_T1_bf16_rebuild.npz", u_ext=u_bf, u_k7=u_bf7)
    rep["T1|TOP5"] = {"file": "directions/u_push_T1_TOP5.npz (copy of exp20 u_top5)",
                      "cos_bf16_rebuild_ext_vs_exp20_fp8": [float(a @ b) for a, b in zip(u_bf, u20)],
                      "cos_bf16_rebuild_k7_vs_exp20_fp8": [float(a @ b) for a, b in zip(u_bf7, u20)],
                      "exp20_sha256": sha256_file(E20 / "directions" / "u_top5.npz")}
    # cosines with the per-slot random directions are logged in directions/seeds.json by the CPU prep
    write_json(RESULTS_DIR / "push_directions.json", rep)
    return rep


def pca_space(F: dict[str, Any], block: int, n_comp: int = 50) -> dict[str, Any]:
    j = BI[block]
    Xb = F["X"][:, j]
    med = float(np.median(np.linalg.norm(Xb, axis=1)))
    Z = Xb / med
    mu = Z.mean(0)
    _, S_, Vt = np.linalg.svd(Z - mu, full_matrices=False)
    V = Vt[:n_comp]
    return {"mu": mu, "V": V, "med": med, "explained": float((S_[:n_comp] ** 2).sum() / (S_ ** 2).sum()),
            "proj": lambda A: ((np.atleast_2d(A) / med) - mu) @ V.T}


def separability(F: dict[str, Any], block: int, kind: str | None = None) -> dict[str, float]:
    """Nearest-centroid leave-one-paraphrase-out accuracy per algorithm in the PCA-50 space (vectorised)."""
    sp = pca_space(F, block)
    m = np.ones(len(F["algs"]), dtype=bool) if kind is None else (F["kinds"] == kind)
    pc = sp["proj"](F["X"][m, BI[block]])
    A = F["algs"][m]
    names = sorted(set(A))
    C = np.stack([pc[A == a].mean(0) for a in names])
    cnt = np.array([(A == a).sum() for a in names], dtype=float)
    lab = np.array([names.index(a) for a in A])
    d = ((pc[:, None, :] - C[None]) ** 2).sum(-1)                     # [n, K]
    # own centroid without the point: c' = (n c - x) / (n - 1)
    own = (cnt[lab][:, None] * C[lab] - pc) / np.maximum(cnt[lab] - 1, 1)[:, None]
    d[np.arange(len(pc)), lab] = ((pc - own) ** 2).sum(-1)
    pred = d.argmin(1)
    return {a: float((pred[lab == i] == i).mean()) for i, a in enumerate(names)}


def push_progress() -> dict[str, Any]:
    bs = read_json(PRED_DIR / "banned_sets.json")["sets"]
    ps = np.load(CACHE_DIR / "push_states.npz")
    out: dict[str, Any] = {}
    for key in ("T03|TOP5", "T03|TOP3", "T10|TOP5", "T1|TOP5"):
        t, site = key.split("|")
        F = load_forced(t)
        surv = bs[key]["survivors"] if t != "T1" else T1_SURV_EXT
        ban = bs[key]["banned"]
        res: dict[str, Any] = {}
        for blk in (18, 23):
            sp = pca_space(F, blk)
            c = centroids(F, "named")
            cS = sp["proj"](np.mean([c[s][BI[blk]] for s in surv], 0))[0]
            cB = sp["proj"](np.mean([c[b][BI[blk]] for b in ban], 0))[0]
            v = _unit(cS - cB)
            per: dict[str, Any] = {}
            for a in (1.0, 2.0, 4.0):
                ts = []
                for jw, w in enumerate(TEMPLATE_IDS):
                    s_tw = sp["proj"](F["twin"][jw, BI[blk]])[0]
                    s_p = sp["proj"](ps[f"{t}|{site}|{w}|{a:g}|{blk}"])[0]
                    den = float((cS - s_tw) @ v)
                    ts.append(float((s_p - s_tw) @ v) / den if abs(den) > 1e-9 else float("nan"))
                per[f"{a:g}"] = {"t_mean": float(np.nanmean(ts)), "t_per_template": ts}
            res[f"block{blk}"] = {"t": per, "pca_explained_50": sp["explained"],
                                  "separability_named_masked": separability(F, blk),
                                  "separability_named": separability(F, blk, "named")}
        out[key] = res
    write_json(RESULTS_DIR / "push_progress.json", out)
    logger.info("push progress: " + "; ".join(f"{k} b18 " + ", ".join(
        f"a{a}={v['block18']['t'][a]['t_mean']:.2f}" for a in ("1", "2", "4")) for k, v in out.items()))
    return out


# ------------------------------------------------------------------------------------------------ manifold
def knn_graph(P: np.ndarray, k: int, n_core: int):
    """Symmetrised k-NN graph; nodes >= n_core (extra points) connect to their k nearest CORE nodes only."""
    from scipy.sparse import coo_matrix

    n = len(P)
    sq = (P ** 2).sum(1)
    D = np.sqrt(np.maximum(sq[:, None] + sq[None, :] - 2 * P @ P.T, 0.0))
    Dc = D[:, :n_core].copy()
    Dc[np.arange(min(n, n_core)), np.arange(min(n, n_core))] = np.inf
    nn = np.argsort(Dc, axis=1)[:, :k]
    rows = np.repeat(np.arange(n), k)
    cols = nn.ravel()
    w = D[rows, cols]
    G = coo_matrix((np.concatenate([w, w]), (np.concatenate([rows, cols]), np.concatenate([cols, rows]))),
                   shape=(n, n)).tocsr()
    G.sum_duplicates()
    # duplicates were summed: restore the single edge weight
    G.data = D[G.nonzero()] if G.nnz else G.data
    return G, D


def geodesics(P: np.ndarray, n_core: int, ks: tuple[int, ...] = (5, 10, 15)) -> dict[str, Any]:
    from scipy.sparse.csgraph import connected_components, shortest_path

    res: dict[str, Any] = {}
    chosen = None
    for k in ks:
        G, D = knn_graph(P, k, n_core)
        ncomp, _ = connected_components(G, directed=False)
        geo = shortest_path(G, directed=False)
        res[k] = {"connected": ncomp == 1, "n_components": int(ncomp), "geo": geo, "euclid": D}
        if chosen is None and ncomp == 1:
            chosen = k
    res["chosen_k"] = chosen
    return res


def classical_mds(G: np.ndarray, d: int = 2) -> np.ndarray:
    n = len(G)
    J = np.eye(n) - 1.0 / n
    B = -0.5 * J @ (G ** 2) @ J
    w, V = np.linalg.eigh(B)
    o = np.argsort(w)[::-1][:d]
    return V[:, o] * np.sqrt(np.maximum(w[o], 0))


def mds2(geo: np.ndarray, seed: int = 0) -> tuple[np.ndarray, float]:
    """2-D metric MDS (SMACOF) on the geodesic matrix, initialised at the classical-MDS solution (one run), with
    Kruskal stress-1 = sqrt(sum (delta - d)^2 / sum delta^2)."""
    from sklearn.manifold import MDS

    G = np.array(geo, dtype=float)
    fin = np.isfinite(G)
    if not fin.all():
        G[~fin] = np.nanmax(G[fin]) * 1.5
    G = (G + G.T) / 2
    np.fill_diagonal(G, 0.0)
    init = classical_mds(G)
    try:
        m = MDS(n_components=2, dissimilarity="precomputed", n_init=1, random_state=seed, normalized_stress=False,
                max_iter=300)
    except TypeError:
        m = MDS(n_components=2, metric="precomputed", n_init=1, random_state=seed, max_iter=300)
    Y = m.fit_transform(G, init=init)
    d = np.linalg.norm(Y[:, None] - Y[None], axis=-1)
    iu = np.triu_indices(len(G), 1)
    stress1 = float(np.sqrt(((G[iu] - d[iu]) ** 2).sum() / max((G[iu] ** 2).sum(), 1e-12)))
    return Y, stress1


def centroid_geo(P_core: np.ndarray, algs: np.ndarray, geo: np.ndarray, names: list[str]) -> np.ndarray:
    """Geodesic between centroids: offset to the nearest forced node + node geodesic + offset."""
    cent = {a: P_core[algs == a].mean(0) for a in names}
    node = {a: int(np.argmin(np.linalg.norm(P_core - cent[a], axis=1))) for a in names}
    off = {a: float(np.linalg.norm(cent[a] - P_core[node[a]])) for a in names}
    M = np.zeros((len(names), len(names)))
    for i, a in enumerate(names):
        for j, b in enumerate(names):
            M[i, j] = 0.0 if a == b else off[a] + geo[node[a], node[b]] + off[b]
    return M


def edge_test(landings: list[str], surv: list[str], dist_to_banned: dict[str, float], n_mc: int = 10000,
              seed: int = 0) -> dict[str, Any]:
    """Random-survivor null: each landing replaced by a uniformly random survivor; exact when enumerable."""
    n, m = len(landings), len(surv)
    if n == 0 or m < 2:
        return {"computable": False, "reason": "no survivor program" if n == 0 else "fewer than 2 survivors",
                "n_landings": n}
    d = np.array([dist_to_banned[s] for s in surv])
    D_obs = float(np.mean([dist_to_banned[s] for s in landings]))
    med = float(np.median(d))
    edge_share = float(np.mean([dist_to_banned[s] < med for s in landings]))
    n_comp = math.comb(n + m - 1, m - 1)
    if n_comp <= 2_000_000:
        # exact: enumerate count vectors with multinomial probabilities
        p_le = p_ge = 0.0
        logm = n * math.log(m)
        lf = [math.lgamma(i + 1) for i in range(n + 1)]
        for cuts in itertools.combinations(range(n + m - 1), m - 1):
            prev = -1
            cnt = []
            for c in cuts:
                cnt.append(c - prev - 1)
                prev = c
            cnt.append(n + m - 1 - prev - 1)
            lp = lf[n] - sum(lf[x] for x in cnt) - logm
            pr = math.exp(lp)
            Dn = float(np.dot(cnt, d)) / n
            if Dn <= D_obs + 1e-12:
                p_le += pr
            if Dn >= D_obs - 1e-12:
                p_ge += pr
        method = "exact enumeration"
    else:
        rng = np.random.default_rng(seed)
        Dn = d[rng.integers(0, m, size=(n_mc, n))].mean(1)
        p_le = float((Dn <= D_obs + 1e-12).mean())
        p_ge = float((Dn >= D_obs - 1e-12).mean())
        method = f"monte carlo {n_mc}"
    return {"computable": True, "n_landings": n, "D_obs": D_obs, "edge_share": edge_share, "median_d": med,
            "p_edge": float(p_le), "p_opp": float(p_ge), "method": method,
            "d_per_survivor": {s: float(dist_to_banned[s]) for s in surv},
            "landing_counts": dict(Counter(landings))}
