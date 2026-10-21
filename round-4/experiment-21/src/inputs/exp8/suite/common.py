#!/usr/bin/env python3
"""Shared constants and helpers for the ban-substitution screen.

Everything that defines the protocol (task texts, catalogue, display names, thresholds,
composition constants) lives here so that every stage reads one frozen definition.
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
TASK_DIR = ROOT / "tasks"
PROMPT_DIR = ROOT / "prompts"
DATA_DIR = ROOT / "data"
ELICIT_DIR = ROOT / "elicitation"
PRED_DIR = ROOT / "predictions"
RESULTS_DIR = ROOT / "results"
FIG_DIR = ROOT / "figures"
LOG_DIR = ROOT / "logs"
LABEL_DIR = ROOT / "labeller"
COMMIT_LOG = ROOT / "commitments.log"

for _d in (DATA_DIR, ELICIT_DIR, PRED_DIR, RESULTS_DIR, FIG_DIR, LOG_DIR):
    _d.mkdir(parents=True, exist_ok=True)

MODEL_ID = os.environ.get("SCREEN_MODEL", "Qwen/Qwen3-8B")
SERVED_NAME = "qwen3-screen"
VLLM_PORT = int(os.environ.get("SCREEN_VLLM_PORT", "8011"))
VLLM_URL = f"http://127.0.0.1:{VLLM_PORT}"
EXT_MODEL = "meta-llama/llama-3.1-8b-instruct"
JUDGE_MODEL = "openai/gpt-4.1-mini"
GOLD_JUDGES = ("openai/gpt-4.1-mini", "google/gemini-2.5-flash")
GOLD_TIEBREAK = "deepseek/deepseek-chat-v3.1"

TASKS = ("t1", "t2")
TASK_DATASET_NAME = {"t1": "T1_grid_path", "t2": "T2_weighted_shortest_path"}
TASK_SUBDIR = {"t1": "t1_grid", "t2": "t2_wsp"}

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


CATALOGUE: dict[str, dict[str, str]] = {
    "t1": {
        "bfs": "breadth-first search (BFS)",
        "dfs": "depth-first search (DFS)",
        "bibfs": "bidirectional BFS",
        "iddfs": "iterative deepening DFS (IDDFS)",
        "astar_gbfs": "A* or greedy best-first search",
        "dijkstra": "Dijkstra's algorithm",
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
OTHER = "other"
UNKNOWN = "unknown"
NO_CODE = "no_code"

# One-line definitions shown to the blind judge (never the condition).
MODE_DEFINITIONS: dict[str, dict[str, str]] = {
    "t1": {
        "bfs": "breadth-first search: explores cells in order of distance from start using a FIFO queue "
               "(deque.popleft, list.pop(0), queue.Queue) or level-by-level frontier lists; one search direction.",
        "dfs": "depth-first search: explores along one branch as deep as possible using recursion or a LIFO stack "
               "(list.pop(), deque.pop(), LifoQueue), with a visited set; no depth-limit iterations.",
        "bibfs": "bidirectional BFS: two breadth-first searches, one from start and one from goal, expanded "
                 "alternately until the frontiers meet; the path is joined at the meeting cell.",
        "iddfs": "iterative deepening DFS: repeated depth-limited depth-first searches with an increasing depth "
                 "limit (0, 1, 2, ...) until the goal is found.",
        "astar_gbfs": "A* search or greedy best-first search: a priority queue ordered by a heuristic estimate of "
                      "the distance to the goal (e.g. Manhattan distance), either f = g + h (A*) or h alone (greedy).",
        "dijkstra": "Dijkstra's algorithm: a priority queue (heap) ordered by distance from start only, with no "
                    "heuristic toward the goal (on a unit-weight grid).",
    },
    "t2": {
        "dijkstra": "Dijkstra's algorithm: a single priority queue (heap) of tentative distances from s, popping the "
                    "smallest distance each time (lazy deletion or decrease-key variants), one search direction.",
        "bf_spfa": "Bellman-Ford (repeated relaxation passes over all edges, up to n-1 rounds, possibly with early "
                   "exit) or SPFA (a FIFO queue of nodes whose distance improved, often with an in-queue flag).",
        "bidijkstra": "bidirectional Dijkstra: two Dijkstra searches, forward from s on the graph and backward from t "
                      "on the reversed graph, with a meeting/stopping rule.",
        "floyd": "Floyd-Warshall: all-pairs shortest paths with a triple loop over k, i, j updating "
                 "dist[i][j] = min(dist[i][j], dist[i][k] + dist[k][j]).",
        "dial": "Dial's algorithm: Dijkstra with a bucket queue, i.e. an array or dict of buckets indexed by distance, "
                "scanned in increasing distance order instead of a binary heap.",
    },
}
EXTENDED_CATALOGUE = {
    "t1": ["bidirectional A*/Dijkstra", "jump point search", "beam search", "random walk"],
    "t2": ["DAG dynamic programming", "Johnson's algorithm", "A* with a non-zero heuristic"],
}

# Pre-registration thresholds (never tuned on outcomes).
THRESHOLDS = {
    "presence": 0.10,
    "compliance_informative": 0.50,
    "realised_margin": 0.15,
    "stability": 0.80,
    "uniform_mix": 0.05,
    "other_floor": 0.02,
    "min_compliant": 20,
    "t9_min_compliant": 10,
}
DECODING_MAIN = "T1.0_topp1.0_topk-off_max1024_thinkoff"
DECODING_T13 = "T1.3_topp1.0_topk-off_max1024_thinkoff"
DECODING_RANK = "T1.0_topp1.0_topk-off_max64_thinkoff"
DECODING_FREE = "T1.0_topp1.0_topk-off_max32_thinkoff"


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


def request_seed(task: str, condition: str, paraphrase_id: int | str, stage: str) -> int:
    """Per-request seed = int(sha256('task|condition|paraphrase|stage')[:8], 16)."""
    return int(hashlib.sha256(f"{task}|{condition}|{paraphrase_id}|{stage}".encode()).hexdigest()[:8], 16)


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
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    tmp.replace(p)


def write_json(p: Path, obj: Any, indent: int | None = 1, sort_keys: bool = False) -> None:
    p = Path(p)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=indent, sort_keys=sort_keys, ensure_ascii=False, default=_json_default))
    tmp.replace(p)


def _json_default(o: Any) -> Any:
    try:
        import numpy as np  # local import: keeps the sandbox runner free of numpy

        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, np.floating):
            return float(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
        if isinstance(o, np.bool_):
            return bool(o)
    except ImportError:
        pass
    if isinstance(o, (set, frozenset)):
        return sorted(o)
    raise TypeError(f"not JSON serialisable: {type(o)}")


def wilson_ci(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if n <= 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, centre - half), min(1.0, centre + half))


def join_names_or(names: list[str]) -> str:
    """'A', 'A or B', 'A, B or C' (ban order preserved)."""
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + " or " + names[-1]


def join_names_and(names: list[str]) -> str:
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + " and " + names[-1]


def cap_first(s: str) -> str:
    return s[:1].upper() + s[1:] if s else s


def read_commitments() -> list[dict[str, Any]]:
    return read_jsonl(COMMIT_LOG)


def commit_file(p: Path, note: str = "") -> dict[str, Any]:
    """Append a hash-chained entry {utc_time, file, sha, prev_entry_hash, entry_hash} to commitments.log.
    entry_hash = sha256(prev_entry_hash + sha + utc_time)."""
    p = Path(p)
    entries = read_commitments()
    prev = entries[-1]["entry_hash"] if entries else "0" * 64
    sha = sha256_file(p)
    t = utc_now()
    entry = {"utc_time": t, "file": str(p.relative_to(ROOT)), "sha": sha, "prev_entry_hash": prev,
             "entry_hash": sha256_text(prev + sha + t), "note": note}
    with COMMIT_LOG.open("a") as fh:
        fh.write(json.dumps(entry) + "\n")
    logger.info(f"committed {entry['file']} sha={sha[:12]} entry={entry['entry_hash'][:12]}")
    return entry


def verify_chain() -> tuple[bool, list[str]]:
    """Recompute the hash chain; returns (ok, problems)."""
    problems: list[str] = []
    prev = "0" * 64
    for i, e in enumerate(read_commitments()):
        if e["prev_entry_hash"] != prev:
            problems.append(f"entry {i}: prev hash mismatch")
        if sha256_text(e["prev_entry_hash"] + e["sha"] + e["utc_time"]) != e["entry_hash"]:
            problems.append(f"entry {i}: entry hash mismatch")
        prev = e["entry_hash"]
    return (not problems, problems)
