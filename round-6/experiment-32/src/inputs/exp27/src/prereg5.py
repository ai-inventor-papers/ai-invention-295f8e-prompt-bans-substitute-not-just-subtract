#!/usr/bin/env python3
"""Commitments (sha256 chain in commitments.log, exp17/exp19 commit.py). Plan S0.8 commit #0 is split by claim
(deviation D-commit, logged): commit0F (literal cell: spec + analysis_f.py) before the first literal-cell sample;
commit0C (Claim C: arm table, N, decisive set, rule, thresholds, hull/bootstrap spec, drop order, analysis_c.py and
the sha256 of every stage-1 prompt) before the first decisive knob sample; commit1 (DMD temperatures, format pilot,
batch probe) after the calibration and before the knob arms.

usage: .venv/bin/python src/prereg5.py {commit0F|commit0C|commit1|verify}
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from loguru import logger

from cfg import PRED_DIR, RESULTS_DIR, ROOT, append_deviation, read_json, setup_logging, sha256_file, utc_now, write_json
from commit import commit, verify

SRC = ROOT / "src"


def commit0F() -> None:
    from cfg5 import (ANSWER_MAX, F_PREDICTION, F_REPEAT_T, F_SEED_K, F_TASK, F_TEMPS, F_TOPK, FP8_REVISION,
                      LITERAL_BOX_S, MAX_MODEL_LEN, THINK_CAP)
    from cfg import stable_seed

    spec = {
        "utc": utc_now(), "claim": "F (literal cell)",
        "precision_rule": read_json(PRED_DIR / "precision_rule.json"),
        "input_hashes_pass": read_json(RESULTS_DIR / "input_hashes.json")["pass"],
        "inputs_SHA256SUMS": sha256_file(ROOT / "inputs" / "SHA256SUMS"),
        "task": F_TASK, "templates": ["W1", "W2", "W3", "W4", "W5"], "k": list(F_SEED_K),
        "seeds": {f"{w}|{k}": {"seed": stable_seed(F_TASK, w, k), "answer_seed": stable_seed(F_TASK, w, k, "answer")}
                  for w in ["W1", "W2", "W3", "W4", "W5"] for k in F_SEED_K},
        "temperatures": list(F_TEMPS), "repeat_T": F_REPEAT_T,
        "decoding": {"top_k": F_TOPK, "top_p": 1.0, "min_p": 0.0, "penalties": "none", "thinking": True,
                     "think_cap": THINK_CAP, "answer_max": ANSWER_MAX, "max_model_len": MAX_MODEL_LEN,
                     "coupling": "vLLM native exponential race, per-request seed (same seed at every T)"},
        "engine": {"vllm": "0.11.0", "checkpoint": f"Qwen/Qwen3-8B-FP8@{FP8_REVISION} (KV rule: bf16 fits < 4 seqs)",
                   "flags": "enforce_eager, TORCH_COMPILE_DISABLE=1, VLLM_TEST_FORCE_FP8_MARLIN=1 (no C compiler)"},
        "time_box_s": LITERAL_BOX_S,
        "prediction": F_PREDICTION,
        "definitions": ("C_T = #seeds (among those with all 4 T completed) whose final-code label is not constant "
                        "across T; Clopper-Pearson one-sided 95% upper bound; same for the first approach; noise "
                        "floor = T0.7 vs repeat byte identity and label agreement; paired comparison with exp21 "
                        "top-p-1 traces at the same (seed, T)."),
        "analysis_f_sha256": sha256_file(SRC / "analysis_f.py"),
        "vllm_literal_sha256": sha256_file(SRC / "vllm_literal.py"),
        "lexicon_sha256": sha256_file(SRC / "lexicon.py"),
        "cfg5_sha256": sha256_file(SRC / "cfg5.py"),
    }
    p = PRED_DIR / "commit0F.json"
    write_json(p, spec)
    commit([p, SRC / "analysis_f.py", SRC / "vllm_literal.py", SRC / "lexicon.py", PRED_DIR / "precision_rule.json"],
           "commit0F")
    append_deviation("D-commit", "plan S0.8 commit #0 split by claim: commit0F (literal cell) is made before the first "
                     "literal-cell sample; commit0C (Claim C) before the first decisive knob sample. Principle (g) "
                     "'committed before the first decisive sample of each claim' is kept.")
    logger.info("commit0F written")


def commit0C() -> None:
    import cfg5 as C5

    rep = read_json(RESULTS_DIR / "prompt_report.json")
    spec = {
        "utc": utc_now(), "claim": "C (plan noise against plan-first prompting)",
        "arms": C5.ARMS5, "D5": list(C5.D5), "ND10": list(C5.ND10),
        "N_per_cell": {"D5": "W1-W5 x k 0-9 = 50", "ND10": "W1-W5 x k 0-5 = 30 (drop step 2: k 0-3 = 20)"},
        "priority": {"P1": list(C5.P1), "P2": list(C5.P2), "P3": list(C5.P3), "P4": list(C5.P4), "P5": list(C5.P5)},
        "drop_order": C5.DROP_ORDER, "generation_deadline_s_after_t0": C5.GEN_DEADLINE_S,
        "class_settings": C5.CLASS_SETTINGS, "text_samplers": list(C5.TEXT_SAMPLERS),
        "rule": ("for t in D5: best_text(t) = max over {IFG, PSL, EAP, BINT} of H5; PN wins t if "
                 "round(H5_PN, 2) >= round(best_text, 2); SUPPORTED if PN wins >= 3 of 5, else DISCONFIRMED"),
        "thresholds": {"cost_bound": C5.COST_BOUND, "hill_targets": list(C5.HILL_TARGETS), "depth": C5.DEPTH,
                       "unresolved_band": list(C5.UNRESOLVED_BAND), "move_excess": C5.MOVE_EXCESS,
                       "move_fisher_p": C5.MOVE_FISHER_P, "min_wins": C5.CLAIM_C_MIN_WINS},
        "hull": "full simplex, grid 0.01 (k<=3) / 0.02 (k=4) / 0.05 (k=5), local refinement 0.0025 within +-0.04 "
                "(k<=3; 0.01 on the support for k>=4), 1,000 CRN draws; edge-restricted (max 2 non-zero) sensitivity",
        "bootstrap": {"D5_claim_classes": C5.N_BOOT_D5, "elsewhere": C5.N_BOOT_ND, "rarefaction_draws": C5.BOOT_RAREFY,
                      "resampling": "slots within each template, jointly across the arms of a task",
                      "per_replicate_grid": "0.05 (k<=4; 0.1 at k=5) + local refinement 0.01 within +-0.04"},
        "dmd": {"steps": C5.DMD_STEPS, "T_range": list(C5.DMD_T_RANGE), "bisect_tol": C5.DMD_BISECT_TOL,
                "onpolicy_tol": C5.DMD_ONPOLICY_TOL, "max_secant": C5.DMD_MAX_SECANT},
        "prompt_sha256": rep["prompt_sha256"], "prompts_jsonl_sha256": sha256_file(ROOT / "prompts" / "prompts.jsonl"),
        "code_sha256": {f: sha256_file(SRC / f) for f in ("analysis_c.py", "hull_full.py", "hull_exp20.py", "parsers.py",
                                                         "engine5.py", "gen5.py", "prompts5.py", "cfg5.py",
                                                         "label5.py", "label_worker_v4.py")},
    }
    p = PRED_DIR / "commit0C.json"
    write_json(p, spec)
    commit([p, SRC / "analysis_c.py", SRC / "hull_full.py", SRC / "parsers.py", SRC / "engine5.py", SRC / "gen5.py",
            SRC / "cfg5.py", ROOT / "prompts" / "prompts.jsonl"], "commit0C")
    logger.info("commit0C written")


def commit1() -> None:
    import cfg5 as C5

    spec = {"utc": utc_now(), "dmd_temperatures": read_json(PRED_DIR / "dmd_temperatures.json"),
            "format_pilot_v1": read_json(PRED_DIR / "format_pilot_v1.json"),
            "format_pilot": read_json(PRED_DIR / "format_pilot.json"),
            "revised_wording": {"PSL_A": C5.PSL_A, "EAP_A": C5.EAP_A, "PSL_B": C5.PSL_B,
                                "sha256": {k: sha256_file(SRC / "cfg5.py") for k in ("cfg5.py",)}},
            "batch_probe": read_json(PRED_DIR / "batch_probe.json"),
            "unit_tests_gpu": read_json(RESULTS_DIR / "unit_tests_gpu.json")}
    p = PRED_DIR / "commit1.json"
    write_json(p, spec)
    commit([p, PRED_DIR / "dmd_temperatures.json", PRED_DIR / "format_pilot.json"], "commit1")
    logger.info("commit1 written (first-decisive-knob-sample boundary)")


if __name__ == "__main__":
    setup_logging("prereg5")
    what = sys.argv[1]
    if what == "commit0F":
        commit0F()
    elif what == "commit0C":
        commit0C()
    elif what == "commit1":
        commit1()
    elif what == "verify":
        print(json.dumps(verify(), indent=1))
