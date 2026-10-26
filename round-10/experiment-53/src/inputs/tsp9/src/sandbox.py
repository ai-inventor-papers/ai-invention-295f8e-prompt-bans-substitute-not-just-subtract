"""Sandbox for generated select_next_node programs: static AST check + fork-server execution with rlimits.

Evaluator processes (spawn context) import numpy once (1 thread), then os.fork() one child per program.
The child sets RLIMIT_CPU / RLIMIT_AS / RLIMIT_FSIZE, chdirs to an empty temp dir, execs the program in a
namespace with restricted builtins and a guarded __import__, re-execs it fresh for every instance, and
sends results back through a pipe. The parent enforces a wall limit of 3x the CPU limit.
"""
from __future__ import annotations

import ast
import builtins
import hashlib
import os
import pickle
import random
import re
import resource
import select
import signal
import tempfile
import time

import numpy as np

ALLOWED_IMPORTS = {"numpy", "math", "random", "heapq", "itertools", "collections", "functools", "typing", "bisect"}
FORBIDDEN_NAMES = {"open", "exec", "eval", "compile", "__import__", "globals", "locals", "vars", "input",
                   "breakpoint", "exit", "quit", "help", "memoryview", "__builtins__", "__loader__", "__spec__"}
FORBIDDEN_MODULE_NAMES = {"os", "sys", "subprocess", "socket", "importlib", "builtins", "shutil", "pathlib",
                          "ctypes", "multiprocessing", "threading", "signal", "resource", "gc", "inspect"}
SAFE_CALLS_IN_CONST = {"float", "int", "abs", "round", "tuple", "list", "dict", "set", "frozenset", "range",
                       "min", "max", "pow", "complex", "bool", "str", "len", "sum"}
ERROR_CLASSES = ["no_code", "syntax_error", "import_violation", "runtime_error", "invalid_return", "timeout",
                 "truncated"]
FUNC = "select_next_node"


class StaticReject(Exception):
    def __init__(self, cls: str, reason: str):
        super().__init__(reason)
        self.cls, self.reason = cls, reason


def _is_const_expr(node: ast.AST) -> bool:
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call):
            f = sub.func
            ok = (isinstance(f, ast.Name) and f.id in SAFE_CALLS_IN_CONST) or (
                isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id in ("np", "math", "numpy"))
            if not ok:
                return False
        elif isinstance(sub, (ast.Lambda, ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp, ast.Await,
                              ast.Yield, ast.YieldFrom, ast.NamedExpr)):
            return False
    return True


def static_check(code: str) -> str:
    """Return sanitised source (top level: imports, defs, constant assignments) or raise StaticReject."""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise StaticReject("syntax_error", f"{e.msg} line {e.lineno}") from None
    keep = []
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
            for nm in names:
                if nm.split(".")[0] not in ALLOWED_IMPORTS or (isinstance(node, ast.ImportFrom) and node.level):
                    raise StaticReject("import_violation", f"import {nm}")
            keep.append(node)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            keep.append(node)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)) and node.value is not None:
            tg = node.targets if isinstance(node, ast.Assign) else [node.target]
            if all(isinstance(t, (ast.Name, ast.Tuple)) for t in tg) and _is_const_expr(node.value):
                keep.append(node)
        # every other top-level statement (prints, tests, loops, if __name__ ...) is stripped
    for sub in ast.walk(ast.Module(body=keep, type_ignores=[])):
        if isinstance(sub, (ast.Import, ast.ImportFrom)):
            names = [a.name for a in sub.names] if isinstance(sub, ast.Import) else [sub.module or ""]
            for nm in names:
                if nm.split(".")[0] not in ALLOWED_IMPORTS or (isinstance(sub, ast.ImportFrom) and sub.level):
                    raise StaticReject("import_violation", f"import {nm}")
        elif isinstance(sub, ast.Name):
            if sub.id in FORBIDDEN_NAMES or sub.id in FORBIDDEN_MODULE_NAMES:
                raise StaticReject("import_violation", f"forbidden name {sub.id}")
        elif isinstance(sub, ast.Attribute):
            if sub.attr.startswith("__") and sub.attr not in ("__name__", "__init__", "__len__", "__lt__",
                                                              "__eq__", "__hash__", "__repr__", "__iter__"):
                raise StaticReject("import_violation", f"dunder attribute {sub.attr}")
        elif isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name) and sub.func.id in ("getattr", "setattr",
                                                                                            "delattr", "hasattr"):
            for a in sub.args[1:2]:
                if not (isinstance(a, ast.Constant) and isinstance(a.value, str) and not a.value.startswith("_")):
                    raise StaticReject("import_violation", f"{sub.func.id} with non-literal/dunder name")
    if not any(isinstance(n, ast.FunctionDef) and n.name == FUNC for n in keep):
        raise StaticReject("no_code", f"no {FUNC} defined")
    return ast.unparse(ast.Module(body=keep, type_ignores=[]))


def strip_docstrings(tree: ast.AST) -> ast.AST:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
            b = node.body
            if b and isinstance(b[0], ast.Expr) and isinstance(b[0].value, ast.Constant) and isinstance(
                    b[0].value.value, str):
                node.body = b[1:] or [ast.Pass()]
    return tree


def ast_hash(code: str) -> str | None:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None
    return hashlib.sha256(ast.dump(strip_docstrings(tree), annotate_fields=False).encode()).hexdigest()


def uses_random(code: str) -> bool:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return False
    for sub in ast.walk(tree):
        if isinstance(sub, ast.Name) and sub.id == "random":
            return True
        if isinstance(sub, ast.Attribute) and sub.attr == "random":
            return True
    return False


# ------------------------------------------------------------------ child-side execution
def _guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
    if level != 0 or name.split(".")[0] not in ALLOWED_IMPORTS:
        raise ImportError(f"import of {name} is not allowed")
    return builtins.__import__(name, globals, locals, fromlist, level)


def _safe_builtins() -> dict:
    sb = {k: getattr(builtins, k) for k in dir(builtins) if k not in FORBIDDEN_NAMES and not k.startswith("_")}
    sb["__import__"] = _guarded_import
    sb["__build_class__"] = builtins.__build_class__
    sb["__name__"] = "candidate"
    return sb


class InvalidReturn(Exception):
    pass


def _fresh_fn(code_obj):
    ns = {"__builtins__": _safe_builtins(), "__name__": "candidate"}
    exec(code_obj, ns)
    fn = ns.get(FUNC)
    if not callable(fn):
        raise InvalidReturn(f"{FUNC} not callable")
    return fn


def _as_city(x, U: set) -> int:
    if isinstance(x, (bool, np.bool_)) or x is None:
        raise InvalidReturn(f"returned {x!r}")
    if isinstance(x, (int, np.integer)):
        v = int(x)
    elif isinstance(x, (float, np.floating)):
        if float(x) != int(x):
            raise InvalidReturn(f"non-integer {x!r}")
        v = int(x)
    else:
        raise InvalidReturn(f"returned type {type(x).__name__}")
    if v not in U:
        raise InvalidReturn(f"returned {v} not in unvisited")
    return v


def run_tours(code_obj, mats, seeds) -> list[float]:
    """Build closed tours from city 0 on each instance; returns lengths (raises on any failure)."""
    out = []
    for D, sd in zip(mats, seeds):
        fn = _fresh_fn(code_obj)
        n = D.shape[0]
        np.random.seed(sd % (2 ** 32))
        random.seed(sd)
        cur, tour, U = 0, [0], set(range(1, n))
        for _ in range(n - 1):
            nxt = _as_city(fn(cur, 0, set(U), D), U)
            tour.append(nxt)
            U.remove(nxt)
            cur = nxt
        t = np.asarray(tour)
        out.append(float(D[t, np.roll(t, -1)].sum()))
    return out


def run_probes(code_obj, states, mats) -> list[int]:
    """One decision per probe state; -1 = ERR (exception or invalid return)."""
    dec = []
    for k, (inst, cur, unv) in enumerate(states):
        try:
            fn = _fresh_fn(code_obj)
            np.random.seed((930000 + k) % (2 ** 32))
            random.seed(930000 + k)
            U = set(unv)
            dec.append(_as_city(fn(cur, 0, set(U), mats[inst]), U))
        except Exception:  # noqa: BLE001 - any failure of the candidate is an ERR decision
            dec.append(-1)
    return dec


def _child(wfd: int, code: str, mode: str, payload, cpu_limit: int) -> None:
    try:
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_limit, cpu_limit + 1))
        resource.setrlimit(resource.RLIMIT_AS, (2 * 1024 ** 3, 2 * 1024 ** 3))
        resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
        try:
            os.nice(5)
        except OSError:
            pass
        os.chdir(tempfile.mkdtemp(prefix="sbx_"))
        code_obj = compile(code, "<candidate>", "exec")
        t0 = time.process_time()
        if mode == "tours":
            mats, seeds = payload
            res = {"ok": True, "lengths": run_tours(code_obj, mats, seeds)}
        else:
            states, mats = payload
            res = {"ok": True, "decisions": run_probes(code_obj, states, mats)}
        res["cpu"] = time.process_time() - t0
    except InvalidReturn as e:
        res = {"ok": False, "cls": "invalid_return", "reason": str(e)[:300]}
    except MemoryError as e:
        res = {"ok": False, "cls": "runtime_error", "reason": f"MemoryError {e}"[:300]}
    except ImportError as e:
        res = {"ok": False, "cls": "import_violation", "reason": str(e)[:300]}
    except RecursionError as e:
        res = {"ok": False, "cls": "runtime_error", "reason": f"RecursionError {e}"[:300]}
    except BaseException as e:  # noqa: BLE001 - candidate code may raise anything
        res = {"ok": False, "cls": "runtime_error", "reason": f"{type(e).__name__}: {e}"[:300]}
    try:
        data = pickle.dumps(res)
        with os.fdopen(wfd, "wb") as w:
            w.write(data)
    except BaseException:  # noqa: BLE001
        pass
    os._exit(0)


def fork_eval(code: str, mode: str, payload, cpu_limit: int) -> dict:
    """Fork a child that runs `code`; parent enforces wall = 3 x cpu limit."""
    rfd, wfd = os.pipe()
    t0 = time.time()
    pid = os.fork()
    if pid == 0:
        os.close(rfd)
        _child(wfd, code, mode, payload, cpu_limit)
        os._exit(0)
    os.close(wfd)
    chunks, deadline, killed = [], t0 + 3 * cpu_limit, False
    while True:
        left = deadline - time.time()
        if left <= 0:
            os.kill(pid, signal.SIGKILL)
            killed = True
            break
        r, _, _ = select.select([rfd], [], [], min(left, 1.0))
        if r:
            b = os.read(rfd, 1 << 20)
            if not b:
                break
            chunks.append(b)
    os.close(rfd)
    _, status = os.waitpid(pid, 0)
    ru = resource.getrusage(resource.RUSAGE_CHILDREN)
    wall = time.time() - t0
    if killed:
        return {"ok": False, "cls": "timeout", "reason": "wall limit", "wall": wall}
    if os.WIFSIGNALED(status) and os.WTERMSIG(status) in (signal.SIGXCPU, signal.SIGKILL):
        return {"ok": False, "cls": "timeout", "reason": f"cpu limit (signal {os.WTERMSIG(status)})", "wall": wall}
    try:
        res = pickle.loads(b"".join(chunks))
    except Exception:  # noqa: BLE001
        sig = os.WTERMSIG(status) if os.WIFSIGNALED(status) else None
        return {"ok": False, "cls": "runtime_error", "reason": f"child died (signal {sig})", "wall": wall}
    res["wall"] = wall
    _ = ru
    return res


# ------------------------------------------------------------------ evaluator worker (spawned process)
_W: dict = {}


def worker_init(sets_payload: dict) -> None:
    """sets_payload: {'selection': (mats, seeds), 'heldout': ..., 'probe_states': [...], 'probe_mats': [...]}"""
    os.environ["OMP_NUM_THREADS"] = "1"
    _W.update(sets_payload)
    for k in list(_W):
        if k.endswith("_mats") or k in ("selection", "heldout", "heldout_ext", "tsplib"):
            pass
    # make matrices read-only (in-place writes by candidates raise ValueError -> runtime_error)
    for key, val in _W.items():
        if isinstance(val, tuple) and len(val) == 2 and isinstance(val[0], list):
            for D in val[0]:
                D.setflags(write=False)
    for D in _W.get("probe_mats", []):
        D.setflags(write=False)


def evaluate_tours(code: str, set_name: str, cpu_limit: int = 10) -> dict:
    mats, seeds = _W[set_name]
    return fork_eval(code, "tours", (mats, seeds), cpu_limit)


def evaluate_probes(code: str, cpu_limit: int = 20) -> dict:
    return fork_eval(code, "probes", (_W["probe_states"], _W["probe_mats"]), cpu_limit)


def evaluate_program(raw_program: str, cpu_limit: int = 10) -> dict:
    """Static check + SELECTION evaluation. Returns dict with label, lengths, cpu, reason."""
    try:
        code = static_check(raw_program)
    except StaticReject as e:
        return {"label": e.cls, "reason": e.reason, "lengths": None, "cpu": 0.0, "code_exec": None}
    res = evaluate_tours(code, "selection", cpu_limit)
    if res.get("ok"):
        return {"label": "valid", "lengths": res["lengths"], "cpu": res.get("cpu"), "wall": res.get("wall"),
                "code_exec": code, "reason": None}
    return {"label": res["cls"], "reason": res.get("reason"), "lengths": None, "cpu": res.get("cpu"),
            "wall": res.get("wall"), "code_exec": code}


def evaluate_set(raw_program: str, set_name: str, cpu_limit: int = 300) -> dict:
    try:
        code = static_check(raw_program)
    except StaticReject as e:
        return {"label": e.cls, "reason": e.reason, "lengths": None}
    res = evaluate_tours(code, set_name, cpu_limit)
    if res.get("ok"):
        return {"label": "valid", "lengths": res["lengths"], "cpu": res.get("cpu")}
    return {"label": res["cls"], "reason": res.get("reason"), "lengths": None}


def probe_program(raw_program: str, cpu_limit: int = 20) -> dict:
    try:
        code = static_check(raw_program)
    except StaticReject as e:
        return {"label": e.cls, "decisions": None}
    res = evaluate_probes(code, cpu_limit)
    if res.get("ok"):
        return {"label": "ok", "decisions": res["decisions"], "cpu": res.get("cpu")}
    return {"label": res["cls"], "reason": res.get("reason"), "decisions": None}


def rename_target(code: str, version: int) -> str:
    return re.sub(rf"\b{FUNC}_v{version}\b", FUNC, code)
