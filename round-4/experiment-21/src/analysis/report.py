#!/usr/bin/env python3
"""S9 analyses on top of the committed core (analysis/core.py): A1 C_T, A2 C_PN, A3 x_s contrast + placebo, A4
phrasing (PPI slopes, theta sweep), A5 paired phrasing, A6 the 1a-c table, A7 thinking on, A8 FP8 cross-check,
engine check + determinism checks, optional arms (ii)-(iv), and A10 figures. Writes results/c1seed.json,
results/phrasing.json, results/thinking.json, results/engine_check.json, results/fp8_crosscheck.json,
results/determinism.json, results/table_1ac.json and figures/.
"""

from __future__ import annotations

import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / "src", ROOT / "analysis"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import core  # noqa: E402
from cfg import DATA_DIR, FIG_DIR, RESULTS_DIR, read_json, read_jsonl, utc_now, wilson_ci, write_json  # noqa: E402
from cfg4 import (DEFAULT4, MINP_T, PN_ALPHAS, PN_SEEDS, PN_TEMPS, TEMPS, TOPK_K, TOPK_T, TPN_ALPHA, TPN_T,  # noqa: E402
                  cond_nopn, cond_pn, fmt_t)

TASKS = ("T2", "T03", "T1")
TEMP_ARMS = [cond_nopn(t) for t in TEMPS]
TOPK_ARM = f"TOPK{TOPK_K}_T{fmt_t(TOPK_T)}"
MINP_ARM = f"MINP_T{fmt_t(MINP_T)}"
THINK_ARMS = [f"THINK_T{fmt_t(t)}" for t in TEMPS]
SEEDS = core.seeds_of()
COUPLING = {"off": "inverse-CDF CRN (PCG64 uniforms, vocabulary order)",
            "on": "vLLM exponential race = Gumbel-max (per-request seed)",
            "gumbel": "HF exponential race = Gumbel-max (per-row CUDA generator)"}


# ------------------------------------------------------------------------------------------------ data
def load_rows() -> list[dict[str, Any]]:
    labs = {r["key"]: r for r in read_jsonl(DATA_DIR / "labels.jsonl")}
    out = []
    for r in read_jsonl(DATA_DIR / "samples_raw.jsonl"):
        key = f"{r['task']}|{r['template']}|{r['arm']}|{r['sample_id']}"
        l = labs.get(key)
        out.append({**r, "key": key, "label": l["label"] if l else None, "passed": bool(l and l["passed"]),
                    "labelled": l is not None, "code": l.get("code") if l else None,
                    "labeller_source": l.get("labeller_source") if l else None,
                    "runtime_label": l.get("runtime_label") if l else None,
                    "ast_label": l.get("ast_label") if l else None})
    return out


def rows_for(rows: list[dict[str, Any]], task: str, arm: str) -> list[dict[str, Any]]:
    return [r for r in rows if r["task"] == task and r["arm"] == arm]


def comp(rows: list[dict[str, Any]], correct: bool = False) -> dict[str, int]:
    c = Counter(core.label_value(r, "correct_only" if correct else "primary") for r in rows)
    c.pop(None, None)
    return dict(c.most_common())


def cp_rate(k: int, n: int) -> dict[str, Any]:
    lo, hi = core.clopper_pearson(k, n)
    return {"k": k, "n": n, "rate": k / n if n else None, "cp95": [lo, hi]}


# ------------------------------------------------------------------------------------------------ A1-A3
def a1_ct(idx: dict, task: str, arms: list[str], seeds: list[str] = SEEDS) -> dict[str, Any]:
    out = {}
    for mode in ("primary", "correct_only", "invalid_as_label"):
        c = core.count_changed(idx, task, seeds, arms, mode)
        out[mode] = {"C_T": c["C"], "n_countable": c["n_countable"], "cp95_rate": cp_rate(c["C"], c["n_countable"]),
                     "changed_seeds": sorted(s for s, v in c["per_seed"].items() if v)}
    return out


def pairwise_t(idx: dict, task: str, arms: list[str]) -> dict[str, Any]:
    out = {}
    for a, b in __import__("itertools").combinations(arms, 2):
        c = core.count_changed(idx, task, SEEDS, [a, b])
        out[f"{a}|{b}"] = {"changed": c["C"], "n": c["n_countable"]}
    return out


def a2_cpn(idx: dict, task: str, prefix: str = "") -> dict[str, Any]:
    out = {}
    for a in PN_ALPHAS:
        for t in PN_TEMPS:
            arms = [prefix + cond_pn(d, a, t) for d in PN_SEEDS]
            if not any((task, s, arms[0]) in idx for s in SEEDS):
                continue
            r = core.c_pn(idx, task, SEEDS, prefix + cond_nopn(t), arms)
            rc = core.c_pn(idx, task, SEEDS, prefix + cond_nopn(t), arms, mode="correct_only")
            out[f"a{a:.1f}_T{fmt_t(t)}"] = {"C_PN": r["C_PN"], "min": r["min"], "median": r["median"], "max": r["max"],
                                            "subset_sums": r["subset_sums"], "uncountable": r["uncountable_seed_subsets"],
                                            "C_PN_correct_only": rc["C_PN"], "per_seed_mean": r["per_seed_mean"]}
    return out


def per_direction(rows: list[dict[str, Any]], task: str, prefix: str = "") -> dict[str, Any]:
    out = {}
    de = DEFAULT4[task]
    for t in PN_TEMPS:
        base = rows_for(rows, task, prefix + cond_nopn(t))
        bv = [core.label_value(r) for r in base]
        bv = [x for x in bv if x]
        b_off = sum(x != de for x in bv) / max(len(bv), 1)
        b_pass = sum(r["passed"] for r in base) / max(len(base), 1)
        for a in PN_ALPHAS:
            for d in PN_SEEDS:
                rr = rows_for(rows, task, prefix + cond_pn(d, a, t))
                if not rr:
                    continue
                v = [core.label_value(r) for r in rr]
                v = [x for x in v if x]
                off = sum(x != de for x in v) / max(len(v), 1)
                pr = sum(r["passed"] for r in rr) / max(len(rr), 1)
                out[f"D{d}_a{a:.1f}_T{fmt_t(t)}"] = {
                    "N": len(rr), "n_valid": len(v), "share_off": off, "nopn_share_off": b_off,
                    "excess": off - b_off, "pass_rate": pr, "pass_ratio": pr / max(b_pass, 1e-9),
                    "escape_descriptive": (off - b_off >= 0.20 and pr / max(b_pass, 1e-9) >= 0.85),
                    "landing": dict(Counter(x for x in v if x != de).most_common()),
                    "mean_disp_S_b23": float(np.mean([r.get("disp_S_mean_b23") or 0 for r in rr])),
                    "mean_disp_S_b35": float(np.mean([r.get("disp_S_mean_b35") or 0 for r in rr])),
                    "mean_disp_R_b35": float(np.mean([r.get("disp_R_b35") or 0 for r in rr]))}
    return out


def a3_contrast(idx: dict, tasks: tuple[str, ...] = ("T2", "T03"), prefix: str = "", n_draws: int = 100_000,
                placebo_reps: int = 200) -> dict[str, Any]:
    xs_by_task = {}
    for task in TASKS:
        ct = core.count_changed(idx, task, SEEDS, [prefix + a for a in TEMP_ARMS])["per_seed"]
        pm = core.c_pn(idx, task, SEEDS, prefix + "NOPN_T1.0",
                       [prefix + cond_pn(d, 1.0, 1.0) for d in PN_SEEDS])["per_seed_mean"]
        xs_by_task[task] = core.x_contrast(ct, pm)
    out: dict[str, Any] = {"per_task": {}}
    for task, x in xs_by_task.items():
        v = list(x.values())
        out["per_task"][task] = {"n": len(v), "mean_x": float(np.mean(v)) if v else None,
                                 "boot95": core.seed_bootstrap_ci(v), "sign_flip": core.sign_flip_p(v, n_draws=20_000)}
    pooled = [v for t in tasks for v in xs_by_task[t].values()]
    out["pooled"] = {"tasks": list(tasks), "n": len(pooled), "mean_x": float(np.mean(pooled)) if pooled else float("nan"),
                     "boot95": core.seed_bootstrap_ci(pooled), "sign_flip": core.sign_flip_p(pooled, n_draws=n_draws)}
    # placebo: permute the 10 condition labels within each seed
    rng = np.random.default_rng(123)
    arms10 = [prefix + a for a in TEMP_ARMS] + [prefix + cond_pn(d, 1.0, 1.0) for d in PN_SEEDS]
    ps, pmeans = [], []
    for rep in range(placebo_reps):
        fake: dict = {}
        for task in tasks:
            for s in SEEDS:
                vals = [idx.get((task, s, a)) for a in arms10]
                perm = rng.permutation(len(vals))
                for a, j in zip(arms10, perm):
                    if vals[j] is not None:
                        fake[(task, s, a)] = vals[j]
        xx = []
        for task in tasks:
            ct = core.count_changed(fake, task, SEEDS, [prefix + a for a in TEMP_ARMS])["per_seed"]
            pm = core.c_pn(fake, task, SEEDS, prefix + "NOPN_T1.0", arms10[4:])["per_seed_mean"]
            xx += list(core.x_contrast(ct, pm).values())
        ps.append(core.sign_flip_p(xx, n_draws=5_000, seed=rep)["p"])
        pmeans.append(float(np.mean(xx)) if xx else float("nan"))
    ps_a = np.array([p for p in ps if np.isfinite(p)])
    pm_a = np.array([m for m in pmeans if np.isfinite(m)])
    obs_m = out["pooled"]["mean_x"]
    out["within_seed_permutation_test"] = {
        "reps": len(pm_a), "observed_mean_x": obs_m, "placebo_mean_x_q95": float(np.quantile(pm_a, 0.95)) if len(pm_a) else None,
        "placebo_mean_x_max": float(pm_a.max()) if len(pm_a) else None,
        "p": float((1 + (pm_a >= obs_m - 1e-12).sum()) / (1 + len(pm_a))) if len(pm_a) else None,
        "note": "assumption-light robustness check of H-CON: condition labels permuted within seed (exchangeability "
                "null); not the committed test"}
    out["placebo_condition_permutation"] = {"reps": placebo_reps, "share_p_lt_0.05": float((ps_a < 0.05).mean()) if
                                            len(ps_a) else None, "median_p": float(np.median(ps_a)) if len(ps_a) else None,
                                            "note": "condition labels shuffled within seed; p should be ~uniform"}
    return out


# ------------------------------------------------------------------------------------------------ A4 / A5 phrasing
def phrasing(rows: list[dict[str, Any]], idx: dict) -> dict[str, Any]:
    res: dict[str, Any] = {"thetas": list(core.THETAS), "per_task": {}, "pooled": {}}
    boots: dict[float, list[np.ndarray]] = defaultdict(list)
    slopes: dict[float, list[float]] = defaultdict(list)
    for task in TASKS:
        cells = {}
        for t, arm in zip(TEMPS, TEMP_ARMS):
            seeds, labs, sh = [], [], []
            for s in SEEDS:
                r = idx.get((task, s, arm))
                lab = core.label_value(r)
                shg = core.shingles(r.get("code")) if (r and lab) else None
                if lab and shg is not None:
                    seeds.append(s)
                    labs.append(lab)
                    sh.append(shg)
            cells[t] = {"seeds": seeds, "labels": labs, "sh": sh}
        tres = {}
        if sum(len(cells[t]["seeds"]) for t in TEMPS) == 0:
            for th in core.THETAS:
                tres[str(th)] = {"slope": float("nan"), "ci95": (float("nan"), float("nan")), "ppi_by_T": {}}
                boots[th].append(np.array([float("nan")]))
                slopes[th].append(float("nan"))
            res["per_task"][task] = {"theta": tres, "n_programs_by_T": {str(t): 0 for t in TEMPS}}
            continue
        for th in core.THETAS:
            b = core.ppi_slope_bootstrap(cells, th, reps=2000, seed=11)
            bc = core.ppi_slope_bootstrap(cells, th, reps=300, seed=12, linkage_kind="complete")
            tres[str(th)] = {"slope": b["slope"], "ci95": b["ci95"], "ppi_by_T": b["ppi_by_T"],
                             "complete_linkage": {"slope": bc["slope"], "ci95": bc["ci95"], "ppi_by_T": bc["ppi_by_T"]}}
            boots[th].append(b["boot"])
            slopes[th].append(b["slope"])
        res["per_task"][task] = {"theta": tres, "n_programs_by_T": {str(t): len(cells[t]["seeds"]) for t in TEMPS}}
    for th in core.THETAS:
        m = min(len(x) for x in boots[th])
        pooled_boot = np.mean([x[:m] for x in boots[th]], axis=0)
        res["pooled"][str(th)] = {"slope": float(np.mean(slopes[th])),
                                  "ci95": (float(np.quantile(pooled_boot, 0.025)), float(np.quantile(pooled_boot, 0.975)))}
    return res


def paired_phrasing(rows: list[dict[str, Any]], idx: dict) -> dict[str, Any]:
    out: dict[str, Any] = {}
    shc: dict[str, Any] = {}

    def sh(r):
        if r is None or not r.get("code"):
            return None
        k = r["key"]
        if k not in shc:
            shc[k] = core.shingles(r["code"])
        return shc[k]
    for task in TASKS:
        tp: dict[str, Any] = {}
        pairs = [(a, b) for i, a in enumerate(TEMP_ARMS) for b in TEMP_ARMS[i + 1:]]
        for t in PN_TEMPS:
            for d in PN_SEEDS:
                pairs.append((cond_nopn(t), cond_pn(d, 1.0, t)))
        agg: dict[str, dict[str, list]] = defaultdict(lambda: {"same_ident": [], "same_j": [], "chg_ident": [],
                                                               "chg_j": []})
        for a, b in pairs:
            kind = "T_pair" if b.startswith("NOPN") else f"NOPN_vs_PN_a1_T{a[-3:]}"
            for s in SEEDS:
                ra, rb = idx.get((task, s, a)), idx.get((task, s, b))
                la, lb = core.label_value(ra), core.label_value(rb)
                if not (la and lb):
                    continue
                ident = ra.get("token_ids") == rb.get("token_ids")
                j = core.jaccard(sh(ra), sh(rb))
                key = "same" if la == lb else "chg"
                agg[kind][f"{key}_ident"].append(ident)
                if np.isfinite(j):
                    agg[kind][f"{key}_j"].append(j)
        for kind, v in agg.items():
            tp[kind] = {"n_same_idea": len(v["same_ident"]), "byte_identical_rate_same_idea":
                        float(np.mean(v["same_ident"])) if v["same_ident"] else None,
                        "mean_jaccard_same_idea": float(np.mean(v["same_j"])) if v["same_j"] else None,
                        "n_changed_idea": len(v["chg_ident"]),
                        "mean_jaccard_changed_idea": float(np.mean(v["chg_j"])) if v["chg_j"] else None}
        out[task] = tp
    return out


# ------------------------------------------------------------------------------------------------ A6 table
def cell_hill(rows_cell: list[dict[str, Any]]) -> dict[str, Any]:
    labs = [core.label_value(r, "correct_only") for r in rows_cell]
    labs = [l for l in labs if l]
    return {"hill1_correct": core.hill1(labs) if labs else None, "n_correct": len(labs),
            "flag_fewer_than_20_correct": len(labs) < 20}


def table_1ac(rows: list[dict[str, Any]], idx: dict, cts: dict, cpns: dict) -> list[dict[str, Any]]:
    out = []
    for task in TASKS:
        base07 = {s: idx.get((task, s, "NOPN_T0.7")) for s in SEEDS}
        conds = TEMP_ARMS + [TOPK_ARM, MINP_ARM] + [f"PN_a{a:.1f}_T{fmt_t(t)}" for a in PN_ALPHAS for t in PN_TEMPS] + \
            ["GB_" + a for a in TEMP_ARMS] + ["GB_PN_a1.0_T1.0"]
        for c in conds:
            if c.startswith("PN_a") or c.startswith("GB_PN_a"):
                pre = "GB_" if c.startswith("GB_") else ""
                a = float(c.split("_a")[1].split("_")[0])
                t = float(c.split("_T")[1])
                arms = [pre + cond_pn(d, a, t) for d in PN_SEEDS]
                rr = [r for r in rows if r["task"] == task and r["arm"] in arms]
                if not rr:
                    continue
                opts = {s: [core.label_value(idx.get((task, s, arm)), "correct_only") for arm in arms
                            if idx.get((task, s, arm))] for s in SEEDS}
                rh = core.rarefied_hill1(opts)
                hill = {"hill1_correct_rarefied20": rh["hill1_mean"], "hill1_q05": rh["hill1_q05"],
                        "hill1_q95": rh["hill1_q95"], "mean_counted_depth": rh["mean_counted_depth"]}
                key = f"a{a:.1f}_T{fmt_t(t)}"
                changed = (cpns.get(task, {}).get(key, {}) if not pre else cpns.get("GB_" + task, {}).get(key, {}))
                ch = changed.get("C_PN")
            else:
                rr = rows_for(rows, task, c)
                if not rr:
                    continue
                hill = cell_hill(rr)
                ch = None
            # phrasing clusters (single linkage) within (cell, idea)
            labs, shs, jp = [], [], []
            for r in rr:
                l = core.label_value(r)
                s = core.shingles(r.get("code")) if l else None
                if l and s is not None:
                    labs.append(l)
                    shs.append(s)
                b = base07.get(f"{r['template']}|{int(r['sample_id'])}")
                if b is not None and l and core.label_value(b) and b.get("code") and r.get("code"):
                    jp.append(core.jaccard(core.shingles(r["code"]), core.shingles(b["code"])))
            J = core.jaccard_matrix(shs) if shs else np.zeros((0, 0))
            cl = {str(th): core.ppi(labs, J, th) for th in core.THETAS}
            rare = None
            if (c.startswith("PN_a") or c.startswith("GB_PN_a")) and shs:
                # committed rarefaction: one program per seed (a random direction), 1,000 draws, depth <= 20
                seeds_of_prog = []
                for r in rr:
                    l = core.label_value(r)
                    if l and core.shingles(r.get("code")) is not None:
                        seeds_of_prog.append(f"{r['template']}|{int(r['sample_id'])}")
                by_seed: dict[str, list[int]] = defaultdict(list)
                for i, sd in enumerate(seeds_of_prog):
                    by_seed[sd].append(i)
                rng = np.random.default_rng(20)
                acc: dict[str, list[float]] = {str(th): [] for th in core.THETAS}
                for _ in range(1000):
                    sel = [v[int(rng.integers(0, len(v)))] for v in by_seed.values()]
                    sl = [labs[i] for i in sel]
                    sj = J[np.ix_(sel, sel)]
                    for th in core.THETAS:
                        acc[str(th)].append(core.ppi(sl, sj, th)["ppi"])
                rare = {k: float(np.mean(v)) for k, v in acc.items()}
            out.append({"task": task, "condition": c, "N": len(rr),
                        "pass_rate": sum(r["passed"] for r in rr) / max(len(rr), 1),
                        "attempted": comp(rr), "correct": comp(rr, correct=True), **hill,
                        "clusters": {k: v["clusters"] for k, v in cl.items()},
                        "ppi": {k: v["ppi"] for k, v in cl.items()},
                        "ppi_rarefied20": rare,
                        "changed_seed_count": ch if ch is not None else (cts.get(task) if c in TEMP_ARMS else None),
                        "paired_jaccard_to_NOPN_T0.7": float(np.nanmean(jp)) if jp else None,
                        "coupling": COUPLING["gumbel"] if c.startswith("GB_") else COUPLING["off"]})
    return out


# ------------------------------------------------------------------------------------------------ A7 thinking
def thinking(rows: list[dict[str, Any]], task: str = "T2") -> dict[str, Any]:
    raw = read_jsonl(DATA_DIR / "raw_thinking.jsonl")
    if not raw:
        return {"available": False}
    lab = {r["key"]: r for r in rows if r["task"] == task and r["arm"].startswith("THINK")}
    by_arm: dict[str, list] = defaultdict(list)
    for r in raw:
        if r["task"] != task:
            continue
        key = f"{task}|{r['template']}|{r['arm']}|{r['sample_id']}"
        L = lab.get(key, {})
        by_arm[r["arm"]].append({**r, "label": L.get("label"), "passed": L.get("passed", False), "key": key,
                                 "code": L.get("code")})
    if not by_arm:
        return {"available": False, "task": task}
    out: dict[str, Any] = {"available": True, "task": task, "coupling": COUPLING["on"], "per_T": {}}
    for arm in THINK_ARMS + ["THINK_REP_T0.7"]:
        rr = by_arm.get(arm, [])
        if not rr:
            continue
        n = len(rr)
        k = sum(r["completed"] for r in rr)
        nt = [r["n_think_tokens"] for r in rr]
        out["per_T"][arm] = {"n": n, "completed": k, "completion_rate": k / n, "wilson95": wilson_ci(k, n),
                             "think_tokens_median": float(np.median(nt)), "think_tokens_q25": float(np.quantile(nt, .25)),
                             "think_tokens_q75": float(np.quantile(nt, .75)), "think_tokens_max": int(max(nt)),
                             "capped": sum(not r["closed"] for r in rr),
                             "final_label_completed": dict(Counter(r["label"] for r in rr if r["completed"]).most_common()),
                             "final_label_all_incl_forced": dict(Counter(r["label"] for r in rr).most_common()),
                             "pass_rate_completed": (sum(r["passed"] for r in rr if r["completed"]) / max(k, 1)),
                             "first_approach": dict(Counter(r["first_approach"] for r in rr).most_common())}
    idx = core.index_rows([r for arm in THINK_ARMS for r in by_arm.get(arm, [])])
    comp_seeds = [s for s in SEEDS if all((idx.get((task, s, a)) or {}).get("completed") for a in THINK_ARMS)]
    ct_c = core.count_changed(idx, task, comp_seeds, THINK_ARMS)
    # all seeds with forced labels: index includes forced traces' labels
    ct_all = core.count_changed(idx, task, SEEDS, THINK_ARMS)
    fa = core.count_changed(idx, task, SEEDS, THINK_ARMS, mode="first_approach")
    out["C_T_completed_all_4"] = {"C_T": ct_c["C"], "n": ct_c["n_countable"], "n_seeds_complete_all_4": len(comp_seeds),
                                  "cp95_rate": cp_rate(ct_c["C"], ct_c["n_countable"]),
                                  "changed_seeds": sorted(s for s, v in ct_c["per_seed"].items() if v)}
    out["C_T_all_seeds_forced_labels"] = {"C_T": ct_all["C"], "n": ct_all["n_countable"]}
    out["C_T_first_approach"] = {"C_T": fa["C"], "n": fa["n_countable"],
                                 "changed_seeds": sorted(s for s, v in fa["per_seed"].items() if v)}
    # repeat (noise floor)
    rep = {f"{r['template']}|{r['sample_id']}": r for r in by_arm.get("THINK_REP_T0.7", [])}
    org = {f"{r['template']}|{r['sample_id']}": r for r in by_arm.get("THINK_T0.7", [])}
    ident, fdiv, agree, changed_rep, fa_agree = [], [], [], 0, []
    for s, r in rep.items():
        o = org.get(s)
        if not o:
            continue
        a, b = o["think_ids"], r["think_ids"]
        d = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), None)
        same = d is None and len(a) == len(b)
        ident.append(same)
        fdiv.append(d if d is not None else (None if same else min(len(a), len(b))))
        la, lb = core.label_value(o), core.label_value(r)
        if la and lb:
            agree.append(la == lb)
            changed_rep += la != lb
        fa_agree.append(o["first_approach"] == r["first_approach"])
    out["repeat_T0.7"] = {"n_pairs": len(ident), "byte_identical_rate": float(np.mean(ident)) if ident else None,
                          "first_divergence_index": fdiv, "label_agreement": float(np.mean(agree)) if agree else None,
                          "repeat_change_count": changed_rep, "first_approach_agreement":
                          float(np.mean(fa_agree)) if fa_agree else None,
                          "note": "the temperature change count is read against this noise floor"}
    return out


# ------------------------------------------------------------------------------------------------ engine check / A8
def engine_check(rows: list[dict[str, Any]]) -> dict[str, Any]:
    scr_lab = read_jsonl(ROOT / "inputs/exp17/data/labels.jsonl")
    scr_raw = {f"{r['task']}|{r['template']}|{r['arm']}|{r['sample_id']}": r
               for r in read_jsonl(ROOT / "inputs/exp17/data/samples_raw_enginecheck_subset.jsonl")}
    out: dict[str, Any] = {"cells": {}}
    ok_all = True
    for task, rseed in (("T03", 9002), ("T2", 9004)):
        for here_arm, scr_arm in (("EC_NEUTRAL_T1.0", "NEUTRAL"), (f"EC_RAND{rseed}_a1.0_T1.0", f"RAND{rseed}_a1.0")):
            here = rows_for(rows, task, here_arm)
            scr = [r for r in scr_lab if r["task"] == task and r["arm"] == scr_arm and int(r["sample_id"]) < 10]
            if not here:
                continue
            key = lambda r: core.label_value(r)  # noqa: E731
            nul = core.template_resampling_null(here, scr, key, reps=2000)
            ident = []
            for r in here:
                s = scr_raw.get(f"{task}|{r['template']}|{scr_arm}|{r['sample_id']}")
                if s:
                    ident.append(s["token_ids"] == r["token_ids"])
            ok = nul["js_bits"] <= nul["null_p95"] + 1e-12
            ok_all &= ok
            out["cells"][f"{task}_{here_arm}"] = {"N_here": len(here), "N_screen": len(scr), "here": comp(here),
                                                  "screen": comp(scr), "pass_here": sum(r["passed"] for r in here) / len(here),
                                                  "pass_screen": sum(bool(r["passed"]) for r in scr) / max(len(scr), 1),
                                                  **nul, "byte_identical_to_screen": f"{sum(ident)}/{len(ident)}",
                                                  "within_null": ok}
    out["verdict"] = "REPRODUCED" if (out["cells"] and ok_all) else ("PRECISION-SENSITIVE" if out["cells"] else "NOT RUN")
    return out


def determinism(rows: list[dict[str, Any]], idx: dict) -> dict[str, Any]:
    out = {}
    for task in TASKS:
        f_same, e_same = [], []
        for s in SEEDS:
            o = idx.get((task, s, "NOPN_T1.0"))
            f = idx.get((task, s, "FILLER_T1.0"))
            e = idx.get((task, s, "EC_NEUTRAL_T1.0"))
            if o and f:
                f_same.append(o["token_ids"] == f["token_ids"])
            if o and e:
                e_same.append(o["token_ids"] == e["token_ids"])
        out[task] = {"filler_repeat_byte_identical": f"{sum(f_same)}/{len(f_same)}",
                     "engine_check_k0_3_vs_NOPN_T1.0_byte_identical": f"{sum(e_same)}/{len(e_same)}"}
    return out


def fp8_crosscheck(rows: list[dict[str, Any]]) -> dict[str, Any]:
    v = rows_for(rows, "T2", "FP8X_T1.0")
    h = rows_for(rows, "T2", "EC_NEUTRAL_T1.0")
    scr = [r for r in read_jsonl(ROOT / "inputs/exp17/data/labels.jsonl") if r["task"] == "T2" and r["arm"] == "NEUTRAL"]
    if not v or not h:
        return {"available": False}
    nul = core.template_resampling_null(v, h, lambda r: core.label_value(r), reps=2000)
    return {"available": True, "vllm_fp8_marlin": {"N": len(v), "composition": comp(v),
                                                  "pass_rate": sum(r["passed"] for r in v) / len(v),
                                                  "mean_tokens": float(np.mean([r["n_tokens"] for r in v]))},
            "hf_fp8_w8a8": {"N": len(h), "composition": comp(h), "pass_rate": sum(r["passed"] for r in h) / len(h),
                            "mean_tokens": float(np.mean([r["n_tokens"] for r in h]))},
            "screen_hf_fp8_w8a8_N100": {"composition": dict(Counter(r["label"] for r in scr).most_common())},
            **nul, "note": "bf16 HF does not fit the 16 GB card: the cross-check compares the two FP8 implementations "
                           "(vLLM weight-only Marlin vs HF W8A8); exp18 bounded FP8 vs bf16 on T2 (JS 0.033 bits, "
                           "null p95 0.068). The cell is near 100% Dijkstra, so this is a weak precision check."}


# ------------------------------------------------------------------------------------------------ optional arms
def optional_arms(rows: list[dict[str, Any]], idx: dict) -> dict[str, Any]:
    out: dict[str, Any] = {}
    gb = {}
    for task in ("T2", "T03"):
        arms = ["GB_" + a for a in TEMP_ARMS]
        if not any((task, s, arms[0]) in idx for s in SEEDS):
            continue
        ct = a1_ct(idx, task, arms)
        cpn = a2_cpn(idx, task, prefix="GB_")
        gb[task] = {"C_T": ct, "C_PN": {k: {kk: vv for kk, vv in v.items() if kk != "per_seed_mean"}
                                        for k, v in cpn.items()},
                    "per_direction": per_direction(rows, task, prefix="GB_")}
    if gb:
        gb["contrast"] = a3_contrast(idx, prefix="GB_", n_draws=100_000, placebo_reps=50)
        gb["coupling"] = COUPLING["gumbel"]
    out["iii_gumbel"] = gb or {"available": False}
    mp = {}
    for task in TASKS:
        rr = rows_for(rows, task, MINP_ARM)
        if not rr:
            continue
        c5 = core.count_changed(idx, task, SEEDS, TEMP_ARMS + [MINP_ARM])
        mp[task] = {"N": len(rr), "composition": comp(rr), "pass_rate": sum(r["passed"] for r in rr) / len(rr),
                    "invalid": sum(core.norm_label(r["label"]) == "invalid" for r in rr), **cell_hill(rr),
                    "C_T_with_minp_cell": c5["C"], "n": c5["n_countable"]}
    out["iv_minp"] = mp or {"available": False}
    tpn = [r for r in rows if r["task"] == "T2" and r["arm"].startswith("TPN_") and "PAD" not in r["arm"]]
    if tpn:
        from lexicon import first_approach
        by = {(r["template"], int(r["sample_id"]), r["arm"]): first_approach(r["text"])[0] for r in tpn}
        base_arm = f"TPN_NOPN_T{fmt_t(TPN_T)}"
        dirs = sorted({r["arm"] for r in tpn if r["arm"] != base_arm})
        res = {}
        for a in dirs:
            moved, n = 0, 0
            for (w, k, arm), fa in by.items():
                if arm != a:
                    continue
                b = by.get((w, k, base_arm))
                n += 1
                moved += (fa != b)
            res[a] = {"moved": moved, "n": n}
        out["ii_thinking_pn"] = {"first_approach_by_arm": {a: dict(Counter(v for (w, k, arm), v in by.items()
                                                                           if arm == a).most_common())
                                                           for a in [base_arm] + dirs},
                                 "moved_vs_no_pn": res,
                                 "expectation_met": any(v["moved"] >= 3 for v in res.values()),
                                 "selection": read_json(RESULTS_DIR / "tpn_direction_selection.json")
                                 if (RESULTS_DIR / "tpn_direction_selection.json").exists() else None,
                                 "causal_mask_check": read_json(RESULTS_DIR / "tpn_causal_mask_check.json")
                                 if (RESULTS_DIR / "tpn_causal_mask_check.json").exists() else None}
    else:
        out["ii_thinking_pn"] = {"available": False}
    return out


def interaction(rows: list[dict[str, Any]], idx: dict, perdir: dict) -> dict[str, Any]:
    out = {}
    for task in TASKS:
        esc = [d for d in PN_SEEDS if perdir[task].get(f"D{d}_a1.0_T1.0", {}).get("escape_descriptive")]
        nopn = core.count_changed(idx, task, SEEDS, ["NOPN_T0.7", "NOPN_T1.0"])
        under = [core.count_changed(idx, task, SEEDS, [cond_pn(d, 1.0, 0.7), cond_pn(d, 1.0, 1.0)]) for d in esc]
        out[task] = {"escaping_directions_a1_T1.0": esc, "nopn_T0.7_vs_T1.0_changed": nopn["C"],
                     "nopn_n": nopn["n_countable"],
                     "pn_T0.7_vs_T1.0_changed_per_escaping_dir": [u["C"] for u in under],
                     "pn_mean_changed": float(np.mean([u["C"] for u in under])) if under else None,
                     "transmission": {f"D{d}": {f"a{a:.1f}": {f"T{fmt_t(t)}": perdir[task].get(
                         f"D{d}_a{a:.1f}_T{fmt_t(t)}", {}).get("share_off") for t in PN_TEMPS} for a in PN_ALPHAS}
                                      for d in PN_SEEDS}}
        out[task]["expectation_met"] = (out[task]["pn_mean_changed"] or 0) > nopn["C"] if esc else None
    return out


# ------------------------------------------------------------------------------------------------ run
def run_analysis() -> dict[str, Any]:
    rows = load_rows()
    n_unl = sum(not r["labelled"] for r in rows)
    logger.info(f"analysis: {len(rows)} rows, {n_unl} unlabelled")
    idx = core.index_rows(rows)
    res: dict[str, Any] = {"utc": utc_now(), "n_rows": len(rows), "n_unlabelled": n_unl, "couplings": COUPLING}
    a1, a1x, a2, pdir, pairs = {}, {}, {}, {}, {}
    for task in TASKS:
        a1[task] = a1_ct(idx, task, TEMP_ARMS)
        a1x[task] = {"with_TOPK10_as_5th": core.count_changed(idx, task, SEEDS, TEMP_ARMS + [TOPK_ARM])["C"],
                     "with_MINP_as_5th": core.count_changed(idx, task, SEEDS, TEMP_ARMS + [MINP_ARM])["C"],
                     "pairwise": pairwise_t(idx, task, TEMP_ARMS)}
        a2[task] = a2_cpn(idx, task)
        pdir[task] = per_direction(rows, task)
    res["A1_C_T_off"] = a1
    res["A1_sensitivities"] = a1x
    res["A2_C_PN"] = {t: {k: {kk: vv for kk, vv in v.items() if kk != "per_seed_mean"} for k, v in a2[t].items()}
                      for t in TASKS}
    res["A2_per_direction"] = pdir
    res["A3_x_contrast"] = a3_contrast(idx)
    th = thinking(rows)
    th_t1 = thinking(rows, "T1")
    if th_t1.get("available"):
        th["T1_optional_i"] = th_t1
    res["A7_thinking_summary"] = {k: v for k, v in th.items() if k.startswith("C_T") or k == "repeat_T0.7"}
    phr = phrasing(rows, idx)
    res["A4_phrasing_pooled"] = phr["pooled"]
    res["interaction"] = interaction(rows, idx, pdir)
    res["optional"] = optional_arms(rows, idx)
    # decision
    ct_cells = {f"{t}_off": a1[t]["primary"]["C_T"] for t in TASKS}
    ct_cells["T2_on"] = th.get("C_T_completed_all_4", {}).get("C_T") if th.get("available") else None
    dec_in = {"C_T": ct_cells, "C_PN_a1_T1": {t: a2[t].get("a1.0_T1.0", {}).get("C_PN", 0) for t in ("T2", "T03")},
              "phr": {th_: {"slope": v["slope"], "ci95": v["ci95"]} for th_, v in phr["pooled"].items()},
              "hcon": {"mean": res["A3_x_contrast"]["pooled"]["mean_x"], "p": res["A3_x_contrast"]["pooled"]["sign_flip"]["p"]},
              "C_T_off": {t: a1[t]["primary"]["C_T"] for t in ("T2", "T03")}}
    res["decision_inputs"] = dec_in
    res["verdict"] = core.decide(dec_in)
    res["holm_entry"] = {"family": "iteration secondary Holm family", "name": "C1-seed",
                         "p": res["A3_x_contrast"]["pooled"]["sign_flip"]["p"]}
    # descriptive expectations
    tab = table_1ac(rows, idx, {t: a1[t]["primary"]["C_T"] for t in TASKS}, a2 | {"GB_" + t: v for t, v in
                    ((t, a2_cpn(idx, t, "GB_")) for t in ("T2", "T03"))})
    by = {(r["task"], r["condition"]): r for r in tab}
    exp = {}
    for task in TASKS:
        tk = by.get((task, TOPK_ARM), {})
        pn07 = by.get((task, "PN_a1.0_T0.7"), {})
        exp[task] = {"TOPK10_hill1_le_1.10": (tk.get("hill1_correct") is not None and tk["hill1_correct"] <= 1.10),
                     "TOPK10_hill1": tk.get("hill1_correct"),
                     "PN_a1_T0.7_hill1_rarefied": pn07.get("hill1_correct_rarefied20"),
                     "PN_hill1_gt_TOPK10": (pn07.get("hill1_correct_rarefied20") or 0) > (tk.get("hill1_correct") or 0),
                     "PN_landing_a1_T1.0": Counter(l for d in PN_SEEDS for l, c in pdir[task].get(
                         f"D{d}_a1.0_T1.0", {}).get("landing", {}).items() for _ in range(c)).most_common(3)}
    res["descriptive_expectations"] = exp
    ec = engine_check(rows)
    det = determinism(rows, idx)
    fp8 = fp8_crosscheck(rows)
    res["engine_check_verdict"] = ec["verdict"]
    res["determinism"] = det
    write_json(RESULTS_DIR / "c1seed.json", res)
    write_json(RESULTS_DIR / "phrasing.json", {**phr, "A5_paired": paired_phrasing(rows, idx)})
    write_json(RESULTS_DIR / "thinking.json", th)
    write_json(RESULTS_DIR / "engine_check.json", ec)
    write_json(RESULTS_DIR / "determinism.json", det)
    write_json(RESULTS_DIR / "fp8_crosscheck.json", fp8)
    write_json(RESULTS_DIR / "table_1ac.json", tab)
    try:
        from figures import make_figures
        make_figures(rows, idx, res, phr, th, tab)
    except Exception as e:  # noqa: BLE001 - figures never block the numbers
        logger.exception(f"figures failed: {e}")
    logger.info(f"verdict: {res['verdict']}")
    return res
