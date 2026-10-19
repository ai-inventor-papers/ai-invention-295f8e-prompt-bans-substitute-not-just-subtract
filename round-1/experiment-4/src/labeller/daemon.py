#!/usr/bin/env python3
"""Labelling daemon: watches data/raw/*.jsonl and labels every new sample text (tests + tracer + AST).

Runs concurrently with the GPU processes (6 sandbox workers). Also labels the 1024-token re-cut of
enumerate samples. Stops when logs/daemon.stop exists, or with --once after one full pass.
"""
from __future__ import annotations

import argparse
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import LOGS_DIR, RAW_DIR, read_jsonl, set_ram_limit, setup_logger  # noqa: E402
from labeller.label import label_and_store, label_file  # noqa: E402
from loguru import logger  # noqa: E402


def pending() -> list[tuple[str, str]]:
    todo, seen = [], set()
    for f in sorted(RAW_DIR.glob("*.jsonl")):
        for r in read_jsonl(f):
            for key in ("text", "text_1024"):
                if key not in r:
                    continue
                k = (r["task"], r[key])
                if k in seen:
                    continue
                seen.add(k)
                if not label_file(r["task"], r[key]).exists():
                    todo.append(k)
    return todo


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()
    setup_logger("label_daemon")
    set_ram_limit(12)
    stop = LOGS_DIR / "daemon.stop"
    n_done = 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        while True:
            todo = pending()
            if todo:
                t0 = time.time()
                futs = {ex.submit(label_and_store, t, x): (t, x) for t, x in todo}
                for fu in as_completed(futs):
                    try:
                        fu.result()
                        n_done += 1
                    except Exception:  # noqa: BLE001 - one bad sample must not stop the daemon
                        logger.exception(f"label failed for a {futs[fu][0]} sample")
                logger.info(f"labelled {len(todo)} samples in {time.time() - t0:.1f}s (total {n_done})")
            if args.once:
                break
            if stop.exists():
                logger.info("stop file found; exiting")
                break
            time.sleep(15)


if __name__ == "__main__":
    main()
