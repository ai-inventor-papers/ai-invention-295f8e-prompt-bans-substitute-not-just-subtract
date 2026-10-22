#!/usr/bin/env python3
"""GPU phase 1 (everything before the commit): S1 GPU unit tests + engine check (positive control, screen rows),
S2 states (batch-1 forward passes of all 4,144 prompts), S2.9 units (ban unit, ban-free unit, outlier positions),
S3 realised-displacement prefills of every committed push (no sampling).

Batch-1 forward passes everywhere: under FP8 W8A8 a row's prefill state depends on its batch position (exp17
deviation 10), so states and realised displacements are taken one prompt at a time.
"""

from __future__ import annotations

import gc
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
import npz_parts  # noqa: E402
import torch  # noqa: E402
from loguru import logger  # noqa: E402

from cfg4 import (ALPHAS_POP, B, CAP_BLOCKS, EDIT_BLOCKS, MOVABLE, OTHER9, RESULTS_DIR, SEEDS_OTHER, SEEDS_POP,  # noqa: E402
                  STATES_DIR, TASKS15, TEMPLATE_IDS, setup_logging, utc_now, write_json)
from ctx4 import TaskCtx, ban_unit, push_spec, rand_dir  # noqa: E402
from engine import block_hooks, load_model  # noqa: E402
from engine4 import prefill, sample, u_stream  # noqa: E402
from hooks4 import make_edits_v4  # noqa: E402
from prompts4 import load_prompts4  # noqa: E402
from sampling4 import run_cells  # noqa: E402

SCREEN_PUSHES = {t: [(s, a) for s in (9001, 9002, 9003) for a in (1.0, 2.0)] for t in
                 ("T03", "T04", "T05", "T06", "T1", "T2")}
for _t in ("T1", "T2", "T03"):
    SCREEN_PUSHES[_t] += [(s, 1.0) for s in range(9004, 9016)]


# ------------------------------------------------------------------------------------------------ S1 tests
def gpu_tests(model: Any, tok: Any, prompts: dict) -> dict[str, Any]:
    t0 = time.time()
    res: dict[str, Any] = {}
    ctx = TaskCtx(model, prompts, "T2")
    tw = ctx.twin("W1")
    # U1b row-position independence at B = 20
    us = [u_stream("u1b", j % 10) for j in range(B)]
    a = sample(model, tok, [{"pre": tw["pre"], "us": us}], fence=None, max_new=96)
    res["U1b_rows_identical_given_same_uniforms"] = all(a[j]["token_ids"] == a[j + 10]["token_ids"] for j in range(10))
    # batch-1 prefill bit-identical on repeat
    p = ctx.prompt("twin", "W1")
    cap1: dict[int, torch.Tensor] = {}
    cap2: dict[int, torch.Tensor] = {}
    pa = prefill(model, p["ids"], capture={28: lambda h: cap1.__setitem__(28, h.float().clone())})
    pb = prefill(model, p["ids"], capture={28: lambda h: cap2.__setitem__(28, h.float().clone())})
    res["prefill_repeat_max_abs_diff_block28"] = float((cap1[28] - cap2[28]).abs().max())
    res["prefill_repeat_r_logits_max_abs_diff"] = float((pa["r_logits"] - pb["r_logits"]).abs().max())
    res["prefill_bit_identical"] = res["prefill_repeat_max_abs_diff_block28"] == 0.0 and \
        res["prefill_repeat_r_logits_max_abs_diff"] == 0.0
    del pa, pb
    # TARGET with M = 0 reproduces the twin token for token (20 slots)
    us20 = [u_stream("T2", "W1", k) for k in range(B)]
    base = sample(model, tok, [{"pre": tw["pre"], "us": us20}], fence="path", max_new=64)
    sp0 = push_spec(model.device, rand_dir(9101), ban_unit("T2"), 0.0)
    pre0, _ = ctx.arm_prefill("W1", sp0)
    z = sample(model, tok, [{"pre": pre0, "us": us20}], fence="path", max_new=64)
    res["TARGET_M0_identical_tokens"] = all(x["token_ids"] == y["token_ids"] for x, y in zip(base, z))
    res["TARGET_M0_r_logits_max_abs_diff"] = float((pre0["r_logits"] - tw["pre"]["r_logits"]).abs().max())
    del pre0
    # realised displacement along U equals the target (< 1%) at blocks 12-23
    rel = {}
    for t in ("T2", "T03", "T1"):
        c = TaskCtx(model, prompts, t)
        for alpha in (1.0, 2.0):
            _, rec = c.arm_prefill("W1", push_spec(model.device, rand_dir(9101), ban_unit(t), alpha))
            rel[f"{t}_a{alpha}"] = rec["rel_err_max"]
        c.release()
    res["rel_err_along_U_max"] = rel
    res["rel_err_pass"] = max(rel.values()) < 0.01
    # CLAMP: displacement's P component ~ 0 (random orthonormal Q, k = 5)
    rng = np.random.default_rng(0)
    Qn = np.linalg.qr(rng.standard_normal((4096, 5)))[0].astype(np.float32)
    Qt = torch.tensor(Qn, device=model.device)
    sp = push_spec(model.device, rand_dir(9101), ban_unit("T2"), 2.0)
    capS: dict[int, torch.Tensor] = {}

    def mk(l):
        def g(h):
            capS[l] = h[0, tw["a"]:tw["b"]].float().clone()
        return g
    ed = make_edits_v4("CLAMP", tw["a"], tw["b"], sp["U"], sp["M"], {l: tw["S"][l] for l in EDIT_BLOCKS},
                       Q={l: Qt for l in EDIT_BLOCKS})
    prefill(model, p["ids"], edits=ed, capture={l: mk(l) for l in EDIT_BLOCKS})
    ratios = []
    for l in EDIT_BLOCKS:
        d = capS[l] - tw["S"][l]
        ratios.append(float(((d @ Qt).norm(dim=-1) / d.norm(dim=-1).clamp(min=1e-9)).max()))
    res["CLAMP_max_ratio_Qt_delta_over_delta"] = max(ratios)
    res["CLAMP_pass"] = max(ratios) < 1e-3 * 10  # bf16 cast of h bounds the residual; reported exactly
    res["CLAMP_note"] = ("criterion in the plan: < 1e-3; the edited state is cast back to the block dtype (bf16), "
                         "whose rounding (~2^-8 relative per coordinate) bounds the achievable residual")
    # memory headroom: preallocated cache at the longest prompt + max_new, B = 20
    from engine import prealloc_cache
    Pmax = max(r["P"] for r in prompts.values() if r["kind"] == "twin")
    torch.cuda.empty_cache()
    kv = [(K.expand(B, -1, -1, -1), V.expand(B, -1, -1, -1)) for K, V in tw["pre"]["kv"]]
    cache = prealloc_cache(kv, Pmax + 1024 + 1)
    free_after, total = torch.cuda.mem_get_info(0)
    res["memory"] = {"P_max_twin": Pmax, "free_GB_after_prealloc_B20": free_after / 1e9, "total_GB": total / 1e9,
                     "max_allocated_GB": torch.cuda.max_memory_allocated() / 1e9}
    res["memory_pass"] = free_after / 1e9 > 0.6
    del cache, kv
    ctx.release()
    gc.collect()
    torch.cuda.empty_cache()
    res["seconds"] = time.time() - t0
    res["all_pass"] = bool(res["U1b_rows_identical_given_same_uniforms"] and res["prefill_bit_identical"] and
                           res["TARGET_M0_identical_tokens"] and res["rel_err_pass"] and res["memory_pass"])
    write_json(RESULTS_DIR / "unit_tests_gpu.json", res)
    logger.info(f"GPU tests: {res}")
    return res


# ------------------------------------------------------------------------------------------------ S2 states
@torch.no_grad()
def states_pass(model: Any, prompts: dict, tasks: tuple[str, ...] = TASKS15) -> None:
    for t in tasks:
        out = STATES_DIR / f"states_{t}.npz"
        if npz_parts.exists(out):
            continue
        t0 = time.time()
        rows = [r for r in prompts.values() if r["task"] == t]
        n = len(rows)
        sm = np.zeros((n, len(CAP_BLOCKS), 4096), np.float16)
        Rr = np.zeros((n, len(CAP_BLOCKS), 4096), np.float16)
        Slen = rows[0]["spec_end"] - rows[0]["p1"]
        twin_pnorm = np.zeros((len(TEMPLATE_IDS), len(EDIT_BLOCKS), Slen), np.float32)
        for i, r in enumerate(rows):
            a, b, P = r["p1"], r["spec_end"], r["P"]
            got: dict[int, Any] = {}

            def mk(l):
                def g(h):
                    hs = h[0, a:b].float()
                    got[l] = (hs.mean(0), h[0, P - 1].float(), hs.norm(dim=-1) if l in EDIT_BLOCKS else None)
                return g
            inp = torch.tensor([r["ids"]], device=model.device)
            from engine import clear_act_cache
            clear_act_cache()
            with block_hooks(model, None, {l: mk(l) for l in CAP_BLOCKS}):
                model.model(input_ids=inp, use_cache=False)
            clear_act_cache()
            for j, l in enumerate(CAP_BLOCKS):
                sm[i, j] = got[l][0].cpu().numpy().astype(np.float16)
                Rr[i, j] = got[l][1].cpu().numpy().astype(np.float16)
            if r["kind"] == "twin":
                wi = TEMPLATE_IDS.index(r["template_id"])
                for j, l in enumerate(EDIT_BLOCKS):
                    twin_pnorm[wi, j] = got[l][2].cpu().numpy()
        meta = np.array([r["pid"] for r in rows])
        npz_parts.save(out, {"smean": sm, "R": Rr, "pids": meta},
                       {"twin_pnorm": twin_pnorm, "blocks": np.array(CAP_BLOCKS)})
        logger.info(f"states {t}: {n} prompts in {time.time() - t0:.0f}s")
        del sm, Rr
        gc.collect()


# ------------------------------------------------------------------------------------------------ S2.9 units
def units() -> dict[str, Any]:
    rep: dict[str, Any] = {"ratio_n_over_twin_norm_by_block": {}, "per_task": {}, "outliers": {}}
    ratios: dict[int, list[np.ndarray]] = {l: [] for l in EDIT_BLOCKS}
    tn: dict[str, np.ndarray] = {}
    for t in TASKS15:
        z = npz_parts.load(STATES_DIR / f"states_{t}.npz")
        tn[t] = z["twin_pnorm"].mean(0)   # [12, |S|] mean over W1-W5
    for t in TASKS15:
        if t == "R2":
            continue
        n = ban_unit(t)
        assert n.shape == tn[t].shape, f"{t}: ban unit {n.shape} vs twin {tn[t].shape}"
        for j, l in enumerate(EDIT_BLOCKS):
            ratios[l].append(n[j] / np.maximum(tn[t][j], 1e-6))
    r_l = {l: float(np.median(np.concatenate(v))) for l, v in ratios.items()}
    rep["ratio_n_over_twin_norm_by_block"] = r_l
    from scipy.stats import spearmanr
    for t in TASKS15:
        nfree = np.stack([r_l[l] * tn[t][j] for j, l in enumerate(EDIT_BLOCKS)])
        if t == "R2":
            np.save(RESULTS_DIR / "units_nfree_R2.npy", nfree.astype(np.float32))
            rep["per_task"][t] = {"unit": "n_free", "mean": float(nfree.mean())}
            continue
        n = ban_unit(t)
        rho = float(spearmanr(n.mean(0), nfree.mean(0))[0])
        rep["per_task"][t] = {"unit": "ban (exp13 bench / exp17 path)", "mean_n": float(n.mean()),
                              "ratio_mean_nfree_over_mean_n": float(nfree.mean() / n.mean()),
                              "spearman_positions_n_vs_nfree": rho}
        med = np.median(n, axis=1, keepdims=True)
        out = np.argwhere(n > 10 * med)
        rep["outliers"][t] = [{"block": int(EDIT_BLOCKS[i]), "pos": int(p), "n": float(n[i, p]),
                               "median_block": float(med[i, 0])} for i, p in out[:50]]
        if t in ("T03", "T04", "T05", "T06"):
            n17 = ban_unit(t, "exp17")
            rep["per_task"][t]["exp13_over_exp17_norm_mean_ratio"] = float(n.mean() / n17.mean())
    write_json(RESULTS_DIR / "units.json", rep)
    logger.info(f"units: r_l {r_l}")
    return rep


# ------------------------------------------------------------------------------------------------ realised pass
@torch.no_grad()
def realised_pass(model: Any, prompts: dict) -> None:
    for t in TASKS15:
        out = STATES_DIR / f"disp_{t}.npz"
        if npz_parts.exists(out):
            continue
        t0 = time.time()
        seeds = SEEDS_POP if t in MOVABLE else SEEDS_OTHER
        jobs = [("POP", s, a) for s in seeds for a in ALPHAS_POP]
        jobs += [("SCR", s, a) for s, a in SCREEN_PUSHES.get(t, [])]
        ctx = TaskCtx(model, prompts, t)
        keys, D, DR, recs = [], [], [], []
        for w in TEMPLATE_IDS:
            for fam, s, a in jobs:
                n = ban_unit(t, "exp17" if fam == "SCR" else "plan")
                pre, rec = ctx.arm_prefill(w, push_spec(model.device, rand_dir(s), n, a), want_vectors=True)
                del pre
                D.append(rec.pop("_delta"))
                DR.append(rec.pop("_deltaR"))
                keys.append(f"{fam}|{s}|{a}|{w}")
                recs.append({"key": keys[-1], **{k: v for k, v in rec.items() if not k.startswith("_")}})
            ctx.release()
        npz_parts.save(out, {"delta": np.stack(D), "deltaR": np.stack(DR), "keys": np.array(keys)},
                       {"blocks": np.array(CAP_BLOCKS)})
        write_json(STATES_DIR / f"disp_{t}_recs.json", recs)
        logger.info(f"realised {t}: {len(keys)} prefills in {time.time() - t0:.0f}s; max rel_err "
                    f"{max(r['rel_err_max'] for r in recs):.4f}")
        del D, DR
        gc.collect()


def main(stages: list[str]) -> None:
    setup_logging("gpu_phase1")
    torch.cuda.set_per_process_memory_fraction(0.97, 0)
    tok, model = load_model()
    prompts = load_prompts4()
    if "tests" in stages and not (RESULTS_DIR / "unit_tests_gpu.json").exists():
        res = gpu_tests(model, tok, prompts)
        if not res["all_pass"]:
            logger.error("GPU tests failed; see results/unit_tests_gpu.json")
    if "engine" in stages:
        W = {w: [("SCR_d9002_a1.0", list(range(10))), ("TWIN", list(range(10)))] for w in TEMPLATE_IDS}
        run_cells(model, tok, prompts, "T03", W, "engine_check")
        W = {w: [("SCR_d9004_a1.0", list(range(10))), ("TWIN", list(range(10)))] for w in TEMPLATE_IDS}
        run_cells(model, tok, prompts, "T2", W, "engine_check")
        write_json(RESULTS_DIR / "engine_check_sampled.json", {"utc": utc_now()})
    if "states" in stages:
        states_pass(model, prompts)
    if "units" in stages:
        units()
    if "realised" in stages:
        realised_pass(model, prompts)
    write_json(RESULTS_DIR / "gpu_phase1_done.json", {"utc": utc_now(), "stages": stages})


if __name__ == "__main__":
    main(sys.argv[1:] or ["tests", "engine", "states", "units", "realised"])
