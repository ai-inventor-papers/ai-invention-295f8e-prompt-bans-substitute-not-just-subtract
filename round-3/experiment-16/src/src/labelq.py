#!/usr/bin/env python3
"""Frozen labellers, used unchanged.

Bench tasks: exp11 bench/common/labeling.label_one (first ```python block -> hidden tests -> AST label ->
runtime-trace label); combined label = runtime when it agrees with AST or AST says 'unknown'; otherwise the frozen
blind judge j1 (bench/common/judge.py, google/gemini-2.5-flash-lite on name-scrubbed code) decides (combine.py rule).
Path tasks t1/t2: exp8's canonical suite labeller (runtime primary, AST second, gpt-4.1-mini judge on disagreement).

Labels depend only on (task, extracted code), so mechanical results and judge answers are cached by code hash.
The worker loop streams data/samples_raw.jsonl -> data/samples.jsonl while the GPU worker generates.
"""

from __future__ import annotations

import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from loguru import logger

from cfg import (BENCH, DATA_DIR, E8, EXP8_JUDGE_MODEL, INPUTS, JUDGE_CAP_USD, JUDGE_SOFT_USD, LABEL_ROOT, PATH_TASKS,
                 RAW, SAMPLES, STAGE_A, TASK_DIR, WORK_DIR, append_jsonl, default_of, read_jsonl, sha256_text)

if str(INPUTS) not in sys.path:
    sys.path.insert(0, str(INPUTS))
SUITE = E8 / "suite"
if str(SUITE) not in sys.path:
    sys.path.append(str(SUITE))

MECH_CACHE = DATA_DIR / "label_mech_cache.jsonl"
PATH_EVAL_CACHE = DATA_DIR / "path_eval_cache.jsonl"
PATH_PURPOSE = "exp16_bench_route"
_LOCK = threading.Lock()
_MECH: dict[str, dict[str, Any]] | None = None
_CASES: dict[str, list[dict]] = {}
_PATH_EVAL: dict[str, dict[str, Any]] | None = None


# ------------------------------------------------------------------------------------------------ bench
def bench_cases(task: str) -> list[dict]:
    from bench.common.testgen import read_tests

    if task not in _CASES:
        _CASES[task] = read_tests(BENCH / TASK_DIR[task] / "tests.jsonl")
    return _CASES[task]


def _mech_cache() -> dict[str, dict[str, Any]]:
    global _MECH
    if _MECH is None:
        _MECH = {r["key"]: r for r in read_jsonl(MECH_CACHE)}
    return _MECH


def bench_mechanical(task: str, text: str) -> dict[str, Any]:
    """label_one on a response text, cached by (task, extracted-code sha256)."""
    from bench.common.harness import extract_code
    from bench.common.labeling import label_one

    code = extract_code(text)
    key = f"{task}|{sha256_text(code) if code is not None else 'none'}"
    cache = _mech_cache()
    if key in cache:
        return cache[key]
    row = {"sample_id": key, "task": task, "condition": "route", "seed": 0, "text": text}
    out = label_one(row, bench_cases(task))
    rec = {"key": key, "task": task, "valid": bool(out.get("valid")), "passed": bool(out.get("passed")),
           "ast_label": out.get("ast_label"), "runtime_label": out.get("runtime_label"),
           "n_pass": out.get("n_pass"), "n_cases": out.get("n_cases"), "load_error": out.get("load_error"),
           "first_fail": out.get("first_fail"), "code": code}
    with _LOCK:
        cache[key] = rec
        append_jsonl(MECH_CACHE, [rec])
    return rec


class BenchJudge:
    """Thin wrapper around the frozen bench Judge with this artifact's cap (spend log under labelling/)."""

    def __init__(self) -> None:
        import bench.common.judge as jm

        jm.PERSONAL_CAP = JUDGE_CAP_USD
        self.jm = jm
        self.judge = jm.Judge(LABEL_ROOT)

    def spent(self) -> float:
        return float(self.judge.spent)

    def label(self, items: list[tuple[str, str]]) -> list[dict[str, Any]]:
        """items: [(task, code)] -> judge records (label None when unavailable)."""
        if not items:
            return []
        if self.judge.spent >= JUDGE_SOFT_USD:
            logger.warning(f"judge spend {self.judge.spent:.4f} >= soft cap {JUDGE_SOFT_USD}; continuing with the "
                           "cheapest frozen judge (j1) only, which is the only judge used here")
        recs = self.judge.label_many([("j1", t, c) for t, c in items], concurrency=4)
        # transient upstream failures (HTTP 429 etc.) are not cached by the frozen Judge: retry them with backoff
        for attempt in range(4):
            bad = [i for i, r in enumerate(recs) if not r.get("label") and r.get("error") not in ("budget", "aborted",
                                                                                              "personal cap reached")]
            if not bad or self.judge.aborted:
                break
            time.sleep(10 * (attempt + 1))
            logger.info(f"judge retry {attempt + 1}: {len(bad)} failed calls")
            again = self.judge.label_many([("j1", items[i][0], items[i][1]) for i in bad], concurrency=2)
            for i, r in zip(bad, again):
                recs[i] = r
        return recs


def combine_bench(m: dict[str, Any], judge_rec: dict[str, Any] | None) -> tuple[str, str]:
    if not m["valid"]:
        return "invalid", "extraction"
    a, rt = m["ast_label"], m["runtime_label"]
    if rt == "unknown" or (a != "unknown" and a != rt):
        if judge_rec is not None and judge_rec.get("label"):
            return str(judge_rec["label"]), "judge"
        return "disputed", "judge_unavailable"
    return str(rt), ("runtime+ast" if a == rt else "runtime(ast_unknown)")


def needs_judge_bench(m: dict[str, Any]) -> bool:
    if not m["valid"]:
        return False
    a, rt = m["ast_label"], m["runtime_label"]
    return rt == "unknown" or (a != "unknown" and a != rt)


def label_bench_texts(items: list[tuple[str, str]], judge: BenchJudge | None, workers: int = 4) -> list[dict]:
    """items: [(task, text)] -> label dicts in order."""
    with ThreadPoolExecutor(max_workers=workers) as ex:
        mech = list(ex.map(lambda it: bench_mechanical(it[0], it[1]), items))
    need = {}
    for (t, _), m in zip(items, mech):
        if needs_judge_bench(m) and m["key"] not in need:
            need[m["key"]] = (t, m["code"])
    jrec: dict[str, dict] = {}
    if need and judge is not None and judge.spent() < JUDGE_CAP_USD:
        keys = list(need)
        recs = judge.label([need[k] for k in keys])
        jrec = {k: r for k, r in zip(keys, recs)}
    out = []
    for (t, _), m in zip(items, mech):
        lab, src = combine_bench(m, jrec.get(m["key"]))
        out.append({"label": lab, "labeller_source": src, "passed": bool(m["passed"]) if m["valid"] else False,
                    "runtime_label": m["runtime_label"], "ast_label": m["ast_label"],
                    "judge_label": (jrec.get(m["key"]) or {}).get("label"), "valid": m["valid"],
                    "n_pass": m.get("n_pass"), "n_cases": m.get("n_cases"), "code": m["code"],
                    "code_sha256": sha256_text(m["code"]) if m["code"] is not None else None})
    return out


# ------------------------------------------------------------------------------------------------ path tasks
def _path_eval_cache() -> dict[str, dict[str, Any]]:
    global _PATH_EVAL
    if _PATH_EVAL is None:
        _PATH_EVAL = {r["key"]: r for r in read_jsonl(PATH_EVAL_CACHE)}
    return _PATH_EVAL


def path_extract(text: str) -> tuple[str | None, str]:
    from labeller.extract import extract_code

    return extract_code(text)


def _path_eval_one(task: str, code: str, key: str) -> dict[str, Any]:
    from labeller import ast_rules, runtime_rules
    from tasks.harness import evaluate_program

    cache = _path_eval_cache()
    if key in cache:
        return cache[key]
    ev = evaluate_program(task, code)
    t = ev["tests"]
    rl, rwhy, _ = runtime_rules.label(task, ev["probes"])
    al, awhy, _ = ast_rules.label(code, task)
    rec = {"key": key, "task": task, "passed": bool(t.get("passed")), "n_passed": t.get("n_passed"),
           "fail_case": t.get("fail_case"), "runtime_label": rl, "ast_label": al}
    with _LOCK:
        cache[key] = rec
        append_jsonl(PATH_EVAL_CACHE, [rec])
    return rec


def path_judge_spent() -> float:
    from labeller.judge import purpose_spent

    return float(purpose_spent(PATH_PURPOSE))


def label_path_texts(items: list[tuple[str, str]], use_judge: bool = True, workers: int = 4,
                     cap_usd: float = JUDGE_CAP_USD) -> list[dict]:
    """exp8's label_codes() rule on [(task, text)]: extract -> tests + probes -> runtime/AST -> judge -> combine."""
    from labeller.combine import combine, needs_judge
    from labeller.judge import judge_many

    codes = []
    for t, text in items:
        code, how = path_extract(text) if text is not None else (None, "no_code")
        codes.append((t, code, how))
    uniq = {}
    for t, code, _ in codes:
        if code is not None:
            k = f"{t}|{sha256_text(code)}"
            uniq.setdefault(k, (t, code))
    with ThreadPoolExecutor(max_workers=workers) as ex:
        evs = dict(zip(uniq.keys(), ex.map(lambda kv: _path_eval_one(kv[1][0], kv[1][1], kv[0]), uniq.items())))
    need = [{"task": uniq[k][0], "code": uniq[k][1], "key": k} for k, e in evs.items()
            if needs_judge(e["runtime_label"], e["ast_label"])]
    jmap: dict[str, Any] = {}
    if need and use_judge:
        judged, _stop = judge_many([{"task": n["task"], "code": n["code"]} for n in need], EXP8_JUDGE_MODEL,
                                   PATH_PURPOSE, cap_usd)
        jmap = {n["key"]: j for n, j in zip(need, judged)}
    out = []
    for t, code, how in codes:
        if code is None:
            out.append({"label": "no_code", "labeller_source": "no_code", "passed": False, "runtime_label": None,
                        "ast_label": None, "judge_label": None, "valid": False, "code": None, "code_sha256": None,
                        "extract_method": how})
            continue
        k = f"{t}|{sha256_text(code)}"
        e, j = evs[k], jmap.get(k)
        lbl, src = combine(e["runtime_label"], e["ast_label"], j)
        out.append({"label": lbl, "labeller_source": src, "passed": bool(e["passed"]), "runtime_label": e["runtime_label"],
                    "ast_label": e["ast_label"], "judge_label": j["label"] if j else None, "valid": True,
                    "code": code, "code_sha256": sha256_text(code), "extract_method": how})
    return out


# ------------------------------------------------------------------------------------------------ worker
def label_rows(rows: list[dict[str, Any]], judge: BenchJudge | None) -> list[dict[str, Any]]:
    bench_idx = [i for i, r in enumerate(rows) if r["task"] not in PATH_TASKS]
    path_idx = [i for i, r in enumerate(rows) if r["task"] in PATH_TASKS]
    labs: list[dict | None] = [None] * len(rows)
    if bench_idx:
        res = label_bench_texts([(rows[i]["task"], rows[i]["text"]) for i in bench_idx], judge)
        for i, r in zip(bench_idx, res):
            labs[i] = r
    if path_idx:
        res = label_path_texts([(rows[i]["task"], rows[i]["text"]) for i in path_idx])
        for i, r in zip(path_idx, res):
            labs[i] = r
    out = []
    for r, lab in zip(rows, labs):
        o = {k: v for k, v in r.items() if k not in ("text",)}
        o.update(lab or {})
        o["text"] = r["text"]
        o["is_default"] = (lab or {}).get("label") == default_of(r["task"])
        out.append(o)
    return out


def run_label_worker(poll_s: float = 20.0, chunk: int = 400) -> None:
    """Label new raw rows until work/gpu_done exists and every raw row is labelled."""
    judge = BenchJudge()
    done_flag = WORK_DIR / "gpu_done"
    labelled = {r["uid"] for r in read_jsonl(SAMPLES)}
    retried: set[str] = set()
    seen_lines = 0
    while True:
        raw = read_jsonl(RAW)
        todo = [r for r in raw if r["uid"] not in labelled]
        if not todo:
            # idle: re-judge rows left 'disputed' by transient judge failures (appended; readers take the last row)
            cur = {r["uid"]: r for r in read_jsonl(SAMPLES)}
            disp = [r for u, r in cur.items() if r.get("label") == "disputed" and u not in retried
                    and r["task"] not in PATH_TASKS]
            if disp:
                res = label_bench_texts([(r["task"], r["text"]) for r in disp], judge)
                fixed = []
                for r, lab in zip(disp, res):
                    retried.add(r["uid"])
                    if lab["label"] != "disputed":
                        o = dict(r)
                        o.update(lab)
                        o["is_default"] = lab["label"] == default_of(r["task"])
                        o["relabelled_after_judge_failure"] = True
                        fixed.append(o)
                if fixed:
                    append_jsonl(SAMPLES, fixed)
                logger.info(f"re-judged {len(disp)} disputed rows; {len(fixed)} resolved")
        if todo:
            t0 = time.time()
            for s in range(0, len(todo), chunk):
                part = todo[s:s + chunk]
                try:
                    out = label_rows(part, judge)
                except Exception:  # noqa: BLE001 - log and retry on the next poll
                    logger.exception("labelling chunk failed; will retry")
                    time.sleep(poll_s)
                    break
                append_jsonl(SAMPLES, out)
                labelled.update(r["uid"] for r in part)
                logger.info(f"labelled {len(part)} rows ({len(labelled)}/{len(raw)} total) in {time.time() - t0:.0f}s; "
                            f"bench judge spend ${judge.spent():.4f}, path judge spend ${path_judge_spent():.4f}")
        elif done_flag.exists() and len(raw) == seen_lines:
            logger.info("GPU done and all rows labelled; label worker exits")
            (WORK_DIR / "label_done").write_text(str(len(labelled)))
            return
        seen_lines = len(raw)
        time.sleep(poll_s)


def relabel_disputed() -> dict[str, Any]:
    """Final pass: re-judge bench rows left 'disputed' by transient judge failures; rewrites data/samples.jsonl."""
    rows = read_jsonl(SAMPLES)
    idx = [i for i, r in enumerate(rows) if r.get("label") == "disputed" and r["task"] not in PATH_TASKS]
    if not idx:
        return {"n_disputed": 0}
    judge = BenchJudge()
    res = label_bench_texts([(rows[i]["task"], rows[i]["text"]) for i in idx], judge)
    fixed = 0
    for i, lab in zip(idx, res):
        if lab["label"] != "disputed":
            fixed += 1
        rows[i].update(lab)
        rows[i]["is_default"] = lab["label"] == default_of(rows[i]["task"])
        rows[i]["relabelled_after_judge_failure"] = True
    from cfg import write_jsonl

    write_jsonl(SAMPLES, rows)
    logger.info(f"relabel_disputed: {fixed}/{len(idx)} resolved")
    return {"n_disputed": len(idx), "n_resolved": fixed}


def labelled_rows(filter_fn=None) -> list[dict[str, Any]]:
    rows = read_jsonl(SAMPLES)
    return [r for r in rows if filter_fn is None or filter_fn(r)]


if __name__ == "__main__":
    from cfg import setup_logging

    setup_logging("label_worker")
    run_label_worker()
    _ = (json, Path, STAGE_A)
