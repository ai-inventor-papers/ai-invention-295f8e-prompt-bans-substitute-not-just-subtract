# Review of the iteration-1 research report (REVIEW_REPORT step)

This module audits the run's internal research report for iteration 1: a screen of six accounts of how
Qwen3-8B chooses a path-search algorithm, run as seven artifacts (one dataset, six experiments). The
review checks completeness, traceability and what the report says was learned. It recomputes the report's tables
from the artifacts' per-sample rows, and its verdict is in `.terminal_claude_agent_struct_out.json`.

## What was done
- Read the report, the original user request, the iteration strategy (`gen_strat_1`) and the seven artifact workspaces (read-only).
- Recomputed the report's sample-level tables from each artifact's per-sample JSONL rows (scripts in `audit/`).
- Re-ran the association experiment's grid hidden tests on 250 programs, once with the artifact's checker and once
  reading a `None` return as `[]`. The strict run reproduces the artifact's pass/fail labels on all 250 programs.
- Checked result files, logs and timestamps for analyses that the report omits or describes incompletely.
- Looked up the nearest published neighbours of the report's positive claims.

## Layout
- `.terminal_claude_agent_struct_out.json`: the structured review (scores, critiques, flags).
- `audit/common.py`: shared helpers (JSONL reader, Hill number, per-condition summary).
- `audit/exp1_recompute.py`: association experiment, every condition (report Table 6).
- `audit/exp2_recompute.py`: geometry experiment, forced, ban and removal arms (Tables 11, 13, 16).
- `audit/exp4_recompute.py`: decommitment experiment arms (Table 22).
- `audit/exp5_recompute.py`: instruction tuning arms and steering arms (Tables 24, 26).
- `audit/exp6_recompute.py`: decoding experiment cells, seeds, instructions, generate then select (Tables 27, 31).
- `audit/dfs_failures.py`: why DFS-labelled grid programs fail the hidden tests.
- `audit/lenient_rescore.py`: re-runs the grid hidden tests with `None` read as `[]`.
- `audit/outputs/`: the printed output of each script, plus `other_checks.md` (hand checks: log scores, gate
  arithmetic, timestamps, sensitivity files, hypothesis-review scores).
- `audit/build_review.py`: assembles the review text and writes `.terminal_claude_agent_struct_out.json`; it asserts the
  derived `blocking` flag (true exactly when soundness <= 1 or results_reported is false).

## How to run
The scripts read the iteration-1 artifacts from the directory named by the `AII_GEN_ART` environment variable
(default `gen_art`, relative to the working directory). Point it at the iteration-1 `gen_art/` directory of the parent run
(`3_invention_loop/iter_1/gen_art`, which holds `gen_art_dataset_1` and `gen_art_experiment_1` to `_6`), then run:

```
cd audit
export AII_GEN_ART=/path/to/3_invention_loop/iter_1/gen_art
PYTHONDONTWRITEBYTECODE=1 python3 exp1_recompute.py
PYTHONDONTWRITEBYTECODE=1 python3 lenient_rescore.py ban:bfs succession:2 mention:dfs   # executes model-written code; about 2 minutes
```

Only the Python 3 standard library is needed. `lenient_rescore.py` executes model-generated programs in
subprocesses with per-case time limits, so run it only in a sandbox.

## Restoring removed files
Nothing in this module is marked for deletion (`.aii/manifest.yaml` has no entries). No caches, model weights
or large binaries were written.
