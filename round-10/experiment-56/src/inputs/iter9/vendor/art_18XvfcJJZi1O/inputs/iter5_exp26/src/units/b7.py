"""B7 count_inversions (statement from the TheAlgorithms/XLCoST rows of the dataset; n <= 20000 so the O(n^2)
pair scan fails the limit while sorted insertion with bisect passes)."""

from __future__ import annotations

import ast
import random

from unitlib import ast_tree, binops, calls_named, ccount, names_used, opcount, probe, recursive_functions

CHECKER = "exact"
ARGS = ["nums"]

ORACLE_A = '''
def solve(nums):
    import sys
    sys.setrecursionlimit(10000)
    def sort_count(a):
        if len(a) <= 1:
            return a, 0
        mid = len(a) // 2
        left, x = sort_count(a[:mid])
        right, y = sort_count(a[mid:])
        merged, inv, i, j = [], x + y, 0, 0
        while i < len(left) and j < len(right):
            if left[i] <= right[j]:
                merged.append(left[i]); i += 1
            else:
                merged.append(right[j]); j += 1
                inv += len(left) - i
        merged += left[i:]
        merged += right[j:]
        return merged, inv
    return sort_count(list(nums))[1]
'''  # adapted from the dataset's XLCoST 'Count Inversions in an array | Set 1 (Using Merge Sort)' / TheAlgorithms rows
ORACLE_B = '''
def solve(nums):
    n = len(nums)
    if n <= 600:
        return sum(1 for i in range(n) for j in range(i + 1, n) if nums[i] > nums[j])
    ranks = {v: i + 1 for i, v in enumerate(sorted(set(nums)))}
    m = len(ranks)
    tree = [0] * (m + 1)
    inv = 0
    for k, v in enumerate(nums):
        r = ranks[v]
        s, i = 0, r
        while i > 0:
            s += tree[i]
            i -= i & -i
        inv += k - s
        i = r
        while i <= m:
            tree[i] += 1
            i += i & -i
    return inv
'''  # brute force on small cases; BIT (XLCoST 'Set 3 (Using BIT)' row) on large ones

REFERENCES = {
    "merge_sort_count": ORACLE_A,
    "fenwick_tree": '''
def solve(nums):
    ranks = {v: i + 1 for i, v in enumerate(sorted(set(nums)))}
    m = len(ranks)
    tree = [0] * (m + 1)
    inv = 0
    for k, v in enumerate(nums):
        r = ranks[v]
        s, i = 0, r
        while i > 0:
            s += tree[i]
            i -= i & -i
        inv += k - s
        i = r
        while i <= m:
            tree[i] += 1
            i += i & -i
    return inv
''',
    "segment_tree": '''
def solve(nums):
    vals = sorted(set(nums))
    rank = {v: i for i, v in enumerate(vals)}
    m = len(vals)
    tree = [0] * (4 * m)
    def update(node, lo, hi, pos):
        tree[node] += 1
        if lo == hi:
            return
        mid = (lo + hi) // 2
        if pos <= mid:
            update(2 * node, lo, mid, pos)
        else:
            update(2 * node + 1, mid + 1, hi, pos)
    def query(node, lo, hi, l, r):
        if r < lo or hi < l or l > r:
            return 0
        if l <= lo and hi <= r:
            return tree[node]
        mid = (lo + hi) // 2
        return query(2 * node, lo, mid, l, r) + query(2 * node + 1, mid + 1, hi, l, r)
    inv = 0
    for v in nums:
        p = rank[v]
        inv += query(1, 0, m - 1, p + 1, m - 1)
        update(1, 0, m - 1, p)
    return inv
''',
    "sorted_insertion_bisect": '''
from bisect import bisect_right, insort

def solve(nums):
    seen = []
    inv = 0
    for k, v in enumerate(nums):
        inv += k - bisect_right(seen, v)
        insort(seen, v)
    return inv
''',
}
MUTANTS = [
    '''
from bisect import bisect_left, insort

def solve(nums):
    seen = []
    inv = 0
    for k, v in enumerate(nums):
        inv += k - bisect_left(seen, v)
        insort(seen, v)
    return inv
''',
    '''
def solve(nums):
    def sort_count(a):
        if len(a) <= 1:
            return a, 0
        mid = len(a) // 2
        left, x = sort_count(a[:mid])
        right, y = sort_count(a[mid:])
        merged, inv, i, j = [], x + y, 0, 0
        while i < len(left) and j < len(right):
            if left[i] <= right[j]:
                merged.append(left[i]); i += 1
            else:
                merged.append(right[j]); j += 1
                inv += 1
        merged += left[i:]
        merged += right[j:]
        return merged, inv
    return sort_count(list(nums))[1]
''',
    '''
def solve(nums):
    return sum(1 for i in range(len(nums) - 1) if nums[i] > nums[i + 1])
''',
]
EXCLUDED = {
    "brute_force_pairs": '''
def solve(nums):
    n = len(nums)
    c = 0
    for i in range(n):
        for j in range(i + 1, n):
            if nums[i] > nums[j]:
                c += 1
    return c
''',
}


def make_tests() -> list[dict]:
    rng = random.Random(4242)
    cases = [("ex0", [[3, 1, 2]]), ("ex1", [[2, 2, 1]]), ("edge0", [[5]]), ("edge1", [[1, 2, 3, 4]]),
             ("edge2", [[4, 3, 2, 1]]), ("edge3", [[7, 7, 7]]), ("edge4", [[-10 ** 9, 10 ** 9, -10 ** 9]])]
    sizes = [2, 3, 5, 8, 10, 20, 50, 100, 200, 500, 1000, 2000]
    i = 0
    while len(cases) < 7 + 48:
        n = sizes[i % len(sizes)]
        span = rng.choice([3, 50, 10 ** 9])
        cases.append((f"rand{i}", [[rng.randint(-span, span) for _ in range(n)]]))
        i += 1
    for j in range(10):
        n = 20000
        if j == 0:
            a = list(range(n, 0, -1))
        elif j == 1:
            a = [5] * n
        elif j == 2:
            a = list(range(n))
        else:
            span = 10 ** 9 if j < 8 else 100
            a = [rng.randint(-span, span) for _ in range(n)]
        cases.append((f"stress{j}", [a]))
    return [{"case_id": f"B7:{cid}", "kind": "stress" if cid.startswith("stress") else
             ("example" if cid.startswith(("ex", "edge")) else "random"), "args": a} for cid, a in cases]


def _probe(n: int, seed: int) -> dict:
    rng = random.Random(seed)
    a = [rng.randint(-1000, 1000) for _ in range(n)]
    exp = sum(1 for i in range(n) for j in range(i + 1, n) if a[i] > a[j])
    return {"name": f"n{n}", "args": [a], "wrap": ["ints"], "expected": exp}


PROBES = [_probe(256, 11), _probe(1024, 12)]


def runtime_rule(tr: dict) -> str | None:
    a, b = probe(tr, "n256"), probe(tr, "n1024")
    if a is None or a.get("error"):
        return None
    n = 256
    ins = ccount(a, "insort", "insort_right", "insort_left")
    bis = ccount(a, "bisect_left", "bisect_right", "bisect")
    linsert = ccount(a, "list.insert")
    sorts = ccount(a, "sorted", "list.sort")
    if ins >= n / 2 or (bis >= n / 2 and linsert >= n / 2):
        return "sorted_insertion_bisect"
    if sorts >= n / 4:
        return "other"
    calls = a["user_calls"] - 1
    depth = a["max_depth"]
    if b is not None and not b.get("error") and b["lines"] / max(a["lines"], 1) >= 10:
        return "other"
    if depth >= 7 and n <= calls <= 6 * n and opcount(a, "cmp") >= n * 4:
        return "merge_sort_count"
    if calls >= n * 4:
        return "segment_tree"
    if bis >= n / 2:
        return "fenwick_tree"
    if b is not None and not b.get("error"):
        growth = b["lines"] / max(a["lines"], 1)
        if growth >= 10:
            return "other"
    if sorts >= 1 and opcount(a, "hash") >= n / 2:
        return "fenwick_tree"
    if sum(a.get("ops", {}).values()) == 0:
        return None
    return "other"


def ast_rule(code: str) -> str | None:
    t = ast_tree(code)
    if t is None:
        return None
    calls = calls_named(t)
    names = {x.lower() for x in names_used(t)}
    ops = binops(t)
    if any(c in calls for c in ("insort", "insort_right", "insort_left", "SortedList")) or \
            (any(c in calls for c in ("bisect_left", "bisect_right", "bisect")) and "insert" in calls):
        return "sorted_insertion_bisect"
    neg_and = any(isinstance(n, ast.BinOp) and isinstance(n.op, ast.BitAnd) and
                  (isinstance(n.right, ast.UnaryOp) and isinstance(n.right.op, ast.USub) or
                   isinstance(n.left, ast.UnaryOp) and isinstance(n.left.op, ast.USub)) for n in ast.walk(t))
    if neg_and or any("fenwick" in x or x in ("bit", "bit_tree", "bitree") for x in names):
        return "fenwick_tree"
    if any("seg" in x for x in names) or ("tree" in names and recursive_functions(t)):
        return "segment_tree"
    rec = recursive_functions(t)
    if rec and ("FloorDiv" in ops or "RShift" in ops) and _counts_in_recursion(t, rec):
        return "merge_sort_count"
    if any(isinstance(n, ast.While) for n in ast.walk(t)) and ("merge" in " ".join(names)) and \
            ("FloorDiv" in ops or "Mult" in ops):
        return "merge_sort_count"
    return "other"


def _counts_in_recursion(t: ast.AST, rec: set[str]) -> bool:
    """A recursive function whose loop body adds a non-unit amount to a counter (inv += len(left) - i, += j, ...)."""
    for f in ast.walk(t):
        if isinstance(f, ast.FunctionDef) and f.name in rec:
            for loop in ast.walk(f):
                if isinstance(loop, (ast.While, ast.For)):
                    for n in ast.walk(loop):
                        if isinstance(n, ast.AugAssign) and isinstance(n.op, ast.Add) and \
                                not (isinstance(n.value, ast.Constant) and n.value.value == 1) and \
                                not isinstance(n.target, ast.Subscript):
                            return True
    return False
