#!/usr/bin/env python3
"""Independent re-derivation of the headline numbers (separate code path from analysis/analyze.py).

Reads data/raw/*.jsonl and the per-sample label files in cache/labels/ directly (not samples.jsonl or results/),
recomputes pass rates, label counts, Hill-1 (via scipy.stats.entropy), rarefied Delta Hill-1 with a vectorised
paired cluster bootstrap, the commitment-test delta_kappa from cache/hR_*.npy, and the T2 PREDICT log score.
Each test is also run on shuffled input (arm membership permuted within paraphrase; ban/mention swapped),
where it should fail. Writes results/audit_rederivation.json.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.stats import entropy

WS = Path(__file__).resolve().parents[1]


def arm(task: str, fname: str) -> list[tuple[int, int, bool, str]]:
    out = []
    for line in (WS / "data/raw" / fname).read_text().splitlines():
        r = json.loads(line)
        h = hashlib.sha256(r["text"].encode("utf-8", errors="replace")).hexdigest()
        lab = json.loads((WS / "cache/labels" / task / f"{h}.json").read_text())
        out.append((r["paraphrase_id"], r["sample_id"], bool(lab["passed"]), lab["label"] or "other"))
    return out


def hill1(labels: list[str]) -> float:
    _, c = np.unique(labels, return_counts=True)
    return float(np.exp(entropy(c)))


def rare(labels: np.ndarray, m: int, rng, reps: int = 30) -> float:
    if len(labels) < m:
        return np.nan
    keys = rng.random((reps, len(labels))).argsort(axis=1)[:, :m]
    vals = [np.exp(entropy(np.unique(labels[k], return_counts=True)[1])) for k in keys]
    return float(np.mean(vals))


def boot_delta(A, B, m, rng, n_boot=2000):
    """Paired cluster bootstrap of rarefied Hill-1(A) - Hill-1(B); A, B: list of (pid, sid, passed, label)."""
    pids = sorted({x[0] for x in A} & {x[0] for x in B})
    ga = {p: [x for x in A if x[0] == p] for p in pids}
    gb = {p: [x for x in B if x[0] == p] for p in pids}
    d = []
    for _ in range(n_boot):
        pick = rng.choice(pids, size=len(pids), replace=True)
        la, lb = [], []
        for p in pick:
            sa = ga[p]
            sb = gb[p]
            la += [sa[i][3] for i in rng.integers(0, len(sa), len(sa)) if sa[i][2]]
            lb += [sb[i][3] for i in rng.integers(0, len(sb), len(sb)) if sb[i][2]]
        va, vb = rare(np.array(la), m, rng), rare(np.array(lb), m, rng)
        if np.isfinite(va) and np.isfinite(vb):
            d.append(va - vb)
    return [float(np.percentile(d, 5)), float(np.percentile(d, 95))], len(d)


def shuffled(A, B, rng):
    """Permute arm membership within each paraphrase (placebo input: no true arm difference)."""
    A2, B2 = [], []
    for p in sorted({x[0] for x in A}):
        pool = [x for x in A if x[0] == p] + [x for x in B if x[0] == p]
        idx = rng.permutation(len(pool))
        na = sum(1 for x in A if x[0] == p)
        A2 += [pool[i] for i in idx[:na]]
        B2 += [pool[i] for i in idx[na:]]
    return A2, B2


def summary(rows):
    lab = [x[3] for x in rows if x[2]]
    u, c = np.unique(lab, return_counts=True)
    return {"n": len(rows), "pass": sum(x[2] for x in rows) / len(rows), "counts": dict(zip(u.tolist(), c.tolist())),
            "hill1": hill1(lab) if lab else None}


def main() -> None:
    rng = np.random.default_rng(20261019)
    out = {}
    c0 = arm("T2", "hf_T2_steer-dc-c0-L18.jsonl")
    dc = arm("T2", "hf_T2_steer-dc-c0.25-L18.jsonl")
    r1 = arm("T2", "hf_T2_steer-rand1-c0.25-L18.jsonl")
    ban = arm("T2", "vllm_T2_ban-dijkstra.jsonl")
    base = arm("T2", "vllm_T2_baseline.jsonl")
    for nm, rows in (("T2_c0", c0), ("T2_dc_c0.25", dc), ("T2_rand1", r1), ("T2_ban", ban), ("T2_baseline", base)):
        out[nm] = summary(rows)
    t1 = {nm: summary(arm("T1", f)) for nm, f in (("T1_baseline", "vllm_T1_baseline.jsonl"),
                                                  ("T1_c0", "hf_T1_steer-dc-c0-L18.jsonl"),
                                                  ("T1_dc_c0.1", "hf_T1_steer-dc-c0.1-L18.jsonl"),
                                                  ("T1_dc_c0.25", "hf_T1_steer-dc-c0.25-L18.jsonl"))}
    out.update(t1)

    def delta(A, B, label):
        nA, nB = sum(x[2] for x in A), sum(x[2] for x in B)
        m = max(2, int(0.85 * min(nA, nB)))
        pt = rare(np.array([x[3] for x in A if x[2]]), m, rng, 1000) - rare(np.array([x[3] for x in B if x[2]]), m, rng, 1000)
        ci, nb = boot_delta(A, B, m, rng)
        sh = [boot_delta(*shuffled(A, B, rng), m, rng, n_boot=400)[0] for _ in range(5)]
        out[label] = {"rarefy_to": m, "point": float(pt), "ci90_cluster": ci, "n_boot_valid": nb,
                      "shuffled_ci90": sh, "shuffled_excludes_zero": [bool(c[0] > 0 or c[1] < 0) for c in sh]}

    delta(dc, c0, "T2_delta_dc_vs_c0")
    delta(dc, r1, "T2_delta_dc_vs_rand1")
    # commitment test, T2 / Dijkstra, layer 18 (index 10 in layers 8..28)
    li = 18 - 8
    L = np.load(WS / "cache/hR_T2_LIST.npy")[:, li].astype(np.float64)
    I = np.load(WS / "cache/hR_T2_IMPLEMENT.npy")[:, li].astype(np.float64)
    B_ = np.load(WS / "cache/hR_T2_ban-dijkstra.npy")[:, li].astype(np.float64)
    M_ = np.load(WS / "cache/hR_T2_mention-dijkstra.npy")[:, li].astype(np.float64)
    d = L.mean(0) - I.mean(0)
    dn = np.linalg.norm(d)
    dk = float((B_[:10] - M_[:10]).mean(0) @ d / dn ** 2)
    null = []
    for _ in range(2000):
        p = rng.permutation(20)
        null.append(float((M_[p[10:]].mean(0) - M_[p[:10]].mean(0)) @ d / dn ** 2))
    band = [float(np.percentile(null, 2.5)), float(np.percentile(null, 97.5))]
    sh = []
    for _ in range(200):  # placebo: swap ban/mention within random pairs
        flip = rng.random(10) < 0.5
        Bs = np.where(flip[:, None], M_[:10], B_[:10])
        Ms = np.where(flip[:, None], B_[:10], M_[:10])
        sh.append(float((Bs - Ms).mean(0) @ d / dn ** 2))
    out["T2_commitment"] = {"delta_kappa": dk, "null_band_95": band, "outside_band": bool(dk > band[1] or dk < band[0]),
                            "shuffled_fraction_outside_band": float(np.mean([(x > band[1] or x < band[0]) for x in sh]))}
    # PREDICT: T2 ban1 dc mean log score over compliant samples
    fc = json.loads((WS / "forecast/predict_T2_ban1.json").read_text())
    q = fc["forecasts"]["dc"]
    comp = [x[3] for x in ban if x[2] and x[3] != "dijkstra"]
    out["T2_predict_dc_logscore"] = float(np.mean([np.log(q.get(l, q["other"])) for l in comp]))
    out["T2_predict_n_compliant"] = len(comp)
    (WS / "results/audit_rederivation.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
