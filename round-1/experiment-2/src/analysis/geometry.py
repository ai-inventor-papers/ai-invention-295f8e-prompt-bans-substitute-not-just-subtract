#!/usr/bin/env python3
"""Geometry helpers shared by Phase B (commit-time geometry) and Phase E (figures/analysis).

Manifold = symmetric kNN graph over the named forced-prompt read-position states of one task (centred,
reduced to the PCs explaining 95% of variance, cap 50); MST edges are added if the kNN graph is
disconnected; extra points (centroids, condition means) are attached as nodes to their k nearest points;
geodesic distances are graph shortest paths.
"""
from __future__ import annotations

import numpy as np
from scipy.sparse import coo_matrix, csr_matrix
from scipy.sparse.csgraph import connected_components, minimum_spanning_tree, shortest_path
from scipy.spatial.distance import cdist


def pca95(X: np.ndarray, cap: int = 50, var: float = 0.95) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (mean, components [k, D], explained ratios) of the PCs explaining `var` of the variance."""
    mu = X.mean(0)
    Xc = X - mu
    U, S, Vt = np.linalg.svd(Xc, full_matrices=False)
    ev = S ** 2 / max(np.sum(S ** 2), 1e-12)
    k = int(np.searchsorted(np.cumsum(ev), var) + 1)
    k = max(2, min(k, cap, Vt.shape[0]))
    return mu, Vt[:k], ev[:k]


def knn_graph(P: np.ndarray, k: int, metric: str = "euclidean") -> tuple[csr_matrix, dict]:
    n = len(P)
    D = cdist(P, P, metric=metric)
    np.fill_diagonal(D, np.inf)
    k = min(k, n - 1)
    idx = np.argsort(D, axis=1)[:, :k]
    rows = np.repeat(np.arange(n), k)
    cols = idx.ravel()
    w = D[rows, cols]
    G = coo_matrix((w, (rows, cols)), shape=(n, n)).tocsr()
    G = G.maximum(G.T)  # symmetric kNN
    ncomp, _ = connected_components(G, directed=False)
    info = {"n_components_knn": int(ncomp), "mst_added": False}
    if ncomp > 1:
        Dfull = D.copy()
        np.fill_diagonal(Dfull, 0)
        mst = minimum_spanning_tree(csr_matrix(Dfull)).tocsr()
        mst = mst.maximum(mst.T)
        G = G.maximum(mst)
        info["mst_added"] = True
        info["n_components_after"] = int(connected_components(G, directed=False)[0])
    return G, info


def attach(G: csr_matrix, P: np.ndarray, Q: np.ndarray, k: int, metric: str = "euclidean") -> csr_matrix:
    """Add the rows of Q as extra nodes, each joined to its k nearest points of P (leaf nodes)."""
    n, m = len(P), len(Q)
    D = cdist(Q, P, metric=metric)
    k = min(k, n)
    idx = np.argsort(D, axis=1)[:, :k]
    G2 = G.tocoo()
    rows = list(G2.row)
    cols = list(G2.col)
    vals = list(G2.data)
    for i in range(m):
        for j in idx[i]:
            rows += [n + i, j]
            cols += [j, n + i]
            vals += [D[i, j], D[i, j]]
    return coo_matrix((vals, (rows, cols)), shape=(n + m, n + m)).tocsr()


def geodesic_between(G: csr_matrix, P: np.ndarray, Q: np.ndarray, k: int, metric: str = "euclidean") -> np.ndarray:
    """Geodesic distance matrix among the rows of Q after attaching them to the fixed graph G over P."""
    n = len(P)
    GA = attach(G, P, Q, k, metric)
    D = shortest_path(GA, directed=False, indices=np.arange(n, n + len(Q)))
    return D[:, n:]


def geodesic_full(G: csr_matrix, P: np.ndarray, Q: np.ndarray, k: int, metric: str = "euclidean") -> np.ndarray:
    """All-pairs geodesics over points + attached nodes (for MDS of the whole picture)."""
    GA = attach(G, P, Q, k, metric)
    return shortest_path(GA, directed=False)


def twonn_id(X: np.ndarray) -> float:
    """TwoNN intrinsic dimension (Facco et al. 2017), MLE form."""
    D = cdist(X, X)
    np.fill_diagonal(D, np.inf)
    s = np.sort(D, axis=1)[:, :2]
    ok = s[:, 0] > 0
    mu = s[ok, 1] / s[ok, 0]
    mu = mu[np.isfinite(mu) & (mu > 1)]
    if len(mu) < 3:
        return float("nan")
    return float(len(mu) / np.sum(np.log(mu)))


def softmax_neg(d: np.ndarray, scale: float) -> np.ndarray:
    z = -d / max(scale, 1e-9)
    z = z - z.max()
    e = np.exp(z)
    return e / e.sum()
