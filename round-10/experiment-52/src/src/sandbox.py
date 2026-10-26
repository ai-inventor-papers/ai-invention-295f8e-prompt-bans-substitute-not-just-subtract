#!/usr/bin/env python3
"""Subprocess sandbox for LLM-written priority programs: AST screen, restricted exec, CPU-time limits, persistent
workers (spawn) each capped by RLIMIT_AS, a parent watchdog that kills and respawns hung workers.

Iteration-10 changes (diff in results/harness_changes.diff):
- ONE cumulative ITIMER_PROF budget across the selection sets (SEL-OR then SEL-W, fail fast) instead of one per set;
  held-out tasks keep a per-set budget (120 s);
- validity rule v10: strict packing (1-D, one score per valid bin, all scores finite) -> 'shape' / 'nonfinite';
  programs that fail ONLY by non-finite scores are re-scored once under FunSearch semantics (sensitivity);
- probe pass on P10 for valid programs only; a probe timeout marks the remaining states ERR (the vector is kept);
- `stochastic` AST flag and a parent-side result cache keyed by normalise_key (see EvalCache)."""
from __future__ import annotations

import ast
import hashlib
import math
import multiprocessing as mp
import os
import queue
import threading
import time
from concurrent.futures import Future
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import numpy as np  # noqa: E402

ALLOWED_MODULES = {"numpy", "math"}
FORBIDDEN_NAMES = {"open", "exec", "eval", "compile", "__import__", "globals", "locals", "vars", "getattr", "setattr",
                   "delattr", "input", "breakpoint"}
# extra I/O layer (not in the plan's list; documented): numpy file/ctypes entry points
FORBIDDEN_ATTRS = {"save", "savez", "savez_compressed", "savetxt", "load", "loadtxt", "fromfile", "tofile", "memmap",
                   "genfromtxt", "fromregex", "ctypeslib", "ctypes", "DataSource", "f2py", "distutils", "testing"}
ERR_CODE = 65535
ERROR_TYPES = ("ok", "syntax", "forbidden", "runtime", "shape", "nonfinite", "timeout", "memory")
SEL_SETS = ["SEL-OR", "SEL-W"]
SEL_BUDGET_S = 20.0
PROBE_BUDGET_S = 20.0
HELDOUT_BUDGET_S = 120.0
SEL_WATCHDOG_S = 90.0


class Forbidden(Exception):
    pass


class CpuTimeout(Exception):
    pass


def screen(tree: ast.AST) -> None:
    """Reject imports other than numpy/math, forbidden names and any dunder attribute or name."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name not in ALLOWED_MODULES:
                    raise Forbidden(f"import {a.name}")
        elif isinstance(node, ast.ImportFrom):
            if node.module not in ALLOWED_MODULES or node.level:
                raise Forbidden(f"from {node.module} import")
        elif isinstance(node, ast.Name):
            if node.id in FORBIDDEN_NAMES or (node.id.startswith("__") and node.id.endswith("__")):
                raise Forbidden(f"name {node.id}")
        elif isinstance(node, ast.Attribute):
            if node.attr.startswith("__") or node.attr in FORBIDDEN_ATTRS:
                raise Forbidden(f"attribute {node.attr}")


def is_stochastic(code: str) -> bool:
    """AST flag: the program references `random` (np.random.*, numpy.random, from numpy import random)."""
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError):
        return False
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == "random":
            return True
        if isinstance(node, ast.Name) and node.id == "random":
            return True
        if isinstance(node, ast.ImportFrom) and node.module and "random" in node.module:
            return True
        if isinstance(node, ast.alias) and "random" in node.name:
            return True
    return False


def _restricted_import(name, globals=None, locals=None, fromlist=(), level=0):  # noqa: A002
    if level or name.split(".")[0] not in ALLOWED_MODULES:
        raise ImportError(f"import of {name} not allowed")
    return __import__(name, globals, locals, fromlist, level)


def _noop(*_a, **_k):
    return None


_SAFE = ["abs", "all", "any", "bool", "dict", "divmod", "enumerate", "filter", "float", "frozenset", "int",
         "isinstance", "iter", "len", "list", "map", "max", "min", "next", "pow", "range", "reversed", "round", "set",
         "slice", "sorted", "str", "sum", "tuple", "zip", "complex", "hash", "Exception", "ValueError", "TypeError",
         "ZeroDivisionError", "IndexError", "KeyError", "ArithmeticError", "OverflowError", "FloatingPointError",
         "RuntimeError", "StopIteration", "AssertionError", "NotImplementedError", "True", "False", "None"]


def safe_builtins() -> dict:
    import builtins
    d = {k: getattr(builtins, k) for k in _SAFE if hasattr(builtins, k)}
    d["print"] = _noop
    d["__import__"] = _restricted_import
    return d


def normalise_key(code: str) -> str | None:
    """sha256 of ast.dump of the program with docstrings removed (comments are dropped by ast)."""
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError):
        return None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.body:
            b0 = node.body[0]
            if isinstance(b0, ast.Expr) and isinstance(getattr(b0, "value", None), ast.Constant) \
                    and isinstance(b0.value.value, str):
                node.body = node.body[1:] or [ast.Pass()]
    return hashlib.sha256(ast.dump(tree, annotate_fields=False, include_attributes=False).encode()).hexdigest()


def compile_program(code: str):
    """Return (priority function, error_type, message)."""
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError) as e:  # TabError/IndentationError are SyntaxError subclasses
        return None, "syntax", repr(e)[:300]
    try:
        screen(tree)
    except Forbidden as e:
        return None, "forbidden", str(e)[:300]
    ns = {"np": np, "math": math, "__builtins__": safe_builtins()}
    try:
        exec(compile(tree, "<program>", "exec"), ns)  # noqa: S102 - screened, restricted namespace, rlimited worker
    except SyntaxError as e:
        return None, "syntax", repr(e)[:300]
    except MemoryError:
        return None, "memory", "MemoryError at definition"
    except Exception as e:  # noqa: BLE001
        return None, "runtime", repr(e)[:300]
    fn = ns.get("priority")
    if not callable(fn):
        return None, "syntax", "no function named priority"
    return fn, "ok", ""


# ------------------------------------------------------------------------------------------------ worker side
def _on_sigprof(signum, frame):
    raise CpuTimeout("cpu time limit")


def _classify(e: BaseException) -> str:
    from bp import NonFiniteError, ShapeError
    if isinstance(e, CpuTimeout):
        return "timeout"
    if isinstance(e, MemoryError):
        return "memory"
    if isinstance(e, ShapeError):
        return "shape"
    if isinstance(e, NonFiniteError):
        return "nonfinite"
    return "runtime"


def probe_decisions(fn, states: list[tuple[int, np.ndarray]]) -> np.ndarray:
    """FunSearch argmax on each probe state (NaN -> first NaN index); the decision is the chosen bin's remaining
    capacity. ERR only on an exception, a wrong shape or a timeout (states not reached are ERR)."""
    out = np.full(len(states), ERR_CODE, dtype=np.uint16)
    try:
        for i, (item, arr) in enumerate(states):
            try:
                p = np.asarray(fn(item, arr.copy()))
                if p.ndim != 1 or p.shape[0] != arr.shape[0]:
                    continue
                out[i] = int(arr[int(np.argmax(p))])
            except (CpuTimeout, MemoryError):
                raise
            except Exception:  # noqa: BLE001 - per-state errors are recorded as ERR
                continue
    except CpuTimeout:
        raise _ProbeTimeout(out) from None
    return out


class _ProbeTimeout(Exception):
    def __init__(self, partial: np.ndarray):
        super().__init__("probe cpu time limit")
        self.partial = partial


def load_probe(path: Path) -> list[tuple[int, np.ndarray]]:
    import json
    if not path.exists():
        return []
    d = json.loads(path.read_text())
    return [(int(it), np.array(list(of) + [int(cap)] * int(ne))) for it, of, ne, cap in d["states"]]


def _run_sets(fn, task: dict, get_set, bp, strict: bool, res: dict, key: str) -> None:
    """Evaluate on task['sets'] in order. budget 'cumulative': one ITIMER_PROF for all sets; 'per_set': one each."""
    import signal
    limit = float(task["limit"])
    cumulative = task.get("budget", "cumulative") == "cumulative"
    nf = [0]
    res[key] = {}
    try:
        if cumulative:
            signal.setitimer(signal.ITIMER_PROF, limit)
        for set_name in task.get("sets", []):
            insts = get_set(set_name)
            try:
                if not cumulative:
                    signal.setitimer(signal.ITIMER_PROF, limit)
                ts = time.process_time()
                res[key][set_name] = [bp.pack(x["items"], x["capacity"], fn, strict=strict, nf_counter=nf)
                                      for x in insts]
                res.setdefault("set_s", {})[f"{key}:{set_name}"] = time.process_time() - ts
            finally:
                if not cumulative:
                    signal.setitimer(signal.ITIMER_PROF, 0)
    finally:
        signal.setitimer(signal.ITIMER_PROF, 0)
    if not strict:
        res["fs_nonfinite_calls"] = nf[0]


def _worker_main(conn, root: str, as_bytes: int) -> None:
    import resource
    import signal
    import sys
    import warnings
    sys.path.insert(0, str(Path(root) / "src"))
    resource.setrlimit(resource.RLIMIT_AS, (as_bytes, as_bytes))
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
    warnings.simplefilter("ignore")
    np.seterr(all="ignore")
    signal.signal(signal.SIGPROF, _on_sigprof)
    import bp
    sets_cache: dict[str, list[dict]] = {}

    def get_set(name):
        if name not in sets_cache:
            sets_cache[name] = bp.load_set(name)
        return sets_cache[name]

    probes = {"P10": load_probe(Path(root) / "data" / "probes" / "P10.json")}
    conn.send({"ready": True, "n_probe_states": len(probes["P10"])})
    while True:
        try:
            task = conn.recv()
        except (EOFError, KeyboardInterrupt):
            return
        if task is None:
            return
        res = {"tid": task["tid"], "error_type": "ok", "msg": "", "bins": {}, "eval_s": 0.0, "probes": {}}
        t0 = time.process_time()
        fn, et, msg = compile_program(task["code"])
        if fn is None:
            res.update(error_type=et, msg=msg)
            conn.send(res)
            continue
        strict = bool(task.get("strict", True))
        try:
            _run_sets(fn, task, get_set, bp, strict, res, "bins")
        except BaseException as e:  # noqa: BLE001 - classify every failure of untrusted code
            if isinstance(e, KeyboardInterrupt):
                raise
            res["error_type"] = _classify(e)
            res["msg"] = f"{e!r}"[:300]
            res["failed_set"] = next((s for s in task.get("sets", []) if s not in res["bins"]), None)
        res["eval_s"] = time.process_time() - t0
        # FunSearch-semantics re-score of programs whose ONLY failure is a non-finite score
        do_fs = res["error_type"] == "nonfinite" and task.get("fs_rescore", False)
        if do_fs:
            fsr: dict = {"bins": {}}
            try:
                _run_sets(fn, dict(task, limit=task["limit"]), get_set, bp, False, fsr, "bins")
                fsr["error_type"] = "ok"
            except BaseException as e:  # noqa: BLE001
                if isinstance(e, KeyboardInterrupt):
                    raise
                fsr["error_type"] = _classify(e)
                fsr["msg"] = f"{e!r}"[:200]
            res["fs"] = {"bins": fsr["bins"], "error_type": fsr["error_type"],
                         "nonfinite_calls": fsr.get("fs_nonfinite_calls")}
        # behaviour probes: valid programs (and FunSearch-valid non-finite-only programs, flagged)
        probe_ok = res["error_type"] == "ok" or (do_fs and res["fs"]["error_type"] == "ok")
        if probe_ok and task.get("probes"):
            for pname in task["probes"]:
                try:
                    signal.setitimer(signal.ITIMER_PROF, float(task.get("probe_limit", PROBE_BUDGET_S)))
                    res["probes"][pname] = probe_decisions(fn, probes[pname]).tobytes()
                except _ProbeTimeout as e:
                    res["probes"][pname] = e.partial.tobytes()
                    res["probe_error"] = f"{pname}: timeout"
                except BaseException as e:  # noqa: BLE001
                    if isinstance(e, KeyboardInterrupt):
                        raise
                    res["probes"][pname] = None
                    res["probe_error"] = f"{pname}: {e!r}"[:200]
                finally:
                    signal.setitimer(signal.ITIMER_PROF, 0)
        res["total_cpu_s"] = time.process_time() - t0
        conn.send(res)


# ------------------------------------------------------------------------------------------------ parent side
class EvalPool:
    """N persistent spawn workers; one manager thread per worker; submit() returns a concurrent Future."""

    def __init__(self, n_workers: int, root: Path, as_gib: float = 2.0, log=None):
        self.root, self.as_bytes, self.log = str(root), int(as_gib * 1024 ** 3), log
        self.ctx = mp.get_context("spawn")
        self.q: queue.Queue = queue.Queue()
        self.n_respawn = 0
        self._tid = 0
        self._busy = 0
        self._lock = threading.Lock()
        self.threads = [threading.Thread(target=self._manage, args=(i,), daemon=True) for i in range(n_workers)]
        for t in self.threads:
            t.start()

    def _spawn(self):
        a, b = self.ctx.Pipe()
        p = self.ctx.Process(target=_worker_main, args=(b, self.root, self.as_bytes), daemon=True)
        p.start()
        b.close()
        if not a.poll(120):
            raise RuntimeError("worker did not become ready")
        a.recv()
        return p, a

    @staticmethod
    def wall_limit(task: dict) -> float:
        if task.get("budget", "cumulative") == "cumulative":
            w = SEL_WATCHDOG_S
            if task.get("fs_rescore"):
                w += 45.0
            return w
        return 2.0 * (float(task.get("limit", HELDOUT_BUDGET_S)) * max(1, len(task.get("sets", [])))) + 30.0 + \
            float(task.get("probe_limit", PROBE_BUDGET_S)) * len(task.get("probes", []))

    def _manage(self, idx: int) -> None:
        proc, conn = self._spawn()
        while True:
            item = self.q.get()
            if item is None:
                try:
                    conn.send(None)
                except (BrokenPipeError, OSError):
                    pass
                proc.join(5)
                return
            task, fut = item
            with self._lock:
                self._busy += 1
            wall = self.wall_limit(task)
            res = None
            t_wall = time.time()
            try:
                conn.send(task)
                if conn.poll(wall):
                    res = conn.recv()
                else:
                    res = {"tid": task["tid"], "error_type": "timeout", "msg": f"watchdog wall {wall:.0f}s",
                           "bins": {}, "eval_s": wall, "probes": {}}
            except (EOFError, BrokenPipeError, OSError) as e:
                res = {"tid": task["tid"], "error_type": "memory", "msg": f"worker died: {e!r}"[:200], "bins": {},
                       "eval_s": 0.0, "probes": {}}
            res["wall_s"] = time.time() - t_wall
            if res.get("error_type") in ("timeout", "memory") and (not proc.is_alive() or "watchdog" in res["msg"]
                                                                  or "died" in res["msg"]):
                proc.kill()
                proc.join(5)
                self.n_respawn += 1
                proc, conn = self._spawn()
            with self._lock:
                self._busy -= 1
            fut.set_result(res)

    def submit(self, task: dict) -> Future:
        with self._lock:
            self._tid += 1
            task = dict(task, tid=self._tid)
        fut: Future = Future()
        self.q.put((task, fut))
        return fut

    def backlog(self) -> int:
        return self.q.qsize()

    def busy(self) -> int:
        return self._busy

    def close(self) -> None:
        for _ in self.threads:
            self.q.put(None)
        for t in self.threads:
            t.join(10)


def selection_task(code: str, probes: bool = True) -> dict:
    """The standard offspring evaluation: strict, cumulative 20 s CPU over SEL-OR then SEL-W, then the P10 pass."""
    return {"code": code, "sets": list(SEL_SETS), "budget": "cumulative", "limit": SEL_BUDGET_S, "strict": True,
            "fs_rescore": True, "probes": ["P10"] if probes else [], "probe_limit": PROBE_BUDGET_S}


def heldout_task(code: str, sets: list[str], strict: bool = True) -> dict:
    return {"code": code, "sets": list(sets), "budget": "per_set", "limit": HELDOUT_BUDGET_S, "strict": strict,
            "fs_rescore": False, "probes": []}


class EvalCache:
    """Parent-side result cache keyed by normalise_key(program), shared across arms and seeds. A duplicate that is
    still in flight attaches to the same future; a cached duplicate inherits the stored result."""

    def __init__(self, pool: EvalPool):
        self.pool = pool
        self.done: dict[str, dict] = {}
        self.inflight: dict[str, Future] = {}
        self.lock = threading.RLock()  # re-entrant: a done-callback may run in the submitting thread
        self.hits = 0

    def preload(self, key: str, res: dict) -> None:
        self.done[key] = res

    def submit(self, code: str) -> tuple[str | None, Future, bool]:
        """Return (key, future, cached?). Unparseable programs (key None) are evaluated without caching."""
        key = normalise_key(code)
        with self.lock:
            if key is not None and key in self.done:
                self.hits += 1
                f: Future = Future()
                f.set_result(self.done[key])
                return key, f, True
            if key is not None and key in self.inflight:
                self.hits += 1
                return key, self.inflight[key], True
            fut = self.pool.submit(selection_task(code))
            if key is not None:
                self.inflight[key] = fut

                def _done(f, k=key):
                    with self.lock:
                        self.done[k] = f.result()
                        self.inflight.pop(k, None)
                fut.add_done_callback(_done)
            return key, fut, False
