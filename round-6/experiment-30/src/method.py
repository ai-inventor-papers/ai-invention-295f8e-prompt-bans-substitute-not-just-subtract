#!/usr/bin/env python3
"""Where in the prompt the algorithm is chosen -- iteration 6 entry point (bf16 Qwen3-8B, one 16 GB GPU).

Method (Stage A): full-state exchange of the modal ban's residual states into the token-length-matched neutral twin,
per block band at the task-specification positions, plus a KV splice of the condition span (direct route) and a
read-position exchange. Baselines/controls: the neutral twin itself, a matched-norm random exchange (MR), a placebo
exchange from a second neutral twin, identity and KV-splice equivalence tests. Also: the bf16 noise-site grid with a
Firth indicator model at matched downstream displacement (ST), state noise vs KL-matched temperature (P4 half), the
top-five plan push on the forced-prompt geometry, and a retrospective landing-forecast contest (L).

Every stage runs in its own process (the GPU holds one model at a time) and is resumable; usage:
    .venv/bin/python method.py [all | prompts utest commit0 gpu ext lgpu label analysis novelty figures outputs audit]
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

from loguru import logger

ROOT = Path(__file__).resolve().parent
PY = str(ROOT / ".venv" / "bin" / "python")
logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
(ROOT / "logs").mkdir(exist_ok=True)
logger.add(str(ROOT / "logs" / "method.log"), rotation="30 MB", level="DEBUG")

STAGES = {
    "prompts": [[PY, "src/prompts6.py"]],                                 # STEP 0-1 (CPU): prompts, positions, dep
    "utest": [[PY, "src/gpu6.py", "utest"]],                              # STEP 2 (GPU): U1-U5
    "commit0": [[PY, "src/prereg6.py"]],                                  # commit #0 before any decisive sample
    "gpu": [["bash", "scripts/run_gpu_main.sh", "175"]],                  # STEPS 4-8 (GPU, deadline in minutes)
    "ext": [[PY, "src/gpu6.py", "ext", "--deadline-min", "25"]],           # STEP 9 extensions (forced, seed, W4)
    "label": [[PY, "src/label6.py"]],                                     # STEP 10 (CPU worker; follows the GPU)
    "lgpu": [[PY, "src/lcontest.py", "events"], [PY, "src/lcontest.py", "open"]],  # STEP 3 (L teacher-forced)
    "analysis": [[PY, "src/analysis6.py"], [PY, "src/lcontest.py", "score"]],
    "novelty": [[PY, "src/novelty6.py"]],
    "figures": [[PY, "src/figures6.py"]],
    "outputs": [[PY, "src/bookkeeping6.py"], [PY, "src/outputs6.py"]],
    "audit": [["python3", "-I", "audit/rederive.py"]],
}
ORDER = ["prompts", "utest", "commit0", "gpu", "ext", "lgpu", "label", "analysis", "novelty", "figures", "outputs",
         "audit"]


@logger.catch(reraise=True)
def main() -> None:
    want = sys.argv[1:] or ["all"]
    stages = ORDER if want == ["all"] else want
    for st in stages:
        for cmd in STAGES[st]:
            t0 = time.time()
            logger.info(f"stage {st}: {' '.join(cmd)}")
            if st == "label" and "all" in want:
                (ROOT / "results" / "gpu_all_done.flag").write_text("done\n")  # the GPU work above has finished
            r = subprocess.run(cmd, cwd=ROOT)
            logger.info(f"stage {st} exit {r.returncode} in {time.time() - t0:.0f}s")
            if r.returncode != 0:
                raise RuntimeError(f"stage {st} failed ({' '.join(cmd)})")


if __name__ == "__main__":
    main()
