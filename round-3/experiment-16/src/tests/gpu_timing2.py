#!/usr/bin/env python3
"""Stock-path (no explicit mask) step latency and peak memory for B in {20, 30, 40}."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import torch  # noqa: E402
from loguru import logger  # noqa: E402

from cfg import setup_logging, write_json, RESULTS_DIR  # noqa: E402
from engine import load_model, prefill, sample, u_stream  # noqa: E402
from prompts_s1 import load_prompts  # noqa: E402

setup_logging("gpu_timing2")
tok, model = load_model(vram_fraction=0.98)
pr = load_prompts()
r = pr[("T03", "W5", "twin_A")]
pre = prefill(model, r["ids"])
out = {}
import engine
for B in (20, 30, 40):
    rows = [{"kv": pre["kv"], "r_logits": pre["r_logits"], "u": u_stream("smoke", B, k)} for k in range(B)]
    torch.cuda.synchronize(); torch.cuda.reset_peak_memory_stats()
    old = (engine.IM_END, engine.ENDOFTEXT)
    engine.IM_END, engine.ENDOFTEXT = -1, -2
    t0 = time.time()
    res = sample(model, rows, max_new=200)
    torch.cuda.synchronize()
    engine.IM_END, engine.ENDOFTEXT = old
    dt = time.time() - t0
    out[B] = {"steps": res[0]["steps"], "s": dt, "ms_per_step": 1000 * dt / res[0]["steps"],
              "peak_gb": torch.cuda.max_memory_allocated() / 1e9}
    logger.info(f"stock B={B}: {out[B]}")
write_json(RESULTS_DIR / "gpu_timing_stock.json", out)
