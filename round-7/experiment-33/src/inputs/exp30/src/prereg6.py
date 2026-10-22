#!/usr/bin/env python3
"""Commit #0 (before the first decisive sample): every rule, threshold and prediction of this artifact, Y per task,
the drop order, the slot map, the seed function, the engine settings, sha256 of the code and of every input file."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from loguru import logger

from cfg import ROOT, setup_logging, sha256_file
from cfg6 import (BANDS, BATCH6, DEFAULT6, MAX_NEW6, N30, ROUTE_CLASS, SITE_BLOCKS6, SITE_POS6, SLOT_MAP, ST_ALPHAS,
                  TASKS6, TEMPLATES6, Y6)
from commit6 import commit

RULES = {
    "stage_A": {
        "cells": "TWIN (N=50), BAN, X_b (b in 0-11, 12-23, 24-35, 0-35; block outputs at task-spec positions <- the "
                 "full ban's), COND (twin prefill, then K/V of the condition span in all layers <- the ban's = route "
                 "arm d), RPOS (read position, all 36 blocks <- the ban's), MR_0-35 and MR_12-23 on T03/T10/T2 "
                 "(h <- h_twin + ||h_src - h_twin|| u, fresh unit u per (slot, l, p)), PLACEBO on T03/T10/T2 (source = "
                 "a second neutral twin, band 0-35); N = 30 on slots 0-29",
        "Y": Y6, "defaults": DEFAULT6, "route_class_iter2_3": ROUTE_CLASS,
        "transfer": "share(label == Y | cell) - share(label == Y | TWIN), all samples (invalid rows count as not-Y)",
        "recovery": "transfer / (Y_BAN - Y_TWIN), reported only if the denominator >= 0.3",
        "slot_IIA": "mean over slots of 1[label_X(s) == label_BAN(s)]",
        "pass_ratio": "pass_X / pass_TWIN (validity gate >= 0.8)",
        "tests": "exact McNemar on paired slots (event = label == Y): X vs TWIN and X_0-35 vs MR_0-35; Holm across "
                 "tasks within each family",
        "P1_prediction": "transfer >= 0.5 at band 0-35 with pass ratio >= 0.8 on at least 2 of T2, T03, T10, AND "
                         "transfer <= 0.2 on T05 and T06 (reported with its 95% Clopper-Pearson upper bound)",
        "route_check_secondary": "COND transfer >= 0.5 on T05 and T06 and <= 0.2 on T2; RPOS transfer <= 0.2 "
                                 "everywhere",
        "placebo_prediction": "|transfer(PLACEBO)| <= 0.1 on T2, T03, T10",
        "MR_prediction": "X_0-35 beats MR_0-35 on Y (exact McNemar p < 0.05) wherever P1 transfers",
    },
    "ST": {
        "tasks": ["T03", "T10"], "sites": SITE_BLOCKS6, "positions": SITE_POS6, "alphas": list(ST_ALPHAS),
        "unit": "ban-free n[l,p] = ||h_twin[l,p]|| * r_Q(l) (exp23 qwen_ratio, exp27 interpolation), bf16 twin states",
        "S1E": "target at R = alpha * sqrt(sum_spec n[l,p]^2) (S0's energy at block l)",
        "S2E": "target per cond position = alpha * sqrt(sum_spec n^2 / sum_cond n^2) * n[l,c]",
        "S3": "generated tokens 1-32, blocks 12-23, target alpha * mean_spec n[l,p], teacher-forced twin shadow rows",
        "edit": "displacement-targeted: delta = h - h_clean; h <- h + (alpha*n - delta.u) u; one fresh direction per "
                "sample from dir_seed(task, site, alpha, slot)",
        "outcome": "1 = passes the hidden tests AND label not in {default, other, invalid}; sensitivity: correct "
                   "'other' counts as 1",
        "design": "prefill sites only (S0 reference, S4, S5, S1, S2, S1E = S1 + energy dummy, S2E = S2 + energy "
                  "dummy) + log D_R + log D_g1 (ban-free units at block 35, offset 1e-3); RCS(3) in log D_R as "
                  "sensitivity; common-support trimming to the 2.5-97.5 percentile overlap of log D_R",
        "estimator": "Firth bias-reduced logistic (numpy), profile-penalised CI + 2,000-resample cluster bootstrap "
                     "over CRN slots (percentile); Mantel-Haenszel OR S0 vs S1, S0 vs S2 within quintiles of log D_R",
        "RULE": "the prefill-site claim SURVIVES iff, on >= 1 of T03 and T10, beta_S1 < 0 and beta_S2 < 0 with the "
                "cluster-bootstrap 95% interval of each excluding 0 and the profile CI agreeing in sign; otherwise it "
                "is WITHDRAWN as FP8-specific. If S0 has 0 correct off-default programs at every alpha on both tasks, "
                "the verdict is 'no prefill site moves the algorithm in bf16' (withdrawn).",
    },
    "state_vs_token": {
        "K_S3": "mean over tokens 1-32 of KL(S3 || teacher-forced twin shadow) per sample, mean over the 50 S3 samples",
        "DMD": "temperature on generated tokens 1-32 only (T = 1 after), bisected until the on-policy mean per-token "
               "KL is within 10% of K_S3 (cap T = 3.0; flagged if not reached); amendment commit #2 before the DMD "
               "samples",
        "flip": "arm correct and non-default while the twin's slot is default",
        "test": "exact McNemar on discordant flips S3-only vs DMD-only; threshold p < 0.05 on both tasks at alpha 2 "
                "(primary; alpha 4 secondary); minimum detectable: 6:0 discordant (p = 0.031)",
    },
    "top5_push": {
        "task": "T1", "direction": "exp20 directions/u_top5.npz (FP8-derived, applied in bf16)",
        "unit": "bf16 nS[l,p] = mean over templates of ||h_ban - h_twin|| at spec positions, blocks 12-23",
        "alphas": [1, 2, 4, 8], "N": 30, "landing": "composition among correct non-BFS programs",
        "geometry": "spec-mean block outputs (blocks 12-23) / exp20 med_norm projected on the PCA plane of the 10 "
                    "forced-prompt centroids (actual activation coordinates) + geodesic k-NN MDS",
        "landing_test": "landing-weighted geodesic distance to the nearest banned centroid vs a random-survivor null "
                        "(1,000 draws); 'not computable' with < 5 correct non-default programs",
    },
    "L": {
        "events": "push-landing events from exp22 escape_9task (FP8), exp25 extra_arm_a + panel A, exp26 panel B, "
                  "exp28 Gemma; one row per event: task, engine, default, landing composition, base runner-up, "
                  "q_base, twin non-default composition (event table frozen in commit #1 before any opening pass)",
        "forecasts": "BASE = q_base + 1; TWINMIN = twin non-default counts + 1 (undefined if empty); OPEN = "
                     "p ~ exp(open[alg]) with open = logmeanexp over >= 3 programs of the summed log-prob of the "
                     "first 48 program tokens, averaged over twin templates; sensitivity p ~ 1/rank; each mixed with "
                     "5% uniform, 'other' floored at 2%",
        "primary": "exact one-sided sign test (BASE > OPEN) on events where BASE top-1 != OPEN top-1 and exactly one "
                   "hits; minimum 5 of 5 (p = 0.031) published before scoring",
        "secondary": "Wilcoxon signed-rank on per-event log-score differences; BASE vs TWINMIN",
    },
    "minima": {"mcnemar_two_sided_6_0": 0.03125, "sign_test_one_sided_5_5": 0.03125,
               "N30_upper_bound_at_3_of_30": 0.2386},
    "analysis_code": "frozen in amendment commit 'analysis_code' before any headline is computed (deviation D-AC)",
}

DROP_ORDER = ["S1E/S2E at alpha 4", "alpha 8 at S1/S2", "forced sources beyond T2 and T10", "A3 and B3",
              "T1 prompt top-five ban", "MR_12-23 and PLACEBO on T03", "N per cell down to 30 (decisive) / 10"]
NEVER_DROP = ["ST alpha 1-4 on T03/T10 + indicator model", "top-five push", "KL-matched comparison at alpha 2",
              "Stage A bands on T2 T03 T10 T1 T05 T06", "MR_0-35", "L", "novelty audit"]


def main() -> None:
    setup_logging("prereg6")
    code = {p.name: sha256_file(p) for p in sorted((ROOT / "src").glob("*.py"))}
    inputs = {"inputs/SHA256SUMS": sha256_file(ROOT / "inputs" / "SHA256SUMS")}
    inputs.update({str(p.relative_to(ROOT)): sha256_file(p) for p in sorted((ROOT / "inputs_extra").rglob("*"))
                   if p.is_file()})
    payload = {"rules": RULES, "drop_order": DROP_ORDER, "never_drop": NEVER_DROP,
               "slot_map": {s: list(SLOT_MAP[s]) for s in range(50)}, "slots_N30": list(N30),
               "templates": list(TEMPLATES6), "tasks": list(TASKS6), "bands": BANDS,
               "dir_seed": "int(sha256('iter6_dir3|'+task+'|'+site+'|'+str(alpha)+'|'+str(slot))[:8], 16)",
               "engine": {"batch": BATCH6, "max_new": MAX_NEW6, "precision": "bf16", "sampler": "exp27 float64 "
                          "inverse-CDF CRN, vocabulary order, T = 1, no truncation, fence stop"},
               "code_sha256": code, "input_sha256": inputs,
               "planned_deviations": {
                   "D-GPU": "RTX 2000 Ada 16 GB (plan: A4500): input-embedding table on the CPU (exact lookup), "
                            "lm_head and all blocks on the GPU in bf16",
                   "D-CAP": "max_new 384 (bench) / 512 (T2) / 640 (T1) instead of 1024/1536: exp27 p99 lengths are "
                            "<= 250 / 227 / 437 tokens; truncation rate reported",
                   "D-A3B3": "A3/B3 (drop-order item 4) not run: time budget of this GPU",
                   "D-AC": "analysis code hashed in an amendment commit before scoring, not in commit #0",
                   "D-L": "L event table frozen in commit #1 (before any teacher-forced opening pass)"}}
    rec = commit("commit0", payload)
    logger.info(f"commit #0: {rec['sha256']}")


if __name__ == "__main__":
    main()
