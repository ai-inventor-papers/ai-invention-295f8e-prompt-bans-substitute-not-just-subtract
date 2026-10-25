#!/usr/bin/env python3
"""BASE-W stage CLI: which weights hold the default algorithm (iteration 10).

Every stage runs its scripts in their own processes (GPU stages load one model per process; never two models on the
GPU); each child's PID is recorded in logs/pids.jsonl and its output goes to logs/<stage>_<n>.log.

  s_1   vendor + hash the inputs, hardware/env record, labeller gate, COMMIT #0 (protocol + code snapshot)
  s0    capture the fork states of Qwen3-8B and Qwen3-8B-Base, numerics debug sweep, stage-0 report, null draws +
        COMMIT #1
  w1tf  W1 teacher-forced arms and nulls + COMMIT #2 (generation plan and predictions); per-token logit export
  w1gen W1 generation (30 CRN slots per arm), G5 determinism test, labelling, analysis
  ext   pre-registered generation extensions: dose-response (COMMIT #4), strong nulls at x3 (COMMIT #5), 60 extra
        CRN slots for power (COMMIT #7); labelling, analysis
  w2    Hungarian matching + COMMIT #3, in-place weight swaps (all-position and fork-only scopes), summary
  w3    Gemma-3-4b it/pt captures and the output-untied row test (descriptive)
  out   CPU tests, delta geometry, LeetCode-pair dependency check, stdlib audit, summary, positioning, figures,
        method_out.json (+ mini/preview)

Usage: .venv/bin/python method.py --stages s_1,s0,w1tf,w1gen,ext,w2,w3,out   (or --stages all)
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
LOGS = ROOT / "logs"
PY = sys.executable

STAGES: dict[str, list[list[str]]] = {
    "s_1": [["inputs10.py", "copy"], ["inputs10.py", "hardware"], ["inputs10.py", "gate"],
            ["protocol10.py", "commit0"]],
    "s0": [["capture10.py", "qwen", "all"], ["capture10.py", "qwen_base", "all"], ["debug_s0.py", "qwen"],
           ["debug_s0.py", "qwen_base"], ["w1_tf.py", "s0report"], ["w1_tf.py", "nulls"]],
    "w1tf": [["w1_tf.py", "score"], ["w1_tf.py", "export_zs"]],
    "w1gen": [["w1_gen.py", "gpu", "2400"], ["w1_gen.py", "g5"], ["w1_gen.py", "label"], ["w1_gen.py", "analyze"]],
    "ext": [["w1_dose_gen.py", "commit"], ["w1_dose_gen.py", "gpu"], ["w1_dose_gen.py", "commit_strong"],
            ["w1_dose_gen.py", "gpu_strong"], ["w1_dose_gen.py", "commit_power"], ["w1_dose_gen.py", "gpu_power"],
            ["w1_gen.py", "label"], ["w1_gen.py", "analyze"], ["w1_dose_gen.py", "analyze_power"]],
    "w2": [["w2_swap.py", "match"], ["w2_swap.py", "gpu", "all"], ["w2_swap.py", "summary"]],
    "w3": [["w3_gemma.py", "gpu", "gemma"], ["w3_gemma.py", "gpu", "gemma_pt"], ["w3_gemma.py", "score"]],
    "out": [["tests_cpu10.py"], ["analysis10.py", "delta_geometry"], ["depcheck10.py"], ["../audit/rederive.py"],
            ["analysis10.py", "summary"], ["positioning10.py"], ["figures10.py"], ["outputs10.py"]],
}
ORDER = ("s_1", "s0", "w1tf", "w1gen", "ext", "w2", "w3", "out")


def run(stage: str, i: int, cmd: list[str]) -> None:
    LOGS.mkdir(exist_ok=True)
    log = LOGS / f"{stage}_{i}.log"
    env = dict(os.environ, PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True")
    argv = [PY, "-I", cmd[0]] + cmd[1:] if cmd[0].startswith("../audit") else [PY] + cmd
    t0 = time.time()
    with open(log, "w") as fh:
        p = subprocess.Popen(argv, cwd=SRC, stdout=fh, stderr=subprocess.STDOUT, env=env)
        with open(LOGS / "pids.jsonl", "a") as pf:
            pf.write(json.dumps({"stage": stage, "cmd": cmd, "pid": p.pid, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                                                                               time.gmtime())}) + "\n")
        rc = p.wait()
    print(f"[{stage}] {' '.join(cmd)} -> rc {rc} in {time.time() - t0:.0f}s (log {log.relative_to(ROOT)})")
    if rc != 0:
        raise SystemExit(f"stage {stage} failed at {cmd}; see {log}")


def format_outputs() -> None:
    skill = Path("/ai-inventor/.claude/skills/aii-json")
    py = skill.parent / ".ability_client_venv" / "bin" / "python"
    if py.exists():
        subprocess.run([str(py), str(skill / "scripts" / "aii_json_validate_schema.py"), "--format", "exp_gen_sol_out",
                        "--file", str(ROOT / "method_out.json")], check=False)
        subprocess.run([str(py), str(skill / "scripts" / "aii_json_format_mini_preview.py"), "--input",
                        str(ROOT / "method_out.json")], check=False)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stages", default="all")
    a = ap.parse_args()
    stages = ORDER if a.stages == "all" else tuple(s.strip() for s in a.stages.split(","))
    for s in stages:
        if s not in STAGES:
            raise SystemExit(f"unknown stage {s}; choose from {ORDER}")
        for i, cmd in enumerate(STAGES[s]):
            run(s, i, cmd)
        if s == "out":
            format_outputs()


if __name__ == "__main__":
    main()
