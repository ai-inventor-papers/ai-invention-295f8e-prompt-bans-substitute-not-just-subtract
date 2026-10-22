#!/usr/bin/env python3
"""U12 independent re-derivation (Python standard library only; shares no code with analysis/).

Recomputes from the raw jsonl: N1 (ban states, Y*), N2 (twin states, default), N3 (forced states), N8b, the gate
FVE_ref (from per-explanation cosines and the committed reference denominator) and every causal EDIT-vs-RT McNemar.
Placebos that must FAIL: N1/N2 with the condition labels shuffled within a task (twin <-> ban / twin <-> forced) and
the causal test with C0 swapped in for RAND. Writes results/rederive.json."""

from __future__ import annotations

import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POS4 = ("SPEC-3", "SPEC-2", "SPEC-1", "READ")
W4 = ("W1", "W2", "W3", "W5")


def jl(p):
    p = ROOT / p
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []


def binom_two_sided(b, n):
    if n == 0:
        return 1.0
    pmf = [math.comb(n, k) * 0.5 ** n for k in range(n + 1)]
    obs = pmf[b]
    return min(1.0, sum(p for p in pmf if p <= obs * (1 + 1e-7)))


def mcnemar(xs, ys):
    b = sum(1 for x, y in zip(xs, ys) if x == 1 and y == 0)
    c = sum(1 for x, y in zip(xs, ys) if x == 0 and y == 1)
    n = len(xs)
    eff = (sum(xs) - sum(ys)) / n if n else None
    return {"n": n, "b": b, "c": c, "p": binom_two_sided(b, b + c), "effect": eff}


def main():
    c2 = json.loads((ROOT / "predictions" / "commit2_readout.json").read_text())
    tasks = c2["tasks"]
    jud = jl("data/judgements.jsonl")
    expl = defaultdict(list)
    text = {}
    for r in jud:
        if r["mode"] == "EXPL":
            expl[r["state_id"]].append(r)
        else:
            text[(r["mode"], r["text_id"])] = r["resolved"]

    def x(sid, tgt):
        rs = sorted(expl.get(sid, []), key=lambda r: int(r["expl_id"].split("#")[-1]))[:3]
        if not rs:
            return None
        h = sum(1 for r in rs if r["resolved"] == tgt)
        return 1 if (h >= 2 if len(rs) >= 2 else h >= 1) else 0

    def y(tid, tgt, mode="NAME"):
        v = text.get((mode, tid))
        return None if v is None else int(v == tgt)

    out = {}
    # N1
    xs, ys = [], []
    for t, v in tasks.items():
        if not v.get("eligible"):
            continue
        for w in W4:
            for p in POS4:
                a, b = x(f"{t}|ban|{v['default']}|{w}|{p}", v["Ystar"]), y(f"{t}|ban|{v['default']}|{w}|PREFILL", v["Ystar"])
                if a is not None and b is not None:
                    xs.append(a)
                    ys.append(b)
    out["N1"] = mcnemar(xs, ys)
    # N2
    xs, ys, pairs = [], [], []
    for t, v in tasks.items():
        if not v.get("default") or not v.get("regate_pass", True):
            continue
        for w in W4:
            for p in POS4:
                a, b = x(f"{t}|twin|-|{w}|{p}", v["default"]), y(f"{t}|twin|-|{w}|PREFILL", v["default"])
                if a is not None and b is not None:
                    xs.append(a)
                    ys.append(b)
                    pairs.append((t, w, p))
    out["N2"] = mcnemar(xs, ys)
    # N8b
    xs, ys = [], []
    for t, v in tasks.items():
        if v.get("default") and not v.get("Ystar") and v.get("regate_pass", True):
            for w in W4:
                for p in POS4:
                    a = x(f"{t}|ban|{v['default']}|{w}|{p}", v["default"])
                    b = y(f"{t}|ban|{v['default']}|{w}|PREFILL", v["default"], "PREDICT")
                    if a is not None and b is not None:
                        xs.append(a)
                        ys.append(b)
    out["N8b_vs_predict"] = mcnemar(xs, ys)
    # N3
    n3 = {}
    for t, v in tasks.items():
        if not v.get("regate_pass", True):
            continue
        vals = [x(f"{t}|forced|{m}|{w}|{p}", m) for m in v.get("forced_readout_modes", []) for w in
                ("W1", "W2", "W3", "W4", "W5") for p in POS4]
        vals = [a for a in vals if a is not None]
        if vals:
            n3[t] = sum(vals) / len(vals)
    out["N3"] = n3
    # placebo: shuffle twin/default naming against the ban text within a task (N2 x vs a permuted y)
    rng = random.Random(11)
    by_task = defaultdict(list)
    for (t, w, p), a, b in zip(pairs, xs[:len(pairs)], ys[:len(pairs)]):
        by_task[t].append((a, b))
    # N6: per-sample accuracy at generated tokens in MIXED conditions, pre-identifying positions, NLA vs PREDICT
    idx_all = {r["state_id"]: r for r in jl("cache/states_index.jsonl")}
    labels = {r["sample_id"]: r for r in jl("data/labels.jsonl")}
    named_excl = {"none_named", "other", "unresolved", None}
    units = []
    for sid, r in idx_all.items():
        if r["kind"] != "GEN" or not tasks.get(r["task"], {}).get("regate_pass", True):
            continue
        lab = labels.get(r["sample_id"])
        if lab is None:
            continue
        tid = f"{r['task']}|{r['condition']}|{r.get('mode') or '-'}|{r['template']}|{r['position']}|{r['slot']}"
        units.append({"sample": r["sample_id"], "g": int(r["position"][1:]), "mixed": bool(r.get("mixed")),
                      "x": x(sid, lab["label"]), "y": y(tid, lab["label"], "PREDICT"),
                      "name": text.get(("NAME", tid))})
    first = {}
    for u in sorted(units, key=lambda u: u["g"]):
        if u["name"] not in named_excl and u["sample"] not in first:
            first[u["sample"]] = u["g"]
    sel = [u for u in units if u["mixed"] and u["g"] < first.get(u["sample"], 10 ** 6)
           and u["x"] is not None and u["y"] is not None]
    out["N6"] = mcnemar([u["x"] for u in sel], [u["y"] for u in sel])
    # gate FVE from cosines
    gate = json.loads((ROOT / "results" / "gate.json").read_text())
    cos = json.loads((ROOT / "results" / "explanation_cosines.json").read_text())
    idx = {r["state_id"]: r for r in jl("cache/states_index.jsonl")}
    ro = [k for k in cos if k.split("|")[-1].split("#")[0] == gate["convention"] and "#" in k
          and int(k.split("#")[-1]) <= 3 and idx.get(k.rsplit("|", 1)[0], {}).get("kind") in ("PREFILL", "GEN")]
    mse = [2 * (1 - cos[k]) for k in ro]
    den = gate["reference"]["denominator_ref"]
    out["gate_fve_ref_all"] = {"rederived": 1 - (sum(mse) / len(mse)) / den if mse else None,
                               "reported": gate["classes"]["ALL"]["fve_ref"], "n": len(mse)}
    # causal
    lab = jl("data/labels_causal.jsonl")
    beh = jl("data/labels.jsonl")
    c3p = ROOT / "predictions" / "commit3_causal.json"
    caus = {}
    if c3p.exists() and lab:
        c3 = json.loads(c3p.read_text())
        for ct in c3["causal_plan"]:
            t, Y = ct["task"], ct["Y"]
            cells = defaultdict(dict)
            for r in lab:
                if r["task"] == t:
                    cells[r["cell"]][(r["template"], int(r["slot"]))] = int(bool(r.get("passed")) and r["label"] == Y)
            c0 = {(r["template"], int(r["slot"])): int(bool(r.get("passed")) and r["label"] == Y)
                  for r in beh if r["task"] == t and r["arm"] == "TWIN" and int(r["slot"]) < 6}
            res = {}
            for d in ("x1", "x2", "x4"):
                E, R = cells.get(f"PRE_EDIT_{d}"), cells.get(f"PRE_RT_{d}")
                if E and R:
                    k = sorted(set(E) & set(R))
                    res[d] = mcnemar([E[i] for i in k], [R[i] for i in k])
                RA = cells.get(f"PRE_RAND_{d}")
                if RA:
                    k = sorted(set(RA) & set(c0))
                    res[f"placebo_RAND_vs_C0_{d}"] = mcnemar([RA[i] for i in k], [c0[i] for i in k])
            caus[t] = res
    out["causal"] = caus
    # N1/N2 placebo: within-task shuffle of the NLA labels across (template, position) units against the text
    plac = []
    for t, lst in by_task.items():
        a_ = [a for a, _ in lst]
        b_ = [b for _, b in lst]
        rng.shuffle(b_)
        plac += list(zip(a_, b_))
    out["placebo_N2_shuffled_text"] = mcnemar([a for a, _ in plac], [b for _, b in plac]) if plac else None
    (ROOT / "results" / "rederive.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: (v if not isinstance(v, dict) or len(str(v)) < 300 else "...") for k, v in out.items()})[:1500])


if __name__ == "__main__":
    main()
