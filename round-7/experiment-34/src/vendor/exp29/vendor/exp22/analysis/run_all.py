#!/usr/bin/env python3
"""S7 analyses: per-arm tables, escape fractions, C2a (primary), decomposition, C2c, C2b, C3b, geometry, novelty.
Every number is computed from data/samples_raw.jsonl + data/labels.jsonl and the committed predictions; outputs go
to results/*.json and figures/ (written by analysis/figures.py)."""

from __future__ import annotations

import ast
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis"))
sys.path.insert(0, str(ROOT / "src"))

import cfg4  # noqa: E402
from cfg4 import (DEFAULT4, K, LABELS, MOVABLE, OTHER9, PRED_DIR, RAW, RESULTS_DIR, SEEDS_C2C, SEEDS_OTHER,  # noqa: E402
                  SEEDS_POP, STATES_DIR, TASKS15, read_json, read_jsonl, write_json)
from common import by_key, dist, hill1, hill1_rarefied, join_rows, share, spearman, wilson  # noqa: E402
import c2a as C2A  # noqa: E402
import c2c as C2C  # noqa: E402
import decomp as DEC  # noqa: E402
from screen import catalogue  # noqa: E402


def load_rows() -> list[dict[str, Any]]:
    raw = read_jsonl(RAW)
    lab = read_jsonl(LABELS)
    rows = join_rows(raw, lab)
    return rows


def twin_kmax(t: str) -> int:
    return len(K["twin_mov"]) if t in MOVABLE else len(K["twin_oth"])


def committed_rows(rows: list[dict[str, Any]], t: str) -> list[dict[str, Any]]:
    """Rows of task t with the TWIN restricted to its committed slots (extra pad twin rows are reported apart)."""
    return [r for r in rows if r["task"] == t and not (r["arm"] == "TWIN" and int(r["sample_id"]) >= twin_kmax(t))]


# ------------------------------------------------------------------------------------------------ phrasing clusters
def ast_4grams(code: str | None) -> set[tuple[str, ...]]:
    if not code:
        return set()
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError):
        return set()
    seq = [type(n).__name__ for n in ast.walk(tree)]
    return {tuple(seq[i:i + 4]) for i in range(len(seq) - 3)}


def jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    return len(a & b) / max(len(a | b), 1)


def n_clusters(sets: list[set], theta: float) -> int:
    """Single-linkage clusters at Jaccard >= theta."""
    n = len(sets)
    parent = list(range(n))

    def f(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for i in range(n):
        for j in range(i + 1, n):
            if jaccard(sets[i], sets[j]) >= theta:
                parent[f(i)] = f(j)
    return len({f(i) for i in range(n)})


def arm_tables(rows: list[dict[str, Any]], codes: dict[str, str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for (t, arm), rr in sorted(by_key(rows, "task", "arm").items()):
        cat = set(catalogue(t))
        s = share(rr, cat, DEFAULT4[t])
        corr = [r for r in rr if r["passed"] and r["label"] not in ("invalid", "disputed")]
        hr = hill1_rarefied([r["label"] for r in corr], depth=25)
        rec = {**s, "pass_wilson": wilson(s["k_pass"], s["n"]), "share_wilson": wilson(s["k_off"], s["n_valid"]),
               "composition": dict(Counter(r["label"] for r in rr)),
               "composition_correct": dict(Counter(r["label"] for r in corr)),
               "hill_correct": hr["hill1"], "hill_correct_rarefied25": hr["rarefied"],
               "hill_flag_below_depth": hr["flag_below_depth"]}
        if len(corr) <= 120:
            pc = {}
            for lab_, grp in by_key(corr, "label").items():
                sets = [ast_4grams(codes.get(r["code_sha256"])) for r in grp]
                pc[lab_[0]] = {str(th): n_clusters(sets, th) for th in (0.7, 0.8, 0.9)}
            rec["phrasing_clusters"] = pc
        out[f"{t}|{arm}"] = rec
    return out


# ------------------------------------------------------------------------------------------------ escape
def escape(rows: list[dict[str, Any]], screen: dict[str, Any]) -> dict[str, Any]:
    res: dict[str, Any] = {}
    for t in TASKS15:
        seeds = SEEDS_POP if t in MOVABLE else SEEDS_OTHER
        rr = committed_rows(rows, t)
        if not any(r["family"] == "POP" for r in rr):
            continue
        cat, d = set(catalogue(t)), DEFAULT4[t]
        tab = C2A.direction_table(rr, seeds, cat, d)
        tw = C2A.twin_stats(rr, cat, d)
        E = {}
        land: Counter = Counter()
        for a in ("1.0", "2.0"):
            ran = [s for s in seeds if tab[s][a]["first10"]["n"] > 0]
            conf = [s for s in ran if tab[s][a]["confirmed"]]
            E[a] = {"n_run": len(ran), "n_screen_pass": sum(tab[s][a]["screen_pass"] for s in ran),
                    "n_confirmed": len(conf), "E_t": len(conf) / len(ran) if ran else None,
                    "E_t_wilson": wilson(len(conf), len(ran)) if ran else None}
            for s in conf:
                pl = [r for r in rr if r["arm"] == f"POP_d{s}_a{a}" and r["label"] in cat and r["label"] != d]
                exc = tab[s][a]["excess_pooled"]
                c = Counter(r["label"] for r in pl)
                tot = sum(c.values())
                for k, v in c.items():
                    land[k] += exc * v / max(tot, 1)
        tot = sum(land.values())
        pland = {k: v / tot for k, v in land.most_common()} if tot else {}
        scr = screen["tasks"][t]["push_landing"]
        res[t] = {"twin": tw, "E_t": E, "movable": any((E[a]["n_confirmed"] or 0) > 0 for a in E),
                  "push_landing_v4": pland, "push_landing_screen": scr,
                  "top1_agree": (next(iter(pland), None) == next(iter(scr), None)) if pland and scr else None,
                  "confirmed": [{"seed": s, "alpha": a, "excess_pooled": tab[s][a]["excess_pooled"],
                                 "pooled": tab[s][a]["pooled"]} for s in seeds for a in ("1.0", "2.0")
                                if tab[s][a]["confirmed"]]}
    return res


# ------------------------------------------------------------------------------------------------ C2a
def c2a(rows: list[dict[str, Any]], commit: dict[str, Any], n_perm: int = 10000) -> dict[str, Any]:
    from ctx4 import rand_dir
    U = np.stack([rand_dir(s) for s in SEEDS_POP]).astype(np.float64)
    per = {}
    for t in MOVABLE:
        rr = committed_rows(rows, t)
        if not any(r["family"] == "POP" for r in rr):
            continue
        cat, d = set(catalogue(t)), DEFAULT4[t]
        res = C2A.analyse_task(rr, commit["predictors"][t], SEEDS_POP, cat, d, U, commit["tasks"][t]["k"],
                               n_perm=n_perm)
        res["kappa"] = commit["tasks"][t]["kappa"]
        per[t] = res
    out: dict[str, Any] = {"per_task": per}
    if len(per) == len(MOVABLE):
        out["verdict"] = C2A.verdict(per)
    from common import holm
    out["holm_within_family"] = {nm: holm({t: per[t]["predictors"][nm]["p"] for t in per
                                           if nm in per[t]["predictors"]}) for nm in ("pi", "pi_masked")}
    # pooled within-task rho (ranks within task), task bootstrap
    xs, ys = [], []
    from scipy.stats import rankdata
    for t, r in per.items():
        x = np.array([commit["predictors"][t][str(s)]["pi"] for s in SEEDS_POP])
        y = np.array(r["y"])
        xs.append(rankdata(x) / len(x))
        ys.append(rankdata(y) / len(y))
    if xs:
        def pooled(ix):
            X = np.concatenate([xs[i] for i in ix])
            Y = np.concatenate([ys[i] for i in ix])
            return float(np.corrcoef(X, Y)[0, 1]) if np.std(Y) > 0 else 0.0
        rng = np.random.default_rng(0)
        bs = [pooled(rng.integers(0, len(xs), len(xs))) for _ in range(2000)]
        out["pooled_within_task_rho"] = {"rho": pooled(list(range(len(xs)))),
                                         "task_bootstrap_ci": [float(np.quantile(bs, .025)),
                                                               float(np.quantile(bs, .975))]}
    # pooled per-predictor summary
    summ = {}
    for nm in [C2A.PRIMARY_PRED] + C2A.SECONDARY + C2A.CONTROLS:
        vals = {t: per[t]["predictors"][nm]["rho"] for t in per if nm in per[t]["predictors"]}
        if vals:
            summ[nm] = {"rho_by_task": vals, "mean_rho": float(np.mean(list(vals.values()))),
                        "p_by_task": {t: per[t]["predictors"][nm]["p"] for t in vals}}
    out["predictor_summary"] = summ
    return out


# ------------------------------------------------------------------------------------------------ decomposition
def decomposition(rows: list[dict[str, Any]]) -> dict[str, Any]:
    p = PRED_DIR / "decomp_list.json"
    if not p.exists():
        return {"not_run": "no decomposition list"}
    dl = read_json(p)["list"]
    out: dict[str, Any] = {"per_task": {}}
    for t, lst in dl.items():
        rr = committed_rows(rows, t)
        cat, d = set(catalogue(t)), DEFAULT4[t]
        twin_all = [r for r in rr if r["arm"] == "TWIN"]
        dirs = []
        for c in lst:
            res = DEC.analyse_direction(rr, c["seed"], c["alpha"], cat, d, twin_all)
            res.update({"seed": c["seed"], "alpha": c["alpha"]})
            if res.get("n_slots"):
                dirs.append(res)
        out["per_task"][t] = {"directions": dirs, "reading": DEC.reading(dirs) if dirs else
                              {"reading": "skipped (no confirmed escape)"}}
    alld = [x for v in out["per_task"].values() for x in v["directions"]]
    out["pooled"] = DEC.reading(alld) if alld else None
    return out


# ------------------------------------------------------------------------------------------------ C2c
def c2c(rows: list[dict[str, Any]], commit: dict[str, Any], esc: dict[str, Any]) -> dict[str, Any]:
    conf_alpha = [float(c["alpha"]) for t in MOVABLE if t in esc for c in esc[t]["confirmed"]]
    med_alpha = float(np.median(conf_alpha)) if conf_alpha else float("nan")
    per = {}
    for t in MOVABLE:
        rr = committed_rows(rows, t)
        cat, d = set(catalogue(t)), DEFAULT4[t]
        info = commit["tasks"][t]
        ru, r2 = info["runner_up"]["runner_up"], info["runner_up"]["second"]
        arms = {}
        for arm in ["TWIN", "C2C_r_s0.25", "C2C_r_s0.5", "C2C_r_s1.0", f"C2C_rand{SEEDS_C2C[t]}_s0.5", "C2C_rm_s0.5",
                    "C2C_r2_s0.5", "SWEEP_r_a4.0", "SWEEP_r_a8.0"]:
            a_rows = [r for r in rr if r["arm"] == arm]
            if a_rows:
                arms[arm] = C2C.arm_summary(a_rows, cat, d, ru, r2)
        if "C2C_r_s0.5" not in arms:
            continue
        res: dict[str, Any] = {"runner_up": ru, "second": r2, "arms": arms, "twin": arms.get("TWIN"),
                               "nu_0.5": info["nu"]["r"]["0.5"], "nu": info["nu"], "s_prime": info["s_prime"]}
        ra = f"C2C_rand{SEEDS_C2C[t]}_s0.5"
        if ra in arms:
            res["targeted_vs_random"] = C2C.paired([r for r in rr if r["arm"] == "C2C_r_s0.5"],
                                                   [r for r in rr if r["arm"] == ra], cat, d)
        if "C2C_rm_s0.5" in arms:
            res["masked_vs_named"] = C2C.paired([r for r in rr if r["arm"] == "C2C_rm_s0.5"],
                                                [r for r in rr if r["arm"] == "C2C_r_s0.5"], cat, d)
        if "C2C_r2_s0.5" in arms:
            a = arms["C2C_r2_s0.5"]
            offl = {k: v for k, v in a["composition"].items() if k in cat and k != d}
            res["second_runner_up_lands_on_X2"] = {"share_X2": a["second_share"], "share_ru": a["runner_up_share"],
                                                   "off_default_composition": offl,
                                                   "lands_on_X2": bool(offl) and max(offl, key=offl.get) == r2}
        by_s = {0.0: [r for r in rr if r["arm"] == "TWIN"]}
        for s in (0.25, 0.5, 1.0):
            x = [r for r in rr if r["arm"] == f"C2C_r_s{s}"]
            if x:
                by_s[s] = x
        res["crossing"] = C2C.crossing(by_s, ru)
        res["crossing"]["b_t"] = 0.5
        res["crossing"]["s_prime_mean"] = info["s_prime"]["r"]["mean"]
        summ = {s: C2C.arm_summary(v, cat, d, ru, r2) for s, v in by_s.items()}
        res["hull"] = C2C.hull(summ, arms["TWIN"]["pass"] if "TWIN" in arms else 1.0)
        per[t] = res
    out = {"per_task": per, "median_alpha_confirmed_random": med_alpha}
    if per:
        out["verdict"] = C2C.verdict(per, med_alpha if np.isfinite(med_alpha) else 2.0)
    return out


def main() -> None:
    from cfg4 import setup_logging
    setup_logging("analysis")
    rows = load_rows()
    codes = {l["code_sha256"]: l["code"] for l in read_jsonl(LABELS) if l.get("code_sha256")}
    commit = read_json(PRED_DIR / "c2_commit.json")
    screen = read_json(RESULTS_DIR / "screen.json")
    only = sys.argv[1:]
    res: dict[str, Any] = {"n_rows_labelled": len(rows), "n_raw": len(read_jsonl(RAW))}
    if not only or "arms" in only:
        write_json(RESULTS_DIR / "arms.json", arm_tables(rows, codes))
    esc = escape(rows, screen)
    write_json(RESULTS_DIR / "escape.json", esc)
    if not only or "c2a" in only:
        write_json(RESULTS_DIR / "c2a.json", c2a(rows, commit))
    if not only or "decomp" in only:
        write_json(RESULTS_DIR / "decomposition.json", decomposition(rows))
    if not only or "c2c" in only:
        write_json(RESULTS_DIR / "c2c.json", c2c(rows, commit, esc))
    for name in ("c2b", "c3b", "geometry", "novelty", "explore"):
        if (not only or name in only) and (ROOT / "analysis" / f"{name}.py").exists():
            mod = __import__(name)
            write_json(RESULTS_DIR / f"{name}.json", mod.run(rows, commit, esc))
    write_json(RESULTS_DIR / "analysis_run.json", res)


if __name__ == "__main__":
    main()
