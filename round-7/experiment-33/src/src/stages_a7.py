#!/usr/bin/env python3
"""GPU stages, part A: unit tests U1-U6 + U8 (+ U9 engine check) and Stage 0 sampling (STEP 3 and STEP 4).

Stage 0 cells per task (CRN T = 1, top-p 1, no top-k, thinking off; slot s uses exp30's stream code_stream(task, s)):
  TWIN      exp30 twin cell, slots 0-19 (slot s uses the noun-0 twin of template SLOT_MAP[s][0]: W1 x8, W2 x8, W3 x4);
            doubles as the engine check against exp30's labels (T2, T03) and as the default-program pool
  F{k}_{Y}  forced family k x every catalogue mode Y, slots 4k..4k+3 (N = 20 per Y pooled over families)
  PAD{k}_{Y} padding twin of every non-default forced prompt, slots 4k..4k+3 (default check, N = 20 per Y)
  BAN_W1-3  ban landing programs, slots 0-9 each;  BAN_W5  the held-out full-ban reference cell, slots 0-29
"""

from __future__ import annotations

import json
import time
from typing import Any

import numpy as np
import torch
from loguru import logger

from cfg import read_jsonl, write_json
from cfg6 import SLOT_MAP
from cfg7 import CATALOGUE7, DEFAULT7, E30, results7
from engine_v4 import block_hooks
from gpu7 import capture_states, code_stream, dev_of, make_edit, prefill7, run_specs, spec_row


def twin_key(task: str, w: str, n: int) -> str:
    return f"{task}|twin|{w}|n{n}"


def ban_key(task: str, w: str) -> str:
    return f"{task}|ban|{w}|-"


def forced_key(task: str, k: int, Y: str) -> str:
    return f"{task}|forced|F{k}|{Y}"


def pad_key(task: str, k: int, Y: str) -> str:
    return f"{task}|padtwin|F{k}|{Y}"


# ------------------------------------------------------------------------------------------------ unit tests
@torch.no_grad()
def stage_utest(model: Any, tok: Any, P7: dict[str, dict[str, Any]]) -> dict[str, Any]:
    from das7 import Site, TFContext, pack, run_blocks, score_ll
    out: dict[str, Any] = {}
    dev = dev_of(model)
    tw, bn = P7[twin_key("T2", "W1", 0)], P7[ban_key("T2", "W1")]
    pos = torch.arange(tw["p1"], tw["spec_end"], device=dev)
    # U1 zero-rank projected edit == unedited (bit-identical logits)
    src = capture_states(model, bn, list(range(36)))
    pre0 = prefill7(model, tw["ids"])
    pre1 = prefill7(model, tw["ids"], edits=make_edit(pos, {20: src[20][:-1]}, "proj",
                                                       B=torch.zeros(0, 4096, device=dev)))
    out["U1_zero_rank_identical"] = bool(torch.equal(pre0["r_logits"], pre1["r_logits"]))
    # U2 full exchange at ALL positions of ALL blocks reproduces the source run (read-position logits)
    allpos = torch.arange(0, tw["P"], device=dev)
    full_src = {}

    def cap_all(l: int):
        def g(h):
            full_src[l] = h[0].clone()
        return g
    from transformers.cache_utils import DynamicCache
    with block_hooks(model, None, {l: cap_all(l) for l in range(36)}):
        model.model(input_ids=torch.tensor([bn["ids"]], device=dev), past_key_values=DynamicCache(), use_cache=True)
    pre_b = prefill7(model, bn["ids"])
    pre2 = prefill7(model, tw["ids"], edits=make_edit(allpos, full_src, "full"))
    d2 = float((pre2["r_logits"] - pre_b["r_logits"]).abs().max())
    out["U2_full_exchange_all_blocks"] = {"max_abs_logit_diff": d2, "top1_equal": bool(
        pre2["r_logits"].argmax() == pre_b["r_logits"].argmax()), "pass": d2 <= 0.5}
    del full_src
    # U3 packed forward vs separate HF forwards of prompt + program
    rows30 = [r for r in read_jsonl(E30 / "data" / "samples_raw.jsonl") if r["task"] == "T2" and r["arm"] == "TWIN"]
    progs = [r["token_ids"][:48] for r in rows30[:6] if len(r["token_ids"]) >= 48]
    pk = pack(tw["ids"], progs, dev)
    h = model.model.embed_tokens(pk["ids"])
    h = run_blocks(model, h, pk, 0, 36)
    llp = score_ll(model, h, pk)[0]
    diffs, tokd = [], []
    for j, pr in enumerate(progs):
        ids = torch.tensor([tw["ids"] + pr], device=dev)
        lg = model(input_ids=ids).logits[0, tw["P"] - 1:tw["P"] - 1 + len(pr)].float()
        lp = torch.log_softmax(lg, -1).gather(-1, torch.tensor(pr, device=dev)[:, None])[:, 0]
        diffs.append(abs(float(lp.sum()) - float(llp[j])))
        # per-token comparison through a 1-program pack
        pk1 = pack(tw["ids"], [pr], dev)
        h1 = run_blocks(model, model.model.embed_tokens(pk1["ids"]), pk1, 0, 36)
        hs = model.model.norm(h1[:, pk1["sc_idx"]])
        lp1 = torch.log_softmax(model.lm_head(hs).float(), -1)[0].gather(-1, pk1["tgt"][:, None])[:, 0]
        tokd.append(float((lp1 - lp).abs().max()))
    out["U3_packed_vs_separate"] = {"per_program_abs_diff": [round(x, 4) for x in diffs],
                                    "max_program_diff": max(diffs), "mean_program_diff": float(np.mean(diffs)),
                                    "max_token_diff_single_pack": max(tokd),
                                    "pass": max(diffs) <= 0.15 and float(np.mean(diffs)) <= 0.15}
    # U4 cached upper forward from site output == full packed forward with the same edit
    site = Site([18])
    targets = {"dijkstra": progs[:3], "bf_spfa": progs[3:6]}
    ctx = TFContext(model, P7, targets, site, {"bf_spfa": ["bf_spfa"]}, "dijkstra")
    Bk = torch.linalg.qr(torch.randn(4096, 8, generator=torch.Generator().manual_seed(1), dtype=torch.float64))[0].T
    Bk = Bk.float().to(dev).contiguous()
    c_cached = ctx.contrast_rows(tw["key"], "bf_spfa", [{"src": bn["key"], "B": Bk}, {"none": True}])
    ctx_full = TFContext(model, P7, targets, Site([18]), {"bf_spfa": ["bf_spfa"]}, "dijkstra")
    ctx_full.site.start = 0
    c_full = ctx_full.contrast_rows(tw["key"], "bf_spfa", [{"src": bn["key"], "B": Bk}, {"none": True}])
    d4 = float((c_cached["C"] - c_full["C"]).abs().max())
    out["U4_cached_vs_full"] = {"max_abs_contrast_diff": d4, "C_edit": float(c_cached["C"][0]),
                                "C_none": float(c_cached["C"][1]), "pass": d4 <= 0.05}
    ctx.free()
    ctx_full.free()
    # U8 memory probe (one training micro-batch with grad)
    torch.cuda.reset_peak_memory_stats()
    ctx = TFContext(model, P7, {"dijkstra": progs[:5], "bf_spfa": progs[:5]}, Site([18]), {"bf_spfa": ["bf_spfa"]},
                    "dijkstra")
    from das7 import DASMap
    das = DASMap(16, 1).to(dev)
    t0 = time.time()
    with torch.enable_grad():
        o = ctx.contrast_rows(tw["key"], "bf_spfa", [{"src": bn["key"], "B": das.basis()}], grad=True)
        (-o["C"][0]).backward()
    gnorm = float(sum(p.grad.norm() ** 2 for p in das.parameters() if p.grad is not None) ** 0.5)
    out["U8_memory"] = {"peak_GB_train_microbatch": round(torch.cuda.max_memory_allocated() / 1e9, 2),
                        "seconds_train_microbatch": round(time.time() - t0, 2), "grad_norm": gnorm,
                        "free_GB": round(torch.cuda.mem_get_info()[0] / 1e9, 2)}
    out["U7a_grad_finite_nonzero"] = bool(np.isfinite(gnorm) and gnorm > 0)
    ctx.free()
    del das
    torch.cuda.empty_cache()
    return out


def stage_utest_gen(model: Any, tok: Any, P7: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """U5 (random orthonormal full-rank basis == full exchange, 10 CRN slots) and U6 (CRN determinism)."""
    task = "T2"
    dev = dev_of(model)
    tw, bn = P7[twin_key(task, "W5", 0)], P7[ban_key(task, "W5")]
    pos = torch.arange(tw["p1"], tw["spec_end"], device=dev)
    src = capture_states(model, bn, [18])
    Q = torch.linalg.qr(torch.randn(4096, 4096, generator=torch.Generator().manual_seed(5), dtype=torch.float64))[0]
    Q = Q.T.float().to(dev).contiguous()
    pre_full = prefill7(model, tw["ids"], edits=make_edit(pos, {18: src[18][:-1]}, "full"))
    pre_rot = prefill7(model, tw["ids"], edits=make_edit(pos, {18: src[18][:-1]}, "proj", B=Q))
    dl = float((pre_full["r_logits"] - pre_rot["r_logits"]).abs().max())
    specs = []
    for s in range(10):
        specs.append(spec_row(task, "UT_FULL18", "UTEST", s, tw, pre=pre_full, stage="utest"))
        specs.append(spec_row(task, "UT_ROT18", "UTEST", s, tw, pre=pre_rot, stage="utest"))
        specs.append(spec_row(task, "UT_DET_A", "UTEST", s, tw, pre=pre_full, stage="utest"))
    run_specs(model, tok, task, specs, "UTEST")
    rows = {r["sample_id"]: r for r in read_jsonl(results7("../data/samples_raw.jsonl"))} if False else None
    from cfg7 import SAMPLES7
    rows = {r["sample_id"]: r for r in read_jsonl(SAMPLES7) if r["cell"] == "UTEST"}
    same_rot = sum(rows[f"{task}|UT_FULL18|{s}"]["token_ids"] == rows[f"{task}|UT_ROT18|{s}"]["token_ids"]
                   for s in range(10))
    same_det = sum(rows[f"{task}|UT_FULL18|{s}"]["token_ids"] == rows[f"{task}|UT_DET_A|{s}"]["token_ids"]
                   for s in range(10))
    return {"U5_fullrank_rotation_equals_exchange": {"max_abs_logit_diff_read_pos": dl,
                                                     "identical_token_streams_of_10": int(same_rot)},
            "U6_crn_determinism": {"identical_token_streams_of_10": int(same_det), "pass": same_det == 10,
                                   "decode_hooks": "edit hooks are registered only inside the prefill context "
                                                   "(engine_v4.block_hooks), so no decode step is hooked"}}


# ------------------------------------------------------------------------------------------------ stage 0
def stage0_specs(task: str, P7: dict[str, dict[str, Any]], pre_cache: dict[str, Any], model: Any) -> list[dict]:
    def pre_of(key: str) -> dict[str, Any]:
        if key not in pre_cache:
            pre_cache[key] = prefill7(model, P7[key]["ids"])
        return pre_cache[key]

    specs: list[dict[str, Any]] = []
    D = DEFAULT7[task]
    for s in range(20):
        w = SLOT_MAP[s][0]
        k = twin_key(task, w, 0)
        specs.append(spec_row(task, "TWIN", "TWIN", s, P7[k], make=lambda k=k: (pre_of(k), None), stage="stage0"))
    for kf in range(5):
        for Y in CATALOGUE7[task]:
            fk = forced_key(task, kf, Y)
            for j in range(4):
                s = 4 * kf + j
                specs.append(spec_row(task, f"F{kf}_{Y}", "FORCED", s, P7[fk], make=lambda k=fk: (pre_of(k), None),
                                      stage="stage0", Y_source=Y))
                if Y != D:
                    pk_ = pad_key(task, kf, Y)
                    specs.append(spec_row(task, f"PAD{kf}_{Y}", "PADCHK", s, P7[pk_],
                                          make=lambda k=pk_: (pre_of(k), None), stage="stage0", Y_source=Y))
    for w in ("W1", "W2", "W3"):
        bk = ban_key(task, w)
        for s in range(10):
            specs.append(spec_row(task, f"BAN_{w}", "BAN", s, P7[bk], make=lambda k=bk: (pre_of(k), None),
                                  stage="stage0"))
    bk = ban_key(task, "W5")
    for s in range(30):
        specs.append(spec_row(task, "BAN_W5", "BAN_W5", s, P7[bk], make=lambda k=bk: (pre_of(k), None),
                              stage="stage0"))
    return specs


def run_stage0(model: Any, tok: Any, P7: dict[str, dict[str, Any]], task: str) -> int:
    pre_cache: dict[str, Any] = {}
    specs = stage0_specs(task, P7, pre_cache, model)
    t0 = time.time()
    n = run_specs(model, tok, task, specs, f"S0:{task}")
    pre_cache.clear()
    torch.cuda.empty_cache()
    logger.info(f"stage0 {task}: {n} rows in {time.time() - t0:.0f}s")
    return n


def engine_check(task: str) -> dict[str, Any]:
    """U9: per-slot TWIN labels (slots 0-19) vs exp30's labels of the same slots."""
    from cfg7 import LABELS7
    mine = {r["slot_index"]: r for r in read_jsonl(LABELS7) if r["task"] == task and r["arm"] == "TWIN"}
    ref = {r["slot_index"]: r for r in read_jsonl(E30 / "data" / "labels.jsonl")
           if r["task"] == task and r["arm"] == "TWIN"}
    pairs = [(mine[s]["label"], ref[s]["label"]) for s in range(20) if s in mine and s in ref]
    agree = sum(a == b for a, b in pairs)
    return {"task": task, "n": len(pairs), "agree": agree, "share": agree / max(1, len(pairs)),
            "pass_0.95": agree / max(1, len(pairs)) >= 0.95,
            "mine": dict(sorted(__import__("collections").Counter(a for a, _ in pairs).items())),
            "exp30": dict(sorted(__import__("collections").Counter(b for _, b in pairs).items()))}
