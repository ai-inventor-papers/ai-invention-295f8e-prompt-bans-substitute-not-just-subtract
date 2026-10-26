"""Correctness harness (STEP 1.4). Two roles:

1. Subprocess entry (run with `python -I harness.py --task tK --code prog.py --tests tK.json --out res.json`):
   RLIMIT_AS 3 GB, recursion limit 20000, solution executed in a 256 MB-stack thread, per-case wall-clock limit
   enforced by the main thread (stop at first failure), result JSON written to --out.
2. Library: score_many() runs one harness subprocess per program in a spawn ProcessPool / thread pool.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import resource
import sys
import threading
import time

_HERE = os.path.dirname(os.path.abspath(__file__))


def _check(task: str, case: dict, result) -> tuple[bool, str]:
    if _HERE not in sys.path:
        sys.path.insert(0, _HERE)
    from tasks import check_t1, check_t2  # local import keeps subprocess startup light
    return check_t1(case, result) if task == "t1" else check_t2(case, result)


def _args_for(task: str, case: dict) -> tuple:
    if task == "t1":
        return (list(case["grid"]), tuple(case["start"]), tuple(case["goal"]))
    return (case["n"], [tuple(e) for e in case["edges"]], case["s"], case["t"])


def run_subprocess_entry() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True)
    ap.add_argument("--code", required=True)
    ap.add_argument("--tests", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max_cases", type=int, default=0)
    a = ap.parse_args()
    out_path = a.out
    tests = json.load(open(a.tests))
    cases = tests["cases"][: a.max_cases] if a.max_cases else tests["cases"]
    limits = [c.get("limit_s", 2.0) for c in cases]
    code = open(a.code).read()
    # check helpers are imported BEFORE the address-space cap so they never fail on import
    _check(a.task, cases[0], None)
    resource.setrlimit(resource.RLIMIT_AS, (3 * 1024**3, 3 * 1024**3))
    sys.setrecursionlimit(20000)
    threading.stack_size(256 * 1024 * 1024)
    state = {"cur": (-1, time.perf_counter()), "done": False, "res": None, "per_case": []}

    def worker() -> None:
        t_all = time.perf_counter()
        ns: dict = {"__name__": "solution", "__builtins__": __builtins__}
        try:
            exec(compile(code, "<solution>", "exec"), ns)
            fn = ns["solve"]
        except BaseException as e:  # noqa: BLE001 - any failure while loading the program is a failure
            state["res"] = {"passed": False, "fail_case": "load", "error": f"load:{type(e).__name__}",
                            "n_passed": 0, "wall_s": time.perf_counter() - t_all}
            state["done"] = True
            return
        n_ok = 0
        for i, case in enumerate(cases):
            args = copy.deepcopy(_args_for(a.task, case))
            t_case = time.perf_counter()
            state["cur"] = (i, t_case)
            try:
                r = fn(*args)
            except BaseException as e:  # noqa: BLE001 - includes RecursionError, MemoryError, SystemExit
                state["res"] = {"passed": False, "fail_case": case["id"], "error": f"exception:{type(e).__name__}",
                                "n_passed": n_ok, "wall_s": time.perf_counter() - t_all}
                state["done"] = True
                return
            dt = time.perf_counter() - t_case
            state["per_case"].append(round(dt, 5))
            try:
                ok, why = _check(a.task, case, r)
            except BaseException as e:  # noqa: BLE001
                ok, why = False, f"checker:{type(e).__name__}"
            if not ok:
                state["res"] = {"passed": False, "fail_case": case["id"], "error": f"wrong:{why}",
                                "n_passed": n_ok, "wall_s": time.perf_counter() - t_all}
                state["done"] = True
                return
            n_ok += 1
        state["res"] = {"passed": True, "fail_case": None, "error": None, "n_passed": n_ok,
                        "wall_s": time.perf_counter() - t_all}
        state["done"] = True

    devnull = open(os.devnull, "w")
    sys.stdout = devnull
    sys.stderr = devnull
    th = threading.Thread(target=worker, daemon=True)
    th.start()
    while not state["done"]:
        th.join(0.005)
        i, t_case = state["cur"]
        if i >= 0 and not state["done"] and time.perf_counter() - t_case > limits[i]:
            state["res"] = {"passed": False, "fail_case": cases[i]["id"], "error": "timeout",
                            "n_passed": i, "wall_s": None}
            break
    res = dict(state["res"])
    res["per_case_s"] = state["per_case"]
    with open(out_path, "w") as f:
        json.dump(res, f)
    os._exit(0)


# ------------------------------------------------------------------------------------------------ library side
def score_one(task: str, code: str, tests_path: str, workdir: str, max_cases: int = 0, timeout_pad: float = 5.0) -> dict:
    import subprocess
    import tempfile
    import uuid
    tests_path = os.path.abspath(tests_path)
    workdir = os.path.abspath(workdir)
    tests = json.load(open(tests_path))
    cases = tests["cases"][:max_cases] if max_cases else tests["cases"]
    budget = sum(c.get("limit_s", 2.0) for c in cases) + timeout_pad
    os.makedirs(workdir, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=workdir) as td:
        prog = os.path.join(td, "prog.py")
        out = os.path.join(td, f"res_{uuid.uuid4().hex}.json")
        with open(prog, "w") as f:
            f.write(code)
        cmd = [sys.executable, "-I", os.path.join(_HERE, "harness.py"), "--task", task, "--code", prog,
               "--tests", tests_path, "--out", out]
        if max_cases:
            cmd += ["--max_cases", str(max_cases)]
        t0 = time.time()
        try:
            p = subprocess.run(cmd, cwd=td, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                               stderr=subprocess.PIPE, timeout=budget)
            err_tail = p.stderr.decode(errors="replace")[-300:]
        except subprocess.TimeoutExpired:
            return {"passed": False, "fail_case": None, "error": "killed_total_budget", "n_passed": None,
                    "wall_s": None, "elapsed": time.time() - t0}
        if not os.path.exists(out):
            return {"passed": False, "fail_case": None, "error": f"crash:rc={p.returncode}:{err_tail}",
                    "n_passed": None, "wall_s": None, "elapsed": time.time() - t0}
        res = json.load(open(out))
        res["elapsed"] = time.time() - t0
        return res


def _score_job(job: tuple) -> dict:
    task, code, tests_path, workdir, key = job
    try:
        r = score_one(task, code, tests_path, workdir)
    except Exception as e:  # noqa: BLE001 - never let one program kill the pool
        r = {"passed": False, "error": f"harness_error:{e!r}"}
    r["key"] = key
    return r


def score_many(jobs: list[tuple], n_workers: int = 4) -> list[dict]:
    """jobs: (task, code, tests_path, workdir, key). Threads are enough: each job is its own subprocess."""
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=n_workers) as ex:
        return list(ex.map(_score_job, jobs))


if __name__ == "__main__":
    run_subprocess_entry()
