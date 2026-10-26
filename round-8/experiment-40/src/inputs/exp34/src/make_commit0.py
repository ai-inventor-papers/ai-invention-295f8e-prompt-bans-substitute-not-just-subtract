#!/usr/bin/env python3
"""Commit #0: input hashes, thresholds, fork/margin/axis/predictor rules, stage and drop order, blindness rule.
Appends its sha256 to commitments.log (genesis = sha256('iter7_dir3'))."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from c7 import (COMMIT_LOG, GENESIS, IN20, IN29, IN30, PRED, ROOT, SEEDS40, SEEDS_T03, SEED_RAND_TARGET, SRC,  # noqa: E402
                    V9, V22, commit, sha256_file, utc_now, write_json)

RULES = {
    "outcome_y": "y_c = correct (passed hidden tests) programs whose frozen label is a non-default catalogue algorithm "
                 "/ N rows of the cell (invalid and 'other' count as not-target); attempted share = non-default "
                 "catalogue labels / N (pass or fail) reported beside it",
    "fork_detection": "per base path: outcome series k_t (continuations whose opening-classifier label differs from "
                      "the base path's class) / n_t at t in {0,4,...,60} inside the program, S = 8, CRN keys (task, "
                      "'fork', base_path_id, t, i); exp31 fork.change_points (exhaustive binomial segmentation, <= 2 "
                      "change points, 1000-permutation null), significant if p < 0.01; pooled per class; a change "
                      "between t1 and t1+4 is localised by sampling t1+1..t1+3 at S = 8 and confirmed at S = 20 at f, "
                      "f-1 and controls f-8, f+8",
    "fork_set": "f_1 = first change position on default paths (the shared opening o_t before it = modal default "
                "token sequence); a later change point along the default path that separates another non-default "
                "class is added as f_2 (multi-fork rule, at most 3 forks); no change in 64 tokens -> window 128 "
                "(every 8th token, 2 paths per class); still none -> the task's margin is the 48-token LLR",
    "token_map": "q_j(tok) = share of continuations starting with token tok at fork f_j whose final opening label is "
                 "non-default, pooled over the S = 20 confirmation runs (and screen runs at f_j) of all base paths; "
                 "tokens seen < 3 times are unmapped",
    "margin": "e_j = sum_tok p(tok) q_j(tok) / sum_{mapped} p(tok) from one teacher-forced pass over [prompt_v + "
              "cell prefill edit] + o_t[0:f_J]; P_esc = 1 - prod_j (1 - e_j); Pbar_c = equal-weight mean over "
              "templates (per sample for per-sample-edit cells); m_c = log Pbar_c - log(1 - Pbar_c) (nats)",
    "axis_layer": "a_L = unit(mean_i mean_j (h_forced_i[L,j] - h_pad_i[L,j])) over runner-up forced paraphrases "
                  "(prompts4 named F0-F9, display-name variant 0) and their ' .' padding twins; leave-one-out "
                  "sep(L) = mean_i d_i / sd_i d_i of the held-out S-mean projection difference; L_ax = argmax over "
                  "12..35 (ties -> smaller L); max sep < 2 -> L_ax = 20",
    "predictors": "(b)_L = mean_v mean_j delta_v(L,j).a_L / Dbar(L) (signed, in default-to-runner-up units); "
                  "(a) = mean_v ||U4^T dbar_v||^2/||dbar_v||^2 at L_ax; pi_Pt = mean_v ||P_t^T dbar_v||^2/"
                  "||dbar_v||^2; norm = mean_v ||dbar_v(L_ax)||; delta_v = h_push - h_twin at spec positions "
                  "(push_spec, ban_unit, alpha 2, blocks 12-23, prefill only); no outcome data",
    "F_test": "within-task Spearman(m, y) over the 40 POP alpha-2 cells, direction-permutation p (10,000); pooled "
              "within-task rho (Pearson of within-task ranks); tie ceiling rho_max reported; held-out logistic "
              "calibration MAE over 10 half-splits stratified by task x cell family (all cells); thresholds: rho >= "
              "0.5 on each task, pooled >= 0.6, p < 0.01, mean held-out MAE <= 0.10; disconfirming rho < 0.4 on both",
    "P2_test": "Spearman((b)_L_ax, y) per task with permutation p; paired bootstrap (10,000 direction resamples) of "
               "rho_b - rho_X for X in {pi_Pt, norm, (a)}, 'ahead' = lower 95% bound > 0 for all three; thresholds "
               "rho_b >= 0.5 on T10 and T2, p < 0.01, ahead of all three; disconfirming rho_b < 0.2",
    "holm": "Holm over {F, P2} within this artifact; raw p exported for the run-level Holm",
    "t03_confirmation": "24 fresh directions 97001-97024, N = 10 (W1-W5 x k 0,1), alpha 2, absolute T03 unit; "
                        "committed (b) and m vs y, one-sided permutation p, no refit; < 3 directions with y > 0 -> "
                        "uninformative (escape count and AUC reported)",
    "targeted_push": "single-layer edit at L_ax, spec positions, prefill only: h <- h + (s D(L_ax,j) - (h - h_twin).a)"
                     " a, s in {0.1,0.25,0.5,1}, N = 30 (W1-W5 x k 0-5); matched random r_t = rand_dir(98001 + task "
                     "index) with the same per-position magnitudes |s D|; escape = correct runner-up share - twin >= "
                     "0.20, exact one-sided binomial p < 0.05 vs the twin's off-default rate, pass >= 0.8 x twin pass;"
                     " pass if the smallest escaping s has rho_s <= 0.25 and the runner-up holds >= half of correct "
                     "off-default programs on >= 2 tasks; CRN McNemar axis vs random at each s",
    "clamp": "4 confirmed escapers with the largest y per task (T10, T2), N = 20 own CRN slots, clamp h <- h - ((h - "
             "h_twin).a_L) a_L at blocks L_ax..35 spec positions after the push; control: matched random unit "
             "direction; necessity supported if the axis clamp removes >= 50% of escapes and the random clamp <= 15%",
    "top5": "T1 band edit blocks 12-23, per position: Delta_l[j] = c_surv[l,j] - c_ban[l,j] (c_ban = mean of the five "
            "banned algorithms' forced centroids), u = unit(Delta_l[j]); h <- h + (s||Delta_l[j]|| - (h - h_twin).u)u;"
            " arms SURV (survivor-region centroid = mean of five survivor centroids), AWAY (u = unit(h_twin - c_ban))"
            ", RSURV (survivor X uniform per slot, seed stable_seed('T1','RSURV',w,k)), IDASTAR (s 0.5) at s in "
            "{0.25,0.5,1}, N = 30; landing scored on Isomap (k 5/10/15) geodesics of forced-prompt S-mean points: "
            "'edge' survivors = g(X) <= median; landing score = share of correct non-TOP5 programs on edge survivors",
    "blindness": "no POP_* outcome row (label, passed, code, text) of exp29 is opened before commit #3; "
                 "common.guarded_e29_rows refuses them until predictions/commit3_predictors.json exists",
    "stage_order": ["S setup", "commit0", "Stage 0 (twins, 5 POP directions unlabelled, realised norms)",
                    "F1 forks -> commit1", "axis -> commit2", "predictors + margins + LLR -> commit3",
                    "N.1-N.3 analysis", "T03 confirmation", "targeted push -> commit4 spec first",
                    "clamp (optional)", "top-five", "novelty audit", "outputs"],
    "drop_order": ["mediator clamp", "tier-3 margin cells", "T03 targeted push", "top-five AWAY and IDASTAR arms",
                   "P2 secondary DAS", "F opening-LLR sensitivity"],
}

THRESHOLDS = {"F": {"rho_each": 0.5, "rho_pooled": 0.6, "p": 0.01, "mae": 0.10, "disconfirm_rho": 0.4},
              "P2": {"rho_b": 0.5, "p": 0.01, "disconfirm_rho": 0.2},
              "fork": {"S_screen": 8, "S_confirm": 20, "positions": list(range(0, 64, 4)), "cp_p": 0.01,
                       "n_perm": 1000, "max_cp": 2, "unmapped_min_n": 3},
              "targeted": {"s": [0.1, 0.25, 0.5, 1.0], "N": 30, "excess": 0.20, "binom_p": 0.05, "pass_frac": 0.8,
                           "rho_s_max": 0.25},
              "clamp": {"axis_removed_min": 0.5, "random_removed_max": 0.15, "N": 20},
              "top5": {"s": [0.25, 0.5, 1.0], "N": 30, "isomap_k": [5, 10, 15]},
              "opening_classifier_agreement": 0.95,
              "engine_check": {"twin_agree": 0.95, "pop_agree": 0.8, "norm_rel": 0.02}}


def main() -> None:
    inputs = {}
    for p in sorted(list(IN29.glob("*")) + list(IN30.glob("*")) + list(IN20.glob("*"))):
        if p.is_file():
            inputs[str(p.relative_to(ROOT))] = sha256_file(p)
    for p in [V22 / "prompts" / "prompts4.jsonl", V9 / "prompts" / "frozen_prompts.json"]:
        inputs[str(p.relative_to(ROOT))] = sha256_file(p)
    code = {str(p.relative_to(ROOT)): sha256_file(p) for p in sorted(SRC.glob("*.py"))}
    obj = {"name": "commit0", "utc": utc_now(), "genesis": GENESIS, "inputs_sha256": inputs, "code_sha256": code,
           "rules": RULES, "thresholds": THRESHOLDS, "seeds": {"pop40": SEEDS40, "t03_fresh": SEEDS_T03,
                                                                "rand_target": SEED_RAND_TARGET},
           "note": "analysis drivers (analysis_f.py, analysis_p2.py, top5.py) are committed by hash in amendment "
                   "commit0b before commit #3 (deviation D-commit0: written after Stage 0 started; no outcome row "
                   "of any POP cell is readable before commit #3, enforced in code)"}
    p = PRED / "commit0.json"
    write_json(p, obj)
    ch = commit("commit0", p)
    print(f"commit0 -> {ch}")


if __name__ == "__main__":
    main()
