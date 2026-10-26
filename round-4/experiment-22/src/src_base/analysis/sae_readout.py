#!/usr/bin/env python3
"""9.5 5a (descriptive): Qwen-Scope SAE latents vs difference-in-means (DiM) on the raw state, on identical folds.

(A) PROHIBITION-PRESENT: ban vs neutral twin at the task-spec mean (S-mean) -- folds stratified by template x class.
(B) DEFAULT-PLAN: within the named ban, default vs any other attempted mechanism at k = 1, 2, 3 (C2e folds).
Readouts: top-1 latent ranked by fold-internal AUC (threshold chosen on the training fold), top-20 latents (L2
logistic, C = 1, balanced), DiM on the raw block-L state (midpoint threshold). Pooled out-of-fold BA and AUC with
sample-bootstrap CIs."""

from __future__ import annotations

import json
from typing import Any

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold

import states_io
from cfg import DATA_DIR, DEFAULT, SAMPLED_TASKS, STATES_DIR, read_jsonl

LAYERS = [15, 20, 27]
NOT_ATT = ("invalid", "disputed")


def _dense(idx: np.ndarray, val: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    lat = np.unique(idx)
    pos = {l: i for i, l in enumerate(lat)}
    X = np.zeros((idx.shape[0], len(lat)), np.float32)
    for r in range(idx.shape[0]):
        for j in range(idx.shape[1]):
            if val[r, j] > 0:
                X[r, pos[idx[r, j]]] = float(val[r, j])
    return X, lat


def _ba(y: np.ndarray, p: np.ndarray) -> float:
    return 0.5 * (float((p[y == 1] == 1).mean()) + float((p[y == 0] == 0).mean()))


def _auc_cols(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Per-column AUC via ranks (ties averaged)."""
    from scipy.stats import rankdata

    n1, n0 = int(y.sum()), int((1 - y).sum())
    R = np.apply_along_axis(rankdata, 0, X)
    return (R[y == 1].sum(0) - n1 * (n1 + 1) / 2) / max(n1 * n0, 1)


def evaluate(XL: np.ndarray, XR: np.ndarray, y: np.ndarray, strata: np.ndarray, seed: int = 0) -> dict[str, Any]:
    st = strata if min(np.unique(strata, return_counts=True)[1]) >= 5 else y
    skf = StratifiedKFold(5, shuffle=True, random_state=seed)
    pred = {k: np.zeros(len(y), int) for k in ("top1", "top20", "dim")}
    score = {k: np.zeros(len(y)) for k in ("top1", "top20", "dim")}
    top_lat = []
    for tr, te in skf.split(np.zeros(len(y)), st):
        a = _auc_cols(XL[tr], y[tr])
        strength = np.abs(a - 0.5)
        order = np.argsort(-strength)
        j = order[0]
        sgn = 1 if a[j] >= 0.5 else -1
        top_lat.append(int(j))
        s_tr, s_te = sgn * XL[tr, j], sgn * XL[te, j]
        ths = np.unique(s_tr)
        bt = max(ths, key=lambda t: _ba(y[tr], (s_tr >= t).astype(int)))
        pred["top1"][te] = (s_te >= bt).astype(int)
        score["top1"][te] = s_te
        cols = order[:20]
        lr = LogisticRegression(C=1.0, class_weight="balanced", max_iter=2000)
        lr.fit(XL[tr][:, cols], y[tr])
        score["top20"][te] = lr.decision_function(XL[te][:, cols])
        pred["top20"][te] = (score["top20"][te] > 0).astype(int)
        mu1, mu0 = XR[tr][y[tr] == 1].mean(0), XR[tr][y[tr] == 0].mean(0)
        w = mu1 - mu0
        thr = 0.5 * ((mu1 @ w) + (mu0 @ w))
        score["dim"][te] = XR[te] @ w - thr
        pred["dim"][te] = (score["dim"][te] > 0).astype(int)
    out: dict[str, Any] = {}
    rng = np.random.default_rng(seed)
    B = [rng.integers(0, len(y), len(y)) for _ in range(1000)]
    for k in pred:
        ba = _ba(y, pred[k])
        auc = float(roc_auc_score(y, score[k]))
        bb = [(_ba(y[i], pred[k][i]), roc_auc_score(y[i], score[k][i])) for i in B if len(set(y[i])) == 2]
        out[k] = {"ba": ba, "auc": auc, "ba_ci95": [float(np.quantile([x[0] for x in bb], 0.025)),
                                                     float(np.quantile([x[0] for x in bb], 0.975))],
                  "auc_ci95": [float(np.quantile([x[1] for x in bb], 0.025)), float(np.quantile([x[1] for x in bb], 0.975))]}
    out["latent_beats_dim_beyond_ci"] = bool(max(out["top1"]["ba"], out["top20"]["ba"]) > out["dim"]["ba_ci95"][1])
    out["top1_latent_cols_by_fold"] = top_lat
    return out


def run_sae_readout() -> dict[str, Any]:
    labs = {r["key"]: r["label"] for r in read_jsonl(DATA_DIR / "labels.jsonl")}
    res: dict[str, Any] = {}
    for t in SAMPLED_TASKS:
        pb, pn = STATES_DIR / f"sae_codes_{t}_BAN.npz", STATES_DIR / f"sae_codes_{t}_NEUTRAL.npz"
        if not (pb.exists() and pn.exists()):
            continue
        cb, cn = np.load(pb), np.load(pn)
        ib = [json.loads(l) for l in open(STATES_DIR / f"{t}_BAN_index.jsonl")]
        inn = [json.loads(l) for l in open(STATES_DIR / f"{t}_NEUTRAL_index.jsonl")]
        Xb = states_io.load(STATES_DIR / f"{t}_BAN")
        Xn = states_io.load(STATES_DIR / f"{t}_NEUTRAL")
        blocks = json.load(open(STATES_DIR / f"{t}_BAN_meta.json"))["blocks"]
        rt: dict[str, Any] = {}
        for L in LAYERS:
            bi = blocks.index(L)
            # (A) prohibition-present at S-mean (position 0 in both the codes and the states)
            idx = np.concatenate([cb[f"idx_L{L}"][:, 0], cn[f"idx_L{L}"][:, 0]])
            val = np.concatenate([cb[f"val_L{L}"][:, 0], cn[f"val_L{L}"][:, 0]]).astype(np.float32)
            XL, lat = _dense(idx, val)
            XR = np.concatenate([np.asarray(Xb[:, 0, bi]), np.asarray(Xn[:, 0, bi])]).astype(np.float32)
            y = np.array([1] * len(ib) + [0] * len(inn))
            g = np.array([r["template"] for r in ib] + [r["template"] for r in inn])
            A = evaluate(XL, XR, y, np.array([f"{a}|{b}" for a, b in zip(g, y)]))
            A["note"] = "S-mean is a prompt-only state: constant within (template, condition)"
            rt[f"L{L}_prohibition_present"] = A
            # (B) default-plan within the ban at k = 1, 2, 3
            lab = [labs.get(r["key"]) for r in ib]
            keep = np.array([l is not None and l not in NOT_ATT for l in lab])
            yb = np.array([int(l == DEFAULT[t]) for l, k in zip(lab, keep) if k])
            if yb.sum() < 8 or (1 - yb).sum() < 8:
                rt[f"L{L}_default_plan"] = {"status": "not testable (< 8 per class)"}
                continue
            gb = np.array([r["template"] for r, k in zip(ib, keep) if k])
            for pi, pname in ((1, "k1"), (2, "k2"), (3, "k3")):
                XLb, _ = _dense(cb[f"idx_L{L}"][keep, pi], cb[f"val_L{L}"][keep, pi].astype(np.float32))
                XRb = np.asarray(Xb[:, 1 + pi, bi])[keep].astype(np.float32)  # states positions: Smean, R, k1..
                rt[f"L{L}_default_plan_{pname}"] = evaluate(XLb, XRb, yb, np.array([f"{a}|{b}" for a, b in zip(gb, yb)]))
        res[t] = rt
    return {"per_task": res, "descriptive": True,
            "note": "DiM is the benchmark every SAE readout must beat (AxBench); states are FP8-model block outputs"}
