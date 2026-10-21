#!/usr/bin/env python3
"""Pre-registration commits (hash chain in commitments.log, src/commit.py = exp17/exp19 commit.py unchanged).

COMMIT #0  protocol v5, precision rule, input hashes, sha256 of the frozen analysis code, every threshold, the CRN
           slot map, the derangement seed, the top-up rule, the N policy and the drop order.
COMMIT #1  (before ANY transplant / control / push / reverse sample) per task: default_t, beta_t with its
           template-cluster CI and stratum stability, r_t, base compositions (chat / plain, correct / attempted),
           Hill-1, strata, the predicted landing r_t and landing composition, the cross-task partner, the Stage 3-6
           task sets and cell plans (with the N policy applied to the measured seconds per batch).
COMMIT #2  (before any hooked S2 sample) lambda*_t, MR breakage and lambda'_t, the validity gate, the S2 task list
           and N, the Stage-4 cell plan.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))

import analysis_b as A  # noqa: E402
from cfg import (BETA_COLLAPSED, BETA_DIVERSE, BOOT_SEED, DATA_DIR, DEFAULT_SHARE_MIN, DEPTH, DERANGEMENT_SEED,  # noqa
                 DS_ALPHAS, DS_SLOTS, E22, LAMBDAS, MODEL_ID, N_BOOT, PASS_FRAC, PATH_TASKS, PRED_DIR, RESULTS_DIR,
                 ROOT, S1_SLOTS, S2_SLOTS_50, S2_SLOTS_100, TASKS15, TEMPLATE_IDS, TOPUP_MIN_CORRECT, TOPUP_N,
                 append_deviation, catalogue, read_json, read_jsonl, sha256_file, utc_now, write_json)
from commit import commit  # noqa: E402

LABELS = DATA_DIR / "labels.jsonl"
GPU_BUDGET_MIN = {"instr2": 95.0}
DROP_ORDER = ["S2 N 100 -> 50", "MR(0.25) and MR(0.5) dropped (MR(1) kept)", "BMR in the reverse arm",
              "DS/ISO beyond alpha 1", "EARLY/LATE on INTERMEDIATE tasks", "the plain-completion base arm",
              "T(0.25) to N = 30"]
NEVER_DROP = ["base repertoire on 15 tasks with COMMIT #1", "instruct twin", "T(1) on all tasks", "READ(1)",
              "Stage 4 with MR and XT", "novelty audit"]


def labels_by(arm: str | None = None, model_suffix: str | None = None) -> list[dict[str, Any]]:
    out = []
    for r in read_jsonl(LABELS):
        if arm is not None and r.get("arm") != arm:
            continue
        out.append(r)
    return out


def rows_of(labs: list[dict[str, Any]], task: str, arm: str, slots: list[int] | None = None) -> list[dict[str, Any]]:
    s = set(slots) if slots is not None else None
    seen, out = set(), []
    for r in labs:
        if r["task"] == task and r["arm"] == arm and (s is None or int(r["slot"]) in s):
            if r["sample_id"] in seen:
                continue
            seen.add(r["sample_id"])
            out.append(r)
    return out


# ------------------------------------------------------------------------------------------------ COMMIT #0
def commit0() -> dict[str, Any]:
    out_p = PRED_DIR / "commit0.json"
    if out_p.exists():
        return read_json(out_p)
    obj = {
        "protocol": "v5 (iteration 5, Step 1): Claim B (transplant of the base model's task-spec states into the "
                    "instruct prefill reopens the base repertoire), Claim D (push along unit(D) vs isotropic), the "
                    "reverse interchange, plan-site geometry, Claim A screen check, novelty audit. Stages 0-8 as in "
                    "README.md. Thinking off, T = 1.0, top-p 1, no top-k, exact CRN per (task, template, slot).",
        "precision_rule": read_json(PRED_DIR / "precision_rule.json"),
        "input_hashes_sha256": sha256_file(RESULTS_DIR / "input_hashes.json")
        if (RESULTS_DIR / "input_hashes.json").exists() else None,
        "frozen_code_sha256": {f: sha256_file(ROOT / "src" / f) for f in
                               ("analysis_b.py", "commits5.py", "hooks5.py", "gpu5.py", "engine5.py",
                                "labels5.py", "prompts5.py")},
        "thresholds": {"default_share_min": DEFAULT_SHARE_MIN, "beta_diverse": BETA_DIVERSE,
                       "beta_collapsed": BETA_COLLAPSED, "pass_frac_validity": PASS_FRAC,
                       "min_correct_for_correct_basis": 20, "topup_min_correct": TOPUP_MIN_CORRECT,
                       "topup_n": TOPUP_N, "lambda_grid": LAMBDAS, "ds_alphas": DS_ALPHAS,
                       "claim_b_share_frac_of_beta": 0.5, "holm_alpha": 0.05, "specificity_tol": 0.05,
                       "specificity_collapsed_frac": 0.8, "claim_b_confirm_frac": "ceil(2/3 n_div)",
                       "claim_b_disconfirm_frac": "> 1/3 of decisive tasks fail (iii)",
                       "escape_excess": 0.20, "escape_binom_p0": "(twin_k + 0.5)/(twin_n + 1)",
                       "claim_d_dose_ratio": 0.5, "reverse_rise_frac": 0.5, "hill_depth": DEPTH,
                       "n_boot": N_BOOT, "boot_seed": BOOT_SEED, "base_audit_agreement_min": 0.8,
                       "template_robustness_min": "3 of 5"},
        "definitions": A.__doc__,
        "crn_slot_map": {"S1": S1_SLOTS, "S2_N50": S2_SLOTS_50, "S2_N100": S2_SLOTS_100, "DS_slots": DS_SLOTS,
                         "base_chat": "j 0-19 (T1/T2 0-39), top-up j 20-39", "base_plain": "j 0-19",
                         "reverse_base_slots": "key (task, W, j, 'base'), j 0-9",
                         "uniforms": "u_stream(task, W, j) instruct; u_stream(task, W, j, 'base') base model"},
        "derangement_seed": DERANGEMENT_SEED,
        "topup_rule": f"any task other than T1/T2 with < {TOPUP_MIN_CORRECT} correct BASE_CHAT programs gets "
                      f"{TOPUP_N} more (once)",
        "n_policy": {"budget_minutes": GPU_BUDGET_MIN, "drop_order": DROP_ORDER, "never_drop": NEVER_DROP,
                     "floors": "never below 30 on a decisive S1 cell, never below 50 on the S2 decisive arms"},
        "utc": utc_now(),
    }
    write_json(out_p, obj)
    c = commit([out_p], "COMMIT0")
    logger.info(f"COMMIT #0 written: {c}")
    return obj


# ------------------------------------------------------------------------------------------------ base audit
def base_audit_flags() -> dict[str, Any]:
    p = RESULTS_DIR / "base_audit.json"
    return read_json(p) if p.exists() else {}


def secs_per_batch(model: str = "instr") -> float:
    rows = [r for r in read_jsonl(RESULTS_DIR / "timing_batches.jsonl") if r.get("model") == model]
    v = [r["seconds"] for r in rows if r.get("block_id", "").startswith(("S1", "EC", "S3", "S4", "S5", "S6"))]
    return float(np.mean(v)) if v else 12.0


def n_batches(cells: list[tuple[str, list[int]]], B: int = 20) -> int:
    rows = sum(len(js) for _, js in cells)
    return math.ceil(rows / B) * len(TEMPLATE_IDS)


# ------------------------------------------------------------------------------------------------ COMMIT #1
def commit1() -> dict[str, Any]:
    out_p = PRED_DIR / "commit1.json"
    if out_p.exists():
        return read_json(out_p)
    labs = read_jsonl(LABELS)
    audit = base_audit_flags()
    per: dict[str, Any] = {}
    for t in TASKS15:
        cat = catalogue(t)
        tw = rows_of(labs, t, "TWIN", S1_SLOTS)
        d, dshare = A.default_from_twin(tw, DEFAULT_SHARE_MIN)
        bc = rows_of(labs, t, "BASE_CHAT")
        bp = rows_of(labs, t, "BASE_PLAIN")
        bb = A.base_beta(bc, d, cat)
        boot = A.beta_bootstrap(bc, d, cat, N_BOOT, BOOT_SEED)
        bpl = A.base_beta(bp, d, cat)
        corr_labels = [r["label"] for r in bc if A.is_correct(r)]
        per[t] = {"default": d, "twin_default_share": dshare, "twin_S1": {"n": len(tw),
                  "pass": A.pass_rate(tw)[0], "composition_correct": A.composition(tw)},
                  "beta": bb["beta"], "beta_basis": bb["basis"], "beta_k": bb["k"], "beta_n": bb["n"],
                  "n_correct_base": bb["n_correct"], "beta_ci": boot["ci"], "stratum_stability": boot["stability"],
                  "stratum": A.stratum(bb["beta"]) if d is not None else None,
                  "r_t": A.runner_up(bc, d, cat),
                  "base_chat": {"n": len(bc), "pass": A.pass_rate(bc)[0],
                                "composition_correct": A.composition(bc),
                                "composition_attempted": A.composition(bc, correct_only=False)},
                  "base_plain": {"n": len(bp), "pass": A.pass_rate(bp)[0], "beta_plain": bpl["beta"],
                                 "beta_plain_basis": bpl["basis"], "composition_correct": A.composition(bp),
                                 "composition_attempted": A.composition(bp, correct_only=False),
                                 "stratum_plain": A.stratum(bpl["beta"]) if d is not None else None},
                  "base_hill1_rarefied": A.rarefied_hill1(corr_labels, DEPTH, 1000, BOOT_SEED),
                  "predicted_landing": A.runner_up(bc, d, cat),
                  "predicted_landing_composition": A.smoothed_landing(bc, d, cat),
                  "low_confidence": bool(audit.get(t, {}).get("low_confidence", False)),
                  "attempt_flag": bb["basis"] == "ATTEMPT"}
    with_def = [t for t in TASKS15 if per[t]["default"] is not None]
    partner = A.derangement(with_def, DERANGEMENT_SEED)
    BD = [t for t in with_def if per[t]["stratum"] == "BASE-DIVERSE"]
    INT = [t for t in with_def if per[t]["stratum"] == "INTERMEDIATE"]
    COL = [t for t in with_def if per[t]["stratum"] == "BASE-COLLAPSED"]
    k50, k30 = list(range(10)), list(range(6))
    mov = read_json(E22 / "escape.json")
    movable = [t for t in TASKS15 if mov.get(t, {}).get("movable")]
    s5_tasks = [t for t in BD if t in movable] or list(BD)
    s5_desc = not any(t in movable for t in BD)
    # stage 3 cell plan, then the N policy against the measured seconds per batch
    dropped: list[str] = []

    def plan3() -> dict[str, list[tuple[str, list[int]]]]:
        p: dict[str, list[tuple[str, list[int]]]] = {}
        for t in TASKS15:
            cells = [("T1.0", k50)]
            if t in BD or t in INT:
                cells += [("T0.5", k50), ("T0.25", k30 if "T(0.25) to N = 30" in dropped else k50)]
                if t in BD or "EARLY/LATE on INTERMEDIATE tasks" not in dropped:
                    cells += [("EARLY1.0", k50), ("LATE1.0", k50)]
                mr = [("MR1.0", k30)]
                if "MR(0.25) and MR(0.5) dropped (MR(1) kept)" not in dropped:
                    mr = [("MR0.25", k30), ("MR0.5", k30), ("MR1.0", k30)]
                cells += mr
            elif t in COL:
                cells += [("T0.5", k30), ("T0.25", k30)]
            cells += [("READ1.0", k30)]
            p[t] = cells
        return p

    def plan5() -> dict[str, list[tuple[str, list[int]]]]:
        al = [a for a in DS_ALPHAS if not ("DS/ISO beyond alpha 1" in dropped and a > 1.0)]
        return {t: [(f"DS{a}", DS_SLOTS) for a in al] + [(f"ISO{a}", DS_SLOTS) for a in al] for t in s5_tasks}

    def s4_rows() -> int:
        n100 = len(BD) <= 3 and "S2 N 100 -> 50" not in dropped
        per_task = 4 * (100 if n100 else 50)
        return sum(per_task for _ in BD) + 4 * 50 * len(INT)

    spb = secs_per_batch("instr")

    def projection() -> float:
        b3 = sum(n_batches(c) for c in plan3().values())
        b5 = sum(n_batches(c) for c in plan5().values())
        b4 = math.ceil(s4_rows() / 20)
        return (b3 + b4 + b5) * spb / 60.0

    proj0 = projection()
    proj = proj0
    for step in ["S2 N 100 -> 50", "MR(0.25) and MR(0.5) dropped (MR(1) kept)", "DS/ISO beyond alpha 1",
                 "EARLY/LATE on INTERMEDIATE tasks", "T(0.25) to N = 30"]:
        if proj <= GPU_BUDGET_MIN["instr2"]:
            break
        dropped.append(step)
        proj = projection()
    s6 = sorted(BD, key=lambda t: -(per[t]["beta"] or 0))[:4]
    s6_desc = False
    if not s6:
        s6 = sorted(with_def, key=lambda t: -(per[t]["beta"] or 0))[:2]
        s6_desc = True
    obj = {"per_task": per, "partner": partner, "tasks_with_default": with_def,
           "strata": {"BASE-DIVERSE": BD, "INTERMEDIATE": INT, "BASE-COLLAPSED": COL,
                      "NO_DEFAULT": [t for t in TASKS15 if t not in with_def]},
           "n_div": len(BD),
           "claim_b_mode": "DECISIVE" if len(BD) >= 3 else "DESCRIPTIVE (n_div < 3, pre-registered)",
           "stage_sets": {"stage3": TASKS15, "stage4_decisive": BD, "stage4_descriptive": INT,
                          "stage5_desharpen": s5_tasks, "stage5_descriptive_only": s5_desc,
                          "stage6_reverse": s6, "stage6_descriptive_only": s6_desc, "movable_exp22": movable},
           "stage3_plan": plan3(), "stage5_plan": plan5(),
           "lambda_selection_rule": "lambda*_t = argmax correct off-default share (among correct) over lambda in "
                                    "{0.25, 0.5, 1} with pass >= 0.8 x pass(twin S1); ties -> smaller; none -> "
                                    "UNTESTED",
           "validity_gate": "T(0.25) pass < 0.8 x twin on more than half of the tasks with a default -> UNTESTED",
           "mr_breakage_rule": "MR(lambda*) BROKEN if pass < 0.8 x twin (S1, MR(lambda*) cell when run, else the "
                               "nearest MR grid point); lambda' = the largest grid lambda with an unbroken MR; none "
                               "-> ISO(1)",
           "claim_b_rule": "see analysis_b.claim_b_task / claim_b_verdict (frozen in COMMIT #0)",
           "claim_d_rule": "see analysis_b.escapes / claim_d_task / claim_d_verdict",
           "reverse_rule": "default share among correct (primary) and among parseable attempts (co-primary) rises "
                           "by >= 0.5 x (instruct twin share - base twin share)",
           "s2_n_policy": "BASE-DIVERSE: 100 if n_div <= 3 else 50; INTERMEDIATE: 50",
           "n_policy_applied": {"seconds_per_batch": spb, "projection_min_before": proj0, "projection_min": proj,
                                "budget_min": GPU_BUDGET_MIN["instr2"], "dropped": dropped},
           "dropped_arms": (["BMR"] if False else []), "utc": utc_now()}
    write_json(out_p, obj)
    c = commit([out_p], "COMMIT1")
    logger.info(f"COMMIT #1: n_div={len(BD)} BD={BD} INT={INT} COL={COL}; dropped={dropped}; proj {proj:.0f} min; "
                f"{c}")
    return obj


# ------------------------------------------------------------------------------------------------ COMMIT #2
def commit2() -> dict[str, Any]:
    out_p = PRED_DIR / "commit2.json"
    if out_p.exists():
        return read_json(out_p)
    c1 = read_json(PRED_DIR / "commit1.json")
    labs = read_jsonl(LABELS)
    per = c1["per_task"]
    BD, INT = c1["strata"]["BASE-DIVERSE"], c1["strata"]["INTERMEDIATE"]
    sel: dict[str, Any] = {}
    gate_fail = 0
    for t in c1["tasks_with_default"]:
        d, cat = per[t]["default"], catalogue(t)
        tw = rows_of(labs, t, "TWIN", S1_SLOTS)
        twp = A.pass_rate(tw)[0] or 0.0
        cells = {}
        for lam in LAMBDAS:
            rr = [r for r in labs if r["task"] == t and r["arm"] == f"T{lam}" and int(r["slot"]) in S1_SLOTS]
            if rr:
                cells[lam] = {"pass": A.pass_rate(rr)[0], "off_share": A.off_share(rr, d, cat)[0], "n": len(rr)}
        t025 = cells.get(0.25)
        if t025 is not None and A.broken(t025["pass"], twp):
            gate_fail += 1
        mr = {}
        for lam in LAMBDAS:
            rr = [r for r in labs if r["task"] == t and r["arm"] == f"MR{lam}" and int(r["slot"]) in S1_SLOTS]
            if rr:
                mr[lam] = {"pass": A.pass_rate(rr)[0], "off_share": A.off_share(rr, d, cat)[0], "n": len(rr),
                           "broken": A.broken(A.pass_rate(rr)[0], twp)}
        lam_star = A.select_lambda(cells, twp, PASS_FRAC) if (t in BD or t in INT) else None
        mr_broke, lam_p = None, None
        if lam_star is not None:
            if lam_star in mr:
                mr_broke = mr[lam_star]["broken"]
            else:  # nearest MR grid point below
                lower = [l for l in mr if l <= lam_star]
                mr_broke = mr[max(lower)]["broken"] if lower else False
            if mr_broke:
                ok = [l for l, v in mr.items() if not v["broken"]]
                lam_p = max(ok) if ok else None
        sel[t] = {"twin_pass_S1": twp, "T_cells": cells, "MR_cells": mr, "lambda_star": lam_star,
                  "MR_broken_at_lambda_star": mr_broke, "lambda_prime": lam_p,
                  "untested": (t in BD or t in INT) and lam_star is None}
    n_def = len(c1["tasks_with_default"])
    valid = not (gate_fail > n_def / 2)
    n100 = len(BD) <= 3 and "S2 N 100 -> 50" not in c1["n_policy_applied"]["dropped"]
    plan4: dict[str, list[tuple[str, list[int]]]] = {}
    extra5: dict[str, list[tuple[str, list[int]]]] = {}
    if valid:
        for t in BD + INT:
            ls = sel[t]["lambda_star"]
            if ls is None:
                continue
            slots = S2_SLOTS_100 if (t in BD and n100) else S2_SLOTS_50
            cells = []
            if slots == S2_SLOTS_100:
                cells.append(("TWIN", list(range(20, 30))))
            cells += [(f"T{ls}", slots), (f"MR{ls}", slots), (f"XT{ls}", slots)]
            if sel[t]["MR_broken_at_lambda_star"]:
                if sel[t]["lambda_prime"] is not None:
                    cells.append((f"MRP{sel[t]['lambda_prime']}", slots))
                else:
                    cells.append(("ISO1.0", slots))
            plan4[t] = cells
    else:
        append_deviation("F4-validity", "validity gate failed: B = UNTESTED; Stage 4 replaced by descriptive repair "
                                        "previews (T(0.125), MR(0.125), TS(0.5/1), TSMR(1))")
        for t in c1["tasks_with_default"]:
            plan4[t] = [("T0.125", list(range(6))), ("MR0.125", list(range(6))), ("TS0.5", list(range(6))),
                        ("TS1.0", list(range(6))), ("TSMR1.0", list(range(6)))]
    obj = {"selection": sel, "validity_gate": {"n_T025_broken": gate_fail, "n_tasks_with_default": n_def,
                                               "valid": valid},
           "s2_N": {t: (100 if (t in BD and n100) else 50) for t in plan4} if valid else {},
           "stage4_plan": plan4, "stage5_extra": extra5, "utc": utc_now()}
    write_json(out_p, obj)
    c = commit([out_p], "COMMIT2")
    logger.info(f"COMMIT #2: lambda* {({t: v['lambda_star'] for t, v in sel.items()})}; valid={valid}; {c}")
    return obj


if __name__ == "__main__":
    from cfg import setup_logging

    setup_logging("commits5")
    which = sys.argv[1]
    {"0": commit0, "1": commit1, "2": commit2}[which]()
