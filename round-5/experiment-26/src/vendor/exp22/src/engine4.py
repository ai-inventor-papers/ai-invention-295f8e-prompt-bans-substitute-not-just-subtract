#!/usr/bin/env python3
"""Sampler = exp17 engine.sample (exp8 inverse-CDF CRN draw, prune=False, constant batch shape, preallocated KV)
plus the exp16 FENCE STOP: a row is finished once its first fenced python block is closed (bench: exp11
harness.FENCE_RE; path tasks: the exp8 suite's closed python block). Both labellers extract exactly that first
block, so later tokens cannot change the label; the stop only shortens generation. Detection runs every
`check_every` steps on rows that drew a backtick-bearing token since the last check; tokens drawn between the closing
fence and its detection are kept (they are exactly the tokens the unstopped sampler would have drawn).
Everything else (load_model, prefill, u_stream, forward_capture, FP8 W8A8 linears) is imported from src_base/engine.
"""

from __future__ import annotations

import re
from typing import Any

import numpy as np
import torch

from cfg4 import ENDOFTEXT, IM_END, MAX_NEW
from engine import (_inverse_cdf, clear_act_cache, forward_capture, load_model, prealloc_cache,  # noqa: F401
                    prefill, u_stream)

BENCH_FENCE = re.compile(r"```[ \t]*(?:python3?|py|Python)?[ \t]*\n(.*?)```", re.S)
PATH_FENCE = re.compile(r"```(?:python|py|Python|python3)[ \t]*\n(.*?)```", re.S)
_TICK: dict[str, Any] = {}


def fence_closed(text: str, kind: str) -> bool:
    if kind == "bench":
        return BENCH_FENCE.search(text) is not None
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
    """groups: [{'pre': prefill dict, 'us': [np.ndarray[max_new], ...]}]; all rows share the prompt length P."""
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
    Bn = len(us)
    U = torch.tensor(np.stack([u[:max_new] for u in us]), dtype=torch.float64, device=dev)
    logits = torch.cat([g["pre"]["r_logits"][None].expand(len(g["us"]), -1) for g in groups], 0).double()
    toks = torch.full((Bn, max_new), -1, dtype=torch.long, device=dev)
    lps = torch.zeros((Bn, max_new), dtype=torch.float64, device=dev)
    done = torch.zeros(Bn, dtype=torch.bool, device=dev)
    ended = torch.zeros(Bn, dtype=torch.bool, device=dev)
    im_end_t = torch.full((Bn,), IM_END, dtype=torch.long, device=dev)
    tm = tick_mask(tok, dev) if fence else None
    fence_step = [None] * Bn
    last_chk = 0
    step = 0
    try:
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
                    "logprob_sum": float(lps_c[r, :n].sum()), "steps": step + 1, "fence_step": fence_step[r]})
    return out
