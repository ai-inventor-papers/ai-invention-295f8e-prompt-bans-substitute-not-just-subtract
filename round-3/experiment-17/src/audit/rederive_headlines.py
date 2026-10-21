#!/usr/bin/env python3
"""Independent re-derivation of the headline numbers from RAW files, through code paths that share nothing with
src/analysis (plain counting, math.comb McNemar, statistics.fmean, an sklearn decoder), plus placebo inputs on which
every statistical test must FAIL. Writes results/rederive_headlines.json."""

from __future__ import annotations

import json
import math
import random
import statistics
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DEF = {"T1": "bfs", "T2": "dijkstra", "T03": "full_sort", "T04": "naive", "T06": "hash_set", "T05": "hash_map"}
NA = ("invalid", "disputed")


def load_rows() -> dict:
    labs = {}
    for line in (ROOT / "data" / "labels.jsonl").read_text().splitlines():
        r = json.loads(line)
        labs[r["key"]] = r["label"]
    rows = {}
    for line in (ROOT / "data" / "samples_raw.jsonl").read_text().splitlines():
        r = json.loads(line)
        k = f"{r['task']}|{r['template']}|{r['arm']}|{r['sample_id']}"
        rows[(r["task"], r["arm"], r["template"], int(r["sample_id"]))] = labs[k]
    return rows


def arm(rows, t, a, kmax=None):
    return {(w, k): l for (tt, aa, w, k), l in rows.items() if tt == t and aa == a and (kmax is None or k < kmax)}


def mcnemar_p(x, y):  # one-sided exact: H1 P(x=1,y=0) > P(x=0,y=1)
    n10 = sum(1 for a, b in zip(x, y) if a and not b)
    n01 = sum(1 for a, b in zip(x, y) if b and not a)
    n = n10 + n01
    return sum(math.comb(n, i) for i in range(n10, n + 1)) / 2 ** n if n else 1.0


def paired(A, B, f):
    ks = [s for s in A if s in B and A[s] not in NA and B[s] not in NA]
    return [f(A[s]) for s in ks], [f(B[s]) for s in ks]


def main() -> None:
    rows = load_rows()
    out: dict = {}
    rnd = random.Random(1)
    # ---- C2d: event gates, ADD vs RAND exact McNemar + Holm, ADD pass count, pooled SUBTRACT
    gate, n_pass, holm_all = {}, 0, {}
    for t, d in DEF.items():
        ban = [l for l in arm(rows, t, "BAN").values() if l not in NA]
        av = sum(l != d for l in ban) / len(ban)
        gate[t] = {"ban_avoidance": av, "n_nonbanned": sum(l != d for l in ban),
                   "gated": av >= 0.5 and sum(l != d for l in ban) >= 20}
        ps = []
        for al in ("1.0", "2.0"):
            A = arm(rows, t, f"ADD_a{al}", 10)
            for s in (9001, 9002, 9003):
                x, y = paired(A, arm(rows, t, f"RAND{s}_a{al}", 10), lambda l: int(l != d))
                ps.append((al, s, mcnemar_p(x, y)))
        order = sorted(range(len(ps)), key=lambda i: ps[i][2])
        adj, run = [0.0] * len(ps), 0.0
        for rank, i in enumerate(order):
            run = max(run, min(1.0, (len(ps) - rank) * ps[i][2]))
            adj[i] = run
        holm_all[t] = [(a, s, round(p, 6), round(q, 6)) for (a, s, p), q in zip(ps, adj)]
        sig_alpha = [al for al in ("1.0", "2.0") if all(q < 0.05 for (a, s, p), q in zip(ps, adj) if a == al)]
        if gate[t]["gated"] and sig_alpha:
            n_pass += 1  # (landing clause checked only if the avoidance clause holds; it never does)
    out["c2d"] = {"event_gate": gate, "holm": holm_all, "n_add_pass_avoidance_clause": n_pass}
    deltas = {}
    for t, d in DEF.items():
        S, Bn = arm(rows, t, "SUB_plain"), arm(rows, t, "BAN")
        x, y = paired(S, Bn, lambda l: int(l == d))
        deltas[t] = (sum(x) - sum(y)) / len(x)
    gated_sub = [t for t in DEF if 1 - gate[t]["ban_avoidance"] <= 0.5]
    out["c2d"]["sub_delta"] = deltas
    out["c2d"]["pooled_sub_delta_gated"] = statistics.fmean(deltas[t] for t in gated_sub)
    out["c2d"]["gated_sub_tasks"] = gated_sub
    # placebo: shuffle ADD/RAND labels within slots -> fraction of significant one-sided McNemar tests ~ alpha
    sig, tot = 0, 0
    for _ in range(200):
        for t, d in (("T2", "dijkstra"), ("T03", "full_sort")):
            A, R = arm(rows, t, "ADD_a1.0", 10), arm(rows, t, "RAND9001_a1.0", 10)
            ks = [s for s in A if s in R and A[s] not in NA and R[s] not in NA]
            x, y = [], []
            for s in ks:
                a, b = (A[s], R[s]) if rnd.random() < 0.5 else (R[s], A[s])
                x.append(int(a != d))
                y.append(int(b != d))
            sig += mcnemar_p(x, y) < 0.05
            tot += 1
    out["c2d"]["placebo_mcnemar_fraction_p_lt_0.05"] = sig / tot
    # ---- C2f
    c2f = {}
    for t, d in (("T1", "bfs"), ("T2", "dijkstra")):
        sh = {}
        for a in ("BAN", "HEADS_target", "HEADS_rand7101", "HEADS_rand7102", "HEADS_rand7103"):
            v = [l for l in arm(rows, t, a, 10).values() if l not in NA]
            sh[a] = sum(l == d for l in v) / len(v)
        c2f[t] = {"banned_share": sh, "delta_vs_mean_random":
                  sh["HEADS_target"] - statistics.fmean(sh[f"HEADS_rand{s}"] for s in (7101, 7102, 7103))}
    out["c2f"] = c2f
    # ---- U7 and exploratory random distribution
    out["u7"] = {a: sum(l == "dijkstra" for l in arm(rows, "T2", a).values()) for a in ("U7_BAN", "U7_NEUTRAL")}
    expl = {}
    for t, d in (("T2", "dijkstra"), ("T03", "full_sort"), ("T1", "bfs")):
        def avoid(a):
            v = [l for l in arm(rows, t, a, 10).values() if l not in NA]
            return sum(l != d for l in v) / len(v)
        r = [avoid(f"RAND{s}_a1.0") for s in range(9001, 9016)]
        a = avoid("ADD_a1.0")
        expl[t] = {"add": a, "n_random": len(r), "n_random_above_add": sum(x > a for x in r), "random_max": max(r)}
    out["exploratory_random"] = expl
    # ---- 0g: FR_zero from the raw per-sequence CE lists (statistics.fmean), frozen rule, and a placebo swap
    raw = json.loads((ROOT / "results" / "sae_transfer_raw.json").read_text())

    def fr(cell, L, swap=False):
        c = statistics.fmean(cell["ce_clean"])
        s, z = cell["layers"][L]["ce_sae"], cell["layers"][L]["ce_zero"]
        if swap:
            pairs = [(b, a) if rnd.random() < 0.5 else (a, b) for a, b in zip(s, z)]
            s, z = [p[0] for p in pairs], [p[1] for p in pairs]
        return (statistics.fmean(z) - statistics.fmean(s)) / (statistics.fmean(z) - c)
    g = {}
    for L in ("15", "20", "27"):
        fi, fb = fr(raw["inst_own"], L), fr(raw["base_own"], L)
        fi_p, fb_p = fr(raw["inst_own"], L, True), fr(raw["base_own"], L, True)
        g[L] = {"fr_zero_inst": fi, "fr_zero_base": fb, "frozen_pass": fi >= 0.9 * fb,
                "placebo_fr_zero_inst": fi_p, "placebo_fr_zero_base": fb_p, "placebo_frozen_pass": fi_p >= 0.9 * fb_p}
    out["zero_g"] = g
    # ---- C2e: independent sklearn decoder on T2 batch-1 states (k = 8, block 17) + permuted-label placebo
    from sklearn.decomposition import PCA
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import balanced_accuracy_score
    from sklearn.model_selection import StratifiedKFold, cross_val_predict
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    single = ROOT / "states" / "T2_BAN.npy"  # states over 90 MB are stored as row-wise parts T2_BAN.partNNN.npy
    X = np.load(single, mmap_mode="r") if single.exists() else np.concatenate(
        [np.load(p) for p in sorted((ROOT / "states").glob("T2_BAN.part[0-9][0-9][0-9].npy"))], axis=0)
    idx = [json.loads(l) for l in (ROOT / "states" / "T2_BAN_index.jsonl").read_text().splitlines()]
    blocks = json.loads((ROOT / "states" / "T2_BAN_meta.json").read_text())["blocks"]
    labs = {json.loads(l)["key"]: json.loads(l)["label"] for l in (ROOT / "data" / "labels.jsonl").read_text().splitlines()}
    keep = [i for i, r in enumerate(idx) if labs[r["key"]] not in NA]
    y = np.array([int(labs[idx[i]["key"]] == "dijkstra") for i in keep])
    g_t = np.array([idx[i]["template"] for i in keep])
    pos = 2 + 7  # Smean, R, k1..k8 -> k8
    Xk = np.asarray(X[keep, pos, blocks.index(17)], dtype=np.float32)
    clf = make_pipeline(StandardScaler(), PCA(64, random_state=0), LogisticRegression(C=0.01, class_weight="balanced",
                                                                                     max_iter=5000))
    cv = StratifiedKFold(5, shuffle=True, random_state=0)
    ba = balanced_accuracy_score(y, cross_val_predict(clf, Xk, y, cv=cv))
    perm_ba = []
    for s in range(20):
        rng = np.random.default_rng(s)
        yp = y.copy()
        for w in np.unique(g_t):
            ix = np.where(g_t == w)[0]
            yp[ix] = y[rng.permutation(ix)]
        perm_ba.append(balanced_accuracy_score(yp, cross_val_predict(clf, Xk, yp, cv=cv)))
    out["c2e_T2_k8_block17_sklearn"] = {"ba": ba, "placebo_ba_mean": float(np.mean(perm_ba)),
                                        "placebo_ba_q95": float(np.quantile(perm_ba, 0.95)),
                                        "frozen_null_q95_k8": 0.695, "below_frozen_null": ba < 0.695}
    # determinism: identical prefixes -> identical batch-1 states (raw fp16 bytes)
    same, diff = 0, 0
    by = {}
    for i in keep:
        by.setdefault((idx[i]["template"], tuple(idx[i]["tok16"][:8])), []).append(i)
    for grp in by.values():
        for j in grp[1:]:
            if np.array_equal(np.asarray(X[grp[0], pos]), np.asarray(X[j, pos])):
                same += 1
            else:
                diff += 1
    out["c2e_T2_determinism_k8"] = {"identical_pairs": same, "differing_pairs": diff}
    # ---- comparison with the reported numbers
    rep_c2d = json.loads((ROOT / "results" / "c2d.json").read_text())
    rep_c2f = json.loads((ROOT / "results" / "c2f.json").read_text())
    rep_sae = json.loads((ROOT / "results" / "sae_transfer.json").read_text())
    chk = {
        "pooled_sub_delta": [out["c2d"]["pooled_sub_delta_gated"], rep_c2d["pooled_subtract"]["delta"]],
        "n_add_pass": [out["c2d"]["n_add_pass_avoidance_clause"], rep_c2d["n_add_pass"]],
        "delta_T1": [c2f["T1"]["delta_vs_mean_random"], rep_c2f["delta_T1"]],
        "delta_T2": [c2f["T2"]["delta_vs_mean_random"], rep_c2f["delta_T2"]],
        "fr_zero_inst_L15": [g["15"]["fr_zero_inst"], rep_sae["per_layer"]["15"]["fr_zero_inst_own"]],
        "fr_zero_base_L27": [g["27"]["fr_zero_base"], rep_sae["per_layer"]["27"]["fr_zero_base_own"]],
    }
    out["comparison_with_reported"] = {k: {"rederived": v[0], "reported": v[1], "match": abs(v[0] - v[1]) < 1e-9}
                                       for k, v in chk.items()}
    (ROOT / "results" / "rederive_headlines.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: out[k] for k in ("comparison_with_reported", "u7", "exploratory_random",
                                          "c2e_T2_k8_block17_sklearn", "c2e_T2_determinism_k8")}, indent=1))
    print("placebo McNemar fraction significant:", out["c2d"]["placebo_mcnemar_fraction_p_lt_0.05"])
    print("0g:", {L: (round(v["fr_zero_inst"], 4), round(v["fr_zero_base"], 4), v["frozen_pass"],
                      round(v["placebo_fr_zero_inst"], 3), round(v["placebo_fr_zero_base"], 3), v["placebo_frozen_pass"])
                  for L, v in g.items()})
    print("gates:", {t: v["gated"] for t, v in gate.items()}, "sub deltas:", {t: round(v, 3) for t, v in deltas.items()})


if __name__ == "__main__":
    main()
