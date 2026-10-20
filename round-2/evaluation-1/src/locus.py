#!/usr/bin/env python3
"""(0a) Locus probe on exp3's saved generation-time residual states (Qwen3-8B, layers 8-28, 8 positions).

Leave-one-paraphrase-out L2 logistic probes (in-fold StandardScaler + PCA(64), C chosen by inner GroupKFold(3)
on pooled log-loss), fitted for every label vector of a cell in one batched Newton-IRLS solve in torch.
Nulls: 200 global + 200 within-paraphrase label shuffles on the within-ban contrast W (same permutation vectors
at every layer of a position, so a layer-max null is valid); 50 global shuffles for the positive controls.
Adds the written-text control, the text-locus curve, a pre-commit qualifier, difference-in-means AUCs, cosines,
the commit-aligned curve, the R-compliance preview and PCA views.

Usage: uv run locus.py [--smoke] [--unit-test-only] [--n-perm 200]
"""
from __future__ import annotations

import argparse
import gc
import itertools
import json
import math
import resource
import time
from collections import Counter, defaultdict

import numpy as np
import pandas as pd
from loguru import logger
from scipy import stats
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold

from common import (EXP, FIG, RES, TAB, auc, balanced_accuracy, boot_auc, boot_ba, clean, find_tokenizer, jdump,
                    pct_ci, read_jsonl, setup_logging, to_bool, wilson)

import torch

LAYERS = list(range(8, 29))
POS = ["R", "k8", "k16", "k32", "k64", "k_fork", "k_pre", "k_post"]
FIXED = ["R", "k8", "k16", "k32", "k64"]
CS = [0.01, 0.1, 1.0]
SUB = {"T1": "DFS", "T2": "bellman_ford_spfa"}
DEF = {"T1": "BFS", "T2": "dijkstra"}
TEXT_KS = list(range(1, 13)) + [16, 24, 32, 48, 64]
HAS_GPU = torch.cuda.is_available()
DEV = torch.device("cuda" if HAS_GPU else "cpu")
DT = torch.float32 if HAS_GPU else torch.float64
N_ITER = 30
EPS = 1e-3


# ============================================================================================ data
def load_task(task: str) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[dict]]:
    sd = EXP["exp3"] / "states"
    parts = sorted(sd.glob(f"{task}_part_*.npz"))
    Xs, Ms, Ks = [], [], []
    for p in parts:
        d = np.load(p)
        Xs.append(d["X"])
        Ms.append(d["mask"])
        Ks.append(d["ks"])
        del d
    X, mask, ks = np.concatenate(Xs), np.concatenate(Ms), np.concatenate(Ks)
    del Xs
    meta = json.loads((sd / f"{task}_meta.json").read_text())
    rows = meta["rows"]
    assert len(rows) == X.shape[0] == mask.shape[0] == ks.shape[0], "state/meta misalignment"
    assert meta["layers"] == LAYERS and meta["positions"] == POS
    assert X.shape[1:] == (8, 21, 4096), X.shape
    return X, mask, ks, rows


def contrast(rows: list[dict], task: str, name: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Row indices, labels (1 = substitute/ban) and paraphrase groups for a contrast."""
    idx, y = [], []
    for i, r in enumerate(rows):
        if name == "W" and r["arm"] == "G2" and r["label"] in (SUB[task], DEF[task]):
            idx.append(i)
            y.append(int(r["label"] == SUB[task]))
        elif name == "P1" and r["label"] == DEF[task] and r["arm"] in ("G1", "G2"):
            idx.append(i)
            y.append(int(r["arm"] == "G2"))
        elif name == "P2" and ((r["arm"] == "G1" and r["label"] == DEF[task]) or
                               (r["arm"] == "G2" and r["label"] == SUB[task])):
            idx.append(i)
            y.append(int(r["arm"] == "G2"))
    g = np.array([int(rows[i]["paraphrase_id"]) for i in idx])
    return np.array(idx), np.array(y), g


# ============================================================================================ folds
class Folds:
    """Leave-one-paraphrase-out outer folds, GroupKFold(3) inner folds, padded index tensors."""

    def __init__(self, groups: np.ndarray):
        self.groups = groups
        self.ug = np.unique(groups)
        self.F = len(self.ug)
        self.tr = [np.where(groups != g)[0] for g in self.ug]
        self.te = [np.where(groups == g)[0] for g in self.ug]
        self.Ntr = max(len(t) for t in self.tr)
        self.Nte = max(len(t) for t in self.te)
        M = np.zeros((self.F, 4, self.Ntr))
        for f, tr in enumerate(self.tr):
            M[f, 3, :len(tr)] = 1
            gkf = GroupKFold(n_splits=3)
            for j, (itr, _) in enumerate(gkf.split(tr, groups=groups[tr])):
                M[f, j, itr] = 1
        self.M = M
        self.tr_pad = np.full((self.F, self.Ntr), -1)
        self.te_pad = np.full((self.F, self.Nte), -1)
        for f in range(self.F):
            self.tr_pad[f, :len(self.tr[f])] = self.tr[f]
            self.te_pad[f, :len(self.te[f])] = self.te[f]


def fold_features(Xl: torch.Tensor, folds: Folds, n_comp: int = 64) -> tuple[torch.Tensor, torch.Tensor]:
    """In-fold StandardScaler + PCA(n_comp); returns padded train/test designs with intercept (last col)."""
    F = folds.F
    Ztr = torch.zeros((F, folds.Ntr, n_comp + 1), device=DEV, dtype=DT)
    Zte = torch.zeros((F, folds.Nte, n_comp + 1), device=DEV, dtype=DT)
    for f in range(F):
        tr = torch.as_tensor(folds.tr[f], device=DEV)
        te = torch.as_tensor(folds.te[f], device=DEV)
        A = Xl[tr]
        mu = A.mean(0)
        sd = A.std(0, unbiased=False)
        sd = torch.where(sd < 10 * torch.finfo(DT).eps, torch.ones_like(sd), sd)
        As = (A - mu) / sd
        _, _, Vh = torch.linalg.svd(As, full_matrices=False)
        k = min(n_comp, Vh.shape[0])
        V = Vh[:k]
        Ztr[f, :len(tr), :k] = As @ V.T
        Ztr[f, :len(tr), -1] = 1.0
        Zte[f, :len(te), :k] = ((Xl[te] - mu) / sd) @ V.T
        Zte[f, :len(te), -1] = 1.0
    return Ztr, Zte


# ============================================================================================ batched IRLS
def _objective(Z, beta, Yk, W, lamR):
    eta = torch.einsum("fnd,bfjkd->bfjkn", Z, beta)
    ll = (W * (torch.nn.functional.softplus(eta) - Yk * eta)).sum(-1)
    return ll + 0.5 * (lamR * beta * beta).sum(-1)


def irls(Z: torch.Tensor, Y: torch.Tensor, M: torch.Tensor, lam: torch.Tensor, n_iter: int = N_ITER) -> torch.Tensor:
    """L2 logistic (balanced class weights, unpenalised intercept) for every (label vector b, fold f, fit j, C k).

    Z (F,N,D) with intercept last; Y (B,F,N) in {0,1}; M (F,J,N) 0/1 fit membership; lam (K,) = 1/C.
    Minimises sum_n w_n logloss_n + lam/2 ||beta_slopes||^2, which has the same optimum as sklearn's
    C * sum w logloss + 1/2 ||w||^2. Newton steps with Jacobi-preconditioned Cholesky and step halving.
    """
    B, F, N = Y.shape
    J, K, D = M.shape[1], lam.shape[0], Z.shape[2]
    Mb = M.unsqueeze(0)
    Yb = Y.unsqueeze(2)
    ntot = Mb.sum(-1)
    n1 = (Mb * Yb).sum(-1)
    n0 = ntot - n1
    cw1 = ntot / (2 * n1.clamp(min=1))
    cw0 = ntot / (2 * n0.clamp(min=1))
    W = Mb * (Yb * cw1.unsqueeze(-1) + (1 - Yb) * cw0.unsqueeze(-1))  # B,F,J,N
    W = W.unsqueeze(3).expand(B, F, J, K, N)
    Yk = Yb.unsqueeze(3)  # B,F,1,1,N
    R = torch.ones(D, device=DEV, dtype=DT)
    R[-1] = 0.0
    lamR = lam[:, None] * R[None, :]  # K,D
    ridge = lamR + (1 - R)[None, :] * 1e-6
    beta = torch.zeros((B, F, J, K, D), device=DEV, dtype=DT)
    Zb = Z[None, :, None, None]  # 1,F,1,1,N,D
    obj = _objective(Z, beta, Yk, W, lamR)
    for _ in range(n_iter):
        eta = torch.einsum("fnd,bfjkd->bfjkn", Z, beta)
        p = torch.sigmoid(eta)
        g = torch.einsum("fnd,bfjkn->bfjkd", Z, W * (p - Yk)) + lamR * beta
        s = (W * p * (1 - p)).unsqueeze(-1)  # B,F,J,K,N,1
        H = (Zb * s).transpose(-1, -2) @ Zb  # B,F,J,K,D,D
        H = H + torch.diag_embed(ridge.expand(B, F, J, K, D))
        dg = torch.diagonal(H, dim1=-2, dim2=-1).clamp(min=1e-12).rsqrt()
        Hs = dg.unsqueeze(-1) * H * dg.unsqueeze(-2)
        L, info = torch.linalg.cholesky_ex(Hs)
        delta = dg * torch.cholesky_solve((dg * g).unsqueeze(-1), L).squeeze(-1)
        delta = torch.nan_to_num(delta)
        # backtracking: take the largest step that does not raise the objective beyond float noise, so full
        # Newton steps are accepted near the optimum (a strict '<' stalls once changes fall below float32 eps)
        tol = 1e-6 * obj.abs() + 1e-7
        new_beta, new_obj = beta, obj
        accepted = torch.zeros_like(obj, dtype=torch.bool)
        for t in (1.0, 0.5, 0.25, 0.125, 0.0625):
            cand = beta - t * delta
            o = _objective(Z, cand, Yk, W, lamR)
            ok = (~accepted) & (o <= obj + tol)
            new_beta = torch.where(ok.unsqueeze(-1), cand, new_beta)
            new_obj = torch.where(ok, o, new_obj)
            accepted = accepted | ok
        beta, obj = new_beta, new_obj
        del H, Hs, L, s, p, eta, g
    return beta


def fit_cell(Xl: torch.Tensor, Ylab: np.ndarray, folds: Folds, chunk: int = 100) -> dict:
    """Fit a cell for every label vector (rows of Ylab: B x n). Returns OOF probabilities and chosen C."""
    Ztr, Zte = fold_features(Xl, folds)
    M = torch.as_tensor(folds.M, device=DEV, dtype=DT)
    lam = torch.as_tensor([1.0 / c for c in CS], device=DEV, dtype=DT)
    B, n = Ylab.shape
    trp = torch.as_tensor(np.maximum(folds.tr_pad, 0), device=DEV)
    tep = torch.as_tensor(np.maximum(folds.te_pad, 0), device=DEV)
    trv = torch.as_tensor(folds.tr_pad >= 0, device=DEV, dtype=DT)
    tev = torch.as_tensor(folds.te_pad >= 0, device=DEV)
    P_oof = np.zeros((B, n))
    C_idx = np.zeros((B, folds.F), dtype=int)
    Yall = torch.as_tensor(Ylab, device=DEV, dtype=DT)
    for b0 in range(0, B, chunk):
        Yc = Yall[b0:b0 + chunk]
        Bc = Yc.shape[0]
        Ytr = Yc[:, trp] * trv  # Bc,F,Ntr
        beta = irls(Ztr, Ytr, M, lam)  # Bc,F,4,K,D
        eta = torch.einsum("fnd,bfjkd->bfjkn", Ztr, beta[:, :, :3])  # inner fits on all train rows
        p = torch.sigmoid(eta).clamp(1e-15, 1 - 1e-15)
        val = (M[:, 3:4] * (1 - M[:, :3]))  # F,3,N : inner validation membership
        ll = -(Ytr[:, :, None, None] * torch.log(p) + (1 - Ytr[:, :, None, None]) * torch.log(1 - p))
        inner = (ll * val[None, :, :, None, :]).sum((2, 4)) / M[None, :, 3].sum(-1)[..., None]  # Bc,F,K
        kstar = torch.argmin(inner, dim=-1)  # ties -> smallest C (first)
        bsel = torch.gather(beta[:, :, 3], 2, kstar[:, :, None, None].expand(Bc, folds.F, 1, beta.shape[-1]))[:, :, 0]
        pt = torch.sigmoid(torch.einsum("fnd,bfd->bfn", Zte, bsel))  # Bc,F,Nte
        pt_np = pt.cpu().numpy().astype(np.float64)
        tev_np = tev.cpu().numpy()
        for f in range(folds.F):
            cols = folds.te_pad[f][tev_np[f]]
            P_oof[b0:b0 + Bc, cols] = pt_np[:, f, tev_np[f]]
        C_idx[b0:b0 + Bc] = kstar.cpu().numpy()
        del beta, eta, p, ll, inner, Ytr, pt
    return {"P": P_oof, "C_idx": C_idx, "Ztr": Ztr, "Zte": Zte}


def ba_batch(Y: np.ndarray, P: np.ndarray, sub: np.ndarray | None = None) -> np.ndarray:
    """Balanced accuracy at 0.5 for each row of Y/P (B x n), optionally on a row subset."""
    if sub is not None:
        Y, P = Y[:, sub], P[:, sub]
    pred = P >= 0.5
    pos = Y == 1
    npos, nneg = pos.sum(1), (~pos).sum(1)
    with np.errstate(invalid="ignore", divide="ignore"):
        tpr = (pred & pos).sum(1) / npos
        tnr = (~pred & ~pos).sum(1) / nneg
    out = 0.5 * (tpr + tnr)
    out[(npos == 0) | (nneg == 0)] = np.nan
    return out


def ce_bits(y: np.ndarray, p: np.ndarray) -> float:
    p = np.clip(p, EPS, 1 - EPS)
    return float(-np.mean(y * np.log2(p) + (1 - y) * np.log2(1 - p)))


def base_rate_oof(y: np.ndarray, folds: Folds) -> np.ndarray:
    out = np.zeros(len(y))
    for f in range(folds.F):
        out[folds.te[f]] = y[folds.tr[f]].mean()
    return out


def make_perms(y: np.ndarray, g: np.ndarray, n: int, kind: str, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    out = np.zeros((n, len(y)), dtype=int)
    for b in range(n):
        if kind == "global":
            out[b] = rng.permutation(y)
        else:
            yy = y.copy()
            for gg in np.unique(g):
                ii = np.where(g == gg)[0]
                yy[ii] = rng.permutation(y[ii])
            out[b] = yy
    return out


# ============================================================================================ unit test
def unit_test(X: np.ndarray, rows: list[dict], task: str, n_cells: int = 5, seed: int = 0) -> dict:
    rng = np.random.default_rng(seed)
    idx, y, g = contrast(rows, task, "W")
    res = []
    for c in range(n_cells):
        pi = int(rng.integers(0, len(POS)))
        li = int(rng.integers(0, len(LAYERS)))
        f = int(rng.integers(0, 10))
        Xl = torch.as_tensor(X[idx, pi, li, :].astype(np.float32), device=DEV, dtype=DT)
        folds = Folds(g)
        Ztr, Zte = fold_features(Xl, folds)
        M = torch.as_tensor(folds.M, device=DEV, dtype=DT)
        lam = torch.as_tensor([1.0 / cc for cc in CS], device=DEV, dtype=DT)
        trp = np.maximum(folds.tr_pad, 0)
        Ytr = torch.as_tensor(y[None, trp] * (folds.tr_pad >= 0)[None], device=DEV, dtype=DT)
        beta = irls(Ztr, Ytr, M, lam).cpu().numpy().astype(np.float64)
        ntr, nte = len(folds.tr[f]), len(folds.te[f])
        Z = Ztr[f, :ntr, :-1].cpu().numpy().astype(np.float64)
        Zt = Zte[f, :nte, :-1].cpu().numpy().astype(np.float64)
        yt = y[folds.tr[f]]
        for k, C in enumerate(CS):
            sk = LogisticRegression(C=C, class_weight="balanced", solver="lbfgs", max_iter=2000, tol=1e-10).fit(Z, yt)
            ref = np.concatenate([sk.coef_[0], sk.intercept_])
            mine = beta[0, f, 3, k]
            rel = float(np.linalg.norm(mine - ref) / max(np.linalg.norm(ref), 1e-12))
            pm = (Zt @ mine[:-1] + mine[-1]) >= 0
            ps = sk.predict(Zt).astype(bool)
            # sklearn with its default tolerance (as written in the plan) for reference
            sk2 = LogisticRegression(C=C, class_weight="balanced", solver="lbfgs", max_iter=2000).fit(Z, yt)
            ref2 = np.concatenate([sk2.coef_[0], sk2.intercept_])
            rel2 = float(np.linalg.norm(mine - ref2) / max(np.linalg.norm(ref2), 1e-12))
            res.append({"task": task, "position": POS[pi], "layer": LAYERS[li], "fold": f, "C": C, "rel_coef_diff": rel,
                        "rel_coef_diff_vs_default_tol": rel2, "pred_identical": bool((pm == ps).all()),
                        "n_test": nte})
        del Xl, Ztr, Zte
    ok = all(r["rel_coef_diff"] < 1e-3 and r["pred_identical"] for r in res)
    return {"passed": bool(ok), "max_rel_coef_diff": max(r["rel_coef_diff"] for r in res), "checks": res}


# ============================================================================================ text control
_TEXT_CACHE: dict = {}


def text_design(pref_tr: list[list[int]], pref_te: list[list[int]]) -> tuple[np.ndarray, np.ndarray]:
    df = Counter()
    for p in pref_tr:
        df.update(set(p))
    vocab = sorted(t for t, c in df.items() if c >= 2)
    vi = {t: i for i, t in enumerate(vocab)}
    slots = []
    for s in (1, 2, 3):
        ids = sorted({p[-s] for p in pref_tr if len(p) >= s})
        slots.append({t: i for i, t in enumerate(ids)})
    width = len(vocab) + sum(len(s) for s in slots)

    def enc(ps):
        A = np.zeros((len(ps), max(width, 1)))
        for r, p in enumerate(ps):
            for t in set(p):
                if t in vi:
                    A[r, vi[t]] = 1
            off = len(vocab)
            for s, sl in zip((1, 2, 3), slots):
                if len(p) >= s and p[-s] in sl:
                    A[r, off + sl[p[-s]]] = 1
                off += len(sl)
        return A

    return enc(pref_tr), enc(pref_te)


def _lr_fit_predict(A: np.ndarray, y: np.ndarray, At: np.ndarray, C: float) -> np.ndarray:
    if len(np.unique(y)) < 2:
        return np.full(len(At), float(y.mean()))
    if A.shape[1] == 0 or not A.any():
        return np.full(len(At), 0.5)
    m = LogisticRegression(C=C, class_weight="balanced", solver="lbfgs", max_iter=2000).fit(A, y)
    return m.predict_proba(At)[:, 1]


def text_probe(prefixes: list[list[int]], y: np.ndarray, g: np.ndarray) -> dict:
    """Same LOPO logistic on the written prefix (binary bag of ids seen >= 2x in training + last-3 one-hots)."""
    folds = Folds(g)
    P = np.zeros(len(y))
    chosen = []
    for f in range(folds.F):
        tr, te = folds.tr[f], folds.te[f]
        ptr = [prefixes[i] for i in tr]
        pte = [prefixes[i] for i in te]
        A, At = text_design(ptr, pte)
        ytr = y[tr]
        best, bestC = None, CS[0]
        for C in CS:
            oof = np.zeros(len(tr))
            for j in range(3):
                itr = np.where(folds.M[f, j, :len(tr)] == 1)[0]
                iva = np.where(folds.M[f, j, :len(tr)] == 0)[0]
                oof[iva] = _lr_fit_predict(A[itr], ytr[itr], A[iva], C)
            pp = np.clip(oof, 1e-15, 1 - 1e-15)
            loss = float(-np.mean(ytr * np.log(pp) + (1 - ytr) * np.log(1 - pp)))
            if best is None or loss < best - 1e-12:
                best, bestC = loss, C
        chosen.append(bestC)
        P[te] = _lr_fit_predict(A, ytr, At, bestC)
    return {"P": P, "BA": balanced_accuracy(y, P >= 0.5), "AUC": auc(y, P), "C_chosen": dict(Counter(chosen))}


# ============================================================================================ main analysis
def spearman_exact(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    rx, ry = stats.rankdata(x), stats.rankdata(y)
    rho = float(stats.spearmanr(x, y).statistic)
    n = len(x)
    if n > 10 or not np.isfinite(rho):
        return rho, float("nan")
    rxc = rx - rx.mean()
    den = math.sqrt((rxc ** 2).sum() * ((ry - ry.mean()) ** 2).sum())
    cnt, tot = 0, 0
    perm_iter = itertools.permutations(ry - ry.mean())
    while True:
        blk = list(itertools.islice(perm_iter, 200000))
        if not blk:
            break
        A = np.asarray(blk)
        r = (A @ rxc) / den
        cnt += int((np.abs(r) >= abs(rho) - 1e-12).sum())
        tot += len(A)
    return rho, cnt / tot


def run(args: argparse.Namespace) -> None:
    t_start = time.time()
    tok = None
    tp = find_tokenizer()
    if tp is not None:
        from tokenizers import Tokenizer
        tok = Tokenizer.from_file(str(tp))
        logger.info("tokenizer loaded (Qwen3-8B tokenizer.json from the shared HF cache)")
    pools = read_jsonl(EXP["exp3"] / "generations" / "pools.jsonl")
    pool_key = defaultdict(list)
    for r in pools:
        pool_key[(r["task"], r["arm"], r["condition"], int(r["paraphrase_id"]), int(r["sample_id"]))].append(r)
    exp2_index = read_jsonl(EXP["exp2"] / "cache" / "hR_index.jsonl")
    out: dict = {"device": str(DEV), "dtype": str(DT), "tasks": {}, "unit_test": {}, "timing": {}}
    cells_rows = []
    n_perm = args.n_perm
    for task in ("T1", "T2"):
        t0 = time.time()
        X, mask, ks, rows = load_task(task)
        logger.info(f"{task}: states {X.shape} loaded in {time.time() - t0:.1f}s")
        T: dict = {}
        # ---------------- counts and commit_idx distribution
        cnt = Counter((r["arm"], r["condition"], r["label"]) for r in rows)
        T["counts"] = {f"{a}|{c}|{l}": v for (a, c, l), v in sorted(cnt.items())}
        cd = defaultdict(Counter)
        for r in rows:
            cd[f"{r['arm']}|{r['condition']}|{r['label']}"][r["commit_idx"]] += 1
        T["commit_idx_distribution"] = {k: {str(a): b for a, b in sorted(v.items(), key=lambda x: (x[0] is None, x[0] or 0))}
                                        for k, v in cd.items()}
        # ---------------- join to pools (one-to-one) for the text control
        joined, label_disagree = [], 0
        for r in rows:
            m = pool_key[(task, r["arm"], r["condition"], int(r["paraphrase_id"]), int(r["sample_id"]))]
            assert len(m) == 1, f"pool join not one-to-one for {r}"
            joined.append(m[0])
            if m[0]["label"] != r["label"]:
                label_disagree += 1
        gen_ids = [json.loads(j["gen_token_ids"]) if isinstance(j["gen_token_ids"], str) else j["gen_token_ids"]
                   for j in joined]
        T["pool_join"] = {"one_to_one": True, "n": len(joined), "meta_vs_pools_label_disagreements": label_disagree}
        commit = np.array([r["commit_idx"] if r["commit_idx"] is not None else -1 for r in rows])
        # ---------------- unit test (once per task) and smoke timing
        if not out["unit_test"].get(task):
            ut = unit_test(X, rows, task, n_cells=5, seed=1 if task == "T1" else 2)
            out["unit_test"][task] = ut
            logger.info(f"{task} unit test vs sklearn: passed={ut['passed']} max rel coef diff={ut['max_rel_coef_diff']:.2e}")
            if args.unit_test_only:
                continue
        Xg = torch.as_tensor(X, device=DEV, dtype=torch.float16) if HAS_GPU else None
        res_c: dict = {}
        for cname in ("W", "P1", "P2"):
            idx_all, y_all, g_all = contrast(rows, task, cname)
            nperm = n_perm if cname == "W" else args.n_perm_p
            C: dict = {"n_rows": int(len(idx_all)), "n_pos_class": int(y_all.sum()), "positions": {}}
            for pi, pname in enumerate(POS):
                if args.smoke and (cname != "W" or pname != "k_pre"):
                    continue
                keep = mask[idx_all, pi]
                idx, y, g = idx_all[keep], y_all[keep], g_all[keep]
                kpos = ks[idx, pi]
                if len(y) < 10 or len(np.unique(y)) < 2 or len(np.unique(g)) < 3:
                    C.setdefault("positions_unavailable", {})[pname] = {
                        "n_rows_with_state": int(len(y)), "classes": sorted(set(int(v) for v in y)),
                        "reason": "no saved state at this position for enough rows/classes (mask False in exp3 states)"}
                    logger.warning(f"{task} {cname} {pname}: unavailable (n={len(y)})")
                    continue
                folds = Folds(g)
                Ylab = [y[None]]
                Pg = make_perms(y, g, nperm, "global", seed=1000 + pi)
                Ylab.append(Pg)
                do_within = (cname == "W" and pname != "R")
                if do_within:
                    Pw = make_perms(y, g, nperm, "within", seed=2000 + pi)
                    Ylab.append(Pw)
                Ylab = np.concatenate(Ylab)
                pre = (kpos <= commit[idx]) & (commit[idx] >= 0)
                n_pre, pre_cls = int(pre.sum()), [int((y[pre] == 0).sum()), int((y[pre] == 1).sum())]
                lay: dict = {"BA": [], "AUC": [], "CE_bits": [], "IG_bits": [], "BA_ci": [], "C_chosen": [],
                             "p_global": [], "p_within": [], "BA_pre": [], "DiM_AUC": [], "DiM_AUC_ci": []}
                null_g, null_w, null_g_pre, null_w_pre = [], [], [], []
                P_obs = []
                base = base_rate_oof(y, folds)
                ce_base = ce_bits(y, base)
                t_pos = time.time()
                for li, L in enumerate(LAYERS):
                    if args.smoke and L not in (20,):
                        continue
                    tc = time.time()
                    if HAS_GPU:
                        Xl = Xg[torch.as_tensor(idx, device=DEV), pi, li].to(DT)
                    else:
                        Xl = torch.as_tensor(X[idx, pi, li].astype(np.float64))
                    fc = fit_cell(Xl, Ylab, folds)
                    P = fc["P"]
                    BAs = ba_batch(Ylab, P)
                    BApre = ba_batch(Ylab, P, pre) if n_pre > 0 else np.full(len(Ylab), np.nan)
                    obs = BAs[0]
                    ng = BAs[1:1 + nperm]
                    nw = BAs[1 + nperm:] if do_within else np.array([])
                    null_g.append(ng)
                    null_w.append(nw)
                    null_g_pre.append(BApre[1:1 + nperm])
                    null_w_pre.append(BApre[1 + nperm:] if do_within else np.array([]))
                    p0 = P[0]
                    P_obs.append(p0)
                    lay["BA"].append(obs)
                    lay["AUC"].append(auc(y, p0))
                    ce = ce_bits(y, p0)
                    lay["CE_bits"].append(ce)
                    lay["IG_bits"].append(ce_base - ce)
                    lay["BA_ci"].append(pct_ci(boot_ba(y, p0 >= 0.5, g, 1000, seed=li)))
                    lay["C_chosen"].append({str(CS[k]): int(v) for k, v in Counter(fc["C_idx"][0]).items()})
                    lay["p_global"].append(float((1 + (ng >= obs - 1e-12).sum()) / (1 + len(ng))))
                    lay["p_within"].append(float((1 + (nw >= obs - 1e-12).sum()) / (1 + len(nw))) if do_within else 1.0)
                    lay["BA_pre"].append(BApre[0])
                    # difference in means (raw residual space), LOPO
                    if cname == "W":
                        s = np.zeros(len(y))
                        for f in range(folds.F):
                            tr = torch.as_tensor(folds.tr[f], device=DEV)
                            te = torch.as_tensor(folds.te[f], device=DEV)
                            ytr = torch.as_tensor(y[folds.tr[f]], device=DEV)
                            A = Xl[tr].double()
                            mu1, mu0 = A[ytr == 1].mean(0), A[ytr == 0].mean(0)
                            d = mu1 - mu0
                            s[folds.te[f]] = ((Xl[te].double() - (mu1 + mu0) / 2) @ d).cpu().numpy()
                        lay["DiM_AUC"].append(auc(y, s))
                        lay["DiM_AUC_ci"].append(pct_ci(boot_auc(y, s, g, 1000, seed=li)))
                    if args.smoke:
                        el = time.time() - tc
                        logger.info(f"SMOKE {task} {cname} {pname} L{L}: {len(Ylab)} label vectors x 10 folds x 4 fits x 3 C "
                                    f"in {el:.2f}s; BA={obs:.3f}")
                        out["timing"]["smoke_cell_s"] = el
                        out["timing"]["smoke_n_label_vectors"] = int(len(Ylab))
                    del Xl, fc
                if args.smoke:
                    continue
                null_g = np.stack(null_g)  # L x nperm
                null_w = np.stack(null_w) if do_within else None
                null_g_pre = np.stack(null_g_pre)
                null_w_pre = np.stack(null_w_pre) if do_within else None
                BA = np.array(lay["BA"])
                lmax_obs = float(np.nanmax(BA))
                Lstar_i = int(np.nanargmax(BA))
                ng_max = np.nanmax(null_g, axis=0)
                pos_res = {"n": int(len(y)), "n_min": int(min(y.sum(), len(y) - y.sum())), "n_pos": int(y.sum()),
                           "median_k": float(np.median(kpos)), "k_values": dict(Counter(int(k) for k in kpos)),
                           "layers": LAYERS, **{k: v for k, v in lay.items()},
                           "L_star": LAYERS[Lstar_i], "layer_max_BA": lmax_obs,
                           "layer_max_null_global_p95": float(np.percentile(ng_max, 95)),
                           "p_layermax_global": float((1 + (ng_max >= lmax_obs - 1e-12).sum()) / (1 + len(ng_max))),
                           "n_precommit": n_pre, "precommit_class_counts": pre_cls,
                           "null_global_mean_BA": float(np.nanmean(null_g)),
                           "fit_seconds": time.time() - t_pos}
                if do_within:
                    nw_max = np.nanmax(null_w, axis=0)
                    pos_res["layer_max_null_within_p95"] = float(np.percentile(nw_max, 95))
                    pos_res["p_layermax_within"] = float((1 + (nw_max >= lmax_obs - 1e-12).sum()) / (1 + len(nw_max)))
                    pos_res["null_within_mean_BA"] = float(np.nanmean(null_w))
                else:
                    pos_res["layer_max_null_within_p95"] = None
                    pos_res["p_layermax_within"] = 1.0 if pname == "R" and cname == "W" else None
                    pos_res["within_note"] = ("degenerate at R by construction (R states identical within a paraphrase, "
                                              "R cos min 0.9997); p = 1 recorded, not computed") if pname == "R" else \
                        "within-paraphrase null not run for positive controls (plan: 50 global shuffles)"
                # pre-commit subset layer-max (fixed offsets; k_pre is pre-commit by definition)
                BApre_arr = np.array(lay["BA_pre"], dtype=float)
                if n_pre > 0 and np.isfinite(BApre_arr).any():
                    lm_pre = float(np.nanmax(BApre_arr))
                    pos_res["precommit_layer_max_BA"] = lm_pre
                    pos_res["precommit_L_star"] = LAYERS[int(np.nanargmax(BApre_arr))]
                    gm = np.nanmax(null_g_pre, axis=0)
                    pos_res["precommit_null_global_p95"] = float(np.nanpercentile(gm, 95))
                    if do_within:
                        wm = np.nanmax(null_w_pre, axis=0)
                        pos_res["precommit_null_within_p95"] = float(np.nanpercentile(wm, 95))
                else:
                    pos_res["precommit_layer_max_BA"] = None
                pos_res["_P_obs"] = np.stack(P_obs)
                pos_res["_idx"] = idx
                pos_res["_y"] = y
                pos_res["_g"] = g
                pos_res["_k"] = kpos
                C["positions"][pname] = pos_res
                logger.info(f"{task} {cname} {pname}: n={len(y)} L*={LAYERS[Lstar_i]} BA*={lmax_obs:.3f} "
                            f"p_glob={pos_res['p_layermax_global']:.3f} p_with={pos_res.get('p_layermax_within')} "
                            f"pre n={n_pre} ({time.time() - t_pos:.0f}s)")
                gc.collect()
                if HAS_GPU:
                    torch.cuda.empty_cache()
            res_c[cname] = C
        if args.smoke:
            out["tasks"][task] = {"smoke": True}
            del Xg
            break
        # ---------------- text control + text-locus curve (contrast W)
        W = res_c["W"]
        idxW, yW, gW = contrast(rows, task, "W")
        text: dict = {"per_position": {}, "curve": {}}
        for pname, pr in W["positions"].items():
            pref = [gen_ids[i][:int(k)] for i, k in zip(pr["_idx"], pr["_k"])]
            if all(len(p) == 0 for p in pref):
                text["per_position"][pname] = {"BA_text": 0.5, "note": "empty written prefix at k=0"}
                continue
            tpres = text_probe(pref, pr["_y"], pr["_g"])
            text["per_position"][pname] = {"BA_text": tpres["BA"], "AUC_text": tpres["AUC"], "C_chosen": tpres["C_chosen"],
                                           "BA_text_ci": pct_ci(boot_ba(pr["_y"], tpres["P"] >= 0.5, pr["_g"], 1000))}
        first_k = None
        for k in TEXT_KS:
            pref = [gen_ids[i][:k] for i in idxW]
            tpres = text_probe(pref, yW, gW)
            text["curve"][str(k)] = {"BA_text": tpres["BA"], "AUC_text": tpres["AUC"],
                                     "BA_text_ci": pct_ci(boot_ba(yW, tpres["P"] >= 0.5, gW, 1000))}
            if first_k is None and tpres["BA"] >= 0.8:
                first_k = k
        text["first_k_BA_text_ge_0.8"] = first_k
        # decoded prefixes up to commit_idx per class
        if tok is not None:
            pref_counts = {}
            for cls, lab in ((1, SUB[task]), (0, DEF[task])):
                c = Counter()
                ct = Counter()
                for i in idxW:
                    if rows[i]["label"] != lab:
                        continue
                    ci = rows[i]["commit_idx"]
                    c[tok.decode(gen_ids[i][:ci])] += 1
                    ct[tok.decode(gen_ids[i][ci:ci + 1])] += 1
                pref_counts[lab] = {"top5_prefix_before_commit": c.most_common(5), "top5_commit_token": ct.most_common(5)}
            text["decoded_prefixes"] = pref_counts
            # token-by-token decode of the most common prefix per class (for the extraction target)
            text["token_strings_first12"] = {}
            for lab in (SUB[task], DEF[task]):
                ex = next(i for i in idxW if rows[i]["label"] == lab)
                text["token_strings_first12"][lab] = [tok.decode([t]) for t in gen_ids[ex][:12]]
        T["text"] = text
        # ---------------- mechanical 20-point rule + qualified verdicts
        Rres = W["positions"]["R"]
        cands = [p for p in POS if p != "R" and p in W["positions"]]
        order = sorted(cands, key=lambda p: (W["positions"][p]["median_k"], 0 if p in FIXED else 1, POS.index(p)))
        rule = []
        locus = None
        for p in order:
            pr = W["positions"][p]
            Ls = pr["L_star"]
            li = LAYERS.index(Ls)
            ba_pos = pr["BA"][li]
            ba_R = Rres["BA"][li]
            thr_g = pr["layer_max_null_global_p95"]
            thr_w = pr["layer_max_null_within_p95"]
            passes = (ba_pos - ba_R >= 0.20) and (pr["layer_max_BA"] > thr_g) and (thr_w is not None and pr["layer_max_BA"] > thr_w)
            # paired difference on common rows with cluster bootstrap
            common = np.intersect1d(pr["_idx"], Rres["_idx"])
            ip = np.searchsorted(pr["_idx"], common)
            ir = np.searchsorted(Rres["_idx"], common)
            yy = pr["_y"][ip]
            gg = pr["_g"][ip]
            pp = pr["_P_obs"][li][ip] >= 0.5
            pR = Rres["_P_obs"][li][ir] >= 0.5
            bdiff = boot_ba(yy, pp, gg, 1000, seed=7) - boot_ba(yy, pR, gg, 1000, seed=7)
            d_obs = balanced_accuracy(yy, pp) - balanced_accuracy(yy, pR)
            # pre-commit qualifier
            pre_ok = False
            pre_detail = {"n_precommit": pr["n_precommit"], "class_counts": pr["precommit_class_counts"]}
            if p == "k_pre":
                pre_ok = passes
                pre_detail["note"] = "k_pre is pre-commit by definition (state predicts the commit token)"
            elif p == "k_post":
                pre_ok = False
                pre_detail["note"] = "k_post is post-commit by definition"
            elif pr["n_precommit"] >= 20 and min(pr["precommit_class_counts"]) > 0 and pr["precommit_layer_max_BA"] is not None:
                Lp = pr["precommit_L_star"]
                lpi = LAYERS.index(Lp)
                prei = (pr["_k"] <= commit[pr["_idx"]])
                ipre = np.searchsorted(Rres["_idx"], pr["_idx"][prei])
                baR_pre = balanced_accuracy(pr["_y"][prei], Rres["_P_obs"][lpi][ipre] >= 0.5)
                pre_detail.update({"BA_pre": pr["precommit_layer_max_BA"], "L_star_pre": Lp, "BA_R_same_rows": baR_pre,
                                   "null_global_p95": pr.get("precommit_null_global_p95"),
                                   "null_within_p95": pr.get("precommit_null_within_p95")})
                pre_ok = (pr["precommit_layer_max_BA"] - baR_pre >= 0.20 and
                          pr["precommit_layer_max_BA"] > pr.get("precommit_null_global_p95", 1) and
                          pr["precommit_layer_max_BA"] > (pr.get("precommit_null_within_p95") or 1))
            else:
                pre_detail["note"] = "pre-commit subset below n=20 or single-class: cannot pass"
            ba_text = text["per_position"].get(p, {}).get("BA_text", float("nan"))
            text_ok = (ba_pos - ba_text) >= 0.10 if np.isfinite(ba_text) else False
            rule.append({"position": p, "median_k": pr["median_k"], "L_star": Ls, "BA": ba_pos, "BA_R_at_L_star": ba_R,
                         "delta_vs_R": ba_pos - ba_R, "delta_vs_R_paired_common_rows": d_obs,
                         "delta_vs_R_ci": pct_ci(bdiff), "layer_max_BA": pr["layer_max_BA"],
                         "null_global_p95": thr_g, "null_within_p95": thr_w,
                         "p_layermax_global": pr["p_layermax_global"], "p_layermax_within": pr["p_layermax_within"],
                         "passes_mechanical": bool(passes), "precommit": pre_detail, "precommit_pass": bool(pre_ok),
                         "BA_text": ba_text, "BA_minus_text": ba_pos - ba_text if np.isfinite(ba_text) else None,
                         "text_margin_ok": bool(text_ok),
                         "qualified": ("DECISION LOCUS" if (passes and pre_ok and text_ok) else
                                       ("POST-COMMIT READOUT" if passes else "NOT PASSING"))})
            if passes and locus is None:
                locus = p
        mech = locus if locus is not None else "R"
        qual = next((r["qualified"] for r in rule if r["position"] == mech), "R (no position passed)")
        any_decision = [r["position"] for r in rule if r["qualified"] == "DECISION LOCUS"]
        T["rule"] = {"position_order": order, "trace": rule, "mechanical_locus": mech,
                     "qualified_verdict": qual if locus is not None else "R (no candidate passed the 20-point rule)",
                     "decision_locus_positions": any_decision,
                     "power_note": (f"W has n={W['positions']['R']['n']} rows with {W['positions']['R']['n_min']} in the minority class over 10 "
                                    "paraphrase clusters; the standard error of BA is about 0.05-0.08, so only effects of roughly 15-20 BA "
                                    "points are detectable and a null is weak evidence."),
                     "use_for_next_round": ("Representation of the implemented algorithm (5b manifold plots, 5c SAE readout) may use the "
                                            "mechanical locus as a post-commit readout; claims about where the choice is made need a "
                                            "DECISION LOCUS" + (f" (found: {any_decision})" if any_decision else
                                                                 " (none found; extract unsaved states at the text-locus index)"))}
        # ---------------- DiM at locus/R/k_pre/k8 + cosines
        Xr_np = X[:, 0]  # R states all rows, (300, 21, 4096)
        g1 = np.array([r["arm"] == "G1" for r in rows])
        g2 = np.array([r["arm"] == "G2" for r in rows])
        sub2, def2 = ("dfs", "bfs") if task == "T1" else ("bellman_ford_spfa", "dijkstra")
        t2k = task.lower()
        rng = np.random.default_rng(11)
        rand = rng.standard_normal((1000, 4096))
        rand /= np.linalg.norm(rand, axis=1, keepdims=True)
        dim: dict = {}
        for p in sorted(set([mech, "R", "k_pre", "k8"])):
            pr = W["positions"][p]
            li = LAYERS.index(pr["L_star"])
            ent = {"L_star": pr["L_star"], "DiM_AUC_at_L_star": pr["DiM_AUC"][li], "DiM_AUC_ci": pr["DiM_AUC_ci"][li],
                   "DiM_AUC_max_over_layers": float(np.nanmax(pr["DiM_AUC"])),
                   "DiM_AUC_argmax_layer": LAYERS[int(np.nanargmax(pr["DiM_AUC"]))],
                   "reopening_bar_auc_0.9_met_at_L_star": bool(pr["DiM_AUC"][li] >= 0.9), "cosines": {}}
            for L in sorted(set([pr["L_star"], 24])):
                lj = LAYERS.index(L)
                Xd = X[pr["_idx"], POS.index(p), lj].astype(np.float64)
                d = Xd[pr["_y"] == 1].mean(0) - Xd[pr["_y"] == 0].mean(0)
                rshift = Xr_np[g2, lj].astype(np.float64).mean(0) - Xr_np[g1, lj].astype(np.float64).mean(0)
                hp = EXP["exp2"] / "cache" / f"hR_layer{L}.npy"
                if not hp.exists():  # exp2 kept layers 8-20 on its run volume only
                    ent["cosines"][f"L{L}"] = {"status": "input_missing", "file": f"exp2/cache/hR_layer{L}.npy"}
                    continue
                H = np.load(hp, mmap_mode="r")
                isub = [i for i, r in enumerate(exp2_index) if r["task"] == t2k and r["condition"] == f"forced:{sub2}"]
                idef = [i for i, r in enumerate(exp2_index) if r["task"] == t2k and r["condition"] == f"forced:{def2}"]
                cdiff = np.asarray(H[isub], dtype=np.float64).mean(0) - np.asarray(H[idef], dtype=np.float64).mean(0)
                dn = d / np.linalg.norm(d)
                cc = {}
                for nm, ref in (("R_ban_shift_exp3", rshift), ("forced_centroid_diff_exp2", cdiff)):
                    rn = ref / np.linalg.norm(ref)
                    cobs = float(dn @ rn)
                    crand = rand @ rn
                    cc[nm] = {"cos": cobs, "random_abs_p95": float(np.percentile(np.abs(crand), 95)),
                              "random_abs_p99": float(np.percentile(np.abs(crand), 99)),
                              "p_vs_random": float((1 + (np.abs(crand) >= abs(cobs)).sum()) / 1001)}
                cc["R_shift_vs_forced_centroid_diff"] = float((rshift / np.linalg.norm(rshift)) @ (cdiff / np.linalg.norm(cdiff)))
                ent["cosines"][f"L{L}"] = cc
            dim[p] = ent
        T["dim"] = dim
        T["layer_convention"] = ("exp3 hooks model.model.layers[l] output (= output of decoder block l); exp2 stores "
                                 "hidden_states[l+1] (= output of decoder block l, exp2/common.py CACHE_LAYERS comment): "
                                 "same index convention, no offset applied")
        # ---------------- commit-aligned curve
        bins = [(-10 ** 9, -33, "<=-33"), (-32, -9, "-32..-9"), (-8, -1, "-8..-1"), (0, 0, "0"), (1, 1, "+1"),
                (2, 8, "+2..+8"), (9, 32, "+9..+32"), (33, 10 ** 9, ">=+33")]
        recs = []
        for p in FIXED + ["k_pre", "k_post"]:
            pr = W["positions"][p]
            li = LAYERS.index(pr["L_star"])
            corr = (pr["_P_obs"][li] >= 0.5).astype(int) == pr["_y"]
            off = pr["_k"] - commit[pr["_idx"]]
            for o, c_, yy in zip(off, corr, pr["_y"]):
                recs.append((p, int(o), int(c_), int(yy)))
        curve = []
        for lo, hi, nm in bins:
            sel = [r for r in recs if lo <= r[1] <= hi]
            k = sum(r[2] for r in sel)
            n = len(sel)
            ci = wilson(k, n) if n else (float("nan"), float("nan"))
            byp = Counter(r[0] for r in sel)
            ycls = Counter(r[3] for r in sel)
            curve.append({"bin": nm, "n": n, "correct": k, "acc": k / n if n else None, "ci": list(ci),
                          "by_position": dict(byp), "class_counts": {"default": ycls.get(0, 0), "substitute": ycls.get(1, 0)}})
        T["commit_aligned_curve"] = curve
        # ---------------- R-compliance preview
        li = LAYERS.index(Rres["L_star"])
        pR = Rres["_P_obs"][li]
        gs = np.unique(Rres["_g"])
        mp = np.array([pR[Rres["_g"] == gg].mean() for gg in gs])
        sh = np.array([Rres["_y"][Rres["_g"] == gg].mean() for gg in gs])
        rho, pex = spearman_exact(mp, sh)
        T["R_compliance_preview"] = {"layer": Rres["L_star"], "paraphrases": gs.tolist(), "heldout_P_substitute": mp.tolist(),
                                     "realised_substitute_share": sh.tolist(), "spearman_rho": rho, "exact_perm_p": pex}
        # ---------------- PCA views (all 300 rows)
        views = {}
        tags = [f"{r['condition']}:{r['label']}" for r in rows]
        for pi, p in enumerate(POS):
            if p not in W["positions"]:
                continue
            pr = W["positions"][p]
            for L in sorted(set([pr["L_star"], 24])):
                lj = LAYERS.index(L)
                keep = mask[:, pi]
                A = X[keep, pi, lj].astype(np.float64)
                A = A - A.mean(0)
                U, S, Vt = np.linalg.svd(A, full_matrices=False)
                ev = (S ** 2) / (S ** 2).sum()
                Zc = A @ Vt[:2].T
                views[f"{p}|L{L}"] = {"position": p, "layer": L, "explained": ev[:2].tolist(),
                                      "x": Zc[:, 0].round(3).tolist(), "y": Zc[:, 1].round(3).tolist(),
                                      "tag": [t for t, kk in zip(tags, keep) if kk]}
        T["pca_views"] = views
        # ---------------- cells table rows + strip private arrays
        for cname, Cr in res_c.items():
            for p, pr in Cr["positions"].items():
                bt = text["per_position"].get(p, {}).get("BA_text") if cname == "W" else None
                for li, L in enumerate(LAYERS):
                    cells_rows.append({"task": task, "contrast": cname, "position": p, "layer": L, "n": pr["n"],
                                       "n_min": pr["n_min"], "BA": pr["BA"][li], "CI_lo": pr["BA_ci"][li][0],
                                       "CI_hi": pr["BA_ci"][li][1], "AUC": pr["AUC"][li], "CE_bits": pr["CE_bits"][li],
                                       "IG": pr["IG_bits"][li], "p_global": pr["p_global"][li],
                                       "p_within": pr["p_within"][li] if cname == "W" else None, "BA_text": bt,
                                       "BA_precommit": pr["BA_pre"][li], "n_precommit": pr["n_precommit"],
                                       "C_chosen": json.dumps(pr["C_chosen"][li]),
                                       "DiM_AUC": pr["DiM_AUC"][li] if cname == "W" else None})
                for k in [k for k in pr if k.startswith("_")]:
                    pr.pop(k)
        T["contrasts"] = res_c
        out["tasks"][task] = T
        del X, Xg
        gc.collect()
        if HAS_GPU:
            torch.cuda.empty_cache()
        logger.info(f"{task} done in {time.time() - t0:.0f}s")
    out["timing"]["total_s"] = time.time() - t_start
    # failure record
    pj = EXP["exp3"] / "probes.json"
    st = pj.stat()
    out["failure_cause"] = (f"exp3/probes.json is {st.st_size} bytes with an empty summary and cells (mtime "
                            f"{pd.Timestamp(st.st_mtime, unit='s', tz='UTC').isoformat()}); exp3/logs/states.out shows "
                            "'phase states start' at 18:31:55 and the T1/T2 states saved at 18:34:34 and 18:34:50, so the "
                            "probe stage ran before its inputs existed (it found an empty states folder).")
    if args.smoke or args.unit_test_only:
        jdump(clean(out), RES / ("locus_smoke.json" if args.smoke else "locus_unittest.json"))
        return
    jdump(clean(out), RES / "locus.json")
    pd.DataFrame(cells_rows).to_csv(TAB / "locus_cells.csv", index=False)
    logger.info(f"wrote results/locus.json and tables/locus_cells.csv ({len(cells_rows)} cells)")


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--unit-test-only", action="store_true")
    ap.add_argument("--n-perm", type=int, default=200)
    ap.add_argument("--n-perm-p", type=int, default=50)
    args = ap.parse_args()
    setup_logging("locus" + ("_smoke" if args.smoke else ""))
    resource.setrlimit(resource.RLIMIT_AS, (120 * 1024 ** 3, 120 * 1024 ** 3))
    if HAS_GPU:
        torch.cuda.set_per_process_memory_fraction(0.85)
    logger.info(f"device={DEV} dtype={DT}")
    run(args)


if __name__ == "__main__":
    main()
