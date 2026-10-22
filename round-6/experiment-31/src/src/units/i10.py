"""I10 best single trade (LeetCode 121; n <= 100000 so the pair scan exceeds the limit)."""

from __future__ import annotations

import ast
import random

from unitlib6 import ast_tree, binop, call, calls_named, lst, op, probe

CHECKER = "exact"
ARGS = ["prices"]

ORACLE_A = '''
def solve(prices):
    ans, mi = 0, float("inf")
    for v in prices:
        ans = max(ans, v - mi)
        mi = min(mi, v)
    return int(ans)
'''  # dataset reference (LeetCode 121 row; inf -> float('inf'), int() for the empty-profit case)
ORACLE_B = '''
def solve(prices):
    best = 0
    hi = -1
    for p in reversed(prices):
        hi = max(hi, p)
        best = max(best, hi - p)
    return best
'''

REFERENCES = {
    "running_min": '''
def solve(prices):
    low = prices[0]
    best = 0
    for p in prices:
        if p < low:
            low = p
        elif p - low > best:
            best = p - low
    return best
''',
    "max_subarray_diffs": '''
def solve(prices):
    cur = best = 0
    for i in range(1, len(prices)):
        cur = max(0, cur + prices[i] - prices[i - 1])
        best = max(best, cur)
    return best
''',
    "suffix_max": '''
def solve(prices):
    top = 0
    best = 0
    for i in range(len(prices) - 1, -1, -1):
        if prices[i] > top:
            top = prices[i]
        if top - prices[i] > best:
            best = top - prices[i]
    return best
''',
    "state_dp": '''
def solve(prices):
    hold = -prices[0]
    sold = 0
    for p in prices[1:]:
        sold = max(sold, hold + p)
        hold = max(hold, -p)
    return sold
''',
}
MUTANTS = [
    '''
def solve(prices):
    return max(prices) - min(prices)
''',
    '''
def solve(prices):
    low = prices[0]
    best = 0
    for p in prices:
        low = min(low, p)
        best = max(best, low - p)
    return best
''',
    '''
def solve(prices):
    return max(0, prices[-1] - prices[0])
''',
]
EXCLUDED = {
    "pair_scan": '''
def solve(prices):
    best = 0
    n = len(prices)
    for i in range(n):
        for j in range(i + 1, n):
            if prices[j] - prices[i] > best:
                best = prices[j] - prices[i]
    return best
''',
}


def make_tests() -> list[dict]:
    rng = random.Random(121)
    cases = [("ex0", [[7, 1, 5, 3, 6, 4]]), ("ex1", [[7, 6, 4, 3, 1]]), ("edge_one", [[5]]), ("edge_two", [[1, 2]]),
             ("edge_flat", [[3, 3, 3]]), ("edge_zero", [[0, 10000]]), ("edge_dip", [[2, 4, 1, 3]])]
    sizes = [1, 2, 3, 5, 8, 13, 20, 50, 100, 300, 1000, 5000]
    for i in range(46):
        n = sizes[i % len(sizes)]
        kind = i % 3
        if kind == 0:
            a = [rng.randint(0, 10000) for _ in range(n)]
        elif kind == 1:
            a = sorted((rng.randint(0, 10000) for _ in range(n)), reverse=True)
        else:
            x = rng.randint(0, 10000)
            a = []
            for _ in range(n):
                x = max(0, min(10000, x + rng.randint(-50, 50)))
                a.append(x)
        cases.append((f"rand{i}", [a]))
    for j in range(6):
        n = 100000
        if j % 2 == 0:
            a = sorted((rng.randint(0, 10000) for _ in range(n)), reverse=True)
        else:
            a = [rng.randint(0, 10000) for _ in range(n)]
        cases.append((f"stress{j}", [a]))
    return [{"case_id": f"I10:{cid}", "kind": "stress" if cid.startswith("stress") else
             ("example" if cid.startswith("ex") else "random"), "args": a} for cid, a in cases]


def _probe(n: int, seed: int, name: str) -> dict:
    rng = random.Random(seed)
    a = [rng.randint(0, 1000) for _ in range(n)]
    best = 0
    lo = a[0]
    for p in a:
        lo = min(lo, p)
        best = max(best, p - lo)
    return {"name": name, "args": [a], "wrap": ["list"], "expected": best, "checker": "exact"}


PROBES = [_probe(200, 17, "p200"), _probe(400, 18, "p400")]


def runtime_rule(tr: dict) -> str | None:
    a = probe(tr, "p200")
    if a is None:
        return None
    n = 200
    if op(a, "JUMP_BACKWARD") >= n * n // 8:
        return "other"
    idx0 = a.get("idx") or []
    idx = [x for i, x in enumerate(idx0) if i == 0 or x != idx0[i - 1]]
    desc = len(idx) >= 6 and sum(1 for x, y in zip(idx, idx[1:]) if y < x) >= 0.7 * (len(idx) - 1)
    if lst(a, "rev") >= 1 or call(a, "reversed") >= 1 or desc or lst(a, "desc_run_max") >= n // 4:
        return "suffix_max"
    if op(a, "UNARY_NEGATIVE") >= n // 2:
        return "state_dp"
    if call(a, "min") >= n // 2:
        return "running_min"
    if binop(a, "-") >= int(0.8 * n) and binop(a, "+") >= int(0.8 * n):
        return "max_subarray_diffs"
    if binop(a, "-") >= int(0.4 * n) or op(a, "COMPARE_OP") >= n:
        return "running_min"
    return "other"


def ast_rule(code: str) -> str | None:
    t = ast_tree(code)
    if t is None:
        return None
    for f in ast.walk(t):   # revision round: a solve that takes no argument cannot be used at all
        if isinstance(f, ast.FunctionDef) and f.name == "solve" and not f.args.args and not f.args.vararg:
            return "invalid"
    calls = calls_named(t)
    loops = [n for n in ast.walk(t) if isinstance(n, (ast.For, ast.While))]
    nested = any(isinstance(m, (ast.For, ast.While)) for L in loops for m in ast.walk(L) if m is not L)
    if nested:
        return "other"
    rev = "reversed" in calls or any(
        isinstance(n, ast.Slice) and n.step is not None and isinstance(n.step, ast.UnaryOp) for n in ast.walk(t))
    for n in ast.walk(t):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "range" and len(n.args) == 3:
            st = n.args[2]
            if isinstance(st, ast.UnaryOp) and isinstance(st.op, ast.USub):
                rev = True
            if isinstance(st, ast.Constant) and isinstance(st.value, int) and st.value < 0:
                rev = True
    if rev:
        return "suffix_max"
    negs = any(isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.USub) and not isinstance(n.operand, ast.Constant)
               for n in ast.walk(t))
    if negs:
        return "state_dp"
    for n in ast.walk(t):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "max" and len(n.args) == 2:
            if any(isinstance(x, ast.Constant) and x.value == 0 for x in n.args) and any(
                    isinstance(x, ast.BinOp) and isinstance(x.op, ast.Add) for x in ast.walk(n)):
                return "max_subarray_diffs"
    if any(isinstance(n, ast.AugAssign) and isinstance(n.op, ast.Add) for n in ast.walk(t)) and any(
            isinstance(n, ast.Subscript) and isinstance(n.slice, ast.BinOp) and isinstance(n.slice.op, ast.Sub)
            for n in ast.walk(t)):
        return "max_subarray_diffs"
    if loops or any(isinstance(n, ast.comprehension) for n in ast.walk(t)):
        return "running_min"
    return "other"   # revision round: no scan over the days (e.g. max(prices) - min(prices))
