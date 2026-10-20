#!/usr/bin/env python3
"""Banning five path algorithms at once (Qwen3-8B, thinking off): orchestrator with one sub-command per stage.

Stages (see README.md for the full ordered run):
  freeze        S1  freeze every prompt known before sampling (commitments.log line 0)
  recheck       S0  re-check the canonical (iteration-1) labeller on its gold set and 22 references
  serve/stop        start / stop the PID-managed vLLM server of a sampling session
  smoke         S2a forced smoke (1 per paraphrase) -> labelled -> descriptive-variant decisions
  s1main        S2b baseline, single modal bans, T2 leave-one-survivor (LOS)
  forced_rest   S2c the remaining forced programs (3 per paraphrase; 4 under a descriptive variant)
  refs/validate S3  extended labeller: references, unit probes, 40-program gold set
  label         S3  label every program of a raw file with the extended labeller
  keep          S4  keep rule, program sets, scrubbing
  score1a       S5  HF stage 1a: baseline, denominators, forced/base/own states
  select        S6  set selection (TOP-5, ARC-5, SCATTER-5) from the consensus geodesic matrix
  score1b       S7  FRLP cells of the planned conditions (ban / mention / neutral, nonce, LOS, tier 3)
  commit        S7  forecasts + analysis-script hash committed (hash chain) before session 2
  session2      S8  TOP-5, ARC-5, SCATTER-5 sampling (W1-W5 x 20)
  score2        S9  HF stage 2: state passes of session-2 programs
  analyse       S10-S11 behaviour, landing tests, LOS, manifold, internals, persistence
  outputs       S12 method_out.json (+ mini / preview), samples.jsonl
"""

from __future__ import annotations

import argparse
import sys
import time

from loguru import logger

from common import DATA_DIR, setup_logging


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stage", nargs="?", default="outputs",
                    help="stage to run (default: outputs, which rebuilds method_out.json from the saved results)")
    ap.add_argument("--src", default=None)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--session", default="s1")
    ap.add_argument("--no-judge", action="store_true")
    args = ap.parse_args()
    setup_logging(args.stage)
    t0 = time.time()
    st = args.stage
    if st == "freeze":
        from mb.prompts import stage_freeze

        stage_freeze()
    elif st == "serve":
        import asyncio

        from mb.gen import start_server, wait_for_server

        start_server(args.session)
        asyncio.run(wait_for_server())
    elif st == "stop":
        from mb.gen import stop_server

        stop_server()
    elif st == "smoke":
        from mb.gen import forced_requests, gen_stats, staged_run
        from mb.prompts import load_frozen

        staged_run(forced_requests(load_frozen(), "smoke", 1), DATA_DIR / "raw_smoke.jsonl", stages=(10, 100))
        logger.info(f"smoke stats: {gen_stats(DATA_DIR / 'raw_smoke.jsonl')}")
    elif st == "s1main":
        from mb.gen import gen_stats, session1_main_requests, staged_run
        from mb.prompts import load_frozen

        staged_run(session1_main_requests(load_frozen()), DATA_DIR / "raw_session1.jsonl", stages=(10, 100))
        logger.info(f"session-1 main stats: {gen_stats(DATA_DIR / 'raw_session1.jsonl')}")
    elif st == "forced_rest":
        from mb.stages import stage_forced_rest

        stage_forced_rest()
    elif st == "recheck":
        from mb.label import stage_recheck

        stage_recheck()
    elif st == "refs":
        from mb.label import stage_refs

        stage_refs()
    elif st == "label":
        from mb.label import stage_label

        stage_label(args.src, use_judge=not args.no_judge)
    elif st == "smoke_decide":
        from mb.stages import stage_smoke_decide

        stage_smoke_decide()
    elif st == "validate":
        from mb.label import stage_validate

        stage_validate()
    elif st == "keep":
        from mb.stages import stage_keep

        stage_keep()
    elif st == "psets":
        from mb.stages import stage_psets

        stage_psets()
    elif st in ("score1a", "score1b", "score2"):
        from mb.score import run_score_stage

        run_score_stage(st, limit=args.limit)
    elif st == "select":
        from mb.sets import stage_select

        stage_select()
    elif st == "commit":
        from mb.forecasts import stage_commit

        stage_commit()
    elif st == "session2":
        from mb.stages import stage_session2

        stage_session2()
    elif st == "analyse":
        from analysis.extra import run_extra
        from analysis.landing import run_landing
        from analysis.manifold import run_manifold

        run_landing()
        run_manifold()
        run_extra()
    elif st == "extra":
        from analysis.extra import run_extra

        run_extra()
    elif st == "landing":
        from analysis.landing import run_landing

        run_landing()
    elif st == "manifold":
        from analysis.manifold import run_manifold

        run_manifold()
    elif st == "aux":
        from mb.aux_datasets import stage_aux

        stage_aux()
    elif st == "outputs":
        from mb.outputs import stage_outputs

        stage_outputs()
    else:
        logger.error(f"unknown stage {st}")
        sys.exit(2)
    logger.info(f"stage {st} done in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
