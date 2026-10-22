"""B2 single_number (LeetCode 136, widened to len(nums) <= 100001 so list.count scanning fails)."""

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
    return reduce(xor, nums)
'''  # dataset reference (LeetCode 136 row), adapted
ORACLE_B = '''
def solve(nums):
    from collections import Counter
    return next(v for v, c in Counter(nums).items() if c == 1)
'''

REFERENCES = {
    "xor_fold": '''
def solve(nums):
    r = 0
    for v in nums:
        r ^= v
    return r
''',
    "hash_count": '''
def solve(nums):
    counts = {}
    for v in nums:
        counts[v] = counts.get(v, 0) + 1
    for v, c in counts.items():
        if c == 1:
            return v
''',
    "set_sum_identity": '''
def solve(nums):
    return 2 * sum(set(nums)) - sum(nums)
''',
    "sort_pair_scan": '''
def solve(nums):
    a = sorted(nums)
    for i in range(0, len(a) - 1, 2):
        if a[i] != a[i + 1]:
            return a[i]
    return a[-1]
''',
}
MUTANTS = [
    '''
def solve(nums):
    a = sorted(nums)
    for i in range(0, len(a) - 1, 2):
        if a[i] != a[i + 1]:
            return a[i]
''',
    '''
def solve(nums):
    return sum(set(nums)) - sum(nums) // 2
''',
    '''
def solve(nums):
    return nums[0]
''',
]
EXCLUDED = {
    "list_count_scan": '''
def solve(nums):
    for v in nums:
        if nums.count(v) == 1:
            return v
''',
}


def _case(rng: random.Random, m: int, single_last: bool = False) -> list:
    vals = rng.sample(range(-30000, 30001), m + 1)
    single, pairs = vals[0], vals[1:]
    a = pairs + pairs
    rng.shuffle(a)
    if single_last:
        a.append(single)
    else:
        a.insert(rng.randint(0, len(a)), single)
    return [a]


def make_tests() -> list[dict]:
    rng = random.Random(136)
    cases = [("ex0", [[2, 2, 1]]), ("ex1", [[4, 1, 2, 1, 2]]), ("ex2", [[1]]), ("edge0", [[-30000]]),
             ("edge1", [[30000, -30000, 30000]])]
    sizes = [1, 1, 2, 3, 5, 8, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000]
    i = 0
    while len(cases) < 5 + 50:
        m = sizes[i % len(sizes)]
        cases.append((f"rand{i}", _case(rng, m, single_last=(i % 3 == 0))))
        i += 1
    for j in range(10):
        cases.append((f"stress{j}", _case(rng, 50000, single_last=(j % 2 == 0))))
    return [{"case_id": f"B2:{cid}", "kind": "stress" if cid.startswith("stress") else
             ("example" if cid.startswith("ex") else "random"), "args": a} for cid, a in cases]


def _probe(m: int, seed: int) -> dict:
    a = _case(random.Random(seed), m, single_last=True)
    from collections import Counter
    return {"name": f"p{2 * m + 1}", "args": a, "wrap": ["ints"],
            "expected": next(v for v, c in Counter(a[0]).items() if c == 1)}


PROBES = [_probe(100, 3), _probe(400, 4)]


def runtime_rule(tr: dict) -> str | None:
    a = probe(tr, "p201")
    if a is None or a.get("error"):
        return None
    n = 201
    xor = opcount(a, "xor")
    add = opcount(a, "add", "sub")
    h = opcount(a, "hash")
    sorts = ccount(a, "sorted", "list.sort")
    total = sum(a.get("ops", {}).values())
    if xor >= 0.5 * n:
        return "xor_fold"
    if h >= 0.5 * n and add >= 0.5 * n:
        return "set_sum_identity"
    if sorts >= 1 or opcount(a, "cmp") >= 3 * n:
        return "sort_pair_scan"
    if h >= 0.5 * n:
        return "hash_count"
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
    has_set = "set" in calls or any(isinstance(n, (ast.Set, ast.SetComp)) for n in ast.walk(t))
    if "sum" in calls and has_set:
        return "set_sum_identity"
    if "sorted" in calls or "sort" in calls:
        return "sort_pair_scan"
    if has_set or any(c in calls for c in ("Counter", "defaultdict", "get", "dict", "setdefault")) or \
            any(isinstance(n, (ast.Dict, ast.DictComp)) for n in ast.walk(t)):
        return "hash_count"
    return "other"


def sublabel(code: str) -> str | None:
    """Split-label sensitivity (plan): hash_count/toggle = set membership toggling; hash_count/count = counts."""
    t = ast_tree(code)
    if t is None:
        return None
    calls = calls_named(t)
    if ("remove" in calls or "discard" in calls) and ("add" in calls):
        return "hash_count/toggle"
    return "hash_count/count"
