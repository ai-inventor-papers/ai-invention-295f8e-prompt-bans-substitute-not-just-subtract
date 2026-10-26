#!/usr/bin/env python3
"""engine6: exp27's bf16 HF engine (engine_v4.prefill / engine5.decode_rows, unchanged) loaded on a 16 GB GPU.

bf16 Qwen3-8B holds 16.4 GB of weights and this GPU (RTX 2000 Ada, 16 GB) cannot hold them all. Following the plan's
memory rule ("if free memory < 18 GiB, put the input embedding table on the CPU (exact lookup); keep lm_head on the
GPU"), the 151,936 x 4,096 input-embedding table stays in CPU RAM and every lookup is an exact row gather whose bf16
result is copied to the GPU. Every decoder block, the final norm, the rotary table and lm_head run on the GPU in bf16
exactly as in exp27 (no quantisation). The lookup is bit-exact, so the only engine difference to exp27 is the GPU
class (GEMM kernels), which the engine check measures.
"""

from __future__ import annotations

import gc
import time
from typing import Any

import torch
from loguru import logger

from cfg import MODEL_ID, MODEL_REVISION, model_path


class CPUEmbedding(torch.nn.Module):
    """Exact embedding lookup from a CPU-resident bf16 table; the gathered rows are moved to `device`."""

    def __init__(self, weight_cpu: torch.Tensor, device: torch.device):
        super().__init__()
        object.__setattr__(self, "weight_cpu", weight_cpu)  # plain attribute: never moved by .to()
        self.dev = device
        self.num_embeddings, self.embedding_dim = weight_cpu.shape

    @property
    def weight(self) -> torch.Tensor:  # read-only access for code that inspects the table
        return self.weight_cpu

    def forward(self, input_ids: torch.Tensor) -> torch.Tensor:
        ids = input_ids.to("cpu")
        return torch.nn.functional.embedding(ids, self.weight_cpu).to(self.dev)


def load_model_bf16(model_id: str = MODEL_ID, revision: str | None = MODEL_REVISION, vram_fraction: float = 0.985,
                    cpu_embed: bool | None = None):
    """Load bf16 Qwen3-8B with every decoder block and lm_head on cuda:0; the input embedding stays on the CPU when
    free VRAM < 18 GiB (or when cpu_embed=True). Returns (tok, model, info)."""
    from transformers import AutoModelForCausalLM, AutoTokenizer

    t0 = time.time()
    path = model_path(model_id, revision)
    kw = {"revision": revision} if path == model_id and revision else {}
    tok = AutoTokenizer.from_pretrained(path, **kw)
    dev = torch.device("cuda", 0)
    free0, total = torch.cuda.mem_get_info(0)
    if cpu_embed is None:
        cpu_embed = free0 < 18 * 1024 ** 3
    model = AutoModelForCausalLM.from_pretrained(path, dtype=torch.bfloat16, attn_implementation="sdpa",
                                                 device_map={"": "cpu"}, low_cpu_mem_usage=True, **kw)
    assert not model.config.tie_word_embeddings, "tied embeddings: the CPU table would also be lm_head"
    for layer in model.model.layers:
        layer.to(dev)
    model.model.norm.to(dev)
    model.model.rotary_emb.to(dev)
    model.lm_head.to(dev)
    if cpu_embed:
        W = model.model.embed_tokens.weight.data.contiguous()
        model.model.embed_tokens = CPUEmbedding(W, dev)
    else:
        model.model.embed_tokens.to(dev)
    gc.collect()
    torch.cuda.empty_cache()
    model.eval()
    model.requires_grad_(False)
    torch.cuda.set_per_process_memory_fraction(vram_fraction, 0)
    free, total = torch.cuda.mem_get_info(0)
    info = {"precision": "bf16", "cpu_embedding": bool(cpu_embed), "free_vram_before_GB": round(free0 / 1e9, 3),
            "free_vram_after_GB": round(free / 1e9, 3), "total_vram_GB": round(total / 1e9, 3),
            "gpu": torch.cuda.get_device_name(0), "load_seconds": round(time.time() - t0, 1)}
    logger.info(f"{model_id} bf16 loaded: {info}")
    return tok, model, info


def model_device(model: Any) -> torch.device:
    return model.lm_head.weight.device
