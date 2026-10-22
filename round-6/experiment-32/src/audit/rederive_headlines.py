#!/usr/bin/env python3
"""Independent re-derivation of the README's headline numbers that audit/rederive.py does not cover.

Reads only raw rows (data/labels*.jsonl, data/judgements.jsonl, data/local_judgements.jsonl, cache/*.npz + indexes) and
recomputes through its own code (no import from src/ or analysis/). Every significant paired test is re-run on placebo
input (random within-pair swaps; a control-vs-control comparison) and must FAIL there. Writes results/rederive_headlines.json.
"""

import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def rows(rel):
    p = ROOT / rel
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []


def p_two_sided(b, n):
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, k) for k in range(0, min(b, n - b) + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def paired(a, b):
    """a, b: dict slot -> 0/1 outcome. Returns discordant counts and exact two-sided p."""
    ks = sorted(set(a) & set(b))
    bb = sum(1 for k in ks if a[k] == 1 and b[k] == 0)
    cc = sum(1 for k in ks if a[k] == 0 and b[k] == 1)
    return {"n": len(ks), "b": bb, "c": cc, "p": p_two_sided(bb, bb + cc)}


def swap_placebo(a, b, n_perm=2000, seed=3):
    """Randomly exchange the two arms inside each pair; share of permutations reaching p < 0.05 (should be ~<= 0.05)."""
    rng = random.Random(seed)
    ks = sorted(set(a) & set(b))
    hits = 0
    for _ in range(n_perm):
        x, y = {}, {}
        for k in ks:
            if rng.random() < 0.5:
                x[k], y[k] = b[k], a[k]
            else:
                x[k], y[k] = a[k], b[k]
        hits += paired(x, y)["p"] < 0.05
    return hits / n_perm


out = {}
lab = rows("data/labels.jsonl")
# ---------------------------------------------------------------- behaviour
twin = [r for r in lab if r["arm"] == "TWIN" and int(r["slot"]) < 10]
ban = [r for r in lab if r["arm"] == "BAN"]
beh = {}
for t in sorted({r["task"] for r in twin}):
    tc = Counter(r["label"] for r in twin if r["task"] == t and r["passed"])
    bc = Counter(r["label"] for r in ban if r["task"] == t and r["passed"])
    top = tc.most_common(1)[0]
    beh[t] = {"twin_correct": dict(tc), "default_share": round(top[1] / sum(tc.values()), 3), "ban_correct": dict(bc)}
out["behaviour"] = beh
tmap = {(r["task"], r["template"], int(r["slot"])): r["label"] for r in twin}
flips = Counter((r["task"], tmap.get((r["task"], r["template"], int(r["slot"]))), r["label"]) for r in ban)
out["T10_union_find_to_dfs_flips"] = flips[("T10", "union_find", "dfs")]
w4 = [r for r in ban if r["template"] == "W4"]
defaults = json.loads((ROOT / "predictions" / "commit1_defaults.json").read_text())["tasks"]
out["W4_attempts_default"] = f"{sum(r['label'] == defaults[r['task']]['default'] for r in w4)}/{len(w4)}"
# ---------------------------------------------------------------- instrument gate (numpy, own implementation)
try:
    import numpy as np

    idx = {r["state_id"]: r for r in rows("cache/states_index.jsonl")}
    z = np.load(ROOT / "cache" / "states_L20.npz")
    rec_ids = [r["expl_id"] for r in rows("cache/recon_index.jsonl")]
    P = np.load(ROOT / "cache" / "recon.npz")["P"]
    pos = {e: i for i, e in enumerate(rec_ids)}
    ex = {e["expl_id"]: e for e in rows("data/explanations.jsonl")}

    def unit(X):
        return X / np.linalg.norm(X, axis=-1, keepdims=True)

    def fve(ids, H, ref_ids):
        g = unit(np.stack([H[idx[ex[i]["state_id"]]["row"]] for i in ids]))
        p = unit(np.stack([P[pos[i]] for i in ids]))
        gr = unit(np.stack([H[idx[ex[i]["state_id"]]["row"]] for i in ref_ids]))
        num = np.mean(np.sum((p - g) ** 2, axis=1))          # unit-norm scale; the sqrt(d) factor cancels in the ratio
        den = np.mean(np.sum((gr - gr.mean(0)) ** 2, axis=1))
        return float(1 - num / den), float(np.mean(np.sum(p * g, axis=1)))

    gate = {}
    for conv, key in (("hs20", "H20"), ("hs21", "H21")):
        ref = [e for e, r in ex.items() if r.get("kind") == "REF" and r.get("gate_set") and r["convention"] == conv]
        gate[f"reference_{conv}"] = fve(ref, z[key], ref)
    ref21 = [e for e, r in ex.items() if r.get("kind") == "REF" and r.get("gate_set") and r["convention"] == "hs21"]
    task = [e for e, r in ex.items() if r.get("convention") == "hs21" and r.get("kind") in ("PREFILL", "GEN")
            and int(r["idx"]) <= 3]
    gate["task_all_hs21"] = fve(task, z["H21"], ref21)
    out["gate_fve_cos"] = gate
except (ImportError, FileNotFoundError, KeyError) as e:
    out["gate_fve_cos"] = f"not re-derived: {e!r}"
# ---------------------------------------------------------------- readout: prefill mention rate, N6 placebo
jud = rows("data/judgements.jsonl")
sidx = {r["state_id"]: r for r in rows("cache/states_index.jsonl")}
c2 = json.loads((ROOT / "predictions" / "commit2_readout.json").read_text())["tasks"]
men = defaultdict(lambda: [0, 0])
for j in jud:
    if j["mode"] != "EXPL":
        continue
    r = sidx[j["state_id"]]
    if r["kind"] != "PREFILL" or r["condition"] not in ("forced", "ban"):
        continue
    tgt = r.get("mode")
    men[r["condition"]][0] += tgt in (j.get("mentioned_any") or [])
    men[r["condition"]][1] += 1
out["prefill_mentions_named_algorithm"] = {k: f"{v[0]}/{v[1]}" for k, v in men.items()}
expl = defaultdict(list)
text = {}
for j in jud:
    if j["mode"] == "EXPL":
        expl[j["state_id"]].append(j)
    else:
        text[(j["mode"], j["text_id"])] = j["resolved"]
labmap = {r["sample_id"]: r for r in lab}
units = []
for sid, r in sidx.items():
    if r["kind"] != "GEN" or not r.get("mixed") or not c2.get(r["task"], {}).get("regate_pass", True):
        continue
    L = labmap.get(r["sample_id"])
    if L is None:
        continue
    tid = f"{r['task']}|{r['condition']}|{r.get('mode') or '-'}|{r['template']}|{r['position']}|{r['slot']}"
    es = sorted(expl.get(sid, []), key=lambda e: int(e["expl_id"].split("#")[-1]))[:3]
    if not es or text.get(("PREDICT", tid)) is None:
        continue
    units.append({"key": sid, "sample": r["sample_id"], "g": int(r["position"][1:]),
                  "x": int(sum(e["resolved"] == L["label"] for e in es) >= 2),
                  "y": int(text[("PREDICT", tid)] == L["label"]), "name": text.get(("NAME", tid))})
first = {}
for u in sorted(units, key=lambda u: u["g"]):
    if u["name"] not in (None, "none_named", "other", "unresolved") and u["sample"] not in first:
        first[u["sample"]] = u["g"]
sel = [u for u in units if u["g"] < first.get(u["sample"], 99)]
A = {u["key"]: u["x"] for u in sel}
B = {u["key"]: u["y"] for u in sel}
out["N6"] = paired(A, B) | {"nla_acc": round(sum(A.values()) / len(A), 3), "predict_acc": round(sum(B.values()) / len(B), 3),
                            "placebo_swap_share_p_lt_05": swap_placebo(A, B)}
# ---------------------------------------------------------------- exploratory causal headline numbers
cx = rows("data/labels_causal_extra.jsonl") + rows("data/labels_causal_extra2.jsonl")
c3 = json.loads((ROOT / "predictions" / "commit3_causal.json").read_text())
Y = {p["task"]: p["Y"] for p in c3["causal_plan"]}
cells = defaultdict(dict)
for r in cx:
    cells[(r["task"], r["cell"])][(r["template"], int(r["slot"]))] = int(bool(r["passed"]) and r["label"] == Y[r["task"]])
C0 = {t: {(r["template"], int(r["slot"])): int(bool(r["passed"]) and r["label"] == Y[t])
          for r in lab if r["task"] == t and r["arm"] == "TWIN" and int(r["slot"]) < 10} for t in Y}


def pooled(t, kind):
    d = dict(cells.get((t, f"EXP_GEN_{kind}_x8"), {}))
    d.update(cells.get((t, f"REP_GEN_{kind}_x8"), {}))
    return d


exp = {}
for t in ("T06", "T05"):
    E, R = pooled(t, "EDIT"), pooled(t, "RAND")
    exp[t] = {"edit_x8_vs_C0": paired(E, C0[t]), "edit_x8_Y_share": round(sum(E.values()) / len(E), 3),
              "C0_Y_share_slots0_9": round(sum(C0[t].values()) / len(C0[t]), 3),
              "replication_slots6_9_vs_C0": paired(cells.get((t, "REP_GEN_EDIT_x8"), {}), C0[t]),
              "edit_vs_rand_x8": paired(E, R),
              "edit_vs_unrel_x8": paired(cells.get((t, "EXP_GEN_EDIT_x8"), {}), cells.get((t, "EXP2_GEN_UNREL_x8"), {})),
              "edit_vs_rtm_x8": paired(cells.get((t, "EXP_GEN_EDIT_x8"), {}), cells.get((t, "EXP2_GEN_RTM_x8"), {})),
              "edit_x16_vs_C0": paired(cells.get((t, "EXP2_GEN_EDIT_x16"), {}), C0[t]),
              "placebo_rand_x8_vs_C0": paired(R, C0[t]),
              "placebo_swap_share_p_lt_05": swap_placebo(E, C0[t])}
exp["T10_dim_x16_vs_C0"] = paired(cells.get(("T10", "EXP2_GEN_DIM_x16"), {}), C0["T10"])
exp["T10_placebo_rand_x16_vs_C0"] = paired(cells.get(("T10", "EXP2_GEN_RAND_x16"), {}), C0["T10"])
out["exploratory_causal"] = exp
# ---------------------------------------------------------------- local positive control
lj = rows("data/local_judgements.jsonl")
lidx = {r["state_id"]: r for r in rows("cache/local_states_index.jsonl")}
by = defaultdict(list)
for e in lj:
    by[e["state_id"]].append(e)
loc = {}
for cond in ("forced", "ban"):
    for k in ("NAME", "SENT"):
        sts = [s for s, r in lidx.items() if r["condition"] == cond and r["position"] == k]
        m = [int(sum(lidx[s]["mode"] in (e.get("mentioned_any") or []) for e in by[s]) >= 2) for s in sts]
        pl = [int(sum(e["resolved"] == lidx[s]["mode"] for e in by[s]) >= 2) for s in sts]
        loc[f"{cond}|{k}"] = {"n": len(sts), "mentioned": round(sum(m) / len(m), 3), "planned": round(sum(pl) / len(pl), 3)}
out["local_control"] = loc
(ROOT / "results" / "rederive_headlines.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1)[:6000])
