#!/usr/bin/env python3
"""Subprocess sandbox for LLM-written priority programs: AST screen, restricted exec, CPU-time limits, persistent
workers (spawn) each capped by RLIMIT_AS, a parent watchdog that kills and respawns hung workers."""
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
ERROR_TYPES = ("ok", "syntax", "forbidden", "runtime", "shape", "timeout", "memory")


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
    from bp import ShapeError
    if isinstance(e, CpuTimeout):
        return "timeout"
    if isinstance(e, MemoryError):
        return "memory"
    if isinstance(e, ShapeError):
        return "shape"
    return "runtime"


def _probe_decisions(fn, states: list[tuple[int, np.ndarray]]) -> np.ndarray:
    out = np.full(len(states), ERR_CODE, dtype=np.uint16)
    for i, (item, arr) in enumerate(states):
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
    import bp
    sets_cache: dict[str, list[dict]] = {}

    def get_set(name):
        if name not in sets_cache:
            sets_cache[name] = bp.load_set(name)
        return sets_cache[name]

    probes = {"P1": _load_probe(Path(root) / "data" / "probes" / "P1.json"),
              "P2": _load_probe(Path(root) / "data" / "probes" / "P2.json")}
    conn.send({"ready": True})
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
        # ---- evaluation on instance sets (fail fast, in the given order)
        for set_name in task.get("sets", []):
            insts = get_set(set_name)
            try:
                signal.setitimer(signal.ITIMER_PROF, float(task["limit"]))
                ts = time.process_time()
                res["bins"][set_name] = [bp.pack(x["items"], x["capacity"], fn) for x in insts]
                res.setdefault("set_s", {})[set_name] = time.process_time() - ts
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
        # ---- behaviour probes (only for programs valid on all requested sets)
        if res["error_type"] == "ok" and task.get("probes"):
            for pname in task["probes"]:
                try:
                    signal.setitimer(signal.ITIMER_PROF, float(task.get("probe_limit", 20.0)))
                    res["probes"][pname] = _probe_decisions(fn, probes[pname]).tobytes()
                except BaseException as e:  # noqa: BLE001
                    if isinstance(e, KeyboardInterrupt):
                        raise
                    res["probes"][pname] = None
                    res["probe_error"] = f"{pname}: {e!r}"[:200]
                finally:
                    signal.setitimer(signal.ITIMER_PROF, 0)
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
            wall = 2.0 * (float(task.get("limit", 10)) * max(1, len(task.get("sets", []))) +
                          float(task.get("probe_limit", 20)) * len(task.get("probes", []))) + 10.0
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

    def submit(self, task: dict) -> Future:
        with self._lock:
            self._tid += 1
            task = dict(task, tid=self._tid)
        fut: Future = Future()
        self.q.put((task, fut))
        return fut

    def backlog(self) -> int:
        return self.q.qsize()

    def close(self) -> None:
        for _ in self.threads:
            self.q.put(None)
        for t in self.threads:
            t.join(10)
