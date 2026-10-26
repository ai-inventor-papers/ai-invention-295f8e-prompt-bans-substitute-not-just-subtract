#!/usr/bin/env python3
"""Independent re-derivation of the TP-B headlines (stdlib only; no project code). Reads data/labelled_v9_*.jsonl,
results/retrace.jsonl and the analysis JSONs, recomputes every headline count, rate, gap, Wilson and paired-Newcombe
interval, the Jonckheere-Terpstra statistic and its permutation p (own implementation), the N2 shares, the N5 sign
count and the verdicts, and runs three placebos that must fail:
  (1) a random swap of the lexical and mechanistic flags within programs -> pooled N1 gap about 0;
  (2) k labels permuted within a model -> JT p about uniform (< 10% of 200 runs below 0.05);
  (3) random survivor identities in N5 -> joint sign counts at chance.
(The fourth placebo, a tracer run on order-shuffled event streams, needs the tracer and lives in
 audit/placebo_shuffled_events.py.)
Usage: python audit/rederive.py  -> results/rederive.json
"""

import glob
import json
import math
import os
import random

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COARSE = {"bfs": "BFS", "dfs": "DFS", "iddfs": "ID", "astar": "HEUR", "gbfs": "HEUR", "bibfs": "BIDIR",
          "biastar": "BIDIR", "idastar": "ID", "jps": "HEUR", "dijkstra_unit": "BFS"}
LIT = ["bfs", "dfs", "iddfs", "astar", "gbfs"]
KORD = ["bfs", "dfs", "iddfs", "astar", "gbfs"]
Z = 1.959963984540054


def rj(p):
    with open(p) as fh:
        return json.load(fh)


def rl(p):
    out = []
    if not os.path.exists(p):
        return out
    with open(p) as fh:
        for ln in fh:
            ln = ln.strip()
            if ln:
                out.append(json.loads(ln))
    return out


def wilson(k, n):
    if n == 0:
        return (None, None)
    p = k / n
    den = 1 + Z * Z / n
    c = (p + Z * Z / (2 * n)) / den
    h = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / den
    return (max(0.0, c - h), min(1.0, c + h))


def newcombe_paired(a, b, c, d):
    n = a + b + c + d
    if n == 0:
        return (None, None, None)
    p1, p2 = (a + b) / n, (a + c) / n
    l1, u1 = wilson(a + b, n)
    l2, u2 = wilson(a + c, n)
    den = (a + b) * (c + d) * (a + c) * (b + d)
    phi = 0.0
    if den:
        num = a * d - b * c
        if num > 0:
            num = max(num - n / 2.0, 0.0)
        phi = num / math.sqrt(den)
    D = p1 - p2
    dl = math.sqrt(max(0.0, (p1 - l1) ** 2 - 2 * phi * (p1 - l1) * (u2 - p2) + (u2 - p2) ** 2))
    du = math.sqrt(max(0.0, (u1 - p1) ** 2 - 2 * phi * (u1 - p1) * (p2 - l2) + (p2 - l2) ** 2))
    return (D, max(-1.0, D - dl), min(1.0, D + du))


MECH = {"field": "runtime_class"}


def mech_class(r):
    """Primary (gate-failure fallback): the iteration-8 runtime label mapped through the coarse table; second
    column: the tracer v9 order class."""
    if MECH["field"] == "order_class":
        return r.get("order_class")
    lab = r.get("runtime_label")
    if not r.get("has_code") or lab in (None, "invalid"):
        return "UNTRACEABLE"
    return COARSE.get(lab, "OTHER")


def traceable(r):
    return mech_class(r) not in (None, "UNTRACEABLE")


def mech_ok(r, banned):
    return mech_class(r) not in {COARSE[b] for b in banned}


def two_by_two(rows, banned):
    a = b = c = d = 0
    for r in rows:
        if not r.get("has_code") or not traceable(r):
            continue
        lx, m = bool(r.get("lexical_L1")), mech_ok(r, banned)
        if lx and m:
            a += 1
        elif lx:
            b += 1
        elif m:
            c += 1
        else:
            d += 1
    return a, b, c, d


def jt(groups):
    zs = [sum(1 for v in g if v == 0) for g in groups]
    os_ = [sum(1 for v in g if v == 1) for g in groups]
    J = 0.0
    for i in range(len(groups)):
        for j in range(i + 1, len(groups)):
            J += zs[i] * os_[j] + 0.5 * (zs[i] * zs[j] + os_[i] * os_[j])
    return J


def jt_perm_p(groups, n_perm, rng):
    sizes = [len(g) for g in groups]
    y = [v for g in groups for v in g]
    obs = jt(groups)
    if not y or min(y) == max(y):
        return None
    le = 0
    for _ in range(n_perm):
        rng.shuffle(y)
        gs, i = [], 0
        for s in sizes:
            gs.append(y[i:i + s])
            i += s
        le += int(jt(gs) <= obs + 1e-9)
    return (le + 1) / (n_perm + 1)


def named_survivor(r, banned):
    if not r.get("passed"):
        return False
    lab = r.get("label")
    if lab in (None, "invalid", "no_code") or lab in banned:
        return False
    if lab == "other":
        return str(r.get("label_other_name") or "").strip().lower() not in ("", "unknown", "none", "null", "n/a")
    return True


def main():
    res = os.path.join(ROOT, "results")
    allout = {}
    for field, suffix in (("runtime_class", ""), ("order_class", "_tracer")):
        MECH["field"] = field
        allout[field] = one(res, suffix)
    out = allout["runtime_class"]
    out["tracer_column"] = {k: v for k, v in allout["order_class"].items() if k != "checks"}
    out["n_mismatches"] = allout["runtime_class"]["n_mismatches"] + allout["order_class"]["n_mismatches"]
    with open(os.path.join(res, "rederive.json"), "w") as fh:
        json.dump(out, fh, indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "checks"}, indent=1))


def one(res, suffix):
    out = {"mismatches": [], "checks": {}, "mech_field": MECH["field"]}
    ret = rl(os.path.join(res, "retrace.jsonl"))
    n1 = rj(os.path.join(res, f"n1{suffix}.json"))
    gaps = []
    for cfg, t in n1["per_config"].items():
        rows = [r for r in ret if r["config"] == cfg]
        a, b, c, d = two_by_two(rows, LIT)
        D, lo, hi = newcombe_paired(a, b, c, d)
        ok = (a, b, c, d) == (t["a_lex_mech"], t["b_lex_notmech"], t["c_notlex_mech"], t["d_neither"]) and \
            abs(D - t["gap"]) < 1e-9 and abs(lo - t["gap_newcombe95"][0]) < 1e-9
        out["checks"][f"N1:{cfg}"] = {"cells": [a, b, c, d], "gap": D, "ci": [lo, hi], "ok": ok}
        if not ok:
            out["mismatches"].append(f"N1 {cfg}")
        gaps.append(D)
    pooled = sum(gaps) / len(gaps)
    out["checks"]["N1:pooled"] = {"pooled": pooled, "ok": abs(pooled - n1["pooled_equal_weight"]) < 1e-9}
    if not out["checks"]["N1:pooled"]["ok"]:
        out["mismatches"].append("N1 pooled")
    v = "SUPPORTED" if pooled >= 0.3 and sum(g > 0 for g in gaps) >= math.ceil(0.7 * len(gaps)) else \
        ("DISCONFIRMED" if pooled < 0.1 else "NOT SUPPORTED (between the bars)")
    out["checks"]["N1:verdict"] = {"verdict": v, "ok": v == n1["verdict"]}
    if v != n1["verdict"]:
        out["mismatches"].append("N1 verdict")
    # placebo 1: swap lexical and mechanistic flags at random within programs
    rng = random.Random(0)
    pl = []
    for _ in range(200):
        gs = []
        for cfg in n1["per_config"]:
            rows = [r for r in ret if r["config"] == cfg and r.get("has_code") and traceable(r)]
            k = 0
            for r in rows:
                lx, m = bool(r.get("lexical_L1")), mech_ok(r, LIT)
                if rng.random() < 0.5:
                    lx, m = m, lx
                k += int(lx) - int(m)
            gs.append(k / len(rows) if rows else 0.0)
        pl.append(sum(gs) / len(gs))
    out["placebo_swap_flags"] = {"mean_pooled_gap": sum(pl) / len(pl), "sd": (sum((x - sum(pl) / len(pl)) ** 2
                                                                                for x in pl) / len(pl)) ** 0.5,
                                 "observed": pooled,
                                 "fails_as_required": abs(sum(pl) / len(pl)) < 0.05}
    # N3 (per model): rates + JT with an own permutation test
    n3 = rj(os.path.join(res, f"n3{suffix}.json")) if os.path.exists(os.path.join(res, f"n3{suffix}.json")) else {}
    for mk, pre in (("q32", "A"), ("q14", "E")):
        if mk not in n3:
            continue
        groups = []
        for k in range(1, 6):
            rows = rl(os.path.join(ROOT, "data", f"labelled_v9_{pre}_k{k}.jsonl"))
            banned = [x for x in ["bfs", "dfs", "bibfs", "iddfs", "astar", "gbfs", "dijkstra_unit", "idastar", "jps",
                                  "biastar"] if x in KORD[:k]]
            comp = [r for r in rows if r.get("has_code") and not r.get("truncated")]
            tr = [r for r in comp if traceable(r)]
            lex = sum(1 for r in comp if r.get("lexical_L1")) / len(comp) if comp else None
            mech = sum(1 for r in tr if mech_ok(r, banned)) / len(tr) if tr else None
            ref = n3[mk]["per_k"][str(k)]
            ok = (lex is None or abs(lex - ref["lex_L1_completed"]["rate"]) < 1e-9) and \
                 (mech is None or abs(mech - ref["mech_coarse_traceable"]["rate"]) < 1e-9)
            out["checks"][f"N3:{mk}:k{k}"] = {"lex": lex, "mech": mech, "ok": ok}
            if not ok:
                out["mismatches"].append(f"N3 {mk} k{k}")
            groups.append([int(mech_ok(r, banned)) for r in tr])
        J = jt(groups)
        okJ = abs(J - n3[mk]["jt_mech_coarse"]["J"]) < 1e-9
        p = jt_perm_p(groups, 20000, random.Random(5))
        out["checks"][f"N3:{mk}:JT"] = {"J": J, "p_perm_20000": p, "p_reported": n3[mk]["jt_mech_coarse"].get("p_mc"),
                                       "ok": okJ}
        if not okJ:
            out["mismatches"].append(f"N3 {mk} JT")
        # placebo 2: permute k labels within the model
        pooled_rows = [v for g in groups for v in g]
        sizes = [len(g) for g in groups]
        r2 = random.Random(11)
        below = 0
        nrun = 200
        for _ in range(nrun):
            ys = pooled_rows[:]
            r2.shuffle(ys)
            gs, i = [], 0
            for s in sizes:
                gs.append(ys[i:i + s])
                i += s
            pp = jt_perm_p(gs, 300, random.Random(r2.random()))
            below += int(pp is not None and pp < 0.05)
        out[f"placebo_permuted_k_{mk}"] = {"share_p_below_0.05": below / nrun, "fails_as_required": below / nrun < 0.10}
    # N2 shares
    n2p = os.path.join(res, f"n2{suffix}.json")
    if os.path.exists(n2p):
        n2 = rj(n2p)
        per = n2["per_survivor"]
        tr = [p for p in per if p["order_class"] not in (None, "UNTRACEABLE")]
        k = sum(1 for p in tr if p["order_class"] in ("BFS", "DFS", "ID", "HEUR"))
        ok = k == n2["a_all"]["k"] and len(tr) == n2["a_all"]["n"]
        out["checks"]["N2:a"] = {"k": k, "n": len(tr), "wilson": wilson(k, len(tr)), "ok": ok}
        if not ok:
            out["mismatches"].append("N2 a")
    # N5 sign count + placebo 3
    n5p = os.path.join(res, "n5.json")
    if os.path.exists(n5p):
        n5 = rj(n5p)
        cnt = sum(1 for v in n5["sets"].values() if v.get("defined") and v.get("Dm") is not None and
                  v.get("Dn") is not None and v["Dm"] < 0 and v["Dn"] > 0)
        out["checks"]["N5:joint"] = {"count": cnt, "ok": cnt == n5["n_joint"]}
        if cnt != n5["n_joint"]:
            out["mismatches"].append("N5 joint")
        r3 = random.Random(3)
        joint = []
        for _ in range(500):
            c = 0
            for v in n5["sets"].values():
                if not v.get("defined"):
                    continue
                c += int(r3.random() < 0.5 and r3.random() < 0.5)
            joint.append(c)
        nd = sum(1 for v in n5["sets"].values() if v.get("defined"))
        out["placebo_random_survivors_n5"] = {"mean_joint": sum(joint) / len(joint), "expected_chance": 0.25 * nd,
                                              "note": "random survivor identities give sign hits with p=0.5 per "
                                                      "component, i.e. 0.25 per set jointly",
                                              "fails_as_required": abs(sum(joint) / len(joint) - 0.25 * nd) < 0.5}
    out["n_mismatches"] = len(out["mismatches"])
    return out


if __name__ == "__main__":
    main()
