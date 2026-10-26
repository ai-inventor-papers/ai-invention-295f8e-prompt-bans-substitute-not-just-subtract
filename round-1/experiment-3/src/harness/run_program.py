"""Sandboxed runner: `python -I harness/run_program.py --task T1 --code FILE --out FILE`.

Extracts the first ```python block, installs the runtime tracer, executes the candidate, traces solve() on crafted
inputs, runs the hidden tests with per-case limits, computes the AST label and writes one JSON result.
"""

from __future__ import annotations

import argparse
import builtins
import io
import json
import resource
import signal
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from harness.extract import extract_code  # noqa: E402
from labeller import tracer  # noqa: E402
from labeller.ast_rules import ast_label  # noqa: E402


class CaseTimeout(BaseException):
    pass


def _alarm(signum, frame):
    raise CaseTimeout()


def _set_limits() -> None:
    try:
        resource.setrlimit(resource.RLIMIT_AS, (4 * 1024 ** 3, 4 * 1024 ** 3))
        resource.setrlimit(resource.RLIMIT_CPU, (120, 125))
    except (ValueError, OSError):
        pass
    sys.setrecursionlimit(20000)


def _jsonable(x, depth=0):
    if depth > 4:
        return str(x)[:200]
    if isinstance(x, (str, int, float, bool)) or x is None:
        return x
    if isinstance(x, dict):
        return {str(k): _jsonable(v, depth + 1) for k, v in list(x.items())[:200]}
    if isinstance(x, (list, tuple)):
        return [_jsonable(v, depth + 1) for v in list(x)[:200]]
    return str(x)[:200]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True, choices=["T1", "T2"])
    ap.add_argument("--code", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--no-tests", action="store_true")
    ap.add_argument("--raw", action="store_true", help="file holds bare code, not a model response")
    args = ap.parse_args()
    _set_limits()
    t0 = time.perf_counter()
    text = Path(args.code).read_text()
    code = text if args.raw else extract_code(text)
    res: dict = {"passed": False, "wall_s": None, "n_failed": None, "n_run": 0, "first_error": None,
                 "tracer_features": None, "runtime_label": None, "runtime_rule": None, "ast_label": None,
                 "label": None, "labeller_source": None, "exec_error": None}
    if code is None:
        res.update(label="no_code", labeller_source="no_block", ast_label="no_code", runtime_label="no_code",
                   first_error="no ```python block")
        Path(args.out).write_text(json.dumps(res))
        return
    alab, afeat = ast_label(args.task, code)
    res["ast_label"] = alab
    res["ast_features"] = {k: v for k, v in afeat.items() if k != "imports"}
    tracer.install()
    real_stdout, real_stderr = sys.stdout, sys.stderr
    sink = io.StringIO()
    ns: dict = {"__name__": "candidate", "__builtins__": builtins}
    signal.signal(signal.SIGALRM, _alarm)
    try:
        compiled = compile(code, tracer.CAND_FILE, "exec")
        sys.stdout = sys.stderr = sink
        signal.setitimer(signal.ITIMER_REAL, 5.0)
        exec(compiled, ns)  # noqa: S102 - sandboxed child process with rlimits
    except CaseTimeout:
        res["exec_error"] = "timeout at import"
    except BaseException as e:  # noqa: BLE001
        res["exec_error"] = f"{type(e).__name__}: {str(e)[:200]}"
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        sys.stdout, sys.stderr = real_stdout, real_stderr
    solve = ns.get("solve")
    if not callable(solve):
        res.update(label="no_code", labeller_source="no_solve", runtime_label="no_code", ast_label="no_code",
                   first_error=res["exec_error"] or "no callable solve")
        Path(args.out).write_text(json.dumps(res))
        return
    # ---------------- tracer phase
    try:
        sys.stdout = sys.stderr = io.StringIO()
        tr = tracer.trace_t1(solve) if args.task == "T1" else tracer.trace_t2(solve)
    except BaseException as e:  # noqa: BLE001
        tr = {"runtime_label": None, "rule": f"tracer_crash:{type(e).__name__}"}
    finally:
        sys.stdout, sys.stderr = real_stdout, real_stderr
    res["runtime_label"] = tr.get("runtime_label")
    res["runtime_rule"] = tr.get("rule")
    res["tracer_features"] = _jsonable({k: v for k, v in tr.items() if k not in ("runtime_label", "rule")})
    if res["runtime_label"] is not None:
        res["label"], res["labeller_source"] = res["runtime_label"], "runtime"
    else:
        res["label"], res["labeller_source"] = alab, "ast_fallback"
    # ---------------- hidden tests
    if not args.no_tests:
        if args.task == "T1":
            from tasks import t1_grid as T
        else:
            from tasks import t2_wsp as T
        spec = json.loads((ROOT / "tasks" / f"{args.task}_cases.json").read_text())
        cases, limits = spec["cases"], spec["limits"]
        n_failed = 0
        n_run = 0
        tt = time.perf_counter()
        for case, lim in zip(cases, limits):
            n_run += 1
            a = T.case_args(case)
            ok, why = False, ""
            try:
                sys.stdout = sys.stderr = io.StringIO()
                signal.signal(signal.SIGALRM, _alarm)
                c0 = time.perf_counter()
                signal.setitimer(signal.ITIMER_REAL, lim)
                out = solve(*a)
                signal.setitimer(signal.ITIMER_REAL, 0)
                el = time.perf_counter() - c0
                if el > lim:
                    ok, why = False, f"case {case['name']}: over limit {el:.2f}s > {lim:.2f}s"
                else:
                    ok, why = T.validate(case, out)
                    if not ok:
                        why = f"case {case['name']}: {why}"
            except CaseTimeout:
                ok, why = False, f"case {case['name']}: timeout > {lim:.2f}s"
            except RecursionError:
                ok, why = False, f"case {case['name']}: RecursionError"
            except BaseException as e:  # noqa: BLE001
                ok, why = False, f"case {case['name']}: {type(e).__name__}: {str(e)[:160]}"
            finally:
                signal.setitimer(signal.ITIMER_REAL, 0)
                sys.stdout, sys.stderr = real_stdout, real_stderr
            if not ok:
                n_failed += 1
                if res["first_error"] is None:
                    res["first_error"] = why
                if "timeout" in why or "over limit" in why or n_failed >= 3:
                    break  # fail fast: pathological programs must not hold a worker
        res["n_failed"] = n_failed
        res["n_run"] = n_run
        res["n_cases"] = len(cases)
        res["passed"] = n_failed == 0 and n_run == len(cases)
        res["test_wall_s"] = time.perf_counter() - tt
    res["wall_s"] = time.perf_counter() - t0
    Path(args.out).write_text(json.dumps(res))


if __name__ == "__main__":
    main()
