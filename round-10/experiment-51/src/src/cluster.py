#!/usr/bin/env python3
"""Behaviour clusters over P1 decision vectors (2,000 states; ERR = 65535 never agrees) and AST surface clusters.

agreement(a, b) = mean_s [a_s == b_s and a_s != ERR]. Distances are kept in integer units (number of disagreeing
states) so the 0.95 threshold is exact: complete linkage cut at 100 of 2,000 = every within-cluster pair agrees
>= 0.95. Leader clustering in call order is the check."""
from __future__ import annotations

import ast
import re

import numpy as np
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components

ERR = 65535
N_STATES = 2000
THRESH = 0.95
CUT = int(round(N_STATES * (1 - THRESH)))  # 100 disagreeing states


def agree_counts(U: np.ndarray, V: np.ndarray | None = None) -> np.ndarray:
    """C[i, j] = number of states where U_i == V_j and U_i != ERR (int32)."""
    V = U if V is None else V
    U = np.ascontiguousarray(U, dtype=np.uint16)
    V = np.ascontiguousarray(V, dtype=np.uint16)
    out = np.zeros((len(U), len(V)), dtype=np.int32)
    if len(U) == 0 or len(V) == 0:
        return out
    blk = max(1, int(1.5e8 // max(1, len(V) * U.shape[1])))
    for i0 in range(0, len(U), blk):
        u = U[i0:i0 + blk]
        eq = (u[:, None, :] == V[None, :, :]) & (u[:, None, :] != ERR)
        out[i0:i0 + blk] = eq.sum(axis=2, dtype=np.int32)
    return out


def agreement(a: np.ndarray, b: np.ndarray) -> float:
    a, b = np.asarray(a), np.asarray(b)
    return float(np.mean((a == b) & (a != ERR)))


def unique_counts(D: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Unique decision vectors, the inverse map row -> unique index, and their pairwise agreement counts."""
    if len(D) == 0:
        return np.zeros((0, N_STATES), dtype=np.uint16), np.zeros(0, dtype=int), np.zeros((0, 0), dtype=np.int32)
    uniq, inv = np.unique(D, axis=0, return_inverse=True)
    return uniq, inv.reshape(-1), agree_counts(uniq)


def linkage_labels(C: np.ndarray) -> tuple[np.ndarray, int]:
    """Complete linkage on unique vectors given their agreement counts; cut so all pairs agree >= 0.95."""
    n = len(C)
    if n == 0:
        return np.zeros(0, dtype=int), 0
    if n == 1:
        return np.zeros(1, dtype=int), 1
    dist = (N_STATES - C).astype(np.float64)
    np.fill_diagonal(dist, 0.0)
    dist = np.maximum(dist, dist.T)
    iu = np.triu_indices(n, 1)
    lab = fcluster(linkage(dist[iu], method="complete"), t=CUT, criterion="distance")
    _, lab = np.unique(lab, return_inverse=True)
    return lab.reshape(-1), int(lab.max() + 1)


def clusters_in_subset(inv: np.ndarray, C: np.ndarray, rows: np.ndarray) -> int:
    """Complete-linkage cluster count recomputed on a subset of rows (prefixes, rarefied subsets, shuffles)."""
    if len(rows) == 0:
        return 0
    u = np.unique(inv[rows])
    return linkage_labels(C[np.ix_(u, u)])[1]


def complete_linkage(D: np.ndarray, pre: tuple | None = None) -> tuple[np.ndarray, int]:
    """Cluster labels (per row of D) with complete linkage cut so that all within-cluster pairs agree >= 0.95.
    Unique vectors are clustered once (exact duplicates map to one point, as the plan's 'unique vectors with
    multiplicities')."""
    if len(D) == 0:
        return np.zeros(0, dtype=int), 0
    uniq, inv, C = pre if pre is not None else unique_counts(D)
    lab_u, n = linkage_labels(C)
    lab = lab_u[inv]
    _, lab = np.unique(lab, return_inverse=True)
    return lab.reshape(-1), int(lab.max() + 1)


def leader(D: np.ndarray) -> tuple[np.ndarray, list[int]]:
    """Leader clustering in row (call) order; a row joins the first leader it agrees with >= 0.95."""
    n = len(D)
    L = np.empty((n, D.shape[1] if D.ndim == 2 else N_STATES), dtype=np.uint16)
    leaders: list[int] = []
    lab = np.zeros(n, dtype=int)
    for i in range(n):
        k = len(leaders)
        if k:
            c = ((L[:k] == D[i]) & (L[:k] != ERR)).sum(axis=1)
            hit = np.nonzero(c >= N_STATES - CUT)[0]
            if hit.size:
                lab[i] = int(hit[0])
                continue
        L[k] = D[i]
        leaders.append(i)
        lab[i] = k
    return lab, leaders


def discovery_curves(D: np.ndarray, call_idx: np.ndarray, n_calls: int, step: int = 100,
                     pre: tuple | None = None) -> dict:
    """Complete-linkage cluster counts on prefixes every `step` calls and the leader curve (per call)."""
    uniq, inv, C = pre if pre is not None else unique_counts(D)
    pts, cl = [], []
    for c in range(step, n_calls + step, step):
        rows = np.nonzero(call_idx < c)[0]
        pts.append(min(c, n_calls))
        cl.append(clusters_in_subset(inv, C, rows))
    lab, leaders = leader(D)
    first = np.zeros(n_calls, dtype=int)
    for li in leaders:
        first[int(call_idx[li])] += 1
    return {"calls": pts, "complete": cl, "leader_cum": np.cumsum(first).tolist()}


# ------------------------------------------------------------------------------------------- surface (AST) clusters
def shingles(code: str, n: int = 4) -> set[str] | None:
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError):
        return None
    toks = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            toks.append("ID")
        elif isinstance(node, ast.Constant):
            toks.append("CONST")
        elif isinstance(node, ast.Attribute):
            toks.append("ATTR:" + (node.attr if re.fullmatch(r"[a-z_]+", node.attr) else "x"))
        elif isinstance(node, ast.arg):
            toks.append("ARG")
        else:
            toks.append(type(node).__name__)
    return {"|".join(toks[i:i + n]) for i in range(max(1, len(toks) - n + 1))}


def surface_clusters(codes: list[str], thresh: float = 0.8) -> tuple[np.ndarray, int]:
    sets = [shingles(c) or set() for c in codes]
    vocab: dict[str, int] = {}
    rows, cols = [], []
    for i, s in enumerate(sets):
        for t in s:
            cols.append(vocab.setdefault(t, len(vocab)))
            rows.append(i)
    if not codes:
        return np.zeros(0, dtype=int), 0
    A = csr_matrix((np.ones(len(rows), dtype=np.float32), (rows, cols)), shape=(len(codes), max(1, len(vocab))))
    inter = (A @ A.T).toarray()
    sz = np.array([len(s) for s in sets], dtype=np.float32)
    union = sz[:, None] + sz[None, :] - inter
    J = np.where(union > 0, inter / np.maximum(union, 1e-9), 0.0)
    adj = csr_matrix(J >= thresh)
    n, lab = connected_components(adj, directed=False)
    return lab, int(n)
