#!/usr/bin/env python3
"""Stage CLI of the iteration-5 'transplanting the base model's plan' artifact (resumable: every stage skips the
rows / files it has already written; GPU stages hold one 8B model at a time).

  .venv/bin/python method.py --stage 0   prompts (src/prompts5.py), Stage-0 checks (src/s0.py), CPU unit tests
  .venv/bin/python method.py --stage 1   base repertoire with vLLM (src/base_vllm.py, .venv_vllm) + label worker
  .venv/bin/python method.py --stage 2   instruct engine check / twin / states (src/gpu5.py instr1), COMMIT #0
  .venv/bin/python method.py --stage 3   base audit (src/audit5.py base), COMMIT #1 (src/commits5.py 1)
  .venv/bin/python method.py --stage 4   base states + Stage 6 reverse interchange (src/gpu5.py base1)
  .venv/bin/python method.py --stage 5   Stage 3 selection, Stage 5 push, COMMIT #2, Stage 4 confirmation
                                         (src/gpu5.py instr2)
  .venv/bin/python method.py --stage 8   analyses, geometry, novelty audit, figures, outputs, re-derivation
The label worker (src/labels5.py --follow) must run beside stages 1-5; `--stage all` runs everything in order.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = str(ROOT / ".venv" / "bin" / "python")
PYV = str(ROOT / ".venv_vllm" / "bin" / "python")
SRC = ROOT / "src"


def run(cmd: list[str]) -> None:
    print(f"$ {' '.join(cmd)}", flush=True)
    t0 = time.time()
    subprocess.run(cmd, cwd=SRC, check=True)
    print(f"  done in {time.time() - t0:.0f}s", flush=True)


def start_labeller() -> subprocess.Popen:
    return subprocess.Popen([PY, "labels5.py", "--follow"], cwd=SRC,
                            stdout=open(ROOT / "logs" / "labels5.out", "a"), stderr=subprocess.STDOUT)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="all", choices=["0", "1", "2", "3", "4", "5", "8", "all"])
    a = ap.parse_args()
    st = a.stage
    lab = None
    if st in ("1", "2", "3", "4", "5", "all"):
        lab = start_labeller()
    try:
        if st in ("0", "all"):
            run([PY, "prompts5.py"])
            run([PY, "s0.py"])
            run([PY, str(ROOT / "tests" / "test_cpu.py")])
        if st in ("1", "all"):
            run([PYV, "base_vllm.py", "--stage", "all"])
        if st in ("2", "all"):
            run([PY, "gpu5.py", "instr1"])
            run([PY, "commits5.py", "0"])
        if st in ("3", "all"):
            run([PY, "audit5.py", "base"])
            run([PY, "commits5.py", "1"])
        if st in ("4", "all"):
            run([PY, "gpu5.py", "base1", "--wait-min", "5"])
        if st in ("5", "all"):
            run([PY, "gpu5.py", "instr2", "--wait-min", "40"])
        if st in ("8", "all"):
            (ROOT / "data" / "labels_stop.flag").write_text("stop")
            run([PY, "analysis_final.py"])
            run([PY, "geometry5.py", "all"])
            run([PY, "audit5.py", "novelty"])
            run([PY, "analysis_final.py"])
            run([PY, "figures5.py"])
            run([PY, "outputs5.py"])
            run([PY, str(ROOT / "audit" / "rederive.py")])
    finally:
        if lab is not None and st != "all":
            lab.terminate()


if __name__ == "__main__":
    sys.exit(main())
