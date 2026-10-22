#!/usr/bin/env python3
"""Per-unit GPU context (ported from exp26 src/ctx5.py): clean twin prefills (captures for h_ref, the push unit and
displacement logging), edited arm prefills with realised-displacement records, random directions and push specs.

Push unit (plan S0): n[l, p] = r_Q(l) * ||h_twin[l, p]|| for l in 12..23 and p in S, r_Q from the in-plan table
(identical to exp23 results/qwen_ratio.json 'r_Q' medians). Edit (make_edits TARGET, prefill only):
h_S <- h_S + (alpha * n[l] - (h_S - h_twin[l]) . u) u, so the displacement from the clean twin along u is exactly
alpha * n[l, p] at every edited block and position (no compounding). Realised displacement against the twin:
  rel_err_l  = mean_p |(h_arm - h_twin)[l, p] . u - M_l[p]| / |M_l[p]|      (edited blocks)
  disp_smean = ||mean_{p in S} (h_arm - h_twin)[l, p]||                      (blocks 12-35)
  disp_R     = ||h_arm[l, R] - h_twin[l, R]||                                 (blocks 12-35, read position R = P - 1)
"""

from __future__ import annotations

from typing import Any

import numpy as np
import torch

from cfg6 import CAP_BLOCKS, D_MODEL, DIR_DIR, EDIT_BLOCKS, R_Q
from engine6 import prefill


def rand_dir(seed: int) -> np.ndarray:
    """u = normalise(PCG64(seed).standard_normal(4096)); saved on first use (directions/rand_<seed>.npy)."""
    p = DIR_DIR / f"rand_{seed}.npy"
    if p.exists():
        return np.load(p)
    x = np.random.Generator(np.random.PCG64(seed)).standard_normal(D_MODEL)
    v = (x / np.linalg.norm(x)).astype(np.float32)
    np.save(p, v)
    return v


def make_edits(a: int, b: int, U: dict[int, torch.Tensor], M: dict[int, torch.Tensor],
               h_ref: dict[int, torch.Tensor]):
    edits = {}
    for l in EDIT_BLOCKS:
        def f(h: torch.Tensor, l: int = l) -> torch.Tensor:
            hs = h[:, a:b].float()
            ul = U[l]
            comp = (hs - h_ref[l]) @ ul
            coef = M[l] - comp
            new = hs + coef[..., None] * ul
            h = h.clone()
            h[:, a:b] = new.to(h.dtype)
            return h
        edits[l] = f
    return edits


class UnitCtx:
    """prompts: {template_id: twin prompt row} of ONE unit (shared task-spec span)."""

    def __init__(self, model: Any, unit: str, prompts: dict[str, dict[str, Any]]):
        self.model, self.unit, self.pr = model, unit, prompts
        self.dev = model.device
        self.clean: dict[str, dict[str, Any]] = {}

    def _capture(self, a: int, b: int, P: int):
        cap: dict[str, dict[int, torch.Tensor]] = {"S": {}, "smean": {}, "R": {}}

        def mk(l):
            def g(h):
                hs = h[0, a:b].float()
                cap["S"][l] = hs.clone() if (l in EDIT_BLOCKS or l == CAP_BLOCKS[-1]) else None
                cap["smean"][l] = hs.mean(0)
                cap["R"][l] = h[0, P - 1].float().clone()
            return g
        return cap, {l: mk(l) for l in CAP_BLOCKS}

    def twin(self, w: str) -> dict[str, Any]:
        if w not in self.clean:
            p = self.pr[w]
            a, b, P = p["p1"], p["spec_end"], p["P"]
            cap, hooks = self._capture(a, b, P)
            pre = prefill(self.model, p["ids"], capture=hooks)
            n = torch.stack([R_Q[l] * cap["S"][l].norm(dim=-1) for l in EDIT_BLOCKS])
            self.clean[w] = {"pre": pre, "S": cap["S"], "smean": cap["smean"], "R": cap["R"], "a": a, "b": b,
                             "P": P, "prompt": p, "n": n}
        return self.clean[w]

    def push_spec(self, w: str, u: np.ndarray, alpha: float) -> dict[str, Any]:
        tw = self.twin(w)
        ut = torch.tensor(u, dtype=torch.float32, device=self.dev)
        return {"U": {l: ut for l in EDIT_BLOCKS}, "M": {l: alpha * tw["n"][j] for j, l in enumerate(EDIT_BLOCKS)}}

    def arm_prefill(self, w: str, spec: dict[str, Any] | None) -> tuple[dict[str, Any], dict[str, Any]]:
        tw = self.twin(w)
        if not spec:
            return tw["pre"], {}
        a, b, P = tw["a"], tw["b"], tw["P"]
        edits = make_edits(a, b, spec["U"], spec["M"], {l: tw["S"][l] for l in EDIT_BLOCKS})
        cap, hooks = self._capture(a, b, P)
        pre = prefill(self.model, tw["prompt"]["ids"], edits=edits, capture=hooks)
        rec: dict[str, Any] = {}
        relerr = {}
        for l in EDIT_BLOCKS:
            d = cap["S"][l] - tw["S"][l]
            comp = d @ spec["U"][l]
            tgt = spec["M"][l]
            relerr[l] = float(((comp - tgt).abs() / tgt.abs().clamp(min=1e-6)).mean())
        rec["rel_err_by_block"] = {l: round(v, 6) for l, v in relerr.items()}
        rec["rel_err_max"] = max(relerr.values())
        dl = torch.stack([cap["smean"][l] - tw["smean"][l] for l in CAP_BLOCKS])
        dR = torch.stack([cap["R"][l] - tw["R"][l] for l in CAP_BLOCKS])
        hn = torch.stack([tw["S"][l].norm(dim=-1).mean() for l in EDIT_BLOCKS])
        rec["disp_smean_norm"] = {l: round(float(dl[i].norm()), 4) for i, l in enumerate(CAP_BLOCKS)}
        rec["disp_R_norm"] = {l: round(float(dR[i].norm()), 4) for i, l in enumerate(CAP_BLOCKS)}
        rec["target_mean"] = float(torch.stack([spec["M"][l].abs().mean() for l in EDIT_BLOCKS]).mean())
        rec["target_ratio_to_h"] = float((torch.stack([spec["M"][l].abs().mean() for l in EDIT_BLOCKS]) / hn).mean())
        return pre, rec

    def release(self) -> None:
        self.clean.clear()
        torch.cuda.empty_cache()
