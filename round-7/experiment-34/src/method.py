#!/usr/bin/env python3
"""Iteration 7 (direction 3): does one early token decide the algorithm? Orchestrator of every stage, in the
committed order. Each GPU stage is a separate process (one bf16 Qwen3-8B on the GPU at a time); every stage is
resumable (row keys / commit files), so re-running skips finished work.

Stages (comma list or 'all'):
  stage0    src/stage0.py         Stage 0 engine check + GPU unit tests; starts the label worker
  forks     src/forkrun.py        F1 prefix resampling, change points, forks -> commit #1 (amendments #1b/#1c)
  axis      src/axis7.py          P2 axis -> commit #2
  freeze    src/make_commit0b.py  analysis code frozen by hash (before commit #3)
  predict   src/predict7.py       predictors, margins, LLR -> commit #3 (#3b)
  push      run_after_c3.sh       sealed-row labelling, F/P2 analysis, clamp selection, T03 confirmation, targeted
                                  push, top-five push, same-engine re-measurement, clamp (GPU)
  analysis  analysis7 / tests / top5geo / analysis_push / novelty / figures
  outputs   src/outputs7.py + audit/rederive.py -> method_out.json
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

from loguru import logger

ROOT = Path(__file__).resolve().parent
PY = str(ROOT / ".venv" / "bin" / "python")
LOGS = ROOT / "logs"
LOGS.mkdir(exist_ok=True)
logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(str(LOGS / "method.log"), rotation="30 MB", level="DEBUG")


def run(args: list[str], log: str, check: bool = True) -> int:
    t0 = time.time()
    logger.info(f"run {' '.join(args)} -> logs/{log}")
    with open(LOGS / log, "a") as f:
        p = subprocess.Popen(args, cwd=ROOT, stdout=f, stderr=subprocess.STDOUT)
        rc = p.wait()
    logger.info(f"exit {rc} after {time.time() - t0:.0f}s")
    if check and rc != 0:
        raise RuntimeError(f"{args} failed with exit code {rc}")
    return rc


def start_labeller(raw: str = "data/samples_raw.jsonl", labels: str = "data/labels.jsonl",
                   log: str = "label7.out") -> subprocess.Popen:
    f = open(LOGS / log, "a")
    p = subprocess.Popen([PY, "src/label7.py", raw, labels], cwd=ROOT, stdout=f, stderr=subprocess.STDOUT)
    logger.info(f"label worker pid {p.pid} ({raw})")
    return p


def wait_labels(raw: str, labels: str, timeout: float = 1800) -> None:
    """Block until every row of `raw` has a label row (the follow-mode worker catches up)."""
    sys.path.insert(0, str(ROOT / "src"))
    from c7 import read_jsonl
    t0 = time.time()
    while time.time() - t0 < timeout:
        n_raw = len(read_jsonl(ROOT / raw))
        n_lab = len(read_jsonl(ROOT / labels))
        if n_lab >= n_raw:
            return
        time.sleep(10)
    logger.warning(f"labelling of {raw} incomplete after {timeout}s")


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stages", default="all")
    args = ap.parse_args()
    order = ["stage0", "forks", "axis", "freeze", "predict", "push", "analysis", "outputs"]
    stages = order if args.stages == "all" else args.stages.split(",")
    lab = None
    if any(s in stages for s in ("stage0", "push")):
        lab = start_labeller()
    try:
        if "stage0" in stages:
            run([PY, "src/make_commit0.py"], "commit0.out", check=False) if not (ROOT / "predictions" /
                                                                               "commit0.json").exists() else None
            run([PY, "src/stage0.py"], "stage0.out")
        if "forks" in stages:
            run([PY, "src/forkrun.py", "--paths", "6", "--tasks", "T2,T10,T03", "--define"], "forkrun.out")
        if "axis" in stages and not (ROOT / "predictions" / "commit2_axis.json").exists():
            run([PY, "src/axis7.py"], "axis7.out")
        if "freeze" in stages and not (ROOT / "predictions" / "commit0b_analysis_code.json").exists():
            run([PY, "src/make_commit0b.py"], "commit0b.out")
        if "predict" in stages and not (ROOT / "predictions" / "commit3_predictors.json").exists():
            run([PY, "src/predict7.py", "--tiers", "1,2,3"], "predict7.out")
        if "push" in stages:
            run(["bash", "run_after_c3.sh"], "run_after_c3.out", check=False)
            pid = int((LOGS / "pushrun.pid").read_text())
            while Path(f"/proc/{pid}").exists():
                time.sleep(15)
            run([PY, "src/pushrun.py", "targeted_ext", "--deadline-min", "30"], "pushrun_ext.out", check=False)
            run([PY, "src/explore_llr.py"], "explore_llr.out", check=False)        # exploratory, post hoc
            run([PY, "src/force_token.py"], "force_token.out", check=False)        # exploratory, post hoc
            run([PY, "src/label7.py", "--once", "data/samples_raw_force.jsonl", "data/labels_force.jsonl"],
                "label7_force.out", check=False)
            run([PY, "src/fork_probs.py"], "fork_probs.out", check=False)          # audit support (T10 token probs)
        if "analysis" in stages:
            wait_labels("data/samples_raw.jsonl", "data/labels.jsonl")
            run([PY, "src/label7.py", "--once", "data/samples_raw_s0b.jsonl", "data/labels_s0b.jsonl"],
                "label7_s0b_once.out", check=False)
            run([PY, "src/label7.py", "--once", "data/samples_raw_clamp.jsonl", "data/labels_clamp.jsonl"],
                "label7_clamp.out", check=False)
            run([PY, "src/analysis7.py"], "analysis7.out")
            run([PY, "src/tests_cpu.py"], "tests_cpu.out", check=False)
            run([PY, "src/top5geo.py"], "top5geo.out", check=False)
            run([PY, "src/analysis_push.py"], "analysis_push.out")
            run([PY, "src/analysis_force.py"], "analysis_force.out", check=False)
            run([PY, "src/summary7.py"], "summary7.out", check=False)
            run([PY, "src/novelty7.py"], "novelty7.out", check=False)
            run([PY, "src/figures7.py"], "figures7.out", check=False)
        if "outputs" in stages:
            run([PY, "src/outputs7.py"], "outputs7.out")
            run([PY, "audit/rederive.py"], "rederive.out", check=False)
            run([PY, "src/readme7.py"], "readme7.out", check=False)
    finally:
        if lab is not None:
            (ROOT / "data" / "STOP_LABELLER").touch()
            lab.wait(timeout=600)


if __name__ == "__main__":
    main()
