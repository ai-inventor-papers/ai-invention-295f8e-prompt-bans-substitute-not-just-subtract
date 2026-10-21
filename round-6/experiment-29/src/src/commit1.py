#!/usr/bin/env python3
"""Commit #1 (Stage D.4): gate outcomes (REAL vs exp19, EMU vs exp19 on the 25 T2 twin slots), per-step timing per
precision, the extrapolated total and any time-based drop decision, appended to the commitments.log chain."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np

import analysis_e as A
from cfg import read_jsonl, utc_now, write_json
from cfg_e import PRED_DIR, RESULTS_DIR
from commit_e import commit


def main() -> None:
    rows = A.merge_rows(out_p=None)
    idx = A.cell_index(rows)
    ec = A.engine_check(idx, rows)
    tim = read_jsonl(RESULTS_DIR / "timing_batches.jsonl")
    per_prec = {}
    for p in sorted({t["precision"] for t in tim}):
        ts = [t for t in tim if t["precision"] == p]
        per_prec[p] = {"n_batches": len(ts), "sec_per_batch_median": float(np.median([t["seconds"] for t in ts])),
                       "sec_per_step_median": float(np.median([(t["seconds"] - t["prefill_seconds"]) / t["steps"]
                                                               for t in ts]))}
    tests = json.loads((RESULTS_DIR / "tests_gpu.json").read_text())["U8_timing"]
    out = {"utc": utc_now(), "gate": {"REAL_vs_exp19": ec["REAL_vs_exp19"]["gate_25_TWIN"] | {
        "PN_a1": ec["REAL_vs_exp19"]["gate_25_PN_a1"]},
        "EMU_vs_exp19": ec["EMU_vs_exp19"]["gate_25_TWIN"] | {"PN_a1": ec["EMU_vs_exp19"]["gate_25_PN_a1"]},
        "EMU_gate_twin_label_agreement_ge_0.9": ec["EMU_gate_twin_label_agreement_ge_0.9"],
        "card_note": "NVIDIA L4 (sm_89) is not the iteration-4 card type (RTX 2000 Ada): byte identity is reported, "
                     "the EMU criteria (label agreement) apply to REAL as well"},
        "timing_per_precision": per_prec, "u8_timing": tests,
        "drops": read_jsonl(RESULTS_DIR / "drops.jsonl"),
        "extrapolation": "queue estimated at ~350 batches x ~20 s = ~2 h at B = 20; no drop expected"}
    write_json(PRED_DIR / "commit1_gate.json", out)
    c = commit([PRED_DIR / "commit1_gate.json"], "commit1")
    print(json.dumps({"commit1_utc": c[0]["utc"], "gate": out["gate"]}, indent=1))


if __name__ == "__main__":
    main()
