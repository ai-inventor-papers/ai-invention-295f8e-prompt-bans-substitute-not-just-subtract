#!/usr/bin/env python3
"""Claim-S analyses (CPU): natural splits, engine check, within-prompt decodability (S6a), the cross-prompt plan
readout (S6b), contrast separability (S6c), clamp tests (S8), logit-sweep summary, TOP5 landing (S11).
Every function reads raw rows / cached states and writes one results/*.json; figures are made in figures_S.py."""

from __future__ import annotations

import itertools
import math
from collections import Counter
from typing import Any

import numpy as np
from loguru import logger
from scipy import stats

from cfg import (DATA_DIR, N_PERM, RESULTS_DIR, STATES_DIR, TEMPLATE_IDS, read_json, read_jsonl, stable_seed,
                 wilson_ci, write_json)

NC = ("invalid", "disputed")


# ------------------------------------------------------------------------------------------------ stats helpers
def mcnemar_exact(a: list[int], b: list[int]) -> dict[str, Any]:
    n10 = sum(1 for x, y in zip(a, b) if x == 1 and y == 0)
    n01 = sum(1 for x, y in zip(a, b) if x == 0 and y == 1)
    n = n10 + n01
    p = 1.0 if n == 0 else min(1.0, 2 * stats.binom.cdf(min(n10, n01), n, 0.5))
    return {"a_only": n10, "b_only": n01, "discordant": n, "p": float(p)}


def holm(ps: dict[str, float]) -> dict[str, float]:
    items = sorted(ps.items(), key=lambda kv: kv[1])
    m = len(items)
    out, run = {}, 0.0
    for i, (k, p) in enumerate(items):
        run = max(run, min(1.0, (m - i) * p))
        out[k] = run
    return out


def hill1_rarefied(labels: list[str], depth: int = 25, n_draw: int = 500, seed: int = 0) -> dict[str, Any]:
    if not labels:
        return {"hill1": None, "n": 0, "flag_below_depth": True}
    rng = np.random.default_rng(seed)
    if len(labels) < depth:
        c = Counter(labels)
        p = np.array(list(c.values())) / len(labels)
        return {"hill1": float(np.exp(-(p * np.log(p)).sum())), "n": len(labels), "flag_below_depth": True}
    arr = np.array(labels)
    vals = []
    for _ in range(n_draw):
        s = rng.choice(arr, size=depth, replace=False)
        c = Counter(s.tolist())
        p = np.array(list(c.values())) / depth
        vals.append(np.exp(-(p * np.log(p)).sum()))
    return {"hill1": float(np.mean(vals)), "n": len(labels), "flag_below_depth": False}


def composition(rows: list[dict[str, Any]], target: str | None = None) -> dict[str, Any]:
    n = len(rows)
    att = Counter(r["label"] for r in rows)
    corr = Counter(r["label"] for r in rows if r.get("passed") and r["label"] not in NC)
    n_valid_att = sum(v for k, v in att.items() if k not in NC)
    out = {"n": n, "attempted": dict(att), "correct": dict(corr), "n_attempted_valid": n_valid_att,
           "pass_rate": sum(1 for r in rows if r.get("passed")) / max(n, 1),
           "pass_ci": wilson_ci(sum(1 for r in rows if r.get("passed")), n),
           "invalid": att.get("invalid", 0), "disputed": att.get("disputed", 0), "other": att.get("other", 0),
           "hill1_correct": hill1_rarefied([r["label"] for r in rows if r.get("passed") and r["label"] not in NC])}
    shares = {}
    for k, v in att.items():
        if k in NC:
            continue
        lo, hi = wilson_ci(v, n_valid_att)
        shares[k] = {"k": v, "share": v / max(n_valid_att, 1), "ci": [lo, hi]}
    out["attempt_shares"] = shares
    nc = sum(corr.values())
    if nc:
        top, kk = corr.most_common(1)[0]
        out["default"] = top if kk / nc >= 0.6 else "NO DEFAULT"
        out["default_share"] = kk / nc
    if target:
        k = sum(1 for r in rows if r["label"] == target and r.get("passed"))
        out["target_correct"] = k
        out["target_correct_ci"] = wilson_ci(k, n)
        out["target_attempted"] = att.get(target, 0)
    return out


# ------------------------------------------------------------------------------------------------ S3 + engine check
def natural_split(load_labelled) -> dict[str, Any]:
    res = {}
    for task in ("T1", "T04", "R6"):
        rows = [r for r in load_labelled("raw_s3.jsonl", task) if r["arm"] == "twin"]
        res[task] = {"all": composition(rows), "by_template": {w: composition([r for r in rows if r["template"] == w])
                                                               for w in TEMPLATE_IDS}}
    write_json(RESULTS_DIR / "natural_split.json", res)
    return res


def engine_check(load_labelled, exp28_samples: str) -> dict[str, Any]:
    ref = {}
    for r in read_jsonl(exp28_samples):
        if r.get("arm") == "twin" and r.get("task") in ("T1", "T04"):
            ref[(r["task"], r["template"], int(r["slot"]))] = r
    res = {}
    for task in ("T1", "T04"):
        rows = [r for r in load_labelled("raw_s3.jsonl", task) if r["arm"] == "twin" and r["slot"] < 10]
        same_label = same_pass = n = 0
        same_code = 0
        per = []
        for r in rows:
            q = ref.get((task, r["template"], int(r["slot"])))
            if q is None:
                continue
            n += 1
            same_label += r["label"] == q["label"]
            same_pass += bool(r["passed"]) == bool(q["passed"])
            same_code += (r.get("code_sha256") is not None and r.get("code_sha256") == q.get("code_sha256"))
            per.append({"template": r["template"], "slot": r["slot"], "label": r["label"], "exp28_label": q["label"]})
        res[task] = {"n": n, "label_agreement": same_label / max(n, 1), "pass_agreement": same_pass / max(n, 1),
                     "identical_program_share": same_code / max(n, 1), "per_slot": per,
                     "verdict": ("reproduces exp28" if same_label / max(n, 1) >= 0.95 else
                                 "kernel/batch-shape sensitivity (RTX 2000 Ada, B=20 single-prompt vs exp28's L4, "
                                 "B=50 multi-prompt batch); contrasts are computed within this artifact's engine")}
    write_json(RESULTS_DIR / "engine_check.json", res)
    return res


# ------------------------------------------------------------------------------------------------ S6a
def _ngram_feats(prefixes: list[list[int]], templates: list[str]):
    from sklearn.feature_extraction import DictVectorizer

    feats = []
    for ids, w in zip(prefixes, templates):
        d: dict[str, float] = {f"tpl={w}": 1.0}
        for t in ids:
            d[f"u{t}"] = d.get(f"u{t}", 0) + 1.0
        for a, b in zip(ids, ids[1:]):
            d[f"b{a}_{b}"] = d.get(f"b{a}_{b}", 0) + 1.0
        feats.append(d)
    return DictVectorizer(sparse=True).fit_transform(feats)


def _cv_ba(X, y: np.ndarray, strata: np.ndarray, kind: str, seed: int = 0, C: float | None = None) -> tuple[float, float]:
    """5-fold CV stratified by template x class; returns (balanced accuracy, C used). kind in l1/l2/dim."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import balanced_accuracy_score
    from sklearn.model_selection import StratifiedKFold

    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
    pred = np.zeros(len(y), dtype=int)
    Cs = [0.01, 0.1, 1.0, 10.0]
    for tr, te in skf.split(np.zeros(len(y)), strata):
        if kind == "dim":
            Xtr, Xte = X[tr], X[te]
            mu1, mu0 = Xtr[y[tr] == 1].mean(0), Xtr[y[tr] == 0].mean(0)
            w = mu1 - mu0
            s_tr, s_te = Xtr @ w, Xte @ w
            thr = (np.mean(s_tr[y[tr] == 1]) + np.mean(s_tr[y[tr] == 0])) / 2
            pred[te] = (s_te > thr).astype(int)
            continue
        if C is None:
            # nested: inner 3-fold choice of C
            best, bC = -1, 1.0
            inner = StratifiedKFold(n_splits=3, shuffle=True, random_state=seed + 1)
            for c in Cs:
                sc = []
                for itr, ite in inner.split(np.zeros(len(tr)), strata[tr]):
                    m = LogisticRegression(penalty="l1" if kind == "l1" else "l2", C=c,
                                           solver="liblinear", class_weight="balanced", max_iter=2000)
                    if len(set(y[tr][itr])) < 2:
                        continue
                    m.fit(X[tr][itr], y[tr][itr])
                    sc.append(balanced_accuracy_score(y[tr][ite], m.predict(X[tr][ite])))
                if sc and np.mean(sc) > best:
                    best, bC = float(np.mean(sc)), c
            c_use = bC
        else:
            c_use = C
        m = LogisticRegression(penalty="l1" if kind == "l1" else "l2", C=c_use, solver="liblinear",
                               class_weight="balanced", max_iter=2000)
        m.fit(X[tr], y[tr])
        pred[te] = m.predict(X[te])
    from sklearn.metrics import balanced_accuracy_score as bas
    return float(bas(y, pred)), (C if C is not None else float("nan"))


def within_prompt(task: str, fk: dict[str, Any] | None, saes: dict, layers: list[int], read: str,
                  n_perm: int = 200) -> dict[str, Any]:
    """S6a at read position `read` ('r_id' | 'r_fork' | 'g16' | 'g32' | 'g64')."""
    import torch
    from sklearn.decomposition import PCA

    S = torch.load(STATES_DIR / f"s3_{task}.pt")
    H, meta = S["H"], S["meta"]
    keep, ys, tpl, prefixes, Xraw = [], [], [], [], []
    cls_map = {"T1": ("bfs", "dfs"), "T04": ("builtin", "naive"), "R6": ("binary_search", "linear_scan")}[task]
    for i, m in enumerate(meta):
        if not m["valid"] or m["label"] not in cls_map:
            continue
        if read == "r_id":
            if m.get("ident_idx") is None or m.get("rid_abs") is None:
                continue
            j = m["ident_idx"]                      # read position predicts response token j
            hidx = 97                               # stored extra slot
        elif read == "r_fork":
            j = fk["fork_token_index"]
            hidx = j
        else:
            j = int(read[1:])
            hidx = j
        if j > m["n_resp"] or (hidx < 97 and hidx >= m["n_pos"]):
            continue
        keep.append(i)
        ys.append(1 if m["label"] == cls_map[0] else 0)
        tpl.append(m["template"])
        prefixes.append(m["resp_ids"][:j])
        Xraw.append(H[i, hidx].float().numpy())       # [L, D]
    ys_a = np.array(ys)
    tpl_a = np.array(tpl)
    # exclusion: prefix identical to some other-class sample's prefix in the same template
    ok = []
    for a in range(len(keep)):
        clash = any(tpl[b] == tpl[a] and ys[b] != ys[a] and prefixes[b] == prefixes[a] for b in range(len(keep)))
        ok.append(not clash)
    ok = np.array(ok, dtype=bool)
    res: dict[str, Any] = {"task": task, "read": read, "n_candidates": len(keep),
                           "n_excluded_identical_prefix": int((~ok).sum())}
    ys_a, tpl_a = ys_a[ok], tpl_a[ok]
    prefixes = [p for p, o in zip(prefixes, ok) if o]
    Xraw = [x for x, o in zip(Xraw, ok) if o]
    n1, n0 = int(ys_a.sum()), int((1 - ys_a).sum())
    res["n_per_class"] = {cls_map[0]: n1, cls_map[1]: n0}
    if n1 < 10 or n0 < 10:
        res["verdict"] = "undefined/underpowered by construction (fewer than 10 per class after exclusion)"
        return res
    strata = np.array([f"{t}|{y}" for t, y in zip(tpl_a, ys_a)])
    # merge rare strata (StratifiedKFold needs >= 5 per stratum)
    cnt = Counter(strata)
    strata = np.array([s if cnt[s] >= 5 else f"rare|{s.split('|')[1]}" for s in strata])
    Xtext = _ngram_feats(prefixes, list(tpl_a))
    ba_text, _ = _cv_ba(Xtext, ys_a, strata, "l1")
    Xr = np.stack(Xraw)                                # [n, L, D]
    onehot = np.stack([[1.0 if t == w else 0.0 for w in TEMPLATE_IDS] for t in tpl_a])
    per_layer = {}
    for li, l in enumerate(layers):
        X = Xr[:, li]
        with torch.no_grad():
            F = saes[l].encode(torch.tensor(X)).numpy()
        from scipy import sparse
        Fs = sparse.csr_matrix(np.hstack([np.log1p(np.maximum(F, 0)), onehot]))
        ba_sae, _ = _cv_ba(Fs, ys_a, strata, "l1")
        pca = PCA(n_components=min(64, X.shape[0] - 1), random_state=0).fit(X)
        ba_pca, _ = _cv_ba(np.hstack([pca.transform(X) / (pca.singular_values_[0] + 1e-9), onehot]), ys_a, strata, "l2")
        ba_dim, _ = _cv_ba(X, ys_a, strata, "dim")
        massive = np.argsort(-np.abs(X).mean(0))[:5]
        Xm = X.copy()
        Xm[:, massive] = 0
        dif = np.abs(Xm[ys_a == 1].mean(0) - Xm[ys_a == 0].mean(0)) / (Xm.std(0) + 1e-6)
        top = np.argsort(-dif)[:32]                     # (selection on all data: optimistic for the raw-dim baseline)
        ba_dims, _ = _cv_ba(np.hstack([Xm[:, top] / (np.abs(Xm[:, top]).max() + 1e-9), onehot]), ys_a, strata, "l2")
        # permutation null for BA_SAE - BA_text (within-template label permutation, C fixed at 1)
        obs = ba_sae - ba_text
        rng = np.random.default_rng(stable_seed("perm", task, read, l) % 2 ** 32)
        null = []
        for _ in range(n_perm):
            yp = ys_a.copy()
            for w in set(tpl_a):
                idx = np.where(tpl_a == w)[0]
                yp[idx] = rng.permutation(yp[idx])
            b1, _ = _cv_ba(Fs, yp, strata, "l1", C=1.0)
            b2, _ = _cv_ba(Xtext, yp, strata, "l1", C=1.0)
            null.append(b1 - b2)
        p = (1 + sum(x >= obs for x in null)) / (1 + n_perm)
        per_layer[str(l)] = {"BA_SAE": ba_sae, "BA_text": ba_text, "BA_rawPCA64": ba_pca, "BA_DiM": ba_dim,
                             "BA_top32_raw_dims": ba_dims, "delta_SAE_minus_text": obs, "p_perm": p,
                             "n_perm": n_perm, "meets_threshold": bool(obs >= 0.10 and p < 0.01)}
    res["per_layer"] = per_layer
    res["BA_text"] = ba_text
    res["verdict"] = ("SAE beyond text at some layer" if any(v["meets_threshold"] for v in per_layer.values())
                      else "no SAE advantage over the visible-prefix text control")
    if min(n1, n0) < 30:
        res["verdict"] += " (underpowered: < 30 per class)"
    return res


# ------------------------------------------------------------------------------------------------ S6b
def cross_prompt_readout(saes: dict, layers: list[int], nouns: dict[str, Any], n_perm: int = N_PERM) -> dict[str, Any]:
    import torch
    from sklearn.decomposition import PCA
    from sklearn.linear_model import Lasso, Ridge

    V = torch.load(STATES_DIR / "variants.pt")
    y = np.array([v["y"] for v in V])
    tpl = np.array([v["template"] for v in V])
    noun = np.array([v["noun"] for v in V])
    res: dict[str, Any] = {"n": len(V), "sd_y": float(y.std(ddof=1)), "mean_y": float(y.mean()),
                           "sd_y_within_template_mean": float(np.mean([y[tpl == w].std(ddof=1) for w in TEMPLATE_IDS])),
                           "sd_y_between_template": float(np.std([y[tpl == w].mean() for w in TEMPLATE_IDS], ddof=1))}
    res["uninformative"] = bool(res["sd_y"] < 0.2)
    onehot = np.stack([[1.0 if t == w else 0.0 for w in TEMPLATE_IDS] for t in tpl])
    # text-only control: sentence embedding of the condition sentence + noun norms
    from sentence_transformers import SentenceTransformer

    st = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2", device="cpu")
    from cfg import TEMPLATES
    sents = [TEMPLATES[v["template"]][1].format(N=v["noun"]) for v in V]
    E = st.encode(sents, normalize_embeddings=True)
    meta = {**{c["word"]: c for c in nouns.get("new_meta", {}).values()}}
    cand = {c["word"]: c for c in read_json(__import__("cfg").ROOT / "inputs" / "dep_extract" / "noun_candidates.json")}
    lex = []
    for v in V:
        c = cand.get(v["noun"]) or meta.get(v["noun"]) or {}
        lex.append([float(c.get("concreteness") or 0.0), math.log1p(float(c.get("subtlex") or 0.0)), 1.0])
    lex = np.array(lex)
    lex = (lex - lex.mean(0)) / (lex.std(0) + 1e-9)
    Xtext = np.hstack([E, lex, onehot])
    folds_noun = [np.where(noun == n)[0] for n in sorted(set(noun))]
    folds_tpl = [np.where(tpl == w)[0] for w in TEMPLATE_IDS]

    def cv_pred(X: np.ndarray, yy: np.ndarray, model: str, folds: list[np.ndarray], alpha: float) -> np.ndarray:
        pred = np.zeros_like(yy)
        for te in folds:
            tr = np.setdiff1d(np.arange(len(yy)), te)
            if model == "dim":
                lo, hi = np.quantile(yy[tr], [1 / 3, 2 / 3])
                w = X[tr][yy[tr] >= hi].mean(0) - X[tr][yy[tr] <= lo].mean(0)
                s = X @ w
                a, b = np.polyfit(s[tr], yy[tr], 1)
                pred[te] = a * s[te] + b
                continue
            m = Lasso(alpha=alpha, max_iter=20000) if model == "lasso" else Ridge(alpha=alpha)
            m.fit(X[tr], yy[tr])
            pred[te] = m.predict(X[te])
        return pred

    def r2(yy: np.ndarray, pred: np.ndarray) -> float:
        return float(1 - ((yy - pred) ** 2).sum() / ((yy - yy.mean()) ** 2).sum())

    models: dict[str, tuple[np.ndarray, str, float]] = {"text": (Xtext, "ridge", 1.0), "template_only": (onehot, "ridge", 1.0)}
    for l in layers:
        for site, key in (("FORK", "codes_fork"), ("SPEC", "codes_spec_mean")):
            F = np.stack([v[key][l].float().numpy() for v in V])
            F = np.log1p(np.maximum(F, 0))
            F = F[:, (F > 0).sum(0) >= 2]                   # latents active in >= 2 variants (y not used)
            F = F / (F.std(0) + 1e-6)
            models[f"SAE|{site}|{l}"] = (np.hstack([F, onehot]), "lasso", 0.01)
            rk = "fork" if site == "FORK" else "spec_mean"
            R = np.stack([v[rk][l].float().numpy() for v in V])
            Rm = R.copy()
            Rm[:, np.argsort(-np.abs(R).mean(0))[:5]] = 0
            for kk in (16, 64):
                P = PCA(n_components=min(kk, len(V) - 1), random_state=0).fit_transform(Rm)
                P = P / (P.std(0) + 1e-9)
                models[f"rawPCA{kk}|{site}|{l}"] = (np.hstack([P, onehot]), "ridge", 10.0)
            models[f"DiM|{site}|{l}"] = (Rm, "dim", 0.0)
    out = {}
    for name, (X, kind, alpha) in models.items():
        pr = cv_pred(X, y, kind, folds_noun, alpha)
        prt = cv_pred(X, y, kind, folds_tpl, alpha)
        out[name] = {"R2_lono": r2(y, pr), "spearman_lono": float(stats.spearmanr(y, pr).correlation),
                     "R2_loto": r2(y, prt)}
    res["models"] = out
    # permutation null (within template) + noun bootstrap for the best SAE model vs text
    sae_names = [k for k in out if k.startswith("SAE|")]
    best = max(sae_names, key=lambda k: out[k]["R2_lono"])
    res["best_sae_model"] = best
    Xb, kb, ab = models[best]
    Xt, kt, at = models["text"]
    obs = out[best]["R2_lono"] - out["text"]["R2_lono"]
    rng = np.random.default_rng(7)
    n_eff = 0 if res["uninformative"] else min(n_perm, 300)
    null = []
    for _ in range(n_eff):
        yp = y.copy()
        for w in TEMPLATE_IDS:
            idx = np.where(tpl == w)[0]
            yp[idx] = rng.permutation(yp[idx])
        null.append(r2(yp, cv_pred(Xb, yp, kb, folds_noun, ab)) - r2(yp, cv_pred(Xt, yp, kt, folds_noun, at)))
    res["delta_R2_best_SAE_minus_text"] = obs
    res["p_perm"] = (1 + sum(x >= obs for x in null)) / (1 + n_eff) if n_eff else None
    res["n_perm"] = n_eff
    pb = cv_pred(Xb, y, kb, folds_noun, ab)
    pt = cv_pred(Xt, y, kt, folds_noun, at)
    nouns_u = sorted(set(noun))
    boots = []
    for _ in range(1000):
        pick = rng.choice(nouns_u, size=len(nouns_u), replace=True)
        idx = np.concatenate([np.where(noun == n)[0] for n in pick])
        boots.append(r2(y[idx], pb[idx]) - r2(y[idx], pt[idx]))
    res["delta_R2_ci95"] = [float(np.quantile(boots, 0.025)), float(np.quantile(boots, 0.975))]
    dim_best = max([k for k in out if k.startswith("DiM|")], key=lambda k: out[k]["R2_lono"])
    raw_best = max([k for k in out if k.startswith("rawPCA")], key=lambda k: out[k]["R2_lono"])
    res["best_DiM"], res["best_raw"] = dim_best, raw_best
    res["SAE_ge_DiM"] = bool(out[best]["R2_lono"] >= out[dim_best]["R2_lono"])
    res["meets_threshold"] = bool(not res["uninformative"] and obs >= 0.10 and (res["p_perm"] or 1) < 0.01)
    res["verdict"] = ("UNINFORMATIVE (SD(y_v) < 0.2 nats)" if res["uninformative"] else
                      ("plan probability readable from features beyond the text" if res["meets_threshold"]
                       else "no SAE advantage over the text-only control"))
    write_json(RESULTS_DIR / "readout.json", res)
    return res


# ------------------------------------------------------------------------------------------------ S6c
def contrast_separability(saes: dict, layers: list[int]) -> dict[str, Any]:
    import torch
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import LeaveOneOut, cross_val_predict

    C = torch.load(STATES_DIR / "contrast.pt")
    res = {}
    for name, ga, gb in (("forcedBFS_vs_forcedDFS", "forced_bfs", "forced_dfs"), ("banDFS_vs_banBFS", "ban_dfs", "ban_bfs")):
        A = [c for c in C if c["group"] == ga]
        B = [c for c in C if c["group"] == gb]
        y = np.array([1] * len(A) + [0] * len(B))
        out = {}
        for l in layers:
            F = np.log1p(np.stack([c["codes_spec_mean"][l].float().numpy() for c in A + B]).clip(min=0))
            R = np.stack([c["spec_mean"][l].float().numpy() for c in A + B])
            R[:, np.argsort(-np.abs(R).mean(0))[:5]] = 0
            R = (R - R.mean(0)) / (R.std(0) + 1e-6)          # z-score (max-abs scaling collapsed the classifier)
            F = (F - F.mean(0)) / (F.std(0) + 1e-6)
            accs = {}
            for nm, X in (("SAE", F), ("raw", R)):
                # leave-one-out nearest-class-mean (z-scored features; a logistic fit on 16k dims did not converge
                # in reasonable time, and max-abs scaling collapsed it to the training majority)
                ok = 0
                for i in range(len(y)):
                    tr = np.arange(len(y)) != i
                    m1 = X[tr & (y == 1)].mean(0)
                    m0 = X[tr & (y == 0)].mean(0)
                    ok += int((np.linalg.norm(X[i] - m1) < np.linalg.norm(X[i] - m0)) == bool(y[i]))
                accs[nm] = ok / len(y)
            F0 = np.log1p(np.stack([c["codes_spec_mean"][l].float().numpy() for c in A + B]).clip(min=0))
            d = (F0[y == 1].mean(0) - F0[y == 0].mean(0)) / (np.sqrt((F0[y == 1].var(0) + F0[y == 0].var(0)) / 2) + 1e-3)
            top = np.argsort(-np.abs(d))[:10]
            out[str(l)] = {"loo_acc": accs, "top_latents": [{"latent": int(i), "d": float(d[i])} for i in top]}
        res[name] = {"n": [len(A), len(B)], "per_layer": out}
    res["neuronpedia_note"] = ("latent ids are reported for lookup on Neuronpedia's Gemma Scope 2 gemma-3-4b-it pages; "
                               "labels were not fetched (descriptive only, no claim rests on them)")
    write_json(RESULTS_DIR / "contrast_separability.json", res)
    return res


# ------------------------------------------------------------------------------------------------ S8
def clamp_tests(load_labelled, c1: dict[str, Any]) -> dict[str, Any]:
    rows = load_labelled("raw_cells.jsonl", "T1")
    by_cell: dict[str, dict[tuple, dict]] = {}
    for r in rows:
        by_cell.setdefault(r["arm"], {})[(r["template"], r["slot"])] = r
    base = by_cell.get("twin_cstar", {})
    keys = sorted(base)
    res: dict[str, Any] = {"cells": {}, "tests": {}}
    tw_pass = sum(1 for k in keys if base[k]["passed"]) / max(len(keys), 1)

    def ind(cell: str, target: str) -> list[int]:
        d = by_cell.get(cell, {})
        return [1 if (k in d and d[k]["label"] == target and d[k]["passed"]) else 0 for k in keys]

    for cell, d in by_cell.items():
        meta = next(iter(d.values()))
        target = meta.get("toward") or "bfs"
        rr = [d[k] for k in keys if k in d]
        comp = composition(rr, target)
        norms = [x["edit_log"][0]["ox_norm_mean"] for x in rr if x.get("edit_log")]
        comp["realised_ox_norm_mean"] = float(np.mean(norms)) if norms else 0.0
        disp = [x["realised_disp"]["R_by_block"] for x in rr if x.get("realised_disp")]
        comp["realised_disp_R_by_block_mean"] = np.mean(np.array(disp), 0).round(2).tolist() if disp else None
        comp["meta"] = {k: meta.get(k) for k in ("site", "layer", "kind", "src", "k_features", "toward", "lambda")}
        comp["flip_table_vs_twin"] = mcnemar_exact(ind(cell, target), ind("twin_cstar", target))
        res["cells"][cell] = comp
    res["twin_pass"] = tw_pass
    ps = {}
    for site in ("FORK", "SPEC"):
        for k in (20, 50):
            fe, dm = f"{site}|FEATin|k{k}", f"{site}|DiM@k{k}"
            if fe in by_cell and dm in by_cell:
                t = mcnemar_exact(ind(fe, "bfs"), ind(dm, "bfs"))
                fc, dc = sum(ind(fe, "bfs")), sum(ind(dm, "bfs"))
                pf = res["cells"][fe]["pass_rate"]
                t.update({"feat_target_correct": fc, "dim_target_correct": dc,
                          "feature_claim": bool(fc >= dc and pf >= 0.8 * tw_pass),
                          "pass_gap": abs(pf - res["cells"][dm]["pass_rate"])})
                res["tests"][f"FEAT_vs_DiM|{site}|k{k}"] = t
                ps[f"FEAT_vs_DiM|{site}|k{k}"] = t["p"]
        fe, rf = f"{site}|FEATin|k50", f"{site}|RANDF@k50"
        if fe in by_cell and rf in by_cell:
            t = mcnemar_exact(ind(fe, "bfs"), ind(rf, "bfs"))
            t["delta"] = (sum(ind(fe, "bfs")) - sum(ind(rf, "bfs"))) / max(len(keys), 1)
            t["meets"] = bool(t["delta"] >= 0.20 and t["p"] < 0.05)
            res["tests"][f"FEAT_vs_RANDF|{site}|k50"] = t
            ps[f"FEAT_vs_RANDF|{site}|k50"] = t["p"]
        for k in (5, 20, 50):
            fe = f"{site}|FEATin|k{k}"
            if fe in by_cell:
                t = mcnemar_exact(ind(fe, "bfs"), ind("twin_cstar", "bfs"))
                res["tests"][f"FEAT_vs_baseline|{site}|k{k}"] = t
                ps[f"FEAT_vs_baseline|{site}|k{k}"] = t["p"]
        for k in (20, 50):
            dm = f"{site}|DiM@k{k}"
            if dm in by_cell:
                t = mcnemar_exact(ind(dm, "bfs"), ind("twin_cstar", "bfs"))
                res["tests"][f"DiM_vs_baseline|{site}|k{k}"] = t
                ps[f"DiM_vs_baseline|{site}|k{k}"] = t["p"]
    for cell in by_cell:
        if "|DAS|" in cell:
            t = mcnemar_exact(ind(cell, "bfs"), ind("twin_cstar", "bfs"))
            res["tests"][f"DAS_vs_baseline|FORK|{cell.split('|')[-1]}"] = t
            ps[f"DAS_vs_baseline|FORK|{cell.split('|')[-1]}"] = t["p"]
    hp = holm(ps)
    for k, v in hp.items():
        res["tests"][k]["p_holm"] = v
    # ---- secondary (descriptive, outside the Holm family): attempted-class indicators (the plan moved, regardless
    # of correctness) and the comparisons involving the matched-dy DiM cells, DAS and the joint top-5 node edits
    def att(cell: str, target: str) -> list[int]:
        d = by_cell.get(cell, {})
        return [1 if (k in d and d[k]["label"] == target) else 0 for k in keys]

    sec: dict[str, Any] = {}
    pairs = []
    for site in ("FORK", "SPEC"):
        for k in (20, 50):
            pairs.append((f"{site}|FEATin|k{k}", f"{site}|DiM@k{k}"))
        pairs.append((f"{site}|FEATin|k50", f"{site}|RANDF@k50"))
        for k in (5, 20, 50):
            pairs.append((f"{site}|FEATin|k{k}", "twin_cstar"))
        for k in (20, 50):
            pairs.append((f"{site}|DiM@k{k}", "twin_cstar"))
    pairs += [("FORK|FEATin|k20", "FORK|DiM@k20|matchDy"), ("FORK|FEATin|k50", "FORK|DiM@k50|matchDy"),
              ("FORK|DiM@k20|matchDy", "twin_cstar"), ("FORK|DiM@k50|matchDy", "twin_cstar"),
              ("FORK|FEATout|k20", "twin_cstar"), ("FORK|FEATout|k20", "FORK|DiM@k20"),
              ("FORK|NODES5|ablate", "twin_cstar"), ("FORK|NODES5|steerBFS", "twin_cstar")]
    pairs += [(c, "twin_cstar") for c in by_cell if "|DAS|" in c]
    for a, b in pairs:
        if a not in by_cell or b not in by_cell:
            continue
        ka = [k for k in keys if k in by_cell[a]]
        if not ka:
            continue
        t_att = mcnemar_exact(att(a, "bfs"), att(b, "bfs"))
        t_cor = mcnemar_exact(ind(a, "bfs"), ind(b, "bfs"))
        sec[f"{a} vs {b}"] = {"attempted_bfs": t_att, "target_correct": t_cor,
                              "attempted_bfs_counts": [sum(att(a, "bfs")), sum(att(b, "bfs"))],
                              "target_correct_counts": [sum(ind(a, "bfs")), sum(ind(b, "bfs"))],
                              "n_pairs_complete": len(ka)}
    for c in ("FORK|FEATin|k20|toDFS", "FORK|DiM@k20|toDFS"):
        if c in by_cell:
            sec[f"{c} vs twin_cstar"] = {"attempted_dfs": mcnemar_exact(att(c, "dfs"), att("twin_cstar", "dfs")),
                                         "target_correct_dfs": mcnemar_exact(ind(c, "dfs"), ind("twin_cstar", "dfs")),
                                         "attempted_dfs_counts": [sum(att(c, "dfs")), sum(att("twin_cstar", "dfs"))]}
    res["tests_secondary"] = sec
    claims = [v for k, v in res["tests"].items() if k.startswith("FEAT_vs_DiM")]
    res["feature_claim"] = bool(claims and all(c["feature_claim"] for c in claims))
    res["matched_pass_rule_triggered"] = [k for k, v in res["tests"].items()
                                          if k.startswith("FEAT_vs_DiM") and v.get("pass_gap", 0) > 0.10]
    write_json(RESULTS_DIR / "clamps.json", res)
    return res


def sweep_summary() -> dict[str, Any]:
    rows = read_jsonl(RESULTS_DIR / "logit_sweep.jsonl")
    out: dict[str, Any] = {"n_rows": len(rows)}
    groups: dict[str, list] = {}
    for r in rows:
        key = f"{r['site']}|{r['layer']}|{r['kind']}|{r['src']}|k{r['k']}|lam{r['lam']}"
        groups.setdefault(key, []).append(r)
    summ = {}
    for key, g in groups.items():
        n_nan = sum(1 for x in g if x["dy"] is None)
        g = [x for x in g if x["dy"] is not None]
        if not g:
            summ[key] = {"n": 0, "n_nonfinite": n_nan}
            continue
        dy = np.array([x["dy"] for x in g], dtype=float)
        ho = np.array([x["dy"] for x in g if x["held_out"]], dtype=float)
        summ[key] = {"n": len(g), "mean_dy": float(dy.mean()), "sd_dy": float(dy.std()),
                     "mean_dy_heldout": float(ho.mean()) if len(ho) else None,
                     "frac_positive": float((dy > 0).mean()),
                     "ox_norm_mean": float(np.nanmean([x.get("ox_norm_mean") or np.nan for x in g])),
                     "n_nonfinite": n_nan}
    out["cells"] = summ
    write_json(RESULTS_DIR / "logit_sweep_summary.json", out)
    return out


def top5_landing(load_labelled) -> dict[str, Any]:
    from cfg import T1_MODES, TOP5_BANNED, TOP5_SURVIVORS

    rows = load_labelled("raw_contrast.jsonl", "T1")
    res = {}
    for arm in ("top5", "top5_twin", "ban_bfs", "ban_dfs", "forced_bfs", "forced_dfs"):
        rr = [r for r in rows if r["arm"] == arm]
        c = composition(rr)
        att = Counter(r["label"] for r in rr if r["label"] not in NC)
        nv = sum(att.values())
        c["banned_share"] = sum(att.get(m, 0) for m in TOP5_BANNED) / max(nv, 1)
        c["survivor_share"] = sum(att.get(m, 0) for m in TOP5_SURVIVORS) / max(nv, 1)
        c["other_share"] = att.get("other", 0) / max(nv, 1)
        c["avoidance"] = 1 - c["banned_share"]
        res[arm] = c
    res["catalogue"] = list(T1_MODES)
    res["banned"] = list(TOP5_BANNED)
    res["survivors"] = list(TOP5_SURVIVORS)
    a = [1 if r["label"] == "bfs" else 0 for r in sorted(rows, key=lambda r: (r["template"], r["slot"])) if r["arm"] == "top5"]
    b = [1 if r["label"] == "bfs" else 0 for r in sorted(rows, key=lambda r: (r["template"], r["slot"])) if r["arm"] == "top5_twin"]
    res["top5_vs_twin_bfs_mcnemar"] = mcnemar_exact(a, b) if len(a) == len(b) else None
    res["qwen_exp9_reference"] = "Qwen3-8B TOP5: avoidance 0.00 (BFS 63, DFS 36) per the plan"
    write_json(RESULTS_DIR / "top5.json", res)
    return res


__all__ = ["natural_split", "engine_check", "within_prompt", "cross_prompt_readout", "contrast_separability",
           "clamp_tests", "sweep_summary", "top5_landing", "mcnemar_exact", "holm", "composition"]
_ = (itertools, logger)
