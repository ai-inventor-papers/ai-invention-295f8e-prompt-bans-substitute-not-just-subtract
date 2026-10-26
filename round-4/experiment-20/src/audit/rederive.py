#!/usr/bin/env python3
"""Independent re-derivation of the headline numbers from the raw rows (a separate code path: it reads
data/samples_raw.jsonl, data/labels.jsonl and data/labels_k7.jsonl directly and re-implements the cell, Hill, hull,
decision and C3d computations), plus three placebos that must fail:
  (a) site labels shuffled within (task, alpha) -> S0's best-site rate should fall to about 1/6;
  (b) template labels shuffled within (task, arm) -> the template spread of the off-default share should shrink;
  (c) survivor-permutation null with randomised d values -> p_edge is 0.5 or 1 about half the time each.
Writes results/rederive.json."""

from __future__ import annotations

import itertools
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = {"T1": "bfs", "T2": "dijkstra", "T03": "full_sort", "T05": "hash_map", "T06": "hash_set",
           "T10": "union_find"}
TASKS = ["T03", "T05", "T06", "T10", "T1", "T2"]
SITES = ["S0", "S1", "S2", "S3", "S4", "S5"]
BAD = {"invalid", "unresolved", "disputed"}


def jl(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []


def load() -> list[dict]:
    lab = {r["key"]: r for r in jl(ROOT / "data" / "labels.jsonl")}
    k7 = {r["key"]: r for r in jl(ROOT / "data" / "labels_k7.jsonl")}
    rows = []
    for r in jl(ROOT / "data" / "samples_raw.jsonl"):
        if r["arm"].startswith("SMOKE_") or r["arm"] == "TWIN_X":
            continue
        key = f"{r['task']}|{r['template']}|{r['arm']}|{r['k']}"
        if key not in lab:
            continue
        L = dict(lab[key])
        code = L.get("code") or ""
        try:
            has_solve = any(getattr(n, "name", None) == "solve" for n in __import__("ast").walk(
                __import__("ast").parse(code))) if "def solve" in code else False
        except SyntaxError:
            has_solve = False
        if L["label"] not in BAD and not has_solve:
            L["label"] = "invalid"
        ok = L["label"] not in BAD
        rows.append({"task": r["task"], "w": r["template"], "k": int(r["k"]), "arm": r["arm"],
                     "site": "TWIN" if r["arm"] == "TWIN" else r["arm"].rsplit("_a", 1)[0],
                     "alpha": 0.0 if r["arm"] == "TWIN" else float(r["arm"].rsplit("_a", 1)[1]),
                     "label": L["label"], "passed": bool(L["passed"]), "correct": bool(L["passed"]) and ok,
                     "k7": (k7.get(key) or {}).get("label_k7"), "k7_passed": (k7.get(key) or {}).get("passed")})
    return rows


def sel(rows, t, site, a):
    ks = range(10) if site == "TWIN" or a == 8.0 else range(6)
    if site == "TWIN":
        return [r for r in rows if r["task"] == t and r["arm"] == "TWIN" and r["k"] in ks]
    return [r for r in rows if r["task"] == t and r["site"] == site and r["alpha"] == a and r["k"] in ks]


def hill_exp(labels: list[str], depth: int, rng: np.random.Generator, n: int = 4000) -> float | None:
    if not labels:
        return None
    m = min(depth, len(labels))
    arr = np.array(labels)
    vals = []
    for _ in range(n):
        s = rng.choice(arr, size=m, replace=False)
        _, c = np.unique(s, return_counts=True)
        p = c / c.sum()
        vals.append(math.exp(-(p * np.log(p)).sum()))
    return float(np.mean(vals))


def hull_h5(settings: list[tuple[float, list[str]]], rng: np.random.Generator, draws: int = 600,
            step: float = 0.05) -> float:
    """Independent H5: enumerate the simplex (<= 3 non-zero), Monte-Carlo the two-stage draw with fresh randomness."""
    k = len(settings)
    m = int(round(1 / step))
    best = -1.0
    U = rng.random((draws, 25))
    perms = []
    for p, labs in settings:
        seqs = []
        for _ in range(draws):
            if len(labs) >= 25:
                seqs.append(list(rng.permutation(labs)[:25]))
            elif labs:
                seqs.append(list(rng.permutation(labs)) + list(rng.choice(labs, size=25 - len(labs))))
            else:
                seqs.append([])
        perms.append(seqs)
    for comb in itertools.product(range(m + 1), repeat=k - 1):
        s = sum(comb)
        if s > m:
            continue
        w = np.array(list(comb) + [m - s]) / m
        if (w > 0).sum() > 3:
            continue
        pas = np.array([p for p, _ in settings])
        if settings[0][0] - (w * pas).sum() > 0.05 + 1e-12:
            continue
        a = w * pas
        if a.sum() <= 0:
            continue
        cdf = np.cumsum(a / a.sum())
        cdf[-1] = 1
        hs = []
        for d in range(draws):
            j = np.searchsorted(cdf, U[d], side="right").clip(max=k - 1)
            comp = Counter()
            for jj in range(k):
                nj = int((j == jj).sum())
                if nj:
                    comp.update(perms[jj][d][:nj])
            c = np.array(list(comp.values()), float)
            pp = c / c.sum()
            hs.append(math.exp(-(pp * np.log(pp)).sum()))
        best = max(best, float(np.mean(hs)))
    return best


def site_h5(rows, t, s, rng, draws=600, step=0.05):
    st = []
    for a in (0.0, 1.0, 2.0, 4.0):
        rs = sel(rows, t, "TWIN" if a == 0 else s, a)
        if not rs:
            return None
        st.append((sum(r["passed"] for r in rs) / len(rs), [r["label"] for r in rs if r["correct"]]))
    return hull_h5(st, rng, draws, step)


def best(h5: dict[str, float]) -> str | None:
    v = {s: round(x, 2) for s, x in h5.items() if x is not None}
    top = max(v.values())
    c = [s for s, x in v.items() if x == top]
    return c[0] if len(c) == 1 else None


def main() -> None:
    rows = load()
    out: dict = {"n_rows": len(rows)}
    cells = json.loads((ROOT / "results" / "cells.json").read_text())
    mism = []
    for key, c in cells.items():
        t, s, a = key.split("|")
        if s in ("TWIN_X", "S0_N50", "ENG"):
            continue
        rs = sel(rows, t, s, float(a)) if s != "TOP5" else [r for r in rows if r["task"] == t and r["site"] == "TOP5"
                                                           and r["alpha"] == float(a) and r["k"] < 10]
        n, npass = len(rs), sum(r["passed"] for r in rs)
        comp = dict(Counter(r["label"] for r in rs if r["correct"]))
        if n != c["n"] or abs(npass / max(n, 1) - (c["pass_rate"] or 0)) > 1e-9 or comp != c["correct_composition"]:
            mism.append(key)
    out["cells_checked"] = len(cells)
    out["cell_mismatches"] = mism
    rng = np.random.default_rng(12345)
    hull = json.loads((ROOT / "results" / "hull.json").read_text())["point"]
    h5_re, h5_diff = {}, {}
    for t in TASKS:
        h5_re[t] = {}
        for s in SITES:
            v = site_h5(rows, t, s, rng)
            h5_re[t][s] = v
            ref = hull.get(f"{t}|{s}", {}).get("H5")
            if v is not None and ref is not None:
                h5_diff[f"{t}|{s}"] = v - ref
    out["H5_rederived"] = h5_re
    out["H5_max_abs_diff"] = max((abs(x) for x in h5_diff.values()), default=None)
    out["H5_mismatches_gt_0.05"] = [k for k, v in h5_diff.items() if abs(v) > 0.05]
    c1 = json.loads((ROOT / "results" / "c1_site.json").read_text())
    re_best = {t: best(h5_re[t]) for t in TASKS if all(h5_re[t].get(s) is not None for s in SITES)}
    cnt = sum(1 for b in re_best.values() if b == "S0")
    out["C1_rederived"] = {"best_site": re_best, "count_S0_best": cnt,
                           "raw_p": sum(math.comb(6, k) * (1 / 6) ** k * (5 / 6) ** (6 - k) for k in range(cnt, 7)),
                           "matches_analysis_count": cnt == c1.get("count_S0_best"),
                           "best_site_disagreements": {t: [re_best[t], c1["best_site"].get(t)] for t in re_best
                                                       if re_best[t] != c1["best_site"].get(t)}}
    # C3d
    geo = json.loads((ROOT / "results" / "plan_geometry_T1.json").read_text())
    d7 = {y: geo["k10"]["d_survivor_to_TOP5"][y] for y in ("bibfs", "idastar")}
    c3 = {}
    for a in (1.0, 2.0, 4.0):
        rs = [r for r in rows if r["task"] == "T1" and r["site"] == "TOP5" and r["alpha"] == a]
        cor = [r for r in rs if r["k7"] not in (None, "invalid") and r["k7_passed"]]
        off = [r for r in cor if r["k7"] not in ("bfs", "dfs", "gbfs", "iddfs", "astar")]
        sv = Counter(r["k7"] for r in off if r["k7"] in d7)
        tot = sum(sv.values())
        c3[f"TOP5_a{a:g}"] = {"avoidance": len(off) / len(cor) if cor else None,
                              "D_obs": sum(sv[y] / tot * d7[y] for y in d7) if tot else None}
    ref3 = json.loads((ROOT / "results" / "c3d.json").read_text())["by_arm"]
    out["C3d_rederived"] = c3
    out["C3d_mismatches"] = [k for k, v in c3.items() if k in ref3 and (
        (v["avoidance"] is not None and abs(v["avoidance"] - (ref3[k]["k7"]["avoidance"] or 0)) > 1e-9) or
        (v["D_obs"] is not None and abs(v["D_obs"] - ref3[k]["k7"].get("D_obs", float("nan"))) > 1e-9))]
    # novelty counts
    nap = ROOT / "results" / "novelty_audit.json"
    if nap.exists():
        na = json.loads(nap.read_text())
        pool = {(r["task"], r["label"]) for r in rows if r["label"] == "other" and r["correct"]}
        out["novelty_rederived"] = {"n_correct_other_rows": sum(1 for r in rows if r["label"] == "other" and
                                                                r["correct"]),
                                    "matches_pool_rows": sum(1 for r in rows if r["label"] == "other" and
                                                             r["correct"]) == na["n_pool_rows"],
                                    "n_confirmed_novel": na["n_novel_confirmed"], "n_task_kinds": len(pool)}
    # placebo (a): site labels shuffled within (task, alpha)
    prng = random.Random(7)
    wins = []
    for rep in range(12):
        sh = [dict(r) for r in rows]
        for t in TASKS:
            for a in (1.0, 2.0, 4.0):
                grp = [r for r in sh if r["task"] == t and r["alpha"] == a and r["site"] in SITES and r["k"] < 6]
                labs = [r["site"] for r in grp]
                prng.shuffle(labs)
                for r, s in zip(grp, labs):
                    r["site"] = s
        rr = np.random.default_rng(rep)
        n_s0 = 0
        n_t = 0
        for t in TASKS:
            h = {s: site_h5(sh, t, s, rr, draws=150, step=0.1) for s in SITES}
            if all(v is not None for v in h.values()):
                n_t += 1
                n_s0 += best(h) == "S0"
        wins.append(n_s0 / max(n_t, 1))
    out["placebo_site_shuffle"] = {"S0_best_rate_mean": float(np.mean(wins)), "replicates": len(wins),
                                   "expected_under_null": 1 / 6,
                                   "observed_S0_best_rate": c1.get("count_S0_best", 0) / max(c1.get("n_tasks", 6), 1)}
    # placebo (b): template labels shuffled within (task, arm)

    def template_spread(rs):
        by = defaultdict(list)
        for r in rs:
            if r["label"] not in BAD:
                by[(r["task"], r["arm"], r["w"])].append(r["label"] != DEFAULT[r["task"]])
        sp = defaultdict(list)
        for (t, a, w), v in by.items():
            sp[(t, a)].append(np.mean(v))
        return float(np.mean([np.std(v) for v in sp.values() if len(v) == 5]))
    obs = template_spread(rows)
    shs = []
    for rep in range(30):
        sh = [dict(r) for r in rows]
        byg = defaultdict(list)
        for r in sh:
            byg[(r["task"], r["arm"])].append(r)
        for g in byg.values():
            ws = [r["w"] for r in g]
            prng.shuffle(ws)
            for r, w in zip(g, ws):
                r["w"] = w
        shs.append(template_spread(sh))
    out["placebo_template_shuffle"] = {"observed_spread": obs, "shuffled_mean": float(np.mean(shs)),
                                       "shuffled_q95": float(np.quantile(shs, 0.95)),
                                       "template_effect_beyond_shuffle": bool(obs > np.quantile(shs, 0.95))}
    # placebo (c): randomised d values in the two-survivor permutation null
    ps = []
    q = {"bibfs": 0.5, "idastar": 0.5}
    for _ in range(1000):
        dv = {"bibfs": prng.random(), "idastar": prng.random()}
        qq = {"bibfs": prng.random()}
        qq["idastar"] = 1 - qq["bibfs"]
        dobs = sum(qq[y] * dv[y] for y in dv)
        perms = [sum(qq[y] * dict(zip(dv, p))[y] for y in dv) for p in itertools.permutations(dv.values())]
        ps.append(np.mean([v <= dobs + 1e-12 for v in perms]))
    out["placebo_random_d"] = {"share_p_edge_0.5": float(np.mean(np.array(ps) == 0.5)),
                               "share_p_edge_1": float(np.mean(np.array(ps) == 1.0)), "unused_q": q}
    out["n_mismatches_total"] = len(mism) + len(out["H5_mismatches_gt_0.05"]) + len(out["C3d_mismatches"]) + \
        (0 if out["C1_rederived"]["matches_analysis_count"] else 1)
    (ROOT / "results" / "rederive.json").write_text(json.dumps(out, indent=1, default=float))
    print({k: v for k, v in out.items() if k not in ("H5_rederived",)})


if __name__ == "__main__":
    main()
