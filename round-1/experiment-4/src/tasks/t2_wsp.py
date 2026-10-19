#!/usr/bin/env python3
"""T2 weighted shortest path: hidden-test generator, checker and tracer probes (standard library only)."""
from __future__ import annotations

import heapq
import random

SPEC_KEY = "T2"


def dijkstra_ref(n: int, edges, s: int, t: int) -> int:
    adj = [[] for _ in range(n)]
    for u, v, w in edges:
        adj[u].append((v, w))
    dist = [None] * n
    dist[s] = 0
    pq = [(0, s)]
    done = [False] * n
    while pq:
        d, u = heapq.heappop(pq)
        if done[u]:
            continue
        done[u] = True
        if u == t:
            return d
        for v, w in adj[u]:
            nd = d + w
            if dist[v] is None or nd < dist[v]:
                dist[v] = nd
                heapq.heappush(pq, (nd, v))
    return -1 if dist[t] is None else dist[t]


def _rand_graph(rng: random.Random, n: int, m: int, wlo: int = 0, whi: int = 100) -> list[list[int]]:
    return [[rng.randrange(n), rng.randrange(n), rng.randint(wlo, whi)] for _ in range(m)]


def _case(cid: str, kind: str, n: int, edges, s: int, t: int) -> dict:
    return {"id": cid, "kind": kind, "args": {"n": n, "edges": [list(e) for e in edges], "s": s, "t": t},
            "expected": dijkstra_ref(n, [tuple(e) for e in edges], s, t)}


def generate_tests(seed: int = 20261019) -> list[dict]:
    rng = random.Random(seed)
    cases = []
    for n in (1, 2, 3, 5, 10, 20, 50, 100):
        for kind, m in (("sparse", 2 * n), ("dense", max(1, n * n // 4))):
            e = _rand_graph(rng, n, m)
            s, t = rng.randrange(n), rng.randrange(n)
            if n > 1:
                while t == s:
                    t = rng.randrange(n)
            cases.append(_case(f"t2_{kind}{n}", f"{kind} n={n}", n, e, s, t))
    # zero-weight edges and zero-weight cycles
    for j in range(3):
        n = rng.choice((10, 30, 60))
        e = _rand_graph(rng, n, 3 * n, 0, 3)
        cyc = rng.sample(range(n), 5)
        e += [[cyc[i], cyc[(i + 1) % 5], 0] for i in range(5)]
        cases.append(_case(f"t2_zero{j}", "zero weights + zero cycle", n, e, cyc[0], rng.randrange(n)))
    for j in range(2):
        n = 20
        e = _rand_graph(rng, n, 40) + [[v, v, rng.randint(0, 100)] for v in range(n)]
        cases.append(_case(f"t2_self{j}", "self-loops", n, e, 0, n - 1))
    for j in range(2):
        n = 15
        base = _rand_graph(rng, n, 30)
        e = base + [[u, v, max(0, w - rng.randint(0, 50))] for u, v, w in base] + [[u, v, w + 7] for u, v, w in base]
        rng.shuffle(e)
        cases.append(_case(f"t2_parallel{j}", "parallel edges", n, e, 0, n - 1))
    for j in range(3):
        n = rng.choice((10, 40, 100))
        half = n // 2
        e = [[rng.randrange(half), rng.randrange(half), rng.randint(0, 100)] for _ in range(2 * n)]
        e += [[rng.randrange(half, n), rng.randrange(n), rng.randint(0, 100)] for _ in range(n)]  # edges out of 2nd half only
        cases.append(_case(f"t2_unreach{j}", "unreachable t", n, e, 0, n - 1))
    for j in range(2):
        n = rng.choice((7, 50))
        e = _rand_graph(rng, n, 3 * n)
        v = rng.randrange(n)
        cases.append(_case(f"t2_same{j}", "s == t", n, e, v, v))
    chain = [[i, i + 1, rng.randint(0, 100)] for i in range(99)]
    cases.append(_case("t2_chain", "100-node chain", 100, chain, 0, 99))
    cases.append(_case("t2_chain_rev", "100-node chain listed backwards", 100, chain[::-1], 0, 99))
    for j in range(2):
        n = 60
        e = [[rng.randrange(n), rng.randrange(n), 100] for _ in range(400)]
        cases.append(_case(f"t2_maxw{j}", "all weights 100", n, e, 0, rng.randrange(1, n)))
    for j in range(6):
        n = rng.randint(30, 100)
        e = _rand_graph(rng, n, rng.randint(n, 6 * n))
        cases.append(_case(f"t2_mixed{j}", "random mixed", n, e, rng.randrange(n), rng.randrange(n)))
    # long cheap path vs short expensive path (greedy / early-exit traps)
    e = [[0, 9, 100]] + [[i, i + 1, 1] for i in range(9)]
    cases.append(_case("t2_trap", "cheap long path beats direct edge", 10, e, 0, 9))
    return cases


def check(case: dict, out) -> tuple[bool, str]:
    exp = case["expected"]
    if type(out) is bool or not isinstance(out, (int, float)):
        return False, f"non-numeric output {str(out)[:60]}"
    if isinstance(out, float):
        if out != out or out in (float("inf"), float("-inf")) or not out.is_integer():
            return False, f"bad float {out}"
    if int(out) != exp:
        return False, f"expected {exp}, got {out}"
    return True, ""


def call_args(case: dict) -> tuple:
    a = case["args"]
    return (a["n"], [tuple(e) for e in a["edges"]], a["s"], a["t"])


def probes() -> list[dict]:
    """Q1 30-node graph with zero-weight edges; Q2 forces SPFA re-enqueue; Q3 60-node random + reversed chain."""
    rng = random.Random(7)
    q1 = [[rng.randrange(30), rng.randrange(30), rng.choice((0, 0, 1, 2, 5, 9))] for _ in range(90)]
    q1 += [[i, i + 1, 0] for i in range(0, 29, 3)]
    q2 = [[0, 1, 1000], [0, 2, 10], [2, 3, 10], [3, 1, 10], [1, 4, 10], [4, 5, 10], [5, 6, 10]]
    q3 = [[rng.randrange(60), rng.randrange(60), rng.randint(6, 20)] for _ in range(150)]
    q3 += [[i, i + 1, 1] for i in range(59)][::-1]
    return [{"id": "Q1", "args": {"n": 30, "edges": q1, "s": 0, "t": 29}},
            {"id": "Q2", "args": {"n": 7, "edges": q2, "s": 0, "t": 6}},
            {"id": "Q3", "args": {"n": 60, "edges": q3, "s": 0, "t": 59}}]
