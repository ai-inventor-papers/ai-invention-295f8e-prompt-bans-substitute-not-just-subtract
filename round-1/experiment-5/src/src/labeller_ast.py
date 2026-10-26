"""AST labeller (STEP 3.2): static feature flags + ordered rules per task.

T1 rules: heap -> astar_greedy if heuristic flag else dijkstra_unit; FIFO -> bidir_bfs if two frontiers else bfs;
          LIFO or recursion -> iddfs if depth-limit loop else dfs; otherwise unknown.
T2 rules: Floyd-Warshall pattern -> floyd_warshall; two heaps + reverse adjacency -> bidir_dijkstra; heap -> dijkstra;
          buckets -> dial; array-scan min -> dijkstra; relaxation rounds or SPFA -> bellman_ford_spfa; otherwise unknown.
'other:<sub>' for library calls, exhaustive enumeration, 0-1 BFS, DAG-DP, BFS ignoring weights (T2).
"""
from __future__ import annotations

import ast
import re

STDLIB_OK = {"collections", "heapq", "queue", "math", "sys", "itertools", "functools", "typing", "bisect", "random",
             "copy", "operator", "dataclasses", "array", "string", "re", "time", "os", "enum", "abc", "statistics",
             "__future__", "types", "numbers", "fractions", "decimal", "contextlib", "threading"}
HEUR_NAME = re.compile(r"(heur|manhattan|estimate|^h$|^h_|_h$|dist_to_goal|cost_to_goal|to_goal|^est)", re.I)
DEPTH_NAME = re.compile(r"(depth|limit|bound|max_d|maxd|lim|level|^d$|^L$|cutoff|threshold)", re.I)


def _name(n: ast.AST) -> str | None:
    if isinstance(n, ast.Name):
        return n.id
    if isinstance(n, ast.Attribute):
        return n.attr
    return None


def _call_name(c: ast.Call) -> str | None:
    return _name(c.func)


def _recv(c: ast.Call) -> str | None:
    """Receiver name for x.method(...) calls (x a Name or x.attr / x[...])."""
    if isinstance(c.func, ast.Attribute):
        v = c.func.value
        if isinstance(v, ast.Name):
            return v.id
        if isinstance(v, ast.Attribute):
            return v.attr
        if isinstance(v, ast.Subscript):
            return ast.unparse(v)
    return None


def _contains(node: ast.AST, pred) -> bool:
    return any(pred(n) for n in ast.walk(node))


class Feats:
    def __init__(self, tree: ast.Module, task: str):
        self.tree = tree
        self.task = task
        self.funcs = {n.name: n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
        self.imports: set[str] = set()
        self.heap_from: set[str] = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                for a in n.names:
                    self.imports.add(a.name.split(".")[0])
            elif isinstance(n, ast.ImportFrom) and n.module:
                self.imports.add(n.module.split(".")[0])
                if n.module == "heapq":
                    for a in n.names:
                        self.heap_from.add(a.asname or a.name)
        self.assign_map: dict[str, list[ast.AST]] = {}
        for n in ast.walk(tree):
            if isinstance(n, ast.Assign):
                for t in n.targets:
                    for tt in ast.walk(t):
                        if isinstance(tt, ast.Name):
                            self.assign_map.setdefault(tt.id, []).append(n.value)
            elif isinstance(n, (ast.AnnAssign, ast.AugAssign)) and isinstance(n.target, ast.Name) and n.value is not None:
                self.assign_map.setdefault(n.target.id, []).append(n.value)
        self.calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)]
        self.compute()

    # ------------------------------------------------------------------ helpers
    def is_heap_call(self, c: ast.Call, names=("heappush", "heappop", "heapify", "heappushpop", "heapreplace")) -> bool:
        f = c.func
        if isinstance(f, ast.Attribute) and f.attr in names and isinstance(f.value, ast.Name) and f.value.id == "heapq":
            return True
        if isinstance(f, ast.Name) and f.id in names and (f.id in self.heap_from or "heapq" in self.imports):
            return True
        return False

    def _resolve(self, e: ast.AST, depth: int = 0) -> list[ast.AST]:
        out = [e]
        if depth < 2:
            for n in ast.walk(e):
                if isinstance(n, ast.Name) and n.id in self.assign_map:
                    for v in self.assign_map[n.id][:4]:
                        out.extend(self._resolve(v, depth + 1))
        return out

    def _heuristicish(self, e: ast.AST) -> bool:
        for x in self._resolve(e):
            for n in ast.walk(x):
                if isinstance(n, ast.Call):
                    nm = _call_name(n)
                    if nm == "abs":
                        return True
                    if nm and HEUR_NAME.search(nm):
                        return True
                    if nm in self.funcs and nm != "solve":
                        body = self.funcs[nm]
                        if _contains(body, lambda k: isinstance(k, ast.Call) and _call_name(k) == "abs"):
                            return True
                if isinstance(n, ast.Name) and HEUR_NAME.search(n.id) and n.id not in ("h",) or (
                        isinstance(n, ast.Name) and n.id in ("h", "heuristic") and n.id in self.assign_map):
                    for v in self.assign_map.get(n.id, []):
                        if _contains(v, lambda k: isinstance(k, ast.Call) and _call_name(k) in ("abs",)
                                     or (isinstance(k, ast.Call) and _call_name(k) in self.funcs
                                         and _contains(self.funcs[_call_name(k)],
                                                       lambda q: isinstance(q, ast.Call) and _call_name(q) == "abs"))):
                            return True
        return False

    # ------------------------------------------------------------------ features
    def compute(self) -> None:
        heap_calls = [c for c in self.calls if self.is_heap_call(c)]
        pq_ctor = any(_call_name(c) == "PriorityQueue" for c in self.calls)
        self.heap = bool(heap_calls) or pq_ctor
        heap_names = set()
        for c in heap_calls:
            if c.args and _call_name(c) in ("heappop", "heappush", "heappushpop", "heapreplace"):
                nm = _name(c.args[0]) or (ast.unparse(c.args[0]) if isinstance(c.args[0], ast.Subscript) else None)
                if nm:
                    heap_names.add(nm)
        if pq_ctor:
            for c in self.calls:
                if _call_name(c) == "put":
                    r = _recv(c)
                    if r:
                        heap_names.add(r)
        self.heap_names = heap_names
        # heuristic flag: priority expression of pushes
        self.heuristic = False
        for c in self.calls:
            item = None
            if self.is_heap_call(c, ("heappush", "heappushpop", "heapreplace")) and len(c.args) >= 2:
                item = c.args[1]
            elif pq_ctor and _call_name(c) == "put" and c.args:
                item = c.args[0]
            if item is None:
                continue
            prio = item.elts[0] if isinstance(item, ast.Tuple) and item.elts else item
            if self._heuristicish(prio):
                self.heuristic = True
        # FIFO / LIFO
        fifo_recv, lifo = set(), False
        for c in self.calls:
            nm = _call_name(c)
            if nm == "popleft":
                fifo_recv.add(_recv(c) or "?")
            elif nm == "pop" and isinstance(c.func, ast.Attribute):
                if len(c.args) == 1 and isinstance(c.args[0], ast.Constant) and c.args[0].value == 0:
                    fifo_recv.add(_recv(c) or "?")
                elif len(c.args) == 0:
                    lifo = True
                elif len(c.args) == 1 and isinstance(c.args[0], ast.UnaryOp) and isinstance(c.args[0].op, ast.USub):
                    lifo = True
            elif nm == "get" and isinstance(c.func, ast.Attribute) and len(c.args) == 0 and not c.keywords:
                r = _recv(c)
                if r and any(_call_name(v) in ("Queue", "SimpleQueue") for v in
                             [x for x in self.assign_map.get(r, []) if isinstance(x, ast.Call)]):
                    fifo_recv.add(r)
                if r and any(_call_name(v) == "LifoQueue" for v in
                             [x for x in self.assign_map.get(r, []) if isinstance(x, ast.Call)]):
                    lifo = True
        # level-synchronous frontier: while F: ... G.append(...) ... F = G   (BFS by layers, no pops)
        self.levels = 0
        for n in ast.walk(self.tree):
            if isinstance(n, ast.While) and isinstance(n.test, (ast.Name, ast.Call, ast.Compare)):
                fn_ = None
                if isinstance(n.test, ast.Name):
                    fn_ = n.test.id
                elif isinstance(n.test, ast.Call) and n.test.args and isinstance(n.test.args[0], ast.Name):
                    fn_ = n.test.args[0].id
                elif isinstance(n.test, ast.Compare) and isinstance(n.test.left, ast.Call) and n.test.left.args and \
                        isinstance(n.test.left.args[0], ast.Name):
                    fn_ = n.test.left.args[0].id
                if not fn_:
                    continue
                appended = {_recv(c) for c in ast.walk(n) if isinstance(c, ast.Call) and _call_name(c) in ("append", "add")}
                for st in n.body:
                    if isinstance(st, ast.Assign) and any(isinstance(t, ast.Name) and t.id == fn_ for t in st.targets):
                        if isinstance(st.value, ast.Name) and st.value.id in appended:
                            self.levels += 1
        self.fifo = bool(fifo_recv)
        self.fifo_recv = fifo_recv
        self.lifo = lifo or any(_call_name(c) == "LifoQueue" for c in self.calls)
        self.appendleft = any(_call_name(c) == "appendleft" for c in self.calls)
        # recursion
        self.recursion = False
        for fn in self.funcs.values():
            for n in ast.walk(fn):
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == fn.name:
                    self.recursion = True
        # IDDFS: loop variable passed to a user function call, or loop body with a stack DFS comparing to loop var
        self.depth_loop = False
        for n in ast.walk(self.tree):
            loopvar = None
            if isinstance(n, ast.For) and isinstance(n.target, ast.Name):
                if isinstance(n.iter, ast.Call) and _call_name(n.iter) in ("range", "count"):
                    loopvar = n.target.id
            elif isinstance(n, ast.While):
                for m in ast.walk(n):
                    if isinstance(m, ast.AugAssign) and isinstance(m.target, ast.Name) and isinstance(m.op, ast.Add):
                        if DEPTH_NAME.search(m.target.id):
                            loopvar = m.target.id
                            break
            if not loopvar:
                continue
            body = n.body
            for st in body:
                for m in ast.walk(st):
                    if isinstance(m, ast.Call) and _call_name(m) in self.funcs and _call_name(m) != "solve":
                        argnames = {a.id for a in m.args if isinstance(a, ast.Name)}
                        argnames |= {k.value.id for k in m.keywords if isinstance(k.value, ast.Name)}
                        if loopvar in argnames:
                            self.depth_loop = True
                    if isinstance(m, ast.While) and _contains(m, lambda q: isinstance(q, ast.Call) and _call_name(q) == "pop"):
                        if _contains(m, lambda q: isinstance(q, ast.Compare) and any(
                                isinstance(x, ast.Name) and x.id == loopvar for x in ast.walk(q))):
                            self.depth_loop = True
        # bidirectional: two FIFO frontiers or two heaps, plus a meet test
        meet = _contains(self.tree, lambda q: (isinstance(q, ast.BinOp) and isinstance(q.op, ast.BitAnd)) or (
            isinstance(q, ast.Call) and _call_name(q) in ("intersection", "isdisjoint")) or (
            isinstance(q, ast.Name) and re.search(r"meet|intersect", q.id, re.I) is not None))
        in_other = _contains(self.tree, lambda q: isinstance(q, ast.Compare) and any(isinstance(o, ast.In) for o in q.ops))
        self.two_fifo = len(fifo_recv) >= 2 and (meet or in_other)
        self.two_heaps = len(heap_names) >= 2
        # reverse adjacency: for (u, v, w) in edges: X[v].append((u, ...)) or names like radj/rev
        self.rev_adj = False
        for n in ast.walk(self.tree):
            if isinstance(n, ast.For) and isinstance(n.target, ast.Tuple) and len(n.target.elts) >= 2:
                names = [e.id if isinstance(e, ast.Name) else None for e in n.target.elts]
                a, b = names[0], names[1]
                for m in ast.walk(n):
                    if isinstance(m, ast.Call) and _call_name(m) == "append" and isinstance(m.func, ast.Attribute):
                        v = m.func.value
                        if isinstance(v, ast.Subscript) and isinstance(v.slice, ast.Name) and v.slice.id == b and m.args:
                            if any(isinstance(x, ast.Name) and x.id == a for x in ast.walk(m.args[0])):
                                self.rev_adj = True
        if not self.rev_adj:
            self.rev_adj = _contains(self.tree, lambda q: isinstance(q, ast.Name) and re.search(
                r"(^r_?adj|rev|reverse|radj|backward|^bwd|in_adj|incoming|pred)", q.id, re.I) is not None)
        # Floyd-Warshall: X[i][k] + X[k][j] or three nested for-range loops with an Add inside
        self.fw = False
        for n in ast.walk(self.tree):
            if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Add):
                l, r = n.left, n.right
                if (isinstance(l, ast.Subscript) and isinstance(l.value, ast.Subscript) and isinstance(r, ast.Subscript)
                        and isinstance(r.value, ast.Subscript)):
                    k1, k2 = l.slice, r.value.slice
                    i1, j2 = l.value.slice, r.slice
                    names_ok = all(isinstance(x, ast.Name) for x in (k1, k2, i1, j2))
                    if names_ok and k1.id == k2.id and len({i1.id, k1.id, j2.id}) == 3:
                        self.fw = True
        if not self.fw:
            for n in ast.walk(self.tree):
                if isinstance(n, ast.For) and isinstance(n.iter, ast.Call) and _call_name(n.iter) == "range":
                    for m in ast.walk(n):
                        if m is n or not (isinstance(m, ast.For) and isinstance(m.iter, ast.Call) and _call_name(m.iter) == "range"):
                            continue
                        for q in ast.walk(m):
                            if q is m or not (isinstance(q, ast.For) and isinstance(q.iter, ast.Call) and _call_name(q.iter) == "range"):
                                continue
                            if _contains(q, lambda z: isinstance(z, ast.BinOp) and isinstance(z.op, ast.Add)) and \
                                    _contains(q, lambda z: isinstance(z, ast.Compare) or (isinstance(z, ast.Call) and _call_name(z) == "min")):
                                outer_vars = {n.target.id if isinstance(n.target, ast.Name) else None}
                                if any(isinstance(z, ast.Subscript) for z in ast.walk(q)) and outer_vars:
                                    self.fw = True
        # Bellman-Ford rounds: outer for-range / while containing an inner for over the edges list with an Add compare
        params = []
        if "solve" in self.funcs:
            params = [a.arg for a in self.funcs["solve"].args.args]
        edges_name = params[1] if len(params) >= 2 else "edges"
        self.bf_rounds = False
        for n in ast.walk(self.tree):
            if isinstance(n, (ast.For, ast.While)):
                for m in ast.walk(n):
                    if m is n or not isinstance(m, ast.For):
                        continue
                    it = m.iter
                    over_edges = isinstance(it, ast.Name) and (it.id == edges_name or it.id in ("edges", "edge_list", "E"))
                    if not over_edges and isinstance(it, ast.Call) and _call_name(it) == "range" and it.args:
                        over_edges = _contains(it, lambda z: isinstance(z, ast.Call) and _call_name(z) == "len" and
                                               any(isinstance(a, ast.Name) and a.id == edges_name for a in z.args))
                    if over_edges and _contains(m, lambda z: isinstance(z, ast.Compare) and isinstance(z.left, ast.BinOp)
                                                 or isinstance(z, ast.Compare) and any(isinstance(c, ast.BinOp) for c in z.comparators)):
                        outer_ok = (isinstance(n, ast.While) or (isinstance(n, ast.For) and isinstance(n.iter, ast.Call)
                                                                  and _call_name(n.iter) == "range"))
                        if outer_ok:
                            self.bf_rounds = True
        # relaxation compare present
        self.relax = _contains(self.tree, lambda z: isinstance(z, ast.Compare) and (
            isinstance(z.left, ast.BinOp) and isinstance(z.left.op, ast.Add) or
            any(isinstance(c, ast.BinOp) and isinstance(c.op, ast.Add) for c in z.comparators)))
        self.inqueue = _contains(self.tree, lambda z: isinstance(z, ast.Name) and re.search(
            r"(in_?q(ueue)?|inq|queued|in_que|on_queue|enqueued)", z.id, re.I) is not None)
        self.spfa = self.fifo and self.relax and self.task == "t2"
        # Dial buckets
        self.buckets = _contains(self.tree, lambda z: isinstance(z, ast.Name) and re.search(r"bucket", z.id, re.I) is not None)
        # array-scan min: min(..., key=lambda x: dist[x]) or loop over range(n) selecting argmin of unvisited
        self.array_min = False
        for c in self.calls:
            if _call_name(c) == "min" and any(k.arg == "key" for k in c.keywords):
                self.array_min = True
        for n in ast.walk(self.tree):
            if isinstance(n, ast.For) and isinstance(n.iter, ast.Call) and _call_name(n.iter) == "range":
                for m in ast.walk(n):
                    if isinstance(m, ast.If) and isinstance(m.test, ast.BoolOp):
                        txt = ast.unparse(m.test)
                        if re.search(r"(not\s+\w*(visit|done|final|used|seen|processed|fixed)|\bnot in\b)", txt) and "<" in txt:
                            if any(isinstance(s, ast.Assign) for s in m.body):
                                self.array_min = True
        # other sub-labels
        nonstd = {m for m in self.imports if m not in STDLIB_OK}
        self.library = bool(nonstd) or any(_call_name(c) in ("shortest_path_length", "shortest_path", "dijkstra_path",
                                                               "dijkstra_path_length") for c in self.calls)
        self.nonstd = sorted(nonstd)
        self.permutations = any(_call_name(c) in ("permutations", "product") for c in self.calls)
        self.topo = _contains(self.tree, lambda z: isinstance(z, ast.Name) and re.search(r"(indeg|in_deg|topo)", z.id, re.I) is not None)

    def as_dict(self) -> dict:
        keys = ["heap", "heuristic", "fifo", "levels", "lifo", "appendleft", "recursion", "depth_loop", "two_fifo", "two_heaps",
                "rev_adj", "fw", "bf_rounds", "relax", "inqueue", "spfa", "buckets", "array_min", "library", "permutations",
                "topo"]
        d = {k: bool(getattr(self, k)) for k in keys}
        d["nonstd_imports"] = self.nonstd
        d["n_fifo_recv"] = len(self.fifo_recv)
        d["n_heap_names"] = len(self.heap_names)
        return d


def label_ast(code: str, task: str) -> tuple[str, dict]:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return "unknown", {"error": "syntax"}
    f = Feats(tree, task)
    d = f.as_dict()
    if f.library:
        return "other:library", d
    if task == "t1":
        if f.heap:
            return ("astar_greedy" if f.heuristic else "dijkstra_unit"), d
        if f.fifo or f.levels:
            if f.two_fifo or f.levels >= 2:
                return "bidir_bfs", d
            return "bfs", d
        if f.lifo or f.recursion:
            return ("iddfs" if f.depth_loop else "dfs"), d
        return "unknown", d
    # t2
    if f.fw:
        return "floyd_warshall", d
    if f.two_heaps and f.rev_adj:
        return "bidir_dijkstra", d
    if f.heap:
        return "dijkstra", d
    if f.buckets:
        return "dial", d
    if f.array_min:
        return "dijkstra", d
    if f.bf_rounds or f.spfa:
        if f.fifo and f.appendleft and not f.inqueue:
            return "other:0-1_bfs", d
        return "bellman_ford_spfa", d
    if (f.fifo or f.levels) and not f.relax:
        return "other:bfs_ignoring_weights", d
    if f.levels and f.relax:
        return "bellman_ford_spfa", d
    if f.permutations:
        return "other:exhaustive_enumeration", d
    if f.topo:
        return "other:dag_dp", d
    if f.recursion and not f.relax:
        return "other:exhaustive_enumeration", d
    return "unknown", d
