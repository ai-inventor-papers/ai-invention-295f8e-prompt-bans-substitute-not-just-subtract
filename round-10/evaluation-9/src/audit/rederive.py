#!/usr/bin/env python3
"""Independent re-derivation of the iteration-10 S0 numbers (standard library only; nothing imported from src/ or
vendor/). Every definition is re-implemented from its statement in the plan and the record, then compared with the
pipeline's tables/*.csv (counts exactly, floats to 1e-6) and results/*.json. Six placebos must fail as required.

Run:  python3 audit/rederive.py      (writes audit/rederive.json)
"""

from __future__ import annotations

import csv
import itertools
import json
import math
import os
import random
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TABLES = ROOT / "tables"
GIVEN: dict[str, str] = {}   # roots come from $AII_DEPS_ROOT, a sibling folder, or DEP_<id> in the untracked .env
REN, GEO, BASE = "art_8nXdw3_lDAll", "art_VVA3P0ocZNA2", "art_cDba8_DycUJd"


def dep_file(art: str, rel: str) -> Path:
    local = ROOT / "inputs" / art / rel
    if local.exists():
        return local
    env = os.environ.get("AII_DEPS_ROOT")
    envf = {}
    if (ROOT / ".env").exists():
        for ln in (ROOT / ".env").read_text().splitlines():
            if "=" in ln and not ln.startswith("#"):
                k, v = ln.split("=", 1)
                envf[k] = v
    bases = ([Path(env) / art] if env else []) + [ROOT.parent / art]
    if envf.get(f"DEP_{art}"):
        bases.append(Path(envf[f"DEP_{art}"]))
    for base in bases:
        if (base / rel).exists():
            return base / rel
    raise FileNotFoundError(f"{art}:{rel}")


def jsonl(p: Path) -> list[dict]:
    with open(p) as fh:
        return [json.loads(x) for x in fh if x.strip()]


# ----------------------------------------------------------------------------------------------- statistics
Z = 1.959963984540054


def wilson(k: int, n: int) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + Z * Z / n
    c = (p + Z * Z / (2 * n)) / den
    h = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / den
    return (max(0.0, c - h), min(1.0, c + h))


def newcombe_paired(a: int, b: int, c: int, d: int) -> tuple[float, float, float]:
    """Newcombe (1998b) method 10 for the difference of paired proportions p1 - p2 (p1 = (a+b)/n, p2 = (a+c)/n)."""
    n = a + b + c + d
    p1, p2 = (a + b) / n, (a + c) / n
    l1, u1 = wilson(a + b, n)
    l2, u2 = wilson(a + c, n)
    dd = p1 - p2
    den = (a + b) * (c + d) * (a + c) * (b + d)
    if den == 0:
        phi = 0.0
    else:
        num = a * d - b * c
        if num > 0:
            num = max(num - n / 2, 0.0)
        phi = num / math.sqrt(den)
    dl = math.sqrt(max(0.0, (p1 - l1) ** 2 - 2 * phi * (p1 - l1) * (u2 - p2) + (u2 - p2) ** 2))
    du = math.sqrt(max(0.0, (u1 - p1) ** 2 - 2 * phi * (u1 - p1) * (p2 - l2) + (p2 - l2) ** 2))
    return dd, max(-1.0, dd - dl), min(1.0, dd + du)


def newcombe_unpaired(k1: int, n1: int, k2: int, n2: int) -> tuple[float, float, float]:
    p1, p2 = k1 / n1, k2 / n2
    l1, u1 = wilson(k1, n1)
    l2, u2 = wilson(k2, n2)
    dd = p1 - p2
    return dd, dd - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2), dd + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)


def ranks(x: list[float]) -> list[float]:
    order = sorted(range(len(x)), key=lambda i: x[i])
    r = [0.0] * len(x)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and x[order[j + 1]] == x[order[i]]:
            j += 1
        for t in range(i, j + 1):
            r[order[t]] = (i + j) / 2 + 1
        i = j + 1
    return r


def resid(y: list[float], z: list[float]) -> list[float]:
    my, mz = statistics.fmean(y), statistics.fmean(z)
    szz = sum((v - mz) ** 2 for v in z)
    b = sum((zi - mz) * (yi - my) for yi, zi in zip(y, z)) / szz
    return [yi - my - b * (zi - mz) for yi, zi in zip(y, z)]


def corr(x: list[float], y: list[float]) -> float:
    mx, my = statistics.fmean(x), statistics.fmean(y)
    sx = math.sqrt(sum((v - mx) ** 2 for v in x))
    sy = math.sqrt(sum((v - my) ** 2 for v in y))
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / (sx * sy)


# ----------------------------------------------------------------------------------------------- definitions
COARSE = {"bfs": "BFS", "dfs": "DFS", "iddfs": "ID", "astar": "HEUR", "gbfs": "HEUR", "bibfs": "BIDIR",
          "biastar": "BIDIR", "idastar": "ID", "jps": "HEUR", "dijkstra_unit": "BFS"}
FINE = {"bfs": "BFS", "dfs": "DFS", "iddfs": "ID-depth", "astar": "HEUR-f", "gbfs": "HEUR-h", "bibfs": "BIDIR-BFS",
        "biastar": "BIDIR-heuristic", "idastar": "ID-f", "jps": "HEUR-jump", "dijkstra_unit": "BFS"}
K_ORDER = ["bfs", "dfs", "iddfs", "astar", "gbfs"]
FAM = {"UD": "BFS", "BF": "OTHER", "CK": "OTHER", "RP": "OTHER", "FL": "OTHER", "SP": "OTHER", "RC": "OTHER",
       "MX": "OTHER"}
UDSET = {"dijkstra_unit", "idastar", "jps"}


def rt(r: dict) -> str:
    lab = r.get("runtime_label")
    if not r.get("has_code") or lab in (None, "invalid"):
        return "UNTRACEABLE"
    return COARSE.get(lab, "OTHER")


def rtf(r: dict) -> str:
    return "UNTRACEABLE" if rt(r) == "UNTRACEABLE" else FINE.get(r.get("runtime_label"), "OTHER")


def reading_ok(rd: str, r: dict, banned: list[str], reads: dict[str, str]) -> bool | None:
    cb = {COARSE[b] for b in banned}
    if rd in ("runtime_coarse", "runtime_fine", "hand_reads", "ud_compliant"):
        if rt(r) == "UNTRACEABLE":
            return None
        if rd == "runtime_coarse":
            return rt(r) not in cb
        if rd == "runtime_fine":
            return rtf(r) not in {FINE[b] for b in banned}
        if rd == "hand_reads":
            return (reads[r["uid"]] not in cb) if r["uid"] in reads else (rt(r) not in cb)
        return True if r.get("runtime_label") in UDSET else (rt(r) not in cb)
    oc = r.get("order_class")
    if oc in (None, "UNTRACEABLE"):
        return None
    if rd == "tracer_coarse":
        return oc not in cb
    fb = {FINE[b] for b in banned}
    if "DFS" in fb:
        fb.add("DFS-revisit")
    return r.get("order_class_fine") not in fb


def table(rows: list[dict], banned: list[str], rd: str, reads: dict[str, str], completed_only: bool = True) -> dict:
    a = b = c = d = 0
    for r in rows:
        if not r.get("has_code") or (completed_only and r.get("truncated")):
            continue
        m = reading_ok(rd, r, banned, reads)
        if m is None:
            continue
        lx = bool(r.get("lexical_L1"))
        a += lx and m
        b += lx and not m
        c += (not lx) and m
        d += (not lx) and (not m)
    gap, lo, hi = newcombe_paired(a, b, c, d)
    return {"a": a, "b": b, "c": c, "d": d, "n": a + b + c + d, "mech_k": a + c, "lex_k": a + b, "gap": gap, "lo": lo,
            "hi": hi}


class Checker:
    def __init__(self) -> None:
        self.n = 0
        self.bad: list[str] = []

    def eq(self, name: str, got, want) -> None:
        self.n += 1
        if got != want:
            self.bad.append(f"{name}: got {got!r} want {want!r}")

    def close(self, name: str, got: float, want: float, tol: float = 1e-6) -> None:
        self.n += 1
        if not (abs(float(got) - float(want)) <= tol):
            self.bad.append(f"{name}: got {got} want {want}")


def read_csv(name: str, base: Path = TABLES) -> list[dict]:
    with open(base / name) as fh:
        return list(csv.DictReader(fh))


# ----------------------------------------------------------------------------------------------- sections
def audit_exhaustion(ck: Checker, csv_name: str = "exhaustion_readings_exact.csv", base: Path = TABLES) -> dict:
    reads = {r["uid"]: FAM[r["family"]] for r in jsonl(dep_file(REN, "data/manual_reads_v9.jsonl"))}
    want = {(r["model"], r["cell"], r["reading"]): r for r in read_csv(csv_name, base)}
    out = {}
    for mk, pre in (("q32", "A"), ("q14", "E")):
        for kk in ("1", "2", "3", "4", "5", "ho"):
            cid = f"{pre}_k5_ho" if kk == "ho" else f"{pre}_k{kk}"
            rows = jsonl(dep_file(REN, f"data/labelled_v9_{cid}.jsonl"))
            banned = K_ORDER[:5] if kk == "ho" else K_ORDER[:int(kk)]
            for rd in ("runtime_coarse", "runtime_fine", "tracer_coarse", "tracer_fine", "hand_reads", "ud_compliant"):
                key = (mk, kk, rd)
                if key not in want:
                    continue
                t = table(rows, banned, rd, reads)
                w = want[key]
                for f in ("a", "b", "c", "d", "n", "mech_k", "lex_k"):
                    ck.eq(f"exh {key} {f}", t[f], int(w[f]))
                ck.close(f"exh {key} gap", t["gap"], float(w["gap"]))
                ck.close(f"exh {key} lo", t["lo"], float(w["ci_lo"]))
                ck.close(f"exh {key} hi", t["hi"], float(w["ci_hi"]))
                out[f"{mk}|{kk}|{rd}"] = [t["mech_k"], t["n"]]
    return {"cells": out, "reads": reads}


def audit_described(ck: Checker) -> dict:
    reads = {r["uid"]: FAM[r["family"]] for r in jsonl(dep_file(REN, "data/manual_reads_v9.jsonl"))}
    desc = jsonl(dep_file(REN, "data/labelled_v9_C_desc.jsonl"))
    named = jsonl(dep_file(REN, "data/labelled_v9_A_k5.jsonl"))
    want = read_csv("table433b_described_vs_named.csv")

    def comp(rows: list[dict], rd: str) -> tuple[int, int]:
        k = n = 0
        for r in rows:
            if not r.get("has_code") or r.get("truncated"):
                continue
            m = reading_ok(rd, r, K_ORDER, reads)
            if m is None:
                continue
            n += 1
            k += bool(m)
        return k, n

    pairs = [("runtime_coarse", "runtime_coarse"), ("tracer_coarse", "tracer_coarse"), ("tracer_fine", "tracer_fine"),
             ("runtime_fine", "runtime_fine"), ("runtime_coarse", "hand_reads")]
    out = {}
    for (rd_d, rd_n), w in zip(pairs, want):
        kd, nd = comp(desc, rd_d)
        kn, nn = comp(named, rd_n)
        dd, lo, hi = newcombe_unpaired(kd, nd, kn, nn)
        ck.eq(f"desc {w['measure']} described", f"{kd}/{nd}", w["described_k_of_n"])
        ck.eq(f"desc {w['measure']} named", f"{kn}/{nn}", w["named_k_of_n"])
        ck.close(f"desc {w['measure']} diff", dd, float(w["diff_exact"]))
        ck.close(f"desc {w['measure']} lo", lo, float(w["ci_lo_exact"]))
        ck.close(f"desc {w['measure']} hi", hi, float(w["ci_hi_exact"]))
        out[w["measure"]] = dd
    return out


def family(label: str, other: str) -> str:
    o = (other or "").lower()
    if label == "dijkstra_unit":
        return "unit-weight Dijkstra"
    if label == "other" and ("bellman" in o or "spfa" in o):
        return "Bellman-Ford/SPFA"
    words = o.replace("-", " ").replace("/", " ").replace("(", " ").split()
    if "bfs" in words:
        return "BFS variants"
    return "other known"


def audit_placement(ck: Checker) -> dict:
    pl = json.loads(dep_file(GEO, "results/placement.json").read_text())
    want = read_csv("table438b_placement_families.csv")
    lab = {"32b|mcode_PRIMARY_R1": "Qwen3-32B, primary readout (block 33)",
           "32b|mcode_PRIMARY_R2": "Qwen3-32B, second readout (block 21; gate fails)",
           "32b|mcode_M32_R1": "Qwen3-32B programs only (block 31)", "8b|mcode_PRIMARY_R1": "Qwen3-8B, primary readout (block 17)"}
    w = {(r["frame"], r["family"]): r for r in want}
    fams = ["unit-weight Dijkstra", "Bellman-Ford/SPFA", "BFS variants", "other known"]
    out = {}
    for fk, fv in pl.items():
        far = max(fv["frame_g"].values())
        surv = [r for r in fv["rows"] if r["set"] == "SURV"]
        for fam in fams:
            rs = [r for r in surv if family(r["label"], r.get("other_name") or "") == fam]
            row = w[(lab[fk], fam)]
            ck.eq(f"pl {fk} {fam} n", len(rs), int(row["n"]))
            ck.eq(f"pl {fk} {fam} edge", sum(r["class"] == "EDGE" for r in rs), int(row["edge"]))
            ck.eq(f"pl {fk} {fam} opposite", sum(r["class"] == "OPPOSITE" for r in rs), int(row["opposite"]))
            ck.eq(f"pl {fk} {fam} beyond", sum(r["g_x"] > far for r in rs), int(row["beyond_farther_reference"]))
            ck.close(f"pl {fk} {fam} median", statistics.median([r["g_x"] for r in rs]), float(row["median_g"]), 5e-4)
            out[f"{fk}|{fam}"] = [sum(r["class"] == "OPPOSITE" for r in rs), len(rs)]
    return {"counts": out, "pl": pl}


def audit_random_sets(ck: Checker) -> dict:
    rs = json.loads(dep_file(BASE, "results/random_sets.json").read_text())
    b2 = json.loads(dep_file(BASE, "results/b2_summary.json").read_text())
    want = {(r["unit"], r["family"]): r for r in read_csv("table441b_random_sets.csv")}
    un = {"B3": "minimum spanning tree", "T10": "connected components"}
    out = {}
    for u in ("B3", "T10"):
        obs = b2["units"][u]["arms"]["FSTACK"]["share"]
        for fam, sk in (("R", "R"), ("Rpure", "Rpure"), ("Rscaled", "R")):
            sets = rs[u][sk]["sets"]
            shares = b2["units"][u][f"null_{fam}"]["shares"]
            rep = sum(1 for s in sets if len([x for x in s if x.startswith("mlp")]) != len({x for x in s if x.startswith("mlp")}))
            full = [i for i, s in enumerate(sets) if len(set(s)) == len(s)]
            ge = sum(1 for i in full if shares[i] >= obs)
            p = (1 + ge) / (len(full) + 1)
            w = want[(un[u], fam)]
            ck.eq(f"rs {u} {fam} repeated", rep, int(w["sets_with_repeated_mlp"]))
            ck.eq(f"rs {u} {fam} ten_distinct", len(full), int(w["ten_distinct_sets"]))
            ck.close(f"rs {u} {fam} restricted_p", p, float(w["restricted_p"]), 5e-4)
            ck.close(f"rs {u} {fam} p_all", (1 + sum(1 for x in shares if x >= obs)) / (len(shares) + 1),
                     float(w["p_all"]), 5e-4)
            out[f"{u}|{fam}"] = [rep, len(full), p]
    return out


def audit_heldout(ck: Checker) -> dict:
    rows = jsonl(dep_file(BASE, "results/b3_heldout_rows.jsonl"))
    want = read_csv("heldout_per_side.csv")
    s0f = json.loads((ROOT / "results" / "s0f.json").read_text())["metrics"]
    out = {}
    for mode, key in (("ablate", "aligned|ablate|mlp|L0|H-1|COND"), ("steer", "aligned|steer|mlp|L0|H-1|COND")):
        d = []
        for r in rows:
            rv = [r["res"][f"{key}|r{j}"] for j in range(50) if f"{key}|r{j}" in r["res"]]
            d.append(r["res"][f"{key}|node"] - statistics.fmean(rv))
        wv = [float(x["d_node_minus_random_mean"]) for x in want if x["mode"] == mode]
        for i, (a, b) in enumerate(zip(d, wv)):
            ck.close(f"ho {mode} row {i}", a, b, 1e-5)
        forced = [x for x, r in zip(d, rows) if r["side"] == "corrupt"]
        padded = [x for x, r in zip(d, rows) if r["side"] == "clean"]
        ck.close(f"ho {mode} forced", statistics.fmean(forced), s0f[f"{mode}_forced"])
        ck.close(f"ho {mode} padded", statistics.fmean(padded), s0f[f"{mode}_padded"])
        ck.close(f"ho {mode} all", statistics.fmean(d), s0f[f"{mode}_all"])
        obs = abs(statistics.fmean(d))
        cnt = sum(1 for s in itertools.product((1, -1), repeat=len(d))
                  if abs(statistics.fmean([x * y for x, y in zip(d, s)])) >= obs - 1e-12)
        p10 = cnt / 2 ** len(d)
        ck.close(f"ho {mode} p10", p10, s0f[f"{mode}_p10_reproduced"], 1e-12)
        contr = {}
        for r, x in zip(rows, d):
            contr.setdefault(r["vid"].split("|")[0], []).append(x)
        cm = [statistics.fmean(v) for v in contr.values()]
        o5 = abs(statistics.fmean(cm))
        p5 = sum(1 for s in itertools.product((1, -1), repeat=5)
                 if abs(statistics.fmean([x * y for x, y in zip(cm, s)])) >= o5 - 1e-12) / 32
        if mode == "ablate":
            ck.close("ho p5 two-sided", p5, s0f["p5_two_sided"], 1e-12)
        out[mode] = {"forced": statistics.fmean(forced), "padded": statistics.fmean(padded), "p10": p10, "p5": p5,
                     "contrasts": cm}
    return out


def _rdm_vec(M: list[list[float]], idx: list[int]) -> list[float]:
    return [M[idx[i]][idx[j]] for i in range(len(idx)) for j in range(i + 1, len(idx))]


def _partials_null(y: list[float], x: list[float], z: list[float], n: int, perms) -> tuple[int, int, int]:
    """Counts of relabelings with statistic >= observed under scheme A (relabel x) and B (relabel residual of y|z)."""
    obs = corr(resid(y, z), resid(x, z))
    pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
    pos = {p: k for k, p in enumerate(pairs)}
    X = [[0.0] * n for _ in range(n)]
    E = [[0.0] * n for _ in range(n)]
    ey = resid(y, z)
    ex = resid(x, z)
    for (i, j), xv, ev in zip(pairs, x, ey):
        X[i][j] = X[j][i] = xv
        E[i][j] = E[j][i] = ev
    zc = [v - statistics.fmean(z) for v in z]
    zz = sum(v * v for v in zc)
    sx2 = sum(v * v for v in x)
    mx = statistics.fmean(x)
    m = len(x)
    se2 = sum(v * v for v in ey)
    eyn = math.sqrt(sum(v * v for v in ey))
    exn = math.sqrt(sum(v * v for v in ex))
    geA = geB = tot = 0
    for pm in perms:
        xp = [X[pm[i]][pm[j]] for i, j in pairs]
        ep = [E[pm[i]][pm[j]] for i, j in pairs]
        xz = sum(a * b for a, b in zip(xp, zc))
        sA = sum(a * b for a, b in zip(xp, ey)) / (eyn * math.sqrt(max(sx2 - m * mx * mx - xz * xz / zz, 1e-300)))
        ez = sum(a * b for a, b in zip(ep, zc))
        sB = sum(a * b for a, b in zip(ep, ex)) / (exn * math.sqrt(max(se2 - ez * ez / zz, 1e-300)))
        geA += sA >= obs - 1e-12
        geB += sB >= obs - 1e-12
        tot += 1
    return geA, geB, tot


def audit_rsa(ck: Checker, mc_draws: int = 200_000) -> dict:
    canon = ["bfs", "dfs", "bibfs", "iddfs", "astar", "gbfs", "dijkstra_unit", "idastar", "jps", "biastar"]
    lex = json.loads(dep_file(GEO, "results/lexical.json").read_text())["R_lex"]
    ds = json.loads(dep_file(GEO, "results/behavioural_distance.json").read_text())["d_DS"]
    want = {r["manifold"]: r for r in read_csv("table437b_partial_rsa.csv")}
    lab = {"32b|mname": "Named, Qwen3-32B", "32b|mdesc": "Described, Qwen3-32B", "32b|mlex": "Name-only, Qwen3-32B",
           "32b|mcode_PRIMARY_R1": "Program, primary readout, Qwen3-32B",
           "32b|mcode_PRIMARY_R2": "Program, second readout, Qwen3-32B", "32b|mcode_M32_R1": "Program, Qwen3-32B programs only",
           "8b|mname": "Named, Qwen3-8B", "8b|mdesc": "Described, Qwen3-8B", "8b|mcode_PRIMARY_R1": "Program, primary readout, Qwen3-8B"}
    rng = random.Random(20261024)
    out = {}
    for key, name in lab.items():
        mt, mn = key.split("|")
        g = json.loads(dep_file(GEO, f"results/geometry_{mt}_{mn}.json").read_text())["L_star"]["describe"]
        M = g["k15"]["class_geodesic_matrix"]
        M = [[(M[i][j] + M[j][i]) / 2 for j in range(10)] for i in range(10)]
        idx = [i for i, a in enumerate(canon) if a in g["present"]]
        n = len(idx)
        y = ranks(_rdm_vec(M, idx))
        xl = ranks(_rdm_vec(lex, idx))
        xd = ranks(_rdm_vec(ds, idx))
        r_ld = corr(xl, xd)
        w = want[name]
        ck.close(f"rsa {key} lex-DS r", r_ld, float(w["lex_ds_spearman"]), 1e-6)
        pl = corr(resid(y, xd), resid(xl, xd))
        pd = corr(resid(y, xl), resid(xd, xl))
        ck.close(f"rsa {key} lex|DS", pl, float(w["lex_given_ds"]), 1e-6)
        ck.close(f"rsa {key} DS|lex", pd, float(w["ds_given_lex"]), 1e-6)
        if n <= 9:
            perms = itertools.permutations(range(n))
            exact = True
        else:
            base = list(range(n))
            perms = (rng.sample(base, n) for _ in range(mc_draws))
            exact = False
        perms = list(perms)
        aA, aB, tot = _partials_null(y, xl, xd, n, perms)
        bA, bB, _ = _partials_null(y, xd, xl, n, perms)
        res = {"pA_lex": aA / tot, "pB_lex": aB / tot, "pA_ds": bA / tot, "pB_ds": bB / tot, "exact": exact, "n_perm": tot}
        for kname, got, col in (("pA_lex", res["pA_lex"], "lex_given_ds_p_A"), ("pB_lex", res["pB_lex"], "lex_given_ds_p_B"),
                                ("pA_ds", res["pA_ds"], "ds_given_lex_p_A"), ("pB_ds", res["pB_ds"], "ds_given_lex_p_B")):
            wantp = float(w[col])
            if exact:
                ck.close(f"rsa {key} {kname} exact", got, wantp, 1e-6)
            else:   # Monte-Carlo: within 4 standard errors of the exact value
                se = math.sqrt(max(wantp * (1 - wantp), 1e-12) / tot)
                ck.close(f"rsa {key} {kname} mc", got, wantp, 4 * se + 1e-6)
        out[key] = {"r": r_ld, "lex_given_ds": pl, "ds_given_lex": pd, **res}
    return out


# ----------------------------------------------------------------------------------------------- placebos
def placebos(exh: dict, pl: dict, rsa_obs: dict, ho: dict) -> dict:
    rng = random.Random(7)
    out = {}
    # P1: shuffle the 76 family labels; the substituted Qwen3-32B k = 5 rate must differ from 27/46 in >= 90%
    reads_rows = jsonl(dep_file(REN, "data/manual_reads_v9.jsonl"))
    fams = [r["family"] for r in reads_rows]
    rows = jsonl(dep_file(REN, "data/labelled_v9_A_k5.jsonl"))
    obs = exh["cells"]["q32|5|hand_reads"]
    diff = 0
    for _ in range(200):
        sh = fams[:]
        rng.shuffle(sh)
        reads = {r["uid"]: FAM[f] for r, f in zip(reads_rows, sh)}
        t = table(rows, K_ORDER, "hand_reads", reads)
        diff += [t["mech_k"], t["n"]] != obs
    out["P1_family_shuffle"] = {"share_differs": diff / 200, "required": 0.9, "fails_as_required": diff / 200 >= 0.9,
                                "draws": 200, "seed": 7}
    # P2: shuffle placement families; Bellman-Ford 15/15 opposite (primary frame) must break in >= 90%
    fv = pl["32b|mcode_PRIMARY_R1"]
    surv = [r for r in fv["rows"] if r["set"] == "SURV"]
    labs = [family(r["label"], r.get("other_name") or "") for r in surv]
    broke = 0
    for _ in range(200):
        sh = labs[:]
        rng.shuffle(sh)
        bf = [r for r, f in zip(surv, sh) if f == "Bellman-Ford/SPFA"]
        broke += not all(r["class"] == "OPPOSITE" for r in bf)
    out["P2_placement_shuffle"] = {"share_broken": broke / 200, "required": 0.9, "fails_as_required": broke / 200 >= 0.9}
    # P3: random lexical/mechanistic swaps within programs give a pooled gap near 0
    ret = jsonl(dep_file(REN, "results/retrace.jsonl"))
    cfgs = sorted({r["config"] for r in ret})
    pooled = []
    for _ in range(200):
        gaps = []
        for c in cfgs:
            lexs = mechs = n = 0
            for r in ret:
                if r["config"] != c or not r.get("has_code") or rt(r) == "UNTRACEABLE":
                    continue
                lx = bool(r.get("lexical_L1"))
                m = rt(r) not in {COARSE[b] for b in K_ORDER}
                if rng.random() < 0.5:
                    lx, m = m, lx
                lexs += lx
                mechs += m
                n += 1
            gaps.append((lexs - mechs) / n)
        pooled.append(statistics.fmean(gaps))
    out["P3_swap_placebo"] = {"mean_pooled_gap": statistics.fmean(pooled), "sd": statistics.pstdev(pooled),
                              "fails_as_required": abs(statistics.fmean(pooled)) < 0.05}
    # P4: neural-RDM relabeling centres the partials near 0; observed outside the central 90%
    canon = ["bfs", "dfs", "bibfs", "iddfs", "astar", "gbfs", "dijkstra_unit", "idastar", "jps", "biastar"]
    lex = json.loads(dep_file(GEO, "results/lexical.json").read_text())["R_lex"]
    ds = json.loads(dep_file(GEO, "results/behavioural_distance.json").read_text())["d_DS"]
    g = json.loads(dep_file(GEO, "results/geometry_32b_mname.json").read_text())["L_star"]["describe"]
    M = g["k15"]["class_geodesic_matrix"]
    M = [[(M[i][j] + M[j][i]) / 2 for j in range(10)] for i in range(10)]
    idx = list(range(10))
    xl = ranks(_rdm_vec(lex, idx))
    xd = ranks(_rdm_vec(ds, idx))
    nl, nd = [], []
    for _ in range(2000):
        pm = rng.sample(idx, 10)
        Mp = [[M[pm[i]][pm[j]] for j in range(10)] for i in range(10)]
        y = ranks(_rdm_vec(Mp, idx))
        nl.append(corr(resid(y, xd), resid(xl, xd)))
        nd.append(corr(resid(y, xl), resid(xd, xl)))
    q = lambda v, a: sorted(v)[int(a * (len(v) - 1))]
    ol, od = rsa_obs["32b|mname"]["lex_given_ds"], rsa_obs["32b|mname"]["ds_given_lex"]
    out["P4_relabel_neural"] = {"null_mean_lex": statistics.fmean(nl), "null_mean_ds": statistics.fmean(nd),
                                "q05_q95_lex": [q(nl, 0.05), q(nl, 0.95)], "q05_q95_ds": [q(nd, 0.05), q(nd, 0.95)],
                                "observed": [ol, od],
                                "fails_as_required": abs(statistics.fmean(nl)) < 0.1 and abs(statistics.fmean(nd)) < 0.1
                                and ol > q(nl, 0.95) and od > q(nd, 0.95)}
    # P5: random sign flips on the five contrasts give a symmetric null
    cm = ho["ablate"]["contrasts"]
    null = [statistics.fmean([x * s for x, s in zip(cm, sg)]) for sg in itertools.product((1, -1), repeat=5)]
    obs5 = statistics.fmean(cm)
    out["P5_sign_flip_null"] = {"null_mean": statistics.fmean(null), "share_ge_obs": sum(v >= obs5 - 1e-12 for v in null) / 32,
                                "share_le_minus_obs": sum(v <= -obs5 + 1e-12 for v in null) / 32,
                                "fails_as_required": abs(statistics.fmean(null)) < 1e-9 and
                                sum(v >= obs5 - 1e-12 for v in null) == sum(v <= -obs5 + 1e-12 for v in null)}
    # P6: a planted wrong value in a copied CSV must produce a mismatch
    src = TABLES / "exhaustion_readings_exact.csv"
    rows_ = read_csv("exhaustion_readings_exact.csv")
    rows_[0]["mech_k"] = str(int(rows_[0]["mech_k"]) + 1)
    planted = ROOT / "audit" / "planted"
    planted.mkdir(exist_ok=True)
    with open(planted / "exhaustion_readings_exact.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows_[0].keys()))
        w.writeheader()
        w.writerows(rows_)
    ck2 = Checker()
    audit_exhaustion(ck2, "exhaustion_readings_exact.csv", planted)
    out["P6_planted_value"] = {"mismatches_on_planted_copy": len(ck2.bad), "fails_as_required": len(ck2.bad) >= 1,
                               "example": ck2.bad[:2], "source_table": str(src.relative_to(ROOT))}
    return out


def main() -> int:
    ck = Checker()
    exh = audit_exhaustion(ck)
    desc = audit_described(ck)
    plc = audit_placement(ck)
    rs = audit_random_sets(ck)
    ho = audit_heldout(ck)
    mc = int(os.environ.get("AUDIT_MC_DRAWS", "200000"))
    rsa = audit_rsa(ck, mc)
    pb = placebos(exh, plc["pl"], rsa, ho)
    n_fail = sum(1 for v in pb.values() if v["fails_as_required"])
    out = {"n_checks": ck.n, "n_mismatches": len(ck.bad), "mismatches": ck.bad[:50], "placebos": pb,
           "placebos_failing_as_required": n_fail, "n_placebos": len(pb),
           "rsa": {k: {kk: vv for kk, vv in v.items()} for k, v in rsa.items()}, "described": desc,
           "random_sets": rs, "heldout": {k: {kk: vv for kk, vv in v.items() if kk != "contrasts"} for k, v in ho.items()},
           "stdlib_only": True, "mc_draws_10_classes": mc}
    (ROOT / "audit" / "rederive.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({"n_checks": ck.n, "n_mismatches": len(ck.bad), "placebos_failing_as_required": f"{n_fail} of {len(pb)}"}))
    for b in ck.bad[:20]:
        print("MISMATCH", b)
    return 0


if __name__ == "__main__":
    sys.exit(main())
