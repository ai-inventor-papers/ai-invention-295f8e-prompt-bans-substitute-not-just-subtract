"""I2 group anagrams (LeetCode 49; order-free 'groups' checker; n <= 20000 so pairwise grouping exceeds the limit)."""

from __future__ import annotations

import ast
import random
import string

from unitlib6 import ast_tree, binop, call, calls_named, has_dict, maxlen, op, probe

CHECKER = "groups"
ARGS = ["strs"]

ORACLE_A = '''
def solve(strs):
    from collections import defaultdict
    d = defaultdict(list)
    for s in strs:
        k = ''.join(sorted(s))
        d[k].append(s)
    return list(d.values())
'''  # dataset reference (LeetCode 49 row)
ORACLE_B = '''
def solve(strs):
    groups = {}
    for s in strs:
        c = [0] * 26
        for ch in s:
            c[ord(ch) - 97] += 1
        groups.setdefault(tuple(c), []).append(s)
    return list(groups.values())
'''

REFERENCES = {
    "sorted_key": '''
def solve(strs):
    groups = {}
    for w in strs:
        key = "".join(sorted(w))
        if key not in groups:
            groups[key] = []
        groups[key].append(w)
    return list(groups.values())
''',
    "count_key": '''
def solve(strs):
    groups = {}
    for w in strs:
        cnt = [0] * 26
        for ch in w:
            cnt[ord(ch) - ord("a")] += 1
        groups.setdefault(tuple(cnt), []).append(w)
    return list(groups.values())
''',
    "prime_product": '''
def solve(strs):
    primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97, 101]
    groups = {}
    for w in strs:
        key = 1
        for ch in w:
            key *= primes[ord(ch) - 97]
        groups.setdefault(key, []).append(w)
    return list(groups.values())
''',
    "sort_then_group": '''
def solve(strs):
    order = sorted(range(len(strs)), key=lambda i: "".join(sorted(strs[i])))
    out = []
    prev = None
    for i in order:
        sig = "".join(sorted(strs[i]))
        if sig != prev:
            out.append([])
            prev = sig
        out[-1].append(strs[i])
    return out
''',
}
MUTANTS = [
    '''
def solve(strs):
    groups = {}
    for w in strs:
        groups.setdefault(len(w), []).append(w)
    return list(groups.values())
''',
    '''
def solve(strs):
    groups = {}
    for w in strs:
        groups.setdefault("".join(sorted(set(w))), []).append(w)
    return list(groups.values())
''',
    '''
def solve(strs):
    groups = {}
    for w in strs:
        key = "".join(sorted(w))
        groups[key] = [w]
    return list(groups.values())
''',
]
EXCLUDED = {
    "pairwise_grouping": '''
def solve(strs):
    groups = []
    for w in strs:
        for g in groups:
            if sorted(g[0]) == sorted(w):
                g.append(w)
                break
        else:
            groups.append([w])
    return groups
''',
}


def _word(rng: random.Random, L: int, alpha: str = string.ascii_lowercase) -> str:
    return "".join(rng.choice(alpha) for _ in range(L))


def _case(rng: random.Random, n: int, n_groups: int, maxlen_: int = 8, alpha: str = string.ascii_lowercase) -> list:
    reps = [_word(rng, rng.randint(0, maxlen_), alpha) for _ in range(max(1, n_groups))]
    out = []
    for _ in range(n):
        w = list(rng.choice(reps))
        rng.shuffle(w)
        out.append("".join(w))
    return [out]


def make_tests() -> list[dict]:
    rng = random.Random(49)
    cases = [("ex0", [["eat", "tea", "tan", "ate", "nat", "bat"]]), ("ex1", [[""]]), ("ex2", [["a"]]),
             ("edge_dup", [["ab", "ba", "ab", ""]]), ("edge_empty2", [["", "", "b"]]),
             ("edge_same_letters", [["aab", "aba", "abb", "bab", "bba"]])]
    sizes = [1, 2, 3, 5, 10, 20, 50, 100, 300, 1000]
    for i in range(44):
        n = sizes[i % len(sizes)]
        cases.append((f"rand{i}", _case(rng, n, max(1, n // rng.choice([1, 2, 3, 5])), rng.choice([3, 6, 10]),
                                        rng.choice(["abc", "abcdef", string.ascii_lowercase]))))
    for j in range(6):
        cases.append((f"stress{j}", _case(rng, 20000, 12000 if j % 2 == 0 else 6000, 30)))
    return [{"case_id": f"I2:{cid}", "kind": "stress" if cid.startswith("stress") else
             ("example" if cid.startswith("ex") else "random"), "args": a} for cid, a in cases]


def _probe(n: int, seed: int, name: str) -> dict:
    rng = random.Random(seed)
    a = _case(rng, n, n // 3, 7)[0]
    groups = {}
    for w in a:
        groups.setdefault("".join(sorted(w)), []).append(w)
    exp = sorted(sorted(g) for g in groups.values())
    return {"name": name, "args": [a], "wrap": ["list"], "expected": exp, "checker": "groups", "n_letters":
            sum(len(w) for w in a)}


PROBES = [_probe(120, 5, "p120"), _probe(240, 6, "p240")]


def runtime_rule(tr: dict) -> str | None:
    a = probe(tr, "p120")
    if a is None:
        return None
    n = 120
    letters = PROBES[0]["n_letters"]
    if call(a, "groupby") >= 1 or max(maxlen(a, "sorted", "sort"), -1) >= int(0.8 * n):
        return "sort_then_group"
    if call(a, "sorted", "sort") >= int(0.8 * n):
        return "sorted_key"
    if binop(a, "*") >= int(0.6 * letters):
        return "prime_product"
    if call(a, "ord") >= int(0.6 * letters) or call(a, "Counter") >= int(0.8 * n) or \
            call(a, "count") >= int(0.8 * n) or op(a, "STORE_SUBSCR") >= int(0.6 * letters):
        return "count_key"
    return "other"


def ast_rule(code: str) -> str | None:
    t = ast_tree(code)
    if t is None:
        return None
    calls = calls_named(t)
    consts = [n.value for n in ast.walk(t) if isinstance(n, ast.Constant) and isinstance(n.value, int)]
    if "groupby" in calls:
        return "sort_then_group"
    primes = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97, 101}
    if len(primes & set(consts)) >= 10 or ("Mult" in [type(n.op).__name__ for n in ast.walk(t)
                                                     if isinstance(n, (ast.BinOp, ast.AugAssign))]
                                           and any(nm in {x.id for x in ast.walk(t) if isinstance(x, ast.Name)}
                                                   for nm in ("primes", "prime", "PRIMES", "prime_map", "primes_map"))):
        return "prime_product"
    if ("sorted" in calls or "sort" in calls) and not has_dict(t):
        return "sort_then_group"
    if ("sorted" in calls or "sort" in calls) and has_dict(t):
        return "sorted_key"
    if "ord" in calls or "Counter" in calls or "count" in calls or "frozenset" in calls:
        return "count_key"
    return "other"
