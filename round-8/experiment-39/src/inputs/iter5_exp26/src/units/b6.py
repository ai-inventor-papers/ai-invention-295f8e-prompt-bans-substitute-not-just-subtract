"""B6 valid_anagram (LeetCode 242). Candidate extra mode alphabet_count_scan (str.count per letter) is labelled by
both labellers but joins the catalogue only under the plan's >= 2 occurrences rule (decided at the stage-(ii)
freeze); until then and otherwise it is mapped to 'other' at analysis time."""

from __future__ import annotations

import ast
import random
import string

from unitlib import ast_tree, calls_named, ccount, opcount, pcount, probe

CHECKER = "bool"
ARGS = ["s", "t"]
EXTRA_MODES = ["alphabet_count_scan"]

ORACLE_A = '''
def solve(s, t):
    from collections import Counter
    if len(s) != len(t):
        return False
    cnt = Counter(s)
    for c in t:
        cnt[c] -= 1
        if cnt[c] < 0:
            return False
    return True
'''  # dataset reference (LeetCode 242 row), adapted
ORACLE_B = '''
def solve(s, t):
    return sorted(s) == sorted(t)
'''

REFERENCES = {
    "sort_compare": ORACLE_B,
    "hash_count": '''
def solve(s, t):
    if len(s) != len(t):
        return False
    d = {}
    for c in s:
        d[c] = d.get(c, 0) + 1
    for c in t:
        if d.get(c, 0) == 0:
            return False
        d[c] -= 1
    return True
''',
    "fixed_count_array": '''
def solve(s, t):
    if len(s) != len(t):
        return False
    cnt = [0] * 26
    for c in s:
        cnt[ord(c) - 97] += 1
    for c in t:
        cnt[ord(c) - 97] -= 1
    return all(v == 0 for v in cnt)
''',
}
EXTRA_REFERENCES = {
    "alphabet_count_scan": '''
def solve(s, t):
    if len(s) != len(t):
        return False
    return all(s.count(c) == t.count(c) for c in "abcdefghijklmnopqrstuvwxyz")
''',
}
MUTANTS = [
    '''
def solve(s, t):
    return set(s) == set(t)
''',
    '''
def solve(s, t):
    return len(s) == len(t)
''',
    '''
def solve(s, t):
    cnt = [0] * 26
    for c in s:
        cnt[ord(c) - 97] += 1
    for c in t:
        cnt[ord(c) - 97] -= 1
    return all(v >= 0 for v in cnt)
''',
]
EXCLUDED = {
    "remove_one_by_one": '''
def solve(s, t):
    if len(s) != len(t):
        return False
    rest = list(t)
    for c in s:
        if c in rest:
            rest.remove(c)
        else:
            return False
    return not rest
''',
}


def _pair(rng: random.Random, n: int, kind: str, alpha: int = 26) -> list:
    letters = string.ascii_lowercase[:alpha]
    s = "".join(rng.choice(letters) for _ in range(n))
    t = list(s)
    rng.shuffle(t)
    t = "".join(t)
    if kind == "flip" and n >= 1:
        i = rng.randrange(n)
        t = t[:i] + rng.choice([c for c in string.ascii_lowercase if c != t[i]]) + t[i + 1:]
    elif kind == "len":
        t = t + rng.choice(letters)
    elif kind == "swapcount" and n >= 2:
        i = rng.randrange(n)
        c = t[i]
        j = next((k for k in range(n) if t[k] != c), None)
        if j is not None:
            t = t[:j] + c + t[j + 1:]
    return [s, t]


def make_tests() -> list[dict]:
    rng = random.Random(242)
    cases = [("ex0", ["anagram", "nagaram"]), ("ex1", ["rat", "car"]), ("ex2", ["listen", "silent"]),
             ("edge0", ["a", "a"]), ("edge1", ["a", "b"]), ("edge2", ["ab", "a"]), ("edge3", ["aab", "abb"])]
    kinds = ["same", "flip", "len", "swapcount"]
    sizes = [1, 2, 3, 5, 8, 13, 30, 100, 300, 1000, 3000, 10000]
    i = 0
    while len(cases) < 7 + 48:
        cases.append((f"rand{i}", _pair(rng, sizes[i % len(sizes)], kinds[i % 4], alpha=rng.choice([2, 5, 26]))))
        i += 1
    for j in range(10):
        cases.append((f"stress{j}", _pair(rng, 50000, kinds[j % 4] if j % 4 != 2 else "same",
                                          alpha=26 if j < 8 else 1)))
    # adversarial worst cases at the maximum size (letter blocks in opposite arrangement)
    cases.append(("stress10", ["a" * 25000 + "b" * 25000, "b" * 25000 + "a" * 25000]))
    cases.append(("stress11", ["a" * 25000 + "b" * 25000, "b" * 25001 + "a" * 24999]))
    return [{"case_id": f"B6:{cid}", "kind": "stress" if cid.startswith("stress") else
             ("example" if cid.startswith(("ex", "edge")) else "random"), "args": a} for cid, a in cases]


def _probe(n: int, seed: int) -> dict:
    a = _pair(random.Random(seed), n, "same")
    return {"name": f"n{n}", "args": a, "wrap": ["str", "str"], "expected": True}


PROBES = [_probe(300, 9), _probe(1200, 10)]


def runtime_rule(tr: dict) -> str | None:
    a = probe(tr, "n300")
    if a is None or a.get("error"):
        return None
    n = 300
    sorts = ccount(a, "sorted", "list.sort")
    if sorts >= 1 and opcount(a, "ccmp") >= n:
        return "sort_compare"
    if ccount(a, "str.count", "count") >= 10:
        return "alphabet_count_scan"
    if ccount(a, "ord") >= n:
        return "fixed_count_array"
    if opcount(a, "chash") >= n or pcount(a, "Counter", "defaultdict") >= 1:
        return "hash_count"
    if sorts >= 1:
        return "sort_compare"
    if sum(a.get("ops", {}).values()) == 0 and a["lines"] <= 3:
        return None
    return "other"


def ast_rule(code: str) -> str | None:
    t = ast_tree(code)
    if t is None:
        return None
    calls = calls_named(t)
    if "sorted" in calls or "sort" in calls:
        return "sort_compare"
    if "count" in calls and any(isinstance(n, (ast.For, ast.comprehension)) for n in ast.walk(t)):
        return "alphabet_count_scan"
    if "ord" in calls:
        return "fixed_count_array"
    if any(c in calls for c in ("Counter", "defaultdict", "get", "dict", "setdefault")) or \
            any(isinstance(n, (ast.Dict, ast.DictComp)) for n in ast.walk(t)):
        return "hash_count"
    return "other"
