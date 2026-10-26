#!/usr/bin/env python3
"""Frozen protocol, paths and shared helpers. COPIED from the iteration-8 artifact (art_R-HSmXq2t97f, src/common.py) and
EXTENDED for iteration 9 TP-B (gen_plan_experiment_1_idx2): input paths, the USD 3.5 cap, the iteration-9 genesis hash
of the commitment chain, and the v9 protocol block at the end of this file (k order, cells, seeds, decoding).
Everything above the v9 block is the iteration-8 protocol, unchanged.

Iteration-8 docstring follows.
Frozen protocol, paths and shared helpers for the iteration-8 top-five ban screen (gen_plan_experiment_6_idx7).

One definition of: the T1 task spec, the 10-algorithm catalogue (display names, canonical order, judge definitions),
the alias table for forced prompts, the W1-W5 + P6/P7 ban templates, the screen configurations C1-C10, the selection
rule, hash-chained commitments, Wilson / Newcombe intervals, the deviation log and the OpenRouter cost ledger.
Prior-iteration files are read only from inputs/ (copied with sha256 at Stage 0) and vendor/exp9/ (harness +
labeller, copied read-only from ITER2 exp9).
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import math
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from loguru import logger

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
INPUTS = ROOT / "inputs"
VENDOR = ROOT / "vendor" / "exp9"
DATA = ROOT / "data"
RESULTS = ROOT / "results"
FIGS = ROOT / "figures"
PRED = ROOT / "predictions"
LOGS = ROOT / "logs"
CACHE = ROOT / "cache"
STATES = CACHE / "states"
COMMIT_LOG = ROOT / "commitments.log"
for _d in (INPUTS, DATA, RESULTS, FIGS, PRED, LOGS, STATES):
    _d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------------------------- prior-artifact inputs
# Iteration 9: the prior artifacts are read ONLY at Stage 0 (method.py stage0 and datasets) and copied into inputs/ with
# inputs/SHA256SUMS; every later stage reads inputs/. Each artifact is found by, in order (amendment commit #5):
# $TP_DEP_<KEY>; a sibling folder of this one named by its artifact id (the published repository's layout); the AI Inventor
# runs layout relative to this folder (where this run read them).
DEP_ARTIFACT_IDS = {
    "iter8": "art_R-HSmXq2t97f",     # ITER8 gen_art_experiment_44: protocol, labeller, C1-C8 rows, results
    "exp9": "art_IVZc3TWCeE9f",      # ITER2 gen_art_experiment_9: T1 task, harness, labeller, multi:TOP5 rows (C9)
    "exp31": "art_zNyBP6zieI5u",     # ITER6 gen_art_experiment_31: gemma-3-4b-it TOP5 rows (C10)
    "exp2": "art_D6Z0Snf09sFL",      # ITER1 gen_art_experiment_2: secondary hidden suite (41 cases)
    "dataset": "art_j3Rm_lr2nzR6",   # declared dependency: algorithm-choice source data (full_data_out.json)
}
RUNS_DIR = Path(os.environ.get("TP_RUNS_DIR", str(ROOT.parents[min(4, len(ROOT.parents) - 1)])))   # the runs/ folder
DEP_DEFAULT_PATHS = {   # relative to RUNS_DIR (amendment commit #4: no absolute server paths in published files)
    "iter8": "run_0oWBKrKEGsmU/3_invention_loop/iter_8/gen_art/gen_art_experiment_44",
    "exp9": "run_aRfWvcSWjssb/3_invention_loop/iter_2/gen_art/gen_art_experiment_9",
    "exp31": "run_0oWBKrKEGsmU/3_invention_loop/iter_6/gen_art/gen_art_experiment_31",
    "exp2": "run_4VFKidE1bxPG/3_invention_loop/iter_1/gen_art/gen_art_experiment_2",
    "dataset": "run_4VFKidE1bxPG/3_invention_loop/iter_1/gen_art/gen_art_dataset_1",
}


def _dep_path(key: str) -> Path:
    if os.environ.get(f"TP_DEP_{key.upper()}"):
        return Path(os.environ[f"TP_DEP_{key.upper()}"])
    sibling = ROOT.parent / DEP_ARTIFACT_IDS[key]
    return sibling if sibling.is_dir() else RUNS_DIR / DEP_DEFAULT_PATHS[key]


SRC_PATHS = {k: _dep_path(k) for k in DEP_DEFAULT_PATHS}
DS_FILE = SRC_PATHS["dataset"] / "full_data_out.json"   # read in place (96 MB); subsets copied to inputs/dataset/

# ---------------------------------------------------------------------------------------------- frozen task protocol
T1_DESCRIPTION = (
    "Task: write a Python function solve(grid, start, goal) that finds a path between two cells of a grid. "
    "grid is a list of equal-length strings with between 1 and 30 rows and between 1 and 30 columns; "
    "the character . is a free cell and the character # is a wall. start and goal are (row, col) tuples of "
    "0-based indices. A move goes to one of the 4 orthogonal neighbours (up, down, left, right) and may not "
    "leave the grid or enter a wall. Return a list of (row, col) tuples that begins with start, ends with goal, "
    "and in which consecutive cells are neighbours and every cell is free. Any valid path is accepted; it does "
    "not have to be the shortest. If start equals goal and the cell is free, return [start]. If no path exists, "
    "or start or goal is a wall, return []."
)
FORMAT_TEXT = (
    "Use only the Python standard library. Return only one ```python code block containing the function solve "
    "and any helpers, with no example usage and no explanation."
)

CANON_ORDER = ["bfs", "dfs", "bibfs", "iddfs", "astar", "gbfs", "dijkstra_unit", "idastar", "jps", "biastar"]
DISPLAY = {
    "bfs": "breadth-first search (BFS)", "dfs": "depth-first search (DFS)", "bibfs": "bidirectional BFS",
    "iddfs": "iterative deepening DFS (IDDFS)", "astar": "A* search", "gbfs": "greedy best-first search",
    "dijkstra_unit": "unit-weight Dijkstra", "idastar": "IDA* search", "jps": "jump point search",
    "biastar": "bidirectional A* search",
}
SHORT = {"bfs": "BFS", "dfs": "DFS", "bibfs": "BiBFS", "iddfs": "IDDFS", "astar": "A*", "gbfs": "GBFS",
         "dijkstra_unit": "Dijkstra(u)", "idastar": "IDA*", "jps": "JPS", "biastar": "BiA*", "other": "other",
         "no_code": "no code", "invalid": "invalid"}
FILL_ORDER = ["bfs", "dfs", "gbfs", "iddfs", "astar"]
GATE_FAILED_CLASSES = ("dijkstra_unit", "jps", "biastar")   # iteration-2 gold gate < 3/4
MODE_DEFINITIONS = {
    "bfs": "breadth-first search: explores cells in order of distance from start with a FIFO queue (deque.popleft, "
           "list.pop(0), queue.Queue) or level-by-level frontier lists; one search direction; no priority queue.",
    "dfs": "depth-first search: follows one branch as deep as possible with recursion or a LIFO stack, with a "
           "visited set; a single pass with no depth limit and no restarts (neighbour ordering by distance is "
           "still DFS).",
    "bibfs": "bidirectional BFS: two breadth-first searches, one from start and one from goal, expanded alternately "
             "until the frontiers meet; the path is joined at the meeting cell; no heuristic, no heap.",
    "iddfs": "iterative deepening DFS: repeated depth-limited depth-first searches with an increasing depth limit "
             "(0, 1, 2, ...) until the goal is found; no heuristic bound.",
    "astar": "A* search: a priority queue (heap) ordered by f = g + h, cost so far plus a heuristic such as the "
             "Manhattan distance to the goal; one search direction.",
    "gbfs": "greedy best-first search: a priority queue ordered by the heuristic h alone (e.g. Manhattan distance "
            "to the goal), ignoring the cost so far; one search direction.",
    "dijkstra_unit": "Dijkstra's algorithm on the unit-weight grid: a priority queue (heap) ordered by distance from "
                     "start only, with no heuristic toward the goal.",
    "idastar": "IDA*: repeated depth-first searches bounded by f = g + h (heuristic, e.g. Manhattan), raising the "
               "bound to the smallest f that exceeded it, until the goal is found.",
    "jps": "jump point search: A*-style search that 'jumps' along straight lines (and, for 8-connected variants, "
           "diagonals) and adds cells to the open list only at jump points (turning points next to walls, or the "
           "goal), instead of adding every neighbour.",
    "biastar": "bidirectional A*: two A* searches, forward from start toward goal and backward from goal toward "
               "start, each with its own heuristic-ordered heap, stopping when the frontiers meet.",
}
# Known algorithms outside the catalogue (an adjudicated 'other' may resolve to one of these -> 'known outside').
KNOWN_OUTSIDE = ["bidirectional Dijkstra", "beam search", "random walk", "wall following", "flood fill / wavefront "
                 "(Lee algorithm)", "union-find connectivity + path reconstruction", "Bellman-Ford / SPFA on the grid",
                 "dynamic programming / value iteration over cells", "Floyd-Warshall"]

# Alias table for forced prompts (3 aliases per algorithm; plan, Stage 1).
ALIAS_TABLE: dict[str, list[str]] = {
    "bfs": ["breadth-first search (BFS)", "BFS", "a breadth-first search"],
    "dfs": ["depth-first search (DFS)", "DFS", "a depth-first search"],
    "bibfs": ["bidirectional BFS", "bidirectional breadth-first search",
              "a breadth-first search run from both start and goal"],
    "iddfs": ["iterative deepening DFS (IDDFS)", "IDDFS", "iterative deepening depth-first search"],
    "astar": ["A* search", "the A* algorithm", "A* search with a Manhattan-distance heuristic"],
    "gbfs": ["greedy best-first search", "greedy best-first search with a Manhattan heuristic",
             "a purely heuristic best-first search"],
    "dijkstra_unit": ["unit-weight Dijkstra", "Dijkstra's algorithm with unit edge weights",
                      "a priority-queue Dijkstra search"],
    "idastar": ["IDA* search", "iterative deepening A* (IDA*)", "IDA* with a Manhattan heuristic"],
    "jps": ["jump point search", "JPS", "jump point search (JPS) on a uniform-cost grid"],
    "biastar": ["bidirectional A* search", "bidirectional A*", "A* run from both start and goal at once"],
}
# Short forms for the name-free re-implementation regex (case-insensitive substrings / word patterns).
SHORT_FORMS: dict[str, list[str]] = {
    "bfs": [r"\bbfs\b", r"breadth[-_ ]?first"],
    "dfs": [r"\bdfs\b", r"depth[-_ ]?first"],
    "bibfs": [r"bidirectional", r"\bbi[-_ ]?bfs\b", r"\bbidir"],
    "iddfs": [r"\biddfs\b", r"iterative[-_ ]?deepening"],
    "astar": [r"a\*", r"\ba[-_ ]?star\b", r"\bastar\b"],
    "gbfs": [r"greedy", r"best[-_ ]?first", r"\bgbfs\b"],
    "dijkstra_unit": [r"dijkstra"],
    "idastar": [r"ida\*", r"\bida[-_ ]?star\b", r"\bidastar\b"],
    "jps": [r"\bjps\b", r"jump[-_ ]?point"],
    "biastar": [r"bidirectional", r"\bbi[-_ ]?a[-_ ]?star\b", r"\bbidir"],
}

W_TEMPLATES: dict[str, str] = {
    "W1": "Do not use {X} for this task.", "W2": "Your solution must not rely on {X}.", "W3": "Avoid {X} entirely.",
    "W4": "{X} is not allowed here.", "W5": "Write a correct solution that does not use {X}.",
    "P6": "None of the following may be used in your solution: {X}.", "P7": "Solve this task without using {X}.",
}
# Rotation index of the name order: W1..W5 rotate by w-1 (iteration 2); P6/P7 continue the cycle (5, 6 mod 5).
W_ROT = {"W1": 0, "W2": 1, "W3": 2, "W4": 3, "W5": 4, "P6": 5, "P7": 6}
SCREEN_SLOTS = [("W1", 17), ("W2", 17), ("W3", 16)]                 # slots 0-16, 17-33, 34-49
CONFIRM_SLOTS = [("W4", 13), ("W5", 13), ("P6", 12), ("P7", 12)]

DECODING = {"temperature": 1.0, "top_p": 1.0, "top_k": "off", "max_tokens_off": 1536, "max_tokens_on": 9728,
            "local_think_budget": 8192, "local_answer_budget": 1536}

# ---------------------------------------------------------------------------------------------- configurations
CONFIGS: dict[str, dict[str, Any]] = {
    "C1": {"name": "qwen3-8b-think", "family": "Qwen3", "params_b": 8.2, "engine": "local-vllm",
           "model": "Qwen/Qwen3-8B-FP8", "hf_repo": "Qwen/Qwen3-8B", "thinking": True, "n_base": 30, "n_ban": 50,
           "provider": "local vLLM 0.11.0 (eager)", "quantization": "fp8 (official FP8 checkpoint, W8A16 Marlin)",
           "local": True},
    "C2": {"name": "llama-3.1-8b", "family": "Llama-3.1", "params_b": 8.0, "engine": "openrouter",
           "model": "meta-llama/llama-3.1-8b-instruct", "hf_repo": "meta-llama/Llama-3.1-8B-Instruct",
           "thinking": False, "n_base": 100, "n_ban": 50, "provider": None, "quantization": "bf16", "local": False},
    "C3": {"name": "qwen3-14b-off", "family": "Qwen3", "params_b": 14.8, "engine": "openrouter",
           "model": "qwen/qwen3-14b", "hf_repo": "Qwen/Qwen3-14B", "thinking": False, "n_base": 100, "n_ban": 50,
           "provider": "DeepInfra", "quantization": "fp8", "local": False},
    "C4": {"name": "qwen3-14b-on", "family": "Qwen3", "params_b": 14.8, "engine": "openrouter",
           "model": "qwen/qwen3-14b", "hf_repo": "Qwen/Qwen3-14B", "thinking": True, "n_base": 100, "n_ban": 50,
           "provider": "DeepInfra", "quantization": "fp8", "local": False},
    "C5": {"name": "qwen3-32b-off", "family": "Qwen3", "params_b": 32.8, "engine": "openrouter",
           "model": "qwen/qwen3-32b", "hf_repo": "Qwen/Qwen3-32B", "thinking": False, "n_base": 100, "n_ban": 50,
           "provider": "DeepInfra", "quantization": "fp8", "local": False},
    "C6": {"name": "qwen3-32b-on", "family": "Qwen3", "params_b": 32.8, "engine": "openrouter",
           "model": "qwen/qwen3-32b", "hf_repo": "Qwen/Qwen3-32B", "thinking": True, "n_base": 100, "n_ban": 50,
           "provider": "DeepInfra", "quantization": "fp8", "local": False},
    # C7 planned as google/gemma-3-12b-it (DeepInfra bf16); its endpoints timed out (504 after 300 s) in the smoke
    # test and no other bf16/fp8 provider exists -> same-family substitute (deviation D11, decided before commit #1).
    "C7": {"name": "gemma-3-27b-it", "family": "Gemma-3", "params_b": 27.4, "engine": "openrouter",
           "model": "google/gemma-3-27b-it", "hf_repo": "google/gemma-3-27b-it", "thinking": False, "n_base": 100,
           "n_ban": 50, "provider": "DeepInfra", "quantization": "fp8", "local": False},
    "C8": {"name": "qwen2.5-coder-32b", "family": "Qwen2.5-Coder", "params_b": 32.8, "engine": "openrouter",
           "model": "qwen/qwen-2.5-coder-32b-instruct", "hf_repo": "Qwen/Qwen2.5-Coder-32B-Instruct",
           "thinking": False, "n_base": 100, "n_ban": 50, "provider": "Cloudflare", "quantization": "unknown",
           "local": False},
}
CARRIED: dict[str, dict[str, Any]] = {
    "C9": {"name": "qwen3-8b-off (carried)", "family": "Qwen3", "params_b": 8.2, "engine": "local-vllm bf16 (iter 2)",
           "source": "art_IVZc3TWCeE9f (ITER2 exp9) TOP5 condition", "thinking": False},
    "C10": {"name": "gemma-3-4b-it (carried)", "family": "Gemma-3", "params_b": 4.3, "engine": "carried",
            "source": "art_zNyBP6zieI5u", "thinking": False},
}
# Precision ladder for states of a selected model (Stage 6 commit #3).
STATE_CHECKPOINTS = {
    "C1": {"repo": "Qwen/Qwen3-8B", "precision": "bf16"},
    "C2": {"repo": "meta-llama/Llama-3.1-8B-Instruct", "precision": "bf16"},
    "C3": {"repo": "Qwen/Qwen3-14B", "precision": "int8"},
    "C4": {"repo": "Qwen/Qwen3-14B", "precision": "int8"},
    "C5": {"repo": "unsloth/Qwen3-32B-bnb-4bit", "precision": "nf4"},
    "C6": {"repo": "unsloth/Qwen3-32B-bnb-4bit", "precision": "nf4"},
    "C7": {"repo": "unsloth/gemma-3-27b-it-bnb-4bit", "precision": "nf4"},
    "C8": {"repo": "unsloth/Qwen2.5-Coder-32B-Instruct-bnb-4bit", "precision": "nf4"},
}
# Hugging Face revisions actually used (snapshot hashes of the run's shared cache).
REVISIONS = {"Qwen/Qwen3-8B": "b968826d9c46dd6066d109eabc6255188de91218",
             "Qwen/Qwen3-8B-FP8": "220b46e3b2180893580a4454f21f22d3ebb187d3",
             "unsloth/Qwen3-32B-bnb-4bit": "7f721e74a6a8cc9ee352f7e49303a2c1705f9083"}
DEPTH_RANGE = (0.30, 0.70)
SELECTION = {"threshold_share_cs": 0.20, "tie_window": 0.02,
             "tie_breaks": ["higher Wilson lower bound", "fewer parameters", "local engine"]}
COST_CAP_USD = float(os.environ.get("TP_COST_CAP", "3.5"))   # iteration 9: min(3.5, 0.35 * phase remaining)
BUDGET_MSG = "AI Inventor per-run OpenRouter budget"
JUDGES = {"a": "google/gemini-2.5-flash-lite", "b": "deepseek/deepseek-chat-v3.1",
          "c": ["moonshotai/kimi-k2", "mistralai/mistral-medium-3.1"]}
# Gate outcome (results/judge_gate.json): gemini-2.5-flash-lite 7/10 FAILED, deepseek-chat-v3.1 9/10, kimi-k2 10/10.
# Adjudication pair = the two gated judges; third = mistral-medium-3.1 if it passes its gate (deviation D12).
ADJ_PAIR = ["deepseek/deepseek-chat-v3.1", "moonshotai/kimi-k2"]
ADJ_THIRD = "mistralai/mistral-medium-3.1"


def spec_text() -> str:
    return T1_DESCRIPTION + "\n\n" + FORMAT_TEXT


# ---------------------------------------------------------------------------------------------- logging + io
def setup_logging(name: str) -> None:
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    logger.add(str(LOGS / f"{name}.log"), rotation="30 MB", level="DEBUG")


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with Path(p).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _json_default(o: Any) -> Any:
    try:
        import numpy as np

        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, np.floating):
            return None if not np.isfinite(o) else float(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
        if isinstance(o, np.bool_):
            return bool(o)
    except ImportError:
        pass
    if isinstance(o, (set, frozenset)):
        return sorted(o)
    if isinstance(o, Path):
        return str(o)
    raise TypeError(f"not JSON serialisable: {type(o)}")


def read_json(p: Path) -> Any:
    return json.loads(Path(p).read_text())


def write_json(p: Path, obj: Any, indent: int | None = 1) -> None:
    p = Path(p)
    tmp = p.with_suffix(p.suffix + f".tmp{os.getpid()}")
    tmp.write_text(json.dumps(obj, indent=indent, ensure_ascii=False, default=_json_default))
    tmp.replace(p)


def read_jsonl(p: Path) -> list[dict[str, Any]]:
    p = Path(p)
    rows: list[dict[str, Any]] = []
    if not p.exists():
        return rows
    with p.open() as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    logger.warning(f"skipping malformed jsonl line in {p.name}")
    return rows


def write_jsonl(p: Path, rows: Iterable[dict[str, Any]]) -> None:
    p = Path(p)
    tmp = p.with_suffix(p.suffix + f".tmp{os.getpid()}")
    with tmp.open("w") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False, default=_json_default) + "\n")
    tmp.replace(p)


def append_jsonl(p: Path, row: dict[str, Any]) -> None:
    with Path(p).open("a") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        fh.write(json.dumps(row, ensure_ascii=False, default=_json_default) + "\n")
        fcntl.flock(fh, fcntl.LOCK_UN)


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=_json_default)


def trunc(s: Any, n: int = 300) -> str:
    s = str(s)
    return s if len(s) <= n else s[:n] + f"...[+{len(s) - n}]"


# ---------------------------------------------------------------------------------------------- statistics
Z95 = 1.959963984540054


def wilson_ci(k: int, n: int, z: float = Z95) -> tuple[float, float]:
    if n <= 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, centre - half), min(1.0, centre + half))


def wilson_upper_one_sided(k: int, n: int) -> float:
    """One-sided 95% upper bound (Wilson with z = 1.645)."""
    return wilson_ci(k, n, z=1.6448536269514722)[1]


def newcombe_diff(k1: int, n1: int, k2: int, n2: int) -> tuple[float, float, float]:
    """Newcombe hybrid-score 95% interval for p1 - p2 (method 10)."""
    if n1 <= 0 or n2 <= 0:
        return (float("nan"), float("nan"), float("nan"))
    p1, p2 = k1 / n1, k2 / n2
    l1, u1 = wilson_ci(k1, n1)
    l2, u2 = wilson_ci(k2, n2)
    d = p1 - p2
    lo = d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2)
    hi = d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)
    return (d, lo, hi)


# ---------------------------------------------------------------------------------------------- commitments
GENESIS = hashlib.sha256(b"iter9_TP-B").hexdigest()   # iteration 9: genesis prev = sha256('iter9_TP-B')


def commit(payload_path: Path, label: str, note: str = "") -> dict[str, Any]:
    """Append '{i, label, utc, prev_line_sha256, payload_sha256, payload_path, note}' to commitments.log.
    Every line chains on the sha256 of the previous line's exact text (GENESIS = sha256('iter9_TP-B') for line 0)."""
    payload_path = Path(payload_path)
    lines = COMMIT_LOG.read_text().splitlines() if COMMIT_LOG.exists() else []
    prev = sha256_text(lines[-1]) if lines else GENESIS
    psha = sha256_file(payload_path)
    entry = {"i": len(lines), "label": label, "utc": utc_now(), "prev_line_sha256": prev, "payload_sha256": psha,
             "payload_path": str(payload_path.relative_to(ROOT)), "note": note}
    with COMMIT_LOG.open("a") as fh:
        fh.write(json.dumps(entry, sort_keys=True) + "\n")
    logger.info(f"COMMIT {label}: {entry['payload_path']} sha256={psha[:16]} line {entry['i']}")
    return entry


def verify_chain() -> tuple[bool, list[str], list[dict[str, Any]]]:
    problems: list[str] = []
    if not COMMIT_LOG.exists():
        return False, ["no commitments.log"], []
    lines = COMMIT_LOG.read_text().splitlines()
    prev = GENESIS
    entries = []
    for i, ln in enumerate(lines):
        e = json.loads(ln)
        entries.append(e)
        if e["prev_line_sha256"] != prev:
            problems.append(f"line {i}: prev-line hash mismatch")
        p = ROOT / e["payload_path"]
        if not p.exists():
            problems.append(f"line {i}: payload missing {e['payload_path']}")
        elif sha256_file(p) != e["payload_sha256"]:
            problems.append(f"line {i}: payload hash mismatch {e['payload_path']}")
        prev = sha256_text(ln)
    return (not problems, problems, entries)


def commit_time(label: str) -> str | None:
    if not COMMIT_LOG.exists():
        return None
    for ln in COMMIT_LOG.read_text().splitlines():
        e = json.loads(ln)
        if e["label"] == label:
            return e["utc"]
    return None


# ---------------------------------------------------------------------------------------------- deviations, costs
def deviation(code: str, text: str) -> None:
    p = RESULTS / "deviations.json"
    with (RESULTS / ".dev.lock").open("w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        devs = json.loads(p.read_text()) if p.exists() else []
        if not any(d["code"] == code for d in devs):
            devs.append({"code": code, "text": text, "utc": utc_now()})
            write_json(p, devs)
            logger.warning(f"DEVIATION {code}: {text}")
        fcntl.flock(lk, fcntl.LOCK_UN)


COST_FILE = RESULTS / "costs.json"


def add_cost(purpose: str, usd: float, refused: bool = False) -> float:
    """Running ledger shared by every process of this artifact (file-locked)."""
    with (RESULTS / ".cost.lock").open("w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        c = json.loads(COST_FILE.read_text()) if COST_FILE.exists() else {"total_usd": 0.0, "by_purpose": {},
                                                                           "n_calls": 0, "budget_refusals": 0}
        c["total_usd"] = round(c["total_usd"] + float(usd or 0.0), 6)
        c["by_purpose"][purpose] = round(c["by_purpose"].get(purpose, 0.0) + float(usd or 0.0), 6)
        c["n_calls"] += 1
        c["budget_refusals"] += int(refused)
        c["updated_utc"] = utc_now()
        write_json(COST_FILE, c)
        fcntl.flock(lk, fcntl.LOCK_UN)
        return c["total_usd"]


def total_cost() -> float:
    return float(read_json(COST_FILE)["total_usd"]) if COST_FILE.exists() else 0.0


def timing(key: str, seconds: float, units: int, note: str = "") -> None:
    append_jsonl(RESULTS / "timing.jsonl", {"key": key, "seconds": round(seconds, 2), "units": units,
                                            "sec_per_unit": round(seconds / max(units, 1), 3), "note": note,
                                            "utc": utc_now()})


# ---------------------------------------------------------------------------------------------- misc helpers
def cap_first(s: str) -> str:
    return s[:1].upper() + s[1:] if s else s


def rotate(xs: list[Any], k: int) -> list[Any]:
    if not xs:
        return xs
    k %= len(xs)
    return xs[k:] + xs[:k]


def join_names_or(names: list[str]) -> str:
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + " or " + names[-1]


def alias_regex(keys: Iterable[str]) -> re.Pattern:
    """Case-insensitive regex matching any alias (table + short forms) of the given algorithms."""
    pats: list[str] = []
    for k in keys:
        pats += [re.escape(a.lower()) for a in ALIAS_TABLE[k]]
        pats += SHORT_FORMS[k]
    return re.compile("|".join(f"(?:{p})" for p in pats), re.IGNORECASE)


def all_configs() -> dict[str, dict[str, Any]]:
    return CONFIGS


# ================================================================================================ iteration-9 v9 block
# TP-B protocol constants (gen_plan_experiment_1_idx2). Committed in predictions/commit1a.json.
K_ORDER = ["bfs", "dfs", "iddfs", "astar", "gbfs"]          # the direction's cumulative order (deviation D-order)
LITERAL5 = sorted(K_ORDER, key=CANON_ORDER.index)            # = iteration 8's B_c for every configuration
DECODING_V9 = {"temperature": 1.0, "top_p": 1.0, "top_k": "off", "max_tokens": 12288, "thinking": True}
CAP_V9_USD = 3.5
# Cells: id -> (model key, kind, k or set, templates/slots). Seeds = 1000 * cell_index + slot + 1.
MODELS_V9: dict[str, dict[str, Any]] = {
    "q32": {"model": "qwen/qwen3-32b", "family": "Qwen3", "thinking": True, "params_b": 32.8,
            "provider": {"order": ["DeepInfra"], "allow_fallbacks": False, "quantizations": ["fp8"]},
            "quantization": "fp8", "name": "Qwen3-32B thinking (DeepInfra fp8)"},
    "q14": {"model": "qwen/qwen3-14b", "family": "Qwen3", "thinking": True, "params_b": 14.8,
            "provider": {"order": ["DeepInfra"], "allow_fallbacks": False, "quantizations": ["fp8"]},
            "quantization": "fp8", "name": "Qwen3-14B thinking (DeepInfra fp8)"},
    "q235": {"model": "qwen/qwen3-235b-a22b-thinking-2507", "family": "Qwen3-2507", "thinking": True,
             "params_b": 235.0, "provider": None, "quantization": "provider-reported",
             "name": "Qwen3-235B-A22B-Thinking-2507"},
    "gptoss": {"model": "openai/gpt-oss-120b", "family": "gpt-oss", "thinking": True, "params_b": 117.0,
               "provider": None, "quantization": "provider-reported", "reasoning_effort": "medium",
               "name": "gpt-oss-120b (reasoning effort medium)"},
}
