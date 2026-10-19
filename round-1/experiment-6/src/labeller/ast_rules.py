#!/usr/bin/env python3
"""AST rules labeller (applied to code with docstrings and comments stripped). Returns (label|None, rule)."""

from __future__ import annotations

import ast
import re

DEPTH_PARAM = re.compile(r"depth|limit|bound|max_?d|remaining|budget|level|cutoff", re.I)
REV_NAME = re.compile(r"(^|_)(rev|reverse|radj|rgraph|backward|bwd|incoming|pred|transpose|inv)", re.I)
INQ_NAME = re.compile(r"in_?q(ueue)?|inqueue|queued|on_?queue|in_?que|inq", re.I)
BUCKET_NAME = re.compile(r"bucket", re.I)
HEUR_NAME = re.compile(r"heuristic|manhattan|euclid|hypot|^h$|estimate", re.I)


def strip_code(code: str) -> tuple[ast.Module | None, str]:
    """Parse, drop docstrings; ast.unparse drops comments."""
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError):
        return None, ""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
            b = node.body
            if b and isinstance(b[0], ast.Expr) and isinstance(getattr(b[0], "value", None), ast.Constant) and \
                    isinstance(b[0].value.value, str):
                node.body = b[1:] or [ast.Pass()]
    try:
        return tree, ast.unparse(tree)
    except (ValueError, RecursionError):
        return tree, code


def _name(n) -> str | None:
    if isinstance(n, ast.Name):
        return n.id
    if isinstance(n, ast.Attribute):
        return n.attr
    return None


def _call_name(c: ast.Call) -> str | None:
    return _name(c.func)


class Info:
    def __init__(self, tree: ast.Module):
        self.tree = tree
        self.imports: set[str] = set()
        self.calls: list[ast.Call] = []
        self.funcs: dict[str, ast.FunctionDef] = {}
        self.assign_targets: list[tuple[str, ast.AST]] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    self.imports.add(a.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                self.imports.add((node.module or "").split(".")[0])
                for a in node.names:
                    self.imports.add(a.name)
            elif isinstance(node, ast.Call):
                self.calls.append(node)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.funcs.setdefault(node.name, node)
            elif isinstance(node, ast.Assign):
                for t in node.targets:
                    for nm in _target_names(t):
                        self.assign_targets.append((nm, node.value))
            elif isinstance(node, ast.AnnAssign) and node.value is not None:
                for nm in _target_names(node.target):
                    self.assign_targets.append((nm, node.value))
        self.call_names = [_call_name(c) for c in self.calls]
        self.identifiers = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | \
            {a.arg for n in ast.walk(tree) if isinstance(n, ast.arguments) for a in n.args}
        solve = self.funcs.get("solve")
        self.params = [a.arg for a in solve.args.args] if solve else []

    def count_calls(self, name: str) -> int:
        return sum(1 for n in self.call_names if n == name)

    def method_calls(self, attr: str) -> list[ast.Call]:
        return [c for c in self.calls if isinstance(c.func, ast.Attribute) and c.func.attr == attr]

    def recursive_funcs(self) -> list[str]:
        out = []
        for nm, f in self.funcs.items():
            for n in ast.walk(f):
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == nm and n is not f:
                    out.append(nm)
                    break
        return out


def _target_names(t) -> list[str]:
    if isinstance(t, ast.Name):
        return [t.id]
    if isinstance(t, (ast.Tuple, ast.List)):
        return [x for e in t.elts for x in _target_names(e)]
    return []


def _contains_name(node, name: str) -> bool:
    return any(isinstance(n, ast.Name) and n.id == name for n in ast.walk(node))


def _loops(node) -> list[ast.AST]:
    return [n for n in ast.walk(node) if isinstance(n, (ast.For, ast.While))]


def has_manhattan(tree) -> bool:
    for n in ast.walk(tree):
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Add):
            l, r = n.left, n.right
            if isinstance(l, ast.Call) and isinstance(r, ast.Call) and _call_name(l) == "abs" and \
                    _call_name(r) == "abs":
                return True
        if isinstance(n, ast.Call) and _call_name(n) in ("hypot", "dist", "sqrt"):
            return True
        if isinstance(n, ast.FunctionDef) and HEUR_NAME.search(n.name):
            return True
        if isinstance(n, ast.Name) and HEUR_NAME.search(n.id) and n.id != "h":
            return True
    return False


def uses_heap(info: Info) -> bool:
    return "heapq" in info.imports or any(nm in ("heappush", "heappop", "heapify", "heappushpop", "heapreplace")
                                          for nm in info.call_names) or "PriorityQueue" in info.call_names


def fifo_ops(info: Info) -> dict:
    popleft = len(info.method_calls("popleft"))
    pop0 = sum(1 for c in info.method_calls("pop") if c.args and isinstance(c.args[0], ast.Constant)
               and c.args[0].value == 0)
    q_get = len(info.method_calls("get")) if ("Queue" in info.call_names or "SimpleQueue" in info.call_names) \
        else 0
    pop_noarg = sum(1 for c in info.method_calls("pop") if not c.args)
    n_deque = info.count_calls("deque") + info.count_calls("Queue") + info.count_calls("SimpleQueue")
    return dict(popleft=popleft, pop0=pop0, q_get=q_get, pop_noarg=pop_noarg, n_fifo_ctor=n_deque)


def goal_seeded(info: Info, goal_name: str | None) -> bool:
    """A frontier/visited structure constructed with the goal (deque([goal]), {goal}, {goal: None}, [goal])."""
    if not goal_name:
        return False
    for nm, val in info.assign_targets:
        if isinstance(val, ast.Call) and _call_name(val) in ("deque", "set", "Queue") and \
                any(_contains_name(a, goal_name) for a in val.args):
            return True
        if isinstance(val, ast.Set) and any(_contains_name(e, goal_name) for e in val.elts):
            return True
        if isinstance(val, ast.Dict) and any(k is not None and _contains_name(k, goal_name) for k in val.keys):
            return True
        if isinstance(val, ast.List) and any(_contains_name(e, goal_name) for e in val.elts) and \
                not any(_contains_name(e, info.params[1] if len(info.params) > 1 else "start") for e in val.elts):
            return True
    for c in info.method_calls("put") + info.method_calls("append"):
        if c.args and isinstance(c.args[0], ast.Name) and c.args[0].id == goal_name:
            # appending the goal itself is common in path reconstruction; only count queue puts
            if isinstance(c.func, ast.Attribute) and c.func.attr == "put":
                return True
    return False


def iddfs_pattern(info: Info) -> bool:
    rec = set(info.recursive_funcs())
    # (a) a depth-bounded function (recursive, or containing a stack loop) called in a loop with the loop variable
    bounded = set()
    for nm, f in info.funcs.items():
        params = [a.arg for a in f.args.args]
        if any(DEPTH_PARAM.search(p) for p in params) and (nm in rec or any(
                isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute) and c.func.attr == "pop"
                for c in ast.walk(f))):
            bounded.add(nm)
    for loop in _loops(info.tree):
        loop_vars = set()
        if isinstance(loop, ast.For):
            loop_vars |= set(_target_names(loop.target))
        for n in ast.walk(loop):
            if isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Name):
                loop_vars.add(n.target.id)
        for n in ast.walk(loop):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in bounded:
                if any(_contains_name(a, v) for a in list(n.args) + [k.value for k in n.keywords]
                       for v in loop_vars):
                    return True
    # (b) iterative: outer loop over a limit containing an inner while-loop that pops a stack and compares depth
    for outer in _loops(info.tree):
        if not isinstance(outer, ast.For):
            continue
        ov = set(_target_names(outer.target))
        if not ov or not any(DEPTH_PARAM.search(v) for v in ov):
            continue
        for inner in ast.walk(outer):
            if inner is outer or not isinstance(inner, ast.While):
                continue
            pops = [c for c in ast.walk(inner) if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
                    and c.func.attr == "pop" and not c.args]
            cmp = [c for c in ast.walk(inner) if isinstance(c, ast.Compare) and any(_contains_name(c, v)
                                                                                    for v in ov)]
            if pops and cmp:
                return True
    return False


def t1_ast(code: str) -> tuple[str | None, str]:
    tree, _ = strip_code(code)
    if tree is None:
        return None, "unparseable"
    info = Info(tree)
    goal_name = info.params[2] if len(info.params) >= 3 else "goal"
    if uses_heap(info):
        if has_manhattan(tree):
            return "astar_greedy", "A1:heap+heuristic"
        return "dijkstra_unit", "A2:heap,no heuristic"
    if iddfs_pattern(info):
        return "iddfs", "A3:loop over depth limit calling depth-bounded search"
    f = fifo_ops(info)
    fifo = f["popleft"] + f["pop0"] + f["q_get"] > 0
    if fifo:
        if goal_seeded(info, goal_name) and (f["n_fifo_ctor"] >= 2 or f["popleft"] + f["pop0"] >= 2):
            return "bidirectional_bfs", "A4:two FIFO frontiers (goal-seeded)"
        return "bfs", "A5:FIFO queue"
    if info.recursive_funcs() or f["pop_noarg"] > 0:
        return "dfs", "A6:recursion or stack pop()"
    return None, "A7:no rule"


def t2_ast(code: str) -> tuple[str | None, str]:
    tree, _ = strip_code(code)
    if tree is None:
        return None, "unparseable"
    info = Info(tree)
    edges_name = info.params[1] if len(info.params) >= 2 else "edges"
    if uses_heap(info):
        heap_args = {(_name(c.args[0]) or ast.unparse(c.args[0])) for c in info.calls
                     if _call_name(c) == "heappush" and c.args}
        n_pq = info.count_calls("PriorityQueue")
        rev = any(REV_NAME.search(nm) for nm, _ in info.assign_targets)
        # revision 2: require one loop that pops two different heaps (interleaved searches)
        interleaved = False
        for w in [x for x in ast.walk(tree) if isinstance(x, (ast.While, ast.For))]:
            popped = {(_name(c.args[0]) or ast.unparse(c.args[0])) for c in ast.walk(w)
                      if isinstance(c, ast.Call) and _call_name(c) == "heappop" and c.args}
            gets = sum(1 for c in ast.walk(w) if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
                       and c.func.attr == "get")
            if len(popped) >= 2 or (n_pq >= 2 and gets >= 2):
                interleaved = True
                break
        if interleaved and (len(heap_args) >= 2 or n_pq >= 2 or rev):
            return "bidirectional_dijkstra", "B1:one loop popping two heaps (rev2)"
        return "dijkstra", "B2:heap"
    # Floyd-Warshall: triple-nested for loops over range(...) whose innermost body adds and compares
    # (covers dist[i][k] + dist[k][j] and the row-hoisted form dik + dk[j])
    for f1 in [x for x in ast.walk(tree) if isinstance(x, ast.For) and isinstance(x.iter, ast.Call)
               and _call_name(x.iter) == "range"]:
        for f2 in [x for x in ast.walk(f1) if x is not f1 and isinstance(x, ast.For) and isinstance(x.iter, ast.Call)
                   and _call_name(x.iter) == "range"]:
            for f3 in [x for x in ast.walk(f2) if x is not f2 and isinstance(x, ast.For)
                       and isinstance(x.iter, ast.Call) and _call_name(x.iter) == "range"]:
                body = ast.Module(body=f3.body, type_ignores=[])
                if any(isinstance(x, ast.BinOp) and isinstance(x.op, ast.Add) for x in ast.walk(body)) and \
                        any(isinstance(x, (ast.Compare, ast.Call)) for x in ast.walk(body)):
                    return "floyd_warshall", "B3:triple range loops with add+compare"
    for n in ast.walk(tree):
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Add) and \
                isinstance(n.left, ast.Subscript) and isinstance(n.left.value, ast.Subscript) and \
                isinstance(n.right, ast.Subscript) and isinstance(n.right.value, ast.Subscript):
            depth_ok = False
            for f1 in ast.walk(tree):
                if isinstance(f1, ast.For):
                    for f2 in ast.walk(f1):
                        if f2 is not f1 and isinstance(f2, ast.For):
                            for f3 in ast.walk(f2):
                                if f3 is not f2 and isinstance(f3, ast.For):
                                    depth_ok = True
            if depth_ok:
                return "floyd_warshall", "B3:triple loop dist[i][k]+dist[k][j]"
    # Bellman-Ford: an outer loop containing a for-loop over the edge list; SPFA: deque + in-queue flag
    edge_aliases = {edges_name} | {nm for nm, v in info.assign_targets if isinstance(v, ast.Name) and v.id ==
                                   edges_name}
    for outer in _loops(tree):
        for inner in ast.walk(outer):
            if inner is not outer and isinstance(inner, ast.For) and isinstance(inner.iter, ast.Name) and \
                    inner.iter.id in edge_aliases:
                return "bellman_ford_spfa", "B4:rounds over all edges"
    f = fifo_ops(info)
    if (f["popleft"] + f["pop0"] + f["q_get"] > 0) and any(INQ_NAME.search(i) for i in info.identifiers):
        return "bellman_ford_spfa", "B4b:FIFO with in-queue flag"
    # revision 1: rounds over all nodes' adjacency lists (outer for-range/while containing for-in-for with a
    # relaxation test), and FIFO label-correcting loops that re-append a node after relaxing it
    for outer in _loops(tree):
        if isinstance(outer, ast.For) and not (isinstance(outer.iter, ast.Call) and _call_name(outer.iter) == "range"):
            continue
        for f1 in ast.walk(outer):
            if f1 is outer or not isinstance(f1, ast.For):
                continue
            for f2 in ast.walk(f1):
                if f2 is f1 or not isinstance(f2, ast.For):
                    continue
                for x in ast.walk(f2):
                    if isinstance(x, ast.If) and any(isinstance(y, ast.BinOp) and isinstance(y.op, ast.Add)
                                                     for y in ast.walk(x.test)) and isinstance(x.test, ast.Compare):
                        return "bellman_ford_spfa", "B4c:rounds over adjacency with relaxation (rev1)"
    if f["popleft"] + f["pop0"] + f["q_get"] > 0:
        for w in [x for x in ast.walk(tree) if isinstance(x, ast.While)]:
            for x in ast.walk(w):
                if isinstance(x, ast.If) and isinstance(x.test, ast.Compare) and \
                        any(isinstance(y, ast.BinOp) and isinstance(y.op, ast.Add) for y in ast.walk(x.test)) and \
                        any(isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute) and
                            c.func.attr in ("append", "put") for b in x.body for c in ast.walk(b)):
                    return "bellman_ford_spfa", "B4d:FIFO label-correcting relaxation (rev1)"
    if any(BUCKET_NAME.search(i) for i in info.identifiers):
        return "dial", "B5:buckets"
    for nm, v in info.assign_targets:
        if isinstance(v, ast.ListComp) and isinstance(v.elt, (ast.List, ast.Call)) and \
                (isinstance(v.elt, ast.List) and not v.elt.elts or _call_name(v.elt) in ("deque", "set", "list")):
            gens = v.generators
            if gens and isinstance(gens[0].iter, ast.Call) and _call_name(gens[0].iter) == "range" and \
                    any(isinstance(x, ast.BinOp) and isinstance(x.op, ast.Mult) or
                        (isinstance(x, ast.Call) and _call_name(x) in ("max", "sum")) for a in gens[0].iter.args
                        for x in ast.walk(a)):
                return "dial", "B5b:list of lists sized by distance range"
    return None, "B6:no rule"


def ast_label(code: str, task: str) -> tuple[str | None, str]:
    try:
        return t1_ast(code) if task == "T1" else t2_ast(code)
    except (RecursionError, ValueError, AttributeError, TypeError, IndexError) as e:
        return None, f"ast_error:{type(e).__name__}"


if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from common import REFS_DIR
    for f in sorted(REFS_DIR.glob("t*.py")):
        task = "T1" if f.name.startswith("t1") else "T2"
        print(f.name, "->", ast_label(f.read_text(), task))
