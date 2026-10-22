"""I9 common values with repeats (LeetCode 350; order-free 'multiset' checker; lists <= 50000 so list.remove loops
exceed the limit)."""

from __future__ import annotations

import ast
import random

from unitlib6 import ast_tree, binop, call, calls_named, has_dict, maxlen, op, probe

CHECKER = "multiset"
ARGS = ["nums1", "nums2"]

ORACLE_A = '''
def solve(nums1, nums2):
    from collections import Counter
    cnt = Counter(nums1)
    ans = []
    for x in nums2:
        if cnt[x]:
            ans.append(x)
            cnt[x] -= 1
    return ans
'''  # dataset reference (LeetCode 350 row)
ORACLE_B = '''
def solve(nums1, nums2):
    a, b = sorted(nums1), sorted(nums2)
    i = j = 0
    out = []
    while i < len(a) and j < len(b):
        if a[i] == b[j]:
            out.append(a[i]); i += 1; j += 1
        elif a[i] < b[j]:
            i += 1
        else:
            j += 1
    return out
'''

REFERENCES = {
    "hash_count": '''
def solve(nums1, nums2):
    counts = {}
    for v in nums1:
        counts[v] = counts.get(v, 0) + 1
    out = []
    for v in nums2:
        if counts.get(v, 0) > 0:
            out.append(v)
            counts[v] -= 1
    return out
''',
    "sort_two_index": '''
def solve(nums1, nums2):
    a, b = sorted(nums1), sorted(nums2)
    i = j = 0
    out = []
    while i < len(a) and j < len(b):
        if a[i] < b[j]:
            i += 1
        elif a[i] > b[j]:
            j += 1
        else:
            out.append(a[i])
            i += 1
            j += 1
    return out
''',
    "sort_binary_search": '''
from bisect import bisect_left

def solve(nums1, nums2):
    a = sorted(nums1)
    used = [False] * len(a)
    out = []
    for v in nums2:
        i = bisect_left(a, v)
        while i < len(a) and a[i] == v and used[i]:
            i += 1
        if i < len(a) and a[i] == v:
            used[i] = True
            out.append(v)
    return out
''',
    "count_array": '''
def solve(nums1, nums2):
    top = max(nums1)
    cnt = [0] * (top + 1)
    for v in nums1:
        cnt[v] += 1
    out = []
    for v in nums2:
        if v <= top and cnt[v] > 0:
            cnt[v] -= 1
            out.append(v)
    return out
''',
}
MUTANTS = [
    '''
def solve(nums1, nums2):
    return list(set(nums1) & set(nums2))
''',
    '''
def solve(nums1, nums2):
    s = set(nums1)
    return [v for v in nums2 if v in s]
''',
    '''
def solve(nums1, nums2):
    return nums1 if len(nums1) < len(nums2) else nums2
''',
]
EXCLUDED = {
    "list_remove_loop": '''
def solve(nums1, nums2):
    rest = list(nums2)
    out = []
    for v in nums1:
        if v in rest:
            rest.remove(v)
            out.append(v)
    return out
''',
}


def make_tests() -> list[dict]:
    rng = random.Random(350)
    cases = [("ex0", [[1, 2, 2, 1], [2, 2]]), ("ex1", [[4, 9, 5], [9, 4, 9, 8, 4]]), ("edge_none", [[1], [2]]),
             ("edge_same", [[3, 3, 3], [3, 3]]), ("edge_zero", [[0], [0]]), ("edge_big", [[1000000], [1000000, 0]])]
    sizes = [1, 2, 3, 5, 8, 13, 20, 50, 100, 300, 1000, 5000]
    for i in range(46):
        n, m = sizes[i % len(sizes)], sizes[(i * 7) % len(sizes)]
        top = rng.choice([3, 10, 100, 1000000])
        cases.append((f"rand{i}", [[rng.randint(0, top) for _ in range(n)], [rng.randint(0, top) for _ in range(m)]]))
    for j in range(6):
        n = 50000
        top = 1000000 if j % 2 == 0 else 60000
        a = [rng.randint(0, top) for _ in range(n)]
        b = [rng.randint(0, top) for _ in range(n)]
        cases.append((f"stress{j}", [a, b]))
    return [{"case_id": f"I9:{cid}", "kind": "stress" if cid.startswith("stress") else
             ("example" if cid.startswith("ex") else "random"), "args": a} for cid, a in cases]


def _probe(n: int, seed: int, name: str) -> dict:
    rng = random.Random(seed)
    a = [rng.randint(0, n // 2) for _ in range(n)]
    b = [rng.randint(0, n // 2) for _ in range(n)]
    from collections import Counter
    exp = sorted((Counter(a) & Counter(b)).elements())
    return {"name": name, "args": [a, b], "wrap": ["list", "list"], "expected": exp, "checker": "multiset"}


PROBES = [_probe(150, 15, "p150"), _probe(300, 16, "p300")]


def runtime_rule(tr: dict) -> str | None:
    a = probe(tr, "p150")
    if a is None:
        return None
    n = 150
    if call(a, "remove", "index") >= n // 4:
        return "other"
    srt = call(a, "sorted", "sort") >= 1 and max(maxlen(a, "sorted", "sort"), 0) >= n // 2
    if srt and call(a, "bisect_left", "bisect_right", "bisect") >= n // 3:
        return "sort_binary_search"
    if srt:
        return "sort_two_index"
    if call(a, "Counter", "defaultdict") >= 1 or call(a, "get", "setdefault") >= n // 2:
        return "hash_count"
    if op(a, "STORE_SUBSCR") >= n // 2 and binop(a, "*") >= 1:
        return "count_array"
    if op(a, "STORE_SUBSCR") >= n // 2:
        return "hash_count"
    return "other"


def ast_rule(code: str) -> str | None:
    t = ast_tree(code)
    if t is None:
        return None
    calls = calls_named(t)
    if any(c in calls for c in ("bisect_left", "bisect_right", "bisect")):
        return "sort_binary_search"
    if "sorted" in calls or "sort" in calls:
        return "sort_two_index"
    if has_dict(t) or "get" in calls:
        return "hash_count"
    if any(isinstance(n, ast.BinOp) and isinstance(n.op, ast.Mult) and isinstance(n.left, ast.List)
           for n in ast.walk(t)):
        return "count_array"
    return "other"
