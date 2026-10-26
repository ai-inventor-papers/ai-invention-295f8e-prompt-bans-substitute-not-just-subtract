#!/usr/bin/env python3
"""Step K of iteration 7: why random nudges stopped changing the algorithm.

Entry point. Every step is a module in src/ (run in its own process; the GPU steps load one 8B model at a time) and is
resumable: generation is keyed by <task>|<template>|<arm>|<sample_id>, labels by the same key, and the commits only
append to the hash chain when their file is missing.

  setup      copy and sha256-verify every earlier-artifact input into inputs/ and vendor/   (src/setup_inputs.py)
  gates      CPU gates G1-G5 -> results/cpu_gates.json                                      (src/s3_prices.py g5, src/cpu_gates.py)
  label      start the label worker in the background (follows data/raw/*.jsonl)          (src/label_k.py)
  gpu0       hardware record, memory probe, GPU unit tests U1-U6, S0 twins                 (src/gen_k.py tests s0)
  commit1    COMMIT #1: design table, units, seeds, rules, predictions, analysis code hash (src/make_commits.py)
  gpu1       S1 2x2 (anchors first) + D5 + S2 profiles                                     (src/gen_k.py s1 d5 s2)
  commit2    COMMIT #2: D* rule applied to the labelled S1 rows, S3 predictions and rules  (src/make_commits.py)
  gpu2       S3 plan-noise cells at D* on T03, T05, T1                                      (src/gen_k.py s3pn)
  knobs      base-model intents, exp27 knob rows relabelled, knob check, reruns            (src/knobs_k.py)
  units      dose units in activation coordinates for the figures                          (src/dump_units.py)
  e1         exploratory dose sweep of the ban-free unit (committed before its first row)  (src/e1_sweep.py)
  analyse    anchors, S1 2x2, D5 split, mediation, S2, D*, E1                               (src/analysis_k.py all)
  prices     S3 hull prices + 2,000 bootstraps, readings, re-tag                            (src/s3_prices.py prices / retag)
  novelty    nearest-known search over the dependency corpus + two-family judge audit      (src/novelty_k.py)
  geometry   exploratory E2: downstream displacement direction vs size                     (src/geometry_k.py)
  figures    F1-F7 and E1 in figures/                                                       (src/figures_k.py)
  report     engine check, timing, costs, deviations, commit-order audit                   (src/report_k.py)
  rederive   independent stdlib re-derivation with placebos                                 (audit/rederive.py)
  outputs    method_out.json (+ full/mini/preview) in the exp_gen_sol_out schema           (src/outputs_k.py)
  all        every step above in order

usage: uv run method.py <step> [<step> ...]      (or .venv/bin/python method.py ...)
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

from loguru import logger

ROOT = Path(__file__).resolve().parent
PY = str(ROOT / ".venv" / "bin" / "python") if (ROOT / ".venv" / "bin" / "python").exists() else sys.executable
LOGS = ROOT / "logs"
LOGS.mkdir(exist_ok=True)
logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(str(LOGS / "method.log"), rotation="30 MB", level="DEBUG")

STEPS: dict[str, list[list[str]]] = {
    "setup": [["src/setup_inputs.py"]],
    "gates": [["src/s3_prices.py", "g5"], ["src/cpu_gates.py"]],
    "gpu0": [["src/gen_k.py", "tests", "s0"]],
    "commit1": [["src/make_commits.py", "commit1"]],
    "gpu1": [["src/gen_k.py", "s1", "d5", "s2"]],
    "commit2": [["src/make_commits.py", "commit2"]],
    "gpu2": [["src/gen_k.py", "s3pn"]],
    "knobs": [["src/knobs_k.py", "base,reuse,check,verdict,rerun"]],
    "units": [["src/dump_units.py"]],
    "e1": [["src/e1_sweep.py"]],
    "analyse": [["src/analysis_k.py", "all"]],
    "prices": [["src/s3_prices.py", "prices"], ["src/s3_prices.py", "retag"]],
    "novelty": [["src/novelty_k.py"], ["src/novelty_k.py", "--manual-only"]],
    "geometry": [["src/geometry_k.py"]],
    "figures": [["src/figures_k.py"]],
    "report": [["src/report_k.py"]],
    "rederive": [["audit/rederive.py"]],
    "outputs": [["src/outputs_k.py"]],
}
ORDER = ["setup", "gates", "label", "gpu0", "commit1", "gpu1", "commit2", "gpu2", "knobs", "units", "e1", "analyse",
         "prices", "novelty", "geometry", "figures", "report", "rederive", "outputs"]
SKIP_IF_EXISTS = {"commit1": ROOT / "predictions" / "commit1.json", "commit2": ROOT / "predictions" / "commit2.json"}


def run(cmd: list[str]) -> None:
    t0 = time.time()
    logger.info(f"run {' '.join(cmd)}")
    r = subprocess.run([PY, *cmd], cwd=ROOT)
    if r.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)} exited with {r.returncode}")
    logger.info(f"done {' '.join(cmd)} in {time.time() - t0:.0f}s")


def start_labeller() -> None:
    pid_file = LOGS / "label_worker.pid"
    if pid_file.exists():
        try:
            os.kill(int(pid_file.read_text().strip()), 0)
            logger.info("label worker already running")
            return
        except (OSError, ValueError):
            pass
    with open(LOGS / "label_k.stdout", "a") as out:
        p = subprocess.Popen([PY, "src/label_k.py"], cwd=ROOT, stdout=out, stderr=subprocess.STDOUT)
    pid_file.write_text(str(p.pid))
    logger.info(f"label worker started (PID {p.pid})")


def wait_labelled(timeout_s: float = 3600) -> None:
    """Block until every generated row has a label (needed before COMMIT #2, the knob verdict and the analyses)."""
    sys.path.insert(0, str(ROOT / "src"))
    import k_cfg as K

    t0 = time.time()
    while time.time() - t0 < timeout_s:
        keys = {K.row_key(r) for n in ("raw_k.jsonl", "knobs_norm.jsonl", "reuse_exp27.jsonl")
                for r in K.read_jsonl(K.RAW_DIR / n)}
        done = {l["key"] for l in K.read_jsonl(K.LABELS)}
        miss = len(keys - done)
        if miss == 0:
            return
        logger.info(f"waiting for {miss} labels")
        time.sleep(20)
    raise TimeoutError("labels incomplete")


@logger.catch(reraise=True)
def main() -> None:
    steps = sys.argv[1:] or ["all"]
    if steps == ["all"]:
        steps = ORDER
    for s in steps:
        if s == "label":
            start_labeller()
            continue
        if s not in STEPS:
            raise SystemExit(f"unknown step {s}; choose from {ORDER + ['all']}")
        if s in SKIP_IF_EXISTS and SKIP_IF_EXISTS[s].exists():
            logger.info(f"{s}: {SKIP_IF_EXISTS[s].name} exists (hash-chained); not rewritten")
            continue
        if s in ("commit2", "analyse", "prices"):
            wait_labelled()
        for cmd in STEPS[s]:
            run(cmd)


if __name__ == "__main__":
    main()
