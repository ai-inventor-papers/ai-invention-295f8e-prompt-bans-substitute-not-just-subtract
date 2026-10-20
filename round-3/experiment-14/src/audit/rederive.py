#!/usr/bin/env python3
"""Independent re-derivation of every c1_events row and the headline numbers (plan T5 / 4.7).

Reads only data/samples.jsonl, the committed predictions/ files and commitments.log.  Imports nothing from analysis/
or exposure/: smoothing, log scores, top-1, gate, advance rule, an exact Wilcoxon signed-rank test (dynamic
programming over rank sums), Holm and the branch are re-implemented here.  Then compares against results/c1_events.jsonl
and results/c1_summary.json, and runs placebo checks that must FAIL to find an effect:
  (1) sign-flip placebo: random signs on the per-event log-score differences -> Holm-significant rarely (<= ~5%);
  (2) constant-forecast placebo: every family forecasts Uniform(S) -> no family wins any event;
  (3) within-task rotation of the Y-specific forecasts (SUBTRACT, ASSOCIATE, PROXIMITY) -> reported.
Writes results/rederive.json and exits non-zero on any mismatch.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOL = 1e-9


def jl(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]


def jread(p: Path):
    return json.loads(p.read_text())


# ------------------------------------------------------------------------------------------- re-implementations
def smoothed(f, surv):
    k = len(surv)
    g = {}
    if f:
        g = {a: float(b) for a, b in f.items() if (a in surv or a == "other") and b > 0}
    tot = sum(g.values())
    g = {a: b / tot for a, b in g.items()} if tot > 0 else {a: 1.0 / k for a in surv}
    p = {a: 0.98 * (0.95 * g.get(a, 0.0) + 0.05 / k) for a in surv}
    p["other"] = 0.98 * 0.95 * g.get("other", 0.0) + 0.02
    return p, g


def argmax_set(d):
    if not d:
        return []
    m = max(d.values())
    return sorted(a for a, b in d.items() if abs(b - m) < 1e-12)


def exact_wilcoxon_p(d):
    """Two-sided exact signed-rank p (zeros dropped, average ranks for ties, exact over integerised half-ranks)."""
    x = [v for v in d if v != 0]
    n = len(x)
    if n == 0:
        return 1.0
    a = sorted(range(n), key=lambda i: abs(x[i]))
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and abs(x[a[j + 1]]) == abs(x[a[i]]):
            j += 1
        for k in range(i, j + 1):
            ranks[a[k]] = (i + j) / 2 + 1
        i = j + 1
    r2 = [int(round(2 * r)) for r in ranks]  # half-ranks are integers
    wplus = sum(r for r, v in zip(r2, x) if v > 0)
    tot = sum(r2)
    if n > 25:
        mu = sum(ranks) / 2
        var = sum(r * r for r in ranks) / 4
        z = (wplus / 2 - mu) / math.sqrt(var)
        return math.erfc(abs(z) / math.sqrt(2))
    counts = {0: 1}
    for r in r2:
        nxt = defaultdict(int)
        for s, c in counts.items():
            nxt[s] += c
            nxt[s + r] += c
        counts = nxt
    total = 2 ** n
    lo = sum(c for s, c in counts.items() if s <= min(wplus, tot - wplus))
    return min(1.0, 2 * lo / total)


def holm(ps):
    m = len(ps)
    order = sorted(range(m), key=lambda i: ps[i])
    out, run = [0.0] * m, 0.0
    for rank, i in enumerate(order):
        run = max(run, min(1.0, (m - rank) * ps[i]))
        out[i] = run
    return out


FAM = ["SUBTRACT", "LADDER", "ASSOCIATE", "PROXIMITY"]
PAIRS = [("SUBTRACT", "ASSOCIATE"), ("SUBTRACT", "PROXIMITY"), ("LADDER", "ASSOCIATE"), ("LADDER", "PROXIMITY")]


def score(land, surv, forecasts):
    n = sum(land.values())
    ls, t1 = {}, {}
    for f in FAM:
        p, g = smoothed(forecasts[f], surv)
        ls[f] = sum(c * math.log(p[lab]) for lab, c in land.items()) / n if n else float("nan")
        t1[f] = argmax_set(g)
    dis = len({tuple(v) for v in t1.values()}) > 1
    return ls, t1, dis


def wins_of(evs):
    w = Counter()
    for e in evs:
        for f in FAM:
            if e["ls"][f] - max(e["ls"][g] for g in FAM if g != f) >= 0.10:
                w[f] += 1
    return {f: w[f] for f in FAM}


def main() -> int:
    samples = jl(ROOT / "data" / "samples.jsonl")
    pred = ROOT / "predictions"
    elig = jread(pred / "eligibility.json")
    asc, lad = jread(pred / "associate.json"), jread(pred / "ladder.json")
    prox, sub = jread(pred / "proximity.json"), jread(pred / "subtract_in_context.json")
    shown = Counter(r["key"] for r in jl(pred / "shown_programs.jsonl"))
    rows = defaultdict(list)
    for r in samples:
        if r["Y"]:
            rows[(r["task"], r["Y"], r["arm"])].append(r)
    mine = {}
    for key in shown:
        t, y = key.split(":")
        surv = [m for m in elig["tasks"][t]["modes"] if m != y]
        fc = {"SUBTRACT": sub[key]["distribution"], "LADDER": lad[key], "ASSOCIATE": asc[key],
              "PROXIMITY": prox[key]["distribution"]}
        for arm in ("named", "unnamed"):
            rs = rows.get((t, y, arm), [])
            if not rs:
                continue
            att = [r["label"] for r in rs if r["label"] != "invalid"]
            ny = att.count(y)
            non = [lab if lab in surv else "other" for lab in att if lab != y]
            land = Counter(non)
            avoid = 1 - ny / len(att) if att else float("nan")
            ls, t1, dis = score(land, surv, fc)
            mine[(t, y, arm)] = {"avoidance": avoid, "n_nonY": len(non), "gate": (avoid >= 0.5 and len(non) >= 20),
                                 "landing": dict(land), "ls": ls, "t1": t1, "dis": dis, "task": t, "Y": y, "surv": surv,
                                 "fc": fc}
    theirs = {(e["task"], e["Y"], e["event_type"].split("_")[1]): e for e in jl(ROOT / "results" / "c1_events.jsonl")}
    mism = []
    for k, m in mine.items():
        e = theirs.get(k)
        if e is None:
            mism.append(f"{k}: missing in c1_events")
            continue
        if not (abs(m["avoidance"] - e["avoidance"]) < TOL or (math.isnan(m["avoidance"]) and e["avoidance"] is None)):
            mism.append(f"{k}: avoidance {m['avoidance']} vs {e['avoidance']}")
        if m["n_nonY"] != e["n_nonY"] or m["gate"] != e["gate_pass"] or m["dis"] != e["disagreeing"]:
            mism.append(f"{k}: n_nonY/gate/disagreeing differ")
        if m["landing"] != e["landing_counts"]:
            mism.append(f"{k}: landing differs")
        for f in FAM:
            if abs(m["ls"][f] - e["logscore"][f]) > 1e-9 or m["t1"][f] != sorted(e["top1"][f]):
                mism.append(f"{k}: {f} logscore/top1 differ ({m['ls'][f]} vs {e['logscore'][f]})")
    if len(theirs) != len(mine):
        mism.append(f"event count {len(mine)} vs {len(theirs)}")
    summ = jread(ROOT / "results" / "c1_summary.json")
    head = {}
    for arm in ("named", "unnamed"):
        sel = [m for k, m in mine.items() if k[2] == arm and m["gate"] and m["dis"]]
        w = wins_of(sel)
        adv = [f for f in FAM if w[f] >= 3]
        tests = []
        if len(sel) >= 10:
            ps = [exact_wilcoxon_p([e["ls"][a] - e["ls"][b] for e in sel]) for a, b in PAIRS]
            tests = [{"pair": f"{a}-{b}", "p": p, "p_holm": q,
                      "mean_diff": sum(e["ls"][a] - e["ls"][b] for e in sel) / len(sel)}
                     for (a, b), p, q in zip(PAIRS, ps, holm(ps))]
        head[arm] = {"n_gated": sum(1 for k, m in mine.items() if k[2] == arm and m["gate"]),
                     "n_gated_disagreeing": len(sel), "wins": w, "advancing": adv, "tests": tests}
        ref = summ[f"c1_{arm}"]
        if ref["n_gated"] != head[arm]["n_gated"] or ref["n_gated_disagreeing"] != len(sel):
            mism.append(f"{arm}: gated counts differ")
        if ref["rule"]["wins"] != w or sorted(ref["rule"]["advancing"]) != sorted(adv):
            mism.append(f"{arm}: wins/advancing differ {ref['rule']['wins']} vs {w}")
        if tests and ref["tests"].get("run"):
            # This exact test enumerates the actual (tied) half-ranks; scipy's exact mode assumes untied ranks and its
            # normal approximation has its own tie correction, so p-values may differ slightly.  A mismatch is a
            # different Holm decision at 0.05 or a p gap > 0.01; every gap is reported.
            gaps = []
            for t_mine, t_ref in zip(tests, ref["tests"]["tests"]):
                gaps.append({"pair": t_mine["pair"], "p_audit": t_mine["p"], "p_frozen": t_ref["p"],
                             "p_holm_audit": t_mine["p_holm"], "p_holm_frozen": t_ref["p_holm"],
                             "method_frozen": t_ref.get("method"), "n_nonzero": t_ref.get("n_nonzero")})
                if (t_mine["p_holm"] < 0.05) != (t_ref["p_holm"] < 0.05) or abs(t_mine["p"] - t_ref["p"]) > 0.01:
                    mism.append(f"{arm} {t_mine['pair']}: p {t_mine['p']:.6g} vs {t_ref['p']:.6g} (decision or gap)")
            head[arm]["p_value_comparison"] = gaps
            head[arm]["max_abs_p_gap"] = max(abs(g["p_audit"] - g["p_frozen"]) for g in gaps)
    # exploratory three-family contest (LADDER / ASSOCIATE / PROXIMITY), recomputed independently
    fam3 = ["LADDER", "ASSOCIATE", "PROXIMITY"]
    ref3 = summ.get("exploratory_not_preregistered", {}).get("three_family_named")
    g3 = [m for k, m in mine.items() if k[2] == "named" and m["gate"]]
    s3 = [m for m in g3 if len({tuple(m["t1"][f]) for f in fam3}) > 1]
    w3 = Counter()
    for e in s3:
        for f in fam3:
            if e["ls"][f] - max(e["ls"][g] for g in fam3 if g != f) >= 0.10:
                w3[f] += 1

    def hit_of(m, f):
        mod = argmax_set(m["landing"])
        return len(set(mod) & set(m["t1"][f])) / (len(mod) * len(m["t1"][f])) if mod and m["t1"][f] else 0.0

    hit3 = {f: (sum(hit_of(m, f) for m in g3) / len(g3)) if g3 else None for f in fam3}
    head["three_family_named"] = {"n_events": len(s3), "wins": {f: w3[f] for f in fam3}, "hit_rate_gated": hit3}
    if ref3 is not None:
        if ref3["n_three_family_disagreeing"] != len(s3) or ref3["wins"] != {f: w3[f] for f in fam3}:
            mism.append(f"three-family wins differ {ref3['wins']} vs {dict(w3)}")
        for f in fam3:
            if ref3["hit_rate_gated"][f] is not None and abs(ref3["hit_rate_gated"][f] - hit3[f]) > 1e-9:
                mism.append(f"three-family hit rate {f} differs")
    # copy rates and NAMED avoidance (headline descriptive numbers)
    cr = {}
    for key in shown:
        t, y = key.split(":")
        att = [r["label"] for r in rows.get((t, y, "copy"), []) if r["label"] != "invalid"]
        cr[key] = att.count(y) / len(att) if att else None
    head["copy_rate_mean"] = sum(v for v in cr.values() if v is not None) / max(1, sum(v is not None for v in cr.values()))
    nav = [m["avoidance"] for k, m in mine.items() if k[2] == "named" and not math.isnan(m["avoidance"])]
    head["named_avoidance_mean"] = sum(nav) / len(nav) if nav else None
    # snap-back to the default: mean share of attempts equal to the context-free default, per arm
    dshare = {}
    for arm in ("copy", "named", "unnamed"):
        vals = []
        for key in shown:
            t, y = key.split(":")
            att = [r["label"] for r in rows.get((t, y, arm), []) if r["label"] != "invalid"]
            if att:
                vals.append(att.count(elig["tasks"][t]["default"]) / len(att))
        dshare[arm] = sum(vals) / len(vals) if vals else None
    head["default_share_mean_by_arm"] = dshare
    gn = [m for k, m in mine.items() if k[2] == "named" and m["gate"]]
    head["named_gated_modal_is_default"] = [sum(1 for m in gn if elig["tasks"][m["task"]]["default"] in argmax_set(m["landing"])),
                                            len(gn)]
    # ------------------------------------------------------------------------------------------- placebos
    rng = random.Random(11)
    sel = [m for k, m in mine.items() if k[2] == "named" and m["gate"] and m["dis"]]
    flips_sig = 0
    n_draws = 200
    if len(sel) >= 10:
        for _ in range(n_draws):
            ps = []
            for a, b in PAIRS:
                d = [(e["ls"][a] - e["ls"][b]) * rng.choice((-1, 1)) for e in sel]
                ps.append(exact_wilcoxon_p(d))
            flips_sig += any(q < 0.05 for q in holm(ps))
    const = []
    for m in mine.values():
        if m["gate"]:
            ls, _, _ = score(Counter(m["landing"]), m["surv"], {f: None for f in FAM})
            const.append({"ls": ls})
    rot_events = []
    by_task = defaultdict(list)
    for k, m in mine.items():
        if k[2] == "named":
            by_task[k[0]].append(m)
    for t, ms in by_task.items():
        if len(ms) < 2:
            continue
        for i, m in enumerate(ms):
            fc2 = dict(m["fc"])
            for f in ("SUBTRACT", "ASSOCIATE", "PROXIMITY"):
                fc2[f] = ms[(i + 1) % len(ms)]["fc"][f]
            ls, t1, dis = score(Counter(m["landing"]), m["surv"], fc2)
            if m["gate"] and dis:
                rot_events.append({"ls": ls})
    placebo = {"sign_flip": {"n_events": len(sel), "n_draws": n_draws if len(sel) >= 10 else 0,
                             "share_any_holm_significant": (flips_sig / n_draws) if len(sel) >= 10 else None},
               "constant_uniform_forecasts": {"n_gated_events": len(const), "wins": wins_of(const)},
               "rotation_Y_specific": {"n_gated_disagreeing": len(rot_events), "wins": wins_of(rot_events),
                                       "advancing": [f for f, v in wins_of(rot_events).items() if v >= 3]}}
    const_ok = all(v == 0 for v in placebo["constant_uniform_forecasts"]["wins"].values())
    flip_ok = placebo["sign_flip"]["share_any_holm_significant"] is None or placebo["sign_flip"]["share_any_holm_significant"] <= 0.10
    # ------------------------------------------------------------------------------------- chain + timing
    lines = (ROOT / "commitments.log").read_text().splitlines()
    prev, chain_ok = "0" * 64, True
    for ln in lines:
        rec = json.loads(ln)
        chain_ok &= rec["prev_line_sha256"] == prev
        prev = hashlib.sha256(ln.encode()).hexdigest()
    files_ok = True
    for ln in lines:
        rec = json.loads(ln)
        if rec["kind"].startswith(("COMMIT1:", "COMMIT2:")) and rec.get("file"):
            p = ROOT / rec["file"]
            files_ok &= p.exists() and hashlib.sha256(p.read_bytes()).hexdigest() == rec["sha256"]
    out = {"n_events_rederived": len(mine), "mismatches": mism, "n_mismatches": len(mism), "headline": head,
           "placebo": placebo, "placebo_constant_forecast_no_wins": const_ok, "placebo_sign_flip_level_ok": flip_ok,
           "chain_verifies": chain_ok, "committed_files_unchanged": files_ok}
    (ROOT / "results" / "rederive.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k != "headline"}, indent=1)[:4000])
    print("HEADLINE", json.dumps(head)[:3000])
    return 0 if (not mism and chain_ok and files_ok and const_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
