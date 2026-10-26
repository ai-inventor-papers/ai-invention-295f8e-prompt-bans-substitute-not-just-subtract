#!/usr/bin/env python3
"""Label worker (CPU): follows data/raw_*.jsonl and appends one label row per sample to data/labels.jsonl.

Path tasks (T1/T2): the exp8 canonical suite: hidden tests + runtime probes (sandboxed subprocesses) -> runtime label
(primary) and AST label (second) -> the blind judge (openai/gpt-4.1-mini) only when they disagree or are unresolved.
Bench tasks (13): the frozen exp11 bench labeller (bench/common/labeling.label_one: hidden tests, AST, runtime
trace) -> runtime label when runtime == AST or AST is 'unknown'; on disagreement (or runtime 'unknown') the frozen
blind judge j1 (google/gemini-2.5-flash-lite). Unjudged disagreements are labelled 'disputed' (excluded from shares
as neither default nor avoidance; their fallback label is kept for a sensitivity). The labeller code is frozen
(copied byte-identical, sha256 in inputs/SHA256SUMS) and never edited.
"""

from __future__ import annotations

import hashlib
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg import (BENCH, DATA_DIR, EXP8_TASK, RESULTS_DIR, ROOT, append_jsonl, bench_paths, read_jsonl, setup_logging,
                 sha256_text)

bench_paths()
LABELS = DATA_DIR / "labels.jsonl"
EVAL_CACHE: dict[str, dict[str, Any]] = {}
_LOCK = threading.Lock()
N_WORKERS = 4
BENCH_JUDGE_CAP = 0.35
PATH_JUDGE_CAP = 0.25


def raw_files() -> list[Path]:
    return sorted(DATA_DIR.glob("raw_*.jsonl"))


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
    rec = {"passed": bool(t.get("passed")), "n_passed": t.get("n_passed"), "runtime_label": rl, "ast_label": al}
    with _LOCK:
        EVAL_CACHE[k] = rec
    return rec


def label_path_rows(rows: list[dict[str, Any]], judge: bool = True) -> list[dict[str, Any]]:
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
    if need and judge:
        try:
            res, stop = J.judge_many([{"task": items[i]["task"], "code": items[i]["code"]} for i in need],
                                     "openai/gpt-4.1-mini", "iter4_gemma_paths", PATH_JUDGE_CAP)
            judged = {i: r for i, r in zip(need, res) if r}
        except Exception as e:  # noqa: BLE001 - judge failure -> 'disputed', never a crash of the worker
            logger.error(f"path judge failed: {e}")
    out = []
    for i, (r, it, m) in enumerate(zip(rows, items, mech)):
        if m is None:
            out.append({"label": "invalid", "labeller_source": "no_code", "passed": False, "valid": False,
                        "runtime_label": None, "ast_label": None, "judge_label": None, "fallback_label": "invalid",
                        "code_sha256": None, "code": None})
            continue
        j = judged.get(i)
        if needs_judge(m["runtime_label"], m["ast_label"]) and not (j and j.get("label")):
            lab, src = "disputed", "judge_unavailable"
            fb, _ = combine(m["runtime_label"], m["ast_label"], None)
        else:
            lab, src = combine(m["runtime_label"], m["ast_label"], j)
            fb = lab
        out.append({"label": lab, "labeller_source": src, "passed": m["passed"], "valid": True,
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


def label_bench_rows(rows: list[dict[str, Any]], judge: bool = True) -> list[dict[str, Any]]:
    import bench.common.judge as BJ
    from bench.common.harness import extract_code
    from bench.common.labeling import label_one

    BJ.PERSONAL_CAP = BENCH_JUDGE_CAP

    def one(r: dict[str, Any]) -> dict[str, Any]:
        row = {"sample_id": r["row_id"], "task": r["task"], "condition": r["arm"], "mode": None,
               "paraphrase_id": r.get("template"), "round": None, "attempt_idx": None, "seed": r.get("seed", 0),
               "finish_reason": r.get("finish_reason"), "text": r["text"]}
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
    if need and judge:
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
            lab, src, fb = "invalid", "extraction", "invalid"
        elif i in need:
            rec = jl.get(i) or {}
            fb = l["runtime_label"] if l["runtime_label"] != "unknown" else l["ast_label"]
            if rec.get("label"):
                lab, src = rec["label"], "judge"
            else:
                lab, src = "disputed", "judge_unavailable"
        else:
            lab = l["runtime_label"]
            src = "runtime+ast" if l["ast_label"] == l["runtime_label"] else "runtime(ast_unknown)"
            fb = lab
        out.append({"label": lab, "labeller_source": src, "passed": bool(l.get("passed")),
                    "valid": bool(l.get("valid")), "runtime_label": l.get("runtime_label"),
                    "ast_label": l.get("ast_label"), "judge_label": (jl.get(i) or {}).get("label"),
                    "fallback_label": fb, "n_pass": l.get("n_pass"), "n_cases": l.get("n_cases"),
                    "code_sha256": hashlib.sha256(code.encode()).hexdigest() if code else None, "code": code})
    return out


# ------------------------------------------------------------------------------------------------ worker
KEEP = ("row_id", "task", "arm", "stage", "site", "alpha", "direction_seed", "template", "slot", "temperature",
        "top_k", "thinking", "prompt_sha256", "finish_reason", "n_new_tokens", "realised_disp", "pad", "batch_id",
        "model", "prompt_kind", "mode", "flag")


def label_rows(rows: list[dict[str, Any]], judge: bool = True) -> list[dict[str, Any]]:
    path = [r for r in rows if r["task"] in EXP8_TASK]
    bench = [r for r in rows if r["task"] not in EXP8_TASK]
    out = []
    if path:
        for r, l in zip(path, label_path_rows(path, judge)):
            out.append({**{k: r.get(k) for k in KEEP}, **l})
    if bench:
        for r, l in zip(bench, label_bench_rows(bench, judge)):
            out.append({**{k: r.get(k) for k in KEEP}, **l})
    return out


def run_worker(follow: bool = True, chunk: int = 48, stop_file: Path | None = None, judge: bool = True) -> None:
    t0 = time.time()
    n_total = 0
    while True:
        done = {r["row_id"] for r in read_jsonl(LABELS)}
        raw = [r for f in raw_files() for r in read_jsonl(f) if r["row_id"] not in done]
        if raw:
            for i in range(0, len(raw), chunk):
                part = raw[i:i + chunk]
                tb = time.time()
                try:
                    out = label_rows(part, judge)
                except Exception as e:  # noqa: BLE001 - log and retry the chunk on the next pass
                    logger.exception(f"labelling chunk failed: {e}")
                    time.sleep(5)
                    break
                append_jsonl(LABELS, out)
                n_total += len(out)
                logger.info(f"labelled {len(out)} rows ({part[0]['task']}/{part[0]['arm']} ...) in "
                            f"{time.time() - tb:.1f}s; total {n_total}; backlog {len(raw) - i - len(part)}")
        else:
            if not follow or (stop_file is not None and stop_file.exists()):
                break
            time.sleep(10)
    logger.info(f"label worker finished: {n_total} rows in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    setup_logging("label_worker")
    run_worker(follow="--once" not in sys.argv, stop_file=DATA_DIR / "STOP_LABELLER")
