#!/usr/bin/env python3
"""Stage B (CPU): layer probe (B2), layer choice (B3), SAE download + hook-alignment FVU check (B4) and readout (i)
discovery (B5) on the exp3 ban-row states; the generic nested-selection machinery is reused for the fresh-pool
replication (E3).

Classes: y = 1 for the banned/modal approach (t1 BFS, t2 Dijkstra: non-compliant under the ban), y = 0 for the main
substitute (t1 DFS, t2 Bellman-Ford/SPFA). Groups = paraphrase (exp3) or template (fresh pool). Every method is
scored on IDENTICAL leave-one-group-out folds; each fold's held-out scores are z-scored by that fold's training-score
mean/sd with the sign fixed on training rows, then pooled. Metrics: pooled AUC and WITHIN-GROUP AUC (pairs sharing a
group; removes group-level 'how hard' signal). Nulls permute labels WITHIN groups.
"""

from __future__ import annotations

import gc
import json
import multiprocessing as mp
import time
from concurrent.futures import ProcessPoolExecutor
from typing import Any

import numpy as np
from loguru import logger
from scipy.stats import rankdata
from sklearn.linear_model import LogisticRegression

from core import (EXP3, EXP3_LABEL_MAP, EXP3_SRC, EXP3_TASK, FIGS, RESULTS, SAE_K, SAE_REPO, TASKS, TENSORS, Timer,
                  add_deviation, read_json, read_jsonl, write_json)

LAYERS = list(range(8, 29))
POS_NAMES = ["R", "k8", "k16", "k32", "k64", "k_fork", "k_pre", "k_post"]
PROBE_POS = ["k_pre", "k_fork", "k16", "R", "k_post"]
MAIN_POS = ["k_pre", "k_fork", "k16"]
N_PERM = 200
N_BOOT = 2000
TOPN = 20
C_REG = 0.1


# ---------------------------------------------------------------- data
def load_exp3(task: str) -> dict[str, Any]:
    """exp3 ban rows (arm G2) of the two main classes, all positions, layers 8..28 (float16, read in place)."""
    T = EXP3_TASK[task]
    meta = read_json(EXP3 / "states" / f"{T}_meta.json")
    parts = sorted((EXP3_SRC / "states").glob(f"{T}_part_*.npz"))
    Xs, Ms, Ks = [], [], []
    for p in parts:
        d = np.load(p)
        Xs.append(d["X"])
        Ms.append(d["mask"])
        Ks.append(d["ks"])
    X, M, K = np.concatenate(Xs), np.concatenate(Ms), np.concatenate(Ks)
    rows = meta["rows"]
    assert len(rows) == X.shape[0], (len(rows), X.shape)
    keep = [i for i, r in enumerate(rows) if r["arm"] == "G2"
            and EXP3_LABEL_MAP.get(r["label"]) in ({"bfs", "dfs"} if task == "t1" else {"dijkstra", "bf_spfa"})]
    lab = np.array([EXP3_LABEL_MAP[rows[i]["label"]] for i in keep])
    y = (lab == ("bfs" if task == "t1" else "dijkstra")).astype(int)
    g = np.array([int(rows[i]["paraphrase_id"]) for i in keep])
    out = {"X": X[keep], "mask": M[keep], "ks": K[keep], "y": y, "g": g, "labels": lab,
           "rows": [rows[i] for i in keep], "all_X": X, "all_rows": rows, "n_dropped": int(sum(
               1 for r in rows if r["arm"] == "G2") - len(keep))}
    return out


# ---------------------------------------------------------------- metrics
def auc(y: np.ndarray, s: np.ndarray) -> float:
    y = np.asarray(y)
    n1, n0 = int(y.sum()), int(len(y) - y.sum())
    if n1 == 0 or n0 == 0:
        return float("nan")
    r = rankdata(s)
    return float((r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def within_u(y: np.ndarray, s: np.ndarray, g: np.ndarray) -> tuple[float, int]:
    """(sum of Mann-Whitney U over groups, number of within-group (pos, neg) pairs)."""
    U, npairs = 0.0, 0
    for gg in np.unique(g):
        m = g == gg
        yy = y[m]
        n1, n0 = int(yy.sum()), int(len(yy) - yy.sum())
        if n1 == 0 or n0 == 0:
            continue
        r = rankdata(s[m])
        U += r[yy == 1].sum() - n1 * (n1 + 1) / 2
        npairs += n1 * n0
    return U, npairs


def within_auc(y: np.ndarray, s: np.ndarray, g: np.ndarray) -> tuple[float, int]:
    U, n = within_u(y, s, g)
    return (float(U / n) if n else float("nan")), n


def auc_matrix(Y: np.ndarray, S: np.ndarray) -> np.ndarray:
    """Column-wise AUC for labels Y (n x P) and scores S (n x P) (or S (n,) broadcast)."""
    if S.ndim == 1:
        S = np.repeat(S[:, None], Y.shape[1], axis=1)
    R = rankdata(S, axis=0)
    n1 = Y.sum(0)
    n0 = Y.shape[0] - n1
    with np.errstate(invalid="ignore", divide="ignore"):
        return ((R * Y).sum(0) - n1 * (n1 + 1) / 2) / (n1 * n0)


def within_auc_matrix(Y: np.ndarray, S: np.ndarray, g: np.ndarray) -> np.ndarray:
    U = np.zeros(Y.shape[1])
    NP = np.zeros(Y.shape[1])
    for gg in np.unique(g):
        m = g == gg
        Yg, Sg = Y[m], S[m]
        n1 = Yg.sum(0)
        n0 = Yg.shape[0] - n1
        R = rankdata(Sg, axis=0)
        U += np.where((n1 > 0) & (n0 > 0), (R * Yg).sum(0) - n1 * (n1 + 1) / 2, 0.0)
        NP += n1 * n0
    with np.errstate(invalid="ignore", divide="ignore"):
        return U / NP


def perm_within(y: np.ndarray, g: np.ndarray, n_perm: int, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    Y = np.repeat(y[:, None], n_perm, axis=1).copy()
    for gg in np.unique(g):
        idx = np.where(g == gg)[0]
        for p in range(n_perm):
            Y[idx, p] = y[idx][rng.permutation(len(idx))]
    return Y


def boot_groups(y: np.ndarray, s: np.ndarray, g: np.ndarray, n_boot: int = N_BOOT, seed: int = 1) -> dict[str, Any]:
    """95% CIs of pooled and within-group AUC, resampling groups with replacement."""
    rng = np.random.default_rng(seed)
    groups = np.unique(g)
    idx_by = {gg: np.where(g == gg)[0] for gg in groups}
    wu = {gg: within_u(y[idx_by[gg]], s[idx_by[gg]], np.zeros(len(idx_by[gg]))) for gg in groups}
    pooled, within = [], []
    for _ in range(n_boot):
        pick = rng.choice(groups, len(groups), replace=True)
        ii = np.concatenate([idx_by[gg] for gg in pick])
        a = auc(y[ii], s[ii])
        if np.isfinite(a):
            pooled.append(a)
        U = sum(wu[gg][0] for gg in pick)
        n = sum(wu[gg][1] for gg in pick)
        if n:
            within.append(U / n)

    def ci(v: list[float]) -> list[float | None]:
        return [float(np.quantile(v, 0.025)), float(np.quantile(v, 0.975))] if len(v) > 20 else [None, None]

    return {"pooled_ci": ci(pooled), "within_ci": ci(within)}


# ---------------------------------------------------------------- per-fold fitters
def _z(train_s: np.ndarray, test_s: np.ndarray) -> np.ndarray:
    m, sd = train_s.mean(), train_s.std()
    return (test_s - m) / (sd if sd > 1e-12 else 1.0)


def _standardize(Xtr: np.ndarray, Xte: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mu = Xtr.mean(0)
    sd = Xtr.std(0)
    sd[sd < 1e-8] = 1.0
    return (Xtr - mu) / sd, (Xte - mu) / sd


def fit_lr(Xtr: np.ndarray, ytr: np.ndarray, Xte: np.ndarray, svd: bool = False) -> tuple[np.ndarray, np.ndarray]:
    """Standardised L2 logistic regression (C=0.1, balanced). svd=True solves it exactly in the row span of the
    training data (representer theorem), which is lossless and ~50x faster when d >> n."""
    A, B = _standardize(Xtr, Xte)
    if svd:
        _, _, Vt = np.linalg.svd(A, full_matrices=False)
        A, B = A @ Vt.T, B @ Vt.T
    clf = LogisticRegression(C=C_REG, class_weight="balanced", max_iter=3000)
    clf.fit(A, ytr)
    return clf.decision_function(A), clf.decision_function(B)


def fit_dim(Xtr: np.ndarray, ytr: np.ndarray, Xte: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    mu1, mu0 = Xtr[ytr == 1].mean(0), Xtr[ytr == 0].mean(0)
    w = mu1 - mu0
    nw = np.linalg.norm(w)
    w = w / (nw if nw > 0 else 1.0)
    m = (mu1 + mu0) / 2
    return (Xtr - m) @ w, (Xte - m) @ w, w, float(m @ w)


def rank_units(Xtr: np.ndarray, ytr: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Per-unit training AUC (vectorised) -> (|AUC-0.5| ranking score, sign)."""
    R = rankdata(Xtr, axis=0)
    n1 = ytr.sum()
    n0 = len(ytr) - n1
    a = ((R[ytr == 1]).sum(0) - n1 * (n1 + 1) / 2) / (n1 * n0)
    return np.maximum(a, 1 - a), np.where(a >= 0.5, 1.0, -1.0)


METHODS = ["sae_top1", "sae_top20_lr", "raw_dim", "raw_lr", "neuron_top1", "neuron_top20_lr", "sae_code_dim"]


def prepare_folds(H: np.ndarray, Z: np.ndarray | None, g: np.ndarray) -> list[dict[str, Any]]:
    """Label-independent per-fold work (ranks, standardisation, SVD projection), reused across permutations."""
    folds = []
    for gg in np.unique(g):
        te, tr = g == gg, g != gg
        f: dict[str, Any] = {"g": int(gg), "te": te, "tr": tr, "RH": rankdata(H[tr], axis=0)}
        A, B = _standardize(H[tr], H[te])
        _, _, Vt = np.linalg.svd(A, full_matrices=False)
        f["HA"], f["HB"] = A @ Vt.T, B @ Vt.T
        if Z is not None:
            f["RZ"] = rankdata(Z[tr], axis=0)
        folds.append(f)
    return folds


def _rank_auc(R: np.ndarray, ytr: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    n1 = ytr.sum()
    n0 = len(ytr) - n1
    a = (R[ytr == 1].sum(0) - n1 * (n1 + 1) / 2) / (n1 * n0)
    return np.maximum(a, 1 - a), np.where(a >= 0.5, 1.0, -1.0)


def _lr_scores(A: np.ndarray, ytr: np.ndarray, B: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    clf = LogisticRegression(C=C_REG, class_weight="balanced", max_iter=3000)
    clf.fit(A, ytr)
    return clf.decision_function(A), clf.decision_function(B)


def nested_scores(H: np.ndarray, Z: np.ndarray | None, y: np.ndarray, g: np.ndarray,
                  methods: list[str] | None = None, folds: list[dict[str, Any]] | None = None
                  ) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    """Leave-one-group-out nested selection; returns pooled z-scored held-out scores per method and fold info.
    H: raw residuals (n x 4096); Z: SAE codes restricted to active latents (n x m) or None. Unit selection (top-1 /
    top-20 by training-fold AUC) happens inside each training fold only."""
    methods = methods or (METHODS if Z is not None else ["raw_dim", "raw_lr", "neuron_top1", "neuron_top20_lr"])
    folds = folds if folds is not None else prepare_folds(H, Z, g)
    out = {m: np.full(len(y), np.nan) for m in methods}
    info: dict[str, Any] = {"fold_top20_latents": {}, "fold_top20_dims": {}}
    for f in folds:
        te, tr = f["te"], f["tr"]
        ytr = y[tr]
        if ytr.sum() == 0 or ytr.sum() == len(ytr):
            continue
        if Z is not None:
            sc, sg = _rank_auc(f["RZ"], ytr)
            top = np.argsort(-sc, kind="stable")[:TOPN]
            info["fold_top20_latents"][f["g"]] = top.tolist()
            if "sae_top1" in out:
                j = top[0]
                out["sae_top1"][te] = _z(sg[j] * Z[tr, j], sg[j] * Z[te, j])
            if "sae_top20_lr" in out:
                A, B = _standardize(Z[tr][:, top], Z[te][:, top])
                a, b = _lr_scores(A, ytr, B)
                out["sae_top20_lr"][te] = _z(a, b)
            if "sae_code_dim" in out:
                a, b, _, _ = fit_dim(Z[tr], ytr, Z[te])
                out["sae_code_dim"][te] = _z(a, b)
        if "raw_dim" in out:
            a, b, _, _ = fit_dim(H[tr], ytr, H[te])
            out["raw_dim"][te] = _z(a, b)
        if "raw_lr" in out:
            a, b = _lr_scores(f["HA"], ytr, f["HB"])
            out["raw_lr"][te] = _z(a, b)
        if "neuron_top1" in out or "neuron_top20_lr" in out:
            sc, sg = _rank_auc(f["RH"], ytr)
            topd = np.argsort(-sc, kind="stable")[:TOPN]
            info["fold_top20_dims"][f["g"]] = topd.tolist()
            if "neuron_top1" in out:
                j = topd[0]
                out["neuron_top1"][te] = _z(sg[j] * H[tr, j], sg[j] * H[te, j])
            if "neuron_top20_lr" in out:
                A, B = _standardize(H[tr][:, topd], H[te][:, topd])
                a, b = _lr_scores(A, ytr, B)
                out["neuron_top20_lr"][te] = _z(a, b)
    return out, info


def score_summary(y: np.ndarray, g: np.ndarray, s: np.ndarray, boot: bool = True) -> dict[str, Any]:
    ok = np.isfinite(s)
    a = auc(y[ok], s[ok])
    w, npairs = within_auc(y[ok], s[ok], g[ok])
    rec = {"auc_pooled": a, "auc_within": w, "n_within_pairs": npairs, "n": int(ok.sum())}
    if boot:
        rec.update(boot_groups(y[ok], s[ok], g[ok]))
    return rec


def nested_with_null(H: np.ndarray, Z: np.ndarray | None, y: np.ndarray, g: np.ndarray, n_perm: int = N_PERM,
                     seed: int = 0) -> dict[str, Any]:
    """Observed nested scores + the whole nested pipeline rerun under within-group label permutations."""
    folds = prepare_folds(H, Z, g)
    obs, info = nested_scores(H, Z, y, g, folds=folds)
    res: dict[str, Any] = {m: score_summary(y, g, s) for m, s in obs.items()}
    Yp = perm_within(y, g, n_perm, seed)
    null_pooled = {m: [] for m in obs}
    null_within = {m: [] for m in obs}
    for p in range(n_perm):
        sp, _ = nested_scores(H, Z, Yp[:, p], g, methods=list(obs), folds=folds)
        for m, s in sp.items():
            ok = np.isfinite(s)
            null_pooled[m].append(auc(Yp[ok, p], s[ok]))
            null_within[m].append(within_auc(Yp[ok, p], s[ok], g[ok])[0])
    for m in obs:
        npool = np.array(null_pooled[m], dtype=float)
        nwith = np.array(null_within[m], dtype=float)
        res[m]["p_pooled"] = float((1 + np.sum(npool >= res[m]["auc_pooled"])) / (1 + np.isfinite(npool).sum()))
        res[m]["p_within"] = (float((1 + np.sum(nwith >= res[m]["auc_within"])) / (1 + np.isfinite(nwith).sum()))
                              if np.isfinite(res[m]["auc_within"]) else None)
        res[m]["null_pooled_q95"] = float(np.nanquantile(npool, 0.95))
        res[m]["null_within_q95"] = float(np.nanquantile(nwith, 0.95)) if np.isfinite(nwith).any() else None
    return {"methods": res, "fold_info": info, "scores": {m: s.tolist() for m, s in obs.items()}}


# ---------------------------------------------------------------- B2 layer probe
def layer_probe(task: str, D: dict[str, Any]) -> dict[str, Any]:
    y, g = D["y"], D["g"]
    out: dict[str, Any] = {}
    for pos in PROBE_POS:
        pj = POS_NAMES.index(pos)
        m = D["mask"][:, pj]
        for li, L in enumerate(LAYERS):
            H = D["X"][m, pj, li, :].astype(np.float32)
            yy, gg = y[m], g[m]
            sc, _ = nested_scores(H, None, yy, gg, methods=["raw_dim", "raw_lr"])
            rec = {"n": int(m.sum()), "n_pos": int(yy.sum())}
            for meth, s in sc.items():
                rec[meth] = score_summary(yy, gg, s, boot=False)
            # DiM within-paraphrase permutation null (vectorised over permutations)
            Yp = perm_within(yy, gg, N_PERM, seed=L)
            S = np.full(Yp.shape, np.nan)
            for gv in np.unique(gg):
                te, tr = gg == gv, gg != gv
                Ytr = Yp[tr]
                n1 = Ytr.sum(0)
                n0 = Ytr.shape[0] - n1
                ok = (n1 > 0) & (n0 > 0)
                M1 = (H[tr].T @ Ytr) / np.maximum(n1, 1)
                M0 = (H[tr].T @ (1 - Ytr)) / np.maximum(n0, 1)
                W = M1 - M0
                W /= np.maximum(np.linalg.norm(W, axis=0), 1e-12)
                mid = ((M1 + M0) / 2 * W).sum(0)
                st = H[tr] @ W - mid
                se = H[te] @ W - mid
                S[te] = np.where(ok, (se - st.mean(0)) / np.maximum(st.std(0), 1e-12), np.nan)
            na = auc_matrix(Yp, np.nan_to_num(S))
            nw = within_auc_matrix(Yp, np.nan_to_num(S), gg)
            rec["raw_dim"]["null_pooled_q95"] = float(np.nanquantile(na, 0.95))
            rec["raw_dim"]["p_pooled"] = float((1 + np.sum(na >= rec["raw_dim"]["auc_pooled"])) / (1 + len(na)))
            if np.isfinite(rec["raw_dim"]["auc_within"]):
                rec["raw_dim"]["null_within_q95"] = float(np.nanquantile(nw, 0.95))
                rec["raw_dim"]["p_within"] = float((1 + np.sum(nw >= rec["raw_dim"]["auc_within"])) / (1 + len(nw)))
            out[f"{pos}|L{L}"] = rec
        logger.info(f"layer probe {task} {pos}: within-paraphrase DiM AUC by layer "
                    f"{[round(out[f'{pos}|L{L}']['raw_dim']['auc_within'], 2) for L in LAYERS]}")
    return out


def confounds(task: str, D: dict[str, Any]) -> dict[str, Any]:
    """commit_idx per class, prefix identity with other-class rows of the same paraphrase, token at commit_idx."""
    pools = [r for r in read_jsonl(EXP3_SRC / "generations" / "pools.jsonl")
             if r["task"] == EXP3_TASK[task] and r.get("arm") == "G2"]
    by = {(r["paraphrase_id"], r["sample_id"]): r for r in pools}
    from transformers import AutoTokenizer

    from core import MODEL_HF

    tok = AutoTokenizer.from_pretrained(MODEL_HF)
    recs = []
    for r, lab in zip(D["rows"], D["labels"]):
        p = by.get((r["paraphrase_id"], r["sample_id"]))
        if p is None:
            continue
        c = p["commit_idx"]
        gids = p["gen_token_ids"]
        recs.append({"pid": r["paraphrase_id"], "label": str(lab), "commit_idx": c,
                     "prefix": tuple(gids[:c]) if c is not None else None,
                     "commit_token": tok.decode([gids[c]]) if c is not None and c < len(gids) else None})
    out: dict[str, Any] = {"n_matched": len(recs)}
    for lab in sorted({x["label"] for x in recs}):
        cs = [x["commit_idx"] for x in recs if x["label"] == lab and x["commit_idx"] is not None]
        toks: dict[str, int] = {}
        for x in recs:
            if x["label"] == lab and x["commit_token"] is not None:
                toks[x["commit_token"]] = toks.get(x["commit_token"], 0) + 1
        same = 0
        for x in recs:
            if x["label"] != lab or x["prefix"] is None:
                continue
            if any(o["pid"] == x["pid"] and o["label"] != lab and o["prefix"] == x["prefix"] for o in recs):
                same += 1
        n = sum(1 for x in recs if x["label"] == lab)
        out[lab] = {"n": n, "commit_idx_median": float(np.median(cs)) if cs else None,
                    "commit_idx_q10_q90": [float(np.quantile(cs, 0.1)), float(np.quantile(cs, 0.9))] if cs else None,
                    "share_prefix_identical_to_other_class_same_paraphrase": same / n if n else None,
                    "commit_token_counts": dict(sorted(toks.items(), key=lambda kv: -kv[1])[:10])}
    return out


def choose_layers(probe: dict[str, dict[str, Any]]) -> dict[str, Any]:
    cand = [L for L in LAYERS if 9 <= L <= 27]  # L-1 and L+1 must exist for the hook-alignment check
    score = {}
    for L in cand:
        vals, wts = [], []
        for task in TASKS:
            for pos, wgt in (("k_pre", 2.0), ("k_fork", 1.0), ("k16", 1.0)):
                v = probe[task][f"{pos}|L{L}"]["raw_dim"]["auc_within"]
                if v is not None and np.isfinite(v):
                    vals.append(v * wgt)
                    wts.append(wgt)
        score[L] = float(sum(vals) / sum(wts)) if wts else float("nan")
    order = sorted(cand, key=lambda L: (-score[L], L))
    L1 = order[0]
    L2 = [L for L in order if abs(L - L1) >= 4][0]
    L3 = [L for L in order if abs(L - L1) >= 4 and abs(L - L2) >= 4][0]
    chosen = sorted([L1, L2, L3])
    return {"score": score, "rule": "score(L)=weighted mean over tasks of within-paraphrase DiM AUC at k_pre (x2), "
            "k_fork, k16; L1=argmax, L2=argmax |L-L1|>=4, L3=argmax >=4 from L1 and L2; candidates 9..27",
            "L1": L1, "L2": L2, "L3": L3, "chosen": chosen,
            "overlap_with_jlens_source_layers": sorted(set(chosen) & {9, 18, 21, 22, 23, 24, 25, 26, 27}),
            "logged_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}


# ---------------------------------------------------------------- SAE
def sae_path(L: int) -> str:
    from huggingface_hub import hf_hub_download

    return hf_hub_download(SAE_REPO, f"layer{L}.sae.pt")


def load_sae(L: int) -> dict[str, np.ndarray]:
    import torch

    d = torch.load(sae_path(L), map_location="cpu", weights_only=True, mmap=True)  # fp32 on disk: no copy
    shapes = {k: tuple(v.shape) for k, v in d.items()}
    assert shapes["W_enc"] == (65536, 4096) and shapes["W_dec"] == (4096, 65536), shapes
    assert shapes["b_enc"] == (65536,) and shapes["b_dec"] == (4096,), shapes
    return {k: v.float().numpy() for k, v in d.items()}


def sae_encode(H: np.ndarray, S: dict[str, np.ndarray], k: int = SAE_K, chunk: int = 256) -> tuple[np.ndarray, float]:
    """Model-card encoder: pre = h @ W_enc.T + b_enc; keep top-k (values kept as is), zero the rest."""
    Z = np.zeros((H.shape[0], S["W_enc"].shape[0]), dtype=np.float32)
    neg = 0
    for a in range(0, H.shape[0], chunk):
        pre = H[a:a + chunk].astype(np.float32) @ S["W_enc"].T + S["b_enc"]
        idx = np.argpartition(-pre, k - 1, axis=1)[:, :k]
        vals = np.take_along_axis(pre, idx, axis=1)
        neg += int((vals < 0).sum())
        np.put_along_axis(Z[a:a + chunk], idx, vals, axis=1)
    return Z, neg / max(1, H.shape[0] * k)


def sae_decode(Z: np.ndarray, S: dict[str, np.ndarray]) -> np.ndarray:
    return Z @ S["W_dec"].T + S["b_dec"]


def fvu(H: np.ndarray, R: np.ndarray) -> float:
    return float(((H - R) ** 2).sum() / ((H - H.mean(0)) ** 2).sum())


# ---------------------------------------------------------------- B5 worker
def _b5_worker(args: tuple) -> tuple[str, dict[str, Any]]:
    task, L, pos, H, Z, y, g, n_perm = args
    t0 = time.time()
    act = (Z != 0).sum(0) >= 5
    Za = Z[:, act]
    act_ids = np.where(act)[0]
    res = nested_with_null(H, Za, y, g, n_perm=n_perm, seed=L * 10 + MAIN_POS.index(pos))
    # in-sample ranking + max-statistic null over all active latents
    sc, sg = rank_units(Za, y)
    order = np.argsort(-sc, kind="stable")[:TOPN]
    Yp = perm_within(y, g, n_perm, seed=999 + L)
    R = rankdata(Za, axis=0)
    n1 = y.sum()
    n0 = len(y) - n1
    A = ((R.T @ Yp) - n1 * (n1 + 1) / 2) / (n1 * n0)
    mx = np.maximum(A, 1 - A).max(0)
    thr = float(np.quantile(mx, 0.95))
    folds = res["fold_info"]["fold_top20_latents"]
    final = []
    for j in order:
        lid = int(act_ids[j])
        final.append({"latent": lid, "auc_in_sample": float(sc[j] if sg[j] > 0 else 1 - sc[j]),
                      "abs_auc": float(sc[j]), "sign": int(sg[j]),
                      "n_folds_selected": int(sum(j in set(v) for v in folds.values())),
                      "mean_act_banned_class": float(Za[y == 1, j].mean()),
                      "mean_act_substitute_class": float(Za[y == 0, j].mean()),
                      "frac_active_banned": float((Za[y == 1, j] != 0).mean()),
                      "frac_active_substitute": float((Za[y == 0, j] != 0).mean()),
                      "passes_maxstat_null": bool(sc[j] > thr)})
    res["fold_info"]["fold_top20_latents"] = {k: [int(act_ids[j]) for j in v] for k, v in folds.items()}
    out = {"task": task, "layer": L, "position": pos, "n": int(len(y)), "n_banned_class": int(y.sum()),
           "n_active_latents": int(act.sum()), "maxstat_null_q95": thr, "final_top20": final, **res,
           "seconds": round(time.time() - t0, 1)}
    return f"{task}|L{L}|{pos}", out


def fit_all_rows_objects(H: np.ndarray, Z: np.ndarray, y: np.ndarray) -> dict[str, Any]:
    """Readout objects fitted on ALL exp3 ban rows (applied to the fresh pool in E3)."""
    act = np.where((Z != 0).sum(0) >= 5)[0]
    Za = Z[:, act]
    sc, sg = rank_units(Za, y)
    top = np.argsort(-sc, kind="stable")[:TOPN]
    obj: dict[str, Any] = {}
    j = top[0]
    s1 = sg[j] * Za[:, j]
    obj["sae_top1"] = {"latent": int(act[j]), "sign": float(sg[j]), "mu": float(s1.mean()), "sd": float(s1.std())}
    # top-20 latent LR
    Zt = Za[:, top]
    mu, sd = Zt.mean(0), Zt.std(0)
    sd[sd < 1e-8] = 1
    clf = LogisticRegression(C=C_REG, class_weight="balanced", max_iter=3000).fit((Zt - mu) / sd, y)
    d = clf.decision_function((Zt - mu) / sd)
    obj["sae_top20_lr"] = {"latents": act[top].tolist(), "mu": mu.tolist(), "sd": sd.tolist(),
                           "coef": clf.coef_[0].tolist(), "b": float(clf.intercept_[0]), "dmu": float(d.mean()),
                           "dsd": float(d.std())}
    a, _, w, mid = fit_dim(H, y, H)
    obj["raw_dim"] = {"w": w.tolist(), "mid": mid, "mu": float(a.mean()), "sd": float(a.std())}
    muH, sdH = H.mean(0), H.std(0)
    sdH[sdH < 1e-8] = 1
    clf2 = LogisticRegression(C=C_REG, class_weight="balanced", max_iter=3000).fit((H - muH) / sdH, y)
    d2 = clf2.decision_function((H - muH) / sdH)
    obj["raw_lr"] = {"mu": muH.tolist(), "sd": sdH.tolist(), "coef": clf2.coef_[0].tolist(),
                     "b": float(clf2.intercept_[0]), "dmu": float(d2.mean()), "dsd": float(d2.std())}
    scd, sgd = rank_units(H, y)
    topd = np.argsort(-scd, kind="stable")[:TOPN]
    Ht = H[:, topd]
    mu3, sd3 = Ht.mean(0), Ht.std(0)
    sd3[sd3 < 1e-8] = 1
    clf3 = LogisticRegression(C=C_REG, class_weight="balanced", max_iter=3000).fit((Ht - mu3) / sd3, y)
    d3 = clf3.decision_function((Ht - mu3) / sd3)
    obj["neuron_top20_lr"] = {"dims": topd.tolist(), "mu": mu3.tolist(), "sd": sd3.tolist(),
                              "coef": clf3.coef_[0].tolist(), "b": float(clf3.intercept_[0]), "dmu": float(d3.mean()),
                              "dsd": float(d3.std())}
    obj["neuron_top1"] = {"dim": int(topd[0]), "sign": float(sgd[topd[0]])}
    a6, _, w6, mid6 = fit_dim(Za, y, Za)
    obj["sae_code_dim"] = {"latents": act.tolist(), "w": w6.tolist(), "mid": mid6, "mu": float(a6.mean()),
                           "sd": float(a6.std())}
    return obj


def apply_objects(obj: dict[str, Any], H: np.ndarray, Z: np.ndarray) -> dict[str, np.ndarray]:
    """Scores of exp3-fitted objects on new states H (n x 4096) with SAE codes Z (n x 65536)."""
    s: dict[str, np.ndarray] = {}
    o = obj["sae_top1"]
    s["sae_top1"] = o["sign"] * Z[:, o["latent"]]
    o = obj["sae_top20_lr"]
    s["sae_top20_lr"] = ((Z[:, o["latents"]] - np.array(o["mu"])) / np.array(o["sd"])) @ np.array(o["coef"]) + o["b"]
    o = obj["raw_dim"]
    s["raw_dim"] = H @ np.array(o["w"]) - o["mid"]
    o = obj["raw_lr"]
    s["raw_lr"] = ((H - np.array(o["mu"])) / np.array(o["sd"])) @ np.array(o["coef"]) + o["b"]
    o = obj["neuron_top20_lr"]
    s["neuron_top20_lr"] = ((H[:, o["dims"]] - np.array(o["mu"])) / np.array(o["sd"])) @ np.array(o["coef"]) + o["b"]
    o = obj["neuron_top1"]
    s["neuron_top1"] = o["sign"] * H[:, o["dim"]]
    o = obj["sae_code_dim"]
    s["sae_code_dim"] = Z[:, o["latents"]] @ np.array(o["w"]) - o["mid"]
    return s


# ---------------------------------------------------------------- stage B
def run_stage_b() -> None:
    probe_path = RESULTS / "layer_probe.json"
    with Timer("B2_layer_probe", gpu=False):
        if probe_path.exists():
            LP = read_json(probe_path)
        else:
            LP = {"tasks": {}, "confounds": {}}
            for task in TASKS:
                D = load_exp3(task)
                logger.info(f"{task}: {len(D['y'])} ban rows ({int(D['y'].sum())} banned-class), groups "
                            f"{np.unique(D['g']).tolist()}, dropped {D['n_dropped']}")
                LP["tasks"][task] = layer_probe(task, D)
                LP["confounds"][task] = confounds(task, D)
                del D
                gc.collect()
            LP["choice"] = choose_layers(LP["tasks"])
            write_json(probe_path, LP)
    choice = LP["choice"]
    logger.info(f"B3 layer choice (logged before any SAE download): {choice['chosen']} score top: "
                f"{sorted(choice['score'].items(), key=lambda kv: -kv[1])[:5]}")
    layers = choice["chosen"]
    # B4: download + alignment check
    align_path = RESULTS / "sae_alignment.json"
    with Timer("B4_sae_alignment", gpu=False):
        AL = read_json(align_path, {"layers": {}})
        Dall = {t: load_exp3(t) for t in TASKS}
        for L in layers:
            if str(L) in AL["layers"]:
                continue
            S = load_sae(L)
            rec: dict[str, Any] = {}
            for dl in (-1, 0, 1):
                li = LAYERS.index(L + dl)
                Hs = []
                for t in TASKS:
                    X = Dall[t]["all_X"]
                    pj = POS_NAMES.index("k16")
                    Hs.append(X[:, pj, li, :].astype(np.float32))
                H = np.concatenate(Hs)
                Z, negfrac = sae_encode(H, S)
                Rc = sae_decode(Z, S)
                # FVU's denominator is the across-row variance, which is tiny for k16 states of shared prompts, so
                # the per-row relative MSE and cosine are also logged (they do not depend on batch diversity).
                rel = float(np.mean(((H - Rc) ** 2).sum(1) / (H ** 2).sum(1)))
                cos = float(np.mean((H * Rc).sum(1) / (np.linalg.norm(H, axis=1) * np.linalg.norm(Rc, axis=1))))
                rec[f"L{L + dl}"] = {"fvu": fvu(H, Rc), "rel_mse": rel, "cos": cos, "frac_negative_kept": negfrac,
                                     "n": len(H)}
            best = min(rec, key=lambda k: rec[k]["rel_mse"])
            rec["argmin"] = best
            rec["aligned"] = best == f"L{L}"
            AL["layers"][str(L)] = rec
            logger.info(f"SAE L{L} FVU at L-1/L/L+1: {[round(rec[k]['fvu'], 3) for k in rec if k.startswith('L')]} "
                        f"-> aligned={rec['aligned']}")
            write_json(align_path, AL)
            del S
            gc.collect()
    # B5: discovery
    disc_path = RESULTS / "readout_i_discovery.json"
    with Timer("B5_discovery", gpu=False):
        DISC = read_json(disc_path, {"configs": {}, "objects": {}})
        jobs = []
        codes = {}
        for L in layers:
            S = load_sae(L)
            li = LAYERS.index(L)
            for t in TASKS:
                D = Dall[t]
                for pos in MAIN_POS:
                    pj = POS_NAMES.index(pos)
                    m = D["mask"][:, pj]
                    key = f"{t}|L{L}|{pos}"
                    n1 = int(D["y"][m].sum())
                    if m.sum() < 10 or n1 < 3 or int(m.sum()) - n1 < 3:
                        # e.g. t1 k_fork: exp3 located no fork token for any T1 ban row (mask all False)
                        DISC["configs"][key] = {"status": "skipped", "n": int(m.sum()), "n_banned_class": n1,
                                                "reason": "fewer than 10 masked rows or fewer than 3 per class"}
                        logger.warning(f"B5 {key}: skipped (n={int(m.sum())}, n_banned={n1})")
                        continue
                    H = D["X"][m, pj, li, :].astype(np.float32)
                    Z, _ = sae_encode(H, S)
                    codes[key] = (H, Z, D["y"][m], D["g"][m])
                    if key not in DISC["objects"]:
                        DISC["objects"][key] = fit_all_rows_objects(H, Z, D["y"][m])
                    if key not in DISC["configs"]:
                        jobs.append((t, L, pos, H, Z, D["y"][m], D["g"][m], N_PERM))
            del S
            gc.collect()
        logger.info(f"B5: {len(jobs)} nested configs to run (200 within-paraphrase permutations each)")
        if jobs:
            with ProcessPoolExecutor(max_workers=3, mp_context=mp.get_context("spawn")) as ex:
                for key, out in ex.map(_b5_worker, jobs):  # noqa: B020
                    DISC["configs"][key] = out
                    meth = out["methods"]
                    logger.info(f"B5 {key}: within AUC sae_top1={meth['sae_top1']['auc_within']:.3f} "
                                f"sae_top20={meth['sae_top20_lr']['auc_within']:.3f} dim={meth['raw_dim']['auc_within']:.3f} "
                                f"rawlr={meth['raw_lr']['auc_within']:.3f} neuron20={meth['neuron_top20_lr']['auc_within']:.3f} "
                                f"({out['seconds']}s)")
                    write_json(disc_path, DISC)
        write_json(disc_path, DISC)
        # sparse codes of the exp3 ban rows (top-50 indices + values) for the replication and contexts
        for key, (H, Z, y, g) in codes.items():
            idx = np.argsort(-np.abs(Z), axis=1)[:, :SAE_K]
            np.savez_compressed(TENSORS / f"exp3_codes_{key.replace('|', '_')}.npz",
                                idx=idx.astype(np.int32), val=np.take_along_axis(Z, idx, 1).astype(np.float16),
                                y=y, g=g)
    add_deviation("D07", "B2 layer-probe permutation null is computed for DiM only (200 within-paraphrase "
                  "permutations); the full nested null for every method runs at the 3 chosen layers (B5).",
                  "A logistic-regression null at all 21 layers x 5 positions x 2 tasks is ~100x the CPU budget.",
                  "Layer choice uses the DiM within-paraphrase AUC, as the rule specifies; no method's p-value at "
                  "non-chosen layers is reported except DiM's.")


if __name__ == "__main__":
    from core import setup_logging

    setup_logging("stage_B")
    run_stage_b()
