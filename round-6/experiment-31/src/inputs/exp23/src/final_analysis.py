#!/usr/bin/env python3
"""STEP 11: analysis after the bans, using the FROZEN analysis functions (predictions/analysis_c3.py, hash-committed
in commit #2). Post-hoc additions are labelled 'post_hoc' in the outputs.

Outputs: results/bans.json (outcome table), c3a.json (primary + sensitivities), rivals.json, c3b.json,
c1_prices.json, phrasing.json, escape.json (per-direction table), banfree_predictors.json, crn_flips.json; commit #3.
"""

from __future__ import annotations

import collections
import importlib.util
import sys
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg import (ALL_TASKS, DATA_DIR, PATH_TASKS, PRED_DIR, RESULTS_DIR, TEMPLATE_IDS, read_json, read_jsonl,
                 setup_logging, sha256_file, write_json)
import prompts_gemma as PG


def frozen_analysis():
    spec = importlib.util.spec_from_file_location("analysis_c3_frozen", PRED_DIR / "analysis_c3.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


A = None
NOT_OFF = ("invalid", "disputed")


def lab_rows() -> list[dict[str, Any]]:
    return read_jsonl(DATA_DIR / "labels.jsonl")


def outcome_table(labs: list[dict[str, Any]], pre: dict[str, Any], use_fallback: bool = False,
                  include_extra: bool = False) -> dict[str, Any]:
    out = {}
    for t in ALL_TASKS:
        D = pre["tasks"][t]["D"]
        cat = set(PG.modes(t))
        arms = ("ban", "ban_extra") if include_extra else ("ban",)
        rr = [r for r in labs if r.get("stage") == "BAN" and r["task"] == t and r["arm"] in arms]
        if not rr:
            continue

        def L(r):
            return (r.get("fallback_label") or r["label"]) if (use_fallback and r["label"] == "disputed") else r["label"]
        n = len(rr)
        cnt = collections.Counter(L(r) for r in rr)
        A_t = sum(v for k, v in cnt.items() if k in cat and k != D) / n
        corr = [r for r in rr if r.get("passed")]
        corr_av = (sum(1 for r in corr if L(r) in cat and L(r) != D) / len(corr)) if corr else None
        per_t = {}
        for w in TEMPLATE_IDS:
            rw = [r for r in rr if r.get("template") == w]
            per_t[w] = sum(1 for r in rw if L(r) in cat and L(r) != D) / len(rw) if rw else None
        tw = [r for r in labs if r.get("stage") == "A" and r["task"] == t and r["arm"] == "twin"]
        tw_def = sum(1 for r in tw if r["label"] == D) / len(tw) if tw else None
        ban_def = cnt.get(D, 0) / n
        out[t] = {"D": D, "n": n, "A_t": A_t, "C_t": int(A_t >= 0.5), "attempted_avoidance": 1 - ban_def,
                  "other": cnt.get("other", 0) / n, "invalid": cnt.get("invalid", 0) / n,
                  "disputed": cnt.get("disputed", 0) / n, "default_share": ban_def, "pass": len(corr) / n,
                  "correct_only_avoidance": corr_av, "per_template_avoidance": per_t, "composition": dict(cnt),
                  "correct_composition": dict(collections.Counter(L(r) for r in corr)),
                  "twin_default_share": tw_def,
                  "default_share_drop": (tw_def - ban_def) if tw_def is not None else None,
                  "flag": read_json(PRED_DIR / "commit1.json")["pilot"][t].get("flag")}
    return out


def crn_flips(labs: list[dict[str, Any]], pre: dict[str, Any]) -> dict[str, Any]:
    by = {}
    for r in labs:
        if (r.get("stage") == "A" and r["arm"] == "twin") or (r.get("stage") == "BAN" and r["arm"] == "ban"):
            by[(r["task"], r["template"], int(r["slot"]), r["arm"])] = r["label"]
    out = {}
    for t in ALL_TASKS:
        D = pre["tasks"][t]["D"]
        c = collections.Counter()
        for w in TEMPLATE_IDS:
            for k in range(10):
                a, b = by.get((t, w, k, "twin")), by.get((t, w, k, "ban"))
                if a is None or b is None:
                    continue
                c[("D" if a == D else "notD") + "->" + ("D" if b == D else ("other" if b in ("other",) + NOT_OFF
                                                                             else "survivor"))] += 1
        out[t] = dict(c)
    return out


def c1_prices(labs: list[dict[str, Any]], pre: dict[str, Any], tasks: list[str]) -> dict[str, Any]:
    res = {}
    for t in tasks:
        arms = {"twin": [r for r in labs if r.get("stage") == "A" and r["task"] == t and r["arm"] == "twin"],
                "pn_a1": [r for r in labs if r.get("stage") == "A" and r["task"] == t and r["arm"] == "pn_a1"],
                "pn_a2": [r for r in labs if r.get("stage") == "A" and r["task"] == t and r["arm"] == "pn_a2"],
                "t13": [r for r in labs if r.get("stage") == "A" and r["task"] == t and r["arm"] == "t13"],
                "novelty": [r for r in labs if r.get("stage") == "C" and r["task"] == t and r["arm"] == "novelty"],
                "t16": [r for r in labs if r.get("stage") == "T16" and r["task"] == t and r["arm"] == "t16"]}
        arms = {k: v for k, v in arms.items() if v}
        summ = {k: A.arm_summary(v) for k, v in arms.items()}
        tab = {}
        pt = summ["twin"]["pass"]
        for k, s in summ.items():
            corr = [r["label"] for r in arms[k] if r.get("passed")]
            rh = A.rarefied_hill(corr, 25, 1000, seed=hash((t, k)) % 1000)
            tab[k] = {"n": s["n"], "pass": s["pass"], "pass_cost_points": max(0.0, 100 * (pt - s["pass"])),
                      "hill1_rarefied25": rh["hill"], "depth": rh["depth"], "flag": rh["flag"],
                      "correct_comp": s["correct_comp"], "attempt_comp": s["attempt_comp"]}
        knobs = {"PN": [k for k in ("pn_a1", "pn_a2") if k in summ],
                 "temperature": [k for k in ("t13", "t16") if k in summ],
                 "novelty": [k for k in ("novelty",) if k in summ]}
        hull = {}
        for kn, ks in knobs.items():
            if not ks:
                continue
            hull[kn] = {}
            for budget, name in ((5, "H5"), (15, "P15"), (20, "P20")):
                b = A.hull_best(summ["twin"], [summ[k] for k in ks], budget, seed=7)
                ci = A.bootstrap_hull(arms, ks, budget, n_boot=100, seed=11) if name == "H5" else None
                hull[kn][name] = {**b, "ci95": ci}
        res[t] = {"arms": tab, "hull": hull}
    return res


def phrasing(labs: list[dict[str, Any]], pre: dict[str, Any], tasks: list[str]) -> dict[str, Any]:
    out = {}
    for t in tasks:
        D = pre["tasks"][t]["D"]
        rec = {}
        for arm in ("twin", "t13", "pn_a1"):
            codes = [r["code"] for r in labs if r.get("stage") == "A" and r["task"] == t and r["arm"] == arm
                     and r.get("passed") and r["label"] == D and r.get("code")]
            rec[arm] = {f"theta_{th}": A.phrasing_clusters(codes, th) for th in (0.7, 0.8, 0.9)}
            rec[arm]["n_programs"] = len(codes)
        out[t] = rec
    return out


def escape_table(labs: list[dict[str, Any]], pre: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for t in ALL_TASKS:
        D = pre["tasks"][t]["D"]
        rows = {}
        for r in labs:
            if r["task"] != t or not str(r.get("arm", "")).startswith("esc"):
                continue
            rows.setdefault(r["arm"], []).append(r)
        out[t] = {a: {"n": len(v), "pass": sum(1 for r in v if r.get("passed")) / len(v),
                      "off_share": sum(1 for r in v if r["label"] not in (D,) + NOT_OFF) / len(v),
                      "composition": dict(collections.Counter(r["label"] for r in v))} for a, v in sorted(rows.items())}
    return out


def main() -> None:
    global A
    setup_logging("final_analysis")
    from commit import commit, verify_chain

    A = frozen_analysis()
    pre = read_json(PRED_DIR / "commit_preban.json")
    labs = lab_rows()
    ot = outcome_table(labs, pre)
    write_json(RESULTS_DIR / "bans.json", ot)
    tasks = [t for t in ALL_TASKS if t in ot]
    E = {t: pre["tasks"][t]["E_t"] for t in tasks}
    mv = {t: bool(pre["tasks"][t]["movable"]) for t in tasks}
    At = {t: ot[t]["A_t"] for t in tasks}
    primary = A.c3a(tasks, E, At, mv)
    sens = {}

    def sub(name: str, keep: list[str], Aval: dict[str, float] | None = None) -> None:
        av = Aval or At
        kk = [t for t in keep if av.get(t) is not None]
        r = A.c3a(kk, E, av, mv, n_perm=20000, n_boot=1000)
        sens[name] = {"n_tasks": len(kk), "BA": r["balanced_accuracy"]["BA"], "fisher_p": r["fisher"]["p_two_sided"],
                      "rho": r["spearman"]["rho"], "rho_p_one_sided": r["spearman"]["p_one_sided"],
                      "verdict": r["verdict"]}
    sub("without_R2", [t for t in tasks if t != "R2"])
    sub("without_T1_T2", [t for t in tasks if t not in PATH_TASKS])
    sub("without_flagged_R6", [t for t in tasks if t != "R6"])
    sub("correct_only_avoidance", tasks, {t: ot[t]["correct_only_avoidance"] for t in tasks})
    la = RESULTS_DIR / "label_audit.json"
    if la.exists():  # F7: tasks whose 4-program blind audit agreement < 0.85
        fl = read_json(la).get("flagged_tasks_below_0.85", [])
        sub("without_label_audit_flagged_tasks", [t for t in tasks if t not in fl])
        sens["without_label_audit_flagged_tasks"]["flagged"] = fl
    ot180 = outcome_table(labs, pre, include_extra=True)
    sub("bans_N180_with_extra_slots", tasks, {t: ot180[t]["A_t"] for t in tasks if t in ot180})
    otfb = outcome_table(labs, pre, use_fallback=True)
    sub("disputed_as_fallback_label", tasks, {t: otfb[t]["A_t"] for t in tasks if t in otfb})
    sub("compliance_as_default_share_drop", tasks, {t: ot[t]["default_share_drop"] for t in tasks})
    low = [t for t in tasks if (pre["tasks"][t]["rivals"].get("twin_modal_share") or 1) < 0.9]
    sub("default_share_drop_twin_modal_lt_0.9", low, {t: ot[t]["default_share_drop"] for t in tasks})
    us = read_json(RESULTS_DIR / "unit_sensitivity.json") if (RESULTS_DIR / "unit_sensitivity.json").exists() else {}
    sens["E_t_in_ban_units"] = {"alpha_in_ban_units": us.get("alpha_in_ban_units"),
                                "median_ratio_ban_over_banfree_ox": us.get("median_ratio_ban_over_ox"),
                                "note": "E_t counts directions; restating alpha in ban units relabels the doses only"}
    # continuous fallback predictors (F6): stage-1 off-default share (max over cells) and PN shares
    s1 = {t: max([c["excess"] for c in pre["tasks"][t]["stage1_cells"].values()] or [0]) for t in tasks}
    r_s1 = A.perm_spearman(np.array([s1[t] for t in tasks]), np.array([At[t] for t in tasks]), n_perm=20000)
    sens["post_hoc_continuous_stage1_max_excess"] = {"rho": r_s1["rho"], "p_one_sided": r_s1["p_one_sided"]}
    write_json(RESULTS_DIR / "c3a.json", {"primary": primary, "sensitivities": sens,
                                          "frozen_analysis_sha256": sha256_file(PRED_DIR / "analysis_c3.py")})
    logger.info(f"C3a: BA={primary['balanced_accuracy']['BA']} fisher={primary['fisher']['p_two_sided']} "
                f"rho={primary['spearman']['rho']} -> {primary['verdict']}")
    # rivals
    names = ["twin_modal_share", "twin_modal_share_correct", "can_max", "t13_off", "novelty_off", "pn_a1_off",
             "pn_a2_off", "opening_margin"]
    R = {nm: {t: pre["tasks"][t]["rivals"].get(nm) for t in tasks} for nm in names}
    rv = A.rivals(tasks, E, At, R, pre["rival_signs"])
    write_json(RESULTS_DIR / "rivals.json", rv)
    # C3b on gated events (C_t = 1)
    events = {}
    for t in tasks:
        if ot[t]["C_t"] != 1:
            continue
        D = pre["tasks"][t]["D"]
        S = pre["tasks"][t]["survivors"]
        realised = [r["label"] for r in labs if r.get("stage") == "BAN" and r["task"] == t and r["arm"] == "ban"
                    and r["label"] not in (D,) + NOT_OFF]
        events[t] = {"S": S, "labels": realised, "forecasts": pre["tasks"][t]["forecasts"]}
    c3b = A.c3b(events) if events else {"note": "no gated events (no task with C_t = 1)"}
    write_json(RESULTS_DIR / "c3b.json", c3b)
    # C1 (descriptive): movable tasks of this model, and all 15
    mov = [t for t in tasks if mv[t]]
    write_json(RESULTS_DIR / "c1_prices.json", {"movable_tasks": mov, "per_task": c1_prices(labs, pre, tasks)})
    write_json(RESULTS_DIR / "phrasing.json", phrasing(labs, pre, tasks))
    write_json(RESULTS_DIR / "escape.json", escape_table(labs, pre))
    write_json(RESULTS_DIR / "crn_flips.json", crn_flips(labs, pre))
    write_json(RESULTS_DIR / "banfree_predictors.json", {t: {k: pre["tasks"][t][k] for k in
                                                              ("D", "E_t", "E_t_1", "E_t_2", "movable",
                                                               "opening_margin", "rivals")} for t in tasks})
    c = commit("commit3_outcomes", [RESULTS_DIR / "bans.json"], note="outcome table (record only)")
    v = verify_chain()
    write_json(RESULTS_DIR / "commit_chain_verify_final.json", v)
    logger.info(f"commit #3 {c['hash'][:12]}; chain ok={v['ok']}")


if __name__ == "__main__":
    main()
