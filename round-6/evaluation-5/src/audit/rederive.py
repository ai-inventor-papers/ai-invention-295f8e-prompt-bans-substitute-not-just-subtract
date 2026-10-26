#!/usr/bin/env python3
"""Independent re-derivation of the iteration-6 record repair, standard library only, no code shared with src/.

Every family re-reads the dependency files (located through AII_DEPS_ROOT, by artifact id), recomputes the
numbers with its own implementation and compares them with what eval.py wrote. Each family has a placebo that
corrupts its input in a way that must make the check FAIL. Writes audit/rederive_report.json."""

import csv
import json
import math
import os
import random
import statistics
import sys
from collections import Counter
from pathlib import Path

WS = Path(__file__).resolve().parent.parent
ROOT = Path(os.environ.get("AII_DEPS_ROOT", str(WS.parent)))
REPORT = Path(os.environ.get("AII_REPORT", str(WS / "inputs" / "report" / "current_report.md")))
_IDS = {"D19": ("art_mWn-MQEnNelg", "iter_4/gen_art/gen_art_experiment_19"),
        "D22": ("art_SHaWv77P1XCI", "iter_4/gen_art/gen_art_experiment_22"),
        "D24": ("art_CcZLW-9NX00l", "iter_5/gen_art/gen_art_experiment_24"),
        "PA": ("art_8WbrpoEFslk9", "iter_5/gen_art/gen_art_experiment_25"),
        "PB": ("art_9a8LrIv2lHbV", "iter_5/gen_art/gen_art_experiment_26"),
        "D27": ("art_jR6Pyy3W9xum", "iter_5/gen_art/gen_art_experiment_27"),
        "GEM": ("art_hG0QPiaIPNhP", "iter_5/gen_art/gen_art_experiment_28"),
        "EV4": ("art_mgek9PfVBNbh", "iter_5/gen_art/gen_art_evaluation_4")}


def _locate(nick):
    aid, folder = _IDS[nick]
    for c in (ROOT / aid, ROOT / folder.rsplit("/", 1)[-1], ROOT / folder, WS / "inputs" / aid):
        if c.is_dir():
            return c
    return ROOT / aid


DEP = {k: _locate(k) for k in _IDS}
CHECKS, PLACEBOS = [], []
ND = statistics.NormalDist()


def dj(nick, rel):
    return json.loads((DEP[nick] / rel).read_text())


def res(name):
    return json.loads((WS / "results" / f"{name}.json").read_text())


def check(family, name, expected, got, tol=0.0, rel=False):
    if isinstance(expected, (list, tuple)):
        ok = len(expected) == len(got) and all(_close(a, b, tol, rel) for a, b in zip(expected, got))
    else:
        ok = _close(expected, got, tol, rel)
    CHECKS.append({"family": family, "name": name, "expected": expected, "got": got, "pass": bool(ok)})
    return ok


def _close(a, b, tol, rel):
    if isinstance(a, str) or isinstance(b, str) or a is None or b is None:
        return a == b
    if isinstance(a, bool) or isinstance(b, bool):
        return bool(a) == bool(b)
    if not (math.isfinite(a) and math.isfinite(b)):
        return (math.isnan(a) and math.isnan(b)) or a == b
    return abs(a - b) <= (tol * max(abs(a), 1e-12) if rel else tol) + 1e-12


def placebo(name, family, result_bool, detail=""):
    PLACEBOS.append({"name": name, "family": family, "check_result": bool(result_bool),
                     "failed_as_required": not bool(result_bool), "detail": detail})


# ----------------------------------------------------------------------------------- exact tests (own code)
def hyper_pmf(a, r1, c1, n):
    return math.comb(r1, a) * math.comb(n - r1, c1 - a) / math.comb(n, c1)


def fisher_two_sided(k1, n1, k2, n2):
    r1, n, c1 = n1, n1 + n2, k1 + k2
    lo, hi = max(0, c1 - (n - r1)), min(r1, c1)
    p_obs = hyper_pmf(k1, r1, c1, n)
    return min(1.0, sum(hyper_pmf(a, r1, c1, n) for a in range(lo, hi + 1) if hyper_pmf(a, r1, c1, n) <= p_obs * (1 + 1e-7)))


def fisher_less(k1, n1, k2, n2):
    """P(K1 <= k1): group 1 has the lower event rate."""
    r1, n, c1 = n1, n1 + n2, k1 + k2
    lo = max(0, c1 - (n - r1))
    return min(1.0, sum(hyper_pmf(a, r1, c1, n) for a in range(lo, k1 + 1)))


def pb_sf(k, probs):
    dist = [1.0]
    for p in probs:
        nd = [0.0] * (len(dist) + 1)
        for i, v in enumerate(dist):
            nd[i] += v * (1 - p)
            nd[i + 1] += v * p
        dist = nd
    return sum(dist[k:])


def ranks(v):
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


def pearson(a, b):
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    den = math.sqrt(sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b))
    return num / den if den > 0 else float("nan")


def spearman(a, b):
    return pearson(ranks(a), ranks(b))


def fz_ci(r, n, kind):
    z = math.atanh(r)
    se = {"plain": 1 / math.sqrt(n - 3), "fieller": math.sqrt(1.06 / (n - 3)),
          "bonett_wright": math.sqrt((1 + r * r / 2) / (n - 3))}[kind]
    q = ND.inv_cdf(0.975)
    return [math.tanh(z - q * se), math.tanh(z + q * se)]


def perm_p(a, b, n_perm, seed):
    rng = random.Random(seed)
    obs = spearman(a, b)
    ra, rb = ranks(a), ranks(b)
    cnt = 0
    for _ in range(n_perm):
        rp = rb[:]
        rng.shuffle(rp)
        if pearson(ra, rp) >= obs - 1e-12:
            cnt += 1
    return (cnt + 1) / (n_perm + 1)


def kappa(a, b):
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    cats = set(a) | set(b)
    pe = sum((a.count(c) / n) * (b.count(c) / n) for c in cats)
    return float("nan") if abs(1 - pe) < 1e-12 else (po - pe) / (1 - pe)


def ac1(a, b, cats):
    n, q = len(a), len(cats)
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum(((a.count(c) + b.count(c)) / (2 * n)) * (1 - (a.count(c) + b.count(c)) / (2 * n)) for c in cats) / (q - 1)
    return (po - pe) / (1 - pe)


def exact_rarefied_hill(counts, depth):
    """Exact expectation of exp(Shannon) of a depth-sized subsample without replacement (multivariate hypergeometric)."""
    c = [x for x in counts if x > 0]
    n = sum(c)
    if len(c) == 1:
        return 1.0
    tot = math.comb(n, depth)
    acc = 0.0

    def rec(i, left, prob_num, comp):
        nonlocal acc
        if i == len(c) - 1:
            if left <= c[i]:
                comp2 = comp + [left]
                w = prob_num * math.comb(c[i], left)
                h = -sum((x / depth) * math.log(x / depth) for x in comp2 if x > 0)
                acc += w * math.exp(h)
            return
        for x in range(0, min(c[i], left) + 1):
            rec(i + 1, left - x, prob_num * math.comb(c[i], x), comp + [x])
    rec(0, depth, 1, [])
    return acc / tot


# ----------------------------------------------------------------------------------- families
def fam_dose():
    r0 = res("0a")
    rows = {r["task"]: r for r in r0["A1"]["rows"]}
    du = {r["task"]: r for r in csv.DictReader((DEP["EV4"] / "tables/dose_units.csv").read_text().splitlines())}
    units = dj("D22", "results/units.json")["per_task"]
    ur = dj("D27", "results/unit_ratio.json")
    for t in ["T1", "T2", "T03", "T05", "T06", "T10", "T14", "R6", "T04"]:
        check("dose", f"ratio of means {t}: units.json vs dose_units.csv", float(du[t]["banfree_over_ban"]),
              units[t]["ratio_mean_nfree_over_mean_n"], 0.005)
    for t in ["T03", "T10", "T2", "T05", "T1", "T06"]:
        check("dose", f"mean ratio {t}", ur[t]["banfree_over_ban_mean"], rows[t]["mean_ratio_knob_exp"], 1e-9)
    # bracket inequality: bf16 alpha 2 dose >= 1 FP8 ban unit under both definitions on every decisive task
    ok = all(2 * min(float(du[t]["banfree_over_ban"]), ur[t]["banfree_over_ban_mean"]) >= 1.0 for t in ["T03", "T10", "T2", "T05", "T1", "T06"])
    check("dose", "bracket dose inequality on all six decisive tasks", True, ok)
    # placebo: the conversion inverted (bf16 alpha-1 cell compared with FP8 alpha 1 expressed in bf16 units, 1/ratio)
    inv_ok = all(1.0 >= 1.0 / min(float(du[t]["banfree_over_ban"]), ur[t]["banfree_over_ban_mean"]) for t in ["T03", "T10", "T2", "T05", "T1", "T06"])
    placebo("dose ratios inverted (bracket inequality must fail on >= 1 task)", "dose", inv_ok)


def engine_counts(rows_path, tasks, arms):
    cnt = {}
    with rows_path.open() as f:
        for line in f:
            r = json.loads(line)
            if r.get("task") in tasks and r.get("arm") in arms:
                cnt.setdefault((r["task"], r["arm"]), []).append((r.get("label"), bool(r.get("passed"))))
    return cnt


def fam_engine():
    r0 = res("0a")["A2"]["per_task"]
    tasks = ["T03", "T10", "T2", "T05", "T1", "T06"]
    bf = engine_counts(DEP["D27"] / "data/labels.jsonl", tasks, {"TWIN", "PN_a1", "PN_a2"})
    fp = engine_counts(DEP["D19"] / "data/labels.jsonl", tasks, {"TWIN", "PN_a1", "PN_a2"})
    recomputed = {}
    for t in tasks:
        tw = Counter(l for l, p in bf[(t, "TWIN")] if p)
        default = tw.most_common(1)[0][0]
        for eng, src, key in (("bf16", bf, "bf16"), ("fp8", fp, "fp8")):
            for arm, a in (("PN_a1", "1.0"), ("PN_a2", "2.0")):
                rows = src[(t, arm)]
                cor = [l for l, p in rows if p]
                k_cor = sum(1 for l in cor if l != default)
                k_att = sum(1 for l, p in rows if l not in (default, "invalid"))
                recomputed[(t, eng, a)] = (k_cor, len(cor), k_att, len(rows))
                rec = r0[t][key][a]
                check("engine", f"{t} {eng} a{a} correct off-default", rec["cor_off"], k_cor)
                check("engine", f"{t} {eng} a{a} n correct", rec["n_correct"], len(cor))
                check("engine", f"{t} {eng} a{a} attempts off-default", rec["att_off"], k_att)
    for t in ["T03", "T10", "T2", "T05", "T1"]:
        kb, nb = recomputed[(t, "bf16", "2.0")][:2]
        kf, nf = recomputed[(t, "fp8", "2.0")][:2]
        check("engine", f"{t} Fisher two-sided a2 (correct-only)", r0[t]["cor"]["fisher_two_sided_matched_alpha"]["2.0"],
              fisher_two_sided(kb, nb, kf, nf), 0.02, rel=True)
        kf1, nf1 = recomputed[(t, "fp8", "1.0")][:2]
        check("engine", f"{t} bracket one-sided p (correct-only)", r0[t]["cor"]["bracket"]["p_one_sided_less"],
              fisher_less(kb, nb, kf1, nf1), 0.02, rel=True)
    # placebo: engine labels swapped between bf16 and FP8 rows -> the FP8 > bf16 effect on T10 vanishes
    kb, nb = recomputed[("T10", "fp8", "2.0")][:2]   # swapped
    kf, nf = recomputed[("T10", "bf16", "2.0")][:2]
    placebo("engine labels swapped (T10 alpha 2: bf16 lower than FP8 at p < 0.01 must fail)", "engine",
            fisher_less(kb, nb, kf, nf) < 0.01, f"p {fisher_less(kb, nb, kf, nf):.3g}")


def fam_landing():
    r0 = res("0b")
    a2 = dj("PA", "results/a2.json")
    a2b = dj("PB", "results/a2_panel.json")
    ea2 = dj("GEM", "results/e_a2.json")
    scr = dj("D24", "results/screen_check.json")["r_t_vs_push_landing"]
    br = dj("D24", "results/base_repertoire.json")["per_task"]
    ex = dj("PA", "results/extra_arm_a.json")
    sets = {
        "FP8 screen": [(scr[t]["push_top1"], scr[t]["r_t"], 1 / len(br[t]["predicted_landing_composition"])) for t in ["T03", "T2", "T05", "T10", "T1"]],
        "bf16 existing remeasure": [(ex[t]["landing"], br[t]["r_t"], 1 / len(br[t]["predicted_landing_composition"])) for t in ["T03", "T10"]],
        "panel A": [(e["L"], e["r"], e["chance"]) for e in a2["events"]],
        "panel B": [(e["push_landing"], e["r_u"], e["chance"]) for e in a2b["events"]],
        "Gemma": [(e["landing"], e["r_u"], c) for e, c in zip(ea2["events"], ea2["chance"])]}
    allev = []
    for s, ev in sets.items():
        h = sum(L == r for L, r, _ in ev)
        check("landing", f"hits {s}", r0["tally"][s]["hits"], h)
        check("landing", f"Poisson-binomial p {s}", r0["tally"][s]["pb_p"], pb_sf(h, [c for _, _, c in ev]), 1e-9)
        allev += ev
    h = sum(L == r for L, r, _ in allev)
    check("landing", "hits total (17 of 21 expected)", 17, h)
    check("landing", "Poisson-binomial p total", r0["tally"]["all"]["pb_p"], pb_sf(h, [c for _, _, c in allev]), 1e-9)
    # confound subset from twin compositions
    pa = {u["unit_id"]: u for u in dj("PA", "pooled_inputs.json")["units"]}
    pb = {u["unit_id"]: u for u in dj("PB", "pooled_inputs.json")["records"]}
    gp = dj("GEM", "results/predictors.json")["units"]
    unc = []
    for e in a2["events"]:
        u = pa[e["unit"]]
        if not any(v > 0 for k, v in u["twin"]["comp_correct"].items() if k != u["default"]):
            unc.append((e["L"] == e["r"], e["chance"]))
    for e in a2b["events"]:
        u = pb[e["unit"]]
        d = u["unit_facts"]["default"]
        if not any(v > 0 for k, v in u["twin"]["correct_composition"].items() if k != d):
            unc.append((e["push_landing"] == e["r_u"], e["chance"]))
    for e, c in zip(ea2["events"], ea2["chance"]):
        g = gp[e["unit"]]
        if not any(v > 0 for k, v in g["default"]["correct_counts"].items() if k != g["D"]):
            unc.append((e["landing"] == e["r_u"], c))
    hu = sum(x for x, _ in unc)
    check("landing", "unconfounded events (8 expected)", 8, len(unc))
    check("landing", "unconfounded hits (5 expected)", 5, hu)
    check("landing", "unconfounded pooled p", r0["confound"]["pooled"]["pb_p"], pb_sf(hu, [c for _, c in unc]), 1e-9)
    # placebo: landings shuffled across events (within sets): the significant total tally must not survive
    rng = random.Random(3)
    sig = 0
    for _ in range(200):
        tot, probs = 0, []
        for s, ev in sets.items():
            Ls = [L for L, _, _ in ev]
            rng.shuffle(Ls)
            tot += sum(L == r for L, (_, r, _) in zip(Ls, ev))
            probs += [c for _, _, c in ev]
        sig += pb_sf(tot, probs) < 0.001
    placebo("landings shuffled across events (tally p < 0.001 in most shuffles must fail)", "landing", sig > 100, f"{sig}/200 significant")


def fam_movability():
    r0 = res("0c")
    core = [u for u in r0["units"] if u["core13"]]
    pa = {u["unit_id"]: u for u in dj("PA", "pooled_inputs.json")["units"]}
    pb = {u["unit_id"]: u for u in dj("PB", "pooled_inputs.json")["records"]}
    x, y = [], []
    for u in core:
        if u["panel"] == "A":
            x.append(pa[u["unit"]]["base"]["beta"]); y.append(pa[u["unit"]]["escape"]["E"])
        else:
            x.append(pb[u["unit"]]["base"]["beta_u"]); y.append(pb[u["unit"]]["outcomes"]["E_u"])
    rho = spearman(x, y)
    check("movability", "rho(beta, E) over 13 units", r0["rho"], rho, 1e-9)
    check("movability", "rho rounds to the recorded 0.15", 0.15, round(rho, 2))
    for kind in ("plain", "fieller", "bonett_wright"):
        check("movability", f"Fisher-z CI {kind}", r0["ci"][kind], fz_ci(rho, 13, kind), 1e-9)
    check("movability", "permutation p (Monte Carlo 20,000)", r0["perm"]["p"], perm_p(x, y, 20000, 7), 0.02)
    # power by an independent simulation: Gaussian copula, empirical margins, permutation test
    rng = random.Random(11)
    r = 2 * math.sin(math.pi * 0.6 / 6)
    xs, ys = sorted(x), sorted(y)
    reps, nperm, rej = 1500, 400, 0
    for _ in range(reps):
        a, b = [], []
        for _ in range(13):
            z1 = rng.gauss(0, 1)
            z2 = r * z1 + math.sqrt(1 - r * r) * rng.gauss(0, 1)
            a.append(xs[min(int(ND.cdf(z1) * 13), 12)])
            b.append(ys[min(int(ND.cdf(z2) * 13), 12)])
        if len(set(a)) < 2 or len(set(b)) < 2:
            continue
        ra, rb = ranks(a), ranks(b)
        obs = pearson(ra, rb)
        c = 0
        for _ in range(nperm):
            rp = rb[:]
            rng.shuffle(rp)
            c += pearson(ra, rp) >= obs - 1e-12
        rej += (c + 1) / (nperm + 1) <= 0.05
    check("movability", "power at rho 0.6 (+-0.03 Monte Carlo)", r0["power"]["0.6"]["power"], rej / reps, 0.03)
    for k, v in r0["rivals"].items():
        vals = [v["values"][u["unit"]] for u in core]
        rr = spearman([v["sign"] * z for z in vals], y)
        check("movability", f"rival {k} rho", v["rho_with_E"], rr, 1e-9)
    # placebo: beta permuted across units must not reproduce the recorded rho
    rng = random.Random(5)
    hits = 0
    for _ in range(200):
        xp = x[:]
        rng.shuffle(xp)
        hits += abs(spearman(xp, y) - rho) < 0.005
    placebo("beta permuted across units (recorded rho reproduced in most permutations must fail)", "movability", hits > 100, f"{hits}/200")


def fam_tables():
    r0 = res("0d")
    lit = dj("D27", "results/literal_cell.json")["per_T"]
    for row in r0["D1"]:
        ph = lit[row["cell"]]["phrasing"]
        check("tables", f"phrasing clusters {row['cell']}", [ph[f"theta_{t}"]["n_clusters"] for t in ("0.7", "0.8", "0.9")],
              [row[f"n_clusters_theta{t}"] for t in ("0.7", "0.8", "0.9")])
    exp = {"LIT_T0.3": [2, 4, 8], "LIT_T0.7": [3, 3, 10], "LIT_T1.0": [2, 3, 9], "LIT_T1.3": [5, 7, 12]}
    for k, v in exp.items():
        check("tables", f"phrasing clusters {k} against the expected", v, [lit[k]["phrasing"][f"theta_{t}"]["n_clusters"] for t in ("0.7", "0.8", "0.9")])
    pr = dj("D27", "results/prices.json")
    for t, a, k, e in (("T10", "BINT", "P15", 0.005), ("T10", "BINT", "P20", 0.011), ("T2", "EAP", "P15", 0.103),
                       ("T2", "EAP", "P20", 0.19), ("T03", "NOVELTY", "P20", 0.018)):
        check("tables", f"{k} {a} {t}", e, round(pr[t][a][k], 3), 0.001)
    pb = {u["unit_id"]: u for u in dj("PB", "pooled_inputs.json")["records"]}
    for row in r0["D3"]:
        o = pb[row["unit"]]["outcomes"]
        c = {"twin": o["twin_cell"], "plan noise alpha 1": o["pn_cells"]["1.0"], "plan noise alpha 2": o["pn_cells"]["2.0"],
             "temperature 1.3": o["t13_cell"]}[row["arm"]]
        lc = c.get("labels_correct") or {}
        d = pb[row["unit"]]["unit_facts"]["default"]
        off = sum(v for k, v in lc.items() if k != d)
        check("tables", f"panel B {row['unit']} {row['arm']} correct off-default", row["offdef_correct"], off)
        n = sum(lc.values())
        if n and len([v for v in lc.values() if v > 0]) <= 5:
            check("tables", f"panel B {row['unit']} {row['arm']} Hill-1 (exact rarefaction vs Monte Carlo)", row["hill1_rarefied"],
                  exact_rarefied_hill(list(lc.values()), min(25, n)), 0.02)
    b3 = [r for r in r0["D3"] if r["unit"] == "B3"]
    check("tables", "B3 T1.3 Prim 18/49", "18/49", f"{[r for r in b3 if r['arm'] == 'temperature 1.3'][0]['labels_correct'].get('prim_heap')}/49")
    for rid, e in (("K0522", 2.87), ("K0523", 2.96), ("K0524", 2.92)):
        got = [r for r in r0["D5"] if r["row_id"] == rid][0]["H1r25"]
        check("tables", f"Table 126c {rid} Hill-1", e, round(got, 2), 0.005)


def fam_judges():
    p = WS / "results" / "0f.json"
    if not p.exists():
        return
    r0 = json.loads(p.read_text())
    items = [i for i in r0["items"] if i["kind"] == "disputed_14" or i["kind"].startswith("control")]
    items = [i for i in items if "judge_primary" in i]
    cats = ["NOVEL_ALGORITHM", "KNOWN_OUTSIDE_CATALOGUE", "CATALOGUE_VARIANT", "DEGENERATE"]
    tr = [i["truth"] for i in items]
    pr = [i["judge_primary"] for i in items]
    k = kappa(tr, pr)
    f6 = r0["F6"]["judge_primary"]
    check("judges", "kappa (4 class, 24 items)", f6["all_24"]["kappa_4class"], k, 1e-9)
    check("judges", "AC1 (4 class, 24 items)", f6["all_24"]["ac1_4class"], ac1(tr, pr, cats), 1e-9)
    core = [i for i in items if i["kind"] == "disputed_14"]
    check("judges", "raw agreement on the 14", f6["disputed_14"]["raw_agree_4class"],
          sum(i["truth"] == i["judge_primary"] for i in core) / len(core), 1e-9)
    check("judges", "controls correct", f6["controls_correct"], sum(i["truth"] == i["judge_primary"] for i in items if i["kind"].startswith("control")))
    check("judges", "novel calls on the 14", r0["readj_novel_k"], sum(i["judge_primary"] == "NOVEL_ALGORITHM" for i in core))
    rng = random.Random(9)
    ks = []
    for _ in range(300):
        pp = pr[:]
        rng.shuffle(pp)
        kk = kappa(tr, pp)
        if math.isfinite(kk):
            ks.append(kk)
    mk = sum(ks) / len(ks)
    placebo("judge verdicts shuffled (kappa reproduced within 0.05 must fail)", "judges", abs(mk - k) < 0.05, f"mean shuffled kappa {mk:.3f} vs {k:.3f}")


def fam_corrections():
    rep = REPORT.read_text()
    c = json.loads((WS / "corrections.json").read_text())["corrections"] if (WS / "corrections.json").exists() else []
    spans = []
    for x in c:
        n = rep.count(x["old_text"])
        check("corrections", f"{x['id']} old_text is an exact unique substring", 1, n)
        i = rep.find(x["old_text"])
        spans.append((i, i + len(x["old_text"])))
        check("corrections", f"{x['id']} marker", "iteration-6 correction", x["marker"])
    spans.sort()
    check("corrections", "old_text spans are disjoint", True, all(b[0] >= a[1] for a, b in zip(spans, spans[1:])))


def main():
    for fam in (fam_dose, fam_engine, fam_landing, fam_movability, fam_tables, fam_judges, fam_corrections):
        try:
            fam()
        except (KeyError, FileNotFoundError, ValueError, ZeroDivisionError) as e:
            CHECKS.append({"family": fam.__name__, "name": "family crashed", "expected": None, "got": repr(e), "pass": False})
    out = {"n_checks": len(CHECKS), "n_passed": sum(c["pass"] for c in CHECKS),
           "n_placebos": len(PLACEBOS), "n_placebos_failed": sum(p["failed_as_required"] for p in PLACEBOS),
           "failed_checks": [c for c in CHECKS if not c["pass"]], "placebos": PLACEBOS, "checks": CHECKS}
    (WS / "audit" / "rederive_report.json").write_text(json.dumps(out, indent=1, default=str))
    print(f"checks {out['n_passed']}/{out['n_checks']} passed; placebos failed as required {out['n_placebos_failed']}/{out['n_placebos']}")
    for c in out["failed_checks"]:
        print("FAILED:", c["family"], c["name"], c["expected"], c["got"])


if __name__ == "__main__":
    main()
