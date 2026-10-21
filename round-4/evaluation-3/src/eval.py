#!/usr/bin/env python3
"""Iteration-4 Step 0: record repair and frozen push screen. Single entry point with stage flags.

    uv run eval.py --stages all            # every stage in order
    uv run eval.py --stages knob,screen    # selected stages (each reads the previous stages' outputs)

Stages: inventory rows judges knob screen route llama other figures rigor wording rivals audit outputs.
CPU only; no model text is generated; the only LLM calls are the (0d) judges (src/run_judges.py).
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

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(WS / "logs" / "eval.log", rotation="30 MB", level="DEBUG")

STAGES = ["inventory", "rows", "judges", "knob", "screen", "route", "llama", "other", "figures", "rigor", "wording", "rivals",
          "audit", "outputs"]


def _limit_memory(gb: float = 18.0) -> None:
    try:
        resource.setrlimit(resource.RLIMIT_AS, (int(gb * 1024 ** 3), int(gb * 1024 ** 3)))
    except (ValueError, OSError) as e:
        logger.warning(f"could not set RLIMIT_AS: {e}")


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stages", default="all")
    args = ap.parse_args()
    stages = STAGES if args.stages == "all" else [s.strip() for s in args.stages.split(",")]
    _limit_memory()
    import pandas as pd

    from src import stages as S
    for st in stages:
        t0 = time.time()
        logger.info(f"=== stage {st} ===")
        getattr(S, f"stage_{st}")()
        logger.info(f"=== stage {st} done in {time.time() - t0:.1f}s ===")
    del pd


if __name__ == "__main__":
    main()
