#!/usr/bin/env python3
"""HF engine for Qwen3-8B on a 16 GB GPU: FP8 (E4M3) W8A8-dynamic linear layers, prompt prefill with block-output
edit hooks, the exp8 common-random-numbers inverse-CDF sampler (prune=False, constant batch shape) and teacher-forced
state capture.

FP8 (deviation F2, logged): bf16 Qwen3-8B needs 16.4 GB of weights and the GPU has 16 GB. Every decoder Linear is
quantised at load time from the pinned bf16 snapshot to float8_e4m3fn with one scale per output channel; activations
are quantised per token (row) at run time and multiplied with torch._scaled_mm (cuBLASLt, sm_89). Embeddings,
RMSNorms and lm_head stay bf16, so logits come from a bf16 projection. Per-token scaling keeps every row's numerics
independent of its batch-mates (for a fixed batch shape), which is what the CRN coupling needs.
"""

from __future__ import annotations

import contextlib
import gc
import time
from typing import Any, Callable, Iterator

import numpy as np
import torch
from loguru import logger

from cfg import ENDOFTEXT, IM_END, MAX_NEW_TOKENS, MODEL_ID, MODEL_REVISION, model_path, stable_seed

FP8_MAX = 448.0
_ACT_CACHE: dict[str, Any] = {"x": None, "xq": None, "xs": None}


class FP8Linear(torch.nn.Module):
    """y = x W^T with W in float8_e4m3fn (per-output-channel scale) and x quantised per row at run time."""

    def __init__(self, lin: torch.nn.Linear, device: torch.device):
        super().__init__()
        W = lin.weight.data.to(device=device, dtype=torch.float32)
        s = W.abs().amax(dim=1, keepdim=True).clamp(min=1e-12) / FP8_MAX  # [N, 1]
        wq = (W / s).clamp_(-FP8_MAX, FP8_MAX).to(torch.float8_e4m3fn)  # [N, K] row-major
        self.register_buffer("wq_t", wq.t(), persistent=False)  # [K, N] column-major view (what _scaled_mm wants)
        self.register_buffer("w_scale", s.t().contiguous(), persistent=False)  # [1, N] fp32
        self.in_features = lin.in_features
        self.out_features = lin.out_features
        if lin.bias is not None:
            self.register_buffer("bias", lin.bias.data.to(device=device, dtype=torch.bfloat16), persistent=False)
        else:
            self.bias = None
        del W, wq

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        shp = x.shape
        if _ACT_CACHE["x"] is x:  # q/k/v and gate/up share one input tensor: quantise it once
            xq, xs = _ACT_CACHE["xq"], _ACT_CACHE["xs"]
        else:
            x2 = x.reshape(-1, shp[-1])
            xs = x2.abs().amax(dim=1, keepdim=True).float().clamp_(min=1e-12) / FP8_MAX
            xq = (x2.float() / xs).clamp_(-FP8_MAX, FP8_MAX).to(torch.float8_e4m3fn)
            _ACT_CACHE.update(x=x, xq=xq, xs=xs)
        out = torch._scaled_mm(xq, self.wq_t, scale_a=xs, scale_b=self.w_scale, out_dtype=torch.bfloat16)
        if self.bias is not None:
            out = out + self.bias
        return out.reshape(*shp[:-1], self.out_features)


def clear_act_cache() -> None:
    _ACT_CACHE.update(x=None, xq=None, xs=None)


def quantise_model_fp8(model: Any, device: torch.device) -> dict[str, Any]:
    """Replace every nn.Linear inside the decoder blocks by FP8Linear (layer by layer, freeing bf16 copies)."""
    n_lin = 0
    for li, layer in enumerate(model.model.layers):
        for name, mod in list(layer.named_modules()):
            for cname, child in list(mod.named_children()):
                if isinstance(child, torch.nn.Linear):
                    setattr(mod, cname, FP8Linear(child, device))
                    n_lin += 1
        layer.to(device)
        gc.collect()
    model.model.embed_tokens.to(device)
    model.model.norm.to(device)
    model.model.rotary_emb.to(device)
    model.lm_head.to(device)
    gc.collect()
    torch.cuda.empty_cache()
    return {"n_fp8_linears": n_lin}


def load_model(model_id: str = MODEL_ID, revision: str | None = MODEL_REVISION, vram_fraction: float = 0.97,
               fp8: bool = True):
    from transformers import AutoModelForCausalLM, AutoTokenizer

    t0 = time.time()
    path = model_path(model_id, revision)
    kw = {"revision": revision} if path == model_id and revision else {}
    tok = AutoTokenizer.from_pretrained(path, **kw)
    dev = torch.device("cuda", 0)
    if fp8:
        model = AutoModelForCausalLM.from_pretrained(path, dtype=torch.bfloat16, attn_implementation="sdpa",
                                                     device_map={"": "cpu"}, low_cpu_mem_usage=True, **kw)
        logger.info(f"bf16 weights on CPU in {time.time() - t0:.0f}s; quantising decoder linears to FP8")
        info = quantise_model_fp8(model, dev)
    else:
        model = AutoModelForCausalLM.from_pretrained(path, dtype=torch.bfloat16, attn_implementation="sdpa",
                                                     device_map={"": 0}, **kw)
        info = {"n_fp8_linears": 0}
    model.eval()
    model.requires_grad_(False)
    torch.cuda.set_per_process_memory_fraction(vram_fraction, 0)
    free, total = torch.cuda.mem_get_info(0)
    logger.info(f"{model_id} loaded in {time.time() - t0:.0f}s ({info}); free VRAM {free / 1e9:.1f}/"
                f"{total / 1e9:.1f} GB")
    return tok, model


def layers(model: Any) -> Any:
    return model.model.layers


# ------------------------------------------------------------------------------------------------ hooks
def _out_tensor(out: Any) -> torch.Tensor:
    return out[0] if isinstance(out, tuple) else out


def _replace_out(out: Any, h: torch.Tensor) -> Any:
    if isinstance(out, tuple):
        return (h,) + tuple(out[1:])
    return h


@contextlib.contextmanager
def block_hooks(model: Any, edits: dict[int, Callable[[torch.Tensor], torch.Tensor]] | None = None,
                capture: dict[int, Callable[[torch.Tensor], None]] | None = None) -> Iterator[None]:
    """edits: {block: f(h) -> h'} applied to the block OUTPUT (in place on a clone); capture: {block: g(h)} called
    after the edit. Hooks are removed on exit."""
    hs = []
    edits = edits or {}
    capture = capture or {}
    for l in sorted(set(edits) | set(capture)):
        def hook(mod, inp, out, l=l):
            h = _out_tensor(out)
            if l in edits:
                h = edits[l](h)
                out = _replace_out(out, h)
            if l in capture:
                capture[l](h)
            return out
        hs.append(layers(model)[l].register_forward_hook(hook))
    try:
        yield
    finally:
        for h in hs:
            h.remove()


@contextlib.contextmanager
def head_ablation(model: Any, masks: dict[int, torch.Tensor], mus: dict[int, torch.Tensor]) -> Iterator[None]:
    """Mean-ablate attention heads at DECODE steps only (q_len == 1): masks[l] is a bool [B, 4096] selecting the
    o_proj-input columns of the ablated heads per row; mus[l] is the [4096] mean input. Prefill is untouched."""
    hs = []
    for l in masks:
        def pre(mod, args, l=l):
            x = args[0]
            if x.shape[1] != 1:
                return None
            m = masks[l]
            x2 = torch.where(m[:, None, :], mus[l].to(x.dtype)[None, None, :], x)
            return (x2,) + tuple(args[1:])
        hs.append(layers(model)[l].self_attn.o_proj.register_forward_pre_hook(pre))
    try:
        yield
    finally:
        for h in hs:
            h.remove()


# ------------------------------------------------------------------------------------------------ caches
def _kv_list(cache: Any) -> list[tuple[torch.Tensor, torch.Tensor]]:
    if hasattr(cache, "layers"):
        return [(L.keys, L.values) for L in cache.layers]
    return list(zip(cache.key_cache, cache.value_cache))


def build_cache(kv: list[tuple[torch.Tensor, torch.Tensor]]):
    from transformers.cache_utils import DynamicCache

    cache = DynamicCache()
    for l, (K, V) in enumerate(kv):
        cache.update(K.contiguous(), V.contiguous(), l)
    return cache


@torch.no_grad()
def prefill(model: Any, ids: list[int], edits: dict | None = None, capture: dict | None = None) -> dict[str, Any]:
    """Batch-1 prompt pass with optional block-output edits. Returns {'kv', 'r_logits' (fp32 [V]), 'P'}."""
    from transformers.cache_utils import DynamicCache

    inp = torch.tensor([ids], device=model.device)
    cache = DynamicCache()
    clear_act_cache()
    with block_hooks(model, edits, capture):
        out = model.model(input_ids=inp, past_key_values=cache, use_cache=True)
    r_logits = model.lm_head(out.last_hidden_state[:, -1]).float()[0]
    kv = [(K.clone(), V.clone()) for K, V in _kv_list(cache)]
    del cache, out
    clear_act_cache()
    return {"kv": kv, "r_logits": r_logits, "P": len(ids)}


# ------------------------------------------------------------------------------------------------ sampling
def u_stream(*key: Any, n: int = MAX_NEW_TOKENS) -> np.ndarray:
    return np.random.Generator(np.random.PCG64(stable_seed(*key))).random(n)


def _inverse_cdf(probs: torch.Tensor, u: torch.Tensor) -> torch.Tensor:
    cdf = probs.cumsum(dim=-1)
    cdf = cdf / cdf[:, -1:]
    tok = torch.searchsorted(cdf, u[:, None].to(cdf.dtype)).squeeze(-1)
    return tok.clamp_(max=probs.shape[-1] - 1)


class PreallocLayer:
    """KV layer with a preallocated [B, H, Lmax, D] buffer: update() writes in place and returns views of the valid
    prefix (the stock DynamicLayer re-concatenates the whole cache at every decode step)."""

    is_sliding = False
    is_compileable = False

    def __init__(self, K: torch.Tensor, V: torch.Tensor, max_len: int):
        B, H, L, D = K.shape
        self.kbuf = torch.empty(B, H, max_len, D, dtype=K.dtype, device=K.device)
        self.vbuf = torch.empty_like(self.kbuf)
        self.kbuf[:, :, :L] = K
        self.vbuf[:, :, :L] = V
        self.n = L
        self.dtype, self.device = K.dtype, K.device
        self.is_initialized = True
        self.keys, self.values = self.kbuf[:, :, :L], self.vbuf[:, :, :L]

    def lazy_initialization(self, key_states: torch.Tensor) -> None:  # already initialised
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


def prealloc_cache(kv: list[tuple[torch.Tensor, torch.Tensor]], max_len: int):
    from transformers.cache_utils import Cache

    return Cache(layers=[PreallocLayer(K, V, max_len) for K, V in kv])


@torch.no_grad()
def sample(model: Any, groups: list[dict[str, Any]], max_new: int = MAX_NEW_TOKENS, temperature: float = 1.0,
           heads: dict[str, Any] | None = None, record_block: int | None = None, record_steps: int = 0,
           check_every: int = 8) -> list[dict[str, Any]]:
    """groups: [{'pre': prefill dict, 'us': [np.ndarray[max_new], ...]}] -- each group's prefill is shared by its rows.
    One uniform per (row, step); token = first index whose CDF (vocabulary order, float64) >= u (exp8 sampler).
    prune=False: finished rows stay in the batch (fed <|im_end|>), so the batch shape is identical at every step in
    every arm. Stop tracking runs on the GPU (host sync every `check_every` steps only).
    heads: {'masks': {l: bool[B, 4096]}, 'mus': {l: [4096]}} mean-ablates heads at decode steps."""
    P = groups[0]["pre"]["P"]
    assert all(g["pre"]["P"] == P for g in groups), "all rows of a batch must share the prompt length"
    dev = model.device
    n_layers = len(groups[0]["pre"]["kv"])
    kv = []
    for l in range(n_layers):
        Ks, Vs = [], []
        for g in groups:
            K, V = g["pre"]["kv"][l]
            Ks.append(K.expand(len(g["us"]), -1, -1, -1))
            Vs.append(V.expand(len(g["us"]), -1, -1, -1))
        kv.append((torch.cat(Ks, 0), torch.cat(Vs, 0)))
    cache = prealloc_cache(kv, P + max_new + 1)
    del kv
    us = [u for g in groups for u in g["us"]]
    B = len(us)
    U = torch.tensor(np.stack([u[:max_new] for u in us]), dtype=torch.float64, device=dev)
    logits = torch.cat([g["pre"]["r_logits"][None].expand(len(g["us"]), -1) for g in groups], 0).double()
    toks = torch.full((B, max_new), -1, dtype=torch.long, device=dev)
    lps = torch.zeros((B, max_new), dtype=torch.float64, device=dev)
    done = torch.zeros(B, dtype=torch.bool, device=dev)
    ended = torch.zeros(B, dtype=torch.bool, device=dev)  # finished by <|im_end|> / <|endoftext|>
    im_end_t = torch.full((B,), IM_END, dtype=torch.long, device=dev)
    rec: list[np.ndarray] = []
    rec_hook = None
    if record_block is not None and record_steps > 0:
        def _rec(mod, inp, out):
            h = _out_tensor(out)
            if h.shape[1] == 1 and len(rec) < record_steps:
                rec.append(h[:, 0].float().cpu().numpy())
            return None
        rec_hook = layers(model)[record_block].register_forward_hook(_rec)
    ctx = head_ablation(model, heads["masks"], heads["mus"]) if heads else contextlib.nullcontext()
    step = 0
    try:
        with ctx:
            while True:
                probs = torch.softmax(logits / temperature, dim=-1)
                nxt = _inverse_cdf(probs, U[:, step])
                plp = torch.log(probs.gather(-1, nxt[:, None])[:, 0])
                live = ~done
                toks[:, step] = torch.where(live, nxt, toks[:, step])
                lps[:, step] = torch.where(live, plp, lps[:, step])
                is_end = (nxt == IM_END) | (nxt == ENDOFTEXT)
                ended |= live & is_end
                done |= is_end
                if step + 1 >= max_new:
                    break
                if (step + 1) % check_every == 0 and bool(done.all().item()):
                    break
                feed = torch.where(done, im_end_t, nxt)[:, None]
                pos = torch.full((B, 1), P + step, device=dev, dtype=torch.long)
                clear_act_cache()
                h = model.model(input_ids=feed, past_key_values=cache, position_ids=pos,
                                use_cache=True).last_hidden_state
                logits = model.lm_head(h[:, -1]).double()
                step += 1
    finally:
        if rec_hook is not None:
            rec_hook.remove()
        clear_act_cache()
    del cache
    toks_c = toks.cpu().numpy()
    lps_c = lps.cpu().numpy()
    ended_c = ended.cpu().numpy()
    out = []
    for r in range(B):
        row = toks_c[r]
        n = int((row >= 0).sum())
        ids = [int(t) for t in row[:n]]
        d = {"token_ids": ids, "finish_reason": "stop" if ended_c[r] else "length", "n_tokens": n,
             "logprob_sum": float(lps_c[r, :n].sum()), "steps": step + 1}
        if rec_hook is not None:
            d["rec"] = np.stack([x[r] for x in rec]) if rec else None
        out.append(d)
    return out


# ------------------------------------------------------------------------------------------------ teacher forcing
@torch.no_grad()
def forward_capture(model: Any, ids_batch: list[list[int]], blocks: list[int], positions: list[int],
                    s_range: tuple[int, int] | None = None, want_embed: list[int] | None = None,
                    want_logits: list[int] | None = None, topk: int = 20,
                    edits: dict | None = None) -> dict[str, Any]:
    """Equal-length batch forward. Returns block outputs at `positions` ({l: fp32 [B, len(pos), D]}), the mean over
    s_range ({l: [B, D]}), layer-0 embeddings at want_embed and top-k log-probs at want_logits."""
    B = len(ids_batch)
    T = len(ids_batch[0])
    assert all(len(x) == T for x in ids_batch)
    inp = torch.tensor(ids_batch, device=model.device)
    pos_t = torch.tensor(positions, device=model.device)
    got: dict[int, torch.Tensor] = {}
    got_s: dict[int, torch.Tensor] = {}

    def cap(l):
        def f(h):
            got[l] = h[:, pos_t].float().cpu()
            if s_range is not None:
                got_s[l] = h[:, s_range[0]:s_range[1]].float().mean(dim=1).cpu()
        return f

    clear_act_cache()
    with block_hooks(model, edits, {l: cap(l) for l in blocks}):
        out = model.model(input_ids=inp, use_cache=False)
    res: dict[str, Any] = {"states": got, "s_mean": got_s}
    if want_embed:
        e = model.model.embed_tokens(inp[:, want_embed]).float().cpu()
        res["embed"] = e
    if want_logits:
        hl = out.last_hidden_state[:, want_logits]
        lp = torch.log_softmax(model.lm_head(hl).float(), dim=-1)
        v, i = lp.topk(topk, dim=-1)
        res["top_lp"] = v.cpu().numpy()
        res["top_id"] = i.cpu().numpy()
    del out
    clear_act_cache()
    return res


def free(*objs: Any) -> None:
    for o in objs:
        del o
    gc.collect()
    torch.cuda.empty_cache()
