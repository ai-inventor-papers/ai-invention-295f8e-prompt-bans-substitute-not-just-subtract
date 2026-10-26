#!/usr/bin/env python3
"""S2: the X-free prohibition direction.

For each of 14 tasks x W1-W5 x {ban, twin}: one prompt-only forward pass; block outputs (blocks 8-28) at the task-spec
positions S and at R. d[t][w][l][p] = h_ban - h_twin (p in S, relative index), n[t][l][p] = mean_w ||d||,
dbar[t][l] = mean_{w,p} d. For each sampled task t: v[t][l] = mean over the 13 other tasks t' and w of
mean_p d[t'][w][l][p] (blocks 12-23); vhat = v / ||v||. Diagnostics -> results/direction.json; directions/*.npy.
"""

from __future__ import annotations

import gc
import time
from typing import Any

import numpy as np
import torch
from loguru import logger

from cfg import (ALL_TASKS, DIR_DIR, D_MODEL, E8, RAND_SEEDS, RESULTS_DIR, SAMPLED_TASKS, SAVE_BLOCKS, TEMPLATE_IDS,
                 V_BLOCKS, read_json, sha256_file, write_json)
from engine import forward_capture
from prompts import load_prompts

SAE_BLOCKS = [15, 20, 27]  # exp12 hook = model.model.layers[L] output = block L (same convention as here)
N_SAE_POS = 32             # evenly spaced S positions kept per prompt for the 0g displacement-preservation test


def _pair_states(model: Any, ban: dict[str, Any], twin: dict[str, Any]) -> dict[str, Any]:
    p1, se, P = ban["p1"], ban["spec_end"], ban["P"]
    S = list(range(p1, se))
    res = forward_capture(model, [ban["ids"], twin["ids"]], SAVE_BLOCKS, S + [P - 1])
    out = {"d_S": {}, "d_R": {}, "twin_S": {}, "ban_S_mean": {}, "twin_S_mean": {}}
    for l in SAVE_BLOCKS:
        h = res["states"][l]  # [2, |S|+1, D] fp32 CPU
        out["d_S"][l] = (h[0, :-1] - h[1, :-1])  # [|S|, D]
        out["d_R"][l] = (h[0, -1] - h[1, -1])
        out["twin_S"][l] = h[1, :-1]
        out["ban_S_mean"][l] = h[0, :-1].mean(0)
        out["twin_S_mean"][l] = h[1, :-1].mean(0)
    return out


def _unit(x: np.ndarray) -> np.ndarray:
    return x / max(float(np.linalg.norm(x)), 1e-12)


def _cos(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / max(np.linalg.norm(a) * np.linalg.norm(b), 1e-12))


@torch.no_grad()
def stage_direction(model: Any) -> dict[str, Any]:
    t0 = time.time()
    pr = load_prompts()
    L = len(SAVE_BLOCKS)
    bi = {l: i for i, l in enumerate(SAVE_BLOCKS)}
    dmean = {t: np.zeros((len(TEMPLATE_IDS), L, D_MODEL), np.float32) for t in ALL_TASKS}   # mean_p d
    dR = {t: np.zeros((len(TEMPLATE_IDS), L, D_MODEL), np.float32) for t in ALL_TASKS}      # d at R
    norms: dict[str, np.ndarray] = {}        # n[t][l][p] for V_BLOCKS
    d_keep: dict[str, np.ndarray] = {}       # sampled tasks: d at V_BLOCKS x S (fp16) for the share diagnostic
    sae_pos: dict[str, Any] = {}             # sampled tasks: ban/twin states at SAE blocks on 32 S positions
    s_means: dict[str, Any] = {}
    for t in ALL_TASKS:
        Slen = pr[(t, "W1", "ban")]["spec_end"] - pr[(t, "W1", "ban")]["p1"]
        nn = np.zeros((len(TEMPLATE_IDS), len(V_BLOCKS), Slen), np.float32)
        keep = np.zeros((len(TEMPLATE_IDS), len(V_BLOCKS), Slen, D_MODEL), np.float16) if t in SAMPLED_TASKS else None
        for wi, w in enumerate(TEMPLATE_IDS):
            st = _pair_states(model, pr[(t, w, "ban")], pr[(t, w, "twin")])
            assert st["d_S"][SAVE_BLOCKS[0]].shape[0] == Slen
            for l in SAVE_BLOCKS:
                dmean[t][wi, bi[l]] = st["d_S"][l].mean(0).numpy()
                dR[t][wi, bi[l]] = st["d_R"][l].numpy()
            for j, l in enumerate(V_BLOCKS):
                nn[wi, j] = st["d_S"][l].norm(dim=-1).numpy()
                if keep is not None:
                    keep[wi, j] = st["d_S"][l].numpy().astype(np.float16)
            if t in SAMPLED_TASKS:
                idx = np.linspace(0, Slen - 1, N_SAE_POS).round().astype(int)
                sae_pos.setdefault(t, {})[w] = {
                    l: {"ban": (st["twin_S"][l][idx] + st["d_S"][l][idx]).numpy().astype(np.float16),
                        "twin": st["twin_S"][l][idx].numpy().astype(np.float16)} for l in SAE_BLOCKS}
            s_means.setdefault(t, {})[w] = {"ban": np.stack([st["ban_S_mean"][l].numpy() for l in SAVE_BLOCKS]),
                                            "twin": np.stack([st["twin_S_mean"][l].numpy() for l in SAVE_BLOCKS])}
            del st
        norms[t] = nn.mean(0)  # [12, |S|]
        if keep is not None:
            d_keep[t] = keep
        logger.info(f"S2 {t}: |S|={Slen} mean ||d|| at block 18 = {float(nn[:, V_BLOCKS.index(18)].mean()):.2f} "
                    f"({time.time() - t0:.0f}s)")
        gc.collect()
    vb = [bi[l] for l in V_BLOCKS]
    task_mean = {t: dmean[t].mean(0) for t in ALL_TASKS}  # dbar[t] [L, D] = mean_{w,p} d
    v: dict[str, np.ndarray] = {}
    vhat: dict[str, np.ndarray] = {}
    for t in SAMPLED_TASKS:
        others = [u for u in ALL_TASKS if u != t]
        v[t] = np.mean([dmean[u][:, vb].mean(0) for u in others], axis=0)  # [12, D]
        vhat[t] = np.stack([_unit(x) for x in v[t]])
    v_all = np.mean([dmean[u][:, vb].mean(0) for u in ALL_TASKS], axis=0)
    vhat_all = np.stack([_unit(x) for x in v_all])
    # random directions: one isotropic unit vector per seed, shared across blocks 12-23
    rand = {s: _unit(np.random.Generator(np.random.PCG64(s)).standard_normal(D_MODEL)).astype(np.float32)
            for s in RAND_SEEDS}
    # ---- diagnostics
    rng = np.random.default_rng(0)
    R = rng.standard_normal((1000, D_MODEL))
    R /= np.linalg.norm(R, axis=1, keepdims=True)
    diag: dict[str, Any] = {"blocks": V_BLOCKS, "convention": "block l output = hidden_states[l+1]"}
    cosv = {}
    for t in SAMPLED_TASKS:
        rows = {}
        for j, l in enumerate(V_BLOCKS):
            db = task_mean[t][bi[l]]
            rc = np.abs(R @ _unit(db))
            rows[l] = {"cos_vhat_dbar": _cos(vhat[t][j], db), "rand_abs_cos_mean": float(rc.mean()),
                       "rand_abs_cos_q95": float(np.quantile(rc, 0.95)), "norm_v": float(np.linalg.norm(v[t][j])),
                       "norm_dbar": float(np.linalg.norm(db))}
        cosv[t] = rows
    diag["cos_vhat_heldout_dbar"] = cosv
    # 14 x 14 cosine matrix of dbar at every V block
    diag["dbar_cos_matrix"] = {l: [[_cos(task_mean[a][bi[l]], task_mean[b][bi[l]]) for b in ALL_TASKS]
                                   for a in ALL_TASKS] for l in V_BLOCKS}
    diag["tasks"] = list(ALL_TASKS)
    # split-half reliability (W1-W2 vs W3-W5), all tasks and leave-one-out per sampled task
    ia, ib = [0, 1], [2, 3, 4]
    def half(ts, idx):
        return np.mean([dmean[u][idx][:, vb].mean(0) for u in ts], axis=0)
    diag["split_half_all"] = {l: _cos(half(ALL_TASKS, ia)[j], half(ALL_TASKS, ib)[j]) for j, l in enumerate(V_BLOCKS)}
    diag["split_half_loo"] = {t: {l: _cos(half([u for u in ALL_TASKS if u != t], ia)[j],
                                          half([u for u in ALL_TASKS if u != t], ib)[j])
                                  for j, l in enumerate(V_BLOCKS)} for t in SAMPLED_TASKS}
    diag["cross_layer_coherence"] = {t: {f"{V_BLOCKS[j]}-{V_BLOCKS[j + 1]}": float(vhat[t][j] @ vhat[t][j + 1])
                                         for j in range(len(V_BLOCKS) - 1)} for t in SAMPLED_TASKS}
    diag["cross_layer_coherence_all"] = {f"{V_BLOCKS[j]}-{V_BLOCKS[j + 1]}": float(vhat_all[j] @ vhat_all[j + 1])
                                         for j in range(len(V_BLOCKS) - 1)}
    # share of the task's own displacement along vhat: mean_{w,p} (d . vhat)^2 / ||d||^2
    share = {}
    for t in SAMPLED_TASKS:
        dk = d_keep[t].astype(np.float32)  # [5, 12, |S|, D]
        sh = {}
        for j, l in enumerate(V_BLOCKS):
            x = dk[:, j]
            pr2 = (x @ vhat[t][j]) ** 2
            nr2 = (x ** 2).sum(-1)
            sh[l] = float(np.mean(pr2 / np.maximum(nr2, 1e-12)))
        rnd = [float(np.mean((dk[:, 6] @ r) ** 2 / np.maximum((dk[:, 6] ** 2).sum(-1), 1e-12))) for r in R[:20]]
        share[t] = {"by_block": sh, "random_unit_share_block18_mean": float(np.mean(rnd))}
        del dk
    diag["own_displacement_share_along_vhat"] = share
    # C5: exp8 c5.json stores no vector -> C5-proxy = mean over T1/T2 and w of the ban-minus-twin displacement at R
    c5 = read_json(E8 / "results" / "c5.json")
    has_vec = isinstance(c5.get("shared_ban_direction"), dict) and any(
        isinstance(v_, list) and len(v_) == D_MODEL for v_ in c5["shared_ban_direction"].values())
    proxy = np.mean([dR[t].mean(0) for t in ("T1", "T2")], axis=0)  # [L, D] at R, block convention
    diag["c5"] = {"c5_json_has_vector": bool(has_vec), "flag": "C5-proxy",
                  "index_mapping": "exp8 c5 'layer l' = hidden_states[l] = block l-1 output here",
                  "cos_vhat_all_vs_proxy_R": {l: _cos(vhat_all[j], proxy[bi[l]]) for j, l in enumerate(V_BLOCKS)},
                  "cos_vhat_T1_vs_proxy_R": {l: _cos(vhat["T1"][j], proxy[bi[l]]) for j, l in enumerate(V_BLOCKS)},
                  "cos_vhat_T2_vs_proxy_R": {l: _cos(vhat["T2"][j], proxy[bi[l]]) for j, l in enumerate(V_BLOCKS)}}
    diag["rand_cos_with_vhat"] = {s: {t: {l: float(rand[s] @ vhat[t][j]) for j, l in enumerate(V_BLOCKS)}
                                      for t in SAMPLED_TASKS} for s in RAND_SEEDS}
    diag["rand_cross_layer_coherence"] = 1.0
    diag["expected_abs_cos_random"] = float(np.sqrt(2 / (np.pi * D_MODEL)))
    # ---- save
    hashes = {}
    for t in SAMPLED_TASKS:
        for name, arr in ((f"v_{t}.npy", vhat[t].astype(np.float32)), (f"vraw_{t}.npy", v[t].astype(np.float32)),
                          (f"norms_{t}.npy", norms[t].astype(np.float32))):
            np.save(DIR_DIR / name, arr)
            hashes[name] = sha256_file(DIR_DIR / name)
    for s in RAND_SEEDS:
        np.save(DIR_DIR / f"rand_{s}.npy", rand[s])
        hashes[f"rand_{s}.npy"] = sha256_file(DIR_DIR / f"rand_{s}.npy")
    np.save(DIR_DIR / "v_all.npy", vhat_all.astype(np.float32))
    hashes["v_all.npy"] = sha256_file(DIR_DIR / "v_all.npy")
    np.savez_compressed(DIR_DIR / "task_dbar.npz", **{t: task_mean[t] for t in ALL_TASKS},
                        blocks=np.array(SAVE_BLOCKS))
    np.savez_compressed(DIR_DIR / "task_dR.npz", **{t: dR[t].mean(0) for t in ALL_TASKS})
    np.savez_compressed(DIR_DIR / "s_means.npz", **{f"{t}|{w}|{k}": s_means[t][w][k] for t in s_means
                                                     for w in s_means[t] for k in ("ban", "twin")})
    np.savez_compressed(DIR_DIR / "sae_pos_states.npz", **{f"{t}|{w}|{l}|{k}": sae_pos[t][w][l][k]
                                                            for t in sae_pos for w in sae_pos[t]
                                                            for l in SAE_BLOCKS for k in ("ban", "twin")})
    diag["sha256"] = hashes
    diag["seconds"] = time.time() - t0
    write_json(RESULTS_DIR / "direction.json", diag)
    write_json(DIR_DIR / "direction_hashes.json", hashes)
    logger.info(f"S2 done in {time.time() - t0:.0f}s; cos(vhat, held-out dbar) at block 18: "
                f"{ {t: round(cosv[t][18]['cos_vhat_dbar'], 3) for t in SAMPLED_TASKS} }")
    return diag


def load_direction(task: str) -> dict[str, np.ndarray]:
    return {"vhat": np.load(DIR_DIR / f"v_{task}.npy"), "norms": np.load(DIR_DIR / f"norms_{task}.npy")}


def load_rand(seed: int) -> np.ndarray:
    return np.load(DIR_DIR / f"rand_{seed}.npy")
