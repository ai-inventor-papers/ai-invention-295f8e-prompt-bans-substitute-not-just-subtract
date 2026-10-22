"""I3 happy number (LeetCode 202). Runtime signal: the number of digit-square evaluations on unhappy probes
(known loop ~1, seen record ~9 plus insertions, Floyd ~3 per round, iteration cap = the cap)."""

from __future__ import annotations

import ast
import random

from unitlib6 import ast_tree, binop, call, calls_named, maxint, op, probe

CHECKER = "bool"
ARGS = ["n"]

ORACLE_A = '''
def solve(n):
    vis = set()
    while n != 1 and n not in vis:
        vis.add(n)
        x = 0
        while n:
            n, v = divmod(n, 10)
            x += v * v
        n = x
    return n == 1
'''  # dataset reference (LeetCode 202 row)
ORACLE_B = '''
def solve(n):
    while n != 1 and n != 4:
        n = sum(int(c) ** 2 for c in str(n))
    return n == 1
'''

REFERENCES = {
    "seen_set": '''
def solve(n):
    seen = set()
    while n != 1:
        if n in seen:
            return False
        seen.add(n)
        n = sum(int(d) ** 2 for d in str(n))
    return True
''',
    "floyd": '''
def solve(n):
    def step(x):
        s = 0
        while x:
            x, d = divmod(x, 10)
            s += d * d
        return s
    slow, fast = n, step(n)
    while fast != 1 and slow != fast:
        slow = step(slow)
        fast = step(step(fast))
    return fast == 1
''',
    "known_loop": '''
def solve(n):
    loop = {4, 16, 37, 58, 89, 145, 42, 20}
    while n != 1 and n not in loop:
        s = 0
        while n:
            n, d = divmod(n, 10)
            s += d * d
        n = s
    return n == 1
''',
    "step_cap": '''
def solve(n):
    for _ in range(1000):
        if n == 1:
            return True
        s = 0
        while n:
            n, d = divmod(n, 10)
            s += d * d
        n = s
    return n == 1
''',
}
MUTANTS = [
    '''
def solve(n):
    return n == 1
''',
    '''
def solve(n):
    for _ in range(2):
        n = sum(int(c) ** 2 for c in str(n))
    return n == 1
''',
    '''
def solve(n):
    seen = set()
    while n not in seen:
        seen.add(n)
        n = sum(int(c) for c in str(n))
    return n == 1
''',
]
EXCLUDED: dict[str, str] = {}


def _happy(n: int) -> bool:
    seen = set()
    while n != 1 and n not in seen:
        seen.add(n)
        n = sum(int(c) ** 2 for c in str(n))
    return n == 1


def make_tests() -> list[dict]:
    rng = random.Random(202)
    cases = [("ex0", [19]), ("ex1", [2]), ("edge1", [1]), ("edge7", [7]), ("edge4", [4]), ("edge_max", [2 ** 31 - 1]),
             ("edge_10", [10]), ("edge_100", [100])]
    vals = set()
    while len(vals) < 50:
        k = rng.choice([2, 3, 4, 6, 9, 10])
        vals.add(rng.randint(1, min(2 ** 31 - 1, 10 ** k)))
    for i, v in enumerate(sorted(vals)):
        cases.append((f"rand{i}", [v]))
    happy = [v for v in range(1, 3000) if _happy(v)]
    for j, v in enumerate(rng.sample(happy, 6)):
        cases.append((f"happy{j}", [v]))
    for j in range(6):
        cases.append((f"stress{j}", [rng.randint(10 ** 9, 2 ** 31 - 1)]))
    return [{"case_id": f"I3:{cid}", "kind": "stress" if cid.startswith("stress") else
             ("example" if cid.startswith("ex") else "random"), "args": a} for cid, a in cases]


PROBES = [{"name": "p2", "args": [2], "wrap": ["none"], "expected": False, "checker": "bool"},
          {"name": "p4", "args": [4], "wrap": ["none"], "expected": False, "checker": "bool"},
          {"name": "p7", "args": [7], "wrap": ["none"], "expected": True, "checker": "bool"}]


def runtime_rule(tr: dict) -> str | None:
    a = probe(tr, "p2")
    if a is None:
        return None
    sq = binop(a, "*", "**") + call(a, "pow")
    remember = call(a, "add", "append", "setdefault", "insert") + op(a, "STORE_SUBSCR")
    if sq <= 6:
        return "known_loop"
    if remember >= 4:
        return "seen_set"
    if maxint(a, "range") >= 20 or sq >= 90:
        return "step_cap"
    if sq >= 20:
        return "floyd"
    return "other"


def ast_rule(code: str) -> str | None:
    t = ast_tree(code)
    if t is None:
        return None
    names = {n.id.lower() for n in ast.walk(t) if isinstance(n, ast.Name)}
    if any(k in nm for nm in names for k in ("slow", "fast", "tortoise", "hare")):
        return "floyd"
    loop_members = {4, 16, 37, 58, 89, 145, 42, 20}
    for n in ast.walk(t):
        if isinstance(n, ast.Compare):
            consts = [c.value for c in ast.walk(n) if isinstance(c, ast.Constant) and isinstance(c.value, int)]
            if any(c in loop_members for c in consts):
                return "known_loop"
            if any(isinstance(op_, (ast.Lt, ast.LtE)) for op_ in n.ops) and any(
                    isinstance(c, int) and 5 <= c <= 10 for c in consts):
                return "known_loop"
        if isinstance(n, (ast.Set, ast.List, ast.Tuple)):
            vals = {e.value for e in n.elts if isinstance(e, ast.Constant) and isinstance(e.value, int)}
            if len(vals & loop_members) >= 3:
                return "known_loop"
    calls = calls_named(t)
    if any(c in calls for c in ("add", "append", "setdefault")) or "set" in calls or any(
            isinstance(n, (ast.Set, ast.Dict)) for n in ast.walk(t)):
        return "seen_set"
    for n in ast.walk(t):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "range" and n.args:
            c = n.args[-1] if len(n.args) == 1 else n.args[1]
            if isinstance(c, ast.Constant) and isinstance(c.value, int) and c.value >= 20:
                return "step_cap"
    return "other"
