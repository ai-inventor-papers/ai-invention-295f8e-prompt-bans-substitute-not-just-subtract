#!/usr/bin/env python3
"""Pipeline driver: Gemma base runner-up vs the tuned model's own tail and likelihood (iteration 6, step 5).

Runs every stage in order, each as its own process (one model on the GPU at a time); every stage is resumable (rows
whose row_id exists are skipped). `--from <stage>` resumes at a stage; `--only <stage>` runs one stage.
Stages:
  preflight    S0 inputs, dependency (10 datasets), bench sha256, seed audit, labeller re-check
  tests        S0 CPU tests T1-T12
  commit0      S0 protocol + frozen analysis -> commit #0
  it_session   S1 GPU tests + engine check + clean-state check; S5 forced programs; S4 twin top-up   (it, GPU)
  engine_eval  S1 engine-check evaluation against exp28's rows
  forced_topup S5 +20 forced programs for algorithms with < 10 kept                                  (it, GPU)
  qlik_select  S5 kept / scrubbed / re-labelled forced programs + fills; opening prefix            (CPU)
  ptfs         S2 few-shot pt top-up, stages A/B/C on correct-count support                         (pt, GPU)
  draft        forecast table draft (needed by the fp32 switch rule)                                 (CPU)
  qlik_score   S5 teacher-forced q_lik (bf16) + fp32 subsample and switch rule                       (it, GPU)
  audit_pt     S3 pt label audit (two judge families + tie-break; one revision round)               (OpenRouter)
  it_regate    S4 it style re-gate (30 programs)                                                     (OpenRouter)
  commit1      S6 forecasts + rescored old events + push plan + grep audit -> commit #1
  push6        S7 fresh FD (8 directions, alpha 2) + fresh PN + confirmations                       (it, GPU)
  final        S8-S9 events and the L1 contest (frozen analysis)
  novelty      S10 novelty audit                                                                     (OpenRouter)
  rederive     S11 independent stdlib re-derivation + placebos
  report       S11 bookkeeping (costs, timing, deviations, verdicts), figures, method_out.json
The label worker (src/label_worker.py) runs in the background throughout and is stopped at the end.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = str(ROOT / ".venv" / "bin" / "python")
STAGES = [
    ("preflight", ["src/stage_inputs6.py"]),
    ("tests", ["src/tests6.py"]),
    ("commit0", ["src/protocol6.py"]),
    ("it_session", ["src/gen6.py", "it_session"]),
    ("engine_eval", ["src/engine_check6.py"]),
    ("forced_topup", ["src/gen6.py", "forced_topup"]),
    ("qlik_select", ["src/qlik6.py", "select"]),
    ("ptfs", ["src/gen6.py", "ptfs"]),
    ("draft", ["src/forecasts6.py", "draft"]),
    ("qlik_score", ["src/qlik6.py", "score"]),
    ("audit_pt", ["src/audit6.py", "pt"]),
    ("it_regate", ["src/audit6.py", "it_regate"]),
    ("commit1", ["src/forecasts6.py", "commit1"]),
    ("push6", ["src/gen6.py", "push6"]),
    ("final", ["src/final6.py"]),
    ("novelty", ["src/audit6.py", "novelty"]),
    ("rederive", ["audit/rederive_l1.py"]),
    ("report", ["src/bookkeeping6.py"]),
]


def main() -> None:
    names = [s for s, _ in STAGES]
    start = names.index(sys.argv[sys.argv.index("--from") + 1]) if "--from" in sys.argv else 0
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    (ROOT / "logs").mkdir(exist_ok=True)
    stop = ROOT / "data" / "STOP_LABELLER"
    if stop.exists():
        stop.unlink()
    lw = subprocess.Popen([PY, "src/label_worker.py"], cwd=ROOT, stdout=open(ROOT / "logs" / "label_worker.out", "a"),
                          stderr=subprocess.STDOUT)
    try:
        for name, cmd in STAGES[start:]:
            if only and name != only:
                continue
            t0 = time.time()
            print(f"== {name}: {' '.join(cmd)}", flush=True)
            r = subprocess.run([PY] + cmd, cwd=ROOT)
            print(f"== {name} exit {r.returncode} in {time.time() - t0:.0f}s", flush=True)
            if r.returncode != 0:
                sys.exit(r.returncode)
    finally:
        stop.touch()
        try:
            lw.wait(timeout=600)
        except subprocess.TimeoutExpired:
            lw.terminate()


if __name__ == "__main__":
    main()
