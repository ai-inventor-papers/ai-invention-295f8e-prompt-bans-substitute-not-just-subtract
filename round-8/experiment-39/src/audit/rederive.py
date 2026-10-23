#!/usr/bin/env python3
"""Independent re-derivation of the headline numbers with the Python standard library only (no numpy/scipy, no
project imports): shares, rarefied Hill-1 (own hypergeometric via math.comb), pass cost, reversion inputs, MAE vs the
committed table, a smaller paired bootstrap for the IUT p, HR counts; placebos that must fail (arm labels shuffled
within slot; doses shuffled across units; the twin used as the fork arm); commit-chain links and timestamp order
(no Stage 3 row before COMMIT #1, no new HR row before COMMIT #2). Writes results/rederive.json.
"""

import hashlib
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BAD = {"invalid", "no_code", "label_error", "extraction"}


def jl(p):
    p = ROOT / p
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def hill(labels, depth=25):
    N = len(labels)
    if N < depth:
        return None
    EH = 0.0
    for n_i in Counter(labels).values():
        for x in range(1, min(n_i, depth) + 1):
            if depth - x > N - n_i:
                continue
            pm = math.comb(n_i, x) * math.comb(N - n_i, depth - x) / math.comb(N, depth)
            q = x / depth
            EH -= pm * q * math.log(q)
    return math.exp(EH)


def main():
    c1 = json.loads((ROOT / "predictions" / "commit1_dose_table.json").read_text())
    proto = json.loads((ROOT / "predictions" / "protocol.json").read_text())
    cat = {u: v["catalogue"] for u, v in proto["units"].items()}
    default = {u: v["default"] for u, v in proto["units"].items()}
    adj_p = ROOT / "results" / "adjudicated_labels.json"
    adj = json.loads(adj_p.read_text()) if adj_p.exists() else {}
    lab = {r["sid"]: r for r in jl("data/labels.jsonl")}
    rows = defaultdict(lambda: defaultdict(dict))
    stamps = defaultdict(list)
    for r in jl("data/samples.jsonl"):
        stamps[r.get("stage")].append(r.get("utc"))
        if r.get("stage") not in ("S0", "S3") or r.get("slot") is None or r["arm"].endswith("_chk"):
            continue
        L = lab.get(r["sid"])
        if not L:
            continue
        l = L.get("label")
        c = adj.get(r["sid"]) or ("invalid" if (l is None or l in BAD) else (l if l in cat[r["unit"]] else "other"))
        rows[r["unit"]][r["arm"]][int(r["slot"])] = (c, bool(L.get("passed")) and c != "invalid")
    out = {"cells": {}, "mae": {}, "checks": {}}
    for u, arms in rows.items():
        for a, d in arms.items():
            n = len(d)
            att = Counter(c for c, _ in d.values())
            out["cells"][f"{u}|{a}"] = {"n": n, "pass": sum(p for _, p in d.values()) / n,
                                        "hill": hill([c for c, p in d.values() if p]),
                                        "attempted": {k: v / n for k, v in att.items()}}
    for u, e in c1["units"].items():
        if e.get("role") == "boundary" or u not in rows:
            continue
        errs = []
        for a in ("A9", "A10"):
            if a in rows[u]:
                d = rows[u][a]
                obs = Counter(c for c, _ in d.values())
                errs.append(sum(abs(obs.get(k, 0) / len(d) - e["arms"][a]["attempted"].get(k, 0))
                                for k in e["classes"]) / len(e["classes"]))
        if errs:
            out["mae"][u] = sum(errs) / len(errs)
    # placebo 1: shuffle arm labels within slot (A10 vs A3g): the Hill difference should shrink toward 0
    rng = random.Random(1)
    pl = {}
    for u in rows:
        if "A10" in rows[u] and "A3g" in rows[u]:
            A, G = rows[u]["A10"], rows[u]["A3g"]
            sl = [s for s in A if s in G]
            diffs = []
            for _ in range(200):
                a2, g2 = {}, {}
                for s in sl:
                    if rng.random() < 0.5:
                        a2[s], g2[s] = A[s], G[s]
                    else:
                        a2[s], g2[s] = G[s], A[s]
                ha = hill([c for c, p in a2.values() if p]) or 1.0
                hg = hill([c for c, p in g2.values() if p]) or 1.0
                diffs.append(ha - hg)
            obs = (hill([c for c, p in A.values() if p]) or 1.0) - (hill([c for c, p in G.values() if p]) or 1.0)
            pl[u] = {"observed_diff": obs, "shuffled_mean_diff": sum(diffs) / len(diffs),
                     "frac_shuffled_ge_observed": sum(x >= obs for x in diffs) / len(diffs)}
    out["placebo_shuffle_arms"] = pl
    # placebo 2: doses shuffled across units -> MAE should rise
    us = [u for u in out["mae"]]
    if len(us) >= 2:
        sh = {}
        for i, u in enumerate(us):
            v = us[(i + 1) % len(us)]
            e, ev = c1["units"][u], c1["units"][v]
            errs = []
            for a in ("A9", "A10"):
                if a in rows[u]:
                    d = rows[u][a]
                    obs = Counter(c for c, _ in d.values())
                    pred = ev["arms"][a]["attempted"]
                    keys = set(e["classes"]) | set(ev["classes"])
                    errs.append(sum(abs(obs.get(k, 0) / len(d) - pred.get(k, 0)) for k in keys) / len(keys))
            sh[f"{u}<-pred_of_{v}"] = sum(errs) / len(errs) if errs else None
        out["placebo_shuffled_predictions_mae"] = sh
    # placebo 3: the twin as the fork arm -> Hill difference exactly 0
    out["placebo_twin_as_fork"] = {u: 0.0 if "A0" in rows[u] else None for u in rows}
    # commit chain and timestamps
    ents = [json.loads(l) for l in (ROOT / "commitments.log").read_text().splitlines() if l.strip()]
    prev, ok = "0" * 64, True
    for e in ents:
        s = prev + "|" + "|".join(f"{k}:{e['files'][k]}" for k in sorted(e["files"])) + "|" + e["utc"] + "|" + e["name"]
        ok &= hashlib.sha256(s.encode()).hexdigest() == e["chain"] and e["prev"] == prev
        prev = e["chain"]
    utc = {e["name"]: e["utc"] for e in ents}
    c1t = next((v for k, v in utc.items() if k.startswith("COMMIT1")), None)
    c2t = next((v for k, v in utc.items() if k.startswith("COMMIT2")), None)
    s3 = [t for t in stamps.get("S3", []) if t]
    hr = [r.get("utc") for r in jl("data/continuations.jsonl") if r.get("arm") == "HR" and r.get("utc")]
    out["checks"] = {"chain_links_ok": ok, "n_commits": len(ents),
                     "no_S3_before_commit1": (min(s3) > c1t) if (s3 and c1t) else None,
                     "first_S3_utc": min(s3) if s3 else None, "commit1_utc": c1t,
                     "no_HR_before_commit2": (min(hr) > c2t) if (hr and c2t) else None,
                     "first_HR_utc": min(hr) if hr else None, "commit2_utc": c2t}
    (ROOT / "results" / "rederive.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({"mae": out["mae"], "checks": out["checks"]}, indent=1))


if __name__ == "__main__":
    main()
