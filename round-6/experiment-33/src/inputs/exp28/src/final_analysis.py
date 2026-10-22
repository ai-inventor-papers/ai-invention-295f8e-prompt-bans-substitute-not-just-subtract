#!/usr/bin/env python3
"""Final analysis (CPU): runs the FROZEN analysis code (predictions/analysis_E.py, hash-committed in commit #0) on the
labelled samples and the commit-#1 predictor table, and writes results/{escape, pn, e_a1, e_a2, transplant,
sensitivities}.json. Also commit #2 (results hashed after analysis)."""

from __future__ import annotations

import collections
import importlib.util
import sys
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg import (ALL_TASKS, ALPHAS, BENCH, DATA_DIR, DIR_SEEDS, E23, PATH_TASKS, PRED_DIR, RESULTS_DIR, ROOT, SUITE,
                 TEMPLATE_IDS, read_json, read_jsonl, setup_logging, write_json)

spec = importlib.util.spec_from_file_location("analysis_E_frozen", PRED_DIR / "analysis_E.py")
A = importlib.util.module_from_spec(spec)
spec.loader.exec_module(A)

LAB: dict[str, dict[str, Any]] = {}


def labels() -> dict[str, dict[str, Any]]:
    if not LAB:
        LAB.update({r["row_id"]: r for r in read_jsonl(DATA_DIR / "labels.jsonl")})
    return LAB


def rows(stage: str, task: str | None = None, arm: str | None = None) -> list[dict[str, Any]]:
    return [r for r in labels().values() if r.get("stage") == stage and (task is None or r["task"] == task)
            and (arm is None or r.get("arm") == arm)]


def cells(t: str, stage: str) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for r in rows(stage, t):
        if str(r.get("arm", "")).startswith("esc"):
            s, a = r["arm"][3:].split("_a")
            out[f"{s}_a{a}"].append(r)
    return dict(out)


# ------------------------------------------------------------------------------------------------ escape + PN
def escape_all(c1: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for t in ALL_TASKS:
        u = c1["units"][t]
        if not u["defaulted"]:
            out[t] = {"defaulted": False}
            continue
        tw = rows("twin", t, "twin")
        s1, cf = cells(t, "push"), cells(t, "confirm")
        res = {k: A.escape_unit(tw, s1, cf, u["D"], u["catalogue"], len(DIR_SEEDS), ALPHAS, kind=k)
               for k in ("cat", "any", "corr")}
        prim = res["cat"]
        conf_rows = [r for k in prim["confirmed"] for r in s1.get(k, []) + cf.get(k, [])]
        land = A.landing(conf_rows, u["D"], u["catalogue"])
        per_dir = {}
        for s in DIR_SEEDS:
            for a in ALPHAS:
                key = f"{s}_a{int(a)}"
                rr = s1.get(key, [])
                per_dir[key] = {"n": len(rr), "off_cat": A.off_cat(rr, u["D"], u["catalogue"]),
                                "pass": A.pass_rate(rr), "composition": A.composition(rr, correct_only=False),
                                "stage1_pass": prim["stage1"].get(key, {}).get("stage1_pass"),
                                "confirmed": key in prim["confirmed"]}
        out[t] = {"defaulted": True, "D": u["D"], "primary": prim, "sensitivity_off_any": res["any"],
                  "sensitivity_off_corr": res["corr"], "E_u": prim["E_u"], "E_u_max": prim["E_u_max"],
                  "E_u_off_any": res["any"]["E_u"], "E_u_off_corr": res["corr"]["E_u"], "movable": prim["movable"],
                  "landing": land, "per_direction": per_dir,
                  "max_over_directions_off_cat": max((v["off_cat"] for v in per_dir.values() if v["n"]), default=None),
                  "per_direction_off_cat_distribution": sorted(v["off_cat"] for v in per_dir.values() if v["n"])}
    return out


def pn_all(c1: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for t in ALL_TASKS:
        u = c1["units"][t]
        D, cat = u["D"], u["catalogue"]
        tw = rows("twin", t, "twin")
        rec: dict[str, Any] = {"twin": {"n": len(tw), "pass": A.pass_rate(tw),
                                        "hill1_correct_d25": A.hill1_rarefied([r["label"] for r in tw if r.get("passed")]),
                                        "off_corr": A.off_corr(tw, D, cat) if D else None,
                                        "composition_correct": A.composition(tw)}}
        ex = []
        for a in ALPHAS:
            rr = rows("push", t, f"pn_a{int(a)}")
            corr = [r["label"] for r in rr if r.get("passed")]
            rec[f"a{int(a)}"] = {"n": len(rr), "pass": A.pass_rate(rr),
                                 "off_corr": A.off_corr(rr, D, cat) if D else None,
                                 "off_cat": A.off_cat(rr, D, cat) if D else None,
                                 "hill1_correct_d25": A.hill1_rarefied(corr) if len(corr) >= 2 else None,
                                 "composition_correct": A.composition(rr), "composition_all": A.composition(rr, False)}
            if D and rr:
                ex.append(rec[f"a{int(a)}"]["off_corr"] - rec["twin"]["off_corr"])
        rec["pn_excess"] = max(ex) if ex else None
        out[t] = rec
    return out


# ------------------------------------------------------------------------------------------------ E-A1
def can_count_exp23() -> dict[str, int]:
    """exp23 forced-'can' count: number of non-default catalogue modes with >= 1 correct adherent forced program."""
    out = collections.defaultdict(set)
    for r in read_jsonl(E23 / "data" / "samples.jsonl"):
        if r.get("arm") == "can" and r.get("passed") and r.get("label") == r.get("mode"):
            out[r["task"]].add(r["mode"])
    return {t: len(out.get(t, set())) for t in ALL_TASKS}


def e_a1_all(c1: dict[str, Any], esc: dict[str, Any], pn: dict[str, Any]) -> dict[str, Any]:
    units = [t for t in ALL_TASKS if c1["units"][t]["defaulted"] and c1["units"][t]["beta"] is not None]
    beta = {t: c1["units"][t]["beta"] for t in units}
    E = {t: esc[t]["E_u"] for t in units}
    cls = {t: c1["units"][t]["class"] for t in units}
    riv = {"twin_modal_share": {t: c1["units"][t]["rivals"]["twin_modal_share"] for t in units},
           "novelty_off_cat": {t: c1["units"][t]["rivals"]["novelty_off_cat"] for t in units},
           "opening_margin": {t: c1["units"][t]["rivals"]["opening_margin"] for t in units},
           "merit_gap_runtime": {t: (c1["units"][t]["rivals"]["merit_gap"] or {}).get("runtime_ratio") for t in units},
           "merit_gap_tokens": {t: (c1["units"][t]["rivals"]["merit_gap"] or {}).get("token_ratio") for t in units}}
    sign = {"twin_modal_share": -1, "novelty_off_cat": 1, "opening_margin": -1, "merit_gap_runtime": -1,
            "merit_gap_tokens": -1}
    main = A.e_a1(units, beta, E, cls, riv, sign)
    # checks and sensitivities
    K = {t: c1["units"][t]["K"] for t in units}
    can = can_count_exp23()
    const_E = len({E[t] for t in units}) <= 1
    main["partial_spearman_given_K_and_can"] = None if const_E else A.partial_spearman([beta[t] for t in units], [E[t] for t in units],
                                                                  [[K[t] for t in units], [can[t] for t in units]])
    main["partial_spearman_given_K"] = None if const_E else A.partial_spearman([beta[t] for t in units], [E[t] for t in units],
                                                          [[K[t] for t in units]])
    sens = {}

    def run(name: str, b: dict[str, float | None], e: dict[str, float], uu: list[str] | None = None) -> None:
        uu = [t for t in (uu or units) if b.get(t) is not None and e.get(t) is not None]
        r = A.e_a1(uu, {t: b[t] for t in uu}, {t: e[t] for t in uu},
                   {t: A_cls(b[t]) for t in uu}, {}, {}, n_perm=50_000, n_boot=0)
        sens[name] = {k: r[k] for k in ("n", "rho", "p_one_sided_perm", "kendall_tau_b", "immovable_frac_collapsed",
                                        "n_beta_ge_movable", "verdict")}
    for src in ("pt_chat", "pt_plain", "pt_pooled"):
        run(f"beta_{src}", {t: c1["units"][t][src]["beta"] for t in units}, E)
    run("beta_excl_other", {t: c1["units"][t][c1["units"][t]["primary_source"]]["beta_excl_other"] for t in units}, E)

    def beta_correct_only(t: str) -> float | None:
        u = c1["units"][t]
        cc = u["pt_pooled"]["correct_counts"]
        n = sum(v for k, v in cc.items() if k != "disputed")
        return (sum(cc.get(m, 0) for m in u["catalogue"] if m != u["D"]) / n) if n else None
    run("beta_correct_programs_only_any_n", {t: beta_correct_only(t) for t in units}, E)
    rj = RESULTS_DIR / "rejudge_disputed.json"
    if rj.exists():
        import predictors as PRm

        over = {k: v for k, v in read_json(rj)["labels"].items() if v}

        def beta_rejudged(t: str) -> float | None:
            u = c1["units"][t]
            prow = [dict(r, label=over.get(r["row_id"], r["label"])) for r in
                    rows("ptchat", t, "pt_chat") + rows("ptplain", t, "pt_plain")]
            return PRm.base_stats(t, u["D"], prow)["beta"]
        bre = {t: beta_rejudged(t) for t in units}
        run("beta_pooled_with_rejudged_disputed_rows", bre, E)
        sens["beta_pooled_with_rejudged_disputed_rows"]["values"] = bre
    sens["beta_correct_programs_only_any_n"]["values"] = {t: beta_correct_only(t) for t in units}
    run("E_off_any_exp23_definition", beta, {t: esc[t]["E_u_off_any"] for t in units})
    run("E_off_corr", beta, {t: esc[t]["E_u_off_corr"] for t in units})
    run("E_u_max", beta, {t: esc[t]["E_u_max"] for t in units})
    flagged = set(read_json(RESULTS_DIR / "regate.json").get("flagged_tasks", [])) if (RESULTS_DIR / "regate.json").exists() else set()
    run("without_regate_flagged_tasks", beta, E, [t for t in units if t not in flagged])
    run("secondary_target_pn_excess", beta, {t: pn[t]["pn_excess"] for t in units})
    e23 = read_json(E23 / "predictions" / "commit_preban.json")["tasks"]
    run("descriptive_beta_vs_exp23_E_t", beta, {t: e23[t]["E_t"] for t in units})
    agree = {t: {"fresh_movable": E[t] > 0, "iter4_movable": e23[t]["E_t"] > 0} for t in units}
    sens["fresh_vs_iteration4_movability"] = {"per_unit": agree,
                                              "agreement": sum(1 for v in agree.values()
                                                               if v["fresh_movable"] == v["iter4_movable"]) / len(units)}
    main["sensitivities"] = sens
    us = read_json(E23 / "results" / "unit_sensitivity.json")["per_task"]
    main["dose_check_exp23_ban_over_ox_unit"] = {
        t: float(np.median([v["ratio_ban_over_ox"] for v in us[t].values()])) if t in us else None for t in units}
    dc = {t: v for t, v in main["dose_check_exp23_ban_over_ox_unit"].items() if v is not None}
    main["dose_check_note"] = ("descriptive: median over band blocks of exp23's measured ban displacement in "
                               "outlier-excluded ban-free units (alpha 1 = 1 unit); rho(beta, ratio) = "
                               f"{A.spearman([beta[t] for t in dc], list(dc.values()))}")
    main["flagged_tasks_regate"] = sorted(flagged)
    main["power_note"] = ("n <= 15 units: one-sided critical rho ~0.46 (alpha .05) and ~0.63 (alpha .01) at n=14; a "
                          "true rho of 0.5 has well under 50% power. A replication on seen tasks, never a confirmation.")
    return main


def A_cls(b: float | None) -> str | None:
    if b is None:
        return None
    return "COLLAPSED" if b < A.THRESH["BETA_MOVABLE"] else ("DIVERSE" if b >= A.THRESH["BETA_DIVERSE"] else "INTERMEDIATE")


# ------------------------------------------------------------------------------------------------ E-A2
def prox_recompute(t: str, D: str, surv: list[str]) -> dict[str, float] | None:
    """Zhang-Shasha proximity forecast for a unit whose D changed from exp23's (port of exp23 predictors.proximity)."""
    import random

    from prox import zs_pair

    twin = [r["code"] for r in rows("twin", t, "twin") if r.get("passed") and r["label"] == D and r.get("code")][:20]
    forced: dict[str, list[str]] = collections.defaultdict(list)
    if t in PATH_TASKS:
        return None
    from bench.common.catalogue import TASKS

    for r in read_jsonl(BENCH / TASKS[t]["task_id"] / "forced_programs.jsonl"):
        if str(r.get("passed")) == "True" and r.get("label") == r.get("forced_mode") and r.get("code"):
            forced[r["forced_mode"]].append(r["code"])
    if not twin:
        return None
    rng = random.Random(f"prox|{t}")
    med = {}
    for m in surv:
        fs = forced.get(m, [])[:20]
        pairs = [(a, b) for a in fs for b in twin]
        rng.shuffle(pairs)
        ds = [d for d in (zs_pair(a, b) for a, b in pairs[:60]) if d is not None]
        if ds:
            med[m] = float(np.median(ds))
    if not med:
        return None
    scale = float(np.median(list(med.values()))) or 1.0
    z = {m: -med[m] / scale for m in med}
    mx = max(z.values())
    e = {m: np.exp(z[m] - mx) for m in z}
    tot = sum(e.values())
    return {m: float(e.get(m, 0.0) / tot) for m in surv}


def e_a2_all(c1: dict[str, Any], esc: dict[str, Any]) -> dict[str, Any]:
    e23 = read_json(E23 / "predictions" / "commit_preban.json")["tasks"]
    prox23 = read_json(E23 / "results" / "proximity.json")
    events, notes = [], {}
    for t in ALL_TASKS:
        u = c1["units"][t]
        if not u["defaulted"] or not esc[t].get("movable") or (u["beta"] or 0) < A.THRESH["BETA_MOVABLE"]:
            continue
        land = esc[t]["landing"]
        if not land["defined"]:
            notes[t] = "no defined landing"
            continue
        D, cat = u["D"], u["catalogue"]
        surv = [m for m in cat if m != D]
        s1, cf = cells(t, "push"), cells(t, "confirm")
        conf_rows = [r for k in esc[t]["primary"]["confirmed"] for r in s1.get(k, []) + cf.get(k, [])]
        outcomes = [r["label"] for r in conf_rows if r.get("passed") and r["label"] in surv]
        same_D = e23[t]["D"] == D
        q_assoc = e23[t]["forecasts"]["association"]["distribution"] if (same_D and e23[t]["forecasts"]["association"]["defined"]) else None
        if same_D and prox23.get(f"{t}|{D}", {}).get("defined"):
            q_prox = prox23[f"{t}|{D}"]["distribution"]
        else:
            q_prox = prox_recompute(t, D, surv)
        events.append({"unit": t, "r_u": u["r_u"], "landing": land["landing"], "K_u": len(cat), "outcomes": outcomes,
                       "survivors": surv, "q_base": u["q_base"], "q_assoc": q_assoc, "q_prox": q_prox,
                       "landing_composition": land["composition"], "D_same_as_exp23": same_D})
    res = A.e_a2(events)
    res["events"] = [{k: v for k, v in e.items() if k != "outcomes"} | {"n_outcomes": len(e["outcomes"])} for e in events]
    res["notes"] = notes
    return res


# ------------------------------------------------------------------------------------------------ transplant
def transplant_all(c1: dict[str, Any]) -> dict[str, Any]:
    tr = c1["transplant"]
    lam_p = RESULTS_DIR / "transplant_lambda.json"
    lam = read_json(lam_p) if lam_p.exists() else {"lambda": None, "status": "not run"}
    per, ctl = {}, {}
    for u in tr["S_T"] + tr["S_C"]:
        un = c1["units"][u]
        D, cat = un["D"], un["catalogue"]
        tw = [r for r in rows("twin", u, "twin")]
        arms = {k: rows("transplant", u, k) for k in ("T", "RND", "XT", "RP")}
        arms = {k: v for k, v in arms.items() if v}
        if not arms:
            continue
        pt_rows = rows("ptchat", u, "pt_chat") + rows("ptplain", u, "pt_plain")
        pt_comp = A.composition(pt_rows)
        res = A.transplant_unit(arms, tw, D, cat, un["beta"] or 0.0, un["r_u"], pt_comp)
        res["beta"], res["r_u"], res["D"] = un["beta"], un["r_u"], D
        disp = [r["realised_disp"]["S_mean_band"] for r in arms.get("T", []) if r.get("realised_disp")]
        res["realised_disp_T_S_mean_band_median"] = float(np.median(disp)) if disp else None
        for k in ("RND", "XT", "RP"):
            dd = [r["realised_disp"]["S_mean_band"] for r in arms.get(k, []) if r.get("realised_disp")]
            res[f"realised_disp_{k}_S_mean_band_median"] = float(np.median(dd)) if dd else None
        (per if u in tr["S_T"] else ctl)[u] = res
    summ = A.transplant_summary(per, ctl)
    return {"lambda": lam, "S_T": tr["S_T"], "S_C": tr["S_C"], "descriptive": tr["descriptive"], "per_unit": per,
            "controls": ctl, "summary": summ, "norms": read_json(RESULTS_DIR / "transplant_norms.json")
            if (RESULTS_DIR / "transplant_norms.json").exists() else None}


def main() -> None:
    setup_logging("final_analysis")
    c1 = read_json(PRED_DIR / "commit_E1.json")
    esc = escape_all(c1)
    write_json(RESULTS_DIR / "escape.json", esc)
    pn = pn_all(c1)
    write_json(RESULTS_DIR / "pn.json", pn)
    a1 = e_a1_all(c1, esc, pn)
    write_json(RESULTS_DIR / "e_a1.json", a1)
    logger.info(f"E-A1: rho={a1['rho']} p={a1['p_one_sided_perm']} immovable={a1['immovable_frac_collapsed']} "
                f"verdict={a1['verdict']} ({a1['why']})")
    a2 = e_a2_all(c1, esc)
    write_json(RESULTS_DIR / "e_a2.json", a2)
    logger.info(f"E-A2: events={a2['n_events']} hits={a2['hits']} p={a2['poisson_binomial_p']} verdict={a2['verdict']}")
    tp = transplant_all(c1)
    write_json(RESULTS_DIR / "transplant.json", tp)
    logger.info(f"transplant summary: {tp['summary'].get('share_supporting_of_valid')} valid={tp['summary'].get('n_valid')}")
    na = read_json(RESULTS_DIR / "novelty_audit.json") if (RESULTS_DIR / "novelty_audit.json").exists() else {}
    summ = tp["summary"]
    lam = tp["lambda"].get("lambda")
    if not tp["per_unit"]:
        tverd = "NOT RUN"
    elif summ.get("n_valid", 0) == 0:
        tverd = "UNTESTED (broken test: T fails the validity criterion on every S_T task)"
    elif tp["descriptive"]:
        tverd = "DESCRIPTIVE (|S_T| < 3 with beta >= 0.2)"
    else:
        share = summ.get("share_supporting_of_valid")
        tverd = "SUPPORTS SUFFICIENCY" if (share is not None and share >= 0.5) else "DOES NOT SUPPORT SUFFICIENCY"
    verdicts = {"E_A1": {"verdict": a1["verdict"], "why": a1["why"], "rho": a1["rho"], "p": a1["p_one_sided_perm"],
                         "n_units": a1["n"], "immovable_frac_collapsed": a1["immovable_frac_collapsed"]},
                "E_A2": {"verdict": a2["verdict"], "n_events": a2["n_events"], "hits": a2["hits"],
                         "p": a2["poisson_binomial_p"], "log_score_test": a2.get("log_score_test")},
                "transplant": {"verdict": tverd, "lambda": lam, "S_T": tp["S_T"], "S_C": tp["S_C"],
                               "share_supporting_of_valid": summ.get("share_supporting_of_valid"),
                               "collapsed_controls_within_tol": summ.get("collapsed_controls_all_within_tol"),
                               "rp_within_tol": summ.get("rp_all_within_tol")},
                "novelty": {"n_correct_other": na.get("n_correct_other"), "novel_count": na.get("novel_count"),
                            "rule_of_three_upper_95": na.get("rule_of_three_upper_95")},
                "status": "REPLICATION on seen tasks (never a confirmation); Holm across the secondary family is "
                          "applied by the evaluation step"}
    write_json(RESULTS_DIR / "verdicts.json", verdicts)
    logger.info(f"verdicts: {verdicts}")
    for t in ALL_TASKS:
        if esc[t].get("defaulted"):
            logger.info(f"{t}: D={esc[t]['D']} E={esc[t]['E_u']:.3f} Emax={esc[t]['E_u_max']:.3f} "
                        f"beta={c1['units'][t]['beta']} landing={esc[t]['landing'].get('landing')} r={c1['units'][t]['r_u']}")


if __name__ == "__main__":
    main()
