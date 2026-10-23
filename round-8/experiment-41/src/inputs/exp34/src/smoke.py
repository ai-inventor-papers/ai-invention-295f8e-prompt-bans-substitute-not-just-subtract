#!/usr/bin/env python3
"""GPU smoke test: load the bf16 engine, one T10 twin batch (B=24) and one T2 batch (B=12); timing + memory."""
import sys, time, json
sys.path.insert(0, __import__("pathlib").Path(__file__).resolve().parent.as_posix())
import c7 as common
from c7 import setup_logging, read_jsonl, V22, write_json, RESULTS
setup_logging("smoke")
from loguru import logger
import torch
import engine7 as E
from engine4 import u_stream
t0=time.time()
tok, model = E.load()
logger.info(f"load {time.time()-t0:.0f}s; {E.hardware_info(model)}")
P = {r["pid"]: r for r in read_jsonl(V22/"prompts"/"prompts4.jsonl")}
out={}
for task, B, fence, mx in (("T10", 24, "bench", 1024), ("T2", 12, "path", 1536)):
    p = P[f"{task}|twin|-|W1|-"]
    pre = E.prefill(model, p["ids"])
    t1=time.time()
    res = E.sample(model, tok, [{"pre": pre, "us": [u_stream(task, "W1", k) for k in range(B)]}], fence, mx)
    dt=time.time()-t1
    free,total=torch.cuda.mem_get_info(0)
    out[task]={"B":B,"sec":dt,"steps":res[0]["steps"],"max_tok":max(r["n_tokens"] for r in res),"peak_gib":torch.cuda.max_memory_allocated()/2**30,"free_gib":free/2**30}
    logger.info(f"{task}: {out[task]}")
    logger.info(tok.decode(res[0]["token_ids"])[:600])
write_json(RESULTS/"smoke.json", out)
