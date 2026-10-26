#!/usr/bin/env python3
"""GPU probe: load bf16 Qwen3-8B (CPU embedding), time prefill and decode steps at several batch sizes."""
import json
import sys
import time
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg import setup_logging, read_jsonl, ROOT, write_json  # noqa: E402
from engine6 import load_model_bf16  # noqa: E402
from engine_v4 import prefill, u_stream  # noqa: E402
from engine5 import decode_rows  # noqa: E402

setup_logging("probe_gpu")
tok, model, info = load_model_bf16()
pr = {(r["task"], r["w"], r["kind"]): r for r in read_jsonl(ROOT / "prompts" / "prompts.jsonl")}
p = pr[("T03", "W1", "twin")]
t0 = time.time(); pre = prefill(model, p["ids"]); torch.cuda.synchronize(); t_pre = time.time() - t0
out = {"info": info, "P": p["P"], "prefill_s": round(t_pre, 3)}
for B in (8, 12, 16):
    rows = [{"pre": pre, "u": u_stream("T03", "W1", k, n=1536), "T": 1.0, "max_new": 160, "fence": False}
            for k in range(B)]
    torch.cuda.reset_peak_memory_stats()
    try:
        t0 = time.time(); res = decode_rows(model, rows, tok, fence_kind=None); torch.cuda.synchronize()
        dt = time.time() - t0
        out[f"B{B}"] = {"seconds": round(dt, 2), "steps": res[0]["steps"], "s_per_step": round(dt / res[0]["steps"], 4),
                        "peak_GB": round(torch.cuda.max_memory_allocated() / 1e9, 3)}
    except torch.cuda.OutOfMemoryError as e:
        out[f"B{B}"] = {"oom": str(e)[:200]}
        torch.cuda.empty_cache()
    print(out, flush=True)
txt = tok.decode(res[0]["token_ids"], skip_special_tokens=True) if "res" in dir() else ""
out["sample_text_head"] = txt[:400]
write_json(ROOT / "results" / "probe_gpu.json", out)
print(json.dumps(out, indent=1))
