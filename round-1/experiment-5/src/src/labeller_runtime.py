"""Runtime-signature labeller (STEP 3.3). Executes a program on crafted inputs inside a tracing subprocess and
labels it from what its data structures actually did. Never used for correctness timing.

Subprocess entry: python -I labeller_runtime.py --task tK --code prog.py --out res.json
Library:          label_many(jobs, n_workers) -> list of {key, label, features}

Instrumentation (installed before the program is exec'd):
  * heapq.heappush/heappop/heapify/heappushpop/heapreplace and queue.heappush/heappop: recording wrappers.
  * collections.deque -> TracedDeque (append/appendleft/pop/popleft per object); queue.Queue therefore uses it.
  * queue.LifoQueue._get recorded as a LIFO pop.  list.pop() vs list.pop(0) inferred through sys.setprofile c_call
    / c_return events (first/last element identity before vs after the call).
  * sys.setprofile also tracks per-code-object recursion depth for functions compiled from '<solution>'.
  * T1: grid passed as TracedGrid(list) of TracedRow(str); every in-bounds cell read (r, c) is logged.
  * T2: edges passed as TracedEdges(list) that counts element accesses (full passes over the edge list);
    sys.settrace counts line events in '<solution>' frames (cap 5M) for the asymptotic exponent.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
import threading
from collections import deque as _RealDeque

_HERE = os.path.dirname(os.path.abspath(__file__))
LINE_CAP = 5_000_000


# ============================================================================================ instrumentation
class Rec:
    heap_ops: list = []          # (op, heap_id, item)
    deque_ops: dict = {}         # id -> {"append":n,"appendleft":n,"pop":n,"popleft":n,"vals":[...]}
    list_pops: dict = {}         # id -> {"front": n, "back": n}
    list_vals: dict = {}         # id -> appended values (plain lists)
    lifo_q_pops: int = 0
    cell_reads: list = []
    depth_max: int = 0
    edge_access: int = 0
    lines: int = 0


def _dq_entry(obj) -> dict:
    d = Rec.deque_ops.get(id(obj))
    if d is None:
        d = {"append": 0, "appendleft": 0, "pop": 0, "popleft": 0, "vals": []}
        Rec.deque_ops[id(obj)] = d
    return d


def _freeze(x):
    try:
        hash(x)
        return x
    except TypeError:
        if isinstance(x, list):
            return tuple(_freeze(i) for i in x)
        return repr(x)


class TracedDeque(_RealDeque):
    def append(self, x):
        e = _dq_entry(self)
        e["append"] += 1
        if len(e["vals"]) < 20000:
            e["vals"].append(_freeze(x))
        return _RealDeque.append(self, x)

    def appendleft(self, x):
        e = _dq_entry(self)
        e["appendleft"] += 1
        if len(e["vals"]) < 20000:
            e["vals"].append(_freeze(x))
        return _RealDeque.appendleft(self, x)

    def pop(self):
        _dq_entry(self)["pop"] += 1
        return _RealDeque.pop(self)

    def popleft(self):
        _dq_entry(self)["popleft"] += 1
        return _RealDeque.popleft(self)

    def extend(self, it):
        for x in it:
            self.append(x)

    def extendleft(self, it):
        for x in it:
            self.appendleft(x)


def install_patches() -> None:
    import collections
    import heapq
    collections.deque = TracedDeque
    orig = {k: getattr(heapq, k) for k in ("heappush", "heappop", "heapify", "heappushpop", "heapreplace")}

    def w_push(h, item):
        Rec.heap_ops.append(("push", id(h), item))
        return orig["heappush"](h, item)

    def w_pop(h):
        item = orig["heappop"](h)
        Rec.heap_ops.append(("pop", id(h), item))
        return item

    def w_heapify(h):
        for it in h:
            Rec.heap_ops.append(("push", id(h), it))
        return orig["heapify"](h)

    def w_pushpop(h, item):
        Rec.heap_ops.append(("push", id(h), item))
        r = orig["heappushpop"](h, item)
        Rec.heap_ops.append(("pop", id(h), r))
        return r

    def w_replace(h, item):
        r = orig["heapreplace"](h, item)
        Rec.heap_ops.append(("pop", id(h), r))
        Rec.heap_ops.append(("push", id(h), item))
        return r

    heapq.heappush, heapq.heappop, heapq.heapify = w_push, w_pop, w_heapify
    heapq.heappushpop, heapq.heapreplace = w_pushpop, w_replace
    import queue  # imported after deque patch: queue.Queue's internal deque is a TracedDeque
    queue.heappush, queue.heappop = w_push, w_pop
    queue.deque = TracedDeque
    _lifo_get = queue.LifoQueue._get

    def lifo_get(self):
        Rec.lifo_q_pops += 1
        return _lifo_get(self)

    queue.LifoQueue._get = lifo_get


def make_profiler():
    active: dict = {}
    pending: list = []

    def prof(frame, event, arg):
        if event == "call":
            co = frame.f_code
            if co.co_filename == "<solution>":
                n = active.get(co, 0) + 1
                active[co] = n
                if n > Rec.depth_max:
                    Rec.depth_max = n
        elif event == "return":
            co = frame.f_code
            if co.co_filename == "<solution>" and active.get(co, 0) > 0:
                active[co] -= 1
        elif event == "c_call":
            if getattr(arg, "__name__", None) == "pop":
                lst = getattr(arg, "__self__", None)
                if type(lst) is list and frame.f_code.co_filename == "<solution>":
                    if lst:
                        pending.append((lst, len(lst), id(lst[0]), lst[0] if len(lst) else None, id(lst[-1])))
                    else:
                        pending.append((lst, 0, None, None, None))
        elif event == "c_return" and getattr(arg, "__name__", None) == "append":
            lst = getattr(arg, "__self__", None)
            if type(lst) is list and lst and frame.f_code.co_filename == "<solution>":
                e = Rec.list_vals.setdefault(id(lst), [])
                if len(e) < 20000:
                    e.append(_freeze(lst[-1]))
        if event in ("c_return", "c_exception"):
            if getattr(arg, "__name__", None) == "pop" and pending:
                lst = getattr(arg, "__self__", None)
                if pending and pending[-1][0] is lst:
                    _, n0, id_first, first_obj, id_last = pending.pop()
                    if event == "c_return" and n0 > 0 and len(lst) == n0 - 1:
                        e = Rec.list_pops.setdefault(id(lst), {"front": 0, "back": 0})
                        # pop() keeps the first element in place; pop(0) removes it
                        if n0 == 1:
                            e["back"] += 1
                        elif id(lst[0]) != id_first:
                            e["front"] += 1
                        else:
                            e["back"] += 1
        return None

    return prof


# ============================================================================================ traced inputs
class TracedRow(str):
    def __new__(cls, s, r, ncols):
        o = str.__new__(cls, s)
        o._r = r
        o._nc = ncols
        return o

    def __getitem__(self, idx):
        if type(idx) is int:
            c = idx
            if 0 <= c < self._nc:
                Rec.cell_reads.append((self._r, c))
        return str.__getitem__(self, idx)


class TracedGrid(list):
    pass


class TracedEdges(list):
    def __iter__(self):
        for x in list.__iter__(self):
            Rec.edge_access += 1
            yield x

    def __getitem__(self, idx):
        if type(idx) is int:
            Rec.edge_access += 1
        return list.__getitem__(self, idx)


def make_grid(rows: list[str]) -> TracedGrid:
    g = TracedGrid()
    for r, s in enumerate(rows):
        list.append(g, TracedRow(s, r, len(s)))
    return g


# ============================================================================================ crafted inputs
def maze15(seed: int = 7) -> list[str]:
    rng = random.Random(seed)
    n = 15
    g = [["#"] * n for _ in range(n)]
    st = (1, 1)
    g[1][1] = "."
    seen = {st}
    stack = [st]
    while stack:
        r, c = stack[-1]
        nb = [(r + dr, c + dc) for dr, dc in ((2, 0), (-2, 0), (0, 2), (0, -2))
              if 0 < r + dr < n - 1 and 0 < c + dc < n - 1 and (r + dr, c + dc) not in seen]
        if not nb:
            stack.pop()
            continue
        nr, nc = rng.choice(nb)
        g[(r + nr) // 2][(c + nc) // 2] = "."
        g[nr][nc] = "."
        seen.add((nr, nc))
        stack.append((nr, nc))
    # open a few extra walls so the maze has cycles (separates BFS / DFS read orders better)
    for _ in range(12):
        r, c = rng.randrange(1, n - 1), rng.randrange(1, n - 1)
        g[r][c] = "."
    return ["".join(x) for x in g]


T1_INPUTS = [
    ("open15_centre", ["." * 15] * 15, (7, 7), (0, 14)),
    ("open12_corner", ["." * 12] * 12, (0, 0), (11, 11)),
    ("maze15", maze15(), (1, 1), (13, 13)),
]


def t2_inputs() -> list[tuple]:
    rng = random.Random(99)
    out = []
    for n in (20, 40, 80):
        chain = [(i, i + 1, 1) for i in range(n - 1)]
        k = max(2, n // 10)
        shortcuts = [(0, rng.randrange(2, n), 100 + rng.randrange(0, 100) // 10 * 0 + 90) for _ in range(k)]
        rev = list(reversed(chain)) + shortcuts
        out.append((f"chain{n}_rev", n, rev, 0, n - 1))
        out.append((f"chain{n}_fwd", n, chain + shortcuts, 0, n - 1))
    dense = [(rng.randrange(30), rng.randrange(30), rng.randint(0, 100)) for _ in range(300)]
    out.append(("dense30", 30, dense, 0, 29))
    return out


# ============================================================================================ features
def _bfs_dist(rows: list[str], src: tuple[int, int]) -> dict:
    R, C = len(rows), len(rows[0])
    d = {src: 0}
    q = _RealDeque([src])
    while q:
        r, c = q.popleft()
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < R and 0 <= nc < C and rows[nr][nc] == "." and (nr, nc) not in d:
                d[(nr, nc)] = d[(r, c)] + 1
                q.append((nr, nc))
    return d


def _find_cell(item, R: int, C: int):
    def is_cell(x):
        return (isinstance(x, (tuple, list)) and len(x) == 2 and all(type(v) is int for v in x)
                and 0 <= x[0] < R and 0 <= x[1] < C)
    if is_cell(item):
        return tuple(item)
    if isinstance(item, (tuple, list)):
        for x in item[1:]:
            if is_cell(x):
                return tuple(x)
        for x in item[1:]:
            if isinstance(x, (tuple, list)):
                for y in x:
                    if is_cell(y):
                        return tuple(y)
        if len(item) >= 3 and type(item[-1]) is int and type(item[-2]) is int:
            r, c = item[-2], item[-1]
            if 0 <= r < R and 0 <= c < C:
                return (r, c)
    return None


def _priority(item):
    if isinstance(item, (tuple, list)) and item and isinstance(item[0], (int, float)) and not isinstance(item[0], bool):
        return item[0]
    if isinstance(item, (int, float)) and not isinstance(item, bool):
        return item
    return None


def t1_features(rows: list[str], start, goal) -> dict:
    R, C = len(rows), len(rows[0])
    ds = _bfs_dist(rows, tuple(start))
    dg = _bfs_dist(rows, tuple(goal))
    pushes = [it for op, _, it in Rec.heap_ops if op == "push"]
    heaps = {}
    for op, hid, _ in Rec.heap_ops:
        if op == "push":
            heaps[hid] = heaps.get(hid, 0) + 1
    n_g = n_gh = n_h = n_valid = 0
    for it in pushes:
        p = _priority(it)
        cell = _find_cell(it, R, C)
        if p is None or cell is None or cell not in ds:
            continue
        n_valid += 1
        g = ds[cell]
        h = abs(cell[0] - goal[0]) + abs(cell[1] - goal[1])
        n_g += math.isclose(p, g)
        n_gh += math.isclose(p, g + h)
        n_h += math.isclose(p, h)
    fifo_containers = sum(1 for d in Rec.deque_ops.values() if d["popleft"] >= 3)
    fifo_containers += sum(1 for d in Rec.list_pops.values() if d["front"] >= 3)
    lifo_pops = (sum(d["pop"] for d in Rec.deque_ops.values()) + sum(d["back"] for d in Rec.list_pops.values())
                 + Rec.lifo_q_pops)
    # read-order layer violations (first reads only; cells eventually read)
    reads = Rec.cell_reads
    first_order = []
    seen = set()
    for x in reads:
        if x not in seen:
            seen.add(x)
            first_order.append(x)

    def violation_rate(dist_of) -> float | None:
        cells = [x for x in first_order if x in dist_of]
        if len(cells) < 10:
            return None
        remaining: dict = {}
        for x in cells:
            remaining[dist_of[x]] = remaining.get(dist_of[x], 0) + 1
        n_viol = n_tot = 0
        for x in cells:
            d = dist_of[x]
            if d >= 2:
                n_tot += 1
                if remaining.get(d - 2, 0) > 0:
                    n_viol += 1
            remaining[d] -= 1
        return n_viol / n_tot if n_tot else None

    dmin = {x: min(ds.get(x, 1 << 30), dg.get(x, 1 << 30)) for x in set(ds) | set(dg)}
    v_start = violation_rate(ds)
    v_min = violation_rate(dmin)
    # restart waves: a read at start-distance <= 1 that follows a read at start-distance >= 4 (BFS never does this:
    # once layer 3 is being expanded it reads only layers 2..4); counted once per excursion
    waves = 0
    far = True
    for x in reads:
        d = ds.get(x)
        if d is None:
            continue
        if d <= 1 and far:
            waves += 1
            far = False
        elif d >= 4:
            far = True
    reread = len(reads) / max(1, len(seen))
    return {"n_heap_push": len(pushes), "n_heaps_ge3": sum(1 for v in heaps.values() if v >= 3),
            "n_valid_push": n_valid, "share_g": n_g / n_valid if n_valid else None,
            "share_gh": n_gh / n_valid if n_valid else None, "share_h": n_h / n_valid if n_valid else None,
            "fifo_containers": fifo_containers, "lifo_pops": lifo_pops, "depth_max": Rec.depth_max,
            "n_reads": len(reads), "n_distinct_reads": len(seen), "reread_ratio": reread,
            "viol_start": v_start, "viol_min": v_min, "waves": waves,
            "reads_available": len(seen) >= 10}


def t1_rule(fs: list[dict]) -> tuple[str, str]:
    """fs: features per crafted input (open15_centre, open12_corner, maze15)."""
    n_push = sum(f["n_heap_push"] for f in fs)
    nv = sum(f["n_valid_push"] for f in fs)
    if n_push >= 3:
        if nv:
            sg = sum((f["share_g"] or 0) * f["n_valid_push"] for f in fs) / nv
            sgh = sum((f["share_gh"] or 0) * f["n_valid_push"] for f in fs) / nv
            sh = sum((f["share_h"] or 0) * f["n_valid_push"] for f in fs) / nv
            if sg >= 0.8 and sg >= max(sgh, sh):
                return "dijkstra_unit", f"heap share_g={sg:.2f}"
            if max(sgh, sh) >= 0.8:
                return "astar_greedy", f"heap share_gh={sgh:.2f} share_h={sh:.2f}"
        return "unknown", "heap with unreadable priorities"
    fifo = max(f["fifo_containers"] for f in fs)
    if fifo >= 2:
        return "bidir_bfs", f"{fifo} FIFO containers"
    if fifo == 1:
        return "bfs", "1 FIFO container"
    lifo = sum(f["lifo_pops"] for f in fs)
    depth = max(f["depth_max"] for f in fs)
    f0 = fs[0]
    restart = f0["waves"] >= 4 and f0["reread_ratio"] >= 5.0
    if lifo > 0 or depth >= 5:
        if restart:
            return "iddfs", f"lifo={lifo} depth={depth} waves={f0['waves']} reread={f0['reread_ratio']:.1f}"
        return "dfs", f"lifo={lifo} depth={depth} waves={f0['waves']}"
    if f0["reads_available"] and f0["viol_start"] is not None:
        if restart:
            return "iddfs", f"read-order restarts waves={f0['waves']}"
        if f0["viol_start"] < 0.05:
            return "bfs", f"read-order violation {f0['viol_start']:.3f}"
        if f0["viol_start"] > 0.2:
            return "dfs", f"read-order violation {f0['viol_start']:.3f}"
    return "unknown", "no decisive signal"


def t2_rule(feats: dict) -> tuple[str, str]:
    if feats["n_heaps_ge3"] >= 2:
        return "bidir_dijkstra", f"{feats['n_heaps_ge3']} heaps"
    if feats["n_heaps_ge3"] == 1:
        return "dijkstra", "1 heap"
    if feats["edge_passes_rev80"] is not None and feats["edge_passes_rev80"] >= 3:
        return "bellman_ford_spfa", f"edge passes {feats['edge_passes_rev80']:.1f}"
    if feats["order_ratio80"] is not None and feats["order_ratio80"] >= 4:
        return "bellman_ford_spfa", f"order sensitivity {feats['order_ratio80']:.1f}"
    if feats["reenqueue"] > 0 and feats["fifo_any"]:
        return "bellman_ford_spfa", f"FIFO re-enqueues {feats['reenqueue']}"
    if feats["exponent"] is not None and feats["exponent"] >= 2.6:
        return "floyd_warshall", f"exponent {feats['exponent']:.2f}"
    return "unknown", f"exponent {feats['exponent']}"


# ============================================================================================ runner
def _reset() -> None:
    Rec.heap_ops = []
    Rec.deque_ops = {}
    Rec.list_pops = {}
    Rec.list_vals = {}
    Rec.lifo_q_pops = 0
    Rec.cell_reads = []
    Rec.depth_max = 0
    Rec.edge_access = 0
    Rec.lines = 0


class _Cap(Exception):
    pass


def run_entry() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True)
    ap.add_argument("--code", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    code = open(a.code).read()
    import resource
    resource.setrlimit(resource.RLIMIT_AS, (3 * 1024**3, 3 * 1024**3))
    sys.setrecursionlimit(20000)
    threading.stack_size(256 * 1024 * 1024)
    install_patches()
    out: dict = {"label": "unknown", "why": "", "features": {}, "errors": []}
    result: dict = {}

    def body() -> None:
        ns: dict = {"__name__": "solution", "__builtins__": __builtins__}
        try:
            exec(compile(code, "<solution>", "exec"), ns)
            fn = ns["solve"]
        except BaseException as e:  # noqa: BLE001
            out["errors"].append(f"load:{type(e).__name__}")
            return
        prof = make_profiler()
        if a.task == "t1":
            fs = []
            for name, rows, s, t in T1_INPUTS:
                _reset()
                sys.setprofile(prof)
                try:
                    fn(make_grid(rows), tuple(s), tuple(t))
                except BaseException as e:  # noqa: BLE001
                    out["errors"].append(f"{name}:{type(e).__name__}")
                finally:
                    sys.setprofile(None)
                f = t1_features(rows, s, t)
                f["input"] = name
                fs.append(f)
            out["features"] = {"per_input": fs}
            out["label"], out["why"] = t1_rule(fs)
        else:
            per = {}
            heaps_ge3 = 0
            reenq = 0
            fifo_any = False
            for name, n, edges, s, t in t2_inputs():
                _reset()
                cnt = [0]

                def tracer(frame, event, arg):
                    if frame.f_code.co_filename != "<solution>":
                        return None

                    def local(fr, ev, ar):
                        if ev == "line":
                            cnt[0] += 1
                            if cnt[0] > LINE_CAP:
                                raise _Cap()
                        return local
                    return local

                sys.setprofile(prof)
                sys.settrace(tracer)
                capped = False
                try:
                    fn(n, TracedEdges(edges), s, t)
                except _Cap:
                    capped = True
                except BaseException as e:  # noqa: BLE001
                    out["errors"].append(f"{name}:{type(e).__name__}")
                finally:
                    sys.settrace(None)
                    sys.setprofile(None)
                hp = {}
                for op, hid, _ in Rec.heap_ops:
                    if op == "push":
                        hp[hid] = hp.get(hid, 0) + 1
                heaps_ge3 = max(heaps_ge3, sum(1 for v in hp.values() if v >= 3))
                for d in Rec.deque_ops.values():
                    if d["popleft"] >= 3:
                        fifo_any = True
                        reenq = max(reenq, len(d["vals"]) - len(set(d["vals"])))
                for lid, d in Rec.list_pops.items():
                    if d["front"] >= 3:
                        fifo_any = True
                        vals = Rec.list_vals.get(lid, [])
                        reenq = max(reenq, len(vals) - len(set(vals)))
                per[name] = {"lines": cnt[0], "capped": capped, "edge_passes": Rec.edge_access / max(1, len(edges)),
                             "n_heap_push": sum(hp.values()), "depth_max": Rec.depth_max}
            xs, ys = [], []
            for n in (20, 40, 80):
                L = per[f"chain{n}_rev"]["lines"]
                if L > 0:
                    xs.append(math.log(n))
                    ys.append(math.log(L))
            expo = None
            if len(xs) >= 2:
                mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
                sxx = sum((x - mx) ** 2 for x in xs)
                expo = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx if sxx > 0 else None
            if per["chain80_rev"]["capped"]:
                expo = max(expo or 0, 3.0)
            r80 = per["chain80_rev"]["lines"] / per["chain80_fwd"]["lines"] if per["chain80_fwd"]["lines"] else None
            feats = {"per_input": per, "n_heaps_ge3": heaps_ge3, "reenqueue": reenq, "fifo_any": fifo_any,
                     "exponent": expo, "edge_passes_rev80": per["chain80_rev"]["edge_passes"], "order_ratio80": r80}
            out["features"] = feats
            out["label"], out["why"] = t2_rule(feats)

    th = threading.Thread(target=body, daemon=True)
    th.start()
    th.join(60)
    if th.is_alive():
        out["errors"].append("runtime_labeller_timeout")
        out["label"] = "unknown"
    with open(a.out, "w") as f:
        json.dump(out, f, default=str)
    os._exit(0)


# ============================================================================================ library side
def label_one(task: str, code: str, workdir: str, timeout: float = 90.0) -> dict:
    import subprocess
    import tempfile
    os.makedirs(workdir, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=workdir) as td:
        prog, out = os.path.join(td, "prog.py"), os.path.join(td, "out.json")
        with open(prog, "w") as f:
            f.write(code)
        try:
            subprocess.run([sys.executable, "-I", os.path.join(_HERE, "labeller_runtime.py"), "--task", task,
                            "--code", prog, "--out", out], cwd=td, stdin=subprocess.DEVNULL,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=timeout)
        except subprocess.TimeoutExpired:
            return {"label": "unknown", "why": "subprocess timeout", "features": {}, "errors": ["timeout"]}
        if not os.path.exists(out):
            return {"label": "unknown", "why": "crash", "features": {}, "errors": ["crash"]}
        return json.load(open(out))


def _job(j: tuple) -> dict:
    task, code, workdir, key = j
    try:
        r = label_one(task, code, workdir)
    except Exception as e:  # noqa: BLE001
        r = {"label": "unknown", "why": f"error {e!r}", "features": {}, "errors": [repr(e)]}
    r["key"] = key
    return r


def label_many(jobs: list[tuple], n_workers: int = 4) -> list[dict]:
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=n_workers) as ex:
        return list(ex.map(_job, jobs))


if __name__ == "__main__":
    run_entry()
