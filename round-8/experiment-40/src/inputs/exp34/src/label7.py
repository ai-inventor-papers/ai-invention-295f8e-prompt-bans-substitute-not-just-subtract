#!/usr/bin/env python3
"""Label worker (CPU, overlapped with generation): the frozen labeller version of exp29 (engine-d rows) for every new
row, so new and old outcomes share one labeller:
  T2 / T1   exp8 suite (hidden tests + runtime probes -> runtime label; AST label second; blind judge only on
            disagreement) + exp28's re-gated array-Dijkstra rule on T2 (vendored regate_rules.apply_t2)
  T10 / T03 exp11 bench label_one (tests, AST, runtime trace; judge on disagreement)
  T1 extra  exp9 labeller_ext AST rules (10-algorithm grid catalogue: bfs dfs bibfs iddfs astar gbfs dijkstra_unit
            idastar jps biastar) -> 'label10'; the frozen 6-class exp8 label is kept as the cross-check
Rows: data/labels.jsonl keyed <task>|<template>|<arm>|<sample_id>. Judge spend cap USD 0.30 (first 'AI Inventor per-run
OpenRouter budget' 403 stops the batch; unjudged disagreements -> 'disputed').
usage: python src/label7.py [--once] [raw.jsonl labels.jsonl]
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from loguru import logger  # noqa: E402

import c7 as common  # noqa: E402
from c7 import DATA, DEFAULTS, LABELS, RAW, RESULTS, append_jsonl, read_jsonl, setup_logging  # noqa: E402

import cfg4  # noqa: E402,F401  (vendored; sets the src_base path)
import label_worker as LW  # noqa: E402  (vendored exp22 src_base/label_worker.py)
from regate_rules import apply_t2  # noqa: E402  (vendored exp28)

LW.JUDGE_CAP_USD = 0.30
LW.N_WORKERS = 6
LW.DATA_DIR = DATA
LW.RESULTS_DIR = RESULTS
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


def label10(code: str | None) -> tuple[str, str]:
    if not code:
        return "invalid", "no code"
    sys.path.insert(0, str(common.V9))
    from labeller_ext import ast_rules as AX
    try:
        lab, why, _ = AX.label(code, "t1")
    except Exception as e:  # noqa: BLE001 - a crash of the AST rules is an 'unknown' label, never a worker crash
        return "unknown", f"labeller_ext error: {e}"[:200]
    return lab, str(why)[:200]


def key(r: dict[str, Any]) -> str:
    return f"{r['task']}|{r['template']}|{r['arm']}|{r['sample_id']}"


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
            l["key"] = key(r)
            l["is_default"] = l["label"] == DEFAULTS[r["task"]]
            l["n_new_tokens"] = r.get("n_new_tokens")
            l["finish_reason"] = r.get("finish_reason")
            l["labeller_version"] = "exp29 label_worker6 (exp22 label_worker + exp28 T2 regate)"
            if r["task"] == "T1":
                l["label10"], l["label10_reason"] = label10(l.get("code"))
            out.append(l)
    return out


def pending(raw: Path, labels: Path) -> list[dict[str, Any]]:
    done = {l["key"] for l in read_jsonl(labels)}
    return [r for r in read_jsonl(raw) if key(r) not in done]


def run(raw: Path, labels: Path, follow: bool = True, chunk: int = 48) -> None:
    stop = DATA / "STOP_LABELLER"
    n_total, t0 = 0, time.time()
    while True:
        rows = pending(raw, labels)
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
                append_jsonl(labels, out)
                n_total += len(out)
                logger.info(f"labelled {len(out)} ({part[0]['task']}/{part[0]['arm']}) in {time.time() - tb:.1f}s; "
                            f"total {n_total}; backlog {len(rows) - i - len(part)}")
        else:
            if not follow or stop.exists():
                break
            time.sleep(10)
    logger.info(f"label worker finished: {n_total} rows in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    setup_logging("label7")
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    raw = Path(args[0]) if args else RAW
    labels = Path(args[1]) if len(args) > 1 else LABELS
    run(raw, labels, follow="--once" not in sys.argv)
