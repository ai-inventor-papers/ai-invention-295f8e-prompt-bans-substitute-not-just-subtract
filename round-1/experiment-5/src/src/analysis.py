"""STEP 8: per-arm metrics, collapse screen (2x2 weights x format), steering analysis, BUY / PREDICT rows,
base ban obedience, labeller QA, figures. Writes results/analysis.json and figures/*.png|pdf.

  .venv/bin/python src/analysis.py [--second_judge]
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path

import numpy as np
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (BANNED, BAN_COND, CATALOGUE, FIGS, PRED, RESULTS, RUNS, SURVIVORS, read_jsonl, setup_logging,  # noqa: E402
                    sha256_file, wilson)
from stats_utils import ArmData, boot_stat, cohen_kappa, hill, js, norm_label, perm_chi2  # noqa: E402

B_BOOT = 2000
VLLM_ARMS = {
    "base_tf": "labelled_base_tf__baseline.jsonl",
    "base_chat": "labelled_base_chat__baseline.jsonl",
    "base_tf_ban": "labelled_base_tf__ban.jsonl",
    "instruct_chat": "labelled_instruct_chat__baseline.jsonl",
    "instruct_tf": "labelled_instruct_tf__baseline.jsonl",
    "instruct_chat_ban": "labelled_instruct_chat__ban.jsonl",
}
PRIORS = {
    "t2": {"invisible_lottery_table12": {"setting": "no cue, 15 configs, T=0, N=35 each", "dijkstra": 0.941, "bfs": 0.059},
           "inspiration_repo_llm_creativity": {"setting": "claude-sonnet-5 weighted shortest path baseline", "dijkstra": "25/25",
                                               "cumulative_bans": "SPFA 16/25, Bellman-Ford 5/25", "ast_judge_agreement": "164/200"}},
    "t1": {"note": "no published prior for the unweighted grid-path task"},
}


# ------------------------------------------------------------------------------------------------ loading
def load_arms() -> dict[str, list[dict]]:
    arms = {}
    for k, f in VLLM_ARMS.items():
        rows = read_jsonl(RUNS / f)
        if rows:
            arms[k] = rows
    for f in sorted(RUNS.glob("labelled_steer__*.jsonl")):
        rows = read_jsonl(f)
        if rows:
            arms[rows[0]["arm"]] = rows
    return arms


def task_rows(rows: list[dict], task: str) -> list[dict]:
    return [r for r in rows if r["task"] == task]


def lab_of(r: dict, cats: list[str], key: str = "label") -> str | None:
    if not r.get("parse_ok") or r.get(key) is None:
        return None
    return norm_label(r[key], cats)


# ------------------------------------------------------------------------------------------------ per arm
def arm_summary(rows: list[dict], task: str, key: str = "label") -> dict:
    cats = CATALOGUE[task]
    n = len(rows)
    npar = sum(bool(r["parse_ok"]) for r in rows)
    npass = sum(bool(r["passed"]) for r in rows)
    ad = ArmData(rows, cats, key)
    c_all = ad.counts(correct_only=False)
    c_cc = ad.counts(correct_only=True)
    names = ad.cats
    out = {"N": n, "parse_rate": npar / n if n else None, "pass_rate": wilson(npass, n), "n_pass": npass,
           "label_counts_all": {names[i]: int(c_all[i]) for i in range(len(names)) if c_all[i]},
           "label_counts_correct": {names[i]: int(c_cc[i]) for i in range(len(names)) if c_cc[i]},
           "other_rate_parseable": float(c_all[-1] / c_all.sum()) if c_all.sum() else None,
           "hill_cc": hill(c_cc), "hill_all": hill(c_all),
           "hill_cc_excl_other": hill(c_cc[:-1]), "n_correct_labelled": int(c_cc.sum())}
    if c_cc.sum():
        m = int(np.argmax(c_cc))
        out["modal_correct"] = names[m]
        out["modal_share_correct"] = wilson(int(c_cc[m]), int(c_cc.sum()))
    if c_all.sum():
        m = int(np.argmax(c_all))
        out["modal_all"] = names[m]
        out["modal_share_all"] = wilson(int(c_all[m]), int(c_all.sum()))
    for flag in ("format_ok_loose", "format_ok_strict", "refusal", "degenerate", "chat_leak", "length_cap"):
        vals = [r.get(flag) for r in rows if r.get(flag) is not None]
        out[f"{flag}_rate"] = (sum(bool(v) for v in vals) / len(vals)) if vals else None
    out["finish_reasons"] = {}
    for r in rows:
        out["finish_reasons"][r.get("finish_reason")] = out["finish_reasons"].get(r.get("finish_reason"), 0) + 1
    out["labeller_sources"] = {}
    for r in rows:
        if r.get("parse_ok"):
            s = r.get("labeller_source")
            out["labeller_sources"][s] = out["labeller_sources"].get(s, 0) + 1
    # bootstrap CIs on Hill
    out["hill_cc_ci"] = boot_stat([ad], lambda ix: hill(ad.counts(ix[0], True)), B=B_BOOT, seed=1)
    out["hill_all_ci"] = boot_stat([ad], lambda ix: hill(ad.counts(ix[0], False)), B=B_BOOT, seed=2, min_correct=0)
    return out


# ------------------------------------------------------------------------------------------------ collapse screen
def diff_ci(a: ArmData, b: ArmData, correct_only: bool, seed: int) -> dict:
    """Hill(a) - Hill(b) with paraphrase ids resampled jointly (arms share P0..P9)."""
    return boot_stat([a, b], lambda ix: hill(a.counts(ix[0], correct_only)) - hill(b.counts(ix[1], correct_only)),
                     B=B_BOOT, seed=seed, min_correct=5 if correct_only else 0)


def modal_share(ad: ArmData, lab: str, correct_only: bool = True) -> tuple:
    c = ad.counts(correct_only=correct_only)
    i = ad.cats.index(lab) if lab in ad.cats else len(ad.cats) - 1
    return wilson(int(c[i]), int(c.sum()))


def verdict(task: str, A: dict[str, "ArmData"], correct_only: bool) -> dict:
    """Pre-registered per-task verdict."""
    tag = "cc" if correct_only else "all"
    ic, bc, bt = A["instruct_chat"], A["base_chat"], A["base_tf"]
    d_w = diff_ci(bc, ic, correct_only, 11)    # base_chat - instruct_chat (weights; >0 means post-training collapsed)
    d_f = diff_ci(bt, bc, correct_only, 12)    # base_tf - base_chat (format)
    d_tf_ic = diff_ci(bt, ic, correct_only, 13)
    inst_modal = ic.cats[int(np.argmax(ic.counts(correct_only=correct_only)))]
    bt_modal = bt.cats[int(np.argmax(bt.counts(correct_only=correct_only)))]
    bc_modal = bc.cats[int(np.argmax(bc.counts(correct_only=correct_only)))]
    sh_ic = modal_share(ic, inst_modal, correct_only)[0]
    sh_bc_same = modal_share(bc, inst_modal, correct_only)[0]
    sh_bt_bcmodal = modal_share(bt, bc_modal, correct_only)[0]
    sh_bc_bcmodal = modal_share(bc, bc_modal, correct_only)[0]
    weights_bar = (d_w["est"] >= 0.5 and d_w["lo"] is not None and d_w["lo"] > 0 and (sh_ic - sh_bc_same) >= 0.15)
    format_bar = (d_f["est"] >= 0.5 and d_f["lo"] is not None and d_f["lo"] > 0 and (sh_bc_bcmodal - sh_bt_bcmodal) >= 0.15)
    already = (bt_modal == inst_modal and d_tf_ic["hi"] is not None and d_tf_ic["hi"] < 0.5)
    if weights_bar:
        v = "INSTALLED_BY_POST_TRAINING"
    elif format_bar:
        v = "INSTALLED_BY_FORMAT"
    elif already:
        v = "ALREADY_IN_BASE"
    else:
        v = "MIXED"
    return {"hill_variant": tag, "verdict": v,
            "hill_base_chat_minus_instruct_chat": d_w, "hill_base_tf_minus_base_chat": d_f,
            "hill_base_tf_minus_instruct_chat": d_tf_ic,
            "instruct_modal": inst_modal, "base_tf_modal": bt_modal, "base_chat_modal": bc_modal,
            "instruct_modal_share": sh_ic, "base_chat_share_of_instruct_modal": sh_bc_same,
            "modal_share_gap_pp_weights": 100 * (sh_ic - sh_bc_same),
            "weights_bar_met": bool(weights_bar), "format_bar_met": bool(format_bar), "already_in_base_bar_met": bool(already)}


def collapse_screen(task: str, arms: dict[str, list[dict]], label_key: str = "label", row_filter=None,
                    with_tests: bool = True) -> dict:
    cats = CATALOGUE[task]
    keep = row_filter or (lambda r: True)
    A = {k: ArmData([r for r in task_rows(arms[k], task) if keep(r)], cats, label_key)
         for k in ("base_tf", "base_chat", "instruct_chat", "instruct_tf") if k in arms}
    sizes = {k: {"N": v.n, "n_correct_labelled": int(v.counts().sum())} for k, v in A.items()}
    out: dict = {"priors": PRIORS[task], "label_key": label_key, "arm_sizes": sizes}
    if not all(k in A for k in ("base_tf", "base_chat", "instruct_chat")):
        return {"error": "missing arms"}
    for co in (True, False):
        tag = "cc" if co else "all"
        out[f"D_weights_{tag}"] = diff_ci(A["instruct_chat"], A["base_chat"], co, 21)   # instruct_chat - base_chat
        out[f"D_format_{tag}"] = diff_ci(A["base_chat"], A["base_tf"], co, 22)          # base_chat - base_tf
        if "instruct_tf" in A:
            out[f"D_format_instruct_{tag}"] = diff_ci(A["instruct_chat"], A["instruct_tf"], co, 23)
            out[f"D_weights_tf_{tag}"] = diff_ci(A["instruct_tf"], A["base_tf"], co, 24)
            ic, it, bc, bt = A["instruct_chat"], A["instruct_tf"], A["base_chat"], A["base_tf"]
            out[f"interaction_{tag}"] = boot_stat(
                [ic, it, bc, bt],
                lambda ix: (hill(ic.counts(ix[0], co)) - hill(it.counts(ix[1], co))) - (hill(bc.counts(ix[2], co)) - hill(bt.counts(ix[3], co))),
                B=B_BOOT, seed=25, min_correct=3 if co else 0)
    tests = {}
    pairs_t = (("instruct_chat", "base_chat"),) if not with_tests else ()
    for a, b in pairs_t or (("instruct_chat", "base_chat"), ("base_chat", "base_tf"), ("instruct_chat", "base_tf"),
                 ("instruct_chat", "instruct_tf"), ("instruct_tf", "base_tf")):
        if a in A and b in A:
            for co in (True, False):
                la = A[a].lab[(A[a].lab >= 0) & (A[a].cor if co else True)]
                lb = A[b].lab[(A[b].lab >= 0) & (A[b].cor if co else True)]
                tests[f"{a}_vs_{b}_{'cc' if co else 'all'}"] = perm_chi2(la, lb, A[a].K, n_perm=10000, seed=7)
    out["permutation_chi2"] = tests
    out["verdict_cc"] = verdict(task, A, True)
    out["verdict_all"] = verdict(task, A, False)
    return out


# ------------------------------------------------------------------------------------------------ steering
def coupled_pairs(rows_a: list[dict], rows_b: list[dict]) -> list[tuple[dict, dict]]:
    ib = {(r["paraphrase_id"], r["sample_id"]): r for r in rows_b}
    return [(ra, ib[(ra["paraphrase_id"], ra["sample_id"])]) for ra in rows_a if (ra["paraphrase_id"], ra["sample_id"]) in ib]


def flip_stats(pairs: list[tuple[dict, dict]], cats: list[str]) -> dict:
    both = [(a, b) for a, b in pairs if a.get("parse_ok") and b.get("parse_ok") and a.get("label") and b.get("label")]
    if not both:
        return {"n_pairs_both_parse": 0, "flip_rate": None, "transitions": {}}
    trans: dict = {}
    flips = 0
    for a, b in both:
        la, lb = norm_label(a["label"], cats), norm_label(b["label"], cats)
        trans.setdefault(lb, {}).setdefault(la, 0)
        trans[lb][la] += 1
        flips += la != lb
    return {"n_pairs_both_parse": len(both), "flip_rate": flips / len(both), "transitions_from_S0_to_arm": trans}


def flip_boot(pairs_by_arm: dict[str, list], cats: list[str], arm: str, rnd: list[str], seed: int = 31) -> dict:
    """flip(arm) - mean flip(random arms), paired bootstrap over paraphrases."""
    def fr(pairs):
        both = [(a, b) for a, b in pairs if a.get("parse_ok") and b.get("parse_ok") and a.get("label") and b.get("label")]
        if not both:
            return None
        return sum(norm_label(a["label"], cats) != norm_label(b["label"], cats) for a, b in both) / len(both)
    if arm not in pairs_by_arm or not all(r in pairs_by_arm for r in rnd):
        return {"est": None}
    rng = np.random.default_rng(seed)
    pids = sorted({a["paraphrase_id"] for a, _ in pairs_by_arm[arm]})
    vals = []

    def stat(sel):
        f1 = fr([p for p in pairs_by_arm[arm] if p[0]["paraphrase_id"] in sel])
        fr_r = [fr([p for p in pairs_by_arm[r] if p[0]["paraphrase_id"] in sel]) for r in rnd]
        if f1 is None or any(x is None for x in fr_r):
            return None
        return f1 - float(np.mean(fr_r))
    est = stat(set(pids))
    for _ in range(1000):
        ch = rng.choice(pids, size=len(pids), replace=True)
        # cluster bootstrap with multiplicity: expand pairs per chosen paraphrase
        def expand(pairs):
            out = []
            for p in ch:
                out.extend([x for x in pairs if x[0]["paraphrase_id"] == p])
            return out
        f1 = fr(expand(pairs_by_arm[arm]))
        fr_r = [fr(expand(pairs_by_arm[r])) for r in rnd]
        if f1 is None or any(x is None for x in fr_r):
            continue
        vals.append(f1 - float(np.mean(fr_r)))
    if not vals:
        return {"est": est, "lo": None, "hi": None}
    lo, hi = np.percentile(vals, [2.5, 97.5])
    return {"est": est, "lo": float(lo), "hi": float(hi), "n_boot": len(vals)}


def steering(task: str, arms: dict[str, list[dict]]) -> dict:
    cats = CATALOGUE[task]
    s0_name = "steer:none:c=0"
    if s0_name not in arms:
        return {"error": "no S0"}
    s0 = task_rows(arms[s0_name], task)
    A0 = ArmData(s0, cats)
    refs = {k: ArmData(task_rows(arms[k], task), cats) for k in ("base_chat", "base_tf") if k in arms}
    steer_arms = sorted([k for k in arms if k.startswith("steer:") and k != s0_name])
    out: dict = {"S0": arm_summary(s0, task), "arms": {}}
    pass0 = sum(bool(r["passed"]) for r in s0) / len(s0)
    fmt0 = np.mean([bool(r.get("format_ok_loose")) for r in s0])
    pairs_by_arm = {}
    for k in steer_arms:
        rows = task_rows(arms[k], task)
        if not rows:
            continue
        Ak = ArmData(rows, cats)
        s = arm_summary(rows, task)
        d_h = boot_stat([Ak, A0], lambda ix: hill(Ak.counts(ix[0], True)) - hill(A0.counts(ix[1], True)), B=B_BOOT, seed=41, min_correct=3)
        d_pass = boot_stat([Ak, A0], lambda ix: 100 * (Ak.cor[ix[0]].mean() - A0.cor[ix[1]].mean()), B=B_BOOT, seed=42, min_correct=0)
        s["delta_hill_cc_vs_S0"] = d_h
        s["delta_pass_pp_vs_S0"] = d_pass
        for flag in ("format_ok_loose", "refusal", "degenerate"):
            a = np.mean([bool(r.get(flag)) for r in rows])
            b = np.mean([bool(r.get(flag)) for r in s0])
            s[f"delta_{flag}"] = float(a - b)
        for rk, Ar in refs.items():
            if s["n_correct_labelled"] == 0:
                s[f"restoration_index_vs_{rk}"] = {"est": None, "lo": None, "hi": None, "note": "no correct samples in arm"}
                continue

            def ri(ix, Ak=Ak, Ar=Ar, sm=0.5):
                j0 = js(A0.counts(ix[1], True), Ar.counts(ix[2], True), sm)
                if j0 <= 1e-9:
                    return float("nan")
                return 1 - js(Ak.counts(ix[0], True), Ar.counts(ix[2], True), sm) / j0
            s[f"restoration_index_vs_{rk}"] = boot_stat([Ak, A0, Ar], ri, B=B_BOOT, seed=43, min_correct=1)
            s[f"restoration_index_unsmoothed_vs_{rk}"] = boot_stat(
                [Ak, A0, Ar], lambda ix, f_=ri: f_(ix, sm=0.0), B=B_BOOT, seed=46, min_correct=1)
        pairs = coupled_pairs(rows, s0)
        pairs_by_arm[k] = pairs
        s["flips_vs_S0"] = flip_stats(pairs, cats)
        s["pass_ratio_vs_S0"] = (s["pass_rate"][0] / pass0) if pass0 else None
        s["format_ratio_vs_S0"] = (s["format_ok_loose_rate"] / fmt0) if fmt0 else None
        out["arms"][k] = s
    # c* and random-direction comparison
    sharp = {k: v for k, v in out["arms"].items() if k.startswith("steer:sharpen:c=")}
    good = [float(k.split("=")[1]) for k, v in sharp.items() if v["pass_ratio_vs_S0"] is not None and v["pass_ratio_vs_S0"] >= 0.8]
    out["c_star"] = max(good) if good else 0.5
    out["c_star_flag"] = None if good else "no sharpening c kept pass >= 0.8 x S0; c* set to 0.5 (flagged)"
    rnd = [k for k in out["arms"] if k.startswith("steer:random")]
    cs = f"steer:sharpen:c={out['c_star']}"
    if cs in out["arms"] and rnd:
        out["flip_diff_cstar_minus_random"] = flip_boot(pairs_by_arm, cats, cs, rnd)
        Ac = ArmData(task_rows(arms[cs], task), cats)
        Rs = [ArmData(task_rows(arms[r], task), cats) for r in rnd]
        out["hill_cstar_minus_max_random"] = boot_stat(
            [Ac] + Rs, lambda ix: hill(Ac.counts(ix[0], True)) - max(hill(R.counts(i, True)) for R, i in zip(Rs, ix[1:])),
            B=B_BOOT, seed=44, min_correct=3)
    # knob verdict (pre-registered)
    restores = False
    for k, v in sharp.items():
        dh = v["delta_hill_cc_vs_S0"]
        ri = v.get("restoration_index_vs_base_chat", {}).get("est")
        beats_rand = out.get("hill_cstar_minus_max_random", {}).get("lo")
        if (dh["lo"] is not None and dh["lo"] > 0 and v["pass_ratio_vs_S0"] is not None and v["pass_ratio_vs_S0"] >= 0.8
                and v["format_ratio_vs_S0"] is not None and v["format_ratio_vs_S0"] >= 0.9 and ri is not None and ri > 0
                and k == cs and beats_rand is not None and beats_rand > 0):
            restores = True
    destructive = bool(sharp) and all((v["pass_ratio_vs_S0"] is None or v["pass_ratio_vs_S0"] < 0.8 or
                                       v["format_ratio_vs_S0"] is None or v["format_ratio_vs_S0"] < 0.9) for v in sharp.values())
    no_effect = bool(sharp) and all(v["delta_hill_cc_vs_S0"]["lo"] is None or (v["delta_hill_cc_vs_S0"]["lo"] <= 0 <= v["delta_hill_cc_vs_S0"]["hi"])
                                    for v in sharp.values())
    for k in [k for k in out["arms"] if k.endswith("+nocutoff")]:
        base_k = k.replace("+nocutoff", "")
        if base_k in out["arms"]:
            nc = {(r["paraphrase_id"], r["sample_id"]): r for r in task_rows(arms[k], task)}
            wc = [r for r in task_rows(arms[base_k], task) if (r["paraphrase_id"], r["sample_id"]) in nc]
            out[f"cutoff_validation|{base_k}"] = {
                "n_coupled": len(wc),
                "parse_rate_with_cutoff": (sum(bool(r["parse_ok"]) for r in wc) / len(wc)) if wc else None,
                "parse_rate_without_cutoff": (sum(bool(nc[(r["paraphrase_id"], r["sample_id"])]["parse_ok"]) for r in wc) / len(wc)) if wc else None,
                "pass_rate_with_cutoff": (sum(bool(r["passed"]) for r in wc) / len(wc)) if wc else None,
                "pass_rate_without_cutoff": (sum(bool(nc[(r["paraphrase_id"], r["sample_id"])]["passed"]) for r in wc) / len(wc)) if wc else None,
                "labels_without_cutoff_correct": {lab: sum(1 for r in nc.values() if r.get("passed") and norm_label(r.get("label"), cats) == lab)
                                                  for lab in cats + ["other"]}}
    # what do rows WITHOUT code say? (thinking-style prose, stated algorithm) - keyword tally, descriptive only
    kw = {"bfs": r"\bbfs\b|breadth[- ]first", "dfs": r"\bdfs\b|depth[- ]first", "dijkstra": r"dijkstra",
          "astar": r"\ba\*|\ba-star\b|\bastar\b", "bellman_ford": r"bellman|\bspfa\b", "floyd": r"floyd"}
    import re as _re
    for k in steer_arms + [s0_name]:
        rows = task_rows(arms[k], task)
        noc = [r for r in rows if not r.get("parse_ok")]
        target = out["arms"][k] if k in out["arms"] else out["S0"]
        think = sum(bool(_re.match(r"\s*(okay|alright|hmm|so|well)\b[,.!]?[ \t]+(i|let|so|the|we|first|now|this)\b",
                                   r.get("text", ""), _re.I)) for r in rows)
        target["thinking_style_opening_rate"] = think / len(rows) if rows else None
        target["nocode_rows"] = len(noc)
        target["nocode_keyword_mentions"] = {name: sum(bool(_re.search(pat, r.get("text", ""), _re.I)) for r in noc)
                                             for name, pat in kw.items()}
    out["knob_verdict"] = ("RESTORES_WITHOUT_LOSS" if restores else "DESTRUCTIVE" if destructive else
                           "NO_EFFECT" if no_effect else "MIXED")
    # fallback-6 single-layer knob and the R-only ablation (same bars, descriptive)
    for fam in ("steer:single18:c=", "steer:sharpen_Ronly:c="):
        fa = {k: v for k, v in out["arms"].items() if k.startswith(fam) and "+nocutoff" not in k}
        if not fa:
            continue
        summ = {}
        for k, v in fa.items():
            ok_pass = v["pass_ratio_vs_S0"] is not None and v["pass_ratio_vs_S0"] >= 0.8
            ok_fmt = v["format_ratio_vs_S0"] is not None and v["format_ratio_vs_S0"] >= 0.9
            dh = v["delta_hill_cc_vs_S0"]
            summ[k] = {"passes_correctness_and_format_bars": bool(ok_pass and ok_fmt),
                       "delta_hill_ci_excludes_0_positive": bool(dh["lo"] is not None and dh["lo"] > 0),
                       "flip_rate": v["flips_vs_S0"].get("flip_rate")}
        verdict_f = ("DESTRUCTIVE" if all(not x["passes_correctness_and_format_bars"] for x in summ.values()) else
                     "RESTORES_DIVERSITY_SOME_C" if any(x["passes_correctness_and_format_bars"] and x["delta_hill_ci_excludes_0_positive"]
                                                         for x in summ.values()) else "NO_EFFECT_WITHIN_BARS")
        out[f"family_verdict|{fam.rstrip(':c=')}"] = {"verdict": verdict_f, "per_c": summ}
    for k in [k for k in out["arms"] if k.startswith("steer:sharpen_Ronly:c=") and "+nocutoff" not in k]:
        c = k.split("=")[1]
        ctrl = f"steer:random1_Ronly:c={c}"
        if ctrl in out["arms"]:
            Ak = ArmData(task_rows(arms[k], task), cats)
            Ac = ArmData(task_rows(arms[ctrl], task), cats)
            out[f"Ronly_vs_random_control|c={c}"] = {
                "hill_diff": boot_stat([Ak, Ac], lambda ix: hill(Ak.counts(ix[0], True)) - hill(Ac.counts(ix[1], True)),
                                       B=B_BOOT, seed=45, min_correct=3),
                "flip_diff_vs_control": flip_boot(pairs_by_arm, cats, k, [ctrl]),
                "perm_chi2_cc": perm_chi2(Ak.lab[(Ak.lab >= 0) & Ak.cor], Ac.lab[(Ac.lab >= 0) & Ac.cor], Ak.K, 10000, 10)}
    # S0 (HF engine) vs B1 (vLLM) implementation check
    if "instruct_chat" in arms:
        b1 = ArmData(task_rows(arms["instruct_chat"], task), cats)
        out["S0_vs_vllm_B1"] = {
            "perm_chi2_cc": perm_chi2(A0.lab[(A0.lab >= 0) & A0.cor], b1.lab[(b1.lab >= 0) & b1.cor], A0.K, 10000, 9),
            "pass_S0": wilson(int(A0.cor.sum()), A0.n), "pass_B1": wilson(int(b1.cor.sum()), b1.n),
            "hill_cc_S0": hill(A0.counts()), "hill_cc_B1": hill(b1.counts())}
    return out


# ------------------------------------------------------------------------------------------------ BUY / PREDICT / obedience
def buy_rows(task: str, arms: dict, st: dict) -> list[dict]:
    rows = []
    cats = CATALOGUE[task]
    if "error" not in st:
        h0, p0 = st["S0"]["hill_cc"], st["S0"]["pass_rate"][0]
        curve = [(0.0, h0, p0)]
        for k, v in sorted(st["arms"].items()):
            if k.startswith("steer:sharpen:c="):
                curve.append((float(k.split("=")[1]), v["hill_cc"], v["pass_rate"][0]))
        curve.sort()
        for k, v in sorted(st["arms"].items()):
            dh = (v["hill_cc"] - h0) if not (math.isnan(v["hill_cc"]) or math.isnan(h0)) else None
            loss = 100 * (p0 - v["pass_rate"][0])
            rows.append({"task": task, "knob": k, "reference": "steer:none:c=0 (HF S0)", "hill_cc": v["hill_cc"],
                         "pass_rate": v["pass_rate"][0], "delta_hill_cc": dh, "delta_pass_pp": -loss,
                         "pass_loss_pp": loss, "efficiency": (dh / max(loss, 1.0)) if dh is not None else None,
                         "n": v["N"], "n_correct": v["n_correct_labelled"]})
        for target, key in ((2.0, "price_hill2"), (3.0, "price_hill3")):
            price = "not reached within the tested range"
            for (c1, h1, q1), (c2, h2, q2) in zip(curve, curve[1:]):
                if any(math.isnan(x) for x in (h1, h2)):
                    continue
                if (h1 - target) * (h2 - target) <= 0 and h1 != h2:
                    f = (target - h1) / (h2 - h1)
                    price = 100 * (p0 - (q1 + f * (q2 - q1)))
                    break
            for r in rows:
                if r["knob"].startswith("steer:sharpen"):
                    r[key] = price
    if "instruct_chat_ban" in arms and "instruct_chat" in arms:
        b = ArmData(task_rows(arms["instruct_chat_ban"], task), cats)
        a = ArmData(task_rows(arms["instruct_chat"], task), cats)
        hb, ha = hill(b.counts()), hill(a.counts())
        pb, pa = b.cor.mean(), a.cor.mean()
        loss = 100 * (pa - pb)
        rows.append({"task": task, "knob": f"prompt:{BAN_COND[task]}", "reference": "instruct_chat:baseline (vLLM B1)",
                     "hill_cc": hb, "pass_rate": float(pb), "delta_hill_cc": hb - ha, "delta_pass_pp": -loss,
                     "pass_loss_pp": loss, "efficiency": (hb - ha) / max(loss, 1.0), "n": b.n, "n_correct": int(b.counts().sum()),
                     "price_hill2": "n/a (single setting)", "price_hill3": "n/a (single setting)"})
    return rows


def predict_rows(task: str, arms: dict) -> list[dict]:
    f = PRED / "predict_modal_ban.json"
    if not f.exists() or "instruct_chat_ban" not in arms:
        return []
    pred = json.loads(f.read_text())
    sha_now = sha256_file(f)
    logged = [json.loads(x) for x in (PRED / "hash_log.txt").read_text().splitlines() if x.strip()]
    sha_committed = logged[-1]["sha256"] if logged else None
    ev = pred["events"][task]
    S = ev["survivors"]
    rows_c = task_rows(arms["instruct_chat_ban"], task)
    comp = [r for r in rows_c if r.get("passed") and r.get("label") and norm_label(r["label"], CATALOGUE[task]) != BANNED[task]]
    labs = [norm_label(r["label"], CATALOGUE[task]) for r in comp]
    labs = [l if l in S else "other" for l in labs]
    cats = S + ["other"]
    cnt = np.array([labs.count(c) for c in cats], dtype=float)
    realised = None
    if cnt.sum():
        order = np.argsort(-cnt)
        lead = (cnt[order[0]] - (cnt[order[1]] if len(order) > 1 else 0)) / cnt.sum()
        realised = cats[order[0]] if lead >= 0.15 else "no clear mode"
    out = []
    for name, pr in ev["predictors"].items():
        p = pr["p"]
        ls = float(np.mean([math.log(p[l]) for l in labs])) if labs else None
        pvec = np.array([p[c] for c in cats])
        jsd = None
        if cnt.sum():
            q = cnt / cnt.sum()
            m = 0.5 * (pvec + q)
            jsd = float(0.5 * (pvec * np.log(pvec / m)).sum() + 0.5 * sum(qi * math.log(qi / mi) for qi, mi in zip(q, m) if qi > 0))
        out.append({"task": task, "event": ev["event"], "predictor": name, "primary": name == ev["primary"],
                    "sha256_committed": sha_committed, "sha256_now": sha_now, "hash_match": sha_committed == sha_now,
                    "n_samples": len(rows_c), "n_compliant": len(comp), "realised_counts": {c: int(x) for c, x in zip(cats, cnt)},
                    "realised_mode": realised, "top1": pr["top1"],
                    "top1_hit": (realised == pr["top1"]) if realised not in (None, "no clear mode") else False,
                    "log_score": ls, "js_to_realised": jsd, "flags": ev.get("flags", [])})
    return out


def ban_obedience(task: str, arms: dict) -> dict:
    if "base_tf_ban" not in arms or "base_tf" not in arms:
        return {}
    cats = CATALOGUE[task]
    a3 = task_rows(arms["base_tf_ban"], task)
    a1 = task_rows(arms["base_tf"], task)
    ban = BANNED[task]

    def share(rows, correct_only):
        labs = [norm_label(r["label"], cats) for r in rows if r.get("parse_ok") and r.get("label") and (r.get("passed") or not correct_only)]
        return (sum(l == ban for l in labs), len(labs))
    out = {"banned_mode": ban}
    for co in (False, True):
        k3, n3 = share(a3, co)
        k1, n1 = share(a1, co)
        tag = "correct" if co else "parseable"
        out[f"banned_share_ban_{tag}"] = wilson(k3, n3)
        out[f"banned_share_baseline_{tag}"] = wilson(k1, n1)
        # bootstrap CI on the difference (resample samples within arm)
        rng = np.random.default_rng(5)
        l3 = np.array([norm_label(r["label"], cats) == ban for r in a3 if r.get("parse_ok") and r.get("label") and (r.get("passed") or not co)], dtype=float)
        l1 = np.array([norm_label(r["label"], cats) == ban for r in a1 if r.get("parse_ok") and r.get("label") and (r.get("passed") or not co)], dtype=float)
        if len(l3) and len(l1):
            d = [rng.choice(l3, len(l3)).mean() - rng.choice(l1, len(l1)).mean() for _ in range(2000)]
            out[f"diff_ban_minus_baseline_{tag}"] = {"est": float(l3.mean() - l1.mean()), "lo": float(np.percentile(d, 2.5)),
                                                    "hi": float(np.percentile(d, 97.5))}
    comp = [r for r in a3 if r.get("passed") and r.get("label") and norm_label(r["label"], cats) != ban]
    out["compliance_rate"] = wilson(len(comp), len(a3))
    S = SURVIVORS[task] + ["other"]
    land = np.array([sum(norm_label(r["label"], cats) == s if s != "other" else norm_label(r["label"], cats) not in SURVIVORS[task]
                         for r in comp) for s in S], dtype=float)
    out["survivor_landing_base"] = {s: int(x) for s, x in zip(S, land)}
    if "instruct_chat_ban" in arms:
        c1 = task_rows(arms["instruct_chat_ban"], task)
        comp1 = [r for r in c1 if r.get("passed") and r.get("label") and norm_label(r["label"], cats) != ban]
        land1 = np.array([sum(norm_label(r["label"], cats) == s if s != "other" else norm_label(r["label"], cats) not in SURVIVORS[task]
                              for r in comp1) for s in S], dtype=float)
        out["survivor_landing_instruct"] = {s: int(x) for s, x in zip(S, land1)}
        out["instruct_compliance_rate"] = wilson(len(comp1), len(c1))
        out["js_base_vs_instruct_landing"] = js(land, land1) if land.sum() and land1.sum() else None
    return out


# ------------------------------------------------------------------------------------------------ labeller QA
def labeller_qa(arms: dict, second_judge: bool) -> dict:
    qa: dict = {}
    gate = RESULTS / "labeller_gate.json"
    if gate.exists():
        g = json.loads(gate.read_text())
        qa["reference_gate"] = {k: g[k] for k in ("gate_ok", "ast_accuracy", "runtime_no_wrong_rate", "runtime_exact_accuracy", "n_programs")}
        qa["reference_gate"]["rows"] = g["rows"]
    rng = random.Random(123)
    per_arm = {}
    all_rt, all_ast = [], []
    audit_items = []
    for arm, rows in arms.items():
        for task in ("t1", "t2"):
            rr = [r for r in task_rows(rows, task) if r.get("parse_ok")]
            if not rr:
                continue
            rt = [r["runtime_label"] for r in rr]
            al = [r["ast_label"] if r["ast_label"] in CATALOGUE[task] or r["ast_label"] == "unknown" else "other" for r in rr]
            all_rt += [f"{task}:{x}" for x in rt]
            all_ast += [f"{task}:{x}" for x in al]
            agree = sum(a == b for a, b in zip(rt, al)) / len(rr)
            audit = rng.sample(rr, min(15, len(rr)))
            ok = sum(norm_label(r["label"], CATALOGUE[task]) == norm_label(r["judge_label"], CATALOGUE[task]) for r in audit if r.get("judge_label"))
            nj = sum(1 for r in audit if r.get("judge_label"))
            full_ok = sum(norm_label(r["label"], CATALOGUE[task]) == norm_label(r["judge_label"], CATALOGUE[task]) for r in rr if r.get("judge_label"))
            full_n = sum(1 for r in rr if r.get("judge_label"))
            det = [r for r in rr if r.get("labeller_source") == "runtime+ast" and r.get("judge_label")]
            det_ok = sum(norm_label(r["label"], CATALOGUE[task]) == norm_label(r["judge_label"], CATALOGUE[task]) for r in det)
            per_arm[f"{arm}|{task}"] = {
                "n_parseable": len(rr), "kappa_runtime_vs_ast": cohen_kappa(rt, al), "raw_agreement_runtime_ast": agree,
                "audit_n": nj, "audit_accuracy_vs_judge": wilson(ok, nj),
                "full_agreement_final_vs_judge": wilson(full_ok, full_n),
                "deterministic_labels_agreement_with_judge": wilson(det_ok, len(det)),
                "sources": {s: sum(r.get("labeller_source") == s for r in rr) for s in ("runtime+ast", "judge", "fallback")}}
            for r in audit:
                audit_items.append((task, r["code"], norm_label(r["judge_label"], CATALOGUE[task]) if r.get("judge_label") else None))
    qa["per_arm"] = per_arm
    qa["kappa_runtime_vs_ast_overall"] = cohen_kappa(all_rt, all_ast)
    if second_judge and audit_items:
        from judge import JUDGE_SECOND, judge_items
        sel = random.Random(7).sample(audit_items, min(40, len(audit_items)))
        res, info = judge_items([(t, c) for t, c, _ in sel], model=JUDGE_SECOND, budget_usd=1.0)
        a, b = [], []
        for (t, c, j1), r in zip(sel, res):
            if r is not None and j1 is not None:
                a.append(j1)
                b.append(norm_label(r["label"], CATALOGUE[t]))
        qa["second_judge"] = {"model": JUDGE_SECOND, "n": len(a), "kappa_inter_judge": cohen_kappa(a, b),
                              "raw_agreement": (sum(x == y for x, y in zip(a, b)) / len(a)) if a else None, "cost": info}
    return qa


def judge_sensitivity(arms: dict) -> dict:
    """Hill_cc recomputed with judge labels (all samples) and on the 15-per-arm audit subset."""
    out = {}
    for arm, rows in arms.items():
        for task in ("t1", "t2"):
            rr = task_rows(rows, task)
            if not rr:
                continue
            ad_j = ArmData(rr, CATALOGUE[task], "judge_label")
            ad_f = ArmData(rr, CATALOGUE[task], "label")
            out[f"{arm}|{task}"] = {"hill_cc_final": hill(ad_f.counts()), "hill_cc_judge": hill(ad_j.counts()),
                                    "hill_all_final": hill(ad_f.counts(correct_only=False)),
                                    "hill_all_judge": hill(ad_j.counts(correct_only=False)),
                                    "hill_cc_excl_fallback": hill(ArmData([r for r in rr if r.get("labeller_source") != "fallback"],
                                                                          CATALOGUE[task]).counts())}
    return out


# ------------------------------------------------------------------------------------------------ figures
def figures(arms: dict, res: dict) -> list[str]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    made = []
    palette = ["#4C72B0", "#DD8452", "#55A868", "#C44E52", "#8172B3", "#937860", "#AAAAAA"]
    order = ["base_tf", "base_chat", "instruct_tf", "instruct_chat", "base_tf_ban", "instruct_chat_ban", "steer:none:c=0"]
    for task in ("t1", "t2"):
        cats = CATALOGUE[task] + ["other"]
        names = [a for a in order if a in arms] + sorted(a for a in arms if a.startswith("steer:") and a != "steer:none:c=0")
        fig, ax = plt.subplots(figsize=(max(8, 1.0 * len(names)), 4.5))
        for i, a in enumerate(names):
            ad = ArmData(task_rows(arms[a], task), CATALOGUE[task])
            c = ad.counts(correct_only=True)
            tot = c.sum()
            bottom = 0.0
            for j, cat in enumerate(cats):
                h = c[j] / tot if tot else 0
                ax.bar(i, h, bottom=bottom, color=palette[j % len(palette)], label=cat if i == 0 else None, edgecolor="white", linewidth=0.5)
                bottom += h
            ax.text(i, 1.02, f"n={int(tot)}", ha="center", fontsize=7)
        ax.set_xticks(range(len(names)))
        ax.set_xticklabels([n.replace("steer:", "s:") for n in names], rotation=40, ha="right", fontsize=8)
        ax.set_ylabel("share of correct samples")
        ax.set_ylim(0, 1.1)
        ax.set_title(f"{task}: algorithm labels of correct programs per arm")
        ax.legend(fontsize=7, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.32))
        fig.tight_layout()
        for ext in ("png", "pdf"):
            fig.savefig(FIGS / f"labels_{task}.{ext}", dpi=150)
        plt.close(fig)
        made.append(f"figures/labels_{task}.png")
    # Hill & pass vs c
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    for task, mk in (("t1", "o"), ("t2", "s")):
        st = res["steering"].get(task, {})
        if "S0" not in st:
            continue
        xs = [0.0]
        hs = [st["S0"]["hill_cc"]]
        ps = [st["S0"]["pass_rate"][0]]
        for k, v in sorted(st["arms"].items()):
            if k.startswith("steer:sharpen:c="):
                xs.append(float(k.split("=")[1]))
                hs.append(v["hill_cc"])
                ps.append(v["pass_rate"][0])
        axes[0].plot(xs, hs, marker=mk, label=f"{task} sharpen (band 8-28)")
        axes[1].plot(xs, ps, marker=mk, label=f"{task} sharpen (band 8-28)")
        for k, v in st["arms"].items():
            if k.startswith("steer:random"):
                axes[0].scatter([st.get("c_star", 0.5)], [v["hill_cc"]], marker="x", color="k")
                axes[1].scatter([st.get("c_star", 0.5)], [v["pass_rate"][0]], marker="x", color="k")
            if k.startswith("steer:single18"):
                axes[1].scatter([float(k.split("=")[1])], [v["pass_rate"][0]], marker="^", color="tab:green")
        bc = res["arms"].get(f"base_chat|{task}", {}).get("hill_cc")
        if bc is not None and not math.isnan(bc):
            axes[0].axhline(bc, ls="--", lw=0.8, color="gray")
    axes[0].set_xlabel("c")
    axes[0].set_ylabel("Hill_cc (correct-sample effective # algorithms)")
    axes[1].set_xlabel("c")
    axes[1].set_ylabel("pass rate")
    axes[0].legend(fontsize=7)
    axes[1].legend(fontsize=7)
    axes[0].set_title("diversity vs steering strength (x: random dirs at c*)")
    axes[1].set_title("correctness vs strength (^: single-layer L18)")
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(FIGS / f"steering_curves.{ext}", dpi=150)
    plt.close(fig)
    made.append("figures/steering_curves.png")
    # per-layer diagnostics
    sd = RESULTS / "sharpening_direction.json"
    if sd.exists():
        d = json.loads(sd.read_text())
        fig, axes = plt.subplots(1, 3, figsize=(13, 3.6))
        for task in ("t1", "t2"):
            pl = d["tasks"][task]["per_layer"]
            L = [x["decoder_layer"] for x in pl]
            axes[0].plot(L, [x["cos_meanI_meanB"] for x in pl], label=f"{task} cos(mean h_I, mean h_B)")
            axes[0].plot(L, [x["split_half_cos"] for x in pl], ls="--", label=f"{task} split-half cos(delta)")
            axes[1].plot(L, [x["rel_norm_delta"] for x in pl], label=f"{task} ||delta||/||h_B||")
            axes[1].plot(L, [x["top10_energy_share"] for x in pl], ls=":", label=f"{task} top-10 energy share")
            axes[2].plot(L, [x["cos_delta_R_delta_gen"] for x in pl], label=f"{task} cos(delta_R, delta_gen)")
        axes[2].plot([x["index"] - 1 for x in d["task_generality_cos"]], [x["cos_delta_t1_t2"] for x in d["task_generality_cos"]],
                     color="k", ls="--", label="cos(delta_T1, delta_T2)")
        for ax in axes:
            ax.axvspan(8, 28, color="orange", alpha=0.08)
            ax.set_xlabel("decoder layer (-1 = embeddings)")
            ax.legend(fontsize=6)
        fig.tight_layout()
        for ext in ("png", "pdf"):
            fig.savefig(FIGS / f"direction_diagnostics.{ext}", dpi=150)
        plt.close(fig)
        made.append("figures/direction_diagnostics.png")
    # flip heatmaps for c* and random
    for task in ("t1", "t2"):
        st = res["steering"].get(task, {})
        arms_f = [k for k in st.get("arms", {}) if st["arms"][k]["flips_vs_S0"].get("n_pairs_both_parse")]
        if not arms_f:
            continue
        cats = CATALOGUE[task] + ["other"]
        fig, axes = plt.subplots(1, len(arms_f), figsize=(3.6 * len(arms_f), 3.4), squeeze=False)
        for ax, k in zip(axes[0], arms_f):
            tr = st["arms"][k]["flips_vs_S0"]["transitions_from_S0_to_arm"]
            M = np.array([[tr.get(a, {}).get(b, 0) for b in cats] for a in cats], dtype=float)
            ax.imshow(M, cmap="Blues")
            for i in range(len(cats)):
                for j in range(len(cats)):
                    if M[i, j]:
                        ax.text(j, i, int(M[i, j]), ha="center", va="center", fontsize=7)
            ax.set_xticks(range(len(cats)))
            ax.set_yticks(range(len(cats)))
            ax.set_xticklabels(cats, rotation=60, fontsize=6)
            ax.set_yticklabels(cats, fontsize=6)
            ax.set_title(k.replace("steer:", ""), fontsize=8)
            ax.set_xlabel("arm label")
            ax.set_ylabel("S0 label (coupled sample)")
        fig.tight_layout()
        for ext in ("png", "pdf"):
            fig.savefig(FIGS / f"flips_{task}.{ext}", dpi=150)
        plt.close(fig)
        made.append(f"figures/flips_{task}.png")
    return made


# ------------------------------------------------------------------------------------------------ main
def sanity_checks() -> dict:
    from scipy.stats import binomtest
    out = {"hill_one_label": hill(np.array([10, 0, 0])), "hill_uniform_k4": hill(np.array([5, 5, 5, 5])),
           "js_identical": js(np.array([3, 4, 5]), np.array([3, 4, 5]))}
    w = wilson(7, 20)
    ci = binomtest(7, 20).proportion_ci(method="wilson")
    out["wilson_matches_scipy"] = bool(abs(w[1] - ci.low) < 1e-9 and abs(w[2] - ci.high) < 1e-9)
    p_good = {"a": 0.98 * (0.95 * 1.0 + 0.05 / 2), "b": 0.98 * (0.05 / 2), "other": 0.02}
    p_unif = {"a": 0.49, "b": 0.49, "other": 0.02}
    realised = ["a"] * 9 + ["b"]
    out["synthetic_predict_good_beats_uniform"] = bool(np.mean([math.log(p_good[x]) for x in realised]) >
                                                        np.mean([math.log(p_unif[x]) for x in realised]))
    assert abs(out["hill_one_label"] - 1) < 1e-9 and abs(out["hill_uniform_k4"] - 4) < 1e-9 and out["js_identical"] < 1e-12
    assert out["wilson_matches_scipy"] and out["synthetic_predict_good_beats_uniform"]
    return out


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--second_judge", action="store_true")
    args = ap.parse_args()
    setup_logging("analysis")
    arms = load_arms()
    logger.info(f"arms: { {k: len(v) for k, v in arms.items()} }")
    res: dict = {"sanity": sanity_checks(), "arms": {}, "collapse_screen": {}, "steering": {}, "rows": {"BUY": [], "PREDICT": []},
                 "base_ban_obedience": {}, "priors": PRIORS}
    for arm, rows in arms.items():
        for task in ("t1", "t2"):
            rr = task_rows(rows, task)
            if rr:
                res["arms"][f"{arm}|{task}"] = arm_summary(rr, task)
    logger.info("per-arm summaries done")
    res["collapse_screen_sensitivity"] = {}
    for task in ("t1", "t2"):
        res["collapse_screen"][task] = collapse_screen(task, arms)
        res["collapse_screen_sensitivity"][f"{task}|judge_labels"] = collapse_screen(task, arms, label_key="judge_label", with_tests=False)
        res["collapse_screen_sensitivity"][f"{task}|planned_N_only"] = collapse_screen(
            task, arms, row_filter=lambda r: not str(r.get("stage", "")).startswith("ext"), with_tests=False)
        logger.info(f"{task}: verdict_cc={res['collapse_screen'][task].get('verdict_cc', {}).get('verdict')} "
                    f"verdict_all={res['collapse_screen'][task].get('verdict_all', {}).get('verdict')}")
        res["steering"][task] = steering(task, arms)
        res["rows"]["BUY"] += buy_rows(task, arms, res["steering"][task])
        res["rows"]["PREDICT"] += predict_rows(task, arms)
        res["base_ban_obedience"][task] = ban_obedience(task, arms)
    # pooled collapse-screen differences (mean over tasks)
    pooled = {}
    for key in ("D_weights_cc", "D_format_cc", "D_weights_all", "D_format_all"):
        vals = [res["collapse_screen"][t].get(key, {}).get("est") for t in ("t1", "t2")]
        if all(v is not None for v in vals):
            pooled[key] = float(np.mean(vals))
    res["collapse_screen"]["pooled_mean_over_tasks"] = pooled
    verdicts = [res["collapse_screen"][t]["verdict_cc"]["verdict"] for t in ("t1", "t2") if "verdict_cc" in res["collapse_screen"][t]]
    res["collapse_screen"]["alternate_passes_screen_cc"] = ("INSTALLED_BY_POST_TRAINING" in verdicts and "ALREADY_IN_BASE" not in verdicts)
    verdicts_all = [res["collapse_screen"][t]["verdict_all"]["verdict"] for t in ("t1", "t2") if "verdict_all" in res["collapse_screen"][t]]
    res["collapse_screen"]["alternate_passes_screen_all"] = ("INSTALLED_BY_POST_TRAINING" in verdicts_all and "ALREADY_IN_BASE" not in verdicts_all)
    res["labeller_qa"] = labeller_qa(arms, args.second_judge)
    res["labeller_qa"]["judge_label_sensitivity"] = judge_sensitivity(arms)
    for name in ("manipulation_S.json", "manipulation_R.json", "manipulation_X.json"):
        f = RESULTS / name
        if f.exists():
            res.setdefault("manipulation", {})[name.replace(".json", "")] = json.loads(f.read_text())
    res["figures"] = figures(arms, res)
    (RESULTS / "analysis.json").write_text(json.dumps(res, indent=1, default=str))
    logger.info("analysis written")


if __name__ == "__main__":
    main()
