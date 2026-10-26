#!/usr/bin/env python3
"""Stage 8 analyses -> results/*.json (every number in README.md comes from these files).

base_repertoire / strata (from COMMIT #1 + the ITER1 replication check), engine_check, selection (Stage 3 dose
curves, site controls, lambda*), confirmation + claim_b (Stage 4, the frozen rule of analysis_b with the committed
sets), desharpen (Claim D), reverse (Stage 6), screen_check (Claim A, descriptive), knob_rows, commit_order_audit,
timing, costs. Rows are deduplicated by sample_id (the first labelled row is kept).
"""

from __future__ import annotations

import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger
from scipy import stats as sps

sys.path.insert(0, str(Path(__file__).resolve().parent))

import analysis_b as A  # noqa: E402
from cfg import (DATA_DIR, DEPTH, DS_ALPHAS, DS_SLOTS, E17, E22, I1E5, LAMBDAS, LOG_DIR, PRED_DIR,  # noqa: E402
                 RESULTS_DIR, ROOT, S1_SLOTS, S2_SLOTS_50, S2_SLOTS_100, TASKS15, TEMPLATE_IDS, catalogue,
                 read_json, read_jsonl, setup_logging, utc_now, write_json, write_jsonl)

LABELS = DATA_DIR / "labels.jsonl"
S2_ALL = set(S2_SLOTS_100)


def load_labels() -> list[dict[str, Any]]:
    seen, out = set(), []
    for r in read_jsonl(LABELS):
        if r["sample_id"] in seen:
            continue
        seen.add(r["sample_id"])
        out.append(r)
    return out


def sel(labs: list[dict[str, Any]], task: str, arm: str, slots: set[int] | list[int] | None = None,
        model: str | None = None) -> list[dict[str, Any]]:
    s = set(slots) if slots is not None else None
    return [r for r in labs if r["task"] == task and r["arm"] == arm and (s is None or int(r["slot"]) in s)
            and (model is None or r.get("model") == model)]


def cell(rows: list[dict[str, Any]], d: str | None, cat: list[str]) -> dict[str, Any]:
    n = len(rows)
    pr, kp, _ = A.pass_rate(rows)
    sh, ko, nc = A.off_share(rows, d, cat)
    y = [A.y_off(r, d, cat) for r in rows]
    comp = A.composition(rows)
    corr = [r["label"] for r in rows if A.is_correct(r)]
    return {"n": n, "pass": pr, "k_pass": kp, "pass_wilson": A.wilson(kp, n), "n_correct": nc, "off_share": sh,
            "k_off": ko, "off_wilson": A.wilson(ko, nc) if nc else [None, None],
            "y_rate": float(np.mean(y)) if y else None, "k_y": int(sum(y)),
            "default_share": A.default_share(rows, d)[0],
            "composition_correct": comp, "composition_attempted": A.composition(rows, correct_only=False),
            "n_other_correct": comp.get("other", 0), "n_invalid": sum(1 for r in rows if r.get("label") == "invalid"),
            "hill1_d25": A.rarefied_hill1(corr, DEPTH, 1000)["hill1"],
            "modal_correct_nondefault": (Counter(l for l in corr if l in set(cat) and l != d).most_common(1)[0][0]
                                         if any(l in set(cat) and l != d for l in corr) else None)}


# ------------------------------------------------------------------------------------------------ base repertoire
def base_repertoire(c1: dict[str, Any], labs: list[dict[str, Any]]) -> dict[str, Any]:
    out = {"per_task": c1["per_task"], "strata": c1["strata"], "n_div": c1["n_div"]}
    # replication check (descriptive): T1/T2 base chat default share vs ITER1 exp5 (BFS 49/57; Dijkstra 63/90)
    i1 = read_jsonl(I1E5 / "labelled_base_chat__baseline.jsonl")
    rep = {}
    for t, it, d in (("T1", "t1", "bfs"), ("T2", "t2", "dijkstra")):
        old = [r for r in i1 if r["task"] == it and str(r.get("passed")) == "True"]
        k_old = sum(1 for r in old if r.get("label") == d)
        mine = [r for r in sel(labs, t, "BASE_CHAT") if A.is_correct(r)]
        k_new = sum(1 for r in mine if r["label"] == d)
        tab = [[k_new, len(mine) - k_new], [k_old, len(old) - k_old]]
        p = float(sps.fisher_exact(tab)[1]) if len(mine) and len(old) else None
        rep[t] = {"this_artifact": {"default_correct": k_new, "n_correct": len(mine),
                                    "share": k_new / len(mine) if mine else None},
                  "iter1_exp5": {"default_correct": k_old, "n_correct": len(old),
                                 "share": k_old / len(old) if old else None},
                  "fisher_p_two_sided": p,
                  "note": "different prompts (ITER1 P0-P9 vs the W1-W5 twins) and labellers; descriptive only"}
    out["replication_iter1"] = rep
    return out


# ------------------------------------------------------------------------------------------------ engine check
def engine_check(labs: list[dict[str, Any]]) -> dict[str, Any]:
    e17 = read_jsonl(E17 / "data" / "labels.jsonl")
    out: dict[str, Any] = {}
    for task, seed in (("T03", 9002), ("T2", 9004)):
        for mine_arm, their_arm in (("EC_NEUTRAL", "NEUTRAL"), (f"EC_RAND{seed}_a1.0", f"RAND{seed}_a1.0")):
            mine = {(r["template"], int(r["slot"])): r for r in sel(labs, task, mine_arm)}
            theirs = {}
            for r in e17:
                if r["task"] == task and r["arm"] == their_arm:
                    k = (r["template"], int(r["sample_id"]))
                    if k[1] < 10 and k not in theirs:
                        theirs[k] = r
            keys = sorted(set(mine) & set(theirs))
            agree = sum(mine[k]["label"] == theirs[k]["label"] for k in keys)
            pagree = sum(bool(mine[k]["passed"]) == (str(theirs[k]["passed"]) == "True") for k in keys)
            same_code = sum((mine[k].get("code_sha256") or "") == theirs[k].get("code_sha256") for k in keys)
            cm = Counter(mine[k]["label"] for k in keys)
            ct = Counter(theirs[k]["label"] for k in keys)
            js = A.jsd(dict(cm), dict(ct))
            # template-resampling null within the exp17 rows
            rng = np.random.default_rng(7)
            byw = {w: [theirs[k]["label"] for k in keys if k[0] == w] for w in TEMPLATE_IDS}
            null = []
            for _ in range(1000):
                ws = rng.choice(TEMPLATE_IDS, size=5, replace=True)
                cc = Counter(l for w in ws for l in byw[w])
                null.append(A.jsd(dict(cc), dict(ct)))
            q95 = float(np.nanpercentile(null, 95))
            out[f"{task}|{mine_arm}"] = {"n_slots": len(keys), "per_slot_label_agreement": agree / max(len(keys), 1),
                                         "per_slot_pass_agreement": pagree / max(len(keys), 1),
                                         "per_slot_identical_code": same_code / max(len(keys), 1),
                                         "ours": dict(cm), "exp17_screen": dict(ct), "js": js,
                                         "null_q95": q95, "within_null": bool(js <= q95)}
    out["precision_note"] = ("exp17 rows are FP8 W8A8 (16 GB RTX 2000 Ada); this artifact runs bf16 on an RTX 4090 "
                             "(precision rule). Byte identity is not expected; agreement/JS vs a template-resampling "
                             "null quantify the precision sensitivity.")
    return out


# ------------------------------------------------------------------------------------------------ selection
def selection(c1: dict[str, Any], c2: dict[str, Any] | None, labs: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    per = c1["per_task"]
    for t in TASKS15:
        d, cat = per[t]["default"], catalogue(t)
        tw = sel(labs, t, "TWIN", S1_SLOTS, "Qwen/Qwen3-8B")
        res = {"twin_S1": cell(tw, d, cat), "stratum": per[t]["stratum"], "default": d, "beta": per[t]["beta"]}
        for arm in [f"T{l}" for l in LAMBDAS] + [f"MR{l}" for l in LAMBDAS] + ["READ1.0", "EARLY1.0", "LATE1.0"]:
            rr = sel(labs, t, arm, S1_SLOTS)
            if rr:
                c = cell(rr, d, cat)
                pairs = A.pair_rows(rr, tw)
                c["mcnemar_vs_twin_y"] = A.mcnemar_exact([A.y_off(a, d, cat) for a, _ in pairs],
                                                         [A.y_off(b, d, cat) for _, b in pairs])
                c["pass_cost_vs_twin"] = A.newcombe(c["k_pass"], c["n"], res["twin_S1"]["k_pass"],
                                                    res["twin_S1"]["n"])
                c["broken"] = A.broken(c["pass"], res["twin_S1"]["pass"] or 0.0)
                res[arm] = c
        if c2:
            res["lambda_star"] = c2["selection"].get(t, {}).get("lambda_star")
            res["lambda_prime"] = c2["selection"].get(t, {}).get("lambda_prime")
            res["MR_broken_at_lambda_star"] = c2["selection"].get(t, {}).get("MR_broken_at_lambda_star")
        out[t] = res
    # specificity (S1, point estimates as pre-registered; McNemar noise-robust version beside)
    col = c1["strata"]["BASE-COLLAPSED"]
    spec_col = {}
    for t in col:
        a, b = out[t].get("T1.0"), out[t]["twin_S1"]
        if a and a["off_share"] is not None and b["off_share"] is not None:
            spec_col[t] = {"abs_diff": abs(a["off_share"] - b["off_share"]),
                           "ok": abs(a["off_share"] - b["off_share"]) <= 0.05,
                           "moved_mcnemar": a["mcnemar_vs_twin_y"]["p_one"] < 0.05}
    spec_read = {}
    for t in TASKS15:
        a, b = out[t].get("READ1.0"), out[t]["twin_S1"]
        if a and a["off_share"] is not None and b["off_share"] is not None:
            spec_read[t] = {"abs_diff": abs(a["off_share"] - b["off_share"]),
                            "ok": abs(a["off_share"] - b["off_share"]) <= 0.05,
                            "moved_mcnemar": a["mcnemar_vs_twin_y"]["p_one"] < 0.05,
                            "granularity": 1 / max(a["n_correct"], 1)}
    n_ok_col = sum(v["ok"] for v in spec_col.values())
    specificity = {"collapsed": spec_col, "read": spec_read,
                   "collapsed_ok_frac": n_ok_col / len(spec_col) if spec_col else None,
                   "read_all_ok": all(v["ok"] for v in spec_read.values()) if spec_read else None}
    specificity["holds"] = bool((specificity["collapsed_ok_frac"] is None or specificity["collapsed_ok_frac"] >= 0.8)
                                and specificity["read_all_ok"])
    specificity["holds_noise_robust"] = bool(
        sum(not v["moved_mcnemar"] for v in spec_col.values()) >= 0.8 * max(len(spec_col), 1)
        and all(not v["moved_mcnemar"] for v in spec_read.values()))
    gate = c2["validity_gate"] if c2 else None
    return {"per_task": out, "specificity": specificity, "validity_gate": gate}


# ------------------------------------------------------------------------------------------------ confirmation
def confirmation(c1: dict[str, Any], c2: dict[str, Any], labs: list[dict[str, Any]], spec: dict[str, Any],
                 ext: bool = False) -> dict[str, Any]:
    """ext=True: the committed post-hoc power extension (COMMIT3_EXT, descriptive): decisive tasks on S2 j 10-29."""
    per = c1["per_task"]
    BD, INT = c1["strata"]["BASE-DIVERSE"], c1["strata"]["INTERMEDIATE"]
    res: dict[str, Any] = {}
    family: dict[str, float] = {}
    for t, cells in c2["stage4_plan"].items():
        if ext and t not in BD:
            continue
        d, cat = per[t]["default"], catalogue(t)
        n2 = 100 if ext else c2["s2_N"].get(t, 50)
        slots = S2_SLOTS_100 if n2 == 100 else S2_SLOTS_50
        tw = sel(labs, t, "TWIN", slots, "Qwen/Qwen3-8B")
        arms = [a for a, _ in cells if a != "TWIN"]
        T_arm = arms[0]
        r = {"decisive": t in BD, "N": n2, "lambda_star": c2["selection"][t]["lambda_star"],
             "twin_S2": cell(tw, d, cat), "arms": {}}
        Trows = sel(labs, t, T_arm, slots)
        for a in arms:
            rows = sel(labs, t, a, slots)
            c = cell(rows, d, cat)
            if a != T_arm and rows and Trows:
                pairs = A.pair_rows(Trows, rows)
                c["mcnemar_T_vs_this"] = A.mcnemar_exact([A.y_off(x, d, cat) for x, _ in pairs],
                                                         [A.y_off(y, d, cat) for _, y in pairs])
                c["template_robustness"] = A.template_robustness(Trows, rows, d, cat)
                c["y_diff_newcombe"] = A.newcombe(sum(A.y_off(x, d, cat) for x in Trows), len(Trows),
                                                  sum(A.y_off(y, d, cat) for y in rows), len(rows))
                ctl = "MR" if a.startswith("MR") and not a.startswith("MRP") else (
                    "XT" if a.startswith("XT") else "MRp")
                c["control_class"] = ctl
                if t in BD:
                    family[f"{t}|{ctl}"] = c["mcnemar_T_vs_this"]["p_one"]
            if rows and tw:
                pairs = A.pair_rows(rows, tw)
                c["mcnemar_vs_twin_y"] = A.mcnemar_exact([A.y_off(x, d, cat) for x, _ in pairs],
                                                         [A.y_off(y, d, cat) for _, y in pairs])
            r["arms"][a] = c
        res[t] = r
    holm = A.holm(family) if family else {}
    for t, r in res.items():
        r["holm"] = {k.split("|")[1]: v for k, v in holm.items() if k.startswith(t + "|")}
        if r["decisive"]:
            Tc = r["arms"][next(iter(r["arms"]))]
            mr_broke = bool(c2["selection"][t]["MR_broken_at_lambda_star"])
            r["rule"] = A.claim_b_task(beta=per[t]["beta"], r_t=per[t]["r_t"], pass_T=Tc["pass"] or 0.0,
                                       pass_twin=r["twin_S2"]["pass"] or 0.0, offshare_T=Tc["off_share"],
                                       p_holm=r["holm"], mr_broke=mr_broke,
                                       modal_T=Tc["modal_correct_nondefault"])
            if mr_broke and "MRp" not in r["holm"]:  # lambda' = None -> ISO(1) comparator
                r["rule"]["note"] = "MR broke and no unbroken MR: ISO(1) used as the pass-matched comparator"
    valid = bool(c2["validity_gate"]["valid"])
    verdict = A.claim_b_verdict(res, c1["n_div"], spec["holds"], valid)
    # sensitivities
    sens = {}
    stab = [t for t in BD if (per[t]["stratum_stability"] or 0) >= 0.8]
    sub = {t: res[t] for t in stab if t in res}
    sens["stable_stratum_only"] = A.claim_b_verdict(sub, len(stab), spec["holds"], valid)
    sens["noise_robust_specificity"] = A.claim_b_verdict(res, c1["n_div"], spec["holds_noise_robust"], valid)
    plain_div = [t for t in c1["tasks_with_default"] if per[t]["base_plain"]["stratum_plain"] == "BASE-DIVERSE"]
    sens["plain_completion_strata"] = {"BASE-DIVERSE_plain": plain_div,
                                       "tested_in_stage4": [t for t in plain_div if t in res],
                                       "n_pass_among_tested": sum(1 for t in plain_div if t in res and
                                                                  res[t].get("rule", {}).get("PASS"))}
    sens["excluding_low_confidence"] = [t for t in BD if per[t]["low_confidence"]]
    tr = {}
    for t, r in res.items():
        tr[t] = {a: c.get("template_robustness", {}).get("n_templates_arm_gt_control")
                 for a, c in r["arms"].items() if "template_robustness" in c}
    sens["template_robustness_counts"] = tr
    sens["attempt_basis_tasks"] = [t for t in BD if per[t]["beta_basis"] == "ATTEMPT"]
    # descriptive: log score of the committed landing composition vs uniform and vs the exp22 push landing
    esc = read_json(E22 / "escape.json")
    ls = {}
    for t, r in res.items():
        Tc = r["arms"][next(iter(r["arms"]))]
        d, cat = per[t]["default"], catalogue(t)
        land = [l for l, k in Tc["composition_correct"].items() for _ in range(k) if l in set(cat) and l != d]
        pred = per[t]["predicted_landing_composition"]
        uni = {m: 1 / max(len(pred), 1) for m in pred}
        push = esc.get(t, {}).get("push_landing_v4") or {}
        ls[t] = {"n_landings": len(land), "log_score_base_pred": A.log_score(land, pred),
                 "log_score_uniform": A.log_score(land, uni),
                 "log_score_push_landing": A.log_score([l for l in land if l in push], push) if push else None,
                 "n_landings_defined_under_push": sum(1 for l in land if l in push)}
    return {"per_task": res, "holm_family": family, "holm_adjusted": holm, "verdict": verdict,
            "sensitivities": sens, "landing_log_scores": ls}


# ------------------------------------------------------------------------------------------------ Claim D
def desharpen(c1: dict[str, Any], labs: list[dict[str, Any]]) -> dict[str, Any]:
    per = c1["per_task"]
    out: dict[str, Any] = {}
    for t in c1["stage_sets"]["stage5_desharpen"]:
        d, cat = per[t]["default"], catalogue(t)
        tw = sel(labs, t, "TWIN", DS_SLOTS, "Qwen/Qwen3-8B")
        twc = cell(tw, d, cat)
        r: dict[str, Any] = {"twin": twc, "cells": {}}
        a_ds = a_iso = None
        land = None
        for kind in ("DS", "ISO"):
            for a in DS_ALPHAS:
                rows = sel(labs, t, f"{kind}{a}", DS_SLOTS)
                if not rows:
                    continue
                c = cell(rows, d, cat)
                e = A.escapes(k_off=c["k_y"], n=c["n"], off_share_arm=c["off_share"],
                              off_share_twin=twc["off_share"] or 0.0, pass_arm=c["pass"] or 0.0,
                              pass_twin=twc["pass"] or 0.0, twin_k=twc["k_y"], twin_n=twc["n"])
                c.update(e)
                r["cells"][f"{kind}{a}"] = c
                if e["escapes"]:
                    if kind == "DS" and a_ds is None:
                        a_ds, land = a, c["modal_correct_nondefault"]
                    if kind == "ISO" and a_iso is None:
                        a_iso = a
        r.update({"a_ds": a_ds, "a_iso": a_iso, "a_iso_censored": a_iso is None, "ds_landing": land,
                  "r_t": per[t]["r_t"]})
        r["rule"] = A.claim_d_task(a_ds, a_iso, land, per[t]["r_t"])
        out[t] = r
    return {"per_task": out, "verdict": A.claim_d_verdict(out),
            "descriptive_only": c1["stage_sets"]["stage5_descriptive_only"]}


# ------------------------------------------------------------------------------------------------ reverse
def reverse(c1: dict[str, Any], labs: list[dict[str, Any]]) -> dict[str, Any]:
    per = c1["per_task"]
    out: dict[str, Any] = {}
    for t in c1["stage_sets"]["stage6_reverse"]:
        d, cat = per[t]["default"], catalogue(t)
        bt = sel(labs, t, "BTWIN")
        r: dict[str, Any] = {"BTWIN": cell(bt, d, cat)}
        r["BTWIN"]["default_share_attempts"] = A.default_share(bt, d, attempts=True)[0]
        for a in ("RT1.0", "BMR1.0"):
            rows = sel(labs, t, a)
            if not rows:
                continue
            c = cell(rows, d, cat)
            c["default_share_attempts"] = A.default_share(rows, d, attempts=True)[0]
            pairs = A.pair_rows(rows, bt)
            c["mcnemar_vs_BTWIN_z_default"] = A.mcnemar_exact([A.z_def(x, d) for x, _ in pairs],
                                                              [A.z_def(y, d) for _, y in pairs])
            r[a] = c
        inst = per[t]["twin_default_share"]
        if "RT1.0" in r:
            r["prediction_correct"] = A.reverse_prediction(r["RT1.0"]["default_share"], r["BTWIN"]["default_share"],
                                                           inst)
            r["prediction_attempts"] = A.reverse_prediction(r["RT1.0"]["default_share_attempts"],
                                                            r["BTWIN"]["default_share_attempts"], inst)
        out[t] = r
    met = [v["prediction_correct"]["met"] for v in out.values() if "prediction_correct" in v]
    return {"per_task": out, "n_tasks": len(out), "n_prediction_met_correct": sum(bool(m) for m in met),
            "descriptive_only": c1["stage_sets"]["stage6_descriptive_only"]}


# ------------------------------------------------------------------------------------------------ Claim A
def screen_check(c1: dict[str, Any]) -> dict[str, Any]:
    esc = read_json(E22 / "escape.json")
    per = c1["per_task"]
    ts = [t for t in TASKS15 if per[t]["beta"] is not None and t in esc]
    beta = np.array([per[t]["beta"] for t in ts])
    out: dict[str, Any] = {"tasks": ts, "label": "screen, ban unit (descriptive)"}
    rng = np.random.default_rng(11)
    for key in ("1.0", "2.0", "mean"):
        if key == "mean":
            e = np.array([np.mean([esc[t]["E_t"][a]["E_t"] for a in ("1.0", "2.0")]) for t in ts])
        else:
            e = np.array([esc[t]["E_t"][key]["E_t"] for t in ts])
        rho = float(sps.spearmanr(beta, e)[0])
        tau = float(sps.kendalltau(beta, e)[0])
        perm = [sps.spearmanr(beta, rng.permutation(e))[0] for _ in range(5000)]
        p = float((np.sum(np.array(perm) >= rho) + 1) / (len(perm) + 1))
        out[f"alpha_{key}"] = {"spearman": rho, "kendall": tau, "perm_p_one_sided": p, "E_t": dict(zip(ts, e))}
    out["collapsed_movability"] = {t: {"E_t_a1": esc[t]["E_t"]["1.0"]["E_t"], "E_t_a2": esc[t]["E_t"]["2.0"]["E_t"],
                                       "movable": esc[t].get("movable")}
                                   for t in c1["strata"]["BASE-COLLAPSED"] if t in esc}
    land = {}
    for t in ts:
        push = esc[t].get("push_landing_v4") or {}
        if not esc[t].get("movable") or not push:
            continue
        top = max(push, key=push.get)
        land[t] = {"r_t": per[t]["r_t"], "push_top1": top, "agree": per[t]["r_t"] == top,
                   "push_prob_of_r_t": push.get(per[t]["r_t"])}
    out["r_t_vs_push_landing"] = land
    return out


# ------------------------------------------------------------------------------------------------ knob rows
def knob_rows(c1: dict[str, Any], labs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    per = c1["per_task"]
    rows = []
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for r in labs:
        if r["arm"].startswith(("EC_", "PAD")):
            continue
        s = int(r["slot"])
        sset = "S1" if s < 10 else "S2"
        if r["arm"] in ("BASE_CHAT", "BASE_PLAIN", "BTWIN", "RT1.0", "BMR1.0"):
            sset = "base"
        groups.setdefault((r["task"], r["arm"], sset), []).append(r)
    for (t, a, s), rr in sorted(groups.items()):
        d, cat = per[t]["default"], catalogue(t)
        c = cell(rr, d, cat)
        ref = groups.get((t, "TWIN", s if s in ("S1", "S2") else "S1"), [])
        rc = cell(ref, d, cat) if ref else None
        cost = A.newcombe(rc["k_pass"], rc["n"], c["k_pass"], c["n"]) if rc else None
        rows.append({"task": t, "arm": a, "slots": s, "n": c["n"], "hill1_d25_correct": c["hill1_d25"],
                     "pass": c["pass"], "pass_cost_vs_twin_points": (cost["diff"] * 100 if cost and
                                                                     cost["diff"] is not None else None),
                     "pass_cost_newcombe": cost, "off_share": c["off_share"], "y_rate": c["y_rate"],
                     "composition_correct": c["composition_correct"]})
    return rows


# ------------------------------------------------------------------------------------------------ audits
def commit_order_audit(labs: list[dict[str, Any]]) -> dict[str, Any]:
    import commit as C

    v = C.verify()
    c1u = v["first_utc_by_tag"].get("COMMIT1")
    c2u = v["first_utc_by_tag"].get("COMMIT2")
    raw = read_jsonl(DATA_DIR / "instr_raw.jsonl") + read_jsonl(DATA_DIR / "basehook_raw.jsonl")
    hooked = [r for r in raw if r["arm"] not in ("TWIN", "BTWIN")]
    first_hooked = min((r["utc"] for r in hooked), default=None)
    s4 = [r for r in raw if r.get("block_id") == "S4"]
    first_s4 = min((r["utc"] for r in s4), default=None)
    return {"hash_chain": v, "commit1_utc": c1u, "commit2_utc": c2u, "first_hooked_row_utc": first_hooked,
            "first_stage4_row_utc": first_s4,
            "hooked_after_commit1": bool(first_hooked is None or (c1u and first_hooked > c1u)),
            "stage4_after_commit2": bool(first_s4 is None or (c2u and first_s4 > c2u)),
            "note": "TWIN_S2 (unhooked) rows were sampled with TWIN_S1 in instr1 (deviation D-twin-s2)."}


def timing() -> dict[str, Any]:
    rows = read_jsonl(RESULTS_DIR / "timing_batches.jsonl")
    vb = read_jsonl(RESULTS_DIR / "timing_base_vllm.jsonl")
    by: dict[str, float] = {}
    for r in rows:
        by[r["block_id"].split(":")[0]] = by.get(r["block_id"].split(":")[0], 0.0) + r["seconds"]
    return {"hf_batches": len(rows), "hf_gpu_seconds": round(sum(r["seconds"] for r in rows), 1),
            "hf_seconds_by_stage": by, "vllm_base_seconds": round(sum(r["seconds"] for r in vb), 1),
            "programs_hf": sum(r["n_rows"] for r in rows), "pad_rows": sum(r["n_pad"] for r in rows),
            "programs_vllm": sum(r["n"] for r in vb),
            "gpu_hours_total": round((sum(r["seconds"] for r in rows) + sum(r["seconds"] for r in vb)) / 3600, 3)}


def costs() -> dict[str, Any]:
    tot = {}
    tot["bench_judge_usd"] = sum(r.get("cost", 0.0) or 0.0 for r in read_jsonl(LOG_DIR / "openrouter_spend.jsonl"))
    pj = RESULTS_DIR / "openrouter_cost_paths.json"
    tot["path_judge_usd"] = (read_json(pj).get("total_usd", 0.0) if pj.exists() else 0.0)
    tot["audits_usd"] = max([r.get("running", 0.0) for r in read_jsonl(LOG_DIR / "openrouter_spend_audit.jsonl")]
                            or [0.0])
    tot["total_usd"] = float(sum(tot.values()))
    tot["cap_usd"] = 1.5
    return tot


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("analysis_final")
    labs = load_labels()
    c1 = read_json(PRED_DIR / "commit1.json")
    c2p = PRED_DIR / "commit2.json"
    c2 = read_json(c2p) if c2p.exists() else None
    write_json(RESULTS_DIR / "base_repertoire.json", base_repertoire(c1, labs))
    write_json(RESULTS_DIR / "engine_check.json", engine_check(labs))
    s = selection(c1, c2, labs)
    write_json(RESULTS_DIR / "selection.json", s)
    if c2:
        cf = confirmation(c1, c2, labs, s["specificity"])
        if any(r.get("block_id") == "S4X" for r in labs):
            cx = confirmation(c1, c2, labs, s["specificity"], ext=True)
            cf["power_extension_N100"] = {"verdict": cx["verdict"], "holm_adjusted": cx["holm_adjusted"],
                                          "per_task": cx["per_task"],
                                          "note": "COMMIT3_EXT, outcome-blind, descriptive sensitivity"}
            cf["sensitivities"]["power_extension_N100_verdict"] = cx["verdict"]
        write_json(RESULTS_DIR / "confirmation.json", cf)
        write_json(RESULTS_DIR / "claim_b.json", {"verdict": cf["verdict"], "sensitivities": cf["sensitivities"],
                                                  "specificity": s["specificity"],
                                                  "validity_gate": c2["validity_gate"],
                                                  "per_task_rule": {t: r.get("rule") for t, r in
                                                                    cf["per_task"].items()},
                                                  "holm_adjusted": cf["holm_adjusted"]})
        logger.info(f"Claim B: {cf['verdict']}")
    write_json(RESULTS_DIR / "desharpen.json", desharpen(c1, labs))
    write_json(RESULTS_DIR / "reverse.json", reverse(c1, labs))
    write_json(RESULTS_DIR / "screen_check.json", screen_check(c1))
    write_jsonl(RESULTS_DIR / "knob_rows.jsonl", knob_rows(c1, labs))
    write_json(RESULTS_DIR / "commit_order_audit.json", commit_order_audit(labs))
    write_json(RESULTS_DIR / "timing.json", timing())
    write_json(RESULTS_DIR / "costs.json", costs())
    dev = read_jsonl(RESULTS_DIR / "deviations.jsonl")
    write_json(RESULTS_DIR / "deviations.json", dev)
    logger.info("analysis_final done")


if __name__ == "__main__":
    main()
