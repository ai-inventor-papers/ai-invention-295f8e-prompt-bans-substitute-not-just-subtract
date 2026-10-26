"""S12 probes (CPU): position x layer multinomial probes scored as information gain over a prompt-only predictor.

Per cell: StandardScaler + PCA(64) fit in-fold, LogisticRegression (C in {0.01, 0.1, 1} by inner 3-fold CV), outer
StratifiedKFold(5, shuffle, seed 0). Nulls: global label shuffles and within-(condition, paraphrase) permutations
(fixed C, same folds). 95% CI of IG by clustered bootstrap over prompt clusters.
"""

from __future__ import annotations

import multiprocessing as mp
import warnings
from concurrent.futures import ProcessPoolExecutor

import numpy as np

CS = (0.01, 0.1, 1.0)
N_NULL = 20


def _prep_folds(X: np.ndarray, y: np.ndarray, folds) -> list:
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import StandardScaler
    out = []
    for tr, te in folds:
        sc = StandardScaler().fit(X[tr])
        k = int(min(64, len(tr) - 1, X.shape[1]))
        pca = PCA(n_components=k, random_state=0).fit(sc.transform(X[tr]))
        out.append((tr, te, pca.transform(sc.transform(X[tr])), pca.transform(sc.transform(X[te]))))
    return out


def _fit_predict(Ztr, ytr, Zte, C: float, n_classes: int) -> np.ndarray:
    from sklearn.linear_model import LogisticRegression
    P = np.zeros((len(Zte), n_classes))
    cls = np.unique(ytr)
    if len(cls) == 1:
        P[:, cls[0]] = 1.0
        return P
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        m = LogisticRegression(C=C, max_iter=300).fit(Ztr, ytr)
    P[:, m.classes_] = m.predict_proba(Zte)
    return P


def _choose_C(Ztr, ytr, n_classes) -> float:
    from sklearn.model_selection import StratifiedKFold
    best, bc = np.inf, 0.1
    mincount = np.bincount(ytr).min() if len(np.unique(ytr)) > 1 else 0
    if mincount < 3:
        return 0.1
    skf = StratifiedKFold(3, shuffle=True, random_state=1)
    for C in CS:
        ce = 0.0
        for a, b in skf.split(Ztr, ytr):
            P = _fit_predict(Ztr[a], ytr[a], Ztr[b], C, n_classes)
            ce += -np.log2(np.clip(P[np.arange(len(b)), ytr[b]], 1e-3, 1)).sum()
        if ce < best:
            best, bc = ce, C
    return bc


def prompt_only(y: np.ndarray, groups: np.ndarray, folds, n_classes: int) -> np.ndarray:
    P = np.zeros((len(y), n_classes))
    for tr, te in folds:
        for g in np.unique(groups[te]):
            m_tr = tr[groups[tr] == g]
            cnt = np.bincount(y[m_tr], minlength=n_classes) + 0.5
            P[te[groups[te] == g]] = cnt / cnt.sum()
    return P


def cell(args: tuple) -> dict:
    X, y, groups, n_classes, seed, do_null = args
    from sklearn.model_selection import StratifiedKFold
    skf = StratifiedKFold(5, shuffle=True, random_state=0)
    folds = list(skf.split(X, y))
    prep = _prep_folds(X, y, folds)
    P = np.zeros((len(y), n_classes))
    Cs = []
    for tr, te, Ztr, Zte in prep:
        C = _choose_C(Ztr, y[tr], n_classes)
        Cs.append(C)
        P[te] = _fit_predict(Ztr, y[tr], Zte, C, n_classes)
    Pp = prompt_only(y, groups, folds, n_classes)
    ce_s = -np.log2(np.clip(P[np.arange(len(y)), y], 1e-3, 1))
    ce_p = -np.log2(np.clip(Pp[np.arange(len(y)), y], 1e-3, 1))
    pred = P.argmax(1)
    acc = float((pred == y).mean())
    bal = float(np.mean([(pred[y == c] == c).mean() for c in np.unique(y)]))
    res = {"acc": acc, "bal_acc": bal, "ce_probe": float(ce_s.mean()), "ce_prompt": float(ce_p.mean()),
           "ig": float(ce_p.mean() - ce_s.mean()), "C": float(np.median(Cs)),
           "ig_per_sample": (ce_p - ce_s).tolist()}
    if do_null:
        rng = np.random.default_rng(seed)
        Cfix = float(np.median(Cs))
        nulls = {"global": [], "within": []}
        for kind in ("global", "within"):
            for _ in range(N_NULL):
                yp = y.copy()
                if kind == "global":
                    yp = rng.permutation(y)
                else:
                    for g in np.unique(groups):
                        idx = np.where(groups == g)[0]
                        yp[idx] = rng.permutation(y[idx])
                Pn = np.zeros((len(y), n_classes))
                for tr, te, Ztr, Zte in prep:
                    Pn[te] = _fit_predict(Ztr, yp[tr], Zte, Cfix, n_classes)
                Ppn = prompt_only(yp, groups, folds, n_classes)
                cs = -np.log2(np.clip(Pn[np.arange(len(y)), yp], 1e-3, 1)).mean()
                cp = -np.log2(np.clip(Ppn[np.arange(len(y)), yp], 1e-3, 1)).mean()
                nulls[kind].append(float(cp - cs))
        res["null_global"] = nulls["global"]
        res["null_within"] = nulls["within"]
        res["significant"] = bool(res["ig"] > max(nulls["within"]))
    return res


def cluster_ci(ig_per_sample: list, groups: np.ndarray, n_boot: int = 1000, seed: int = 0) -> tuple:
    v = np.asarray(ig_per_sample)
    gs = np.unique(groups)
    rng = np.random.default_rng(seed)
    sums = np.array([v[groups == g].sum() for g in gs])
    cnts = np.array([(groups == g).sum() for g in gs])
    bs = []
    for _ in range(n_boot):
        pick = rng.integers(0, len(gs), len(gs))
        bs.append(sums[pick].sum() / max(1, cnts[pick].sum()))
    return float(np.quantile(bs, 0.025)), float(np.quantile(bs, 0.975))


def run_grid(X: np.ndarray, mask: np.ndarray, y: np.ndarray, groups: np.ndarray, pos_names: list, layers: list,
             workers: int = 10, null_every: int = 2, subset_fn=None) -> list[dict]:
    """X: [n, P, L, D]; returns one dict per (position, layer) cell."""
    jobs, keys = [], []
    for pi, pn in enumerate(pos_names):
        sel = mask[:, pi] if subset_fn is None else (mask[:, pi] & subset_fn(pi))
        idx = np.where(sel)[0]
        if len(idx) < 20:
            continue
        yy = y[idx]
        cls, cnt = np.unique(yy, return_counts=True)
        if (cnt >= 10).sum() < 2:
            continue
        remap = {c: i for i, c in enumerate(cls)}
        yr = np.array([remap[c] for c in yy])
        if np.bincount(yr).min() < 5:
            continue
        for li, ln in enumerate(layers):
            jobs.append((X[idx, pi, li, :].astype(np.float32), yr, groups[idx], len(cls), 1000 * pi + li,
                         li % null_every == 0))
            keys.append((pn, ln, idx))
    out = []
    if not jobs:
        return out
    with ProcessPoolExecutor(max_workers=workers, mp_context=mp.get_context("spawn")) as ex:
        for (pn, ln, idx), r in zip(keys, ex.map(cell, jobs, chunksize=2)):
            lo, hi = cluster_ci(r["ig_per_sample"], groups[idx])
            r.pop("ig_per_sample")
            r.update({"position": pn, "layer": int(ln), "n": int(len(idx)), "ig_ci": [lo, hi]})
            out.append(r)
    return out
