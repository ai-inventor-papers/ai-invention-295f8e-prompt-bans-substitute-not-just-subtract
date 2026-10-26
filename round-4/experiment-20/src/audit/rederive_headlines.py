#!/usr/bin/env python3
"""Second, independent re-derivation of the headline numbers NOT covered by audit/rederive.py.
Reads only raw files (data/samples_raw.jsonl, data/labels.jsonl, data/labels_k7.jsonl, data/row_logs.jsonl,
inputs/exp17/data/labels.jsonl) and uses different methods from src/analysis.py:
  H2 inert sites: correct off-default counts at S1/S2 (and S5) over alpha 1/2/4;
  H3 matched-dose S0 effect: Mantel-Haenszel common odds ratio (strata = task x quintile of log displacement at R),
     computed by hand (analysis.py fits a logit) + placebo: S0 labels shuffled within task;
  H4 paired flips: exact McNemar by hand for S0 vs S1 at alpha 2 + placebo: within-pair labels randomly swapped;
  H5 alpha 8 pass rates; H6 correct-program and correct-'other' counts; H7 TOP5 avoidance from K=7 labels;
  H8 engine check: byte identity of the first ```python block (own regex) vs exp17's screen code;
  H1 binomial p of the C1 count, by hand.
Writes results/rederive_headlines.json."""

import json
import math
import random
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEF = {"T1": "bfs", "T2": "dijkstra", "T03": "full_sort", "T05": "hash_map", "T06": "hash_set", "T10": "union_find"}
TASKS = list(DEF)
BAD = {"invalid", "unresolved", "disputed"}


def jl(p):
    return [json.loads(l) for l in Path(p).read_text().splitlines() if l.strip()]


raw = jl(ROOT / "data/samples_raw.jsonl")
lab = {r["key"]: r for r in jl(ROOT / "data/labels.jsonl")}
k7 = {r["key"]: r for r in jl(ROOT / "data/labels_k7.jsonl")}
logs = {r["key"]: r for r in jl(ROOT / "data/row_logs.jsonl")}
rows = []
for r in raw:
    if r["arm"].startswith("SMOKE_") or r["arm"] == "TWIN_X":
        continue
    key = f"{r['task']}|{r['template']}|{r['arm']}|{r['k']}"
    L = lab[key]
    code = L.get("code") or ""
    has_solve = bool(re.search(r"^\s*def solve\s*\(", code, re.M))  # different test from analysis' ast walk
    label = L["label"] if (L["label"] in BAD or has_solve) else "invalid"
    site, alpha = ("TWIN", 0.0) if r["arm"] == "TWIN" else (r["arm"].rsplit("_a", 1)[0], float(r["arm"].rsplit("_a", 1)[1]))
    rows.append({"key": key, "task": r["task"], "w": r["template"], "k": r["k"], "site": site, "alpha": alpha,
                 "label": label, "passed": bool(L["passed"]), "text": r["text"],
                 "d35": (logs.get(key, {}).get("realised_disp_R") or {}).get("35")})
out = {}

# H2 inert sites
inert = {}
for s in ("S1", "S2", "S5"):
    c = [r for r in rows if r["site"] == s and r["alpha"] in (1.0, 2.0, 4.0) and r["k"] < 6 and r["passed"]
         and r["label"] not in BAD]
    inert[s] = {"n_correct": len(c), "n_off_default": sum(r["label"] != DEF[r["task"]] for r in c),
                "off_by_task": dict(Counter(r["task"] for r in c if r["label"] != DEF[r["task"]]))}
out["H2_inert_sites"] = inert

# H3 Mantel-Haenszel odds ratio, S0 vs other prefill sites, strata = task x quintile of log d35
pre = [r for r in rows if r["site"] in ("S0", "S1", "S2", "S4", "S5", "S1E", "S2E") and r["alpha"] in (1.0, 2.0, 4.0)
       and r["k"] < 6 and r["passed"] and r["label"] not in BAD and r["d35"]]


def mh(data, flag):
    by = defaultdict(list)
    for r in data:
        by[r["task"]].append(r)
    num = den = 0.0
    P = Q = R_ = S_ = 0.0  # Robins-Breslow-Greenland variance terms
    for t, rs in by.items():
        ds = sorted(math.log(r["d35"]) for r in rs)
        cuts = [ds[int(len(ds) * q / 5)] for q in range(1, 5)]
        strata = defaultdict(list)
        for r in rs:
            strata[sum(math.log(r["d35"]) > c for c in cuts)].append(r)
        for g in strata.values():
            a = sum(1 for r in g if flag(r) and r["label"] != DEF[r["task"]])
            b = sum(1 for r in g if flag(r) and r["label"] == DEF[r["task"]])
            c = sum(1 for r in g if not flag(r) and r["label"] != DEF[r["task"]])
            d = sum(1 for r in g if not flag(r) and r["label"] == DEF[r["task"]])
            n = a + b + c + d
            if n == 0:
                continue
            num += a * d / n
            den += b * c / n
            P += (a + d) / n * a * d / n
            Q += ((a + d) / n * b * c / n + (b + c) / n * a * d / n)
            R_ += (b + c) / n * b * c / n
            S_ += 0
    if den == 0 or num == 0:
        return {"OR": None}
    orr = num / den
    var = P / (2 * num ** 2) + Q / (2 * num * den) + R_ / (2 * den ** 2)
    se = math.sqrt(var)
    return {"OR": orr, "log_OR": math.log(orr), "ci95": [math.exp(math.log(orr) - 1.96 * se),
                                                         math.exp(math.log(orr) + 1.96 * se)]}


out["H3_mantel_haenszel"] = {"n": len(pre), **mh(pre, lambda r: r["site"] == "S0")}
rng = random.Random(0)
plac = []
for rep in range(200):
    shuf = []
    by = defaultdict(list)
    for r in pre:
        by[r["task"]].append(r)
    for t, rs in by.items():
        flags = [r["site"] == "S0" for r in rs]
        rng.shuffle(flags)
        shuf += [dict(r, _f=f) for r, f in zip(rs, flags)]
    m = mh(shuf, lambda r: r["_f"])
    plac.append(m)
excl = [m for m in plac if m["OR"] and not (m["ci95"][0] <= 1 <= m["ci95"][1])]
out["H3_placebo_S0_shuffled_within_task"] = {"replicates": len(plac), "share_CI_excluding_1": len(excl) / len(plac),
                                             "median_OR": sorted(m["OR"] for m in plac if m["OR"])[len(plac) // 2]}


# H4 exact McNemar by hand, S0 vs S1 at alpha 2, per task + placebo (random within-pair swap)
def mcnemar(b, c):
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


idx = {(r["task"], r["w"], r["k"], r["site"], r["alpha"]): r for r in rows}
mc, mc_plac = {}, []
for t in TASKS:
    pairs = []
    for w in ["W1", "W2", "W3", "W4", "W5"]:
        for k in range(6):
            a, b = idx.get((t, w, k, "S0", 2.0)), idx.get((t, w, k, "S1", 2.0))
            if a and b and a["label"] not in BAD and b["label"] not in BAD:
                pairs.append((a["label"] != DEF[t], b["label"] != DEF[t]))
    bb = sum(1 for x, y in pairs if x and not y)
    cc = sum(1 for x, y in pairs if y and not x)
    mc[t] = {"S0_only": bb, "S1_only": cc, "p": mcnemar(bb, cc)}
    for rep in range(200):
        sw = [(y, x) if rng.random() < 0.5 else (x, y) for x, y in pairs]
        b2 = sum(1 for x, y in sw if x and not y)
        c2 = sum(1 for x, y in sw if y and not x)
        mc_plac.append(mcnemar(b2, c2))
out["H4_mcnemar_S0_vs_S1_alpha2"] = mc
out["H4_placebo_random_swap"] = {"n_tests": len(mc_plac), "share_p_lt_0.05": sum(p < 0.05 for p in mc_plac) /
                                 len(mc_plac)}

# H5 alpha 8 pass rates; H6 counts
out["H5_alpha8_pass"] = {t: sum(r["passed"] for r in rows if r["task"] == t and r["site"] == "S0" and
                                r["alpha"] == 8.0) / max(1, sum(1 for r in rows if r["task"] == t and
                                                               r["site"] == "S0" and r["alpha"] == 8.0))
                         for t in TASKS}
cor = [r for r in rows if r["passed"] and r["label"] not in BAD]
out["H6_counts"] = {"n_correct_programs": len(cor), "n_correct_other": sum(r["label"] == "other" for r in cor)}

# H7 TOP5 avoidance from the K=7 labels
top5 = {"bfs", "dfs", "gbfs", "iddfs", "astar"}
h7 = {}
for a in ("1", "2", "4"):
    ks = [k7[r["key"]] for r in rows if r["task"] == "T1" and r["site"] == "TOP5" and r["alpha"] == float(a)]
    c = [x for x in ks if x["passed"] and x["label_k7"] != "invalid"]
    h7[f"TOP5_a{a}"] = {"n_correct": len(c), "avoidance": (sum(x["label_k7"] not in top5 for x in c) / len(c))
                        if c else None, "labels": dict(Counter(x["label_k7"] for x in c))}
out["H7_top5"] = h7

# H8 engine check: own code-block extraction vs exp17 screen code
scr = {(r["task"], r["template"], r["arm"], int(r["sample_id"])): r for r in jl(ROOT / "inputs/exp17/data/labels.jsonl")}
h8 = {}
for t, arm, sarm in (("T03", "ENG_r9002_a1", "RAND9002_a1.0"), ("T2", "ENG_r9004_a1", "RAND9004_a1.0")):
    same = n = 0
    for r in raw:
        if r["task"] == t and r["arm"] == arm:
            m = re.search(r"```(?:python)?\n(.*?)```", r["text"], re.S)
            ours = m.group(1) if m else None
            s = scr.get((t, r["template"], sarm, int(r["k"])))
            if s is None:
                continue
            n += 1
            same += ours is not None and s.get("code") is not None and ours.strip() == s["code"].strip()
    h8[t] = {"n": n, "identical_code": same}
out["H8_engine_check"] = h8

# H1 binomial tail of the C1 count (3 of 6 under p = 1/6), by hand
cnt = json.loads((ROOT / "results/c1_site.json").read_text())["count_S0_best"]
out["H1_binomial_p"] = {"count": cnt, "p": sum(math.comb(6, j) * (1 / 6) ** j * (5 / 6) ** (6 - j)
                                               for j in range(cnt, 7))}
(ROOT / "results/rederive_headlines.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1)[:3500])
