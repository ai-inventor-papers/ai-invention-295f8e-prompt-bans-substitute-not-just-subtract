"""Recompute the iteration-3 headline numbers this review relies on, from the artifacts' own raw files.

Read-only over the artifact workspaces; prints everything to stdout (redirect to verify_iter3.log).
Run: python3 verify_iter3.py > verify_iter3.log
"""
import itertools
import json
import math
import random
import re
from collections import Counter, defaultdict
from pathlib import Path

RUN = Path(__file__).resolve().parents[2]
EXP13 = RUN / "round-3/experiment-13/src"  # bench forecast (Qwen3-8B)
EXP14 = RUN / "round-3/experiment-14/src"  # exposure bans
EXP15 = RUN / "round-3/experiment-15/src"  # Llama bench
EXP16 = RUN / "round-3/experiment-16/src"  # bench route
EXP17 = RUN / "round-3/experiment-17/src"  # locus
EVAL2 = RUN / "round-3/evaluation-2/src"  # record audit


def jsonl(p):
    return [json.loads(line) for line in open(p)]


def hill_rare(labels, depth=25, draws=2000, seed=0):
    """Rarefied Hill-1 at a fixed depth (mean of exp(Shannon) over draws without replacement)."""
    if len(labels) < depth:
        return None
    rng = random.Random(seed)
    tot = 0.0
    for _ in range(draws):
        c = Counter(rng.sample(labels, depth))
        tot += math.exp(-sum(v / depth * math.log(v / depth) for v in c.values()))
    return round(tot / draws, 2)


def section(title):
    print(f"\n=== {title}")


section("Exposure experiment (exp14): gate, snap-back, wins, hit rates")
ev = jsonl(EXP14 / "results/c1_events.jsonl")
for et in ("exposure_named", "exposure_unnamed"):
    E = [e for e in ev if e["event_type"] == et]
    G = [e for e in E if e["gate_pass"]]
    md = sum(1 for e in G if e["default"] in e["modal"])
    pr = [e for e in G if e["priority"]]
    wins = Counter()
    for e in G:
        if not e["disagreeing"]:
            continue
        s = sorted(e["logscore"].items(), key=lambda kv: -kv[1])
        if s[0][1] - s[1][1] >= 0.10:
            wins[s[0][0]] += 1
    print(et, "events", len(E), "gated", len(G), "disagreeing", sum(e["disagreeing"] for e in G),
          "modal==default", md, "priority", sum(1 for e in pr if e["default"] in e["modal"]), "of", len(pr),
          "mean default share", round(sum(e["default_share"] for e in E) / len(E), 3), "wins", dict(wins))
    for f in ("LADDER", "PROXIMITY", "ASSOCIATE", "SUBTRACT"):
        print("   hit rate (fractional tie credit)", f, round(sum(e["hit"][f] for e in G) / len(G), 3))
    dfn = [e for e in G if e["forecasts"]["SUBTRACT"] is not None]
    print("   SUBTRACT defined on", len(dfn), "gated events; defined-only hits",
          sum(e["hit"]["SUBTRACT"] for e in dfn), [(e["task"], e["Y"], e["top1"]["SUBTRACT"], e["modal"]) for e in dfn])
tmpl = json.load(open(EXP14 / "results/other_reports.json"))["template_arm"]
named = {e["task"] + ":" + e["Y"]: e for e in ev if e["event_type"] == "exposure_named"}
n_def = n_assoc = 0
for key, tp in tmpl.items():
    e = named[key]
    agg = Counter()
    for v in tp.values():
        agg.update(v.get("landing") or {})
    if not agg:
        continue
    top = agg.most_common(1)[0][0]
    n_def += top == e["default"]
    n_assoc += top == next(iter(e["associate"]))
    if top != e["modal"][0]:
        print("   template arm W1-W4 modal differs from W5:", key, dict(agg), "| W5", e["landing_counts"])
print("   template arm (19 priority Y): modal is default", n_def, "associate", n_assoc)

section("Bench forecast experiment (exp13): gate, wins, mean log score minus uniform")
ev = jsonl(EXP13 / "results/c1_events.jsonl")
G = [e for e in ev if e["gate_pass"]]
print("gated", len(G), [e["task"] for e in G])
uni = {"T03": -1.630, "T06": -1.406, "T05": -1.119, "T10": -1.119, "T13": -3.140}  # Table 96 uniform column
for f in ("LADDER", "SUBTRACT", "PROXIMITY", "ASSOCIATE"):
    d = [e["logscore"][f] - uni[e["task"]] for e in G]
    print("  ", f, "mean minus uniform", round(sum(d) / len(d), 3))

section("Bench forecast experiment (exp13): merge intervals ban, programs labelled other")
rows = jsonl(EXP13 / "data/samples.jsonl")
t13 = [r for r in rows if r["condition"] == "ban" and r["task"] == "T13"]
print("T13 ban labels", dict(Counter(r["label"] for r in t13)))
cls = Counter()
for r in t13:
    if r["label"] != "other":
        continue
    code = r["code"] or ""
    if re.search(r"\[False\]\s*\*|covered\s*=|\[0\]\s*\*\s*\(", code):
        cls["coverage/point-marking array"] += 1
    elif re.search(r"current_end|last_end|merged\[-1\]", code):
        cls["sweep without sort"] += 1
    else:
        cls["misc"] += 1
print("T13 'other' rough classes (regex):", dict(cls), "passed", sum(bool(r["passed"]) for r in t13 if r["label"] == "other"))

section("Bench forecast experiment (exp13): knob view of the ban-free arms (rarefied Hill-1, depth 25, correct programs)")
for task in ("T03", "T04", "T05", "T06", "T08", "T10"):
    for cond in ("twin", "ban", "novelty", "rand1", "rand2", "rand3", "bandpatch"):
        R = [r for r in rows if r["task"] == task and r["condition"] == cond]
        default = Counter(r["label"] for r in rows if r["task"] == task and r["condition"] == "twin").most_common(1)[0][0]
        cor = [r["label"] for r in R if r["passed"] and r["label"] not in ("invalid", None)]
        if cond == "ban":
            cor = [x for x in cor if x != default]
        h = hill_rare(cor)
        if h and h >= 1.5:
            print(f"  {task} {cond}: pass {sum(bool(r['passed']) for r in R) / len(R):.2f} correct {dict(Counter(cor))} Hill-1 {h}")

section("Locus experiment (exp17): ADD and random-direction arms as knobs (rarefied Hill-1, depth 25)")
lab = jsonl(EXP17 / "data/labels.jsonl")
by = defaultdict(list)
for r in lab:
    by[(r["task"], r["arm"])].append(r)
ref = {t: sum(bool(r["passed"]) for r in by[(t, "NEUTRAL")]) / len(by[(t, "NEUTRAL")])
       for t in {r["task"] for r in lab} if by.get((t, "NEUTRAL"))}
for (t, a), R in sorted(by.items()):
    if not (a.startswith("ADD") or a.startswith("RAND")):
        continue
    cor = [r["label"] for r in R if r["passed"] and r["label"] not in ("invalid", None)]
    p = sum(bool(r["passed"]) for r in R) / len(R)
    att = [r for r in R if r["valid"] and r["label"] not in ("invalid", None)]
    avoid = sum(1 for r in att if not r["is_default"]) / len(att) if att else float("nan")
    h = hill_rare(cor)
    if (h and h >= 1.8) or a in ("RAND9001_a2.0", "RAND9002_a2.0", "RAND9003_a2.0", "ADD_a2.0"):
        print(f"  {t} {a}: n {len(R)} avoid {avoid:.2f} pass {p:.2f} (pts lost {100 * (ref[t] - p):.0f}) correct {dict(Counter(cor))} Hill-1 {h}")

section("Bench route experiment (exp16): route fractions and landing by route")
s = json.load(open(EXP16 / "results/shares.json"))
num = Counter()
for t in ("T03", "T10", "T05", "T06", "T13"):
    sa, sb, sc, sd, sk = (s[t][x]["s"] for x in ("a", "b", "c", "d", "K0"))
    print(f"  {t}: F_prompt {(sb - sc) / (sb - sa):.3f} F_direct {(sb - sd) / (sb - sa):.3f} F_K0 {(sb - sk) / (sb - sa):.3f}")
    for k, v in (("p", sb - sc), ("d", sb - sd), ("den", sb - sa)):
        num[k] += v
        if t != "T13":
            num[k + "_noT13"] += v
print(f"  pooled F_prompt {num['p'] / num['den']:.3f} F_direct {num['d'] / num['den']:.3f};"
      f" without merge intervals {num['p_noT13'] / num['den_noT13']:.3f} / {num['d_noT13'] / num['den_noT13']:.3f}")
lr = json.load(open(EXP16 / "results/landing_by_route.json"))
for t in ("T03", "T10", "T06", "T05", "T04"):
    print("  landing by route", t, {arm: v["counts"] for arm, v in lr[t].items()})

section("Llama bench (exp15): realised-hit definition, top-1 hits, exact Wilcoxon")
ev = jsonl(EXP15 / "results/c1_events.jsonl")
G = [e for e in ev if e["gate_pass"]]
hits, hits_no_other = Counter(), Counter()
for e in G:
    lc = {k: v for k, v in e["landing_counts"].items() if k != e["banned"]}
    modal = max(lc, key=lc.get)
    if modal != e["hit_label"]:
        print(f"  {e['event_id']}: modal landing {modal} ({lc[modal]}) but scored hit label {e['hit_label']} ({lc.get(e['hit_label'], 0)})")
    for f in ("SUBTRACT", "LADDER", "ASSOCIATE", "PROXIMITY"):
        if e["top1"].get(f) == e["hit_label"]:
            hits[f] += 1
            if e["hit_label"] != "other":
                hits_no_other[f] += 1
print("  hits", dict(hits), "| excluding 'other' as landing", dict(hits_no_other))
print("  exact binomial P(X>=7 | n=13, p=0.27) =", round(sum(math.comb(13, i) * 0.27 ** i * 0.73 ** (13 - i) for i in range(7, 14)), 4),
      "; P(X>=6) =", round(sum(math.comb(13, i) * 0.27 ** i * 0.73 ** (13 - i) for i in range(6, 14)), 4))


def wilcoxon_two_sided(d):
    d = [x for x in d if abs(x) > 1e-12]
    n = len(d)
    order = sorted(range(n), key=lambda i: abs(d[i]))
    r = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and abs(abs(d[order[j + 1]]) - abs(d[order[i]])) < 1e-12:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2 + 1
        i = j + 1
    w = sum(r[i] for i in range(n) if d[i] > 0)
    sums = [sum(r[i] for i in range(n) if sg[i]) for sg in itertools.product([0, 1], repeat=n)]
    return min(1.0, 2 * min(sum(x >= w for x in sums), sum(x <= w for x in sums)) / len(sums))


GD = [e for e in G if e["disagreeing"]]
for a, b in (("SUBTRACT", "PROXIMITY"), ("LADDER", "PROXIMITY"), ("SUBTRACT", "ASSOCIATE"), ("LADDER", "ASSOCIATE")):
    d = [e["logscore"][a] - e["logscore"][b] for e in GD]
    print(f"  {a}-{b}: n {len(GD)} mean {sum(d) / len(d):.3f} exact two-sided p {wilcoxon_two_sided(d):.4f}")

section("Record audit (eval2): likelihood argmax hits, events vs distinct likelihood rows")
import csv  # noqa: E402

rows = list(csv.DictReader(open(EVAL2 / "tables/c1_argmax_vs_landing.csv")))
q = [r for r in rows if r["model"] == "Qwen/Qwen3-8B"]
print("  Qwen events", len(q), "gain hits", sum(r["hit_Gbar_neutral"] == "True" for r in q),
      "mass hits", sum(r["hit_mass"] == "True" for r in q))
distinct = {}
for r in q:
    distinct[(r["task"], r["banned"])] = r
print("  distinct (task, banned) likelihood rows", len(distinct), "mass hits", sum(r["hit_mass"] == "True" for r in distinct.values()),
      "modal rows", sum(r["ban_kind"] == "modal" for r in distinct.values()))
