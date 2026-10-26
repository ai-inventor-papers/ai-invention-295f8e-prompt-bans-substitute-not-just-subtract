#!/usr/bin/env python3
"""Directions, layer selection, diagnostics and the forward-pass-only commitment test (CPU, from cache/).

d[t,l] = mean(LIST) - mean(IMPLEMENT) over 50 + 50 held-out frame paraphrases; L* by 5-fold CV held-out
AUC averaged over tasks (ties within 0.005 broken by held-out d'). Writes directions/*.npy,
directions/directions_meta.json, results/layer_selection.json, results/direction_diagnostics.json and
results/commitment_test.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import CACHE_DIR, CATALOGUE, DIRECTIONS_DIR, LAYERS, RESULTS_DIR, TASKS, setup_logger, set_ram_limit, stable_hash  # noqa: E402
from loguru import logger  # noqa: E402


def gname(group: str) -> str:
    return group.replace(":", "-").replace("+", "_")


def load(task: str, group: str) -> np.ndarray:
    return np.load(CACHE_DIR / f"hR_{task}_{gname(group)}.npy").astype(np.float32)


def unit(v: np.ndarray) -> np.ndarray:
    return v / (np.linalg.norm(v) + 1e-12)


def cos(a: np.ndarray, b: np.ndarray) -> float:
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12))


def cv_layer(L: np.ndarray, I: np.ndarray, seed: int = 0) -> tuple[float, float]:
    """5-fold CV over paraphrase indices: held-out AUC and d' of the projection on the train diff-of-means."""
    n = L.shape[0]
    rng = np.random.default_rng(seed)
    idx = rng.permutation(n)
    folds = np.array_split(idx, 5)
    aucs, dps = [], []
    for k in range(5):
        te = folds[k]
        tr = np.setdiff1d(idx, te)
        d = unit(L[tr].mean(0) - I[tr].mean(0))
        pl, pi = L[te] @ d, I[te] @ d
        y = np.r_[np.ones(len(pl)), np.zeros(len(pi))]
        aucs.append(roc_auc_score(y, np.r_[pl, pi]))
        sd = np.sqrt(0.5 * (pl.var(ddof=1) + pi.var(ddof=1))) + 1e-12
        dps.append((pl.mean() - pi.mean()) / sd)
    return float(np.mean(aucs)), float(np.mean(dps))


def split_half(L: np.ndarray, I: np.ndarray, n_rep: int = 200, seed: int = 1) -> float:
    rng = np.random.default_rng(seed)
    cs = []
    n = L.shape[0]
    for _ in range(n_rep):
        p = rng.permutation(n)
        q = rng.permutation(n)
        a, b = p[: n // 2], p[n // 2:]
        c, d = q[: n // 2], q[n // 2:]
        cs.append(cos(L[a].mean(0) - I[c].mean(0), L[b].mean(0) - I[d].mean(0)))
    return float(np.mean(cs))


def pair_consistency(L: np.ndarray, I: np.ndarray) -> float:
    D = L - I
    Dn = D / (np.linalg.norm(D, axis=1, keepdims=True) + 1e-12)
    G = Dn @ Dn.T
    iu = np.triu_indices(len(D), 1)
    return float(G[iu].mean())


def shift_null(H: np.ndarray, dhat: np.ndarray, dnorm: float, n_rep: int = 2000, seed: int = 3) -> dict:
    """Null of mean(B) - mean(A) over random 10/10 splits of 20 paraphrases."""
    rng = np.random.default_rng(seed)
    dk, cs = [], []
    n = H.shape[0]
    for _ in range(n_rep):
        p = rng.permutation(n)
        s = H[p[n // 2:]].mean(0) - H[p[: n // 2]].mean(0)
        pr = float(s @ dhat)
        dk.append(pr / dnorm)
        cs.append(pr / (np.linalg.norm(s) + 1e-12))
    dk, cs = np.array(dk), np.array(cs)
    return {"dk": dk, "cos": cs, "band": [float(np.percentile(dk, 2.5)), float(np.percentile(dk, 97.5))]}


def commitment(task: str, li: int, X: str, dvec: np.ndarray, pcs: np.ndarray, base_null: dict,
               mention_cache: dict, rng_seed: int) -> dict:
    dnorm = float(np.linalg.norm(dvec))
    dhat = dvec / dnorm
    ban = load(task, f"ban:{X}")[:, li]
    men = mention_cache[X][:, li]
    s = ban[:10] - men[:10]
    sbar = s.mean(0)
    proj = float(sbar @ dhat)
    c = proj / (np.linalg.norm(sbar) + 1e-12)
    dk = proj / dnorm
    nul = shift_null(men, dhat, dnorm, seed=rng_seed)
    p = (1 + np.sum(np.abs(nul["dk"]) >= abs(dk))) / (1 + len(nul["dk"]))
    rng = np.random.default_rng(rng_seed + 7)
    U = rng.standard_normal((1000, dvec.shape[0])).astype(np.float32)
    U /= np.linalg.norm(U, axis=1, keepdims=True)
    share_iso = ((U @ sbar) / (np.linalg.norm(sbar) + 1e-12)) ** 2
    W = rng.standard_normal((1000, pcs.shape[0])).astype(np.float32) @ pcs
    W /= np.linalg.norm(W, axis=1, keepdims=True)
    share_pc = ((W @ sbar) / (np.linalg.norm(sbar) + 1e-12)) ** 2
    lo, hi = nul["band"]
    enum_dk, enum_band = base_null["enum_dk"], base_null["band"]
    pos_ok = not (enum_band[0] <= enum_dk <= enum_band[1])
    if not pos_ok:
        verdict = "uninformative"
    elif lo <= dk <= hi:
        verdict = "intact"
    elif dk > hi:
        verdict = "de-commits"
    else:
        verdict = "commits"
    return {"X": X, "proj": proj, "cos": c, "share": c ** 2, "delta_kappa": dk, "null_band_95": [lo, hi],
            "perm_p_two_sided": float(p), "null_cos_band_95": [float(np.percentile(nul["cos"], 2.5)),
                                                                float(np.percentile(nul["cos"], 97.5))],
            "share_pct_vs_isotropic": float((share_iso < c ** 2).mean()),
            "share_pct_vs_top50pc": float((share_pc < c ** 2).mean()),
            "share_iso_q95": float(np.percentile(share_iso, 95)), "share_pc_q95": float(np.percentile(share_pc, 95)),
            "kappa_ban": None, "kappa_mention": None, "positive_control_ok": pos_ok, "verdict": verdict,
            "norm_sbar": float(np.linalg.norm(sbar))}


def main() -> None:
    setup_logger("directions")
    set_ram_limit(30)
    DIRECTIONS_DIR.mkdir(parents=True, exist_ok=True)
    G = {t: {g: load(t, g) for g in ("LIST", "IMPLEMENT", "ONE", "LONGNAMES", "SHORTNAMES", "baseline", "enumerate",
                                       "listall")} for t in TASKS}
    if "--commitment-only" in sys.argv:
        commitment_test(G, json.loads((RESULTS_DIR / "layer_selection.json").read_text())["L_star"])
        return
    sel = {"layers": LAYERS, "per_layer": {}}
    for li, l in enumerate(LAYERS):
        row = {}
        for t in TASKS:
            auc, dp = cv_layer(G[t]["LIST"][:, li], G[t]["IMPLEMENT"][:, li], seed=stable_hash("cv", t) % 1000)
            row[t] = {"auc": auc, "dprime": dp}
        row["score"] = float(np.mean([row[t]["auc"] for t in TASKS]))
        row["dprime_mean"] = float(np.mean([row[t]["dprime"] for t in TASKS]))
        sel["per_layer"][str(l)] = row
    best = max(r["score"] for r in sel["per_layer"].values())
    tied = [int(l) for l, r in sel["per_layer"].items() if r["score"] >= best - 0.005]
    lstar = max(tied, key=lambda l: sel["per_layer"][str(l)]["dprime_mean"])
    sel.update({"L_star": lstar, "best_auc": best, "tied_layers": tied,
                "rule": "argmax mean held-out AUC over tasks; ties within 0.005 broken by mean held-out d'"})
    (RESULTS_DIR / "layer_selection.json").write_text(json.dumps(sel, indent=1))
    logger.info(f"L* = {lstar} (best AUC {best:.4f}; tied {tied})")
    diag = {"per_layer": {}}
    meta = {"rand": {}, "files": []}
    for li, l in enumerate(LAYERS):
        dl = {}
        ds = {}
        for t in TASKS:
            Lh, Ih = G[t]["LIST"][:, li], G[t]["IMPLEMENT"][:, li]
            d = Lh.mean(0) - Ih.mean(0)
            ds[t] = d
            dbr = Lh.mean(0) - G[t]["ONE"][:, li].mean(0)
            dpl = G[t]["LONGNAMES"][:, li].mean(0) - G[t]["SHORTNAMES"][:, li].mean(0)
            enum_shift = G[t]["enumerate"][:, li].mean(0) - G[t]["baseline"][:10, li].mean(0)
            hn = np.linalg.norm(np.concatenate([Lh, Ih]), axis=1).mean()
            np.save(DIRECTIONS_DIR / f"d_dc_{t}_L{l}.npy", d.astype(np.float32))
            np.save(DIRECTIONS_DIR / f"d_breadth_{t}_L{l}.npy", dbr.astype(np.float32))
            np.save(DIRECTIONS_DIR / f"d_placebo_{t}_L{l}.npy", dpl.astype(np.float32))
            for k in (1, 2):
                r = np.random.default_rng(stable_hash("rand", k, t, l)).standard_normal(d.shape[0]).astype(np.float32)
                r /= np.linalg.norm(r)
                np.save(DIRECTIONS_DIR / f"rand{k}_{t}_L{l}.npy", r)
                meta["rand"][f"rand{k}_{t}_L{l}"] = {"cos_with_d_hat": cos(r, d), "seed": stable_hash("rand", k, t, l)}
            dl[t] = {"norm_d": float(np.linalg.norm(d)), "norm_ratio": float(np.linalg.norm(d) / hn),
                     "mean_norm_hR": float(hn), "split_half_cos": split_half(Lh, Ih),
                     "pair_consistency": pair_consistency(Lh, Ih), "cos_breadth": cos(d, dbr),
                     "cos_placebo": cos(d, dpl), "cos_enumerate_shift": cos(d, enum_shift),
                     "norm_placebo": float(np.linalg.norm(dpl)), "norm_breadth": float(np.linalg.norm(dbr))}
        dl["cross_task_cos"] = cos(ds["T1"], ds["T2"])
        diag["per_layer"][str(l)] = dl
    diag["L_star"] = lstar
    (RESULTS_DIR / "direction_diagnostics.json").write_text(json.dumps(diag, indent=1))
    meta["note"] = ("d_dc/d_breadth/d_placebo are raw difference-of-means vectors (unnormalised); rand are seeded "
                    "isotropic unit vectors; the steering hook normalises every vector and scales by coef*||h||.")
    (DIRECTIONS_DIR / "directions_meta.json").write_text(json.dumps(meta, indent=1))
    commitment_test(G, lstar)


def commitment_test(G: dict, lstar: int) -> None:
    ct = {"layer_star": lstar, "per_task": {}}
    for t in TASKS:
        allstates = [G[t][g] for g in G[t]]
        men_cache = {X: load(t, f"mention:{X}") for X in CATALOGUE[t]}
        prof = {}
        for li, l in enumerate(LAYERS):
            d = G[t]["LIST"][:, li].mean(0) - G[t]["IMPLEMENT"][:, li].mean(0)
            dnorm = float(np.linalg.norm(d))
            dhat = d / dnorm
            imp_mean = G[t]["IMPLEMENT"][:, li].mean(0)

            def kappa(H):
                return float(((H.mean(0) - imp_mean) @ dhat) / dnorm)

            kap = {g: kappa(G[t][g][:, li]) for g in ("baseline", "enumerate", "listall", "LIST", "IMPLEMENT", "ONE")}
            for X in CATALOGUE[t]:
                kap[f"ban:{X}"] = kappa(load(t, f"ban:{X}")[:, li])
                kap[f"mention:{X}"] = kappa(men_cache[X][:10, li])
            base = G[t]["baseline"][:, li]
            en = G[t]["enumerate"][:, li]
            enum_dk = float(((en - base[:10]).mean(0) @ dhat) / dnorm)
            bn = shift_null(base, dhat, dnorm, seed=stable_hash("basenull", t, l) % 10000)
            base_null = {"enum_dk": enum_dk, "band": bn["band"]}
            res = {"kappa": kap, "positive_control": {"enum_delta_kappa": enum_dk, "null_band_95": bn["band"],
                                                       "ok": not (bn["band"][0] <= enum_dk <= bn["band"][1])}}
            if l == lstar or l % 4 == 0:
                S = np.concatenate([a[:, li] for a in allstates] + [men_cache[X][:, li] for X in CATALOGUE[t]])
                S = S - S.mean(0)
                _, _, Vt = np.linalg.svd(S, full_matrices=False)
                pcs = Vt[:50]
                res["ban"] = {X: commitment(t, li, X, d, pcs, base_null, men_cache, stable_hash("ct", t, l, X) % 10000)
                              for X in CATALOGUE[t]}
                for X in CATALOGUE[t]:
                    res["ban"][X]["kappa_ban"] = kap[f"ban:{X}"]
                    res["ban"][X]["kappa_mention"] = kap[f"mention:{X}"]
            prof[str(l)] = res
        ct["per_task"][t] = prof
        logger.info(f"{t} commitment at L*: " + json.dumps({X: (round(v['delta_kappa'], 4), v['verdict'])
                                                           for X, v in prof[str(lstar)]['ban'].items()}))
    (RESULTS_DIR / "commitment_test.json").write_text(json.dumps(ct, indent=1, default=float))
    logger.info("directions + commitment test written")


if __name__ == "__main__":
    main()
