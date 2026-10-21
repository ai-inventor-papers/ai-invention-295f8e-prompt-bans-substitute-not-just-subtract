#!/usr/bin/env python3
"""GPU tests U1-U7 (run inside the worker so they use the loaded engine).
U1 CRN determinism; U2 hook identity at alpha 0; U4 dose (realised u-component = alpha * n within 1e-3 relative at
blocks 12-23, zero displacement at block 11); U5 base sanity (stop reasons, extraction rate); U6 memory probe;
U7 fence stop invariance (5 slots with and without the fence give the same first code block)."""

from __future__ import annotations

import time
from typing import Any

import numpy as np
import torch

from cfg5 import MAX_NEW_PATH, V_BLOCKS


def _extract(text: str) -> str | None:
    from engine5 import BENCH_FENCE

    m = BENCH_FENCE.search(text)
    return m.group(1) if m else None


def run_tests(W: Any, job: dict[str, Any]) -> dict[str, Any]:
    from engine5 import prefill, prealloc_cache, sample, u_stream
    from sampler5 import rand_dir, run_batch

    task = job["task"]
    ctx = W.context(task)
    out: dict[str, Any] = {"model": W.which, "task": task}
    t0 = time.time()
    if W.which == "base":
        rows = run_batch(ctx, "W1", [("BASE", list(range(10)))], "U5", write=False)
        fr = {}
        for r in rows:
            fr[r["finish_reason"]] = fr.get(r["finish_reason"], 0) + 1
        ext = [_extract(r["text"]) for r in rows]
        ok = [e is not None and "def solve" in e for e in ext]
        out["U5"] = {"finish_reasons": fr, "extraction_rate": sum(ok) / len(ok),
                     "mean_tokens": float(np.mean([r["n_new_tokens"] for r in rows])),
                     "pass": sum(ok) / len(ok) >= 0.3, "examples": [r["text"][:300] for r in rows[:2]]}
        out["seconds"] = round(time.time() - t0, 1)
        return out
    # U1
    a = run_batch(ctx, "W1", [("TWIN", [0, 1, 2, 3])], "U1a", write=False)
    b = run_batch(ctx, "W1", [("TWIN", [0, 1, 2, 3])], "U1b", write=False)
    out["U1"] = {"identical": all(x["token_ids"] == y["token_ids"] for x, y in zip(a, b)), "n": len(a)}
    # U2: alpha 0 under the ban-free unit must equal the twin (same batch shape)
    c = run_batch(ctx, "W1", [("ESC_d95101_a0.0", [0, 1, 2, 3])], "U2", write=False)
    out["U2"] = {"identical": all(x["token_ids"] == y["token_ids"] for x, y in zip(a, c)), "n": len(a)}
    # U4: dose accuracy + no displacement before block 12
    n = ctx.unit("W2", "twin", "banfree")
    u = torch.tensor(rand_dir(95102), device=W.model.device)
    pre, rec = ctx.edited_prefill("W2", "twin", u, 2.0, n, {"arm": "U4"})
    base = ctx.clean_prefill("W2", "twin")
    p = ctx.prompt("W2", "twin")
    cap11 = {}

    def g(h):
        cap11["h"] = h[0, p["p1"]:p["spec_end"]].float().clone()
    from engine5 import block_hooks
    from hooks5 import make_edits
    edits = make_edits("RAND", p["p1"], p["spec_end"], {l: u for l in V_BLOCKS}, n,
                       {l: base["S"][l] for l in V_BLOCKS}, alpha=2.0)
    with torch.no_grad(), block_hooks(W.model, edits, {11: g}):
        W.model.model(input_ids=torch.tensor([p["ids"]], device=W.model.device), use_cache=False)
    cap11c = {}

    def g2(h):
        cap11c["h"] = h[0, p["p1"]:p["spec_end"]].float().clone()
    with torch.no_grad(), block_hooks(W.model, {}, {11: g2}):
        W.model.model(input_ids=torch.tensor([p["ids"]], device=W.model.device), use_cache=False)
    d11 = float((cap11["h"] - cap11c["h"]).abs().max())
    out["U4"] = {"rel_err_along_u_max": max(rec["rel_err_along_u"].values()),
                 "rel_err_by_block": rec["rel_err_along_u"], "block11_max_abs_disp": d11,
                 "pass": max(rec["rel_err_along_u"].values()) <= 1e-2 and d11 == 0.0,
                 "note": "bf16 cast after the fp32 edit bounds the achievable accuracy"}
    del pre
    # U6 memory probe: largest B in (20, 16, 12, 10, 8, 6) that holds prompt 450 + 1,536 new tokens
    pre450 = prefill(W.model, list(p["ids"]) * 3)
    P = pre450["P"]
    fits = {}
    for B in (20, 16, 12, 10, 8, 6):
        try:
            kv = [(K.expand(B, -1, -1, -1), V.expand(B, -1, -1, -1)) for K, V in pre450["kv"]]
            cache = prealloc_cache(kv, P + MAX_NEW_PATH + 1)
            x = torch.full((B, 1), 13, device=W.model.device)
            pos = torch.full((B, 1), P, device=W.model.device)
            with torch.no_grad():
                h = W.model.model(input_ids=x, past_key_values=cache, position_ids=pos, use_cache=True).last_hidden_state
                lg = W.model.lm_head(h[:, -1]).double()
                pr = torch.softmax(lg, -1).cumsum(-1)
            fits[B] = {"ok": True, "peak_gb": round(torch.cuda.max_memory_allocated() / 1e9, 2)}
            del cache, kv, h, lg, pr
        except torch.cuda.OutOfMemoryError:
            fits[B] = {"ok": False}
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()
    out["U6"] = {"prompt_len": P, "fits": fits}
    del pre450
    torch.cuda.empty_cache()
    # U7 fence invariance
    grp = [{"pre": base["pre"], "us": [u_stream(task, "W1", k) for k in range(5)]}]
    base1 = ctx.clean_prefill("W1", "twin")
    grp = [{"pre": base1["pre"], "us": [u_stream(task, "W1", k) for k in range(5)]}]
    r1 = sample(W.model, grp, max_new=1024, fence="bench", tok=W.tok)
    r2 = sample(W.model, grp, max_new=1024, fence=None, tok=W.tok)
    nv = len(W.tok)
    e1 = [_extract(W.tok.decode([t for t in r["token_ids"] if t < nv], skip_special_tokens=True)) for r in r1]
    e2 = [_extract(W.tok.decode([t for t in r["token_ids"] if t < nv], skip_special_tokens=True)) for r in r2]
    out["U7"] = {"identical_code": sum(x == y for x, y in zip(e1, e2)), "n": 5,
                 "fence_reasons": [r["finish_reason"] for r in r1]}
    out["seconds"] = round(time.time() - t0, 1)
    return out
