"""I1 longest consecutive run (LeetCode 128, n <= 30000 so the list-membership brute force exceeds the limit)."""

from __future__ import annotations

import ast
import random

from unitlib6 import ast_tree, calls_named, func_defs, has_dict, has_set_literal, call, maxlen, op, probe, \
    recursive_functions, user_calls, binop

CHECKER = "exact"
ARGS = ["nums"]

ORACLE_A = '''
def solve(nums):
    s = set(nums)
    ans = 0
    d = {}
    for x in nums:
        y = x
        while y in s:
            s.remove(y)
            y += 1
        d[x] = d.get(y, 0) + y - x
        ans = max(ans, d[x])
    return ans
'''  # dataset reference (LeetCode 128 row), defaultdict -> dict.get
ORACLE_B = '''
def solve(nums):
    if not nums:
        return 0
    a = sorted(set(nums))
    best = cur = 1
    for i in range(1, len(a)):
        cur = cur + 1 if a[i] == a[i - 1] + 1 else 1
        best = max(best, cur)
    return best
'''

REFERENCES = {
    "set_start_walk": '''
def solve(nums):
    s = set(nums)
    best = 0
    for v in s:
        if v - 1 not in s:
            w = v
            while w + 1 in s:
                w += 1
            best = max(best, w - v + 1)
    return best
''',
    "set_remove_expand": '''
def solve(nums):
    s = set(nums)
    best = 0
    while s:
        v = s.pop()
        lo, hi = v - 1, v + 1
        while lo in s:
            s.remove(lo)
            lo -= 1
        while hi in s:
            s.remove(hi)
            hi += 1
        best = max(best, hi - lo - 1)
    return best
''',
    "sort_scan": '''
def solve(nums):
    if not nums:
        return 0
    a = sorted(nums)
    best = cur = 1
    for i in range(1, len(a)):
        if a[i] == a[i - 1]:
            continue
        if a[i] == a[i - 1] + 1:
            cur += 1
        else:
            cur = 1
        best = max(best, cur)
    return best
''',
    "boundary_map": '''
def solve(nums):
    length = {}
    best = 0
    for v in nums:
        if v in length:
            continue
        left = length.get(v - 1, 0)
        right = length.get(v + 1, 0)
        total = left + right + 1
        length[v] = total
        length[v - left] = total
        length[v + right] = total
        best = max(best, total)
    return best
''',
    "union_find": '''
def solve(nums):
    parent = {}
    size = {}
    for v in nums:
        if v not in parent:
            parent[v] = v
            size[v] = 1

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra == rb:
            return
        if size[ra] < size[rb]:
            ra, rb = rb, ra
        parent[rb] = ra
        size[ra] += size[rb]

    for v in list(parent):
        if v + 1 in parent:
            union(v, v + 1)
    return max((size[find(v)] for v in parent), default=0)
''',
}
MUTANTS = [
    '''
def solve(nums):
    s = set(nums)
    best = 0
    for v in s:
        if v - 1 not in s:
            w = v
            while w + 1 in s:
                w += 1
            best = max(best, w - v)
    return best
''',
    '''
def solve(nums):
    if not nums:
        return 0
    a = sorted(nums)
    best = cur = 1
    for i in range(1, len(a)):
        if a[i] == a[i - 1] + 1:
            cur += 1
        else:
            cur = 1
        best = max(best, cur)
    return best
''',
    '''
def solve(nums):
    return len(set(nums))
''',
]
EXCLUDED = {
    "list_membership_scan": '''
def solve(nums):
    best = 0
    for v in nums:
        if v - 1 not in nums:
            w = v
            while w + 1 in nums:
                w += 1
            best = max(best, w - v + 1)
    return best
''',
}


def _case(rng: random.Random, n: int, kind: str) -> list:
    if n == 0:
        return [[]]
    if kind == "dense":
        base = rng.randint(-10 ** 9, 10 ** 9 - 3 * n)
        a = [base + rng.randint(0, 2 * n) for _ in range(n)]
    elif kind == "runs":
        a = []
        while len(a) < n:
            st = rng.randint(-10 ** 9, 10 ** 9 - 1000)
            L = rng.randint(1, max(1, min(n - len(a), 50)))
            a.extend(range(st, st + L))
        a = a[:n]
        a += rng.sample(a, min(len(a), n // 10))
        rng.shuffle(a)
    else:
        a = [rng.randint(-10 ** 9, 10 ** 9) for _ in range(n)]
    return [a]


def make_tests() -> list[dict]:
    rng = random.Random(128)
    cases = [("ex0", [[100, 4, 200, 1, 3, 2]]), ("ex1", [[0, 3, 7, 2, 5, 8, 4, 6, 0, 1]]), ("edge_empty", [[]]),
             ("edge_one", [[5]]), ("edge_dups", [[1, 1, 1]]), ("edge_neg", [[-1, -2, -3, 0, 5, 6]]),
             ("edge_ext", [[10 ** 9, -10 ** 9, 10 ** 9 - 1]])]
    sizes = [1, 2, 3, 5, 8, 13, 20, 50, 100, 300, 1000, 3000]
    for i in range(48):
        cases.append((f"rand{i}", _case(rng, sizes[i % len(sizes)], ("dense", "runs", "random")[i % 3])))
    for j in range(6):
        st = rng.randint(-10 ** 9, 10 ** 9 - 30000)
        a = list(range(st, st + 30000))
        rng.shuffle(a)
        cases.append((f"stress{j}", [a] if j % 2 == 0 else _case(rng, 30000, "dense")))
    return [{"case_id": f"I1:{cid}", "kind": "stress" if cid.startswith("stress") else
             ("example" if cid.startswith("ex") else "random"), "args": a} for cid, a in cases]


def _probe(n: int, seed: int, name: str) -> dict:
    rng = random.Random(seed)
    a = list(range(1000, 1000 + n // 2)) + list(range(5000, 5000 + n // 4)) + [rng.randint(10 ** 6, 10 ** 7)
                                                                                 for _ in range(n // 4)]
    a += a[: n // 10]
    rng.shuffle(a)
    from collections import Counter  # noqa: F401
    exp = max(n // 2, 1)
    return {"name": name, "args": [a], "wrap": ["list"], "expected": exp, "checker": "exact"}


PROBES = [_probe(200, 3, "p200"), _probe(400, 4, "p400")]


def runtime_rule(tr: dict) -> str | None:
    a = probe(tr, "p200")
    if a is None:
        return None
    n = 220
    if call(a, "sorted", "sort") >= 1 and max(maxlen(a, "sorted", "sort"), 0) >= n // 3:
        return "sort_scan"
    uc = user_calls(a)
    if uc >= n // 2:
        return "union_find"
    removes = call(a, "remove", "discard", "pop")
    if removes >= n // 4:
        return "set_remove_expand"
    gets = call(a, "get", "setdefault")
    if gets >= n // 2:
        return "boundary_map"
    cont = op(a, "CONTAINS_OP")
    if cont >= n // 2:
        stores = op(a, "STORE_SUBSCR")
        if stores >= n:
            return "boundary_map"
        return "set_start_walk"
    if op(a, "STORE_SUBSCR") >= n:
        return "boundary_map"
    return "other"


def ast_rule(code: str) -> str | None:
    t = ast_tree(code)
    if t is None:
        return None
    calls = calls_named(t)
    names = {n.id for n in ast.walk(t) if isinstance(n, ast.Name)} | {n.arg for n in ast.walk(t)
                                                                      if isinstance(n, ast.arg)}
    fdefs = [f.lower() for f in func_defs(t)]
    if any(f in ("find", "union", "unite", "find_root", "root", "join") for f in fdefs) or "parent" in names:
        return "union_find"
    if "sorted" in calls or "sort" in calls:
        return "sort_scan"
    if any(c in calls for c in ("remove", "discard", "pop")) and has_set_literal(t):
        return "set_remove_expand"
    if has_dict(t) and ("get" in calls or any(isinstance(n, ast.Subscript) for n in ast.walk(t))) and \
            not has_set_literal(t):
        return "boundary_map"
    if has_set_literal(t):
        return "set_start_walk"
    return "other"
