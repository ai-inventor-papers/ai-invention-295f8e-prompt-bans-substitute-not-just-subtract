#!/usr/bin/env python3
"""Orchestrator: do prompt-level algorithm bans on Qwen3-8B pick a specific substitute or move mass along a generic
ladder? (FRLP output-space screen, two path-search tasks; descriptive.)

Stages (each resumes from what is on disk; GPU stages run in their own processes so vLLM and HF never coexist):
  inputs      step 0.1  copy iteration-1 inputs (paths.local.json or FRLP_EXP1/FRLP_EXP4/FRLP_DS env vars)
  recheck     step 0.2  canonical labeller on the gold set and the 22 references
  events      step 0.3  FRLP gate events from exp1 samples (hash-committed)
  prompts     step 0.4  prompts_v2.json (hash-committed before GPU work)
  generate    step 1    vLLM: forced programs (adaptive rounds) + free-form answers   [GPU]
  select      step 2    scrub / verify / select programs, association profiles
  score       step 3    HF teacher-forced scoring queue Q1..Q9 (validation, cut rule)  [GPU]
  gate        step 5    FRLP validity gate (needs Q1 + Q2)
  analyse     steps 4,6,7  cells, ESS, coverage, C1 share/aim (both references), sensitivity, secondary
  freeze      step 8    frozen profiles + code hashes for the confirmation bench
  outputs     step 9    method_out.json + figures
  audit       T6        independent re-derivation from the raw parquet files
  all         every stage in order

The proposed method is the X-specific substitution account (residual aimed at the prime-and-veto or association
profile); the baseline/rival is the generic ladder (the external profile from nonce bans, matched-norm random
prompt-band edits and a novelty instruction), with uniform and neutral/mention-twin references.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from loguru import logger

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
PY = sys.executable

STAGES = {
    "inputs": ["copy_inputs.py"],
    "recheck": ["labelling.py"],
    "events": ["gate_events.py"],
    "prompts": ["prompts_v2.py"],
    "generate": ["gen_vllm.py", "--max-num-seqs", "48"],
    "select": ["select_programs.py"],
    "score": ["frlp_score.py", "--deadline", "05:35", "--precision", "tf32"],
    "gate": ["gate.py"],
    "analyse_misc": ["analysis_misc.py"],
    "analyse": ["c1.py"],
    "freeze": ["freeze.py"],
    "outputs": ["outputs.py"],
    "audit": [str(ROOT / "audit" / "rederive.py")],
}
ORDER = ["inputs", "recheck", "events", "prompts", "generate", "select", "score", "gate", "analyse_misc", "analyse",
         "freeze", "outputs", "audit"]


def run(stage: str, extra: list[str]) -> None:
    cmd = STAGES[stage]
    script = cmd[0] if cmd[0].startswith("/") else str(SRC / cmd[0])
    full = [PY, script] + cmd[1:] + extra
    logger.info(f"stage {stage}: {' '.join(Path(c).name if c.startswith('/') else c for c in full)}")
    r = subprocess.run(full, cwd=str(SRC))
    if r.returncode != 0:
        raise SystemExit(f"stage {stage} failed with exit code {r.returncode}")


@logger.catch(reraise=True)
def main() -> None:
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    (ROOT / "logs").mkdir(exist_ok=True)
    logger.add(str(ROOT / "logs" / "method.log"), rotation="30 MB", level="DEBUG")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stage", choices=ORDER + ["all"])
    ap.add_argument("extra", nargs=argparse.REMAINDER, help="extra arguments passed to the stage script")
    a = ap.parse_args()
    for st in (ORDER if a.stage == "all" else [a.stage]):
        run(st, a.extra if a.stage != "all" else [])


if __name__ == "__main__":
    main()
