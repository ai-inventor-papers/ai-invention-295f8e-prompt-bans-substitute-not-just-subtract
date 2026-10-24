#!/usr/bin/env python3
"""Behaviour agreement via sparse one-hot products, complete-linkage clusters (every within-cluster pair agrees at
least 0.95) and the leader-clustering check (call order)."""
from __future__ import annotations

import numpy as np
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.sparse import csr_matrix
from scipy.spatial.distance import squareform

ERR = 65535
V = 152  # decision values are remaining capacities 0..150


def onehot(dec: np.ndarray) -> csr_matrix:
    dec = np.asarray(dec)
    if dec.ndim == 1:
        dec = dec[None, :]
    n, S = dec.shape
    ok = (dec != ERR).ravel()
    rows = np.repeat(np.arange(n, dtype=np.int64), S)[ok]
    cols = (np.tile(np.arange(S, dtype=np.int64), n) * V + np.minimum(dec, V - 1).astype(np.int64).ravel())[ok]
    return csr_matrix((np.ones(len(rows), dtype=np.float32), (rows, cols)), shape=(n, S * V))


def agreement_matrix(a: np.ndarray, b: np.ndarray, mask: np.ndarray | None = None) -> np.ndarray:
    """A[i, j] = mean over states of [a_i == b_j and a_i != ERR] (optionally over the masked states only)."""
    a, b = np.atleast_2d(a), np.atleast_2d(b)
    if mask is not None:
        a, b = a[:, mask], b[:, mask]
    S = a.shape[1]
    if a.shape[0] == 0 or b.shape[0] == 0:
        return np.zeros((a.shape[0], b.shape[0]))
    M = (onehot(a) @ onehot(b).T).toarray().astype(np.float64)
    return M / S


def complete_linkage(dec: np.ndarray, thr: float = 0.95, mask: np.ndarray | None = None) -> np.ndarray:
    """Cluster labels (1..k) by complete linkage on 1 - agreement, cut at 1 - thr."""
    n = len(dec)
    if n == 0:
        return np.zeros(0, dtype=int)
    if n == 1:
        return np.ones(1, dtype=int)
    A = agreement_matrix(dec, dec, mask)
    D = 1.0 - A
    np.fill_diagonal(D, 0.0)
    D = np.clip((D + D.T) / 2.0, 0.0, 1.0)
    Z = linkage(squareform(D, checks=False), method="complete")
    return fcluster(Z, t=1.0 - thr + 1e-12, criterion="distance")


def linkage_invariant(dec: np.ndarray, labels: np.ndarray, thr: float = 0.95, mask=None) -> bool:
    """Every within-cluster pair (distinct members) agrees at least thr."""
    A = agreement_matrix(dec, dec, mask)
    for c in np.unique(labels):
        ii = np.nonzero(labels == c)[0]
        if len(ii) < 2:
            continue
        sub = A[np.ix_(ii, ii)]
        off = sub[~np.eye(len(ii), dtype=bool)]
        if off.min() < thr - 1e-9:
            return False
    return True


def leader_clusters(dec: np.ndarray, thr: float = 0.95, mask=None) -> np.ndarray:
    """Leader clustering in the given (call) order: join the first leader agreeing >= thr, else lead."""
    leaders: list[int] = []
    lab = np.zeros(len(dec), dtype=int)
    if len(dec) == 0:
        return lab
    X = onehot(dec[:, mask] if mask is not None else dec)
    S = dec.shape[1] if mask is None else int(mask.sum())
    for i in range(len(dec)):
        if leaders:
            ag = (X[leaders] @ X[i].T).toarray().ravel() / S
            j = int(np.argmax(ag >= thr)) if (ag >= thr).any() else -1
        else:
            j = -1
        if j < 0:
            leaders.append(i)
            lab[i] = len(leaders)
        else:
            lab[i] = j + 1
    return lab


def unique_with_counts(dec: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Unique decision vectors (first-occurrence order), their counts and the inverse index."""
    if len(dec) == 0:
        return dec, np.zeros(0, dtype=int), np.zeros(0, dtype=int)
    u, first, inv, cnt = np.unique(dec, axis=0, return_index=True, return_inverse=True, return_counts=True)
    order = np.argsort(first)
    rank = np.empty_like(order)
    rank[order] = np.arange(len(order))
    return u[order], cnt[order], rank[inv.ravel()]
