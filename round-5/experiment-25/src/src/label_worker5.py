#!/usr/bin/env python3
"""Label worker (CPU): follows data/raw/<task>.jsonl and appends one label row per sample to data/labels/<task>.jsonl.

Existing tasks (exp19 label_worker_v4 logic, unchanged): bench tasks -> exp11 bench.common.labeling.label_one
(hidden tests, AST, runtime trace) with the frozen blind judge j1 on runtime/AST disagreement; path tasks T1/T2 ->
the exp8 canonical suite with the gpt-4.1-mini judge on disagreement.
New units (newbench/<unit>): newbench/common/label5.label_program (hidden tests through the bench runner, runtime
label from the unit's frozen runtime rules, AST label) -> agree: label; disagree: blind judge (two-family pair,
newbench/common/judge5); judge unavailable or budget gone -> 'disputed' (excluded from the denominator).
A unit is labelled only once its labeller is frozen (newbench/<unit>/labeller.frozen exists).
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg5 import (BENCH, E11, EXISTING_DEFAULT, LAB_DIR, NEWBENCH, RAW_DIR, RESULTS, ROOT, SUITE, append_jsonl,  # noqa
                  read_jsonl, setup_logging, sha256_text, unit_dir, UNIT_DIRS)

EVAL_CACHE: dict[str, dict[str, Any]] = {}
_LOCK = threading.Lock()
N_WORKERS = 10
PATH_JUDGE_CAP = 0.30
BENCH_JUDGE_CAP = 0.30
EXP8_TASK = {"T1": "t1", "T2": "t2"}

for p in (str(SUITE), str(E11), str(ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)


# ------------------------------------------------------------------------------------------------ path tasks
def array_dijkstra(code: str | None) -> bool:
    """Style re-gate (plan Stage 0): array-based Dijkstra -- no heap / priority queue, and a linear min-scan over the
    unvisited nodes (min(..., key=...) over an unvisited container, or an index loop comparing dist values under a
    visited test) -- is labelled dijkstra, never bellman_ford_spfa."""
    import re

    if not code or re.search(r"heap|PriorityQueue|SortedList|bisect", code):
        return False
    vis = re.search(r"\b(visited|unvisited|seen|done|used|processed|settled|finalized|final)\b", code)
    minscan = re.search(r"min\(\s*\w+\s*,\s*key\s*=", code) or \
        re.search(r"(not\s+\w*(visited|seen|done|used|processed|settled)\w*\[\s*\w+\s*\]|\w+\s+not\s+in\s+\w*"
                  r"(visited|seen|done|used|processed|settled)\w*)\s+and\s+\(?\s*\w+\s*==\s*-1\s+or\s+\w*dist\w*\[", code) \
        or re.search(r"\w*dist\w*\[\s*\w+\s*\]\s*<\s*\w*(min|best|smallest)\w*", code)
    return bool(vis and minscan)


def _path_mech(task: str, code: str) -> dict[str, Any]:
    from labeller import ast_rules, runtime_rules
    from tasks.harness import evaluate_program

    k = f"{task}|{sha256_text(code)}"
    with _LOCK:
        if k in EVAL_CACHE:
            return EVAL_CACHE[k]
    ev = evaluate_program(task, code)
    t = ev["tests"]
    rl, rwhy, _ = runtime_rules.label(task, ev["probes"])
    al, awhy, _ = ast_rules.label(code, task)
    if task == "t2" and array_dijkstra(code):  # structural style re-gate (array-based Dijkstra)
        rl = al = "dijkstra"
        rwhy = awhy = "array-based Dijkstra (linear min-scan over unvisited nodes): structural re-gate rule"
    rec = {"passed": bool(t.get("passed")), "n_passed": t.get("n_passed"), "fail_case": t.get("fail_case"),
           "runtime_label": rl, "ast_label": al, "runtime_reason": str(rwhy)[:200], "ast_reason": str(awhy)[:200]}
    with _LOCK:
        EVAL_CACHE[k] = rec
    return rec


def label_path_rows(rows: list[dict[str, Any]], use_judge: bool = True) -> list[dict[str, Any]]:
    import labeller.judge as J
    from labeller.combine import combine, needs_judge
    from labeller.extract import extract_code

    J.CACHE = ROOT / "data" / "judge_cache_paths.jsonl"
    J.COST_FILE = RESULTS / "openrouter_cost_paths.json"
    items = []
    for r in rows:
        code, how = extract_code(r["text"])
        items.append({"task": EXP8_TASK[r["task"]], "code": code, "how": how})
    with ThreadPoolExecutor(N_WORKERS) as ex:
        mech = list(ex.map(lambda it: _path_mech(it["task"], it["code"]) if it["code"] else None, items))
    need = [i for i, (it, m) in enumerate(zip(items, mech)) if m and needs_judge(m["runtime_label"], m["ast_label"])]
    judged: dict[int, Any] = {}
    if need and use_judge:
        try:
            res, _stop = J.judge_many([{"task": items[i]["task"], "code": items[i]["code"]} for i in need],
                                      "openai/gpt-4.1-mini", "iter5_paths", PATH_JUDGE_CAP)
            judged = {i: r for i, r in zip(need, res)}
        except Exception as e:  # noqa: BLE001 - judge failure -> runtime label kept (flagged)
            logger.error(f"path judge failed: {e}")
    out = []
    for i, (r, it, m) in enumerate(zip(rows, items, mech)):
        if m is None:
            out.append({"label": "invalid", "labeller_source": "no_code", "passed": False, "valid": False,
                        "runtime_label": None, "ast_label": None, "judge_label": None, "code": None})
            continue
        j = judged.get(i)
        if needs_judge(m["runtime_label"], m["ast_label"]) and not (j and j.get("label")):
            fb, _ = combine(m["runtime_label"], m["ast_label"], None)
            lab, src = (fb if fb not in (None, "unknown", "unresolved") else (m["runtime_label"] or "other")), \
                "runtime_unjudged"
        else:
            lab, src = combine(m["runtime_label"], m["ast_label"], j)
        out.append({"label": lab, "labeller_source": src, "passed": m["passed"], "valid": True,
                    "runtime_label": m["runtime_label"], "ast_label": m["ast_label"],
                    "judge_label": j.get("label") if j else None, "code": it["code"]})
    return out


# ------------------------------------------------------------------------------------------------ bench tasks
_CASES: dict[str, list[dict[str, Any]]] = {}
_JUDGE: dict[str, Any] = {}


def _bench_cases(task: str) -> list[dict[str, Any]]:
    from bench.common.catalogue import TASKS
    from bench.common.testgen import read_tests

    if task not in _CASES:
        _CASES[task] = read_tests(BENCH / TASKS[task]["task_id"] / "tests.jsonl")
    return _CASES[task]


def label_bench_rows(rows: list[dict[str, Any]], use_judge: bool = True) -> list[dict[str, Any]]:
    import bench.common.judge as BJ
    from bench.common.harness import extract_code
    from bench.common.labeling import label_one

    BJ.PERSONAL_CAP = BENCH_JUDGE_CAP

    def one(r: dict[str, Any]) -> dict[str, Any]:
        row = {"sample_id": r["sample_id"], "task": r["task"], "condition": r["arm"], "mode": None,
               "paraphrase_id": r["template"], "round": None, "attempt_idx": None, "seed": 0,
               "finish_reason": r["finish_reason"], "text": r["text"]}
        code = extract_code(r["text"])
        ck = f"{r['task']}|{sha256_text(code or '')}"
        with _LOCK:
            if ck in EVAL_CACHE:
                return dict(EVAL_CACHE[ck])
        lab = label_one(row, _bench_cases(r["task"]))
        lab.pop("trace", None)
        with _LOCK:
            EVAL_CACHE[ck] = lab
        return dict(lab)

    with ThreadPoolExecutor(N_WORKERS) as ex:
        labs = list(ex.map(one, rows))
    need = [i for i, l in enumerate(labs) if l.get("valid") and (
        l["runtime_label"] == "unknown" or (l["ast_label"] != "unknown" and l["ast_label"] != l["runtime_label"]))]
    jl: dict[int, Any] = {}
    if need and use_judge:
        try:
            if "j" not in _JUDGE:
                _JUDGE["j"] = BJ.Judge(ROOT)
            recs = _JUDGE["j"].label_many([("j1", rows[i]["task"], extract_code(rows[i]["text"])) for i in need])
            jl = {i: rec for i, rec in zip(need, recs)}
        except Exception as e:  # noqa: BLE001
            logger.error(f"bench judge failed: {e}")
    out = []
    for i, (r, l) in enumerate(zip(rows, labs)):
        code = extract_code(r["text"])
        if not l.get("valid"):
            lab, src = "invalid", "extraction"
        elif i in need:
            rec = jl.get(i) or {}
            if rec.get("label"):
                lab, src = rec["label"], "judge"
            else:
                lab = l["runtime_label"] if l["runtime_label"] != "unknown" else (
                    l["ast_label"] if l["ast_label"] != "unknown" else "other")
                src = "runtime_unjudged"
        else:
            lab = l["runtime_label"]
            src = "runtime+ast" if l["ast_label"] == l["runtime_label"] else "runtime(ast_unknown)"
        out.append({"label": lab, "labeller_source": src, "passed": bool(l.get("passed")) and bool(l.get("valid")),
                    "valid": bool(l.get("valid")), "runtime_label": l.get("runtime_label"),
                    "ast_label": l.get("ast_label"), "judge_label": (jl.get(i) or {}).get("label"),
                    "n_pass": l.get("n_pass"), "n_cases": l.get("n_cases"), "code": code})
    return out


# ------------------------------------------------------------------------------------------------ new units
def label_new_rows(rows: list[dict[str, Any]], use_judge: bool = True) -> list[dict[str, Any]]:
    from newbench.common.label5 import label_many

    return label_many(rows, use_judge=use_judge, workers=N_WORKERS)


# ------------------------------------------------------------------------------------------------ worker
KEEP = ("task", "arm", "model", "template", "slot", "sample_id", "crn_key", "direction_seed", "alpha", "unit_kind",
        "site", "lambda", "temperature", "top_k", "thinking", "prompt_kind", "prompt_sha256", "precision", "max_new",
        "stop_rule", "block_id", "batch_B", "finish_reason", "n_new_tokens", "realised_disp", "utc")


def label_rows(rows: list[dict[str, Any]], use_judge: bool = True) -> list[dict[str, Any]]:
    path = [r for r in rows if r["task"] in EXP8_TASK]
    new = [r for r in rows if r["task"] in UNIT_DIRS]
    bench = [r for r in rows if r["task"] not in EXP8_TASK and r["task"] not in UNIT_DIRS]
    pairs = []
    if path:
        pairs += list(zip(path, label_path_rows(path, use_judge)))
    if bench:
        pairs += list(zip(bench, label_bench_rows(bench, use_judge)))
    if new:
        pairs += list(zip(new, label_new_rows(new, use_judge)))
    out = []
    for r, l in pairs:
        code = l.get("code")
        o = {k: r.get(k) for k in KEEP}
        o.update({k: v for k, v in l.items() if k != "code"})
        o["code"] = code
        o["code_sha256"] = hashlib.sha256(code.encode()).hexdigest() if code else None
        o["is_default"] = (o["label"] == EXISTING_DEFAULT.get(o["task"])) if o["task"] in EXISTING_DEFAULT else None
        out.append(o)
    return out


def frozen(task: str) -> bool:
    if task in UNIT_DIRS:
        return (unit_dir(task) / "labeller.frozen").exists()
    return True


def one_pass(raw_files: list[Path], chunk: int, use_judge: bool) -> int:
    n = 0
    for raw in raw_files:
        task = raw.stem
        if task == "enginecheck":
            out_p = LAB_DIR / "enginecheck.jsonl"
        else:
            out_p = LAB_DIR / f"{task}.jsonl"
            if not frozen(task):
                continue
        done = {r["sample_id"] for r in read_jsonl(out_p)}
        todo, seen = [], set()
        for r in read_jsonl(raw):
            if r["sample_id"] in done or r["sample_id"] in seen:
                continue
            if r["task"] in UNIT_DIRS and not frozen(r["task"]):
                continue
            seen.add(r["sample_id"])
            todo.append(r)
        for i in range(0, len(todo), chunk):
            part = todo[i:i + chunk]
            tb = time.time()
            try:
                out = label_rows(part, use_judge)
            except Exception as e:  # noqa: BLE001 - log and retry the chunk on the next pass
                logger.exception(f"labelling chunk failed ({task}): {e}")
                break
            append_jsonl(out_p, out)
            n += len(out)
            logger.info(f"labelled {len(out)} rows of {task} ({part[0]['arm']} ...) in {time.time() - tb:.1f}s; "
                        f"backlog {len(todo) - i - len(part)}")
    return n


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-judge", action="store_true")
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--tasks", default=None, help="comma-separated subset of tasks")
    args = ap.parse_args()
    setup_logging("label_worker")
    while True:
        files = sorted(RAW_DIR.glob("*.jsonl"))
        if args.tasks:
            keep = set(args.tasks.split(","))
            files = [f for f in files if f.stem in keep]
        # small files first so the escape screen of every task advances
        files.sort(key=lambda f: f.stat().st_size)
        n = one_pass(files, chunk=40, use_judge=not args.no_judge)
        if args.once:
            break
        if (ROOT / "queue" / "STOP_LABEL").exists():
            break
        if n == 0:
            time.sleep(10)


if __name__ == "__main__":
    main()
