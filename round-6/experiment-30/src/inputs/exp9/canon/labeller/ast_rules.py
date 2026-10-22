#!/usr/bin/env python3
"""5b AST rules: a static labeller independent of the runtime tracer.

Comments are invisible to ast; docstrings and other bare string expressions are dropped before any name scan.
Rules map features to one catalogue mode or 'unknown', with a short reason string.
"""

from __future__ import annotations

import ast
import re
from typing import Any

DEPTH_RE = re.compile(r"(depth|limit|bound|max_?d|maxd|lim\b|level|remaining|budget|deep)", re.I)
DIR_PAIRS = [("fwd", "bwd"), ("forward", "backward"), ("front", "back"), ("start", "goal"), ("start", "end"),
             ("src", "dst"), ("source", "target"), ("begin", "end"), ("from_start", "from_goal"), ("_s", "_g"),
             ("_s", "_t"), ("left", "right"), ("_f", "_b"), ("1", "2"), ("_a", "_b"), ("top", "bottom")]
CONTAINER_WORDS = ("visited", "seen", "parent", "parents", "prev", "frontier", "queue", "q", "dist", "came_from",
                   "pq", "heap", "open", "closed", "explored", "pred", "front", "level", "border", "fringe")
HEUR_RE = re.compile(r"(heuristic|manhattan|f_?score|h_?score|g_?score|astar|a_star|best_?first|greedy|\bh\b)", re.I)
BIDIR_WORD_RE = re.compile(r"(bidirect|bi_?bfs|bibfs|bi_?dijkstra|bidijkstra|meet|intersect|bi_?search)", re.I)
IDDFS_WORD_RE = re.compile(r"(iddfs|iterative_?deepening|deepening|depth_?limited|\bdls\b|_dls|dls_)", re.I)
INQUEUE_RE = re.compile(r"(in_?queue|inq|in_?q\b|on_?queue|queued|in_?deque|is_?in_?queue)", re.I)


class _DocStripper(ast.NodeTransformer):
    def visit_Expr(self, node: ast.Expr):
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            return None
        return self.generic_visit(node)


def _parse(code: str) -> ast.AST | None:
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError):
        return None
    return _DocStripper().visit(tree)


def _identifiers(tree: ast.AST) -> set[str]:
    out: set[str] = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Name):
            out.add(n.id)
        elif isinstance(n, ast.arg):
            out.add(n.arg)
        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out.add(n.name)
        elif isinstance(n, ast.Attribute):
            out.add(n.attr)
        elif isinstance(n, ast.alias):
            out.add(n.asname or n.name)
    return out


def _call_name(call: ast.Call) -> str:
    f = call.func
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        base = f.value
        b = base.id if isinstance(base, ast.Name) else (base.attr if isinstance(base, ast.Attribute) else "")
        return f"{b}.{f.attr}"
    return ""


def _is_manhattan(node: ast.AST) -> bool:
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        def is_abs(x):
            return isinstance(x, ast.Call) and isinstance(x.func, ast.Name) and x.func.id == "abs"
        return is_abs(node.left) and is_abs(node.right) or (_is_manhattan(node.left) and is_abs(node.right))
    return False


def _subscript_chain(node: ast.AST) -> list[str] | None:
    """dist[i][k] -> ['dist', 'i', 'k'] (indices as names when simple)."""
    idx = []
    while isinstance(node, ast.Subscript):
        sl = node.slice
        idx.append(sl.id if isinstance(sl, ast.Name) else ast.dump(sl))
        node = node.value
    if isinstance(node, ast.Name) and idx:
        return [node.id] + idx[::-1]
    return None


def _floyd_pattern(tree: ast.AST) -> bool:
    """X[i][k] + X[k][j] (or X[i][k] + X[k][j] inside min) in a depth-3 loop nest."""
    for n in ast.walk(tree):
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Add):
            a, b = _subscript_chain(n.left), _subscript_chain(n.right)
            if a and b and len(a) == 3 and len(b) == 3 and a[0] == b[0] and a[2] == b[1] and a[1] != b[2]:
                return True
    return False


def _loop_depth_max(tree: ast.AST) -> int:
    best = 0

    def rec(node, d):
        nonlocal best
        for ch in ast.iter_child_nodes(node):
            if isinstance(ch, (ast.For, ast.While)):
                best = max(best, d + 1)
                rec(ch, d + 1)
            elif isinstance(ch, ast.comprehension):
                rec(ch, d)
            else:
                rec(ch, d)

    rec(tree, 0)
    return best


def _self_recursive(tree: ast.AST) -> list[str]:
    rec = []
    for fn in ast.walk(tree):
        if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for n in ast.walk(fn):
                if n is fn:
                    continue
                if isinstance(n, ast.Call):
                    f = n.func
                    if (isinstance(f, ast.Name) and f.id == fn.name) or (isinstance(f, ast.Attribute)
                                                                       and f.attr == fn.name):
                        rec.append(fn.name)
                        break
    return rec


def _iddfs_structure(tree: ast.AST, rec_funcs: list[str], funcs: dict[str, ast.FunctionDef]) -> bool:
    """An outer loop that repeatedly calls a (recursive or stack-based) search with a depth-like argument."""
    stack_funcs = set(rec_funcs)
    for name, fn in funcs.items():
        for n in ast.walk(fn):
            if isinstance(n, ast.While):
                stack_funcs.add(name)
                break
    for loop in ast.walk(tree):
        if not isinstance(loop, (ast.For, ast.While)):
            continue
        loop_vars = set()
        if isinstance(loop, ast.For):
            for t in ast.walk(loop.target):
                if isinstance(t, ast.Name):
                    loop_vars.add(t.id)
        for n in ast.walk(loop):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in stack_funcs:
                fn = funcs.get(n.func.id)
                if fn is None or any(isinstance(a, ast.For) and a is loop for a in ast.walk(fn)):
                    continue
                arg_names = {a.id for a in n.args if isinstance(a, ast.Name)}
                arg_names |= {k.value.id for k in n.keywords if isinstance(k.value, ast.Name)}
                params = {a.arg for a in fn.args.args}
                if (arg_names & loop_vars and (any(DEPTH_RE.search(v) for v in arg_names & loop_vars)
                                               or isinstance(loop, ast.For))) or \
                        (any(DEPTH_RE.search(p) for p in params) and any(DEPTH_RE.search(v) for v in arg_names)):
                    return True
    return False


def _bidir_names(idents: set[str]) -> list[str]:
    low = {i.lower() for i in idents}
    hits = []
    for a, b in DIR_PAIRS:
        for w in CONTAINER_WORDS:
            forms_a = {f"{w}_{a}".replace("__", "_"), f"{a}_{w}".replace("__", "_"), f"{w}{a}", f"{a}{w}"}
            forms_b = {f"{w}_{b}".replace("__", "_"), f"{b}_{w}".replace("__", "_"), f"{w}{b}", f"{b}{w}"}
            if low & forms_a and low & forms_b:
                hits.append(f"{w}:{a}/{b}")
    return hits


def features(code: str, task: str) -> dict[str, Any]:
    tree = _parse(code)
    if tree is None:
        return {"parse_error": True}
    idents = _identifiers(tree)
    joined = " ".join(sorted(idents))
    calls = [_call_name(n) for n in ast.walk(tree) if isinstance(n, ast.Call)]
    imports = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            imports |= {a.name for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.module:
            imports.add(n.module)
            imports |= {f"{n.module}.{a.name}" for a in n.names}
    funcs = {n.name: n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    pop0 = popnoarg = 0
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "pop":
            if not n.args:
                popnoarg += 1
            elif isinstance(n.args[0], ast.Constant) and n.args[0].value == 0:
                pop0 += 1
    heap_calls = [c for c in calls if c.split(".")[-1] in ("heappush", "heappop", "heapify", "heapreplace",
                                                            "heappushpop")]
    heappop_targets = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and _call_name(n).split(".")[-1] in ("heappop", "heappush") and n.args:
            a0 = n.args[0]
            heappop_targets.add(ast.dump(a0))
    f = {
        "parse_error": False,
        "uses_heap": bool(heap_calls) or "heapq" in imports,
        "heap_calls": len(heap_calls),
        "n_heap_targets": len(heappop_targets),
        "priority_queue": any("PriorityQueue" in c for c in calls) or "queue.PriorityQueue" in imports,
        "deque": "collections.deque" in imports or any(c in ("deque", "collections.deque") for c in calls),
        "popleft": sum(1 for c in calls if c.endswith(".popleft")),
        "pop0": pop0,
        "pop_noarg": popnoarg,
        "fifo_queue": any(c in ("Queue", "queue.Queue", "SimpleQueue", "queue.SimpleQueue") for c in calls),
        "lifo_queue": any(c in ("LifoQueue", "queue.LifoQueue") for c in calls),
        "insert0": sum(1 for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                       and n.func.attr == "insert" and n.args and isinstance(n.args[0], ast.Constant)
                       and n.args[0].value == 0),
        "appendleft": sum(1 for c in calls if c.endswith(".appendleft")),
        "self_recursive": _self_recursive(tree),
        "manhattan": any(_is_manhattan(n) for n in ast.walk(tree)),
        "heuristic_names": bool(HEUR_RE.search(joined)),
        "bidir_names": _bidir_names(idents),
        "bidir_words": bool(BIDIR_WORD_RE.search(joined)),
        "iddfs_words": bool(IDDFS_WORD_RE.search(joined)),
        "floyd_pattern": _floyd_pattern(tree),
        "loop_depth": _loop_depth_max(tree),
        "bucket_words": bool(re.search(r"bucket|dial", joined, re.I)),
        "inqueue_words": bool(INQUEUE_RE.search(joined)),
        "spfa_bellman_words": bool(re.search(r"spfa|bellman", joined, re.I)),
        "frontier_lists": bool(re.search(r"(next_?(level|frontier|layer|queue|q)|new_?(frontier|level|layer)"
                                         r"|current_?(level|layer|frontier)|frontier)", joined, re.I)),
    }
    f["iddfs_structure"] = _iddfs_structure(tree, f["self_recursive"], funcs) or _inline_iddfs(tree)
    f["edge_pass_loop"] = _edge_pass_loop(tree)
    low = {i.lower() for i in idents}
    f["bare_dir_pairs"] = [f"{a}/{b}" for a, b in (("forward", "backward"), ("fwd", "bwd"), ("front", "back"))
                           if a in low and b in low]
    f["reverse_graph"] = bool(re.search(r"\b(rev|reverse|reversed_graph|radj|rgraph|rev_adj|radj_list|in_adj|"
                                        r"incoming|backward|bwd|graph_rev|adj_rev|rev_graph)\b", joined, re.I))
    f["triple_range_nest"] = _triple_range_nest(tree)
    return f


def _is_range_loop(n: ast.AST) -> bool:
    return isinstance(n, ast.For) and isinstance(n.iter, ast.Call) and _call_name(n.iter) == "range"


def _triple_range_nest(tree: ast.AST) -> bool:
    for a in ast.walk(tree):
        if not _is_range_loop(a):
            continue
        for b in ast.walk(a):
            if b is a or not _is_range_loop(b):
                continue
            for c in ast.walk(b):
                if c is b or not _is_range_loop(c):
                    continue
                names = [x.target.id for x in (a, b, c) if isinstance(x.target, ast.Name)]
                if len(set(names)) == 3:
                    return True
    return False


def _inline_iddfs(tree: ast.AST) -> bool:
    """Outer loop over a depth-like variable containing an inner stack loop that compares against it."""
    for outer in ast.walk(tree):
        if not isinstance(outer, (ast.For, ast.While)):
            continue
        if isinstance(outer, ast.For):
            dvars = {t.id for t in ast.walk(outer.target) if isinstance(t, ast.Name) and DEPTH_RE.search(t.id)}
        else:
            dvars = {t.id for t in ast.walk(outer.test) if isinstance(t, ast.Name) and DEPTH_RE.search(t.id)}
            dvars |= {t.target.id for t in ast.walk(outer) if isinstance(t, ast.AugAssign)
                      and isinstance(t.target, ast.Name) and DEPTH_RE.search(t.target.id)}
        if not dvars:
            continue
        for inner in ast.walk(outer):
            if inner is outer or not isinstance(inner, ast.While):
                continue
            has_pop = any(isinstance(x, ast.Call) and isinstance(x.func, ast.Attribute) and x.func.attr == "pop"
                          for x in ast.walk(inner))
            cmp_depth = any(isinstance(x, ast.Compare) and any(isinstance(y, ast.Name) and y.id in dvars
                                                               for y in ast.walk(x)) for x in ast.walk(inner))
            if has_pop and cmp_depth:
                return True
    return False


def _edge_pass_loop(tree: ast.AST) -> bool:
    """Bellman-Ford: a loop (for/while) whose body contains a for-loop over the edges list with a relaxation."""
    for outer in ast.walk(tree):
        if not isinstance(outer, (ast.For, ast.While)):
            continue
        for inner in ast.walk(outer):
            if inner is outer or not isinstance(inner, ast.For):
                continue
            it = inner.iter
            name = it.id if isinstance(it, ast.Name) else (_call_name(it) if isinstance(it, ast.Call) else "")
            targets = [t.id for t in ast.walk(inner.target) if isinstance(t, ast.Name)]
            if ("edge" in name.lower() or len(targets) == 3) and any(isinstance(x, ast.Compare) or
                                                                     (isinstance(x, ast.Call) and _call_name(x) == "min")
                                                                     for x in ast.walk(inner)):
                return True
    return False


def label(code: str, task: str) -> tuple[str, str, dict[str, Any]]:
    f = features(code, task)
    if f.get("parse_error"):
        return "unknown", "parse error", f
    heapish = f["uses_heap"] and f["heap_calls"] > 0 or f["priority_queue"]
    fifo = f["popleft"] > 0 or f["pop0"] > 0 or f["fifo_queue"] or (f["insert0"] > 0 and f["pop_noarg"] > 0)
    lifo = (f["pop_noarg"] > 0 and f["insert0"] == 0) or f["lifo_queue"]
    bidir = bool(f["bidir_names"]) or f["bidir_words"] or (f["n_heap_targets"] >= 2 and task == "t2")
    if task == "t1":
        if bidir or f["bare_dir_pairs"]:
            return ("other", "bidirectional with a heap (bidirectional A*/Dijkstra)", f) if heapish else \
                ("bibfs", "two direction-paired frontiers", f)
        if heapish:
            if f["manhattan"] or f["heuristic_names"]:
                return "astar_gbfs", "heap + Manhattan/heuristic", f
            return "dijkstra", "heap without heuristic", f
        if f["iddfs_words"] or f["iddfs_structure"]:
            return "iddfs", "outer loop over increasing depth limit calling a depth-limited search", f
        if fifo:
            return "bfs", "FIFO queue (popleft/pop(0)/Queue)", f
        if lifo or f["self_recursive"]:
            return "dfs", "LIFO stack or self-recursion", f
        if f["frontier_lists"]:
            return "bfs", "level-by-level frontier lists", f
        return "unknown", "no rule fired", f
    # t2
    if (f["floyd_pattern"] and f["loop_depth"] >= 3) or (f["triple_range_nest"] and not heapish):
        return "floyd", "dist[i][k] + dist[k][j] / triple range loop nest", f
    if heapish and (bidir or f["bare_dir_pairs"] or f["reverse_graph"]):
        return "bidijkstra", "two direction-paired heaps", f
    if f["bucket_words"]:
        return "dial", "bucket queue indexed by distance", f
    if heapish:
        return "dijkstra", "binary heap of tentative distances", f
    if f["edge_pass_loop"] or f["spfa_bellman_words"] or (fifo and f["inqueue_words"]):
        return "bf_spfa", "repeated relaxation over edges / FIFO label-correcting queue", f
    if fifo:
        return "bf_spfa", "FIFO queue with relaxation (label-correcting)", f
    return "unknown", "no rule fired", f
