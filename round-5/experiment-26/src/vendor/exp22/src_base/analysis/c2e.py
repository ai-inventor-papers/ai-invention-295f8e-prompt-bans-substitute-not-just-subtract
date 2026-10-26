#!/usr/bin/env python3
"""9.2 C2e: is there a within-ban locus -- a residual state that linearly predicts the default-vs-other choice better
than the written text does at matched capacity?

Per eligible task (>= 8 of each class among the named-ban samples; T1 includes the declared W4 top-up), per position
in {S-mean, R, k1..k8, k16} and block 8..28: L2 logistic (batched Newton-IRLS on the GPU, balanced class weights,
unpenalised intercept) on standardised states after PCA-64 fit on the training fold; C by inner 3-fold CV (pooled
log-loss) from {1e-3, 1e-2, 1e-1, 1}; 5 outer folds stratified by (template, class); pooled balanced accuracy.
Null: within-template label permutations with full refits (inner CV included) and a layer-max statistic per position.
Text controls at each k (all with template one-hot): Ta one-hot token ids 1..k; Tb layer-0 embeddings (mean 1..k ++
token k) PCA-64; Tc exact prefix-match leave-one-out majority within template. R baseline = decoder at R.
"""

from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from typing import Any

import numpy as np
import torch
from loguru import logger
from sklearn.model_selection import StratifiedKFold

import states_io
from cfg import DEFAULT, SAVE_BLOCKS, STATES_DIR, read_jsonl

CS = [1e-3, 1e-2, 1e-1, 1.0]
N_PCA = 64
POS = ["Smean", "R"] + [f"k{k}" for k in range(1, 9)] + ["k16"]
DEV = torch.device("cuda" if torch.cuda.is_available() else "cpu")
DT = torch.float32
NOT_ATT = ("invalid", "disputed")


# ------------------------------------------------------------------------------------------------ batched IRLS
def _obj(Z: torch.Tensor, beta: torch.Tensor, Y: torch.Tensor, W: torch.Tensor, lamR: torch.Tensor) -> torch.Tensor:
    eta = torch.einsum("...nd,...d->...n", Z, beta)
    ll = W * (torch.nn.functional.softplus(eta) - Y * eta)
    return ll.sum(-1) + 0.5 * (lamR * beta * beta).sum(-1)


def irls(Z: torch.Tensor, Y: torch.Tensor, W: torch.Tensor, lam: torch.Tensor, n_iter: int = 25) -> torch.Tensor:
    """Batched L2 logistic. Z [..., N, D] (intercept last column, unpenalised), Y/W [..., N], lam [...] = 1/C.
    Minimises sum_n W_n logloss_n + lam/2 ||slopes||^2 (sklearn's C * sum w logloss + 1/2 ||w||^2 optimum)."""
    D = Z.shape[-1]
    R = torch.ones(D, device=Z.device, dtype=Z.dtype)
    R[-1] = 0.0
    lamR = lam[..., None] * R
    beta = torch.zeros(Z.shape[:-2] + (D,), device=Z.device, dtype=Z.dtype)
    obj = _obj(Z, beta, Y, W, lamR)
    eye = torch.eye(D, device=Z.device, dtype=Z.dtype)
    for _ in range(n_iter):
        eta = torch.einsum("...nd,...d->...n", Z, beta)
        p = torch.sigmoid(eta)
        g = torch.einsum("...nd,...n->...d", Z, W * (p - Y)) + lamR * beta
        s = W * p * (1 - p)
        H = torch.einsum("...nd,...n,...ne->...de", Z, s, Z) + torch.diag_embed(lamR) + 1e-6 * eye
        L, info = torch.linalg.cholesky_ex(H)
        delta = torch.cholesky_solve(g[..., None], L)[..., 0]
        delta = torch.nan_to_num(delta)
        best_b, best_o = beta, obj
        for t in (1.0, 0.5, 0.25, 0.1):
            cand = beta - t * delta
            o = _obj(Z, cand, Y, W, lamR)
            better = o < best_o
            best_b = torch.where(better[..., None], cand, best_b)
            best_o = torch.where(better, o, best_o)
        conv = (obj - best_o).abs().max() < 1e-6 * (best_o.abs().max() + 1)
        beta, obj = best_b, best_o
        if bool(conv):
            break
    return beta


def bal_weights(Y: torch.Tensor, M: torch.Tensor) -> torch.Tensor:
    """Balanced class weights within the fit mask M (0/1)."""
    n = M.sum(-1, keepdim=True)
    n1 = (M * Y).sum(-1, keepdim=True)
    n0 = n - n1
    return M * (Y * n / (2 * n1.clamp(min=1)) + (1 - Y) * n / (2 * n0.clamp(min=1)))


def ba_np(y: np.ndarray, pred: np.ndarray) -> float:
    m1, m0 = y == 1, y == 0
    if m1.sum() == 0 or m0.sum() == 0:
        return float("nan")
    return 0.5 * (float((pred[m1] == 1).mean()) + float((pred[m0] == 0).mean()))


def ba_t(Y: torch.Tensor, P: torch.Tensor) -> torch.Tensor:
    """Balanced accuracy along the last axis; Y, P 0/1 tensors with identical shapes."""
    n1 = Y.sum(-1)
    n0 = (1 - Y).sum(-1)
    tp = (Y * P).sum(-1)
    tn = ((1 - Y) * (1 - P)).sum(-1)
    return 0.5 * (tp / n1.clamp(min=1) + tn / n0.clamp(min=1))


# ------------------------------------------------------------------------------------------------ features
def fold_features(X: torch.Tensor, train_masks: list[np.ndarray], n_comp: int = N_PCA,
                  extra: np.ndarray | None = None) -> torch.Tensor:
    """X [G, N, D] (G feature sets, e.g. blocks) -> Z [G, F, N, n_comp + n_extra + 1]: per fold, standardise with the
    training rows, PCA on the training rows, standardise the PC scores; extra columns (template one-hot) appended;
    intercept last."""
    G, N, D = X.shape
    out = []
    for tr in train_masks:
        trt = torch.as_tensor(tr, device=X.device)
        Xt = X[:, trt]
        mu = Xt.mean(1, keepdim=True)
        sd = Xt.std(1, keepdim=True).clamp(min=1e-6)
        Xs = (X - mu) / sd
        k = min(n_comp, int(trt.sum()) - 1, D)
        U, S, Vh = torch.linalg.svd(Xs[:, trt], full_matrices=False)
        Vk = Vh[:, :k].transpose(1, 2)  # [G, D, k]
        Zs = Xs @ Vk
        zm = Zs[:, trt].mean(1, keepdim=True)
        zs = Zs[:, trt].std(1, keepdim=True).clamp(min=1e-6)
        Zs = (Zs - zm) / zs
        cols = [Zs]
        if extra is not None:
            cols.append(torch.as_tensor(extra, device=X.device, dtype=X.dtype)[None].expand(G, -1, -1))
        cols.append(torch.ones(G, N, 1, device=X.device, dtype=X.dtype))
        out.append(torch.cat(cols, -1))
    return torch.stack(out, 1)  # [G, F, N, D']


def inner_masks(y: np.ndarray, strata: np.ndarray, train: np.ndarray, seed: int) -> list[np.ndarray]:
    idx = np.where(train)[0]
    skf = StratifiedKFold(3, shuffle=True, random_state=seed)
    st = strata[idx]
    # strata with < 3 members: fall back to class-only stratification
    if min(Counter(st).values()) < 3:
        st = y[idx]
    out = []
    for tr_i, _ in skf.split(idx, st):
        m = np.zeros(len(y), bool)
        m[idx[tr_i]] = True
        out.append(m)
    return out


def decode(Z: torch.Tensor, Yb: torch.Tensor, outer_tr: list[np.ndarray], inner_tr: list[list[np.ndarray]],
           chunk: int = 20) -> torch.Tensor:
    """Z [G, F, N, D]; Yb [B, N] label vectors (row 0 observed, rest permutations) -> out-of-fold predictions
    [G, B, N] (0/1) with C chosen per (g, b, fold) by inner 3-fold CV pooled weighted log-loss."""
    G, F, N, D = Z.shape
    B = Yb.shape[0]
    lam_all = torch.tensor([1.0 / c for c in CS], device=Z.device, dtype=Z.dtype)
    K = len(CS)
    OT = torch.as_tensor(np.stack(outer_tr), device=Z.device, dtype=Z.dtype)  # [F, N]
    IT = torch.as_tensor(np.stack([np.stack(x) for x in inner_tr]), device=Z.device, dtype=Z.dtype)  # [F, 3, N]
    preds = torch.zeros(G, B, N, device=Z.device, dtype=Z.dtype)
    for b0 in range(0, B, chunk):
        Y = Yb[b0:b0 + chunk]  # [b, N]
        b = Y.shape[0]
        # inner CV: shapes [G, b, F, 3, K, N]
        Zi = Z[:, None, :, None, None]                      # [G,1,F,1,1,N,D]
        Yi = Y[None, :, None, None, None, :]                # [1,b,1,1,1,N]
        Mi = IT[None, None, :, :, None, :]                  # [1,1,F,3,1,N]
        Wi = bal_weights(Yi.expand(G, b, F, 3, K, N), Mi.expand(G, b, F, 3, K, N))
        lam = lam_all[None, None, None, None, :].expand(G, b, F, 3, K)
        beta = irls(Zi.expand(G, b, F, 3, K, N, D), Yi.expand(G, b, F, 3, K, N), Wi, lam)
        eta = torch.einsum("gfnd,gbfjkd->gbfjkn", Z, beta)
        # validation = outer-train rows not in the inner-train fit
        Vm = (OT[:, None, :] * (1 - IT))[None, None, :, :, None, :]  # [1,1,F,3,1,N]
        Wv = bal_weights(Yi.expand(G, b, F, 3, K, N), Vm.expand(G, b, F, 3, K, N))
        ll = (Wv * (torch.nn.functional.softplus(eta) - Yi * eta)).sum(-1).sum(3)  # [G,b,F,K]
        kbest = ll.argmin(-1)  # [G,b,F]
        lam_o = lam_all[kbest]
        Mo = OT[None, None, :, :]
        Yo = Y[None, :, None, :].expand(G, b, F, N)
        Wo = bal_weights(Yo, Mo.expand(G, b, F, N))
        beta_o = irls(Z[:, None].expand(G, b, F, N, D), Yo, Wo, lam_o)
        eta_o = torch.einsum("gfnd,gbfd->gbfn", Z, beta_o)
        test = (1 - OT)[None, None]  # [1,1,F,N]
        p = ((eta_o > 0).to(Z.dtype) * test).sum(2)  # each row is a test row in exactly one fold
        preds[:, b0:b0 + b] = p
        del beta, eta, ll, beta_o, eta_o
    return preds


# ------------------------------------------------------------------------------------------------ data
def load_task(task: str, archive: bool = False) -> dict[str, Any] | None:
    labs = {r["key"]: r for r in read_jsonl(STATES_DIR.parent / "data" / "labels.jsonl")}
    tags = [f"{task}_ARCHIVE"] if archive else [f"{task}_BAN"] + ([f"{task}_BAN_TOPUP"] if task == "T1" else [])
    Xs, E, idx = [], [], []
    for tag in tags:
        if not states_io.exists(STATES_DIR / tag):
            continue
        Xs.append(states_io.load(STATES_DIR / tag))
        e = STATES_DIR / f"{tag}_embed.npy"
        E.append(np.load(e) if e.exists() else None)
        idx += [json.loads(l) for l in open(STATES_DIR / f"{tag}_index.jsonl")]
    if not Xs:
        return None
    X = np.concatenate([np.asarray(x) for x in Xs])
    Em = np.concatenate(E) if all(e is not None for e in E) else None
    lab = []
    for r in idx:
        l = r.get("label")
        if r.get("key") in labs:
            l = labs[r["key"]]["label"]
        lab.append(l)
    keep = np.array([l is not None and l not in NOT_ATT for l in lab])
    y = np.array([int(l == DEFAULT[task]) if l is not None else -1 for l in lab])
    meta = json.load(open(STATES_DIR / f"{tags[0]}_meta.json"))
    return {"X": X[keep], "E": Em[keep] if Em is not None else None, "y": y[keep],
            "templates": np.array([r["template"] for r in idx])[keep], "tok16": [r["tok16"] for r, k in zip(idx, keep) if k],
            "n_gen": np.array([r["n_gen"] for r in idx])[keep], "blocks": meta["blocks"],
            "labels": [l for l, k in zip(lab, keep) if k], "n_excluded": int((~keep).sum())}


def within_template_perms(y: np.ndarray, g: np.ndarray, n: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    out = np.empty((n, len(y)), dtype=y.dtype)
    groups = [np.where(g == w)[0] for w in np.unique(g)]
    for i in range(n):
        yy = y.copy()
        for ix in groups:
            yy[ix] = y[rng.permutation(ix)]
        out[i] = yy
    return out


def template_onehot(g: np.ndarray) -> np.ndarray:
    ws = sorted(np.unique(g))
    return np.stack([(g == w).astype(np.float32) for w in ws], 1)


# ------------------------------------------------------------------------------------------------ text controls
def tc_prefix_ba(tok16: list[list[int]], y: np.ndarray, g: np.ndarray, k: int) -> float:
    """Exact prefix-match leave-one-out majority within template; fallback = template majority (LOO)."""
    pred = np.zeros(len(y), int)
    for i in range(len(y)):
        same = [j for j in range(len(y)) if j != i and g[j] == g[i]]
        pm = [j for j in same if tok16[j][:k] == tok16[i][:k]]
        pool = pm if pm else same
        if not pool:
            pred[i] = int(round(y.mean()))
            continue
        c = Counter(int(y[j]) for j in pool)
        pred[i] = 1 if c[1] > c[0] else (0 if c[0] > c[1] else int(np.mean(y[same]) >= 0.5) if same else 0)
    return ba_np(y, pred)


def onehot_tokens(tok16: list[list[int]], k: int) -> np.ndarray:
    cols: dict[tuple[int, int], int] = {}
    for t in tok16:
        for j in range(k):
            cols.setdefault((j, t[j]), len(cols))
    A = np.zeros((len(tok16), len(cols)), np.float32)
    for i, t in enumerate(tok16):
        for j in range(k):
            A[i, cols[(j, t[j])]] = 1.0
    return A


def raw_features(A: np.ndarray, extra: np.ndarray) -> torch.Tensor:
    """No PCA: [1, F=1-broadcast later] -- returns Z [1, N, D] with template one-hot and intercept."""
    Z = np.concatenate([A, extra, np.ones((len(A), 1), np.float32)], 1)
    return torch.as_tensor(Z, device=DEV, dtype=DT)


# ------------------------------------------------------------------------------------------------ main
def run_task(task: str, n_perm: int = 500, archive: bool = False, seed: int = 0) -> dict[str, Any]:
    d = load_task(task, archive=archive)
    if d is None:
        return {"status": "no states"}
    y, g = d["y"], d["templates"]
    n1, n0 = int((y == 1).sum()), int((y == 0).sum())
    res: dict[str, Any] = {"n": int(len(y)), "n_default": n1, "n_other": n0, "n_excluded": d["n_excluded"],
                           "blocks": d["blocks"], "label_counts": dict(Counter(d["labels"]))}
    if n1 < 8 or n0 < 8:
        res["status"] = "not testable (< 8 per class)"
        return res
    res["status"] = "testable"
    strata = np.array([f"{w}|{c}" for w, c in zip(g, y)])
    st = strata if min(Counter(strata).values()) >= 5 else y
    skf = StratifiedKFold(5, shuffle=True, random_state=seed)
    outer = []
    for tr, _ in skf.split(np.zeros(len(y)), st):
        m = np.zeros(len(y), bool)
        m[tr] = True
        outer.append(m)
    inner = [inner_masks(y, strata, m, seed + 1 + i) for i, m in enumerate(outer)]
    perms = within_template_perms(y, g, n_perm, seed + 100)
    Yb = torch.as_tensor(np.concatenate([y[None], perms]), device=DEV, dtype=DT)
    yt = Yb
    oh = template_onehot(g)
    curves: dict[str, Any] = {}
    nullmax: dict[str, Any] = {}
    for pi, pname in enumerate(POS):
        X = torch.as_tensor(np.ascontiguousarray(d["X"][:, pi].transpose(1, 0, 2)), device=DEV, dtype=DT)  # [G,N,D]
        Z = fold_features(X, outer)
        del X
        P = decode(Z, Yb, outer, inner)  # [G, B, N]
        ba = ba_t(yt[None].expand_as(P), P)  # [G, B]
        obs = ba[:, 0].cpu().numpy()
        lmax = ba[:, 1:].max(0).values.cpu().numpy()  # layer-max per permutation
        curves[pname] = {"ba_by_block": {int(b): float(v) for b, v in zip(d["blocks"], obs)},
                         "max_ba": float(obs.max()), "argmax_block": int(d["blocks"][int(obs.argmax())])}
        # within-template BA (templates containing both classes), observed predictions of the best block
        pb = P[int(obs.argmax()), 0].cpu().numpy()
        wt = [ba_np(y[g == w], pb[g == w]) for w in np.unique(g) if len(set(y[g == w])) == 2]
        curves[pname]["within_template_ba_best_block"] = float(np.mean(wt)) if wt else None
        nullmax[pname] = {"q95": float(np.quantile(lmax, 0.95)), "mean": float(lmax.mean()),
                          "p_layer_max": float((np.sum(lmax >= obs.max()) + 1) / (len(lmax) + 1))}
        del Z, P
        torch.cuda.empty_cache()
        logger.info(f"C2e {task}{' archive' if archive else ''} {pname}: max BA {obs.max():.3f} at block "
                    f"{curves[pname]['argmax_block']}; null q95 {nullmax[pname]['q95']:.3f}")
    res["state_curves"] = curves
    res["null_layer_max"] = nullmax
    # text controls at k = 1..8 and 16
    ctrl: dict[str, Any] = {}
    Y1 = Yb[:1]
    for k in list(range(1, 9)) + [16]:
        c: dict[str, Any] = {}
        A = onehot_tokens(d["tok16"], k)
        Z = raw_features(A, oh)[None, None].expand(1, len(outer), -1, -1).contiguous()
        c["Ta"] = float(ba_t(Y1[None].expand(1, 1, -1), decode(Z, Y1, outer, inner))[0, 0])
        if d["E"] is not None and k <= 8:
            Em = d["E"][:, :k].astype(np.float32)
            feat = np.concatenate([Em.mean(1), Em[:, k - 1]], 1)
            X = torch.as_tensor(feat, device=DEV, dtype=DT)[None]
            Z = fold_features(X, outer, extra=oh)
            c["Tb"] = float(ba_t(Y1[None].expand(1, 1, -1), decode(Z, Y1, outer, inner))[0, 0])
        c["Tc"] = tc_prefix_ba(d["tok16"], y, g, k)
        ctrl[f"k{k}"] = c
    # template-only decoder (= R by construction) for reference
    Z = raw_features(np.zeros((len(y), 0), np.float32), oh)[None, None].expand(1, len(outer), -1, -1).contiguous()
    res["template_only_ba"] = float(ba_t(Y1[None].expand(1, 1, -1), decode(Z, Y1, outer, inner))[0, 0])
    res["text_controls"] = ctrl
    # locus rule
    ba_R = curves["R"]["max_ba"]
    locus = None
    rows = []
    for k in range(1, 9):
        s = curves[f"k{k}"]["max_ba"]
        tc = ctrl[f"k{k}"]
        best_text = max(v for v in (ba_R, tc.get("Ta"), tc.get("Tb"), tc.get("Tc")) if v is not None)
        cond1 = s >= best_text + 0.10
        cond2 = s > nullmax[f"k{k}"]["q95"]
        rows.append({"k": k, "state_ba": s, "best_text_or_R": best_text, "margin": s - best_text,
                     "beats_text_by_0.10": bool(cond1), "above_null_q95": bool(cond2)})
        if locus is None and cond1 and cond2:
            locus = {"k": k, "block": curves[f"k{k}"]["argmax_block"]}
    res["locus_table"] = rows
    res["locus"] = locus
    res["locus_at_tokens_1_3"] = bool(locus and locus["k"] <= 3)
    # first-divergence index: first k whose prefix leaves the template's default-class prefix tree
    fd = []
    for i in range(len(y)):
        same_def = [j for j in range(len(y)) if j != i and g[j] == g[i] and y[j] == 1]
        kk = None
        for k in range(1, 17):
            if not any(d["tok16"][j][:k] == d["tok16"][i][:k] for j in same_def):
                kk = k
                break
        fd.append(kk)
    by = defaultdict(list)
    for v, c in zip(fd, y):
        by[int(c)].append(v if v is not None else 17)
    res["first_divergence"] = {("default" if c == 1 else "other"): {"median": float(np.median(v)),
                                                                    "hist": dict(Counter(v))} for c, v in by.items()}
    # determinism check: identical prefixes 1..k within a template -> identical states at k (fp16 max abs diff)
    det = {}
    for k in (1, 2, 3, 4, 8):
        pi = POS.index(f"k{k}")
        mx, npairs = 0.0, 0
        for w in np.unique(g):
            ix = np.where(g == w)[0]
            groups = defaultdict(list)
            for i in ix:
                groups[tuple(d["tok16"][i][:k])].append(i)
            for grp in groups.values():
                if len(grp) > 1:
                    a = d["X"][grp[0], pi].astype(np.float32)
                    for j in grp[1:]:
                        mx = max(mx, float(np.abs(d["X"][j, pi].astype(np.float32) - a).max()))
                        npairs += 1
        det[f"k{k}"] = {"max_abs_diff": mx, "n_pairs": npairs}
    res["determinism_check"] = det
    return res
