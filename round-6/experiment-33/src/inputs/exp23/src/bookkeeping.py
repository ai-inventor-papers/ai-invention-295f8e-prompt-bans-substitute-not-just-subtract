#!/usr/bin/env python3
"""Timing summary (results/timing_summary.json) from results/timing_batches.jsonl and the deviations log
(results/deviations.json)."""

from __future__ import annotations

import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg import RESULTS_DIR, read_jsonl, write_json

DEVIATIONS = {
    "D1_hardware": "The GPU is an RTX 2000 Ada (16 GB, 224 GB/s), not the planned A4500 (20 GB). The committed model "
                   "rule (gemma-2-9b-it only with >= 32 GB) selects gemma-3-4b-it bf16 as expected. Batch size is fixed "
                   "at B = 36 for every CRN batch (plan: 40 on 20 GB); the 72 Phase-A rows per (task, template) fill "
                   "exactly two batches. Caps from the pre-registered pilot rule: 640 new tokens (bench and T1/T2).",
    "D2_qwen_session": "Qwen3-8B (16.4 GB bf16) does not fit the 16 GB card: the ratio forward passes and the "
                       "forward-only positive control ran in bf16 with accelerate CPU offload of the overflow layers. "
                       "The optional generation positive control (3c) was dropped first, as planned.",
    "D3_push_unit": "PRIMARY UNIT CHANGED BEFORE COMMIT #1 (and before any ban prompt existed). In gemma-3-4b-it the 5 "
                    "largest channels carry 99% of ||h||^2 at spec positions (Qwen3-8B: 40%), so the committed unit "
                    "r_Q x ||h|| is ~8x larger than the Qwen push relative to the non-massive residual. A 24-row "
                    "ban-free calibration probe (results/unit_probe.json) showed alpha-1 pushes under that unit "
                    "erase the task (unrelated programs and prose), which makes the escape screen degenerate by "
                    "construction. The plan's own outlier-excluded variant was adopted as the primary unit: "
                    "n = r_Q,ox(d) x ||h_ox||, both norms with the 5 largest-|h| channels per position removed "
                    "(src/units.py). It was adopted without probing it (no tuning); the committed-plan unit is "
                    "reported as a diagnostic, and the ban-derived unit is reported after the bans.",
    "D4_pilot_uncoupled": "Pilot rows ran in multi-prompt batches with their own uniform keys (arm 'twin_pilot'), "
                          "reported and not pooled; the full twin is 10 CRN slots per template (N = 50).",
    "D5_default_rule": "Clarification committed in commit #1: D must be a catalogue mode with >= 3 correct programs "
                       "because the ban names D by its frozen display name. R6's modal correct twin label is "
                       "'linear_scan' (off-catalogue) -> D = X_q = binary_search, task flagged; C3a is also "
                       "reported without R6. The same rule is applied after the full twin (D_final).",
    "D6_uncoupled_engine": "'can', association and novelty use the same inverse-CDF sampler with per-row uniform "
                           "streams (multi-prompt batches: batch-1 prefill per distinct prompt, KV right-aligned with "
                           "masked zero pads) instead of HF generate; per-row seeding is exact.",
    "D7_suite_gold": "exp8 suite gold re-check: runtime accuracy 0.804 on its 92 eval items vs 0.843 in "
                     "gate_report.json (references 22/22). Not reproduced to the decimal; the suite labeller is used "
                     "unchanged; T1/T2 are covered by the label audit and the without-T1/T2 sensitivity.",
    "D8_N180": "The ban padding rows are slots 20-35 (B = 36), so the planned N = 200 sensitivity is N = 180.",
    "D9_holm": "Holm across the cross-artifact primary family cannot be computed here: the raw p and the "
               "Bonferroni bound min(1, 3p) are reported (as planned).",
    "D10_proximity_pairs": "Proximity uses up to 20 x 20 program pairs per survivor, subsampled to at most 120 "
                           "pairs (seeded) to bound CPU time.",
    "D11_c1_bootstrap": "C1 hull intervals use 100 bootstrap replicates (grid 11) instead of 2,000 because each "
                        "replicate runs a Monte-Carlo rarefaction; this affects only the descriptive C1 table.",
    "D13_t16_cell": "The plan's optional T 1.6 cell (N = 25 per movable task) was run after the bans (slack allowed); "
                    "it enters only the descriptive C1 temperature knob.",
    "D14_posthoc_T2": "POST HOC: the label audit (T2 agreement 1/4) and T2's 27% runtime/AST disagreement led to a "
                      "mechanism re-audit of all 374 T2 programs labelled bf_spfa (array-based Dijkstra read as "
                      "Bellman-Ford by the frozen suite labeller). Primary labels unchanged; C3a re-run reported as a "
                      "sensitivity (results/posthoc_t2_relabel.json).",
    "D12_disputed": "Unresolved runtime/AST disagreements ('disputed') are never counted as default, off-default or "
                    "avoidance; a sensitivity replaces them by their fallback labels.",
}


def main() -> None:
    rows = read_jsonl(RESULTS_DIR / "timing_batches.jsonl")
    by = collections.defaultdict(lambda: {"batches": 0, "seconds": 0.0, "rows": 0})
    for r in rows:
        k = r["stage"]
        by[k]["batches"] += 1
        by[k]["seconds"] += r["seconds"]
        by[k]["rows"] += r["B"]
    tot = sum(v["seconds"] for v in by.values())
    write_json(RESULTS_DIR / "timing_summary.json", {"by_stage": dict(by), "generation_gpu_hours": tot / 3600,
                                                     "note": "decode + prefill wall time of generation batches; "
                                                             "model loads, Qwen session and teacher forcing excluded"})
    write_json(RESULTS_DIR / "deviations.json", DEVIATIONS)
    print({k: round(v["seconds"] / 60, 1) for k, v in by.items()}, round(tot / 3600, 2))


if __name__ == "__main__":
    main()
