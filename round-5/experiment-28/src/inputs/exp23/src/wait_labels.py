#!/usr/bin/env python3
"""Block until every row of the given raw files is labelled (data/labels.jsonl)."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg import DATA_DIR, read_jsonl

files = [DATA_DIR / f for f in sys.argv[1:]]
t0 = time.time()
while True:
    need = {r["row_id"] for f in files for r in read_jsonl(f)}
    have = {r["row_id"] for r in read_jsonl(DATA_DIR / "labels.jsonl")}
    miss = need - have
    if not miss:
        print(f"all {len(need)} rows labelled after {time.time() - t0:.0f}s")
        break
    if time.time() - t0 > 3600:
        print(f"timeout: {len(miss)} unlabelled")
        sys.exit(1)
    time.sleep(10)
