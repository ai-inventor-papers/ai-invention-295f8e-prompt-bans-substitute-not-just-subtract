"""Runtime-signature tracer driver (run with `python -I` in a temp dir, one crafted input per process).

argv: prog_path task input_json out_path
Instrumentation is installed BEFORE the program is exec'd:
  * heapq.heappush/heappop/heapify/heappushpop/heapreplace -> logging wrappers
  * collections.deque -> logging subclass; queue.Queue/LifoQueue/PriorityQueue/SimpleQueue -> logging subclasses
  * an ast.NodeTransformer routes obj.pop/append/add/insert(...) through _aii_tr(obj, method, ...) so list-as-queue
    pop(0) and list-as-stack pop() are separated
  * sys.settrace (program code only) counts line events and records calls of user functions whose arguments
    contain a cell (T1) or a node (T2), with the per-function recursion depth
  * on T2 the edge list is a list subclass counting full iterations and indexed reads
Writes one JSON object with the event log summary to out_path.
"""

import ast
import json
import os
import resource
import sys
import threading
import time

# import queue/threading BEFORE patching so their internals keep the original deque/heapq
import queue as _queue_mod  # noqa: E402
import heapq as _heapq_mod  # noqa: E402
import collections as _collections_mod  # noqa: E402

PROG_FILE = "solution.py"
MAX_EVENTS = 200000
EVENTS = []          # (kind, ctype, cid, method, node, key)
CALLS = []           # (func, depth, node)
STATE = {"lines": 0, "edge_iters": 0, "edge_getitem": 0, "n_events": 0, "max_depth": 0, "seq": 0}
DEPTH = {}
CTX = {"task": None, "R": 0, "C": 0, "grid": None, "n": 0}


def is_int(x):
    return isinstance(x, int) and not isinstance(x, bool)


def is_cell(x):
    if isinstance(x, (tuple, list)) and len(x) == 2 and is_int(x[0]) and is_int(x[1]):
        return 0 <= x[0] < CTX["R"] and 0 <= x[1] < CTX["C"]
    return False


def cell_of(item, heap=False, depth=0):
    """Extract a grid cell from a container item (T1)."""
    if depth > 3:
        return None
    if is_cell(item):
        return (item[0], item[1])
    if isinstance(item, (tuple, list)) and len(item) > 0:
        if len(item) <= 2000 and all(is_cell(x) for x in item):
            return tuple(item[-1])  # a path: the current cell is its last element
        for x in item:
            if is_cell(x):
                return (x[0], x[1])
        for x in item:
            if isinstance(x, (tuple, list)) and x and len(x) <= 2000 and all(is_cell(y) for y in x):
                return tuple(x[-1])
        ints = [x for x in item if is_int(x)]
        if len(ints) >= 2 and len(ints) == len(item):
            cand = (ints[-2], ints[-1]) if heap else (ints[0], ints[1])
            if is_cell(cand):
                return cand
        for x in item:
            if isinstance(x, (tuple, list)) or hasattr(x, "__dict__"):
                c = cell_of(x, heap, depth + 1)
                if c is not None:
                    return c
        return None
    d = getattr(item, "__dict__", None)
    if isinstance(d, dict):
        for v in d.values():
            if is_cell(v):
                return (v[0], v[1])
        for a, b in (("row", "col"), ("r", "c"), ("x", "y"), ("i", "j")):
            if a in d and b in d and is_cell((d[a], d[b])):
                return (d[a], d[b])
    return None


def node_of(item, heap=False):
    """Extract a node id (< n) from a container item (T2): heap items -> last top-level int < n except item[0]."""
    n = CTX["n"]
    if is_int(item):
        return item if 0 <= item < n else None
    if isinstance(item, (tuple, list)) and item:
        if heap:
            for x in reversed(item[1:]):
                if is_int(x) and 0 <= x < n:
                    return x
            return None
        for x in item:
            if is_int(x) and 0 <= x < n:
                return x
        return None
    d = getattr(item, "__dict__", None)
    if isinstance(d, dict):
        for k in ("node", "v", "u", "id", "vertex"):
            if k in d and is_int(d[k]) and 0 <= d[k] < n:
                return d[k]
    return None


def key_of(item):
    if isinstance(item, (tuple, list)) and item:
        k = item[0]
        if isinstance(k, (tuple, list)) and k and isinstance(k[0], (int, float)) and not isinstance(k[0], bool):
            k = k[0]
        if isinstance(k, (int, float)) and not isinstance(k, bool):
            return float(k)
        return None
    if isinstance(item, (int, float)) and not isinstance(item, bool):
        return float(item)
    for a in ("f", "priority", "cost", "dist", "g", "key"):
        v = getattr(item, a, None)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return float(v)
    return None


def where(item, heap=False):
    if CTX["task"] == "T1":
        return cell_of(item, heap)
    return node_of(item, heap)


def log(kind, ctype, cid, method, item, heap=False):
    STATE["n_events"] += 1
    if len(EVENTS) >= MAX_EVENTS:
        return
    try:
        node = where(item, heap)
        key = key_of(item) if heap else None
    except Exception:  # noqa: BLE001
        node, key = None, None
    STATE["seq"] += 1
    EVENTS.append((kind, ctype, cid, method, node, key, STATE["seq"]))


# ---------------- heapq ----------------
_orig = {k: getattr(_heapq_mod, k) for k in ("heappush", "heappop", "heapify", "heappushpop", "heapreplace")}


def _heappush(h, item):
    log("push", "heap", id(h), "heappush", item, heap=True)
    return _orig["heappush"](h, item)


def _heappop(h):
    item = _orig["heappop"](h)
    log("pop", "heap", id(h), "heappop", item, heap=True)
    return item


def _heapify(h):
    for it in list(h)[:1000]:
        log("push", "heap", id(h), "heapify", it, heap=True)
    return _orig["heapify"](h)


def _heappushpop(h, item):
    res = _orig["heappushpop"](h, item)
    log("push", "heap", id(h), "heappushpop", item, heap=True)
    log("pop", "heap", id(h), "heappushpop", res, heap=True)
    return res


def _heapreplace(h, item):
    res = _orig["heapreplace"](h, item)
    log("pop", "heap", id(h), "heapreplace", res, heap=True)
    log("push", "heap", id(h), "heapreplace", item, heap=True)
    return res


_heapq_mod.heappush = _heappush
_heapq_mod.heappop = _heappop
_heapq_mod.heapify = _heapify
_heapq_mod.heappushpop = _heappushpop
_heapq_mod.heapreplace = _heapreplace


# ---------------- deque ----------------
_RealDeque = _collections_mod.deque


class LoggingDeque(_RealDeque):
    def append(self, x):
        log("push", "deque", id(self), "append", x)
        return _RealDeque.append(self, x)

    def appendleft(self, x):
        log("push", "deque", id(self), "appendleft", x)
        return _RealDeque.appendleft(self, x)

    def extend(self, it):
        it = list(it)
        for x in it:
            log("push", "deque", id(self), "append", x)
        return _RealDeque.extend(self, it)

    def extendleft(self, it):
        it = list(it)
        for x in it:
            log("push", "deque", id(self), "appendleft", x)
        return _RealDeque.extendleft(self, it)

    def pop(self):
        x = _RealDeque.pop(self)
        log("pop", "deque", id(self), "pop", x)
        return x

    def popleft(self):
        x = _RealDeque.popleft(self)
        log("pop", "deque", id(self), "popleft", x)
        return x


LoggingDeque.__name__ = "deque"
LoggingDeque.__qualname__ = "deque"


# ---------------- queue ----------------
class LogQueue(_queue_mod.Queue):
    def put(self, item, block=True, timeout=None):
        log("push", "queue_fifo", id(self), "put", item)
        return super().put(item, block, timeout)

    def get(self, block=True, timeout=None):
        x = super().get(False)
        log("pop", "queue_fifo", id(self), "get", x)
        return x


class LogLifo(_queue_mod.LifoQueue):
    def put(self, item, block=True, timeout=None):
        log("push", "queue_lifo", id(self), "put", item)
        return super().put(item, block, timeout)

    def get(self, block=True, timeout=None):
        x = super().get(False)
        log("pop", "queue_lifo", id(self), "get", x)
        return x


class LogPQ(_queue_mod.PriorityQueue):
    def put(self, item, block=True, timeout=None):
        log("push", "heap", id(self), "pq_put", item, heap=True)
        return super().put(item, block, timeout)

    def get(self, block=True, timeout=None):
        x = super().get(False)
        log("pop", "heap", id(self), "pq_get", x, heap=True)
        return x


class LogSimple(_queue_mod.SimpleQueue):
    def put(self, item, block=True, timeout=None):
        log("push", "queue_fifo", id(self), "put", item)
        return super().put(item, block, timeout)

    def get(self, block=True, timeout=None):
        x = super().get(False)
        log("pop", "queue_fifo", id(self), "get", x)
        return x


for _cls, _name in ((LogQueue, "Queue"), (LogLifo, "LifoQueue"), (LogPQ, "PriorityQueue"),
                    (LogSimple, "SimpleQueue")):
    _cls.__name__ = _name
    _cls.__qualname__ = _name

INSTRUMENTED = (LoggingDeque, LogQueue, LogLifo, LogPQ, LogSimple)


# ---------------- AST rewrite of container methods ----------------
TRACKED = {"pop", "append", "add", "insert"}


class Rewriter(ast.NodeTransformer):
    def visit_Call(self, node):
        self.generic_visit(node)
        f = node.func
        if isinstance(f, ast.Attribute) and f.attr in TRACKED and not any(isinstance(a, ast.Starred)
                                                                          for a in node.args):
            return ast.copy_location(ast.Call(func=ast.Name(id="_aii_tr", ctx=ast.Load()),
                                              args=[f.value, ast.Constant(f.attr)] + node.args,
                                              keywords=node.keywords), node)
        return node


def _aii_tr(obj, method, *a, **k):
    meth = getattr(obj, method)
    if isinstance(obj, INSTRUMENTED):
        return meth(*a, **k)
    tname = type(obj).__name__
    if method == "pop":
        n_before = len(obj) if isinstance(obj, list) else 0
        res = meth(*a, **k)
        if isinstance(obj, list):
            idx = a[0] if a else -1
            if is_int(idx) and (idx == 0 or (idx == -n_before and n_before > 1)):
                m = "pop0"
            elif idx == -1 or idx == n_before - 1:
                m = "pop"
            else:
                m = "pop_mid"
            log("pop", "list", id(obj), m, res)
        elif isinstance(obj, (set, frozenset)):
            log("pop", "set", id(obj), "set_pop", res)
        elif isinstance(obj, dict):
            pass
        else:
            log("pop", tname, id(obj), "pop", res)
        return res
    if isinstance(obj, list):
        if method == "append":
            log("push", "list", id(obj), "append", a[0] if a else None)
        elif method == "insert" and len(a) >= 2:
            log("push", "list", id(obj), "insert0" if a[0] == 0 else "insert", a[1])
    elif isinstance(obj, (set, frozenset)) and method == "add":
        log("push", "set", id(obj), "add", a[0] if a else None)
    return meth(*a, **k)


# ---------------- T2 edge list ----------------
class EdgeList(list):
    def __iter__(self):
        STATE["edge_iters"] += 1
        return list.__iter__(self)

    def __getitem__(self, i):
        STATE["edge_getitem"] += 1
        return list.__getitem__(self, i)


# ---------------- settrace ----------------
def arg_where(frame):
    co = frame.f_code
    names = co.co_varnames[:co.co_argcount + co.co_kwonlyargcount]
    loc = frame.f_locals
    vals = [loc.get(nm) for nm in names]
    if CTX["task"] == "T1":
        for v in vals:
            if is_cell(v):
                return (v[0], v[1])
        for a, b in zip(vals, vals[1:]):
            if is_int(a) and is_int(b) and is_cell((a, b)):
                return (a, b)
        return None
    n = CTX["n"]
    for v in vals:
        if is_int(v) and 0 <= v < n:
            return v
    return None


def local_trace(frame, event, arg):
    if event == "line":
        STATE["lines"] += 1
    elif event == "return":
        nm = frame.f_code.co_name
        DEPTH[nm] = DEPTH.get(nm, 1) - 1
    return local_trace


def global_trace(frame, event, arg):
    if event != "call" or frame.f_code.co_filename != PROG_FILE:
        return None
    nm = frame.f_code.co_name
    d = DEPTH.get(nm, 0) + 1
    DEPTH[nm] = d
    if d > STATE["max_depth"]:
        STATE["max_depth"] = d
    if len(CALLS) < MAX_EVENTS and nm not in ("<module>", "<genexpr>", "<listcomp>", "<lambda>", "<dictcomp>",
                                              "<setcomp>"):
        try:
            STATE["seq"] += 1
            CALLS.append((nm, d, arg_where(frame), STATE["seq"]))
        except Exception:  # noqa: BLE001
            pass
    return local_trace


def main():
    prog_path, task, input_path, out_path = sys.argv[1:5]
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024 ** 3, 2 * 1024 ** 3))
    sys.setrecursionlimit(100000)
    threading.stack_size(256 * 1024 * 1024)
    inp = json.loads(open(input_path).read())
    CTX["task"] = task
    src = open(prog_path).read()
    tree = ast.parse(src)
    tree = Rewriter().visit(tree)
    ast.fix_missing_locations(tree)
    code = compile(tree, PROG_FILE, "exec")
    _collections_mod.deque = LoggingDeque
    _queue_mod.Queue = LogQueue
    _queue_mod.LifoQueue = LogLifo
    _queue_mod.PriorityQueue = LogPQ
    _queue_mod.SimpleQueue = LogSimple
    import io
    sys.stdout = io.StringIO()
    sys.stdin = io.StringIO("")
    ns = {"__name__": "solution", "__builtins__": __builtins__, "_aii_tr": _aii_tr}
    if task == "T1":
        grid = [str(r) for r in inp["grid"]]
        CTX.update(R=len(grid), C=len(grid[0]), grid=grid)
        args = (grid, tuple(inp["start"]), tuple(inp["goal"]))
    else:
        CTX.update(n=int(inp["n"]))
        args = (int(inp["n"]), EdgeList([tuple(e) for e in inp["edges"]]), int(inp["s"]), int(inp["t"]))
    res = {}

    def _run():
        try:
            exec(code, ns)
            solve = ns.get("solve")
            if not callable(solve):
                res["status"] = "no_solve"
                return
            sys.settrace(global_trace)
            t0 = time.perf_counter()
            out = solve(*args)
            sys.settrace(None)
            res["t"] = time.perf_counter() - t0
            res["status"] = "ok"
            if task == "T1":
                if isinstance(out, (list, tuple)):
                    res["out_len"] = len(out)
                    res["out_valid_cells"] = all(is_cell(c) for c in out)
                else:
                    res["out_len"] = None
            else:
                res["out"] = out if isinstance(out, (int, float)) and not isinstance(out, bool) else repr(out)[:50]
        except BaseException as e:  # noqa: BLE001
            sys.settrace(None)
            res["status"] = "exception"
            res["err"] = f"{type(e).__name__}: {str(e)[:150]}"

    th = threading.Thread(target=_run, daemon=True)
    th.start()
    th.join(float(inp.get("timeout", 6.0)))
    if th.is_alive():
        res["status"] = "timeout"
    payload = dict(res=res, events=EVENTS[:MAX_EVENTS], calls=CALLS[:MAX_EVENTS], state=STATE,
                   truncated=STATE["n_events"] > MAX_EVENTS)
    with open(out_path, "w") as f:
        f.write(json.dumps(payload, default=lambda o: list(o) if isinstance(o, tuple) else repr(o)[:30]))
    sys.stdout = sys.__stdout__
    os._exit(0)


if __name__ == "__main__":
    main()
