"""Child side of the S1 re-timing harness (stdlib only; run as `python -I time_child.py` with a JSON job on stdin).

One harness for every unit: the reference is exec'd in a fresh interpreter, each case's inputs are deep-copied
OUTSIDE the timed region, and only the call `solve(...)` is timed with time.perf_counter. The whole case loop runs
in one worker thread with a 256 MB stack so recursive references are not penalised (same convention as the exp8
path-task sandbox). Correctness uses the unit's own checker:
  {"type": "module", "path": <checker.py defining check(kwargs, expected, output)>}   bench and panel-A units
  {"type": "kind", "kind": "exact" | "subsets" | "bool"}                              panel-B units (exp26 rules)
  {"type": "path", "tasks_dir": <suite/tasks>, "task": "t1" | "t2"}                   path tasks (tests_gen.check_t*)
Job: {"code_path", "mode": "kwargs"|"args"|"t1"|"t2", "cases": [...], "checker": {...}, "check": bool}
Prints ONE JSON line: {"load_error": str|null, "cases": [{"i", "t", "ok", "status"}]}.
"""

import copy
import importlib.util
import json
import sys
import threading
import time


def _kind_check(kind, got, exp):
    # identical to exp26 src/sandbox_tests.py::_check
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


def _make_args(mode, case):
    if mode == "kwargs":
        return (), case["kwargs"]
    if mode == "args":
        return tuple(case["args"]), {}
    if mode == "t1":
        return (list(case["grid"]), tuple(case["start"]), tuple(case["goal"])), {}
    return (case["n"], [tuple(e) for e in case["edges"]], case["s"], case["t"]), {}


def main():
    job = json.loads(sys.stdin.read())
    out = {"load_error": None, "cases": []}
    sys.setrecursionlimit(200000)
    ns = {"__name__": "cand"}
    try:
        code = open(job["code_path"], encoding="utf-8").read()
        exec(compile(code, "<reference>", "exec"), ns)
        fn = ns["solve"]
    except BaseException as e:  # noqa: BLE001
        out["load_error"] = f"{type(e).__name__}: {str(e)[:200]}"
        print(json.dumps(out))
        return
    chk = job["checker"]
    check_fn = None
    if job.get("check", True):
        if chk["type"] == "module":
            spec = importlib.util.spec_from_file_location("unit_checker", chk["path"])
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            check_fn = lambda case, got: bool(mod.check(case["kwargs"], case["expected"], got))  # noqa: E731
        elif chk["type"] == "kind":
            check_fn = lambda case, got: _kind_check(chk["kind"], got, case["expected"])  # noqa: E731
        else:
            sys.path.insert(0, chk["tasks_dir"])
            import tests_gen  # noqa: E402  (stdlib-only module of the exp8 suite)
            f = tests_gen.check_t1 if chk["task"] == "t1" else tests_gen.check_t2
            check_fn = lambda case, got: bool(f(case, got)[0])  # noqa: E731

    def run_all():
        for i, case in enumerate(job["cases"]):
            args, kwargs = _make_args(job["mode"], case)
            a, k = copy.deepcopy(args), copy.deepcopy(kwargs)
            status, ok = "ok", True
            t0 = time.perf_counter()
            try:
                got = fn(*a, **k)
                dt = time.perf_counter() - t0
            except BaseException as e:  # noqa: BLE001
                dt = time.perf_counter() - t0
                status, ok, got = f"error:{type(e).__name__}", False, None
            if ok and check_fn is not None:
                try:
                    ok = check_fn(case, got)
                except BaseException:  # noqa: BLE001
                    ok = False
                if not ok:
                    status = "wrong"
            out["cases"].append({"i": i, "t": dt, "ok": ok, "status": status})

    threading.stack_size(256 * 1024 * 1024)
    th = threading.Thread(target=run_all)
    th.start()
    th.join()
    print(json.dumps(out))


main()
