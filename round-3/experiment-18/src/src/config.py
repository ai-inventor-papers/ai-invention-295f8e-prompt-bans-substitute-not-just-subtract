"""Shared constants, paths and the task registry for Step 4 (token walk, prompt reach, long-form novelty).

Every frozen choice of the artifact plan that more than one stage reads lives here: task registry (catalogues,
defaults, display names, analysis sets), decoding, seeds, thresholds, model paths and the input locations.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
INPUTS = ROOT / "inputs"
DATA = ROOT / "data"
RESULTS = ROOT / "results"
PRED = ROOT / "predictions"
FIGS = ROOT / "figures"
LOGS = ROOT / "logs"
COMMIT_LOG = ROOT / "commitments.log"
for _d in (DATA, RESULTS, PRED, FIGS, LOGS):
    _d.mkdir(parents=True, exist_ok=True)

BENCH_DIR = INPUTS / "bench"          # copy of exp11 bench (frozen; verified against bench/commitment.json)
SUITE_DIR = INPUTS / "suite"          # copy of exp8 suite (exp1 canonical labeller + T1/T2 tasks)
# The declared dataset dependency (art_j3Rm_lr2nzR6, folder gen_art_dataset_1): read only by audit.py (corpus) and
# dep_usage.py.  DEP_DATASET_DIR overrides the default sibling-folder location of the published repository.
DEP_DATASET = Path(os.environ.get("DEP_DATASET_DIR", str(ROOT.parent / "gen_art_dataset_1")))

for _p in (str(INPUTS), str(SUITE_DIR), str(SRC)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ------------------------------------------------------------------------------------------------ models
MODEL_BF16 = "Qwen/Qwen3-8B"
MODEL_BF16_REV = "b968826d9c46dd6066d109eabc6255188de91218"
MODEL_FP8 = "Qwen/Qwen3-8B-FP8"
HF_HUB = Path(os.environ.get("HF_HUB_CACHE", str(Path.home() / ".cache/huggingface/hub")))


def model_dir(kind: str) -> str:
    if kind == "bf16":
        p = HF_HUB / "models--Qwen--Qwen3-8B" / "snapshots" / MODEL_BF16_REV
        return str(p) if p.exists() else MODEL_BF16
    snaps = sorted((HF_HUB / "models--Qwen--Qwen3-8B-FP8" / "snapshots").glob("*"))
    return str(snaps[-1]) if snaps else MODEL_FP8


SERVED = {"bf16": "qwen3-8b-bf16", "fp8": "qwen3-8b-fp8"}
PORTS = {"bf16": int(os.environ.get("S4_PORT_BF16", "8231")), "fp8": int(os.environ.get("S4_PORT_FP8", "8232"))}

# ------------------------------------------------------------------------------------------------ decoding
DECODING = {"temperature": 1.0, "top_p": 1.0, "top_k": -1, "min_p": 0.0, "repetition_penalty": 1.0}
MAX_TOKENS_SHORT = 1024
MAX_TOKENS_LONG = 4096
THINK_CAP = 16384
THINK_MAX_MODEL_LEN = 20480
THINK_STOP_PHRASE = ("\n\nConsidering the limited time by the user, I have to give the solution based on the thinking "
                     "directly now.\n</think>\n\n")
THINK_END_ID = 151668   # '</think>' in the Qwen3 vocabulary
IM_END_ID = 151645

# ------------------------------------------------------------------------------------------------ seeds
SEED_BASE = 20261021
TASK_IDX = {"T1": 0, "T2": 1, "T03": 2, "T04": 3, "T06": 4, "T10": 5}


def seed_walk(task: str, step: int, rnd: int, i: int) -> int:
    return SEED_BASE + 2_000_000 + 10_000 * TASK_IDX[task] + 1_000 * step + 100 * rnd + i


def seed_sham(task: str, rnd: int, i: int) -> int:
    return SEED_BASE + 2_500_000 + 10_000 * TASK_IDX[task] + 100 * rnd + i


def seed_top5(rnd: int, i: int) -> int:
    return SEED_BASE + 2_600_000 + 100 * rnd + i


def seed_los(task: str, s_idx: int, i: int) -> int:
    return SEED_BASE + 3_000_000 + 10_000 * TASK_IDX[task] + 1_000 * s_idx + i


def seed_two_step(task: str, i: int) -> int:
    return SEED_BASE + 4_000_000 + 10_000 * TASK_IDX[task] + i


def seed_long_off(task: str, prompt_idx: int, i: int, dtype_offset: int = 0) -> int:
    return SEED_BASE + 5_000_000 + 10_000 * TASK_IDX[task] + 1_000 * prompt_idx + 500 * dtype_offset + i


def seed_long_on(task: str, prompt_idx: int, i: int) -> int:
    return SEED_BASE + 6_000_000 + 10_000 * TASK_IDX[task] + 1_000 * prompt_idx + i


def seed_unit(i: int) -> int:
    return SEED_BASE + 9_000_000 + i


# ------------------------------------------------------------------------------------------------ templates
W_TEMPLATES = {
    "W1": "Do not use {N} for this task.",
    "W2": "Your solution must not rely on {N}.",
    "W3": "Avoid {N} entirely.",
    "W4": "{N} is not allowed here.",
    "W5": "Write a correct solution that does not use {N}.",
}
W_IDS = list(W_TEMPLATES)
FILLER = " ."   # exp7 neutral-padding filler

LF_PROMPTS = {
    "LF1": ("Make a new algorithm for this task. Before writing any code, write a design rationale of about 2,000 "
            "words that explains the idea, how it differs from every algorithm you know for this task, and why it "
            "is correct."),
    "LF2": ("Make a fully novel algorithm never seen before for this task. Before writing any code, write a design "
            "rationale of about 2,000 words that explains the idea, why no one has used it before, and why it is "
            "correct."),
}
LF_FORMAT = ("Use only the Python standard library. Give the rationale first, then exactly one ```python block "
             "containing solve.")

# ------------------------------------------------------------------------------------------------ tasks
# T1/T2 labels are the exp1 canonical suite labels (suite/common.py CATALOGUE); A* and greedy best-first share
# 'astar_gbfs', and 'dijkstra' on T1 is unit-weight Dijkstra.  Display names are exp7's v2 names as frozen in
# exp8 prompts/frozen_prompts.json.
TASKS: dict[str, dict[str, Any]] = {
    "T1": {"family": "path", "suite": "t1", "default": "bfs",
           "catalogue": ["bfs", "dfs", "bibfs", "iddfs", "astar_gbfs", "dijkstra"],
           "display": {"bfs": "breadth-first search (BFS)", "dfs": "depth-first search (DFS)",
                       "bibfs": "bidirectional BFS", "iddfs": "iterative deepening DFS (IDDFS)",
                       "astar_gbfs": "A* search", "dijkstra": "unit-weight Dijkstra"},
           "signature": "def solve(grid, start, goal):", "dtype": "bf16"},
    "T2": {"family": "path", "suite": "t2", "default": "dijkstra",
           "catalogue": ["dijkstra", "bf_spfa", "bidijkstra", "floyd", "dial"],
           "display": {"dijkstra": "Dijkstra's algorithm", "bf_spfa": "Bellman-Ford or SPFA",
                       "bidijkstra": "bidirectional Dijkstra", "floyd": "Floyd-Warshall",
                       "dial": "Dial's bucket-queue algorithm"},
           "signature": "def solve(n, edges, s, t):", "dtype": "bf16"},
    "T03": {"family": "bench", "bench": "T03", "task_id": "T03_kth_smallest", "default": "full_sort",
            "analysis_set": ["full_sort", "quickselect", "size_k_heap", "counting_sort", "heapify_pop"],
            "signature": "def solve(nums, k):", "dtype": "fp8"},
    "T04": {"family": "bench", "bench": "T04", "task_id": "T04_substring_search", "default": "naive",
            "analysis_set": ["naive", "kmp", "rabin_karp", "builtin", "z_algorithm"],
            "signature": "def solve(haystack, needle):", "dtype": "fp8"},
    "T06": {"family": "bench", "bench": "T06", "task_id": "T06_find_duplicate", "default": "hash_set",
            "analysis_set": ["hash_set", "value_binary_search", "floyd", "sort_adjacent"],
            "signature": "def solve(nums):", "dtype": "fp8"},
    "T10": {"family": "bench", "bench": "T10", "task_id": "T10_connected_components", "default": "union_find",
            "analysis_set": ["bfs", "dfs", "union_find"],
            "signature": "def solve(n, edges):", "dtype": "fp8"},
}
PATH_TASKS = ["T1", "T2"]
BENCH_TASKS = ["T03", "T04", "T06", "T10"]
ALL_TASKS = PATH_TASKS + BENCH_TASKS
OFF_LABELS = ("other", "invalid")


def load_spec(task: str) -> dict[str, Any]:
    return json.loads((BENCH_DIR / TASKS[task]["task_id"] / "spec.json").read_text())


def _fill_bench() -> None:
    for t in BENCH_TASKS:
        s = load_spec(t)
        TASKS[t]["catalogue"] = [c["mode"] for c in s["catalogue"]]
        TASKS[t]["display"] = {c["mode"]: c["display_name"] for c in s["catalogue"]}
        TASKS[t]["description"] = s["description"]
        TASKS[t]["spec_text"] = s["spec_text"]
        TASKS[t]["aliases"] = s["aliases"]
        sig = s["signature"]
        TASKS[t]["signature"] = f"def {sig}:"


_fill_bench()

# ------------------------------------------------------------------------------------------------ thresholds
N_PER_TEMPLATE = 10            # 5 templates x 10 = 50 per walk step-round / LOS list
N_TWO_STEP_PER_TEMPLATE = 20   # 100 per task
WALK_MAX_STEPS = 5
WALK_MAX_EXTRA_ROUNDS = 2
LEAK_THRESHOLD = 0.05
REEMERGE_THRESHOLD = 0.20
STALL_MIN_NONVETOED = 20
STALL_VETOED_SHARE = 0.5
NGRAM_PRESENCE = 0.8
CO_VETO_SHARE = 0.5
C3_CAN_MIN = 0.7
C3_WILL_MAX = 0.10
C3_DISCONFIRM = 0.30
STEP0_MIN_DEFAULT = 0.8
OPENROUTER_OWN_CAP = 0.95      # stop at USD 0.95 of this artifact's own spend (plan: <= USD 1.0)


# ------------------------------------------------------------------------------------------------ utils
def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with Path(p).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_jsonl(p: Path) -> list[dict[str, Any]]:
    p = Path(p)
    if not p.exists():
        return []
    out = []
    for line in p.read_text().splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def append_jsonl(p: Path, rows: list[dict[str, Any]]) -> None:
    with Path(p).open("a") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


def write_json(p: Path, obj: Any) -> None:
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(obj, indent=1, default=str))


def cap_first(s: str) -> str:
    return s[:1].upper() + s[1:] if s else s


def setup_logging(name: str) -> None:
    from loguru import logger

    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    logger.add(str(LOGS / f"{name}.log"), rotation="30 MB", level="DEBUG")
