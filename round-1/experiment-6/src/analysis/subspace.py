#!/usr/bin/env python3
"""8d subspace test at the read position R and 8e temperature variance split at generated positions.

Mode subspace S_R(l): orthonormal basis of the centred forced-prompt (named) centroids, dim M-1.
8d: paired displacement d_p = ||P_S(h(c,p) - h(base,p))|| vs the 45 baseline-pair null; mean-shift permutation;
    alignment share of the mean paired difference vs isotropic and data-matched random subspaces; direction.
8e: per (task, T) and generated position t: mode variance tr(P_S Cov_t), complement variance, share; nulls from
    random subspaces; OLS slopes in T with sample-bootstrap CIs computed exactly from per-position Gram matrices.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import STATES, load_npy_parts  # noqa: E402

TEMPS = [0.3, 0.7, 1.0, 1.3]
COND_ORDER = ["seed_entropy", "seed_word", "seed_semantic", "seed_entropy_fresh", "seed_word_fresh", "neutral_insert",
              "instr_creative", "instr_new_algo", "instr_fully_novel", "instr_enumerate"]


def load_meta() -> dict:
    return json.loads((STATES / "meta.json").read_text())


def basis_from_groups(X: np.ndarray, y: np.ndarray, min_n: int = 1) -> tuple[np.ndarray, list, np.ndarray]:
    modes = [m for m in sorted(set(y.tolist())) if (y == m).sum() >= min_n]
    C = np.stack([X[y == m].mean(0) for m in modes])
    Cc = C - C.mean(0)
    U, S, _ = np.linalg.svd(Cc.T, full_matrices=False)
    k = max(1, len(modes) - 1)
    return U[:, :k], modes, Cc


def random_frame(d: int, k: int, rng, V: np.ndarray | None = None) -> np.ndarray:
    if V is None:
        Q, _ = np.linalg.qr(rng.standard_normal((d, k)))
        return Q
    q, _ = np.linalg.qr(rng.standard_normal((V.shape[1], k)))
    return V @ q


def subspace_test(meta: dict, task: str, layer: int, rng, n_boot=2000, n_perm=10000, n_null=100) -> dict:
    Hn = np.load(STATES / f"R_named_{task}.npy", mmap_mode="r")[:, layer].astype(np.float64)
    Hd = np.load(STATES / f"R_described_{task}.npy", mmap_mode="r")[:, layer].astype(np.float64)
    Hc = np.load(STATES / f"R_conditions_{task}.npy", mmap_mode="r")[:, layer].astype(np.float64)
    yn = np.array([r["condition"].split(":")[1] for r in meta[f"R_named_{task}"]])
    rows = meta[f"R_conditions_{task}"]
    B, modes, Cc = basis_from_groups(Hn, yn)
    k = B.shape[1]
    allR = np.concatenate([Hn, Hd, Hc])
    mu = allR.mean(0)
    _, _, Vt = np.linalg.svd(allR - mu, full_matrices=False)
    V50 = Vt[:50].T
    d = Hn.shape[1]
    idx = {(r["condition"], r["paraphrase_id"]): i for i, r in enumerate(rows)}
    base = np.stack([Hc[idx[("baseline", p)]] for p in range(10)])
    null = np.array([np.linalg.norm(B.T @ (base[p] - base[q])) for p in range(10) for q in range(p + 1, 10)])
    iso = [random_frame(d, k, rng) for _ in range(n_null)]
    dm = [random_frame(d, k, rng, V50) for _ in range(n_null)]
    probe = np.load(STATES / f"R_conditions_probe_{task}.npy")
    classes = meta[f"probe_classes_{task}"]
    base_probe = np.stack([probe[idx[("baseline", p)]] for p in range(10)]).mean(0)
    out = dict(layer=layer, subspace_dim=k, modes=modes, null_median=float(np.median(null)), conditions={})
    from scipy.stats import mannwhitneyu
    for c in COND_ORDER:
        if (c, 0) not in idx:
            continue
        H = np.stack([Hc[idx[(c, p)]] for p in range(10)])
        diffs = H - base
        dvals = np.linalg.norm(diffs @ B, axis=1)
        ratio = float(np.median(dvals) / np.median(null))
        bs = [np.median(rng.choice(dvals, 10)) / np.median(rng.choice(null, 45)) for _ in range(n_boot)]
        mw = mannwhitneyu(dvals, null, alternative="greater")
        obs = np.linalg.norm(B.T @ (H.mean(0) - base.mean(0)))
        pool = np.concatenate([H, base])
        cnt = 0
        for _ in range(n_perm):
            pm = rng.permutation(20)
            cnt += np.linalg.norm(B.T @ (pool[pm[:10]].mean(0) - pool[pm[10:]].mean(0))) >= obs - 1e-12
        D = diffs.mean(0)
        nD = np.linalg.norm(D)
        share = float(np.linalg.norm(B.T @ D) ** 2 / nD ** 2) if nD > 0 else None
        iso_sh = [float(np.linalg.norm(Q.T @ D) ** 2 / nD ** 2) for Q in iso]
        dm_sh = [float(np.linalg.norm(Q.T @ D) ** 2 / nD ** 2) for Q in dm]
        cos = {m: float(D @ Cc[i] / (nD * np.linalg.norm(Cc[i]) + 1e-12)) for i, m in enumerate(modes)}
        cprobe = np.stack([probe[idx[(c, p)]] for p in range(10)]).mean(0)
        out["conditions"][c] = dict(
            d_median=float(np.median(dvals)), ratio=ratio, ratio_ci90=[float(np.quantile(bs, 0.05)),
                                                                     float(np.quantile(bs, 0.95))],
            mannwhitney_p_greater=float(mw.pvalue), mean_shift=float(obs), mean_shift_perm_p=(cnt + 1) / (n_perm + 1),
            alignment_share=share, share_pct_rank_isotropic=float(np.mean(np.array(iso_sh) < share)) if share
            is not None else None, share_pct_rank_datamatched=float(np.mean(np.array(dm_sh) < share)) if share
            is not None else None, isotropic_null_median=float(np.median(iso_sh)),
            datamatched_null_median=float(np.median(dm_sh)), total_displacement=float(np.linalg.norm(diffs, axis=1).mean()),
            cos_with_centroids=cos, probe_shift={cl: float(cprobe[j] - base_probe[j]) for j, cl in enumerate(classes)},
            within_null_1p5=bool(np.quantile(bs, 0.95) < 1.5))
    return out


def probe_validity(meta: dict, task: str, samples: list[dict], rng, n_perm: int = 1000) -> dict:
    """Probe-predicted mode distribution at R vs realised label distribution per generated condition."""
    probe = np.load(STATES / f"R_conditions_probe_{task}.npy")
    classes = meta[f"probe_classes_{task}"]
    rows = meta[f"R_conditions_{task}"]
    conds = ["baseline", "seed_entropy", "seed_word", "seed_semantic", "instr_creative", "instr_new_algo",
             "instr_fully_novel", "instr_enumerate"]
    P, Q = [], []
    for c in conds:
        pi = probe[[i for i, r in enumerate(rows) if r["condition"] == c]].mean(0)
        arm_rows = [s for s in samples if s["task"] == task and s["condition"] == c and s["arm"] in ("A0", "A2", "A3")]
        cnt = Counter(s["label"] for s in arm_rows)
        q = np.array([cnt.get(cl, 0) for cl in classes], float)
        q = q / q.sum() if q.sum() else q
        P.append(pi)
        Q.append(q)
    P, Q = np.array(P), np.array(Q)

    def js(p, q):
        m = 0.5 * (p + q)
        kl = lambda a, b: float(np.sum(np.where(a > 0, a * np.log((a + 1e-12) / (b + 1e-12)), 0)))
        return 0.5 * kl(p, m) + 0.5 * kl(q, m)
    from scipy.stats import spearmanr
    obs_js = float(np.mean([js(p, q) for p, q in zip(P, Q)]))
    null = []
    for _ in range(n_perm):
        pm = rng.permutation(len(classes))
        null.append(np.mean([js(p[pm], q) for p, q in zip(P, Q)]))
    # across conditions: does the probe's predicted primary-mode mass track the realised primary share?
    prim = int(np.argmax(Q[0])) if Q[0].sum() else 0
    rho = spearmanr(P[:, prim], Q[:, prim]).statistic if np.std(P[:, prim]) > 0 and np.std(Q[:, prim]) > 0 else None
    return dict(conditions=conds, classes=classes, mean_js=obs_js, shuffled_probe_js_p05=float(np.quantile(null, 0.05)),
                js_below_null_p=float(np.mean(np.array(null) <= obs_js)), spearman_primary_mass_vs_share=rho,
                predicted=P.round(4).tolist(), realised=Q.round(4).tolist())


def _gram_stats(X: np.ndarray, B: np.ndarray):
    """X [n, 64, d] -> per-position Gram matrices of raw and projected states."""
    G = np.einsum("itd,jtd->tij", X, X, optimize=True)
    Y = X @ B
    P = np.einsum("itk,jtk->tij", Y, Y, optimize=True)
    return G, P


def _proj_gram(X: np.ndarray, B: np.ndarray) -> np.ndarray:
    Y = X @ B
    return np.einsum("itk,jtk->tij", Y, Y, optimize=True)


def _var_from_gram(G: np.ndarray, W: np.ndarray) -> np.ndarray:
    """Sample variance trace per position for weight vectors W [b, n] (bootstrap multiplicities)."""
    n = W.sum(1, keepdims=True)  # [b,1]
    diag = np.einsum("tii->ti", G)  # [t, n]
    s1 = W @ diag.T  # [b, t]
    quad = np.einsum("bi,tij,bj->bt", W, G, W, optimize=True)
    return (s1 - quad / n) / (n - 1)


def variance_split(meta: dict, task: str, samples: list[dict], rng, n_boot=1000, n_null=100) -> dict:
    lstar = meta["l_star"][task]
    layers = meta[f"eval_{task}"]["layers"]
    li = lstar if lstar in layers else layers[len(layers) // 2]
    rows = meta[f"eval_{task}"]["rows"]
    X_all = load_npy_parts(STATES / f"eval_{task}_l{li}").astype(np.float32)
    Ts = np.array([r["T"] for r in rows])
    d = X_all.shape[2]
    lab = {s["key"]: s for s in samples}
    # S_gen: forced generations whose final label equals the forced mode (modes with >= 5 such samples)
    fit_rows = meta[f"fit_{task}"]["rows"]
    F = np.load(STATES / f"fitmeans_{task}_l{li}.npy")
    sel = [i for i, r in enumerate(fit_rows) if r["src"] == "A5" and r["key"] in lab and
           lab[r["key"]]["label"] == r["condition"].split(":")[1]]
    yF = np.array([fit_rows[i]["condition"].split(":")[1] for i in sel])
    cnt = Counter(yF.tolist())
    keep = [i for i, y in zip(sel, yF) if cnt[y] >= 5]
    yk = np.array([fit_rows[i]["condition"].split(":")[1] for i in keep])
    subspaces = {}
    info = {}
    if len(set(yk.tolist())) >= 2:
        B, modes, _ = basis_from_groups(F[keep].astype(np.float64), yk)
        subspaces["S_gen"] = B.astype(np.float32)
        info["S_gen"] = dict(modes=modes, n_per_mode={m: int((yk == m).sum()) for m in modes}, dim=B.shape[1])
    Hn = np.load(STATES / f"R_named_{task}.npy", mmap_mode="r")[:, li].astype(np.float64)
    yn = np.array([r["condition"].split(":")[1] for r in meta[f"R_named_{task}"]])
    B_R, modes_R, _ = basis_from_groups(Hn, yn)
    subspaces["S_R"] = B_R.astype(np.float32)
    info["S_R"] = dict(modes=modes_R, dim=B_R.shape[1])
    nat = [i for i, r in enumerate(fit_rows) if r["src"] == "A1p" and r["key"] in lab]
    yN = np.array([lab[fit_rows[i]["key"]]["label"] for i in nat])
    cN = Counter(yN.tolist())
    okN = [i for i, y in zip(nat, yN) if cN[y] >= 5]
    if len({y for y in yN.tolist() if cN[y] >= 5}) >= 2:
        BN, modesN, _ = basis_from_groups(F[okN].astype(np.float64),
                                          np.array([lab[fit_rows[i]["key"]]["label"] for i in okN]))
        subspaces["S_nat"] = BN.astype(np.float32)
        info["S_nat"] = dict(modes=modesN, dim=BN.shape[1])
    else:
        info["S_nat"] = dict(skipped=True, reason=f"natural labels have < 2 modes with >= 5 samples: {dict(cN)}")
    sub = X_all.reshape(-1, d)[rng.choice(X_all.shape[0] * X_all.shape[1], min(4000, X_all.shape[0] * 64),
                                          replace=False)]
    _, _, Vt = np.linalg.svd(sub - sub.mean(0), full_matrices=False)
    V50 = Vt[:50].T.astype(np.float32)
    res = dict(layer=int(li), subspaces=info, per_T={}, slopes={})
    for name, B in subspaces.items():
        k = B.shape[1]
        iso = [random_frame(d, k, rng).astype(np.float32) for _ in range(n_null)]
        dmf = [random_frame(d, k, rng, V50).astype(np.float32) for _ in range(n_null)]
        series = {"share": [], "excess_share_dm": [], "excess_share_iso": [], "mode_var": [], "comp_var": []}
        boots = {m: [] for m in ("excess_share_dm", "share", "mode_var", "comp_var")}
        for T in TEMPS:
            X = X_all[Ts == T]
            n = X.shape[0]
            G, P = _gram_stats(X, B)
            W1 = np.ones((1, n))
            tot = _var_from_gram(G, W1)[0]
            mode = _var_from_gram(P, W1)[0]
            share = float(np.mean(mode / tot))
            nulls_iso, nulls_dm = [], []
            for Q in iso[:30]:
                nulls_iso.append(float(np.mean(_var_from_gram(_proj_gram(X, Q), W1)[0] / tot)))
            for Q in dmf:
                nulls_dm.append(float(np.mean(_var_from_gram(_proj_gram(X, Q), W1)[0] / tot)))
            off_dm, off_iso = float(np.median(nulls_dm)), float(np.median(nulls_iso))
            series["share"].append(share)
            series["excess_share_dm"].append(share - off_dm)
            series["excess_share_iso"].append(share - off_iso)
            series["mode_var"].append(float(np.mean(mode)))
            series["comp_var"].append(float(np.mean(tot - mode)))
            W = rng.multinomial(n, np.ones(n) / n, size=n_boot).astype(np.float64)
            bt = _var_from_gram(G, W)
            bm = _var_from_gram(P, W)
            boots["excess_share_dm"].append((bm / bt).mean(1) - off_dm)
            boots["share"].append((bm / bt).mean(1))
            boots["mode_var"].append(bm.mean(1))
            boots["comp_var"].append((bt - bm).mean(1))
            res["per_T"].setdefault(name, {})[str(T)] = dict(
                n=n, share=share, null_median_datamatched=off_dm, null_median_isotropic=off_iso,
                expected_isotropic=k / d, excess_share_dm=share - off_dm, mode_var=float(np.mean(mode)),
                comp_var=float(np.mean(tot - mode)), total_var=float(np.mean(tot)))
        x = np.array(TEMPS)
        xm = x - x.mean()
        for m in ("excess_share_dm", "excess_share_iso", "mode_var", "comp_var", "share"):
            y = np.array(series[m])
            sl = float((xm * (y - y.mean())).sum() / (xm ** 2).sum())
            rec = dict(slope=sl)
            if m in boots:
                Yb = np.stack(boots[m], 1)  # [b, 4]
                sb = ((Yb - Yb.mean(1, keepdims=True)) * xm).sum(1) / (xm ** 2).sum()
                rec["ci95"] = [float(np.quantile(sb, 0.025)), float(np.quantile(sb, 0.975))]
                rec["ci90"] = [float(np.quantile(sb, 0.05)), float(np.quantile(sb, 0.95))]
                rec["p_le0"] = float(np.mean(sb <= 0))
                rec["p_ge0"] = float(np.mean(sb >= 0))
            res["slopes"].setdefault(name, {})[m] = rec
    return res


def synthetic_check(rng) -> dict:
    """Plant a 3-dim subspace whose variance grows with T in isotropic noise; the share slope must be positive."""
    d, n = 512, 50
    B, _ = np.linalg.qr(rng.standard_normal((d, 3)))
    shares, rand_shares = [], []
    R, _ = np.linalg.qr(rng.standard_normal((d, 3)))
    for T in TEMPS:
        X = rng.standard_normal((n, 8, d)) + (rng.standard_normal((n, 8, 3)) * (2.0 * T)) @ B.T
        G, P = _gram_stats(X, B)
        _, Pr = _gram_stats(X, R)
        W1 = np.ones((1, n))
        tot = _var_from_gram(G, W1)[0]
        shares.append(float(np.mean(_var_from_gram(P, W1)[0] / tot)))
        rand_shares.append(float(np.mean(_var_from_gram(Pr, W1)[0] / tot)))
    x = np.array(TEMPS) - np.mean(TEMPS)
    sl = float((x * (np.array(shares) - np.mean(shares))).sum() / (x ** 2).sum())
    slr = float((x * (np.array(rand_shares) - np.mean(rand_shares))).sum() / (x ** 2).sum())
    return dict(planted_share_by_T=shares, planted_slope=sl, random_subspace_slope=slr,
                recovered_sign_positive=bool(sl > 0 and abs(slr) < sl / 10))
