#!/usr/bin/env python3
"""Entry point: the full path-search ban screen on Qwen3-8B (thinking off), stage by stage.

Every GPU phase runs as its own process (process exit frees VRAM); bans (C) run before removal (D) so the
core prompt-ban events are safe if the removal arm overruns. Forecasts are hash-committed at the end of
Phase B, before any Phase C/D sample exists; Phases C and D refuse to start if the hash does not match.

  tasks       build hidden tests, verify every catalogue reference 3/3, check wrong programs fail
  labtests    labeller unit tests (references + mutants, runtime and AST)
  prompts     build every prompt (token ids, suffix-identity assertion)
  phase_a     baseline (N=200/task), forced named + masked (30x1/mode), association elicitation
  label_a     label Phase A, labeller gate (gold set, two judges + resolver), Phase A summary
  succession  rebuild prompts with the ordered succession ban sets for the modal mode
  phase_b     read-position states, R gate, manifold, directions/anchors, basis, COMMIT forecasts
  phase_c     prompt bans (modal, present-minor, succession steps 2-3), labelled online
  phase_d     affine directional ablation of the modal mode (+ random controls, hooked alpha=0)
  phase_c_ext optional mention:modal arm + exploratory (already committed) step-2 ban events
  phase_d_ext exploratory full-variant removal arms (prompt suffix + generated positions, alpha 2 and 4)
  analysis    contest, C3 decomposition, C2 removal, manifold figures, method_out.json

Usage: python method.py [--from STAGE] [--only STAGE]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from common import TASKS, setup_logger  # noqa: E402

logger = setup_logger("method")
PY = str(ROOT / ".venv" / "bin" / "python")


def modal_arg() -> list[str]:
    s = json.loads((ROOT / "results" / "phaseA_summary.json").read_text())
    return ["--modal", ",".join(f"{t}={s[t]['modal']}" for t in TASKS)]


STAGES = [
    ("tasks", lambda: [PY, "tasks/tasklib.py"]),
    ("labtests", lambda: [PY, "labeller/test_labeller.py"]),
    ("prompts", lambda: [PY, "prompts/build_prompts.py"]),
    ("phase_a", lambda: [PY, "gen/phase_a.py", "--batch", "32"]),
    ("label_a", lambda: [PY, "labeller/run_label_a.py"]),
    ("succession", lambda: [PY, "prompts/build_prompts.py"] + modal_arg()),
    ("phase_b", lambda: [PY, "hf/phase_b.py"]),
    ("phase_c", lambda: [PY, "gen/phase_c.py", "--deadline-min", "45"]),
    ("phase_d", lambda: [PY, "hf/phase_d.py"]),
    ("phase_c_ext", lambda: [PY, "gen/phase_c_ext.py"]),
    ("phase_d_ext", lambda: [PY, "hf/phase_d.py", "--exploratory-full"]),
    ("analysis", lambda: [PY, "analysis/analyze.py"]),
]


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="start", default="tasks")
    ap.add_argument("--only", default=None)
    args = ap.parse_args()
    names = [n for n, _ in STAGES]
    todo = [args.only] if args.only else names[names.index(args.start):]
    for name, cmd in STAGES:
        if name not in todo:
            continue
        c = cmd()
        logger.info(f"=== stage {name}: {' '.join(x.replace(str(ROOT), '.') for x in c)}")
        t0 = time.time()
        r = subprocess.run(c, cwd=str(ROOT))
        logger.info(f"=== stage {name} exit {r.returncode} in {(time.time() - t0) / 60:.1f} min")
        if r.returncode != 0:
            raise RuntimeError(f"stage {name} failed with exit code {r.returncode}")


if __name__ == "__main__":
    main()
