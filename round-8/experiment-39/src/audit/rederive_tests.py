#!/usr/bin/env python3
"""Second independent re-derivation (stdlib only, own code; reads the raw jsonl rows, never the aggregated results):
the headline shares, the exact McNemar test (T10 fork d2 vs global T 2.0), the paired-bootstrap comparisons (B6 and
T10: best fork dose vs best comparator under the 5-point cost constraint), the HR count and the novelty count.
Every test is also run on placebo input (arm labels shuffled within slot; the twin used as the fork arm), where it must
fail. Writes results/rederive_tests.json."""

import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BAD = {"invalid", "no_code", "label_error", "extraction"}


def jl(rel):
    return [json.loads(l) for l in (ROOT / rel).read_text().splitlines() if l.strip()]


proto = json.loads((ROOT / "predictions" / "protocol.json").read_text())
CAT = {u: v["catalogue"] for u, v in proto["units"].items()}
DEF = {u: v["default"] for u, v in proto["units"].items()}
ADJ = json.loads((ROOT / "results" / "adjudicated_labels.json").read_text())
LAB = {r["sid"]: r for r in jl("data/labels.jsonl")}
LAB.update({r["sid"]: r for r in jl("data/continuation_labels.jsonl")})


def klass(unit, sid, label):
    if sid in ADJ:
        return ADJ[sid]
    if label is None or label in BAD:
        return "invalid"
    return label if label in CAT[unit] else "other"


cells = defaultdict(lambda: defaultdict(dict))        # unit -> arm -> slot -> (class, passed)
for r in jl("data/samples.jsonl"):
    if r.get("stage") not in ("S0", "S3") or r.get("slot") is None or r["arm"].endswith("_chk"):
        continue
    L = LAB[r["sid"]]
    c = klass(r["unit"], r["sid"], L.get("label"))
    cells[r["unit"]][r["arm"]][int(r["slot"])] = (c, bool(L.get("passed")) and c != "invalid")


def hill25(labels):
    """exp of the expected Shannon entropy of a random 25-subset (own hypergeometric sum)."""
    n = len(labels)
    if n < 25:
        return None
    h = 0.0
    for k in Counter(labels).values():
        for x in range(max(1, 25 - (n - k)), min(k, 25) + 1):
            h -= math.comb(k, x) * math.comb(n - k, 25 - x) / math.comb(n, 25) * (x / 25) * math.log(x / 25)
    return math.exp(h)


def mcnemar_greater(b, c):
    n = b + c
    return 1.0 if n == 0 else sum(math.comb(n, k) for k in range(b, n + 1)) / 2 ** n


def best_hill(unit, arms, idx, twin):
    """Best correct Hill-1 among `arms` whose pass cost vs the twin is <= 0.05 on the resampled slots; else twin."""
    tp = sum(twin[i][1] for i in idx) / len(idx)
    best = None
    for a in arms:
        rows = [a[i] for i in idx]
        if tp - sum(p for _, p in rows) / len(rows) > 0.05:
            continue
        h = hill25([c for c, p in rows if p])
        if h is not None and (best is None or h > best):
            best = h
    return best if best is not None else (hill25([twin[i][0] for i in idx if twin[i][1]]) or 1.0)


def boot(unit, fork_arms, comp_families, n_rep=1000, seed=7):
    d = cells[unit]
    twin = [d["A0"][s] for s in range(50)]
    fa = [[d[a][s] for s in range(50)] for a in fork_arms]
    fams = [[[d[a][s] for s in range(50)] for a in fam if a in d] for fam in comp_families]
    rnd = random.Random(seed)
    full = list(range(50))
    point = best_hill(unit, fa, full, twin) - max(best_hill(unit, f, full, twin) for f in fams)
    le0 = 0
    diffs = []
    for _ in range(n_rep):
        idx = [rnd.randrange(50) for _ in range(50)]
        x = best_hill(unit, fa, idx, twin) - max(best_hill(unit, f, idx, twin) for f in fams)
        diffs.append(x)
        le0 += x <= 0
    diffs.sort()
    return {"point_diff": point, "lb_97_5": diffs[int(0.025 * n_rep)], "p_one_sided": (le0 + 1) / (n_rep + 1)}


out = {}
# headline shares
sh = {}
for u, a in (("T10", "A0"), ("T10", "A1"), ("T10", "A2"), ("T10", "A3g"), ("T10", "A9"), ("T10", "A10"),
             ("B6", "A0"), ("B6", "A10"), ("B3", "A9"), ("B3", "A10"), ("G", "A10"), ("G", "A11")):
    rows = list(cells[u][a].values())
    sh[f"{u}|{a}"] = {"counts": dict(Counter(c for c, _ in rows)), "pass": sum(p for _, p in rows) / len(rows),
                      "hill25": hill25([c for c, p in rows if p])}
out["shares"] = sh

# exact McNemar on correct off-default flips, T10 A10 vs A3g, with within-slot shuffle placebo
A, G = cells["T10"]["A10"], cells["T10"]["A3g"]


def cod(x):
    return x[1] and x[0] not in (DEF["T10"], "other", "invalid")


b = sum(1 for s in A if cod(A[s]) and not cod(G[s]))
c = sum(1 for s in A if cod(G[s]) and not cod(A[s]))
rnd = random.Random(11)
ps = []
for _ in range(1000):
    bb = cc = 0
    for s in A:
        x, y = (A[s], G[s]) if rnd.random() < 0.5 else (G[s], A[s])
        bb += cod(x) and not cod(y)
        cc += cod(y) and not cod(x)
    ps.append(mcnemar_greater(bb, cc))
out["mcnemar_T10_A10_vs_A3g"] = {"b": b, "c": c, "p_one_sided": mcnemar_greater(b, c),
                                 "placebo_shuffled_frac_p_le_0.05": sum(p <= 0.05 for p in ps) / len(ps),
                                 "placebo_constant_A3g_vs_A3g_p": mcnemar_greater(0, 0)}

# paired bootstrap: best fork vs best comparator family (B6: global T, EDT; T10: global T, min-p, EDT, AdapT)
fams_b6 = [["A1", "A2", "A3g"], ["A5"]]
fams_t10 = [["A1", "A2", "A3g"], ["A4"], ["A5"], ["A6"]]
out["boot_B6"] = boot("B6", ["A9", "A10"], fams_b6)
out["boot_B6_placebo_twin_as_fork"] = boot("B6", ["A0"], fams_b6)
out["boot_T10"] = boot("T10", ["A9", "A10"], fams_t10)
out["boot_T10_placebo_twin_as_fork"] = boot("T10", ["A0"], fams_t10)

# HR: units where correct ideas reached by forced branches exceed those of every sampling knob
hr = defaultdict(set)
for r in jl("data/continuations.jsonl"):
    if r.get("arm") == "HR" or (r.get("arm") == "MAP" and r.get("k", 9) < 5):
        L = LAB.get(r["sid"])
        if L and L.get("passed"):
            c = klass(r["unit"], r["sid"], L.get("label"))
            if c != "invalid":
                hr[r["unit"]].add(c)
extra = {}
for u, ideas in hr.items():
    k = set()
    for a in ("A0", "A1", "A2", "A3g", "A4", "A5", "A6", "A7", "A8", "A9", "A10"):
        k |= {c for c, p in cells[u].get(a, {}).values() if p and c != "invalid"}
    extra[u] = sorted(ideas - k)
out["hr_extra_ideas"] = extra
out["hr_units_with_extra"] = sum(1 for v in extra.values() if v)

# novelty count: correct programs and correct 'other' after adjudication (manual reads relabel 2 as counting sort)
n_correct = sum(1 for L in LAB.values() if L.get("passed"))
other = [sid for sid, L in LAB.items() if L.get("passed") and L.get("labeller_source") != "oc_partial"
         and klass(L.get("unit") or sid.split("|")[0], sid, L.get("label")) == "other"]
out["novelty"] = {"n_correct_programs": n_correct, "n_correct_other_after_adjudication": len(other),
                  "rule_of_three_95": 3 / n_correct}
(ROOT / "results" / "rederive_tests.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
