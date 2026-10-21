#!/usr/bin/env python3
"""Stage 2.3 size report of D = h_base - h_instruct, and Stage 7 plan-site geometry (CPU).

d_norms   per block and position class (S, R): ||D|| / ||h_instr|| (relative, all 36 blocks); ban-free units
          ||D|| / (||h_instr|| r_Q(l)) for blocks 12-23 (r_Q: exp23 qwen_ratio.json; other blocks relative only);
          breakage flag per lambda = share of hooked (l, p) with lambda ||D|| > 4 ban-free units; generic vs
          task-specific structure: share of ||D||^2 along unit(Dbar_gen[l]), the cross-task cosine matrix of
          Dbar_t[l], cross-position coherence and the split-half (templates W1-W2 vs W4-W5) reliability.
geometry  per task panel (BASE-DIVERSE + T1 + T2) and site (S-mean at blocks 18, 23, 27; R at 18, 23): forced
          'Implement X' centroids per algorithm and model (30 paraphrases each), the twin states (5 per model), the
          T(lambda*) and READ(1) states (5 each) and the ISO(1) states (Stage 5); metric MDS (stress-1) and Isomap
          (k = 5, 10, 15) fitted jointly, plus a forced-only Isomap fit with the other points projected; centroid
          distances (is the transplanted state nearer the base twin or the instruct twin?). Within-band panels
          (18, 23) put transplant points on the instruct-base segment by construction; block 27 and R are the
          informative panels.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg import (CACHE_DIR, E23, N_LAYERS, PRED_DIR, RESULTS_DIR, STATES_DIR, TASKS15, TEMPLATE_IDS,  # noqa: E402
                 read_json, setup_logging, write_json)
from prompts5 import load_prompts  # noqa: E402

GEO_DIR = CACHE_DIR / "geometry"


def load_u16(p: Path) -> np.ndarray:
    import torch

    a = np.load(p)
    return torch.from_numpy(a.view(np.int16)).view(torch.bfloat16).float().numpy()


def r_q() -> dict[int, float]:
    q = read_json(E23 / "qwen_ratio.json")["r_Q"]
    return {int(k): float(v["median"]) for k, v in q.items()}


def d_norms() -> dict[str, Any]:
    pr = {(r["task"], r["w"]): r for r in load_prompts(("twin",))}
    rq = r_q()
    out: dict[str, Any] = {"per_task": {}, "blocks": list(range(N_LAYERS))}
    dbar = np.load(CACHE_DIR / "dbar.npy")                    # [15, 36, D]
    gen = dbar.mean(0)
    ugen = gen / np.linalg.norm(gen, axis=-1, keepdims=True)
    agg_rel_S = np.zeros(N_LAYERS)
    agg_rel_R = np.zeros(N_LAYERS)
    n_agg = 0
    for t in TASKS15:
        relS, relR, bfree, gshare, coh = [], [], [], [], []
        brk = {0.25: [], 0.5: [], 1.0: []}
        halves = {"a": np.zeros((N_LAYERS, 4096)), "b": np.zeros((N_LAYERS, 4096))}
        for w in TEMPLATE_IDS:
            nS = pr[(t, w)]["spec_end"] - pr[(t, w)]["p1"]
            hb = load_u16(STATES_DIR / f"base_{t}_{w}.npy")
            hi = load_u16(STATES_DIR / f"instr_{t}_{w}.npy")
            D = hb - hi
            nD = np.linalg.norm(D, axis=-1)                    # [36, nS+1]
            nh = np.linalg.norm(hi, axis=-1).clip(1e-6)
            relS.append((nD[:, :nS] / nh[:, :nS]).mean(1))
            relR.append(nD[:, nS] / nh[:, nS])
            bf = np.array([(nD[l, :nS] / (nh[l, :nS] * rq[l])).mean() if l in rq else np.nan
                           for l in range(N_LAYERS)])
            bfree.append(bf)
            for lam in brk:
                v = [float((lam * nD[l, :nS] / (nh[l, :nS] * rq[l]) > 4).mean()) for l in range(12, 24)]
                brk[lam].append(np.mean(v))
            proj = np.einsum("lpd,ld->lp", D[:, :nS], ugen)
            gshare.append((proj ** 2).sum(1) / (nD[:, :nS] ** 2).sum(1).clip(1e-9))
            idx = np.linspace(0, nS - 1, min(nS, 24)).astype(int)
            U = D[:, idx] / nD[:, idx, None].clip(1e-6)
            C = np.einsum("lpd,lqd->lpq", U, U)
            m = ~np.eye(len(idx), dtype=bool)
            coh.append(np.array([C[l][m].mean() for l in range(N_LAYERS)]))
            if w in ("W1", "W2"):
                halves["a"] += D[:, :nS].mean(1)
            elif w in ("W4", "W5"):
                halves["b"] += D[:, :nS].mean(1)
            del hb, hi, D, U, C
        a, b = halves["a"], halves["b"]
        split = (a * b).sum(-1) / (np.linalg.norm(a, axis=-1) * np.linalg.norm(b, axis=-1)).clip(1e-9)
        rs, rr = np.mean(relS, 0), np.mean(relR, 0)
        agg_rel_S += rs
        agg_rel_R += rr
        n_agg += 1
        out["per_task"][t] = {"rel_norm_S": rs.round(4).tolist(), "rel_norm_R": rr.round(4).tolist(),
                              "banfree_S_blocks12_23": np.mean(bfree, 0)[12:24].round(3).tolist(),
                              "breakage_share_gt4_banfree": {str(k): float(np.mean(v)) for k, v in brk.items()},
                              "generic_share_of_D2": np.mean(gshare, 0).round(4).tolist(),
                              "cross_position_coherence": np.mean(coh, 0).round(4).tolist(),
                              "split_half_cos_W12_vs_W45": split.round(4).tolist()}
        logger.info(f"d_norms {t}: rel S b18 {rs[18]:.3f}, banfree b18 {np.mean(bfree, 0)[18]:.2f}")
    out["mean_rel_norm_S"] = (agg_rel_S / n_agg).round(4).tolist()
    out["mean_rel_norm_R"] = (agg_rel_R / n_agg).round(4).tolist()
    cos = {}
    for l in (12, 18, 23, 27):
        U = dbar[:, l] / np.linalg.norm(dbar[:, l], axis=-1, keepdims=True)
        M = U @ U.T
        off = M[~np.eye(len(TASKS15), dtype=bool)]
        cos[str(l)] = {"matrix": M.round(3).tolist(), "mean_offdiag": float(off.mean()), "min_offdiag": float(off.min())}
    out["cross_task_cosine_Dbar"] = cos
    out["tasks"] = list(TASKS15)
    return out


def _load_geo(name: str) -> tuple[list[dict[str, Any]], dict[str, np.ndarray]]:
    p = GEO_DIR / f"{name}.npz"
    if not p.exists():
        return [], {}
    z = np.load(p, allow_pickle=False)
    meta = json.loads(str(z["meta"]))
    return meta, {k: z[k].astype(np.float32) for k in z.files if k != "meta"}


def geometry() -> dict[str, Any]:
    from sklearn.manifold import MDS, Isomap

    c1 = read_json(PRED_DIR / "commit1.json")
    c2p = PRED_DIR / "commit2.json"
    c2 = read_json(c2p) if c2p.exists() else {"selection": {}}
    pr = {(r["task"], r["w"]): r for r in load_prompts(("twin",))}
    fm = {tag: _load_geo(f"forced_{tag}") for tag in ("instr", "base")}
    hm, ha = _load_geo("hooked_instr")
    panels = sorted(set(c1["strata"]["BASE-DIVERSE"]) | {"T1", "T2"}, key=TASKS15.index)
    out: dict[str, Any] = {"panels": {}, "note": "within-band panels (S18, S23) put T(lambda) points on the "
                                                 "instruct-base segment by construction; S27 and R are informative"}
    for t in panels:
        lam = c2["selection"].get(t, {}).get("lambda_star") or 1.0
        res_t: dict[str, Any] = {"lambda_star": lam}
        for site in ("S18", "S23", "S27", "R18", "R23"):
            pts, lab = [], []
            for tag in ("instr", "base"):
                meta, arr = fm[tag]
                if not meta:
                    continue
                X = arr[site]
                for alg in sorted({m["X"] for m in meta if m["task"] == t}):
                    ii = [i for i, m in enumerate(meta) if m["task"] == t and m["X"] == alg]
                    pts.append(X[ii].mean(0))
                    lab.append(f"forced:{tag}:{alg}")
            l = int(site[1:])
            for tag in ("instr", "base"):
                for w in TEMPLATE_IDS:
                    H = load_u16(STATES_DIR / f"{tag}_{t}_{w}.npy")
                    nS = pr[(t, w)]["spec_end"] - pr[(t, w)]["p1"]
                    pts.append(H[l, :nS].mean(0) if site[0] == "S" else H[l, nS])
                    lab.append(f"twin:{tag}")
                    del H
            for arm in (f"T{lam}", "READ1.0", "ISO1.0"):
                ii = [i for i, m in enumerate(hm) if m["task"] == t and m["arm"] == arm]
                for i in ii:
                    pts.append(ha[site][i])
                    lab.append(f"hooked:{arm}")
            P = np.stack(pts).astype(np.float64)
            Dm = np.linalg.norm(P[:, None] - P[None], axis=-1)
            mds = MDS(n_components=2, dissimilarity="precomputed", random_state=0, normalized_stress="auto",
                      n_init=2, max_iter=300)
            Y = mds.fit_transform(Dm)
            d2 = np.linalg.norm(Y[:, None] - Y[None], axis=-1)
            iu = np.triu_indices(len(P), 1)
            stress1 = float(np.sqrt(((Dm[iu] - d2[iu]) ** 2).sum() / (Dm[iu] ** 2).sum()))
            iso = {}
            for k in (5, 10, 15):
                kk = min(k, len(P) - 1)
                try:
                    Z = Isomap(n_neighbors=kk, n_components=2).fit_transform(P)
                    iso[str(k)] = Z.round(4).tolist()
                except ValueError as e:
                    iso[str(k)] = str(e)
            forced_idx = [i for i, s in enumerate(lab) if s.startswith("forced")]
            proj = None
            try:
                im = Isomap(n_neighbors=min(5, len(forced_idx) - 1), n_components=2).fit(P[forced_idx])
                proj = im.transform(P).round(4).tolist()
            except ValueError:
                proj = None
            cent = {}
            for key in sorted(set(lab)):
                cent[key] = P[[i for i, s in enumerate(lab) if s == key]].mean(0)
            dist = {}
            if f"hooked:T{lam}" in cent:
                for key in cent:
                    dist[key] = float(np.linalg.norm(cent[f"hooked:T{lam}"] - cent[key]))
            gap = float(np.linalg.norm(cent["twin:base"] - cent["twin:instr"])) if "twin:base" in cent else None
            res_t[site] = {"labels": lab, "mds_xy": Y.round(4).tolist(), "mds_stress1": stress1, "isomap_xy": iso,
                           "isomap_forced_fit_projection": proj, "dist_from_T_centroid": dist,
                           "instr_base_twin_gap": gap,
                           "T_frac_of_gap_from_instr": (dist.get("twin:instr") / gap if gap and dist else None)}
        out["panels"][t] = res_t
        logger.info(f"geometry {t}: done")
    return out


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("geometry5")
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("dnorms", "all"):
        write_json(RESULTS_DIR / "d_norms.json", d_norms())
    if which in ("geometry", "all"):
        write_json(RESULTS_DIR / "geometry.json", geometry())


if __name__ == "__main__":
    main()
