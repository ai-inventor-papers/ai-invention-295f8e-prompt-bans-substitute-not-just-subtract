#!/usr/bin/env python3
"""Label worker (CPU, overlapped with generation): ONE labeller version for every row of every engine.

Version = exp22's label worker (vendored src_base/label_worker.py, unchanged: exp8 suite for T2 -- hidden tests +
runtime probes -> runtime label (primary), AST label (second); exp11 bench label_one for T10/T03; a blind judge only
on disagreement) + the iteration-5 exp28 re-gated array-Dijkstra rule (vendored regate_rules.apply_t2) applied to the
T2 runtime and AST labels before combine(), exactly as exp28 layered it. Judge spend: path judge <= USD 0.30 and bench
judge <= USD 0.10 (exp22 split of JUDGE_CAP_USD 0.40); identical programs are never re-judged (exp22/exp17 caches);
the vendored judges stop at the first 'AI Inventor per-run OpenRouter budget' 403 and unjudged disagreements become
'disputed' (never counted as default or off-default).
Rows: data/labels.jsonl keyed <engine>|<task>|<template>|<arm>|<sample_id>.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from loguru import logger  # noqa: E402

import c6  # noqa: E402,F401
from c6 import DATA, DEFAULTS, LABELS, RAW_DIR, append_jsonl, read_jsonl, row_key, setup_logging  # noqa: E402

import cfg4  # noqa: E402,F401  (vendored; sets the src_base path)
import label_worker as LW  # noqa: E402  (vendored exp22 src_base/label_worker.py)
from regate_rules import apply_t2  # noqa: E402  (vendored exp28)

LW.JUDGE_CAP_USD = 0.40
LW.N_WORKERS = 4
_ORIG_PATH_MECH = LW._path_mech


def _path_mech_regate(task: str, code: str) -> dict[str, Any]:
    rec = dict(_ORIG_PATH_MECH(task, code))
    if task == "t2":
        rl, r1 = apply_t2(rec["runtime_label"], code)
        al, r2 = apply_t2(rec["ast_label"], code)
        rec.update(runtime_label_frozen=rec["runtime_label"], ast_label_frozen=rec["ast_label"], runtime_label=rl,
                   ast_label=al, regate_t2_applied=bool(r1 or r2))
    return rec


LW._path_mech = _path_mech_regate


def label_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    import bench.common.judge as BJ

    BJ.PERSONAL_CAP = LW.JUDGE_CAP_USD * 0.25
    path = [r for r in rows if r["task"] in LW.EXP8_TASK]
    bench = [r for r in rows if r["task"] not in LW.EXP8_TASK]
    out_p = LW.label_path_rows(path) if path else []
    out_b = LW.label_bench_rows(bench) if bench else []
    out = []
    for src, labs in ((path, out_p), (bench, out_b)):
        for r, l in zip(src, labs):
            l["key"] = row_key(r["engine"], r)
            l["engine"] = r["engine"]
            l["is_default"] = l["label"] == DEFAULTS[r["task"]]
            out.append(l)
    return out


def pending() -> list[dict[str, Any]]:
    done = {l["key"] for l in read_jsonl(LABELS)}
    rows = []
    for p in sorted(RAW_DIR.glob("raw_*.jsonl")):
        for r in read_jsonl(p):
            if row_key(r["engine"], r) not in done:
                rows.append(r)
    # screen and twin rows first (they gate the confirmation stage), then the rest in file order
    rows.sort(key=lambda r: (0 if r["arm"] == "TWIN" or (r["family"] == "POP" and int(r["sample_id"]) < 2) else 1))
    return rows


def run(follow: bool = True, chunk: int = 40) -> None:
    stop = DATA / "STOP_LABELLER"
    n_total, t0 = 0, time.time()
    while True:
        rows = pending()
        if rows:
            for i in range(0, len(rows), chunk):
                part = rows[i:i + chunk]
                tb = time.time()
                try:
                    out = label_rows(part)
                except Exception as e:  # noqa: BLE001 - log, back off, retry on the next pass
                    logger.exception(f"labelling chunk failed: {e}")
                    time.sleep(5)
                    break
                append_jsonl(LABELS, out)
                n_total += len(out)
                logger.info(f"labelled {len(out)} ({part[0]['engine']}/{part[0]['task']}/{part[0]['arm']}) in "
                            f"{time.time() - tb:.1f}s; total {n_total}; backlog {len(rows) - i - len(part)}")
        else:
            if not follow or stop.exists():
                break
            time.sleep(10)
    logger.info(f"label worker finished: {n_total} rows in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    setup_logging("label_worker6")
    run(follow="--once" not in sys.argv)
