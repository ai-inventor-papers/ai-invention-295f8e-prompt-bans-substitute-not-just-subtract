#!/usr/bin/env python3
"""Independent re-derivation of every headline (Python standard library only; shares no code with src/).

Reads data/samples_raw.jsonl + data/labels.jsonl (+ data/l_events.json, data/tf_scores.jsonl) and recomputes:
Stage A Y shares, transfers and exact McNemar counts/p (X vs TWIN, X_0-35 vs MR_0-35); ST correct off-default counts per
(task, site, alpha); S3-vs-DMD discordant flips; top-five landing compositions; L top-1 hits and the sign test.
Each number is compared with results/*.json (tolerance 1e-9) and mismatches are counted. Placebos (must FAIL to show
an effect): shuffled slot pairing for the X_0-35 vs TWIN McNemar, shuffled site labels for the ST site contrast.
Writes results/rederive.json."""

import json
import math
import os
import random
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT = {"T03": "full_sort", "T10": "union_find", "T2": "dijkstra", "T05": "hash_map", "T06": "hash_set", "T1": "bfs"}
LAB = {}
Y = {"T2": "bf_spfa", "T03": "quickselect", "T10": "bfs", "T1": "dfs", "T05": "brute_force", "T06": "index_marking"}


def jl(p):
    out = []
    if not os.path.exists(p):
        return out
    with open(p) as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def binom_two_sided(k, n):
    if n == 0:
        return 1.0
    k = min(k, n - k)
    tail = sum(math.comb(n, i) for i in range(0, k + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def main():
    labs = {r["sample_id"]: r for r in jl(os.path.join(ROOT, "data", "labels.jsonl"))}
    LAB.update({k: v["label"] for k, v in labs.items()})
    raw_rows = jl(os.path.join(ROOT, "data", "samples_raw.jsonl"))
    rows = []
    for r in raw_rows:
        l = labs.get(r["sample_id"])
        if l:
            rows.append({"task": r["task"], "arm": r["arm"], "cell": r["cell"], "site": r.get("site"),
                         "alpha": r.get("alpha"), "s": r["slot_index"], "label": l["label"], "sid": r["sample_id"],
                         "passed": bool(l.get("passed"))})
    by = defaultdict(dict)
    for r in rows:
        by[(r["task"], r["arm"])][r["s"]] = r
    res = {"n_rows": len(rows), "checks": [], "mismatches": 0}

    def check(name, mine, theirs):
        ok = (mine is None and theirs is None) or (mine is not None and theirs is not None and
                                                   abs(float(mine) - float(theirs)) < 1e-9)
        res["checks"].append({"name": name, "rederived": mine, "analysis": theirs, "match": ok})
        if not ok:
            res["mismatches"] += 1
    sa_p = os.path.join(ROOT, "results", "stage_a.json")
    sa = json.load(open(sa_p))["tasks"] if os.path.exists(sa_p) else {}
    for t in DEFAULT:
        tw = {s: r for s, r in by.get((t, "TWIN"), {}).items() if s < 30}
        if not tw:
            continue
        ytw = sum(r["label"] == Y[t] for r in tw.values()) / len(tw)
        for arm in ("BAN", "X_0-11", "X_12-23", "X_24-35", "X_0-35", "COND", "RPOS", "MR_0-35", "MR_12-23", "PLACEBO"):
            c = by.get((t, arm))
            if not c:
                continue
            share = sum(r["label"] == Y[t] for r in c.values()) / len(c)
            b = sum(c[s]["label"] == Y[t] and tw[s]["label"] != Y[t] for s in c if s in tw)
            cc = sum(c[s]["label"] != Y[t] and tw[s]["label"] == Y[t] for s in c if s in tw)
            a = (sa.get(t, {}).get("cells", {}).get(arm) or {})
            check(f"{t}|{arm}|transfer", share - ytw, a.get("transfer"))
            check(f"{t}|{arm}|mcnemar_b", b, (a.get("mcnemar_vs_twin") or {}).get("b_Y_only_cell"))
            check(f"{t}|{arm}|mcnemar_c", cc, (a.get("mcnemar_vs_twin") or {}).get("c_Y_only_twin"))
            check(f"{t}|{arm}|mcnemar_p", binom_two_sided(b, b + cc) if b + cc else 1.0,
                  (a.get("mcnemar_vs_twin") or {}).get("p"))
        x, m = by.get((t, "X_0-35"), {}), by.get((t, "MR_0-35"), {})
        if x and m:
            b = sum(x[s]["label"] == Y[t] and m[s]["label"] != Y[t] for s in x if s in m)
            cc = sum(x[s]["label"] != Y[t] and m[s]["label"] == Y[t] for s in x if s in m)
            a = ((sa.get(t, {}).get("cells", {}).get("X_0-35") or {}).get("mcnemar_vs_MR_0-35") or {})
            check(f"{t}|X_0-35_vs_MR|b", b, a.get("b_X_only"))
            check(f"{t}|X_0-35_vs_MR|c", cc, a.get("c_MR_only"))
        # placebo 1: shuffled slot pairing must destroy the paired structure (report the counts)
        x = by.get((t, "X_0-35"), {})
        if x and tw:
            rnd = random.Random(3)
            ks = sorted(set(x) & set(tw))
            perm = ks[:]
            rnd.shuffle(perm)
            b = sum(x[s]["label"] == Y[t] and tw[p]["label"] != Y[t] for s, p in zip(ks, perm))
            cc = sum(x[s]["label"] != Y[t] and tw[p]["label"] == Y[t] for s, p in zip(ks, perm))
            res.setdefault("placebo_shuffled_slots", {})[t] = {"b": b, "c": cc,
                                                               "note": "twin has no Y rows, so pairing cannot matter "
                                                                       "when Y_twin = 0" if ytw == 0 else ""}
    # ST cells
    sg_p = os.path.join(ROOT, "results", "site_grid.json")
    sg = json.load(open(sg_p))["tasks"] if os.path.exists(sg_p) else {}
    for t in ("T03", "T10"):
        cnt = defaultdict(lambda: [0, 0])
        for r in rows:
            if r["task"] == t and r["cell"] == "ST":
                k = f"{r['site']}|a{float(r['alpha']):g}"
                cnt[k][0] += 1
                cnt[k][1] += int(r["passed"] and r["label"] not in (DEFAULT[t], "other", "invalid"))
        for k, (n, kk) in cnt.items():
            a = sg.get(t, {}).get("cells", {}).get(k) or {}
            check(f"ST|{t}|{k}|k_correct_off_default", kk, a.get("k_correct_off_default"))
        # placebo 2: shuffled site labels -> S0-vs-others contrast should vanish
        st = [r for r in rows if r["task"] == t and r["cell"] == "ST" and r["site"] in ("S0", "S1", "S2")]
        if st:
            rnd = random.Random(5)
            sites = [r["site"] for r in st]
            rnd.shuffle(sites)
            sh = defaultdict(lambda: [0, 0])
            for r, s in zip(st, sites):
                sh[s][0] += 1
                sh[s][1] += int(r["passed"] and r["label"] not in (DEFAULT[t], "other", "invalid"))
            res.setdefault("placebo_shuffled_sites", {})[t] = {s: v[1] / v[0] for s, v in sh.items()}
    # S3 vs DMD
    sv_p = os.path.join(ROOT, "results", "state_vs_token.json")
    sv = json.load(open(sv_p)) if os.path.exists(sv_p) else {}
    for t in ("T03", "T10"):
        tw = by.get((t, "TWIN"), {})
        for a in (2.0, 4.0):
            s3 = {r["s"]: r for r in rows if r["task"] == t and r["cell"] == "ST" and r["site"] == "S3"
                  and float(r["alpha"]) == a}
            dm = by.get((t, f"DMD_a{a:g}"), {})
            sl = sorted(set(s3) & set(dm) & set(tw))
            if not sl:
                continue
            f = lambda r, s: r["passed"] and r["label"] not in (DEFAULT[t], "other", "invalid") and tw[s]["label"] == DEFAULT[t]  # noqa: E731
            b = sum(f(s3[s], s) and not f(dm[s], s) for s in sl)
            c = sum(f(dm[s], s) and not f(s3[s], s) for s in sl)
            k = f"{t}|a{a:g}"
            check(f"SVT|{k}|S3_only", b, (sv.get(k) or {}).get("S3_only_flips"))
            check(f"SVT|{k}|DMD_only", c, (sv.get(k) or {}).get("DMD_only_flips"))
    # top-five landing compositions
    t5_p = os.path.join(ROOT, "results", "top5_push.json")
    t5 = json.load(open(t5_p)) if os.path.exists(t5_p) else {}
    for arm in ("TOP5_a1", "TOP5_a2", "TOP5_a4", "TOP5_a8", "TOP5BAN"):
        c = by.get(("T1", arm))
        if not c:
            continue
        n = sum(r["passed"] and r["label"] not in ("bfs", "other", "invalid") for r in c.values())
        check(f"TOP5|{arm}|correct_non_bfs", n, ((t5.get("cells") or {}).get(arm) or {}).get("correct_non_bfs"))
    # L: base top-1 hits from the frozen event table
    ev_p = os.path.join(ROOT, "data", "l_events.json")
    lf_p = os.path.join(ROOT, "results", "landing_forecast.json")
    if os.path.exists(ev_p):
        ev = json.load(open(ev_p))["events"]
        check("L|base_runner_up_hits_recorded", sum(e["r_u"] == e["landing_top1"] for e in ev),
              json.load(open(ev_p))["hits_base_top1"])
        if os.path.exists(lf_p):
            lf = json.load(open(lf_p))
            check("L|BASE_top1_hits", sum(1 for e in lf["events"] if e.get("BASE_hit")), lf["BASE_hits"]["hits"])
            st = lf["primary_sign_test"]
            n, k = st["n_discordant"], st["base_wins"]
            p = sum(math.comb(n, i) for i in range(k, n + 1)) / 2 ** n if n else float("nan")
            if n:
                check("L|sign_test_p", p, st["p_one_sided_base_gt_open"])
    headline_tests(rows, by, raw_rows, check, res)
    res["n_checks"] = len(res["checks"])
    with open(os.path.join(ROOT, "results", "rederive.json"), "w") as fh:
        json.dump(res, fh, indent=1)
    print(json.dumps({"n_checks": res["n_checks"], "mismatches": res["mismatches"]}))
    return 0 if res["mismatches"] == 0 else 1


# ------------------------------------------------------------------------------------------------ headline tests + placebos
def swap_placebo(pairs, seed, n_perm=2000):
    """pairs: [(event_a, event_b)] booleans per paired slot. Observed exact McNemar (b, c, p); one placebo with the two
    labels of every pair swapped at random (the null), and the permutation p of the observed discordance."""
    b = sum(1 for a, c in pairs if a and not c)
    c = sum(1 for a, cc in pairs if cc and not a)
    rnd = random.Random(seed)
    sw = [(cc, a) if rnd.random() < 0.5 else (a, cc) for a, cc in pairs]
    pb = sum(1 for a, cc in sw if a and not cc)
    pc = sum(1 for a, cc in sw if cc and not a)
    obs = abs(b - c)
    hits = 0
    for _ in range(n_perm):
        d = 0
        for a, cc in pairs:
            if a != cc:
                d += (1 if a else -1) * (1 if rnd.random() < 0.5 else -1)
        hits += abs(d) >= obs
    return {"b": b, "c": c, "p": binom_two_sided(b, b + c) if b + c else 1.0, "placebo_b": pb, "placebo_c": pc,
            "placebo_p": binom_two_sided(pb, pb + pc) if pb + pc else 1.0, "permutation_p": (hits + 1) / (n_perm + 1)}


def headline_tests(rows, by, raw_rows, check, res):
    out = {}
    D = DEFAULT
    # Stage A: X_0-35 vs TWIN and X_0-35 vs MR_0-35 on Y (paired CRN slots)
    for t in ("T2", "T03", "T10"):
        x, tw, mr = by.get((t, "X_0-35"), {}), {s: r for s, r in by.get((t, "TWIN"), {}).items() if s < 30}, \
            by.get((t, "MR_0-35"), {})
        out[f"stageA|{t}|X_vs_TWIN"] = swap_placebo([(x[s]["label"] == Y[t], tw[s]["label"] == Y[t])
                                                     for s in sorted(x) if s in tw], 11)
        out[f"stageA|{t}|X_vs_MR"] = swap_placebo([(x[s]["label"] == Y[t], mr[s]["label"] == Y[t])
                                                  for s in sorted(x) if s in mr], 12)
    # ST: paired S0 vs S1 flips (all alphas) and the Mantel-Haenszel OR in log D_R quintiles, from raw rows
    disp = {}
    for r in raw_rows:
        rec = r.get("realised") or {}
        dr = (rec.get("dR") or {}).get("35")
        if r.get("cell") == "ST" and dr is not None:
            disp[r["sample_id"]] = dr
    for t in ("T03", "T10"):
        ok = lambda r: r["passed"] and r["label"] not in (D[t], "other", "invalid")  # noqa: E731
        st = [r for r in rows if r["task"] == t and r["cell"] == "ST"]
        pairs = []
        for a in (1.0, 2.0, 4.0, 8.0):
            s0 = {r["s"]: r for r in st if r["site"] == "S0" and float(r["alpha"]) == a}
            s1 = {r["s"]: r for r in st if r["site"] == "S1" and float(r["alpha"]) == a}
            pairs += [(ok(s0[s]), ok(s1[s])) for s in sorted(set(s0) & set(s1))]
        out[f"ST|{t}|S0_vs_S1_flips"] = swap_placebo(pairs, 13)
        sub = [r for r in st if r["site"] in ("S0", "S1") and r["sid"] in disp]
        lx = sorted(math.log(disp[r["sid"]] + 1e-3) for r in sub)
        def q(p_):
            k = (len(lx) - 1) * p_
            f, c = math.floor(k), math.ceil(k)
            return lx[f] + (lx[c] - lx[f]) * (k - f)
        edges = [q(i / 5) for i in range(6)]
        def mh(site_of):
            num = den = 0.0
            for i in range(5):
                g = [r for r in sub if edges[i] <= math.log(disp[r["sid"]] + 1e-3) <= edges[i + 1]]
                n = len(g)
                if not n:
                    continue
                a_ = sum(1 for r in g if site_of(r) == "S0" and ok(r))
                b_ = sum(1 for r in g if site_of(r) == "S0" and not ok(r))
                c_ = sum(1 for r in g if site_of(r) == "S1" and ok(r))
                d_ = sum(1 for r in g if site_of(r) == "S1" and not ok(r))
                if (a_ + b_) and (c_ + d_):
                    num += a_ * d_ / n
                    den += b_ * c_ / n
            return num / den if den else float("inf")
        obs = mh(lambda r: r["site"])
        rnd = random.Random(17)
        labs = [r["site"] for r in sub]
        perm_or = []
        for _ in range(500):
            sh = labs[:]
            rnd.shuffle(sh)
            m = dict(zip([r["sid"] for r in sub], sh))
            perm_or.append(mh(lambda r: m[r["sid"]]))
        out[f"ST|{t}|MH_OR_S0_vs_S1"] = {"or": obs, "placebo_or_first_shuffle": perm_or[0],
                                         "permutation_p_or_ge_obs": (sum(v >= obs for v in perm_or) + 1) / 501}
        sg_p = os.path.join(ROOT, "results", "site_grid.json")
        if os.path.exists(sg_p):
            a_or = json.load(open(sg_p))["tasks"][t]["mh"].get("S0_vs_S1", {}).get("or")
            check(f"ST|{t}|MH_OR_S0_vs_S1", obs if math.isfinite(obs) else None, a_or)
            pf = json.load(open(sg_p))["tasks"][t]["paired_flips"]["S0_vs_S1"]
            check(f"ST|{t}|paired_flips_S0_only", out[f"ST|{t}|S0_vs_S1_flips"]["b"], pf["S0_only"])
            check(f"ST|{t}|paired_flips_S1_only", out[f"ST|{t}|S0_vs_S1_flips"]["c"], pf["other_only"])
    # engine check: this engine's twin vs exp27's twin labels at the same (task, template, stream index)
    e27 = {}
    for r in jl(os.path.join(ROOT, "inputs_extra", "exp27", "data", "labels.jsonl")):
        if r.get("arm") == "TWIN":
            e27[(r["task"], r["template"], int(r["slot"]))] = r["label"]
    ec_p = os.path.join(ROOT, "results", "engine_check.json")
    ec = json.load(open(ec_p)) if os.path.exists(ec_p) else {}
    for t in ("T03", "T2"):
        tw = [r for r in raw_rows if r["task"] == t and r["arm"] == "TWIN"]
        pairs = [(LAB.get(r["sample_id"]), e27.get((t, r["template"], int(r["slot"])))) for r in tw]
        pairs = [(a, b) for a, b in pairs if b is not None and a is not None]
        agree = sum(a == b for a, b in pairs) / len(pairs)
        out[f"engine|{t}"] = {"n_pairs": len(pairs), "agreement": agree}
        check(f"engine|{t}|agreement", agree, (ec.get(t) or {}).get("label_agreement"))
    # L: OPEN top-1 recomputed from the raw teacher-forced rows; BASE top-1 from the frozen event table; sign test
    ev = json.load(open(os.path.join(ROOT, "data", "l_events.json")))["events"]
    fc = json.load(open(os.path.join(ROOT, "predictions", "commit1b_L_forecasts.json")))["forecasts"]
    tf = defaultdict(list)
    for r in jl(os.path.join(ROOT, "data", "tf_scores.jsonl")):
        tf[(r["model"], r["task"], r["alg"], r["tmpl_idx"])].append(r["ll48"])
    per = defaultdict(lambda: defaultdict(list))
    for (m, t, a, ti), v in tf.items():
        mx = max(v)
        per[(m, t)][a].append(mx + math.log(sum(math.exp(x - mx) for x in v) / len(v)))
    openv = {k: {a: sum(v) / len(v) for a, v in d.items()} for k, d in per.items()}
    rowsL = []
    for e in ev:
        sup = fc[e["event"]]["support"]
        if e.get("q_base_counts"):
            sc = {a: e["q_base_counts"].get(a, 0) + 1 for a in sup}
        elif e.get("q_base_probs"):
            sc = {a: e["q_base_probs"].get(a, 0.0) for a in sup}
        else:
            sc = {a: (2.0 if a == e["r_u"] else 1.0) for a in sup}
        base = max(sup, key=lambda a: sc[a])
        ov = openv.get((e["model"], e["task"]), {})
        cand = [a for a in sup if a in ov]
        op = max(cand, key=lambda a: ov[a]) if cand else None
        rowsL.append((e["event"], base, op, e["landing_top1"]))
    disc = [(b == l, o == l) for _, b, o, l in rowsL if o and b != o and ((b == l) != (o == l))]
    kb, n = sum(1 for a, _ in disc if a), len(disc)
    pL = sum(math.comb(n, i) for i in range(kb, n + 1)) / 2 ** n if n else float("nan")
    rnd = random.Random(19)
    sw = [((o == l), (b == l)) if rnd.random() < 0.5 else ((b == l), (o == l)) for _, b, o, l in rowsL
          if o and b != o and ((b == l) != (o == l))]
    kp = sum(1 for a, _ in sw if a)
    out["L|sign_test_from_raw"] = {"base_hits": sum(b == l for _, b, _, l in rowsL),
                                   "open_hits": sum(o == l for _, _, o, l in rowsL), "n_discordant": n,
                                   "base_wins": kb, "p_one_sided": pL, "placebo_base_wins": kp,
                                   "placebo_p_one_sided": sum(math.comb(n, i) for i in range(kp, n + 1)) / 2 ** n}
    lf_p = os.path.join(ROOT, "results", "landing_forecast.json")
    if os.path.exists(lf_p):
        lf = json.load(open(lf_p))
        check("L|OPEN_hits_from_raw_tf", out["L|sign_test_from_raw"]["open_hits"], lf["OPEN_hits"]["hits"])
        check("L|BASE_hits_from_events", out["L|sign_test_from_raw"]["base_hits"], lf["BASE_hits"]["hits"])
        check("L|discordant_from_raw", n, lf["primary_sign_test"]["n_discordant"])
        check("L|base_wins_from_raw", kb, lf["primary_sign_test"]["base_wins"])
        check("L|sign_test_p_from_raw", pL, lf["primary_sign_test"]["p_one_sided_base_gt_open"])
    res["headline_tests_with_placebos"] = out
    res["placebo_failures_expected"] = {k: v.get("placebo_p", v.get("placebo_p_one_sided")) for k, v in out.items()
                                        if isinstance(v, dict) and ("placebo_p" in v or "placebo_p_one_sided" in v)}


if __name__ == "__main__":
    sys.exit(main())
