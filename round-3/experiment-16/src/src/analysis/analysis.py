#!/usr/bin/env python3
"""S9 analysis (CPU). Committed in commit #1 before any ban sample; reads data/samples.jsonl and predictions/*.

9.1 shares per task x arm (+ per template); 9.2 route fractions with a hierarchical bootstrap (task -> template ->
CRN slot, all arms of a slot kept together), BCa, leave-one-task-out jackknife, leave-one-template-out, Bayesian
mixed GLM sensitivity, C2a verdict; 9.3 CRN flip tables (exact McNemar), identical-output rates, first divergence;
9.4 landing by route vs a template->program resampling null; 9.5 C2c; 9.6 C2b sensitivity; 9.7 prefill P_open;
9.8 path screen; 9.9 secondary C1 rows; continuous log-prob companion readout (S8).
"""

from __future__ import annotations

import collections
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cfg import (E8, E9, E12, N_BOOT, N_PERM, PATH_DEFAULT, PATH_SUB, PATH_TASKS, PRED_DIR, RESULTS_DIR, RNG_SEED,  # noqa: E402
                 SAMPLES, STAGE_A, TEMPLATE_IDS, THRESHOLDS, default_of, read_json, read_jsonl, sha256_file,
                 wilson_ci, write_json)

EXCL = ("invalid", "no_code", "disputed")
ROUTE_ARMS = ("a", "b", "c", "d")


# ------------------------------------------------------------------------------------------------ helpers
def load_rows() -> list[dict[str, Any]]:
    rows = read_jsonl(SAMPLES)
    seen = {}
    for r in rows:  # last label wins if a uid was relabelled
        seen[r["uid"]] = r
    return list(seen.values())


def catalogue(task: str) -> list[str]:
    from forecast_s2 import catalogue as cat

    return cat(task)


def survivors(task: str) -> list[str]:
    return [m for m in catalogue(task) if m != default_of(task)] + ["other"]


def hill1(labels: list[str]) -> float:
    if not labels:
        return float("nan")
    c = np.array(list(collections.Counter(labels).values()), float)
    p = c / c.sum()
    return float(np.exp(-(p * np.log(p)).sum()))


def share(rows: list[dict[str, Any]], task: str) -> dict[str, Any]:
    D = default_of(task)
    att = [r for r in rows if r["label"] not in EXCL]
    nd = sum(r["label"] == D for r in att)
    n = len(att)
    lo, hi = wilson_ci(nd, n) if n else (float("nan"), float("nan"))
    nond = [r for r in att if r["label"] != D]
    land = collections.Counter(r["label"] for r in nond)
    corr = collections.Counter(r["label"] for r in nond if r.get("passed"))
    return {"n_rows": len(rows), "n_attempted": n, "n_default": nd, "s": nd / n if n else float("nan"),
            "ci95": [lo, hi], "landing": dict(land), "modal_survivor": land.most_common(1)[0][0] if land else None,
            "correct_landing": dict(corr),
            "other_share": (sum(r["label"] == "other" for r in att) / n) if n else float("nan"),
            "invalid_share": (sum(r["label"] in ("invalid", "no_code") for r in rows) / len(rows)) if rows else float("nan"),
            "disputed": sum(r["label"] == "disputed" for r in rows),
            "pass_rate": float(np.mean([bool(r.get("passed")) for r in rows])) if rows else float("nan"),
            "hill_cc": hill1([r["label"] for r in att if r.get("passed")]),
            "hill_cc_nondefault": hill1([r["label"] for r in nond if r.get("passed")])}


def by(rows: list[dict[str, Any]], *keys: str) -> dict[tuple, list[dict[str, Any]]]:
    out: dict[tuple, list] = collections.defaultdict(list)
    for r in rows:
        out[tuple(r[k] for k in keys)].append(r)
    return out


def js_div(p: np.ndarray, q: np.ndarray) -> float:
    p = p / p.sum()
    q = q / q.sum()
    m = 0.5 * (p + q)

    def kl(a, b):
        mask = a > 0
        return float((a[mask] * np.log2(a[mask] / b[mask])).sum())

    return 0.5 * kl(p, m) + 0.5 * kl(q, m)


def dist_vec(counts: dict[str, int], cats: list[str], pseudo: float = 0.5) -> np.ndarray:
    return np.array([counts.get(c, 0) + pseudo for c in cats], float)


# ------------------------------------------------------------------------------------------------ 9.1
def shares_table(rows: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    g = by(rows, "task", "arm")
    for (t, a), lst in sorted(g.items()):
        out.setdefault(t, {})[a] = share(lst, t)
        per_w = {}
        for w in TEMPLATE_IDS:
            sub = [r for r in lst if r["template"] == w]
            if sub:
                s = share(sub, t)
                per_w[w] = {k: s[k] for k in ("n_attempted", "n_default", "s", "modal_survivor", "pass_rate")}
        out[t][a]["per_template"] = per_w
    return out


# ------------------------------------------------------------------------------------------------ 9.2
def slot_arrays(rows: list[dict[str, Any]], tasks: list[str], arms: tuple[str, ...] = ROUTE_ARMS) -> dict[str, Any]:
    """banned[t, w, k, arm] in {0,1}, att[t, w, k, arm] in {0,1} (attempted)."""
    T, Wn, K, A = len(tasks), len(TEMPLATE_IDS), 20, len(arms)
    ban = np.zeros((T, Wn, K, A), np.int8)
    att = np.zeros((T, Wn, K, A), np.int8)
    idx = {(r["task"], r["template"], r["k"], r["arm"]): r for r in rows}
    for i, t in enumerate(tasks):
        D = default_of(t)
        for j, w in enumerate(TEMPLATE_IDS):
            for k in range(K):
                for a_i, a in enumerate(arms):
                    r = idx.get((t, w, k, a))
                    if r is not None and r["label"] not in EXCL:
                        att[i, j, k, a_i] = 1
                        ban[i, j, k, a_i] = int(r["label"] == D)
    return {"ban": ban, "att": att, "tasks": tasks, "arms": arms}


def fractions_from_counts(nb: np.ndarray, na: np.ndarray, arms: tuple[str, ...]) -> dict[str, np.ndarray]:
    """nb, na: [..., T, A] counts -> pooled (ratio of sums over T) F values [...]."""
    s = nb / np.maximum(na, 1)
    ai = {a: i for i, a in enumerate(arms)}
    sa, sb, sc, sd = (s[..., ai[x]] for x in ("a", "b", "c", "d"))
    den = (sb - sa).sum(-1)
    with np.errstate(divide="ignore", invalid="ignore"):
        Fp = (sb - sc).sum(-1) / den
        Fd = (sb - sd).sum(-1) / den
        out = {"F_prompt": Fp, "F_direct": Fd, "I": 1 - Fp - Fd,
               "F_prompt_mean": np.nanmean((sb - sc) / (sb - sa), -1),
               "F_direct_mean": np.nanmean((sb - sd) / (sb - sa), -1)}
        if "K0" in ai:
            out["F_K0"] = (sb - s[..., ai["K0"]]).sum(-1) / den
    return out


def point_fractions(arr: dict[str, Any]) -> dict[str, float]:
    nb = arr["ban"].sum((1, 2)).astype(float)
    na = arr["att"].sum((1, 2)).astype(float)
    f = fractions_from_counts(nb, na, arr["arms"])
    return {k: float(v) for k, v in f.items()}


def hier_boot(arr: dict[str, Any], n_boot: int = N_BOOT, seed: int = RNG_SEED) -> dict[str, np.ndarray]:
    rng = np.random.default_rng(seed)
    ban, att = arr["ban"], arr["att"]
    T, Wn, K, A = ban.shape
    out = collections.defaultdict(list)
    chunk = 500
    for s in range(0, n_boot, chunk):
        R = min(chunk, n_boot - s)
        ti = rng.integers(0, T, (R, T))
        wi = rng.integers(0, Wn, (R, T, Wn))
        ki = rng.integers(0, K, (R, T, Wn, K))
        tt = ti[:, :, None, None]
        ww = wi[:, :, :, None]
        b = ban[tt, ww, ki]  # [R, T, Wn, K, A]
        a = att[tt, ww, ki]
        nb = b.sum((2, 3)).astype(float)
        na = a.sum((2, 3)).astype(float)
        f = fractions_from_counts(nb, na, arr["arms"])
        for k, v in f.items():
            out[k].append(v)
    return {k: np.concatenate(v) for k, v in out.items()}


def jackknife(arr: dict[str, Any]) -> dict[str, np.ndarray]:
    T = arr["ban"].shape[0]
    res = collections.defaultdict(list)
    for i in range(T):
        keep = [j for j in range(T) if j != i]
        sub = {"ban": arr["ban"][keep], "att": arr["att"][keep], "arms": arr["arms"]}
        for k, v in point_fractions(sub).items():
            res[k].append(v)
    return {k: np.array(v) for k, v in res.items()}


def bca_ci(theta: float, boot: np.ndarray, jack: np.ndarray, alpha: float = 0.05) -> list[float]:
    boot = boot[np.isfinite(boot)]
    if len(boot) < 100 or not np.isfinite(theta) or len(jack) < 3:
        return [float("nan"), float("nan")]
    z0 = stats.norm.ppf(np.clip(np.mean(boot < theta), 1e-6, 1 - 1e-6))
    d = jack.mean() - jack
    den = 6 * (np.sum(d ** 2) ** 1.5)
    a = float(np.sum(d ** 3) / den) if den > 0 else 0.0
    zs = stats.norm.ppf([alpha / 2, 1 - alpha / 2])
    adj = stats.norm.cdf(z0 + (z0 + zs) / (1 - a * (z0 + zs)))
    return [float(np.quantile(boot, adj[0])), float(np.quantile(boot, adj[1]))]


def jack_ci(theta: float, jack: np.ndarray) -> list[float]:
    n = len(jack)
    if n < 3:
        return [float("nan"), float("nan")]
    se = math.sqrt((n - 1) / n * np.sum((jack - jack.mean()) ** 2))
    tq = stats.t.ppf(0.975, n - 1)
    return [theta - tq * se, theta + tq * se]


def pct_ci(boot: np.ndarray) -> list[float]:
    b = boot[np.isfinite(boot)]
    return [float(np.quantile(b, 0.025)), float(np.quantile(b, 0.975))] if len(b) else [float("nan")] * 2


def per_task_route(arr: dict[str, Any], n_boot: int = 4000) -> dict[str, Any]:
    out = {}
    for i, t in enumerate(arr["tasks"]):
        sub = {"ban": arr["ban"][i:i + 1], "att": arr["att"][i:i + 1], "arms": arr["arms"], "tasks": [t]}
        pt = point_fractions(sub)
        rng = np.random.default_rng(RNG_SEED + 7 + i)
        ban, att = sub["ban"][0], sub["att"][0]
        Wn, K, A = ban.shape
        wi = rng.integers(0, Wn, (n_boot, Wn))
        ki = rng.integers(0, K, (n_boot, Wn, K))
        b = ban[wi[:, :, None], ki]
        a = att[wi[:, :, None], ki]
        f = fractions_from_counts(b.sum((1, 2))[:, None, :].astype(float), a.sum((1, 2))[:, None, :].astype(float),
                                  arr["arms"])
        out[t] = {k: {"point": pt[k], "ci95": pct_ci(f[k])} for k in ("F_prompt", "F_direct", "I") + (("F_K0",) if "F_K0" in pt else ())}
        out[t]["N_prompt"] = 1 - pt["F_direct"]
        out[t]["N_direct"] = 1 - pt["F_prompt"]
    return out


def mixed_glm(rows: list[dict[str, Any]], tasks: list[str]) -> dict[str, Any]:
    try:
        import pandas as pd
        from statsmodels.genmod.bayes_mixed_glm import BinomialBayesMixedGLM

        recs = [{"banned": int(r["label"] == default_of(r["task"])), "arm": r["arm"], "task": r["task"],
                 "tt": f"{r['task']}:{r['template']}"} for r in rows
                if r["task"] in tasks and r["arm"] in ROUTE_ARMS and r["label"] not in EXCL]
        df = pd.DataFrame(recs)
        df["arm"] = pd.Categorical(df["arm"], categories=["b", "a", "c", "d"])
        m = BinomialBayesMixedGLM.from_formula("banned ~ C(arm)", {"task": "0 + C(task)", "tt": "0 + C(tt)"}, df)
        fit = m.fit_vb()
        names = list(m.exog_names)
        fe = dict(zip(names, map(float, fit.fe_mean)))
        sd = dict(zip(names, map(float, fit.fe_sd)))
        b0 = fe["Intercept"]
        p = {"b": 1 / (1 + math.exp(-b0))}
        for a in ("a", "c", "d"):
            p[a] = 1 / (1 + math.exp(-(b0 + fe[f"C(arm)[T.{a}]"])))
        Fp = (p["b"] - p["c"]) / (p["b"] - p["a"]) if p["b"] != p["a"] else float("nan")
        Fd = (p["b"] - p["d"]) / (p["b"] - p["a"]) if p["b"] != p["a"] else float("nan")
        return {"fixed_effects_mean": fe, "fixed_effects_sd": sd, "vcp_mean": list(map(float, fit.vcp_mean)),
                "probabilities_at_zero_random_effects": p, "F_prompt_glm": Fp, "F_direct_glm": Fd,
                "note": "descriptive sensitivity (variational Bayes); logit-scale fixed effects at zero random effects"}
    except Exception as e:  # noqa: BLE001 - descriptive sensitivity; record the failure
        logger.exception("mixed GLM failed")
        return {"error": str(e)[:300]}


def route_analysis(rows: list[dict[str, Any]], gated: list[str]) -> dict[str, Any]:
    full = [t for t in gated if all(any(r["task"] == t and r["arm"] == a for r in rows) for a in ROUTE_ARMS)]
    if not full:
        return {"n_tasks": 0, "verdict": "NOT_RUN", "tasks": []}
    arms = ROUTE_ARMS + (("K0",) if all(any(r["task"] == t and r["arm"] == "K0" for r in rows) for t in full) else ())
    arr = slot_arrays(rows, full, arms)
    pt = point_fractions(arr)
    boot = hier_boot(arr)
    jack = jackknife(arr)
    res: dict[str, Any] = {"tasks": full, "n_tasks": len(full), "arms": list(arms), "point": pt, "intervals": {}}
    for k in pt:
        res["intervals"][k] = {"percentile": pct_ci(boot[k]), "bca": bca_ci(pt[k], boot[k], jack[k]),
                               "jackknife": jack_ci(pt[k], jack[k]), "jackknife_values": jack[k].tolist()}
    res["p_boot_F_prompt_le_half"] = float(np.mean(boot["F_prompt"][np.isfinite(boot["F_prompt"])] <= 0.5))
    res["p_boot_F_direct_ge_third"] = float(np.mean(boot["F_direct"][np.isfinite(boot["F_direct"])] >= 1 / 3))
    lot = {}
    for j, w in enumerate(TEMPLATE_IDS):
        keep = [x for x in range(len(TEMPLATE_IDS)) if x != j]
        sub = {"ban": arr["ban"][:, keep], "att": arr["att"][:, keep], "arms": arr["arms"]}
        lot[w] = point_fractions(sub)
    res["leave_one_template_out"] = lot
    verdicts = {}
    for kind in ("percentile", "bca", "jackknife"):
        lo = res["intervals"]["F_prompt"][kind][0]
        sup = bool(pt["F_prompt"] >= THRESHOLDS["F_confirm"] and np.isfinite(lo) and lo > THRESHOLDS["F_ci_lower"])
        dis = bool(pt["F_direct"] >= THRESHOLDS["F_direct_disconfirm"])
        verdicts[kind] = "SUPPORTED" if sup and not dis else ("DISCONFIRMED" if dis and not sup else "MIXED")
    res["verdict_by_interval"] = verdicts
    res["low_cluster"] = len(full) < 6
    # amendment 2 (logged): plan fallback F5 -- with 3-5 gated tasks the pooled estimate is 'low-cluster' and the
    # leave-one-task-out jackknife CI is the primary interval
    res["primary_interval"] = "jackknife" if 3 <= len(full) <= 5 else "percentile"
    res["verdict"] = verdicts[res["primary_interval"]]
    res["per_task"] = per_task_route(arr)
    res["mixed_glm"] = mixed_glm(rows, full)
    res["holm_note"] = "bootstrap p values enter the cross-artifact primary Holm family next round"
    return res


# ------------------------------------------------------------------------------------------------ 9.3
def crn_analysis(rows: list[dict[str, Any]], tasks: list[str]) -> dict[str, Any]:
    idx = {(r["task"], r["template"], r["k"], r["arm"]): r for r in rows}
    ngr = read_json(PRED_DIR / "ngrams.json")
    out = {}
    for t in tasks:
        D = default_of(t)
        res: dict[str, Any] = {"flip_tables": {}, "identical": {}, "first_divergence": {}}
        for X, Y in (("a", "c"), ("a", "d"), ("b", "d"), ("a", "K0"), ("c", "K0"), ("b", "V1"), ("b", "c")):
            n = np.zeros((2, 2), int)
            for w in TEMPLATE_IDS:
                for k in range(20):
                    rx, ry = idx.get((t, w, k, X)), idx.get((t, w, k, Y))
                    if rx is None or ry is None or rx["label"] in EXCL or ry["label"] in EXCL:
                        continue
                    n[int(rx["label"] == D), int(ry["label"] == D)] += 1
            if n.sum() == 0:
                continue
            b01, b10 = int(n[1, 0]), int(n[0, 1])
            p = float(stats.binomtest(min(b01, b10), b01 + b10, 0.5).pvalue) if b01 + b10 > 0 else 1.0
            res["flip_tables"][f"{X}-{Y}"] = {"table[X_banned][Y_banned]": n.tolist(), "X_only": b01, "Y_only": b10,
                                              "mcnemar_exact_p": p, "n_pairs": int(n.sum())}
        for X, Y in (("c", "a"), ("d", "b"), ("V1", "b"), ("K0", "a")):
            same = [idx[(t, w, k, X)]["token_ids"] == idx[(t, w, k, Y)]["token_ids"] for w in TEMPLATE_IDS
                    for k in range(20) if (t, w, k, X) in idx and (t, w, k, Y) in idx]
            if same:
                res["identical"][f"{X}=={Y}"] = float(np.mean(same))
        g = ngr.get(t, {})
        first_occ = []
        for w in TEMPLATE_IDS:
            for k in range(20):
                rb = idx.get((t, w, k, "b"))
                if rb and g.get("defined"):
                    ids = rb["token_ids"]
                    n_ = len(g["ids"])
                    for i in range(len(ids) - n_ + 1):
                        if ids[i:i + n_] == g["ids"]:
                            first_occ.append(i)
                            break
        res["ngram_first_occurrence_in_b"] = {"median": float(np.median(first_occ)) if first_occ else None,
                                               "n": len(first_occ)}
        for X in ("a", "c", "d", "K0", "V1"):
            divs, n_ident = [], 0
            for w in TEMPLATE_IDS:
                for k in range(20):
                    rx, rb = idx.get((t, w, k, X)), idx.get((t, w, k, "b"))
                    if rx is None or rb is None:
                        continue
                    x, b = rx["token_ids"], rb["token_ids"]
                    m = min(len(x), len(b))
                    d = next((i for i in range(m) if x[i] != b[i]), None)
                    if d is None:
                        if len(x) == len(b):
                            n_ident += 1
                            continue
                        d = m
                    divs.append(d)
            if divs or n_ident:
                res["first_divergence"][X] = {"median": float(np.median(divs)) if divs else None,
                                              "iqr": [float(np.quantile(divs, .25)), float(np.quantile(divs, .75))] if divs else None,
                                              "n_diverged": len(divs), "n_identical_to_b": n_ident, "values": divs}
        out[t] = res
    return out


# ------------------------------------------------------------------------------------------------ 9.4
def landing_null(rows_a: list[dict[str, Any]], task: str, n: int, cats: list[str], n_rep: int = 2000,
                 seed: int = RNG_SEED + 2) -> float:
    """q95 of JS(resample of a's non-default attempts at size n, a) -- resampling template then program."""
    D = default_of(task)
    nond = [r for r in rows_a if r["label"] not in EXCL and r["label"] != D]
    if not nond or n <= 0:
        return float("nan")
    byw = collections.defaultdict(list)
    for r in nond:
        byw[r["template"]].append(r["label"])
    ws = sorted(byw)
    full = dist_vec(collections.Counter(r["label"] for r in nond), cats)
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(n_rep):
        labs = []
        for _ in range(n):
            w = ws[rng.integers(len(ws))]
            labs.append(byw[w][rng.integers(len(byw[w]))])
        vals.append(js_div(dist_vec(collections.Counter(labs), cats), full))
    return float(np.quantile(vals, 0.95))


def landing_by_route(rows: list[dict[str, Any]], tasks: list[str]) -> dict[str, Any]:
    g = by(rows, "task", "arm")
    out = {}
    for t in tasks:
        D = default_of(t)
        cats = survivors(t)
        ra = g.get((t, "a"), [])
        ca = collections.Counter(r["label"] for r in ra if r["label"] not in EXCL and r["label"] != D)
        res = {"a": {"counts": dict(ca), "modal": ca.most_common(1)[0][0] if ca else None}}
        for X in ("c", "d", "K0", "V1"):
            rx = g.get((t, X), [])
            cx = collections.Counter(r["label"] for r in rx if r["label"] not in EXCL and r["label"] != D)
            n = sum(cx.values())
            if not n or not ca:
                continue
            js = js_div(dist_vec(cx, cats), dist_vec(ca, cats))
            q95 = landing_null(ra, t, n, cats)
            res[X] = {"counts": dict(cx), "modal": cx.most_common(1)[0][0], "same_modal_as_a": cx.most_common(1)[0][0] == res["a"]["modal"],
                      "JS_vs_a": js, "null_q95": q95, "within_null": bool(js < q95)}
        out[t] = res
    return out


# ------------------------------------------------------------------------------------------------ 9.5 / 9.6
def c2c_analysis(route: dict[str, Any], gated: list[str], c2c: dict[str, Any] | None = None) -> dict[str, Any]:
    if c2c is None:
        if not (PRED_DIR / "c2c.json").exists():
            return {"decision": "NOT_AVAILABLE (commit #2 missing)", "hit_fraction": float("nan"),
                    "spearman_rho": float("nan"), "rows": []}
        c2c = read_json(PRED_DIR / "c2c.json")
    per = route.get("per_task", {})
    rows = []
    for t in STAGE_A:
        cls = c2c.get(t, {}).get("class")
        Fd = per.get(t, {}).get("F_direct", {}).get("point")
        ci = per.get(t, {}).get("F_direct", {}).get("ci95")
        hit = None
        if t in gated and Fd is not None and cls in ("LOW_DIRECT", "HIGH_DIRECT"):
            hit = bool(Fd <= THRESHOLDS["pred_low_direct_F"]) if cls == "LOW_DIRECT" else bool(Fd >= THRESHOLDS["pred_high_direct_F"])
        rows.append({"task": t, "gated": t in gated, "V": c2c.get(t, {}).get("V"), "class": cls, "F_direct": Fd,
                     "F_direct_ci95": ci, "hit": hit, "fire_rate": c2c.get(t, {}).get("fire_rate"),
                     "V_fired": c2c.get(t, {}).get("V_fired")})
    scored = [r for r in rows if r["hit"] is not None]
    hf = float(np.mean([r["hit"] for r in scored])) if scored else float("nan")
    pts = [(r["V"], r["F_direct"]) for r in rows if r["gated"] and r["V"] is not None and r["F_direct"] is not None
           and np.isfinite(r["V"]) and np.isfinite(r["F_direct"])]
    rho = p_perm = float("nan")
    rho_ci = [float("nan"), float("nan")]
    if len(pts) >= 3:
        v = np.array([p[0] for p in pts])
        f = np.array([p[1] for p in pts])
        rho = float(stats.spearmanr(v, f).statistic)
        rng = np.random.default_rng(RNG_SEED + 1)
        rv, rf = stats.rankdata(v), stats.rankdata(f)
        perm = np.array([np.corrcoef(rv, rf[rng.permutation(len(rf))])[0, 1] for _ in range(N_PERM)])
        p_perm = float(np.mean(perm <= rho)) if np.isfinite(rho) else float("nan")
        bs = []
        for _ in range(4000):
            ii = rng.integers(0, len(v), len(v))
            if len(set(ii)) > 2:
                r_ = stats.spearmanr(v[ii], f[ii]).statistic
                if np.isfinite(r_):
                    bs.append(r_)
        rho_ci = pct_ci(np.array(bs)) if bs else rho_ci
    if not scored or not np.isfinite(rho):
        decision = "INCONCLUSIVE (insufficient classed gated tasks)"
    elif hf >= THRESHOLDS["c2c_hit_fraction"] and rho < 0 and p_perm < THRESHOLDS["c2c_alpha"]:
        decision = "SUPPORTED"
    elif rho >= 0 or hf < THRESHOLDS["c2c_disconfirm_hit"]:
        decision = "DISCONFIRMED"
    else:
        decision = "INCONCLUSIVE"
    return {"rows": rows, "n_scored": len(scored), "hit_fraction": hf, "spearman_rho": rho, "perm_p_one_sided": p_perm,
            "rho_task_bootstrap_ci95": rho_ci, "n_points": len(pts), "decision": decision,
            "rule": "SUPPORTED if hit fraction >= 2/3 AND rho < 0 with permutation p < 0.05; DISCONFIRMED if rho >= 0 "
                    "or hit fraction < 1/2; else INCONCLUSIVE (committed in commit #1)"}


def c2b_analysis(rows: list[dict[str, Any]], gated: list[str], c2c: dict[str, Any] | None = None) -> dict[str, Any]:
    if c2c is None:
        if not (PRED_DIR / "c2c.json").exists():
            return {"per_task": {}, "eligible": [], "n_hold": 0, "holds_overall": None, "status": "commit #2 missing"}
        c2c = read_json(PRED_DIR / "c2c.json")
    ngr = read_json(PRED_DIR / "ngrams.json")
    g = by(rows, "task", "arm")
    idx = {(r["task"], r["template"], r["k"], r["arm"]): r for r in rows}
    out, elig = {}, []
    for t in gated:
        V = c2c.get(t, {}).get("V")
        if V is None or not np.isfinite(V) or V < THRESHOLDS["c2b_eligible_V"]:
            continue
        elig.append(t)
        D = default_of(t)
        cov = set(ngr[t].get("co_vetoed") or [])
        cats = [c for c in survivors(t) if c not in cov]
        ra = [r for r in g.get((t, "a"), []) if r["label"] not in cov]
        rv = g.get((t, "V1"), [])
        cv = collections.Counter(r["label"] for r in rv if r["label"] not in EXCL and r["label"] != D and r["label"] not in cov)
        ca = collections.Counter(r["label"] for r in ra if r["label"] not in EXCL and r["label"] != D)
        n = sum(cv.values())
        if not n or not ca:
            out[t] = {"eligible": True, "holds": False, "reason": "no non-default V1 or a attempts"}
            continue
        js = js_div(dist_vec(cv, cats), dist_vec(ca, cats))
        q95 = landing_null(ra, t, n, cats)
        same = cv.most_common(1)[0][0] == ca.most_common(1)[0][0]
        pairs = [(idx[(t, w, k, "V1")]["label"], idx[(t, w, k, "a")]["label"]) for w in TEMPLATE_IDS for k in range(20)
                 if (t, w, k, "V1") in idx and (t, w, k, "a") in idx and idx[(t, w, k, "V1")]["label"] not in EXCL + (D,)
                 and idx[(t, w, k, "a")]["label"] not in EXCL + (D,)]
        agree = float(np.mean([x == y for x, y in pairs])) if pairs else float("nan")
        rng = np.random.default_rng(RNG_SEED + 3)
        null = []
        if pairs:
            xs = [p[0] for p in pairs]
            ys = [p[1] for p in pairs]
            for _ in range(2000):
                perm = rng.permutation(len(ys))
                null.append(np.mean([xs[i] == ys[j] for i, j in enumerate(perm)]))
        out[t] = {"eligible": True, "V": V, "modal_V1": cv.most_common(1)[0][0], "modal_a": ca.most_common(1)[0][0],
                  "same_modal": same, "JS": js, "null_q95": q95, "within_null": bool(js < q95), "holds": bool(same and js < q95),
                  "slot_label_agreement": agree, "permuted_pairing_null_mean": float(np.mean(null)) if null else None,
                  "permuted_pairing_null_q95": float(np.quantile(null, 0.95)) if null else None, "n_pairs": len(pairs)}
    nh = sum(bool(out[t].get("holds")) for t in elig)
    return {"per_task": out, "eligible": elig, "n_hold": nh,
            "holds_overall": bool(elig and nh / len(elig) >= THRESHOLDS["c2b_task_share"]) if elig else None}


# ------------------------------------------------------------------------------------------------ 9.7
def prefill_analysis(shares: dict[str, Any], gated: list[str], rows: list[dict[str, Any]]) -> dict[str, Any]:
    out = {}
    for t in gated:
        s = shares.get(t, {})
        res = {}
        for pf in ("SIG", "NEU"):
            ban, twin = s.get(f"BAN+{pf}"), s.get(f"TWIN+{pf}")
            if ban is None:
                continue
            sa = s["a"]["s"]
            ref = twin["s"] if twin else s["b"]["s"]
            den = ref - sa
            P_open = (ban["s"] - sa) / den if den else float("nan")
            sub = [r for r in rows if r["task"] == t and r["arm"] == f"BAN+{pf}" and r["label"] not in EXCL]
            dead = float(np.mean([r["label"] != default_of(t) for r in sub])) if (sub and pf == "SIG") else None
            res[pf] = {"s_ban_prefill": ban["s"], "s_twin_prefill": twin["s"] if twin else None, "s_a": sa,
                       "P_open": P_open, "reference": "twin+prefill" if twin else "arm b (twin reference missing; flagged)",
                       "dead_opening_rate": dead, "landing_ban_prefill": ban["landing"],
                       "n_ban": ban["n_attempted"], "n_twin": twin["n_attempted"] if twin else None}
        out[t] = res
    return out


# ------------------------------------------------------------------------------------------------ 9.8
def iter2_ban_landings() -> dict[str, Any]:
    """Recompute the iteration-2 ban-draw landings from raw rows (exp8 arm a, exp9 single bans, exp12 fresh pool)."""
    from labelq import label_path_texts

    res = {}
    e8 = [r for r in read_jsonl(E8 / "data" / "samples.jsonl") if r["condition"] == "a"]
    e9 = [r for r in read_jsonl(E9 / "data" / "samples.jsonl") if r["condition"] in ("single:bfs", "single:dijkstra")]
    e12 = read_jsonl(E12 / "results" / "raw" / "c1_fresh_pool.jsonl")
    # amendment 1 (logged): exp12's per-row labels from the same frozen suite labeller (results/labelled_c1.jsonl)
    # are recounted here instead of re-judging (saves ~USD 0.1); a judge-free mechanical relabel of the raw texts is
    # reported as a cross-check on the rows where runtime and AST agree
    e12l = {(r["task"], r["template"], r["sample_id"]): r for r in read_jsonl(E12 / "results" / "labelled_c1.jsonl")}
    mech = label_path_texts([(r["task"], r["text"]) for r in e12], use_judge=False) if e12 else []
    agree = [lab["label"] == e12l[(r["task"], r["template"], r["sample_id"])]["label"] for r, lab in zip(e12, mech)
             if lab["labeller_source"] == "agree" and (r["task"], r["template"], r["sample_id"]) in e12l]
    res["exp12_mechanical_crosscheck"] = {"n_runtime_ast_agree": len(agree),
                                          "agreement_with_exp12_labels": float(np.mean(agree)) if agree else None}
    for t in PATH_TASKS:
        D = PATH_DEFAULT[t]
        labs = ([r["label"] for r in e8 if r["task"] == t] + [r["label"] for r in e9 if r["task"] == t]
                + [e12l[(r["task"], r["template"], r["sample_id"])]["label"] for r in e12
                   if r["task"] == t and (r["task"], r["template"], r["sample_id"]) in e12l])
        att = [x for x in labs if x not in EXCL]
        nond = [x for x in att if x != D]
        c = collections.Counter(nond)
        res[t] = {"n_total": len(labs), "n_attempted": len(att), "n_nondefault": len(nond), "counts": dict(c),
                  "modal": c.most_common(1)[0][0] if c else None,
                  "modal_count": c.most_common(1)[0][1] if c else 0,
                  "sources": {"exp8_arm_a": sum(1 for r in e8 if r["task"] == t),
                              "exp9_single_ban": sum(1 for r in e9 if r["task"] == t),
                              "exp12_c1_fresh_pool": sum(1 for r in e12 if r["task"] == t)}}
    return res


def screen_analysis(rows: list[dict[str, Any]]) -> dict[str, Any]:
    ref = iter2_ban_landings()
    out = {"iteration2_ban_landings": {k: v for k, v in ref.items() if k in PATH_TASKS},
           "exp12_mechanical_crosscheck": ref.get("exp12_mechanical_crosscheck"), "rounds": {}}
    pf = read_json(PRED_DIR / "prefills.json")
    for t in PATH_TASKS:
        D = PATH_DEFAULT[t]
        cats = [m for m in catalogue(t) if m != D] + ["other"]
        res = {}
        last_ok = None
        for arm in ("b", "V1", "VP", "R2", "R3", "OPEN"):
            sub = [r for r in rows if r["task"] == t and r["arm"] == arm]
            if not sub:
                continue
            s = share(sub, t)
            surfaces = []
            for r in sub:
                if r.get("veto_fired") and r.get("gen_text"):
                    lines = [ln for ln in r["gen_text"].split("```python")[-1].splitlines() if ln.strip()][:3]
                    surfaces.append(lines)
            c = collections.Counter(s["landing"])
            refc = collections.Counter(ref[t]["counts"])
            js = js_div(dist_vec(c, cats), dist_vec(refc, cats)) if c and refc else float("nan")
            res[arm] = {**{k: s[k] for k in ("n_attempted", "n_default", "s", "landing", "modal_survivor", "pass_rate",
                                              "correct_landing")},
                        "off_default": 1 - s["s"] if np.isfinite(s["s"]) else float("nan"),
                        "fire_rate": float(np.mean([bool(r.get("veto_fired")) for r in sub])),
                        "mean_redraws": float(np.mean([r.get("n_redraws", 0) for r in sub])),
                        "JS_vs_iter2_ban": js, "same_modal_as_iter2_ban": s["modal_survivor"] == ref[t]["modal"],
                        "reemergence_surfaces": surfaces[:12]}
            if arm in ("V1", "VP", "R2", "R3") and (s["n_attempted"] - s["n_default"]) >= THRESHOLDS["screen_min_nond"]:
                last_ok = arm
        res["SUBTRACT_forecast_round"] = last_ok
        res["SUBTRACT_forecast"] = res[last_ok]["landing"] if last_ok else None
        res["opening_veto_ngram"] = pf[t].get("opening_veto")
        out["rounds"][t] = res
    pred = {}
    t2 = out["rounds"].get("t2", {}).get("V1")
    t1 = out["rounds"].get("t1", {}).get("V1")
    if t2:
        pred["T2_oneshot_suffices_and_lands_bf_spfa"] = {"V": t2["off_default"], "modal": t2["modal_survivor"],
                                                         "hit": bool(t2["off_default"] >= 0.8 and t2["modal_survivor"] == PATH_SUB["t2"])}
    if t1:
        pred["T1_oneshot_does_not_suffice"] = {"V": t1["off_default"], "hit": bool(t1["off_default"] < 0.5)}
    out["committed_predictions"] = pred
    try:
        an = read_json(E8 / "results" / "analysis.json")
        out["exp8_behaviour_route"] = an.get("behaviour", {}).get("per_task")
    except (FileNotFoundError, KeyError, ValueError):
        out["exp8_behaviour_route"] = None
    return out


# ------------------------------------------------------------------------------------------------ 9.9
def smooth(dist: dict[str, float], cats: list[str]) -> dict[str, float]:
    surv = [c for c in cats if c != "other"]
    base = {c: dist.get(c, 0.0) for c in cats}
    tot = sum(base.values())
    p = {c: (base[c] / tot if tot else 1 / len(cats)) for c in cats}
    p = {c: 0.95 * p[c] + (0.05 / len(surv) if c in surv else 0.0) for c in cats}
    if p.get("other", 0) < 0.02:
        scale = 0.98 / sum(v for c, v in p.items() if c != "other")
        p = {c: (v * scale if c != "other" else 0.02) for c, v in p.items()}
    z = sum(p.values())
    return {c: v / z for c, v in p.items()}


def c1_rows(shares: dict[str, Any]) -> list[dict[str, Any]]:
    if not (PRED_DIR / "veto_landings.json").exists():
        return []
    land = read_json(PRED_DIR / "veto_landings.json")
    ap = read_json(PRED_DIR / "associate_proximity.json")
    chain = sha256_file(Path(__file__).resolve().parents[2] / "commitments.log")
    out = []
    for t in STAGE_A:
        a = shares.get(t, {}).get("a")
        if not a or not a["landing"]:
            continue
        cats = survivors(t)
        obs = a["landing"]
        n = sum(obs.values())
        fams = {"SUBTRACT": smooth(land.get(t, {}).get("subtract_oneshot_forecast") or {}, cats),
                "ASSOCIATE": smooth({ap.get(t, {}).get("associate"): 1.0} if ap.get(t, {}).get("associate") else {}, cats),
                "PROXIMITY": smooth({ap.get(t, {}).get("proximity"): 1.0} if ap.get(t, {}).get("proximity") else {}, cats),
                "LADDER": {c: 1 / len(cats) for c in cats}}
        modal = max(obs, key=obs.get)
        rec = {"event": f"{t}|ban:{default_of(t)}", "task": t, "X": default_of(t), "n_nondefault": n, "observed": obs,
               "observed_modal": modal, "families": {}, "commit_sha256": chain,
               "flags": {"SUBTRACT": "oneshot_not_iterated", "LADDER": "undefined_scored_uniform"}}
        tops = {}
        for f, p in fams.items():
            ls = sum(cnt * math.log(p.get(lab if lab in cats else "other", 1e-9)) for lab, cnt in obs.items()) / n
            # amendment 3 (logged): a family whose distribution has tied maxima (LADDER is uniform) has no top-1
            mx = max(p.values())
            ties = [c for c, v in p.items() if abs(v - mx) < 1e-12]
            top = ties[0] if len(ties) == 1 else None
            tops[f] = top
            rec["families"][f] = {"p": p, "logscore_per_event": ls, "top1": top,
                                  "top1_hit": (top == modal) if top is not None else None}
        rec["disagreeing"] = len({tops[f] for f in ("SUBTRACT", "ASSOCIATE", "PROXIMITY")}) > 1
        out.append(rec)
    return out


# ------------------------------------------------------------------------------------------------ S8
def lp_analysis(gated: list[str]) -> dict[str, Any]:
    p = RESULTS_DIR / "lp_readout_raw.json"
    if not p.exists():
        return {"status": "not run"}
    raw = read_json(p)
    out = {}
    num_p = num_d = den = 0.0
    for t, v in raw.items():
        per = {}
        for w, arms in v["per_template"].items():
            lp = {a: arms[a]["sig"] for a in arms}
            d = lp["b"] - lp["a"]
            per[w] = {"lp": lp, "F_lp_prompt": (lp["b"] - lp["c"]) / d if d else float("nan"),
                      "F_lp_direct": (lp["b"] - lp["d"]) / d if d else float("nan"),
                      "F_lp_K0": (lp["b"] - lp["K0"]) / d if d else float("nan")}
            if t in gated:
                num_p += lp["b"] - lp["c"]
                num_d += lp["b"] - lp["d"]
                den += d
        out[t] = {"per_template": per,
                  "mean_F_lp_prompt": float(np.nanmean([x["F_lp_prompt"] for x in per.values()])),
                  "mean_F_lp_direct": float(np.nanmean([x["F_lp_direct"] for x in per.values()]))}
    out["pooled_gated"] = {"F_lp_prompt": num_p / den if den else float("nan"),
                           "F_lp_direct": num_d / den if den else float("nan"),
                           "note": "descriptive companion readout (teacher-forced log-prob of the default's signature prefix)"}
    return out


# ------------------------------------------------------------------------------------------------ main
def run_analysis() -> dict[str, Any]:
    rows = load_rows()
    bench_rows = [r for r in rows if r["task"] in STAGE_A and r["stage"] not in ("U9",)]
    gate = read_json(RESULTS_DIR / "gate.json") if (RESULTS_DIR / "gate.json").exists() else {}
    rm = read_json(RESULTS_DIR / "labeller_recheck.json") if (RESULTS_DIR / "labeller_recheck.json").exists() else {}
    failed = set(rm.get("failed_tasks", []))
    gated = [t for t in STAGE_A if gate.get(t, {}).get("gated") and t not in failed]
    shares = shares_table(bench_rows)
    route = route_analysis(bench_rows, gated)
    nongated = [t for t in STAGE_A if t not in gated]
    route_ng = {}
    if nongated:
        arr = slot_arrays(bench_rows, [t for t in nongated if all((t, a) in by(bench_rows, "task", "arm") for a in ROUTE_ARMS)])
        route_ng = per_task_route(arr) if arr["tasks"] else {}
    crn = crn_analysis(bench_rows, STAGE_A)
    land = landing_by_route(bench_rows, STAGE_A)
    c2c = c2c_analysis(route, gated)
    c2b = c2b_analysis(bench_rows, gated)
    pre = prefill_analysis(shares, gated, bench_rows)
    path_rows = [r for r in rows if r["task"] in PATH_TASKS and r["stage"] != "U9"]
    import os

    skip_screen = os.environ.get("BRT_SKIP_SCREEN") == "1"
    scr = screen_analysis(path_rows) if (path_rows and not skip_screen) else {"status": "not run"}
    c1 = c1_rows(shares)
    lp = lp_analysis(gated)
    ctrl = {}
    for t in STAGE_A[:3]:
        s = shares.get(t, {})
        if "pl" in s and "bB" in s:
            ctrl[t] = {"s_pl": s["pl"]["s"], "s_b_nounB": s["bB"]["s"], "diff": s["pl"]["s"] - s["bB"]["s"],
                       "placebo_pass": bool(abs(s["pl"]["s"] - s["bB"]["s"]) <= THRESHOLDS["placebo_tol"])}
        if "K0b" in s and "b" in s:
            ctrl.setdefault(t, {}).update({"s_K0b": s["K0b"]["s"], "s_b": s["b"]["s"],
                                           "K0b_ratio": s["K0b"]["s"] / s["b"]["s"] if s["b"]["s"] else float("nan"),
                                           "K0b_pass": bool(s["b"]["s"] and s["K0b"]["s"] / s["b"]["s"] >= 0.9)})
    res = {"gated": gated, "gate": gate, "shares": shares, "route": route, "route_nongated_descriptive": route_ng,
           "crn": crn, "landing_by_route": land, "c2c": c2c, "c2b_sensitivity": c2b, "prefill": pre, "screen": scr,
           "controls": ctrl, "lp_readout": lp, "n_rows": len(rows)}
    write_json(RESULTS_DIR / "route.json", {"route": route, "route_nongated_descriptive": route_ng, "gated": gated})
    write_json(RESULTS_DIR / "crn_flips.json", crn)
    write_json(RESULTS_DIR / "landing_by_route.json", land)
    write_json(RESULTS_DIR / "c2c.json", c2c)
    write_json(RESULTS_DIR / "c2b_sensitivity.json", c2b)
    write_json(RESULTS_DIR / "prefill.json", pre)
    write_json(RESULTS_DIR / "screen_paths.json", scr)
    write_json(RESULTS_DIR / "lp_readout.json", lp)
    write_json(RESULTS_DIR / "controls.json", ctrl)
    write_json(RESULTS_DIR / "shares.json", shares)
    from cfg import write_jsonl

    write_jsonl(RESULTS_DIR / "c1_events.jsonl", c1)
    write_json(RESULTS_DIR / "analysis.json", res)
    logger.info(f"analysis: gated={gated}; C2a={route.get('verdict')} point={route.get('point')}; "
                f"C2c={c2c['decision']} (hit {c2c['hit_fraction']}, rho {c2c['spearman_rho']})")
    return res


if __name__ == "__main__":
    from cfg import setup_logging

    setup_logging("analysis")
    run_analysis()
