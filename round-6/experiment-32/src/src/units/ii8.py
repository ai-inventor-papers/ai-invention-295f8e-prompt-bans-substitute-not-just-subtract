"""II8 nearest_k_points (LeetCode 973; validity checker 'kclosest': a sub-multiset of the input of size k whose
largest squared distance is <= the k-th smallest; any order). Flagged structural neighbour of bench task T03."""

from __future__ import annotations

import random

from unitlib import ast_tree, calls_named, ccount, names_used, opcount, pcount, probe, recursive_functions

CHECKER = "kclosest"
ARGS = ["points", "k"]

ORACLE_A = '''
def solve(points, k):
    from math import hypot
    points = list(points)
    points.sort(key=lambda p: hypot(p[0], p[1]))
    return points[:k]
'''  # dataset reference (LeetCode 973 row), adapted
ORACLE_B = '''
def solve(points, k):
    import heapq
    return heapq.nsmallest(k, points, key=lambda p: p[0] * p[0] + p[1] * p[1])
'''

REFERENCES = {
    "full_sort": '''
def solve(points, k):
    return sorted(points, key=lambda p: p[0] * p[0] + p[1] * p[1])[:k]
''',
    "maxheap_k": '''
def solve(points, k):
    import heapq
    h = []
    for x, y in points:
        d = -(x * x + y * y)
        if len(h) < k:
            heapq.heappush(h, (d, x, y))
        elif d > h[0][0]:
            heapq.heapreplace(h, (d, x, y))
    return [[x, y] for _, x, y in h]
''',
    "nsmallest": ORACLE_B,
    "quickselect": '''
def solve(points, k):
    import random
    pts = [list(p) for p in points]
    dist = lambda p: p[0] * p[0] + p[1] * p[1]
    lo, hi = 0, len(pts) - 1
    rng = random.Random(0)
    while lo < hi:
        piv = dist(pts[rng.randint(lo, hi)])
        i, j = lo, hi
        while i <= j:
            while dist(pts[i]) < piv:
                i += 1
            while dist(pts[j]) > piv:
                j -= 1
            if i <= j:
                pts[i], pts[j] = pts[j], pts[i]
                i += 1
                j -= 1
        if k - 1 <= j:
            hi = j
        elif k - 1 >= i:
            lo = i
        else:
            break
    return pts[:k]
''',
}
MUTANTS = [
    '''
def solve(points, k):
    return points[:k]
''',
    '''
def solve(points, k):
    return sorted(points, key=lambda p: abs(p[0]) + abs(p[1]))[:k]
''',
    '''
def solve(points, k):
    return sorted(points, key=lambda p: p[0] * p[0] + p[1] * p[1])[:k - 1] or points[:1]
''',
]
EXCLUDED: dict[str, str] = {}


def _pts(rng: random.Random, n: int, span: int) -> list:
    return [[rng.randint(-span, span), rng.randint(-span, span)] for _ in range(n)]


def make_tests() -> list[dict]:
    rng = random.Random(973)
    cases = [("ex0", [[[1, 3], [-2, 2]], 1]), ("ex1", [[[3, 3], [5, -1], [-2, 4]], 2]), ("edge0", [[[0, 0]], 1]),
             ("edge1", [[[1, 0], [0, 1], [-1, 0], [0, -1]], 2]), ("edge2", [[[10000, 10000], [-10000, -10000]], 2])]
    i = 0
    while len(cases) < 5 + 55:
        n = rng.choice([1, 2, 5, 10, 50, 200, 1000])
        k = rng.randint(1, n)
        cases.append((f"rand{i}", [_pts(rng, n, rng.choice([2, 100, 10000])), k]))
        i += 1
    for j in range(8):
        n = 20000
        k = [1, 10000, 19999, 5000, 20000, 100, 15000, 7][j]
        cases.append((f"stress{j}", [_pts(rng, n, [10000, 10000, 5, 10000, 10000, 3, 10000, 10000][j]), k]))
    return [{"case_id": f"II8:{cid}", "kind": "stress" if cid.startswith("stress") else
             ("example" if cid.startswith(("ex", "edge")) else "random"), "args": a} for cid, a in cases]


def _probe() -> dict:
    rng = random.Random(11)
    return {"name": "p400", "args": [_pts(rng, 400, 1000), 20], "wrap": ["pts", "plain"], "expected": None}


PROBES = [_probe()]


def runtime_rule(tr: dict) -> str | None:
    a = probe(tr, "p400")
    if a is None or a.get("error"):
        return None
    cc = a.get("ccalls", {})
    if pcount(a, "heapq.nsmallest") >= 1:
        return "nsmallest"
    hp = ccount(a, "heappush", "heappop", "heapreplace", "heappushpop", "heapify")
    if hp >= 20:
        return "maxheap_k"
    if ccount(a, "sorted", "list.sort") >= 1:
        return "full_sort"
    if int(a.get("lines") or 0) >= 400 and opcount(a, "mul") >= 400:
        return "quickselect"
    if not cc and sum(a.get("ops", {}).values()) == 0:
        return None
    return "other"


def ast_rule(code: str) -> str | None:
    t = ast_tree(code)
    if t is None:
        return None
    calls = calls_named(t)
    names = names_used(t)
    if "nsmallest" in calls:
        return "nsmallest"
    if any(c in calls for c in ("heappush", "heappop", "heapreplace", "heappushpop", "heapify")):
        return "maxheap_k"
    if "sort" in calls or "sorted" in calls:
        return "full_sort"
    from units.ii_common import tuple_swap
    if "partition" in names or "quickselect" in names or "pivot" in names or recursive_functions(t) or tuple_swap(t):
        return "quickselect"
    return "other"
