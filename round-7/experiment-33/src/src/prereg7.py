#!/usr/bin/env python3
"""STEP 2: commit #0 (before any decisive sample): inputs, model revision, split, every rule and threshold, the cell
list, seeds and the committed point forecasts (PREDICTIONS are scored, not thresholds)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg import INPUTS, ROOT, setup_logging, sha256_file
from cfg7 import (BAND, CATALOGUE7, DEFAULT7, HELD_FAM, HELD_W, K_MAX, MAX_NEW7, N_PI, N_TGT, PROFILE_LAYERS,
                  PROMPTS7, RANKS, SEEDS, TRAIN_FAM, TRAIN_NOUNS, TRAIN_W, VAL_NOUNS)
from commit7 import commit

DESIGN = {
    "model": {"id": "Qwen/Qwen3-8B", "revision": "b968826d9c46dd6066d109eabc6255188de91218", "precision": "bf16",
              "thinking": False},
    "split": {"ban_twin_train": {"templates": TRAIN_W, "nouns": TRAIN_NOUNS},
              "validation_bases": {"templates": TRAIN_W, "nouns": VAL_NOUNS},
              "held_out": {"template": HELD_W, "nouns": "all 12"}, "W4": "reported separately",
              "forced_train_families": TRAIN_FAM, "forced_held_families": HELD_FAM},
    "kept_Y_rule": "correct-Y adherence >= 0.7 over N = 20 forced samples (4 per family, all 5 families)",
    "padding_twin_rule": "pooled default share >= 0.9 per Y (N = 20); a (k, Y) cell with < 3 of 4 default is excluded",
    "ban_landing_rule": "algorithms with share >= 0.2 of the W1-W3 ban samples (N = 30), correct programs",
    "target_rule": f"{N_PI} correct programs per algorithm (ban samples first for the ban's landing algorithm, then "
                   f"TRAIN-family forced samples), first {N_TGT} response tokens, exact generated ids, programs with < "
                   f"{N_TGT} tokens excluded (T03 fallback: >= 16 tokens, flagged), clean openings preferred; "
                   "default set from the W1-W3 noun-0 twins; disjoint validation sets of 3",
    "objective": "C = LME_{Pi_Y} ll - LME_{Pi_D} ll over the first 48 response tokens; loss = -C_k",
    "map_class": f"Linear(4096 -> {K_MAX}) under parametrizations.orthogonal, nested ranks {RANKS}, fp32",
    "fit_budget": "Adam lr 2e-3, 4 micro-batches of 1 pair per step (stratified by source context), 150 steps, "
                  "rank cycled [16,8,4,2,1] by micro-batch, validation every 25 steps (TRAIN sources -> VAL bases, "
                  "all ranks), best state kept, early stop after 3 non-improving validations; equal budget for every "
                  "control fit; +75 steps for every fit of a task if the main fit is still improving at 150",
    "layer_profile_rule": f"teacher-forced full-state exchange at single blocks {PROFILE_LAYERS} + bands 12-23, 0-35 + "
                          "read position on 24 aligned TRAIN pairs; L* = argmax mean gain, ties within 0.25 nats to "
                          "the smaller block",
    "band_fallback_rule": f"if TRANSFER(full@L*) < 0.5 x TRANSFER(band {BAND[0]}-{BAND[-1]}) on the W5 ban source in "
                          "generation, the map is ONE R shared over blocks 12-23 and every later step uses that site",
    "k_star_rule": "smallest k with generation RECOVERY_k >= 0.8 on the ban source, else 16",
    "P1": "PASS on a task if some k <= 16 has RECOVERY_k >= 0.8 AND RECOVERY_k - RECOVERY_random_k >= 0.4 AND exact "
          "McNemar DAS vs random (correct-Y, paired by slot, pooled over held-out sources at that k) p < 0.01 after "
          "Holm across tasks AND permuted-label TRANSFER <= 0.1 AND pass >= 0.8 x BASE pass; on T2 also random-init "
          "held-out TF gain < 0.5 x trained gain. Overall PASS on >= 2 tasks. DISCONFIRMED if RECOVERY_16 < 0.5 on "
          "every task.",
    "C": "routing(Y) = #correct Y / #correct off-default; CATEGORICAL if routing >= 0.6 for >= 2 non-default Y on >= 2 "
         "tasks at the P1 k; MARGIN-AND-LADDER if routing <= 0.2 for every Y other than the runner-up while "
         "off-default TRANSFER >= 0.5; else MIXED; a Y whose full-state exchange does not route (< 0.6) is 'not "
         "routable at this site'",
    "dormant_flag": "projected-map TF retention < 0.5 OR reverse recovery < 0.5 while forward recovery >= 0.8",
    "M": "z = mean over spec positions of R_16 h at the site; paraphrase null = distances of 60 twins + padtwins + P0 "
         "to the default-condition centroid; seeds/instructions scored by percentile",
    "R": "lambda in {0,0.2,0.4,0.5,0.6,0.7,0.8,1.0,1.25,1.5}, N = 20 each; logistic width = 2 s ln 9; DISCRETE if "
         "width <= 0.3 and hybrids <= 5% of correct programs",
    "novelty_rule": "every correct 'other' program -> two blind judges of different families + nearest known "
                    "solutions; 'no correct novel algorithm' claimed only at a count of 0",
    "generation": {"N_decisive": 30, "slots": "0-29 CRN shared by every arm", "max_new": MAX_NEW7,
                   "sampler": "exp30 float64 inverse-CDF CRN, T = 1, top-p 1, no top-k, fence stop"},
    "cells": ["BASE W5 twin (nouns cycle slot mod 12)", "BASE pooled padtwin (family 3 + s mod 2, kept Y (s div 2) mod "
              "|Y|)", "FULL ban W5 [Stage 0]", "FULL-STATE ban + each kept forced Y", "DAS k 1,2,4,8,16 ban; 1,4,16 "
              "forced Y", "RANDOM k16 x3 ban; k16 x1 forced; k* x1 ban", "PERMUTED k16 + k* ban; k16 one forced Y",
              "RPOS DAS k16 + full-state at R", "NULL 'Implement <default>' DAS k16 + full-state", "REVERSE DAS k* + "
              "full-state reverse", "DIM-1, PCA-16 ban", "W4 k* N = 10"],
    "catalogues": CATALOGUE7, "defaults": DEFAULT7, "seeds": SEEDS,
}
PREDICTIONS = {
    "L_star": "a single block in 14-20, or the band fallback on T10",
    "full_state_transfer_T2_ban_at_site": ">= 0.5",
    "k_star": "in {2, 4, 8} on T2 and T10",
    "P1": "PASS on T2 and T10",
    "controls": {"permuted": "<= 0.1", "random_rank16": "<= 0.15", "rpos": "<= 0.05", "null_source": "<= 0.1",
                 "random_init_gain": "< 0.2 x trained"},
    "C": "CATEGORICAL on T10 (forced BFS -> BFS, forced DFS -> DFS); MARGIN-AND-LADDER or not-routable for "
         "Floyd-Warshall / Dial on T2",
    "M": "random seeds inside the paraphrase null; the semantic seed outside it",
    "R": "transition width <= 0.3",
}


def main() -> None:
    setup_logging("prereg7")
    files = [PROMPTS7] + sorted((ROOT / "src").glob("*.py"))
    payload = {"design": DESIGN, "predictions": PREDICTIONS,
               "sha256": {str(p.relative_to(ROOT)): sha256_file(p) for p in files},
               "inputs_sha256sums": sha256_file(INPUTS / "SHA256SUMS"),
               "note": "analysis code (src/analysis7.py) is frozen in an amendment commit before any held-out "
                       "generation is scored (deviation: not in commit #0)"}
    c = commit("commit0", payload)
    print(c)


if __name__ == "__main__":
    main()
