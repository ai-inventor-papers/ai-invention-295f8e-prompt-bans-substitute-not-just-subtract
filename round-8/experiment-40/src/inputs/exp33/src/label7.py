#!/usr/bin/env python3
"""Label worker of iteration 7: exp30's frozen labelling path unchanged (label_worker_v4 via label6: exp8 suite
labeller for T2, exp11 bench labeller for T10/T03; runtime tracer first, then AST, blind judge only on disagreement;
exp28's re-gated array-Dijkstra rule for T2). Follows data/samples_raw.jsonl -> data/labels.jsonl until
results/gpu_all_done.flag exists. Judge caps for labels: path USD 0.20 + bench USD 0.15 (this artifact's total
OpenRouter cap is USD 0.50); the first 403 'AI Inventor per-run OpenRouter budget' stops the batch."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import label6  # noqa: F401 - installs the T2 re-gate into label_worker_v4.label_rows
import label_worker_v4 as LW
from cfg import RESULTS_DIR, setup_logging
from cfg7 import LABELS7, SAMPLES7

LW.PATH_JUDGE_CAP = 0.20
LW.BENCH_JUDGE_CAP = 0.15
LW.N_WORKERS = 8
LW.KEEP = tuple(dict.fromkeys(LW.KEEP + (
    "cell", "stage", "slot_index", "base_key", "source_key", "Y_source", "layer", "rank_k", "lambda", "fit", "noun",
    "fam", "precision", "gpu", "P", "prompt_kind", "top_p", "realised_disp", "logprob_sum", "direction_seed")))

if __name__ == "__main__":
    setup_logging("label7")
    LW.run_worker(SAMPLES7, LABELS7, RESULTS_DIR / "gpu_all_done.flag", chunk=48)
