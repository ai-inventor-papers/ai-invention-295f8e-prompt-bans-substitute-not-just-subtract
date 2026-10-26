#!/usr/bin/env python3
"""GPU smoke + timing: per-step latency and peak memory for B in {10, 20, 40}; 1024 forced steps at the chosen B."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import torch  # noqa: E402
from loguru import logger  # noqa: E402

from cfg import setup_logging, write_json, RESULTS_DIR  # noqa: E402
from engine import load_model, prefill, sample, u_stream  # noqa: E402
from prompts_s1 import load_prompts  # noqa: E402

setup_logging("gpu_smoke")
tok, model = load_model()
pr = load_prompts()
longest = max((r for k, r in pr.items() if k[2] == "twin_A" and k[0] not in ("t1", "t2")), key=lambda r: r["P"])
logger.info(f"longest bench P = {longest['P']} ({longest['task']} {longest['w']})")
pre = prefill(model, longest["ids"])
out = {}
for B in (10, 20, 40):
    rows = [{"kv": pre["kv"], "r_logits": pre["r_logits"], "u": u_stream("smoke", B, k)} for k in range(B)]
    torch.cuda.synchronize(); torch.cuda.reset_peak_memory_stats()
    t0 = time.time()
    res = sample(model, rows, max_new=128)
    torch.cuda.synchronize()
    dt = time.time() - t0
    steps = res[0]["steps"]
    out[B] = {"steps": steps, "s": dt, "ms_per_step": 1000 * dt / max(steps, 1),
              "peak_gb": torch.cuda.max_memory_allocated() / 1e9}
    logger.info(f"B={B}: {steps} steps in {dt:.1f}s -> {out[B]['ms_per_step']:.1f} ms/step; peak {out[B]['peak_gb']:.2f} GB")
print(tok.decode(res[0]["token_ids"])[:300])
Bp = int(sys.argv[1]) if len(sys.argv) > 1 else 40
rows = [{"kv": pre["kv"], "r_logits": pre["r_logits"], "u": u_stream("probe", k)} for k in range(Bp)]
# force 1024 steps: replace EOS by never stopping -> use max_new=1024 and a stop-free run on repeated uniforms
torch.cuda.reset_peak_memory_stats()
t0 = time.time()
try:
    import engine
    old = (engine.IM_END, engine.ENDOFTEXT)
    engine.IM_END, engine.ENDOFTEXT = -1, -2  # never stop: memory probe at the full 1024 steps
    res = sample(model, rows, max_new=1024)
    engine.IM_END, engine.ENDOFTEXT = old
    out["probe"] = {"B": Bp, "steps": res[0]["steps"], "s": time.time() - t0,
                    "peak_gb": torch.cuda.max_memory_allocated() / 1e9, "ok": True}
except torch.cuda.OutOfMemoryError as e:
    out["probe"] = {"B": Bp, "ok": False, "error": str(e)[:200]}
logger.info(f"probe: {out['probe']}")
write_json(RESULTS_DIR / "gpu_smoke.json", out)
