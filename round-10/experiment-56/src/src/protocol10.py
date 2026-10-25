#!/usr/bin/env python3
"""COMMIT #0: the pre-registered protocol (every arm, null, threshold, verdict rule, seed and figure), written before
any model forward, plus sha256 snapshots of the code that exists at that point and inputs_manifest.json.

Usage: protocol10.py commit0
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import Any

from cfg10 import (DOSES, EARLY_POOL, GEN_ARMS, GEN_B, GENESIS, ITER9_W_LAYERS, LATE, MAX_NEW, MODELS, N_BOOT,
                   N_NULL, N_RANDDELTA, NULL_SEED0, PRED_DIR, RANDDELTA_SEED0, RESID_PCS, ROOT, SEED0, SEED_BOOT,
                   SIGN_DOSE, SLOTS_PER_T, THRESH, commit, ledger, setup_logging)


def protocol() -> dict[str, Any]:
    return {
        "artifact": "iteration 10 BASE-W: which weights hold the default algorithm",
        "genesis": GENESIS, "models": MODELS,
        "units": {"T10": "connected components (primary): D = [' find'], A = [' dfs', ' bfs'], 20 prompts",
                  "B3": "MST (beside): D = Kruskal-class tokens, A = Prim-class tokens, 20 prompts",
                  "G-GRID": "Gemma-3-4b grid fork @32 (W3, descriptive): D = DFS class (' visited'), A = BFS class",
                  "T1_T2": "descriptive only, 5 prompts, single-position margin (dropped first after W3)"},
        "S0": {"path": "iteration 9 one-token path: cmap9.prefix_kv on ids[:-1], then a one-token forward of ids[-1] "
                       "at a fixed batch shape B_ot (largest of 40, 24, 16, 8 that fits), row 0 read",
               "captures": ["h_pre (final-norm input)", "h_fin (final-normed)", "mlp_in/mlp_out[0..35]",
                            "fp32 full-vocabulary fork logits (chunked)"],
               "reproduction_rule": {"mean_tol": THRESH["S0_mean_tol"], "per_prompt_tol_B40": THRESH["S0_prompt_tol_B40"],
                                     "per_prompt_tol_smaller_B": THRESH["S0_prompt_tol_small_B"],
                                     "spearman_min": THRESH["S0_spearman"],
                                     "decomposition_targets": THRESH["S0_decomp_target"],
                                     "decomposition_tol": THRESH["S0_decomp_tol"]},
               "fallback": "F1: on failure after 2 debug rounds, proceed on own captures (shares vs own m_I/m_B)"},
        "W1_TF": {
            "margin": "m(h, rows) = lse(h @ rows[D].T) - lse(h @ rows[A].T), fp32; rms(h, g) mimics the bf16 "
                      "Qwen3RMSNorm path (fp32 normalise, bf16 round, times g, bf16 round), eps 1e-6",
            "arms": {"TWIN": "m(h_fin_I, W_I)", "ROWS_ALL (PRIMARY)": "every S = D u A row = w_B,t",
                     "ROWS_D": "D rows base", "ROWS_A": "A rows base", "NORM": "m(rms(h_pre_I, g_B), W_I)",
                     "ROWS_NORM": "m(rms(h_pre_I, g_B), base S rows) = readout upper bound for the class margin",
                     "FULL_UNEMB": "all rows base; identical to ROWS_ALL for the margin by construction (kept for "
                                   "full-distribution metrics and generation)",
                     "DOSE": f"w_I,t + lambda Delta_t, lambda in {list(DOSES)}", "SIGN": f"lambda = {SIGN_DOSE}",
                     "FACTORIAL_2x2": "m_II = m_I, m_IB = ROWS_NORM, m_BI = m(rms(h_pre_B, g_I), W_I), m_BB = m_B; "
                                      "interaction = m_II - m_IB - m_BI + m_BB"},
            "nulls": {"n_draws": N_NULL, "seeds": {k: f"{v} + 100*unit_idx + k" for k, v in NULL_SEED0.items()},
                      "rng": "np.random.default_rng([seed, vocabulary row index]) per row",
                      "RAND_ISO": "w_I,t + ||Delta_t|| u_t, u_t isotropic Gaussian normalised",
                      "DELTA_SWAP": "w_I,t + Delta_s, s uniform among tokens with ||Delta_s|| within 5% of "
                                    "||Delta_t||, ||w_I,s|| within 10% of ||w_I,t||, s not in S, decoded string "
                                    "(stripped, lowercased) containing none of the class strings; no repeats in a draw",
                      "RAND_RESID": f"u_t = random unit vector (isotropic) in the span of the top-{RESID_PCS} "
                                    "principal components (centred) of the instruct h_fin over all prompt + opening "
                                    "positions of the unit's 20 prompts, scaled to ||Delta_t||"},
            "outcomes": "share = ratio of sums (primary); mean/median of per-prompt ratios; prompts with gap < 0.5 "
                        f"flagged; {N_BOOT} prompt-bootstrap 95% CI (seed {SEED_BOOT}); per-token logit change "
                        "h_fin_I . Delta_t; P(D), P(A), unmapped mass, entropy, JS and KL to the base fork "
                        "distribution; nulls: distribution of the 50 shares, median, p95, max, empirical "
                        "p = (1 + #draws >= observed) / 51",
            "verdict_T10": {"SUPPORTED": f"share(ROWS_ALL) >= {THRESH['W1_rows_share']} AND median RAND_ISO <= "
                                         f"{THRESH['W1_rand_iso_median']} AND share(ROWS_ALL) > max RAND_ISO",
                            "DISCONFIRMED": f"share(ROWS_ALL) <= {THRESH['W1_disconfirm']}", "else": "PARTIAL"},
            "specificity_qualifier": "'written into these tokens' own rows' requires share(ROWS_ALL) above the p95 of "
                                     "DELTA_SWAP and of RAND_RESID; otherwise 'readout-level but not token-specific'"},
        "W1_GEN": {"slots": f"30 = W1-W5 x {SLOTS_PER_T}, slot s = 6*template_index + k, uniforms "
                            f"np.random.default_rng({SEED0} + s).random(MAX_NEW)", "max_new": MAX_NEW,
                   "batch": f"one batch of the template's 6 slots per arm at a fixed batch shape B = {GEN_B}",
                   "arms": list(GEN_ARMS),
                   "fork": "fp32 full-vocabulary readout for every arm at the fork (TWIN included); later steps use "
                           "the unmodified bf16 lm_head except ROWS_ALLSTEPS (S rows of the bf16 lm_head swapped in "
                           "place, restored and asserted equal afterwards); FPD = base fp32 fork logits from S0",
                   "FULL_UNEMB_FORK": "run only if its fork distribution differs from ROWS by total variation > 0.05",
                   "drop_order": ["FULL_UNEMB_FORK", "ROWS_ALLSTEPS", "RAND_0", "B3 unit"],
                   "never_dropped": "TWIN / ROWS / RAND_MED / FPD x 30 slots on T10",
                   "label": "frozen label_k3.py; correct DFS = label 'dfs' AND passes hidden tests (primary); B3 "
                            "correct Prim = label in {prim_heap, prim_array} AND pass",
                   "tests": "exact two-sided McNemar on CRN pairs; primary ROWS vs TWIN and ROWS vs RAND_MED (Holm "
                            "over 2); reported ROWS vs RAND_MAX, ROWS vs RAND_0, FPD vs TWIN, ROWS vs FPD; Wilson "
                            "CIs for pass rates, Newcombe CIs for pass differences",
                   "verdict": f"SUPPORTED if ROWS >= {THRESH['W1GEN_rows_min_correct']}/30 correct DFS AND each RAND "
                              f"arm <= {THRESH['W1GEN_rand_max_correct']}/30 AND both primary Holm p < 0.05",
                   "predictions": "COMMIT #2: 30 * mean over the 5 slot prompts of sum_tok p_arm(tok) P(class|tok)"},
        "W2": {"late": list(LATE), "early_pool": list(EARLY_POOL),
               "matching": "Hungarian on |log N_l - log N_e|, N_l = sqrt(||dGate||^2 + ||dUp||^2 + ||dDown||^2); "
                           "E_joint scaled by c = ||dW_late_joint|| / ||dW_early_joint||; committed (COMMIT #3) "
                           "before any W2 forward",
               "scope_A_all_position (primary)": ["W_l single (26..35)", "W_late_joint", "E_match(l) single",
                                                  "E_joint (scaled)", f"RANDDELTA_l x {N_RANDDELTA} "
                                                  f"(seeds {RANDDELTA_SEED0} + ...)", f"RANDDELTA_joint x {N_RANDDELTA}",
                                                  "DECOMP = W_late_joint + ROWS_NORM readout", "ATTN_late_joint "
                                                                                                "(optional)"],
               "scope_B_fork_only (bridge)": f"base MLP on the live fork input (CPU fp32), singles 26..35, joint of "
                                             f"the 10, iteration-9 joint of {list(ITER9_W_LAYERS)}; reproduction of "
                                             f"iteration 9's W shares within +-{THRESH['W2_bridge_tol']}",
               "rule": f"share(W_late_joint) - share(E_joint) >= {THRESH['W2_late_minus_early']} with bootstrap CI "
                       "excluding 0 AND share(W_late_joint) > max of the 3 RANDDELTA_joint draws",
               "decomposition": "readout (ROWS_NORM); late MLPs all-position; joint DECOMP; interaction = joint - "
                                "readout - late; remainder = 1 - joint"},
        "W3": {"unit": "G-GRID@32", "arms": ["ROWS_ALL", "ROWS_D", "ROWS_A", "NORM", "ROWS_NORM", "DOSE",
                                             "RAND_ISO x 50", "DELTA_SWAP x 50"],
               "untie": "output only: logits for S tokens use the pt embedding rows; Gemma3RMSNorm gain (1 + w); "
                        "final_logit_softcapping applied if non-null", "threshold": None},
        "figures": ["F1 closed share by arm with null histograms", "F2 per-prompt shares sized by gap",
                    "F3 dose-response vs RAND_ISO at matched lambda", "F4 generation counts by arm",
                    "F5 fork states on the readout plane with margin isolines", "F6 PCA of block-35 outputs at "
                                                                                 "the fork", "F7 W2 singles vs "
                                                                                             "controls + "
                                                                                             "decomposition",
                    "F8 W3 Gemma shares"],
        "seeds": {"null": NULL_SEED0, "randdelta": RANDDELTA_SEED0, "boot": SEED_BOOT, "gen": SEED0},
        "thresholds": THRESH,
    }


def commit0() -> None:
    snap = PRED_DIR / "code_commit0"
    snap.mkdir(parents=True, exist_ok=True)
    files = []
    for p in sorted((ROOT / "src").glob("*.py")):
        q = snap / p.name
        shutil.copy2(p, q)
        files.append(q)
    commit("commit0_protocol", protocol(), files=files + [ROOT / "inputs_manifest.json",
                                                          ROOT / "results" / "labeller_gate.json"])
    ledger("COMMIT0")


if __name__ == "__main__":
    setup_logging("protocol10")
    {"commit0": commit0}[sys.argv[1]]()
