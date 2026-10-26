#!/usr/bin/env python3
"""Second independent re-derivation (plain Python + numpy; no analysis/ code), from data/samples_raw.jsonl,
data/labels.jsonl and the committed predictions, of the headlines audit/rederive.py does not cover:
decomposition medians, the T10 targeted-vs-random C2c contrast (exact McNemar), the pooled within-task rho, the
template split-half reliability of y, and the novelty counts. Each test is also run on placebo input that must fail.
-> results/rederive_extra.json"""

import json
import math
import random
import statistics as st
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
MOV = ["T03", "T2", "T05", "T10", "T06", "T1"]
BAD = {"invalid", "disputed"}
rng = random.Random(2026)


def jl(p):
    return [json.loads(l) for l in open(p) if l.strip()]


raw = {f"{r['task']}|{r['template']}|{r['arm']}|{r['sample_id']}": r for r in jl(ROOT / "data/samples_raw.jsonl")}
lab = {l["key"]: l for l in jl(ROOT / "data/labels.jsonl")}
commit = json.loads((ROOT / "predictions/c2_commit.json").read_text())
cat = {t: set(v["modes"]) for t, v in commit["tasks"].items()}
dft = {t: v["default"] for t, v in commit["tasks"].items()}
cell = {}  # (task, arm, template, k) -> (off-default 0/1 or None, passed)
for k, l in lab.items():
    t, w, arm, sid = k.split("|")
    off = None if l["label"] in BAD else int(l["label"] in cat[t] and l["label"] != dft[t])
    cell[(t, arm, w, int(sid))] = (off, bool(l["passed"]), l["label"])
W = ["W1", "W2", "W3", "W4", "W5"]


def share(t, arm, ks):
    v = [cell[(t, arm, w, k)][0] for w in W for k in ks if (t, arm, w, k) in cell]
    v = [x for x in v if x is not None]
    return sum(v) / len(v) if v else float("nan")


def ranks(x):
    order = sorted(range(len(x)), key=lambda i: x[i])
    r = [0.0] * len(x)
    i = 0
    while i < len(x):
        j = i
        while j + 1 < len(x) and x[order[j + 1]] == x[order[i]]:
            j += 1
        for m in range(i, j + 1):
            r[order[m]] = (i + j) / 2 + 1
        i = j + 1
    return r


def corr(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    return float(np.corrcoef(a, b)[0, 1]) if a.std() > 0 and b.std() > 0 else 0.0


out = {}
# 1. decomposition medians (k 0-3)
dl = json.loads((ROOT / "predictions/decomp_list.json").read_text())["list"]
R = defaultdict(lambda: defaultdict(list))
plac = []
for t, lst in dl.items():
    for c in lst:
        s, a = c["seed"], c["alpha"]
        so, st_ = share(t, f"POP_d{s}_a{a}", range(4)), share(t, "TWIN", range(4))
        for fam in ("UPERP", "UP", "CLAMP"):
            sa = share(t, f"{fam}_d{s}_a{a}", range(4))
            if not math.isnan(sa) and so != st_:
                R[t][fam].append((sa - st_) / (so - st_))
        # placebo: swap POP and TWIN labels within each slot with p = 0.5 -> the escape itself must vanish
        d = []
        for w in W:
            for k in range(4):
                x, y = cell.get((t, f"POP_d{s}_a{a}", w, k)), cell.get((t, "TWIN", w, k))
                if x and y and x[0] is not None and y[0] is not None:
                    d.append((y[0] - x[0]) if rng.random() < 0.5 else (x[0] - y[0]))
        plac.append(sum(d) / len(d))
out["decomposition"] = {t: {f: round(st.median(v), 3) for f, v in fams.items()} for t, fams in R.items()}
out["decomposition_pooled"] = {f: round(st.median([x for t in R for x in R[t][f]]), 3) for f in ("UPERP", "UP", "CLAMP")}
real = [share(t, f"POP_d{c['seed']}_a{c['alpha']}", range(4)) - share(t, "TWIN", range(4)) for t, l in dl.items() for c in l]
out["decomposition_placebo"] = {"real_mean_escape_excess": round(sum(real) / len(real), 3),
                                "placebo_pop_twin_swapped_mean_excess": round(sum(plac) / len(plac), 3)}
# 2. T10 targeted (r, s = 0.5) vs random of the same magnitude: exact McNemar on CRN-paired flips
def mcnemar(t, a1, a2, swap=False):
    b = c = 0
    for w in W:
        for k in range(10):
            x, y = cell.get((t, a1, w, k)), cell.get((t, a2, w, k))
            if not x or not y:
                continue
            u, v = int(x[0] or 0), int(y[0] or 0)
            if swap and rng.random() < 0.5:
                u, v = v, u
            b += u and not v
            c += v and not u
    n = b + c
    p = min(1.0, 2 * sum(math.comb(n, i) for i in range(max(b, c), n + 1)) / 2 ** n) if n else 1.0
    return b, c, p
b, c, p = mcnemar("T10", "C2C_r_s0.5", "C2C_rand9304_s0.5")
pl = [mcnemar("T10", "C2C_r_s0.5", "C2C_rand9304_s0.5", swap=True)[2] for _ in range(1000)]
out["c2c_T10"] = {"share_targeted": round(share("T10", "C2C_r_s0.5", range(10)), 3),
                  "share_random": round(share("T10", "C2C_rand9304_s0.5", range(10)), 3),
                  "flips_targeted_only": b, "flips_random_only": c, "mcnemar_p": p,
                  "placebo_swapped_frac_p_below_0.05": sum(x < 0.05 for x in pl) / len(pl)}
# 3. pooled within-task rho(pi, y) and 4. template split-half reliability of y
X, Y, rel = [], [], {}
for t in MOV:
    seeds = list(range(9101, 9141))
    y = [st.mean([share(t, f"POP_d{s}_a{a}", (0, 1)) for a in ("1.0", "2.0")]) for s in seeds]
    pi = [commit["predictors"][t][str(s)]["pi"] for s in seeds]
    X.append([r / 40 for r in ranks(pi)])
    Y.append([r / 40 for r in ranks(y)])
    hA = [st.mean([o for a in ("1.0", "2.0") for w in ("W1", "W3", "W5") for k in (0, 1)
                   for o in [cell.get((t, f"POP_d{s}_a{a}", w, k), (None,))[0]] if o is not None] or [0]) for s in seeds]
    hB = [st.mean([o for a in ("1.0", "2.0") for w in ("W2", "W4") for k in (0, 1)
                   for o in [cell.get((t, f"POP_d{s}_a{a}", w, k), (None,))[0]] if o is not None] or [0]) for s in seeds]
    hBs = hB[:]
    rng.shuffle(hBs)
    rel[t] = {"split_half_rho": round(corr(ranks(hA), ranks(hB)), 3),
              "placebo_shuffled_rho": round(corr(ranks(hA), ranks(hBs)), 3)}
xs, ys = sum(X, []), sum(Y, [])
pl = []
for _ in range(200):
    Xs = []
    for xx in X:
        z = xx[:]
        rng.shuffle(z)
        Xs += z
    pl.append(corr(Xs, ys))
out["pooled_within_task_rho"] = {"rho": round(corr(xs, ys), 3), "placebo_pi_shuffled_mean": round(st.mean(pl), 3)}
out["y_reliability"] = rel
# 5. novelty counts
push = ("POP_", "UPERP_", "UP_", "CLAMP_", "C2C_", "SWEEP_")
corr_push = [v for (t, arm, w, k), v in cell.items() if arm.startswith(push) and v[1]]
out["novelty_counts"] = {"correct_push_programs": len(corr_push),
                         "correct_push_labelled_other": sum(v[2] == "other" for v in corr_push)}
(ROOT / "results/rederive_extra.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
