#!/usr/bin/env python3
"""Sites, units, directions and fixed-shape batches (exp20 gpu_main Ctx/row_prefill/run_batch, ban-free unit).

Per (task, template) a Ctx holds the clean twin prefill with every block output captured (fp32 on GPU), the
position classes S / R / COND and the ban-free units n[l, p] = ||h_twin[l, p]|| * r_Q(l):
  S0/S4/S5/TOP5/TOP3 target alpha * n[l, S];  S1 alpha * n[l, R];  S1E alpha * c * n[l, R] with
  c = sqrt(sum_{l in 12-23, p in S} n[l,p]^2 / sum_{l in 12-23} n[l,R]^2) (energy-matched to S0 at the same alpha);
  S2 alpha * n[l, COND] (every COND position, frame tokens included);  S3 alpha * n_G[l], n_G[l] = r_Q(l) * mean_S
  ||h_twin[l, p]|| at generated input positions 1-32 against the shadow;  ENG (positive control U8) alpha * exp17's
  FP8 per-position ban unit (inputs/exp17/directions/norms_<task>.npy) along rand_<seed>.
Every prefill row logs the realised displacement at R for blocks 0-35 (block 35 = the final-norm input), the realised
along-u displacement and its relative error at every hooked block, the total displacement ||d_p|| and ||d_p||/||h_p||
summaries, the first-token KL, and the post-edit S-mean at blocks 18 and 23 (S-d plan states).
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
from loguru import logger

from cfg import (ALL_BLOCKS, BATCH, D_MODEL, DATA_DIR, DIR_DIR, DIRECTION_NS, E17, E20, MAX_NEW, MODEL_ID,
                 MODEL_REVISION, PLAN_BLOCKS, PRECISION, RESULTS_DIR, ROOT, S3_STEPS, SITE_BLOCKS, SITE_POS,
                 append_jsonl, read_json, sha256_file, stable_seed, utc_now)
from engine_w16 import fence_token_mask, prefill, sample, u_stream
from hooks import make_prefill_edits

RAW = DATA_DIR / "samples_raw.jsonl"
TIMING = RESULTS_DIR / "timing_batches.jsonl"
HOOK_SHA = None
STATE_BLOCKS = (18, 23)


def hook_sha256() -> str:
    global HOOK_SHA
    if HOOK_SHA is None:
        import hashlib

        h = hashlib.sha256()
        for f in ("sites.py", "hooks.py"):
            h.update((ROOT / "src" / f).read_bytes())
        HOOK_SHA = h.hexdigest()
    return HOOK_SHA


# ------------------------------------------------------------------------------------------------ r_Q
def load_rq() -> np.ndarray:
    """r_Q per block 0-35 as frozen in units/r_Q_all.json (key 'r_Q_used')."""
    d = read_json(ROOT / "units" / "r_Q_all.json")
    return np.array([d["r_Q_used"][str(l)] for l in ALL_BLOCKS], dtype=np.float32)


# ------------------------------------------------------------------------------------------------ directions
def pn_seed(t: str, w: str, k: int) -> int:
    return stable_seed(DIRECTION_NS, t, w, k)


def pn_dir(t: str, w: str, k: int) -> np.ndarray:
    x = np.random.Generator(np.random.PCG64(pn_seed(t, w, k))).standard_normal(D_MODEL)
    return (x / np.linalg.norm(x)).astype(np.float32)


def push_file(task: str, site: str) -> Path:
    return DIR_DIR / f"u_push_{task}_{site}.npz"


def direction_for(row: dict[str, Any], dev: torch.device) -> dict[int, torch.Tensor]:
    site = row["site"]
    if site in ("TOP5", "TOP3"):
        z = np.load(push_file(row["task"], site))["u"]
        return {l: torch.tensor(z[j], device=dev) for j, l in enumerate(PLAN_BLOCKS)}
    if site == "ENG":
        s = int(row["arm"].split("_r")[1].split("_")[0])
        v = torch.tensor(np.load(E17 / "directions" / f"rand_{s}.npy").astype(np.float32), device=dev)
        return {l: v for l in PLAN_BLOCKS}
    v = torch.tensor(pn_dir(row["task"], row["w"], row["k"]), device=dev)
    return {l: v for l in SITE_BLOCKS.get(site, PLAN_BLOCKS)}


def direction_seed(row: dict[str, Any]) -> Any:
    if row["site"] in ("TWIN", "TWIN_X"):
        return None
    if row["site"] in ("TOP5", "TOP3", "ENG"):
        return row["arm"]
    return pn_seed(row["task"], row["w"], row["k"])


# ------------------------------------------------------------------------------------------------ context
class Ctx:
    """Per (task, template): clean twin prefill (shared by TWIN / S3 rows) with every block output captured."""

    def __init__(self, model: Any, base: dict, rq: np.ndarray, t: str, w: str):
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
        self.rq = torch.tensor(rq, device=dev)
        self.norm = {l: cap[l].norm(dim=-1) for l in ALL_BLOCKS}                  # [P] per block
        self.nS = {l: self.norm[l][self.idx["S"]] * self.rq[l] for l in ALL_BLOCKS}
        self.nR = {l: self.norm[l][self.idx["R"]] * self.rq[l] for l in ALL_BLOCKS}
        self.nC = {l: self.norm[l][self.idx["COND"]] * self.rq[l] for l in ALL_BLOCKS}
        self.nG = {l: self.rq[l] * self.norm[l][self.idx["S"]].mean() for l in PLAN_BLOCKS}
        eS = sum(float((self.nS[l] ** 2).sum()) for l in PLAN_BLOCKS)
        eR = sum(float((self.nR[l] ** 2).sum()) for l in PLAN_BLOCKS)
        self.cE = float(np.sqrt(eS / max(eR, 1e-12)))
        self.eng = None
        p = E17 / "directions" / f"norms_{t}.npy"
        if p.exists():
            self.eng = torch.tensor(np.load(p).astype(np.float32), device=dev)  # [12, |S|] FP8 ban unit (exp17)
        self.ban4 = None
        p4 = E20 / "units" / f"units_{t}.npz"
        if p4.exists():
            self.ban4 = np.load(p4)
        self.shared: dict[Any, Any] = {}

    def target(self, site: str, l: int, alpha: float) -> torch.Tensor:
        if site in ("S0", "S4", "S5", "TOP5", "TOP3"):
            return alpha * self.nS[l]
        if site == "ENG":
            return alpha * self.eng[l - PLAN_BLOCKS[0]]
        if site == "S1":
            return alpha * self.nR[l].reshape(1)
        if site == "S1E":
            return alpha * self.cE * self.nR[l].reshape(1)
        if site == "S2":
            return alpha * self.nC[l]
        raise ValueError(site)

    def ban_unit_iter4(self, site: str) -> float | None:
        """Mean iteration-4 FP8 ban unit at the site (exp20 units npz), logged beside every row."""
        if self.ban4 is None:
            return None
        z = self.ban4
        bl = SITE_BLOCKS.get(site, PLAN_BLOCKS)
        if site in ("S0", "S4", "S5", "TOP5", "TOP3"):
            return float(z["nS"][bl].mean())
        if site in ("S1", "S1E"):
            return float(z["nR"][bl].mean())
        if site == "S2":
            k = f"nC_{self.w}"
            return float(z[k][bl].mean()) if k in z.files else None
        if site == "S3":
            return float(z["nG"].mean())
        return None


@torch.no_grad()
def row_prefill(ctx: Ctx, row: dict[str, Any], blocks_override: list[int] | None = None,
                keep_arrays: bool = True) -> tuple[dict, dict]:
    site, alpha = row["site"], row["alpha"]
    dev = ctx.model.device
    blocks = blocks_override or SITE_BLOCKS[site]
    idx = ctx.idx[SITE_POS[site]]
    u = direction_for(row, dev)
    target = {l: ctx.target(site, l, alpha) for l in blocks}
    h_ref = {l: ctx.H[l][idx] for l in blocks}
    edits = make_prefill_edits(blocks, idx, u, target, h_ref)
    stats: dict[Any, torch.Tensor] = {}
    arrays: dict[str, np.ndarray] = {}
    R = ctx.P - 1
    last = max(blocks)
    S_idx = ctx.idx["S"]

    def mk(l):
        def g(h):
            stats[("R", l)] = (h[0, R].float() - ctx.H[l][R]).norm()
            if l in STATE_BLOCKS:
                stats[("smean", l)] = h[0, S_idx].float().mean(0)
            if l in target:
                dd = h[0, idx].float() - h_ref[l]
                along = dd @ u[l]
                tg = target[l]
                m = tg.abs() > 1e-6
                dn = dd.norm(dim=-1)
                hn = ctx.norm[l][idx]
                stats[("along", l)] = along.mean()
                stats[("tot", l)] = dn.mean()
                stats[("totmax", l)] = dn.max()
                stats[("rel", l)] = (dn / hn.clamp(min=1e-6)).mean()
                stats[("relmn", l)] = dn.mean() / hn.mean().clamp(min=1e-6)
                stats[("tgt", l)] = tg.mean()
                stats[("relerr", l)] = ((along - tg).abs()[m] / tg.abs()[m]).max() if bool(m.any()) else \
                    torch.zeros((), device=dev)
                if keep_arrays and l == last:
                    stats[("arr_d", l)] = dn
                    stats[("arr_h", l)] = hn
        return g
    pre = prefill(ctx.model, ctx.ids, edits=edits, capture={l: mk(l) for l in ALL_BLOCKS})
    lp = torch.log_softmax(pre["r_logits"].double(), -1)
    kl = float((lp.exp() * (lp - ctx.r_logp)).sum())
    st: dict[str, dict[int, float]] = {}
    for k, v in stats.items():
        if k[0] in ("smean", "arr_d", "arr_h"):
            continue
        st.setdefault(k[0], {})[int(k[1])] = float(v.float().reshape(()).item())
    if keep_arrays:
        arrays = {"d_last": stats[("arr_d", last)].cpu().numpy().astype(np.float32),
                  "h_last": stats[("arr_h", last)].cpu().numpy().astype(np.float32)}
    for l in STATE_BLOCKS:
        if ("smean", l) in stats:
            arrays[f"smean{l}"] = stats[("smean", l)].cpu().numpy().astype(np.float32)
    rel = st.get("rel", {})
    log = {"disp_R": st.get("R", {}), "along_u": st.get("along", {}), "total_disp_mean": st.get("tot", {}),
           "total_disp_max": st.get("totmax", {}), "disp_over_h_mean": rel, "disp_over_h_ratio_of_means":
           st.get("relmn", {}), "target_mean": st.get("tgt", {}), "relerr_along_u_max": st.get("relerr", {}),
           "first_token_kl": kl, "disp_R35": st.get("R", {}).get(35),
           "disp_over_h_site_mean": float(np.mean(list(rel.values()))) if rel else None,
           "disp_over_h_site_ratio_of_means": float(np.mean(list(st.get("relmn", {}).values())))
           if st.get("relmn") else None,
           "banfree_unit_mean": float(np.mean([float(target[l].mean()) for l in blocks]) / max(alpha, 1e-12))
           if alpha else None,
           "iter4_ban_unit_mean": ctx.ban_unit_iter4(site), "energy_c": ctx.cE if site == "S1E" else None}
    return pre, {"log": log, "arrays": arrays}


# ------------------------------------------------------------------------------------------------ batches
_FENCE: dict[str, torch.Tensor] = {}
ROWARR: dict[str, dict[str, list]] = {}


def twin_smeans(ctx: Ctx) -> dict[str, np.ndarray]:
    return {f"smean{l}": ctx.H[l][ctx.idx["S"]].mean(0).cpu().numpy().astype(np.float32) for l in STATE_BLOCKS}


def run_batch(model: Any, tok: Any, ctx: Ctx, rows: list[dict[str, Any]], batch_id: str, write: bool = True,
              keep_shadow_states: bool = False, no_stop: bool = False,
              block_override: dict[int, list[int]] | None = None, max_new: int | None = None) -> list[dict]:
    assert len(rows) == BATCH[ctx.t], (len(rows), BATCH[ctx.t])
    t0 = time.time()
    dev = model.device
    mx = max_new or MAX_NEW[ctx.t]
    if "m" not in _FENCE:
        _FENCE["m"] = fence_token_mask(tok, dev)
    groups, logs = [], []
    hooked, shadow, s3u, s3a = [], [], [], []
    for i, r in enumerate(rows):
        us = [u_stream(ctx.t, ctx.w, r["k"])]
        site = r["site"]
        if site in ("TWIN", "TWIN_X") or site == "S3":
            groups.append({"pre": ctx.pre, "us": us})
            logs.append({"log": {}, "arrays": twin_smeans(ctx) if site == "TWIN" else {}})
            if site == "S3":
                (shadow if r["shadow"] else hooked).append(i)
                if not r["shadow"]:
                    s3u.append(torch.tensor(pn_dir(r["task"], r["w"], r["k"])))
                    s3a.append(r["alpha"])
            continue
        key = None
        if site in ("TOP5", "TOP3", "ENG"):  # one fixed direction per (template, alpha): prefill shared by its rows
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
        hk = sorted(hooked, key=lambda i: (rows[i]["k"], rows[i]["alpha"]))
        sh = sorted(shadow, key=lambda i: (rows[i]["k"], rows[i]["alpha"]))
        assert [rows[i]["k"] for i in hk] == [rows[i]["k"] for i in sh]
        assert [rows[i]["alpha"] for i in hk] == [rows[i]["alpha"] for i in sh]
        order = {i: j for j, i in enumerate(hooked)}
        U = torch.stack([s3u[order[i]] for i in hk])
        al = torch.tensor([s3a[order[i]] for i in hk], dtype=torch.float32, device=dev)
        tgt = {l: (al * ctx.nG[l]) for l in PLAN_BLOCKS}
        s3 = {"hooked": hk, "shadow": sh, "u": U, "target": tgt, "blocks": PLAN_BLOCKS, "steps": S3_STEPS,
              "log_blocks": [23, 35], "keep_shadow_states": keep_shadow_states}
    res = sample(model, groups, mx, fence_mask=_FENCE["m"], s3=s3, no_stop=no_stop)
    out = []
    for i, (r, rs) in enumerate(zip(rows, res)):
        if r["shadow"]:
            continue
        text = tok.decode(rs["token_ids"], skip_special_tokens=True)
        lg = dict(logs[i]["log"])
        if "s3" in rs:
            lg["s3"] = rs["s3"]
            lg["banfree_unit_mean"] = float(np.mean([float(ctx.nG[l]) for l in PLAN_BLOCKS]))
            lg["iter4_ban_unit_mean"] = ctx.ban_unit_iter4("S3")
        rec = {"model": MODEL_ID, "model_revision": MODEL_REVISION, "precision": PRECISION, "kernel": "sdpa",
               "checkpoint": f"{MODEL_ID}@{MODEL_REVISION}", "unit": f"existing:{r['task']}",
               "unit_kind": "path" if r["task"] in ("T1", "T2") else "bench", "task": r["task"],
               "template": r["w"], "k": r["k"], "slot": f"{r['task']}|{r['w']}|{r['k']}", "arm": r["arm"],
               "site": r["site"], "alpha": r["alpha"], "lambda": None, "prio": r["prio"],
               "direction_seed": direction_seed(r), "uniform_seed": stable_seed(r["task"], r["w"], r["k"]),
               "temperature": 1.0, "top_k": None, "top_p": 1.0, "thinking": False,
               "prompt_sha256": ctx.rec["prompt_sha256"], "finish_reason": rs["finish_reason"],
               "n_new_tokens": rs["n_tokens"], "batch_id": batch_id, "batch_B": len(rows), "max_new": mx,
               "hook_sha256": hook_sha256(), "text": text, "token_ids": rs["token_ids"], "realised_disp": lg,
               "utc": utc_now()}
        out.append(rec)
        arr = logs[i].get("arrays") or {}
        if write and arr:
            cell = f"{r['task']}|{r['arm']}"
            d = ROWARR.setdefault(cell, {})
            d.setdefault("key", []).append(f"{r['task']}|{r['w']}|{r['arm']}|{r['k']}")
            for kk, vv in arr.items():
                d.setdefault(kk, []).append(vv)
    if write:
        append_jsonl(RAW, out)
        dt = time.time() - t0
        append_jsonl(TIMING, [{"batch_id": batch_id, "task": ctx.t, "w": ctx.w, "seconds": dt,
                               "steps": res[0]["steps"], "arms": sorted({r["arm"] for r in rows}),
                               "n_rows": len(rows), "max_alpha": max(r["alpha"] for r in rows), "utc": utc_now()}])
        logger.info(f"{batch_id}: {dt:.1f}s, {res[0]['steps']} steps, arms {sorted({r['arm'] for r in rows})}")
    if keep_shadow_states:
        out.append({"_res": res})
    return out


def flush_rowarrays() -> None:
    """Write data/row_logs/<task>__<arm>.npz (fp32 per-position arrays at the last hooked block, S-means)."""
    from cfg import ROWLOG_DIR

    for cell, d in ROWARR.items():
        t, arm = cell.split("|")
        p = ROWLOG_DIR / f"{t}__{arm}.npz"
        old: dict[str, Any] = {}
        if p.exists():
            z = np.load(p, allow_pickle=True)
            old = {k: list(z[k]) for k in z.files}
        merged = {}
        keys = (old.get("key", []) + d.get("key", []))
        merged["key"] = np.array(keys)
        for kk in set(old) | set(d):
            if kk == "key":
                continue
            vals = list(old.get(kk, [])) + list(d.get(kk, []))
            if kk in ("d_last", "h_last"):
                merged[kk] = np.array(vals, dtype=object)
            else:
                merged[kk] = np.stack(vals).astype(np.float32) if vals else np.zeros((0,), np.float32)
        np.savez(p, **merged)
    ROWARR.clear()


def hooks_identity() -> dict[str, str]:
    return {"src/sites.py": sha256_file(ROOT / "src" / "sites.py"), "src/hooks.py": sha256_file(ROOT / "src" / "hooks.py"),
            "combined": hook_sha256()}
