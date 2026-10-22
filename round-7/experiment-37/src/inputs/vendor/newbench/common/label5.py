"""Labelling of new-unit programs: extraction -> hidden tests (runner5) -> AST label (unit ast_rules) -> runtime label
(tracer5 on the unit's probes + runtime_rules) -> combine (bench rule): agree, or AST 'unknown' -> runtime label;
runtime 'unknown' or a real disagreement -> blind judges (judge5.adjudicate); no majority / judges unavailable ->
'disputed'. Mechanism-level labels: a renamed or disguised default is still the default."""

from __future__ import annotations

import importlib.util
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path
from typing import Any

from .harness5 import (code_sha, extract_code, extract_plainc, has_solve, read_tests, run_tests, run_trace,
                       syntax_ok, unit_path)

_LOCK = threading.Lock()
_CACHE: dict[str, dict[str, Any]] = {}


@lru_cache(maxsize=None)
def _mod(unit: str, name: str):
    p = unit_path(unit) / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"{unit}_{name}", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@lru_cache(maxsize=None)
def spec_of(unit: str) -> dict:
    return json.loads((unit_path(unit) / "spec.json").read_text())


@lru_cache(maxsize=None)
def probes_of(unit: str) -> list:
    return json.loads((unit_path(unit) / "probes.json").read_text())


@lru_cache(maxsize=None)
def cases_of(unit: str) -> list:
    return read_tests(unit_path(unit) / "tests.jsonl")


def code_of(row: dict[str, Any], prompts: dict | None = None) -> str | None:
    if row.get("prompt_kind") == "plainc" or row.get("arm") == "PLAINC":
        from specs5_bridge import plainc_text  # noqa: F401 (resolved via sys.path of the caller)
        return extract_plainc(plainc_text(row["task"]), row.get("text") or "")
    return extract_code(row.get("text"))


def mech_labels(unit: str, code: str) -> dict[str, Any]:
    """Tests + AST + runtime labels of one program (cached by code sha)."""
    k = f"{unit}|{code_sha(code)}"
    with _LOCK:
        if k in _CACHE:
            return dict(_CACHE[k])
    if not code or not syntax_ok(code) or not has_solve(code):
        rec = {"valid": False, "passed": False, "ast_label": "invalid", "runtime_label": "invalid"}
    else:
        tr = run_tests(code, unit, cases_of(unit))
        try:
            al = _mod(unit, "ast_rules").label(code)
        except Exception:  # noqa: BLE001 - a crashing rule is 'unknown'
            al = "unknown"
        trace = run_trace(code, probes_of(unit))
        try:
            rl = _mod(unit, "runtime_rules").label(trace)
        except Exception:  # noqa: BLE001
            rl = "unknown"
        rec = {"valid": True, "passed": bool(tr["passed"]), "n_pass": tr["n_pass"], "n_cases": tr["n_cases"],
               "first_fail": tr["first_fail"], "load_error": tr["load_error"], "ast_label": al,
               "runtime_label": rl, "trace_error": trace.get("error")}
    with _LOCK:
        _CACHE[k] = rec
    return dict(rec)


def needs_judge(rl: str, al: str) -> bool:
    return rl == "unknown" or (al not in ("unknown",) and al != rl)


def label_many(rows: list[dict[str, Any]], use_judge: bool = True, workers: int = 10) -> list[dict[str, Any]]:
    from .judge5 import adjudicate

    codes = [code_of(r) for r in rows]
    with ThreadPoolExecutor(workers) as ex:
        mech = list(ex.map(lambda rc: mech_labels(rc[0]["task"], rc[1]), zip(rows, codes)))
    need = [i for i, m in enumerate(mech) if m["valid"] and needs_judge(m["runtime_label"], m["ast_label"])]
    adj: dict[int, dict[str, Any]] = {}
    if need and use_judge:
        by_unit: dict[str, list[int]] = {}
        for i in need:
            by_unit.setdefault(rows[i]["task"], []).append(i)
        for u, idx in by_unit.items():
            try:
                res = adjudicate(u, spec_of(u), [codes[i] for i in idx])
            except Exception:  # noqa: BLE001 - judges unavailable -> disputed
                res = [{"label": None} for _ in idx]
            for i, r in zip(idx, res):
                adj[i] = r
    out = []
    for i, (r, m, c) in enumerate(zip(rows, mech, codes)):
        if not m["valid"]:
            lab, src = "invalid", "extraction"
        elif i in need:
            a = adj.get(i) or {}
            if a.get("label"):
                lab, src = a["label"], "judge"
            else:
                lab, src = "disputed", "judge_unavailable_or_split"
        else:
            lab = m["runtime_label"]
            src = "runtime+ast" if m["ast_label"] == m["runtime_label"] else "runtime(ast_unknown)"
        out.append({"label": lab, "labeller_source": src, "passed": bool(m.get("passed")) and m["valid"],
                    "valid": m["valid"], "runtime_label": m.get("runtime_label"), "ast_label": m.get("ast_label"),
                    "judge_label": (adj.get(i) or {}).get("label"),
                    "judge_votes": {k: (adj.get(i) or {}).get(k) for k in ("j1", "j2", "j3")} if i in adj else None,
                    "n_pass": m.get("n_pass"), "n_cases": m.get("n_cases"), "code": c})
    return out
