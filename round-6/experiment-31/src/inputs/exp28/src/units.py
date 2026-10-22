#!/usr/bin/env python3
"""Ban-free push unit.

PRIMARY (deviation D3, decided before commit #1 and before any ban prompt): the outlier-excluded unit
    n[l, p] = r_Q,ox(d_l) * ||h_ref[l, p] with its 5 largest-|h| channels zeroed||,
with r_Q,ox(d) = median over (task, w, p) of ||Qwen ban displacement|| / ||Qwen twin state with its 5 largest
channels zeroed|| (results/qwen_ratio.json, key r_Q_ox), interpolated linearly over Qwen relative depths (l + 1)/36
and clamped at the ends, d_l = (l + 1) / 34.
COMMITTED-PLAN UNIT (reported as a diagnostic only): n_plain[l, p] = r_Q(d_l) * ||h_ref[l, p]||. In gemma-3-4b-it the
top-5 channels carry 99% of ||h||^2 at spec positions (Qwen3-8B: 40%), so n_plain is about 8x larger than the Qwen
push relative to the non-massive residual; the calibration probe (results/unit_probe.json) showed that alpha 1 under
n_plain erases the task specification (off-task programs and prose), i.e. the escape screen would be degenerate.
"""

from __future__ import annotations

import numpy as np
import torch

from cfg import BAND, E23, N_LAYERS, N_MASSIVE, read_json




def rq_table(key: str = "r_Q_ox") -> tuple[np.ndarray, np.ndarray]:
    q = read_json(E23 / "results" / "qwen_ratio.json")[key]
    d = np.array([v["depth"] for v in q.values()])
    r = np.array([v["median"] for v in q.values()])
    o = np.argsort(d)
    return d[o], r[o]


def r_at(l: int, key: str = "r_Q_ox", n_layers: int = N_LAYERS) -> float:
    d, r = rq_table(key)
    return float(np.interp((l + 1) / n_layers, d, r))  # np.interp clamps outside [d0, d_end]


def ox_norm(h: torch.Tensor) -> torch.Tensor:
    """||h|| with the N_MASSIVE largest-|h| channels of each position zeroed. h: [..., D]."""
    sq = h.float() ** 2
    return (sq.sum(-1) - sq.topk(N_MASSIVE, dim=-1).values.sum(-1)).clamp(min=1e-12).sqrt()


def unit_n(h_ref_S: dict[int, torch.Tensor], kind: str = "ox") -> dict[int, torch.Tensor]:
    """h_ref_S: {l: [S, D] fp32} clean twin states -> {l: [S] fp32} push norms for the band blocks."""
    if kind == "plain":
        return {l: r_at(l, "r_Q") * h_ref_S[l].norm(dim=-1) for l in BAND}
    return {l: r_at(l, "r_Q_ox") * ox_norm(h_ref_S[l]) for l in BAND}
