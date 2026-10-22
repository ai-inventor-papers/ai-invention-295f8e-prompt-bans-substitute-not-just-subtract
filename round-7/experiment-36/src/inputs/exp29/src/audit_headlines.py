#!/usr/bin/env python3
"""Independent headline audit (stdlib only; reads the RAW rows and labels directly -- not data/samples.jsonl and not
any results/*.json -- and joins them with its own code). Recomputes: REPRO byte identity of engine a vs exp22;
E(a), E(d) at alpha 2 (exp22 rule, own implementation); the T10 screen-slot off-default rates of a vs d with an exact
McNemar test; and runs placebos (engine labels swapped at random within each paired slot; slot pairing permuted)
that must NOT be significant. Writes results/audit_headlines.json."""

import json
import math
import random
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEF = {"T10": "union_find", "T2": "dijkstra"}
CAT = {"T10": {"bfs", "dfs", "label_propagation", "union_find"}, "T2": {"bf_spfa", "bidijkstra", "dial", "dijkstra",
                                                                       "floyd"}}


def jl(p):
    with open(p) as f:
        return [json.loads(x) for x in f if x.strip()]


def rows_for(engine):
    lab = {}
    for l in jl(ROOT / "data" / "labels.jsonl"):
        lab[l["key"]] = l
    out = {}
    for r in jl(ROOT / "data" / "raw" / f"raw_{engine}.jsonl"):
        k = f"{engine}|{r['task']}|{r['template']}|{r['arm']}|{r['sample_id']}"
        if k in lab:
            out[(r["task"], r["template"], r["arm"], int(r["sample_id"]))] = (lab[k]["label"], bool(lab[k]["passed"]))
    if engine == "a":   # exp22's own rows, relabelled (data/iter4_relabelled.jsonl), fill every slot not re-run
        rel = {l["key"]: l for l in jl(ROOT / "data" / "iter4_relabelled.jsonl")}
        for r in jl(ROOT / "inputs" / "exp22" / "samples_raw.jsonl"):
            if r["task"] not in DEF:
                continue
            key = (r["task"], r["template"], r["arm"], int(r["sample_id"]))
            l = rel.get(f"{r['task']}|{r['template']}|{r['arm']}|{r['sample_id']}")
            if l and key not in out:
                out[key] = (l["label"], bool(l["passed"]))
    return out


def offd(lbl, t):
    return lbl in CAT[t] and lbl != DEF[t]


def share(cells, t):
    valid = [c for c in cells if c[0] not in ("invalid", "disputed")]
    k = sum(offd(c[0], t) for c in valid)
    return k, len(valid), (k / len(valid) if valid else 0.0), (sum(c[1] for c in cells) / len(cells) if cells else 0.0)


def escape_E(rows, t):
    tw = [v for (tt, w, a, k), v in rows.items() if tt == t and a == "TWIN" and k < 10]
    kt, nt, st, pt = share(tw, t)
    p0 = (kt + 0.5) / (nt + 1)
    conf = 0
    for s in range(9101, 9141):
        arm = f"POP_d{s}_a2.0"
        first = [v for (tt, w, a, k), v in rows.items() if tt == t and a == arm and k in (0, 1)]
        pooled = [v for (tt, w, a, k), v in rows.items() if tt == t and a == arm and 0 <= k <= 5]
        k1, n1, s1, p1 = share(first, t)
        if not (n1 and s1 - st >= 0.2 - 1e-12 and p1 >= 0.8 * pt - 1e-12) or len(pooled) <= len(first):
            continue
        k3, n3, s3, p3 = share(pooled, t)
        pv = sum(math.comb(n3, i) * p0 ** i * (1 - p0) ** (n3 - i) for i in range(k3, n3 + 1))
        conf += (s3 - st >= 0.2 - 1e-12 and pv < 0.05 and p3 >= 0.8 * pt - 1e-12)
    return conf / 40


def mcnemar_p(n10, n01):
    m = n10 + n01
    if m == 0:
        return 1.0
    return min(1.0, 2 * sum(math.comb(m, i) for i in range(0, min(n10, n01) + 1)) / 2 ** m)


def main():
    A, D = rows_for("a"), rows_for("d")
    out = {}
    # REPRO byte identity (raw token ids)
    ref = {(r["task"], r["template"], r["arm"], int(r["sample_id"])): r["token_ids"]
           for r in jl(ROOT / "inputs" / "exp22" / "samples_raw.jsonl") if r["task"] in DEF}
    mine = [r for r in jl(ROOT / "data" / "raw" / "raw_a.jsonl") if r["stage"] == "REPRO"]
    same = sum(r["token_ids"] == ref.get((r["task"], r["template"], r["arm"], int(r["sample_id"]))) for r in mine)
    out["repro_byte_identical"] = f"{same}/{len(mine)}"
    out["E_alpha2"] = {t: {"a": escape_E(A, t), "d": escape_E(D, t)} for t in DEF}
    # T10 screen-slot a vs d (CRN-paired)
    t = "T10"
    keys = [k for k in D if k[0] == t and k[2].startswith("POP_d") and k[2].endswith("_a2.0") and k[3] in (0, 1)
            and k in A and A[k][0] not in ("invalid", "disputed") and D[k][0] not in ("invalid", "disputed")]
    xa = [int(offd(A[k][0], t)) for k in keys]
    xd = [int(offd(D[k][0], t)) for k in keys]
    n10 = sum(1 for a, d in zip(xa, xd) if a and not d)
    n01 = sum(1 for a, d in zip(xa, xd) if d and not a)
    out["T10_screen_slots"] = {"n": len(keys), "a": sum(xa) / len(keys), "d": sum(xd) / len(keys), "n10": n10,
                               "n01": n01, "mcnemar_p": mcnemar_p(n10, n01)}
    rng = random.Random(11)
    ps_swap, ps_perm = [], []
    for _ in range(1000):
        b10 = b01 = 0
        for a, d in zip(xa, xd):
            if rng.random() < 0.5:
                a, d = d, a
            b10 += a and not d
            b01 += d and not a
        ps_swap.append(mcnemar_p(b10, b01))
        dp = xd[:]
        rng.shuffle(dp)
        c10 = sum(1 for a, d in zip(xa, dp) if a and not d)
        c01 = sum(1 for a, d in zip(xa, dp) if d and not a)
        ps_perm.append(mcnemar_p(c10, c01))
    out["placebo_engine_swap"] = {"frac_p_lt_0.05": sum(p < 0.05 for p in ps_swap) / len(ps_swap),
                                  "median_p": sorted(ps_swap)[len(ps_swap) // 2]}
    out["placebo_note"] = ("engine-swap placebo must be non-significant (~5% false positives); a permuted pairing keeps "
                           "the marginal rates, so it tests the pairing only (reported, not required to fail)")
    out["placebo_permuted_pairing"] = {"frac_p_lt_0.05": sum(p < 0.05 for p in ps_perm) / len(ps_perm),
                                       "median_p": sorted(ps_perm)[len(ps_perm) // 2]}
    (ROOT / "results" / "audit_headlines.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
