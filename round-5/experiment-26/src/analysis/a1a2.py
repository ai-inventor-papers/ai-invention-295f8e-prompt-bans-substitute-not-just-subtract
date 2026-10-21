#!/usr/bin/env python3
"""Frozen A1/A2 analysis for panel B (plan section 11). Hash-committed before the first push sample of any unit.

Inputs : predictions/units/<u>.json (committed predictions), data/labels.jsonl + data/judge_labels.jsonl (outcomes,
         through src/labels_view.py), units/<u>/catalogue_frozen.json.
Outputs: results/a1_panel.json, results/a2_panel.json, results/rivals.json, results/repertoire_check.json,
         results/units_table.csv, pooled_inputs.json (schema iter5_panel_v1).

A1 (descriptive within this panel): rho = Spearman(beta_u, E_u) (average ranks) over gated units with a default;
exact one-sided permutation p (full enumeration when n <= 9, else 10,000 shuffles); unit bootstrap 95% CI (10,000);
secondary Spearman(beta_u, PN_excess_u); share of beta < 0.05 units with E = 0 (Clopper-Pearson CI); 2x3 table;
partial Spearman controlling K_u; each rival's Spearman with E and the paired bootstrap rho difference; sensitivities
(attempt beta, plain beta, uncertain-class exclusion, B2 split label); shuffled-beta placebo (1,000).
A2: events = movable units with beta >= 0.05 and a defined push landing; top-1 hit (r_u == landing; tie -> 1/|tie|),
chance 1/(K_u - 1), exact Poisson-binomial p; per-event log score under BASE / ASSOC / PROX (mean over correct
off-default landing programs pooled over confirmed escapes); paired differences (exact Wilcoxon if >= 5 events);
Jensen-Shannon(landing, base composition).
"""

from __future__ import annotations

import csv
import itertools
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cfg5 import ALPHAS, ESC_PASS_FRAC, PRED_DIR, RESULTS_DIR, read_json, utc_now, write_json  # noqa: E402
from labels_view import EXCLUDE, direction_table, final_rows, frozen_catalogue, summarise  # noqa: E402

RNG = np.random.default_rng(5)
UNIT_IDS = ["B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B9"]


def rankdata(x: list[float]) -> np.ndarray:
    return stats.rankdata(np.asarray(x, dtype=float), method="average")


def spearman(x: list[float], y: list[float]) -> float | None:
    if len(x) < 3:
        return None
    rx, ry = rankdata(x), rankdata(y)
    if np.std(rx) == 0 or np.std(ry) == 0:
        return None
    return float(np.corrcoef(rx, ry)[0, 1])


def perm_p(x: list[float], y: list[float], n_shuffle: int = 10000) -> dict[str, Any]:
    """Exact one-sided (greater) permutation p for Spearman rho: full enumeration if n <= 9."""
    r0 = spearman(x, y)
    if r0 is None:
        return {"rho": None, "p": None, "method": "undefined (constant ranks or n < 3)"}
    n = len(x)
    rx, ry = rankdata(x), rankdata(y)
    if n <= 9:
        perms = np.array(list(itertools.permutations(range(n))))
        ys = ry[perms]
        rxc = rx - rx.mean()
        ysc = ys - ys.mean(axis=1, keepdims=True)
        rr = (ysc @ rxc) / (np.sqrt((ysc ** 2).sum(axis=1)) * np.sqrt((rxc ** 2).sum()))
        p = float((rr >= r0 - 1e-12).mean())
        return {"rho": r0, "p": p, "method": f"exact enumeration ({len(perms)} permutations)", "n": n}
    cnt = 0
    for _ in range(n_shuffle):
        r = spearman(x, list(RNG.permutation(y)))
        cnt += (r is not None and r >= r0 - 1e-12)
    return {"rho": r0, "p": (cnt + 1) / (n_shuffle + 1), "method": f"{n_shuffle} shuffles", "n": n}


def boot_ci(x: list[float], y: list[float], n_boot: int = 10000) -> list[float] | None:
    n = len(x)
    if n < 3:
        return None
    xs, ys = np.asarray(x), np.asarray(y)
    vals = []
    for _ in range(n_boot):
        idx = RNG.integers(0, n, n)
        r = spearman(list(xs[idx]), list(ys[idx]))
        if r is not None:
            vals.append(r)
    if len(vals) < 100:
        return None
    return [float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975))]


def partial_spearman(x: list[float], y: list[float], z: list[float]) -> float | None:
    if len(x) < 4:
        return None
    rx, ry, rz = rankdata(x), rankdata(y), rankdata(z)
    if np.std(rz) == 0:
        return spearman(x, y)

    def resid(a):
        A = np.vstack([rz, np.ones_like(rz)]).T
        coef, *_ = np.linalg.lstsq(A, a, rcond=None)
        return a - A @ coef
    ex, ey = resid(rx), resid(ry)
    if np.std(ex) == 0 or np.std(ey) == 0:
        return None
    return float(np.corrcoef(ex, ey)[0, 1])


def clopper_pearson(k: int, n: int, a: float = 0.05) -> list[float] | None:
    if n == 0:
        return None
    lo = 0.0 if k == 0 else float(stats.beta.ppf(a / 2, k, n - k + 1))
    hi = 1.0 if k == n else float(stats.beta.ppf(1 - a / 2, k + 1, n - k))
    return [lo, hi]


def poisson_binomial_sf(hits: float, probs: list[float]) -> float | None:
    """P(X >= hits) for X = sum of independent Bernoulli(p_i) (hits may be fractional under ties: ceil)."""
    if not probs:
        return None
    dist = np.zeros(len(probs) + 1)
    dist[0] = 1.0
    for p in probs:
        dist[1:] = dist[1:] * (1 - p) + dist[:-1] * p
        dist[0] *= (1 - p)
    k = int(math.ceil(hits - 1e-9))
    return float(dist[k:].sum())


def js_divergence(p: dict[str, float], q: dict[str, float]) -> float | None:
    keys = sorted(set(p) | set(q))
    P = np.array([p.get(k, 0.0) for k in keys], dtype=float)
    Q = np.array([q.get(k, 0.0) for k in keys], dtype=float)
    if P.sum() == 0 or Q.sum() == 0:
        return None
    P, Q = P / P.sum(), Q / Q.sum()
    M = (P + Q) / 2

    def kl(a, b):
        m = a > 0
        return float((a[m] * np.log(a[m] / b[m])).sum())
    return 0.5 * kl(P, M) + 0.5 * kl(Q, M)


def hill1(labels: list[str]) -> float | None:
    c = Counter(labels)
    n = sum(c.values())
    if n == 0:
        return None
    return math.exp(-sum(v / n * math.log(v / n) for v in c.values()))


def rarefied(labels: list[str], depth: int = 25, n_sub: int = 1000) -> float | None:
    if len(labels) < depth:
        return hill1(labels)
    arr = np.array(labels)
    return float(np.mean([hill1(list(RNG.choice(arr, size=depth, replace=False))) for _ in range(n_sub)]))


# ------------------------------------------------------------------------------------------------ outcomes
def unit_outcomes(u: str, pred: dict[str, Any]) -> dict[str, Any]:
    d = pred["default"] if pred["default"] != "NO_DEFAULT" else None
    rows = final_rows(u)
    tab = direction_table(u, rows=rows, d=d)
    cat = set(frozen_catalogue(u))
    tw = tab["twin"]
    pn_cells, pn_ex, pn_ex_unc = {}, [], []
    for a in ALPHAS:
        rr = [r for r in rows if r["arm"] == f"PN_a{a}" and r["slot"] in range(10)]
        if not rr:
            continue
        S = summarise(rr, cat, d)
        pn_cells[str(a)] = S
        if S["share"] is not None and tw["share"] is not None:
            ex = S["share"] - tw["share"]
            pn_ex_unc.append(ex)
            if S["pass"] >= ESC_PASS_FRAC * tw["pass"] - 1e-12:
                pn_ex.append(ex)
    t13 = [r for r in rows if r["arm"] == "T13" and r["slot"] in range(10)]
    pooled_esc = [r for r in rows if r["family"] == "ESC"]
    base_corr = [r["label"] for r in rows if r["arm"] == "BASE" and r["slot"] < 40 and r["passed"]
                 and r["label"] != "disputed"]
    pn_corr = [r["label"] for r in rows if r["family"] == "PN" and r["passed"]]
    esc_corr = [r["label"] for r in pooled_esc if r["passed"]]
    support_viol = Counter(l for l in pn_corr + esc_corr if l in cat and l != d and l not in set(base_corr))
    per_dir = [{"arm": arm, "seed": c["seed"], "alpha": c["alpha"],
                "stage1_share": c["stage1"]["share"], "stage1_pass": c["stage1"]["pass"],
                "stage1_n_valid": c["stage1"]["n_valid"], "stage1_passed": c["stage1_pass"],
                "confirmed": c["confirmed"], "excess_stage1": c["excess_stage1"],
                "excess_pooled": c["excess_pooled"], "p": c["p"]} for arm, c in tab["cells"].items()]
    return {"E_by_alpha": tab["E_by_alpha"], "E_u": tab["E_u"], "movable": tab["movable"], "per_direction": per_dir,
            "push_landing": tab["push_landing"], "push_landing_tie": tab.get("push_landing_tie"),
            "push_landing_composition": tab["push_landing_composition"], "twin_cell": tw,
            "pn_cells": pn_cells, "PN_excess_u": max(pn_ex) if pn_ex else 0.0,
            "PN_excess_u_unconstrained": max(pn_ex_unc) if pn_ex_unc else None,
            "t13_cell": summarise(t13, cat, d) if t13 else None,
            "repertoire": {"base_hill1_rarefied": rarefied(base_corr), "pn_hill1_rarefied": rarefied(pn_corr),
                           "escape_hill1_rarefied": rarefied(esc_corr), "n_base_correct": len(base_corr),
                           "n_pn_correct": len(pn_corr), "n_escape_correct": len(esc_corr),
                           "support_violations": dict(support_viol)},
            "n_push_rows": len(pooled_esc)}


def load_units() -> list[tuple[str, dict[str, Any]]]:
    out = []
    for u in UNIT_IDS:
        p = PRED_DIR / "units" / f"{u}.json"
        if p.exists():
            out.append((u, read_json(p)))
    return out


def b2_split_beta(pred: dict[str, Any]) -> float | None:
    """B2 split-label sensitivity: hash_count/toggle and hash_count/count as separate labels."""
    rows = final_rows("B2")
    tw = [r for r in rows if r["arm"] == "TWIN" and r["slot"] in range(10) and r["passed"]]
    lab = lambda r: (r["sublabel"] or r["label"]) if r["label"] == "hash_count" else r["label"]  # noqa: E731
    c = Counter(lab(r) for r in tw if r["label"] not in EXCLUDE)
    if not c:
        return None
    d = c.most_common(1)[0][0]
    base = [lab(r) for r in rows if r["arm"] == "BASE" and r["slot"] < 40 and r["passed"] and r["label"] != "disputed"]
    return sum(l != d for l in base) / len(base) if base else None


def a1(units: list[dict[str, Any]]) -> dict[str, Any]:
    U = [x for x in units if x["default"] != "NO_DEFAULT" and x["beta_u"] is not None and x["E_u"] is not None]
    beta = [x["beta_u"] for x in U]
    E = [x["E_u"] for x in U]
    res: dict[str, Any] = {"n_units": len(U), "units": [x["unit"] for x in U], "beta": beta, "E": E}
    res["primary"] = perm_p(beta, E)
    res["primary"]["bootstrap_ci95"] = boot_ci(beta, E)
    res["pooled_thresholds"] = {"one_sided_alpha_0.01_rho_at_n": {"7": 0.893, "12": 0.678, "14": 0.626},
                                "reading": "descriptive within panel B; the decisive test pools panels A and B"}
    pn = [x["PN_excess_u"] for x in U]
    res["secondary_PN"] = perm_p(beta, pn)
    coll = [x for x in U if x["beta_u"] < 0.05]
    k = sum(1 for x in coll if x["E_u"] == 0)
    res["collapsed_immovable"] = {"n_collapsed": len(coll), "n_immovable": k,
                                  "share": k / len(coll) if coll else None, "ci95": clopper_pearson(k, len(coll))}
    table = {m: {c: 0 for c in ("beta<0.05", "0.05<=beta<0.2", "beta>=0.2")} for m in ("movable", "immovable")}
    for x in U:
        c = "beta<0.05" if x["beta_u"] < 0.05 else ("0.05<=beta<0.2" if x["beta_u"] < 0.2 else "beta>=0.2")
        table["movable" if x["E_u"] > 0 else "immovable"][c] += 1
    res["table_2x3"] = table
    res["partial_spearman_given_K"] = partial_spearman(beta, E, [x["K_u"] for x in U])
    # rivals
    riv = {}
    for name in ("R_margin", "R_merit_runtime", "R_merit_length", "R_modal", "R_novel", "R_novel_correct", "K_u"):
        V = [x for x in U if x["rivals"].get(name) is not None]
        rv = [x["rivals"][name] for x in V]
        ev = [x["E_u"] for x in V]
        bv = [x["beta_u"] for x in V]
        r = perm_p(rv, ev)
        diffs = []
        n = len(V)
        if n >= 3:
            for _ in range(10000):
                idx = RNG.integers(0, n, n)
                a_ = spearman([bv[i] for i in idx], [ev[i] for i in idx])
                b_ = spearman([rv[i] for i in idx], [ev[i] for i in idx])
                if a_ is not None and b_ is not None:
                    diffs.append(a_ - b_)
        riv[name] = {"n": n, "rho_rival_E": r.get("rho"), "p_rival": r.get("p"),
                     "rho_beta_minus_rival_ci95": [float(np.quantile(diffs, 0.025)), float(np.quantile(diffs, 0.975))]
                     if len(diffs) >= 100 else None, "values": dict(zip([x["unit"] for x in V], rv))}
    res["rivals"] = riv
    # sensitivities
    sens = {}
    for name, key in (("beta_attempt", "beta_attempt"), ("beta_plain", "beta_plain"), ("beta_correct", "beta_correct")):
        V = [x for x in U if x.get(key) is not None]
        sens[name] = perm_p([x[key] for x in V], [x["E_u"] for x in V])
    V = [x for x in U if not (x.get("P_beta_ge_0.05") is not None and 0.2 < x["P_beta_ge_0.05"] < 0.8)]
    sens["exclude_uncertain_class"] = {**perm_p([x["beta_u"] for x in V], [x["E_u"] for x in V]),
                                       "excluded": [x["unit"] for x in U if x not in V]}
    if any(x["unit"] == "B2" for x in U):
        bs = [x.get("beta_b2_split", x["beta_u"]) if x["unit"] == "B2" else x["beta_u"] for x in U]
        sens["b2_split_label"] = perm_p(bs, E)
    V = [x for x in U if not any(f.startswith(("default_from_few_correct", "twin_pass_below")) for f in x["flags"])]
    sens["exclude_flagged_twins"] = {**perm_p([x["beta_u"] for x in V], [x["E_u"] for x in V]),
                                     "excluded": [x["unit"] for x in U if x not in V]}
    res["sensitivities"] = sens
    # placebo: shuffled beta
    rhos, rej = [], 0
    for _ in range(1000):
        bsh = list(RNG.permutation(beta))
        r = perm_p(bsh, E) if len(U) <= 7 else {"rho": spearman(bsh, E), "p": None}
        if r["rho"] is not None:
            rhos.append(r["rho"])
            rej += int(r["p"] is not None and r["p"] < 0.05)
    res["placebo_shuffled_beta"] = {"n": len(rhos), "mean_rho": float(np.mean(rhos)) if rhos else None,
                                    "rejection_rate_p_lt_0.05": rej / len(rhos) if rhos else None}
    return res


def a2(units: list[dict[str, Any]]) -> dict[str, Any]:
    ev = [x for x in units if x["default"] != "NO_DEFAULT" and x["E_u"] and x["E_u"] > 0 and x["beta_u"] is not None
          and x["beta_u"] >= 0.05 and x["push_landing"] is not None]
    res: dict[str, Any] = {"n_events": len(ev), "events": []}
    hits, probs = 0.0, []
    lsd = {"BASE": [], "ASSOC": [], "PROX": []}
    for x in ev:
        land = x["push_landing"]
        tie = x.get("push_landing_tie") or [land]
        ru = x["r_u"]
        hit = (1.0 / len(tie)) if (ru in tie) else 0.0
        if ru == "tie":
            ties = x.get("r_u_ties") or []
            hit = len(set(ties) & set(tie)) / max(len(ties), 1)
        hits += hit
        p_ch = 1.0 / max(x["K_u"] - 1, 1)
        probs.append(p_ch)
        comp = x["push_landing_composition"]
        n_l = sum(comp.values())
        scores = {}
        for f in ("BASE", "ASSOC", "PROX"):
            dist = x["forecasts"].get(f)
            if not dist or n_l == 0:
                scores[f] = None
                continue
            surv = [k for k in dist if k != "other"]
            uni = {k: 1.0 / len(surv) for k in surv}
            s = sum(c * math.log(max(dist.get(lab, dist.get("other", 1e-6)), 1e-12)) for lab, c in comp.items()) / n_l
            scores[f] = s
            lsd[f].append(s)
        res["events"].append({"unit": x["unit"], "r_u": ru, "push_landing": land, "tie": tie, "hit": hit,
                              "chance": p_ch, "log_scores": scores, "landing_composition": comp,
                              "js_landing_vs_base": js_divergence(comp, {k: v for k, v in
                                                                         x["base_correct_composition"].items()
                                                                         if k != x["default"]})})
    res["top1"] = {"hits": hits, "n": len(ev), "expected_by_chance": sum(probs),
                   "poisson_binomial_p": poisson_binomial_sf(hits, probs)}
    pairs = {}
    for other in ("ASSOC", "PROX"):
        dd = [b - o for b, o in zip(lsd["BASE"], lsd[other]) if b is not None and o is not None]
        rec: dict[str, Any] = {"n": len(dd), "mean_diff": float(np.mean(dd)) if dd else None, "diffs": dd,
                               "margin_0.10_nat_met": (float(np.mean(dd)) >= 0.10) if dd else None}
        if len(dd) >= 5:
            w = stats.wilcoxon(dd, alternative="greater", method="exact")
            rec["wilcoxon_exact_p"] = float(w.pvalue)
        pairs[f"BASE_minus_{other}"] = rec
    res["paired_log_score"] = pairs
    res["reading"] = "A2 not computable in panel B" if not ev else "descriptive (few events)"
    return res


def main() -> None:
    units = []
    for u, pred in load_units():
        out = unit_outcomes(u, pred)
        b = pred["base"]
        x = {"unit": u, "unit_id": pred["unit_id"], "default": pred["default"], "flags": pred["flags"],
             "beta_u": b["beta_u"], "beta_attempt": b["beta_attempt"], "beta_plain": b["beta_plain"],
             "beta_correct": b["beta_correct"], "r_u": b["r_u"], "r_u_ties": b["r_u_ties"],
             "P_beta_ge_0.05": b.get("P_beta_ge_0.05"), "K_u": pred["K_u"], "rivals": pred["rivals"],
             "forecasts": pred["forecasts"], "base_correct_composition": b["correct_composition"],
             "predicted_class": pred["predicted_class"], **out}
        if u == "B2":
            x["beta_b2_split"] = b2_split_beta(pred)
        units.append(x)
    r1 = a1(units)
    r2 = a2(units)
    write_json(RESULTS_DIR / "a1_panel.json", {"utc": utc_now(), **r1})
    write_json(RESULTS_DIR / "a2_panel.json", {"utc": utc_now(), **r2})
    write_json(RESULTS_DIR / "rivals.json", {"utc": utc_now(), "rivals": r1["rivals"]})
    write_json(RESULTS_DIR / "repertoire_check.json",
               {"utc": utc_now(), "units": {x["unit"]: x["repertoire"] for x in units}})
    write_json(RESULTS_DIR / "unit_outcomes.json", {"utc": utc_now(), "units": units})
    with open(RESULTS_DIR / "units_table.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["unit", "default", "K_u", "beta_u", "beta_attempt", "beta_plain", "r_u", "predicted_class",
                    "E_alpha1", "E_alpha2", "E_u", "movable", "push_landing", "PN_excess_u", "R_margin",
                    "R_merit_runtime", "R_modal", "R_novel", "flags"])
        for x in units:
            w.writerow([x["unit"], x["default"], x["K_u"], x["beta_u"], x["beta_attempt"], x["beta_plain"], x["r_u"],
                        x["predicted_class"], x["E_by_alpha"].get("1.0"), x["E_by_alpha"].get("2.0"), x["E_u"],
                        x["movable"], x["push_landing"], x["PN_excess_u"], x["rivals"].get("R_margin"),
                        x["rivals"].get("R_merit_runtime"), x["rivals"].get("R_modal"), x["rivals"].get("R_novel"),
                        ";".join(x["flags"])])
    print(json.dumps({"A1": r1["primary"], "A2_top1": r2["top1"], "n_units": len(units)}, indent=1, default=str))


if __name__ == "__main__":
    main()
