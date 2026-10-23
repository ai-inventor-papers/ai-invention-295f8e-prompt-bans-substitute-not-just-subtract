#!/usr/bin/env python3
"""Expansion tracer child (stdlib only; run as `python3.12 -I -S expansion_child.py job.json out.json`).

Built on the iteration-2 tracer (vendor/exp9/labeller_ext/tracer.py): the same instrumentation idea, reduced to what
the behavioural RDM needs. Installed BEFORE the candidate is exec'd:
  * sys.modules['heapq'] -> proxy recording every pop (heappop / heappushpop / heapreplace) with the popped cell
  * collections.deque -> subclass recording pop / popleft
  * queue.Queue / LifoQueue / PriorityQueue -> subclasses recording get()
  * sys.setprofile: list.pop (front vs back decided by comparing the list ends before/after the C call), builtin abs()
    calls (Manhattan evaluations), Python calls of candidate functions with a cell argument (recursive expansions)
    and self-recursion depth
  * the grid is a list of str-subclass rows whose __getitem__ records (row, col) reads (burst fallback)
Per probe grid the child reports: container pops [kind, container, r, c], recursive-call cells [fn, r, c], grid-read
bursts (a run of >= 2 consecutive reads that are all 4-neighbours of one cell = an expansion of that cell), abs()
count, recursion depth, whether the rows were copied, and whether a valid path was returned.
Kinds: F = FIFO (deque.popleft, list.pop(0), Queue.get), L = LIFO (deque.pop, list.pop(), LifoQueue.get),
H = heap (heapq pops, PriorityQueue.get).
"""

import collections
import heapq as _rh
import json
import queue
import resource
import signal
import sys
import types

CAP_POPS = 6000
CAP_CALLS = 6000
CAP_READS = 40000


class Rec:
    def __init__(self):
        self.reset(None)

    def reset(self, dims):
        self.dims = dims
        self.pops = []
        self.calls = []
        self.reads = []
        self.abs_calls = 0
        self.copied = False
        self.cont_ids = {}
        self.pending = []
        self.code_depth = {}
        self.rec_codes = set()
        self.max_rec_depth = 0
        self.code_ids = {}


R = Rec()


def _ok(a, b):
    d = R.dims
    return (d is not None and type(a) is int and type(b) is int and 0 <= a < d[0] and 0 <= b < d[1])


def _cell(item, kind="H"):
    """Cell of a popped item. Heap items carry their priority first ((f, g, r, c) / (f, (r, c))); stack and queue
    items usually carry the cell first ((r, c, depth) / ((r, c), depth, path))."""
    if isinstance(item, (tuple, list)):
        if len(item) == 2 and _ok(item[0], item[1]):
            return (item[0], item[1])
        if (kind != "H" and len(item) >= 2 and all(isinstance(x, (tuple, list)) and len(x) == 2 and _ok(x[0], x[1])
                                                    for x in item)):
            return (item[-1][0], item[-1][1])          # a carried path: the expanded cell is its last cell
        if kind != "H":
            x = item[0] if item else None
            if isinstance(x, (tuple, list)) and len(x) >= 2 and _ok(x[0], x[1]):
                return (x[0], x[1])
            if len(item) >= 2 and _ok(item[0], item[1]):
                return (item[0], item[1])
        for x in (item[1:] if len(item) > 1 else item):
            if isinstance(x, (tuple, list)) and len(x) >= 2 and _ok(x[0], x[1]):
                return (x[0], x[1])
        if len(item) >= 3 and _ok(item[-2], item[-1]):
            return (item[-2], item[-1])
        x = item[0] if item else None
        if isinstance(x, (tuple, list)) and len(x) >= 2 and _ok(x[0], x[1]):
            return (x[0], x[1])
        if len(item) >= 2 and _ok(item[0], item[1]):
            return (item[0], item[1])
    return None


def _cid(obj):
    k = id(obj)
    if k not in R.cont_ids:
        R.cont_ids[k] = len(R.cont_ids)
    return R.cont_ids[k]


def _rec_pop(kind, container, item):
    c = _cell(item, kind)
    if c is not None and len(R.pops) < CAP_POPS:
        R.pops.append((kind, _cid(container), c[0], c[1], len(R.reads)))


def _mk_heapq():
    m = types.ModuleType("heapq")
    for name in dir(_rh):
        if not name.startswith("__"):
            setattr(m, name, getattr(_rh, name))

    def heappop(h):
        x = _rh.heappop(h)
        _rec_pop("H", h, x)
        return x

    def heappushpop(h, item):
        x = _rh.heappushpop(h, item)
        if x is not item:
            _rec_pop("H", h, x)
        return x

    def heapreplace(h, item):
        x = _rh.heapreplace(h, item)
        _rec_pop("H", h, x)
        return x

    m.heappop, m.heappushpop, m.heapreplace = heappop, heappushpop, heapreplace
    return m


_RealDeque = collections.deque


class TDeque(_RealDeque):
    def popleft(self):
        x = _RealDeque.popleft(self)
        _rec_pop("F", self, x)
        return x

    def pop(self):
        x = _RealDeque.pop(self)
        _rec_pop("L", self, x)
        return x


def _mk_q(base, kind):
    class TQ(base):
        def get(self, *a, **k):
            x = base.get(self, *a, **k)
            _rec_pop(kind, self, x)
            return x

        def get_nowait(self):
            x = base.get_nowait(self)
            _rec_pop(kind, self, x)
            return x
    TQ.__name__ = base.__name__
    return TQ


class TRow(str):
    def __getitem__(self, c):
        if type(c) is int and len(R.reads) < CAP_READS:
            R.reads.append((self._r, c if c >= 0 else len(self) + c))
        elif type(c) is slice:
            R.copied = True
        return str.__getitem__(self, c)

    def __iter__(self):
        R.copied = True
        return str.__iter__(self)


def make_grid(rows):
    out = []
    for i, r in enumerate(rows):
        t = TRow(r)
        t._r = i
        out.append(t)
    return out


_list_pop = list.pop
_abs = abs


def _call_cell(frame):
    co = frame.f_code
    n = co.co_argcount + co.co_kwonlyargcount
    loc = frame.f_locals
    names = co.co_varnames[:n]
    vals = [loc.get(v) for v in names]
    for v in vals:
        if isinstance(v, (tuple, list)) and len(v) == 2 and _ok(v[0], v[1]):
            return (v[0], v[1])
    for i in range(len(vals) - 1):
        if _ok(vals[i], vals[i + 1]):
            return (vals[i], vals[i + 1])
    return None


def _profile(frame, event, arg):
    try:
        if event == "c_call":
            if arg is _abs:
                R.abs_calls += 1
            elif getattr(arg, "__name__", "") == "pop" and type(getattr(arg, "__self__", None)) is list:
                lst = arg.__self__
                if lst:
                    R.pending.append((lst, len(lst), lst[0], lst[-1]))
                else:
                    R.pending.append(None)
        elif event in ("c_return", "c_exception"):
            if getattr(arg, "__name__", "") == "pop" and type(getattr(arg, "__self__", None)) is list and R.pending:
                p = R.pending.pop()
                if p is not None and event == "c_return":
                    lst, n0, first, last = p
                    if len(lst) == n0 - 1:
                        if n0 == 1:
                            _rec_pop("L", lst, last)
                        elif lst and lst[0] is not first:
                            _rec_pop("F", lst, first)
                        elif not lst or lst[-1] is not last or n0 == 1:
                            _rec_pop("L", lst, last)
                        else:
                            _rec_pop("M", lst, first)
        elif event == "call":
            co = frame.f_code
            if co.co_filename == "<candidate>":
                d = R.code_depth.get(co, 0) + 1
                R.code_depth[co] = d
                if d >= 2:
                    R.rec_codes.add(co)
                    if d > R.max_rec_depth:
                        R.max_rec_depth = d
                c = _call_cell(frame)
                if c is not None and len(R.calls) < CAP_CALLS:
                    if co not in R.code_ids:
                        R.code_ids[co] = len(R.code_ids)
                    R.calls.append((R.code_ids[co], c[0], c[1], co))
        elif event == "return":
            co = frame.f_code
            if co.co_filename == "<candidate>":
                R.code_depth[co] = R.code_depth.get(co, 1) - 1
    except Exception:  # noqa: BLE001 - instrumentation must never break the candidate
        pass


def bursts(reads, dims):
    """Expansion centres from runs of >= 2 consecutive reads that are all 4-neighbours of one cell."""
    H, W = dims

    def cands(cell):
        r, c = cell
        return {(r + dr, c + dc) for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1))
                if 0 <= r + dr < H and 0 <= c + dc < W}

    out, seen = [], set()
    i, n = 0, len(reads)
    while i < n - 1:
        cand = cands(reads[i])
        j = i + 1
        while j < n:
            nc = cand & cands(reads[j])
            if not nc:
                break
            cand = nc
            j += 1
        if j - i >= 2:
            pick = sorted(cand, key=lambda x: (x not in seen, x))[0]
            out.append(pick)
            seen.add(pick)
            i = j
        else:
            seen.add(reads[i])
            i += 1
    return out


class _Timeout(Exception):
    pass


def _alarm(signum, frame):
    raise _Timeout()


def valid_path(rows, start, goal, path):
    try:
        p = [tuple(x) for x in path]
    except TypeError:
        return False
    if not p or p[0] != tuple(start) or p[-1] != tuple(goal):
        return False
    for a, b in zip(p, p[1:]):
        if abs(a[0] - b[0]) + abs(a[1] - b[1]) != 1:
            return False
    return all(0 <= r < len(rows) and 0 <= c < len(rows[0]) and rows[r][c] == "." for r, c in p)


def main():
    job = json.loads(open(sys.argv[1]).read())
    try:
        resource.setrlimit(resource.RLIMIT_AS, (2 * 1024 ** 3, 2 * 1024 ** 3))
    except (ValueError, OSError):
        pass
    sys.modules["heapq"] = _mk_heapq()
    collections.deque = TDeque
    queue.Queue = _mk_q(queue.Queue, "F")
    queue.LifoQueue = _mk_q(queue.LifoQueue, "L")
    queue.PriorityQueue = _mk_q(queue.PriorityQueue, "H")
    sys.setrecursionlimit(20000)
    g = {"__name__": "candidate"}
    out = {"grids": [], "load_error": None}
    try:
        exec(compile(job["code"], "<candidate>", "exec"), g)
    except BaseException as e:  # noqa: BLE001
        out["load_error"] = f"{type(e).__name__}: {e}"[:200]
        open(sys.argv[2], "w").write(json.dumps(out))
        return
    solve = g.get("solve")
    signal.signal(signal.SIGALRM, _alarm)
    n_timeouts = 0
    for gi, pg in enumerate(job["grids"]):
        if n_timeouts >= 3:
            out["grids"].append({"ok": False, "err": "skipped_after_3_timeouts", "pops": [], "calls": [], "bursts": [],
                                 "bursts_after_pops": [], "n_reads": 0, "abs_calls": 0, "max_rec_depth": 0,
                                 "copied": False})
            continue
        rows = pg["rows"]
        start, goal = tuple(pg["start"]), tuple(pg["goal"])
        R.reset((len(rows), len(rows[0])))
        res = {"ok": False, "err": None}
        grid = make_grid(rows)
        signal.setitimer(signal.ITIMER_REAL, float(job.get("timeout_s", 3.0)))
        sys.setprofile(_profile)
        try:
            path = solve(grid, start, goal)
            sys.setprofile(None)
            res["ok"] = valid_path(rows, start, goal, path)
        except _Timeout:
            sys.setprofile(None)
            res["err"] = "timeout"
            n_timeouts += 1
        except BaseException as e:  # noqa: BLE001
            sys.setprofile(None)
            res["err"] = f"{type(e).__name__}"
        finally:
            sys.setprofile(None)
            signal.setitimer(signal.ITIMER_REAL, 0)
        rec_ids = {R.code_ids[co] for co in R.rec_codes if co in R.code_ids}
        res["pops"] = [list(p) for p in R.pops]
        res["calls"] = [[f, r, c] for f, r, c, _co in R.calls if f in rec_ids]
        res["bursts"] = [list(x) for x in bursts(R.reads, R.dims)]
        last = R.pops[-1][4] if R.pops else 0
        res["bursts_after_pops"] = [list(x) for x in bursts(R.reads[last:], R.dims)] if R.pops else res["bursts"]
        res["n_reads"] = len(R.reads)
        res["n_calls_all"] = len(R.calls)
        res["abs_calls"] = R.abs_calls
        res["max_rec_depth"] = R.max_rec_depth
        res["copied"] = R.copied
        out["grids"].append(res)
    open(sys.argv[2], "w").write(json.dumps(out))


if __name__ == "__main__":
    main()
