#!/usr/bin/env python3
"""C2a (PRIMARY): does a direction's projection share pi(u) on the plan subspace rank which fresh random plan-site
pushes change the algorithm?

y(u) = off-default share over the FIRST 10 samples (slots k 0-1 x W1-W5) of the POP arm, averaged over alpha 1 and 2
(first-10 rule: no winner's-curse inflation from top-ups). Statistic: within-task one-sided Spearman rho(pi, y),
p from 10,000 shuffles of y.
PASS: rho >= 0.4 and p < 0.01 on >= 4 of 6 movable tasks, AND the same for pi_masked on >= 3 of 6.
DISCONFIRM: rho < 0.2 on most (>= 4 of 6) tasks. Tasks with < 5 directions with y > 0 are flagged 'underpowered'
and still count in the primary (as failures if they fail).
Escape / confirmation: a (task, direction, alpha) passes the screen at N = 10 if excess >= 0.20 over the twin and
pass >= 0.8 x twin; it is CONFIRMED if the pooled 30 (k 0-5) keeps excess >= 0.20 with one-sided exact binomial
p < 0.05 against p0 = (k_twin + 0.5) / (n_twin + 1), and pass >= 0.8 x twin. E_t(alpha) = confirmed / run.
Sensitivities: per alpha; pooled-30 shares; Kendall tau-b; 20/20 split (logistic fit of escape on pi in 20
directions, AUC on the other 20, 200 splits); secondary (pi_masked, s, pi_real, pi_late, pi_R) and control predictors
(pi_wrong, pi_within, gain, pi_whitened, pi_noOutlier); partial Spearman of pi given gain; Haar random-subspace null
rank of rho_pi (1,000 subspaces per block, seed 4242); pooled within-task rho with a task bootstrap; kappa beside it.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from common import auc, binom_greater_p, by_key, kendall, partial_spearman, perm_spearman, share, spearman

PRIMARY_PRED = "pi"
SECONDARY = ["pi_masked", "s", "s_runner_up", "pi_real", "pi_late", "pi_R"]
CONTROLS = ["pi_wrong", "pi_within", "gain", "gain_smean", "pi_whitened", "pi_noOutlier", "pi_adherent"]
RULE = {"rho_min": 0.4, "p_max": 0.01, "n_tasks_pi": 4, "n_tasks_pi_masked": 3, "disconfirm_rho": 0.2,
        "disconfirm_n": 4, "underpowered_min_movers": 5}


def twin_stats(rows: list[dict[str, Any]], cat: set[str], default: str) -> dict[str, Any]:
    return share([r for r in rows if r["arm"] == "TWIN"], cat, default)


def direction_table(rows: list[dict[str, Any]], seeds: list[int], cat: set[str], default: str,
                    alphas=(1.0, 2.0)) -> dict[int, dict[str, Any]]:
    tw = twin_stats(rows, cat, default)
    p0 = (tw["k_off"] + 0.5) / (tw["n_valid"] + 1)
    out = {}
    pop = by_key([r for r in rows if r["family"] == "POP"], "direction_seed", "alpha")
    for s in seeds:
        rec: dict[str, Any] = {}
        ys = []
        for a in alphas:
            rr = pop.get((s, a), [])
            first = [r for r in rr if int(r["sample_id"]) in (0, 1)]
            pooled = [r for r in rr if int(r["sample_id"]) in range(6)]
            f, pl = share(first, cat, default), share(pooled, cat, default)
            screen_pass = (f["n_valid"] > 0 and f["share"] - tw["share"] >= 0.20 - 1e-12 and
                           f["pass"] >= 0.8 * tw["pass"] - 1e-12)
            topped = pl["n"] > f["n"]
            conf = False
            pbin = None
            if screen_pass and topped:
                pbin = binom_greater_p(pl["k_off"], pl["n_valid"], p0)
                conf = (pl["share"] - tw["share"] >= 0.20 - 1e-12 and pbin < 0.05 and
                        pl["pass"] >= 0.8 * tw["pass"] - 1e-12)
            rec[str(a)] = {"first10": f, "pooled": pl, "screen_pass": bool(screen_pass), "topped_up": bool(topped),
                           "binom_p": pbin, "confirmed": bool(conf), "excess_first10": f["share"] - tw["share"],
                           "excess_pooled": pl["share"] - tw["share"]}
            ys.append(f["share"])
        rec["y"] = float(np.nanmean(ys)) if ys else float("nan")
        rec["y_pooled"] = float(np.nanmean([rec[str(a)]["pooled"]["share"] for a in alphas]))
        rec["escape_any"] = any(rec[str(a)]["confirmed"] for a in alphas)
        out[s] = rec
    return out


def haar_null(pred_y: np.ndarray, u: np.ndarray, k: int, n_sub: int = 1000, seed: int = 4242,
              n_blocks: int = 12) -> np.ndarray:
    """rho(pi_rand, y) over random k-dim subspaces (one per block, Haar), pi_rand = mean over blocks."""
    rng = np.random.default_rng(seed)
    D = u.shape[1]
    out = np.zeros(n_sub)
    for i in range(n_sub):
        pis = np.zeros(u.shape[0])
        for _ in range(n_blocks):
            Q = np.linalg.qr(rng.standard_normal((D, k)))[0]
            pis += np.sum((u @ Q) ** 2, 1)
        out[i] = spearman(pis / n_blocks, pred_y)
    return out


def split_auc(x: np.ndarray, esc: np.ndarray, n_split: int = 200, seed: int = 0) -> dict[str, Any]:
    from sklearn.linear_model import LogisticRegression
    rng = np.random.default_rng(seed)
    n = len(x)
    if esc.sum() < 2 or esc.sum() > n - 2:
        return {"auc_mean": float("nan"), "n_splits": 0, "note": "too few escapers/non-escapers"}
    aucs = []
    for _ in range(n_split):
        p = rng.permutation(n)
        tr, te = p[: n // 2], p[n // 2:]
        if esc[tr].sum() == 0 or esc[tr].sum() == len(tr) or esc[te].sum() == 0 or esc[te].sum() == len(te):
            continue
        z = (x - x[tr].mean()) / max(x[tr].std(), 1e-12)
        m = LogisticRegression().fit(z[tr, None], esc[tr])
        aucs.append(auc(m.decision_function(z[te, None]), esc[te]))
    return {"auc_mean": float(np.nanmean(aucs)) if aucs else float("nan"), "n_splits": len(aucs),
            "auc_q05": float(np.nanquantile(aucs, 0.05)) if aucs else float("nan")}


def analyse_task(rows: list[dict[str, Any]], preds: dict[str, dict[str, float]], seeds: list[int], cat: set[str],
                 default: str, U: np.ndarray, k: int, n_perm: int = 10000) -> dict[str, Any]:
    tab = direction_table(rows, seeds, cat, default)
    y = np.array([tab[s]["y"] for s in seeds])
    yp = np.array([tab[s]["y_pooled"] for s in seeds])
    esc = np.array([int(tab[s]["escape_any"]) for s in seeds])
    res: dict[str, Any] = {"n_directions": len(seeds), "n_movers_y_gt_0": int(np.sum(y > 0)),
                           "underpowered": bool(np.sum(y > 0) < RULE["underpowered_min_movers"]),
                           "twin": twin_stats(rows, cat, default), "y": y.tolist(), "escape": esc.tolist()}
    allp = [PRIMARY_PRED] + SECONDARY + CONTROLS
    res["predictors"] = {}
    for nm in allp:
        if nm not in preds[str(seeds[0])]:
            continue
        x = np.array([preds[str(s)][nm] for s in seeds])
        r = perm_spearman(x, y, n_perm=n_perm, seed=1)
        r["kendall_tau_b"] = kendall(x, y)
        r["rho_pooled30"] = spearman(x, yp)
        r["per_alpha"] = {a: spearman(x, np.array([tab[s][a]["first10"]["share"] for s in seeds]))
                          for a in ("1.0", "2.0")}
        res["predictors"][nm] = r
    x = np.array([preds[str(s)]["pi"] for s in seeds])
    if "gain" in preds[str(seeds[0])]:
        g = np.array([preds[str(s)]["gain"] for s in seeds])
        res["partial_spearman_pi_given_gain"] = partial_spearman(x, y, g)
    nul = haar_null(y, U, k)
    res["haar_null"] = {"q95": float(np.quantile(nul, 0.95)), "q99": float(np.quantile(nul, 0.99)),
                        "rank_of_rho_pi": float(np.mean(nul < res["predictors"]["pi"]["rho"]))}
    res["split_auc_pi"] = split_auc(x, esc)
    res["E_t"] = {a: float(np.mean([tab[s][a]["confirmed"] for s in seeds])) for a in ("1.0", "2.0")}
    res["screen_pass_rate"] = {a: float(np.mean([tab[s][a]["screen_pass"] for s in seeds])) for a in ("1.0", "2.0")}
    res["direction_table"] = {str(s): tab[s] for s in seeds}
    return res


def verdict(per_task: dict[str, dict[str, Any]]) -> dict[str, Any]:
    def ok(t, nm):
        r = per_task[t]["predictors"].get(nm)
        return bool(r and r["rho"] >= RULE["rho_min"] and r["p"] < RULE["p_max"])
    n_pi = sum(ok(t, "pi") for t in per_task)
    n_pm = sum(ok(t, "pi_masked") for t in per_task)
    n_low = sum(per_task[t]["predictors"]["pi"]["rho"] < RULE["disconfirm_rho"] for t in per_task)
    evaluable = [t for t in per_task if not per_task[t]["underpowered"]]
    n_pi_eval = sum(ok(t, "pi") for t in evaluable)
    out = {"n_tasks_pi_pass": n_pi, "n_tasks_pi_masked_pass": n_pm, "n_tasks_rho_below_0.2": n_low,
           "PASS": n_pi >= RULE["n_tasks_pi"] and n_pm >= RULE["n_tasks_pi_masked"],
           "DISCONFIRM": n_low >= RULE["disconfirm_n"],
           "evaluable_tasks": evaluable, "n_evaluable_pi_pass": n_pi_eval, "rule": RULE}
    out["reading"] = "PASS" if out["PASS"] else ("DISCONFIRM" if out["DISCONFIRM"] else "INCONCLUSIVE")
    return out
