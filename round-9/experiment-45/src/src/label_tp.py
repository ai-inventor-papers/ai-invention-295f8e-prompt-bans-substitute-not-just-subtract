#!/usr/bin/env python3
"""Labelling of screen rows (Stage 2/4): last ```python fence of the answer -> sandboxed hidden tests (primary: the
ITER2 exp9 suite in vendor/exp9/tasks; secondary: the ITER1 exp2 suite in vendor/exp2) -> tracer probes -> the
10-class runtime + AST rules (exp9 labeller_ext, unchanged) -> gated judge 'a' on runtime/AST disagreement ->
combine (exp9 rule) = label_raw with labeller_source."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable

from loguru import logger

from common import DATA, ROOT, VENDOR, append_jsonl, read_jsonl, sha256_text

sys.path.insert(0, str(VENDOR))
EVAL_CACHE = DATA / "program_eval_cache.jsonl"
EXP2_DIR = ROOT / "vendor" / "exp2"
WORKERS = 5
_FENCE = re.compile(r"```[ \t]*(?:python3|python|py|Python)?[ \t]*\n(.*?)(?:```|\Z)", re.DOTALL)
_PYFENCE = re.compile(r"```[ \t]*(?:python3|python|py|Python)[ \t]*\n(.*?)(?:```|\Z)", re.DOTALL)


def ref_mode(fname: str) -> str:
    """Reference file name -> catalogue class (exp9 mb/label.py rule)."""
    stem = Path(fname).stem
    for prefix, mode in (("bibfs", "bibfs"), ("biastar", "biastar"), ("bfs", "bfs"), ("dfs", "dfs"),
                         ("iddfs", "iddfs"), ("idastar", "idastar"), ("astar", "astar"), ("gbfs", "gbfs"),
                         ("dijkstra", "dijkstra_unit"), ("jps", "jps")):
        if stem.startswith(prefix):
            return mode
    raise ValueError(f"cannot map reference {fname}")


def extract_last_fence(content: str | None) -> tuple[str | None, str]:
    """Last ```python fence of the answer (an unclosed final fence = truncation is still extracted); a bare ``` fence
    is the fallback; no fence -> None ('invalid')."""
    if not content:
        return None, "no_content"
    blocks = [m.group(1) for m in _PYFENCE.finditer(content) if m.group(1).strip()]
    if blocks:
        return blocks[-1].rstrip() + "\n", "python_fence_last"
    blocks = [m.group(1) for m in _FENCE.finditer(content) if m.group(1).strip()]
    if blocks:
        return blocks[-1].rstrip() + "\n", "bare_fence_last"
    return None, "no_fence"


def run_exp2_suite(code: str) -> dict[str, Any]:
    """Secondary pass column: ITER1 exp2 harness.py (tests mode) on hidden_tests_t1.json (41 cases)."""
    ht = json.loads((EXP2_DIR / "hidden_tests_t1.json").read_text())
    job = {"mode": "tests", "task": "t1", "code": code, "tests": ht["tests"], "limits": ht["limits"]}
    from tasks.harness import SYS_PY  # vendor/exp9 harness: stdlib-only CPython 3.12

    with tempfile.TemporaryDirectory(dir=str(DATA)) as d:
        jp, rp = Path(d) / "job.json", Path(d) / "res.json"
        jp.write_text(json.dumps(job))
        try:
            subprocess.run([SYS_PY, "-I", str(EXP2_DIR / "harness.py"), str(jp), str(rp)], cwd=d,
                           stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=sum(ht["limits"]) + 10.0,
                           start_new_session=True)
            res = json.loads(rp.read_text()) if rp.exists() else {"passed": False, "fail_kind": "no_result"}
        except subprocess.TimeoutExpired:
            res = {"passed": False, "fail_kind": "hard_timeout"}
        except (OSError, json.JSONDecodeError) as e:
            res = {"passed": False, "fail_kind": f"harness_error:{type(e).__name__}"}
    return {"passed_exp2": bool(res.get("passed", False)), "exp2_fail_kind": res.get("fail_kind"),
            "exp2_n_pass": res.get("n_pass")}


def _trim_probes(pr: dict[str, Any]) -> dict[str, Any]:
    out = dict(pr)
    probes = []
    for p in pr.get("probes", []):
        q = dict(p)
        q["heaps"] = [{"push": h.get("push", 0), "pop": h.get("pop", 0), "pops": h.get("pops", [])[:120],
                       "first": h.get("first"), "last": h.get("last"), "cells": h.get("cells", [])[:40]}
                      for h in p.get("heaps", [])]
        probes.append(q)
    out["probes"] = probes
    return out


def _evaluate_one(code: str) -> dict[str, Any]:
    from tasks.harness import evaluate_program

    ev = evaluate_program("t1", code)
    t, sm = ev["tests"], ev["small"]
    e2 = run_exp2_suite(code)
    return {"passed": bool(t.get("passed")), "n_cases": t.get("n_cases"), "n_passed": t.get("n_passed"),
            "error": t.get("error"), "fail_case": t.get("fail_case"), "fail_msg": t.get("fail_msg"),
            "wall_s": t.get("wall_s"), "passed_small": bool(sm.get("passed")), **e2,
            "probes": _trim_probes(ev["probes"])}


def parallel_map(fn: Callable[[Any], Any], items: list[Any], workers: int = WORKERS, desc: str = "") -> list[Any]:
    out: list[Any] = [None] * len(items)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(fn, it): i for i, it in enumerate(items)}
        done = 0
        for f in as_completed(futs):
            i = futs[f]
            try:
                out[i] = f.result()
            except Exception as e:  # noqa: BLE001 - one bad program must not stop the batch
                logger.error(f"{desc} item {i} failed: {type(e).__name__}: {e}")
                out[i] = None
            done += 1
            if done % 50 == 0 or done == len(items):
                logger.info(f"{desc}: {done}/{len(items)}")
    return out


def evaluate_unique(codes: list[str]) -> dict[str, dict[str, Any]]:
    """sha256(code) -> evaluation (cached in data/program_eval_cache.jsonl)."""
    cache = {r["key"]: r for r in read_jsonl(EVAL_CACHE)}
    todo = {}
    for c in codes:
        k = sha256_text(c)
        if k not in cache:
            todo[k] = c
    logger.info(f"evaluate_unique: {len(set(sha256_text(c) for c in codes))} unique, {len(todo)} to run")
    keys = list(todo)
    res = parallel_map(lambda k: _evaluate_one(todo[k]), keys, desc="sandbox")
    for k, r in zip(keys, res):
        if r is None:
            r = {"passed": False, "error": "harness_exception", "probes": {"probes": []}, "passed_exp2": False}
        r["key"] = k
        append_jsonl(EVAL_CACHE, r)
        cache[k] = r
    return cache


def mechanical(code: str, ev: dict[str, Any]) -> dict[str, Any]:
    from labeller_ext import ast_rules, runtime_rules

    try:
        rl, rwhy, rinfo = runtime_rules.label("t1", ev.get("probes") or {"probes": []})
    except Exception as e:  # noqa: BLE001 - malformed probe records
        rl, rwhy, rinfo = "unknown", f"runtime rule error {type(e).__name__}", {}
    try:
        al, awhy, _ = ast_rules.label(code, "t1")
    except Exception as e:  # noqa: BLE001
        al, awhy = "unknown", f"ast rule error {type(e).__name__}"
    return {"runtime_label": rl, "runtime_reason": str(rwhy)[:200], "ast_label": al, "ast_reason": str(awhy)[:200],
            "force_judge": bool((rinfo or {}).get("force_judge"))}


def label_rows(rows: list[dict[str, Any]], use_judge: bool = True) -> list[dict[str, Any]]:
    """rows need 'content' (final answer text) and 'uid'. Adds code, passed, passed_exp2, runtime/AST labels,
    label_raw and labeller_source (agree / judge / fallback_no_judge / invalid)."""
    from labeller_ext.combine import combine, needs_judge

    import judge_tp

    out = []
    codes = []
    for r in rows:
        code, how = extract_last_fence(r.get("content"))
        rr = dict(r)
        rr["extract_method"] = how
        rr["code"] = code
        rr["code_sha256"] = sha256_text(code) if code else None
        if code:
            codes.append(code)
        out.append(rr)
    cache = evaluate_unique(codes)
    mech = {sha256_text(c): mechanical(c, cache[sha256_text(c)]) for c in set(codes)}
    need = [c for c in set(codes) if needs_judge(mech[sha256_text(c)]["runtime_label"],
                                                 mech[sha256_text(c)]["ast_label"],
                                                 mech[sha256_text(c)]["force_judge"])]
    jl: dict[str, dict[str, Any] | None] = {}
    if need and use_judge:
        res = judge_tp.judge_codes(need, judge_tp.LABELLER_JUDGE, purpose="labeller")
        jl = {sha256_text(c): j for c, j in zip(need, res)}
    for rr in out:
        if rr["code"] is None:
            rr.update({"label_raw": "invalid", "labeller_source": "invalid", "passed": False, "passed_exp2": False,
                       "runtime_label": None, "ast_label": None, "test_error": rr["extract_method"]})
            continue
        k = rr["code_sha256"]
        ev, mk = cache[k], mech[k]
        j = jl.get(k)
        lbl, src = combine(mk["runtime_label"], mk["ast_label"], j, mk["force_judge"])
        rr.update({"passed": bool(ev.get("passed")), "passed_exp2": bool(ev.get("passed_exp2")),
                   "n_cases_passed": ev.get("n_passed"), "test_error": ev.get("error"),
                   "fail_case": ev.get("fail_case"), "passed_small": ev.get("passed_small"),
                   "runtime_label": mk["runtime_label"], "runtime_reason": mk["runtime_reason"],
                   "ast_label": mk["ast_label"], "ast_reason": mk["ast_reason"],
                   "labeller_judge": j.get("label") if j else None, "label_raw": lbl, "labeller_source": src})
    return out
