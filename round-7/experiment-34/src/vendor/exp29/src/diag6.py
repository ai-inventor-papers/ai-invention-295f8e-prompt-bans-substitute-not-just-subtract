#!/usr/bin/env python3
"""Teacher-forced diagnostics (non-decisive), run inside each weight-set process for its engines.

KL        20 exp22 twin programs per task (T10, T2; W1-W5 x k 0-3): per generated position the engine's log-softmax.
          Weight set B stores BF16's top-512 log-probs (cache/kl_ref_d.npz) and computes KL(c || d) exactly in-process;
          weight set Q computes KL(e || d) for e in {a, b} on e's top-64 tokens against the stored BF16 top-512
          (tokens outside it get BF16's 512th log-prob: an upper bound on p_d, so the reported KL is a lower bound;
          the uncovered mass of p_e is reported). Argmax disagreement with BF16 per position.
FIDELITY  40 exp22 FP8 rows (TWIN k 0-1 + POP alpha 2 directions 9101-9110 k 0, T10 and T2) teacher-forced (the POP
          rows with the same prefill edit) through the engine; sum of generated-token log-probs vs exp22's sampled
          logprob_sum. Pre-registered: median |diff| under a <= 0.25 x the median under d, else EMULATION_INFIDELITY.
INDUCED   alpha 2 POP pushes, 3 slots (W1-W3, k 0) x 4 directions (9101-9104) per task, on the engine's OWN twin
          program at the slot (identical tokens in the pushed and the twin pass): per block, delta = (h_push - h_twin)
          - nominal (nominal = alpha n[l,p] u at blocks 12-23, p in S; 0 elsewhere); median ||delta|| over <= 32
          evenly spaced positions of S, at R, and at generated positions 1-32, in ban units (/ mean_p n).
ROUNDING  at the 4 linear-input sites of every block (qkv-in, o-in, gateup-in, down-in), same passes:
          RMS(x - dq(q(x))) / RMS(x); ||r_push - r_twin|| / ||x_push - x_twin|| (r = x - dq(q(x))); the fraction of
          rows whose per-token scale s_x changes, median |ds_x| / s_x, and the fraction whose absmax channel changes.
          Blocks 0-12 must show x_push == x_twin exactly (the edit is at block outputs 12-23).
"""

from __future__ import annotations

import time
from typing import Any

import numpy as np
import torch
from loguru import logger

import c6  # noqa: F401
from c6 import CACHE, DEFAULTS, E22, RESULTS, read_jsonl, write_json, read_json

SITES = {"qkv_in": ("self_attn", "q_proj"), "o_in": ("self_attn", "o_proj"), "gateup_in": ("mlp", "gate_proj"),
         "down_in": ("mlp", "down_proj")}
TOPK_REF = 512
TOPK_E = 64


def _logprobs(model: Any, ids: list[int], P: int, edits: dict | None = None) -> torch.Tensor:
    """Teacher-forced log-softmax (fp64 softmax like the sampler) at positions P-1 .. len(ids)-2 -> [n_gen, V] fp32."""
    import engine as VE

    inp = torch.tensor([ids], device=model.device)
    VE.clear_act_cache()
    with VE.block_hooks(model, edits, None):
        h = model.model(input_ids=inp, use_cache=False).last_hidden_state[0, P - 1:len(ids) - 1]
    out = []
    for i in range(0, h.shape[0], 128):
        lg = model.lm_head(h[i:i + 128]).double()
        out.append(torch.log_softmax(lg, dim=-1).float())
    VE.clear_act_cache()
    return torch.cat(out, 0)


def _edits_for(ctx: Any, w: str, seed: int, alpha: float) -> dict:
    from ctx4 import ban_unit, push_spec, rand_dir
    from hooks4 import make_edits_v4

    tw = ctx.twin(w)
    spec = push_spec(ctx.dev, rand_dir(seed), ban_unit(ctx.task), alpha)
    import cfg4
    return make_edits_v4("TARGET", tw["a"], tw["b"], spec["U"], spec["M"], {l: tw["S"][l] for l in cfg4.EDIT_BLOCKS})


def _exp22_rows(task: str) -> dict[tuple, dict[str, Any]]:
    return {(r["template"], r["arm"], int(r["sample_id"])): r for r in read_jsonl(E22 / "samples_raw.jsonl")
            if r["task"] == task and r["family"] in ("TWIN", "POP")}


@torch.no_grad()
def kl_and_fidelity(model: Any, prompts: dict, engines: tuple[str, ...], weight_set: str) -> dict[str, Any]:
    import engines as EN
    from ctx4 import TaskCtx

    res: dict[str, Any] = {}
    ref_path = CACHE / "kl_ref_d.npz"
    ref_store: dict[str, np.ndarray] = {}
    if weight_set == "Q" and ref_path.exists():
        z = np.load(ref_path)
        ref_store = {k: z[k] for k in z.files}
    for task in ("T10", "T2"):
        ex = _exp22_rows(task)
        progs = [(w, k) for w in ("W1", "W2", "W3", "W4", "W5") for k in range(4)]
        kl_stats = {e: {"kl": [], "argmax_dis": [], "uncovered": []} for e in engines}
        for (w, k) in progs:
            r = ex[(w, "TWIN", k)]
            p = prompts[f"{task}|twin|-|{w}|-"]
            ids = p["ids"] + r["token_ids"]
            P = p["P"]
            lps = {}
            for e in engines:
                EN.set_mode(e)
                lps[e] = _logprobs(model, ids, P)
            key = f"{task}|{w}|{k}"
            if weight_set == "B":
                d = lps["d"]
                v, i = d.topk(TOPK_REF, dim=-1)
                ref_store[key + "|v"] = v.cpu().numpy().astype(np.float16)
                ref_store[key + "|i"] = i.cpu().numpy().astype(np.int32)
                ref_store[key + "|argmax"] = d.argmax(-1).cpu().numpy().astype(np.int32)
                for e in engines:
                    if e == "d":
                        continue
                    pe = lps[e].exp()
                    kl = (pe * (lps[e] - d)).sum(-1)
                    kl_stats[e]["kl"] += kl.cpu().tolist()
                    kl_stats[e]["argmax_dis"] += (lps[e].argmax(-1) != d.argmax(-1)).float().cpu().tolist()
                    kl_stats[e]["uncovered"] += [0.0] * kl.numel()
            else:
                if key + "|v" not in ref_store:
                    continue
                rv = torch.tensor(ref_store[key + "|v"].astype(np.float32), device=model.device)
                ri = torch.tensor(ref_store[key + "|i"].astype(np.int64), device=model.device)
                ram = torch.tensor(ref_store[key + "|argmax"].astype(np.int64), device=model.device)
                for e in engines:
                    le = lps[e]
                    ve, ie = le.topk(TOPK_E, dim=-1)
                    # p_d at e's top tokens: look up in d's top-512, else d's 512th value (upper bound)
                    match = (ie[:, :, None] == ri[:, None, :])
                    found = match.any(-1)
                    pos = match.float().argmax(-1)
                    ld = torch.where(found, rv.gather(1, pos), rv[:, -1:].expand_as(ve))
                    pe = ve.exp()
                    kl = (pe * (ve - ld)).sum(-1)
                    kl_stats[e]["kl"] += kl.cpu().tolist()
                    kl_stats[e]["argmax_dis"] += (le.argmax(-1) != ram).float().cpu().tolist()
                    kl_stats[e]["uncovered"] += (1 - pe.sum(-1)).cpu().tolist()
            del lps
        for e in engines:
            if e == "d" or not kl_stats[e]["kl"]:
                continue
            a = np.array(kl_stats[e]["kl"])
            res.setdefault("KL", {}).setdefault(e, {})[task] = {
                "n_positions": int(a.size), "mean_kl_vs_bf16": float(a.mean()), "median_kl": float(np.median(a)),
                "p90_kl": float(np.percentile(a, 90)), "argmax_disagreement": float(np.mean(kl_stats[e]["argmax_dis"])),
                "mean_uncovered_mass": float(np.mean(kl_stats[e]["uncovered"])),
                "method": "exact in-process" if weight_set == "B" else "top-64 of e vs stored BF16 top-512 (lower bound)"}
        # FIDELITY: exp22's own sampled programs
        fid = {e: [] for e in engines if e in ("a", "d", "b", "c")}
        ctx = TaskCtx(model, prompts, task)
        sel = [(w, "TWIN", k) for w in ("W1", "W2", "W3", "W4", "W5") for k in (0, 1)] + \
              [(w, f"POP_d{s}_a2.0", 0) for s, w in zip(range(9101, 9111), ["W1", "W2", "W3", "W4", "W5"] * 2)]
        for (w, arm, k) in sel:
            r = ex[(w, arm, k)]
            p = prompts[f"{task}|twin|-|{w}|-"]
            ids = p["ids"] + r["token_ids"]
            for e in fid:
                EN.set_mode(e)
                ctx.release()
                edits = _edits_for(ctx, w, int(r["direction_seed"]), 2.0) if arm != "TWIN" else None
                lp = _logprobs(model, ids, p["P"], edits)
                tok_lp = lp.gather(1, torch.tensor(r["token_ids"], device=model.device)[:, None])[:, 0]
                fid[e].append(abs(float(tok_lp.double().sum()) - float(r["logprob_sum"])))
            ctx.release()
        for e, v in fid.items():
            res.setdefault("FIDELITY", {}).setdefault(e, {})[task] = {
                "n": len(v), "median_abs_diff": float(np.median(v)), "mean_abs_diff": float(np.mean(v)),
                "max_abs_diff": float(np.max(v))}
    if weight_set == "B":
        np.savez_compressed(ref_path, **ref_store)
    return res


@torch.no_grad()
def induced_and_rounding(model: Any, prompts: dict, engine: str, tasks=("T10", "T2"), n_slots: int = 3,
                         seeds=(9101, 9102, 9103, 9104), alpha: float = 2.0) -> dict[str, Any]:
    import engine as VE
    import engines as EN
    from ctx4 import TaskCtx, ban_unit, rand_dir
    from rows6 import engine_rows
    from gen import raw_path

    EN.set_mode(engine)
    out: dict[str, Any] = {}
    nL = len(model.model.layers)
    for task in tasks:
        own = {(r["template"], int(r["sample_id"])): r for r in read_jsonl(raw_path(engine))
               if r["task"] == task and r["arm"] == "TWIN"}
        if engine == "a" and not own:
            own = {(r["template"], int(r["sample_id"])): r for r in read_jsonl(E22 / "samples_raw.jsonl")
                   if r["task"] == task and r["arm"] == "TWIN"}
        n = ban_unit(task)
        mean_n = float(n.mean())
        ctx = TaskCtx(model, prompts, task)
        acc = {"S": [[] for _ in range(nL)], "R": [[] for _ in range(nL)], "G": [[] for _ in range(nL)]}
        rnd = {s: {k: [[] for _ in range(nL)] for k in ("rel_rms", "amp", "scale_changed", "ds_rel", "argmax_changed")}
               for s in SITES}
        exact_early = True
        for w in ("W1", "W2", "W3")[:n_slots]:
            r = own.get((w, 0))
            if r is None:
                continue
            p = prompts[f"{task}|twin|-|{w}|-"]
            ids = p["ids"] + r["token_ids"][:32]
            P, a, b = p["P"], p["p1"], p["spec_end"]
            step_s = max(1, -(-(b - a) // 32))            # <= 32 task-spec positions (memory on the 16 GB card)
            s_idx = list(range(0, b - a, step_s))
            pos = torch.tensor([a + i for i in s_idx] + [P - 1] + list(range(P, min(P + 32, len(ids)))),
                               device=model.device)
            nS = len(s_idx)
            # twin pass: block outputs + linear inputs at pos
            hs_t: dict[int, torch.Tensor] = {}
            xs_t: dict[tuple, torch.Tensor] = {}
            hooks = []

            def cap_out(l):
                def f(h):
                    hs_t[l] = h[0, pos].float().clone()
                return f

            def cap_in(l, s, store):
                def pre(m, args):
                    store[(l, s)] = args[0][0, pos].clone()
                return pre
            for l in range(nL):
                for s, (sub, lin) in SITES.items():
                    hooks.append(getattr(getattr(model.model.layers[l], sub), lin).register_forward_pre_hook(
                        cap_in(l, s, xs_t)))
            VE.clear_act_cache()
            with VE.block_hooks(model, None, {l: cap_out(l) for l in range(nL)}):
                model.model(input_ids=torch.tensor([ids], device=model.device), use_cache=False)
            for h in hooks:
                h.remove()
            ctx.release()
            tw = ctx.twin(w)
            for seed in seeds:
                u = torch.tensor(rand_dir(seed), device=model.device)
                edits = _edits_for(ctx, w, seed, alpha)
                hs_p: dict[int, torch.Tensor] = {}
                xs_p: dict[tuple, torch.Tensor] = {}
                hooks = []

                def cap_out_p(l):
                    def f(h):
                        hs_p[l] = h[0, pos].float().clone()
                    return f
                for l in range(nL):
                    for s, (sub, lin) in SITES.items():
                        hooks.append(getattr(getattr(model.model.layers[l], sub), lin).register_forward_pre_hook(
                            cap_in(l, s, xs_p)))
                VE.clear_act_cache()
                with VE.block_hooks(model, edits, {l: cap_out_p(l) for l in range(nL)}):
                    model.model(input_ids=torch.tensor([ids], device=model.device), use_cache=False)
                for h in hooks:
                    h.remove()
                for l in range(nL):
                    d = hs_p[l] - hs_t[l]
                    if 12 <= l <= 23:
                        nominal = torch.zeros_like(d)
                        nominal[:nS] = alpha * torch.tensor(n[l - 12][s_idx], device=d.device)[:, None] * u[None, :]
                        d = d - nominal
                    nr = d.norm(dim=-1) / mean_n
                    acc["S"][l].append(float(nr[:nS].median()))
                    acc["R"][l].append(float(nr[nS]))
                    if nr.numel() > nS + 1:
                        acc["G"][l].append(float(nr[nS + 1:].median()))
                    for s in SITES:
                        xp, xt = xs_p[(l, s)].float(), xs_t[(l, s)].float()
                        qp, sp = EN.actq(xs_p[(l, s)])
                        qt, st = EN.actq(xs_t[(l, s)])
                        rp = xp - qp.float() * sp
                        rt = xt - qt.float() * st
                        dx = (xp - xt).norm(dim=-1)
                        moved = dx > 0
                        if l <= 12:
                            exact_early &= bool(torch.equal(xs_p[(l, s)], xs_t[(l, s)]))
                        rnd[s]["rel_rms"][l].append(float((rp.pow(2).mean(-1).sqrt() / xp.pow(2).mean(-1).sqrt()
                                                            .clamp(min=1e-12)).median()))
                        if bool(moved.any()):
                            rnd[s]["amp"][l].append(float(((rp - rt).norm(dim=-1)[moved] / dx[moved]).median()))
                            rnd[s]["scale_changed"][l].append(float((sp != st).float()[moved].mean()))
                            rnd[s]["ds_rel"][l].append(float(((sp - st).abs() / st)[moved].median()))
                            rnd[s]["argmax_changed"][l].append(
                                float((xp.abs().argmax(-1) != xt.abs().argmax(-1)).float()[moved].mean()))
                del hs_p, xs_p
            del hs_t, xs_t
            ctx.release()
        med = lambda v: float(np.median(v)) if v else None  # noqa: E731
        out[task] = {"induced_ban_units": {g: [med(acc[g][l]) for l in range(nL)] for g in ("S", "R", "G")},
                     "rounding": {s: {k: [med(rnd[s][k][l]) for l in range(nL)] for k in rnd[s]} for s in SITES},
                     "x_push_equals_x_twin_blocks_0_12": exact_early, "mean_n": mean_n,
                     "n_pairs": len(acc["S"][0])}
    return out


def run_weight_set(model: Any, tok: Any, prompts: dict, engines: tuple[str, ...], deadline: float) -> dict[str, Any]:
    t0 = time.time()
    ws = "B" if engines[0] in ("c", "d") else "Q"
    res: dict[str, Any] = {"weight_set": ws, "engines": list(engines)}
    try:
        res["kl_fidelity"] = kl_and_fidelity(model, prompts, engines, ws)
    except Exception as e:  # noqa: BLE001 - diagnostics never abort the decisive stages
        logger.exception(f"KL/FIDELITY failed: {e}")
        res["kl_fidelity_error"] = str(e)
    for e in engines:
        if time.time() > deadline:
            res[f"induced_{e}"] = "dropped (deadline)"
            continue
        try:
            res[f"induced_{e}"] = induced_and_rounding(model, prompts, e)
        except Exception as ex:  # noqa: BLE001
            logger.exception(f"induced/rounding {e} failed: {ex}")
            res[f"induced_{e}"] = f"error: {ex}"
    res["minutes"] = (time.time() - t0) / 60
    write_json(RESULTS / f"diagnostics_{ws}.json", res)
    logger.info(f"diagnostics {ws} done in {res['minutes']:.1f} min")
    return {"minutes": res["minutes"]}
