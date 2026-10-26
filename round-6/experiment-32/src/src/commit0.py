#!/usr/bin/env python3
"""Commit #0 (before any sample): the design -- tasks, arms, N, positions, doses, thresholds, judge rubric v1 -- plus
the bench commitment check and the inputs' SHA256SUMS hash. (Run inline at 05:13 UTC in this artifact; this file is
the same code, kept for reproducibility -- commit() is idempotent per name.)"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg import (AV_ID, AV_REVISION, AR_ID, AR_REVISION, BENCH, CAUSAL_SLOTS, DOSES, FVE_PARTIAL, FVE_PASS,
                 FVE_REF_TARGET, GEN_POSITIONS, LAYER_CONVENTIONS, MODEL_ID, MODEL_REVISION, PAD_FILLER, ROOT, TASKS,
                 TEMPLATES, bench_dir, read_json, sha256_file)
from commit import commit


def main() -> dict:
    cm = read_json(BENCH / "commitment.json")
    bad, n = [], 0
    for t, rec in cm["tasks"].items():
        d = BENCH / bench_dir(t)
        for f, h in rec["files"].items():
            if f == "catalogue":
                continue
            n += 1
            if not (d / f).exists() or sha256_file(d / f) != h:
                bad.append(f"{t}/{f}")
    design = {
        "artifact": "iter6 gen_art_experiment_32: Reading the planned algorithm in words",
        "model": f"{MODEL_ID}@{MODEL_REVISION}", "av": f"{AV_ID}@{AV_REVISION}", "ar": f"{AR_ID}@{AR_REVISION}",
        "precision": "bf16 (no quantisation)",
        "engine": "HF generate + inverse-CDF CRN logits processor, T=1.0, top-p 1, no top-k, no repetition penalty; "
                  "max_new 1024 (T1/T2 1536); fence stop; eos {151645,151643}",
        "tasks": list(TASKS), "templates": TEMPLATES, "pad_filler": PAD_FILLER,
        "arms": {"TWIN": "W1-W5 x slots 0-9 (N=50)",
                 "BAN": "modal-ban of this model's default, W1-W5 x slots 0-9, CRN-paired with TWIN",
                 "FORCED": "5 paraphrases x 4 slots per catalogue mode (N=20)",
                 "SEED": "T2 semantic seed p0-p4 x slots 0-9 (N=50)", "NO_DEFAULT": "extra twin slots 10-19 instead of a ban"},
        "rules": {"default": "modal correct label with share >= 0.6 of correct programs, else NO DEFAULT",
                  "Ystar": "modal correct non-default label under the ban (W1-W5 pooled) with >= 50% of correct ban "
                           "programs and >= 10 programs, else BAN-FAILURE",
                  "mixed": "minority label >= 0.2 of correct programs -> 20 generated-token samples",
                  "adherent": "forced adherence (correct and labelled Y) >= 0.7"},
        "positions": {"READ": "P-1", "SPEC-1": "P-6", "SPEC-2": "P-7", "SPEC-3": "P-8", "generated": list(GEN_POSITIONS)},
        "layer": {"extraction": 20, "conventions": LAYER_CONVENTIONS,
                  "rule": "use hidden_states[20] unless FVE_ref with [21] is higher by >= 0.05"},
        "gate": {"PASS": FVE_PASS, "PARTIAL": [FVE_PARTIAL, FVE_PASS], "FAIL": f"< {FVE_PARTIAL}",
                 "pipeline_check": f"|FVE_ref(reference) - {FVE_REF_TARGET}| <= 0.10"},
        "doses": list(DOSES), "causal_N_per_cell": 30, "causal_slots": CAUSAL_SLOTS,
        "inputs_sha256sums": sha256_file(ROOT / "inputs" / "SHA256SUMS"),
        "bench_commitment_check": {"n_files": n, "mismatches": bad},
    }
    return commit("commit0_design", design)


if __name__ == "__main__":
    print(main())
