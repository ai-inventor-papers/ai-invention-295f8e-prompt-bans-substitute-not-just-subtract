"""I5 minimum meeting rooms (LeetCode 253; half-open [start, end); n <= 50000 so per-meeting overlap counting exceeds
the limit)."""

from __future__ import annotations

import ast
import random

from unitlib6 import ast_tree, call, calls_named, maxlen, op, probe

CHECKER = "exact"
ARGS = ["intervals"]

ORACLE_A = '''
def solve(intervals):
    m = max(e[1] for e in intervals)
    d = [0] * (m + 1)
    for l, r in intervals:
        d[l] += 1
        d[r] -= 1
    ans = s = 0
    for v in d:
        s += v
        ans = max(ans, s)
    return ans
'''  # dataset reference (LeetCode 253 row)
ORACLE_B = '''
def solve(intervals):
    import heapq
    ends = []
    for s, e in sorted(intervals):
        if ends and ends[0] <= s:
            heapq.heapreplace(ends, e)
        else:
            heapq.heappush(ends, e)
    return len(ends)
'''

REFERENCES = {
    "min_heap_ends": '''
import heapq

def solve(intervals):
    intervals = sorted(intervals, key=lambda x: x[0])
    ends = []
    for s, e in intervals:
        if ends and ends[0] <= s:
            heapq.heappop(ends)
        heapq.heappush(ends, e)
    return len(ends)
''',
    "two_sorted_lists": '''
def solve(intervals):
    starts = sorted(s for s, _ in intervals)
    ends = sorted(e for _, e in intervals)
    rooms = best = 0
    j = 0
    for s in starts:
        while j < len(ends) and ends[j] <= s:
            j += 1
            rooms -= 1
        rooms += 1
        best = max(best, rooms)
    return best
''',
    "sweep_events": '''
def solve(intervals):
    events = []
    for s, e in intervals:
        events.append((s, 1))
        events.append((e, -1))
    events.sort(key=lambda x: (x[0], x[1]))
    cur = best = 0
    for _, d in events:
        cur += d
        if cur > best:
            best = cur
    return best
''',
    "difference_array": '''
def solve(intervals):
    top = max(e for _, e in intervals)
    diff = [0] * (top + 2)
    for s, e in intervals:
        diff[s] += 1
        diff[e] -= 1
    cur = best = 0
    for d in diff:
        cur += d
        best = max(best, cur)
    return best
''',
}
MUTANTS = [
    '''
def solve(intervals):
    events = []
    for s, e in intervals:
        events.append((s, 1))
        events.append((e, -1))
    events.sort(key=lambda x: (x[0], -x[1]))
    cur = best = 0
    for _, d in events:
        cur += d
        best = max(best, cur)
    return best
''',
    '''
def solve(intervals):
    return len(intervals)
''',
    '''
def solve(intervals):
    import heapq
    intervals = sorted(intervals)
    ends = []
    for s, e in intervals:
        if ends and ends[0] < s:
            heapq.heappop(ends)
        heapq.heappush(ends, e)
    return len(ends)
''',
]
EXCLUDED = {
    "overlap_count_per_meeting": '''
def solve(intervals):
    best = 0
    for s, _ in intervals:
        c = 0
        for a, b in intervals:
            if a <= s < b:
                c += 1
        best = max(best, c)
    return best
''',
}


def _case(rng: random.Random, n: int, T: int, maxlen_: int) -> list:
    out = []
    for _ in range(n):
        s = rng.randint(0, T - 1)
        e = min(T, s + rng.randint(1, maxlen_))
        out.append([s, e])
    return [out]


def make_tests() -> list[dict]:
    rng = random.Random(253)
    cases = [("ex0", [[[0, 30], [5, 10], [15, 20]]]), ("ex1", [[[7, 10], [2, 4]]]), ("edge_one", [[[0, 1]]]),
             ("edge_touch", [[[1, 5], [5, 10], [10, 15]]]), ("edge_same", [[[2, 3], [2, 3], [2, 3]]]),
             ("edge_big", [[[0, 1000000], [999999, 1000000]]]), ("edge_nested", [[[1, 10], [2, 9], [3, 8], [9, 10]]])]
    sizes = [1, 2, 3, 5, 8, 13, 20, 50, 100, 300, 1000, 3000]
    for i in range(46):
        n = sizes[i % len(sizes)]
        T = rng.choice([10, 100, 1000, 1000000])
        cases.append((f"rand{i}", _case(rng, n, T, rng.choice([1, 5, max(1, T // 10), T]))))
    for j in range(6):
        cases.append((f"stress{j}", _case(rng, 50000, 1000000, 400000 if j % 2 == 0 else 20000)))
    return [{"case_id": f"I5:{cid}", "kind": "stress" if cid.startswith("stress") else
             ("example" if cid.startswith("ex") else "random"), "args": a} for cid, a in cases]


def _probe(n: int, seed: int, name: str) -> dict:
    rng = random.Random(seed)
    a = _case(rng, n, 5000, 600)[0]
    import heapq
    ends = []
    for s, e in sorted(a):
        if ends and ends[0] <= s:
            heapq.heapreplace(ends, e)
        else:
            heapq.heappush(ends, e)
    return {"name": name, "args": [a], "wrap": ["list"], "expected": len(ends), "checker": "exact"}


PROBES = [_probe(100, 9, "p100"), _probe(200, 10, "p200")]


def runtime_rule(tr: dict) -> str | None:
    a = probe(tr, "p100")
    if a is None:
        return None
    n = 100
    if call(a, "heappush", "heappop", "heapify", "heapreplace", "heappushpop") >= n // 4:
        return "min_heap_ends"
    nsort = call(a, "sorted", "sort")
    ml = max(maxlen(a, "sorted", "sort"), 0)
    if nsort >= 1 and ml >= int(1.5 * n):
        return "sweep_events"
    if nsort >= 2:
        return "two_sorted_lists"
    if nsort == 0 and op(a, "STORE_SUBSCR") >= int(1.5 * n) and op(a, "BINARY_OP:*") >= 1:
        return "difference_array"
    if nsort == 0 and op(a, "STORE_SUBSCR") >= int(1.5 * n):
        return "difference_array"
    return "other"


def ast_rule(code: str) -> str | None:
    t = ast_tree(code)
    if t is None:
        return None
    calls = calls_named(t)
    names = {n.id for n in ast.walk(t) if isinstance(n, ast.Name)} | {n.attr for n in ast.walk(t)
                                                                      if isinstance(n, ast.Attribute)}
    if "heapq" in names or any(c.startswith("heap") for c in calls):
        return "min_heap_ends"
    nsort = calls.count("sorted") + calls.count("sort")
    tuples_pm = 0
    for n in ast.walk(t):
        if isinstance(n, ast.Tuple) and len(n.elts) == 2:
            for e in n.elts:
                if isinstance(e, ast.Constant) and e.value in (1, 0) or (isinstance(e, ast.UnaryOp) and
                                                                          isinstance(e.op, ast.USub)):
                    tuples_pm += 1
    if nsort >= 2:
        return "two_sorted_lists"
    if nsort == 1 and (tuples_pm >= 2 or "events" in names or any(
            isinstance(n, ast.Dict) for n in ast.walk(t)) or "defaultdict" in calls or "Counter" in calls):
        return "sweep_events"
    if nsort == 0 and any(isinstance(n, ast.BinOp) and isinstance(n.op, ast.Mult) and isinstance(n.left, ast.List)
                          for n in ast.walk(t)):
        return "difference_array"
    if nsort == 1:
        return "other"
    return "other"
