#!/usr/bin/env python3
"""Format-pilot diagnosis: raw stage-A texts for EAP_A / PSL_A on calibration keys (no code outcome observed)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import json
import torch
from engine_v4 import load_model, u_stream, vocab_len
from engine5 import decode_rows
from prompts5 import load_prompts
from gen5 import Ctx
from cfg5 import PSL_A_MAX, EAP_A_MAX

kinds = sys.argv[1].split(",") if len(sys.argv) > 1 else ["eap", "psl"]
prompts = load_prompts()
tok, model = load_model(fp8=False, vram_fraction=0.97)
nv = vocab_len(tok)
out = {}
for task in ("T03", "T2"):
    ctx = Ctx(model, tok, prompts, task)
    for kind in kinds:
        rows = [{"pre": ctx.pre_of(w, kind), "u": u_stream(task, w, 0, "CAL", kind.upper() + ":A", n=320),
                 "T": 1.0 if kind == "eap" else 0.9, "top_p": 1.0 if kind == "eap" else 0.95, "max_new": 320,
                 "fence": False} for w in ("W1", "W2")]
        res = decode_rows(model, rows, tok)
        out[f"{task}|{kind}"] = [tok.decode([t for t in r["token_ids"] if t < nv], skip_special_tokens=True)[:700]
                                 for r in res]
    ctx.release()
print(json.dumps(out, indent=1))
