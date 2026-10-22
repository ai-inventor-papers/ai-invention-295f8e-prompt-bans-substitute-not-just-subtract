#!/usr/bin/env python3
"""Hidden-test sandbox: runs ONE candidate program against the hidden cases in a fresh process.

Invoked as `python -I -S sandbox_tests.py` with a JSON job on stdin:
  {"task": "t1"|"t2", "code": str, "tasks_dir": str, "limits": {case_id: seconds} | null, "max_case_s": float}
Writes one JSON line on stdout. Cases run in increasing size order and the run stops at the first failing case.
Stdlib only. RLIMIT_AS 2 GB; recursion limit 20000; solve runs inside a thread with a 256 MB stack so recursive
DFS/IDDFS are not penalised; the candidate is exec'd in a module named 'cand' (so __main__ blocks never run)
with source filename '<candidate>'.
"""

import ast
import io
import json
import os
import resource
import sys
import threading
import time
import types

FORBIDDEN = {"os", "subprocess", "socket", "shutil", "ctypes", "multiprocessing"}


def screen(code):
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError) as e:
        return "syntax_error", str(e)[:200]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name.split(".")[0] in FORBIDDEN:
                    return "forbidden_import", a.name
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.split(".")[0] in FORBIDDEN:
                return "forbidden_import", node.module
    return None, None


def make_args(task, case):
    if task == "t1":
        return (list(case["grid"]), tuple(case["start"]), tuple(case["goal"]))
    return (case["n"], [tuple(e) for e in case["edges"]], case["s"], case["t"])


def main():
    job = json.loads(sys.stdin.read())
    real_out = sys.stdout
    out = {"passed": False, "n_cases": 0, "n_passed": 0, "error": None, "fail_case": None, "fail_msg": None,
           "case_times": {}, "wall_s": 0.0}

    def emit():
        real_out.write(json.dumps(out) + "\n")
        real_out.flush()

    sys.path.insert(0, job["tasks_dir"])
    from tests_gen import check_t1, check_t2  # noqa: E402  (stdlib-only module)

    task = job["task"]
    with open(os.path.join(job["tasks_dir"], "t1_grid" if task == "t1" else "t2_wsp", "tests.json")) as fh:
        cases = json.load(fh)
    cases.sort(key=lambda c: (c["size"], c["id"]))
    out["n_cases"] = len(cases)
    check = check_t1 if task == "t1" else check_t2
    limits = job.get("limits") or {}
    default_limit = float(job.get("max_case_s", 60.0))

    kind, detail = screen(job["code"])
    if kind is not None:
        out["error"] = kind
        out["fail_msg"] = detail
        emit()
        return

    mem = int(job.get("rlimit_as_bytes", 2 * 1024 ** 3))
    resource.setrlimit(resource.RLIMIT_AS, (mem, mem))
    sys.setrecursionlimit(20000)
    threading.stack_size(256 * 1024 * 1024)
    sys.stdout = io.StringIO()
    sys.stdin = io.StringIO("")

    mod = types.ModuleType("cand")
    mod.__file__ = "<candidate>"
    sys.modules["cand"] = mod
    box = {}

    def do_exec():
        try:
            exec(compile(job["code"], "<candidate>", "exec"), mod.__dict__)
        except BaseException as e:  # noqa: BLE001 - candidate code may raise anything, incl. SystemExit
            box["exc"] = type(e).__name__ + ": " + str(e)[:200]

    th = threading.Thread(target=do_exec, daemon=True)
    th.start()
    th.join(10.0)
    if th.is_alive():
        out["error"] = "exec_timeout"
        emit()
        os._exit(0)
    if "exc" in box:
        out["error"] = "exec_error"
        out["fail_msg"] = box["exc"]
        emit()
        return
    solve = mod.__dict__.get("solve")
    if not callable(solve):
        out["error"] = "no_solve"
        emit()
        return

    t_total = time.perf_counter()
    for case in cases:
        args = make_args(task, case)
        res = {}

        def target():
            try:
                res["out"] = solve(*args)
            except BaseException as e:  # noqa: BLE001
                res["exc"] = type(e).__name__ + ": " + str(e)[:200]

        limit = float(limits.get(case["id"], default_limit))
        th = threading.Thread(target=target, daemon=True)
        t0 = time.perf_counter()
        th.start()
        th.join(limit)
        dt = time.perf_counter() - t0
        out["case_times"][case["id"]] = round(dt, 5)
        if th.is_alive():
            out["error"] = "timeout"
            out["fail_case"] = case["id"]
            out["fail_msg"] = f"exceeded {limit:.2f}s"
            out["wall_s"] = round(time.perf_counter() - t_total, 4)
            emit()
            os._exit(0)
        if "exc" in res:
            out["error"] = "runtime_error"
            out["fail_case"] = case["id"]
            out["fail_msg"] = res["exc"]
            break
        try:
            ok, msg = check(case, res["out"])
        except Exception as e:  # noqa: BLE001 - malformed outputs must not crash the checker
            ok, msg = False, "checker exception: " + type(e).__name__
        if not ok:
            out["error"] = "wrong_answer"
            out["fail_case"] = case["id"]
            out["fail_msg"] = msg[:200]
            break
        out["n_passed"] += 1
    out["wall_s"] = round(time.perf_counter() - t_total, 4)
    out["passed"] = out["n_passed"] == out["n_cases"]
    emit()


if __name__ == "__main__":
    main()
