#!/usr/bin/env python3
"""STEP 11.10 overlap check, runnable later: looks for Step-1 rows (model Qwen3-8B, arm PN, alpha 4) in sibling
iteration-4 artifacts (<iter_4>/gen_art/*/data/samples.jsonl) and compares their per-task compositions with this
artifact's S0 alpha-4 compositions (JS divergence). Writes results/overlap_check.json."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from analysis import load_rows, overlap_check  # noqa: E402
from cfg import RESULTS_DIR, write_json  # noqa: E402

if __name__ == "__main__":
    res = overlap_check(load_rows())
    write_json(RESULTS_DIR / "overlap_check.json", res)
    print(res.get("status"), res.get("n_rows"))
