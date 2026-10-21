#!/usr/bin/env python3
"""STEP 3: Qwen3-8B session (bf16, sdpa; layers that do not fit the 16 GB card are CPU-offloaded by accelerate).

(a) Ban-free unit ratio. Prompt-only forward passes of the exact Qwen twin prompts that produced the iteration-3
    ban-displacement norms (exp17 prompts.jsonl: 14 tasks x W1-W5). For blocks 12-23 and spec positions p:
    res[l, p, w] = ||block-l output at spec_start + p||, ratio = norm[l, p] / res[l, p, w], where norm is the
    exp13 (bench) or exp17 (T1/T2) mean ban-minus-twin displacement norm. r_Q(l) = median over (task, w, p).
    Massive-activation diagnostic: share of ||h||^2 in the top-5 channels at spec positions.
(b) Engine positive control (forward only): the generic batched push hook (src/push.py) on T03 W1, twin and
    RAND9002 alpha 1, against exp17 data/realised_norms.jsonl (FP8 run): median relative difference < 15%.
"""

from __future__ import annotations

import gc
import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg import (E13, E17, QWEN_BAND, QWEN_ID, QWEN_LAYERS, QWEN_RATIO_TASKS, QWEN_REVISION, RESULTS_DIR,
                 TEMPLATE_IDS, model_path, read_jsonl, setup_logging, write_json)
from push import block_hooks, make_push_edits

ALL_BLOCKS = list(range(12, QWEN_LAYERS))


def qwen_norms(task: str) -> np.ndarray:
    if task in ("T1", "T2"):
        return np.load(E17 / "directions" / f"norms_{task}.npy")
    z = np.load(E13 / "results" / "tensors" / f"norms_{task}.npz")
    assert list(z["layers"]) == QWEN_BAND
    return z["norm"]


@torch.no_grad()
def forward_states(model: Any, ids: list[int], a: int, b: int, blocks: list[int],
                   edits: dict | None = None) -> dict[int, torch.Tensor]:
    got: dict[int, torch.Tensor] = {}

    def cap(l):
        def g(h):
            got[l] = h[0, a:b].float().cpu()
        return g
    inp = torch.tensor([ids], device="cuda:0")
    with block_hooks(model.model.layers, edits, {l: cap(l) for l in blocks}):
        model.model(input_ids=inp, use_cache=False)
    return got


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("qwen_ratio")
    from transformers import AutoModelForCausalLM

    t0 = time.time()
    path = model_path(QWEN_ID, QWEN_REVISION)
    model = AutoModelForCausalLM.from_pretrained(path, dtype=torch.bfloat16, attn_implementation="sdpa",
                                                 device_map="auto", max_memory={0: "13GiB", "cpu": "24GiB"})
    model.eval()
    model.requires_grad_(False)
    dm = getattr(model, "hf_device_map", {})
    n_off = sum(1 for v in dm.values() if v in ("cpu", "disk"))
    logger.info(f"Qwen3-8B bf16 loaded in {time.time() - t0:.0f}s; {n_off} modules offloaded to CPU")
    prompts = {(r["task"], r["w"], r["kind"]): r for r in read_jsonl(E17 / "prompts" / "prompts.jsonl")}
    ratios: dict[str, Any] = {}
    allr = {l: [] for l in QWEN_BAND}
    allr_ox = {l: [] for l in QWEN_BAND}
    massive = []
    per_task = {}
    for t in QWEN_RATIO_TASKS:
        norm = qwen_norms(t)
        rt = []
        for w in TEMPLATE_IDS:
            p = prompts[(t, w, "twin")]
            a, b = p["p1"], p["spec_end"]
            assert b - a == norm.shape[1], f"{t}/{w}: |S| {b - a} != norm positions {norm.shape[1]}"
            st = forward_states(model, p["ids"], a, b, QWEN_BAND)
            for j, l in enumerate(QWEN_BAND):
                h = st[l]
                res = h.norm(dim=-1).numpy()
                r = norm[j] / res
                allr[l].append(r)
                rt.append(float(np.median(r)))
                sq = (h ** 2)
                top5 = sq.topk(5, dim=-1).values.sum(-1) / sq.sum(-1)
                massive.append(float(top5.mean()))
                res_ox = (sq.sum(-1) - sq.topk(5, dim=-1).values.sum(-1)).clamp(min=1e-12).sqrt().numpy()
                allr_ox[l].append(norm[j] / res_ox)
        per_task[t] = float(np.median(rt))
        logger.info(f"{t}: median ratio {per_task[t]:.4f}")
    rq = {}
    for l in QWEN_BAND:
        x = np.concatenate(allr[l])
        rq[l] = {"median": float(np.median(x)), "q25": float(np.quantile(x, 0.25)), "q75": float(np.quantile(x, 0.75)),
                 "depth": (l + 1) / QWEN_LAYERS, "n": int(x.size)}
    rq_ox = {}
    for l in QWEN_BAND:
        x = np.concatenate(allr_ox[l])
        rq_ox[l] = {"median": float(np.median(x)), "q25": float(np.quantile(x, 0.25)),
                    "q75": float(np.quantile(x, 0.75)), "depth": (l + 1) / QWEN_LAYERS, "n": int(x.size)}
    ratios = {"r_Q": rq, "r_Q_ox": rq_ox, "per_task_median": per_task,
              "definition_ox": "ratio_ox = norm_ban_disp[l,p] / ||h_twin[l,p,w] with its 5 largest-|h| channels zeroed||",
              "massive_top5_share_mean": float(np.mean(massive)), "massive_top5_share_max": float(np.max(massive)),
              "definition": "ratio[l,p,w,task] = norm_ban_disp[l,p] / ||h_twin[l,p,w]||; r_Q(l) = median over (task,w,p)",
              "model": f"{QWEN_ID}@{QWEN_REVISION}", "precision": "bf16 sdpa, accelerate CPU offload of "
              f"{n_off} modules (16 GB card)", "tasks": list(QWEN_RATIO_TASKS)}

    # (b) engine positive control: generic push hook vs exp17 realised norms (T03 W1 RAND9002 alpha 1)
    pc: dict[str, Any] = {}
    try:
        p = prompts[("T03", "W1", "twin")]
        a, b = p["p1"], p["spec_end"]
        n17 = np.load(E17 / "directions" / "norms_T03.npy")
        u = torch.tensor(np.load(E17 / "directions" / "rand_9002.npy"), dtype=torch.float32, device="cuda:0")
        clean = forward_states(model, p["ids"], a, b, ALL_BLOCKS)
        n = {l: torch.tensor(n17[j], dtype=torch.float32, device="cuda:0") for j, l in enumerate(QWEN_BAND)}
        h_ref = {l: clean[l].to("cuda:0") for l in QWEN_BAND}
        edits = make_push_edits(QWEN_BAND, a, b, u[None, :], torch.tensor([1.0], device="cuda:0"), n, h_ref)
        pushed = forward_states(model, p["ids"], a, b, ALL_BLOCKS, edits=edits)
        disp = {l: float((pushed[l] - clean[l]).norm(dim=-1).mean()) for l in ALL_BLOCKS}
        relerr = {}
        for j, l in enumerate(QWEN_BAND):
            comp = (pushed[l] - clean[l]) @ u.cpu()
            tgt = torch.tensor(n17[j])
            relerr[l] = float(((comp - tgt).abs() / tgt.abs().clamp(min=1e-6)).mean())
        ref = [r for r in read_jsonl(E17 / "data" / "realised_norms.jsonl")
               if r["task"] == "T03" and r["w"] == "W1" and r["arm"] == "RAND9002_a1.0"]
        if ref:
            r0 = ref[0]
            diffs = [abs(disp[l] - r0["disp_S_mean_norm"][str(l)]) / max(r0["disp_S_mean_norm"][str(l)], 1e-6)
                     for l in ALL_BLOCKS]
            pc = {"disp_S_mean_norm_here": disp, "disp_S_mean_norm_exp17_fp8": r0["disp_S_mean_norm"],
                  "rel_err_along_u_here": relerr, "rel_err_along_u_exp17": r0.get("rel_err_along_u"),
                  "median_rel_diff": float(np.median(diffs)), "max_rel_diff": float(np.max(diffs)),
                  "pass": bool(np.median(diffs) < 0.15 and max(relerr.values()) < 0.02),
                  "note": "bf16 (offloaded) here vs FP8 W8A8 in exp17; tolerance median rel diff < 15%"}
        else:
            pc = {"pass": None, "note": "exp17 realised_norms has no T03/W1/RAND9002_a1.0 record"}
        logger.info(f"positive control: median rel diff {pc.get('median_rel_diff')}, pass {pc.get('pass')}")
    except (KeyError, AssertionError, RuntimeError) as e:
        logger.error(f"positive control failed: {e}")
        pc = {"pass": False, "error": str(e)}
    ratios["positive_control_forward"] = pc
    ratios["positive_control_generation"] = {"run": False, "reason": "optional cell (3c) dropped first: no bf16 "
                                             "Qwen3-8B decode fits the 16 GB card without offload (logged deviation)"}
    write_json(RESULTS_DIR / "qwen_ratio.json", ratios)
    logger.info(f"STEP 3 done in {time.time() - t0:.0f}s: r_Q = {[round(v['median'], 4) for v in rq.values()]}")
    del model
    gc.collect()
    torch.cuda.empty_cache()


if __name__ == "__main__":
    main()
