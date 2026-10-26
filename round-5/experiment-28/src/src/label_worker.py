#!/usr/bin/env python3
"""Label worker (CPU): follows data/raw_*.jsonl and appends one label row per sample to data/labels.jsonl.

Code extraction (both models): the first fenced block (python or any language; an unterminated last block counts)
that contains 'def solve'; else the bench's first ```python block; else the exp8 suite heuristics (raw text defining
solve); else 'no_code' (label 'invalid'). pt plain completion: program = 'def <signature>:\\n' + continuation cut at
the end of the function.
Path tasks (T1/T2): the exp8 canonical suite (hidden tests + runtime probes -> runtime label, AST label), then the
RE-GATE T2 rule (src/regate_rules.py: array-based Dijkstra -> 'dijkstra' ahead of the bf_spfa decision, in both
paths), then the blind judge (openai/gpt-4.1-mini) only when runtime and AST disagree or are unresolved.
Bench tasks (13): the frozen exp11 bench labeller (hidden tests, AST, runtime trace) -> runtime label when runtime ==
AST or AST is 'unknown'; on disagreement (or runtime 'unknown') the frozen blind judge j1 (gemini-2.5-flash-lite).
Unjudged disagreements are 'disputed' (never counted as default or off-default; fallback label kept). The frozen
labeller code is never edited; the re-gate rule is an explicit, logged layer on top of it.
"""

from __future__ import annotations

import hashlib
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg import (BENCH, DATA_DIR, EXP8_TASK, LOG_DIR, RESULTS_DIR, ROOT, append_jsonl, bench_paths, read_jsonl,
                 setup_logging, sha256_text)
from regate_rules import apply_t2

bench_paths()
LABELS = DATA_DIR / "labels.jsonl"
EVAL_CACHE: dict[str, dict[str, Any]] = {}
_LOCK = threading.Lock()
N_WORKERS = 5
BENCH_JUDGE_CAP = 0.60
PATH_JUDGE_CAP = 0.40
BLOCK_RE = re.compile(r"```[^\n`]*\n(.*?)(?:\n[ \t]*```|\Z)", re.S)
SOLVE_RE = re.compile(r"\bdef solve\s*\(")
PLAIN_KEEP = ("def ", "class ", "import ", "from ", "@", "#")


def raw_files() -> list[Path]:
    return sorted(DATA_DIR.glob("raw_*.jsonl"))


# ------------------------------------------------------------------------------------------------ extraction
def cut_plain(text: str) -> str:
    lines = text.split("\n")
    out = []
    body_seen = False
    for ln in lines:
        if ln.strip() and ln[0] not in (" ", "\t"):
            if ln.startswith("if __name__") or (body_seen and not ln.startswith(PLAIN_KEEP)):
                break
        elif ln.strip():
            body_seen = True
        out.append(ln)
    return "\n".join(out).rstrip() + "\n"


def extract5(r: dict[str, Any]) -> tuple[str | None, str]:
    text = r.get("text") or ""
    if r.get("arm") == "pt_plain":
        return (r.get("program_prefix") or "") + cut_plain(text), "plain_completion"
    for m in BLOCK_RE.finditer(text):
        b = m.group(1)
        if SOLVE_RE.search(b) and b.strip():
            return b.rstrip() + "\n", "fenced_solve"
    from bench.common.harness import extract_code as bench_extract

    c = bench_extract(text)
    if c and c.strip():
        return c.rstrip() + "\n", "bench_python_block"
    from labeller.extract import extract_code as suite_extract

    c2, how = suite_extract(text)
    if c2:
        return c2, f"suite_{how}"
    return None, "no_code"


# ------------------------------------------------------------------------------------------------ path tasks
def _path_mech(task: str, code: str) -> dict[str, Any]:
    from labeller import ast_rules, runtime_rules
    from tasks.harness import evaluate_program

    k = f"{task}|{sha256_text(code)}"
    with _LOCK:
        if k in EVAL_CACHE:
            return EVAL_CACHE[k]
    try:
        ev = evaluate_program(task, code)
    except Exception as e:  # noqa: BLE001 - a program that breaks the harness counts as failing, not a crash
        logger.warning(f"suite harness error: {type(e).__name__}: {str(e)[:120]}")
        ev = {"tests": {"passed": False, "error": f"harness_error: {type(e).__name__}"}, "probes": {"error": "crash"}}
    t = ev["tests"]
    rl, rwhy, _ = runtime_rules.label(task, ev["probes"])
    al, awhy, _ = ast_rules.label(code, task)
    rl0, al0 = rl, al
    regate = False
    if task == "t2":
        rl, r1 = apply_t2(rl, code)
        al, r2 = apply_t2(al, code)
        regate = r1 or r2
    rec = {"passed": bool(t.get("passed")), "n_passed": t.get("n_passed"), "runtime_label": rl, "ast_label": al,
           "runtime_label_frozen": rl0, "ast_label_frozen": al0, "regate_t2_applied": regate}
    with _LOCK:
        EVAL_CACHE[k] = rec
    return rec


def label_path_rows(rows: list[dict[str, Any]], codes: list[tuple[str | None, str]],
                    judge: bool = True) -> list[dict[str, Any]]:
    import labeller.judge as J
    from labeller.combine import combine, needs_judge

    J.CACHE = DATA_DIR / "judge_cache_paths.jsonl"
    J.COST_FILE = RESULTS_DIR / "openrouter_cost_paths.json"
    items = [{"task": EXP8_TASK[r["task"]], "code": c} for r, (c, _) in zip(rows, codes)]
    with ThreadPoolExecutor(N_WORKERS) as ex:
        mech = list(ex.map(lambda it: _path_mech(it["task"], it["code"]) if it["code"] else None, items))
    need = [i for i, m in enumerate(mech) if m and needs_judge(m["runtime_label"], m["ast_label"])]
    judged: dict[int, Any] = {}
    if need and judge:
        try:
            res, stop = J.judge_many([{"task": items[i]["task"], "code": items[i]["code"]} for i in need],
                                     "openai/gpt-4.1-mini", "iter5_gemma_paths", PATH_JUDGE_CAP)
            judged = {i: r for i, r in zip(need, res) if r}
        except Exception as e:  # noqa: BLE001 - judge failure -> 'disputed', never a crash of the worker
            logger.error(f"path judge failed: {e}")
    out = []
    for i, (r, it, m) in enumerate(zip(rows, items, mech)):
        if m is None:
            out.append({"label": "invalid", "labeller_source": "no_code", "passed": False, "valid": False,
                        "runtime_label": None, "ast_label": None, "judge_label": None, "fallback_label": "invalid",
                        "code_sha256": None, "code": None, "extract_how": codes[i][1]})
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
                    "runtime_label_frozen": m["runtime_label_frozen"], "ast_label_frozen": m["ast_label_frozen"],
                    "regate_t2_applied": m["regate_t2_applied"], "judge_label": j.get("label") if j else None,
                    "fallback_label": fb, "code_sha256": sha256_text(it["code"]), "code": it["code"],
                    "extract_how": codes[i][1]})
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


def label_bench_rows(rows: list[dict[str, Any]], codes: list[tuple[str | None, str]],
                     judge: bool = True) -> list[dict[str, Any]]:
    import bench.common.judge as BJ
    from bench.common.labeling import label_one

    BJ.PERSONAL_CAP = BENCH_JUDGE_CAP

    def one(args: tuple[dict[str, Any], str | None]) -> dict[str, Any]:
        r, code = args
        if code is None:
            return {"valid": False, "passed": False, "runtime_label": "invalid", "ast_label": "invalid"}
        ck = f"{r['task']}|{sha256_text(code)}"
        with _LOCK:
            if ck in EVAL_CACHE:
                return dict(EVAL_CACHE[ck])
        row = {"sample_id": r["row_id"], "task": r["task"], "condition": r["arm"], "mode": None,
               "paraphrase_id": r.get("template"), "round": None, "attempt_idx": None, "seed": 0,
               "finish_reason": r.get("finish_reason"), "text": "```python\n" + code + "\n```"}
        try:
            lab = label_one(row, _bench_cases(r["task"]))
        except Exception as e:  # noqa: BLE001 - e.g. the program prints a '{...}' line that breaks the frozen
            # harness's stdout protocol (json.loads on every line starting with '{'): a failing program, not a crash
            logger.warning(f"harness error on {r['row_id']}: {type(e).__name__}: {str(e)[:120]}")
            lab = {"valid": False, "passed": False, "runtime_label": "invalid", "ast_label": "invalid",
                   "harness_error": f"{type(e).__name__}: {str(e)[:200]}"}
        lab.pop("trace", None)
        with _LOCK:
            EVAL_CACHE[ck] = lab
        return dict(lab)

    with ThreadPoolExecutor(N_WORKERS) as ex:
        labs = list(ex.map(one, [(r, c) for r, (c, _) in zip(rows, codes)]))
    need = [i for i, l in enumerate(labs) if l.get("valid") and (
        l["runtime_label"] == "unknown" or (l["ast_label"] != "unknown" and l["ast_label"] != l["runtime_label"]))]
    jl: dict[int, Any] = {}
    if need and judge:
        try:
            if "j" not in _JUDGE:
                _JUDGE["j"] = BJ.Judge(ROOT)
            recs = _JUDGE["j"].label_many([("j1", rows[i]["task"], codes[i][0]) for i in need])
            jl = {i: rec for i, rec in zip(need, recs)}
        except Exception as e:  # noqa: BLE001
            logger.error(f"bench judge failed: {e}")
    out = []
    for i, (r, l) in enumerate(zip(rows, labs)):
        code = codes[i][0]
        if not l.get("valid"):
            lab, fb = "invalid", "invalid"
            src = "extraction" if code is None else ("harness_error" if l.get("harness_error") else "syntax")
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
                    "code_sha256": hashlib.sha256(code.encode()).hexdigest() if code else None, "code": code,
                    "extract_how": codes[i][1]})
    return out


# ------------------------------------------------------------------------------------------------ worker
KEEP = ("row_id", "task", "arm", "stage", "model", "model_kind", "site", "lambda", "alpha", "direction_seed",
        "dir_kind", "tkind", "template", "slot", "temperature", "top_k", "thinking", "precision", "prompt_sha256",
        "prompt_kind", "finish_reason", "n_new_tokens", "realised_disp", "pad", "batch_id", "utc")


def label_rows(rows: list[dict[str, Any]], judge: bool = True) -> list[dict[str, Any]]:
    path = [r for r in rows if r["task"] in EXP8_TASK]
    bench = [r for r in rows if r["task"] not in EXP8_TASK]
    out = []
    if path:
        codes = [extract5(r) for r in path]
        for r, l in zip(path, label_path_rows(path, codes, judge)):
            out.append({**{k: r.get(k) for k in KEEP}, **l})
    if bench:
        codes = [extract5(r) for r in bench]
        for r, l in zip(bench, label_bench_rows(bench, codes, judge)):
            out.append({**{k: r.get(k) for k in KEEP}, **l})
    return out


def run_worker(follow: bool = True, chunk: int = 60, stop_file: Path | None = None, judge: bool = True) -> None:
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
