#!/usr/bin/env python3
"""Same seed: temperature vs plan nudges (iteration 4, C1-seed) -- orchestrator.

A seed-coupled 2x2 on Qwen3-8B (thinking off, FP8 W8A8 HF engine on the 16 GB RTX 2000 Ada, the screen's card) for
T2 (weighted shortest path), T1 (grid path) and T03 (k-th smallest): every token seed keeps one noise stream across
temperature conditions (NO-PN block) and across plan-noise draws (PN block: 6 isotropic directions added at the
task-spec states of blocks 12-23, prefill only, alpha 1/2 ban units). Thinking-on T2 runs in vLLM 0.11 (Gumbel-max /
exponential-race coupling with per-request seeds). See README.md.

Stages (run in this order; every stage is resumable):
  uv run method.py --stage setup         # S0: inputs, hashes, hardware, labeller re-check   (.venv_hf, CPU)
  uv run method.py --stage screen        # S1 screen file + S2 power expectation              (CPU)
  uv run method.py --stage tests         # CPU synthetic tests of the analysis code            (CPU)
  uv run method.py --stage commit        # S3 commit #0 (pre-registration hash chain)
  .venv_vllm/bin/python src/vllm_think.py all   # S5 G1: U6 smoke, FP8 cross-check, thinking-on T2 (vLLM, GPU)
  uv run method.py --stage smoke         # S4 HF GPU unit tests U1-U5, U7                      (GPU)
  uv run method.py --stage engine_check  # S6 positive control (screen rows re-run)            (GPU)
  uv run method.py --stage grid          # S7 the 2x2 (thinking off)                           (GPU)
  uv run method.py --stage optional      # S8 optional HF arms (ii) (iii) (iv)                 (GPU)
  uv run method.py --stage label         # label worker (follows data/samples_raw.jsonl)       (CPU)
  uv run method.py --stage analyse       # S9 analyses + figures                               (CPU)
  uv run method.py --stage export        # S10 method_out.json (+ mini / preview)              (CPU)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
for _p in (ROOT / "src", ROOT / "analysis", ROOT / "tests"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from loguru import logger  # noqa: E402


def setup_logging(stage: str) -> None:
    (ROOT / "logs").mkdir(exist_ok=True)
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    logger.add(str(ROOT / "logs" / f"{stage}.log"), rotation="30 MB", level="DEBUG")


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stage", required=True,
                    choices=["setup", "screen", "tests", "commit", "smoke", "engine_check", "grid", "optional", "hf_chain",
                             "label", "analyse", "export", "rederive"])
    ap.add_argument("--tasks", default="T2,T03,T1")
    ap.add_argument("--minutes", type=float, default=None, help="wall-clock guard for GPU stages")
    ap.add_argument("--arms", default="iii,iv,ii", help="optional HF arms to run, in order")
    ap.add_argument("--follow", action="store_true", help="label worker: keep following the raw file")
    args = ap.parse_args()
    setup_logging(args.stage)
    tasks = [t for t in args.tasks.split(",") if t]
    if args.stage == "setup":
        from s0_setup import run_s0
        run_s0()
    elif args.stage == "screen":
        from screen import run_screen
        run_screen()
    elif args.stage == "tests":
        from test_analysis import run_all_tests
        run_all_tests()
    elif args.stage == "commit":
        from prereg import commit0
        commit0()
    elif args.stage == "smoke":
        from grid import run_smoke
        run_smoke()
    elif args.stage == "engine_check":
        from grid import run_engine_check
        run_engine_check(minutes=args.minutes)
    elif args.stage == "grid":
        from grid import run_grid
        run_grid(tasks=tasks, minutes=args.minutes)
    elif args.stage == "optional":
        from grid import run_optional
        run_optional(arms=[a for a in args.arms.split(",") if a], minutes=args.minutes)
    elif args.stage == "hf_chain":
        from grid import run_hf_chain
        run_hf_chain(tasks=tasks, arms=[a for a in args.arms.split(",") if a], minutes=args.minutes)
    elif args.stage == "label":
        from label4 import run_labels
        run_labels(follow=args.follow, minutes=args.minutes)
    elif args.stage == "analyse":
        from report import run_analysis
        run_analysis()
    elif args.stage == "export":
        from export import run_export
        run_export()
    elif args.stage == "rederive":
        import runpy
        runpy.run_path(str(ROOT / "audit" / "rederive.py"), run_name="__main__")


if __name__ == "__main__":
    main()
