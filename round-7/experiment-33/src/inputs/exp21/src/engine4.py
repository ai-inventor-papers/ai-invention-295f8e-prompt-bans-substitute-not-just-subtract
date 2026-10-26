#!/usr/bin/env python3
"""Extension of exp17 engine.sample() (engine.py is kept byte-identical): per-row temperature, top-k, min-p and token
coupling, with the same KV preallocation, prune=False batch shape and stop rules.

Per row r: scaled = logits / T_r; top-k (k_r > 0) masks scaled < k-th largest to -inf; probs = softmax(scaled);
min-p (m_r > 0) keeps probs >= m_r * max(probs) and renormalises; then
- coupling 'invcdf' (exp8/exp17): token = first index whose float64 CDF (vocabulary order) >= u[r, step];
- coupling 'gumbel': q = Exp(1) of vocabulary size from the row's own CUDA generator (seeded per slot, one draw per
  step), token = argmax(probs / q) -- the exponential race, i.e. Gumbel-max with step-indexed noise (vLLM's coupling).
With T_r = 1, no top-k and no min-p, an invcdf row is computed exactly as exp17's sample() computes it.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import torch

from cfg import ENDOFTEXT, IM_END
from engine import _inverse_cdf, clear_act_cache, prealloc_cache


def mask_probs(logits: torch.Tensor, Tv: torch.Tensor, kk: torch.Tensor, mp: torch.Tensor,
               any_topk: bool, any_minp: bool, kmax: int) -> torch.Tensor:
    scaled = logits / Tv
    if any_topk:
        kth = torch.topk(scaled, kmax, dim=-1).values.gather(-1, (kk.clamp(min=1) - 1)[:, None])
        scaled = scaled.masked_fill((kk[:, None] > 0) & (scaled < kth), float("-inf"))
    probs = torch.softmax(scaled, dim=-1)
    if any_minp:
        keep = probs >= mp * probs.max(dim=-1, keepdim=True).values
        probs = torch.where(keep, probs, torch.zeros_like(probs))
        probs = probs / probs.sum(dim=-1, keepdim=True)
    return probs


def gumbel_pick(probs: torch.Tensor, gens: list[torch.Generator]) -> torch.Tensor:
    out = torch.empty(probs.shape[0], dtype=torch.long, device=probs.device)
    for i, g in enumerate(gens):
        q = torch.empty(probs.shape[1], dtype=probs.dtype, device=probs.device).exponential_(generator=g)
        out[i] = torch.argmax(probs[i] / q)
    return out


@torch.no_grad()
def sample4(model: Any, groups: list[dict[str, Any]], max_new: int, check_every: int = 8,
            force_len: bool = False, count_decode_hooks: dict[str, int] | None = None) -> list[dict[str, Any]]:
    """groups: [{'pre': prefill dict, 'rows': [{'u': ndarray|None, 'T': float, 'top_k': int, 'min_p': float,
    'coupling': 'invcdf'|'gumbel', 'gseed': int|None}, ...]}]. All groups share the prompt length P."""
    P = groups[0]["pre"]["P"]
    assert all(g["pre"]["P"] == P for g in groups), "all rows of a batch must share the prompt length"
    dev = model.device
    n_layers = len(groups[0]["pre"]["kv"])
    kv = []
    for l in range(n_layers):
        Ks, Vs = [], []
        for g in groups:
            K, V = g["pre"]["kv"][l]
            Ks.append(K.expand(len(g["rows"]), -1, -1, -1))
            Vs.append(V.expand(len(g["rows"]), -1, -1, -1))
        kv.append((torch.cat(Ks, 0), torch.cat(Vs, 0)))
    cache = prealloc_cache(kv, P + max_new + 1)
    del kv
    rows = [r for g in groups for r in g["rows"]]
    B = len(rows)
    couplings = {r["coupling"] for r in rows}
    assert couplings <= {"invcdf", "gumbel"} and len(couplings) == 1, "one coupling per batch"
    coupling = couplings.pop()
    if coupling == "invcdf":
        U = torch.tensor(np.stack([r["u"][:max_new] for r in rows]), dtype=torch.float64, device=dev)
        gens = []
    else:
        U = None
        gens = []
        for r in rows:
            g = torch.Generator(device=dev)
            g.manual_seed(int(r["gseed"]) % (2 ** 63))
            gens.append(g)
    Tv = torch.tensor([float(r["T"]) for r in rows], dtype=torch.float64, device=dev)[:, None]
    kk = torch.tensor([int(r.get("top_k") or 0) for r in rows], dtype=torch.long, device=dev)
    mp = torch.tensor([float(r.get("min_p") or 0.0) for r in rows], dtype=torch.float64, device=dev)[:, None]
    any_topk = bool((kk > 0).any().item())
    kmax = int(kk.max().item()) if any_topk else 0
    any_minp = bool((mp > 0).any().item())
    logits = torch.cat([g["pre"]["r_logits"][None].expand(len(g["rows"]), -1) for g in groups], 0).double()
    toks = torch.full((B, max_new), -1, dtype=torch.long, device=dev)
    lps = torch.zeros((B, max_new), dtype=torch.float64, device=dev)
    done = torch.zeros(B, dtype=torch.bool, device=dev)
    ended = torch.zeros(B, dtype=torch.bool, device=dev)
    im_end_t = torch.full((B,), IM_END, dtype=torch.long, device=dev)
    step = 0
    try:
        while True:
            probs = mask_probs(logits, Tv, kk, mp, any_topk, any_minp, kmax)
            nxt = _inverse_cdf(probs, U[:, step]) if coupling == "invcdf" else gumbel_pick(probs, gens)
            plp = torch.log(probs.gather(-1, nxt[:, None])[:, 0])
            live = ~done
            toks[:, step] = torch.where(live, nxt, toks[:, step])
            lps[:, step] = torch.where(live, plp, lps[:, step])
            is_end = (nxt == IM_END) | (nxt == ENDOFTEXT)
            if force_len:
                is_end = torch.zeros_like(is_end)
            ended |= live & is_end
            done |= is_end
            if step + 1 >= max_new:
                break
            if (step + 1) % check_every == 0 and bool(done.all().item()):
                break
            feed = torch.where(done, im_end_t, nxt)[:, None]
            pos = torch.full((B, 1), P + step, device=dev, dtype=torch.long)
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
    for r in range(B):
        row = toks_c[r]
        n = int((row >= 0).sum())
        out.append({"token_ids": [int(t) for t in row[:n]], "finish_reason": "stop" if ended_c[r] else "length",
                    "n_tokens": n, "logprob_sum": float(lps_c[r, :n].sum()), "steps": step + 1})
    return out
