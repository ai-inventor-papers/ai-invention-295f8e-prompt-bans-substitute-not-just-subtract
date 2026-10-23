#!/usr/bin/env python3
"""Displacement-targeted block-output edits applied during the prompt PREFILL only (port of iteration-3 exp17
hooks.py to batched rows, each with its own unit direction and dose).

For every row b with alpha_b > 0, at every block l in the band and every spec position p in [a, b):
    delta = h[b, p] - h_ref[l, p]          (h_ref = the clean twin states of the same (task, template))
    coef  = alpha_b * n[l, p] - delta . u_b
    h[b, p] <- h[b, p] + coef * u_b
so the displacement from the clean twin along u_b is exactly alpha_b * n[l, p] at every hooked block (no
compounding across blocks). Rows with alpha_b == 0 are never touched. Edits are computed in fp32 and cast back.
"""

from __future__ import annotations

import contextlib
from typing import Any, Callable, Iterator

import torch


def _out_tensor(out: Any) -> torch.Tensor:
    return out[0] if isinstance(out, tuple) else out


def _replace_out(out: Any, h: torch.Tensor) -> Any:
    if isinstance(out, tuple):
        return (h,) + tuple(out[1:])
    return h


@contextlib.contextmanager
def block_hooks(layers: Any, edits: dict[int, Callable[[torch.Tensor], torch.Tensor]] | None = None,
                capture: dict[int, Callable[[torch.Tensor], None]] | None = None) -> Iterator[None]:
    """edits: {block: f(h) -> h'} applied to the block OUTPUT; capture: {block: g(h)} called after the edit."""
    hs = []
    edits = edits or {}
    capture = capture or {}
    for l in sorted(set(edits) | set(capture)):
        def hook(mod, inp, out, l=l):
            h = _out_tensor(out)
            if l in edits:
                h = edits[l](h)
                out = _replace_out(out, h)
            if l in capture:
                capture[l](h)
            return out
        hs.append(layers[l].register_forward_hook(hook))
    try:
        yield
    finally:
        for h in hs:
            h.remove()


def make_push_edits(band: list[int], a: int, b: int, U: torch.Tensor, alpha: torch.Tensor,
                    n: dict[int, torch.Tensor], h_ref: dict[int, torch.Tensor],
                    log: dict[int, list[float]] | None = None) -> dict[int, Callable[[torch.Tensor], torch.Tensor]]:
    """U: [B, D] fp32 unit rows (zeros where alpha == 0); alpha: [B] fp32; n: {l: [S]} fp32;
    h_ref: {l: [S, D]} (shared) or {l: [B, S, D]} (per row) fp32 clean twin states at positions [a, b)."""
    rows = torch.nonzero(alpha > 0).flatten()
    edits: dict[int, Callable[[torch.Tensor], torch.Tensor]] = {}
    if rows.numel() == 0:
        return edits
    Ur = U[rows]                     # [r, D]
    ar = alpha[rows]                 # [r]
    for l in band:
        def f(h: torch.Tensor, l: int = l) -> torch.Tensor:
            hs = h[rows, a:b].float()                    # [r, S, D]
            ref = h_ref[l] if h_ref[l].dim() == 2 else h_ref[l][rows]
            comp = ((hs - ref) * Ur[:, None, :]).sum(-1)  # [r, S]
            coef = ar[:, None] * n[l][None, :] - comp
            new = hs + coef[..., None] * Ur[:, None, :]
            if log is not None:
                log.setdefault(l, []).append(float(coef.abs().mean()))
            h = h.clone()
            h[rows, a:b] = new.to(h.dtype)
            return h
        edits[l] = f
    return edits
