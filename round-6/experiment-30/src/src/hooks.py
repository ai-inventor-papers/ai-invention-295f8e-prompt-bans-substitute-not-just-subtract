#!/usr/bin/env python3
"""Displacement-targeted block-output edits (exp20 hooks.make_prefill_edits, unchanged maths).

edit(h, l, idx, u, target, h_ref):  hs = h[:, idx].float();  coef = target - (hs - h_ref) . u;
                                    h[:, idx] = (hs + coef[..., None] * u).to(bf16)
so the displacement from the clean neutral twin ALONG u is exactly `target` at every hooked block and position
(each block re-targets the total displacement, no compounding); components orthogonal to u are left as they are.
fp32 maths, cast back to bf16. alpha = 0 (target 0) is the identity on the twin.

`edit_batched` is the same formula for a batch of rows with one direction per row (coef[b, n] = target[b, n] -
(h[b, idx] - h_ref) . u_b); the CPU test checks it against make_prefill_edits and exp27's make_edits('RAND').
"""

from __future__ import annotations

from typing import Callable

import torch


def make_prefill_edits(blocks: list[int], idx: torch.Tensor, u: dict[int, torch.Tensor],
                       target: dict[int, torch.Tensor], h_ref: dict[int, torch.Tensor]
                       ) -> dict[int, Callable[[torch.Tensor], torch.Tensor]]:
    """idx: LongTensor of positions; u: {l: fp32 [D] unit}; target: {l: fp32 [len(idx)]};
    h_ref: {l: fp32 [len(idx), D]} (clean twin block outputs at idx)."""
    edits = {}
    for l in blocks:
        def f(h: torch.Tensor, l: int = l) -> torch.Tensor:
            hs = h[:, idx].float()                       # [1, n, D]
            ul = u[l]
            comp = (hs - h_ref[l]) @ ul                  # [1, n]
            coef = target[l] - comp
            new = hs + coef[..., None] * ul
            h = h.clone()
            h[:, idx] = new.to(h.dtype)
            return h
        edits[l] = f
    return edits


def edit_batched(h: torch.Tensor, idx: torch.Tensor, u: torch.Tensor, target: torch.Tensor,
                 h_ref: torch.Tensor) -> torch.Tensor:
    """h [B, T, D] (any dtype); u [B, D] fp32 units; target [B, n] fp32; h_ref [n, D] fp32."""
    hs = h[:, idx].float()                                   # [B, n, D]
    coef = target - torch.einsum("bnd,bd->bn", hs - h_ref[None], u)
    out = h.clone()
    out[:, idx] = (hs + coef[..., None] * u[:, None, :]).to(h.dtype)
    return out
