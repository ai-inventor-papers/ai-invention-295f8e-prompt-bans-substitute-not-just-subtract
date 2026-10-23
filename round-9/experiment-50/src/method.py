#!/usr/bin/env python3
"""Stage CLI for the iteration-9 BASE artifact (claims B1-B3): where instruction tuning sharpened the algorithm choice.

Every GPU stage runs in its own process (one model on the GPU at a time). Stages, in the order they were run:

  preflight   hardware record + sha256-checked copies of the read-only inputs (vendor/)      src/s0_preflight.py
  units       units.json: prompts, openings, fork class tokens (CPU, tokenizers)              src/units9.py
  tests       CPU unit tests (must pass before COMMIT #0)                                    src/tests_cpu9.py
  commit0     COMMIT #0: units, node lists, samplers, thresholds, verdict rules              src/commit9.py
  cache_qwen  B2 s1 (Qwen3-8B capture) + s2 (Qwen3-8B-Base capture, random sets, REV arm)    src/cmap9.py
  patch_qwen  B2 s3: one-token CMAP sweep, sets, random nulls, RS swaps, SPEC, W arm          src/cmap9.py
  b3          B3: exp41 reproduction, MeanCache bug, COMMIT B3, interpolated held-out rerun   src/b3_9.py
  generate    B2 generation (COMMIT #1, TWIN/FSTACK/RAND/FPD x 30 CRN slots), labels, tests   src/b2gen9.py
  b1          B1: Gemma-3-4b it/pt and Llama-3.1-8B instruct/base teacher-forced forks       src/b1_9.py
  commit0b    sha256 of analysis9.py before any verdict                                      src/commit9.py
  analyze     committed B1/B2 rules, B3 statistics, summaries                                src/{b1_9,b3_9,analysis9}.py
  figures     F1-F8 (PDF + PNG)                                                              src/figures9.py
  positioning dated literature verdicts                                                      src/positioning9.py
  rederive    stdlib re-derivation of every headline number + placebos                       src/rederive9.py
  outputs     method_out.json (exp_gen_sol_out)                                              src/outputs9.py

Usage: uv run method.py --stages all | --stages b1,analyze,figures
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

from loguru import logger

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
PY = sys.executable

STAGES: dict[str, list[list[str]]] = {
    "preflight": [["s0_preflight.py"]],
    "units": [["units9.py"]],
    "tests": [["tests_cpu9.py"]],
    "commit0": [["commit9.py", "commit0"]],
    "cache_qwen": [["cmap9.py", "s1", "all"], ["cmap9.py", "s2", "all"]],
    "patch_qwen": [["cmap9.py", "s3", "all"]],
    "b3": [["b3_9.py", "gpu"]],
    "b1": [["b1_9.py", "gpu", m] for m in ("gemma", "gemma_pt", "llama", "llama_base")],
    "commit0b": [["commit9.py", "commit0b"]],
    "analyze": [["b1_9.py", "analyze"], ["b3_9.py", "analyze"], ["analysis9.py"]],
    "generate": [["b2gen9.py", "gpu"], ["b2gen9.py", "label"], ["b2gen9.py", "analyze"]],
    "figures": [["figures9.py"]],
    "positioning": [["positioning9.py"]],
    "rederive": [["rederive9.py"]],
    "outputs": [["outputs9.py"]],
}
ORDER = list(STAGES)


@logger.catch(reraise=True)
def main() -> None:
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    (ROOT / "logs").mkdir(exist_ok=True)
    logger.add(str(ROOT / "logs" / "method.log"), rotation="30 MB", level="DEBUG")
    ap = argparse.ArgumentParser()
    ap.add_argument("--stages", default="all", help="comma-separated stage names or 'all'")
    args = ap.parse_args()
    todo = ORDER if args.stages == "all" else [s.strip() for s in args.stages.split(",")]
    for s in todo:
        if s not in STAGES:
            raise ValueError(f"unknown stage {s}; known: {ORDER}")
    for s in todo:
        for cmd in STAGES[s]:
            t0 = time.time()
            logger.info(f"stage {s}: {' '.join(cmd)}")
            r = subprocess.run([PY, *cmd], cwd=SRC)
            if r.returncode != 0:
                raise RuntimeError(f"stage {s} failed: {' '.join(cmd)} (exit {r.returncode})")
            logger.info(f"stage {s}: done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
