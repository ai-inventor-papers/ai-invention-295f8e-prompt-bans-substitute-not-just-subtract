#!/usr/bin/env python3
"""HF pass 1: residual states at the read position R for every frame and condition.

Saves cache/hR_<task>_<group>.npy with shape [n_prompts, len(LAYERS), d] (hidden_states[l][:, -1, :],
l in LAYERS; hidden_states[l] is the output of model.model.layers[l-1]) plus an index JSON.
Also runs the layer-index hook test (hook output at layers[L-1] == hidden_states[L]).
Own process: never load vLLM here.
"""
from __future__ import annotations

import gc
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch
from loguru import logger
from transformers import AutoModelForCausalLM, AutoTokenizer

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import CACHE_DIR, LAYERS, PAD_ID, RESULTS_DIR, TASKS, resolve_model_path, set_ram_limit, setup_logger  # noqa: E402
from prompts.scaffold import all_groups, build_prompt, check_suffix, segments  # noqa: E402

BATCH = 16


def gname(group: str) -> str:
    return group.replace(":", "-").replace("+", "_")


@torch.no_grad()
def states_for(model, ids_list: list[list[int]]) -> np.ndarray:
    out = []
    for b in range(0, len(ids_list), BATCH):
        chunk = ids_list[b:b + BATCH]
        L = max(len(x) for x in chunk)
        inp = torch.full((len(chunk), L), PAD_ID, dtype=torch.long)
        att = torch.zeros((len(chunk), L), dtype=torch.long)
        for i, x in enumerate(chunk):
            inp[i, L - len(x):] = torch.tensor(x)
            att[i, L - len(x):] = 1
        pos = (att.cumsum(-1) - 1).clamp(min=0)
        res = model(input_ids=inp.cuda(), attention_mask=att.cuda(), position_ids=pos.cuda(),
                    output_hidden_states=True, use_cache=False, logits_to_keep=1)
        hs = res.hidden_states
        arr = torch.stack([hs[l][:, -1, :].float() for l in LAYERS], dim=1).cpu().numpy()
        out.append(arr)
        del res, hs
    return np.concatenate(out, axis=0)


@torch.no_grad()
def hook_layer_test(model, ids: list[int], layer: int) -> dict:
    captured = {}

    def hook(module, inp, outp):
        h = outp[0] if isinstance(outp, tuple) else outp
        captured["h"] = h[:, -1, :].float().clone()

    hd = model.model.layers[layer - 1].register_forward_hook(hook)
    try:
        res = model(input_ids=torch.tensor([ids]).cuda(), output_hidden_states=True, use_cache=False,
                    logits_to_keep=1)
    finally:
        hd.remove()
    ref = res.hidden_states[layer][:, -1, :].float()
    diff = (captured["h"] - ref).abs().max().item()
    return {"layer": layer, "max_abs_diff": diff, "ref_norm": ref.norm().item(), "pass": bool(diff <= 1e-2 * max(1.0, ref.abs().max().item()))}


@logger.catch(reraise=True)
def main() -> None:
    setup_logger("hf_states")
    # RLIMIT_AS is incompatible with the CUDA driver (it reserves huge virtual ranges); GPU processes rely on
    # the container cgroup limit instead and keep host RAM use to the model load (~16 GB).
    t0 = time.time()
    mp = resolve_model_path()
    tok = AutoTokenizer.from_pretrained(mp)
    model = AutoModelForCausalLM.from_pretrained(mp, torch_dtype=torch.bfloat16, attn_implementation="sdpa")
    model = model.cuda().eval()
    logger.info(f"model loaded in {time.time() - t0:.1f}s; layers={len(model.model.layers)}")
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    index: dict = {"layers": LAYERS, "groups": {}}
    maxabs = 0.0
    for task in TASKS:
        for group in all_groups(task):
            segs = segments(task, group)
            ids_list = [build_prompt(tok, s, task) for s in segs]
            for ids in ids_list:
                check_suffix(tok, ids, task)
            t1 = time.time()
            arr = states_for(model, ids_list)
            maxabs = max(maxabs, float(np.abs(arr).max()))
            norms = np.linalg.norm(arr, axis=-1)  # [n, n_layers]
            fn = CACHE_DIR / f"hR_{task}_{gname(group)}.npy"
            np.save(fn, arr.astype(np.float16) if np.abs(arr).max() < 6e4 else arr.astype(np.float32))
            index["groups"][f"{task}|{group}"] = {
                "file": fn.name, "n": len(segs), "segments": segs, "n_tokens": [len(x) for x in ids_list],
                "mean_norm_per_layer": norms.mean(0).round(3).tolist(),
            }
            logger.info(f"{task} {group}: {arr.shape} in {time.time() - t1:.1f}s (max|h|={np.abs(arr).max():.1f})")
    index["max_abs_value"] = maxabs
    (CACHE_DIR / "hR_index.json").write_text(json.dumps(index, indent=1))
    # Hook test (a): hook output at layers[L-1] equals hidden_states[L]
    ids = build_prompt(tok, segments("T1", "baseline")[0], "T1")
    tests = [hook_layer_test(model, ids, L) for L in (8, 18, 28)]
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "hook_layer_test.json").write_text(json.dumps(tests, indent=1))
    logger.info(f"hook layer tests: {tests}")
    logger.info(f"done in {time.time() - t0:.1f}s")
    del model
    gc.collect()
    torch.cuda.empty_cache()


if __name__ == "__main__":
    main()
