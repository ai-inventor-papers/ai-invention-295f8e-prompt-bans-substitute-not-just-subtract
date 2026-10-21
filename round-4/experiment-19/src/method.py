#!/usr/bin/env python3
"""Pricing plan noise against temperature -- orchestrator.

Fresh per-sample plan noise (PN: one isotropic unit direction per sample, displacement-targeted at the task-spec
positions of blocks 12-23 during prefill, alpha in ban units) is priced against temperature, top-k, the nonce ban,
the novelty instruction, the semantic seed, min-p, verbalized sampling and reused signature vetoes, by correct-only
Hill-1 rarefied at depth 25 on each knob's randomisation hull (H5, P15, P20), with exact common random numbers.

Stages (each resumable; run in this order):
  prompts   render every prompt, assert identical task-spec ids across arms, R2 alias audit   (CPU)
  inputs    input hashes vs bench/commitment.json, labeller re-check (13 bench tasks + exp8 suite)  (CPU)
  screen    screen.json from the iteration-3 rows, reused veto rows, dependency-dataset usage (CPU)
  gpu       GPU unit tests U1-U6, R2 ban-free unit, engine check, stage 10, [waits for the commit],
            stage 100, timing rule, full priority queue                               (GPU, background)
  label     label worker following data/samples_raw.jsonl (run concurrently with gpu)   (CPU, background)
  label_ec  label worker for the engine-check rows                                      (CPU)
  commit    decision rule + screen forecast + analysis-code hashes into the sha256 chain (CPU)
  audit     novelty audit of every correct 'other' program (OpenRouter)                 (API)
  analyze   merge, knob rows, hull prices, bootstraps, C1 + sensitivities, descriptive  (CPU)
  validity  label-validity audit of PN and each task's best NA knob (OpenRouter)        (API)
  report    figures, method_out.json (+ mini/preview), independent re-derivation        (CPU)

Usage: .venv/bin/python method.py <stage> [--deadline-utc ISO]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from loguru import logger

ROOT = Path(__file__).resolve().parent
PY = sys.executable


def run(args: list[str], cwd: Path = ROOT) -> None:
    logger.info(f"$ {' '.join(args)}")
    subprocess.run([PY] + args, cwd=cwd, check=True)


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["prompts", "inputs", "screen", "gpu", "label", "label_ec", "commit", "audit",
                                      "analyze", "validity", "report", "all_cpu_after_gpu"])
    ap.add_argument("--deadline-utc", default="2099-01-01T00:00:00Z")
    a = ap.parse_args()
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    logger.add(str(ROOT / "logs" / "method.log"), rotation="30 MB", level="DEBUG")
    s = a.stage
    if s == "prompts":
        run(["src/prompts_v4.py"])
    elif s == "inputs":
        run(["src/s0_checks.py"])
    elif s == "screen":
        run(["src/screen.py"])
        run(["src/dep_usage.py"])
    elif s == "gpu":
        run(["src/gpu_stage.py", "--deadline-utc", a.deadline_utc])
    elif s == "label":
        run(["src/label_worker_v4.py", "--raw", "data/samples_raw.jsonl", "--out", "data/labels.jsonl",
             "--follow-until", "results/gpu_done.flag", "--name", "label_main"])
    elif s == "label_ec":
        run(["src/label_worker_v4.py", "--raw", "data/engine_check_raw.jsonl", "--out",
             "data/engine_check_labels.jsonl", "--name", "label_ec"])
        run(["-m", "analysis.engine_check"], cwd=ROOT / "src")
    elif s == "commit":
        run(["src/prereg.py"])
    elif s == "audit":
        run(["-m", "analysis.run_all", "--skip-boot"], cwd=ROOT / "src")  # merge samples first
        run(["src/audit_llm.py", "novelty"])
    elif s == "analyze":
        run(["-m", "analysis.run_all"], cwd=ROOT / "src")
        run(["-m", "analysis.descriptive"], cwd=ROOT / "src")
    elif s == "validity":
        c1 = json.loads((ROOT / "results" / "c1.json").read_text())["primary"]["per_task"]
        from_cls = {"TEMP": "T1.3,T1.6", "TOPK10": "TOPK10", "NONCE": "NONCE", "NOVELTY": "NOVELTY",
                    "SEMSEED": "SEMSEED", "VETO_1SHOT": "VETO_1SHOT", "VETO_PERSIST": "VETO_PERSIST",
                    "VETO_ITER": "VETO_ITER1,VETO_ITER2,VETO_ITER3"}
        best = {t: from_cls[d["best_na"]] for t, d in c1.items() if d.get("best_na") in from_cls}
        run(["src/audit_llm.py", "validity", "--best-na", json.dumps(best)])
    elif s == "report":
        run(["src/figures.py"])
        run(["src/outputs.py"])
        run(["audit/rederive.py"])
        run(["src/outputs.py"])  # again, so method_out.json carries the re-derivation
    elif s == "all_cpu_after_gpu":
        for st in ("audit", "analyze", "validity", "report"):
            subprocess.run([PY, str(ROOT / "method.py"), st], cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
