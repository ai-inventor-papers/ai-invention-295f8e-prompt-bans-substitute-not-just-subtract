#!/usr/bin/env python3
"""TP-G2 (iteration 10): do program-state maps of code LMs track expansion DISCIPLINE or storage CONTAINER, and where
do the survivor families of the five-name ban land on a frame built from a discipline x container factorial?

Method (G1): Qwen3-32B (OpenRouter, thinking off) writes name-scrubbed grid path programs for a pre-committed 6 x 6
discipline x container factorial (24 implementable cells, 12 verified programs each). Each program is teacher-forced
under iteration 9's neutral-twin context through an exact truncated decoder and read out with iteration 9's frozen
readout R1 (mean over code tokens) at block 17 of Qwen3-8B bf16 and block 33 of Qwen3-32B NF4. The program-state RDM
is fitted with partial Spearman correlations against the discipline RDM controlling container (rho_dc) and the
reverse (rho_cd); restricted (within-stratum) permutations and a program bootstrap give the inference.
Baselines (same pipeline, same programs): E0 = bag-of-tokens embedding mean; RANDNET = random-init truncated Qwen3-8B;
token-surface / length / context RDMs fitted jointly (rank regression); the 3 x 4 crossed core.
Method (G2): survivor families (unit-weight Dijkstra, grid Bellman-Ford, coordinate-key heaps, random frontiers, raster
sweeps, set frontiers, covert BFS/DFS) are placed out of sample on the factorial + catalogue frame with iteration 9's
kNN-geodesic landing code (also on container-held-fixed and discipline-held-fixed subframes).

Stages (each resumable; every module lives in src/):
  setup      copy inputs with sha256 (scripts/setup_inputs.py)
  r0         reproduction gate on iteration 9's frozen frames (src/r0.py)
  tests      verifier unit tests (tests/test_verifiers.py) and analysis unit tests (tests/test_analysis.py)
  generate   smoke -> pilot -> COMMIT1a -> wave A/B with repair -> paraphrase fallback (src/gen.py)
  assemble   placed-program families (src/assemble.py)
  freeze     factorial / top-up freeze (src/freeze.py)
  states     Qwen3-8B, RANDNET, Qwen3-32B states (src/extract.py)
  g1 | g2 | robust   analyses (src/analysis.py), outputs (src/outputs.py), figures (src/figures.py)
  audit      stdlib re-derivation (audit/rederive.py)
Usage: .venv/bin/python method.py <stage> [...]   ('all-analysis' runs g1, g2, robust, outputs, figures, audit)
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from loguru import logger

ROOT = Path(__file__).resolve().parent
PY = sys.executable
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_v] = "1"

STAGES: dict[str, list[list[str]]] = {
    "setup": [["python3", "scripts/setup_inputs.py"]],
    "r0": [[PY, "src/r0.py"]],
    "tests": [[PY, "tests/test_verifiers.py"], [PY, "tests/test_analysis.py"]],
    "generate": [[PY, "src/gen.py", "smoke"], [PY, "src/gen.py", "pilot"], [PY, "src/gen.py", "main"],
                 [PY, "src/gen.py", "paraphrase"]],
    "assemble": [[PY, "src/assemble.py"]],
    "freeze": [[PY, "src/freeze.py", "factorial"], [PY, "src/freeze.py", "topups"]],
    "states": [[PY, "src/extract.py", "8b", "repro", "placed", "refs", "factorial", "factorial_ctx2", "topups"],
               [PY, "src/extract.py", "randnet", "factorial"],
               [PY, "src/extract.py", "32b", "repro", "placed", "refs", "factorial", "topups"]],
    "order": [[PY, "scripts/order_matrix.py"]],
    "g1": [[PY, "src/analysis.py", "g1", "8b", "32b"]],
    "g2": [[PY, "src/analysis.py", "g2", "8b", "32b"]],
    "robust": [[PY, "src/analysis.py", "robust", "8b", "32b"]],
    "outputs": [[PY, "src/outputs.py"]],
    "figures": [[PY, "src/figures.py"]],
    "audit": [["python3", "-I", "audit/rederive.py"]],
}
STAGES["all-analysis"] = STAGES["g1"] + STAGES["g2"] + STAGES["robust"] + STAGES["outputs"] + STAGES["figures"] + \
    STAGES["audit"]


@logger.catch(reraise=True)
def main() -> None:
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    (ROOT / "logs").mkdir(exist_ok=True)
    logger.add(str(ROOT / "logs" / "method.log"), rotation="30 MB", level="DEBUG")
    stages = sys.argv[1:] or ["all-analysis"]
    for st in stages:
        if st not in STAGES:
            raise SystemExit(f"unknown stage {st}; choose from {sorted(STAGES)}")
        for cmd in STAGES[st]:
            logger.info(f"[{st}] {' '.join(cmd)}")
            r = subprocess.run(cmd, cwd=ROOT)
            if r.returncode != 0:
                logger.error(f"[{st}] failed with exit code {r.returncode}")
                raise SystemExit(r.returncode)


if __name__ == "__main__":
    main()
