#!/usr/bin/env python3
"""Shared constants, paths and helpers for the de-commitment steering screen.

Every path is derived from this file's location so the workspace can be forked and
re-run elsewhere. Nothing here imports torch or vLLM, so CPU tools stay light.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
from pathlib import Path

from loguru import logger

WS = Path(__file__).resolve().parent
TASKS_DIR = WS / "tasks"
LABELLER_DIR = WS / "labeller"
PROMPTS_DIR = WS / "prompts"
DATA_DIR = WS / "data"
RAW_DIR = DATA_DIR / "raw"
CACHE_DIR = WS / "cache"
LABEL_CACHE = CACHE_DIR / "labels"
DIRECTIONS_DIR = WS / "directions"
FORECAST_DIR = WS / "forecast"
GOLD_DIR = WS / "gold"
RESULTS_DIR = WS / "results"
FIGURES_DIR = WS / "figures"
LOGS_DIR = WS / "logs"

MODEL_ID = "Qwen/Qwen3-8B"
N_LAYERS = 36
LAYERS = list(range(8, 29))          # candidate read/steer layers (hidden_states index), below 0.8 L
GRID_C = [0.25, 0.5, 1.0, 1.5]        # steering coefficient grid (c = 0 is the zero-strength control)
PAD_ID = 151643
EOS_IDS = [151645, 151643]

TASKS = ["T1", "T2"]

SPEC = {
    "T1": (
        "Task: write a Python function solve(grid, start, goal). grid is a list of equal-length strings in which . "
        "is an open cell and # is a wall; start and goal are (row, col) tuples of open cells. A move goes up, down, "
        "left or right to an open cell inside the grid. Return any valid path from start to goal as a list of "
        "(row, col) tuples that begins with start, ends with goal and in which consecutive cells are adjacent; "
        "return [] if goal cannot be reached. Grids have at most 30 rows and 30 columns. Use only the Python "
        "standard library. Return only one ```python code block containing solve."
    ),
    "T2": (
        "Task: write a Python function solve(n, edges, s, t). The graph is directed with nodes 0..n-1 (n <= 100); "
        "edges is a list of (u, v, w) tuples with integer weights 0 <= w <= 100; parallel edges, self-loops and "
        "cycles may occur. Return the length of a shortest path from s to t as an int, or -1 if t is unreachable "
        "from s (0 when s == t). Use only the Python standard library. Return only one ```python code block "
        "containing solve."
    ),
}

# Catalogue modes per task (label ids) and the display names used inside ban / mention prompts.
CATALOGUE = {
    "T1": ["bfs", "dfs", "bidirectional_bfs", "iddfs", "astar", "dijkstra_unit"],
    "T2": ["dijkstra", "bellman_ford_spfa", "bidirectional_dijkstra", "floyd_warshall", "dial"],
}
DISPLAY = {
    "T1": {
        "bfs": "breadth-first search (BFS)",
        "dfs": "depth-first search (DFS)",
        "bidirectional_bfs": "bidirectional BFS",
        "iddfs": "iterative-deepening DFS",
        "astar": "A* search",
        "dijkstra_unit": "Dijkstra's algorithm",
    },
    "T2": {
        "dijkstra": "Dijkstra's algorithm",
        "bellman_ford_spfa": "the Bellman-Ford algorithm (including SPFA)",
        "bidirectional_dijkstra": "bidirectional Dijkstra",
        "floyd_warshall": "the Floyd-Warshall algorithm",
        "dial": "Dial's algorithm (bucket queue)",
    },
}
DEFINITIONS = {
    "T1": {
        "bfs": "breadth-first search with a FIFO queue (deque or list.pop(0)), recursive or iterative",
        "dfs": "depth-first search with a LIFO stack or plain recursion, no outer depth-limit loop",
        "bidirectional_bfs": "two simultaneous breadth-first frontiers, one from start and one from goal, that meet",
        "iddfs": "iterative deepening: repeated depth-limited DFS from start with an increasing depth limit",
        "astar": "best-first search on a heap keyed by g+h or h with h = Manhattan distance to goal (A* or greedy best-first)",
        "dijkstra_unit": "uniform-cost search / Dijkstra on a heap keyed by path length g only (no heuristic)",
    },
    "T2": {
        "dijkstra": "Dijkstra's algorithm with one priority queue (heap), nodes popped in non-decreasing distance",
        "bellman_ford_spfa": "Bellman-Ford edge relaxation in repeated passes, or SPFA (FIFO queue with re-enqueueing)",
        "bidirectional_dijkstra": "two Dijkstra searches, forward from s and backward from t on reversed edges, that meet",
        "floyd_warshall": "all-pairs Floyd-Warshall triple loop dist[i][j] = min(dist[i][j], dist[i][k] + dist[k][j])",
        "dial": "Dial's algorithm: Dijkstra with an array of buckets indexed by distance instead of a heap",
    },
}
# Case-insensitive lexicon used for names_mentioned (prose + code comments).
LEXICON = {
    "bfs": [r"\bbfs\b", r"breadth[- ]first"],
    "dfs": [r"\bdfs\b", r"depth[- ]first"],
    "iddfs": [r"iterative[- ]deepening", r"\biddfs\b"],
    "astar": [r"\ba\*", r"\ba-star\b", r"\bastar\b", r"best[- ]first"],
    "dijkstra": [r"dijkstra"],
    "bidirectional": [r"bidirectional", r"bi-directional"],
    "bellman_ford_spfa": [r"bellman", r"\bspfa\b", r"shortest path faster"],
    "floyd_warshall": [r"floyd", r"warshall"],
    "dial": [r"\bdial\b", r"\bdial'?s\b", r"bucket queue"],
}
# Map lexicon keys onto catalogue modes of each task.
LEXICON_TO_MODE = {
    "T1": {"bfs": "bfs", "dfs": "dfs", "iddfs": "iddfs", "astar": "astar", "dijkstra": "dijkstra_unit",
           "bidirectional": "bidirectional_bfs"},
    "T2": {"dijkstra": "dijkstra", "bellman_ford_spfa": "bellman_ford_spfa", "floyd_warshall": "floyd_warshall",
           "dial": "dial", "bidirectional": "bidirectional_dijkstra"},
}


def stable_hash(*parts: object) -> int:
    """Deterministic 31-bit seed from arbitrary parts (independent of PYTHONHASHSEED)."""
    h = hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()
    return int(h[:8], 16) % (2**31 - 1)


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8", errors="replace")).hexdigest()


def setup_logger(name: str, level: str = "INFO") -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    logger.remove()
    logger.add(sys.stdout, level=level, format="{time:HH:mm:ss}|{level:<7}|{message}")
    logger.add(str(LOGS_DIR / f"{name}.log"), rotation="30 MB", level="DEBUG")


def resolve_model_path() -> str:
    """Local snapshot directory of Qwen3-8B inside the shared HF cache (never written into outputs)."""
    from huggingface_hub import snapshot_download
    return snapshot_download(MODEL_ID, local_files_only=True)


def detect_cpus() -> int:
    try:
        q = int(Path("/sys/fs/cgroup/cpu/cpu.cfs_quota_us").read_text())
        p = int(Path("/sys/fs/cgroup/cpu/cpu.cfs_period_us").read_text())
        if q > 0:
            return math.ceil(q / p)
    except (FileNotFoundError, ValueError):
        pass
    try:
        parts = Path("/sys/fs/cgroup/cpu.max").read_text().split()
        if parts[0] != "max":
            return math.ceil(int(parts[0]) / int(parts[1]))
    except (FileNotFoundError, ValueError, IndexError):
        pass
    try:
        return len(os.sched_getaffinity(0))
    except (AttributeError, OSError):
        return os.cpu_count() or 1


def container_ram_bytes() -> int | None:
    for p in ["/sys/fs/cgroup/memory/memory.limit_in_bytes", "/sys/fs/cgroup/memory.max"]:
        try:
            v = Path(p).read_text().strip()
            if v != "max" and int(v) < 1_000_000_000_000:
                return int(v)
        except (FileNotFoundError, ValueError):
            pass
    return None


def set_ram_limit(budget_gb: float) -> None:
    """Hard address-space cap so a runaway process raises MemoryError instead of OOM-killing the box."""
    import resource
    b = int(budget_gb * 1e9)
    resource.setrlimit(resource.RLIMIT_AS, (b, b))


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                logger.warning(f"skipping corrupt line in {path.name}")
    return rows


def append_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


def cond_name_steer(direction: str, coef: float, layer: int) -> str:
    return f"steer:{direction}:c={coef:g}:L={layer}"
