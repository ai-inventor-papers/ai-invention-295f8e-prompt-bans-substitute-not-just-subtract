#!/usr/bin/env python3
"""bf16 HF engine for Qwen3-8B and Qwen3-8B-Base on one RTX 4090 (24 GiB): prompt prefill with block-output edit hooks,
the exp8 common-random-numbers inverse-CDF sampler (prune=False, constant batch shape, preallocated KV) with the
exp16/exp22 FENCE STOP, and teacher-forced forward passes (opening log-probs, state capture).

Ported from iteration-4 exp22 (src_base/engine.py + src/engine4.py) with the FP8 W8A8 path removed: the frozen
precision rule selects bf16 because this GPU has more than 19.5 GiB (results/precision.json). Every operation of the
sampler (float64 softmax over logits / T, one uniform per (row, step), first CDF index >= u) is unchanged.
"""

from __future__ import annotations

import contextlib
import gc
import re
import time
from typing import Any, Callable, Iterator

import numpy as np
import torch
from loguru import logger

from cfg5 import ENDOFTEXT, IM_END, MAX_NEW, model_path, stable_seed

BENCH_FENCE = re.compile(r"```[ \t]*(?:python3?|py|Python)?[ \t]*\n(.*?)```", re.S)
PATH_FENCE = re.compile(r"```(?:python|py|Python|python3)[ \t]*\n(.*?)```", re.S)
_TICK: dict[str, Any] = {}


def load_model(model_id: str, revision: str | None, vram_fraction: float = 0.97):
    from transformers import AutoModelForCausalLM, AutoTokenizer

    t0 = time.time()
    path = model_path(model_id, revision)
    kw = {"revision": revision} if path == model_id and revision else {}
    tok = AutoTokenizer.from_pretrained(path, **kw)
    model = AutoModelForCausalLM.from_pretrained(path, dtype=torch.bfloat16, attn_implementation="sdpa",
                                                 device_map={"": 0}, **kw)
    model.eval()
    model.requires_grad_(False)
    torch.cuda.set_per_process_memory_fraction(vram_fraction, 0)
    free, total = torch.cuda.mem_get_info(0)
    logger.info(f"{model_id}@{revision} loaded in {time.time() - t0:.0f}s; free VRAM {free / 1e9:.1f}/"
                f"{total / 1e9:.1f} GB")
    return tok, model


def layers(model: Any) -> Any:
    return model.model.layers


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
    with block_hooks(model, edits, capture):
        out = model.model(input_ids=inp, past_key_values=cache, use_cache=True)
    r_logits = model.lm_head(out.last_hidden_state[:, -1]).float()[0]
    kv = [(K.clone(), V.clone()) for K, V in _kv_list(cache)]
    del cache, out
    return {"kv": kv, "r_logits": r_logits, "P": len(ids)}


def u_stream(*key: Any, n: int = MAX_NEW) -> np.ndarray:
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
        Bn, H, L, D = K.shape
        self.kbuf = torch.empty(Bn, H, max_len, D, dtype=K.dtype, device=K.device)
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


def fence_closed(text: str, kind: str) -> bool:
    if kind == "bench":
        return BENCH_FENCE.search(text) is not None
    if kind == "plain":
        return "```" in text
    m = PATH_FENCE.search(text)
    return bool(m and m.group(1).strip())


def tick_mask(tok: Any, device: torch.device) -> torch.Tensor:
    if "mask" not in _TICK:
        V = len(tok)
        m = torch.zeros(max(V, 151936 + 1024), dtype=torch.bool)
        for i in range(V):
            if "`" in tok.decode([i]):
                m[i] = True
        _TICK["mask"] = m.to(device)
    return _TICK["mask"]


@torch.no_grad()
def sample(model: Any, tok: Any, groups: list[dict[str, Any]], fence: str | None, max_new: int = MAX_NEW,
           temperature: float = 1.0, check_every: int = 8) -> list[dict[str, Any]]:
    """groups: [{'pre': prefill dict, 'us': [np.ndarray[max_new], ...]}]; all rows share the prompt length P.
    One uniform per (row, step); token = first index whose CDF (vocabulary order, float64) >= u (exp8 sampler).
    prune=False: finished rows stay in the batch (fed <|im_end|>). FENCE STOP (exp22): a row is finished once its
    first fenced python block is closed (checked every `check_every` steps on rows that drew a backtick token)."""
    P = groups[0]["pre"]["P"]
    assert all(g["pre"]["P"] == P for g in groups), "all rows of a batch must share the prompt length"
    dev = model.device
    n_layers = len(groups[0]["pre"]["kv"])
    kv = []
    for l in range(n_layers):
        Ks, Vs = [], []
        for g in groups:
            Kt, Vt = g["pre"]["kv"][l]
            Ks.append(Kt.expand(len(g["us"]), -1, -1, -1))
            Vs.append(Vt.expand(len(g["us"]), -1, -1, -1))
        kv.append((torch.cat(Ks, 0), torch.cat(Vs, 0)))
    cache = prealloc_cache(kv, P + max_new + 1)
    del kv
    us = [u for g in groups for u in g["us"]]
    Bn = len(us)
    U = torch.tensor(np.stack([u[:max_new] for u in us]), dtype=torch.float64, device=dev)
    logits = torch.cat([g["pre"]["r_logits"][None].expand(len(g["us"]), -1) for g in groups], 0).double()
    toks = torch.full((Bn, max_new), -1, dtype=torch.long, device=dev)
    lps = torch.zeros((Bn, max_new), dtype=torch.float64, device=dev)
    done = torch.zeros(Bn, dtype=torch.bool, device=dev)
    ended = torch.zeros(Bn, dtype=torch.bool, device=dev)
    im_end_t = torch.full((Bn,), IM_END, dtype=torch.long, device=dev)
    tm = tick_mask(tok, dev) if fence else None
    fence_step: list[int | None] = [None] * Bn
    last_chk = 0
    step = 0
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
        if (step + 1) % check_every == 0:
            if fence:
                win = toks[:, last_chk:step + 1]
                hit = (tm[win.clamp(min=0)] & (win >= 0)).any(dim=1) & ~done
                rows = torch.nonzero(hit).flatten().tolist()
                if rows:
                    tc = toks[rows, :step + 1].cpu().numpy()
                    for j, r in enumerate(rows):
                        ids = [int(t) for t in tc[j] if t >= 0]
                        if fence_closed(tok.decode(ids, skip_special_tokens=True), fence):
                            done[r] = True
                            fence_step[r] = step
                last_chk = step + 1
            if bool(done.all().item()):
                break
        feed = torch.where(done, im_end_t, nxt)[:, None]
        pos = torch.full((Bn, 1), P + step, device=dev, dtype=torch.long)
        h = model.model(input_ids=feed, past_key_values=cache, position_ids=pos, use_cache=True).last_hidden_state
        logits = model.lm_head(h[:, -1]).double()
        step += 1
    del cache
    toks_c = toks.cpu().numpy()
    lps_c = lps.cpu().numpy()
    ended_c = ended.cpu().numpy()
    out = []
    for r in range(Bn):
        row = toks_c[r]
        n = int((row >= 0).sum())
        fr = "stop" if ended_c[r] else ("fence" if fence_step[r] is not None else "length")
        out.append({"token_ids": [int(t) for t in row[:n]], "finish_reason": fr, "n_tokens": n,
                    "logprob_sum": float(lps_c[r, :n].sum()), "steps": step + 1, "fence_step": fence_step[r]})
    return out


@torch.no_grad()
def teacher_forced_logprob(model: Any, prompt_ids: list[int], cont_ids_list: list[list[int]],
                           batch: int = 8) -> list[float]:
    """Sum of log p(continuation tokens | prompt) for each continuation (right-padded batches)."""
    out: list[float] = []
    dev = model.device
    for i in range(0, len(cont_ids_list), batch):
        part = cont_ids_list[i:i + batch]
        L = max(len(c) for c in part)
        seqs = [prompt_ids + c + [ENDOFTEXT] * (L - len(c)) for c in part]
        inp = torch.tensor(seqs, device=dev)
        logits = model(input_ids=inp, use_cache=False).logits.float()
        lp = torch.log_softmax(logits, dim=-1)
        P = len(prompt_ids)
        for j, c in enumerate(part):
            s = 0.0
            for t, tid in enumerate(c):
                s += float(lp[j, P + t - 1, tid])
            out.append(s)
        del logits, lp
    return out


def free_cuda() -> None:
    gc.collect()
    torch.cuda.empty_cache()
