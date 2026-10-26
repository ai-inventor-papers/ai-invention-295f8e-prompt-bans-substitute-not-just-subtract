#!/usr/bin/env python3
"""Block-output edits of this artifact (all applied in the PROMPT PREFILL only, at the hooked blocks' outputs;
fp32 math, cast back to the model dtype). h_ref = the cached clean state of the RECIPIENT model for the same prompt;
D[l,p] = h_donor[l,p] - h_recipient[l,p] (base minus instruct for the forward transplant).

SETTO kinds (the hooked state is SET, so it is independent of the upstream state: nothing compounds):
  SET(lam):  h[l,p] <- h_ref[l,p] + lam * D[l,p]                               (transplant; lam = 1 -> donor state)
  MR(lam):   h[l,p] <- h_ref[l,p] + lam * ||D[l,p]|| * u_s                      (norm-matched random; one isotropic unit
                                                                                 u_s per sample, shared by all blocks
                                                                                 and positions)
  XT(lam):   h[l,p] <- h_ref[l,p] + lam * ||D_t[l,p]|| * unit(Dbar_partner[l])  (cross-task content control)
ALONG kinds (exp19 ADD/PN: displacement-targeted along a unit direction; orthogonal components left free):
  DS(alpha): h <- h + (alpha * n[l,p] - (h - h_ref) . d[l,p]) d[l,p],  d = D / ||D|| per (l,p)
  ISO(alpha): the same with one isotropic unit u_s per sample;  n[l,p] = ||h_instr[l,p]|| * r_Q(l) (ban-free unit)
  EC_RAND:   exp17 engine-check push: one fixed direction, exp17 ban unit n[l,p]
"""

from __future__ import annotations

from typing import Callable

import torch


def edits_setto(blocks: list[int], idx: torch.Tensor, targets: dict[int, torch.Tensor]
                ) -> dict[int, Callable[[torch.Tensor], torch.Tensor]]:
    """targets: {l: fp32 [len(idx), D]} -> h[:, idx] = target (batch-1 prefill)."""
    edits = {}
    for l in blocks:
        def f(h: torch.Tensor, l: int = l) -> torch.Tensor:
            h = h.clone()
            h[:, idx] = targets[l].to(h.dtype)[None]
            return h
        edits[l] = f
    return edits


def edits_along(blocks: list[int], idx: torch.Tensor, dirs: dict[int, torch.Tensor], tgt: dict[int, torch.Tensor],
                h_ref: dict[int, torch.Tensor]) -> dict[int, Callable[[torch.Tensor], torch.Tensor]]:
    """dirs: {l: fp32 [len(idx), D] unit rows or [D]}; tgt: {l: fp32 [len(idx)]}; h_ref: {l: fp32 [len(idx), D]}."""
    edits = {}
    for l in blocks:
        def f(h: torch.Tensor, l: int = l) -> torch.Tensor:
            hs = h[:, idx].float()                                  # [1, n, D]
            d = dirs[l] if dirs[l].dim() == 2 else dirs[l][None].expand(hs.shape[1], -1)
            comp = ((hs - h_ref[l][None]) * d[None]).sum(-1)        # [1, n]
            coef = tgt[l][None] - comp
            new = hs + coef[..., None] * d[None]
            h = h.clone()
            h[:, idx] = new.to(h.dtype)
            return h
        edits[l] = f
    return edits


def unit_rows(x: torch.Tensor, eps: float = 1e-8) -> torch.Tensor:
    return x / x.norm(dim=-1, keepdim=True).clamp(min=eps)
