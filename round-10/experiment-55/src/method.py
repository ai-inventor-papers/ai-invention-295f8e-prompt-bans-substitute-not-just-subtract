#!/usr/bin/env python3
"""TP-G2 entry point: runs the whole pipeline stage by stage (each stage is a script in src/; the frozen analysis is
src/analysis_g2.py + src/run_analysis.py, hash-committed in COMMIT #1). Every stage is resumable: generation and the
instrument / sandbox evaluations are cached by sha256, states checkpoint every 50 programs.

  python method.py all            # everything below, in order (skips stages whose outputs exist; --force reruns)
  python method.py <stage>        # one stage

Stages (plan section in brackets):
  cells       [1.1, 1.3]  cell table + words-only prompts + forbidden-word audit + COMMIT0a
  gate        [1.2]       instrument gate on 18 planted + 15 catalogue references (+ mutation tests)
  repro       [0.5]       reproduction gate of iteration 9's frozen readout (8B, 32B)
  generate    [1.4]       forced Qwen3-32B generation, rounds 0-2 (OpenRouter, USD 0.70 stop)
  topups      [1.6]       top-up re-adjudication + named top-ups (jps / iddfs / biastar)
  accept      [1.5]       suites + scrub + alias audit + instrument + dedupe + acceptance
  sets        [1.7, 1.8]  survivor families, covert BFS/DFS set, PRIMARY frame measurement
  frames      [1.10]      hand reads applied, design check, frame lists, state items
  t4          [T4]        synthetic validation of the G1 pipeline
  states      [3]         R1 / R1g / R2 states for 8B and 32B (GPU)
  analysis    [4, 5]      G1 RSA (model + block-0 / TF-IDF / AST baselines) and G2 placement, both models
  rederive    [7]         two independent stdlib + numpy re-derivations (audit/rederive*.py) with placebos
  figures     [6]         figures in activation coordinates
  outputs     [9]         T3 / T9 checks, T5 + LOO predictions, verdicts, method_out.json
  explore     [post-COMMIT1, exploratory] LOO confusion structure, graded behavioural RDM, bootstrap-coverage addendum
Hand reads (data/hand_reads.jsonl) are the executor's reads of the scrubbed code, recorded with src/handread.py.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = str(ROOT / ".venv" / "bin" / "python")
STAGES: list[tuple[str, list[list[str]], str | None]] = [
    ("cells", [["src/gen_or.py", "cells"]], "predictions/cells.json"),
    ("gate", [["src/gate_instrument.py"]], "results/instrument_gate.json"),
    ("repro", [["src/states10.py", "gate", "8b"], ["src/states10.py", "gate", "32b"]], "results/repro_gate.json"),
    ("generate", [["src/gen_or.py", "gen", "0"], ["src/gen_or.py", "gen", "1"],
                  ["src/gen_or.py", "gen", "2",
                   "LEV_DEQ,LEV_HEAP,LEV_SET,LEV_ARR,DFS_DEQ,DFS_HEAP,HEU_HEAP,HEU_SLIST,HEU_ARR,RLX_ARR,RLX_STK,"
                   "RLX_HEAP,RND_HEAP,RND_SET,CRD_SLIST"]], "data/raw_factorial.jsonl"),
    ("topups", [["src/gen_or.py", "topup", a, w, "30"] for a in ("jps", "iddfs", "biastar") for w in ("0",)] +
     [["src/gen_or.py", "topup", a, "1", "30"] for a in ("jps", "biastar")] + [["src/stage_sets.py", "topups"]],
     "data/topup_candidates.jsonl"),
    ("accept", [["src/accept.py", "factorial"]], "data/factorial.jsonl"),
    ("sets", [["src/stage_sets.py", "survivors"], ["src/stage_sets.py", "covert"], ["src/stage_sets.py", "primary"],
              ["src/measure_primary.py"]], "data/placed_covert.jsonl"),
    ("frames", [["src/build_frames.py"]], "data/frames.json"),
    ("t4", [["src/synth_t4.py"]], "results/t4_synthetic.json"),
    ("states", [["src/states10.py", "extract", "8b"], ["src/states10.py", "extract", "32b"]],
     "cache/states/tpg2_32b.npz"),
    ("analysis", [["src/run_analysis.py", "8b", "--boot", "1000"], ["src/run_analysis.py", "32b", "--boot", "1000"]],
     "results/g2_32b.json"),
    ("rederive", [["-I", "audit/rederive.py", "8b", "32b"], ["-I", "audit/rederive2.py", "8b", "32b"]],
     "audit/rederive2.json"),
    ("figures", [["src/figures.py", "both"]], "figures/g1_forest.png"),
    ("outputs", [["src/t3_t9_checks.py"], ["src/make_outputs.py"], ["src/add_topup_preds.py"]], "method_out.json"),
    ("explore", [["src/explore_confusion.py"], ["src/explore_dbeh.py"], ["src/synth_t4b.py"]],
     "results/t4b_bootstrap_coverage.json"),
]


def run_stage(name: str, force: bool) -> None:
    for st, cmds, out in STAGES:
        if st != name:
            continue
        if out and (ROOT / out).exists() and not force:
            print(f"[{st}] skipped ({out} exists; --force to rerun)")
            return
        for c in cmds:
            print(f"[{st}] {' '.join(c)}", flush=True)
            subprocess.run([PY] + c, cwd=ROOT, check=True)
        return
    raise SystemExit(f"unknown stage {name}")


if __name__ == "__main__":
    force = "--force" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__)
        raise SystemExit(0)
    if args[0] == "all":
        for st, _, _ in STAGES:
            run_stage(st, force)
    else:
        for a in args:
            run_stage(a, force)
