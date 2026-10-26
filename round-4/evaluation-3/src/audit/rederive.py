#!/usr/bin/env python3
"""Independent re-derivation of the headline numbers (pure Python + collections; imports nothing from src/).

Re-reads the raw dependency files and recomputes: verification targets (counts exact, Hill +-0.03, pass +-0.005),
E_t / movable and the screen core JSON (sha256 must match screen.sha256 byte for byte), the Llama hit counts and
Poisson-binomial p-values, the exp16 route fractions with and without T13, catalogue-only avoidance per event,
the Table 82 hits and the 0j Spearman values. Writes audit/rederive.json.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

def _dep(aid: str, env: str, folder: str) -> str:
    """AII_ITERn or the unpublished paths.local.json on the run server; else the published sibling folder under
    AII_DEPS_DIR (default: this workspace's parent), named by artifact id or by the original folder name."""
    base = os.environ.get(env)
    loc = Path(__file__).resolve().parent.parent / "paths.local.json"
    if not base and loc.exists():
        base = json.loads(loc.read_text()).get(env)
    if base:
        return f"{base}/{folder}"
    deps = Path(os.environ.get("AII_DEPS_DIR") or Path(__file__).resolve().parent.parent.parent)
    for cand in (deps / aid, deps / folder, *sorted(deps.glob(f"*{aid}*"))):
        if cand.is_dir():
            return str(cand)
    raise FileNotFoundError(f"dependency {aid} ({folder}) not found; set AII_DEPS_DIR or {env}")

WS = Path(__file__).resolve().parent.parent
DEPS = {"exp4": ("art_U5UKkFrOgSsE", "AII_ITER1", "experiment-4/src"),
        "exp6": ("art_UoCVh2Qe5RZ0", "AII_ITER1", "experiment-6/src"),
        "exp7": ("art_6zBfl3kDjeiP", "AII_ITER2", "experiment-7/src"),
        "exp9": ("art_IVZc3TWCeE9f", "AII_ITER2", "experiment-9/src"),
        "exp11": ("art_0ndRfWKBWclR", "AII_ITER2", "experiment-11/src"),
        "exp13": ("art_1AYTO1Epb_7t", "AII_ITER3", "experiment-13/src"),
        "exp14": ("art_WiY4wqHLb9Gy", "AII_ITER3", "experiment-14/src"),
        "exp15": ("art_Q-qh-9HhPoWo", "AII_ITER3", "experiment-15/src"),
        "exp16": ("art__5akZ9W9iZM4", "AII_ITER3", "experiment-16/src"),
        "exp17": ("art_pVlCZ272hDV7", "AII_ITER3", "experiment-17/src")}
E = {k: _dep(*v) for k, v in DEPS.items()}
AID = {"exp9": "art_IVZc3TWCeE9f", "exp13": "art_1AYTO1Epb_7t", "exp17": "art_pVlCZ272hDV7"}
BENCH = {"T03": "T03_kth_smallest", "T04": "T04_substring_search", "T05": "T05_two_sum", "T06": "T06_find_duplicate",
         "T08": "T08_fibonacci", "T10": "T10_connected_components", "T11": "T11_longest_increasing_subsequence",
         "T13": "T13_merge_intervals", "T14": "T14_top_k_frequent", "R1": "R1_non_overlapping_intervals",
         "R3": "R3_topological_order", "R6": "R6_first_last_position"}
DEF = {"T03": "full_sort", "T04": "naive", "T05": "hash_map", "T06": "hash_set", "T08": "iteration", "T10": "union_find",
       "T11": "quadratic_dp", "T13": "sort_sweep", "T14": "sort_by_count", "R1": "greedy_end", "R3": "kahn",
       "R6": "binary_search", "T1": "bfs", "T2": "dijkstra"}
TASKS14 = ["T03", "T04", "T05", "T06", "T08", "T10", "T11", "T13", "T14", "R1", "R3", "R6", "T1", "T2"]
NOATT = {"invalid", "no_code", "unparseable", "disputed", "unresolved", "extraction_failed", "", "None", "none"}
ALIAS = {"bellman_ford_spfa": "bf_spfa", "bidirectional_bfs": "bibfs", "floyd_warshall": "floyd",
         "bidirectional_dijkstra": "bidijkstra", "astar_greedy": "astar", "astar_gbfs": "astar"}


def jl(path):
    with open(path) as f:
        return [json.loads(x) for x in f if x.strip()]


def tru(v):
    return v is True or str(v) == "True"


def lab(v):
    s = "no_code" if v is None else str(v)
    return ALIAS.get(s, s)


def cat(task):
    if task == "T1":
        return ["bfs", "dfs", "bibfs", "iddfs", "astar", "gbfs", "idastar", "dijkstra_unit"]
    if task == "T2":
        return ["dijkstra", "bf_spfa", "bidijkstra", "floyd", "dial"]
    return [c["mode"] for c in json.load(open(f"{E['exp11']}/bench/{BENCH[task]}/spec.json"))["catalogue"]]


def sha_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()


def hill_rarefied(labels, depth=25, draws=2000, seed=7):
    if len(labels) < depth:
        return None
    if len(set(labels)) == 1:
        return 1.0
    rnd = random.Random(seed)
    tot = 0.0
    for _ in range(draws):
        s = Counter(rnd.sample(labels, depth))
        tot += math.exp(-sum((c / depth) * math.log(c / depth) for c in s.values()))
    return tot / draws


class Cell:
    def __init__(self, rows, task):
        self.n = len(rows)
        att = [r for r in rows if r["label"] not in NOATT]
        self.na = len(att)
        self.nd = sum(1 for r in att if r["label"] == DEF[task])
        self.np = sum(1 for r in rows if r["passed"])
        self.correct = [r["label"] for r in rows if r["passed"]]
        c = set(cat(task))
        self.offcat = Counter(r["label"] for r in att if r["label"] in c and r["label"] != DEF[task])
        self.n_catnd = sum(self.offcat.values())

    def off(self):
        return 1 - self.nd / self.na if self.na else None

    def pas(self):
        return self.np / self.n if self.n else None


def esc(d, t):
    return (d.off() - t.off()) >= 0.20 - 1e-9 and d.pas() >= 0.8 * t.pas() - 1e-12, d.off() - t.off()


def main():
    out = {"checks": [], "mismatches": []}

    def check(name, got, exp, ok):
        out["checks"].append({"name": name, "rederived": got, "expected": exp, "match": bool(ok)})
        if not ok:
            out["mismatches"].append(name)

    # ---------------- exp17 / exp13 random directions
    g17 = defaultdict(list)
    for r in jl(f"{E['exp17']}/data/labels.jsonl"):
        g17[(r["task"], r["arm"])].append({"label": lab(r["label"]), "passed": tru(r["passed"])})
    g13 = defaultdict(list)
    for r in jl(f"{E['exp13']}/data/samples.jsonl"):
        g13[(r["task"], r["condition"])].append({"label": lab(r["label"]), "passed": tru(r["passed"]),
                                                 "template": r["template"]})
    dirs = []  # (task, alpha, id, engine, cell, twin)
    for (t, a), rows in g17.items():
        if a.startswith("RAND"):
            did, al = a.split("_a")
            dirs.append((t, float(al), "exp17:" + did, "hf-fp8", Cell(rows, t), Cell(g17[(t, "NEUTRAL")], t)))
    for (t, a), rows in g13.items():
        if a in ("rand1", "rand2", "rand3"):
            dirs.append((t, 1.0, "exp13:" + a, "hf-bf16", Cell(rows, t), Cell(g13[(t, "hf_twin")], t)))
    # targets
    t03 = [d for d in dirs if d[0] == "T03" and d[1] == 1.0 and d[3] == "hf-fp8"]
    e03 = [d for d in t03 if esc(d[4], d[5])[0]]
    check("T03_a1_escape", f"{len(e03)}/{len(t03)}", "7/15", len(e03) == 7 and len(t03) == 15)
    hs = sorted([hill_rarefied(d[4].correct) for d in e03 if d[4].pas() >= 0.96], reverse=True)[:5]
    exp_h = [2.92, 2.42, 2.32, 2.14, 2.10]
    check("T03_a1_hill", [round(h, 3) for h in hs], exp_h, len(hs) == 5 and all(abs(a - b) <= 0.03 for a, b in zip(hs, exp_h)))
    t2 = [d for d in dirs if d[0] == "T2" and d[1] == 1.0]
    e2 = [d for d in t2 if esc(d[4], d[5])[0]]
    check("T2_a1_escape", f"{len(e2)}/{len(t2)}", "3/15", len(e2) == 3 and len(t2) == 15)
    check("T2_landing", sorted({k for d in e2 for k in d[4].offcat}), ["bf_spfa"],
          sorted({k for d in e2 for k in d[4].offcat}) == ["bf_spfa"])
    for task, al, n_exp, n_run in (("T05", 1.0, 0, 3), ("T05", 2.0, 2, 3), ("T06", 2.0, 1, 3)):
        dd = [d for d in dirs if d[0] == task and d[1] == al and d[3] == "hf-fp8"]
        ee = [d for d in dd if esc(d[4], d[5])[0]]
        check(f"{task}_a{int(al)}_escape", f"{len(ee)}/{len(dd)}", f"{n_exp}/{n_run}", len(ee) == n_exp and len(dd) == n_run)
    d4 = [d for d in dirs if d[0] == "T04" and d[3] == "hf-fp8"]
    check("T04_escape", f"{sum(esc(d[4], d[5])[0] for d in d4)}/{len(d4)}", "0/6",
          sum(esc(d[4], d[5])[0] for d in d4) == 0 and len(d4) == 6)
    c = Cell(g13[("T03", "rand3")], "T03")
    cc = Counter(c.correct)
    check("exp13_T03_rand", dict(cc), {"quickselect": 34, "full_sort": 9}, cc["quickselect"] == 34 and cc["full_sort"] == 9)
    c = Cell(g13[("T10", "rand3")], "T10")
    check("exp13_T10_rand", {"dfs": Counter(c.correct)["dfs"], "pass": c.pas()}, {"dfs": 13, "pass": 1.0},
          Counter(c.correct)["dfs"] == 13 and c.pas() == 1.0)
    for task, arm, ref, exp_h1, exp_cost in (("T06", "iter1", "twin", 2.49, 2), ("T08", "novelty", "twin", 1.90, 24),
                                             ("T10", "novelty", "twin", 1.68, 0), ("T10", "bandpatch", "hf_twin", 1.88, 0),
                                             ("T03", "bandpatch", "hf_twin", 1.98, 0), ("T10", "rand3", "hf_twin", 1.76, 0)):
        c, tw = Cell(g13[(task, arm)], task), Cell(g13[(task, ref)], task)
        h1 = hill_rarefied(c.correct)
        cost = 100 * (tw.pas() - c.pas())
        check(f"{task}_{arm}", {"H1r25": round(h1, 3), "cost": round(cost, 1)}, {"H1r25": exp_h1, "cost": exp_cost},
              abs(h1 - exp_h1) <= 0.03 and abs(cost - exp_cost) <= 0.5)
    # exp4 / exp6
    g4 = defaultdict(list)
    for r in jl(f"{E['exp4']}/data/samples.jsonl"):
        g4[(r["task"], r["condition"])].append({"label": lab(r["label"]), "passed": tru(r["passed"])})
    c, tw = Cell(g4[("T2", "steer:dc:c=0.25:L=18")], "T2"), Cell(g4[("T2", "steer:dc:c=0:L=18")], "T2")
    h1 = hill_rarefied(c.correct)
    check("exp4_dc025", {"H1r25": round(h1, 3), "cost": round(100 * (tw.pas() - c.pas()), 1)}, {"H1r25": 1.913, "cost": 17},
          abs(h1 - 1.913) <= 0.03 and abs(100 * (tw.pas() - c.pas()) - 17) <= 0.5)
    g6 = defaultdict(list)
    for r in jl(f"{E['exp6']}/results/samples.jsonl"):
        g6[(r["task"], r["arm"] + ":" + r["condition"])].append({"label": lab(r["label"]), "passed": tru(r["passed"])})
    h1 = hill_rarefied(Cell(g6[("T2", "A2:seed_semantic")], "T2").correct)
    check("exp6_semantic", round(h1, 3), 1.94, abs(h1 - 1.94) <= 0.03)

    # ---------------- screen core (independent implementation of the published rule)
    g9 = defaultdict(list)
    for r in jl(f"{E['exp9']}/data/samples.jsonl"):
        t = {"t1": "T1", "t2": "T2"}.get(r["task"], r["task"])
        g9[(t, r["condition"])].append({"label": lab(r["label"]), "passed": tru(r["passed"])})
    av = {}
    for t in TASKS14:
        cell = Cell(g13[(t, "ban")], t) if t in BENCH else Cell(g9[(t, "single:bfs" if t == "T1" else "single:dijkstra")], t)
        av[t] = round(cell.n_catnd / cell.na, 6)

    def r4(x):
        if isinstance(x, float):
            return round(x, 4)
        if isinstance(x, dict):
            return {k: r4(v) for k, v in x.items()}
        if isinstance(x, list):
            return [r4(v) for v in x]
        return x

    per = {}
    for t in TASKS14:
        rec, num, den, mov = {}, defaultdict(float), 0.0, 0
        for al in (1.0, 2.0):
            dd = [d for d in dirs if d[0] == t and d[1] == al]
            ne = 0
            for d in dd:
                ok, e = esc(d[4], d[5])
                if ok:
                    ne += 1
                    tot = sum(v for k, v in d[4].offcat.items() if k != "other")
                    if tot:
                        den += e
                        for k, v in d[4].offcat.items():
                            if k != "other" and v > 0:
                                num[k] += e * v / tot
            rec[f"alpha_{int(al)}"] = {"n_directions_run": len(dd), "n_escape": ne, "E_t": (ne / len(dd)) if dd else None}
            if dd and ne:
                mov = 1
        land = {k: v / den for k, v in sorted(num.items())} if den > 0 else {}
        top = sorted(land.items(), key=lambda kv: (-round(kv[1], 12), kv[0]))[0][0] if land else None
        rec.update({"movable": mov, "push_landing": land, "push_top1": top, "cat_only_ban_avoidance": av[t],
                    "ban_avoidance_ge_0_5": bool(av[t] >= 0.5)})
        per[t] = rec
    src = {f"{AID['exp17']}:data/labels.jsonl": sha_file(f"{E['exp17']}/data/labels.jsonl"),
           f"{AID['exp13']}:data/samples.jsonl": sha_file(f"{E['exp13']}/data/samples.jsonl"),
           f"{AID['exp9']}:data/samples.jsonl": sha_file(f"{E['exp9']}/data/samples.jsonl")}
    core = {"screen_version": "iter4-step0", "tasks": per, "c1_event_set": sorted(["T03", "T05", "T06", "T10", "T1", "T2"]),
            "screen_rule": "movable(t) implies catalogue-only modal-ban avoidance(t) >= 0.5",
            "escape_rule": ("escape(d,t,a): offdef(d)-offdef(twin) >= 0.20 and pass(d) >= 0.8*pass(twin); "
                            "offdef = 1 - n_default/n_attempted; pass = n_passed/n (no-code rows fail)"),
            "movable_tasks": sorted(t for t in TASKS14 if per[t]["movable"]), "source_sha256": dict(sorted(src.items()))}
    b = (json.dumps(r4(core), sort_keys=True, ensure_ascii=True, separators=(",", ":")) + "\n").encode("ascii")
    sha = hashlib.sha256(b).hexdigest()
    rec_sha = (WS / "screen.sha256").read_text().split()[0]
    check("screen_core_sha256", sha, rec_sha, sha == rec_sha)
    check("movable_tasks", core["movable_tasks"], ["T03", "T05", "T06", "T1", "T10", "T2"],
          core["movable_tasks"] == ["T03", "T05", "T06", "T1", "T10", "T2"])

    # ---------------- Llama hits ('other' excluded, strict) and Poisson-binomial p
    evs = jl(f"{E['exp15']}/results/c1_events.jsonl")
    fc = json.load(open(f"{E['exp15']}/predictions/forecasts.json"))["events"]
    hits = Counter()
    chances = []
    for e in evs:
        if not e["gate_pass"]:
            continue
        f = fc[e["event_id"]]
        S, X = f["S"], e["banned"]
        nb = Counter()
        for k, v in e["landing_counts"].items():
            if k in ("invalid", "unresolved", "no_code", "disputed") or k == X:
                continue
            nb[k if k in S else "other"] += v
        n = sum(nb.values())
        land = {k: v / n for k, v in nb.items()}
        if e["event_type"] == "modal":
            cand = {k: v for k, v in land.items() if k != "other"}
            L = max(sorted(cand), key=lambda k: cand[k]) if cand else None
        else:
            ex = {k: land.get(k, 0.0) - f["B_S"].get(k, 0.0) for k in S}
            L = max(S, key=lambda k: (ex[k], -S.index(k)))
        chances.append(1 / len(S))
        for fam in ("LADDER", "ASSOCIATE"):
            tp = e["top1"].get(fam)
            hits[fam] += int(tp not in (None, "other") and tp == L)

    def pb_sf(k, ps):
        dist = [1.0] + [0.0] * len(ps)
        for q in ps:
            for i in range(len(ps), 0, -1):
                dist[i] = dist[i] * (1 - q) + dist[i - 1] * q
            dist[0] *= (1 - q)
        return sum(dist[k:])

    check("llama_ladder_excl_other", hits["LADDER"], 6, hits["LADDER"] == 6)
    check("llama_assoc_excl_other", hits["ASSOCIATE"], 7, hits["ASSOCIATE"] == 7)
    out["llama_p"] = {"LADDER": pb_sf(hits["LADDER"], chances), "ASSOCIATE": pb_sf(hits["ASSOCIATE"], chances)}

    # ---------------- route fractions (exp16)
    rows16, seen = [], set()
    for r in jl(f"{E['exp16']}/data/samples.jsonl"):
        if r["uid"] in seen:
            continue
        seen.add(r["uid"])
        rows16.append((r["task"], r["arm"], lab(r["label"])))

    def frac(tasks, mode):
        s = {}
        for t in tasks:
            cs = set(cat(t))
            for a in ("a", "b", "c", "d"):
                ll = [x[2] for x in rows16 if x[0] == t and x[1] == a and x[2] not in ("invalid", "no_code", "disputed")]
                if mode == "plain":
                    nb = sum(1 for x in ll if x == DEF[t])
                else:
                    nb = sum(1 for x in ll if not (x in cs and x != DEF[t]))
                s[(t, a)] = nb / len(ll)
        den = sum(s[(t, "b")] - s[(t, "a")] for t in tasks)
        return (sum(s[(t, "b")] - s[(t, "c")] for t in tasks) / den, sum(s[(t, "b")] - s[(t, "d")] for t in tasks) / den)

    T5 = ["T03", "T05", "T06", "T10", "T13"]
    fp, fd = frac(T5, "plain")
    check("route_all5", [round(fp, 4), round(fd, 4)], [0.6111, 0.744], abs(fp - 0.6111) < 1e-3 and abs(fd - 0.7440) < 1e-3)
    fp2, fd2 = frac([t for t in T5 if t != "T13"], "plain")
    rr = json.load(open(WS / "results" / "route.json"))["route_fractions"]["plain_wo_T13"]["point"]
    check("route_wo_T13", [round(fp2, 4), round(fd2, 4)], [round(rr["F_prompt"], 4), round(rr["F_direct"], 4)],
          abs(fp2 - rr["F_prompt"]) < 1e-9 and abs(fd2 - rr["F_direct"]) < 1e-9)
    fpc, fdc = frac(T5, "cat")
    rc = json.load(open(WS / "results" / "route.json"))["route_fractions"]["cat_all5"]["point"]
    check("route_cat_all5", [round(fpc, 4), round(fdc, 4)], [round(rc["F_prompt"], 4), round(rc["F_direct"], 4)],
          abs(fpc - rc["F_prompt"]) < 1e-9 and abs(fdc - rc["F_direct"]) < 1e-9)

    # ---------------- catalogue-only avoidance per event (exp13 bans vs the knob table)
    import csv
    kt = {}
    with open(WS / "tables" / "knob_table.csv") as f:
        for row in csv.DictReader(f):
            if row["artifact_id"] == AID["exp13"] and row["arm"] == "ban":
                kt[row["task"]] = float(row["cat_only_avoidance"])
    bad = [t for t in BENCH if abs(kt[t] - av[t]) > 1e-9]
    check("cat_only_avoidance_exp13_bans", {t: av[t] for t in BENCH}, kt, not bad)
    check("T13_residue_gated", av["T13"], "< 0.5 with plain >= 0.5", av["T13"] < 0.5)

    # ---------------- Table 82 hits (exp7)
    L = defaultdict(lambda: defaultdict(list))
    for r in jl(f"{E['exp7']}/results/frlp_cells.jsonl"):
        if r.get("variant") != "primary" or r.get("half") != "all":
            continue
        p_ = r["condition"].split("|")
        if (p_[0] == "ban" and len(p_) == 3) or (p_[0] == "neutral" and len(p_) == 4):
            try:
                L[(r["task"], p_[0], p_[1])][r["algorithm"]].append(float(r["L"]))
            except (TypeError, ValueError):
                pass
    lp = json.load(open(f"{E['exp7']}/frozen/ladder_profile.json"))
    ge = json.load(open(f"{E['exp7']}/results/gate_events.json"))["events"]
    real = {}
    import ast as _ast
    for e in ge:
        if e["condition"].startswith("ban:"):
            X = e["condition"].split(":")[1]
            dist = _ast.literal_eval(e["distribution_allowed"]) if isinstance(e["distribution_allowed"], str) else e["distribution_allowed"]
            c_ = {k: v for k, v in dist.items() if k != X and k != "other"}
            m = max(c_.values())
            real[(e["task"], X)] = sorted(k for k, v in c_.items() if v == m)[0]
    dflt = {"t1": "bfs", "t2": "dijkstra"}
    h_imp = h_gain = n_rows = 0
    for (t, kind, X), d in L.items():
        if kind != "ban" or X not in lp[t]["measurable"]:
            continue
        catm = lp[t]["measurable"]
        ban = {j: sum(v) / len(v) for j, v in d.items() if j in catm}
        tw = {j: sum(v) / len(v) for j, v in L[(t, "neutral", X)].items() if j in catm}
        surv = [j for j in catm if j != X and j in ban and j in tw]
        if not surv:
            continue
        n_rows += 1
        realised = real.get((t, X)) if X == dflt[t] else dflt[t]
        h_gain += int(max(surv, key=lambda j: ban[j] - tw[j]) == realised)
        h_imp += int(max(surv, key=lambda j: ban[j]) == realised)
    check("table82", {"rows": n_rows, "gain": h_gain, "implied": h_imp}, {"rows": 11, "gain": 0, "implied": 8},
          n_rows == 11 and h_gain == 0 and h_imp == 8)

    # ---------------- 0j Spearman values
    def ranks(v):
        idx = sorted(range(len(v)), key=lambda i: v[i])
        rk = [0.0] * len(v)
        i = 0
        while i < len(v):
            j = i
            while j + 1 < len(v) and v[idx[j + 1]] == v[idx[i]]:
                j += 1
            for k in range(i, j + 1):
                rk[idx[k]] = (i + j) / 2 + 1
            i = j + 1
        return rk

    def spear(x, y):
        pr = [(a, b) for a, b in zip(x, y) if a == a and b == b and a is not None]
        rx, ry = ranks([a for a, _ in pr]), ranks([b for _, b in pr])
        mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
        num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
        den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
        return num / den if den else float("nan")

    vals = {}
    with open(WS / "tables" / "rival_predictor_values.csv") as f:
        rows_v = list(csv.DictReader(f))
    rec = {}
    with open(WS / "tables" / "rival_predictors.csv") as f:
        for row in csv.DictReader(f):
            rec[row["predictor"]] = float(row["spearman_rho"])
    y = [per[r["task"]]["cat_only_ban_avoidance"] for r in rows_v]
    mov = [float(per[r["task"]]["movable"]) for r in rows_v]
    vals["movable"] = spear(mov, y)
    for k in ("can", "clarity", "frlp_runner_up_mass", "nonce_offdef", "novelty_offdef"):
        x = [float(r[k]) if r[k] not in ("", "nan") else float("nan") for r in rows_v]
        vals[k] = spear(x, y)
    bad = [k for k, v in vals.items() if abs(v - rec[k]) > 1e-9]
    check("rival_spearman", {k: round(v, 4) for k, v in vals.items()}, {k: round(rec[k], 4) for k in vals}, not bad)
    out["n_checks"] = len(out["checks"])
    out["n_mismatches"] = len(out["mismatches"])
    (WS / "audit" / "rederive.json").write_text(json.dumps(out, indent=1, default=str))
    print(f"rederive: {out['n_checks']} checks, {out['n_mismatches']} mismatches {out['mismatches']}")


if __name__ == "__main__":
    sys.exit(main())
