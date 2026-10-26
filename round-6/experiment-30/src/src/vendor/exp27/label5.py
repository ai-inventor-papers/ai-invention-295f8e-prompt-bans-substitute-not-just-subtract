#!/usr/bin/env python3
"""S6 label worker for the knob rows: exp19 label_worker_v4 (frozen bench and path labellers, blind judge on
disagreement only) following data/samples_raw.jsonl -> data/labels.jsonl until results/gpu_done.flag exists.
Judge sub-cap for labels USD 0.40 (path 0.25 + bench 0.15). The raw rows carry the LAST stage's text only, so the
labeller's first-python-block extraction reads the final code stage (plan S6)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import label_worker_v4 as LW
from cfg import DATA_DIR, RESULTS_DIR, setup_logging

LW.PATH_JUDGE_CAP = 0.25
LW.BENCH_JUDGE_CAP = 0.15
LW.N_WORKERS = 8

if __name__ == "__main__":
    setup_logging("label5")
    LW.run_worker(DATA_DIR / "samples_raw.jsonl", DATA_DIR / "labels.jsonl", RESULTS_DIR / "gpu_done.flag", chunk=40)
