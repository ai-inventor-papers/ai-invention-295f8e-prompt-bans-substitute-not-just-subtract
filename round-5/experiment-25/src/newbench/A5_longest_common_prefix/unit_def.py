"""A5 longest common prefix: references, mutants, baselines, generator, probes."""
import json
import random
import string

REFERENCES = {
    "horizontal_scan": '''
def solve(strs):
    prefix = strs[0]
    for s in strs[1:]:
        while not s.startswith(prefix):
            prefix = prefix[:-1]
            if not prefix:
                return ""
    return prefix
''',
    "vertical_scan": '''
def solve(strs):
    first = strs[0]
    for i in range(len(first)):
        c = first[i]
        for s in strs[1:]:
            if i >= len(s) or s[i] != c:
                return first[:i]
    return first
''',
    "sort_ends": '''
def solve(strs):
    lo, hi = min(strs), max(strs)
    i = 0
    while i < len(lo) and i < len(hi) and lo[i] == hi[i]:
        i += 1
    return lo[:i]
''',
    "binary_search_length": '''
def solve(strs):
    def ok(k):
        p = strs[0][:k]
        return all(s.startswith(p) for s in strs)
    lo, hi = 0, min(len(s) for s in strs)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if ok(mid):
            lo = mid
        else:
            hi = mid - 1
    return strs[0][:lo]
''',
    "divide_conquer": '''
def solve(strs):
    def common(a, b):
        i = 0
        while i < len(a) and i < len(b) and a[i] == b[i]:
            i += 1
        return a[:i]

    def rec(lo, hi):
        if lo == hi:
            return strs[lo]
        mid = (lo + hi) // 2
        return common(rec(lo, mid), rec(mid + 1, hi))
    return rec(0, len(strs) - 1)
''',
    "trie": '''
class TrieNode:
    def __init__(self):
        self.children = {}
        self.end = False


def solve(strs):
    root = TrieNode()
    for s in strs:
        node = root
        for ch in s:
            if ch not in node.children:
                node.children[ch] = TrieNode()
            node = node.children[ch]
        node.end = True
    out = []
    node = root
    while len(node.children) == 1 and not node.end:
        ch, nxt = next(iter(node.children.items()))
        out.append(ch)
        node = nxt
    return "".join(out)
''',
    "library_commonprefix": '''
import os


def solve(strs):
    return os.path.commonprefix(strs)
''',
}

MUTANTS = [
    ("horizontal_scan", '''
def solve(strs):
    prefix = strs[0]
    for s in strs[1:2]:
        while not s.startswith(prefix):
            prefix = prefix[:-1]
    return prefix
'''),
    ("vertical_scan", '''
def solve(strs):
    first = strs[0]
    for i in range(len(first)):
        for s in strs[1:]:
            if i >= len(s) or s[i] != first[i]:
                return first[:i + 1]
    return first
'''),
    ("sort_ends", '''
def solve(strs):
    s = sorted(strs)
    a, b = s[0], s[1]
    i = 0
    while i < min(len(a), len(b)) and a[i] == b[i]:
        i += 1
    return a[:i]
'''),
    ("binary_search_length", '''
def solve(strs):
    lo, hi = 0, min(len(s) for s in strs)
    while lo < hi:
        mid = (lo + hi) // 2
        if all(s.startswith(strs[0][:mid]) for s in strs):
            lo = mid + 1
        else:
            hi = mid
    return strs[0][:lo]
'''),
    ("divide_conquer", '''
def solve(strs):
    def rec(lo, hi):
        if lo == hi:
            return strs[lo]
        mid = (lo + hi) // 2
        return rec(lo, mid)
    return rec(0, len(strs) - 1)
'''),
    ("trie", '''
def solve(strs):
    root = {}
    for s in strs:
        node = root
        for ch in s:
            node = node.setdefault(ch, {})
    out = []
    node = root
    while len(node) == 1:
        ch = next(iter(node))
        out.append(ch)
        node = node[ch]
    return "".join(out)
'''),
    ("library_commonprefix", '''
import os


def solve(strs):
    return os.path.commonprefix(strs[:2])
'''),
]

BASELINES = []

VARIANTS = {
    "zip_set": ("vertical_scan", '''
def solve(strs):
    res = []
    for chars in zip(*strs):
        if len(set(chars)) == 1:
            res.append(chars[0])
        else:
            break
    return "".join(res)
'''),
    "sorted_first_last": ("sort_ends", '''
def solve(strs):
    strs = sorted(strs)
    a, b = strs[0], strs[-1]
    i = 0
    while i < len(a) and i < len(b) and a[i] == b[i]:
        i += 1
    return a[:i]
'''),
    "horizontal_charloop": ("horizontal_scan", '''
def solve(strs):
    prefix = strs[0]
    for s in strs[1:]:
        j = 0
        while j < len(prefix) and j < len(s) and prefix[j] == s[j]:
            j += 1
        prefix = prefix[:j]
    return prefix
'''),
    "from_ospath": ("library_commonprefix", '''
from os.path import commonprefix


def solve(strs):
    return commonprefix(strs)
'''),
    "trie_dict": ("trie", '''
def solve(strs):
    trie = {}
    for w in strs:
        cur = trie
        for c in w:
            cur = cur.setdefault(c, {})
        cur["$"] = True
    pre = ""
    cur = trie
    while len(cur) == 1 and "$" not in cur:
        c = next(iter(cur))
        pre += c
        cur = cur[c]
    return pre
'''),
}


def _w(rng, k):
    return "".join(rng.choice(string.ascii_lowercase) for _ in range(k))


def gen_cases(rng: random.Random) -> list:
    out = []
    edge = [["a"], [""], ["", "abc"], ["abc", "abc"], ["ab", "a"], ["flower", "flow", "flight"], ["dog", "racecar", "car"],
            ["a" * 200, "a" * 200], ["abc", "abd", "ab"], ["z", "z", "y"]]
    for i, e in enumerate(edge):
        out.append({"case_id": f"gen:edge:{i}", "kind": "edge", "kwargs": {"strs": e}})
    for i in range(14):
        m = rng.randint(1, 30)
        base = _w(rng, rng.randint(0, 30))
        strs = [base[:rng.randint(len(base) // 2, len(base))] + _w(rng, rng.randint(0, 10)) for _ in range(m)]
        out.append({"case_id": f"gen:rand:{i}", "kind": "random", "kwargs": {"strs": strs}})
    st = []
    p = _w(rng, 199)
    st.append([p + _w(rng, 1) for _ in range(200)])
    st.append(["a" * 200] * 199 + ["a" * 199 + "b"])
    st.append([_w(rng, 100) + _w(rng, 100) for _ in range(200)])
    q = _w(rng, 150)
    st.append([q + _w(rng, 50) for _ in range(199)] + [q])
    st.append(["x" * 200 for _ in range(200)])
    for i, e in enumerate(st):
        out.append({"case_id": f"gen:stress:{i}", "kind": "stress", "kwargs": {"strs": e}})
    return out


def lc_ok(kwargs, expected) -> bool:
    s = kwargs.get("strs")
    return isinstance(s, list) and 1 <= len(s) <= 200 and all(
        isinstance(x, str) and len(x) <= 200 and all(c in string.ascii_lowercase for c in x) for x in s)


_r = random.Random(5555)
_pre = "".join(_r.choice(string.ascii_lowercase) for _ in range(12))
_strs = [_pre + "".join(_r.choice(string.ascii_lowercase) for _ in range(_r.randint(8, 20))) for _ in range(40)]
_strs[7] = _pre + "q"
PROBES = [{"name": "lcp40", "kwargs_json": json.dumps({"strs": _strs}), "wrap": {"strs": "clist_cstr"},
           "trace_ops": True}]
