#!/usr/bin/env python3
"""Short headline re-derivation from RAW per-row files (not the aggregated result fields), stdlib only.

Separate code path from eval.py/src and from audit/rederive.py. Headlines checked:
  0a  L0 condition-MLP pair-prompt means (8.144 / 7.408) and held-out means (0.0) from raw validation margins
  0b  Qwen3-8B fork toward BFS: 29 written, 5 correct, pass 0.20 vs base 0.83, DAS:random discordance 5:0 (p 0.0625)
  0c  highest-entropy arm hits the fork on 44/44, 32/39, 21/39, 2/50, 0/37 slots
  0e  15-alias Spearman -0.61 and exact p 0.0093 at k 15
Placebos that must FAIL: shuffled point labels (0e), a non-condition node (0a), random dose positions (0c).
    python -I audit/headline_rederive.py   ->   audit/headline_rederive.json
"""
import array
import ast
import itertools
import json
import math
import os
import random
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEPS = Path(os.environ.get("S0_DEPS_DIR", ROOT.parents[2] / "round-8" / "."))
NAMES = {"circ": ("art_18XvfcJJZi1O", "experiment-41/src"), "das": ("art_e-_q5mSJGrSb", "experiment-40/src"),
         "fork": ("art_vnyi0Fm5SyNH", "experiment-39/src"), "tp": ("art_R-HSmXq2t97f", "experiment-44/src")}


def art(key):
    for base in (DEPS, ROOT.parent):
        for n in NAMES[key]:
            if (base / n).is_dir():
                return base / n
    return DEPS / NAMES[key][1]


def jl(p):
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


out, ok = {}, []

# ---- 0a: raw validation margins, d = node margin - mean of its 50 matched random components
rows = jl(art("circ") / "data/validation_rows_C1forced.jsonl")
for mode, exp_pair in (("ablate", 8.144148281097412), ("steer", 7.407574213027954)):
    def d_of(r, node):
        rnd = [v for k, v in r["res"].items() if k.startswith(f"{mode}|{node}|r")]
        return r["res"][f"{mode}|{node}|node"] - sum(rnd) / len(rnd)
    node = "mlp|L0|H-1|COND"
    pair = [d_of(r, node) for r in rows if not r["heldout"]]
    held = [d_of(r, node) for r in rows if r["heldout"]]
    out[f"0a_{mode}"] = {"pair_mean": sum(pair) / len(pair), "heldout_mean": sum(held) / len(held), "n": [len(pair), len(held)]}
    ok.append(abs(out[f"0a_{mode}"]["pair_mean"] - exp_pair) < 1e-6 and out[f"0a_{mode}"]["heldout_mean"] == 0.0)
    plac = [d_of(r, "head|L33|H14|DEC") for r in rows if r["heldout"]]
    out[f"0a_placebo_{mode}"] = {"node": "head|L33|H14|DEC", "heldout_mean": sum(plac) / len(plac),
                                 "failed_as_required": sum(plac) / len(plac) != 0.0}

# ---- 0b: raw generation labels at the Qwen3-8B fork (unit T10, site dec, target BFS)
lab = [r for r in jl(art("das") / "data/labels_T10.jsonl") if r.get("site") == "dec" and r.get("target_class") == "bfs"]
cell = lambda arm: {r["slot"]: r for r in lab if r["arm"] == arm}  # noqa: E731
das, base, rnd = cell("DAS"), cell("BASE"), cell("RAND")
corr = lambda r: r["label"] == "bfs" and r["passed"]  # noqa: E731
b = sum(1 for s in das if corr(das[s]) and not corr(rnd[s]))
c = sum(1 for s in das if corr(rnd[s]) and not corr(das[s]))
p_mc = min(1.0, 2 * sum(math.comb(b + c, i) for i in range(min(b, c) + 1)) / 2 ** (b + c)) if b + c else 1.0
out["0b"] = {"n": len(das), "written_bfs": sum(1 for r in das.values() if r["label"] == "bfs"),
             "correct_bfs": sum(1 for r in das.values() if corr(r)), "pass_das": sum(r["passed"] for r in das.values()) / len(das),
             "pass_base": sum(r["passed"] for r in base.values()) / len(base), "das_vs_random": [b, c], "mcnemar_p": p_mc}
ok.append([out["0b"][k] for k in ("written_bfs", "correct_bfs")] == [29, 5] and abs(out["0b"]["mcnemar_p"] - 0.0625) < 1e-12
          and round(out["0b"]["pass_das"], 2) == 0.20 and round(out["0b"]["pass_base"], 2) == 0.83)

# ---- 0c: raw rows. For every twin slot that reaches the fork, is the position the A7 arm doses (the highest-entropy
# position, fixed from the twin's own entropies) the twin's fork position?
smp = jl(art("fork") / "data/samples.jsonl")
twin = {(r["unit"], r["slot"]): r for r in smp if r.get("arm") == "A0" and r.get("stage") == "S0" and r.get("reached_decision")}
a7pos = {(r["unit"], r["slot"]): set(r["schedule"]["fixed_pos"]["pos"]) for r in smp if r.get("arm") == "A7"}
rng = random.Random(7)
hits, plac = {}, {}
for u in ("G", "B3", "B6", "T10", "A3"):
    keys = [k for k in twin if k[0] == u]
    fork = lambda k: {twin[k]["decision_pos"]} | ({10, 11} if u == "T10" else set())  # noqa: E731
    hits[u] = [sum(1 for k in keys if a7pos.get(k, set()) & fork(k)), len(keys)]
    plac[u] = sum(1 for k in keys if {rng.randrange(64)} & fork(k))
out["0c_hits"] = hits
out["0c_placebo_random_position"] = {"hits": plac, "total": sum(plac.values()),
                                     "real_total": sum(h[0] for h in hits.values()),
                                     "failed_as_required": sum(plac.values()) <= 0.1 * sum(h[0] for h in hits.values())}
ok.append(hits == {"G": [44, 44], "B3": [32, 39], "B6": [21, 39], "T10": [2, 50], "A3": [0, 37]})

# ---- 0e: raw npz -> alias-level g -> Spearman and its exact permutation p
def npy(zp, m):
    raw = zipfile.ZipFile(zp).read(m + ".npy")
    hl = int.from_bytes(raw[8:10], "little")
    hd = ast.literal_eval(raw[10:10 + hl].decode("latin1"))
    data = raw[10 + hl:]
    if hd["descr"].startswith("<U"):
        w = int(hd["descr"][2:]) * 4
        return [data[i:i + w].decode("utf-32-le").rstrip("\x00") for i in range(0, len(data), w)]
    a = array.array("d" if hd["descr"] == "<f8" else "q")
    a.frombytes(data)
    return list(a)


def rk(x):
    s = sorted(range(len(x)), key=x.__getitem__)
    r, i = [0.0] * len(x), 0
    while i < len(s):
        j = i
        while j + 1 < len(s) and x[s[j + 1]] == x[s[i]]:
            j += 1
        for t in s[i:j + 1]:
            r[t] = (i + j) / 2 + 1
        i = j + 1
    return r


def rho(x, y):
    a, b_ = rk(x), rk(y)
    ma, mb = sum(a) / len(a), sum(b_) / len(b_)
    return sum((u - ma) * (v - mb) for u, v in zip(a, b_)) / math.sqrt(
        sum((u - ma) ** 2 for u in a) * sum((v - mb) ** 2 for v in b_))


tp = art("tp") / "cache/states"
geo, labels = npy(tp / "geo_C6_nf4.npz", "geo_k15"), npy(tp / "geo_C6_nf4.npz", "labels")
if (tp / "smean_C6_nf4.npz").exists():
    kind, grp = npy(tp / "smean_C6_nf4.npz", "kind"), npy(tp / "smean_C6_nf4.npz", "group")
else:   # published copy without the 181 MB states file: the vendored index of the same rows
    _ix = json.loads((ROOT / "inputs/forced_index_C6_nf4.json").read_text())
    kind, grp = _ix["kind"], _ix["group"]
alias = [int(g) % 3 for g, k in zip(grp, kind) if k == "forced"]
banned, nonb = ["bfs", "dfs", "iddfs", "astar", "gbfs"], ["bibfs", "dijkstra_unit", "idastar", "jps", "biastar"]
overlap = [1, 1, 1, 0, 0, 0, 1, 2, 3, 0, 0, 0, 1, 1, 1]   # committed primary vectors (predictions/commit_s0e.json)


def g_alias(lab, ali):
    bi = {b_: [i for i in range(300) if lab[i] == b_] for b_ in banned}
    g = []
    for a_ in nonb:
        for j in range(3):
            ii = [i for i in range(300) if lab[i] == a_ and ali[i] == j]
            g.append(min(sum(geo[i * 300 + t] for i in ii for t in bi[b_]) / (len(ii) * len(bi[b_])) for b_ in banned))
    return g


null = []
for p2 in range(15):
    for p3 in range(15):
        if p3 == p2:
            continue
        rest = [i for i in range(15) if i not in (p2, p3)]
        for zeros in itertools.combinations(rest, 6):
            v = [1] * 15
            v[p2], v[p3] = 2, 3
            for z in zeros:
                v[z] = 0
            null.append(v)
gr = list(range(15))
null_r = sorted(rho(gr, v) for v in null)
pval = lambda r: sum(1 for v in null_r if v <= r + 1e-12) / len(null_r)  # noqa: E731
r15 = rho(g_alias(labels, alias), overlap)
out["0e"] = {"rho_k15": r15, "p_exact": pval(r15), "n_assignments": len(null)}
ok.append(abs(r15 - (-0.6068480408008414)) < 1e-9 and abs(out["0e"]["p_exact"] - 0.009324009324009324) < 1e-12)
pts = list(zip(labels, alias))
rej = 0
for _ in range(100):
    sh = pts[:]
    rng.shuffle(sh)
    rej += pval(rho(g_alias([s[0] for s in sh], [s[1] for s in sh]), overlap)) < 0.05
out["0e_placebo_shuffled_labels"] = {"reject_share": rej / 100, "failed_as_required": rej / 100 <= 0.10}
out["all_headlines_match"] = all(ok)
out["placebos_failed_as_required"] = sum(1 for k, v in out.items() if "placebo" in k and isinstance(v, dict)
                                         and v.get("failed_as_required"))
(ROOT / "audit/headline_rederive.json").write_text(json.dumps(out, indent=1))
print(json.dumps({k: out[k] for k in ("0a_ablate", "0a_steer", "0b", "0c_hits", "0e", "0e_placebo_shuffled_labels",
                                      "0c_placebo_random_position", "all_headlines_match", "placebos_failed_as_required")}, indent=1))
