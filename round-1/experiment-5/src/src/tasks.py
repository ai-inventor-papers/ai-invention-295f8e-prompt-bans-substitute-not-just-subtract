"""Hidden tests (STEP 1.2): seeded generators for T1 (unweighted grid path) and T2 (weighted shortest path),
ground truth (BFS for T1; Dijkstra cross-checked against Floyd-Warshall for T2) and the checkers.

  .venv/bin/python src/tasks.py      -> data/tests/t1.json, data/tests/t2.json (no limits yet; see calibrate.py)
"""
from __future__ import annotations

import heapq
import json
import random
import sys
from collections import deque
from pathlib import Path



# ----------------------------------------------------------------------------------------------- T1 ground truth
def bfs_dist(grid: list[str], start: tuple[int, int], goal: tuple[int, int]) -> int:
    R, C = len(grid), len(grid[0])
    if grid[start[0]][start[1]] != "." or grid[goal[0]][goal[1]] != ".":
        return -1
    dist = {start: 0}
    q = deque([start])
    while q:
        r, c = q.popleft()
        if (r, c) == goal:
            return dist[(r, c)]
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < R and 0 <= nc < C and grid[nr][nc] == "." and (nr, nc) not in dist:
                dist[(nr, nc)] = dist[(r, c)] + 1
                q.append((nr, nc))
    return -1


def check_t1(case: dict, result) -> tuple[bool, str]:
    grid, start, goal = case["grid"], tuple(case["start"]), tuple(case["goal"])
    R, C = len(grid), len(grid[0])
    if not isinstance(result, (list, tuple)):
        return False, f"type {type(result).__name__}"
    if case["expected_dist"] < 0:
        return (len(result) == 0), ("nonempty_for_unreachable" if len(result) else "ok")
    if len(result) == 0:
        return False, "empty_for_reachable"
    try:
        path = [tuple(int(x) for x in cell) for cell in result]
    except (TypeError, ValueError):
        return False, "bad_cell"
    if any(len(p) != 2 for p in path):
        return False, "bad_cell_len"
    if path[0] != start or path[-1] != goal:
        return False, "bad_ends"
    for (r, c) in path:
        if not (0 <= r < R and 0 <= c < C) or grid[r][c] != ".":
            return False, "bad_cell_blocked"
    for a, b in zip(path, path[1:]):
        if abs(a[0] - b[0]) + abs(a[1] - b[1]) != 1:
            return False, "bad_step"
    return True, "ok"


# ----------------------------------------------------------------------------------------------- T1 generators
def _empty(R: int, C: int) -> list[list[str]]:
    return [["."] * C for _ in range(R)]


def _s(g: list[list[str]]) -> list[str]:
    return ["".join(r) for r in g]


def serpentine(n: int) -> list[str]:
    g = _empty(n, n)
    for i, r in enumerate(range(1, n - 1, 2)):
        for c in range(n):
            g[r][c] = "#"
        g[r][n - 1 if i % 2 == 0 else 0] = "."
    return _s(g)


def spiral(n: int) -> list[str]:
    """Concentric wall rings (offsets 1,3,5,...) each with one gap; gaps alternate corners -> long spiral path."""
    g = _empty(n, n)
    k = 0
    o = 1
    while o < n - 1 - o:
        lo, hi = o, n - 1 - o
        for i in range(lo, hi + 1):
            g[lo][i] = g[hi][i] = g[i][lo] = g[i][hi] = "#"
        gaps = [(lo, lo + 1), (hi - 1, hi), (hi, hi - 1), (lo + 1, lo)]
        gr, gc = gaps[k % 4]
        g[gr][gc] = "."
        k += 1
        o += 2
    return _s(g)


def dfs_maze(n: int, rng: random.Random) -> list[str]:
    g = [["#"] * n for _ in range(n)]
    cells = [(r, c) for r in range(1, n - 1, 2) for c in range(1, n - 1, 2)]
    start = cells[0]
    g[start[0]][start[1]] = "."
    seen = {start}
    stack = [start]
    while stack:
        r, c = stack[-1]
        nb = [(r + dr, c + dc) for dr, dc in ((2, 0), (-2, 0), (0, 2), (0, -2))
              if 0 < r + dr < n - 1 and 0 < c + dc < n - 1 and (r + dr, c + dc) not in seen]
        if not nb:
            stack.pop()
            continue
        nr, nc = rng.choice(nb)
        g[(r + nr) // 2][(c + nc) // 2] = "."
        g[nr][nc] = "."
        seen.add((nr, nc))
        stack.append((nr, nc))
    return _s(g)


def random_grid(R: int, C: int, dens: float, rng: random.Random) -> list[str]:
    return ["".join("#" if rng.random() < dens else "." for _ in range(C)) for _ in range(R)]


def _free_cells(grid: list[str]) -> list[tuple[int, int]]:
    return [(r, c) for r, row in enumerate(grid) for c, ch in enumerate(row) if ch == "."]


def _set(grid: list[str], cells: list[tuple[int, int]], ch: str) -> list[str]:
    g = [list(r) for r in grid]
    for r, c in cells:
        g[r][c] = ch
    return _s(g)


def gen_t1(seed: int = 12345) -> list[dict]:
    rng = random.Random(seed)
    cases: list[dict] = []

    def add(name: str, grid: list[str], start, goal) -> None:
        start, goal = tuple(start), tuple(goal)
        grid = _set(grid, [start, goal], ".")
        cases.append({"id": f"t1_{len(cases):02d}_{name}", "grid": grid, "start": list(start), "goal": list(goal),
                      "expected_dist": bfs_dist(grid, start, goal)})

    add("1x1_same", ["."], (0, 0), (0, 0))
    add("5x5_same", _s(_empty(5, 5)), (2, 2), (2, 2))
    add("adjacent", _s(_empty(6, 7)), (3, 3), (3, 4))
    add("corridor_1x30", ["." * 30], (0, 0), (0, 29))
    add("corridor_30x1", ["."] * 30, (29, 0), (0, 0))
    add("open30_corner", _s(_empty(30, 30)), (0, 0), (29, 29))
    add("open30_centre", _s(_empty(30, 30)), (15, 15), (0, 29))
    g = _s(_empty(10, 10))
    g = _set(g, [(4, 5), (6, 5), (5, 4), (5, 6)], "#")
    add("goal_walled_in", g, (0, 0), (5, 5))
    g = _s(_empty(10, 10))
    g = _set(g, [(1, 2), (3, 2), (2, 1), (2, 3)], "#")
    add("start_walled_in", g, (2, 2), (9, 9))
    g = _set(_s(_empty(30, 30)), [(r, 15) for r in range(30)], "#")
    add("split_wall_column", g, (0, 0), (29, 29))
    for n in (15, 21, 29):
        add(f"spiral{n}", spiral(n), (0, 0), (n // 2, n // 2))
    for n in (15, 21, 29):
        add(f"serpentine{n}", serpentine(n), (0, 0), (n - 1, n - 1) if ((n - 2) // 2) % 2 == 0 else (n - 1, 0))
    for n in (11, 15, 21, 29):
        for k in range(2):
            m = dfs_maze(n, rng)
            fc = _free_cells(m)
            if k == 0:
                add(f"dfsmaze{n}_{k}", m, (1, 1), (n - 2, n - 2))
            else:
                add(f"dfsmaze{n}_{k}", m, fc[len(fc) // 2], (1, n - 2))
    n_unreach_random = 0
    for size in (8, 15, 22, 30):
        for dens in (0.10, 0.25, 0.35, 0.45):
            g = random_grid(size, size, dens, rng)
            fc = _free_cells(g) or [(0, 0)]
            s, t = rng.choice(fc), rng.choice(fc)
            if size >= 22 and dens <= 0.25:
                s, t = (0, 0), (size - 1, size - 1)
            add(f"rand{size}_{int(dens * 100)}", g, s, t)
            n_unreach_random += cases[-1]["expected_dist"] < 0
    # four extra random grids, biased to be unreachable so that >= 6 unreachable exist overall
    extra = 0
    while extra < 4:
        size = rng.choice([12, 20, 30])
        g = random_grid(size, size, 0.42, rng)
        fc = _free_cells(g)
        if len(fc) < 2:
            continue
        s, t = rng.choice(fc), rng.choice(fc)
        if s == t:
            continue
        unreachable = bfs_dist(g, s, t) < 0
        if extra < 2 and not unreachable:
            continue
        add(f"rand_extra{size}_{extra}", g, s, t)
        extra += 1
    for R, C in ((5, 30), (30, 5), (12, 25)):
        g = random_grid(R, C, 0.2, rng)
        if R <= C:
            s, t = (rng.randrange(R), 0), (rng.randrange(R), C - 1)
        else:
            s, t = (0, rng.randrange(C)), (R - 1, rng.randrange(C))
        add(f"nonsq{R}x{C}", g, s, t)
    n_unreach = sum(c["expected_dist"] < 0 for c in cases)
    assert n_unreach >= 6, n_unreach
    assert len(cases) >= 44, len(cases)
    return cases


# ----------------------------------------------------------------------------------------------- T2 ground truth
def dijkstra_ref(n: int, edges: list, s: int, t: int) -> int:
    adj = [[] for _ in range(n)]
    for u, v, w in edges:
        adj[u].append((v, w))
    dist = [None] * n
    pq = [(0, s)]
    best = {s: 0}
    while pq:
        d, u = heapq.heappop(pq)
        if dist[u] is not None:
            continue
        dist[u] = d
        for v, w in adj[u]:
            nd = d + w
            if dist[v] is None and nd < best.get(v, 1 << 60):
                best[v] = nd
                heapq.heappush(pq, (nd, v))
    return -1 if dist[t] is None else dist[t]


def fw_ref(n: int, edges: list, s: int, t: int) -> int:
    INF = 1 << 60
    d = [[INF] * n for _ in range(n)]
    for i in range(n):
        d[i][i] = 0
    for u, v, w in edges:
        d[u][v] = min(d[u][v], w)
    for k in range(n):
        dk = d[k]
        for i in range(n):
            di = d[i]
            dik = di[k]
            if dik == INF:
                continue
            for j in range(n):
                if dik + dk[j] < di[j]:
                    di[j] = dik + dk[j]
    return -1 if d[s][t] >= INF else d[s][t]


def check_t2(case: dict, result) -> tuple[bool, str]:
    if isinstance(result, bool) or not isinstance(result, (int, float)):
        return False, f"type {type(result).__name__}"
    return (result == case["expected"]), ("ok" if result == case["expected"] else "wrong_value")


def _rand_graph(n: int, m: int, rng: random.Random, wmax: int = 100) -> list[list[int]]:
    return [[rng.randrange(n), rng.randrange(n), rng.randint(0, wmax)] for _ in range(m)]


def gen_t2(seed: int = 54321) -> list[dict]:
    rng = random.Random(seed)
    cases: list[dict] = []

    def add(name: str, n: int, edges: list, s: int, t: int) -> None:
        edges = [[int(u), int(v), int(w)] for u, v, w in edges]
        e1, e2 = dijkstra_ref(n, edges, s, t), fw_ref(n, edges, s, t)
        assert e1 == e2, (name, e1, e2)
        cases.append({"id": f"t2_{len(cases):02d}_{name}", "n": n, "edges": edges, "s": s, "t": t, "expected": e1})

    add("n1_noedges", 1, [], 0, 0)
    add("n2_noedges", 2, [], 0, 1)
    add("s_eq_t_with_edges", 5, [[0, 1, 3], [1, 2, 4], [2, 0, 1], [3, 4, 2]], 2, 2)
    add("single_edge", 2, [[0, 1, 7]], 0, 1)
    add("zero_weight_path", 5, [[0, 1, 0], [1, 2, 0], [2, 3, 0], [3, 4, 0], [0, 4, 1]], 0, 4)
    add("zero_weight_cycle", 6, [[0, 1, 2], [1, 2, 0], [2, 1, 0], [2, 3, 0], [3, 1, 0], [3, 4, 5], [1, 5, 9], [4, 5, 1]], 0, 5)
    add("self_loops", 4, [[0, 0, 1], [0, 1, 5], [1, 1, 0], [1, 2, 2], [2, 2, 7], [2, 3, 1]], 0, 3)
    add("parallel_edges", 3, [[0, 1, 9], [0, 1, 2], [0, 1, 5], [1, 2, 4], [1, 2, 1], [0, 2, 10]], 0, 2)
    add("heavy_direct_vs_light_hops", 12, [[0, 11, 100]] + [[i, i + 1, 1] for i in range(11)], 0, 11)
    add("bfs_hops_wrong", 6, [[0, 5, 50], [0, 1, 1], [1, 2, 1], [2, 3, 1], [3, 4, 1], [4, 5, 1], [0, 2, 30]], 0, 5)
    add("reverse_only", 5, [[4, 3, 1], [3, 2, 1], [2, 1, 1], [1, 0, 1]], 0, 4)
    add("chain100_reverse_listed", 100, [[i, i + 1, rng.randint(0, 100)] for i in range(98, -1, -1)], 0, 99)
    # random DAG with n=50
    order = list(range(50))
    rng.shuffle(order)
    pos = {v: i for i, v in enumerate(order)}
    dag = []
    for _ in range(150):
        a, b = rng.sample(range(50), 2)
        if pos[a] > pos[b]:
            a, b = b, a
        dag.append([a, b, rng.randint(0, 100)])
    add("dag50", 50, dag, order[0], order[-1])
    for i in range(12):
        n = (20, 50, 100)[i % 3]
        m = rng.randint(2 * n, 3 * n)
        e = _rand_graph(n, m, rng)
        s, t = rng.sample(range(n), 2)
        add(f"sparse{n}_{i}", n, e, s, t)
    for i in range(12):
        n = (30, 60)[i % 2]
        m = min(2000, rng.randint(n * n // 4, n * n // 2))
        e = _rand_graph(n, m, rng)
        s, t = rng.sample(range(n), 2)
        add(f"dense{n}_{i}", n, e, s, t)
    for i in range(5):
        n = 100
        e = [[u, v, 100] for u, v, _ in _rand_graph(n, rng.randint(250, 400), rng)]
        s, t = rng.sample(range(n), 2)
        add(f"allw100_{i}", n, e, s, t)
    k = 0
    while k < 4:
        n = rng.choice([20, 50, 80])
        e = _rand_graph(n, rng.randint(n, 2 * n), rng)
        s, t = rng.sample(range(n), 2)
        # cut every edge into t from the reachable side: drop all edges entering t
        e = [x for x in e if x[1] != t]
        add(f"unreachable{n}_{k}", n, e, s, t)
        assert cases[-1]["expected"] == -1
        k += 1
    assert len(cases) >= 44, len(cases)
    return cases


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from common import TESTS
    t1, t2 = gen_t1(), gen_t2()
    (TESTS / "t1.json").write_text(json.dumps({"task": "t1", "cases": t1}))
    (TESTS / "t2.json").write_text(json.dumps({"task": "t2", "cases": t2}))
    print(f"T1: {len(t1)} cases ({sum(c['expected_dist'] < 0 for c in t1)} unreachable); "
          f"T2: {len(t2)} cases ({sum(c['expected'] < 0 for c in t2)} unreachable)")
