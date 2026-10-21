#!/usr/bin/env python3
"""GPU unit tests U1-U3 (prompt-only and short sampling; no ban prompt is sampled before commit #1 except U7)."""

from __future__ import annotations

import time
from typing import Any

import numpy as np
import torch
from loguru import logger

from cfg import RESULTS_DIR, V_BLOCKS, write_json
from engine import forward_capture, sample, u_stream
from hooks import head_masks, make_edits
from sampling import TaskContext


def run_gpu_tests(model: Any, tok: Any, prompts: dict) -> dict[str, Any]:
    t0 = time.time()
    res: dict[str, Any] = {}
    task, w = "T2", "W1"
    ctx = TaskContext(model, tok, prompts, task)
    twin = ctx.clean_prefill(w, "twin")
    us = [u_stream("unit", task, w, k) for k in range(20)]
    # U1 CRN determinism
    a = sample(model, [{"pre": twin["pre"], "us": us}], max_new=48)
    b = sample(model, [{"pre": twin["pre"], "us": us}], max_new=48)
    res["U1_crn_determinism"] = all(x["token_ids"] == y["token_ids"] for x, y in zip(a, b))
    # U2a ADD alpha=0 with u = vhat -> identical ids to the clean twin
    a_ = ctx.clean_prefill(w, "twin")
    edits = make_edits("ADD", a_["a"], a_["b"], ctx.vhat, ctx.n, {l: a_["S"][l] for l in V_BLOCKS}, alpha=0.0)
    from engine import prefill
    pre_a0 = prefill(model, prompts[(task, w, "twin")]["ids"], edits=edits)
    c = sample(model, [{"pre": pre_a0, "us": us}], max_new=48)
    res["U2a_add_alpha0_identical_ids"] = all(x["token_ids"] == y["token_ids"] for x, y in zip(a, c))
    res["U2a_r_logits_max_abs_diff"] = float((pre_a0["r_logits"] - twin["pre"]["r_logits"]).abs().max())
    # U2b realised displacement along u equals alpha * n (relative error < 2%)
    _, rec1 = ctx.arm_prefill(w, "ADD_a1.0")
    _, rec2 = ctx.arm_prefill(w, "RAND9001_a2.0")
    res["U2b_rel_err_along_u_ADD1_max"] = max(rec1["rel_err_along_u"].values())
    res["U2b_rel_err_along_u_RAND2_max"] = max(rec2["rel_err_along_u"].values())
    res["U2b_pass"] = res["U2b_rel_err_along_u_ADD1_max"] < 0.02 and res["U2b_rel_err_along_u_RAND2_max"] < 0.02
    # U2c SUB_plain leaves |h . vhat| < 1e-2 ||h|| (checked on the TWIN prompt here: no ban prompt before commit #1)
    tw = prompts[(task, w, "twin")]
    cap: dict[int, torch.Tensor] = {}
    ed = make_edits("SUB_plain", tw["p1"], tw["spec_end"], ctx.vhat, None, None)

    def mk(l):
        def g(h):
            cap[l] = h[0, tw["p1"]:tw["spec_end"]].float()
        return g
    prefill(model, tw["ids"], edits=ed, capture={l: mk(l) for l in V_BLOCKS})
    ratios = {l: float(((cap[l] @ ctx.vhat[l]).abs() / cap[l].norm(dim=-1)).max()) for l in V_BLOCKS}
    res["U2c_sub_plain_max_ratio"] = max(ratios.values())
    res["U2c_pass"] = res["U2c_sub_plain_max_ratio"] < 1e-2
    # U2d head-ablation identity: masks active but selecting nothing -> ids identical; hook skips the prefill
    masks = head_masks([[] for _ in range(20)], model.device)
    masks = {21: torch.zeros(20, 4096, dtype=torch.bool, device=model.device)}
    d = sample(model, [{"pre": twin["pre"], "us": us}], max_new=48,
               heads={"masks": masks, "mus": {21: torch.zeros(4096, device=model.device)}})
    res["U2d_heads_identity_ids"] = all(x["token_ids"] == y["token_ids"] for x, y in zip(a, d))
    # U3 teacher-forced states at generated positions 1..8 vs states recorded while sampling (block 20)
    e = sample(model, [{"pre": twin["pre"], "us": us}], max_new=16, record_block=20, record_steps=8)
    P = tw["P"]
    ids5 = [tw["ids"] + r["token_ids"][:9] for r in e[:5] if r["n_tokens"] >= 9]
    fc = forward_capture(model, ids5, [20], [P + k - 1 for k in range(1, 9)])
    diffs, shifted = [], []
    fc2 = forward_capture(model, ids5, [20], [P + k for k in range(1, 9)])  # off-by-one positions (k+1)
    for i, r in enumerate(e[:len(ids5)]):
        # decode step s (0-based) processes generated token s+1 at position P+s -> generated position k = s+1
        rec = r["rec"][:8]
        tf = fc["states"][20][i].numpy()
        tf2 = fc2["states"][20][i].numpy()
        diffs.append(np.linalg.norm(rec - tf, axis=-1) / np.linalg.norm(tf, axis=-1))
        shifted.append(np.linalg.norm(rec - tf2, axis=-1) / np.linalg.norm(tf2, axis=-1))
    d_al = np.concatenate(diffs) if diffs else np.array([np.nan])
    d_sh = np.concatenate(shifted) if shifted else np.array([np.nan])
    res["U3_max_rel_diff_sampling_vs_teacher_forced"] = float(d_al.max())
    res["U3_mean_rel_diff_aligned"] = float(d_al.mean())
    res["U3_mean_rel_diff_off_by_one"] = float(d_sh.mean())
    # FP8 W8A8: decode (M=20) and prefill GEMM shapes differ, so tiny accumulation differences flip FP8 roundings and
    # the same state differs by a few percent. The test confirms the POSITION convention: aligned << off-by-one.
    res["U3_pass"] = bool(diffs) and float(d_al.max()) < 0.15 and float(d_al.mean()) < 0.25 * float(d_sh.mean())
    res["seconds"] = time.time() - t0
    res["all_pass"] = bool(res["U1_crn_determinism"] and res["U2a_add_alpha0_identical_ids"] and res["U2b_pass"]
                           and res["U2c_pass"] and res["U2d_heads_identity_ids"] and res["U3_pass"])
    write_json(RESULTS_DIR / "unit_tests_gpu.json", res)
    logger.info(f"GPU unit tests: {res}")
    return res
