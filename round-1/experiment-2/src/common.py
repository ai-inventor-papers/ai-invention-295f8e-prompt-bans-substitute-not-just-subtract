#!/usr/bin/env python3
"""Shared constants, task specs, catalogue, prompt templates and helpers for the path-search ban screen.

Every phase script imports this module, so condition names, display names and the
shared row schema stay identical across phases (and across sibling screens that
follow the same SHARED SCREEN PROTOCOL).
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parent

# Keep every compiler / kernel cache inside the workspace (the workspace is the only writable place).
os.environ.setdefault("VLLM_CACHE_ROOT", str(ROOT / ".vllm_cache"))
os.environ.setdefault("TRITON_CACHE_DIR", str(ROOT / ".triton_cache"))
os.environ.setdefault("TORCHINDUCTOR_CACHE_DIR", str(ROOT / ".inductor_cache"))
os.environ.setdefault("FLASHINFER_WORKSPACE_BASE", str(ROOT / ".flashinfer_cache"))
os.environ.setdefault("XDG_CACHE_HOME", str(ROOT / ".xdg_cache"))
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

MODEL_ID = "Qwen/Qwen3-8B"
MODEL_TAG = "Qwen3-8B-bf16"
DECODING_GEN = "T=1.0,top_p=1.0,top_k=off,min_p=0,max_tokens=1024,thinking=off,stop=closing_fence"
DECODING_HOOK = "T=1.0,top_p=1.0,top_k=off,max_new_tokens=768,thinking=off,hooked_hf,stop=closing_fence"

TASKS = ["t1", "t2"]
TASK_DATASET = {"t1": "t1_grid_path", "t2": "t2_weighted_sp"}
CACHE_LAYERS = list(range(8, 29))  # l = output of decoder block l = hidden_states[l + 1]
N_LAYERS_MODEL = 36

SPEC = {
    "t1": (
        "Write a Python function solve(grid, start, goal). grid is a list of equal-length strings over . (free) "
        "and # (wall), at most 30 rows and 30 columns; start and goal are (row, col) tuples of free cells. A move "
        "goes to one of the 4 orthogonal neighbours inside the grid. Return any valid path from start to goal as a "
        "list of (row, col) tuples including both endpoints, or [] if the goal is unreachable. Return only one "
        "```python code block containing the function and its imports."
    ),
    "t2": (
        "Write a Python function solve(n, edges, s, t). Nodes are 0..n-1 with n <= 100; edges is a list of directed "
        "(u, v, w) triples with integer weights 0 <= w <= 100, at most 1000 edges; cycles, self-loops and parallel "
        "edges may occur. Return the length of the shortest path from s to t, or -1 if t is unreachable. Return only "
        "one ```python code block containing the function and its imports."
    ),
}

CATALOGUE: dict[str, list[str]] = {
    "t1": ["bfs", "dfs", "bidir_bfs", "iddfs", "astar", "dijkstra_unit"],
    "t2": ["dijkstra", "bellman_ford_spfa", "bidir_dijkstra", "floyd_warshall", "dial"],
}

DISPLAY: dict[str, dict[str, str]] = {
    "t1": {
        "bfs": "breadth-first search (BFS)",
        "dfs": "depth-first search (DFS)",
        "bidir_bfs": "bidirectional BFS",
        "iddfs": "iterative-deepening DFS (IDDFS)",
        "astar": "A* search with a Manhattan-distance heuristic",
        "dijkstra_unit": "Dijkstra's algorithm",
    },
    "t2": {
        "dijkstra": "Dijkstra's algorithm",
        "bellman_ford_spfa": "Bellman-Ford (or SPFA)",
        "bidir_dijkstra": "bidirectional Dijkstra",
        "floyd_warshall": "Floyd-Warshall",
        "dial": "Dial's bucket-queue algorithm",
    },
}

ONE_LINE_DEF: dict[str, dict[str, str]] = {
    "t1": {
        "bfs": "breadth-first search: FIFO queue, level-by-level expansion from the start only",
        "dfs": "depth-first search: LIFO stack or recursion following one route deep and backtracking (no growing depth limit)",
        "bidir_bfs": "bidirectional BFS: two FIFO frontiers, one from the start and one from the goal, until they meet",
        "iddfs": "iterative-deepening DFS: depth-limited DFS restarted with limits 0,1,2,... until the goal is found",
        "astar": "A* (or greedy best-first): priority queue ordered by cost-so-far plus (or only) Manhattan distance to the goal",
        "dijkstra_unit": "Dijkstra with unit weights: priority queue (heap) ordered by step count only, no heuristic",
    },
    "t2": {
        "dijkstra": "Dijkstra: one binary heap (or repeated minimum selection) of tentative distances from the source",
        "bellman_ford_spfa": "Bellman-Ford (repeated sweeps over all edges) or SPFA (FIFO queue of improved nodes, no heap)",
        "bidir_dijkstra": "bidirectional Dijkstra: forward search from s and backward search from t on reversed edges",
        "floyd_warshall": "Floyd-Warshall: all-pairs n x n distance matrix with a triple loop over intermediate nodes",
        "dial": "Dial's algorithm: array of buckets indexed by integer distance scanned in increasing order, no heap",
    },
}

DESCRIPTIONS: dict[str, dict[str, list[str]]] = {
    "t1": {
        "bfs": [
            "explore cells in order of their step distance from the start, level by level, with a first-in-first-out queue",
            "expand the search outward one ring of equal step count at a time, always processing the earliest-discovered cell next",
            "keep a first-in-first-out frontier of discovered cells and record each cell's predecessor the first time it is reached",
        ],
        "dfs": [
            "follow one route as deep as possible and backtrack with a last-in-first-out stack or recursion",
            "keep extending the current route to an unvisited neighbour and step back only when the route gets stuck",
            "always continue from the most recently discovered cell, retreating to an earlier branch point at dead ends",
        ],
        "bidir_bfs": [
            "grow two level-by-level frontiers, one from the start and one from the goal, until they meet",
            "search outward from both endpoints at the same time, one ring of cells per round, and join the two halves where they touch",
            "alternate expanding a first-in-first-out frontier around the start and another around the goal, stopping when a cell is reached from both sides",
        ],
        "iddfs": [
            "repeat a depth-limited deep-first search with limits 0, 1, 2, ... until the goal is found",
            "run a deep-first search that may not exceed a maximum route length, and restart it with a larger maximum each time it fails",
            "combine deep-first exploration with a step budget that grows by one after every unsuccessful complete pass",
        ],
        "astar": [
            "always expand the cell with the smallest steps-so-far plus Manhattan distance to the goal",
            "rank frontier cells by the route length so far plus the row and column distance remaining to the goal, and expand the best-ranked one",
            "use a priority queue ordered by cost-so-far plus an optimistic estimate of the remaining distance (absolute row difference plus absolute column difference)",
        ],
        "dijkstra_unit": [
            "keep a min-priority queue of tentative step counts and settle the cell with the smallest one",
            "repeatedly take the cell with the smallest known distance from a heap, finalize it, and lower its neighbours' distances",
            "maintain tentative distances to every cell and always finalize the closest unfinalized cell, taken from a heap, updating its neighbours",
        ],
    },
    "t2": {
        "dijkstra": [
            "settle the unsettled node with the smallest tentative distance from a min-priority queue and relax its outgoing edges",
            "grow a set of finalized nodes by always finalizing the closest remaining node, taken from a heap, and updating its neighbours",
            "keep tentative distances in a binary heap and repeatedly pop the minimum, skipping stale entries, and lower the distances of its successors",
        ],
        "bellman_ford_spfa": [
            "relax every edge repeatedly, or the edges of nodes whose distance just improved kept in a queue, until nothing changes",
            "sweep over the full edge list again and again, lowering any distance that an edge can improve, for at most n-1 rounds",
            "start with only the source distance known and keep improving distances by passing over all edges until a full pass makes no change",
        ],
        "bidir_dijkstra": [
            "run the smallest-tentative-distance settling process forward from the source and backward from the target on reversed edges until they meet",
            "search from both ends at once, settling nodes by distance from the source and by distance to the target on reversed edges, and stop when the two searches cannot improve the best meeting point",
            "alternate between a forward heap-based search from the source and a backward heap-based search from the target over reversed edges, combining them at the meeting node",
        ],
        "floyd_warshall": [
            "fill an all-pairs distance matrix by letting each node in turn act as an intermediate point",
            "build an n by n table of distances and improve every entry through each possible intermediate node with three nested loops",
            "compute distances between all pairs of nodes with dynamic programming over the allowed intermediate nodes, then read off the source-to-target entry",
        ],
        "dial": [
            "keep buckets indexed by integer tentative distance and scan them in increasing order",
            "place nodes into a list of buckets, one per possible integer distance, and process the buckets from the smallest distance upward",
            "exploit the small integer weights with an array of lists indexed by distance value instead of a heap, sweeping the array in increasing order",
        ],
    },
}

# Ten frames shared by every framed condition; frame f wraps the core clause of paraphrase f.
FRAMES = [
    "{core}",
    "Here is a programming exercise. {core}",
    "{core} Keep the code concise.",
    "Read the task below carefully. {core}",
    "{core} Make sure the code is correct.",
    "Consider the problem below. {core}",
    "{core} Write clean, readable Python.",
    "A coding task follows. {core}",
    "{core} Aim for a correct and efficient program.",
    "Your assignment is described below. {core}",
]
BASELINE_CORES = [
    "Solve the following programming task.",
    "Please solve the task below.",
    "Complete the following coding task.",
    "Solve this programming problem.",
    "Write a solution to the following task.",
    "Solve the task described below.",
    "Here is a task for you to solve.",
    "Please complete the programming task below.",
    "Solve the following problem in Python.",
    "Write code that solves the task below.",
]
FORCED_CORES = ["Implement {X} for this task.", "Solve this task using {X}.", "Write a solution based on {X}."]
MASKED_CORE = "Solve this task with the following approach: {D}."
BAN_CORES = [
    "Do not use {X}.",
    "You must not use {X}.",
    "Avoid {X} entirely.",
    "Your solution must not use {X}.",
    "Do not implement {X}.",
    "Using {X} is not allowed.",
    "Do not base your solution on {X}.",
    "{X} is forbidden for this task.",
    "Please do not use {X}.",
    "Stay away from {X}.",
]
MENTION_CORES = [
    "{X} is one well-known approach to this task; implement any correct algorithm.",
    "{X} is one standard way to solve this; you may implement any correct algorithm.",
    "{X} is a common approach here; implement any correct algorithm.",
    "{X} is one known approach; your solution may use any correct algorithm.",
    "{X} is one familiar technique for this; implement any correct algorithm.",
    "{X} is one possible approach; any correct algorithm is allowed.",
    "{X} is one approach people use for this; implement any correct algorithm.",
    "{X} is one option for this task; implement any correct algorithm.",
    "{X} is one well-known approach; please implement any correct algorithm.",
    "{X} is one widely used approach; implement any correct algorithm.",
]
LISTALL_CORE = "Known approaches include {LIST}; implement any correct algorithm."
ELICIT_TEMPLATE = (
    "For the task below, rank the following approaches by how standard an alternative to {X} they are for this task, "
    "most standard first. Approaches: {NAMES}. Answer with only a JSON list of the names exactly as written."
)
N_PARA = 10


def join_names(names: list[str]) -> str:
    """'a', 'a or b', 'a, b or c' (used inside ban cores)."""
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + " or " + names[-1]


def join_names_and(names: list[str]) -> str:
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + " and " + names[-1]


def frame(f: int, core: str) -> str:
    return FRAMES[f].format(core=core)


def user_message(condition_segment: str, task: str) -> str:
    return condition_segment + "\n\n" + SPEC[task]


def stable_seed(*parts: Any) -> int:
    h = hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()
    return int(h[:8], 16) % (2**31 - 1)


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def sha256_file(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def read_jsonl(p: Path) -> list[dict]:
    p = Path(p)
    if not p.exists():
        return []
    out = []
    for line in p.read_text().splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def write_jsonl(p: Path, rows: Iterable[dict]) -> None:
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")


def append_jsonl(p: Path, rows: Iterable[dict]) -> None:
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, c - h), min(1.0, c + h))


def hill1(counts: dict[str, int]) -> float:
    """Hill number of order 1 = exp(Shannon entropy) over label counts."""
    tot = sum(v for v in counts.values() if v > 0)
    if tot == 0:
        return 0.0
    H = -sum((v / tot) * math.log(v / tot) for v in counts.values() if v > 0)
    return math.exp(H)


def js_div(p: dict[str, float] | list[float], q: dict[str, float] | list[float], keys: list[str] | None = None) -> float:
    """Jensen-Shannon divergence (base 2, in [0, 1])."""
    import numpy as np

    if isinstance(p, dict):
        keys = keys or sorted(set(p) | set(q))
        pa = np.array([p.get(k, 0.0) for k in keys], float)
        qa = np.array([q.get(k, 0.0) for k in keys], float)
    else:
        pa, qa = np.asarray(p, float), np.asarray(q, float)
    pa = pa / pa.sum() if pa.sum() > 0 else pa
    qa = qa / qa.sum() if qa.sum() > 0 else qa
    m = 0.5 * (pa + qa)

    def kl(a, b):
        mask = a > 0
        return float(np.sum(a[mask] * np.log2(a[mask] / b[mask])))

    return 0.5 * kl(pa, m) + 0.5 * kl(qa, m)


def setup_logger(name: str):
    from loguru import logger

    (ROOT / "logs").mkdir(exist_ok=True)
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    logger.add(str(ROOT / "logs" / f"{name}.log"), rotation="30 MB", level="DEBUG")
    return logger


def log_timing(phase: str, arm: str, n: int, seconds: float, **extra: Any) -> None:
    import time

    row = {"utc": time.time(), "phase": phase, "arm": arm, "n": n, "seconds": round(seconds, 3),
           "sec_per_sample": round(seconds / max(n, 1), 4)}
    row.update(extra)
    append_jsonl(ROOT / "logs" / "timing.jsonl", [row])


def add_deviation(text: str) -> None:
    """Append a deviation note (deduplicated) to results/deviations.json."""
    p = ROOT / "results" / "deviations.json"
    p.parent.mkdir(exist_ok=True)
    cur = json.loads(p.read_text()) if p.exists() else []
    if text not in cur:
        cur.append(text)
        p.write_text(json.dumps(cur, indent=1))


def set_limits(ram_gb: float) -> None:
    import resource

    b = int(ram_gb * 1024**3)
    try:
        resource.setrlimit(resource.RLIMIT_AS, (b, b))
    except (ValueError, OSError):
        pass


def container_ram_gb() -> float:
    for p in ["/sys/fs/cgroup/memory.max", "/sys/fs/cgroup/memory/memory.limit_in_bytes"]:
        try:
            v = Path(p).read_text().strip()
            if v != "max" and int(v) < 1_000_000_000_000:
                return int(v) / 1e9
        except (FileNotFoundError, ValueError):
            pass
    return 32.0


def detect_cpus() -> int:
    try:
        q = int(Path("/sys/fs/cgroup/cpu/cpu.cfs_quota_us").read_text())
        p = int(Path("/sys/fs/cgroup/cpu/cpu.cfs_period_us").read_text())
        if q > 0:
            return max(1, q // p)
    except (FileNotFoundError, ValueError):
        pass
    try:
        parts = Path("/sys/fs/cgroup/cpu.max").read_text().split()
        if parts[0] != "max":
            return max(1, int(parts[0]) // int(parts[1]))
    except (FileNotFoundError, ValueError):
        pass
    try:
        return len(os.sched_getaffinity(0))
    except (AttributeError, OSError):
        return os.cpu_count() or 1


def mode_names(task: str) -> list[str]:
    return list(CATALOGUE[task])


def condition_mode(cond: str) -> str | None:
    """'forced:bfs' -> 'bfs'; 'ban:bfs+dfs' -> 'dfs' (most recent); 'baseline' -> None."""
    if ":" not in cond:
        return None
    return cond.split(":", 1)[1].split("+")[-1]


def condition_banset(cond: str) -> list[str]:
    if cond.startswith("ban:"):
        return cond.split(":", 1)[1].split("+")
    if cond.startswith("removal:"):
        return [cond.split(":", 1)[1]]
    return []
