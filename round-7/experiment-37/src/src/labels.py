#!/usr/bin/env python3
"""Frozen labellers of the three tasks (vendored, executed from inputs/vendor/ only) + DS-signature.

T2  : exp8 suite (tasks.harness.run_probes -> labeller.runtime_rules / labeller.ast_rules) + the iteration-4/6
      array-Dijkstra re-gate (regate_rules.apply_t2) applied to both the runtime and the AST label.
T03 : exp11 bench (bench.common.probes.run_trace -> rtrules.runtime_label; astrules.ast_label).
A3  : iteration-5 newbench (newbench.common.harness5.run_trace on probes.json -> A3 runtime_rules; A3 ast_rules).
Combine (bench rule): runtime primary; agree or AST 'unknown' -> runtime label; runtime 'unknown' or a real
disagreement -> blind judge (google/gemini-2.5-flash-lite, catalogue + 'other'); no judge -> runtime label if known,
else AST label if known, else 'other' (flag runtime_unjudged).
"""

from __future__ import annotations

import ast
import importlib.util
import json
import sys
import threading
from functools import lru_cache
from typing import Any

from common import VENDOR, sha256_text

_LOCK = threading.Lock()
_CACHE: dict[str, dict[str, Any]] = {}
UNRESOLVED = ("unknown", "inconsistent", None, "", "invalid")
T2_MAP = {"bidijkstra": "bidijkstra", "dijkstra": "dijkstra", "bf_spfa": "bf_spfa", "floyd": "floyd", "dial": "dial"}

for _p in (VENDOR, VENDOR / "exp8_suite", VENDOR / "exp30_src"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))


@lru_cache(maxsize=None)
def _a3_mod(name: str):
    p = VENDOR / "newbench" / "A3_trapping_rain_water" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"A3_{name}", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@lru_cache(maxsize=None)
def _a3_probes() -> list:
    return json.loads((VENDOR / "newbench" / "A3_trapping_rain_water" / "probes.json").read_text())


def _norm(task: str, lab: Any) -> str:
    lab = str(lab) if lab is not None else "unknown"
    if task == "T2":
        return T2_MAP.get(lab, lab)
    return lab


def mech_label(task: str, code: str) -> dict[str, Any]:
    """Runtime + AST labels of one program (no judge); cached by (task, code sha)."""
    key = f"{task}|{sha256_text(code)}"
    with _LOCK:
        if key in _CACHE:
            return dict(_CACHE[key])
    rec: dict[str, Any] = {"runtime_label": "unknown", "ast_label": "unknown", "regate": False, "trace_error": None}
    try:
        if task == "T2":
            from labeller import ast_rules, runtime_rules
            from regate_rules import apply_t2
            from tasks.harness import run_probes
            pr = run_probes("t2", code)
            rl, rwhy, _ = runtime_rules.label("t2", pr)
            al, awhy, _ = ast_rules.label(code, "t2")
            rl2, g1 = apply_t2(rl, code)
            al2, g2 = apply_t2(al, code)
            rec.update(runtime_label=_norm(task, rl2), ast_label=_norm(task, al2), regate=bool(g1 or g2),
                       runtime_reason=str(rwhy)[:160], ast_reason=str(awhy)[:160],
                       trace_error=pr.get("error") if isinstance(pr, dict) else None)
        elif task == "T03":
            from bench.common.astrules import ast_label
            from bench.common.probes import run_trace
            from bench.common.rtrules import runtime_label
            tr = run_trace(code, "T03")
            rec.update(runtime_label=_norm(task, runtime_label("T03", tr)), ast_label=_norm(task, ast_label("T03", code)),
                       trace_error=tr.get("error"))
        elif task == "A3":
            from newbench.common.harness5 import run_trace
            tr = run_trace(code, _a3_probes())
            try:
                rl = _a3_mod("runtime_rules").label(tr)
            except Exception:  # noqa: BLE001 - a crashing frozen rule is 'unknown' (labeller convention)
                rl = "unknown"
            try:
                al = _a3_mod("ast_rules").label(code)
            except Exception:  # noqa: BLE001
                al = "unknown"
            rec.update(runtime_label=_norm(task, rl), ast_label=_norm(task, al), trace_error=tr.get("error"))
    except Exception as e:  # noqa: BLE001 - labeller failure must not kill the search; recorded
        rec["trace_error"] = f"labeller_exception:{type(e).__name__}:{str(e)[:120]}"
    with _LOCK:
        _CACHE[key] = rec
    return dict(rec)


def needs_judge(rl: str, al: str) -> bool:
    return rl in UNRESOLVED or (al not in UNRESOLVED and al != rl)


def combine(rl: str, al: str, judge_label: str | None) -> tuple[str, str]:
    if not needs_judge(rl, al):
        return rl, ("runtime+ast" if al == rl else "runtime(ast_unknown)")
    if judge_label:
        return judge_label, "judge"
    if rl not in UNRESOLVED:
        return rl, "runtime_unjudged"
    if al not in UNRESOLVED:
        return al, "ast_unjudged"
    return "other", "fallback_other"


def judge_prompt(task_obj: dict[str, Any], code: str) -> str:
    cat = "\n".join(f"- {c['mode']}: {c['display_name']} -- {c['mechanism']}" for c in task_obj["catalogue"])
    return (f"You are labelling the core algorithm of a Python program.\n\n{task_obj['spec_body']}\n\n"
            f"Known algorithm classes for this task:\n{cat}\n- other: the core mechanism is none of the classes above\n\n"
            f"Program:\n```python\n{code}\n```\n\nJudge the mechanism, not the variable names or comments. Answer with "
            f"JSON only: {{\"label\": \"<one of: {', '.join(task_obj['modes'])}, other>\", \"reason\": \"<one sentence>\"}}")


# ------------------------------------------------------------------------------------------------ DS signature
DS_FLAGS = ("heap", "deque_or_queue", "sort", "bisect", "recursion", "dict_or_counter", "set", "matrix_2d",
            "stack_list", "bitops", "random", "custom_class")


def _call_name(c: ast.Call) -> str:
    f = c.func
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        return f.attr
    return ""


def ds_flags(code: str) -> list[str]:
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError, RecursionError, MemoryError):
        return []
    imps: set[str] = set()
    calls: list[ast.Call] = []
    names: set[str] = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            imps |= {a.name.split(".")[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.module:
            imps.add(n.module.split(".")[0])
            imps |= {a.name for a in n.names}
        elif isinstance(n, ast.Call):
            calls.append(n)
        elif isinstance(n, ast.Name):
            names.add(n.id)
    cn = {_call_name(c) for c in calls}
    f: set[str] = set()
    if "heapq" in imps or cn & {"heappush", "heappop", "heapify", "heapreplace", "heappushpop", "nsmallest",
                                 "nlargest", "PriorityQueue"}:
        f.add("heap")
    if cn & {"deque", "Queue", "SimpleQueue", "popleft", "appendleft"} or any(
            _call_name(c) == "pop" and c.args and isinstance(c.args[0], ast.Constant) and c.args[0].value == 0
            for c in calls):
        f.add("deque_or_queue")
    if cn & {"sorted", "sort"}:
        f.add("sort")
    if "bisect" in imps or cn & {"bisect_left", "bisect_right", "bisect", "insort", "insort_left", "insort_right"}:
        f.add("bisect")
    for fn in ast.walk(tree):
        if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if any(isinstance(c, ast.Call) and isinstance(c.func, ast.Name) and c.func.id == fn.name
                   for c in ast.walk(fn) if c is not fn):
                f.add("recursion")
                break
    if any(isinstance(n, (ast.Dict, ast.DictComp)) for n in ast.walk(tree)) or \
            cn & {"dict", "Counter", "defaultdict", "OrderedDict"}:
        f.add("dict_or_counter")
    if any(isinstance(n, (ast.Set, ast.SetComp)) for n in ast.walk(tree)) or cn & {"set", "frozenset"}:
        f.add("set")
    for n in ast.walk(tree):
        if isinstance(n, ast.ListComp) and isinstance(n.elt, (ast.List, ast.ListComp, ast.BinOp)):
            if isinstance(n.elt, ast.BinOp) and not isinstance(n.elt.left, ast.List):
                continue
            f.add("matrix_2d")
            break
        if isinstance(n, ast.List) and n.elts and all(isinstance(e, ast.List) for e in n.elts):
            f.add("matrix_2d")
            break
    pops_noarg = any(_call_name(c) == "pop" and not c.args and isinstance(c.func, ast.Attribute) for c in calls)
    if pops_noarg and "append" in cn:
        f.add("stack_list")
    if any(isinstance(n, ast.BinOp) and isinstance(n.op, (ast.LShift, ast.RShift, ast.BitAnd, ast.BitOr, ast.BitXor))
           for n in ast.walk(tree)) or any(isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.Invert)
                                           for n in ast.walk(tree)):
        f.add("bitops")
    if "random" in imps:
        f.add("random")
    if any(isinstance(n, ast.ClassDef) for n in ast.walk(tree)):
        f.add("custom_class")
    return [x for x in DS_FLAGS if x in f]


def ds_signature(code: str) -> str:
    fl = ds_flags(code)
    return "+".join(fl[:3]) if fl else "none"
