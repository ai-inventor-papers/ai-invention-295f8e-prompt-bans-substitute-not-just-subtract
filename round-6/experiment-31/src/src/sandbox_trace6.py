"""Child side of the runtime tracer (run as `python -I -S sandbox_trace6.py` with a JSON payload on stdin).

For every probe input it records, inside the user's code only (filename '<user>'), with sys.monitoring (PEP 669):
  ops       dynamic opcode profile: every executed instruction by name; BINARY_OP split by operator
            ('BINARY_OP:>>', 'BINARY_OP:&', 'BINARY_OP:+=', ...), so arithmetic on plain ints is visible;
  calls     every call made from user code, by callable name ('sorted', 'list.sort', 'heappush', 'set.add', 'gcd',
            'bit_count', 'Counter', user functions ...), and calls_maxlen: the largest len() of the first argument
            seen per callable (e.g. the size of the sequence handed to sorted / list.sort / heapify);
  py_calls  starts of user-defined Python code objects by name, max_depth of nested user frames, lines (LINE events);
  lst       counters of the wrapped input lists (TracedList): getitem, setitem, contains (list membership scans),
            iter, delitem.
payload = {"code": str, "probes": [{"name", "args", "wrap": [kind per arg], "expected", "checker"}], "limit": float}
wrap kinds: 'list' (TracedList, nested lists kept plain), 'none'.
"""

import json
import signal
import sys
import time

MON = sys.monitoring
TOOL = 3
OPS = {}
CALLS = {}
CALL_MAXLEN = {}
CALL_MAXINT = {}
PYC = {}
STATE = {"depth": 0, "max_depth": 0, "lines": 0}
LST = {"getitem": 0, "setitem": 0, "contains": 0, "iter": 0, "delitem": 0, "rev": 0, "desc_run_max": 0}
IDX = []
RUN = {"last": None, "cur": 0}
CODES = []
BYTES = {}
_OPNAME = None
_NBOPS = None


class TracedList(list):
    def __getitem__(self, k):
        LST["getitem"] += 1
        if isinstance(k, slice):
            if k.step is not None and k.step < 0:
                LST["rev"] += 1
        elif isinstance(k, int):
            kk = k if k >= 0 else len(self) + k
            if len(IDX) < 40:
                IDX.append(kk)
            last = RUN["last"]
            if last is not None and kk != last:
                RUN["cur"] = RUN["cur"] + 1 if kk < last else 0
                if RUN["cur"] > LST["desc_run_max"]:
                    LST["desc_run_max"] = RUN["cur"]
            RUN["last"] = kk
        r = list.__getitem__(self, k)
        return TracedList(r) if isinstance(k, slice) else r

    def __setitem__(self, k, v):
        LST["setitem"] += 1
        return list.__setitem__(self, k, v)

    def __delitem__(self, k):
        LST["delitem"] += 1
        return list.__delitem__(self, k)

    def __contains__(self, x):
        LST["contains"] += 1
        return list.__contains__(self, x)

    def __iter__(self):
        LST["iter"] += 1
        return list.__iter__(self)

    def __reversed__(self):
        LST["rev"] += 1
        return list.__reversed__(self)


def _wrap(kind, v):
    if kind == "list":
        return TracedList(v)
    return v


def _cname(c):
    try:
        q = getattr(c, "__qualname__", None) or getattr(c, "__name__", None)
        if q is None:
            q = type(c).__name__
        return str(q)
    except Exception:  # noqa: BLE001
        return "?"


def on_instr(code, off):
    b = BYTES.get(code)
    if b is None:
        b = code.co_code
        BYTES[code] = b
    op = b[off]
    name = _OPNAME[op]
    if name == "BINARY_OP":
        name = "BINARY_OP:" + _NBOPS[b[off + 1]][1]
    OPS[name] = OPS.get(name, 0) + 1


def on_call(code, off, callable_, arg0):
    n = _cname(callable_)
    CALLS[n] = CALLS.get(n, 0) + 1
    if arg0 is not MON.MISSING:
        if isinstance(arg0, int) and not isinstance(arg0, bool):
            if arg0 > CALL_MAXINT.get(n, -(1 << 62)):
                CALL_MAXINT[n] = arg0 if abs(arg0) < (1 << 62) else (1 << 62)
        try:
            if isinstance(arg0, (list, tuple, str, dict, set, frozenset, bytes, range)):
                L = len(arg0)
                if L > CALL_MAXLEN.get(n, -1):
                    CALL_MAXLEN[n] = L
        except Exception:  # noqa: BLE001
            pass


def on_start(code, off):
    PYC[code.co_name] = PYC.get(code.co_name, 0) + 1
    if code.co_name not in ("<genexpr>", "<listcomp>", "<setcomp>", "<dictcomp>"):
        STATE["depth"] += 1
        if STATE["depth"] > STATE["max_depth"]:
            STATE["max_depth"] = STATE["depth"]


def on_return(code, off, retval):
    if code.co_name not in ("<genexpr>", "<listcomp>", "<setcomp>", "<dictcomp>"):
        STATE["depth"] -= 1


def on_line(code, line):
    STATE["lines"] += 1


def _allcodes(co):
    out = [co]
    for c in co.co_consts:
        if hasattr(c, "co_code"):
            out += _allcodes(c)
    return out


class _Timeout(Exception):
    pass


def _alarm(signum, frame):
    raise _Timeout()


def _set(on):
    ev = (MON.events.INSTRUCTION | MON.events.CALL | MON.events.PY_START | MON.events.PY_RETURN |
          MON.events.LINE) if on else 0
    for co in CODES:
        if co.co_name != "<module>":
            MON.set_local_events(TOOL, co, ev)


def _canon(checker, got, exp, args):
    try:
        if checker == "inplace":
            return list(args[0]) == exp
        if checker == "groups":
            return sorted(sorted(x) for x in got) == exp
        if checker == "multiset":
            return sorted(got) == sorted(exp)
        return got == exp
    except BaseException:  # noqa: BLE001
        return False


_REAL_OUT = sys.stdout
MARK = '@@AII@@'


def _emit(obj):
    _REAL_OUT.write(MARK + json.dumps(obj) + '\n')
    _REAL_OUT.flush()


def main():
    import os
    sys.stdout = open(os.devnull, 'w')
    global _OPNAME, _NBOPS
    import dis
    _OPNAME = dis.opname
    _NBOPS = dis._nb_ops
    payload = json.loads(sys.stdin.read())
    sys.setrecursionlimit(20000)
    signal.signal(signal.SIGALRM, _alarm)
    ns = {"__name__": "__user__"}
    try:
        signal.setitimer(signal.ITIMER_REAL, 10.0)
        mod = compile(payload["code"], "<user>", "exec")
        exec(mod, ns)
        signal.setitimer(signal.ITIMER_REAL, 0)
        fn = ns["solve"]
    except BaseException as e:  # noqa: BLE001
        signal.setitimer(signal.ITIMER_REAL, 0)
        _emit(({"load_error": f"{type(e).__name__}: {str(e)[:200]}"}))
        return
    CODES.extend(_allcodes(mod))
    MON.use_tool_id(TOOL, "aii_tracer")
    MON.register_callback(TOOL, MON.events.INSTRUCTION, on_instr)
    MON.register_callback(TOOL, MON.events.CALL, on_call)
    MON.register_callback(TOOL, MON.events.PY_START, on_start)
    MON.register_callback(TOOL, MON.events.PY_RETURN, on_return)
    MON.register_callback(TOOL, MON.events.LINE, on_line)
    out = {}
    for pr in payload["probes"]:
        for d in (OPS, CALLS, CALL_MAXLEN, CALL_MAXINT, PYC):
            d.clear()
        STATE.update(depth=0, max_depth=0, lines=0)
        for k in LST:
            LST[k] = 0
        IDX.clear()
        RUN.update(last=None, cur=0)
        args = [_wrap(k, v) for k, v in zip(pr["wrap"], pr["args"])]
        rec = {"error": None}
        t0 = time.perf_counter()
        try:
            signal.setitimer(signal.ITIMER_REAL, float(payload.get("limit", 8.0)))
            _set(True)
            res = fn(*args)
            _set(False)
            signal.setitimer(signal.ITIMER_REAL, 0)
            if pr.get("expected") is not None:
                rec["correct"] = _canon(pr.get("checker", "exact"), res, pr["expected"], args)
        except _Timeout:
            _set(False)
            rec["error"] = "timeout"
        except BaseException as e:  # noqa: BLE001
            _set(False)
            signal.setitimer(signal.ITIMER_REAL, 0)
            rec["error"] = f"{type(e).__name__}: {str(e)[:120]}"
        rec["t"] = round(time.perf_counter() - t0, 5)
        rec["ops"] = dict(OPS)
        rec["calls"] = dict(CALLS)
        rec["calls_maxlen"] = dict(CALL_MAXLEN)
        rec["calls_maxint"] = dict(CALL_MAXINT)
        rec["py_calls"] = dict(PYC)
        rec["max_depth"] = STATE["max_depth"]
        rec["lines"] = STATE["lines"]
        rec["lst"] = dict(LST)
        rec["idx"] = list(IDX)
        out[pr["name"]] = rec
    _emit((out))


main()
