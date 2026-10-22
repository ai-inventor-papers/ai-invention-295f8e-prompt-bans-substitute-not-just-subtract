#!/usr/bin/env python3
"""COMMIT #0 -- written before the first decisive sample (any engine b/c/d row; engine-a REPRO rows are validation).
Fixes: E definition and rule, verdict table, the T2 feasibility reading (fixed from C4), the PN secondary reading,
predicted E per engine under each account, stage and drop order, N, slot-map and input hashes, and the hash of
src/escape.py (the committed escape code). The analysis/re-derivation code is committed by a later amendment before it
is run (logged deviation D-ANALYSIS-LATE); the decision rules below are the binding text."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from commit6 import commit  # noqa: E402
from c6 import PRED, RESULTS, read_json, sha256_file, utc_now, write_json, ROOT  # noqa: E402


def main() -> None:
    gates = read_json(RESULTS / "cpu_gates.json")
    assert gates["all_pass"], "CPU gates must pass before COMMIT #0"
    E4 = gates["C4"]["E_iter4_relabelled"]
    feas_tasks = [t for t in ("T10", "T2") if min(E4[t]["1.0"], E4[t]["2.0"]) < 0.3]
    c0 = {
        "utc": utc_now(),
        "claim": "E (PRIMARY): are iteration 4's random-push escapes a property of Qwen3-8B or of the FP8 W8A8 engine?",
        "engines": {"a": "W8A8 (iteration-4 engine; native torch._scaled_mm on this sm_89 card)",
                    "b": "W8A16", "c": "W16A8", "d": "BF16"},
        "E_definition": "E[e,t,alpha] = confirmed escapes / 40 directions (9101-9140) under exp22's two-stage rule "
                        "(src/escape.py), each engine scored against ITS OWN twin (N = 50, k 0-9 x W1-W5): screen at "
                        "N = 10 (k 0-1) excess >= 0.20 and pass >= 0.8 x twin pass; confirmed if pooled 30 (k 0-5) keeps "
                        "excess >= 0.20 with one-sided exact binomial p < 0.05 vs p0 = (k_twin + 0.5)/(n_twin + 1) and "
                        "pass >= 0.8 x twin. Wilson CIs.",
        "E_rule": "E_rule[e,t] = mean over alpha in {1,2} if alpha 1 exists for all four engines on t, else alpha 2 "
                  "for all.",
        "default_labels": {"T10": "union_find", "T2": "dijkstra", "T03": "full_sort"},
        "verdict_literal_primary": {
            "ACTIVATION_ROUNDING": "E(c)-E(d) >= 0.2, |E(a)-E(c)| <= 0.1, |E(b)-E(d)| <= 0.1 (both tasks for the claim)",
            "WEIGHT": "E(b)-E(d) >= 0.2",
            "INTERACTION": "E(a)-E(d) >= 0.2 while E(b)-E(d) < 0.1 and E(c)-E(d) < 0.1",
            "NOT_REPRODUCED_LOW": "E(a)-E(d) < 0.1 and E(a) < E_iter4_relabelled(a) - 0.15",
            "NOT_REPRODUCED_HIGH": "E(a)-E(d) < 0.1 and E(d) >= E_iter4_relabelled(a) - 0.15",
            "MIXED": "otherwise",
            "order": "first matching rule in the order ACTIVATION_ROUNDING, WEIGHT, INTERACTION, NOT_REPRODUCED_LOW, "
                     "NOT_REPRODUCED_HIGH, MIXED"},
        "feasibility_reading": {
            "tasks": feas_tasks,
            "rule": "for a task whose relabelled iteration-4 E(a) < 0.3, the ACTIVATION_ROUNDING clause E(c)-E(d) >= 0.2 "
                    "is replaced by E(c)-E(d) >= (2/3)(E(a)-E(d)) AND one-sided exact McNemar (c vs d, direction-paired "
                    "escape indicators) p < 0.05; reported BESIDE the literal verdict, which leads."},
        "pn_secondary_reading": "PN (exp19 per-sample plan noise, N = 50 per task x alpha in {1,2}, exp19 slots and "
                                "direction seeds, the same absolute unit n): off-default share per engine; CRN-paired "
                                "exact McNemar between engines; Fisher vs exp19's FP8 rows. Activation-rounding account "
                                "predicts share(c) ~ share(a) > share(b) ~ share(d).",
        "equivalence": "|x| <= 0.1 clauses are point estimates; 90% paired CIs and the formal TOST at margin 0.1 are "
                       "printed beside them; wording 'consistent with', never 'equivalent'.",
        "predictions": {
            "iteration4_relabelled_E_a": E4,
            "activation_rounding": "E(c) ~ E(a); E(b) ~ E(d) ~ 0",
            "weight_rounding": "E(b) ~ E(a); E(c) ~ E(d) ~ 0",
            "model_property": "E(a) ~ E(b) ~ E(c) ~ E(d) ~ iteration-4 values",
            "iteration4_as_published": {"T10": [0.375, 0.725], "T2": [0.175, 0.20]}},
        "design": {
            "tasks_decisive": ["T10", "T2"], "task_descriptive": "T03 (dropped first)",
            "directions": "rand_9101..rand_9140 (C1 bitwise), positive control rand_9004 on T2 (N = 20, k 0-3)",
            "N": {"twin": 50, "screen": 10, "confirm_extra": 20, "PN": 50},
            "unit": "absolute n[l,p] from exp22 ctx4.ban_unit (T10: exp13 norms; T2: exp17 norms), identical in "
                    "every engine",
            "batch": "B = 20 for weight set Q (a, b; exp22 numerics); B = largest that fits for weight set B (c, d; "
                     "bf16 weights fill 14.1 GiB of the 16 GiB card); B-sensitivity control: engine a re-run at the "
                     "weight-set-B batch size on the REPRO cells",
            "stage_order": ["REPRO (a, alpha 2, dirs 9101-9110 + twins; byte identity vs exp22)",
                            "S1/S2 d: twins + POP alpha 2 screen + confirmations + POSCTRL",
                            "S1/S3 c: same", "S4 PN alpha 1, 2 for d, c", "S1/S3/S4 b (weight set Q)",
                            "S5 alpha 1 (only if time)", "S6 mimic (only if time)", "S7 T03 (only if time)"],
            "drop_order": ["S7", "mimic", "S5 for b and c", "confirmation for b and c (screen-level E, flagged)"],
            "engine_a_reuse": "if REPRO shows byte identity with exp22 on its slots, exp22's own (relabelled) rows "
                              "are used for engine a on the remaining cells (they are the same engine on the same "
                              "slots); otherwise engine a is regenerated."},
        "hashes": {"slot_map": gates["C2"]["slot_map_sha256"],
                   "src/escape.py": sha256_file(ROOT / "src" / "escape.py"),
                   "inputs/MANIFEST.json": sha256_file(ROOT / "inputs" / "MANIFEST.json")},
    }
    write_json(PRED / "commit0.json", c0)
    e = commit("COMMIT #0 (before the first decisive sample)", c0,
               ["predictions/commit0.json", "predictions/slot_map.json", "src/escape.py", "inputs/MANIFEST.json",
                "results/cpu_gates.json", "results/relabel_iter4.json"])
    print(e)


if __name__ == "__main__":
    main()
