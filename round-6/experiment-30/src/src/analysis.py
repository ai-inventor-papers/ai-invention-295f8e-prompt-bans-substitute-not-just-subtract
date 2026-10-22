#!/usr/bin/env python3
"""STEP 9 analysis (CPU). Reads data/samples_raw.jsonl + data/labels.jsonl (+ data/labels_k7.jsonl for T1), writes
data/samples.jsonl (merged row schema) and results/*.json:
  cells.json, s_a.json, s_b.json, s_c.json, landings.json, dose_axis.json, f1.json, f2.json, q_lik_existing.json,
  s_d.json, engine_checks.json (U8, U9), fp8_vs_bf16_sites.json, failure_modes.json, banned_sets_check.json.
Every number is W16A16 (bf16 weights and activations). Nothing here crosses precisions inferentially.
"""

from __future__ import annotations

import os

for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):  # 5-CPU cgroup: avoid BLAS oversubscription
    os.environ.setdefault(_v, "2")

import json
import math
from collections import Counter, defaultdict
from typing import Any

import numpy as np
from loguru import logger

import decide as D
from cfg import (CACHE_DIR, DATA_DIR, DEFAULT, E20, E24, E25, E27, PLAN_BLOCKS, PRECISION, PRED_DIR, RESULTS_DIR,
                 ROWLOG_DIR, RUNNER_UP, TEMPLATE_IDS, read_json, read_jsonl, setup_logging, wilson_ci, write_json,
                 write_jsonl)
from stats import first_divergence, mcnemar_exact

RAW = DATA_DIR / "samples_raw.jsonl"
LABELS = DATA_DIR / "labels.jsonl"
K7 = DATA_DIR / "labels_k7.jsonl"
MERGED = DATA_DIR / "samples.jsonl"


# ------------------------------------------------------------------------------------------------ merge
def merge() -> list[dict[str, Any]]:
    labs = {r["key"]: r for r in read_jsonl(LABELS)}
    k7 = {r["key"]: r for r in read_jsonl(K7)}
    out = []
    for r in read_jsonl(RAW):
        key = f"{r['task']}|{r['template']}|{r['arm']}|{r['k']}"
        lb = labs.get(key)
        if lb is None:
            continue
        row = {k: r[k] for k in ("model", "unit", "unit_kind", "arm", "site", "precision", "lambda", "alpha",
                                 "direction_seed", "template", "k", "slot", "temperature", "thinking", "prompt_sha256",
                                 "finish_reason", "n_new_tokens", "realised_disp", "token_ids", "hook_sha256",
                                 "kernel", "checkpoint", "task", "prio", "batch_id", "uniform_seed", "max_new",
                                 "batch_B")}
        lab = lb["label"]
        if lab not in ("invalid", "unresolved") and not _defines_solve(lb.get("code")):
            lab = "invalid"  # exp20 D13: the bench rule (no def solve / syntax error -> invalid) applied to every task
        row.update({"key": key, "label": lab, "labeller_source": lb["labeller_source"],
                    "passed": bool(lb["passed"]), "valid": bool(lb.get("valid")), "runtime_label": lb.get("runtime_label"),
                    "ast_label": lb.get("ast_label"), "judge_label": lb.get("judge_label"),
                    "fallback_label": lb.get("fallback_label"), "code_sha256": lb.get("code_sha256"),
                    "code": lb.get("code"), "text": r["text"]})
        if r["task"] == "T1" and key in k7:
            row.update({"label_k7": k7[key]["label_k7"], "label_ext": k7[key]["label_ext"],
                        "passed_k7": k7[key]["passed"]})
        out.append(row)
    write_jsonl(MERGED, out)
    logger.info(f"merged {len(out)} labelled rows -> {MERGED.name}")
    return out


def _defines_solve(code: str | None) -> bool:
    import ast

    if not code or "def solve" not in code:
        return False
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError):
        return False
    return any(isinstance(n, ast.FunctionDef) and n.name == "solve" for n in ast.walk(tree))


def decisive(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [r for r in rows if not str(r["arm"]).startswith(("SMOKE_", "ENG", "TWIN_X"))]


# ------------------------------------------------------------------------------------------------ cells
def hill1_rarefied(labels: list[str], depth: int = 25, n_rep: int = 200, seed: int = 0) -> dict[str, Any]:
    n = len(labels)
    if n == 0:
        return {"hill1": None, "n": 0, "flag_below_depth": True}

    def h(ls):
        c = np.array(list(Counter(ls).values()), dtype=float)
        p = c / c.sum()
        return float(np.exp(-(p * np.log(p)).sum()))
    if n <= depth:
        return {"hill1": h(labels), "n": n, "flag_below_depth": n < depth}
    rng = np.random.default_rng(seed)
    arr = np.array(labels)
    vals = [h(list(arr[rng.choice(n, depth, replace=False)])) for _ in range(n_rep)]
    return {"hill1": float(np.mean(vals)), "n": n, "flag_below_depth": False}


def cells(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        by[(r["task"], r["arm"])].append(r)
    twin_tok = {(r["task"], r["template"], r["k"]): r["token_ids"] for r in rows if r["arm"] == "TWIN"}
    out = {}
    for (t, arm), rs in sorted(by.items()):
        n = len(rs)
        y = [D.y_of(r) for r in rs]
        corr = [r["label"] for r in rs if r["passed"]]
        ident = [r["token_ids"] == twin_tok.get((t, r["template"], r["k"])) for r in rs
                 if (t, r["template"], r["k"]) in twin_tok]
        dose = [r["realised_disp"].get("disp_over_h_site_mean") for r in rs if r.get("realised_disp")]
        dose = [x for x in dose if x is not None]
        dose2 = [r["realised_disp"].get("disp_over_h_site_ratio_of_means") for r in rs if r.get("realised_disp")]
        dose2 = [x for x in dose2 if x is not None]
        dR = [r["realised_disp"].get("disp_R35") for r in rs if r.get("realised_disp")]
        dR = [x for x in dR if x is not None]
        s3kl = [r["realised_disp"]["s3"]["kl_mean_steps1_32"] for r in rs if r.get("realised_disp", {}).get("s3")]
        s3d = [r["realised_disp"]["s3"]["disp_mean"].get("35", r["realised_disp"]["s3"]["disp_mean"].get(35))
               for r in rs if r.get("realised_disp", {}).get("s3")]
        rec = {"task": t, "arm": arm, "site": rs[0]["site"], "alpha": rs[0]["alpha"], "n": n,
               "pass": float(np.mean([r["passed"] for r in rs])),
               "pass_ci": list(wilson_ci(sum(r["passed"] for r in rs), n)),
               "invalid": float(np.mean([r["label"] == "invalid" for r in rs])),
               "other": float(np.mean([r["label"] == "other" for r in rs])),
               "unresolved": float(np.mean([r["label"] == "unresolved" for r in rs])),
               "y": int(sum(y)), "share_correct_off_default": float(np.mean(y)),
               "share_ci": list(wilson_ci(int(sum(y)), n)),
               "composition_attempted": dict(Counter(r["label"] for r in rs)),
               "composition_correct": dict(Counter(corr)),
               "byte_identical_vs_twin": float(np.mean(ident)) if ident else None,
               "hill1_correct_rarefied25": hill1_rarefied(corr),
               "finish": dict(Counter(r["finish_reason"] for r in rs)),
               "length_truncated_share": float(np.mean([r["finish_reason"] == "length" for r in rs])),
               "dose_disp_over_h_mean_of_ratios": float(np.mean(dose)) if dose else None,
               "dose_disp_over_h_ratio_of_means": float(np.mean(dose2)) if dose2 else None,
               "disp_R35_median": float(np.median(dR)) if dR else None,
               "s3_kl_mean_steps1_32": float(np.mean(s3kl)) if s3kl else None,
               "s3_disp35_vs_shadow_mean": float(np.mean([x for x in s3d if x is not None])) if s3d else None,
               "precision": PRECISION}
        out[f"{t}|{arm}"] = rec
    write_json(RESULTS_DIR / "cells.json", out)
    return out


# ------------------------------------------------------------------------------------------------ S-b extras
def s_b_full(rows: list[dict[str, Any]]) -> dict[str, Any]:
    main = D.s_b(rows)
    res = {"primary": main, "S0_only": D.s_b(rows, indicator=("S0",)), "S4_only": D.s_b(rows, indicator=("S4",))}
    plac = [D.s_b(rows, shuffle_seed=s) for s in range(200)]
    lo = [p["mh"]["ci"][0] for p in plac if p.get("mh")]
    res["placebo_shuffled_TS_within_task"] = {
        "n": len(plac), "share_ci_excludes_1": float(np.mean([(x is not None and np.isfinite(x) and x > 1)
                                                             for x in lo])),
        "median_or": float(np.nanmedian([p["mh"]["or"] for p in plac if p.get("mh")]))}
    # exp20-style logistic transmission model: y ~ log disp_R35 + site + template + task (L2, sklearn)
    from sklearn.linear_model import LogisticRegression

    pr = [r for r in rows if r["task"] in ("T03", "T10", "T2") and r["site"] in ("S0", "S4", "S5", "S1", "S1E", "S2")
          and r.get("realised_disp", {}).get("disp_R35")]
    if pr:
        sites = ["S0", "S4", "S5", "S1", "S1E", "S2"]
        X, Y = [], []
        for r in pr:
            x = [math.log(max(float(r["realised_disp"]["disp_R35"]), 1e-6))]
            x += [1.0 if r["site"] == s else 0.0 for s in sites[1:]]
            x += [1.0 if r["template"] == w else 0.0 for w in TEMPLATE_IDS[1:]]
            x += [1.0 if r["task"] == t else 0.0 for t in ("T10", "T2")]
            X.append(x)
            Y.append(D.y_of(r))
        X, Y = np.array(X), np.array(Y)
        names = ["log_disp_R35"] + [f"site_{s}_vs_S0" for s in sites[1:]] + [f"tmpl_{w}" for w in TEMPLATE_IDS[1:]] + \
                ["task_T10", "task_T2"]
        if Y.min() != Y.max():
            m = LogisticRegression(C=10.0, max_iter=5000).fit(X, Y)
            coef = dict(zip(names, m.coef_[0].tolist()))
            rng = np.random.default_rng(0)
            boots = []
            for _ in range(200):
                ii = rng.integers(0, len(Y), len(Y))
                if Y[ii].min() == Y[ii].max():
                    continue
                boots.append(LogisticRegression(C=10.0, max_iter=5000).fit(X[ii], Y[ii]).coef_[0])
            B = np.array(boots)
            res["logistic_transmission"] = {"coef": coef, "ci95": {n_: [float(np.quantile(B[:, j], 0.025)),
                                                                        float(np.quantile(B[:, j], 0.975))]
                                                                   for j, n_ in enumerate(names)},
                                            "n_rows": int(len(Y)), "n_y": int(Y.sum()), "penalty": "L2, C = 10"}
    return res


# ------------------------------------------------------------------------------------------------ landings
def landings(cl: dict[str, Any]) -> dict[str, Any]:
    from scipy.stats import binomtest

    out: dict[str, Any] = {}
    for t in ("T03", "T10", "T2"):
        K = len(D.CATALOGUE[t])
        p0 = 1.0 / (K - 1)
        ru = RUNNER_UP[t]
        moving = []
        ev_total = ev_ru = 0
        for key, c in cl.items():
            if c["task"] != t or c["arm"] == "TWIN":
                continue
            offc = {a: n for a, n in c["composition_correct"].items() if a in D.CATALOGUE[t] and a != DEFAULT[t]}
            tot = sum(offc.values())
            ev_total += tot
            ev_ru += offc.get(ru, 0)
            if tot >= 5:
                modal = max(offc, key=lambda a: (offc[a], a == ru))
                moving.append({"cell": key, "n_off_default_correct": tot, "modal": modal, "is_runner_up": modal == ru,
                               "composition": offc})
        k_cells = sum(m["is_runner_up"] for m in moving)
        out[t] = {"runner_up": ru, "K": K, "chance": p0, "moving_cells": moving,
                  "per_cell": {"n_cells": len(moving), "modal_is_runner_up": k_cells,
                               "p_binom_vs_chance": float(binomtest(k_cells, len(moving), p0, alternative="greater")
                                                          .pvalue) if moving else None,
                               "all_cells_hit": bool(moving) and k_cells == len(moving)},
                  "per_event": {"n_events": ev_total, "n_runner_up": ev_ru,
                                "share": ev_ru / ev_total if ev_total else None,
                                "p_binom_vs_chance": float(binomtest(ev_ru, ev_total, p0, alternative="greater").pvalue)
                                if ev_total else None}}
    out["prediction_ii"] = {t: out[t]["per_cell"]["all_cells_hit"] for t in ("T03", "T10")}
    write_json(RESULTS_DIR / "landings.json", out)
    return out


# ------------------------------------------------------------------------------------------------ dose axis
def dose_axis(rows: list[dict[str, Any]]) -> dict[str, Any]:
    from sklearn.linear_model import LogisticRegression

    out: dict[str, Any] = {}
    for t in ("T03", "T10", "T2"):
        s0 = [r for r in rows if r["task"] == t and r["site"] == "S0"]
        ref = {}
        for a in (1.0, 2.0):
            v = [r["realised_disp"]["disp_over_h_site_mean"] for r in s0 if r["alpha"] == a and
                 r["realised_disp"].get("disp_over_h_site_mean") is not None]
            if v:
                ref[a] = float(np.mean(v))
        res = {"S0_residual_fraction": {f"{a:g}": v for a, v in ref.items()}, "sites": {}}
        for s in ("S0", "S4", "S5", "S1", "S2", "S1E"):
            rs = [r for r in rows if r["task"] == t and r["site"] == s and
                  r["realised_disp"].get("disp_over_h_site_mean")]
            if len(rs) < 10:
                continue
            x = np.log(np.array([r["realised_disp"]["disp_over_h_site_mean"] for r in rs]))[:, None]
            y = np.array([D.y_of(r) for r in rs])
            rec = {"n": len(rs), "y": int(y.sum()), "frac_range": [float(np.exp(x.min())), float(np.exp(x.max()))],
                   "mean_frac_by_alpha": {f"{a:g}": float(np.mean([r["realised_disp"]["disp_over_h_site_mean"]
                                                                   for r in rs if r["alpha"] == a]))
                                          for a in sorted({r["alpha"] for r in rs})}}
            if y.min() != y.max():
                m = LogisticRegression(C=100.0, max_iter=5000).fit(x, y)
                rec["slope_log_frac"] = float(m.coef_[0][0])
                rec["intercept"] = float(m.intercept_[0])
                rec["share_at_S0_fraction"] = {f"{a:g}": float(m.predict_proba([[math.log(v)]])[0, 1])
                                               for a, v in ref.items()}
                rec["extrapolated"] = {f"{a:g}": not (rec["frac_range"][0] <= v <= rec["frac_range"][1])
                                       for a, v in ref.items()}
            else:
                rec["share_at_S0_fraction"] = {f"{a:g}": float(y.mean()) for a in ref}
                rec["note"] = "constant outcome; no fit"
            res["sites"][s] = rec
        out[t] = res
    write_json(RESULTS_DIR / "dose_axis.json", out)
    return out


# ------------------------------------------------------------------------------------------------ F1
def code_start_of(tok_texts: list[str]) -> int | None:
    from stats import code_start

    return code_start(tok_texts)


def f1(rows: list[dict[str, Any]], tok: Any) -> dict[str, Any]:
    from scipy.stats import mannwhitneyu

    twin = {(r["task"], r["template"], r["k"]): r for r in rows if r["arm"] == "TWIN"}
    pairs_change, pairs_keep = [], []
    cs_cache: dict[tuple, int | None] = {}
    for r in rows:
        if r["arm"] == "TWIN" or r["site"] in ("TOP5", "TOP3"):
            continue
        tw = twin.get((r["task"], r["template"], r["k"]))
        if tw is None or not r["valid"] or not tw["valid"] or r["label"] in ("invalid", "unresolved") or \
                tw["label"] in ("invalid", "unresolved"):
            continue
        key = (tw["task"], tw["template"], tw["k"])
        if key not in cs_cache:
            cs_cache[key] = code_start_of([tok.decode([i]) for i in tw["token_ids"][:64]])
        cs = cs_cache[key]
        if cs is None:
            continue
        fd = first_divergence(tw["token_ids"], r["token_ids"])
        d = fd - cs
        rec = {"task": r["task"], "site": r["site"], "alpha": r["alpha"], "first_div": fd, "code_start": cs, "d": d,
               "y": D.y_of(r)}
        if r["label"] != tw["label"]:
            pairs_change.append(rec)
        elif r["token_ids"] != tw["token_ids"]:
            pairs_keep.append(rec)
    n = len(pairs_change)
    early = sum(1 for p in pairs_change if p["d"] < D.F1_TOKENS)
    res = {"decision": D.f1_decision(n, early),
           "n_d_negative": sum(1 for p in pairs_change if p["d"] < 0),
           "by_site": {}, "control_label_preserving": {}, "subset_correct_off_default": {}}
    for s in sorted({p["site"] for p in pairs_change}):
        ps = [p for p in pairs_change if p["site"] == s]
        e = sum(1 for p in ps if p["d"] < D.F1_TOKENS)
        res["by_site"][s] = {"n": len(ps), "early": e, "share": e / len(ps), "ci": list(wilson_ci(e, len(ps))),
                             "median_d": float(np.median([p["d"] for p in ps]))}
    ke = sum(1 for p in pairs_keep if p["d"] < D.F1_TOKENS)
    res["control_label_preserving"] = {
        "n": len(pairs_keep), "early": ke, "share": ke / len(pairs_keep) if pairs_keep else None,
        "median_d_change": float(np.median([p["d"] for p in pairs_change])) if pairs_change else None,
        "median_d_keep": float(np.median([p["d"] for p in pairs_keep])) if pairs_keep else None,
        "mannwhitney_p_change_earlier": float(mannwhitneyu([p["d"] for p in pairs_change], [p["d"] for p in pairs_keep],
                                                           alternative="less").pvalue)
        if pairs_change and pairs_keep else None}
    sub = [p for p in pairs_change if p["y"] == 1]
    se = sum(1 for p in sub if p["d"] < D.F1_TOKENS)
    res["subset_correct_off_default"] = {"n": len(sub), "early": se, "share": se / len(sub) if sub else None}
    # placebo: re-pair pushed rows with twin rows of other slots (same task, template) -> early share should drop
    rng = np.random.default_rng(0)
    tw_by = defaultdict(list)
    for (t, w, k), tr in twin.items():
        tw_by[(t, w)].append(tr)
    plc = []
    for r in rows:
        if r["arm"] == "TWIN" or r["site"] in ("TOP5", "TOP3") or not r["valid"]:
            continue
        cands = [x for x in tw_by[(r["task"], r["template"])] if x["k"] != r["k"] and x["valid"]]
        if not cands:
            continue
        tw = cands[int(rng.integers(len(cands)))]
        if tw["label"] == r["label"]:
            continue
        key = (tw["task"], tw["template"], tw["k"])
        if key not in cs_cache:
            cs_cache[key] = code_start_of([tok.decode([i]) for i in tw["token_ids"][:64]])
        cs = cs_cache[key]
        if cs is None:
            continue
        plc.append(first_divergence(tw["token_ids"], r["token_ids"]) - cs)
    res["placebo_repaired_across_slots"] = {"n": len(plc), "share_early": float(np.mean([d < D.F1_TOKENS for d in plc]))
                                            if plc else None}
    res["pairs_change"] = pairs_change
    write_json(RESULTS_DIR / "f1.json", res)
    return res


# ------------------------------------------------------------------------------------------------ F2
def f2() -> dict[str, Any]:
    raw_p = RESULTS_DIR / "q_lik_raw.json"
    if not raw_p.exists():
        return {"status": "not run"}
    raw = read_json(raw_p)
    rows = raw["rows"]
    rep = read_json(E24 / "results" / "base_repertoire.json")["per_task"]
    ex = read_json(E25 / "results" / "extra_arm_a.json")
    by = defaultdict(list)
    for r in rows:
        by[(r["task"], r["alg"], r["w"])].append(r)
    tasks = sorted({r["task"] for r in rows})
    qlik: dict[str, Any] = {}
    f2res: dict[str, Any] = {}
    for t in tasks:
        algs = sorted({r["alg"] for r in rows if r["task"] == t})
        Dd = rep[t]["default"]
        ru = rep[t]["r_t"]
        per_alg = {}
        for a in algs:
            lp = [np.mean([x["lp48"] for x in by[(t, a, w)]]) for w in TEMPLATE_IDS if by[(t, a, w)]]
            tokm = [np.mean([x["lp_tok_mean"] for x in by[(t, a, w)] if x["lp_tok_mean"] is not None])
                    for w in TEMPLATE_IDS if by[(t, a, w)]]
            per_alg[a] = {"mean_lp48": float(np.mean(lp)), "per_template": [float(x) for x in lp],
                          "mean_lp_per_token": float(np.mean(tokm)),
                          "n_programs": len({x["prog"] for w in TEMPLATE_IDS for x in by[(t, a, w)]})}
        nondef = [a for a in algs if a != Dd]
        z = np.array([per_alg[a]["mean_lp_per_token"] for a in nondef]) if nondef else np.zeros(0)
        soft = (np.exp(z - z.max()) / np.exp(z - z.max()).sum()).tolist() if len(z) else []
        top1 = nondef[int(np.argmax(z))] if nondef else None
        flagged = False
        if ru is None or ru not in per_alg:
            flagged = ru is None
            ru_used = top1 if ru is None else None
        else:
            ru_used = ru
        qlik[t] = {"default": Dd, "r_t": ru, "r_u_used": ru_used, "r_u_from_qlik_top1": flagged,
                   "per_algorithm": per_alg, "softmax_per_token_over_nondefault": dict(zip(nondef, soft)),
                   "top1_nondefault": top1}
        if Dd not in per_alg or ru_used is None or ru_used not in per_alg:
            f2res[t] = {"m": None, "verdict": "UNDEFINED (< 3 programs for the default or the runner-up)",
                        "default": Dd, "r_u": ru_used}
            continue
        mw = []
        sd_pairs = []
        for w in TEMPLATE_IDS:
            dl = [x["lp48"] for x in by[(t, Dd, w)]]
            rl = [x["lp48"] for x in by[(t, ru_used, w)]]
            mw.append(np.mean(dl) - np.mean(rl))
            sd_pairs += [x["lp48"] - x["lp48_rep2"] for x in by[(t, Dd, w)] + by[(t, ru_used, w)]]
        m = float(np.mean(mw))
        # scoring SD of m: per-program rescoring differences propagated to the template-mean contrast
        sd_prog = float(np.std(sd_pairs) / math.sqrt(2)) if sd_pairs else float("nan")
        nD = max(1, per_alg[Dd]["n_programs"])
        nR = max(1, per_alg[ru_used]["n_programs"])
        sd_m = sd_prog * math.sqrt(1 / nD + 1 / nR) / math.sqrt(len(TEMPLATE_IDS))
        m_lme = float(np.mean([lme(np.array([x["lp48"] for x in by[(t, Dd, w)]])) -
                               lme(np.array([x["lp48"] for x in by[(t, ru_used, w)]])) for w in TEMPLATE_IDS]))
        m_tok = float(np.mean([np.mean([x["lp_tok_mean"] for x in by[(t, Dd, w)]]) -
                               np.mean([x["lp_tok_mean"] for x in by[(t, ru_used, w)]]) for w in TEMPLATE_IDS]) * 48)
        forks = []
        for w in TEMPLATE_IDS:
            for xd in by[(t, Dd, w)]:
                for xr in by[(t, ru_used, w)]:
                    a_, b_ = xd["lp_tokens"], xr["lp_tokens"]
                    # identical prefix of code TOKENS is not stored; the per-token log-probs coincide on the shared
                    # prefix, so the first index where they differ is the fork (exact under teacher forcing)
                    # j = 0 is a fork too: both continuations share the prompt and the fence line
                    j = next((i for i in range(min(len(a_), len(b_))) if abs(a_[i] - b_[i]) > 1e-4), None)
                    if j is not None:
                        forks.append(a_[j] - b_[j])
        m_all_terms = []
        for a in algs:
            if a == Dd:
                continue
            ma = float(np.mean([np.mean([x["lp48"] for x in by[(t, Dd, w)]]) -
                                np.mean([x["lp48"] for x in by[(t, a, w)]]) for w in TEMPLATE_IDS]))
            m_all_terms.append(ma)
        m_all = float(-np.log(np.sum(np.exp(-np.array(m_all_terms))))) if m_all_terms else None
        dec = D.f2_decision(m, sd_m)
        f2res[t] = {**dec, "default": Dd, "r_u": ru_used, "r_u_flagged_qlik_top1": flagged, "m_per_template":
                    [float(x) for x in mw], "scoring_sd_per_program": sd_prog, "m_lme": m_lme, "m_tok": m_tok,
                    "m_fork_median": float(np.median(forks)) if forks else None, "n_fork_pairs": len(forks),
                    "m_all": m_all, "n_default_programs": nD, "n_runner_up_programs": nR,
                    "E_bf16_exp25": (ex.get(t) or {}).get("E"),
                    "E_fp8_exp22": float(np.mean(ex[t]["iter4_E1_E2"])) if ex.get(t, {}).get("iter4_E1_E2") else None}
    # thinking-on T2
    th_p = RESULTS_DIR / "f2_thinking_raw.json"
    if th_p.exists():
        th = read_json(th_p)
        ms = [x["m"] for x in th["traces"] if x.get("completed") and x.get("m") is not None]
        f2res["T2_thinking_on"] = {"m_think_median": float(np.median(ms)) if ms else None, "n_completed": len(ms),
                                   "n_traces": len(th["traces"]),
                                   "verdict": D.f2_decision(float(np.median(ms)), None)["verdict"] if ms else
                                   "NOT COMPUTABLE (no completed trace)", "traces": th["traces"]}
    # descriptive M screen: Spearman of m with E (two rows, never pooled)
    from scipy.stats import spearmanr

    scr = {}
    for key in ("E_bf16_exp25", "E_fp8_exp22"):
        pts = [(v["m"], v[key]) for t, v in f2res.items() if isinstance(v, dict) and v.get("m") is not None and
               v.get(key) is not None]
        if len(pts) >= 4:
            rho = spearmanr([p[0] for p in pts], [p[1] for p in pts])
            scr[key] = {"rho": float(rho.correlation), "p": float(rho.pvalue), "n_tasks": len(pts)}
    f2res["M_screen_spearman_m_vs_E"] = scr
    f2res["prediction_v"] = {t: (f2res.get(t, {}).get("m") or 0) > D.F2_BOUND for t in ("T2", "T03", "T1")}
    f2res["note"] = ("same-seed rows of exp21/exp27 ran on FP8 with top-k 10; top-k only lowers p_alt, so the bound "
                     "is conservative; cross-engine caveat")
    write_json(RESULTS_DIR / "f2.json", f2res)
    write_json(RESULTS_DIR / "q_lik_existing.json", {"precision": PRECISION, "tasks": qlik,
                                                       "n_programs": raw["n_programs"],
                                                       "program_sources": raw.get("program_sources")})
    return f2res


def lme(x: np.ndarray) -> float:
    m = float(np.max(x))
    return m + float(np.log(np.mean(np.exp(x - m))))


# ------------------------------------------------------------------------------------------------ S-d
def load_rowlog_states(task: str, arm: str, l: int) -> dict[str, np.ndarray]:
    p = ROWLOG_DIR / f"{task}__{arm}.npz"
    if not p.exists():
        return {}
    z = np.load(p, allow_pickle=True)
    if f"smean{l}" not in z.files:
        return {}
    return {str(k): v for k, v in zip(z["key"], z[f"smean{l}"])}


def s_d(rows: list[dict[str, Any]], out_name: str = "s_d.json") -> dict[str, Any]:
    import geometry as G

    bs = read_json(PRED_DIR / "banned_sets.json")["sets"]
    ps = np.load(CACHE_DIR / "push_states.npz")
    idx = D.cell_index(rows)
    out: dict[str, Any] = {}
    for key in ("T03|TOP5", "T03|TOP3", "T10|TOP5", "T1|TOP5"):
        t, site = key.split("|")
        banned = bs[key]["banned"]
        lab_field = "label_k7" if t == "T1" else "label"
        survs = {"K7": G.T1_SURV7, "ext": G.T1_SURV_EXT} if t == "T1" else {"S": bs[key]["survivors"]}
        res: dict[str, Any] = {"banned": banned, "survivors": survs, "arms": {}}

        def zvec(cell):
            outz = {}
            for s, r in cell.items():
                lab = r.get(lab_field) if t == "T1" else r["label"]
                ok = r.get("passed_k7", r["passed"]) if t == "T1" else r["passed"]
                outz[s] = (bool(ok), lab, r.get("label_ext") if t == "T1" else r["label"])
            return outz
        twin = zvec(idx.get((t, "TWIN"), {}))
        for a in (1.0, 2.0, 4.0):
            push = zvec(idx.get((t, f"{site}_a{a:g}"), {}))
            rc = zvec(idx.get((t, f"S0_a{a:g}"), {}))
            if not push:
                continue

            def summ(z):
                corr = [lab for ok, lab, _ in z.values() if ok]
                corr_ext = [le for ok, _, le in z.values() if ok]
                av = sum(1 for lab in corr if lab not in banned)
                av_cat = sum(1 for le in corr_ext if le not in banned and le not in ("other", "invalid", "unresolved",
                                                                                     None))
                return {"n": len(z), "n_correct": len(corr), "avoid": av,
                        "avoidance": av / len(corr) if corr else None,
                        "avoidance_ci": list(wilson_ci(av, len(corr))) if corr else None,
                        "avoid_to_named_catalogue_algorithm": av_cat,
                        "composition_correct": dict(Counter(corr)),
                        "composition_correct_ext": dict(Counter(corr_ext)) if t == "T1" else None,
                        "on_survivor": {nm: sum(1 for lab in (corr if nm != "ext" else corr_ext) if lab in sv)
                                        for nm, sv in survs.items()}}

            def mcn(z1, z2):
                sh = sorted(set(z1) & set(z2))
                f = lambda z, s: int(z[s][0] and z[s][1] not in banned)  # noqa: E731
                b = sum(1 for s in sh if f(z1, s) == 1 and f(z2, s) == 0)
                c = sum(1 for s in sh if f(z1, s) == 0 and f(z2, s) == 1)
                return {"n_shared": len(sh), "b": b, "c": c, "p": mcnemar_exact(b, c)}
            res["arms"][f"{a:g}"] = {"push": summ(push), "random_control": summ(rc) if rc else None,
                                     "twin": summ(twin), "push_vs_random_control": mcn(push, rc) if rc else None,
                                     "push_vs_twin": mcn(push, twin)}
            # edge test
            for nm, sv in survs.items():
                if len(sv) < 2:
                    res["arms"][f"{a:g}"][f"edge_test_{nm}"] = {"computable": False,
                                                                "reason": "NOT COMPUTABLE BY CONSTRUCTION (|S| = 1)"}
        # geometry: forced points (named + masked) at blocks 18, 23
        F = G.load_forced(t)
        geo_res: dict[str, Any] = {}
        for blk in (18, 23):
            sp = G.pca_space(F, blk)
            named = F["kinds"] == "named"
            core_mask = np.ones(len(F["algs"]), dtype=bool) if t != "T1" else named
            Pc = sp["proj"](F["X"][core_mask, G.BI[blk]])
            algs = F["algs"][core_mask]
            extra, extra_meta = [], []
            for jw, w in enumerate(TEMPLATE_IDS):
                extra.append(sp["proj"](F["twin"][jw, G.BI[blk]])[0])
                extra_meta.append({"kind": "twin", "w": w})
                for a in (1.0, 2.0, 4.0):
                    k_ = f"{t}|{site}|{w}|{a:g}|{blk}"
                    if k_ in ps.files:
                        extra.append(sp["proj"](ps[k_])[0])
                        extra_meta.append({"kind": "push", "w": w, "alpha": a})
            for a in (1.0, 2.0, 4.0):
                st = load_rowlog_states(t, f"S0_a{a:g}", blk)
                for kk, v in sorted(st.items())[:30]:
                    extra.append(sp["proj"](v)[0])
                    extra_meta.append({"kind": "random_control", "alpha": a, "key": kk})
            P = np.vstack([Pc, np.array(extra)]) if extra else Pc
            gres = G.geodesics(P, len(Pc))
            k_use = gres["chosen_k"] or 15
            names = sorted(set(algs))
            ksweep = {}
            for k in (5, 10, 15):
                geo = gres[k]["geo"]
                M = G.centroid_geo(Pc, algs, geo[:len(Pc), :len(Pc)], names)
                ksweep[k] = {"connected": gres[k]["connected"], "centroid_geodesic": M.tolist()}
            geo = gres[k_use]["geo"]
            M = np.array(ksweep[k_use]["centroid_geodesic"])
            Y, stress = G.mds2(geo)
            try:
                from sklearn.manifold import Isomap

                iso = Isomap(n_neighbors=k_use, n_components=2).fit(Pc)
                iso_err = float(iso.reconstruction_error())
            except Exception as e:  # noqa: BLE001
                iso_err = None
                logger.warning(f"isomap failed: {e}")
            ban_idx = [names.index(b) for b in banned if b in names]
            dist_to_banned = {s: float(min(M[names.index(s), j] for j in ban_idx)) for s in names
                              if s not in banned and ban_idx}
            # nearest-centroid map agreement across k (sanity)
            geo_res[f"block{blk}"] = {"k_used": k_use, "k_sweep": {str(k): {"connected": v["connected"]}
                                                                   for k, v in ksweep.items()},
                                      "centroid_names": names, "centroid_geodesic": M.tolist(),
                                      "dist_survivor_to_nearest_banned": dist_to_banned,
                                      "mds_stress1": stress, "isomap_reconstruction_error": iso_err,
                                      "pca_explained_50": sp["explained"],
                                      "separability": G.separability(F, blk, None if t != "T1" else "named"),
                                      "embedding": {"points": Y.tolist(), "core_algs": algs.tolist(),
                                                    "extra_meta": extra_meta}}
        res["geometry"] = geo_res
        # edge tests where |S| >= 2 (block 18 primary, 23 beside)
        for a in (1.0, 2.0, 4.0):
            arm_ = res["arms"].get(f"{a:g}")
            if not arm_:
                continue
            for nm, sv in survs.items():
                if len(sv) < 2:
                    continue
                cell = idx.get((t, f"{site}_a{a:g}"), {})
                lf = "label_k7" if (t == "T1" and nm == "K7") else ("label_ext" if t == "T1" else "label")
                pf = "passed_k7" if t == "T1" else "passed"
                land = [r.get(lf) for r in cell.values() if r.get(pf) and r.get(lf) in sv]
                et = {}
                for blk in (18, 23):
                    dtb = geo_res[f"block{blk}"]["dist_survivor_to_nearest_banned"]
                    if all(s in dtb for s in sv):
                        et[f"block{blk}"] = G.edge_test(land, sv, dtb)
                    else:
                        et[f"block{blk}"] = {"computable": False, "reason": "survivor centroid missing"}
                arm_[f"edge_test_{nm}"] = et
        # push progress (pre-sampling) with the second, stable normalisation t' = <s_push - s_twin, v> / ||c_S - c_B||
        pp = read_json(RESULTS_DIR / "push_progress.json")[key]
        surv_pp = bs[key]["survivors"] if t != "T1" else G.T1_SURV_EXT
        for blk in (18, 23):
            sp = G.pca_space(F, blk)
            c = G.centroids(F, "named")
            cS = sp["proj"](np.mean([c[s_][G.BI[blk]] for s_ in surv_pp], 0))[0]
            cB = sp["proj"](np.mean([c[b][G.BI[blk]] for b in banned], 0))[0]
            gap = float(np.linalg.norm(cS - cB))
            v = (cS - cB) / max(gap, 1e-12)
            tw_proj = {w: sp["proj"](F["twin"][jw, G.BI[blk]])[0] for jw, w in enumerate(TEMPLATE_IDS)}
            tp = {}
            for a in (1.0, 2.0, 4.0):
                vals = []
                for w in TEMPLATE_IDS:
                    k_ = f"{t}|{site}|{w}|{a:g}|{blk}"
                    if k_ in ps.files:
                        vals.append(float((sp["proj"](ps[k_])[0] - tw_proj[w]) @ v) / max(gap, 1e-12))
                tp[f"{a:g}"] = float(np.mean(vals)) if vals else None
            twin_pos = float(np.mean([float((tw_proj[w] - cB) @ v) / max(gap, 1e-12) for w in TEMPLATE_IDS]))
            pp[f"block{blk}"]["t_prime_over_centroid_gap"] = tp
            pp[f"block{blk}"]["twin_position_on_axis_B0_S1"] = twin_pos
            pp[f"block{blk}"]["centroid_gap_pca"] = gap
        res["push_progress"] = pp
        out[key] = res
    out["prediction_vi"] = {
        "T03_top5_avoidance_below_0.5_at_alpha_le_2": all(
            (out["T03|TOP5"]["arms"].get(a, {}).get("push", {}).get("avoidance") or 0) < 0.5 for a in ("1", "2")),
        "T1_push_stays_on_bfs": all(
            (max((out["T1|TOP5"]["arms"].get(a, {}).get("push", {}).get("composition_correct") or {"bfs": 1}).items(),
                 key=lambda kv: kv[1])[0] == "bfs") for a in ("1", "2", "4")
            if out["T1|TOP5"]["arms"].get(a, {}).get("push", {}).get("n_correct"))}
    write_json(RESULTS_DIR / out_name, out)
    return out


def s_d_audit_relabelled(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Sensitivity: correct 'other' programs that the novelty audit's manual pass classed as a CATALOGUE VARIANT of
    counting sort (judges' closest known algorithm: counting_sort) are relabelled counting_sort; S-d is recomputed."""
    from cfg import AUDIT_DIR

    pool = read_json(AUDIT_DIR / "novelty_audit_pool.json")["records"]
    manual = {r["id"]: r for r in read_jsonl(AUDIT_DIR / "manual_pass.jsonl")}
    relab = {}
    for x in pool:
        ca = {(x.get("judge_A") or {}).get("closest_known_algorithm"),
              (x.get("judge_B") or {}).get("closest_known_algorithm")}
        if manual.get(x["id"], {}).get("verdict") == "CATALOGUE VARIANT" and "counting_sort" in ca:
            relab[(x["task"], x["code_sha256"])] = "counting_sort"
    rr = []
    for r in rows:
        k = (r["task"], r.get("code_sha256"))
        if r["label"] == "other" and k in relab:
            r = dict(r, label=relab[k], label_audit_relabelled=True)
        rr.append(r)
    res = s_d(rr, out_name="s_d_audit_relabelled.json")
    res["n_relabelled_programs"] = len(relab)
    write_json(RESULTS_DIR / "s_d_audit_relabelled.json", res)
    return res


# ------------------------------------------------------------------------------------------------ engine checks
def engine_checks(all_rows: list[dict[str, Any]]) -> dict[str, Any]:
    from scipy.stats import fisher_exact

    e25 = read_jsonl(E25 / "data" / "samples.jsonl")
    out: dict[str, Any] = {}
    for t, arm, e25arm, rec in (("T03", "ENG_r9002_a1", "ECBAN_d9002_a1.0", 41), ("T2", "ENG_r9004_a1",
                                                                                 "ECBAN_d9004_a1.0", 19)):
        rs = [r for r in all_rows if r["task"] == t and r["arm"] == arm]
        ref = {(r["template"], int(r["slot"])): r for r in e25 if r["arm"] == e25arm}
        comp = Counter(r["label"] for r in rs)
        refc = Counter(r["label"] for r in ref.values())
        off = sum(1 for r in rs if r["passed"] and r["label"] != DEFAULT[t])
        agree = [ref[(r["template"], int(r["k"]))]["label"] == r["label"] for r in rs if (r["template"], int(r["k"]))
                 in ref]
        ident = [ref[(r["template"], int(r["k"]))]["code"] == r["code"] for r in rs if (r["template"], int(r["k"]))
                 in ref]
        labs = sorted(set(comp) | set(refc))
        p = np.array([comp[l] for l in labs], float) + 1e-12
        q = np.array([refc[l] for l in labs], float) + 1e-12
        p, q = p / p.sum(), q / q.sum()
        m = (p + q) / 2
        js = float(0.5 * (p * np.log(p / m)).sum() + 0.5 * (q * np.log(q / m)).sum())
        fp = float(fisher_exact([[off, len(rs) - off], [rec, 50 - rec]])[1]) if rs else None
        out[f"U8_{t}"] = {"n": len(rs), "composition": dict(comp), "exp25_composition": dict(refc),
                          "off_default_correct": off, "record_exp25": rec, "fisher_p": fp, "JS": js,
                          "JS_null_p95_exp25": 0.077 if t == "T03" else 0.0047,
                          "per_slot_label_agreement": float(np.mean(agree)) if agree else None,
                          "code_identical_share": float(np.mean(ident)) if ident else None,
                          "pass": bool(fp is not None and fp >= 0.05 and (t != "T03" or js <= 0.077)),
                          "kind": "positive control (T03 decisive, T2 descriptive)"}
    # U9: this artifact's twin vs earlier bf16 twin rows (exp27 TWIN, exp25 ECTWIN) on the same prompts and uniforms
    e27 = read_jsonl(E27 / "data" / "labels.jsonl")
    for t in ("T03", "T10", "T2", "T1"):
        rs = {(r["template"], int(r["k"])): r for r in all_rows if r["task"] == t and r["arm"] == "TWIN"}
        for src, ref in (("exp27_TWIN_hf_bf16", {(r["template"], int(r["slot"])): r for r in e27
                                                 if r["task"] == t and r["arm"] == "TWIN"}),
                         ("exp25_ECTWIN_bf16", {(r["template"], int(r["slot"])): r for r in e25
                                                if r["arm"] == "ECTWIN" and str(r.get("unit", "")).endswith(t)})):
            sh = sorted(set(rs) & set(ref))
            if not sh:
                continue
            out[f"U9_{t}_{src}"] = {"n_shared": len(sh),
                                    "label_agreement": float(np.mean([rs[s]["label"] == ref[s]["label"] for s in sh])),
                                    "code_identical": float(np.mean([rs[s]["code"] == ref[s].get("code") for s in sh])),
                                    "this_composition": dict(Counter(rs[s]["label"] for s in sh)),
                                    "ref_composition": dict(Counter(ref[s]["label"] for s in sh))}
    write_json(RESULTS_DIR / "engine_checks.json", out)
    return out


# ------------------------------------------------------------------------------------------------ FP8 vs bf16
def fp8_vs_bf16(cl: dict[str, Any]) -> dict[str, Any]:
    c20 = read_json(E20 / "results" / "cells.json")
    out = {}
    for key, c in cl.items():
        t, arm = key.split("|")
        site, alpha = (arm, 0.0) if arm == "TWIN" else (arm.rsplit("_a", 1)[0], float(arm.rsplit("_a", 1)[1]))
        k20 = f"{t}|{site}|{alpha:g}"
        if k20 not in c20:
            continue
        o = c20[k20]
        n20 = int(o["n"])
        nc20 = int(o["n_correct"])
        y20 = float(o["off_share_correct"]) * nc20 / n20 if (n20 and o.get("off_share_correct") is not None) else \
            (0.0 if n20 and nc20 == 0 else None)
        out[key] = {"bf16_share_correct_off_default": c["share_correct_off_default"], "bf16_pass": c["pass"],
                    "bf16_n": c["n"], "fp8_exp20_share_correct_off_default": y20,
                    "fp8_exp20_pass": float(o["pass_rate"]), "fp8_exp20_n": n20,
                    "fp8_exp20_composition_correct": o.get("correct_composition"),
                    "bf16_composition_correct": c["composition_correct"],
                    "fp8_exp20_hill_correct": o.get("hill_correct"),
                    "bf16_hill_correct": c["hill1_correct_rarefied25"]["hill1"],
                    "note": "cross-engine and cross-unit (exp20: FP8 W8A8 with the iteration-4 ban unit; here: W16A16 "
                            "with the bf16 ban-free unit); descriptive only, no test crosses precisions"}
    write_json(RESULTS_DIR / "fp8_vs_bf16_sites.json", out)
    return out


def failure_modes(cl: dict[str, Any]) -> dict[str, Any]:
    """exp20 classes per (task, site) at the gated dose with the largest excess: moves (excess >= 0.20, pass >= 0.8x
    twin), moves with cost (excess >= 0.20 only below the gate), breakage first (pass < 0.8x twin before any
    excess >= 0.20), weak movement (0.10-0.20), no movement."""
    out: dict[str, Any] = {}
    for t in ("T03", "T10", "T2"):
        tw = cl.get(f"{t}|TWIN")
        if not tw:
            continue
        for s in ("S0", "S4", "S5", "S1", "S2", "S3", "S1E"):
            cs = [cl[f"{t}|{s}_a{a:g}"] for a in (1.0, 2.0, 4.0, 8.0) if f"{t}|{s}_a{a:g}" in cl]
            if not cs:
                continue
            ex = [(c["alpha"], c["share_correct_off_default"] - tw["share_correct_off_default"],
                   c["pass"] >= 0.8 * tw["pass"]) for c in cs]
            gated = [e for e in ex if e[2]]
            best_g = max([e[1] for e in gated], default=0.0)
            best_u = max([e[1] for e in ex], default=0.0)
            if best_g >= 0.20:
                cls = "moves"
            elif best_u >= 0.20:
                cls = "moves with cost"
            elif any(not e[2] for e in ex) and best_g < 0.10:
                cls = "breakage first"
            elif best_g >= 0.10:
                cls = "weak movement"
            else:
                cls = "no movement"
            out[f"{t}|{s}"] = {"class": cls, "by_alpha": [{"alpha": a, "excess": e, "gated": g} for a, e, g in ex]}
    write_json(RESULTS_DIR / "failure_modes.json", out)
    return out


def banned_sets_check(rows: list[dict[str, Any]]) -> dict[str, Any]:
    import geometry as G

    out = {}
    for t in ("T03", "T10"):
        c = G.implemented_counts(t)
        tw = Counter(r["label"] for r in rows if r["task"] == t and r["arm"] == "TWIN" and r["passed"])
        for a, n in tw.items():
            if a in c["pooled"]:
                c["pooled"][a] += n
        out[t] = {"rank_with_this_twin": G.rank_algorithms(t, c), "this_twin_correct": dict(tw)}
    bs = read_json(PRED_DIR / "banned_sets.json")
    out["unchanged"] = {"T03_TOP5": out["T03"]["rank_with_this_twin"][:5] == bs["sets"]["T03|TOP5"]["banned"],
                        "T03_TOP3": out["T03"]["rank_with_this_twin"][:3] == bs["sets"]["T03|TOP3"]["banned"],
                        "T10_TOP5": out["T10"]["rank_with_this_twin"][:3] == bs["sets"]["T10|TOP5"]["banned"]}
    write_json(RESULTS_DIR / "banned_sets_check.json", out)
    return out


def s_c_full(rows: list[dict[str, Any]], cl: dict[str, Any]) -> dict[str, Any]:
    res = D.s_c(rows)
    dmd = read_json(E27 / "results" / "pn_vs_dmd.json")["per_task"] if (E27 / "results" / "pn_vs_dmd.json").exists() \
        else {}
    for t in ("T03", "T10", "T2"):
        if t in res:
            res[t]["s3_kl_by_alpha"] = {f"{a:g}": cl.get(f"{t}|S3_a{a:g}", {}).get("s3_kl_mean_steps1_32")
                                        for a in (1.0, 2.0, 4.0)}
            res[t]["exp27_matched_decoding_kl"] = {k: {"K_PN": v.get("K_PN"), "f_on_DMD": v.get("f_on_DMD"),
                                                       "T_dmd": v.get("T_dmd")} for k, v in dmd.get(t, {}).items()
                                                   if isinstance(v, dict)}
    res["prediction_iii_T10"] = bool(res.get("T10", {}).get("pass"))
    write_json(RESULTS_DIR / "s_c.json", res)
    return res


def prediction_i(sa: dict[str, Any], cl: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for t in ("T03", "T10"):
        tr = sa["tasks"].get(t, {})
        best = {}
        for s in ("S0", "S4"):
            g = [c for c in tr.get("candidates", []) if c["site"] == s and c["gated"]]
            best[s] = max(g, key=lambda c: c["share"]) if g else None
        comp_max = max((cl.get(f"{t}|{s}_a{a:g}", {}).get("share_correct_off_default", 0) for s in ("S1", "S2", "S5")
                        for a in (1.0, 2.0, 4.0)), default=0)
        s4, s0 = best["S4"], best["S0"]
        out[t] = {"best_gated_S0": s0 and {"alpha": s0["alpha"], "share": s0["share"]},
                  "best_gated_S4": s4 and {"alpha": s4["alpha"], "share": s4["share"]},
                  "max_comparator_share": comp_max,
                  "hit": bool(s0 and s4 and s4["share"] >= s0["share"] and s0["share"] > comp_max and
                              s4["share"] > comp_max)}
    return out


def main() -> None:
    from transformers import AutoTokenizer

    from cfg import model_path

    setup_logging("analysis")
    rows_all = merge()
    rows = decisive(rows_all)
    cl = cells(rows)
    sa = D.s_a(rows)
    sa["prediction_i"] = prediction_i(sa, cl)
    # sensitivity: the pre-registered N 30 slots only (k 0-5), i.e. without the outcome-blind P6(b) top-ups
    sa30 = D.s_a([r for r in rows if r["arm"] == "TWIN" or int(r["k"]) < 6])
    sa["sensitivity_N30_slots_k0_5"] = {"verdict": sa30["verdict"], "task_pass": sa30["task_pass"],
                                        "selected": {t: v["selected"] for t, v in sa30["tasks"].items()},
                                        "contrasts": {t: v["contrasts"] for t, v in sa30["tasks"].items()}}
    sa["n_shared_note"] = "primary uses every shared slot (N 50 where the P6(b) top-ups ran, else N 30)"
    write_json(RESULTS_DIR / "s_a.json", sa)
    logger.info(f"S-a verdict: {sa['verdict']}")
    sb = s_b_full(rows)
    write_json(RESULTS_DIR / "s_b.json", sb)
    logger.info(f"S-b: OR {sb['primary'].get('mh', {}).get('or')} CI {sb['primary'].get('mh', {}).get('ci')}")
    sc = s_c_full(rows, cl)
    logger.info(f"S-c: { {t: sc[t]['pass'] for t in ('T03', 'T10', 'T2') if t in sc} }")
    landings(cl)
    dose_axis(rows)
    tok = AutoTokenizer.from_pretrained(model_path())
    f = f1(rows, tok)
    logger.info(f"F1: {f['decision']}")
    f2()
    s_d(rows)
    engine_checks(rows_all)
    fp8_vs_bf16(cl)
    failure_modes(cl)
    banned_sets_check(rows)
    logger.info("analysis done")


if __name__ == "__main__":
    main()
