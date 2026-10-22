"""Child side of the test sandbox (run as `python -I -S sandbox_tests6.py` with a JSON payload on stdin).

payload = {"code": str, "checker": "exact"|"bool"|"groups"|"multiset"|"inplace", "stop_on_fail": bool,
           "cases": [{"args_json": str, "expected_json": str, "limit": float}]}
Prints one JSON line per case: {"i", "status" (ok|wrong|error|timeout), "t", "msg"}; i = -1 reports a load error.
Checkers: exact (type-strict for int/bool), bool (a real bool), groups (order-free list of lists of words),
multiset (order-free list of ints), inplace (the first argument after the call must equal expected; the return value
is ignored, as the spec says only the contents of nums are checked).
"""

import copy
import json
import signal
import sys
import time


class _Timeout(Exception):
    pass


def _alarm(signum, frame):
    raise _Timeout()


def _canon_groups(g):
    return sorted(sorted(x) for x in g)


def _check(kind, got, exp, args):
    if kind == "inplace":
        return isinstance(args[0], list) and args[0] == exp
    if kind == "bool":
        return isinstance(got, bool) and got == exp
    if kind == "groups":
        if not isinstance(got, (list, tuple)):
            return False
        try:
            if any(not isinstance(x, (list, tuple)) or any(not isinstance(w, str) for w in x) for x in got):
                return False
            return _canon_groups(got) == exp
        except TypeError:
            return False
    if kind == "multiset":
        if not isinstance(got, (list, tuple)):
            return False
        if any(isinstance(x, bool) or not isinstance(x, int) for x in got):
            return False
        return sorted(got) == sorted(exp)
    if isinstance(exp, bool) or isinstance(got, bool):
        return type(got) is type(exp) and got == exp
    if isinstance(exp, int):
        return isinstance(got, int) and not isinstance(got, bool) and got == exp
    if isinstance(exp, list):
        return isinstance(got, list) and len(got) == len(exp) and all(
            isinstance(a, int) and not isinstance(a, bool) and a == b for a, b in zip(got, exp))
    return got == exp


_REAL_OUT = sys.stdout
MARK = '@@AII@@'


def _emit(obj):
    _REAL_OUT.write(MARK + json.dumps(obj) + '\n')
    _REAL_OUT.flush()


def main():
    import os
    sys.stdout = open(os.devnull, 'w')
    payload = json.loads(sys.stdin.read())
    sys.setrecursionlimit(100000)
    ns = {"__name__": "__user__"}
    signal.signal(signal.SIGALRM, _alarm)
    try:
        signal.setitimer(signal.ITIMER_REAL, 10.0)
        exec(compile(payload["code"], "<user>", "exec"), ns)
        signal.setitimer(signal.ITIMER_REAL, 0)
        fn = ns["solve"]
    except BaseException as e:  # noqa: BLE001
        signal.setitimer(signal.ITIMER_REAL, 0)
        _emit(({"i": -1, "status": "load_error", "msg": f"{type(e).__name__}: {str(e)[:200]}"}))
        return
    for i, c in enumerate(payload["cases"]):
        args = json.loads(c["args_json"])
        exp = json.loads(c["expected_json"])
        status, msg = "ok", None
        call_args = copy.deepcopy(args)
        t0 = time.perf_counter()
        try:
            signal.setitimer(signal.ITIMER_REAL, float(c["limit"]))
            got = fn(*call_args)
            signal.setitimer(signal.ITIMER_REAL, 0)
            dt = time.perf_counter() - t0
            if not _check(payload["checker"], got, exp, call_args):
                status = "wrong"
                msg = repr(got)[:120]
        except _Timeout:
            dt = time.perf_counter() - t0
            status = "timeout"
        except RecursionError:
            signal.setitimer(signal.ITIMER_REAL, 0)
            dt = time.perf_counter() - t0
            status, msg = "error", "RecursionError"
        except BaseException as e:  # noqa: BLE001
            signal.setitimer(signal.ITIMER_REAL, 0)
            dt = time.perf_counter() - t0
            status, msg = "error", f"{type(e).__name__}: {str(e)[:120]}"
        _emit(({"i": i, "status": status, "t": round(dt, 6), "msg": msg}))
        if status != "ok" and payload.get("stop_on_fail"):
            break


main()
