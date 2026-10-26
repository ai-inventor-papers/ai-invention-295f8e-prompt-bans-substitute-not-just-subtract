"""Child side of the test sandbox (run as `python -I -S sandbox_tests.py` with a JSON payload on stdin).

payload = {"code": str, "checker": "exact"|"subsets"|"bool", "stop_on_fail": bool,
           "cases": [{"args_json": str, "expected_json": str, "limit": float}]}
Prints one JSON line per case: {"i", "status" (ok|wrong|error|timeout), "t", "msg"}; i = -1 reports a load error.
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


def _check(kind, got, exp):
    if kind == "bool":
        return isinstance(got, bool) and got == exp
    if kind == "subsets":
        if not isinstance(got, (list, tuple)):
            return False
        try:
            items = [frozenset(x) for x in got]
            if any(len(frozenset(x)) != len(list(x)) for x in got):
                return False
        except TypeError:
            return False
        if len(items) != len(exp):
            return False
        return sorted(map(sorted, items)) == sorted(map(sorted, (frozenset(e) for e in exp)))
    if isinstance(exp, bool) or isinstance(got, bool):
        return type(got) is type(exp) and got == exp
    if isinstance(exp, int):
        return isinstance(got, int) and got == exp
    return got == exp


def main():
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
        print(json.dumps({"i": -1, "status": "load_error", "msg": f"{type(e).__name__}: {str(e)[:200]}"}))
        sys.stdout.flush()
        return
    for i, c in enumerate(payload["cases"]):
        args = json.loads(c["args_json"])
        exp = json.loads(c["expected_json"])
        t0 = time.perf_counter()
        status, msg = "ok", None
        try:
            signal.setitimer(signal.ITIMER_REAL, float(c["limit"]))
            got = fn(*copy.deepcopy(args))
            signal.setitimer(signal.ITIMER_REAL, 0)
            if not _check(payload["checker"], got, exp):
                status = "wrong"
                msg = repr(got)[:120]
        except _Timeout:
            status = "timeout"
        except RecursionError:
            signal.setitimer(signal.ITIMER_REAL, 0)
            status, msg = "error", "RecursionError"
        except BaseException as e:  # noqa: BLE001
            signal.setitimer(signal.ITIMER_REAL, 0)
            status, msg = "error", f"{type(e).__name__}: {str(e)[:120]}"
        dt = time.perf_counter() - t0
        print(json.dumps({"i": i, "status": status, "t": round(dt, 6), "msg": msg}))
        sys.stdout.flush()
        if status != "ok" and payload.get("stop_on_fail"):
            break


main()
