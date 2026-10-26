#!/usr/bin/env python3
"""HF engine for Qwen3-8B on a 16 GB Ada GPU (exp17 engine, extended).

Reused from exp17 (src/engine.py, art_pVlCZ272hDV7) unchanged: FP8 (E4M3) W8A8-dynamic decoder linears with
per-output-channel weight scales and per-token activation scales (rows are numerically independent of their
batch-mates for a fixed batch shape), batch-1 prefill with block-output edit hooks, the exp8 common-random-numbers
inverse-CDF sampler (finished rows stay in the batch, fed <|im_end|>), and the preallocated KV cache.

Extensions for this artifact:
- fence stop: a row also finishes once it has emitted two tokens containing a code fence (```), i.e. at the closing
  fence of its first code block (exp16 'fence stop'); the tokens up to that point are unchanged.
- S3 decode-time site: for (hooked, shadow) row pairs, at decode steps whose INPUT is generated token 1-32 the hooked
  row's block outputs at blocks 12-23 are displaced along its own unit u_i so that (h_i - h_shadow) . u_i equals the
  target exactly; the shadow row is fed the hooked row's token at every step (teacher forcing), so it carries the clean
  states of the same text. Logs per pair: displacement at blocks 23 and 35 and KL(hooked || shadow) per step.
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
    for layer in model.model.layers:
        for _, mod in list(layer.named_modules()):
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
    """edits: {block: f(h) -> h'} applied to the block OUTPUT; capture: {block: g(h)} called after the edit."""
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


# ------------------------------------------------------------------------------------------------ caches
def _kv_list(cache: Any) -> list[tuple[torch.Tensor, torch.Tensor]]:
    if hasattr(cache, "layers"):
        return [(L.keys, L.values) for L in cache.layers]
    return list(zip(cache.key_cache, cache.value_cache))


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
    """exp17/exp8 token uniforms: PCG64(stable_seed(*key)).random(n)."""
    return np.random.Generator(np.random.PCG64(stable_seed(*key))).random(n)


def _inverse_cdf(probs: torch.Tensor, u: torch.Tensor) -> torch.Tensor:
    cdf = probs.cumsum(dim=-1)
    cdf = cdf / cdf[:, -1:]
    tok = torch.searchsorted(cdf, u[:, None].to(cdf.dtype)).squeeze(-1)
    return tok.clamp_(max=probs.shape[-1] - 1)


class PreallocLayer:
    """KV layer with a preallocated [B, H, Lmax, D] buffer (exp17)."""

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


def prealloc_cache(kv: list[tuple[torch.Tensor, torch.Tensor]], max_len: int):
    from transformers.cache_utils import Cache

    return Cache(layers=[PreallocLayer(K, V, max_len) for K, V in kv])


def fence_token_mask(tok: Any, device: torch.device) -> torch.Tensor:
    """Bool [V]: tokens whose decoded text contains a code fence (```)."""
    V = len(tok)
    m = np.zeros(max(V, 151936 + 1024), dtype=bool)
    for i in range(V):
        s = tok.decode([i])
        if "```" in s:
            m[i] = True
    return torch.tensor(m, device=device)


@torch.no_grad()
def sample(model: Any, groups: list[dict[str, Any]], max_new: int = MAX_NEW_TOKENS, temperature: float = 1.0,
           fence_mask: torch.Tensor | None = None, s3: dict[str, Any] | None = None, check_every: int = 8,
           no_stop: bool = False) -> list[dict[str, Any]]:
    """groups: [{'pre': prefill dict, 'us': [np.ndarray[max_new], ...]}] -- each group's prefill is shared by its rows.
    One uniform per (row, step); token = first index whose CDF (vocabulary order, float64) >= u (exp8 sampler).
    Finished rows stay in the batch (fed <|im_end|>), so the batch shape is identical at every step in every arm.
    s3 (optional): {'hooked': [row idx], 'shadow': [row idx], 'u': fp32 [n_pairs, D], 'target': {l: fp32 [n_pairs]},
    'blocks': [...], 'steps': 32, 'log_blocks': [23, 35], 'keep_shadow_states': bool}."""
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
    ended = torch.zeros(B, dtype=torch.bool, device=dev)
    fenced = torch.zeros(B, dtype=torch.bool, device=dev)
    nfence = torch.zeros(B, dtype=torch.long, device=dev)
    im_end_t = torch.full((B,), IM_END, dtype=torch.long, device=dev)
    state = {"step": 0}
    hooks = []
    s3_log: dict[str, list] = {"disp": [], "kl": [], "shadow_states": []}
    if s3:
        hi = torch.tensor(s3["hooked"], device=dev, dtype=torch.long)
        si = torch.tensor(s3["shadow"], device=dev, dtype=torch.long)
        Uv = s3["u"].to(dev, torch.float32)  # [n, D]
        tgt = {l: s3["target"][l].to(dev, torch.float32) for l in s3["blocks"]}
        log_blocks = s3.get("log_blocks", [23, 35])
        cur_disp: dict[int, torch.Tensor] = {}

        def mk(l):
            def hook(mod, inp, out):
                h = _out_tensor(out)
                if h.shape[1] != 1:
                    return out
                if l in tgt and state["step"] < s3["steps"]:
                    hh = h[hi, 0].float()
                    hs = h[si, 0].float()
                    coef = tgt[l] - ((hh - hs) * Uv).sum(-1)
                    h = h.clone()
                    h[hi, 0] = (hh + coef[:, None] * Uv).to(h.dtype)
                    out = _replace_out(out, h)
                if l in log_blocks and state["step"] < s3["steps"]:
                    cur_disp[l] = (h[hi, 0].float() - h[si, 0].float()).norm(dim=-1)
                    if s3.get("keep_shadow_states") and l == log_blocks[0]:
                        s3_log["shadow_states"].append(h[si, 0].float().cpu())
                        s3_log.setdefault("hooked_states", []).append(h[hi, 0].float().cpu())
                return out
            return hook
        for l in sorted(set(s3["blocks"]) | set(log_blocks)):
            hooks.append(layers(model)[l].register_forward_hook(mk(l)))
    step = 0
    try:
        while True:
            state["step"] = step
            probs = torch.softmax(logits / temperature, dim=-1)
            nxt = _inverse_cdf(probs, U[:, step])
            if s3:
                nxt[si] = nxt[hi]  # shadows are teacher-forced with the hooked row's token
            plp = torch.log(probs.gather(-1, nxt[:, None])[:, 0])
            live = ~done
            toks[:, step] = torch.where(live, nxt, toks[:, step])
            lps[:, step] = torch.where(live, plp, lps[:, step])
            is_end = (nxt == IM_END) | (nxt == ENDOFTEXT)
            ended |= live & is_end
            if fence_mask is not None and not no_stop:
                nfence += (fence_mask[nxt] & live).long()
                fz = live & (nfence >= 2) & ~is_end
                fenced |= fz
                done |= fz
            done |= is_end
            if s3:
                done[si] = done[hi]
            if no_stop:
                done.zero_()
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
            if s3 and step < s3["steps"]:
                lp_h = torch.log_softmax(logits[hi], -1)
                lp_s = torch.log_softmax(logits[si], -1)
                s3_log["kl"].append((lp_h.exp() * (lp_h - lp_s)).sum(-1).float())
                s3_log["disp"].append({l: cur_disp[l].clone() for l in cur_disp})
            step += 1
    finally:
        for hk in hooks:
            hk.remove()
        clear_act_cache()
    del cache
    toks_c = toks.cpu().numpy()
    lps_c = lps.cpu().numpy()
    ended_c = ended.cpu().numpy()
    fenced_c = fenced.cpu().numpy()
    out = []
    for r in range(B):
        row = toks_c[r]
        n = int((row >= 0).sum())
        ids = [int(t) for t in row[:n]]
        fr = "stop" if ended_c[r] else ("fence" if fenced_c[r] else "length")
        out.append({"token_ids": ids, "finish_reason": fr, "n_tokens": n,
                    "logprob_sum": float(lps_c[r, :n].sum()), "steps": step + 1})
    if s3:
        kl = torch.stack(s3_log["kl"], 0).cpu().numpy() if s3_log["kl"] else np.zeros((0, len(s3["hooked"])))
        disp = {l: torch.stack([d[l] for d in s3_log["disp"]], 0).cpu().numpy() for l in
                (s3_log["disp"][0].keys() if s3_log["disp"] else [])}
        for j, r in enumerate(s3["hooked"]):
            out[r]["s3"] = {"kl_mean_steps1_32": float(kl[:, j].mean()) if len(kl) else None,
                            "kl_steps": [round(float(x), 6) for x in kl[:, j]],
                            "disp_mean": {int(l): float(disp[l][:, j].mean()) for l in disp},
                            "disp_steps": {int(l): [round(float(x), 4) for x in disp[l][:, j]] for l in disp}}
        if s3.get("keep_shadow_states"):
            out[0]["_shadow_states"] = s3_log["shadow_states"]
            out[0]["_hooked_states"] = s3_log.get("hooked_states", [])
    return out


@torch.no_grad()
def forward_capture(model: Any, ids: list[int], blocks: list[int]) -> dict[int, torch.Tensor]:
    """Batch-1 forward without cache; returns block outputs at ALL positions ({l: fp32 [T, D]} on GPU)."""
    got: dict[int, torch.Tensor] = {}

    def cap(l):
        def f(h):
            got[l] = h[0].float().clone()
        return f
    clear_act_cache()
    with block_hooks(model, None, {l: cap(l) for l in blocks}):
        model.model(input_ids=torch.tensor([ids], device=model.device), use_cache=False)
    clear_act_cache()
    return got


def free_cuda() -> None:
    gc.collect()
    torch.cuda.empty_cache()
