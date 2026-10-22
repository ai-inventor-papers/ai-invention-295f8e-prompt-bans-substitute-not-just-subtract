#!/usr/bin/env python3
"""Commit #0 (plan 0.8): predictions/protocol_v6_panelII.json, written and hash-chained BEFORE any sample of this
artifact. It freezes the decoding, templates, alphas, dose, every definition of plan 0.9 (spec_digest), the M
candidate definitions with their fallback mechanism signs (the screen-derived signs of plan 0.7 are committed in a
separate file before the first nudge sample), the enrolment rule, the drop order, the candidate order and the power
table of domain_practice point 4."""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from scipy.stats import binom  # noqa: E402

from cfg5 import (DECODING_STR, EDIT_BLOCKS, GENESIS, GPU_NAME, MODEL_ID, MODEL_REVISION, BASE_ID, BASE_REVISION,  # noqa: E402
                  NEW_UNITS, OPENROUTER_CAP_USD, PRED_DIR, RESERVE_UNITS, SCREEN_A, SCREEN_B, TEMPLATES, setup_logging,
                  utc_now, write_json)
from commit5 import commit  # noqa: E402


def power_table() -> list[dict]:
    rows = []
    for n in range(4, 13):
        for p_true in (0.6, 0.7, 0.8, 0.9):
            need = next((h for h in range(n + 1) if h / n >= 2 / 3 - 1e-12 and binom.sf(h - 1, n, 1 / 3) < 0.05),
                        None)
            pw = float(binom.sf(need - 1, n, p_true)) if need is not None else 0.0
            rows.append({"n_events": n, "chance": round(1 / 3, 4), "hits_needed": need,
                         "p_at_needed": None if need is None else float(binom.sf(need - 1, n, 1 / 3)),
                         "true_hit_rate": p_true, "power": round(pw, 3)})
    sign = []
    for n in range(4, 11):
        need = next((b for b in range(n + 1) if binom.sf(b - 1, n, 0.5) < 0.05), None)
        sign.append({"n_nontied": n, "b_needed": need,
                     "p_at_needed": None if need is None else float(binom.sf(need - 1, n, 0.5))})
    return [{"L1a_poisson_binomial_at_K4": rows, "L1b_sign_test": sign}]


PROTOCOL = {
    "schema": "protocol_v6_panelII",
    "panel": "II",
    "direction": "iteration-6 direction 5: does a content-free nudge land on the base model's runner-up r_u or on the "
                 "tuned model's own hidden second choice (q_tail / q_lik)?",
    "genesis": "sha256('iter6_dir5_panelII') = " + GENESIS,
    "models": {"instruct": {"id": MODEL_ID, "revision": MODEL_REVISION},
               "base": {"id": BASE_ID, "revision": BASE_REVISION}},
    "precision": "W16A16 bf16 everywhere (HF transformers 4.57.6 sdpa for every hooked arm; vLLM 0.11.0 bf16 only for "
                 "unhooked sampling under the engine-equivalence check); never FP8",
    "gpu": GPU_NAME + " (23 GB, cc 8.9) -- the plan's RTX A4500 was not assigned; frozen precision rule -> bf16",
    "decoding": {"temperature": 1.0, "top_p": 1.0, "top_k": None, "max_new_tokens": 1024, "thinking": False,
                 "enable_thinking": False, "fence_stop": "first closed ```python block (HF exp22 rule; vLLM: V1 "
                 "logits processor forcing <|im_end|>)", "decoding_str": DECODING_STR,
                 "hf_sampler": "exp8 inverse-CDF CRN sampler, one uniform per (row, step), B = 20 rows of one "
                               "(unit, template) per batch, prune=False",
                 "twin_T13": "100 extra twin slots at T 1.3 (vLLM)"},
    "templates": {w: v[1] for w, v in TEMPLATES.items()},
    "template_rule": "W1-W5 neutral twins; the unit's neutral noun (exp7 frozen noun rule) padded with ' .' to the "
                     "token length of the dataset-reference mode's display name; N per cell = 5 x N/5",
    "entry_point": "def solve(...) (the iteration-5 harness, plain-completion template and tracer are reused "
                   "unchanged; the plan's 'class Solution' entry point is a logged deviation)",
    "alphas": {"ESC": [1.0, 2.0, 4.0], "PN": [2.0, 4.0], "GTN": [2.0]},
    "dose": {"unit": "ban-free unit n[l,p] = ||h_twin_clean[l,p]|| x r_Q(l), r_Q from exp23 qwen_ratio.json "
                     "(median at relative depth (l+1)/36)",
             "blocks": EDIT_BLOCKS, "positions": "task-spec positions S = [p1, spec_end)",
             "ESC_PN_site": "prompt prefill only",
             "GTN_site": "exp20 S3 site: generated tokens 1-32; the edit targets displacement alpha x n_gen from the "
                         "teacher-forced clean shadow row of the same token sequence, n_gen = ||h_shadow|| x r_Q(l)",
             "edit": "h <- h + (alpha x n[l,p] - (h - h_twin_clean[l,p]) . u) u (exp19 make_edits TARGET; exp26 ctx5)",
             "directions": "u = PCG64(seed).standard_normal(4096) / norm, identical at every block and position",
             "seeds": {"ESC": "int(sha256('iter6|panelII|{u}|dir|{k}')[:8], 16), k = 0..7",
                       "PN": "int(sha256('iter6|panelII|{u}|PN|{alpha}|{w}|{s}')[:8], 16)",
                       "GTN": "int(sha256('iter6|panelII|{u}|GTN|{alpha}|{w}|{s}')[:8], 16)",
                       "CRN_new_units": "PCG64(int(sha256('iter6|crn|{u}|{w}|{s}')[:8], 16)) uniforms",
                       "CRN_iter5_units": "the iteration-5 exp26 stream PCG64(stable_seed(u, w, s)) (reused)",
                       "vLLM": "per-request seed int(sha256('iter6|vllm|...')[:8], 16)"},
             "logging": "per pushed row: realised targeted-component relative error, ||delta|| at the mean task-spec "
                        "position and the read position, the target norm"},
    "spec_digest": {
        "sets": "CAT = frozen catalogue; S = CAT minus default; 'other' and 'invalid' are separate columns and 'other' "
                "never counts as a landing; CORRECT = passes every hidden test within its per-case limit",
        "DEFAULT": "modal CORRECT label over the 300 twin samples (T 1.0 and T 1.3 pooled) with share >= 0.6 among "
                   "correct programs, else NO_DEFAULT (CHOICE: pooled 300; the T 1.0-only default reported beside and "
                   "flagged if different); NO_DEFAULT units enter no L or M test",
        "TWIN_BASELINE_for_gates": "the T 1.0 twin (50 HF CRN slots + 150 vLLM slots if the unit passed the engine "
                                   "check, else the 50 HF slots): twin_pass and twin_off = correct S-labelled / all",
        "q_tail": "add-one smoothed counts over S + {other} of the correct non-default programs among the 300 twin "
                  "samples; t_u = argmax over S (tie: higher T 1.0 count, then catalogue order); TAIL_EMPTY = no "
                  "correct S program among the 300",
        "q_lik": "10 name-scrubbed, test-passing forced programs per algorithm whose runtime/final label equals the "
                 "algorithm (comments + docstrings removed first); tokens = chat_template(twin prompt w) + "
                 "'```python\\n' + program; lp = sum log-softmax(fp32 logits) over the first 48 program tokens; "
                 "score_raw = mean lp, score_tok = mean lp / n_tokens; q_lik = softmax over S of score_tok; "
                 "q_lik_raw = softmax over S of score_raw; qlik_top1 = argmax over S of score_tok; unscrubbed "
                 "sensitivity; noise floor = median |delta lp| of 20 programs re-scored in another batch composition; "
                 "fixed batch shapes, left padding with attention mask",
        "fork_margin": "m = mean lp(default) - mean lp(r_u) (raw; per-token version beside)",
        "q_base": "counts of CORRECT base programs over CAT + {other} from 200 chat-template samples (identical "
                  "token ids to the twin W1-W5 prompts) + 100 plain completions; < 20 correct -> valid attempts, "
                  "flag LOW_CORRECT; add-one smoothing over S + {other} for forecasting; r_u = argmax over S (tie: "
                  "higher plain count, then catalogue order); DISCORDANT = r_u != qlik_top1; beta = 1 - "
                  "base_correct(default) / base_correct_total",
        "forecasts_for_scoring": "every forecast restricted to S and renormalised ('other' dropped), identically for "
                                 "q_base, q_tail, q_lik, association and uniform = 1/(K-1)",
        "CELL": "one (arm, alpha, direction); QUALIFIES iff pass_rate >= 0.8 x twin_pass",
        "ESCAPE": "share = correct S-labelled programs / all programs in the cell; stage 1 (N 10): share >= twin_off "
                  "+ 0.20 and qualifies; stage 2: +20 slots (2-5 per template), CONFIRMED iff the pooled 30 has "
                  "one-sided exact binomial p < 0.05 vs p0 = (k_twin + 0.5)/(n_twin + 1) and still qualifies; "
                  "E_u(alpha) = confirmed / 8; E_u = mean over the alphas run",
        "LANDING_EVENT": "one (unit, nudge type), nudge in {ESC, PN, GTN} (content_free) or BINT (content_free = "
                         "false: K and descriptive tables only); pool correct S-labelled programs over the nudge "
                         "type's QUALIFYING cells (every ESC cell at N 10 or 30; PN alpha 2 and 4; GTN alpha 2); "
                         "is_event iff pooled count >= 5; modal_landing = argmax over S if its share of the pooled "
                         "S-labelled correct programs leads the next by >= 15 points, else NO_CLEAR_LANDING (a miss "
                         "for every top-1 forecast); pooled correct 'other' reported, flag other_dominant if it "
                         "exceeds the modal count",
        "SETS": "CONFIRMATION = new list-II units; SCREEN = the 15 iteration-5 units",
    },
    "tests": {
        "L1a": "Ea = tail-empty events; hits = [r_u == modal_landing]; exact Poisson-binomial P(X >= hits) with "
               "per-event chance 1/(K_e - 1); PASS iff |Ea| >= 6, hits/|Ea| >= 2/3, p < 0.05; |Ea| < 6 -> "
               "DESCRIPTIVE (carried to the pooled panel I + II analysis)",
        "L1b": "Eb = discordant events; b = #(r_u hit, qlik_top1 miss), c = #(qlik_top1 hit, r_u miss); one-sided "
               "P(Binomial(b + c, 1/2) >= b); PASS iff |Eb| >= 6 and p < 0.05",
        "log_scores": "LS_f(e) = (1/n_e) sum_a counts_e(a) log q_f(a), f in {base, lik, lik_raw, tail, assoc, "
                      "uniform}; D_lik = LS_base - LS_lik, D_tail = LS_base - LS_tail; one-sided 95% percentile "
                      "bootstrap lower bound (10,000 event resamples, numpy default_rng(20261021)); NON-INFERIOR iff "
                      "LB > -0.10; two-sided CIs and the unit-clustered bootstrap beside",
        "pseudo_replication_guard": "unit-level pooled landing (15-point rule) and unit-level L1a/L1b",
        "verdict": "SUPPORTED-IN-PANEL iff L1a PASS and L1b PASS; DISCONFIRMED-IN-PANEL iff (mean D_lik <= 0 or mean "
                   "D_tail <= 0 on E) and L1a p >= 0.05 with |Ea| >= 6; otherwise DESCRIPTIVE",
        "L2": "correct S-labelled nudged programs whose algorithm has base valid == 0 and base correct == 0; "
              "rule-of-three bound 3/N if 0",
        "L3": "events with >= 10 correct S programs: 10 random half-splits (seed 20261021 + i), one power gamma in "
              "0:0.05:8 by ML on half A for q_base^g, q_tail^g, assoc^g; held-out log score on half B; Wilcoxon "
              "(descriptive); Kendall tau-b per unit between q_base and q_tail orders on S",
        "M": "Spearman rho of each candidate with E_u over enrolled new units with a default; one-sided exact "
             "permutation p in the committed direction; Holm over 6 candidates; SUPPORTED iff rho >= 0.5 in the "
             "committed direction and Holm p < 0.05",
        "K": "H5, P15, P20 of BINT, PN alpha 2 and PN alpha 4 on the full-simplex randomisation hull (exp27 "
             "hull_full.py), 2,000 bootstrap replicates with the maximum over settings inside each replicate; "
             "correct-only rarefied Hill-1 at depth 25; pass-rate cost with Newcombe CIs",
    },
    "M_candidates": {
        "beta": {"definition": "1 - base_correct(default) / base_correct_total", "fallback_sign": "+"},
        "replacement_class": {"definition": "1 if the base runner-up r_u is a library/one-line mode or the twin "
                                            "minority already contains r_u, else 0 (exp26 'replacement' coding: "
                                            "rank of r_u among the twin's non-default correct labels; 0 = absent)",
                              "fallback_sign": "-"},
        "runtime_merit": {"definition": "log2(default median time / fastest correct non-default reference median "
                                        "time) on the unit's stress cases, 5 repeats", "fallback_sign": "+"},
        "twin_modal_share": {"definition": "share of the default among correct twin programs (300)",
                             "fallback_sign": "-"},
        "K": {"definition": "catalogue size", "fallback_sign": "+"},
        "fork_margin": {"definition": "m = mean lp(default) - mean lp(r_u)", "fallback_sign": "-"},
        "sign_rule": "screen rho sign from the iteration-5 units (plan 0.7) unless |rho| < 0.1 or no screen value, "
                     "then the fallback sign; committed in predictions/m_signs.json before the first nudge sample",
    },
    "units": {"candidate_order": NEW_UNITS, "reserves": RESERVE_UNITS,
              "mid_artifact_rule": "reserves built only if fewer than 5 units gated at T+3:00",
              "screen_units": SCREEN_A + SCREEN_B},
    "enrolment_rule": "PRIORITY iff pilot runner-up (base chat slots 0-29) != qlik_top1 OR twin slots 0-49 hold no "
                      "correct S program; priority units first in list order, then the others; iteration-5 units "
                      "form a separate SCREEN queue (movable first: A1, A3, A7, B2, B3, B4, B7) and never pre-empt "
                      "new units",
    "drop_order": ["(1) BINT on iteration-5 units", "(2) GTN on iteration-5 units",
                   "(3) alpha-4 ESC/PN on never-moved iteration-5 units",
                   "(4) the plain-completion top-up of iteration-5 units", "(5) new units beyond 6"],
    "never_drop": ["the gate", "the twin of 300", "q_lik", "the base 200", "the commit before the first nudge",
                   "the 8 x 3 escape population with confirmation", "PN alpha 2 and 4 on every enrolled new unit",
                   "the twin and q_lik top-ups of the iteration-5 units", "the novelty audit"],
    "labellers": "runtime tracer (primary) + AST rules; disagreements -> two blind judges of different families "
                 "(google/gemini-2.5-flash, openai/gpt-4.1-mini), deepseek tie-break; never a Qwen judge; gate (ii): "
                 "references 100%, kappa >= 0.8, runtime vs adjudicated >= 0.9",
    "openrouter_cap_usd": OPENROUTER_CAP_USD,
    "deviations_at_commit0": [
        "GPU: NVIDIA L4 (23 GB) instead of RTX A4500; batches of B = 20 rows as in exp26",
        "analysis code (analysis/pool_l1.py, l2l3.py, m_k.py) is hash-committed before the FIRST NUDGE sample of any "
        "unit (the outcomes), not before the first predictor-side sample; this protocol freezes every rule in prose",
        "entry point def solve(...) instead of class Solution (iteration-5 harness reused unchanged)",
        "model weights read from the run's shared HF cache (HF_HUB_CACHE), not WS/hf_cache",
    ],
    "power": power_table(),
}


def main() -> None:
    setup_logging("protocol6")
    p = PRED_DIR / "protocol_v6_panelII.json"
    if p.exists():
        print("protocol already written; never edited")
        return
    PROTOCOL["utc"] = utc_now()
    write_json(p, PROTOCOL)
    e = commit([p], "commit0")
    print(e)


if __name__ == "__main__":
    main()
