#!/usr/bin/env python3
"""Panel I of iteration 6 (Step 3; Claim L primary, M and K secondary) on Qwen3-8B / Qwen3-8B-Base, W16A16 bf16.

The method (the base model's forecast of where content-free nudges land: q_base and its runner-up r_u) and its
baselines (the tuned model's own rivals q_tail / t_u and q_lik, chance = uniform over the surviving algorithms, and the
association forecast) are computed in one pipeline from identical chat-templated token ids, committed by sha256
before each unit's first nudge row, and scored on the same landing events. Every stage is a resumable script:

  prompts      src/extract_sources6.py, src/build_prompts6.py          cards, prompts, grep audit, commit #0
  vllm_inst    src/vllm6.py --phase instruct                            forced / twin / association rows (vLLM bf16)
  build        src/unitbuild6.py                                        tests, oracles, references, labellers (stage i)
  vllm_base    src/vllm6.py --phase base                                base chat / plain / intent rows
  label        src/label6.py                                            runtime tracer + AST labels (+ judges later)
  gate         src/gate6.py [--revision], --post                        gate (ii), adjudication, base audits
  forced       src/forced6.py                                           verified, name-scrubbed forced programs
  hf           src/hf6.py all                                           B probe, GPU tests, HF twin, q_lik, nudges
  commit       src/instruments6.py commit / enrol                       per-unit commits and the enrolment hash
  bint         src/bint6.py                                             BINT knob rows (vLLM)
  analysis     analysis/build_events.py, pool_l1.py, analysis/secondary.py, analysis/novelty.py,
               analysis/figures.py, analysis/outputs.py, audit/rederive.py, audit/commit_order.py, tests/test_cpu.py
Usage: uv run method.py                  # CPU-only final stage (analysis, audits, figures, outputs)
       uv run method.py --stage all      # every stage in order (needs one >= 20 GB GPU and OPENROUTER_* variables)
       uv run method.py --stage <name>   # one stage
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from loguru import logger

ROOT = Path(__file__).resolve().parent
PY = sys.executable
UNITS = "I1,I2,I3,I4,I5,I6,I7,I8,I9,I10"

STAGES: dict[str, list[list[str]]] = {
    "prompts": [["src/extract_sources6.py"], ["src/build_prompts6.py"]],
    "vllm_inst": [["src/vllm6.py", "--phase", "instruct", "--units", UNITS, "--deadline-min", "70"]],
    "build": [["src/unitbuild6.py", UNITS]],
    "vllm_base": [["src/vllm6.py", "--phase", "base", "--units", UNITS, "--deadline-min", "75"]],
    "label": [["src/label6.py"]],
    "gate": [["src/gate6.py", UNITS], ["src/gate6.py", UNITS, "--post"]],
    "forced": [["src/forced6.py", UNITS]],
    "hf": [["src/hf6.py", "all", "--units", UNITS, "--stop-at-utc", "2026-10-22T00:25:00Z"]],
    "commit": [["src/instruments6.py", "commit", UNITS], ["src/instruments6.py", "enrol", UNITS, "--final"]],
    "bint": [["src/bint6.py", "--units", UNITS], ["src/label6.py"]],
    "analysis": [["analysis/build_events.py"],
                 ["pool_l1.py", "--events", "landing_events.json", "--units", "units.json", "--out",
                  "results/pool_l1_panelI.json"],
                 ["analysis/secondary.py"], ["analysis/novelty.py"], ["analysis/label_qa.py"], ["analysis/harness_check.py"],
                 ["analysis/figures.py"], ["analysis/outputs.py"], ["analysis/summary.py"], ["audit/rederive.py"], ["audit/rederive_headlines.py"],
                 ["audit/commit_order.py"], ["tests/test_cpu.py"]],
}
ORDER = ["prompts", "vllm_inst", "build", "vllm_base", "label", "gate", "forced", "hf", "commit", "bint", "analysis"]


def run(stage: str) -> None:
    for cmd in STAGES[stage]:
        logger.info(f"[{stage}] {' '.join(cmd)}")
        r = subprocess.run([PY, *cmd], cwd=ROOT)
        if r.returncode != 0:
            raise RuntimeError(f"stage {stage} failed: {' '.join(cmd)} (exit {r.returncode})")


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="analysis", choices=ORDER + ["all"])
    a = ap.parse_args()
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    (ROOT / "logs").mkdir(exist_ok=True)
    logger.add(str(ROOT / "logs" / "method.log"), rotation="30 MB", level="DEBUG")
    stages = ORDER if a.stage == "all" else [a.stage]
    for s in stages:
        run(s)
    logger.info(f"done: {stages}")


if __name__ == "__main__":
    main()
