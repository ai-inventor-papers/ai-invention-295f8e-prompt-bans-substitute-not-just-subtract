"""Labelling with the frozen exp11 bench labeller.

label_one (bench_copy/common/labeling.py): code extraction, hidden tests (10x-reference limits, sandboxed
subprocess), AST labeller and runtime-trace labeller.  Combined label (bench_copy/common/combine.py rule):
runtime when it agrees with AST or AST says 'unknown'; on disagreement (or runtime 'unknown') the blind judge j1
(google/gemini-2.5-flash-lite, name-scrubbed code, temperature 0, cached by code hash) decides; if the judge is
unavailable (cap or HTTP 403) the runtime label is used and the row is flagged judge_skipped.
"""

from __future__ import annotations

import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from loguru import logger

from .core import BENCH, DATA, JUDGE_SOFT_CAP, LOGS, ROOT, append_jsonl, ensure_bench_importable, read_jsonl, task_dir

ensure_bench_importable()
from bench_copy.common import judge as bench_judge  # noqa: E402
from bench_copy.common.harness import code_sha, extract_code  # noqa: E402
from bench_copy.common.labeling import label_one  # noqa: E402

bench_judge.PERSONAL_CAP = JUDGE_SOFT_CAP  # module global read at call time: stop new judge calls at USD 0.50

_CASES: dict[str, list[dict]] = {}
_CASES_LOCK = threading.Lock()


def cases_for(task: str) -> list[dict]:
    with _CASES_LOCK:
        if task not in _CASES:
            _CASES[task] = read_jsonl(task_dir(task) / "tests.jsonl")
        return _CASES[task]


def label_text(row: dict) -> dict:
    """row: {task, condition, sample_id, seed, text, finish_reason?} -> bench label_one output (+ timing)."""
    t0 = time.time()
    out = label_one({"task": row["task"], "condition": row.get("condition", "exposure"), "sample_id": row["sample_id"],
                     "seed": row.get("seed", 0), "text": row["text"], "finish_reason": row.get("finish_reason")},
                    cases_for(row["task"]))
    out["label_seconds"] = round(time.time() - t0, 3)
    return out


class LabelPool:
    """Background labelling of generated rows (threads; every label_one spawns sandboxed subprocesses)."""

    def __init__(self, out_path: Path, workers: int):
        self.out_path = out_path
        self.ex = ThreadPoolExecutor(max_workers=workers)
        self.futs = []
        self.done = {r["sample_id"] for r in read_jsonl(out_path)}
        self.lock = threading.Lock()
        self.n_done = 0

    def submit(self, rows: list[dict]) -> int:
        n = 0
        for r in rows:
            if r["sample_id"] in self.done:
                continue
            self.done.add(r["sample_id"])
            self.futs.append(self.ex.submit(self._one, r))
            n += 1
        return n

    def _one(self, r: dict) -> None:
        try:
            res = label_text(r)
        except Exception as e:  # noqa: BLE001 - record the failure as an invalid label, never drop the row
            logger.error(f"labelling failed for {r['sample_id']}: {e}")
            res = {"sample_id": r["sample_id"], "task": r["task"], "valid": False, "passed": False,
                   "ast_label": "invalid", "runtime_label": "invalid", "label_error": str(e)[:300],
                   "code_sha256": code_sha(extract_code(r["text"]))}
        append_jsonl(self.out_path, [res])
        with self.lock:
            self.n_done += 1

    def wait(self) -> None:
        for f in as_completed(self.futs):
            f.result()
        self.futs = []

    def pending(self) -> int:
        return sum(1 for f in self.futs if not f.done())

    def shutdown(self) -> None:
        self.wait()
        self.ex.shutdown(wait=True)


def label_many(rows: list[dict], workers: int, out_path: Path | None = None) -> list[dict]:
    res = [None] * len(rows)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(label_text, r): i for i, r in enumerate(rows)}
        for f in as_completed(futs):
            res[futs[f]] = f.result()
    if out_path is not None:
        append_jsonl(out_path, res)
    return res


def needs_judge(lab: dict) -> bool:
    if not lab.get("valid"):
        return False
    a, rt = lab.get("ast_label"), lab.get("runtime_label")
    return rt == "unknown" or (a != "unknown" and a != rt)


_JUDGE = None


def get_judge():
    global _JUDGE
    if _JUDGE is None:
        _JUDGE = bench_judge.Judge(ROOT)
    return _JUDGE


def judge_spend() -> float:
    p = LOGS / "openrouter_spend.jsonl"
    return sum((r.get("cost") or 0.0) for r in read_jsonl(p))


def combine(labs: list[dict], codes: dict[str, str], tasks: dict[str, str]) -> list[dict]:
    """labs: label_one outputs; codes: sample_id -> extracted code; tasks: sample_id -> task.  Returns labs with
    label / labeller_source / judge_label / judge_skipped filled (the frozen combine rule)."""
    need = [r for r in labs if needs_judge(r)]
    recs = {}
    if need:
        j = get_judge()
        items = [("j1", tasks[r["sample_id"]], codes[r["sample_id"]] or "") for r in need]
        logger.info(f"judge: {len(need)} disagreements (cache has {len(j.cache)} entries; spend so far ${j.spent:.4f})")
        out = j.label_many(items, concurrency=6)
        recs = {r["sample_id"]: rec for r, rec in zip(need, out)}
        if j.aborted:
            logger.warning("judge aborted (cap or budget); remaining disagreements take the runtime label")
    res = []
    for r in labs:
        r2 = dict(r)
        if not r.get("valid"):
            lab, src = "invalid", "extraction"
        elif r["sample_id"] in recs:
            rec = recs[r["sample_id"]]
            if rec.get("label"):
                lab, src = rec["label"], "judge"
            else:
                lab = r["runtime_label"] if r["runtime_label"] != "unknown" else r["ast_label"]
                src = "runtime_fallback" if r["runtime_label"] != "unknown" else "ast_fallback"
                r2["judge_skipped"] = True
        else:
            lab = r["runtime_label"]
            src = "runtime+ast" if r["ast_label"] == r["runtime_label"] else "runtime(ast_unknown)"
        r2["label"] = lab
        r2["labeller_source"] = src
        r2["judge_label"] = recs.get(r["sample_id"], {}).get("label")
        res.append(r2)
    return res


def openrouter_key_info() -> dict:
    """GET <base_url>/key (limit / usage of this phase's budget); errors are recorded, never fatal."""
    import requests
    base = os.environ.get("OPENROUTER_BASE_URL", "")
    try:
        r = requests.get(f"{base}/key", headers={"Authorization": f"Bearer {os.environ.get('OPENROUTER_API_KEY', '')}"},
                         timeout=20)
        info = {"status": r.status_code, "body": r.text[:500]}
    except Exception as e:  # noqa: BLE001
        info = {"status": None, "error": str(e)[:300]}
    logger.info(f"OpenRouter /key: {json.dumps(info)[:400]}")
    return info
