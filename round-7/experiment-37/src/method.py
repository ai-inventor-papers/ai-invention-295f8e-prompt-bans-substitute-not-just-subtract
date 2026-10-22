#!/usr/bin/env python3
"""Evolving programs to find new algorithms (iteration 7, claim N): stage CLI.

  uv run method.py --stage inputs      # STEP 1: vendor non-declared inputs, build + verify the 3 task objects
  uv run method.py --stage corpus      # STEP 2: known-solution corpus (18,237) + catalogue references
  uv run method.py --stage tests       # STEP 3: CPU unit tests U1-U5 (pytest)
  uv run method.py --stage commit0     # STEP 5: commit #0 (before ANY GPU sample)
  uv run method.py --stage calib       # STEP 4: GPU smoke/engine check, calibration pool, throughput pilot
  uv run method.py --stage commit1     # STEP 5: s*_task, seed pools, measured throughput, final N per arm
  uv run method.py --stage base        # STEP 6: Qwen3-8B-Base BINT intents
  uv run method.py --stage run         # STEP 6: arms S, NE, I0, EAP, BINT, B0 per task
  uv run method.py --stage L           # STEP 6 L4: large-mutator arm on T03 via OpenRouter (optional)
  uv run method.py --stage label       # final labels (dispute judge), OOC screen
  uv run method.py --stage adjudicate  # STEP 7: dedup, clusters, candidates, control gate, judges (commit #2 inside)
  uv run method.py --stage analyse     # STEP 8
  uv run method.py --stage outputs     # STEP 9: samples.jsonl, figures, method_out.json, audit
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from loguru import logger  # noqa: E402

from common import (CAP_TOTAL_USD, PRED, RESULTS, TASKS, commit, read_json, set_ram_limit, setup_logging,  # noqa: E402
                    sha256_file, utc_now, write_json)

HYPOTHESIS = (
    "Claim N (iteration 7, secondary family): a FunSearch / MAP-Elites program search with Qwen3-8B (bf16, thinking "
    "off, vLLM, T 1.0) as the mutator, hidden tests plus fresh randomised stress tests as the evaluator, and a novelty "
    "critic built against the 18,237 known solutions of art_j3Rm_lr2nzR6 produces correct out-of-catalogue programs "
    "at a much higher rate per call than the best single-sample text knobs of iteration 5, on memorised "
    "LeetCode-style tasks with one 8B mutator.")
PREDICTION = ("S >= 10x K on >= 2 tasks: per task the point estimate R_hat = (X_S/N_S)/(X_K/N_K) >= 10 and the exact "
              "conditional Poisson one-sided 95% lower bound LB95 on R above 1, at level a (distinct OOC_screen "
              "programs), K = the better of EAP and BINT per task (max rule). With 2 tasks run, MET needs both.")
LADDER = {
    "level0": {"T2": {"S": 1500, "EAP": 750, "BINT": 750, "NE": 500, "I0": 500, "B0": 200},
               "T03": {"S": 1500, "EAP": 750, "BINT": 750, "NE": 500, "I0": 500, "B0": 200}},
    "level1": {"A3": {"S": 1000, "EAP": 500, "BINT": 500, "NE": 300, "I0": 300, "B0": 100}},
    "level2": "raise S on T03 then T2 in +1000 steps up to 4000 while time allows; K arms >= S/2",
    "level3": "reachability (prompt_logprobs teacher forcing) - optional",
    "level4": "large mutator arm L on T03 via OpenRouter, 500 children, <= USD 1.0 - optional, concurrent",
    "level5": "plan noise - first dropped",
    "floors": {"S": 1000, "EAP": 400, "BINT": 400, "NE": 300, "I0": 300, "B0": 100},
    "drop_order": ["plan_noise", "L (only if OpenRouter binds)", "reachability", "A3", "I0->300,B0->100",
                   "K arms->500", "S->1500->1000 on T2/T03"],
}
DEFINITIONS = {
    "call": "one generated child program (one completion); EAP/BINT count only code-writing calls, their stage-1 GPU "
            "time is charged to their GPU-seconds",
    "correct": "valid (AST pre-screen) AND stage 1 (8 quick cases) AND stage 2 (full hidden suite) AND stage 3 (10 "
               "seeded max-size stress inputs vs the fastest reference)",
    "OOC_screen": "correct AND (final label == 'other' OR nearest-known Jaccard s < s*_task), s*_task = 5th "
                  "percentile of nearest-known similarities of correct forced catalogue programs (label == Y) and "
                  "the references",
    "distinct": "within an arm in call order: identical normalised-token hash merges, then Jaccard >= 0.9 to an earlier "
                "program collapses into it",
    "idea_cluster": "pooled over arms, within each cell (runtime label, DS-signature): single-linkage components at "
                    "Jaccard >= 0.5; after adjudication clusters whose judges named the same algorithm merge",
    "level_a": "distinct OOC_screen programs", "level_b": "distinct adjudicated KNOWN OUTSIDE CATALOGUE + NOVEL",
    "cell": "(runtime label, DS-signature = first 3 of heap, deque_or_queue, sort, bisect, recursion, dict_or_counter, "
            "set, matrix_2d, stack_list, bitops, random, custom_class)",
    "novelty": "nu = 1 - s, s = max token-4-gram Jaccard to corpus + catalogue references (self-match of a seed excluded)",
}
TESTS = {
    "primary": "exact conditional binomial test of two Poisson rates; LB95 from the one-sided Clopper-Pearson bound; "
               "two-sided 95% CI; Holm across tasks",
    "verdict": "STRONG LB95>=10; MET R_hat>=10 & LB95>1; UNRESOLVED R_hat>=10 & LB95<=1; NOT MET R_hat<10; "
               "NOT ESTIMABLE X_S=X_K=0; overall MET if >=2 tasks MET/STRONG",
    "secondary": ["S vs NE", "S vs I0", "NE vs I0", "I0 vs K", "K vs B0", "L vs S (first 500 calls, T03)"],
    "matched_effort": "rarefaction/Chao-1 extrapolation of idea-cluster richness of i.i.d. arms to N_S (trusted to 2x N)",
    "robustness": "island-cluster bootstrap (2,000 reps) of S's rate; arm-shuffle placebo; seeds-as-children check",
    "zero": "rule of three 3/n",
}
JUDGES = {"pair": ["mistralai/mistral-medium-3.1", "moonshotai/kimi-k2-0905"],
          "replacements": ["google/gemini-2.5-flash", "deepseek/deepseek-chat-v3.1", "openai/gpt-4.1-mini"],
          "third": "deepseek/deepseek-chat-v3.1", "temperature": 0, "gate": ">= 9 of 10 controls",
          "label_dispute_judge": "google/gemini-2.5-flash-lite",
          "L_mutator": "qwen/qwen3-235b-a22b-2507", "L_fallback": "qwen/qwen3-coder"}
JUDGE_PROMPT = (
    "You are an expert in algorithms. Decide whether the program below implements a NEW algorithm for a known task.\n\n"
    "TASK\n{spec}\n\nCATALOGUE (the standard known algorithms for this task)\n{catalogue}\n\n"
    "PROGRAM UNDER REVIEW (comments and docstrings removed)\n```python\n{code}\n```\n\n"
    "NEAREST KNOWN SOLUTIONS from a corpus of 18,237 published code solutions (for comparison)\n{nearest}\n\n"
    "SANDBOXED STRESS RESULTS of the program (inputs at three sizes; runtime ratio to the fastest catalogue "
    "reference; log-log slope of runtime against size)\n{stress}\n\n"
    "Classify the program's core algorithm into exactly one class:\n"
    "- NOVEL ALGORITHM: a correct general algorithm whose core mechanism is not in the catalogue and that you cannot "
    "identify as any known published algorithm or textbook technique.\n"
    "- KNOWN OUTSIDE CATALOGUE: a correct general algorithm that is a known, nameable algorithm or textbook technique "
    "not in the catalogue (name it).\n"
    "- CATALOGUE VARIANT: an implementation, restyling or minor modification of a catalogue algorithm (name which).\n"
    "- DEGENERATE: hard-coded or special-cased answers, wrong in general, or brute force that passes only because "
    "the tests are small.\n\n"
    "Answer with JSON only: {{\"class\": \"NOVEL ALGORITHM|KNOWN OUTSIDE CATALOGUE|CATALOGUE VARIANT|DEGENERATE\", "
    "\"named_algorithm\": \"...\", \"core_idea\": \"<one sentence>\", \"confidence\": <0 to 1>, "
    "\"rationale\": \"<at most two sentences>\"}}")
CONTROL_SET_PLAN = [
    "T03 quickselect (Lomuto partition, renamed identifiers) -> CATALOGUE VARIANT",
    "T03 Floyd-Rivest selection -> KNOWN OUTSIDE CATALOGUE",
    "T03 binary search over the value range counting elements <= mid -> KNOWN OUTSIDE CATALOGUE",
    "T03 answer lookup table failing stress -> DEGENERATE",
    "T2 D'Esopo-Pape deque shortest paths -> KNOWN OUTSIDE CATALOGUE",
    "T2 Dijkstra with a hand-written binary-heap class -> CATALOGUE VARIANT",
    "T2 exhaustive simple-path enumeration passing only tiny graphs -> DEGENERATE",
    "A3 sparse-table range-maximum solution -> KNOWN OUTSIDE CATALOGUE",
    "A3 monotonic stack with renamed identifiers -> CATALOGUE VARIANT",
    "A3 decreasing-height processing keeping leftmost/rightmost index -> KNOWN OUTSIDE CATALOGUE",
]


def stage_commit0() -> None:
    from inputs import load_task
    from prompts import frozen_prompt_record
    objs = {t: load_task(t) for t in TASKS}
    root = Path(__file__).resolve().parent
    rec = {"utc": utc_now(), "hypothesis": HYPOTHESIS, "prediction": PREDICTION, "ladder": LADDER,
           "definitions": DEFINITIONS, "tests": TESTS, "judges": JUDGES, "judge_prompt": JUDGE_PROMPT,
           "control_set_plan": CONTROL_SET_PLAN, "openrouter_cap_usd": CAP_TOTAL_USD,
           "decoding": {"temperature": 1.0, "top_p": 1.0, "top_k": None, "max_tokens": {"T2": 1536, "T03": 1024,
                                                                                       "A3": 1024},
                        "stop": ["\\n```\\n"], "model": "Qwen/Qwen3-8B@b968826d9c46dd6066d109eabc6255188de91218",
                        "base": "Qwen/Qwen3-8B-Base@49e3418fbbbca6ecbdf9608b4d22e5a407081db4", "precision": "bf16",
                        "thinking": False},
           "search": {"islands": 4, "prompts_per_island_per_round": 3, "children_per_prompt": 4, "reset_every": 500,
                      "tau": "0.1*(1-(t mod 500)/500)+0.01", "parents_per_prompt": 2},
           "code_sha256": {p: sha256_file(root / p) for p in ("src/analysis.py", "src/run.py", "src/search.py",
                                                               "src/prompts.py", "src/sandbox.py", "src/sandbox_runner.py",
                                                               "src/critic.py", "src/labels.py", "src/inputs.py")},
           "input_sha256": {"vendor_manifest": sha256_file(root / "inputs/vendor_manifest.json"),
                            **{f"task_{t}": sha256_file(root / f"inputs/tasks/{t}.json") for t in TASKS},
                            "corpus_summary": sha256_file(root / "data/corpus/summary.json"),
                            "corpus_shingles": sha256_file(root / "data/corpus/shingles.npz")}}
    write_json(PRED / "prompts_frozen.json", frozen_prompt_record(objs))
    write_json(PRED / "commit0.json", rec)
    commit([PRED / "commit0.json", PRED / "prompts_frozen.json", root / "src/analysis.py"], "commit0",
           "before any GPU sample")


def stage_commit1(gpu_hours_avail: float) -> None:
    """s*_task, seed pools, measured throughput, final N per arm from the budget ladder."""
    import numpy as np

    from common import DATA, read_jsonl
    from inputs import load_task
    from labels import combine
    rows = read_jsonl(DATA / "rows_calib.jsonl")
    tp = read_json(PRED / "throughput_pilot.json")
    sstar = {}
    eng_check = {}
    for t in TASKS:
        obj = load_task(t)
        cal = [r for r in rows if r["task"] == t and r["arm"] == "CAL" and r["correct"]]
        sims = []
        per_mode = {}
        for r in cal:
            lab, src = combine(r["runtime_label"] or "unknown", r["ast_label"] or "unknown", None)
            ok = lab == r["cal_mode"] and src in ("runtime+ast", "runtime(ast_unknown)")
            per_mode.setdefault(r["cal_mode"], [0, 0])
            per_mode[r["cal_mode"]][1] += 1
            if ok and r["nearest_known_sim"] is not None:
                sims.append(r["nearest_known_sim"])
                per_mode[r["cal_mode"]][0] += 1
        seeds = read_json(DATA / f"seeds_{t}.json") if (DATA / f"seeds_{t}.json").exists() else []
        from critic import Critic
        ref_s = [x["s"] for x in Critic().score(list(obj["references"].values()), exclude_self=True)]
        allv = sims + ref_s
        sstar[t] = {"s_star": float(np.percentile(allv, 5)), "n_forced_kept": len(sims), "n_refs": len(ref_s),
                    "per_mode_kept_of_correct": per_mode, "median_s": float(np.median(allv)),
                    "seed_ids": [x["id"] for x in seeds]}
        eng = [r for r in rows if r["task"] == t and r["arm"] == "ENG"]
        corr = [r for r in eng if r["correct"]]
        labs = [combine(r["runtime_label"] or "unknown", r["ast_label"] or "unknown", None)[0] for r in corr]
        dflt = obj["default"]
        eng_check[t] = {"n": len(eng), "pass_rate": len(corr) / max(len(eng), 1),
                        "default_share_of_correct": sum(l == dflt for l in labs) / max(len(labs), 1),
                        "labels": dict(__import__("collections").Counter(labs)), "default": dflt}
    s_rate = tp["S_shaped"]["children_per_hour"]
    b_rate = tp["B0"]["children_per_hour"]
    write_json(RESULTS / "engine_check.json", eng_check)
    # time per level (S-shaped prompts for S/NE; B0-like for I0/B0/BINT; EAP = 1.5x B0 for stage 1)
    def hours(N: dict) -> float:
        h = 0.0
        for t, arms in N.items():
            for a, n in arms.items():
                rate = s_rate if a in ("S", "NE") else b_rate
                if a == "EAP":
                    rate = b_rate / 1.5
                h += n / rate
        return h
    lv0, lv1 = LADDER["level0"], LADDER["level1"]
    h0, h1 = hours(lv0), hours(lv1)
    N = dict(lv0)
    level = 0
    if h0 + h1 <= gpu_hours_avail:
        N.update(lv1)
        level = 1
    rec = {"utc": utc_now(), "s_star": sstar, "engine_check": eng_check, "throughput": tp,
           "hours_level0": round(h0, 3), "hours_level1": round(h1, 3), "gpu_hours_available": gpu_hours_avail,
           "level": level, "N": N, "task_order": ["T03", "T2"] + (["A3"] if level >= 1 else []),
           "notes": "N per arm = calls; S/NE prompts carry 4 children each"}
    write_json(PRED / "commit1.json", rec)
    commit([PRED / "commit1.json"], "commit1", "before the first decisive sample")
    logger.info(f"commit1: level {level}, hours L0 {h0:.2f} L1 {h1:.2f} avail {gpu_hours_avail:.2f}; s* "
                f"{ {t: round(v['s_star'], 3) for t, v in sstar.items()} }; engine check {eng_check}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True)
    ap.add_argument("--gpu-hours", type=float, default=2.3)
    ap.add_argument("--deadline-min", type=float, default=170.0, help="minutes from now when the GPU run must stop")
    ap.add_argument("--n-l", type=int, default=500)
    ap.add_argument("--tasks", type=str, default="", help="comma list of tasks for --stage adjudicate")
    ap.add_argument("--plan", type=str, default="predictions/commit1.json", help="committed plan (N per arm) to run")
    args = ap.parse_args()
    setup_logging(f"method_{args.stage}")
    if args.stage not in ("calib", "base", "run"):
        set_ram_limit(48.0)   # CPU stages only: RLIMIT_AS breaks CUDA's virtual reservations
    t0 = time.time()
    if args.stage == "inputs":
        from inputs import build_task, vendor_all
        vendor_all()
        for t in TASKS:
            build_task(t, force=True)
    elif args.stage == "corpus":
        from critic import build_corpus
        from inputs import load_task
        build_corpus({t: load_task(t) for t in TASKS}, force=True)
    elif args.stage == "tests":
        import subprocess
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests"], cwd=str(Path(__file__).parent))
        sys.exit(r.returncode)
    elif args.stage == "commit0":
        stage_commit0()
    elif args.stage == "calib":
        from run import stage_calib
        stage_calib()
    elif args.stage == "commit1":
        stage_commit1(args.gpu_hours)
    elif args.stage == "base":
        from run import stage_base
        plan = read_json(PRED / "commit1.json")
        amend = read_json(PRED / "amendment1.json") if (PRED / "amendment1.json").exists() else {}
        want = amend.get("bint_intents_generated", {})
        stage_base({t: max(plan["N"][t].get("BINT", 0), int(want.get(t, 0))) for t in plan["N"]})
    elif args.stage == "run":
        from run import stage_run
        plan = read_json(Path(__file__).resolve().parent / args.plan)
        stage_run(plan, deadline_epoch=time.time() + 60 * args.deadline_min)
    elif args.stage == "L":
        from arm_l import stage_l
        stage_l(args.n_l)
    elif args.stage == "label":
        from finalize import stage_label
        stage_label()
    elif args.stage == "adjudicate":
        from adjudicate import stage_adjudicate
        stage_adjudicate([t for t in args.tasks.split(",") if t] or None)
    elif args.stage == "classes":
        from adjudicate import finalize_classes
        finalize_classes()
    elif args.stage == "analyse":
        from finalize import stage_analyse
        stage_analyse()
    elif args.stage == "outputs":
        from finalize import stage_outputs
        stage_outputs()
    else:
        raise SystemExit(f"unknown stage {args.stage}")
    logger.info(f"stage {args.stage} done in {time.time() - t0:.0f}s")
    write_json(RESULTS / f"stage_{args.stage}_done.json", {"utc": utc_now(), "seconds": round(time.time() - t0, 1)})
    _ = json


if __name__ == "__main__":
    main()
