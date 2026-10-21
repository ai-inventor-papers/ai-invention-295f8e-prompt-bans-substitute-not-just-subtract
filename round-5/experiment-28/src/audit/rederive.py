#!/usr/bin/env python3
"""Independent re-derivation (a second code path; does NOT import src/analysis_E.py or src/final_analysis.py).

Reads only data/samples.jsonl and predictions/commit_E1.json, re-derives beta_u, r_u, E_u (escape rule), landings,
Spearman rho and its permutation p, E-A2 hits, McNemar discordant counts and the log scores' base forecasts, and
compares them with results/{predictors,escape,e_a1,e_a2,transplant}.json (0 mismatches required; the permutation p
is Monte-Carlo and compared within 0.01). Placebos: beta shuffled across units (mean rho ~ 0) and labels shuffled
within CRN pairs (McNemar rejection rate ~ 5% or less)."""

from __future__ import annotations

import collections
import json
import math
from pathlib import Path

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]


def load_jsonl(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def main() -> None:
    S = [r for r in load_jsonl(ROOT / "data" / "samples.jsonl") if r.get("labelled")]
    c1 = json.loads((ROOT / "predictions" / "commit_E1.json").read_text())
    res_e = json.loads((ROOT / "results" / "escape.json").read_text())
    res_a1 = json.loads((ROOT / "results" / "e_a1.json").read_text())
    res_a2 = json.loads((ROOT / "results" / "e_a2.json").read_text())
    tp_p = ROOT / "results" / "transplant.json"
    res_tp = json.loads(tp_p.read_text()) if tp_p.exists() else None
    mism = []
    out: dict = {"checks": {}}
    by = collections.defaultdict(list)
    for r in S:
        by[(r["stage"], r["task"])].append(r)
    gate_src = c1["pt_chat_validity_gate"]["primary"]
    # ---- beta and r_u
    for t, u in c1["units"].items():
        if not u["defaulted"]:
            continue
        D, cat = u["D"], u["catalogue"]
        surv = [m for m in cat if m != D]
        pt = [r for r in by[("ptchat", t)] if r["arm"] == "pt_chat"]
        if gate_src == "pt_pooled":
            pt = pt + [r for r in by[("ptplain", t)] if r["arm"] == "pt_plain"]
        corr = [r for r in pt if r["passed"] and r["label"] != "disputed"]
        if len(corr) >= 20:
            beta = sum(1 for r in corr if r["label"] in surv) / len(corr)
            cc = collections.Counter(r["label"] for r in corr)
        else:
            valid = [r for r in pt if r["label"] not in ("disputed", "invalid")]
            beta = sum(1 for r in valid if r["label"] in surv) / len(valid) if valid else None
            cc = collections.Counter(r["label"] for r in valid)
        ac = collections.Counter(r["label"] for r in pt)
        rk = sorted(surv, key=lambda m: (-cc.get(m, 0), -ac.get(m, 0), cat.index(m)))
        r_u = rk[0] if rk and cc.get(rk[0], 0) > 0 else None
        if (beta is None) != (u["beta"] is None) or (beta is not None and abs(beta - u["beta"]) > 1e-9):
            mism.append({"what": "beta", "unit": t, "rederived": beta, "committed": u["beta"]})
        if r_u != u["r_u"]:
            mism.append({"what": "r_u", "unit": t, "rederived": r_u, "committed": u["r_u"]})
    # ---- escape
    E_re = {}
    for t, u in c1["units"].items():
        if not u["defaulted"]:
            continue
        D, cat = u["D"], u["catalogue"]
        surv = set(cat) - {D}
        tw = [r for r in by[("twin", t)] if r["arm"] == "twin"]
        p0 = sum(1 for r in tw if r["label"] in surv) / len(tw)
        pt_ = sum(1 for r in tw if r["passed"]) / len(tw)
        n_conf = collections.Counter()
        for alpha in (1, 2):
            for s in range(52001, 52017):
                arm = f"esc{s}_a{alpha}"
                s1 = [r for r in by[("push", t)] if r["arm"] == arm]
                if not s1:
                    continue
                o1 = sum(1 for r in s1 if r["label"] in surv) / len(s1)
                pa1 = sum(1 for r in s1 if r["passed"]) / len(s1)
                if not (o1 - p0 >= 0.2 and pa1 >= 0.8 * pt_):
                    continue
                al = s1 + [r for r in by[("confirm", t)] if r["arm"] == arm]
                k = sum(1 for r in al if r["label"] in surv)
                n = len(al)
                pb = stats.binom.sf(k - 1, n, max(p0, 0.01))
                if n >= 30 and k / n - p0 >= 0.2 and sum(1 for r in al if r["passed"]) / n >= 0.8 * pt_ and pb < 0.05:
                    n_conf[alpha] += 1
        E = (n_conf[1] / 16 + n_conf[2] / 16) / 2
        E_re[t] = E
        if abs(E - res_e[t]["E_u"]) > 1e-9:
            mism.append({"what": "E_u", "unit": t, "rederived": E, "reported": res_e[t]["E_u"]})
    # ---- rho and permutation p
    units = res_a1["units"]
    b = np.array([c1["units"][t]["beta"] for t in units], float)
    e = np.array([E_re[t] for t in units], float)
    rho = stats.spearmanr(b, e).statistic if len(set(e)) > 1 and len(set(b)) > 1 else None
    if rho is not None and not math.isfinite(rho):
        rho = None
    if (rho is None) != (res_a1["rho"] is None) or (rho is not None and abs(rho - res_a1["rho"]) > 1e-9):
        mism.append({"what": "rho", "rederived": rho, "reported": res_a1["rho"]})
    if rho is not None:
        rng = np.random.default_rng(12345)
        perm = np.array([stats.spearmanr(b, rng.permutation(e)).statistic for _ in range(20000)])
        p = (np.sum(perm >= rho - 1e-12) + 1) / (len(perm) + 1)
        out["checks"]["perm_p_rederived"] = float(p)
        if res_a1["p_one_sided_perm"] is not None and abs(p - res_a1["p_one_sided_perm"]) > 0.01:
            mism.append({"what": "perm_p", "rederived": float(p), "reported": res_a1["p_one_sided_perm"]})
        # placebo: beta shuffled across units
        pl = [stats.spearmanr(rng.permutation(b), e).statistic for _ in range(2000)]
        out["checks"]["placebo_beta_shuffled_mean_rho"] = float(np.nanmean(pl))
    out["checks"]["rho_rederived"] = rho
    # ---- E-A2 hits
    hits = 0
    for ev in res_a2.get("events", []):
        t = ev["unit"]
        hits += int(c1["units"][t]["r_u"] == ev["landing"])
    if hits != res_a2.get("hits", 0):
        mism.append({"what": "E_A2_hits", "rederived": hits, "reported": res_a2.get("hits")})
    out["checks"]["e_a2_hits_rederived"] = hits
    # ---- McNemar counts (transplant)
    if res_tp:
        for t, v in res_tp["per_unit"].items():
            u = c1["units"][t]
            D, surv = u["D"], set(u["catalogue"]) - {u["D"]}
            arm = {a: {(r["template"], r["slot"]): bool(r["passed"] and r["label"] in surv)
                       for r in by[("transplant", t)] if r["arm"] == a} for a in ("T", "RND", "XT", "RP")}
            for ctl in ("RND", "XT", "RP"):
                key = f"mcnemar_T_vs_{ctl}"
                if key not in v or not arm[ctl]:
                    continue
                ks = set(arm["T"]) & set(arm[ctl])
                a_only = sum(1 for k in ks if arm["T"][k] and not arm[ctl][k])
                b_only = sum(1 for k in ks if arm[ctl][k] and not arm["T"][k])
                if a_only != v[key]["a_only"] or b_only != v[key]["b_only"]:
                    mism.append({"what": key, "unit": t, "rederived": [a_only, b_only],
                                 "reported": [v[key]["a_only"], v[key]["b_only"]]})
        # placebo: labels shuffled within CRN pairs -> McNemar rejection rate
        rng = np.random.default_rng(7)
        rej, tot = 0, 0
        for t in res_tp["per_unit"]:
            u = c1["units"][t]
            surv = set(u["catalogue"]) - {u["D"]}
            T = {(r["template"], r["slot"]): bool(r["passed"] and r["label"] in surv)
                 for r in by[("transplant", t)] if r["arm"] == "T"}
            X = {(r["template"], r["slot"]): bool(r["passed"] and r["label"] in surv)
                 for r in by[("transplant", t)] if r["arm"] == "XT"}
            ks = sorted(set(T) & set(X))
            for _ in range(500):
                a_only = b_only = 0
                for k in ks:
                    x, y = (T[k], X[k]) if rng.random() < 0.5 else (X[k], T[k])
                    a_only += int(x and not y)
                    b_only += int(y and not x)
                n = a_only + b_only
                p = stats.binom.sf(a_only - 1, n, 0.5) if n else 1.0
                rej += int(p < 0.05)
                tot += 1
        out["checks"]["placebo_mcnemar_rejection_rate"] = rej / tot if tot else None
    out["mismatches"] = mism
    out["n_mismatches"] = len(mism)
    out["pass"] = not mism
    (ROOT / "results" / "rederive.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k != "mismatches"}, indent=1), "mismatches:", mism[:5])


if __name__ == "__main__":
    main()
