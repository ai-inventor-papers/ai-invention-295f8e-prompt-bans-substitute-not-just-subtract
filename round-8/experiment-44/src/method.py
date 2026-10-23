#!/usr/bin/env python3
"""Top-five ban: who obeys, where survivors land (iteration 8, gen_plan_experiment_6_idx7).

Orchestrator: one sub-command per stage, run in order (see README.md):
  stage0 | smoke | commit1 | screen_base | commit2 | screen_ban | adjudicate | select | states | geometry |
  m2 | quantcheck | confirm | novelty | positioning | figures | rederive | outputs
`uv run method.py <stage>`; with no stage it rebuilds method_out.json from saved results.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from loguru import logger  # noqa: E402

from common import setup_logging  # noqa: E402


@logger.catch(reraise=True)
def main() -> None:
    stage = sys.argv[1] if len(sys.argv) > 1 else "outputs"
    args = sys.argv[2:]
    setup_logging(f"method_{stage}")
    logger.info(f"=== stage {stage} {args}")
    import stages

    fn = getattr(stages, f"stage_{stage}", None)
    if fn is None:
        raise SystemExit(f"unknown stage {stage}")
    fn(*args)


if __name__ == "__main__":
    main()
