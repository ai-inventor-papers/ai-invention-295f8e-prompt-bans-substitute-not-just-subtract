#!/usr/bin/env python3
"""Iteration-7 constants: DAS localisation of the planned algorithm (bf16 Qwen3-8B, thinking off, one RTX 4090).

Builds on exp30's src/cfg.py and src/cfg6.py (byte copies next to this file; ROOT = this workspace, INPUTS = inputs/,
a byte copy of exp30's inputs/ folder plus inputs/exp30/ with exp30's own prompts, labels and code).

Conventions (plan STEP 'CONVENTIONS'):
- site(l) = residual stream at the OUTPUT of decoder block l (exp30 hooks.py convention; HF hidden_states[l + 1]).
- spec = [p1, spec_end) (p1 = first 'Task:' token). Every prompt of a task has the same spec ids, so source position
  p1_s + i maps to base position p1_b + i. Edits act in PREFILL only and are computed in fp32, cast to bf16.
- DAS edit at site L*:  h_b[spec] <- h_b[spec] + (h_s[spec] - h_b[spec]) @ R_k^T @ R_k.
- CRN slot s of a task uses exp30's stream code_stream(task, s) = u_stream(task, *SLOT_MAP[s], n=1536); every arm of
  a cell shares the slot's uniform stream.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from cfg import INPUTS, PRED_DIR, RESULTS_DIR, ROOT

TASKS7 = ("T2", "T10", "T03")
CORE7 = ("T2", "T10")
DEFAULT7 = {"T2": "dijkstra", "T10": "union_find", "T03": "full_sort"}
# label vocabulary of the frozen labellers (exp8 suite for T2, exp11 bench for T10/T03)
CATALOGUE7 = {
    "T2": ["dijkstra", "bf_spfa", "bidijkstra", "floyd", "dial"],
    "T10": ["bfs", "dfs", "union_find", "label_propagation"],
    "T03": ["full_sort", "size_k_heap", "heapify_pop", "quickselect", "median_of_medians", "counting_sort"],
}
FORCED_TEMPLATES7 = ("Implement {j} for this task.", "Use {j} to solve this task.", "Solve this task with {j}.",
                     "Your solution should use {j}.", "Write an implementation based on {j}.")  # bench k = 0..4
TRAIN_W = ("W1", "W2", "W3")
HELD_W = "W5"
W4 = "W4"
N_NOUNS = 12
TRAIN_NOUNS = tuple(range(0, 8))
VAL_NOUNS = tuple(range(8, 12))
TRAIN_FAM = (0, 1, 2)
HELD_FAM = (3, 4)
RANKS = (1, 2, 4, 8, 16)
K_MAX = 16
PROFILE_LAYERS = tuple(range(10, 27, 2))           # 10, 12, ..., 26
BAND = tuple(range(12, 24))                          # declared fallback band 12-23
BAND_ALL = tuple(range(0, 36))
N_TGT = 48                                           # target = first 48 response tokens
N_PI = 5                                             # programs per target set
N_PI_VAL = 3
SEEDS = {"das_init": {"T2": 7001 + 2, "T10": 7001 + 10, "T03": 7001 + 3}, "random_subspaces": (9001, 9002, 9003),
         "permutation": 7101, "random_init_network": 0, "mds": 0, "boot": 20261022, "split": 7007}
MAX_NEW7 = {"T2": 512, "T10": 384, "T03": 384}       # exp30 caps (logged deviation D-cap)
BATCH7 = {"T2": 16, "T10": 16, "T03": 16}            # fixed per task (identical GEMM shapes in every arm)
PRECISION7 = "bf16"
ENGINE7 = "hf_bf16_gpu_embed"
GENESIS7 = hashlib.sha256(b"iter7_dir2").hexdigest()
PROMPTS7 = ROOT / "prompts" / "prompts7.jsonl"
SAMPLES7 = ROOT / "data" / "samples_raw.jsonl"
LABELS7 = ROOT / "data" / "labels.jsonl"
CACHE7 = ROOT / "cache"
MAPS7 = ROOT / "das_maps"
TF7 = ROOT / "data" / "tf_scores.jsonl"
E30 = INPUTS / "exp30"
JUDGE_CAP7 = 0.50
BUDGET_MSG7 = "AI Inventor per-run OpenRouter budget"
SEED_STRINGS = {"seed_rand1": "seed=d32qxk4nt43", "seed_rand2": "seed=(horse chair roof love)"}
INSTR = {"instr_new": "Make a new algorithm.",
         # exp18 src/config.py LONGFORM['LF2'] verbatim (ITER3/gen_art_experiment_18)
         "instr_novel": ("Make a fully novel algorithm never seen before for this task. Before writing any code, write "
                         "a design rationale of about 2,000 words that explains the idea, why no one has used it "
                         "before, and why it is correct.")}


def results7(name: str) -> Path:
    return RESULTS_DIR / name


def pred7(name: str) -> Path:
    return PRED_DIR / name
