#!/usr/bin/env python3
"""Re-gate rule additions (STAGE 0, decided before any Stage-1 label is used).

T2 FIX (iteration-4 D14): the frozen exp8 suite labeller reads array-based Dijkstra (linear minimum scan over
unvisited nodes + a visited/settled set, no heap) as Bellman-Ford/SPFA or 'unknown'. Mechanism-level rule, applied
in BOTH the runtime and the AST path ahead of the bf_spfa decision: a single-source loop that SELECTS the
minimum-distance UNVISITED node by a linear scan and FINALISES each selected node once -> 'dijkstra'.
  SPFA = FIFO queue with re-insertion of improved nodes (deque/popleft/pop(0)/Queue) -> never matched;
  Bellman-Ford = repeated full edge sweeps with no selection step -> never matched;
  heap Dijkstra is already labelled by the frozen rules (heap present -> this rule does not fire).
The iteration-4 post-hoc regex rule (visited + `dist[a] < dist[b]` + no heapq/deque; 219 of 374 matches) is kept as
a sufficient condition so every program it matched is labelled 'dijkstra' (CPU test T3).

R6 EXTENDED LABEL: the frozen bench labeller already names the off-catalogue linear scan ('linear_scan'); the
structural audit promotes it to a named extended-catalogue label (eligible as a default) with a reference program
that passes the hidden tests (extensions/R6/linear_scan.py).
"""

from __future__ import annotations

import ast
import re

SETTLE_RE = re.compile(r"(visit|settled|done|processed|final|spt|used|seen|closed|explored|fixed|known|marked|"
                       r"permanent|unvisit|remaining|unseen|unprocessed|queue|candidates|nodes_left|left|todo|pending)",
                       re.I)
DIST_RE = re.compile(r"(dist|cost|d$|^d_|best|shortest|length|weight|lengths|distance)", re.I)
EXTENDED_LABELS = {"R6": ["linear_scan"]}


def _imports(tree: ast.AST) -> set[str]:
    out: set[str] = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            out |= {a.name for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.module:
            out.add(n.module)
            out |= {f"{n.module}.{a.name}" for a in n.names}
    return out


def _call_name(c: ast.Call) -> str:
    f = c.func
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        return f.attr
    return ""


def _names(node: ast.AST) -> set[str]:
    out = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Name):
            out.add(n.id)
        elif isinstance(n, ast.Attribute):
            out.add(n.attr)
    return out


def _is_dist_subscript(n: ast.AST) -> bool:
    if isinstance(n, ast.Subscript):
        base = n.value
        while isinstance(base, ast.Subscript):
            base = base.value
        return isinstance(base, ast.Name) and bool(DIST_RE.search(base.id))
    return False


def _selection(tree: ast.AST) -> str | None:
    """(a) min(<nodes>, key=<dist lookup>) or min((dist[v], v) ...); (b) a linear min-scan: inside a for-loop an
    `if ... dist[v] < best ...:` (left side a plain distance subscript, op < or <=; relaxations `dist[u] + w < dist[v]`
    and `nd < dist[v]` have a different left side) whose body assigns the selected node."""
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and _call_name(n) == "min":
            for kw in n.keywords:
                if kw.arg == "key":
                    kn = _names(kw.value)
                    has_dist = any(DIST_RE.search(x) for x in kn) or any(_is_dist_subscript(x) for x in ast.walk(kw.value))
                    if has_dist:
                        return "min(key=dist)"
            if n.args and isinstance(n.args[0], (ast.GeneratorExp, ast.ListComp)):
                elt = n.args[0].elt
                if isinstance(elt, ast.Tuple) and elt.elts and _is_dist_subscript(elt.elts[0]):
                    return "min((dist[v], v) for v in ...)"
    for loop in ast.walk(tree):
        if not isinstance(loop, ast.For):
            continue
        for iff in ast.walk(loop):
            if not isinstance(iff, ast.If):
                continue
            ok = False
            for c in ast.walk(iff.test):
                if isinstance(c, ast.Compare) and _is_dist_subscript(c.left) and len(c.ops) == 1 \
                        and isinstance(c.ops[0], (ast.Lt, ast.LtE)) \
                        and (isinstance(c.comparators[0], ast.Name) or _is_dist_subscript(c.comparators[0])):
                    ok = True
            if ok and any(isinstance(a, ast.Assign) for a in ast.walk(iff)):
                return "linear min-scan over nodes"
    return None


def _settle(tree: ast.AST) -> str | None:
    """Each selected node is finalised once: X[u] = True/1, or X.add/remove/discard(u) on a node collection."""
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Subscript) and isinstance(t.value, ast.Name) \
                        and isinstance(n.value, ast.Constant) and n.value.value in (True, 1):
                    return f"{t.value.id}[u] = True"
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name):
            if n.func.attr in ("add", "remove", "discard"):
                return f"{n.func.value.id}.{n.func.attr}(u)"
            if n.func.attr == "append" and SETTLE_RE.search(n.func.value.id) and \
                    re.search(r"(visit|settled|done|processed|final|spt)", n.func.value.id, re.I):
                return f"{n.func.value.id}.append(u)"
    return None


def t2_array_dijkstra(code: str | None) -> tuple[bool, str]:
    """True if the program is array-based Dijkstra (see module docstring). Returns (match, reason)."""
    if not code:
        return False, "no code"
    exp23 = bool(re.search(r"visited", code)) and bool(re.search(r"dist\[\w+\]\s*<\s*dist\[\w+\]", code)) \
        and "heapq" not in code and "deque" not in code
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError):
        return exp23, "exp23 regex rule (unparsable)" if exp23 else "parse error"
    imps = _imports(tree)
    calls = {_call_name(c) for c in ast.walk(tree) if isinstance(c, ast.Call)}
    heap = "heapq" in imps or bool(calls & {"heappush", "heappop", "heapify", "heapreplace", "PriorityQueue"})
    fifo = ("collections.deque" in imps or "deque" in calls or "popleft" in calls or "Queue" in calls
            or any(isinstance(c, ast.Call) and _call_name(c) == "pop" and c.args and isinstance(c.args[0], ast.Constant)
                   and c.args[0].value == 0 for c in ast.walk(tree)))
    if heap or fifo:
        return exp23, "exp23 regex rule" if exp23 else ("heap present" if heap else "FIFO queue present")
    sel = _selection(tree)
    st = _settle(tree)
    if sel and st:
        return True, f"selection: {sel}; finalise: {st}"
    if exp23:
        return True, "exp23 regex rule"
    return False, f"selection={sel}; finalise={st}"


def apply_t2(label: str | None, code: str | None) -> tuple[str | None, bool]:
    """Ahead of the bf_spfa decision: bf_spfa / unknown / inconsistent -> dijkstra when the structure matches."""
    if label in ("bf_spfa", "unknown", "inconsistent", None):
        ok, _ = t2_array_dijkstra(code)
        if ok:
            return "dijkstra", True
    return label, False
