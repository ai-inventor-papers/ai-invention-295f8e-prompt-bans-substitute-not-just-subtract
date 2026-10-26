"""Independent re-derivation of the headline numbers from RAW files only (data/samples_*.jsonl, data/raw_*.jsonl,
data/llm_cache.jsonl, committed predictions/, inputs/exp9 los.json). Imports nothing from src/: own parsing,
own counting, own tests (scipy chi2_contingency / fisher_exact instead of the analysis code's permutation helpers).
Every statistical test is also run on placebo input (shuffled group or arm labels) and must fail there.
Writes results/verify_headlines.json."""

import json
import math
import random
import re
from collections import Counter
from pathlib import Path

import numpy as np
from scipy.stats import chi2_contingency, fisher_exact

ROOT = Path(__file__).resolve().parent.parent


def rows(name):
    p = ROOT / "data" / name
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


out = {}
# 1. veto exactness: banned id sequences in vetoed generations (scan raw token ids directly)
occ = 0
n_vetoed = 0
for f in ("raw_walk.jsonl", "raw_sham.jsonl", "raw_fixed_top5.jsonl"):
    for r in rows(f):
        ids, seqs = r["token_ids"], r.get("veto_seqs") or []
        if seqs:
            n_vetoed += 1
        s = "," + ",".join(map(str, ids)) + ","
        occ += sum(s.count("," + ",".join(map(str, q)) + ",") for q in seqs)
out["veto_occurrences"] = {"vetoed_generations": n_vetoed, "banned_sequence_occurrences": occ}

# 2. walk: last round of every step, stall rule recomputed from raw labels + the committed vetoed lists
walk = rows("samples_walk.jsonl")
masks = {(m["task"], m["step"], m["round"]): m["vetoed"] for m in
         (json.loads(p.read_text()) for p in (ROOT / "predictions").glob("walk_*_s*_r*.json"))}
wk = {}
for t in sorted({r["task"] for r in walk}):
    steps = sorted({r["step"] for r in walk if r["task"] == t})
    last_step = max(steps)
    last_round = max(r["round"] for r in walk if r["task"] == t and r["step"] == last_step)
    rr = [r for r in walk if r["task"] == t and r["step"] == last_step and r["round"] == last_round]
    vet = masks[(t, last_step, last_round)]
    valid = [r for r in rr if r["label"] != "invalid"]
    nonv = [r for r in valid if r["label"] not in vet]
    wk[t] = {"max_step": last_step, "vetoed_share": round(1 - len(nonv) / len(valid), 3) if valid else None,
             "nonvetoed_attempts": len(nonv), "stalled": len(nonv) < 20 or (len(valid) - len(nonv)) / max(1, len(valid)) > 0.5,
             "counts": dict(Counter(r["label"] for r in rr))}
out["walk_last_round"] = wk

# 3. sham: default share among valid programs
DEF = {"T1": "bfs", "T2": "dijkstra", "T03": "full_sort", "T04": "naive", "T06": "hash_set", "T10": "union_find"}
sham = rows("samples_sham.jsonl")
out["sham_default_share"] = {t: f"{sum(r['label'] == DEF[t] for r in sham if r['task'] == t)}/"
                                f"{sum(r['label'] != 'invalid' for r in sham if r['task'] == t)}"
                             for t in sorted({r["task"] for r in sham})}

# 4. C3 cells: will = share labelled S among valid programs of LOS(S); T2 Floyd from exp9
los = rows("samples_los.jsonl")
cells = []
for g in ("path", "bench"):
    p = ROOT / "predictions" / f"reach_forecasts_{g}.json"
    for t, v in json.loads(p.read_text())["tasks"].items():
        cells += [c for c in v["c3_cells"] if c["qualifies"]]
exp9 = json.loads((ROOT / "inputs" / "exp9" / "results" / "los.json").read_text())
c3 = {}
for c in cells:
    if c["task"] == "T2":
        c3[f"T2:{c['S']}"] = exp9[c["S"]]["will_attempted_share"]
    else:
        v = [r for r in los if r["task"] == c["task"] and r["condition"] == f"los:LOS({c['S']})" and r["label"] != "invalid"]
        c3[f"{c['task']}:{c['S']}"] = round(sum(r["label"] == c["S"] for r in v) / len(v), 3)
out["c3_will"] = c3
out["c3_verdict"] = "DISCONFIRMED" if any(w >= 0.30 for w in c3.values()) else (
    "CONFIRMED" if all(w <= 0.10 for w in c3.values()) else "MIXED")
fs = [r["label"] for r in los if r["task"] == "T03" and r["condition"] == "los:LOS(full_sort)"]
out["T03_LOS_full_sort"] = dict(Counter(fs))

# 5. two-step compliance = share of valid programs not labelled D or R2
two = rows("samples_two_step.jsonl")
ts = {}
for t in sorted({r["task"] for r in two}):
    rr = [r for r in two if r["task"] == t and r["label"] != "invalid"]
    ban = rr[0]["meta_banned"]
    ts[t] = round(sum(r["label"] not in ban for r in rr) / len(rr), 3)
out["two_step_compliance"] = ts

# 6. long-form: N, correct off-catalogue programs, claims of novelty parsed from the RAW judge responses
lf = rows("samples_longform.jsonl")
out["longform_N"] = len(lf)
allrows = walk + sham + los + two + lf + rows("samples_fixed_top5.jsonl")
out["correct_other_unique"] = len({(r["task"], r["code_sha256"]) for r in allrows if r["label"] == "other" and r["passed"]})
cache = rows("llm_cache.jsonl")
cl = [r for r in cache if r["key"].startswith("claimA|")]
nov = [bool(re.search(r'"claims_novelty"\s*:\s*true', r.get("text") or "", re.I)) for r in cl]
out["claims"] = {"raw_claimA_responses": len(cl), "claims_novelty_true": sum(nov),
                 "share": round(sum(nov) / len(nov), 3) if nov else None}
aud = [r for r in cache if r["key"].startswith("auditB|") or r["key"].startswith("auditA|")]
out["audit_raw_novel_verdicts"] = {k: sum(1 for r in aud if r["key"].startswith(k) and
                                          re.search(r'"class"\s*:\s*"NOVEL', r.get("text") or "", re.I))
                                   for k in ("auditA|", "auditB|")}
man = json.loads((ROOT / "results" / "manual_audit.json").read_text())["records"]
out["manual_final_classes"] = dict(Counter(v["final_class"] for v in man.values()))
out["spend_usd_from_raw_costs"] = round(sum(r.get("cost") or 0 for r in cache), 4)

# 7. tests + placebos
rng = np.random.default_rng(0)


def chi_p(groups):
    tab = np.array([[g.count("D"), g.count("R2")] for g in groups.values()])
    tab = tab[tab.sum(1) > 0]
    return float(chi2_contingency(tab)[1]) if tab.shape[0] >= 2 and (tab.sum(0) > 0).all() else None


grp = {}
for name in ("LOS(rabin_karp)", "LOS(builtin)", "LOS(z_algorithm)"):
    grp[name] = ["D" if r["label"] == "naive" else "R2" for r in los if r["task"] == "T04"
                 and r["condition"] == f"los:{name}" and r["label"] in ("naive", "kmp")]
grp["TWO"] = ["D" if r["label"] == "naive" else "R2" for r in two if r["task"] == "T04" and r["label"] in ("naive", "kmp")]
pooled = [x for v in grp.values() for x in v]
plac = []
for s in range(20):
    perm = list(rng.permutation(pooled))
    i, g2 = 0, {}
    for k, v in grp.items():
        g2[k] = perm[i:i + len(v)]
        i += len(v)
    plac.append(chi_p(g2))
out["list_independence_T04"] = {"chi2_asymptotic_p": chi_p(grp), "placebo_p_median": float(np.median(plac)),
                                "placebo_share_p_below_0.05": float(np.mean([p < 0.05 for p in plac]))}
# sham vs distinctive pass rate on T2 (valid programs): Fisher exact, placebo = shuffled arm labels
a = [r["passed"] for r in sham if r["task"] == "T2" and r["label"] != "invalid"]
b = [r["passed"] for r in walk if r["task"] == "T2" and r["step"] == 1 and r["round"] == 0 and r["label"] != "invalid"]
fp = fisher_exact([[sum(a), len(a) - sum(a)], [sum(b), len(b) - sum(b)]])[1]
pl = []
both = a + b
for s in range(20):
    perm = list(rng.permutation(both))
    x, y = perm[:len(a)], perm[len(a):]
    pl.append(fisher_exact([[sum(x), len(x) - sum(x)], [sum(y), len(y) - sum(y)]])[1])
out["T2_sham_vs_distinctive_pass"] = {"sham": f"{sum(a)}/{len(a)}", "distinctive": f"{sum(b)}/{len(b)}",
                                      "fisher_p": fp, "placebo_p_median": float(np.median(pl)),
                                      "placebo_share_p_below_0.05": float(np.mean([p < 0.05 for p in pl]))}


def js(c1, c2):
    n1, n2 = sum(c1.values()), sum(c2.values())
    s = 0.0
    for k in set(c1) | set(c2):
        p, q = c1.get(k, 0) / n1, c2.get(k, 0) / n2
        m = (p + q) / 2
        s += (0.5 * p * math.log2(p / m) if p else 0) + (0.5 * q * math.log2(q / m) if q else 0)
    return s


xa = [r["label"] for r in lf if r["task"] == "T2" and r["prompt_id"] == "LF1" and not r["thinking"] and r["engine_dtype"] == "bf16"]
xb = [r["label"] for r in lf if r["task"] == "T2" and r["prompt_id"] == "LF1" and not r["thinking"] and r["engine_dtype"] == "fp8"]
out["crosscheck_js_bits"] = round(js(Counter(xa), Counter(xb)), 4)
(ROOT / "results" / "verify_headlines.json").write_text(json.dumps(out, indent=1, default=str))
print(json.dumps(out, indent=1, default=str))
