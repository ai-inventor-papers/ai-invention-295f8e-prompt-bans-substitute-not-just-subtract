"""II4 peak_index (LeetCode 162; validity checker: any peak index is accepted). Probes: a strictly increasing list
(a linear scan reads n values, the halving search ~log n, the maximum is found by C-level comparisons) and a list
whose first descent is at index 1 (the linear scan stops at once; the argmax still reads every value)."""

from __future__ import annotations

import random

from unitlib import ast_tree, calls_named, has_loop, opcount, probe
from units.ii_common import has_midpoint, return_inside_loop

CHECKER = "peak"
ARGS = ["nums"]

ORACLE_A = '''
def solve(nums):
    left, right = 0, len(nums) - 1
    while left < right:
        mid = (left + right) >> 1
        if nums[mid] > nums[mid + 1]:
            right = mid
        else:
            left = mid + 1
    return left
'''  # dataset reference (LeetCode 162 row), adapted
ORACLE_B = '''
def solve(nums):
    best = 0
    for i in range(1, len(nums)):
        if nums[i] > nums[best]:
            best = i
    return best
'''

REFERENCES = {
    "binary_search_slope": ORACLE_A,
    "linear_scan": '''
def solve(nums):
    for i in range(len(nums) - 1):
        if nums[i] > nums[i + 1]:
            return i
    return len(nums) - 1
''',
    "index_of_max": '''
def solve(nums):
    return nums.index(max(nums))
''',
}
MUTANTS = [
    '''
def solve(nums):
    return 0
''',
    '''
def solve(nums):
    for i in range(len(nums) - 1):
        if nums[i] > nums[i + 1]:
            return i + 1
    return len(nums) - 1
''',
    '''
def solve(nums):
    lo, hi = 0, len(nums) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if nums[mid] > nums[mid + 1]:
            lo = mid + 1
        else:
            hi = mid
    return lo
''',
]
EXCLUDED: dict[str, str] = {}
LO, HI = -2147483648, 2147483647


def _fix(a: list[int]) -> list[int]:
    for i in range(1, len(a)):
        if a[i] == a[i - 1]:
            a[i] = a[i] + 1 if a[i] < HI else a[i] - 1
            if i >= 2 and a[i] == a[i - 1]:
                a[i] -= 2
    return a


def _rand(rng: random.Random, n: int, span: int) -> list[int]:
    return _fix([rng.randint(-span, span) for _ in range(n)])


def make_tests() -> list[dict]:
    rng = random.Random(162)
    cases = [("ex0", [[1, 2, 3, 1]]), ("ex1", [[1, 2, 1, 3, 5, 6, 4]]), ("edge0", [[5]]), ("edge1", [[1, 2]]),
             ("edge2", [[2, 1]]), ("edge3", [[LO, HI]]), ("edge4", [[HI, LO, HI]]), ("edge5", [[3, 2, 1]])]
    i = 0
    while len(cases) < 8 + 55:
        n = rng.choice([1, 2, 3, 5, 10, 50, 100, 1000, 5000])
        kind = i % 4
        if kind == 0:
            a = _rand(rng, n, rng.choice([3, 100, HI]))
        elif kind == 1:
            a = sorted(rng.sample(range(-10 ** 6, 10 ** 6), n))
        elif kind == 2:
            a = sorted(rng.sample(range(-10 ** 6, 10 ** 6), n), reverse=True)
        else:
            p = rng.randrange(n)
            a = sorted(rng.sample(range(-10 ** 6, 0), p + 1)) + sorted(rng.sample(range(-10 ** 6, 0), n - p - 1),
                                                                     reverse=True)
            a = _fix(a)
        cases.append((f"rand{i}", [a]))
        i += 1
    n = 100000
    stress = [list(range(n)), list(range(n, 0, -1)), _rand(rng, n, HI), _rand(rng, n, 2),
              list(range(n // 2)) + list(range(n // 2, 0, -1)), [((-1) ** k) * k for k in range(n)],
              list(range(-n, 0)), _rand(rng, n, 1000), list(range(0, 2 * n, 2)), list(range(n - 1, -1, -1))]
    for j, a in enumerate(stress):
        cases.append((f"stress{j}", [_fix(list(a))]))
    return [{"case_id": f"II4:{cid}", "kind": "stress" if cid.startswith("stress") else
             ("example" if cid.startswith(("ex", "edge")) else "random"), "args": a} for cid, a in cases]


PROBES = [{"name": "p_inc", "args": [list(range(4096))], "wrap": ["ints"], "expected": 4095},
          {"name": "p_early", "args": [[0, 100000] + list(range(1, 4095))], "wrap": ["ints"], "expected": None}]


def runtime_rule(tr: dict) -> str | None:
    a, b = probe(tr, "p_inc"), probe(tr, "p_early")
    if a is None or b is None or a.get("error") or b.get("error"):
        return None
    ca = opcount(a, "cmp", "eq")
    cb = opcount(b, "cmp", "eq")
    if ca <= 200 and cb <= 200:
        return "binary_search_slope"
    if cb <= 50 and ca >= 2000:
        return "linear_scan"
    if ca >= 2000 and cb >= 2000:
        return "index_of_max"
    if ca == 0 and cb == 0:
        return None
    return "other"


def ast_rule(code: str) -> str | None:
    t = ast_tree(code)
    if t is None:
        return None
    calls = calls_named(t)
    if has_midpoint(t):
        return "binary_search_slope"
    if "max" in calls:
        return "index_of_max"
    if has_loop(t):
        return "linear_scan" if return_inside_loop(t) else "index_of_max"
    return "other"
