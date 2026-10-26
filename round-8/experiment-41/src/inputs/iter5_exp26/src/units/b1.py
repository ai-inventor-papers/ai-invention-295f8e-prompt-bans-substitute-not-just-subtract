"""B1 missing_number (LeetCode 268, widened to n <= 1e5 so list-membership scanning fails)."""

from __future__ import annotations

import ast
import random

from unitlib import ast_tree, binops, calls_named, ccount, names_used, opcount, probe

CHECKER = "exact"
ARGS = ["nums"]

ORACLE_A = '''
def solve(nums):
    from functools import reduce
    from operator import xor
    return reduce(xor, (i ^ v for i, v in enumerate(nums, 1)), 0)
'''  # dataset reference (LeetCode 268 row), adapted to solve(nums)
ORACLE_B = '''
def solve(nums):
    return (set(range(len(nums) + 1)) - set(nums)).pop()
'''

REFERENCES = {
    "arithmetic_sum": '''
def solve(nums):
    n = len(nums)
    return n * (n + 1) // 2 - sum(nums)
''',
    "xor_fold": '''
def solve(nums):
    r = len(nums)
    for i, v in enumerate(nums):
        r ^= i ^ v
    return r
''',
    "sort_scan": '''
def solve(nums):
    a = sorted(nums)
    for i, v in enumerate(a):
        if v != i:
            return i
    return len(a)
''',
    "sort_binary_search": '''
def solve(nums):
    a = sorted(nums)
    lo, hi = 0, len(a)
    while lo < hi:
        mid = (lo + hi) // 2
        if a[mid] > mid:
            hi = mid
        else:
            lo = mid + 1
    return lo
''',
    "hash_set": '''
def solve(nums):
    seen = set(nums)
    for i in range(len(nums) + 1):
        if i not in seen:
            return i
''',
}
MUTANTS = [
    '''
def solve(nums):
    n = len(nums)
    return n * (n - 1) // 2 - sum(nums)
''',
    '''
def solve(nums):
    a = sorted(nums)
    for i, v in enumerate(a):
        if v != i:
            return i
    return -1
''',
    '''
def solve(nums):
    r = 0
    for i, v in enumerate(nums):
        r ^= i ^ v
    return r
''',
]
EXCLUDED = {
    "list_membership_scan": '''
def solve(nums):
    for i in range(len(nums) + 1):
        if i not in nums:
            return i
''',
}


def _case(rng: random.Random, n: int, miss: int | None = None) -> list:
    miss = rng.randint(0, n) if miss is None else miss
    vals = [v for v in range(n + 1) if v != miss]
    rng.shuffle(vals)
    return [vals]


def make_tests() -> list[dict]:
    rng = random.Random(268)
    cases = [("ex0", [[3, 0, 1]]), ("ex1", [[0, 1]]), ("ex2", [[9, 6, 4, 2, 3, 5, 7, 0, 1]])]
    sizes = [1, 1, 2, 2, 3, 4, 5, 7, 10, 16, 31, 50, 64, 100, 128, 200, 500, 1000, 2000, 5000]
    i = 0
    for n in sizes:
        for miss in (0, n, None):
            if len(cases) >= 3 + 55:
                break
            cases.append((f"rand{i}", _case(rng, n, miss)))
            i += 1
    for j, miss in enumerate([0, 100000, 50000, 1, 99999, None, None, None, None, None]):
        cases.append((f"stress{j}", _case(rng, 100000, miss)))
    return [{"case_id": f"B1:{cid}", "kind": "stress" if cid.startswith("stress") else
             ("example" if cid.startswith("ex") else "random"), "args": a} for cid, a in cases]


def _probe(n: int, seed: int) -> dict:
    rng = random.Random(seed)
    a = _case(rng, n, miss=n - 2)   # missing value near the top: a scan must walk (almost) the whole list
    exp = (set(range(n + 1)) - set(a[0])).pop()
    return {"name": f"p{n}", "args": a, "wrap": ["ints"], "expected": exp}


PROBES = [_probe(200, 1), _probe(800, 2)]


def runtime_rule(tr: dict) -> str | None:
    a, b = probe(tr, "p200"), probe(tr, "p800")
    if a is None or b is None or a.get("error") or b.get("error"):
        return None
    n = 200
    xor = opcount(a, "xor")
    add = opcount(a, "add", "sub")
    h = opcount(a, "hash")
    idx = opcount(a, "index")
    sorts = ccount(a, "sorted", "list.sort")
    bis = ccount(a, "bisect_left", "bisect_right", "bisect")
    growth = b["lines"] / max(a["lines"], 1)
    total = sum(a.get("ops", {}).values())
    if xor >= 0.5 * n:
        return "xor_fold"
    if sorts >= 1 or opcount(a, "cmp") >= n * 3:
        if bis >= 1:
            return "sort_binary_search"
        return "sort_scan" if growth >= 2.5 else "sort_binary_search"
    if h >= 0.5 * n or idx >= 0.5 * n:
        return "hash_set"
    if add >= 0.5 * n:
        return "arithmetic_sum"
    if total == 0:
        return None
    return "other"


def ast_rule(code: str) -> str | None:
    t = ast_tree(code)
    if t is None:
        return None
    calls = calls_named(t)
    ops = binops(t)
    names = names_used(t)
    if "BitXor" in ops or "xor" in names or "ixor" in names:
        return "xor_fold"
    if "sorted" in calls or "sort" in calls:
        if any(c in calls for c in ("bisect_left", "bisect_right", "bisect")):
            return "sort_binary_search"
        has_mid = any(isinstance(n, ast.BinOp) and isinstance(n.op, (ast.FloorDiv, ast.RShift))
                      and isinstance(n.left, ast.BinOp) and isinstance(n.left.op, ast.Add) for n in ast.walk(t))
        has_while = any(isinstance(n, ast.While) for n in ast.walk(t))
        return "sort_binary_search" if (has_mid and has_while) else "sort_scan"
    has_set = "set" in calls or any(isinstance(n, (ast.Set, ast.SetComp)) for n in ast.walk(t)) \
        or any(c in calls for c in ("Counter", "dict", "fromkeys"))
    presence = any(isinstance(n, ast.BinOp) and isinstance(n.op, ast.Mult) and isinstance(n.left, ast.List)
                   for n in ast.walk(t))
    if has_set or presence:
        return "hash_set"
    if "sum" in calls or ("Mult" in ops and ("FloorDiv" in ops or "Div" in ops)):
        return "arithmetic_sum"
    return "other"
