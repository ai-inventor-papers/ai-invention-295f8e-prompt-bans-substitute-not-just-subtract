#!/usr/bin/env python3
"""Build hidden tests with per-case wall-clock limits, then run gate R0 and the labeller unit tests.

limit_s(case) = max(1.0 s, 10 x the slowest catalogue reference's median time on that case over 5 runs).
R0: every reference passes 100% of its task's tests; every deliberately wrong program fails.
Unit tests: each reference gets its own label from runtime AND AST; hand-written variants
(recursive DFS, list.pop(0) BFS, zero-heuristic A*, ...) get the expected labels; broken programs
never crash the harness. Writes tasks/tests_T*.json and results/r0_gate.json.
"""
from __future__ import annotations

import importlib.util
import json
import multiprocessing as mp
import statistics
import sys
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import RESULTS_DIR, TASKS_DIR, setup_logger  # noqa: E402
from loguru import logger  # noqa: E402

REF_LABEL = {
    "T1_bfs": "bfs", "T1_dfs": "dfs", "T1_bidirectional_bfs": "bidirectional_bfs", "T1_iddfs": "iddfs",
    "T1_astar": "astar", "T1_dijkstra_unit": "dijkstra_unit", "T2_dijkstra": "dijkstra",
    "T2_bellman_ford": "bellman_ford_spfa", "T2_spfa": "bellman_ford_spfa",
    "T2_bidirectional_dijkstra": "bidirectional_dijkstra", "T2_floyd_warshall": "floyd_warshall", "T2_dial": "dial",
}

VARIANTS = {
    "T1": {
        "dfs": '''
import sys
def solve(grid, start, goal):
    sys.setrecursionlimit(10000)
    R, C = len(grid), len(grid[0])
    seen = set()
    path = []
    def go(r, c):
        if not (0 <= r < R and 0 <= c < C) or grid[r][c] != "." or (r, c) in seen:
            return False
        seen.add((r, c)); path.append((r, c))
        if (r, c) == goal:
            return True
        for dr, dc in ((0, 1), (1, 0), (0, -1), (-1, 0)):
            if go(r + dr, c + dc):
                return True
        path.pop()
        return False
    return path if go(*start) else []
''',
        "bfs": '''
def solve(grid, start, goal):
    R, C = len(grid), len(grid[0])
    prev = {start: None}
    q = [start]
    while q:
        cur = q.pop(0)
        if cur == goal:
            out = []
            while cur is not None:
                out.append(cur); cur = prev[cur]
            return out[::-1]
        for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (cur[0] + d[0], cur[1] + d[1])
            if 0 <= n[0] < R and 0 <= n[1] < C and grid[n[0]][n[1]] == "." and n not in prev:
                prev[n] = cur; q.append(n)
    return []
''',
        "dijkstra_unit": '''
import heapq
def solve(grid, start, goal):
    R, C = len(grid), len(grid[0])
    def heuristic(a):
        return 0
    g = {start: 0}; par = {start: None}
    pq = [(heuristic(start), start)]
    while pq:
        f, cur = heapq.heappop(pq)
        if cur == goal:
            out = []
            while cur is not None:
                out.append(cur); cur = par[cur]
            return out[::-1]
        if f > g[cur] + heuristic(cur):
            continue
        for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (cur[0] + d[0], cur[1] + d[1])
            if 0 <= n[0] < R and 0 <= n[1] < C and grid[n[0]][n[1]] == "." and g[cur] + 1 < g.get(n, 10**9):
                g[n] = g[cur] + 1; par[n] = cur
                heapq.heappush(pq, (g[n] + heuristic(n), n))
    return []
''',
    },
    "T2": {
        "dijkstra": '''
def solve(n, edges, s, t):
    INF = float("inf")
    w = [[INF] * n for _ in range(n)]
    for u, v, c in edges:
        w[u][v] = min(w[u][v], c)
    dist = [INF] * n; dist[s] = 0; done = [False] * n
    for _ in range(n):
        u = min((i for i in range(n) if not done[i]), key=lambda i: dist[i], default=None)
        if u is None or dist[u] == INF:
            break
        done[u] = True
        for v in range(n):
            if w[u][v] < INF and dist[u] + w[u][v] < dist[v]:
                dist[v] = dist[u] + w[u][v]
    return -1 if dist[t] == INF else dist[t]
''',
    },
}

BROKEN = {
    "raises": "def solve(*a):\n    raise ValueError('boom')\n",
    "loops": "def solve(*a):\n    while True:\n        pass\n",
    "nosolve": "def other():\n    return 1\n",
    "syntax": "def solve(:\n  pass\n",
}

OFFCAT = {
    "T1": {
        "relaxation_sweeps": '''
def solve(grid, start, goal):
    R, C = len(grid), len(grid[0])
    INF = 10**9
    d = [[INF] * C for _ in range(R)]
    d[goal[0]][goal[1]] = 0
    changed = True
    while changed:
        changed = False
        for r in range(R):
            for c in range(C):
                if grid[r][c] != ".":
                    continue
                for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < R and 0 <= nc < C and d[nr][nc] + 1 < d[r][c]:
                        d[r][c] = d[nr][nc] + 1
                        changed = True
    if d[start[0]][start[1]] >= INF:
        return []
    path = [start]
    r, c = start
    while (r, c) != goal:
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < R and 0 <= nc < C and d[nr][nc] == d[r][c] - 1:
                r, c = nr, nc
                break
        path.append((r, c))
    return path
''',
        "union_find_walk": '''
def solve(grid, start, goal):
    R, C = len(grid), len(grid[0])
    if start == goal:
        return [start]
    INF = 10**9
    dist = {start: 0}
    changed = True
    cells = [(r, c) for r in range(R) for c in range(C) if grid[r][c] == "."]
    while changed:
        changed = False
        for (r, c) in cells:
            best = dist.get((r, c), INF)
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nb = (r + dr, c + dc)
                if nb in dist and dist[nb] + 1 < best:
                    best = dist[nb] + 1
            if best < dist.get((r, c), INF):
                dist[(r, c)] = best
                changed = True
    if goal not in dist:
        return []
    path = [goal]
    cur = goal
    while cur != start:
        r, c = cur
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nb = (r + dr, c + dc)
            if dist.get(nb, INF) == dist[cur] - 1:
                cur = nb
                break
        path.append(cur)
    return path[::-1]
''',
    },
    "T2": {
        "minplus_squaring": '''
def solve(n, edges, s, t):
    INF = float("inf")
    M = [[INF] * n for _ in range(n)]
    for i in range(n):
        M[i][i] = 0
    for u, v, w in edges:
        M[u][v] = min(M[u][v], w)
    steps = 1
    while steps < n:
        P = [[min((M[i][k] + M[k][j] for k in range(n)), default=INF) for j in range(n)] for i in range(n)]
        M = P
        steps *= 2
    return -1 if M[s][t] == INF else int(M[s][t])
''',
        "subdivided_01bfs": '''
from collections import deque
def solve(n, edges, s, t):
    adj = {}
    nxt = n
    for u, v, w in edges:
        if w <= 1:
            adj.setdefault(u, []).append((v, w))
        else:
            prev = u
            for _ in range(w - 1):
                adj.setdefault(prev, []).append((nxt, 1))
                prev = nxt
                nxt += 1
            adj.setdefault(prev, []).append((v, 1))
    dist = {s: 0}
    dq = deque([s])
    while dq:
        x = dq.popleft()
        for y, c in adj.get(x, []):
            nd = dist[x] + c
            if nd < dist.get(y, float("inf")):
                dist[y] = nd
                if c == 0:
                    dq.appendleft(y)
                else:
                    dq.append(y)
    return dist.get(t, -1)
''',
    },
}


def _load_solve(path: str):
    spec = importlib.util.spec_from_file_location(Path(path).stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.solve


def time_reference(args: tuple[str, str, list]) -> dict:
    path, task, cases = args
    sys.setrecursionlimit(10000)
    tm = _load_task(task)
    solve = _load_solve(path)
    med = {}
    for case in cases:
        ts = []
        for _ in range(5):
            a = tm.call_args(case)
            t0 = time.perf_counter()
            solve(*a)
            ts.append(time.perf_counter() - t0)
        med[case["id"]] = statistics.median(ts)
    return {"ref": Path(path).stem, "median": med}


def _load_task(task: str):
    p = TASKS_DIR / ("t1_grid.py" if task == "T1" else "t2_wsp.py")
    spec = importlib.util.spec_from_file_location(f"tm_{task}", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> None:
    setup_logger("build_tests")
    from labeller.label import run_code
    from labeller.ast_rules import ast_label
    from labeller.tracer import runtime_label
    gate = {"R0": {}, "unit_tests": {}, "limit_table": {}}
    reuse = "--reuse-limits" in sys.argv
    for task in ("T1", "T2"):
        tm = _load_task(task)
        tf = TASKS_DIR / f"tests_{task}.json"
        if reuse and tf.exists():
            cases = json.loads(tf.read_text())["cases"]
            gate["limit_table"][task] = {c["id"]: c["limit_s"] for c in cases}
            logger.info(f"{task}: reusing {len(cases)} tests and their limits")
            continue
        cases = tm.generate_tests()
        refs = sorted((TASKS_DIR / "references").glob(f"{task}_*.py"))
        with ProcessPoolExecutor(max_workers=min(6, len(refs)), mp_context=mp.get_context("spawn")) as ex:
            timings = list(ex.map(time_reference, [(str(p), task, cases) for p in refs]))
        for c in cases:
            slow = max(t["median"][c["id"]] for t in timings)
            c["ref_slowest_median_s"] = round(slow, 5)
            c["limit_s"] = round(max(1.0, 10 * slow), 3)
        gate["limit_table"][task] = {c["id"]: c["limit_s"] for c in cases}
        (TASKS_DIR / f"tests_{task}.json").write_text(json.dumps({"task": task, "n": len(cases), "cases": cases}))
        logger.info(f"{task}: {len(cases)} tests; limits: max {max(c['limit_s'] for c in cases):.2f}s; "
                    f"sum {sum(c['limit_s'] for c in cases):.1f}s")
    for task in ("T1", "T2"):
        progs = {p.stem: p.read_text() for p in sorted((TASKS_DIR / "references").glob(f"{task}_*.py"))}
        wrong = {p.stem: p.read_text() for p in sorted((TASKS_DIR / "wrong").glob(f"{task}_*.py"))}
        variants = {f"variant_{k}": v for k, v in VARIANTS[task].items()}
        offcat = {f"offcat_{k}": v for k, v in OFFCAT[task].items()}
        broken = {f"broken_{k}": v for k, v in BROKEN.items()}
        allp = {**progs, **wrong, **variants, **offcat, **broken}
        with ThreadPoolExecutor(max_workers=6) as ex:
            res = dict(zip(allp, ex.map(lambda code: run_code(task, code), allp.values())))
        for name, code in allp.items():
            r = res[name]
            al = ast_label(task, code)
            rt = runtime_label(task, r.get("trace") or {}, al.get("facts"))
            gate["unit_tests"][f"{task}/{name}"] = {"passed": r.get("passed"), "runtime": rt, "ast": al["label"],
                                                    "first_failure": r.get("first_failure"),
                                                    "trace_error": r.get("trace_error")}
        gate["R0"][task] = {
            "references_pass": {n: bool(res[n].get("passed")) for n in progs},
            "wrong_fail": {n: not bool(res[n].get("passed")) for n in wrong},
            "reference_labels_ok": {n: (gate["unit_tests"][f"{task}/{n}"]["runtime"] == REF_LABEL[n]
                                        and gate["unit_tests"][f"{task}/{n}"]["ast"] == REF_LABEL[n]) for n in progs},
            "variants_ok": {n: (gate["unit_tests"][f"{task}/{n}"]["runtime"] == n.split("_", 1)[1]
                                or gate["unit_tests"][f"{task}/{n}"]["ast"] == n.split("_", 1)[1]) for n in variants},
            "broken_handled": {n: not bool(res[n].get("passed")) for n in broken},
        }
        ok = (all(gate["R0"][task]["references_pass"].values()) and all(gate["R0"][task]["wrong_fail"].values())
              and all(gate["R0"][task]["broken_handled"].values()))
        gate["R0"][task]["pass"] = ok
        logger.info(f"R0 {task}: {'PASS' if ok else 'FAIL'}; {json.dumps(gate['R0'][task])}")
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "r0_gate.json").write_text(json.dumps(gate, indent=1))
    for k, v in gate["unit_tests"].items():
        logger.info(f"unit {k}: {v}")


if __name__ == "__main__":
    main()
