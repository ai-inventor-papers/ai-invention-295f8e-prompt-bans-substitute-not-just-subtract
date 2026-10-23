"""Parent side of the iteration-5 sandbox (bench harness.py logic): code extraction, hidden tests through
runner5.py and runtime traces through tracer5.py, each in a fresh `python3.12 -I -S` subprocess."""

from __future__ import annotations

import hashlib
import json
import os
import re
import resource
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

PY = os.environ.get("BENCH_SANDBOX_PYTHON") or shutil.which("python3.12") or sys.executable
COMMON = Path(__file__).resolve().parent
NEWBENCH = COMMON.parent
RUNNER = COMMON / "runner5.py"
TRACER = COMMON / "tracer5.py"
FENCE_RE = re.compile(r"```[ \t]*(?:python3?|py|Python)?[ \t]*\n(.*?)```", re.S)
OPEN_FENCE_RE = re.compile(r"```[ \t]*(?:python3?|py|Python)?[ \t]*\n(.*)$", re.S)
TOPLEVEL = re.compile(r"\n(?=[^\s#])")


def extract_code(text: str | None) -> str | None:
    """bench harness.extract_code: first ```python block; an unterminated final block is taken as-is."""
    if not text:
        return None
    m = FENCE_RE.search(text)
    if m:
        return m.group(1)
    m = OPEN_FENCE_RE.search(text)
    return m.group(1) if m else None


def extract_plainc(prompt: str, text: str) -> str:
    """Base plain completion: prompt (signature + docstring) + the body up to the first new top-level statement."""
    body = text
    m = TOPLEVEL.search("\n" + body)
    if m:
        body = ("\n" + body)[:m.start()][1:]
    return prompt + body


def code_sha(code: str | None) -> str:
    return hashlib.sha256((code or "").encode()).hexdigest()


def has_solve(code: str) -> bool:
    """True when the program parses and defines a function named solve (a 'def solve' inside a comment or a string
    does not count)."""
    import ast
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError, RecursionError):
        return False
    return any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == "solve" for n in ast.walk(tree))


def syntax_ok(code: str) -> bool:
    try:
        compile(code, "<c>", "exec")
        return True
    except (SyntaxError, ValueError):
        return False


def _limit_mem():
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024 ** 3, 2 * 1024 ** 3))


def unit_path(unit: str) -> Path:
    for d in NEWBENCH.iterdir():
        if d.is_dir() and d.name.startswith(unit + "_"):
            return d
    raise FileNotFoundError(unit)


def run_tests(code: str, unit: str, cases: list[dict], default_limit: float = 1.0) -> dict:
    payload = {"code": code, "task": unit, "checker_path": str(unit_path(unit) / "checker.py"),
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
    return {"passed": load_error is None and n_ok == len(cases), "n_cases": len(cases), "n_pass": n_ok,
            "statuses": statuses, "times": times, "first_fail": first_fail, "load_error": load_error}


def run_trace(code: str, probes: list[dict], timeout: float = 10.0) -> dict:
    payload = {"code": code, "probes": probes, "timeout": timeout}
    try:
        pr = subprocess.run([PY, "-I", "-S", str(TRACER)], input=json.dumps(payload), capture_output=True, text=True,
                            timeout=timeout * len(probes) + 20, preexec_fn=_limit_mem)
        lines = [json.loads(l) for l in pr.stdout.splitlines() if l.startswith("{")]
    except subprocess.TimeoutExpired:
        lines = [{"probe": None, "error": "tracer timeout"}]
    except json.JSONDecodeError:
        lines = [{"probe": None, "error": "tracer output unparseable"}]
    out: dict[str, Any] = {"probes": {}, "error": None}
    for l in lines:
        if l.get("probe") is None:
            out["error"] = l.get("error")
        else:
            out["probes"][l["probe"]] = l
    if not lines:
        out["error"] = "no tracer output"
    return out


def read_tests(p: Path) -> list[dict]:
    return [json.loads(l) for l in Path(p).read_text().splitlines() if l.strip()]
