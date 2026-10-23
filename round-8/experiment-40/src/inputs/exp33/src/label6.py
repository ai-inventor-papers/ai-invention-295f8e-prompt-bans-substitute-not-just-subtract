#!/usr/bin/env python3
"""STEP 10 label worker: exp27's frozen labelling path (label_worker_v4: exp8 suite labeller for T1/T2, exp11 bench
labeller for the bench tasks; runtime tracer first, then AST, blind judge on disagreement only) following
data/samples_raw.jsonl -> data/labels.jsonl until results/gpu_all_done.flag exists. T2 rows additionally pass exp28's
re-gated array-Dijkstra rule (regate_rules.apply_t2: bf_spfa / unknown -> dijkstra when the program selects the
minimum-distance unvisited node by a linear scan and finalises it once). Judge cap for labels: USD 0.60 in total
(path 0.35 + bench 0.25); the first 403 'AI Inventor per-run OpenRouter budget' stops the batch (both judge modules)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import label_worker_v4 as LW
from cfg import DATA_DIR, RESULTS_DIR, setup_logging
from regate_rules import apply_t2

LW.PATH_JUDGE_CAP = 0.35
LW.BENCH_JUDGE_CAP = 0.25
LW.N_WORKERS = 5
LW.KEEP = LW.KEEP + ("cell", "band", "source", "slot_index", "dir_seed", "precision", "gpu", "dmd_T", "P",
                     "prompt_kind")
_orig = LW.label_rows


def label_rows6(rows, use_judge=True):
    out = _orig(rows, use_judge)
    for o in out:
        if o["task"] == "T2":
            lab, changed = apply_t2(o.get("label"), o.get("code"))
            if changed:
                o["label_pre_regate"] = o["label"]
                o["label"] = lab
                o["labeller_source"] = str(o.get("labeller_source")) + "+regate_t2"
                o["is_default"] = lab == "dijkstra"
    return out


LW.label_rows = label_rows6

if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "samples_raw"
    setup_logging(f"label6_{name}")
    LW.run_worker(DATA_DIR / f"{name}.jsonl", DATA_DIR / ("labels.jsonl" if name == "samples_raw" else
                                                          f"labels_{name}.jsonl"),
                  RESULTS_DIR / "gpu_all_done.flag", chunk=40)
