"""Sandbox child: run solve(**kwargs) on each case with a per-case wall-clock limit (stdlib only).

Reads {"code", "cases": [{"id", "kwargs"}], "limits": [seconds], "fn"} as JSON on stdin; writes one JSON object
{"results": [{"id", "ok", "output" | "error", "seconds"}]} on stdout. Launched by src/adjudicate.py with
`python -I`, RLIMIT_AS and RLIMIT_CPU caps and an empty environment."""
import copy
import json
import signal
import sys
import time


class _Timeout(Exception):
    pass


def _alarm(signum, frame):
    raise _Timeout()


def _plain(x):
    if isinstance(x, tuple):
        return [_plain(v) for v in x]
    if isinstance(x, list):
        return [_plain(v) for v in x]
    if isinstance(x, (int, float, str, bool)) or x is None:
        return x
    try:
        return [_plain(v) for v in x]
    except TypeError:
        return repr(x)


def main():
    job = json.loads(sys.stdin.read())
    ns = {"__name__": "__candidate__"}
    out = []
    try:
        exec(compile(job["code"], "<candidate>", "exec"), ns)
        fn = ns[job.get("fn", "solve")]
    except Exception as e:  # noqa: BLE001 - a broken candidate is a result, not a crash
        print(json.dumps({"compile_error": f"{type(e).__name__}: {e}"[:300], "results": []}))
        return
    signal.signal(signal.SIGALRM, _alarm)
    for case, lim in zip(job["cases"], job["limits"]):
        kw = copy.deepcopy(case["kwargs"])
        t0 = time.perf_counter()
        signal.setitimer(signal.ITIMER_REAL, lim)
        try:
            res = fn(**kw)
            signal.setitimer(signal.ITIMER_REAL, 0)
            out.append({"id": case["id"], "ok": True, "output": _plain(res), "seconds": time.perf_counter() - t0})
        except _Timeout:
            out.append({"id": case["id"], "ok": False, "error": "timeout", "seconds": time.perf_counter() - t0})
        except RecursionError:
            signal.setitimer(signal.ITIMER_REAL, 0)
            out.append({"id": case["id"], "ok": False, "error": "RecursionError", "seconds": time.perf_counter() - t0})
        except Exception as e:  # noqa: BLE001
            signal.setitimer(signal.ITIMER_REAL, 0)
            out.append({"id": case["id"], "ok": False, "error": f"{type(e).__name__}: {e}"[:200],
                        "seconds": time.perf_counter() - t0})
    print(json.dumps({"results": out}))


if __name__ == "__main__":
    main()
