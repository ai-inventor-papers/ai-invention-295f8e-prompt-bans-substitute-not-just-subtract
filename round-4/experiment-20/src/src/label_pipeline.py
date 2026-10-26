#!/usr/bin/env python3
"""STEP 10 - labelling (CPU, concurrent with the GPU): follows data/samples_raw.jsonl, writes data/labels.jsonl.

Same labellers as exp17 (src/label_worker.py), frozen:
- T1/T2: the exp8 canonical suite (inputs/exp8/suite): hidden tests + runtime probes (sandboxed subprocesses) ->
  runtime label (primary) and AST label (second) -> blind judge (openai/gpt-4.1-mini) only when they disagree.
- Bench tasks: exp11 bench/common/labeling.label_one (tests, AST, runtime trace) -> runtime label when runtime == AST
  or AST is 'unknown'; otherwise the frozen blind judge j1 (google/gemini-2.5-flash-lite).
Judge spend cap USD 0.40 (path 0.30, bench 0.10). A disagreement the judge could not resolve is 'unresolved' (its own
column; its fallback label is kept for sensitivity). 'invalid' = no code block, syntax error or no solve().
Judge caches start from exp17's caches (identical programs are not paid twice).
"""

from __future__ import annotations

import hashlib
import shutil
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from loguru import logger

from cfg import (BENCH, DATA_DIR, DEFAULT, E11, E17, EXP8_TASK, JUDGE_CAP_LABEL_USD, RESULTS_DIR, ROOT, SUITE,
                 append_jsonl, read_jsonl, setup_logging, sha256_text)

RAW = DATA_DIR / "samples_raw.jsonl"
LABELS = DATA_DIR / "labels.jsonl"
EVAL_CACHE: dict[str, dict[str, Any]] = {}
_LOCK = threading.Lock()
N_WORKERS = 4

for p in (str(SUITE), str(E11)):
    if p not in sys.path:
        sys.path.insert(0, p)


def row_key(r: dict[str, Any]) -> str:
    return f"{r['task']}|{r['template']}|{r['arm']}|{r['k']}"


def seed_caches() -> None:
    for name in ("judge_cache.jsonl", "judge_cache_paths.jsonl"):
        src, dst = E17 / "data" / name, DATA_DIR / name
        if src.exists() and not dst.exists():
            shutil.copy(src, dst)


# ------------------------------------------------------------------------------------------------ path tasks
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
    rec = {"passed": bool(t.get("passed")), "n_passed": t.get("n_passed"), "fail_case": t.get("fail_case"),
           "runtime_label": rl, "ast_label": al, "runtime_reason": str(rwhy)[:200], "ast_reason": str(awhy)[:200]}
    with _LOCK:
        EVAL_CACHE[k] = rec
    return rec


def label_path_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    import labeller.judge as J
    from labeller.combine import combine, needs_judge
    from labeller.extract import extract_code

    J.CACHE = DATA_DIR / "judge_cache_paths.jsonl"
    J.COST_FILE = RESULTS_DIR / "openrouter_cost_paths.json"
    items = []
    for r in rows:
        code, how = extract_code(r["text"])
        items.append({"task": EXP8_TASK[r["task"]], "code": code, "how": how})
    with ThreadPoolExecutor(N_WORKERS) as ex:
        mech = list(ex.map(lambda it: _path_mech(it["task"], it["code"]) if it["code"] else None, items))
    need = [i for i, (it, m) in enumerate(zip(items, mech)) if m and needs_judge(m["runtime_label"], m["ast_label"])]
    judged: dict[int, Any] = {}
    if need:
        try:
            res, _ = J.judge_many([{"task": items[i]["task"], "code": items[i]["code"]} for i in need],
                                  "openai/gpt-4.1-mini", "iter4_paths", JUDGE_CAP_LABEL_USD * 0.75)
            judged = {i: r for i, r in zip(need, res)}
        except Exception as e:  # noqa: BLE001 - judge failure -> 'unresolved', never a crash of the worker
            logger.error(f"path judge failed: {e}")
    out = []
    for i, (r, it, m) in enumerate(zip(rows, items, mech)):
        base = {"key": row_key(r), "task": r["task"], "template": r["template"], "arm": r["arm"], "k": r["k"]}
        if m is None:
            out.append({**base, "label": "invalid", "labeller_source": "no_code", "passed": False, "valid": False,
                        "runtime_label": None, "ast_label": None, "judge_label": None, "fallback_label": "invalid",
                        "code_sha256": None, "code": None})
            continue
        j = judged.get(i)
        if needs_judge(m["runtime_label"], m["ast_label"]) and not (j and j.get("label")):
            lab, src = "unresolved", "judge_unavailable"
            fb, _ = combine(m["runtime_label"], m["ast_label"], None)
        else:
            lab, src = combine(m["runtime_label"], m["ast_label"], j)
            fb = lab
        out.append({**base, "label": lab, "labeller_source": src, "passed": m["passed"], "valid": True,
                    "runtime_label": m["runtime_label"], "ast_label": m["ast_label"],
                    "judge_label": j.get("label") if j else None, "fallback_label": fb,
                    "code_sha256": sha256_text(it["code"]), "code": it["code"]})
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


def label_bench_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    import bench.common.judge as BJ
    from bench.common.harness import extract_code
    from bench.common.labeling import label_one

    BJ.PERSONAL_CAP = JUDGE_CAP_LABEL_USD * 0.25

    def one(r: dict[str, Any]) -> dict[str, Any]:
        row = {"sample_id": row_key(r), "task": r["task"], "condition": r["arm"], "mode": None,
               "paraphrase_id": r["template"], "round": None, "attempt_idx": None, "seed": r["uniform_seed"],
               "finish_reason": r["finish_reason"], "text": r["text"]}
        code = extract_code(r["text"])
        ck = f"{r['task']}|{sha256_text(code or '')}"
        with _LOCK:
            if ck in EVAL_CACHE:
                return {**EVAL_CACHE[ck], "sample_id": row["sample_id"]}
        lab = label_one(row, _bench_cases(r["task"]))
        lab.pop("trace", None)
        with _LOCK:
            EVAL_CACHE[ck] = lab
        return lab

    with ThreadPoolExecutor(N_WORKERS) as ex:
        labs = list(ex.map(one, rows))
    need = [i for i, l in enumerate(labs) if l.get("valid") and (
        l["runtime_label"] == "unknown" or (l["ast_label"] != "unknown" and l["ast_label"] != l["runtime_label"]))]
    jl: dict[int, Any] = {}
    if need:
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
        base = {"key": row_key(r), "task": r["task"], "template": r["template"], "arm": r["arm"], "k": r["k"]}
        if not l.get("valid"):
            lab, src, fb = "invalid", "extraction", "invalid"
        elif i in need:
            rec = jl.get(i) or {}
            fb = l["runtime_label"] if l["runtime_label"] != "unknown" else l["ast_label"]
            if rec.get("label"):
                lab, src = rec["label"], "judge"
            else:
                lab, src = "unresolved", "judge_unavailable"
        else:
            lab = l["runtime_label"]
            src = "runtime+ast" if l["ast_label"] == l["runtime_label"] else "runtime(ast_unknown)"
            fb = lab
        out.append({**base, "label": lab, "labeller_source": src, "passed": bool(l.get("passed")),
                    "valid": bool(l.get("valid")), "runtime_label": l.get("runtime_label"),
                    "ast_label": l.get("ast_label"), "judge_label": (jl.get(i) or {}).get("label"),
                    "fallback_label": fb, "n_pass": l.get("n_pass"), "n_cases": l.get("n_cases"),
                    "code_sha256": hashlib.sha256(code.encode()).hexdigest() if code else None, "code": code})
    return out


# ------------------------------------------------------------------------------------------------ worker
def label_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    path = [r for r in rows if r["task"] in EXP8_TASK]
    bench = [r for r in rows if r["task"] not in EXP8_TASK]
    out = []
    if path:
        out += label_path_rows(path)
    if bench:
        out += label_bench_rows(bench)
    for o in out:
        o["is_default"] = o["label"] == DEFAULT[o["task"]]
    return out


def run_worker(follow: bool = True, chunk: int = 40, stop_file: str = "sampling_done.json") -> None:
    seed_caches()
    t0 = time.time()
    n_total = 0
    while True:
        done = {r["key"] for r in read_jsonl(LABELS)}
        raw = [r for r in read_jsonl(RAW) if row_key(r) not in done]
        if raw:
            for i in range(0, len(raw), chunk):
                part = raw[i:i + chunk]
                tb = time.time()
                try:
                    out = label_rows(part)
                except Exception as e:  # noqa: BLE001 - log and retry the chunk on the next pass
                    logger.exception(f"labelling chunk failed: {e}")
                    time.sleep(5)
                    break
                append_jsonl(LABELS, out)
                n_total += len(out)
                logger.info(f"labelled {len(out)} rows ({part[0]['task']}/{part[0]['arm']} ...) in "
                            f"{time.time() - tb:.1f}s; total {n_total}; backlog {len(raw) - i - len(part)}")
        else:
            if not follow or (RESULTS_DIR / stop_file).exists():
                break
            time.sleep(15)
    logger.info(f"label worker finished: {n_total} rows in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    setup_logging("label_worker")
    run_worker(follow=(sys.argv[1] == "follow") if len(sys.argv) > 1 else True)
