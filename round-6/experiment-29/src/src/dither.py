#!/usr/bin/env python3
"""Dither arm (mechanism probe): W16A16 with non-subtractive uniform noise matched element by element to the e4m3
rounding step of the A8 quantiser.

For a linear-input row x at an active (block, position): xs = absmax_row / 448, z = x / xs,
    step(z) = 2 ** (floor(log2 |z|) - 3)   for |z| >= 2^-6     (e4m3 normal spacing, 3 mantissa bits)
            = 2 ** -9                       below               (e4m3 subnormal spacing)
    x' = bf16(x + U(-step/2, +step/2) * xs)
One draw per DISTINCT input tensor (q/k/v share one draw, gate/up share one, o_proj and down_proj draw their own),
mirroring exp19's activation cache. Implemented as forward pre-hooks on the NATIVE nn.Linear modules, so the GEMM
kernel is the W16A16 one. Variant 1: blocks 12-35, spec positions [p1, spec_end), prefill only. Variant 2: variant 1
plus position R = P - 1 in the prefill and the first 32 decode steps (every row of the batch). Noise is deterministic
per row: torch.Generator('cuda') seeded by stable_seed(task, 'DITHER', variant, w, k, block, input_id, step) % 2**63,
so DITHER_TWIN and DITHER_PN2 rows of the same slot share their uniforms (they differ only by the displacement).
"""

from __future__ import annotations

import contextlib
from typing import Any, Iterator

import torch

from cfg import stable_seed
from cfg_e import DITHER_BLOCKS, N_DITHER_DECODE

E4M3_MAX = 448.0
# (role, input_id): q/k/v read input 0, o_proj input 1, gate/up input 2, down input 3
ROLES = {"self_attn.q_proj": ("draw", 0), "self_attn.k_proj": ("reuse", 0), "self_attn.v_proj": ("reuse", 0),
         "self_attn.o_proj": ("draw", 1), "mlp.gate_proj": ("draw", 2), "mlp.up_proj": ("reuse", 2),
         "mlp.down_proj": ("draw", 3)}

STATE: dict[str, Any] = {"active": False}
_GEN: dict[str, torch.Generator] = {}


def _gen() -> torch.Generator:
    if "g" not in _GEN:
        _GEN["g"] = torch.Generator(device="cuda")
    return _GEN["g"]


def step_size(z: torch.Tensor) -> torch.Tensor:
    az = z.abs()
    e = torch.floor(torch.log2(az.clamp(min=2.0 ** -6)))
    return torch.where(az >= 2.0 ** -6, torch.exp2(e - 3.0), torch.full_like(az, 2.0 ** -9))


def dither_rows(x2: torch.Tensor, U: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    """x2 [n, K] (any float dtype), U [n, K] uniforms in [0, 1). Returns (bf16 dithered rows, fp32 noise)."""
    xf = x2.float()
    xs = x2.abs().amax(dim=1, keepdim=True).float().clamp_(min=1e-12) / E4M3_MAX
    noise = (U - 0.5) * step_size(xf / xs) * xs
    return (xf + noise).to(torch.bfloat16), noise


def _uniforms(seed: int, n: int, K: int) -> torch.Tensor:
    g = _gen()
    g.manual_seed(seed % (2 ** 63))
    return torch.rand(n, K, generator=g, device="cuda", dtype=torch.float32)


def _apply(x: torch.Tensor, block: int, input_id: int) -> torch.Tensor:
    st = STATE
    B, T, K = x.shape
    if st["mode"] == "prefill":
        assert B == 1
        pos = [p for p in st["positions"] if p < T]
        if not pos:
            return x
        seed = stable_seed(st["task"], "DITHER", st["variant"], st["w"], st["k"], block, input_id, "prefill")
        U = _uniforms(seed, len(pos), K)
        idx = torch.tensor(pos, device=x.device)
        xd, _ = dither_rows(x[0, idx], U)
        out = x.clone()
        out[0, idx] = xd
        return out
    # decode: one position per row, every row dithered during the first N_DITHER_DECODE steps (variant 2 only)
    step = st["step"]
    if st["variant"] != 2 or step >= N_DITHER_DECODE or step < 0:
        return x
    assert T == 1 and B == len(st["row_ks"])
    U = torch.cat([_uniforms(stable_seed(st["task"], "DITHER", st["variant"], st["w"], k, block, input_id, step),
                             1, K) for k in st["row_ks"]], 0)
    xd, _ = dither_rows(x[:, 0], U)
    return xd[:, None, :]


class DitherHooks:
    """Pre-hooks on the native W16A16 nn.Linear modules of blocks 12-35 plus a decoder pre-hook that clears the
    shared-input cache and counts decode steps. Inactive (identity) unless STATE['active']."""

    def __init__(self, model: Any):
        from qlinear import _resolve

        self.handles = []
        self.cache: dict[tuple[int, int], tuple[torch.Tensor, torch.Tensor]] = {}
        for l in DITHER_BLOCKS:
            layer = model.model.layers[l]
            for name, (role, iid) in ROLES.items():
                parent, attr = _resolve(layer, name)
                mod = getattr(parent, attr)
                assert isinstance(mod, torch.nn.Linear), f"dither needs native W16A16 linears ({name}: {type(mod)})"
                self.handles.append(mod.register_forward_pre_hook(self._mk(l, role, iid)))
        self.handles.append(model.model.register_forward_pre_hook(self._model_pre))

    def _model_pre(self, mod: Any, args: Any, kwargs: Any = None) -> None:
        self.cache.clear()
        if STATE.get("active") and STATE.get("mode") == "decode":
            STATE["step"] += 1
        return None

    def _mk(self, l: int, role: str, iid: int):
        def pre(mod: Any, args: tuple) -> Any:
            if not STATE.get("active"):
                return None
            x = args[0]
            if role == "reuse":
                c = self.cache.get((l, iid))
                if c is not None and c[0] is x:
                    return (c[1],) + tuple(args[1:])
                # not shared with the drawing projection (should not happen): draw for this input
            xd = _apply(x, l, iid)
            self.cache[(l, iid)] = (x, xd)
            return (xd,) + tuple(args[1:])
        return pre

    def remove(self) -> None:
        for h in self.handles:
            h.remove()
        self.handles.clear()


@contextlib.contextmanager
def dither_prefill(task: str, variant: int, w: str, k: int, positions: list[int]) -> Iterator[None]:
    STATE.update(active=True, mode="prefill", task=task, variant=variant, w=w, k=k, positions=list(positions))
    try:
        yield
    finally:
        STATE.update(active=False)


@contextlib.contextmanager
def dither_decode(task: str, variant: int, w: str, row_ks: list[int]) -> Iterator[None]:
    STATE.update(active=True, mode="decode", task=task, variant=variant, w=w, row_ks=list(row_ks), step=-1)
    try:
        yield
    finally:
        STATE.update(active=False)
