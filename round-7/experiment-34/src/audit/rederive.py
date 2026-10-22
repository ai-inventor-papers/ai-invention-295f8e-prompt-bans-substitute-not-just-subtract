#!/usr/bin/env python3
"""Independent stdlib-only re-derivation of the headline numbers from raw rows and committed predictor files.

Re-derives: every POP-cell y on T10/T2 (exp29 engine-d label rows), the F and P2 Spearmans, the tie ceilings, the
T03 confirmation Spearmans, the targeted-push runner-up shares and McNemar counts, and the T1 top-five label counts;
then compares with results/*.json (0 mismatches required, tolerance 1e-9). Placebos (must NOT reproduce the
effects): shuffled y gives a null Spearman; a random 'axis' (shuffled b) is not ahead; a shuffled fork token map
gives a different margin ordering.
usage: python audit/rederive.py   (stdlib only; run from the repository root)
"""

import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAT = {"T10": ["union_find", "bfs", "dfs", "label_propagation"],
       "T2": ["dijkstra", "bf_spfa", "bidijkstra", "floyd", "dial"],
       "T03": ["full_sort", "size_k_heap", "heapify_pop", "quickselect", "median_of_medians", "counting_sort"]}
DEF = {"T10": "union_find", "T2": "dijkstra", "T03": "full_sort", "T1": "bfs"}
RU = {"T10": "dfs", "T2": "bf_spfa", "T03": "quickselect"}


def jl(p):
    out = []
    if not Path(p).exists():
        return out
    for line in open(p):
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except ValueError:
                pass
    return out


def rank(v):
    idx = sorted(range(len(v)), key=lambda i: v[i])
    r = [0.0] * len(v)
    i = 0
    while i < len(v):
        j = i
        while j + 1 < len(v) and v[idx[j + 1]] == v[idx[i]]:
            j += 1
        for k in range(i, j + 1):
            r[idx[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def pearson(a, b):
    n = len(a)
    ma, mb = sum(a) / n, sum(b) / n
    va = sum((x - ma) ** 2 for x in a)
    vb = sum((x - mb) ** 2 for x in b)
    if va == 0 or vb == 0:
        return float("nan")
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / (va * vb) ** 0.5


def spearman(a, b):
    pairs = [(x, y) for x, y in zip(a, b) if x == x and y == y]
    if len(pairs) < 3:
        return float("nan")
    a, b = [p[0] for p in pairs], [p[1] for p in pairs]
    return pearson(rank(a), rank(b))


def close(a, b, tol=1e-9):
    if a is None or b is None:
        return a is None and b is None
    if a != a and b != b:
        return True
    return abs(a - b) <= tol * max(1.0, abs(a), abs(b))


def main():
    checks, mism = [], []

    def chk(name, a, b):
        ok = close(a, b)
        checks.append({"name": name, "rederived": a, "reported": b, "ok": ok})
        if not ok:
            mism.append(name)

    fa = json.loads((ROOT / "results" / "f_analysis.json").read_text())
    pa = json.loads((ROOT / "results" / "p2_analysis.json").read_text())
    c3p = ROOT / "predictions" / "commit3b_predictors.json"
    if not c3p.exists():
        c3p = ROOT / "predictions" / "commit3_predictors.json"
    c3 = json.loads(c3p.read_text())["cells"]
    lab29 = {}
    for r in jl(ROOT / "inputs" / "exp29" / "labels.jsonl"):
        if r["key"].startswith("d|") and r["arm"].startswith("POP_") and r["arm"].endswith("_a2.0") \
                and int(r["sample_id"]) <= 5:
            lab29.setdefault((r["task"], r["arm"]), []).append(r)
    for task in ("T10", "T2"):
        m, y, b = [], [], []
        for row in fa["cells"][task]:
            rr = lab29.get((task, f"POP_d{row['seed']}_a2.0"), [])
            yy = sum(1 for r in rr if r["label"] in CAT[task] and r["label"] != DEF[task] and r["passed"]) / len(rr)
            chk(f"y {task} {row['seed']}", yy, row["y"])
            c = c3[f"{task}|POP_d{row['seed']}_a2.0"]
            m.append(c["m"])
            b.append(c["b"])
            y.append(yy)
        chk(f"F rho {task}", spearman(m, y), fa["F"][task]["rho"])
        chk(f"P2 rho {task}", spearman(b, y), pa["P2"][task]["rho_b"])
        srt = sorted(range(len(y)), key=lambda i: (y[i], i))
        ordinal = [0] * len(y)
        for r_, i in enumerate(srt):
            ordinal[i] = r_ + 1
        chk(f"tie ceiling {task}", spearman(ordinal, y), fa["F"][task]["rho_max_ties"])
        rnd = random.Random(7)
        null = []
        for _ in range(500):
            yy = y[:]
            rnd.shuffle(yy)
            null.append(spearman(m, yy))
        null = [v for v in null if v == v]
        checks.append({"name": f"placebo shuffled-y F {task}", "median_null_rho": sorted(null)[len(null) // 2],
                       "observed": spearman(m, y)})
        bb = b[:]
        rnd.shuffle(bb)
        checks.append({"name": f"placebo random axis P2 {task}", "rho_shuffled_b": spearman(bb, y),
                       "observed": spearman(b, y)})
    fp = ROOT / "results" / "fork_token_probs.json"
    fkp = ROOT / "predictions" / "commit1c_forks.json"
    if fp.exists() and fkp.exists():
        import math
        P = json.loads(fp.read_text())
        maps = json.loads(fkp.read_text())["tasks"]["T10"]["token_maps"]
        forks = P["forks"]

        def margin(cell, qmaps):
            vals = []
            for w, d in P["cells"][cell].items():
                prod = 1.0
                for j, f in enumerate(forks):
                    probs = d[str(f)]
                    tot = sum(probs.values())
                    e = sum(p * qmaps[j][k] for k, p in probs.items()) / tot
                    prod *= 1 - e
                vals.append(1 - prod)
            pb = sum(vals) / len(vals)
            pb = min(max(pb, 1e-12), 1 - 1e-12)
            return math.log(pb) - math.log(1 - pb)

        q_true = []
        for j, f in enumerate(forks):
            q = {str(k): maps[str(f)][str(k)]["q"] for k in P["mapped_tokens"][str(f)]}
            if j < len(forks) - 1:
                q[str(P["default_token"][str(f)])] = 0.0     # sequential multi-fork rule (commit1c)
            q_true.append(q)
        y10 = {r["seed"]: r["y"] for r in fa["cells"]["T10"]}
        m_re, yv = [], []
        for s, yy in sorted(y10.items()):
            mm = margin(f"POP_d{s}_a2.0", q_true)
            chk(f"T10 margin m {s} (from token probabilities)", mm, c3[f"T10|POP_d{s}_a2.0"]["m"])
            m_re.append(mm)
            yv.append(yy)
        chk("T10 twin margin", margin("TWIN", q_true), c3["T10|TWIN"]["m"])
        rnd = random.Random(11)
        null = []
        for _ in range(200):
            qs = []
            for q in q_true:
                keys = list(q)
                vals = [q[k] for k in keys]
                rnd.shuffle(vals)
                qs.append(dict(zip(keys, vals)))
            null.append(spearman([margin(f"POP_d{s}_a2.0", qs) for s in sorted(y10)], yv))
        null = sorted(v for v in null if v == v)
        checks.append({"name": "placebo shuffled fork token map (T10)", "observed": spearman(m_re, yv),
                       "null_median": null[len(null) // 2] if null else None,
                       "null_95pct": null[int(0.95 * len(null))] if null else None,
                       "share_null_ge_observed": sum(1 for v in null if v >= spearman(m_re, yv)) / max(1, len(null))})
    tc = ROOT / "results" / "t03_confirmation.json"
    if tc.exists():
        t = json.loads(tc.read_text())
        mine = {}
        for r in jl(ROOT / "data" / "labels.jsonl"):
            if r["task"] == "T03" and r["arm"].startswith("POP_d97") and int(r["sample_id"]) < 2:
                mine.setdefault(r["arm"], []).append(r)
        ys, bs = [], []
        for row in t["rows"]:
            rr = mine.get(f"POP_d{row['seed']}_a2.0", [])
            yy = sum(1 for r in rr if r["label"] in CAT["T03"] and r["label"] != "full_sort" and r["passed"]) / len(rr)
            chk(f"y T03 {row['seed']}", yy, row["y"])
            ys.append(yy)
            bs.append(row["b"])
        chk("T03 rho b", spearman(bs, ys), t["b"]["rho"])
    tp = ROOT / "results" / "targeted_push.json"
    if tp.exists():
        T = json.loads(tp.read_text())
        L = jl(ROOT / "data" / "labels.jsonl")
        for task in ("T10", "T2", "T03"):
            if task not in T:
                continue
            for arm, v in T[task]["arms"].items():
                rr = [r for r in L if r["task"] == task and r["arm"] == arm and int(r["sample_id"]) <= 5]
                chk(f"targeted {task} {arm} runner-up share",
                    sum(1 for r in rr if r["label"] == RU[task] and r["passed"]) / len(rr), v["y_runner_up"])
    # ---------------------------------------------------------------- tests re-run here + placebos that must FAIL
    import math

    def perm_p(x, y, n, rnd):
        obs = spearman(x, y)
        cnt = 0
        for _ in range(n):
            yy = y[:]
            rnd.shuffle(yy)
            cnt += spearman(x, yy) >= obs - 1e-12
        return (1 + cnt) / (1 + n)

    def mcnemar(b, c):
        n = b + c
        if n == 0:
            return 1.0
        k = min(b, c)
        return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)

    tests = []
    rnd = random.Random(2026)
    for task, key, src in (("T10", "F", "f"), ("T03", "T03 m", "t03")):
        if src == "f":
            rows = fa["cells"]["T10"]
            x = [c3[f"T10|POP_d{r['seed']}_a2.0"]["m"] for r in rows]
            yv = [r["y"] for r in rows]
        else:
            if not tc.exists():
                continue
            rows = json.loads(tc.read_text())["rows"]
            x = [r["m"] for r in rows]
            yv = [r["y"] for r in rows]
        p_obs = perm_p(x, yv, 2000, rnd)
        plac = []
        for _ in range(100):
            ys = yv[:]
            rnd.shuffle(ys)
            plac.append(perm_p(x, ys, 300, rnd))
        tests.append({"test": f"{key}: Spearman permutation test ({task})", "rho": spearman(x, yv), "p_observed": p_obs,
                      "placebo_shuffled_y_share_p_lt_0.05": sum(p < 0.05 for p in plac) / len(plac),
                      "placebo_fails": sum(p < 0.05 for p in plac) / len(plac) <= 0.10})

    def slot_pairs(path, task, arm_a, arm_b):
        A, B = {}, {}
        for r in jl(path):
            if r["task"] != task:
                continue
            k = (r["template"], int(r["sample_id"]))
            if r["arm"] == arm_a:
                A[k] = r
            elif r["arm"] == arm_b:
                B[k] = r
        return [(A[k], B[k]) for k in sorted(set(A) & set(B))]

    def off(r, task):
        return int(r["label"] in CAT[task] and r["label"] != DEF[task] and bool(r["passed"]))

    def mcn_test(name, pairs, task):
        b = sum(1 for a, c in pairs if off(a, task) and not off(c, task))
        c = sum(1 for a, c_ in pairs if off(c_, task) and not off(a, task))
        plac = []
        for _ in range(200):
            bb = cc = 0
            for a, c_ in pairs:
                x, z = (a, c_) if rnd.random() < 0.5 else (c_, a)
                bb += off(x, task) and not off(z, task)
                cc += off(z, task) and not off(x, task)
            plac.append(mcnemar(bb, cc))
        share = sum(p < 0.05 for p in plac) / len(plac)
        tests.append({"test": name, "n_pairs": len(pairs), "discordant": [b, c], "p_exact": mcnemar(b, c),
                      "placebo_random_arm_swap_share_p_lt_0.05": share, "placebo_fails": share <= 0.10})

    lab = ROOT / "data" / "labels.jsonl"
    mcn_test("targeted push T10 s=4: axis vs matched random (exact McNemar)",
             slot_pairs(lab, "T10", "AX_s4", "RX_s4"), "T10")
    lf = ROOT / "data" / "labels_force.jsonl"
    if lf.exists():
        F_ = {(r["template"], int(r["sample_id"])): r for r in jl(lf) if r["task"] == "T10" and r["arm"] == "F11_dfs"}
        T_ = {(r["template"], int(r["sample_id"])): r for r in jl(lab) if r["task"] == "T10" and r["arm"] == "TWIN"}
        mcn_test("forced token ' def dfs' vs twin on T10 (exact McNemar, exploratory)",
                 [(F_[k], T_[k]) for k in sorted(set(F_) & set(T_))], "T10")
    lc = ROOT / "data" / "labels_clamp.jsonl"
    if lc.exists():
        esc = {"CLU": 0, "CLA": 0, "CLR": 0}
        for r in jl(lc):
            esc[r["arm"].split("_")[0]] += off(r, r["task"])
        cl = json.loads((ROOT / "results" / "clamp.json").read_text())["pooled"]["escapes"]
        for k_ in esc:
            chk(f"clamp escapes {k_}", float(esc[k_]), float(cl[k_]))
    T1_SURV = {"bibfs", "dijkstra_unit", "idastar", "jps", "biastar"}
    t1 = [r for r in jl(lab) if r["task"] == "T1" and r["arm"].split("_")[0] in ("SURV", "RSURV", "AWAY", "IDASTAR")
          and int(r["sample_id"]) <= 5]
    tests.append({"test": "T1 in-manifold top-five push: non-top-five programs (label10) among all push rows",
                  "n_rows": len(t1), "n_non_top5_attempted": sum(1 for r in t1 if r.get("label10") in T1_SURV),
                  "n_bfs": sum(1 for r in t1 if r.get("label10") == "bfs")})
    s0b = ROOT / "data" / "labels_s0b.jsonl"
    rmp = ROOT / "results" / "remeasure.json"
    if s0b.exists() and rmp.exists():
        rm = json.loads(rmp.read_text())
        mine = {}
        for r in jl(s0b):
            if r["arm"].startswith("POP_"):
                mine.setdefault((r["task"], r["arm"]), []).append(r)
        for task in ("T10", "T2"):
            ys, ye = [], []
            for row in fa["cells"][task]:
                rr = mine.get((task, f"POP_d{row['seed']}_a2.0"), [])
                if rr:
                    ys.append(sum(off(r, task) for r in rr) / len(rr))
                    ye.append(row["y"])
            chk(f"remeasure y-correlation {task}", spearman(ys, ye), rm[task]["y_this_vs_exp29d_rho"])
    out = {"n_checks": len([c for c in checks if "ok" in c]), "mismatches": mism, "checks": checks, "tests": tests,
           "all_placebos_fail": all(t.get("placebo_fails", True) for t in tests)}
    (ROOT / "results" / "rederive.json").write_text(json.dumps(out, indent=1))
    print(f"{out['n_checks']} checks, {len(mism)} mismatches")


if __name__ == "__main__":
    main()
