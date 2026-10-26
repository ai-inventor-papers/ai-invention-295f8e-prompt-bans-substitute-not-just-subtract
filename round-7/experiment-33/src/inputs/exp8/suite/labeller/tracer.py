#!/usr/bin/env python3
"""5c runtime tracer (subprocess, stdlib only): instruments ONE candidate on fixed probe inputs and reports raw
runtime features as one JSON line. The decision rules live in labeller/runtime_rules.py (parent side).

Instrumentation is installed BEFORE the candidate is exec'd:
  * sys.modules['heapq'] -> proxy recording (op, id(heap), priority), priority = item if numeric else item[0]
  * collections.deque -> recording subclass (per-instance append/appendleft/pop/popleft counts)
  * queue.Queue/LifoQueue/PriorityQueue -> recording subclasses (put/get; PriorityQueue priorities)
  * sys.setprofile: candidate-frame call depth / self-recursion, list.pop FIFO-vs-LIFO (by comparing the list
    before/after the C call), list.insert counts
  * T1: the grid is a list of str-subclass rows whose __getitem__ records (row, col) access order
    (__iter__ on a row flags grid_copied)
  * T2: edges is a list subclass counting full passes / index reads; sys.settrace counts 'line' events of
    '<candidate>' frames (scaling exponent between the n=24 and n=48 probe graphs)
Job on stdin: {"task", "code", "tasks_dir", "probe_timeout_s"}.
"""

import ast
import collections
import heapq as _real_heapq
import io
import json
import os
import queue
import random
import resource
import sys
import threading
import time
import types

FORBIDDEN = {"os", "subprocess", "socket", "shutil", "ctypes", "multiprocessing"}


class Rec:
    def __init__(self):
        self.reset()

    def reset(self):
        self.heaps = {}        # id -> dict(push, pop, pops=[], pushes=[], order)
        self.deques = {}       # id -> dict(append, appendleft, pop, popleft, order)
        self.queues = {}       # id -> dict(kind, put, get, gets=[], order)
        self.list_pop = {"fifo": 0, "lifo": 0, "ambig": 0, "mid": 0}
        self.list_insert = 0
        self.pop_lists = set()
        self.calls = 0
        self.max_depth = 0
        self.recursion = False
        self.stack = []
        self.pending = {}
        self.access = []
        self.flags = {"grid_copied": False, "row_slice": False}
        self.lines = 0
        self.seq = 0
        self.keep = []
        self.edges_iter = 0
        self.edges_full = 0
        self.edges_index = 0
        self.order = 0


R = Rec()
_CAP = 4000


def _prio(item):
    if isinstance(item, bool):
        return None
    if isinstance(item, (int, float)):
        return float(item)
    if isinstance(item, (tuple, list)) and item:
        f = item[0]
        if isinstance(f, (int, float)) and not isinstance(f, bool):
            return float(f)
    return None


def _heap_rec(h):
    k = id(h)
    rec = R.heaps.get(k)
    if rec is None:
        R.order += 1
        rec = {"push": 0, "pop": 0, "pops": [], "pushes": [], "order": R.order, "first": None, "last": None}
        R.heaps[k] = rec
        R.keep.append(h)
    return rec


def _mark_pop(rec):
    R.seq += 1
    if rec["first"] is None:
        rec["first"] = R.seq
    rec["last"] = R.seq


def _mk_heap_proxy():
    m = types.ModuleType("heapq")

    def heappush(heap, item):
        rec = _heap_rec(heap)
        rec["push"] += 1
        if len(rec["pushes"]) < _CAP:
            rec["pushes"].append(_prio(item))
        return _real_heapq.heappush(heap, item)

    def heappop(heap):
        item = _real_heapq.heappop(heap)
        rec = _heap_rec(heap)
        _mark_pop(rec)
        rec["pop"] += 1
        if len(rec["pops"]) < _CAP:
            rec["pops"].append(_prio(item))
        return item

    def heapify(x):
        rec = _heap_rec(x)
        rec["push"] += len(x)
        return _real_heapq.heapify(x)

    def heappushpop(heap, item):
        out = _real_heapq.heappushpop(heap, item)
        rec = _heap_rec(heap)
        _mark_pop(rec)
        rec["push"] += 1
        rec["pop"] += 1
        if len(rec["pops"]) < _CAP:
            rec["pops"].append(_prio(out))
        return out

    def heapreplace(heap, item):
        out = _real_heapq.heapreplace(heap, item)
        rec = _heap_rec(heap)
        _mark_pop(rec)
        rec["push"] += 1
        rec["pop"] += 1
        if len(rec["pops"]) < _CAP:
            rec["pops"].append(_prio(out))
        return out

    m.heappush = heappush
    m.heappop = heappop
    m.heapify = heapify
    m.heappushpop = heappushpop
    m.heapreplace = heapreplace
    m.nsmallest = _real_heapq.nsmallest
    m.nlargest = _real_heapq.nlargest
    m.merge = _real_heapq.merge
    m.__all__ = ["heappush", "heappop", "heapify", "heapreplace", "merge", "nlargest", "nsmallest", "heappushpop"]
    return m


_RealDeque = collections.deque


class TDeque(_RealDeque):
    def _r(self):
        k = id(self)
        rec = R.deques.get(k)
        if rec is None:
            R.order += 1
            rec = {"append": 0, "appendleft": 0, "pop": 0, "popleft": 0, "order": R.order, "first": None,
                   "last": None}
            R.deques[k] = rec
            R.keep.append(self)
        return rec

    def append(self, x):
        self._r()["append"] += 1
        return _RealDeque.append(self, x)

    def appendleft(self, x):
        self._r()["appendleft"] += 1
        return _RealDeque.appendleft(self, x)

    def pop(self):
        v = _RealDeque.pop(self)
        rec = self._r()
        _mark_pop(rec)
        rec["pop"] += 1
        return v

    def popleft(self):
        v = _RealDeque.popleft(self)
        rec = self._r()
        _mark_pop(rec)
        rec["popleft"] += 1
        return v

    def extend(self, it):
        it = list(it)
        self._r()["append"] += len(it)
        return _RealDeque.extend(self, it)


def _mk_queue_cls(base, kind):
    class TQ(base):
        def _r(self):
            k = id(self)
            rec = R.queues.get(k)
            if rec is None:
                R.order += 1
                rec = {"kind": kind, "put": 0, "get": 0, "gets": [], "order": R.order, "first": None, "last": None}
                R.queues[k] = rec
                R.keep.append(self)
            return rec

        def put(self, item, block=True, timeout=None):
            self._r()["put"] += 1
            return base.put(self, item, block, timeout)

        def get(self, block=True, timeout=None):
            v = base.get(self, block, timeout)
            rec = self._r()
            _mark_pop(rec)
            rec["get"] += 1
            if kind == "priority" and len(rec["gets"]) < _CAP:
                rec["gets"].append(_prio(v))
            return v

        def put_nowait(self, item):
            return self.put(item, False)

        def get_nowait(self):
            return self.get(False)

    TQ.__name__ = base.__name__
    TQ.__qualname__ = base.__qualname__
    return TQ


class TRow(str):
    def __getitem__(self, c):
        if isinstance(c, int):
            if len(R.access) < 200000:
                R.access.append((self._r, c if c >= 0 else c + len(self)))
        else:
            R.flags["row_slice"] = True
        return str.__getitem__(self, c)

    def __iter__(self):
        R.flags["grid_copied"] = True
        return str.__iter__(self)


def make_grid(rows):
    out = []
    for i, s in enumerate(rows):
        r = TRow(s)
        r._r = i
        out.append(r)
    return out


class TEdges(list):
    def __iter__(self):
        R.edges_iter += 1
        n = 0
        for x in list.__iter__(self):
            n += 1
            yield x
        if n == len(self):
            R.edges_full += 1

    def __getitem__(self, i):
        if isinstance(i, int):
            R.edges_index += 1
        return list.__getitem__(self, i)


def _profile(frame, event, arg):
    try:
        if event == "call":
            code = frame.f_code
            if code.co_filename == "<candidate>":
                R.calls += 1
                if code in R.stack:
                    R.recursion = True
                R.stack.append(code)
                if len(R.stack) > R.max_depth:
                    R.max_depth = len(R.stack)
        elif event == "return":
            if frame.f_code.co_filename == "<candidate>" and R.stack:
                R.stack.pop()
        elif event == "c_call":
            obj = getattr(arg, "__self__", None)
            if type(obj) is list:
                name = getattr(arg, "__name__", "")
                if name == "pop":
                    n = len(obj)
                    if n >= 2:
                        R.pending[id(obj)] = (n, id(obj[0]), id(obj[1]), id(obj[-1]), id(obj[-2]))
                elif name == "insert":
                    R.list_insert += 1
        elif event == "c_return":
            obj = getattr(arg, "__self__", None)
            if type(obj) is list and getattr(arg, "__name__", "") == "pop":
                snap = R.pending.pop(id(obj), None)
                if len(R.pop_lists) < 10000:
                    R.pop_lists.add(id(obj))
                if snap is not None and len(obj) == snap[0] - 1 and obj:
                    first_removed = id(obj[0]) == snap[2]
                    last_removed = id(obj[-1]) == snap[4]
                    if first_removed and not last_removed:
                        R.list_pop["fifo"] += 1
                    elif last_removed and not first_removed:
                        R.list_pop["lifo"] += 1
                    elif first_removed and last_removed:
                        R.list_pop["ambig"] += 1
                    else:
                        R.list_pop["mid"] += 1
    except Exception:  # noqa: BLE001 - the profiler must never break the candidate
        pass


def _ltrace(frame, event, arg):
    if event == "line":
        R.lines += 1
    return _ltrace


def _gtrace(frame, event, arg):
    if frame.f_code.co_filename == "<candidate>":
        return _ltrace
    return None


def screen(code):
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError):
        return "syntax_error"
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name.split(".")[0] in FORBIDDEN:
                    return "forbidden_import"
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.split(".")[0] in FORBIDDEN:
                return "forbidden_import"
    return None


def perfect_maze(h, w, rng):
    g = [["#"] * w for _ in range(h)]
    stack = [(0, 0)]
    g[0][0] = "."
    while stack:
        r, c = stack[-1]
        nbrs = [(r + dr, c + dc, r + dr // 2, c + dc // 2) for dr, dc in ((-2, 0), (2, 0), (0, -2), (0, 2))
                if 0 <= r + dr < h and 0 <= c + dc < w and g[r + dr][c + dc] == "#"]
        if not nbrs:
            stack.pop()
            continue
        nr, nc, wr, wc = rng.choice(nbrs)
        g[wr][wc] = "."
        g[nr][nc] = "."
        stack.append((nr, nc))
    return ["".join(row) for row in g]


def bfs_dist(grid, src):
    rows, cols = len(grid), len(grid[0])
    dist = {src: 0}
    q = _RealDeque([src])
    while q:
        r, c = q.popleft()
        for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == "." and (nr, nc) not in dist:
                dist[(nr, nc)] = dist[(r, c)] + 1
                q.append((nr, nc))
    return dist


def t1_probes():
    open15 = ["." * 15] * 15
    maze = perfect_maze(15, 15, random.Random(7))
    probes = []
    for g in ((7, 0), (7, 14), (0, 7), (14, 7)):
        probes.append(("P_open", open15, (7, 7), g))
    probes.append(("P_maze", maze, (0, 0), (14, 14)))
    probes.append(("P_diag", open15, (0, 0), (14, 14)))
    return probes


def rand_graph(n, m, seed):
    rng = random.Random(seed)
    while True:
        edges = [(rng.randrange(n), rng.randrange(n), rng.randint(1, 100)) for _ in range(m)]
        adj = {}
        for u, v, w in edges:
            adj.setdefault(u, []).append(v)
        seen = {0}
        st = [0]
        while st:
            u = st.pop()
            for v in adj.get(u, []):
                if v not in seen:
                    seen.add(v)
                    st.append(v)
        if n - 1 in seen:
            return edges
        seed += 1000
        rng = random.Random(seed)


def dijkstra_value(n, edges, s, t):
    adj = [[] for _ in range(n)]
    for u, v, w in edges:
        adj[u].append((v, w))
    dist = [float("inf")] * n
    dist[s] = 0
    pq = [(0, s)]
    while pq:
        d, u = _real_heapq.heappop(pq)
        if d > dist[u]:
            continue
        for v, w in adj[u]:
            if d + w < dist[v]:
                dist[v] = d + w
                _real_heapq.heappush(pq, (d + w, v))
    return dist[t] if dist[t] != float("inf") else -1


def spearman(xs, ys):
    n = len(xs)
    if n < 3:
        return None

    def ranks(v):
        order = sorted(range(n), key=lambda i: v[i])
        rk = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and v[order[j + 1]] == v[order[i]]:
                j += 1
            for k in range(i, j + 1):
                rk[order[k]] = (i + j) / 2.0
            i = j + 1
        return rk

    rx, ry = ranks(xs), ranks(ys)
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return num / den if den > 0 else None


def snapshot(task, extra):
    heaps = sorted(R.heaps.values(), key=lambda r: r["order"])
    pq = [q for q in sorted(R.queues.values(), key=lambda r: r["order"]) if q["kind"] == "priority"]
    heap_like = [{"push": h["push"], "pop": h["pop"], "pops": h["pops"][:400], "first": h["first"],
                  "last": h["last"]} for h in heaps]
    heap_like += [{"push": q["put"], "pop": q["get"], "pops": q["gets"][:400], "first": q["first"],
                   "last": q["last"]} for q in pq]
    snap = {
        "heaps": heap_like,
        "deques": [{k: d[k] for k in ("append", "appendleft", "pop", "popleft", "first", "last")}
                   for d in sorted(R.deques.values(), key=lambda r: r["order"])],
        "queues": [{k: q[k] for k in ("kind", "put", "get", "first", "last")} for q in R.queues.values()
                   if q["kind"] != "priority"],
        "list_pop": dict(R.list_pop), "list_insert": R.list_insert, "n_pop_lists": len(R.pop_lists),
        "n_deques_popped": sum(1 for d in R.deques.values() if d["pop"] + d["popleft"] > 0), "calls": R.calls, "max_depth": R.max_depth,
        "recursion": R.recursion,
    }
    snap.update(extra)
    return snap


def access_features(grid, start, goal):
    acc = R.access
    feats = {"n_access": len(acc), "grid_copied": R.flags["grid_copied"], "row_slice": R.flags["row_slice"]}
    if not acc:
        return feats
    first = []
    seen = set()
    for cell in acc:
        if cell not in seen:
            seen.add(cell)
            first.append(cell)
    feats["n_distinct"] = len(first)
    feats["reaccess_ratio"] = len(acc) / max(1, len(first))
    ds = bfs_dist(grid, tuple(start))
    dg = bfs_dist(grid, tuple(goal))
    k = max(5, int(0.3 * len(first)))
    early = [c for c in first[:k] if c in ds]
    if len(early) >= 5:
        feats["rho_s"] = spearman(list(range(len(early))), [ds[c] for c in early])
        feats["goal_side_share"] = sum(1 for c in early if dg.get(c, 10 ** 9) < ds[c]) / len(early)
        feats["near_goal3_share"] = sum(1 for c in early if dg.get(c, 10 ** 9) <= 3) / len(early)
    return feats


def main():
    job = json.loads(sys.stdin.read())
    real_out = sys.stdout
    task = job["task"]
    result = {"task": task, "error": None, "probes": []}

    def emit():
        real_out.write(json.dumps(result) + "\n")
        real_out.flush()

    if screen(job["code"]):
        result["error"] = screen(job["code"])
        emit()
        return
    mem = 2 * 1024 ** 3
    resource.setrlimit(resource.RLIMIT_AS, (mem, mem))
    sys.setrecursionlimit(20000)
    threading.stack_size(256 * 1024 * 1024)
    sys.stdout = io.StringIO()
    sys.stdin = io.StringIO("")

    sys.modules["heapq"] = _mk_heap_proxy()
    collections.deque = TDeque
    queue.Queue = _mk_queue_cls(queue.Queue, "fifo")
    queue.LifoQueue = _mk_queue_cls(queue.LifoQueue, "lifo")
    queue.PriorityQueue = _mk_queue_cls(queue.PriorityQueue, "priority")
    queue.SimpleQueue = queue.Queue

    mod = types.ModuleType("cand")
    mod.__file__ = "<candidate>"
    sys.modules["cand"] = mod
    # Gate revision round 1 (development programs only): pre-inject common stdlib names so a program that
    # crashes only on a missing import can still be traced. Explicit imports in the program overwrite these.
    # Labelling aid only -- the hidden-test sandbox never injects anything.
    import itertools
    import math
    hp = sys.modules["heapq"]
    mod.__dict__.update({"heapq": hp, "heappush": hp.heappush, "heappop": hp.heappop, "heapify": hp.heapify,
                         "deque": TDeque, "collections": collections, "defaultdict": collections.defaultdict,
                         "math": math, "itertools": itertools, "queue": queue, "inf": float("inf")})
    box = {}

    def do_exec():
        try:
            exec(compile(job["code"], "<candidate>", "exec"), mod.__dict__)
        except BaseException as e:  # noqa: BLE001
            box["exc"] = type(e).__name__

    th = threading.Thread(target=do_exec, daemon=True)
    th.start()
    th.join(10.0)
    if th.is_alive() or "exc" in box or not callable(mod.__dict__.get("solve")):
        result["error"] = "exec_failed" if not th.is_alive() else "exec_timeout"
        emit()
        os._exit(0)
    solve = mod.__dict__["solve"]
    timeout = float(job.get("probe_timeout_s", 4.0))

    if task == "t1":
        probes = [(name, grid, s, g, None) for (name, grid, s, g) in t1_probes()]
    else:
        probes = []
        for name, n, m, seed in (("G24", 24, 96, 11), ("G48", 48, 192, 12)):
            edges = rand_graph(n, m, seed)
            indeg = [0] * n
            for _u, _v, _w in edges:
                indeg[_v] += 1
            cand = [v for v in range(1, n) if dijkstra_value(n, edges, 0, v) >= 0 and indeg[v] >= 3]
            far = max(cand, key=lambda v: (dijkstra_value(n, edges, 0, v), v))
            probes.append((name, n, edges, 0, far))

    for pr in probes:
        R.reset()
        res = {}
        if task == "t1":
            name, grid, s, g, _ = pr
            args = (make_grid(grid), s, g)
        else:
            name, n, edges, s, g = pr
            args = (n, TEdges(edges), s, g)

        def target():
            sys.setprofile(_profile)
            if task == "t2":
                sys.settrace(_gtrace)
            try:
                res["out"] = solve(*args)
            except BaseException as e:  # noqa: BLE001
                res["exc"] = type(e).__name__
            finally:
                sys.settrace(None)
                sys.setprofile(None)

        th = threading.Thread(target=target, daemon=True)
        t0 = time.perf_counter()
        th.start()
        th.join(timeout)
        dt = time.perf_counter() - t0
        extra = {"name": name, "seconds": round(dt, 4), "timeout": th.is_alive(), "exc": res.get("exc")}
        if task == "t1":
            grid, s, g = pr[1], pr[2], pr[3]
            extra["start"] = list(s)
            extra["goal"] = list(g)
            shortest = bfs_dist(grid, s).get(g)
            extra["shortest_len"] = None if shortest is None else shortest + 1
            out = res.get("out")
            valid = False
            plen = None
            if isinstance(out, (list, tuple)) and out:
                try:
                    path = [(int(p[0]), int(p[1])) for p in out]
                    valid = (path[0] == tuple(s) and path[-1] == tuple(g)
                             and all(0 <= r < 15 and 0 <= c < 15 and grid[r][c] == "." for r, c in path)
                             and all(abs(a - c) + abs(b - d) == 1 for (a, b), (c, d) in zip(path, path[1:])))
                    plen = len(path)
                except (TypeError, ValueError, IndexError):
                    valid = False
            extra["valid"] = valid
            extra["path_len"] = plen
            extra["optimal"] = bool(valid and extra["shortest_len"] is not None and plen == extra["shortest_len"])
            extra.update(access_features(grid, s, g))
        else:
            n, edges, s, g = pr[1], pr[2], pr[3], pr[4]
            exp = dijkstra_value(n, edges, s, g)
            out = res.get("out")
            extra["correct"] = (not isinstance(out, bool)) and isinstance(out, (int, float)) and out == exp
            extra["n"] = n
            extra["lines"] = R.lines
            extra["edges_iter"] = R.edges_iter
            extra["edges_full"] = R.edges_full
            extra["edges_index"] = R.edges_index
            extra["n_edges"] = len(edges)
        result["probes"].append(snapshot(task, extra))
        if th.is_alive():
            result["error"] = "probe_timeout"
            emit()
            os._exit(0)
    emit()


if __name__ == "__main__":
    main()
