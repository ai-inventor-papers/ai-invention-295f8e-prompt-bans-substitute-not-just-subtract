#!/usr/bin/env python3
"""Coding-task bench with a baseline pilot (iteration 2, GEN_ART experiment).

Subcommands (run in this order; GPU jobs are separate processes, one model at a time):
  extract   pull the dependency rows the bench needs into data/extract/
  specs     freeze spec v1 (descriptions, catalogues, display names, templates) + commitment
  gen       GPU job A (pilot, association, forced round 1), C (top-ups) or D (Llama pilot)
  build     hidden tests, checkers, references and limits for every task (CPU)
  label     label pilot + forced attempts (tests, AST, runtime tracer, judge on disagreement)
  order     association map, nominations and the Stage-A / Stage-B orders (committed)
  gate      per-task gold set, adjudication and labeller gate in Stage-A order
  score     GPU job B: vLLM prompt-logprob scoring of forced programs (+ consistency checks)
  frlp      baseline forced-ratio latent probability cells
  freeze    commitments of every gated task
  report    pilot statistics, method_out.json, audits
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from loguru import logger

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

(ROOT / "logs").mkdir(exist_ok=True)
logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")


def _file_sink(name: str) -> None:
    logger.add(ROOT / "logs" / f"{name}.log", rotation="30 MB", level="DEBUG")


def cmd_specs(args: argparse.Namespace) -> None:
    from bench.common.catalogue import (ASSOCIATION_TEMPLATE, DESCRIPTIVE_FORCED_TEMPLATE, FORCED_TEMPLATES,
                                        FORMAT_LINE, TASK_ORDER, TASKS)
    from bench.common.commit import canon_json, commit, sha256_text
    from bench.common.prompts import spec_text
    frozen = {}
    for t in TASK_ORDER:
        c = TASKS[t]
        d = ROOT / "bench" / c["task_id"]
        d.mkdir(parents=True, exist_ok=True)
        spec = {"task": t, "task_id": c["task_id"], "leetcode_ids": c["leetcode_ids"], "signature": c["signature"],
                "description": c["description"], "format_line": FORMAT_LINE, "spec_text": spec_text(t),
                "bounds": c["bounds"],
                "catalogue": [{"mode": m, "display_name": v[0], "mechanism": v[1]} for m, v in c["modes"].items()],
                "aliases": c["aliases"], "forced_templates": FORCED_TEMPLATES,
                "descriptive_forced_template": DESCRIPTIVE_FORCED_TEMPLATE,
                "association_template": ASSOCIATION_TEMPLATE, "spec_version": 1}
        (d / "spec.json").write_text(json.dumps(spec, indent=1))
        frozen[t] = spec
    h = sha256_text(canon_json(frozen))
    rec = commit(ROOT / "commitments.log", "spec_v1", h, {"n_tasks": len(frozen)})
    logger.info(f"spec v1 frozen for {len(frozen)} tasks: {rec}")


def cmd_gen(args: argparse.Namespace) -> None:
    _file_sink(f"gen_job_{args.job}")
    from bench.common import gen_vllm
    gen_vllm.set_cache_env(ROOT)
    if args.job == "A":
        paraphrases = [int(x) for x in args.paraphrases.split(",")]
        gen_vllm.job_a(ROOT, args.model, args.max_num_seqs, args.gpu_util, args.n_pilot, args.n_assoc,
                       args.forced_rounds, paraphrases)
    elif args.job == "C":
        gen_vllm.job_c(ROOT, args.model, args.max_num_seqs, args.gpu_util, Path(args.plan))
    elif args.job == "D":
        gen_vllm.job_d(ROOT, args.model, args.max_num_seqs, args.gpu_util, args.tasks.split(","), args.n_pilot)


def cmd_extract(args: argparse.Namespace) -> None:
    _file_sink("extract")
    from bench.common.build import extract
    extract(ROOT)


def cmd_build(args: argparse.Namespace) -> None:
    _file_sink("build")
    from bench.common.build import build_task, exp_bruteforce_check, smoke_humanevalplus
    from bench.common.catalogue import TASK_ORDER
    tasks = args.tasks.split(",") if args.tasks else TASK_ORDER
    reps = {t: build_task(ROOT, t, workers=args.workers) for t in tasks}
    smoke = smoke_humanevalplus(ROOT)
    brute = exp_bruteforce_check(ROOT) if ("T11" in tasks and "T08" in tasks) else None
    out = ROOT / "results" / "build_summary.json"
    prev = json.loads(out.read_text()) if out.exists() else {"tasks": {}}
    prev["tasks"].update(reps)
    prev["humanevalplus_smoke"] = smoke
    if brute is not None:
        prev["exponential_bruteforce_check"] = brute
    out.write_text(json.dumps(prev, indent=1))
    logger.info(f"humanevalplus smoke: {smoke}; exponential brute force: {brute}")


def cmd_score(args: argparse.Namespace) -> None:
    _file_sink("score_job_B")
    from bench.common import gen_vllm, score_vllm
    gen_vllm.set_cache_env(ROOT)
    score_vllm.job_b(ROOT, args.model, args.gpu_util, [int(x) for x in args.paraphrases.split(",")], args.only_checks)


def cmd_label(args: argparse.Namespace) -> None:
    """tests + AST + runtime trace + scrub check -> stored traces -> runtime rules -> judge on disagreement."""
    _file_sink("label")
    from bench.common.combine import combine, load_raw_samples, write_shared_rows
    from bench.common.labeling import label_all
    from bench.common.retrace import apply_runtime_rules, retrace_all
    sources = args.sources.split(",")
    if args.retest:  # re-run extended hidden tests for already-labelled attempts (used for T14), then re-combine
        from bench.common.labeling import retest
        logger.info(f"retest: {retest(ROOT, args.retest.split(','), sources, args.out, workers=args.workers)}")
        args.combine_only = True
    llama = args.llama
    out = "labels_llama_raw.jsonl" if llama else args.out
    traces = "traces_llama.jsonl" if llama else "traces.jsonl"
    if not args.combine_only:
        label_all(ROOT, sources, out, workers=args.workers)
        retrace_all(ROOT, sources, out, out=traces, workers=args.workers)
    logger.info(f"runtime rules re-applied: {apply_runtime_rules(ROOT, out, traces)}")
    combined = combine(ROOT, sources, out, "labels_llama_combined.jsonl" if llama else "labels_combined.jsonl")
    write_shared_rows(ROOT, combined, load_raw_samples(ROOT, sources),
                      {"baseline": "samples_llama_pilot.jsonl"} if llama else None)
    logger.info(f"combined labels written for {len(combined)} attempts")


def cmd_order(args: argparse.Namespace) -> None:
    _file_sink("order")
    from bench.common.commit import canon_json, commit, sha256_text
    from bench.common.order import map_association, nominations
    if args.stage == "A":
        if not (ROOT / "data" / "association.jsonl").exists():
            map_association(ROOT)
        res = nominations(ROOT, "A")
    else:
        cells = {}
        p = ROOT / "data" / "frlp_cells.jsonl"
        if p.exists():
            for l in p.open():
                r = json.loads(l)
                if r.get("half") == "all" and r.get("variant") == "main":
                    cells[(r["task"], r["algorithm"])] = r
        res = nominations(ROOT, "B", cells)
    out = ROOT / "results" / f"stage{args.stage}_nominations.json"
    out.write_text(json.dumps(res, indent=1, default=str))
    h = sha256_text(canon_json(json.loads(out.read_text())))
    rec = commit(ROOT / "commitments.log", f"stage{args.stage}_order", h, {"order": res["order"]})
    logger.info(f"Stage-{args.stage} order {res['order']} committed: {rec['sha256'][:16]}")


def cmd_gate(args: argparse.Namespace) -> None:
    _file_sink("gate")
    import time
    from bench.common.gate import run_gate
    order = json.loads((ROOT / "results" / "stageA_nominations.json").read_text())["order"]
    if args.tasks:
        order = [t for t in order if t in args.tasks.split(",")]
    deadline = time.time() + args.minutes * 60 if args.minutes else None
    if args.revise:
        from bench.common.gate import revise
        summ = revise(ROOT, args.tasks.split(","), args.revise)
    else:
        summ = run_gate(ROOT, order, deadline)
    out = ROOT / "results" / "gate_summary.json"
    prev = json.loads(out.read_text()) if out.exists() else {}
    prev.update(summ)
    out.write_text(json.dumps(prev, indent=1))


def cmd_frlp(args: argparse.Namespace) -> None:
    _file_sink("frlp")
    from bench.common.catalogue import TASK_ORDER, TASKS
    from bench.common.frlp import compute
    from bench.common.gate import frlp_sets
    forced = [json.loads(l) for l in (ROOT / "data" / "samples_forced.jsonl").open()]
    for t in TASK_ORDER:  # final frozen FRLP sets (after top-ups)
        (ROOT / "bench" / TASKS[t]["task_id"] / "frlp_sets.json").write_text(json.dumps(frlp_sets(t, forced), indent=1))
    compute(ROOT)


def cmd_freeze(args: argparse.Namespace) -> None:
    _file_sink("freeze")
    from bench.common.report import freeze
    gate = json.loads((ROOT / "results" / "gate_summary.json").read_text())
    order = json.loads((ROOT / "results" / "stageA_nominations.json").read_text())["order"]
    gated = [t for t in order if gate.get(t, {}).get("status") == "gated"][: args.max_tasks]
    if len(gated) < 6:
        raise RuntimeError(f"only {len(gated)} gated tasks; minimum is 6")
    doc = freeze(ROOT, gated)
    (ROOT / "results" / "frozen_tasks.json").write_text(json.dumps({"frozen": gated, "order": order}, indent=1))
    logger.info(f"frozen {len(gated)} tasks {gated}: {doc['combined_sha256'][:16]}")


def cmd_report(args: argparse.Namespace) -> None:
    _file_sink("report")
    from bench.common.finalize import finalize
    finalize(ROOT)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("specs")
    g = sub.add_parser("gen")
    g.add_argument("--job", choices=["A", "C", "D"], required=True)
    g.add_argument("--model", default="Qwen/Qwen3-8B-FP8")
    g.add_argument("--max-num-seqs", type=int, default=48)
    g.add_argument("--gpu-util", type=float, default=0.90)
    g.add_argument("--n-pilot", type=int, default=50)
    g.add_argument("--n-assoc", type=int, default=20)
    g.add_argument("--forced-rounds", type=int, default=8)
    g.add_argument("--paraphrases", default="0,1,2,3,4")
    g.add_argument("--plan", default=str(ROOT / "data" / "topup_plan.json"))
    g.add_argument("--tasks", default="")
    sc = sub.add_parser("score")
    sc.add_argument("--model", default="Qwen/Qwen3-8B-FP8")
    sc.add_argument("--gpu-util", type=float, default=0.85)
    sc.add_argument("--paraphrases", default="0,1,2,3,4")
    sc.add_argument("--only-checks", action="store_true")
    lb = sub.add_parser("label")
    lb.add_argument("--sources", default="samples_pilot_raw.jsonl,samples_forced_raw.jsonl")
    lb.add_argument("--out", default="labels_raw.jsonl")
    lb.add_argument("--workers", type=int, default=5)
    lb.add_argument("--combine-only", action="store_true")
    lb.add_argument("--llama", action="store_true", help="label the optional Llama pilot into separate files")
    lb.add_argument("--retest", default="", help="comma-separated tasks whose attempts are re-tested, then re-combined")
    od = sub.add_parser("order")
    od.add_argument("--stage", choices=["A", "B"], default="A")
    gt = sub.add_parser("gate")
    gt.add_argument("--tasks", default="")
    gt.add_argument("--minutes", type=float, default=0)
    gt.add_argument("--revise", type=int, default=0)
    sub.add_parser("frlp")
    fz = sub.add_parser("freeze")
    fz.add_argument("--max-tasks", type=int, default=12)
    sub.add_parser("report")
    sub.add_parser("extract")
    b = sub.add_parser("build")
    b.add_argument("--tasks", default="")
    b.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()
    fn = {"specs": cmd_specs, "gen": cmd_gen, "extract": cmd_extract, "build": cmd_build, "score": cmd_score,
          "label": cmd_label, "order": cmd_order, "gate": cmd_gate, "frlp": cmd_frlp, "freeze": cmd_freeze,
          "report": cmd_report}[args.cmd]
    logger.catch(reraise=True)(fn)(args)


if __name__ == "__main__":
    main()
