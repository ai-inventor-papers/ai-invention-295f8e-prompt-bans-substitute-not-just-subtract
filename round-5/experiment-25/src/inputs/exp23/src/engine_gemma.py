#!/usr/bin/env python3
"""STEP 5: HF engine for gemma-3-4b-it (bf16, sdpa), text-only.

Load: the language-model weights of the multimodal checkpoint (keys 'language_model.model.*') are loaded into a
Gemma3ForCausalLM built from config.text_config (vision tower and projector are not loaded; for text-only inputs the
two models compute the same function). lm_head is tied to embed_tokens; final-logit softcapping is applied if set.

CRN sampler (port of iteration-3 exp17 engine.py / iteration-2 exp8 engine.py): every row carries its own temperature
T_b, push spec (unit u_b, dose alpha_b) and uniform stream U[b] = PCG64(stable_seed(slot key)).random(max_new);
per step: logits fp32 / T_b -> softmax -> cumsum in float64 in token-id order -> token = searchsorted(cdf, U[b,t]).
Finished rows stay in the batch (fed <end_of_turn>) so the batch shape is fixed at every step: a slot's computation
is independent of its batch-mates for a fixed shape, which makes the twin/push/ban coupling exact.
Stops: <eos> (1), <end_of_turn> (106), or the row's text has closed its first fenced code block containing 'def '
(checked every 16 steps; finish_reason 'fence'), or the cap ('length').

Single-prompt batches (all CRN arms): one batched prefill of the prompt repeated B times, with displacement-targeted
push edits on rows with alpha_b > 0 (src/push.py). Multi-prompt batches (pilot, novelty, 'can', association):
each distinct prompt is prefilled at batch 1 and its KV right-aligned into the decode buffer with zero-filled left
pads masked out by a 2-D attention mask; position ids are each row's own logical positions.
"""

from __future__ import annotations

import gc
import re
import time
from typing import Any

import numpy as np
import torch
from loguru import logger

from cfg import (CAPTURE_BLOCKS, D_MODEL, EOS_ID, EOT_ID, MODEL_ID, MODEL_REVISION, N_LAYERS, STOP_CHECK_EVERY,
                 model_path, stable_seed)
from push import block_hooks, make_push_edits

FENCE_RE = re.compile(r"```[^\n`]*\n(.*?)\n[ \t]*```", re.S)


# ------------------------------------------------------------------------------------------------ loading
def load_model(vram_fraction: float = 0.97) -> tuple[Any, Any, dict[str, Any]]:
    from safetensors import safe_open
    from transformers import AutoConfig, AutoTokenizer, Gemma3ForCausalLM

    t0 = time.time()
    path = model_path(MODEL_ID, MODEL_REVISION)
    tok = AutoTokenizer.from_pretrained(path)
    cfg = AutoConfig.from_pretrained(path)
    tcfg = cfg.text_config
    tcfg._attn_implementation = "sdpa"
    torch.cuda.set_per_process_memory_fraction(vram_fraction, 0)
    old = torch.get_default_dtype()
    torch.set_default_dtype(torch.bfloat16)
    try:
        with torch.device("cuda"):
            model = Gemma3ForCausalLM(tcfg)
    finally:
        torch.set_default_dtype(old)
    model.eval()
    model.requires_grad_(False)
    sd = model.state_dict()
    loaded = set()
    import json
    from pathlib import Path

    idx = json.loads((Path(path) / "model.safetensors.index.json").read_text())
    files = sorted(set(idx["weight_map"].values()))
    file_sha = {}
    for fn in files:
        with safe_open(str(Path(path) / fn), framework="pt", device="cuda") as fh:
            for k in fh.keys():
                if not k.startswith("language_model.model."):
                    continue
                nk = "model." + k[len("language_model.model."):]
                assert nk in sd, f"unexpected key {k}"
                t = fh.get_tensor(k)
                assert sd[nk].shape == t.shape, (nk, sd[nk].shape, t.shape)
                sd[nk].copy_(t.to(sd[nk].dtype))
                loaded.add(nk)
                del t
    model.tie_weights()
    missing = sorted(set(k for k in sd if not k.startswith("lm_head")) - loaded)
    assert not missing, f"weights not loaded: {missing[:5]}"
    assert model.lm_head.weight.data_ptr() == model.model.embed_tokens.weight.data_ptr(), "lm_head not tied"
    gc.collect()
    torch.cuda.empty_cache()
    free, total = torch.cuda.mem_get_info(0)
    info = {"path_revision": MODEL_REVISION, "n_tensors_loaded": len(loaded), "load_seconds": time.time() - t0,
            "vram_free_gb_after_load": free / 1e9, "vram_total_gb": total / 1e9,
            "n_layers": len(model.model.layers), "d_model": tcfg.hidden_size,
            "layer_types": list(tcfg.layer_types), "sliding_window": tcfg.sliding_window,
            "final_logit_softcapping": tcfg.final_logit_softcapping,
            "attn_logit_softcapping": getattr(tcfg, "attn_logit_softcapping", None), "files": files}
    assert len(model.model.layers) == N_LAYERS and tcfg.hidden_size == D_MODEL
    logger.info(f"{MODEL_ID} loaded in {info['load_seconds']:.0f}s; free VRAM {free / 1e9:.2f}/{total / 1e9:.2f} GB")
    return tok, model, info


def layers(model: Any) -> Any:
    return model.model.layers


def lm_logits(model: Any, h: torch.Tensor) -> torch.Tensor:
    x = model.lm_head(h).float()
    cap = model.config.final_logit_softcapping
    if cap is not None:
        x = torch.tanh(x / cap) * cap
    return x


# ------------------------------------------------------------------------------------------------ caches
class PreallocLayer:
    """KV layer with a preallocated [B, H, Lmax, D] buffer (exp17): update() writes in place."""

    is_sliding = False
    is_compileable = False

    def __init__(self, K: torch.Tensor, V: torch.Tensor, max_len: int, L0: int | None = None):
        B, H, L, D = K.shape
        self.kbuf = torch.zeros(B, H, max_len, D, dtype=K.dtype, device=K.device)
        self.vbuf = torch.zeros_like(self.kbuf)
        off = 0 if L0 is None else L0 - L
        self.kbuf[:, :, off:off + L] = K
        self.vbuf[:, :, off:off + L] = V
        self.n = L if L0 is None else L0
        self.dtype, self.device = K.dtype, K.device
        self.is_initialized = True
        self.keys, self.values = self.kbuf[:, :, :self.n], self.vbuf[:, :, :self.n]

    def lazy_initialization(self, key_states: torch.Tensor) -> None:
        return None

    def update(self, key_states, value_states, cache_kwargs=None):
        q = key_states.shape[-2]
        self.kbuf[:, :, self.n:self.n + q] = key_states
        self.vbuf[:, :, self.n:self.n + q] = value_states
        self.n += q
        self.keys, self.values = self.kbuf[:, :, :self.n], self.vbuf[:, :, :self.n]
        return self.keys, self.values

    def get_mask_sizes(self, cache_position: torch.Tensor) -> tuple[int, int]:
        return self.n + cache_position.shape[0], 0

    def get_seq_length(self) -> int:
        return self.n

    def get_max_cache_shape(self) -> int:
        return -1


def _kv_from_cache(cache: Any) -> list[tuple[torch.Tensor, torch.Tensor]]:
    if hasattr(cache, "layers"):
        return [(L.keys, L.values) for L in cache.layers]
    return list(zip(cache.key_cache, cache.value_cache))


def build_prealloc(kv: list, max_len: int) -> Any:
    """kv: list of (K, V) [B, H, L, D] (consumed: entries are dropped as they are copied to save VRAM)."""
    from transformers.cache_utils import Cache

    lays = []
    for l in range(len(kv)):
        K, V = kv[l]
        lays.append(PreallocLayer(K, V, max_len))
        kv[l] = None
        del K, V
    return Cache(layers=lays)


# ------------------------------------------------------------------------------------------------ prefill
@torch.no_grad()
def prefill_single(model: Any, ids: list[int], B: int, push: dict[str, Any] | None = None,
                   capture_ref: dict[str, Any] | None = None) -> dict[str, Any]:
    """One prompt repeated B times. push = {'U': [B, D] fp32, 'alpha': [B] fp32, 'n': {l: [S]}, 'h_ref': {l: [S, D]},
    'a': int, 'b': int, 'band': [...]}. capture_ref = {'S': {l: [S, D]}, 'R': {l: [D]}, 'a', 'b'} -> per-row
    realised displacement from the clean twin at CAPTURE_BLOCKS (mean over spec positions and at R)."""
    from transformers.cache_utils import DynamicCache

    P = len(ids)
    inp = torch.tensor([ids], device="cuda").expand(B, -1).contiguous()
    edits = {}
    if push is not None:
        edits = make_push_edits(push["band"], push["a"], push["b"], push["U"], push["alpha"], push["n"],
                                push["h_ref"])
    disp: dict[str, dict[int, torch.Tensor]] = {"S": {}, "R": {}, "along": {}}
    cap = {}
    if capture_ref is not None:
        a, b = capture_ref["a"], capture_ref["b"]

        def mk(l):
            def g(h):
                hs = h[:, a:b].float()
                disp["S"][l] = (hs - capture_ref["S"][l][None]).norm(dim=-1).mean(-1)
                disp["R"][l] = (h[:, P - 1].float() - capture_ref["R"][l][None]).norm(dim=-1)
                if push is not None and l in push["n"]:
                    comp = ((hs - capture_ref["S"][l][None]) * push["U"][:, None, :]).sum(-1)  # [B, S]
                    tgt = push["alpha"][:, None] * push["n"][l][None, :]
                    disp["along"][l] = ((comp - tgt).abs() / tgt.abs().clamp(min=1e-6)).mean(-1)
            return g
        cap = {l: mk(l) for l in CAPTURE_BLOCKS}
    cache = DynamicCache()
    with block_hooks(layers(model), edits, cap):
        out = model.model(input_ids=inp, past_key_values=cache, use_cache=True)
    logits = lm_logits(model, out.last_hidden_state[:, -1])
    kv = [(K, V) for K, V in _kv_from_cache(cache)]
    del out, cache
    res = {"kv": kv, "logits": logits, "P": P, "mask": None, "lens": None}
    if capture_ref is not None:
        res["disp_S"] = torch.stack([disp["S"][l] for l in CAPTURE_BLOCKS], 1).cpu().numpy()  # [B, nblocks]
        res["disp_R"] = torch.stack([disp["R"][l] for l in CAPTURE_BLOCKS], 1).cpu().numpy()
        if disp["along"]:
            ks = sorted(disp["along"])
            res["relerr_along"] = torch.stack([disp["along"][l] for l in ks], 1).cpu().numpy()
    return res


@torch.no_grad()
def clean_states(model: Any, ids: list[int], a: int, b: int, blocks: list[int]) -> dict[str, Any]:
    """Batch-1 clean prefill; block outputs at spec positions [a, b) and at R for `blocks` (fp32, on GPU)."""
    S, R = {}, {}

    def mk(l):
        def g(h):
            S[l] = h[0, a:b].float().clone()
            R[l] = h[0, len(ids) - 1].float().clone()
        return g
    inp = torch.tensor([ids], device="cuda")
    with block_hooks(layers(model), None, {l: mk(l) for l in blocks}):
        out = model.model(input_ids=inp, use_cache=False)
    logits = lm_logits(model, out.last_hidden_state[:, -1])[0]
    del out
    return {"S": S, "R": R, "a": a, "b": b, "logits": logits}


@torch.no_grad()
def prefill_multi(model: Any, id_lists: list[list[int]]) -> dict[str, Any]:
    """Distinct prompts: batch-1 prefill each (deduplicated), right-align KV into one [B, H, Pmax, D] block."""
    from transformers.cache_utils import DynamicCache

    B = len(id_lists)
    Pmax = max(len(x) for x in id_lists)
    uniq: dict[tuple, int] = {}
    for x in id_lists:
        uniq.setdefault(tuple(x), len(uniq))
    per: list[Any] = [None] * len(uniq)
    logits_u = []
    for key, j in uniq.items():
        cache = DynamicCache()
        out = model.model(input_ids=torch.tensor([list(key)], device="cuda"), past_key_values=cache, use_cache=True)
        logits_u.append(lm_logits(model, out.last_hidden_state[:, -1])[0])
        per[j] = _kv_from_cache(cache)
        del out, cache
    n_l = len(per[0])
    H, D = per[0][0][0].shape[1], per[0][0][0].shape[3]
    dt = per[0][0][0].dtype
    kv = []
    rowj = [uniq[tuple(x)] for x in id_lists]
    for l in range(n_l):
        K = torch.zeros(B, H, Pmax, D, dtype=dt, device="cuda")
        V = torch.zeros_like(K)
        for r, x in enumerate(id_lists):
            Kr, Vr = per[rowj[r]][l]
            L = len(x)
            K[r, :, Pmax - L:] = Kr[0]
            V[r, :, Pmax - L:] = Vr[0]
        kv.append((K, V))
    del per
    lens = torch.tensor([len(x) for x in id_lists], device="cuda")
    mask = torch.zeros(B, Pmax, dtype=torch.long, device="cuda")
    for r, x in enumerate(id_lists):
        mask[r, Pmax - len(x):] = 1
    logits = torch.stack([logits_u[j] for j in rowj], 0)
    return {"kv": kv, "logits": logits, "P": Pmax, "mask": mask, "lens": lens}


# ------------------------------------------------------------------------------------------------ sampling
def u_stream(*key: Any, n: int) -> np.ndarray:
    return np.random.Generator(np.random.PCG64(stable_seed(*key))).random(n)


def unit_dir(*key: Any) -> np.ndarray:
    x = np.random.Generator(np.random.PCG64(stable_seed(*key))).standard_normal(D_MODEL)
    return (x / np.linalg.norm(x)).astype(np.float32)


def seed_dir(seed: int) -> np.ndarray:
    """exp17 _RandDirs construction: PCG64(seed) standard normal of d_model, normalised."""
    x = np.random.Generator(np.random.PCG64(seed)).standard_normal(D_MODEL)
    return (x / np.linalg.norm(x)).astype(np.float32)


def fence_closed(text: str) -> bool:
    for m in FENCE_RE.finditer(text):
        if "def " in m.group(1):
            return True
    return False


@torch.no_grad()
def decode(model: Any, tok: Any, pre: dict[str, Any], U: np.ndarray, temps: np.ndarray, max_new: int,
           fence_stop: bool = True) -> list[dict[str, Any]]:
    """pre: prefill dict (kv consumed). U: [B, >= max_new] uniforms; temps: [B]."""
    B = U.shape[0]
    P = pre["P"]
    dev = torch.device("cuda")
    cache = build_prealloc(pre["kv"], P + max_new + 1)
    pre["kv"] = None
    Ut = torch.tensor(U[:, :max_new], dtype=torch.float64, device=dev)
    Tt = torch.tensor(temps, dtype=torch.float32, device=dev)[:, None]
    logits = pre["logits"]
    V = logits.shape[-1]
    toks = torch.full((B, max_new), -1, dtype=torch.long, device=dev)
    done = torch.zeros(B, dtype=torch.bool, device=dev)
    ended = torch.zeros(B, dtype=torch.bool, device=dev)
    fenced = torch.zeros(B, dtype=torch.bool, device=dev)
    eot_t = torch.full((B,), EOT_ID, dtype=torch.long, device=dev)
    mask_full = None
    if pre["mask"] is not None:
        mask_full = torch.ones(B, P + max_new + 1, dtype=torch.long, device=dev)
        mask_full[:, :P] = pre["mask"]
        lens = pre["lens"]
    cpu_ids: list[list[int]] = [[] for _ in range(B)]
    done_cpu = np.zeros(B, dtype=bool)
    synced = 0
    step = 0
    t0 = time.time()
    while True:
        probs = torch.softmax(logits / Tt, dim=-1)
        cdf = probs.double().cumsum(dim=-1)
        cdf = cdf / cdf[:, -1:]
        nxt = torch.searchsorted(cdf, Ut[:, step:step + 1]).squeeze(-1).clamp_(max=V - 1)
        live = ~done
        toks[:, step] = torch.where(live, nxt, toks[:, step])
        is_end = (nxt == EOT_ID) | (nxt == EOS_ID)
        ended |= live & is_end
        done |= is_end
        if step + 1 >= max_new:
            break
        if (step + 1) % STOP_CHECK_EVERY == 0:
            chunk = toks[:, synced:step + 1].cpu().numpy()
            dnow = done.cpu().numpy()
            synced = step + 1
            newly = []
            for r in range(B):
                if done_cpu[r]:
                    continue
                cpu_ids[r].extend(int(t) for t in chunk[r] if t >= 0)
                if dnow[r]:
                    done_cpu[r] = True
                    continue
                if fence_stop and "```" in tok.decode(cpu_ids[r][-24:]) and fence_closed(tok.decode(cpu_ids[r])):
                    newly.append(r)
                    done_cpu[r] = True
            if newly:
                idx = torch.tensor(newly, device=dev)
                done[idx] = True
                fenced[idx] = True
            if done_cpu.all():
                break
        feed = torch.where(done, eot_t, nxt)[:, None]
        if mask_full is None:
            pos = torch.full((B, 1), P + step, device=dev, dtype=torch.long)
            h = model.model(input_ids=feed, past_key_values=cache, position_ids=pos, use_cache=True).last_hidden_state
        else:
            pos = (lens + step)[:, None]
            h = model.model(input_ids=feed, past_key_values=cache, position_ids=pos,
                            attention_mask=mask_full[:, :P + step + 1], use_cache=True).last_hidden_state
        logits = lm_logits(model, h[:, -1])
        step += 1
    dt = time.time() - t0
    del cache
    toks_c = toks.cpu().numpy()
    ended_c = ended.cpu().numpy()
    fenced_c = fenced.cpu().numpy()
    out = []
    for r in range(B):
        row = toks_c[r]
        n = int((row >= 0).sum())
        ids = [int(t) for t in row[:n]]
        fr = "stop" if ended_c[r] else ("fence" if fenced_c[r] else "length")
        out.append({"token_ids": ids, "finish_reason": fr, "n_tokens": n, "steps": step + 1,
                    "text": tok.decode(ids, skip_special_tokens=True)})
    logger.debug(f"decode B={B} P={P} steps={step + 1} in {dt:.1f}s ({1000 * dt / max(step + 1, 1):.1f} ms/step)")
    return out


# ------------------------------------------------------------------------------------------------ teacher forcing
@torch.no_grad()
def tf_logprobs(model: Any, ids: list[int], targets: list[int]) -> list[float]:
    """Log-probs of ids[t] given ids[:t] for t in targets (batch-1 forward, lm_head only at the needed positions)."""
    inp = torch.tensor([ids], device="cuda")
    out = model.model(input_ids=inp, use_cache=False)
    pos = torch.tensor([t - 1 for t in targets], device="cuda")
    lg = lm_logits(model, out.last_hidden_state[0, pos])
    lp = torch.log_softmax(lg, dim=-1)
    tg = torch.tensor([ids[t] for t in targets], device="cuda")
    res = lp.gather(-1, tg[:, None])[:, 0].cpu().tolist()
    del out
    return res


@torch.no_grad()
def spec_states(model: Any, ids: list[int], a: int, b: int, blocks: list[int]) -> dict[int, torch.Tensor]:
    st = clean_states(model, ids, a, b, blocks)
    return st["S"]
