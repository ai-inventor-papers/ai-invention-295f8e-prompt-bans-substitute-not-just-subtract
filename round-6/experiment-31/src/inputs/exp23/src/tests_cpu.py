#!/usr/bin/env python3
"""CPU tests (testing plan T1-T6) -> results/tests_cpu.json.
T1 bench sha256 vs commitment.json; T2 labeller re-check; T3 Gemma prompts (rendering, one BOS, spec_start on a token
boundary, twin/ban id alignment for 15 x 5, tokenizer only); T4 grep audit on planted positives; T5 analysis
self-tests + the frozen analysis on the iteration-3 screen rows (Qwen3-8B: screen E_t vs its own ban compliance) +
the screen reproduction; T6 label-permutation placebos null-centred."""

from __future__ import annotations

import collections
import sys
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg import (ALL_TASKS, E13, E17, PRED_DIR, QWEN_DEFAULT, RESULTS_DIR, TEMPLATE_IDS, TEMPLATES, read_json,
                 read_jsonl, setup_logging, write_json)
import analysis_c3 as A
import prompts_gemma as PG


def t3_prompts() -> dict[str, Any]:
    c1 = read_json(PRED_DIR / "commit1.json")
    bad = []
    n = 0
    for t in ALL_TASKS:
        X = c1["pilot"][t]["D_g"]
        for w in TEMPLATE_IDS:
            tw = PG.p_twin(t, X, w)
            n += 1
            if not PG.aligned_with_ban(t, X, w):
                bad.append(f"{t}/{w}")
            assert tw["ids"][0] == 2 and tw["ids"].count(2) == 1
    return {"pairs_checked": n, "misaligned": bad, "pass": not bad}


def t4_grep() -> dict[str, Any]:
    planted = [("ban", PG.TEMPLATES["W1"][0].format(X=PG.display("T03", "full_sort")) + "\n\n" + PG.spec_text("T03")),
               ("ban_cap", PG.TEMPLATES["W4"][0].format(X=PG.cap_first(PG.display("T05", "hash_map"))))]
    clean = [("twin", PG.p_twin("T03", "full_sort", "W1")["text"]), ("novelty", PG.p_novelty("T03")["text"]),
             ("association", PG.p_assoc("T03", "full_sort")["text"]), ("forced", PG.p_forced("T03", "quickselect", 0)["text"]),
             ("nonce", TEMPLATES["W2"][0].format(X="the Zorblax method"))]
    a = PG.grep_audit(planted, list(ALL_TASKS))
    b = PG.grep_audit(clean, list(ALL_TASKS))
    return {"planted_hits": a["n_hits"], "clean_hits": b["n_hits"], "pass": a["n_hits"] >= 2 and b["n_hits"] == 0}


def qwen_screen_rows() -> dict[str, Any]:
    """Iteration-3 Qwen: screen E_t (results/screen.json) vs catalogue-only ban avoidance from exp13/exp17 ban rows."""
    scr = read_json(RESULTS_DIR / "screen.json")["tasks"]
    e13 = read_jsonl(E13 / "data" / "samples.jsonl")
    e17 = read_jsonl(E17 / "data" / "labels.jsonl")
    E, Av = {}, {}
    for t, v in scr.items():
        D = QWEN_DEFAULT[t]
        cat = set(PG.modes(t))
        bans = [r for r in e17 if r["task"] == t and r["arm"] == "BAN"] or \
               [r for r in e13 if r["task"] == t and r.get("condition") == "ban"]
        if not bans or v.get("E_t") is None:
            continue
        E[t] = v["E_t"]
        Av[t] = sum(1 for r in bans if r["label"] in cat and r["label"] != D) / len(bans)
    tasks = sorted(E)
    r = A.c3a(tasks, E, Av, n_perm=20000, n_boot=500)
    return {"tasks": tasks, "E_t": E, "A_t": Av, "BA": r["balanced_accuracy"]["BA"], "fisher": r["fisher"],
            "rho": r["spearman"]["rho"], "verdict_on_screen_data": r["verdict"],
            "note": "in-sample (the rule was frozen from these data); a dry run of the frozen analysis code"}


def t6_placebo() -> dict[str, Any]:
    rng = np.random.default_rng(11)
    tasks = [f"t{i}" for i in range(15)]
    ps, bas = [], []
    for k in range(30):
        E = {t: float(rng.choice([0, 0.125, 0.25, 0.5])) for t in tasks}
        Av = {t: float(rng.random()) for t in tasks}
        r = A.c3a(tasks, E, Av, n_perm=2000, n_boot=50, seed=k)
        if r["spearman"]["p_one_sided"] is not None:
            ps.append(r["spearman"]["p_one_sided"])
        if r["balanced_accuracy"]["BA"] is not None:
            bas.append(r["balanced_accuracy"]["BA"])
    return {"mean_null_p_one_sided": float(np.mean(ps)), "mean_null_BA": float(np.mean(bas)),
            "pass": 0.3 < np.mean(ps) < 0.7 and 0.35 < np.mean(bas) < 0.65}


def main() -> None:
    setup_logging("tests_cpu")
    ih = read_json(RESULTS_DIR / "input_hashes.json")
    lr = read_json(RESULTS_DIR / "labeller_recheck.json")
    scr = read_json(RESULTS_DIR / "screen.json")
    res = {"T1_bench_sha256": {"pass": ih["pass"], "mismatches": ih["mismatches"]},
           "T2_labeller_recheck": {"bench_all_reproduce_gate": all(v["reproduces_gate"] for v in lr["bench"].values()),
                                   "bench_all_references_pass": all(v["references_pass"] for v in lr["bench"].values()),
                                   "suite_references": f"{lr['exp8_suite']['references_ok']}/{lr['exp8_suite']['n_references']}",
                                   "suite_gold_runtime_acc": lr["exp8_suite"].get("acc_runtime_vs_adjudicated"),
                                   "suite_gate_runtime_acc": lr["exp8_suite"].get("gate_acc_runtime"),
                                   "suite_reproduces_gate": lr["exp8_suite"].get("reproduces_gate_runtime")},
           "T3_prompts": t3_prompts(), "T4_grep": t4_grep(), "T5_analysis_selftest": A.self_test(),
           "T5_screen_reproduction": {k: v["match"] for k, v in scr["t5_reproduction"].items()},
           "T5_frozen_analysis_on_iteration3_screen": qwen_screen_rows(), "T6_placebo": t6_placebo()}
    write_json(RESULTS_DIR / "tests_cpu.json", res)
    print({k: (v.get("pass") if isinstance(v, dict) else v) for k, v in res.items()})
    print(res["T5_frozen_analysis_on_iteration3_screen"])


if __name__ == "__main__":
    main()
