#!/usr/bin/env python3
"""Temperature and seeds: new ideas or rewording? -- screen on Qwen3-8B over two path-search tasks.

Orchestrates every stage of the artifact (each GPU stage in its own process; vLLM and HF never share the GPU):
  setup     hidden tests, time limits, reference gate + negative controls, prompt scaffold assertions, metric checks
  smoke     GPU smoke test (16 A0 samples per task, thinking two-pass incl. a forced 64-token truncation)
  generate  vLLM arms A0, A1, A2, A6a, A3, A5, A4 (gen-then-select), A6b-d  -> results/raw/<arm>.jsonl
  label     hidden tests + runtime tracer + AST rules (+ blind judge on disagreements) -> results/samples.jsonl
  gate      gold set (two judges + adjudicator) and labeller gate -> results/labeller_gate.json
  hooks     HF activation block (R states, probes, l*, trajectory states) -> states/, results/probe_curves.json
  analyze   8a-8i analyses, verdicts, forecast check, figures -> results/analysis.json, figures/
  output    method_out.json (exp_gen_sol_out schema) with every per-sample prediction and all results
  all       everything above in order (the hash-committed forecast must already exist; it is never rewritten)

The baseline is the no-cue A0 arm (and the same baseline preambles across the temperature grid); every cue
(seeds, instructions, gen-then-select) is compared with it at matched decoding.
Usage: .venv/bin/python method.py <stage> [--deadline HH:MM]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

WS = Path(__file__).resolve().parent
sys.path.insert(0, str(WS))
from common import (CATALOGUE, LOGS, RAW, RESULTS, TASK_TEXT, TESTS_DIR, read_jsonl, setup_logging,  # noqa: E402
                    sha256_file, write_json)

PY = sys.executable
logger = setup_logging("method")

MODULES = ["common.py", "tasks/t1_grid.py", "tasks/t2_sssp.py", "harness/run_tests.py", "harness/_driver.py",
           "labeller/_trace_driver.py", "labeller/tracer.py", "labeller/ast_rules.py", "labeller/judge.py",
           "labeller/label.py", "labeller/gold.py", "prompts/build.py", "gen/arms.py", "hooks/states.py",
           "analysis/metrics.py", "analysis/behaviour.py", "analysis/phrasing.py", "analysis/subspace.py",
           "analysis/thinking.py", "analysis/verdicts.py", "analysis/figures.py", "analysis/run_all.py",
           "analysis/test_metrics.py", "labeller/test_rewrite.py", "verify_headlines.py", "method.py"]

DEVIATIONS = [
    dict(what="GPU was an RTX 5090 (32 GB) instead of a 20 GB card: max_num_seqs=128 (plan 16) and thinking-on "
              "cells have N=100 (10 paraphrases x 10) instead of N=50; all four thinking-on cells per task ran",
         why="more KV-cache capacity (92k tokens) and ~4k tok/s throughput", effect="more power for thinking-on "
         "cells; no planned arm was dropped"),
    dict(what="vLLM 0.11.0 started with enforce_eager=True (no CUDA graphs / torch.compile)",
         why="the container has no C compiler, so Triton/Inductor compilation cannot run", effect="speed only"),
    dict(what="HF_HOME was not set to ./hf_cache; Qwen/Qwen3-8B was read from the run's shared HF cache",
         why="the run's shared cache variables must not be overridden", effect="none on outputs"),
    dict(what="per-request seed = stable hash of (task, condition, paraphrase, sample, arm, T, sampler, thinking) "
              "instead of (task, condition, paraphrase, sample)",
         why="so that different decoding cells are independent draws rather than common-random-number pairs",
         effect="cells are independent samples, matching the per-cell bootstrap"),
    dict(what="forced:X uses 20 frames = 10 neutral preambles x 2 templates; described:X uses 2 name-free "
              "descriptions x 5 preambles per mode", why="the plan fixes counts but not the frame construction",
         effect="none"),
    dict(what="A4 stage 1 has no paraphrase preambles (paraphrase_id=-1); its bootstrap treats each sample as a cluster",
         why="the plan's stage-1 prompt has no preamble", effect="none"),
    dict(what="tracer uses sys.settrace for both call/return (recursion depth, call expansions) and line events",
         why="one trace function covers both; sys.setprofile would duplicate the call bookkeeping", effect="none"),
    dict(what="IDDFS reference written in the common recursive form (best-depth map per iteration) plus an "
              "iterative-stack variant; serpentine T1 test fixed (its goal cell was a wall)",
         why="first version did not match model-written IDDFS and the test case violated the spec",
         effect="labeller validated on both IDDFS forms; hidden tests regenerated before any scoring"),
    dict(what="tracer crafted graphs W1/W2 made strongly connected (Hamiltonian cycle) with a FIFO re-relaxation "
              "gadget next to s; Floyd-Warshall rule also accepts growth >= 2.2 with >= n^3/2 line events",
         why="on the planned generator SPFA never re-popped a node and an INF-skipping Floyd-Warshall grew as n^1.4",
         effect="100% runtime labels on references (pre-gate change, logged)"),
    dict(what="two rounds of labeller signature revision after the first gate (see labeller_gate.revisions)",
         why="gate failures traced to stale-pop handling, Bellman-Ford over adjacency lists, and sequential double "
             "Dijkstra mislabelled bidirectional", effect="samples needing the judge fell from 247 to 116 (of 5,220)"),
    dict(what="labeller gate failed on both tasks by the strict criterion and both tasks carry the flag "
              "'labeller_gate_failed'; their results are descriptive",
         why="kappa(runtime, AST) on the gold set is low by construction (the gold set oversamples disagreements; "
             "population kappa is 0.88 / 0.85); T2 gold agreement 70% because the gold judges call broken "
             "attempts 'other' while the pipeline labels the attempted structure",
         effect="verdicts are reported mechanically but marked descriptive; agreement on correct gold programs is "
                "92% on both tasks"),
    dict(what="probe nulls: 200 shuffled-label permutations for transfer accuracy in layers 8-28 (50 elsewhere); "
              "leave-one-frame-out null uses 20 permutations",
         why="time budget", effect="l* selection uses the planned 200-permutation transfer null"),
    dict(what="S_nat skipped on both tasks; variance split uses S_gen (primary) and S_R",
         why="natural samples have < 2 modes with >= 5 samples (fallback 5)", effect="as planned"),
    dict(what="variance-split data-matched null frames are drawn inside the top-50 PCs of the pooled generated-"
              "position states of the task (not the R states)",
         why="the null should match the space whose variance is being split", effect="excess-share values"),
    dict(what="max_model_len=4096 (shared protocol 2048) and max_tokens=1536 for instr_enumerate",
         why="planned deviations", effect="none on thinking-off outputs"),
]


def run(cmd: list[str], log: str) -> None:
    logger.info("$ " + " ".join(cmd).replace(str(WS) + "/", ""))
    t0 = time.time()
    with (LOGS / log).open("a") as f:
        r = subprocess.run(cmd, cwd=WS, stdout=f, stderr=subprocess.STDOUT)
    logger.info(f"exit {r.returncode} after {time.time() - t0:.0f}s (log: logs/{log})")
    if r.returncode != 0:
        raise RuntimeError(f"stage failed: {' '.join(cmd)}")


def stage_setup() -> None:
    run([PY, "tasks/t1_grid.py"], "setup.log")
    run([PY, "tasks/t2_sssp.py"], "setup.log")
    run([PY, "harness/run_tests.py"], "setup.log")
    run([PY, "prompts/build.py"], "setup.log")
    run([PY, "labeller/tracer.py"], "setup.log")
    run([PY, "labeller/ast_rules.py"], "setup.log")
    run([PY, "analysis/test_metrics.py"], "setup.log")
    run([PY, "labeller/test_rewrite.py"], "setup.log")
    fc = WS / "forecast" / "predictions_screen.json"
    if not fc.exists():
        raise RuntimeError("forecast/predictions_screen.json must be written (and hashed) before sampling")
    (LOGS / "forecast_sha256.txt").write_text(sha256_file(fc) + "\n")


def build_method_out() -> dict:
    A = json.loads((RESULTS / "analysis.json").read_text())
    gate = json.loads((RESULTS / "labeller_gate.json").read_text())
    cap = json.loads((LOGS / "capacity.json").read_text())
    stats = json.loads((LOGS / "gen_stats.json").read_text())
    meta_states = json.loads((WS / "states" / "meta.json").read_text())
    import torch
    import transformers
    import vllm
    from labeller.judge import total_cost
    raw = {}
    for f in sorted(RAW.glob("A*.jsonl")):
        for r in read_jsonl(f):
            raw[r["key"]] = r
    datasets = {"T1": [], "T2": []}
    for s in read_jsonl(RESULTS / "samples.jsonl"):
        r = raw.get(s["key"], {})
        d = s["decoding"]
        ex = {
            "input": r.get("user_message", ""),
            "output": r.get("answer_text") or r.get("text") or "",
            "predict_algorithm_label": str(s["label"]),
            "predict_runtime_label": str(s.get("runtime_label")),
            "predict_ast_label": str(s.get("ast_label")),
            "predict_judge_label": str(s.get("judge_label")),
            "metadata_key": s["key"], "metadata_arm": s["arm"], "metadata_condition": s["condition"],
            "metadata_paraphrase_id": s["paraphrase_id"], "metadata_sample_id": s["sample_id"],
            "metadata_model": s.get("model"), "metadata_temperature": d["T"], "metadata_sampler": d["sampler"],
            "metadata_top_k": d["top_k"], "metadata_top_p": d["top_p"], "metadata_thinking": d["thinking"],
            "metadata_max_tokens": d["max_tokens"], "metadata_seed": d["seed"],
            "metadata_labeller_source": s["labeller_source"], "metadata_runtime_rule": s.get("runtime_rule"),
            "metadata_ast_rule": s.get("ast_rule"), "metadata_judge_rationale": s.get("judge_rationale"),
            "metadata_passed": s["passed"], "metadata_n_cases_passed": s.get("n_cases_passed"),
            "metadata_first_fail": s.get("first_fail"), "metadata_wall_s": s.get("wall_s"),
            "metadata_code_sha256": s.get("code_sha256"), "metadata_extraction_rule": s.get("extraction_rule"),
            "metadata_n_output_tokens": s.get("n_output_tokens"), "metadata_finish_reason": s.get("finish_reason"),
            "metadata_truncated_thinking": s.get("truncated_thinking"),
            "metadata_n_thinking_tokens": s.get("n_thinking_tokens"), "metadata_two_pass": s.get("two_pass"),
        }
        if s.get("gts_item"):
            ex["metadata_gts_item"] = s["gts_item"]
            ex["metadata_gts_k"] = s.get("gts_k")
            ex["metadata_gts_n_items"] = s.get("gts_n_items")
        datasets[s["task"]].append(ex)
    module_sha = {m: sha256_file(WS / m) for m in MODULES if (WS / m).exists()}
    data_sha = {p.name: sha256_file(p) for p in sorted(TESTS_DIR.glob("*_hidden.json"))}
    metadata = dict(
        method_name="Temperature and seeds: new ideas or rewording? (screen)",
        description=("Qwen3-8B, thinking off and on, on T1 (unweighted grid path search) and T2 (weighted "
                     "single-pair shortest path). Baseline = no-cue A0 arm at matched decoding; cues = temperature "
                     "x sampler grid, entropy/word/semantic seeds, four creativity instructions, gen-then-select."),
        setup=dict(model=cap.get("model"), vllm_version=vllm.__version__, transformers_version=transformers.__version__,
                   torch_version=torch.__version__, gpu=torch.cuda.get_device_name(0) if torch.cuda.is_available()
                   else None, capacity=cap, task_text=TASK_TEXT,
                   catalogue={t: {m: v[1] for m, v in c.items()} for t, c in CATALOGUE.items()},
                   hidden_tests_sha256=data_sha, hook_checks=A.get("hook_checks"),
                   l_star=meta_states.get("l_star")),
        deviations=DEVIATIONS,
        forecast_sha256=(LOGS / "forecast_sha256.txt").read_text().strip(),
        labeller_gate=gate,
        forced_label_agreement={t: gate[t]["forced_label_agreement"] for t in ("T1", "T2")},
        arms=stats,
        results=dict(bfs_dijkstra_table=A["bfs_dijkstra_table"], ideas_by_phrasings=A["ideas_by_phrasings"],
                     seeds_instructions=A["seeds_instructions"], subspace_test=A["subspace_test"],
                     variance_split=A["variance_split"], probe_curves=A["probe_curves"],
                     thinking_trajectories=A["thinking_trajectories"], gen_then_select=A["gen_then_select"],
                     buy_rows=A["buy_rows"], figures=A.get("figures")),
        verdicts=A["verdicts"], verdict_status="descriptive (labeller_gate_failed on both tasks; see labeller_gate)",
        forecast_check=A["forecast_check"], openrouter_cost_usd=total_cost(),
        module_sha256=module_sha,
    )
    return dict(metadata=metadata, datasets=[
        dict(dataset="T1_grid_path_search_qwen3_8b_generations", examples=datasets["T1"]),
        dict(dataset="T2_weighted_shortest_path_qwen3_8b_generations", examples=datasets["T2"])])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["setup", "smoke", "generate", "label", "gate", "hooks", "analyze", "output",
                                      "all"])
    ap.add_argument("--deadline", default=None)
    args = ap.parse_args()
    stages = ["setup", "generate", "label", "gate", "hooks", "analyze", "output"] if args.stage == "all" \
        else [args.stage]
    for st in stages:
        logger.info(f"=== stage {st} ===")
        if st == "setup":
            stage_setup()
        elif st == "smoke":
            run([PY, "gen/arms.py", "--smoke"], "smoke_gpu.out")
        elif st == "generate":
            cmd = [PY, "gen/arms.py", "--n-think", "10"] + (["--deadline", args.deadline] if args.deadline else [])
            run(cmd, "gen_run.out")
        elif st == "label":
            run([PY, "labeller/label.py", "--workers", "12", "--judge-cap", "1.0"], "label_run.out")
        elif st == "gate":
            run([PY, "labeller/gold.py"], "gold.log")
        elif st == "hooks":
            run([PY, "hooks/states.py"], "hooks_run.out")
        elif st == "analyze":
            run([PY, "analysis/run_all.py"], "analysis_run.out")
        elif st == "output":
            out = build_method_out()
            write_json(WS / "method_out.json", out, indent=1)
            n = sum(len(d["examples"]) for d in out["datasets"])
            logger.info(f"method_out.json written: {n} examples")


if __name__ == "__main__":
    main()
