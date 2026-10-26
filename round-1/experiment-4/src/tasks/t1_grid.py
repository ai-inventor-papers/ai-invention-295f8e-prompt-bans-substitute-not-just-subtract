#!/usr/bin/env python3
"""T1 grid path search: hidden-test generator, checker and tracer probes (standard library only).

The checker and probe builders are also imported by labeller/runner.py inside the sandbox.
"""
from __future__ import annotations

import random
from collections import deque

SPEC_KEY = "T1"


def bfs_reachable(grid: list[str], start, goal) -> int:
    """Shortest path length in moves, or -1 if unreachable."""
    R, C = len(grid), len(grid[0])
    if tuple(start) == tuple(goal):
        return 0
    dist = {tuple(start): 0}
    q = deque([tuple(start)])
    while q:
        r, c = q.popleft()
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < R and 0 <= nc < C and grid[nr][nc] == "." and (nr, nc) not in dist:
                dist[(nr, nc)] = dist[(r, c)] + 1
                if (nr, nc) == tuple(goal):
                    return dist[(nr, nc)]
                q.append((nr, nc))
    return -1


def _random_grid(rng: random.Random, R: int, C: int, p: float) -> list[list[str]]:
    return [["#" if rng.random() < p else "." for _ in range(C)] for _ in range(R)]


def _maze(rng: random.Random, n: int) -> list[str]:
    """Perfect maze (iterative recursive backtracker) on an n x n grid, n odd; cells at even coords."""
    g = [["#"] * n for _ in range(n)]
    cells = [(r, c) for r in range(0, n, 2) for c in range(0, n, 2)]
    start = (0, 0)
    g[0][0] = "."
    stack, seen = [start], {start}
    while stack:
        r, c = stack[-1]
        nbrs = [(r + dr, c + dc, r + dr // 2, c + dc // 2) for dr, dc in ((2, 0), (-2, 0), (0, 2), (0, -2))
                if 0 <= r + dr < n and 0 <= c + dc < n and (r + dr, c + dc) not in seen]
        if not nbrs:
            stack.pop()
            continue
        nr, nc, wr, wc = rng.choice(nbrs)
        g[wr][wc] = "."
        g[nr][nc] = "."
        seen.add((nr, nc))
        stack.append((nr, nc))
    assert len(seen) == len(cells)
    return ["".join(row) for row in g]


def _spiral(n: int) -> list[str]:
    """Nested square wall rings with alternating gaps: a long spiral-like corridor to the centre."""
    g = [["."] * n for _ in range(n)]
    k, side = 1, 0
    while k < n // 2:
        lo, hi = k, n - 1 - k
        for i in range(lo, hi + 1):
            g[lo][i] = g[hi][i] = g[i][lo] = g[i][hi] = "#"
        gap = [(lo, (lo + hi) // 2), ((lo + hi) // 2, hi), (hi, (lo + hi) // 2), ((lo + hi) // 2, lo)][side % 4]
        g[gap[0]][gap[1]] = "."
        k += 2
        side += 1
    return ["".join(row) for row in g]


def _case(cid: str, kind: str, grid: list[str], start, goal) -> dict:
    assert grid[start[0]][start[1]] == "." and grid[goal[0]][goal[1]] == "."
    d = bfs_reachable(grid, start, goal)
    return {"id": cid, "kind": kind, "args": {"grid": grid, "start": list(start), "goal": list(goal)},
            "reachable": d >= 0, "shortest": d}


def generate_tests(seed: int = 20261019) -> list[dict]:
    rng = random.Random(seed)
    cases = []
    cases.append(_case("t1_single", "1x1 start==goal", ["."], (0, 0), (0, 0)))
    cases.append(_case("t1_row", "1xN corridor", ["." * 25], (0, 0), (0, 24)))
    cases.append(_case("t1_col", "Nx1 corridor", ["."] * 25, (24, 0), (0, 0)))
    cases.append(_case("t1_open30", "open 30x30", ["." * 30] * 30, (0, 0), (29, 29)))
    cases.append(_case("t1_open30_rev", "open 30x30 reversed", ["." * 30] * 30, (29, 0), (0, 29)))
    k = 0
    for p in (0.1, 0.2, 0.3, 0.4):
        for size in (5, 10, 17, 24, 30):
            R = size
            C = max(5, min(30, size + rng.randint(-3, 3)))
            g = _random_grid(rng, R, C, p)
            s = (rng.randrange(R), rng.randrange(C))
            t = (rng.randrange(R), rng.randrange(C))
            while t == s:
                t = (rng.randrange(R), rng.randrange(C))
            g[s[0]][s[1]] = "."
            g[t[0]][t[1]] = "."
            cases.append(_case(f"t1_rand{k}", f"random p={p} {R}x{C}", ["".join(r) for r in g], s, t))
            k += 1
    for n in (15, 29):
        m = _maze(rng, n)
        cases.append(_case(f"t1_maze{n}", f"perfect maze {n}x{n}", m, (0, 0), (n - 1, n - 1)))
    m = _maze(rng, 29)
    cases.append(_case("t1_maze29_mid", "perfect maze 29x29 to middle", m, (0, 28), (14, 14)))
    for n in (21, 29):
        sp = _spiral(n)
        c = n // 2
        goal = (c, c) if sp[c][c] == "." else next((r, cc) for r in range(c - 1, c + 2) for cc in range(c - 1, c + 2)
                                                  if sp[r][cc] == ".")
        cases.append(_case(f"t1_spiral{n}", f"spiral {n}x{n}", sp, (0, 0), goal))
    # unreachable: walled-off goals and separating walls
    for j in range(6):
        R, C = rng.randint(6, 30), rng.randint(6, 30)
        g = _random_grid(rng, R, C, 0.15)
        t = (rng.randint(1, R - 2), rng.randint(1, C - 2))
        if j < 3:
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                g[t[0] + dr][t[1] + dc] = "#"
        else:
            col = rng.randint(2, C - 3)
            for r in range(R):
                g[r][col] = "#"
            t = (rng.randrange(R), rng.randint(col + 1, C - 1))
        s = (rng.randrange(R), rng.randint(0, 1))
        g[s[0]][s[1]] = "."
        g[t[0]][t[1]] = "."
        if j < 3:
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                g[t[0] + dr][t[1] + dc] = "#"
        case = _case(f"t1_unreach{j}", "unreachable", ["".join(r) for r in g], s, t)
        assert not case["reachable"], case["id"]
        cases.append(case)
    cases.append(_case("t1_adjacent", "goal adjacent", ["....", ".##.", "...."], (0, 0), (0, 1)))
    cases.append(_case("t1_adjacent2", "goal adjacent vertical", ["." * 30] * 30, (15, 15), (16, 15)))
    cases.append(_case("t1_same_big", "start==goal large", ["." * 30] * 30, (12, 7), (12, 7)))
    # comb grids (long detours) and dense larger random
    comb = [["."] * 25 for _ in range(25)]
    for c in range(1, 25, 2):
        for r in range(25):
            comb[r][c] = "#"
        comb[0 if (c // 2) % 2 else 24][c] = "."
    cases.append(_case("t1_comb", "comb serpentine 25x25", ["".join(r) for r in comb], (24, 0), (24, 24)))
    for j in range(3):
        g = _random_grid(rng, 30, 30, 0.25)
        g[0][0] = g[29][29] = "."
        cases.append(_case(f"t1_big{j}", "random 30x30 p=0.25", ["".join(r) for r in g], (0, 0), (29, 29)))
    return cases


def check(case: dict, out) -> tuple[bool, str]:
    grid = case["args"]["grid"]
    start, goal = tuple(case["args"]["start"]), tuple(case["args"]["goal"])
    R, C = len(grid), len(grid[0])
    if not case["reachable"]:
        if isinstance(out, (list, tuple)) and len(out) == 0:
            return True, ""
        return False, f"expected [] for unreachable, got {str(out)[:80]}"
    if not isinstance(out, (list, tuple)) or len(out) == 0:
        return False, f"expected a path, got {str(out)[:80]}"
    path = []
    for cell in out:
        if not isinstance(cell, (list, tuple)) or len(cell) != 2:
            return False, f"bad cell {str(cell)[:40]}"
        r, c = cell
        if type(r) is not int or type(c) is not int:  # noqa: E721 - bools/floats are not cells
            return False, f"non-int cell {str(cell)[:40]}"
        if not (0 <= r < R and 0 <= c < C) or grid[r][c] != ".":
            return False, f"cell out of bounds or wall {cell}"
        path.append((r, c))
    if path[0] != start or path[-1] != goal:
        return False, "path does not begin at start and end at goal"
    for (a, b), (x, y) in zip(path, path[1:]):
        if abs(a - x) + abs(b - y) != 1:
            return False, f"non-adjacent step {(a, b)}->{(x, y)}"
    return True, ""


def call_args(case: dict) -> tuple:
    a = case["args"]
    return ([str(r) for r in a["grid"]], tuple(a["start"]), tuple(a["goal"]))


def probes() -> list[dict]:
    """Tracer probes P1-P3 (separate from hidden tests)."""
    p1 = {"id": "P1", "args": {"grid": ["." * 12] * 12, "start": [0, 0], "goal": [11, 11]}}
    g2 = ["." * 8, "#" * 7 + ".", "." * 8, "." * 8, "." * 8, "." * 8]
    p2 = {"id": "P2", "args": {"grid": g2, "start": [0, 0], "goal": [2, 0]}}
    p3 = {"id": "P3", "args": {"grid": ["." * 15] * 15, "start": [7, 2], "goal": [7, 11]}}
    return [p1, p2, p3]
