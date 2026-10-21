#!/usr/bin/env python3
"""Ban-free unit calibration probe (before commit #1): what the committed push unit does to twin generations on
T2 and T03 at alpha 1 and 2 (8 random directions each), against 8 unpushed twin rows. Diagnostic only."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import torch
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg import BAND, CAPTURE_BLOCKS, QWEN_DEFAULT, RESULTS_DIR, setup_logging, write_json
import engine_gemma as EG
import prompts_gemma as PG
from units import unit_n

setup_logging("unit_probe")
tok, model, info = EG.load_model()
out = {}
for task in ("T2", "T03", "T05"):
    tw = PG.p_twin(task, QWEN_DEFAULT[task], "W1")
    ids, a, b = tw["ids"], tw["spec_start"], tw["spec_end"]
    clean = EG.clean_states(model, ids, a, b, CAPTURE_BLOCKS)
    n = unit_n(clean["S"])
    # outlier-excluded norms (top-5 channels by mean |h| over spec positions, per block) -- diagnostic
    nox = {}
    for l in BAND:
        h = clean["S"][l]
        top = h.abs().mean(0).topk(5).indices
        m = torch.ones(h.shape[1], dtype=torch.bool, device=h.device); m[top] = False
        nox[l] = float(h[:, m].norm(dim=-1).mean() / h.norm(dim=-1).mean())
    B = 24
    alphas = [0.0] * 8 + [1.0] * 8 + [2.0] * 8
    U = torch.zeros(B, EG.D_MODEL, device="cuda")
    for i in range(8, 24):
        U[i] = torch.tensor(EG.seed_dir(9001 + (i % 8)), device="cuda")
    ps = {"U": U, "alpha": torch.tensor(alphas, device="cuda"), "n": n, "h_ref": {l: clean["S"][l] for l in BAND},
          "a": a, "b": b, "band": BAND}
    pre = EG.prefill_single(model, ids, B, push=ps, capture_ref=clean)
    Us = np.stack([EG.u_stream(task, "probe", k % 8, n=700) for k in range(B)])
    res = EG.decode(model, tok, pre, Us, np.ones(B), 700)
    out[task] = {"nonmassive_norm_fraction_by_block": nox,
                 "rows": [{"alpha": al, "text": r["text"][:400], "n_tokens": r["n_tokens"], "finish": r["finish_reason"]}
                          for al, r in zip(alphas, res)]}
    for al, r in zip(alphas, res):
        logger.info(f"{task} a={al} [{r['finish_reason']},{r['n_tokens']}] {r['text'][:160]!r}")
write_json(RESULTS_DIR / "unit_probe.json", out)
