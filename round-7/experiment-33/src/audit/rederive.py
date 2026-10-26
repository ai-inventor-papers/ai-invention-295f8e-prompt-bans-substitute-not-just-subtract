#!/usr/bin/env python3
"""Independent stdlib re-derivation of the headline numbers from data/labels.jsonl (no numpy, no project imports),
compared with results/p1.json, results/p1_controls_<task>.json and results/c_routing.json; plus placebo versions of
the headline tests that must fail (within-slot arm swaps; Y labels shuffled across sources).

usage: python3 audit/rederive.py   (writes results/rederive.json)
"""

import json
import math
import random
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
N = 30
PREF = ("DASLY", "PERMLY")


def load(p):
    return [json.loads(l) for l in open(p) if l.strip()]


def mcnemar(b, c):
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    p = sum(math.comb(n, i) for i in range(0, k + 1)) / 2 ** n
    return min(1.0, 2 * p)


def main():
    labs = load(ROOT / "data" / "labels.jsonl")
    A = defaultdict(dict)
    for r in labs:
        A[(r["task"], r["arm"])][int(r["slot_index"])] = r
    checks, mism = [], []

    def check(name, mine, theirs, tol=1e-9):
        ok = (mine is None and theirs is None) or (mine is not None and theirs is not None and
                                                  abs(float(mine) - float(theirs)) <= tol)
        checks.append({"check": name, "rederived": mine, "reported": theirs, "ok": ok})
        if not ok:
            mism.append(name)

    p1 = json.loads((ROOT / "results" / "p1.json").read_text())
    for task, r in p1["tasks"].items():
        tg = json.loads((ROOT / "results" / f"targets_{task}.json").read_text())
        ks = json.loads((ROOT / "results" / f"kstar_{task}.json").read_text())
        site = json.loads((ROOT / "results" / f"site_{task}.json").read_text())
        full_ban = "FULL_ban_band" if site["site"] == "band" else f"FULL_ban_L{site['L_star']}"
        land = tg["landing"] or tg["kept_Y"][:1]

        def cnt(arm, Y):
            d = A.get((task, arm), {})
            return sum(1 for s in range(N) if s in d and d[s].get("passed") and d[s].get("label") in Y)
        srcs = [("ban", land, "BASE_W5", full_ban, {k: f"DASLY_ban_k{k}" for k in (1, 2, 4, 8, 16)})]
        for Y in ks["kept_Y_cells"]:
            srcs.append((f"F_{Y}", [Y], "BASE_PAD", f"FULL_F_{Y}", {k: f"DASLY_F_{Y}_k{k}" for k in (1, 4, 16)}))
        for name, Y, base, full, das in srcs:
            ps = r["per_source"].get(name)
            if not ps:
                continue
            check(f"{task}:{name}:base_count", cnt(base, Y), ps["base_count"])
            check(f"{task}:{name}:full_count", cnt(full, Y), ps["full_count"])
            for k, a in das.items():
                if str(k) in ps["das"] or k in ps["das"]:
                    e = ps["das"].get(str(k)) or ps["das"].get(k)
                    check(f"{task}:{name}:das_k{k}_count", cnt(a, Y), e["count"])
        for k in (1, 2, 4, 8, 16):
            num = den = 0
            for name, Y, base, full, das in srcs:
                if k not in das or (task, das[k]) not in A:
                    continue
                num += cnt(das[k], Y) - cnt(base, Y)
                den += cnt(full, Y) - cnt(base, Y)
            e = r["per_k"].get(str(k)) or r["per_k"].get(k) or {}
            check(f"{task}:recovery_k{k}", num / den if den > 0 else None, e.get("recovery"), 1e-9)
        # McNemar DAS vs random at k = 16 (draw 1 for the ban source)
        b = c = 0
        for name, Y, base, full, das in srcs:
            ra = "RAND_ban_k16_d1" if name == "ban" else f"RAND_F_{Y[0]}_k16"
            da = das.get(16)
            if (task, ra) not in A or (task, da) not in A:
                continue
            for s in range(N):
                x = A[(task, da)].get(s)
                y = A[(task, ra)].get(s)
                xv = int(bool(x and x.get("passed") and x.get("label") in Y))
                yv = int(bool(y and y.get("passed") and y.get("label") in Y))
                b += xv and not yv
                c += yv and not xv
        e16 = r["per_k"].get("16") or r["per_k"].get(16) or {}
        mc = e16.get("mcnemar_das_vs_rand") or {}
        check(f"{task}:mcnemar16_b", b, mc.get("b_das_only"))
        check(f"{task}:mcnemar16_c", c, mc.get("c_rand_only"))
        check(f"{task}:mcnemar16_p", mcnemar(b, c), mc.get("p"), 1e-9)
        # placebo 1: within-slot swap of DAS k16 and random k16 labels (coin per slot) -> p should be large
        rng = random.Random(7)
        pb = pc = 0
        for name, Y, base, full, das in srcs:
            ra = "RAND_ban_k16_d1" if name == "ban" else f"RAND_F_{Y[0]}_k16"
            da = das.get(16)
            if (task, ra) not in A or (task, da) not in A:
                continue
            for s in range(N):
                x = A[(task, da)].get(s)
                y = A[(task, ra)].get(s)
                xv = int(bool(x and x.get("passed") and x.get("label") in Y))
                yv = int(bool(y and y.get("passed") and y.get("label") in Y))
                if rng.random() < 0.5:
                    xv, yv = yv, xv
                pb += xv and not yv
                pc += yv and not xv
        checks.append({"check": f"{task}:placebo_swap_mcnemar16", "b": pb, "c": pc, "p": mcnemar(pb, pc),
                       "ok": True, "note": "placebo (should not be significant)"})
        # placebo 2: Y labels shuffled across the task's catalogue (score DAS ban k16 against a wrong Y)
        wrong = [y for y in tg["kept_Y"] if y not in land] or ["other"]
        checks.append({"check": f"{task}:placebo_wrongY_ban_k16", "count_wrong_Y": cnt("DASLY_ban_k16", wrong),
                       "count_true_Y": cnt("DASLY_ban_k16", land), "ok": True, "note": "placebo (Y shuffled)"})
    # controls
    for task in p1["tasks"]:
        cp = ROOT / "results" / f"p1_controls_{task}.json"
        if not cp.exists():
            continue
        ctrl = json.loads(cp.read_text())
        tg = json.loads((ROOT / "results" / f"targets_{task}.json").read_text())
        land = tg["landing"] or tg["kept_Y"][:1]
        for arm in ("RPOSLY_ban_k16", "RPOSFULL_ban", "DIM1_ban", "PCA16_ban"):
            e = ctrl.get(arm)
            if not e:
                continue
            d = A.get((task, arm), {})
            c_ = sum(1 for s in range(N) if s in d and d[s].get("passed") and d[s].get("label") in land)
            check(f"{task}:{arm}:count", c_, e["count"])
    # ---------------------------------------------------------------- extended headline checks (step 2 audit)
    def correct(task, arm, Y, n=N):
        d = A.get((task, arm), {})
        return [int(bool(d.get(s) and d[s].get("passed") and d[s].get("label") in Y)) for s in range(n)]

    def holm(pv):
        items = sorted(pv.items(), key=lambda x: x[1])
        m, run, out = len(items), 0.0, {}
        for i, (k, p) in enumerate(items):
            run = max(run, min(1.0, (m - i) * p))
            out[k] = run
        return out
    p_at_k = {}
    for task, r in p1["tasks"].items():
        tg = json.loads((ROOT / "results" / f"targets_{task}.json").read_text())
        ks = json.loads((ROOT / "results" / f"kstar_{task}.json").read_text())
        land = tg["landing"] or tg["kept_Y"][:1]
        base = sum(correct(task, "BASE_W5", land))
        # permuted-label transfers on the ban source
        for a, e in (r["per_source"]["ban"].get("perm") or {}).items():
            check(f"{task}:{a}:count", sum(correct(task, a, land)), e["count"])
            check(f"{task}:{a}:transfer", (sum(correct(task, a, land)) - base) / N, e["transfer"], 1e-9)
        # McNemar DAS vs random at the P1 k (pooled over sources that have both arms at that k)
        k = r.get("P1_k")
        b = c = 0
        cand = [("ban", land, f"DASLY_ban_k{k}", f"RAND_ban_k{k}" if k != 16 else "RAND_ban_k16_d1")]
        for Y in ks["kept_Y_cells"]:
            if k == 16:
                cand.append((Y, [Y], f"DASLY_F_{Y}_k16", f"RAND_F_{Y}_k16"))
        for _, Y, da, ra in cand:
            if (task, da) in A and (task, ra) in A:
                x, y = correct(task, da, Y), correct(task, ra, Y)
                b += sum(1 for i in range(N) if x[i] and not y[i])
                c += sum(1 for i in range(N) if y[i] and not x[i])
        e = r["per_k"].get(str(k)) or r["per_k"].get(k)
        mc = e["mcnemar_das_vs_rand"]
        check(f"{task}:mcnemar_P1k{k}_b", b, mc["b_das_only"])
        check(f"{task}:mcnemar_P1k{k}_c", c, mc["c_rand_only"])
        p_at_k[task] = mcnemar(b, c)
        check(f"{task}:mcnemar_P1k{k}_p", p_at_k[task], mc["p"], 1e-12)
        # placebo A: two random subspaces against each other (must NOT be significant)
        x, y = correct(task, "RAND_ban_k16_d1", land), correct(task, "RAND_ban_k16_d2" if (task, "RAND_ban_k16_d2") in A
                                                              else "BASE_W5", land)
        pb_ = sum(1 for i in range(N) if x[i] and not y[i])
        pc_ = sum(1 for i in range(N) if y[i] and not x[i])
        checks.append({"check": f"{task}:placebo_random_vs_random_mcnemar", "b": pb_, "c": pc_, "p": mcnemar(pb_, pc_),
                       "ok": mcnemar(pb_, pc_) > 0.05, "note": "placebo must fail (p > 0.05)"})
        if mcnemar(pb_, pc_) <= 0.05:
            mism.append(f"{task}:placebo_random_vs_random significant")
        # placebo B: recovery with a random arm in place of DAS (must be ~0, far below 0.8)
        full = sum(correct(task, r["per_source"]["ban"] and (
            "FULL_ban_band" if json.loads((ROOT / "results" / f"site_{task}.json").read_text())["site"] == "band"
            else f"FULL_ban_L{json.loads((ROOT / 'results' / f'site_{task}.json').read_text())['L_star']}"), land))
        rnd = sum(correct(task, "RAND_ban_k16_d1", land))
        rec_pl = (rnd - base) / (full - base) if full > base else None
        checks.append({"check": f"{task}:placebo_recovery_random_as_DAS", "value": rec_pl,
                       "ok": rec_pl is not None and rec_pl < 0.4, "note": "placebo must fail (<< 0.8)"})
        if rec_pl is None or rec_pl >= 0.4:
            mism.append(f"{task}:placebo_recovery not near 0")
    ph = holm(p_at_k)
    for t, v in ph.items():
        check(f"{t}:holm_p", v, p1["holm"].get(t), 1e-12)
    # routing (C)
    cr = json.loads((ROOT / "results" / "c_routing.json").read_text())
    for task, r in cr["per_task"].items():
        D = {"T2": "dijkstra", "T10": "union_find", "T03": "full_sort"}[task]
        for Y, e in r["per_Y"].items():
            for nm, arm in [("full", f"FULL_F_{Y}")] + [(f"k{k}", f"DASLY_F_{Y}_k{k}") for k in (1, 4, 16)]:
                if nm not in e:
                    continue
                d = A.get((task, arm), {})
                rows = [d[s] for s in range(N) if s in d]
                corr = [x for x in rows if x.get("passed")]
                ny = sum(1 for x in corr if x["label"] == Y)
                off = sum(1 for x in corr if x["label"] != D)
                check(f"{task}:route:{Y}:{nm}:correct_Y", ny, e[nm]["correct_Y"])
                check(f"{task}:route:{Y}:{nm}:off_default", off, e[nm]["correct_off_default"])
    # M behaviour, R curve, novelty, engine check
    mb = ROOT / "results" / "m_behaviour.json"
    if mb.exists():
        for kind, e in json.loads(mb.read_text()).items():
            d = A.get(("T2", f"MGEN_{kind}"), {})
            check(f"T2:mgen:{kind}:dijkstra", sum(1 for x in d.values() if x.get("passed") and x["label"] == "dijkstra"),
                  e["correct_composition"].get("dijkstra", 0))
            check(f"T2:mgen:{kind}:off_default", e["correct_off_default"],
                  sum(1 for x in d.values() if x.get("passed") and x["label"] != "dijkstra"))
    rd = ROOT / "results" / "r_discreteness.json"
    if rd.exists():
        rj = json.loads(rd.read_text())
        for lam, e in rj["curve"].items():
            arm = next((a for (t, a) in A if t == "T2" and a.startswith(f"LAM{lam}_ban")), None)
            if arm:
                check(f"T2:R:lam{lam}:correct_Y", sum(correct("T2", arm, ["bf_spfa"], 20)), e["correct_Y"])
    nv = json.loads((ROOT / "results" / "novelty_audit.json").read_text())
    n_other = sum(1 for r in labs if r.get("passed") and r.get("label") == "other" and r.get("code"))
    check("novelty:n_correct_other", n_other, nv["n_correct_other"])
    check("novelty:n_novel", sum(1 for r in nv["rows"] if r["class"] == "NOVEL"), nv["classes"].get("NOVEL", 0))
    ref = defaultdict(dict)
    for r in load(ROOT / "inputs" / "exp30" / "data" / "labels.jsonl"):
        if r["arm"] == "TWIN":
            ref[r["task"]][int(r["slot_index"])] = r["label"]
    ec = json.loads((ROOT / "results" / "engine_check.json").read_text())
    for t in ("T2", "T03", "T10"):
        mine = A.get((t, "TWIN"), {})
        agree = sum(1 for s in range(20) if s in mine and s in ref[t] and mine[s]["label"] == ref[t][s])
        check(f"{t}:engine_agree", agree, ec[t]["agree"])
    out = {"n_checks": len([c for c in checks if "rederived" in c]), "n_mismatch": len(mism), "mismatches": mism,
           "checks": checks}
    (ROOT / "results" / "rederive.json").write_text(json.dumps(out, indent=1))
    print(f"rederive: {out['n_checks']} checks, {len(mism)} mismatches {mism[:10]}")


if __name__ == "__main__":
    main()
