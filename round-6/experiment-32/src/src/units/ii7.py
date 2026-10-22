"""II7 combine_in_place (LeetCode 88 'merge sorted array'; in-place contract: nums1 is mutated and None returned;
checker 'inplace0' compares the mutated first argument). m, n <= 50000."""

from __future__ import annotations

import random
import re

from unitlib import ast_tree, calls_named, ccount, names_used, opcount, pcount, probe

CHECKER = "inplace0"
ARGS = ["nums1", "m", "nums2", "n"]

ORACLE_A = '''
def solve(nums1, m, nums2, n):
    k = m + n - 1
    i, j = m - 1, n - 1
    while j >= 0:
        if i >= 0 and nums1[i] > nums2[j]:
            nums1[k] = nums1[i]
            i -= 1
        else:
            nums1[k] = nums2[j]
            j -= 1
        k -= 1
'''  # dataset reference (LeetCode 88 row), adapted
ORACLE_B = '''
def solve(nums1, m, nums2, n):
    nums1[:] = sorted(nums1[:m] + nums2[:n])
'''

REFERENCES = {
    "backward_fill": ORACLE_A,
    "concat_sort": '''
def solve(nums1, m, nums2, n):
    nums1[m:] = nums2[:n]
    nums1.sort()
''',
    "heapq_merge": '''
def solve(nums1, m, nums2, n):
    import heapq
    nums1[:] = list(heapq.merge(nums1[:m], nums2[:n]))
''',
    "forward_copy": '''
def solve(nums1, m, nums2, n):
    out = []
    i = j = 0
    while i < m and j < n:
        if nums1[i] <= nums2[j]:
            out.append(nums1[i])
            i += 1
        else:
            out.append(nums2[j])
            j += 1
    out.extend(nums1[i:m])
    out.extend(nums2[j:n])
    nums1[:] = out
''',
}
MUTANTS = [
    '''
def solve(nums1, m, nums2, n):
    nums1[m:] = nums2[:n]
''',
    '''
def solve(nums1, m, nums2, n):
    k = m + n - 1
    i, j = m - 1, n - 1
    while i >= 0 and j >= 0:
        if nums1[i] > nums2[j]:
            nums1[k] = nums1[i]
            i -= 1
        else:
            nums1[k] = nums2[j]
            j -= 1
        k -= 1
''',
    '''
def solve(nums1, m, nums2, n):
    return sorted(nums1[:m] + nums2)
''',
]
EXCLUDED: dict[str, str] = {
    "insertion_shift": '''
def solve(nums1, m, nums2, n):
    for v in nums2[:n]:
        i = m
        while i > 0 and nums1[i - 1] > v:
            nums1[i] = nums1[i - 1]
            i -= 1
        nums1[i] = v
        m += 1
''',
}
LIM = 10 ** 9


def _case(rng: random.Random, m: int, n: int, span: int) -> list:
    a = sorted(rng.randint(-span, span) for _ in range(m))
    b = sorted(rng.randint(-span, span) for _ in range(n))
    return [a + [0] * n, m, b, n]


def make_tests() -> list[dict]:
    rng = random.Random(88)
    cases = [("ex0", [[1, 2, 3, 0, 0, 0], 3, [2, 5, 6], 3]), ("ex1", [[1], 1, [], 0]), ("ex2", [[0], 0, [1], 1]),
             ("edge0", [[4, 5, 6, 0, 0, 0], 3, [1, 2, 3], 3]), ("edge1", [[-LIM, LIM, 0], 2, [0], 1]),
             ("edge2", [[2, 2, 0, 0], 2, [2, 2], 2])]
    i = 0
    while len(cases) < 6 + 55:
        m, n = rng.randint(0, 200), rng.randint(0, 200)
        if m + n == 0:
            continue
        cases.append((f"rand{i}", _case(rng, m, n, rng.choice([3, 100, LIM]))))
        i += 1
    for j in range(8):
        m, n = [(50000, 50000), (50000, 1), (1, 50000), (30000, 50000), (50000, 50000), (0, 50000), (50000, 0),
                (40000, 40000)][j]
        cases.append((f"stress{j}", _case(rng, m, n, [LIM, 10, LIM, 1000, 3, LIM, LIM, LIM][j])))
    return [{"case_id": f"II7:{cid}", "kind": "stress" if cid.startswith("stress") else
             ("example" if cid.startswith(("ex", "edge")) else "random"), "args": a} for cid, a in cases]


def _probe() -> dict:
    rng = random.Random(9)
    a = sorted(rng.sample(range(0, 100000), 300))
    b = sorted(rng.sample(range(0, 100000), 300))
    return {"name": "p600", "args": [a + [0] * 300, 300, b, 300], "wrap": ["ints", "plain", "ints", "plain"],
            "expected": None}


PROBES = [_probe()]


WANTS_CODE = True


def runtime_rule(tr: dict) -> str | None:
    """Revision round (gate ii): heap insertion and insert-at-front shifting are 'other'; a backward fill needs a hot
    (>= 50 executions) source line that decrements an index while values are compared."""
    a = probe(tr, "p600")
    if a is None or a.get("error"):
        return None
    if pcount(a, "heapq.merge") >= 1:
        return "heapq_merge"
    if ccount(a, "list.sort", "sorted") >= 1:
        return "concat_sort"
    if ccount(a, "heappush", "heapify", "heappop", "heapreplace", "heappushpop", "insert") >= 1:
        return "other"
    src = (tr.get("_code") or "").splitlines()
    hot = [src[int(k) - 1] for k, v in (a.get("line_counts") or {}).items() if v >= 50 and 0 < int(k) <= len(src)]
    cmp_ = opcount(a, "cmp")
    app = ccount(a, "append")
    if cmp_ >= 300 and app >= 300:
        return "forward_copy"
    if cmp_ >= 300 and any(re.search(r"-=\s*1|-\s*1\s*\]", l) for l in hot):
        return "backward_fill"
    if sum(a.get("ops", {}).values()) == 0 and not a.get("ccalls"):
        return None
    return "other"


def ast_rule(code: str) -> str | None:
    t = ast_tree(code)
    if t is None:
        return None
    import ast as _a
    for nd in _a.walk(t):            # revision round: calls inside assert statements are input checks, not mechanism
        if hasattr(nd, "body") and isinstance(nd.body, list):
            nd.body = [b for b in nd.body if not isinstance(b, _a.Assert)] or [_a.Pass()]
    calls = calls_named(t)
    if any(c in calls for c in ("heappush", "heapify", "insert")):
        return "other"
    names = names_used(t)
    if "merge" in calls and ("heapq" in names or "merge" in names):
        return "heapq_merge"
    if "sort" in calls or "sorted" in calls:
        return "concat_sort"
    if "append" in calls or "extend" in calls:
        return "forward_copy"
    import ast as _ast
    for nd in _ast.walk(t):
        if isinstance(nd, _ast.AugAssign) and isinstance(nd.op, _ast.Sub):
            return "backward_fill"
    return "other"
