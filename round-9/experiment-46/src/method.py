#!/usr/bin/env python3
"""TP-G (iteration 9): Qwen3-32B's ten-algorithm grid manifold with and without the algorithms' names.

Orchestrator: one sub-command per stage (`.venv/bin/python method.py <stage> [args]`). Stages, in run order:
  inputs        Stage -1  copy prior-artifact inputs into inputs/ (+ SHA256SUMS), hardware record
  commit0       Stage 0   predictions, gates and definitions, hash-committed before any state
  mname [tag]   Stage 1   M-name states (iteration 8's 300 forced prompts) + reproduction gate (GPU)
  cpu           Stage 2   probe grids, expansion tracer, behavioural RDM, lexical measures, descriptions,
                          M-lex prompts and twins, M-code contexts; then COMMIT #1a
  naming        Stage 3a  OpenRouter naming gate (Qwen3-32B names each description 20 times)
  topups        Stage 3b  OpenRouter forced top-ups (Qwen3-32B programs)
  pools         Stage 4   ACCEPT, scrub (G-scrub), program sets, placement sets; then COMMIT #1b
  states [tag]  Stage 5   M-desc, M-lex, ban and M-code states (GPU)
  blocks        Stage 6   label-only block selection; then COMMIT #2
  analyse       Stages 7-10  geometry, verdicts, landing, bootstrap, robustness, lexical regression, RSA, placement
  figures       Stage 11
  outputs       Stage 12  points/placements rows, n4_verdict.json, method_out.json
"""

from __future__ import annotations

import os
import resource
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(1, str(ROOT / "vendor" / "exp9"))

from loguru import logger  # noqa: E402

from common import setup_logging  # noqa: E402

GPU_STAGES = {"mname", "states", "smoke_gpu"}


def _limits(stage: str) -> None:
    if stage in GPU_STAGES:
        import torch

        if torch.cuda.is_available():
            torch.cuda.set_per_process_memory_fraction(0.90, 0)
        return
    ram = int(float(os.environ.get("TPG_RAM_GB", "40")) * 1024 ** 3)
    resource.setrlimit(resource.RLIMIT_AS, (ram, ram))


@logger.catch(reraise=True)
def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    stage, args = sys.argv[1], sys.argv[2:]
    setup_logging(f"stage_{stage}")
    _limits(stage)
    logger.info(f"=== stage {stage} {args} ===")
    if stage == "inputs":
        import stage_setup
        stage_setup.stage_inputs()
    elif stage == "hardware":
        import stage_setup
        stage_setup.stage_hardware()
    elif stage == "commit0":
        import stage_setup
        stage_setup.stage_commit0()
    elif stage == "mname":
        import stage_states
        stage_states.stage_mname(args[0] if args else "32b", int(args[1]) if len(args) > 1 else 0)
    elif stage == "repro":
        import stage_states
        stage_states.repro_check(args[0] if args else "32b")
    elif stage == "cpu":
        import stage_cpu
        stage_cpu.stage_cpu(*args)
    elif stage == "naming":
        import stage_or
        stage_or.stage_naming(*args)
    elif stage == "topups":
        import stage_or
        stage_or.stage_topups(*args)
    elif stage == "pools":
        import stage_pools
        stage_pools.stage_pools(*args)
    elif stage == "states":
        import stage_states
        stage_states.stage_states(*args)
    elif stage == "blocks":
        import stage_analysis
        stage_analysis.stage_blocks(*args)
    elif stage == "analyse":
        import stage_analysis
        stage_analysis.stage_analyse(*args)
    elif stage == "figures":
        import stage_figures
        stage_figures.stage_figures(*args)
    elif stage == "outputs":
        import stage_outputs
        stage_outputs.stage_outputs(*args)
    else:
        raise SystemExit(f"unknown stage {stage}")
    logger.info(f"=== stage {stage} done ===")


if __name__ == "__main__":
    main()
