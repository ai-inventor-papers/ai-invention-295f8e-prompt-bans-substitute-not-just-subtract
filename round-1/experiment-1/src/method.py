#!/usr/bin/env python3
"""What does a ban switch the model to? -- orchestrator.

Behavioural screen on Qwen3-8B (thinking off, vLLM) of two rival predictors of where probability mass goes
when a prompt bans an algorithm: substitution by association (the model's own ranked 'standard alternative
to X' map, Borda-aggregated; the proposed method) versus the typicality ladder (latent baseline frequency
renormalised over the survivors; the baseline/rival). Stages (run in order):

  uv run method.py prompts      # build + freeze prompts/conditions.json (hash-chained)
  uv run method.py smoke        # GPU smoke test (baseline, listall, 3 ranking prompts on T1)
  uv run method.py preban       # pre-ban GPU job (forced, baseline, baseline_empty, baseline_T13, listall, elicitation)
  uv run method.py tasks        # build hidden tests, time limits, reference + mutation acceptance
  uv run method.py label --src data/raw_preban.jsonl
  uv run method.py gate         # labeller gate (gold set adjudicated by two judge families + tie-breaker)
  uv run method.py elicit       # parse Qwen rankings (resample invalid ones up to 3x) + map free-text answers
  uv run method.py external     # external-family elicitation replication (OpenRouter)
  uv run method.py assoc        # association + baseline objects
  uv run method.py freeze       # freeze single-ban predictions (hash chain)
  uv run method.py bans         # ban arms + mention twins (N=100 / N=50)
  uv run method.py succession   # greedy cumulative-ban succession, lockstep across tasks
  uv run method.py score        # all descriptive scoring
  uv run method.py outputs      # method_out.json, samples.jsonl, condition summaries, figures
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from loguru import logger

from common import (DATA_DIR, DECODING_FREE, DECODING_MAIN, DECODING_RANK, DECODING_T13, MODES, PROMPT_DIR, TASKS,
                    commit_file, read_jsonl, request_seed, setup_logging, write_json)

RAW_PREBAN = DATA_DIR / "raw_preban.jsonl"
RAW_SMOKE = DATA_DIR / "raw_smoke.jsonl"
RAW_BANS = DATA_DIR / "raw_bans.jsonl"
RAW_SUCC = DATA_DIR / "raw_succession.jsonl"


def load_conditions() -> dict[str, Any]:
    return json.loads((PROMPT_DIR / "conditions.json").read_text())


def program_req(task: str, condition: str, pid: int, stage: str, prompt: str, n: int, temperature: float = 1.0,
                decoding: str = DECODING_MAIN, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    r = {"req_id": f"{task}|{condition}|{pid}|{stage}", "task": task, "condition": condition, "paraphrase_id": pid,
         "stage": stage, "kind": "program", "prompt": prompt, "n": n, "temperature": temperature,
         "max_tokens": 1024, "seed": request_seed(task, condition, pid, stage), "decoding": decoding}
    if extra:
        r.update(extra)
    return r


def elicitation_reqs(conds: dict[str, Any], stage: str = "preban") -> list[dict[str, Any]]:
    reqs: list[dict[str, Any]] = []
    for task in TASKS:
        tc = conds["tasks"][task]
        for m in MODES[task]:
            for it in tc["elicit_rank"][m]:
                cond = f"rank:{m}"
                reqs.append({"req_id": f"{task}|{cond}|{it['sample_id']}|{stage}", "task": task, "condition": cond,
                             "mode_X": m, "paraphrase_id": it["sample_id"], "option_order": it["option_order"],
                             "stage": stage, "kind": "rank", "prompt": it["prompt"], "n": 1, "temperature": 1.0,
                             "max_tokens": 64, "seed": request_seed(task, cond, it["sample_id"], stage),
                             "decoding": DECODING_RANK})
            cond = f"free:{m}"
            reqs.append({"req_id": f"{task}|{cond}|0|{stage}", "task": task, "condition": cond, "mode_X": m,
                         "paraphrase_id": 0, "stage": stage, "kind": "free", "prompt": tc["elicit_free"][m]["prompt"],
                         "n": tc["elicit_free"][m]["n"], "temperature": 1.0, "max_tokens": 32,
                         "seed": request_seed(task, cond, 0, stage), "decoding": DECODING_FREE})
    return reqs


def preban_requests(conds: dict[str, Any]) -> list[dict[str, Any]]:
    """Order = priority order (core first) so a staged/partial run always holds the core."""
    reqs: list[dict[str, Any]] = []
    for task in TASKS:
        tc = conds["tasks"][task]["conditions"]
        for p in tc["baseline"]:
            reqs.append(program_req(task, "baseline", p["paraphrase_id"], "preban", p["prompt"], 30))
    reqs += elicitation_reqs(conds)
    for task in TASKS:
        tc = conds["tasks"][task]["conditions"]
        for p in tc["listall"]:
            reqs.append(program_req(task, "listall", p["paraphrase_id"], "preban", p["prompt"], 10))
        for m in MODES[task]:
            for p in tc[f"forced:{m}"]:
                reqs.append(program_req(task, f"forced:{m}", p["paraphrase_id"], "preban", p["prompt"], 2))
    for task in TASKS:
        tc = conds["tasks"][task]["conditions"]
        for p in tc["baseline"]:
            reqs.append(program_req(task, "baseline_T13", p["paraphrase_id"], "preban", p["prompt"], 20,
                                    temperature=1.3, decoding=DECODING_T13))
        p = tc["baseline_empty"][0]
        reqs.append(program_req(task, "baseline_empty", 0, "preban", p["prompt"], 50))
    return reqs


def stage_prompts() -> None:
    from gen.prompts import build_conditions, conditions_path

    path = conditions_path()
    if path.exists():
        logger.warning(f"{path} already exists and is frozen; not rebuilding")
        return
    conds = build_conditions()
    write_json(path, conds, indent=1, sort_keys=True)
    commit_file(path, note="prompts frozen before any generation")


def stage_smoke() -> None:
    from gen.run_vllm import check_template, run_requests

    decoded = check_template()
    logger.info(f"chat template tail OK: {decoded[-60:]!r}")
    conds = load_conditions()
    tc = conds["tasks"]["t1"]["conditions"]
    reqs = [program_req("t1", "baseline", 0, "smoke", tc["baseline"][0]["prompt"], 10),
            program_req("t1", "listall", 0, "smoke", tc["listall"][0]["prompt"], 10)]
    er = [r for r in elicitation_reqs(conds, stage="smoke") if r["task"] == "t1" and r["kind"] == "rank"][:3]
    stats = run_requests(reqs + er, RAW_SMOKE, concurrency=8)
    rows = read_jsonl(RAW_SMOKE)
    from labeller.extract import extract_code

    progs = [r for r in rows if r["kind"] == "program"]
    n_code = sum(1 for r in progs if extract_code(r["text"])[0] is not None)
    think = sum(1 for r in rows if "<think>" in r["text"])
    logger.info(f"smoke: {len(progs)} programs, code extraction {n_code}/{len(progs)}, '<think>' in {think} outputs")
    for r in rows:
        if r["kind"] == "rank":
            logger.info(f"rank output: {r['text'][:80]!r}")
    write_json(DATA_DIR / "smoke_stats.json", {"stats": stats, "n_code": n_code, "n_programs": len(progs),
                                               "think_tags": think})
    assert think == 0, "thinking text leaked into outputs"


def stage_preban(limit: int | None) -> None:
    from gen.run_vllm import check_template, run_requests

    check_template()
    conds = load_conditions()
    reqs = preban_requests(conds)
    logger.info(f"pre-ban job: {len(reqs)} requests, "
                f"{sum(r['n'] for r in reqs if r['kind'] == 'program')} programs, "
                f"{sum(r['n'] for r in reqs if r['kind'] != 'program')} short queries")
    if limit is not None:
        reqs = reqs[:limit]
    stats = run_requests(reqs, RAW_PREBAN, concurrency=16)
    write_json(DATA_DIR / f"preban_stats_{limit or 'all'}.json", stats)


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("stage")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--src", type=str, default=None)
    ap.add_argument("--round", type=int, default=None)
    ap.add_argument("--no-judge", dest="no_judge", action="store_true")
    args = ap.parse_args()
    setup_logging(f"method_{args.stage}")
    logger.info(f"stage={args.stage} argv={sys.argv[1:]}")
    if args.stage == "prompts":
        stage_prompts()
    elif args.stage == "smoke":
        stage_smoke()
    elif args.stage == "preban":
        stage_preban(args.limit)
    else:
        from pipeline import run_stage

        run_stage(args)


if __name__ == "__main__":
    main()
