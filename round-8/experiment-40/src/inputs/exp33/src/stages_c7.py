#!/usr/bin/env python3
"""GPU stages, part C: held-out generation cells (STEP 9), the R lambda sweep and M states (STEP 11), the third
task's reduced cell set, and the Sutter random-initialisation control (T2)."""

from __future__ import annotations

import gc
import time
from typing import Any

import numpy as np
import torch
from loguru import logger

from cfg import ROOT, read_json, read_jsonl, write_json
from cfg7 import BAND, DEFAULT7, RANKS, SEEDS, results7
from gpu7 import capture_states, run_specs, spec_row
from stages_a7 import ban_key, forced_key, pad_key, twin_key
from stages_b7 import (Gen, counts, held_pairs, label_rows, load_map, load_targets, site_blocks, site_of,
                       slot_base_ban, slot_forced, wait_labels)

LAMBDAS = (0.0, 0.2, 0.4, 0.5, 0.6, 0.7, 0.8, 1.0, 1.25, 1.5)


def full_ban_arm(task: str) -> str:
    s = site_of(task)
    return "FULL_ban_band" if s["site"] == "band" else f"FULL_ban_L{s['L_star']}"


def site_name(task: str) -> str:
    s = site_of(task)
    return "band12-23" if s["site"] == "band" else f"L{s['L_star']}"


PREFIX = {"MAIN": ("DAS", "PERM", "PERM", "RPOS", "REV", "NULL"),
          "MAIN_LY": ("DASLY", "PERMLY", "PERM_LY", "RPOSLY", "REVLY", "NULLLY")}


def k_star(task: str, T: dict[str, Any], fit: str = "MAIN_LY") -> tuple[int, dict[str, Any]]:
    P = PREFIX[fit][0]
    landing = T["landing"] or T["kept_Y"][:1]
    base = counts(task, "BASE_W5", landing)["correct_Y"]
    full = counts(task, full_ban_arm(task), landing)["correct_Y"] - base
    rec = {}
    for k in RANKS:
        c = counts(task, f"{P}_ban_k{k}", landing)
        rec[k] = (c["correct_Y"] - base) / full if (full > 0 and c["n"] >= 30) else None
    ks = [k for k in RANKS if rec[k] is not None and rec[k] >= 0.8]
    return (min(ks) if ks else 16), {"recovery_by_k": rec, "full_transfer_count": full, "base_count": base}


def stage_gen(model: Any, tok: Any, P7: dict, task: str, reduced: bool = False, fit: str = "MAIN_LY",
              pilot: bool = False) -> dict[str, Any]:
    """Held-out generation cells for one fitted map (fit = MAIN_LY: amended bounded objective, full cell set;
    fit = MAIN with pilot=True: the committed contrastive map's DAS cells on slots 0-9 only)."""
    T = load_targets(task)
    blocks = site_blocks(task)
    sn = site_name(task)
    D = DEFAULT7[task]
    G = Gen(model, P7, task)
    P_das, P_perm, permfit, P_rpos, P_rev, P_null = PREFIX[fit]
    have = {nm: load_map(task, nm) for nm in ("RAND1", "RAND2", "RAND3", "PCA16", "DIM1")}
    have["MAP"] = load_map(task, fit)
    try:
        have["PERMMAP"] = load_map(task, permfit)
    except FileNotFoundError:
        have["PERMMAP"] = None
    try:
        have["RPOSMAP"] = load_map(task, "RPOS_LY" if fit == "MAIN_LY" else "RPOS")
    except FileNotFoundError:
        have["RPOSMAP"] = None
    kept = [Y for Y in T["kept_Y"] if Y in T["groups"]]
    ex = {(k, Y) for k, Y in T["excluded_pad_cells"]}
    if reduced:
        kept = sorted(kept, key=lambda y: -T["adherence"][y]["share"])[:2]
    srcW5 = ban_key(task, "W5")
    specs: list[dict[str, Any]] = []
    n_slots = 10 if pilot else 30

    def add(arm: str, cell: str, s: int, base: str, source: str | None, B: torch.Tensor | None = None,
            full: bool = False, pos_kind: str = "spec", Y: str | None = None, rank: int | None = None,
            fit_: str | None = None, lam: float = 1.0) -> None:
        specs.append(spec_row(task, arm, cell, s, P7[base], make=G.make(base, source, blocks, pos_kind, B, full, lam),
                              stage="gen", source_key=source, site=sn + ("_R" if pos_kind == "R" else ""),
                              layer=blocks[0] if len(blocks) == 1 else None, rank_k=rank, fit=fit_, Y_source=Y,
                              lam=lam))

    def pad_ok(s: int, Y: str) -> bool:
        return (3 + (s % 2), Y) not in ex

    W = have["MAP"]
    # ------------------------------------------------------------------ phase 1: ban source
    for s in range(n_slots):
        b = slot_base_ban(task, s)
        for k in (RANKS if not reduced else (1, 4, 16)):
            add(f"{P_das}_ban_k{k}", "DAS", s, b, srcW5, B=W[:k], Y="ban", rank=k, fit_=fit)
        if pilot:
            continue
        add("BASE_W5", "BASE", s, b, None)
        for i in ((1, 2, 3) if not reduced else (1,)):
            add(f"RAND_ban_k16_d{i}", "RAND", s, b, srcW5, B=have[f"RAND{i}"][:16], Y="ban", rank=16, fit_=f"RAND{i}")
        if have["PERMMAP"] is not None:
            add(f"{P_perm}_ban_k16", "PERM", s, b, srcW5, B=have["PERMMAP"][:16], Y="ban", rank=16, fit_=permfit)
        if not reduced:
            if have["RPOSMAP"] is not None:
                add(f"{P_rpos}_ban_k16", "RPOS", s, b, srcW5, B=have["RPOSMAP"][:16], pos_kind="R", Y="ban", rank=16,
                    fit_="RPOS_LY" if fit == "MAIN_LY" else "RPOS")
            add("RPOSFULL_ban", "RPOS", s, b, srcW5, full=True, pos_kind="R", Y="ban")
            add("DIM1_ban", "UNLEARNED", s, b, srcW5, B=have["DIM1"], Y="ban", rank=1, fit_="DIM1")
            add("PCA16_ban", "UNLEARNED", s, b, srcW5, B=have["PCA16"], Y="ban", rank=16, fit_="PCA16")
            add("REV_full", "REVERSE", s, srcW5, twin_key(task, "W5", s % 12), full=True, Y=D)
        if reduced and full_ban_arm(task) not in {r["arm"] for r in label_rows(task)}:
            add(full_ban_arm(task), "CONFIRM", s, b, srcW5, full=True, Y="ban")
    run_specs(model, tok, task, specs, f"GEN1:{task}:{fit}")
    ban_ids = {x["sample_id"] for x in specs}
    specs = []
    # ------------------------------------------------------------------ phase 2: forced + null sources
    for s in range(n_slots):
        if kept and not pilot:
            Yb = kept[(s // 2) % len(kept)]
            fk, pk_ = slot_forced(task, s, Yb)
            if pad_ok(s, Yb):
                add("BASE_PAD", "BASE", s, pk_, None)
        for Y in kept:
            if not pad_ok(s, Y):
                continue
            fk, pk_ = slot_forced(task, s, Y)
            for k in (1, 4, 16):
                add(f"{P_das}_F_{Y}_k{k}", "DAS", s, pk_, fk, B=W[:k], Y=Y, rank=k, fit_=fit)
            if pilot:
                continue
            add(f"FULL_F_{Y}", "FULL", s, pk_, fk, full=True, Y=Y)
            if not reduced:
                add(f"RAND_F_{Y}_k16", "RAND", s, pk_, fk, B=have["RAND1"][:16], Y=Y, rank=16, fit_="RAND1")
        if pilot:
            continue
        if kept and not reduced and have["PERMMAP"] is not None:
            Yp = max(kept, key=lambda y: T["adherence"][y]["correct_Y"])
            if pad_ok(s, Yp):
                fk, pk_ = slot_forced(task, s, Yp)
                add(f"{P_perm}_F_{Yp}_k16", "PERM", s, pk_, fk, B=have["PERMMAP"][:16], Y=Yp, rank=16, fit_=permfit)
        if not reduced:
            fk, pk_ = slot_forced(task, s, D)
            add(f"{P_null}_k16", "NULL", s, pk_, fk, B=W[:16], Y=D, rank=16, fit_=fit)
            add("NULL_full", "NULL", s, pk_, fk, full=True, Y=D)
    run_specs(model, tok, task, specs, f"GEN2:{task}:{fit}")
    if pilot:
        return {"task": task, "fit": fit, "pilot": True}
    wait_labels(ban_ids)
    ks, kinfo = k_star(task, T, fit)
    logger.info(f"{task} {fit}: k* = {ks} ({kinfo})")
    out = {"task": task, "fit": fit, "k_star": ks, "k_star_info": kinfo, "site": sn, "kept_Y_cells": kept}
    write_json(results7(f"kstar_{task}.json" if fit == "MAIN_LY" else f"kstar_{task}_{fit}.json"), out)
    specs = []
    if not reduced:
        for s in range(30):
            b = slot_base_ban(task, s)
            if ks != 16:
                add(f"RAND_ban_k{ks}", "RAND", s, b, srcW5, B=have["RAND1"][:ks], Y="ban", rank=ks, fit_="RAND1")
                if have["PERMMAP"] is not None:
                    add(f"{P_perm}_ban_k{ks}", "PERM", s, b, srcW5, B=have["PERMMAP"][:ks], Y="ban", rank=ks,
                        fit_=permfit)
            add(f"{P_rev}_k{ks}", "REVERSE", s, srcW5, twin_key(task, "W5", s % 12), B=W[:ks], Y=D, rank=ks, fit_=fit)
        srcW4 = ban_key(task, "W4")
        for s in range(10):
            b4 = twin_key(task, "W4", s % 12)
            add("BASE_W4", "W4", s, b4, None)
            add("FULL_W4", "W4", s, b4, srcW4, full=True, Y="ban")
            add(f"{P_das}_W4_k{ks}", "W4", s, b4, srcW4, B=W[:ks], Y="ban", rank=ks, fit_=fit)
    else:
        for s in range(30):
            b = slot_base_ban(task, s)
            if have["PERMMAP"] is not None and ks != 16:
                add(f"{P_perm}_ban_k{ks}", "PERM", s, b, srcW5, B=have["PERMMAP"][:ks], Y="ban", rank=ks,
                    fit_=permfit)
            if ks != 16:
                add(f"RAND_ban_k{ks}", "RAND", s, b, srcW5, B=have["RAND1"][:ks], Y="ban", rank=ks, fit_="RAND1")
    run_specs(model, tok, task, specs, f"GEN3:{task}:{fit}")
    return out


def stage_r(model: Any, tok: Any, P7: dict, task: str, k: int | None = None, forced_Y: str | None = None
            ) -> None:
    """Discreteness sweep: interpolated DAS edit lam in LAMBDAS, N = 20, CRN slots 0-19 (ban W5 source)."""
    if k is None:
        k = read_json(results7(f"kstar_{task}.json"))["k_star"]
    blocks = site_blocks(task)
    sn = site_name(task)
    G = Gen(model, P7, task)
    W = load_map(task, "MAIN_LY")[:k]
    srcW5 = ban_key(task, "W5")
    specs = []
    for lam in LAMBDAS:
        for s in range(20):
            b = slot_base_ban(task, s)
            specs.append(spec_row(task, f"LAM{lam}_ban_k{k}", "R", s, P7[b], make=G.make(b, srcW5, blocks, "spec", W,
                                                                                         False, lam),
                                  stage="r", source_key=srcW5, site=sn, rank_k=k, fit="MAIN_LY", Y_source="ban",
                                  lam=lam))
            if forced_Y:
                fk, pk_ = slot_forced(task, s, forced_Y)
                specs.append(spec_row(task, f"LAM{lam}_F_{forced_Y}_k{k}", "R", s, P7[pk_],
                                      make=G.make(pk_, fk, blocks, "spec", W, False, lam), stage="r", source_key=fk,
                                      site=sn, rank_k=k, fit="MAIN_LY", Y_source=forced_Y, lam=lam))
    run_specs(model, tok, task, specs, f"R:{task}")


@torch.no_grad()
def stage_m(model: Any, P7: dict, task: str) -> None:
    """M coordinates: spec states at the site's middle block for every prompt of the task (and spec-mean)."""
    blocks = site_blocks(task)
    l = blocks[len(blocks) // 2]
    W = load_map(task, "MAIN_LY").to(model.lm_head.weight.device)
    z, mean_state = {}, {}
    for key, r in P7.items():
        if r["task"] != task:
            continue
        st = capture_states(model, r, [l], with_r=False)[l].float()
        z[key] = (st @ W.T).mean(0).cpu().numpy()
        mean_state[key] = st.mean(0).cpu().numpy().astype(np.float16)
    np.savez_compressed(ROOT / "cache" / f"m_states_{task}.npz", keys=np.array(list(z)),
                        z=np.stack([z[k] for k in z]), mean=np.stack([mean_state[k] for k in z]), block=l)
    logger.info(f"M states {task}: {len(z)} prompts at block {l}")


def stage_randinit(model_unused: Any, P7: dict, task: str = "T2", objective: str = "C") -> dict[str, Any]:
    """Sutter control: a randomly initialised Qwen3-8B (HF _init_weights, normal 0.02, norms 1, seed 0), the same
    token sequences, caches, map class and fit budget; held-out TF gain against the trained network's."""
    from transformers import AutoConfig, AutoModelForCausalLM

    from cfg import model_path
    from das7 import fit_das
    from stages_b7 import build_ctx, pair_lists
    import gpu7
    t0 = time.time()
    cfg = AutoConfig.from_pretrained(model_path())
    torch.manual_seed(SEEDS["random_init_network"])
    with torch.device("meta"):
        rnd = AutoModelForCausalLM.from_config(cfg, torch_dtype=torch.bfloat16, attn_implementation="sdpa")
    rnd = rnd.to_empty(device="cuda")
    with torch.no_grad():
        for m in rnd.modules():
            if isinstance(m, (torch.nn.Linear, torch.nn.Embedding)):
                torch.nn.init.normal_(m.weight, mean=0.0, std=cfg.initializer_range)
                if getattr(m, "bias", None) is not None:
                    torch.nn.init.zeros_(m.bias)
            elif hasattr(m, "weight") and m.__class__.__name__.endswith("RMSNorm"):
                torch.nn.init.ones_(m.weight)
    from transformers.models.qwen3.modeling_qwen3 import Qwen3RotaryEmbedding
    rnd.model.rotary_emb = Qwen3RotaryEmbedding(config=cfg, device="cuda")
    rnd.eval()
    rnd.requires_grad_(False)
    T = load_targets(task)
    ctx = build_ctx(rnd, P7, task, T)
    ctx_val = build_ctx(rnd, P7, task, T, val=True)
    tr, va = pair_lists(task, T)
    fits = read_json(results7(f"das_fits_{task}.json"))
    budget = fits["n_steps_budget"]
    budget = read_json(results7(f"das_fits_ly_{task}.json"))["fits"]["MAIN_LY"]["budget"] if objective == "lmeY" \
        else budget
    f = fit_das(ctx, tr, va, SEEDS["das_init"][task], ctx_val=ctx_val, n_steps=budget,
                log_name=f"{task}:RANDINIT_{objective}", objective=objective)
    W = f["basis"].to(ctx.dev)
    gains, fulls, gY, fY = [], [], [], []
    with torch.no_grad():
        for (s, b, g, kind) in held_pairs(task, T):
            if kind != "ban" and not kind.startswith("forced"):
                continue
            o = ctx.contrast_rows(b, g, [{"none": True}, {"src": s, "B": None}, {"src": s, "B": W[:16]}])
            fulls.append(float(o["C"][1] - o["C"][0]))
            gains.append(float(o["C"][2] - o["C"][0]))
            fY.append(float(o["lmeY"][1] - o["lmeY"][0]))
            gY.append(float(o["lmeY"][2] - o["lmeY"][0]))
    if objective == "lmeY":
        tf = read_json(results7(f"tf_eval_{task}_LY.json"))["summary"]
        key = "DASLY_k16"
    else:
        tf = read_json(results7(f"tf_eval_{task}.json"))["summary"]
        key = "DAS_k16"
    ks_ = [k for k in ("ban", "forced") if k in tf and key in tf[k]]
    n_tr = [tf[k][key]["n"] for k in ks_]
    trained_gain = float(np.average([tf[k][key]["mean_gain"] for k in ks_], weights=n_tr)) if ks_ else None
    trained_full = float(np.average([tf[k][key]["mean_full_gain"] for k in ks_], weights=n_tr)) if ks_ else None
    trained_dY = float(np.average([tf[k][key]["d_lmeY"] for k in ks_], weights=n_tr)) if ks_ else None
    out = {"task": task, "objective": objective, "random_net_heldout_das16_gain": float(np.mean(gains)),
           "random_net_heldout_full_gain": float(np.mean(fulls)),
           "random_net_heldout_das16_lmeY_gain": float(np.mean(gY)),
           "random_net_heldout_full_lmeY_gain": float(np.mean(fY)),
           "trained_heldout_das16_gain": trained_gain, "trained_heldout_full_gain": trained_full,
           "trained_heldout_das16_lmeY_gain": trained_dY,
           "ratio": float(np.mean(gains)) / trained_gain if trained_gain else None,
           "ratio_lmeY": float(np.mean(gY)) / trained_dY if trained_dY else None,
           "c3_pass_lt_0.5": (float(np.mean(gains)) < 0.5 * trained_gain) if trained_gain else None,
           "fit": {k: v for k, v in f.items() if k not in ("basis", "curve")}, "seconds": round(time.time() - t0, 1),
           "init": "meta-device Qwen3-8B, to_empty(cuda), normal(0, 0.02) Linear/Embedding, RMSNorm 1, seed 0"}
    write_json(results7(f"randinit_{task}.json" if objective == "C" else f"randinit_ly_{task}.json"), out)
    ctx.free()
    ctx_val.free()
    del rnd
    gc.collect()
    torch.cuda.empty_cache()
    return out


def stage_mgen(model: Any, tok: Any, P7: dict, task: str = "T2") -> None:
    """Extension (not in the plan): behaviour of the prompts M places, N = 30 each on CRN slots 0-29: the spec alone,
    two random seeds, the semantic seed and 'Make a new algorithm.' (cap 512); exp18's LF2 long-form novelty
    instruction with cap 1,536 (it asks for a ~2,000-word rationale before the code)."""
    from cfg7 import MAX_NEW7
    G = Gen(model, P7, task)
    specs = []
    for kind in ("p0", "seed_rand1", "seed_rand2", "seed_sem", "instr_new", "instr_novel"):
        key = next(k for k, r in P7.items() if r["task"] == task and r["kind"] == kind)
        for s in range(30):
            sp = spec_row(task, f"MGEN_{kind}", "MGEN", s, P7[key], make=G.make(key, None, []), stage="mgen")
            if kind == "instr_novel":
                sp["max_new"] = 1536
            specs.append(sp)
    run_specs(model, tok, task, specs, f"MGEN:{task}")


def stage_seed2(model: Any, tok: Any, P7: dict, task: str = "T2") -> dict[str, Any]:
    """Extension (plan departure 2): a second init seed of the amended LME_Y map on T2, same pairs and budget,
    generated at k in {1, k*, 16} on the ban source and k = 16 on each forced Y (arms DASLY2_*)."""
    from das7 import fit_das
    from stages_b7 import build_ctx, pair_lists, save_map
    T = load_targets(task)
    fits0 = read_json(results7(f"das_fits_ly_{task}.json"))
    budget = fits0["fits"]["MAIN_LY"]["budget"]
    ctx = build_ctx(model, P7, task, T)
    ctx_val = build_ctx(model, P7, task, T, val=True)
    tr, va = pair_lists(task, T)
    seed2 = SEEDS["das_init"][task] + 1000
    f = fit_das(ctx, tr, va, seed2, ctx_val=ctx_val, n_steps=budget, log_name=f"{task}:MAIN_LY_s2", objective="lmeY")
    sha = save_map(task, "MAIN_LY_s2", f["basis"], {k: v for k, v in f.items() if k != "basis"})
    W1 = load_map(task, "MAIN_LY").float()
    W2 = f["basis"].float()
    # principal angles between the two fitted subspaces (rank 1, 2, 16)
    ang = {}
    for k in (1, 2, 4, 16):
        sv = torch.linalg.svdvals(W1[:k] @ W2[:k].T).clamp(max=1.0)
        ang[k] = [float(torch.rad2deg(torch.arccos(x))) for x in sv]
    ctx.free()
    ctx_val.free()
    ks = read_json(results7(f"kstar_{task}.json"))["k_star"]
    blocks = site_blocks(task)
    sn = site_name(task)
    G = Gen(model, P7, task)
    srcW5 = ban_key(task, "W5")
    specs = []
    for s in range(30):
        b = slot_base_ban(task, s)
        for k in sorted({1, ks, 16}):
            specs.append(spec_row(task, f"DASLY2_ban_k{k}", "SEED2", s, P7[b],
                                  make=G.make(b, srcW5, blocks, "spec", W2[:k], False, 1.0), stage="gen",
                                  source_key=srcW5, site=sn, rank_k=k, fit="MAIN_LY_s2", Y_source="ban"))
        for Y in [y for y in T["kept_Y"] if y in T["groups"]]:
            fk, pk_ = slot_forced(task, s, Y)
            specs.append(spec_row(task, f"DASLY2_F_{Y}_k16", "SEED2", s, P7[pk_],
                                  make=G.make(pk_, fk, blocks, "spec", W2[:16], False, 1.0), stage="gen",
                                  source_key=fk, site=sn, rank_k=16, fit="MAIN_LY_s2", Y_source=Y))
    run_specs(model, tok, task, specs, f"SEED2:{task}")
    out = {"task": task, "seed": seed2, "map_sha256": sha, "principal_angles_deg": ang,
           "fit": {k: v for k, v in f.items() if k not in ("basis", "curve")}}
    write_json(results7(f"seed2_{task}.json"), out)
    return out
