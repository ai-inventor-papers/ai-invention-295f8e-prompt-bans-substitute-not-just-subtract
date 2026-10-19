#!/usr/bin/env python3
"""Per-sample labelling: hidden tests + runtime trace (sandbox subprocess) + AST rules -> combined label.

combine(): runtime == AST and in catalogue -> that label ('runtime+ast'); runtime 'unknown' and AST
'other' -> 'other'; anything else -> needs the judge (filled in later by labeller/judge.py).
Test/trace results are cached by code sha256 (cache/tests/<task>/), sample labels by text sha256
(cache/labels/<task>/).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import CACHE_DIR, CATALOGUE, LABEL_CACHE, TASKS_DIR, sha256_text  # noqa: E402
from labeller.ast_rules import ast_label  # noqa: E402
from labeller.harness import analyse_text  # noqa: E402
from labeller.tracer import runtime_label  # noqa: E402

RUNNER = Path(__file__).resolve().parent / "runner.py"
TEST_CACHE = CACHE_DIR / "tests"
PY = sys.executable


def tests_file(task: str) -> Path:
    return TASKS_DIR / f"tests_{task}.json"


def overall_timeout(task: str) -> float:
    d = json.loads(tests_file(task).read_text())
    return sum(c.get("limit_s", 1.0) for c in d["cases"]) + 5.0 + 3 * 3.0 + 10.0


_TIMEOUTS: dict = {}


def run_code(task: str, code: str, trace: bool = True) -> dict:
    """Run hidden tests + tracer on one program (cached by code sha256)."""
    csha = sha256_text(code)
    cf = TEST_CACHE / task / f"{csha}.json"
    if cf.exists():
        try:
            return json.loads(cf.read_text())
        except json.JSONDecodeError:
            pass
    if task not in _TIMEOUTS:
        _TIMEOUTS[task] = overall_timeout(task)
    with tempfile.TemporaryDirectory(dir=str(CACHE_DIR / "tmp")) as td:
        job = Path(td) / "job.json"
        out = Path(td) / "res.json"
        job.write_text(json.dumps({"task": task, "code": code, "tests_file": str(tests_file(task)), "trace": trace,
                                   "probe_timeout": 3.0}))
        env = {k: v for k, v in os.environ.items() if k in ("PATH", "LANG", "LC_ALL", "HOME")}
        try:
            p = subprocess.run([PY, "-I", str(RUNNER), str(job), str(out)], capture_output=True, text=True,
                               timeout=_TIMEOUTS[task], cwd=td, env=env)
            if out.exists():
                res = json.loads(out.read_text())
            else:
                res = {"has_solve": None, "passed": False, "first_failure": {"msg": f"runner crashed rc={p.returncode}"},
                       "stderr": (p.stderr or "")[-400:], "trace": None, "wall_s": None}
        except subprocess.TimeoutExpired:
            res = {"has_solve": None, "passed": False, "first_failure": {"msg": "overall timeout"}, "trace": None,
                   "wall_s": None}
    res["code_sha256"] = csha
    cf.parent.mkdir(parents=True, exist_ok=True)
    cf.write_text(json.dumps(res))
    return res


def combine(task: str, lab_rt: str, lab_ast: str) -> tuple[str | None, str]:
    cat = CATALOGUE[task]
    if lab_rt == lab_ast and lab_rt in cat:
        return lab_rt, "runtime+ast"
    if lab_rt == "unknown" and lab_ast == "other":
        return "other", "runtime+ast"
    return None, "judge_needed"


def label_text(task: str, text: str) -> dict:
    """Full label record for one sample text (without the judge)."""
    a = analyse_text(task, text)
    rec = {"text_sha256": sha256_text(text), "task": task, "format_ok": a["format_ok"], "enumerated": a["enumerated"],
           "names_mentioned": a["names_mentioned"], "n_python_blocks": a["n_python_blocks"],
           "code_from_bare_fence": a["code_from_bare_fence"]}
    if a["code"] is None:
        rec.update({"code": None, "code_sha256": None, "passed": False, "wall_s": None, "label": "no_code",
                    "labeller_source": "no_code", "label_runtime": None, "label_ast": None, "label_judge": None,
                    "first_failure": None, "needs_judge": False})
        return rec
    code = a["code"]
    res = run_code(task, code)
    al = ast_label(task, code)
    rt = runtime_label(task, res.get("trace") or {}, al.get("facts"))
    lab, src = combine(task, rt, al["label"])
    rec.update({"code": code, "code_sha256": sha256_text(code), "passed": bool(res.get("passed")),
                "wall_s": res.get("wall_s"), "first_failure": res.get("first_failure"),
                "has_solve": res.get("has_solve"), "exec_error": res.get("exec_error"),
                "trace_error": res.get("trace_error"), "label_runtime": rt, "label_ast": al["label"],
                "label_judge": None, "label": lab, "labeller_source": src, "needs_judge": lab is None,
                "trace_summary": summarise_trace(res.get("trace"))})
    return rec


def summarise_trace(tr: dict | None) -> dict | None:
    if not tr:
        return None
    keep = ("main_discipline", "n_heaps_pushed", "start_initiations", "heap_identifiable", "astar_frac",
            "greedy_frac", "dijkstra_frac", "two_fifo_frontiers", "goal_adjacent_early", "pop_monotone_frac",
            "fifo_reenqueue", "edge_passes", "n_bucket_containers", "max_self_calls")
    return {pid: {k: v for k, v in f.items() if k in keep} for pid, f in tr.items()}


def label_file(task: str, text: str) -> Path:
    return LABEL_CACHE / task / f"{sha256_text(text)}.json"


def label_and_store(task: str, text: str) -> dict:
    f = label_file(task, text)
    if f.exists():
        try:
            return json.loads(f.read_text())
        except json.JSONDecodeError:
            pass
    rec = label_text(task, text)
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_suffix(".tmp")
    tmp.write_text(json.dumps(rec))
    tmp.replace(f)
    return rec


(CACHE_DIR / "tmp").mkdir(parents=True, exist_ok=True)
