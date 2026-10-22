"""I7 one counts 0..n (LeetCode 338 counting bits; n <= 50000)."""

from __future__ import annotations

import ast
import random

from unitlib6 import ast_tree, binop, call, calls_named, op, probe

CHECKER = "exact"
ARGS = ["n"]

ORACLE_A = '''
def solve(n):
    return [i.bit_count() for i in range(n + 1)]
'''  # dataset reference (LeetCode 338 row)
ORACLE_B = '''
def solve(n):
    out = []
    for i in range(n + 1):
        c = 0
        x = i
        while x:
            c += x % 2
            x //= 2
        out.append(c)
    return out
'''

REFERENCES = {
    "builtin_count": '''
def solve(n):
    return [bin(i).count("1") for i in range(n + 1)]
''',
    "dp_half": '''
def solve(n):
    ans = [0] * (n + 1)
    for i in range(1, n + 1):
        ans[i] = ans[i >> 1] + (i & 1)
    return ans
''',
    "dp_lowest_one": '''
def solve(n):
    ans = [0] * (n + 1)
    for i in range(1, n + 1):
        ans[i] = ans[i & (i - 1)] + 1
    return ans
''',
    "dp_offset": '''
def solve(n):
    ans = [0] * (n + 1)
    p = 1
    for i in range(1, n + 1):
        if p * 2 == i:
            p = i
        ans[i] = ans[i - p] + 1
    return ans
''',
    "per_number_loop": '''
def solve(n):
    ans = []
    for i in range(n + 1):
        c = 0
        x = i
        while x:
            x &= x - 1
            c += 1
        ans.append(c)
    return ans
''',
}
MUTANTS = [
    '''
def solve(n):
    return [bin(i).count("1") for i in range(n)]
''',
    '''
def solve(n):
    ans = [0] * (n + 1)
    for i in range(1, n + 1):
        ans[i] = ans[i >> 1] + 1
    return ans
''',
    '''
def solve(n):
    return [i % 2 for i in range(n + 1)]
''',
]
EXCLUDED: dict[str, str] = {}


def make_tests() -> list[dict]:
    rng = random.Random(338)
    cases = [("ex0", [2]), ("ex1", [5]), ("edge0", [0]), ("edge1", [1]), ("edge_pow", [64]), ("edge_pow1", [1023])]
    vals = sorted(set(rng.randint(2, 5000) for _ in range(48)))
    for i, v in enumerate(vals):
        cases.append((f"rand{i}", [v]))
    for j, v in enumerate([50000, 49999, 32768, 40000, 50000, 45678]):
        cases.append((f"stress{j}", [v]))
    return [{"case_id": f"I7:{cid}", "kind": "stress" if cid.startswith("stress") else
             ("example" if cid.startswith("ex") else "random"), "args": a} for cid, a in cases]


PROBES = [{"name": "p300", "args": [300], "wrap": ["none"], "expected": [bin(i).count("1") for i in range(301)],
           "checker": "exact"},
          {"name": "p600", "args": [600], "wrap": ["none"], "expected": [bin(i).count("1") for i in range(601)],
           "checker": "exact"}]


def runtime_rule(tr: dict) -> str | None:
    a = probe(tr, "p300")
    if a is None:
        return None
    n = 300
    if call(a, "bin", "bit_count", "format", "count") >= n // 2:
        return "builtin_count"
    iters = op(a, "JUMP_BACKWARD")
    if iters >= int(2.5 * n):
        return "per_number_loop"
    if binop(a, ">>") >= int(0.8 * n) or binop(a, "//") >= int(0.8 * n):
        return "dp_half"
    if binop(a, "&") >= int(0.8 * n) and binop(a, "-") >= int(0.8 * n):
        return "dp_lowest_one"
    if binop(a, "-") >= int(0.8 * n):
        return "dp_offset"
    return "other"


def _sub_index_ops(t: ast.AST) -> set[str]:
    out = set()
    for n in ast.walk(t):
        if isinstance(n, ast.Subscript):
            for m in ast.walk(n.slice):
                if isinstance(m, ast.BinOp):
                    out.add(type(m.op).__name__)
    return out


def ast_rule(code: str) -> str | None:
    t = ast_tree(code)
    if t is None:
        return None
    calls = calls_named(t)
    if any(c in calls for c in ("bin", "bit_count", "format")) or ("count" in calls and "str" in calls):
        return "builtin_count"
    loops = [n for n in ast.walk(t) if isinstance(n, (ast.For, ast.While))]
    nested = any(isinstance(m, (ast.While, ast.For)) for L in loops for m in ast.walk(L) if m is not L)
    if nested:
        return "per_number_loop"
    so = _sub_index_ops(t)
    if "RShift" in so or "FloorDiv" in so:
        return "dp_half"
    if "BitAnd" in so:
        return "dp_lowest_one"
    if "Sub" in so:
        return "dp_offset"
    return "other"
