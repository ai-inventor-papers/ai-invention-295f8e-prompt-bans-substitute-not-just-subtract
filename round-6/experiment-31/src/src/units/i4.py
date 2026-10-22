"""I4 h-index (LeetCode 274; n <= 100000 so the quadratic scan over h exceeds the limit)."""

from __future__ import annotations

import ast
import random

from unitlib6 import ast_tree, call, calls_named, lst, maxlen, op, probe, subscript_stores

CHECKER = "exact"
ARGS = ["citations"]

ORACLE_A = '''
def solve(citations):
    citations = sorted(citations, reverse=True)
    for h in range(len(citations), 0, -1):
        if citations[h - 1] >= h:
            return h
    return 0
'''  # dataset reference (LeetCode 274 row; sort(reverse=True) on a copy)
ORACLE_B = '''
def solve(citations):
    n = len(citations)
    cnt = [0] * (n + 1)
    for c in citations:
        cnt[min(c, n)] += 1
    total = 0
    for h in range(n, -1, -1):
        total += cnt[h]
        if total >= h:
            return h
    return 0
'''

REFERENCES = {
    "sort_scan": '''
def solve(citations):
    a = sorted(citations, reverse=True)
    h = 0
    for i, c in enumerate(a):
        if c >= i + 1:
            h = i + 1
        else:
            break
    return h
''',
    "counting_levels": '''
def solve(citations):
    n = len(citations)
    levels = [0] * (n + 1)
    for c in citations:
        if c >= n:
            levels[n] += 1
        else:
            levels[c] += 1
    total = 0
    for h in range(n, -1, -1):
        total += levels[h]
        if total >= h:
            return h
    return 0
''',
    "binary_search_h": '''
def solve(citations):
    lo, hi = 0, len(citations)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if sum(1 for c in citations if c >= mid) >= mid:
            lo = mid
        else:
            hi = mid - 1
    return lo
''',
    "heap_pop": '''
import heapq

def solve(citations):
    heap = [-c for c in citations]
    heapq.heapify(heap)
    h = 0
    while heap:
        c = -heapq.heappop(heap)
        if c >= h + 1:
            h += 1
        else:
            break
    return h
''',
}
MUTANTS = [
    '''
def solve(citations):
    a = sorted(citations, reverse=True)
    h = 0
    for i, c in enumerate(a):
        if c > i + 1:
            h = i + 1
    return h
''',
    '''
def solve(citations):
    return min(len(citations), max(citations))
''',
    '''
def solve(citations):
    a = sorted(citations)
    return a[len(a) // 2]
''',
]
EXCLUDED = {
    "quadratic_h_scan": '''
def solve(citations):
    n = len(citations)
    for h in range(n, 0, -1):
        if sum(1 for c in citations if c >= h) >= h:
            return h
    return 0
''',
}


def make_tests() -> list[dict]:
    rng = random.Random(274)
    cases = [("ex0", [[3, 0, 6, 1, 5]]), ("ex1", [[1, 3, 1]]), ("edge0", [[0]]), ("edge1", [[100]]),
             ("edge_zeros", [[0, 0, 0]]), ("edge_big", [[100000] * 7]), ("edge_one_each", [[1, 1, 1, 1]])]
    sizes = [1, 2, 3, 5, 8, 13, 20, 50, 100, 300, 1000, 5000]
    for i in range(46):
        n = sizes[i % len(sizes)]
        top = rng.choice([3, n, 2 * n, 100000])
        cases.append((f"rand{i}", [[rng.randint(0, top) for _ in range(n)]]))
    for j in range(6):
        n = 100000
        cases.append((f"stress{j}", [[rng.randint(0, 100000) for _ in range(n)]] if j % 2 == 0 else
                      [[rng.randint(n // 3, n) for _ in range(n)]]))
    return [{"case_id": f"I4:{cid}", "kind": "stress" if cid.startswith("stress") else
             ("example" if cid.startswith("ex") else "random"), "args": a} for cid, a in cases]


def _probe(n: int, seed: int, name: str) -> dict:
    rng = random.Random(seed)
    a = [rng.randint(0, n) for _ in range(n)]
    b = sorted(a, reverse=True)
    h = 0
    for i, c in enumerate(b):
        if c >= i + 1:
            h = i + 1
    return {"name": name, "args": [a], "wrap": ["list"], "expected": h, "checker": "exact"}


PROBES = [_probe(200, 7, "p200"), _probe(400, 8, "p400")]


def runtime_rule(tr: dict) -> str | None:
    a = probe(tr, "p200")
    if a is None:
        return None
    n = 200
    if call(a, "heappush", "heapify", "heappop", "nlargest", "heappushpop", "heapreplace") >= 1:
        return "heap_pop"
    if call(a, "sorted", "sort") >= 1 and max(maxlen(a, "sorted", "sort"), 0) >= n // 2:
        return "sort_scan"
    passes = lst(a, "iter") + call(a, "count")
    if passes >= n // 4:
        return "other"
    if passes >= 4:
        return "binary_search_h"
    if op(a, "STORE_SUBSCR") >= n // 2:
        return "counting_levels"
    return "other"


def ast_rule(code: str) -> str | None:
    t = ast_tree(code)
    if t is None:
        return None
    calls = calls_named(t)
    names = {n.id for n in ast.walk(t) if isinstance(n, ast.Name)} | {n.attr for n in ast.walk(t)
                                                                      if isinstance(n, ast.Attribute)}
    if "heapq" in names or any(c.startswith("heap") for c in calls) or "nlargest" in calls:
        return "heap_pop"
    if "sorted" in calls or "sort" in calls:
        return "sort_scan"
    lohi = any(nm in names for nm in ("lo", "hi", "low", "high", "left", "right", "l", "r", "mid"))
    if lohi and any(isinstance(n, ast.While) for n in ast.walk(t)) and "mid" in names | {"m"}:
        return "binary_search_h"
    if lohi and any(isinstance(n, ast.While) for n in ast.walk(t)):
        return "binary_search_h"
    loops = [n for n in ast.walk(t) if isinstance(n, (ast.For, ast.While))]
    nested = any(isinstance(m, (ast.For, ast.While, ast.comprehension)) for L in loops for m in ast.walk(L)
                 if m is not L)
    if subscript_stores(t) >= 1 and not nested:
        return "counting_levels"
    if subscript_stores(t) >= 1 and any(isinstance(n, ast.BinOp) and isinstance(n.op, ast.Mult)
                                        for n in ast.walk(t)):
        return "counting_levels"
    return "other"
