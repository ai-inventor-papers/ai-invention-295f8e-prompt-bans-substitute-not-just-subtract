#!/usr/bin/env python3
"""Analysis of iteration 6 (plan STEPS 5-8): every headline from data/samples_raw.jsonl + data/labels.jsonl.

  engine   engine check (TWIN T03/T2 vs exp27 per-slot labels) + U-test summary
  stageA   Stage A exchange: transfer, recovery, slot IIA, pass ratio, compositions, exact McNemar (Holm), verdicts
  st       ST noise-site grid: per-cell table, Firth indicator model at matched downstream displacement, profile CI,
           cluster bootstrap, MH OR in log D_R quintiles, shuffled-site placebo, paired site flips, ST x Stage A
           concordance, RULE verdict
  svt      state vs token: S3 vs DMD paired flips, exact McNemar per task and alpha
  top5     top-five plan push on T1: landing compositions, geometry in actual activation coordinates (PCA plane of
           the forced-prompt centroids) and geodesic k-NN MDS, landing-position test against a random-survivor null
usage: .venv/bin/python src/analysis6.py [engine,stageA,st,svt,top5]
"""

from __future__ import annotations

import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg import RESULTS_DIR, ROOT, read_json, read_jsonl, setup_logging, utc_now, write_json
from cfg6 import (D_OFFSET, DEFAULT6, LABELS, N30, N50, PREFILL_SITES, ROUTE_CLASS, SAMPLES, SLOT_MAP, ST_TASKS,
                  TASKS6, Y6)
import stats6 as S

BAD = ("other", "invalid")
A_ARMS = ("BAN", "X_0-11", "X_12-23", "X_24-35", "X_0-35", "COND", "RPOS", "MR_0-35", "MR_12-23", "PLACEBO")


# ------------------------------------------------------------------------------------------------ data
def load_rows(include_code: bool = False) -> list[dict[str, Any]]:
    labs = {r["sample_id"]: r for r in read_jsonl(LABELS)}
    rows = []
    for r in read_jsonl(SAMPLES):
        lab = labs.get(r["sample_id"])
        if lab is None:
            continue
        d = {k: r.get(k) for k in ("task", "arm", "cell", "band", "source", "site", "alpha", "template", "slot",
                                   "slot_index", "dir_seed", "dmd_T", "realised", "s3", "n_new_tokens",
                                   "finish_reason", "utc", "prompt_kind", "sample_id", "batch_B")}
        d.update(label=lab["label"], passed=bool(lab.get("passed")), valid=bool(lab.get("valid")),
                 labeller_source=lab.get("labeller_source"), code_sha256=lab.get("code_sha256"))
        if include_code:
            d["code"] = lab.get("code")
        rows.append(d)
    return rows


def cell(rows: list[dict[str, Any]], task: str, arm: str, slots: tuple[int, ...] | None = None) -> dict[int, dict]:
    return {r["slot_index"]: r for r in rows if r["task"] == task and r["arm"] == arm and
            (slots is None or r["slot_index"] in slots)}


def comp(c: dict[int, dict], correct: bool) -> dict[str, int]:
    return dict(Counter(r["label"] for r in c.values() if (r["passed"] if correct else r["valid"])).most_common())


def corr_off(r: dict[str, Any], D: str) -> bool:
    return bool(r["passed"] and r["label"] not in (D,) + BAD)


# ------------------------------------------------------------------------------------------------ engine check
def engine_check(rows: list[dict[str, Any]]) -> dict[str, Any]:
    e27 = {}
    for r in read_jsonl(ROOT / "inputs_extra" / "exp27" / "data" / "labels.jsonl"):
        if r.get("arm") == "TWIN":
            e27[(r["task"], r["template"], int(r["slot"]))] = r
    out: dict[str, Any] = {}
    for t in ("T03", "T2", "T10", "T05", "T1"):
        tw = cell(rows, t, "TWIN")
        pairs = [(r, e27[(t, r["template"], int(r["slot"]))]) for r in tw.values()
                 if (t, r["template"], int(r["slot"])) in e27]
        if not pairs:
            continue
        agree = sum(a["label"] == b["label"] for a, b in pairs)
        out[t] = {"n_pairs": len(pairs), "label_agreement": agree / len(pairs),
                  "byte_identical_code": sum((a.get("code_sha256") or 1) == (b.get("code_sha256") or 2)
                                             for a, b in pairs),
                  "this_twin_comp": comp(tw, False),
                  "exp27_twin_comp": dict(Counter(b["label"] for _, b in pairs)),
                  "decisive": t in ("T03", "T2")}
    dec = [v["label_agreement"] for k, v in out.items() if v["decisive"]]
    out["verdict"] = ("ENGINE AGREES (>= 0.95)" if dec and min(dec) >= 0.95 else
                      "KERNEL SENSITIVITY: below 0.95; every contrast is computed within this engine")
    ut = RESULTS_DIR / "unit_tests_gpu.json"
    if ut.exists():
        out["unit_tests"] = read_json(ut)
    utl = read_jsonl(ROOT / "data" / "labels_unit_tests_raw.jsonl")
    if utl:
        lab = {(r["task"], r["arm"], r["template"], r["slot"]): r["label"] for r in utl}
        x = [(k, lab.get((k[0], "UT_SPLICE", k[2], k[3]))) for k in lab if k[1] == "UT_X0-35"]
        out.setdefault("unit_tests", {})["U3_label_equality"] = {
            "n": len(x), "equal": sum(lab[k] == v for k, v in x if v is not None)}
    write_json(RESULTS_DIR / "engine_check.json", out)
    return out


# ------------------------------------------------------------------------------------------------ Stage A
def stage_a(rows: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {"tasks": {}}
    fam: dict[str, dict[str, float]] = defaultdict(dict)
    for t in TASKS6:
        Y, D = Y6[t], DEFAULT6[t]
        tw30 = cell(rows, t, "TWIN", N30)
        tw50 = cell(rows, t, "TWIN")
        ban = cell(rows, t, "BAN")
        if not tw30:
            continue
        nt = len(tw30)
        y_tw = sum(r["label"] == Y for r in tw30.values()) / nt
        off_tw = sum(r["label"] not in (D, "invalid") for r in tw30.values()) / nt
        pass_tw = sum(r["passed"] for r in tw30.values()) / nt
        y_ban = (sum(r["label"] == Y for r in ban.values()) / len(ban)) if ban else None
        off_ban = (sum(r["label"] not in (D, "invalid") for r in ban.values()) / len(ban)) if ban else None
        tres: dict[str, Any] = {"Y": Y, "default": D, "route_class_iter2_3": ROUTE_CLASS[t],
                                "TWIN": {"n": nt, "n50": len(tw50), "Y_share": y_tw, "off_default": off_tw,
                                         "pass": pass_tw, "correct_comp": comp(tw30, True),
                                         "attempted_comp": comp(tw30, False), "Y_share_N50":
                                             (sum(r["label"] == Y for r in tw50.values()) / len(tw50)) if tw50 else None},
                                "cells": {}}
        mr = cell(rows, t, "MR_0-35")
        for arm in A_ARMS:
            c = cell(rows, t, arm)
            if not c:
                continue
            n = len(c)
            kY = sum(r["label"] == Y for r in c.values())
            koff = sum(r["label"] not in (D, "invalid") for r in c.values())
            kp = sum(r["passed"] for r in c.values())
            sl = [s for s in c if s in tw30]
            b = sum(c[s]["label"] == Y and tw30[s]["label"] != Y for s in sl)
            cc = sum(c[s]["label"] != Y and tw30[s]["label"] == Y for s in sl)
            transfer = kY / n - y_tw
            den = (y_ban - y_tw) if y_ban is not None else None
            iia_sl = [s for s in c if s in ban]
            res = {"n": n, "Y_share": kY / n, "Y_ci95_cp": S.clopper_pearson(kY, n), "Y_ci95_wilson": S.wilson(kY, n),
                   "transfer": transfer, "transfer_upper95": S.clopper_pearson(kY, n)[1] - y_tw,
                   "off_default": koff / n, "off_default_transfer": koff / n - off_tw,
                   "pass": kp / n, "pass_ratio": (kp / n) / pass_tw if pass_tw else None,
                   "recovery": (transfer / den) if (den is not None and den >= 0.3) else None,
                   "recovery_den": den,
                   "slot_IIA": (sum(c[s]["label"] == ban[s]["label"] for s in iia_sl) / len(iia_sl)) if iia_sl else None,
                   "mcnemar_vs_twin": {"b_Y_only_cell": b, "c_Y_only_twin": cc, "p": S.mcnemar_exact(b, cc)},
                   "correct_comp": comp(c, True), "attempted_comp": comp(c, False),
                   "n_length_truncated": sum(r["finish_reason"] == "length" for r in c.values())}
            if arm == "X_0-35" and mr:
                sl2 = [s for s in c if s in mr]
                b2 = sum(c[s]["label"] == Y and mr[s]["label"] != Y for s in sl2)
                c2 = sum(c[s]["label"] != Y and mr[s]["label"] == Y for s in sl2)
                res["mcnemar_vs_MR_0-35"] = {"b_X_only": b2, "c_MR_only": c2, "p": S.mcnemar_exact(b2, c2),
                                            "n_pairs": len(sl2)}
                fam["X_0-35_vs_MR_0-35"][t] = res["mcnemar_vs_MR_0-35"]["p"]
            fam[f"{arm}_vs_TWIN"][t] = res["mcnemar_vs_twin"]["p"]
            tres["cells"][arm] = res
        tres["BAN_Y_share"] = y_ban
        tres["BAN_off_default"] = off_ban
        out["tasks"][t] = tres
    # Holm within each family (across tasks)
    for f, ps in fam.items():
        adj = S.holm(ps)
        for t, p in adj.items():
            key = f.replace("_vs_TWIN", "")
            if f == "X_0-35_vs_MR_0-35":
                out["tasks"][t]["cells"]["X_0-35"]["mcnemar_vs_MR_0-35"]["p_holm"] = p
            elif key in out["tasks"][t]["cells"]:
                out["tasks"][t]["cells"][key]["mcnemar_vs_twin"]["p_holm"] = p
    # verdicts (committed rules)
    T = out["tasks"]

    def g(t: str, arm: str, k: str) -> Any:
        return T.get(t, {}).get("cells", {}).get(arm, {}).get(k)
    prompt_hits = [t for t in ("T2", "T03", "T10") if g(t, "X_0-35", "transfer") is not None and
                   g(t, "X_0-35", "transfer") >= 0.5 and (g(t, "X_0-35", "pass_ratio") or 0) >= 0.8]
    direct_low = {t: g(t, "X_0-35", "transfer") for t in ("T05", "T06")}
    p1 = len(prompt_hits) >= 2 and all(v is not None and v <= 0.2 for v in direct_low.values())
    out["P1"] = {"prompt_route_tasks_transferring": prompt_hits, "n_needed": 2,
                 "T05_T06_transfer": direct_low,
                 "T05_T06_upper95": {t: g(t, "X_0-35", "transfer_upper95") for t in ("T05", "T06")},
                 "verdict": "SUPPORTED" if p1 else "NOT SUPPORTED"}
    out["route_check"] = {
        "COND_T05_T06_ge_0.5": {t: g(t, "COND", "transfer") for t in ("T05", "T06")},
        "COND_T2_le_0.2": g("T2", "COND", "transfer"),
        "RPOS_le_0.2": {t: g(t, "RPOS", "transfer") for t in TASKS6},
        "verdict_COND": bool(all((g(t, "COND", "transfer") or 0) >= 0.5 for t in ("T05", "T06")) and
                             (g("T2", "COND", "transfer") is not None and g("T2", "COND", "transfer") <= 0.2)),
        "verdict_RPOS": bool(all(v is not None and v <= 0.2 for v in
                                 [g(t, "RPOS", "transfer") for t in TASKS6 if g(t, "RPOS", "transfer") is not None]))}
    out["placebo"] = {t: g(t, "PLACEBO", "transfer") for t in ("T2", "T03", "T10")}
    out["placebo_verdict"] = bool(all(v is not None and abs(v) <= 0.1 for v in out["placebo"].values()))
    out["MR"] = {t: T[t]["cells"]["X_0-35"].get("mcnemar_vs_MR_0-35") for t in ("T2", "T03", "T10")
                 if t in T and "X_0-35" in T[t]["cells"]}
    out["MR_verdict"] = {t: bool(v and v["b_X_only"] > v["c_MR_only"] and v["p"] < 0.05) for t, v in out["MR"].items()
                         if t in prompt_hits}
    # U6: COND on T05 against exp16 arm d (fraction of the full ban effect)
    try:
        r16 = read_json(ROOT / "inputs_extra" / "exp16" / "results" / "route.json")["route"]["per_task"]
        out["U6_COND_vs_exp16_arm_d"] = {t: {"this_recovery": g(t, "COND", "recovery"),
                                             "this_off_default_transfer": g(t, "COND", "off_default_transfer"),
                                             "exp16_F_direct": (r16.get(t) or {}).get("F_direct"),
                                             "exp16_F_prompt": (r16.get(t) or {}).get("F_prompt")}
                                         for t in ("T05", "T06", "T03", "T10")}
    except (FileNotFoundError, KeyError) as e:
        out["U6_COND_vs_exp16_arm_d"] = {"error": str(e)}
    write_json(RESULTS_DIR / "stage_a.json", out)
    return out


# ------------------------------------------------------------------------------------------------ ST grid
def _dR(r: dict[str, Any]) -> float | None:
    rec = r.get("realised") or {}
    v = (rec.get("dR") or {}).get("35")
    if v is None:
        v = (rec.get("dR") or {}).get(35)
    return v


def _dG(r: dict[str, Any]) -> float | None:
    rec = r.get("realised") or {}
    g = rec.get("dG1") or {}
    return g.get("35", g.get(35))


def st_design(rows: list[dict[str, Any]], D: str, sens_other: bool = False,
              energy: bool = True) -> tuple[np.ndarray, np.ndarray, list[str], np.ndarray]:
    names = ["const", "S4", "S5", "S1", "S2", "energy", "logDR", "logDg1"]
    X, y, cl = [], [], []
    for r in rows:
        s = r["site"]
        dr, dg = _dR(r), _dG(r)
        if dr is None or dg is None:
            continue
        x = [1.0, s == "S4", s == "S5", s in ("S1", "S1E"), s in ("S2", "S2E"), energy and s in ("S1E", "S2E"),
             math.log(dr + D_OFFSET), math.log(dg + D_OFFSET)]
        X.append([float(v) for v in x])
        ok = r["passed"] and r["label"] not in ((D, "invalid") if sens_other else (D,) + BAD)
        y.append(float(ok))
        cl.append(r["slot_index"])
    return np.array(X), np.array(y), names, np.array(cl)


def trim_support(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Common support: each comparison site and S0 trimmed to the overlap of their 2.5-97.5% log D_R ranges."""
    lg = defaultdict(list)
    for r in rows:
        if _dR(r) is not None:
            lg[r["site"]].append(math.log(_dR(r) + D_OFFSET))
    if "S0" not in lg:
        return rows, {"note": "no S0 rows"}
    s0lo, s0hi = np.percentile(lg["S0"], [2.5, 97.5])
    keep_ranges, info = {}, {}
    for s, v in lg.items():
        if s == "S0":
            continue
        lo, hi = np.percentile(v, [2.5, 97.5])
        keep_ranges[s] = (max(lo, s0lo), min(hi, s0hi))
        info[s] = {"overlap": [float(keep_ranges[s][0]), float(keep_ranges[s][1])],
                   "has_support": bool(keep_ranges[s][0] < keep_ranges[s][1])}
    s0_lo = min((v[0] for v in keep_ranges.values() if v[0] < v[1]), default=s0lo)
    s0_hi = max((v[1] for v in keep_ranges.values() if v[0] < v[1]), default=s0hi)
    out = []
    for r in rows:
        if _dR(r) is None:
            continue
        x = math.log(_dR(r) + D_OFFSET)
        if r["site"] == "S0":
            if s0_lo <= x <= s0_hi:
                out.append(r)
        else:
            lo, hi = keep_ranges[r["site"]]
            if lo < hi and lo <= x <= hi:
                out.append(r)
    info["n_before"] = len(rows)
    info["n_after"] = len(out)
    return out, info


def fit_indicator(rows: list[dict[str, Any]], D: str, label: str, boot: int = 2000,
                  strata: list[str] | None = None, sens_other: bool = False, energy: bool = True) -> dict[str, Any]:
    X, y, names, cl = st_design(rows, D, sens_other, energy)
    res: dict[str, Any] = {"n": int(len(y)), "n_events": int(y.sum()), "names": names}
    if strata:
        st = np.array(strata)
        for tt in sorted(set(strata))[1:]:
            X = np.column_stack([X, (st == tt).astype(float)])
            names = names + [f"task_{tt}"]
    keep = [j for j in range(X.shape[1]) if j == 0 or X[:, j].std() > 0]
    X = X[:, keep]
    names = [names[j] for j in keep]
    res["names_used"] = names
    if y.sum() == 0 or y.sum() == len(y):
        res["error"] = "no variation in the outcome"
        return res
    if np.linalg.matrix_rank(X) < X.shape[1]:
        res["error"] = "design not identifiable (collinear columns, e.g. S2 == energy when only S2E rows remain)"
        return res
    f = S.firth_fit(X, y)
    res["beta"] = {n: float(b) for n, b in zip(names, f["beta"])}
    res["converged"] = f["converged"]
    res["se_wald"] = {n: float(math.sqrt(max(f["cov"][j, j], 0))) for j, n in enumerate(names)}
    res["profile_ci95"] = {}
    for nm in ("S1", "S2", "S4", "S5", "energy", "logDR", "logDg1"):
        if nm in names:
            j = names.index(nm)
            res["profile_ci95"][nm] = list(S.firth_profile_ci(X, y, j, f))
    idx = [names.index(nm) for nm in ("S1", "S2") if nm in names]
    if boot and idx:
        bs = S.cluster_bootstrap(X, y, cl if not strata else np.array([f"{a}|{b}" for a, b in zip(strata, cl)]),
                                 idx, n_boot=boot, strata=None if not strata else np.array(strata))
        res["cluster_bootstrap"] = {"n_ok": bs["n_ok"], "n_failed": bs["n_failed"],
                                    "ci95": {names[j]: v for j, v in bs.get("ci95", {}).items()}}
    return res


def st_analysis(rows: list[dict[str, Any]], boot: int = 2000) -> dict[str, Any]:
    out: dict[str, Any] = {"tasks": {}}
    pooled_rows, pooled_strata = [], []
    for t in ST_TASKS:
        D = DEFAULT6[t]
        st = [r for r in rows if r["task"] == t and r["cell"] == "ST"]
        if not st:
            continue
        tw = cell(rows, t, "TWIN", N30)
        cells = {}
        for (site, a), grp in sorted(_group(st).items(), key=lambda x: (x[0][0], x[0][1])):
            n = len(grp)
            dr = [v for v in (_dR(r) for r in grp) if v is not None]
            dg = [v for v in (_dG(r) for r in grp) if v is not None]
            cells[f"{site}|a{a:g}"] = {
                "site": site, "alpha": a, "n": n, "correct_off_default": sum(corr_off(r, D) for r in grp) / n,
                "k_correct_off_default": sum(corr_off(r, D) for r in grp),
                "correct_other": sum(r["passed"] and r["label"] == "other" for r in grp),
                "off_default": sum(r["label"] not in (D, "invalid") for r in grp) / n,
                "pass": sum(r["passed"] for r in grp) / n,
                "median_D_R": float(np.median(dr)) if dr else None, "median_D_g1": float(np.median(dg)) if dg else None,
                "median_kl_s3": float(np.median([r["s3"]["kl_mean_steps1_32"] for r in grp if r.get("s3")]))
                if site == "S3" and any(r.get("s3") for r in grp) else None,
                "correct_comp": dict(Counter(r["label"] for r in grp if r["passed"]).most_common())}
        pre = [r for r in st if r["site"] in PREFILL_SITES and r["slot_index"] in N30]
        trimmed, info = trim_support(pre)
        res = {"cells": cells, "twin_correct_off_default": sum(corr_off(r, D) for r in tw.values()) / max(len(tw), 1),
               "common_support": info}
        # plan fallback: a raw arm (S1 at R, S2 at the condition span) without common support with S0 on log D_R is
        # replaced by its energy-matched arm (S1E / S2E, coded as S1 / S2 with no energy dummy); logged
        arm_used = {}
        for arm in ("S1", "S2"):
            raw_ok = (info.get(arm) or {}).get("has_support", False)
            e_ok = (info.get(arm + "E") or {}).get("has_support", False)
            arm_used[arm] = arm if raw_ok else (arm + "E" if e_ok else None)
        res["rule_arms"] = arm_used
        if all(arm_used[a] == a for a in ("S1", "S2")):
            rule_rows = trimmed  # noqa: F841 - also used by the alpha <= 4 sensitivity below
            res["rule_model"] = "primary (raw S1, S2 with common support; energy dummy for S1E/S2E)"
            res["indicator"] = fit_indicator(rule_rows, D, t, boot=boot)
        else:
            keep_sites = {"S0", "S4", "S5"} | {v for v in arm_used.values() if v}
            rule_rows = [r for r in trimmed if r["site"] in keep_sites]
            res["rule_model"] = (f"fallback: energy-matched arms {arm_used} (raw arm without common support with S0 on "
                                 f"log D_R); no energy dummy")
            res["indicator"] = fit_indicator(rule_rows, D, t, boot=boot, energy=False)
            res["indicator_primary_all_trimmed_rows"] = fit_indicator(trimmed, D, t, boot=0)
        # sensitivity (post hoc, labelled as such): the same rule model on the pre-breakage doses alpha <= 4
        res["indicator_alpha_le4_posthoc"] = fit_indicator([r for r in rule_rows if float(r["alpha"]) <= 4.0], D, t,
                                                           boot=500, energy=all(arm_used[a] == a for a in ("S1", "S2")))
        res["indicator_untrimmed"] = fit_indicator(pre, D, t, boot=0)
        res["indicator_logDR_only"] = fit_indicator([dict(r, realised=dict(r.get("realised") or {},
                                                                           dG1={"35": 1.0}))
                                                     for r in trimmed], D, t, boot=0)
        res["indicator_sens_other_correct"] = fit_indicator(trimmed, D, t, boot=0, sens_other=True)
        # RCS(3) sensitivity in log D_R (restricted cubic spline, knots at the 10/50/90th percentiles)
        res["indicator_rcs3"] = fit_rcs(trimmed, D)
        # MH OR S0 vs S1 and S0 vs S2 within quintiles of log D_R
        res["mh"] = {}
        for comp_site in ("S1", "S2", "S1E", "S2E"):
            sub = [r for r in pre if r["site"] in ("S0", comp_site) and _dR(r) is not None]
            if len(sub) < 10:
                continue
            ld = np.array([math.log(_dR(r) + D_OFFSET) for r in sub])
            qs = np.quantile(ld, [0, .2, .4, .6, .8, 1.0])
            tabs = []
            for i in range(5):
                g_ = [r for r, x in zip(sub, ld) if (qs[i] <= x <= qs[i + 1])]
                a_ = sum(corr_off(r, D) for r in g_ if r["site"] == "S0")
                b_ = sum(not corr_off(r, D) for r in g_ if r["site"] == "S0")
                c_ = sum(corr_off(r, D) for r in g_ if r["site"] == comp_site)
                d_ = sum(not corr_off(r, D) for r in g_ if r["site"] == comp_site)
                tabs.append(np.array([[a_, b_], [c_, d_]]))
            res["mh"][f"S0_vs_{comp_site}"] = {**S.mh_or(tabs), "tables": [t_.tolist() for t_ in tabs]}
        # shuffled-site placebo (within task): S1/S2 coefficients should vanish
        rng = np.random.default_rng(7)
        sites = [r["site"] for r in trimmed]
        perm = rng.permutation(len(sites))
        shuf = [dict(r, site=sites[j]) for r, j in zip(trimmed, perm)]
        res["placebo_shuffled_sites"] = fit_indicator(shuf, D, t, boot=0)
        # paired site flips: per slot and alpha, correct-off-default at S0 vs S1 / S2
        pf = {}
        for comp_site in ("S1", "S2", "S4", "S5", "S3"):
            b_, c_ = 0, 0
            for a in (1.0, 2.0, 4.0, 8.0):
                s0 = {r["slot_index"]: r for r in st if r["site"] == "S0" and r["alpha"] == a}
                sx = {r["slot_index"]: r for r in st if r["site"] == comp_site and r["alpha"] == a}
                for s in set(s0) & set(sx):
                    b_ += corr_off(s0[s], D) and not corr_off(sx[s], D)
                    c_ += corr_off(sx[s], D) and not corr_off(s0[s], D)
            pf[f"S0_vs_{comp_site}"] = {"S0_only": int(b_), "other_only": int(c_), "p": S.mcnemar_exact(b_, c_)}
        res["paired_flips"] = pf
        out["tasks"][t] = res
        pooled_rows += trimmed
        pooled_strata += [t] * len(trimmed)
    # pooled with task fixed effects (descriptive)
    if pooled_rows:
        # rows of both tasks: the outcome definition needs each row's own default
        X, y, names, cl, strata = [], [], None, [], []
        for t in ST_TASKS:
            sub = [r for r in pooled_rows if r["task"] == t]
            if not sub:
                continue
            Xt, yt, names, clt = st_design(sub, DEFAULT6[t])
            X.append(Xt)
            y.append(yt)
            cl += [f"{t}|{c}" for c in clt]
            strata += [t] * len(yt)
        X, y = np.vstack(X), np.concatenate(y)
        st_ = np.array(strata)
        Xp = np.column_stack([X] + [(st_ == tt).astype(float) for tt in sorted(set(strata))[1:]])
        nm = names + [f"task_{tt}" for tt in sorted(set(strata))[1:]]
        keep = [j for j in range(Xp.shape[1]) if j == 0 or Xp[:, j].std() > 0]
        if 0 < y.sum() < len(y):
            f = S.firth_fit(Xp[:, keep], y)
            out["pooled_task_FE"] = {"beta": {nm[j]: float(b) for j, b in zip(keep, f["beta"])}, "n": int(len(y)),
                                     "n_events": int(y.sum()), "converged": f["converged"]}
    # RULE
    surv = []
    for t, res in out["tasks"].items():
        ind = res["indicator"]
        if "beta" not in ind:
            continue
        ok = True
        for nm in ("S1", "S2"):
            b = ind["beta"].get(nm)
            bci = (ind.get("cluster_bootstrap") or {}).get("ci95", {}).get(nm)
            pci = ind["profile_ci95"].get(nm)
            if b is None or bci is None or pci is None or not (b < 0 and bci[1] < 0 and pci[1] < 0):
                ok = False
        if ok:
            surv.append(t)
    s0_any = any(c["k_correct_off_default"] > 0 for t, res in out["tasks"].items() for c in res["cells"].values()
                 if c["site"] == "S0")
    if not s0_any:
        verdict = "WITHDRAWN: no prefill site moves the algorithm in bf16 (S0 has 0 correct off-default programs)"
    elif surv:
        verdict = f"SURVIVES on {surv}: S1 and S2 below S0 at matched downstream displacement"
    else:
        verdict = "WITHDRAWN as FP8-specific: the site of the choice is open"
    out["RULE"] = {"verdict": verdict, "tasks_surviving": surv}
    # ST x Stage A concordance: the noise-sensitive spec band vs the band with the largest exchange transfer
    conc = {}
    sa_p = RESULTS_DIR / "stage_a.json"
    sa = read_json(sa_p)["tasks"] if sa_p.exists() else {}
    band_of = {"S4": "0-11", "S0": "12-23", "S5": "24-35"}
    for t, res in out["tasks"].items():
        noise = {}
        for site in ("S4", "S0", "S5"):
            cs = [c for c in res["cells"].values() if c["site"] == site and c["alpha"] in (1.0, 2.0, 4.0)]
            if cs:
                noise[band_of[site]] = sum(c["k_correct_off_default"] for c in cs) / sum(c["n"] for c in cs)
        xb = {b: (sa.get(t, {}).get("cells", {}).get(f"X_{b}") or {}).get("off_default_transfer")
              for b in ("0-11", "12-23", "24-35")}
        xb = {k: v for k, v in xb.items() if v is not None}
        nb = max(noise, key=noise.get) if noise and max(noise.values()) > 0 else None
        tb = max(xb, key=xb.get) if xb else None
        conc[t] = {"noise_share_by_band": noise, "exchange_off_default_transfer_by_band": xb,
                   "noise_band": nb, "exchange_band": tb, "concordant": (nb == tb) if nb and tb else None}
    out["ST_x_StageA_concordance"] = conc
    write_json(RESULTS_DIR / "site_grid.json", out)
    return out


def fit_rcs(rows: list[dict[str, Any]], D: str) -> dict[str, Any]:
    X, y, names, _ = st_design(rows, D)
    if len(y) < 20 or y.sum() == 0 or y.sum() == len(y):
        return {"error": "too few rows or no variation"}
    x = X[:, names.index("logDR")]
    k = np.percentile(x, [10, 50, 90])

    def pos3(v: np.ndarray) -> np.ndarray:
        return np.clip(v, 0, None) ** 3
    sp = (pos3(x - k[0]) - pos3(x - k[1]) * (k[2] - k[0]) / (k[2] - k[1]) + pos3(x - k[2]) * (k[1] - k[0]) /
          (k[2] - k[1])) / (k[2] - k[0]) ** 2
    Xr = np.column_stack([X, sp])
    nm = names + ["logDR_rcs1"]
    keep = [j for j in range(Xr.shape[1]) if j == 0 or Xr[:, j].std() > 0]
    f = S.firth_fit(Xr[:, keep], y)
    return {"beta": {nm[j]: float(b) for j, b in zip(keep, f["beta"])}, "converged": f["converged"], "n": int(len(y))}


def _group(st: list[dict[str, Any]]) -> dict[tuple[str, float], list[dict[str, Any]]]:
    g = defaultdict(list)
    for r in st:
        g[(r["site"], float(r["alpha"]))].append(r)
    return g


# ------------------------------------------------------------------------------------------------ state vs token
def state_vs_token(rows: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    dmd = read_json(ROOT / "predictions" / "dmd_temperatures_iter6.json") if \
        (ROOT / "predictions" / "dmd_temperatures_iter6.json").exists() else {}
    for t in ST_TASKS:
        D = DEFAULT6[t]
        tw = cell(rows, t, "TWIN")
        for a in (2.0, 4.0):
            s3 = {r["slot_index"]: r for r in rows if r["task"] == t and r["cell"] == "ST" and r["site"] == "S3"
                  and r["alpha"] == a}
            dm = cell(rows, t, f"DMD_a{a:g}")
            sl = sorted(set(s3) & set(dm) & set(tw))
            if not sl:
                continue

            def flip(r: dict[str, Any], s: int) -> bool:
                return bool(corr_off(r, D) and tw[s]["label"] == D)
            b = sum(flip(s3[s], s) and not flip(dm[s], s) for s in sl)
            c = sum(flip(dm[s], s) and not flip(s3[s], s) for s in sl)
            out[f"{t}|a{a:g}"] = {"n_pairs": len(sl), "S3_only_flips": b, "DMD_only_flips": c,
                                  "p_exact_mcnemar": S.mcnemar_exact(b, c),
                                  "S3_flip_share": sum(flip(s3[s], s) for s in sl) / len(sl),
                                  "DMD_flip_share": sum(flip(dm[s], s) for s in sl) / len(sl),
                                  "S3_pass": sum(s3[s]["passed"] for s in sl) / len(sl),
                                  "DMD_pass": sum(dm[s]["passed"] for s in sl) / len(sl),
                                  "S3_correct_comp": dict(Counter(s3[s]["label"] for s in sl if s3[s]["passed"])),
                                  "DMD_correct_comp": dict(Counter(dm[s]["label"] for s in sl if dm[s]["passed"])),
                                  "calibration": dmd.get(f"{t}|{a:g}"), "primary": a == 2.0}
    prim = [v for k, v in out.items() if v["primary"]]
    out["verdict_alpha2"] = ("S3 (state noise) moves the algorithm beyond KL-matched temperature on both tasks"
                             if len(prim) == 2 and all(v["p_exact_mcnemar"] < 0.05 and v["S3_only_flips"] >
                                                       v["DMD_only_flips"] for v in prim)
                             else "not established at alpha 2 on both tasks (threshold p < 0.05, min 6:0)")
    write_json(RESULTS_DIR / "state_vs_token.json", out)
    return out


# ------------------------------------------------------------------------------------------------ top-five push
GEO_MAP = {"bfs": ["bfs"], "dfs": ["dfs"], "bibfs": ["bibfs"], "iddfs": ["iddfs"], "astar_gbfs": ["astar", "gbfs"],
           "dijkstra": ["dijkstra_unit"]}


def top5(rows: list[dict[str, Any]]) -> dict[str, Any]:
    t, D = "T1", "bfs"
    out: dict[str, Any] = {"cells": {}}
    for arm in ("TWIN", "BAN", "TOP5_a1", "TOP5_a2", "TOP5_a4", "TOP5_a8", "TOP5BAN"):
        c = cell(rows, t, arm)
        if not c:
            continue
        n = len(c)
        land = Counter(r["label"] for r in c.values() if r["passed"] and r["label"] not in (D,) + BAD)
        out["cells"][arm] = {"n": n, "pass": sum(r["passed"] for r in c.values()) / n,
                             "bfs_share": sum(r["label"] == D for r in c.values()) / n,
                             "correct_non_bfs": sum(land.values()), "landing_comp": dict(land.most_common()),
                             "attempted_comp": comp(c, False)}
    # geometry
    gz_p = ROOT / "inputs_extra" / "exp20" / "directions" / "plan_geometry_T1.npz"
    st_p = ROOT / "cache" / "geometry_T1_states.npz"
    gj = read_json(ROOT / "inputs_extra" / "exp20" / "results" / "plan_geometry_T1.json")
    if gz_p.exists() and st_p.exists():
        gz = np.load(gz_p)
        sz = np.load(st_p)
        names = [str(x) for x in gz["centroid_names"]]
        med = gz["med_norm"]
        C = gz["centroids"] / med[None, :, None]                          # [10, 12, D]
        Cf = C.reshape(len(C), -1)
        mu = Cf.mean(0)
        U, Sv, Vt = np.linalg.svd(Cf - mu, full_matrices=False)
        V2 = Vt[:2]
        expl = (Sv[:2] ** 2 / (Sv ** 2).sum()).tolist()

        def proj(A: np.ndarray) -> list[float]:
            return (((A / med[:, None]).reshape(-1) - mu) @ V2.T).tolist()
        pts = {k: proj(sz[k]) for k in sz.files if k != "blocks"}
        out["geometry"] = {"centroid_names": names, "centroids_pc": ((Cf - mu) @ V2.T).tolist(),
                           "explained_by_pc1_pc2_of_centroids": expl, "points_pc": pts,
                           "basis": "PCA of the 10 forced-prompt centroids (exp20, spec-mean block outputs 12-23 / "
                                    "median block norm), i.e. actual activation coordinates"}
        # geodesic k-NN MDS over centroids + this artifact's states
        keys = [k for k in sz.files if k != "blocks"]
        A = np.vstack([Cf] + [((sz[k] / med[:, None]).reshape(1, -1)) for k in keys])
        lab = names + keys
        Dm = np.sqrt(((A[:, None, :] - A[None, :, :]) ** 2).sum(-1))
        k_nn = 6
        G = np.full_like(Dm, np.inf)
        for i in range(len(A)):
            nn = np.argsort(Dm[i])[:k_nn + 1]
            G[i, nn] = Dm[i, nn]
            G[nn, i] = Dm[nn, i]
        for kk in range(len(A)):  # Floyd-Warshall
            G = np.minimum(G, G[:, kk:kk + 1] + G[kk:kk + 1, :])
        G[~np.isfinite(G)] = np.nanmax(G[np.isfinite(G)]) * 1.5
        n = len(G)
        J = np.eye(n) - np.ones((n, n)) / n
        Bm = -0.5 * J @ (G ** 2) @ J
        w, v = np.linalg.eigh(Bm)
        o = np.argsort(w)[::-1][:2]
        Y2 = v[:, o] * np.sqrt(np.clip(w[o], 0, None))
        out["geometry"]["mds_geodesic_knn"] = {"labels": lab, "xy": Y2.tolist(), "k": k_nn}
    # landing-position test on exp20's geodesic matrix (k10)
    Gc = gj["k10"]["G"]
    top5_set = ["bfs", "dfs", "gbfs", "iddfs", "astar"]
    surv = [a for a in Gc if a not in top5_set]

    def d_near_ban(a: str) -> float:
        return min(Gc[a][b] for b in top5_set)
    tests = {}
    for arm in ("TOP5_a1", "TOP5_a2", "TOP5_a4", "TOP5_a8", "TOP5BAN"):
        cc = out["cells"].get(arm)
        if not cc:
            continue
        land = cc["landing_comp"]
        mapped = []
        for lab_, k in land.items():
            for gname in GEO_MAP.get(lab_, []):
                mapped += [gname] * k if len(GEO_MAP.get(lab_, [])) == 1 else []
            if len(GEO_MAP.get(lab_, [])) == 2:
                mapped += [GEO_MAP[lab_][0]] * k
        surv_land = [m for m in mapped if m in surv]
        on_banned = Counter(m for m in mapped if m in top5_set)
        base_rec = {"n_correct_non_default": len(mapped), "n_on_survivors": len(surv_land),
                    "on_banned_algorithms": dict(on_banned)}
        if len(surv_land) < 5:
            tests[arm] = {**base_rec, "verdict": "not computable (< 5 correct programs on survivor algorithms)" +
                          (f"; correct non-BFS programs land on banned algorithms {dict(on_banned)}" if on_banned else "")}
            continue
        obs = float(np.mean([d_near_ban(m) for m in surv_land]))
        rng = np.random.default_rng(11)
        null = [float(np.mean([d_near_ban(s) for s in rng.choice(surv, len(surv_land))])) for _ in range(1000)]
        tests[arm] = {**base_rec, "mean_geodesic_to_nearest_banned": obs, "null_mean": float(np.mean(null)),
                      "p_closer_than_null": float(np.mean(np.array(null) <= obs)),
                      "reading": "lands at the edge of the banned set" if obs < np.percentile(null, 5) else
                      ("lands on the opposite side" if obs > np.percentile(null, 95) else "indistinguishable from a "
                                                                                          "random survivor")}
    out["landing_test"] = tests
    write_json(RESULTS_DIR / "top5_push.json", out)
    return out


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("analysis6")
    which = sys.argv[1].split(",") if len(sys.argv) > 1 else ["engine", "stageA", "st", "svt", "top5"]
    rows = load_rows()
    logger.info(f"{len(rows)} labelled rows")
    if "engine" in which:
        logger.info(f"engine check: {engine_check(load_rows())}")
    if "stageA" in which:
        a = stage_a(rows)
        logger.info(f"Stage A P1: {a['P1']}")
    if "st" in which:
        s = st_analysis(rows)
        logger.info(f"ST RULE: {s['RULE']}")
    if "svt" in which:
        logger.info(f"state vs token: {state_vs_token(rows)}")
    if "top5" in which:
        top5(rows)


if __name__ == "__main__":
    main()
