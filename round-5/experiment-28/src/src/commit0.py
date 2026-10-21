#!/usr/bin/env python3
"""COMMIT #0 (before ANY generation): protocol_E.json (every threshold, decision rule, seed, slot scheme, arm list and
drop order), the frozen analysis code (predictions/analysis_E.py = src/analysis_E.py), inputs/SHA256SUMS and
predictions/hardware.json are sha256 hash-chained in commitments.log."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cfg as C
from commit import commit, verify_chain
import analysis_E as A


def protocol() -> dict:
    return {
        "claim": "E (secondary): second-family REPLICATION of the narrowed-repertoire account on gemma-3-4b pt/it",
        "models": {"it": [C.IT_ID, C.IT_REV], "pt": [C.PT_ID, C.PT_REV], "pt_fallback": list(C.PT_FALLBACK),
                   "precision": C.PRECISION, "decoding": C.DECODING},
        "tasks": list(C.ALL_TASKS), "cyclic_order_donors": list(C.CYCLIC_ORDER),
        "band_blocks": C.BAND, "capture_blocks": C.CAPTURE_BLOCKS, "caps": {"bench": C.MAX_NEW_BENCH, "path": C.MAX_NEW_PATH,
                                                                          "pt_plain": C.MAX_NEW_PLAIN},
        "templates": C.TEMPLATES, "twin_x_exp23": C.EXP23_TWIN_X, "novelty_sentence": C.NOVELTY,
        "plain_prompt": "'<bos>\"\"\"' + description + '\\n' + 'Use only the Python standard library.' + '\"\"\"' + "
                        "'\\n\\n' + 'def ' + signature + ':' + '\\n'",
        "slots": {"uniforms": "PCG64(stable_seed('iter5E', task, template, k))",
                  "twin": "k=0..9 per template (N=50)", "stage1_escape": "k=0..1 per template (N=10)",
                  "confirmation": "k=2..5 per template (+20 -> N=30)", "pt_chat": "k=0..19 per template (N=100)",
                  "plan_noise": "k=0..9 per template per alpha (N=50 per alpha)",
                  "transplant": "k=0..9 per template (the twin's slots)",
                  "novelty": "PCG64(stable_seed('iter5E', task, 'NOV', k)), k=0..29",
                  "pt_plain": "PCG64(stable_seed('iter5E', 'plain', task, k)), k=0..49"},
        "directions": {"fresh_seeds": list(C.DIR_SEEDS), "construction": "unit(PCG64(seed).standard_normal(2560))",
                       "plan_noise": "unit(PCG64(stable_seed('iter5E_PN', task, alpha, template, k)).standard_normal(2560))",
                       "matched_random": "g = unit(PCG64(stable_seed('iter5E_RND', u, w, k)).standard_normal(2560) "
                                         "with channels M zeroed)"},
        "push": {"alphas": list(C.ALPHAS), "unit": "outlier-excluded ban-free unit n[l,p] = r_Q,ox((l+1)/34) x "
                                                   "||h_ox[l,p]|| (exp23 units.py, N_MASSIVE=5)",
                 "edit": "displacement-targeted: component of h - h_clean along u set to alpha n[l,p] at every band "
                         "block, task-spec positions, prefill only"},
        "escape_rule": {"excess": C.ESCAPE_EXCESS, "pass_frac": C.ESCAPE_PASS_FRAC, "binom_alpha": C.BINOM_ALPHA,
                        "p0_floor": C.P0_FLOOR, "primary_share": "off_cat (catalogue survivors over ALL attempts; "
                                                                 "'other' never counts as avoidance)",
                        "sensitivities": ["off_any (exp23 definition)", "off_corr (correct-only)", "E_u_max"],
                        "E_u": "mean over alphas of confirmed/16", "movable": "E_u > 0"},
        "predictors": {"default_rule": f"D_u = modal correct label (catalogue or named extended) with share >= "
                                       f"{C.DEFAULT_SHARE} among correct twin programs and >= {C.DEFAULT_MIN_CORRECT} "
                                       "correct (the 10-correct floor is a logged clarification); else NO_DEFAULT",
                       "beta": "pt correct programs with a catalogue label != D_u / correct programs with label != "
                               "disputed ('other' in the denominator only)",
                       "r_u": "argmax over catalogue minus D_u of pt correct count (ties: attempt count, then frozen "
                              "catalogue order)",
                       "low_correct": f"< {C.MIN_CORRECT_BASE} correct pt programs -> attempt composition, flagged",
                       "base_hill1": "rarefied Hill-1 at depth 25 (1,000 subsamples) over correct labels",
                       "q_base": "count_correct(y) + 0.5 over catalogue minus D_u; 'other' floor 0.02",
                       "classes": {"COLLAPSED": f"beta < {C.BETA_MOVABLE}", "DIVERSE": f"beta >= {C.BETA_DIVERSE}",
                                   "INTERMEDIATE": "otherwise"},
                       "pt_chat_validity_gate": "fewer than 8 defaulted units with >= 20 correct pt-chat programs -> "
                                                "primary beta/r/q pool pt-chat + pt-plain (flagged)",
                       "rivals": ["twin modal share (-)", "novelty-instruction catalogue off-default share (+)",
                                  "opening margin D vs r_u (-)", "merit gap: median runtime ratio r_u/D (-)",
                                  "merit gap: token-length ratio r_u/D (-)"]},
        "transplant": {"S_T": "defaulted units with beta >= 0.2 (if < 3: beta >= 0.05, DESCRIPTIVE)",
                       "S_C": "up to 3 COLLAPSED units with the highest twin pass rate",
                       "lambda": C.LAMBDA, "validity_switch": "T at N=10 per S_T task first; pass < 0.8 x twin on "
                                                              "more than half of S_T -> lambda 0.5 for T, RND, XT; "
                                                              "still broken -> UNTESTED",
                       "arms": {"T": "h <- h + lam (h_pt - h) at spec positions of blocks 11-22 (prefill)",
                                "RND": "v = lam (d_M + ||d_ox|| g), displacement-targeted",
                                "XT": "v = lam (d_M + ||d_ox|| m_hat_donor[l]), displacement-targeted",
                                "RP": "T at position R only", "S_C": "T only"},
                       "massive_set_M": "union of the top-5 |h| channels at spec positions of the it twin over "
                                        "blocks 11-22, frozen at commit #1"},
        "decision_rules": {
            "E_A1": "CONFIRMED iff rho >= 0.5 and one-sided permutation p < 0.01 and >= 80% of COLLAPSED units "
                    "immovable and beta ahead of every rival (paired task bootstrap 90% CI lower bound > 0); "
                    "DISCONFIRMED iff rho < 0.3 or most DIVERSE units have E_u == 0; PARTIAL iff rho >= 0.5 and "
                    "p < 0.05 but another criterion fails; INCONCLUSIVE otherwise or if < 4 units have beta >= 0.05",
            "E_A2": "events = MOVABLE units with beta >= 0.05 and a defined landing; PASS iff hit rate (r_u == "
                    "landing) >= 0.7 and exact Poisson-binomial p < 0.05 vs chance 1/(K_u-1); log-score contest "
                    "base vs association >= 0.10 nats (one-sided paired Wilcoxon p < 0.05; descriptive with < 5 "
                    "matched events); DISCONFIRMED iff hit rate <= mean chance",
            "transplant": "per S_T unit: exact one-sided McNemar on CRN slots (correct off-default) T vs RND and T vs "
                          "XT, Holm across tasks; supports iff T valid, s_T >= 0.5 beta, beats RND (or "
                          "norm-confounded) and XT, lands on r_u; controls: COLLAPSED and RP within 0.05 of the twin",
            "thresholds": A.THRESH},
        "drop_order": ["transplant arm (RP and collapsed controls first, then XT, then T/RND)",
                       "pt plain-completion arm (only if the chat validity gate passed)",
                       "16 -> 12 fresh directions (seeds 52001-52012)", "PN alpha 2"],
        "never_drop": ["style re-gate", "twins", "pt-chat repertoire with commit #1",
                       "fresh push population with confirmation", "novelty audit"],
        "openrouter_cap_usd": C.OPENROUTER_CAP_USD,
    }


def main() -> None:
    C.setup_logging("commit0")
    st = A.self_test()
    assert st["all_ok"], st
    C.write_json(C.RESULTS_DIR / "analysis_selftest.json", st)
    gpu = C.read_json(C.RESULTS_DIR / "tests_gpu_it.json")
    hw = {"gpu": "NVIDIA L4", "vram_total_gb": gpu["U9_memory"]["vram_total_gb"], "compute_capability": "8.9",
          "cpus": C.detect_cpus(), "ram_gb": C.container_ram_gb(),
          "precision_rule": "Gemma always bf16 HF (sdpa); the FP8 W8A8 engine is Qwen-only",
          "batch_shape_crn": C.B_CRN, "memory_probe": gpu["U9_memory"],
          "planned_gpu": "RTX A4500 (20 GB, Ampere); exp23 ran on an RTX 2000 Ada (16 GB)"}
    C.write_json(C.PRED_DIR / "hardware.json", hw)
    C.write_json(C.PRED_DIR / "protocol_E.json", protocol())
    shutil.copy2(C.ROOT / "src" / "analysis_E.py", C.PRED_DIR / "analysis_E.py")
    rec = commit("commit0_protocol_analysis_inputs_hardware",
                 [C.PRED_DIR / "protocol_E.json", C.PRED_DIR / "analysis_E.py", C.ROOT / "src" / "analysis_E.py",
                  C.INPUTS / "SHA256SUMS", C.PRED_DIR / "hardware.json"],
                 note="before any generation (engine check, stage 1, pushes, transplant)")
    logger.info(f"commit #0 {rec['hash'][:16]} at {rec['utc']}; chain {verify_chain()}")


if __name__ == "__main__":
    main()
