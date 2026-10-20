#!/usr/bin/env python3
"""Independent re-derivation of the headline numbers from data/samples.jsonl (+ the committed forecasts), written
without importing the analysis code (stdlib + numpy only).  Compares against results/analysis.json and
results/c1_events.jsonl and runs two placebos:
  (1) task-shuffled ban landings for C1: each task's committed forecasts are scored against another task's ban
      landing (mapped by survivor position), over 500 random derangements -> family wins should collapse;
  (2) template-shuffled labels: a within-task permutation test of template heterogeneity in the banned share
      (chi-square statistic over the task x template table) on the real and on template-shuffled data.
Usage: python audit/rederive.py   (writes results/rederive.json)
"""

from __future__ import annotations

import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
PRIMARY = ["SUBTRACT", "LADDER", "ASSOCIATE", "PROXIMITY"]


def load_jsonl(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def smooth(p_raw, S):
    out = {}
    for k in S + ["other"]:
        base = p_raw.get(k, 0.0) if p_raw is not None else (1.0 / len(S) if k in S else 0.0)
        out[k] = 0.93 * base + 0.05 * (1.0 / len(S) if k in S else 0.0) + (0.02 if k == "other" else 0.0)
    return out


def mean_log(p, labels):
    return sum(math.log(p[x]) for x in labels) / len(labels) if labels else float("nan")


def js2(a: Counter, b: Counter, space):
    na, nb = sum(a.values()), sum(b.values())
    pa = {k: a.get(k, 0) / na for k in space}
    pb = {k: b.get(k, 0) / nb for k in space}
    m = {k: (pa[k] + pb[k]) / 2 for k in space}
    kl = lambda p: sum(p[k] * math.log2(p[k] / m[k]) for k in space if p[k] > 0)
    return 0.5 * kl(pa) + 0.5 * kl(pb)


def wins(events, fams, margin=0.10):
    w = {f: 0 for f in fams}
    for ls in events:
        for f in fams:
            if ls[f] - max(ls[g] for g in fams if g != f) >= margin:
                w[f] += 1
    return w


def main() -> None:
    rows = load_jsonl(ROOT / "data" / "samples.jsonl")
    fc = json.loads((ROOT / "predictions" / "forecasts.json").read_text())["tasks"]
    an = json.loads((ROOT / "results" / "analysis.json").read_text())
    ev_ref = {e["task"]: e for e in load_jsonl(ROOT / "results" / "c1_events.jsonl")}
    by = defaultdict(list)
    for r in rows:
        by[(r["condition"], r["task"])].append(r)
    mism = []
    out = {"tasks": {}}
    events = []
    for t, F in fc.items():
        D, S = F["D"], F["S"]
        ban = by.get(("ban", t), [])
        if not ban:
            continue
        att = [r for r in ban if r["label"] != "invalid"]
        nb = [(r["label"] if r["label"] in S else "other") for r in att if r["label"] != D]
        avoid = len(nb) / len(att) if att else 0.0
        gate = avoid >= 0.5 and len(nb) >= 20
        ls = {f: mean_log(smooth(F["families"][f]["p_raw"], S), nb) if nb else None for f in
              PRIMARY + ["SUBTRACT_1SHOT", "FRLP_FP8", "UNIFORM"]}
        land = Counter(nb)
        ref = ev_ref.get(t)
        rec = {"avoidance": avoid, "gate": gate, "landing": dict(land), "logscore": ls}
        if ref:
            if abs((ref["avoidance"] or 0) - avoid) > 1e-9:
                mism.append(f"{t}: avoidance {ref['avoidance']} vs {avoid}")
            if ref["gate_pass"] != gate:
                mism.append(f"{t}: gate {ref['gate_pass']} vs {gate}")
            if dict(Counter(ref["landing_counts"])) != dict(land):
                mism.append(f"{t}: landing {ref['landing_counts']} vs {dict(land)}")
            for f, v in ls.items():
                rv = ref["logscore"].get(f)
                if (v is None) != (rv is None) or (v is not None and abs(v - rv) > 1e-9):
                    mism.append(f"{t}: logscore {f} {rv} vs {v}")
        out["tasks"][t] = rec
        if gate and F["disagreeing"]:
            events.append((t, {f: ls[f] for f in PRIMARY}))
    w = wins([e[1] for e in events], PRIMARY)
    ref_w = an["c1"]["advance"]["wins"]
    if w != ref_w:
        mism.append(f"advance wins {ref_w} vs {w}")
    out["advance_wins"] = w
    out["n_gated_disagreeing"] = len(events)
    # C2b (one-shot): modal agreement and JS recomputed; null threshold taken from the analysis (random), and an
    # independent null with another seed checks the reproduce/elsewhere classification
    c2 = []
    for e in an["c2b"]["oneshot"]["events"]:
        if not e.get("eligible"):
            continue
        t = e["task"]
        F = fc[t]
        D, S = F["D"], F["S"]
        cv = set(F.get("co_veto", []))
        space = [s for s in S if s not in cv] + ["other"]
        mp = lambda l: l if l in S else "other"
        v = Counter(mp(r["label"]) for r in by[("oneshot", t)] if r["label"] not in ("invalid", D))
        v = Counter({k: c for k, c in v.items() if k in space})
        bt = defaultdict(list)
        for r in by[("ban", t)]:
            if r["label"] not in ("invalid", D) and mp(r["label"]) in space:
                bt[r["template"]].append(mp(r["label"]))
        b = Counter(x for xs in bt.values() for x in xs)
        mv = max(space, key=lambda k: (v.get(k, 0), -space.index(k)))
        mb = max(space, key=lambda k: (b.get(k, 0), -space.index(k)))
        js = js2(v, b, space)
        if (mv == mb) != e["agree"] or abs(js - e["js"]) > 1e-9:
            mism.append(f"C2b {t}: agree {e['agree']} vs {mv == mb}, js {e['js']} vs {js}")
        rng = random.Random(99)
        temps = sorted(w_ for w_, xs in bt.items() if xs)
        nv, nbn = sum(v.values()), sum(b.values())

        def pseudo(m):
            slots = [rng.choice(temps) for _ in range(5)]
            sizes = [m // 5] * 5
            for i in rng.sample(range(5), m % 5):
                sizes[i] += 1
            return Counter(rng.choice(bt[s]) for s, k in zip(slots, sizes) for _ in range(k))

        null = sorted(js2(pseudo(nv), pseudo(nbn), space) for _ in range(2000))
        p95 = null[int(0.95 * (len(null) - 1))]
        c2.append({"task": t, "agree": mv == mb, "js": js, "p95_independent": p95, "p95_analysis": e["null_p95"],
                   "reproduces_independent": (mv == mb) and js <= p95, "reproduces_analysis": e["reproduces"]})
    out["c2b_oneshot"] = c2
    # placebo 1: task-shuffled ban landings
    tasks = [t for t in out["tasks"] if out["tasks"][t]["gate"] and fc[t]["disagreeing"]]
    rng = random.Random(7)
    pw = Counter()
    n_perm = 0
    if len(tasks) >= 2:
        for _ in range(500):
            perm = tasks[:]
            while any(a == b for a, b in zip(perm, tasks)):
                rng.shuffle(perm)
            evs = []
            for t, src in zip(tasks, perm):
                S = fc[t]["S"]
                Ss = fc[src]["S"]
                lab = []
                for k, c in out["tasks"][src]["landing"].items():
                    if k == "other":
                        lab += ["other"] * c
                    else:
                        i = Ss.index(k)
                        lab += [S[i] if i < len(S) else "other"] * c
                evs.append({f: mean_log(smooth(fc[t]["families"][f]["p_raw"], S), lab) for f in PRIMARY})
            for f, x in wins(evs, PRIMARY).items():
                pw[f] += x
            n_perm += 1
    out["placebo_task_shuffled"] = {"n_permutations": n_perm, "mean_wins": {f: pw[f] / n_perm for f in PRIMARY}
                                    if n_perm else None, "observed_wins": w}
    # placebo 2: template heterogeneity permutation test (real vs template-shuffled)
    def chi(rows_):
        tab = defaultdict(lambda: [0, 0])
        for r in rows_:
            tab[(r["task"], r["template"])][0] += r["label"] == r["banned_default"]
            tab[(r["task"], r["template"])][1] += 1
        stat = 0.0
        for t in sorted({k[0] for k in tab}):
            cells = [v for k, v in tab.items() if k[0] == t]
            K, N = sum(c[0] for c in cells), sum(c[1] for c in cells)
            p = K / N
            if p in (0.0, 1.0):
                continue
            stat += sum((c[0] - c[1] * p) ** 2 / (c[1] * p * (1 - p)) for c in cells)
        return stat

    def perm_p(rows_, seed, n=500):
        r_ = random.Random(seed)
        obs = chi(rows_)
        by_t = defaultdict(list)
        for x in rows_:
            by_t[x["task"]].append(x)
        ge = 0
        for _ in range(n):
            sh = []
            for t, xs in by_t.items():
                ts = [x["template"] for x in xs]
                r_.shuffle(ts)
                sh += [dict(x, template=w_) for x, w_ in zip(xs, ts)]
            ge += chi(sh) >= obs - 1e-12
        return obs, (ge + 1) / (n + 1)

    ban_att = [r for r in rows if r["condition"] == "ban" and r["label"] != "invalid"]
    obs, p = perm_p(ban_att, 1)
    r2 = random.Random(3)
    shuffled = []
    by_t = defaultdict(list)
    for x in ban_att:
        by_t[x["task"]].append(x)
    for t, xs in by_t.items():
        ts = [x["template"] for x in xs]
        r2.shuffle(ts)
        shuffled += [dict(x, template=w_) for x, w_ in zip(xs, ts)]
    obs_s, p_s = perm_p(shuffled, 2)
    out["template_permutation_test"] = {"chi2_real": obs, "p_real": p, "chi2_placebo_shuffled": obs_s,
                                        "p_placebo_shuffled": p_s}
    out["mismatches"] = mism
    out["n_mismatches"] = len(mism)
    (ROOT / "results" / "rederive.json").write_text(json.dumps(out, indent=1))
    print(f"re-derivation: {len(mism)} mismatches; advance wins {w}; placebo mean wins "
          f"{out['placebo_task_shuffled']['mean_wins']}; template p real {p:.3f} / placebo {p_s:.3f}")


if __name__ == "__main__":
    main()
