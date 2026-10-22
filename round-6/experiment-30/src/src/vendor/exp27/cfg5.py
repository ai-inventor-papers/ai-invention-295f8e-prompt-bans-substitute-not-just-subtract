#!/usr/bin/env python3
"""Iteration-5 constants (Claim C: plan noise against plan-first prompting; Claim F: the literal thinking-on cell).

Builds on exp19's src/cfg.py (copied verbatim next to this file; its ROOT is this workspace and INPUTS = inputs/).
Conventions added here:
- D5 = the decisive tasks (N = 50 per cell: W1-W5 x k 0-9); ND10 = the other 10 tasks (N = 30: W1-W5 x k 0-5).
- The code-stage CRN stream of every Claim-C arm is u_stream(task, w, k), shared with TWIN. Intent / stage-A / stage-B
  streams use their own tags (u_stream(task, w, k, '<TAG>')), so they never consume the code stream.
- PN direction of a slot: x ~ N(0, I) from PCG64(stable_seed(task, 'PN5', w, k)), u = x / ||x||, SHARED by PN_a1,
  PN_a2 and PNPLAIN_a1 (deviation from exp19's arm-specific seeds, logged).
- Ban-free unit: n[l, p] = ||h_clean[l, p]|| * r_Q((l + 1) / 36) for l in 12-23 and p in the task-specification span
  (exp23 results/qwen_ratio.json key 'r_Q', linear interpolation over relative depth, clamped).
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

from cfg import INPUTS, PRED_DIR, RESULTS_DIR, ROOT, read_json

E19 = INPUTS / "exp19"
E20 = INPUTS / "exp20"
E21 = INPUTS / "exp21"
E23 = INPUTS / "exp23"
E5 = INPUTS / "exp5"
EVAL3 = INPUTS / "eval3"
PROMPTS5 = ROOT / "prompts" / "prompts.jsonl"

# ------------------------------------------------------------------------------------------------ wall clock
T0_FILE = RESULTS_DIR / "t0.json"
GEN_DEADLINE_S = 4.75 * 3600          # hard generation deadline: 4 h 45 min after the module's start
LITERAL_BOX_S = 80 * 60               # literal-cell time box (hard stop)


def t0_unix() -> float:
    try:
        return float(read_json(T0_FILE)["t0_unix"])
    except (FileNotFoundError, KeyError, ValueError):
        return time.time()


def gen_deadline_unix() -> float:
    return t0_unix() + GEN_DEADLINE_S


# ------------------------------------------------------------------------------------------------ tasks
D5 = ("T03", "T10", "T2", "T05", "T1")
ND10 = ("T04", "T06", "T08", "T11", "T13", "T14", "R1", "R2", "R3", "R6")
TASKS15 = D5 + ND10
K_D5 = tuple(range(10))
K_ND10 = tuple(range(6))
K_ND10_REDUCED = tuple(range(4))       # drop-order item (2): ND10 N 30 -> 20


def slots_for(task: str, reduced_nd: bool = False) -> tuple[int, ...]:
    if task in D5:
        return K_D5
    return K_ND10_REDUCED if reduced_nd else K_ND10


# ------------------------------------------------------------------------------------------------ literal cell F
F_TASK = "T2"
F_TEMPS = (0.3, 0.7, 1.0, 1.3)
F_TOPK = 10
F_SEED_K = (0, 1, 2, 3)
F_REPEAT_T = 0.7
THINK_CAP = 16384
ANSWER_MAX = 1536
MAX_MODEL_LEN = 18432
THINK_START = 151667
THINK_END = 151668
EARLY_EXIT = ("\n\nConsidering the limited time by the user, I have to give the solution based on the thinking "
              "directly now.\n</think>\n\n")
FP8_MODEL_ID = "Qwen/Qwen3-8B-FP8"
FP8_REVISION = "220b46e3b2180893580a4454f21f22d3ebb187d3"
BASE_MODEL_ID = "Qwen/Qwen3-8B-Base"
F_PREDICTION = {"C_T_max": 1, "of": 20, "statement": "C_T <= 1 of 20 seeds change their final-code label across T"}

# first approach named in a thinking trace (case-insensitive earliest match; exp21 cfg4.FIRST_APPROACH_LEXICON)
FIRST_APPROACH_LEXICON = [
    ("dijkstra", r"dijkstra"),
    ("bellman_ford", r"bellman[- ]?ford"),
    ("spfa", r"spfa|shortest path faster"),
    ("floyd_warshall", r"floyd|warshall"),
    ("a_star", r"a-star|astar|(?<![A-Za-z0-9_])A\*"),
    ("bidirectional", r"bidirectional"),
    ("dial_bucket", r"(?<![a-z])dial(?![a-z])|bucket"),
    ("bfs", r"(?<![a-z])bfs(?![a-z])|breadth[- ]first"),
    ("dfs", r"(?<![a-z])dfs(?![a-z])|depth[- ]first"),
    ("topological_dag", r"topolog|(?<![a-z])dag(?![a-z])"),
]

# ------------------------------------------------------------------------------------------------ prompts (frozen)
IFG_INSTR = ("Before writing any code, state in one sentence the algorithm you will use, on a single line that "
             "starts with Intent:. Then write the code.")
# Wording v2 (deviation D-pilot, the plan's one allowed revision before commit #1): the v1 stage-1 sentences
# ("Do not write code yet. ...") lost to the specification's final format line on 0-100% of pilot rows (the model
# wrote the code block at once), so the step structure is stated and the format line is deferred explicitly.
PSL_A_V1 = ("Do not write code yet. First list exactly 5 short, distinct observations about this problem that could "
            "help solve it, numbered 1 to 5.")
EAP_A_V1 = ("Do not write code yet. List the distinct algorithms that correctly solve this task, one per line, "
            "formatted as <number>. <algorithm name>: <one-line idea>. List at most 8.")
PSL_A = ("This is step 1 of 3: do not write any code in this step, and ignore the code-block instruction at the end "
         "of the task for now (you will write the code in a later step). First list exactly 5 short, distinct "
         "observations about this problem that could help solve it, numbered 1 to 5.")
EAP_A = ("This is step 1 of 2: do not write any code in this step, and ignore the code-block instruction at the end "
         "of the task for now (you will write the code in step 2). List the distinct algorithms that correctly solve "
         "this task, one per line, formatted as <number>. <algorithm name>: <one-line idea>. List at most 8.")
PSL_B_V1 = ("Combine observations {i} and {j} into a short natural-language plan (at most 5 sentences) for an "
            "algorithm that solves the problem. Do not write code yet.")
PSL_B = ("Step 2 of 3: combine observations {i} and {j} into a short natural-language plan (at most 5 sentences) for "
         "an algorithm that solves the problem. Do not write any code yet.")
PSL_C = "Now implement your plan in Python with the required function signature. Output only the code in one python code block."
EAP_B = "Implement approach {i}: {name}. Output only the code in one python code block."
INTENT_PREFIX = "Intent:"

# ------------------------------------------------------------------------------------------------ arms (Claim C)
# kind: prompt kind; T: code-stage temperature; extra per-family fields. 'decode': shared | pn | leftpad | multi
ARMS5: dict[str, dict[str, Any]] = {
    "TWIN": {"kind": "twin", "T": 1.0, "family": "REF", "decode": "shared"},
    "PLAIN": {"kind": "plain", "T": 1.0, "family": "REF_PLAIN", "decode": "shared"},
    "PN_a1": {"kind": "twin", "T": 1.0, "alpha": 1.0, "family": "PN", "decode": "pn"},
    "PN_a2": {"kind": "twin", "T": 1.0, "alpha": 2.0, "family": "PN", "decode": "pn"},
    "PNPLAIN_a1": {"kind": "plain", "T": 1.0, "alpha": 1.0, "family": "PNPLAIN", "decode": "pn"},
    "IFG_hot": {"kind": "ifg", "T": 0.7, "t_intent": 1.3, "family": "IFG", "decode": "shared"},
    "IFG_paper": {"kind": "ifg", "T": 0.60, "t_intent": 0.73, "family": "IFG", "decode": "shared"},
    "BINT": {"kind": "ifg", "T": 0.7, "t_intent": 1.3, "family": "BINT", "decode": "leftpad"},
    "PSL": {"kind": "psl", "T": 0.9, "top_p": 0.95, "family": "PSL", "decode": "multi"},
    "EAP": {"kind": "eap", "T": 1.0, "family": "EAP", "decode": "multi"},
    "DMD_a1": {"kind": "twin", "T": 1.0, "dmd_alpha": 1.0, "family": "DMD", "decode": "shared"},
    "DMD_a2": {"kind": "twin", "T": 1.0, "dmd_alpha": 2.0, "family": "DMD", "decode": "shared"},
    # P3 reruns (bf16 engine: iteration-4 FP8 rows are not reusable slot for slot)
    "T1.3": {"kind": "twin", "T": 1.3, "family": "TEMP", "decode": "shared"},
    "TOPK10": {"kind": "twin", "T": 1.0, "top_k": 10, "family": "TOPK10", "decode": "shared"},
    "NOVELTY": {"kind": "novelty", "T": 1.0, "family": "NOVELTY", "decode": "shared"},
    "SEMSEED": {"kind": "semseed", "T": 1.0, "family": "SEMSEED", "decode": "shared"},
}
INTENT_MAX = 64
PSL_A_MAX = 320
PSL_B_MAX = 256
EAP_A_MAX = 320
PN_BLOCKS = list(range(12, 24))

# priority queue (plan S5)
P1 = ("TWIN", "PN_a1", "PN_a2", "IFG_hot", "EAP", "DMD_a1")
P2 = ("PLAIN", "PNPLAIN_a1", "DMD_a2", "IFG_paper", "PSL", "BINT")
P3 = ("T1.3", "TOPK10", "NOVELTY", "SEMSEED")
P4 = ("TWIN", "PN_a1", "PN_a2", "IFG_hot", "EAP", "DMD_a1", "PLAIN", "PNPLAIN_a1", "DMD_a2")
P5 = ("PSL", "BINT")
DROP_ORDER = ["P5", "ND10_N20", "SEMSEED_rerun", "ND10_DMD_a2", "IFG_paper", "ND10_PLAIN_PNPLAIN"]

# ------------------------------------------------------------------------------------------------ DMD calibration
DMD_STEPS = 32
DMD_T_RANGE = (1.0, 4.0)
DMD_BISECT_TOL = 0.01
DMD_ONPOLICY_TOL = 0.15
DMD_MAX_SECANT = 3
CAL_W = ("W1", "W2", "W3", "W4", "W5")
CAL_K = tuple(range(10))
PILOT_TASKS = ("T03", "T2", "T05")
PILOT_N = 10
PILOT_MIN_RATE = 0.8

# ------------------------------------------------------------------------------------------------ analysis (frozen)
DEPTH = 25
N_RAREFY = 1000
N_BOOT_D5 = 2000
N_BOOT_ND = 500
BOOT_RAREFY = 200
COST_BOUND = 0.05
HILL_TARGETS = (1.5, 2.0)
CLAIM_C_MIN_WINS = 3
UNRESOLVED_BAND = (0.2, 0.8)
MOVE_EXCESS = 0.10
MOVE_FISHER_P = 0.05
BOOT_SEED5 = 20261021
TEXT_SAMPLERS = ("IFG", "PSL", "EAP", "BINT")
CLASS_SETTINGS: dict[str, list[str]] = {
    "PN": ["TWIN", "PN_a1", "PN_a2"],
    "PN+": ["TWIN", "PN_a1", "PN_a2", "PLAIN", "PNPLAIN_a1"],
    "IFG": ["TWIN", "IFG_hot", "IFG_paper"],
    "IFG_hot_only": ["TWIN", "IFG_hot"],
    "PSL": ["TWIN", "PSL"],
    "EAP": ["TWIN", "EAP"],
    "BINT": ["TWIN", "BINT"],
    "DMD": ["TWIN", "DMD_a1", "DMD_a2"],
    "TEMP": ["TWIN", "T1.3"],
    "TOPK10": ["TWIN", "TOPK10"],
    "NOVELTY": ["TWIN", "NOVELTY"],
    "SEMSEED": ["TWIN", "SEMSEED"],
}
JUDGE_CAP_TOTAL = 1.00
SUBCAPS = {"labels": 0.40, "regate": 0.25, "novelty": 0.15, "lexicon": 0.05}
JUDGE_A = "google/gemini-2.5-flash-lite"
JUDGE_B = "openai/gpt-4.1-mini"
JUDGE_TIE = "deepseek/deepseek-chat-v3.1"


def precision() -> dict[str, Any]:
    p = PRED_DIR / "precision_rule.json"
    if p.exists():
        return read_json(p)
    return {"hf_engine": "hf_bf16"}


def hf_engine_tag() -> str:
    return precision().get("hf_engine", "hf_bf16")


ENV_INFO = {k: os.environ.get(k) for k in ("HF_HUB_CACHE",)}
