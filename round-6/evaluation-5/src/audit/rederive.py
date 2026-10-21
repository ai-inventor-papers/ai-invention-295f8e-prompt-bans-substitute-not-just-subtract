#!/usr/bin/env python3
"""Independent re-derivation of the Step-0 headlines (stdlib only: json, csv, math, random, statistics, hashlib,
difflib, ast, os, pathlib). Imports NOTHING from the eval code. Reads the raw dependency files directly, recomputes
each headline with its own implementation, compares it with the eval outputs, runs five placebos that must FAIL,
verifies the commitments.log hash chain and that every frozen file predates every S3 output.
Run: python3 -I audit/rederive.py   (writes audit/rederive_result.json and audit/placebos.json)
"""

import ast
import csv
import hashlib
import json
import math
import os
import random
import statistics
from pathlib import Path

WS = Path(__file__).resolve().parent.parent
# Same resolution as the eval code, re-implemented here: <AII_DEPS_ROOT>/<artifact_id> (default: sibling folders of
# this artifact), per-artifact AII_DEP_<id>, or the unpublished paths.local.json {"deps": {id: folder}}.
_LOC = json.loads((WS / "paths.local.json").read_text()) if (WS / "paths.local.json").exists() else {}
_ROOT = Path(os.environ.get("AII_DEPS_ROOT", str(WS.parent)))


def _dep(art_id):
    env = os.environ.get("AII_DEP_" + "".join(c if c.isalnum() or c == "_" else "_" for c in art_id))
    return Path(env or _LOC.get("deps", {}).get(art_id) or _ROOT / art_id)


E19, E25, E26, E27, E28, E24 = (_dep("art_mWn-MQEnNelg"), _dep("art_8WbrpoEFslk9"), _dep("art_9a8LrIv2lHbV"),
                                _dep("art_jR6Pyy3W9xum"), _dep("art_hG0QPiaIPNhP"), _dep("art_CcZLW-9NX00l"))
EVAL3 = WS / "inputs" / "eval3"  # vendored copy (inputs/SOURCES.json)
BLOCKS = [str(b) for b in range(12, 24)]
DECISIVE = ["T10", "T2", "T05", "T1", "T03"]
ALL15 = DECISIVE + ["T04", "T06", "T08", "T11", "T13", "T14", "R1", "R2", "R3", "R6"]
DEFAULT = {"T03": "full_sort", "T2": "dijkstra", "T05": "hash_map", "T10": "union_find", "T1": "bfs"}


def jl(p):
    with open(p) as f:
        for ln in f:
            if ln.strip():
                yield json.loads(ln)


def dictish(x):
    return x if isinstance(x, dict) else ast.literal_eval(x)


# ------------------------------------------------------------------------------------------------ stdlib statistics
def ranks(xs):
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0] * len(xs)
    i = 0
    while i < len(xs):
        j = i
        while j + 1 < len(xs) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def pearson(a, b):
    ma, mb = statistics.fmean(a), statistics.fmean(b)
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    den = math.sqrt(sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b))
    return num / den if den else float("nan")


def spearman(a, b):
    return pearson(ranks(a), ranks(b))


def pb_upper(ps, k):
    pmf = [1.0]
    for p in ps:
        new = [0.0] * (len(pmf) + 1)
        for i, q in enumerate(pmf):
            new[i] += q * (1 - p)
            new[i + 1] += q * p
        pmf = new
    return sum(pmf[k:])


def hyper(k, K, n, N):
    return math.comb(K, k) * math.comb(N - K, n - k) / math.comb(N, n)


def fisher2(a, b, c, d):
    K, n, N = a + c, a + b, a + b + c + d
    obs = hyper(a, K, n, N)
    lo, hi = max(0, n + K - N), min(K, n)
    return min(1.0, sum(hyper(k, K, n, N) for k in range(lo, hi + 1) if hyper(k, K, n, N) <= obs * (1 + 1e-7)))


def binom_cdf(k, n, p):
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(0, k + 1))


def mcnemar(b, c):
    n = b + c
    return 1.0 if n == 0 else min(1.0, 2 * binom_cdf(min(b, c), n, 0.5))


def wilcoxon_greater(d):
    d = [x for x in d if x != 0]
    r = ranks([abs(x) for x in d])
    w = sum(ri for ri, x in zip(r, d) if x > 0)
    n = len(d)
    cnt = 0
    for mask in range(2 ** n):
        s = sum(r[i] for i in range(n) if mask >> i & 1)
        cnt += s >= w - 1e-12
    return cnt / 2 ** n


def bw_ci(r, n):
    z = math.atanh(r)
    h = statistics.NormalDist().inv_cdf(0.975) * math.sqrt((1 + r * r / 2) / (n - 3))
    return math.tanh(z - h), math.tanh(z + h)


# ------------------------------------------------------------------------------------------------ checks
CHECKS = []


def check(name, ours, theirs, tol):
    ok = (ours is None and theirs is None) or (ours is not None and theirs is not None and abs(float(ours) - float(theirs)) <= tol)
    CHECKS.append({"name": name, "rederived": ours, "eval": theirs, "tol": tol, "ok": bool(ok)})


# ------------------------------------------------------------------------------------------------ extra headlines
BENCH_DIRS = {"T03": "T03_kth_smallest", "T04": "T04_substring_search", "T05": "T05_two_sum", "T06": "T06_find_duplicate",
              "T08": "T08_fibonacci", "T10": "T10_connected_components", "T11": "T11_longest_increasing_subsequence",
              "T13": "T13_merge_intervals", "T14": "T14_top_k_frequent", "R1": "R1_non_overlapping_intervals",
              "R2": "R2_cycle_detection", "R3": "R3_topological_order", "R6": "R6_first_last_position"}
PATH_CAT = {"T1": ["bfs", "dfs", "bibfs", "iddfs", "astar_gbfs", "dijkstra"], "T2": ["dijkstra", "bf_spfa", "bidijkstra", "floyd", "dial"]}


def binom_sf_ge(k, n, p):
    return 1.0 - (binom_cdf(k - 1, n, p) if k > 0 else 0.0)


def cp_lower(k, n):
    if k == 0:
        return 0.0
    lo, hi = 0.0, 1.0
    for _ in range(80):  # P(X >= k | p) = 0.025
        mid = (lo + hi) / 2
        if binom_sf_ge(k, n, mid) < 0.025:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def interp(x, xs, ys):
    for (x0, y0), (x1, y1) in zip(zip(xs, ys), zip(xs[1:], ys[1:])):
        if x0 <= x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return ys[-1] if x > xs[-1] else ys[0]


def extra_checks(S, F_m, mpr, rmn, kk):
    pa = {u["unit_id"]: u for u in json.loads((E25 / "pooled_inputs.json").read_text())["units"]}
    pb = {r["unit_id"]: r for r in json.loads((E26 / "pooled_inputs.json").read_text())["records"]}
    br = json.loads((E24 / "results" / "base_repertoire.json").read_text())["per_task"]
    # (1) runtime merit for all 30 units from the raw per-reference timings
    rows = [r for r in json.loads((WS / "retime" / "raw_times.json").read_text())["rows"] if r]
    merit = {}
    for u in F_m["units"]:
        if u.startswith("A"):  # panel A unit (pooled_inputs also lists the existing tasks, without catalogues)
            dflt, cat = pa[u]["default"], pa[u]["catalogue"]
        elif u.startswith("B"):
            dflt, cat = pb[u]["unit_facts"]["default"], pb[u]["unit_facts"]["catalogue"]
        else:
            dflt = br[u]["default"]
            cat = PATH_CAT[u] if u in PATH_CAT else [c["mode"] for c in json.loads(
                (E25 / "inputs" / "exp11" / "bench" / BENCH_DIRS[u] / "spec.json").read_text())["catalogue"]]
        best = {}
        for r in rows:
            if r["unit"] == u and r.get("passes_all") and r.get("t_median") is not None:
                best[r["mode"]] = min(best.get(r["mode"], float("inf")), statistics.median(r["repeats"]))
        alts = [t for m, t in best.items() if m != dflt and m in cat]
        merit[u] = math.log2(best[dflt] / min(alts)) if dflt in best and alts else None
        check(f"runtime merit {u}", merit[u], F_m["units"][u]["runtime_merit"], 1e-9)
    # (2) R6 rho on the 13 primary units, E from the raw pooled inputs
    p13 = ["A1", "A2", "A3", "A4", "A5", "A7", "B1", "B2", "B3", "B4", "B5", "B6", "B7"]
    E = {u: (pa[u]["escape"]["E"] if u in pa else pb[u]["outcomes"]["E_u"]) for u in p13}
    r6 = spearman([merit[u] for u in p13], [E[u] for u in p13])
    ev = next(x for x in S["0c"]["rivals"] if x["units"] == "primary13" and x["rival"] == "R6_runtime_merit")
    check("R6 runtime merit rho n13", r6, ev["rho"], 0.005)
    # (3) Fieller interval n13
    beta = {u: (pa[u]["base"]["beta"] if u in pa else pb[u]["base"]["beta_u"]) for u in p13}
    r13 = spearman([beta[u] for u in p13], [E[u] for u in p13])
    h = statistics.NormalDist().inv_cdf(0.975) * math.sqrt(1.06 / 10)
    ci = next(x for x in S["0c"]["ci"] if x["units"] == "primary13" and x["beta"] == "beta_iter5_committed")
    check("Fieller lo n13", math.tanh(math.atanh(r13) - h), ci["fieller_95"][0], 0.005)
    check("Fieller hi n13", math.tanh(math.atanh(r13) + h), ci["fieller_95"][1], 0.005)
    # (4) dose-matched exact binomial p (correct off-default shares, linear interpolation over the 8-bit alpha grid)
    sw = json.loads((E19 / "results" / "alpha_sweep.json").read_text())
    grid = [0.0, 0.5, 1.0, 2.0, 4.0]
    dm = {(x["task"], x["alpha_bf16"], x["definition"]): x for x in S["0a"]["dose_matched"]}
    for t, a, dname in (("T10", 2.0, "D_mpr"), ("T10", 2.0, "D_rmn"), ("T2", 1.0, "D_rmn"), ("T2", 2.0, "D_rmn"),
                        ("T03", 1.0, "D_rmn"), ("T1", 2.0, "D_mpr")):
        ks = []
        for g in grid:
            e = next(x for x in sw[t]["sweep"] if float(x["alpha"]) == g)
            ks.append((sum(v for m, v in e["correct_comp"].items() if m != DEFAULT[t]), int(e["n"])))
        D = statistics.fmean(mpr[t]) if dname == "D_mpr" else rmn[t]
        p8 = interp(a * D, grid, [k / n for k, n in ks])
        p8lo = interp(a * D, grid, [cp_lower(k, n) for k, n in ks])
        kb, nb = kk[(t, a)][0], kk[(t, a)][1]
        check(f"dose-matched p {t} a{int(a)} {dname}", binom_cdf(kb, nb, p8), dm[(t, a, dname)]["p_binom_le_x"], 1e-6)
        check(f"dose-matched conservative p {t} a{int(a)} {dname}", binom_cdf(kb, nb, p8lo), dm[(t, a, dname)]["p_binom_conservative"], 2e-3)
    # (5) one power cell by an independent stdlib simulation (bivariate normal, n 13, rho 0.6)
    rnd = random.Random(7013)
    def sim(rho, n, m):
        r = 2 * math.sin(math.pi * rho / 6)
        out = []
        for _ in range(m):
            x = [rnd.gauss(0, 1) for _ in range(n)]
            y = [r * xi + math.sqrt(1 - r * r) * rnd.gauss(0, 1) for xi in x]
            out.append(spearman(x, y))
        return out
    null = sorted(sim(0.0, 13, 4000))
    crit = null[int(math.ceil(0.95 * len(null))) - 1]
    pw = statistics.fmean([r >= crit for r in sim(0.6, 13, 3000)])
    evp = next(x for x in S["0c"]["power"]["rows"] if x["generator"] == "a" and x["n"] == 13 and x["rho"] == 0.6)
    check("power bivariate normal n13 rho0.6 (MC, tol 0.04)", pw, evp["power"], 0.04)
    # (6) no cached third-family judge response anywhere is NOVEL_ALGORITHM
    nov = 0
    for ln in (WS / "results" / "judge_cache.jsonl").read_text().splitlines():
        raw = json.loads(ln).get("raw", "")
        k = raw.find("{")
        try:
            cls = json.loads(raw[k: raw.rfind("}") + 1]).get("class", "") if k >= 0 else ""
        except json.JSONDecodeError:
            cls = ""
        nov += cls.strip().upper() == "NOVEL_ALGORITHM"
    check("judge responses classed NOVEL (all judges, both passes)", nov, 0, 0)
    # (7) twin-minority rival: no event where t_u and the base runner-up disagree on a hit
    a2 = json.loads((E25 / "results" / "a2_assoc_corrected.json").read_text())["events"]
    b2 = json.loads((E26 / "results" / "a2_panel.json").read_text())["events"]
    e2 = json.loads((E28 / "results" / "e_a2.json").read_text())["events"]
    pr = json.loads((E28 / "results" / "predictors.json").read_text())["units"]
    disc = defined = 0
    for evs, twin in ((a2, lambda u: (pa[u]["twin"]["comp_correct"], pa[u]["default"], "L", "r")),
                      (b2, lambda u: (pb[u]["twin"]["correct_composition"], pb[u]["unit_facts"]["default"], "push_landing", "r_u")),
                      (e2, lambda u: (pr[u]["default"]["correct_counts"], pr[u]["default"]["D"], "landing", "r_u"))):
        for x in evs:
            comp, d, lk, rk = twin(x["unit"])
            alts = sorted(((-int(v), k) for k, v in comp.items() if k not in (d, "other") and int(v) > 0))
            if not alts:
                continue
            defined += 1
            tu = alts[0][1]
            disc += (tu == x[lk]) != (x[rk] == x[lk])
    tws = [r for r in S["0b"]["twin_rival"] if r["scope"] in ("QWEN_NEW_A+B", "GEMMA")]
    check("t_u defined events (new units + Gemma)", defined, sum(r["t_u_defined"] for r in tws), 0)
    check("t_u vs base runner-up discordant hits (new units + Gemma)", disc,
          sum(r["r_u_only_hits"] + r["t_u_only_hits"] for r in tws), 0)


def main():
    S = json.loads((WS / "results" / "s3_analyses.json").read_text())
    F_m = json.loads((WS / "frozen" / "m_candidates.json").read_text())
    # ---- A. dose: D_mpr and D_rmn from raw rows
    mpr = {}
    for r in jl(E27 / "data" / "samples_raw.jsonl"):
        if r.get("arm") in ("PN_a1", "PN_a2") and r.get("unit_ratio_banfree_over_ban"):
            vals = list(r["unit_ratio_banfree_over_ban"].values())
            mpr.setdefault(r["task"], []).append(sum(vals) / len(vals))
    s27, s19 = {}, {}
    for r in jl(E27 / "data" / "realised.jsonl"):
        if r.get("arm") in ("PN_a1", "PN_a2"):
            tm = dictish(r["target_mean"])
            for bl in BLOCKS:
                s27.setdefault(r["task"], {}).setdefault(bl, []).append(float(tm[bl]) / float(r["alpha"]))
    for r in jl(E19 / "data" / "realised.jsonl"):
        if str(r.get("arm", "")).startswith("PN_a"):
            tm = dictish(r["target_mean"])
            for bl in BLOCKS:
                if bl in tm:
                    s19.setdefault(r["task"], {}).setdefault(bl, []).append(float(tm[bl]) / float(r["alpha"]))
    ev_dose = {x["task"]: x for x in S["0a"]["dose"]["rows"] if "D_rmn" in x}
    rmn, blockratio = {}, {}
    for t in ALL15:
        a27 = {bl: statistics.fmean(s27[t][bl]) for bl in BLOCKS}
        a19 = {bl: statistics.fmean(s19[t][bl]) for bl in BLOCKS}
        rmn[t] = sum(a27.values()) / sum(a19.values())
        blockratio[t] = ({bl: a27[bl] / a19[bl] for bl in BLOCKS}, {bl: a19[bl] / sum(a19.values()) for bl in BLOCKS})
        check(f"D_mpr {t}", statistics.fmean(mpr[t]), ev_dose[t]["D_mpr"], 0.005)
        check(f"D_rmn {t}", rmn[t], ev_dose[t]["D_rmn"], 0.005)
        ident = sum(blockratio[t][1][bl] * blockratio[t][0][bl] for bl in BLOCKS)
        check(f"identity {t}", ident - rmn[t], 0.0, 1e-9)
    # ---- B. engine contrast (correct-only shares) and Fisher p at alpha 2
    cells = json.loads((E27 / "results" / "cells.json").read_text())
    sw = json.loads((E19 / "results" / "alpha_sweep.json").read_text())
    ev_con = {(x["task"], x["alpha"]): x for x in S["0a"]["contrast"]}
    kk = {}
    for t in DECISIVE:
        for a in (1.0, 2.0):
            c = cells[f"{t}|PN_a{int(a)}"]
            kb = round(float(c["correct_only_off_default_share"]) * int(c["N"]))
            e = next(x for x in sw[t]["sweep"] if float(x["alpha"]) == a)
            k8 = sum(v for m, v in e["correct_comp"].items() if m != DEFAULT[t])
            kk[(t, a)] = (kb, int(c["N"]), k8, int(e["n"]))
            check(f"bf16 correct off-default {t} a{int(a)}", kb / int(c["N"]), ev_con[(t, a)]["bf16_share"], 0.005)
            check(f"FP8 correct off-default {t} a{int(a)}", k8 / int(e["n"]), ev_con[(t, a)]["fp8_share_correct"], 0.005)
            if a == 2.0:
                p = fisher2(k8, int(e["n"]) - k8, kb, int(c["N"]) - kb)
                q = ev_con[(t, a)]["fisher_p_correct_only"]
                check(f"Fisher p {t} a2 (log10)", math.log10(p), math.log10(q), 0.05)
    # ---- C. landing tallies from the raw result files
    a2 = json.loads((E25 / "results" / "a2_assoc_corrected.json").read_text())
    b2 = json.loads((E26 / "results" / "a2_panel.json").read_text())
    e2 = json.loads((E28 / "results" / "e_a2.json").read_text())
    sc = json.loads((E24 / "results" / "screen_check.json").read_text())["r_t_vs_push_landing"]
    xa = json.loads((E25 / "results" / "extra_arm_a.json").read_text())
    br = json.loads((E24 / "results" / "base_repertoire.json").read_text())["per_task"]
    new = [(bool(x["hit"]), float(x["chance"]), x["unit"]) for x in a2["events"]] + \
          [(bool(x["hit"]), float(x["chance"]), x["unit"]) for x in b2["events"]]
    gem = [(x["r_u"] == x["landing"], float(ch), x["unit"]) for x, ch in zip(e2["events"], e2["chance"])]
    T = S["0b"]["tallies"]
    for name, evs in (("QWEN_NEW_A+B", new), ("GEMMA", gem)):
        h = sum(x[0] for x in evs)
        check(f"hits {name}", h, T[name]["hits"], 0)
        check(f"Poisson-binomial p {name}", pb_upper([x[1] for x in evs], h), T[name]["p_poisson_binomial"], 1e-6)
    check("FP8 screen hits", sum(bool(v["agree"]) for v in sc.values()), T["QWEN_FP8_SCREEN"]["hits"], 0)
    bf = [(br[t]["r_t"] == xa[t]["landing"]) for t in ("T10", "T03")]
    check("bf16 remeasure hits", sum(bf), T["QWEN_BF16_REMEASURE"]["hits"], 0)
    check("all-event hits", sum(x[0] for x in new) + sum(x[0] for x in gem) + sum(bool(v["agree"]) for v in sc.values()) + sum(bf),
          T["ALL21"]["hits"], 0)
    # unconfounded subset: twin with no correct non-default program
    pa = {u["unit_id"]: u for u in json.loads((E25 / "pooled_inputs.json").read_text())["units"]}
    pb = {r["unit_id"]: r for r in json.loads((E26 / "pooled_inputs.json").read_text())["records"]}
    pr = json.loads((E28 / "results" / "predictors.json").read_text())["units"]
    def clean_twin(u, family):
        if family == "gemma":
            c, d = pr[u]["default"]["correct_counts"], pr[u]["default"]["D"]
        elif u in pb:
            c, d = pb[u]["twin"]["correct_composition"], pb[u]["unit_facts"]["default"]
        else:
            c, d = pa[u]["twin"]["comp_correct"], pa[u]["default"]
        return not any(int(v) > 0 for k, v in c.items() if k not in (d, "other"))
    un_q = [x for x in new if clean_twin(x[2], "qwen")]
    un_g = [x for x in gem if clean_twin(x[2], "gemma")]
    U = S["0b"]["unconfounded"]
    for name, evs in (("QWEN_NEW_A+B", un_q), ("GEMMA", un_g), ("POOLED", un_q + un_g)):
        h = sum(x[0] for x in evs)
        check(f"unconfounded hits {name}", h, U[name]["hits"], 0)
        check(f"unconfounded p {name}", pb_upper([x[1] for x in evs], h), U[name]["p_poisson_binomial"], 1e-6)
    # ---- D. movability rho with the committed betas
    beta = {u: pa[u]["base"]["beta"] for u in ("A1", "A2", "A3", "A4", "A5", "A7", "A8", "A9")}
    beta.update({u: pb[u]["base"]["beta_u"] for u in ("B1", "B2", "B3", "B4", "B5", "B6", "B7")})
    E = {u: pa[u]["escape"]["E"] for u in ("A1", "A2", "A3", "A4", "A5", "A7", "A8", "A9")}
    E.update({u: pb[u]["outcomes"]["E_u"] for u in ("B1", "B2", "B3", "B4", "B5", "B6", "B7")})
    p13 = ["A1", "A2", "A3", "A4", "A5", "A7", "B1", "B2", "B3", "B4", "B5", "B6", "B7"]
    ci = {(x["units"], x["beta"]): x for x in S["0c"]["ci"]}
    r13 = spearman([beta[u] for u in p13], [E[u] for u in p13])
    r15 = spearman([beta[u] for u in beta], [E[u] for u in beta])
    check("rho n13", r13, ci[("primary13", "beta_iter5_committed")]["rho"], 0.005)
    check("rho n15", r15, ci[("with_A8_A9_15", "beta_iter5_committed")]["rho"], 0.005)
    lo, hi = bw_ci(r13, 13)
    check("Bonett-Wright lo n13", lo, ci[("primary13", "beta_iter5_committed")]["bonett_wright_95"][0], 0.005)
    check("Bonett-Wright hi n13", hi, ci[("primary13", "beta_iter5_committed")]["bonett_wright_95"][1], 0.005)
    # ---- E. phrasing, pn_vs_dmd, Gemma fill, novelty audit, Table 126c
    L = json.loads((E27 / "results" / "literal_cell.json").read_text())["per_T"]
    for k, ph in zip(("LIT_T0.3", "LIT_T0.7", "LIT_T1.0", "LIT_T1.3", "LIT_REP_T0.7"), S["0d"]["phrasing"]):
        for th in ("0.7", "0.8", "0.9"):
            raw = L[k]["phrasing"][f"theta_{th}"]
            check(f"phrasing {k} theta {th}", raw["n_clusters"] if isinstance(raw, dict) else raw, ph[f"theta_{th}"], 0)
    D = json.loads((E27 / "results" / "pn_vs_dmd.json").read_text())["per_task"]
    b_ = sum(D[t]["alpha2"]["mcnemar_PN_vs_DMD"]["x_only"] for t in DECISIVE)
    c_ = sum(D[t]["alpha2"]["mcnemar_PN_vs_DMD"]["y_only"] for t in DECISIVE)
    t211 = {(x["task"], x["alpha"]): x for x in S["0e"]["t211"]}
    check("PN-only alpha 2 pooled", b_, t211[("POOLED_D5", "alpha2")]["PN_only"], 0)
    check("DMD-only alpha 2 pooled", c_, t211[("POOLED_D5", "alpha2")]["DMD_only"], 0)
    check("McNemar p alpha 2 pooled", mcnemar(b_, c_), t211[("POOLED_D5", "alpha2")]["p_exact_recomputed"], 1e-9)
    d7 = [x["q_base"] - x["q_assoc"] for x in e2["log_scores"]]
    d6 = [x["q_base"] - x["q_assoc"] for x in e2["log_scores"] if x["q_assoc_defined"]]
    gf = S["0e"]["gemma_fill"]
    check("Gemma fill mean all 7", statistics.fmean(d7), gf[0]["mean"], 1e-9)
    check("Gemma fill mean defined 6", statistics.fmean(d6), gf[1]["mean"], 1e-9)
    check("Gemma fill Wilcoxon all 7", wilcoxon_greater(d7), gf[0]["wilcoxon_exact_p_one_sided"], 1e-9)
    check("Gemma fill Wilcoxon defined 6", wilcoxon_greater(d6), gf[1]["wilcoxon_exact_p_one_sided"], 1e-9)
    na = json.loads((E24 / "results" / "novelty_audit.json").read_text())
    check("novelty items NOVEL (judges)", sum(1 for it in na["items"] if it["final_class"] == "NOVEL_ALGORITHM"), 14, 0)
    check("novelty items NOVEL (manual)", sum(1 for it in na["items"] if "NOVEL" in str(it.get("manual_class", ""))), 0, 0)
    rows = {r["row_id"]: r for r in csv.DictReader(open(EVAL3 / "tables" / "knob_table.csv"))}
    for r in S["0d"]["t126c"]:
        check(f"Table 126c {r['row_id']}", float(rows[r["row_id"]]["H1r25"]), r["H1r25"], 1e-9)
    extra_checks(S, F_m, mpr, rmn, kk)
    # ---- placebos (must FAIL to reproduce the effects)
    rnd = random.Random(6012)
    all_ev = [(x[0], x[1]) for x in new + gem] + [(True, 1 / 5), (True, 1 / 4), (True, 1 / 3), (True, 1 / 3), (True, 1 / 5)] + \
             [(bf[0], 1 / 3), (bf[1], 1 / 5)]
    p1 = []
    for _ in range(200):
        hits = [rnd.random() < ch for _, ch in all_ev]
        p1.append(pb_upper([ch for _, ch in all_ev], sum(hits)))
    p2, p2s = [], []
    es = [E[u] for u in p13]
    for _ in range(200):
        perm = es[:]
        rnd.shuffle(perm)
        rr_ = spearman([beta[u] for u in p13], perm)
        p2.append(abs(rr_))
        p2s.append(rr_)
    p3 = []
    for (t, a), (kb, nb, k8, n8) in kk.items():
        for _ in range(20):
            pool = [1] * (kb + k8) + [0] * (nb + n8 - kb - k8)
            rnd.shuffle(pool)
            x, y = sum(pool[:n8]), sum(pool[n8:])
            p3.append(fisher2(x, n8 - x, y, nb - y))
    p4 = []
    for _ in range(200):
        p4.append(statistics.fmean([rnd.random() < ch for _, ch in all_ev]))
    p5 = []
    for t in DECISIVE:
        rr, _ = blockratio[t]
        for _ in range(100):
            w = [rnd.gammavariate(1, 1) for _ in BLOCKS]
            s = sum(w)
            p5.append(abs(sum(wi / s * rr[bl] for wi, bl in zip(w, BLOCKS)) - rmn[t]) > 0.01)
    plac = {"P1_landing_permuted_median_p": statistics.median(p1), "P1_fails_as_required": statistics.median(p1) > 0.2,
            "P2_E_permuted_median_abs_rho": statistics.median(p2), "P2_E_permuted_median_signed_rho": statistics.median(p2s),
            "P2_fails_as_required": statistics.median(p2) < 0.1,
            "P2_signed_median_below_0.1": abs(statistics.median(p2s)) < 0.1,
            "P2_note": "the plan's criterion (median |rho| below 0.1) cannot be met at n 13: under any permutation null the "
                       "median |rho| is about 0.67/sqrt(n-1) = 0.19; the signed median is beside. P2 is uninformative here "
                       "because the observed rho (0.15) is itself inside the null band.",
            "P3_engine_permuted_median_fisher_p": statistics.median(p3), "P3_fails_as_required": statistics.median(p3) > 0.3,
            "P4_random_t_u_hit_rate": statistics.fmean(p4), "P4_mean_chance": statistics.fmean([ch for _, ch in all_ev]),
            "P4_fails_as_required": abs(statistics.fmean(p4) - statistics.fmean([ch for _, ch in all_ev])) < 0.05,
            "P5_share_random_weights_breaking_identity": statistics.fmean(p5), "P5_fails_as_required": statistics.fmean(p5) > 0.5}
    n_fail = sum(1 for k, v in plac.items() if k.endswith("fails_as_required") and v)
    # ---- chain and mtimes
    prev = hashlib.sha256(b"iter6_step0").hexdigest()
    chain_ok = True
    frozen_mt = []
    for ln in (WS / "commitments.log").read_text().splitlines():
        if not ln.strip():
            continue
        utc, f, sha, p, ch = ln.split(" | ")
        fsha = hashlib.sha256((WS / f).read_bytes()).hexdigest()
        chain_ok &= (p == prev and fsha == sha and hashlib.sha256((prev + sha).encode()).hexdigest() == ch)
        prev = ch
        frozen_mt.append(os.path.getmtime(WS / f))
    s3_files = [WS / "results" / "s3_analyses.json"] + sorted((WS / "tables").glob("*.csv"))
    s3_mt = [os.path.getmtime(p) for p in s3_files]
    predate = max(frozen_mt) < min(s3_mt)
    n_mis = sum(1 for c in CHECKS if not c["ok"])
    res = {"n_checks": len(CHECKS), "n_mismatches": n_mis, "mismatches": [c for c in CHECKS if not c["ok"]],
           "checks": CHECKS, "placebos_failing": n_fail, "n_placebos": 5, "chain_ok": bool(chain_ok),
           "frozen_predate_s3": bool(predate), "frozen_max_mtime": max(frozen_mt), "s3_min_mtime": min(s3_mt)}
    (WS / "audit" / "rederive_result.json").write_text(json.dumps(res, indent=1))
    (WS / "audit" / "placebos.json").write_text(json.dumps(plac, indent=1))
    print(f"checks {len(CHECKS)}, mismatches {n_mis}; placebos failing as required {n_fail}/5; chain {chain_ok}; frozen predate S3 {predate}")
    for c in CHECKS:
        if not c["ok"]:
            print("MISMATCH", c)


if __name__ == "__main__":
    main()
