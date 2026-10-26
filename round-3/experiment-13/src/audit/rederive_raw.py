#!/usr/bin/env python3
"""Second independent audit of the headline numbers, reading only the RAW per-sample files (data/labels/<arm>.jsonl,
data/raw/<arm>.jsonl), the committed forecasts (inputs to scoring) and raw FRLP program scores.  No project module is
imported; logistic regression, smoothing, log scores and FRLP cells are re-implemented here (numpy only).
Placebos: (a) template labels shuffled within task -> the template LR test must FAIL (p > 0.05);
(b) ban landings shuffled across tasks -> family wins must collapse.
Usage: python audit/rederive_raw.py   (prints a table and writes results/rederive_raw.json)"""

import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parent.parent
rd = lambda p: [json.loads(x) for x in Path(p).read_text().splitlines() if x.strip()]
fc = json.loads((R / "predictions/forecasts.json").read_text())["tasks"]
lab = {a: rd(R / f"data/labels/{a}.jsonl") for a in ["ban", "oneshot", "bandpatch", "rand", "hf_twin", "twin"]}
P4 = ["SUBTRACT", "LADDER", "ASSOCIATE", "PROXIMITY"]
out = {}


def avoid(rows, t, D, arm=None):
    a = [r["label"] for r in rows if r["task"] == t and r["label"] != "invalid" and (arm is None or r["arm"] == arm)]
    return (sum(x != D for x in a) / len(a)) if a else None


def p_s(raw, S):  # frozen smoothing re-implemented: 0.93 raw + 0.05 uniform(S) + 0.02 other
    u = {k: (1 / len(S) if k in S else 0.0) for k in S + ["other"]}
    raw = raw if raw is not None else u
    return {k: 0.93 * raw.get(k, 0.0) + 0.05 * u[k] + (0.02 if k == "other" else 0.0) for k in u}


ev = {}
for t, F in fc.items():
    D, S = F["D"], F["S"]
    att = [r["label"] for r in lab["ban"] if r["task"] == t and r["label"] != "invalid"]
    nb = [(x if x in S else "other") for x in att if x != D]
    ev[t] = {"avoid": len(nb) / len(att), "gate": len(nb) / len(att) >= 0.5 and len(nb) >= 20, "nb": nb,
             "dis": F["disagreeing"], "S": S}
    for f in P4 + ["UNIFORM"]:
        raw = F["families"][f]["p_raw"]
        ps = p_s(raw, S)
        ev[t][f] = sum(math.log(ps[x]) for x in nb) / len(nb) if nb else None
        ev[t][f + "_def"] = raw is not None
gated = [t for t in ev if ev[t]["gate"]]
out["ban_avoidance"] = {t: round(ev[t]["avoid"], 4) for t in ev}
out["gated"] = gated
out["realised_modal"] = {t: Counter(ev[t]["nb"]).most_common(1)[0][0] for t in gated}


def wins(tasks, defined_only=False, src=None):
    w = Counter()
    for t in tasks:
        ls = {f: ev[t][f] for f in P4} if src is None else src[t]
        for f in P4:
            if defined_only and not ev[t][f + "_def"]:
                continue
            if ls[f] - max(ls[g] for g in P4 if g != f) >= 0.10:
                w[f] += 1
    return {f: w[f] for f in P4}


dis = [t for t in gated if ev[t]["dis"]]
out["frozen_wins"] = wins(dis)
out["defined_only_wins"] = wins(dis, True)
out["mean_ls_minus_uniform_gated"] = {f: round(float(np.mean([ev[t][f] - ev[t]["UNIFORM"] for t in gated])), 4)
                                      for f in P4}
out["oneshot_avoidance_gated"] = {t: avoid(lab["oneshot"], t, fc[t]["D"]) for t in gated}
out["c2b_oneshot_eligible"] = sum(1 for t in gated if (out["oneshot_avoidance_gated"][t] or 0) >= 0.5)
out["bandpatch_avoidance"] = {t: avoid(lab["bandpatch"], t, fc[t]["D"]) for t in ["T03", "T10", "T05", "T13"]}
out["rand3_avoid_T03"] = avoid(lab["rand"], "T03", "full_sort", "rand3")
out["hf_twin_D_T03"] = 1 - avoid(lab["hf_twin"], "T03", "full_sort")
# placebo (b): score each task's forecasts against another task's ban landing (survivor index mapping)
rng = np.random.default_rng(3)
pw = Counter()
for _ in range(300):
    perm = list(rng.permutation(dis))
    while any(a == b for a, b in zip(perm, dis)):
        perm = list(rng.permutation(dis))
    src = {}
    for t, s in zip(dis, perm):
        S, Ss = ev[t]["S"], ev[s]["S"]
        lab_t = [("other" if x == "other" or Ss.index(x) >= len(S) else S[Ss.index(x)]) for x in ev[s]["nb"]]
        src[t] = {f: sum(math.log(p_s(fc[t]["families"][f]["p_raw"], S)[x]) for x in lab_t) / len(lab_t) for f in P4}
    for f, k in wins(dis, src=src).items():
        pw[f] += k / 300
out["placebo_task_shuffled_mean_wins"] = {f: round(pw[f], 3) for f in P4}


# template effect: hand-written IRLS logistic regression, LR test for template (df 4), real vs placebo
def fit_ll(X, y):
    b = np.zeros(X.shape[1])
    for _ in range(100):
        p = 1 / (1 + np.exp(-np.clip(X @ b, -30, 30)))
        g = X.T @ (y - p)
        H = X.T @ (X * (p * (1 - p))[:, None]) + 1e-6 * np.eye(X.shape[1])
        step = np.linalg.solve(H, g)
        b += step
        if np.abs(step).max() < 1e-10:
            break
    p = np.clip(1 / (1 + np.exp(-(X @ b))), 1e-12, 1 - 1e-12)
    return float(np.sum(y * np.log(p) + (1 - y) * np.log(1 - p)))


def lr_test(rows):
    by_t = defaultdict(list)
    for r in rows:
        by_t[r["task"]].append(r)
    keep = [t for t, xs in by_t.items() if 0 < np.mean([x["y"] for x in xs]) < 1]
    rs = [r for t in sorted(keep) for r in by_t[t]]
    T, W = sorted(keep), ["W1", "W2", "W3", "W4", "W5"]
    X0 = np.array([[1.0 if r["task"] == t else 0.0 for t in T] for r in rs])
    X1 = np.hstack([X0, np.array([[1.0 if r["template"] == w else 0.0 for w in W[1:]] for r in rs])])
    y = np.array([r["y"] for r in rs], dtype=float)
    lr = 2 * (fit_ll(X1, y) - fit_ll(X0, y))
    from scipy.stats import chi2
    return round(lr, 3), float(chi2.sf(lr, 4))


rows = [{"task": r["task"], "template": r["template"], "y": int(r["label"] == fc[r["task"]]["D"])}
        for r in lab["ban"] if r["label"] != "invalid"]
out["template_LR_real"] = lr_test(rows)
sh = []
for t in sorted({r["task"] for r in rows}):
    xs = [r for r in rows if r["task"] == t]
    ws = list(rng.permutation([r["template"] for r in xs]))
    sh += [dict(r, template=w) for r, w in zip(xs, ws)]
out["template_LR_placebo_shuffled"] = lr_test(sh)
# FRLP fp32 cells from raw program scores + frozen set metadata (proposal counts, adherence)
sc = json.loads((R / "results/frlp_program_scores_fp32.json").read_text())
fp8 = {(c["task"], c["algorithm"]): c["L_corr"] for c in rd(R / "inputs/exp11/frlp_cells.jsonl")
       if c["variant"] == "main" and c["half"] == "all"}
lse = lambda v: float(np.max(v) + np.log(np.sum(np.exp(np.asarray(v) - np.max(v)))))
diffs, cells32, cells8 = [], {}, {}
for tdir in sorted((R / "inputs/bench").glob("*_*")):
    if not (tdir / "frlp_sets.json").exists():
        continue
    t = json.loads((tdir / "spec.json").read_text())["task"]
    for j, st in json.loads((tdir / "frlp_sets.json").read_text()).items():
        nk = {int(k): v for k, v in st["proposal_counts"].items()}
        N = sum(nk.values())
        w = [sc[p["program_id"]]["baseline"] - lse([math.log(n / N) + sc[p["program_id"]][f"F{k}"] for k, n in nk.items()])
             for p in st["programs"] if p["program_id"] in sc]
        if w and st["adherence"] > 0 and fp8.get((t, j)) is not None:
            lc = lse(w) - math.log(len(w)) + math.log(st["adherence"])
            diffs.append(lc - fp8[(t, j)])
            cells32.setdefault(t, {})[j], cells8.setdefault(t, {})[j] = lc, fp8[(t, j)]
out["frlp_n_cells"], out["frlp_median_abs_diff"] = len(diffs), round(float(np.median(np.abs(diffs))), 4)
out["frlp_max_abs_diff"] = round(float(np.max(np.abs(diffs))), 3)
out["frlp_tasks_argmax_unchanged"] = sum(max(cells32[t], key=cells32[t].get) == max(cells8[t], key=cells8[t].get) for t in cells32)
# descriptive C2b for the last iterated round (T06, T10): modal agreement + JS (base 2) vs the ban landing
chain = json.loads((R / "predictions/iterated_chain.json").read_text())


def js2(a, b):
    ks = sorted(set(a) | set(b))
    pa = np.array([a.get(k, 0) for k in ks], float) / sum(a.values())
    pb = np.array([b.get(k, 0) for k in ks], float) / sum(b.values())
    m = (pa + pb) / 2
    kl = lambda p: float(np.sum(p[p > 0] * np.log2(p[p > 0] / m[p > 0])))
    return 0.5 * kl(pa) + 0.5 * kl(pb)


c2 = {}
for t in ["T06", "T10"]:
    last = chain[t]["rounds"][-1]
    arm = "persistent" if last == 0 else f"iter{last}"
    S, D = fc[t]["S"], fc[t]["D"]
    v = Counter((x["label"] if x["label"] in S else "other") for x in rd(R / f"data/labels/{arm}.jsonl")
                if x["task"] == t and x["label"] not in ("invalid", D))
    b = Counter(ev[t]["nb"])
    c2[t] = {"arm": arm, "modal_veto": v.most_common(1)[0][0], "modal_ban": b.most_common(1)[0][0],
             "js": round(js2(v, b), 3)}
out["c2b_last_iterated_descriptive"] = c2
# re-emergence: D present in every executed chain round
every = 0
for t, ch in chain.items():
    arms = ["persistent" if r == 0 else f"iter{r}" for r in ch["rounds"]]
    every += all(any(x["task"] == t and x["label"] == fc[t]["D"] for x in rd(R / f"data/labels/{a}.jsonl"))
                 for a in arms)
out["tasks_D_in_every_round"] = f"{every}/{len(chain)}"
# veto fire and text-leak rates from the raw veto rows
for a in ["oneshot", "iter2"]:
    xs = rd(R / f"data/raw/{a}.jsonl")
    out[f"{a}_fire_rate"] = round(sum(x["n_vetoes"] > 0 for x in xs) / len(xs), 3)
    out[f"{a}_text_leak_rate"] = round(sum(bool(x["text_leak"]) for x in xs) / len(xs), 3)
# DISGUISE: banned-mechanism ban programs whose full completion names no alias / display name of D
raw_ban = {x["sample_id"]: x["text"] for x in rd(R / "data/raw/ban.jsonl")}
dg = {}
for tdir in sorted((R / "inputs/bench").glob("*_*")):
    if not (tdir / "spec.json").exists():
        continue
    sp = json.loads((tdir / "spec.json").read_text())
    t = sp["task"]
    if t not in fc:
        continue
    D = fc[t]["D"]
    names = [c["display_name"].lower() for c in sp["catalogue"] if c["mode"] == D] + \
        [a.lower() for a in sp["aliases"].get(D, [])]
    ids = [x["sample_id"] for x in lab["ban"] if x["task"] == t and x["label"] == D]
    if ids:
        dg[t] = round(sum(not any(n in raw_ban[i].lower() for n in names) for i in ids) / len(ids), 3)
out["disguise_share_min_max"] = [min(dg.values()), max(dg.values())]
spend = sum(json.loads(x).get("cost") or 0 for x in (R / "logs/openrouter_spend.jsonl").read_text().splitlines() if x)
out["judge_spend_usd"] = round(spend, 4)
(R / "results/rederive_raw.json").write_text(json.dumps(out, indent=1))
for k, v in out.items():
    print(f"{k}: {v}")
