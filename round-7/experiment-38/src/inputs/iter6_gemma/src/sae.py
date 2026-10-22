#!/usr/bin/env python3
"""Gemma Scope 2 resid_post JumpReLU SAEs, loaded directly from the Hub snapshot (config.json + params.safetensors).

f(x)    = (x W_enc + b_enc) * 1[x W_enc + b_enc > threshold]     (JumpReLU)
xhat(f) = f W_dec + b_dec
The hook point of every SAE is 'model.layers.<l>.output' (asserted), i.e. the decoder-block output = HF
hidden_states[l + 1] = the residual stream after block l. config.json carries no input-normalisation field for these
SAEs (asserted: only the keys listed in KNOWN_KEYS are accepted, so an unexpected normalisation field fails loudly).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import torch

from cfg import SAE_IDS, SCOPE_REPO, SCOPE_REV

KNOWN_KEYS = {"hf_hook_point_in", "hf_hook_point_out", "width", "model_name", "architecture", "l0",
              "affine_connection", "type"}


def sae_dir(layer: int) -> Path:
    from huggingface_hub import snapshot_download

    sid = SAE_IDS[layer]
    root = snapshot_download(SCOPE_REPO, revision=SCOPE_REV, allow_patterns=[f"{sid}/config.json",
                                                                             f"{sid}/params.safetensors"])
    return Path(root) / sid


class JumpReLUSAE:
    """Minimal JumpReLU SAE. All weights fp32 on `device`."""

    def __init__(self, layer: int, device: str = "cpu"):
        from safetensors.torch import load_file

        d = sae_dir(layer)
        self.cfg: dict[str, Any] = json.loads((d / "config.json").read_text())
        extra = set(self.cfg) - KNOWN_KEYS
        assert not extra, f"unexpected SAE config fields (normalisation?): {extra}"
        assert self.cfg["architecture"] == "jump_relu", self.cfg
        assert self.cfg["hf_hook_point_in"] == f"model.layers.{layer}.output", self.cfg
        assert not self.cfg.get("affine_connection"), self.cfg
        p = load_file(str(d / "params.safetensors"))
        keys = {k.lower(): k for k in p}
        self.W_enc = p[keys["w_enc"]].float().to(device)          # [D, F]
        self.W_dec = p[keys["w_dec"]].float().to(device)          # [F, D]
        self.b_enc = p[keys["b_enc"]].float().to(device)
        self.b_dec = p[keys["b_dec"]].float().to(device)
        self.threshold = p[keys["threshold"]].float().to(device)
        self.layer = layer
        self.device = device
        self.d_model, self.d_sae = self.W_enc.shape
        assert self.W_dec.shape == (self.d_sae, self.d_model)
        self.param_keys = sorted(p)

    def to(self, device: str) -> "JumpReLUSAE":
        for k in ("W_enc", "W_dec", "b_enc", "b_dec", "threshold"):
            setattr(self, k, getattr(self, k).to(device))
        self.device = device
        return self

    def pre(self, x: torch.Tensor) -> torch.Tensor:
        return x.float() @ self.W_enc + self.b_enc

    def encode(self, x: torch.Tensor) -> torch.Tensor:
        pre = self.pre(x)
        return pre * (pre > self.threshold)

    def decode(self, f: torch.Tensor) -> torch.Tensor:
        return f @ self.W_dec + self.b_dec

    def recon(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        f = self.encode(x)
        return f, self.decode(f)


def load_saes(device: str = "cpu", layers: tuple[int, ...] | None = None) -> dict[int, JumpReLUSAE]:
    return {l: JumpReLUSAE(l, device) for l in (layers or tuple(SAE_IDS))}


def sparse_codes(f: torch.Tensor) -> dict[str, Any]:
    """Dense [N, F] codes -> {'idx': list of int16 arrays, 'val': list of fp16 arrays} (nonzero latents only)."""
    out_i, out_v = [], []
    for row in f:
        nz = torch.nonzero(row).flatten()
        out_i.append(nz.to(torch.int32).cpu())
        out_v.append(row[nz].to(torch.float16).cpu())
    return {"idx": out_i, "val": out_v}


def dense_from_sparse(idx: list[torch.Tensor], val: list[torch.Tensor], d_sae: int) -> torch.Tensor:
    X = torch.zeros(len(idx), d_sae, dtype=torch.float32)
    for i, (a, b) in enumerate(zip(idx, val)):
        if a.numel():
            X[i, a.long()] = b.float()
    return X
