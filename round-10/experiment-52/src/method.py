#!/usr/bin/env python3
"""NOV-B2 entry point: a FunSearch-style island search on online bin packing with Qwen3-8B-FP8 as the mutator, comparing
decision-token branching (DTB) with its random-position placebo (RPB), two temperature baselines (T1.0; T1.6 with
top-p 0.95), an instruction arm (IDEA) and a no-selection baseline (NS), against the textbook rules, every retrievable
published heuristic and the tuned ab family.

Each stage is a module in src/ (resumable; outputs in data/, results/, figures/, predictions/). Run all stages in order
with `python method.py all`, or one stage with `python method.py <stage>`. Stages that start or need the vLLM server
(smoke, search, v5) expect it up (stage `engine`); `hfreplay` expects it stopped (stage `engine-stop`).

Stages, in the order they were run (see reproducibility.md for timings):
  setup       S0: copy-verify the iteration-9 harness by sha256, run gate.py (G-HARNESS PASS), re-verify
  probes      S2: build the P10 probe states and run the probe gate
  corpus      S3: corpus (textbook, FunSearch, EoH, HSEvo, MCTS-AHD, ReEvo, LLM4AD, 3,843 ab members, tuned ab, stateful)
  tests       offline unit tests (sandbox, prompts, DTB/RPB, islands, clusters)
  commit1     S7: predictions/commit1.json + hash chain (refuses to overwrite)
  engine      start vLLM (start_vllm.sh, TSP9 settings verbatim)
  smoke       S8: seed-99 smoke test (10 calls x 6 arms)
  search      S8/S9: rounds 1-5, C* rule + commit #2, full lockstep search to C*, then NS
  extension   exploratory seeds 4-5 (amendment commit #3): NOVB2_SEEDS=4,5 NOVB2_TAG=ext45 search
  analysis    S10: clusters + sensitivities + bootstrap + placebo, best programs, V3 candidates
  heldout     S10: held-out scoring of best programs; V3 candidates (0.8 rule, corpus-novelty filter)
  s3b         S3b: dependency scan (art_j3Rm_lr2nzR6) + corpus additions
  judges      S11: gated judges (manual read is done before, arm-blind: results/manual_read*.json)
  verdicts    V3 combination + frozen V1/V2/V3/V6 verdicts
  v5          V5 (descriptive; vLLM up)
  engine-stop stop vLLM by PID
  hfreplay    HF bf16 replay of 20 DTB calls
  figures     F1-F7
  outputs     method_out.json (exp_gen_sol_out)
  audit       audit/rederive.py (stdlib re-derivation + placebos)
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = sys.executable


def run(*args: str, env: dict | None = None) -> None:
    print(f"$ {' '.join(args)}", flush=True)
    r = subprocess.run([PY, *args], cwd=ROOT, env=dict(os.environ, **(env or {})))
    if r.returncode != 0:
        raise SystemExit(f"stage failed: {' '.join(args)} (exit {r.returncode})")


def engine_start() -> None:
    run("-c", "import sys; sys.path.insert(0, 'src'); import common as C; C.setup_logging('engine'); "
              "import engine as E; E.start_server('graphs'); assert E.wait_ready(900), 'vLLM did not start'; "
              "E.parse_engine_log()")


def engine_stop() -> None:
    run("-c", "import sys; sys.path.insert(0, 'src'); import common as C; C.setup_logging('engine'); "
              "import engine as E; E.stop_server()")


STAGES = {
    "setup": lambda: run("src/s0_setup.py"),
    "probes": lambda: run("src/probes.py"),
    "corpus": lambda: run("src/corpus.py", "build"),
    "tests": lambda: run("tests/test_offline.py"),
    "commit1": lambda: run("src/commit.py", "commit1"),
    "engine": engine_start,
    "smoke": lambda: run("src/search.py", "smoke"),
    "search": lambda: run("src/search.py", "run"),
    "extension": lambda: run("src/search.py", "run", env={"NOVB2_SEEDS": "4,5", "NOVB2_TAG": "ext45"}),
    "analysis": lambda: [run("src/analysis.py", s) for s in ("clusters", "best", "candidates")],
    "heldout": lambda: [run("src/heldout.py", s) for s in ("best", "candidates")],
    "s3b": lambda: [run("-I", "scripts/s3b_scan.py", "results/s3b_hits.json"),
                    run("src/corpus.py", "add", "results/corpus_additions_s3b.json"),
                    run("src/corpus.py", "add", "results/corpus_additions_s3c.json"),
                    run("src/heldout.py", "novelty")],
    "judges": lambda: run("src/judges.py"),
    "verdicts": lambda: [run("src/v3final.py"), run("src/analysis.py", "verdicts"), run("scripts/ext_analysis.py")],
    "v5": lambda: run("src/v5.py"),
    "engine-stop": engine_stop,
    "hfreplay": lambda: run("src/hfreplay.py"),
    "figures": lambda: run("src/figures.py"),
    "outputs": lambda: run("src/outputs.py"),
    "audit": lambda: run("audit/rederive.py"),
}
ORDER = ["setup", "probes", "corpus", "tests", "commit1", "engine", "smoke", "search", "extension", "analysis",
         "heldout", "s3b", "judges", "verdicts", "v5", "engine-stop", "hfreplay", "figures", "outputs", "audit"]


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in list(STAGES) + ["all"]:
        print(__doc__)
        raise SystemExit(2)
    for s in (ORDER if sys.argv[1] == "all" else [sys.argv[1]]):
        STAGES[s]()


if __name__ == "__main__":
    main()
