#!/usr/bin/env python3
"""Where noise must go to change the idea -- orchestrator (one sub-command per stage; every stage is resumable).

  uv run method.py tests-cpu     # CPU unit tests T1-T5 (hook maths, hull, permutation null, screen, binomial p)
  uv run method.py screen        # STEP 6 screen file (exp17 + exp13 rows) -> results/screen.json + sha256
  uv run method.py gpu           # STEPS 0-5, GPU tests, commit gates, engine check, staged sampling (src/gpu_main.py)
  uv run method.py commit0       # commit #0 (protocol, precision rule, units, screen hash) -> lets the engine check run
  uv run method.py commit1       # predictions + decision code -> lets decisive sampling start
  uv run method.py label         # STEP 10 label worker (follows data/samples_raw.jsonl until sampling_done.json)
  uv run method.py k7            # exp9 extended / K=7 labels for every T1 row (C3d)
  uv run method.py analysis      # STEP 11 (results/*.json); optional: --boot B --workers W
  uv run method.py audit         # STEP 12: known-solution index, stress tests, judge controls, blind judges
  uv run method.py audit-summary # STEP 12.5 (needs audit/manual_pass.jsonl from the executor's manual pass)
  uv run method.py deps          # how each dependency dataset is used (+ HumanEval+ sandbox validation)
  uv run method.py rederive      # independent re-derivation + placebos (audit/rederive.py)
  uv run method.py rederive-headlines  # second re-derivation of the headlines from raw files (different methods)
  uv run method.py u4            # U4 follow-up diagnostic (GPU)
  uv run method.py figures       # figures/*.pdf|png
  uv run method.py outputs       # method_out.json (exp_gen_sol_out)
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from loguru import logger

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
PY = sys.executable

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
(ROOT / "logs").mkdir(exist_ok=True)
logger.add(str(ROOT / "logs" / "method.log"), rotation="30 MB", level="DEBUG")


def run(args: list[str], cwd: Path = SRC) -> None:
    env = dict(os.environ, PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True")
    logger.info(f"$ {' '.join(args)}  (cwd {cwd.relative_to(ROOT) if cwd != ROOT else '.'})")
    r = subprocess.run([PY] + args, cwd=cwd, env=env)
    if r.returncode != 0:
        raise SystemExit(f"stage failed ({r.returncode}): {' '.join(args)}")


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stage")
    ap.add_argument("--boot", type=int, default=1000)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--budget-hours", type=float, default=3.3)
    a = ap.parse_args()
    s = a.stage
    if s == "tests-cpu":
        run(["../tests/test_cpu.py"])
    elif s == "screen":
        run(["screen.py"])
    elif s == "gpu":
        run(["gpu_main.py", "--stage", "all", "--budget-hours", str(a.budget_hours)])
    elif s == "commit0":
        run(["prereg.py", "0"])
    elif s == "commit1":
        run(["predictions_spec.py"])
        run(["prereg.py", "1", "hull.py", "label_pipeline.py", "predictions_spec.py", "screen.py", "prereg.py",
             "commit.py"])
    elif s == "label":
        run(["label_pipeline.py", "follow"])
    elif s == "k7":
        run(["label_k7.py"])
    elif s == "analysis":
        run(["analysis.py", str(a.boot), str(a.workers)])
    elif s == "audit":
        run(["audit.py", "index"])
        run(["audit.py", "run"])
    elif s == "audit-summary":
        run(["audit.py", "summary"])
    elif s == "deps":
        run(["audit.py", "deps"])
    elif s == "rederive":
        run(["audit/rederive.py"], cwd=ROOT)
    elif s == "rederive-headlines":
        run(["audit/rederive_headlines.py"], cwd=ROOT)
    elif s == "u4":
        run(["tests/u4_diagnostic.py"], cwd=ROOT)
    elif s == "figures":
        run(["figures.py"])
    elif s == "outputs":
        run(["outputs.py"])
    else:
        raise SystemExit(f"unknown stage {s}")


if __name__ == "__main__":
    main()
