#!/usr/bin/env python3
"""Predicting which bans a new model obeys -- held-out-family (gemma-3-4b-it) confirmation of Claim 3a.

Method (ours): a ban-free push screen. Eight fixed isotropic directions x alpha {1, 2} are written into the task-spec
states of the middle third of blocks (displacement-targeted, ban-free unit transferred from Qwen3-8B) on the
token-matched neutral twin prompt; a direction 'escapes' if it moves the model off its default algorithm without a
pass-rate cost (stage 1, N = 10) and survives a 20-sample confirmation with an exact binomial gate (N = 30).
E_t = share of escaping directions; MOVABLE = E_t > 0 predicts that the model will OBEY a ban of its default.
Baselines / rivals (same pipeline, same CRN slots): the un-pushed twin (zero dose), fresh-direction plan noise at
alpha 1 and 2, temperature 1.3, the novelty instruction (prompting ceiling), forced 'can' attempts, the twin's modal
share (how collapsed the default is), the opening-ladder margin; landing forecasts: push-landing, opening ladder,
association, AST proximity. All predictions are hash-committed (commit #2) before any ban prompt is built.

Pipeline (each stage is a module under src/; this driver runs them in order, resumable with --from):
  inputs     src/stage_inputs.py   stage inputs, sha256 checks, labeller re-check, dependency extraction
  screen     src/screen.py         iteration-3 screen file (shared protocol) + T5 reproduction
  qwen       src/qwen_ratio.py     Qwen3-8B ban-to-residual ratio r_Q (plain and outlier-excluded) + positive control
  gputests   src/gpu_tests.py      U1-U4, U6 on gemma
  probe      src/unit_probe.py     unit calibration probe (diagnostic; decided deviation D3)
  pilot      src/banfree.py pilot + commit1   pilot, default rule, cap rule, commit #1
  phaseA     src/banfree.py phaseA            twin N=50, escape stage 1, PN alpha 1/2, T 1.3 (CRN, B = 36)
  afterA     src/banfree.py all_after_A       confirmation top-up, association, opening ladder, novelty, 'can'
             (optional T 1.6 cell: src/banfree.py t16 --tasks <movable tasks>, run after the bans)
  commit2    src/commit2.py        grep audit + pre-ban predictions + frozen analysis hash (commit #2)
  bans       src/bans.py           1,500 modal-ban programs (+ extras) and the ban-derived unit
  audit      src/judge_audit.py    label audit, disagreement rates, novelty audit (OpenRouter, capped)
  analysis   src/final_analysis.py C3a, rivals, C3b, C1 prices, commit #3
  posthoc    src/posthoc_t2.py     POST HOC mechanism re-audit of T2 'bf_spfa' labels (array-Dijkstra), C3a re-run
  figures    src/figures.py
  tests      src/tests_cpu.py      CPU tests T1-T6
  rederive   audit/rederive.py     independent re-derivation of the headline numbers
  bookkeeping src/bookkeeping.py   timing summary and deviations log
  outputs    src/outputs.py        data/samples.jsonl, method_out.json (+ mini / preview)
The label worker (src/label_worker.py) runs in the background from 'pilot' to 'bans' and labels every raw row.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

from loguru import logger

ROOT = Path(__file__).resolve().parent
PY = sys.executable
STAGES = [
    ("inputs", ["src/stage_inputs.py"]),
    ("screen", ["src/screen.py"]),
    ("qwen", ["src/qwen_ratio.py"]),
    ("gputests", ["src/gpu_tests.py"]),
    ("probe", ["src/unit_probe.py"]),
    ("pilot", ["src/banfree.py", "pilot"]),
    ("commit1", ["src/banfree.py", "commit1"]),
    ("phaseA", ["src/banfree.py", "phaseA"]),
    ("afterA", ["src/banfree.py", "all_after_A"]),
    ("commit2", ["src/commit2.py"]),
    ("bans", ["src/bans.py"]),
    ("audit", ["src/judge_audit.py"]),
    ("analysis", ["src/final_analysis.py"]),
    ("posthoc", ["src/posthoc_t2.py"]),
    ("figures", ["src/figures.py"]),
    ("tests", ["src/tests_cpu.py"]),
    ("rederive", ["audit/rederive.py"]),
    ("bookkeeping", ["src/bookkeeping.py"]),
    ("outputs", ["src/outputs.py"]),
]
WAIT_BEFORE = {"commit1": ["raw_pilot.jsonl"], "afterA": ["raw_phaseA.jsonl"],
               "commit2": ["raw_phaseA.jsonl", "raw_phaseB.jsonl", "raw_novelty.jsonl", "raw_can.jsonl"],
               "audit": ["raw_bans.jsonl"], "analysis": ["raw_bans.jsonl"]}

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
(ROOT / "logs").mkdir(exist_ok=True)
logger.add(str(ROOT / "logs" / "method.log"), rotation="30 MB", level="DEBUG")


def run(cmd: list[str]) -> None:
    t0 = time.time()
    logger.info(f"running {' '.join(cmd)}")
    r = subprocess.run([PY] + cmd, cwd=ROOT)
    if r.returncode != 0:
        raise RuntimeError(f"stage failed ({r.returncode}): {' '.join(cmd)}")
    logger.info(f"done {' '.join(cmd)} in {time.time() - t0:.0f}s")


@logger.catch(reraise=True)
def main() -> None:
    names = [s for s, _ in STAGES]
    start = names[0]
    only = None
    if "--from" in sys.argv:
        start = sys.argv[sys.argv.index("--from") + 1]
    if "--only" in sys.argv:
        only = sys.argv[sys.argv.index("--only") + 1]
    labeller = None
    try:
        for name, cmd in STAGES[names.index(start):]:
            if only and name != only:
                continue
            if name == "pilot" and labeller is None:
                labeller = subprocess.Popen([PY, "src/label_worker.py"], cwd=ROOT,
                                            stdout=open(ROOT / "logs" / "label_worker.out", "a"),
                                            stderr=subprocess.STDOUT)
                logger.info(f"label worker started (pid {labeller.pid})")
            if name in WAIT_BEFORE and labeller is not None:
                run(["src/wait_labels.py"] + WAIT_BEFORE[name])
            run(cmd)
    finally:
        if labeller is not None:
            (ROOT / "data" / "STOP_LABELLER").touch()
            labeller.wait(timeout=600)
            (ROOT / "data" / "STOP_LABELLER").unlink(missing_ok=True)


if __name__ == "__main__":
    main()
