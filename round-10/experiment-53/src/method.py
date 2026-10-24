#!/usr/bin/env python3
"""NOV-T: decision-token branching (DTB) vs temperature in a FunSearch-style search over constructive TSP heuristics.

Method (DTB) and baselines/comparators (T1.0, T1.6, RPB placebo, IDEA, NOSEL; NN seed program, tuned parametric P1,
insertion / greedy-edge references, published-heuristic corpus) all run in the same pipeline: same LLM
(Qwen3-8B-FP8 on vLLM 0.11), same prompts, same selection instances, matched calls per arm and seed.

Stages (each is its own process; long ones run in the background with checkpoints and can resume):
  python method.py stage0      # hardware, instances, probe states, TSPLIB, LKH-3 references, NN gate, baselines
  python method.py p1          # tuned parametric baseline P1: 2,000-evaluation random search (rng 777)
  python method.py tests       # CPU unit tests T1-T9
  python method.py gpu         # GPU mechanics tests G1-G5 + throughput probe (needs the vLLM server)
  python method.py commit1     # predictions/protocol.json, hash-chained in commitments.log
  python method.py pilot       # seed 99, 10 calls per arm (excluded from analysis)
  python method.py search      # the main search (reads data/targets.json every round; data/STOP ends it)
  python method.py commit2     # C* from the measured round times (COMMIT #2) -> data/targets.json
  python method.py corpus      # published-heuristic corpus: extraction, sandbox admission, evaluation
  python method.py analyze     # clusters, rarefaction, bootstrap, held-out bests, verdicts -> results/*.json
  python method.py judges      # V3-T candidates -> gated OpenRouter judges (USD 0.50 cap)
  python method.py figures     # figures/F1..F6 (PDF + PNG)
  python method.py outputs     # method_out.json (exp_gen_sol_out) + full/mini/preview variants
  python method.py rederive    # audit/rederive.py: stdlib re-derivation + placebos
Start the server first: bash start_vllm.sh compile   (logs/vllm_server.log)
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from loguru import logger

ROOT = Path(__file__).resolve().parent
PY = sys.executable
logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
(ROOT / "logs").mkdir(exist_ok=True)
logger.add(str(ROOT / "logs" / "run.log"), rotation="30 MB", level="DEBUG")

STAGES = {
    "stage0": [PY, "src/stage0.py", "all"],
    "p1": [PY, "src/p1_search.py", "2"],
    "tests": [PY, "-m", "pytest", "-q", "-c", "tests/pytest.ini", "--rootdir", ".", "tests/test_core.py",
              "-p", "no:cacheprovider"],
    "gpu": [PY, "tests/gpu_mechanics.py"],
    "commit1": [PY, "src/commit.py", "commit1"],
    "pilot": [PY, "src/search.py", "--out", "data/pilot", "--n-eval", "4"],
    "search": [PY, "src/search.py", "--out", "data", "--n-eval", "4", "--wait"],
    "commit2": [PY, "src/cstar.py"],
    "corpus": [PY, "src/corpus.py"],
    "analyze": [PY, "src/analyze_run.py"],
    "judges": [PY, "src/judges.py"],
    "figures": [PY, "src/figures.py"],
    "outputs": [PY, "src/outputs.py"],
    "rederive": [PY, "audit/rederive.py"],
}


@logger.catch(reraise=True)
def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in STAGES:
        print(__doc__)
        sys.exit(0 if len(sys.argv) < 2 else 2)
    stage = sys.argv[1]
    cmd = STAGES[stage] + sys.argv[2:]
    logger.info(f"stage {stage}: {' '.join(cmd)}")
    try:
        r = subprocess.run(cmd, cwd=ROOT, check=False)
    except FileNotFoundError:
        logger.error(f"cannot run {cmd}")
        raise
    if r.returncode != 0:
        logger.error(f"stage {stage} exited with {r.returncode}")
        sys.exit(r.returncode)
    logger.info(f"stage {stage} finished")


if __name__ == "__main__":
    main()
