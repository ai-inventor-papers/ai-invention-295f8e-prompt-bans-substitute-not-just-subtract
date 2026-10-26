#!/usr/bin/env python3
"""Where the model's algorithm choice lives -- orchestrator (Qwen3-8B, FP8 W8A8 on a 16 GB RTX 2000 Ada).

Stages (each resumable; see README.md):
  s0        input copies + sha256 + bench verification, screen file (entry #0), labeller re-check
  prompts   masked descriptions (OpenRouter, leak-checked) + all 4,144 prompts
  gpu1      GPU unit tests, engine check (screen replication), states, units, realised displacements
  commit    S3 plan subspace + predictors, then S4 commit (predictions/c2_commit.json, commitments.log)
  label     label worker (run concurrently with gpu2)
  gpu2      S5 sampling stages A-H
  analyze   S7 analyses + figures (analysis/run_all.py)
  outputs   S8 method_out.json (+ mini/preview), audit
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(k, "4")   # the cgroup allows ~5 CPUs; unbounded BLAS threads oversubscribe them
PY = sys.executable


def sh(*args: str) -> None:
    print("+", " ".join(args), flush=True)
    subprocess.run([PY, *args], cwd=ROOT, check=True)


def main() -> None:
    stage = sys.argv[1] if len(sys.argv) > 1 else "help"
    extra = sys.argv[2:]
    if stage == "s0":
        sh("src/s0_setup.py")
        sh("src/screen.py")
        sh("src/recheck4.py")
    elif stage == "prompts":
        sh("src/describe.py")
        sh("src/prompts4.py")
    elif stage == "gpu1":
        sh("src/gpu_phase1.py", *(extra or ["tests", "engine", "states", "units", "realised"]))
    elif stage == "commit":
        sh("analysis/tests_cpu.py")
        sh("src/subspace.py")
        sh("src/make_commit.py")
    elif stage == "label":
        sh("src/label4.py", *extra)
    elif stage == "gpu2":
        sh("src/gpu_phase2.py", *extra)
    elif stage == "analyze":
        sh("analysis/run_all.py", *extra)
    elif stage == "outputs":
        sh("analysis/outputs.py", *extra)
        sh("audit/rederive.py")
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
