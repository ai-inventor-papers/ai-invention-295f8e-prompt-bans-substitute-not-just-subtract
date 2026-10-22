#!/usr/bin/env python3
"""Panel II (iteration 6): where nudged code lands -- base runner-up vs the tuned model's own tail and likelihood
ranking (Qwen3-8B vs Qwen3-8B-Base). Entry point.

    uv run method.py                 # CPU final stage (default): events, frozen analysis, audits, figures, outputs
    uv run method.py --stage gpu     # print the GPU pipeline commands, in the order they were run

The method (base-model forecasts r_u / q_base) and its baselines (the tuned model's own twin tail t_u / q_tail, its
likelihood ranking qlik_top1 / q_lik, association answers and uniform) are computed side by side by the same code
(src/quantities6.py) and scored on the same landing events by the frozen analysis (analysis/pool_l1.py)."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from loguru import logger

ROOT = Path(__file__).resolve().parent
PY = sys.executable
GPU_STEPS = [
    "python src/extract_sources.py                       # rows of the dependency art_j3Rm_lr2nzR6",
    "python src/protocol6.py                             # commit #0 (before any sample)",
    "python src/unitbuild.py II1,II2,...,II8             # gate stage (i)",
    "python -c 'import requests6 ...'                    # vLLM request files (src/requests6.py builders)",
    ".venv_vllm/bin/python src/vllm_gen.py --model <snapshot> --requests data/vllm_req/<job>.jsonl --out data/vllm_out/<job>.jsonl",
    "python src/requests6.py ingest <job> [--model-tag base]",
    "python src/label5.py                                # label daemon (runtime + AST labellers, sandboxed tests)",
    "python src/gate2.py II1,...                         # gate stage (ii): gold set, two judge families",
    "python src/m_screen.py                              # M-screen signs from iteration-5 data",
    "python src/gpu6.py --plan data/gpu_plan_v3.json     # HF daemon: twin CRN slots, q_lik, ESC/PN/GTN",
    "python src/quantities6.py <units>                   # per-unit forecasts + hash-chained commit (before nudges)",
    "python src/base_audit6.py <units> ; python src/novelty6.py ; python src/gpu_tests6.py",
]


def run(cmd: list[str]) -> None:
    logger.info("$ " + " ".join(cmd))
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        logger.error(r.stderr[-2000:])
        raise RuntimeError(f"step failed: {' '.join(cmd)}")
    logger.info(r.stdout[-800:])


@logger.catch(reraise=True)
def main() -> None:
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    (ROOT / "logs").mkdir(exist_ok=True)
    logger.add(str(ROOT / "logs" / "method.log"), rotation="30 MB", level="DEBUG")
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="final", choices=["final", "gpu"])
    a = ap.parse_args()
    if a.stage == "gpu":
        print("\n".join(GPU_STEPS))
        return
    run([PY, "src/outputs6.py"])
    run([PY, "-I", "audit/commit_order.py"])
    run([PY, "-I", "audit/rederive.py"])
    run([PY, "-I", "audit/rederive_headlines.py"])
    run([PY, "src/cpu_checks6.py"])
    run([PY, "src/readme6.py"])
    logger.info("final stage complete: method_out.json, landing_events.json, units.json, results/, figures/")


if __name__ == "__main__":
    main()
