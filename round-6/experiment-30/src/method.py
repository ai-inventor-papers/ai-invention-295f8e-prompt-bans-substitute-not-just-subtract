#!/usr/bin/env python3
"""Where noise changes the algorithm, in bf16 (iteration 6, Step 2): orchestrator, one sub-command per stage.

  uv run method.py inputs     STEP 0.2  input hashes (inputs/SHA256SUMS) + bench check against commitment.json
  uv run method.py cputests   STEP 0.4  CPU unit tests -> results/unit_tests_cpu.json
  uv run method.py prep       STEP 1-2, 5 (GPU) positions, r_Q, ban-free units, forced states, banned sets, pushes
  uv run method.py seeds      STEP 1.4  direction seeds + cosines with earlier directions -> directions/seeds.json
  uv run method.py gputests   STEP 4 (GPU) U1-U7, positive control U8, smoke batches
  uv run method.py commit1    STEP 6    commit #1 (predictions/s_commit.json + hash chain)
  uv run method.py sample     STEP 7 (GPU) decisive sampling (waits for commit #1; staged; time-only drop order)
  uv run method.py label      STEP 8    label worker (follows data/samples_raw.jsonl) ; label_k7 for T1
  uv run method.py score      STEP 5.4/5.5 (GPU) F2 q_lik passes on 15 tasks + thinking-on T2 margin
  uv run method.py commit2    STEP 9    commit #2 (final analysis code)
  uv run method.py analyse    STEP 9    every analysis -> results/*.json
  uv run method.py audit      STEP 9.10 novelty audit (OpenRouter judges, capped) -> results/novelty_audit.json
  uv run method.py figures    STEP 10   figures/*.pdf + .png
  uv run method.py outputs    STEP 11   method_out.json (+ re-derivation audit/rederive.py)
The GPU stages run src/gpu_main.py / src/scoring.py in their own process (model loaded once per stage).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
PY = sys.executable


def run(args: list[str]) -> int:
    import os

    print("+", " ".join(args), flush=True)
    env = dict(os.environ)
    for v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
        env.setdefault(v, "2")  # 5-CPU cgroup on a 48-core host: avoid BLAS oversubscription
    return subprocess.call(args, cwd=str(SRC), env=env)


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    cmd = sys.argv[1]
    extra = sys.argv[2:]
    table = {
        "inputs": [PY, "prereg.py", "inputs"],
        "cputests": [PY, str(ROOT / "tests" / "test_cpu.py")],
        "prep": [PY, "gpu_main.py", "--stage", "prep"],
        "seeds": [PY, "prereg.py", "seeds"],
        "gputests": [PY, "gpu_main.py", "--stage", "tests"],
        "commit1": [PY, "prereg.py", "commit1"],
        "sample": [PY, "gpu_main.py", "--stage", "sample"] + extra,
        "label": [PY, "label_worker.py", "once"],
        "label_k7": [PY, "label_k7.py"],
        "score": [PY, "scoring.py", "all"],
        "commit2": [PY, "prereg.py", "commit2"],
        "analyse": [PY, "analysis.py"],
        "audit": [PY, "audit.py", "run"],
        "audit_summary": [PY, "audit.py", "summary"],
        "figures": [PY, "figures.py"],
        "outputs": [PY, "outputs.py"],
        "rederive": [PY, str(ROOT / "audit" / "rederive.py")],
    }
    if cmd not in table:
        print(f"unknown stage {cmd}\n{__doc__}")
        return 1
    rc = run(table[cmd])
    if cmd == "label" and rc == 0:
        rc = run(table["label_k7"])
    if cmd == "outputs" and rc == 0:
        rc = run(table["rederive"])
    return rc


if __name__ == "__main__":
    sys.exit(main())
