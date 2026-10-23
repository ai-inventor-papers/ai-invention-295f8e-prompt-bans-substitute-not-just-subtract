#!/usr/bin/env python3
"""COMMIT #0 (before anything touches the GPU): map class, objective, readout, every control and threshold, verdict
rules, the p_K2 rule, cell lists and N, the drop order, declared departures, analysis-code and input hashes."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg8 import (FIT_STEPS, INPUTS, LR, N_RANDOM_SUBSPACES, OFF_MANIFOLD, PROSPECTIVE_SEEDS, RANKS, ROOT, SCAN_STEPS,
                  THRESH, setup_logging, sha256_file, utc_now, write_json)
from commit8 import commit

PROTOCOL = {
    "map_class": "linear orthonormal R (d_model x 8) = QR(W)[:, :k], nested ranks k in {1, 2, 4, 8}, one rank sampled "
                 "per step; interchange h <- h + R (R^T h_src - R^T h_base). Declared before any fit (Sutter et al.).",
    "objective": "KL(q_src || q_edit) over the class bins {classes..., other} at the decision position d (bounded, "
                 "CDAS-style). Label controls: target = class-mean q of the permuted class. Random-init network: "
                 "target = the TRAINED model's q_src.",
    "readout": "Delta = margin_edit - margin_base, margin = log P(class_src) - log P(class_base) at d, computed on "
               "the same path (KV path at the decision site; recompute path at the band).",
    "recovery": "mean(Delta_DAS) / mean(Delta_FULL) over held-out pairs with |Delta_FULL| >= 1 nat; 95% CI from "
                "2,000 two-way cluster bootstrap resamples (source prompts x base prompts); OFF-MANIFOLD flag if "
                f"recovery > {OFF_MANIFOLD}",
    "sites": {"dec": "block L* = argmax rank-1 2-fold leave-family-out CV recovery over blocks 0,2,4,..; edit of the "
                     "block-L* OUTPUT at d with the canonical opening prefilled",
              "band": "Qwen T10 blocks 12-23 x every spec position, one shared R"},
    "fit": {"steps": FIT_STEPS, "scan_steps": SCAN_STEPS, "optimizer": "Adam", "lr": LR,
            "batch": "decision site 4 bases x 12 sources (48 pairs); band 8 pairs",
            "early_stopping": "inner-validation KL (mean over ranks) every 20 steps on one rotated-out train family; "
                              "patience 3; best state kept", "init": "W ~ N(0, 1) with torch seed 1000 + fit seed",
            "seeds": [0, 1, 2]},
    "k_star": "smallest rank whose held-out TF recovery (seed 0) >= 0.9 x the best rank",
    "controls": {
        "c1": f"{N_RANDOM_SUBSPACES} Haar subspaces per rank (seeds 7000+i): median recovery <= {THRESH['c1_median_max']}",
        "c2": "label-control refits (seeds 10, 11, 12; same steps/early stopping): cyclic derangements pi1, pi2 and a "
              "prompt-level balanced derangement; pairs whose permuted target equals class_base dropped; PRIMARY: "
              f"held-out recovery toward the TRUE class <= {THRESH['c2_ratio_max']} x true-fit recovery",
        "c3": f"randomly initialised network (same config, torch seed 0, HF _init_weights), same map class, objective "
              f"(trained q_src targets), readout, pairs and steps: mean held-out Delta (random-init / trained) <= "
              f"{THRESH['c3_ratio_max']}",
        "c4": f"reverse interchange (base = held-out forced source, source = its padding twin): DAS / full-state "
              f"reverse >= {THRESH['c4_min']}",
        "c5": f"projected-map retention on the top 64 natural twin PCs at (L*, d) >= {THRESH['c5_min']}; c5b with "
              f"twins + forced + placement prompts (sensitivity, never substituted)",
        "c6": "natural-variance share tr(R^T S R)/tr(S) above the 95th percentile of 1,000 random rank-k subspaces; "
              "c6b on the c5b basis",
        "c7": f"principal angles among the 3 seeds at k*: median first principal cosine >= {THRESH['c7_cos_min']} and "
              f"above the random 99th percentile"},
    "verdicts": {
        "V0": "held-out TF recovery at k* >= 0.5 (CI lower bound > 0.25) AND generation recovery >= 0.5 with pass "
              "ratio >= 0.8 AND McNemar DAS > RAND at p < 0.05",
        "CERTIFIED VARIABLE": "V0 and c1-c7 all pass",
        "SUFFICIENT HANDLE": "V0 and c1 pass but some of c2-c7 fail (named)",
        "NO HANDLE": "V0 fails",
        "K2": "confirmed iff T10-dec and GRID-dec are both CERTIFIED; disconfirmed iff a decision site fails c2 or c3 "
              "in either family; p_K2 = max over {T10-dec, GRID-dec} of max(p_c2, p_c3) (intersection-union)",
        "committed_prediction": "both decision sites certified; T10 band passes V0 but fails c4, c5 and the clamp"},
    "generation": {"decoding": "T 1.0, top-p 1, no top-k; CRN: one uniform stream per (unit, site, slot) shared by "
                               "every arm; fence stop", "N_decisive": 30, "N_supporting": 20,
                   "cells_per_off_default_class": ["FULL 30", "DAS k* 30", "RAND k* 30", "PERM k* 20", "REV-DAS 20",
                                                   "REV-FULL 20", "SRC 20"], "BASE": 30,
                   "primary_class_extra_ranks": "the two ranks of {1, 2, 4} other than k*, 30 each",
                   "decision_cells": "prompt + canonical opening prefilled; edit at d at L* in the prefill",
                   "band_cells": "edit at the band's spec positions in the prefill; free generation from index 0"},
    "mediation": {"predictor": "pi_u = max_c <z_u, g_c> / ||g_c||^2 (band subspace at k*)",
                  "test": "Spearman(pi, escape) >= 0.5; partial Spearman controlling ||D_u||",
                  "clamp": "10 most-escaping directions, PUSH / PUSH+TASK-CLAMP / PUSH+RAND-CLAMP (N = 30), "
                           "PUSH+DEC-CLAMP (N = 10); pass: TASK removal >= 0.5 and RAND <= 0.10",
                  "prospective_seeds": list(PROSPECTIVE_SEEDS)},
    "drop_order": ["Gemma task-site fit", "rank 8 in generation", "third seed at the task site", "B3 at the task site",
                   "supporting cells 20 -> 10"],
    "declared_departures_at_commit0": [
        "Hardware: one NVIDIA L4 (23 GB, 300 GB/s), 6 CPUs, 57 GB RAM instead of the planned RTX A4500; ~5.5 h total.",
        "B3 (Kruskal/Prim/Boruvka) is dropped at commit #0 (replication unit; not in the never-dropped list); the "
        "Gemma task band is dropped (drop order item 1).",
        "T10 forced sources use 4 display-name paraphrases per template (k x j = 20 per class) so held-out pairs span "
        "8 source prompts per class; (k, j=0) reproduces iteration 7's forced prompts exactly.",
        "Labeller disagreements are not sent to the blind judge (OpenRouter is reserved for the novelty audit): T10 "
        "keeps the runtime label flagged 'runtime_unjudged'; GRID marks them 'disputed' (iteration-7 rule).",
        "T10 max_new_tokens 512 after the opening (iteration-7 T10 programs: median 132, max 384)."],
}


def main() -> None:
    setup_logging("commit0")
    code = {p.name: sha256_file(p) for p in sorted((ROOT / "src").glob("*.py"))}
    payload = {"utc": utc_now(), "protocol": PROTOCOL, "thresholds": THRESH, "ranks": list(RANKS),
               "analysis_code_sha256": code,
               "input_hashes_sha256": sha256_file(INPUTS / "input_hashes.json"),
               "prompts_sha256": {p.name: sha256_file(p) for p in sorted((ROOT / "prompts").glob("*.jsonl"))}}
    h = commit("commit0", payload)
    write_json(ROOT / "results" / "commit0_done.json", {"hash": h})
    print(h)


if __name__ == "__main__":
    main()
