"""Runtime tracer (primary labeller). Runs INSIDE the sandboxed harness subprocess.

Instruments heapq / collections.deque / queue.* before the candidate code is executed, then calls the candidate
solve() on crafted inputs while recording container traffic, grid-cell reads (T1), edge-list passes (T2), the call
depth of candidate functions (recursion), builtin min() calls and line events (growth exponent). The recorded
features are mapped to one catalogue label by explicit, ordered signature rules; None means 'unresolved' and the
caller falls back to the AST label.
"""

from __future__ import annotations

import builtins
import collections
import heapq
import math
import queue
import random
import signal
import sys

CAND_FILE = "<candidate>"
MAX_ITEMS = 6000
MAX_READS = 40000


class TraceTimeout(BaseException):
    """Raised by SIGALRM inside candidate code; BaseException so `except Exception` cannot swallow it."""


class Rec:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.on = False
        self.heap_push = 0
        self.heap_pop = 0
        self.heap_ids: dict[int, int] = {}
        self.heap_items: list = []
        self.deques: dict[int, dict] = {}
        self.deque_items: list = []
        self.q = {"fifo_put": 0, "fifo_get": 0, "lifo_put": 0, "lifo_get": 0, "pq_put": 0, "pq_get": 0}
        self.q_ids: dict[int, int] = {}
        self.pq_items: list = []
        self.reads: list = []
        self.edge_iters = 0
        self.edge_getitem = 0
        self.depth = 0
        self.max_depth = 0
        self.code_depth: dict = {}
        self.self_rec_max = 0
        self.top_calls: dict[str, int] = {}
        self.lines = 0
        self.min_calls = 0

    def dq(self, d, op: str, x=None) -> None:
        st = self.deques.get(id(d))
        if st is None:
            st = {"append": 0, "appendleft": 0, "pop": 0, "popleft": 0}
            self.deques[id(d)] = st
        st[op] += 1
        if x is not None and op in ("append", "appendleft") and len(self.deque_items) < MAX_ITEMS:
            self.deque_items.append((id(d), x))


REC = Rec()

# --------------------------------------------------------------------------- instrumentation
_orig = {
    "heappush": heapq.heappush, "heappop": heapq.heappop, "heappushpop": heapq.heappushpop,
    "heapreplace": heapq.heapreplace, "heapify": heapq.heapify,
}


def _hp_push(h, item):
    if REC.on:
        REC.heap_push += 1
        REC.heap_ids[id(h)] = REC.heap_ids.get(id(h), 0) + 1
        if len(REC.heap_items) < MAX_ITEMS:
            REC.heap_items.append((id(h), item))
    return _orig["heappush"](h, item)


def _hp_pop(h):
    if REC.on:
        REC.heap_pop += 1
    return _orig["heappop"](h)


def _hp_pushpop(h, item):
    if REC.on:
        REC.heap_push += 1
        REC.heap_pop += 1
        REC.heap_ids[id(h)] = REC.heap_ids.get(id(h), 0) + 1
        if len(REC.heap_items) < MAX_ITEMS:
            REC.heap_items.append((id(h), item))
    return _orig["heappushpop"](h, item)


def _hp_replace(h, item):
    if REC.on:
        REC.heap_push += 1
        REC.heap_pop += 1
        REC.heap_ids[id(h)] = REC.heap_ids.get(id(h), 0) + 1
        if len(REC.heap_items) < MAX_ITEMS:
            REC.heap_items.append((id(h), item))
    return _orig["heapreplace"](h, item)


def _hp_heapify(h):
    return _orig["heapify"](h)


_Deque = collections.deque


class RecDeque(_Deque):
    def append(self, x):
        if REC.on:
            REC.dq(self, "append", x)
        return _Deque.append(self, x)

    def appendleft(self, x):
        if REC.on:
            REC.dq(self, "appendleft", x)
        return _Deque.appendleft(self, x)

    def pop(self):
        if REC.on:
            REC.dq(self, "pop")
        return _Deque.pop(self)

    def popleft(self):
        if REC.on:
            REC.dq(self, "popleft")
        return _Deque.popleft(self)

    def extend(self, it):
        it = list(it)
        if REC.on:
            for x in it:
                REC.dq(self, "append", x)
        return _Deque.extend(self, it)


def _make_q(base, kind):
    class _Q(base):
        def put(self, item, block=True, timeout=None):
            if REC.on:
                REC.q[f"{kind}_put"] += 1
                REC.q_ids[id(self)] = REC.q_ids.get(id(self), 0) + 1
                if kind == "pq" and len(REC.pq_items) < MAX_ITEMS:
                    REC.pq_items.append((id(self), item))
                if kind == "fifo" and len(REC.deque_items) < MAX_ITEMS:
                    REC.deque_items.append((id(self), item))
            return base.put(self, item, block, timeout)

        def get(self, block=True, timeout=None):
            if REC.on:
                REC.q[f"{kind}_get"] += 1
            return base.get(self, block, timeout)

    _Q.__name__ = base.__name__
    _Q.__qualname__ = base.__qualname__
    return _Q


_installed = False


def install() -> None:
    global _installed
    if _installed:
        return
    heapq.heappush = _hp_push
    heapq.heappop = _hp_pop
    heapq.heappushpop = _hp_pushpop
    heapq.heapreplace = _hp_replace
    heapq.heapify = _hp_heapify
    collections.deque = RecDeque
    queue.Queue = _make_q(queue.Queue, "fifo")
    queue.LifoQueue = _make_q(queue.LifoQueue, "lifo")
    queue.PriorityQueue = _make_q(queue.PriorityQueue, "pq")
    _installed = True


# --------------------------------------------------------------------------- tracked inputs
class TRow(str):
    def __new__(cls, s: str, r: int):
        obj = str.__new__(cls, s)
        obj._r = r
        return obj

    def __getitem__(self, c):
        if REC.on and isinstance(c, int) and len(REC.reads) < MAX_READS:
            REC.reads.append((self._r, c if c >= 0 else c + len(self)))
        return str.__getitem__(self, c)


class TEdges(list):
    def __iter__(self):
        if REC.on:
            REC.edge_iters += 1
        return list.__iter__(self)

    def __getitem__(self, i):
        if REC.on:
            REC.edge_getitem += 1
        return list.__getitem__(self, i)


# --------------------------------------------------------------------------- profiling hooks
def _prof(frame, event, arg):
    if event == "call":
        code = frame.f_code
        if code.co_filename == CAND_FILE:
            REC.depth += 1
            if REC.depth > REC.max_depth:
                REC.max_depth = REC.depth
            cnt = REC.code_depth.get(code, 0) + 1
            REC.code_depth[code] = cnt
            if cnt > REC.self_rec_max:
                REC.self_rec_max = cnt
            if cnt == 1:
                REC.top_calls[code.co_name] = REC.top_calls.get(code.co_name, 0) + 1
    elif event == "return":
        code = frame.f_code
        if code.co_filename == CAND_FILE:
            REC.depth -= 1
            REC.code_depth[code] = REC.code_depth.get(code, 1) - 1
    elif event == "c_call":
        if arg is builtins.min and frame.f_code.co_filename == CAND_FILE:
            REC.min_calls += 1


def _ltrace(frame, event, arg):
    if event == "line":
        REC.lines += 1
    return _ltrace


def _gtrace(frame, event, arg):
    if frame.f_code.co_filename == CAND_FILE:
        return _ltrace
    return None


def _on_alarm(signum, frame):
    raise TraceTimeout()


def run_traced(fn, args: tuple, time_limit: float, lines: bool = False) -> dict:
    """Call fn(*args) with recording on; returns a snapshot of the recorder (kept even on timeout/crash)."""
    REC.reset()
    old = signal.signal(signal.SIGALRM, _on_alarm)
    status = "ok"
    out = None
    try:
        signal.setitimer(signal.ITIMER_REAL, time_limit)
        sys.setprofile(_prof)
        if lines:
            sys.settrace(_gtrace)
        REC.on = True
        out = fn(*args)
    except TraceTimeout:
        status = "timeout"
    except RecursionError:
        status = "recursion_error"
    except BaseException as e:  # noqa: BLE001 - candidate code may raise anything
        status = f"error:{type(e).__name__}"
    finally:
        REC.on = False
        sys.setprofile(None)
        sys.settrace(None)
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)
    snap = {k: getattr(REC, k) for k in (
        "heap_push", "heap_pop", "heap_ids", "heap_items", "deques", "deque_items", "q", "q_ids", "pq_items",
        "reads", "edge_iters", "edge_getitem", "max_depth", "self_rec_max", "top_calls", "lines", "min_calls")}
    snap = dict(snap)
    snap["status"] = status
    snap["out"] = out
    return snap


# --------------------------------------------------------------------------- helpers
def _first_num(x, depth=0):
    if isinstance(x, bool):
        return None
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, (tuple, list)) and x and depth < 2:
        return _first_num(x[0], depth + 1)
    return None


def _is_cell(x) -> bool:
    return (isinstance(x, (tuple, list)) and len(x) == 2 and all(isinstance(v, int) and not isinstance(v, bool)
                                                                  for v in x))


def _find_cell(item, depth=0):
    if _is_cell(item):
        return tuple(item)
    if isinstance(item, (tuple, list)) and depth < 3:
        for el in item:
            c = _find_cell(el, depth + 1)
            if c is not None:
                return c
        ints = [v for v in item if isinstance(v, int) and not isinstance(v, bool)]
        if len(ints) >= 3 and isinstance(item[-1], int) and isinstance(item[-2], int):
            return (item[-2], item[-1])
    return None


def _node_of(item):
    if isinstance(item, bool):
        return None
    if isinstance(item, int):
        return item
    if isinstance(item, (tuple, list)) and item:
        ints = [v for v in item if isinstance(v, int) and not isinstance(v, bool)]
        if ints:
            return ints[-1]
    return None


def _spearman(a: list, b: list) -> float:
    n = len(a)
    if n < 5:
        return float("nan")

    def ranks(v):
        order = sorted(range(n), key=lambda i: v[i])
        r = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2.0
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r

    ra, rb = ranks(a), ranks(b)
    ma, mb = sum(ra) / n, sum(rb) / n
    cov = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    va = math.sqrt(sum((x - ma) ** 2 for x in ra))
    vb = math.sqrt(sum((y - mb) ** 2 for y in rb))
    if va == 0 or vb == 0:
        return float("nan")
    return cov / (va * vb)


def _lstsq3(rows: list[tuple[float, float, float]]):
    """Least squares p = a*x + b*y + c; returns (a, b, c) or None if rank deficient."""
    n = len(rows)
    if n < 6:
        return None
    sx = sy = sp = sxx = syy = sxy = sxp = syp = 0.0
    for x, y, p in rows:
        sx += x; sy += y; sp += p
        sxx += x * x; syy += y * y; sxy += x * y
        sxp += x * p; syp += y * p
    m = [[sxx, sxy, sx], [sxy, syy, sy], [sx, sy, float(n)]]
    v = [sxp, syp, sp]
    # Gaussian elimination
    for i in range(3):
        piv = max(range(i, 3), key=lambda r: abs(m[r][i]))
        if abs(m[piv][i]) < 1e-9:
            return None
        m[i], m[piv] = m[piv], m[i]
        v[i], v[piv] = v[piv], v[i]
        for r in range(3):
            if r != i:
                f = m[r][i] / m[i][i]
                for c in range(3):
                    m[r][c] -= f * m[i][c]
                v[r] -= f * v[i]
    return tuple(v[i] / m[i][i] for i in range(3))


# --------------------------------------------------------------------------- T1 crafted inputs + rules
def _t1_inputs() -> dict:
    open15 = ["." * 15 for _ in range(15)]
    rng = random.Random(7)
    k = 7
    n = 2 * k + 1
    g = [["#"] * n for _ in range(n)]
    st = [(1, 1)]
    g[1][1] = "."
    while st:
        r, c = st[-1]
        nb = [(r + dr, c + dc, r + dr // 2, c + dc // 2) for dr, dc in ((2, 0), (-2, 0), (0, 2), (0, -2))
              if 0 < r + dr < n and 0 < c + dc < n and g[r + dr][c + dc] == "#"]
        if not nb:
            st.pop()
            continue
        nr, nc, wr, wc = rng.choice(nb)
        g[wr][wc] = "."
        g[nr][nc] = "."
        st.append((nr, nc))
    maze = ["".join(row) for row in g]
    open11 = ["." * 11 for _ in range(11)]
    return {
        "O1": (open15, (0, 0), (14, 14)),
        "O2": (open15, (7, 1), (7, 13)),
        "M": (maze, (1, 1), (n - 2, n - 2)),
        "D": (open11, (5, 2), (5, 8)),
    }


def _bfs_d(grid, start):
    R, C = len(grid), len(grid[0])
    d = {start: 0}
    q = _Deque([start])
    while q:
        r, c = q.popleft()
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < R and 0 <= nc < C and grid[nr][nc] == "." and (nr, nc) not in d:
                d[(nr, nc)] = d[(r, c)] + 1
                q.append((nr, nc))
    return d


def _t1_features(snap: dict, grid, start, goal) -> dict:
    ds = _bfs_d(grid, start)
    f: dict = {"status": snap["status"]}
    f["heap_push"] = snap["heap_push"] + snap["q"]["pq_put"]
    f["n_heaps"] = sum(1 for v in snap["heap_ids"].values() if v >= 3) + sum(
        1 for i, v in snap["q_ids"].items() if v >= 3 and any(qi == i for qi, _ in snap["pq_items"][:50]))
    fifo_deques = [st for st in snap["deques"].values() if st["popleft"] >= 3]
    f["n_fifo_deques"] = len(fifo_deques)
    f["fifo_pops"] = sum(st["popleft"] for st in snap["deques"].values()) + snap["q"]["fifo_get"]
    f["lifo_pops"] = sum(st["pop"] for st in snap["deques"].values()) + snap["q"]["lifo_get"]
    f["self_rec_max"] = snap["self_rec_max"]
    f["top_calls_max_rec"] = 0
    f["n_reads"] = len(snap["reads"])
    # first-read order
    first: dict = {}
    counts: dict = {}
    for i, cell in enumerate(snap["reads"]):
        counts[cell] = counts.get(cell, 0) + 1
        if cell not in first:
            first[cell] = i
    f["n_cells_read"] = len(first)
    cells = [c for c in first if c in ds]
    if len(cells) >= 8:
        order = [first[c] for c in cells]
        dist = [ds[c] for c in cells]
        f["spearman_ring"] = _spearman(order, dist)
    else:
        f["spearman_ring"] = float("nan")
    dg = ds.get(tuple(goal))
    if dg is not None and dg >= 4:
        inner = [c for c in ds if ds[c] <= dg - 2]
        f["coverage"] = sum(1 for c in inner if c in first) / max(1, len(inner))
    else:
        f["coverage"] = float("nan")
    near_start = [counts[c] for c in counts if c in ds and ds[c] <= 1]
    f["max_reread_near_start"] = max(near_start) if near_start else 0
    f["max_reread_any"] = max(counts.values()) if counts else 0
    # bidirectional: cells adjacent to goal (not the goal) first read within the first 20% of reads
    total = len(snap["reads"])
    near_goal = [first[c] for c in first if abs(c[0] - goal[0]) + abs(c[1] - goal[1]) == 1]
    f["near_goal_early"] = bool(total >= 20 and near_goal and min(near_goal) < 0.2 * total and
                                abs(start[0] - goal[0]) + abs(start[1] - goal[1]) >= 8)
    # heap priority regression p = a*d_start + b*d_goal + c
    rows = []
    items = snap["heap_items"] + snap["pq_items"]
    for _, item in items:
        p = _first_num(item)
        cell = _find_cell(item[1:] if isinstance(item, (tuple, list)) and len(item) > 1 else item)
        if p is None or cell is None or cell not in ds:
            continue
        rows.append((float(ds[cell]), float(abs(cell[0] - goal[0]) + abs(cell[1] - goal[1])), p))
    f["n_prio_rows"] = len(rows)
    reg = _lstsq3(rows)
    f["prio_a"], f["prio_b"] = (reg[0], reg[1]) if reg else (None, None)
    return f


def classify_t1(feats: dict) -> tuple[str | None, str]:
    """Ordered signature rules. Returns (label or None, rule name)."""
    o2 = feats.get("O2") or {}
    o1 = feats.get("O1") or {}
    allf = [feats[k] for k in ("O2", "O1", "M", "D") if feats.get(k)]
    if not allf:
        return None, "no_trace"
    heap = max(f.get("heap_push", 0) for f in allf)
    n_heaps = max(f.get("n_heaps", 0) for f in allf)
    n_fifo_dq = max(f.get("n_fifo_deques", 0) for f in allf)
    fifo = sum(f.get("fifo_pops", 0) for f in allf)
    lifo = sum(f.get("lifo_pops", 0) for f in allf)
    rec = max(f.get("self_rec_max", 0) for f in allf)
    reread = max(o1.get("max_reread_near_start", 0), o2.get("max_reread_near_start", 0))
    bidir_reads = bool(o2.get("near_goal_early")) or bool(o1.get("near_goal_early"))
    if n_heaps >= 2 or n_fifo_dq >= 2 or bidir_reads:
        return "bidirectional_BFS", "two_frontiers"
    if heap >= 3:
        for f in (o2, o1, feats.get("D") or {}):
            if f.get("prio_b") is not None:
                return ("astar_greedy", "heap_prio_goal") if f["prio_b"] > 0.3 else ("unit_dijkstra", "heap_prio_len")
        return None, "heap_no_prio"
    if reread >= 12:
        return "IDDFS", "rereads_start"
    if fifo >= 3 and fifo >= lifo:
        return "BFS", "fifo"
    if lifo >= 3 or rec >= 5:
        return "DFS", "lifo_or_recursion"
    sp = o2.get("spearman_ring", float("nan"))
    if sp != sp:
        sp = o1.get("spearman_ring", float("nan"))
    cov = o2.get("coverage", float("nan"))
    if cov != cov:
        cov = o1.get("coverage", float("nan"))
    if sp == sp and max(f.get("n_reads", 0) for f in allf) >= 20:
        if sp >= 0.85 and cov == cov and cov >= 0.9:
            return "BFS", "ring_order"
        return "DFS", "non_ring_order"
    return None, "unresolved"


def trace_t1(solve, time_limit: float = 2.0) -> dict:
    out: dict = {"inputs": {}}
    for name, (grid, s, g) in _t1_inputs().items():
        tgrid = [TRow(row, r) for r, row in enumerate(grid)]
        snap = run_traced(solve, (tgrid, s, g), time_limit)
        out["inputs"][name] = _t1_features(snap, grid, s, g)
    lab, rule = classify_t1(out["inputs"])
    out["runtime_label"], out["rule"] = lab, rule
    return out


# --------------------------------------------------------------------------- T2 crafted inputs + rules
def _t2_graph(n: int, seed: int):
    rng = random.Random(seed)
    edges = [(i, i + 1, 50) for i in range(n - 1)]
    edges += [(rng.randrange(n), rng.randrange(n), rng.randint(1, 20)) for _ in range(4 * n)]
    rng.shuffle(edges)
    return edges


def trace_t2(solve, time_limit: float = 2.0) -> dict:
    out: dict = {"inputs": {}}
    lines = {}
    for n in (10, 20, 40):
        edges = _t2_graph(n, 100 + n)
        snap = run_traced(solve, (n, TEdges(edges), 0, n - 1), time_limit, lines=True)
        m = len(edges)
        dq_nodes: dict = {}
        for did, item in snap["deque_items"]:
            node = _node_of(item)
            if node is not None:
                dq_nodes[(did, node)] = dq_nodes.get((did, node), 0) + 1
        f = {
            "status": snap["status"],
            "heap_push": snap["heap_push"] + snap["q"]["pq_put"],
            "n_heaps": sum(1 for v in snap["heap_ids"].values() if v >= 3),
            "fifo_pops": sum(st["popleft"] for st in snap["deques"].values()) + snap["q"]["fifo_get"],
            "lifo_pops": sum(st["pop"] for st in snap["deques"].values()) + snap["q"]["lifo_get"],
            "appendleft": sum(st["appendleft"] for st in snap["deques"].values()),
            "reenqueue": sum(1 for v in dq_nodes.values() if v >= 2),
            "edge_passes": snap["edge_iters"] + snap["edge_getitem"] / max(1, m),
            "self_rec_max": snap["self_rec_max"],
            "min_calls": snap["min_calls"],
            "lines": snap["lines"],
        }
        out["inputs"][f"G{n}"] = f
        if snap["status"] == "ok":
            lines[n] = max(1, snap["lines"])
    # re-enqueue provoking graph
    re_edges = [(0, 1, 1), (1, 2, 1), (2, 3, 1), (0, 3, 10), (3, 4, 1)]
    snap = run_traced(solve, (5, TEdges(re_edges), 0, 4), time_limit)
    dq_nodes = {}
    for did, item in snap["deque_items"]:
        node = _node_of(item)
        if node is not None:
            dq_nodes[(did, node)] = dq_nodes.get((did, node), 0) + 1
    out["inputs"]["RE"] = {"status": snap["status"], "reenqueue": sum(1 for v in dq_nodes.values() if v >= 2),
                           "fifo_pops": sum(st["popleft"] for st in snap["deques"].values()) + snap["q"]["fifo_get"]}
    if len(lines) >= 2:
        xs = [math.log(k) for k in sorted(lines)]
        ys = [math.log(lines[k]) for k in sorted(lines)]
        mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
        den = sum((x - mx) ** 2 for x in xs)
        out["exponent"] = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den if den else None
    else:
        out["exponent"] = None
    lab, rule = classify_t2(out)
    out["runtime_label"], out["rule"] = lab, rule
    return out


def classify_t2(tr: dict) -> tuple[str | None, str]:
    ins = tr["inputs"]
    g = ins.get("G40") or ins.get("G20") or ins.get("G10")
    if g is None:
        return None, "no_trace"
    allg = [ins[k] for k in ("G10", "G20", "G40") if k in ins]
    timeouts = [k for k in ("G10", "G20", "G40") if ins.get(k, {}).get("status") == "timeout"]
    heap = max(f["heap_push"] for f in allg)
    n_heaps = max(f["n_heaps"] for f in allg)
    fifo = max(f["fifo_pops"] for f in allg)
    reenq = max([f["reenqueue"] for f in allg] + [ins.get("RE", {}).get("reenqueue", 0)])
    passes = max(f["edge_passes"] for f in allg)
    rec = max(f["self_rec_max"] for f in allg)
    expo = tr.get("exponent")
    if n_heaps >= 2:
        return "bidirectional_dijkstra", "two_heaps"
    if heap >= 3:
        return "dijkstra", "heap"
    if fifo >= 3 and reenq >= 1 and max(f["appendleft"] for f in allg) == 0:
        return "bellman_ford_spfa", "fifo_reenqueue"
    if timeouts or rec >= 3:
        return None, "timeout_or_recursion"
    if expo is not None and expo >= 2.6:
        return "floyd_warshall", "cubic"
    if g["min_calls"] >= 10:
        return "dijkstra", "min_scan"
    if passes >= 2:
        return "bellman_ford_spfa", "multi_edge_pass"
    return None, "unresolved"
