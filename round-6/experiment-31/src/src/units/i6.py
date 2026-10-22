"""I6 three values in place (LeetCode 75 sort colors; in-place checker; n <= 200000 so quadratic exchange sorts exceed
the limit)."""

from __future__ import annotations

import ast
import random

from unitlib6 import ast_tree, call, calls_named, lst, op, probe, tuple_swaps

CHECKER = "inplace"
ARGS = ["nums"]

ORACLE_A = '''
def solve(nums):
    i, j, k = -1, len(nums), 0
    while k < j:
        if nums[k] == 0:
            i += 1
            nums[i], nums[k] = nums[k], nums[i]
            k += 1
        elif nums[k] == 2:
            j -= 1
            nums[j], nums[k] = nums[k], nums[j]
        else:
            k += 1
'''  # dataset reference (LeetCode 75 row)
ORACLE_B = '''
def solve(nums):
    c = [nums.count(0), nums.count(1), nums.count(2)]
    nums[:] = [0] * c[0] + [1] * c[1] + [2] * c[2]
'''

REFERENCES = {
    "dutch_flag": '''
def solve(nums):
    low, mid, high = 0, 0, len(nums) - 1
    while mid <= high:
        if nums[mid] == 0:
            nums[low], nums[mid] = nums[mid], nums[low]
            low += 1
            mid += 1
        elif nums[mid] == 1:
            mid += 1
        else:
            nums[mid], nums[high] = nums[high], nums[mid]
            high -= 1
''',
    "counting_overwrite": '''
def solve(nums):
    c0 = c1 = 0
    for v in nums:
        if v == 0:
            c0 += 1
        elif v == 1:
            c1 += 1
    for i in range(len(nums)):
        if i < c0:
            nums[i] = 0
        elif i < c0 + c1:
            nums[i] = 1
        else:
            nums[i] = 2
''',
    "builtin_sort": '''
def solve(nums):
    nums.sort()
''',
    "two_pass_partition": '''
def solve(nums):
    b = 0
    for i in range(len(nums)):
        if nums[i] == 0:
            nums[i], nums[b] = nums[b], nums[i]
            b += 1
    for i in range(b, len(nums)):
        if nums[i] == 1:
            nums[i], nums[b] = nums[b], nums[i]
            b += 1
''',
}
MUTANTS = [
    '''
def solve(nums):
    low, mid, high = 0, 0, len(nums) - 1
    while mid < high:
        if nums[mid] == 0:
            nums[low], nums[mid] = nums[mid], nums[low]
            low += 1
            mid += 1
        elif nums[mid] == 1:
            mid += 1
        else:
            nums[mid], nums[high] = nums[high], nums[mid]
            high -= 1
''',
    '''
def solve(nums):
    return sorted(nums)
''',
    '''
def solve(nums):
    c0 = nums.count(0)
    for i in range(len(nums)):
        nums[i] = 0 if i < c0 else 2
''',
]
EXCLUDED = {
    "quadratic_exchange_sort": '''
def solve(nums):
    n = len(nums)
    for i in range(n):
        for j in range(n - 1 - i):
            if nums[j] > nums[j + 1]:
                nums[j], nums[j + 1] = nums[j + 1], nums[j]
''',
}


def make_tests() -> list[dict]:
    rng = random.Random(75)
    cases = [("ex0", [[2, 0, 2, 1, 1, 0]]), ("ex1", [[2, 0, 1]]), ("edge_one", [[1]]), ("edge_two", [[2, 0]]),
             ("edge_all2", [[2, 2, 2]]), ("edge_sorted", [[0, 0, 1, 2, 2]]), ("edge_rev", [[2, 2, 1, 1, 0, 0]])]
    sizes = [1, 2, 3, 5, 8, 13, 20, 50, 100, 300, 1000, 5000]
    for i in range(46):
        n = sizes[i % len(sizes)]
        w = rng.choice([(1, 1, 1), (5, 1, 1), (1, 5, 1), (1, 1, 5), (0, 1, 1), (1, 0, 1)])
        cases.append((f"rand{i}", [rng.choices([0, 1, 2], weights=w, k=n)]))
    for j in range(6):
        n = 200000
        if j % 3 == 0:
            a = [2] * (n // 3) + [1] * (n // 3) + [0] * (n - 2 * (n // 3))
        else:
            a = rng.choices([0, 1, 2], k=n)
        cases.append((f"stress{j}", [a]))
    return [{"case_id": f"I6:{cid}", "kind": "stress" if cid.startswith("stress") else
             ("example" if cid.startswith("ex") else "random"), "args": a} for cid, a in cases]


def _probe(n: int, seed: int, name: str) -> dict:
    rng = random.Random(seed)
    a = rng.choices([0, 1, 2], k=n)
    return {"name": name, "args": [a], "wrap": ["list"], "expected": sorted(a), "checker": "inplace"}


PROBES = [_probe(150, 11, "p150"), _probe(300, 12, "p300")]


def runtime_rule(tr: dict) -> str | None:
    a = probe(tr, "p150")
    if a is None:
        return None
    n = 150
    if call(a, "sort", "sorted") >= 1:
        return "builtin_sort"
    swaps = op(a, "SWAP")
    iters = op(a, "JUMP_BACKWARD")
    if swaps >= n // 4 or (lst(a, "setitem") >= n // 2 and swaps >= n // 8):
        if iters >= n * n // 8:
            return "other"
        if iters >= int(1.3 * n):
            return "two_pass_partition"
        return "dutch_flag"
    if call(a, "count") >= 2 or lst(a, "setitem") >= 1:
        if iters >= n * n // 8:
            return "other"
        return "counting_overwrite"
    return "other"


def ast_rule(code: str) -> str | None:
    t = ast_tree(code)
    if t is None:
        return None
    calls = calls_named(t)
    if "sort" in calls or "sorted" in calls:
        return "builtin_sort"
    loops = [n for n in ast.walk(t) if isinstance(n, (ast.For, ast.While))]
    nested = any(isinstance(m, (ast.For, ast.While)) for L in loops for m in ast.walk(L) if m is not L)
    sw = tuple_swaps(t)
    if sw >= 1:
        if nested:
            outer_while = any(isinstance(L, ast.While) for L in loops)
            if not outer_while:
                return "other"
        top = [n for n in t.body if isinstance(n, ast.FunctionDef) and n.name == "solve"]
        body = top[0].body if top else []
        n_top_loops = sum(1 for s in body if isinstance(s, (ast.For, ast.While)))
        if n_top_loops >= 2:
            return "two_pass_partition"
        return "dutch_flag"
    if "count" in calls or any(isinstance(n, ast.AugAssign) for n in ast.walk(t)):
        return "counting_overwrite"
    return "other"
