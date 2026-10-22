#!/usr/bin/env python3
"""Label worker (CPU, overlapped with generation): ONE labeller version for every row of this artifact and for every
reused earlier row it is compared with.

Version = exp29's label_worker6: exp22's vendored label worker (exp8 suite for T1/T2: hidden tests + runtime probes ->
runtime label (primary), AST label (second); exp11 bench label_one for T10/T03/T05) + the iteration-5 exp28 re-gated
T2 array-Dijkstra rule applied to the T2 runtime and AST labels before combine(). A blind judge is called only on
runtime/AST disagreement (path judge <= USD 0.30 x 0.75 of the cap, bench <= 0.25 x the cap; identical programs are
never re-judged); the vendored judges stop at the first 'AI Inventor per-run OpenRouter budget' 403 and unjudged
disagreements become 'disputed' (counted as not-target, reported).

Sources it follows: data/raw/raw_k.jsonl (this artifact's instruct rows), data/raw/knobs_norm.jsonl (S3 knob rows
generated here with exp27's code) and data/raw/reuse_exp27.jsonl (exp27 rows re-labelled for the knob check and the
reused hull rows). Output: data/labels.jsonl keyed <task>|<template>|<arm>|<sample_id>.

usage: .venv/bin/python src/label_k.py [--once]
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from loguru import logger  # noqa: E402

import k_cfg as K  # noqa: E402
from k_cfg import DATA, DEFAULTS, LABELS, RAW_DIR, RESULTS, append_jsonl, read_jsonl, row_key  # noqa: E402

import cfg4  # noqa: E402,F401  (vendored; sets the src_base path)
import label_worker as LW  # noqa: E402  (vendored exp22 src_base/label_worker.py)
from regate_rules import apply_t2  # noqa: E402  (vendored exp28)

LW.JUDGE_CAP_USD = 0.40
LW.N_WORKERS = 8
_ORIG_PATH_MECH = LW._path_mech
SOURCES = ("raw_k.jsonl", "knobs_norm.jsonl", "reuse_exp27.jsonl")


def _path_mech_regate(task: str, code: str) -> dict[str, Any]:
    rec = dict(_ORIG_PATH_MECH(task, code))
    if task == "t2":
        rl, r1 = apply_t2(rec["runtime_label"], code)
        al, r2 = apply_t2(rec["ast_label"], code)
        rec.update(runtime_label_frozen=rec["runtime_label"], ast_label_frozen=rec["ast_label"], runtime_label=rl,
                   ast_label=al, regate_t2_applied=bool(r1 or r2))
    return rec


LW._path_mech = _path_mech_regate


# Judge caches and cost ledgers go to this artifact's data/, results/ and logs/ (never into vendor/): the vendored
# path labeller sets labeller.judge.CACHE / COST_FILE from these module globals at every call, and the bench judge
# object is created once with this artifact's root.
LW.DATA_DIR = DATA
LW.RESULTS_DIR = RESULTS


def label_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    import bench.common.judge as BJ

    BJ.PERSONAL_CAP = LW.JUDGE_CAP_USD * 0.25
    if "j" not in LW._JUDGE:
        LW._JUDGE["j"] = BJ.Judge(K.ROOT)
    path = [r for r in rows if r["task"] in LW.EXP8_TASK]
    bench = [r for r in rows if r["task"] not in LW.EXP8_TASK]
    out_p = LW.label_path_rows(path) if path else []
    out_b = LW.label_bench_rows(bench) if bench else []
    out = []
    for src, labs in ((path, out_p), (bench, out_b)):
        for r, l in zip(src, labs):
            l["key"] = row_key(r)
            l["source_file"] = r.get("_source")
            l["is_default"] = l["label"] == DEFAULTS[r["task"]]
            l["labeller_version"] = "exp22_label_worker+exp28_regate_t2 (exp29 label_worker6)"
            out.append(l)
    return out


def pending() -> list[dict[str, Any]]:
    done = {l["key"] for l in read_jsonl(LABELS)}
    rows = []
    for name in SOURCES:
        for r in read_jsonl(RAW_DIR / name):
            if r.get("text") is None:
                continue
            if row_key(r) not in done:
                r["_source"] = name
                if "seed" not in r:
                    r["seed"] = K.stable_seed(r["task"], r["template"], r["sample_id"])
                rows.append(r)
                done.add(row_key(r))
    # anchors and twins first (they gate decisions), then the rest in file order
    pri = {"S1_anchor": 0, "S0_check": 1, "S0_twin": 1}
    rows.sort(key=lambda r: pri.get(r.get("stage"), 2))
    return rows


def run(follow: bool = True, chunk: int = 48) -> None:
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
                logger.info(f"labelled {len(out)} ({part[0]['task']}/{part[0]['arm']}) in {time.time() - tb:.1f}s; "
                            f"total {n_total}; backlog {len(rows) - i - len(part)}")
                if stop.exists():
                    break
        else:
            if not follow or stop.exists():
                break
            time.sleep(10)
    logger.info(f"label worker finished: {n_total} rows in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    K.setup_logging("label_k")
    run(follow="--once" not in sys.argv)
