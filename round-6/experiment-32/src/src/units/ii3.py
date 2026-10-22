"""II3 count_ones (LeetCode 191 'number of 1 bits', 0 <= x < 2**32). The probes wrap x as a PROPAGATING traced int
(sandbox_trace.PInt), so loops that rebind x keep counting: 2**31 separates Kernighan (popcount iterations) from the
shift loop (bit-length iterations); 2**32 - 1 confirms the loop."""

from __future__ import annotations

import random

from unitlib import ast_tree, calls_named, ccount, opcount, probe
from units.ii_common import binop_kinds, const_values, kernighan_pattern

CHECKER = "exact"
ARGS = ["x"]

ORACLE_A = '''
def solve(x):
    ans = 0
    while x:
        x &= x - 1
        ans += 1
    return ans
'''  # dataset reference (LeetCode 191 row), adapted
ORACLE_B = '''
def solve(x):
    return bin(x).count("1")
'''

REFERENCES = {
    "library_count": ORACLE_B,
    "kernighan": ORACLE_A,
    "shift_mask": '''
def solve(x):
    c = 0
    while x:
        c += x & 1
        x >>= 1
    return c
''',
    "lookup_table": '''
_T = [0] * 256
for _i in range(1, 256):
    _T[_i] = _T[_i >> 1] + (_i & 1)


def solve(x):
    return _T[x & 255] + _T[(x >> 8) & 255] + _T[(x >> 16) & 255] + _T[(x >> 24) & 255]
''',
}
MUTANTS = [
    '''
def solve(x):
    return bin(x).count("0")
''',
    '''
def solve(x):
    c = 0
    while x > 1:
        c += x & 1
        x >>= 1
    return c
''',
    '''
def solve(x):
    return len(bin(x)) - 2
''',
]
EXCLUDED: dict[str, str] = {}
ARITH = ("and", "rshift", "floordiv", "mod", "sub", "divmod", "truediv")


def make_tests() -> list[dict]:
    rng = random.Random(191)
    vals = [11, 128, 4294967293, 0, 1, 2, 3, 4294967295, 2147483648, 2147483647, 255, 256, 65535, 65536, 16777216]
    cases = [(f"ex{i}", [v]) for i, v in enumerate(vals)]
    for i in range(50):
        b = rng.randint(1, 32)
        cases.append((f"rand{i}", [rng.getrandbits(b)]))
    for i in range(10):
        cases.append((f"stress{i}", [rng.choice([(1 << 32) - 1, (1 << 31), rng.getrandbits(32) | (1 << 31)])]))
    return [{"case_id": f"II3:{cid}", "kind": "stress" if cid.startswith("stress") else
             ("example" if cid.startswith("ex") else "random"), "args": a} for cid, a in cases]


PROBES = [{"name": "p_pow31", "args": [1 << 31], "wrap": ["pint"], "expected": 1},
          {"name": "p_full", "args": [(1 << 32) - 1], "wrap": ["pint"], "expected": 32},
          {"name": "p_11", "args": [11], "wrap": ["pint"], "expected": 3}]


def runtime_rule(tr: dict) -> str | None:
    a, b = probe(tr, "p_pow31"), probe(tr, "p_full")
    if a is None or b is None or a.get("error") or b.get("error"):
        return None
    ar_a, ar_b = opcount(a, *ARITH), opcount(b, *ARITH)
    idx_a = opcount(a, "index")
    lib = ccount(a, "bin", "format", "int.bit_count", "bit_count", "str.count") + ccount(b, "bin", "format",
                                                                                         "int.bit_count",
                                                                                         "bit_count", "str.count")
    if (idx_a >= 3 or (4 <= ar_a and lib == 0)) and ar_a <= 12 and ar_b <= 12:
        return "lookup_table"          # byte extraction: a constant number of & / >> ops on both probes
    if lib >= 1 and ar_a <= 3 and ar_b <= 3:
        return "library_count"
    if ar_a >= 25:
        return "shift_mask"
    if ar_a <= 6 and ar_b >= 25:
        return "kernighan"
    if ar_a == 0 and ar_b == 0 and idx_a == 0 and lib == 0:
        return None
    return "other"


def ast_rule(code: str) -> str | None:
    t = ast_tree(code)
    if t is None:
        return None
    calls = calls_named(t)
    consts = const_values(t)
    ops = binop_kinds(t)
    if (255 in consts or 0xFF in consts) and (256 in consts or "range" in calls) and \
            any(o == "RShift" and c in (8, 16, 24) for o, c in ops):
        return "lookup_table"
    if kernighan_pattern(t):
        return "kernighan"
    if any(c in calls for c in ("bin", "format", "bit_count")):
        return "library_count"
    if any(o == "RShift" for o, _ in ops) or any(o in ("FloorDiv", "Mod") and c == 2 for o, c in ops) or \
            any(o == "BitAnd" and c == 1 for o, c in ops) or any(o == "LShift" for o, _ in ops):
        return "shift_mask"
    return "other"
