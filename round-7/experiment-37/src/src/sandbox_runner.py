"""Child side of the evaluator sandbox (stdlib only; run as `python3.12 -I -S sandbox_runner.py`, job JSON on stdin).

Limits are applied here before the candidate is executed: RLIMIT_AS (address space), RLIMIT_NOFILE, RLIMIT_CPU, and a
per-case wall alarm. Network and process modules are stubbed in sys.modules before exec. Stages run in order and the
run stops at the first failing case. One JSON line per case is flushed to stdout so a killed child still reports
how far it got.
"""

import io
import json
import resource
import signal
import sys
import time

_OUT = sys.stdout


class _Timeout(BaseException):
    pass


def _alarm(signum, frame):
    raise _Timeout()


def emit(obj):
    _OUT.write(json.dumps(obj) + "\n")
    _OUT.flush()


def check(task, expected, output):
    # all three tasks have a unique integer answer
    return isinstance(output, int) and not isinstance(output, bool) and output == expected


def convert(task, kwargs):
    if task == "T2":
        kwargs["edges"] = [tuple(e) for e in kwargs["edges"]]
    return kwargs


def main():
    job = json.loads(sys.stdin.read())
    mem = int(job.get("mem_bytes", 2 * 1024 ** 3))
    resource.setrlimit(resource.RLIMIT_AS, (mem, mem))
    try:
        resource.setrlimit(resource.RLIMIT_NOFILE, (32, 32))
    except (ValueError, OSError):
        pass
    cpu = int(job.get("cpu_s", 60)) + 1
    resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu + 1))
    for name in ("socket", "_socket", "ssl", "subprocess", "_posixsubprocess", "ctypes", "_ctypes",
                 "multiprocessing", "urllib", "http", "requests", "shutil", "pathlib"):
        sys.modules[name] = None
    signal.signal(signal.SIGALRM, _alarm)
    task = job["task"]
    g = {"__name__": "__candidate__"}
    sink = io.StringIO()
    sys.stdout = sink
    try:
        signal.setitimer(signal.ITIMER_REAL, float(job.get("load_limit", 5.0)))
        exec(compile(job["code"], "<candidate>", "exec"), g)
        signal.setitimer(signal.ITIMER_REAL, 0)
        fn = g.get("solve")
        if not callable(fn):
            raise NameError("no callable solve")
    except _Timeout:
        sys.stdout = _OUT
        emit({"load_error": "load_timeout"})
        return
    except BaseException as e:  # noqa: BLE001 - any failure while loading the candidate is a load error
        signal.setitimer(signal.ITIMER_REAL, 0)
        sys.stdout = _OUT
        emit({"load_error": f"{type(e).__name__}: {str(e)[:200]}"})
        return
    sys.stdout = _OUT
    emit({"loaded": True})
    for s, cases in enumerate(job["stages"]):
        for i, c in enumerate(cases):
            kwargs = convert(task, json.loads(c["kw"]))
            expected = json.loads(c["exp"])
            status = "ok"
            t = None
            sys.stdout = sink
            try:
                signal.setitimer(signal.ITIMER_REAL, float(c["lim"]))
                t0 = time.perf_counter()
                out = fn(**kwargs)
                t = time.perf_counter() - t0
                signal.setitimer(signal.ITIMER_REAL, 0)
                if not check(task, expected, out):
                    status = "wrong"
            except _Timeout:
                status = "timeout"
            except MemoryError:
                signal.setitimer(signal.ITIMER_REAL, 0)
                status = "memory"
            except RecursionError:
                signal.setitimer(signal.ITIMER_REAL, 0)
                status = "recursion"
            except BaseException as e:  # noqa: BLE001 - a crashing candidate fails the case
                signal.setitimer(signal.ITIMER_REAL, 0)
                status = "error:" + type(e).__name__
            sys.stdout = _OUT
            if sink.tell() > 1_000_000:
                sink.seek(0)
                sink.truncate()
            emit({"s": s, "i": i, "st": status, "t": t})
            if status != "ok":
                emit({"stop": s})
                return
    emit({"done": True})


if __name__ == "__main__":
    main()
