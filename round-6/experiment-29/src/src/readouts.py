#!/usr/bin/env python3
"""Stage F mechanism readouts (forward passes only, batch 1) on the 50 PN alpha-2 slots of T10 and T2, per precision.

Per slot (task, w, k), with the same PN direction / ban unit / make_edits('RAND') as generation:
 (a) SCALE CHANGE at the 4 distinct quantised linear inputs of blocks 12-35 (attn-in = q/k/v input, o-in, mlp-in =
     gate/up input, down-in), by position class (spec / chat-tail / R): |absmax(pushed) - absmax(clean)| /
     absmax(clean) and the share of rows whose FP8 scale changes (the A8 quantiser applied virtually in A16 runs).
 (b) RE-ROUNDING GAIN ||(Q(x+d) - (x+d)) - (Q(x) - x)|| / ||d|| at the same inputs, and ||Q(x) - x|| / ||x||.
 (c) DIVERGENCE TRAVEL per block 0-35 and class: ||h_pushed - h_clean|| / (alpha * mean n) and the cosine;
     amplification ||dh(l)|| / ||dh(23)|| for l = 24-35 at R.
 (d) OUTPUT DEPARTURE: KL(pushed || clean) of the next-token distribution at R, and the per-token KL over tokens
     1-32 teacher-forced on the W16A16 TWIN sample of that slot (one token sequence shared by every precision).
Clean states at blocks {11, 17, 23, 29, 35} (all positions, bf16) are saved per task/template/precision for the
clean-vs-clean divergence between precisions and the kernel-only floor (W16A16 native vs W16A16mm).
"""

from __future__ import annotations

import json
import time
from typing import Any

import numpy as np
import torch
from loguru import logger

from cfg import V_BLOCKS, append_jsonl, read_jsonl
from cfg_e import RAW_E, RESULTS_DIR, STATES_DIR
from engine_v4 import block_hooks, clear_act_cache
from hooks import make_edits
from qlinear import _resolve
from sampling_v4 import load_norms, pn_direction

LIN_INPUTS = {0: "self_attn.q_proj", 1: "self_attn.o_proj", 2: "mlp.gate_proj", 3: "mlp.down_proj"}
LIN_NAMES_RO = {0: "attn_in", 1: "o_in", 2: "mlp_in", 3: "down_in"}
RO_BLOCKS = list(range(12, 36))
SAVE_BLOCKS = (11, 17, 23, 29, 35)
SLOTS_FILE = RESULTS_DIR / "readouts_slots.jsonl"
N_TF = 32


def q_rows(x: torch.Tensor) -> torch.Tensor:
    """Dequantised e4m3 rows (exp19 activation quantiser), fp32."""
    xs = x.abs().amax(dim=-1, keepdim=True).float().clamp_(min=1e-12) / 448.0
    return (x.float() / xs).clamp_(-448.0, 448.0).to(torch.float8_e4m3fn).float() * xs


@torch.no_grad()
def fwd_capture(model: Any, ids: list[int], edits: dict | None = None) -> dict[str, Any]:
    blocks: dict[int, torch.Tensor] = {}
    lin: dict[tuple[int, int], torch.Tensor] = {}
    hs = []
    for l in RO_BLOCKS:
        for iid, name in LIN_INPUTS.items():
            parent, attr = _resolve(model.model.layers[l], name)
            def pre(mod, args, l=l, iid=iid):
                lin[(l, iid)] = args[0][0].detach().clone()
                return None
            hs.append(getattr(parent, attr).register_forward_pre_hook(pre))

    def cap(l):
        def g(h):
            blocks[l] = h[0].detach().clone()
        return g
    clear_act_cache()
    try:
        with block_hooks(model, edits, {l: cap(l) for l in range(len(model.model.layers))}):
            out = model.model(input_ids=torch.tensor([ids], device=model.device), use_cache=False)
        logits_r = model.lm_head(out.last_hidden_state[:, -1]).float()[0]
    finally:
        for h in hs:
            h.remove()
        clear_act_cache()
    return {"blocks": blocks, "lin": lin, "logits_r": logits_r}


@torch.no_grad()
def teacher_forced_logprobs(model: Any, ids: list[int], tokens: list[int], edits: dict | None = None) -> torch.Tensor:
    """log-probs [len(tokens), V] of the next token at positions P-1 .. P-2+len(tokens) for the sequence ids+tokens."""
    seq = list(ids) + list(tokens)
    P = len(ids)
    clear_act_cache()
    with block_hooks(model, edits, None):
        out = model.model(input_ids=torch.tensor([seq], device=model.device), use_cache=False)
    h = out.last_hidden_state[0, P - 1:P - 1 + len(tokens)]
    lp = torch.log_softmax(model.lm_head(h).float(), dim=-1)
    clear_act_cache()
    return lp


def _classes(a: int, b: int, P: int) -> dict[str, list[int]]:
    return {"spec": list(range(a, b)), "tail": list(range(b, P - 1)), "R": [P - 1]}


def slot_metrics(clean: dict[str, Any], pushed: dict[str, Any], a: int, b: int, P: int, alpha: float,
                 n_mean: float) -> dict[str, Any]:
    cls = _classes(a, b, P)
    out: dict[str, Any] = {"scale_change": {}, "scale_changed_share": {}, "rerounding_gain": {}, "round_err": {}}
    for (l, iid), xc in clean["lin"].items():
        xp = pushed["lin"][(l, iid)]
        key = f"{l}:{LIN_NAMES_RO[iid]}"
        amc = xc.abs().amax(dim=-1).float()
        amp = xp.abs().amax(dim=-1).float()
        rel = (amp - amc).abs() / amc.clamp(min=1e-12)
        chg = (amp != amc).float()
        xcf, xpf = xc.float(), xp.float()
        d = xpf - xcf
        ec = q_rows(xc) - xcf
        ep = q_rows(xp) - xpf
        dn = d.norm(dim=-1)
        gain = (ep - ec).norm(dim=-1) / dn.clamp(min=1e-12)
        rerr = ec.norm(dim=-1) / xcf.norm(dim=-1).clamp(min=1e-12)
        for c, pos in cls.items():
            if not pos:
                continue
            idx = torch.tensor(pos, device=xc.device)
            moved = dn[idx] > 0
            out["scale_change"].setdefault(c, {})[key] = round(float(rel[idx].mean()), 6)
            out["scale_changed_share"].setdefault(c, {})[key] = round(float(chg[idx].mean()), 4)
            out["rerounding_gain"].setdefault(c, {})[key] = (round(float(gain[idx][moved].mean()), 5)
                                                             if bool(moved.any()) else None)
            out["round_err"].setdefault(c, {})[key] = round(float(rerr[idx].mean()), 6)
    div, cos = {}, {}
    for l, hc in clean["blocks"].items():
        hp = pushed["blocks"][l]
        dd = (hp.float() - hc.float()).norm(dim=-1)
        cs = torch.nn.functional.cosine_similarity(hp.float(), hc.float(), dim=-1)
        for c, pos in cls.items():
            if not pos:
                continue
            idx = torch.tensor(pos, device=hc.device)
            div.setdefault(c, {})[str(l)] = round(float(dd[idx].mean()) / (alpha * n_mean), 5)
            cos.setdefault(c, {})[str(l)] = round(float(cs[idx].mean()), 6)
    out["divergence"] = div
    out["cosine"] = cos
    dR = {l: float((pushed["blocks"][l][P - 1].float() - clean["blocks"][l][P - 1].float()).norm())
          for l in clean["blocks"]}
    out["amplification_R"] = {str(l): round(dR[l] / max(dR[23], 1e-12), 4) for l in range(24, 36)}
    lp_p = torch.log_softmax(pushed["logits_r"], -1)
    lp_c = torch.log_softmax(clean["logits_r"], -1)
    out["kl_R"] = round(float((lp_p.exp() * (lp_p - lp_c)).sum()), 6)
    out["argmax_R_changed"] = bool(int(lp_p.argmax()) != int(lp_c.argmax()))
    return out


def twin_tokens_w16(task: str) -> dict[tuple[str, int], list[int]]:
    out = {}
    for r in read_jsonl(RAW_E):
        if r["task"] == task and r["precision"] == "W16A16" and r["arm"] == "TWIN":
            out[(r["template"], int(r["slot"]))] = r["token_ids"][:N_TF]
    return out


def run_readouts(model: Any, tok: Any, prompts: dict, fm: Any, precision: str, tasks: tuple[str, ...],
                 templates: list[str], slots: list[int], deadline: float) -> dict[str, Any]:
    from engine_e import TaskContextE

    fm.set_precision(precision)
    done = {(r["task"], r["precision"], r["template"], r["slot"]) for r in read_jsonl(SLOTS_FILE)}
    n_new = 0
    t0 = time.time()
    for task in tasks:
        tw = twin_tokens_w16(task)
        nm = load_norms(task)
        n_mean = float(np.mean(nm))
        ctx = TaskContextE(model, tok, prompts, task, precision)
        for w in templates:
            if time.time() > deadline:
                logger.warning(f"readouts {precision}: deadline reached")
                return {"n_new": n_new, "stopped": "deadline"}
            todo = [k for k in slots if (task, precision, w, k) not in done]
            if not todo:
                continue
            p = ctx.prompt(w, "twin")
            ids, a, b, P = p["ids"], p["p1"], p["spec_end"], p["P"]
            clean = fwd_capture(model, ids)
            torch.save({l: clean["blocks"][l].cpu() for l in SAVE_BLOCKS},
                       STATES_DIR / f"clean_{task}_{w}_{precision}.pt")
            h_ref = {l: clean["blocks"][l][a:b].float() for l in V_BLOCKS}
            ntab = {l: torch.tensor(nm[j], device=model.device) for j, l in enumerate(V_BLOCKS)}
            rows = []
            for k in todo:
                seed, u = pn_direction(task, "PN_a2", w, k)
                ut = torch.tensor(u, device=model.device)
                edits = make_edits("RAND", a, b, {l: ut for l in V_BLOCKS}, ntab, h_ref, alpha=2.0, log={})
                pushed = fwd_capture(model, ids, edits=edits)
                m = slot_metrics(clean, pushed, a, b, P, 2.0, n_mean)
                del pushed
                toks = tw.get((w, k))
                if toks:
                    lp_c = teacher_forced_logprobs(model, ids, toks)
                    edits2 = make_edits("RAND", a, b, {l: ut for l in V_BLOCKS}, ntab, h_ref, alpha=2.0, log={})
                    lp_p = teacher_forced_logprobs(model, ids, toks, edits=edits2)
                    kl = (lp_p.exp() * (lp_p - lp_c)).sum(-1)
                    m["kl_tf"] = [round(float(x), 6) for x in kl.tolist()]
                    m["kl_tf_mean"] = round(float(kl.mean()), 6)
                    m["tf_tokens_source"] = "W16A16 TWIN sample of this slot"
                else:
                    m["kl_tf"] = None
                rows.append({"task": task, "precision": precision, "template": w, "slot": k, "arm": "PN_a2",
                             "direction_seed": seed, "alpha": 2.0, "n_mean": n_mean, **m})
            append_jsonl(SLOTS_FILE, rows)
            n_new += len(rows)
            del clean
            torch.cuda.empty_cache()
        ctx.clean.clear()
    logger.info(f"readouts {precision}: {n_new} slots in {time.time() - t0:.0f}s")
    return {"n_new": n_new, "seconds": round(time.time() - t0, 1)}


__all__ = ["run_readouts", "teacher_forced_logprobs", "fwd_capture", "json"]
