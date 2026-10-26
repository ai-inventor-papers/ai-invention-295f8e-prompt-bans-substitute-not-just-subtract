#!/usr/bin/env python3
"""Headline re-derivation, second independent code path (no import of src/, no results/*.json aggregates as inputs).

Reads data/labels.jsonl (one label per generated row), inputs/exp23 iteration-4 rows and forecasts, and only the task
catalogues from predictions/commit_E1.json; recomputes D_u, beta_u, r_u, E_u, the E-A1 Spearman and its permutation p,
the E-A2 hits / exact Poisson-binomial p (full 2^n enumeration) / log scores / exact Wilcoxon p (sign enumeration),
the transplant counts and McNemar p (binomial tail by hand), the descriptive Fisher test (hypergeometric by hand) and
the engine-check agreement; then runs each test on placebo input and checks that it fails there.
Writes results/rederive_headlines.json and prints reported-vs-rederived."""

from __future__ import annotations

import itertools
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def jl(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]


def ranks(v: list[float]) -> list[float]:
    order = sorted(range(len(v)), key=lambda i: v[i])
    r = [0.0] * len(v)
    i = 0
    while i < len(v):
        j = i
        while j + 1 < len(v) and v[order[j + 1]] == v[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def pearson(a: list[float], b: list[float]) -> float:
    n = len(a)
    ma, mb = sum(a) / n, sum(b) / n
    cov = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    va = math.sqrt(sum((x - ma) ** 2 for x in a))
    vb = math.sqrt(sum((y - mb) ** 2 for y in b))
    return cov / (va * vb)


def spearman(a: list[float], b: list[float]) -> float:
    return pearson(ranks(a), ranks(b))


def binom_sf(k: int, n: int, p: float) -> float:
    """P(X >= k), X ~ Binomial(n, p), by direct summation."""
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(max(k, 0), n + 1))


def main() -> None:
    labs = jl(ROOT / "data" / "labels.jsonl")
    c1 = json.loads((ROOT / "predictions" / "commit_E1.json").read_text())
    cat = {t: u["catalogue"] for t, u in c1["units"].items()}
    tasks = list(cat)
    by = defaultdict(list)
    for r in labs:
        by[(r["stage"], r["task"])].append(r)
    out: dict = {}

    # ---------------------------------------------------------------- D_u, beta_u, r_u (pooled pt, LOW_CORRECT rule)
    D, beta, r_u = {}, {}, {}
    for t in tasks:
        tw = [r for r in by[("twin", t)] if r["arm"] == "twin"]
        cc = Counter(r["label"] for r in tw if r["passed"] and r["label"] not in ("invalid", "disputed"))
        (lab, top), n_c = cc.most_common(1)[0], sum(cc.values())
        D[t] = lab if (lab in cat[t] and top / n_c >= 0.6 and n_c >= 10) else None
        pt = by[("ptchat", t)] + by[("ptplain", t)]
        n_corr = sum(1 for r in pt if r["passed"] and r["label"] != "disputed")
        assert n_corr < 20, "LOW_CORRECT rule expected for every unit"
        valid = [r["label"] for r in pt if r["label"] not in ("invalid", "disputed")]
        vc, ac = Counter(valid), Counter(r["label"] for r in pt)
        surv = [m for m in cat[t] if m != D[t]]
        beta[t] = sum(vc[m] for m in surv) / len(valid)
        best = sorted(surv, key=lambda m: (-vc[m], -ac[m], cat[t].index(m)))[0]
        r_u[t] = best if vc[best] > 0 else None
    out["D_match_committed"] = all(D[t] == c1["units"][t]["D"] for t in tasks)
    out["beta_max_abs_diff_vs_committed"] = max(abs(beta[t] - c1["units"][t]["beta"]) for t in tasks)
    out["r_u_match_committed"] = all(r_u[t] == c1["units"][t]["r_u"] for t in tasks)

    # ---------------------------------------------------------------- E_u (escape rule written from scratch)
    E, conf_rows = {}, {}
    for t in tasks:
        S = set(cat[t]) - {D[t]}
        tw = [r for r in by[("twin", t)] if r["arm"] == "twin"]
        p0 = sum(r["label"] in S for r in tw) / len(tw)
        pt0 = sum(r["passed"] for r in tw) / len(tw)
        cells = defaultdict(list)
        for st in ("push", "confirm"):
            for r in by[(st, t)]:
                if r["arm"].startswith("esc"):
                    cells[(r["arm"], st)].append(r)
        n_conf = {1: 0, 2: 0}
        rows_conf = []
        for s in range(52001, 52017):
            for a in (1, 2):
                arm = f"esc{s}_a{a}"
                s1 = cells[(arm, "push")]
                if not s1:
                    continue
                if not (sum(r["label"] in S for r in s1) / len(s1) - p0 >= 0.2 and sum(r["passed"] for r in s1) / len(s1) >= 0.8 * pt0):
                    continue
                allr = s1 + cells[(arm, "confirm")]
                k, n = sum(r["label"] in S for r in allr), len(allr)
                if n >= 30 and k / n - p0 >= 0.2 and sum(r["passed"] for r in allr) / n >= 0.8 * pt0 \
                        and binom_sf(k, n, max(p0, 0.01)) < 0.05:
                    n_conf[a] += 1
                    rows_conf += allr
        E[t] = (n_conf[1] + n_conf[2]) / 32
        conf_rows[t] = rows_conf
    rho = spearman([beta[t] for t in tasks], [E[t] for t in tasks])
    rng = random.Random(2024)
    e_list = [E[t] for t in tasks]
    b_list = [beta[t] for t in tasks]
    n_perm, hits = 50_000, 0
    for _ in range(n_perm):
        sh = e_list[:]
        rng.shuffle(sh)
        hits += spearman(b_list, sh) >= rho - 1e-12
    p_perm = (hits + 1) / (n_perm + 1)
    out["E_A1"] = {"rho": rho, "perm_p": p_perm, "E": E, "beta": beta}
    # placebo: beta shuffled across units -> how often would p < 0.01 (the decisive bar) be reached?
    rej, n_pl = 0, 300
    for _ in range(n_pl):
        bb = b_list[:]
        rng.shuffle(bb)
        r0 = spearman(bb, e_list)
        h = 0
        for _ in range(400):
            sh = e_list[:]
            rng.shuffle(sh)
            h += spearman(bb, sh) >= r0 - 1e-12
        rej += (h + 1) / 401 < 0.05
    out["E_A1_placebo_rejection_rate_at_0.05"] = rej / n_pl

    # ---------------------------------------------------------------- E-A2 hits, exact Poisson-binomial, log scores
    ev = []
    for t in tasks:
        if E[t] > 0 and beta[t] >= 0.05:
            surv = [m for m in cat[t] if m != D[t]]
            lc = Counter(r["label"] for r in conf_rows[t] if r["passed"] and r["label"] in surv)
            if lc:
                land = max(surv, key=lambda m: (lc[m], -surv.index(m)))
                ev.append((t, land, surv, [r["label"] for r in conf_rows[t] if r["passed"] and r["label"] in surv]))
    hits_obs = sum(r_u[t] == land for t, land, _, _ in ev)
    chance = [1 / (len(cat[t]) - 1) for t, _, _, _ in ev]

    def pb_tail(k: int, ps: list[float]) -> float:            # exact by enumerating all 2^n outcomes
        tot = 0.0
        for outc in itertools.product((0, 1), repeat=len(ps)):
            if sum(outc) >= k:
                tot += math.prod(p if o else 1 - p for o, p in zip(outc, ps))
        return tot
    p_hits = pb_tail(hits_obs, chance)
    e23 = json.loads((ROOT / "inputs" / "exp23" / "predictions" / "commit_preban.json").read_text())["tasks"]

    def mean_log(q: dict, ys: list[str], surv: list[str]) -> float:
        qq = {m: max(q.get(m, 0.0), 0.0) for m in surv}
        z = sum(qq.values()) or 1.0
        qq = {m: 0.98 * v / z for m, v in qq.items()}
        return sum(math.log(max(qq.get(y, 1e-12), 1e-12)) for y in ys) / len(ys)
    diffs = []
    for t, land, surv, ys in ev:
        pt = by[("ptchat", t)] + by[("ptplain", t)]
        vc = Counter(r["label"] for r in pt if r["label"] not in ("invalid", "disputed"))
        qb = {m: vc[m] + 0.5 for m in surv}
        fa = e23[t]["forecasts"]["association"]
        qa = fa["distribution"] if (fa["defined"] and e23[t]["D"] == D[t]) else {m: 1.0 for m in surv}
        diffs.append(mean_log(qb, ys, surv) - mean_log(qa, ys, surv))
    rk = ranks([abs(d) for d in diffs])
    w_obs = sum(r for r, d in zip(rk, diffs) if d > 0)
    w_all = [sum(r for r, s in zip(rk, signs) if s) for signs in itertools.product((0, 1), repeat=len(diffs))]
    p_w = sum(w >= w_obs - 1e-12 for w in w_all) / len(w_all)
    out["E_A2"] = {"events": [e[0] for e in ev], "hits": hits_obs, "hit_rate": hits_obs / len(ev),
                   "poisson_binomial_p": p_hits, "mean_base_minus_assoc": sum(diffs) / len(diffs), "wilcoxon_exact_p": p_w}
    # placebo: r_u replaced by a uniformly random survivor -> how often is the hit test passed (rate >= .7, p < .05)?
    passed = 0
    for _ in range(2000):
        h = sum(rng.choice(surv) == land for _, land, surv, _ in ev)
        passed += (h / len(ev) >= 0.7) and pb_tail(h, chance) < 0.05
    out["E_A2_placebo_pass_rate_random_r_u"] = passed / 2000
    # placebo: q_base replaced by a random Dirichlet forecast -> how often does it beat association by >= .10 at p < .05?
    passed = 0
    for _ in range(500):
        dd = []
        for t, land, surv, ys in ev:
            g = {m: rng.gammavariate(1.0, 1.0) for m in surv}
            fa = e23[t]["forecasts"]["association"]
            qa = fa["distribution"] if (fa["defined"] and e23[t]["D"] == D[t]) else {m: 1.0 for m in surv}
            dd.append(mean_log(g, ys, surv) - mean_log(qa, ys, surv))
        rr = ranks([abs(d) for d in dd])
        wo = sum(r for r, d in zip(rr, dd) if d > 0)
        pw = sum(sum(r for r, s in zip(rr, sg) if s) >= wo - 1e-12 for sg in itertools.product((0, 1), repeat=len(dd))) / 2 ** len(dd)
        passed += (sum(dd) / len(dd) >= 0.10) and pw < 0.05
    out["E_A2_placebo_logscore_pass_rate_random_forecast"] = passed / 500

    # ---------------------------------------------------------------- transplant counts and McNemar
    tp = {}
    for u in ("T04", "R6", "T03", "T05", "T06", "T10", "T11"):
        S = set(cat[u]) - {D[u]}
        arm = defaultdict(dict)
        for r in by[("transplant", u)]:
            arm[r["arm"]][(r["template"], r["slot"])] = r
        def succ(a):
            return {k: bool(r["passed"] and r["label"] in S) for k, r in arm[a].items()}
        T, X, Rn = succ("T"), succ("XT"), succ("RND")
        b10x = sum(T[k] and not X[k] for k in T)
        b01x = sum(X[k] and not T[k] for k in T)
        b10r = sum(T[k] and not Rn[k] for k in T)
        b01r = sum(Rn[k] and not T[k] for k in T)
        tp[u] = {"T_correct_offdefault": sum(T.values()), "n_T": len(T),
                 "T_pass": sum(r["passed"] for r in arm["T"].values()) / len(arm["T"]),
                 "RND_pass": sum(r["passed"] for r in arm["RND"].values()) / len(arm["RND"]),
                 "XT_pass": sum(r["passed"] for r in arm["XT"].values()) / len(arm["XT"]),
                 "mcnemar_T_vs_XT": [b10x, b01x, binom_sf(b10x, b10x + b01x, 0.5) if b10x + b01x else 1.0],
                 "mcnemar_T_vs_RND": [b10r, b01r, binom_sf(b10r, b10r + b01r, 0.5) if b10r + b01r else 1.0],
                 "T_composition": dict(Counter(r["label"] for r in arm["T"].values()))}
    out["transplant"] = tp
    # placebo: T and XT outcomes swapped at random within each CRN pair -> McNemar rejection rate (T04 + R6 pooled draws)
    rej = tot = 0
    for u in ("T04", "R6"):
        S = set(cat[u]) - {D[u]}
        arm = defaultdict(dict)
        for r in by[("transplant", u)]:
            arm[r["arm"]][(r["template"], r["slot"])] = bool(r["passed"] and r["label"] in S)
        for _ in range(1000):
            a = b = 0
            for k in arm["T"]:
                x, y = (arm["T"][k], arm["XT"][k]) if rng.random() < 0.5 else (arm["XT"][k], arm["T"][k])
                a += x and not y
                b += y and not x
            rej += (binom_sf(a, a + b, 0.5) if a + b else 1.0) < 0.05
            tot += 1
    out["transplant_placebo_mcnemar_rejection_rate"] = rej / tot

    # ---------------------------------------------------------------- descriptive Fisher (beta >= .2 vs movable)
    div = [t for t in tasks if beta[t] >= 0.2]
    oth = [t for t in tasks if beta[t] < 0.2]
    a_, b_ = sum(E[t] > 0 for t in div), sum(E[t] == 0 for t in div)
    c_, d_ = sum(E[t] > 0 for t in oth), sum(E[t] == 0 for t in oth)
    N, K, n = a_ + b_ + c_ + d_, a_ + c_, a_ + b_
    p_f = sum(math.comb(K, x) * math.comb(N - K, n - x) / math.comb(N, n) for x in range(a_, min(K, n) + 1))
    out["fisher_descriptive"] = {"table": [[a_, b_], [c_, d_]], "p_one_sided": p_f}
    rej = 0
    mv = [E[t] > 0 for t in tasks]
    for _ in range(2000):
        sh = mv[:]
        rng.shuffle(sh)
        aa = sum(m for t, m in zip(tasks, sh) if beta[t] >= 0.2)
        pf = sum(math.comb(K, x) * math.comb(N - K, n - x) / math.comb(N, n) for x in range(aa, min(K, n) + 1))
        rej += pf < 0.05
    out["fisher_placebo_rejection_rate"] = rej / 2000

    # ---------------------------------------------------------------- engine check agreement (vs exp23 raw rows)
    e23rows = {(r["task"], r["arm"], r["template"], int(r["slot"])): r["label"] for r in jl(ROOT / "inputs" / "exp23" / "data" / "samples.jsonl")
               if r["task"] in ("T1", "T2") and r.get("stage") in ("A", "B")}
    ec = [r for r in labs if r["stage"] == "engine_check"]
    m = [(r["label"], e23rows.get((r["task"], r["arm"].replace("e23_", ""), r["template"], int(r["slot"])))) for r in ec]
    out["engine_check_agreement"] = sum(a == b for a, b in m if b is not None) / sum(b is not None for _, b in m)

    # ---------------------------------------------------------------- rivals quoted in the bottom line + novelty count
    modal = {t: Counter(r["label"] for r in by[("twin", t)] if r["arm"] == "twin").most_common(1)[0][1]
             / len([r for r in by[("twin", t)] if r["arm"] == "twin"]) for t in tasks}
    nov = {t: sum(r["label"] in (set(cat[t]) - {D[t]}) for r in by[("novelty", t)]) / len(by[("novelty", t)]) for t in tasks}
    out["rho_twin_modal_share_signed"] = spearman([-modal[t] for t in tasks], e_list)
    out["rho_novelty_off_cat"] = spearman([nov[t] for t in tasks], e_list)
    out["n_correct_other_all_arms"] = sum(1 for r in labs if r["passed"] and r["label"] == "other")

    # ---------------------------------------------------------------- compare with reported values
    rep = {"a1": json.loads((ROOT / "results" / "e_a1.json").read_text()),
           "a2": json.loads((ROOT / "results" / "e_a2.json").read_text())}
    cmp = {"rho": (rho, rep["a1"]["rho"]), "perm_p (MC, tol .01)": (p_perm, rep["a1"]["p_one_sided_perm"]),
           "hits": (hits_obs, rep["a2"]["hits"]), "poisson_binomial_p": (p_hits, rep["a2"]["poisson_binomial_p"]),
           "base_minus_assoc": (out["E_A2"]["mean_base_minus_assoc"], rep["a2"]["mean_base_minus_assoc"]),
           "wilcoxon_p": (p_w, rep["a2"]["wilcoxon_p_base_vs_assoc"]),
           "rho_twin_modal_share": (out["rho_twin_modal_share_signed"], rep["a1"]["rivals"]["twin_modal_share"]["rho"]),
           "rho_novelty_off_cat": (out["rho_novelty_off_cat"], rep["a1"]["rivals"]["novelty_off_cat"]["rho"]),
           "n_correct_other": (out["n_correct_other_all_arms"],
                               json.loads((ROOT / "results" / "novelty_audit.json").read_text())["n_correct_other"])}
    out["comparison"] = {k: {"rederived": a, "reported": b,
                             "match": abs(a - b) <= (0.01 if "perm" in k else 1e-9)} for k, (a, b) in cmp.items()}
    out["all_match"] = all(v["match"] for v in out["comparison"].values()) and out["D_match_committed"] \
        and out["r_u_match_committed"] and out["beta_max_abs_diff_vs_committed"] < 1e-12
    (ROOT / "results" / "rederive_headlines.json").write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps({k: v for k, v in out.items() if k not in ("E_A1",)}, indent=1, default=str)[:4000])


if __name__ == "__main__":
    main()
