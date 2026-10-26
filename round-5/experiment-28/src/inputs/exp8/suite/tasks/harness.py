#!/usr/bin/env python3
"""Parent-side harness: runs candidate programs in fresh stdlib-only subprocesses (hidden tests + runtime probes).

The candidate interpreter is the system CPython 3.12 run with -I -S (isolated, no site-packages), which also
enforces the task's 'standard library only' rule. Each program gets its own process for the tests and another
for the probes, so tracer overhead never affects the correctness time limits.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable

from loguru import logger

ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = ROOT / "tasks"
SANDBOX_TESTS = TASKS_DIR / "sandbox_tests.py"
TRACER = ROOT / "labeller" / "tracer.py"

def _sandbox_python() -> str:
    """Stdlib-only CPython 3.12 used for candidates: $SANDBOX_PYTHON, else the system CPython 3.12 this run used,
    else python3.12 on PATH, else the current interpreter (always run with -I -S, so site-packages stay hidden)."""
    env = os.environ.get("SANDBOX_PYTHON")
    if env:
        return env
    for cand in ("/usr/local/bin/python3.12", "/usr/bin/python3.12"):
        if Path(cand).exists():
            return cand
    return shutil.which("python3.12") or sys.executable


SYS_PY = _sandbox_python()


def limits_path(task: str) -> Path:
    return TASKS_DIR / ("t1_grid" if task == "t1" else "t2_wsp") / "limits.json"


_LIMITS: dict[str, dict[str, float]] = {}


def load_limits(task: str) -> dict[str, float]:
    if task not in _LIMITS:
        p = limits_path(task)
        _LIMITS[task] = json.loads(p.read_text())["limits"] if p.exists() else {}
    return _LIMITS[task]


def _run(script: Path, job: dict[str, Any], timeout: float) -> dict[str, Any]:
    try:
        proc = subprocess.run([SYS_PY, "-I", "-S", str(script)], input=json.dumps(job), capture_output=True,
                              text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"error": "harness_timeout"}
    lines = [ln for ln in proc.stdout.strip().splitlines() if ln.startswith("{")]
    if not lines:
        return {"error": "crash", "returncode": proc.returncode, "stderr": proc.stderr[-300:]}
    try:
        return json.loads(lines[-1])
    except json.JSONDecodeError:
        return {"error": "bad_output", "stderr": proc.stderr[-300:]}


def run_tests(task: str, code: str, limits: dict[str, float] | None = None, max_case_s: float = 60.0) -> dict[str, Any]:
    limits = load_limits(task) if limits is None else limits
    total = sum(limits.values()) if limits else max_case_s * 80
    job = {"task": task, "code": code, "tasks_dir": str(TASKS_DIR), "limits": limits, "max_case_s": max_case_s}
    res = _run(SANDBOX_TESTS, job, timeout=total + 30.0)
    res.setdefault("passed", False)
    return res


def run_probes(task: str, code: str, probe_timeout_s: float = 4.0) -> dict[str, Any]:
    job = {"task": task, "code": code, "tasks_dir": str(TASKS_DIR), "probe_timeout_s": probe_timeout_s}
    return _run(TRACER, job, timeout=probe_timeout_s * 8 + 30.0)


def evaluate_program(task: str, code: str) -> dict[str, Any]:
    return {"tests": run_tests(task, code), "probes": run_probes(task, code)}


def parallel_map(fn: Callable[[Any], Any], items: list[Any], workers: int = 10, desc: str = "") -> list[Any]:
    out: list[Any] = [None] * len(items)
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(fn, it): i for i, it in enumerate(items)}
        for f in as_completed(futs):
            i = futs[f]
            try:
                out[i] = f.result()
            except Exception as e:  # noqa: BLE001 - one bad program must not stop the batch
                logger.error(f"{desc} item {i} failed: {e}")
                out[i] = {"error": f"harness_exception: {type(e).__name__}"}
            done += 1
            if done % 100 == 0 or done == len(items):
                logger.info(f"{desc}: {done}/{len(items)}")
    return out


if __name__ == "__main__":
    print(SYS_PY, sys.version)
