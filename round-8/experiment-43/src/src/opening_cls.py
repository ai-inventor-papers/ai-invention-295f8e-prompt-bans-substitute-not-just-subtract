#!/usr/bin/env python3
"""OC_u: per-unit opening classifier over PARTIAL programs (regex rules on the code with comments, docstrings and
string literals removed). Returns a catalogue label or 'undecided'. Developed on iteration-5 instruct rows of the unit
only; validated (Step B4) on the new twin programs plus held-out iteration-5 instruct programs truncated to the scan
horizon. A continuation whose OC label is 'undecided' at the horizon is completed to the fence and labelled by the
full frozen labeller.

Rules (a label is returned only when its structural evidence is present, so early prefixes stay 'undecided'):
  B3  kruskal      union-find evidence (find(/union(/parent[...]) or edges sorted by weight before any heap
                   frontier; boruvka if 'cheapest' per component appears with union-find
      prim_heap    heap ops (heappush/heappop) together with a visited/in-tree marker and no union-find
      prim_array   O(n^2) selection: a key/dist array + 'min' selection over unvisited cities without a heap
  A3  two_pointers left/right (l/r) indices moving inward under 'while l < r'
      prefix_suffix_max  two max arrays (left_max[i] = max(left_max[i - 1], ...) or a right/suffix array)
      monotonic_stack    a stack with a pop loop
      peak_split   index of the global maximum used to split
  B6  sort_compare sorted(s)/sorted(t) or .sort()
      hash_count   Counter / dict / defaultdict / .get( counting
      fixed_count_array  [0] * 26 or ord(c) - ord('a') indexing
"""

from __future__ import annotations

import io
import re
import tokenize

FENCE_OPEN = re.compile(r"```[ \t]*(?:python3?|py|Python)?[ \t]*\n")


def code_part(text: str) -> str:
    """Code of a (possibly unfinished) generation: after the first opening fence, up to a closing fence."""
    m = FENCE_OPEN.search(text)
    body = text[m.end():] if m else text
    return body.split("```", 1)[0]


def strip_comments(code: str) -> str:
    """Remove # comments and string literals (docstrings) token-wise; falls back to a line regex on partial code."""
    out = []
    try:
        for tk in tokenize.generate_tokens(io.StringIO(code).readline):
            if tk.type in (tokenize.COMMENT,):
                continue
            if tk.type == tokenize.STRING:
                out.append('""')
                continue
            out.append(tk.string)
            if tk.type in (tokenize.NEWLINE, tokenize.NL):
                pass
        return " ".join(out)
    except (tokenize.TokenError, IndentationError, SyntaxError):
        lines = []
        for ln in code.splitlines():
            ln = re.sub(r"#.*$", "", ln)
            lines.append(ln)
        s = "\n".join(lines)
        s = re.sub(r'"""[\s\S]*?("""|$)', '""', s)
        s = re.sub(r"'''[\s\S]*?('''|$)", '""', s)
        return s


def _b3(c: str) -> str:
    uf = re.search(r"\bfind\s*\(|\bunion\s*\(|\bparent\s*\[|\bparent\s*=\s*list\s*\(|\bdsu\b|\bDSU\b|UnionFind|"
                   r"\bparent\s*=\s*\[", c) is not None
    sort_edges = re.search(r"\.sort\s*\(|\bsorted\s*\(", c) is not None
    heap_ops = re.search(r"heappush|heappop|heapify|PriorityQueue", c) is not None
    visited = re.search(r"\bvisited\b|\bin_mst\b|\bin_tree\b|\bmst_set\b|\bseen\b|\bused\b|\badded\b|\bin_mst_set\b|"
                        r"\bincluded\b|\bconnected\b|\bmst\b", c) is not None
    cheapest = re.search(r"\bcheapest\b", c) is not None
    if uf and cheapest:
        return "boruvka"
    if uf:
        return "kruskal"
    if heap_ops and visited and re.search(r"heappop", c):
        return "prim_heap"
    if sort_edges and not heap_ops and re.search(r"(edges|roads)\s*\.sort|sorted\s*\(\s*(edges|roads)", c):
        return "kruskal"
    if (not heap_ops and visited and re.search(r"\bmin_?(cost|dist|key|edge)\w*\s*=\s*\[|\bkey\s*=\s*\[|"
                                                 r"\bdist\s*=\s*\[", c)
            and re.search(r"for\s+\w+\s+in\s+range\s*\(\s*n\s*\)\s*:[\s\S]*if\s+not\s+\w+\s*\[", c)):
        return "prim_array"
    return "undecided"


def _a3(c: str) -> str:
    if re.search(r"\bstack\b", c) and re.search(r"\.pop\s*\(", c):
        return "monotonic_stack"
    tp = re.search(r"while\s+\(?\s*(left|l|i|lo|low)\s*<=?\s*(right|r|j|hi|high)\b", c) is not None
    moves = re.search(r"\b(left|l|i|lo|low)\s*\+=\s*1", c) and re.search(r"\b(right|r|j|hi|high)\s*-=\s*1", c)
    if tp and (moves or re.search(r"(left_max|right_max|lmax|rmax|max_left|max_right|leftmax|rightmax)", c)):
        return "two_pointers"
    arr = re.search(r"\w+\s*\[\s*i\s*\]\s*=\s*max\s*\(\s*\w+\s*\[\s*i\s*[-+]\s*1\s*\]", c) is not None or \
        re.search(r"(left_max|right_max|max_left|max_right|prefix_max|suffix_max|left|right|lmax|rmax|leftmax|"
                  r"rightmax)\s*=\s*\[\s*0\s*\]\s*\*", c) is not None
    if arr:
        return "prefix_suffix_max"
    if re.search(r"\.index\s*\(\s*max\s*\(|max\s*\(\s*range\s*\(", c):
        return "peak_split"
    return "undecided"


def _b6(c: str) -> str:
    if re.search(r"\bsorted\s*\(|\.sort\s*\(", c):
        return "sort_compare"
    if re.search(r"\[\s*0\s*\]\s*\*\s*26|ord\s*\(", c):
        return "fixed_count_array"
    if re.search(r"\bCounter\b|defaultdict|\{\s*\}|\bdict\s*\(|\.get\s*\(", c):
        return "hash_count"
    return "undecided"


RULES = {"B3": _b3, "A3": _a3, "B6": _b6}


def classify(unit: str, text: str) -> str:
    c = strip_comments(code_part(text))
    return RULES[unit](c)
