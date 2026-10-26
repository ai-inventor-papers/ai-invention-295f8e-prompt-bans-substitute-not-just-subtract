#!/usr/bin/env python3
"""Independent re-derivation of the headline numbers from data/samples.jsonl + data/reused_rows.jsonl, with code that
shares nothing with src/analysis: its own hull (numpy multinomial draws with a fresh generator, lambda step 0.01 on
every edge, cost <= 5 boundary handled by clipping the grid), its own C1 counts and its own JSD. Placebos: (1) arm
labels shuffled within a task (100 shuffles; the counts rule count1 >= 3 AND count2 >= 4 must fire in < 5% of them);
(2) every PN setting replaced by the TWIN rows: D_t <= 0 on every task. Hash chain: every commitments.log line
re-hashed; every commit before the first row beyond stage 10.

Usage: python audit/rederive.py   (writes results/rederive.json)
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
E6 = ["T03", "T05", "T06", "T10", "T1", "T2"]
NA = {"TEMP": ["T1.3", "T1.6"], "TOPK10": ["TOPK10"], "NONCE": ["NONCE"], "NOVELTY": ["NOVELTY"],
      "SEMSEED": ["SEMSEED"], "VETO_1SHOT": ["VETO_1SHOT"], "VETO_PERSIST": ["VETO_PERSIST"],
      "VETO_ITER": ["VETO_ITER1", "VETO_ITER2", "VETO_ITER3"]}
PN = ["PN_a0.5", "PN_a1", "PN_a2", "PN_a4"]


def jl(p):
    with open(p) as f:
        return [json.loads(l) for l in f if l.strip()]


def mapped(r, omap):
    if r["label"] == "other" and omap is not None:
        m = omap.get(r.get("code_sha256") or "", "other")
        return None if m == "DEGENERATE" else m
    return r["label"]


def vertex(rows, cats, omap):
    n = len(rows)
    v = np.zeros(len(cats))
    ok = 0
    for r in rows:
        if r.get("passed") and r["label"] != "invalid":
            ok += 1
            m = mapped(r, omap)
            if m is not None:
                v[cats.index(m)] += 1
    return v / n, ok / n


def hill_mc(q, rng_seed=123, n=2000, depth=25):
    q = np.asarray(q, float)
    if q.sum() <= 0:
        return float("nan")
    q = q / q.sum()
    g = np.random.Generator(np.random.PCG64(rng_seed))
    m = g.multinomial(depth, q, size=n)
    p = m / depth
    with np.errstate(divide="ignore", invalid="ignore"):
        h = -np.where(m > 0, p * np.log(np.where(m > 0, p, 1)), 0).sum(1)
    return float(np.exp(h).mean())


def h5(vs, ps, step=0.01, n=2000, coarse=False):
    """max Hill over edges of the simplex with cost 100 (p0 - p) <= 5."""
    best = -np.inf
    lam = np.arange(0, 1 + 1e-9, 0.05 if coarse else step)
    cost = lambda p: 100 * (ps[0] - p)
    for i, j in itertools.combinations(range(len(vs)), 2) if len(vs) > 1 else [(0, 0)]:
        for l in lam:
            p = (1 - l) * ps[i] + l * ps[j]
            if cost(p) > 5 + 1e-9:
                continue
            r = (1 - l) * vs[i] + l * vs[j]
            best = max(best, hill_mc(r, n=n if not coarse else 400))
        # exact boundary point
        ci, cj = cost(ps[i]), cost(ps[j])
        if (ci - 5) * (cj - 5) < 0:
            l = (5 - ci) / (cj - ci)
            r = (1 - l) * vs[i] + l * vs[j]
            best = max(best, hill_mc(r, n=n if not coarse else 400))
    return best if np.isfinite(best) else None


def task_h5(rows_by_arm, ref_rows, settings_by_class, omap, coarse=False):
    out = {}
    for cls, sets in settings_by_class.items():
        ref = ref_rows(cls)
        present = [s for s in sets if rows_by_arm.get(s)]
        if not ref or not present:
            continue
        allrows = ref + [r for s in present for r in rows_by_arm[s]]
        cats = sorted({m for r in allrows if r.get("passed") and r["label"] != "invalid"
                       and (m := mapped(r, omap)) is not None})
        if not cats:
            continue
        vs, ps = [], []
        for rr in [ref] + [rows_by_arm[s] for s in present]:
            v, p = vertex(rr, cats, omap)
            vs.append(v)
            ps.append(p)
        out[cls] = h5(vs, ps, coarse=coarse)
    return out


def counts_rule(h5s):
    count1 = sum(1 for t, d in h5s.items() if d.get("PN") is not None and d["PN"] >= 1.5)
    count2 = 0
    D = {}
    for t, d in h5s.items():
        best = max([v for k, v in d.items() if k != "PN" and v is not None], default=None)
        if d.get("PN") is None or best is None:
            continue
        D[t] = d["PN"] - best
        count2 += d["PN"] > best
    return count1, count2, D


def main():
    samples = jl(ROOT / "data" / "samples.jsonl")
    reused = jl(ROOT / "data" / "reused_rows.jsonl")
    omap_p = ROOT / "audit" / "other_map.json"
    omap = json.loads(omap_p.read_text())["by_code_sha256"] if omap_p.exists() else None
    c1 = json.loads((ROOT / "results" / "c1.json").read_text())["primary"]
    out = {"checks": [], "placebos": {}}
    by = defaultdict(lambda: defaultdict(list))
    for r in samples:
        by[r["task"]][r["arm"]].append(r)
    for r in reused:
        by[r["task"]][r["arm"]].append(r)
    classes = {"PN": PN, **NA}

    def ref_fn(t):
        def f(cls):
            if cls.startswith("VETO"):
                return by[t].get("REUSED_TWIN") or by[t].get("TWIN")
            return by[t].get("TWIN")
        return f

    h5s = {t: task_h5(by[t], ref_fn(t), classes, omap) for t in E6 if t in by}
    count1, count2, D = counts_rule(h5s)
    out["independent"] = {"H5": h5s, "count1": count1, "count2": count2, "D_t": D,
                          "D_bar": float(np.mean(list(D.values()))) if D else None}
    out["checks"].append({"what": "count1", "ours": count1, "analysis": c1["count1"], "match": count1 == c1["count1"]})
    out["checks"].append({"what": "count2", "ours": count2, "analysis": c1["count2"], "match": count2 == c1["count2"]})
    for t, d in D.items():
        a = c1["per_task"].get(t, {}).get("D_t")
        out["checks"].append({"what": f"D_t {t}", "ours": d, "analysis": a,
                              "match": a is not None and abs(a - d) <= 0.05, "tolerance": 0.05})
    for t in h5s:
        for cls, v in h5s[t].items():
            a = c1["per_task"].get(t, {})
            pass
    # placebo 1: arm labels shuffled within a task
    rng = random.Random(0)
    fires = 0
    n_shuf = 100
    for s in range(n_shuf):
        hs = {}
        for t in E6:
            if t not in by:
                continue
            arms = [a for a in ["TWIN"] + PN + [x for v in NA.values() for x in v if not x.startswith("VETO")]
                    if by[t].get(a)]
            pool = [r for a in arms for r in by[t][a]]
            sizes = [len(by[t][a]) for a in arms]
            rng.shuffle(pool)
            sh, pos = {}, 0
            for a, n in zip(arms, sizes):
                sh[a] = pool[pos:pos + n]
                pos += n
            cl = {"PN": PN, **{k: v for k, v in NA.items() if not k.startswith("VETO")}}
            hs[t] = task_h5(sh, lambda cls, sh=sh: sh.get("TWIN"), cl, omap, coarse=True)
        c1_, c2_, _ = counts_rule(hs)
        fires += (c1_ >= 3 and c2_ >= 4)
    out["placebos"]["arm_label_shuffle"] = {"n_shuffles": n_shuf, "n_counts_rule_fires": fires,
                                            "pass": fires < 0.05 * n_shuf,
                                            "note": "counts part of the rule only (no CI): a stricter placebo"}
    # placebo 2: PN replaced by TWIN rows -> D_t <= 0
    hs2 = {}
    for t in E6:
        if t not in by:
            continue
        b2 = dict(by[t])
        for a in PN:
            b2[a] = list(by[t].get("TWIN", []))
        hs2[t] = task_h5(b2, ref_fn(t) if True else None, classes, omap, coarse=True)
    _, _, D2 = counts_rule(hs2)
    out["placebos"]["pn_replaced_by_twin"] = {"D_t": D2, "pass": all(v <= 1e-6 for v in D2.values())}
    # engine-check JSD (independent)
    ec = json.loads((ROOT / "results" / "engine_check.json").read_text())
    ours = defaultdict(Counter)
    for r in jl(ROOT / "data" / "engine_check_labels.jsonl"):
        ours[f"{r['task']}|{r['arm']}"][r["label"]] += 1
    for k, c in ec["cells"].items():
        a, b = Counter(c["screen_composition"]), ours[k]
        keys = sorted(set(a) | set(b))
        x = np.array([a[q] for q in keys], float)
        y = np.array([b[q] for q in keys], float)
        x, y = x / x.sum(), y / y.sum()
        m = (x + y) / 2
        kl = lambda p, q: float(sum(pi * math.log2(pi / qi) for pi, qi in zip(p, q) if pi > 0))
        j = 0.5 * kl(x, m) + 0.5 * kl(y, m)
        out["checks"].append({"what": f"engine-check JSD {k}", "ours": j, "analysis": c["JSD"],
                              "match": abs(j - c["JSD"]) < 1e-9})
    # hash chain + timing
    prev, breaks, n = "0" * 64, 0, 0
    first_commit = None
    for line in (ROOT / "commitments.log").read_text().splitlines():
        if not line.strip():
            continue
        utc, rp, h, chain, tag = line.split()[:5]
        ok = hashlib.sha256((prev + h + utc + rp).encode()).hexdigest() == chain
        breaks += not ok
        n += 1
        prev = chain
        if tag == "commit1" and first_commit is None:
            first_commit = utc
    raw_utc = sorted(r["utc"] for r in jl(ROOT / "data" / "samples_raw.jsonl")
                     if not r["block_id"].startswith(("P1:T03:W1", "P2:T03:W1", "P1:T2:W1", "P2:T2:W1")))
    out["hash_chain"] = {"n_lines": n, "breaks": breaks, "first_commit1_utc": first_commit,
                         "first_row_beyond_stage10_utc": raw_utc[0] if raw_utc else None,
                         "commit_precedes_stage1": bool(first_commit and raw_utc and first_commit < raw_utc[0])}
    out["n_checks"] = len(out["checks"])
    out["n_mismatches"] = sum(1 for c in out["checks"] if not c["match"])
    (ROOT / "results" / "rederive.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps({k: v for k, v in out.items() if k != "independent"}, indent=1, default=float)[:3000])


if __name__ == "__main__":
    main()
