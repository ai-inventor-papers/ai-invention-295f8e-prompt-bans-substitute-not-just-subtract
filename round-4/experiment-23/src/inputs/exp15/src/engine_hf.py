#!/usr/bin/env python3
"""HF session (E1, E2, T4): prompt-only ban-displacement norms n_{l,i} at the task-specification positions of decoder
layers 11..21 (hidden_states[l+1], fp32 differences), seeded random unit directions, and the hook tests.

n_{l,i} = mean over W1..W5 of || h_{l,i}(ban_w(D)) - h_{l,i}(twin_w(D), h=0) ||, i = offset from spec_start.
No ban is sampled here (forward passes only)."""

from __future__ import annotations

import hashlib
import time
from typing import Any

import numpy as np
import torch
from loguru import logger

from src import prompts_llama as P
from src.ws import PUSH_LAYERS, RANDDIR_SEEDS, RESULTS, model_path, write_json


def load_model():
    from transformers import AutoModelForCausalLM

    t0 = time.time()
    m = AutoModelForCausalLM.from_pretrained(model_path(), dtype=torch.bfloat16, attn_implementation="sdpa")
    m = m.to("cuda")
    m.eval()
    logger.info(f"HF model loaded in {time.time() - t0:.0f}s")
    return m


@torch.no_grad()
def hidden(model, ids: list[int]) -> tuple:
    x = torch.tensor([ids], device="cuda")
    out = model(input_ids=x, output_hidden_states=True, use_cache=False)
    return out.hidden_states


@torch.no_grad()
def ban_norms(model, task: str, D: str) -> dict[str, Any]:
    per_w = []
    S = None
    for w in range(1, 6):
        ban = P.p_ban(task, D, w)
        tw = P.p_twin(task, D, w, 0, family="normtwin")
        assert len(ban["ids"]) == len(tw["ids"]) and ban["spec_start"] == tw["spec_start"]
        s0, s1 = ban["spec_start"], ban["spec_end"]
        S = s1 - s0 + 1
        hb = hidden(model, ban["ids"])
        ht = hidden(model, tw["ids"])
        rows = []
        for l in PUSH_LAYERS:
            d = (hb[l + 1][0, s0:s1 + 1].float() - ht[l + 1][0, s0:s1 + 1].float()).norm(dim=-1)
            rows.append(d.cpu().numpy())
        per_w.append(np.stack(rows))  # [L, S]
        del hb, ht
    arr = np.stack(per_w)  # [W, L, S]
    n = arr.mean(0)
    return {"task": task, "D": D, "S": int(S), "norms": n.tolist(), "per_layer_mean": n.mean(1).tolist(),
            "per_template_layer_mean": arr.mean(2).tolist(),
            "spec_start_by_w": {w: P.p_ban(task, D, w)["spec_start"] for w in range(1, 6)}}


def directions(seed: int, d: int = 4096) -> torch.Tensor:
    g = torch.Generator(device="cpu").manual_seed(int(seed))
    rs = []
    for _ in PUSH_LAYERS:
        r = torch.randn(d, generator=g, dtype=torch.float32)
        rs.append(r / r.norm())
    return torch.stack(rs)  # [L, d]


def directions_record() -> dict[str, Any]:
    out = {}
    for s in RANDDIR_SEEDS:
        t = directions(s)
        out[str(s)] = {"sha256": hashlib.sha256(t.numpy().tobytes()).hexdigest(), "shape": list(t.shape),
                       "dtype": "float32", "rule": "torch.Generator(cpu).manual_seed(seed); per layer 11..21 in order "
                       "randn(4096) / norm; shared across positions"}
    return out


@torch.no_grad()
def hook_tests(model, task: str, D: str, norms: np.ndarray, X0: str) -> dict[str, Any]:
    """T4 (HF part): perturbation only at spec positions of layers 11..21 in one forward pass; added-norm check;
    realised cumulative displacement at layer 21 (descriptive: pushes at 11..20 propagate)."""
    p = P.p_twin(task, X0, 1, 0)
    s0, s1 = p["spec_start"], p["spec_end"]
    S = s1 - s0 + 1
    R = directions(RANDDIR_SEEDS[0]).to("cuda")
    nt = torch.tensor(norms, device="cuda", dtype=torch.float32)  # [L, S]
    handles = []
    added = []

    def mk(li):
        def hook(mod, args, output):
            hs = output[0] if isinstance(output, tuple) else output
            if hs.shape[1] > 1:
                add = (nt[li][:, None] * R[li][None, :]).to(hs.dtype)
                hs[0, s0:s1 + 1] += add
                added.append(float(add.float().norm(dim=-1).mean() / nt[li].mean()))
            return output
        return hook

    base = hidden(model, p["ids"])
    for li, l in enumerate(PUSH_LAYERS):
        handles.append(model.model.layers[l].register_forward_hook(mk(li)))
    pert = hidden(model, p["ids"])
    for h in handles:
        h.remove()
    res = {"task": task, "prompt": "X0 twin W1 h0", "S": S}
    # before layer 11 output: hidden_states[11] is the output of layer 10 -> must be identical everywhere
    res["max_abs_diff_layer10_out"] = float((pert[11] - base[11]).abs().max())
    d11 = (pert[12][0] - base[12][0]).float().norm(dim=-1)
    nz = (d11 > 0).nonzero().flatten().tolist()
    res["layer11_nonzero_positions_equal_spec"] = (nz == list(range(s0, s1 + 1)))
    res["layer11_nonzero_n"] = len(nz)
    pre = (pert[22][0, :s0] - base[22][0, :s0]).abs().max()
    res["max_abs_diff_before_spec_layer21"] = float(pre)
    d21 = (pert[22][0, s0:s1 + 1] - base[22][0, s0:s1 + 1]).float().norm(dim=-1)
    res["added_norm_ratio_mean"] = float(np.mean(added))
    res["realised_cum_disp_l21_over_n21_mean"] = float((d21 / nt[-1]).mean())
    res["expected_if_independent_sqrt_sum_sq_over_n21"] = float((nt.pow(2).sum(0).sqrt() / nt[-1]).mean())
    res["passed"] = (res["max_abs_diff_layer10_out"] == 0.0 and res["layer11_nonzero_positions_equal_spec"]
                     and res["max_abs_diff_before_spec_layer21"] == 0.0 and abs(res["added_norm_ratio_mean"] - 1) < 0.02)
    return res


def run(D_by_task: dict[str, str], X0: dict[str, str]) -> dict[str, Any]:
    model = load_model()
    out = {"layers": PUSH_LAYERS, "tasks": {}}
    for t, D in D_by_task.items():
        t0 = time.time()
        out["tasks"][t] = ban_norms(model, t, D)
        logger.info(f"norms {t} ban:{D} S={out['tasks'][t]['S']} mean per layer "
                    f"{np.round(out['tasks'][t]['per_layer_mean'], 2).tolist()} ({time.time() - t0:.1f}s)")
    out["directions"] = directions_record()
    write_json(RESULTS / "ban_norms.json", out)
    t = next(iter(D_by_task))
    ht = hook_tests(model, t, D_by_task[t], np.array(out["tasks"][t]["norms"]), X0[t])
    write_json(RESULTS / "tests_hooks_hf.json", ht)
    logger.info(f"T4 HF hook test: {ht}")
    del model
    torch.cuda.empty_cache()
    return out
