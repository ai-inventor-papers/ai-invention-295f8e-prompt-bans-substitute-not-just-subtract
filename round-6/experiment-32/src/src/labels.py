#!/usr/bin/env python3
"""Label worker (CPU), adapted from iteration-5 exp27 src/label_worker_v4.py with exp28's re-gated T2 rule.

Path tasks (T1/T2): the exp8 suite (inputs/exp8/suite): hidden tests + runtime probes in sandboxed subprocesses ->
runtime label (primary), AST label (second); for T2 the exp28 array-Dijkstra rule (regate_rules.apply_t2) is applied
to both before combining; a blind judge (openai/gpt-4.1-mini) only when they disagree. Bench tasks: exp11
bench.common.labeling.label_one (tests, AST, runtime trace) -> runtime label when runtime == AST or AST is 'unknown',
else the frozen blind judge j1 (google/gemini-2.5-flash-lite). The first HTTP 403 'AI Inventor per-run OpenRouter
budget' stops the batch (both judge modules implement it). An unjudged disagreement keeps its runtime label, flagged
labeller_source='runtime_unjudged'. 'other' and 'invalid' are labels of their own.

Usage: python src/labels.py --raw data/samples_raw.jsonl --out data/labels.jsonl [--follow-until FLAG]
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

from cfg import (BENCH, DATA_DIR, EXP8_TASK, RESULTS_DIR, ROOT, append_jsonl, bench_paths, read_jsonl,
                 setup_logging, sha256_text)

bench_paths()
EVAL_CACHE: dict[str, dict[str, Any]] = {}
_LOCK = threading.Lock()
N_WORKERS = 5
PATH_JUDGE_CAP = 0.30
BENCH_JUDGE_CAP = 0.30


# ------------------------------------------------------------------------------------------------ path tasks
def _path_mech(task: str, code: str) -> dict[str, Any]:
    from labeller import ast_rules, runtime_rules
    from regate_rules import apply_t2
    from tasks.harness import evaluate_program

    k = f"{task}|{sha256_text(code)}"
    with _LOCK:
        if k in EVAL_CACHE:
            return EVAL_CACHE[k]
    ev = evaluate_program(task, code)
    t = ev["tests"]
    rl, rwhy, _ = runtime_rules.label(task, ev["probes"])
    al, awhy, _ = ast_rules.label(code, task)
    rl0, al0, regate = rl, al, False
    if task == "t2":
        rl, r1 = apply_t2(rl, code)
        al, r2 = apply_t2(al, code)
        regate = r1 or r2
    rec = {"passed": bool(t.get("passed")), "n_passed": t.get("n_passed"), "fail_case": t.get("fail_case"),
           "runtime_label": rl, "ast_label": al, "runtime_label_frozen": rl0, "ast_label_frozen": al0,
           "regate_t2_applied": regate, "runtime_reason": str(rwhy)[:200], "ast_reason": str(awhy)[:200]}
    with _LOCK:
        EVAL_CACHE[k] = rec
    return rec


def label_path_rows(rows: list[dict[str, Any]], use_judge: bool = True) -> list[dict[str, Any]]:
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
    if need and use_judge:
        try:
            res, _stop = J.judge_many([{"task": items[i]["task"], "code": items[i]["code"]} for i in need],
                                      "openai/gpt-4.1-mini", "iter6_paths", PATH_JUDGE_CAP)
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
        if lab in (None, "unknown", "unresolved", "inconsistent"):
            lab = "other"
        out.append({"label": lab, "labeller_source": src, "passed": m["passed"], "valid": True,
                    "runtime_label": m["runtime_label"], "ast_label": m["ast_label"],
                    "runtime_label_frozen": m["runtime_label_frozen"], "ast_label_frozen": m["ast_label_frozen"],
                    "regate_t2_applied": m["regate_t2_applied"],
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
    (ROOT / "logs").mkdir(exist_ok=True)

    def one(r: dict[str, Any]) -> dict[str, Any]:
        row = {"sample_id": r["sample_id"], "task": r["task"], "condition": r["arm"], "mode": None,
               "paraphrase_id": r["template"], "round": None, "attempt_idx": None, "seed": r.get("u_seed", 0),
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
        if lab in (None, "unknown", "unresolved"):
            lab = "other"
        out.append({"label": lab, "labeller_source": src, "passed": bool(l.get("passed")) and bool(l.get("valid")),
                    "valid": bool(l.get("valid")), "runtime_label": l.get("runtime_label"),
                    "ast_label": l.get("ast_label"), "judge_label": (jl.get(i) or {}).get("label"),
                    "n_pass": l.get("n_pass"), "n_cases": l.get("n_cases"), "code": code})
    return out


# ------------------------------------------------------------------------------------------------ worker
KEEP = ("task", "arm", "cell", "template", "slot", "sample_id", "crn_key", "u_seed", "mode", "site", "alpha",
        "direction_seed", "temperature", "prompt_kind", "prompt_sha256", "model", "engine", "max_new", "batch_B",
        "finish_reason", "n_new_tokens", "realised_disp", "delta_norm_ratio", "edit_class", "state_ids", "utc")


def label_rows(rows: list[dict[str, Any]], use_judge: bool = True) -> list[dict[str, Any]]:
    path = [r for r in rows if r["task"] in EXP8_TASK]
    bench = [r for r in rows if r["task"] not in EXP8_TASK]
    pairs = []
    if path:
        pairs += list(zip(path, label_path_rows(path, use_judge)))
    if bench:
        pairs += list(zip(bench, label_bench_rows(bench, use_judge)))
    by_id: dict[str, dict[str, Any]] = {}
    for r, l in pairs:
        code = l.get("code")
        o = {k: r.get(k) for k in KEEP}
        o.update({k: v for k, v in l.items() if k != "code"})
        o["code"] = code
        o["code_sha256"] = hashlib.sha256(code.encode()).hexdigest() if code else None
        o["label_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        by_id[r["sample_id"]] = o
    return [by_id[r["sample_id"]] for r in rows]  # input order


def run_worker(raw: Path, out_p: Path, follow_until: Path | None = None, chunk: int = 40,
               use_judge: bool = True) -> None:
    t0 = time.time()
    n_total = 0
    final_pass = False
    while True:
        done = {r["sample_id"] for r in read_jsonl(out_p)}
        seen: set[str] = set()
        todo = []
        for r in read_jsonl(raw):
            if r["sample_id"] in done or r["sample_id"] in seen:
                continue
            seen.add(r["sample_id"])
            todo.append(r)
        if todo:
            for i in range(0, len(todo), chunk):
                part = todo[i:i + chunk]
                tb = time.time()
                try:
                    out = label_rows(part, use_judge)
                except Exception as e:  # noqa: BLE001 - log and retry the chunk on the next pass
                    logger.exception(f"labelling chunk failed: {e}")
                    time.sleep(5)
                    break
                append_jsonl(out_p, out)
                n_total += len(out)
                logger.info(f"labelled {len(out)} rows ({part[0]['task']}/{part[0]['arm']} ...) in "
                            f"{time.time() - tb:.1f}s; total {n_total}; backlog {len(todo) - i - len(part)}")
        else:
            if follow_until is None:
                break
            if follow_until.exists():
                if final_pass:
                    break
                final_pass = True
                time.sleep(3)
                continue
            time.sleep(8)
    logger.info(f"label worker finished: {n_total} rows in {time.time() - t0:.0f}s")


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default=str(DATA_DIR / "samples_raw.jsonl"))
    ap.add_argument("--out", default=str(DATA_DIR / "labels.jsonl"))
    ap.add_argument("--follow-until", default=None, help="keep following until this flag file exists")
    ap.add_argument("--no-judge", action="store_true")
    ap.add_argument("--name", default="label")
    args = ap.parse_args()
    setup_logging(args.name)
    run_worker(Path(args.raw), Path(args.out), Path(args.follow_until) if args.follow_until else None,
               use_judge=not args.no_judge)


if __name__ == "__main__":
    main()
