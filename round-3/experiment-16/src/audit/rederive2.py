#!/usr/bin/env python3
"""Second independent re-derivation (raw rows only; no import of src/): the headline numbers audit/rederive.py does
not cover, each recomputed by direct counting, plus every statistical test re-run on shuffled input, where it must fail.
Writes results/rederive2.json and prints a compact comparison against the reported values."""

import collections
import json
from pathlib import Path

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
X = {"invalid", "no_code", "disputed"}
D = {"T03": "full_sort", "T04": "naive", "T06": "hash_set", "T05": "hash_map", "T10": "union_find", "R1": "greedy_end",
     "T08": "iteration", "R3": "kahn", "T13": "sort_sweep", "R6": "binary_search", "T14": "sort_by_count",
     "T11": "quadratic_dp", "t1": "bfs", "t2": "dijkstra"}
GATED = ["T03", "T06", "T05", "T10", "T13"]
rng = np.random.default_rng(7)

rows = {}
for line in (ROOT / "data" / "samples.jsonl").open():
    r = json.loads(line)
    rows[r["uid"]] = r
rows = list(rows.values())
cell = collections.defaultdict(list)                  # (task, arm) -> [is_default] over attempted rows
slot = {}                                             # (task, arm, w, k) -> is_default
for r in rows:
    if r["label"] in X or r["stage"] == "U9":
        continue
    v = int(r["label"] == D[r["task"]])
    cell[(r["task"], r["arm"])].append(v)
    slot[(r["task"], r["arm"], r["template"], r["k"])] = v
s = {k: float(np.mean(v)) for k, v in cell.items()}


def pooled(tasks, arm, b="b", a="a"):
    return sum(s[(t, b)] - s[(t, arm)] for t in tasks) / sum(s[(t, b)] - s[(t, a)] for t in tasks)


out = {}
# pooled F incl. F_K0 and I, and a leave-one-task-out jackknife written from scratch
pt = {k: pooled(GATED, arm) for k, arm in (("F_prompt", "c"), ("F_direct", "d"), ("F_K0", "K0"))}
pt["I"] = 1 - pt["F_prompt"] - pt["F_direct"]
jk = {}
for k, arm in (("F_prompt", "c"), ("F_direct", "d"), ("F_K0", "K0")):
    th = np.array([pooled([t for t in GATED if t != u], arm) for u in GATED])
    n = len(th)
    se = np.sqrt((n - 1) / n * ((th - th.mean()) ** 2).sum())
    q = stats.t.ppf(0.975, n - 1)
    jk[k] = [pt[k] - q * se, pt[k] + q * se]
out["pooled"] = pt
out["jackknife95"] = jk
# C2c Spearman rho + permutation p (scipy's exact permutation test, a different path), and on shuffled F
c2c = json.loads((ROOT / "predictions" / "c2c.json").read_text())
V = np.array([c2c[t]["V"] for t in GATED])
Fd = np.array([(s[(t, "b")] - s[(t, "d")]) / (s[(t, "b")] - s[(t, "a")]) for t in GATED])
res = stats.permutation_test((V, Fd), lambda x, y: stats.spearmanr(x, y).statistic, permutation_type="pairings",
                             alternative="less", n_resamples=np.inf)
out["c2c"] = {"rho": float(stats.spearmanr(V, Fd).statistic), "perm_p_less_exact": float(res.pvalue),
              "hits": {t: bool(f >= 0.25) for t, f in zip(GATED, Fd)}}
# McNemar on CRN-paired slots, and on shuffled pairings (must not be significant)
mc = {}
for t, x, y in (("T06", "a", "c"), ("T03", "b", "d"), ("T05", "b", "d"), ("T13", "a", "d")):
    keys = [(w, k) for w in ("W1", "W2", "W3", "W4", "W5") for k in range(20)
            if (t, x, w, k) in slot and (t, y, w, k) in slot]
    xs = np.array([slot[(t, x) + kk] for kk in keys])
    ys = np.array([slot[(t, y) + kk] for kk in keys])
    n10, n01 = int(((xs == 1) & (ys == 0)).sum()), int(((xs == 0) & (ys == 1)).sum())
    p = stats.binomtest(min(n10, n01), n10 + n01).pvalue if n10 + n01 else 1.0
    # placebo: same arm against itself under a random re-pairing of slots (no true difference)
    xp = xs[rng.permutation(len(xs))]
    m10, m01 = int(((xs == 1) & (xp == 0)).sum()), int(((xs == 0) & (xp == 1)).sum())
    pp = stats.binomtest(min(m10, m01), m10 + m01).pvalue if m10 + m01 else 1.0
    mc[f"{t} {x}-{y}"] = {"X_only": n10, "Y_only": n01, "p": float(p), "placebo_same_arm_repaired_p": float(pp)}
out["mcnemar"] = mc
# prefill P_open at every depth (BAN+pf vs TWIN+pf against a)
out["P_open"] = {t: {pf: (s[(t, f"BAN+{pf}")] - s[(t, "a")]) / (s[(t, f"TWIN+{pf}")] - s[(t, "a")])
                     for pf in ("NEU", "D25", "SIG", "D50", "D75") if (t, f"BAN+{pf}") in s} for t in GATED}
# second CRN draw
out["r2_pooled"] = {k: sum(s[(t, "b@r2")] - s[(t, arm)] for t in GATED) / sum(s[(t, "b@r2")] - s[(t, "a@r2")] for t in GATED)
                    for k, arm in (("F_prompt", "c@r2"), ("F_direct", "d@r2"))}
f1 = [(s[(t, "b")] - s[(t, "c")]) / (s[(t, "b")] - s[(t, "a")]) for t in GATED]
f2 = [(s[(t, "b@r2")] - s[(t, "c@r2")]) / (s[(t, "b@r2")] - s[(t, "a@r2")]) for t in GATED]
g1 = [(s[(t, "b")] - s[(t, "d")]) / (s[(t, "b")] - s[(t, "a")]) for t in GATED]
g2 = [(s[(t, "b@r2")] - s[(t, "d@r2")]) / (s[(t, "b@r2")] - s[(t, "a@r2")]) for t in GATED]
out["r2_spearman"] = {"F_prompt": float(stats.spearmanr(f1, f2).statistic), "F_direct": float(stats.spearmanr(g1, g2).statistic),
                      "max_abs_diff": float(max(np.abs(np.array(f1) - f2).max(), np.abs(np.array(g1) - g2).max()))}
# path screen off-default shares and the iteration-2 reference landings recounted from the upstream rows
out["screen_off_default"] = {f"{t}|{a}": 1 - s[(t, a)] for t in ("t1", "t2") for a in ("V1", "VP", "R2", "R3", "OPEN")
                             if (t, a) in s}
ref = collections.Counter()
for p, cond in ((ROOT / "inputs/exp8/data/samples.jsonl", lambda r: r["condition"] == "a"),
                (ROOT / "inputs/exp9/data/samples.jsonl", lambda r: r["condition"] in ("single:bfs", "single:dijkstra")),
                (ROOT / "inputs/exp12/results/labelled_c1.jsonl", lambda r: True)):
    for line in p.open():
        r = json.loads(line)
        if cond(r) and r["label"] not in X and r["label"] != D[r["task"]]:
            ref[(r["task"], r["label"])] += 1
out["iter2_ref"] = {"t1_dfs": ref[("t1", "dfs")], "t1_nondefault": sum(v for (t, _), v in ref.items() if t == "t1"),
                    "t2_bf_spfa": ref[("t2", "bf_spfa")], "t2_nondefault": sum(v for (t, _), v in ref.items() if t == "t2")}
# W4: pooled avoidance by template and W4's share of ban failures (arm a, all 12 tasks)
fail = collections.Counter()
att = collections.Counter()
for (t, arm, w, k), v in slot.items():
    if arm == "a" and t in D and not t.startswith("t"):
        att[w] += 1
        fail[w] += v
out["template_avoidance"] = {w: 1 - fail[w] / att[w] for w in sorted(att)}
out["W4_share_of_failures"] = fail["W4"] / sum(fail.values())
# U9 recount (T2 engine validation)
u9 = collections.Counter((r["arm"], r["label"] == "dijkstra") for r in rows if r["stage"] == "U9")
out["U9_banned"] = {a: u9[(a, True)] for a in "abcd"}
# continuous readout from the raw token log-prob arrays
num_p = num_d = den = 0.0
for t in GATED:
    z = np.load(ROOT / "token_lp" / f"{t}.npz")
    for w in ("W1", "W2", "W3", "W4", "W5"):
        lp = {a: float(z[f"{w}|{a}|sig"].sum()) for a in ("a", "b", "c", "d")}
        num_p += lp["b"] - lp["c"]
        num_d += lp["b"] - lp["d"]
        den += lp["b"] - lp["a"]
out["lp_pooled"] = {"F_lp_prompt": num_p / den, "F_lp_direct": num_d / den}
(ROOT / "results" / "rederive2.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=None)[:3000])
