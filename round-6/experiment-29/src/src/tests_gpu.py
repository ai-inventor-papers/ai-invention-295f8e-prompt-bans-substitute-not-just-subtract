#!/usr/bin/env python3
"""GPU tests U1-U8 (results/tests_gpu.json). Nothing decisive runs until they pass or a deviation is logged."""

from __future__ import annotations

import time
from typing import Any

import numpy as np
import torch
from loguru import logger

from cfg import NORM_BLOCKS, V_BLOCKS, read_jsonl
from cfg_e import K10, RESULTS_DIR
from engine_v4 import _ACT_CACHE, clear_act_cache, prefill, sample, u_stream
from qlinear import LIN_NAMES, MODE, QLinear, _resolve, quant_e4m3_rows, quant_weight
from sampling_v4 import fence_for, max_new_for, pn_direction

CAP_BLOCKS = (0, 12, 23, 35)
CAP_LINS = ("self_attn.q_proj", "self_attn.o_proj", "mlp.gate_proj", "mlp.down_proj")


def capture_linear_inputs(model: Any, ids: list[int], n_rows: int = 200) -> dict[tuple[int, str], torch.Tensor]:
    got: dict[tuple[int, str], torch.Tensor] = {}
    hs = []
    for l in CAP_BLOCKS:
        for name in CAP_LINS:
            parent, attr = _resolve(model.model.layers[l], name)
            def pre(mod, args, l=l, name=name):
                got[(l, name)] = args[0][0, :n_rows].detach().clone()
                return None
            hs.append(getattr(parent, attr).register_forward_pre_hook(pre))
    try:
        prefill(model, ids)
    finally:
        for h in hs:
            h.remove()
    return got


def u1_per_linear(model: Any, fm: Any, ids: list[int], precisions: list[str]) -> dict[str, Any]:
    """Row-norm relative error of every precision's linear against a float64 reference of the same quantised math."""
    fm.set_precision("W16A16")
    X = capture_linear_inputs(model, ids)
    out: dict[str, Any] = {}
    real_out: dict[tuple[int, str], torch.Tensor] = {}
    emu_out: dict[tuple[int, str], torch.Tensor] = {}
    for prec in precisions:
        fm.set_precision(prec)
        errs = []
        for (l, name), x in X.items():
            parent, attr = _resolve(model.model.layers[l], name)
            mod = getattr(parent, attr)
            clear_act_cache()
            with torch.no_grad():
                y = mod(x[None])[0].double()
            W = fm.cpu[(l, name)].weight.data.to(x.device)
            wq, s = quant_weight(W)
            xq, xs = quant_e4m3_rows(x)
            Wd = wq.double() * s.t().double() if prec in ("W8A8", "W8A16", "W8A8REAL") else W.double()
            Xd = xq.double() * xs.double() if prec in ("W8A8", "W16A8", "W8A8REAL") else x.double()
            yref = Xd @ Wd.t()
            rel = ((y - yref).norm(dim=1) / yref.norm(dim=1).clamp(min=1e-30)).cpu().numpy()
            errs.append({"block": l, "linear": name, "median": float(np.median(rel)), "max": float(rel.max())})
            if prec == "W8A8REAL":
                real_out[(l, name)] = y.float()
            if prec == "W8A8":
                emu_out[(l, name)] = y.float()
        out[prec] = {"median_of_medians": float(np.median([e["median"] for e in errs])),
                     "max": float(max(e["max"] for e in errs)), "per_linear": errs}
    if real_out and emu_out:
        cmp = []
        for k in real_out:
            a, b = emu_out[k], real_out[k]
            cmp.append({"block": k[0], "linear": k[1], "frac_identical_bf16": float((a == b).float().mean()),
                        "rel_diff": float((a - b).norm() / b.norm())})
        out["EMU_vs_REAL"] = {"frac_identical_bf16_mean": float(np.mean([c["frac_identical_bf16"] for c in cmp])),
                              "rel_diff_max": float(max(c["rel_diff"] for c in cmp)), "per_linear": cmp}
    del X
    return out


def _batch(ctx: Any, w: str, spec: list[tuple[str, list[int]]], alpha0: bool = False) -> list[dict[str, Any]]:
    """Minimal generation of one fixed-shape batch (no file writes) -> token ids per row."""
    model, tok, task = ctx.model, ctx.tok, ctx.task
    groups = []
    for arm, ks in spec:
        if arm == "TWIN":
            groups.append({"pre": ctx.clean_prefill(w, "twin")["pre"], "us": [u_stream(task, w, k) for k in ks]})
        else:
            alpha = 0.0 if alpha0 else {"PN_a0.5": 0.5, "PN_a1": 1.0, "PN_a2": 2.0}[arm]
            for k in ks:
                _, u = pn_direction(task, arm, w, k)
                pre, _ = ctx.pushed_prefill(w, torch.tensor(u, device=model.device), alpha, {"arm": arm, "slot": k})
                groups.append({"pre": pre, "us": [u_stream(task, w, k)]})
    res = sample(model, groups, max_new=max_new_for(task), fence=fence_for(task), tok=tok)
    return res


def u2_u3_u5(model: Any, tok: Any, prompts: dict, fm: Any, precisions: list[str], B: int) -> dict[str, Any]:
    from engine_e import TaskContextE

    out: dict[str, Any] = {}
    half = B // 2
    ks = list(range(half))
    for prec in precisions:
        fm.set_precision(prec)
        ctx = TaskContextE(model, tok, prompts, "T03", prec)
        t0 = time.time()
        r1 = _batch(ctx, "W1", [("TWIN", ks), ("PN_a0.5", ks)])
        r2 = _batch(ctx, "W1", [("TWIN", ks), ("PN_a0.5", ks)])
        u2 = all(a["token_ids"] == b["token_ids"] for a, b in zip(r1, r2))
        r3 = _batch(ctx, "W1", [("TWIN", ks), ("PN_a2", ks)])     # batch-mates changed
        u3 = sum(a["token_ids"] == b["token_ids"] for a, b in zip(r1[:half], r3[:half]))
        r4 = _batch(ctx, "W1", [("TWIN", ks), ("PN_a1", ks)], alpha0=True)   # alpha = 0 edit == clean prefill
        u5 = sum(a["token_ids"] == b["token_ids"] for a, b in zip(r1[:half], r4[half:]))
        out[prec] = {"U2_crn_determinism": bool(u2), "U3_row_independence": f"{u3}/{half}",
                     "U3_pass": u3 == half, "U5_alpha0_equals_clean": f"{u5}/{half}", "U5_pass": u5 == half,
                     "seconds": round(time.time() - t0, 1)}
        logger.info(f"U2/U3/U5 {prec}: {out[prec]}")
        ctx.clean.clear()
    return out


def u4_hook_accuracy(model: Any, tok: Any, prompts: dict, fm: Any, precisions: list[str]) -> dict[str, Any]:
    from engine_e import TaskContextE

    out = {}
    for prec in precisions:
        fm.set_precision(prec)
        ctx = TaskContextE(model, tok, prompts, "T2", prec)
        worst, comp_ratio = 0.0, []
        for k in range(3):
            _, u = pn_direction("T2", "PN_a2", "W1", k)
            _, rec = ctx.pushed_prefill("W1", torch.tensor(u, device=model.device), 2.0, {"arm": "PN_a2", "slot": k})
            worst = max(worst, max(rec["rel_err_along_u"].values()))
            comp_ratio.append(rec["u_component_mean"]["12"] / rec["target_mean"]["12"])
        out[prec] = {"rel_err_along_u_max": worst, "U4_pass": worst < 1e-2,
                     "u_component_over_target_b12": [round(c, 5) for c in comp_ratio]}
        ctx.clean.clear()
    return out


def u6_floor(model: Any, tok: Any, prompts: dict, fm: Any) -> dict[str, Any]:
    """W8A16 == FAM_W8 with act_q off (same code path); W16A16mm vs native W16A16: max |delta logit| at R and the
    per-token KL over 32 teacher-forced tokens (the kernel-only floor)."""
    from readouts import teacher_forced_logprobs

    p = prompts[("T2", "W1", "twin")]
    out: dict[str, Any] = {}
    fm.set_precision("W16A16")
    r_nat = prefill(model, p["ids"])["r_logits"]
    ctx_tokens = None
    rows = [r for r in read_jsonl(RESULTS_DIR.parent / "inputs" / "exp19" / "data" / "samples_raw.jsonl")
            if r["sample_id"] == "T2|TWIN|W1|0"]
    if rows:
        tid = rows[0]["token_ids"]
        ctx_tokens = (tid if isinstance(tid, list) else __import__("json").loads(tid))[:32]
    lp_nat = teacher_forced_logprobs(model, p["ids"], ctx_tokens) if ctx_tokens else None
    fm.set_precision("W16A16mm")
    r_mm = prefill(model, p["ids"])["r_logits"]
    lp_mm = teacher_forced_logprobs(model, p["ids"], ctx_tokens) if ctx_tokens else None
    out["W16A16mm_vs_native"] = {"max_abs_delta_logit_R": float((r_nat - r_mm).abs().max())}
    if lp_nat is not None:
        kl = (lp_nat.exp() * (lp_nat - lp_mm)).sum(-1)
        out["W16A16mm_vs_native"].update({"kl_per_token_mean": float(kl.mean()), "kl_per_token_max": float(kl.max())})
    fm.set_precision("W8A16")
    r_a16 = prefill(model, p["ids"])["r_logits"]
    fm.set_precision("W8A8")
    MODE["act_q"] = False
    r_off = prefill(model, p["ids"])["r_logits"]
    MODE["act_q"] = True
    out["W8A16_vs_W8_actq_off"] = {"identical": bool(torch.equal(r_a16, r_off))}
    return out


def u8_timing(model: Any, tok: Any, prompts: dict, fm: Any, precisions: list[str], B: int) -> dict[str, Any]:
    out = {}
    p = prompts[("T2", "W1", "twin")]
    for prec in precisions:
        fm.set_precision(prec)
        torch.cuda.synchronize()
        t0 = time.time()
        pre = prefill(model, p["ids"])
        torch.cuda.synchronize()
        t_pre = time.time() - t0
        groups = [{"pre": pre, "us": [np.full(1024, 0.5) for _ in range(B)]}]
        torch.cuda.synchronize()
        t0 = time.time()
        res = sample(model, groups, max_new=33, fence=None, tok=tok)
        torch.cuda.synchronize()
        out[prec] = {"prefill_s": round(t_pre, 4), "decode_step_s": round((time.time() - t0) / res[0]["steps"], 4)}
    return out


def run_all(model: Any, tok: Any, prompts: dict, fm: Any, B: int, real: bool) -> dict[str, Any]:
    precs = ["W8A8", "W8A16", "W16A8", "W16A16"]
    res: dict[str, Any] = {"B": B}
    t0 = time.time()
    res["U1_per_linear"] = u1_per_linear(model, fm, prompts[("T2", "W1", "twin")]["ids"],
                                         precs + ["W16A16mm"] + (["W8A8REAL"] if real else []))
    res["U6_flags_and_floor"] = u6_floor(model, tok, prompts, fm)
    res["U4_hook_accuracy"] = u4_hook_accuracy(model, tok, prompts, fm, precs)
    res["U2_U3_U5"] = u2_u3_u5(model, tok, prompts, fm, ["W8A8", "W16A16"], B)
    res["U8_timing"] = u8_timing(model, tok, prompts, fm, precs + (["W8A8REAL"] if real else []), B)
    res["seconds"] = round(time.time() - t0, 1)
    res["all_pass"] = bool(all(v["U4_pass"] for v in res["U4_hook_accuracy"].values())
                           and all(v["U2_crn_determinism"] and v["U3_pass"] and v["U5_pass"]
                                   for v in res["U2_U3_U5"].values())
                           and res["U6_flags_and_floor"]["W8A16_vs_W8_actq_off"]["identical"])
    _ACT_CACHE.update(x=None, xq=None, xs=None)
    return res
