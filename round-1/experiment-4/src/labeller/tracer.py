#!/usr/bin/env python3
"""Runtime tracer: instrumented containers / heaps / queues + sys.setprofile, run on 3 probe inputs.

Inside the sandbox (labeller/runner.py) `install()` replaces heapq, collections, queue and bisect in
sys.modules and `transform()` rewrites every list display / list comprehension / list() call of the
candidate into a traced list subclass. `features()` summarises the events per probe; `runtime_label()`
(parent side) applies the pre-registered first-match rules. Standard library only.
"""
from __future__ import annotations

import ast
import bisect as _real_bisect
import collections as _real_collections
import heapq as _real_heapq
import queue as _real_queue
import sys
import types

MAX_EVENTS = 300000
MAX_TRACKED = 60000


def _is_num(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


class Recorder:
    def __init__(self):
        self.reset_all()

    def reset_all(self):
        self.task = "T1"
        self.R = self.C = self.n = 0
        self.start = self.goal = None
        self.probe = "module"
        self.cont = {}        # id -> info
        self.refs = []        # strong refs so ids stay unique within a run
        self.heaps = {}       # id -> {"pushes": [...], "pops": [...]}
        self.heap_seq = []    # ordered ("push"/"pop", heap_id, priority, key)
        self.push_seq = []    # ordered (container_id, key) for non-heap pushes
        self.calls = {}
        self.self_calls = {}
        self.start_calls = []
        self.edges_iters = 0
        self.edges_getitem = 0
        self.bisect_calls = 0
        self.events = 0
        self.iters = {}       # id -> number of full iterations of a traced list (adjacency passes)

    # ---- key extraction -------------------------------------------------
    def is_cell(self, x) -> bool:
        return (isinstance(x, (tuple, list)) and len(x) == 2 and type(x[0]) is int and type(x[1]) is int
                and 0 <= x[0] < self.R and 0 <= x[1] < self.C)

    def cell_of(self, item, depth: int = 0):
        if self.is_cell(item):
            return (item[0], item[1])
        if depth < 3 and isinstance(item, (tuple, list)) and len(item) < 64:
            for x in item:
                if self.is_cell(x):
                    return (x[0], x[1])
            if (len(item) >= 2 and type(item[0]) is int and type(item[1]) is int and 0 <= item[0] < self.R
                    and 0 <= item[1] < self.C):
                return (item[0], item[1])
            for x in item:
                if isinstance(x, (tuple, list)):
                    c = self.cell_of(x, depth + 1)
                    if c is not None:
                        return c
        return None

    def key_of(self, item):
        if self.task == "T1":
            return self.cell_of(item)
        if type(item) is int and 0 <= item < self.n:
            return item
        if isinstance(item, (tuple, list)):
            for x in item[:4]:  # first int in node range; Q2 distances are >= 10 > n-1, so they never collide
                if type(x) is int and 0 <= x < self.n:
                    return x
        return None

    def heap_pk(self, item):
        """(priority, key) of a heap item."""
        if _is_num(item):
            return item, None
        if not (isinstance(item, (tuple, list)) and len(item) >= 2 and _is_num(item[0])):
            return None, None
        p, rest = item[0], item[1:]
        if self.task == "T2":
            k = rest[0] if type(rest[0]) is int else None
            return p, k
        for x in rest:
            if self.is_cell(x):
                return p, (x[0], x[1])
        if (len(rest) >= 2 and type(rest[-2]) is int and type(rest[-1]) is int and 0 <= rest[-2] < self.R
                and 0 <= rest[-1] < self.C):
            return p, (rest[-2], rest[-1])
        for x in rest:
            if isinstance(x, (tuple, list)):
                c = self.cell_of(x, 1)
                if c is not None:
                    return p, c
        return p, None

    # ---- events --------------------------------------------------------
    def _info(self, obj, kind: str):
        i = id(obj)
        if i not in self.cont:
            if len(self.refs) >= MAX_TRACKED:
                return None
            self.refs.append(obj)
            self.cont[i] = {"kind": kind, "probe": self.probe, "first": None, "push_back": 0, "push_front": 0,
                            "push_mid": 0, "pop_back": 0, "pop_front": 0, "pop_mid": 0, "keys": [],
                            "pop_keys": []}
        return self.cont[i]

    def on_init(self, obj, kind: str, items):
        if self.events > MAX_EVENTS:
            return
        info = self._info(obj, kind)
        if info is not None and items:
            info["first"] = self.key_of(items[0])

    def push(self, obj, end: str, x, kind: str = "list"):
        self.events += 1
        if self.events > MAX_EVENTS:
            return
        info = self._info(obj, kind)
        if info is None:
            return
        info["push_" + end] += 1
        k = self.key_of(x)
        if info["first"] is None and not info["keys"]:
            info["first"] = k
        if len(info["keys"]) < 4000:
            info["keys"].append(k)
        if k is not None and len(self.push_seq) < 20000:
            self.push_seq.append((id(obj), k))

    def pop(self, obj, end: str, x, kind: str = "list"):
        self.events += 1
        if self.events > MAX_EVENTS:
            return
        info = self._info(obj, kind)
        if info is None:
            return
        info["pop_" + end] += 1
        if len(info["pop_keys"]) < 4000:
            info["pop_keys"].append(self.key_of(x))

    def heap(self, op: str, h, item):
        self.events += 1
        if self.events > MAX_EVENTS:
            return
        i = id(h)
        if i not in self.heaps:
            self.refs.append(h)
            self.heaps[i] = {"probe": self.probe, "pushes": 0, "pops": 0}
        p, k = self.heap_pk(item) if item is not None else (None, None)
        self.heaps[i]["pushes" if op == "push" else "pops"] += 1
        if len(self.heap_seq) < 40000:
            self.heap_seq.append((op, i, p, k))

    def on_call(self, frame):
        self.events += 1
        if self.events > MAX_EVENTS:
            return
        co = frame.f_code
        name = co.co_name
        self.calls[name] = self.calls.get(name, 0) + 1
        back = frame.f_back
        same = back is not None and back.f_code is co
        if same:
            self.self_calls[name] = self.self_calls.get(name, 0) + 1
        if self.task == "T1" and self.start is not None:
            try:
                loc = frame.f_locals
                vals = [loc.get(v) for v in co.co_varnames[:co.co_argcount]]
            except Exception:  # noqa: BLE001 - frame introspection must never break the candidate
                return
            hit = False
            for v in vals:
                if self.is_cell(v) and (v[0], v[1]) == self.start:
                    hit = True
                    break
            if not hit:
                for a, b in zip(vals, vals[1:]):
                    if type(a) is int and type(b) is int and (a, b) == self.start:
                        hit = True
                        break
            if hit and len(self.start_calls) < 10000:
                self.start_calls.append((name, same))


REC = Recorder()


class TL(list):
    """Traced list: records appends / inserts / pops (heapq's C functions bypass these methods)."""

    def __init__(self, *a):
        super().__init__(*a)
        if len(self):
            REC.on_init(self, "list", list.__getitem__(self, slice(0, 1)))

    def append(self, x):
        REC.push(self, "back", x)
        list.append(self, x)

    def insert(self, i, x):
        n = len(self)
        REC.push(self, "front" if i == 0 or i <= -n else ("back" if i >= n else "mid"), x)
        list.insert(self, i, x)

    def extend(self, it):
        it = list(it)
        for x in it:
            REC.push(self, "back", x)
        list.extend(self, it)

    def __iadd__(self, it):
        self.extend(it)
        return self

    def __iter__(self):
        i = id(self)
        if REC.events <= MAX_EVENTS:
            if i not in REC.iters and len(REC.refs) < MAX_TRACKED:
                REC.refs.append(self)
            REC.iters[i] = REC.iters.get(i, 0) + 1
        return list.__iter__(self)

    def pop(self, *a):
        n = len(self)
        i = a[0] if a else -1
        if i == 0 or (n and i == -n and n > 1):
            end = "front"
        elif i == -1 or i == n - 1:
            end = "back"
        else:
            end = "mid"
        x = list.pop(self, *a)
        REC.pop(self, end, x)
        return x


_RealDeque = _real_collections.deque


class TDeque(_RealDeque):
    def __init__(self, iterable=(), maxlen=None):
        if maxlen is None:
            super().__init__(iterable)
        else:
            super().__init__(iterable, maxlen)
        if len(self):
            REC.on_init(self, "deque", [self[0]])

    def append(self, x):
        REC.push(self, "back", x, "deque")
        _RealDeque.append(self, x)

    def appendleft(self, x):
        REC.push(self, "front", x, "deque")
        _RealDeque.appendleft(self, x)

    def extend(self, it):
        it = list(it)
        for x in it:
            REC.push(self, "back", x, "deque")
        _RealDeque.extend(self, it)

    def extendleft(self, it):
        it = list(it)
        for x in it:
            REC.push(self, "front", x, "deque")
        _RealDeque.extendleft(self, it)

    def pop(self):
        x = _RealDeque.pop(self)
        REC.pop(self, "back", x, "deque")
        return x

    def popleft(self):
        x = _RealDeque.popleft(self)
        REC.pop(self, "front", x, "deque")
        return x


class TQueue(_real_queue.Queue):
    def put(self, item, block=True, timeout=None):
        REC.push(self, "back", item, "queue")
        return super().put(item, block, timeout)

    def get(self, block=True, timeout=None):
        x = super().get(block, timeout)
        REC.pop(self, "front", x, "queue")
        return x


class TLifo(_real_queue.LifoQueue):
    def put(self, item, block=True, timeout=None):
        REC.push(self, "back", item, "lifoq")
        return super().put(item, block, timeout)

    def get(self, block=True, timeout=None):
        x = super().get(block, timeout)
        REC.pop(self, "back", x, "lifoq")
        return x


class TPQ(_real_queue.PriorityQueue):
    def put(self, item, block=True, timeout=None):
        REC.heap("push", self, item)
        return super().put(item, block, timeout)

    def get(self, block=True, timeout=None):
        x = super().get(block, timeout)
        REC.heap("pop", self, x)
        return x


class TEdges(list):
    """Edge list passed to T2 probes: counts full iterations and indexed reads."""

    def __iter__(self):
        REC.edges_iters += 1
        return list.__iter__(self)

    def __getitem__(self, i):
        if type(i) is int:
            REC.edges_getitem += 1
        return list.__getitem__(self, i)


def _clone_module(mod, name: str) -> types.ModuleType:
    m = types.ModuleType(name)
    for k in dir(mod):
        if k in ("__name__", "__loader__", "__spec__"):
            continue
        try:
            setattr(m, k, getattr(mod, k))
        except (AttributeError, TypeError):
            pass
    return m


def install() -> None:
    hq = _clone_module(_real_heapq, "heapq")

    def heappush(h, item):
        REC.heap("push", h, item)
        return _real_heapq.heappush(h, item)

    def heappop(h):
        x = _real_heapq.heappop(h)
        REC.heap("pop", h, x)
        return x

    def heapify(h):
        _real_heapq.heapify(h)
        for x in list.__iter__(h) if isinstance(h, list) else h:
            REC.heap("push", h, x)

    def heappushpop(h, item):
        REC.heap("push", h, item)
        x = _real_heapq.heappushpop(h, item)
        REC.heap("pop", h, x)
        return x

    def heapreplace(h, item):
        x = _real_heapq.heapreplace(h, item)
        REC.heap("pop", h, x)
        REC.heap("push", h, item)
        return x

    hq.heappush, hq.heappop, hq.heapify, hq.heappushpop, hq.heapreplace = (heappush, heappop, heapify,
                                                                              heappushpop, heapreplace)
    col = _clone_module(_real_collections, "collections")
    col.deque = TDeque
    col.__path__ = getattr(_real_collections, "__path__", [])
    qm = _clone_module(_real_queue, "queue")
    qm.Queue, qm.LifoQueue, qm.PriorityQueue = TQueue, TLifo, TPQ
    try:
        class TSimple(_real_queue.SimpleQueue):
            def put(self, item, block=True, timeout=None):
                REC.push(self, "back", item, "queue")
                return super().put(item, block, timeout)

            def get(self, block=True, timeout=None):
                x = super().get(block, timeout)
                REC.pop(self, "front", x, "queue")
                return x
        qm.SimpleQueue = TSimple
    except TypeError:
        pass
    bm = _clone_module(_real_bisect, "bisect")

    def _wrap(fn):
        def w(*a, **k):
            REC.bisect_calls += 1
            return fn(*a, **k)
        return w

    for nm in ("insort", "insort_left", "insort_right"):
        setattr(bm, nm, _wrap(getattr(_real_bisect, nm)))
    sys.modules["heapq"] = hq
    sys.modules["collections"] = col
    sys.modules["queue"] = qm
    sys.modules["bisect"] = bm


class _ListWrap(ast.NodeTransformer):
    def _wrap(self, node):
        return ast.copy_location(ast.Call(func=ast.Name(id="__TL__", ctx=ast.Load()), args=[node], keywords=[]), node)

    def visit_List(self, node):
        self.generic_visit(node)
        if isinstance(node.ctx, ast.Load):
            return self._wrap(node)
        return node

    def visit_ListComp(self, node):
        self.generic_visit(node)
        return self._wrap(node)

    def visit_Call(self, node):
        self.generic_visit(node)
        if isinstance(node.func, ast.Name) and node.func.id == "list":
            node.func = ast.copy_location(ast.Name(id="__TL__", ctx=ast.Load()), node.func)
        return node


def transform(code: str):
    tree = ast.parse(code)
    tree = _ListWrap().visit(tree)
    ast.fix_missing_locations(tree)
    return compile(tree, "<candidate>", "exec")


def profiler(frame, event, arg):
    if event == "call" and frame.f_code.co_filename == "<candidate>":
        REC.on_call(frame)


def setup_probe(task: str, probe: dict) -> None:
    REC.task = task
    REC.probe = probe["id"]
    a = probe["args"]
    if task == "T1":
        REC.R, REC.C = len(a["grid"]), len(a["grid"][0])
        REC.start, REC.goal = tuple(a["start"]), tuple(a["goal"])
    else:
        REC.n = a["n"]
        REC.start, REC.goal = a["s"], a["t"]


def features(task: str, probe: dict, n_edges: int = 0) -> dict:
    """Summarise everything recorded during one probe (call right after the probe ran)."""
    pid = probe["id"]
    conts = [dict(v, cid=k) for k, v in REC.cont.items() if v["probe"] == pid]
    heap_ids = {k for k, v in REC.heaps.items() if v["probe"] == pid and v["pushes"] > 0}
    conts = [c for c in conts if c["cid"] not in heap_ids]
    active = [c for c in conts if (c["pop_back"] + c["pop_front"] + c["pop_mid"]) > 0]
    f: dict = {"probe": pid, "n_heaps_pushed": len(heap_ids), "n_active_containers": len(active),
               "calls": dict(REC.calls), "self_calls": dict(REC.self_calls)}

    def disc(c):
        fifo = min(c["push_back"], c["pop_front"]) + min(c["push_front"], c["pop_back"])
        lifo = min(c["push_back"], c["pop_back"]) + min(c["push_front"], c["pop_front"])
        return "fifo" if fifo > lifo else ("lifo" if lifo > fifo else "none")

    if active:
        main = max(active, key=lambda c: c["pop_back"] + c["pop_front"] + c["pop_mid"])
        f["main"] = {k: main[k] for k in ("kind", "push_back", "push_front", "pop_back", "pop_front", "pop_mid")}
        f["main_discipline"] = disc(main)
    else:
        f["main"], f["main_discipline"] = None, "none"
    f["max_self_calls"] = max(REC.self_calls.values()) if REC.self_calls else 0
    seq = [e for e in REC.heap_seq if e[1] in heap_ids]
    if task == "T1":
        gr, gc = REC.goal
        sr, sc = REC.start

        def h(cell):
            return abs(cell[0] - gr) + abs(cell[1] - gc)

        # top-level searches begun at the start cell (IDDFS signature)
        init_start = sum(1 for c in active if c["first"] == REC.start)
        rec_funcs = {k for k, v in REC.self_calls.items() if v > 0}
        top_calls = sum(1 for (nm, same) in REC.start_calls if nm in rec_funcs and not same)
        f["start_initiations"] = init_start + top_calls
        f["start_initiations_containers"] = init_start
        f["start_initiations_calls"] = top_calls
        # heap priority patterns (parent-relative): A* f = g_parent + 1 + h, greedy f = h, Dijkstra f = g_parent + 1
        last = None
        n_id = a_ok = g_ok = d_ok = 0
        for op, hid, p, k in seq:
            if op == "pop":
                last = (p, k) if (p is not None and k is not None) else None
            elif op == "push" and last is not None and p is not None and k is not None:
                n_id += 1
                pp, pk = last
                if abs(p - (pp - h(pk) + 1 + h(k))) < 1e-9:
                    a_ok += 1
                if abs(p - h(k)) < 1e-9:
                    g_ok += 1
                if abs(p - (pp + 1)) < 1e-9:
                    d_ok += 1
        f.update({"heap_identifiable": n_id, "astar_frac": a_ok / n_id if n_id else 0.0,
                  "greedy_frac": g_ok / n_id if n_id else 0.0, "dijkstra_frac": d_ok / n_id if n_id else 0.0})
        fifo_frontiers = [c for c in active if disc(c) == "fifo" and sum(1 for x in c["keys"] if x is not None) >= 3]
        firsts = {c["first"] for c in fifo_frontiers}
        f["two_fifo_frontiers"] = len(fifo_frontiers) >= 2 and REC.start in firsts and REC.goal in firsts
        cells = [k for (cid, k) in REC.push_seq if cid in {c["cid"] for c in conts}]
        adj = {(gr + 1, gc), (gr - 1, gc), (gr, gc + 1), (gr, gc - 1)}
        cut = max(1, int(0.25 * len(cells) + 0.999))
        f["n_cell_pushes"] = len(cells)
        f["goal_adjacent_early"] = bool(len(cells) >= 8 and any(x in adj for x in cells[:cut]))
    else:
        pops_by_heap: dict = {}
        for op, hid, p, k in seq:
            if op == "pop" and p is not None:
                pops_by_heap.setdefault(hid, []).append(p)
        pairs = ok = 0
        for ps in pops_by_heap.values():
            for a, b in zip(ps, ps[1:]):
                pairs += 1
                ok += b >= a - 1e-9
        f["pop_monotone_frac"] = ok / pairs if pairs else None
        f["heap_pops"] = sum(len(v) for v in pops_by_heap.values())
        reenq = False
        for c in active:
            if disc(c) == "fifo":
                ks = [x for x in c["keys"] if x is not None]
                if len(ks) != len(set(ks)):
                    reenq = True
        f["fifo_reenqueue"] = reenq
        f["edge_passes"] = max(REC.edges_iters, (REC.edges_getitem / n_edges) if n_edges else 0)
        its = sorted(REC.iters.values())
        f["adj_iter_median"] = its[len(its) // 2] if its else 0
        f["adj_iter_max"] = its[-1] if its else 0
        f["n_iterated_lists"] = len(its)
        f["n_bucket_containers"] = sum(1 for c in active if (c["push_back"] + c["push_front"]) > 0)
        f["n_containers_3pops"] = sum(1 for c in active if (c["pop_back"] + c["pop_front"] + c["pop_mid"]) >= 3)
    f["bisect_calls"] = REC.bisect_calls
    return f


def reset_probe_counters() -> None:
    REC.calls, REC.self_calls, REC.start_calls = {}, {}, []
    REC.edges_iters = REC.edges_getitem = REC.bisect_calls = 0
    REC.push_seq = []
    REC.heap_seq = []
    REC.iters = {}
    REC.events = 0


# ------------------------------------------------------------------ parent side rules
def runtime_label(task: str, probes: dict, ast_facts: dict | None = None) -> str:
    """First-match rules over per-probe features; 'unknown' if nothing fires or tracing failed."""
    if not probes:
        return "unknown"
    P = list(probes.values())
    if task == "T1":
        p2 = probes.get("P2")
        if p2 and p2.get("start_initiations", 0) >= 3:
            return "iddfs"
        n_id = sum(p.get("heap_identifiable", 0) for p in P)
        if n_id >= 5:
            def pooled(key):
                return sum(p.get(key, 0) * p.get("heap_identifiable", 0) for p in P) / n_id
            if max(pooled("astar_frac"), pooled("greedy_frac")) >= 0.8:
                return "astar"
            if pooled("dijkstra_frac") >= 0.8:
                return "dijkstra_unit"
        p1 = probes.get("P1")
        if any(p.get("two_fifo_frontiers") for p in P) or (p1 and p1.get("goal_adjacent_early")
                                                           and p1.get("main_discipline") == "fifo"):
            return "bidirectional_bfs"
        discs = [p.get("main_discipline") for p in P if p.get("main_discipline") not in (None, "none")]
        if discs and discs.count("fifo") > len(discs) / 2:
            return "bfs"
        if (discs and discs.count("lifo") > len(discs) / 2) or any(p.get("max_self_calls", 0) >= 3 for p in P):
            return "dfs"
        return "unknown"
    # T2
    if any(p.get("n_heaps_pushed", 0) >= 2 for p in P):
        return "bidirectional_dijkstra"
    if any(p.get("n_heaps_pushed", 0) == 1 for p in P):
        mons = [p["pop_monotone_frac"] for p in P if p.get("pop_monotone_frac") is not None]
        if mons and min(mons) >= 0.95:
            return "dijkstra"
    no_heap = all(p.get("n_heaps_pushed", 0) == 0 for p in P)
    q3 = probes.get("Q3")
    if no_heap and q3 and q3.get("n_bucket_containers", 0) >= 5:
        return "dial"
    q2 = probes.get("Q2")
    # revision round 2: SPFA needs a re-enqueued node to be re-processed (some adjacency list iterated twice)
    if (any(p.get("edge_passes", 0) >= 3 for p in P) or (q3 and q3.get("adj_iter_median", 0) >= 3 and no_heap)
            or (q2 and q2.get("fifo_reenqueue") and q2.get("adj_iter_max", 0) >= 2)):
        return "bellman_ford_spfa"
    no_queue = all(p.get("n_containers_3pops", 0) == 0 for p in P)
    if (no_heap and no_queue and ast_facts and ast_facts.get("fw_pattern")
            and ast_facts.get("loop_depth", 0) >= 3):
        return "floyd_warshall"
    # revision round 2: heap-less (array) Dijkstra - no heap, no queue, every adjacency list processed once
    if no_heap and no_queue and q3 and q3.get("n_iterated_lists", 0) >= 10 and q3.get("adj_iter_max", 0) == 1:
        return "dijkstra"
    return "unknown"
