#!/usr/bin/env python3
"""Claim E: does Gemma's base model (gemma-3-4b-pt) predict which tasks ban-free activation nudges move in the
instruction-tuned model (gemma-3-4b-it)? A second-family REPLICATION of the narrowed-repertoire account.

Method (ours): beta_u = the pt model's share of non-default catalogue algorithms among its correct programs on the SAME
token ids as the it twin (pt under the it chat template; pt plain completion as the pre-declared fallback/pool),
predicting E_u = the share of 16 fresh isotropic directions (x alpha 1, 2) whose displacement-targeted push at the
task-spec states of blocks 11-22 moves the it model off its default without a pass-rate cost (stage 1 N=10, exact
binomial confirmation at N=30). The pt runner-up r_u predicts where the escapes land. A pt->it transplant of the
task-spec states (lambda 1) tests sufficiency on base-diverse tasks.
Baselines / controls (same engine, same CRN slots): the un-pushed it twin (zero dose); per-sample plan noise; rivals
for E (prompting ceiling = novelty instruction, twin modal share, opening margin, merit gap); rivals for landings
(iteration-4 association and AST proximity forecasts); transplant controls: matched-norm random displacement in the
non-massive subspace (RND), cross-task displacement (XT), read-position transplant (RP), base-collapsed tasks (S_C).
Predictions, thresholds and analysis code are hash-chained (commitments.log) before the first push sample.

Pipeline (src/ modules; `--from <stage>` resumes; the label worker runs in the background from 'engine_check'):
  inputs        src/stage_inputs.py --recheck  stage + sha256 inputs, bench vs ITER2 commitment, dependency (10 sets),
                                               seed audit, labeller re-check on gold + references (re-gate 5a)
  it_tests      src/gen.py it_tests            GPU U1-U4, U9 (memory), U5 reference logits
  commit0       src/commit0.py                 protocol_E.json + analysis_E.py + SHA256SUMS + hardware.json
  engine_check  src/gen.py engine_check        exp23 slot keys / direction 9003 / cap 640 (positive control)
  engine_eval   src/engine_check_eval.py       per-slot agreement + JS vs template-resampling null (gates stage 1)
  tests_cpu     src/tests_cpu.py               T1-T8 (T2 rule references, exp23 structural matches, extraction, ...)
  stage1_it     src/gen.py stage1_it           it twin N=50, novelty N=30, clean it states
  stage1_pt     src/gen.py stage1_pt           U5; pt-chat N=100, pt plain N=50, pt states
  regate        src/regate.py                  re-gate sample (2 judge families), structural audit, iteration-4 rescoring
  draft         src/predictors.py draft        D_u, r_u (for the opening ladder)
  ladder        src/gen.py ladder              opening-margin rival (teacher forcing)
  commit1       src/predictors.py commit1      predictor table, S_T, S_C, M, donors, grep audit -> hash chain
  amend_M       src/amend_M.py                 commit #1b: massive set M* (5 channels) before any transplant sample
  stage2        src/gen.py stage2_pipelined    fresh push population + plan noise; confirmation top-up per task
  stage3_valid  src/gen.py stage3_valid        U6/U7 + T at N=10 per S_T task (validity switch)
  decide        src/transplant_decide.py       lambda 1 or 0.5 (validity only)
  stage3        src/gen.py stage3              T, RND, XT, RP on S_T; T on S_C
  rejudge       src/rejudge_disputed.py        re-judge rows left 'disputed' by judge rate limits (sensitivity only)
  novelty       src/novelty_audit.py           novelty audit + pt label audit (OpenRouter, capped)
  analysis      src/final_analysis.py          frozen analysis: escape, PN, E-A1, E-A2, transplant
  bookkeeping   src/bookkeeping.py             timing, costs, deviations
  outputs       src/outputs.py                 data/samples.jsonl, method_out.json
  rederive      audit/rederive.py              independent re-derivation + placebos
  rederive2     audit/rederive_headlines.py    second-code-path re-derivation of the headline numbers + placebos
  figures       src/figures.py                 F1-F6
  report        src/report.py                  results/report.md (the README's result tables)
What was actually run: the same stages, driven by src/chain_after_pt.sh, src/chain_stage3.sh and src/chain_final.sh
(see README 'How to run').
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
    ("inputs", ["src/stage_inputs.py", "--recheck"]),
    ("it_tests", ["src/gen.py", "it_tests"]),
    ("commit0", ["src/commit0.py"]),
    ("engine_check", ["src/gen.py", "engine_check"]),
    ("engine_eval", ["src/engine_check_eval.py"]),
    ("tests_cpu", ["src/tests_cpu.py"]),
    ("stage1_it", ["src/gen.py", "stage1_it"]),
    ("stage1_pt", ["src/gen.py", "stage1_pt"]),
    ("regate", ["src/regate.py"]),
    ("draft", ["src/predictors.py", "draft"]),
    ("ladder", ["src/gen.py", "ladder"]),
    ("commit1", ["src/predictors.py", "commit1"]),
    ("amend_M", ["src/amend_M.py"]),
    ("stage2", ["src/gen.py", "stage2_pipelined"]),
    ("stage3_valid", ["src/gen.py", "stage3_valid"]),
    ("decide", ["src/transplant_decide.py"]),
    ("stage3", ["src/gen.py", "stage3"]),
    ("rejudge", ["src/rejudge_disputed.py"]),
    ("novelty", ["src/novelty_audit.py"]),
    ("analysis", ["src/final_analysis.py"]),
    ("bookkeeping", ["src/bookkeeping.py"]),
    ("outputs", ["src/outputs.py"]),
    ("rederive", ["audit/rederive.py"]),
    ("rederive2", ["audit/rederive_headlines.py"]),
    ("figures", ["src/figures.py"]),
    ("report", ["src/report.py"]),
]
WAIT_BEFORE = {"engine_eval": ["raw_engine_check.jsonl"], "regate": ["raw_twin.jsonl", "raw_novelty.jsonl",
                                                                     "raw_ptchat.jsonl", "raw_ptplain.jsonl"],
               "decide": ["raw_transplant_valid.jsonl"], "novelty": ["raw_transplant.jsonl", "raw_push.jsonl",
                                                                      "raw_confirm.jsonl"]}

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
    start = sys.argv[sys.argv.index("--from") + 1] if "--from" in sys.argv else names[0]
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    labeller = None
    try:
        for name, cmd in STAGES[names.index(start):]:
            if only and name != only:
                continue
            if name == "engine_check" and labeller is None:
                labeller = subprocess.Popen([PY, "src/label_worker.py"], cwd=ROOT,
                                            stdout=open(ROOT / "logs" / "label_worker.out", "a"),
                                            stderr=subprocess.STDOUT)
                logger.info(f"label worker started (pid {labeller.pid})")
            if name in WAIT_BEFORE and labeller is not None:
                run(["src/wait_labels.py"] + [f for f in WAIT_BEFORE[name] if (ROOT / "data" / f).exists()])
            run(cmd)
    finally:
        if labeller is not None:
            (ROOT / "data" / "STOP_LABELLER").touch()
            labeller.wait(timeout=900)
            (ROOT / "data" / "STOP_LABELLER").unlink(missing_ok=True)


if __name__ == "__main__":
    main()
