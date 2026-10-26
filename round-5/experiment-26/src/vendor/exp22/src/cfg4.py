#!/usr/bin/env python3
"""Constants for the iteration-4 plan-subspace artifact. Utilities come from the untouched exp17 code base
(src_base/cfg.py, whose ROOT resolves to this workspace).

Conventions (inherited from exp17, restated in README.md):
- BLOCK l = decoder block l (0-based); its output is HF hidden_states[l + 1].
- S = [p1, spec_end): first token of 'Task:' to the last user token (chat tail excluded); R = P - 1.
- CRN slot = (task, template, k): uniforms u_stream(task, template, k), identical in every arm; every batch has
  exactly B = 20 rows of ONE (task, template), prune=False, so batch shapes match across arms and coupling is exact.
- EDIT_BLOCKS 12-23 are pushed at S during the prompt prefill only; realised displacements are logged at 12-35.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "src_base", ROOT / "src"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from cfg import (BENCH, BENCH_TASKS, D_MODEL, DATA_DIR, DEFAULT, DIR_DIR, E7, E8, E11, ENDOFTEXT,  # noqa: E402,F401
                 EXP8_TASK, FIG_DIR, IM_END, INPUTS, LOG_DIR, MODEL_ID, MODEL_REVISION, PAD_FILLER, PRED_DIR,
                 PROMPTS_DIR, QUANT, RESULTS_DIR, STATES_DIR, SUITE, TEMPLATE_IDS, TEMPLATE_TAIL, TEMPLATES,
                 append_jsonl, cap_first, container_ram_gb, detect_cpus, read_json, read_jsonl, rel, set_ram_limit,
                 setup_logging, sha256_bytes, sha256_file, sha256_text, stable_seed, utc_now, wilson_ci, write_json,
                 write_jsonl)

E13 = INPUTS / "exp13"
E16 = INPUTS / "exp16"
E17 = INPUTS / "exp17"
E18 = INPUTS / "exp18"
DEP = INPUTS / "dep_art_j3Rm"
# Declared dependency art_j3Rm_lr2nzR6, published as a sibling folder (override with AII_DEP_ART_J3RM); only
# src/extract_known.py reads it, and its output inputs/dep_art_j3Rm/known_subset.jsonl ships with the repository.
DEP_ART_J3RM = Path(os.environ.get("AII_DEP_ART_J3RM", str(ROOT.parent / "art_j3Rm_lr2nzR6")))
DEP_FULL = DEP_ART_J3RM / "full_data_out.json"
ANALYSIS_DIR = ROOT / "analysis"
AUDIT_DIR = ROOT / "audit"
for _d in (ANALYSIS_DIR, AUDIT_DIR, STATES_DIR, PRED_DIR, FIG_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------------------------------------------ tasks
PATH_TASKS = ("T1", "T2")
MOVABLE = ("T03", "T2", "T05", "T10", "T06", "T1")      # frozen C1 set, in the plan's sampling order
OTHER9 = ("T04", "T08", "T11", "T13", "T14", "R1", "R3", "R6", "R2")
TASKS15 = MOVABLE + OTHER9
BENCH13 = tuple(t for t in TASKS15 if t not in PATH_TASKS)   # 12 bench tasks + R2
KNOB_TASKS = tuple(t for t in TASKS15 if t != "R2")          # C2b never touches R2
DEFAULT4 = dict(DEFAULT)
DEFAULT4["R2"] = "dfs_parent"   # modal pilot label (bench/R2/pilot_rows.jsonl: 50/50 dfs_parent), asserted in S0

# T1/T2 catalogues (exp7 prompts_v2 forced conditions; names: exp7 display name + two hand-written aliases)
PATH_CATALOGUE: dict[str, dict[str, list[str]]] = {
    "T1": {"bfs": ["breadth-first search (BFS)", "BFS", "breadth-first search"],
           "dfs": ["depth-first search (DFS)", "DFS", "depth-first search"],
           "bibfs": ["bidirectional BFS", "bidirectional breadth-first search", "two-ended BFS"],
           "iddfs": ["iterative deepening DFS (IDDFS)", "IDDFS", "iterative deepening depth-first search"],
           "astar_gbfs": ["A* or greedy best-first search", "A* search", "greedy best-first search"],
           "dijkstra": ["Dijkstra's algorithm", "Dijkstra", "Dijkstra's shortest-path algorithm"]},
    "T2": {"dijkstra": ["Dijkstra's algorithm", "Dijkstra", "Dijkstra's shortest-path algorithm"],
           "bf_spfa": ["Bellman-Ford or SPFA", "Bellman-Ford", "SPFA"],
           "bidijkstra": ["bidirectional Dijkstra", "bidirectional Dijkstra's algorithm", "two-ended Dijkstra"],
           "floyd": ["Floyd-Warshall", "the Floyd-Warshall algorithm", "Floyd's all-pairs algorithm"],
           "dial": ["Dial's algorithm", "a bucket-queue Dijkstra", "bucket-based shortest paths"]},
}
PATH_EXTRA_LEAK = {"T1": ["bfs", "dfs", "iddfs", "a*", "a star", "astar", "best-first", "dijkstra", "breadth-first",
                          "depth-first", "iterative deepening", "bidirectional"],
                   "T2": ["dijkstra", "bellman", "ford", "spfa", "floyd", "warshall", "dial", "bidirectional"]}

# ------------------------------------------------------------------------------------------------ design
EDIT_BLOCKS = list(range(12, 24))
CAP_BLOCKS = list(range(12, 36))
LATE_BLOCKS = list(range(24, 36))
GEO_BLOCKS = (18, 23)
N_PARA = 30                      # paraphrases per algorithm and prompt family (named / masked)
SEEDS_POP = list(range(9101, 9141))
SEEDS_OTHER = list(range(9101, 9109))
SEEDS_C2C = {t: 9301 + i for i, t in enumerate(MOVABLE)}
ALPHAS_POP = (1.0, 2.0)
ALPHAS_SWEEP = (4.0, 8.0)
DOSES = (0.25, 0.5, 1.0)
B = 20
MAX_NEW = 1024
ESC_EXCESS = 0.20
ESC_PASS_FRAC = 0.8
SCREEN_DIRS = list(range(9001, 9016))
BUDGET_MSG = "AI Inventor per-run OpenRouter budget"
OPENROUTER_CAP_USD = 1.0         # plan: OpenRouter at most USD 1 for this artifact
JUDGE_NOVELTY_CAP_USD = 0.40
DESCRIBE_MODEL = "openai/gpt-4.1-mini"

DESC_FRAMES = [
    "Implement the approach described as: {d}",
    "Solve this task with the following approach: {d}",
    "Use this method for the task: {d}",
    "Your solution should work as follows: {d}",
    "Write code that follows this approach: {d}",
    "Base your solution on this idea: {d}",
    "Apply the following strategy to solve the task: {d}",
    "Your implementation must use this approach: {d}",
    "Write a solution whose method is: {d}",
    "Follow this plan when you solve the task: {d}",
]

RAW = DATA_DIR / "samples_raw.jsonl"
LABELS = DATA_DIR / "labels.jsonl"
SAMPLES = DATA_DIR / "samples.jsonl"
REALISED = DATA_DIR / "realised_disp.jsonl"
TIMING = RESULTS_DIR / "timing.jsonl"
COMMIT_LOG = ROOT / "commitments.log"
PROMPTS4 = PROMPTS_DIR / "prompts4.jsonl"
DESCRIPTIONS = PROMPTS_DIR / "descriptions.json"
DECODING_STR = "T1.0_topp1.0_topk-off_max1024_thinkoff_fencestop"
K = {"twin_mov": list(range(10)), "twin_oth": list(range(6)), "pop": [0, 1], "topup": [2, 3, 4, 5],
     "decomp": [0, 1, 2, 3], "k30": list(range(6)), "k50": list(range(10))}
