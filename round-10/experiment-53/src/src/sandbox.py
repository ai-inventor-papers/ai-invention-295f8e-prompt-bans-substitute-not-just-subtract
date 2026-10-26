"""Sandbox for generated select_next_node programs: static AST check + fork-server execution with rlimits.

Adapted from TSP9 (inputs/tsp9/src/sandbox.py). Changes for iteration 10 (ReEvo eval.py semantics):
  * every call receives distance_matrix = D.copy() (a fresh WRITABLE copy) and unvisited_nodes = set(U);
  * SELECTION and PROBES run in the same forked child: soft RLIMIT_CPU 30 s / hard 62 s, and before the probe phase
    the child raises its soft limit to (CPU used + 30 s); an overrun is classified by phase (timeout / probe_timeout);
  * the child reports each phase through a length-prefixed pickle frame, so a probe-phase death keeps the
    SELECTION result.
Evaluator processes (spawn context) import numpy once (1 thread), then os.fork() one child per program. The child
sets RLIMIT_CPU / RLIMIT_AS / RLIMIT_FSIZE, chdirs to an empty temp dir, execs the program in a namespace with
restricted builtins and a guarded __import__, re-execs it fresh for every instance (tours) and every probe call,
and the parent enforces a wall limit of 1.5 x the CPU limit per phase.
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
import struct
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
SEL_CPU = 30          # s CPU for the 64 SELECTION instances together
PROBE_CPU = 30        # s CPU for the 2,000 probe calls
HARD_CPU = 62         # hard RLIMIT_CPU of the combined child
WALL_FACTOR = 1.5     # parent wall limit = 1.5 x CPU limit (per phase)
SET_CPU = 600         # s CPU per HELDOUT / EXT / TSPLIB set
MEM_LIMIT = 2 * 1024 ** 3
PROBE_ERR_MAX = 0.10  # PROBE-VALID requires at most 10% ERR decisions
ERR = -1


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
    """sha256 of the AST dump with docstrings stripped (comments never reach the AST)."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None
    return hashlib.sha256(ast.dump(strip_docstrings(tree), annotate_fields=False).encode()).hexdigest()


# ------------------------------------------------------------------ child-side execution
_SBX = {"dir": None}


def _sbx_dir() -> str:
    """An empty working directory per evaluator process, created BEFORE the child's RLIMIT_FSIZE 0 (inside the
    workspace: scratch/sbx/<pid>); the child cannot write files there (FSIZE 0, no open/os)."""
    if _SBX["dir"] is None or not os.path.isdir(_SBX["dir"]):
        root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scratch", "sbx",
                            str(os.getpid()))
        os.makedirs(root, exist_ok=True)
        _SBX["dir"] = root
    return _SBX["dir"]


class CpuLimit(BaseException):
    """Raised from the SIGXCPU handler; BaseException so candidate `except Exception` cannot swallow it."""


def _on_xcpu(signum, frame):  # noqa: ARG001
    raise CpuLimit()


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
    """Accept ints, numpy ints and integral floats that are in the unvisited set."""
    if isinstance(x, (bool, np.bool_)) or x is None:
        raise InvalidReturn(f"returned {x!r}")
    if isinstance(x, (int, np.integer)):
        v = int(x)
    elif isinstance(x, (float, np.floating)):
        if not np.isfinite(x) or float(x) != int(x):
            raise InvalidReturn(f"non-integer {x!r}")
        v = int(x)
    elif isinstance(x, np.ndarray) and x.ndim == 0 and np.issubdtype(x.dtype, np.integer):
        v = int(x)
    else:
        raise InvalidReturn(f"returned type {type(x).__name__}")
    if v not in U:
        raise InvalidReturn(f"returned {v} not in unvisited")
    return v


def run_tours(code_obj, mats, seeds, tours_out: list | None = None) -> list[float]:
    """Build closed tours from city 0 on each instance (ReEvo protocol); returns lengths (raises on any failure).

    Every call gets a fresh set copy and a fresh writable matrix copy; np.random / random are seeded once per
    instance with the instance seed; the program is exec'd fresh per instance.
    """
    out = []
    for D, sd in zip(mats, seeds):
        fn = _fresh_fn(code_obj)
        n = D.shape[0]
        np.random.seed(sd % (2 ** 32))
        random.seed(sd)
        cur, tour, U = 0, [0], set(range(1, n))
        for _ in range(n - 1):
            nxt = _as_city(fn(cur, 0, set(U), D.copy()), U)
            tour.append(nxt)
            U.remove(nxt)
            cur = nxt
        t = np.asarray(tour)
        out.append(float(D[t, np.roll(t, -1)].sum()))
        if tours_out is not None:
            tours_out.append(tour)
    return out


def run_probes(code_obj, states, mats) -> list[int]:
    """One decision per probe state; ERR (-1) = exception or invalid return. Fresh exec per call; RNGs seeded
    with 930000+k before every call."""
    dec = []
    for k, (inst, cur, unv) in enumerate(states):
        try:
            fn = _fresh_fn(code_obj)
            np.random.seed((930000 + k) % (2 ** 32))
            random.seed(930000 + k)
            U = set(unv)
            dec.append(_as_city(fn(cur, 0, set(U), mats[inst].copy()), U))
        except Exception:  # noqa: BLE001 - any ordinary failure of the candidate is an ERR decision
            dec.append(ERR)
    return dec


def _send(wfd: int, obj) -> None:
    data = pickle.dumps(obj)
    os.write(wfd, struct.pack("<Q", len(data)))
    view, off = memoryview(data), 0
    while off < len(data):
        off += os.write(wfd, view[off:off + (1 << 20)])


def _classify(e: BaseException, phase: str) -> dict:
    if isinstance(e, CpuLimit):
        return {"ok": False, "cls": "probe_timeout" if phase == "probe" else "timeout", "reason": "cpu soft limit"}
    if isinstance(e, InvalidReturn):
        return {"ok": False, "cls": "invalid_return", "reason": str(e)[:300]}
    if isinstance(e, MemoryError):
        return {"ok": False, "cls": "runtime_error", "reason": f"MemoryError {e}"[:300]}
    if isinstance(e, ImportError):
        return {"ok": False, "cls": "import_violation", "reason": str(e)[:300]}
    if isinstance(e, RecursionError):
        return {"ok": False, "cls": "runtime_error", "reason": f"RecursionError {e}"[:300]}
    return {"ok": False, "cls": "runtime_error", "reason": f"{type(e).__name__}: {e}"[:300]}


def _child(wfd: int, code: str, jobs: list, cpu_soft: int, cpu_hard: int, extra_cpu: list) -> None:
    """jobs: list of (phase, mode, payload). Each phase's result is sent as its own frame; the first failure stops."""
    try:
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_soft, cpu_hard))
        resource.setrlimit(resource.RLIMIT_AS, (MEM_LIMIT, MEM_LIMIT))
        resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
        signal.signal(signal.SIGXCPU, _on_xcpu)
        try:
            os.nice(5)
        except OSError:
            pass
        os.chdir(_sbx_dir())
        code_obj = compile(code, "<candidate>", "exec")
    except BaseException as e:  # noqa: BLE001
        _send(wfd, {"phase": jobs[0][0], **_classify(e, jobs[0][0])})
        os._exit(0)
    for j, (phase, mode, payload) in enumerate(jobs):
        try:
            if j > 0:
                used = resource.getrusage(resource.RUSAGE_SELF)
                used_s = used.ru_utime + used.ru_stime
                soft = min(int(used_s) + 1 + extra_cpu[j], cpu_hard)
                resource.setrlimit(resource.RLIMIT_CPU, (soft, cpu_hard))
            t0 = time.process_time()
            if mode == "tours":
                mats, seeds = payload[0], payload[1]
                want = len(payload) > 2 and payload[2]
                tours: list = []
                res = {"ok": True, "lengths": run_tours(code_obj, mats, seeds, tours if want else None)}
                if want:
                    res["tours"] = tours
            elif mode == "probes":
                states, mats = payload
                res = {"ok": True, "decisions": run_probes(code_obj, states, mats)}
            else:
                raise ValueError(mode)
            res["cpu"] = time.process_time() - t0
            res["phase"] = phase
        except BaseException as e:  # noqa: BLE001 - candidate code may raise anything
            res = {"phase": phase, **_classify(e, phase)}
        try:
            _send(wfd, res)
        except BaseException:  # noqa: BLE001
            os._exit(0)
        if not res.get("ok"):
            break
    os._exit(0)


def fork_eval(code: str, jobs: list, cpu_limits: list[int], cpu_hard: int | None = None) -> list[dict]:
    """Fork one child that runs `code` over `jobs` (phase, mode, payload) in order.

    cpu_limits[j] is the CPU budget of phase j (the soft limit is raised before every later phase);
    the parent's wall limit for phase j is WALL_FACTOR x cpu_limits[j]. Returns one dict per phase reached.
    """
    cpu_hard = cpu_hard or (sum(cpu_limits) + 2)
    _sbx_dir()
    rfd, wfd = os.pipe()
    pid = os.fork()
    if pid == 0:
        os.close(rfd)
        try:
            _child(wfd, code, jobs, cpu_limits[0], cpu_hard, cpu_limits)
        finally:
            os._exit(0)
    os.close(wfd)
    results: list[dict] = []
    buf = b""
    phase_idx = 0
    t_phase = time.time()
    deadline = t_phase + WALL_FACTOR * cpu_limits[0] + 2
    killed = False
    eof = False
    while not eof and phase_idx < len(jobs):
        left = deadline - time.time()
        if left <= 0:
            os.kill(pid, signal.SIGKILL)
            killed = True
            break
        r, _, _ = select.select([rfd], [], [], min(left, 1.0))
        if not r:
            continue
        b = os.read(rfd, 1 << 20)
        if not b:
            eof = True
        buf += b
        while len(buf) >= 8:
            (ln,) = struct.unpack("<Q", buf[:8])
            if len(buf) < 8 + ln:
                break
            res = pickle.loads(buf[8:8 + ln])
            buf = buf[8 + ln:]
            res["wall"] = time.time() - t_phase
            results.append(res)
            phase_idx += 1
            t_phase = time.time()
            if phase_idx < len(jobs):
                deadline = t_phase + WALL_FACTOR * cpu_limits[phase_idx] + 2
            if not res.get("ok"):
                phase_idx = len(jobs)
    os.close(rfd)
    _, status = os.waitpid(pid, 0)
    if len(results) < len(jobs) and (not results or results[-1].get("ok")):
        phase = jobs[len(results)][0]
        tcls = "probe_timeout" if phase == "probe" else "timeout"
        if killed:
            results.append({"ok": False, "cls": tcls, "reason": "wall limit", "phase": phase})
        elif os.WIFSIGNALED(status) and os.WTERMSIG(status) in (signal.SIGXCPU, signal.SIGKILL):
            results.append({"ok": False, "cls": tcls, "reason": f"cpu limit (signal {os.WTERMSIG(status)})",
                            "phase": phase})
        else:
            sig = os.WTERMSIG(status) if os.WIFSIGNALED(status) else None
            results.append({"ok": False, "cls": "runtime_error", "reason": f"child died (signal {sig})",
                            "phase": phase})
    return results


# ------------------------------------------------------------------ evaluator worker (spawned process)
_W: dict = {}


def worker_init(sets_payload: dict) -> None:
    """sets_payload: {'selection': (mats, seeds), 'heldout': ..., 'probe_states': [...], 'probe_mats': [...]}.

    Matrices stay writable: every candidate call receives its own D.copy(), so in-place writes cannot leak.
    """
    os.environ["OMP_NUM_THREADS"] = "1"
    _W.update(sets_payload)
    _sbx_dir()


def evaluate_program(raw_program: str, with_probes: bool = True) -> dict:
    """Static check + SELECTION (+ PROBES in the same child). Returns a dict with label, lengths, decisions."""
    try:
        code = static_check(raw_program)
    except StaticReject as e:
        return {"label": e.cls, "reason": e.reason, "lengths": None, "decisions": None, "probe_label": None,
                "cpu_sel": 0.0, "cpu_probe": 0.0, "wall": 0.0}
    jobs = [("selection", "tours", _W["selection"])]
    limits = [SEL_CPU]
    if with_probes:
        jobs.append(("probe", "probes", (_W["probe_states"], _W["probe_mats"])))
        limits.append(PROBE_CPU)
    t0 = time.time()
    res = fork_eval(code, jobs, limits, cpu_hard=HARD_CPU if with_probes else SEL_CPU + 2)
    out = {"label": None, "reason": None, "lengths": None, "decisions": None, "probe_label": None,
           "cpu_sel": None, "cpu_probe": None, "wall": time.time() - t0}
    r0 = res[0]
    if not r0.get("ok"):
        out.update(label=r0["cls"], reason=r0.get("reason"), cpu_sel=r0.get("cpu"))
        return out
    out.update(label="valid", lengths=r0["lengths"], cpu_sel=r0.get("cpu"))
    if with_probes:
        r1 = res[1] if len(res) > 1 else {"ok": False, "cls": "probe_timeout", "reason": "missing"}
        if r1.get("ok"):
            dec = r1["decisions"]
            n_err = sum(1 for d in dec if d == ERR)
            out.update(decisions=dec, cpu_probe=r1.get("cpu"), n_err=n_err,
                       probe_label="probe_valid" if n_err <= PROBE_ERR_MAX * len(dec) else "probe_err")
        else:
            out.update(probe_label=r1.get("cls", "probe_error"), reason=r1.get("reason"))
    return out


def evaluate_set(raw_program: str, set_name: str, cpu_limit: int = SET_CPU) -> dict:
    """Tours on a held-out set (HELDOUT / EXT / TSPLIB) in one child with `cpu_limit` seconds of CPU."""
    try:
        code = static_check(raw_program)
    except StaticReject as e:
        return {"label": e.cls, "reason": e.reason, "lengths": None}
    res = fork_eval(code, [(set_name, "tours", _W[set_name])], [cpu_limit])[0]
    if res.get("ok"):
        return {"label": "valid", "lengths": res["lengths"], "tours": res.get("tours"), "cpu": res.get("cpu"),
                "wall": res.get("wall")}
    return {"label": res["cls"], "reason": res.get("reason"), "lengths": None}


def probe_program(raw_program: str, cpu_limit: int = PROBE_CPU) -> dict:
    try:
        code = static_check(raw_program)
    except StaticReject as e:
        return {"label": e.cls, "decisions": None}
    res = fork_eval(code, [("probe", "probes", (_W["probe_states"], _W["probe_mats"]))], [cpu_limit])[0]
    if res.get("ok"):
        return {"label": "ok", "decisions": res["decisions"], "cpu": res.get("cpu")}
    return {"label": res["cls"], "reason": res.get("reason"), "decisions": None}


# ------------------------------------------------------------------ generic fork + rlimit check (harness test)
def _pycheck_child(wfd: int, code: str, cpu_limit: int) -> None:
    try:
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_limit, cpu_limit + 1))
        resource.setrlimit(resource.RLIMIT_AS, (MEM_LIMIT, MEM_LIMIT))
        resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
        os.chdir(_sbx_dir())
        ns = {"__name__": "candidate"}
        exec(compile(code, "<check>", "exec"), ns)
        res = {"ok": True}
    except BaseException as e:  # noqa: BLE001
        res = {"ok": False, "cls": type(e).__name__, "reason": str(e)[:200]}
    try:
        _send(wfd, res)
    except BaseException:  # noqa: BLE001
        pass
    os._exit(0)


def fork_pycheck(code: str, cpu_limit: int = 10) -> dict:
    """Run arbitrary trusted test code (a HumanEval+ solution plus its check) through the same fork+rlimit path."""
    _sbx_dir()
    rfd, wfd = os.pipe()
    pid = os.fork()
    if pid == 0:
        os.close(rfd)
        _pycheck_child(wfd, code, cpu_limit)
        os._exit(0)
    os.close(wfd)
    buf, deadline = b"", time.time() + WALL_FACTOR * cpu_limit + 2
    while True:
        left = deadline - time.time()
        if left <= 0:
            os.kill(pid, signal.SIGKILL)
            break
        r, _, _ = select.select([rfd], [], [], min(left, 1.0))
        if r:
            b = os.read(rfd, 1 << 20)
            if not b:
                break
            buf += b
    os.close(rfd)
    os.waitpid(pid, 0)
    if len(buf) >= 8:
        (ln,) = struct.unpack("<Q", buf[:8])
        return pickle.loads(buf[8:8 + ln])
    return {"ok": False, "cls": "timeout_or_killed", "reason": "no result"}


def rename_target(code: str, version: int) -> str:
    return re.sub(rf"\b{FUNC}_v{version}\b", FUNC, code)
