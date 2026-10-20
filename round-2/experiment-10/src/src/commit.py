#!/usr/bin/env python3
"""S0.9: hash-chained commitments (canon format: entry_hash = sha256(prev_entry_hash + sha + utc_time)). Written once,
before the first S5 score, for results/frozen_config.json and the frozen analysis/scoring code; later bug fixes are
appended as separate entries and logged as deviations."""

from __future__ import annotations

import json
import sys

from src.ws import WS, C, RESULTS, write_json
from loguru import logger

LOG = WS / "commitments.log"
FILES = ["results/frozen_config.json", "src/frlp.py", "src/analysis_c1.py", "src/run_analysis.py", "src/config.py"]


def append(path: str, note: str) -> dict:
    entries = C.read_jsonl(LOG)
    prev = entries[-1]["entry_hash"] if entries else "0" * 64
    sha = C.sha256_file(WS / path)
    t = C.utc_now()
    e = {"utc_time": t, "file": path, "sha": sha, "prev_entry_hash": prev, "entry_hash": C.sha256_text(prev + sha + t),
         "note": note}
    with LOG.open("a") as fh:
        fh.write(json.dumps(e) + "\n")
    return e


@logger.catch(reraise=True)
def main() -> None:
    note = sys.argv[1] if len(sys.argv) > 1 else "S0.9 freeze before the first S5 score"
    if note.startswith("freeze"):
        from src import config as K

        write_json(RESULTS / "frozen_config.json", K.frozen_config())
    for f in (sys.argv[2:] or FILES):
        print(append(f, note))


if __name__ == "__main__":
    main()
