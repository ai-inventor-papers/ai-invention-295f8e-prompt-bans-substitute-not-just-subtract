#!/usr/bin/env python3
"""Displacement-targeted block-output edits (generalising exp17 hooks.make_edits to every site).

edit(h, l, idx, u, target, h_ref):  hs = h[:, idx].float();  coef = target - (hs - h_ref) . u;
                                    h[:, idx] = (hs + coef[..., None] * u).to(bf16)
so the displacement from the clean neutral twin ALONG u is exactly `target` at every hooked block and position
(no compounding across blocks: each block re-targets the total displacement), and components orthogonal to u are
left as they are. Computed in fp32, cast back to bf16. alpha = 0 (target 0) is the identity on the twin.

Prefill sites: S0/S4/S5/TOP5/ENG on the task-spec positions S, S1/S1E on R, S2/S2E on the condition span COND.
The S3 decode site lives in engine.sample (it needs the shadow rows of the same batch).
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


def apply_edit_tensor(h: torch.Tensor, idx: torch.Tensor, ul: torch.Tensor, target: torch.Tensor,
                      h_ref: torch.Tensor) -> torch.Tensor:
    """Pure-tensor version of one block's edit (used by the CPU unit tests)."""
    hs = h[:, idx].float()
    coef = target - (hs - h_ref) @ ul
    out = h.clone()
    out[:, idx] = (hs + coef[..., None] * ul).to(h.dtype)
    return out
