#!/usr/bin/env python3
"""HF scoring engine (S3/S5): l(p | c) = summed log-probability of a scored program placed as the assistant turn under
prompt c (fp32 log-softmax), with the prompt prefilled ONCE and its KV cache reused across length-sorted, right-padded
program batches (a fresh DynamicCache per batch built from the prompt K/V repeated to the batch size; causal masking
alone protects real tokens from right padding). Also: patch-style random edits at prompt positions (forward hooks on
decoder layers), hybrid route-test caches, layer-output capture for the ban displacement, and the T3/T4/T7/T8 checks.
"""

from __future__ import annotations

import gc
import math
import time
from dataclasses import dataclass
from typing import Any, Callable

import numpy as np
import torch
from loguru import logger
from transformers import AutoModelForCausalLM, DynamicCache

LM_CHUNK = 1024


@dataclass
class PromptState:
    kv: list[tuple[torch.Tensor, torch.Tensor]]  # per layer (k, v) [1, n_kv, T, d]
    last_logp: torch.Tensor  # [V] fp32 log-softmax at position R
    T: int


class Scorer:
    def __init__(self, path: str, quant8: bool = False):
        t0 = time.time()
        kw: dict[str, Any] = {"torch_dtype": torch.bfloat16, "attn_implementation": "sdpa"}
        if quant8:
            from transformers import BitsAndBytesConfig

            kw["quantization_config"] = BitsAndBytesConfig(load_in_8bit=True)
            self.model = AutoModelForCausalLM.from_pretrained(path, device_map="cuda", **kw).eval()
        else:
            self.model = AutoModelForCausalLM.from_pretrained(path, **kw).cuda().eval()
        self.layers = self.model.model.layers
        self.n_layers = len(self.layers)
        # fp32 LM head: bf16 logits (|logit| ~ 30) carry ~0.05-nat rounding per token, which summed over a ~250-token
        # program gave up to 0.7 nats of batch-composition noise (T4); the head is applied in fp32 everywhere.
        torch.backends.cuda.matmul.allow_tf32 = False
        self.W32 = self.model.lm_head.weight.detach().float()
        self.budget = 4096
        logger.info(f"HF model loaded in {time.time() - t0:.1f}s; layers={self.n_layers}")

    # -------------------------------------------------------------------------------------------- prompt
    @torch.inference_mode()
    def prefill(self, ids: list[int], hooks: list[tuple[int, Callable]] | None = None) -> PromptState:
        handles = [self.layers[l].register_forward_hook(fn) for l, fn in (hooks or [])]
        try:
            x = torch.tensor([ids], device="cuda")
            out = self.model.model(input_ids=x, use_cache=True)
        finally:
            for h in handles:
                h.remove()
        cache = out.past_key_values
        kv = [(lay.keys, lay.values) for lay in cache.layers]
        last = torch.log_softmax(self.head32(out.last_hidden_state[0, -1:])[0], dim=-1)
        return PromptState(kv=kv, last_logp=last, T=len(ids))

    @torch.inference_mode()
    def capture(self, ids: list[int], layers: list[int], pos: slice) -> torch.Tensor:
        """Outputs of `layers` at positions `pos` -> [len(layers), n_pos, d] fp32."""
        store: dict[int, torch.Tensor] = {}

        def mk(l: int):
            def fn(_m, _i, out):
                h = out[0] if isinstance(out, tuple) else out
                store[l] = h[0, pos].float().clone()
            return fn

        handles = [self.layers[l].register_forward_hook(mk(l)) for l in layers]
        try:
            self.model.model(input_ids=torch.tensor([ids], device="cuda"), use_cache=False)
        finally:
            for h in handles:
                h.remove()
        return torch.stack([store[l] for l in layers])

    def head32(self, h: torch.Tensor) -> torch.Tensor:
        return h.float() @ self.W32.T

    @staticmethod
    def hybrid(a: PromptState, b: PromptState, split: int, first_from: PromptState) -> PromptState:
        """K/V positions < split from a, >= split from b; first-token logits from `first_from`."""
        assert a.T == b.T
        kv = [(torch.cat([ka[:, :, :split], kb[:, :, split:]], dim=2), torch.cat([va[:, :, :split], vb[:, :, split:]], dim=2))
              for (ka, va), (kb, vb) in zip(a.kv, b.kv)]
        return PromptState(kv=kv, last_logp=first_from.last_logp, T=a.T)

    # -------------------------------------------------------------------------------------------- programs
    @torch.inference_mode()
    def _batch(self, st: PromptState, progs: list[list[int]], per_token: bool = False):
        B = len(progs)
        L = max(len(p) for p in progs)
        inp = torch.zeros((B, L), dtype=torch.long, device="cuda")
        mask = torch.zeros((B, L), dtype=torch.bool, device="cuda")
        for i, p in enumerate(progs):
            inp[i, :len(p)] = torch.tensor(p, device="cuda")
            mask[i, :len(p)] = True
        cache = DynamicCache(ddp_cache_data=[(k.expand(B, -1, -1, -1).contiguous(), v.expand(B, -1, -1, -1).contiguous())
                                             for k, v in st.kv])
        cpos = torch.arange(st.T, st.T + L, device="cuda")
        out = self.model.model(input_ids=inp, past_key_values=cache, use_cache=True, cache_position=cpos,
                               position_ids=cpos.unsqueeze(0).expand(B, -1))
        hid = out.last_hidden_state  # [B, L, d], final norm applied
        del cache, out
        tok_lp = torch.zeros((B, L), dtype=torch.float32, device="cuda")
        tok_lp[:, 0] = st.last_logp[inp[:, 0]]
        if L > 1:
            sel = mask[:, 1:]
            h = hid[:, :-1][sel]
            tgt = inp[:, 1:][sel]
            lps = []
            for c0 in range(0, h.shape[0], LM_CHUNK):
                lg = self.head32(h[c0:c0 + LM_CHUNK])
                lps.append(lg.gather(1, tgt[c0:c0 + LM_CHUNK, None])[:, 0] - torch.logsumexp(lg, dim=-1))
                del lg
            vals = torch.cat(lps)
            tmp = torch.zeros((B, L - 1), dtype=torch.float32, device="cuda")
            tmp[sel] = vals
            tok_lp[:, 1:] = tmp
        tok_lp = tok_lp * mask
        if per_token:
            return [tok_lp[i, :len(p)].cpu().numpy() for i, p in enumerate(progs)]
        return tok_lp.cpu().numpy()

    def score(self, st: PromptState, progs: list[list[int]], n_fence: list[int]) -> tuple[np.ndarray, np.ndarray]:
        """Returns (l_full, l_body) per program (input order)."""
        n = len(progs)
        l_full = np.zeros(n)
        l_body = np.zeros(n)
        order = sorted(range(n), key=lambda i: len(progs[i]))
        i = 0
        while i < n:
            j = i
            L = 0
            while j < n and max(L, len(progs[order[j]])) * (j - i + 1) <= self.budget:
                L = max(L, len(progs[order[j]]))
                j += 1
            j = max(j, i + 1)
            idx = order[i:j]
            try:
                tl = self._batch(st, [progs[k] for k in idx])
            except torch.cuda.OutOfMemoryError:
                torch.cuda.empty_cache()
                gc.collect()
                self.budget = max(512, self.budget // 2)
                logger.warning(f"OOM: batch token budget -> {self.budget}")
                continue
            for r, k in enumerate(idx):
                row = tl[r, :len(progs[k])]
                l_full[k] = float(row.sum())
                l_body[k] = float(row[n_fence[k]:].sum())
            i = j
        return l_full, l_body

    def per_token(self, st: PromptState, prog: list[int]) -> np.ndarray:
        return self._batch(st, [prog], per_token=True)[0]

    @torch.inference_mode()
    def full_sequence(self, prompt_ids: list[int], prog: list[int]) -> np.ndarray:
        """Reference: one full forward over prompt + program (no cache reuse) -> per-token log-probs of prog."""
        x = torch.tensor([prompt_ids + prog], device="cuda")
        hid = self.model.model(input_ids=x, use_cache=False).last_hidden_state[0]
        lp = torch.log_softmax(self.head32(hid[len(prompt_ids) - 1:-1]), dim=-1)
        return lp.gather(1, torch.tensor(prog, device="cuda")[:, None])[:, 0].cpu().numpy()


def logmeanexp(a: np.ndarray, axis: int = -1) -> np.ndarray:
    m = np.max(a, axis=axis, keepdims=True)
    return (m + np.log(np.mean(np.exp(a - m), axis=axis, keepdims=True))).squeeze(axis)


def unit_directions(seed: int, n: int, d: int) -> torch.Tensor:
    g = torch.Generator().manual_seed(seed)
    r = torch.randn((n, d), generator=g, dtype=torch.float64)
    return (r / r.norm(dim=1, keepdim=True)).float()


def edit_hook(h_clean: torch.Tensor, rho: torch.Tensor, r: torch.Tensor, S: slice) -> Callable:
    """Patch-style edit: output[:, S] <- h_clean[S] + rho[S, None] * r (fp32 add, cast back to bf16)."""
    def fn(_m, _i, out):
        h = out[0] if isinstance(out, tuple) else out
        h = h.clone()
        new = h_clean.to(h.device) + rho.to(h.device)[:, None] * r.to(h.device)[None, :]
        h[0, S] = new.to(h.dtype)
        return (h,) + tuple(out[1:]) if isinstance(out, tuple) else h
    return fn


def clean_store_hook(store: dict, l: int, S: slice) -> Callable:
    def fn(_m, _i, out):
        h = out[0] if isinstance(out, tuple) else out
        store[l] = h[0, S].float().clone()
    return fn


_ = math
