#!/usr/bin/env python3
"""GPU driver (one process per stage, model loaded once per process):
  prep    hardware, positions, r_Q (ban forward passes only), twin states and ban-free units, forced states, banned
          sets, push directions, push progress, batch-shape memory probe
  tests   GPU tests U1-U7, positive control U8 (ENG rows), smoke mini batches (k >= 100), timing
  sample  waits for predictions/commit1.done, then decisive sampling in priority order (staged 10 -> 100 -> full with
          time extrapolation; drop order applied on time only)
Every stage is resumable: finished outputs are skipped, raw rows are keyed by (task, template, arm, k).
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
from loguru import logger

import schedule as SCH
from cfg import (ALL_BLOCKS, BATCH, CACHE_DIR, D_MODEL, DATA_DIR, DIR_DIR, E20, E23, MAX_NEW, PLAN_BLOCKS, PRECISION,
                 PRED_DIR, RESULTS_DIR, ROOT, TASKS, TEMPLATE_IDS, UNIT_TASKS, UNITS_DIR, append_jsonl, container_ram_gb,
                 detect_cpus, log_deviation, read_json, read_jsonl, setup_logging, sha256_file, utc_now, write_json)
from engine_w16 import forward_capture, free_cuda, load_model, prefill
from prompts import forced_prompts, load_base, save_positions
from sites import (RAW, STATE_BLOCKS, TIMING, Ctx, flush_rowarrays, load_rq, pn_dir, push_file, row_prefill,
                   run_batch)

STOP_FILE = RESULTS_DIR / "STOP_SAMPLING"


# ------------------------------------------------------------------------------------------------ STEP 1
def hardware() -> dict[str, Any]:
    import platform

    import transformers

    props = torch.cuda.get_device_properties(0)
    hw = {"gpu": props.name, "vram_gib": round(props.total_memory / 1024 ** 3, 2),
          "compute_capability": f"{props.major}.{props.minor}", "cpus": detect_cpus(),
          "ram_gb_container": container_ram_gb(), "python": platform.python_version(), "torch": torch.__version__,
          "transformers": transformers.__version__, "precision": PRECISION, "kernel": "sdpa",
          "cuda": torch.version.cuda, "cudnn": torch.backends.cudnn.version(), "utc": utc_now(),
          "note": "VRAM >= 19.5 GiB: plain W16A16 on GPU (no CPU embedding offload needed)"}
    write_json(RESULTS_DIR / "hardware.json", hw)
    return hw


# ------------------------------------------------------------------------------------------------ STEP 2.3 r_Q
@torch.no_grad()
def compute_rq(model: Any, base: dict) -> dict[str, Any]:
    out = UNITS_DIR / "r_Q_all.json"
    if out.exists():
        return read_json(out)
    t0 = time.time()
    ratios: dict[int, list[np.ndarray]] = {l: [] for l in ALL_BLOCKS}
    per_task: dict[str, dict[int, float]] = {}
    for t in UNIT_TASKS:
        rt: dict[int, list[np.ndarray]] = {l: [] for l in ALL_BLOCKS}
        for w in TEMPLATE_IDS:
            b, n = base[(t, w, "ban")], base[(t, w, "twin")]
            S = list(range(n["p1"], n["spec_end"]))
            hb = forward_capture(model, b["ids"], ALL_BLOCKS, positions=S)
            ht = forward_capture(model, n["ids"], ALL_BLOCKS, positions=S)
            for l in ALL_BLOCKS:
                r = ((hb[l] - ht[l]).norm(dim=-1) / ht[l].norm(dim=-1).clamp(min=1e-6)).cpu().numpy()
                ratios[l].append(r)
                rt[l].append(r)
            del hb, ht
        per_task[t] = {l: float(np.median(np.concatenate(rt[l]))) for l in ALL_BLOCKS}
    q23 = read_json(E23 / "results" / "qwen_ratio.json")["r_Q"]
    med = {l: float(np.median(np.concatenate(ratios[l]))) for l in ALL_BLOCKS}
    q25 = {l: float(np.quantile(np.concatenate(ratios[l]), 0.25)) for l in ALL_BLOCKS}
    q75 = {l: float(np.quantile(np.concatenate(ratios[l]), 0.75)) for l in ALL_BLOCKS}
    calib = float(np.median([med[l] / q23[str(l)]["median"] for l in PLAN_BLOCKS]))
    in_band = 0.9 <= calib <= 1.1
    scale = 1.0 if in_band else 1.0 / calib
    used = {}
    for l in ALL_BLOCKS:
        if str(l) in q23 and l in PLAN_BLOCKS:
            used[str(l)] = float(q23[str(l)]["median"])
        else:
            used[str(l)] = float(med[l] * scale)
    if not in_band:
        log_deviation("D_rQ_calib", f"bf16 r_Q / exp23 r_Q median ratio at blocks 12-23 = {calib:.3f} (outside "
                      "[0.9, 1.1])", "precision / recipe difference",
                      f"blocks 0-11 and 24-35 scaled by 1/{calib:.3f} (plan fallback)")
    res = {"definition": "r_Q(l) = median over (task, template, S position) of ||h_ban[l,p] - h_twin[l,p]|| / "
                         "||h_twin[l,p]||, exp20's ban/twin prompts of T03, T05, T06, T10, T1, T2 (W1-W5), "
                         "bf16 forward passes only",
           "bf16_median": {str(l): med[l] for l in ALL_BLOCKS}, "bf16_q25": {str(l): q25[l] for l in ALL_BLOCKS},
           "bf16_q75": {str(l): q75[l] for l in ALL_BLOCKS},
           "exp23_frozen_12_23": {str(l): float(q23[str(l)]["median"]) for l in PLAN_BLOCKS},
           "calibration_ratio_bf16_over_exp23_blocks12_23": calib, "calibration_in_band_0.9_1.1": in_band,
           "scale_applied_to_0_11_24_35": scale, "r_Q_used": used,
           "per_task_median_bf16": {t: {str(l): v for l, v in d.items()} for t, d in per_task.items()},
           "n_ratios_per_block": int(len(np.concatenate(ratios[0]))), "precision": PRECISION,
           "seconds": time.time() - t0, "utc": utc_now()}
    write_json(out, res)
    logger.info(f"r_Q: calibration ratio {calib:.3f} (in band {in_band}); r_Q used b0 {used['0']:.4f} b11 "
                f"{used['11']:.4f} b12 {used['12']:.4f} b23 {used['23']:.4f} b24 {used['24']:.4f} b35 {used['35']:.4f}")
    return res


# ------------------------------------------------------------------------------------------------ STEP 2.2/2.4 units
@torch.no_grad()
def twin_states_and_units(model: Any, base: dict) -> None:
    rq = load_rq()
    summ: dict[str, Any] = {}
    for t in TASKS:
        outp = UNITS_DIR / f"units_{t}.npz"
        cp = CACHE_DIR / f"twin_states_{t}.pt"
        if outp.exists() and cp.exists():
            continue
        arrs: dict[str, np.ndarray] = {}
        states: dict[str, Any] = {}
        nS_w, nR_w, nG_w, cE_w, tnS_w, tnR_w = [], [], [], [], [], []
        for w in TEMPLATE_IDS:
            n = base[(t, w, "twin")]
            H = forward_capture(model, n["ids"], ALL_BLOCKS)
            S = list(range(n["p1"], n["spec_end"]))
            R = n["P"] - 1
            C = n["cond"]
            norms = torch.stack([H[l].norm(dim=-1) for l in ALL_BLOCKS]).cpu().numpy()  # [36, P]
            tnS, tnR, tnC = norms[:, S], norms[:, R], norms[:, C]
            nS, nR, nC = tnS * rq[:, None], tnR * rq, tnC * rq[:, None]
            nG = rq[PLAN_BLOCKS] * tnS[PLAN_BLOCKS].mean(1)
            cE = float(np.sqrt((nS[PLAN_BLOCKS] ** 2).sum() / max((nR[PLAN_BLOCKS] ** 2).sum(), 1e-12)))
            nS_w.append(nS)
            nR_w.append(nR)
            nG_w.append(nG)
            cE_w.append(cE)
            tnS_w.append(tnS)
            tnR_w.append(tnR)
            arrs[f"nC_{w}"] = nC.astype(np.float32)
            arrs[f"normC_{w}"] = tnC.astype(np.float32)
            states[w] = {"S": torch.stack([H[l][S] for l in ALL_BLOCKS]).to(torch.bfloat16).cpu(),
                         "R": torch.stack([H[l][R] for l in ALL_BLOCKS]).to(torch.bfloat16).cpu(),
                         "COND": torch.stack([H[l][C] for l in ALL_BLOCKS]).to(torch.bfloat16).cpu(),
                         "positions": {"S": S, "R": R, "COND": C}}
            del H
            free_cuda()
        arrs.update({"nS": np.stack(nS_w).astype(np.float32), "nR": np.stack(nR_w).astype(np.float32),
                     "nG": np.stack(nG_w).astype(np.float32), "cE": np.array(cE_w, dtype=np.float32),
                     "normS": np.stack(tnS_w).astype(np.float32), "normR": np.stack(tnR_w).astype(np.float32),
                     "r_Q": rq})
        np.savez(outp, **arrs)
        torch.save(states, cp)
        logger.info(f"units {t}: nS[18] {arrs['nS'][:, 18].mean():.2f}, nR[18] {arrs['nR'][:, 18].mean():.2f}, "
                    f"nG[b18] {arrs['nG'][:, 6].mean():.2f}, c_S1E {np.mean(cE_w):.2f}")
    # summary: per site, unit / ||h|| and ban-free / iteration-4 ban unit
    for t in TASKS:
        z = np.load(UNITS_DIR / f"units_{t}.npz")
        b4 = np.load(E20 / "units" / f"units_{t}.npz") if (E20 / "units" / f"units_{t}.npz").exists() else None
        site_bl = {"S0": PLAN_BLOCKS, "S4": list(range(12)), "S5": list(range(24, 36))}
        st: dict[str, Any] = {}
        for s, bl in site_bl.items():
            nS, normS = z["nS"][:, bl], z["normS"][:, bl]
            d = {"unit_over_h_mean_of_ratios": float((nS / np.maximum(normS, 1e-6)).mean()),
                 "unit_over_h_ratio_of_means": float(nS.mean() / max(normS.mean(), 1e-6)),
                 "banfree_unit_mean": float(nS.mean())}
            if b4 is not None:
                ban = b4["nS"][bl]
                d["iter4_ban_unit_mean"] = float(ban.mean())
                d["iter4_ban_over_h_ratio_of_means"] = float(ban.mean() / max(normS.mean(), 1e-6))
                d["banfree_over_iter4_ban_mean_of_ratios"] = float((nS.mean(0) / np.maximum(ban, 1e-6)).mean())
            st[s] = d
        nR, normR = z["nR"][:, PLAN_BLOCKS], z["normR"][:, PLAN_BLOCKS]
        st["S1"] = {"unit_over_h_mean_of_ratios": float((nR / np.maximum(normR, 1e-6)).mean()),
                    "unit_over_h_ratio_of_means": float(nR.mean() / max(normR.mean(), 1e-6)),
                    "banfree_unit_mean": float(nR.mean())}
        st["S1E"] = {"c_mean": float(z["cE"].mean()), "c_per_template": z["cE"].tolist(),
                     "unit_over_h_ratio_of_means": float(z["cE"].mean() * nR.mean() / max(normR.mean(), 1e-6))}
        nCs = [z[f"nC_{w}"][PLAN_BLOCKS] for w in TEMPLATE_IDS]
        nCn = [z[f"normC_{w}"][PLAN_BLOCKS] for w in TEMPLATE_IDS]
        st["S2"] = {"unit_over_h_ratio_of_means": float(np.mean([a.mean() / max(b.mean(), 1e-6)
                                                                   for a, b in zip(nCs, nCn)])),
                    "banfree_unit_mean": float(np.mean([a.mean() for a in nCs]))}
        st["S3"] = {"nG_mean": float(z["nG"].mean()), "unit_over_h_ratio_of_means":
                    float(z["nG"].mean() / max(z["normS"][:, PLAN_BLOCKS].mean(), 1e-6))}
        if b4 is not None:
            st["S3"]["iter4_ban_nG_mean"] = float(b4["nG"].mean())
            st["S0"]["reconcile_exp27_unit_ratio"] = read_json(ROOT / "inputs" / "exp27" / "results" /
                                                               "unit_ratio.json").get(t, {}).get("banfree_over_ban_mean")
        summ[t] = st
    write_json(RESULTS_DIR / "units_summary.json", summ)


# ------------------------------------------------------------------------------------------------ STEP 5 forced states
@torch.no_grad()
def forced_states(model: Any, tok: Any, base: dict) -> None:
    for t in ("T03", "T10", "T1"):
        cp = CACHE_DIR / f"forced_states_{t}.pt"
        if cp.exists():
            continue
        t0 = time.time()
        fps = forced_prompts(tok, base, t)
        X = np.zeros((len(fps), len(PLAN_BLOCKS), D_MODEL), dtype=np.float32)
        for i, f in enumerate(fps):
            S = list(range(f["p1"], f["spec_end"]))
            h = forward_capture(model, f["ids"], PLAN_BLOCKS, positions=S)
            X[i] = np.stack([h[l].mean(0).cpu().numpy() for l in PLAN_BLOCKS])
        tw = np.zeros((5, len(PLAN_BLOCKS), D_MODEL), dtype=np.float32)
        for j, w in enumerate(TEMPLATE_IDS):
            n = base[(t, w, "twin")]
            S = list(range(n["p1"], n["spec_end"]))
            h = forward_capture(model, n["ids"], PLAN_BLOCKS, positions=S)
            tw[j] = np.stack([h[l].mean(0).cpu().numpy() for l in PLAN_BLOCKS])
        meta = [{k: f[k] for k in ("alg", "kind", "i", "segment", "source", "prompt_sha256")} for f in fps]
        torch.save({"X": torch.tensor(X).to(torch.bfloat16), "twin": torch.tensor(tw).to(torch.bfloat16),
                    "meta": meta, "blocks": PLAN_BLOCKS}, cp)
        write_json(CACHE_DIR / f"forced_meta_{t}.json", meta)
        logger.info(f"forced states {t}: {len(fps)} prompts in {time.time() - t0:.0f}s")
        free_cuda()


@torch.no_grad()
def push_progress_states(model: Any, base: dict, rq: np.ndarray) -> None:
    """Post-edit S-means (blocks 18, 23) of every push setting per template x alpha, before sampling."""
    out = CACHE_DIR / "push_states.npz"
    if out.exists():
        return
    arrs: dict[str, np.ndarray] = {}
    for t, site in (("T03", "TOP5"), ("T03", "TOP3"), ("T10", "TOP5"), ("T1", "TOP5")):
        for w in TEMPLATE_IDS:
            ctx = Ctx(model, base, rq, t, w)
            for a in (1.0, 2.0, 4.0):
                row = SCH._row(t, w, 0, SCH.arm_name(site, a), 0)
                _, lg = row_prefill(ctx, row, keep_arrays=False)
                for l in STATE_BLOCKS:
                    arrs[f"{t}|{site}|{w}|{a:g}|{l}"] = lg["arrays"][f"smean{l}"]
            del ctx
            free_cuda()
    np.savez(out, **arrs)
    logger.info(f"push states: {len(arrs)} vectors")


# ------------------------------------------------------------------------------------------------ batch probe
@torch.no_grad()
def batch_probe(model: Any, tok: Any, base: dict, rq: np.ndarray) -> dict[str, Any]:
    outp = RESULTS_DIR / "batch_probe.json"
    if outp.exists():
        return read_json(outp)
    res: dict[str, Any] = {}
    for t in ("T03", "T2"):
        wmax = max(TEMPLATE_IDS, key=lambda w: base[(t, w, "twin")]["P"])
        ctx = Ctx(model, base, rq, t, wmax)
        torch.cuda.reset_peak_memory_stats()
        rows = [SCH._row(t, wmax, 300 + i, "S0_a1", 0) for i in range(BATCH[t])]
        t0 = time.time()
        try:
            run_batch(model, tok, ctx, rows, f"PROBE:{t}", write=False, no_stop=True)
            ok = True
        except torch.cuda.OutOfMemoryError as e:
            logger.error(f"probe OOM at B={BATCH[t]} for {t}: {e}")
            ok = False
        res[t] = {"B": BATCH[t], "P": ctx.P, "max_new": MAX_NEW[t], "ok": ok, "seconds_full_length": time.time() - t0,
                  "peak_gib": torch.cuda.max_memory_allocated() / 1024 ** 3,
                  "total_gib": torch.cuda.get_device_properties(0).total_memory / 1024 ** 3}
        logger.info(f"probe {t}: {res[t]}")
        del ctx
        free_cuda()
    write_json(outp, res)
    return res


# ------------------------------------------------------------------------------------------------ GPU tests
@torch.no_grad()
def gpu_tests(model: Any, tok: Any, base: dict, rq: np.ndarray) -> dict[str, Any]:
    outp = RESULTS_DIR / "unit_tests_gpu.json"
    if outp.exists():
        return read_json(outp)
    res: dict[str, Any] = {"utc": utc_now(), "precision": PRECISION}
    for t in ("T03", "T10"):
        ctx = Ctx(model, base, rq, t, "W1")
        K = [100, 101, 102, 103]
        mk = lambda arm, k, shadow=False: dict(SCH._row(t, "W1", k, arm, 0, shadow))  # noqa: E731
        A = [mk("TWIN", k) for k in K] + [mk(a, k) for a in ("S0_a0", "S1_a0", "S2_a0") for k in K]
        oa = run_batch(model, tok, ctx, A, f"U:{t}:A", write=False)
        Bq = [mk("S4_a0", k) for k in K] + [mk("S5_a0", k) for k in K] + \
             [x for k in K[:2] for x in (mk("S3_a0", k), mk("S3_a0", k, True))] + [mk("TWIN", k) for k in K]
        ob = run_batch(model, tok, ctx, Bq, f"U:{t}:B", write=False)
        Cq = [mk("S1E_a0", k) for k in K] + [mk("S5_a1", k) for k in K] + [mk("S5_a1", k) for k in K] + \
             [mk("TWIN", k) for k in K]
        bo = {i: list(range(24, 35)) for i in range(8, 12)}  # U5: S5 on blocks 24-34 (rows 8-11) vs 24-35 (4-7)
        oc = run_batch(model, tok, ctx, Cq, f"U:{t}:C", write=False, block_override=bo)
        twin = {r["k"]: r["token_ids"] for r in oa if r["arm"] == "TWIN"}
        u1 = all(r["token_ids"] == twin[r["k"]] for r in ob + oc if r["arm"] == "TWIN")
        u2 = {a: all(r["token_ids"] == twin[r["k"]] for r in oa + ob + oc if r["arm"] == a)
              for a in ("S0_a0", "S1_a0", "S2_a0", "S4_a0", "S5_a0", "S3_a0", "S1E_a0")}
        s5 = [r for r in oc if r["arm"] == "S5_a1"]
        u5 = all(s5[i]["token_ids"] == s5[i + 4]["token_ids"] for i in range(4))
        res[t] = {"U1_crn_determinism_two_compositions": u1, "U2_identity_alpha0": u2, "U5_block35_noop": u5,
                  "twin_first_tokens": {str(k): tok.decode(v[:12]) for k, v in twin.items()}}
        # U3 dose at alpha 1, every prefill site
        rel: dict[str, Any] = {}
        for site in ("S0", "S4", "S5", "S1", "S2", "S1E", "TOP5"):
            if site == "TOP5" and not push_file(t, "TOP5").exists():
                continue
            row = SCH._row(t, "W1", 100, f"{site}_a1", 0)
            _, lg = row_prefill(ctx, row, keep_arrays=False)
            L = lg["log"]
            bl = [l for l in L["relerr_along_u_max"] if not (site == "S5" and l == 35)]
            rel[site] = {"max_relerr_along_u": max(L["relerr_along_u_max"][l] for l in bl) if bl else None,
                         "block35_relerr": L["relerr_along_u_max"].get(35) if site == "S5" else None,
                         "mean_along_u": float(np.mean([L["along_u"][l] for l in bl])),
                         "mean_target": float(np.mean([L["target_mean"][l] for l in bl])),
                         "disp_R35": L["disp_R35"], "first_token_kl": L["first_token_kl"],
                         "pass_0.5pct": bool(max(L["relerr_along_u_max"][l] for l in bl) < 0.005) if bl else None}
        # S3 against its shadow + U4 shadow fidelity
        Dq = [x for k in K for x in (mk("S3_a1", k), mk("S3_a1", k, True))] + [mk("TWIN", k) for k in K] + \
             [mk("S0_a1", k) for k in K]
        od = run_batch(model, tok, ctx, Dq, f"U:{t}:D", write=False, keep_shadow_states=True)
        rr = od[-1]["_res"]
        hk_states = rr[0].get("_hooked_states") or []
        sh_states = rr[0].get("_shadow_states") or []
        u4: dict[str, Any] = {}
        if sh_states:
            hk = [i for i, r in enumerate(Dq) if r["site"] == "S3" and not r["shadow"]]
            hk_sorted = sorted(hk, key=lambda i: Dq[i]["k"])
            j0 = 0
            i0 = hk_sorted[j0]
            gen = rr[i0]["token_ids"][:32]
            cap = forward_capture(model, ctx.ids + gen, [23])[23]
            n_ = min(len(sh_states), len(gen))
            shs = torch.stack([sh_states[s][j0] for s in range(n_)]).to(model.device)
            hks = torch.stack([hk_states[s][j0] for s in range(n_)]).to(model.device)
            tf = cap[ctx.P:ctx.P + n_]
            cos = torch.nn.functional.cosine_similarity(shs, tf, dim=-1)
            relerr = (shs - tf).norm(dim=-1) / tf.norm(dim=-1)
            u = torch.tensor(pn_dir(t, "W1", Dq[i0]["k"]), device=model.device)
            along = ((hks - shs) @ u)
            tgt = float(ctx.nG[23] * Dq[i0]["alpha"])
            u4 = {"n_steps": n_, "min_cos": float(cos.min()), "max_rel_norm_err": float(relerr.max()),
                  "pass_cos_0.99": bool(cos.min() > 0.99)}
            rel["S3"] = {"mean_along_u_vs_shadow_block23": float(along.mean()), "target_block23": tgt,
                         "max_relerr": float(((along - tgt).abs() / abs(tgt)).max()),
                         "pass_0.5pct": bool(((along - tgt).abs() / abs(tgt)).max() < 0.005)}
        res[t]["U3_dose_alpha1"] = rel
        res[t]["U4_shadow_fidelity"] = u4
        del ctx
        free_cuda()
    # U6 memory (fixed B, full length, no stop) is in results/batch_probe.json
    res["U6_memory"] = read_json(RESULTS_DIR / "batch_probe.json") if (RESULTS_DIR / "batch_probe.json").exists() \
        else None
    res["all_identity_tests_pass"] = all(res[t]["U1_crn_determinism_two_compositions"] and
                                         all(res[t]["U2_identity_alpha0"].values()) and res[t]["U5_block35_noop"]
                                         for t in ("T03", "T10"))
    res["all_dose_tests_pass"] = all(v.get("pass_0.5pct", True) for t in ("T03", "T10")
                                     for v in res[t]["U3_dose_alpha1"].values())
    write_json(outp, res)
    logger.info(f"GPU tests: identity pass={res['all_identity_tests_pass']}, dose pass={res['all_dose_tests_pass']}")
    return res


def u7_ban_grep(batches: list[dict[str, Any]], base: dict) -> dict[str, Any]:
    """U7: no ban prompt is ever sampled: every sampled row's prompt is the twin of its (task, template)."""
    ban_sha = {r["prompt_sha256"] for (t, w, kind), r in base.items() if kind == "ban"}
    twin_sha = {(t, w): r["prompt_sha256"] for (t, w, kind), r in base.items() if kind == "twin"}
    n = 0
    bad = 0
    for b in batches:
        for r in b["rows"]:
            n += 1
            if twin_sha[(r["task"], r["w"])] in ban_sha:
                bad += 1
    sampled = read_jsonl(RAW)
    bad_raw = sum(1 for r in sampled if r["prompt_sha256"] in ban_sha)
    return {"n_rows_queue": n, "n_ban_prompts_in_queue": bad, "n_raw_rows": len(sampled),
            "n_ban_prompts_in_raw": bad_raw, "pass": bad == 0 and bad_raw == 0}


# ------------------------------------------------------------------------------------------------ sampling
def done_keys() -> set[str]:
    return {f"{r['task']}|{r['template']}|{r['arm']}|{r['k']}" for r in read_jsonl(RAW)}


def run_batches(model: Any, tok: Any, base: dict, rq: np.ndarray, batches: list[dict[str, Any]], label: str,
                deadline: float | None = None, max_batches: int | None = None) -> int:
    done = done_keys()
    ctxs: dict[tuple[str, str], Ctx] = {}
    n = 0
    for b in batches:
        keys = [f"{r['task']}|{r['w']}|{r['arm']}|{r['k']}" for r in b["rows"] if not r["shadow"]
                and r["arm"] != "TWIN_X"]
        if keys and all(k in done for k in keys):
            continue
        if deadline is not None and time.time() > deadline:
            logger.warning(f"{label}: deadline reached before {b['id']}")
            break
        if STOP_FILE.exists():
            logger.warning("STOP_SAMPLING file found; stopping")
            break
        key = (b["task"], b["w"])
        if key not in ctxs:
            ctxs.clear()
            free_cuda()
            ctxs[key] = Ctx(model, base, rq, *key)
        run_batch(model, tok, ctxs[key], b["rows"], b["id"])
        n += 1
        if n % 10 == 0:
            flush_rowarrays()
        if max_batches is not None and n >= max_batches:
            break
    flush_rowarrays()
    return n


def batch_seconds_model() -> dict[str, float]:
    """Mean seconds per batch by task from the timing log (decisive + engine-check batches)."""
    tm = read_jsonl(TIMING)
    out: dict[str, list[float]] = {}
    for x in tm:
        out.setdefault(x["task"], []).append(float(x["seconds"]))
    return {t: float(np.mean(v)) for t, v in out.items() if v}


def projected_seconds(batches: list[dict[str, Any]], done: set[str], sec: dict[str, float]) -> float:
    tot = 0.0
    default = float(np.mean(list(sec.values()))) if sec else 20.0
    for b in batches:
        keys = [f"{r['task']}|{r['w']}|{r['arm']}|{r['k']}" for r in b["rows"] if not r["shadow"]
                and r["arm"] != "TWIN_X"]
        if keys and all(k in done for k in keys):
            continue
        s = sec.get(b["task"], default)
        if b["task"] in ("T1", "T2") and b["task"] not in sec:
            s = default * 1.8
        tot += s
    return tot


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="prep", choices=["prep", "tests", "sample"])
    ap.add_argument("--deadline-unix", type=float, default=0.0)
    args = ap.parse_args()
    setup_logging(f"gpu_{args.stage}")
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    hw = hardware()
    logger.info(f"hardware: {hw}")
    tok, model = load_model()
    base = load_base(tok)
    if args.stage == "prep":
        save_positions(tok, base)
        compute_rq(model, base)
        twin_states_and_units(model, base)
        forced_states(model, tok, base)
        import geometry as G  # CPU: banned sets and push directions need the forced states

        G.build_banned_sets()
        G.build_push_directions()
        rq = load_rq()
        push_progress_states(model, base, rq)
        G.push_progress()
        batch_probe(model, tok, base, rq)
        logger.info("prep done")
        return
    rq = load_rq()
    if args.stage == "tests":
        gpu_tests(model, tok, base, rq)
        eng = SCH.pack(SCH.eng_rows())
        run_batches(model, tok, base, rq, eng, "engine_check_U8")
        sm = SCH.pack(SCH.smoke_rows())
        run_batches(model, tok, base, rq, sm, "smoke")
        write_json(RESULTS_DIR / "tests_done.json", {"utc": utc_now()})
        return
    # decisive sampling
    c1 = PRED_DIR / "commit1.done"
    while not c1.exists():
        logger.info("waiting for commit #1 (predictions/commit1.done) before decisive sampling ...")
        time.sleep(20)
    all_rows = SCH.cell_rows()
    batches = SCH.pack(all_rows)
    write_json(RESULTS_DIR / "schedule_summary.json", SCH.summary(batches))
    deadline = args.deadline_unix or (time.time() + 2.6 * 3600)
    t_main = time.time()
    n10 = run_batches(model, tok, base, rq, batches, "stage10", deadline=deadline, max_batches=1)
    n100 = run_batches(model, tok, base, rq, batches, "stage100", deadline=deadline, max_batches=6)
    sec = batch_seconds_model()
    done = done_keys()
    proj = projected_seconds(batches, done, sec)
    avail = deadline - time.time()
    drop_order = [62, 61, 60, 59, 58, 57, 56, 55]
    dropped: list[int] = []
    kept = list(batches)
    while proj > avail and drop_order:
        p = drop_order.pop(0)
        dropped.append(p)
        kept = [b for b in kept if b["min_prio"] != p]
        proj = projected_seconds(kept, done, sec)
    write_json(RESULTS_DIR / "timing_extrapolation.json",
               {"seconds_per_batch_by_task": sec, "projected_seconds_kept": proj, "available_seconds": avail,
                "dropped_priorities": dropped, "dropped_names": [SCH.PRIO_NAMES[p] for p in dropped],
                "n_batches_total": len(batches), "n_batches_kept": len(kept), "stage_batches": [n10, n100],
                "utc": utc_now(), "rule": "time only, never outcome; plan drop order"})
    logger.info(f"projection: {proj / 60:.1f} min needed vs {avail / 60:.1f} min available; dropped {dropped}")
    for p in dropped:
        log_deviation(f"D_drop_{p}", f"dropped priority block {p} ({SCH.PRIO_NAMES[p]})",
                      "time extrapolation after stage 100 (time only, never outcome)",
                      "cells absent from the analysis")
    run_batches(model, tok, base, rq, kept, "full", deadline=deadline)
    write_json(RESULTS_DIR / "sampling_done.json", {"utc": utc_now(), "hours": (time.time() - t_main) / 3600,
                                                     "n_raw": len(read_jsonl(RAW))})
    logger.info("sampling finished")


if __name__ == "__main__":
    main()
