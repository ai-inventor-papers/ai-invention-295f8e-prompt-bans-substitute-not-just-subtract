#!/usr/bin/env python3
"""Second independent re-derivation (standard library only; shares no code with src/, analysis/ or audit/rederive.py)
of the headline numbers not covered by audit/rederive.py: the top-1 hit counts of r_u, qlik_top1 and t_u, the mean
log-score differences D_lik and D_tail on the CONFIRMATION events, the escape fraction E_u per unit (escape rule
re-implemented from the raw rows), beta re-counted from the raw base rows, the M headline Spearman rho(beta, E_u)
with its exact one-sided permutation p, and the L2 violation count. Inputs: data/samples.jsonl (one row per program)
and predictions/units/II*.json (the committed forecasts); results/*.json are read only to compare.
Placebos that must FAIL: (1) E_u shuffled across units (2,000 shuffles: the share with p < 0.05 must sit near 0.05);
(2) q_base permuted over S inside each event (the mean D_lik advantage must vanish); (3) a constant beta (rho undefined)."""

import itertools
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def binom_sf(k, n, p):
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k, n + 1))


def ranks(x):
    order = sorted(range(len(x)), key=lambda i: x[i])
    r = [0.0] * len(x)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and x[order[j + 1]] == x[order[i]]:
            j += 1
        for t in range(i, j + 1):
            r[order[t]] = (i + j) / 2 + 1
        i = j + 1
    return r


def pearson(a, b):
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    va = sum((x - ma) ** 2 for x in a)
    vb = sum((y - mb) ** 2 for y in b)
    if va == 0 or vb == 0:
        return None
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / math.sqrt(va * vb)


def spearman(a, b):
    return pearson(ranks(a), ranks(b))


def perm_p(a, b):
    r0 = spearman(a, b)
    if r0 is None:
        return None, None
    ra, rb = ranks(a), ranks(b)
    hits = tot = 0
    for perm in itertools.permutations(range(len(b))):
        r = pearson(ra, [rb[i] for i in perm])
        hits += r is not None and r >= r0 - 1e-12
        tot += 1
    return r0, hits / tot


def main():
    rows = [json.loads(l) for l in (ROOT / "data" / "samples.jsonl").read_text().splitlines() if l.strip()]
    units = {p.stem: json.loads(p.read_text()) for p in sorted((ROOT / "predictions" / "units").glob("II*.json"))}
    by_unit = defaultdict(list)
    for r in rows:
        by_unit[r["unit"]].append(r)
    E, eu, beta_raw, l2_viol, l2_n = [], {}, {}, 0, 0
    for u, c in units.items():
        d = c["default"]
        if d == "NO_DEFAULT":
            continue
        S = [a for a in c["catalogue"] if a != d]
        R = by_unit[u]
        ok = (c.get("engine_check_twin") or {}).get("pass", True)
        tw = [r for r in R if r["arm"] == "TWIN" and r["model_tag"] == "instruct" and
              ((r["engine"] == "hf" and r["slot"] < 10) or (ok and r["engine"] == "vllm"))]
        n_tw = len(tw)
        k_tw = sum(1 for r in tw if r["passed"] and r["label"] in S)
        pass_tw = sum(1 for r in tw if r["passed"]) / n_tw
        p0 = (k_tw + 0.5) / (n_tw + 1)
        cells = defaultdict(list)
        for r in R:
            if r["family"] in ("ESC", "PN", "GTN"):
                cells[r["arm"]].append(r)
        conf = defaultdict(lambda: [0, 0])
        pooled = defaultdict(Counter)
        for arm, rr in cells.items():
            fam = arm.split("_")[0]
            if fam == "ESC":
                alpha = arm.rsplit("_a", 1)[1]
                s1 = [r for r in rr if r["slot"] <= 1]
                s30 = [r for r in rr if r["slot"] <= 5]
                conf[alpha][1] += 1
                sh1 = sum(1 for r in s1 if r["passed"] and r["label"] in S) / len(s1)
                pr1 = sum(1 for r in s1 if r["passed"]) / len(s1)
                st1 = len(s1) >= 10 and pr1 >= 0.8 * pass_tw - 1e-12 and sh1 - k_tw / n_tw >= 0.2 - 1e-12
                if st1 and len(s30) >= 30:
                    k = sum(1 for r in s30 if r["passed"] and r["label"] in S)
                    pr = sum(1 for r in s30 if r["passed"]) / len(s30)
                    conf[alpha][0] += binom_sf(k, len(s30), p0) < 0.05 and pr >= 0.8 * pass_tw - 1e-12
                use = s30 if len(s30) >= 30 else s1
            else:
                if arm not in ("PN_a2.0", "PN_a4.0", "GTN_a2.0"):
                    continue
                use = rr
            if sum(1 for r in use if r["passed"]) / len(use) < 0.8 * pass_tw - 1e-12:
                continue
            pooled[fam].update(r["label"] for r in use if r["passed"] and r["label"] in S)
        for r in R:                       # L2 counts ALL correct S-labelled content-free nudged programs (plan)
            if r["family"] in ("ESC", "PN", "GTN") and r["passed"] and r["label"] in S:
                l2_n += 1
                sup = (c.get("support") or {}).get(r["label"], {})
                l2_viol += sup.get("valid", 0) == 0 and sup.get("correct", 0) == 0
        eu[u] = sum(cf / 8 for cf, _ in conf.values()) / len(conf) if conf else None
        base = [r for r in R if r["model_tag"] == "base" and r["arm"] in ("BASE", "PLAIN") and r["passed"]
                and r["label"] not in ("invalid", "disputed")]
        bc = Counter(r["label"] for r in base)
        beta_raw[u] = 1 - bc.get(d, 0) / sum(bc.values()) if bc else None
        for fam, cnt in pooled.items():
            n = sum(cnt.values())
            if n < 5:
                continue
            srt = sorted(S, key=lambda a: (-cnt.get(a, 0), S.index(a)))
            lead = cnt.get(srt[0], 0) / n - (cnt.get(srt[1], 0) / n if len(srt) > 1 else 0)
            E.append({"id": f"{u}|{fam}", "S": S, "cnt": cnt, "n": n, "c": c,
                      "modal": srt[0] if lead >= 0.15 - 1e-12 else "NO_CLEAR_LANDING"})

    def q_of(c, key, S):
        q = c.get(key)
        if not q:
            return {a: 1 / len(S) for a in S}
        t = sum(q.get(a, 0) for a in S)
        return {a: q.get(a, 0) / t for a in S}

    def ls(e, q):
        return sum(v * math.log(max(q[a], 1e-12)) for a, v in e["cnt"].items() if a in q) / e["n"]

    hits = {k: sum(1 for e in E if e["c"].get(k) and e["c"][k] == e["modal"]) for k in ("r_u", "qlik_top1", "t_u")}
    n_tu = sum(1 for e in E if e["c"].get("t_u"))
    d_lik = [ls(e, q_of(e["c"], "q_base", e["S"])) - ls(e, q_of(e["c"], "q_lik", e["S"])) for e in E]
    d_tail = [ls(e, q_of(e["c"], "q_base", e["S"])) - ls(e, q_of(e["c"], "q_tail", e["S"])) for e in E]
    us = sorted(u for u in eu if eu[u] is not None)
    betas = [units[u]["m_candidates"]["beta"] for u in us]
    rho, p = perm_p(betas, [eu[u] for u in us])
    # placebo 1: E_u shuffled across units
    rng = random.Random(20261021)
    rej, rhos = 0, []
    vals = [eu[u] for u in us]
    for _ in range(300):
        sh = vals[:]
        rng.shuffle(sh)
        r_, p_ = perm_p(betas, sh)
        rhos.append(r_ or 0.0)
        rej += p_ is not None and p_ < 0.05
    # placebo 2: q_base permuted over S inside each event
    pl = []
    for _ in range(200):
        tot = 0.0
        for e in E:
            qb = q_of(e["c"], "q_base", e["S"])
            perm = e["S"][:]
            rng.shuffle(perm)
            qp = {a: qb[b] for a, b in zip(e["S"], perm)}
            tot += ls(e, qp) - ls(e, q_of(e["c"], "q_lik", e["S"]))
        pl.append(tot / len(E))
    # placebo 3: constant beta
    rho_const = spearman([0.5] * len(us), [eu[u] for u in us])
    frozen = {"l1": json.loads((ROOT / "results" / "l1.json").read_text()),
              "m": json.loads((ROOT / "results" / "m.json").read_text()),
              "l2": json.loads((ROOT / "results" / "l2.json").read_text())}
    fl = frozen["l1"]["log_scores"]["E"]
    out = {"n_events_E": len(E), "hits": hits, "n_events_t_u_defined": n_tu,
           "mean_D_lik": sum(d_lik) / len(d_lik), "mean_D_tail": sum(d_tail) / len(d_tail),
           "frozen_mean_D_lik": fl["D_lik"]["event"]["mean"], "frozen_mean_D_tail": fl["D_tail"]["event"]["mean"],
           "E_u": eu, "frozen_E_u": frozen["m"]["E_u"],
           "beta_committed": dict(zip(us, betas)), "beta_recounted_from_rows": {u: beta_raw[u] for u in us},
           "M_beta": {"rho": rho, "p_one_sided": p, "frozen_rho": frozen["m"]["candidates"]["beta"]["rho"],
                      "frozen_p": frozen["m"]["candidates"]["beta"]["p_one_sided"]},
           "L2": {"violations": l2_viol, "n": l2_n, "frozen": [frozen["l2"]["content_free"]["violations"],
                                                                frozen["l2"]["content_free"]["n_programs"]]},
           "placebo_shuffled_E_u": {"rejection_rate_p<0.05": rej / 300, "mean_rho": sum(rhos) / len(rhos)},
           "placebo_permuted_q_base_mean_D_lik": sum(pl) / len(pl),
           "placebo_constant_beta_rho": rho_const}
    out["checks"] = {
        "D_lik_match": abs(out["mean_D_lik"] - out["frozen_mean_D_lik"]) < 1e-9,
        "D_tail_match": abs(out["mean_D_tail"] - out["frozen_mean_D_tail"]) < 1e-9,
        "E_u_match": all(abs((eu[u] or 0) - (frozen["m"]["E_u"].get(u) or 0)) < 1e-9 for u in us),
        "beta_rho_match": rho is not None and abs(rho - out["M_beta"]["frozen_rho"]) < 1e-9,
        "beta_p_match": p is not None and abs(p - out["M_beta"]["frozen_p"]) < 1e-9,
        "L2_match": [l2_viol, l2_n] == out["L2"]["frozen"],
        "beta_recount_max_abs_drift_after_final_adjudication": max(abs((beta_raw[u] or 0) - b) for u, b in zip(us, betas)),
        "M_rho_with_recounted_beta": spearman([beta_raw[u] for u in us], [eu[u] for u in us]),
        "placebo_shuffle_fails": rej / 300 < 0.15,
        "placebo_permuted_q_base_loses_advantage": out["placebo_permuted_q_base_mean_D_lik"] < out["mean_D_lik"],
        "placebo_constant_beta_undefined": rho_const is None}
    (ROOT / "results" / "rederive_headlines.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: out[k] for k in ("n_events_E", "hits", "n_events_t_u_defined", "mean_D_lik", "mean_D_tail",
                                          "M_beta", "L2", "placebo_shuffled_E_u",
                                          "placebo_permuted_q_base_mean_D_lik", "checks")}, indent=1))


if __name__ == "__main__":
    main()
