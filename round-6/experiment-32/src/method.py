#!/usr/bin/env python3
"""Reading the planned algorithm in words -- the full pipeline of this artifact (iteration 6, experiment 32).

Qwen/Qwen2.5-7B-Instruct (bf16) writes Python solutions to 8 algorithm-choice tasks. The released natural-language
autoencoder pair kitft/nla-qwen2.5-7b-L20-av / -ar verbalises its layer-20 states before any code token; blind judges
map every explanation to a catalogue algorithm. The METHOD is the NLA readout; its BASELINES / CONTROLS are the
text-only reader (same judges, the visible text), the outside-reader forecast (PREDICT), swapped twin explanations,
explanations of matched-norm random perturbations and the forced-prompt positive control. The causal arm patches the
difference of two AR reconstructions (edited vs unedited explanation) into the layer-20 states, against the unedited
round trip, an unrelated-word edit, a matched-norm random push and a matched-norm difference-in-means push.

Stages (one GPU model in memory at a time; every stage is its own script under src/ so it can be resumed):
  S0  src/tests_cpu.py, src/dep_usage.py, src/commit0.py          CPU tests, dependency use, commit #0
  S1-3 src/gen.py twin engine_check forced_seed ban             prompts, engine checks, behaviour (GPU)
       src/labels.py (follows data/samples_raw.jsonl)           frozen labellers (CPU, in parallel)
       src/behaviour.py defaults | report | regate              commit #1, per-task report, style re-gate
  S4  src/states.py                                             layer-20 state cache (GPU)
       src/judges.py calibrate ; src/commit2.py                 judge calibration gate, commit #2
  S5  src/nla_av.py gate ; S6 src/nla_ar.py gate                smoke tests, reference FVE, layer convention
  S5  src/nla_av.py production ; S6 src/nla_ar.py production    explanations, task gate, edits, deltas, commit #3
  S7  src/judges.py run                                         blind judges (OpenRouter; runs while S8 uses the GPU)
  S8  src/causal_gen.py + src/labels.py (labels_causal)         causal arm (GPU)
  S9  src/novelty.py ; analysis/readout.py ; analysis/causal.py ; src/figures.py ; audit/rederive.py ; src/outputs.py

Usage: python method.py [--from STAGE] [--only STAGE ...]
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

from loguru import logger

ROOT = Path(__file__).resolve().parent
PY = sys.executable
STAGES: list[tuple[str, list[list[str]]]] = [
    ("S0", [["src/tests_cpu.py"], ["src/dep_usage.py"], ["src/commit0.py"]]),
    ("S3", [["src/gen.py", "twin", "engine_check", "forced_seed", "ban"]]),  # labels.py and behaviour.py defaults run beside it
    ("S3b", [["src/labels.py", "--raw", "data/samples_raw.jsonl", "--out", "data/labels.jsonl"]]),
    ("S3c", [["src/behaviour.py", "report"], ["src/behaviour.py", "regate"]]),
    ("S4", [["src/states.py"], ["src/judges.py", "calibrate"], ["src/commit2.py"]]),
    ("S5a", [["src/nla_av.py", "gate"], ["src/nla_ar.py", "gate"]]),
    ("S5b", [["src/nla_av.py", "production"], ["src/nla_ar.py", "production"]]),
    ("S7S8", [["src/causal_gen.py", "--deadline-min", "75"]]),  # src/judges.py run in parallel
    ("S8b", [["src/labels.py", "--raw", "data/samples_causal_raw.jsonl", "--out", "data/labels_causal.jsonl",
              "--name", "label_causal"]]),
    ("S9", [["src/novelty.py"], ["analysis/readout.py"], ["analysis/causal.py"], ["src/figures.py"],
            ["audit/rederive.py"], ["src/outputs.py"]]),
]


def run(cmd: list[str]) -> None:
    t0 = time.time()
    logger.info(f"$ {' '.join(cmd)}")
    r = subprocess.run([PY] + cmd, cwd=ROOT)
    if r.returncode != 0:
        raise RuntimeError(f"{cmd} exited {r.returncode}")
    logger.info(f"  done in {time.time() - t0:.0f}s")


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="start", default="S0")
    ap.add_argument("--only", nargs="*", default=None)
    args = ap.parse_args()
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    (ROOT / "logs").mkdir(exist_ok=True)
    logger.add(str(ROOT / "logs" / "method.log"), rotation="30 MB", level="DEBUG")
    names = [s for s, _ in STAGES]
    todo = args.only or names[names.index(args.start):]
    for name, cmds in STAGES:
        if name not in todo:
            continue
        if name == "S7S8":
            jp = subprocess.Popen([PY, "src/judges.py", "run"], cwd=ROOT)
            for c in cmds:
                run(c)
            jp.wait()
            continue
        for c in cmds:
            run(c)


if __name__ == "__main__":
    main()
