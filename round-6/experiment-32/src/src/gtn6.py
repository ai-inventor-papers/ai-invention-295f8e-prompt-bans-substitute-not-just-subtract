#!/usr/bin/env python3
"""GTN arm (generated-token noise, the exp20 S3 site): during the first 32 decode steps (input = generated tokens
1-32) every pushed row is displaced at blocks 12-23 along its own fresh isotropic direction u so that its component
along u, measured from a TEACHER-FORCED SHADOW ROW of the same batch (same tokens, no edit), equals alpha x n with
n = ||h_shadow[l]|| x r_Q(l) (the ban-free unit from the shadow-row norms). Edit rule (exp20 hooks.py, exp19 TARGET):
h_p <- h_p + (alpha n - (h_p - h_s) . u) u, fp32, cast back to bf16. Batch = m pushed rows + m shadow rows (B = 20),
sampled with the exp8 inverse-CDF CRN sampler (pushed rows only; shadow j mirrors pushed j's tokens)."""

from __future__ import annotations

from typing import Any

import numpy as np
import torch

from cfg5 import EDIT_BLOCKS, ENDOFTEXT, IM_END, MAX_NEW
from engine5 import _inverse_cdf, _out_tensor, _replace_out, fence_closed, layers, prealloc_cache, tick_mask

N_GTN_STEPS = 32


@torch.no_grad()
def sample_gtn(model: Any, tok: Any, pre: dict[str, Any], us: list[np.ndarray], dirs: list[np.ndarray],
               alpha: float, rq: dict[int, float], fence: str = "bench", max_new: int = MAX_NEW,
               temperature: float = 1.0, check_every: int = 8) -> list[dict[str, Any]]:
    P = pre["P"]
    m = len(us)
    Bn = 2 * m
    dev = model.device
    kv = [(K.expand(Bn, -1, -1, -1).contiguous(), V.expand(Bn, -1, -1, -1).contiguous()) for K, V in pre["kv"]]
    cache = prealloc_cache(kv, P + max_new + 1)
    del kv
    U = torch.tensor(np.stack([u[:max_new] for u in us]), dtype=torch.float64, device=dev)
    D = torch.tensor(np.stack(dirs), dtype=torch.float32, device=dev)            # [m, d]
    logits = pre["r_logits"][None].expand(m, -1).double()
    toks = torch.full((m, max_new), -1, dtype=torch.long, device=dev)
    lps = torch.zeros((m, max_new), dtype=torch.float64, device=dev)
    done = torch.zeros(m, dtype=torch.bool, device=dev)
    ended = torch.zeros(m, dtype=torch.bool, device=dev)
    im_end_t = torch.full((m,), IM_END, dtype=torch.long, device=dev)
    tm = tick_mask(tok, dev)
    fence_step: list[int | None] = [None] * m
    state = {"active": False}
    rel_err: list[float] = []
    disp: list[float] = []
    tgt: list[float] = []

    def mk(l: int):
        r = float(rq[l])

        def hook(mod, inp, out):
            if not state["active"]:
                return out
            h = _out_tensor(out)
            hp = h[:m, -1].float()
            hs = h[m:, -1].float()
            n = hs.norm(dim=-1) * r
            comp = ((hp - hs) * D).sum(-1)
            target = alpha * n
            new = hp + (target - comp)[:, None] * D
            h = h.clone()
            h[:m, -1] = new.to(h.dtype)
            realised = ((h[:m, -1].float() - hs) * D).sum(-1)
            rel_err.append(float(((realised - target).abs() / target.abs().clamp(min=1e-6)).max()))
            disp.append(float((h[:m, -1].float() - hs).norm(dim=-1).mean()))
            tgt.append(float(target.mean()))
            return _replace_out(out, h)
        return hook

    hs_ = [layers(model)[l].register_forward_hook(mk(l)) for l in EDIT_BLOCKS]
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
            f = torch.where(done, im_end_t, nxt)
            feed = torch.cat([f, f], 0)[:, None]                 # shadow row j is fed pushed row j's token
            pos = torch.full((Bn, 1), P + step, device=dev, dtype=torch.long)
            state["active"] = step < N_GTN_STEPS                  # input = generated token step + 1 (1..32)
            h = model.model(input_ids=feed, past_key_values=cache, position_ids=pos, use_cache=True).last_hidden_state
            logits = model.lm_head(h[:m, -1]).double()
            step += 1
    finally:
        for hh in hs_:
            hh.remove()
        state["active"] = False
    del cache
    toks_c = toks.cpu().numpy()
    lps_c = lps.cpu().numpy()
    ended_c = ended.cpu().numpy()
    out = []
    rec = {"gtn_rel_err_max": max(rel_err) if rel_err else None,
           "gtn_disp_mean": float(np.mean(disp)) if disp else None,
           "gtn_target_mean": float(np.mean(tgt)) if tgt else None, "gtn_steps_edited": min(step, N_GTN_STEPS)}
    for r in range(m):
        row = toks_c[r]
        n = int((row >= 0).sum())
        fr = "stop" if ended_c[r] else ("fence" if fence_step[r] is not None else "length")
        out.append({"token_ids": [int(t) for t in row[:n]], "finish_reason": fr, "n_tokens": n,
                    "logprob_sum": float(lps_c[r, :n].sum()), "steps": step + 1, "fence_step": fence_step[r], **rec})
    return out
