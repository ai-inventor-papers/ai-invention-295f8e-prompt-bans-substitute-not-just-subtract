#!/usr/bin/env python3
"""Sandboxed runner, invoked as:  python -I runner.py <job.json> <result.json>

Phase A runs the candidate's solve() on the hidden tests (fresh argument copies, per-test alarm at the
case's wall-clock limit, stop at the first failure). Phase B re-executes the candidate with instrumented
modules and traced lists on the 3 tracer probes. RLIMIT_AS = 2 GB. Results go to <result.json>; the
candidate's own stdout / stderr / stdin are redirected to /dev/null.
"""
import builtins
import importlib.util
import json
import os
import resource
import signal
import sys
import time


class _Timeout(BaseException):
    """BaseException so that a candidate's `except Exception` cannot swallow the alarm."""


def _alarm(signum, frame):
    raise _Timeout()


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _exec_candidate(code_obj, extra=None):
    ns = {"__name__": "candidate", "__builtins__": builtins}
    if extra:
        ns.update(extra)
    err = None
    signal.setitimer(signal.ITIMER_REAL, 5.0)
    try:
        exec(code_obj, ns)
    except _Timeout:
        err = "module-level timeout"
    except BaseException as e:  # noqa: BLE001 - candidate code may raise anything, incl. SystemExit
        err = f"module-level {type(e).__name__}: {str(e)[:200]}"
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
    return ns, err


def main():
    job_path, res_path = sys.argv[1], sys.argv[2]
    with open(job_path) as f:
        job = json.load(f)
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024 ** 3, 2 * 1024 ** 3))
    signal.signal(signal.SIGALRM, _alarm)
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(here)
    task = job["task"]
    tmod = _load(os.path.join(root, "tasks", "t1_grid.py" if task == "T1" else "t2_wsp.py"), "taskmod")
    tracer = _load(os.path.join(here, "tracer.py"), "tracer_mod")
    with open(job["tests_file"]) as f:
        tests = json.load(f)["cases"]
    res = {"has_solve": False, "exec_error": None, "passed": False, "n_tests": len(tests), "n_run": 0,
           "first_failure": None, "wall_s": 0.0, "trace": None, "trace_error": None}
    devnull = open(os.devnull, "w")
    real_out, real_err = sys.stdout, sys.stderr
    sys.stdin = open(os.devnull)
    code = job["code"]
    try:
        code_obj = compile(code, "<candidate>", "exec")
    except (SyntaxError, ValueError) as e:
        res["exec_error"] = f"SyntaxError: {str(e)[:200]}"
        code_obj = None
    if code_obj is not None:
        sys.stdout, sys.stderr = devnull, devnull
        ns, err = _exec_candidate(code_obj)
        res["exec_error"] = err
        solve = ns.get("solve")
        res["has_solve"] = callable(solve)
        if callable(solve):
            t_all = time.time()
            ok_all = True
            for case in tests:
                args = tmod.call_args(case)
                lim = float(case.get("limit_s", 1.0))
                t0 = time.time()
                signal.setitimer(signal.ITIMER_REAL, lim)
                try:
                    out = solve(*args)
                    signal.setitimer(signal.ITIMER_REAL, 0)
                    ok, msg = tmod.check(case, out)
                except _Timeout:
                    ok, msg = False, f"timeout > {lim:.2f}s"
                except RecursionError:
                    signal.setitimer(signal.ITIMER_REAL, 0)
                    ok, msg = False, "RecursionError"
                except MemoryError:
                    signal.setitimer(signal.ITIMER_REAL, 0)
                    ok, msg = False, "MemoryError"
                except BaseException as e:  # noqa: BLE001
                    signal.setitimer(signal.ITIMER_REAL, 0)
                    ok, msg = False, f"{type(e).__name__}: {str(e)[:160]}"
                res["n_run"] += 1
                if not ok:
                    ok_all = False
                    res["first_failure"] = {"id": case["id"], "kind": case.get("kind"), "msg": msg,
                                            "t": round(time.time() - t0, 3)}
                    break
            res["wall_s"] = round(time.time() - t_all, 3)
            res["passed"] = ok_all
        sys.stdout, sys.stderr = real_out, real_err
    # Phase B: runtime trace on probes
    if code_obj is not None and job.get("trace", True) and res["has_solve"]:
        try:
            tracer.install()
            tcode = tracer.transform(code)
            sys.stdout, sys.stderr = devnull, devnull
            ns, err = _exec_candidate(tcode, {"__TL__": tracer.TL})
            solve = ns.get("solve")
            feats, perr = {}, {}
            if callable(solve):
                for probe in tmod.probes():
                    tracer.reset_probe_counters()
                    tracer.setup_probe(task, probe)
                    a = probe["args"]
                    if task == "T1":
                        args = ([str(r) for r in a["grid"]], tuple(a["start"]), tuple(a["goal"]))
                        n_edges = 0
                    else:
                        edges = tracer.TEdges([tuple(e) for e in a["edges"]])
                        args = (a["n"], edges, a["s"], a["t"])
                        n_edges = len(a["edges"])
                    sys.setprofile(tracer.profiler)
                    signal.setitimer(signal.ITIMER_REAL, float(job.get("probe_timeout", 3.0)))
                    try:
                        solve(*args)
                    except _Timeout:
                        perr[probe["id"]] = "timeout"
                    except BaseException as e:  # noqa: BLE001
                        perr[probe["id"]] = f"{type(e).__name__}: {str(e)[:120]}"
                    finally:
                        signal.setitimer(signal.ITIMER_REAL, 0)
                        sys.setprofile(None)
                    feats[probe["id"]] = tracer.features(task, probe, n_edges)
            sys.stdout, sys.stderr = real_out, real_err
            res["trace"] = feats
            res["trace_error"] = perr or err
        except BaseException as e:  # noqa: BLE001 - tracing failure must not lose the test result
            sys.stdout, sys.stderr = real_out, real_err
            sys.setprofile(None)
            res["trace_error"] = f"tracer {type(e).__name__}: {str(e)[:200]}"
    with open(res_path, "w") as f:
        json.dump(res, f)


if __name__ == "__main__":
    main()
