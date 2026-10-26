"""Sandbox runner (stdlib only).  Executed as: python3.12 -I -S runner.py < payload.json

payload: {"code", "task", "checkers_path", "cases": [{"kwargs_json", "expected_json", "limit"}]}
Prints one JSON line per case: {"i", "status": ok|wrong|error|timeout, "t", "msg"} and stops at the first timeout.
The candidate may not import os, subprocess, socket, shutil, ctypes or multiprocessing.
"""

import builtins
import importlib.util
import io
import json
import os
import sys
import threading
import time

FORBIDDEN = {"os", "subprocess", "socket", "shutil", "ctypes", "multiprocessing", "pty", "signal", "resource"}
CAND = "__candidate__"


def main():
    payload = json.loads(sys.stdin.read())
    sys.stdin = io.StringIO("")
    out = sys.stdout
    spec = importlib.util.spec_from_file_location("checkers", payload["checkers_path"])
    chk_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(chk_mod)
    check = chk_mod.CHECK[payload["task"]]
    # pre-import common stdlib modules so their own internal imports are unaffected by the hook
    for m in ("heapq", "bisect", "collections", "functools", "itertools", "math", "random", "typing", "re",
              "string", "operator", "copy", "array", "queue", "dataclasses", "statistics", "sys", "time"):
        try:
            __import__(m)
        except ImportError:
            pass
    real_import = builtins.__import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        if globals is not None and globals.get("__name__") == CAND and name.split(".")[0] in FORBIDDEN:
            raise ImportError(f"import of {name} is not allowed")
        return real_import(name, globals, locals, fromlist, level)

    builtins.__import__ = guarded_import
    sys.setrecursionlimit(10**6)
    threading.stack_size(512 * 1024 * 1024)
    ns = {"__name__": CAND, "__builtins__": builtins}
    try:
        code = compile(payload["code"], "<candidate>", "exec")
        sys.stdout = io.StringIO()
        exec(code, ns)
        sys.stdout = out
    except BaseException as e:  # noqa: BLE001 - any failure of candidate module code is a result
        sys.stdout = out
        out.write(json.dumps({"i": -1, "status": "error", "t": 0.0, "msg": f"load: {type(e).__name__}: {e}"[:300]}) + "\n")
        out.flush()
        return
    solve = ns.get("solve")
    if not callable(solve):
        out.write(json.dumps({"i": -1, "status": "error", "t": 0.0, "msg": "no solve()"}) + "\n")
        out.flush()
        return
    for i, c in enumerate(payload["cases"]):
        kwargs = json.loads(c["kwargs_json"])
        box = {}

        def target():
            try:
                t0 = time.perf_counter()
                r = solve(**kwargs)
                box["t"] = time.perf_counter() - t0
                box["r"] = r
            except BaseException as e:  # noqa: BLE001
                box["e"] = f"{type(e).__name__}: {e}"[:300]

        sys.stdout = io.StringIO()
        th = threading.Thread(target=target, daemon=True)
        t_start = time.perf_counter()
        th.start()
        th.join(c["limit"])
        sys.stdout = out
        if th.is_alive():
            out.write(json.dumps({"i": i, "status": "timeout", "t": time.perf_counter() - t_start, "msg": ""}) + "\n")
            out.flush()
            os._exit(0)
        if "e" in box:
            out.write(json.dumps({"i": i, "status": "error", "t": time.perf_counter() - t_start, "msg": box["e"]}) + "\n")
        else:
            try:
                ok = bool(check(json.loads(c["kwargs_json"]), json.loads(c["expected_json"]), box["r"]))
            except BaseException as e:  # noqa: BLE001
                ok = False
                box["e"] = f"checker: {type(e).__name__}: {e}"[:200]
            st = "ok" if ok and box["t"] <= c["limit"] else ("slow" if ok else "wrong")
            out.write(json.dumps({"i": i, "status": st, "t": box["t"], "msg": box.get("e", "")}) + "\n")
        out.flush()


if __name__ == "__main__":
    main()
