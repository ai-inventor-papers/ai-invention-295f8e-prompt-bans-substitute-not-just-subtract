#!/usr/bin/env python3
"""F8: independent re-derivation of every headline number with the Python standard library only (json, math, random),
straight from the raw rows (data/samples_raw.jsonl, data/labels.jsonl) and the committed predictions
(results/predictions_view.json, predictions/predictions_raw.json, predictions/collapsed_raw.json); compared with the
analysis outputs (results/test1.json, test2.json, test3.json). Placebo: the temperature labels are permuted within
each slot; the drop test must then fail."""

import json
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPS = (0.3, 0.7, 1.0, 1.3)
SAMPLERS = ("p1", "k10")
TEMPLATES = ("W1", "W2", "W3", "W4", "W5")
SLOTS = tuple(range(20, 30))


def jl(p):
    with open(p) as fh:
        return [json.loads(l) for l in fh if l.strip()]


def mcnemar(b, c):
    n = b + c
    if n == 0:
        return 1.0
    return sum(math.comb(n, k) for k in range(b, n + 1)) / 2 ** n


def ent(p):
    return -sum(x * math.log2(x) for x in p if x > 0)


def main():
    labs = {r["sid"]: r for r in jl(ROOT / "data" / "labels.jsonl")}
    jp = ROOT / "data" / "judge_labels.jsonl"
    judged = {r["sid"]: r["label"] for r in jl(jp) if r.get("label")} if jp.exists() else {}
    rows = []
    for r in jl(ROOT / "data" / "samples_raw.jsonl"):
        if r["sid"] not in labs:
            continue
        y = labs[r["sid"]]["label"]
        if y == "disputed" and r["sid"] in judged:
            y = judged[r["sid"]]
        rows.append(dict(r, label=y, passed=labs[r["sid"]]["passed"]))
    pv = json.loads((ROOT / "results" / "predictions_view.json").read_text())
    t1 = json.loads((ROOT / "results" / "test1.json").read_text())
    t2 = json.loads((ROOT / "results" / "test2.json").read_text())
    t3 = json.loads((ROOT / "results" / "test3.json").read_text())
    raw = json.loads((ROOT / "predictions" / "predictions_raw.json").read_text())
    checks, mism = [], []

    def chk(name, a, b, tol=1e-9):
        ok = (a is None and b is None) or (a is not None and b is not None and abs(a - b) <= tol)
        checks.append({"check": name, "rederived": a, "reported": b, "ok": ok})
        if not ok:
            mism.append(name)

    placebo = {}
    pooled_b = pooled_c = 0
    for u, U in pv["units"].items():
        A = U["A_min"]
        tab = {}
        for r in rows:
            if r["unit"] == u and r["arm"] == "SWEEP":
                tab[(r["cell"], r["template"], r["slot"])] = r
        if not tab:
            continue
        errs = []
        for T in TEMPS:
            for s in SAMPLERS:
                cell = "T%s_%s" % (T, s)
                rr = [tab[(cell, w, k)] for w in TEMPLATES for k in SLOTS if (cell, w, k) in tab]
                sh = sum(r["label"] == A for r in rr) / len(rr)
                chk(u + "|" + cell + "|a_min_share", sh, t2["per_unit"][u]["cells"][cell]["a_min"])
                errs.append(abs(sh - U["cells"][cell]["a_min"]))
        chk(u + "|MAE", sum(errs) / len(errs), t2["per_unit"][u]["MAE"])
        keys = [(w, k) for w in TEMPLATES for k in SLOTS]
        x10 = [tab[("T1.0_p1", w, k)]["label"] == A for w, k in keys]
        x03 = [tab[("T0.3_p1", w, k)]["label"] == A for w, k in keys]
        x13 = [tab[("T1.3_p1", w, k)]["label"] == A for w, k in keys]
        b = sum(a and not c for a, c in zip(x10, x03))
        c = sum(c and not a for a, c in zip(x10, x03))
        if u in ("B3", "A3"):
            pooled_b += b
            pooled_c += c
        chk(u + "|delta_obs_10_03", (sum(x10) - sum(x03)) / len(keys), t2["per_unit"][u]["delta_obs_10_03"])
        chk(u + "|mcnemar_p", mcnemar(b, c), t2["per_unit"][u]["mcnemar_p_one_sided"])
        chk(u + "|delta_obs_10_13", (sum(x13) - sum(x10)) / len(keys), t2["per_unit"][u]["delta_obs_10_13"])
        # placebo: permute the four temperature labels within each slot (top-p 1), 500 times
        rng = random.Random(7)
        n_pass = 0
        for _ in range(500):
            perm_x10, perm_x03 = [], []
            for w, k in keys:
                vals = [tab[("T%s_p1" % T, w, k)]["label"] == A for T in TEMPS]
                rng.shuffle(vals)
                perm_x03.append(vals[0])
                perm_x10.append(vals[2])
            bb = sum(a and not cc for a, cc in zip(perm_x10, perm_x03))
            cc_ = sum(cc and not a for a, cc in zip(perm_x10, perm_x03))
            d = (sum(perm_x10) - sum(perm_x03)) / len(keys)
            n_pass += d >= 0.15 and mcnemar(bb, cc_) < 0.05
        placebo[u] = {"placebo_drop_test_pass_rate": n_pass / 500,
                      "observed_drop_test_pass": bool(t2["per_unit"][u]["delta_obs_10_03"] >= 0.15 and
                                                      t2["per_unit"][u]["mcnemar_p_one_sided"] < 0.05)}
    if "pooled_B3_A3" in t2:
        chk("pooled_mcnemar_p", mcnemar(pooled_b, pooled_c), t2["pooled_B3_A3"]["p"])
    # S4(b): exchange vs padding twin, exact one-sided McNemar on the shared slots; attempted shares per arm
    s4b_p = ROOT / "results" / "s4b.json"
    if s4b_p.exists():
        s4b = json.loads(s4b_p.read_text())
        for u, U in pv["units"].items():
            if u not in s4b:
                continue
            A = U["A_min"]
            arms = {}
            for r in rows:
                if r["unit"] == u and r["arm"] == "S4B":
                    arms.setdefault(r["cell"], {})[r["slot"]] = r["label"] == A
            for a, d in arms.items():
                chk(u + "|S4B|" + a + "|attempted", sum(d.values()) / len(d), s4b[u]["arms"][a]["attempted_a_min"])
            if "EXCH" in arms and "FORCEDPAD" in arms:
                ks = sorted(set(arms["EXCH"]) & set(arms["FORCEDPAD"]))
                b = sum(arms["EXCH"][k] and not arms["FORCEDPAD"][k] for k in ks)
                c = sum(arms["FORCEDPAD"][k] and not arms["EXCH"][k] for k in ks)
                chk(u + "|S4B|exchange_vs_pad_p", mcnemar(b, c), s4b[u]["exchange_vs_pad"]["p_one_sided"])
    # S0 twins: A_min shares straight from the rows
    tw_p = ROOT / "results" / "twins.json"
    if tw_p.exists():
        tw = json.loads(tw_p.read_text())
        for u, v in tw.items():
            rr = [r for r in rows if r["unit"] == u and r["arm"] == "TWIN"]
            raw_share = sum(labs[r["sid"]]["label"] == v["a_min"] for r in rr) / len(rr)
            chk(u + "|twin_a_min_share", raw_share, v["share_a_min"])
    # Test 1: H(A | C) from the raw token-conditional counts
    for u, R in raw.items():
        C = R["cats"]
        covs = {cid: cl["cov"] for cid, cl in R["clusters"].items()}
        ws = sum(covs.values())
        joint = {}
        for cid, cl in R["clusters"].items():
            items = [(cl["counts"][t], cl["pi1_avg"][t]) for t in cl["pi1_avg"]]
            items.append((cl["resid_counts"], max(0.0, 1 - sum(cl["pi1_avg"].values()))))
            for cnt, m in items:
                n = sum(cnt)
                if n == 0:
                    continue
                ph = [x / n for x in cnt]
                cls = C[max(range(len(C)), key=lambda i: ph[i])]
                v = joint.setdefault(cls, [0.0] * len(C))
                for i in range(len(C)):
                    v[i] += covs[cid] / ws * m * ph[i]
        tot = sum(sum(v) for v in joint.values())
        H = sum(sum(v) / tot * ent([x / sum(v) for x in v]) for v in joint.values() if sum(v) > 0)
        chk(u + "|H_bits", H, t1["per_unit"][u]["H_bits"], 1e-6)
    # Test 3: margins straight from the collapsed raw numbers (single-token alternative class)
    col = ROOT / "predictions" / "collapsed_raw.json"
    if col.exists():
        for t, r in json.loads(col.read_text()).items():
            if r.get("alt_class_tokens"):
                alt = sum(r["pi1"][str(x)] for x in r["alt_class_tokens"])
                rest = sum(v for k, v in r["pi1"].items() if int(k) not in r["alt_class_tokens"])
                rest += 1 - sum(r["pi1"].values())
                chk(t + "|margin_nats", math.log(rest) - math.log(alt), t3["per_task"][t]["margin_nats"], 1e-6)
            else:
                chk(t + "|margin_nats(path)", r["margin_nats"], t3["per_task"][t]["margin_nats"], 1e-9)
    out = {"n_checks": len(checks), "n_mismatch": len(mism), "mismatches": mism, "checks": checks,
           "placebo": placebo}
    (ROOT / "results" / "rederive.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k != "checks"}, indent=1))


if __name__ == "__main__":
    main()
