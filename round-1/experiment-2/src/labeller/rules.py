#!/usr/bin/env python3
"""Labeller rules: (a) runtime-trace classifier (primary) and (b) AST rules (secondary).

Both return (label | None, confident: bool, evidence: dict). A None label means the rule set could not
decide; the combination step then sends the program to the blind LLM judge.
"""
from __future__ import annotations

import ast
import io
import sys
import tokenize
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tasks"))
from tasklib import bfs_dist, probes  # noqa: E402

# ------------------------------------------------------------------------------------------ helpers


def _is_int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def find_cell(item, R: int, C: int):
    """Find an (r, c) grid cell inside a recorded (json-ified) container item."""
    def is_cell(x):
        return isinstance(x, list) and len(x) == 2 and _is_int(x[0]) and _is_int(x[1]) and 0 <= x[0] < R and 0 <= x[1] < C

    if is_cell(item):
        return tuple(item)
    if isinstance(item, list):
        # (r, c, d) style triples
        if len(item) >= 3 and _is_int(item[0]) and _is_int(item[1]) and all(_num(v) for v in item[:3]) and \
                0 <= item[0] < R and 0 <= item[1] < C and not any(isinstance(v, list) for v in item):
            return (item[0], item[1])
        for sub in item:
            if is_cell(sub):
                return tuple(sub)
        for sub in item:  # nested: path lists -> last cell
            if isinstance(sub, list) and sub and all(is_cell(s) for s in sub if s != "..."):
                cells = [s for s in sub if s != "..."]
                if cells:
                    return tuple(cells[-1])
    return None


def find_node(item, n: int):
    if _is_int(item) and 0 <= item < n:
        return item
    if isinstance(item, list):
        ints = [v for v in item if _is_int(v)]
        # (dist, node) or (dist, node, ...) -> the node is usually item[1]
        if len(item) >= 2 and _is_int(item[1]) and 0 <= item[1] < n:
            return item[1]
        if ints and 0 <= ints[-1] < n:
            return ints[-1]
    return None


def first_prio(item):
    if _num(item):
        return float(item)
    if isinstance(item, list) and item and _num(item[0]):
        return float(item[0])
    return None


# ------------------------------------------------------------------------------------------ runtime rules


def runtime_label(task: str, trace: dict) -> tuple[str | None, bool, dict]:
    if not trace or not trace.get("ok") or trace.get("load_error"):
        return None, False, {"reason": "trace_failed", "detail": str(trace.get("load_error") or trace.get("harness_error"))[:200]}
    prs = probes(task)
    pres = trace.get("probes", [])
    if task == "t1":
        return _runtime_t1(prs, pres)
    return _runtime_t2(prs, pres)


def _pops(pr: dict, kinds: str) -> list[list]:
    """Popped items grouped per structure; kinds 'fifo' or 'lifo'."""
    groups = []
    for d in pr.get("deques", []):
        side = "L" if kinds == "fifo" else "R"
        items = [it for s, it in d["popped"] if s == side]
        if items:
            groups.append(items)
    for l in pr.get("lists", []):
        side = "F" if kinds == "fifo" else "B"
        items = [it for s, it in l["popped"] if s == side]
        if items:
            groups.append(items)
    for q in pr.get("queues", []):
        if (q["kind"] == "fifo" and kinds == "fifo") or (q["kind"] == "lifo" and kinds == "lifo"):
            if q["popped"]:
                groups.append(q["popped"])
    return groups


def _runtime_t1(prs, pres) -> tuple[str | None, bool, dict]:
    ev: dict = {}
    heap_rows = []
    n_heaps_max = 0
    fifo_n = lifo_n = 0
    fifo_groups_max = 0
    start_reexp = 0
    bidir_early = False
    max_depth = 0
    for spec, pr in zip(prs, pres):
        if pr.get("error"):
            ev.setdefault("probe_errors", []).append(pr["error"])
            continue
        grid, start, goal = spec["args"]
        R, C = len(grid), len(grid[0])
        dist = bfs_dist(grid, tuple(start))
        heaps = [h for h in pr["heaps"] if len(h["pushes"]) >= 2]
        pq = [q for q in pr["queues"] if q["kind"] == "prio" and len(q["put"]) >= 2]
        n_heaps_max = max(n_heaps_max, len(heaps) + len(pq))
        for h in heaps + [{"pushes": q["put"]} for q in pq]:
            for it in h["pushes"]:
                p = first_prio(it)
                cell = find_cell(it[1:] if isinstance(it, list) else it, R, C)
                if p is None or cell is None or cell not in dist:
                    continue
                g = dist[cell]
                hh = abs(cell[0] - goal[0]) + abs(cell[1] - goal[1])
                heap_rows.append((p, g, hh, spec["name"]))
        fg = _pops(pr, "fifo")
        lg = _pops(pr, "lifo")
        fifo_n += sum(len(g) for g in fg)
        lifo_n += sum(len(g) for g in lg)
        fifo_groups_max = max(fifo_groups_max, sum(1 for g in fg if len(g) >= 2))
        max_depth = max(max_depth, pr.get("max_depth", 0))
        if spec["name"].startswith("T1-P3"):
            # start re-expansions: recursive calls with the start cell, or stack pops of the start cell
            pops_start = 0
            for g in lg + fg:
                for it in g:
                    if find_cell(it, R, C) == tuple(start):
                        pops_start += 1
            start_reexp = max(pr.get("start_calls", 0), pops_start)
            # bidirectional: one of the first 6 FIFO pops lies within 2 steps of the goal
            first = []
            for g in fg:
                first.extend(g[:6])
            for it in first:
                cell = find_cell(it, R, C)
                if cell is not None and abs(cell[0] - goal[0]) + abs(cell[1] - goal[1]) <= 2 and \
                        abs(cell[0] - start[0]) + abs(cell[1] - start[1]) > 4:
                    bidir_early = True
    sorts = max((pr.get("sorts", 0) for pr in pres if not pr.get("error")), default=0)
    if sorts >= 3:
        return None, False, ev | {"reason": "sorted_list_queue", "sorts": sorts}
    ev.update({"heap_pushes": len(heap_rows), "n_heaps_max": n_heaps_max, "fifo_pops": fifo_n, "lifo_pops": lifo_n,
               "fifo_groups_max": fifo_groups_max, "start_reexp": start_reexp, "bidir_early": bidir_early,
               "max_depth": max_depth})
    if len(heap_rows) >= 8:
        P = np.array([r[0] for r in heap_rows], float)
        G = np.array([r[1] for r in heap_rows], float)
        H = np.array([r[2] for r in heap_rows], float)
        X = np.stack([G, H, np.ones_like(G)], 1)
        coef, *_ = np.linalg.lstsq(X, P, rcond=None)
        pred = X @ coef
        ss = float(np.sum((P - P.mean()) ** 2))
        r2 = 1.0 - float(np.sum((P - pred) ** 2)) / ss if ss > 1e-9 else 0.0
        a, b = float(coef[0]), float(coef[1])
        ev.update({"coef_g": round(a, 3), "coef_h": round(b, 3), "r2": round(r2, 3)})
        if n_heaps_max >= 2:
            return None, False, ev | {"reason": "two_heaps_t1"}
        if b > 0.4 and r2 >= 0.8:
            return "astar", r2 >= 0.9, ev
        if a > 0.5 and abs(b) < 0.25 and r2 >= 0.8:
            return "dijkstra_unit", r2 >= 0.9, ev
        return None, False, ev | {"reason": "heap_unexplained"}
    if fifo_n >= 5 and fifo_n >= lifo_n:
        if fifo_groups_max >= 2 or bidir_early:
            return "bidir_bfs", True, ev
        return "bfs", True, ev
    if lifo_n >= 5 or max_depth >= 6:
        if start_reexp >= 5:
            return "iddfs", True, ev
        return "dfs", True, ev
    return None, False, ev | {"reason": "no_structure_seen"}


def _runtime_t2(prs, pres) -> tuple[str | None, bool, dict]:
    ev: dict = {}
    n_heaps_max = 0
    fifo_reinsert = False
    fifo_n = 0
    floyd_like = False
    bucket_lists = 0
    edge_sweeps = False
    sorts = 0
    min_sel = False
    for spec, pr in zip(prs, pres):
        if pr.get("error"):
            ev.setdefault("probe_errors", []).append(pr["error"])
            continue
        n, edges, s, t = spec["args"]
        heaps = [h for h in pr["heaps"] if len(h["pushes"]) + len(h["pops"]) >= 2]
        pq = [q for q in pr["queues"] if q["kind"] == "prio" and len(q["put"]) >= 2]
        n_heaps_max = max(n_heaps_max, len(heaps) + len(pq))
        for g in _pops(pr, "fifo"):
            fifo_n += len(g)
            nodes = [find_node(it, n) for it in g]
            cnt = Counter(v for v in nodes if v is not None)
            if cnt and max(cnt.values()) >= 2:
                fifo_reinsert = True
        if pr.get("max_line_count", 0) >= 0.8 * n ** 3:
            floyd_like = True
        bucket_lists = max(bucket_lists, sum(1 for l in pr.get("lists", []) if l["back"] + l["front"] >= 1))
        if pr.get("max_line_count", 0) >= 2 * len(edges) and not heaps:
            edge_sweeps = True
        sorts = max(sorts, pr.get("sorts", 0))
        if pr.get("mins", 0) >= n // 2:
            min_sel = True
    ev.update({"n_heaps_max": n_heaps_max, "fifo_pops": fifo_n, "fifo_reinsert": fifo_reinsert,
               "floyd_like": floyd_like, "bucket_lists": bucket_lists, "edge_sweeps": edge_sweeps, "sorts": sorts,
               "min_select": min_sel})
    if n_heaps_max >= 4:  # many small heaps = heaps used as distance buckets -> let the judge decide
        return None, False, ev | {"reason": "many_heaps"}
    if n_heaps_max >= 2:
        return "bidir_dijkstra", True, ev
    if n_heaps_max == 1:
        return "dijkstra", True, ev
    if floyd_like:
        return "floyd_warshall", True, ev
    if sorts >= 3:
        return "dijkstra", True, ev
    if min_sel and fifo_n < 5 and bucket_lists < 5:
        return "dijkstra", False, ev
    if bucket_lists >= 5:
        return "dial", True, ev
    if fifo_n >= 5 and fifo_reinsert:
        return "bellman_ford_spfa", True, ev
    if fifo_n >= 5:
        return "bellman_ford_spfa", False, ev
    if edge_sweeps:
        return "bellman_ford_spfa", False, ev
    return None, False, ev | {"reason": "no_structure_seen"}


# ------------------------------------------------------------------------------------------ AST rules


class _Feat(ast.NodeVisitor):
    def __init__(self):
        self.names = Counter()
        self.attrs = Counter()
        self.calls = Counter()
        self.pop0 = 0
        self.pop_plain = 0
        self.popleft = 0
        self.min_key = 0
        self.funcs: dict[str, ast.FunctionDef] = {}
        self.recursive: set[str] = set()
        self.manhattan = False
        self.max_for_depth = 0
        self.range_triple = False
        self.edge_sweep = False
        self.bucket_lists = False
        self.depth_param = False
        self.two_sided = False
        self.reverse_adj = False
        self._cur_func: list[str] = []
        self._for_stack: list[ast.For] = []

    def visit_FunctionDef(self, node):
        self.funcs[node.name] = node
        self._cur_func.append(node.name)
        for a in node.args.args:
            if any(k in a.arg.lower() for k in ("depth", "limit", "bound", "max_d")):
                self.depth_param = True
        self.generic_visit(node)
        self._cur_func.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Name(self, node):
        self.names[node.id] += 1
        self.generic_visit(node)

    def visit_Attribute(self, node):
        self.attrs[node.attr] += 1
        self.generic_visit(node)

    def visit_Call(self, node):
        f = node.func
        name = f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else None)
        if name:
            self.calls[name] += 1
            if self._cur_func and name == self._cur_func[-1] and isinstance(f, ast.Name):
                self.recursive.add(name)
            if isinstance(f, ast.Attribute) and name == "pop":
                if node.args and isinstance(node.args[0], ast.Constant) and node.args[0].value == 0:
                    self.pop0 += 1
                elif not node.args:
                    self.pop_plain += 1
            if name == "popleft":
                self.popleft += 1
            if name == "min" and any(k.arg == "key" for k in node.keywords):
                self.min_key += 1
        self.generic_visit(node)

    def visit_BinOp(self, node):
        if isinstance(node.op, ast.Add):
            def is_abs(x):
                return isinstance(x, ast.Call) and isinstance(x.func, ast.Name) and x.func.id == "abs"
            if is_abs(node.left) and is_abs(node.right):
                self.manhattan = True
        self.generic_visit(node)

    def visit_For(self, node):
        self._for_stack.append(node)
        depth = len(self._for_stack)
        self.max_for_depth = max(self.max_for_depth, depth)
        if depth >= 3 and all(_is_range_for(f) for f in self._for_stack[-3:]):
            self.range_triple = True
        # (n-1)-iteration loop over all edges
        if _is_range_for(node) and any(_iterates_edges(sub) for sub in ast.walk(node) if isinstance(sub, ast.For) and sub is not node):
            self.edge_sweep = True
        self.generic_visit(node)
        self._for_stack.pop()

    def visit_While(self, node):
        if any(_iterates_edges(sub) for sub in ast.walk(node) if isinstance(sub, ast.For)):
            # `while changed:` sweeps over all edges
            src = ast.unparse(node.test).lower() if hasattr(ast, "unparse") else ""
            if any(k in src for k in ("changed", "updated", "relax", "improved", "true")):
                self.edge_sweep = True
        self.generic_visit(node)

    def visit_ListComp(self, node):
        if isinstance(node.elt, (ast.List, ast.Set)) and not getattr(node.elt, "elts", [1]):
            self._maybe_bucket(node)
        elif isinstance(node.elt, ast.Call) and isinstance(node.elt.func, ast.Name) and node.elt.func.id in ("list", "set", "deque"):
            self._maybe_bucket(node)
        self.generic_visit(node)

    def _maybe_bucket(self, node):
        try:
            src = ast.unparse(node)
        except (ValueError, AttributeError):
            src = ""
        if any(k in src for k in ("* (n", "*(n", "* n", "*n", "max_w", "maxw", "max_weight", "100 *", "100*", "C *", "C*")):
            self.bucket_lists = True


def _is_range_for(f: ast.For) -> bool:
    it = f.iter
    return isinstance(it, ast.Call) and isinstance(it.func, ast.Name) and it.func.id == "range"


def _iterates_edges(f) -> bool:
    it = getattr(f, "iter", None)
    return isinstance(it, ast.Name) and it.id in ("edges", "edge_list", "E", "graph_edges")


def ast_features(code: str) -> dict | None:
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError):
        return None
    v = _Feat()
    v.visit(tree)
    src = code.lower()
    names = {k.lower() for k in v.names}
    heap = ("heapq" in src) or ("heappush" in src) or ("priorityqueue" in src)
    deque_used = "deque" in src
    ids = " ".join(sorted(names))

    def has_sub(k):
        return any(k in nm for nm in names)

    two_sided = ((has_sub("forward") and has_sub("backward")) or
                 (any(nm.startswith("front") for nm in names) and any(nm.startswith("back") for nm in names)) or
                 any(k in names for k in ("visited_start", "visited_goal", "visited_end", "q_start", "q_goal", "q_end",
                                        "start_queue", "goal_queue", "end_queue", "visited_s", "visited_t", "dist_s",
                                        "dist_t", "pf", "pb", "qf", "qb", "df", "db", "fwd", "bwd", "hf", "hb",
                                        "from_start", "from_goal", "from_end", "frontier_start", "frontier_goal",
                                        "start_frontier", "goal_frontier", "reverse", "rev", "radj", "rgraph",
                                        "reverse_graph", "reverse_adj", "dist_f", "dist_b", "heap_f", "heap_b",
                                        "pq_f", "pq_b", "parent_start", "parent_goal")))
    iddfs = (v.depth_param or any(k in names for k in ("depth_limit", "max_depth", "limit", "depth"))) and \
            ("iddfs" in src or "iterative deepening" in src or "deepening" in src or
             any(k in names for k in ("depth_limit", "limit", "max_depth")) and (bool(v.recursive) or v.pop_plain > 0))
    sort_select = (v.calls.get("sort", 0) > 0 or v.calls.get("sorted", 0) > 0) and (v.pop0 > 0 or v.pop_plain > 0)
    min_select = v.min_key > 0
    return {"heap": heap, "deque": deque_used, "sort_select": sort_select, "min_select": min_select, "popleft": v.popleft, "pop0": v.pop0, "pop_plain": v.pop_plain,
            "recursive": sorted(v.recursive), "manhattan": v.manhattan or "manhattan" in src or "heuristic" in ids,
            "range_triple": v.range_triple, "edge_sweep": v.edge_sweep, "bucket_lists": v.bucket_lists or "bucket" in ids,
            "two_sided": two_sided, "iddfs": bool(iddfs), "max_for_depth": v.max_for_depth}


def ast_label(task: str, code: str) -> tuple[str | None, bool, dict]:
    f = ast_features(code)
    if f is None:
        return None, False, {"reason": "syntax_error"}
    fifo = f["popleft"] > 0 or f["pop0"] > 0
    stackish = f["pop_plain"] > 0 or bool(f["recursive"])
    if task == "t1":
        if f["sort_select"] or f["min_select"]:
            return ("astar", True, f) if f["manhattan"] else ("dijkstra_unit", False, f)
        if f["heap"]:
            if f["two_sided"]:
                return None, False, f | {"reason": "two_sided_heap"}
            return ("astar", True, f) if f["manhattan"] else ("dijkstra_unit", True, f)
        if fifo:
            return ("bidir_bfs", True, f) if f["two_sided"] else ("bfs", not stackish or f["popleft"] > 0, f)
        if f["iddfs"] and stackish:
            return "iddfs", True, f
        if stackish:
            return "dfs", True, f
        if f["two_sided"]:
            return "bidir_bfs", False, f
        return None, False, f | {"reason": "no_rule"}
    # T2
    if f["range_triple"] and not f["heap"]:
        return "floyd_warshall", True, f
    if f["bucket_lists"] and not f["heap"]:
        return "dial", True, f
    if f["heap"]:
        return ("bidir_dijkstra", True, f) if f["two_sided"] else ("dijkstra", True, f)
    if f["sort_select"] or f["min_select"]:
        return ("bidir_dijkstra", False, f) if f["two_sided"] else ("dijkstra", True, f)
    if f["edge_sweep"]:
        return "bellman_ford_spfa", True, f
    if fifo:
        return "bellman_ford_spfa", True, f
    return None, False, f | {"reason": "no_rule"}


# ------------------------------------------------------------------------------------------ comment stripping


def strip_comments(code: str) -> str:
    """Remove comments and docstrings (the judge must not read the algorithm name from prose).

    ast.unparse drops every comment; docstrings are removed from module, class and function bodies.
    Unparseable code falls back to line-wise '#' stripping.
    """
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                body = node.body
                if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant) \
                        and isinstance(body[0].value.value, str):
                    node.body = body[1:] or [ast.Pass()]
        return ast.unparse(tree)
    except (SyntaxError, ValueError, RecursionError):
        return "\n".join(ln.split("#", 1)[0].rstrip() for ln in code.splitlines() if ln.split("#", 1)[0].strip())
