#!/usr/bin/env python3
"""Item 0e: is iteration 8's 'opposite' landing a property of the alias-named manifold?

Works only on iteration 8's own stored state of art_R-HSmXq2t97f, read in place:
  cache/states/geo_C6_nf4.npz   geo_k10, geo_k15 (300 x 300 kNN geodesics at block 31), labels, L
  cache/states/smean_C6_nf4.npz kind, algorithm, group (= template * 3 + alias), template, smean, blocks
The k-NN graph used for inference is never refitted; gate E4 recomputes it once, with separate code, as a cross-check.

Definitions (committed in predictions/commit_s0e.json before any alias-level number was computed):
  g(alg, alias) = min over banned b of the mean geodesic between the 10 points of (alg, alias) and the 30 points of b
  primary overlap   = number of distinct committed detectors D1-D11 matching the alias string
  secondary overlap = max content-token Jaccard with any of the 15 banned aliases
"""
from __future__ import annotations

import ast
import itertools
import math
import re
from pathlib import Path
from typing import Any

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components, shortest_path
from scipy.spatial import ConvexHull, cKDTree
from scipy.spatial.distance import cdist
from scipy.stats import rankdata

BANNED = ["bfs", "dfs", "iddfs", "astar", "gbfs"]
NONBANNED = ["bibfs", "dijkstra_unit", "idastar", "jps", "biastar"]   # CANON_ORDER restricted to the non-banned five
DISPLAY = {"bibfs": "bidirectional BFS", "dijkstra_unit": "unit-weight Dijkstra", "idastar": "IDA*",
           "jps": "jump point search", "biastar": "bidirectional A*"}
DETECTORS: list[tuple[str, str]] = [
    ("D1_bfs", r"\bbfs\b"), ("D2_breadth_first", r"breadth[-_ ]?first"), ("D3_dfs", r"\bdfs\b"),
    ("D4_depth_first", r"depth[-_ ]?first"), ("D5_iddfs", r"\biddfs\b"),
    ("D6_iterative_deepening", r"iterative[-_ ]?deepening"), ("D7_astar", r"a\*|a[-_ ]?star|astar"),
    ("D8_greedy", r"greedy"), ("D9_best_first", r"best[-_ ]?first"), ("D10_manhattan", r"manhattan"),
    ("D11_heuristic", r"heuristic")]
EXPECTED_PRIMARY = {"bibfs": [1, 1, 1], "dijkstra_unit": [0, 0, 0], "idastar": [1, 2, 3], "jps": [0, 0, 0],
                    "biastar": [1, 1, 1]}
STOPWORDS = {"a", "an", "the", "with", "from", "both", "at", "once", "on", "run", "and", "of", "to", "s", "search",
             "algorithm"}
N_TEMPLATES, N_ALIAS = 10, 3
N_BOOT, N_PLACEBO, N_MC_SECONDARY = 2000, 1000, 200_000
SEED = 20261023


# ------------------------------------------------------------------------------------------- inputs from source code
def read_literal(py: Path, name: str) -> Any:
    """Read a module-level literal assignment (e.g. ALIAS_TABLE) from a source file without importing it."""
    tree = ast.parse(py.read_text())
    for node in tree.body:
        tgt = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            tgt, val = node.targets[0].id, node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.value is not None:
            tgt, val = node.target.id, node.value
        if tgt == name:
            return ast.literal_eval(val)
    raise KeyError(f"{name} not found in {py}")


# ------------------------------------------------------------------------------------------- lexical overlap scores
def primary_overlap(alias: str) -> tuple[int, list[str]]:
    hits = [n for n, pat in DETECTORS if re.search(pat, alias, flags=re.IGNORECASE)]
    return len(hits), hits


def content_tokens(s: str) -> set[str]:
    return {t for t in re.split(r"[^a-z0-9*]+", s.lower()) if t and t not in STOPWORDS}


def secondary_overlap(alias: str, banned_aliases: list[str]) -> tuple[float, str]:
    a = content_tokens(alias)
    best, arg = 0.0, ""
    for b in banned_aliases:
        bt = content_tokens(b)
        j = len(a & bt) / len(a | bt) if (a | bt) else 0.0
        if j > best + 1e-15:
            best, arg = j, b
    return best, arg


def overlap_table(alias_table: dict[str, list[str]]) -> list[dict[str, Any]]:
    banned_aliases = [s for b in BANNED for s in alias_table[b]]
    rows = []
    for a in NONBANNED:
        for j, s in enumerate(alias_table[a]):
            p, hits = primary_overlap(s)
            sec, arg = secondary_overlap(s, banned_aliases)
            rows.append({"algorithm": a, "alias_index": j, "alias": s, "primary": p, "detectors": hits,
                         "secondary": round(sec, 12), "secondary_argmax_banned_alias": arg,
                         "content_tokens": sorted(content_tokens(s))})
    return rows


# ------------------------------------------------------------------------------------------- statistics helpers
def spearman(x: np.ndarray, y: np.ndarray) -> float:
    rx, ry = rankdata(x), rankdata(y)
    rx, ry = rx - rx.mean(), ry - ry.mean()
    den = math.sqrt(float((rx ** 2).sum() * (ry ** 2).sum()))
    return float((rx * ry).sum() / den) if den > 0 else float("nan")


def distinct_assignments(values: list[float]) -> np.ndarray:
    """All distinct arrangements of a multiset over len(values) positions (rows), by recursive placement."""
    vals, counts = np.unique(np.asarray(values, dtype=float), return_counts=True)
    n = len(values)
    rows: list[np.ndarray] = []

    def place(free: tuple[int, ...], k: int, cur: np.ndarray) -> None:
        if k == len(vals):
            rows.append(cur.copy())
            return
        for pos in itertools.combinations(free, int(counts[k])):
            cur[list(pos)] = vals[k]
            rest = tuple(f for f in free if f not in pos)
            place(rest, k + 1, cur)

    place(tuple(range(n)), 0, np.full(n, np.nan))
    return np.stack(rows)


def n_distinct_assignments(values: list[float]) -> int:
    _, counts = np.unique(np.asarray(values, dtype=float), return_counts=True)
    out = math.factorial(len(values))
    for c in counts:
        out //= math.factorial(int(c))
    return out


def null_rhos_exact(values: list[float]) -> np.ndarray:
    """Spearman of g-ranks 1..n (no ties) against every distinct arrangement of the overlap multiset. The distribution
    does not depend on which g-rank order is observed, so one table serves every observed g without ties."""
    A = distinct_assignments(values)
    R = np.apply_along_axis(rankdata, 1, A)
    R = R - R.mean(1, keepdims=True)
    gr = np.arange(1, A.shape[1] + 1, dtype=float)
    gr = gr - gr.mean()
    den = np.sqrt((R ** 2).sum(1) * (gr ** 2).sum())
    return (R @ gr) / den


def p_from_null(rho: float, null: np.ndarray) -> dict[str, float]:
    eps = 1e-12
    return {"p_lower": float(np.mean(null <= rho + eps)), "p_two_sided": float(np.mean(np.abs(null) >= abs(rho) - eps))}


def null_rhos_mc(g: np.ndarray, values: np.ndarray, n: int, rng: np.random.Generator) -> np.ndarray:
    rg = rankdata(g)
    rg = rg - rg.mean()
    out = np.empty(n)
    for s in range(0, n, 20_000):
        m = min(20_000, n - s)
        P = np.stack([rng.permutation(values) for _ in range(m)])
        R = np.apply_along_axis(rankdata, 1, P)
        R = R - R.mean(1, keepdims=True)
        out[s:s + m] = (R @ rg) / np.sqrt((R ** 2).sum(1) * (rg ** 2).sum())
    return out


# ------------------------------------------------------------------------------------------- geometry
def alias_sets(labels: np.ndarray, group: np.ndarray) -> dict[tuple[str, int], np.ndarray]:
    return {(a, j): np.where((labels == a) & (group % 3 == j))[0] for a in NONBANNED for j in range(N_ALIAS)}


def g_alias(geo: np.ndarray, labels: np.ndarray, group: np.ndarray) -> dict[tuple[str, int], float]:
    sets = alias_sets(labels, group)
    bidx = {b: np.where(labels == b)[0] for b in BANNED}
    return {k: min(float(geo[np.ix_(ix, bidx[b])].mean()) for b in BANNED) for k, ix in sets.items()}


def g_algorithm(geo: np.ndarray, labels: np.ndarray) -> dict[str, float]:
    bidx = {b: np.where(labels == b)[0] for b in BANNED}
    return {a: min(float(geo[np.ix_(np.where(labels == a)[0], bidx[b])].mean()) for b in BANNED) for a in NONBANNED}


def classify(g: dict[str, float]) -> dict[str, str]:
    med = float(np.median(list(g.values())))
    return {a: ("EDGE" if v < med - 1e-12 else "OPPOSITE" if v > med + 1e-12 else "MIDDLE") for a, v in g.items()}


def knn_geodesic_independent(X: np.ndarray, k: int) -> tuple[np.ndarray, int]:
    """Cross-check implementation (E4): cKDTree k-NN, symmetrised by union, every pair of components joined by its
    shortest inter-component edge, Dijkstra shortest paths. Shares no code with iteration 8's geometry.py."""
    n = len(X)
    tree = cKDTree(X)
    dist, idx = tree.query(X, k=k + 1)
    rows, cols, vals = [], [], []
    for i in range(n):
        nb = [(d, j) for d, j in zip(dist[i], idx[i]) if j != i][:k]
        for d, j in nb:
            rows += [i, j]
            cols += [j, i]
            vals += [max(d, 1e-12)] * 2
    W = csr_matrix((vals, (rows, cols)), shape=(n, n))
    W.sum_duplicates()
    W.data = np.where(W.data > 0, W.data, 1e-12)
    # union symmetrisation: duplicate entries were summed, so restore the plain distance on every stored edge
    W = W.tocoo()
    D_full = np.sqrt(np.maximum(((X[W.row] - X[W.col]) ** 2).sum(1), 0.0))
    W = csr_matrix((np.maximum(D_full, 1e-12), (W.row, W.col)), shape=(n, n))
    ncomp, lab = connected_components(W, directed=False)
    if ncomp > 1:
        W = W.tolil()
        comps = [np.where(lab == c)[0] for c in range(ncomp)]
        for a in range(ncomp):
            for b in range(a + 1, ncomp):
                Da = cdist(X[comps[a]], X[comps[b]])
                i, j = np.unravel_index(np.argmin(Da), Da.shape)
                W[comps[a][i], comps[b][j]] = W[comps[b][j], comps[a][i]] = max(float(Da[i, j]), 1e-12)
        W = W.tocsr()
    return shortest_path(W, method="D", directed=False), int(ncomp)


def classical_mds(D: np.ndarray, k: int = 2) -> tuple[np.ndarray, float]:
    n = len(D)
    J = np.eye(n) - 1.0 / n
    B = -0.5 * J @ (D ** 2) @ J
    w, V = np.linalg.eigh(B)
    i = np.argsort(w)[::-1][:k]
    Y = V[:, i] * np.sqrt(np.maximum(w[i], 0))
    d = np.sqrt(((Y[:, None, :] - Y[None, :, :]) ** 2).sum(-1))
    iu = np.triu_indices(n, 1)
    stress = float(np.sqrt(((D[iu] - d[iu]) ** 2).sum() / (D[iu] ** 2).sum()))
    return Y, stress


# ------------------------------------------------------------------------------------------- within-algorithm tests
def within_perms() -> list[tuple[int, ...]]:
    return list(itertools.permutations(range(N_ALIAS)))


def stratified_stat(g: np.ndarray, x: np.ndarray) -> tuple[float, int]:
    """Mean over algorithms with non-constant x of the 3-point within-algorithm Spearman (g, x). g, x: (5, 3)."""
    vals = [spearman(g[a], x[a]) for a in range(len(g)) if np.ptp(x[a]) > 1e-12]
    return (float(np.mean(vals)) if vals else float("nan")), len(vals)


def fe_beta(g: np.ndarray, x: np.ndarray) -> float:
    gc = g - g.mean(1, keepdims=True)
    xc = x - x.mean(1, keepdims=True)
    den = float((xc ** 2).sum())
    return float((gc * xc).sum() / den) if den > 0 else float("nan")


def stratified_exact(g: np.ndarray, x: np.ndarray) -> dict[str, Any]:
    """Exact null over (3!)^5 within-algorithm relabelings of x; reports both the nominal and effective spaces."""
    obs, n_used = stratified_stat(g, x)
    b_obs = fe_beta(g, x)
    P = within_perms()
    stats, betas = [], []
    for combo in itertools.product(P, repeat=len(g)):
        xp = np.stack([x[a][list(combo[a])] for a in range(len(g))])
        stats.append(stratified_stat(g, xp)[0])
        betas.append(fe_beta(g, xp))
    stats, betas = np.array(stats), np.array(betas)
    eps = 1e-12
    n_var = int(sum(np.ptp(x[a]) > 1e-12 for a in range(len(g))))
    return {"stat": obs, "n_algorithms_used": n_used, "n_constant_skipped": len(g) - n_used,
            "n_arrangements_nominal": len(stats), "n_arrangements_effective": 6 ** n_var,
            "floor_effective": 1.0 / 6 ** n_var if n_var else float("nan"),
            "p_lower": float(np.mean(stats <= obs + eps)), "p_upper": float(np.mean(stats >= obs - eps)),
            "p_two_sided": float(np.mean(np.abs(stats) >= abs(obs) - eps)),
            "beta": b_obs, "beta_p_lower": float(np.mean(betas <= b_obs + eps)),
            "beta_p_two_sided": float(np.mean(np.abs(betas) >= abs(b_obs) - eps)),
            "null_mean": float(np.nanmean(stats)), "null_sd": float(np.nanstd(stats))}


# ------------------------------------------------------------------------------------------- bootstrap over templates
def template_blocks(geo: np.ndarray, labels: np.ndarray, group: np.ndarray) -> dict[tuple[str, int, str], np.ndarray]:
    """For each non-banned alias set and banned algorithm: a 10 x 10 (template x template) matrix of mean geodesics,
    averaging the banned side over its 3 aliases, so that resampled means are quadratic forms in template weights."""
    tmpl = group // 3
    out = {}
    for a in NONBANNED:
        for j in range(N_ALIAS):
            ia = {int(t): int(i) for i in np.where((labels == a) & (group % 3 == j))[0] for t in [tmpl[i]]}
            for b in BANNED:
                M = np.zeros((N_TEMPLATES, N_TEMPLATES))
                for t in range(N_TEMPLATES):
                    for t2 in range(N_TEMPLATES):
                        ib = np.where((labels == b) & (tmpl == t2))[0]
                        M[t, t2] = geo[ia[t], ib].mean()
                out[(a, j, b)] = M
    return out


def boot_g(blocks: dict[tuple[str, int, str], np.ndarray], W: np.ndarray) -> np.ndarray:
    """(n_boot, 15) alias-level g under template weights W (n_boot, 10)."""
    tot = W.sum(1) ** 2
    G = np.empty((len(W), len(NONBANNED) * N_ALIAS))
    c = 0
    for a in NONBANNED:
        for j in range(N_ALIAS):
            m = np.stack([np.einsum("rt,ts,rs->r", W, blocks[(a, j, b)], W) / tot for b in BANNED], 1)
            G[:, c] = m.min(1)
            c += 1
    return G


def boot_g_alg(blocks: dict[tuple[str, int, str], np.ndarray], W: np.ndarray) -> np.ndarray:
    """(n_boot, 5) algorithm-level g: the algorithm's 30 points are the 3 alias sets pooled."""
    tot = W.sum(1) ** 2
    out = np.empty((len(W), len(NONBANNED)))
    for ai, a in enumerate(NONBANNED):
        m = np.stack([np.mean([np.einsum("rt,ts,rs->r", W, blocks[(a, j, b)], W) / tot for j in range(N_ALIAS)], 0)
                      for b in BANNED], 1)
        out[:, ai] = m.min(1)
    return out


def rowwise_spearman(G: np.ndarray, x: np.ndarray) -> np.ndarray:
    RG = np.apply_along_axis(rankdata, 1, G)
    RG = RG - RG.mean(1, keepdims=True)
    rx = rankdata(x)
    rx = rx - rx.mean()
    return (RG @ rx) / np.sqrt((RG ** 2).sum(1) * (rx ** 2).sum())


def verdict_sentence(rho: float, p: float, strat_p: float) -> tuple[str, str]:
    if rho <= -0.6 and strat_p < 0.05:
        return "NAMES", "names move the geometry even with the algorithm held fixed"
    if rho <= -0.6:
        return "CONFOUNDED", (f"g follows alias overlap across algorithms (rho {rho:.2f}, p {p:.3g}), but the pattern is "
                              "carried by algorithm identity; on this manifold names and mechanisms are confounded, "
                              "and TP-G's name-free manifolds decide")
    return "NOT_TRACKED", (f"iteration 8's geodesics do not track alias overlap at the committed strength "
                           f"(rho {rho:.2f})")


def convex_outline(P: np.ndarray) -> np.ndarray:
    try:
        h = ConvexHull(P)
        v = list(h.vertices) + [h.vertices[0]]
        return P[v]
    except Exception:  # noqa: BLE001 - degenerate hulls (collinear points) fall back to the points themselves
        return P
