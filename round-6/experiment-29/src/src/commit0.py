#!/usr/bin/env python3
"""Commit #0 (Stage C): freeze predictions, thresholds, the attribution rule, outcome definitions, the consequence rule,
the drop order, the device rule, B, the gate rules and the sha256 of every input and analysis/engine file, BEFORE the
first decisive sample. Appends to the commitments.log hash chain."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg import sha256_file, utc_now, write_json
from cfg_e import PRED_DIR, RESULTS_DIR, ROOT
from commit_e import commit, verify

SRC = ROOT / "src"


def main() -> None:
    rule = json.loads((PRED_DIR / "device_rule.json").read_text())
    files = ["analysis_e.py", "qlinear.py", "hooks.py", "engine_e.py", "engine_v4.py", "sampling_v4.py", "dither.py",
             "run_e.py", "readouts.py", "label_e.py", "label_worker_v4.py", "cfg.py", "cfg_e.py"]
    c = {
        "utc": utc_now(),
        "claim": "E: the plan-noise movability measured in iteration 4 (FP8 W8A8 engine) is a property of the 8-bit "
                 "arithmetic, tested by a 2x2 weight-by-activation precision factorial on identical inputs",
        "predictions": {
            "W8A8_PN_a2_Y_correct_min": {"T10": 0.40, "T2": 0.30},
            "W8A8_PN_a2_inside_iter4_cp95": True,
            "W16A16_PN_a2_Y_correct_max": {"T10": 0.10, "T2": 0.10},
            "W8A8_minus_W16A16_min": {"T10": 0.25, "T2": 0.15},
            "mcnemar_exact_two_sided_p_max": 0.01,
            "disconfirming": "|W8A8 - W16A16| <= 0.10 on both tasks",
        },
        "outcome_definitions": {
            "Y_correct": "passed AND label not in {default, invalid} ('other' counted as off-default)",
            "Y_correct_catalogue_only": "passed AND label not in {default, invalid, other}",
            "Y_attempted": "label not in {default, invalid}",
            "defaults": {"T10": "union_find", "T2": "dijkstra", "T03": "full_sort"},
        },
        "verdict_rule": {"PRECISION EFFECT": "both T10 and T2: diff >= threshold and McNemar p < 0.01",
                         "PARTIAL": "one task", "NO PRECISION EFFECT": "|diff| <= 0.10 on both",
                         "AMBIGUOUS": "otherwise", "holm": "4-claim primary family: smallest p < 0.0125",
                         "backend": "verdict stated for EMU; REAL repeats the McNemar as the kernel check"},
        "attribution_rule": {"AME": "0.5*[(W8A8-W8A16)+(W16A8-W16A16)]", "WME": "0.5*[(W8A8-W16A8)+(W8A16-W16A16)]",
                             "INT": "(W8A8-W8A16)-(W16A8-W16A16)",
                             "ACTIVATION": "AME >= 0.20 and WME < 0.10 and AME slot-bootstrap 95% CI excludes 0",
                             "WEIGHT": "WME >= 0.20 and AME < 0.10 and WME CI excludes 0",
                             "INTERACTION": "W8A8-W16A16 >= threshold while W8A16-W16A16 < 0.10 and W16A8-W16A16 < 0.10",
                             "else": "MIXED", "scope": "PN_a2, per task, then pooled over T10+T2 stratified by task; "
                             "population check = same rule on per-direction mean shares of the 40 directions"},
        "consequence_rule": {
            "PRECISION EFFECT": "every iteration-4 internal claim (same-seed contrast, task-spec site, plan noise as the "
                                "cheapest knob, frozen screen) is written as a property of the FP8 W8A8 engine; the "
                                "effect is reported as a deployment finding, with the attribution class",
            "NO PRECISION EFFECT": "the unit cross locates the iteration-5 shrinkage; the iteration-4 claims are "
                                   "restored as model properties"},
        "gate_rules": {"REAL": "byte identity with exp19 on 25 TWIN + 25 PN_a1 slots when the card is the iteration-4 "
                               "type; on another sm_89 SKU (here L4) report the identity rate and apply the EMU criteria",
                       "EMU": "twin label agreement >= 0.9 on 25 T2 slots (W1 k0-9, W2 k0-9, W3 k0-4); PN_a2 shares "
                              "inside iteration 4's 95% CP intervals (correct-only like-for-like)",
                       "W16A16_anchor": "label agreement >= 0.9 with 25 exp27 TWIN slots (T10, W1-W5 k0-4)",
                       "failed_gate": "does not stop the factorial; the verdict is written as conditional on emulation"},
        "drop_order_time_only": ["dither (ii)", "dither (i)", "unit cross", "T03 under W8A16 and W16A8",
                                 "40 directions under W8A16/W16A8 down to N 5 (k 0 only)",
                                 "REAL T03 and REAL population cells"],
        "never_drop": ["engine check", "W8A8/W16A16/W8A16/W16A8 TWIN+PN (core) on T10 and T2",
                       "W8A8 and W16A16 40-direction arm (k 0-1)", "middle precisions' 40-direction arm at k 0",
                       "T03 under W8A8 and W16A16", "mechanism readouts", "novelty audit"],
        "device_rule": rule, "B": rule["B"],
        "sha256": {f: sha256_file(SRC / f) for f in files},
        "e_inputs_sha256": sha256_file(PRED_DIR / "e_inputs.json"),
        "tests": {"cpu_all_pass": json.loads((RESULTS_DIR / "tests_cpu.json").read_text())["all_pass"],
                  "gpu_all_pass": json.loads((RESULTS_DIR / "tests_gpu.json").read_text())["all_pass"]},
    }
    write_json(PRED_DIR / "e_commit.json", c)
    out = commit([PRED_DIR / "e_commit.json"] + [SRC / f for f in files] + [PRED_DIR / "device_rule.json",
                                                                           RESULTS_DIR / "tests_cpu.json",
                                                                           RESULTS_DIR / "tests_gpu.json"], "commit0")
    print(json.dumps({"commit0_utc": out[0]["utc"], "n_files": len(out), "verify": verify()}, indent=1))


if __name__ == "__main__":
    main()
