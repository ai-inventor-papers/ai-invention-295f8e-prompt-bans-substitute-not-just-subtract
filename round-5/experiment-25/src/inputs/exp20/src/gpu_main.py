#!/usr/bin/env python3
"""GPU driver (one process, model loaded once):
  STEP 0.2-0.3 hardware + frozen precision rule + model;  STEP 1 positions;  STEP 2 units at every site;
  STEP 3 directions;  STEP 5 C3d plan-site geometry (forced T1 prompts);  GPU tests U1-U4, U6, U7;
  STEP 7 engine check (after commit #0);  STEP 9 staged sampling (smoke -> wait for commit #1 -> stage 100 -> full).
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
from cfg import (BATCH, D_MODEL, DATA_DIR, DECODING, DIR_DIR, E13, E17, MAX_NEW_TOKENS, MODEL_ID, MODEL_REVISION,
                 N_LAYERS, NORM_BLOCKS, PLAN_BLOCKS, PRED_DIR, QUANT, RESULTS_DIR, S3_STEPS, SITE_BLOCKS, SITE_POS,
                 TASKS, TEMPLATE_IDS, UNITS_DIR, append_jsonl, read_json, read_jsonl, setup_logging, sha256_file,
                 sha256_text, stable_seed, utc_now, write_json)
from engine import fence_token_mask, forward_capture, free_cuda, load_model, prefill, sample, u_stream
from hooks import make_prefill_edits
from prompts import SURV, SURV7, TOP5, build_c3d_prompts, load_base, save_positions

RAW = DATA_DIR / "samples_raw.jsonl"
ROWLOG = DATA_DIR / "row_logs.jsonl"
TIMING = RESULTS_DIR / "timing_batches.jsonl"
GEOM_NPZ = DIR_DIR / "plan_geometry_T1.npz"
U_TOP5 = DIR_DIR / "u_top5.npz"
ALL_BLOCKS = list(range(N_LAYERS))


# ------------------------------------------------------------------------------------------------ STEP 0
def hardware_and_precision() -> dict[str, Any]:
    import platform

    props = torch.cuda.get_device_properties(0)
    total_gib = props.total_memory / 1024 ** 3
    cc = (props.major, props.minor)
    if total_gib >= 19.5:
        prec = "bf16"
    elif cc >= (8, 9):
        prec = "fp8_w8a8"
    else:
        prec = "fp8_weight_only"
    from cfg import container_ram_gb, detect_cpus

    hw = {"gpu": props.name, "vram_gib": round(total_gib, 2), "compute_capability": f"{cc[0]}.{cc[1]}",
          "cpus": detect_cpus(), "ram_gb_container": container_ram_gb(), "python": platform.python_version(),
          "torch": torch.__version__, "precision_rule": "VRAM >= 19.5 GiB -> bf16; Ada/Hopper < 19.5 GiB -> exp17 FP8 "
          "W8A8; Ampere < 19.5 GiB -> FP8 weight-only", "precision": prec, "quant": QUANT if prec != "bf16" else
          "bf16", "utc": utc_now()}
    import transformers

    hw["transformers"] = transformers.__version__
    write_json(RESULTS_DIR / "hardware.json", hw)
    return hw


# ------------------------------------------------------------------------------------------------ STEP 2 units
@torch.no_grad()
def compute_units(model: Any, base: dict) -> None:
    for t in TASKS:
        out = UNITS_DIR / f"units_{t}.npz"
        if out.exists():
            continue
        t0 = time.time()
        dS, tnS, dR, tnR, dC, tnC = [], [], [], [], {}, {}
        for w in TEMPLATE_IDS:
            b, n = base[(t, w, "ban")], base[(t, w, "twin")]
            hb = forward_capture(model, b["ids"], ALL_BLOCKS)
            ht = forward_capture(model, n["ids"], ALL_BLOCKS)
            d = torch.stack([(hb[l] - ht[l]).norm(dim=-1) for l in ALL_BLOCKS]).cpu().numpy()  # [36, P]
            tn = torch.stack([ht[l].norm(dim=-1) for l in ALL_BLOCKS]).cpu().numpy()
            del hb, ht
            p1, se, P = n["p1"], n["spec_end"], n["P"]
            dS.append(d[:, p1:se])
            tnS.append(tn[:, p1:se])
            dR.append(d[:, P - 1])
            tnR.append(tn[:, P - 1])
            dC[w] = d[:, n["cond"]]
            tnC[w] = tn[:, n["cond"]]
            free_cuda()
        nS = np.mean(dS, 0).astype(np.float32)                   # [36, |S|]
        nR = np.mean(dR, 0).astype(np.float32)                   # [36]
        nG = nS[PLAN_BLOCKS].mean(1).astype(np.float32)          # [12] per-token unit of S3
        eS = np.sqrt((nS ** 2).sum(1))                           # S energy per block
        cS1 = (eS / np.maximum(nR, 1e-6)).astype(np.float32)
        arrs = {"nS": nS, "nR": nR, "nG": nG, "cS1": cS1, "nS_per_template": np.stack(dS).astype(np.float32),
                "twin_norm_S": np.mean(tnS, 0).astype(np.float32), "twin_norm_R": np.mean(tnR, 0).astype(np.float32),
                "relS": (nS / np.maximum(np.mean(tnS, 0), 1e-6)).astype(np.float32),
                "relR": (nR / np.maximum(np.mean(tnR, 0), 1e-6)).astype(np.float32)}
        for w in TEMPLATE_IDS:
            arrs[f"nC_{w}"] = dC[w].astype(np.float32)
            arrs[f"cS2_{w}"] = np.sqrt((nS ** 2).sum(1) / np.maximum((dC[w] ** 2).sum(1), 1e-12)).astype(np.float32)
            arrs[f"relC_{w}"] = (dC[w] / np.maximum(tnC[w], 1e-6)).astype(np.float32)
        np.savez(out, **arrs)
        logger.info(f"units {t}: |S|={nS.shape[1]} nS[18] mean {nS[18].mean():.2f}, nR[18] {nR[18]:.2f}, "
                    f"nG[18] {nG[6]:.2f}, cS1[18] {cS1[18]:.1f} ({time.time() - t0:.0f}s)")
    # cross-checks against the FP8 units of exp13 (bench) and exp17
    cc: dict[str, Any] = {}
    from scipy.stats import spearmanr

    for t in TASKS:
        u = np.load(UNITS_DIR / f"units_{t}.npz")
        nS12 = u["nS"][PLAN_BLOCKS]
        refs = {}
        p17 = E17 / "directions" / f"norms_{t}.npy"
        if p17.exists():
            refs["exp17"] = np.load(p17)
        p13 = E13 / "tensors" / f"norms_{t}.npz"
        if p13.exists():
            z = np.load(p13)
            arr = z["norm"] if "norm" in z.files else None
            if arr is not None:
                refs["exp13"] = arr
            cc.setdefault(t, {})["exp13_keys"] = list(z.files)
        for name, ref in refs.items():
            ref = np.asarray(ref, dtype=np.float32)
            if ref.shape != nS12.shape:
                cc.setdefault(t, {})[name] = {"shape_mismatch": [list(ref.shape), list(nS12.shape)]}
                continue
            ratio = nS12 / np.maximum(ref, 1e-6)
            rho = spearmanr(nS12.ravel(), ref.ravel()).correlation
            cc.setdefault(t, {})[name] = {"median_ratio": float(np.median(ratio)), "spearman": float(rho),
                                          "in_0.8_1.25": bool(0.8 <= np.median(ratio) <= 1.25)}
    write_json(RESULTS_DIR / "units_crosscheck.json", cc)
    write_json(UNITS_DIR / "units_sha256.json", {f.name: sha256_file(f) for f in sorted(UNITS_DIR.glob("*.npz"))})


def load_units() -> dict[str, dict[str, np.ndarray]]:
    return {t: dict(np.load(UNITS_DIR / f"units_{t}.npz")) for t in TASKS}


# ------------------------------------------------------------------------------------------------ STEP 3 directions
def pn_dir(t: str, w: str, k: int) -> np.ndarray:
    x = np.random.Generator(np.random.PCG64(stable_seed("PN4", t, w, k))).standard_normal(D_MODEL)
    return (x / np.linalg.norm(x)).astype(np.float32)


def check_engine_dirs() -> dict[str, Any]:
    hashes = read_json(E17 / "directions" / "direction_hashes.json")
    out = {}
    for s in (9002, 9004):
        p = E17 / "directions" / f"rand_{s}.npy"
        v = np.load(p)
        x = np.random.Generator(np.random.PCG64(s)).standard_normal(D_MODEL)
        rebuilt = (x / np.linalg.norm(x)).astype(np.float32)
        out[f"rand_{s}"] = {"sha256": sha256_file(p), "listed_sha256": hashes.get(f"rand_{s}.npy"),
                            "rebuilt_max_abs_diff": float(np.abs(rebuilt - v).max()), "norm": float(np.linalg.norm(v))}
    return out


# ------------------------------------------------------------------------------------------------ STEP 5 geometry
@torch.no_grad()
def c3d_geometry(model: Any, tok: Any, base: dict) -> None:
    if U_TOP5.exists() and GEOM_NPZ.exists():
        return
    t0 = time.time()
    c3 = build_c3d_prompts(tok, base)

    def smean(ids, p1, se):
        h = forward_capture(model, ids, PLAN_BLOCKS)
        return np.stack([h[l][p1:se].mean(0).cpu().numpy() for l in PLAN_BLOCKS])  # [12, D]

    X = np.stack([smean(f["ids"], f["p1"], f["spec_end"]) for f in c3["forced"]])          # [300, 12, D]
    algs = [f["alg"] for f in c3["forced"]]
    twin = np.stack([smean(base[("T1", w, "twin")]["ids"], base[("T1", w, "twin")]["p1"],
                           base[("T1", w, "twin")]["spec_end"]) for w in TEMPLATE_IDS])
    top5 = np.stack([smean(f["ids"], f["p1"], f["spec_end"]) for f in c3["top5"]])
    ban1 = np.stack([smean(base[("T1", w, "ban")]["ids"], base[("T1", w, "ban")]["p1"],
                           base[("T1", w, "ban")]["spec_end"]) for w in TEMPLATE_IDS])
    names = sorted(set(algs))
    cent = {a: X[[i for i, x in enumerate(algs) if x == a]].mean(0) for a in names}         # raw centroids [12, D]

    def unit(v):
        return v / max(float(np.linalg.norm(v)), 1e-12)

    def utop(surv):
        return np.stack([unit(np.mean([cent[y][j] for y in surv], 0) - np.mean([cent[x][j] for x in TOP5], 0))
                         for j in range(len(PLAN_BLOCKS))]).astype(np.float32)

    u_full, u_s7 = utop(SURV), utop(SURV7)
    med = np.median(np.linalg.norm(X, axis=2), axis=0)                                      # [12] median block norm
    Z = (X / med[None, :, None]).reshape(len(X), -1)
    mu = Z.mean(0)
    U_, S_, Vt = np.linalg.svd(Z - mu, full_matrices=False)
    V50 = Vt[:50]
    pc = (Z - mu) @ V50.T
    proj = lambda A: ((A / med[None, :, None]).reshape(len(A), -1) - mu) @ V50.T  # noqa: E731
    np.savez(GEOM_NPZ, pc=pc.astype(np.float32), algs=np.array(algs), pc_twin=proj(twin).astype(np.float32),
             pc_top5ban=proj(top5).astype(np.float32), pc_ban1=proj(ban1).astype(np.float32),
             explained=(S_[:50] ** 2 / (S_ ** 2).sum()).astype(np.float32), med_norm=med.astype(np.float32),
             centroids=np.stack([cent[a] for a in names]).astype(np.float32), centroid_names=np.array(names))
    # separability (held-out nearest centroid in PCA space, leave-one-out)
    acc = {}
    A = np.array(algs)
    for a in names:
        idx = np.where(A == a)[0]
        ok = 0
        for i in idx:
            cs = {b: pc[(A == b) & (np.arange(len(A)) != i)].mean(0) for b in names}
            pred = min(cs, key=lambda b: np.linalg.norm(pc[i] - cs[b]))
            ok += pred == a
        acc[a] = ok / len(idx)
    sep = [y for y in SURV if acc[y] >= 0.5]
    u_sep = utop(sep) if sep and len(sep) < len(SURV) else u_full
    chosen = "full" if len(sep) == len(SURV) else ("separable_survivors" if sep else "full_fallback")
    u_use = u_full if chosen != "separable_survivors" else u_sep
    np.savez(U_TOP5, u_top5=u_use, u_full=u_full, u_surv7=u_s7, u_sep=u_sep, blocks=np.array(PLAN_BLOCKS))
    cos = {"full_vs_surv7": [float(a @ b) for a, b in zip(u_full, u_s7)],
           "full_vs_sep": [float(a @ b) for a, b in zip(u_full, u_sep)],
           "cross_block_full": [float(u_full[j] @ u_full[j + 1]) for j in range(len(PLAN_BLOCKS) - 1)]}
    write_json(RESULTS_DIR / "plan_geometry_T1_raw.json",
               {"n_forced": len(algs), "per_alg": {a: algs.count(a) for a in names}, "nearest_centroid_acc": acc,
                "separable_survivors": sep, "u_top5_version": chosen, "cosines": cos,
                "pca_explained_50": float((S_[:50] ** 2).sum() / (S_ ** 2).sum()), "seconds": time.time() - t0,
                "sha256": {"u_top5.npz": sha256_file(U_TOP5), "plan_geometry_T1.npz": sha256_file(GEOM_NPZ)}})
    logger.info(f"C3d geometry: {len(algs)} forced prompts, nearest-centroid acc {acc}, u_top5 = {chosen} "
                f"({time.time() - t0:.0f}s)")


# ------------------------------------------------------------------------------------------------ contexts
class Ctx:
    """Per (task, template): clean twin prefill (shared by TWIN/S3 rows) with every block output captured."""

    def __init__(self, model: Any, base: dict, units: dict, t: str, w: str):
        self.model, self.t, self.w = model, t, w
        n = base[(t, w, "twin")]
        self.rec = n
        self.ids = n["ids"]
        self.P, self.p1, self.se = n["P"], n["p1"], n["spec_end"]
        dev = model.device
        cap: dict[int, torch.Tensor] = {}

        def mk(l):
            def g(h):
                cap[l] = h[0].float().clone()
            return g
        self.pre = prefill(model, self.ids, capture={l: mk(l) for l in ALL_BLOCKS})
        self.H = cap
        self.r_logp = torch.log_softmax(self.pre["r_logits"].double(), -1)
        self.idx = {"S": torch.arange(self.p1, self.se, device=dev), "R": torch.tensor([self.P - 1], device=dev),
                    "COND": torch.tensor(n["cond"], device=dev)}
        u = units[t]
        self.nS = torch.tensor(u["nS"], device=dev)
        self.nR = torch.tensor(u["nR"], device=dev)
        self.nG = torch.tensor(u["nG"], device=dev)
        self.cS1 = torch.tensor(u["cS1"], device=dev)
        self.nC = torch.tensor(u[f"nC_{w}"], device=dev)
        self.cS2 = torch.tensor(u[f"cS2_{w}"], device=dev)
        self.eng = None
        if t in ("T03", "T2"):
            self.eng = torch.tensor(np.load(E17 / "directions" / f"norms_{t}.npy"), device=dev)  # [12, |S|]
        self.shared: dict[str, Any] = {}

    def target(self, site: str, l: int, alpha: float) -> torch.Tensor:
        if site in ("S0", "S4", "S5", "TOP5"):
            return alpha * self.nS[l]
        if site == "ENG":
            return alpha * self.eng[l - PLAN_BLOCKS[0]]
        if site == "S1":
            return alpha * self.nR[l].reshape(1)
        if site == "S1E":
            return alpha * (self.cS1[l] * self.nR[l]).reshape(1)
        if site == "S2":
            return alpha * self.nC[l]
        if site == "S2E":
            return alpha * self.cS2[l] * self.nC[l]
        raise ValueError(site)


def direction_for(row: dict[str, Any], dev: torch.device) -> dict[int, torch.Tensor]:
    site = row["site"]
    if site == "TOP5":
        z = np.load(U_TOP5)["u_top5"]
        return {l: torch.tensor(z[j], device=dev) for j, l in enumerate(PLAN_BLOCKS)}
    if site == "ENG":
        s = int(row["arm"].split("_r")[1].split("_")[0])
        v = torch.tensor(np.load(E17 / "directions" / f"rand_{s}.npy"), device=dev)
        return {l: v for l in PLAN_BLOCKS}
    v = torch.tensor(pn_dir(row["task"], row["w"], row["k"]), device=dev)
    return {l: v for l in SITE_BLOCKS.get(site, PLAN_BLOCKS)}


@torch.no_grad()
def row_prefill(ctx: Ctx, row: dict[str, Any], blocks_override: list[int] | None = None) -> tuple[dict, dict]:
    site, alpha = row["site"], row["alpha"]
    dev = ctx.model.device
    blocks = blocks_override or SITE_BLOCKS[site]
    idx = ctx.idx[SITE_POS[site]]
    u = direction_for(row, dev)
    target = {l: ctx.target(site, l, alpha) for l in blocks}
    h_ref = {l: ctx.H[l][idx] for l in blocks}
    edits = make_prefill_edits(blocks, idx, u, target, h_ref)
    stats: dict[str, Any] = {}
    R = ctx.P - 1

    def mk(l):
        def g(h):
            if l in NORM_BLOCKS:
                stats[("R", l)] = (h[0, R].float() - ctx.H[l][R]).norm()
            if l in target:
                dd = h[0, idx].float() - h_ref[l]
                along = dd @ u[l]
                tg = target[l]
                m = tg.abs() > 1e-6
                stats[("along", l)] = along.mean()
                stats[("tot", l)] = dd.norm(dim=-1).mean()
                stats[("tgt", l)] = tg.mean()
                stats[("relerr", l)] = ((along - tg).abs()[m] / tg.abs()[m]).mean() if bool(m.any()) else \
                    torch.zeros((), device=dev)
        return g
    cap_blocks = sorted(set(blocks) | set(NORM_BLOCKS))
    pre = prefill(ctx.model, ctx.ids, edits=edits, capture={l: mk(l) for l in cap_blocks})
    lp = torch.log_softmax(pre["r_logits"].double(), -1)
    kl = float((lp.exp() * (lp - ctx.r_logp)).sum())
    keys = list(stats)
    vals = torch.stack([stats[k].float().reshape(()) for k in keys]).cpu().numpy() if keys else []
    st = {}
    for k, v in zip(keys, vals):
        st.setdefault(k[0], {})[int(k[1])] = float(v)
    log = {"realised_disp_R": st.get("R", {}), "along_u": st.get("along", {}), "total_disp_site": st.get("tot", {}),
           "target_mean": st.get("tgt", {}), "relerr_along_u": st.get("relerr", {}), "first_token_kl": kl,
           "top1_first_token": int(lp.argmax()), "twin_top1_first_token": int(ctx.r_logp.argmax())}
    return pre, log


# ------------------------------------------------------------------------------------------------ batches
_FENCE: dict[str, torch.Tensor] = {}


def run_batch(model: Any, tok: Any, ctx: Ctx, rows: list[dict[str, Any]], batch_id: str,
              write: bool = True, keep_shadow_states: bool = False, no_stop: bool = False,
              block_override: dict[int, list[int]] | None = None) -> list[dict[str, Any]]:
    assert len(rows) == BATCH, len(rows)
    t0 = time.time()
    dev = model.device
    if "m" not in _FENCE:
        _FENCE["m"] = fence_token_mask(tok, dev)
    groups, logs = [], []
    hooked, shadow, s3u, s3a = [], [], [], []
    for i, r in enumerate(rows):
        us = [u_stream(ctx.t, ctx.w, r["k"])]
        site = r["site"]
        if site in ("TWIN", "TWIN_X") or site == "S3":
            groups.append({"pre": ctx.pre, "us": us})
            logs.append({})
            if site == "S3":
                (shadow if r["shadow"] else hooked).append(i)
                if not r["shadow"]:
                    s3u.append(torch.tensor(pn_dir(r["task"], r["w"], r["k"])))
                    s3a.append(r["alpha"])
            continue
        key = None
        if site in ("TOP5", "ENG"):  # one fixed direction per (template, alpha): prefill shared by its rows
            key = (site, r["arm"], r["alpha"])
            if key in ctx.shared:
                groups.append({"pre": ctx.shared[key][0], "us": us})
                logs.append(ctx.shared[key][1])
                continue
        bo = block_override.get(i) if block_override else None
        pre, lg = row_prefill(ctx, r, blocks_override=bo)
        if key is not None:
            ctx.shared[key] = (pre, lg)
        groups.append({"pre": pre, "us": us})
        logs.append(lg)
    s3 = None
    if hooked:
        # pair order: shadows sorted to match hooked rows by slot k
        hk = sorted(hooked, key=lambda i: rows[i]["k"])
        sh = sorted(shadow, key=lambda i: rows[i]["k"])
        assert [rows[i]["k"] for i in hk] == [rows[i]["k"] for i in sh]
        order = {i: j for j, i in enumerate(hooked)}
        U = torch.stack([s3u[order[i]] for i in hk])
        al = torch.tensor([s3a[order[i]] for i in hk], dtype=torch.float32)
        tgt = {l: (al.to(dev) * ctx.nG[j]) for j, l in enumerate(PLAN_BLOCKS)}
        s3 = {"hooked": hk, "shadow": sh, "u": U, "target": tgt, "blocks": PLAN_BLOCKS, "steps": S3_STEPS,
              "log_blocks": [23, 35], "keep_shadow_states": keep_shadow_states}
    res = sample(model, groups, fence_mask=_FENCE["m"], s3=s3, no_stop=no_stop)
    out = []
    for i, (r, rs) in enumerate(zip(rows, res)):
        if r["shadow"]:
            continue
        text = tok.decode(rs["token_ids"], skip_special_tokens=True)
        rec = {"model": MODEL_ID, "model_revision": MODEL_REVISION, "quant": QUANT, "decoding": DECODING,
               "task": r["task"], "template": r["w"], "k": r["k"], "slot": f"{r['task']}|{r['w']}|{r['k']}",
               "arm": r["arm"], "site": r["site"], "alpha": r["alpha"], "prio": r["prio"],
               "direction_seed": (stable_seed("PN4", r["task"], r["w"], r["k"]) if r["site"] not in
                                  ("TOP5", "ENG", "TWIN", "TWIN_X") else r["arm"]),
               "uniform_seed": stable_seed(r["task"], r["w"], r["k"]), "temperature": 1.0, "top_k": None,
               "thinking": False, "prompt_sha256": ctx.rec["prompt_sha256"], "finish_reason": rs["finish_reason"],
               "n_new_tokens": rs["n_tokens"], "batch_id": batch_id, "text": text, "token_ids": rs["token_ids"],
               "utc": utc_now()}
        lg = dict(logs[i])
        if "s3" in rs:
            lg["s3"] = rs["s3"]
        rec["realised_disp_R35"] = lg.get("realised_disp_R", {}).get(35)
        rec["first_token_kl"] = lg.get("first_token_kl")
        if r["site"] == "S3" and "s3" in rs:
            rec["s3_kl_mean"] = rs["s3"]["kl_mean_steps1_32"]
            rec["s3_disp35_mean"] = rs["s3"]["disp_mean"].get(35)
        out.append(rec)
        logs[i] = {"key": f"{r['task']}|{r['w']}|{r['arm']}|{r['k']}", **lg}
    if write:
        append_jsonl(RAW, out)
        append_jsonl(ROWLOG, [lg for lg, r in zip(logs, rows) if not r["shadow"] and lg])
        dt = time.time() - t0
        append_jsonl(TIMING, [{"batch_id": batch_id, "task": ctx.t, "w": ctx.w, "seconds": dt,
                               "steps": res[0]["steps"], "arms": sorted({r["arm"] for r in rows}),
                               "max_alpha": max(r["alpha"] for r in rows), "utc": utc_now()}])
        logger.info(f"{batch_id}: {dt:.1f}s, {res[0]['steps']} steps, arms {sorted({r['arm'] for r in rows})}")
    if keep_shadow_states:
        out.append({"_res": res})
    return out


def done_keys() -> set[str]:
    return {f"{r['task']}|{r['template']}|{r['arm']}|{r['k']}" for r in read_jsonl(RAW)}


# ------------------------------------------------------------------------------------------------ GPU tests
@torch.no_grad()
def gpu_tests(model: Any, tok: Any, base: dict, units: dict) -> dict[str, Any]:
    outp = RESULTS_DIR / "unit_tests_gpu.json"
    if outp.exists():
        return read_json(outp)
    res: dict[str, Any] = {"utc": utc_now()}
    for t in ("T03", "T1"):
        ctx = Ctx(model, base, units, t, "W1")
        K = [100, 101, 102, 103]
        mkr = lambda arm, k, shadow=False: dict(SCH._row(t, "W1", k, arm, 0, shadow))  # noqa: E731
        A = [mkr("TWIN", k) for k in K] + [mkr(a, k) for a in ("S0_a0", "S1_a0", "S2_a0", "S4_a0") for k in K]
        oa = run_batch(model, tok, ctx, A, f"U:{t}:A", write=False)
        Bq = [mkr("S5_a0", k) for k in K] + [x for k in K for x in (mkr("S3_a0", k), mkr("S3_a0", k, True))] + \
             [mkr("TWIN", k) for k in K] + [mkr("S5_a1", k) for k in K]
        bo = {i: [35] for i in range(16, 20)}  # U7: block-35-only edit at alpha 1
        ob = run_batch(model, tok, ctx, Bq, f"U:{t}:B", write=False, block_override=bo)
        twin = {r["k"]: r["token_ids"] for r in oa if r["arm"] == "TWIN"}
        u1 = all(r["token_ids"] == twin[r["k"]] for r in ob if r["arm"] == "TWIN")
        u2 = {a: all(r["token_ids"] == twin[r["k"]] for r in oa + ob if r["arm"] == a)
              for a in ("S0_a0", "S1_a0", "S2_a0", "S4_a0", "S5_a0", "S3_a0")}
        u7 = all(r["token_ids"] == twin[r["k"]] for r in ob if r["arm"] == "S5_a1")
        res[t] = {"U1_crn_determinism_two_compositions": u1, "U2_identity_alpha0": u2, "U7_block35_noop": u7,
                  "twin_first_tokens": {k: tok.decode(v[:12]) for k, v in twin.items()}}
        # U3 dose (alpha 1, all prefill sites) and U4 shadow fidelity (S3 alpha 1)
        D = [mkr(a, k) for a in ("S0_a1", "S1_a1", "S2_a1", "S4_a1") for k in K] + \
            [x for k in K for x in (mkr("S3_a1", k), mkr("S3_a1", k, True))]
        rows_d = D[:16] + D[16:20]
        od = run_batch(model, tok, ctx, rows_d, f"U:{t}:D", write=False, keep_shadow_states=True)
        rr = od[-1]["_res"]
        Eq = [mkr("S5_a1", k) for k in K] + [mkr("S1E_a1", k) for k in K] + [mkr("S2E_a1", k) for k in K] + \
             [mkr("TWIN", k) for k in K] + [x for k in K[:2] for x in (mkr("S3_a1", k), mkr("S3_a1", k, True))]
        oe = run_batch(model, tok, ctx, Eq, f"U:{t}:E", write=False)
        rel = {}
        for site in ("S0", "S1", "S2", "S4", "S5", "S1E", "S2E"):
            arm = f"{site}_a1"
            row = SCH._row(t, "W1", 100, arm, 0)
            _, lg = row_prefill(ctx, row)
            rel[site] = {"max_relerr_along_u": max(lg["relerr_along_u"].values()) if lg["relerr_along_u"] else None,
                         "mean_along_u": float(np.mean(list(lg["along_u"].values()))),
                         "mean_target": float(np.mean(list(lg["target_mean"].values()))),
                         "realised_disp_R35": lg["realised_disp_R"].get(35), "first_token_kl": lg["first_token_kl"]}
        # S3: along-u displacement relative to the shadow equals the target by construction; check from states
        hk_states = od[-1]["_res"][0].get("_hooked_states") or []
        sh_states = od[-1]["_res"][0].get("_shadow_states") or []
        u4 = {}
        if sh_states:
            s3_rows = [i for i, r in enumerate(rows_d) if r["site"] == "S3" and not r["shadow"]]
            hk = sorted(s3_rows, key=lambda i: rows_d[i]["k"])
            j0 = 0
            gen = rr[hk[j0]]["token_ids"][:S3_STEPS]
            ids_tf = ctx.ids + gen
            cap = forward_capture(model, ids_tf, [23])[23]  # [P + n, D]
            n = min(len(sh_states), len(gen))
            shs = torch.stack([sh_states[s][j0] for s in range(n)]).to(model.device)
            tf = cap[ctx.P: ctx.P + n]
            cos = torch.nn.functional.cosine_similarity(shs, tf, dim=-1)
            relerr = ((shs - tf).norm(dim=-1) / tf.norm(dim=-1))
            u4 = {"n_steps": n, "min_cos": float(cos.min()), "max_rel_norm_err": float(relerr.max()),
                  "pass": bool(cos.min() > 0.9999 and relerr.max() < 1e-2)}
            hks = torch.stack([hk_states[s][j0] for s in range(n)]).to(model.device)
            u3_s3 = float(((hks - shs) @ torch.tensor(pn_dir(t, "W1", rows_d[hk[j0]]["k"]),
                                                      device=model.device)).mean())
            rel["S3"] = {"mean_along_u_vs_shadow_block23": u3_s3, "target_block23": float(ctx.nG[-1])}
        res[t]["U3_dose_alpha1"] = rel
        res[t]["U4_shadow_fidelity"] = u4
        res[t]["s3_logs_alpha1"] = [r.get("s3_kl_mean") for r in od if isinstance(r, dict) and r.get("site") == "S3"]
        res[t]["smoke_finish"] = [r["finish_reason"] for r in oa + ob + oe if "finish_reason" in r]
        del ctx
        free_cuda()
    # U6 memory: largest prompt (T1), fixed B, full max_new without stopping
    torch.cuda.reset_peak_memory_stats()
    wmax = max(TEMPLATE_IDS, key=lambda w: base[("T1", w, "twin")]["P"])
    ctx = Ctx(model, base, units, "T1", wmax)
    rows = [SCH._row("T1", wmax, 200 + i, "TWIN", 0) for i in range(BATCH)]
    t0 = time.time()
    run_batch(model, tok, ctx, rows, "U6", write=False, no_stop=True)
    res["U6_memory"] = {"P": ctx.P, "max_new": MAX_NEW_TOKENS, "batch": BATCH, "seconds": time.time() - t0,
                        "peak_gib": torch.cuda.max_memory_allocated() / 1024 ** 3, "ok": True}
    del ctx
    free_cuda()
    ok = all(res[t]["U1_crn_determinism_two_compositions"] and all(res[t]["U2_identity_alpha0"].values()) and
             res[t]["U7_block35_noop"] for t in ("T03", "T1"))
    res["all_identity_tests_pass"] = ok
    write_json(outp, res)
    logger.info(f"GPU tests: identity pass={ok}; U6 peak {res['U6_memory']['peak_gib']:.2f} GiB "
                f"in {res['U6_memory']['seconds']:.0f}s")
    return res


# ------------------------------------------------------------------------------------------------ sampling
def run_batches(model: Any, tok: Any, base: dict, units: dict, batches: list[dict[str, Any]], label: str,
                deadline: float | None = None) -> int:
    done = done_keys()
    ctxs: dict[tuple[str, str], Ctx] = {}
    n = 0
    for b in batches:
        keys = [f"{r['task']}|{r['w']}|{r['arm']}|{r['k']}" for r in b["rows"] if not r["shadow"]]
        if all(k in done for k in keys):
            continue
        if deadline is not None and time.time() > deadline:
            logger.warning(f"{label}: deadline reached before {b['id']}")
            break
        key = (b["task"], b["w"])
        if key not in ctxs:
            for kk in list(ctxs):
                del ctxs[kk]
            free_cuda()
            ctxs[key] = Ctx(model, base, units, *key)
        run_batch(model, tok, ctxs[key], b["rows"], b["id"])
        n += 1
        if Path(RESULTS_DIR / "STOP_SAMPLING").exists():
            logger.warning("STOP_SAMPLING file found; stopping")
            break
    return n


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="all", choices=["prep", "tests", "engine", "smoke", "main", "all"])
    ap.add_argument("--budget-hours", type=float, default=2.6)
    ap.add_argument("--wait-commit", type=int, default=1)
    args = ap.parse_args()
    setup_logging("gpu_main")
    torch.backends.cuda.matmul.allow_tf32 = False
    t_start = time.time()
    hw = hardware_and_precision()
    logger.info(f"hardware: {hw}")
    assert hw["precision"] == "fp8_w8a8", "this run implements the FP8 W8A8 branch of the frozen precision rule"
    tok, model = load_model(fp8=True)
    base = load_base(tok)
    save_positions(tok, base)
    compute_units(model, base)
    units = load_units()
    write_json(RESULTS_DIR / "engine_dirs.json", check_engine_dirs())
    c3d_geometry(model, tok, base)
    if args.stage == "prep":
        return
    gpu_tests(model, tok, base, units)
    if args.stage == "tests":
        return
    # STEP 7 engine check -- commit #0 must exist first
    c0 = PRED_DIR / "commit0.done"
    while not c0.exists():
        logger.info("waiting for commit #0 (predictions/commit0.done) ...")
        time.sleep(20)
    all_rows = SCH.cell_rows()
    batches = SCH.pack(all_rows)
    write_json(RESULTS_DIR / "schedule_summary.json", SCH.summary(batches))
    eng = [b for b in batches if any(r["site"] == "ENG" for r in b["rows"])]
    run_batches(model, tok, base, units, eng, "engine_check")
    if args.stage == "engine":
        return
    # stage 10 smoke (reserved slots k >= 100)
    sm = SCH.smoke_rows()
    smb = SCH.pack(sm)
    run_batches(model, tok, base, units, smb, "smoke")
    if args.stage == "smoke":
        return
    c1 = PRED_DIR / "commit1.done"
    while args.wait_commit and not c1.exists():
        logger.info("waiting for commit #1 (predictions/commit1.done) before decisive sampling ...")
        time.sleep(20)
    rest = [b for b in batches if b not in eng]
    t_main = time.time()
    deadline = t_start + args.budget_hours * 3600
    # stage 100 (first 5 batches), timing extrapolation, then full
    run_batches(model, tok, base, units, rest[:5], "stage100", deadline=deadline)
    tm = read_jsonl(TIMING)
    if tm:
        sec = float(np.mean([x["seconds"] for x in tm[-5:]]))
        proj_h = sec * len(rest) / 3600
        write_json(RESULTS_DIR / "timing_projection.json",
                   {"mean_batch_s_stage100": sec, "n_batches_rest": len(rest), "projected_hours": proj_h,
                    "budget_hours_total": args.budget_hours, "elapsed_h": (time.time() - t_start) / 3600,
                    "utc": utc_now()})
        logger.info(f"stage 100: {sec:.1f}s/batch -> projected {proj_h:.2f} h for {len(rest)} batches")
    run_batches(model, tok, base, units, rest, "full", deadline=deadline)
    write_json(RESULTS_DIR / "sampling_done.json", {"utc": utc_now(), "hours": (time.time() - t_main) / 3600,
                                                     "n_raw": len(read_jsonl(RAW))})
    logger.info("sampling finished")


if __name__ == "__main__":
    main()
