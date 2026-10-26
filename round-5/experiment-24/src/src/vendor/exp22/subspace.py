#!/usr/bin/env python3
"""S3: plan subspace, axes, reliability, predictors, doses (CPU, forward-pass data only).

Per task t and block l (12-35), from the S-mean states of the forced prompts:
  c_X = mean of the 30 NAMED states of algorithm X; cm_X = mean of the 30 MASKED states.
  Q_l = orthonormal basis (SVD) of {c_X - c_def : X != def} (rank k = M - 1); Qm_l the masked analogue;
  Q_R,l from the R-position states.
  a_l = normalise(mean_{X != def} c_X - c_def); r_l = normalise(c_ru - c_def); r2_l (second runner-up);
  rm_l = normalise(cm_ru - cm_def).  D_r = ||c_ru - c_def||, D_rm = ||cm_ru - cm_def||, D_r2 = ||c_r2 - c_def||.
Runner-up = screen push-landing top-1 (results/screen.json); second = the screen's second landing, else the nearest
other NAMED centroid at block 18 (both fall back to the nearest centroid when the screen has no landing).
Predictors per direction u (all committed before any population sample):
  pi(u)        = mean_{l=12..23} ||Q_l^T u||^2                    (PRIMARY)
  pi_masked(u) = same with Qm_l;  s(u) = mean_l <u, a_l>
  pi_real      = mean_{l=12..23} ||Q_l^T d_l||^2 / ||d_l||^2 of the realised S-mean displacement d_l (avg over
                 templates; per alpha and averaged over alpha 1, 2); pi_late (blocks 24-35, their own Q_l);
                 pi_R (R-position displacement, Q_R,l, blocks 12-35); gain (per-position block-35 / target norm)
  controls     : pi_wrong (other tasks' Q, same blocks), pi_within (top-k PCs of pooled within-class residuals),
                 pi_whitened (Q of within-class-whitened centroids, shrinkage), pi_noOutlier (massive dims removed)
  kappa_t      = mean_alpha alpha * sqrt(mean_u pi(u)) * mean_l(mean_p n[l,p] / D_r,l)
Doses: M_s[l,p] = s D_l n[l,p] / mean_p n[l,p]; nu(s) = mean_l s D_l / mean_p n[l,p];
  s'_l = <(c_def + c_ru)/2 - hbar_twin, r_l> / D_l (twin-relative Voronoi midpoint along r).
"""

from __future__ import annotations

import time
from typing import Any

import numpy as np
from loguru import logger

from cfg4 import (CAP_BLOCKS, DEFAULT4, DOSES, EDIT_BLOCKS, LATE_BLOCKS, MOVABLE, OTHER9, PATH_TASKS, RESULTS_DIR,
                  SEEDS_C2C, SEEDS_OTHER, SEEDS_POP, STATES_DIR, TASKS15, TEMPLATE_IDS, read_json, write_json)
import npz_parts
from ctx4 import ban_unit, rand_dir
from prompts4 import load_prompts4

BI = {l: i for i, l in enumerate(CAP_BLOCKS)}
EI = [BI[l] for l in EDIT_BLOCKS]
LI = [BI[l] for l in LATE_BLOCKS]


def unit(x: np.ndarray) -> np.ndarray:
    return x / max(float(np.linalg.norm(x)), 1e-12)


def orth(V: np.ndarray, k: int | None = None) -> np.ndarray:
    """Orthonormal basis of the column span of V [D, m] via SVD (rank k = m by default)."""
    U, S, _ = np.linalg.svd(V, full_matrices=False)
    k = k or V.shape[1]
    return U[:, :k]


def load_task_states(task: str, prompts: dict[str, dict[str, Any]]) -> dict[str, Any]:
    z = npz_parts.load(STATES_DIR / f"states_{task}.npz")
    pids = [str(p) for p in z["pids"]]
    meta = [prompts[p] for p in pids]
    return {"smean": z["smean"].astype(np.float32), "R": z["R"].astype(np.float32), "meta": meta, "pids": pids,
            "twin_pnorm": z["twin_pnorm"]}


def class_index(meta: list[dict[str, Any]], kind: str) -> dict[str, np.ndarray]:
    out: dict[str, list[int]] = {}
    for i, m in enumerate(meta):
        if m["kind"] == kind:
            out.setdefault(m["X"], []).append(i)
    return {k: np.array(v) for k, v in out.items()}


def centroids(H: np.ndarray, idx: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    return {X: H[ii].mean(0) for X, ii in idx.items()}   # [24, D] per X


def plan_basis(C: dict[str, np.ndarray], default: str, bi: int, modes: list[str] | None = None) -> np.ndarray:
    others = [X for X in (modes or C) if X != default and X in C]
    V = np.stack([C[X][bi] - C[default][bi] for X in others], 1).astype(np.float64)
    return orth(V, len(others))


def proj_share(Q: np.ndarray, v: np.ndarray) -> float:
    v = v.astype(np.float64)
    nv = float(v @ v)
    return float(np.sum((Q.T @ v) ** 2) / max(nv, 1e-30))


def adherence(task: str) -> dict[str, dict[str, float]]:
    from cfg4 import E7, read_jsonl
    from describe import bench_dir
    out: dict[str, dict[str, float]] = {}
    if task in PATH_TASKS:
        rows = read_jsonl(E7 / "data" / "forced_selected.jsonl")
        et = {"T1": "t1", "T2": "t2"}[task]
        rows = [r for r in rows if r.get("task") == et]
        key_mode = "X" if rows and "X" in rows[0] else "forced_mode"
    else:
        rows = read_jsonl(bench_dir(task) / "forced_programs.jsonl")
        key_mode = "forced_mode"
    by: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        by.setdefault(r.get(key_mode), []).append(r)
    for m, rr in by.items():
        out[str(m)] = {"n": len(rr), "adherence": sum(r.get("label") == m for r in rr) / len(rr),
                       "adherent_correct": sum(r.get("label") == m and bool(r.get("passed")) for r in rr) / len(rr)}
    return out


def runner_ups(task: str, C: dict[str, np.ndarray], screen: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    d = DEFAULT4[task]
    st = screen["tasks"][task]
    dist18 = {X: float(np.linalg.norm(C[X][BI[18]] - C[d][BI[18]])) for X in C if X != d}
    near = sorted(dist18, key=dist18.get)
    ru = st.get("runner_up_screen") or near[0]
    src_ru = "screen push-landing top-1" if st.get("runner_up_screen") else "nearest named centroid at block 18"
    if st.get("second_screen"):
        r2, src2 = st["second_screen"], "screen second landing"
    else:
        cand = [X for X in near if X != ru]
        r2, src2 = cand[0], "nearest other named centroid at block 18"
    return ru, r2, {"runner_up": ru, "runner_up_source": src_ru, "second": r2, "second_source": src2,
                    "dist18": dist18}


def split_half(H: np.ndarray, idx: dict[str, np.ndarray], default: str, bi: int, n_split: int = 200,
               seed: int = 0) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    cos: dict[str, list[float]] = {X: [] for X in idx if X != default}
    pa: list[float] = []
    for _ in range(n_split):
        A, Bc = {}, {}
        for X, ii in idx.items():
            p = rng.permutation(ii)
            h = len(p) // 2
            A[X] = H[p[:h], bi].mean(0)
            Bc[X] = H[p[h:2 * h], bi].mean(0)
        others = [X for X in idx if X != default]
        for X in others:
            da, db = A[X] - A[default], Bc[X] - Bc[default]
            cos[X].append(float(da @ db / max(np.linalg.norm(da) * np.linalg.norm(db), 1e-12)))
        QA = orth(np.stack([A[X] - A[default] for X in others], 1).astype(np.float64))
        QB = orth(np.stack([Bc[X] - Bc[default] for X in others], 1).astype(np.float64))
        sv = np.linalg.svd(QA.T @ QB, compute_uv=False)
        pa.append(float(np.mean(sv)))
    k = len(idx) - 1
    rng2 = np.random.default_rng(seed + 1)
    rand = []
    for _ in range(50):
        QA = np.linalg.qr(rng2.standard_normal((H.shape[-1], k)))[0]
        QB = np.linalg.qr(rng2.standard_normal((H.shape[-1], k)))[0]
        rand.append(float(np.mean(np.linalg.svd(QA.T @ QB, compute_uv=False))))
    return {"cos_diff_mean": {X: float(np.mean(v)) for X, v in cos.items()},
            "cos_diff_q05": {X: float(np.quantile(v, 0.05)) for X, v in cos.items()},
            "principal_cos_mean": float(np.mean(pa)), "principal_cos_q05": float(np.quantile(pa, 0.05)),
            "random_subspace_principal_cos_mean": float(np.mean(rand))}


def snr(H: np.ndarray, idx: dict[str, np.ndarray], C: dict[str, np.ndarray], default: str, bi: int) -> dict[str, Any]:
    res = []
    for X, ii in idx.items():
        res.append(H[ii, bi] - C[X][bi])
    Rm = np.concatenate(res, 0)
    tr = float(np.sum(Rm ** 2) / max(Rm.shape[0] - len(idx), 1))   # tr(Sigma_within), pooled
    n_per = np.mean([len(ii) for ii in idx.values()])
    return {X: float(np.sum((C[X][bi] - C[default][bi]) ** 2) / (2 * tr / n_per)) for X in idx if X != default}


def within_pcs(H: np.ndarray, idx: dict[str, np.ndarray], C: dict[str, np.ndarray], bi: int, k: int) -> np.ndarray:
    Rm = np.concatenate([H[ii, bi] - C[X][bi] for X, ii in idx.items()], 0).astype(np.float64)
    _, _, Vt = np.linalg.svd(Rm, full_matrices=False)
    return Vt[:k].T


def whitener(H: np.ndarray, idx: dict[str, np.ndarray], C: dict[str, np.ndarray], bi: int,
             shrink: float = 0.5) -> tuple[np.ndarray, np.ndarray, float]:
    """Shrinkage whitening W = (Sigma_w + lam I)^(-1/2) represented in the residual PC basis: returns (V, f, g) with
    W x = V (f * (V^T x)) + g (x - V V^T x)."""
    Rm = np.concatenate([H[ii, bi] - C[X][bi] for X, ii in idx.items()], 0).astype(np.float64)
    _, S, Vt = np.linalg.svd(Rm, full_matrices=False)
    ev = S ** 2 / max(Rm.shape[0] - 1, 1)
    lam = shrink * float(ev.sum() / H.shape[-1]) + 1e-12
    V = Vt.T
    f = 1.0 / np.sqrt(ev + lam)
    g = 1.0 / np.sqrt(lam)
    return V, f, g


def apply_w(Wt: tuple[np.ndarray, np.ndarray, float], x: np.ndarray) -> np.ndarray:
    V, f, g = Wt
    c = V.T @ x
    return V @ (f[:, None] * c if x.ndim == 2 else f * c) + g * (x - V @ c)


def run_subspace() -> dict[str, Any]:
    t0 = time.time()
    prompts = load_prompts4()
    screen = read_json(RESULTS_DIR / "screen.json")
    commit: dict[str, Any] = {"tasks": {}, "directions": {}}
    Qall: dict[str, dict[int, np.ndarray]] = {}
    cache: dict[str, Any] = {}
    # pass 1: subspaces per task
    for t in TASKS15:
        st = load_task_states(t, prompts)
        H, HR, meta = st["smean"], st["R"], st["meta"]
        d = DEFAULT4[t]
        nidx, midx = class_index(meta, "named"), class_index(meta, "masked")
        assert d in nidx, f"{t}: default {d} missing from named prompts"
        modes = sorted(nidx)
        C, Cm = centroids(H, nidx), centroids(H, midx)
        CR = centroids(HR, nidx)
        ru, r2, rinfo = runner_ups(t, C, screen)
        k = len(modes) - 1
        Q = np.stack([plan_basis(C, d, BI[l]) for l in CAP_BLOCKS])          # [24, D, k]
        Qm = np.stack([plan_basis(Cm, d, BI[l]) for l in CAP_BLOCKS])
        QR = np.stack([plan_basis(CR, d, BI[l]) for l in CAP_BLOCKS])
        adh = adherence(t)
        good = [X for X in modes if X == d or adh.get(X, {}).get("adherence", 0) >= 0.5]
        Qadh = np.stack([plan_basis(C, d, BI[l], good) for l in EDIT_BLOCKS]) if len(good) > 1 else None
        a_ax = np.stack([unit(np.mean([C[X][BI[l]] for X in modes if X != d], 0) - C[d][BI[l]]) for l in CAP_BLOCKS])
        r_ax = np.stack([unit(C[ru][BI[l]] - C[d][BI[l]]) for l in CAP_BLOCKS])
        r2_ax = np.stack([unit(C[r2][BI[l]] - C[d][BI[l]]) for l in CAP_BLOCKS])
        rm_ax = np.stack([unit(Cm[ru][BI[l]] - Cm[d][BI[l]]) for l in CAP_BLOCKS])
        D_r = np.array([np.linalg.norm(C[ru][BI[l]] - C[d][BI[l]]) for l in CAP_BLOCKS])
        D_rm = np.array([np.linalg.norm(Cm[ru][BI[l]] - Cm[d][BI[l]]) for l in CAP_BLOCKS])
        D_r2 = np.array([np.linalg.norm(C[r2][BI[l]] - C[d][BI[l]]) for l in CAP_BLOCKS])
        tw_idx = [i for i, m in enumerate(meta) if m["kind"] == "twin"]
        hbar_tw = H[tw_idx].mean(0)                                          # [24, D]
        np.savez(STATES_DIR / f"subspace_{t}.npz", Q=Q.astype(np.float32), Qm=Qm.astype(np.float32),
                 QR=QR.astype(np.float32), a=a_ax.astype(np.float32), r=r_ax.astype(np.float32),
                 r2=r2_ax.astype(np.float32), rm=rm_ax.astype(np.float32), D_r=D_r, D_rm=D_rm, D_r2=D_r2,
                 blocks=np.array(CAP_BLOCKS), modes=np.array(modes), hbar_twin=hbar_tw.astype(np.float32),
                 c_named=np.stack([C[X] for X in modes]).astype(np.float32),
                 c_masked=np.stack([Cm[X] for X in modes]).astype(np.float32))
        Qall[t] = {l: Q[BI[l]] for l in CAP_BLOCKS}
        n = ban_unit(t)
        nmean = n.mean(1)                                                    # [12]
        ncent = {}
        for l in EDIT_BLOCKS:
            ncent[l] = {X: float(np.linalg.norm(C[X][BI[l]] - C[d][BI[l]]) / nmean[EDIT_BLOCKS.index(l)])
                        for X in modes if X != d}
        rel = {"block18": split_half(H, nidx, d, BI[18]),
               "block18_masked": split_half(H, midx, d, BI[18], seed=7)}
        dist_named_masked = {X: float(np.dot(unit(C[X][BI[18]] - C[d][BI[18]]), unit(Cm[X][BI[18]] - Cm[d][BI[18]])))
                             for X in modes if X != d}
        # ban's own displacement projection share per template (not R2)
        pi_ban = {}
        if t != "R2":
            for w in TEMPLATE_IDS:
                ib = [i for i, m in enumerate(meta) if m["kind"] == "ban" and m["template_id"] == w]
                it = [i for i, m in enumerate(meta) if m["kind"] == "twin" and m["template_id"] == w]
                if ib and it:
                    dv = H[ib[0]] - H[it[0]]
                    pi_ban[w] = float(np.mean([proj_share(Q[BI[l]], dv[BI[l]]) for l in EDIT_BLOCKS]))
        # within-class PCs, whitening, outlier dims (blocks 12-23)
        Wpc = {l: within_pcs(H, nidx, C, BI[l], k) for l in EDIT_BLOCKS}
        Wt = {l: whitener(H, nidx, C, BI[l]) for l in EDIT_BLOCKS}
        Qw = {}
        for l in EDIT_BLOCKS:
            V = np.stack([apply_w(Wt[l], (C[X][BI[l]] - C[d][BI[l]]).astype(np.float64)) for X in modes if X != d], 1)
            Qw[l] = orth(V)
        out_dims = {}
        Qno = {}
        for l in EDIT_BLOCKS:
            mu = np.abs(H[list(nidx[d])][:, BI[l]].mean(0))
            dims = np.where(mu > 50 * np.median(mu))[0]
            out_dims[l] = dims.tolist()
            mask = np.ones(H.shape[-1], bool)
            mask[dims] = False
            V = np.stack([(C[X][BI[l]] - C[d][BI[l]]) * mask for X in modes if X != d], 1).astype(np.float64)
            Qno[l] = (orth(V), mask)
        cache[t] = {"Q": Q, "Qm": Qm, "QR": QR, "a": a_ax, "Wpc": Wpc, "Wt": Wt, "Qw": Qw, "Qno": Qno, "Qadh": Qadh,
                    "D_r": D_r, "nmean": nmean, "C": C, "ru": ru, "r_ax": r_ax, "hbar": hbar_tw, "d": d}
        sprime = {}
        for nm, Cx, ax, Dx, X in (("r", C, r_ax, D_r, ru), ("rm", Cm, rm_ax, D_rm, ru), ("r2", C, r2_ax, D_r2, r2)):
            sprime[nm] = {l: float(((Cx[d][BI[l]] + Cx[X][BI[l]]) / 2 - hbar_tw[BI[l]]) @ ax[BI[l]] / Dx[BI[l]])
                          for l in EDIT_BLOCKS}
        nu = {nm: {str(s): float(np.mean([s * Dx[BI[l]] / nmean[j] for j, l in enumerate(EDIT_BLOCKS)]))
                   for s in DOSES} for nm, Dx in (("r", D_r), ("rm", D_rm), ("r2", D_r2))}
        commit["tasks"][t] = {
            "default": d, "modes": modes, "k": k, "runner_up": rinfo, "Q_rank": int(np.linalg.matrix_rank(Q[BI[18]])),
            "Qm_rank": int(np.linalg.matrix_rank(Qm[BI[18]])), "reliability": rel, "snr_block18": snr(H, nidx, C, d, BI[18]),
            "snr_block18_masked": snr(H, midx, Cm, d, BI[18]), "adherence": adh, "adherent_modes_ge_0.5": good,
            "centroid_dist_ban_units": {str(l): v for l, v in ncent.items()},
            "named_vs_masked_diff_cos_block18": dist_named_masked, "pi_ban_per_template": pi_ban,
            "D_r": D_r.tolist(), "D_rm": D_rm.tolist(), "D_r2": D_r2.tolist(), "nu": nu,
            "s_prime": {nm: {"per_block": v, "mean": float(np.mean(list(v.values())))} for nm, v in sprime.items()},
            "outlier_dims": {str(l): v for l, v in out_dims.items()}, "n_named": {X: int(len(v)) for X, v in nidx.items()},
            "n_masked": {X: int(len(v)) for X, v in midx.items()}}
        logger.info(f"S3 {t}: k={k} ru={ru} r2={r2} rel18 pc={rel['block18']['principal_cos_mean']:.3f} "
                    f"(rand {rel['block18']['random_subspace_principal_cos_mean']:.3f}) D_r18={D_r[BI[18]]:.1f}")
    # pass 2: predictors per direction
    for t in TASKS15:
        c = cache[t]
        seeds = SEEDS_POP if t in MOVABLE else SEEDS_OTHER
        dz = npz_parts.load(STATES_DIR / f"disp_{t}.npz")
        keys = [str(x) for x in dz["keys"]]
        delta, deltaR = dz["delta"].astype(np.float32), dz["deltaR"].astype(np.float32)
        recs = {r["key"]: r for r in read_json(STATES_DIR / f"disp_{t}_recs.json")}
        kix = {k: i for i, k in enumerate(keys)}
        pred = {}
        allu = {}
        for s in seeds + ([SEEDS_C2C[t]] if t in SEEDS_C2C else []):
            u = rand_dir(s).astype(np.float64)
            allu[s] = u
            p = {"pi": float(np.mean([proj_share(c["Q"][BI[l]], u) for l in EDIT_BLOCKS])),
                 "pi_masked": float(np.mean([proj_share(c["Qm"][BI[l]], u) for l in EDIT_BLOCKS])),
                 "s": float(np.mean([u @ c["a"][BI[l]] for l in EDIT_BLOCKS])),
                 "s_runner_up": float(np.mean([u @ c["r_ax"][BI[l]] for l in EDIT_BLOCKS])),
                 "pi_within": float(np.mean([proj_share(c["Wpc"][l], u) for l in EDIT_BLOCKS])),
                 "pi_wrong": float(np.mean([np.mean([proj_share(Qall[t2][l], u) for l in EDIT_BLOCKS])
                                            for t2 in TASKS15 if t2 != t])),
                 "pi_whitened": float(np.mean([proj_share(c["Qw"][l], apply_w(c["Wt"][l], u)) for l in EDIT_BLOCKS])),
                 "pi_noOutlier": float(np.mean([proj_share(c["Qno"][l][0], u * c["Qno"][l][1]) for l in EDIT_BLOCKS]))}
            if c["Qadh"] is not None:
                p["pi_adherent"] = float(np.mean([proj_share(c["Qadh"][j], u) for j in range(len(EDIT_BLOCKS))]))
            if s in seeds:
                for a in (1.0, 2.0):
                    pr, pl, pR, g, gs = [], [], [], [], []
                    for w in TEMPLATE_IDS:
                        key = f"POP|{s}|{a}|{w}"
                        i = kix[key]
                        dl = delta[i]
                        pr.append(np.mean([proj_share(c["Q"][BI[l]], dl[BI[l]]) for l in EDIT_BLOCKS]))
                        pl.append(np.mean([proj_share(c["Q"][BI[l]], dl[BI[l]]) for l in LATE_BLOCKS]))
                        pR.append(np.mean([proj_share(c["QR"][BI[l]], deltaR[i][BI[l]]) for l in CAP_BLOCKS]))
                        g.append(recs[key]["gain"])
                        gs.append(recs[key]["gain_smean"])
                    p[f"pi_real_a{a}"] = float(np.mean(pr))
                    p[f"pi_late_a{a}"] = float(np.mean(pl))
                    p[f"pi_R_a{a}"] = float(np.mean(pR))
                    p[f"gain_a{a}"] = float(np.mean(g))
                    p[f"gain_smean_a{a}"] = float(np.mean(gs))
                for nm in ("pi_real", "pi_late", "pi_R", "gain", "gain_smean"):
                    p[nm] = float(np.mean([p[f"{nm}_a1.0"], p[f"{nm}_a2.0"]]))
            pred[str(s)] = p
        mean_pi = float(np.mean([pred[str(s)]["pi"] for s in seeds]))
        kappa = float(np.mean([a * np.sqrt(mean_pi) for a in (1.0, 2.0)]) *
                      np.mean([c["nmean"][j] / c["D_r"][BI[l]] for j, l in enumerate(EDIT_BLOCKS)]))
        commit["tasks"][t]["kappa"] = kappa
        commit["tasks"][t]["mean_pi"] = mean_pi
        commit["tasks"][t]["expected_pi_isotropic"] = commit["tasks"][t]["k"] / 4096
        commit["directions"][t] = pred
        # screen-push displacement projections (for C2b; recorded outcomes exist for these pushes)
        scr = {}
        for key in keys:
            fam, s, a, w = key.split("|")
            if fam != "SCR":
                continue
            i = kix[key]
            scr.setdefault(f"{s}|{a}", []).append(
                (np.mean([proj_share(c["Q"][BI[l]], delta[i][BI[l]]) for l in EDIT_BLOCKS]),
                 np.mean([np.linalg.norm(delta[i][BI[l]]) / c["nmean"][j] for j, l in enumerate(EDIT_BLOCKS)]),
                 np.mean([delta[i][BI[l]] @ c["a"][BI[l]] / c["nmean"][j] for j, l in enumerate(EDIT_BLOCKS)])))
        commit["tasks"][t]["screen_push_projection"] = {k: {"pi_delta": float(np.mean([x[0] for x in v])),
                                                            "norm_ban_units": float(np.mean([x[1] for x in v])),
                                                            "s_delta": float(np.mean([x[2] for x in v]))}
                                                        for k, v in scr.items()}
        logger.info(f"S3 predictors {t}: mean pi {mean_pi:.5f} (k/4096 = {commit['tasks'][t]['k'] / 4096:.5f}); "
                    f"kappa {kappa:.4f}")
    commit["seconds"] = time.time() - t0
    write_json(RESULTS_DIR / "subspace_report.json", commit)
    return commit


if __name__ == "__main__":
    from cfg4 import setup_logging

    setup_logging("subspace")
    run_subspace()
