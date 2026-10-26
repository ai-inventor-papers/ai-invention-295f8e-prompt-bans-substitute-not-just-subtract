#!/usr/bin/env python3
"""S7/S8 machinery: feature selection (input score = Cohen's d on forced-prompt contrasts; output score = first-order
attribution patching of the fork readout y), live prefill-only edits, and the matched-norm controls.

Edit kinds (all at one block output l, at the site positions, prefill only, computed live from the clean h because
nothing upstream of block l is edited):
  FEAT : f = SAE(h); dh = lam * sum_{i in S} (t_i - f_i) W_dec[i]                       (error-preserving clamp)
  DiM  : dh = n(p) * dim_hat         with dim_hat = unit(mu_forced_target - mu_forced_other), massive channels 0
  RANDF: dh = n(p) * unit(sum_{i in R} s_i W_dec[i]), R random latents active in >= 5% of tokens, random signs
  ISO  : dh = n(p) * u, u isotropic (seeded) with massive channels 0
n(p) = the realised norm of the matched FEAT edit at position p with the 5 massive channels excluded (the 'ox' norm
of exp23, on the fixed massive-channel set M of the layer), so every control moves the non-massive residual exactly as
far as the FEAT edit does, position by position.
"""

from __future__ import annotations

from typing import Any, Callable

import numpy as np
import torch

from cfg import D_MODEL, N_MASSIVE, stable_seed


def massive_channels(states: torch.Tensor) -> torch.Tensor:
    """states [N, D] -> the N_MASSIVE channels with the largest mean |h|."""
    return states.float().abs().mean(0).topk(N_MASSIVE).indices


def ox_mask(M: torch.Tensor, device: str = "cuda") -> torch.Tensor:
    m = torch.ones(D_MODEL, device=device)
    m[M.to(device)] = 0.0
    return m


def unit_masked(v: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    v = v.float().to(mask.device) * mask
    return v / v.norm().clamp(min=1e-12)


def cohens_d(Xa: torch.Tensor, Xb: torch.Tensor) -> torch.Tensor:
    ma, mb = Xa.mean(0), Xb.mean(0)
    va = Xa.var(0, unbiased=True) if Xa.shape[0] > 1 else torch.zeros_like(ma)
    vb = Xb.var(0, unbiased=True) if Xb.shape[0] > 1 else torch.zeros_like(mb)
    na, nb = Xa.shape[0], Xb.shape[0]
    sp = (((na - 1) * va + (nb - 1) * vb) / max(na + nb - 2, 1)).sqrt()
    return (ma - mb) / sp.clamp(min=1e-3)


def top_by_d(Xa: torch.Tensor, Xb: torch.Tensor, k: int, active_frac: float = 0.05) -> dict[str, Any]:
    X = torch.cat([Xa, Xb])
    active = (X > 0).float().mean(0) >= active_frac
    d = cohens_d(Xa.float(), Xb.float())
    d_m = torch.where(active, d.abs(), torch.full_like(d, -1.0))
    idx = d_m.topk(k).indices
    return {"idx": idx.tolist(), "d": d[idx].tolist(), "n_active": int(active.sum())}


def top_by_attr(S: torch.Tensor, k: int, consist: float = 0.8, min_frac: float = 0.05) -> dict[str, Any]:
    """S [V, F] per-variant attribution scores -> top-k sign-consistent latents by |mean|."""
    mean = S.mean(0)
    nz = (S != 0).float()
    frac_nz = nz.mean(0)
    same = ((torch.sign(S) == torch.sign(mean)[None]) & (S != 0)).float().sum(0) / nz.sum(0).clamp(min=1)
    ok = (frac_nz >= min_frac) & (same >= consist)
    m = torch.where(ok, mean.abs(), torch.full_like(mean, -1.0))
    idx = m.topk(k).indices
    return {"idx": idx.tolist(), "s": mean[idx].tolist(), "consistency": same[idx].tolist(), "n_ok": int(ok.sum())}


class EditSpec:
    """One row's edit at one layer. kind in FEAT/DiM/RANDF/ISO. Positions are absolute indices in the prompt."""

    def __init__(self, kind: str, layer: int, pos: list[int], sae: Any, lat: list[int] | None = None,
                 target: torch.Tensor | None = None, lam: float = 1.0, direction: torch.Tensor | None = None,
                 match: dict[str, Any] | None = None, mask: torch.Tensor | None = None):
        self.kind, self.layer, self.lam = kind, layer, lam
        self.pos = torch.tensor(pos, device="cuda", dtype=torch.long)
        self.sae = sae
        self.lat = torch.tensor(lat, device="cuda", dtype=torch.long) if lat is not None else None
        self.target = target.to("cuda").float() if target is not None else None   # [S', k] or [k]
        self.direction = direction.to("cuda").float() if direction is not None else None
        self.match = match            # {'lat', 'target', 'lam'} of the matched FEAT edit (controls)
        self.mask = mask.to("cuda") if mask is not None else None
        self.log: dict[str, float] = {}

    @staticmethod
    def feat_dh(sae: Any, hs: torch.Tensor, lat: torch.Tensor, target: torch.Tensor, lam: float) -> torch.Tensor:
        pre = hs @ sae.W_enc[:, lat] + sae.b_enc[lat]
        f = pre * (pre > sae.threshold[lat])
        t = target if target.dim() == 2 else target[None].expand_as(f)
        return lam * (t - f) @ sae.W_dec[lat]

    def dh(self, hs: torch.Tensor) -> torch.Tensor:
        """hs [S', D] fp32 clean states at the site -> dh [S', D]."""
        if self.kind == "FEAT":
            d = self.feat_dh(self.sae, hs, self.lat, self.target, self.lam)
        else:
            m = self.match
            dm = self.feat_dh(self.sae, hs, torch.tensor(m["lat"], device="cuda"), m["target"].to("cuda").float(),
                              m["lam"])
            n = (dm * self.mask).norm(dim=-1)                      # [S'] ox norm of the matched FEAT edit
            d = n[:, None] * self.direction[None]
        self.log = {"ox_norm_mean": float((d * (self.mask if self.mask is not None else 1)).norm(dim=-1).mean()),
                    "norm_mean": float(d.norm(dim=-1).mean())}
        return d


def live_edits(row_specs: list[list[EditSpec] | None]) -> dict[int, Callable[[torch.Tensor], torch.Tensor]]:
    by_layer: dict[int, list[tuple[int, EditSpec]]] = {}
    for r, specs in enumerate(row_specs):
        for s in specs or []:
            by_layer.setdefault(s.layer, []).append((r, s))
    edits = {}
    for l, items in by_layer.items():
        def f(h: torch.Tensor, items=items) -> torch.Tensor:
            if h.shape[1] == 1:
                return h
            h = h.clone()
            for r, s in items:
                hs = h[r, s.pos].float()
                h[r, s.pos] = (hs + s.dh(hs)).to(h.dtype)
            return h
        edits[l] = f
    return edits


def iso_dir(seed_key: tuple, mask: torch.Tensor) -> torch.Tensor:
    x = np.random.Generator(np.random.PCG64(stable_seed(*seed_key))).standard_normal(D_MODEL)
    return unit_masked(torch.tensor(x, dtype=torch.float32), mask)


def randf_dir(sae: Any, freq: torch.Tensor, k: int, seed_key: tuple, mask: torch.Tensor,
              min_freq: float = 0.05) -> tuple[torch.Tensor, list[int], list[int]]:
    rng = np.random.Generator(np.random.PCG64(stable_seed(*seed_key)))
    pool = torch.nonzero(freq >= min_freq).flatten().tolist()
    lat = sorted(rng.choice(pool, size=min(k, len(pool)), replace=False).tolist())
    sg = rng.choice([-1, 1], size=len(lat)).tolist()
    v = sum(s * sae.W_dec[i] for s, i in zip(sg, lat))
    return unit_masked(v, mask), lat, sg
