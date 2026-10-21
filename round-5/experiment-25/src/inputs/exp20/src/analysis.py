#!/usr/bin/env python3
"""STEP 11 - analysis (rules frozen in predictions/predictions.json, commit #1; hull and decision code in hull.py).

11.1 cells; 11.2 randomisation hull per (task, site) + template-stratified bootstrap with selection inside replicates;
11.3 C1-site decision; 11.4 failure modes; 11.5 Hill gain per pass point; 11.6 paired flips (exact McNemar) and
byte-identical rates; 11.7 transmission GLM; 11.8 pooled mixed logistic + site x template table; 11.9 C3c boundary;
11.10 overlap check; 11.11 C3d scoring (plan-site geometry, avoidance, landing, survivor permutation null).
Outputs: results/*.json.
"""

from __future__ import annotations

import ast
import glob
import math
import multiprocessing as mp
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from typing import Any

import numpy as np
from loguru import logger

from cfg import (DATA_DIR, DEFAULT, DIR_DIR, N50_K, N_GRID_K, RESULTS_DIR, ROOT, SITES, TASKS, TEMPLATE_IDS,
                 read_json, read_jsonl, setup_logging, utc_now, wilson_ci, write_json)
from hull import DEPTH, binom_tail, c1_decision, hull_prices, rarefied_hill

INVALID = ("invalid",)
UNRES = ("unresolved", "disputed")
GRID_ALPHAS = (1.0, 2.0, 4.0)
TOP5 = ("bfs", "dfs", "gbfs", "iddfs", "astar")
SURV7 = ("bibfs", "idastar")
SURV_EXT = ("bibfs", "dijkstra_unit", "idastar", "jps", "biastar")


# ------------------------------------------------------------------------------------------------ data
def load_rows() -> list[dict[str, Any]]:
    labs = {r["key"]: r for r in read_jsonl(DATA_DIR / "labels.jsonl")}
    logs = {r["key"]: r for r in read_jsonl(DATA_DIR / "row_logs.jsonl")}
    k7 = {r["key"]: r for r in read_jsonl(DATA_DIR / "labels_k7.jsonl")}
    out = []
    for r in read_jsonl(DATA_DIR / "samples_raw.jsonl"):
        if r["arm"].startswith("SMOKE_"):
            continue
        key = f"{r['task']}|{r['template']}|{r['arm']}|{r['k']}"
        lb = labs.get(key)
        if lb is None:
            continue
        lg = logs.get(key, {})
        lab = lb["label"]
        if lab not in INVALID + UNRES and not _defines_solve(lb.get("code")):
            lab = "invalid"  # D13: the bench rule (no def solve / syntax error -> invalid) applied to every task
        d = DEFAULT[r["task"]]
        att = lab not in INVALID + UNRES
        rec = {"key": key, "task": r["task"], "w": r["template"], "k": int(r["k"]), "arm": r["arm"],
               "site": r["site"], "alpha": float(r["alpha"]), "label": lab, "passed": bool(lb.get("passed")),
               "attempt": att, "invalid": lab in INVALID, "unresolved": lab in UNRES,
               "correct": bool(lb.get("passed")) and att, "off": att and lab != d,
               "code_sha256": lb.get("code_sha256"), "code": lb.get("code"), "fallback_label": lb.get("fallback_label"),
               "disp35": (lg.get("realised_disp_R") or {}).get("35"), "ftkl": lg.get("first_token_kl"),
               "s3kl": ((lg.get("s3") or {}).get("kl_mean_steps1_32")), "finish": r["finish_reason"],
               "n_tokens": r["n_new_tokens"]}
        if key in k7:
            rec["label_k7"] = k7[key]["label_k7"]
            rec["label_ext"] = k7[key]["label_ext"]
            rec["passed_k7"] = k7[key]["passed"]
        out.append(rec)
    return out


def _defines_solve(code: str | None) -> bool:
    if not code or "def solve" not in code:
        return False
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError):
        return False
    return any(isinstance(n, ast.FunctionDef) and n.name == "solve" for n in ast.walk(tree))


def cell(rows: list[dict[str, Any]], task: str, site: str, alpha: float, ks: list[int] | None) -> list[dict]:
    if site == "TWIN":
        return [r for r in rows if r["task"] == task and r["arm"] == "TWIN" and (ks is None or r["k"] in ks)]
    return [r for r in rows if r["task"] == task and r["site"] == site and r["alpha"] == alpha and
            r["arm"] != "TWIN_X" and (ks is None or r["k"] in ks)]


def grid_ks(site: str, alpha: float) -> list[int]:
    return N50_K if (site == "TWIN" or alpha == 8.0 or site == "TOP5") else N_GRID_K


# ------------------------------------------------------------------------------------------------ 11.1 cells
def _ast_tokens(code: str) -> list[str]:
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError):
        return []
    toks: list[str] = []

    def visit(n: ast.AST) -> None:
        name = type(n).__name__
        if isinstance(n, (ast.Name, ast.arg)):
            toks.append("ID")
        elif isinstance(n, ast.Constant):
            toks.append("C:" + type(n.value).__name__)
        elif isinstance(n, ast.Attribute):
            toks.append("ATTR:" + n.attr)
        elif isinstance(n, ast.FunctionDef):
            toks.append("FUNC")
        else:
            toks.append(name)
        for c in ast.iter_child_nodes(n):
            visit(c)
    visit(tree)
    return toks


def shingles(code: str, n: int = 4) -> frozenset:
    t = _ast_tokens(code or "")
    return frozenset(tuple(t[i:i + n]) for i in range(max(0, len(t) - n + 1)))


def clusters_per_idea(rows: list[dict[str, Any]], theta: float) -> dict[str, Any]:
    by: dict[str, list[frozenset]] = defaultdict(list)
    for r in rows:
        if r["correct"] and r.get("code"):
            by[r["label"]].append(shingles(r["code"]))
    per = {}
    for lab, sh in by.items():
        n = len(sh)
        parent = list(range(n))

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x
        for i in range(n):
            for j in range(i + 1, n):
                a, b = sh[i], sh[j]
                u = len(a | b)
                if u and len(a & b) / u >= theta:
                    parent[find(i)] = find(j)
        per[lab] = {"n": n, "clusters": len({find(i) for i in range(n)})}
    tot_c = sum(v["clusters"] for v in per.values())
    tot_n = sum(v["n"] for v in per.values())
    return {"per_idea": per, "clusters_per_idea": tot_c / len(per) if per else None,
            "clusters_per_10_programs": 10 * tot_c / tot_n if tot_n else None}


def cell_stats(rs: list[dict[str, Any]], default: str, twin: dict[str, Any] | None = None,
               clusters: bool = True) -> dict[str, Any]:
    n = len(rs)
    att = [r for r in rs if r["attempt"]]
    cor = [r for r in rs if r["correct"]]
    out: dict[str, Any] = {"n": n, "n_attempted": len(att), "n_correct": len(cor)}
    out["pass_rate"] = sum(r["passed"] for r in rs) / n if n else None
    out["pass_ci"] = wilson_ci(sum(r["passed"] for r in rs), n) if n else None
    out["invalid_rate"] = sum(r["invalid"] for r in rs) / n if n else None
    out["unresolved_rate"] = sum(r["unresolved"] for r in rs) / n if n else None
    out["other_rate"] = sum(r["label"] == "other" for r in att) / len(att) if att else None
    out["attempted_composition"] = dict(Counter(r["label"] for r in att))
    out["correct_composition"] = dict(Counter(r["label"] for r in cor))
    out["off_share_attempts"] = sum(r["off"] for r in att) / len(att) if att else None
    out["off_share_correct"] = sum(r["label"] != default for r in cor) / len(cor) if cor else None
    h = rarefied_hill([r["label"] for r in cor], depth=DEPTH)
    out["hill_correct"] = h["hill"]
    out["hill_depth"] = h["depth"]
    out["hill_own_depth_flag"] = h["flag_own_depth"]
    h2 = rarefied_hill([r["label"] for r in cor if r["label"] != "other"], depth=DEPTH)
    out["hill_correct_excl_other"] = h2["hill"]
    out["finish_reasons"] = dict(Counter(r["finish"] for r in rs))
    if twin is not None:
        out["excess_correct_off"] = (out["off_share_correct"] - twin["off_share_correct"]) \
            if out["off_share_correct"] is not None and twin.get("off_share_correct") is not None else None
        out["excess_attempt_off"] = (out["off_share_attempts"] - twin["off_share_attempts"]) \
            if out["off_share_attempts"] is not None and twin.get("off_share_attempts") is not None else None
        out["pass_ratio"] = out["pass_rate"] / twin["pass_rate"] if twin.get("pass_rate") else None
    if clusters:
        out["phrasing"] = {str(th): clusters_per_idea(rs, th) for th in (0.7, 0.8, 0.9)}
    d35 = [r["disp35"] for r in rs if r.get("disp35") is not None]
    out["realised_disp_R35_median"] = float(np.median(d35)) if d35 else None
    s3 = [r["s3kl"] for r in rs if r.get("s3kl") is not None]
    out["s3_kl_steps1_32_median"] = float(np.median(s3)) if s3 else None
    return out


def all_cells(rows: list[dict[str, Any]]) -> dict[str, Any]:
    res: dict[str, Any] = {}
    for t in TASKS:
        d = DEFAULT[t]
        tw = cell_stats(cell(rows, t, "TWIN", 0.0, N50_K), d)
        res[f"{t}|TWIN|0"] = tw
        twx = [r for r in rows if r["task"] == t and r["arm"] == "TWIN_X"]
        if twx:
            res[f"{t}|TWIN_X|0"] = cell_stats(twx, d, tw, clusters=False)
        for s in SITES:
            for a in GRID_ALPHAS:
                rs = cell(rows, t, s, a, N_GRID_K)
                if rs:
                    res[f"{t}|{s}|{a:g}"] = cell_stats(rs, d, tw)
        rs = cell(rows, t, "S0", 8.0, N50_K)
        if rs:
            res[f"{t}|S0|8"] = cell_stats(rs, d, tw)
        for s in ("S1E", "S2E"):
            rs = cell(rows, t, s, 1.0, N_GRID_K)
            if rs:
                res[f"{t}|{s}|1"] = cell_stats(rs, d, tw)
        if t == "T1":
            for a in GRID_ALPHAS:
                rs = cell(rows, t, "TOP5", a, N50_K)
                if rs:
                    res[f"{t}|TOP5|{a:g}"] = cell_stats(rs, d, tw)
                rs = cell(rows, t, "S0", a, N50_K)
                if rs:
                    res[f"{t}|S0_N50|{a:g}"] = cell_stats(rs, d, tw)
        for eng in ("ENG",):
            rs = [r for r in rows if r["task"] == t and r["site"] == eng]
            if rs:
                res[f"{t}|ENG|1"] = cell_stats(rs, d, tw)
    return res


# ------------------------------------------------------------------------------------------------ 11.2 hull
def hull_settings(rows: list[dict[str, Any]], t: str, s: str, alphas=GRID_ALPHAS) -> list[dict[str, Any]]:
    out = []
    for a in (0.0,) + tuple(alphas):
        rs = cell(rows, t, "TWIN" if a == 0.0 else s, a, grid_ks("TWIN" if a == 0 else s, a))
        out.append({"alpha": a, "rows": rs})
    return out


def _settings_from(rows_by_setting: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
    return [{"pass": (sum(r["passed"] for r in rs) / len(rs)) if rs else 0.0,
             "correct_labels": [r["label"] for r in rs if r["correct"]]} for rs in rows_by_setting]


def _strat_resample(rs: list[dict[str, Any]], rng: np.random.Generator) -> list[dict[str, Any]]:
    by: dict[str, list] = defaultdict(list)
    for r in rs:
        by[r["w"]].append(r)
    out = []
    for w in sorted(by):
        g = by[w]
        idx = rng.integers(0, len(g), size=len(g))
        out.extend(g[i] for i in idx)
    return out


def _boot_task(args: tuple) -> dict[str, Any]:
    t, packs, B, seed = args
    rng = np.random.default_rng(seed)
    out = {s: {"H5": [], "P15": [], "P20": []} for s in packs}
    for b in range(B):
        # the twin is resampled once per replicate and shared by every site (same twin in every hull)
        twin_b = _strat_resample(packs[next(iter(packs))][0], rng)
        for s, sets in packs.items():
            rb = [twin_b] + [_strat_resample(x, rng) for x in sets[1:]]
            hp = hull_prices(_settings_from(rb), n_draws=200, step=0.1, seed=int(rng.integers(1 << 31)))
            for key in ("H5", "P15", "P20"):
                out[s][key].append(hp[key])
    return {"task": t, "boot": out}


def hull_all(rows: list[dict[str, Any]], B: int, workers: int) -> dict[str, Any]:
    t0 = time.time()
    point: dict[str, Any] = {}
    packs_by_task = {}
    for t in TASKS:
        packs = {}
        for s in SITES:
            st = hull_settings(rows, t, s)
            if any(not x["rows"] for x in st):
                continue
            packs[s] = [x["rows"] for x in st]
            hp = hull_prices(_settings_from(packs[s]), n_draws=1000, step=0.05, seed=0, keep_frontier=True)
            point[f"{t}|{s}"] = hp
            # sensitivity 1: linear interpolation along alpha (mixtures of adjacent settings only)
            # sensitivity 2: S0 with alpha 8 appended
        if "S0" in packs:
            r8 = cell(rows, t, "S0", 8.0, N50_K)
            if r8:
                hp8 = hull_prices(_settings_from(packs["S0"] + [r8]), n_draws=1000, step=0.05, seed=0,
                                  keep_frontier=True)
                point[f"{t}|S0+a8"] = hp8
        packs_by_task[t] = packs
    for t, packs in packs_by_task.items():
        for s, sets in packs.items():
            point[f"{t}|{s}"]["adjacent_only"] = _adjacent_interp(_settings_from(sets))
    logger.info(f"hull point estimates in {time.time() - t0:.0f}s")
    boot: dict[str, Any] = {}
    if B > 0:
        jobs = [(t, packs_by_task[t], B, 1000 + i) for i, t in enumerate(TASKS) if packs_by_task.get(t)]
        with ProcessPoolExecutor(max_workers=workers, mp_context=mp.get_context("spawn")) as ex:
            for res in ex.map(_boot_task, jobs):
                boot[res["task"]] = res["boot"]
        logger.info(f"hull bootstrap B={B} in {time.time() - t0:.0f}s")
    return {"point": point, "boot": boot, "B": B}


def _adjacent_interp(settings: list[dict[str, Any]]) -> dict[str, Any]:
    """Sensitivity: only mixtures of two adjacent settings along alpha (linear interpolation)."""
    from hull import HullSampler, COST_BOUND

    hs = HullSampler(settings, n_draws=1000, seed=0)
    best = -1.0
    p15 = p20 = math.inf
    for j in range(len(settings) - 1):
        for lam in np.linspace(0, 1, 21):
            w = np.zeros(len(settings))
            w[j], w[j + 1] = 1 - lam, lam
            c, h = hs.cost_of(w), hs.hill_of(w)
            if not np.isfinite(h):
                continue
            if c <= COST_BOUND + 1e-12:
                best = max(best, h)
            if h >= 1.5:
                p15 = min(p15, c)
            if h >= 2.0:
                p20 = min(p20, c)
    return {"H5": best if best >= 0 else None, "P15": p15, "P20": p20}


def c1_site(hull: dict[str, Any]) -> dict[str, Any]:
    pt = hull["point"]
    h5 = {t: {s: pt[f"{t}|{s}"]["H5"] for s in SITES if f"{t}|{s}" in pt} for t in TASKS}
    p15 = {t: {s: pt[f"{t}|{s}"]["P15"] for s in SITES if f"{t}|{s}" in pt} for t in TASKS}
    h5 = {t: v for t, v in h5.items() if len(v) == len(SITES)}
    p15 = {t: p15[t] for t in h5}
    dec = c1_decision(h5, p15)
    if not h5:
        dec["verdict"] = "NOT EVALUABLE (no task has all six sites yet)"
    per: dict[str, Any] = {}
    for t in h5:
        others = {s: v for s, v in h5[t].items() if s != "S0"}
        D = h5[t]["S0"] - max(others.values())
        rec: dict[str, Any] = {"H5": h5[t], "P15": p15[t], "D_t": D,
                               "P20": {s: pt[f"{t}|{s}"]["P20"] for s in SITES}}
        bt = hull["boot"].get(t)
        if bt:
            Bn = len(bt["S0"]["H5"])
            arr = {s: np.array(bt[s]["H5"], dtype=float) for s in SITES if s in bt}
            Db = arr["S0"] - np.nanmax(np.stack([arr[s] for s in arr if s != "S0"]), axis=0)
            Db = Db[np.isfinite(Db)]
            rec["D_t_ci95"] = [float(np.quantile(Db, 0.025)), float(np.quantile(Db, 0.975))] if len(Db) else None
            present = [s for s in SITES if s in arr]
            M = np.stack([np.round(arr[s], 2) for s in present])
            win = np.zeros(Bn)
            for b in range(Bn):
                col = M[:, b]
                if np.all(~np.isfinite(col)):
                    continue
                mx = np.nanmax(col)
                cands = [present[i] for i in range(len(present)) if col[i] == mx]
                if cands == ["S0"]:
                    win[b] = 1
            rec["P_S0_argmax_boot"] = float(win.mean())
            rec["H5_ci95"] = {s: [float(np.nanquantile(arr[s], 0.025)), float(np.nanquantile(arr[s], 0.975))]
                              for s in arr}
            rec["S0_within_0.10_of_best_share_boot"] = float(np.mean(Db >= -0.10)) if len(Db) else None
            rec["close_call"] = bool(rec["D_t_ci95"] and rec["D_t_ci95"][0] < 0 < rec["D_t_ci95"][1])
        per[t] = rec
    dec["per_task"] = per
    dec["equivalence_margin_0.10"] = {t: bool(abs(per[t]["D_t"]) <= 0.10) for t in per}
    return dec


# ------------------------------------------------------------------------------------------------ 11.4 / 11.5
def failure_modes(cells: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for t in TASKS:
        tw = cells.get(f"{t}|TWIN|0")
        if not tw:
            continue
        for s in SITES:
            rec = {}
            for a in GRID_ALPHAS:
                c = cells.get(f"{t}|{s}|{a:g}")
                if c:
                    rec[a] = {"excess": c["excess_correct_off"], "pass_ratio": c["pass_ratio"],
                              "invalid": c["invalid_rate"]}
            if not rec:
                continue
            ex = {a: (v["excess"] if v["excess"] is not None else 0.0) for a, v in rec.items()}
            pr = {a: (v["pass_ratio"] if v["pass_ratio"] is not None else 0.0) for a, v in rec.items()}
            iv = {a: v["invalid"] or 0.0 for a, v in rec.items()}
            if any(ex[a] >= 0.20 and pr[a] >= 0.8 for a in rec):
                mode = "moves"
            elif any(ex[a] >= 0.10 for a in rec) and all(pr[a] < 0.8 for a in rec if ex[a] >= 0.10):
                mode = "moves with cost"
            elif any((pr[a] < 0.8 or iv[a] >= 0.2) and ex[a] < 0.10 for a in rec):
                mode = "breakage first"
            elif all(ex[a] < 0.10 and pr[a] >= 0.8 for a in rec):
                mode = "no movement"
            else:
                mode = "unclassified (weak movement: 0.10 <= excess < 0.20 with pass >= 0.8 x twin)"
            out[f"{t}|{s}"] = {"mode": mode, "by_alpha": rec}
    summ = {s: dict(Counter(v["mode"] for k, v in out.items() if k.endswith("|" + s))) for s in SITES}
    return {"per_task_site": out, "summary_by_site": summ}


def hill_gain(cells: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for t in TASKS:
        tw = cells.get(f"{t}|TWIN|0")
        if not tw:
            continue
        for s in SITES:
            for a in GRID_ALPHAS:
                c = cells.get(f"{t}|{s}|{a:g}")
                if not c or c["hill_correct"] is None or tw["hill_correct"] is None:
                    continue
                dp = tw["pass_rate"] - c["pass_rate"]
                out[f"{t}|{s}|{a:g}"] = {"G": (c["hill_correct"] - tw["hill_correct"]) / max(dp, 0.01),
                                         "dHill": c["hill_correct"] - tw["hill_correct"], "dPass": dp}
    return out


# ------------------------------------------------------------------------------------------------ 11.6 paired flips
def mcnemar_exact(b: int, c: int) -> float:
    from scipy.stats import binomtest

    n = b + c
    return 1.0 if n == 0 else float(binomtest(min(b, c), n, 0.5).pvalue)


def paired_flips(rows: list[dict[str, Any]]) -> dict[str, Any]:
    idx = {(r["task"], r["w"], r["k"], r["arm"]): r for r in rows}
    out = {}
    for t in TASKS:
        for a in GRID_ALPHAS:
            s0a = f"S0_a{a:g}"
            for s in SITES[1:]:
                arm = f"{s}_a{a:g}"
                tab = {"attempts": [0, 0, 0, 0], "correct": [0, 0, 0, 0]}  # [both, S0 only, site only, neither]
                ident_twin = ident_s0 = npair = 0
                for w in TEMPLATE_IDS:
                    for k in N_GRID_K:
                        r0, r1, tw = idx.get((t, w, k, s0a)), idx.get((t, w, k, arm)), idx.get((t, w, k, "TWIN"))
                        if not r0 or not r1:
                            continue
                        npair += 1
                        if tw is not None:
                            ident_twin += (r1["code_sha256"] is not None and r1["code_sha256"] == tw["code_sha256"])
                        ident_s0 += (r1["code_sha256"] is not None and r1["code_sha256"] == r0["code_sha256"])
                        for kind, ok in (("attempts", r0["attempt"] and r1["attempt"]),
                                         ("correct", r0["correct"] and r1["correct"])):
                            if not ok:
                                continue
                            o0 = r0["label"] != DEFAULT[t]
                            o1 = r1["label"] != DEFAULT[t]
                            tab[kind][0 if (o0 and o1) else 1 if o0 else 2 if o1 else 3] += 1
                if npair == 0:
                    continue
                out[f"{t}|{s}|{a:g}"] = {
                    "n_pairs": npair, "table_attempts[both,S0only,siteonly,neither]": tab["attempts"],
                    "mcnemar_p_attempts": mcnemar_exact(tab["attempts"][1], tab["attempts"][2]),
                    "table_correct": tab["correct"], "mcnemar_p_correct": mcnemar_exact(tab["correct"][1],
                                                                                        tab["correct"][2]),
                    "byte_identical_vs_twin": ident_twin / npair, "byte_identical_vs_S0": ident_s0 / npair}
    # twin vs S0 byte-identical rates (inertness of S0 itself)
    for t in TASKS:
        for a in GRID_ALPHAS:
            n = same = 0
            for w in TEMPLATE_IDS:
                for k in N_GRID_K:
                    r0, tw = idx.get((t, w, k, f"S0_a{a:g}")), idx.get((t, w, k, "TWIN"))
                    if r0 and tw:
                        n += 1
                        same += (r0["code_sha256"] is not None and r0["code_sha256"] == tw["code_sha256"])
            if n:
                out[f"{t}|S0|{a:g}|vs_twin"] = {"n_pairs": n, "byte_identical_vs_twin": same / n}
    return out


# ------------------------------------------------------------------------------------------------ 11.7 / 11.8
def transmission(rows: list[dict[str, Any]]) -> dict[str, Any]:
    import pandas as pd
    import statsmodels.formula.api as smf

    pre = [r for r in rows if r["site"] in ("S0", "S1", "S2", "S4", "S5", "S1E", "S2E") and r["correct"] and
           r.get("disp35") and r["k"] in N_GRID_K and r["alpha"] in (1.0, 2.0, 4.0)]
    df = pd.DataFrame([{"y": int(r["label"] != DEFAULT[r["task"]]), "logd": math.log(max(r["disp35"], 1e-6)),
                        "logkl": math.log(max(r["ftkl"] or 0.0, 1e-12)), "is_S0": int(r["site"] == "S0"),
                        "site": r["site"], "task": r["task"], "w": r["w"], "alpha": r["alpha"]} for r in pre])
    out: dict[str, Any] = {"n_rows": len(df)}
    if df.empty:
        return out
    var_tasks = [t for t, g in df.groupby("task") if 0 < g["y"].mean() < 1]
    d2 = df[df["task"].isin(var_tasks)].copy()
    out["tasks_with_variation"] = var_tasks
    out["n_rows_used"] = len(d2)
    out["ftkl_degenerate"] = bool(df["logkl"].std() < 1e-6 or (np.exp(df["logkl"]) < 1e-6).mean() > 0.9)
    out["ftkl_share_below_1e-6"] = float((np.exp(df["logkl"]) < 1e-6).mean())
    for name, f in (("disp_R35", "y ~ logd + is_S0 + C(w) + C(task)"),
                    ("disp_R35_sites", "y ~ logd + C(site, Treatment('S0')) + C(w) + C(task)"),
                    ("first_token_kl", "y ~ logkl + is_S0 + C(w) + C(task)")):
        try:
            if len(var_tasks) < 1 or len(d2) < 20:
                raise ValueError("too few rows with variation")
            m = smf.logit(f.replace(" + C(task)", "") if len(var_tasks) == 1 else f, data=d2).fit(disp=0,
                                                                                                    maxiter=200)
            ci = m.conf_int()
            out[name] = {"params": {k: float(v) for k, v in m.params.items() if not k.startswith("C(w")},
                         "ci95": {k: [float(ci.loc[k, 0]), float(ci.loc[k, 1])] for k in m.params.index
                                  if not k.startswith("C(w") and not k.startswith("C(task")},
                         "converged": bool(m.mle_retvals.get("converged", True)), "n": int(m.nobs)}
            if "is_S0" in m.params:
                lo, hi = ci.loc["is_S0", 0], ci.loc["is_S0", 1]
                out[name]["S0_reading"] = ("site-specific beyond downstream dose" if lo > 0 else
                                           "S0 below others at matched transmission" if hi < 0 else
                                           "generic transmission (S0 indicator CI includes 0)")
        except Exception as e:  # noqa: BLE001 - separation / singular fits are reported, not hidden
            out[name] = {"error": str(e)[:200]}
    # matched-dose bins: off-default among correct programs, S0 vs other prefill sites within quintiles of log d
    if len(df) >= 10:
        q = np.quantile(df["logd"], [0, 0.2, 0.4, 0.6, 0.8, 1.0])
        bins = []
        for i in range(5):
            g = df[(df["logd"] >= q[i]) & (df["logd"] <= q[i + 1])]
            a, b = g[g["is_S0"] == 1], g[g["is_S0"] == 0]
            bins.append({"logd_range": [float(q[i]), float(q[i + 1])], "n_S0": len(a), "n_other": len(b),
                         "off_S0": float(a["y"].mean()) if len(a) else None,
                         "off_other": float(b["y"].mean()) if len(b) else None})
        out["matched_dose_bins"] = bins
    # S3 on its own step-wise KL
    s3 = [r for r in rows if r["site"] == "S3" and r["correct"] and r.get("s3kl") is not None and
          r["k"] in N_GRID_K]
    if s3:
        d3 = pd.DataFrame([{"y": int(r["label"] != DEFAULT[r["task"]]), "logkl": math.log(max(r["s3kl"], 1e-9)),
                            "task": r["task"], "alpha": r["alpha"]} for r in s3])
        out["S3_stepwise_kl"] = {"n": len(d3), "off_rate": float(d3["y"].mean()),
                                 "median_kl_by_alpha": {str(a): float(g["logkl"].apply(math.exp).median())
                                                        for a, g in d3.groupby("alpha")}}
        try:
            vt = [t for t, g in d3.groupby("task") if 0 < g["y"].mean() < 1]
            d4 = d3[d3["task"].isin(vt)]
            if len(vt) >= 1 and len(d4) >= 20:
                m = smf.logit("y ~ logkl" + (" + C(task)" if len(vt) > 1 else ""), data=d4).fit(disp=0)
                out["S3_stepwise_kl"]["logkl_coef"] = float(m.params["logkl"])
                out["S3_stepwise_kl"]["logkl_ci95"] = [float(x) for x in m.conf_int().loc["logkl"]]
        except Exception as e:  # noqa: BLE001
            out["S3_stepwise_kl"]["error"] = str(e)[:200]
    # descriptive: median realised displacement at R (block 35) per site and alpha
    md = defaultdict(list)
    for r in rows:
        if r.get("disp35") is not None and r["k"] in N_GRID_K:
            md[f"{r['site']}|{r['alpha']:g}"].append(r["disp35"])
    out["median_disp_R35_by_site_alpha"] = {k: float(np.median(v)) for k, v in sorted(md.items())}
    return out


def pooled_model(rows: list[dict[str, Any]]) -> dict[str, Any]:
    import pandas as pd

    rs = [r for r in rows if r["site"] in SITES and r["attempt"] and r["k"] in N_GRID_K and r["alpha"] in GRID_ALPHAS]
    df = pd.DataFrame([{"y": int(r["off"]), "site": r["site"], "la": math.log2(r["alpha"]), "task": r["task"],
                        "w": r["w"]} for r in rs])
    out: dict[str, Any] = {"n": len(df)}
    if df.empty:
        return out
    try:
        from statsmodels.genmod.bayes_mixed_glm import BinomialBayesMixedGLM

        m = BinomialBayesMixedGLM.from_formula("y ~ C(site, Treatment('S0')) * la",
                                               {"task": "0 + C(task)", "template": "0 + C(w)"}, df)
        f = m.fit_vb()
        names = m.exog_names
        out["fixed_effects_posterior_mean"] = {n: float(v) for n, v in zip(names, f.fe_mean)}
        out["fixed_effects_posterior_sd"] = {n: float(v) for n, v in zip(names, f.fe_sd)}
        out["vc_log_sd_mean"] = {n: float(v) for n, v in zip(m.vcp_names, f.vcp_mean)}
    except Exception as e:  # noqa: BLE001
        out["error"] = str(e)[:200]
    tab = df.groupby(["site", "w"])["y"].mean().unstack().round(3)
    out["site_x_template_off_share_attempts"] = {s: {w: (None if pd.isna(v) else float(v)) for w, v in row.items()}
                                                 for s, row in tab.iterrows()}
    return out


# ------------------------------------------------------------------------------------------------ 11.9 boundary
def boundary(rows: list[dict[str, Any]], cells: dict[str, Any], hull: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for t in TASKS:
        d = DEFAULT[t]
        tw = cells.get(f"{t}|TWIN|0")
        curve = []
        for a in (0.0, 1.0, 2.0, 4.0, 8.0):
            rs = cell(rows, t, "TWIN" if a == 0 else "S0", a, None if a in (1.0, 2.0, 4.0) else N50_K)
            if not rs:
                continue
            c = cell_stats(rs, d, tw, clusters=False)
            curve.append({"alpha": a, "n": c["n"], "pass": c["pass_rate"], "invalid": c["invalid_rate"],
                          "other_share_attempts": c["other_rate"], "hill_correct": c["hill_correct"],
                          "hill_depth": c["hill_depth"], "off_share_correct": c["off_share_correct"],
                          "correct_composition": c["correct_composition"]})
        peak = max((x for x in curve if x["hill_correct"] is not None), key=lambda x: x["hill_correct"],
                   default=None)
        a8 = next((x for x in curve if x["alpha"] == 8.0), None)
        out[t] = {"curve": curve, "hill_peak_alpha": peak["alpha"] if peak else None,
                  "pass_at_alpha8": a8["pass"] if a8 else None,
                  "frontier_S0_with_a8": hull["point"].get(f"{t}|S0+a8", {}).get("frontier")}
    n_lt = sum(1 for t in out if out[t]["pass_at_alpha8"] is not None and out[t]["pass_at_alpha8"] < 0.5)
    peaks = Counter(out[t]["hill_peak_alpha"] for t in out)
    return {"per_task": out, "n_tasks_pass_lt_0.5_at_alpha8": n_lt, "hill_peak_alpha_counts": dict(peaks),
            "prediction_pass_lt_0.5_on_ge4": n_lt >= 4}


# ------------------------------------------------------------------------------------------------ 11.10 overlap
def overlap_check(rows: list[dict[str, Any]]) -> dict[str, Any]:
    import json

    base = ROOT.parent
    found = []
    for f in sorted(glob.glob(str(base / "*" / "data" / "samples.jsonl"))):
        if str(ROOT) in f:
            continue
        try:
            with open(f) as fh:
                for line in fh:
                    r = json.loads(line)
                    if "Qwen3-8B" in str(r.get("model", "")) and str(r.get("arm", r.get("condition", ""))) in (
                            "PN", "PN_a4") and float(r.get("alpha", 0) or 0) == 4.0:
                        found.append({"file": f.replace(str(base), "<iter_4/gen_art>"), "task": r.get("task"),
                                      "label": r.get("label"),
                                      "w": r.get("template") or r.get("paraphrase_id") or r.get("w")})
        except (OSError, ValueError):
            continue
    if not found:
        return {"status": "pending", "note": "no Step-1 rows (model Qwen3-8B, arm PN, alpha 4) found among sibling "
                                             "iter-4 artifacts at analysis time; tools/overlap_check.py runs the "
                                             "comparison later"}
    out = {"status": "done", "n_rows": len(found), "sources": sorted({x["file"] for x in found}), "per_task": {},
           "null": "pooled (template-stratified where both sides carry templates) resampling of the two compositions "
                   "at their own sizes, 2,000 draws; REPRODUCED if JS <= null q95"}
    rng = np.random.default_rng(0)
    for t in TASKS:
        th = [x for x in found if x["task"] == t and x["label"] and x["label"] not in INVALID + UNRES]
        ou = [r for r in cell(rows, t, "S0", 4.0, N_GRID_K) if r["attempt"]]
        theirs, ours = Counter(x["label"] for x in th), Counter(r["label"] for r in ou)
        if not (theirs and ours):
            continue
        js = js_div(ours, theirs)
        pooled = [(x.get("w"), x["label"]) for x in th] + [(r["w"], r["label"]) for r in ou]
        strat = all(w for w, _ in pooled)
        by = defaultdict(list)
        for w, l in pooled:
            by[w if strat else "all"].append(l)
        na, nb = len(ou), len(th)
        null = []
        for _ in range(2000):
            a, b = Counter(), Counter()
            for g, ls in by.items():
                fa = na / (na + nb)
                ka = max(1, int(round(len(ls) * fa)))
                a.update(rng.choice(ls, size=ka, replace=True))
                b.update(rng.choice(ls, size=max(1, len(ls) - ka), replace=True))
            null.append(js_div(a, b))
        q95 = float(np.quantile(null, 0.95))
        offa = sum(v for k, v in ours.items() if k != DEFAULT[t]) / sum(ours.values())
        offb = sum(v for k, v in theirs.items() if k != DEFAULT[t]) / sum(theirs.values())
        out["per_task"][t] = {"ours": dict(ours), "theirs": dict(theirs), "js": js, "null_q95": q95,
                              "template_stratified": strat, "off_ours": offa, "off_theirs": offb,
                              "REPRODUCED": bool(js <= q95)}
    return out


def js_div(a: Counter, b: Counter) -> float:
    keys = sorted(set(a) | set(b))
    p = np.array([a.get(k, 0) for k in keys], float)
    q = np.array([b.get(k, 0) for k in keys], float)
    p, q = p / p.sum(), q / q.sum()
    m = (p + q) / 2

    def kl(x, y):
        mm = x > 0
        return float((x[mm] * np.log2(x[mm] / y[mm])).sum())
    return 0.5 * kl(p, m) + 0.5 * kl(q, m)


# ------------------------------------------------------------------------------------------------ engine check
def engine_check(rows: list[dict[str, Any]]) -> dict[str, Any]:
    scr = defaultdict(list)
    from cfg import E17

    for r in read_jsonl(E17 / "data" / "labels.jsonl"):
        scr[(r["task"], r["arm"])].append(r)
    out = {}
    rng = np.random.default_rng(0)
    for t, arm, sarm in (("T03", "ENG_r9002_a1", "RAND9002_a1.0"), ("T2", "ENG_r9004_a1", "RAND9004_a1.0")):
        ours = [r for r in rows if r["task"] == t and r["arm"] == arm]
        theirs = [r for r in scr[(t, sarm)] if int(r["sample_id"]) < 10]
        ca = Counter(r["label"] for r in ours if r["attempt"])
        cb = Counter(r["label"] for r in theirs if r["label"] not in ("invalid", "disputed"))
        js = js_div(ca, cb) if ca and cb else None
        pooled = [(r["w"], r["label"]) for r in ours if r["attempt"]] + \
                 [(r["template"], r["label"]) for r in theirs if r["label"] not in ("invalid", "disputed")]
        by = defaultdict(list)
        for w, l in pooled:
            by[w].append(l)
        null = []
        for _ in range(2000):
            s1, s2 = Counter(), Counter()
            for w, ls in by.items():
                n = len(ls) // 2
                s1.update(rng.choice(ls, size=n, replace=True))
                s2.update(rng.choice(ls, size=n, replace=True))
            null.append(js_div(s1, s2))
        q95 = float(np.quantile(null, 0.95))
        offa = sum(v for k, v in ca.items() if k != DEFAULT[t]) / max(sum(ca.values()), 1)
        offb = sum(v for k, v in cb.items() if k != DEFAULT[t]) / max(sum(cb.values()), 1)
        theirs_by = {(r["template"], int(r["sample_id"])): r for r in theirs}
        agree = same = n = 0
        for r in ours:
            s = theirs_by.get((r["w"], r["k"]))
            if s:
                n += 1
                agree += r["label"] == s["label"]
                same += r["code_sha256"] is not None and r["code_sha256"] == s.get("code_sha256")
        out[t] = {"ours": dict(ca), "screen": dict(cb), "js": js, "null_q95": q95, "off_ours": offa,
                  "off_screen": offb, "per_slot_label_agreement": agree / n if n else None,
                  "per_slot_identical_code": same / n if n else None, "n_slots": n,
                  "REPRODUCED": bool(js is not None and js <= q95 and abs(offa - offb) <= 0.15)}
    return out


# ------------------------------------------------------------------------------------------------ 11.11 C3d
def c3d(rows: list[dict[str, Any]]) -> dict[str, Any]:
    from scipy.sparse import csr_matrix
    from scipy.sparse.csgraph import connected_components, shortest_path
    from sklearn.neighbors import NearestNeighbors

    z = np.load(DIR_DIR / "plan_geometry_T1.npz")
    pc, algs = z["pc"], [str(a) for a in z["algs"]]
    A = np.array(algs)
    names = sorted(set(algs))
    geo_out: dict[str, Any] = {}

    def geodesics(k):
        while True:
            nn = NearestNeighbors(n_neighbors=k + 1).fit(pc)
            dist, ind = nn.kneighbors(pc)
            n = len(pc)
            rr = np.repeat(np.arange(n), k)
            cc = ind[:, 1:].ravel()
            vv = dist[:, 1:].ravel()
            Gm = csr_matrix((vv, (rr, cc)), shape=(n, n))
            Gm = Gm.maximum(Gm.T)
            ncomp, _ = connected_components(Gm, directed=False)
            if ncomp == 1:
                return shortest_path(Gm, directed=False), k
            k += 1

    for k in (10, 5, 15):
        D, k_used = geodesics(k)
        G = np.zeros((len(names), len(names)))
        for i, a in enumerate(names):
            for j, b in enumerate(names):
                if i != j:
                    G[i, j] = float(np.median(D[np.ix_(A == a, A == b)]))
        dY = {y: float(min(G[names.index(y), names.index(x)] for x in TOP5)) for y in SURV_EXT}
        geo_out[f"k{k}"] = {"k_used": k_used, "G": {a: {b: float(G[i, j]) for j, b in enumerate(names)}
                                                    for i, a in enumerate(names)}, "d_survivor_to_TOP5": dY}
    G = np.array([[geo_out["k10"]["G"][a][b] for b in names] for a in names])
    try:
        from sklearn.manifold import MDS

        mds = MDS(n_components=2, dissimilarity="precomputed", random_state=0, n_init=8, normalized_stress="auto")
        X2 = mds.fit_transform(G)
        dd = np.sqrt(((X2[:, None] - X2[None]) ** 2).sum(-1))
        iu = np.triu_indices(len(names), 1)
        stress1 = float(np.sqrt(((dd[iu] - G[iu]) ** 2).sum() / (G[iu] ** 2).sum()))
        geo_out["mds"] = {"coords": {a: X2[i].tolist() for i, a in enumerate(names)}, "stress1": stress1}
    except Exception as e:  # noqa: BLE001
        geo_out["mds"] = {"error": str(e)[:200]}
    try:
        from ripser import ripser

        dg = ripser(pc[:, :10], maxdim=1)["dgms"][1]
        life = (dg[:, 1] - dg[:, 0]) if len(dg) else np.array([0.0])
        rng = np.random.default_rng(0)
        null = []
        for _ in range(20):
            P = pc[:, :10].copy()
            for j in range(P.shape[1]):
                P[:, j] = rng.permutation(P[:, j])
            dgn = ripser(P, maxdim=1)["dgms"][1]
            null.append(float((dgn[:, 1] - dgn[:, 0]).max()) if len(dgn) else 0.0)
        geo_out["persistence_H1"] = {"max_lifetime": float(life.max()), "null_max_q95": float(np.quantile(null, 0.95)),
                                     "loop_evidence": bool(life.max() > np.quantile(null, 0.95)),
                                     "note": "descriptive; PCA-10 of the 300 forced points; coordinate-permutation null"}
    except Exception as e:  # noqa: BLE001
        geo_out["persistence_H1"] = {"error": str(e)[:200]}
    raw = read_json(RESULTS_DIR / "plan_geometry_T1_raw.json")
    geo_out["separability"] = raw.get("nearest_centroid_acc")
    geo_out["u_top5_version"] = raw.get("u_top5_version")
    geo_out["u_top5_cosines"] = raw.get("cosines")
    write_json(RESULTS_DIR / "plan_geometry_T1.json", geo_out)
    dY7 = {y: geo_out["k10"]["d_survivor_to_TOP5"][y] for y in SURV7}
    dYe = geo_out["k10"]["d_survivor_to_TOP5"]

    def score(rs: list[dict[str, Any]], lab_key: str, surv: tuple, dvals: dict[str, float]) -> dict[str, Any]:
        cor = [r for r in rs if r.get(lab_key) not in (None, "invalid") and r.get("passed_k7", r["passed"])]
        n = len(cor)
        off = [r for r in cor if r[lab_key] not in TOP5]
        sv = Counter(r[lab_key] for r in off if r[lab_key] in surv)
        tot = sum(sv.values())
        res = {"n_correct": n, "avoidance": len(off) / n if n else None,
               "avoidance_ci": wilson_ci(len(off), n) if n else None, "landing_counts": dict(sv),
               "composition_correct": dict(Counter(r[lab_key] for r in cor)),
               "composition_all": dict(Counter(r.get(lab_key) for r in rs))}
        if tot:
            q = {y: sv.get(y, 0) / tot for y in surv}
            dobs = sum(q[y] * dvals[y] for y in surv)
            import itertools

            perms = [sum(q[y] * dict(zip(surv, p))[y] for y in surv) for p in itertools.permutations(
                [dvals[y] for y in surv])]
            res.update({"q": q, "D_obs": dobs, "n_perm": len(perms),
                        "p_edge": float(np.mean([v <= dobs + 1e-12 for v in perms])),
                        "p_opp": float(np.mean([v >= dobs - 1e-12 for v in perms]))})
        return res

    out: dict[str, Any] = {"d_survivor_k7": dY7, "d_survivor_ext": dYe, "by_arm": {}}
    for a in GRID_ALPHAS:
        for arm in (f"TOP5_a{a:g}", f"S0_a{a:g}"):
            rs = [r for r in rows if r["task"] == "T1" and r["arm"] == arm and r["k"] in N50_K]
            if not rs:
                continue
            out["by_arm"][arm] = {"n": len(rs), "k7": score(rs, "label_k7", SURV7, dY7),
                                  "ext_flagged": score(rs, "label_ext", SURV_EXT, dYe)}
    tw = [r for r in rows if r["task"] == "T1" and r["arm"] == "TWIN"]
    out["by_arm"]["TWIN"] = {"n": len(tw), "k7": score(tw, "label_k7", SURV7, dY7)}
    out["references"] = {"prompt_TOP5_ban_exp9": {"avoidance": 0.00, "BFS": 63, "DFS": 36, "IDDFS": 1},
                         "token_veto_TOP5_exp18": {"BFS": 13, "DFS": 2, "invalid": 35}}
    out["prediction_avoidance_lt_0.5_at_alpha_le_2"] = all(
        (out["by_arm"].get(f"TOP5_a{a:g}", {}).get("k7", {}).get("avoidance") or 0) < 0.5 for a in (1.0, 2.0))
    out["status"] = "descriptive (K=7: 2 gated survivors -> exact permutation p floor 0.5; extended labeller flagged)"
    return out


# ------------------------------------------------------------------------------------------------ units summary
def units_summary() -> dict[str, Any]:
    """Per task and site: mean per-position unit over the hooked blocks (absolute and relative to ||h_twin||),
    energy-matching scalars, and the block profile of the S unit (descriptive)."""
    from cfg import UNITS_DIR

    out = {}
    for t in TASKS:
        z = np.load(UNITS_DIR / f"units_{t}.npz")
        nS, rS, nR, rR = z["nS"], z["relS"], z["nR"], z["relR"]
        rec = {"S0_blocks12_23": {"abs": float(nS[12:24].mean()), "rel": float(rS[12:24].mean())},
               "S4_blocks0_11": {"abs": float(nS[0:12].mean()), "rel": float(rS[0:12].mean())},
               "S5_blocks24_35": {"abs": float(nS[24:36].mean()), "rel": float(rS[24:36].mean())},
               "S1_R_blocks12_23": {"abs": float(nR[12:24].mean()), "rel": float(rR[12:24].mean())},
               "S3_nG_blocks12_23": {"abs": float(z["nG"].mean())},
               "S2_COND_blocks12_23": {w: {"abs": float(z[f"nC_{w}"][12:24].mean()),
                                           "rel": float(z[f"relC_{w}"][12:24].mean()),
                                           "n_positions": int(z[f"nC_{w}"].shape[1])} for w in TEMPLATE_IDS},
               "cS1_blocks12_23_mean": float(z["cS1"][12:24].mean()),
               "cS2_blocks12_23_mean": {w: float(z[f"cS2_{w}"][12:24].mean()) for w in TEMPLATE_IDS},
               "nS_block_profile": [float(x) for x in nS.mean(1)], "n_S_positions": int(nS.shape[1])}
        out[t] = rec
    return out


# ------------------------------------------------------------------------------------------------ main
def main(B: int = 1000, workers: int = 4) -> None:
    setup_logging("analysis")
    t0 = time.time()
    rows = load_rows()
    logger.info(f"loaded {len(rows)} labelled program rows")
    cells = all_cells(rows)
    write_json(RESULTS_DIR / "cells.json", cells)
    eng = engine_check(rows)
    write_json(RESULTS_DIR / "engine_check.json", eng)
    hull = hull_all(rows, B=B, workers=workers)
    write_json(RESULTS_DIR / "hull.json", {"point": hull["point"], "B": B,
                                           "boot_summary": {t: {s: {k: [float(np.nanmean(np.where(np.isinf(v), np.nan,
                                                                                                   v))) if len(v) else
                                                                     None for v in [np.array(x[k], float)]][0]
                                                                for k in x} for s, x in bt.items()}
                                                            for t, bt in hull["boot"].items()}})
    np.savez_compressed(RESULTS_DIR / "hull_boot.npz", **{f"{t}|{s}|{k}": np.array(v, float)
                                                          for t, bt in hull["boot"].items() for s, x in bt.items()
                                                          for k, v in x.items()})
    c1 = c1_site(hull)
    write_json(RESULTS_DIR / "c1_site.json", c1)
    write_json(RESULTS_DIR / "failure_modes.json", failure_modes(cells))
    write_json(RESULTS_DIR / "hill_gain.json", hill_gain(cells))
    write_json(RESULTS_DIR / "paired_flips.json", paired_flips(rows))
    write_json(RESULTS_DIR / "transmission.json", transmission(rows))
    write_json(RESULTS_DIR / "pooled_model.json", pooled_model(rows))
    write_json(RESULTS_DIR / "boundary.json", boundary(rows, cells, hull))
    write_json(RESULTS_DIR / "overlap_check.json", overlap_check(rows))
    write_json(RESULTS_DIR / "c3d.json", c3d(rows))
    write_json(RESULTS_DIR / "units_summary.json", units_summary())
    logger.info(f"analysis done in {time.time() - t0:.0f}s: C1-site {c1['verdict']} (S0 best on "
                f"{c1['count_S0_best']}/{c1['n_tasks']}, p={c1['raw_p_binom']:.4f})")


if __name__ == "__main__":
    main(B=int(sys.argv[1]) if len(sys.argv) > 1 else 1000, workers=int(sys.argv[2]) if len(sys.argv) > 2 else 4)
