"""B4 integer_sqrt (LeetCode 69; the LeetCode no-exponent rule is NOT part of the spec, so library and float modes
are valid). Runtime signature: iteration trajectories on probe x in {15, 10**6, 2**30}."""

from __future__ import annotations

import ast
import random

from unitlib import ast_tree, binops, calls_named, ccount, opcount, probe

CHECKER = "exact"
ARGS = ["x"]

ORACLE_A = '''
def solve(x):
    l, r = 0, x
    while l < r:
        mid = (l + r + 1) >> 1
        if mid > x // mid:
            r = mid - 1
        else:
            l = mid
    return l
'''  # dataset reference (LeetCode 69 row), adapted
ORACLE_B = '''
def solve(x):
    import math
    return math.isqrt(x)
'''

REFERENCES = {
    "binary_search": '''
def solve(x):
    lo, hi = 0, x
    while lo <= hi:
        mid = (lo + hi) // 2
        if mid * mid <= x:
            lo = mid + 1
        else:
            hi = mid - 1
    return hi
''',
    "newton": '''
def solve(x):
    if x < 2:
        return x
    r = x
    while r * r > x:
        r = (r + x // r) // 2
    return r
''',
    "bit_by_bit": '''
def solve(x):
    res = 0
    for b in range(16, -1, -1):
        cand = res | (1 << b)
        if cand * cand <= x:
            res = cand
    return res
''',
    "library_isqrt": '''
import math

def solve(x):
    return math.isqrt(x)
''',
    "float_sqrt": '''
import math

def solve(x):
    r = int(math.sqrt(x))
    while r * r > x:
        r -= 1
    while (r + 1) * (r + 1) <= x:
        r += 1
    return r
''',
    "linear_scan": '''
def solve(x):
    r = 0
    while (r + 1) * (r + 1) <= x:
        r += 1
    return r
''',
}
MUTANTS = [
    '''
def solve(x):
    return int(x ** 0.5 + 0.5)
''',
    '''
def solve(x):
    lo, hi = 0, x
    while lo <= hi:
        mid = (lo + hi) // 2
        if mid * mid <= x:
            lo = mid + 1
        else:
            hi = mid - 1
    return lo
''',
    '''
def solve(x):
    r = x
    while r * r > x:
        r = (r + x // r) // 2
    return r + (1 if x == 0 else 0) - (1 if x == 1 else 0)
''',
]
EXCLUDED: dict[str, str] = {}


def make_tests() -> list[dict]:
    rng = random.Random(69)
    xs = [("ex0", 4), ("ex1", 8), ("ex2", 0), ("ex3", 16), ("edge1", 1), ("edge2", 2), ("edge3", 3)]
    i = 0
    for v in range(5, 21):
        xs.append((f"small{v}", v))
    while len(xs) < 7 + 16 + 30:
        k = rng.randint(2, 46340)
        xs.append((f"rand{i}", rng.choice([k * k - 1, k * k, k * k + 1, rng.randint(0, 2 ** 31 - 1)])))
        i += 1
    top = [2 ** 31 - 1, 2 ** 31 - 2, 46340 ** 2, 46340 ** 2 - 1, 46341 ** 2 - 1, 2 ** 30, 2 ** 30 - 1, 2 ** 31 - 3,
           2147395599, 2147395600]
    for j, v in enumerate(top):
        xs.append((f"stress{j}", v))
    return [{"case_id": f"B4:{cid}", "kind": "stress" if cid.startswith("stress") else
             ("example" if cid.startswith(("ex", "edge")) else "random"), "args": [v]} for cid, v in xs]


PROBES = [{"name": "x15", "args": [15], "wrap": ["int"], "expected": 3},
          {"name": "x1e6", "args": [10 ** 6], "wrap": ["int"], "expected": 1000},
          {"name": "x2p30", "args": [1234567890], "wrap": ["int"], "expected": 35136}]  # name kept; non-square


def _traj_vals(p: dict) -> list[float]:
    tr = p.get("traj", [])
    by: dict[str, list[float]] = {}
    for op, v in tr:
        by.setdefault(op, []).append(v)
    if not by:
        return []
    vals = max(by.values(), key=len)
    return [v for v in vals if v > 16]   # drop guard comparisons against small constants (x < 2, x <= 1, ...)


def _decreasing_frac(vals: list[float]) -> float:
    if len(vals) < 3:
        return 0.0
    dec = sum(1 for a, b in zip(vals, vals[1:]) if b < a)
    return dec / (len(vals) - 1)


def runtime_rule(tr: dict) -> str | None:
    a, b, c = probe(tr, "x15"), probe(tr, "x1e6"), probe(tr, "x2p30")
    if a is None or b is None or c is None or a.get("error") or b.get("error") or c.get("error"):
        return None
    if ccount(c, "isqrt") >= 1:
        return "library_isqrt"
    if ccount(c, "sqrt") >= 1 or opcount(c, "pow_half") >= 1:
        return "float_sqrt"
    if b["lines"] >= 1500 or len(_traj_vals(b)) >= 400:
        return "linear_scan"
    vals = _traj_vals(c)
    ops = sum(c.get("ops", {}).values())
    if ops == 0 and c["lines"] <= 3:
        return None
    if _decreasing_frac(vals) >= 0.95 and len(vals) >= 4:
        return "newton"
    la, lc = max(a["lines"], 1), c["lines"]
    if lc >= 16 and 0.5 <= lc / la <= 2.0:
        return "bit_by_bit"
    if len(vals) >= 5:
        return "binary_search"
    return "other"


def _is_mid(n: ast.AST) -> bool:
    """(lo + hi) // 2, (lo + hi) >> 1, lo + (hi - lo) // 2 and the like: a halving of a sum/difference of names."""
    if not (isinstance(n, ast.BinOp) and isinstance(n.op, (ast.FloorDiv, ast.RShift, ast.Div))):
        return False
    if not (isinstance(n.right, ast.Constant) and n.right.value in (1, 2)):
        return False
    left = n.left
    return isinstance(left, ast.BinOp) and isinstance(left.op, (ast.Add, ast.Sub)) and \
        any(isinstance(x, ast.Name) for x in (left.left, left.right))


def _is_newton(n: ast.AST) -> bool:
    if not (isinstance(n, ast.BinOp) and isinstance(n.op, (ast.FloorDiv, ast.Div, ast.RShift, ast.Mult))):
        return False
    s = n.left if isinstance(n.left, ast.BinOp) else None
    if s is None or not isinstance(s.op, ast.Add):
        return False
    for x, y in ((s.left, s.right), (s.right, s.left)):
        if isinstance(x, ast.Name) and isinstance(y, ast.BinOp) and isinstance(y.op, (ast.FloorDiv, ast.Div)) \
                and isinstance(y.right, ast.Name) and y.right.id == x.id:
            return True
    return False


def ast_rule(code: str) -> str | None:
    t = ast_tree(code)
    if t is None:
        return None
    calls = calls_named(t)
    user_defs = {f.name for f in ast.walk(t) if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef))}
    if "isqrt" in calls and "isqrt" not in user_defs:
        return "library_isqrt"
    pow_half = any(isinstance(n, ast.BinOp) and isinstance(n.op, ast.Pow) and isinstance(n.right, ast.Constant)
                   and n.right.value == 0.5 for n in ast.walk(t))
    if ("sqrt" in calls and "sqrt" not in user_defs) or pow_half or ("pow" in calls and "0.5" in code):
        return "float_sqrt"
    if any(_is_newton(n) for n in ast.walk(t)):
        return "newton"
    if any(_is_mid(n) for n in ast.walk(t)) and any(isinstance(n, ast.While) for n in ast.walk(t)):
        return "binary_search"
    ops = binops(t)
    if ("LShift" in ops or "RShift" in ops) and any(isinstance(n, (ast.For, ast.While)) for n in ast.walk(t)):
        return "bit_by_bit"
    inc = any(isinstance(n, ast.AugAssign) and isinstance(n.op, (ast.Add, ast.Sub)) and
              isinstance(n.value, ast.Constant) and n.value.value == 1 for n in ast.walk(t))
    if inc and any(isinstance(n, (ast.While, ast.For)) for n in ast.walk(t)):
        return "linear_scan"
    return "other"
