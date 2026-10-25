#!/usr/bin/env python3
"""B2: cross-model activation patching (CMAP) in Qwen3-8B (bf16, sdpa, one GPU, never both models on it).

Stages (one model load each):
  s1  instruct capture: fork-position caches (MLP outputs, o_proj inputs z and per-head writes, attention outputs,
      residual at every layer input and at the final-norm input), all-position residuals at RS_LAYERS, all-position
      MLP outputs / z in the SPEC band (layers 4-24); engine checks against base_subarm and exp41.
  s2  base capture (same + full-vocab fork logits), base W_O (layers 4-24) and FSTACK-MLP weights for the W arm,
      matched random sets (needs both caches), basis alignment, REV arm (instruct outputs into the base model).
  s3  instruct patching: one-token forwards of the fork token over the cached prefix KV (row 0 unpatched) for the
      single-component sweep (36 MLPs + 1152 heads), the sets, 50 random sets (R / R-pure / R-scaled), placebos,
      the identity checks, RS-fork(0..36) and the W arm; full forwards for RS-prefix / RS-all and the SPEC arm.

Patch semantics (base values into the instruct run, fork position only unless stated):
  MLP l       output of layers[l].mlp set to the base output.
  head (l,h)  o_proj output += base_write_h - z_h @ W_O[:, h].T  (the head's write becomes the base write).
  attn l      o_proj output set to the base o_proj output.
  RS(l)       input of layers[l] (l = 36: the final-norm input) set to the base residual.
  W l         MLP l recomputed from its current input with the BASE MLP weights (fp32, CPU).
"""

from __future__ import annotations

import gc
import sys
import time
from typing import Any

import numpy as np
import torch
from loguru import logger

from cfg9 import (CACHE_DIR, D_MODEL, ENGINE_TOL, FSTACK, HEAD_DIM, IDENTITY_TOL, N_HEADS, N_LAYERS, N_RAND,
                  N_RAND_SPEC, RAND_BAND, RAND_TOL, RAND_TOL_WIDE, RESULTS_DIR, RS_LAYERS, SEED_RAND,
                  SELF_PATCH_TOL, SPEC_EMBEDDED, SPEC_RAND_BAND, TEMPLATES, TOPK, V41, V43, append_jsonl,
                  log_deviation, model_path, read_json, read_jsonl, setup_logging, stage_time, utc_now, write_json)
from units9 import load_units

B2_UNITS = ("B3", "T10")
SPEC_LAYERS = tuple(range(SPEC_RAND_BAND[0], SPEC_RAND_BAND[1] + 1))
GEOM_LAYER = 31          # input of layer 31 = output of block 30 (F8)
MLP_W_LAYERS = (26, 27, 28, 30, 32)
ROWS = 40                # one-token rows per chunk
FROWS = 8                # full-forward rows per chunk


# ================================================================================================ keys
def parse(k: str) -> tuple[str, int, int]:
    p = k.split("|")
    return (p[0], int(p[1][1:]), int(p[2][1:]) if len(p) > 2 else -1)


def key(kind: str, l: int, h: int = -1) -> str:
    return f"mlp|L{l}" if kind == "mlp" else f"head|L{l}|H{h}"


def exp41_to_key(k: str) -> tuple[str, str]:
    """'mlp|L27|H-1|DEC' -> ('mlp|L27', 'DEC')."""
    kind, l, h, c = k.split("|")
    return (f"mlp|{l}" if kind == "mlp" else f"head|{l}|{h}"), c


def node_sets() -> dict[str, list[str]]:
    s = read_json(V41 / "results" / "summary.json")
    out = {"FSTACK": list(FSTACK), "F_MLP": [k for k in FSTACK if k.startswith("mlp")],
           "F_HEAD": [k for k in FSTACK if k.startswith("head")]}
    for name, c in (("F_MST", "C1forced"), ("F_CC", "C2a")):
        ks = []
        for r in s["validation"][c]["node_pass"]:
            k, cl = exp41_to_key(r["node"])
            if r["both"] and cl == "DEC":
                ks.append(k)
        out[name] = ks
    return out


def spec_sets() -> dict[str, list[str]]:
    out = {}
    for unit, cname in (("B3", "C1nat"), ("T10", "C2a")):
        top15 = read_json(V41 / "results" / "summary.json")["circuits"][cname]["top15"]
        top15 = [t if isinstance(t, str) else t.get("node") for t in top15]
        ks = [exp41_to_key(k)[0] for k in top15 if exp41_to_key(k)[1] == "SPEC"][:5]
        if ks != SPEC_EMBEDDED[unit]:
            log_deviation(f"spec_set_{unit}", f"SPEC set from circuit_{cname}.json top15 {ks} differs from the "
                                              f"embedded list {SPEC_EMBEDDED[unit]}; the file's list is used")
        out[unit] = ks or SPEC_EMBEDDED[unit]
    return out


def exp41_top15_dec() -> set[str]:
    s = read_json(V41 / "results" / "summary.json")
    out = set()
    for c, v in s["circuits"].items():
        for k in v.get("top15") or []:
            kk, cl = exp41_to_key(k if isinstance(k, str) else k["node"])
            if cl == "DEC":
                out.add(kk)
    return out


# ================================================================================================ model
STATE: dict[str, Any] = {}


def load(which: str) -> tuple[Any, Any]:
    from transformers import AutoModelForCausalLM, AutoTokenizer
    t0 = time.time()
    path = model_path(which)
    tok = AutoTokenizer.from_pretrained(path)
    free0, _ = torch.cuda.mem_get_info(0)
    model = AutoModelForCausalLM.from_pretrained(path, dtype=torch.bfloat16, attn_implementation="sdpa",
                                                 device_map={"": 0}, low_cpu_mem_usage=True)
    model.eval()
    model.requires_grad_(False)
    gc.collect()
    torch.cuda.empty_cache()
    torch.cuda.set_per_process_memory_fraction(0.97, 0)
    free, total = torch.cuda.mem_get_info(0)
    info = {"model": which, "path_snapshot": path.split("/")[-1], "load_s": round(time.time() - t0, 1),
            "free_vram_before_GB": round(free0 / 1e9, 2), "free_vram_after_GB": round(free / 1e9, 2),
            "gpu": torch.cuda.get_device_name(0)}
    logger.info(f"loaded {which}: {info}")
    STATE.update(model=model, tok=tok, which=which, info=info)
    return model, tok


def unload() -> None:
    for k in ("model",):
        STATE.pop(k, None)
    gc.collect()
    torch.cuda.empty_cache()


class Readout:
    """fp32 readout from the final-norm hidden state: m = lse(z[D]) - lse(z[A]); m_tok = z[a] - z[b]."""

    def __init__(self, model: Any, fork: dict[str, Any], tok: Any):
        W = model.lm_head.weight
        self.D, self.A = list(fork["D"]), list(fork["A"])
        self.WD = W[self.D].float()
        self.WA = W[self.A].float()
        if fork.get("tok_a"):
            a = tok(fork["tok_a"], add_special_tokens=False)["input_ids"][0]
            b = tok(fork["tok_b"], add_special_tokens=False)["input_ids"][0]
            self.Wab = W[[a, b]].float()
        else:
            self.Wab = None

    def __call__(self, h: torch.Tensor) -> dict[str, torch.Tensor]:
        hf = h.float()
        m = torch.logsumexp(hf @ self.WD.T, -1) - torch.logsumexp(hf @ self.WA.T, -1)
        out = {"m": m}
        if self.Wab is not None:
            z = hf @ self.Wab.T
            out["m_tok"] = z[..., 0] - z[..., 1]
        return out


def bf16_logits(model: Any, h: torch.Tensor) -> torch.Tensor:
    return model.lm_head(h).float()


def dist_summary(lg: torch.Tensor, D: list[int], A: list[int], k: int = TOPK) -> dict[str, Any]:
    lp = torch.log_softmax(lg.float(), -1)
    ent = float(-(lp.exp() * lp).sum())
    top = torch.topk(lp, k)
    return {"entropy": ent, "top_ids": top.indices.tolist(), "top_lp": [round(float(x), 5) for x in top.values],
            "pD": float(lp[D].exp().sum()), "pA": float(lp[A].exp().sum()),
            "m_bf16": float(torch.logsumexp(lp[D], 0) - torch.logsumexp(lp[A], 0)), "argmax": int(lp.argmax())}


# ================================================================================================ capture
@torch.no_grad()
def capture(model: Any, ids: list[int], spec_band: bool = True) -> dict[str, torch.Tensor]:
    """One forward over ids; returns CPU bf16 tensors (fork = last position)."""
    L = N_LAYERS
    rin: dict[int, torch.Tensor] = {}
    rall: dict[int, torch.Tensor] = {}
    mlp: dict[int, torch.Tensor] = {}
    mall: dict[int, torch.Tensor] = {}
    z: dict[int, torch.Tensor] = {}
    zall: dict[int, torch.Tensor] = {}
    att: dict[int, torch.Tensor] = {}
    hs = []
    layers = model.model.layers

    def pre_layer(l):
        def f(m, args, kwargs):
            x = args[0] if args else kwargs["hidden_states"]
            rin[l] = x[0, -1].detach().to(torch.bfloat16).cpu()
            if l in RS_LAYERS:
                rall[l] = x[0].detach().to(torch.bfloat16).cpu()
        return f

    def pre_norm(m, args, kwargs):
        x = args[0] if args else kwargs["hidden_states"]
        rin[L] = x[0, -1].detach().to(torch.bfloat16).cpu()

    def mlp_hook(l):
        def f(m, inp, out):
            mlp[l] = out[0, -1].detach().to(torch.bfloat16).cpu()
            if spec_band and l in SPEC_LAYERS:
                mall[l] = out[0].detach().to(torch.bfloat16).cpu()
        return f

    def o_hook(l):
        def f(m, inp, out):
            zz = inp[0]
            z[l] = zz[0, -1].detach().to(torch.bfloat16).cpu()
            att[l] = out[0, -1].detach().to(torch.bfloat16).cpu()
            if spec_band and l in SPEC_LAYERS:
                zall[l] = zz[0].detach().to(torch.bfloat16).cpu()
        return f

    for l in range(L):
        hs.append(layers[l].register_forward_pre_hook(pre_layer(l), with_kwargs=True))
        hs.append(layers[l].mlp.register_forward_hook(mlp_hook(l)))
        hs.append(layers[l].self_attn.o_proj.register_forward_hook(o_hook(l)))
    hs.append(model.model.norm.register_forward_pre_hook(pre_norm, with_kwargs=True))
    try:
        out = model.model(input_ids=torch.tensor([ids], device="cuda"), use_cache=False)
    finally:
        for h in hs:
            h.remove()
    hfin = out.last_hidden_state[0, -1].detach()
    # per-head writes at the fork with this model's own W_O
    writes = torch.zeros(L, N_HEADS, D_MODEL, dtype=torch.bfloat16)
    for l in range(L):
        Wo = layers[l].self_attn.o_proj.weight.float().view(D_MODEL, N_HEADS, HEAD_DIM)
        zz = z[l].cuda().float().view(N_HEADS, HEAD_DIM)
        writes[l] = torch.einsum("hd,ohd->ho", zz, Wo).to(torch.bfloat16).cpu()
    res = {"resid": torch.stack([rin[l] for l in range(L + 1)]), "mlp": torch.stack([mlp[l] for l in range(L)]),
           "z": torch.stack([z[l] for l in range(L)]), "attn": torch.stack([att[l] for l in range(L)]),
           "writes": writes, "resid_all": torch.stack([rall[l] for l in RS_LAYERS]),
           "hfin": hfin.to(torch.bfloat16).cpu()}
    if spec_band:
        res["mlp_all"] = torch.stack([mall[l] for l in SPEC_LAYERS])
        res["z_all"] = torch.stack([zall[l] for l in SPEC_LAYERS])
    del out
    return res


@torch.no_grad()
def onetok_capture(model: Any, ids: list[int], B: int = ROWS) -> dict[str, torch.Tensor]:
    """Fork-position values on the SAME computation path as the patched runs: a one-token forward of the fork token
    over the prefix KV with the fixed batch shape B (all rows unpatched; row 0 is read). Patch values and anchors taken
    from this path make the self-patch exact and remove full-forward vs one-token kernel offsets."""
    kv = prefix_kv(model, ids)
    L = N_LAYERS
    rin: dict[int, torch.Tensor] = {}
    mlp: dict[int, torch.Tensor] = {}
    z: dict[int, torch.Tensor] = {}
    att: dict[int, torch.Tensor] = {}
    hs = []
    layers = model.model.layers

    def pre_layer(l):
        def f(m, args, kwargs):
            x = args[0] if args else kwargs["hidden_states"]
            rin[l] = x[0, -1].detach().to(torch.bfloat16).cpu()
        return f

    def pre_norm(m, args, kwargs):
        x = args[0] if args else kwargs["hidden_states"]
        rin[L] = x[0, -1].detach().to(torch.bfloat16).cpu()

    def mlp_hook(l):
        def f(m, inp, out):
            mlp[l] = out[0, -1].detach().to(torch.bfloat16).cpu()
        return f

    def o_hook(l):
        def f(m, inp, out):
            z[l] = inp[0][0, -1].detach().to(torch.bfloat16).cpu()
            att[l] = out[0, -1].detach().to(torch.bfloat16).cpu()
        return f

    for l in range(L):
        hs.append(layers[l].register_forward_pre_hook(pre_layer(l), with_kwargs=True))
        hs.append(layers[l].mlp.register_forward_hook(mlp_hook(l)))
        hs.append(layers[l].self_attn.o_proj.register_forward_hook(o_hook(l)))
    hs.append(model.model.norm.register_forward_pre_hook(pre_norm, with_kwargs=True))
    pos = len(ids) - 1
    try:
        cache = build_cache(kv, B)
        o = model.model(input_ids=torch.full((B, 1), ids[-1], device="cuda", dtype=torch.long), past_key_values=cache,
                        position_ids=torch.full((B, 1), pos, device="cuda"),
                        cache_position=torch.tensor([pos], device="cuda"), use_cache=True)
    finally:
        for h in hs:
            h.remove()
    hfin = o.last_hidden_state[0, -1].detach()
    writes = torch.zeros(L, N_HEADS, D_MODEL, dtype=torch.bfloat16)
    for l in range(L):
        Wo = layers[l].self_attn.o_proj.weight.float().view(D_MODEL, N_HEADS, HEAD_DIM)
        writes[l] = torch.einsum("hd,ohd->ho", z[l].cuda().float().view(N_HEADS, HEAD_DIM), Wo).to(
            torch.bfloat16).cpu()
    del o, cache, kv
    return {"resid": torch.stack([rin[l] for l in range(L + 1)]), "mlp": torch.stack([mlp[l] for l in range(L)]),
            "z": torch.stack([z[l] for l in range(L)]), "attn": torch.stack([att[l] for l in range(L)]),
            "writes": writes, "hfin": hfin.to(torch.bfloat16).cpu()}


@torch.no_grad()
def check_margins(model: Any, tok: Any, units: dict[str, Any], which: str) -> dict[str, Any]:
    """base_arm-style margins (bf16 lm_head logits -> fp32 log_softmax) on the iteration-8 twins (chat and plain)."""
    out = {}
    ref = read_json(V43 / "results" / "base_subarm.json")["tasks"]
    for u, t in (("CHK_B3", "B3"), ("CHK_T10", "T10")):
        U = units[u]
        f = U["forks"][0]
        rec = {}
        for mode in ("chat", "plain"):
            ms = []
            for p in U["prompts"]:
                ids = (p["ids"] if mode == "chat" else p["ids_plain"]) + f["opening"]
                # exactly iteration 8's engine8.teacher_force call shape (logits_to_keep = len(opening) + 1): the bf16
                # lm_head output is quantised (0.125-0.25 at |logit| 16-64) and its rounding depends on the GEMM shape
                o = model(input_ids=torch.tensor([ids], device="cuda"), use_cache=False,
                          logits_to_keep=len(f["opening"]) + 1)
                lp = torch.log_softmax(o.logits[0, -1].float().double(), -1)
                ms.append(float(torch.logsumexp(lp[f["D"]], 0) - torch.logsumexp(lp[f["A"]], 0)))
            rec[mode] = ms
        key_ = "margin_instr" if which == "qwen" else "margin_base"
        key_p = "margin_instr_template_free" if which == "qwen" else "margin_base_template_free"
        diffs = [abs(a - b) for a, b in zip(rec["chat"], ref[t][key_])]
        diffs_p = [abs(a - b) for a, b in zip(rec["plain"], ref[t][key_p])]
        out[t] = {"chat": rec["chat"], "plain": rec["plain"], "ref_chat": ref[t][key_], "ref_plain": ref[t][key_p],
                  "max_abs_diff_chat": max(diffs), "max_abs_diff_plain": max(diffs_p),
                  "pass": max(diffs) <= ENGINE_TOL}
        logger.info(f"engine check {which} {t}: chat {np.round(rec['chat'], 3).tolist()} vs ref "
                    f"{np.round(ref[t][key_], 3).tolist()} (max diff {max(diffs):.4f})")
    return out


def stage_capture(which: str, max_prompts: int | None = None) -> None:
    """s1 (which='qwen') / s2 capture part (which='qwen_base')."""
    t0 = time.time()
    model, tok = load(which)
    units = load_units()
    tag = "instr" if which == "qwen" else "base"
    gt: dict[str, Any] = {"model": which, "load": STATE["info"], "utc": utc_now()}
    gt["engine_check"] = check_margins(model, tok, units, which)
    for u in B2_UNITS:
        U = units[u]
        f = U["forks"][0]
        R = Readout(model, f, tok)
        caps, recs = [], []
        prompts = U["prompts"][:max_prompts] if max_prompts else U["prompts"]
        for p in prompts:
            ids = p["ids"] + f["opening"]
            c = capture(model, ids)
            c["ot"] = onetok_capture(model, ids)
            r_ot = R(c["ot"]["hfin"].cuda())
            h = c["hfin"].cuda()
            r = R(h)
            lg = bf16_logits(model, h)
            ds = dist_summary(lg, f["D"], f["A"])
            rec = {"pid": p["pid"], "m": float(r["m"]), "m_tok": float(r["m_tok"]), **ds, "n_ids": len(ids),
                   "m_ot": float(r_ot["m"]), "m_tok_ot": float(r_ot["m_tok"])}
            if which == "qwen_base":
                c["logits_full"] = lg.to(torch.float16).cpu()
            # opening log-likelihood (on-policy check is instruct-only)
            if which == "qwen":
                o = model(input_ids=torch.tensor([ids], device="cuda"), use_cache=False)
                lp = torch.log_softmax(o.logits[0].float(), -1)
                P = len(p["ids"])
                op = f["opening"]
                rec["logp_opening"] = float(sum(lp[P - 1 + j, op[j]] for j in range(len(op))))
                del o, lp
            caps.append(c)
            recs.append(rec)
        torch.save({"pids": [p["pid"] for p in prompts], "caps": caps}, CACHE_DIR / f"{tag}_{u}.pt")
        gt[u] = recs
        if which == "qwen":
            d = [abs(r["m_tok"] - p["exp41_m_clean"]) for r, p in zip(recs, prompts) if p.get("exp41_m_clean")]
            gt[f"{u}_exp41_check"] = {"max_abs_diff": max(d) if d else None, "n": len(d),
                                      "pass": bool(d) and max(d) <= ENGINE_TOL,
                                      "per_prompt": [(p["pid"], p.get("exp41_m_clean"), r["m_tok"])
                                                     for r, p in zip(recs, prompts)]}
            logger.info(f"exp41 clean-margin check {u}: max |diff| {gt[f'{u}_exp41_check']['max_abs_diff']}")
        logger.info(f"{tag} {u}: m mean {np.mean([r['m'] for r in recs]):.3f} over {len(recs)} prompts")
    if which == "qwen_base":
        sd = {}
        for l in MLP_W_LAYERS:
            mm = model.model.layers[l].mlp
            sd[l] = {n: getattr(mm, n).weight.detach().to(torch.bfloat16).cpu() for n in ("gate_proj", "up_proj",
                                                                                           "down_proj")}
        torch.save(sd, CACHE_DIR / "base_mlp_w.pt")
        torch.save({l: model.model.layers[l].self_attn.o_proj.weight.detach().to(torch.bfloat16).cpu()
                    for l in SPEC_LAYERS}, CACHE_DIR / "base_wo.pt")
    write_json(RESULTS_DIR / f"capture_{tag}.json", gt)
    stage_time(f"capture_{tag}", time.time() - t0)


# ================================================================================================ random sets
def delta_norms(ci: dict, cb: dict) -> dict[str, float]:
    """Mean over prompts of ||base - instr|| at the fork for every MLP and head write."""
    acc: dict[str, list[float]] = {}
    for a, b in zip(ci["caps"], cb["caps"]):
        a, b = a["ot"], b["ot"]
        dm = (b["mlp"].float() - a["mlp"].float()).norm(dim=-1)
        dw = (b["writes"].float() - a["writes"].float()).norm(dim=-1)
        for l in range(N_LAYERS):
            acc.setdefault(key("mlp", l), []).append(float(dm[l]))
            for h in range(N_HEADS):
                acc.setdefault(key("head", l, h), []).append(float(dw[l, h]))
    return {k: float(np.mean(v)) for k, v in acc.items()}


def draw_random_sets(norms: dict[str, float], targets: list[str], seed: int, n: int, band: tuple[int, int],
                     exclude: set[str]) -> dict[str, Any]:
    """For each target node: same type, layer in band, not in exclude; candidates with mean delta norm within
    x[0.70, 1.43] of the target's (widened to x[0.5, 2] if < 3 candidates). n sets; within a set no repeats."""
    rng = np.random.default_rng(seed)
    pools, meta = {}, {}
    for t in targets:
        kind, _, _ = parse(t)
        pool = [k for k in norms if parse(k)[0] == kind and band[0] <= parse(k)[1] <= band[1] and k not in exclude]
        w0 = norms[t]
        cand = [k for k in pool if RAND_TOL[0] * w0 <= norms[k] <= RAND_TOL[1] * w0]
        tol = list(RAND_TOL)
        if len(cand) < 3:
            cand = [k for k in pool if RAND_TOL_WIDE[0] * w0 <= norms[k] <= RAND_TOL_WIDE[1] * w0]
            tol = list(RAND_TOL_WIDE)
            if len(cand) < 3:
                cand = sorted(pool, key=lambda k: abs(norms[k] - w0))[:3]
                tol = "nearest-3"
        pools[t] = sorted(cand)
        meta[t] = {"tolerance": tol, "n_candidates": len(cand), "norm": w0}
    sets = []
    for _ in range(n):
        s = []
        for t in targets:
            c = [k for k in pools[t] if k not in s] or pools[t]
            s.append(c[int(rng.integers(len(c)))])
        sets.append(s)
    for t in targets:
        j = targets.index(t)
        meta[t]["n_distinct_drawn"] = len({s[j] for s in sets})
    return {"sets": sets, "meta": meta, "n_distinct_sets": len({tuple(sorted(s)) for s in sets}), "seed": seed}


def spec_delta_norms(ci: dict, cb: dict, pos_lists: list[list[int]], Wo_i: dict, Wo_b: dict) -> dict[str, float]:
    acc: dict[str, list[float]] = {}
    for a, b, ps in zip(ci["caps"], cb["caps"], pos_lists):
        pt = torch.tensor(ps)
        for j, l in enumerate(SPEC_LAYERS):
            dm = (b["mlp_all"][j][pt].float() - a["mlp_all"][j][pt].float()).norm(dim=-1).mean()
            acc.setdefault(key("mlp", l), []).append(float(dm))
            za = a["z_all"][j][pt].cuda().float().view(len(ps), N_HEADS, HEAD_DIM)
            zb = b["z_all"][j][pt].cuda().float().view(len(ps), N_HEADS, HEAD_DIM)
            wa = torch.einsum("phd,ohd->pho", za, Wo_i[l].cuda().float().view(D_MODEL, N_HEADS, HEAD_DIM))
            wb = torch.einsum("phd,ohd->pho", zb, Wo_b[l].cuda().float().view(D_MODEL, N_HEADS, HEAD_DIM))
            dn = (wb - wa).norm(dim=-1).mean(0).cpu()
            for h in range(N_HEADS):
                acc.setdefault(key("head", l, h), []).append(float(dn[h]))
            del za, zb, wa, wb
    return {k: float(np.mean(v)) for k, v in acc.items()}


# ================================================================================================ patched forwards
class OneTok:
    """Row specs for a one-token forward at the fork: list of ops per row.
    ops: ('mlp', l, vec) | ('head', l, h, vec) | ('attn', l, vec) | ('resid', l, vec) | ('mlpw', l)."""

    def __init__(self, model: Any, base_w: dict | None = None):
        self.model = model
        self.Wo = [model.model.layers[l].self_attn.o_proj.weight.view(D_MODEL, N_HEADS, HEAD_DIM)
                   for l in range(N_LAYERS)]
        self.base_w = base_w

    def hooks(self, rows: list[list[tuple]], capture_l: int | None = None, store: dict | None = None) -> list:
        m = self.model
        B = len(rows)
        per_mlp: dict[int, list] = {}
        per_head: dict[int, list] = {}
        per_attn: dict[int, list] = {}
        per_res: dict[int, list] = {}
        per_w: dict[int, list] = {}
        for r, ops in enumerate(rows):
            for op in ops:
                if op[0] == "mlp":
                    per_mlp.setdefault(op[1], []).append((r, op[2]))
                elif op[0] == "head":
                    per_head.setdefault(op[1], []).append((r, op[2], op[3]))
                elif op[0] == "attn":
                    per_attn.setdefault(op[1], []).append((r, op[2]))
                elif op[0] == "resid":
                    per_res.setdefault(op[1], []).append((r, op[2]))
                elif op[0] == "mlpw":
                    per_w.setdefault(op[1], []).append(r)
        hs = []
        dev = "cuda"

        def T(v):
            return torch.stack([(x if torch.is_tensor(x) else torch.as_tensor(x)).float() for x in v]).to(dev)

        for l in set(per_mlp) | set(per_w):
            it = per_mlp.get(l, [])
            rr = torch.tensor([a for a, _ in it], device=dev, dtype=torch.long)
            vv = T([b for _, b in it]) if it else None
            wr = per_w.get(l, [])

            def f(mod, inp, out, rr=rr, vv=vv, wr=wr, l=l):
                out = out.clone()
                if vv is not None:
                    out[rr, -1] = vv.to(out.dtype)
                if wr:
                    x = inp[0][wr, -1].float().cpu()
                    W = self.base_w[l]
                    y = (torch.nn.functional.silu(x @ W["gate_proj"].T) * (x @ W["up_proj"].T)) @ W["down_proj"].T
                    out[torch.tensor(wr, device=dev), -1] = y.to(dev).to(out.dtype)
                return out
            hs.append(m.model.layers[l].mlp.register_forward_hook(f))
        for l in set(per_head) | set(per_attn):
            ih = per_head.get(l, [])
            ia = per_attn.get(l, [])
            hr = torch.tensor([a for a, _, _ in ih], device=dev, dtype=torch.long)
            hh = torch.tensor([b for _, b, _ in ih], device=dev, dtype=torch.long)
            hv = T([c for _, _, c in ih]).float() if ih else None
            ar = torch.tensor([a for a, _ in ia], device=dev, dtype=torch.long)
            av = T([b for _, b in ia]) if ia else None

            def g(mod, inp, out, hr=hr, hh=hh, hv=hv, ar=ar, av=av, l=l):
                out = out.clone()
                if av is not None:
                    out[ar, -1] = av.to(out.dtype)
                if hv is not None:
                    z = inp[0][hr, -1].float().view(-1, N_HEADS, HEAD_DIM)
                    zh = z[torch.arange(len(hr), device=dev), hh]                       # [k, 128]
                    Wb = self.Wo[l][:, hh, :].float().permute(1, 0, 2)                   # [k, 4096, 128]
                    cur = torch.einsum("kd,kod->ko", zh, Wb)
                    acc = out[:, -1].float()
                    acc.index_add_(0, hr, hv - cur)
                    out[:, -1] = acc.to(out.dtype)
                return out
            hs.append(m.model.layers[l].self_attn.o_proj.register_forward_hook(g))
        for l, it in per_res.items():
            rr = torch.tensor([a for a, _ in it], device=dev, dtype=torch.long)
            vv = T([b for _, b in it])
            mod = m.model.norm if l == N_LAYERS else m.model.layers[l]

            def pre(mod_, args, kwargs, rr=rr, vv=vv):
                x = args[0] if args else kwargs["hidden_states"]
                x = x.clone()
                x[rr, -1] = vv.to(x.dtype)
                if args:
                    return (x,) + tuple(args[1:]), kwargs
                kwargs = dict(kwargs, hidden_states=x)
                return args, kwargs
            hs.append(mod.register_forward_pre_hook(pre, with_kwargs=True))
        if capture_l is not None and store is not None:
            def capg(mod_, args, kwargs):
                x = args[0] if args else kwargs["hidden_states"]
                store["geom"] = x[:, -1].detach().to(torch.bfloat16).cpu()
            hs.append(m.model.layers[capture_l].register_forward_pre_hook(capg, with_kwargs=True))
        return hs


def build_cache(kv: list[tuple[torch.Tensor, torch.Tensor]], B: int):
    from transformers.cache_utils import DynamicCache
    cache = DynamicCache()
    for l, (K, V) in enumerate(kv):
        cache.update(K.expand(B, -1, -1, -1).contiguous(), V.expand(B, -1, -1, -1).contiguous(), l)
    return cache


@torch.no_grad()
def prefix_kv(model: Any, ids: list[int]) -> list[tuple[torch.Tensor, torch.Tensor]]:
    from transformers.cache_utils import DynamicCache
    cache = DynamicCache()
    model.model(input_ids=torch.tensor([ids[:-1]], device="cuda"), past_key_values=cache, use_cache=True)
    if hasattr(cache, "layers"):
        kv = [(L.keys.clone(), L.values.clone()) for L in cache.layers]
    else:
        kv = [(K.clone(), V.clone()) for K, V in zip(cache.key_cache, cache.value_cache)]
    del cache
    return kv


@torch.no_grad()
def run_onetok(model: Any, ot: OneTok, kv: list, last_id: int, pos: int, rows: list[list[tuple]], R: Readout,
               want_dist: set[int], want_geom: set[int], D: list[int], A: list[int],
               max_rows: int = ROWS) -> list[dict[str, Any]]:
    """rows[0] must be [] (unpatched). Each chunk re-adds an unpatched row 0; dm is relative to that row."""
    out: list[dict[str, Any]] = []
    body = rows[1:]
    idx_body = list(range(1, len(rows)))
    first = None
    step = max(1, max_rows - 1)
    for b0 in range(0, max(1, len(body)), step):
        chunk = [[]] + body[b0:b0 + step]
        cidx = [0] + idx_body[b0:b0 + step]
        n_real = len(chunk)
        chunk = chunk + [[] for _ in range(max_rows - n_real)]      # fixed batch shape (padding rows unpatched)
        cidx = cidx + [-1] * (max_rows - n_real)
        B = len(chunk)
        store: dict[str, Any] = {}
        hs = ot.hooks(chunk, capture_l=GEOM_LAYER, store=store)
        try:
            cache = build_cache(kv, B)
            o = model.model(input_ids=torch.full((B, 1), last_id, device="cuda", dtype=torch.long),
                            past_key_values=cache, position_ids=torch.full((B, 1), pos, device="cuda"),
                            cache_position=torch.tensor([pos], device="cuda"), use_cache=True)
        finally:
            for h in hs:
                h.remove()
        h = o.last_hidden_state[:, -1]
        r = R(h)
        m = r["m"].tolist()
        mt = r["m_tok"].tolist() if "m_tok" in r else [None] * B
        if first is None:
            first = m[0]
        lg = None
        for j, gi in enumerate(cidx):
            if gi < 0:
                continue
            if j == 0 and gi != 0:
                continue
            if gi == 0 and out:
                continue
            rec = {"i": gi, "m": first + (m[j] - m[0]), "m_raw": m[j], "ref0_drift": m[0] - first,
                   "m_tok": (mt[j] - mt[0]) if mt[j] is not None else None}
            if gi in want_dist:
                if lg is None:
                    lg = bf16_logits(model, h)
                rec["dist"] = dist_summary(lg[j], D, A)
            if gi in want_geom:
                rec["geom"] = store["geom"][j].clone()
            out.append(rec)
        del o, cache, lg
    out.sort(key=lambda d: d["i"])
    return out


@torch.no_grad()
def run_full(model: Any, ids: list[int], rows: list[list[tuple]], R: Readout, Wo_b: dict,
             max_rows: int = FROWS) -> list[dict[str, Any]]:
    """Full forwards; ops: ('rpos', l, pos LongTensor, vals [k, 4096]) | ('mpos', l, pos, vals) |
    ('hpos', l, h, pos, z_base [k, 128]) (base write = z_base @ W_O_base[:, h].T)."""
    m_ = model
    out = []
    dev = "cuda"
    for b0 in range(0, len(rows), max_rows - 1):
        chunk = [[]] + rows[b0:b0 + max_rows - 1]
        n_real = len(chunk)
        chunk = chunk + [[] for _ in range(max_rows - n_real)]      # fixed batch shape
        B = len(chunk)
        hs = []
        per_r: dict[int, list] = {}
        per_m: dict[int, list] = {}
        per_h: dict[int, list] = {}
        for r, ops in enumerate(chunk):
            for op in ops:
                {"rpos": per_r, "mpos": per_m, "hpos": per_h}[op[0]].setdefault(op[1], []).append((r,) + op[2:])
        for l, it in per_r.items():
            def pre(mod_, args, kwargs, it=it):
                x = args[0] if args else kwargs["hidden_states"]
                x = x.clone()
                for r, ps, v in it:
                    x[r, ps.to(dev)] = v.to(dev).to(x.dtype)
                if args:
                    return (x,) + tuple(args[1:]), kwargs
                return args, dict(kwargs, hidden_states=x)
            mod = m_.model.norm if l == N_LAYERS else m_.model.layers[l]
            hs.append(mod.register_forward_pre_hook(pre, with_kwargs=True))
        for l, it in per_m.items():
            def f(mod_, inp, o, it=it):
                o = o.clone()
                for r, ps, v in it:
                    o[r, ps.to(dev)] = v.to(dev).to(o.dtype)
                return o
            hs.append(m_.model.layers[l].mlp.register_forward_hook(f))
        for l, it in per_h.items():
            Wi = m_.model.layers[l].self_attn.o_proj.weight.view(D_MODEL, N_HEADS, HEAD_DIM)
            Wb = Wo_b[l].to(dev).view(D_MODEL, N_HEADS, HEAD_DIM)

            def g(mod_, inp, o, it=it, Wi=Wi, Wb=Wb):
                o = o.clone()
                for r, h, ps, zb in it:
                    ps = ps.to(dev)
                    zc = inp[0][r, ps, h * HEAD_DIM:(h + 1) * HEAD_DIM].float()
                    cur = zc @ Wi[:, h, :].float().T
                    base = zb.to(dev).float() @ Wb[:, h, :].float().T
                    o[r, ps] = (o[r, ps].float() + base - cur).to(o.dtype)
                return o
            hs.append(m_.model.layers[l].self_attn.o_proj.register_forward_hook(g))
        try:
            inp = torch.tensor([ids], device=dev).expand(B, -1).contiguous()
            o = m_.model(input_ids=inp, use_cache=False)
        finally:
            for h in hs:
                h.remove()
        r = R(o.last_hidden_state[:, -1])
        mm = r["m"].tolist()
        for j in range(1, n_real):
            out.append({"m": mm[j], "m_ref_row": mm[0]})
        if b0 == 0:
            out.insert(0, {"m": mm[0], "m_ref_row": mm[0], "unpatched": True})
        del o
    return out


# ================================================================================================ stage s2 extras
def base_stage_extras(max_prompts: int | None = None) -> None:
    """In the base load (after capture): random sets, basis alignment, REV arm."""
    model, tok = STATE["model"], STATE["tok"]
    units = load_units()
    sets = node_sets()
    rs_all = {}
    top15 = exp41_top15_dec()
    for ui, u in enumerate(B2_UNITS):
        ci = torch.load(CACHE_DIR / f"instr_{u}.pt")
        cb = torch.load(CACHE_DIR / f"base_{u}.pt")
        norms = delta_norms(ci, cb)
        R = draw_random_sets(norms, FSTACK, SEED_RAND + ui, N_RAND, RAND_BAND, set(FSTACK))
        Rp = draw_random_sets(norms, FSTACK, SEED_RAND + ui, N_RAND, RAND_BAND, set(FSTACK) | top15)
        rs_all[u] = {"R": R, "Rpure": Rp, "norms_fork": norms}
        # basis alignment
        cos, ratio = [], []
        for a, b in zip(ci["caps"], cb["caps"]):
            ra, rb = a["ot"]["resid"].float(), b["ot"]["resid"].float()
            cos.append(torch.nn.functional.cosine_similarity(ra, rb, dim=-1).numpy())
            ratio.append((rb.norm(dim=-1) / ra.norm(dim=-1).clamp_min(1e-6)).numpy())
        rs_all[u]["basis_alignment"] = {"cos_mean_by_layer": np.mean(cos, 0).tolist(),
                                        "norm_ratio_mean_by_layer": np.mean(ratio, 0).tolist()}
        # REV arm: instruct outputs into the base model at the fork
        f = units[u]["forks"][0]
        Rd = Readout(model, f, tok)
        ot = OneTok(model)
        recs = []
        prompts = units[u]["prompts"][:max_prompts] if max_prompts else units[u]["prompts"]
        for pi, p in enumerate(prompts):
            ids = p["ids"] + f["opening"]
            kv = prefix_kv(model, ids)
            a = ci["caps"][pi]["ot"]

            def ops_for(keys: list[str]) -> list[tuple]:
                ops = []
                for k in keys:
                    kind, l, h = parse(k)
                    ops.append(("mlp", l, a["mlp"][l]) if kind == "mlp" else ("head", l, h, a["writes"][l, h]))
                return ops
            rows = [[], ops_for(FSTACK), ops_for(sets["F_MLP"]), ops_for(sets["F_HEAD"])]
            rows += [ops_for(s) for s in R["sets"]]
            rows += [[("resid", N_LAYERS, a["resid"][N_LAYERS])]]
            res = run_onetok(model, ot, kv, ids[-1], len(ids) - 1, rows, Rd, set(), set(), f["D"], f["A"])
            names = ["none", "FSTACK", "F_MLP", "F_HEAD"] + [f"R{s}" for s in range(N_RAND)] + ["RS36_instr"]
            for nm, rr in zip(names, res):
                recs.append({"unit": u, "pid": p["pid"], "arm": nm, "m": rr["m"], "utc": utc_now()})
            del kv
        append_jsonl(RESULTS_DIR / f"b2_rev_{u}.jsonl", recs)
        del ci, cb
        gc.collect()
    write_json(RESULTS_DIR / "random_sets.json", {u: {k: v for k, v in d.items()} for u, d in rs_all.items()})


# ================================================================================================ stage s3
def stage_patch(max_prompts: int | None = None, units_sel: tuple[str, ...] = B2_UNITS) -> None:
    t0 = time.time()
    model, tok = load("qwen")
    units = load_units()
    sets = node_sets()
    specs = spec_sets()
    rsets = read_json(RESULTS_DIR / "random_sets.json")
    base_w = {l: {k: v.float() for k, v in d.items()} for l, d in torch.load(CACHE_DIR / "base_mlp_w.pt").items()}
    Wo_b = torch.load(CACHE_DIR / "base_wo.pt")
    Wo_i = {l: model.model.layers[l].self_attn.o_proj.weight.detach().cpu() for l in SPEC_LAYERS}
    ot = OneTok(model, base_w)
    gpu_tests: dict[str, Any] = {}
    for ui, u in enumerate(units_sel):
        U = units[u]
        f = U["forks"][0]
        Rd = Readout(model, f, tok)
        ci = torch.load(CACHE_DIR / f"instr_{u}.pt")
        cb = torch.load(CACHE_DIR / f"base_{u}.pt")
        prompts = U["prompts"][:max_prompts] if max_prompts else U["prompts"]
        n = len(prompts)
        R = rsets[u]["R"]["sets"]
        Rp = rsets[u]["Rpure"]["sets"]
        norms = rsets[u]["norms_fork"]
        # SPEC random sets (needs SPEC-position delta norms; drawn once per unit, committed seed)
        pos_lists = [p["pos"]["SPEC"] for p in prompts]
        sp_path = RESULTS_DIR / f"spec_random_sets_{u}.json"
        if sp_path.exists():
            SR = read_json(sp_path)
        else:
            snorms = spec_delta_norms({"caps": ci["caps"][:n]}, {"caps": cb["caps"][:n]}, pos_lists, Wo_i, Wo_b)
            SR = draw_random_sets(snorms, specs[u], SEED_RAND + 100 + ui, N_RAND_SPEC, SPEC_RAND_BAND,
                                  set(specs[u]))
            SR["norms_spec"] = snorms
            write_json(sp_path, SR)
        done = {r["pid"] for r in read_jsonl(RESULTS_DIR / f"b2_tf_{u}.jsonl")}
        mB_of = {r["pid"]: r["m_ot"] for r in read_json(RESULTS_DIR / "capture_base.json")[u]}
        for pi, p in enumerate(prompts):
            if p["pid"] in done:
                continue
            tp = time.time()
            ids = p["ids"] + f["opening"]
            af, bf = ci["caps"][pi], cb["caps"][pi]          # full-forward caches (RS-prefix / RS-all / SPEC arms)
            a, b = af["ot"], bf["ot"]                          # one-token-path fork values (one-token arms)
            bx = cb["caps"][(pi + 1) % len(cb["caps"])]["ot"]
            kv = prefix_kv(model, ids)

            def ops(keys: list[str], src: dict, scale_to: list[str] | None = None) -> list[tuple]:
                o = []
                for j, k in enumerate(keys):
                    kind, l, h = parse(k)
                    if kind == "mlp":
                        v = src["mlp"][l]
                        if scale_to is not None:
                            s = norms[scale_to[j]] / max(norms[k], 1e-6)
                            v = (a["mlp"][l].float() + s * (src["mlp"][l].float() - a["mlp"][l].float()))
                        o.append(("mlp", l, v))
                    else:
                        v = src["writes"][l, h]
                        if scale_to is not None:
                            s = norms[scale_to[j]] / max(norms[k], 1e-6)
                            v = (a["writes"][l, h].float() + s * (src["writes"][l, h].float() -
                                                                  a["writes"][l, h].float()))
                        o.append(("head", l, h, v))
                return o
            names: list[str] = ["none"]
            rows: list[list[tuple]] = [[]]
            for l in range(N_LAYERS):
                names.append(key("mlp", l))
                rows.append(ops([key("mlp", l)], b))
            for l in range(N_LAYERS):
                for h in range(N_HEADS):
                    names.append(key("head", l, h))
                    rows.append(ops([key("head", l, h)], b))
            for sname in ("FSTACK", "F_MLP", "F_HEAD", "F_MST", "F_CC"):
                names.append(sname)
                rows.append(ops(sets[sname], b))
            for s in range(len(R)):
                names.append(f"R{s}")
                rows.append(ops(R[s], b))
            for s in range(len(Rp)):
                names.append(f"Rpure{s}")
                rows.append(ops(Rp[s], b))
            for s in range(len(R)):
                names.append(f"Rscaled{s}")
                rows.append(ops(R[s], b, scale_to=FSTACK))
            names += ["self_FSTACK", "xprompt_FSTACK"]
            rows += [ops(FSTACK, a), ops(FSTACK, bx)]
            allc = [("resid", 0, b["resid"][0])] + [("mlp", l, b["mlp"][l]) for l in range(N_LAYERS)]
            names += ["ALL_attn", "ALL_heads"]
            rows += [allc + [("attn", l, b["attn"][l]) for l in range(N_LAYERS)],
                     allc + [("head", l, h, b["writes"][l, h]) for l in range(N_LAYERS) for h in range(N_HEADS)]]
            for l in range(N_LAYERS + 1):
                names.append(f"RSfork{l}")
                rows.append([("resid", l, b["resid"][l])])
            names += ["W_all"] + [f"W{l}" for l in MLP_W_LAYERS]
            rows += [[("mlpw", l) for l in MLP_W_LAYERS]] + [[("mlpw", l)] for l in MLP_W_LAYERS]
            nm2i = {nm: i for i, nm in enumerate(names)}
            want_dist = {nm2i[k] for k in ("none", "FSTACK", "F_MST", "F_CC", "RSfork23", "RSfork36", "ALL_attn")}
            want_dist |= {nm2i[f"R{s}"] for s in range(len(R))}
            want_geom = {nm2i[k] for k in ("none", "FSTACK", "RSfork23", "RSfork36")} | {nm2i[f"R{s}"]
                                                                                         for s in range(len(R))}
            res = run_onetok(model, ot, kv, ids[-1], len(ids) - 1, rows, Rd, want_dist, want_geom, f["D"], f["A"])
            m_none = res[0]["m"]
            out_rows, geom = [], {}
            for nm, rr in zip(names, res):
                rec = {"unit": u, "pid": p["pid"], "template": p["template"], "arm": nm, "m": rr["m"],
                       "m_raw": rr["m_raw"], "dm_tok": rr["m_tok"], "dm": rr["m"] - m_none,
                       "ref0_drift": rr["ref0_drift"]}
                if "dist" in rr:
                    rec["dist"] = rr["dist"]
                if "geom" in rr:
                    geom[nm] = rr["geom"]
                out_rows.append(rec)
            # full-forward arms: RS-prefix / RS-all and the SPEC arm
            P = len(ids)
            fpos = torch.arange(P - 1)
            apos = torch.arange(P)
            frows, fnames = [], []
            for j, l in enumerate(RS_LAYERS):
                fnames.append(f"RSprefix{l}")
                frows.append([("rpos", l, fpos, bf["resid_all"][j][:P - 1])])
                fnames.append(f"RSall{l}")
                frows.append([("rpos", l, apos, bf["resid_all"][j])])
            sp = torch.tensor(p["pos"]["SPEC"])

            def spec_ops(keys: list[str]) -> list[tuple]:
                o = []
                for k in keys:
                    kind, l, h = parse(k)
                    j = SPEC_LAYERS.index(l)
                    if kind == "mlp":
                        o.append(("mpos", l, sp, bf["mlp_all"][j][sp]))
                    else:
                        o.append(("hpos", l, h, sp, bf["z_all"][j][sp][:, h * HEAD_DIM:(h + 1) * HEAD_DIM]))
                return o
            fnames.append("SPEC")
            frows.append(spec_ops(specs[u]))
            for s, ss in enumerate(SR["sets"]):
                fnames.append(f"SPECR{s}")
                frows.append(spec_ops(ss))
            fres = run_full(model, ids, frows, Rd, Wo_b)
            m_full0 = fres[0]["m"]
            for nm, rr in zip(["full_none"] + fnames, fres):
                dmf = rr["m"] - rr["m_ref_row"]
                out_rows.append({"unit": u, "pid": p["pid"], "template": p["template"], "arm": nm,
                                 "m": (m_full0 if nm == "full_none" else m_none + dmf), "m_raw": rr["m"],
                                 "m_tok": None, "dm": dmf, "ref0_drift": rr["m_ref_row"] - m_full0})
            mB = mB_of[p["pid"]]
            for rr in out_rows:
                rr["m_I"] = m_none
                rr["m_B"] = mB
                rr["utc"] = utc_now()
            append_jsonl(RESULTS_DIR / f"b2_tf_{u}.jsonl", out_rows)
            torch.save(geom, CACHE_DIR / f"geom_{u}_{pi:02d}.pt")
            # GPU tests on the first prompt of each unit
            if pi == 0:
                gpu_tests[u] = gpu_checks(model, ot, kv, ids, Rd, f, a, b, out_rows)
                write_json(RESULTS_DIR / "gpu_tests_b2.json", gpu_tests)
            del kv
            dt = time.time() - tp
            byarm = {r["arm"]: r for r in out_rows}
            gap = m_none - mB
            logger.info(f"[{u}] {p['pid']} {dt:.1f}s | m_I {m_none:.3f} m_B {mB:.3f} | share FSTACK "
                        f"{(m_none - byarm['FSTACK']['m']) / gap:.3f} RS36 {(m_none - byarm['RSfork36']['m']) / gap:.3f} "
                        f"RS23 {(m_none - byarm['RSfork23']['m']) / gap:.3f} self {byarm['self_FSTACK']['dm']:.4f} "
                        f"ALL-RS36 {byarm['ALL_attn']['m'] - byarm['RSfork36']['m']:.4f}")
        del ci, cb
        gc.collect()
        torch.cuda.empty_cache()
    stage_time("b2_patch", time.time() - t0, max_prompts=max_prompts)


@torch.no_grad()
def gpu_checks(model: Any, ot: OneTok, kv: list, ids: list[int], Rd: Readout, f: dict, a: dict, b: dict,
               rows: list[dict]) -> dict[str, Any]:
    by = {r["arm"]: r for r in rows}
    out: dict[str, Any] = {}
    out["G2_self_patch_dm"] = by["self_FSTACK"]["dm"]
    out["G2_pass"] = abs(by["self_FSTACK"]["dm"]) <= SELF_PATCH_TOL
    out["G3_identity_attn_minus_RS36"] = by["ALL_attn"]["m"] - by["RSfork36"]["m"]
    out["G3_identity_heads_minus_RS36"] = by["ALL_heads"]["m"] - by["RSfork36"]["m"]
    out["G3_pass"] = abs(out["G3_identity_heads_minus_RS36"]) <= IDENTITY_TOL
    out["RSfork36_vs_mB"] = by["RSfork36"]["m"] - by["RSfork36"]["m_B"]
    # G4 batching: 8 single-MLP rows batched vs one at a time (each with its own unpatched row 0)
    keys = [key("mlp", l) for l in (5, 12, 20, 26, 27, 30, 33, 35)]
    rows_b = [[]] + [[("mlp", parse(k)[1], b["mlp"][parse(k)[1]])] for k in keys]
    rb = run_onetok(model, ot, kv, ids[-1], len(ids) - 1, rows_b, Rd, set(), set(), f["D"], f["A"])
    diffs = []
    for j, k in enumerate(keys):
        r1 = run_onetok(model, ot, kv, ids[-1], len(ids) - 1, [[], rows_b[j + 1]], Rd, set(), set(), f["D"], f["A"])
        diffs.append(abs((rb[j + 1]["m"] - rb[0]["m"]) - (r1[1]["m"] - r1[0]["m"])))
    # unbatched (B = 1 shape) unpatched one-token margin vs the fixed-shape row 0, for the record
    r_b1 = run_onetok(model, ot, kv, ids[-1], len(ids) - 1, [[]], Rd, set(), set(), f["D"], f["A"], max_rows=1)
    out["B1_shape_vs_B40_unpatched"] = r_b1[0]["m"] - rb[0]["m"]
    out["G4_batched_vs_single_max_abs_dm_diff"] = max(diffs)
    out["G4_pass"] = max(diffs) <= SELF_PATCH_TOL
    # one-token unpatched vs full forward
    out["onetok_vs_full_unpatched"] = by["none"]["m"] - by["full_none"]["m"]
    out["RSfork36_vs_mB_ot"] = by["RSfork36"]["m"] - by["RSfork36"]["m_B"]
    out["utc"] = utc_now()
    logger.info(f"GPU checks: {out}")
    return out


if __name__ == "__main__":
    setup_logging(f"cmap9_{sys.argv[1]}")
    mp = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2] != "all" else None
    if sys.argv[1] == "s1":
        stage_capture("qwen", mp)
    elif sys.argv[1] == "s2":
        stage_capture("qwen_base", mp)
        base_stage_extras(mp)
    elif sys.argv[1] == "s3":
        stage_patch(mp)
