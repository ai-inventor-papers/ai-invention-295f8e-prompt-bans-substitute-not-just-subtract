#!/usr/bin/env python3
"""NOV-B1 entry point: FunSearch-style island search on online bin packing with Qwen3-8B-FP8 as the mutator.

The proposed method is decision-token branching (DTB: force a rank-2..8 token at the highest-entropy code token of the
first 48 body tokens); its baselines run side by side in the same pipeline at matched calls: temperature T1.0,
temperature T1.6 (top-p 0.95), the random-position placebo RPB, the idea instruction IDEA, and a no-selection arm NS,
plus the known-heuristic corpus (best fit, FunSearch c12/c14, EoH, ReEvo, HSEvo, MCTS-AHD, LLM4AD, Sum-of-Squares,
the ab family and a tuned ab member).

Every stage is a resumable script under src/ and writes results/*.json; this file runs them in order:
  s0      copy check + harness gate          (src/s0_verify.py verify, src/gate.py, src/s0_verify.py gate)
  s1      probes, corpus, unit tests          (src/probes.py, src/corpus.py, tests/unit_tests.py)
  vllm    start the vLLM server               (start_vllm.sh; Qwen/Qwen3-8B-FP8 @ 220b46e)
  smoke   seed-99 smoke round                 (src/search.py --run smoke)
  search  main search, pauses after round 4 for commit #2 (src/search.py --run main; src/commit2.py)
  ns      no-selection arm                    (src/search.py --run ns)
  post    clusters, best programs, V1/V2, V3 candidates, V6, evaluator effect, placebos (src/postsearch.py)
  judges  gate + candidates                   (src/judges.py)
  v5      founder reversion                   (src/v5.py)
  final   V3 classes, figures, method_out.json, independent re-derivation (src/v3_final.py, src/figures.py,
          src/outputs.py, audit/rederive.py)
Commitments (predictions/commit1-4.json, commitments.log hash chain) are written by src/commit.py / src/commit2.py and
must precede the samples they govern. Usage: uv run method.py <stage> [<stage> ...] | uv run method.py final
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

from loguru import logger

ROOT = Path(__file__).resolve().parent
PY = [sys.executable, "-I"]
ENV = dict(os.environ, OMP_NUM_THREADS="1", HF_HUB_OFFLINE=os.environ.get("HF_HUB_OFFLINE", "1"))
STAGES = {
    "s0": [["src/s0_verify.py", "verify"], ["src/gate.py"], ["src/s0_verify.py", "gate"]],
    "s1": [["src/probes.py"], ["src/corpus.py", "10"], ["tests/unit_tests.py"]],
    "smoke": [["src/search.py", "--run", "smoke", "--seeds", "99", "--rounds", "1", "--calls-per-round", "10"]],
    "search": [["src/search.py", "--run", "main", "--seeds", "0,1", "--rounds", "80", "--pause-after", "3"]],
    "ns": [["src/search.py", "--run", "ns", "--seeds", "0,1", "--rounds", "40", "--arms", "NS"]],
    "post": [["src/postsearch.py", "clusters,best,v12,v3"]],
    "judges": [["src/judges.py", "gate"], ["src/judges.py", "candidates"]],
    "v5": [["src/v5.py"]],
    "final": [["src/v3_final.py"], ["src/postsearch.py", "v6,evaluator,placebo"], ["src/figures.py"],
              ["src/costs.py"], ["audit/rederive.py"], ["src/outputs.py"]],
}


def run(stage: str) -> None:
    if stage == "vllm":
        pid = subprocess.run(["bash", str(ROOT / "start_vllm.sh")], capture_output=True, text=True).stdout.strip()
        logger.info(f"vLLM server PID {pid} (poll logs/vllm.log for 'GPU KV cache size' and /health)")
        return
    for cmd in STAGES[stage]:
        t0 = time.time()
        logger.info(f"[{stage}] {' '.join(cmd)}")
        r = subprocess.run(PY + [str(ROOT / cmd[0])] + cmd[1:], cwd=ROOT, env=ENV)
        if r.returncode != 0:
            raise RuntimeError(f"stage {stage} failed at {cmd} (exit {r.returncode})")
        logger.info(f"[{stage}] done in {time.time() - t0:.0f}s")


@logger.catch(reraise=True)
def main() -> None:
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    logger.add(ROOT / "logs" / "method.log", rotation="30 MB", level="DEBUG")
    stages = sys.argv[1:] or ["final"]
    for st in stages:
        run(st)


if __name__ == "__main__":
    main()
