"""Frozen probe states for the name-blind behaviour instrument (frozen before COMMIT #1).

For each of the 20 PROBE instances (n_i = round(50 + 150 i/19)): an NN tour and a random-insertion tour
(rng 930100+i), each read in visiting order from city 0. From each tour, 50 prefix lengths t ~ U{1..n-2} are
drawn without replacement (one generator, rng 930200+i, NN tour first). When n-2 < 50 (only i = 0, n = 50: 48
values) all 48 values are taken and the remaining 2 are drawn with replacement (logged deviation).
State = (instance i, current = tour[t-1], destination 0, unvisited = all cities not in tour[:t]).
"""
from __future__ import annotations

import json

import numpy as np

from common import DATA, sha256_file
from tsp_task import SETS, dist_matrix, coords_for

PROBE_STATES_PATH = DATA / "probe_states.json"
N_PER_TOUR = 50


def nn_tour(D: np.ndarray) -> list[int]:
    n = len(D)
    tour, U = [0], np.ones(n, dtype=bool)
    U[0] = False
    cur = 0
    for _ in range(n - 1):
        d = np.where(U, D[cur], np.inf)
        nxt = int(np.argmin(d))
        tour.append(nxt)
        U[nxt] = False
        cur = nxt
    return tour


def random_insertion_tour(D: np.ndarray, rng: np.random.Generator) -> list[int]:
    """Random insertion: cities in random order, each inserted where it lengthens the tour least."""
    n = len(D)
    order = list(rng.permutation(n))
    tour = order[:2]
    for c in order[2:]:
        t = np.asarray(tour)
        nxt = np.roll(t, -1)
        inc = D[t, c] + D[c, nxt] - D[t, nxt]
        k = int(np.argmin(inc))
        tour.insert(k + 1, int(c))
    i0 = tour.index(0)
    return [int(x) for x in tour[i0:] + tour[:i0]]


def _prefix_lengths(rng: np.random.Generator, n: int) -> tuple[list[int], bool]:
    pool = np.arange(1, n - 1)  # 1..n-2
    if len(pool) >= N_PER_TOUR:
        return [int(x) for x in rng.choice(pool, size=N_PER_TOUR, replace=False)], False
    first = [int(x) for x in rng.permutation(pool)]
    extra = [int(x) for x in rng.choice(pool, size=N_PER_TOUR - len(first), replace=True)]
    return first + extra, True


def build_probe_states() -> dict:
    """Returns {'states': [(inst, cur, unvisited_list)], 'meta': [...], 'n': [...], 'sha256': ...}."""
    if PROBE_STATES_PATH.exists():
        obj = json.loads(PROBE_STATES_PATH.read_text())
        obj["sha256"] = sha256_file(PROBE_STATES_PATH)
        return obj
    states, meta, padded = [], [], []
    for i, (seed, n) in enumerate(SETS["probe"]):
        D = dist_matrix(coords_for(seed, n))
        tours = {"nn": nn_tour(D), "ri": random_insertion_tour(D, np.random.default_rng(930100 + i))}
        rng = np.random.default_rng(930200 + i)
        for kind in ("nn", "ri"):
            tour = tours[kind]
            assert tour[0] == 0 and sorted(tour) == list(range(n))
            ts, pad = _prefix_lengths(rng, n)
            if pad:
                padded.append({"instance": i, "tour": kind, "n": n})
            for t in ts:
                prefix = tour[:t]
                unv = sorted(set(range(n)) - set(prefix))
                states.append([i, int(tour[t - 1]), unv])
                meta.append({"instance": i, "tour": kind, "t": t, "n": n})
    obj = {"states": states, "meta": meta, "n": [n for _, n in SETS["probe"]], "padded": padded,
           "rule": __doc__}
    PROBE_STATES_PATH.write_text(json.dumps(obj))
    obj["sha256"] = sha256_file(PROBE_STATES_PATH)
    return obj


def probe_matrices() -> list[np.ndarray]:
    return [dist_matrix(coords_for(seed, n)) for seed, n in SETS["probe"]]


def agreement(a: np.ndarray, b: np.ndarray) -> float:
    """Share of probe states with the same decision (ERR = -1 only matches -1)."""
    return float(np.mean(np.asarray(a) == np.asarray(b)))
