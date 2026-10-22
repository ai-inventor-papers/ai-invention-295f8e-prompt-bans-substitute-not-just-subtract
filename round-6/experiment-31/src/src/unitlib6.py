#!/usr/bin/env python3
"""Parent side of the sandbox and the generic labeller backbone for the panel-I units (ported from exp26 unitlib.py).

extract_code: first ```python block (an unterminated final block is taken as-is).
run_tests:    fresh `python -I -S src/sandbox_tests6.py` subprocess, RLIMIT_AS 2 GiB, per-case time limits.
run_trace:    fresh `python -I -S src/sandbox_trace6.py` subprocess on the unit's probe inputs.
label_code:   invalid (no code / syntax error / no def solve / raises at load) -> tests -> runtime label (primary) and
              AST label; combined: agree -> label; one abstains -> the other; both abstain -> 'other'; disagree ->
              None (judges adjudicate later; unresolved -> 'disputed').
Unit modules live in src/units/<u>.py and expose: CHECKER, ARGS, ORACLE_A, ORACLE_B, make_tests(), REFERENCES,
MUTANTS, EXCLUDED, PROBES, runtime_rule(trace) -> label | None, ast_rule(code) -> label | None.
"""

from __future__ import annotations

import ast
import hashlib
import importlib
import json
import re
import resource
import subprocess
import sys
from pathlib import Path
from typing import Any

SRC = Path(__file__).resolve().parent
ROOT = SRC.parent
PY = sys.executable
FENCE_RE = re.compile(r"```[ \t]*(?:python3?|py|Python)?[ \t]*\n(.*?)```", re.S)
OPEN_FENCE_RE = re.compile(r"```[ \t]*(?:python3?|py|Python)?[ \t]*\n(.*)$", re.S)


def extract_code(text: str | None) -> str | None:
    if not text:
        return None
    m = FENCE_RE.search(text)
    if m:
        return m.group(1)
    m = OPEN_FENCE_RE.search(text)
    return m.group(1) if m else None


def extract_plain(prompt_text: str, gen_text: str) -> str:
    """Plain completion: the prompt opened the fence and wrote the def line + docstring; the program is that header
    plus the generation up to the closing fence."""
    head = prompt_text.split("```python\n", 1)[1]
    body = gen_text.split("```", 1)[0]
    return head + body


def code_sha(code: str | None) -> str:
    return hashlib.sha256((code or "").encode()).hexdigest()


def syntax_ok(code: str) -> bool:
    try:
        compile(code, "<c>", "exec")
        return True
    except (SyntaxError, ValueError):
        return False


def _limit_mem() -> None:
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024 ** 3, 2 * 1024 ** 3))


def unit_mod(u: str):
    if str(SRC) not in sys.path:
        sys.path.insert(0, str(SRC))
    return importlib.import_module(f"units.{u.lower()}")


def load_tests(u: str) -> list[dict[str, Any]]:
    p = ROOT / "units" / u / "tests.jsonl"
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def run_tests(code: str, cases: list[dict[str, Any]], checker: str, stop_on_fail: bool = True,
              limit_override: float | None = None) -> dict[str, Any]:
    payload = {"code": code, "checker": checker, "stop_on_fail": stop_on_fail,
               "cases": [{"args_json": json.dumps(c["args"]), "expected_json": json.dumps(c["expected"]),
                          "limit": float(limit_override or c.get("limit", 1.0))} for c in cases]}
    total = sum(p["limit"] for p in payload["cases"]) + 30.0
    try:
        pr = subprocess.run([PY, "-I", "-S", str(SRC / "sandbox_tests6.py")], input=json.dumps(payload),
                            capture_output=True, text=True, timeout=total, preexec_fn=_limit_mem)
        lines = []
        for l in pr.stdout.splitlines():
            if l.startswith("@@AII@@"):
                try:
                    lines.append(json.loads(l[7:]))
                except json.JSONDecodeError:
                    pass
        err = pr.stderr[-300:]
    except subprocess.TimeoutExpired:
        lines, err = [], "harness timeout"
    statuses = ["not_run"] * len(cases)
    times: list[float | None] = [None] * len(cases)
    load_error = None
    msgs = []
    for r in lines:
        if r["i"] == -1:
            load_error = r["msg"]
            continue
        statuses[r["i"]] = r["status"]
        times[r["i"]] = r["t"]
        if r.get("msg"):
            msgs.append(r["msg"])
    if not lines and not load_error:
        load_error = f"no output: {err}"
    n_ok = sum(1 for s in statuses if s == "ok")
    first_fail = next(({"i": i, "status": s, "case_id": cases[i]["case_id"]} for i, s in enumerate(statuses)
                       if s != "ok"), None)
    return {"passed": load_error is None and n_ok == len(cases), "n_cases": len(cases), "n_pass": n_ok,
            "statuses": statuses, "times": times, "first_fail": first_fail, "load_error": load_error,
            "msgs": msgs[:3]}


def run_trace(code: str, probes: list[dict[str, Any]], limit: float = 6.0) -> dict[str, Any]:
    payload = {"code": code, "probes": probes, "limit": limit}
    total = limit * len(probes) + 30.0
    try:
        pr = subprocess.run([PY, "-I", "-S", str(SRC / "sandbox_trace6.py")], input=json.dumps(payload),
                            capture_output=True, text=True, timeout=total, preexec_fn=_limit_mem)
        lines = [l[7:] for l in pr.stdout.splitlines() if l.startswith("@@AII@@")]
        if not lines:
            return {"_error": f"no output: {pr.stderr[-300:]}"}
        return json.loads(lines[-1])
    except subprocess.TimeoutExpired:
        return {"_error": "trace timeout"}
    except json.JSONDecodeError as e:
        return {"_error": f"bad trace json: {e}"}


# ------------------------------------------------------------------------------------------------ trace helpers
def probe(tr: dict[str, Any], name: str) -> dict[str, Any] | None:
    if "_error" in tr or "load_error" in tr:
        return None
    v = tr.get(name)
    if v is None or v.get("error"):
        return None
    return v


def op(p: dict[str, Any], *names: str) -> int:
    o = p.get("ops", {})
    return sum(int(o.get(n, 0)) for n in names)


def binop(p: dict[str, Any], *syms: str) -> int:
    """BINARY_OP count for operator symbols, plain and in-place ('>>' counts '>>' and '>>=')."""
    o = p.get("ops", {})
    return sum(int(o.get("BINARY_OP:" + s, 0)) + int(o.get("BINARY_OP:" + s + "=", 0)) for s in syms)


def call(p: dict[str, Any], *names: str) -> int:
    c = p.get("calls", {})
    return sum(int(v) for k, v in c.items() if k in names or k.split(".")[-1] in names)


def maxlen(p: dict[str, Any], *names: str) -> int:
    c = p.get("calls_maxlen", {})
    vals = [int(v) for k, v in c.items() if k in names or k.split(".")[-1] in names]
    return max(vals) if vals else -1


def maxint(p: dict[str, Any], *names: str) -> int:
    c = p.get("calls_maxint", {})
    vals = [int(v) for k, v in c.items() if k in names or k.split(".")[-1] in names]
    return max(vals) if vals else -1


def user_calls(p: dict[str, Any]) -> int:
    """Calls of user-defined functions other than solve, lambdas and comprehension frames."""
    return sum(int(v) for k, v in p.get("py_calls", {}).items()
               if k not in ("solve", "<genexpr>", "<listcomp>", "<setcomp>", "<dictcomp>", "<lambda>"))


def lst(p: dict[str, Any], k: str) -> int:
    return int(p.get("lst", {}).get(k, 0))


# ------------------------------------------------------------------------------------------------ AST helpers
def ast_tree(code: str) -> ast.AST | None:
    try:
        return ast.parse(code)
    except (SyntaxError, ValueError):
        return None


def names_used(tree: ast.AST) -> set[str]:
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Name):
            out.add(n.id)
        elif isinstance(n, ast.Attribute):
            out.add(n.attr)
        elif isinstance(n, ast.alias):
            out.add(n.name.split(".")[-1])
            if n.asname:
                out.add(n.asname)
    return out


def calls_named(tree: ast.AST) -> list[str]:
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Name):
                out.append(f.id)
            elif isinstance(f, ast.Attribute):
                out.append(f.attr)
    return out


def binops(tree: ast.AST) -> list[str]:
    return [type(n.op).__name__ for n in ast.walk(tree) if isinstance(n, (ast.BinOp, ast.AugAssign))]


def has_set_literal(tree: ast.AST) -> bool:
    return any(isinstance(n, (ast.Set, ast.SetComp)) for n in ast.walk(tree)) or "set" in calls_named(tree)


def has_dict(tree: ast.AST) -> bool:
    return any(isinstance(n, (ast.Dict, ast.DictComp)) for n in ast.walk(tree)) or any(
        c in calls_named(tree) for c in ("dict", "defaultdict", "Counter", "OrderedDict"))


def recursive_functions(tree: ast.AST) -> set[str]:
    out = set()
    for f in ast.walk(tree):
        if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for n in ast.walk(f):
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == f.name:
                    out.add(f.name)
    return out


def func_defs(tree: ast.AST) -> list[str]:
    return [f.name for f in ast.walk(tree) if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef))]


def subscript_stores(tree: ast.AST, name: str | None = None) -> int:
    """Number of assignment targets of the form X[...] (optionally X == name)."""
    n_ = 0
    for n in ast.walk(tree):
        tg = []
        if isinstance(n, ast.Assign):
            tg = n.targets
        elif isinstance(n, ast.AugAssign):
            tg = [n.target]
        for t in tg:
            for e in ast.walk(t):
                if isinstance(e, ast.Subscript) and isinstance(e.value, ast.Name) and (name is None or
                                                                                        e.value.id == name):
                    n_ += 1
    return n_


def tuple_swaps(tree: ast.AST) -> int:
    """a[i], a[j] = a[j], a[i] style exchanges."""
    k = 0
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Tuple) and \
                isinstance(n.value, ast.Tuple):
            if any(isinstance(e, ast.Subscript) for e in n.targets[0].elts):
                k += 1
    return k


def strip_comments_docstrings(code: str) -> str:
    tree = ast_tree(code)
    if tree is None:
        return code
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef, ast.Module)):
            if n.body and isinstance(n.body[0], ast.Expr) and isinstance(getattr(n.body[0], "value", None),
                                                                          ast.Constant) \
                    and isinstance(n.body[0].value.value, str):
                n.body = n.body[1:] or [ast.Pass()]
    try:
        return ast.unparse(tree)
    except Exception:  # noqa: BLE001
        return code


# ------------------------------------------------------------------------------------------------ labelling
def label_code(u: str, code: str | None, cases: list[dict[str, Any]] | None = None,
               want_tests: bool = True) -> dict[str, Any]:
    mod = unit_mod(u)
    out: dict[str, Any] = {"code_sha256": code_sha(code), "extracted": code is not None}
    if code is None or not syntax_ok(code) or not re.search(r"def\s+solve\s*\(", code):
        out.update(valid=False, passed=False, ast_label="invalid", runtime_label="invalid", label_pre="invalid",
                   labeller_source="invalid")
        return out
    out["valid"] = True
    if want_tests:
        tr = run_tests(code, cases if cases is not None else load_tests(u), mod.CHECKER)
        out.update(passed=tr["passed"], n_pass=tr["n_pass"], n_cases=tr["n_cases"], first_fail=tr["first_fail"],
                   load_error=tr["load_error"])
        if tr["load_error"] is not None and str(tr["load_error"]).split(":")[0] not in ("no output",):
            out.update(valid=False, passed=False, ast_label="invalid", runtime_label="invalid", label_pre="invalid",
                       labeller_source="invalid_load_error")
            return out
    try:
        out["ast_label"] = mod.ast_rule(code)
    except Exception as e:  # noqa: BLE001
        out["ast_label"] = None
        out["ast_error"] = f"{type(e).__name__}: {e}"
    trace = run_trace(code, mod.PROBES)
    try:
        out["runtime_label"] = mod.runtime_rule(trace)
    except Exception as e:  # noqa: BLE001
        out["runtime_label"] = None
        out["runtime_error"] = f"{type(e).__name__}: {e}"
    out["trace_summary"] = summarise_trace(trace)
    rt, al = out["runtime_label"], out["ast_label"]
    if rt is not None and al is not None and rt == al:
        out.update(label_pre=rt, labeller_source="agree")
    elif rt is None and al is not None:
        out.update(label_pre=al, labeller_source="ast_only_untraceable")
    elif al is None and rt is not None:
        out.update(label_pre=rt, labeller_source="runtime_only")
    elif rt is None and al is None:
        out.update(label_pre="other", labeller_source="neither")
    else:
        out.update(label_pre=None, labeller_source="disagree")
    return out


def summarise_trace(tr: dict[str, Any]) -> dict[str, Any]:
    if "_error" in tr or "load_error" in tr:
        return {"error": tr.get("_error") or tr.get("load_error")}
    s = {}
    for k, v in tr.items():
        s[k] = {"error": v.get("error"), "calls": v.get("calls"), "py_calls": v.get("py_calls"),
                "max_depth": v.get("max_depth"), "lines": v.get("lines"), "lst": v.get("lst"),
                "correct": v.get("correct"),
                "binops": {k2: v2 for k2, v2 in (v.get("ops") or {}).items() if k2.startswith(("BINARY_OP",
                                                                                                 "CONTAINS",
                                                                                                 "COMPARE"))}}
    return s
