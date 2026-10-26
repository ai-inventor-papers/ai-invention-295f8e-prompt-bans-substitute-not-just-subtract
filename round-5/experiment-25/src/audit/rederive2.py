#!/usr/bin/env python3
"""Second independent re-derivation (standard library only, no project imports) of the headline numbers that
audit/rederive.py does not cover, each through its own code path, plus placebos that must fail.

  A2 log scores of the corrected association and of proximity (from the raw answers / committed distances)
  rival Spearman rhos (merit runtime, twin modal share) from the committed rival values and E re-derived from samples
  'half + screen' rho and permutation p from inputs/step1/commit1.json + E re-derived from samples; placebo: E shuffled
  engine-check per-slot label agreement (samples vs exp19's FP8 rows); gate kappas from the gate item lists
  novelty-audit counts and the 'outside the base repertoire' count from samples
  A2 placebo: random survivors as forecasts -> hit count at chance
Writes audit/rederive2_report.json; exit 1 on a mismatch.
"""

import json
import math
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCL = ("invalid", "disputed")
SEEDS = [95101 + i for i in range(8)]
MISM = []


def close(name, got, exp, tol=1e-6):
    ok = (got == exp) if (got is None or exp is None or isinstance(got, (str, bool))) else abs(got - exp) <= tol
    if not ok:
        MISM.append({"check": name, "rederived": got, "reported": exp})
    return ok


def rank(v):
    s = sorted(range(len(v)), key=lambda i: v[i])
    r = [0.0] * len(v)
    i = 0
    while i < len(s):
        j = i
        while j + 1 < len(s) and v[s[j + 1]] == v[s[i]]:
            j += 1
        for k in range(i, j + 1):
            r[s[k]] = (i + j) / 2.0 + 1.0
        i = j + 1
    return r


def rho(x, y):
    a, b = rank(x), rank(y)
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    c = sum((p - ma) * (q - mb) for p, q in zip(a, b))
    d = math.sqrt(sum((p - ma) ** 2 for p in a) * sum((q - mb) ** 2 for q in b))
    return c / d if d else float("nan")


def perm_p(x, y, n=20000, seed=7):
    obs = rho(x, y)
    rng = random.Random(seed)
    yy = list(y)
    ge = 0
    for _ in range(n):
        rng.shuffle(yy)
        ge += rho(x, yy) >= obs - 1e-12
    return obs, (ge + 1) / (n + 1)


def load_samples():
    by = defaultdict(list)
    for line in (ROOT / "data" / "samples.jsonl").read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            by[r["unit_kind"] == "engine_check" and "EC" or r["unit"]].append(r)
    return by


def esc_E(rows, cat, d):
    """Escape fraction: stage-1 screen, top-up and exact binomial confirmation, written independently."""
    def stats(rs):
        v = [r for r in rs if r["label"] not in EXCL]
        k = sum(1 for r in v if r["label"] in cat and r["label"] != d)
        return len(rs), len(v), k, (k / len(v) if v else None), (sum(r["passed"] for r in rs) / len(rs) if rs else None)
    n_t, nv_t, k_t, sh_t, ps_t = stats([r for r in rows if r["arm"] == "TWIN" and r["model"] == "instruct"])
    p0 = (k_t + 0.5) / (nv_t + 1)
    conf, land = 0, Counter()
    for s in SEEDS:
        for a in (1.0, 2.0):
            cell = [r for r in rows if r["arm"] == f"ESC_d{s}_a{a}"]
            n1, nv1, k1, sh1, ps1 = stats([r for r in cell if r["slot"] < 2])
            n3, nv3, k3, sh3, ps3 = stats([r for r in cell if r["slot"] < 6])
            if not (nv1 and sh1 - sh_t >= 0.2 - 1e-12 and ps1 >= 0.8 * ps_t - 1e-12 and n3 > n1 and nv3):
                continue
            pv = sum(math.comb(nv3, i) * p0 ** i * (1 - p0) ** (nv3 - i) for i in range(k3, nv3 + 1))
            if sh3 - sh_t >= 0.2 - 1e-12 and ps3 >= 0.8 * ps_t - 1e-12 and pv < 0.05:
                conf += 1
                land.update(r["label"] for r in cell if r["slot"] < 6 and r["passed"] and r["label"] in cat and
                            r["label"] != d)
    return conf / 16, land


def qmix(raw, surv):
    K = len(surv)
    t = sum(raw.get(s, 0.0) for s in surv) if raw else 0.0
    return {s: 0.98 * (0.95 * ((raw.get(s, 0.0) / t) if t > 0 else 1.0 / K) + 0.05 / K) for s in surv}


def main():
    by = load_samples()
    preds = {}
    for p in sorted((ROOT / "predictions").glob("unit_*.json")):
        j = json.loads(p.read_text())
        if j.get("status") == "OK":
            preds[j["unit"]] = j
    E, LAND = {}, {}
    for u, pr in preds.items():
        E[u], LAND[u] = esc_E(by[u], set(pr["catalogue"]), pr["default"])
    out = {}
    # ---- rivals (primary set)
    a1 = json.loads((ROOT / "results" / "a1.json").read_text())
    prim = [u for u in ("A1", "A2", "A3", "A4", "A5", "A7") if u in preds]
    for name, key in (("merit_runtime_min", "merit_runtime_min"), ("twin_modal_share", "twin_modal_share"),
                      ("opening_margin", "opening_margin"), ("novelty_share", "novelty_share")):
        r = rho([preds[u]["rivals"][key] for u in prim], [E[u] for u in prim])
        close(f"rival.{name}.rho", r, a1["rivals"][name]["rho_r_E"])
        out[f"rival_{name}_rho"] = r
    # ---- A2 with the corrected association (independent mapper: text after the echoed default name)
    a2c = json.loads((ROOT / "results" / "a2_assoc_corrected.json").read_text())
    for ev in a2c["events"]:
        u = ev["unit"]
        pr = preds[u]
        spec = json.loads(next((ROOT / "newbench").glob(f"{u}_*/spec.json")).read_text())
        d = pr["default"]
        surv = [m for m in pr["catalogue"] if m != d]
        names = {c["mode"]: [c["display_name"].lower()] + [a.lower() for a in spec["aliases"].get(c["mode"], [])]
                 for c in spec["catalogue"]}
        dname = names[d][0]
        counts = Counter()
        raw_rows = [r for r in (json.loads(l) for l in (ROOT / "data" / "raw" / f"{u}.jsonl").read_text().splitlines()
                                if l.strip()) if r["arm"] == "ASSOC"]
        for r in raw_rows:
            t = r["text"].lower()
            i = t.find(dname)
            rest = t[i + len(dname):] if i >= 0 else t
            hits = []
            for m in surv:
                for a in names[m]:
                    mm = re.search(r"(?<![a-z])" + re.escape(a) + r"(?![a-z])", rest)
                    if mm:
                        hits.append((mm.start(), pr["catalogue"].index(m), m))
            if hits:
                counts[min(hits)[2]] += 1
        realised = [r["label"] for r in by[u] if r["arm"].startswith("ESC_") and r["slot"] < 6
                    and r["passed"] and r["label"] in surv and _confirmed(by[u], r, pr)]
        qa = qmix({s: counts.get(s, 0) + 1 for s in surv}, surv)
        ls_a = sum(math.log(qa.get(l, 0.02)) for l in realised) / len(realised)
        pdist = {s: v for s, v in pr["rivals"]["prox_dist"].items() if v is not None}
        med = sorted(pdist.values())[len(pdist) // 2] if len(pdist) % 2 else \
            (sorted(pdist.values())[len(pdist) // 2 - 1] + sorted(pdist.values())[len(pdist) // 2]) / 2
        qp = qmix({s: math.exp(-pdist[s] / med) for s in pdist}, surv)
        ls_p = sum(math.log(qp.get(l, 0.02)) for l in realised) / len(realised)
        close(f"a2c.{u}.assoc_logscore", ls_a, ev["log_scores"]["assoc"])
        close(f"a2c.{u}.prox_logscore", ls_p, ev["log_scores"]["prox"])
        out[f"a2c_{u}"] = {"assoc_counts": dict(counts), "assoc_logscore": ls_a, "prox_logscore": ls_p,
                           "n_realised": len(realised)}
    # ---- A2 placebo: random survivors as forecasts -> hits at chance
    rng = random.Random(11)
    evs = [u for u in prim if preds[u]["beta"] >= 0.05 and E[u] > 0]
    obs_hits = sum(preds[u]["r"] == max(LAND[u], key=lambda m: (LAND[u][m], -preds[u]["catalogue"].index(m)))
                   for u in evs)
    sims = []
    for _ in range(5000):
        sims.append(sum(rng.choice([m for m in preds[u]["catalogue"] if m != preds[u]["default"]]) ==
                        max(LAND[u], key=lambda m: (LAND[u][m], -preds[u]["catalogue"].index(m))) for u in evs))
    out["a2_hits"] = obs_hits
    out["a2_placebo_mean_hits"] = sum(sims) / len(sims)
    out["a2_placebo_share_reaching_observed"] = sum(1 for s in sims if s >= obs_hits) / len(sims)
    # ---- half + screen
    s1 = json.loads((ROOT / "inputs" / "step1" / "commit1.json").read_text())["per_task"]
    hs = json.loads((ROOT / "results" / "half_screen.json").read_text())["primary"]
    cats = {}
    for d in (ROOT / "inputs" / "exp11" / "bench").iterdir():
        if d.is_dir() and (d / "spec.json").exists():
            cats[d.name.split("_")[0]] = [c["mode"] for c in json.loads((d / "spec.json").read_text())["catalogue"]]
    cats["T1"] = ["bfs", "dfs", "bibfs", "iddfs", "astar_gbfs", "dijkstra"]
    cats["T2"] = ["dijkstra", "bf_spfa", "bidijkstra", "floyd", "dial"]
    xa = json.loads((ROOT / "results" / "extra_arm_a.json").read_text())
    xs, ys, xe, ye = [], [], [], []
    for u in prim:
        xs.append(preds[u]["beta"])
        ys.append(E[u])
    for t in xa:
        if t in s1 and s1[t].get("beta") is not None:
            et, _ = esc_E(by[t], set(cats[t]), xa[t]["default"])
            xs.append(s1[t]["beta"])
            ys.append(et)
            xe.append(s1[t]["beta"])
            ye.append(et)
    r_all, p_all = perm_p(xs, ys)
    r_ex, p_ex = perm_p(xe, ye)
    close("half_screen.rho_all", r_all, hs["all"]["rho_beta_E"])
    close("half_screen.p_all", p_all, hs["all"]["perm_p_one_sided"], tol=0.004)
    close("half_screen.rho_existing", r_ex, hs["existing_only"]["rho_beta_E"])
    close("half_screen.p_existing", p_ex, hs["existing_only"]["perm_p_one_sided"], tol=0.004)
    pl = []
    rng2 = random.Random(3)
    for _ in range(200):
        yy = list(ys)
        rng2.shuffle(yy)
        pl.append(perm_p(xs, yy, n=1000, seed=rng2.randrange(10 ** 6))[1])
    out["half_screen"] = {"n": len(xs), "rho": r_all, "p": p_all, "rho_existing": r_ex, "p_existing": p_ex,
                          "placebo_share_p_below_0.05": sum(1 for p in pl if p < 0.05) / len(pl),
                          "placebo_share_p_below_0.0065": sum(1 for p in pl if p <= 0.0065) / len(pl)}
    # ---- engine check agreement
    ec = json.loads((ROOT / "results" / "engine_check.json").read_text())
    fp8 = {}
    for line in (ROOT / "inputs" / "exp19" / "data" / "engine_check_labels.jsonl").read_text().splitlines():
        r = json.loads(line)
        fp8[(r["task"], r["arm"], r["template"], int(r["slot"]))] = r["label"]
    amap = {"ECTWIN": "NEUTRAL", "ECBAN_d9002_a1.0": "RAND9002_a1.0", "ECBAN_d9004_a1.0": "RAND9004_a1.0"}
    for key, v in ec["cells"].items():
        t, arm = key.split("|")
        mine = [r for r in by["EC"] if r["unit"] == t and r["arm"] == arm]
        ag = [r["label"] == fp8.get((t, amap[arm], r["template"], r["slot"])) for r in mine]
        close(f"engine.{key}.agreement", sum(ag) / len(ag), v["per_slot_label_agreement"])
    # ---- gate kappas (own Cohen kappa on the stored item lists)
    for g in sorted((ROOT / "newbench").glob("A*/gate_round0.json")) + sorted((ROOT / "newbench").glob("A*/gate_holdout.json")):
        j = json.loads(g.read_text())
        it = [i for i in j["items"] if i.get("valid")]
        a, b = [i["runtime_label"] for i in it], [i["ast_label"] for i in it]
        po = sum(x == y for x, y in zip(a, b)) / len(a)
        ca, cb = Counter(a), Counter(b)
        pe = sum(ca[k] * cb[k] for k in ca) / len(a) ** 2
        kap = (1.0 if po == 1 else 0.0) if pe >= 1 - 1e-12 else (po - pe) / (1 - pe)
        close(f"gate.{g.parent.name}.{g.stem}.kappa", kap, j["kappa_runtime_ast"])
    # ---- novelty + repertoire counts
    allrows = [r for k, v in by.items() if k != "EC" for r in v]
    n_corr = sum(1 for r in allrows if r["passed"])
    n_other = sum(1 for r in allrows if r["passed"] and r["label"] == "other")
    nov = json.loads((ROOT / "results" / "novelty_audit.json").read_text())
    close("novelty.n_correct", n_corr, nov["n_correct_programs_total"])
    close("novelty.n_correct_other", n_other, nov["n_correct_other"])
    outside = 0
    for u, pr in preds.items():
        base = [r for r in by[u] if r["arm"] == "BASE"]
        okc = {r["label"] for r in base if r["passed"] and r["label"] not in EXCL}
        okv = {r["label"] for r in base if r["label"] not in EXCL}
        outside += sum(1 for r in by[u] if (r["arm"].startswith("PN_") or r["arm"].startswith("ESC_")) and r["passed"]
                       and r["label"] in pr["catalogue"] and r["label"] != pr["default"] and r["label"] not in okc
                       and r["label"] not in okv)
    close("repertoire.outside", outside, len(json.loads((ROOT / "results" / "outside_base_repertoire.json").read_text())))
    out["n_mismatches"] = len(MISM)
    out["mismatches"] = MISM
    (ROOT / "audit" / "rederive2_report.json").write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps(out, indent=1, default=str)[:4000])
    sys.exit(1 if MISM else 0)


def _confirmed(rows, r, pr):
    """True when row r belongs to a confirmed escape cell (recomputed per cell, cached)."""
    key = (pr["unit"], r["arm"])
    if key not in _CC:
        cell = [x for x in rows if x["arm"] == r["arm"]]
        tw = [x for x in rows if x["arm"] == "TWIN" and x["model"] == "instruct"]
        e, _ = esc_E(tw + cell, set(pr["catalogue"]), pr["default"])
        _CC[key] = e > 0
    return _CC[key]


_CC = {}

if __name__ == "__main__":
    main()
