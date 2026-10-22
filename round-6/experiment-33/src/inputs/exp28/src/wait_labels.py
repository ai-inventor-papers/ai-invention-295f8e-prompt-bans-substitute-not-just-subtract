#!/usr/bin/env python3
"""Block until every row of the given raw files is labelled (data/labels.jsonl)."""

from __future__ import annotations

import sys
import time
from pathlib import Path

from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg import DATA_DIR, read_jsonl


def wait_for(raw_names: list[str], timeout_s: float = 3600.0, poll: float = 10.0) -> bool:
    t0 = time.time()
    while True:
        need = {r["row_id"] for n in raw_names for r in read_jsonl(DATA_DIR / n)}
        have = {r["row_id"] for r in read_jsonl(DATA_DIR / "labels.jsonl")}
        miss = need - have
        if not miss:
            logger.info(f"all {len(need)} rows of {raw_names} labelled")
            return True
        if time.time() - t0 > timeout_s:
            logger.warning(f"label wait timed out: {len(miss)} of {len(need)} unlabelled")
            return False
        time.sleep(poll)


if __name__ == "__main__":
    ok = wait_for(sys.argv[1:])
    sys.exit(0 if ok else 1)
