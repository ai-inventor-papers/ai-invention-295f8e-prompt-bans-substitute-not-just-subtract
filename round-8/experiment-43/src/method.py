#!/usr/bin/env python3
"""Predicting how temperature shifts code ideas (iteration 8, claim L): entry point.

Runs every stage in order (each stage resumes from its result files; commits refuse to overwrite):
  vendor      copy the prior artifacts' files into inputs/ with sha256 (src/vendor_inputs.py)
  prompts     prompt ids per (unit, template) with source checks (src/prompts8.py)
  cputests    U5/U8/U9/U10/U11, change-point rule, scoring dry run on iteration-7 data, labeller references
  commit0     protocol8L.json + code hashes, COMMIT #0 (src/commit0.py)
  gemma       held-out family 1: tests, fit (+ engine check), locate, COMMIT #1, predict, COMMIT #2, sweep
  llama       held-out family 2: the same plus bench-candidate selection (COMMIT #1a) and label re-gate (COMMIT #1b)
  qwen        law-development family: A3, B6 (second decisions), B3 (fresh streams)
  base        base sub-arm: Qwen3-8B and Qwen3-8B-Base teacher forcing, then analysis (src/base_arm.py)
  adjudicate  judges on cells with > 20% 'other' (src/novelty8.py adjudicate)
  analysis    committed scoring (src/analysis_L.py) -> results/analysis_L.json, results/verdict.json
  novelty     novelty audit of every correct off-catalogue program (src/novelty8.py audit)
  figures     F1-F6 (src/figures8.py)
  report      results/summary.md (src/report8.py)
  outputs     method_out.json (src/outputs8.py)
  rederive    audit/rederive.py (standard library only)
Usage: .venv/bin/python method.py all | <stage>[,<stage>...]
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
PY = sys.executable
GPU_STAGES = "tests,fit,locate,commit1,predict,commit2,sweep"

STAGES = {
    "vendor": [[PY, "vendor_inputs.py"]],
    "prompts": [[PY, "prompts8.py"]],
    "cputests": [[PY, "tests_cpu.py"]],
    "commit0": [[PY, "commit0.py"]],
    "gemma": [[PY, "gpu8.py", "gemma", GPU_STAGES]],
    "llama": [[PY, "gpu8.py", "llama", GPU_STAGES]],
    "qwen": [[PY, "gpu8.py", "qwen", GPU_STAGES]],
    "base": [[PY, "base_arm.py", "gpu", "qwen"], [PY, "base_arm.py", "gpu", "qwen_base"], [PY, "base_arm.py", "analyze"]],
    "adjudicate": [[PY, "novelty8.py", "adjudicate"]],
    "analysis": [[PY, "analysis_L.py"]],
    "novelty": [[PY, "novelty8.py", "audit"]],
    "figures": [[PY, "figures8.py"]],
    "report": [[PY, "report8.py"]],
    "outputs": [[PY, "outputs8.py"]],
    "rederive": [[PY, "-I", str(ROOT / "audit" / "rederive.py")]],
}
ORDER = list(STAGES)


def main() -> None:
    want = ORDER if len(sys.argv) < 2 or sys.argv[1] == "all" else sys.argv[1].split(",")
    env = dict(os.environ, PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True")
    for st in want:
        for cmd in STAGES[st]:
            print(f"== {st}: {' '.join(cmd[1:])}", flush=True)
            r = subprocess.run(cmd, cwd=str(SRC), env=env)
            if r.returncode != 0:
                raise SystemExit(f"stage {st} failed ({r.returncode})")


if __name__ == "__main__":
    main()
