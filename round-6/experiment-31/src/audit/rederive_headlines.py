#!/usr/bin/env python3
"""Headline re-derivation through a separate code path: reads the RAW row files (data/raw_hf.jsonl, data/raw_vllm.jsonl),
the labeller output (data/labels.jsonl) and the judge adjudications (data/adjudications.jsonl) directly -- not
samples.jsonl, landing_events.json or any analysis module -- plus the committed forecasts (predictions/units/*.json),
and recomputes: the number of landing events, r_u / t_u / q_lik top-1 hits, L1a, L1b (b, c, sign-test p), the mean
log-score differences base - q_lik and base - q_tail, L2, and the M Spearman rho for beta and twin modal share
(Monte Carlo permutation p). Placebos, each of which must FAIL: L1b with r_u replaced by a random non-default mode;
M with E_u permuted across units; log-score D with q_base replaced by a random Dirichlet forecast.
Writes results/rederive_headlines.json. Usage: python audit/rederive_headlines.py"""

from __future__ import annotations

import hashlib
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def jl(p):
    return [json.loads(l) for l in (ROOT / p).read_text().splitlines() if l.strip()]


def main() -> None:
    adj = {r["key"]: r for r in jl("data/adjudications.jsonl")}
    lab = {}
    for l in jl("data/labels.jsonl"):
        f = l.get("label")
        if f is None:
            a = adj.get(l["key"])
            f = (a.get("label") or "disputed") if a else "disputed"
        lab[l["key"]] = (f, bool(l.get("passed")), bool(l.get("valid")))
    P = {p.stem: json.loads(p.read_text()) for p in (ROOT / "predictions" / "units").glob("*.json")}
    rows = defaultdict(list)
    for r in jl("data/raw_hf.jsonl"):
        if r["arm"] == "PAD" or r.get("shadow"):
            continue
        k = f"{r['unit']}|{r['template']}|{r['arm']}|{r['slot']}|instruct|hf"
        f, ok, _ = lab[k]
        rows[r["unit"]].append((r["arm"], r["slot"], f, ok))
    base = defaultdict(list)
    for r in jl("data/raw_vllm.jsonl"):
        if r["model_tag"] == "base" and r["arm"] in ("BASE", "PLAIN"):
            k = f"{r['unit']}|{r['template']}|{r['arm']}|{r['slot']}|base|vllm"
            base[r["unit"]].append(lab[k])

    def stats(rs, D, cat):
        rs = [x for x in rs if x[2] != "disputed"]
        n = len(rs)
        ok = sum(1 for x in rs if x[3])
        off = sum(1 for x in rs if x[3] and x[2] in cat and x[2] != D)
        return n, ok, off

    ev, E, l2n, l2abs = [], {}, 0, 0
    for u, rec in P.items():
        D, cat = rec["default"], rec["catalogue"]
        R = rows[u]
        n_t, ok_t, off_t = stats([x for x in R if x[0] == "TWINHF"], D, cat)
        tp, to = ok_t / n_t, off_t / n_t
        p0 = (off_t + 0.5) / (n_t + 1)
        pools = {"ESC": [], "PN": [], "GTN": []}
        conf = Counter()
        for arm in sorted({x[0] for x in R if x[0] != "TWINHF"}):
            cell = [x for x in R if x[0] == arm]
            n, ok, off = stats(cell, D, cat)
            fam = arm.split("_")[0]
            if fam == "ESC":
                n1, ok1, off1 = stats([x for x in cell if x[1] in (0, 1)], D, cat)
                if n1 and off1 / n1 >= to + 0.2 and ok1 / n1 >= 0.8 * tp and n >= 25:
                    pv = sum(math.comb(n, i) * p0 ** i * (1 - p0) ** (n - i) for i in range(off, n + 1))
                    conf[arm.split("_a")[1]] += pv < 0.05
            if n and ok / n >= 0.8 * tp:
                pools[fam] += cell
        E[u] = sum(conf.values()) / 24
        sup = Counter(f for f, ok, val in base[u] if val)
        for x in R:
            if x[0] != "TWINHF" and x[3] and x[2] in cat and x[2] != D:
                l2n += 1
                l2abs += sup.get(x[2], 0) == 0
        for t, cell in pools.items():
            c = Counter(x[2] for x in cell if x[3] and x[2] in cat and x[2] != D)
            tot = sum(c.values())
            if tot < 5:
                continue
            top = c.most_common()
            lead = (top[0][1] - (top[1][1] if len(top) > 1 else 0)) / tot
            ev.append({"u": u, "t": t, "counts": dict(c), "modal": top[0][0] if lead >= 0.15 else None,
                       "rec": rec})

    def hit(e, f):
        return f is not None and e["modal"] == f

    def sign_p(b, c):
        n = b + c
        return 1.0 if n == 0 else sum(math.comb(n, i) for i in range(b, n + 1)) / 2 ** n

    def l1b(evs, ru_of):
        dis = [e for e in evs if e["rec"]["discordant"]]
        b = sum(1 for e in dis if hit(e, ru_of(e)) and not hit(e, e["rec"]["q_lik_top1"]))
        c = sum(1 for e in dis if hit(e, e["rec"]["q_lik_top1"]) and not hit(e, ru_of(e)))
        return len(dis), b, c, sign_p(b, c)

    def mean_ls(e, vec):
        nd = [m for m in e["rec"]["catalogue"] if m != e["rec"]["default"]]
        q = {m: float((vec or {}).get(m, 0.0) or 0.0) for m in nd}
        z = sum(q.values())
        q = {m: (v / z if z > 0 else 1 / len(nd)) for m, v in q.items()}
        tot = sum(e["counts"].values())
        return sum(n * math.log(max(q[m], 1e-12)) for m, n in e["counts"].items()) / tot

    nd_b = l1b(ev, lambda e: e["rec"]["r_u"])
    tail_ev = [e for e in ev if e["rec"]["tail_empty"]]
    D_qlik = sum(mean_ls(e, e["rec"]["q_base"]) - mean_ls(e, e["rec"]["q_lik"]) for e in ev) / len(ev)
    D_tail = sum(mean_ls(e, e["rec"]["q_base"]) - mean_ls(e, e["rec"]["q_tail"]) for e in ev) / len(ev)

    def ranks(xs):
        o = sorted(range(len(xs)), key=lambda i: xs[i])
        r = [0.0] * len(xs)
        i = 0
        while i < len(o):
            j = i
            while j + 1 < len(o) and xs[o[j + 1]] == xs[o[i]]:
                j += 1
            for k in range(i, j + 1):
                r[o[k]] = (i + j) / 2
            i = j + 1
        return r

    def rho(x, y):
        a, b = ranks(x), ranks(y)
        ma, mb = sum(a) / len(a), sum(b) / len(b)
        num = sum((p - ma) * (q - mb) for p, q in zip(a, b))
        den = math.sqrt(sum((p - ma) ** 2 for p in a) * sum((q - mb) ** 2 for q in b))
        return num / den if den else 0.0

    us = sorted(P)
    Ev = [E[u] for u in us]
    rng = random.Random(0)

    def perm_p(x, y, sgn, R=20000):
        obs = sgn * rho(x, y)
        cnt = sum(1 for _ in range(R) if sgn * rho(x, rng.sample(y, len(y))) >= obs - 1e-12)
        return (cnt + 1) / (R + 1)
    tms = [P[u]["M"]["twin_modal_share"] for u in us]
    beta = [P[u]["M"]["beta"] for u in us]
    m_res = {"twin_modal_share": {"rho": rho(tms, Ev), "p_one_sided_mc": perm_p(tms, Ev, -1)},
             "beta": {"rho": rho(beta, Ev), "p_one_sided_mc": perm_p(beta, Ev, +1)}}
    # ---- placebos (each must fail)
    pl_b = []
    for _ in range(2000):
        pick = {u: rng.choice([m for m in P[u]["catalogue"] if m != P[u]["default"]]) for u in us}
        pl_b.append(l1b(ev, lambda e: pick[e["u"]])[3] < 0.05)
    pl_m = []
    for _ in range(200):
        Ep = rng.sample(Ev, len(Ev))
        pl_m.append(perm_p(tms, Ep, -1, R=2000) < 0.05)
    pl_d = []
    for _ in range(2000):
        dd = []
        for e in ev:
            nd = [m for m in e["rec"]["catalogue"] if m != e["rec"]["default"]]
            g = [rng.gammavariate(1.0, 1.0) for _ in nd]
            dd.append(mean_ls(e, dict(zip(nd, g))) - mean_ls(e, e["rec"]["q_lik"]))
        pl_d.append(sum(dd) / len(dd))
    out = {"n_existing_events": len(ev), "events": [(e["u"], e["t"], e["modal"]) for e in ev],
           "r_u_hits": sum(1 for e in ev if hit(e, e["rec"]["r_u"])),
           "t_u_hits_defined": [sum(1 for e in ev if e["rec"]["t_u"] and hit(e, e["rec"]["t_u"])),
                                sum(1 for e in ev if e["rec"]["t_u"])],
           "q_lik_hits": sum(1 for e in ev if hit(e, e["rec"]["q_lik_top1"])),
           "L1a": {"n": len(tail_ev), "hits": sum(1 for e in tail_ev if hit(e, e["rec"]["r_u"]))},
           "L1b": {"n": nd_b[0], "b": nd_b[1], "c": nd_b[2], "p": nd_b[3]},
           "mean_D_base_minus_qlik": D_qlik, "mean_D_base_minus_qtail": D_tail,
           "L2": {"N": l2n, "in_base_absent_modes": l2abs}, "E_u": dict(zip(us, Ev)), "M": m_res,
           "placebo_L1b_random_r_u_share_p_lt_0.05": sum(pl_b) / len(pl_b),
           "placebo_M_permuted_E_share_p_lt_0.05": sum(pl_m) / len(pl_m),
           "placebo_D_random_dirichlet_vs_qlik_mean": sum(pl_d) / len(pl_d),
           "placebo_D_share_ge_observed": sum(1 for d in pl_d if d >= D_qlik) / len(pl_d)}
    # ---- comparison with the reported numbers
    pool = json.loads((ROOT / "results" / "pool_l1_panelI.json").read_text())
    rep = {"n_events": pool["n_events"], "L1b": [pool["per_event"]["L1b"]["n_discordant"],
                                                 pool["per_event"]["L1b"]["b_base_only"],
                                                 pool["per_event"]["L1b"]["c_qlik_only"]],
           "r_u_hits": pool["per_event"]["r_u_top1_all_events"]["hits"],
           "D_qlik": pool["per_event"]["log_scores"]["q_lik"]["all"]["mean_D"],
           "D_tail": pool["per_event"]["log_scores"]["q_tail"]["all"]["mean_D"]}
    out["matches_reported"] = {
        "n_events": rep["n_events"] == out["n_existing_events"],
        "L1b": rep["L1b"] == [out["L1b"]["n"], out["L1b"]["b"], out["L1b"]["c"]],
        "r_u_hits": rep["r_u_hits"] == out["r_u_hits"],
        "D_qlik": abs(rep["D_qlik"] - D_qlik) < 1e-9, "D_tail": abs(rep["D_tail"] - D_tail) < 1e-9}
    (ROOT / "results" / "rederive_headlines.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k not in ("events", "E_u")}, indent=1))


if __name__ == "__main__":
    main()
