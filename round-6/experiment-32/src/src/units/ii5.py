"""II5 all_arrangements (LeetCode 46 permutations; order-free checker: exactly n! distinct arrangements, each a
rearrangement of nums). Runtime signals: the patched itertools.permutations constructor, recursion depth and
list.insert calls; the runtime rule ABSTAINS (None) between the recursive families (used flags / swaps / recursive
Heap's), which the AST decides (exp26 gate_abstention convention)."""

from __future__ import annotations

import random
import re

from unitlib import ast_tree, calls_named, ccount, names_used, pcount, probe, recursive_functions
from units.ii_common import has_parity_test, tuple_swap

CHECKER = "perms"
ARGS = ["nums"]

ORACLE_A = '''
def solve(nums):
    n = len(nums)
    vis = [False] * n
    t = [0] * n
    ans = []

    def dfs(i):
        if i >= n:
            ans.append(t[:])
            return
        for j, x in enumerate(nums):
            if not vis[j]:
                vis[j] = True
                t[i] = x
                dfs(i + 1)
                vis[j] = False

    dfs(0)
    return ans
'''  # dataset reference (LeetCode 46 row), adapted
ORACLE_B = '''
def solve(nums):
    from itertools import permutations
    return [list(p) for p in permutations(nums)]
'''

REFERENCES = {
    "backtracking_used": ORACLE_A,
    "swap_backtracking": '''
def solve(nums):
    a = list(nums)
    out = []

    def go(i):
        if i == len(a):
            out.append(a[:])
            return
        for j in range(i, len(a)):
            a[i], a[j] = a[j], a[i]
            go(i + 1)
            a[i], a[j] = a[j], a[i]

    go(0)
    return out
''',
    "library_permutations": ORACLE_B,
    "heaps_algorithm": '''
def solve(nums):
    a = list(nums)
    n = len(a)
    c = [0] * n
    out = [a[:]]
    i = 0
    while i < n:
        if c[i] < i:
            if i % 2 == 0:
                a[0], a[i] = a[i], a[0]
            else:
                a[c[i]], a[i] = a[i], a[c[i]]
            out.append(a[:])
            c[i] += 1
            i = 0
        else:
            c[i] = 0
            i += 1
    return out
''',
    "insertion_build": '''
def solve(nums):
    res = [[]]
    for x in nums:
        res = [p[:i] + [x] + p[i:] for p in res for i in range(len(p) + 1)]
    return res
''',
}
MUTANTS = [
    '''
def solve(nums):
    return [list(nums)]
''',
    '''
def solve(nums):
    res = [[]]
    for x in nums:
        res = [p[:i] + [x] + p[i:] for p in res for i in range(len(p))] or [[x]]
    return res
''',
    '''
def solve(nums):
    a = list(nums)
    out = []

    def go(i):
        if i == len(a):
            out.append(a[:])
            return
        for j in range(i, len(a)):
            a[i], a[j] = a[j], a[i]
            go(i + 1)

    go(0)
    return out
''',
]
EXCLUDED: dict[str, str] = {}


def make_tests() -> list[dict]:
    rng = random.Random(46)
    cases = [("ex0", [[1, 2, 3]]), ("ex1", [[0, 1]]), ("ex2", [[1]]), ("edge0", [[-10, 10]]),
             ("edge1", [[5, -3, 0, 7]])]
    i = 0
    while len(cases) < 5 + 40:
        n = rng.randint(1, 6)
        cases.append((f"rand{i}", [rng.sample(range(-10, 11), n)]))
        i += 1
    for j in range(8):
        cases.append((f"stress{j}", [rng.sample(range(-10, 11), 7)]))
    out = []
    import math
    for cid, a in cases:
        out.append({"case_id": f"II5:{cid}", "kind": "stress" if cid.startswith("stress") else
                    ("example" if cid.startswith(("ex", "edge")) else "random"), "args": a})
    return out


PROBES = [{"name": "p6", "args": [[4, -2, 9, 0, 7, -5]], "wrap": ["ints"], "expected": None}]


WANTS_CODE = True
SWAP_RE = re.compile(r"(\w+)\[([^\]]+)\]\s*,\s*\1\[([^\]]+)\]\s*=\s*\1\[\3\]\s*,\s*\1\[\2\]")
INSERT_RE = re.compile(r"\.insert\(|\[:\s*\w+\s*\]\s*\+\s*\[")
PARITY_RE = re.compile(r"%\s*2\b|&\s*1\b")


def runtime_rule(tr: dict) -> str | None:
    """Executed-line profile on the n = 6 probe (720 arrangements): only source lines executed >= 50 times count
    (dead helpers and one-off setup are ignored), combined with the recursion depth and the patched constructor."""
    a = probe(tr, "p6")
    if a is None or a.get("error"):
        return None
    if pcount(a, "itertools.permutations") >= 1:
        return "library_permutations"
    src = (tr.get("_code") or "").splitlines()
    hot = [src[int(k) - 1] for k, v in (a.get("line_counts") or {}).items()
           if v >= 50 and 0 < int(k) <= len(src)]
    if not hot:
        return None
    d = int(a.get("max_depth") or 0)
    swap = any(SWAP_RE.search(l) for l in hot)
    parity = any(PARITY_RE.search(l) for l in hot)
    if swap and parity:
        return "heaps_algorithm"
    if swap and d >= 6:
        return "swap_backtracking"
    if any(INSERT_RE.search(l) for l in hot) or ccount(a, "list.insert") >= 100:
        return "insertion_build"
    if d >= 6:
        return "backtracking_used"
    return "other"


def ast_rule(code: str) -> str | None:
    t = ast_tree(code)
    if t is None:
        return None
    calls = calls_named(t)
    names = names_used(t)
    if "permutations" in names:
        return "library_permutations"
    swap = tuple_swap(t)
    rec = bool(recursive_functions(t))
    if swap and has_parity_test(t):
        return "heaps_algorithm"
    if swap and rec:
        return "swap_backtracking"
    if "insert" in calls:
        return "insertion_build"
    src = code.replace(" ", "")
    if "[:i]+[" in src or ":i]+[" in src:
        return "insertion_build"
    if rec:
        return "backtracking_used"
    if any(c in calls for c in ("append", "extend")) and ("remove" in calls or "not in" in code or "set" in calls
                                                          or "used" in names or "visited" in names):
        return "backtracking_used"
    return "other"
