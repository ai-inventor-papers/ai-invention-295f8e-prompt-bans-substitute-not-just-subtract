#!/usr/bin/env python3
"""Frozen protocol constants and shared helpers for the five-name ban study (iteration 2, artifact gen_plan_experiment_3_idx4).

Everything that defines the protocol (task texts, the 10-algorithm grid catalogue, the 5-algorithm shortest-path
catalogue, display names, W1-W5 templates of shared protocol v2, thresholds, the hash-chain commit helper) lives here
so every stage reads one frozen definition. The labeller modules in labeller_ext/ import their catalogue from here.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from loguru import logger

ROOT = Path(__file__).resolve().parent
CANON = ROOT / "canon"
TASK_DIR = ROOT / "tasks"
PROMPT_DIR = ROOT / "prompts"
DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "results"
FIG_DIR = ROOT / "figures"
LOG_DIR = ROOT / "logs"
LABEL_DIR = ROOT / "labeller_ext"
STATES_DIR = ROOT / "states"
COMMIT_LOG = ROOT / "commitments.log"

for _d in (PROMPT_DIR, DATA_DIR, RESULTS_DIR, FIG_DIR, LOG_DIR, STATES_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# Declared dependency art_j3Rm_lr2nzR6 (gen_art_dataset_1, the algorithm-choice source data): read through ONE constant,
# overridable with MB_DEP_DATASET; by default the published sibling folder next to this artifact.
DS_FILE = Path(os.environ.get("MB_DEP_DATASET", str(ROOT.parent / "dataset-1/src" / "full_data_out.json")))

MODEL_ID = os.environ.get("MB_MODEL", "Qwen/Qwen3-8B")
MODEL_REVISION = "b968826d9c46dd6066d109eabc6255188de91218"
SERVED_NAME = "qwen3-multiban"
VLLM_PORT = int(os.environ.get("MB_VLLM_PORT", "8019"))
VLLM_URL = f"http://127.0.0.1:{VLLM_PORT}"
JUDGE_MODEL = "openai/gpt-4.1-mini"
GOLD_JUDGES = ("openai/gpt-4.1-mini", "google/gemini-2.5-flash")
GOLD_TIEBREAK = "deepseek/deepseek-chat-v3.1"
JUDGE_CAP_USD = 0.70

TASKS = ("t1", "t2")
TASK_DATASET_NAME = {"t1": "T1_grid_path", "t2": "T2_weighted_shortest_path"}
TASK_SUBDIR = {"t1": "t1_grid", "t2": "t2_wsp"}

# Task text: verbatim copy of iteration-1 exp1 (asserted equal to canon/prompts/conditions.json['spec'] at freeze time).
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
T2_DESCRIPTION = (
    "Task: write a Python function solve(n, edges, s, t) that returns the length of the shortest path from node "
    "s to node t in a directed weighted graph. Nodes are numbered 0 to n-1 with 1 <= n <= 100. edges is a list "
    "of (u, v, w) tuples, each a directed edge from u to v with integer weight 0 <= w <= 100; there are at most "
    "600 edges and the graph may contain cycles, self-loops and parallel edges. Return the minimum total weight "
    "of a path from s to t as an int, 0 if s equals t, and -1 if t cannot be reached from s."
)
FORMAT_TEXT = (
    "Use only the Python standard library. Return only one ```python code block containing the function solve "
    "and any helpers, with no example usage and no explanation."
)
DESCRIPTION = {"t1": T1_DESCRIPTION, "t2": T2_DESCRIPTION}


def spec_text(task: str) -> str:
    """SPEC = DESCRIPTION + blank line + FORMAT."""
    return DESCRIPTION[task] + "\n\n" + FORMAT_TEXT


# Catalogues (key -> frozen display name), in CANONICAL LIST ORDER.
CATALOGUE: dict[str, dict[str, str]] = {
    "t1": {
        "bfs": "breadth-first search (BFS)",
        "dfs": "depth-first search (DFS)",
        "bibfs": "bidirectional BFS",
        "iddfs": "iterative deepening DFS (IDDFS)",
        "astar": "A* search",
        "gbfs": "greedy best-first search",
        "dijkstra_unit": "unit-weight Dijkstra",
        "idastar": "IDA* search",
        "jps": "jump point search",
        "biastar": "bidirectional A* search",
    },
    "t2": {
        "dijkstra": "Dijkstra's algorithm",
        "bf_spfa": "Bellman-Ford or SPFA",
        "bidijkstra": "bidirectional Dijkstra",
        "floyd": "Floyd-Warshall",
        "dial": "Dial's bucket-queue algorithm",
    },
}
MODES = {t: list(CATALOGUE[t].keys()) for t in TASKS}
NEW_T1 = ("gbfs", "idastar", "jps", "biastar")
OTHER = "other"
UNKNOWN = "unknown"
NO_CODE = "no_code"
SHORT = {"bfs": "BFS", "dfs": "DFS", "bibfs": "BiBFS", "iddfs": "IDDFS", "astar": "A*", "gbfs": "GBFS",
         "dijkstra_unit": "Dijkstra(u)", "idastar": "IDA*", "jps": "JPS", "biastar": "BiA*",
         "dijkstra": "Dijkstra", "bf_spfa": "BF/SPFA", "bidijkstra": "BiDijkstra", "floyd": "Floyd",
         "dial": "Dial", "other": "other", "unknown": "unknown", "no_code": "no code"}

# One-line definitions shown to the strategy-blind judge (never the condition).
MODE_DEFINITIONS: dict[str, dict[str, str]] = {
    "t1": {
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
    },
    "t2": {
        "dijkstra": "Dijkstra's algorithm: a single priority queue (heap) of tentative distances from s, popping the "
                    "smallest distance each time (lazy deletion or decrease-key variants), one search direction.",
        "bf_spfa": "Bellman-Ford (repeated relaxation passes over all edges, up to n-1 rounds, possibly with early exit) "
                   "or SPFA (a FIFO queue of nodes whose distance improved, often with an in-queue flag).",
        "bidijkstra": "bidirectional Dijkstra: two Dijkstra searches, forward from s on the graph and backward from t on "
                      "the reversed graph, with a meeting/stopping rule.",
        "floyd": "Floyd-Warshall: all-pairs shortest paths with a triple loop over k, i, j updating "
                 "dist[i][j] = min(dist[i][j], dist[i][k] + dist[k][j]).",
        "dial": "Dial's algorithm: Dijkstra with a bucket queue, i.e. an array or dict of buckets indexed by distance, "
                "scanned in increasing distance order instead of a binary heap.",
    },
}
EXTENDED_CATALOGUE = {
    "t1": ["bidirectional Dijkstra on the grid", "beam search", "random walk", "wall following"],
    "t2": ["DAG dynamic programming", "Johnson's algorithm", "A* with a non-zero heuristic"],
}

# Shared protocol v2: frozen W1-W5 (ban, mention, neutral) templates.
W_TEMPLATES: list[dict[str, str]] = [
    {"ban": "Do not use {X} for this task.", "mention": "You could use {X} for this task.",
     "neutral": "Do not use {N} for this task."},
    {"ban": "Your solution must not rely on {X}.", "mention": "Your solution may rely on {X}.",
     "neutral": "Your solution must not rely on {N}."},
    {"ban": "Avoid {X} entirely.", "mention": "Consider {X} first.", "neutral": "Avoid {N} entirely."},
    {"ban": "{X} is not allowed here.", "mention": "{X} is allowed here.", "neutral": "{N} is not allowed here."},
    {"ban": "Write a correct solution that does not use {X}.", "mention": "Write a correct solution that may use {X}.",
     "neutral": "Write a correct solution that does not use {N}."},
]
NONCE_NAME = "the Zorblax method"
PAD_FILLER = " Thanks."

# Forced paraphrases: the 5 exp1 forced templates are read from canon/prompts/conditions.json; these 5 are new.
# 'Solve this task with {j}.' duplicates exp1's third forced template verbatim, so it is replaced by
# 'Apply {j} to solve this task.' (logged deviation D-forced-dup).
FORCED_NEW = ["Apply {X} to solve this task.", "Your solution should implement {X}.", "Please write {X} for this task.",
              "Base your solution on {X}.", "Use {X} as the algorithm here."]
FORCED_NEW_PLANNED_DUPLICATE = "Solve this task with {X}."
DESCRIPTIVE: dict[str, str] = {
    "bidijkstra": "run Dijkstra forward from s and backward from t over reversed edges at the same time and stop when "
                  "the two searches meet",
    "biastar": "run A* forward from start and backward from goal at the same time, each guided by the Manhattan "
               "distance to its own target, and stop when the frontiers meet",
    "jps": "on this 4-connected grid, jump in straight lines and add a cell to the open list only at turning points "
           "next to walls or at the goal",
    "idastar": "repeat a depth-first search bounded by f = g + Manhattan distance, raising the bound to the smallest f "
               "that exceeded it",
    "gbfs": "always expand the frontier cell with the smallest Manhattan distance to the goal, ignoring the cost so far",
    "iddfs": "repeat a depth-limited DFS with limits 0, 1, 2, ... until the goal is found",
    "dial": "Dijkstra with an array of buckets indexed by tentative distance instead of a heap",
}

# Alias lexicon (case-insensitive substrings) for disguise and scrub steps; keyed by mechanism family.
ALIASES: dict[str, list[str]] = {
    "bfs": ["bfs", "breadth-first", "breadth first", "breadth_first"],
    "dfs": ["dfs", "depth-first", "depth first", "depth_first"],
    "astar": ["a*", "a-star", "astar", "a_star"],
    "gbfs": ["greedy", "best-first", "best first", "best_first"],
    "iddfs": ["iddfs", "iterative deepening", "iterative_deepening"],
    "idastar": ["ida*", "ida_star", "idastar"],
    "jps": ["jps", "jump point", "jump_point"],
    "bidir": ["bidirectional", "bidir"],
    "dijkstra": ["dijkstra"],
    "bf_spfa": ["bellman", "ford", "spfa"],
    "floyd": ["floyd", "warshall"],
    "dial": ["dial", "bucket queue", "bucket_queue"],
}
# Which alias families name each mechanism (a program 'names its own mechanism' if any family matches).
MECH_ALIAS_FAMILIES: dict[str, list[str]] = {
    "bfs": ["bfs"], "dfs": ["dfs"], "bibfs": ["bidir"], "iddfs": ["iddfs"], "astar": ["astar"], "gbfs": ["gbfs"],
    "dijkstra_unit": ["dijkstra"], "idastar": ["idastar"], "jps": ["jps"], "biastar": ["bidir"],
    "dijkstra": ["dijkstra"], "bf_spfa": ["bf_spfa"], "bidijkstra": ["bidir"], "floyd": ["floyd"], "dial": ["dial"],
}

THRESHOLDS = {"keep_forced_share": 0.70, "smoke_descriptive_min": 7, "gate_avoidance": 0.50, "gate_min_nonbanned": 20,
              "uniform_mix": 0.05, "other_floor": 0.02, "ess_flag": 5.0, "gold_accept": 36, "gold_per_algo_min": 3}
DECODING = {"temperature": 1.0, "top_p": 1.0, "top_k": -1, "max_tokens": 1024, "thinking": "off"}
DECODING_TAG = "T1.0_topp1.0_topk-off_max1024_thinkoff"
LAYERS = list(range(20, 29))
GEN_POSITIONS = ("g8", "g16", "g32", "pre")
N_PER_TEMPLATE = 20
M_MAX = 30


def setup_logging(name: str) -> None:
    """loguru: stdout INFO + rotating DEBUG file sink per stage."""
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    logger.add(str(LOG_DIR / f"{name}.log"), rotation="30 MB", level="DEBUG")


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def sha256_file(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def request_seed(*parts: Any) -> int:
    """Per-request seed = int(sha256('task|condition|template|paraphrase')[:8], 16)."""
    return int(hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()[:8], 16)


def read_jsonl(p: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    p = Path(p)
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
    tmp = p.with_suffix(p.suffix + ".tmp")
    with tmp.open("w") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False, default=_json_default) + "\n")
    tmp.replace(p)


def write_json(p: Path, obj: Any, indent: int | None = 1, sort_keys: bool = False) -> None:
    p = Path(p)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=indent, sort_keys=sort_keys, ensure_ascii=False, default=_json_default))
    tmp.replace(p)


def read_json(p: Path) -> Any:
    return json.loads(Path(p).read_text())


def _json_default(o: Any) -> Any:
    try:
        import numpy as np  # local import: keeps the sandbox runner free of numpy

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


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=_json_default)


def wilson_ci(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if n <= 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, centre - half), min(1.0, centre + half))


def join_names_or(names: list[str]) -> str:
    """'A', 'A or B', 'A, B or C' (order preserved)."""
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + " or " + names[-1]


def cap_first(s: str) -> str:
    return s[:1].upper() + s[1:] if s else s


def rotate(xs: list[Any], k: int) -> list[Any]:
    if not xs:
        return xs
    k %= len(xs)
    return xs[k:] + xs[:k]


def logsumexp(xs: list[float]) -> float:
    if not xs:
        return float("-inf")
    m = max(xs)
    if m == float("-inf"):
        return m
    return m + math.log(sum(math.exp(x - m) for x in xs))


def logmeanexp(xs: list[float]) -> float:
    return logsumexp(xs) - math.log(len(xs)) if xs else float("nan")


# ------------------------------------------------------------------------------------------------ commitments
def read_commitments() -> list[dict[str, Any]]:
    return read_jsonl(COMMIT_LOG)


def commit_payload(payload_path: Path, note: str = "") -> dict[str, Any]:
    """Append a hash-chained line {i, utc_time, prev_line_sha256, payload_sha256, payload_path, note} to commitments.log.
    payload_sha256 = sha256 of the canonical sorted-key JSON of the payload (JSON files) or of the raw bytes
    (other files); prev_line_sha256 = sha256 of the previous line's exact text ('0'*64 for line 0)."""
    payload_path = Path(payload_path)
    lines = COMMIT_LOG.read_text().splitlines() if COMMIT_LOG.exists() else []
    prev = sha256_text(lines[-1]) if lines else "0" * 64
    if payload_path.suffix == ".json":
        psha = sha256_text(canonical_json(json.loads(payload_path.read_text())))
    else:
        psha = sha256_file(payload_path)
    entry = {"i": len(lines), "utc_time": utc_now(), "prev_line_sha256": prev, "payload_sha256": psha,
             "payload_path": str(payload_path.relative_to(ROOT)), "note": note}
    with COMMIT_LOG.open("a") as fh:
        fh.write(json.dumps(entry, sort_keys=True) + "\n")
    logger.info(f"committed {entry['payload_path']} sha={psha[:12]} (line {entry['i']})")
    return entry


def verify_chain() -> tuple[bool, list[str]]:
    """Recompute the chain and every payload hash; returns (ok, problems)."""
    problems: list[str] = []
    if not COMMIT_LOG.exists():
        return False, ["no commitments.log"]
    lines = COMMIT_LOG.read_text().splitlines()
    prev = "0" * 64
    for i, ln in enumerate(lines):
        e = json.loads(ln)
        if e["prev_line_sha256"] != prev:
            problems.append(f"line {i}: prev-line hash mismatch")
        p = ROOT / e["payload_path"]
        if not p.exists():
            problems.append(f"line {i}: payload missing {e['payload_path']}")
        else:
            psha = sha256_text(canonical_json(json.loads(p.read_text()))) if p.suffix == ".json" else sha256_file(p)
            if psha != e["payload_sha256"]:
                problems.append(f"line {i}: payload hash mismatch for {e['payload_path']}")
        prev = sha256_text(ln)
    return (not problems, problems)


def deviation(code: str, text: str) -> None:
    """Append one entry to results/deviations.json (deduplicated by code)."""
    p = RESULTS_DIR / "deviations.json"
    devs = json.loads(p.read_text()) if p.exists() else []
    if any(d["code"] == code for d in devs):
        return
    devs.append({"code": code, "text": text, "utc": utc_now()})
    write_json(p, devs)
    logger.warning(f"DEVIATION {code}: {text}")


def timing(key: str, seconds: float, units: int, note: str = "") -> None:
    """Record time-per-unit to logs/timing.json (staged scaling 10 -> 100 -> full)."""
    p = LOG_DIR / "timing.json"
    t = json.loads(p.read_text()) if p.exists() else {}
    t.setdefault(key, []).append({"seconds": round(seconds, 3), "units": units,
                                   "sec_per_unit": round(seconds / max(units, 1), 4), "note": note, "utc": utc_now()})
    write_json(p, t)
