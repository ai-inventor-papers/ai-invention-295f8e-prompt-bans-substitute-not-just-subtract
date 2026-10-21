#!/usr/bin/env python3
"""Emulated FP8 (e4m3) decoder linears for the weight-by-activation precision factorial, and the model families.

quant_weight / quant_e4m3_rows are exp19's FP8Linear quantisers op for op (per-output-channel weight scale
s = absmax_row / 448, per-row activation scale xs = absmax_row / 448, clamp +-448, RNE cast to float8_e4m3fn).
An e4m3 value is exact in bf16 and a product of two e4m3 values is exact in fp32, so
    acc = torch.mm(xq_bf16, wq_bf16^T, out_dtype=float32)        (fp32 accumulate, fp32 out)
    y   = (acc * w_scale * xs).to(bf16)                           (both scales in fp32, ONE rounding)
reproduces the quantisation grid of _scaled_mm exactly; only the accumulation order inside the GEMM differs.
All three FP8 cells (W8A8, W8A16, W16A8) use this one backend; only the quantisers switch on or off.

Families (one model on the GPU at a time; built from a CPU copy of the bf16 decoder linears, so switching costs one
host-to-device copy instead of a reload):
  W16  native bf16 nn.Linear (W16A16, the iteration-5 engine); QLinear wrappers that SHARE the weight tensor give
       W16A8 (activation quantiser on) and W16A16mm (kernel-only floor, quantisers off)
  W8   QLinear with bf16 containers of the e4m3 weight codes + fp32 scales: W8A8 (act_q on) / W8A16 (act_q off)
  REAL exp19's FP8Linear unchanged (float8 storage, torch._scaled_mm) -- sm_89+ only
The shared-input cache is exp19's own engine_v4._ACT_CACHE (q/k/v and gate/up quantise one input once), so
engine_v4.prefill / sample, which clear it before every model call, drive QLinear exactly as they drove FP8Linear.
"""

from __future__ import annotations

import gc
import time
from typing import Any

import torch
from loguru import logger

from engine_v4 import _ACT_CACHE, FP8Linear

E4M3_MAX = 448.0
MODE: dict[str, Any] = {"act_q": False}
LIN_NAMES = ("self_attn.q_proj", "self_attn.k_proj", "self_attn.v_proj", "self_attn.o_proj", "mlp.gate_proj",
             "mlp.up_proj", "mlp.down_proj")


def quant_e4m3_rows(x2: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    """exp19's activation quantiser; returns the e4m3 values in a bf16 container (exact) and the fp32 row scale."""
    xs = x2.abs().amax(dim=1, keepdim=True).float().clamp_(min=1e-12) / E4M3_MAX
    xq = (x2.float() / xs).clamp_(-E4M3_MAX, E4M3_MAX).to(torch.float8_e4m3fn)
    return xq.to(torch.bfloat16), xs


def quant_e4m3_rows_codes(x2: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    """Same as quant_e4m3_rows but returns the float8 codes (tests)."""
    xs = x2.abs().amax(dim=1, keepdim=True).float().clamp_(min=1e-12) / E4M3_MAX
    xq = (x2.float() / xs).clamp_(-E4M3_MAX, E4M3_MAX).to(torch.float8_e4m3fn)
    return xq, xs


def quant_weight(W: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    """exp19's weight quantiser: float8 codes [N, K] and the fp32 scale as [1, N]."""
    Wf = W.float()
    s = Wf.abs().amax(dim=1, keepdim=True).clamp(min=1e-12) / E4M3_MAX
    wq = (Wf / s).clamp_(-E4M3_MAX, E4M3_MAX).to(torch.float8_e4m3fn)
    return wq, s.t().contiguous()


class QLinear(torch.nn.Module):
    """y = x W^T through torch.mm(out_dtype=float32); weights either the original bf16 (w_scale None) or a bf16
    container of e4m3 codes with an fp32 per-output-channel scale; activations quantised per row iff MODE['act_q']."""

    def __init__(self, w: torch.Tensor, w_scale: torch.Tensor | None, in_features: int, out_features: int,
                 act_q: bool | None = None):
        super().__init__()
        self.w = w                          # [N, K] bf16 (shared with a native nn.Linear for the W16 wrappers)
        self.w_scale = w_scale              # [1, N] fp32 or None
        self.in_features, self.out_features = in_features, out_features
        self.act_q = act_q                  # None -> follow MODE['act_q']

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        shp = x.shape
        aq = MODE["act_q"] if self.act_q is None else self.act_q
        if aq:
            if _ACT_CACHE["x"] is x:        # q/k/v and gate/up share one input tensor: quantise it once
                xin, xs = _ACT_CACHE["xq"], _ACT_CACHE["xs"]
            else:
                xin, xs = quant_e4m3_rows(x.reshape(-1, shp[-1]))
                _ACT_CACHE.update(x=x, xq=xin, xs=xs)
        else:
            xin, xs = x.reshape(-1, shp[-1]), None
        acc = torch.mm(xin, self.w.t(), out_dtype=torch.float32)
        if self.w_scale is not None:
            acc.mul_(self.w_scale)
        if xs is not None:
            acc.mul_(xs)
        return acc.to(torch.bfloat16).reshape(*shp[:-1], self.out_features)


def _resolve(layer: torch.nn.Module, name: str) -> tuple[torch.nn.Module, str]:
    parent = layer
    parts = name.split(".")
    for p in parts[:-1]:
        parent = getattr(parent, p)
    return parent, parts[-1]


class FamilyManager:
    """Holds the CPU bf16 decoder linears and installs one family at a time on the GPU."""

    def __init__(self, model: Any, dev: torch.device):
        self.model, self.dev = model, dev
        self.cpu: dict[tuple[int, str], torch.nn.Linear] = {}
        for li, layer in enumerate(model.model.layers):
            for name in LIN_NAMES:
                parent, attr = _resolve(layer, name)
                lin = getattr(parent, attr)
                assert isinstance(lin, torch.nn.Linear) and lin.bias is None, (li, name)
                self.cpu[(li, name)] = lin
        self.family: str | None = None
        self.precision: str | None = None
        self.native: dict[tuple[int, str], torch.nn.Linear] = {}
        self.n_linears = len(self.cpu)

    # ------------------------------------------------------------------------------------------ build
    def _install(self, li: int, name: str, mod: torch.nn.Module) -> None:
        parent, attr = _resolve(self.model.model.layers[li], name)
        setattr(parent, attr, mod)

    def build(self, family: str) -> dict[str, Any]:
        if self.family == family:
            return {"family": family, "seconds": 0.0, "rebuilt": False}
        t0 = time.time()
        self.native.clear()
        MODE["act_q"] = False
        _ACT_CACHE.update(x=None, xq=None, xs=None)
        for li, layer in enumerate(self.model.model.layers):
            for name in LIN_NAMES:   # drop the previous family's module of this layer first (peak = 1 family + 1 layer)
                self._install(li, name, torch.nn.Identity())
            gc.collect()
            for name in LIN_NAMES:
                lin = self.cpu[(li, name)]
                if family == "W16":
                    new = torch.nn.Linear(lin.in_features, lin.out_features, bias=False, device=self.dev,
                                          dtype=torch.bfloat16)
                    with torch.no_grad():
                        new.weight.copy_(lin.weight.data.to(self.dev))
                    new.requires_grad_(False)
                    self.native[(li, name)] = new
                elif family == "W8":
                    wq, s = quant_weight(lin.weight.data.to(self.dev))
                    new = QLinear(wq.to(torch.bfloat16), s, lin.in_features, lin.out_features)
                    del wq
                elif family == "REAL":
                    new = FP8Linear(lin, self.dev)
                else:
                    raise ValueError(family)
                self._install(li, name, new)
            layer.to(self.dev)          # norms (and nothing else: the CPU linears are no longer attached)
        torch.cuda.empty_cache()
        gc.collect()
        self.family = family
        self.precision = {"W16": "W16A16", "W8": "W8A8", "REAL": "W8A8REAL"}[family]
        if family == "W8":
            MODE["act_q"] = True
        free, total = torch.cuda.mem_get_info(0)
        info = {"family": family, "seconds": round(time.time() - t0, 1), "rebuilt": True,
                "free_vram_gb": round(free / 1e9, 2), "alloc_gb": round(torch.cuda.memory_allocated() / 1e9, 2)}
        logger.info(f"family {family} installed: {info}")
        return info

    # ------------------------------------------------------------------------------------------ precision
    def set_precision(self, precision: str) -> None:
        """Switch inside the installed family (builds the family first if needed)."""
        fam = {"W8A8": "W8", "W8A16": "W8", "W16A16": "W16", "W16A8": "W16", "W16A16mm": "W16",
               "W8A8REAL": "REAL"}[precision]
        self.build(fam)
        _ACT_CACHE.update(x=None, xq=None, xs=None)
        if fam == "W8":
            MODE["act_q"] = precision == "W8A8"
        elif fam == "W16":
            MODE["act_q"] = False
            for (li, name), lin in self.native.items():
                if precision == "W16A16":
                    self._install(li, name, lin)
                else:                     # W16A8 (act_q on) or W16A16mm (off): wrappers sharing the weight tensor
                    self._install(li, name, QLinear(lin.weight.data, None, lin.in_features, lin.out_features,
                                                    act_q=(precision == "W16A8")))
        self.precision = precision

    def describe(self) -> dict[str, Any]:
        kinds: dict[str, int] = {}
        for li, layer in enumerate(self.model.model.layers):
            for name in LIN_NAMES:
                parent, attr = _resolve(layer, name)
                k = type(getattr(parent, attr)).__name__
                kinds[k] = kinds.get(k, 0) + 1
        return {"precision": self.precision, "family": self.family, "act_q": MODE["act_q"], "modules": kinds}


def load_model_cpu() -> tuple[Any, Any, FamilyManager]:
    """bf16 Qwen3-8B (pinned snapshot) on the CPU; embeddings, final norm, rotary and lm_head moved to the GPU; the
    decoder linears stay on the CPU as the source of every family."""
    from transformers import AutoModelForCausalLM, AutoTokenizer

    from cfg import MODEL_ID, MODEL_REVISION, model_path

    t0 = time.time()
    path = model_path(MODEL_ID, MODEL_REVISION)
    kw = {"revision": MODEL_REVISION} if path == MODEL_ID else {}
    tok = AutoTokenizer.from_pretrained(path, **kw)
    model = AutoModelForCausalLM.from_pretrained(path, dtype=torch.bfloat16, attn_implementation="sdpa",
                                                 device_map={"": "cpu"}, low_cpu_mem_usage=True, **kw)
    model.eval()
    model.requires_grad_(False)
    dev = torch.device("cuda", 0)
    fm = FamilyManager(model, dev)
    for li, layer in enumerate(model.model.layers):
        for name in LIN_NAMES:
            fm._install(li, name, torch.nn.Identity())
    model.model.embed_tokens.to(dev)
    model.model.norm.to(dev)
    model.model.rotary_emb.to(dev)
    model.lm_head.to(dev)
    for layer in model.model.layers:
        layer.to(dev)          # norms only; linears are placeholders until a family is built
    logger.info(f"bf16 weights on CPU + shared parts on GPU in {time.time() - t0:.0f}s (path {path})")
    return tok, model, fm
