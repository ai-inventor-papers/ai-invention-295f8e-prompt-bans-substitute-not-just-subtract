#!/usr/bin/env python3
"""COMMIT #1b (amendment; before ANY transplant sample, decided on the activation statistics only).

The plan's literal massive-channel rule (union over all prompts, band blocks and spec positions of the per-position
top-5 |h| channels) returned 488 channels, because at most positions the top-5 holds 1-3 truly massive channels plus
position-specific ordinary ones. With that M, the matched-random (RND) and cross-task (XT) controls would copy the
transplant's own displacement on 488 of 2,560 channels (51-92% of ||d||^2 by block), defeating their purpose (the
design wants them matched where the model is sensitive and scrambled everywhere else). The amendment keeps the
design's N_MASSIVE = 5: M* = the 5 channels most often in the per-position top-5 (channel 443 is in every cell's top-5
and alone carries ~99% of ||h||^2). The literal set stays in commit_E1.json and is reported as a sensitivity of the
norm report; RND/XT/T use M*."""

from __future__ import annotations

import collections
import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg import ALL_TASKS, CACHE_DIR, DATA_DIR, N_MASSIVE, PRED_DIR, RESULTS_DIR, TEMPLATE_IDS, read_json, \
    setup_logging, write_json
from commit import commit, verify_chain
from predictors import transplant_norms


def main() -> None:
    setup_logging("amend_M")
    from loguru import logger

    assert not (DATA_DIR / "raw_transplant.jsonl").exists() and not (DATA_DIR / "raw_transplant_valid.jsonl").exists(), \
        "the amendment must precede every transplant sample"
    cnt: collections.Counter = collections.Counter()
    n = 0
    for t in ALL_TASKS:
        for w in TEMPLATE_IDS:
            S = torch.load(CACHE_DIR / f"hit_{t}_{w}.pt")["S"].float()
            top = S.abs().topk(N_MASSIVE, dim=-1).indices
            cnt.update(top.flatten().tolist())
            n += top.shape[0] * top.shape[1]
    freq = {int(c): v / n for c, v in cnt.most_common(30)}
    M_star = sorted(int(c) for c, _ in cnt.most_common(N_MASSIVE))
    sh = []
    for t in ALL_TASKS:
        for w in TEMPLATE_IDS:
            S2 = torch.load(CACHE_DIR / f"hit_{t}_{w}.pt")["S"].float() ** 2
            sh.append(float((S2[..., M_star].sum(-1) / S2.sum(-1)).mean()))
    c1 = read_json(PRED_DIR / "commit_E1.json")
    tasks = c1["transplant"]["S_T"] + c1["transplant"]["S_C"]
    norms_star = transplant_norms(M_star, tasks)
    rec = {"M_star": M_star, "M_star_size": len(M_star), "M_star_share_of_h2_mean": sum(sh) / len(sh),
           "rule": f"the N_MASSIVE = {N_MASSIVE} channels most often among the per-position top-{N_MASSIVE} |h| channels "
                   "of the it twin (all prompts, blocks 11-22, spec positions)",
           "top_channel_frequencies": freq, "n_cells": n,
           "literal_M_size": c1["transplant"]["M_size"],
           "literal_M_share_of_h2_mean": c1["transplant"]["M_share_of_h2_mean"],
           "why": __doc__, "transplant_norms_M_star": norms_star,
           "transplant_norms_literal_M": c1.get("transplant_norms")}
    write_json(PRED_DIR / "commit_E1b_M.json", rec)
    write_json(RESULTS_DIR / "transplant_norms.json", {**norms_star, "M": "M_star (commit #1b)",
                                                       "literal_M_version": c1.get("transplant_norms")})
    r = commit("commit1b_massive_set_amendment_before_any_transplant_sample", [PRED_DIR / "commit_E1b_M.json"],
               note="validity-only amendment of M (no transplant sample exists)")
    logger.info(f"M* = {M_star} (share {rec['M_star_share_of_h2_mean']:.4f}); commit #1b {r['hash'][:16]}; "
                f"chain {verify_chain()}; median units {norms_star['overall_median_units']:.2f}")


if __name__ == "__main__":
    main()
