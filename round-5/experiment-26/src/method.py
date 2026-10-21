#!/usr/bin/env python3
"""Panel B of the iteration-5 confirmation (Claims A1/A2) on Qwen3-8B (instruct) and Qwen3-8B-Base.

METHOD (ours): a ban-free, base-derived predictor of push movability. For every coding unit, the base model's
repertoire under the identical chat-templated prompt gives beta_u (share of correct base programs whose mechanism is
not the instruct twin's default) and r_u (the base model's most frequent correct non-default mechanism). Both are
hash-committed BEFORE the unit's first push sample. A1: does beta_u rank the escape fraction E_u of isotropic random
pushes (8 directions x alpha 1, 2; task-spec positions, blocks 12-23, prefill only) across units? A2: does r_u (and
the base composition) forecast where the pushes land?
BASELINES / RIVALS (same frozen material, committed beside beta): R_modal (1 - twin modal share), R_margin (opening
log-prob margin of the default over the best survivor), R_merit (runtime and length of the fastest non-default
reference vs the default's), R_novel (novelty-instruction off-default share), K_u (catalogue size) for A1; ASSOC
(association answers) and PROX (AST proximity) forecasts against BASE for A2; plus shuffled-beta, shuffled-arm and
twin-as-push placebos.

This file orchestrates the stages implemented in src/ (see README.md for the full layout):
  setup     extract dependency rows, render prompts, commit #0           (src/extract_sources.py, src/protocol0.py)
  build     unit build + gate stage (i) for B1-B7                         (src/unitbuild.py)
  gpu-i1    instruct: GPU tests, engine check, twins/novelty/association  (src/gpu_main.py)
  gpu-b1    base: chat repertoire (N = 200) + plain completion            (src/gpu_main.py)
  label     CPU label worker (runtime primary, AST second, judges on disagreement)   (src/label5.py)
  gate      gate stage (ii) (+ one revision round)                        (src/gate2.py)
  commit    per-unit predictions + hash chain                             (src/quantities.py, src/quantities_extra.py)
  push      escape population, confirmations, PN, T1.3                     (src/gpu_main.py --phases push)
  extra     disguised variants + paired parents                           (src/units_extra.py, gpu phases extra_*)
  final     analysis, audits, figures and outputs (CPU only; this is what `uv run method.py` runs by default)
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from loguru import logger

ROOT = Path(__file__).resolve().parent
PY = sys.executable
UNITS = "B1,B2,B3,B4,B5,B6,B7"
PAIRS = "T03,T10,T05,T06,T04,T08,T14,R1"

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
(ROOT / "logs").mkdir(exist_ok=True)
logger.add(str(ROOT / "logs" / "method.log"), rotation="30 MB", level="DEBUG")


def run(args: list[str], cwd: Path | None = None) -> None:
    logger.info(f"$ {' '.join(args)}")
    r = subprocess.run([PY] + args, cwd=str(cwd or ROOT))
    if r.returncode != 0:
        raise RuntimeError(f"stage failed ({r.returncode}): {' '.join(args)}")


STAGES = {
    "setup": [["src/extract_sources.py"], ["src/protocol0.py"]],
    "build": [["src/unitbuild.py", UNITS]],
    "gpu-i1": [["src/gpu_main.py", "--model", "instruct", "--phases", "tests,engine,inst1,margins", "--units", UNITS]],
    "gpu-b1": [["src/gpu_main.py", "--model", "base", "--phases", "base1", "--units", UNITS, "--n-base", "40"]],
    "label": [["src/label5.py", "--once"]],
    "gate": [["src/gate2.py", UNITS]],
    "commit": [["src/quantities.py", UNITS]],
    "push": [["src/gpu_main.py", "--model", "instruct", "--phases", "push", "--units", UNITS]],
    "extra": [["src/units_extra.py"],
              ["src/gpu_main.py", "--model", "instruct", "--phases", "extra_inst", "--pairs", PAIRS],
              ["src/gpu_main.py", "--model", "base", "--phases", "extra_base", "--pairs", PAIRS],
              ["src/quantities_extra.py", ",".join(f"{p}{t}" for t in PAIRS.split(",") for p in ("P_", "V_"))],
              ["src/gpu_main.py", "--model", "instruct", "--phases", "push", "--arms", "esc,conf", "--units",
               ",".join(f"{p}{t}" for t in PAIRS.split(",") for p in ("P_", "V_"))]],
    "final": [["src/adjudicate_all.py"], ["src/engine_check.py"], ["analysis/a1a2.py"], ["analysis/variants.py"], ["analysis/a1_extended.py"],
              ["analysis/screen_view.py"], ["src/novelty_audit.py"], ["audit/rederive.py"], ["audit/commit_order.py"], ["tests/test_analysis.py"],
              ["tests/test_cpu.py"], ["tests/test_datasets.py"], ["src/vendor_check.py"], ["src/figures.py"], ["src/outputs.py"]],
}


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--stage", default="final", help="comma-separated stages, or 'all'; see the module docstring")
    a = ap.parse_args()
    order = list(STAGES) if a.stage == "all" else a.stage.split(",")
    for s in order:
        if s not in STAGES:
            raise ValueError(f"unknown stage {s}; choose from {list(STAGES)}")
        logger.info(f"=== stage {s}")
        for cmd in STAGES[s]:
            run(cmd)
    logger.info("done")


if __name__ == "__main__":
    main()
