#!/usr/bin/env python3
"""Four numerics from ONE bf16 snapshot of Qwen/Qwen3-8B b968826d, switched by a global mode (never two model copies).

Weight set Q (process gpu_q): the vendored exp22 loader load_model(fp8=True) replaces every decoder nn.Linear by the
vendored FP8Linear (e4m3 codes, s_w = absmax(row)/448 per output channel, quantised in fp32 on the GPU). Modes:
  a        vendored FP8Linear.forward, torch._scaled_mm (cuBLASLt, sm_89) -- iteration-4 numerics, unchanged
  a_emul   exact-math emulation of _scaled_mm: e4m3 activation codes and weight codes held exactly in bf16,
           torch.mm(out_dtype=float32), x s_x x s_w in fp32, one rounding to bf16 (used for U1 only)
  b        W8A16: torch.mm(x_bf16, codes_bf16^T, out_dtype=float32) x s_w, one rounding to bf16
           (impl 'cast': codes cast to bf16 per call; impl 'triton': fused fp8->bf16 GEMM, fp32 accumulate)
Weight set B (process gpu_b): bf16 weights on the GPU, embeddings on the CPU (exact gather), lm_head/norms bf16. Modes:
  d        F.linear(x, W)  (== the stock HF bf16 nn.Linear path)
  c        W16A8: q, s = actq(x) (per-token e4m3, == FP8Linear's quantiser); torch.mm(q, W^T, out_dtype=float32) x s,
           one rounding to bf16
Embeddings, RMSNorms and lm_head are bf16 in every engine. q/k/v and gate/up share one input tensor: its activation
quantisation is computed once (vendored _ACT_CACHE identity rule; cleared by the vendored sampler every step).
"""

from __future__ import annotations

import gc
import time
from typing import Any

import torch
import torch.nn.functional as F
from loguru import logger

import c6  # noqa: F401  (sys.path for the vendored code)
import engine as VE  # vendored exp22 src_base/engine.py

FP8_MAX = 448.0
MODE: dict[str, Any] = {"m": None, "b_impl": "cast"}


def actq(x2: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    """Per-row e4m3 activation quantiser, the exact operations of the vendored FP8Linear.forward."""
    xs = x2.abs().amax(dim=1, keepdim=True).float().clamp_(min=1e-12) / FP8_MAX
    xq = (x2.float() / xs).clamp_(-FP8_MAX, FP8_MAX).to(torch.float8_e4m3fn)
    return xq, xs


def weight_quant(W: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    """Per-output-channel e4m3 weight quantiser, the exact operations of the vendored FP8Linear.__init__."""
    W = W.float()
    s = W.abs().amax(dim=1, keepdim=True).clamp(min=1e-12) / FP8_MAX
    return (W / s).clamp_(-FP8_MAX, FP8_MAX).to(torch.float8_e4m3fn), s


def _cached_act(x: torch.Tensor, x2: torch.Tensor, as_bf16: bool) -> tuple[torch.Tensor, torch.Tensor]:
    c = VE._ACT_CACHE
    if c["x"] is x and c.get("tag") == ("bf16" if as_bf16 else "fp8"):
        return c["xq"], c["xs"]
    xq, xs = actq(x2)
    if as_bf16:
        xq = xq.to(torch.bfloat16)
    c.update(x=x, xq=xq, xs=xs, tag="bf16" if as_bf16 else "fp8")
    return xq, xs


# ------------------------------------------------------------------------------------------------ weight set Q
_NATIVE_FORWARD = VE.FP8Linear.forward


def _q_forward(self: Any, x: torch.Tensor) -> torch.Tensor:
    m = MODE["m"]
    if m == "a":
        if VE._ACT_CACHE.get("tag") not in (None, "fp8"):
            VE._ACT_CACHE.update(x=None, xq=None, xs=None, tag=None)
        return _NATIVE_FORWARD(self, x)
    shp = x.shape
    x2 = x.reshape(-1, shp[-1])
    if m == "b":
        if MODE["b_impl"] == "triton":
            import w8a16_triton
            y = w8a16_triton.w8a16_mm(x2, self.wq_t.t(), self.w_scale)
        else:
            wb = self.wq_t.t().to(torch.bfloat16)
            y = (torch.mm(x2, wb.t(), out_dtype=torch.float32) * self.w_scale).to(torch.bfloat16)
    elif m == "a_emul":
        q, s = _cached_act(x, x2, as_bf16=True)
        wb = self.wq_t.t().to(torch.bfloat16)
        y = (torch.mm(q, wb.t(), out_dtype=torch.float32) * s * self.w_scale).to(torch.bfloat16)
    else:
        raise ValueError(f"mode {m} is not a weight-set-Q mode")
    if self.bias is not None:
        y = y + self.bias
    return y.reshape(*shp[:-1], self.out_features)


def load_q(vram_fraction: float = 0.97) -> tuple[Any, Any]:
    VE.FP8Linear.forward = _q_forward
    VE._ACT_CACHE["tag"] = None
    tok, model = VE.load_model(fp8=True, vram_fraction=vram_fraction)
    MODE["m"] = "a"
    return tok, model


# ------------------------------------------------------------------------------------------------ weight set B
class EngLinearB(torch.nn.Module):
    def __init__(self, lin: torch.nn.Linear, device: torch.device):
        super().__init__()
        self.weight = torch.nn.Parameter(lin.weight.data.to(device=device, dtype=torch.bfloat16), requires_grad=False)
        assert lin.bias is None
        self.in_features, self.out_features = lin.in_features, lin.out_features

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        m = MODE["m"]
        if m == "d":
            return F.linear(x, self.weight)
        if m == "c":
            shp = x.shape
            x2 = x.reshape(-1, shp[-1])
            q, s = _cached_act(x, x2, as_bf16=True)
            y = (torch.mm(q, self.weight.t(), out_dtype=torch.float32) * s).to(torch.bfloat16)
            return y.reshape(*shp[:-1], self.out_features)
        raise ValueError(f"mode {m} is not a weight-set-B mode")


class CPUEmbed(torch.nn.Module):
    """Exact embedding gather from a CPU copy (16 GB card); the weight is hidden from .parameters() so that
    model.device stays the GPU."""

    def __init__(self, emb: torch.nn.Embedding, device: torch.device):
        super().__init__()
        self._w = [emb.weight.data.to("cpu", torch.bfloat16).contiguous()]
        self.dev = device
        self.padding_idx = emb.padding_idx

    def forward(self, ids: torch.Tensor) -> torch.Tensor:
        return F.embedding(ids.to("cpu"), self._w[0]).to(self.dev)


def load_b(vram_fraction: float = 0.995) -> tuple[Any, Any]:
    from transformers import AutoModelForCausalLM, AutoTokenizer

    from cfg import model_path

    t0 = time.time()
    path = model_path()
    tok = AutoTokenizer.from_pretrained(path)
    dev = torch.device("cuda", 0)
    model = AutoModelForCausalLM.from_pretrained(path, dtype=torch.bfloat16, attn_implementation="sdpa",
                                                 device_map={"": "cpu"}, low_cpu_mem_usage=True)
    n_lin = 0
    for layer in model.model.layers:
        for name, mod in list(layer.named_modules()):
            for cname, child in list(mod.named_children()):
                if isinstance(child, torch.nn.Linear):
                    setattr(mod, cname, EngLinearB(child, dev))
                    n_lin += 1
        layer.to(dev)
        gc.collect()
    model.model.embed_tokens = CPUEmbed(model.model.embed_tokens, dev)
    model.model.norm.to(dev)
    model.model.rotary_emb.to(dev)
    model.lm_head.to(dev)
    gc.collect()
    torch.cuda.empty_cache()
    model.eval()
    model.requires_grad_(False)
    torch.cuda.set_per_process_memory_fraction(vram_fraction, 0)
    MODE["m"] = "d"
    free, total = torch.cuda.mem_get_info(0)
    logger.info(f"bf16 weight set loaded in {time.time() - t0:.0f}s ({n_lin} linears); device {model.device}; "
                f"free VRAM {free / 2**30:.2f}/{total / 2**30:.2f} GiB")
    return tok, model


def set_mode(m: str) -> None:
    MODE["m"] = m
    VE._ACT_CACHE.update(x=None, xq=None, xs=None, tag=None)


def kv_bytes_per_row(model: Any, P: int, max_new: int) -> int:
    cfg = model.config
    return int(cfg.num_hidden_layers * 2 * cfg.num_key_value_heads * (P + max_new + 1) * cfg.head_dim * 2)
