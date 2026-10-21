#!/usr/bin/env python3
"""make_edits_v4: block-output edits at the task-spec positions S = [a, b) of EDIT_BLOCKS during the prompt prefill.

TARGET: h_S <- h_S + (M[l] - (h_S - h_ref[l]) . U[l]) U[l]   -- the displacement from the clean twin along U[l] is
        exactly M[l][p] at every edited block (no compounding); with U[l] = u and M = alpha * n this is exp17 RAND,
        written with the same fp32 operations in the same order.
CLAMP:  TARGET, then h_S <- h_S - ((h_S - h_ref[l]) Q_l) Q_l^T, so the displacement's component in the plan subspace
        P_t (orthonormal basis Q_l, [D, k]) is zero at that block.
All edits are computed in fp32 and cast back to the block's dtype. `log` collects the mean |coefficient| per block.
"""

from __future__ import annotations

from typing import Any, Callable

import numpy as np
import torch

from cfg4 import EDIT_BLOCKS


def make_edits_v4(kind: str, a: int, b: int, U: dict[int, torch.Tensor], M: dict[int, torch.Tensor],
                  h_ref: dict[int, torch.Tensor], Q: dict[int, torch.Tensor] | None = None,
                  log: dict[int, list[float]] | None = None) -> dict[int, Callable[[torch.Tensor], torch.Tensor]]:
    assert kind in ("TARGET", "CLAMP"), kind
    edits = {}
    for l in EDIT_BLOCKS:
        def f(h: torch.Tensor, l: int = l) -> torch.Tensor:
            hs = h[:, a:b].float()
            ul = U[l]
            comp = (hs - h_ref[l]) @ ul
            coef = M[l] - comp
            new = hs + coef[..., None] * ul
            if kind == "CLAMP":
                Ql = Q[l]
                dproj = (new - h_ref[l]) @ Ql
                new = new - dproj @ Ql.T
            if log is not None:
                log.setdefault(l, []).append(float(coef.abs().mean()))
            h = h.clone()
            h[:, a:b] = new.to(h.dtype)
            return h
        edits[l] = f
    return edits


def to_dev(d: dict[int, Any], device: torch.device) -> dict[int, torch.Tensor]:
    return {int(k): torch.as_tensor(np.asarray(v), dtype=torch.float32, device=device) for k, v in d.items()}


def unit(x: np.ndarray) -> np.ndarray:
    return (x / max(float(np.linalg.norm(x)), 1e-12)).astype(np.float32)
