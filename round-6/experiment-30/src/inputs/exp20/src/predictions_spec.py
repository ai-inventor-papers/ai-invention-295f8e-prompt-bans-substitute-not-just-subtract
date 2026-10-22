#!/usr/bin/env python3
"""Writes predictions/predictions.json (commit #1): every prediction, decision rule and threshold, frozen before the
first decisive sample. Analysis code that is not yet written at commit #1 must implement exactly these rules."""

from __future__ import annotations

from cfg import DIR_DIR, PRED_DIR, RESULTS_DIR, UNITS_DIR, read_json, sha256_file, utc_now, write_json

PRED = {
    "C1_site": {"prediction": "S0 has the highest H5 on >= 4 of 6 tasks",
                "rule": "per task best site = argmax H5 (rounded 0.01) over S0-S5; ties -> lower P15 ('not reached' = "
                        "inf); remaining tie does not count for S0. CONFIRMED if count(S0 best) >= 4 of 6, raw p = "
                        "P(X >= count | Bin(6, 1/6)) (4 -> 0.0087), passed to the iteration's secondary Holm family; "
                        "DISCONFIRMED (generic perturbation) if one other site has H5 >= H5(S0) on >= 4 of 6; else "
                        "PARTIAL with the per-task table. Per task D_t = H5(S0) - max_other H5 with a bootstrap CI (max "
                        "inside replicates), P(S0 argmax) from the bootstrap, 0.10-Hill equivalence margin as "
                        "sensitivity. If whole tasks are dropped the threshold becomes >= two thirds of the remaining."},
    "S1": "'no movement' on >= 5 of 6 tasks (R is causally inert, F_R about 0)",
    "S2": "below S0 (H5) on >= 4 of 6; may move T05/T06",
    "S3": "more phrasing clusters per idea than S0 at matched alpha; little idea change; 'breakage first' by alpha 4",
    "S4": "'breakage first' at alpha >= 2",
    "S5": "'no movement' at alpha 1-2, breakage at alpha 4",
    "S1E_S2E": "breakage (pass < 0.8 x twin) on >= 4 of 6 tasks",
    "boundary": {"pass_lt_0.5_at_alpha8_on_ge4_of_6": True, "correct_only_hill_peaks_at_alpha": [2, 4],
                 "judge_confirmed_novel_algorithms": 0},
    "C3d": {"avoidance_of_TOP5_lt_0.5_at_alpha_le_2": True, "landing": "edge (BiBFS, adjacent to BFS) rather than "
            "the opposite side", "status": "descriptive (2 gated survivors: exact permutation p floor 0.5)"},
    "failure_mode_rule": {"moves": "correct-only excess >= 0.20 at some alpha with pass >= 0.8 x twin",
                          "moves_with_cost": "excess >= 0.10 only where pass < 0.8 x twin",
                          "breakage_first": "pass < 0.8 x twin or invalid >= 0.2 at an alpha where excess < 0.10",
                          "no_movement": "excess < 0.10 and pass >= 0.8 x twin at every alpha",
                          "precedence": "moves > moves_with_cost > breakage_first > no_movement"},
    "hull": {"settings": "twin (alpha 0), alpha 1, 2, 4 of one site", "grid": 0.05, "max_nonzero": 3,
             "depth": 25, "draws": 1000, "cost": "pass_twin - sum_j w_j pass_j", "H5": "max Hill(w), cost <= 0.05",
             "P15_P20": "min cost with Hill >= 1.5 / 2.0, else not reached",
             "bootstrap": "2,000 replicates (reduced to >= 500 only if CPU time forces it, logged), programs "
                          "resampled within cells stratified by template; hull max recomputed inside replicates "
                          "(200 draws, grid 0.1)",
             "sensitivity": ["linear interpolation along alpha", "S0 with alpha 8 appended"]},
    "measures": {"diversity": "correct-only, mechanism-labelled; 'other', 'invalid', 'unresolved' own columns; "
                              "rarefied Hill-1 at depth 25 (1,000 subsamples; own depth flagged if < 25 correct)",
                 "phrasing_clusters": "identifier-normalised AST 4-gram shingles, Jaccard connected components at "
                                      "theta 0.7/0.8/0.9, clusters per idea",
                 "paired_flips": "exact McNemar on off-default (all parseable attempts and correct-only), S0 vs each "
                                 "site over the 30 shared slots per (task, alpha); byte-identical code rates",
                 "transmission": "logistic GLM of correct-only off-default on log realised displacement at R "
                                 "(block 35) and separately log first-token KL, with site indicators and template and "
                                 "task fixed effects; S0 indicator CI excluding 0 -> site-specific beyond downstream "
                                 "dose; S3 analysed on its own step-wise KL",
                 "pooled": "mixed logistic off-default ~ site x log2(alpha) + (1|task) + (1|template) (descriptive)",
                 "engine_check": "see protocol_commit0.json"},
    "novelty_audit": {"pool": "every correct 'other' program from every arm", "stress_tests": 3,
                      "judges": "two blind judges from different families (exp18 ids) + tie-break model",
                      "claim": "'no correct novel algorithm' only at a count of 0 confirmed; rule of three 3/N"},
    "holm": "C1-site raw p enters the iteration's secondary Holm family (alongside the other secondary claims)",
}


def main() -> None:
    hw = read_json(RESULTS_DIR / "hardware.json")
    out = {"utc": utc_now(), "predictions": PRED,
           "slot_and_seed_scheme": {"slot": "(task, template, k); k 0-5 for N=30 cells, 0-9 for N=50 cells; smoke "
                                            "k >= 100; filler TWIN_X k >= 10",
                                    "uniforms": "u_stream(task, template, k) = PCG64(stable_seed(task, template, k))",
                                    "direction": "PCG64(stable_seed('PN4', task, template, k)).standard_normal(4096)",
                                    "batch": "20 rows of one (task, template), packed by priority"},
           "precision": hw["precision"], "units_sha256": read_json(UNITS_DIR / "units_sha256.json"),
           "u_top5_sha256": sha256_file(DIR_DIR / "u_top5.npz"),
           "screen_sha256": (RESULTS_DIR / "screen.sha256").read_text().strip(),
           "forced_prompts_T1_sha256": sha256_file(PRED_DIR / "forced_prompts_T1.json")}
    write_json(PRED_DIR / "predictions.json", out)


if __name__ == "__main__":
    main()
