"""Recompute the iteration-4 numbers this review relies on, from the artifacts' own raw and result files.

Read-only over the artifact workspaces; standard library only; prints to stdout.
Run: python3 verify_iter4.py > verify_iter4.log
"""
import difflib
import itertools
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

LOOP = Path(__file__).resolve().parents[2]
ART = LOOP / "round-4"
EVAL3 = ART / "evaluation-3/src"      # record audit
EXP19 = ART / "experiment-19/src"     # plan noise price
EXP20 = ART / "experiment-20/src"     # site
EXP21 = ART / "experiment-21/src"     # same seed
EXP22 = ART / "experiment-22/src"     # plan subspace
EXP23 = ART / "experiment-23/src"     # held-out family (gemma-3-4b-it)
RES1 = ART / "research-1/src"         # positioning audit
DRAFT3 = LOOP / "round-3/report-text/paper_draft.md"
DRAFT4 = LOOP / "round-4/report-text/paper_draft.md"


def jsonl(p):
    with open(p) as f:
        return [json.loads(line) for line in f if line.strip()]


def section(title):
    print(f"\n=== {title}")


def hill_rare(labels, depth=25, draws=3000, seed=0):
    if len(labels) < depth:
        return None
    rng = random.Random(seed)
    tot = 0.0
    for _ in range(draws):
        c = Counter(rng.sample(labels, depth))
        tot += math.exp(-sum(v / depth * math.log(v / depth) for v in c.values()))
    return round(tot / draws, 2)


def fisher_two_sided(a, b, c, d):
    n, r1, c1 = a + b + c + d, a + b, a + c

    def p(x):
        return math.comb(r1, x) * math.comb(n - r1, c1 - x) / math.comb(n, c1)

    p0 = p(a)
    return sum(p(x) for x in range(max(0, c1 - (n - r1)), min(r1, c1) + 1) if p(x) <= p0 + 1e-12)


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


def spearman(x, y):
    rx, ry = ranks(x), ranks(y)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return num / den


# ---------------------------------------------------------------- chronology
section("Chronology: every change to iterations 1-3 between the iter-3 and iter-4 drafts")
a = DRAFT3.read_text()
b = DRAFT4.read_text()
A = a[: a.find("# What we have learned so far")].splitlines()
B = b[: b.find("# Iteration 4")].splitlines()
sm = difflib.SequenceMatcher(None, A, B, autojunk=False)
n_hunks = n_marked = 0
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    if tag == "equal":
        continue
    n_hunks += 1
    new = "\n".join(B[j1:j2])
    marked = "iteration 4" in new
    n_marked += marked
    if not marked:
        print("  UNMARKED hunk", tag, i1, i2, "->", j1, j2, new[:200])
print("hunks", n_hunks, "marked 'iteration 4'", n_marked)

# ---------------------------------------------------------------- exp19
section("Plan noise price (exp19): Table 141 alpha sweep, Table 137 per-task decision")
rows19 = jsonl(EXP19 / "data/samples.jsonl")
print("rows", len(rows19), "cells", len(Counter((r["task"], r["arm"]) for r in rows19)))
for t in ["T03", "T05", "T06", "T10", "T1", "T2"]:
    for arm in ["TWIN", "PN_a0.5", "PN_a1", "PN_a2", "PN_a4", "PN_a8"]:
        R = [r for r in rows19 if r["task"] == t and r["arm"] == arm]
        n = len(R)
        print(f"  {t} {arm:8s} pass {sum(r['passed'] for r in R)/n:.2f} off "
              f"{sum(1 for r in R if r['valid'] and not r['is_default'])/n:.2f} correct "
              f"{dict(Counter(r['label'] for r in R if r['passed']))}")
c1 = json.load(open(EXP19 / "results/c1.json"))
pr = c1["primary"]
print("verdict", pr["verdict"], "count1", pr["count1"], "count2", pr["count2"], "D_bar", round(pr["D_bar"], 3),
      [round(x, 2) for x in pr["D_bar_ci95"]])
for t, v in pr["per_task"].items():
    print(f"  {t}: H5_PN {v['H5_PN']:.2f} best {v['best_na']} {v['H5_best']:.2f} D {v['D_t']:.2f} "
          f"CI {[round(x, 2) for x in v['D_t_boot_ci95']]} P {v['P_boot_PN_gt_best']}")

section("exp19 Table 140 flips (code differs / label differs vs TWIN, CRN-paired)")
by = defaultdict(dict)
for r in rows19:
    by[(r["task"], r["crn_key"])][r["arm"]] = r
for t in ["T1", "T03", "T10", "T2"]:
    out = []
    for arm in ["T1.3", "T1.6", "TOPK10", "PN_a1", "PN_a2"]:
        n = cd = ld = 0
        for (tt, _), d in by.items():
            if tt != t or "TWIN" not in d or arm not in d:
                continue
            n += 1
            cd += d[arm]["code_sha256"] != d["TWIN"]["code_sha256"]
            ld += d[arm]["label"] != d["TWIN"]["label"]
        out.append(f"{arm} {cd/n:.2f}/{ld/n:.2f}")
    print(" ", t, "; ".join(out))

section("exp19 executed arm not in the report: plan noise on the PLAIN prompt (PNPLAIN_a1) vs on the twin (PN_a1)")
for t in ["T03", "T05", "T06", "T10", "T1", "T2"]:
    for arm in ["PLAIN", "TWIN", "PNPLAIN_a1", "PN_a1"]:
        R = [r for r in rows19 if r["task"] == t and r["arm"] == arm]
        print(f"  {t} {arm:10s} pass {sum(r['passed'] for r in R)/len(R):.2f} off "
              f"{sum(1 for r in R if r['valid'] and not r['is_default'])/len(R):.2f} "
              f"{dict(Counter(r['label'] for r in R if r['passed']))}")
devs = jsonl(EXP19 / "results/deviations.jsonl")
for dv in devs:
    if dv["id"] == "D-hull-edges":
        print("deviation D-hull-edges (not in report):", dv["deviation"][:400])
prices = json.load(open(EXP19 / "results/prices.json"))


def tri_gaps(o, path=""):
    if isinstance(o, dict):
        if o.get("triangle_minus_edge") not in (None, 0.0):
            print(f"  triangle_minus_edge {path}: {o['triangle_minus_edge']:+.3f} (H5 {o.get('H5', float('nan')):.3f})")
        for k, v in o.items():
            tri_gaps(v, f"{path}/{k}")


tri_gaps(prices)

# ---------------------------------------------------------------- exp20
section("Site (exp20): inert sites, energy-matched read position, generated-token noise, boundary depths, TOP5")
rows20 = [r for r in jsonl(EXP20 / "data/samples.jsonl") if r.get("analysed")]
D = {"T03": "full_sort", "T05": "hash_map", "T06": "hash_set", "T10": "union_find", "T1": "bfs", "T2": "dijkstra"}
for site in ["S1", "S2", "S5", "S3", "S4", "S0"]:
    corr = off = 0
    for al in ["a1", "a2", "a4"]:
        for r in rows20:
            if r["arm"] == f"{site}_{al}" and r["passed"]:
                corr += 1
                off += r["label"] != D[r["task"]]
    print(f"  {site} alpha 1-4: correct {corr}, off default {off}")
for arm in ["S1E_a1", "S2E_a1"]:
    for t in D:
        R = [r for r in rows20 if r["task"] == t and r["arm"] == arm]
        print(f"  {arm} {t}: pass {sum(r['passed'] for r in R)/len(R):.2f} correct "
              f"{dict(Counter(r['label'] for r in R if r['passed']))}")
for t in ["T06", "T05"]:
    for arm in ["S0_a2", "S3_a2"]:
        R = [r for r in rows20 if r["task"] == t and r["arm"] == arm]
        print(f"  {t} {arm}: pass {sum(r['passed'] for r in R)/len(R):.2f} correct "
              f"{dict(Counter(r['label'] for r in R if r['passed']))}")
pf = json.load(open(EXP20 / "results/paired_flips.json"))
print("  paired flips S0 vs S3 at alpha 2, T06:", pf["T06|S3|2"]["table_attempts[both,S0only,siteonly,neither]"],
      "p", pf["T06|S3|2"]["mcnemar_p_attempts"])
bd = json.load(open(EXP20 / "results/boundary.json"))
for t, v in bd["per_task"].items():
    c4 = [c for c in v["curve"] if c["alpha"] == 4.0][0]
    print(f"  boundary {t} alpha 4: Hill {c4['hill_correct'] and round(c4['hill_correct'], 2)} at depth {c4['hill_depth']}"
          f" from {c4['correct_composition']}")
for arm in ["TWIN", "TOP5_a1", "TOP5_a2", "TOP5_a4"]:
    R = [r for r in rows20 if r["task"] == "T1" and r["arm"] == arm]
    print(f"  T1 {arm}: correct {dict(Counter(r['label'] for r in R if r['passed']))}")
tr = json.load(open(EXP20 / "results/transmission.json"))
print("  pooled S0 indicator", round(tr["disp_R35"]["params"]["is_S0"], 2), [round(x, 2) for x in tr["disp_R35"]["ci95"]["is_S0"]],
      "| per-site model, S4 vs S0:", round(tr["disp_R35_sites"]["params"]["C(site, Treatment('S0'))[T.S4]"], 2),
      [round(x, 2) for x in tr["disp_R35_sites"]["ci95"]["C(site, Treatment('S0'))[T.S4]"]])

# ---------------------------------------------------------------- exp21
section("Same seed (exp21): temperature and plan-noise change counts (Table 150)")
rows21 = jsonl(EXP21 / "data/samples.jsonl")
print("  temperature block sampler:", Counter((r["arm"], r["top_k"]) for r in rows21 if r["arm"].startswith("NOPN_T")))
x_s = []
for task in ["T2", "T03", "T1"]:
    lab = defaultdict(dict)
    for r in rows21:
        if r["task"] == task and not r["thinking"]:
            lab[r["seed"]][r["arm"]] = r["label"]
    seeds = [s for s in lab if "NOPN_T1.0" in lab[s]]
    temps = ["NOPN_T0.3", "NOPN_T0.7", "NOPN_T1.0", "NOPN_T1.3"]
    ct = sum(1 for s in seeds if len({lab[s][a] for a in temps}) > 1)
    res = []
    for al, T in [("1.0", "0.7"), ("1.0", "1.0"), ("2.0", "0.7"), ("2.0", "1.0")]:
        dirs = [f"PN_D4600{i}_a{al}_T{T}" for i in range(1, 7)]
        per_seed = defaultdict(float)
        subs = list(itertools.combinations(dirs, 3))
        for sub in subs:
            for s in seeds:
                if len({lab[s][a] for a in sub} | {lab[s][f"NOPN_T{T}"]}) > 1:
                    per_seed[s] += 1 / len(subs)
        res.append(round(sum(per_seed.values()), 2))
        if (al, T) == ("1.0", "1.0") and task in ("T2", "T03"):
            x_s += [per_seed[s] - (1 if len({lab[s][a] for a in temps}) > 1 else 0) for s in seeds]
    print(f"  {task}: seeds {len(seeds)} temperature changes {ct}; PN (a1 T0.7, a1 T1.0, a2 T0.7, a2 T1.0) {res}")
print("  pooled contrast x_s (T2+T03, a1 T1.0):", round(sum(x_s) / len(x_s), 3), "over", len(x_s), "seeds")

# ---------------------------------------------------------------- exp22
section("Plan subspace (exp22): escape fractions, correlations, reliability, exploratory signed progress, C3b event sets")
esc = json.load(open(EXP22 / "results/escape.json"))
for t, v in esc.items():
    print(f"  {t}: " + ", ".join(f"a{a} {e['n_confirmed']}/{e['n_run']}" for a, e in v["E_t"].items()),
          "landing", {k: round(x, 2) for k, x in (v.get("push_landing_v4") or {}).items()})
c2a = json.load(open(EXP22 / "results/c2a.json"))
print("  pooled within-task rho", round(c2a["pooled_within_task_rho"]["rho"], 3),
      [round(x, 3) for x in c2a["pooled_within_task_rho"]["task_bootstrap_ci"]], "verdict", c2a["verdict"]["reading"])
ex = json.load(open(EXP22 / "results/explore.json"))
tot = pos = sig = 0
for t, v in ex["tasks"].items():
    if "profile" not in v:
        continue
    pr_ = v["profile"]["proj_r"]
    pp = v["profile"]["proj_r_p"]
    bl = v["blocks"]
    plan = [pr_[i] for i, blk in enumerate(bl) if 12 <= blk <= 23]
    nsig = sum(1 for p in pp if p < 0.05)
    tot += len(pr_)
    pos += sum(1 for x in pr_ if x > 0)
    sig += nsig
    print(f"  {t}: template-half reliability {v['y_reliability']['rho_template_halves']:.2f}; signed progress max "
          f"{max(pr_):.2f} @block {bl[pr_.index(max(pr_))]}, mean over blocks 12-23 {sum(plan)/len(plan):.2f}, "
          f"block 18 {pr_[bl.index(18)]:.2f}, cells p<0.05 {nsig}/24")
print(f"  signed progress: {pos}/{tot} cells positive, {sig}/{tot} cells p<0.05 (uncorrected)")
c3b = json.load(open(EXP22 / "results/c3b.json"))
ev = c3b["events"]
gated = c3b["gated_events"]
push_def = [t for t in gated if ev[t]["defined"]["PUSH"]]
for f in ["PUSH", "PUSH_SCREEN", "LADDER_OPEN", "ASSOCIATE", "PROXIMITY"]:
    dfd = [t for t in gated if ev[t]["defined"][f]]
    print(f"  {f}: mean over its defined events ({len(dfd)}) {sum(ev[t]['logscore'][f] for t in dfd)/len(dfd):.2f}; "
          f"over the PUSH-defined events {push_def} {sum(ev[t]['logscore'][f] for t in push_def)/len(push_def):.2f}; "
          f"over all 5 gated (undefined = uniform) {sum(ev[t]['logscore'][f] for t in gated)/len(gated):.2f}")

# ---------------------------------------------------------------- exp23
section("Held-out family (exp23, gemma-3-4b-it): C3a, sensitivities, grid default, shortest path labels")
c3a = json.load(open(EXP23 / "results/c3a.json"))
p = c3a["primary"]
E, Av, T = p["E_t"], p["A_t"], p["tasks"]
pred = {t: E[t] > 0 for t in T}
obs = {t: Av[t] >= 0.5 for t in T}
tp = sum(pred[t] and obs[t] for t in T)
fp = sum(pred[t] and not obs[t] for t in T)
fn = sum(not pred[t] and obs[t] for t in T)
tn = sum(not pred[t] and not obs[t] for t in T)
ba = (tp / (tp + fn) + tn / (tn + fp)) / 2
print(f"  table [[{tp},{fp}],[{fn},{tn}]] BA {ba:.3f} Fisher {fisher_two_sided(tp, fp, fn, tn):.3f} "
      f"Spearman {spearman([E[t] for t in T], [Av[t] for t in T]):.3f} verdict {p['verdict']}")
for k, v in c3a["sensitivities"].items():
    if "verdict" in v:
        print(f"  sensitivity {k}: BA {v.get('BA')} verdict {v['verdict']}")
rows23 = jsonl(EXP23 / "data/samples.jsonl")
pilot = json.load(open(EXP23 / "predictions/commit1.json"))["pilot"]["T1"]
print("  grid pilot (froze the default):", pilot["correct_labels"], "labels_all", pilot["labels_all"], "default", pilot["D_g"])
for arm in ["twin", "ban", "pn_a1", "pn_a2"]:
    print(f"  grid {arm}: {dict(Counter(r['label'] for r in rows23 if r['task'] == 'T1' and r['arm'] == arm))}")
for arm in ["twin", "pn_a1", "pn_a2", "novelty", "ban"]:
    print(f"  shortest path {arm} correct: "
          f"{dict(Counter(r['label'] for r in rows23 if r['task'] == 'T2' and r['arm'] == arm and r['passed']))}")
for t in ["T06"]:
    print(f"  find duplicate ban: {dict(Counter(r['label'] for r in rows23 if r['task'] == t and r['arm'] == 'ban'))}")

# ---------------------------------------------------------------- eval3
section("Record audit (eval3): Llama knob cells, per-task verdicts")
import csv  # noqa: E402

kt = list(csv.DictReader(open(EVAL3 / "tables/knob_table.csv")))
ll = [r for r in kt if r["model"].startswith("meta") and r["class"] == "knob"]
print("  Llama knob cells", len(ll), "qualifying", sum(r["qualify"] == "True" for r in ll),
      "random-direction cells", sum(r["family"] == "activation-random" for r in ll),
      "random qualifying", sum(r["family"] == "activation-random" and r["qualify"] == "True" for r in ll))
for r in ll:
    if r["qualify"] == "True":
        print(f"    qualifies: {r['task']} {r['arm']} H1r25 {float(r['H1r25']):.2f} cost {float(r['pass_cost_pts']):.1f}")
for r in csv.DictReader(open(EVAL3 / "tables/per_task_verdict.csv")):
    print(f"  {r['task']}: best<=5 {r['best_le5_arm']} {r['best_le5_H1r25']} @{r['best_le5_cost']}; "
          f"random qualifying {r['n_qualifying_random_directions']}/{r['n_random_directions_run']}")

# ---------------------------------------------------------------- research
section("Positioning (research_1): rows for the novelty-boundary claim")
for line in (RES1 / "research_report.md").read_text().splitlines():
    if line.startswith("| C3c"):
        cells = [c.strip() for c in line.split("|")]
        print("  ", cells[1], "|", cells[3][:90], "|", cells[-2][:60])
