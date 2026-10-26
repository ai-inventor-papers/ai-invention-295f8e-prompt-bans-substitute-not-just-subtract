#!/usr/bin/env python3
"""Shared constants and helpers: paths, model id, task texts, algorithm catalogue, seeds, JSONL I/O, hardware."""

from __future__ import annotations

import hashlib
import json
import math
import os
import sys
from pathlib import Path
from typing import Any, Iterable, Iterator

WS = Path(__file__).resolve().parent
LOGS = WS / "logs"
RESULTS = WS / "results"
RAW = RESULTS / "raw"
LABELS = RESULTS / "labels"
STATES = WS / "states"
FIGURES = WS / "figures"
PROMPTS_DIR = WS / "prompts"
TESTS_DIR = WS / "tests"
REFS_DIR = WS / "references"
FORECAST_DIR = WS / "forecast"
for _d in (LOGS, RESULTS, RAW, LABELS, STATES, FIGURES, PROMPTS_DIR, TESTS_DIR, REFS_DIR, FORECAST_DIR):
    _d.mkdir(parents=True, exist_ok=True)

CAPACITY_FILE = LOGS / "capacity.json"
DEFAULT_MODEL = "Qwen/Qwen3-8B"
FALLBACK_MODEL = "Qwen/Qwen3-4B"
THINK_END_ID = 151668  # </think>
EARLY_STOP_TEXT = ("\n\nConsidering the limited time by the user, I have to give the solution based on the "
                   "thinking directly now.\n")


def model_id() -> str:
    """The single model used for every arm (decided once by the capacity probe)."""
    if CAPACITY_FILE.exists():
        try:
            return json.loads(CAPACITY_FILE.read_text()).get("model", DEFAULT_MODEL)
        except json.JSONDecodeError:
            return DEFAULT_MODEL
    return DEFAULT_MODEL


TASKS = ("T1", "T2")
TASK_TEXT = {
    "T1": ("Write a Python function solve(grid, start, goal). grid is a list of strings of equal length; . is an "
           "open cell and # is a wall. start and goal are (row, col) tuples of open cells. Moves go up, down, left "
           "or right. Return any valid path from start to goal as a list of (row, col) tuples that begins with "
           "start, ends with goal and visits only open cells, or [] if goal is unreachable. Grids have at most 30 "
           "rows and 30 columns. Return only one ```python code block containing solve and any helpers."),
    "T2": ("Write a Python function solve(n, edges, s, t). The graph is directed with nodes 0..n-1 (n <= 100); "
           "edges is a list of (u, v, w) tuples with integer weight 0 <= w <= 100; cycles, self-loops and parallel "
           "edges may occur. Return the length of the shortest path from s to t, 0 if s == t, or -1 if t is "
           "unreachable. Return only one ```python code block containing solve and any helpers."),
}
OUTPUT_FORMAT_SENTENCE = "Return only one ```python code block containing solve and any helpers."
TASK_TEXT_NO_FORMAT = {k: v.replace(" " + OUTPUT_FORMAT_SENTENCE, "") for k, v in TASK_TEXT.items()}

# Catalogue: mode -> (display name used in forced prompts, one-line definition used by the judge)
CATALOGUE: dict[str, dict[str, tuple[str, str]]] = {
    "T1": {
        "bfs": ("breadth-first search (BFS)",
                "breadth-first search: a FIFO queue expands cells in order of distance from start"),
        "dfs": ("depth-first search (DFS)",
                "depth-first search: a LIFO stack or recursion follows one branch as deep as possible before "
                "backtracking (recursive and iterative versions are the same algorithm)"),
        "bidirectional_bfs": ("bidirectional breadth-first search",
                              "bidirectional BFS: two FIFO frontiers grow from start and from goal and stop "
                              "when they meet"),
        "iddfs": ("iterative deepening depth-first search (IDDFS)",
                  "iterative deepening DFS: repeated depth-limited DFS with an increasing depth limit"),
        "astar_greedy": ("A* search with a Manhattan-distance heuristic",
                         "heuristic best-first search: a priority queue ordered by a goal-distance heuristic "
                         "h (greedy best-first) or by g+h (A*)"),
        "dijkstra_unit": ("Dijkstra's algorithm with a priority queue",
                          "Dijkstra / uniform-cost search: a priority queue ordered by path cost g only, "
                          "no heuristic"),
    },
    "T2": {
        "dijkstra": ("Dijkstra's algorithm",
                     "Dijkstra: repeatedly settle the unsettled node with the smallest tentative distance "
                     "(binary heap or linear scan), relaxing its outgoing edges"),
        "bellman_ford_spfa": ("the Bellman-Ford algorithm",
                              "Bellman-Ford / SPFA: relax all edges in rounds until nothing changes, or a FIFO "
                              "queue of nodes whose distance changed (nodes may be processed many times)"),
        "bidirectional_dijkstra": ("bidirectional Dijkstra's algorithm",
                                   "bidirectional Dijkstra: one Dijkstra search forward from s and one backward "
                                   "from t over reversed edges, stopping when the frontiers meet"),
        "floyd_warshall": ("the Floyd-Warshall algorithm",
                           "Floyd-Warshall: all-pairs dynamic programming over an n x n distance matrix with "
                           "three nested loops over k, i, j"),
        "dial": ("Dial's algorithm (a bucket-based priority queue)",
                 "Dial's algorithm: Dijkstra with an array of buckets indexed by integer distance instead of "
                 "a heap"),
    },
}
MODES = {t: list(CATALOGUE[t]) for t in TASKS}
PRIMARY_MODE = {"T1": "bfs", "T2": "dijkstra"}
NON_CLASSIFIED = {"other", "unparseable", "unresolved", None}

# Lexicon of catalogue names and aliases (used to check that seeds and descriptions never name an algorithm,
# and to find plan statements in thinking traces).
ALIAS_LEXICON = {
    "bfs": [r"\bbfs\b", r"breadth[- ]first", r"breadth first"],
    "dfs": [r"\bdfs\b", r"depth[- ]first", r"backtrack"],
    "bidirectional_bfs": [r"bi-?directional", r"two[- ]way search", r"meet in the middle", r"meet-in-the-middle"],
    "iddfs": [r"\biddfs\b", r"iterative[- ]deepening", r"depth[- ]limited"],
    "astar_greedy": [r"\ba\*", r"\ba-star\b", r"\bastar\b", r"best[- ]first", r"greedy best"],
    "dijkstra_unit": [r"dijkstra", r"uniform[- ]cost"],
    "dijkstra": [r"dijkstra"],
    "bellman_ford_spfa": [r"bellman", r"\bford\b", r"\bspfa\b", r"shortest path faster"],
    "bidirectional_dijkstra": [r"bi-?directional dijkstra"],
    "floyd_warshall": [r"floyd", r"warshall", r"all[- ]pairs"],
    "dial": [r"\bdial'?s?\b(?! a)", r"bucket[- ]?queue", r"radix heap"],
}


def stable_seed(*parts: Any) -> int:
    """Deterministic 31-bit seed from arbitrary parts (stable across processes, unlike hash())."""
    h = hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()
    return int(h[:8], 16) & 0x7FFFFFFF


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def read_jsonl(path: Path) -> Iterator[dict]:
    path = Path(path)
    if not path.exists():
        return
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue  # a torn last line after a crash; the row is regenerated on resume


def append_jsonl(path: Path, rows: Iterable[dict]) -> int:
    n = 0
    with Path(path).open("a") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
            n += 1
        f.flush()
        os.fsync(f.fileno())
    return n


def write_json(path: Path, obj: Any, indent: int | None = 2) -> None:
    tmp = Path(str(path) + ".tmp")
    tmp.write_text(json.dumps(obj, indent=indent, default=_json_default))
    tmp.replace(path)


def _json_default(o: Any) -> Any:
    try:
        import numpy as np
        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, np.floating):
            return None if not math.isfinite(float(o)) else float(o)
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
    raise TypeError(f"not JSON serializable: {type(o)}")


def detect_cpus() -> int:
    try:
        parts = Path("/sys/fs/cgroup/cpu.max").read_text().split()
        if parts[0] != "max":
            return max(1, int(int(parts[0]) / int(parts[1])))
    except (FileNotFoundError, ValueError, IndexError):
        pass
    try:
        return len(os.sched_getaffinity(0))
    except (AttributeError, OSError):
        return os.cpu_count() or 1


def container_ram_gb() -> float:
    for p in ["/sys/fs/cgroup/memory.max", "/sys/fs/cgroup/memory/memory.limit_in_bytes"]:
        try:
            v = Path(p).read_text().strip()
            if v != "max" and int(v) < 1_000_000_000_000:
                return int(v) / 1e9
        except (FileNotFoundError, ValueError):
            pass
    import psutil
    return psutil.virtual_memory().total / 1e9


def setup_logging(name: str, level: str = "INFO"):
    from loguru import logger
    logger.remove()
    logger.add(sys.stdout, level=level, format="{time:HH:mm:ss}|{level:<7}|{message}")
    logger.add(str(LOGS / f"{name}.log"), rotation="30 MB", level="DEBUG")
    return logger


def truncate(s: str, n: int = 300) -> str:
    s = str(s)
    return s if len(s) <= n else s[:n] + f"...[+{len(s) - n} chars]"


NPY_PART_BYTES = 45_000_000  # keep every published binary well under GitHub's 100 MB file limit


def save_npy_parts(base: Path, arr, max_bytes: int = NPY_PART_BYTES) -> list[Path]:
    """Save `arr` split along axis 0 as <base>_part_001.npy, <base>_part_002.npy, ... (each < max_bytes)."""
    import numpy as np
    base = Path(base)
    for old in base.parent.glob(base.name + "_part_*.npy"):
        old.unlink()
    n_parts = max(1, math.ceil(arr.nbytes / max_bytes))
    paths = []
    for i, chunk in enumerate(np.array_split(arr, n_parts, axis=0), 1):
        p = base.parent / f"{base.name}_part_{i:03d}.npy"
        np.save(p, chunk)
        paths.append(p)
    return paths


def load_npy_parts(base: Path):
    """Load an array saved by save_npy_parts (sorted parts concatenated on axis 0); falls back to <base>.npy."""
    import numpy as np
    base = Path(base)
    parts = sorted(base.parent.glob(base.name + "_part_*.npy"))
    if not parts:
        return np.load(base.parent / (base.name + ".npy"))
    return np.concatenate([np.load(p) for p in parts], axis=0)
