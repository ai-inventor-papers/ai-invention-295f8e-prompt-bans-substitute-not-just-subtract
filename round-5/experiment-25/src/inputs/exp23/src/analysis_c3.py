#!/usr/bin/env python3
"""FROZEN ANALYSIS (hash-committed in commit #2, before any ban prompt reaches the model).

C3a (primary): per task, A_t = catalogue-only avoidance = #(ban attempts with label in catalogue minus {D}) / N_ban,
C_t = 1[A_t >= 0.5]. Prediction: MOVABLE (E_t > 0) -> predicted to obey (C_t = 1).
  BA = (TPR + TNR) / 2 with positive class C_t = 1; two-sided Fisher exact (one-sided 'greater' too); exact permutation
  Spearman(E_t, A_t) (1e5 permutations, average ranks) with Kendall tau-b beside it.
  Verdict: CONFIRMED iff BA >= 0.8 AND Fisher p < 0.05 AND rho >= 0.5; DISCONFIRMED iff BA <= 0.6; else INCONCLUSIVE.
  Edge cases: all tasks in one compliance class -> BA untestable, Spearman alone; a single predicted class -> BA 0.5
  ('no discrimination'), disconfirming only if both outcome classes exist; ties in E_t -> average ranks.
  Task bootstrap (2,000) CIs for BA and rho; task-label permutation placebo; leave-one-task-out BA and rho;
  conservative primary-family bound min(1, 3p).
Rivals: sign-oriented Spearman with A_t, paired task-bootstrap delta-rho, partial Spearman of E_t given each rival,
  BA of a median-threshold rule (reported, not optimised).
C3b: p' = 0.93 p + 0.05 uniform(survivors) + 0.02 'other'; realised = ban attempts with label not in {D, invalid,
  disputed}; mean log score per event; top-1 hit vs the modal realised catalogue landing (fractional tie credit
  separately; defined-only hit rates); contest: a ban-free forecast (push-landing or ladder) beats association by
  >= 0.10 nats on >= 3 disagreeing events; paired Wilcoxon (Holm over the two comparisons) if >= 10 disagreeing.
C1 (descriptive): correct-only rarefied Hill-1 at depth 25; pass cost = 100 x (pass_twin - pass_arm) floored at 0;
  H5 / P15 / P20 = best correct-only Hill-1 within 5 / 15 / 20 pass points on the randomisation hull of each knob
  class (mixtures twin->setting and between adjacent settings; Monte-Carlo rarefaction at depth 25).
"""

from __future__ import annotations

import collections
import itertools
import math
from typing import Any

import numpy as np
from scipy import stats

SMOOTH = {"f": 0.93, "uniform_S": 0.05, "other": 0.02}
NOT_OFF = ("invalid", "disputed")
N_PERM = 100_000
N_BOOT = 2_000


# ------------------------------------------------------------------------------------------------ basic statistics
def rankdata(x: np.ndarray) -> np.ndarray:
    return stats.rankdata(x, method="average")


def spearman(x: np.ndarray, y: np.ndarray) -> float:
    x, y = np.asarray(x, float), np.asarray(y, float)
    if len(x) < 3 or np.std(x) == 0 or np.std(y) == 0:
        return float("nan")
    rx, ry = rankdata(x), rankdata(y)
    return float(np.corrcoef(rx, ry)[0, 1])


def perm_spearman(x: np.ndarray, y: np.ndarray, n_perm: int = N_PERM, seed: int = 0) -> dict[str, Any]:
    x, y = np.asarray(x, float), np.asarray(y, float)
    rho = spearman(x, y)
    if not np.isfinite(rho):
        return {"rho": None, "p_one_sided": None, "p_two_sided": None, "n": len(x), "note": "constant input"}
    rx, ry = rankdata(x), rankdata(y)
    rx = (rx - rx.mean()) / rx.std()
    ry = (ry - ry.mean()) / ry.std()
    rng = np.random.default_rng(seed)
    perm = np.argsort(rng.random((n_perm, len(x))), axis=1)
    rp = (rx[None, :] * ry[perm]).mean(1)
    return {"rho": rho, "p_one_sided": float((np.sum(rp >= rho - 1e-12) + 1) / (n_perm + 1)),
            "p_two_sided": float((np.sum(np.abs(rp) >= abs(rho) - 1e-12) + 1) / (n_perm + 1)), "n": len(x)}


def kendall(x, y) -> float | None:
    if len(set(x)) < 2 or len(set(y)) < 2:
        return None
    return float(stats.kendalltau(x, y, variant="b").statistic)


def balanced_accuracy(pred: list[int], obs: list[int]) -> dict[str, Any]:
    pred, obs = np.asarray(pred, int), np.asarray(obs, int)
    pos, neg = obs == 1, obs == 0
    out = {"n_pos": int(pos.sum()), "n_neg": int(neg.sum()), "n_pred_pos": int(pred.sum()),
           "n_pred_neg": int((1 - pred).sum())}
    if pos.sum() == 0 or neg.sum() == 0:
        out.update(BA=None, TPR=None, TNR=None, testable=False, note="all tasks in one compliance class")
        return out
    tpr = float((pred[pos] == 1).mean())
    tnr = float((pred[neg] == 0).mean())
    out.update(BA=(tpr + tnr) / 2, TPR=tpr, TNR=tnr, testable=True,
               single_predicted_class=bool(pred.min() == pred.max()))
    return out


def fisher(pred: list[int], obs: list[int]) -> dict[str, Any]:
    pred, obs = np.asarray(pred, int), np.asarray(obs, int)
    tab = [[int(((pred == 1) & (obs == 1)).sum()), int(((pred == 1) & (obs == 0)).sum())],
           [int(((pred == 0) & (obs == 1)).sum()), int(((pred == 0) & (obs == 0)).sum())]]
    if (pred.min() == pred.max()) or (obs.min() == obs.max()):
        return {"table": tab, "p_two_sided": 1.0, "p_greater": 1.0, "note": "degenerate margin"}
    return {"table": tab, "p_two_sided": float(stats.fisher_exact(tab, alternative="two-sided").pvalue),
            "p_greater": float(stats.fisher_exact(tab, alternative="greater").pvalue)}


# ------------------------------------------------------------------------------------------------ C3a
def c3a(tasks: list[str], E: dict[str, float], A: dict[str, float], movable: dict[str, bool] | None = None,
        thresh: float = 0.5, seed: int = 0, n_perm: int = N_PERM, n_boot: int = N_BOOT) -> dict[str, Any]:
    tasks = [t for t in tasks if t in E and t in A and E[t] is not None and A[t] is not None]
    e = np.array([E[t] for t in tasks], float)
    a = np.array([A[t] for t in tasks], float)
    mv = np.array([int((movable or {}).get(t, E[t] > 0)) for t in tasks])
    C = (a >= thresh).astype(int)
    ba = balanced_accuracy(mv, C)
    fi = fisher(mv, C)
    sp = perm_spearman(e, a, n_perm=n_perm, seed=seed)
    kt = kendall(list(e), list(a))
    rho = sp["rho"]
    if not ba["testable"]:
        verdict = "UNTESTABLE_BA (Spearman alone)"
        if rho is not None:
            verdict += f": rho={rho:.3f}"
    else:
        b = ba["BA"]
        if b >= 0.8 and fi["p_two_sided"] < 0.05 and rho is not None and rho >= 0.5:
            verdict = "CONFIRMED"
        elif b <= 0.6:
            verdict = "DISCONFIRMED"
        else:
            verdict = "INCONCLUSIVE"
    rng = np.random.default_rng(seed + 1)
    bb, br = [], []
    for _ in range(n_boot):
        idx = rng.integers(0, len(tasks), len(tasks))
        r = balanced_accuracy(mv[idx], C[idx])
        if r["BA"] is not None:
            bb.append(r["BA"])
        rr = spearman(e[idx], a[idx])
        if np.isfinite(rr):
            br.append(rr)
    boot = {"BA_ci95": [float(np.quantile(bb, 0.025)), float(np.quantile(bb, 0.975))] if bb else None,
            "rho_ci95": [float(np.quantile(br, 0.025)), float(np.quantile(br, 0.975))] if br else None,
            "n_valid_BA": len(bb), "n_valid_rho": len(br)}
    # task-label permutation placebo: shuffle the outcome across tasks
    rng = np.random.default_rng(seed + 2)
    pl_ba, pl_rho = [], []
    for _ in range(2000):
        p = rng.permutation(len(tasks))
        r = balanced_accuracy(mv, C[p])
        if r["BA"] is not None:
            pl_ba.append(r["BA"])
        rr = spearman(e, a[p])
        if np.isfinite(rr):
            pl_rho.append(rr)
    placebo = {"BA_mean": float(np.mean(pl_ba)) if pl_ba else None,
               "BA_p_ge_observed": (float(np.mean(np.array(pl_ba) >= ba["BA"] - 1e-12)) if (pl_ba and ba["BA"] is not None)
                                    else None),
               "rho_mean": float(np.mean(pl_rho)) if pl_rho else None}
    loo = {}
    for i, t in enumerate(tasks):
        m = np.arange(len(tasks)) != i
        r = balanced_accuracy(mv[m], C[m])
        loo[t] = {"BA": r["BA"], "rho": spearman(e[m], a[m])}
    p_raw = fi["p_two_sided"]
    return {"tasks": tasks, "E_t": dict(zip(tasks, e.tolist())), "A_t": dict(zip(tasks, a.tolist())),
            "movable": dict(zip(tasks, mv.tolist())), "C_t": dict(zip(tasks, C.tolist())), "balanced_accuracy": ba,
            "fisher": fi, "spearman": sp, "kendall_tau_b": kt, "verdict": verdict, "fisher_p_raw": p_raw,
            "fisher_p_bonferroni3": min(1.0, 3 * p_raw), "bootstrap": boot, "placebo_task_permutation": placebo,
            "leave_one_task_out": loo}


# ------------------------------------------------------------------------------------------------ rivals
def partial_spearman(x, y, z) -> float | None:
    x, y, z = (rankdata(np.asarray(v, float)) for v in (x, y, z))
    if np.std(z) == 0:
        return spearman(x, y)
    rxy, rxz, ryz = (np.corrcoef(p, q)[0, 1] for p, q in ((x, y), (x, z), (y, z)))
    den = math.sqrt(max(1e-12, (1 - rxz ** 2) * (1 - ryz ** 2)))
    v = (rxy - rxz * ryz) / den
    return float(v) if np.isfinite(v) else None


def rivals(tasks: list[str], E: dict[str, float], A: dict[str, float], R: dict[str, dict[str, float | None]],
           sign: dict[str, int], seed: int = 0, n_boot: int = N_BOOT) -> dict[str, Any]:
    out = {}
    for name, vals in R.items():
        tt = [t for t in tasks if vals.get(t) is not None and E.get(t) is not None and A.get(t) is not None]
        if len(tt) < 4:
            out[name] = {"n": len(tt), "note": "too few defined tasks"}
            continue
        e = np.array([E[t] for t in tt])
        a = np.array([A[t] for t in tt])
        r = sign.get(name, 1) * np.array([vals[t] for t in tt], float)
        rho_r, rho_e = spearman(r, a), spearman(e, a)
        rng = np.random.default_rng(seed + hash(name) % 1000)
        d = []
        for _ in range(n_boot):
            idx = rng.integers(0, len(tt), len(tt))
            x1, x2 = spearman(e[idx], a[idx]), spearman(r[idx], a[idx])
            if np.isfinite(x1) and np.isfinite(x2):
                d.append(x1 - x2)
        med = np.median(r)
        pred = (r > med).astype(int)
        C = (a >= 0.5).astype(int)
        out[name] = {"n": len(tt), "rho_rival_sign_oriented": rho_r, "rho_E_t_same_tasks": rho_e,
                     "delta_rho": (rho_e - rho_r) if (np.isfinite(rho_e) and np.isfinite(rho_r)) else None,
                     "delta_rho_ci95": [float(np.quantile(d, 0.025)), float(np.quantile(d, 0.975))] if d else None,
                     "partial_spearman_E_given_rival": partial_spearman(e, a, r),
                     "median_threshold_BA": balanced_accuracy(pred, C)["BA"], "sign": sign.get(name, 1)}
    return out


# ------------------------------------------------------------------------------------------------ C3b
def smooth(p: dict[str, float], S: list[str]) -> dict[str, float]:
    out = {m: SMOOTH["f"] * p.get(m, 0.0) + SMOOTH["uniform_S"] / len(S) for m in S}
    out["other"] = SMOOTH["other"]
    return out


def log_score(p: dict[str, float], labels: list[str], S: list[str]) -> float | None:
    ps = smooth(p, S)
    xs = [math.log(ps.get(l if l in S else "other", ps["other"])) for l in labels]
    return float(np.mean(xs)) if xs else None


def top1_hit(top: str | None, labels: list[str], S: list[str]) -> dict[str, Any]:
    c = collections.Counter(l for l in labels if l in S)
    if not c or top is None:
        return {"hit": None, "frac": None, "modal": sorted(c)[:1] if c else None}
    mx = max(c.values())
    modal = sorted(m for m, v in c.items() if v == mx)
    return {"hit": int(top in modal and len(modal) == 1) if len(modal) == 1 else int(top in modal),
            "frac": (1 / len(modal)) if top in modal else 0.0, "modal": modal}


def c3b(events: dict[str, dict[str, Any]], seed: int = 0) -> dict[str, Any]:
    """events[t] = {'S': survivors, 'labels': realised ban labels (not D/invalid/disputed), 'forecasts':
    {name: {'distribution', 'top1', 'defined'}}}."""
    names = ["push_landing", "opening_ladder", "association", "proximity"]
    per = {}
    for t, ev in events.items():
        S, labs = ev["S"], ev["labels"]
        row = {"n_realised": len(labs), "realised": dict(collections.Counter(labs))}
        for nm in names:
            f = ev["forecasts"].get(nm) or {}
            dist = f.get("distribution") if f.get("defined") else {m: 1 / len(S) for m in S}
            row[nm] = {"log_score": log_score(dist or {}, labs, S), "defined": bool(f.get("defined")),
                       **top1_hit(f.get("top1") if f.get("defined") else None, labs, S)}
        per[t] = row
    summ = {}
    for nm in names:
        ls = [v[nm]["log_score"] for v in per.values() if v[nm]["log_score"] is not None]
        hits = [v[nm]["hit"] for v in per.values() if v[nm]["hit"] is not None and v[nm]["defined"]]
        frac = [v[nm]["frac"] for v in per.values() if v[nm]["frac"] is not None and v[nm]["defined"]]
        summ[nm] = {"mean_log_score": float(np.mean(ls)) if ls else None, "n_events": len(ls),
                    "n_defined": sum(1 for v in per.values() if v[nm]["defined"]),
                    "defined_only_hit_rate": float(np.mean(hits)) if hits else None,
                    "fractional_tie_credit": float(np.mean(frac)) if frac else None}
    contest = {}
    pvals = {}
    for nm in ("push_landing", "opening_ladder"):
        dis = [t for t, v in per.items() if v[nm]["log_score"] is not None and v["association"]["log_score"] is not None
               and (events[t]["forecasts"].get(nm) or {}).get("top1") != (events[t]["forecasts"].get("association")
                                                                           or {}).get("top1")]
        diffs = [per[t][nm]["log_score"] - per[t]["association"]["log_score"] for t in dis]
        md = float(np.mean(diffs)) if diffs else None
        res = {"n_disagreeing": len(dis), "mean_diff_vs_association": md,
               "wins": bool(md is not None and md >= 0.10 and len(dis) >= 3),
               "association_wins": bool(md is not None and md <= -0.10 and len(dis) >= 3)}
        if len(dis) >= 10:
            w = stats.wilcoxon(diffs)
            res["wilcoxon_p"] = float(w.pvalue)
            pvals[nm] = float(w.pvalue)
        contest[nm] = res
    if pvals:
        order = sorted(pvals, key=pvals.get)
        for i, nm in enumerate(order):
            contest[nm]["wilcoxon_p_holm"] = min(1.0, pvals[nm] * (len(order) - i))
    # shuffled-forecast placebo: forecasts permuted across events (same survivor sets only)
    rng = np.random.default_rng(seed)
    pl = {}
    ts = list(events)
    for nm in names:
        vals = []
        for _ in range(200):
            perm = rng.permutation(len(ts))
            s = []
            for i, t in enumerate(ts):
                src = events[ts[perm[i]]]["forecasts"].get(nm) or {}
                S = events[t]["S"]
                d = src.get("distribution") if src.get("defined") else None
                d = {m: (d or {}).get(m, 0.0) for m in S}
                tot = sum(d.values())
                d = {m: v / tot for m, v in d.items()} if tot > 0 else {m: 1 / len(S) for m in S}
                x = log_score(d, events[t]["labels"], S)
                if x is not None:
                    s.append(x)
            if s:
                vals.append(np.mean(s))
        pl[nm] = float(np.mean(vals)) if vals else None
    return {"per_event": per, "summary": summ, "contest": contest, "placebo_shuffled_mean_log_score": pl,
            "verdict": ("CONFIRMED" if any(c["wins"] for c in contest.values()) else
                        "DISCONFIRMED" if all(c.get("association_wins") for c in contest.values() if c["n_disagreeing"])
                        and any(c["n_disagreeing"] for c in contest.values()) else "INCONCLUSIVE")}


# ------------------------------------------------------------------------------------------------ C1 (descriptive)
def hill1(labels: list[str]) -> float:
    c = np.array(list(collections.Counter(labels).values()), float)
    if c.sum() == 0:
        return float("nan")
    p = c / c.sum()
    return float(np.exp(-(p * np.log(p)).sum()))


def rarefied_hill(labels: list[str], depth: int = 25, n_sub: int = 1000, seed: int = 0) -> dict[str, Any]:
    if not labels:
        return {"hill": None, "depth": 0, "flag": "no correct programs"}
    rng = np.random.default_rng(seed)
    d = min(depth, len(labels))
    arr = np.array(labels)
    hs = [hill1(list(arr[rng.choice(len(arr), d, replace=False)])) for _ in range(n_sub)]
    return {"hill": float(np.mean(hs)), "depth": d, "flag": None if d == depth else f"own depth {d}"}


def mc_hill(dist: dict[str, float], depth: int = 25, n_sub: int = 300, rng=None) -> float:
    rng = rng or np.random.default_rng(0)
    ks = list(dist)
    p = np.array([dist[k] for k in ks], float)
    if p.sum() <= 0:
        return float("nan")
    p /= p.sum()
    draws = rng.multinomial(depth, p, size=n_sub)
    q = draws / depth
    with np.errstate(divide="ignore", invalid="ignore"):
        h = -np.nansum(np.where(q > 0, q * np.log(q), 0.0), axis=1)
    return float(np.mean(np.exp(h)))


def arm_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    corr = [r["label"] for r in rows if r.get("passed")]
    pr = len(corr) / n if n else float("nan")
    comp = collections.Counter(corr)
    return {"n": n, "pass": pr, "correct_comp": dict(comp), "attempt_comp": dict(collections.Counter(r["label"] for r in rows))}


def hull_best(twin: dict[str, Any], settings: list[dict[str, Any]], budget_points: float, depth: int = 25,
              grid: int = 21, seed: int = 0) -> dict[str, Any]:
    """Best correct-only Hill-1 on the randomisation hull (twin -> s1 -> s2 ...) within `budget_points` pass points."""
    rng = np.random.default_rng(seed)
    chain = [twin] + settings
    best = {"hill": None, "segment": None, "lambda": None, "cost": None}
    pt = twin["pass"]
    for i in range(len(chain) - 1):
        a, b = chain[i], chain[i + 1]
        for lam in np.linspace(0, 1, grid):
            pas = (1 - lam) * a["pass"] + lam * b["pass"]
            cost = max(0.0, 100 * (pt - pas))
            if cost > budget_points + 1e-9:
                continue
            mix = collections.Counter()
            for comp, w in ((a["correct_comp"], (1 - lam) * a["pass"]), (b["correct_comp"], lam * b["pass"])):
                tot = sum(comp.values())
                for k, v in comp.items():
                    mix[k] += w * v / tot if tot else 0.0
            if sum(mix.values()) <= 0:
                continue
            h = mc_hill(dict(mix), depth, rng=rng)
            if best["hill"] is None or h > best["hill"]:
                best = {"hill": h, "segment": i, "lambda": float(lam), "cost": cost}
    return best


def bootstrap_hull(arms: dict[str, list[dict[str, Any]]], knob: list[str], budget: float, n_boot: int = 200,
                   seed: int = 0) -> list[float] | None:
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(n_boot):
        res = {}
        for k in ["twin"] + knob:
            rr = arms[k]
            res[k] = arm_summary([rr[i] for i in rng.integers(0, len(rr), len(rr))])
        b = hull_best(res["twin"], [res[k] for k in knob], budget, grid=11, seed=int(rng.integers(1e9)))
        if b["hill"] is not None:
            vals.append(b["hill"])
    if not vals:
        return None
    return [float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975))]


def shingles(code: str, n: int = 4) -> set[tuple[str, ...]]:
    import ast

    try:
        tree = ast.parse(code)
    except SyntaxError:
        return set()
    names: dict[str, str] = {}
    toks = []
    for node in ast.walk(tree):
        t = type(node).__name__
        if isinstance(node, ast.Name):
            names.setdefault(node.id, f"v{len(names)}")
            t += ":" + names[node.id]
        toks.append(t)
    return {tuple(toks[i:i + n]) for i in range(max(0, len(toks) - n + 1))}


def phrasing_clusters(codes: list[str], theta: float) -> int:
    sh = [shingles(c) for c in codes]
    n = len(sh)
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for i, j in itertools.combinations(range(n), 2):
        if not sh[i] or not sh[j]:
            continue
        jac = len(sh[i] & sh[j]) / len(sh[i] | sh[j])
        if jac >= theta:
            parent[find(i)] = find(j)
    return len({find(i) for i in range(n)})


# ------------------------------------------------------------------------------------------------ self-tests
def self_test() -> dict[str, Any]:
    """Synthetic tables with known answers (testing plan T5/T6)."""
    out = {}
    tasks = [f"t{i}" for i in range(15)]
    E = {t: (0.5 if i < 6 else 0.0) for i, t in enumerate(tasks)}
    A = {t: (0.9 if i < 6 else 0.1) for i, t in enumerate(tasks)}
    r = c3a(tasks, E, A, n_perm=20000, n_boot=300)
    out["perfect"] = {"BA": r["balanced_accuracy"]["BA"], "verdict": r["verdict"], "fisher": r["fisher"]["p_two_sided"]}
    assert r["balanced_accuracy"]["BA"] == 1.0 and r["verdict"] == "CONFIRMED", r["verdict"]
    E2 = {t: 0.0 for t in tasks}
    r2 = c3a(tasks, E2, A, n_perm=2000, n_boot=100)
    out["all_immovable"] = {"BA": r2["balanced_accuracy"]["BA"], "verdict": r2["verdict"]}
    assert r2["balanced_accuracy"]["BA"] == 0.5 and r2["verdict"] == "DISCONFIRMED"
    A3 = {t: 0.9 for t in tasks}
    r3 = c3a(tasks, E, A3, n_perm=2000, n_boot=100)
    out["one_outcome_class"] = r3["verdict"]
    assert r3["verdict"].startswith("UNTESTABLE")
    rng = np.random.default_rng(5)
    ps = []
    for k in range(40):
        Er = {t: float(rng.random()) for t in tasks}
        Ar = {t: float(rng.random()) for t in tasks}
        ps.append(perm_spearman(np.array(list(Er.values())), np.array(list(Ar.values())), n_perm=2000, seed=k)
                  ["p_one_sided"])
    out["null_p_mean"] = float(np.mean(ps))
    assert 0.3 < np.mean(ps) < 0.7, np.mean(ps)
    S = ["a", "b", "c"]
    ev = {"e1": {"S": S, "labels": ["a"] * 9 + ["b"], "forecasts": {
        "push_landing": {"defined": True, "distribution": {"a": 0.9, "b": 0.05, "c": 0.05}, "top1": "a"},
        "association": {"defined": True, "distribution": {"a": 0.1, "b": 0.8, "c": 0.1}, "top1": "b"}}}}
    for i in range(2, 5):
        ev[f"e{i}"] = ev["e1"]
    c = c3b(ev)
    out["c3b_contest"] = c["contest"]["push_landing"]
    assert c["contest"]["push_landing"]["wins"]
    out["hill_uniform4"] = hill1(["a", "b", "c", "d"])
    assert abs(out["hill_uniform4"] - 4) < 1e-9
    tw = {"pass": 1.0, "correct_comp": {"x": 50}}
    s1 = {"pass": 0.9, "correct_comp": {"x": 25, "y": 20}}
    hb = hull_best(tw, [s1], 5)
    out["hull_h5"] = hb
    assert hb["cost"] <= 5 + 1e-9 and hb["hill"] > 1.0
    return out
