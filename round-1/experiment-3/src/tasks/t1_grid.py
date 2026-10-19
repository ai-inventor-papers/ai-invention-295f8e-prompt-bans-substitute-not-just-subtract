"""T1: unweighted grid path. Spec, seeded hidden-test generator, references and validator."""

from __future__ import annotations

import random
from collections import deque

TASK_ID = "T1"
SPEC = (
    "Write a Python function solve(grid, start, goal) that finds a path on a 2-D grid. grid is a list of "
    "equal-length strings in which . is a free cell and # is an obstacle; start and goal are (row, col) tuples. "
    "Moves go up, down, left or right between free cells. Return any valid path as a list of (row, col) tuples "
    "from start to goal inclusive, or [] if the goal is unreachable or either endpoint is blocked. The grid has at "
    "most 30 rows and 30 columns. Use only the Python standard library. Return only one ```python code block "
    "containing the function and its imports."
)

# Catalogue (merged modes). 'other' and 'no_code' complete the outcome space.
CATALOGUE = ["BFS", "DFS", "bidirectional_BFS", "IDDFS", "astar_greedy", "unit_dijkstra"]
BANNED_MODE = "BFS"
CATALOGUE_DEFS = {
    "BFS": "breadth-first search with a FIFO queue (deque.popleft, list.pop(0) or queue.Queue), expanding cells in rings of increasing distance from the start",
    "DFS": "depth-first search with a LIFO stack or recursion (no growing depth limit), following one branch as deep as possible",
    "bidirectional_BFS": "a search with two frontiers grown from start and from goal that meet in the middle",
    "IDDFS": "iterative-deepening depth-first search: repeated depth-limited DFS with a growing depth limit",
    "astar_greedy": "A* or greedy best-first search: a priority queue ordered by a heuristic such as the Manhattan distance to the goal (with or without path cost)",
    "unit_dijkstra": "Dijkstra's algorithm on the grid: a priority queue keyed only by path length / distance from the start (no heuristic)",
    "other": "any other approach (e.g. brute-force enumeration, dynamic programming, flood fill without a queue, wall following)",
}


def free(grid: list[str], cell: tuple[int, int]) -> bool:
    r, c = cell
    return 0 <= r < len(grid) and 0 <= c < len(grid[0]) and grid[r][c] == "."


def bfs_dist(grid: list[str], start: tuple[int, int]) -> dict:
    """Reference BFS distances from start (used by the validator and the tracer)."""
    if not free(grid, start):
        return {}
    dist = {start: 0}
    q = deque([start])
    R, C = len(grid), len(grid[0])
    while q:
        r, c = q.popleft()
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < R and 0 <= nc < C and grid[nr][nc] == "." and (nr, nc) not in dist:
                dist[(nr, nc)] = dist[(r, c)] + 1
                q.append((nr, nc))
    return dist


def reachable(grid: list[str], start, goal) -> bool:
    start, goal = tuple(start), tuple(goal)
    if not free(grid, start) or not free(grid, goal):
        return False
    return goal in bfs_dist(grid, start)


def validate(case: dict, out) -> tuple[bool, str]:
    grid, start, goal = case["grid"], tuple(case["start"]), tuple(case["goal"])
    exp_reach = case["reachable"]
    if not isinstance(out, (list, tuple)):
        return False, f"output is {type(out).__name__}, not a list"
    if not exp_reach:
        return (len(out) == 0, "expected [] (unreachable or blocked)" if len(out) else "ok")
    if len(out) == 0:
        return False, "returned [] but goal is reachable"
    try:
        path = [tuple(int(x) for x in cell) for cell in out]
    except (TypeError, ValueError):
        return False, "cells are not (row, col) pairs"
    if any(len(p) != 2 for p in path):
        return False, "cells are not (row, col) pairs"
    if path[0] != start:
        return False, "path does not start at start"
    if path[-1] != goal:
        return False, "path does not end at goal"
    for p in path:
        if not free(grid, p):
            return False, f"cell {p} is a wall or out of bounds"
    for a, b in zip(path, path[1:]):
        if abs(a[0] - b[0]) + abs(a[1] - b[1]) != 1:
            return False, f"non-adjacent step {a}->{b}"
    return True, "ok"


# ----------------------------------------------------------------------------- generators
def _rand_grid(rng: random.Random, R: int, C: int, dens: float) -> list[str]:
    return ["".join("#" if rng.random() < dens else "." for _ in range(C)) for _ in range(R)]


def _rand_free(rng: random.Random, grid: list[str]) -> tuple[int, int]:
    cells = [(r, c) for r in range(len(grid)) for c in range(len(grid[0])) if grid[r][c] == "."]
    return rng.choice(cells)


def _maze(rng: random.Random, k: int) -> list[str]:
    """Random-DFS maze on a (2k+1) x (2k+1) grid."""
    n = 2 * k + 1
    g = [["#"] * n for _ in range(n)]
    stack = [(1, 1)]
    g[1][1] = "."
    while stack:
        r, c = stack[-1]
        nbrs = [(r + dr, c + dc, r + dr // 2, c + dc // 2) for dr, dc in ((2, 0), (-2, 0), (0, 2), (0, -2))
                if 0 < r + dr < n and 0 < c + dc < n and g[r + dr][c + dc] == "#"]
        if not nbrs:
            stack.pop()
            continue
        nr, nc, wr, wc = rng.choice(nbrs)
        g[wr][wc] = "."
        g[nr][nc] = "."
        stack.append((nr, nc))
    return ["".join(row) for row in g]


def _serpentine(R: int, C: int, flip: bool) -> list[str]:
    g = [["."] * C for _ in range(R)]
    for i, r in enumerate(range(1, R - 1, 2)):
        gap = (C - 1) if (i % 2 == 0) != flip else 0
        for c in range(C):
            if c != gap:
                g[r][c] = "#"
    return ["".join(row) for row in g]


def make_cases(seed: int = 1234) -> list[dict]:
    rng = random.Random(seed)
    cases: list[dict] = []

    def add(name, grid, start, goal):
        cases.append({"name": name, "grid": grid, "start": list(start), "goal": list(goal),
                      "reachable": reachable(grid, start, goal)})

    # 8 edge cases
    add("start_eq_goal", ["....", ".#..", "...."], (1, 2), (1, 2))
    add("start_on_wall", ["....", ".#..", "...."], (1, 1), (2, 3))
    add("goal_on_wall", ["....", ".#..", "...."], (0, 0), (1, 1))
    add("one_by_one", ["."], (0, 0), (0, 0))
    add("corridor_1xN", ["." * 25], (0, 0), (0, 24))
    add("corridor_Nx1", ["."] * 25, (24, 0), (0, 0))
    add("walled_goal", [".....", ".###.", ".#.#.", ".###.", "....."], (0, 0), (2, 2))
    add("enclosed_start", ["###....", "#.#....", "###....", "......."], (1, 1), (3, 6))
    # 12 random grids 10x10..30x30, density 0.10-0.35
    for i in range(12):
        R, C = rng.randint(10, 30), rng.randint(10, 30)
        g = _rand_grid(rng, R, C, rng.uniform(0.10, 0.35))
        s, t = _rand_free(rng, g), _rand_free(rng, g)
        add(f"random_{i}", g, s, t)
    # 6 random-DFS mazes up to 29x29
    for i, k in enumerate([5, 7, 9, 11, 13, 14]):
        g = _maze(rng, k)
        n = len(g)
        add(f"maze_{i}", g, (1, 1), (n - 2, n - 2))
    # 4 open 30x30
    for i in range(4):
        g = ["." * 30] * 30
        add(f"open_{i}", g, (rng.randrange(30), rng.randrange(30)), (rng.randrange(30), rng.randrange(30)))
    # 4 serpentine long-path grids
    for i, (R, C) in enumerate([(29, 29), (30, 30), (27, 30), (30, 25)]):
        g = _serpentine(R, C, flip=bool(i % 2))
        add(f"serpentine_{i}", g, (0, 0), (R - 1, 0 if (len(range(1, R - 1, 2)) % 2 == 0) else C - 1))
    # 6 large unreachable grids (a full wall separates the endpoints)
    for i in range(6):
        g = [list(row) for row in _rand_grid(rng, 30, 30, 0.15)]
        if i % 2 == 0:
            wc = rng.randint(8, 21)
            for r in range(30):
                g[r][wc] = "#"
            s = (rng.randrange(30), rng.randrange(0, wc))
            t = (rng.randrange(30), rng.randrange(wc + 1, 30))
        else:
            wr = rng.randint(8, 21)
            for c in range(30):
                g[wr][c] = "#"
            s = (rng.randrange(0, wr), rng.randrange(30))
            t = (rng.randrange(wr + 1, 30), rng.randrange(30))
        g[s[0]][s[1]] = "."
        g[t[0]][t[1]] = "."
        add(f"unreachable_{i}", ["".join(row) for row in g], s, t)
    # order small -> large so pathological programs fail early on cheap cases
    cases.sort(key=lambda cs: len(cs["grid"]) * len(cs["grid"][0]))
    for i, cs in enumerate(cases):
        cs["idx"] = i
    return cases


def case_args(case: dict) -> tuple:
    return (list(case["grid"]), tuple(case["start"]), tuple(case["goal"]))


# ----------------------------------------------------------------------------- references
REFERENCES: dict[str, tuple[str, str]] = {}

REFERENCES["ref_bfs"] = ("BFS", '''
from collections import deque

def solve(grid, start, goal):
    R, C = len(grid), len(grid[0])
    sr, sc = start
    gr, gc = goal
    if grid[sr][sc] == '#' or grid[gr][gc] == '#':
        return []
    parent = {start: None}
    q = deque([start])
    while q:
        cur = q.popleft()
        if cur == goal:
            path = []
            while cur is not None:
                path.append(cur)
                cur = parent[cur]
            return path[::-1]
        r, c = cur
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < R and 0 <= nc < C and grid[nr][nc] == '.' and (nr, nc) not in parent:
                parent[(nr, nc)] = cur
                q.append((nr, nc))
    return []
''')

REFERENCES["ref_bfs_listpop0"] = ("BFS", '''
def solve(grid, start, goal):
    R, C = len(grid), len(grid[0])
    if grid[start[0]][start[1]] != '.' or grid[goal[0]][goal[1]] != '.':
        return []
    prev = {start: None}
    frontier = [start]
    while frontier:
        cur = frontier.pop(0)
        if cur == goal:
            out = []
            while cur is not None:
                out.append(cur)
                cur = prev[cur]
            return out[::-1]
        for dr, dc in ((0, 1), (1, 0), (0, -1), (-1, 0)):
            nr, nc = cur[0] + dr, cur[1] + dc
            if 0 <= nr < R and 0 <= nc < C and grid[nr][nc] == '.' and (nr, nc) not in prev:
                prev[(nr, nc)] = cur
                frontier.append((nr, nc))
    return []
''')

REFERENCES["ref_dfs_iter"] = ("DFS", '''
def solve(grid, start, goal):
    R, C = len(grid), len(grid[0])
    if grid[start[0]][start[1]] == '#' or grid[goal[0]][goal[1]] == '#':
        return []
    stack = [start]
    parent = {start: None}
    while stack:
        cur = stack.pop()
        if cur == goal:
            path = []
            while cur is not None:
                path.append(cur)
                cur = parent[cur]
            return path[::-1]
        r, c = cur
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < R and 0 <= nc < C and grid[nr][nc] == '.' and (nr, nc) not in parent:
                parent[(nr, nc)] = cur
                stack.append((nr, nc))
    return []
''')

REFERENCES["ref_dfs_rec"] = ("DFS", '''
import sys

def solve(grid, start, goal):
    sys.setrecursionlimit(10000)
    R, C = len(grid), len(grid[0])
    if grid[start[0]][start[1]] == '#' or grid[goal[0]][goal[1]] == '#':
        return []
    seen = set()
    path = []

    def dfs(r, c):
        if (r, c) == goal:
            path.append((r, c))
            return True
        seen.add((r, c))
        path.append((r, c))
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < R and 0 <= nc < C and grid[nr][nc] == '.' and (nr, nc) not in seen:
                if dfs(nr, nc):
                    return True
        path.pop()
        return False

    return path if dfs(start[0], start[1]) else []
''')

REFERENCES["ref_bidir_bfs"] = ("bidirectional_BFS", '''
from collections import deque

def solve(grid, start, goal):
    R, C = len(grid), len(grid[0])
    if grid[start[0]][start[1]] == '#' or grid[goal[0]][goal[1]] == '#':
        return []
    if start == goal:
        return [start]
    par_s = {start: None}
    par_g = {goal: None}
    qs, qg = deque([start]), deque([goal])

    def nbrs(cell):
        r, c = cell
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < R and 0 <= nc < C and grid[nr][nc] == '.':
                yield (nr, nc)

    def build(meet):
        left = []
        cur = meet
        while cur is not None:
            left.append(cur)
            cur = par_s[cur]
        left.reverse()
        cur = par_g[meet]
        while cur is not None:
            left.append(cur)
            cur = par_g[cur]
        return left

    while qs and qg:
        for _ in range(len(qs)):
            cur = qs.popleft()
            for nb in nbrs(cur):
                if nb not in par_s:
                    par_s[nb] = cur
                    if nb in par_g:
                        return build(nb)
                    qs.append(nb)
        for _ in range(len(qg)):
            cur = qg.popleft()
            for nb in nbrs(cur):
                if nb not in par_g:
                    par_g[nb] = cur
                    if nb in par_s:
                        return build(nb)
                    qg.append(nb)
    return []
''')

REFERENCES["ref_iddfs"] = ("IDDFS", '''
def solve(grid, start, goal):
    R, C = len(grid), len(grid[0])
    if grid[start[0]][start[1]] == '#' or grid[goal[0]][goal[1]] == '#':
        return []
    n_free = sum(row.count('.') for row in grid)
    cut = [False]

    def dls(cell, depth, limit, path, best):
        if cell == goal:
            return True
        if depth == limit:
            cut[0] = True
            return False
        r, c = cell
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = r + dr, c + dc
            nxt = (nr, nc)
            if 0 <= nr < R and 0 <= nc < C and grid[nr][nc] == '.':
                if best.get(nxt, 10 ** 9) <= depth + 1:
                    continue
                best[nxt] = depth + 1
                path.append(nxt)
                if dls(nxt, depth + 1, limit, path, best):
                    return True
                path.pop()
        return False

    for limit in range(n_free + 1):
        path = [start]
        cut[0] = False
        if dls(start, 0, limit, path, {start: 0}):
            return path
        if not cut[0]:
            return []
    return []
''')

REFERENCES["ref_astar"] = ("astar_greedy", '''
import heapq

def solve(grid, start, goal):
    R, C = len(grid), len(grid[0])
    if grid[start[0]][start[1]] == '#' or grid[goal[0]][goal[1]] == '#':
        return []

    def h(cell):
        return abs(cell[0] - goal[0]) + abs(cell[1] - goal[1])

    open_heap = [(h(start), 0, start)]
    g = {start: 0}
    came = {start: None}
    while open_heap:
        f, cost, cur = heapq.heappop(open_heap)
        if cur == goal:
            path = []
            while cur is not None:
                path.append(cur)
                cur = came[cur]
            return path[::-1]
        if cost > g[cur]:
            continue
        r, c = cur
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < R and 0 <= nc < C and grid[nr][nc] == '.':
                ng = cost + 1
                if ng < g.get((nr, nc), float('inf')):
                    g[(nr, nc)] = ng
                    came[(nr, nc)] = cur
                    heapq.heappush(open_heap, (ng + h((nr, nc)), ng, (nr, nc)))
    return []
''')

REFERENCES["ref_greedy"] = ("astar_greedy", '''
import heapq

def solve(grid, start, goal):
    R, C = len(grid), len(grid[0])
    if grid[start[0]][start[1]] == '#' or grid[goal[0]][goal[1]] == '#':
        return []
    pq = [(abs(start[0] - goal[0]) + abs(start[1] - goal[1]), start)]
    came = {start: None}
    while pq:
        _, cur = heapq.heappop(pq)
        if cur == goal:
            path = []
            while cur is not None:
                path.append(cur)
                cur = came[cur]
            return path[::-1]
        r, c = cur
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < R and 0 <= nc < C and grid[nr][nc] == '.' and (nr, nc) not in came:
                came[(nr, nc)] = cur
                heapq.heappush(pq, (abs(nr - goal[0]) + abs(nc - goal[1]), (nr, nc)))
    return []
''')

REFERENCES["ref_unit_dijkstra"] = ("unit_dijkstra", '''
import heapq

def solve(grid, start, goal):
    R, C = len(grid), len(grid[0])
    if grid[start[0]][start[1]] == '#' or grid[goal[0]][goal[1]] == '#':
        return []
    dist = {start: 0}
    prev = {start: None}
    pq = [(0, start)]
    while pq:
        d, cur = heapq.heappop(pq)
        if d > dist[cur]:
            continue
        if cur == goal:
            path = []
            while cur is not None:
                path.append(cur)
                cur = prev[cur]
            return path[::-1]
        r, c = cur
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < R and 0 <= nc < C and grid[nr][nc] == '.':
                nd = d + 1
                if nd < dist.get((nr, nc), float('inf')):
                    dist[(nr, nc)] = nd
                    prev[(nr, nc)] = cur
                    heapq.heappush(pq, (nd, (nr, nc)))
    return []
''')

# Programs that are expected to FAIL (validator / limit tests), never part of the catalogue references.
BAD_PROGRAMS: dict[str, str] = {
    "bad_nonadjacent": '''
def solve(grid, start, goal):
    if grid[start[0]][start[1]] == '#' or grid[goal[0]][goal[1]] == '#':
        return []
    return [start, goal] if start != goal else [start]
''',
    "bad_always_empty": '''
def solve(grid, start, goal):
    return []
''',
}
