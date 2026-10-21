#!/usr/bin/env python3
"""Artifact E -- did 8-bit arithmetic cause the nudge effect? Entry point that runs the whole pipeline in order.

Method vs baseline: the 2x2 weight-by-activation precision factorial of per-sample plan noise (PN) on Qwen3-8B.
W16A16 (native bf16 nn.Linear, the iteration-5 engine) is the baseline; W8A8 (emulated e4m3 weights x e4m3
activations, the iteration-4 engine's numerics) is the method under test; W8A16 / W16A8 split the effect into its
weight and activation halves; W8A8REAL is exp19's own FP8Linear (torch._scaled_mm) on this sm_89 card.

Stages (each is a script under src/; every stage is resumable and writes JSONL/JSON immediately):
  a        src/stage_a.py        inputs + sha256 (committed), iteration-4 reference numbers, prompt diff, landing ref
  recheck  src/label_e.py --recheck    the copied labeller re-labels exp19 / exp22 rows (must agree 1.00)
  tests    src/run_e.py --stage tests  device rule + memory probe + GPU tests U1-U8;  src/tests_cpu.py CPU tests 1-8
  smoke    src/run_e.py --stage smoke  every arm type end to end (rows in data/smoke_*.jsonl)
  commit0  src/commit0.py        predictions, rules, analysis code sha256 -> commitments.log (before decisive rows)
  gen      run_gpu_pipeline.sh   generation queue (engine check, factorial, T03, unit cross, dither, REAL cells) then
                                 the mechanism readouts; src/label_e.py --follow-until labels rows as they appear
  commit1  src/commit1.py        gate outcomes + timing -> commitments.log
  analysis src/analysis_e.py     Stage G statistics -> results/*.json
  novelty  src/novelty_e.py      blind two-judge novelty audit of correct 'other' programs (OpenRouter, cap 0.50 USD)
  dep      src/dep_usage_e.py    dependency art_j3Rm_lr2nzR6: known solutions + per-dataset usage
  rederive src/rederive_e.py     independent re-derivation + placebos + commit-chain audit
  figures  src/figures_e.py      F1-F8
  outputs  src/outputs_e.py      method_out.json (exp_gen_sol_out)

Usage: uv run method.py --stage all        (or one stage name; 'post' = analysis..outputs)
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

from loguru import logger

ROOT = Path(__file__).resolve().parent
PY = sys.executable
(ROOT / "logs").mkdir(exist_ok=True)
logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(str(ROOT / "logs" / "method.log"), rotation="30 MB", level="DEBUG")

STAGES = {
    "a": [[PY, "src/stage_a.py"]],
    "recheck": [[PY, "src/label_e.py", "--recheck"]],
    "tests": [[PY, "src/run_e.py", "--stage", "tests"], [PY, "src/tests_cpu.py"]],
    "smoke": [[PY, "src/run_e.py", "--stage", "smoke"],
              [PY, "src/label_e.py", "--raw", "data/smoke_raw.jsonl", "--out", "data/smoke_labels.jsonl"]],
    "commit0": [[PY, "src/commit0.py"]],
    "gen": [["bash", "run_gpu_pipeline.sh"]],
    "label": [[PY, "src/label_e.py"]],
    "commit1": [[PY, "src/commit1.py"]],
    "dep": [[PY, "src/dep_usage_e.py"]],
    "analysis": [[PY, "src/analysis_e.py"]],
    "novelty": [[PY, "src/novelty_e.py"]],
    "rederive": [[PY, "src/rederive_e.py"]],
    "figures": [[PY, "src/figures_e.py"]],
    "outputs": [[PY, "src/outputs_e.py"]],
}
ORDER = ["a", "recheck", "tests", "smoke", "commit0", "gen", "label", "commit1", "dep", "analysis", "novelty",
         "analysis", "rederive", "figures", "outputs"]
POST = ["label", "dep", "analysis", "novelty", "analysis", "rederive", "figures", "outputs"]


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="all", choices=["all", "post"] + list(STAGES))
    args = ap.parse_args()
    names = ORDER if args.stage == "all" else (POST if args.stage == "post" else [args.stage])
    env = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
    for name in names:
        for cmd in STAGES[name]:
            t0 = time.time()
            logger.info(f"stage {name}: {' '.join(cmd[1:] if cmd[0] == PY else cmd)}")
            try:
                subprocess.run(cmd, cwd=ROOT, env=env, check=True)
            except subprocess.CalledProcessError as e:
                logger.error(f"stage {name} failed with exit code {e.returncode}")
                raise
            logger.info(f"stage {name} done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
