"""Parent side of the sandbox: code extraction and test execution in fresh `python3.12 -I -S` subprocesses."""

from __future__ import annotations

import hashlib
import json
import os
import re
import resource
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# sandbox interpreter: a plain CPython 3.12 (run with -I -S); BENCH_SANDBOX_PYTHON overrides
PY = os.environ.get("BENCH_SANDBOX_PYTHON") or shutil.which("python3.12") or sys.executable
COMMON = Path(__file__).resolve().parent
RUNNER = COMMON / "runner.py"
CHECKERS = COMMON / "checkers.py"
FENCE_RE = re.compile(r"```[ \t]*(?:python3?|py|Python)?[ \t]*\n(.*?)```", re.S)
OPEN_FENCE_RE = re.compile(r"```[ \t]*(?:python3?|py|Python)?[ \t]*\n(.*)$", re.S)


def extract_code(text: str | None) -> str | None:
    """First ```python block; an unterminated final block (truncated answer) is taken as-is."""
    if not text:
        return None
    m = FENCE_RE.search(text)
    if m:
        return m.group(1)
    m = OPEN_FENCE_RE.search(text)
    return m.group(1) if m else None


def code_sha(code: str | None) -> str:
    return hashlib.sha256((code or "").encode()).hexdigest()


def syntax_ok(code: str) -> bool:
    try:
        compile(code, "<c>", "exec")
        return True
    except (SyntaxError, ValueError):
        return False


def _limit_mem():
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))


def run_tests(code: str, task: str, cases: list[dict], default_limit: float = 1.0) -> dict:
    payload = {"code": code, "task": task, "checkers_path": str(CHECKERS),
               "cases": [{"kwargs_json": json.dumps(c["kwargs"]), "expected_json": json.dumps(c["expected"]),
                          "limit": float(c.get("limit", default_limit))} for c in cases]}
    total = sum(p["limit"] for p in payload["cases"]) + 20.0
    try:
        pr = subprocess.run([PY, "-I", "-S", str(RUNNER)], input=json.dumps(payload), capture_output=True, text=True,
                            timeout=total, preexec_fn=_limit_mem)
        lines = [json.loads(l) for l in pr.stdout.splitlines() if l.startswith("{")]
        err = pr.stderr[-300:]
    except subprocess.TimeoutExpired:
        lines, err = [], "harness timeout"
    statuses = ["not_run"] * len(cases)
    times = [None] * len(cases)
    load_error = None
    for r in lines:
        if r["i"] == -1:
            load_error = r["msg"]
            continue
        statuses[r["i"]] = r["status"]
        times[r["i"]] = r["t"]
    if not lines and not load_error:
        load_error = f"no output: {err}"
    n_ok = sum(1 for s in statuses if s == "ok")
    first_fail = next(({"i": i, "status": s, "case_id": cases[i]["case_id"]} for i, s in enumerate(statuses)
                       if s != "ok"), None)
    msgs = [r["msg"] for r in lines if r.get("msg")][:3]
    return {"passed": load_error is None and n_ok == len(cases), "n_cases": len(cases), "n_pass": n_ok,
            "statuses": statuses, "times": times, "first_fail": first_fail, "load_error": load_error, "msgs": msgs}


def run_many(items: list[tuple[str, str]], task: str, cases: list[dict], workers: int = 5) -> dict[str, dict]:
    """items: [(id, code)] -> {id: result}."""
    out = {}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(run_tests, code, task, cases): pid for pid, code in items}
        for f, pid in futs.items():
            out[pid] = f.result()
    return out
