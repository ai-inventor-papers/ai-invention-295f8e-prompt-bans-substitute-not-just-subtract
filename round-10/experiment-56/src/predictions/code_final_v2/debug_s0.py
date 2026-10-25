#!/usr/bin/env python3
"""S0 debug round 1 (plan: ids, opening, D/A ids, versions, attention, batch shape): per-prompt margin spread of the
instruct and base T10/B3 fork over numerically equivalent computation paths on THIS GPU (one-token path at
B = 1, 8, 16, 24, 40 and a B = 1 full forward), to size the bf16 numerics floor against the cross-GPU differences
from iteration 9 (L4). Writes results/s0_debug.json.

Usage: debug_s0.py qwen|qwen_base
"""

from __future__ import annotations

import sys
from typing import Any

import numpy as np
import torch
from loguru import logger

from cfg10 import I9_RES, RESULTS_DIR, UNITS_TF, read_json, setup_logging, utc_now, write_json
from capture10 import CM, class_margin, full_logits, load, onetok_states


@torch.no_grad()
def main(which: str) -> None:
    model, tok, info = load(which)
    units = read_json(I9_RES / "units.json")
    W = model.lm_head.weight
    p_out = RESULTS_DIR / "s0_debug.json"
    out: dict[str, Any] = read_json(p_out) if p_out.exists() else {}
    rec: dict[str, Any] = {"utc": utc_now(), "load": info, "units": {}}
    for u in UNITS_TF:
        f = units[u]["forks"][0]
        rows = []
        for p in units[u]["prompts"]:
            ids = p["ids"] + f["opening"]
            kv = CM.prefix_kv(model, ids)
            r: dict[str, Any] = {"pid": p["pid"]}
            for B in (1, 8, 16, 24, 40):
                c = onetok_states(model, ids, B, kv=kv, want_mlp=False)
                r[f"B{B}"] = float(class_margin(full_logits(W, c["h_fin"].cuda()[None])[0], f["D"], f["A"]))
            o = model.model(input_ids=torch.tensor([ids], device="cuda"), use_cache=False)
            r["full_fwd"] = float(class_margin(full_logits(W, o.last_hidden_state[0, -1][None])[0], f["D"], f["A"]))
            vals = [r[k] for k in r if k != "pid"]
            r["spread"] = float(max(vals) - min(vals))
            rows.append(r)
            del kv, o
        sp = np.array([r["spread"] for r in rows])
        rec["units"][u] = {"rows": rows, "spread_mean": float(sp.mean()), "spread_max": float(sp.max()),
                           "spread_median": float(np.median(sp))}
        logger.info(f"{which} {u}: per-prompt path spread mean {sp.mean():.3f}, median {np.median(sp):.3f}, max "
                    f"{sp.max():.3f}")
    out[which] = rec
    write_json(p_out, out)


if __name__ == "__main__":
    setup_logging(f"debug_s0_{sys.argv[1]}")
    main(sys.argv[1])
