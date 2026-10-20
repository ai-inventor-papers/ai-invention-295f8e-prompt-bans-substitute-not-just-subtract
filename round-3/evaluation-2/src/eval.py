#!/usr/bin/env python3
"""Iteration-3 Step 0 evaluation: repair the iteration-2 record from data on disk and audit novel code (CPU only).

Sections (run all, or one with --section):
  inventory   S0  inputs/inventory.json, tables/label_map.csv, de-duplicated row counts
  c1          0a  C1 likelihood diagnostics (argmax vs landing, implied mass, bootstrap/replicate, AIM null, M arithmetic)
  manifold    0b  exp9 figures, implemented counts, g16 geometry with nulls and planted-loop power
  judges      0c  blind LLM judges for the novelty audit (paid; cached in audit/judge_cache.jsonl)
  novelty     0c  final classes, kappa, controls, manual pass merge, corrected multi-ban avoidance
  llama       0d  Llama correct-only compositions and Hill numbers
  knob        0e  knob table under a declared class rule (rarefied Hill-1 at depth 25)
  positioning 0f  dated positioning rows (reads results/positioning_raw.json from the web check)
  corrections 0h  corrections.json (12 record items)
  assemble        full/mini/preview eval_out.json (exp_eval_sol_out)

Usage: uv run eval.py [--section NAME] [--reuse-judge-cache] [--n-boot 2000]
"""

from __future__ import annotations

import argparse
import json
import resource
import sys
import time
from pathlib import Path

from loguru import logger

WS = Path(__file__).resolve().parent
sys.path.insert(0, str(WS))

from common.paths import LOGS, RESULTS, write_json  # noqa: E402

LOGS.mkdir(parents=True, exist_ok=True)
logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(str(LOGS / "run.log"), rotation="30 MB", level="DEBUG")

SECTIONS = ["inventory", "c1", "manifold", "judges", "novelty", "llama", "knob", "positioning", "corrections",
            "assemble"]


def _rows(include_extra: bool = False):
    from common.rows import iter_rows

    return list(iter_rows(include_exp12_extra=include_extra))


def sec_inventory(args) -> None:
    from sections import s0_inventory

    s0_inventory.run(_rows(include_extra=True))


def sec_c1(args) -> None:
    from sections import s0a_c1

    s0a_c1.run(n_boot=args.n_boot, n_sim=args.n_sim)


def sec_manifold(args) -> None:
    from sections import s0b_manifold

    s0b_manifold.run(n_perm=args.n_perm, n_null=args.n_null, n_power=args.n_power, workers=args.workers)


def sec_judges(args) -> None:
    from sections import s0c_novelty

    out = s0c_novelty.run(_rows(include_extra=True), reuse_cache=args.reuse_judge_cache, call_judges=True)
    write_json(RESULTS / "novelty_judge_run.json", {"spend": out["spend"], "commit_sha256": out["commit_sha256"],
                                                    "control_scores": out["control_scores"],
                                                    "counts_unique": out["selection"]["counts_unique"],
                                                    "counts_with_duplicates": out["selection"]["counts_with_duplicates"]})


def sec_novelty(args) -> None:
    from sections import s0c_final

    s0c_final.run(_rows(include_extra=True))


def sec_llama(args) -> None:
    from sections import s0d_llama

    s0d_llama.run()


def sec_knob(args) -> None:
    from sections import s0e_knob

    s0e_knob.run(_rows(include_extra=False))


def sec_positioning(args) -> None:
    from sections import s0f_positioning

    s0f_positioning.run()


def sec_corrections(args) -> None:
    from sections import s0h_corrections

    s0h_corrections.run()


def sec_assemble(args) -> None:
    from sections import assemble

    assemble.run()


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--section", choices=SECTIONS + ["all", "no_judges"], default="all")
    ap.add_argument("--reuse-judge-cache", action="store_true", default=True)
    ap.add_argument("--fresh-judges", action="store_true", help="ignore audit/judge_cache.jsonl (spends money)")
    ap.add_argument("--n-boot", type=int, default=2000)
    ap.add_argument("--n-sim", type=int, default=10000)
    ap.add_argument("--n-perm", type=int, default=500)
    ap.add_argument("--n-null", type=int, default=200)
    ap.add_argument("--n-power", type=int, default=200)
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()
    if args.fresh_judges:
        args.reuse_judge_cache = False
    resource.setrlimit(resource.RLIMIT_AS, (24 * 1024 ** 3, 24 * 1024 ** 3))
    todo = SECTIONS if args.section == "all" else (
        [s for s in SECTIONS if s != "judges"] if args.section == "no_judges" else [args.section])
    timings = {}
    for s in todo:
        t0 = time.time()
        logger.info(f"=== section {s} ===")
        globals()[f"sec_{s}"](args)
        timings[s] = round(time.time() - t0, 1)
        logger.info(f"=== section {s} done in {timings[s]} s ===")
    p = RESULTS / "timings.json"
    old = json.loads(p.read_text()) if p.exists() else {}
    old.update(timings)
    write_json(p, old)


if __name__ == "__main__":
    main()
