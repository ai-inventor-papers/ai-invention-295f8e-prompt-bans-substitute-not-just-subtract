#!/usr/bin/env python3
"""Audit of the STATISTICAL headline numbers, through code paths separate from src/ (no import from src/ or scipy).

From data/raw_gen.jsonl, data/labels.jsonl and the committed predictions/forecasts.json it recomputes:
  * the frozen default D per task (decision set = FP8 pilot + bf16 B1; modal correct label if >= 10 correct and a
    lead >= 2, else modal attempted label);
  * per-event smoothed log scores, gate, disagreement and the four paired differences on disagreeing gated events;
  * exact two-sided Wilcoxon signed-rank p-values by full enumeration of the 2^n sign-flip null, then Holm;
  * top-1 hit counts on gated events and exact one-sided binomial p-values (math.comb).
Placebos (each must FAIL, i.e. not reproduce the effect):
  A. the four family log scores permuted within every disagreeing gated event (1,000x): Holm-rejection rate of the
     SUBTRACT-PROXIMITY and LADDER-PROXIMITY tests;
  B. a random top-1 predictor (uniform over S, 1,000 draws): rate of binomial p < 0.05.
Writes results/independent_rederivation_tests.json and compares every number with results/analysis.json."""

from __future__ import annotations

import itertools
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

WS = Path(__file__).resolve().parent.parent
FAM = ["SUBTRACT", "LADDER", "ASSOCIATE", "PROXIMITY"]
PAIRS = [("SUBTRACT", "ASSOCIATE"), ("SUBTRACT", "PROXIMITY"), ("LADDER", "ASSOCIATE"), ("LADDER", "PROXIMITY")]


def jl(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]


def qdist(f, S):
    bins = S + ["other"]
    if not f:
        f = {b: 1.0 for b in bins}
    tot = sum(max(f.get(b, 0.0), 0.0) for b in bins)
    return {b: 0.93 * max(f.get(b, 0.0), 0.0) / tot + (0.05 / len(S) if b in S else 0.0) + (0.02 if b == "other" else 0.0)
            for b in bins}


def wilcoxon_exact(d: list[float]) -> float:
    d = [x for x in d if x != 0.0]
    n = len(d)
    order = sorted(range(n), key=lambda i: abs(d[i]))
    ranks = [0.0] * n
    i = 0
    while i < n:  # average ranks for ties in |d|
        j = i
        while j + 1 < n and abs(d[order[j + 1]]) == abs(d[order[i]]):
            j += 1
        for k in range(i, j + 1):
            ranks[order[k]] = (i + j) / 2 + 1
        i = j + 1
    w_obs = sum(r for r, x in zip(ranks, d) if x > 0)
    null = [sum(r for r, s in zip(ranks, signs) if s) for signs in itertools.product((0, 1), repeat=n)]
    lo = sum(1 for w in null if w <= w_obs + 1e-12) / len(null)
    hi = sum(1 for w in null if w >= w_obs - 1e-12) / len(null)
    return min(1.0, 2 * min(lo, hi))


def holm(p: dict[str, float]) -> dict[str, bool]:
    items = sorted(p.items(), key=lambda kv: kv[1])
    out, stop = {}, False
    for i, (k, v) in enumerate(items):
        ok = (not stop) and v <= 0.05 / (len(items) - i)
        stop = stop or not ok
        out[k] = ok
    return out


def binom_upper(k: int, n: int, p0: float) -> float:
    return sum(math.comb(n, j) * p0 ** j * (1 - p0) ** (n - j) for j in range(k, n + 1))


def main() -> None:
    raw = {r["row_id"]: r for r in jl(WS / "data" / "raw_gen.jsonl")}
    lab = {r["row_id"]: r for r in jl(WS / "data" / "labels.jsonl")}
    fcs = json.loads((WS / "predictions" / "forecasts.json").read_text())["events"]
    ev = json.loads((WS / "predictions" / "events.json").read_text())
    an = json.loads((WS / "results" / "analysis.json").read_text())
    out: dict = {}
    # ---- D per task from raw labels (decision set = pilot + B1; every homogeneity p was >= 0.01)
    dec = defaultdict(list)
    for rid, l in lab.items():
        if l.get("phase") in ("pilot", "B1"):
            dec[l["task"]].append(l)
    dmatch = {}
    for t, info in ev["tasks"].items():
        modes = list(fcs[f"{t}|modal|{info['D']}"]["S"]) + [info["D"]]
        corr = Counter(l["label"] for l in dec[t] if l.get("passed") and l["label"] in modes)
        att = Counter(l["label"] for l in dec[t] if l["label"] in modes)
        rk = corr.most_common()
        lead = rk[0][1] - (rk[1][1] if len(rk) > 1 else 0) if rk else 0
        n_corr = sum(1 for l in dec[t] if l.get("passed") and l["label"] != "invalid")
        D = rk[0][0] if (n_corr >= 10 and lead >= 2) else att.most_common(1)[0][0]
        dmatch[t] = {"rederived": D, "frozen": info["D"], "match": D == info["D"]}
    out["D_per_task"] = dmatch
    # ---- per-event scores
    ban = defaultdict(list)
    for rid, r in raw.items():
        if r.get("phase") in ("G1", "G2") and rid in lab:
            ban[r["event_id"]].append(lab[rid]["label"])
    rows = []
    for eid, fc in fcs.items():
        X, S = fc["X"], fc["S"]
        att = [l for l in ban[eid] if l not in ("invalid", "unresolved")]
        nb = [l for l in att if l != X and l in S + ["other"]]
        avoid = 1 - att.count(X) / len(att)
        gate = avoid >= 0.5 and len(nb) >= 20
        c = Counter(nb)
        if fc["event_type"] == "modal":
            hit = sorted(c, key=lambda k: (-c[k], k))[0]
        else:
            share = {k: c.get(k, 0) / len(nb) - fc["B_S"].get(k, 0.0) for k in S}
            hit = max(S, key=lambda k: (share[k], -S.index(k)))
        ls, top = {}, {}
        for f in FAM:
            fam = fc["families"][f]
            q = qdist(fam["f"] if fam["defined"] else None, S)
            ls[f] = sum(math.log(q[l]) for l in nb) / len(nb)
            top[f] = fam["top1"] if fam["defined"] else None
        dis = len({v for v in top.values() if v is not None}) > 1
        rows.append({"eid": eid, "task": fc["task"], "gate": gate, "dis": dis, "ls": ls, "top": top, "hit": hit,
                     "chance": 1 / len(S), "S": S})
    gd = [r for r in rows if r["gate"] and r["dis"]]
    out["n_gated"] = sum(r["gate"] for r in rows)
    out["n_disagreeing_gated"] = len(gd)
    pv, md = {}, {}
    for a, b in PAIRS:
        d = [r["ls"][a] - r["ls"][b] for r in gd]
        pv[f"{a}-{b}"] = wilcoxon_exact(d)
        md[f"{a}-{b}"] = sum(d) / len(d)
    hh = holm(pv)
    rep = an["c1"]["wilcoxon"]
    out["wilcoxon"] = {k: {"mean_diff": md[k], "p_exact_enumeration": pv[k], "holm_reject": hh[k],
                           "reported_mean": rep[k]["mean_diff"], "reported_p": rep[k]["p"],
                           "reported_reject": rep[k]["reject"],
                           "match": abs(md[k] - rep[k]["mean_diff"]) < 1e-9 and abs(pv[k] - rep[k]["p"]) < 1e-9
                           and hh[k] == rep[k]["reject"]} for k in pv}
    gated = [r for r in rows if r["gate"]]
    hits = {}
    for f in FAM:
        hh_ = [r for r in gated if r["top"][f] is not None]
        k = sum(1 for r in hh_ if r["top"][f] == r["hit"])
        p0 = sum(r["chance"] for r in hh_) / len(hh_)
        rp = an["c1"]["top1_hits_gated"][f]
        hits[f] = {"hits": k, "n": len(hh_), "chance": p0, "p_binom_exact": binom_upper(k, len(hh_), p0),
                   "reported": [rp["hits"], rp["n"], rp["p_binom"]],
                   "match": k == rp["hits"] and len(hh_) == rp["n"] and abs(binom_upper(k, len(hh_), p0) - rp["p_binom"]) < 1e-9}
        hits[f]["_rows"] = None
    out["top1_hits"] = hits
    # ---- placebo A: permute family labels within each disagreeing gated event
    rng = random.Random(0)
    rej = Counter()
    for _ in range(1000):
        perm_rows = []
        for r in gd:
            vals = [r["ls"][f] for f in FAM]
            rng.shuffle(vals)
            perm_rows.append(dict(zip(FAM, vals)))
        pp = {f"{a}-{b}": wilcoxon_exact([x[a] - x[b] for x in perm_rows]) for a, b in PAIRS}
        for k, v in holm(pp).items():
            rej[k] += int(v)
    out["placebo_family_permutation"] = {"n_perm": 1000, "holm_rejection_rate": {k: rej[k] / 1000 for k, _ in pv.items()},
                                         "fails_as_required": all(rej[k] / 1000 <= 0.10 for k in pv)}
    # ---- placebo B: random top-1 predictor
    rng = random.Random(1)
    sig, mean_hits = 0, 0.0
    for _ in range(1000):
        k = sum(1 for r in gated if rng.choice(r["S"]) == r["hit"])
        p0 = sum(r["chance"] for r in gated) / len(gated)
        sig += int(binom_upper(k, len(gated), p0) < 0.05)
        mean_hits += k / 1000
    out["placebo_random_top1"] = {"n_draws": 1000, "n_gated": len(gated), "rate_p_below_0.05": sig / 1000,
                                  "mean_hits": mean_hits, "fails_as_required": sig / 1000 <= 0.10}
    out["all_match"] = (all(v["match"] for v in out["wilcoxon"].values()) and all(v["match"] for v in hits.values())
                        and all(v["match"] for v in dmatch.values()) and out["n_gated"] == an["c1"]["n_gated"]
                        and out["n_disagreeing_gated"] == an["c1"]["n_disagreeing_gated"])
    for v in hits.values():
        v.pop("_rows", None)
    (WS / "results" / "independent_rederivation_tests.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({"all_match": out["all_match"], "n_gated": out["n_gated"], "n_dg": out["n_disagreeing_gated"],
                      "wilcoxon": {k: [round(v["mean_diff"], 3), round(v["p_exact_enumeration"], 4), v["holm_reject"], v["match"]]
                                   for k, v in out["wilcoxon"].items()},
                      "hits": {k: [v["hits"], v["n"], round(v["p_binom_exact"], 4), v["match"]] for k, v in hits.items()},
                      "D_all_match": all(v["match"] for v in dmatch.values()),
                      "placeboA": out["placebo_family_permutation"], "placeboB": out["placebo_random_top1"]}, indent=1))


if __name__ == "__main__":
    main()
