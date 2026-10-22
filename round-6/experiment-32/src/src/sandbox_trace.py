"""Child side of the runtime tracer (run as `python -I -S sandbox_trace.py` with a JSON payload on stdin).

For every probe input it records, inside the user's code only (filename '<user>'):
  (a) c_calls: sys.setprofile 'c_call' counts by C-function qualname (sorted, list.sort, heappush, bisect_left, isqrt,
      sqrt, ord, str.count, list.insert, ...) and the ordered sequence of selected calls (heap/bisect/insert);
  (b) ops: an instrumented element type -- TracedInt (int subclass) counts + - * // / % ** ^ & | >> << unary-minus,
      the six comparisons, __hash__ and __index__; TracedStr/TracedChar count __hash__, comparisons and iteration;
      `traj` keeps the other operand of comparisons / floor-divisions involving a traced scalar (B4 trajectories);
  (c) user_calls and max_depth of user-defined Python functions (sys.settrace 'call' events);
  (d) lines: line events in user code (loop-iteration growth across two probe sizes);
  (e) patched constructors: itertools.combinations/permutations/product, collections.Counter/defaultdict/deque.
A program that strips the instrumentation (e.g. int(x)) shows zero element ops: the rule then returns None
('untraceable') and the AST label is used with a flag.
payload = {"code": str, "probes": [{"name", "args", "wrap": [kind per arg], "expected"}], "limit": float}
"""

import collections
import itertools
import json
import signal
import sys
import time

C = collections.Counter()
TRAJ = []
SEQ = []
SEQ_NAMES = {"heappush", "heappop", "heapify", "heappushpop", "heapreplace", "bisect_left", "bisect_right", "bisect",
             "insort", "insort_left", "insort_right", "list.insert", "sorted", "list.sort", "nsmallest", "nlargest"}
TRACE_SCALAR = [False]


def _num(o):
    return int.__int__(o) if isinstance(o, int) and not isinstance(o, bool) else o


def _t(op, other=None):
    C[op] += 1
    if TRACE_SCALAR[0] and other is not None and len(TRAJ) < 20000:
        try:
            TRAJ.append((op, int(other) if isinstance(other, int) else float(other)))
        except (TypeError, ValueError, OverflowError):
            pass


class TracedInt(int):
    def __add__(self, o): _t("add"); return int.__add__(int(self), _num(o))
    def __radd__(self, o): _t("add"); return int.__radd__(int(self), _num(o))
    def __sub__(self, o): _t("sub"); return int.__sub__(int(self), _num(o))
    def __rsub__(self, o): _t("sub"); return int.__rsub__(int(self), _num(o))
    def __mul__(self, o): _t("mul"); return int.__mul__(int(self), _num(o))
    def __rmul__(self, o): _t("mul"); return int.__rmul__(int(self), _num(o))
    def __floordiv__(self, o): _t("floordiv", o); return int.__floordiv__(int(self), _num(o))
    def __rfloordiv__(self, o): _t("rfloordiv"); return int.__rfloordiv__(int(self), _num(o))
    def __truediv__(self, o): _t("truediv", o); return int.__truediv__(int(self), _num(o))
    def __rtruediv__(self, o): _t("rtruediv"); return int.__rtruediv__(int(self), _num(o))
    def __mod__(self, o): _t("mod"); return int.__mod__(int(self), _num(o))
    def __rmod__(self, o): _t("mod"); return int.__rmod__(int(self), _num(o))
    def __pow__(self, o, m=None):
        _t("pow"); C["pow_half"] += int(isinstance(o, float) and abs(o - 0.5) < 1e-12)
        return int.__pow__(int(self), _num(o)) if m is None else pow(int(self), _num(o), m)
    def __rpow__(self, o): _t("rpow"); return int.__rpow__(int(self), _num(o))
    def __xor__(self, o): _t("xor"); return int.__xor__(int(self), _num(o))
    def __rxor__(self, o): _t("xor"); return int.__rxor__(int(self), _num(o))
    def __and__(self, o): _t("and"); return int.__and__(int(self), _num(o))
    def __rand__(self, o): _t("and"); return int.__rand__(int(self), _num(o))
    def __or__(self, o): _t("or"); return int.__or__(int(self), _num(o))
    def __ror__(self, o): _t("or"); return int.__ror__(int(self), _num(o))
    def __rshift__(self, o): _t("rshift"); return int.__rshift__(int(self), _num(o))
    def __rrshift__(self, o): _t("rshift"); return int.__rrshift__(int(self), _num(o))
    def __lshift__(self, o): _t("lshift"); return int.__lshift__(int(self), _num(o))
    def __rlshift__(self, o): _t("lshift"); return int.__rlshift__(int(self), _num(o))
    def __neg__(self): _t("neg"); return -int(self)
    def __lt__(self, o): _t("cmp", o); return int(self) < _num(o)
    def __le__(self, o): _t("cmp", o); return int(self) <= _num(o)
    def __gt__(self, o): _t("cmp", o); return int(self) > _num(o)
    def __ge__(self, o): _t("cmp", o); return int(self) >= _num(o)
    def __eq__(self, o): _t("eq"); return int(self) == _num(o)
    def __ne__(self, o): _t("eq"); return int(self) != _num(o)
    def __hash__(self): _t("hash"); return int.__hash__(int(self))
    def __index__(self): _t("index"); return int(self)


def _p(v):
    return PInt(v) if type(v) is int else v


class PInt(int):
    """Propagating traced int (panel II): arithmetic results stay traced, so loops that rebind x keep counting."""
    def __add__(self, o): _t("add"); return _p(int(self) + _num(o))
    def __radd__(self, o): _t("add"); return _p(_num(o) + int(self))
    def __sub__(self, o): _t("sub"); return _p(int(self) - _num(o))
    def __rsub__(self, o): _t("sub"); return _p(_num(o) - int(self))
    def __mul__(self, o): _t("mul"); return _p(int(self) * _num(o))
    def __rmul__(self, o): _t("mul"); return _p(_num(o) * int(self))
    def __floordiv__(self, o): _t("floordiv"); return _p(int(self) // _num(o))
    def __rfloordiv__(self, o): _t("rfloordiv"); return _p(_num(o) // int(self))
    def __truediv__(self, o): _t("truediv"); return int(self) / _num(o)
    def __rtruediv__(self, o): _t("rtruediv"); return _num(o) / int(self)
    def __mod__(self, o): _t("mod"); return _p(int(self) % _num(o))
    def __rmod__(self, o): _t("mod"); return _p(_num(o) % int(self))
    def __divmod__(self, o): _t("divmod"); q, r = divmod(int(self), _num(o)); return _p(q), _p(r)
    def __pow__(self, o, m=None): _t("pow"); return _p(pow(int(self), _num(o)) if m is None else pow(int(self), _num(o), m))
    def __rpow__(self, o): _t("rpow"); return _p(_num(o) ** int(self))
    def __xor__(self, o): _t("xor"); return _p(int(self) ^ _num(o))
    def __rxor__(self, o): _t("xor"); return _p(_num(o) ^ int(self))
    def __and__(self, o): _t("and"); return _p(int(self) & _num(o))
    def __rand__(self, o): _t("and"); return _p(_num(o) & int(self))
    def __or__(self, o): _t("or"); return _p(int(self) | _num(o))
    def __ror__(self, o): _t("or"); return _p(_num(o) | int(self))
    def __rshift__(self, o): _t("rshift"); return _p(int(self) >> _num(o))
    def __rrshift__(self, o): _t("rshift"); return _p(_num(o) >> int(self))
    def __lshift__(self, o): _t("lshift"); return _p(int(self) << _num(o))
    def __rlshift__(self, o): _t("lshift"); return _p(_num(o) << int(self))
    def __neg__(self): _t("neg"); return _p(-int(self))
    def __invert__(self): _t("invert"); return _p(~int(self))
    def __lt__(self, o): _t("cmp"); return int(self) < _num(o)
    def __le__(self, o): _t("cmp"); return int(self) <= _num(o)
    def __gt__(self, o): _t("cmp"); return int(self) > _num(o)
    def __ge__(self, o): _t("cmp"); return int(self) >= _num(o)
    def __eq__(self, o): _t("eq"); return int(self) == _num(o)
    def __ne__(self, o): _t("eq"); return int(self) != _num(o)
    def __hash__(self): _t("hash"); return int.__hash__(int(self))
    def __index__(self): _t("index"); return int(self)


class TracedChar(str):
    def __hash__(self): C["chash"] += 1; return str.__hash__(str(self))
    def __eq__(self, o): C["ceq"] += 1; return str.__eq__(str(self), o)
    def __ne__(self, o): C["ceq"] += 1; return str.__ne__(str(self), o)
    def __lt__(self, o): C["ccmp"] += 1; return str.__lt__(str(self), str(o))
    def __gt__(self, o): C["ccmp"] += 1; return str.__gt__(str(self), str(o))
    def __le__(self, o): C["ccmp"] += 1; return str.__le__(str(self), str(o))
    def __ge__(self, o): C["ccmp"] += 1; return str.__ge__(str(self), str(o))


class TracedStr(str):
    def __iter__(self):
        C["str_iter"] += 1
        for ch in str.__str__(self):
            yield TracedChar(ch)

    def __getitem__(self, k):
        r = str.__getitem__(str(self), k)
        C["str_getitem"] += 1
        return TracedChar(r) if isinstance(k, int) else TracedStr(r)

    def __hash__(self): return str.__hash__(str(self))
    def __eq__(self, o): C["seq_eq"] += 1; return str.__eq__(str(self), o)
    def __ne__(self, o): C["seq_eq"] += 1; return str.__ne__(str(self), o)


def _wrap(kind, v):
    if kind == "int":
        return TracedInt(v)
    if kind == "ints":
        return [TracedInt(x) for x in v]
    if kind == "str":
        return TracedStr(v)
    if kind == "roads":
        return [[a, b, TracedInt(w)] for a, b, w in v]
    if kind == "pint":
        return PInt(v)
    if kind == "pints":
        return [PInt(x) for x in v]
    if kind == "pts":
        return [[TracedInt(a), TracedInt(b)] for a, b in v]
    return v


def _patch():
    _comb = itertools.combinations
    _perm = itertools.permutations
    _prod = itertools.product

    def combinations(*a, **k):
        C["p:itertools.combinations"] += 1
        return _comb(*a, **k)

    def permutations(*a, **k):
        C["p:itertools.permutations"] += 1
        return _perm(*a, **k)

    def product(*a, **k):
        C["p:itertools.product"] += 1
        return _prod(*a, **k)

    itertools.combinations = combinations
    itertools.permutations = permutations
    itertools.product = product
    _Counter, _dd, _dq = collections.Counter, collections.defaultdict, collections.deque

    class Counter(_Counter):
        def __init__(self, *a, **k):
            C["p:Counter"] += 1
            super().__init__(*a, **k)

    class defaultdict(_dd):
        def __init__(self, *a, **k):
            C["p:defaultdict"] += 1
            super().__init__(*a, **k)

    class deque(_dq):
        def __init__(self, *a, **k):
            C["p:deque"] += 1
            super().__init__(*a, **k)

    collections.Counter = Counter
    collections.defaultdict = defaultdict
    collections.deque = deque
    import heapq  # panel II: heapq's pure-Python helpers emit no c_call event, so they are counted here
    _merge, _nsm, _nlg = heapq.merge, heapq.nsmallest, heapq.nlargest

    def merge(*a, **k):
        C["p:heapq.merge"] += 1
        return _merge(*a, **k)

    def nsmallest(*a, **k):
        C["p:heapq.nsmallest"] += 1
        return _nsm(*a, **k)

    def nlargest(*a, **k):
        C["p:heapq.nlargest"] += 1
        return _nlg(*a, **k)

    heapq.merge, heapq.nsmallest, heapq.nlargest = merge, nsmallest, nlargest


STATE = {"depth": 0, "max_depth": 0, "user_calls": 0, "lines": 0}
LC = collections.Counter()


def _local(frame, event, arg):
    if event == "line":
        STATE["lines"] += 1
        LC[frame.f_lineno] += 1
    elif event == "return":
        STATE["depth"] -= 1
    return _local


def _global(frame, event, arg):
    if event == "call" and frame.f_code.co_filename == "<user>":
        STATE["user_calls"] += 1
        STATE["depth"] += 1
        STATE["max_depth"] = max(STATE["max_depth"], STATE["depth"])
        return _local
    return None


def _prof(frame, event, arg):
    if event == "c_call" and frame.f_code.co_filename == "<user>":
        nm = getattr(arg, "__qualname__", None) or getattr(arg, "__name__", "?")
        C["c:" + nm] += 1
        if nm in SEQ_NAMES and len(SEQ) < 50000:
            SEQ.append(nm)


class _Timeout(Exception):
    pass


def _alarm(signum, frame):
    raise _Timeout()


def main():
    payload = json.loads(sys.stdin.read())
    sys.setrecursionlimit(100000)
    _patch()
    signal.signal(signal.SIGALRM, _alarm)
    ns = {"__name__": "__user__"}
    out = {}
    try:
        signal.setitimer(signal.ITIMER_REAL, 10.0)
        exec(compile(payload["code"], "<user>", "exec"), ns)
        signal.setitimer(signal.ITIMER_REAL, 0)
        fn = ns["solve"]
    except BaseException as e:  # noqa: BLE001
        signal.setitimer(signal.ITIMER_REAL, 0)
        print(json.dumps({"load_error": f"{type(e).__name__}: {str(e)[:200]}"}))
        return
    for pr in payload["probes"]:
        C.clear()
        TRAJ.clear()
        SEQ.clear()
        STATE.update(depth=0, max_depth=0, user_calls=0, lines=0)
        LC.clear()
        args = [_wrap(k, v) for k, v in zip(pr["wrap"], pr["args"])]
        TRACE_SCALAR[0] = any(k == "int" for k in pr["wrap"])
        rec = {"error": None}
        t0 = time.perf_counter()
        try:
            signal.setitimer(signal.ITIMER_REAL, float(payload.get("limit", 8.0)))
            sys.setprofile(_prof)
            sys.settrace(_global)
            res = fn(*args)
            sys.settrace(None)
            sys.setprofile(None)
            signal.setitimer(signal.ITIMER_REAL, 0)
            exp = pr.get("expected")
            if exp is not None:
                try:
                    if pr.get("checker") == "subsets":
                        rec["correct"] = sorted(sorted(x) for x in res) == sorted(sorted(x) for x in exp)
                    else:
                        rec["correct"] = res == exp
                except BaseException:  # noqa: BLE001
                    rec["correct"] = False
        except _Timeout:
            sys.settrace(None)
            sys.setprofile(None)
            rec["error"] = "timeout"
        except BaseException as e:  # noqa: BLE001
            sys.settrace(None)
            sys.setprofile(None)
            signal.setitimer(signal.ITIMER_REAL, 0)
            rec["error"] = f"{type(e).__name__}: {str(e)[:120]}"
        rec["t"] = round(time.perf_counter() - t0, 5)
        rec["ops"] = {k: v for k, v in C.items() if not k.startswith(("c:", "p:"))}
        rec["ccalls"] = {k[2:]: v for k, v in C.items() if k.startswith("c:")}
        rec["patched"] = {k[2:]: v for k, v in C.items() if k.startswith("p:")}
        rec["user_calls"] = STATE["user_calls"]
        rec["max_depth"] = STATE["max_depth"]
        rec["lines"] = STATE["lines"]
        rec["line_counts"] = {str(k): v for k, v in LC.items()}
        rec["traj"] = TRAJ[:3000]
        rec["seq"] = SEQ[:3000]
        out[pr["name"]] = rec
    print(json.dumps(out))


main()
