#!/usr/bin/env python3
"""T2: directed weighted single-pair shortest path. Hidden tests (fixed RNG), scipy oracle, checker."""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import TESTS_DIR, sha256_file  # noqa: E402

SEED = 2019


def oracle(n: int, edges: list, s: int, t: int) -> int:
    """scipy dijkstra on the graph after keeping the minimum weight of each parallel edge (zero weights kept)."""
    from scipy.sparse.csgraph import csgraph_from_dense, dijkstra
    if s == t:
        return 0
    M = np.full((n, n), np.inf)
    for u, v, w in edges:
        if u != v and w < M[u, v]:
            M[u, v] = w
    G = csgraph_from_dense(M, null_value=np.inf)
    d = dijkstra(G, directed=True, indices=s)[t]
    return -1 if not np.isfinite(d) else int(round(d))


def rand_graph(n: int, m: int, rng: random.Random, wmin: int = 0, wmax: int = 100) -> list:
    return [(rng.randrange(n), rng.randrange(n), rng.randint(wmin, wmax)) for _ in range(m)]


def make_cases() -> list[dict]:
    rng = random.Random(SEED)
    cases: list[dict] = []

    def add(name, n, edges, s, t):
        edges = [list(map(int, e)) for e in edges]
        cases.append(dict(case_id=f"t2_{len(cases):02d}_{name}", n=n, edges=edges, s=s, t=t,
                          expected=oracle(n, edges, s, t)))

    # edge cases
    add("n1", 1, [], 0, 0)
    add("n1_selfloop", 1, [(0, 0, 5)], 0, 0)
    add("s_eq_t", 5, [(0, 1, 3), (1, 2, 4), (2, 0, 1)], 2, 2)
    add("unreachable", 6, [(0, 1, 2), (1, 2, 2), (3, 4, 1), (4, 5, 1)], 0, 5)
    add("unreachable_reverse_only", 4, [(1, 0, 1), (2, 1, 1), (3, 2, 1)], 0, 3)
    add("no_edges", 7, [], 2, 5)
    # zero weights, zero-weight cycles, self-loops, parallel edges
    add("zero_weights", 6, [(0, 1, 0), (1, 2, 0), (2, 3, 5), (0, 3, 6), (3, 4, 0), (4, 5, 0)], 0, 5)
    add("zero_cycle", 5, [(0, 1, 0), (1, 2, 0), (2, 0, 0), (2, 3, 7), (1, 3, 9), (3, 4, 0)], 0, 4)
    add("self_loops", 5, [(0, 0, 3), (0, 1, 4), (1, 1, 0), (1, 2, 2), (2, 2, 9), (2, 4, 1), (0, 4, 10)], 0, 4)
    add("parallel", 4, [(0, 1, 9), (0, 1, 2), (0, 1, 5), (1, 2, 4), (1, 2, 1), (2, 3, 7), (0, 3, 50), (0, 3, 11)],
        0, 3)
    add("zero_heavy_mix", 30, rand_graph(30, 120, rng, 0, 3), 0, 29)
    # DAGs and long chains
    add("chain100", 100, [(i, i + 1, rng.randint(0, 100)) for i in range(99)], 0, 99)
    add("chain100_rev_query", 100, [(i, i + 1, rng.randint(1, 100)) for i in range(99)], 99, 0)
    dag = [(u, v, rng.randint(0, 100)) for u in range(60) for v in range(u + 1, min(60, u + 6))]
    add("dag60", 60, dag, 0, 59)
    dag2 = [(u, v, rng.randint(0, 100)) for u in range(100) for v in rng.sample(range(u + 1, 100), min(3, 99 - u))
            if u < 99]
    add("dag100", 100, dag2, 0, 99)
    # long path that beats a short heavy edge
    add("detour", 50, [(i, i + 1, 1) for i in range(49)] + [(0, 49, 100)], 0, 49)
    # dense n=100 (E ~ 2000) and sparse n=100 (E ~ 200)
    for k in range(3):
        add(f"dense100_{k}", 100, rand_graph(100, 2000, rng), rng.randrange(100), rng.randrange(100))
    for k in range(3):
        add(f"sparse100_{k}", 100, rand_graph(100, 200, rng), rng.randrange(100), rng.randrange(100))
    # random graphs n in {5,20,50,100}
    for n in (5, 20, 50, 100):
        for k in range(4):
            m = rng.choice([n, 2 * n, 4 * n])
            s, t = rng.randrange(n), rng.randrange(n)
            while t == s and n > 1:
                t = rng.randrange(n)
            add(f"rand{n}_{k}", n, rand_graph(n, m, rng), s, t)
    # unreachable random (sparse) graphs
    tries = 0
    while sum(c["expected"] == -1 for c in cases) < 8 and tries < 1000:
        tries += 1
        n = rng.choice([10, 30, 60, 100])
        edges = rand_graph(n, n // 2, rng)
        s, t = rng.randrange(n), rng.randrange(n)
        if s != t and oracle(n, edges, s, t) == -1:
            add(f"unreach{n}", n, edges, s, t)
    # grid-like weighted graph with many equal paths
    edges = []
    for r in range(10):
        for c in range(10):
            u = r * 10 + c
            if c < 9:
                edges.append((u, u + 1, 1))
            if r < 9:
                edges.append((u, u + 10, 1))
    add("grid10_weighted", 100, edges, 0, 99)
    return cases


def check(case: dict, out) -> tuple[bool, str, bool]:
    exp = case["expected"]
    if isinstance(out, bool):
        return False, "bool_output", False
    if isinstance(out, (int, np.integer)) or (isinstance(out, float) and out == int(out)):
        return (int(out) == exp), ("ok" if int(out) == exp else f"wrong_value({int(out)}!={exp})"), \
            isinstance(out, float)
    if isinstance(out, float) and out == float("inf") and exp == -1:
        return False, "inf_instead_of_minus1", False
    return False, f"bad_type({type(out).__name__})", False


def call_args(case: dict):
    return (int(case["n"]), [tuple(e) for e in case["edges"]], int(case["s"]), int(case["t"]))


def write_cases() -> Path:
    path = TESTS_DIR / "t2_hidden.json"
    path.write_text(json.dumps(make_cases()))
    return path


if __name__ == "__main__":
    p = write_cases()
    cs = json.loads(p.read_text())
    print(len(cs), "cases;", sum(c["expected"] == -1 for c in cs), "unreachable; sha256", sha256_file(p))
