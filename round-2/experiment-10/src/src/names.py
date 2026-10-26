#!/usr/bin/env python3
"""Frozen NAME TABLE (plan S2.2): whole-word, case-insensitive patterns per catalogue algorithm, ordered so that the
more specific (longer) pattern wins at a given position. Used by the scrubber (union of both tasks) and to parse the
free-form association answers (the task's own table)."""

from __future__ import annotations

import re

_L = r"(?<![A-Za-z0-9_])"  # left whole-word guard (works for 'A*')
_R = r"(?![A-Za-z0-9_])"
_SEARCH = r"(?:[\s_-]+search)?"
_ALG = r"(?:[\s_-]+algorithm)?"

# (mode, pattern) in priority order per task
TABLE: dict[str, list[tuple[str, str]]] = {
    "t1": [
        ("bibfs", r"bi[\s_-]?directional[\s_-]+(?:bfs|breadth[\s_-]?first(?:[\s_-]+search)?|search)"),
        ("bibfs", r"bibfs"),
        ("iddfs", r"iterative[\s_-]+deepening(?:[\s_-]+(?:dfs|depth[\s_-]?first(?:[\s_-]+search)?|search))?"),
        ("iddfs", r"iddfs"),
        ("dijkstra", r"unit[\s_-]?weight[\s_-]+dijkstra(?:'s)?" + _ALG),
        ("astar_gbfs", r"(?:greedy[\s_-]+)?best[\s_-]?first" + _SEARCH),
        ("astar_gbfs", r"gbfs"),
        ("astar_gbfs", r"(?:a\s?\*|a-star|astar|a_star)" + _SEARCH),
        ("dfs", r"depth[\s_-]?first" + _SEARCH),
        ("dfs", r"dfs"),
        ("bfs", r"breadth[\s_-]?first" + _SEARCH),
        ("bfs", r"bfs"),
        ("dijkstra", r"uniform[\s_-]?cost" + _SEARCH),
        ("dijkstra", r"ucs"),
        ("dijkstra", r"dijkstra(?:'s)?" + _ALG),
    ],
    "t2": [
        ("bidijkstra", r"bi[\s_-]?directional[\s_-]+dijkstra(?:'s)?" + _ALG),
        ("bf_spfa", r"bellman[\s-]?ford" + _ALG),
        ("bf_spfa", r"spfa"),
        ("bf_spfa", r"shortest[\s_-]+path[\s_-]+faster" + _ALG),
        ("floyd", r"floyd[\s_-]?warshall" + _ALG),
        ("floyd", r"floyd"),
        ("floyd", r"warshall"),
        ("dial", r"dial(?:'s)?(?:[\s_-]+bucket[\s_-]?queue)?" + _ALG),
        ("dial", r"bucket[\s_-]?queue"),
        ("dijkstra", r"dijkstra(?:'s)?" + _ALG),
    ],
}


def _compile(entries: list[tuple[str, str]]) -> tuple[re.Pattern[str], list[str]]:
    groups = [f"(?P<g{i}>{_L}{pat}{_R})" for i, (_, pat) in enumerate(entries)]
    return re.compile("|".join(groups), re.IGNORECASE), [m for m, _ in entries]


_TASK_RE = {t: _compile(TABLE[t]) for t in TABLE}
# union table for scrubbing: every specific pattern of both tasks before the generic ones, longest pattern first
_UNION = sorted({(m, p) for t in TABLE for (m, p) in TABLE[t]}, key=lambda mp: -len(mp[1]))
_UNION_RE = _compile(_UNION)


def find_all(text: str, task: str | None = None) -> list[tuple[int, int, str]]:
    """[(start, end, mode)] non-overlapping, leftmost-first, most specific pattern first at each position."""
    rx, modes = _TASK_RE[task] if task else _UNION_RE
    out = []
    for m in rx.finditer(text):
        gi = next(i for i, g in enumerate(m.groups()) if g is not None)
        out.append((m.start(), m.end(), modes[gi]))
    return out


def neutralise(text: str, repl: str = "search") -> str:
    """Replace every name-table match (both tasks) by `repl`; collapse 'search search'."""
    hits = find_all(text, None)
    if not hits:
        return text
    pieces, last = [], 0
    for a, b, _ in hits:
        pieces.append(text[last:a])
        pieces.append(repl)
        last = b
    pieces.append(text[last:])
    out = "".join(pieces)
    out = re.sub(r"\bsearch(?:[\s_-]+search)+\b", "search", out, flags=re.IGNORECASE)
    return out


def parse_free(text: str, task: str, x: str) -> str:
    """Free-form answer -> first non-X catalogue algorithm matched; 'none' if only X or nothing is named."""
    for _, _, mode in find_all(text, task):
        if mode != x:
            return mode
    return "none"


# identifier pieces that trigger a rename (plan S2.2 iii) plus the two pairs
ID_PIECES = {"bfs", "dfs", "iddfs", "bibfs", "gbfs", "astar", "dijkstra", "bidijkstra", "bellman", "ford", "spfa",
             "floyd", "warshall", "dial", "bidir", "bidirectional", "breadth", "ucs"}
ID_PAIRS = {("a", "star"), ("depth", "first")}


def split_identifier(name: str) -> list[str]:
    parts = []
    for chunk in name.split("_"):
        if not chunk:
            continue
        parts += [p for p in re.findall(r"[A-Z]+(?=[A-Z][a-z]|\d|\b)|[A-Z]?[a-z]+|[A-Z]+|\d+", chunk)]
    return [p.lower() for p in parts]


def identifier_names_algorithm(name: str) -> bool:
    ps = split_identifier(name)
    if any(p in ID_PIECES for p in ps):
        return True
    return any((a, b) in ID_PAIRS for a, b in zip(ps, ps[1:]))
