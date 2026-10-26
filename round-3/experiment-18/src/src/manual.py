"""Manual-pass support (S8): every audited program is run on 3 extra seeded random inputs against a trusted
reference (sandboxed with the bench runner and this artifact's own checkers), and a review sheet is printed so the
executor can read each program next to its nearest known solutions and judge classes.  The executor's final
classes and justifications are recorded in results/manual_audit.json (written by `manual.py record`)."""

from __future__ import annotations

import heapq
import json
import random
import sys
from collections import deque
from pathlib import Path
from typing import Any

from config import RESULTS, ROOT, SRC, setup_logging, utc_now, write_json

CHECKERS = SRC / "manual_checkers.py"


def ref_t1(grid, start, goal):
    R, C = len(grid), len(grid[0])
    if grid[start[0]][start[1]] == "#" or grid[goal[0]][goal[1]] == "#":
        return []
    q, seen = deque([tuple(start)]), {tuple(start)}
    while q:
        r, c = q.popleft()
        if (r, c) == tuple(goal):
            return True
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < R and 0 <= nc < C and grid[nr][nc] == "." and (nr, nc) not in seen:
                seen.add((nr, nc))
                q.append((nr, nc))
    return []


def ref_t2(n, edges, s, t):
    adj = [[] for _ in range(n)]
    for u, v, w in edges:
        adj[u].append((v, w))
    dist = [None] * n
    pq = [(0, s)]
    while pq:
        d, u = heapq.heappop(pq)
        if dist[u] is not None:
            continue
        dist[u] = d
        for v, w in adj[u]:
            if dist[v] is None:
                heapq.heappush(pq, (d + w, v))
    return dist[t] if dist[t] is not None else -1


def ref_t10(n, edges):
    p = list(range(n))

    def f(x):
        while p[x] != x:
            p[x] = p[p[x]]
            x = p[x]
        return x
    for u, v in edges:
        p[f(u)] = f(v)
    return len({f(i) for i in range(n)})


def gen_case(task: str, rng: random.Random) -> dict[str, Any]:
    if task == "T1":
        R, C = rng.randint(3, 25), rng.randint(3, 25)
        g = ["".join("#" if rng.random() < 0.25 else "." for _ in range(C)) for _ in range(R)]
        s = (rng.randrange(R), rng.randrange(C))
        t = (rng.randrange(R), rng.randrange(C))
        g = [row[:s[1]] + "." + row[s[1] + 1:] if i == s[0] else row for i, row in enumerate(g)]
        g = [row[:t[1]] + "." + row[t[1] + 1:] if i == t[0] else row for i, row in enumerate(g)]
        kw = {"grid": g, "start": list(s), "goal": list(t)}
        return {"kwargs": kw, "expected": ref_t1(g, s, t) is True}
    if task == "T2":
        n = rng.randint(2, 60)
        edges = [[rng.randrange(n), rng.randrange(n), rng.randint(0, 100)] for _ in range(rng.randint(1, 300))]
        s, t = rng.randrange(n), rng.randrange(n)
        return {"kwargs": {"n": n, "edges": edges, "s": s, "t": t}, "expected": 0 if s == t else ref_t2(n, edges, s, t)}
    if task == "T03":
        nums = [rng.randint(-10000, 10000) for _ in range(rng.randint(1, 2000))]
        k = rng.randint(1, len(nums))
        return {"kwargs": {"nums": nums, "k": k}, "expected": sorted(nums)[k - 1]}
    if task == "T04":
        hay = "".join(rng.choice("ab") for _ in range(rng.randint(1, 3000)))
        nd = hay[rng.randrange(len(hay)):][:rng.randint(1, 8)] if rng.random() < 0.7 else \
            "".join(rng.choice("ab") for _ in range(rng.randint(1, 8)))
        return {"kwargs": {"haystack": hay, "needle": nd}, "expected": hay.find(nd)}
    if task == "T06":
        n = rng.randint(1, 3000)
        nums = list(range(1, n + 1))
        d = rng.randint(1, n)
        reps = rng.randint(1, 3)
        for _ in range(reps):
            nums[rng.randrange(len(nums))] = d
        nums.append(d)
        rng.shuffle(nums)
        nums = nums[:n + 1]
        if nums.count(d) < 2:
            nums[0] = d
            nums[-1] = d
        return {"kwargs": {"nums": nums}, "expected": d}
    if task == "T10":
        n = rng.randint(1, 300)
        es = set()
        for _ in range(rng.randint(0, min(1500, n * (n - 1) // 2))):
            u, v = rng.randrange(n), rng.randrange(n)
            if u != v and (u, v) not in es and (v, u) not in es:
                es.add((u, v))
        edges = [list(e) for e in es]
        return {"kwargs": {"n": n, "edges": edges}, "expected": ref_t10(n, edges)}
    raise KeyError(task)


CHECKER_SRC = '''"""Checkers for the manual pass (stdlib only; loaded by the bench sandbox runner)."""


def _t1(kw, exp, got):
    grid, s, g = kw["grid"], tuple(kw["start"]), tuple(kw["goal"])
    if not exp:
        return got == [] or got is None
    try:
        path = [tuple(p) for p in got]
    except TypeError:
        return False
    if not path or path[0] != s or path[-1] != g:
        return False
    R, C = len(grid), len(grid[0])
    for (a, b), (c, d) in zip(path, path[1:]):
        if abs(a - c) + abs(b - d) != 1:
            return False
    return all(0 <= r < R and 0 <= c < C and grid[r][c] == "." for r, c in path)


def _eq(kw, exp, got):
    return got == exp


CHECK = {"T1": _t1, "T2": _eq, "T03": _eq, "T04": _eq, "T06": _eq, "T10": _eq}
'''


def extra_tests(task: str, code: str, seed: int) -> dict[str, Any]:
    from bench.common.harness import run_tests
    import bench.common.harness as H

    CHECKERS.write_text(CHECKER_SRC)
    rng = random.Random(seed)
    cases = []
    for i in range(3):
        c = gen_case(task, rng)
        cases.append({"case_id": f"manual:{task}:{seed}:{i}", "kwargs": c["kwargs"], "expected": c["expected"],
                      "limit": 5.0})
    old = H.CHECKERS
    H.CHECKERS = CHECKERS
    try:
        r = run_tests(code, task, cases)
    finally:
        H.CHECKERS = old
    return {"n": 3, "n_pass": r["n_pass"], "statuses": r["statuses"], "load_error": r["load_error"]}


def sheet() -> None:
    d = json.loads((RESULTS / "novelty_audit_judges.json").read_text())
    out = []
    for i, r in enumerate(d["records"]):
        et = extra_tests(r["task"], r["code"], 1000 + i)
        r["extra_tests"] = et
        out.append(r)
        print(f"\n=== [{i}] {r['sample_id']} task={r['task']} arm={r['arm']} role={r['audit_role']} "
              f"passed={r['passed']} extra={et['n_pass']}/3")
        print(f"A: {r['judge_A']}\nB: {r['judge_B']}")
        print("nearest known:", [(n['source'], n['mode_hint'], n['similarity']) for n in r['neighbours_known']])
        print("nearest refs:", [(n['mode_hint'], n['similarity']) for n in r['neighbours_refs']])
        print(r["code"][:2500])
    d["records"] = out
    (RESULTS / "novelty_audit_judges.json").write_text(json.dumps(d, indent=1))


if __name__ == "__main__":
    setup_logging("manual")
    if sys.argv[1] == "sheet":
        sheet()
