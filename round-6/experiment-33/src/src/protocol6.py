#!/usr/bin/env python3
"""COMMIT #0 (CPU, before any new generation row): writes predictions/protocol_G6.json (every threshold, seed, slot
map, stopping rule, exemplar rule, audit rule, fp32 switch rule, event definitions, drop order), copies the frozen
analysis src/analysis_L.py to predictions/analysis_L_gemma.py, records the hardware, and appends commit #0 to the
commitments.log hash chain (genesis sha256('iter6_gemma_L'))."""

from __future__ import annotations

import json
import platform
import shutil
import sys
from pathlib import Path

from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg import (ALL_TASKS, ALPHA6, DIR_SEEDS6, FORCED_KEEP, FORCED_N, MODELS, PN6_SLOTS, PRED_DIR, PTFS_CAP,
                 PTFS_MIN_CORRECT, PTFS_STAGE, PUSH_TASKS6, QLIK_WINDOW, RESULTS_DIR, SLOT_PREFIX, T_HOT,
                 TWIN6_T10_SLOTS, TWIN6_T13_SLOTS, read_json, setup_logging, utc_now, write_json, detect_cpus,
                 container_ram_gb)
import analysis_L as A
import commit as C
import prompts6 as P6


def protocol() -> dict:
    he = [{k: h[k] for k in ("task_id", "entry_point", "signature")} for h in P6.f_he_exemplars()]
    return {
        "name": "iteration 6 step 5: Gemma base runner-up vs the tuned model's own tail and likelihood (Claim L, "
                "second-family REPLICATION; never pooled with Qwen)",
        "models": {k: f"{m}@{r}" for k, (m, r) in MODELS.items()}, "precision": "bf16 W16A16, sdpa, text-only",
        "decoding": "T 1.0 (T 1.3 for the hot twin arm), top-p 1, no top-k, CRN inverse-CDF sampler (exp28 engine)",
        "slot_scheme": {"twin_T1.0": f"slots 0-9 = exp28 rows; new slots {TWIN6_T10_SLOTS[0]}-{TWIN6_T10_SLOTS[-1]} "
                                     f"x W1-W5, ukey ('{SLOT_PREFIX}', task, W, slot)",
                        "twin_T1.3": f"slots {TWIN6_T13_SLOTS[0]}-{TWIN6_T13_SLOTS[-1]} x W1-W5, same ukeys as T 1.0 "
                                     "slots 0-19 (paired)",
                        "fresh_FD": "stage 1 slots 0-1 x W1-W5 (N 10), confirmation slots 2-5 (+20, N 30)",
                        "fresh_PN": f"slots {PN6_SLOTS[0]}-{PN6_SLOTS[-1]} x W1-W5 (N 50), direction "
                                    "PCG64(stable_seed('iter6G-PN', task, W, slot))",
                        "pt_fewshot": "draw k: uniforms PCG64(stable_seed('iter6G-ptfs', task, k)); even k F_bench, odd F_he",
                        "forced": "algorithm a, paraphrase k (0-4), draw j: PCG64(stable_seed('iter6G-forced', task, a, k, j))"},
        "direction_seeds_fresh_FD": list(DIR_SEEDS6), "alpha_fresh": ALPHA6, "push_tasks_order": list(PUSH_TASKS6),
        "dose_unit": "exp28 outlier-excluded ban-free unit n[l,p] = r_Q_ox(l) x ||h_ref ox-5||, BAND 11-22 x spec, prefill",
        "pt_topup": {"stages": f"A/B/C of {PTFS_STAGE} draws per task, cap {PTFS_CAP}",
                     "stop_rule": f"stop when pooled CORRECT pt programs (exp28 chat + exp28 plain + few-shot) >= "
                                  f"{PTFS_MIN_CORRECT}; outcome-blind w.r.t. the it model",
                     "exemplar_rule_F_bench": "first two of [T08, T04, R6, T13] not the target and not in its family "
                                              "group; bodies = T08 iteration, T04 naive, R6 linear_scan, T13 sort_sweep",
                     "F_he_exemplars": he, "max_new": 768, "stop": "plain_ended (exp28)",
                     "priming_check": "Fisher-Freeman-Halton (Monte Carlo 10k) few-shot vs exp28 zero-shot plain, "
                                      "F_bench vs F_he; flag p < 0.01"},
        "pt_audit": {"per_task": 15, "strata": "all non-default programs up to 10 (r_u support stratum) + random fill",
                     "judges": {"A": "google/gemini-2.5-flash", "B": "openai/gpt-4.1-mini",
                                "C_tiebreak": "deepseek/deepseek-chat-v3.1"},
                     "gate": "overall >= 0.8 AND r_u stratum >= 0.8; one revision round; else AUDIT_FAIL"},
        "q_base": "add-one over nondef + 'other'; correct-only if >= 20 correct pt programs else valid attempts "
                  "(LOW_CORRECT); r_u tie rule: correct, valid, few-shot count, alphabetical (TIE flag); THIN_RU if "
                  "correct support < 5",
        "twin": "D_u at N 300 (share >= 0.6, >= 10 correct, unique, catalogue); q_tail add-one over nondef + 'other' "
                "of correct off-default programs in all 300; t_u; TAIL-EMPTY",
        "q_lik": {"writers": f"gemma-3-4b-it forced prompts (bench FORCED_TEMPLATES 0-4 / exp7 forced k0-k4), "
                             f"{FORCED_N} per algorithm (+20 if < {FORCED_KEEP} kept, cap 40); keep iff passes all "
                             "tests AND label == requested; name-scrubbed, re-tested, re-labelled unchanged; first 10",
                  "fill": "ITER2 bench forced_programs.jsonl (Qwen-written) then exp8 suite references (flagged); "
                          "< 3 -> THIN_QLIK; 0 -> cannot be top-1",
                  "window": QLIK_WINDOW, "ids": "twin_ids(W) + ids(opening prefix) + ids(code)[:48], tokenised "
                                               "separately; opening prefix = modal pre-code text of the twin outputs",
                  "score": "s_u(a) = mean over programs x W1-W5 of mean (norm) / sum (raw) log-prob; top-1 = argmax "
                           "nondef of norm; dist = softmax(norm) x 0.98 + other 0.02",
                  "fp32_rule": "re-score a 10% subsample in fp32; if top-1 flips on >= 2 units -> re-score all in fp32",
                  "sensitivity": "q_lik from Qwen-written bench programs only"},
        "events": "v6: one event per (unit, nudge type FD/PN) pooling old (exp28) and fresh qualifying cells "
                  "(pass >= 0.8 x twin T1.0 pass); EVENT iff >= 5 correct off-default catalogue programs; landing = "
                  "modal catalogue label if it leads by >= 15 points else no clear landing; fresh-only and old-only "
                  "splits; exp28's confirmed-escape definition beside for old events",
        "committed_prediction": "for every event: modal landing = r_u",
        "tests": "see predictions/analysis_L_gemma.py (L1a, L1b, tail rival, log scores with Wilcoxon/BCa/cluster, "
                 "unit-clustered, old tally, L2-G)",
        "thresholds": A.TH,
        "drop_order": ["fresh FD (keep fresh PN)", "fresh PN alpha 2", "twin 300 -> 200 (T1.0 slots 10-29, T1.3 0-9)"],
        "drop_rule": "time-based only; fresh FD on T1/T2 first; PN >= N 50; a decisive cell never below N 30",
        "never_dropped": ["pt top-up + audit", "it twin top-up", "q_lik", "commit #1", "rescored contest",
                          "novelty audit"],
        "multiplicity": "Holm within this artifact's Gemma tests; the iteration-wide family is left to evaluation",
        "tasks": list(ALL_TASKS),
    }


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("commit0")
    st = A.self_test()
    write_json(RESULTS_DIR / "analysis_selftest.json", st)
    assert st["all_ok"], f"frozen-analysis self-test failed: {st}"
    pr = protocol()
    write_json(PRED_DIR / "protocol_G6.json", pr)
    shutil.copy2(Path(__file__).resolve().parent / "analysis_L.py", PRED_DIR / "analysis_L_gemma.py")
    import torch

    hw = {"gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
          "vram_gb": torch.cuda.get_device_properties(0).total_memory / 1e9 if torch.cuda.is_available() else None,
          "cpus": detect_cpus(), "ram_gb_container": container_ram_gb(), "python": platform.python_version(),
          "torch": torch.__version__, "utc": utc_now()}
    write_json(PRED_DIR / "hardware.json", hw)
    rec = C.commit("commit#0 protocol + frozen analysis", [PRED_DIR / "protocol_G6.json",
                                                            PRED_DIR / "analysis_L_gemma.py",
                                                            PRED_DIR / "hardware.json"],
                   note="before any iteration-6 generation row")
    logger.info(f"commit #0 at {rec['utc']}: {rec['hash'][:16]}")


if __name__ == "__main__":
    main()
