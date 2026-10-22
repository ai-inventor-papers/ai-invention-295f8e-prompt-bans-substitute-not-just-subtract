"""II1 is_subsequence (LeetCode 392; len(t) widened to 50000 so that the LCS table exceeds the limit)."""

from __future__ import annotations

import random
import string

from unitlib import ast_tree, calls_named, ccount, has_loop, names_used, opcount, probe, recursive_functions
from units.ii_common import has_2d_table, has_midpoint

CHECKER = "bool"
ARGS = ["s", "t"]

ORACLE_A = '''
def solve(s, t):
    i = j = 0
    while i < len(s) and j < len(t):
        if s[i] == t[j]:
            i += 1
        j += 1
    return i == len(s)
'''  # dataset reference (LeetCode 392 row), adapted to solve
ORACLE_B = '''
def solve(s, t):
    pos = -1
    for c in s:
        pos = t.find(c, pos + 1)
        if pos < 0:
            return False
    return True
'''

REFERENCES = {
    "two_pointers": ORACLE_A,
    "iterator_consumption": '''
def solve(s, t):
    it = iter(t)
    return all(c in it for c in s)
''',
    "bisect_positions": '''
def solve(s, t):
    from bisect import bisect_left
    pos = {}
    for i, ch in enumerate(t):
        pos.setdefault(ch, []).append(i)
    cur = 0
    for c in s:
        lst = pos.get(c)
        if not lst:
            return False
        j = bisect_left(lst, cur)
        if j == len(lst):
            return False
        cur = lst[j] + 1
    return True
''',
}
MUTANTS = [
    '''
def solve(s, t):
    return set(s) <= set(t)
''',
    '''
def solve(s, t):
    return all(c in t for c in s)
''',
    '''
def solve(s, t):
    i = j = 0
    while i < len(s) and j < len(t):
        if s[i] == t[j]:
            i += 1
        j += 1
    return j == len(t)
''',
]
EXCLUDED = {
    "lcs_dynamic_programming": '''
def solve(s, t):
    m, n = len(s), len(t)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if s[i - 1] == t[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    return dp[m][n] == m
''',
}


def _rand_str(rng: random.Random, n: int, alpha: str = string.ascii_lowercase) -> str:
    return "".join(rng.choice(alpha) for _ in range(n))


def _sub_of(rng: random.Random, t: str, k: int) -> str:
    if not t or k == 0:
        return ""
    idx = sorted(rng.sample(range(len(t)), min(k, len(t))))
    return "".join(t[i] for i in idx)


def _break(rng: random.Random, s: str) -> str:
    if not s:
        return "a"
    i = rng.randrange(len(s))
    if rng.random() < 0.5 and len(s) >= 2:
        j = rng.randrange(len(s))
        lst = list(s)
        lst[i], lst[j] = lst[j], lst[i]
        return "".join(lst)
    return s[:i] + rng.choice(string.ascii_lowercase) + s[i + 1:]


def make_tests() -> list[dict]:
    rng = random.Random(392)
    cases = [("ex0", ["abc", "ahbgdc"]), ("ex1", ["axc", "ahbgdc"]), ("edge0", ["", ""]), ("edge1", ["", "abc"]),
             ("edge2", ["a", ""]), ("edge3", ["aaaaaa", "bbaaaa"]), ("edge4", ["b", "abc"]), ("edge5", ["abc", "abc"]),
             ("edge6", ["acb", "abc"])]
    i = 0
    while len(cases) < 9 + 60:
        n = rng.choice([1, 2, 5, 10, 30, 80, 200, 500])
        alpha = string.ascii_lowercase[:rng.choice([2, 3, 5, 26])]
        t = _rand_str(rng, n, alpha)
        s = _sub_of(rng, t, rng.randint(0, min(100, n)))
        if i % 2 == 1:
            s = _break(rng, s)[:100]
        cases.append((f"rand{i}", [s, t]))
        i += 1
    for j in range(10):
        alpha = string.ascii_lowercase[:rng.choice([3, 10, 26])]
        t = _rand_str(rng, 50000, alpha)
        idx = sorted(rng.sample(range(40000, 50000), 99)) + [49999]
        s = "".join(t[k] for k in sorted(set(idx)))[:100]
        if j % 2 == 1:
            s = s[:-1] + ("z" if t[-1] != "z" and "z" not in t[-20000:] else s[-1])
            s = s[:50] + s[51:] + s[50]
        cases.append((f"stress{j}", [s, t]))
    return [{"case_id": f"II1:{cid}", "kind": "stress" if cid.startswith("stress") else
             ("example" if cid.startswith(("ex", "edge")) else "random"), "args": a} for cid, a in cases]


def _probe() -> dict:
    rng = random.Random(7)
    t = _rand_str(rng, 800)
    idx = sorted(rng.sample(range(0, 799), 19)) + [799]
    s = "".join(t[k] for k in idx)
    return {"name": "p800", "args": [s, t], "wrap": ["str", "str"], "expected": True}


PROBES = [_probe()]


def runtime_rule(tr: dict) -> str | None:
    a = probe(tr, "p800")
    if a is None or a.get("error"):
        return None
    if ccount(a, "bisect_left", "bisect_right", "bisect", "insort", "insort_left", "insort_right") >= 1:
        return "bisect_positions"
    if ccount(a, "str.find", "str.index", "str.rfind", "str.rindex") >= 1:
        return "other"
    gi = opcount(a, "str_getitem")
    si = opcount(a, "str_iter")
    ce = opcount(a, "ceq")
    ch = opcount(a, "chash")
    if ch >= 400:
        return None          # per-letter position table: library or hand-written halving decided by the AST
    if gi >= 200:
        return "two_pointers"
    if si >= 1 and ce >= 20:
        return "iterator_consumption"
    if sum(a.get("ops", {}).values()) == 0:
        return None
    return "other"


def ast_rule(code: str) -> str | None:
    t = ast_tree(code)
    if t is None:
        return None
    calls = calls_named(t)
    names = names_used(t)
    if any(c in calls for c in ("bisect_left", "bisect_right", "bisect", "insort")) or "bisect" in names:
        return "bisect_positions"
    if has_midpoint(t) and any(c in calls for c in ("setdefault", "defaultdict", "append")):
        return "bisect_positions"
    if any(c in calls for c in ("find", "index", "rfind", "rindex")):
        return "other"
    if "iter" in calls or "next" in calls:
        return "iterator_consumption"
    if has_2d_table(t):
        return "other"
    if has_loop(t) or recursive_functions(t):
        return "two_pointers"
    return "other"
