"""Runtime-signature tracer (stdlib only).  Executed as: python3.12 -I -S tracer.py < payload.json

payload: {"code", "probes": [{"name", "kwargs_json", "wrap": {arg: "clist_int"|"clist_pairs"|"cstr"|"cint"},
          "trace_lines": bool}], "timeout"}
Prints one JSON feature line per probe.  Instrumentation: heapq / bisect proxy modules, recording deque and
queue subclasses, functools.lru_cache/cache and Counter.most_common wrappers, patched builtins.sorted,
sys.setprofile (user calls, self-recursion, C calls, list.pop FIFO vs LIFO by bytecode), instrumented inputs
(CInt comparisons/hash/add, CList reads/writes/full passes, CStr method calls and read positions),
sys.settrace line counts (scaling probes) and a scan of list/dict sizes in returning user frames.
"""

import builtins
import collections
import dis
import functools
import heapq as _real_heapq
import bisect as _real_bisect
import io
import json
import os
import queue as _real_queue
import sys
import threading
import time
import types

CAND = "<candidate>"
ST = {}


def reset():
    ST.clear()
    ST.update({"calls": collections.Counter(), "selfrec": collections.Counter(), "maxdepth": 0, "maxrec": 0,
               "c_calls": collections.Counter(), "pop_fifo": 0, "pop_lifo": 0, "pop_other": 0,
               "heap": collections.Counter(), "heapify_sizes": [], "heap_max_size": 0, "nsel_args": [],
               "bisect": collections.Counter(), "deque": collections.Counter(), "queue": collections.Counter(),
               "sorted_lens": [], "sort_lens": [], "sorted_key": 0, "sorted_by_second": 0, "sorted_by_first": 0,
               "lru": 0, "most_common": collections.Counter(),
               "cint": collections.Counter(), "clist_get": 0, "clist_set": 0, "clist_iter": 0, "clist_slice": 0,
               "clist_idx": [], "clist_set_idx": [], "cstr": collections.Counter(), "cstr_idx": [],
               "lines": 0, "list_lens": collections.Counter(), "dict_sizes": collections.Counter(),
               "user_classes": 0, "returns_scanned": 0})


reset()


# ----------------------------------------------------------------------------- instrumented inputs
class CInt(int):
    __slots__ = ()

    def __hash__(self):
        ST["cint"]["hash"] += 1
        return int.__hash__(self)

    def __eq__(self, o):
        ST["cint"]["eq"] += 1
        return int.__eq__(self, o)

    def __ne__(self, o):
        ST["cint"]["eq"] += 1
        return int.__ne__(self, o)

    def __lt__(self, o):
        ST["cint"]["cmp"] += 1
        return int.__lt__(self, o)

    def __le__(self, o):
        ST["cint"]["cmp"] += 1
        return int.__le__(self, o)

    def __gt__(self, o):
        ST["cint"]["cmp"] += 1
        return int.__gt__(self, o)

    def __ge__(self, o):
        ST["cint"]["cmp"] += 1
        return int.__ge__(self, o)

    def __add__(self, o):
        ST["cint"]["add"] += 1
        return int.__add__(self, o)

    def __radd__(self, o):
        ST["cint"]["add"] += 1
        return int.__radd__(self, o)

    def __sub__(self, o):
        ST["cint"]["sub"] += 1
        return int.__sub__(self, o)

    def __rsub__(self, o):
        ST["cint"]["sub"] += 1
        return int.__rsub__(self, o)


class CList(list):
    def __getitem__(self, i):
        if isinstance(i, slice):
            ST["clist_slice"] += 1
        else:
            ST["clist_get"] += 1
            if len(ST["clist_idx"]) < 4000:
                ST["clist_idx"].append(int(i) if not isinstance(i, bool) else 0)
        return list.__getitem__(self, i)

    def __setitem__(self, i, v):
        ST["clist_set"] += 1
        if len(ST["clist_set_idx"]) < 1000 and not isinstance(i, slice):
            ST["clist_set_idx"].append(int(i))
        return list.__setitem__(self, i, v)

    def __iter__(self):
        ST["clist_iter"] += 1
        return list.__iter__(self)


class CStr(str):
    def __getitem__(self, i):
        if isinstance(i, slice):
            ST["cstr"]["slice"] += 1
            if len(ST["cstr_idx"]) < 6000:
                ST["cstr_idx"].append(i.start if i.start is not None else 0)
        else:
            ST["cstr"]["get"] += 1
            if len(ST["cstr_idx"]) < 6000:
                ST["cstr_idx"].append(int(i))
        return str.__getitem__(self, i)

    def __iter__(self):
        ST["cstr"]["iter"] += 1
        return str.__iter__(self)

    def __eq__(self, o):
        ST["cstr"]["eq"] += 1
        return str.__eq__(self, o)

    def __ne__(self, o):
        ST["cstr"]["eq"] += 1
        return str.__ne__(self, o)

    __hash__ = str.__hash__

    def __add__(self, o):
        ST["cstr"]["concat"] += 1
        return str.__add__(self, o)

    def __radd__(self, o):
        ST["cstr"]["concat"] += 1
        return str.__add__(o, self)

    def __contains__(self, o):
        ST["cstr"]["contains"] += 1
        return str.__contains__(self, o)

    def find(self, *a):
        ST["cstr"]["find"] += 1
        return str.find(self, *a)

    def index(self, *a):
        ST["cstr"]["index"] += 1
        return str.index(self, *a)

    def rfind(self, *a):
        ST["cstr"]["find"] += 1
        return str.rfind(self, *a)

    def count(self, *a):
        ST["cstr"]["count"] += 1
        return str.count(self, *a)

    def startswith(self, *a):
        ST["cstr"]["startswith"] += 1
        return str.startswith(self, *a)

    def split(self, *a):
        ST["cstr"]["split"] += 1
        return str.split(self, *a)

    def partition(self, *a):
        ST["cstr"]["split"] += 1
        return str.partition(self, *a)


def wrap_value(v, how):
    if how == "clist_int":
        return CList(CInt(x) for x in v)
    if how == "clist_pairs":
        return CList([CInt(a), CInt(b)] for a, b in v)
    if how == "cstr":
        return CStr(v)
    if how == "cint":
        return CInt(v)
    return v


# ----------------------------------------------------------------------------- proxies
def _heap_size(h):
    try:
        n = len(h)
        if n > ST["heap_max_size"]:
            ST["heap_max_size"] = n
    except TypeError:
        pass


def _mk_heap(name):
    real = getattr(_real_heapq, name)

    def w(*a, **k):
        ST["heap"][name] += 1
        if name == "heapify" and a:
            ST["heapify_sizes"].append(len(a[0]))
        if name in ("nlargest", "nsmallest") and a:
            ST["nsel_args"].append(a[0])
        r = real(*a, **k)
        if name in ("heappush", "heappushpop", "heapreplace", "heapify") and a:
            _heap_size(a[0])
        return r
    w.__name__ = name
    return w


heapq_proxy = types.ModuleType("heapq")
for _n in dir(_real_heapq):
    if not _n.startswith("__"):
        setattr(heapq_proxy, _n, getattr(_real_heapq, _n))
for _n in ("heappush", "heappop", "heapify", "heappushpop", "heapreplace", "nlargest", "nsmallest", "merge",
           "_heappop_max", "_heapify_max", "heappush_max", "heappop_max", "heapify_max"):
    if hasattr(_real_heapq, _n):
        setattr(heapq_proxy, _n, _mk_heap(_n))


def _mk_bisect(name):
    real = getattr(_real_bisect, name)

    def w(*a, **k):
        ST["bisect"][name] += 1
        return real(*a, **k)
    w.__name__ = name
    return w


bisect_proxy = types.ModuleType("bisect")
for _n in dir(_real_bisect):
    if not _n.startswith("__"):
        setattr(bisect_proxy, _n, getattr(_real_bisect, _n))
for _n in ("bisect", "bisect_left", "bisect_right", "insort", "insort_left", "insort_right"):
    setattr(bisect_proxy, _n, _mk_bisect(_n))

_RealDeque = collections.deque


class RDeque(_RealDeque):
    def __init__(self, *a, **k):
        ST["deque"]["new"] += 1
        _RealDeque.__init__(self, *a, **k)

    def popleft(self):
        ST["deque"]["popleft"] += 1
        return _RealDeque.popleft(self)

    def pop(self):
        ST["deque"]["pop"] += 1
        return _RealDeque.pop(self)

    def append(self, x):
        ST["deque"]["append"] += 1
        return _RealDeque.append(self, x)

    def appendleft(self, x):
        ST["deque"]["appendleft"] += 1
        return _RealDeque.appendleft(self, x)

    def extend(self, it):
        ST["deque"]["extend"] += 1
        return _RealDeque.extend(self, it)


class RQueue(_real_queue.Queue):
    def get(self, *a, **k):
        ST["queue"]["fifo_get"] += 1
        return _real_queue.Queue.get(self, *a, **k)


class RLifo(_real_queue.LifoQueue):
    def get(self, *a, **k):
        ST["queue"]["lifo_get"] += 1
        return _real_queue.LifoQueue.get(self, *a, **k)


class RPrio(_real_queue.PriorityQueue):
    def get(self, *a, **k):
        ST["queue"]["prio_get"] += 1
        return _real_queue.PriorityQueue.get(self, *a, **k)


_real_sorted = builtins.sorted


def rsorted(iterable, *a, **k):
    lst = list(iterable)
    ST["sorted_lens"].append(len(lst))
    if k.get("key") is not None:
        ST["sorted_key"] += 1
    r = _real_sorted(lst, *a, **k)
    try:
        if len(r) >= 3 and all(isinstance(x, (list, tuple)) and len(x) >= 2 for x in r[:50]):
            sec = [x[1] for x in r]
            fst = [x[0] for x in r]
            if all(sec[i] <= sec[i + 1] for i in range(len(sec) - 1)) and not all(fst[i] <= fst[i + 1] for i in range(len(fst) - 1)):
                ST["sorted_by_second"] += 1
            elif all(fst[i] <= fst[i + 1] for i in range(len(fst) - 1)):
                ST["sorted_by_first"] += 1
    except (TypeError, IndexError):
        pass
    return r


_real_lru = functools.lru_cache
_real_cache = getattr(functools, "cache", None)


def rlru(*a, **k):
    ST["lru"] += 1
    return _real_lru(*a, **k)


def rcache(f):
    ST["lru"] += 1
    return _real_lru(maxsize=None)(f)


_real_mc = collections.Counter.most_common


def rmost_common(self, n=None):
    ST["most_common"]["none" if n is None else "n"] += 1
    if n is not None:
        ST["heap"]["nlargest"] += 1
        ST["nsel_args"].append(n)
    return _real_mc(self, n)


def install():
    sys.modules["heapq"] = heapq_proxy
    sys.modules["bisect"] = bisect_proxy
    collections.deque = RDeque
    _real_queue.Queue = RQueue
    _real_queue.LifoQueue = RLifo
    _real_queue.PriorityQueue = RPrio
    builtins.sorted = rsorted
    functools.lru_cache = rlru
    if _real_cache is not None:
        functools.cache = rcache
    collections.Counter.most_common = rmost_common


# ----------------------------------------------------------------------------- profiling
_CALLINFO = {}


def _call_info(code):
    info = _CALLINFO.get(code)
    if info is None:
        info = {}
        prev = None
        for ins in dis.get_instructions(code):
            if ins.opname.startswith("CALL"):
                zero_const = prev is not None and prev.opname == "LOAD_CONST" and prev.argval == 0 and ins.arg == 1
                info[ins.offset] = (ins.arg, zero_const)
            if ins.opname != "CACHE":
                prev = ins
        _CALLINFO[code] = info
    return info


def make_profiler():
    stack = []

    def prof(frame, event, arg):
        if event == "call":
            code = frame.f_code
            if code.co_filename == CAND:
                ST["calls"][code.co_name] += 1
                cnt = sum(1 for c in stack if c is code)
                if stack and stack[-1] is code:
                    ST["selfrec"][code.co_name] += 1
                if cnt + 1 > ST["maxrec"]:
                    ST["maxrec"] = cnt + 1
                stack.append(code)
                if len(stack) > ST["maxdepth"]:
                    ST["maxdepth"] = len(stack)
        elif event == "return":
            code = frame.f_code
            if code.co_filename == CAND:
                if stack and stack[-1] is code:
                    stack.pop()
                elif code in stack:
                    while stack and stack.pop() is not code:
                        pass
                if ST["returns_scanned"] < 400:
                    ST["returns_scanned"] += 1
                    try:
                        for v in frame.f_locals.values():
                            if type(v) is list and len(v) > 1:
                                ST["list_lens"][len(v)] += 1
                            elif type(v) is dict and len(v) > 1:
                                ST["dict_sizes"][len(v)] += 1
                    except Exception:  # noqa: BLE001
                        pass
        elif event == "c_call":
            if frame.f_code.co_filename != CAND:
                return
            name = getattr(arg, "__name__", "?")
            ST["c_calls"][name] += 1
            if name == "pop":
                self_obj = getattr(arg, "__self__", None)
                if type(self_obj) is list or isinstance(self_obj, CList):
                    info = _call_info(frame.f_code).get(frame.f_lasti)
                    if info is None:
                        ST["pop_other"] += 1
                    elif info[0] == 0:
                        ST["pop_lifo"] += 1
                    elif info[1]:
                        ST["pop_fifo"] += 1
                    else:
                        ST["pop_other"] += 1
            elif name == "sort":
                self_obj = getattr(arg, "__self__", None)
                if isinstance(self_obj, list):
                    ST["sort_lens"].append(len(self_obj))
    return prof


def make_line_tracer():
    def local(frame, event, arg):
        if event == "line":
            ST["lines"] += 1
        return local

    def glob(frame, event, arg):
        if frame.f_code.co_filename == CAND:
            return local
        return None
    return glob


def summarize():
    s = {}
    for k, v in list(ST.items()):
        if isinstance(v, collections.Counter):
            items = _real_sorted(dict.items(v), key=lambda kv: -kv[1])[:60]
            s[k] = {str(a): b for a, b in items}
        else:
            s[k] = v
    s["clist_idx"] = ST["clist_idx"][:400]
    s["cstr_idx"] = ST["cstr_idx"][:1500]
    s["clist_set_idx"] = ST["clist_set_idx"][:200]
    s["heapify_sizes"] = ST["heapify_sizes"][:20]
    s["sorted_lens"] = ST["sorted_lens"][:50]
    s["sort_lens"] = ST["sort_lens"][:50]
    s["nsel_args"] = [a if isinstance(a, int) else -1 for a in ST["nsel_args"][:20]]
    return s


def main():
    payload = json.loads(sys.stdin.read())
    sys.stdin = io.StringIO("")
    out = sys.stdout
    install()
    for m in ("collections", "functools", "itertools", "math", "random", "typing", "re", "string", "operator",
              "copy", "array", "queue", "dataclasses", "statistics", "time"):
        try:
            __import__(m)
        except ImportError:
            pass
    sys.setrecursionlimit(10**6)
    threading.stack_size(512 * 1024 * 1024)
    ns = {"__name__": "__candidate__", "__builtins__": builtins}
    try:
        sys.stdout = io.StringIO()
        exec(compile(payload["code"], CAND, "exec"), ns)
        sys.stdout = out
    except BaseException as e:  # noqa: BLE001
        sys.stdout = out
        out.write(json.dumps({"probe": None, "error": f"load: {type(e).__name__}: {e}"[:200]}) + "\n")
        return
    ST["user_classes"] = sum(1 for v in ns.values() if isinstance(v, type) and getattr(v, "__module__", "") == "__candidate__")
    n_classes = ST["user_classes"]
    solve = ns.get("solve")
    if not callable(solve):
        out.write(json.dumps({"probe": None, "error": "no solve()"}) + "\n")
        return
    for p in payload["probes"]:
        reset()
        ST["user_classes"] = n_classes
        raw = json.loads(p["kwargs_json"])
        kwargs = {k: wrap_value(v, p.get("wrap", {}).get(k)) for k, v in raw.items()}
        box = {}
        trace_lines = p.get("trace_lines", False)

        def target():
            sys.setprofile(make_profiler())
            if trace_lines:
                sys.settrace(make_line_tracer())
            try:
                t0 = time.perf_counter()
                box["r"] = solve(**kwargs)
                box["t"] = time.perf_counter() - t0
            except BaseException as e:  # noqa: BLE001
                box["e"] = f"{type(e).__name__}: {e}"[:200]
            finally:
                sys.settrace(None)
                sys.setprofile(None)

        sys.stdout = io.StringIO()
        th = threading.Thread(target=target, daemon=True)
        th.start()
        th.join(payload.get("timeout", 10.0))
        sys.stdout = out
        if th.is_alive():
            out.write(json.dumps({"probe": p["name"], "error": "timeout", "features": summarize()}) + "\n")
            out.flush()
            os._exit(0)
        res = box.get("r")
        try:
            res_json = json.loads(json.dumps(res, default=lambda o: int(o) if isinstance(o, int) else str(o)))
        except (TypeError, ValueError):
            res_json = str(res)[:200]
        out.write(json.dumps({"probe": p["name"], "error": box.get("e"), "result": res_json,
                              "features": summarize()}) + "\n")
        out.flush()


if __name__ == "__main__":
    main()
