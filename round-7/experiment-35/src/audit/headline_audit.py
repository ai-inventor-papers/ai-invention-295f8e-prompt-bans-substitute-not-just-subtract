#!/usr/bin/env python3
"""Independent audit of the headline numbers NOT already recomputed from raw rows by src/rederive.py.
Reads only raw files (data/*.jsonl, cache/tf/*.npz logits, inputs/iter6_exp30 rows) plus the committed teacher-forced
margins; shares no code with src/ (own softmax, own rank correlation, own exact tests). Placebos must FAIL.
Writes results/headline_audit.json."""

import json
import math
import random
from itertools import permutations
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CATS = {"B3": ["kruskal", "prim_heap", "prim_array", "boruvka"],
        "A3": ["two_pointers", "prefix_suffix_max", "monotonic_stack", "peak_split"],
        "B6": ["sort_compare", "hash_count", "fixed_count_array"]}
AMIN = {"B3": "prim_heap", "A3": "two_pointers", "B6": "fixed_count_array"}
DEF = {"B3": "kruskal", "A3": "prefix_suffix_max", "B6": "sort_compare", "T1": "bfs", "T2": "dijkstra",
       "T10": "union_find", "T03": "full_sort"}
W = ("W1", "W2", "W3", "W4", "W5")


def jl(p):
    return [json.loads(l) for l in open(p) if l.strip()]


def mcn(b, c):
    n = b + c
    return 1.0 if n == 0 else sum(math.comb(n, k) for k in range(b, n + 1)) / 2 ** n


def ranks(x):
    o = sorted(range(len(x)), key=lambda i: x[i])
    r = [0.0] * len(x)
    i = 0
    while i < len(o):
        j = i
        while j + 1 < len(o) and x[o[j + 1]] == x[o[i]]:
            j += 1
        for k in range(i, j + 1):
            r[o[k]] = (i + j) / 2
        i = j + 1
    return r


def pearson(a, b):
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    den = math.sqrt(sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b))
    return num / den if den else 0.0


def spearman(a, b):
    return pearson(ranks(a), ranks(b))


def entropy(p):
    return -sum(x * math.log2(x) for x in p if x > 0)


def main():
    labs = {r["sid"]: r for r in jl(ROOT / "data" / "labels.jsonl")}
    jud = {r["sid"]: r["label"] for r in jl(ROOT / "data" / "judge_labels.jsonl") if r.get("label")}
    lab = lambda s: (jud.get(s, labs[s]["label"]) if labs[s]["label"] == "disputed" else labs[s]["label"])  # noqa
    rows = [dict(r, y=lab(r["sid"]), ok=labs[r["sid"]]["passed"]) for r in jl(ROOT / "data" / "samples_raw.jsonl")]
    out = {}
    # (1) H(A | fork class): pi_1 from the raw teacher-forced logits (own softmax), counts from raw continuation rows
    full = {r["sid"]: r["label"] for r in jl(ROOT / "data" / "continuation_labels.jsonl")}
    conts = jl(ROOT / "data" / "continuations.jsonl")
    forks = json.loads((ROOT / "results" / "forks.json").read_text())
    for u in CATS:
        C = CATS[u] + ["other"]
        covs = {c["id"]: c["cov"] for c in forks[u]["opening"]["clusters"]}
        joint = {}
        for cid, cov in covs.items():
            z = np.load(ROOT / "cache" / "tf" / f"{u}_{cid}.npz")
            pis = []
            for w in W:
                x = z[f"zf_{w}"].astype(np.float64)
                e = np.exp(x - x.max())
                pis.append(e / e.sum())
            pi = np.mean(pis, 0)
            cnt = {}
            for r in conts:
                if r["unit"] == u and r.get("cluster") == cid and r.get("kind") in ("tok", "resid"):
                    y = r.get("label") or full.get(r["cid"]) or "other"
                    key = r["tok"] if r["kind"] == "tok" else "resid"
                    cnt.setdefault(key, [0] * len(C))[C.index(y) if y in C else len(C) - 1] += 1
            toks = [t for t in cnt if t != "resid"]
            mass = {t: float(pi[int(t)]) for t in toks}
            mass["resid"] = max(0.0, 1 - sum(mass.values()))
            for t, v in cnt.items():
                n = sum(v)
                p = [x / n for x in v]
                cls = max(range(len(C)), key=lambda i: p[i])
                acc = joint.setdefault(cls, [0.0] * len(C))
                for i in range(len(C)):
                    acc[i] += cov / sum(covs.values()) * mass[t] * p[i]
        tot = sum(sum(v) for v in joint.values())
        out[f"{u}|H_bits"] = sum(sum(v) / tot * entropy([x / sum(v) for x in v]) for v in joint.values() if sum(v))
    # (2) top-k 10 token identity in the sweep
    sw = {(r["unit"], r["cell"], r["template"], r["slot"]): r for r in rows if r["arm"] == "SWEEP"}
    same = [sw[(u, c.replace("_k10", "_p1"), w, s)]["token_ids"] == r["token_ids"]
            for (u, c, w, s), r in sw.items() if c.endswith("_k10")]
    out["topk10_identical"] = [sum(same), len(same)]
    # (3) per-slot replay accuracy (committed per-slot replay vs observed label), on-opening slots only
    pv = json.loads((ROOT / "results" / "predictions_view.json").read_text())
    acc = {}
    for (u, c, w, s), r in sw.items():
        pr = pv["units"][u]["replay"].get(f"{w}|{s}|{c}", {}).get("pred")
        if pr and not str(pr).startswith("rest:"):
            a = acc.setdefault(u, [0, 0])
            a[0] += pr == r["y"]
            a[1] += 1
    out["replay_accuracy_pooled"] = {u: a[0] / a[1] for u, a in acc.items()}
    # (4) S4(b): exchange vs padding twin (and placebo: arm labels swapped within each slot at random)
    rng = random.Random(1)
    for u in CATS:
        arm = {}
        for r in rows:
            if r["unit"] == u and r["arm"] == "S4B":
                arm.setdefault(r["cell"], {})[r["slot"]] = r["y"] == AMIN[u]
        ks = sorted(set(arm["EXCH"]) & set(arm["FORCEDPAD"]))
        b = sum(arm["EXCH"][k] and not arm["FORCEDPAD"][k] for k in ks)
        c = sum(arm["FORCEDPAD"][k] and not arm["EXCH"][k] for k in ks)
        out[f"{u}|S4B_exchange_vs_pad"] = {"b": b, "c": c, "p": mcn(b, c),
                                           "exch_share": sum(arm["EXCH"].values()) / len(arm["EXCH"]),
                                           "pad_share": sum(arm["FORCEDPAD"].values()) / len(arm["FORCEDPAD"])}
        sig = 0
        for _ in range(1000):
            bb = cc = 0
            for k in ks:
                x, y = arm["EXCH"][k], arm["FORCEDPAD"][k]
                if rng.random() < 0.5:
                    x, y = y, x
                bb += x and not y
                cc += y and not x
            sig += mcn(bb, cc) < 0.05
        out[f"{u}|S4B_placebo_sig_rate"] = sig / 1000
    # (5) S4(a): Spearman(d margin, d share) over 8 directions + the twin (0, 0), exact lower-tail p; placebo = the
    #     observed shares assigned to random directions (expected rejection rate about 0.05)
    for u in CATS:
        tw = [r["y"] == AMIN[u] for r in rows if r["unit"] == u and r["arm"] == "S4A" and r["cell"] == "twin0"]
        s0 = sum(tw) / len(tw)
        dm, ds = [0.0], [0.0]
        for d, v in pv["units"][u]["s4"]["push"].items():
            pr = [r["y"] == AMIN[u] for r in rows if r["unit"] == u and r["arm"] == "S4A" and r["cell"] == f"push{d}"]
            dm.append(v["d_margin"])
            ds.append(sum(pr) / len(pr) - s0)
        rho = spearman(dm, ds)
        perms = [spearman(dm, [ds[i] for i in p]) for p in permutations(range(len(ds)))]
        p_lo = sum(x <= rho + 1e-12 for x in perms) / len(perms)
        rej = sum(sum(x <= q + 1e-12 for x in perms) / len(perms) < 0.05 for q in perms[::997]) / len(perms[::997])
        out[f"{u}|S4A_spearman"] = {"rho": rho, "p_lower": p_lo, "placebo_rejection_rate": rej}
    # (6) collapsed T 1.3 check and engine check (raw rows of both iterations)
    for t in ("T1", "T2", "T10", "T03"):
        rr = [r for r in rows if r["unit"] == t and r["arm"] == "T13CHK"]
        out[f"{t}|T13_off_default"] = [sum(r["y"] not in (DEF[t], "invalid", "other", "disputed") for r in rr), len(rr)]
    six = {(r["task"], r["template"], r["slot"]): r for r in jl(ROOT / "inputs" / "iter6_exp30" / "data" /
                                                                 "samples_raw.jsonl") if r["arm"] == "TWIN"}
    lab6 = {r["sample_id"]: r["label"] for r in jl(ROOT / "inputs" / "iter6_exp30" / "data" / "labels.jsonl")}
    for t in ("T2", "T03"):
        pr = [(r, six[(t, r["template"], r["slot"])]) for r in rows if r["unit"] == t and r["arm"] == "TWIN6"]
        out[f"{t}|engine_label_agreement"] = sum(lab6[o["sample_id"]] == r["y"] for r, o in pr) / len(pr)
    # (7) collapsed margins straight from the raw per-token numbers (path margins from the path log-probability)
    col = json.loads((ROOT / "predictions" / "collapsed_raw.json").read_text())
    for t, r in col.items():
        if r["alt_class_tokens"]:
            a = sum(r["pi1"][str(x)] for x in r["alt_class_tokens"])
            out[f"{t}|margin"] = math.log(1 - a) - math.log(a)
        else:
            lp = r["path"]["logp_segment"]
            out[f"{t}|margin"] = math.log(-math.expm1(lp)) - lp
    # (8) the committed cell predictions, recomputed from the raw logits (own softmax / top-k) and raw label counts
    #     (labels as they stood at COMMIT #2, i.e. before any judge adjudication)
    def dist(x, T, k):
        x = x / T
        if k:
            keep = np.argsort(x)[-k:]
            y = np.full_like(x, -np.inf)
            y[keep] = x[keep]
            x = y
        e = np.exp(x - x.max())
        return e / e.sum()
    raw_lab = {s: r["label"] for s, r in labs.items()}
    maxdiff = 0.0
    for u in CATS:
        C = CATS[u] + ["other"]
        A = C.index(AMIN[u])
        cl = forks[u]["opening"]["clusters"]
        tw = [r for r in rows if r["unit"] == u and r["arm"] == "TWIN"]
        off = [r for r in tw if not any(r["token_ids"][:len(c["O"])] == c["O"] for c in cl)]
        src = off if len(off) >= 10 else tw
        q = sum(raw_lab[r["sid"]] == AMIN[u] for r in src) / len(src)
        ph = {}
        for c in cl:
            cnt = {}
            for r in conts:
                if r["unit"] == u and r.get("cluster") == c["id"] and r.get("kind") in ("tok", "resid"):
                    y = r.get("label") or full.get(r["cid"]) or "other"
                    key = r["tok"] if r["kind"] == "tok" else "resid"
                    v = cnt.setdefault(key, [0, 0])
                    v[0] += y == AMIN[u]
                    v[1] += 1
            ph[c["id"]] = cnt
        for T in (0.3, 0.7, 1.0, 1.3):
            for sname, k in (("p1", 0), ("k10", 10)):
                vals = []
                for w in W:
                    tot, wsum = 0.0, 0.0
                    for c in cl:
                        z = np.load(ROOT / "cache" / "tf" / f"{u}_{c['id']}.npz")
                        Zo, zf = z[f"Zo_{w}"].astype(np.float64), z[f"zf_{w}"].astype(np.float64)
                        wc = float(np.prod([dist(Zo[i], T, k)[t] for i, t in enumerate(c["O"])]))
                        d = dist(zf, T, k)
                        cnt = ph[c["id"]]
                        toks = [t for t in cnt if t != "resid"]
                        F = sum(d[t] * cnt[t][0] / cnt[t][1] for t in toks)
                        rest = max(0.0, 1 - sum(d[t] for t in toks))
                        if "resid" in cnt:
                            F += rest * cnt["resid"][0] / cnt["resid"][1]
                        else:
                            F += rest * q
                        tot += wc * F
                        wsum += wc
                    vals.append(tot + (1 - min(wsum, 1.0)) * q)
                got = sum(vals) / len(vals)
                ref = pv["units"][u]["cells"][f"T{T}_{sname}"]["a_min"]
                out[f"{u}|pred|T{T}_{sname}"] = got
                maxdiff = max(maxdiff, abs(got - ref))
    out["committed_predictions_max_abs_diff"] = maxdiff
    (ROOT / "results" / "headline_audit.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
