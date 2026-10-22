#!/usr/bin/env python3
"""Does FP8 rounding make random pushes work? -- entry point.

Re-runs iteration 4's 40 fixed random plan-site pushes (seeds 9101-9140) on Qwen3-8B under four numerics built from
ONE bf16 snapshot (a W8A8 = iteration-4 engine, b W8A16, c W16A8, d BF16 = full-precision baseline), on iteration 4's
CRN slots, twin prompts and absolute per-block/per-position displacement, and asks which numerics carry the escapes.

Steps (each resumable; GPU steps must run one at a time on a 16 GB card):
  setup      copy + sha256-verify every earlier-artifact input (src/setup_inputs.py)
  gates      CPU gates C1-C5 and the iteration-4 relabel (src/cpu_gates.py)
  commit0    hash-chained pre-registration (src/make_commit0.py)
  label      label worker, run in the background during generation (src/label_worker6.py)
  q1         weight set Q: unit tests + REPRO with byte identity vs exp22 + exp19 PN check (src/gpu_q.py --phase q1)
  b          weight set B: engines d and c (src/gpu_b.py)
  q2         weight set Q: engine b, diagnostics, B-sensitivity control (src/gpu_q.py --phase q2)
  analyse    E per engine, McNemar, verdicts, PN, REPRO, landings, relabel table (src/analysis.py)
  rederive   stdlib re-derivation + placebos (src/rederive.py)
  figures    figures/ (src/figures6.py)
  outputs    results bookkeeping + method_out.json (src/finalize6.py, src/outputs6.py)
  all        every step in order (labeller in the background)
Usage: uv run method.py <step> [extra args passed to the step]
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = str(ROOT / ".venv" / "bin" / "python") if (ROOT / ".venv" / "bin" / "python").exists() else sys.executable
STEPS = {
    "setup": ["src/setup_inputs.py"],
    "gates": ["src/cpu_gates.py"],
    "commit0": ["src/make_commit0.py"],
    "label": ["src/label_worker6.py"],
    "q1": ["src/gpu_q.py", "--phase", "q1"],
    "b": ["src/gpu_b.py"],
    "q2": ["src/gpu_q.py", "--phase", "q2"],
    "analyse": ["src/analysis.py"],
    "rederive": ["src/rederive.py"],
    "figures": ["src/figures6.py"],
    "outputs": ["src/finalize6.py"],
}
ORDER = ["setup", "gates", "commit0", "q1", "b", "q2", "analyse", "rederive", "figures", "outputs"]


def run(step: str, extra: list[str]) -> int:
    env = dict(os.environ, PYTHONUNBUFFERED="1")
    if step in ("b",):
        env["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
    cmd = [PY, *STEPS[step], *extra]
    if step == "rederive":
        cmd = [sys.executable, "-I", *STEPS[step]]
    print("+", " ".join(cmd), flush=True)
    rc = subprocess.call(cmd, cwd=ROOT, env=env)
    if step == "outputs" and rc == 0:
        rc = subprocess.call([PY, "src/outputs6.py"], cwd=ROOT, env=env)
    return rc


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in list(STEPS) + ["all"]:
        print(__doc__)
        sys.exit(1)
    step, extra = sys.argv[1], sys.argv[2:]
    if step != "all":
        sys.exit(run(step, extra))
    lab = subprocess.Popen([PY, "src/label_worker6.py"], cwd=ROOT, env=dict(os.environ, PYTHONUNBUFFERED="1"))
    try:
        for s in ORDER:
            if s == "analyse":
                (ROOT / "data" / "STOP_LABELLER").touch()
                lab.wait()
            rc = run(s, [])
            if rc != 0:
                print(f"step {s} failed with exit code {rc}")
                sys.exit(rc)
    finally:
        if lab.poll() is None:
            lab.terminate()


if __name__ == "__main__":
    main()
