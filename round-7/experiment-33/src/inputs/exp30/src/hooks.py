#!/usr/bin/env python3
"""S3: block-output edits applied during the prompt PREFILL only (task-spec positions S, blocks 12-23).

ADD / RAND (displacement-targeted): delta = h - h_twin_clean; h <- h + (alpha * n[l,p] - delta . u_l) u_l, so the
    displacement from the clean neutral twin along u_l is exactly alpha * n[l,p] at every hooked block (no compounding).
SUB_plain:  h <- h - (h . vhat_l) vhat_l                         (Arditi projection-out, on the BAN prompt)
SUB_affine: h <- h - ((h - h_twin_clean) . vhat_l) vhat_l        (twin-anchored; removes only the ban's excess)
SUB_rand:   h <- h - |h . vhat_l| r                              (random-direction edit of SUB_plain's norm)
All edits are computed in fp32 and cast back to bf16. Head mean-ablation masks for C2f live here too.
"""

from __future__ import annotations

from typing import Any, Callable

import numpy as np
import torch

from cfg import HEAD_DIM, N_HEADS, V_BLOCKS


def make_edits(kind: str, a: int, b: int, u: dict[int, torch.Tensor] | None, n: dict[int, torch.Tensor] | None,
               h_ref: dict[int, torch.Tensor] | None, alpha: float = 0.0, r: torch.Tensor | None = None,
               log: dict[int, list[float]] | None = None) -> dict[int, Callable[[torch.Tensor], torch.Tensor]]:
    """Edits for positions [a, b) at V_BLOCKS. u/vhat: {l: [D] fp32 unit}; n: {l: [b-a] fp32}; h_ref: {l: [b-a, D]}."""
    edits = {}
    for l in V_BLOCKS:
        def f(h: torch.Tensor, l: int = l) -> torch.Tensor:
            hs = h[:, a:b].float()
            if kind in ("ADD", "RAND"):
                ul = u[l]
                comp = (hs - h_ref[l]) @ ul                       # [1, |S|]
                coef = alpha * n[l] - comp
                new = hs + coef[..., None] * ul
                edit = coef.abs()
            elif kind == "SUB_plain":
                vl = u[l]
                proj = hs @ vl
                new = hs - proj[..., None] * vl
                edit = proj.abs()
            elif kind == "SUB_affine":
                vl = u[l]
                proj = (hs - h_ref[l]) @ vl
                new = hs - proj[..., None] * vl
                edit = proj.abs()
            elif kind == "SUB_rand":
                vl = u[l]
                proj = (hs @ vl).abs()
                new = hs - proj[..., None] * r
                edit = proj
            else:
                raise ValueError(kind)
            if log is not None:
                log.setdefault(l, []).append(float(edit.mean()))
            h = h.clone()
            h[:, a:b] = new.to(h.dtype)
            return h
        edits[l] = f
    return edits


def head_sets(seeds: tuple[int, ...]) -> dict[str, list[tuple[int, int]]]:
    """Layer-matched random head sets: 1 head from block 21 minus H17, 2 from block 26 minus {H21, H25}."""
    out = {}
    for s in seeds:
        rng = np.random.default_rng(s)
        h21 = [h for h in range(N_HEADS) if h != 17]
        h26 = [h for h in range(N_HEADS) if h not in (21, 25)]
        a = int(rng.choice(h21))
        bb = sorted(int(x) for x in rng.choice(h26, size=2, replace=False))
        out[f"rand{s}"] = [(21, a), (26, bb[0]), (26, bb[1])]
    return out


def head_masks(row_sets: list[list[tuple[int, int]]], device: torch.device) -> dict[int, torch.Tensor]:
    """row_sets[i] = heads ablated in batch row i -> {block: bool [B, 4096]} over o_proj-input columns."""
    blocks = sorted({l for s in row_sets for (l, _) in s})
    masks = {}
    for l in blocks:
        m = torch.zeros(len(row_sets), N_HEADS * HEAD_DIM, dtype=torch.bool, device=device)
        for i, s in enumerate(row_sets):
            for (ll, h) in s:
                if ll == l:
                    m[i, h * HEAD_DIM:(h + 1) * HEAD_DIM] = True
        masks[l] = m
    return masks


def to_dev(d: dict[int, Any], device: torch.device) -> dict[int, torch.Tensor]:
    return {int(k): torch.as_tensor(v, dtype=torch.float32, device=device) for k, v in d.items()}
