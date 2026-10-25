#!/usr/bin/env python3
"""Subprocess sandbox for LLM-written priority programs: AST screen, restricted exec, CPU-time limits, persistent
workers (spawn) each capped by RLIMIT_AS, a parent watchdog that kills and respawns hung workers.

Iteration-10 changes against the BP9 copy (inputs/bp9/src/sandbox.py):
- probe sets are data/probes/P10.json (and P10r.json after a gate revision), loaded lazily, in place of P1/P2;
- HARNESS SEEDING: before probe state i under harness seed s, np.random.seed((1000003*s + i) mod 2^32); the worker
  patches np.random.default_rng, np.random.PCG64 and np.random.RandomState so that a None seed becomes that same
  value; the program is re-compiled for every harness seed with the patch active at compile time (seed value of i=0);
- during packing, np.random.seed(instance index) (and the same patch value) is set before each instance;
- per-set CPU limits (task['limits']) and a 60 s CPU limit per pass over the probe set;
- decision = int(arr[argmax(priority(item, arr.copy()))]) (remaining capacity of the chosen bin, so ties between
  equal-capacity bins are canonicalised); 65535 on any per-state error (counts as a disagreement).
"""
from __future__ import annotations

import __future__
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
# extra I/O layer (BP9, documented): numpy file/ctypes entry points
FORBIDDEN_ATTRS = {"save", "savez", "savez_compressed", "savetxt", "load", "loadtxt", "fromfile", "tofile", "memmap",
                   "genfromtxt", "fromregex", "ctypeslib", "ctypes", "DataSource", "f2py", "distutils", "testing"}
ERR_CODE = 65535
ERROR_TYPES = ("ok", "syntax", "forbidden", "runtime", "shape", "timeout", "memory")
SEED_MULT = 1000003
PROBE_CPU_LIMIT_S = 60.0


class Forbidden(Exception):
    pass


class CpuTimeout(Exception):
    pass


def screen(tree: ast.AST) -> None:
    """Reject imports other than numpy/math, forbidden names and any dunder attribute or name."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                parts = a.name.split(".")
                if parts[0] not in ALLOWED_MODULES or any(p in FORBIDDEN_ATTRS or p.startswith("__") for p in parts):
                    raise Forbidden(f"import {a.name}")
        elif isinstance(node, ast.ImportFrom):
            parts = (node.module or "").split(".")
            if parts[0] not in ALLOWED_MODULES or node.level or any(p in FORBIDDEN_ATTRS for p in parts):
                raise Forbidden(f"from {node.module} import")
            for a in node.names:
                if a.name in FORBIDDEN_ATTRS or a.name in FORBIDDEN_NAMES or a.name.startswith("__"):
                    raise Forbidden(f"from {node.module} import {a.name}")
        elif isinstance(node, ast.Name):
            if node.id in FORBIDDEN_NAMES or (node.id.startswith("__") and node.id.endswith("__")):
                raise Forbidden(f"name {node.id}")
        elif isinstance(node, ast.Attribute):
            if node.attr.startswith("__") or node.attr in FORBIDDEN_ATTRS:
                raise Forbidden(f"attribute {node.attr}")


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
         "RuntimeError", "StopIteration", "AssertionError", "NotImplementedError", "True", "False", "None",
         "object", "property", "staticmethod", "classmethod", "super", "type", "callable", "repr", "format", "ord",
         "chr", "hex", "bin", "oct", "id"]


def safe_builtins() -> dict:
    import builtins
    d = {k: getattr(builtins, k) for k in _SAFE if hasattr(builtins, k)}
    d["print"] = _noop
    d["__import__"] = _restricted_import
    d["__build_class__"] = builtins.__build_class__  # class definitions (helper classes in LLM programs)
    return d


def normalise_key(code: str) -> str | None:
    """sha256 of ast.dump of the program with docstrings removed (comments are dropped by ast)."""
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError):
        return None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.body:
            b0 = node.body[0]
            if isinstance(b0, ast.Expr) and isinstance(getattr(b0, "value", None), ast.Constant) \
                    and isinstance(b0.value.value, str):
                node.body = node.body[1:] or [ast.Pass()]
    return hashlib.sha256(ast.dump(tree, annotate_fields=False, include_attributes=False).encode()).hexdigest()


# ------------------------------------------------------------------------------------------------ RNG patch
_CUR_SEED = [0]
_ORIG = {"default_rng": np.random.default_rng, "PCG64": np.random.PCG64, "RandomState": np.random.RandomState}


def _p_default_rng(seed=None, *a, **k):
    return _ORIG["default_rng"](_CUR_SEED[0] if seed is None else seed, *a, **k)


class _PatchedPCG64(_ORIG["PCG64"]):
    """PCG64 whose None seed becomes the current harness value (a type, so numpy's isinstance checks still work)."""

    def __init__(self, seed=None):
        super().__init__(_CUR_SEED[0] if seed is None else seed)


class _PatchedRandomState(_ORIG["RandomState"]):
    def __init__(self, seed=None):
        super().__init__(_CUR_SEED[0] if seed is None else seed)


def install_rng_patch() -> None:
    np.random.default_rng = _p_default_rng
    np.random.PCG64 = _PatchedPCG64
    np.random.RandomState = _PatchedRandomState


def harness_seed(value: int) -> None:
    """Seed numpy's global RandomState and the None-seed patch with the same value."""
    v = int(value) % (2 ** 32)
    _CUR_SEED[0] = v
    np.random.seed(v)


def state_seed(s: int, i: int) -> int:
    return (SEED_MULT * int(s) + int(i)) % (2 ** 32)


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
    ns = {"np": np, "math": math, "__builtins__": safe_builtins(), "__name__": "program"}
    try:
        # annotations are never evaluated (PEP 563 flag), so a dropped 'typing' import cannot break a definition
        exec(compile(tree, "<program>", "exec", flags=__future__.annotations.compiler_flag, dont_inherit=True),
             ns)  # noqa: S102 - screened, restricted namespace, rlimited worker
    except SyntaxError as e:
        return None, "syntax", repr(e)[:300]
    except MemoryError:
        return None, "memory", "MemoryError at definition"
    except CpuTimeout:
        raise
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
    from bp import ShapeError
    if isinstance(e, CpuTimeout):
        return "timeout"
    if isinstance(e, MemoryError):
        return "memory"
    if isinstance(e, ShapeError):
        return "shape"
    return "runtime"


def _probe_decisions(fn, states: list[tuple[int, np.ndarray]], seed: int | None = None) -> np.ndarray:
    """Decision vector of fn on the probe states; with `seed`, harness seeding before every state."""
    out = np.full(len(states), ERR_CODE, dtype=np.uint16)
    for i, (item, arr) in enumerate(states):
        if seed is not None:
            harness_seed(state_seed(seed, i))
        try:
            p = np.asarray(fn(item, arr.copy()))
            if p.ndim != 1 or p.shape[0] != arr.shape[0]:
                continue
            out[i] = int(arr[int(np.argmax(p))])
        except CpuTimeout:
            raise
        except MemoryError:
            raise
        except Exception:  # noqa: BLE001 - per-state errors are recorded as ERR
            continue
    return out


def probe_with_seed(code: str, states: list[tuple[int, np.ndarray]], seed: int,
                    cpu_limit: float | None = None) -> tuple[np.ndarray | None, str]:
    """Compile `code` afresh under harness seed `seed` (patch active at compile time) and probe every state.
    Returns (decisions or None, error message). Used in-worker and, for trusted code, in-process."""
    import signal
    harness_seed(state_seed(seed, 0))
    use_timer = cpu_limit is not None and threading.current_thread() is threading.main_thread()
    try:
        if use_timer:
            signal.setitimer(signal.ITIMER_PROF, float(cpu_limit))
        fn, et, msg = compile_program(code)
        if fn is None:
            return None, f"{et}: {msg}"
        dec = _probe_decisions(fn, states, seed)
        return dec, ""
    except CpuTimeout:
        return None, "timeout"
    except MemoryError:
        return None, "memory"
    finally:
        if use_timer:
            signal.setitimer(signal.ITIMER_PROF, 0)


def _load_probe(path: Path) -> list[tuple[int, np.ndarray]]:
    import json
    if not path.exists():
        return []
    d = json.loads(path.read_text())
    return [(int(it), np.array(list(of) + [int(cap)] * int(ne))) for it, of, ne, cap in d["states"]]


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
    install_rng_patch()
    import bp
    sets_cache: dict[str, list[dict]] = {}
    probe_cache: dict[str, list[tuple[int, np.ndarray]]] = {}

    def get_set(name):
        if name not in sets_cache:
            sets_cache[name] = bp.load_set(name)
        return sets_cache[name]

    def get_probe(name):
        if name not in probe_cache or not probe_cache[name]:
            probe_cache[name] = _load_probe(Path(root) / "data" / "probes" / f"{name}.json")
        return probe_cache[name]

    conn.send({"ready": True})
    while True:
        try:
            task = conn.recv()
        except (EOFError, KeyboardInterrupt):
            return
        if task is None:
            return
        res = {"tid": task["tid"], "error_type": "ok", "msg": "", "bins": {}, "eval_s": 0.0, "probes": {},
               "set_s": {}}
        t0 = time.process_time()
        harness_seed(0)
        try:
            signal.setitimer(signal.ITIMER_PROF, 20.0)
            fn, et, msg = compile_program(task["code"])
        except CpuTimeout:
            fn, et, msg = None, "timeout", "definition exceeded 20 s CPU"
        finally:
            signal.setitimer(signal.ITIMER_PROF, 0)
        if fn is None:
            res.update(error_type=et, msg=msg)
            conn.send(res)
            continue
        # ---- evaluation on instance sets (fail fast, in the given order); np.random.seed(instance index) first
        limits = task.get("limits", {})
        for set_name in task.get("sets", []):
            insts = get_set(set_name)
            try:
                signal.setitimer(signal.ITIMER_PROF, float(limits.get(set_name, task.get("limit", 30.0))))
                ts = time.process_time()
                out_b = []
                for idx, x in enumerate(insts):
                    harness_seed(idx)
                    out_b.append(bp.pack(x["items"], x["capacity"], fn))
                res["bins"][set_name] = out_b
                res["set_s"][set_name] = time.process_time() - ts
            except BaseException as e:  # noqa: BLE001 - classify every failure of untrusted code
                signal.setitimer(signal.ITIMER_PROF, 0)
                if isinstance(e, KeyboardInterrupt):
                    raise
                res["error_type"] = _classify(e)
                res["msg"] = f"{set_name}: {e!r}"[:300]
                res["failed_set"] = set_name
                if task.get("fail_fast", True):
                    break
            finally:
                signal.setitimer(signal.ITIMER_PROF, 0)
        res["eval_s"] = time.process_time() - t0
        # ---- behaviour probes under harness seeds (only for programs valid on all requested sets)
        if (res["error_type"] == "ok" or task.get("probe_even_if_failed")) and task.get("probes"):
            for pname in task["probes"]:
                states = get_probe(pname)
                for s in task.get("probe_seeds", [0, 1]):
                    key = f"{pname}@{s}"
                    tp = time.process_time()
                    dec, err = probe_with_seed(task["code"], states, s, cpu_limit=float(
                        task.get("probe_limit", PROBE_CPU_LIMIT_S)))
                    res.setdefault("probe_s", {})[key] = time.process_time() - tp
                    res["probes"][key] = dec.tobytes() if dec is not None else None
                    if err:
                        res.setdefault("probe_error", {})[key] = err[:200]
        conn.send(res)


# ------------------------------------------------------------------------------------------------ parent side
class EvalPool:
    """N persistent spawn workers; one manager thread per worker; submit() returns a concurrent Future."""

    def __init__(self, n_workers: int, root: Path, as_gib: float = 2.0, log=None):
        self.root, self.as_bytes, self.log = str(root), int(as_gib * 1024 ** 3), log
        self.ctx = mp.get_context("spawn")
        self.q: queue.PriorityQueue = queue.PriorityQueue()
        self.n_respawn = 0
        self._tid = 0
        self._lock = threading.Lock()
        self.threads = [threading.Thread(target=self._manage, args=(i,), daemon=True) for i in range(n_workers)]
        for t in self.threads:
            t.start()

    def _spawn(self):
        a, b = self.ctx.Pipe()
        p = self.ctx.Process(target=_worker_main, args=(b, self.root, self.as_bytes), daemon=True)
        p.start()
        b.close()
        if not a.poll(180):
            raise RuntimeError("worker did not become ready")
        a.recv()
        return p, a

    def _manage(self, idx: int) -> None:
        proc, conn = self._spawn()
        while True:
            _prio, _tid, item = self.q.get()
            if item is None:
                try:
                    conn.send(None)
                except (BrokenPipeError, OSError):
                    pass
                proc.join(5)
                return
            task, fut = item
            limits = task.get("limits", {})
            set_wall = sum(float(limits.get(s, task.get("limit", 30.0))) for s in task.get("sets", []))
            n_probe = len(task.get("probes", [])) * len(task.get("probe_seeds", [0, 1]))
            wall = 2.0 * (set_wall + 20.0 + float(task.get("probe_limit", PROBE_CPU_LIMIT_S)) * n_probe) + 20.0
            res = None
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
            if res.get("error_type") in ("timeout", "memory") and (not proc.is_alive() or "watchdog" in res["msg"]
                                                                  or "died" in res["msg"]):
                proc.kill()
                proc.join(5)
                self.n_respawn += 1
                proc, conn = self._spawn()
            fut.set_result(res)

    def submit(self, task: dict, priority: int = 5) -> Future:
        """Lower `priority` runs first (ties in submission order)."""
        with self._lock:
            self._tid += 1
            task = dict(task, tid=self._tid)
            tid = self._tid
        fut: Future = Future()
        self.q.put((priority, tid, (task, fut)))
        return fut

    def backlog(self) -> int:
        return self.q.qsize()

    def close(self) -> None:
        for i, _ in enumerate(self.threads):
            self.q.put((10 ** 9, 10 ** 12 + i, None))
        for t in self.threads:
            t.join(10)


def decode(b: bytes | None) -> np.ndarray | None:
    return None if b is None else np.frombuffer(b, dtype=np.uint16).copy()
