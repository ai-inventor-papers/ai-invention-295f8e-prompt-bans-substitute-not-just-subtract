"""A7 longest substring that reads the same both ways: references, mutants, baselines, generator, probes."""
import json
import random
import string

REFERENCES = {
    "expand_center": '''
def solve(s):
    best_l, best_r = 0, 0
    n = len(s)
    for c in range(2 * n - 1):
        l, r = c // 2, c // 2 + c % 2
        while l >= 0 and r < n and s[l] == s[r]:
            l -= 1
            r += 1
        if r - l - 1 > best_r - best_l:
            best_l, best_r = l + 1, r
    return s[best_l:best_r]
''',
    "dp_table": '''
def solve(s):
    n = len(s)
    dp = [[False] * n for _ in range(n)]
    start, length = 0, 1
    for i in range(n - 1, -1, -1):
        dp[i][i] = True
        for j in range(i + 1, n):
            if s[i] == s[j] and (j - i < 3 or dp[i + 1][j - 1]):
                dp[i][j] = True
                if j - i + 1 > length:
                    start, length = i, j - i + 1
    return s[start:start + length]
''',
    "manacher": '''
def solve(s):
    t = "^#" + "#".join(s) + "#$"
    n = len(t)
    p = [0] * n
    center = right = 0
    for i in range(1, n - 1):
        if i < right:
            p[i] = min(right - i, p[2 * center - i])
        while t[i + p[i] + 1] == t[i - p[i] - 1]:
            p[i] += 1
        if i + p[i] > right:
            center, right = i, i + p[i]
    k = max(range(n), key=lambda i: p[i])
    start = (k - p[k]) // 2
    return s[start:start + p[k]]
''',
    "brute_force": '''
def solve(s):
    n = len(s)
    for length in range(n, 0, -1):
        for i in range(n - length + 1):
            sub = s[i:i + length]
            if sub == sub[::-1]:
                return sub
    return s[:1]
''',
}

MUTANTS = [
    ("expand_center", '''
def solve(s):
    best = s[:1]
    n = len(s)
    for c in range(n):
        l = r = c
        while l >= 0 and r < n and s[l] == s[r]:
            l -= 1
            r += 1
        if r - l - 1 > len(best):
            best = s[l + 1:r]
    return best
'''),
    ("dp_table", '''
def solve(s):
    n = len(s)
    dp = [[False] * n for _ in range(n)]
    start, length = 0, 1
    for i in range(n - 1, -1, -1):
        dp[i][i] = True
        for j in range(i + 1, n):
            if s[i] == s[j] and (j - i < 3 or dp[i][j - 1]):
                dp[i][j] = True
                if j - i + 1 > length:
                    start, length = i, j - i + 1
    return s[start:start + length]
'''),
    ("manacher", '''
def solve(s):
    t = "^#" + "#".join(s) + "#$"
    n = len(t)
    p = [0] * n
    center = right = 0
    for i in range(1, n - 1):
        if i < right:
            p[i] = min(right - i, p[2 * center - i])
        while t[i + p[i] + 1] == t[i - p[i] - 1]:
            p[i] += 1
        if i + p[i] > right:
            center, right = i, i + p[i]
    k = max(range(n), key=lambda i: p[i])
    start = (k - p[k]) // 2 + 1
    return s[start:start + p[k]]
'''),
    ("brute_force", '''
def solve(s):
    best = ""
    for i in range(len(s)):
        for j in range(i, len(s)):
            sub = s[i:j]
            if sub == sub[::-1] and len(sub) > len(best):
                best = sub
    return best
'''),
]

BASELINES = []

VARIANTS = {
    "expand_helper": ("expand_center", '''
def solve(s):
    def expand(l, r):
        while l >= 0 and r < len(s) and s[l] == s[r]:
            l -= 1
            r += 1
        return s[l + 1:r]
    res = ""
    for i in range(len(s)):
        for cand in (expand(i, i), expand(i, i + 1)):
            if len(cand) > len(res):
                res = cand
    return res
'''),
    "dp_by_length": ("dp_table", '''
def solve(s):
    n = len(s)
    if n < 2:
        return s
    dp = [[0] * n for _ in range(n)]
    best = (0, 0)
    for i in range(n):
        dp[i][i] = 1
    for L in range(2, n + 1):
        for i in range(n - L + 1):
            j = i + L - 1
            if s[i] == s[j] and (L == 2 or dp[i + 1][j - 1]):
                dp[i][j] = 1
                best = (i, j)
    return s[best[0]:best[1] + 1]
'''),
    "brute_all": ("brute_force", '''
def solve(s):
    best = s[0]
    for i in range(len(s)):
        for j in range(i + len(best) + 1, len(s) + 1):
            t = s[i:j]
            if t == t[::-1]:
                best = t
    return best
'''),
}


def _pal(rng, k):
    h = "".join(rng.choice("abc") for _ in range(k // 2))
    return h + (rng.choice("abc") if k % 2 else "") + h[::-1]


def gen_cases(rng: random.Random) -> list:
    out = []
    edge = ["a", "ab", "aa", "aba", "abba", "abc", "babad", "cbbd", "a" * 600, "ab" * 300, "0123210", "9" * 2,
            "abcdcbaxyz"]
    for i, e in enumerate(edge):
        out.append({"case_id": f"gen:edge:{i}", "kind": "edge", "kwargs": {"s": e}})
    al = string.ascii_lowercase + string.digits
    for i in range(14):
        n = rng.randint(1, 120)
        s = "".join(rng.choice("ab" if i % 2 else al) for _ in range(n))
        out.append({"case_id": f"gen:rand:{i}", "kind": "random", "kwargs": {"s": s}})
    st = []
    st.append("".join(rng.choice(al) for _ in range(600)))
    base = "".join(rng.choice("ab") for _ in range(600))
    st.append(base)
    x = "".join(rng.choice(al) for _ in range(600))
    p = _pal(rng, 301)
    st.append(x[:150] + p + x[451:600])
    st.append("ab" * 299 + "a")
    st.append("".join(rng.choice("abc") for _ in range(600)))
    st.append("a" * 300 + "b" + "a" * 299)
    for i, e in enumerate(st):
        out.append({"case_id": f"gen:stress:{i}", "kind": "stress", "kwargs": {"s": e[:600]}})
    return out


def lc_ok(kwargs, expected) -> bool:
    s = kwargs.get("s")
    return isinstance(s, str) and 1 <= len(s) <= 600 and all(c in string.ascii_lowercase + string.digits for c in s)


_r = random.Random(7777)
_s = "".join(_r.choice("abc") for _ in range(150))
_p = _pal(_r, 21)
_s1 = _s[:60] + _p + _s[81:150]
PROBES = [{"name": "rand150", "kwargs_json": json.dumps({"s": _s1}), "wrap": {"s": "cstr_id"}, "trace_ops": True},
          {"name": "uni80", "kwargs_json": json.dumps({"s": "a" * 80}), "wrap": {"s": "cstr_id"}}]
