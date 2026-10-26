#!/usr/bin/env python3
"""S3 commit #0: pre-registration of the C1-seed 2x2 (thresholds, definitions, analysis code, screen hash, power
expectation, the arm-(ii) selection rule, drop order, guards), hash-chained in commitments.log BEFORE any decisive
sample. Never edit a committed file; amendments are new committed files (commit(paths, tag)).

commitments.log: one JSON line per file {utc, file, sha256, prev_chain, chain = sha256(prev_chain + sha256), tag}.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger

from cfg import D_MODEL, PRED_DIR, RESULTS_DIR, ROOT, read_json, rel, sha256_file, sha256_text, utc_now, write_json
from cfg4 import (ANSWER_MAX, C1_EVENT_SET, DEFAULT4, FIRST_APPROACH_LEXICON, MAX_MODEL_LEN, MAX_NEW4, MINP_P, MINP_T,
                  PN_ALPHAS, PN_SEEDS, PN_TEMPS, SEED_K, TEMPS, THINK_CAP, TOPK_K, TOPK_T, TPN_ALPHA, TPN_MAX_NEW, TPN_T)

LOG = ROOT / "commitments.log"
PREREG = PRED_DIR / "prereg_c1seed.json"


def last_chain() -> str:
    if not LOG.exists():
        return "0" * 64
    lines = [l for l in LOG.read_text().splitlines() if l.strip()]
    return json.loads(lines[-1])["chain"] if lines else "0" * 64


def commit(paths: list[Path], tag: str) -> list[dict[str, Any]]:
    out = []
    prev = last_chain()
    with open(LOG, "a") as fh:
        for p in paths:
            h = sha256_file(p)
            chain = sha256_text(prev + h)
            rec = {"utc": utc_now(), "file": rel(p), "sha256": h, "prev_chain": prev, "chain": chain, "tag": tag}
            fh.write(json.dumps(rec) + "\n")
            fh.flush()
            out.append(rec)
            prev = chain
    return out


def verify_chain() -> dict[str, Any]:
    prev = "0" * 64
    n = bad = changed = 0
    first: dict[str, str] = {}
    if not LOG.exists():
        return {"n_lines": 0, "chain_breaks": 0}
    for line in LOG.read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        ok = r["prev_chain"] == prev and sha256_text(prev + r["sha256"]) == r["chain"]
        bad += not ok
        p = ROOT / r["file"]
        changed += (not p.exists()) or sha256_file(p) != r["sha256"]
        first.setdefault(r["tag"], r["utc"])
        prev = r["chain"]
        n += 1
    return {"n_lines": n, "chain_breaks": bad, "files_changed_since_commit": changed, "first_utc_by_tag": first}


def make_directions() -> dict[str, str]:
    """D1-D6: normalised PCG64(seed).standard_normal(4096) (the exp17 _RandDirs construction)."""
    out = {}
    for s in PN_SEEDS:
        p = ROOT / "directions" / f"rand_{s}.npy"
        if not p.exists():
            x = np.random.Generator(np.random.PCG64(s)).standard_normal(D_MODEL)
            np.save(p, (x / np.linalg.norm(x)).astype(np.float32))
        out[p.name] = sha256_file(p)
    return out


def commit0() -> dict[str, Any]:
    if LOG.exists() and "prereg_c1seed.json" in LOG.read_text():
        logger.info("commit #0 already in commitments.log; nothing to do")
        return verify_chain()
    tests = read_json(RESULTS_DIR / "tests_cpu.json")
    assert tests.get("all_pass"), "analysis code must pass its synthetic tests before commit #0"
    dirs = make_directions()
    exp = read_json(RESULTS_DIR / "expectations.json")
    screen_sha = sha256_file(RESULTS_DIR / "screen.json")
    analysis_files = sorted((ROOT / "analysis").glob("*.py"))
    pre = {
        "id": "prereg_c1seed", "created_utc": utc_now(),
        "claim": "C1-seed: under one fixed token-noise stream per seed, temperature changes the algorithm (idea) "
                 "almost never while plan noise at the task-spec states (blocks 12-23, prefill only) changes it in a "
                 "substantial share of seeds; temperature changes phrasings.",
        "model": {"id": "Qwen/Qwen3-8B", "revision": "b968826d9c46dd6066d109eabc6255188de91218",
                  "hf_engine": "exp17 FP8 W8A8 (per-output-channel weight / per-token activation scales; lm_head, "
                               "embeddings, norms bf16) on the 16 GB RTX 2000 Ada (the screen's card)",
                  "vllm_engine": "Qwen/Qwen3-8B-FP8 (vLLM 0.11.0, weight-only FP8 Marlin, eager)"},
        "seeds": {"definition": "slot (task, w, k), w in W1-W5, k in 0-3 (20 per task); the screen's NEUTRAL slot "
                                "keys; uniforms u_stream(task, w, k, n = max_new) (PCG64 prefix property: the 1,536 "
                                "stream extends the 1,024 one)", "k": list(SEED_K)},
        "couplings": {"thinking_off_primary": "inverse-CDF in vocabulary order (float64 CDF, one PCG64 uniform per "
                                              "row and step, prune=False, fixed batch shape B per task)",
                      "thinking_on": "vLLM exponential race (Gumbel-max) with per-request seed stable_seed(task,w,k)",
                      "gumbel_replicate_iii": "HF exponential race with per-row CUDA generator seeded "
                                              "stable_seed(task, w, k, 'gumbel'), step-indexed",
                      "caveat": "off/on change counts use different couplings; every count is labelled with its "
                                "coupling; arm (iii) reruns the T2/T03 NO-PN block and the alpha-1 T1.0 PN block "
                                "under Gumbel-max"},
        "conditions_thinking_off": {
            "NOPN": [f"T{t}" for t in TEMPS] + [f"TOPK{TOPK_K} at T{TOPK_T}"], "top_p": 1.0,
            "PN": {"directions": {f"D{i + 1}": s for i, s in enumerate(PN_SEEDS)}, "direction_sha256": dirs,
                   "alphas_ban_units": list(PN_ALPHAS), "temperatures": list(PN_TEMPS)},
            "filler_repeats": "G_clean, T1.0, slots k 0-3, different batch-mates (noise floor)",
            "max_new": MAX_NEW4},
        "unit": {"T1": "exp17 directions/norms_T1.npy", "T2": "exp17 directions/norms_T2.npy",
                 "T03": "exp13 results/tensors/norms_T03.npz['norm'] (protocol v4)",
                 "engine_check_T03": "exp17 directions/norms_T03.npy (to match the screen)",
                 "T03_unit_ratio_exp17_over_exp13": read_json(RESULTS_DIR / "screen.json")["T03_unit_comparison"]},
        "hook": "exp17 make_edits('RAND', u = D_d, alpha): h <- h + (alpha n[l,p] - (h - h_twin_clean).u) u on block "
                "outputs 12-23, positions S = [p1, spec_end), fp32, prefill only; h_twin_clean from the clean twin "
                "prefill of the same template",
        "batch_rule": "B per task = largest of {20, 10, 5} with B * (P + max_new + 1) * 147,456 <= 0.85 * free VRAM "
                      "after loading; constant across all of that task's arms",
        "layout_rule": "per (task, template): 120 rows (NOPN 20, PN 96, filler 4); tier 0 = NOPN + alpha-1 PN + "
                       "filler, tier 1 = alpha-2 PN; within a tier rows are sorted by (temperature descending, group, "
                       "slot) and cut into batches of B; filler rows are placed after their originals so each repeat "
                       "has different batch-mates (deterministic = committed permutation); tier 1 runs last",
        "labels": {"modes": "catalogue modes + 'other'; 'invalid' (no code, syntax error, crash before the first "
                            "traced op) and 'unresolved' (incl. 'disputed') excluded from change counting",
                   "defaults": DEFAULT4,
                   "sensitivities": ["correct_only", "invalid_as_label", "TOPK10 as 5th condition",
                                     "all 6 temperature pairs", "with the min-p cell"],
                   "primary_population": "VALID programs (attempted ideas); correct-only is the sensitivity"},
        "definitions": {
            "changed_T": "1 if the seed's valid labels over {NOPN T0.3, T0.7, T1.0, T1.3} contain >= 2 distinct "
                         "values (>= 2 valid labels required, else not countable)",
            "changed_PN": "same over {NOPN at T} + {PN(d, alpha, T) for d in S}",
            "C_T": "sum of changed_T over countable seeds (n reported)",
            "C_PN": "mean over all C(6,3) = 20 subsets S of sum_s changed_PN(s; S)",
            "x_s": "(mean over countable subsets of changed_PN(s; alpha 1, T1.0)) - changed_T(s)"},
        "thresholds": {
            "H-T": "C_T <= 1 of 20 in each of 4 cells: T1, T2, T03 thinking off; T2 thinking on (seeds complete at "
                   "all 4 temperatures, n reported)",
            "H-PN": "C_PN(alpha 1, T 1.0) >= 5 of 20 on T2 AND on T03",
            "H-PHR": "pooled slope of log(PPI) on T > 0 with the 95% seed-bootstrap CI excluding 0, at every theta in "
                     "{0.7, 0.8, 0.9}",
            "H-CON": "one-sided sign-flip permutation p < 0.05 for mean x_s > 0, pooled over T2 and T03 (40 seeds); "
                     "100,000 draws; the artifact's single entry to the iteration's secondary Holm family (C1-seed)"},
        "outcomes": {"CONFIRMED": "H-T and H-PN and H-PHR and H-CON",
                     "DISCONFIRMED": "pooled mean x_s <= 0, or C_T >= C_PN(alpha 1, T1.0) on both T2 and T03",
                     "PARTIAL": "anything else, naming the part that failed (e.g. 'temperature inert but PN weaker "
                                "than predicted' when H-T holds and C_PN in [1, 4])"},
        "descriptive_expectations": {
            "TOPK10_T0.7_hill1": "<= 1.10 on all 3 tasks",
            "hill1_PN_a1_T0.7_vs_TOPK10": "Hill-1(PN alpha 1, T0.7, depth 20) > Hill-1(TOPK10 at T0.7) on T03 and T2",
            "PN_landings": {"T03": "size-k heap or quickselect", "T2": "Bellman-Ford/SPFA", "T1": "DFS or none"},
            "interaction": "under escaping directions, T0.7 vs T1.0 changes the label in more seeds than under no PN",
            "optional_ii": "the first approach named moves in >= 3 of 10 seeds for at least one direction"},
        "phrasing": {"shingles": "ast.parse; docstrings dropped (comments never reach the AST); identifiers renamed "
                                 "in first-appearance order; constants -> type; pre-order node types + operators + "
                                 "attribute names; 4-grams; Jaccard", "thetas": [0.7, 0.8, 0.9],
                     "clusters": "connected components at Jaccard >= theta within each (condition, idea); complete "
                                 "linkage as robustness", "PPI": "clusters / ideas present",
                     "rarefaction": "PN cells rarefied to depth 20 by drawing one direction per seed (1,000 draws)",
                     "slope": "OLS slope of log PPI on T per task over the 4 NOPN cells; seed bootstrap 2,000 reps "
                              "(each seed's coupled programs resampled together); pooled = mean of task slopes"},
        "thinking_on": {"T": list(TEMPS), "top_p": 1.0, "top_k": "off", "cap": THINK_CAP, "answer_max": ANSWER_MAX,
                        "max_model_len": MAX_MODEL_LEN, "repeat": "T0.7 x 20 seeds, reverse order, interleaved",
                        "first_approach_lexicon": FIRST_APPROACH_LEXICON,
                        "primary": "seeds complete at all 4 temperatures; forced-close labels as sensitivity"},
        "optional_arms": {"ii": {"what": "PN with thinking on, T2, 10 seeds (W1-W5 x k 0-1) x {no PN, 3 directions "
                                         f"at alpha {TPN_ALPHA}}}, T {TPN_T}, max_new {TPN_MAX_NEW}",
                                 "selection_rule": "the 3 of the 6 directions with the highest alpha-2 T0.7 off-default "
                                                   "share on T2 (thinking off, this 2x2); ties broken by seed"},
                          "iii": "Gumbel-max replicate on T2 and T03: NOPN x 4 T x 20 seeds + PN alpha 1 T1.0 x 6 x 20",
                          "iv": f"min-p extended dial: NOPN T{MINP_T}, min-p {MINP_P}, 20 seeds x 3 tasks",
                          "i": "T1 thinking on (vLLM), only if >= 1.5 h of wall clock remain"},
        "drop_order": ["optional (ii)", "optional (i)", "(iii) Gumbel replicate", "(iv) min-p cell",
                       "alpha-2 PN block on T1", "thinking-on repeat halved to 10 seeds"],
        "never_drop": ["NOPN block (3 tasks)", "alpha-1 PN block on T2 and T03", "thinking-on T2 arm (80 traces)",
                       "engine check", "commit #0"],
        "wall_clock_guards": {"G1_done_by": "t0 + 2h15", "G2_core_done_by": "t0 + 4h00",
                              "analysis_export_start_by": "t0 + 4h45", "t0": read_json(RESULTS_DIR / "t0.json")},
        "engine_check": {"T03": "per template one 20-row batch: NEUTRAL k 0-9 + RAND9002 alpha 1 k 0-9 (exp17 unit)",
                         "T2": "NEUTRAL k 0-9 + RAND9004 alpha 1 k 0-9 at the task's B", "T": 1.0,
                         "verdict_rule": "REPRODUCED if JS(this run, screen) <= the template-resampling null p95 for "
                                         "all four compositions, else PRECISION-SENSITIVE (logged addendum, no "
                                         "threshold change)"},
        "screen": {"file": "results/screen.json", "sha256": screen_sha},
        "power_expectation": exp,
        "C1_event_set_frozen": C1_EVENT_SET,
        "multiplicity": "one p-value (H-CON pooled sign-flip) enters the iteration's secondary Holm family as C1-seed",
        "analysis_code_sha256": {rel(p): sha256_file(p) for p in analysis_files},
        "cpu_tests": {k: v.get("pass") for k, v in tests.items() if isinstance(v, dict)},
    }
    write_json(PREREG, pre)
    files = [PREREG, *analysis_files, ROOT / "tests/test_analysis.py", RESULTS_DIR / "tests_cpu.json",
             RESULTS_DIR / "screen.json", RESULTS_DIR / "expectations.json", ROOT / "src/cfg4.py",
             ROOT / "src/screen.py", ROOT / "src/vllm_think.py", ROOT / "src/prereg.py",
             *[ROOT / "directions" / n for n in sorted(dirs)]]
    recs = commit(files, "commit0")
    logger.info(f"commit #0: {len(recs)} files; chain head {recs[-1]['chain'][:16]} at {recs[-1]['utc']}")
    return verify_chain()


def amend(paths: list[Path], tag: str) -> list[dict[str, Any]]:
    recs = commit(paths, tag)
    logger.info(f"commit {tag}: {[r['file'] for r in recs]}")
    return recs
