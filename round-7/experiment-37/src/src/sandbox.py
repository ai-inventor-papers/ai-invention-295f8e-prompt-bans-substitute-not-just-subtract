#!/usr/bin/env python3
"""Parent side of the evaluator: AST pre-screen, code extraction, and the 3-stage cascade in a fresh subprocess.

STAGE 1: 8 quick cases (6 smallest + 2 at maximum size of the hidden suite). STAGE 2: the rest of the hidden suite.
STAGE 3: 10 randomised stress inputs at maximum size (seed fixed per task, never shown to the mutator), checked
against the fastest reference's output. CORRECT = all three stages pass.
"""

from __future__ import annotations

import ast
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
from pathlib import Path
from typing import Any

SANDBOX_PY = os.environ.get("SANDBOX_PYTHON") or ("/usr/local/bin/python3.12" if Path("/usr/local/bin/python3.12").exists()
                                                  else (shutil.which("python3.12") or sys.executable))
RUNNER = Path(__file__).resolve().parent / "sandbox_runner.py"
MEM_BYTES = 2 * 1024 ** 3

BANNED_MODULES = {"os", "sys", "subprocess", "socket", "urllib", "requests", "http", "shutil", "pathlib", "ctypes",
                  "multiprocessing", "importlib", "inspect", "gc", "builtins", "signal", "resource"}
SYS_ALLOWED_ATTRS = {"setrecursionlimit", "getrecursionlimit", "maxsize", "float_info", "int_info", "maxunicode"}
BANNED_CALLS = {"open", "eval", "exec", "compile", "__import__", "globals", "breakpoint", "input", "vars", "locals"}
BANNED_NAMES = {"__file__", "__builtins__", "__loader__", "__spec__"}
MAX_LITERAL = 64

FENCE_RE = re.compile(r"```[ \t]*(?:python3?|py|Python)?[ \t]*\n(.*?)```", re.S)
OPEN_FENCE_RE = re.compile(r"```[ \t]*(?:python3?|py|Python)[ \t]*\n(.*)$", re.S)


def extract_code(text: str | None) -> str | None:
    """First ```python block; a block cut by the stop string (no closing fence) is taken as-is."""
    if not text:
        return None
    m = FENCE_RE.search(text)
    if m:
        return m.group(1)
    m = OPEN_FENCE_RE.search(text)
    return m.group(1) if m else None


def prescreen(code: str | None) -> tuple[bool, list[str]]:
    """Return (ok, reasons). Any banned import/call/name or a >64-element literal (possible lookup table) => invalid."""
    if not code or not code.strip():
        return False, ["no_code"]
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError, RecursionError, MemoryError):
        return False, ["syntax_error"]
    reasons: list[str] = []
    sys_imported = False
    has_solve = False
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == "solve":
            has_solve = True
        if isinstance(n, ast.Import):
            for a in n.names:
                root = a.name.split(".")[0]
                if root == "sys":
                    sys_imported = True
                elif root in BANNED_MODULES:
                    reasons.append(f"import:{root}")
        elif isinstance(n, ast.ImportFrom):
            root = (n.module or "").split(".")[0]
            if root == "sys":
                bad = [a.name for a in n.names if a.name not in SYS_ALLOWED_ATTRS]
                if bad:
                    reasons.append(f"from_sys_import:{','.join(bad)}")
            elif root in BANNED_MODULES:
                reasons.append(f"import:{root}")
        elif isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Name) and f.id in BANNED_CALLS:
                reasons.append(f"call:{f.id}")
        elif isinstance(n, ast.Name) and n.id in BANNED_NAMES:
            reasons.append(f"name:{n.id}")
        elif isinstance(n, ast.Attribute):
            if isinstance(n.value, ast.Name) and n.value.id == "sys" and n.attr not in SYS_ALLOWED_ATTRS:
                reasons.append(f"sys.{n.attr}")
            if n.attr.startswith("__") and n.attr.endswith("__") and n.attr not in ("__init__", "__lt__", "__eq__",
                                                                                   "__le__", "__gt__", "__ge__",
                                                                                   "__len__", "__repr__", "__hash__"):
                reasons.append(f"dunder:{n.attr}")
        elif isinstance(n, (ast.List, ast.Set, ast.Tuple)) and len(n.elts) > MAX_LITERAL:
            reasons.append("big_literal")
        elif isinstance(n, ast.Dict) and len(n.keys) > MAX_LITERAL:
            reasons.append("big_literal")
    if not has_solve:
        reasons.append("no_solve")
    _ = sys_imported
    return (not reasons), sorted(set(reasons))


def _run_child(job: dict[str, Any], timeout: float) -> list[dict[str, Any]]:
    try:
        pr = subprocess.run([SANDBOX_PY, "-I", "-S", str(RUNNER)], input=json.dumps(job), capture_output=True,
                            text=True, timeout=timeout, cwd=str(RUNNER.parent))
        out = pr.stdout
        rc = pr.returncode
    except subprocess.TimeoutExpired as e:
        out = e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
        rc = "harness_timeout"
    lines = []
    for ln in out.splitlines():
        if ln.startswith("{"):
            try:
                lines.append(json.loads(ln))
            except json.JSONDecodeError:
                pass
    if not any("done" in x or "stop" in x or "load_error" in x for x in lines):
        lines.append({"killed": str(rc)})
    return lines


def run_stages(task: str, code: str, stages: list[list[dict[str, Any]]], load_limit: float = 5.0) -> dict[str, Any]:
    """Run the candidate through the given stages (lists of {id, kw, exp, lim}); stop at the first failure."""
    total = sum(float(c["lim"]) for st in stages for c in st)
    job = {"code": code, "task": task, "stages": stages, "cpu_s": total + 5.0, "mem_bytes": MEM_BYTES,
           "load_limit": load_limit}
    lines = _run_child(job, timeout=total + load_limit + 15.0)
    res: dict[str, Any] = {"load_error": None, "killed": None, "times": [[None] * len(st) for st in stages],
                           "status": [["not_run"] * len(st) for st in stages], "stage_failed": None, "first_fail": None}
    for x in lines:
        if "load_error" in x:
            res["load_error"] = x["load_error"]
        elif "killed" in x:
            res["killed"] = x["killed"]
        elif "s" in x and "i" in x:
            res["status"][x["s"]][x["i"]] = x["st"]
            res["times"][x["s"]][x["i"]] = x["t"]
    for s, st in enumerate(res["status"]):
        for i, v in enumerate(st):
            if v != "ok":
                if res["stage_failed"] is None:
                    res["stage_failed"] = s
                    res["first_fail"] = {"stage": s, "i": i, "status": v if v != "not_run" else
                                         ("killed" if res["killed"] else "load_error" if res["load_error"] else v),
                                         "case_id": stages[s][i].get("id")}
                break
        if res["stage_failed"] is not None:
            break
    res["passed_all"] = res["stage_failed"] is None and res["load_error"] is None
    return res


def evaluate(task_obj: dict[str, Any], code: str | None) -> dict[str, Any]:
    """Full evaluator record of one program: pre-screen + stages 1-3 + runtime summary."""
    ok, reasons = prescreen(code)
    rec: dict[str, Any] = {"valid": ok, "prescreen": reasons, "stage1": False, "stage2": False, "stress_pass": False,
                           "correct": False, "first_fail": None, "median_case_ms": None, "runtime_ratio": None,
                           "load_error": None}
    if not ok:
        return rec
    st = task_obj["stages"]
    r = run_stages(task_obj["task"], code, [st["quick"], st["rest"], st["stress"]])
    rec["load_error"] = r["load_error"]
    rec["first_fail"] = r["first_fail"]
    sf = r["stage_failed"]
    rec["stage1"] = sf is None or sf > 0
    rec["stage2"] = sf is None or sf > 1
    rec["stress_pass"] = sf is None
    rec["correct"] = bool(r["passed_all"])
    hidden_t = [t for t in r["times"][0] + r["times"][1] if t is not None]
    if hidden_t:
        rec["median_case_ms"] = round(1000 * statistics.median(hidden_t), 4)
    if rec["correct"]:
        stress_t = sum(t for t in r["times"][2] if t is not None)
        ref = task_obj["fastest_ref_stress_s"]
        rec["runtime_ratio"] = round(stress_t / ref, 4) if ref > 0 else None
        rec["stress_s"] = round(stress_t, 6)
    return rec
