#!/usr/bin/env python3
"""COMMIT #0 (before any sample): predictions/protocol_v5_panelB.json + predictions/precision.json, hash-chained."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg5 import (ALPHAS, ASSOCIATION_TEMPLATE, B, CAP_BLOCKS, DECODING_STR, DEFAULT_SHARE, EDIT_BLOCKS,  # noqa: E402
                  ESC_EXCESS, ESC_PASS_FRAC, FORMAT_LINE, K, MAX_NEW, N_ASSOC, N_DIRS, N_NOVELTY, N_PLAIN,
                  NOVELTY_SEGMENT, PAD_FILLER, PRED_DIR, PROHIBITION_CUES, RAW, TEMPLATES, read_jsonl, utc_now,
                  write_json, BASE_ID, BASE_REVISION, MODEL_ID, MODEL_REVISION)
from commit5 import commit  # noqa: E402
from units_spec import BANNED_BASE, RESERVES, UNIT_ORDER, UNITS  # noqa: E402


def main() -> None:
    assert not read_jsonl(RAW), "commit #0 must precede every sample"
    import torch
    cc = torch.cuda.get_device_capability(0)
    vram = torch.cuda.get_device_properties(0).total_memory / 1024 ** 3
    engine = "fp8_w8a8_hf" if (cc[0] + cc[1] / 10 >= 8.9 and vram < 19.5) else "bf16_hf"
    prec = {"utc": utc_now(), "gpu": torch.cuda.get_device_name(0), "compute_capability": list(cc),
            "vram_gib": vram, "rule": "if cc >= 8.9 and vram < 19.5 GiB: fp8_w8a8_hf else bf16_hf",
            "engine": engine, "batch_rows": B,
            "note": "plan expected an RTX A4500 (bf16); the pod has an RTX 4090 (24 GiB) -> bf16 with B = 20 rows"}
    write_json(PRED_DIR / "precision.json", prec)
    proto = {
        "utc": utc_now(), "artifact": "iteration-5 panel B (Qwen3-8B instruct vs Qwen3-8B-Base)",
        "models": {"instruct": [MODEL_ID, MODEL_REVISION], "base": [BASE_ID, BASE_REVISION],
                   "base_revision_note": "pinned to the newest snapshot (no revision recorded in ITER1 exp5 for the "
                                         "base model's HF snapshot at hand)"},
        "precision": prec,
        "templates": {w: v[1] for w, v in TEMPLATES.items()}, "pad_filler": PAD_FILLER,
        "novelty_segment": NOVELTY_SEGMENT, "association_template": ASSOCIATION_TEMPLATE, "format_line": FORMAT_LINE,
        "plain_completion": "opened ```python fence + 'def <signature>:' + docstring(description); stop at the "
                            "closing fence; max 768 new tokens",
        "decoding": {"string": DECODING_STR, "temperature": 1.0, "top_p": 1.0, "top_k": None,
                     "max_new_tokens": MAX_NEW, "thinking": False, "sampler": "exp8 inverse-CDF CRN, float64"},
        "crn_slot_map": {"twin": "W1-W5 x k 0-9", "t13": "W1-W5 x k 0-9 (paired with twin)",
                         "escape_stage1": "W1-W5 x k 0-1", "confirmation": "W1-W5 x k 2-5",
                         "pn": "W1-W5 x k 0-9, fresh direction per sample", "base_chat": "W1-W5 x k 0-19",
                         "base_pilot": "k 0-5 (N = 30)", "base_plain": "k 0-49", "novelty": "k 0-29",
                         "association": f"{N_ASSOC} answers per catalogue mode, max 64 tokens",
                         "gate_draw": "W1-W5 x k 100-101", "batch": f"B = {B} rows of one (unit, prompt); pads "
                         "are *_EXTRA rows, never decisive", "K": K},
        "escape_rule": {"ESC_EXCESS": ESC_EXCESS, "ESC_PASS_FRAC": ESC_PASS_FRAC,
                        "share": "catalogue off-default over valid attempts (invalid and disputed excluded)",
                        "stage1": "N = 10 (k 0-1): share >= twin + 0.20 and pass >= 0.8 x twin pass -> +20 slots",
                        "confirmed": "pooled 30 keeps excess >= 0.20 with one-sided exact binomial p < 0.05 against "
                                     "p0 = (k_twin + 0.5)/(n_twin + 1), and pass >= 0.8 x twin",
                        "E_u": "confirmed/8 per alpha; E_u = mean over alpha 1, 2; MOVABLE := E_u > 0",
                        "directions": N_DIRS, "alphas": list(ALPHAS)},
        "default_rule": f"modal correct-only twin label if its share >= {DEFAULT_SHARE} with N >= 50, else NO_DEFAULT",
        "unit_formula": "n[l,p] = r_Q(l) x ||h_twin_clean[l,p]||, r_Q from exp23 qwen_ratio.json key r_Q "
                        "(interp over (l+1)/36), plain (not outlier-excluded) variant",
        "edit": "h_S <- h_S + (alpha*n[l,p] - (h_S - h_twin_clean[l,p]).u) u at blocks 12-23, task-spec positions, "
                "prefill only (exp22 make_edits_v4 TARGET)", "edit_blocks": EDIT_BLOCKS, "log_blocks": CAP_BLOCKS,
        "direction_seed_rule": "seed(unit, k) = int(sha256(f'iter5|panelB|{unit}|dir|{k}').hexdigest()[:8], 16), "
                               "k = 0..7; direction = PCG64(seed).standard_normal(4096) normalised; variants and "
                               "their parents share the parent's seeds",
        "gate": {"stage_i": "references 100% by runtime AND AST; probes pass; mutants fail; oracles agree",
                 "stage_ii": "gold = references + 10 base-pilot + 10 instruct gate-draw programs; two blind judges "
                             "(google/gemini-2.5-flash, openai/gpt-4.1-mini; tie-break deepseek/deepseek-chat) after "
                             "a 5/6 control gate; PASS: references 100%, kappa(runtime, AST) >= 0.8, runtime vs "
                             "adjudicated >= 0.9; one revision round"},
        "banned_words_base": BANNED_BASE, "prohibition_cues": list(PROHIBITION_CUES),
        "candidate_order": UNIT_ORDER, "reserves": RESERVES,
        "build_stratification": "alternate pilot-diverse (non-modal correct share >= 0.2) and pilot-collapsed "
                                "(< 0.05) units for builds after two pilots exist; every gated unit is enrolled",
        "mid_artifact_rule": "at T+3:00, if fewer than 5 units passed stage (ii), build B8 then B9",
        "drop_order": ["plain-completion base arm", "T1.3", "PN alpha 2", "extra arm tail (later pairs first)"],
        "never_drop": ["gate", "twin", "base repertoire", "commit before first push", "escape population + "
                       "confirmation", "novelty audit"],
        "per_unit_quantities": {
            "beta_u": "share of correct base programs whose label != default (catalogue + other, invalid excluded)",
            "r_u": "most frequent correct non-default CATALOGUE label in the base repertoire (ties flagged; top-1 "
                   "hit scored 1/|tie|)",
            "predicted_class": "MOVABLE iff beta_u >= 0.05", "predicted_landing": "r_u",
            "rivals": {"R_margin": "-(mean_W [log p(default opening) - max_survivor log p(survivor opening)]), "
                                   "opening = reference's first <= 16 body tokens after the def line, teacher-forced "
                                   "under the twin prompt with assistant prefix '```python\\n' + def line",
                       "R_merit": "-log(runtime of fastest non-default reference / runtime of default reference) on "
                                  "hidden tests (+ length-ratio version)",
                       "R_modal": "1 - twin correct-only modal share",
                       "R_novel": "novelty-instruction catalogue off-default share over valid attempts",
                       "K_u": "number of catalogue modes passing limits"},
            "forecasts": "BASE / ASSOC / PROX over survivors + 'other'; 5% uniform mixing over survivors, 2% "
                         "'other' floor, +0.5 pseudo-counts (BASE, ASSOC); PROX = softmax(-d_j / median_j d_j)"},
        "analysis_rules": {
            "A1": "rho_A1 = Spearman(beta_u, E_u) over gated new units with a default (average ranks); exact "
                  "one-sided permutation p (full enumeration n <= 9, else 10,000 shuffles); bootstrap 95% CI "
                  "(10,000); secondary Spearman(beta_u, PN_excess_u); share of beta < 0.05 units with E = 0 + exact "
                  "CI; 2x3 table; partial Spearman controlling K_u; rivals with paired unit-bootstrap rho "
                  "differences; sensitivities (attempt beta, plain beta, uncertain-class exclusion, split B2 label); "
                  "shuffled-beta placebo (1,000); clustered A1 with variants. DESCRIPTIVE within this panel "
                  "(pooled bar rho >= 0.6, p < 0.01 next round).",
            "A2": "movable units with beta >= 0.05 and a defined push landing: top-1 hit (r_u == landing), chance "
                  "1/(K_u - 1), exact Poisson-binomial p; log score per event under BASE/ASSOC/PROX; paired "
                  "differences (exact Wilcoxon if >= 5 events); 0.10-nat margin reported; JS landing vs base.",
            "within_parent": "per pair delta_beta, delta_E, per-(direction, alpha) McNemar; sign agreement; Spearman.",
            "analysis_code_freeze": "analysis/a1a2.py and analysis/variants.py are hash-committed before the first "
                                    "push sample of any unit"},
    }
    p = PRED_DIR / "protocol_v5_panelB.json"
    write_json(p, proto)
    commit([PRED_DIR / "precision.json", p, Path(__file__).resolve().parent / "units_spec.py",
            Path(__file__).resolve().parents[1] / "data" / "prompts.jsonl"], "commit0_protocol")
    print("commit #0 written")


if __name__ == "__main__":
    main()
