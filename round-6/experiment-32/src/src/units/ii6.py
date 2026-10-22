"""II6 bracket_matching (LeetCode 20; len(s) <= 4000, nesting depth <= 400 so the recursive reference runs without
changing the recursion limit; repeated pair removal stays under 0.25 x the limit)."""

from __future__ import annotations

import random

from unitlib import ast_tree, calls_named, ccount, names_used, probe, recursive_functions

CHECKER = "bool"
ARGS = ["s"]

ORACLE_A = '''
def solve(s):
    stk = []
    d = {"()", "[]", "{}"}
    for c in s:
        if c in "({[":
            stk.append(c)
        elif not stk or stk.pop() + c not in d:
            return False
    return not stk
'''  # dataset reference (LeetCode 20 row), adapted
ORACLE_B = '''
def solve(s):
    prev = None
    while prev != s:
        prev = s
        s = s.replace("()", "").replace("[]", "").replace("{}", "")
    return s == ""
'''

REFERENCES = {
    "stack": ORACLE_A,
    "replace_pairs": ORACLE_B,
    "recursive_descent": '''
def solve(s):
    pairs = {"(": ")", "[": "]", "{": "}"}
    n = len(s)

    def seq(i):
        while i < n and s[i] in pairs:
            j = seq(i + 1)
            if j < 0 or j >= n or s[j] != pairs[s[i]]:
                return -1
            i = j + 1
        return i

    return seq(0) == n
''',
}
MUTANTS = [
    '''
def solve(s):
    return s.count("(") == s.count(")") and s.count("[") == s.count("]") and s.count("{") == s.count("}")
''',
    '''
def solve(s):
    stk = []
    d = {"()", "[]", "{}"}
    for c in s:
        if c in "({[":
            stk.append(c)
        elif not stk or stk.pop() + c not in d:
            return False
    return True
''',
    '''
def solve(s):
    return len(s) % 2 == 0
''',
]
EXCLUDED: dict[str, str] = {}
OPEN, CLOSE = "([{", ")]}"


def _valid(rng: random.Random, n_pairs: int, max_depth: int) -> str:
    out, st = [], []
    left = n_pairs
    while left or st:
        if left and len(st) < max_depth and (not st or rng.random() < 0.55):
            k = rng.randrange(3)
            out.append(OPEN[k])
            st.append(k)
            left -= 1
        else:
            out.append(CLOSE[st.pop()])
    return "".join(out)


def _deep(depth: int, reps: int) -> str:
    unit = "".join(OPEN[i % 3] for i in range(depth)) + "".join(CLOSE[i % 3] for i in reversed(range(depth)))
    return unit * reps


def _break(rng: random.Random, s: str) -> str:
    lst = list(s)
    r = rng.random()
    i = rng.randrange(len(lst))
    if r < 0.4:
        c = lst[i]
        pool = OPEN if c in OPEN else CLOSE
        lst[i] = rng.choice([x for x in pool if x != c])
    elif r < 0.7 and len(lst) > 1:
        del lst[i]
    else:
        j = rng.randrange(len(lst))
        lst[i], lst[j] = lst[j], lst[i]
    out = "".join(lst)
    return out or ")"


def make_tests() -> list[dict]:
    rng = random.Random(20)
    cases = [("ex0", ["()[]{}"]), ("ex1", ["(]"]), ("ex2", ["([{}])"]), ("ex3", ["()"]), ("edge0", ["("]),
             ("edge1", [")"]), ("edge2", ["([)]"]), ("edge3", ["]["]), ("edge4", ["{[]}"]), ("edge5", ["(("])]
    i = 0
    while len(cases) < 10 + 60:
        n = rng.choice([1, 2, 3, 5, 10, 40, 200])
        s = _valid(rng, n, rng.choice([1, 3, 10, 400]))
        if i % 2 == 1:
            s = _break(rng, s)
        cases.append((f"rand{i}", [s]))
        i += 1
    stress = [_deep(400, 5), _valid(rng, 2000, 400), _valid(rng, 2000, 3), _deep(400, 4) + "(" * 400 + ")" * 400]
    stress += [_break(rng, x) for x in stress]
    stress += [_deep(400, 5)[:-1] + "(", "()" * 2000]
    for j, s in enumerate(stress):
        cases.append((f"stress{j}", [s[:4000]]))
    return [{"case_id": f"II6:{cid}", "kind": "stress" if cid.startswith("stress") else
             ("example" if cid.startswith(("ex", "edge")) else "random"), "args": a} for cid, a in cases]


PROBES = [{"name": "p400", "args": [_deep(30, 3) + _valid(random.Random(3), 110, 20)], "wrap": ["str"],
           "expected": True}]


def runtime_rule(tr: dict) -> str | None:
    a = probe(tr, "p400")
    if a is None or a.get("error"):
        return None
    if ccount(a, "str.replace") >= 3:
        return "replace_pairs"
    if int(a.get("max_depth") or 0) >= 15:
        return "recursive_descent"
    # revision round (gate ii): the tracer's patched deque reports '_patch.<locals>.deque.append', so container
    # pushes/pops are matched on the method name (list or deque)
    ap = ccount(a, "append", "pop", "appendleft", "popleft")
    if ap >= 100:
        return "stack"
    if sum(a.get("ops", {}).values()) == 0 and not a.get("ccalls"):
        return None
    return "other"


def ast_rule(code: str) -> str | None:
    t = ast_tree(code)
    if t is None:
        return None
    calls = calls_named(t)
    names = names_used(t)
    if "replace" in calls:
        return "replace_pairs"
    if recursive_functions(t):
        return "recursive_descent"
    if any(c in calls for c in ("append", "pop")) or "deque" in names:
        return "stack"
    return "other"
