#!/usr/bin/env python3
"""Plan noise against plan-first prompting (iteration 5, Claim C) + the literal thinking-on cell (Claim F).

Orchestrator: every stage is a script under src/ that resumes from what is already on disk (keyed by task, arm,
template, slot), so `method.py all` can be re-run after an interruption. The vLLM stage runs in .venv_vllm (never
imported together with the HF engine); everything else runs in .venv.

Stages (in the order they were run, see reproducibility.md):
  s0        hardware + precision rule, input hashes, seed registry, labeller re-check     src/s0.py
  prompts   every stage-1 prompt (twin/plain/novelty/semseed + frame-matched IFG/PSL/EAP)  src/prompts5.py
  commit0F  literal-cell spec + analysis_f.py by sha256                                     src/prereg5.py
  literal   S2 literal cell on vLLM (FP8 checkpoint, thinking on, top-k 10, 4 T + repeat)   src/vllm_literal.py
  label_f   frozen exp8-suite labels of the literal cell's final code                       src/label_worker_v4.py
  gpu       S3 base intents, GPU tests, S4 DMD calibration + format pilot, S1 engine check
            (after commit0C), S5 knob queue (after commit1)                                  src/gen5.py
  commit0C  Claim-C rule, arm table, thresholds, analysis code, prompt hashes               src/prereg5.py
  commit1   DMD temperatures, format pilot, batch probe                                     src/prereg5.py
  label     S6 labels of the knob rows (follows data/samples_raw.jsonl)                     src/label5.py
  audit     lexicon audit (F), style re-gate, novelty audit (OpenRouter judges)             src/audit5.py
  analyze   analysis_f (F), analysis_ec (engine check), analysis_c (Claim C)                src/analysis_*.py
  figures   F1-F6                                                                           src/figures5.py
  outputs   method_out.json (+ full/mini/preview)                                           src/outputs5.py
  rederive  independent re-derivation + placebos                                            audit/rederive.py

usage: .venv/bin/python method.py <stage>[,<stage>...] | all
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

from loguru import logger

ROOT = Path(__file__).resolve().parent
PY = str(ROOT / ".venv" / "bin" / "python")
PYV = str(ROOT / ".venv_vllm" / "bin" / "python")
(ROOT / "logs").mkdir(exist_ok=True)
logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(str(ROOT / "logs" / "method.log"), rotation="30 MB", level="DEBUG")

STAGES: dict[str, list[list[str]]] = {
    "s0": [[PY, "src/s0.py", "all"]],
    "prompts": [[PY, "src/prompts5.py"]],
    "commit0F": [[PY, "src/prereg5.py", "commit0F"]],
    "literal": [[PYV, "src/vllm_literal.py", "all"]],
    "label_f": [[PY, "src/label_worker_v4.py", "--raw", "data/literal_samples.jsonl", "--out",
                 "data/literal_labels.jsonl", "--name", "label_literal"]],
    "gpu": [[PY, "src/gen5.py", "base,tests,calib,ec,knobs"]],
    "commit0C": [[PY, "src/prereg5.py", "commit0C"]],
    "commit1": [[PY, "src/prereg5.py", "commit1"]],
    "label": [[PY, "src/label5.py"],
              [PY, "src/label_worker_v4.py", "--raw", "data/engine_check_raw.jsonl", "--out",
               "data/engine_check_labels.jsonl", "--name", "label_ec"]],
    "audit": [[PY, "src/audit5.py", "all"]],
    "analyze": [[PY, "src/analysis_f.py"], [PY, "src/analysis_ec.py"], [PY, "src/analysis_c.py"]],
    "figures": [[PY, "src/figures5.py"]],
    "outputs": [[PY, "src/outputs5.py"]],
    "rederive": [[PY, "audit/rederive.py"]],
}
ORDER = ["s0", "prompts", "commit0F", "literal", "label_f", "gpu", "commit0C", "commit1", "label", "audit",
         "analyze", "figures", "outputs", "rederive"]


@logger.catch(reraise=True)
def main() -> None:
    want = ORDER if len(sys.argv) < 2 or sys.argv[1] == "all" else sys.argv[1].split(",")
    for st in want:
        if st not in STAGES:
            raise SystemExit(f"unknown stage {st}; choose from {ORDER}")
        if st == "gpu" and "all" in sys.argv[1:]:
            logger.warning("the gpu stage blocks on commit0C/commit1: run commit0C and commit1 from a second shell "
                           "once calibration has finished (results/calib_done.flag)")
        for cmd in STAGES[st]:
            t0 = time.time()
            logger.info(f"[{st}] {' '.join(cmd[1:])}")
            r = subprocess.run(cmd, cwd=str(ROOT))
            if r.returncode != 0:
                logger.error(f"[{st}] failed with exit code {r.returncode}")
                raise SystemExit(r.returncode)
            logger.info(f"[{st}] done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
