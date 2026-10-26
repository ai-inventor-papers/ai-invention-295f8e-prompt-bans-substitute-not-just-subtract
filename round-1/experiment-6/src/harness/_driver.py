"""Subprocess driver: exec a candidate program and call solve() on hidden cases, one worker thread per case.

argv: prog_path cases_path limits_path start_index out_path task
Writes one JSON line per case to out_path; on a per-case timeout writes a timeout record and exits immediately.
Run with `python -I` in a temporary working directory.
"""

import io
import json
import os
import resource
import sys
import threading
import time


def to_jsonable(x, depth=0):
    if depth > 4:
        return repr(x)[:200]
    if x is None or isinstance(x, (bool, int, str)):
        return x
    if isinstance(x, float):
        if x != x:
            return "NaN"
        if x in (float("inf"), float("-inf")):
            return {"__float__": "inf" if x > 0 else "-inf"}
        return x
    if isinstance(x, (list, tuple)):
        if len(x) > 5000:
            return {"__too_long__": len(x)}
        return {"__seq__": "tuple" if isinstance(x, tuple) else "list",
                "items": [to_jsonable(v, depth + 1) for v in x]}
    try:
        import numpy as np  # noqa: F401
        if hasattr(x, "item") and hasattr(x, "dtype"):
            return to_jsonable(x.item(), depth + 1)
    except Exception:  # noqa: BLE001
        pass
    return {"__repr__": repr(x)[:200], "__type__": type(x).__name__}


def main():
    prog_path, cases_path, limits_path, start, out_path, task = sys.argv[1:7]
    start = int(start)
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024 ** 3, 2 * 1024 ** 3))
    sys.setrecursionlimit(100000)
    threading.stack_size(256 * 1024 * 1024)
    cases = json.loads(open(cases_path).read())
    limits = json.loads(open(limits_path).read())
    out = open(out_path, "a")
    real_stdout = sys.stdout
    sys.stdout = io.StringIO()
    sys.stdin = io.StringIO("")
    ns = {"__name__": "solution", "__builtins__": __builtins__}
    try:
        src = open(prog_path).read()
        code = compile(src, "solution.py", "exec")
        holder = {}

        def _load():
            try:
                exec(code, ns)
            except BaseException as e:  # noqa: BLE001
                holder["err"] = f"{type(e).__name__}: {str(e)[:200]}"

        th = threading.Thread(target=_load, daemon=True)
        th.start()
        th.join(10.0)
        if th.is_alive():
            out.write(json.dumps({"i": -1, "status": "load_timeout"}) + "\n")
            out.flush()
            os._exit(0)
        if "err" in holder:
            out.write(json.dumps({"i": -1, "status": "load_error", "err": holder["err"]}) + "\n")
            out.flush()
            os._exit(0)
        solve = ns.get("solve")
        if not callable(solve):
            out.write(json.dumps({"i": -1, "status": "no_solve"}) + "\n")
            out.flush()
            os._exit(0)
    except SyntaxError as e:
        out.write(json.dumps({"i": -1, "status": "syntax_error", "err": str(e)[:200]}) + "\n")
        out.flush()
        os._exit(0)
    for i in range(start, len(cases)):
        c = cases[i]
        if task == "T1":
            args = ([str(r) for r in c["grid"]], tuple(c["start"]), tuple(c["goal"]))
        else:
            args = (int(c["n"]), [tuple(e) for e in c["edges"]], int(c["s"]), int(c["t"]))
        res = {}

        def _run():
            t0 = time.perf_counter()
            try:
                res["out"] = solve(*args)
                res["status"] = "ok"
            except RecursionError as e:
                res["status"] = "exception"
                res["err"] = f"RecursionError: {str(e)[:100]}"
            except MemoryError:
                res["status"] = "exception"
                res["err"] = "MemoryError"
            except BaseException as e:  # noqa: BLE001
                res["status"] = "exception"
                res["err"] = f"{type(e).__name__}: {str(e)[:150]}"
            res["t"] = time.perf_counter() - t0

        th = threading.Thread(target=_run, daemon=True)
        t0 = time.perf_counter()
        th.start()
        th.join(limits[i])
        if th.is_alive():
            out.write(json.dumps({"i": i, "status": "timeout", "t": time.perf_counter() - t0}) + "\n")
            out.flush()
            os._exit(0)
        rec = {"i": i, "status": res.get("status", "exception"), "t": res.get("t", 0.0)}
        if rec["status"] == "ok":
            rec["out"] = to_jsonable(res.get("out"))
        else:
            rec["err"] = res.get("err", "")
        out.write(json.dumps(rec) + "\n")
        out.flush()
    sys.stdout = real_stdout
    out.close()
    os._exit(0)


if __name__ == "__main__":
    main()
