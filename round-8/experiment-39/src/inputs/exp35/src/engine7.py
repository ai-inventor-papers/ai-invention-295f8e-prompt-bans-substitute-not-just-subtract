#!/usr/bin/env python3
"""engine7: the iteration-6 bf16 HF engine reused (vendored, unmodified) with one added decoder variant.

Reused unchanged from inputs/iter6_exp30/src (byte copies of exp27/iteration 6):
  engine_v4.block_hooks / _inverse_cdf / backtick_ids / fence_closed, engine5.decode_rows (float64 CRN sampler:
  softmax(logits / T_row) in float64 -> top-k mask (keep p >= k-th largest) -> cumsum over the FULL vocabulary in
  TOKEN-ID order, normalised by the kept mass -> searchsorted(u)), engine5.step_probs5, hooks.make_edits.
Added here:
  load_model()      bf16 Qwen3-8B fully on the GPU (24 GB card: the input embedding needs no CPU fallback; the
                    iteration-6 rule 'CPU embedding if free VRAM < 18 GiB before load' is kept).
  prefill()         engine_v4.prefill with the KV kept on the GPU.
  decode_stop()     engine5.decode_rows with one extra stop rule: every `check_every` steps a host callback may mark
                    rows finished (used ONLY for prefix-resampling continuations, where a row stops once the opening
                    classifier decides its algorithm). Its per-step sampling transform is identical (same functions).
  teacher_force()   one batch-1 forward over prompt + continuation returning fp32 logits at the predicting positions
                    and optional block-output captures.
"""

from __future__ import annotations

import gc
import sys
import time
from typing import Any, Callable

import numpy as np
import torch
from loguru import logger

from cfg7 import I6_SRC, MODEL_ID, MODEL_REVISION, model_path

if str(I6_SRC) not in sys.path:
    sys.path.append(str(I6_SRC))

import engine5 as E5  # noqa: E402
import engine_v4 as E4  # noqa: E402
import hooks as H4  # noqa: E402

decode_rows = E5.decode_rows
step_probs5 = E5.step_probs5
inverse_cdf = E4._inverse_cdf
block_hooks = E4.block_hooks
fence_closed = E4.fence_closed


def load_model(vram_fraction: float = 0.97, cpu_embed: bool | None = None):
    from transformers import AutoModelForCausalLM, AutoTokenizer

    t0 = time.time()
    path = model_path(MODEL_ID, MODEL_REVISION)
    kw = {"revision": MODEL_REVISION} if path == MODEL_ID else {}
    tok = AutoTokenizer.from_pretrained(path, **kw)
    dev = torch.device("cuda", 0)
    free0, total = torch.cuda.mem_get_info(0)
    if cpu_embed is None:
        cpu_embed = free0 < 18 * 1024 ** 3
    model = AutoModelForCausalLM.from_pretrained(path, dtype=torch.bfloat16, attn_implementation="sdpa",
                                                 device_map={"": "cpu"}, low_cpu_mem_usage=True, **kw)
    assert not model.config.tie_word_embeddings
    for layer in model.model.layers:
        layer.to(dev)
    model.model.norm.to(dev)
    model.model.rotary_emb.to(dev)
    model.lm_head.to(dev)
    if cpu_embed:
        sys.path.append(str(I6_SRC))
        from engine6 import CPUEmbedding
        model.model.embed_tokens = CPUEmbedding(model.model.embed_tokens.weight.data.contiguous(), dev)
    else:
        model.model.embed_tokens.to(dev)
    gc.collect()
    torch.cuda.empty_cache()
    model.eval()
    model.requires_grad_(False)
    torch.cuda.set_per_process_memory_fraction(vram_fraction, 0)
    free, total = torch.cuda.mem_get_info(0)
    info = {"precision": "bf16", "cpu_embedding": bool(cpu_embed), "free_vram_before_GB": round(free0 / 1e9, 3),
            "free_vram_after_GB": round(free / 1e9, 3), "total_vram_GB": round(total / 1e9, 3),
            "gpu": torch.cuda.get_device_name(0), "load_seconds": round(time.time() - t0, 1)}
    logger.info(f"{MODEL_ID} bf16 loaded: {info}")
    return tok, model, info


def dev_of(model: Any) -> torch.device:
    return model.lm_head.weight.device


@torch.no_grad()
def prefill(model: Any, ids: list[int], edits: dict | None = None, capture: dict | None = None) -> dict[str, Any]:
    """Batch-1 prompt pass with optional block-output edits/captures -> {'kv', 'r_logits' fp32 [V], 'P'}."""
    from transformers.cache_utils import DynamicCache

    inp = torch.tensor([ids], device=dev_of(model))
    cache = DynamicCache()
    with block_hooks(model, edits, capture):
        out = model.model(input_ids=inp, past_key_values=cache, use_cache=True)
    r_logits = model.lm_head(out.last_hidden_state[:, -1]).float()[0]
    kv = [(K.clone(), V.clone()) for K, V in E4._kv_list(cache)]
    del cache, out
    return {"kv": kv, "r_logits": r_logits, "P": len(ids)}


@torch.no_grad()
def teacher_force(model: Any, ids: list[int], start: int, capture_blocks: list[int] | None = None,
                  capture_pos: list[int] | None = None, edits: dict | None = None) -> dict[str, Any]:
    """fp32 logits at positions start-1 .. len(ids)-1 (row j predicts ids[start + j]; the last row predicts the next
    token after ids). Optional capture of block outputs at absolute positions capture_pos (fp32 [n_pos, D])."""
    inp = torch.tensor([ids], device=dev_of(model))
    caps: dict[int, torch.Tensor] = {}
    capture = None
    if capture_blocks:
        pos_t = torch.tensor(capture_pos, device=dev_of(model))

        def mk(l: int) -> Callable:
            def g(h: torch.Tensor) -> None:
                caps[l] = h[0, pos_t].float().clone()
            return g
        capture = {l: mk(l) for l in capture_blocks}
    with block_hooks(model, edits, capture):
        out = model.model(input_ids=inp, use_cache=False)
    lg = model.lm_head(out.last_hidden_state[0, start - 1:]).float()
    del out
    return {"logits": lg, "caps": caps}


@torch.no_grad()
def batch_last_states(model: Any, ids_batch: list[list[int]], blocks: list[int]) -> dict[str, Any]:
    """Equal-length batch forward: block outputs at the LAST position of every row (fp32 [B, D]) + last logits."""
    inp = torch.tensor(ids_batch, device=dev_of(model))
    caps: dict[int, torch.Tensor] = {}

    def mk(l: int) -> Callable:
        def g(h: torch.Tensor) -> None:
            caps[l] = h[:, -1].float().clone()
        return g
    with block_hooks(model, None, {l: mk(l) for l in blocks}):
        out = model.model(input_ids=inp, use_cache=False)
    lg = model.lm_head(out.last_hidden_state[:, -1]).float()
    del out
    return {"caps": caps, "logits": lg}


def capture_hooks(store: dict[int, torch.Tensor], pos: torch.Tensor, blocks: list[int]) -> dict[int, Callable]:
    def mk(l: int) -> Callable:
        def g(h: torch.Tensor) -> None:
            store[l] = h[0, pos].float().clone()
        return g
    return {l: mk(l) for l in blocks}


def set_rows_edit(pos: torch.Tensor, src: dict[int, torch.Tensor]) -> dict[int, Callable]:
    """Exchange (iteration 6 gpu6.set_rows_edit): overwrite block-l outputs at positions pos with src[l]."""
    def mk(l: int) -> Callable:
        def f(h: torch.Tensor) -> torch.Tensor:
            h = h.clone()
            h[0, pos] = src[l].to(h.dtype)
            return h
        return f
    return {l: mk(l) for l in src}


def mr_edit(pos: torch.Tensor, h_clean: dict[int, torch.Tensor], norms: dict[int, torch.Tensor],
            seed: int) -> tuple[dict[int, Callable], dict[int, float]]:
    """Matched-norm random exchange (iteration 6 MR): h <- h_clean + ||h_src - h_clean|| * r with a fresh isotropic
    unit r per (block, position); realised norms are returned for the G5 check."""
    rng = np.random.Generator(np.random.PCG64(seed))
    src: dict[int, torch.Tensor] = {}
    real: dict[int, float] = {}
    for l, hc in h_clean.items():
        r = rng.standard_normal(hc.shape).astype(np.float32)
        r /= np.linalg.norm(r, axis=1, keepdims=True)
        rt = torch.from_numpy(r).to(hc.device)
        src[l] = hc + norms[l][:, None] * rt
        real[l] = float((src[l] - hc).norm(dim=1).mean())
    return set_rows_edit(pos, src), real


def push_edits(a: int, b: int, u: torch.Tensor, n: dict[int, torch.Tensor], h_ref: dict[int, torch.Tensor],
               alpha: float, log: dict | None = None) -> dict[int, Callable]:
    """Displacement-targeted random push (hooks.make_edits 'RAND'): h <- h + (alpha n[l,p] - delta.u) u at the task-spec
    positions [a, b) of blocks 12-23, prefill only."""
    return H4.make_edits("RAND", a, b, {l: u for l in H4.V_BLOCKS}, n, h_ref, alpha=alpha, log=log)


@torch.no_grad()
def decode_stop(model: Any, rows: list[dict[str, Any]], tok: Any, fence_kind: str | None = "bench",
                stop_fn: Callable[[int, list[int]], bool] | None = None, check_every: int = 8) -> list[dict[str, Any]]:
    """engine5.decode_rows (float64 CRN inverse-CDF sampler, left-padded KV for mixed prompt lengths, fence stop) with an
    extra host stop rule: every check_every steps stop_fn(row, generated_ids) may finish a live row ('decided')."""
    dev = dev_of(model)
    B = len(rows)
    max_new = [int(r["max_new"]) for r in rows]
    max_steps = max(max_new)
    cache, Pmax, pads = E5.assemble_cache(rows, max_steps)
    padded = any(p > 0 for p in pads)
    am_full = None
    if padded:
        am_full = torch.ones(B, Pmax + max_steps + 1, dtype=torch.long, device=dev)
        for i, p in enumerate(pads):
            if p:
                am_full[i, :p] = 0
    Pvec = torch.tensor([r["pre"]["P"] for r in rows], dtype=torch.long, device=dev)
    Ucode = torch.zeros(B, max_steps, dtype=torch.float64, device=dev)
    for i, r in enumerate(rows):
        u = np.asarray(r["u"], dtype=np.float64)[:max_new[i]]
        assert len(u) >= max_new[i]
        Ucode[i, :max_new[i]] = torch.from_numpy(u)
    T_code = torch.tensor([float(r["T"]) for r in rows], dtype=torch.float64, device=dev)
    top_k_t = torch.tensor([int(r.get("top_k") or 0) for r in rows], dtype=torch.long, device=dev)
    top_p_t = torch.ones(B, dtype=torch.float64, device=dev)
    any_topk = bool((top_k_t > 0).any())
    maxnew_t = torch.tensor(max_new, dtype=torch.long, device=dev)
    fence_rows = torch.tensor([bool(r.get("fence", True)) for r in rows], device=dev)
    i_code = torch.zeros(B, dtype=torch.long, device=dev)
    tick = E4.backtick_ids(tok).to(dev) if fence_kind else None
    logits = torch.stack([r["pre"]["r_logits"] for r in rows], 0).double()
    toks = torch.full((B, max_steps), -1, dtype=torch.long, device=dev)
    done = torch.zeros(B, dtype=torch.bool, device=dev)
    ended = torch.zeros(B, dtype=torch.bool, device=dev)
    fenced = torch.zeros(B, dtype=torch.bool, device=dev)
    decided = torch.zeros(B, dtype=torch.bool, device=dev)
    im_end_t = torch.full((B,), E5.IM_END, dtype=torch.long, device=dev)
    ar = torch.arange(B, device=dev)
    host_toks: list[list[int]] = [[] for _ in range(B)]
    last_sync = 0
    step = 0
    nv = E4.vocab_len(tok)
    while True:
        probs = step_probs5(logits, T_code[:, None], top_k_t, top_p_t, any_topk, False)
        u = Ucode[ar, i_code.clamp(max=max_steps - 1)]
        nxt = inverse_cdf(probs, u)
        live = ~done
        i_code += live.long()
        toks[:, step] = torch.where(live, nxt, toks[:, step])
        is_end = (nxt == E5.IM_END) | (nxt == E5.ENDOFTEXT)
        ended |= live & is_end
        done |= is_end | (live & (i_code >= maxnew_t))
        if step + 1 >= max_steps:
            break
        if (step + 1) % check_every == 0:
            chunk = toks[:, last_sync:step + 1].cpu().numpy()
            for r_ in range(B):
                host_toks[r_].extend(int(t) for t in chunk[r_] if t >= 0)
            last_sync = step + 1
            dn = done.cpu().numpy()
            newly_f, newly_d = [], []
            for r_ in range(B):
                if dn[r_]:
                    continue
                ids_r = [t for t in host_toks[r_] if t < nv]
                if fence_kind and bool(fence_rows[r_]) and tick is not None:
                    txt = rows[r_].get("text_prefix", "") + tok.decode(ids_r, skip_special_tokens=True)
                    if "`" in txt and fence_closed(txt, fence_kind):
                        newly_f.append(r_)
                        continue
                if stop_fn is not None and stop_fn(r_, ids_r):
                    newly_d.append(r_)
            if newly_f:
                idx = torch.tensor(newly_f, device=dev)
                fenced[idx] = True
                done[idx] = True
            if newly_d:
                idx = torch.tensor(newly_d, device=dev)
                decided[idx] = True
                done[idx] = True
            if bool(done.all().item()):
                break
        feed = torch.where(done, im_end_t, nxt)[:, None]
        pos = (Pvec + step)[:, None]
        if padded:
            h = model.model(input_ids=feed, past_key_values=cache, position_ids=pos,
                            attention_mask=am_full[:, :Pmax + step + 1], use_cache=True).last_hidden_state
        else:
            h = model.model(input_ids=feed, past_key_values=cache, position_ids=pos, use_cache=True).last_hidden_state
        logits = model.lm_head(h[:, -1]).double()
        step += 1
    del cache
    toks_c = toks.cpu().numpy()
    ended_c, fenced_c, dec_c = ended.cpu().numpy(), fenced.cpu().numpy(), decided.cpu().numpy()
    out = []
    for r_ in range(B):
        row = toks_c[r_]
        n = int((row >= 0).sum())
        fr = "stop" if ended_c[r_] else ("fence" if fenced_c[r_] else ("decided" if dec_c[r_] else "length"))
        out.append({"token_ids": [int(t) for t in row[:n]], "finish_reason": fr, "n_tokens": n, "steps": step + 1,
                    "engine_path": "leftpad" if padded else "shared"})
    return out
