#!/usr/bin/env python3
"""T1: unweighted 4-connected grid path search. Hidden tests (fixed RNG), path checker, BFS oracle."""

from __future__ import annotations

import json
import random
import sys
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import TESTS_DIR, sha256_file  # noqa: E402

SEED = 1019


def bfs_dist(grid: list[str], src: tuple[int, int]) -> dict[tuple[int, int], int]:
    R, C = len(grid), len(grid[0])
    dist = {src: 0}
    q = deque([src])
    while q:
        r, c = q.popleft()
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < R and 0 <= nc < C and grid[nr][nc] == "." and (nr, nc) not in dist:
                dist[(nr, nc)] = dist[(r, c)] + 1
                q.append((nr, nc))
    return dist


def shortest_len(grid, start, goal) -> int | None:
    d = bfs_dist(grid, tuple(start))
    return d.get(tuple(goal))


def maze(h: int, w: int, rng: random.Random) -> list[str]:
    """Recursive-backtracker maze on odd dimensions (cells at odd coordinates)."""
    g = [["#"] * w for _ in range(h)]
    stack = [(1, 1)]
    g[1][1] = "."
    while stack:
        r, c = stack[-1]
        nbrs = [(r + dr, c + dc, r + dr // 2, c + dc // 2) for dr, dc in ((2, 0), (-2, 0), (0, 2), (0, -2))
                if 0 < r + dr < h - 1 and 0 < c + dc < w - 1 and g[r + dr][c + dc] == "#"]
        if not nbrs:
            stack.pop()
            continue
        nr, nc, wr, wc = rng.choice(nbrs)
        g[wr][wc] = "."
        g[nr][nc] = "."
        stack.append((nr, nc))
    return ["".join(row) for row in g]


def random_grid(h: int, w: int, density: float, rng: random.Random) -> list[str]:
    return ["".join("#" if rng.random() < density else "." for _ in range(w)) for _ in range(h)]


def open_cells(grid):
    return [(r, c) for r in range(len(grid)) for c in range(len(grid[0])) if grid[r][c] == "."]


def pick_pair(grid, rng: random.Random, want_reachable: bool | None):
    cells = open_cells(grid)
    for _ in range(500):
        s, g = rng.choice(cells), rng.choice(cells)
        if s == g:
            continue
        reach = shortest_len(grid, s, g) is not None
        if want_reachable is None or reach == want_reachable:
            return s, g
    return None


def make_cases() -> list[dict]:
    rng = random.Random(SEED)
    cases: list[dict] = []

    def add(name, grid, start, goal):
        cases.append(dict(case_id=f"t1_{len(cases):02d}_{name}", grid=grid, start=list(start), goal=list(goal),
                          reachable=shortest_len(grid, start, goal) is not None,
                          shortest=shortest_len(grid, start, goal)))

    # edge cases
    add("1x1", ["."], (0, 0), (0, 0))
    add("row", ["........"], (0, 0), (0, 7))
    add("row_wall", ["...#...."], (0, 0), (0, 7))
    add("col", ["."] * 9, (0, 0), (8, 0))
    add("col_rev", ["."] * 6, (5, 0), (0, 0))
    g = random_grid(12, 12, 0.2, rng)
    g = [row[:5] + "." + row[6:] if i == 5 else row for i, row in enumerate(g)]
    add("start_eq_goal", g, (5, 5), (5, 5))
    # unreachable: walled-off goal and walled-off start region
    g = ["." * 10 for _ in range(10)]
    g = [list(r) for r in g]
    for r, c in ((6, 7), (8, 7), (7, 6), (7, 8)):
        g[r][c] = "#"
    add("goal_walled", ["".join(r) for r in g], (0, 0), (7, 7))
    g = [list("." * 15) for _ in range(15)]
    for r in range(15):
        g[r][4] = "#"
    add("start_region_walled", ["".join(r) for r in g], (3, 1), (10, 12))
    g = [list("." * 20) for _ in range(20)]
    for c in range(20):
        g[9][c] = "#"
    add("split_rows", ["".join(r) for r in g], (2, 2), (17, 15))
    # corridor mazes 15x15 and 29x29
    for k in range(3):
        m = maze(15, 15, rng)
        add(f"maze15_{k}", m, (1, 1), (13, 13))
    for k in range(3):
        m = maze(29, 29, rng)
        add(f"maze29_{k}", m, (1, 1), (27, 27))
    m = maze(29, 29, rng)
    add("maze29_mid", m, (27, 1), (1, 27))
    # random grids 5x5 .. 30x30 at densities 0.0 0.15 0.3 0.45, reachable and unreachable pairs
    sizes = [(5, 5), (8, 12), (12, 8), (15, 15), (20, 20), (25, 18), (30, 30)]
    for dens in (0.0, 0.15, 0.3, 0.45):
        for (h, w) in rng.sample(sizes, 4):
            for _ in range(50):
                grid = random_grid(h, w, dens, rng)
                want = None if dens < 0.3 else rng.random() < 0.6
                pair = pick_pair(grid, rng, want)
                if pair:
                    add(f"rand{h}x{w}_d{int(dens * 100)}", grid, *pair)
                    break
    # extra unreachable random cases (target about 25% unreachable overall)
    while sum(not c["reachable"] for c in cases) < 12:
        h, w = rng.choice(sizes)
        grid = random_grid(h, w, 0.42, rng)
        pair = pick_pair(grid, rng, False)
        if pair:
            add(f"unreach{h}x{w}", grid, *pair)
    # open 30x30 corner to corner (stress case for DFS and IDDFS)
    add("open30_corner", ["." * 30 for _ in range(30)], (0, 0), (29, 29))
    add("open30_corner_rev", ["." * 30 for _ in range(30)], (29, 29), (0, 0))
    # serpentine corridor 30x30 (long single path)
    g = []
    for r in range(29):
        if r % 2 == 0:
            g.append("." * 30)
        elif r % 4 == 1:
            g.append("#" * 29 + ".")
        else:
            g.append("." + "#" * 29)
    g.append("#" * 30)
    assert g[28][29] == "." and g[0][0] == "."
    add("serpentine30", g, (0, 0), (28, 29))
    return cases


def check(case: dict, out) -> tuple[bool, str, bool]:
    """Return (ok, reason, lenient_io)."""
    grid, start, goal = case["grid"], tuple(case["start"]), tuple(case["goal"])
    R, C = len(grid), len(grid[0])
    if not case["reachable"]:
        if out is None:
            return True, "ok_none_lenient", True
        if isinstance(out, (list, tuple)) and len(out) == 0:
            return True, "ok", False
        return False, "expected_empty", False
    if not isinstance(out, (list, tuple)) or len(out) == 0:
        return False, "no_path_for_reachable", False
    path = []
    for cell in out:
        if not isinstance(cell, (list, tuple)) or len(cell) != 2:
            return False, "bad_cell_type", False
        try:
            r, c = int(cell[0]), int(cell[1])
        except (TypeError, ValueError):
            return False, "bad_cell_value", False
        if r != cell[0] or c != cell[1]:
            return False, "non_integer_cell", False
        path.append((r, c))
    if path[0] != start:
        return False, "wrong_start", False
    if path[-1] != goal:
        return False, "wrong_goal", False
    for (r, c) in path:
        if not (0 <= r < R and 0 <= c < C) or grid[r][c] != ".":
            return False, "invalid_cell", False
    for (a, b), (c, d) in zip(path, path[1:]):
        if abs(a - c) + abs(b - d) != 1:
            return False, "non_adjacent_step", False
    return True, "ok", False


def call_args(case: dict):
    return ([str(r) for r in case["grid"]], tuple(case["start"]), tuple(case["goal"]))


def write_cases() -> Path:
    path = TESTS_DIR / "t1_hidden.json"
    path.write_text(json.dumps(make_cases()))
    return path


if __name__ == "__main__":
    p = write_cases()
    cs = json.loads(p.read_text())
    print(len(cs), "cases;", sum(not c["reachable"] for c in cs), "unreachable; sha256", sha256_file(p))
