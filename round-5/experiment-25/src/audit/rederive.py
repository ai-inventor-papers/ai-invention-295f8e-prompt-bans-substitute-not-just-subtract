#!/usr/bin/env python3
"""Independent re-derivation (Python standard library only): recomputes every headline number of panel A from
data/samples.jsonl and predictions/unit_*.json, without importing any project module, and compares it with the
result files. Also runs the two placebos that must fail. Writes audit/rederive_report.json; exit 1 on a mismatch.

Recomputed: default (twin modal correct label, share >= 0.6), beta_u, r_u, the escape table (stage-1 screen,
top-up, exact one-sided binomial confirmation), E_u, landing L_u, Spearman rho(beta, E) with the exact permutation
p, collapsed/diverse immovable shares, the A2 hits + Poisson-binomial p + log scores, and Extra-arm-A E_t.
Placebos: (1) beta shuffled across units -> the mean rho over all permutations is ~0; (2) labels shuffled between
the twin and the escape rows of each unit (pushes made uninformative) -> confirmed escapes collapse to the rule's
false-positive level.
"""

import itertools
import json
import math
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCL = ("invalid", "disputed")
SEEDS = [95101 + i for i in range(8)]
ALPHAS = (1.0, 2.0)
TOL = 1e-9


def load():
    rows = [json.loads(l) for l in (ROOT / "data" / "samples.jsonl").read_text().splitlines() if l.strip()]
    by = defaultdict(list)
    for r in rows:
        if r["unit_kind"] != "engine_check":
            by[r["unit"]].append(r)
    return by


def share(rows, cat, d):
    valid = [r for r in rows if r["label"] not in EXCL]
    off = [r for r in valid if r["label"] in cat and r["label"] != d]
    return {"n": len(rows), "nv": len(valid), "k": len(off), "share": len(off) / len(valid) if valid else None,
            "pass": sum(1 for r in rows if r["passed"]) / len(rows) if rows else None,
            "land": Counter(r["label"] for r in off if r["passed"])}


def binom_greater(k, n, p):
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k, n + 1))


def escape(rows, cat, d):
    tw = share([r for r in rows if r["arm"] == "TWIN" and r["model"] == "instruct"], cat, d)
    p0 = (tw["k"] + 0.5) / (tw["nv"] + 1)
    cells = []
    for s in SEEDS:
        for a in ALPHAS:
            c = [r for r in rows if r["arm"].startswith("ESC_") and r["direction_seed"] == s and abs(r["alpha"] - a) < 1e-9]
            f = share([r for r in c if r["slot"] in (0, 1)], cat, d)
            pl = share([r for r in c if r["slot"] in range(6)], cat, d)
            sp = (f["nv"] > 0 and f["share"] - tw["share"] >= 0.2 - 1e-12 and f["pass"] >= 0.8 * tw["pass"] - 1e-12)
            conf = False
            if sp and pl["n"] > f["n"] and pl["nv"] > 0:
                conf = (pl["share"] - tw["share"] >= 0.2 - 1e-12 and binom_greater(pl["k"], pl["nv"], p0) < 0.05 and
                        pl["pass"] >= 0.8 * tw["pass"] - 1e-12)
            cells.append({"seed": s, "alpha": a, "confirmed": conf, "land": pl["land"] if conf else Counter()})
    E = sum(c["confirmed"] for c in cells) / len(cells)
    land = Counter()
    for c in cells:
        land.update(c["land"])
    return E, land, cells


def ranks(x):
    o = sorted(range(len(x)), key=lambda i: x[i])
    r = [0.0] * len(x)
    i = 0
    while i < len(o):
        j = i
        while j + 1 < len(o) and x[o[j + 1]] == x[o[i]]:
            j += 1
        for k in range(i, j + 1):
            r[o[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def spearman(x, y):
    rx, ry = ranks(x), ranks(y)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return num / den if den else float("nan")


def perm_p(x, y):
    obs = spearman(x, y)
    ge = tot = 0
    rs = []
    for p in itertools.permutations(range(len(x))):
        r = spearman(x, [y[i] for i in p])
        rs.append(r)
        tot += 1
        ge += r >= obs - 1e-12
    return obs, ge / tot, sum(rs) / len(rs)


def pois_binom_sf(h, ps):
    dist = [1.0] + [0.0] * len(ps)
    for p in ps:
        new = [0.0] * len(dist)
        for i, v in enumerate(dist):
            new[i] += v * (1 - p)
            if i + 1 < len(dist):
                new[i + 1] += v * p
        dist = new
    return sum(dist[h:])


def mixture_logscore(raw, surv, labels):
    K = len(surv)
    tot = sum(max(0.0, (raw or {}).get(s, 0.0)) for s in surv)
    base = {s: (max(0.0, raw.get(s, 0.0)) / tot if raw and tot > 0 else 1.0 / K) for s in surv}
    q = {s: 0.98 * (0.95 * base[s] + 0.05 / K) for s in surv}
    return sum(math.log(q.get(l, 0.02)) for l in labels) / len(labels) if labels else None


def main():
    by = load()
    mism = []

    def check(name, got, exp, tol=1e-6):
        ok = (got == exp) if not isinstance(got, float) or not isinstance(exp, (float, int)) else \
            (exp is not None and abs(got - exp) <= tol)
        if not ok:
            mism.append({"check": name, "rederived": got, "reported": exp})
        return ok
    preds = {json.loads(p.read_text())["unit"]: json.loads(p.read_text()) for p in sorted((ROOT / "predictions").glob("unit_*.json"))}
    summ_ext = json.loads((ROOT / "results" / "unit_summaries_with_extension.json").read_text())
    out_units = {}
    for u, pr in preds.items():
        if pr.get("status") != "OK":
            continue
        rows = by[u]
        cat = pr["catalogue"]
        tw = [r for r in rows if r["arm"] == "TWIN" and r["model"] == "instruct"]
        corr = Counter(r["label"] for r in tw if r["passed"] and r["label"] not in EXCL)
        lab, k = sorted(corr.items(), key=lambda kv: (-kv[1], kv[0]))[0]
        d = lab if (len(tw) >= 50 and k / sum(corr.values()) >= 0.6 and lab != "other") else None
        check(f"{u}.default", d, pr["default"])
        base = [r for r in rows if r["arm"] == "BASE" and r["model"] == "base"]
        valid = [r for r in base if r["label"] not in EXCL]
        cor = [r for r in valid if r["passed"]]
        use = cor if len(cor) >= 20 else valid
        beta = sum(1 for r in use if r["label"] in cat and r["label"] != d) / len(use)
        check(f"{u}.beta", beta, pr["beta"])
        cnt = Counter(r["label"] for r in cor if r["label"] in cat and r["label"] != d)
        vcnt = Counter(r["label"] for r in valid if r["label"] in cat and r["label"] != d)
        if not cnt and len(cor) < 20:
            cnt = vcnt
        r_u = sorted(cnt, key=lambda m: (-cnt[m], -vcnt.get(m, 0), cat.index(m)))[0] if cnt else None
        check(f"{u}.r", r_u, pr["r"])
        E, land, cells = escape(rows, set(cat), d)
        L = sorted(land, key=lambda m: (-land[m], cat.index(m) if m in cat else 99))[0] if land else None
        oc = summ_ext[u]["outcome"]
        check(f"{u}.E", E, oc["E"])
        check(f"{u}.landing", L, oc["landing"])
        out_units[u] = {"default": d, "beta": beta, "r": r_u, "E": E, "landing": L, "rows": rows, "cat": cat,
                        "land": land}
    report = {}
    for setname, units, a1f, a2f in (("primary", [u for u in out_units if u not in ("A8", "A9")], "a1.json", "a2.json"),
                                     ("with_extension", list(out_units), "a1_with_extension.json",
                                      "a2_with_extension.json")):
        xs = [out_units[u]["beta"] for u in units]
        ys = [out_units[u]["E"] for u in units]
        rho, p, mean_perm = perm_p(xs, ys)
        a1 = json.loads((ROOT / "results" / a1f).read_text())
        check(f"{setname}.rho", rho, a1["rho_beta_E"])
        check(f"{setname}.perm_p", p, a1["perm_p_one_sided"])
        low = [u for u in units if out_units[u]["beta"] < 0.05]
        hi = [u for u in units if out_units[u]["beta"] >= 0.2]
        ci = sum(out_units[u]["E"] == 0 for u in low) / len(low) if low else None
        di = sum(out_units[u]["E"] == 0 for u in hi) / len(hi) if hi else None
        check(f"{setname}.collapsed_immovable", ci, a1["collapsed_immovable"])
        check(f"{setname}.diverse_immovable", di, a1["diverse_immovable"])
        # A2
        a2 = json.loads((ROOT / "results" / a2f).read_text())
        evs = [u for u in units if out_units[u]["beta"] >= 0.05 and out_units[u]["E"] > 0]
        hits = sum(out_units[u]["r"] == out_units[u]["landing"] for u in evs)
        ps = [1.0 / (len(out_units[u]["cat"]) - 1) for u in evs]
        check(f"{setname}.a2_hits", hits, a2["hits"])
        if evs:
            check(f"{setname}.a2_p", pois_binom_sf(hits, ps), a2["p_poisson_binomial"])
        for ev in a2["events"]:
            u = ev["unit"]
            o = out_units[u]
            surv = [m for m in o["cat"] if m != o["default"]]
            realised = []
            for c in escape(o["rows"], set(o["cat"]), o["default"])[2]:
                if c["confirmed"]:
                    realised += [r["label"] for r in o["rows"] if r["arm"].startswith("ESC_") and
                                 r["direction_seed"] == c["seed"] and abs(r["alpha"] - c["alpha"]) < 1e-9 and
                                 r["slot"] in range(6) and r["passed"] and r["label"] in surv]
            bcc = Counter(r["label"] for r in o["rows"] if r["arm"] == "BASE" and r["passed"] and r["label"] not in EXCL)
            ls = mixture_logscore({s: float(bcc.get(s, 0)) for s in surv}, surv, realised)
            check(f"{setname}.{u}.logscore_base", ls, ev["log_scores"]["base"])
        report[setname] = {"rho": rho, "perm_p": p, "mean_rho_over_all_permutations": mean_perm, "n": len(units)}
        # placebo 1: beta shuffled across units -> mean rho over permutations ~ 0
        report[setname]["placebo_beta_shuffle_mean_rho"] = mean_perm
    # Extra arm A
    xa = json.loads((ROOT / "results" / "extra_arm_a.json").read_text())
    for t, v in xa.items():
        rows = by[t]
        catf = None
        for d in (ROOT / "inputs" / "exp11" / "bench").iterdir():
            if d.is_dir() and d.name.startswith(t + "_"):
                catf = [c["mode"] for c in json.loads((d / "spec.json").read_text())["catalogue"]]
        if catf is None:
            catf = {"T1": ["bfs", "dfs", "bibfs", "iddfs", "astar_gbfs", "dijkstra"],
                    "T2": ["dijkstra", "bf_spfa", "bidijkstra", "floyd", "dial"]}[t]
        E, _, _ = escape(rows, set(catf), v["default"])
        check(f"extra_arm_a.{t}.E", E, v["E"])
    # placebo 2: labels shuffled between twin and escape rows (pushes uninformative)
    rng = random.Random(20261021)
    pl = {}
    for u, o in out_units.items():
        es = []
        for _ in range(20):
            rows = [dict(r) for r in o["rows"]]
            pool = [i for i, r in enumerate(rows) if (r["arm"] == "TWIN" and r["model"] == "instruct") or r["arm"].startswith("ESC_")]
            vals = [(rows[i]["label"], rows[i]["passed"]) for i in pool]
            rng.shuffle(vals)
            for i, (lb, ps_) in zip(pool, vals):
                rows[i]["label"], rows[i]["passed"] = lb, ps_
            es.append(escape(rows, set(o["cat"]), o["default"])[0])
        pl[u] = {"observed_E": o["E"], "placebo_mean_E": sum(es) / len(es), "placebo_max_E": max(es)}
    report["placebo_label_shuffle"] = pl
    report["n_mismatches"] = len(mism)
    report["mismatches"] = mism
    (ROOT / "audit" / "rederive_report.json").write_text(json.dumps(report, indent=1, default=str))
    print(json.dumps({k: v for k, v in report.items() if k != "placebo_label_shuffle"}, indent=1, default=str))
    print(json.dumps(pl, indent=0))
    sys.exit(1 if mism else 0)


if __name__ == "__main__":
    main()
