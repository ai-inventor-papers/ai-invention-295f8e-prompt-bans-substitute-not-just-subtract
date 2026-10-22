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


def _check(kind, got, exp, args=None):
    if kind == "peak":
        nums = args[0]
        if isinstance(got, bool) or not isinstance(got, int) or not (0 <= got < len(nums)):
            return False
        left = nums[got - 1] if got > 0 else None
        right = nums[got + 1] if got + 1 < len(nums) else None
        return (left is None or nums[got] > left) and (right is None or nums[got] > right)
    if kind == "kclosest":
        pts, k = args[0], args[1]
        if not isinstance(got, (list, tuple)) or len(got) != k:
            return False
        pool = {}
        for p in pts:
            t = (p[0], p[1])
            pool[t] = pool.get(t, 0) + 1
        for g in got:
            try:
                t = (g[0], g[1])
                if len(g) != 2:
                    return False
            except (TypeError, IndexError):
                return False
            if pool.get(t, 0) <= 0:
                return False
            pool[t] -= 1
        return max(g[0] * g[0] + g[1] * g[1] for g in got) <= exp
    if kind == "perms":
        nums = args[0]
        if not isinstance(got, (list, tuple)):
            return False
        try:
            tg = [tuple(x) for x in got]
        except TypeError:
            return False
        if len(tg) != exp or len(set(tg)) != len(tg):
            return False
        key = sorted(nums)
        return all(sorted(x) == key for x in tg)
    if kind == "inplace0":
        return isinstance(got, list) and got == exp
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
            a = copy.deepcopy(args)
            got = fn(*a)
            signal.setitimer(signal.ITIMER_REAL, 0)
            if payload["checker"] == "inplace0":
                if got is not None:
                    status, msg = "wrong", "returned a value instead of None"
                got = a[0]
            if status == "ok" and not _check(payload["checker"], got, exp, args):
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
