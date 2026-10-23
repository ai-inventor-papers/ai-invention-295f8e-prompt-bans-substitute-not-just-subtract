#!/usr/bin/env python3
"""Expansion-order tracer v9 -- CHILD process (stdlib only; run as `python -I -S tracer_v9.py` with a JSON job on stdin).

Extends the iteration-2 runtime tracer (vendor/exp9/labeller_ext/tracer.py: heapq / deque / queue proxies, a grid of
str-subclass rows that logs (row, col) reads, call tracking) with ONE global event stream per probe, in order:

  PUSH (0)  append / appendleft / add / put / insert / extend / extendleft on ANY object (AST rewrite of the method
            call), heapq.heappush / heapify / heappushpop / heapreplace (proxy), deque(...) constructor items, and
            item assignment of a cell key (d[cell] = v and a[r][c] = v, AST rewrite of the assignment target)
  POP  (1)  pop / popleft / remove / discard / popitem on ANY object (AST rewrite; the returned or removed item),
            heapq.heappop / heappushpop / heapreplace (proxy), queue.Queue / LifoQueue / PriorityQueue .get (proxy)
  READ (2)  grid[r][c] reads through the str-subclass rows
  CALL (3)  candidate-code function calls whose arguments contain an in-grid cell (a 2-int tuple/list argument, or
            two consecutive int arguments); the top-level solve() call is skipped
  ITER (4)  items yielded by a for-loop / comprehension over a list, deque, set or dict that was pushed to, or that
            is a seed frontier (<= 2 items) holding the start or goal cell when the loop starts

One event source per operation: methods are logged only by the AST wrapper (the deque / queue subclasses log only
their constructor items and .get), functions of heapq only by the proxy. Cell extraction follows tracer._cell():
the first in-grid 2-int pair, nested or trailing; for heap items the priority slot item[0] is skipped first.
Events are capped per probe (flag 'truncated'). Each probe runs in a daemon thread with a timeout; on a timeout the
child prints what it has and exits (the parent restarts it on the remaining probes).

Output: one JSON line per probe {"i", "events": [[t, r, c, s, cid, prio], ...], "strings", "valid", "path_len",
"exc", "timeout", "seconds", "grid_copied", "truncated"}; a final line {"done": true} or {"error": ...}.
"""

import ast
import collections
import heapq as _real_heapq
import io
import json
import os
import queue
import resource
import sys
import threading
import time
import types

FORBIDDEN = {"os", "subprocess", "socket", "shutil", "ctypes", "multiprocessing", "signal", "pty", "resource"}
POP_NAMES = {"pop", "popleft", "remove", "discard", "popitem"}
PUSH_NAMES = {"append", "appendleft", "add", "put", "insert", "extend", "extendleft"}
METHODS = POP_NAMES | PUSH_NAMES
CAP = 60000


class S:
    dims = None
    start = None
    goal = None
    events = []
    strings = {}
    cids = {}
    pushed = set()
    keep = []
    truncated = False
    on = False
    grid_copied = False


def _sid(s):
    k = S.strings.get(s)
    if k is None:
        k = S.strings[s] = len(S.strings)
    return k


def _cid(obj):
    k = id(obj)
    v = S.cids.get(k)
    if v is None:
        v = S.cids[k] = len(S.cids)
        S.keep.append(obj)
    return v


def _ok(a, b):
    d = S.dims
    return (type(a) is int and type(b) is int and 0 <= a < d[0] and 0 <= b < d[1])


def _pair(x):
    return isinstance(x, (tuple, list)) and len(x) == 2 and _ok(x[0], x[1])


def _path(x):
    """A carried path: a list of >= 2 cells (or a tuple of >= 3 cells); its cell is the LAST element."""
    if isinstance(x, list):
        return len(x) >= 2 and _pair(x[-1]) and _pair(x[0])
    if isinstance(x, tuple):
        return len(x) >= 3 and _pair(x[-1]) and _pair(x[0]) and _pair(x[1])
    return False


def _cell(item, prio_first=False):
    """First in-grid (row, col) int pair of an item: the item itself, the last cell of a carried path, a nested 2-int
    tuple/list (item[1:] first for heap items, whose item[0] is the priority), else the last two ints."""
    if S.dims is None:
        return None
    if isinstance(item, (tuple, list)):
        n = len(item)
        if n == 0:
            return None
        if n == 2 and _ok(item[0], item[1]):
            return (item[0], item[1])
        if _path(item):
            c = item[-1]
            return (c[0], c[1])
        if not prio_first and n >= 3 and _ok(item[0], item[1]):   # (r, c, ...) queue/stack items
            return (item[0], item[1])
        order = list(item[1:]) + [item[0]] if prio_first else list(item)
        for x in order:
            if _pair(x):
                return (x[0], x[1])
        for x in order:
            if _path(x):
                return (x[-1][0], x[-1][1])
        for x in order:
            if isinstance(x, (tuple, list)) and len(x) >= 2 and _ok(x[0], x[1]):
                return (x[0], x[1])
        if n >= 3 and _ok(item[-2], item[-1]):
            return (item[-2], item[-1])
    return None


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


def ev(t, cell, src, obj=None, prio=None):
    if not S.on or cell is None:
        return
    if len(S.events) >= CAP:
        S.truncated = True
        return
    S.events.append((t, cell[0], cell[1], _sid(src), _cid(obj) if obj is not None else -1,
                     None if prio is None or prio != prio else prio))


# ---------------------------------------------------------------------------------------------- AST wrappers
def _kind(obj, name, args):
    tn = type(obj).__name__
    if isinstance(obj, list):
        if name == "pop":
            if not args or args[0] == -1:
                return "list.pop"
            return "list.pop0" if args[0] == 0 else "list.popi"
        return "list." + name
    if isinstance(obj, _RealDeque):
        return "deque." + name
    if isinstance(obj, (set, frozenset)):
        return "set." + name
    if isinstance(obj, dict):
        return "dict." + name
    return tn + "." + name


def __tr_m(obj, name, *args, **kw):
    f = getattr(obj, name)
    if name in ("extend", "extendleft") and args and not isinstance(obj, (str, bytes)):
        items = list(args[0])
        res = f(items, *args[1:], **kw)
        if S.on:
            S.pushed.add(id(obj))
            for it in items:
                ev(0, _cell(it), _kind(obj, name, ()), obj)
        return res
    res = f(*args, **kw)
    if not S.on or isinstance(obj, (str, bytes)):
        return res
    if name in POP_NAMES:
        if name in ("remove", "discard") or (isinstance(obj, dict) and name == "pop"):
            item = args[0] if args else None
        elif name == "popitem":
            item = res[0] if isinstance(res, tuple) and res else res
        else:
            item = res
        ev(1, _cell(item), _kind(obj, name, args), obj, _prio(item))
    else:
        item = args[-1] if (name == "insert" and len(args) >= 2) else (args[0] if args else None)
        S.pushed.add(id(obj))
        ev(0, _cell(item), _kind(obj, name, ()), obj, _prio(item))
    return res


def __tr_k(key):
    if S.on:
        ev(0, _cell(key), "setitem", None)
    return key


def __tr_k2(a, b):
    if S.on and _ok(a, b) if S.dims else False:
        ev(0, (a, b), "setitem2", None)
    return b


def _iter_log(obj):
    for x in obj:
        ev(4, _cell(x), "iter", obj)
        yield x


def __tr_it(obj):
    """Frontier iteration: a list/deque/set/dict that was pushed to, or a seed frontier of <= 2 items holding the
    start or goal cell (tuples -- neighbour literals -- are never wrapped)."""
    if S.on and isinstance(obj, (list, _RealDeque, set, frozenset, dict)):
        hit = id(obj) in S.pushed
        if not hit and S.start is not None:
            try:
                hit = len(obj) <= 2 and (S.start in obj or S.goal in obj)
            except TypeError:
                hit = False
        if hit:
            return _iter_log(obj)
    return obj


def _simple(n):
    return all(isinstance(x, (ast.Name, ast.Constant, ast.BinOp, ast.UnaryOp, ast.Load, ast.operator, ast.unaryop,
                              ast.Attribute)) for x in ast.walk(n))


class Rewriter(ast.NodeTransformer):
    def visit_Call(self, node):
        self.generic_visit(node)
        f = node.func
        if isinstance(f, ast.Attribute) and f.attr in METHODS and not (isinstance(f.value, ast.Name) and
                                                                     f.value.id in ("heapq", "self", "super")):
            return ast.copy_location(ast.Call(func=ast.Name(id="__tr_m", ctx=ast.Load()),
                                              args=[f.value, ast.Constant(f.attr)] + node.args,
                                              keywords=node.keywords), node)
        return node

    def visit_Assign(self, node):
        self.generic_visit(node)
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Subscript):
            t = node.targets[0]
            if isinstance(t.value, ast.Subscript) and _simple(t.value.slice) and _simple(t.slice):
                t.slice = ast.Call(func=ast.Name(id="__tr_k2", ctx=ast.Load()),
                                   args=[_copy(t.value.slice), t.slice], keywords=[])
            elif not isinstance(t.slice, ast.Slice):
                t.slice = ast.Call(func=ast.Name(id="__tr_k", ctx=ast.Load()), args=[t.slice], keywords=[])
        return node

    def visit_For(self, node):
        self.generic_visit(node)
        node.iter = ast.Call(func=ast.Name(id="__tr_it", ctx=ast.Load()), args=[node.iter], keywords=[])
        return node

    def visit_comprehension(self, node):
        self.generic_visit(node)
        node.iter = ast.Call(func=ast.Name(id="__tr_it", ctx=ast.Load()), args=[node.iter], keywords=[])
        return node


def _copy(n):
    return ast.parse(ast.unparse(n), mode="eval").body


# ---------------------------------------------------------------------------------------------- proxies
def _mk_heap_proxy():
    m = types.ModuleType("heapq")

    def heappush(heap, item):
        _real_heapq.heappush(heap, item)
        S.pushed.add(id(heap))
        ev(0, _cell(item, True), "heap", heap, _prio(item))

    def heappop(heap):
        item = _real_heapq.heappop(heap)
        ev(1, _cell(item, True), "heap", heap, _prio(item))
        return item

    def heapify(x):
        _real_heapq.heapify(x)
        S.pushed.add(id(x))
        for it in x:
            ev(0, _cell(it, True), "heap", x, _prio(it))

    def heappushpop(heap, item):
        out = _real_heapq.heappushpop(heap, item)
        ev(0, _cell(item, True), "heap", heap, _prio(item))
        ev(1, _cell(out, True), "heap", heap, _prio(out))
        return out

    def heapreplace(heap, item):
        out = _real_heapq.heapreplace(heap, item)
        ev(1, _cell(out, True), "heap", heap, _prio(out))
        ev(0, _cell(item, True), "heap", heap, _prio(item))
        return out

    m.heappush, m.heappop, m.heapify = heappush, heappop, heapify
    m.heappushpop, m.heapreplace = heappushpop, heapreplace
    m.nsmallest, m.nlargest, m.merge = _real_heapq.nsmallest, _real_heapq.nlargest, _real_heapq.merge
    m.__all__ = ["heappush", "heappop", "heapify", "heapreplace", "merge", "nlargest", "nsmallest", "heappushpop"]
    return m


_RealDeque = collections.deque


class TDeque(_RealDeque):
    def __init__(self, iterable=(), maxlen=None):
        items = list(iterable)
        _RealDeque.__init__(self, items, maxlen)
        if S.on and items:
            S.pushed.add(id(self))
            for it in items:
                ev(0, _cell(it), "deque.init", self)


def _mk_queue_cls(base, kind):
    class TQ(base):
        def get(self, block=True, timeout=None):
            v = base.get(self, block, timeout)
            ev(1, _cell(v, kind == "pq"), kind + ".get", self, _prio(v))
            return v

        def get_nowait(self):
            return self.get(False)

    TQ.__name__ = base.__name__
    TQ.__qualname__ = base.__qualname__
    return TQ


class TRow(str):
    def __getitem__(self, c):
        if type(c) is int and S.on:
            if len(S.events) < CAP:
                S.events.append((2, self._r, c if c >= 0 else c + len(self), 0, -1, None))
            else:
                S.truncated = True
        return str.__getitem__(self, c)

    def __iter__(self):
        S.grid_copied = True
        return str.__iter__(self)


def make_grid(rows):
    out = []
    for i, s in enumerate(rows):
        r = TRow(s)
        r._r = i
        out.append(r)
    return out


_COORD = None


def _coordlike(name):
    """Parameter names that plausibly hold a row or column index (two consecutive int arguments count as a cell only
    under such names, so (depth, limit) or (g, bound) pairs are never read as cells)."""
    global _COORD
    if _COORD is None:
        import re as _re

        _COORD = _re.compile(r"^(r|c|x|y|i|j|row|col|rows?_?\w*|cols?_?\w*|\w*_(r|c|x|y|row|col)|n[rcxy]|c[rcxy]|"
                             r"[rcxy][0-9]|s[rc]|g[rc]|t[rc]|p[rc]|cur_?[rcxy]|new_?[rcxy]|next_?[rcxy]|\w*row|\w*col)$")
    return bool(_COORD.match(name))


def _arg_cell(frame):
    co = frame.f_code
    names = co.co_varnames[:co.co_argcount + co.co_kwonlyargcount]
    loc = frame.f_locals
    vals = [loc.get(n) for n in names]
    for v in vals:
        if isinstance(v, (tuple, list)) and len(v) == 2 and _ok(v[0], v[1]):
            return (v[0], v[1])
    for v in vals:                     # a carried path (or a one-cell path [start]): its last cell
        if isinstance(v, list) and v and _pair(v[-1]) and _pair(v[0]):
            return (v[-1][0], v[-1][1])
    for (na, a), (nb, b) in zip(zip(names, vals), list(zip(names, vals))[1:]):
        if _ok(a, b) and _coordlike(na) and _coordlike(nb):
            return (a, b)
    return None


def _gtrace(frame, event, arg):
    if event == "call" and S.on and frame.f_code.co_filename == "<candidate>":
        fb = frame.f_back
        if fb is not None and fb.f_code.co_filename == "<candidate>":
            try:
                c = _arg_cell(frame)
            except Exception:  # noqa: BLE001 - the tracer must never break the candidate
                c = None
            name = frame.f_code.co_name
            if c is not None and not name.startswith("<"):     # skip lambdas / genexpr key functions
                ev(3, c, "call:" + name + ("<self" if fb.f_code is frame.f_code else "<other"), None)
    return None


def screen(code):
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError):
        return "syntax_error", None
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name.split(".")[0] in FORBIDDEN:
                    return "forbidden_import", None
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.split(".")[0] in FORBIDDEN:
                return "forbidden_import", None
    return None, tree


def main():
    job = json.loads(sys.stdin.read())
    real_out = sys.stdout

    def emit(obj):
        real_out.write(json.dumps(obj, separators=(",", ":")) + "\n")
        real_out.flush()

    err, tree = screen(job["code"])
    if err:
        emit({"error": err})
        return
    try:
        tree = Rewriter().visit(tree)
        ast.fix_missing_locations(tree)
        code_obj = compile(tree, "<candidate>", "exec")
    except (SyntaxError, ValueError, TypeError, RecursionError) as e:
        emit({"error": "rewrite_failed:" + type(e).__name__})
        return
    mem = int(job.get("rlimit_as", 1024 ** 3))
    resource.setrlimit(resource.RLIMIT_AS, (mem, mem))
    sys.setrecursionlimit(20000)
    threading.stack_size(256 * 1024 * 1024)
    sys.stdout = io.StringIO()
    sys.stdin = io.StringIO("")
    hp = _mk_heap_proxy()
    sys.modules["heapq"] = hp
    collections.deque = TDeque
    queue.Queue = _mk_queue_cls(queue.Queue, "queue")
    queue.LifoQueue = _mk_queue_cls(queue.LifoQueue, "lifo")
    queue.PriorityQueue = _mk_queue_cls(queue.PriorityQueue, "pq")
    queue.SimpleQueue = queue.Queue
    mod = types.ModuleType("cand")
    mod.__file__ = "<candidate>"
    sys.modules["cand"] = mod
    import itertools
    import math

    mod.__dict__.update({"__tr_m": __tr_m, "__tr_k": __tr_k, "__tr_k2": __tr_k2, "__tr_it": __tr_it,
                         "heapq": hp, "heappush": hp.heappush, "heappop": hp.heappop, "heapify": hp.heapify,
                         "deque": TDeque, "collections": collections, "defaultdict": collections.defaultdict,
                         "math": math, "itertools": itertools, "queue": queue, "inf": float("inf")})
    box = {}

    def do_exec():
        try:
            exec(code_obj, mod.__dict__)
        except BaseException as e:  # noqa: BLE001
            box["exc"] = type(e).__name__

    th = threading.Thread(target=do_exec, daemon=True)
    th.start()
    th.join(10.0)
    if th.is_alive() or "exc" in box or not callable(mod.__dict__.get("solve")):
        emit({"error": "exec_timeout" if th.is_alive() else "exec_failed:" + str(box.get("exc"))})
        os._exit(0)
    solve = mod.__dict__["solve"]
    timeout = float(job.get("probe_timeout_s", 2.0))
    for i, pr in enumerate(job["probes"]):
        if i < int(job.get("first", 0)):
            continue
        grid, s, g = pr["grid"], tuple(pr["start"]), tuple(pr["goal"])
        S.dims, S.start, S.goal = (len(grid), len(grid[0])), s, g
        S.events, S.strings, S.cids, S.pushed, S.keep = [], {"read": 0}, {}, set(), []
        S.truncated, S.grid_copied = False, False
        res = {}
        args = (make_grid(grid), s, g)

        def target():
            sys.settrace(_gtrace)
            S.on = True
            try:
                res["out"] = solve(*args)
            except BaseException as e:  # noqa: BLE001
                res["exc"] = type(e).__name__
            finally:
                S.on = False
                sys.settrace(None)

        t0 = time.perf_counter()
        th = threading.Thread(target=target, daemon=True)
        th.start()
        th.join(timeout)
        dt = time.perf_counter() - t0
        alive = th.is_alive()
        S.on = False
        out = res.get("out")
        valid, plen = False, None
        if isinstance(out, (list, tuple)) and out:
            try:
                path = [(int(p[0]), int(p[1])) for p in out]
                valid = (path[0] == s and path[-1] == g and all(0 <= r < len(grid) and 0 <= c < len(grid[0])
                                                              and grid[r][c] == "." for r, c in path)
                         and all(abs(a - c) + abs(b - d) == 1 for (a, b), (c, d) in zip(path, path[1:])))
                plen = len(path)
            except (TypeError, ValueError, IndexError):
                valid = False
        elif isinstance(out, (list, tuple)) and not out:
            plen = 0
        strings = [None] * len(S.strings)
        for k, v in S.strings.items():
            strings[v] = k
        emit({"i": i, "events": S.events, "strings": strings, "valid": valid, "path_len": plen,
              "exc": res.get("exc"), "timeout": alive, "seconds": round(dt, 4), "grid_copied": S.grid_copied,
              "truncated": S.truncated})
        if alive:
            os._exit(0)
    emit({"done": True})
    os._exit(0)


if __name__ == "__main__":
    main()
