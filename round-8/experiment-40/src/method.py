#!/usr/bin/env python3
"""Entry point: runs the whole iteration-8 DAS experiment in stage order (each stage is resumable and skips work
whose result file already exists). GPU stages load one model at a time.

  S0  src/s0_inputs.py      copy + hash inputs; dependency extraction (all ten datasets of art_j3Rm_lr2nzR6)
  S1  src/prompts8.py       T10 and GRID prompt sets, splits
  #0  src/commit0.py        protocol commitment (before any GPU use)
  S3-S6  src/run_dec.py     decision site per unit: token maps, adherence, commit #1, caches, unit tests, scan, fits,
                            controls c1/c2/c4/c5/c6/c7, baselines
  S9  src/run_gen.py        generation cells (commit #2 first), labelled by src/label8.py
  S8  src/run_rinit.py      random-initialisation control c3 (decision site; --band for the band)
  S7  src/run_band.py       T10 task band
  S10 src/run_med.py        mediation of iteration 4's random pushes (commit #3, #4)
  post src/run_post.py      per-pair label-control test for p_K2 (T10)
  S11-S12 src/analysis8.py, src/figures8.py, src/novelty8.py, src/digest8.py, src/outputs8.py, audit/rederive.py

Usage: .venv/bin/python method.py [--cpu-only]
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = sys.executable


def run(*args: str) -> None:
    print("+", " ".join(args), flush=True)
    subprocess.run([PY, *args], cwd=ROOT, check=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cpu-only", action="store_true", help="only the analysis / output stages")
    a = ap.parse_args()
    if not a.cpu_only:
        run("src/s0_inputs.py")
        run("src/prompts8.py")
        run("src/commit0.py")
        run("src/run_dec.py", "--unit", "T10")
        run("src/run_gen.py", "--unit", "T10", "--sites", "dec")
        run("src/run_rinit.py", "--unit", "T10")
        run("src/run_band.py")
        run("src/run_gen.py", "--unit", "T10", "--sites", "band")
        run("src/run_rinit.py", "--unit", "T10", "--band")
        run("src/run_dec.py", "--unit", "GRID")
        run("src/run_gen.py", "--unit", "GRID", "--sites", "dec")
        run("src/run_rinit.py", "--unit", "GRID")
        run("src/run_med.py")
        run("src/run_post.py", "--unit", "T10")
        run("src/run_dec.py", "--unit", "T10", "--force_L", "24")
        run("src/label8.py", "--unit", "T10")
        run("src/label8.py", "--unit", "GRID")
    run("src/analysis8.py")
    run("src/novelty8.py")
    run("src/figures8.py")
    run("src/digest8.py")
    run("src/outputs8.py")
    subprocess.run([sys.executable, "audit/rederive.py"], cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
