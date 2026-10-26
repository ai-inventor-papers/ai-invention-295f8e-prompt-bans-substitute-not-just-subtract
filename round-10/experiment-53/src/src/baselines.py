"""Baselines: NN (seed program), tour-length references (insertion heuristics, greedy edge), tuned parametric P1.

P1 family (a superset of the EoH/ReEvo seed rule's features), argmin over j in U of
  d(c,j) + w_dst d(j,dest) + w_ang (1 - cos turn(last edge, c->j)) + w_mu mean_{k in U,k!=j} d(j,k)
        + w_sd std_{k in U,k!=j} d(j,k)
with the turn computed from the distance matrix by the law of cosines (1 - cos turn = 1 + cos alpha_c), 0 on the
first move. The last edge needs the previous city, which the interface does not pass: the program keeps it in a
module-level dict, so the angle term is active in tours (one exec per instance) and inactive in probes (one exec
per probe call) -- the same protocol every generated program faces.
"""
from __future__ import annotations

import numpy as np

SPEC_DOC = "Return the next city to visit: one element of unvisited_nodes."

NN_PROGRAM = '''import numpy as np
import math


def select_next_node(current_node, destination_node, unvisited_nodes, distance_matrix):
    """Return the next city to visit: one element of unvisited_nodes."""
    next_node = None
    best_distance = float("inf")
    for node in unvisited_nodes:
        distance = distance_matrix[current_node][node]
        if distance < best_distance:
            best_distance = distance
            next_node = node
    return next_node
'''

P1_TEMPLATE = '''import numpy as np
import math

W_DST = {w_dst!r}
W_ANG = {w_ang!r}
W_MU = {w_mu!r}
W_SD = {w_sd!r}
_STATE = {{"cur": -1, "next": -1}}


def select_next_node(current_node, destination_node, unvisited_nodes, distance_matrix):
    """Tuned parametric next-city rule P1 (distance, destination, turn angle, mean/std to unvisited)."""
    D = distance_matrix
    n = D.shape[0]
    U = np.array(sorted(unvisited_nodes), dtype=np.int64)
    c = current_node
    prev = -1
    if len(U) < n - 1 and _STATE["next"] == c:
        prev = _STATE["cur"]
    score = D[c, U] + W_DST * D[U, destination_node]
    if prev >= 0:
        a = D[prev, c]
        b = D[c, U]
        e = D[prev, U]
        cos_alpha = (a * a + b * b - e * e) / (2.0 * a * b + 1e-12)
        score = score + W_ANG * (1.0 + cos_alpha)
    m = len(U)
    if m > 1:
        S = D[np.ix_(U, U)]
        mu = S.sum(axis=1) / (m - 1)
        var = np.maximum((S * S).sum(axis=1) / (m - 1) - mu * mu, 0.0)
        score = score + W_MU * mu + W_SD * np.sqrt(var)
    j = int(U[int(np.argmin(score))])
    _STATE["cur"] = c
    _STATE["next"] = j
    return j
'''


def p1_program(w: dict) -> str:
    return P1_TEMPLATE.format(w_dst=float(w["w_dst"]), w_ang=float(w["w_ang"]), w_mu=float(w["w_mu"]),
                              w_sd=float(w["w_sd"]))


def p1_draw_weights(n: int = 2000, seed: int = 777) -> list[dict]:
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        w_dst, w_mu, w_sd = rng.uniform(-1, 1, 3)
        w_ang = rng.uniform(0, 1)
        out.append({"w_dst": float(w_dst), "w_ang": float(w_ang), "w_mu": float(w_mu), "w_sd": float(w_sd)})
    return out


def p1_tour_fast(D: np.ndarray, w: dict) -> float:
    """In-process replica of the P1 program's tour (same numpy expressions, so identical decisions)."""
    n = D.shape[0]
    unv = set(range(1, n))
    cur, tour = 0, [0]
    st_cur, st_next = -1, -1
    for _ in range(n - 1):
        U = np.array(sorted(unv), dtype=np.int64)
        c = cur
        prev = -1
        if len(U) < n - 1 and st_next == c:
            prev = st_cur
        score = D[c, U] + w["w_dst"] * D[U, 0]
        if prev >= 0:
            a = D[prev, c]
            b = D[c, U]
            e = D[prev, U]
            cos_alpha = (a * a + b * b - e * e) / (2.0 * a * b + 1e-12)
            score = score + w["w_ang"] * (1.0 + cos_alpha)
        m = len(U)
        if m > 1:
            S = D[np.ix_(U, U)]
            mu = S.sum(axis=1) / (m - 1)
            var = np.maximum((S * S).sum(axis=1) / (m - 1) - mu * mu, 0.0)
            score = score + w["w_mu"] * mu + w["w_sd"] * np.sqrt(var)
        j = int(U[int(np.argmin(score))])
        st_cur, st_next = c, j
        tour.append(j)
        unv.remove(j)
        cur = j
    t = np.asarray(tour)
    return float(D[t, np.roll(t, -1)].sum())


# ------------------------------------------------------------------ tour-length references (other interface)
def _closed(t, D) -> float:
    t = np.asarray(t)
    return float(D[t, np.roll(t, -1)].sum())


def insertion_tour(D: np.ndarray, mode: str, seed: int = 0) -> list[int]:
    """nearest / farthest / random / cheapest insertion, starting from city 0."""
    n = len(D)
    rng = np.random.default_rng(seed)
    if mode == "random":
        order = [0] + [int(x) for x in rng.permutation(np.arange(1, n))]
        tour = order[:2]
        for c in order[2:]:
            t = np.asarray(tour)
            nx = np.roll(t, -1)
            k = int(np.argmin(D[t, c] + D[c, nx] - D[t, nx]))
            tour.insert(k + 1, c)
        return tour
    in_tour = np.zeros(n, dtype=bool)
    in_tour[0] = True
    tour = [0]
    dmin = D[0].copy()  # distance of each city to the partial tour
    while len(tour) < n:
        cand = np.where(~in_tour)[0]
        t = np.asarray(tour)
        nx = np.roll(t, -1)
        if mode == "nearest":
            c = int(cand[np.argmin(dmin[cand])])
        elif mode == "farthest":
            c = int(cand[np.argmax(dmin[cand])])
        elif mode == "cheapest":
            inc = D[t][:, cand] + D[cand][:, nx].T - D[t, nx][:, None]  # |t| x |cand|
            if len(tour) == 1:
                inc = 2 * D[0, cand][None, :]
            k, ci = np.unravel_index(int(np.argmin(inc)), inc.shape)
            c = int(cand[ci])
            tour.insert(int(k) + 1, c)
            in_tour[c] = True
            dmin = np.minimum(dmin, D[c])
            continue
        else:
            raise ValueError(mode)
        if len(tour) == 1:
            tour.append(c)
        else:
            k = int(np.argmin(D[t, c] + D[c, nx] - D[t, nx]))
            tour.insert(k + 1, c)
        in_tour[c] = True
        dmin = np.minimum(dmin, D[c])
    return tour


def greedy_edge_tour(D: np.ndarray) -> list[int]:
    """Greedy edge matching: add shortest edges keeping degree <= 2 and no subtours, then close."""
    n = len(D)
    iu = np.triu_indices(n, 1)
    order = np.argsort(D[iu], kind="stable")
    deg = np.zeros(n, dtype=int)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    adj = [[] for _ in range(n)]
    added = 0
    for e in order:
        i, j = int(iu[0][e]), int(iu[1][e])
        if deg[i] >= 2 or deg[j] >= 2:
            continue
        ri, rj = find(i), find(j)
        if ri == rj:
            continue
        parent[ri] = rj
        deg[i] += 1
        deg[j] += 1
        adj[i].append(j)
        adj[j].append(i)
        added += 1
        if added == n - 1:
            break
    ends = [v for v in range(n) if deg[v] < 2]
    if len(ends) == 2:
        a, b = ends
        adj[a].append(b)
        adj[b].append(a)
    tour, prev, cur = [0], -1, 0
    while len(tour) < n:
        nxt = adj[cur][0] if adj[cur][0] != prev else adj[cur][1]
        tour.append(nxt)
        prev, cur = cur, nxt
    return tour


def reference_heuristics(D: np.ndarray) -> dict[str, float]:
    out = {f"{m}_insertion": _closed(insertion_tour(D, m), D) for m in ("nearest", "farthest", "cheapest", "random")}
    out["greedy_edge"] = _closed(greedy_edge_tour(D), D)
    return out
