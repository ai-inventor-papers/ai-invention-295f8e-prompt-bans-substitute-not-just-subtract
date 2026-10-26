#!/usr/bin/env python3
"""TP-B, iteration 9 (gen_plan_experiment_1_idx2): do banned AI coders just rename BFS?

Orchestrator with one sub-command per stage (`uv run method.py <stage> [args]`). The stage code lives in src/:

  stage0        hardware record, read-only input copies (inputs/ + SHA256SUMS), /key, mocked-403 test, smoke calls
  commit1a      pre-registration of everything that governs the A/E cells (prompts, seeds, N, predictions, thresholds)
  sample <ids>  OpenRouter sampling of the named cells (background; staged 10 -> 100 -> full; budget-gated)
  tracer_gate   expansion-order tracer v9 on references, planted controls and gold programs (gate, <= 2 rounds)
  n5sets        D_mech / D_name matrices and the committed rotated-set rule (R1..R6)
  describe      N3-D name-free descriptions + naming check
  commit1b      pre-registration of the tracer, probes, gate, rotated sets, descriptions and the analysis code
  retrace       Stage 2: trace ~580 iteration 1-8 five-name-ban programs (+ descriptive extras)
  label <ids>   Stage 4: name-level labelling (hidden suites + 10-class labeller + judges) + tracing of new rows
  analyse       Stage 5: N1, N2, N3, N3-D, N5, scale, novelty
  figures       F1-F8
  audit         Stage 6: independent re-derivation + placebos
  outputs       method_out.json (+ full/mini/preview)
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from loguru import logger  # noqa: E402

import stages_v9  # noqa: E402
from common import setup_logging  # noqa: E402


@logger.catch(reraise=True)
def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        return
    stage = sys.argv[1]
    setup_logging(f"method_{stage}")
    fn = getattr(stages_v9, f"stage_{stage}", None)
    if fn is None:
        raise SystemExit(f"unknown stage {stage!r}; see `uv run method.py --help`")
    logger.info(f"=== stage {stage} {sys.argv[2:]} ===")
    fn(*sys.argv[2:])
    logger.info(f"=== stage {stage} done ===")


if __name__ == "__main__":
    main()
