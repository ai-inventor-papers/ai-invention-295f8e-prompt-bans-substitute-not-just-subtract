#!/usr/bin/env python3
"""Static (AST) algorithm labels, independent of the runtime tracer.

Recursion versus iteration never changes a label. First matching rule wins:
  T1: iddfs > astar > dijkstra_unit > bidirectional_bfs > bfs > dfs > other
  T2: bidirectional_dijkstra > dijkstra (heap, or array/min-scan) > dial > floyd_warshall > bellman_ford_spfa > other
"""
from __future__ import annotations

import ast
import re

HEAP_FUNCS = {"heappush", "heappop", "heapify", "heappushpop", "heapreplace"}
LIMIT_PARAM = re.compile(r"depth|limit|max_?d|bound|maxd|lim\b|cutoff", re.I)


def _fname(call: ast.Call) -> str:
    f = call.func
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        return f.attr
    return ""


def _names_in(node: ast.AST) -> set[str]:
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}


def _is_abs_call(n: ast.AST) -> bool:
    return isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "abs"


def _loop_depth(node: ast.AST, depth: int = 0) -> int:
    best = depth
    for ch in ast.iter_child_nodes(node):
        d = depth + 1 if isinstance(ch, (ast.For, ast.AsyncFor)) else depth
        best = max(best, _loop_depth(ch, d))
    return best


def facts(code: str) -> dict:
    tree = ast.parse(code)
    f: dict = {"heap_calls": 0, "heap_targets": set(), "priority_queue": False, "deque": False, "popleft": False,
               "pop0": False, "pop_noarg": False, "appendleft": False, "queue_get": False, "lifo_queue": False,
               "fifo_queue": False, "recursive": set(), "manhattan": False, "identifiers": set(),
               "min_key": False, "relax_compare": False, "bucket_listcomp": False, "fw_pattern": False,
               "edges_loop_nested": False, "solve_params": [], "start_init": set(), "goal_init": set(),
               "iddfs_loop_call": False, "loop_depth": _loop_depth(tree)}
    funcs = {n.name: n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    if "solve" in funcs:
        f["solve_params"] = [a.arg for a in funcs["solve"].args.args]
    for n in ast.walk(tree):
        if isinstance(n, ast.Name):
            f["identifiers"].add(n.id.lower())
        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            f["identifiers"].add(n.name.lower())
            for a in n.args.args:
                f["identifiers"].add(a.arg.lower())
        elif isinstance(n, ast.Attribute):
            f["identifiers"].add(n.attr.lower())
        if isinstance(n, ast.Call):
            nm = _fname(n)
            if nm in HEAP_FUNCS:
                f["heap_calls"] += 1
                if n.args and nm in ("heappush", "heappop", "heapify", "heappushpop", "heapreplace"):
                    f["heap_targets"].add(ast.unparse(n.args[0]))
            elif nm == "PriorityQueue":
                f["priority_queue"] = True
            elif nm == "deque":
                f["deque"] = True
            elif nm == "popleft":
                f["popleft"] = True
            elif nm == "appendleft":
                f["appendleft"] = True
            elif nm == "pop" and isinstance(n.func, ast.Attribute):
                if len(n.args) == 1 and isinstance(n.args[0], ast.Constant) and n.args[0].value == 0:
                    f["pop0"] = True
                elif not n.args or (len(n.args) == 1 and isinstance(n.args[0], ast.UnaryOp)
                                    and isinstance(n.args[0].operand, ast.Constant) and n.args[0].operand.value == 1):
                    f["pop_noarg"] = True
            elif nm == "LifoQueue":
                f["lifo_queue"] = True
            elif nm in ("Queue", "SimpleQueue"):
                f["fifo_queue"] = True
            elif nm == "get" and isinstance(n.func, ast.Attribute) and not n.args:
                f["queue_get"] = True
            elif nm == "min" and any(k.arg == "key" for k in n.keywords):
                f["min_key"] = True
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Add):
            if _is_abs_call(n.left) and _is_abs_call(n.right):
                f["manhattan"] = True
            if (isinstance(n.left, ast.BinOp) and isinstance(n.left.op, ast.Add) and _is_abs_call(n.left.right)
                    and _is_abs_call(n.right)):
                f["manhattan"] = True
            l, r = n.left, n.right
            if (isinstance(l, ast.Subscript) and isinstance(l.value, ast.Subscript) and isinstance(r, ast.Subscript)
                    and isinstance(r.value, ast.Subscript)):
                if ast.unparse(l.slice) == ast.unparse(r.value.slice):
                    f["fw_pattern"] = True
        if isinstance(n, ast.Compare) and any(isinstance(o, (ast.Lt, ast.Gt, ast.LtE, ast.GtE)) for o in n.ops):
            sides = [n.left] + list(n.comparators)
            if any(isinstance(s, ast.BinOp) and isinstance(s.op, ast.Add) for s in sides):
                f["relax_compare"] = True
        if isinstance(n, ast.ListComp):
            elt = n.elt
            empty = (isinstance(elt, (ast.List, ast.Set)) and not getattr(elt, "elts", [1])) or (
                isinstance(elt, ast.Call) and _fname(elt) in ("set", "list", "deque") and not elt.args)
            if empty and n.generators:
                it = n.generators[0].iter
                if isinstance(it, ast.Call) and _fname(it) == "range" and any(
                        isinstance(x, ast.BinOp) and isinstance(x.op, ast.Mult) for a in it.args for x in ast.walk(a)):
                    f["bucket_listcomp"] = True
    # recursion: a function that calls itself
    for name, fn in funcs.items():
        for n in ast.walk(fn):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == name:
                f["recursive"].add(name)
                break
    # containers initialised with the start / goal parameter
    params = f["solve_params"]
    sname = params[1] if len(params) >= 3 else "start"
    gname = params[2] if len(params) >= 3 else "goal"
    for n in ast.walk(tree):
        if isinstance(n, (ast.Assign, ast.AnnAssign)) and n.value is not None:
            v = n.value
            kind = None
            if isinstance(v, ast.Call) and _fname(v) == "deque":
                kind = "deque"
            elif isinstance(v, (ast.Set, ast.Dict)):
                kind = "setdict"
            if kind:
                nm = _names_in(v)
                if sname in nm:
                    f["start_init"].add(kind)
                if gname in nm:
                    f["goal_init"].add(kind)
    # IDDFS: a depth-limited function called from an outer loop with the loop variable as an argument
    limited = {name for name, fn in funcs.items() if any(LIMIT_PARAM.search(a.arg) for a in fn.args.args)}
    for n in ast.walk(tree):
        if isinstance(n, (ast.For, ast.While)):
            loopvars = _names_in(n.target) if isinstance(n, ast.For) else set()
            for m in ast.walk(n):
                if m is n:
                    continue
                if isinstance(m, ast.Call) and isinstance(m.func, ast.Name) and m.func.id in limited:
                    argnames = set().union(*[_names_in(a) for a in m.args]) if m.args else set()
                    argnames |= set().union(*[_names_in(k.value) for k in m.keywords]) if m.keywords else set()
                    if (loopvars & argnames) or isinstance(n, ast.While):
                        f["iddfs_loop_call"] = True
    # Bellman-Ford: a loop over the edge list nested inside another loop
    eparam = params[1] if len(params) >= 4 else "edges"
    for n in ast.walk(tree):
        if isinstance(n, (ast.For, ast.While)):
            for m in ast.walk(n):
                if m is not n and isinstance(m, ast.For):
                    it = m.iter
                    itn = ast.unparse(it)
                    if itn == eparam or re.fullmatch(r"[A-Za-z_]*edge[s]?[A-Za-z_]*", itn or "") and "adj" not in itn:
                        f["edges_loop_nested"] = True
    # array Dijkstra: an argmin scan (if X[i] < best: u = i; best = X[i]) nested inside an outer loop
    f["argmin_loop"] = False
    f["bf_adjacency"] = False
    for outer in ast.walk(tree):
        if not isinstance(outer, (ast.For, ast.While)):
            continue
        for inner in ast.walk(outer):
            if inner is outer or not isinstance(inner, ast.For):
                continue
            for node in ast.walk(inner):
                if isinstance(node, ast.If):
                    cmps = [c for c in ast.walk(node.test) if isinstance(c, ast.Compare)
                            and any(isinstance(o, (ast.Lt, ast.LtE, ast.Gt, ast.GtE)) for o in c.ops)]
                    named = [a for a in node.body if isinstance(a, ast.Assign)
                             and all(isinstance(tg, ast.Name) for tg in a.targets)]
                    for c in cmps:
                        sides = [c.left] + list(c.comparators)
                        if (any(isinstance(x, ast.Subscript) for x in sides) and any(isinstance(x, ast.Name)
                                                                                   for x in sides) and len(named) >= 1):
                            f["argmin_loop"] = True
            # Bellman-Ford over adjacency: outer loop > for over nodes > for over adjacency with relaxation
            for inner2 in ast.walk(inner):
                if inner2 is inner or not isinstance(inner2, ast.For):
                    continue
                if isinstance(inner2.iter, ast.Subscript):
                    for node in ast.walk(inner2):
                        if isinstance(node, ast.Compare) and any(isinstance(x, ast.BinOp) and isinstance(x.op, ast.Add)
                                                                 for x in [node.left] + list(node.comparators)):
                            f["bf_adjacency"] = True
    for k in ("heap_targets", "recursive", "identifiers", "start_init", "goal_init"):
        f[k] = sorted(f[k])
    return f


def _has_ident(f: dict, *subs: str) -> bool:
    return any(any(s in i for s in subs) for i in f["identifiers"])


def label_t1(f: dict) -> str:
    heap = f["heap_calls"] > 0 or f["priority_queue"]
    if _has_ident(f, "iddfs", "deepening", "depth_limited", "dls") or f["iddfs_loop_call"]:
        return "iddfs"
    if heap and f["manhattan"]:
        return "astar"
    if heap:
        return "dijkstra_unit"
    bidir_ident = _has_ident(f, "bidir", "bi_dir") or (_has_ident(f, "forward") and _has_ident(f, "backward"))
    if (f["start_init"] and f["goal_init"]) or bidir_ident:
        return "bidirectional_bfs"
    if f["popleft"] or f["pop0"] or (f["fifo_queue"] and f["queue_get"]):
        return "bfs"
    if f["pop_noarg"] or f["recursive"] or f["lifo_queue"]:
        return "dfs"
    return "other"


def label_t2(f: dict) -> str:
    heap = f["heap_calls"] > 0 or f["priority_queue"]
    n_heaps = len(f["heap_targets"])
    rev = _has_ident(f, "rev", "backward", "radj", "bwd", "reverse")
    if heap and (n_heaps >= 2 and (rev or _has_ident(f, "mu", "meet", "best"))):
        return "bidirectional_dijkstra"
    if heap and _has_ident(f, "bidir", "bi_dir"):
        return "bidirectional_dijkstra"
    if heap:
        return "dijkstra"
    if f["bucket_listcomp"] or _has_ident(f, "bucket"):
        return "dial"
    if f["fw_pattern"] and f["loop_depth"] >= 3:
        return "floyd_warshall"
    if (f["min_key"] or f.get("argmin_loop")) and not f["edges_loop_nested"]:
        return "dijkstra"
    if f["edges_loop_nested"] or f.get("bf_adjacency"):
        return "bellman_ford_spfa"
    if (f["deque"] or f["fifo_queue"] or f["pop0"] or f["popleft"]) and f["relax_compare"]:
        return "bellman_ford_spfa"
    return "other"


def ast_label(task: str, code: str) -> dict:
    try:
        f = facts(code)
    except (SyntaxError, ValueError, RecursionError) as e:
        return {"label": "other", "facts": {"parse_error": repr(e)[:200]}}
    lab = label_t1(f) if task == "T1" else label_t2(f)
    small = {k: v for k, v in f.items() if k != "identifiers"}
    return {"label": lab, "facts": small}
