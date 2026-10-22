"""I8 first missing positive (LeetCode 41; n <= 100000 so the quadratic membership search exceeds the limit)."""

from __future__ import annotations

import ast
import random

from unitlib6 import ast_tree, call, calls_named, has_set_literal, lst, maxlen, op, probe, subscript_stores, \
    tuple_swaps

CHECKER = "exact"
ARGS = ["nums"]

ORACLE_A = '''
def solve(nums):
    nums = list(nums)
    n = len(nums)
    for i in range(n):
        while 1 <= nums[i] <= n and nums[i] != nums[nums[i] - 1]:
            j = nums[i] - 1
            nums[i], nums[j] = nums[j], nums[i]
    for i in range(n):
        if nums[i] != i + 1:
            return i + 1
    return n + 1
'''  # dataset reference (LeetCode 41 row; works on a copy)
ORACLE_B = '''
def solve(nums):
    s = set(nums)
    x = 1
    while x in s:
        x += 1
    return x
'''

REFERENCES = {
    "cyclic_placement": '''
def solve(nums):
    n = len(nums)
    for i in range(n):
        while 1 <= nums[i] <= n and nums[nums[i] - 1] != nums[i]:
            j = nums[i] - 1
            nums[i], nums[j] = nums[j], nums[i]
    for i in range(n):
        if nums[i] != i + 1:
            return i + 1
    return n + 1
''',
    "sign_marking": '''
def solve(nums):
    n = len(nums)
    for i in range(n):
        if nums[i] <= 0 or nums[i] > n:
            nums[i] = n + 1
    for i in range(n):
        v = abs(nums[i])
        if v <= n and nums[v - 1] > 0:
            nums[v - 1] = -nums[v - 1]
    for i in range(n):
        if nums[i] > 0:
            return i + 1
    return n + 1
''',
    "hash_set_scan": '''
def solve(nums):
    present = set(nums)
    k = 1
    while k in present:
        k += 1
    return k
''',
    "sort_scan": '''
def solve(nums):
    want = 1
    for v in sorted(nums):
        if v == want:
            want += 1
        elif v > want:
            break
    return want
''',
    "presence_array": '''
def solve(nums):
    n = len(nums)
    seen = [False] * (n + 2)
    for v in nums:
        if 1 <= v <= n + 1:
            seen[v] = True
    for k in range(1, n + 2):
        if not seen[k]:
            return k
    return n + 2
''',
}
MUTANTS = [
    '''
def solve(nums):
    s = set(nums)
    x = 0
    while x in s:
        x += 1
    return x
''',
    '''
def solve(nums):
    return max(nums) + 1 if max(nums) > 0 else 1
''',
    '''
def solve(nums):
    want = 1
    for v in sorted(nums):
        if v == want:
            want += 1
    return want if want > 1 else 2
''',
]
EXCLUDED = {
    "quadratic_search": '''
def solve(nums):
    x = 1
    while x in nums:
        x += 1
    return x
''',
}


def make_tests() -> list[dict]:
    rng = random.Random(41)
    cases = [("ex0", [[1, 2, 0]]), ("ex1", [[3, 4, -1, 1]]), ("ex2", [[7, 8, 9, 11, 12]]), ("edge_one", [[1]]),
             ("edge_neg", [[-5]]), ("edge_dups", [[1, 1, 2, 2]]), ("edge_ext", [[2 ** 31 - 1, -2 ** 31]]),
             ("edge_perm", [[3, 1, 2]])]
    sizes = [1, 2, 3, 5, 8, 13, 20, 50, 100, 300, 1000, 5000]
    for i in range(45):
        n = sizes[i % len(sizes)]
        kind = i % 3
        if kind == 0:
            a = list(range(1, n + 1))
            rng.shuffle(a)
            if n > 1:
                a[rng.randrange(n)] = rng.choice([0, -1, n + 5])
        elif kind == 1:
            a = [rng.randint(-n, 2 * n) for _ in range(n)]
        else:
            a = [rng.randint(-2 ** 31, 2 ** 31 - 1) for _ in range(n)]
        cases.append((f"rand{i}", [a]))
    for j in range(6):
        n = 100000
        a = list(range(1, n + 1))
        rng.shuffle(a)
        if j % 2 == 1:
            a[rng.randrange(n)] = -7
        cases.append((f"stress{j}", [a]))
    return [{"case_id": f"I8:{cid}", "kind": "stress" if cid.startswith("stress") else
             ("example" if cid.startswith("ex") else "random"), "args": a} for cid, a in cases]


def _probe(n: int, seed: int, name: str) -> dict:
    rng = random.Random(seed)
    a = list(range(1, n + 1))
    rng.shuffle(a)
    miss = rng.randrange(n // 2, n)
    a = [v if v != miss else -3 for v in a] + [n + 7, 0]
    rng.shuffle(a)
    return {"name": name, "args": [a], "wrap": ["list"], "expected": miss, "checker": "exact"}


PROBES = [_probe(200, 13, "p200"), _probe(400, 14, "p400")]


def runtime_rule(tr: dict) -> str | None:
    a = probe(tr, "p200")
    if a is None:
        return None
    n = 202
    if lst(a, "contains") >= 20:
        return "other"
    if call(a, "sorted", "sort") >= 1 and max(maxlen(a, "sorted", "sort"), 0) >= n // 2:
        return "sort_scan"
    neg = op(a, "UNARY_NEGATIVE") + call(a, "abs")
    if neg >= n // 3 and lst(a, "setitem") >= n // 3:
        return "sign_marking"
    if op(a, "SWAP") >= n // 4 and lst(a, "setitem") >= n // 4:
        return "cyclic_placement"
    if lst(a, "setitem") >= n // 2:
        return "cyclic_placement"
    if max(maxlen(a, "set", "frozenset"), -1) >= n // 2 or call(a, "add") >= n // 2:
        return "hash_set_scan"
    if op(a, "STORE_SUBSCR") >= n // 2:
        return "presence_array"
    if op(a, "CONTAINS_OP") >= n // 2:
        return "hash_set_scan"
    return "other"


def ast_rule(code: str) -> str | None:
    t = ast_tree(code)
    if t is None:
        return None
    calls = calls_named(t)
    if "sorted" in calls or "sort" in calls:
        return "sort_scan"
    arg = None
    for f in ast.walk(t):
        if isinstance(f, ast.FunctionDef) and f.name == "solve" and f.args.args:
            arg = f.args.args[0].arg
    negs = any(isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.USub) and not isinstance(n.operand, ast.Constant)
               for n in ast.walk(t)) or "abs" in calls
    stores_in = subscript_stores(t, arg) if arg else 0
    if negs and stores_in >= 1:
        return "sign_marking"
    if tuple_swaps(t) >= 1 and stores_in >= 1:
        return "cyclic_placement"
    if has_set_literal(t):
        return "hash_set_scan"
    if subscript_stores(t) >= 1 and stores_in == 0:
        return "presence_array"
    if stores_in >= 1:
        return "cyclic_placement"
    if any(isinstance(n, ast.Dict) for n in ast.walk(t)) or "dict" in calls:
        return "hash_set_scan"
    return "other"
