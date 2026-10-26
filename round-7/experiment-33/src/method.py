#!/usr/bin/env python3
"""Iteration 7 entry point: DAS localisation of the planned algorithm in bf16 Qwen3-8B, validated by generation.

Runs every stage in the order it was run (each stage is resumable; GPU stages skip finished sample ids / files):
  prompts   src/prompts7.py                 all prompt records + CPU tests (prompts/prompts7.jsonl)
  commit0   src/prereg7.py                  commit #0 (design, thresholds, predictions; hash chain)
  label     src/label7.py (background)      frozen labellers follow data/samples_raw.jsonl -> data/labels.jsonl
  utest     src/run_gpu7.py utest           U1-U8 (results/unit_tests_gpu.json)
  s0        src/run_gpu7.py s0              Stage 0 sampling T2, T10, T03
  targets   stages_b7.stage_targets         kept Y, ban landing set, target programs (commit1_<task>_v2)
  profile   src/run_gpu7.py profile         layer profile + generation confirmation -> site (commit1b_<task>)
  fit       src/run_gpu7.py fit/fitlight    committed contrastive DAS fits + controls (commit2_<task>)
  fitly     src/run_gpu7.py fitly           amendment 1: bounded LME_Y maps (MAIN_LY, PERM_LY, RPOS_LY)
  tfeval    src/run_gpu7.py tfeval          held-out teacher-forced evaluation
  gen       src/run_gpu7.py gen,genpilot    held-out generation (MAIN_LY full cell set; MAIN 10-slot pilot)
  after     scripts/run_gpu_after.sh        R sweep + M states (T2), third task T03, random-init network (T2)
  report    src/report7.py                  every analysis + figures (results/*.json, figures/)
  novelty   src/novelty6.py                 two-family novelty audit of correct 'other' programs
  outputs   src/outputs7.py                 method_out.json (+ full_/mini_/preview_), schema-validated
  audit     audit/rederive.py               independent stdlib re-derivation + placebo tests

usage: .venv/bin/python method.py [stage ...]   (no argument = the whole pipeline)
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = str(ROOT / ".venv" / "bin" / "python")


def run(*args: str) -> None:
    print("+", " ".join(args), flush=True)
    subprocess.run(list(args), cwd=ROOT, check=True)


STAGES = {
    "prompts": lambda: run(PY, "src/prompts7.py"),
    "commit0": lambda: run(PY, "src/prereg7.py"),
    "utest": lambda: run(PY, "src/run_gpu7.py", "utest", "--tasks", "T2"),
    "s0": lambda: run(PY, "src/run_gpu7.py", "s0", "--tasks", "T2,T10,T03"),
    "targets": lambda: run(PY, "-c", "import sys; sys.path.insert(0,'src'); from cfg import setup_logging; "
                                     "setup_logging('targets7'); from prompts7 import load_tokenizer; import stages_b7 "
                                     "as B; tok=load_tokenizer(); [B.stage_targets(t, tok) for t in "
                                     "('T2','T10','T03')]"),
    "profile": lambda: run(PY, "src/run_gpu7.py", "profile", "--tasks", "T2,T10"),
    "fit": lambda: (run(PY, "src/run_gpu7.py", "fit", "--tasks", "T2"),
                    run(PY, "src/run_gpu7.py", "fitlight", "--tasks", "T10")),
    "fitly": lambda: run(PY, "src/run_gpu7.py", "fitly,tfeval", "--tasks", "T2,T10"),
    "gen": lambda: run(PY, "src/run_gpu7.py", "gen,genpilot", "--tasks", "T2,T10"),
    "after": lambda: run("bash", "scripts/run_gpu_after.sh"),
    "report": lambda: run(PY, "src/report7.py"),
    "novelty": lambda: run(PY, "src/novelty6.py"),
    "outputs": lambda: run(PY, "src/outputs7.py"),
    "audit": lambda: run("python3", "audit/rederive.py"),
}


def main() -> None:
    want = sys.argv[1:] or list(STAGES)
    label = None
    if any(s in want for s in ("utest", "s0", "profile", "fit", "fitly", "gen", "after")):
        label = subprocess.Popen([PY, "src/label7.py"], cwd=ROOT)
    try:
        for s in want:
            STAGES[s]()
    finally:
        if label is not None:
            (ROOT / "results" / "gpu_all_done.flag").touch()
            label.wait()


if __name__ == "__main__":
    main()
