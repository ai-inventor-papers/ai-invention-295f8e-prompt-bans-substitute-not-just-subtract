#!/usr/bin/env python3
"""Panel A (iteration 5, Step 2): does the base model's repertoire forecast which coding tasks a ban-free isotropic
plan push can move, and where they land? Entry point that runs every stage of the pipeline in src/.

METHOD (the forecast under test): for each unit, the correct-only off-default share beta_u of Qwen3-8B-Base on the
instruct twin's exact token ids (predicted class MOVABLE iff beta_u >= 0.05) and its most frequent correct non-default
algorithm r_u (predicted landing), sha256-committed before any push.
BASELINES / RIVALS (pre-registered, computed ban-free before the commitment): the instruct model's opening margin
(teacher-forced log-prob of each mode's first body tokens), the merit gap (runtime and length ratios of each mode's
reference to the default's), the twin's modal share, the novelty-instruction off-default share, the association prompt
('What is the standard alternative to <default>?') and AST proximity (Zhang-Shasha distance of each mode's reference to
the twin's default programs). A1 compares rho(beta, E) with every rival; A2 compares the log score of the base
composition with association and proximity on the realised landings.

Usage:
  python method.py setup        # stage 0 + frozen specs/prompts + CPU tests (fresh checkout only: in this workspace
                                # it would overwrite files already committed in commitments.log)
  python method.py workers      # start gpu_worker, label_worker5 and controller in the background
  python method.py unit A1      # build, gate (round 0), freeze and commit one unit (pushes follow automatically)
  python method.py final        # every post-sampling stage: analysis, audits, outputs, figures, report, re-derivation
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = str(ROOT / ".venv" / "bin" / "python")


def run(args: list[str], check: bool = True) -> int:
    print("+", " ".join(a.replace(str(ROOT) + "/", "") for a in args), flush=True)
    r = subprocess.run(args, cwd=ROOT)
    if check and r.returncode != 0:
        raise SystemExit(f"step failed ({r.returncode}): {' '.join(args)}")
    return r.returncode


def setup() -> None:
    run([PY, "src/stage0.py"])
    run([PY, "src/specs5.py"])
    run([PY, "-m", "pytest", "-q", "-c", "pytest.ini", "tests"])


def workers() -> None:
    for script in ("src/gpu_worker.py", "src/label_worker5.py", "src/controller.py"):
        log = open(ROOT / "logs" / (Path(script).stem + ".out"), "a")
        p = subprocess.Popen([PY, script], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        print(f"started {script} pid {p.pid}")


def unit(u: str) -> None:
    run([PY, "-m", "newbench.common.build5", u])
    run([PY, "-m", "newbench.common.gate5", u])
    run([PY, "src/freeze_unit.py", u, "round0"])
    run([PY, "src/unit_commit.py", u])


def final() -> None:
    steps = [[PY, "src/fix_validity.py"], [PY, "src/novelty_audit.py"], [PY, "src/final_run.py"],
             [PY, "src/assoc_fix.py"],
             [PY, "src/engine_check.py"], [PY, "src/recheck.py"], [PY, "src/external_refs.py"],
             [PY, "src/outputs5.py"], [PY, "src/figures5.py"], [PY, "src/report5.py"],
             ["python3", "-I", "audit/rederive.py"], [PY, "src/verify_chain.py"]]
    for s in steps:
        run(s)


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("setup", "workers", "unit", "final"):
        print(__doc__)
        sys.exit(2)
    cmd = sys.argv[1]
    if cmd == "setup":
        setup()
    elif cmd == "workers":
        workers()
    elif cmd == "unit":
        unit(sys.argv[2])
    else:
        final()
