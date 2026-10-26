#!/usr/bin/env python3
"""Seeded hidden-test generators for T1 (grid path) and T2 (weighted shortest path), plus the checkers.

Stdlib only: tasks/sandbox_tests.py imports nothing from here; the generated cases are written to
tasks/<task>/tests.json and the sandbox re-implements the (tiny) checker so it stays self-contained.
"""

from __future__ import annotations

import heapq
import random
from collections import deque
from typing import Any

# ----------------------------------------------------------------------------------------------- T1


def bfs_dist(grid: list[str], src: tuple[int, int]) -> dict[tuple[int, int], int]:
    rows, cols = len(grid), len(grid[0])
    if grid[src[0]][src[1]] == "#":
        return {}
    dist = {src: 0}
    q = deque([src])
    while q:
        r, c = q.popleft()
        for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == "." and (nr, nc) not in dist:
                dist[(nr, nc)] = dist[(r, c)] + 1
                q.append((nr, nc))
    return dist


def perfect_maze(h: int, w: int, rng: random.Random) -> list[str]:
    """DFS-generated perfect maze on an h x w grid (odd h, w): cells at even coordinates."""
    g = [["#"] * w for _ in range(h)]
    stack = [(0, 0)]
    g[0][0] = "."
    while stack:
        r, c = stack[-1]
        nbrs = [(r + dr, c + dc, r + dr // 2, c + dc // 2) for dr, dc in ((-2, 0), (2, 0), (0, -2), (0, 2))
                if 0 <= r + dr < h and 0 <= c + dc < w and g[r + dr][c + dc] == "#"]
        if not nbrs:
            stack.pop()
            continue
        nr, nc, wr, wc = rng.choice(nbrs)
        g[wr][wc] = "."
        g[nr][nc] = "."
        stack.append((nr, nc))
    return ["".join(row) for row in g]


def spiral_maze(n: int = 30) -> list[str]:
    """Concentric walls with alternating gaps: a single long corridor (path length > 400)."""
    g = [["." for _ in range(n)] for _ in range(n)]
    for k in range(1, n // 2, 2):
        lo, hi = k, n - 1 - k
        if lo > hi:
            break
        for i in range(lo, hi + 1):
            g[lo][i] = "#"
            g[hi][i] = "#"
            g[i][lo] = "#"
            g[i][hi] = "#"
        # one gap per ring, alternating sides so the corridor winds
        if (k // 2) % 2 == 0:
            g[lo][lo + 1 if lo + 1 <= hi else lo] = "."
        else:
            g[hi][hi - 1 if hi - 1 >= lo else hi] = "."
    return ["".join(row) for row in g]


def random_grid(h: int, w: int, density: float, rng: random.Random) -> list[str]:
    return ["".join("#" if rng.random() < density else "." for _ in range(w)) for _ in range(h)]


def _t1_case(cid: str, grid: list[str], start: tuple[int, int], goal: tuple[int, int]) -> dict[str, Any]:
    d = bfs_dist(grid, start)
    reachable = goal in d and grid[goal[0]][goal[1]] == "."
    return {"id": cid, "grid": grid, "start": list(start), "goal": list(goal), "reachable": reachable,
            "shortest_len": (d[goal] + 1) if reachable else 0, "size": len(grid) * len(grid[0])}


def t1_cases(seed: int = 20261019) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    cases: list[dict[str, Any]] = []
    cases.append(_t1_case("one_by_one_free", ["."], (0, 0), (0, 0)))
    cases.append(_t1_case("one_by_one_wall", ["#"], (0, 0), (0, 0)))
    cases.append(_t1_case("two_by_two_open", ["..", ".."], (0, 0), (1, 1)))
    cases.append(_t1_case("three_by_three_blocked", [".#.", "##.", "..."], (0, 0), (2, 2)))
    g = random_grid(8, 8, 0.2, rng)
    g = [row[:3] + "." + row[4:] if i == 3 else row for i, row in enumerate(g)]
    cases.append(_t1_case("start_equals_goal", g, (3, 3), (3, 3)))
    cases.append(_t1_case("start_equals_goal_wall", ["...", ".#.", "..."], (1, 1), (1, 1)))
    cases.append(_t1_case("start_wall", ["#....", ".....", "....."], (0, 0), (2, 4)))
    cases.append(_t1_case("goal_wall", [".....", ".....", "....#"], (0, 0), (2, 4)))
    cases.append(_t1_case("unreachable_walled_region", ["....#....", "....#....", "....#....", "....#...."],
                          (0, 0), (3, 8)))
    cases.append(_t1_case("unreachable_enclosed_goal", [".......", ".###...", ".#.#...", ".###...", "......."],
                          (0, 0), (2, 2)))
    cases.append(_t1_case("corridor_1x30", ["." * 30], (0, 0), (0, 29)))
    cases.append(_t1_case("corridor_30x1", ["."] * 30, (29, 0), (0, 0)))
    cases.append(_t1_case("corridor_1x30_reverse", ["." * 30], (0, 29), (0, 3)))
    open30 = ["." * 30] * 30
    cases.append(_t1_case("open_30x30_corner", open30, (0, 0), (29, 29)))
    cases.append(_t1_case("open_30x30_centre", open30, (15, 15), (0, 29)))
    cases.append(_t1_case("open_30x30_adjacent", open30, (10, 10), (10, 11)))
    for density in (0.1, 0.2, 0.3, 0.4):
        made = 0
        while made < 6:
            h, w = rng.randint(10, 30), rng.randint(10, 30)
            grid = random_grid(h, w, density, rng)
            free = [(r, c) for r in range(h) for c in range(w) if grid[r][c] == "."]
            if len(free) < 2:
                continue
            s, t = rng.sample(free, 2)
            cases.append(_t1_case(f"random_d{int(density * 100)}_{made}", grid, s, t))
            made += 1
    for k in range(4):
        mz = perfect_maze(29, 29, rng)
        cases.append(_t1_case(f"maze_29x29_{k}", mz, (0, 0), (28, 28)))
    cases.append(_t1_case("maze_15x15", perfect_maze(15, 15, rng), (14, 14), (0, 0)))
    cases.append(_t1_case("maze_21x21", perfect_maze(21, 21, rng), (0, 20), (20, 0)))
    sp = spiral_maze(30)
    d = bfs_dist(sp, (0, 0))
    far = max(d, key=lambda k: d[k])
    cases.append(_t1_case("spiral_30x30", sp, (0, 0), far))
    comb = ["." * 30] + [("." + "#" * 28 + ".") if i % 2 else "." * 30 for i in range(1, 29)] + ["." * 30]
    cases.append(_t1_case("comb_30x30", comb, (0, 0), (29, 29)))
    cases.sort(key=lambda c: (c["size"], c["id"]))
    return cases


def check_t1(case: dict[str, Any], out: Any) -> tuple[bool, str]:
    grid = case["grid"]
    start = tuple(case["start"])
    goal = tuple(case["goal"])
    rows, cols = len(grid), len(grid[0])
    if not isinstance(out, (list, tuple)):
        return False, f"returned {type(out).__name__}"
    if not case["reachable"]:
        return (len(out) == 0, "expected []" if out else "ok")
    if len(out) == 0:
        return False, "returned [] for a reachable goal"
    try:
        path = [(int(p[0]), int(p[1])) for p in out]
        if any(len(p) != 2 for p in out):
            return False, "cell not a pair"
    except (TypeError, ValueError, IndexError):
        return False, "cells not (row, col) pairs"
    if path[0] != start or path[-1] != goal:
        return False, "wrong endpoints"
    for (r, c) in path:
        if not (0 <= r < rows and 0 <= c < cols) or grid[r][c] != ".":
            return False, "cell out of bounds or wall"
    for (a, b), (c, d) in zip(path, path[1:]):
        if abs(a - c) + abs(b - d) != 1:
            return False, "non-adjacent step"
    return True, "ok"


# ----------------------------------------------------------------------------------------------- T2


def dijkstra_ref(n: int, edges: list[tuple[int, int, int]], s: int, t: int) -> int:
    adj: list[list[tuple[int, int]]] = [[] for _ in range(n)]
    for u, v, w in edges:
        adj[u].append((v, w))
    dist = [float("inf")] * n
    dist[s] = 0
    pq = [(0, s)]
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist[u]:
            continue
        for v, w in adj[u]:
            if d + w < dist[v]:
                dist[v] = d + w
                heapq.heappush(pq, (d + w, v))
    return int(dist[t]) if dist[t] != float("inf") else -1


def bellman_ref(n: int, edges: list[tuple[int, int, int]], s: int, t: int) -> int:
    dist = [float("inf")] * n
    dist[s] = 0
    for _ in range(n):
        for u, v, w in edges:
            if dist[u] + w < dist[v]:
                dist[v] = dist[u] + w
    return int(dist[t]) if dist[t] != float("inf") else -1


def random_graph(n: int, m: int, rng: random.Random, wlo: int = 0, whi: int = 100) -> list[tuple[int, int, int]]:
    return [(rng.randrange(n), rng.randrange(n), rng.randint(wlo, whi)) for _ in range(m)]


def _t2_case(cid: str, n: int, edges: list[tuple[int, int, int]], s: int, t: int) -> dict[str, Any]:
    exp = dijkstra_ref(n, edges, s, t)
    assert exp == bellman_ref(n, edges, s, t), cid
    return {"id": cid, "n": n, "edges": [list(e) for e in edges], "s": s, "t": t, "expected": exp,
            "size": n + len(edges)}


def t2_cases(seed: int = 20261020) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    cases: list[dict[str, Any]] = []
    cases.append(_t2_case("n1_no_edges", 1, [], 0, 0))
    cases.append(_t2_case("n1_self_loop", 1, [(0, 0, 5)], 0, 0))
    cases.append(_t2_case("s_equals_t", 6, [(0, 1, 3), (1, 2, 4), (2, 0, 1), (3, 4, 2)], 2, 2))
    cases.append(_t2_case("unreachable_small", 4, [(0, 1, 1), (2, 3, 1)], 0, 3))
    cases.append(_t2_case("unreachable_reverse_edge", 3, [(1, 0, 4), (2, 1, 4)], 0, 2))
    cases.append(_t2_case("no_edges_two_nodes", 2, [], 0, 1))
    cases.append(_t2_case("zero_weight_chain", 5, [(0, 1, 0), (1, 2, 0), (2, 3, 0), (3, 4, 0)], 0, 4))
    cases.append(_t2_case("zero_weight_cycle", 5, [(0, 1, 0), (1, 2, 0), (2, 0, 0), (2, 3, 7), (1, 3, 9),
                                                   (3, 4, 0)], 0, 4))
    cases.append(_t2_case("self_loops", 4, [(0, 0, 1), (0, 1, 5), (1, 1, 0), (1, 2, 5), (2, 2, 3), (2, 3, 5)], 0, 3))
    cases.append(_t2_case("parallel_edges", 3, [(0, 1, 50), (0, 1, 7), (0, 1, 30), (1, 2, 9), (1, 2, 2),
                                                (0, 2, 100)], 0, 2))
    cases.append(_t2_case("parallel_edges_zero", 3, [(0, 1, 3), (0, 1, 0), (1, 2, 4), (1, 2, 0)], 0, 2))
    chain = [(i, i + 1, rng.randint(1, 100)) for i in range(99)]
    cases.append(_t2_case("chain_99_reverse_order", 100, list(reversed(chain)), 0, 99))
    chain100 = [(i, i + 1, 100) for i in range(99)]
    cases.append(_t2_case("chain_all_weight_100", 100, list(reversed(chain100)), 0, 99))
    cases.append(_t2_case("chain_all_weight_100_shortcut_heavy", 100, chain100 + [(0, 99, 100)], 0, 99))
    # few heavy edges vs many light edges: fewest-edges answer is wrong
    for k in range(4):
        n = 30 + k * 20
        light = [(i, i + 1, 1) for i in range(n - 1)]
        heavy = [(0, n - 1, n + 5 + k), (0, n // 2, n), (n // 2, n - 1, n)]
        extra = random_graph(n, 2 * n, rng, 50, 100)
        cases.append(_t2_case(f"heavy_vs_light_{k}", n, heavy + light + extra, 0, n - 1))
    cases.append(_t2_case("diamond_trap", 4, [(0, 1, 1), (1, 3, 100), (0, 2, 50), (2, 3, 1)], 0, 3))
    cases.append(_t2_case("relax_later_bf_order", 5, [(3, 4, 1), (2, 3, 1), (1, 2, 1), (0, 1, 1), (0, 4, 10)], 0, 4))
    for k in range(8):
        n = 100
        e = random_graph(n, 600, rng)
        s, t = rng.randrange(n), rng.randrange(n)
        while t == s:
            t = rng.randrange(n)
        cases.append(_t2_case(f"dense_random_{k}", n, e, s, t))
    for k in range(6):
        n = 100
        e = random_graph(n, 150, rng)
        s, t = rng.randrange(n), rng.randrange(n)
        while t == s:
            t = rng.randrange(n)
        cases.append(_t2_case(f"sparse_random_{k}", n, e, s, t))
    for k in range(4):
        n = rng.randint(10, 60)
        e = random_graph(n, rng.randint(n, min(600, n * 6)), rng, 0, 10)
        cases.append(_t2_case(f"small_weights_random_{k}", n, e, 0, n - 1))
    for k in range(3):
        n = 100
        e = [(rng.randrange(n), rng.randrange(n), rng.choice([0, 0, 0, 1, 100])) for _ in range(600)]
        cases.append(_t2_case(f"zero_heavy_mix_{k}", n, e, 0, n - 1))
    # layered grid-like graph with many equal-length paths
    n = 100
    e = []
    for i in range(10):
        for j in range(10):
            u = i * 10 + j
            if j < 9:
                e.append((u, u + 1, rng.randint(1, 9)))
            if i < 9:
                e.append((u, u + 10, rng.randint(1, 9)))
    cases.append(_t2_case("layered_grid_100", n, e, 0, 99))
    cases.append(_t2_case("star_out", 50, [(0, i, i) for i in range(1, 50)], 0, 49))
    cases.append(_t2_case("star_in_unreachable", 50, [(i, 0, i) for i in range(1, 50)], 0, 49))
    cases.append(_t2_case("max_edges_complete_small", 25, [(u, v, rng.randint(0, 100)) for u in range(25)
                                                           for v in range(25)][:600], 3, 17))
    cases.sort(key=lambda c: (c["size"], c["id"]))
    return cases


def check_t2(case: dict[str, Any], out: Any) -> tuple[bool, str]:
    if isinstance(out, bool):
        return False, "returned bool"
    if isinstance(out, int):
        return (out == case["expected"], "ok" if out == case["expected"] else f"got {out}")
    if isinstance(out, float):
        if out != out or out in (float("inf"), float("-inf")):
            return False, f"got {out}"
        return (out == case["expected"], "ok" if out == case["expected"] else f"got {out}")
    return False, f"returned {type(out).__name__}"
