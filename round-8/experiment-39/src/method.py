#!/usr/bin/env python3
"""Temperature at one deciding token (iteration 8, claims K1 and HR): entry point running every stage in order.

The method: temperature applied ONLY at a located decision token (T = d with top-20 there, T = 1 everywhere else),
with d committed in advance from that token's teacher-forced logits and a token map of forced continuations.
The baselines/comparators, run on the same 50 common-random-number slot streams per unit: global temperature
1.3 / 1.6 / 2.0 with top-p 0.95, min-p 0.1 at T 3.0, EDT-style and AdapT-style per-token temperature, the
highest-entropy position and a random position at the same dose (placebos), and class-uniform forcing.

Stages (each resumes from its files; GPU stages run one model per process):
  vendor      copy and hash every prior input into inputs/                       (src/vendor_inputs.py)
  prompts     Gemma twin prompt ids (exp38 prompt code, run once)                   (scripts/build_gemma_prompts.sh)
  labeller    background label daemon (frozen labellers)                           (src/label_daemon.py)
  cputests    C1-C6                                                                (src/tests8.py cpu)
  commit0     protocol.json                                                        (src/protocol8.py, commit8.py)
  s0          twins + GPU tests U1-U8, Qwen then Gemma                             (src/gpu8.py <model> s0)
  gputests    evaluate U1-U8 -> identity-shortcut flag                             (src/tests8.py gpu)
  s2          token maps (Qwen, then Gemma)                                        (src/gpu8.py <model> s2)
  commit1     dose table and every committed prediction                            (src/make_commits.py c1)
  commit2     HR predictions and novelty-audit protocol                            (src/make_commits.py c2)
  s3          arms (Gemma, Qwen)                                                    (src/gpu8.py <model> s3)
  s4          HR branches                                                          (src/gpu8.py <model> s4)
  s1          blind locator (T10, B3); COMMIT #1b is its verdict                    (src/gpu8.py qwen s1)
  commit3     adjudication + the pass-filtered-dose amendment (COMMIT #3)           (src/amend8.py)
  s3x         amendment arms A9f/A10f on T10 and G                                 (src/gpu8.py <model> s3x)
  analyse     adjudication, stage-0 report, K1 analysis, amendment, HR, locator, novelty audit, tables, figures,
              outputs, stdlib audit
Usage: .venv/bin/python method.py all | <stage>[,<stage>...]
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

from loguru import logger

ROOT = Path(__file__).resolve().parent
PY = str(ROOT / ".venv" / "bin" / "python")
QWEN_UNITS = "T10,B3,T1,A3,B6"

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
(ROOT / "logs").mkdir(exist_ok=True)
logger.add(str(ROOT / "logs" / "method.log"), rotation="30 MB", level="DEBUG")

STEPS: dict[str, list[list[str]]] = {
    "vendor": [[PY, "src/vendor_inputs.py"]],
    "prompts": [["bash", "scripts/build_gemma_prompts.sh"]],
    "cputests": [[PY, "src/tests8.py", "cpu"]],
    "commit0": [[PY, "src/protocol8.py"],
                [PY, "src/commit8.py", "commit", "COMMIT0_protocol", "predictions/protocol.json", "src/cfg8.py",
                 "src/engine8.py", "src/predict8.py", "src/units8.py", "src/gpu8.py", "src/stages8.py"]],
    "s0": [[PY, "src/gpu8.py", "qwen", "s0"], [PY, "src/gpu8.py", "gemma", "s0"]],
    "gputests": [[PY, "src/stage0_report.py"], [PY, "src/tests8.py", "gpu"]],
    "s2": [[PY, "src/gpu8.py", "qwen", "s2", "--units", QWEN_UNITS], [PY, "src/gpu8.py", "gemma", "s2"]],
    "commit1": [[PY, "src/make_commits.py", "c1"]],
    "commit2": [[PY, "src/make_commits.py", "c2"]],
    "s3": [[PY, "src/gpu8.py", "gemma", "s3,s4"], [PY, "src/gpu8.py", "qwen", "s3,s4", "--units", "T10,B3"],
           [PY, "src/gpu8.py", "qwen", "s3", "--units", "B6,T2,T03,T1,A3"]],
    "s1": [[PY, "src/gpu8.py", "qwen", "s1", "--units", "T10,B3"]],
    "s4": [[PY, "src/gpu8.py", "qwen", "s4", "--units", "B6,A3"], [PY, "src/gpu8.py", "qwen", "s3", "--units", "A3"]],
    "commit3": [[PY, "src/novelty8.py", "adjudicate"], [PY, "src/amend8.py"]],
    "s3x": [[PY, "src/gpu8.py", "qwen", "s3x", "--units", "T10"], [PY, "src/gpu8.py", "gemma", "s3x", "--units", "G"]],
    "analyse": [[PY, "src/novelty8.py", "adjudicate"], [PY, "src/stage0_report.py"], [PY, "src/analysis_k1.py"],
                [PY, "src/amend_analysis8.py"], [PY, "src/hr8.py"], [PY, "src/locator8.py"],
                [PY, "src/novelty8.py", "index"], [PY, "src/novelty8.py", "audit"], [PY, "src/report8.py"],
                [PY, "src/finalize8.py"]],
}
ORDER = ["vendor", "prompts", "cputests", "commit0", "s0", "gputests", "s2", "commit1", "commit2", "s1", "s3", "s4",
         "commit3", "s3x", "analyse"]


@logger.catch(reraise=True)
def main() -> None:
    req = sys.argv[1] if len(sys.argv) > 1 else "all"
    stages = ORDER if req == "all" else req.split(",")
    labeller = None
    if any(s in ("s0", "s2", "s3", "s4", "s1") for s in stages):
        labeller = subprocess.Popen([PY, "src/label_daemon.py"], cwd=ROOT)
        logger.info(f"label daemon pid {labeller.pid}")
    try:
        for st in stages:
            for cmd in STEPS[st]:
                t0 = time.time()
                logger.info(f"[{st}] {' '.join(cmd[1:])}")
                r = subprocess.run(cmd, cwd=ROOT)
                if r.returncode != 0:
                    logger.error(f"[{st}] failed with exit code {r.returncode}")
                    raise SystemExit(r.returncode)
                logger.info(f"[{st}] done in {time.time() - t0:.0f}s")
    finally:
        if labeller is not None:
            (ROOT / "data" / "STOP_LABELLER").touch()
            labeller.wait(timeout=3600)


if __name__ == "__main__":
    main()
