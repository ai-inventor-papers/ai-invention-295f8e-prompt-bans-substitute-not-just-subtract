"""B5 all_subsets (LeetCode 78; order-free checker comparing multisets of selections)."""

from __future__ import annotations

import ast
import random

from unitlib import ast_tree, binops, calls_named, ccount, pcount, probe, recursive_functions

CHECKER = "subsets"
ARGS = ["nums"]

ORACLE_A = '''
def solve(nums):
    ans = []
    t = []
    def dfs(i):
        if i == len(nums):
            ans.append(t[:])
            return
        dfs(i + 1)
        t.append(nums[i])
        dfs(i + 1)
        t.pop()
    dfs(0)
    return ans
'''  # dataset reference (LeetCode 78 row), adapted
ORACLE_B = '''
def solve(nums):
    n = len(nums)
    return [[nums[j] for j in range(n) if m >> j & 1] for m in range(1 << n)]
'''

REFERENCES = {
    "backtracking": '''
def solve(nums):
    res = []
    path = []
    def bt(start):
        res.append(path[:])
        for i in range(start, len(nums)):
            path.append(nums[i])
            bt(i + 1)
            path.pop()
    bt(0)
    return res
''',
    "bitmask_enumeration": '''
def solve(nums):
    n = len(nums)
    out = []
    for mask in range(1 << n):
        sub = []
        for j in range(n):
            if mask & (1 << j):
                sub.append(nums[j])
        out.append(sub)
    return out
''',
    "iterative_doubling": '''
def solve(nums):
    res = [[]]
    for x in nums:
        res += [s + [x] for s in res]
    return res
''',
    "itertools_combinations": '''
from itertools import combinations

def solve(nums):
    out = []
    for r in range(len(nums) + 1):
        out.extend(list(c) for c in combinations(nums, r))
    return out
''',
}
MUTANTS = [
    '''
def solve(nums):
    res = [[]]
    for x in nums:
        res += [s + [x] for s in res]
    return res[1:]
''',
    '''
def solve(nums):
    res = []
    path = []
    def bt(start):
        res.append(path)
        for i in range(start, len(nums)):
            path.append(nums[i])
            bt(i + 1)
            path.pop()
    bt(0)
    return res
''',
    '''
from itertools import combinations

def solve(nums):
    out = []
    for r in range(1, len(nums) + 1):
        out.extend(list(c) for c in combinations(nums, r))
    return out
''',
]
EXCLUDED: dict[str, str] = {}


def make_tests() -> list[dict]:
    rng = random.Random(78)
    cases = [("ex0", [[1, 2, 3]]), ("ex1", [[0]]), ("ex2", [[1, 2]]), ("edge0", [[-10, 10]])]
    i = 0
    while len(cases) < 4 + 46:
        n = 1 + i % 10
        cases.append((f"rand{i}", [rng.sample(range(-10, 11), n)]))
        i += 1
    for j in range(10):
        cases.append((f"stress{j}", [rng.sample(range(-10, 11), 10)]))
    return [{"case_id": f"B5:{cid}", "kind": "stress" if cid.startswith("stress") else
             ("example" if cid.startswith(("ex", "edge")) else "random"), "args": a} for cid, a in cases]


def _probe(n: int, seed: int) -> dict:
    a = random.Random(seed).sample(range(-10, 11), n)
    return {"name": f"n{n}", "args": [a], "wrap": ["ints"], "checker": "subsets",
            "expected": [[a[j] for j in range(n) if m >> j & 1] for m in range(1 << n)]}


PROBES = [_probe(4, 7), _probe(8, 8)]


def runtime_rule(tr: dict) -> str | None:
    a, b = probe(tr, "n4"), probe(tr, "n8")
    if a is None or b is None or a.get("error") or b.get("error"):
        return None
    n = 8
    if pcount(b, "itertools.combinations") >= 1:
        return "itertools_combinations"
    calls = b["user_calls"] - 1
    pops = ccount(b, "list.pop", "pop")
    apps = ccount(b, "list.append", "append")
    if calls >= 2 ** n * 0.9:
        return "backtracking"
    if b["max_depth"] >= n and n - 1 <= calls <= 3 * n + 3:
        return "iterative_doubling"
    if pops >= 2 ** n * 0.5:
        return "backtracking"
    if b["lines"] == 0:
        return None
    if apps >= 2.5 * 2 ** n:
        return "bitmask_enumeration"
    ratio = b["lines"] / max(a["lines"], 1)
    return "bitmask_enumeration" if ratio >= 24 else "iterative_doubling"


def ast_rule(code: str) -> str | None:
    t = ast_tree(code)
    if t is None:
        return None
    calls = calls_named(t)
    if "combinations" in calls:
        return "itertools_combinations"
    rec = recursive_functions(t)
    if rec:
        for f in ast.walk(t):
            if isinstance(f, ast.FunctionDef) and f.name in rec:
                for n in ast.walk(f):
                    if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == f.name:
                        if any(isinstance(a, ast.Subscript) and isinstance(a.slice, ast.Slice) for a in n.args):
                            return "iterative_doubling"
        return "backtracking"
    ops = binops(t)
    uses_pow2 = ("LShift" in ops) or any(isinstance(n, ast.BinOp) and isinstance(n.op, ast.Pow) and
                                         isinstance(n.left, ast.Constant) and n.left.value == 2
                                         for n in ast.walk(t))
    if uses_pow2 and ("BitAnd" in ops or "RShift" in ops):
        return "bitmask_enumeration"
    if "pop" in calls and "append" in calls:
        return "backtracking"
    if any(isinstance(n, (ast.ListComp, ast.For)) for n in ast.walk(t)):
        return "iterative_doubling"
    return "other"
