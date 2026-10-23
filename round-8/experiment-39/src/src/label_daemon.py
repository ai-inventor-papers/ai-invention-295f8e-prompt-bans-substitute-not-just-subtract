#!/usr/bin/env python3
"""Label daemon (CPU, separate process): follows data/samples.jsonl and data/continuations.jsonl and appends one label
row per program to data/labels.jsonl / data/continuation_labels.jsonl, using the frozen labellers through label7.py
(vendored unchanged from exp35: B3/B6 exp26 unitlib, A3 exp25 newbench, T1/T2/T10/T03 iteration-6 label_worker_v4;
the Gemma grid unit G is labelled with the T1 labeller). Rows whose program is only partial ('decided' locator
continuations) are labelled by the opening classifier instead (labeller_source 'oc_partial').
Stops when data/STOP_LABELLER exists and nothing is left to label.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg8 import (CONT_LABELS, CONTS, DATA_DIR, LABELS, SAMPLES, append_jsonl, label_task, read_jsonl,  # noqa: E402
                  setup_logging, utc_now)

import label7 as L7  # noqa: E402
import units8 as U8  # noqa: E402

STOP = DATA_DIR / "STOP_LABELLER"
CHUNK = 60


def _done(p: Path) -> set[str]:
    return {r["sid"] for r in read_jsonl(p)}


def label_batch(rows: list[dict]) -> list[dict]:
    full = [r for r in rows if r.get("finish_reason") != "decided"]
    part = [r for r in rows if r.get("finish_reason") == "decided"]
    out = []
    if full:
        inp = [{"sid": r["sid"], "unit": label_task(r["unit"]), "text": r["text"]} for r in full]
        res = L7.label_rows(inp)
        for r, o in zip(full, res):
            o = dict(o)
            o["unit"] = r["unit"]
            o["utc_label"] = utc_now()
            out.append(o)
    for r in part:
        lab = U8.classify_partial(r["unit"], r["text"])
        out.append({"sid": r["sid"], "unit": r["unit"], "label": lab, "labeller_source": "oc_partial",
                    "passed": None, "valid": None, "code": None, "utc_label": utc_now()})
    return out


def main() -> None:
    setup_logging("label_daemon")
    logger.info("label daemon started")
    idle = 0
    while True:
        work = 0
        for src, dst in ((SAMPLES, LABELS), (CONTS, CONT_LABELS)):
            done = _done(dst)
            todo = [r for r in read_jsonl(src) if r["sid"] not in done]
            for i in range(0, len(todo), CHUNK):
                part = todo[i:i + CHUNK]
                t0 = time.time()
                try:
                    res = label_batch(part)
                except Exception:  # noqa: BLE001 - a crashing batch is logged and its rows marked, never dropped
                    logger.exception("label batch failed; marking rows label_error")
                    res = [{"sid": r["sid"], "unit": r["unit"], "label": "label_error",
                            "labeller_source": "error", "passed": False, "valid": False, "code": None}
                           for r in part]
                append_jsonl(dst, res)
                work += len(part)
                logger.info(f"{dst.name}: labelled {len(part)} in {time.time() - t0:.1f}s")
        if work == 0:
            if STOP.exists():
                logger.info("STOP file present and nothing left: exiting")
                return
            idle += 1
            time.sleep(8)
        else:
            idle = 0


if __name__ == "__main__":
    main()
