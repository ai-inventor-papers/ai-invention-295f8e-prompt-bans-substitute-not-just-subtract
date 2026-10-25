#!/usr/bin/env python3
"""Per-unit GPU context: clean twin prefills (captures for h_ref, the ban-free unit and displacement logging), edited
arm prefills with realised-displacement records, random directions and push specs (ported from exp22 ctx4.py).

Ban-free unit (plan section 9; exp23 units.py PLAIN variant for Qwen): n[l, p] = r_Q(l) * ||h_twin_clean[l, p]||
for l in 12..23 and p in S, with r_Q(l) = the exp23 results/qwen_ratio.json 'r_Q' median at relative depth (l+1)/36
(np.interp over depth, clamped). Engine-check arms use exp17's own ban unit (directions/norms_<task>.npy).

Edit (exp22 make_edits_v4 TARGET): h_S <- h_S + (M[l] - (h_S - h_ref[l]) . u) u, M[l] = alpha * n[l]; the displacement
from the clean twin along u is exactly alpha * n[l, p] at every edited block and position (no compounding).
Realised displacement of an edited prefill against the template-matched clean twin:
  rel_err_l  = mean_p |(h_arm - h_twin)[l, p] . u - M_l[p]| / |M_l[p]|      (edited blocks)
  disp_smean = ||mean_{p in S} (h_arm - h_twin)[l, p]||                      (blocks 12-35)
  disp_R     = ||h_arm[l, R] - h_twin[l, R]||                                 (blocks 12-35, read position R = P - 1)
"""

from __future__ import annotations

from typing import Any

import numpy as np
import torch

from cfg5 import CAP_BLOCKS, CACHE_DIR, D_MODEL, DIR_DIR, EDIT_BLOCKS, N_LAYERS, VENDOR, read_json
from engine5 import prefill

QWEN_RATIO = VENDOR / "exp23" / "qwen_ratio.json"
E17 = VENDOR / "exp17"


def rq_table(key: str = "r_Q") -> tuple[np.ndarray, np.ndarray]:
    q = read_json(QWEN_RATIO)[key]
    d = np.array([v["depth"] for v in q.values()])
    r = np.array([v["median"] for v in q.values()])
    o = np.argsort(d)
    return d[o], r[o]


def r_at(l: int, key: str = "r_Q", n_layers: int = N_LAYERS) -> float:
    d, r = rq_table(key)
    return float(np.interp((l + 1) / n_layers, d, r))


def rand_dir(seed: int) -> np.ndarray:
    """exp17 _RandDirs construction: PCG64(seed).standard_normal(4096), normalised; saved on first use."""
    p = DIR_DIR / f"rand_{seed}.npy"
    if p.exists():
        return np.load(p)
    src = E17 / "directions" / f"rand_{seed}.npy"
    if src.exists():
        v = np.load(src)
    else:
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
    """prompts: {template_id: prompt row} for ONE (unit, kind) family sharing the spec span."""

    def __init__(self, model: Any, unit: str, prompts: dict[str, dict[str, Any]], unit_kind: str = "ban_free"):
        self.model, self.unit, self.pr = model, unit, prompts
        self.dev = model.device
        self.unit_kind = unit_kind
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
            n = self.unit_n(w, cap["S"])
            self.clean[w] = {"pre": pre, "S": cap["S"], "smean": cap["smean"], "R": cap["R"], "a": a, "b": b,
                             "P": P, "prompt": p, "n": n}
        return self.clean[w]

    def unit_n(self, w: str, S: dict[int, torch.Tensor]) -> torch.Tensor:
        """[12, |S|] fp32 push norms for template w."""
        if self.unit_kind == "ban_free":
            n = torch.stack([r_at(l, "r_Q") * S[l].norm(dim=-1) for l in EDIT_BLOCKS])
            d = CACHE_DIR / self.unit
            d.mkdir(parents=True, exist_ok=True)
            fp = d / f"n_{w}.npy"
            if not fp.exists():
                np.save(fp, n.cpu().numpy().astype(np.float16))
            return n
        task = self.unit_kind.split(":", 1)[1]   # 'exp17:<task>' -> exp17's own FP8 ban unit (engine check)
        return torch.tensor(np.load(E17 / "directions" / f"norms_{task}.npy").astype(np.float32), device=self.dev)

    def push_spec(self, w: str, u: np.ndarray, alpha: float) -> dict[str, Any]:
        tw = self.twin(w)
        ut = torch.tensor(u, dtype=torch.float32, device=self.dev)
        return {"kind": "TARGET", "U": {l: ut for l in EDIT_BLOCKS},
                "M": {l: alpha * tw["n"][j] for j, l in enumerate(EDIT_BLOCKS)}}

    def arm_prefill(self, w: str, spec: dict[str, Any] | None) -> tuple[dict[str, Any], dict[str, Any]]:
        tw = self.twin(w)
        if not spec or spec.get("kind") is None:
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
        rec["rel_err_max"] = max(relerr.values())
        dl = torch.stack([cap["smean"][l] - tw["smean"][l] for l in CAP_BLOCKS])
        dR = torch.stack([cap["R"][l] - tw["R"][l] for l in CAP_BLOCKS])
        rec["disp_smean_norm"] = {l: round(float(dl[i].norm()), 4) for i, l in enumerate(CAP_BLOCKS)}
        rec["disp_R_norm"] = {l: round(float(dR[i].norm()), 4) for i, l in enumerate(CAP_BLOCKS)}
        last = CAP_BLOCKS[-1]
        rec["disp_pos_norm_35"] = float((cap["S"][last] - tw["S"][last]).norm(dim=-1).mean())
        rec["target_mean"] = float(torch.stack([spec["M"][l].abs().mean() for l in EDIT_BLOCKS]).mean())
        return pre, rec

    def release(self) -> None:
        self.clean.clear()
        torch.cuda.empty_cache()
