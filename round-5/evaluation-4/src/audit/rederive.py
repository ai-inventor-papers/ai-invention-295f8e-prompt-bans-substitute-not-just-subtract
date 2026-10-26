#!/usr/bin/env python3
"""Independent re-derivation (STANDARD LIBRARY ONLY; no code shared with eval.py, src/ or rivals/).

Recomputes from raw rows: the (0a) confusion matrix, balanced accuracy, Fisher p and Spearman under both measures;
the exp20 S1/S2/S5 counts and the find-duplicate 12:0 McNemar; the (0c) matched-event log-score means; the PNPLAIN
off-default shares; the split-half values (two stored sources); every frozen rival value; every rival Spearman with
E_pool.  Placebos that must FAIL: E permuted across tasks (rival-rho rejection about 5%), S0/S1 labels swapped within
slot (OR about 1), landing labels shuffled across events (difference shrinks toward 0), escape fractions permuted in
(0a) (BA about 0.5).  Output: audit/rederive.json (every check with |diff|, tolerance and pass/fail).
"""

import ast
import json
import math
import os
import random
import re
import statistics
from collections import Counter
from pathlib import Path

WS = Path(__file__).resolve().parent.parent
# dependency folders (same convention as the rest of the artifact, re-implemented here so that no code is shared):
# <AII_DEPS_ROOT>/<artifact_id>, AII_DEPS_ROOT defaulting to this workspace's parent; AII_DEP_<id> overrides one
ROOT = Path(os.environ.get("AII_DEPS_ROOT", str(WS.parent)))


def dep(art_id):
    return Path(os.environ.get("AII_DEP_" + re.sub(r"\W", "_", art_id), str(ROOT / art_id)))


E19, E20, E22, E23 = dep("art_mWn-MQEnNelg"), dep("art_Cx9JOh8soBw7"), dep("art_SHaWv77P1XCI"), dep("art_k6nzFCDLOjQP")
BENCH = dep("art_0ndRfWKBWclR")
RNG = random.Random(20261021)
CHECKS = []


def rd_jsonl(p, needle=None):
    out = []
    with open(p) as fh:
        for ln in fh:
            if ln.strip() and (needle is None or needle in ln):
                out.append(json.loads(ln))
    return out


def tb(v):
    return v is True or v == "True"


def check(name, mine, theirs, tol):
    # stored eval values are rounded to 6 decimals: a float comparison never needs to be tighter than 1e-6
    tol = tol if tol == 0 else max(tol, 1e-6)
    if isinstance(mine, (list, tuple)):
        ok = len(mine) == len(theirs) and all(abs(a - b) <= tol + 1e-9 for a, b in zip(mine, theirs))
        diff = max(abs(a - b) for a, b in zip(mine, theirs)) if ok or len(mine) == len(theirs) else None
    elif mine is None or theirs is None:
        ok, diff = mine is None and theirs is None, None
    else:
        diff = abs(mine - theirs)
        ok = diff <= tol + 1e-9
    CHECKS.append({"check": name, "audit_value": mine, "eval_value": theirs, "abs_diff": diff, "tolerance": tol,
                   "pass": bool(ok)})


def ranks(x):
    order = sorted(range(len(x)), key=lambda i: x[i])
    r = [0.0] * len(x)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and x[order[j + 1]] == x[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def pearson(a, b):
    ma, mb = statistics.fmean(a), statistics.fmean(b)
    sa = math.sqrt(sum((x - ma) ** 2 for x in a))
    sb = math.sqrt(sum((y - mb) ** 2 for y in b))
    if sa == 0 or sb == 0:
        return None
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / (sa * sb)


def spearman(a, b):
    return pearson(ranks(a), ranks(b)) if len(a) >= 3 else None


def ba(pred, obs):
    pos = [p for p, o in zip(pred, obs) if o == 1]
    neg = [p for p, o in zip(pred, obs) if o == 0]
    if not pos or not neg:
        return None
    return (sum(pos) / len(pos) + sum(1 - p for p in neg) / len(neg)) / 2


def fisher_two_sided(a, b, c, d):
    n1, n2, m1, n = a + b, c + d, a + c, a + b + c + d

    def hp(x):
        return math.comb(n1, x) * math.comb(n2, m1 - x) / math.comb(n, m1)
    p0 = hp(a)
    lo, hi = max(0, m1 - n2), min(n1, m1)
    return min(1.0, sum(hp(x) for x in range(lo, hi + 1) if hp(x) <= p0 * (1 + 1e-7)))


def table(pred, obs):
    return [[sum(1 for p, o in zip(pred, obs) if p == 1 and o == 1), sum(1 for p, o in zip(pred, obs) if p == 1 and o == 0)],
            [sum(1 for p, o in zip(pred, obs) if p == 0 and o == 1), sum(1 for p, o in zip(pred, obs) if p == 0 and o == 0)]]


# ------------------------------------------------------------------------------------------------ (0a)
def audit_0a(ev):
    rows = rd_jsonl(E23 / "data/samples.jsonl")
    pre = json.loads((E23 / "predictions/commit_preban.json").read_text())["tasks"]
    tasks = list(pre)
    E, A, drop = {}, {}, {}
    for t in tasks:
        d = pre[t]["D"]
        cat = set(pre[t]["survivors"]) | {d}
        ban = [x for x in rows if x["task"] == t and x["stage"] == "BAN" and x["arm"] == "ban"]
        tw = [x for x in rows if x["task"] == t and x["stage"] == "A" and x["arm"] == "twin"]
        A[t] = sum(1 for x in ban if x["label"] in cat and x["label"] != d) / len(ban)
        drop[t] = sum(1 for x in tw if x["label"] == d) / len(tw) - sum(1 for x in ban if x["label"] == d) / len(ban)
        conf = pre[t].get("confirm_cells") or {}
        E[t] = len({k.split("_")[0] for k, v in conf.items() if v.get("confirmed")}) / pre[t]["n_directions_run"]
    variants = {v["variant"]: v for v in ev["0a"]["variants"]}
    for label, meas, keep in (("primary: catalogue-only avoidance A_t", A, tasks),
                              ("sensitivity: default-share drop", drop, tasks),
                              ("without T1 and T2 (A_t)", A, [t for t in tasks if t not in ("T1", "T2")])):
        mv = [int(E[t] > 0) for t in keep]
        C = [int(meas[t] >= 0.5) for t in keep]
        tab = table(mv, C)
        mine_p = fisher_two_sided(tab[0][0], tab[0][1], tab[1][0], tab[1][1]) if len(set(mv)) > 1 and len(set(C)) > 1 else 1.0
        theirs = variants[label]
        check(f"0a {label}: table", [x for r_ in tab for x in r_], [x for r_ in theirs["table"] for x in r_], 0)
        check(f"0a {label}: BA", ba(mv, C), theirs["BA"], 1e-9)
        check(f"0a {label}: Fisher p", mine_p, theirs["fisher_p_two_sided"], 1e-6)
        check(f"0a {label}: Spearman", spearman([E[t] for t in keep], [meas[t] for t in keep]), theirs["spearman_rho"], 1e-9)
    # placebo: permuted escape fractions -> BA about 0.5
    C = [int(A[t] >= 0.5) for t in tasks]
    es = [E[t] for t in tasks]
    vals = []
    for _ in range(1000):
        p = es[:]
        RNG.shuffle(p)
        b = ba([int(v > 0) for v in p], C)
        if b is not None:
            vals.append(b)
    return {"placebo_0a_BA_mean": statistics.fmean(vals), "placebo_0a_expected": "about 0.5"}


# ------------------------------------------------------------------------------------------------ (0b)
def has_solve(code):
    if not code or code == "None":
        return False
    try:
        return any(isinstance(n, ast.FunctionDef) and n.name == "solve" for n in ast.walk(ast.parse(code)))
    except (SyntaxError, ValueError):
        return False


def audit_0b(ev):
    rows = rd_jsonl(E20 / "data/samples.jsonl")
    for x in rows:
        if x["label"] not in ("invalid", "unresolved", "disputed") and not has_solve(x.get("code")):
            x["label"] = "invalid"
    D = {}
    for t in {x["task"] for x in rows}:
        c = Counter(x["label"] for x in rows if x["task"] == t and x["arm"] == "TWIN" and tb(x["passed"]))
        D[t] = sorted(c, key=lambda k: (-c[k], k))[0]
    bad = ("other", "invalid", "disputed", "unknown", "unresolved", "None", None, "")
    sc = ev["0b"]["site_counts"]
    for site in ("S1", "S2", "S5"):
        corr = [x for x in rows if x["site"] == site and x["arm"] in (f"{site}_a1", f"{site}_a2", f"{site}_a4")
                and tb(x["passed"])]
        k = sum(1 for x in corr if x["label"] not in bad and x["label"] != D[x["task"]])
        check(f"0b {site} correct off-default, correct", [k, len(corr)],
              [sc[site]["n_correct_off_default"], sc[site]["n_correct"]], 0)
    s0 = {x["slot"]: x for x in rows if x["task"] == "T06" and x["arm"] == "S0_a2"}
    s3 = {x["slot"]: x for x in rows if x["task"] == "T06" and x["arm"] == "S3_a2"}

    def off(x):
        return x["label"] not in ("invalid", "unresolved", "disputed") and x["label"] != D[x["task"]]
    b = sum(1 for k in s0 if k in s3 and off(s0[k]) and not off(s3[k]))
    c = sum(1 for k in s0 if k in s3 and off(s3[k]) and not off(s0[k]))
    n = b + c
    p = min(1.0, 2 * sum(math.comb(n, i) for i in range(0, min(b, c) + 1)) / 2 ** n) if n else 1.0
    f = ev["0b"]["flips_S3_vs_S0"]["T06|2|attempts"]
    check("0b find duplicate S3:S0 flips (attempts)", [c, b], [f["S3_only"], f["S0_only"]], 0)
    check("0b McNemar exact p", p, f["mcnemar_p_exact"], 1e-9)
    em = ev["0b"]["energy_matched"]
    for t in ("T06", "T10"):
        corr = [x for x in rows if x["task"] == t and x["arm"] == "S1E_a1" and tb(x["passed"])]
        tw = [x for x in rows if x["task"] == t and x["arm"] == "TWIN" and tb(x["passed"])]
        k = sum(1 for x in corr if x["label"] not in bad and x["label"] != D[t])
        k_tw = sum(1 for x in tw if x["label"] not in bad and x["label"] != D[t])
        check(f"0b S1E excess {t}", k / len(corr) - k_tw / len(tw), em[f"S1E|{t}"]["excess"], 1e-9)
    # placebo: S0/S1 labels swapped within slot -> OR about 1
    pairs = []
    for a in ("1", "2", "4"):
        for t in D:
            x0 = {x["slot"]: x for x in rows if x["task"] == t and x["arm"] == f"S0_a{a}"}
            x1 = {x["slot"]: x for x in rows if x["task"] == t and x["arm"] == f"S1_a{a}"}
            pairs += [(off(x0[k]), off(x1[k])) for k in x0 if k in x1]

    def odds(pr):
        a_ = sum(1 for u, _ in pr if u) + 0.5
        b_ = sum(1 for u, _ in pr if not u) + 0.5
        c_ = sum(1 for _, v in pr if v) + 0.5
        d_ = sum(1 for _, v in pr if not v) + 0.5
        return (a_ * d_) / (b_ * c_)
    real = odds(pairs)
    pl = []
    for _ in range(200):
        sw = [(u, v) if RNG.random() < 0.5 else (v, u) for u, v in pairs]
        pl.append(odds(sw))
    return {"S0_vs_S1_OR_real": real, "placebo_swap_OR_median": statistics.median(pl),
            "placebo_swap_expected": "about 1"}


# ------------------------------------------------------------------------------------------------ (0c)
def audit_0c(ev):
    c3b = json.loads((E22 / "results/c3b.json").read_text())
    esc = json.loads((E22 / "results/escape.json").read_text())
    scr = json.loads((E22 / "results/screen.json").read_text())
    e13 = {e["task"]: e for e in rd_jsonl(E22 / "inputs/exp13/results/c1_events.jsonl")}
    cat = {}
    for td in (BENCH / "bench").iterdir():
        if (td / "spec.json").exists():
            cat[td.name.split("_")[0]] = [c["mode"] for c in json.loads((td / "spec.json").read_text())["catalogue"]]
    gated = c3b["gated_events"]

    def score(dist, S, labels):
        raw = dist if dist is not None else {m: 1 / len(S) for m in S}
        tot = sum(v for k, v in raw.items() if k in S or k == "other") if dist is not None else 1.0
        p = {m: 0.93 * raw.get(m, 0) / tot + 0.05 / len(S) for m in S}
        p["other"] = 0.93 * raw.get("other", 0) / tot + 0.02
        return statistics.fmean(math.log(p[l if l in p else "other"]) for l in labels)

    per = {}
    for t in gated:
        S = [m for m in cat[t] if m != e13[t]["banned"]]
        labels = [k for k, v in e13[t]["landing_counts"].items() for _ in range(v)]
        pv = esc.get(t, {}).get("push_landing_v4") or None
        per[t] = {"S": S, "labels": labels, "PUSH": pv, "ASSOC": e13[t]["forecasts"].get("ASSOCIATE"),
                  "push_defined": bool(pv)}
    d3 = [t for t in gated if per[t]["push_defined"]]
    m_push3 = statistics.fmean(score(per[t]["PUSH"], per[t]["S"], per[t]["labels"]) for t in d3)
    m_ass3 = statistics.fmean(score(per[t]["ASSOC"], per[t]["S"], per[t]["labels"]) for t in d3)
    m_push5 = statistics.fmean(score(per[t]["PUSH"], per[t]["S"], per[t]["labels"]) for t in gated)
    m_ass5 = statistics.fmean(score(per[t]["ASSOC"], per[t]["S"], per[t]["labels"]) for t in gated)
    tab = {r["forecast"]: r for r in ev["0c"]["table"]}
    check("0c PUSH mean on defined events", m_push3, tab["PUSH"]["mean_bench_push_defined"], 1e-6)
    check("0c ASSOCIATE mean on PUSH-defined events", m_ass3, tab["ASSOCIATE"]["mean_bench_push_defined"], 1e-6)
    check("0c PUSH mean over 5 (uniform fill)", m_push5, tab["PUSH"]["mean_bench_all_gated_uniform_fill"], 1e-6)
    check("0c ASSOCIATE mean over 5", m_ass5, tab["ASSOCIATE"]["mean_bench_all_gated_uniform_fill"], 1e-6)
    # placebo: landing labels shuffled across events -> PUSH - ASSOCIATE shrinks
    diffs = []
    for _ in range(1000):
        perm = gated[:]
        RNG.shuffle(perm)
        dd = []
        for t, u in zip(gated, perm):
            if per[t]["push_defined"]:
                lab = [l if l in per[t]["S"] else "other" for l in per[u]["labels"]]
                dd.append(score(per[t]["PUSH"], per[t]["S"], lab) - score(per[t]["ASSOC"], per[t]["S"], lab))
        diffs.append(statistics.fmean(dd))
    return {"landing_diff_real": m_push3 - m_ass3, "placebo_shuffled_landing_diff_mean": statistics.fmean(diffs),
            "placebo_landing_expected": "difference shrinks toward 0"}


# ------------------------------------------------------------------------------------------------ (0d) PNPLAIN
def audit_0d(ev):
    rows = rd_jsonl(E19 / "data/samples.jsonl", '"PN')
    tw = rd_jsonl(E19 / "data/samples.jsonl", '"TWIN"')
    for t, v in ev["0d"]["pnplain"].items():
        c = Counter(x["label"] for x in tw if x["task"] == t and x["arm"] == "TWIN" and tb(x["passed"]))
        d = sorted(c, key=lambda k: (-c[k], k))[0]
        for arm, key in (("PNPLAIN_a1", "PNPLAIN_a1"), ("PN_a1", "PN_a1_twin_frame")):
            xs = [x for x in rows if x["task"] == t and x["arm"] == arm]
            share = sum(1 for x in xs if x["label"] not in (d, "invalid", "disputed")) / len(xs)
            check(f"0d {t} {arm} off-default share", share, v[key]["off_default_share"], 1e-9)


# ------------------------------------------------------------------------------------------------ rivals
def audit_rivals():
    riv = json.loads((WS / "rivals.json").read_text())
    sc = json.loads((WS / "results/rival_scores.json").read_text())
    vals = riv["values"]
    D = riv["default_exp22_twin"]
    # R7 and the default from exp22 twin rows, de-duplicated by CRN seed
    seeds = {}
    for x in rd_jsonl(E22 / "data/samples_raw.jsonl", '"arm": "TWIN"'):
        seeds[f"{x['task']}|{x['template']}|{x['arm']}|{x['sample_id']}"] = x["seed"]
    seen, tw = set(), {}
    for x in rd_jsonl(E22 / "data/labels.jsonl", '"arm": "TWIN"'):
        s = seeds.get(x["key"])
        if x["arm"] != "TWIN" or s is None or (x["task"], s) in seen:
            continue
        seen.add((x["task"], s))
        tw.setdefault(x["task"], []).append(x)
    for t in riv["tasks"]:
        c = Counter(x["label"] for x in tw[t] if x["passed"])
        m = sorted(c, key=lambda k: (-c[k], k))[0]
        check(f"R7 {t}", c[m] / sum(c.values()), vals["R7"][t], 1e-6)
        CHECKS.append({"check": f"default {t}", "audit_value": m, "eval_value": D[t], "pass": m == D[t]})
    # R1 opening margin
    olp = json.loads((E22 / "results/opening_lp.json").read_text())["by_task"]
    for t in riv["tasks"]:
        if t in olp and D[t] in olp[t]:
            lpd = olp[t][D[t]]["lp_per_template"]
            oth = [v["lp_per_template"] for m, v in olp[t].items() if m != D[t] and v.get("lp_per_template")]
            mine = statistics.fmean(lpd[w] - max(o[w] for o in oth) for w in range(len(lpd)))
            check(f"R1 {t}", mine, vals["R1"][t], 1e-6)
    # R2 can rate, R3 clarity
    forced = rd_jsonl(BENCH / "data/samples_forced.jsonl")
    assoc = rd_jsonl(BENCH / "data/association.jsonl")
    ff = rd_jsonl(E22 / "inputs/exp7/data/freeform_labelled.jsonl")
    cat = {}
    for td in (BENCH / "bench").iterdir():
        if (td / "spec.json").exists():
            cat[td.name.split("_")[0]] = [c["mode"] for c in json.loads((td / "spec.json").read_text())["catalogue"]]
    for t in riv["tasks"]:
        if t not in ("T1", "T2"):
            cans = []
            for m in cat[t]:
                if m == D[t]:
                    continue
                rr = [x for x in forced if x["task"] == t and x["forced_mode"] == m and (x.get("paraphrase_id") or 0) >= 0]
                if rr:
                    cans.append(sum(1 for x in rr if x["passed"] and x["label"] == m) / len(rr))
            check(f"R2 {t}", max(cans), vals["R2"][t], 1e-6)
            ans = [x["mapped"] for x in assoc if x["task"] == t and x["X"] == D[t]]
        else:
            ans = [x["label"] for x in ff if x["task"] == t.lower() and x["X"] == D[t]]
        c = Counter(ans)
        check(f"R3 {t}", max(c.values()) / len(ans), vals["R3"][t], 1e-6)
    # R4 novelty excess (exp19)
    r19 = rd_jsonl(E19 / "data/samples.jsonl", '"arm": "TWIN"') + rd_jsonl(E19 / "data/samples.jsonl", '"arm": "NOVELTY"')
    bad = ("other", "invalid", "disputed", "unknown", "unlabelled", None, "None", "")
    for t in riv["tasks"]:
        def sh(arm):
            corr = [x for x in r19 if x["task"] == t and x["arm"] == arm and tb(x["passed"])]
            return sum(1 for x in corr if x["label"] not in bad and x["label"] != D[t]) / len(corr)
        check(f"R4 {t}", sh("NOVELTY") - sh("TWIN"), vals["R4"][t], 1e-6)
    # R6 runtime ratio from the timing file
    r6 = json.loads((WS / "rivals/r6_merit_raw.json").read_text())["rows"]
    for t in riv["tasks"]:
        det = riv["details"]["R6"].get(t) or {}
        if vals["R6"].get(t) is None:
            continue
        tk = t.lower() if t in ("T1", "T2") else t

        def med(m):
            return statistics.median(x["total_median_s"] for x in r6 if x["task"] == tk and x["mode"] == m and x["passes_all"])
        check(f"R6 {t}", med(det["runner_up"]) / med(D[t]), vals["R6"][t], 1e-6)
    # R8 + K
    u22 = json.loads((E22 / "results/units.json").read_text())["per_task"]
    for t in riv["tasks"]:
        if vals["R8"].get(t) is not None:
            check(f"R8 {t}", u22[t]["ratio_mean_nfree_over_mean_n"], vals["R8"][t], 1e-9)
        if t in cat:
            check(f"K {t}", float(len(cat[t])), vals["K"][t], 0)
    # R5: exact expected Hill-1 of a without-replacement subsample at depth min(20, n), by direct enumeration
    r5 = json.loads((WS / "rivals/r5_human_raw.json").read_text())["rows"]

    def exp_hill(counts, depth):
        counts = [c for c in counts if c > 0]
        n = sum(counts)
        d = min(depth, n)
        tot = 0.0

        def rec(i, left, prob_num, comp):
            nonlocal tot
            if i == len(counts) - 1:
                if left <= counts[i]:
                    ks = comp + [left]
                    pr = prob_num * math.comb(counts[i], left) / math.comb(n, d)
                    h = -sum((k / d) * math.log(k / d) for k in ks if k > 0)
                    tot += pr * math.exp(h)
                return
            for k in range(0, min(counts[i], left) + 1):
                rec(i + 1, left - k, prob_num * math.comb(counts[i], k), comp + [k])
        rec(0, d, 1, [])
        return tot
    for t in riv["tasks"]:
        if vals["R5"].get(t) is None:
            continue
        lab = Counter(x["final_label"] for x in r5 if x["task"] == t and x["role"] == "primary" and x["passed"]
                      and x["final_label"] not in (None, "unlabelled"))
        n = sum(lab.values())
        check(f"R5 {t}", exp_hill(list(lab.values()), min(20, n)), vals["R5"][t], 1e-6)
    # every rival Spearman with E_pool
    esc = json.loads((E22 / "results/escape.json").read_text())
    epool = {t: (esc[t]["E_t"]["1.0"]["n_confirmed"] + esc[t]["E_t"]["2.0"]["n_confirmed"]) /
             (esc[t]["E_t"]["1.0"]["n_run"] + esc[t]["E_t"]["2.0"]["n_run"]) for t in riv["tasks"]}
    for rv in ("R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8", "K"):
        tk = [t for t in riv["tasks"] if vals[rv].get(t) is not None]
        mine = spearman([vals[rv][t] for t in tk], [epool[t] for t in tk])
        check(f"Spearman {rv} vs E_pool", mine, sc["scores"][rv]["E_pool"]["rho"], 1e-9)
    # placebo: E permuted across tasks -> rejection rate about 5% (null from 2,000 permutations)
    rej = {}
    for rv in ("R4", "R6", "K"):
        tk = [t for t in riv["tasks"] if vals[rv].get(t) is not None]
        x = [vals[rv][t] for t in tk]
        y = [epool[t] for t in tk]
        null = []
        for _ in range(2000):
            yy = y[:]
            RNG.shuffle(yy)
            r_ = spearman(x, yy)
            null.append(abs(r_) if r_ is not None else 0.0)
        crit = sorted(null)[int(0.95 * len(null))]
        n_rej = 0
        for _ in range(1000):
            yy = y[:]
            RNG.shuffle(yy)
            r_ = spearman(x, yy)
            n_rej += int(r_ is not None and abs(r_) > crit)
        rej[rv] = n_rej / 1000
    return {"placebo_E_permuted_rejection_rate": rej, "placebo_E_expected": "about 0.05"}


def audit_split_half():
    rx = json.loads((E22 / "results/rederive_extra.json").read_text())["y_reliability"]
    ex = json.loads((E22 / "results/explore.json").read_text())["tasks"]
    for t, v in rx.items():
        check(f"split-half {t} (rederive_extra vs explore)", v["split_half_rho"],
              ex[t]["y_reliability"]["rho_template_halves"], 0.0006)


def main():
    ev = json.loads((WS / "results/corrections_metrics.json").read_text())
    out = {"stdlib_only": True, "seed": 20261021}
    out.update(audit_0a(ev))
    out.update(audit_0b(ev))
    out.update(audit_0c(ev))
    audit_0d(ev)
    audit_split_half()
    out.update(audit_rivals())
    out["checks"] = CHECKS
    out["n_checks"] = len(CHECKS)
    out["n_fail"] = sum(1 for c in CHECKS if not c["pass"])
    pl = out
    out["placebos_fail_as_required"] = {
        "0a_BA_near_0.5": abs(pl["placebo_0a_BA_mean"] - 0.5) < 0.1,
        "S0_S1_swap_OR_near_1": abs(math.log(pl["placebo_swap_OR_median"])) < 0.35 and pl["S0_vs_S1_OR_real"] > 3,
        "landing_shuffle_shrinks": abs(pl["placebo_shuffled_landing_diff_mean"]) < abs(pl["landing_diff_real"]),
        "E_permuted_rejection_near_0.05": all(v <= 0.1 for v in pl["placebo_E_permuted_rejection_rate"].values()),
    }
    (WS / "audit" / "rederive.json").write_text(json.dumps(out, indent=1, default=str))
    print(f"audit: {out['n_checks']} checks, {out['n_fail']} failed; placebos: {out['placebos_fail_as_required']}")
    for c in CHECKS:
        if not c["pass"]:
            print("FAIL", c)


if __name__ == "__main__":
    main()
