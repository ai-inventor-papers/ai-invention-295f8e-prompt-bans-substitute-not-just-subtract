#!/usr/bin/env python3
"""Labeller unit tests: runtime and AST rules must give every reference (and its variants) its own label, and
five mutants must get their expected labels. Writes labeller/unit_test_results.json."""
from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tasks"))
sys.path.insert(0, str(ROOT / "labeller"))
from references import REFS  # noqa: E402
from rules import ast_label, runtime_label  # noqa: E402
from tasklib import run_hidden_tests, run_trace  # noqa: E402

MUTANTS = [
    ("t1", "dfs", "bfs_with_pop_is_dfs", REFS["t1"][0][2].replace("q.popleft()", "q.pop()")),
    ("t1", "bfs", "bfs_list_pop0", '''
def solve(grid, start, goal):
    R, C = len(grid), len(grid[0])
    start, goal = tuple(start), tuple(goal)
    queue = [start]
    parent = {start: None}
    while queue:
        cur = queue.pop(0)
        if cur == goal:
            path = []
            while cur is not None:
                path.append(cur)
                cur = parent[cur]
            return path[::-1]
        for dr, dc in ((0, 1), (1, 0), (0, -1), (-1, 0)):
            nr, nc = cur[0] + dr, cur[1] + dc
            if 0 <= nr < R and 0 <= nc < C and grid[nr][nc] == '.' and (nr, nc) not in parent:
                parent[(nr, nc)] = cur
                queue.append((nr, nc))
    return []
'''),
    ("t1", "astar", "astar_path_items", '''
import heapq

def solve(grid, start, goal):
    rows, cols = len(grid), len(grid[0])
    def heuristic(a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])
    open_set = [(heuristic(start, goal), 0, tuple(start), [tuple(start)])]
    visited = set()
    while open_set:
        f, g, node, path = heapq.heappop(open_set)
        if node == tuple(goal):
            return path
        if node in visited:
            continue
        visited.add(node)
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = node[0] + dx, node[1] + dy
            if 0 <= nx < rows and 0 <= ny < cols and grid[nx][ny] == '.' and (nx, ny) not in visited:
                heapq.heappush(open_set, (g + 1 + heuristic((nx, ny), goal), g + 1, (nx, ny), path + [(nx, ny)]))
    return []
'''),
    ("t2", "dijkstra", "dijkstra_resort_list", '''
def solve(n, edges, s, t):
    adj = {}
    for u, v, w in edges:
        adj.setdefault(u, []).append((v, w))
    dist = {s: 0}
    frontier = [(0, s)]
    done = set()
    while frontier:
        frontier.sort()
        d, u = frontier.pop(0)
        if u in done:
            continue
        done.add(u)
        if u == t:
            return d
        for v, w in adj.get(u, []):
            if v not in done and d + w < dist.get(v, float('inf')):
                dist[v] = d + w
                frontier.append((d + w, v))
    return -1
'''),
    ("t2", "bellman_ford_spfa", "spfa_is_bf", REFS["t2"][2][2]),
]


def check(task, expect, name, code):
    tr = run_hidden_tests(code, task)
    trace = run_trace(code, task)
    rl, rc, rev = runtime_label(task, trace)
    al, ac, aev = ast_label(task, code)
    return {"task": task, "name": name, "expect": expect, "runtime": rl, "rt_conf": rc, "ast": al, "ast_conf": ac,
            "passed_tests": tr["passed"], "rt_ev": rev, "ast_ev": {k: v for k, v in aev.items() if k != "recursive"}}


def main() -> None:
    jobs = [(t, lab, var, src) for t in ("t1", "t2") for lab, var, src in REFS[t]]
    jobs += [(t, e, n, c) for t, e, n, c in MUTANTS]
    with ThreadPoolExecutor(6) as ex:
        res = list(ex.map(lambda j: check(*j), jobs))
    ok_all = True
    for r in res:
        ok_rt = r["runtime"] == r["expect"]
        ok_ast = r["ast"] == r["expect"]
        ok_all &= ok_rt and ok_ast
        print(f"{r['task']} {r['name']:<24} expect={r['expect']:<18} runtime={str(r['runtime']):<18}{'OK ' if ok_rt else 'BAD'} "
              f"ast={str(r['ast']):<18}{'OK ' if ok_ast else 'BAD'} tests={r['passed_tests']}  ev={json.dumps(r['rt_ev'])[:300]}")
    (ROOT / "labeller" / "unit_test_results.json").write_text(json.dumps(res, indent=1, default=str))
    print("ALL OK" if ok_all else "SOME FAILURES")


if __name__ == "__main__":
    main()
