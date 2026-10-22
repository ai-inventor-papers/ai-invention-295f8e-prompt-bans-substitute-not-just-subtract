#!/usr/bin/env python3
"""Independent re-derivation of the teacher-forced and geometry headlines from the raw rows (numpy only, no project
imports): layer-profile gains and L* (data/tf_profile.jsonl), held-out TF gains / recoveries of the amended map
(data/tf_heldout_ly.jsonl), and M's paraphrase-null percentiles (cache/m_states_T2.npz + prompts/prompts7.jsonl).
Placebo: the M percentile of a randomly chosen null member must sit inside the null.

usage: .venv/bin/python audit/rederive_tf.py   (writes results/rederive_tf.json)
"""

import json
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def load(p):
    return [json.loads(l) for l in open(p) if l.strip()]


def main():
    checks, mism = [], []

    def check(name, mine, theirs, tol):
        ok = mine is not None and theirs is not None and abs(float(mine) - float(theirs)) <= tol
        checks.append({"check": name, "rederived": mine, "reported": theirs, "ok": ok})
        if not ok:
            mism.append(name)

    # layer profile: mean gain per edit = mean over pairs of C(edit) - C(none); L* = argmax over single blocks
    prof = load(ROOT / "data" / "tf_profile.jsonl")
    by = defaultdict(dict)
    for r in prof:
        by[(r["task"], r["source"], r["base"])][r["edit"]] = r["C"]
    for task in ("T2", "T10", "T03"):
        site = json.loads((ROOT / "results" / f"site_{task}.json").read_text())
        g = defaultdict(list)
        for (t, s, b), d in by.items():
            if t != task:
                continue
            for e, c in d.items():
                g[e].append(c - d["none"])
        mean = {e: float(np.mean(v)) for e, v in g.items()}
        single = {int(e.split("@")[1]): v for e, v in mean.items() if e.startswith("full@")}
        best = max(single.values())
        L = min(l for l, v in single.items() if v >= best - 0.25)
        check(f"{task}:L_star", L, site["L_star"], 0)
        check(f"{task}:band12-23_gain", mean["band12-23"], site["profile"]["mean_gain"]["band12-23"], 1e-6)
    # held-out TF of the amended map: per-kind mean gain and pooled recovery (sum of gains / sum of full gains)
    ho = load(ROOT / "data" / "tf_heldout_ly.jsonl")
    pairs = defaultdict(dict)
    for r in ho:
        pairs[(r["task"], r["source"], r["base"], r["kind"])][r["edit"]] = r["C"]
    for task in ("T2", "T10", "T03"):
        tf = json.loads((ROOT / "results" / f"tf_eval_{task}_LY.json").read_text())["summary"]
        for kind in ("ban", "forced"):
            sel = [d for (t, s, b, k), d in pairs.items() if t == task and (k == kind or k.startswith(kind + "_"))]
            if not sel:
                continue
            for e in ("DASLY_k1", "DASLY_k16"):
                gains = [d[e] - d["none"] for d in sel]
                fulls = [d["full"] - d["none"] for d in sel]
                check(f"{task}:{kind}:{e}:mean_gain", float(np.mean(gains)), tf[kind][e]["mean_gain"], 1e-6)
                check(f"{task}:{kind}:{e}:tf_recovery", float(np.sum(gains) / np.sum(fulls)), tf[kind][e]["tf_recovery"],
                      1e-6)
    # M: distance of each probe to the null centroid and its percentile in the null distribution
    z = np.load(ROOT / "cache" / "m_states_T2.npz")
    keys = [str(k) for k in z["keys"]]
    Z = z["z"].astype(np.float64)
    meta = {r["key"]: r for r in load(ROOT / "prompts" / "prompts7.jsonl")}
    null = [i for i, k in enumerate(keys) if meta[k]["kind"] == "twin" or meta[k]["kind"] == "p0" or
            (meta[k]["kind"] == "padtwin" and meta[k]["Y"] == "dijkstra")]
    zbar = Z[null].mean(0)
    dn = np.linalg.norm(Z[null] - zbar, axis=1)
    m = json.loads((ROOT / "results" / "m_manifold.json").read_text())
    for k, e in m["probes"].items():
        d = float(np.linalg.norm(Z[keys.index(k)] - zbar))
        check(f"M:{k}:D", d, e["D"], 1e-6)
        check(f"M:{k}:percentile", float((dn < d).mean() * 100), e["null_percentile"], 1e-6)
    rng = np.random.default_rng(3)
    i = int(rng.choice(null))
    pl = float((dn < np.linalg.norm(Z[i] - zbar)).mean() * 100)
    checks.append({"check": "M:placebo_null_member_percentile", "value": pl, "ok": pl < 100.0,
                   "note": "a null member must not look like a ban (100th percentile)"})
    out = {"n_checks": len([c for c in checks if "rederived" in c]), "n_mismatch": len(mism), "mismatches": mism,
           "checks": checks}
    (ROOT / "results" / "rederive_tf.json").write_text(json.dumps(out, indent=1))
    print(f"rederive_tf: {out['n_checks']} checks, {len(mism)} mismatches {mism[:10]}; placebo percentile {pl:.1f}")


if __name__ == "__main__":
    main()
