#!/usr/bin/env python3
"""bf16 HF engine for Qwen3-8B (ported from iteration-5 exp26 src/engine5.py): prompt prefill with block-output edit
hooks, the common-random-numbers inverse-CDF sampler (float64 softmax(logits / T), one uniform per (row, step), token =
first vocabulary index whose CDF >= u; prune=False, constant batch shape, preallocated KV) with the FENCE STOP (a row is
finished once its first fenced python block is closed, checked every 8 steps), plus the iteration-6 GTN hook:
generated-token noise on rows paired with a teacher-forced SHADOW row in the same batch (the shadow is fed the GTN row's
sampled token at every step and receives no edit; at generated tokens 1..32 the GTN row's block-l output becomes
h <- h + (alpha*n_t - (h - h_shadow).u) u with n_t = r_Q(l) * ||h_shadow||, blocks 12-23, fp32 then bf16), and
teacher-forced log-probs in B-row right-padded batches with an attention mask (q_lik, fork margins).
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

from cfg6 import EDIT_BLOCKS, ENDOFTEXT, IM_END, MAX_NEW, R_Q, crn_seed, model_path

BENCH_FENCE = re.compile(r"```[ \t]*(?:python3?|py|Python)?[ \t]*\n(.*?)```", re.S)
_TICK: dict[str, Any] = {}


def load_model(model_id: str, revision: str | None, vram_fraction: float = 0.97):
    from transformers import AutoModelForCausalLM, AutoTokenizer

    t0 = time.time()
    path = model_path(model_id, revision)
    tok = AutoTokenizer.from_pretrained(path)
    model = AutoModelForCausalLM.from_pretrained(path, dtype=torch.bfloat16, attn_implementation="sdpa",
                                                 device_map={"": 0}, low_cpu_mem_usage=True)
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


def u_stream(unit: str, w: str, k: int, n: int = MAX_NEW) -> np.ndarray:
    """CRN: PCG64(int(sha256('iter6|panelI|'+unit+'|'+w+'|'+k)[:16], 16)).random(max_new)."""
    return np.random.Generator(np.random.PCG64(crn_seed(unit, w, k))).random(n)


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


def fence_closed(text: str) -> bool:
    return BENCH_FENCE.search(text) is not None


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
def sample(model: Any, tok: Any, groups: list[dict[str, Any]], max_new: int = MAX_NEW, temperature: float = 1.0,
           check_every: int = 8, gtn: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """groups: [{'pre': prefill dict, 'us': [np.ndarray[max_new], ...]}]; every row shares the prompt length P.
    gtn (optional): {'pairs': [(gtn_row, shadow_row)], 'U': fp32 [G, D] directions (one per pair), 'alpha': float,
    'steps': 32}. Returns per row: token_ids, finish_reason, n_tokens, logprob_sum, steps, fence_step, and for GTN rows
    the realised displacement record."""
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
    tm = tick_mask(tok, dev)
    fence_step: list[int | None] = [None] * Bn
    # ---- GTN hook state
    hooks = []
    gstate: dict[str, Any] = {"step": 0}
    disp_rec: dict[int, list[float]] = {}
    if gtn:
        gi = torch.tensor([p[0] for p in gtn["pairs"]], device=dev)
        si = torch.tensor([p[1] for p in gtn["pairs"]], device=dev)
        Ug = gtn["U"].to(dev).float()
        alpha = float(gtn["alpha"])
        n_steps = int(gtn.get("steps", 32))
        shadow_rows = set(int(x) for x in si.tolist())

        def mk(l):
            def hook(mod, inp, out, l=l):
                t = gstate["step"]
                if not (1 <= t <= n_steps):
                    return out
                h = _out_tensor(out)
                hg = h[gi, -1].float()
                hs_ = h[si, -1].float()
                n_t = R_Q[l] * hs_.norm(dim=-1)
                comp = ((hg - hs_) * Ug).sum(-1)
                new = hg + (alpha * n_t - comp)[:, None] * Ug
                h = h.clone()
                h[gi, -1] = new.to(h.dtype)
                if l == EDIT_BLOCKS[-1]:
                    d = ((new.to(h.dtype).float() - hs_) * Ug).sum(-1)
                    rel = ((d - alpha * n_t).abs() / (alpha * n_t).abs().clamp(min=1e-6)).tolist()
                    for j, r in enumerate(rel):
                        disp_rec.setdefault(j, []).append(r)
                return _replace_out(out, h)
            return hook
        for l in EDIT_BLOCKS:
            hooks.append(layers(model)[l].register_forward_hook(mk(l)))
    last_chk = 0
    step = 0
    try:
        while True:
            probs = torch.softmax(logits / temperature, dim=-1)
            nxt = _inverse_cdf(probs, U[:, step])
            if gtn and step < n_steps:
                # generated tokens 1..n_steps: the shadow row is teacher-forced with its GTN row's token
                nxt = nxt.clone()
                nxt[si] = nxt[gi]
            plp = torch.log(probs.gather(-1, nxt[:, None])[:, 0])
            live = ~done
            toks[:, step] = torch.where(live, nxt, toks[:, step])
            lps[:, step] = torch.where(live, plp, lps[:, step])
            is_end = (nxt == IM_END) | (nxt == ENDOFTEXT)
            ended |= live & is_end
            done |= is_end
            if gtn and step < n_steps:
                # inside the window a shadow row lives exactly as long as its GTN row
                done[si] = done[gi]
            elif gtn and step == n_steps:
                # after the window the shadow is masked (fed <|im_end|>, kept in the batch so B stays fixed)
                done[si] = True
            if step + 1 >= max_new:
                break
            if (step + 1) % check_every == 0:
                win = toks[:, last_chk:step + 1]
                hit = (tm[win.clamp(min=0)] & (win >= 0)).any(dim=1) & ~done
                rows = torch.nonzero(hit).flatten().tolist()
                if rows:
                    tc = toks[rows, :step + 1].cpu().numpy()
                    for j, r in enumerate(rows):
                        ids = [int(t) for t in tc[j] if t >= 0]
                        if fence_closed(tok.decode(ids, skip_special_tokens=True)):
                            done[r] = True
                            fence_step[r] = step
                last_chk = step + 1
                if gtn and step < n_steps:
                    done[si] = done[gi]
                if bool(done.all().item()):
                    break
            feed = torch.where(done, im_end_t, nxt)
            pos = torch.full((Bn, 1), P + step, device=dev, dtype=torch.long)
            gstate["step"] = step + 1
            h = model.model(input_ids=feed[:, None], past_key_values=cache, position_ids=pos,
                            use_cache=True).last_hidden_state
            logits = model.lm_head(h[:, -1]).double()
            step += 1
    finally:
        for hk in hooks:
            hk.remove()
    del cache
    toks_c = toks.cpu().numpy()
    lps_c = lps.cpu().numpy()
    ended_c = ended.cpu().numpy()
    out = []
    pair_of = {int(p[0]): j for j, p in enumerate(gtn["pairs"])} if gtn else {}
    for r in range(Bn):
        row = toks_c[r]
        n = int((row >= 0).sum())
        fr = "stop" if ended_c[r] else ("fence" if fence_step[r] is not None else "length")
        rec = {"token_ids": [int(t) for t in row[:n]], "finish_reason": fr, "n_tokens": n,
               "logprob_sum": float(lps_c[r, :n].sum()), "steps": step + 1, "fence_step": fence_step[r]}
        if gtn and r in pair_of:
            v = disp_rec.get(pair_of[r], [])
            rec["gtn_rel_err_max"] = max(v) if v else None
            rec["gtn_edited_steps"] = len(v)
        if gtn and r in shadow_rows:
            rec["shadow"] = True
        out.append(rec)
    return out


@torch.no_grad()
def teacher_forced(model: Any, seqs: list[tuple[list[int], list[int]]], batch: int = 8) -> list[list[float]]:
    """Per-token log p(cont_t | prompt + cont_<t) for each (prompt_ids, cont_ids), right-padded batches with an
    attention mask, fp32 log-softmax. Returns the list of per-token log-probs of every continuation."""
    out: list[list[float]] = []
    dev = model.device
    for i in range(0, len(seqs), batch):
        part = seqs[i:i + batch]
        L = max(len(p) + len(c) for p, c in part)
        inp = torch.full((len(part), L), ENDOFTEXT, dtype=torch.long, device=dev)
        att = torch.zeros((len(part), L), dtype=torch.long, device=dev)
        for j, (p, c) in enumerate(part):
            s = p + c
            inp[j, :len(s)] = torch.tensor(s, device=dev)
            att[j, :len(s)] = 1
        logits = model(input_ids=inp, attention_mask=att, use_cache=False).logits
        for j, (p, c) in enumerate(part):
            P = len(p)
            sl = logits[j, P - 1:P - 1 + len(c)].float()
            lp = torch.log_softmax(sl, dim=-1)
            idx = torch.tensor(c, device=dev)
            out.append(lp.gather(-1, idx[:, None])[:, 0].tolist())
        del logits
    return out


def free_cuda() -> None:
    gc.collect()
    torch.cuda.empty_cache()
