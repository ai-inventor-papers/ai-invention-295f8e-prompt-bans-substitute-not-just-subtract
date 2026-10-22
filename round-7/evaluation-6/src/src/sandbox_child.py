"""Sandboxed runner for one program: reads {code, cases, limits_s} as JSON on stdin and writes results on stdout.

Runs under RLIMIT_AS 2 GB and RLIMIT_CPU 10 s (set by the parent through preexec_fn and again here), with the
socket module disabled before the program is executed (best-effort network block: unprivileged network namespaces
are not available on this host). Each case has its own wall-clock limit enforced with an interval timer.
"""

import json
import resource
import signal
import socket
import sys
import time

resource.setrlimit(resource.RLIMIT_AS, (2 * 1024 ** 3, 2 * 1024 ** 3))
resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
sys.setrecursionlimit(20000)


def _blocked(*a, **k):
    raise OSError("network disabled in the sandbox")


socket.socket = _blocked  # type: ignore[assignment]
socket.create_connection = _blocked  # type: ignore[assignment]


class CaseTimeout(Exception):
    pass


def _alarm(signum, frame):
    raise CaseTimeout()


def main() -> None:
    job = json.loads(sys.stdin.read())
    ns: dict = {"__name__": "candidate"}
    out = {"compiled": True, "results": []}
    try:
        exec(compile(job["code"], "<candidate>", "exec"), ns)
        solve = ns["solve"]
    except BaseException as e:  # noqa: BLE001 - any failure of the candidate is a result, not a crash
        out["compiled"] = False
        out["error"] = f"{type(e).__name__}: {str(e)[:200]}"
        print(json.dumps(out))
        return
    signal.signal(signal.SIGALRM, _alarm)
    for case, lim in zip(job["cases"], job["limits_s"]):
        t0 = time.perf_counter()
        try:
            signal.setitimer(signal.ITIMER_REAL, lim)
            got = solve(case["n"], [tuple(e) for e in case["edges"]], case["s"], case["t"])
            signal.setitimer(signal.ITIMER_REAL, 0)
            out["results"].append({"ok": True, "got": got, "secs": time.perf_counter() - t0})
        except CaseTimeout:
            out["results"].append({"ok": False, "error": "timeout", "secs": time.perf_counter() - t0})
        except BaseException as e:  # noqa: BLE001
            signal.setitimer(signal.ITIMER_REAL, 0)
            out["results"].append({"ok": False, "error": f"{type(e).__name__}: {str(e)[:120]}",
                                   "secs": time.perf_counter() - t0})
    print(json.dumps(out))


if __name__ == "__main__":
    main()
