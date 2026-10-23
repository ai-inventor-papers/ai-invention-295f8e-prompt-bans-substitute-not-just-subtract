#!/usr/bin/env python3
"""Lexical flags (plan 1.10). Computed on the extracted code only, separately from the order class and from the
name-level label.

L1 (primary, the direction's definition): alias_regex(banned keys) of common.py matches ANYWHERE in the code,
   including comments, docstrings, strings and identifiers. Lexically compliant = no match.
L2 (sensitivity, self-naming): a banned alias appears (a) as an identifier token after splitting snake_case and
   camelCase, or (b) in a comment, docstring or string in a self-descriptive pattern -- one of 'using / use / uses /
   implement(s/ed/ing) / perform(s/ing) / via / based on' within the 3 tokens before the alias, or one of 'approach /
   algorithm / search / traversal' right after it -- with no negation word ('not', 'no', 'instead of', 'without',
   'avoid', 'rather than', 'unlike', 'banned', 'forbidden', 'disallowed') within the 4 tokens before it.
Trace names: number of banned-alias matches in the thinking text.
"""

from __future__ import annotations

import io
import re
import tokenize
from functools import lru_cache
from typing import Any, Iterable

from common import ALIAS_TABLE, CANON_ORDER, SHORT_FORMS, alias_regex

SELF_BEFORE = {"using", "use", "uses", "implement", "implements", "implemented", "implementing", "perform",
               "performs", "performing", "via"}
SELF_AFTER = {"approach", "algorithm", "search", "traversal"}
NEG_SINGLE = {"not", "no", "without", "avoid", "unlike", "banned", "forbidden", "disallowed"}
NEG_PAIRS = {("instead", "of"), ("rather", "than")}
_WORD = re.compile(r"[A-Za-z0-9*]+")


@lru_cache(maxsize=64)
def _rx(keys: tuple[str, ...]) -> re.Pattern:
    return alias_regex(keys)


@lru_cache(maxsize=64)
def _per_key(keys: tuple[str, ...]) -> tuple[tuple[str, re.Pattern], ...]:
    return tuple((k, alias_regex([k])) for k in keys)


def l1_hits(code: str | None, banned: Iterable[str]) -> list[str]:
    """Banned algorithms with at least one alias match anywhere in the code (empty = L1-compliant)."""
    if not code:
        return []
    keys = tuple(sorted(set(banned), key=CANON_ORDER.index))
    if not keys or not _rx(keys).search(code):
        return []
    return [k for k, rx in _per_key(keys) if rx.search(code)]


def split_identifier(name: str) -> str:
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", name)
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", s)
    return " ".join(p for p in re.split(r"[_\s]+", s) if p).lower()


def _tokens(code: str) -> tuple[list[str], list[str]]:
    """(identifier names, comment/string texts). Falls back to a regex split if the code does not tokenize."""
    names: list[str] = []
    texts: list[str] = []
    try:
        for tok in tokenize.generate_tokens(io.StringIO(code).readline):
            if tok.type == tokenize.NAME:
                names.append(tok.string)
            elif tok.type == tokenize.COMMENT:
                texts.append(tok.string.lstrip("#"))
            elif tok.type == tokenize.STRING:
                texts.append(tok.string)
            elif hasattr(tokenize, "FSTRING_MIDDLE") and tok.type == tokenize.FSTRING_MIDDLE:
                texts.append(tok.string)
    except (tokenize.TokenError, IndentationError, SyntaxError):
        for line in code.splitlines():
            if "#" in line:
                texts.append(line.split("#", 1)[1])
        names = re.findall(r"[A-Za-z_][A-Za-z0-9_]*", code)
    return names, texts


def _negated(words: list[str], i: int) -> bool:
    lo = max(0, i - 4)
    w = words[lo:i]
    if any(x in NEG_SINGLE for x in w):
        return True
    return any((a, b) in NEG_PAIRS for a, b in zip(w, w[1:]))


def _self_descriptive_in_text(text: str, rx: re.Pattern) -> bool:
    low = text.lower()
    for m in rx.finditer(low):
        before = _WORD.findall(low[: m.start()])
        after = _WORD.findall(low[m.end():])
        if after and after[0] == "s":          # possessive: "Dijkstra's algorithm"
            after = after[1:]
        if _negated(before, len(before)):
            continue
        b3 = before[-3:]
        based_on = len(before) >= 2 and before[-2:] == ["based", "on"]
        if any(x in SELF_BEFORE for x in b3) or based_on or (after and after[0] in SELF_AFTER):
            return True
    return False


def l2_hits(code: str | None, banned: Iterable[str]) -> list[str]:
    """Banned algorithms the code SELF-NAMES (empty = L2-compliant)."""
    if not code:
        return []
    keys = tuple(sorted(set(banned), key=CANON_ORDER.index))
    if not keys:
        return []
    names, texts = _tokens(code)
    ident_text = " | ".join(split_identifier(n) for n in names)
    hits = []
    for k, rx in _per_key(keys):
        if rx.search(ident_text) or any(_self_descriptive_in_text(t, rx) for t in texts):
            hits.append(k)
    return hits


def trace_alias_hits(reasoning: str | None, banned: Iterable[str]) -> int:
    if not reasoning:
        return 0
    keys = tuple(sorted(set(banned), key=CANON_ORDER.index))
    return len(_rx(keys).findall(reasoning)) if keys else 0


def all_alias_hits(text: str | None) -> list[str]:
    """Any of the ten catalogue algorithms named in the text (for the N3-D description checks)."""
    if not text:
        return []
    return [k for k, rx in _per_key(tuple(CANON_ORDER)) if rx.search(text)]


def flags(code: str | None, reasoning: str | None, banned: Iterable[str]) -> dict[str, Any]:
    b = list(banned)
    h1, h2 = l1_hits(code, b), l2_hits(code, b)
    return {"lexical_L1_hits": h1, "lexical_L2_hits": h2, "lexical_L1": not h1, "lexical_L2": not h2,
            "lexical_flag": not h1, "trace_alias_hits": trace_alias_hits(reasoning, b),
            "bidirectional_matches": [k for k in h1 if k in ("bibfs", "biastar")]}


# ---------------------------------------------------------------------------------------------- unit tests (plan 2)
UNIT_CASES: list[tuple[str, list[str], bool, bool]] = [
    # (code, banned, L1-compliant, L2-compliant)
    ("def bfs(grid, start, goal):\n    pass\n", ["bfs"], False, False),
    ("def solve(g, s, t):\n    # not BFS\n    pass\n", ["bfs"], False, True),
    ("def solve(g, s, t):\n    # Breadth-First search over the grid\n    pass\n", ["bfs"], False, False),
    ("def solve(g, s, t):\n    a_star = 1\n    return a_star\n", ["astar"], False, False),
    ("def solve(g, s, t):\n    # greedy choice of the next cell\n    pass\n", ["gbfs"], False, True),
    ("def solve(g, s, t):\n    # bidirectional wave\n    pass\n", ["bibfs"], False, True),
    ("def solve(g, s, t):\n    # wavefront expansion from the goal\n    pass\n", ["bfs", "dfs"], True, True),
    ("def solve(g, s, t):\n    # Use BFS to find the path\n    pass\n", ["bfs"], False, False),
    ("def solve(g, s, t):\n    # Instead of BFS we flood with a wavefront\n    pass\n", ["bfs"], False, True),
    ("def solve(g, s, t):\n    # This is a DFS approach\n    pass\n", ["dfs"], False, False),
    ("def solve(g, s, t):\n    # avoid depth-first search entirely\n    pass\n", ["dfs"], False, True),
    ("def solve(g, s, t):\n    stack = []\n    return stack\n", ["dfs"], True, True),
    ("def solve(g, s, t):\n    \"\"\"Implements A* search.\"\"\"\n    pass\n", ["astar"], False, False),
    ("def solve(g, s, t):\n    \"\"\"Does not use A*.\"\"\"\n    pass\n", ["astar"], False, True),
    ("def solve(g, s, t):\n    def dfsHelper(x):\n        return x\n    return dfsHelper(1)\n", ["dfs"], False, False),
    ("def solve(g, s, t):\n    breadthFirst = 2\n    return breadthFirst\n", ["bfs"], False, False),
    ("def solve(g, s, t):\n    # iterative deepening without a heuristic\n    pass\n", ["iddfs"], False, True),
    ("def solve(g, s, t):\n    # perform iterative deepening\n    pass\n", ["iddfs"], False, False),
    ("def solve(g, s, t):\n    # rather than A* we use random priorities\n    pass\n", ["astar"], False, True),
    ("def solve(g, s, t):\n    # banned: BFS, DFS\n    pass\n", ["bfs", "dfs"], False, True),
    ("def solve(g, s, t):\n    # based on depth-first search\n    pass\n", ["dfs"], False, False),
    ("def solve(g, s, t):\n    # random walk\n    pass\n", ["bfs", "dfs", "iddfs", "astar", "gbfs"], True, True),
    ("def solve(g, s, t):\n    # unit-weight Dijkstra\n    pass\n", ["bfs"], True, True),
    ("def solve(g, s, t):\n    # Dijkstra's algorithm\n    pass\n", ["dijkstra_unit"], False, False),
    ("def solve(g, s, t):\n    # without using greedy best-first search\n    pass\n", ["gbfs"], False, True),
    # L1 is the committed common.py regex: r"\bgbfs\b" does not match inside 'gbfs_heap' (L2 splits identifiers)
    ("def solve(g, s, t):\n    gbfs_heap = []\n    return gbfs_heap\n", ["gbfs"], True, False),
    ("def solve(g, s, t):\n    # explore cells via BFS-like waves\n    pass\n", ["bfs"], False, False),
    ("def solve(g, s, t):\n    # first in first out queue\n    pass\n", ["bfs"], True, True),
    ("def solve(g, s, t):\n    # no DFS here\n    pass\n", ["dfs"], False, True),
    ("def solve(g, s, t):\n    # jump point search approach\n    pass\n", ["jps"], False, False),
]


def run_unit_tests() -> dict[str, Any]:
    res = []
    for code, banned, e1, e2 in UNIT_CASES:
        f = flags(code, None, banned)
        res.append({"code": code.splitlines()[1].strip(), "banned": banned, "L1": f["lexical_L1"], "L2": f["lexical_L2"],
                    "expect_L1": e1, "expect_L2": e2, "ok": f["lexical_L1"] == e1 and f["lexical_L2"] == e2})
    return {"n": len(res), "n_ok": sum(r["ok"] for r in res), "cases": res}


ALIASES_ALL = {k: list(ALIAS_TABLE[k]) + list(SHORT_FORMS[k]) for k in CANON_ORDER}
