#!/usr/bin/env python3
"""The 40 committed probe grids of tracer v9 (plan 1.1; seed 9009). T1 format: list of equal-length strings of '.'
and '#'; sizes 7x7 to 15x15; start and goal free and distinct (and never (0, 1) or (1, 0), which coincide with
direction tuples). Families:
  P01-P08 open fields (goal in each quadrant, then 4 axis-aligned placements)
  P09-P14 U-traps facing the start with the goal behind them (4 rotations) + 2 offset walls with one gap
  P15-P22 perfect mazes (randomised DFS) | P23-P26 braided mazes (perfect + 25% of inner walls removed)
  P27-P32 four-room layouts with doors (start and goal in different rooms; in P27-P30 the doors force a detour of
          >= 4 steps over the Manhattan distance, P31-P32 are unconstrained)
  P33-P36 corridors with dead-end side branches
  P37-P38 goal enclosed by walls (unreachable: forces full component exhaustion)
  P39-P40 open fields with the start at the centre (FIFO vs coordinate tie order within BFS levels)
"""

from __future__ import annotations

import random
from collections import deque
from typing import Any

SEED = 9009
BAD = {(0, 1), (1, 0)}


def bfs_dist(grid: list[str], src: tuple[int, int]) -> dict[tuple[int, int], int]:
    R, C = len(grid), len(grid[0])
    dist = {src: 0}
    q = deque([src])
    while q:
        r, c = q.popleft()
        for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            if 0 <= nr < R and 0 <= nc < C and grid[nr][nc] == "." and (nr, nc) not in dist:
                dist[(nr, nc)] = dist[(r, c)] + 1
                q.append((nr, nc))
    return dist


def _open(n: int) -> list[list[str]]:
    return [["."] * n for _ in range(n)]


def _s(g: list[list[str]]) -> list[str]:
    return ["".join(r) for r in g]


def perfect_maze(n: int, rng: random.Random) -> list[list[str]]:
    g = [["#"] * n for _ in range(n)]
    stack = [(0, 0)]
    g[0][0] = "."
    while stack:
        r, c = stack[-1]
        nb = [(r + dr, c + dc, r + dr // 2, c + dc // 2) for dr, dc in ((-2, 0), (2, 0), (0, -2), (0, 2))
              if 0 <= r + dr < n and 0 <= c + dc < n and g[r + dr][c + dc] == "#"]
        if not nb:
            stack.pop()
            continue
        nr, nc, wr, wc = rng.choice(nb)
        g[wr][wc] = "."
        g[nr][nc] = "."
        stack.append((nr, nc))
    return g


def _far_pair(grid: list[str], rng: random.Random, min_frac: float = 0.6,
              detour: int = 0) -> tuple[tuple[int, int], tuple[int, int]]:
    """A random start and a goal at >= min_frac of the start's eccentricity; with detour > 0 the shortest path must
    exceed the Manhattan distance by >= detour (layouts that force a detour)."""
    free = [(r, c) for r in range(len(grid)) for c in range(len(grid[0])) if grid[r][c] == "." and (r, c) not in BAD]
    for _ in range(400):
        s = rng.choice(free)
        d = bfs_dist(grid, s)
        far = max(d.values())
        cands = [x for x, v in d.items() if v >= min_frac * far and x not in BAD and x != s
                 and v >= abs(x[0] - s[0]) + abs(x[1] - s[1]) + detour]
        if cands:
            return s, rng.choice(sorted(cands))
    raise RuntimeError("no far pair")


def make_probes() -> list[dict[str, Any]]:
    rng = random.Random(SEED)
    P: list[dict[str, Any]] = []

    def add(fam: str, g: list[list[str]] | list[str], s: tuple[int, int], t: tuple[int, int]) -> None:
        grid = _s(g) if isinstance(g[0], list) else list(g)
        assert grid[s[0]][s[1]] == "." and grid[t[0]][t[1]] == "." and s != t and s not in BAD and t not in BAD
        P.append({"name": f"P{len(P) + 1:02d}", "family": fam, "grid": grid, "start": list(s), "goal": list(t)})

    # P01-P08 open fields
    for n, s, t in ((11, (6, 6), (1, 2)), (12, (6, 5), (1, 10)), (13, (5, 5), (11, 12)), (14, (5, 8), (12, 2)),
                    (11, (8, 5), (1, 5)), (12, (2, 6), (10, 6)), (13, (6, 9), (6, 1)), (15, (7, 2), (7, 13))):
        add("open", _open(n), s, t)
    # P09-P14 U-traps (the U opens toward the start; the goal is behind its base) + offset walls
    for rot in range(4):
        n = 15
        g = _open(n)
        for r in range(3, 12):
            g[r][10] = "#"
        for c in range(5, 11):
            g[3][c] = "#"
            g[11][c] = "#"
        s, t = (7, 2), (7, 13)
        for _ in range(rot):                       # rotate the grid and the cells by 90 degrees clockwise
            g = [list(row) for row in zip(*g[::-1])]
            s, t = (s[1], n - 1 - s[0]), (t[1], n - 1 - t[0])
        add("utrap", g, s, t)
    for n, gap_top in ((13, True), (14, False)):
        g = _open(n)
        wc = n // 2
        for r in range(n):
            g[r][wc] = "#"
        gr = 1 if gap_top else n - 2
        g[gr][wc] = "."
        add("wall_gap", g, (n - 2 if gap_top else 1, 2), (n - 2 if gap_top else 1, n - 3))
    # P15-P22 perfect mazes, P23-P26 braided mazes
    for n in (9, 11, 11, 13, 13, 15, 15, 15):
        g = perfect_maze(n, rng)
        s, t = _far_pair(_s(g), rng)
        add("maze", g, s, t)
    for n in (11, 13, 15, 15):
        g = perfect_maze(n, rng)
        walls = [(r, c) for r in range(1, n - 1) for c in range(1, n - 1) if g[r][c] == "#" and
                 ((g[r - 1][c] == "." and g[r + 1][c] == ".") or (g[r][c - 1] == "." and g[r][c + 1] == "."))]
        for r, c in rng.sample(walls, k=max(1, len(walls) // 4)):
            g[r][c] = "."
        s, t = _far_pair(_s(g), rng)
        add("braided", g, s, t)
    # P27-P32 four rooms with doors
    for ri, n in enumerate((11, 12, 13, 13, 14, 15)):
        g = _open(n)
        a, b = rng.randint(n // 3, 2 * n // 3), rng.randint(n // 3, 2 * n // 3)
        for i in range(n):
            g[a][i] = "#"
            g[i][b] = "#"
        for seg in ((0, b), (b + 1, n)):
            d = rng.randrange(*seg)
            g[a][d] = "."
        for seg in ((0, a), (a + 1, n)):
            d = rng.randrange(*seg)
            g[d][b] = "."
        rooms = [[(r, c) for r in range(lo_r, hi_r) for c in range(lo_c, hi_c) if g[r][c] == "." and (r, c) not in BAD]
                 for lo_r, hi_r in ((0, a), (a + 1, n)) for lo_c, hi_c in ((0, b), (b + 1, n))]
        for _ in range(500):                       # start and goal in different rooms; the doors force a detour
            i, j = rng.sample(range(4), 2)
            s0, t0 = rng.choice(rooms[i]), rng.choice(rooms[j])
            dd = bfs_dist(_s(g), s0).get(t0)
            if dd is not None and (ri >= 4 or dd >= abs(s0[0] - t0[0]) + abs(s0[1] - t0[1]) + 4):
                break
        add("rooms", g, s0, t0)
    # P33-P36 corridors with dead-end side branches
    for n in (9, 11, 13, 15):
        g = [["#"] * n for _ in range(n)]
        mid = n // 2
        for c in range(n):
            g[mid][c] = "."
        for c in range(1, n - 1, 2):
            L = rng.randint(1, mid - 1)
            sign = rng.choice((-1, 1))
            for k in range(1, L + 1):
                g[mid + sign * k][c] = "."
            if rng.random() < 0.5 and c + 1 < n - 1:          # a bent branch end
                g[mid + sign * L][c + 1] = "."
        add("corridor", g, (mid, 0), (mid, n - 1))
    # P37-P38 goal enclosed by walls (unreachable)
    for n, t in ((11, (2, 8)), (13, (9, 3))):
        g = _open(n)
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if (dr, dc) != (0, 0):
                    g[t[0] + dr][t[1] + dc] = "#"
        add("unreachable", g, (n - 2, 1) if t[0] < n // 2 else (1, n - 2), t)
    # P39-P40 open fields, start at the centre
    add("open_centre", _open(13), (6, 6), (0, 12))
    add("open_centre", _open(15), (7, 7), (14, 0))
    assert len(P) == 40, len(P)
    for p in P:
        g = p["grid"]
        assert len(g) >= 7 and len(g) <= 15 and all(len(r) == len(g[0]) for r in g)
    return P


def precompute(probe: dict[str, Any]) -> dict[str, Any]:
    g = probe["grid"]
    s, t = tuple(probe["start"]), tuple(probe["goal"])
    return {"d_s": bfs_dist(g, s), "d_t": bfs_dist(g, t), "s": s, "t": t, "R": len(g), "C": len(g[0]),
            "free": {(r, c) for r in range(len(g)) for c in range(len(g[0])) if g[r][c] == "."}}
