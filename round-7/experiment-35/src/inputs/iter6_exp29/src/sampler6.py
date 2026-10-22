#!/usr/bin/env python3
"""The vendored exp22 engine4.sample (exact inverse-CDF CRN draw, prune=False, constant batch shape, fence stop),
copied line for line, with ONE addition for the 16 GB card: the preallocated KV buffer holds `cap` generated tokens
instead of max_new. KV capacity never changes numerics (the cache returns views of the valid prefix), so every row
that finishes within `cap` tokens is bitwise what the vendored sampler draws (tested in U6). If live rows remain when
the buffer is full, those rows only are moved to a full-length buffer and continue to max_new (OVERFLOW; the batch
then has fewer rows, which can change numerics of those rows' later tokens -- each such row is flagged
'overflow_at_step'). With cap >= max_new this is exactly the vendored sampler.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import torch

import c6  # noqa: F401
from engine import _inverse_cdf, clear_act_cache, prealloc_cache  # vendored
from engine4 import ENDOFTEXT, IM_END, fence_closed, tick_mask  # vendored


@torch.no_grad()
def sample(model: Any, tok: Any, groups: list[dict[str, Any]], fence: str | None, max_new: int = 1024,
           temperature: float = 1.0, check_every: int = 8, cap: int | None = None) -> list[dict[str, Any]]:
    dev = model.device
    cap_len = max_new if cap is None else min(int(cap), max_new)
    us = [u for g in groups for u in g["us"]]
    Bn = len(us)
    cache, r_rows, P = _build_cache(model, groups, Bn, cap_len)
    U = torch.tensor(np.stack([u[:max_new] for u in us]), dtype=torch.float64, device=dev)
    logits = torch.cat(r_rows, 0).double()
    del r_rows
    toks = torch.full((Bn, max_new), -1, dtype=torch.long, device=dev)
    lps = torch.zeros((Bn, max_new), dtype=torch.float64, device=dev)
    done = torch.zeros(Bn, dtype=torch.bool, device=dev)
    ended = torch.zeros(Bn, dtype=torch.bool, device=dev)
    tm = tick_mask(tok, dev) if fence else None
    fence_step = [None] * Bn
    overflow_at = [None] * Bn
    act = torch.arange(Bn, device=dev)          # global ids of the rows in the current batch
    full = True                                  # act == all rows
    last_chk = 0
    step = 0
    try:
        while True:
            probs = torch.softmax(logits / temperature, dim=-1)
            nxt = _inverse_cdf(probs, U[act, step])
            plp = torch.log(probs.gather(-1, nxt[:, None])[:, 0])
            live = ~done[act]
            toks[act, step] = torch.where(live, nxt, toks[act, step])
            lps[act, step] = torch.where(live, plp, lps[act, step])
            is_end = (nxt == IM_END) | (nxt == ENDOFTEXT)
            ended[act] |= live & is_end
            done[act] |= is_end
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
            if step + 1 > cap_len:   # the next feed would write past the buffer: move live rows to a full buffer
                keep = (~done[act]).nonzero().flatten()
                if keep.numel() == 0:
                    break
                new_layers = []
                for L in cache.layers:
                    n = L.n
                    Kn = torch.empty(keep.numel(), L.kbuf.shape[1], P + max_new + 1, L.kbuf.shape[3],
                                     dtype=L.kbuf.dtype, device=dev)
                    Vn = torch.empty_like(Kn)
                    Kn[:, :, :n] = L.kbuf[keep, :, :n]
                    Vn[:, :, :n] = L.vbuf[keep, :, :n]
                    L.kbuf = L.vbuf = L.keys = L.values = None
                    new_layers.append((Kn, Vn, n))
                del cache
                torch.cuda.empty_cache()
                from transformers.cache_utils import Cache
                from engine import PreallocLayer
                layers = []
                for Kn, Vn, n in new_layers:
                    pl = PreallocLayer.__new__(PreallocLayer)
                    pl.kbuf, pl.vbuf, pl.n = Kn, Vn, n
                    pl.dtype, pl.device, pl.is_initialized = Kn.dtype, Kn.device, True
                    pl.keys, pl.values = Kn[:, :, :n], Vn[:, :, :n]
                    layers.append(pl)
                cache = Cache(layers=layers)
                del new_layers
                act = act[keep]
                nxt = nxt[keep]
                for r in act.tolist():
                    overflow_at[r] = step
                cap_len = max_new
                full = False
            feed = torch.where(done[act], torch.full_like(nxt, IM_END), nxt)[:, None]
            pos = torch.full((act.numel(), 1), P + step, device=dev, dtype=torch.long)
            clear_act_cache()
            h = model.model(input_ids=feed, past_key_values=cache, position_ids=pos, use_cache=True).last_hidden_state
            logits = model.lm_head(h[:, -1]).double()
            step += 1
    finally:
        clear_act_cache()
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
                    "logprob_sum": float(lps_c[r, :n].sum()), "steps": step + 1, "fence_step": fence_step[r],
                    "overflow_at_step": overflow_at[r], "batch_full_to_end": full})
    return out

def _build_cache(model: Any, groups: list[dict[str, Any]], Bn: int, cap_len: int):
    """Streamed version of the vendored expand/cat/prealloc_cache: the [Bn, H, P + cap_len + 1, D] buffers are
    allocated first and each group's prefill KV is copied into its rows, one group at a time. A group whose 'pre' is a
    callable is prefilled here and released right after the copy (peak memory = buffer + one prefill). The values in
    the buffer are exactly the vendored ones (same prefill tensors, plain copies)."""
    from transformers.cache_utils import Cache

    from engine import PreallocLayer

    cfg = model.config
    nL, H, D = cfg.num_hidden_layers, cfg.num_key_value_heads, cfg.head_dim
    dev = model.device
    kb = vb = None
    P = None
    r_rows = []
    r0 = 0
    for g in groups:
        pre = g["pre"]() if callable(g["pre"]) else g["pre"]
        n = len(g["us"])
        if P is None:
            P = pre["P"]
            kb = [torch.empty(Bn, H, P + cap_len + 1, D, dtype=torch.bfloat16, device=dev) for _ in range(nL)]
            vb = [torch.empty_like(kb[0]) for _ in range(nL)]
        assert pre["P"] == P, "all rows of a batch must share the prompt length"
        for l in range(nL):
            K, V = pre["kv"][l]
            kb[l][r0:r0 + n, :, :P] = K.expand(n, -1, -1, -1)
            vb[l][r0:r0 + n, :, :P] = V.expand(n, -1, -1, -1)
        r_rows.append(pre["r_logits"][None].expand(n, -1).clone())
        r0 += n
        if callable(g["pre"]):
            del pre
    assert r0 == Bn
    layers = []
    for l in range(nL):
        pl = PreallocLayer.__new__(PreallocLayer)
        pl.kbuf, pl.vbuf, pl.n = kb[l], vb[l], P
        pl.dtype, pl.device, pl.is_initialized = kb[l].dtype, kb[l].device, True
        pl.keys, pl.values = kb[l][:, :, :P], vb[l][:, :, :P]
        layers.append(pl)
    return Cache(layers=layers), r_rows, P
