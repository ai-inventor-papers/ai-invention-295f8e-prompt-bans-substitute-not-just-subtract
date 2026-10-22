#!/usr/bin/env python3
"""S4 commit #1 (before ANY sampling) and S6 commit #2 (after the S5 labels, before any ban sample)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cfg import (ALPHAS_ADD, ALPHAS_RAND, BATCH, DIR_DIR, HEAD_RAND_SEEDS, HEAD_TARGET, PRED_DIR, QUANT, RAND_SEEDS,
                 ROOT, SAMPLED_TASKS, V_BLOCKS, read_json, utc_now, write_json)
from commit import commit
from hooks import head_sets

DECISION_RULES = {
    "C2d": (
        "Per task: avoidance per arm with Wilson CIs; CRN flip tables for ADD vs each RAND at the same alpha; a one-sided "
        "exact McNemar test (H1: ADD avoidance > RAND avoidance), Holm over 3 controls x 2 alphas. A task PASSES ADD if, "
        "at some alpha in {1, 2}, all three Holm-adjusted p < 0.05 AND ADD's modal non-default label (requiring >= 10 "
        "non-default attempts) equals the named ban's modal non-banned label. Denominator = tasks where the named ban "
        "passes the EVENT GATE (avoidance >= 0.5 AND >= 20 non-banned attempts). On gate-failing tasks only the "
        "avoidance contrast is reported. SUBTRACT: for each task, Delta = banned share(SUB_plain) - banned share(ban, "
        "same slots), with a paired bootstrap CI over slots. Pooled Delta = the mean over the GATED tasks (those where "
        "the named ban's banned share is <= 0.5), with a task-level bootstrap and jackknife. C2d SUPPORTED iff ADD "
        "passes on >= 2/3 of the denominator tasks AND pooled Delta >= 0.3 with the CI lower bound > 0. DISCONFIRMED "
        "iff ADD avoidance is within the random range (not above max RAND) on > 1/3 of the tasks. Otherwise PARTIAL. "
        "Necessity is credited to v only if SUB_plain or SUB_affine exceeds SUB_rand by >= 0.15."),
    "C2e": (
        "Classes: 1 = default mechanism (incl. renamed/disguised defaults), 0 = any other attempted label incl. "
        "'other'; 'invalid' and 'disputed' excluded. Eligible tasks have >= 8 of each class in the named-ban samples "
        "(T1 primary includes the declared W4 top-up: 100 + 60). Per position in {R, S-mean, 1..8, 16} and block "
        "8..28: L2 logistic (batched IRLS; C by inner 3-fold CV from {1e-3,1e-2,1e-1,1}) on standardised states "
        "after PCA-64 fit on the training fold; 5-fold stratified by (template, class); pooled balanced accuracy; "
        "null = 500 within-template label permutations with full refits and a layer-max statistic per position. "
        "Text controls at each k (all with template one-hot): Ta one-hot token ids at 1..k; Tb layer-0 embeddings "
        "(mean of 1..k concatenated with token k), PCA-64; Tc exact prefix-match leave-one-out majority within "
        "template (fallback: template majority). R baseline = decoder at R (template-only by construction). "
        "LOCUS RULE (frozen): the first k in 1..8 at which max over blocks of state BA >= max(BA_R, BA_Ta, BA_Tb, "
        "BA_Tc) + 0.10 AND state BA > the layer-max null q95. 'Locus at tokens 1-3' requires k <= 3. Non-eligible "
        "tasks are 'not testable'. Conditional causal patch only if a locus (k*, L*) is found."),
    "C2f": (
        "Banned share for the target head set {L21H17, L26H21, L26H25} and each of 3 layer-matched random sets "
        "(k 0-9 slots), CRN flip tables against the no-ablation ban. Delta_T1 = target - mean(random). SUPPORTED iff "
        "Delta_T1 >= 0.15 (exact paired test against each random set, p < 0.05) AND |Delta_T2| <= 0.10 (90% CI "
        "reported)."),
    "0g": (
        "FR_zero = (CE_zero - CE_sae) / (CE_zero - CE_clean). FROZEN PASS(L) := FR_zero(instruct, own text) >= 0.9 x "
        "FR_zero(base, own text). Companions: FR_mean, KL(clean||spliced), dCE ratio on own text, FVU and L0, "
        "displacement preservation cos(SAE(h_ban) - SAE(h_twin), h_ban - h_twin) and norm ratio at S. 5a stays "
        "descriptive whatever 0g shows (the zero-ablation denominator of ~12 nats makes the frozen rule lenient)."),
    "event_gate": "named ban avoidance >= 0.5 AND >= 20 non-banned attempts",
    "best_alpha": "alpha in {1, 2} with the highest avoidance among those with pass rate >= 0.5; ties -> alpha 1",
}

PREDICTIONS = {
    "P1": "ADD at alpha 1 or 2 beats every random control on >= 2/3 of the gated tasks and lands on the named ban's "
          "modal survivor.",
    "P2": "SUB raises the banned share by >= 0.3.",
    "P3": "C2e: no position beats the text controls by 0.10. State and text curves rise together at the first "
          "divergent token; the expected T2 fork is the import line, tokens 3-5.",
    "P4": "C2f: T1 banned share rises >= 0.15 over random heads, T2 is unchanged.",
    "P5": "0g: PASS by the frozen rule, with expected FR_zero about 0.98-0.995 for both models.",
}


def write_commit1() -> dict[str, Any]:
    hs = head_sets(HEAD_RAND_SEEDS)
    doc = {
        "created_utc": utc_now(),
        "quantisation": QUANT,
        "direction_sha256": read_json(DIR_DIR / "direction_hashes.json"),
        "random_direction_seeds": list(RAND_SEEDS),
        "alpha_grid": {"ADD": list(ALPHAS_ADD), "RAND": list(ALPHAS_RAND)},
        "hooked_blocks": V_BLOCKS,
        "head_sets": {"target": HEAD_TARGET, **hs},
        "head_rand_seeds": list(HEAD_RAND_SEEDS),
        "uniform_key": "u_stream(task, template, k) = PCG64(stable_seed(task, template, k)), identical in every arm",
        "batch_layout": f"every batch has {BATCH} rows of one (task, template): one 20-slot block or two 10-slot "
                        "blocks; prune=False",
        "decision_rules": DECISION_RULES,
        "predictions": PREDICTIONS,
        "t1_w4_topup_in_c2e_primary": True,
        "sampled_tasks": list(SAMPLED_TASKS),
        "deviations_declared_before_sampling": [
            "FP8 W8A8-dynamic quantisation of the pinned bf16 weights (16 GB RTX 2000 Ada; F2 named bnb-8bit only "
            "because it assumed a GPU without FP8 support)",
            "batch of 20 rows (two 10-slot blocks) instead of 10; N=50 arms that cannot be paired in a batch get the "
            "slots k 10-19 as extra rows (N=100) rather than idle padding",
            "analysis code is hash-committed at commit #2 (still before any ban sample); the decision rules above "
            "are committed verbatim here",
        ],
    }
    p = PRED_DIR / "commit1.json"
    write_json(p, doc)
    files = [p] + sorted(DIR_DIR.glob("*.npy")) + [ROOT / "prompts" / "prompts.jsonl"] + \
        sorted((ROOT / "src").glob("*.py"))
    return {"doc": doc, "chain": commit(files, "commit1")}


def write_commit2(landings: dict[str, Any], c1: dict[str, Any]) -> dict[str, Any]:
    p1 = PRED_DIR / "c2d_landings.json"
    p2 = PRED_DIR / "c1_forecasts.json"
    write_json(p1, landings)
    write_json(p2, c1)
    files = [p1, p2] + sorted((ROOT / "src").glob("*.py")) + sorted((ROOT / "src" / "analysis").glob("*.py"))
    return {"chain": commit(files, "commit2")}
