#!/usr/bin/env python3
"""Hidden tests, probe inputs and the sandboxed runner for T1 (grid path) and T2 (weighted shortest path).

Run directly to (re)build tasks/hidden_tests_t{1,2}.json: generates >= 40 cases per task, times every
catalogue reference (3 runs, all must pass 3/3), sets per-test limits = max(1 s, 10 x slowest reference),
and checks that the deliberately wrong programs fail.
"""
from __future__ import annotations

import heapq
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import time
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TASK_DIR = ROOT / "tasks"
HARNESS = TASK_DIR / "harness.py"
SANDBOX = ROOT / "sandbox"
PY = sys.executable

# ------------------------------------------------------------------------------------------ T1 generators


def bfs_dist(grid: list[str], start: tuple[int, int]) -> dict[tuple[int, int], int]:
    R, C = len(grid), len(grid[0])
    d = {tuple(start): 0}
    q = deque([tuple(start)])
    while q:
        r, c = q.popleft()
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < R and 0 <= nc < C and grid[nr][nc] == "." and (nr, nc) not in d:
                d[(nr, nc)] = d[(r, c)] + 1
                q.append((nr, nc))
    return d


def _free_cells(grid):
    return [(r, c) for r in range(len(grid)) for c in range(len(grid[0])) if grid[r][c] == "."]


def _random_grid(rng, R, C, p):
    g = [["#" if rng.random() < p else "." for _ in range(C)] for _ in range(R)]
    return g


def _maze(rng, R, C):
    """Recursive-backtracker maze on an R x C grid (odd cells are rooms)."""
    g = [["#"] * C for _ in range(R)]
    sr, sc = 0, 0
    g[sr][sc] = "."
    stack = [(sr, sc)]
    while stack:
        r, c = stack[-1]
        nbrs = [(r + dr, c + dc, r + dr // 2, c + dc // 2) for dr, dc in ((2, 0), (-2, 0), (0, 2), (0, -2))
                if 0 <= r + dr < R and 0 <= c + dc < C and g[r + dr][c + dc] == "#"]
        if not nbrs:
            stack.pop()
            continue
        nr, nc, wr, wc = rng.choice(nbrs)
        g[wr][wc] = "."
        g[nr][nc] = "."
        stack.append((nr, nc))
    return g


def _t1_case(grid_rows, start, goal, name):
    grid = ["".join(r) if not isinstance(r, str) else r for r in grid_rows]
    d = bfs_dist(grid, start)
    return {"name": name, "args": [grid, list(start), list(goal)], "reachable": tuple(goal) in d,
            "shortest": d.get(tuple(goal), -1)}


def build_t1_tests(seed: int = 1) -> list[dict]:
    rng = random.Random(seed)
    T = []
    T.append(_t1_case(["."], (0, 0), (0, 0), "1x1"))
    g = ["." * 7 for _ in range(5)]
    T.append(_t1_case(g, (2, 3), (2, 3), "start_eq_goal"))
    g = [list("." * 8) for _ in range(8)]
    for r, c in ((5, 6), (6, 5), (6, 7), (7, 6)):
        g[r][c] = "#"
    T.append(_t1_case(g, (0, 0), (6, 6), "unreachable_walled_goal"))
    g = [list("." * 10) for _ in range(10)]
    for c in range(10):
        g[5][c] = "#"
    T.append(_t1_case(g, (0, 0), (9, 9), "unreachable_split"))
    # snake corridor
    R, C = 15, 15
    g = [["#"] * C for _ in range(R)]
    for r in range(0, R, 2):
        for c in range(C):
            g[r][c] = "."
        if r + 1 < R:
            g[r + 1][C - 1 if (r // 2) % 2 == 0 else 0] = "."
    T.append(_t1_case(g, (0, 0), (R - 1, 0 if ((R - 1) // 2) % 2 == 1 else C - 1), "snake_corridor"))
    T.append(_t1_case(["." * 30 for _ in range(30)], (0, 0), (29, 29), "open_30x30"))
    T.append(_t1_case(["." * 30 for _ in range(30)], (15, 15), (0, 29), "open_30x30_center"))
    T.append(_t1_case(["." * 30], (0, 0), (0, 29), "single_row"))
    T.append(_t1_case(["."] * 30, (29, 0), (0, 0), "single_column"))
    T.append(_t1_case(["....#....", "....#....", "........."], (0, 0), (0, 8), "single_row_detour"))
    T.append(_t1_case(["." * 30 for _ in range(3)], (1, 0), (1, 29), "wide_3x30"))
    # U-shaped detour that defeats greedy
    R, C = 20, 20
    g = [["."] * C for _ in range(R)]
    for r in range(3, 17):
        g[r][14] = "#"
    for c in range(5, 15):
        g[3][c] = "#"
        g[16][c] = "#"
    T.append(_t1_case(g, (10, 2), (10, 18), "u_detour"))
    R, C = 25, 25
    g = [["."] * C for _ in range(R)]
    for r in range(0, 22):
        g[r][12] = "#"
    T.append(_t1_case(g, (0, 0), (0, 24), "long_wall_detour"))
    # carved mazes
    for i, (R, C) in enumerate([(15, 15), (21, 21), (29, 29), (29, 15), (11, 29), (25, 25), (9, 9), (29, 29)]):
        g = _maze(rng, R, C)
        free = _free_cells(g)
        a, b = rng.sample(free, 2)
        T.append(_t1_case(g, (0, 0), b if i % 2 else (R - 1 if (R - 1) % 2 == 0 else R - 2, C - 1 if (C - 1) % 2 == 0 else C - 2), f"maze_{i}"))
    # random walls 20-40% at sizes 5..30
    sizes = [5, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 30, 30, 7, 13, 19, 25]
    for i, s in enumerate(sizes):
        p = 0.2 + 0.2 * (i % 5) / 4
        Rr, Cc = s, max(5, s - (i % 3) * 2)
        g = _random_grid(rng, Rr, Cc, p)
        free = _free_cells(g)
        if len(free) < 2:
            g[0][0] = "."
            g[Rr - 1][Cc - 1] = "."
            free = _free_cells(g)
        a, b = rng.sample(free, 2)
        T.append(_t1_case(g, a, b, f"random_{s}x{Cc}_p{p:.2f}_{i}"))
    return T


# ------------------------------------------------------------------------------------------ T2 generators


def dijkstra_ref(n, edges, s, t):
    adj = [[] for _ in range(n)]
    for u, v, w in edges:
        adj[u].append((v, w))
    dist = [None] * n
    dist[s] = 0
    h = [(0, s)]
    done = [False] * n
    while h:
        d, u = heapq.heappop(h)
        if done[u]:
            continue
        done[u] = True
        for v, w in adj[u]:
            if dist[v] is None or d + w < dist[v]:
                dist[v] = d + w
                heapq.heappush(h, (d + w, v))
    return -1 if dist[t] is None else dist[t]


def floyd_ref(n, edges, s, t):
    INF = float("inf")
    d = [[INF] * n for _ in range(n)]
    for i in range(n):
        d[i][i] = 0
    for u, v, w in edges:
        d[u][v] = min(d[u][v], w)
    for k in range(n):
        for i in range(n):
            if d[i][k] == INF:
                continue
            for j in range(n):
                if d[i][k] + d[k][j] < d[i][j]:
                    d[i][j] = d[i][k] + d[k][j]
    return -1 if d[s][t] == INF else d[s][t]


def _t2_case(n, edges, s, t, name):
    exp = dijkstra_ref(n, edges, s, t)
    if n <= 100:
        assert floyd_ref(n, edges, s, t) == exp, f"reference disagreement on {name}"
    return {"name": name, "args": [n, [list(e) for e in edges], s, t], "expected": exp}


def build_t2_tests(seed: int = 2) -> list[dict]:
    rng = random.Random(seed)
    T = []
    T.append(_t2_case(1, [], 0, 0, "n1_s_eq_t"))
    T.append(_t2_case(5, [(0, 1, 3), (1, 2, 4), (2, 0, 1)], 2, 2, "s_eq_t_cycle"))
    T.append(_t2_case(4, [(0, 1, 5), (2, 3, 1)], 0, 3, "unreachable"))
    T.append(_t2_case(3, [(1, 0, 4), (2, 1, 4)], 0, 2, "unreachable_reverse_edges"))
    T.append(_t2_case(4, [(0, 1, 0), (1, 2, 0), (2, 3, 0)], 0, 3, "zero_chain"))
    T.append(_t2_case(4, [(0, 1, 0), (1, 0, 0), (1, 2, 7), (2, 1, 0), (2, 3, 1)], 0, 3, "zero_cycle"))
    T.append(_t2_case(3, [(0, 0, 5), (0, 1, 2), (1, 1, 0), (1, 2, 2)], 0, 2, "self_loops"))
    T.append(_t2_case(3, [(0, 1, 9), (0, 1, 3), (0, 1, 7), (1, 2, 5), (1, 2, 1)], 0, 2, "parallel_edges"))
    T.append(_t2_case(5, [(0, 1, 100), (1, 2, 100), (0, 2, 250), (2, 3, 0), (3, 4, 100)], 0, 4, "max_weights"))
    T.append(_t2_case(2, [(0, 1, 0)], 0, 1, "single_zero_edge"))
    T.append(_t2_case(6, [(0, 1, 1), (1, 2, 1), (0, 2, 5), (2, 3, 1), (3, 1, 0), (3, 4, 2), (4, 5, 1), (1, 5, 10)],
                      0, 5, "cycle_mixed"))
    # sparse chains / long paths
    for n in (10, 50, 100):
        edges = [(i, i + 1, rng.randint(0, 100)) for i in range(n - 1)]
        T.append(_t2_case(n, edges, 0, n - 1, f"chain_{n}"))
    edges = [(i, i + 1, 100) for i in range(99)]
    T.append(_t2_case(100, edges, 0, 99, "chain_100_max"))
    edges = [(i + 1, i, 1) for i in range(99)] + [(i, i + 1, 100) for i in range(99)]
    T.append(_t2_case(100, edges, 0, 99, "bidirectional_chain"))
    # DAGs
    for i, (n, m) in enumerate([(20, 60), (50, 200), (100, 600)]):
        edges = []
        for _ in range(m):
            u = rng.randrange(n - 1)
            v = rng.randrange(u + 1, n)
            edges.append((u, v, rng.randint(0, 100)))
        T.append(_t2_case(n, edges, 0, n - 1, f"dag_{i}"))
    # random graphs
    for i in range(18):
        n = rng.choice([2, 3, 5, 8, 12, 20, 30, 45, 60, 80, 100])
        m = rng.randint(0, min(1000, n * n * 2))
        m = min(m, rng.choice([n, 2 * n, 4 * n, 10 * n, 1000]))
        edges = [(rng.randrange(n), rng.randrange(n), rng.choice([0, rng.randint(0, 100), rng.randint(1, 10)]))
                 for _ in range(m)]
        s, t = rng.randrange(n), rng.randrange(n)
        T.append(_t2_case(n, edges, s, t, f"random_{i}_n{n}_m{m}"))
    # long shortest path hidden behind cheap-looking short paths (defeats greedy / hop-count BFS)
    n = 60
    edges = [(i, i + 1, 1) for i in range(n - 1)] + [(0, n - 1, 100), (0, n // 2, 90)]
    T.append(_t2_case(n, edges, 0, n - 1, "many_hops_cheaper"))
    # dense n=100, m=1000
    for i in range(4):
        n = 100
        edges = [(rng.randrange(n), rng.randrange(n), rng.randint(0, 100)) for _ in range(1000)]
        T.append(_t2_case(n, edges, rng.randrange(n), rng.randrange(n), f"dense_{i}"))
    return T


# ------------------------------------------------------------------------------------------ probe inputs


def probes(task: str) -> list[dict]:
    if task == "t1":
        p1 = {"name": "T1-P1_open9", "args": [["." * 9 for _ in range(9)], [0, 0], [8, 8]]}
        g = [list("." * 9) for _ in range(9)]
        for r in range(1, 8):
            g[r][5] = "#"
        for c in range(2, 6):
            g[1][c] = "#"
            g[7][c] = "#"
        p2 = {"name": "T1-P2_cup", "args": [["".join(r) for r in g], [4, 0], [4, 8]]}
        p3 = {"name": "T1-P3_corridor", "args": [["#" * 14, "." * 14, "#" * 14], [1, 0], [1, 13]]}
        return [p1, p2, p3]
    rng = random.Random(7)
    n1 = 30
    e1 = [(i, i + 1, rng.randint(1, 20)) for i in range(n1 - 1)]
    e1 += [(rng.randrange(n1), rng.randrange(n1), rng.randint(1, 20)) for _ in range(90)]
    p1 = {"name": "T2-P1_random30", "args": [n1, [list(e) for e in e1], 0, n1 - 1]}
    n2 = 24
    e2 = [(i, i + 1, 3) for i in range(n2 - 1)] + [(i, i + 2, 7) for i in range(0, n2 - 2, 3)]
    e2 += [(i, (i * 7) % n2, 9) for i in range(n2)]
    p2 = {"name": "T2-P2_chain24", "args": [n2, [list(e) for e in e2], 0, n2 - 1]}
    n3 = 40
    e3 = [(rng.randrange(n3), rng.randrange(n3), rng.randint(0, 30)) for _ in range(160)]
    e3 += [(i, i + 1, 25) for i in range(n3 - 1)]
    p3 = {"name": "T2-P3_random40", "args": [n3, [list(e) for e in e3], 0, n3 - 1]}
    return [p1, p2, p3]


# ------------------------------------------------------------------------------------------ runner


def run_job(job: dict, hard_timeout: float) -> dict:
    """Run the harness in a fresh isolated interpreter; hard-kill at hard_timeout seconds."""
    SANDBOX.mkdir(exist_ok=True)
    d = Path(tempfile.mkdtemp(dir=SANDBOX))
    jp, rp = d / "job.json", d / "res.json"
    jp.write_text(json.dumps(job))
    t0 = time.time()
    try:
        proc = subprocess.run([PY, "-I", str(HARNESS), str(jp), str(rp)], cwd=str(d), stdout=subprocess.DEVNULL,
                              stderr=subprocess.PIPE, timeout=hard_timeout, start_new_session=True)
        if rp.exists():
            res = json.loads(rp.read_text())
        else:
            res = {"ok": False, "harness_error": f"no result (rc={proc.returncode}) {proc.stderr[-300:].decode(errors='replace')}"}
    except subprocess.TimeoutExpired:
        res = {"ok": True, "passed": False, "fail_kind": "hard_timeout", "hard_killed": True}
    except (OSError, json.JSONDecodeError) as e:
        res = {"ok": False, "harness_error": f"{type(e).__name__}:{e}"}
    finally:
        shutil.rmtree(d, ignore_errors=True)
    res.setdefault("wall_s", time.time() - t0)
    res["wall_total_s"] = time.time() - t0
    return res


_TESTS_CACHE: dict[str, dict] = {}


def load_tests(task: str) -> dict:
    if task not in _TESTS_CACHE:
        _TESTS_CACHE[task] = json.loads((TASK_DIR / f"hidden_tests_{task}.json").read_text())
    return _TESTS_CACHE[task]


def run_hidden_tests(code: str, task: str) -> dict:
    ht = load_tests(task)
    job = {"mode": "tests", "task": task, "code": code, "tests": ht["tests"], "limits": ht["limits"]}
    res = run_job(job, hard_timeout=sum(ht["limits"]) + 5.0)
    passed = bool(res.get("passed", False))
    return {"passed": passed, "wall_s": round(float(res.get("wall_s", 0.0)), 4), "fail_kind": res.get("fail_kind"),
            "fail_index": res.get("fail_index"), "n_pass": res.get("n_pass"), "harness_error": res.get("harness_error")}


def run_trace(code: str, task: str) -> dict:
    job = {"mode": "trace", "task": task, "code": code, "probes": probes(task), "probe_limit": 20.0}
    return run_job(job, hard_timeout=75.0)


def main() -> None:
    from references import REFS, WRONG  # noqa: E402  (tasks/ on sys.path when run directly)

    for task, builder in (("t1", build_t1_tests), ("t2", build_t2_tests)):
        tests = builder()
        assert len(tests) >= 40, f"{task}: only {len(tests)} tests"
        # time every reference 3x with generous limits
        gen_limits = [60.0] * len(tests)
        ref_times = []
        for label, var, src in REFS[task]:
            for rep in range(3):
                res = run_job({"mode": "tests", "task": task, "code": src, "tests": tests, "limits": gen_limits},
                              hard_timeout=900)
                assert res.get("passed"), f"{task} reference {var} failed rep {rep}: {res}"
                ref_times.append(res["times"])
            print(f"{task} reference {label}/{var}: pass 3/3, total {sum(res['times']):.3f}s", flush=True)
        slowest = [max(rt[i] for rt in ref_times) for i in range(len(tests))]
        limits = [round(max(1.0, 10 * s), 3) for s in slowest]
        out = {"task": task, "n_tests": len(tests), "tests": tests, "limits": limits,
               "slowest_reference_s": slowest, "names": [t["name"] for t in tests]}
        (TASK_DIR / f"hidden_tests_{task}.json").write_text(json.dumps(out))
        _TESTS_CACHE.pop(task, None)
        print(f"{task}: {len(tests)} tests, sum of limits {sum(limits):.1f}s", flush=True)
        for name, src in WRONG[task]:
            r = run_hidden_tests(src, task)
            assert not r["passed"], f"{task} wrong program {name} PASSED: {r}"
            print(f"{task} wrong program {name}: correctly fails ({r['fail_kind']} at test {r['fail_index']}, "
                  f"{r['wall_s']:.1f}s)", flush=True)
        # final 3/3 check under the real limits
        for label, var, src in REFS[task]:
            for rep in range(3):
                r = run_hidden_tests(src, task)
                assert r["passed"], f"{task} reference {var} failed under real limits: {r}"
        print(f"{task}: all references pass 3/3 under the final limits", flush=True)


if __name__ == "__main__":
    sys.path.insert(0, str(TASK_DIR))
    main()
