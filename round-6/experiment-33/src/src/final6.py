#!/usr/bin/env python3
"""S8 EVENTS + S9 L1 CONTEST (CPU) on the committed forecasts (predictions/forecasts_G6.json) with the FROZEN analysis
(predictions/analysis_L_gemma.py, imported from its committed copy and hash-checked against commit #0).

Outputs (results/): events_G6.json (every (unit, nudge) record, pooled / fresh-only / old-only), l1_contest.json
(primary pooled contest + splits + sensitivities), old_tally.json, l2.json, push_descriptives.json, pt_repertoire.json
(support before/after, priming check), l3.json (descriptive), report6.md.
"""

from __future__ import annotations

import collections
import importlib.util
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg import (ALL_TASKS, DATA_DIR, DIR_SEEDS6, E28_DATA, E28_RESULTS, PRED_DIR, PUSH_TASKS6, RESULTS_DIR, ROOT,
                 read_json, read_jsonl, setup_logging, sha256_file, write_json)
from audit6 import all_labels

FORECASTS = ("q_base", "q_tail", "q_lik", "q_lik_raw")


def frozen_analysis() -> Any:
    """Import the committed copy (predictions/analysis_L_gemma.py) after checking its sha256 against commit #0."""
    p = PRED_DIR / "analysis_L_gemma.py"
    recs = [json.loads(x) for x in (ROOT / "commitments.log").read_text().splitlines() if x.strip()]
    last = [r for r in recs if "predictions/analysis_L_gemma.py" in r["files"]][-1]   # commit #0 or its #0b bug fix
    assert last["files"]["predictions/analysis_L_gemma.py"] == sha256_file(p), "frozen analysis changed after commit"
    spec = importlib.util.spec_from_file_location("analysis_L_gemma", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


AL = frozen_analysis()


# ------------------------------------------------------------------------------------------------ cells
def cells_for(labs: dict[str, dict[str, Any]], t: str) -> dict[str, dict[str, dict[str, list[dict[str, Any]]]]]:
    """{'FD': {cell: rows}, 'PN': {cell: rows}} with provenance-tagged cell keys ('old:' exp28, 'fresh:' iter6)."""
    fd: dict[str, list] = collections.defaultdict(list)
    pn: dict[str, list] = collections.defaultdict(list)
    for r in labs.values():
        if r["task"] != t:
            continue
        st, arm = r.get("stage"), str(r.get("arm") or "")
        if st in ("push", "confirm") and arm.startswith("esc"):
            fd["old:" + arm[3:]].append(r)
        elif st == "push" and arm.startswith("pn_a"):
            pn["old:" + arm].append(r)
        elif st in ("push6", "confirm6") and arm.startswith("esc"):
            fd["fresh:" + arm[3:]].append(r)
        elif st == "push6" and arm.startswith("pn6"):
            pn["fresh:" + arm].append(r)
    return {"FD": dict(fd), "PN": dict(pn)}


def attach(e: dict[str, Any], u: dict[str, Any], prov: str) -> dict[str, Any]:
    nd = e["nondef"]
    e = dict(e)
    e["provenance"] = prov
    for k in ("r_u", "t_u", "qlik_top1", "TAIL_EMPTY", "DISCORDANT", "TAIL_DISCORDANT", "AUDIT_FAIL"):
        e[k] = u.get(k)
    e["q_base"] = {"q": u["q_base"], "defined": u["r_u"] is not None}
    e["q_tail"] = {"q": u["q_tail"], "defined": True}
    lk = u.get("q_lik")
    e["q_lik"] = {"q": lk, "defined": True} if (lk and u.get("qlik_defined")) else {"q": AL.uniform(nd), "defined": False}
    lr = u.get("q_lik_raw")
    e["q_lik_raw"] = {"q": lr, "defined": True} if (lr and u.get("qlik_defined")) else {"q": AL.uniform(nd), "defined": False}
    e["q_assoc"] = AL.assoc_forecast(u.get("q_assoc"), nd)
    return e


def build_events(labs: dict[str, dict[str, Any]], units: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list] = {"pooled": [], "fresh": [], "old": []}
    for t in PUSH_TASKS6:
        u = units[t]
        if u["D"] is None:
            continue
        cs = cells_for(labs, t)
        for nudge in ("FD", "PN"):
            cells = cs[nudge]
            for prov, sel in (("pooled", cells), ("fresh", {k: v for k, v in cells.items() if k.startswith("fresh:")}),
                              ("old", {k: v for k, v in cells.items() if k.startswith("old:")})):
                if not sel:
                    continue
                e = AL.build_event(t, nudge, sel, u["D"], u["catalogue"], u["twin_pass_T10"])
                e = attach(e, u, prov)
                e["D_changed_vs_exp28"] = u["D_changed_vs_exp28"]
                out[prov].append(e)
    return out


def strip(ev: list[dict[str, Any]]) -> list[dict[str, Any]]:
    keep = ("unit", "nudge", "provenance", "event", "n_cells", "n_qualifying_cells", "qualifying_cells",
            "n_rows_pooled", "n_correct_offdefault_catalogue", "n_correct_other", "composition", "landing", "modal",
            "clear_landing", "landing_margin", "D", "nondef", "K_u", "chance", "r_u", "t_u", "qlik_top1",
            "TAIL_EMPTY", "DISCORDANT", "TAIL_DISCORDANT", "AUDIT_FAIL", "D_changed_vs_exp28")
    return [{k: e.get(k) for k in keep} for e in ev]


def contest(ev: list[dict[str, Any]], label: str) -> dict[str, Any]:
    ev = [e for e in ev if e["event"]]
    if not ev:
        return {"label": label, "n_events": 0, "note": "no events"}
    r = AL.l1_contest(ev, FORECASTS, assoc=True)
    r["label"] = label
    return r


def with_ru(ev: list[dict[str, Any]], units: dict[str, Any], src: str) -> list[dict[str, Any]]:
    out = []
    for e in ev:
        e2 = dict(e)
        e2["r_u"] = units[e["unit"]]["r_u_by_source"].get(src)
        e2["TAIL_DISCORDANT"] = bool(e2["r_u"] is not None and e2["t_u"] is not None and e2["r_u"] != e2["t_u"])
        e2["DISCORDANT"] = bool(e2["r_u"] is not None and e2["qlik_top1"] is not None and e2["r_u"] != e2["qlik_top1"])
        out.append(e2)
    return out


def with_qwen_lik(ev: list[dict[str, Any]], units: dict[str, Any], qwen: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for e in ev:
        e2 = dict(e)
        sc = qwen.get(e["unit"])
        lk = AL.lik_forecast(sc or {}, e["nondef"], "norm")
        e2["qlik_top1"] = lk["top1"]
        e2["q_lik"] = {"q": lk["q"], "defined": lk["defined"]}
        e2["DISCORDANT"] = bool(e2["r_u"] is not None and lk["top1"] is not None and e2["r_u"] != lk["top1"])
        out.append(e2)
    return out


# ------------------------------------------------------------------------------------------------ tallies
def old_tally() -> dict[str, Any]:
    oe = read_json(PRED_DIR / "old_events_rescored.json")["events"]
    res = {}
    for name, sel in (("all7", oe), ("twin_silent", [e for e in oe if e["twin_silent_exp28_N50"]])):
        ps = [1.0 / (e["K_u"] - 1) for e in sel]
        out = {"n": len(sel), "units": [e["unit"] for e in sel]}
        fkey = {"hit_exp28": "r_u_exp28", "hit_repaired": "r_u_repaired", "hit_tail": "t_u", "hit_qlik": "qlik_top1"}
        for key in ("hit_exp28", "hit_repaired", "hit_tail", "hit_qlik"):
            k = sum(1 for e in sel if e[key])
            d = [e for e in sel if e.get(fkey[key]) is not None]
            kd = sum(1 for e in d if e[key])
            pd = [1.0 / (e["K_u"] - 1) for e in d]
            out[key] = {"hits": k, "poisson_binomial_p": AL.poisson_binomial_sf(k, ps) if sel else None,
                        "note": "undefined forecast counted as a miss",
                        "n_defined": len(d), "hits_defined_only": kd,
                        "poisson_binomial_p_defined_only": AL.poisson_binomial_sf(kd, pd) if d else None}
        out["n_changed_r_u"] = sum(1 for e in sel if e["CHANGED"])
        out["changed_units"] = [e["unit"] for e in sel if e["CHANGED"]]
        res[name] = out
    res["events"] = oe
    res["exp28_definition_note"] = ("exp28 E-A2 events (confirmed escapes only; landing = modal correct off-default "
                                    "catalogue label, ties by catalogue order) are the 'all7' set; the v6 pooled "
                                    "definition is in events_G6.json")
    return res


def l2(labs: dict[str, dict[str, Any]], units: dict[str, Any]) -> dict[str, Any]:
    """Correct nudged programs on algorithms with zero valid AND zero correct pt programs."""
    rows = []
    total = 0
    for t in PUSH_TASKS6:
        u = units[t]
        if u["D"] is None:
            continue
        b = u["base_by_source"]
        pooled_valid = collections.Counter()
        pooled_corr = collections.Counter()
        for src in ("exp28_pooled", "fewshot"):
            pooled_valid.update(b[src]["valid_counts"])
            pooled_corr.update(b[src]["correct_counts"])
        absent = [m for m in u["nondef"] if pooled_valid.get(m, 0) == 0 and pooled_corr.get(m, 0) == 0]
        nudged = [r for r in labs.values() if r["task"] == t and r.get("stage") in ("push", "confirm", "push6", "confirm6")
                  and AL.is_correct(r) and r["label"] in u["nondef"]]
        hit = collections.Counter(r["label"] for r in nudged if r["label"] in absent)
        total += len(nudged)
        rows.append({"unit": t, "absent_from_pt": absent, "n_correct_nudged_offdefault": len(nudged),
                     "n_on_absent": sum(hit.values()), "by_label": dict(hit)})
    n_abs = sum(r["n_on_absent"] for r in rows)
    return {"per_unit": rows, "n_correct_nudged_offdefault_catalogue": total, "n_on_pt_absent_algorithms": n_abs,
            "rule_of_three_upper_95": AL.rule_of_three(total) if n_abs == 0 else None,
            "rate": n_abs / total if total else None}


def hill(labels: list[str]) -> float | None:
    from analysis_E import hill1_rarefied

    return hill1_rarefied(labels, depth=25, n_sub=500, seed=0) if len(labels) >= 2 else None


def push_desc(labs: dict[str, dict[str, Any]], units: dict[str, Any]) -> dict[str, Any]:
    out = {}
    s1 = {r["task"]: r for r in read_jsonl(RESULTS_DIR / "push6_stage1_log.jsonl")}
    for t in PUSH_TASKS6:
        u = units[t]
        if u["D"] is None:
            out[t] = {"note": "NO DEFAULT at N 300"}
            continue
        cs = cells_for(labs, t)
        per = {}
        for k, rr in sorted(cs["FD"].items()):
            corr = [r for r in rr if AL.is_correct(r)]
            per[k] = {"n": len(rr), "pass": AL.pass_rate(rr),
                      "off_corr": sum(1 for r in corr if r["label"] in u["nondef"]) / len(rr),
                      "composition_correct": dict(collections.Counter(r["label"] for r in corr)),
                      "hill1_d25_correct": hill([r["label"] for r in corr]), "hill_flag_lt25": len(corr) < 25}
        fresh = [v["off_corr"] for k, v in per.items() if k.startswith("fresh:")]
        old2 = [v["off_corr"] for k, v in per.items() if k.startswith("old:") and k.endswith("_a2")]
        old1 = [v["off_corr"] for k, v in per.items() if k.startswith("old:") and k.endswith("_a1")]
        pn = {}
        for k, rr in sorted(cs["PN"].items()):
            corr = [r for r in rr if AL.is_correct(r)]
            pn[k] = {"n": len(rr), "pass": AL.pass_rate(rr),
                     "off_corr": sum(1 for r in corr if r["label"] in u["nondef"]) / len(rr),
                     "composition_correct": dict(collections.Counter(r["label"] for r in corr)),
                     "hill1_d25_correct": hill([r["label"] for r in corr])}
        conf = [k for k, v in per.items() if k.startswith("fresh:") and v["n"] >= 30]
        log = s1.get(t, {})
        out[t] = {"twin_pass_T10": u["twin_pass_T10"], "twin_off_corr_T10": u["twin_off_corr_T10"], "per_cell_FD": per,
                  "fresh_alpha2_off_corr": {"values": fresh, "max": max(fresh) if fresh else None,
                                            "median": float(np.median(fresh)) if fresh else None},
                  "exp28_alpha2_off_corr": {"values": old2, "max": max(old2) if old2 else None,
                                            "median": float(np.median(old2)) if old2 else None},
                  "exp28_alpha1_off_corr": {"values": old1, "max": max(old1) if old1 else None},
                  "PN": pn, "fresh_stage1_passing": log.get("passing"), "fresh_confirmation_cells": conf,
                  "fresh_confirmed": confirmed_fresh(per, u)}
    return out


def confirmed_fresh(per: dict[str, Any], u: dict[str, Any]) -> dict[str, Any]:
    from scipy import stats

    res = {}
    p0 = max(u["twin_off_corr_T10"] or 0.0, 0.01)
    for k, v in per.items():
        if not k.startswith("fresh:") or v["n"] < 30:
            continue
        kk = round(v["off_corr"] * v["n"])
        pb = float(stats.binom.sf(kk - 1, v["n"], p0))
        ok = (v["off_corr"] - (u["twin_off_corr_T10"] or 0) >= 0.20) and (v["pass"] >= 0.8 * u["twin_pass_T10"]) and pb < 0.05
        res[k] = {"n": v["n"], "off_corr": v["off_corr"], "pass": v["pass"], "binom_p": pb, "confirmed": ok}
    res["E_u_alpha2_fresh"] = sum(1 for k, v in res.items() if isinstance(v, dict) and v.get("confirmed")) / len(DIR_SEEDS6)
    return res


# ------------------------------------------------------------------------------------------------ pt repertoire
def mc_chi2(groups: dict[str, collections.Counter], n_perm: int = 10_000, seed: int = 0) -> dict[str, Any]:
    """Monte-Carlo permutation test of independence (label x group) with the chi-square statistic (the Monte-Carlo
    counterpart of the Fisher-Freeman-Halton test)."""
    labels = sorted(set().union(*[set(c) for c in groups.values()]))
    gs = sorted(groups)
    if len(labels) < 2 or len(gs) < 2:
        return {"p": None, "note": "degenerate table"}
    arr_l, arr_g = [], []
    for gi, g in enumerate(gs):
        for li, l in enumerate(labels):
            arr_l += [li] * groups[g].get(l, 0)
            arr_g += [gi] * groups[g].get(l, 0)
    arr_l, arr_g = np.array(arr_l), np.array(arr_g)

    def stat(gv: np.ndarray) -> float:
        tab = np.zeros((len(gs), len(labels)))
        np.add.at(tab, (gv, arr_l), 1)
        exp = tab.sum(1, keepdims=True) * tab.sum(0, keepdims=True) / tab.sum()
        m = exp > 0
        return float((((tab - exp) ** 2)[m] / exp[m]).sum())
    obs = stat(arr_g)
    rng = np.random.default_rng(seed)
    ge = sum(1 for _ in range(n_perm) if stat(rng.permutation(arr_g)) >= obs - 1e-9)
    return {"chi2": obs, "p": (ge + 1) / (n_perm + 1), "n": int(len(arr_l)), "groups": gs, "flag_p_lt_0.01": (ge + 1) / (n_perm + 1) < 0.01}


def pt_repertoire(labs: dict[str, dict[str, Any]], units: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for t in ALL_TASKS:
        u = units[t]
        b = u["base_by_source"]
        rows = [r for r in labs.values() if r["task"] == t and r.get("stage") in ("ptchat", "ptplain", "ptfs6")]
        by_src = {}
        for src, sel in (("exp28_chat", "ptchat"), ("exp28_plain", "ptplain"), ("fewshot", "ptfs6")):
            rr = [r for r in rows if r["stage"] == sel]
            corr = [r for r in rr if AL.is_correct(r)]
            by_src[src] = {"draws": len(rr), "valid": sum(1 for r in rr if r.get("valid")),
                           "catalogue_labelled": sum(1 for r in rr if r["label"] in u["catalogue"]),
                           "correct": len(corr),
                           "correct_nondefault_catalogue": sum(1 for r in corr if r["label"] in u["nondef"]),
                           "valid_counts": dict(collections.Counter(r["label"] for r in rr if AL.is_valid_attempt(r))),
                           "correct_counts": dict(collections.Counter(r["label"] for r in corr)),
                           "per_draw_correct_rate": len(corr) / len(rr) if rr else None}
        fs = [r for r in rows if r["stage"] == "ptfs6"]
        fam = {f: collections.Counter(r["label"] for r in fs if r.get("family") == f and AL.is_valid_attempt(r))
               for f in ("F_bench", "F_he")}
        zs = collections.Counter(r["label"] for r in rows if r["stage"] == "ptplain" and AL.is_valid_attempt(r))
        fsc = collections.Counter(r["label"] for r in fs if AL.is_valid_attempt(r))
        out[t] = {"by_source": by_src, "q_base_primary": u["base"]["primary"], "LOW_CORRECT": u["base"]["LOW_CORRECT"],
                  "n_correct_pooled": u["base"]["n_correct"], "r_u": u["r_u"], "r_u_exp28_pooled": b["exp28_pooled"]["r_u"],
                  "r_u_by_source": u["r_u_by_source"], "THIN_RU": u["base"]["THIN_RU"], "TIE": u["base"]["TIE"],
                  "r_u_correct_support": u["base"]["r_u_correct_support"],
                  "r_u_valid_support": u["base"]["r_u_valid_support"],
                  "priming_fewshot_vs_zeroshot_plain": mc_chi2({"fewshot": fsc, "zeroshot_plain": zs}) if fsc and zs else None,
                  "priming_F_bench_vs_F_he": mc_chi2(fam) if all(fam.values()) else None,
                  "stages_run": sorted({r.get("ptfs_stage") for r in fs if r.get("ptfs_stage")})}
    n_up = sum(1 for t in ALL_TASKS if (out[t]["by_source"]["fewshot"]["per_draw_correct_rate"] or 0) > 0.12)
    return {"units": out, "n_tasks_fewshot_correct_rate_above_exp28_zeroshot_12pct": n_up,
            "n_tasks_ge20_correct": sum(1 for t in ALL_TASKS if not out[t]["LOW_CORRECT"])}


def l3(units: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
    """Descriptive: Kendall tau between the base and tail orderings of the non-default algorithms (units with both
    defined), and the per-event log score of a gamma-tempered q_base (gamma fitted on one half of the events, scored
    on the other; split by unit order) vs uniform / q_tail / q_assoc."""
    from scipy import stats

    taus = {}
    for t in PUSH_TASKS6:
        u = units[t]
        if u["D"] is None or len(u["nondef"]) < 3:
            continue
        a = [u["q_base"][m] for m in u["nondef"]]
        b = [u["q_tail"][m] for m in u["nondef"]]
        tau = stats.kendalltau(a, b).statistic
        taus[t] = None if tau is None or not np.isfinite(tau) else float(tau)
    ev = [e for e in events if e["event"] and e["outcomes"]]
    half_a = [e for i, e in enumerate(sorted(ev, key=lambda e: (e["unit"], e["nudge"]))) if i % 2 == 0]
    half_b = [e for i, e in enumerate(sorted(ev, key=lambda e: (e["unit"], e["nudge"]))) if i % 2 == 1]

    def temper(q: dict[str, float], g: float) -> dict[str, float]:
        z = sum(v ** g for v in q.values())
        return {k: v ** g / z for k, v in q.items()}

    def score(es: list[dict[str, Any]], g: float) -> float:
        return float(np.mean([AL.log_score(temper(e["q_base"]["q"], g), e["outcomes"]) for e in es])) if es else float("nan")
    grid = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]
    res = {"kendall_tau_base_vs_tail": taus}
    if half_a and half_b:
        g_a = max(grid, key=lambda g: score(half_a, g))
        g_b = max(grid, key=lambda g: score(half_b, g))
        held = [AL.log_score(temper(e["q_base"]["q"], g_a), e["outcomes"]) for e in half_b] + \
               [AL.log_score(temper(e["q_base"]["q"], g_b), e["outcomes"]) for e in half_a]
        res.update({"gamma_fit_half_a": g_a, "gamma_fit_half_b": g_b,
                    "heldout_logscore_qbase_gamma": float(np.mean(held)),
                    "logscore_uniform": float(np.mean([AL.log_score(AL.uniform(e["nondef"]), e["outcomes"]) for e in ev])),
                    "logscore_qtail": float(np.mean([AL.log_score(e["q_tail"]["q"], e["outcomes"]) for e in ev])),
                    "logscore_qassoc": float(np.mean([AL.log_score(e["q_assoc"]["q"], e["outcomes"]) for e in ev])),
                    "n_events": len(ev)})
    return res


def jsonable_events(ev: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for e in ev:
        r = {k: v for k, v in e.items() if k not in ("q_base", "q_tail", "q_lik", "q_lik_raw", "q_assoc")}
        for k in ("q_base", "q_tail", "q_lik", "q_lik_raw", "q_assoc"):
            if e.get(k):
                r[k] = e[k]["q"]
                r[k + "_defined"] = e[k].get("defined", True)
        out.append(r)
    return out


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("final6")
    labs = all_labels()
    fc = read_json(PRED_DIR / "forecasts_G6.json")
    units = fc["units"]
    ev = build_events(labs, units)
    write_json(RESULTS_DIR / "events_G6.json", {k: jsonable_events(v) for k, v in ev.items()})
    res: dict[str, Any] = {"primary_pooled": contest(ev["pooled"], "pooled (old + fresh) - REPLICATION"),
                           "split_fresh_only": contest(ev["fresh"], "fresh-only (outcomes unseen at commit #1)"),
                           "split_old_only": contest(ev["old"], "old-only (exp28 rows, v6 definition)")}
    pooled = [e for e in ev["pooled"] if e["event"]]
    sens = {}
    for src in ("fewshot", "exp28_pooled", "F_bench", "F_he", "stageA_plus_exp28"):
        e2 = with_ru(pooled, units, src)
        sens[f"r_u_from_{src}"] = {"hits": AL.hit_test(e2, "r_u"), "L1a": AL.l1a(e2),
                                   "L1b": AL.discordant_sign(e2, "qlik_top1", "DISCORDANT")}
    ex = [e for e in pooled if not units[e["unit"]].get("exemplar_sensitive")]
    sens["exemplar_sensitive_excluded"] = {"n_events": len(ex), "excluded_units": sorted({e["unit"] for e in pooled
                                                                                          if units[e["unit"]].get("exemplar_sensitive")}),
                                           "hits": AL.hit_test(ex, "r_u"), "L1a": AL.l1a(ex),
                                           "L1b": AL.discordant_sign(ex, "qlik_top1", "DISCORDANT"),
                                           "logscore_base_vs_tail": AL.paired_contest(AL.logscore_table(ex, ["q_base", "q_tail"]),
                                                                                      "q_base", "q_tail", noninf=True)}
    nf = [e for e in pooled if not e.get("AUDIT_FAIL")]
    sens["audit_fail_excluded"] = {"n_events": len(nf), "hits": AL.hit_test(nf, "r_u"), "L1a": AL.l1a(nf)}
    qs = read_json(RESULTS_DIR / "qlik_scores.json")
    eq = with_qwen_lik(pooled, units, qs.get("qwen_only", {}))
    sens["q_lik_from_qwen_programs"] = {"hits_qlik": AL.hit_test(eq, "qlik_top1"),
                                        "L1b": AL.discordant_sign(eq, "qlik_top1", "DISCORDANT"),
                                        "logscore_base_vs_lik": AL.paired_contest(AL.logscore_table(eq, ["q_base", "q_lik"]),
                                                                                  "q_base", "q_lik")}
    res["sensitivities"] = sens
    # provenance sign agreement: mean log-score difference base - tail in fresh vs old splits
    def sgn(c: dict[str, Any], k: str) -> float | None:
        x = (c.get("logscore_contests") or {}).get(k, {}).get("mean_diff_nats")
        return None if x is None else float(np.sign(x))
    res["provenance_sensitive"] = {k: (sgn(res["split_fresh_only"], k), sgn(res["split_old_only"], k))
                                   for k in ("base_vs_tail", "base_vs_lik_norm")}
    write_json(RESULTS_DIR / "l1_contest.json", res)
    write_json(RESULTS_DIR / "old_tally.json", old_tally())
    write_json(RESULTS_DIR / "l2.json", l2(labs, units))
    write_json(RESULTS_DIR / "push_descriptives.json", push_desc(labs, units))
    write_json(RESULTS_DIR / "pt_repertoire.json", pt_repertoire(labs, units))
    write_json(RESULTS_DIR / "l3.json", l3(units, ev["pooled"]))
    p = res["primary_pooled"]
    logger.info(f"pooled events {p.get('n_events')}; clear landings {p.get('n_clear_landing')}; "
                f"hits r_u {p.get('hits_r_u_all', {}).get('hits')}/{p.get('hits_r_u_all', {}).get('n_events')}")


if __name__ == "__main__":
    main()
