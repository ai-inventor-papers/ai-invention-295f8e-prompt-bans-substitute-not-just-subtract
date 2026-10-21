#!/usr/bin/env python3
"""Independent re-derivation of the headline numbers from the raw files (data/samples_raw.jsonl, data/labels.jsonl,
predictions/c2_commit.json), with code paths that share nothing with analysis/ except the file formats:
plain dict counting, scipy.stats.spearmanr, an own permutation loop, math.comb binomial tails.

Checks: twin and POP arm shares, y per direction, C2a rho per task (vs results/c2a.json), confirmed-escape counts
(vs results/escape.json), C2c arm shares (vs results/c2c.json). Placebos that must FAIL: (1) pi shuffled across
directions (mean rho ~ 0), (2) labels shuffled between arms within (task, template) (escapes vanish),
(3) a wrong task's subspace (rho_pi with another task's pi; no specificity expected to survive). Hash chain and the
commit-before-first-population-row timing are verified. -> results/rederive.json
"""

from __future__ import annotations

import json
import math
import random
import sys
from collections import defaultdict
from pathlib import Path

from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
MOV = ["T03", "T2", "T05", "T10", "T06", "T1"]
OTH = ["T04", "T08", "T11", "T13", "T14", "R1", "R3", "R6", "R2"]
EXC = {"invalid", "disputed"}


def jl(p):
    with open(p) as fh:
        return [json.loads(l) for l in fh if l.strip()]


def binom_sf(k, n, p):
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k, n + 1))


def main():
    raw = jl(ROOT / "data/samples_raw.jsonl")
    lab = {l["key"]: l for l in jl(ROOT / "data/labels.jsonl")}
    commit = json.loads((ROOT / "predictions/c2_commit.json").read_text())
    cats = {t: set(commit["tasks"][t]["modes"]) for t in commit["tasks"]}
    dflt = {t: commit["tasks"][t]["default"] for t in commit["tasks"]}
    R = []
    for r in raw:
        k = f"{r['task']}|{r['template']}|{r['arm']}|{r['sample_id']}"
        if k in lab:
            R.append((r["task"], r["arm"], r["template"], int(r["sample_id"]), lab[k]["label"], bool(lab[k]["passed"])))
    out = {"n_rows": len(R), "mismatches": []}

    def shr(rows, t):
        v = [x for x in rows if x[4] not in EXC]
        off = sum(1 for x in v if x[4] in cats[t] and x[4] != dflt[t])
        return (off / len(v) if v else float("nan")), off, len(v), (sum(x[5] for x in rows) / len(rows) if rows else 0)
    by = defaultdict(list)
    for x in R:
        by[(x[0], x[1])].append(x)
    tw_k = {t: 10 if t in MOV else 6 for t in MOV + OTH}
    res_c2a = json.loads((ROOT / "results/c2a.json").read_text()) if (ROOT / "results/c2a.json").exists() else {}
    res_esc = json.loads((ROOT / "results/escape.json").read_text()) if (ROOT / "results/escape.json").exists() else {}
    out["c2a"], out["escape"] = {}, {}
    rng = random.Random(7)
    for t in MOV + OTH:
        twin = [x for x in by[(t, "TWIN")] if x[3] < tw_k[t]]
        if not twin:
            continue
        ts, tk, tn, tp = shr(twin, t)
        p0 = (tk + 0.5) / (tn + 1)
        seeds = list(range(9101, 9141)) if t in MOV else list(range(9101, 9109))
        ys, conf = [], 0
        for s in seeds:
            yy = []
            for a in ("1.0", "2.0"):
                rr = by[(t, f"POP_d{s}_a{a}")]
                f10 = [x for x in rr if x[3] in (0, 1)]
                p30 = [x for x in rr if x[3] < 6]
                fs, fk, fn, fp = shr(f10, t)
                yy.append(fs)
                ps, pk, pn, pp = shr(p30, t)
                if (fn and fs - ts >= 0.2 - 1e-12 and fp >= 0.8 * tp - 1e-12 and len(p30) > len(f10) and
                        ps - ts >= 0.2 - 1e-12 and binom_sf(pk, pn, p0) < 0.05 and pp >= 0.8 * tp - 1e-12):
                    conf += 1
            ys.append(sum(yy) / len(yy))
        out["escape"][t] = {"twin_share": ts, "n_confirmed_total": conf}
        e_ref = res_esc.get(t, {}).get("E_t", {})
        ref_conf = sum((e_ref.get(a) or {}).get("n_confirmed") or 0 for a in ("1.0", "2.0"))
        if t in res_esc and ref_conf != conf:
            out["mismatches"].append({"what": "confirmed", "task": t, "rederived": conf, "analysis": ref_conf})
        if t in MOV and t in commit["predictors"]:
            pi = [commit["predictors"][t][str(s)]["pi"] for s in seeds]
            rho = float(spearmanr(pi, ys)[0]) if len(set(ys)) > 1 else 0.0
            ge = 0
            for _ in range(2000):
                yy = ys[:]
                rng.shuffle(yy)
                rr = float(spearmanr(pi, yy)[0]) if len(set(yy)) > 1 else 0.0
                ge += rr >= rho - 1e-12
            p = (1 + ge) / 2001
            ref = res_c2a.get("per_task", {}).get(t, {}).get("predictors", {}).get("pi", {})
            out["c2a"][t] = {"rho": rho, "p_2000perm": p, "analysis_rho": ref.get("rho"), "analysis_p": ref.get("p")}
            if ref and abs(ref["rho"] - rho) > 1e-9:
                out["mismatches"].append({"what": "rho_pi", "task": t, "rederived": rho, "analysis": ref["rho"]})
            # placebo 1: pi shuffled across directions
            pl = []
            for _ in range(500):
                pp_ = pi[:]
                rng.shuffle(pp_)
                pl.append(float(spearmanr(pp_, ys)[0]) if len(set(ys)) > 1 else 0.0)
            out["c2a"][t]["placebo_pi_shuffled_mean_rho"] = sum(pl) / len(pl)
            # placebo 3: wrong task's pi (same seeds, other task's subspace)
            wr = [float(spearmanr([commit["predictors"][t2][str(s)]["pi"] for s in seeds], ys)[0])
                  for t2 in MOV if t2 != t and len(set(ys)) > 1]
            out["c2a"][t]["placebo_wrong_task_rho_mean"] = sum(wr) / len(wr) if wr else None
        # placebo 2: labels shuffled between arms within (task, template)
        allr = [x for x in R if x[0] == t and (x[1] == "TWIN" or x[1].startswith("POP_"))]
        bytpl = defaultdict(list)
        for x in allr:
            bytpl[x[2]].append(x)
        shuf = []
        for w, xs in bytpl.items():
            labs = [(x[4], x[5]) for x in xs]
            rng.shuffle(labs)
            shuf += [(x[0], x[1], x[2], x[3], l, p) for x, (l, p) in zip(xs, labs)]
        sb = defaultdict(list)
        for x in shuf:
            sb[x[1]].append(x)
        twin_s = [x for x in sb["TWIN"] if x[3] < tw_k[t]]
        ts2, tk2, tn2, tp2 = shr(twin_s, t)
        p02 = (tk2 + 0.5) / (tn2 + 1)
        conf2 = 0
        for s in seeds:
            for a in ("1.0", "2.0"):
                rr = sb[f"POP_d{s}_a{a}"]
                f10 = [x for x in rr if x[3] in (0, 1)]
                p30 = [x for x in rr if x[3] < 6]
                fs, fk, fn, fp = shr(f10, t)
                ps, pk, pn, pp = shr(p30, t)
                if (fn and fs - ts2 >= 0.2 and fp >= 0.8 * tp2 and len(p30) > len(f10) and ps - ts2 >= 0.2 and
                        binom_sf(pk, pn, p02) < 0.05 and pp >= 0.8 * tp2):
                    conf2 += 1
        out["escape"][t]["placebo_labels_shuffled_confirmed"] = conf2
    # C2c shares
    res_c2c = json.loads((ROOT / "results/c2c.json").read_text()) if (ROOT / "results/c2c.json").exists() else {}
    out["c2c"] = {}
    for t in MOV:
        for arm in ("C2C_r_s0.5", f"C2C_rand{9301 + MOV.index(t)}_s0.5"):
            rr = by[(t, arm)]
            if rr:
                s, k, n, p = shr(rr, t)
                out["c2c"][f"{t}|{arm}"] = {"share": s, "pass": p, "n": len(rr)}
                ref = res_c2c.get("per_task", {}).get(t, {}).get("arms", {}).get(arm, {})
                if ref and abs(ref.get("share", -1) - s) > 1e-9:
                    out["mismatches"].append({"what": "c2c_share", "task": t, "arm": arm, "rederived": s,
                                              "analysis": ref.get("share")})
    # hash chain + timing
    sys.path.insert(0, str(ROOT / "src"))
    sys.path.insert(0, str(ROOT / "src_base"))
    from commit4 import verify
    v = verify()
    first_pop = min((r["utc"] for r in raw if r.get("family") == "POP"), default=None)
    c1 = v["first_utc_by_tag"].get("commit1_predictors_rules")
    out["commitments"] = v
    out["commit1_utc"], out["first_population_row_utc"] = c1, first_pop
    out["commit_precedes_population"] = bool(c1 and first_pop and c1 < first_pop)
    out["n_mismatches"] = len(out["mismatches"])
    (ROOT / "results/rederive.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: out[k] for k in ("n_rows", "n_mismatches", "commit_precedes_population")}))


if __name__ == "__main__":
    main()
