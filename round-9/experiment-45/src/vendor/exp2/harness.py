"""Sandbox harness: executed as `python -I harness.py job.json result.json` inside a resource-limited subprocess.

Modes
  tests : run solve() sequentially on the hidden tests with per-test itimer limits; fail fast.
  trace : run solve() on the labeller probe inputs with runtime instrumentation (heapq, deque, queue,
          list pops via sys.setprofile c_call/c_return, recursion depth, start re-expansions, line counts).
The harness never imports anything from the workspace (-I isolates it); everything comes from the job JSON.
"""
import collections
import heapq
import io
import json
import queue
import resource
import signal
import sys
import time

JOB, RES = sys.argv[1], sys.argv[2]
job = json.load(open(JOB))
mem = int(job.get("mem_bytes", 2 * 1024**3))
try:
    resource.setrlimit(resource.RLIMIT_AS, (mem, mem))
except (ValueError, OSError):
    pass
sys.setrecursionlimit(20000)


class _Timeout(BaseException):
    pass


def _alarm(signum, frame):
    raise _Timeout()


signal.signal(signal.SIGALRM, _alarm)
_result = {"ok": False}


def _write():
    with open(RES, "w") as fh:
        json.dump(_result, fh)


def _conv_t1(args):
    grid, start, goal = args
    return [list(grid), tuple(start), tuple(goal)]


def _conv_t2(args):
    n, edges, s, t = args
    return [n, [tuple(e) for e in edges], s, t]


def _valid_t1(out, test):
    grid, start, goal = test["args"]
    start, goal = tuple(start), tuple(goal)
    R, C = len(grid), len(grid[0])
    if not test["reachable"]:
        return isinstance(out, (list, tuple)) and len(out) == 0
    if not isinstance(out, (list, tuple)) or len(out) == 0:
        return False
    try:
        cells = [tuple(int(v) for v in c) for c in out]
    except (TypeError, ValueError):
        return False
    if any(len(c) != 2 for c in cells):
        return False
    if cells[0] != start or cells[-1] != goal:
        return False
    for (r, c) in cells:
        if not (0 <= r < R and 0 <= c < C) or grid[r][c] != ".":
            return False
    for a, b in zip(cells, cells[1:]):
        if abs(a[0] - b[0]) + abs(a[1] - b[1]) != 1:
            return False
    return True


def _valid_t2(out, test):
    exp = test["expected"]
    if isinstance(out, bool) or not isinstance(out, (int, float)):
        return False
    return out == exp


def _load_solve(code):
    ns = {"__name__": "__solution__", "__builtins__": __builtins__}
    old_out = sys.stdout
    sys.stdout = io.StringIO()
    try:
        exec(compile(code, "<program>", "exec"), ns)
    finally:
        sys.stdout = old_out
    fn = ns.get("solve")
    if not callable(fn):
        raise NameError("no solve()")
    return fn


def run_tests():
    task = job["task"]
    conv = _conv_t1 if task == "t1" else _conv_t2
    valid = _valid_t1 if task == "t1" else _valid_t2
    t_all = time.time()
    _result.update({"n_pass": 0, "n_tests": len(job["tests"]), "fail_index": None, "fail_kind": None, "times": []})
    try:
        signal.setitimer(signal.ITIMER_REAL, 10.0)
        solve = _load_solve(job["code"])
        signal.setitimer(signal.ITIMER_REAL, 0)
    except _Timeout:
        _result.update({"ok": True, "passed": False, "fail_kind": "load_timeout", "wall_s": time.time() - t_all})
        return
    except BaseException as e:  # noqa: BLE001 -- untrusted program; record any load failure
        signal.setitimer(signal.ITIMER_REAL, 0)
        _result.update({"ok": True, "passed": False, "fail_kind": f"load_error:{type(e).__name__}:{str(e)[:200]}",
                        "wall_s": time.time() - t_all})
        return
    for i, (test, lim) in enumerate(zip(job["tests"], job["limits"])):
        args = conv(json.loads(json.dumps(test["args"])))
        old_out = sys.stdout
        sys.stdout = io.StringIO()
        t0 = time.time()
        try:
            signal.setitimer(signal.ITIMER_REAL, float(lim))
            out = solve(*args)
            signal.setitimer(signal.ITIMER_REAL, 0)
            ok = valid(out, test)
            kind = None if ok else "wrong_answer"
        except _Timeout:
            ok, kind = False, "timeout"
        except RecursionError:
            signal.setitimer(signal.ITIMER_REAL, 0)
            ok, kind = False, "recursion_error"
        except MemoryError:
            signal.setitimer(signal.ITIMER_REAL, 0)
            ok, kind = False, "memory_error"
        except BaseException as e:  # noqa: BLE001
            signal.setitimer(signal.ITIMER_REAL, 0)
            ok, kind = False, f"exception:{type(e).__name__}"
        finally:
            sys.stdout = old_out
        _result["times"].append(round(time.time() - t0, 5))
        if not ok:
            _result.update({"ok": True, "passed": False, "fail_index": i, "fail_kind": kind,
                            "wall_s": time.time() - t_all})
            return
        _result["n_pass"] += 1
    _result.update({"ok": True, "passed": True, "wall_s": time.time() - t_all})


# ----------------------------------------------------------------------------------------------- trace mode
class _Rec:
    def __init__(self):
        self.reset()

    def reset(self):
        self.heaps = {}          # id(list) -> list of pushed items (json-safe repr)
        self.heap_pops = {}      # id(list) -> list of popped items
        self.deq = {}            # id(deque) -> {"popleft": n, "pop": n, "appendleft": n, "append": n, "popped": [...]}
        self.lists = {}          # id(list) -> {"front": n, "back": n, "popped": [...]} via profile
        self.queues = {}         # id(Queue) -> {"kind": .., "get": n, "popped": [...]}
        self.calls = collections.Counter()
        self.max_depth = 0
        self.depth = 0
        self.start_calls = 0
        self.start_calls_fn = collections.Counter()
        self.lines = collections.Counter()
        self.sorts = 0
        self.mins = 0


REC = _Rec()
MAXREC = 5000


def _js(x, depth=0):
    if isinstance(x, (int, float, str, bool)) or x is None:
        return x
    if depth > 3:
        return None
    if isinstance(x, (tuple, list)):
        if len(x) > 50:
            return [_js(x[0], depth + 1), "...", _js(x[-1], depth + 1)]
        return [_js(v, depth + 1) for v in x]
    return repr(x)[:40]


_orig = {k: getattr(heapq, k) for k in ("heappush", "heappop", "heapify", "heapreplace", "heappushpop")}


def _hp_push(h, item):
    lst = REC.heaps.setdefault(id(h), [])
    if len(lst) < MAXREC:
        lst.append(_js(item))
    return _orig["heappush"](h, item)


def _hp_pop(h):
    item = _orig["heappop"](h)
    lst = REC.heap_pops.setdefault(id(h), [])
    if len(lst) < MAXREC:
        lst.append(_js(item))
    REC.heaps.setdefault(id(h), [])
    return item


def _hp_heapify(h):
    lst = REC.heaps.setdefault(id(h), [])
    for it in h[:MAXREC]:
        lst.append(_js(it))
    return _orig["heapify"](h)


def _hp_replace(h, item):
    out = _orig["heapreplace"](h, item)
    REC.heaps.setdefault(id(h), []).append(_js(item))
    REC.heap_pops.setdefault(id(h), []).append(_js(out))
    return out


def _hp_pushpop(h, item):
    out = _orig["heappushpop"](h, item)
    REC.heaps.setdefault(id(h), []).append(_js(item))
    REC.heap_pops.setdefault(id(h), []).append(_js(out))
    return out


_OrigDeque = collections.deque


class RecDeque(_OrigDeque):
    def _st(self):
        return REC.deq.setdefault(id(self), {"popleft": 0, "pop": 0, "appendleft": 0, "append": 0, "popped": []})

    def popleft(self):
        x = _OrigDeque.popleft(self)
        st = self._st()
        st["popleft"] += 1
        if len(st["popped"]) < MAXREC:
            st["popped"].append(["L", _js(x)])
        return x

    def pop(self):
        x = _OrigDeque.pop(self)
        st = self._st()
        st["pop"] += 1
        if len(st["popped"]) < MAXREC:
            st["popped"].append(["R", _js(x)])
        return x

    def appendleft(self, x):
        self._st()["appendleft"] += 1
        return _OrigDeque.appendleft(self, x)

    def append(self, x):
        self._st()["append"] += 1
        return _OrigDeque.append(self, x)


def _wrap_queue(cls, kind):
    class W(cls):
        def get(self, *a, **k):
            x = cls.get(self, *a, **k)
            st = REC.queues.setdefault(id(self), {"kind": kind, "get": 0, "popped": [], "put": []})
            st["get"] += 1
            if len(st["popped"]) < MAXREC:
                st["popped"].append(_js(x))
            return x

        def put(self, item, *a, **k):
            st = REC.queues.setdefault(id(self), {"kind": kind, "get": 0, "popped": [], "put": []})
            if len(st["put"]) < MAXREC:
                st["put"].append(_js(item))
            return cls.put(self, item, *a, **k)

    W.__name__ = cls.__name__
    return W


_pending_pop = {}


def _profile(frame, event, arg):
    if event == "call":
        if frame.f_code.co_filename == "<program>":
            REC.depth += 1
            REC.calls[frame.f_code.co_name] += 1
            if REC.depth > REC.max_depth:
                REC.max_depth = REC.depth
            st = job.get("_cur_start")
            if st is not None and frame.f_code.co_name != "solve":
                code = frame.f_code
                argv = [frame.f_locals.get(nm) for nm in code.co_varnames[:code.co_argcount]]
                hit = any(isinstance(v, (tuple, list)) and len(v) == 2 and list(v) == st for v in argv)
                if not hit:
                    ints = [v for v in argv if isinstance(v, int) and not isinstance(v, bool)]
                    hit = any(ints[i] == st[0] and ints[i + 1] == st[1] for i in range(len(ints) - 1))
                if hit:
                    REC.start_calls_fn[code.co_name] += 1
    elif event == "return":
        if frame.f_code.co_filename == "<program>":
            REC.depth -= 1
    elif event == "c_call":
        nm = getattr(arg, "__name__", "")
        if nm == "sort" and isinstance(getattr(arg, "__self__", None), list):
            REC.sorts += 1
        elif nm in ("min", "sorted") and getattr(arg, "__self__", None) is not None and \
                type(arg.__self__).__name__ == "module":
            REC.mins += 1
        if nm == "pop" and isinstance(getattr(arg, "__self__", None), list):
            lst = arg.__self__
            if lst:
                _pending_pop[id(lst)] = (len(lst), lst[0], lst[-1])
    elif event == "c_return":
        if getattr(arg, "__name__", "") == "pop" and isinstance(getattr(arg, "__self__", None), list):
            lst = arg.__self__
            pre = _pending_pop.pop(id(lst), None)
            if pre is not None and len(lst) == pre[0] - 1:
                st = REC.lists.setdefault(id(lst), {"front": 0, "back": 0, "popped": []})
                if pre[0] == 1:
                    side = "back"
                elif lst and lst[0] is not pre[1] and (lst[-1] is pre[2]):
                    side = "front"
                else:
                    side = "back"
                st[side] += 1
                if len(st["popped"]) < MAXREC:
                    st["popped"].append([side[0].upper(), _js(pre[1] if side == "front" else pre[2])])


def _tracer(frame, event, arg):
    if frame.f_code.co_filename != "<program>":
        return None
    if event == "line":
        REC.lines[frame.f_lineno] += 1
    return _tracer


def run_trace():
    task = job["task"]
    conv = _conv_t1 if task == "t1" else _conv_t2
    for k, f in (("heappush", _hp_push), ("heappop", _hp_pop), ("heapify", _hp_heapify),
                 ("heapreplace", _hp_replace), ("heappushpop", _hp_pushpop)):
        setattr(heapq, k, f)
    collections.deque = RecDeque
    queue.Queue = _wrap_queue(queue.Queue, "fifo")
    queue.LifoQueue = _wrap_queue(queue.LifoQueue, "lifo")
    queue.PriorityQueue = _wrap_queue(queue.PriorityQueue, "prio")
    try:
        signal.setitimer(signal.ITIMER_REAL, 10.0)
        solve = _load_solve(job["code"])
        signal.setitimer(signal.ITIMER_REAL, 0)
    except BaseException as e:  # noqa: BLE001
        signal.setitimer(signal.ITIMER_REAL, 0)
        _result.update({"ok": True, "load_error": f"{type(e).__name__}:{str(e)[:200]}", "probes": []})
        return
    probes = []
    for probe in job["probes"]:
        REC.reset()
        _pending_pop.clear()
        args = conv(json.loads(json.dumps(probe["args"])))
        if task == "t1":
            job["_cur_start"] = list(probe["args"][1])
            job["_cur_start_node"] = None
        else:
            job["_cur_start"] = None
            job["_cur_start_node"] = probe["args"][2]
        err = None
        old_out = sys.stdout
        sys.stdout = io.StringIO()
        try:
            signal.setitimer(signal.ITIMER_REAL, float(job.get("probe_limit", 20.0)))
            sys.setprofile(_profile)
            sys.settrace(_tracer)
            out = solve(*args)
        except _Timeout:
            err = "timeout"
            out = None
        except BaseException as e:  # noqa: BLE001
            err = f"{type(e).__name__}"
            out = None
        finally:
            sys.settrace(None)
            sys.setprofile(None)
            signal.setitimer(signal.ITIMER_REAL, 0)
            sys.stdout = old_out
        probes.append({
            "name": probe["name"], "error": err, "out": _js(out),
            "heaps": [{"pushes": v, "pops": REC.heap_pops.get(k, [])} for k, v in REC.heaps.items()],
            "deques": list(REC.deq.values()),
            "lists": [v for v in REC.lists.values() if v["front"] + v["back"] > 0],
            "queues": list(REC.queues.values()),
            "calls": dict(REC.calls), "max_depth": REC.max_depth,
            "start_calls": max(REC.start_calls_fn.values()) if REC.start_calls_fn else 0,
            "start_calls_fn": dict(REC.start_calls_fn),
            "sorts": REC.sorts, "mins": REC.mins,
            "max_line_count": max(REC.lines.values()) if REC.lines else 0,
            "line_counts_top": REC.lines.most_common(5),
        })
    _result.update({"ok": True, "probes": probes})


try:
    if job["mode"] == "tests":
        run_tests()
    else:
        run_trace()
except BaseException as e:  # noqa: BLE001
    _result.update({"ok": False, "harness_error": f"{type(e).__name__}:{str(e)[:300]}"})
_write()
