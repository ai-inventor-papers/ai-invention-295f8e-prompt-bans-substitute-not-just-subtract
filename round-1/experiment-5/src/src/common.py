"""Shared constants, paths and small helpers for the collapse screen (alternate 4: post-training)."""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import time
from pathlib import Path
from typing import Any, Iterable

from loguru import logger

WS = Path(__file__).resolve().parent.parent
SRC = WS / "src"
DATA = WS / "data"
TESTS = DATA / "tests"
REFS = DATA / "refs"
RUNS = WS / "runs"
PRED = WS / "predictions"
ACTS = WS / "activations"
RESULTS = WS / "results"
FIGS = WS / "figures"
LOGS = WS / "logs"
for _d in (DATA, TESTS, REFS, RUNS, PRED, ACTS, RESULTS, FIGS, LOGS):
    _d.mkdir(parents=True, exist_ok=True)

MB = "Qwen/Qwen3-8B-Base"
MI = "Qwen/Qwen3-8B"
N_LAYERS = 36
D_MODEL = 4096
EOS_IDS = [151645, 151643]  # <|im_end|>, <|endoftext|>
IM_START_ID = 151644
TASKS = ("t1", "t2")
TASK_NAMES = {"t1": "T1_unweighted_grid_path", "t2": "T2_weighted_shortest_path"}

T1_LABELS = ["bfs", "dfs", "bidir_bfs", "iddfs", "astar_greedy", "dijkstra_unit"]
T2_LABELS = ["dijkstra", "bellman_ford_spfa", "bidir_dijkstra", "floyd_warshall", "dial"]
CATALOGUE = {"t1": T1_LABELS, "t2": T2_LABELS}
BANNED = {"t1": "bfs", "t2": "dijkstra"}
BAN_COND = {"t1": "ban:BFS", "t2": "ban:Dijkstra"}
SURVIVORS = {"t1": ["dfs", "bidir_bfs", "iddfs", "astar_greedy", "dijkstra_unit"],
             "t2": ["bellman_ford_spfa", "bidir_dijkstra", "floyd_warshall", "dial"]}

DECODING = {"temperature": 1.0, "top_p": 1.0, "top_k": "disabled", "min_p": 0.0,
            "repetition_penalty": 1.0, "max_tokens": 1024, "thinking": "off"}


def setup_logging(name: str, level: str = "INFO") -> None:
    logger.remove()
    logger.add(sys.stdout, level=level, format="{time:HH:mm:ss}|{level:<7}|{message}")
    logger.add(str(LOGS / f"{name}.log"), rotation="30 MB", level="DEBUG")


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def stable_seed(*parts: Any, mod: int = 2**31 - 1) -> int:
    """Deterministic seed from arbitrary parts (Python's hash() is salted per process)."""
    s = "|".join(str(p) for p in parts)
    return int(hashlib.sha256(s.encode()).hexdigest()[:15], 16) % mod


def read_jsonl(p: Path) -> list[dict]:
    if not p.exists():
        return []
    out = []
    with open(p) as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def write_jsonl(p: Path, rows: Iterable[dict]) -> None:
    tmp = p.with_suffix(p.suffix + ".tmp")
    with open(tmp, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    tmp.replace(p)


def append_jsonl(p: Path, rows: Iterable[dict]) -> None:
    with open(p, "a") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float, float]:
    if n == 0:
        return (float("nan"), float("nan"), float("nan"))
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (p, max(0.0, c - h), min(1.0, c + h))


def time_log(event: str, **kw: Any) -> None:
    """Append a phase-boundary event to time_log.json (list of dicts)."""
    p = WS / "time_log.json"
    try:
        cur = json.loads(p.read_text()) if p.exists() else []
    except json.JSONDecodeError:
        cur = []
    cur.append({"utc": utc_now(), "event": event, **kw})
    p.write_text(json.dumps(cur, indent=1))


def add_deviation(what: str, why: str) -> None:
    p = RESULTS / "deviations.json"
    try:
        cur = json.loads(p.read_text()) if p.exists() else []
    except json.JSONDecodeError:
        cur = []
    if any(d["what"] == what for d in cur):
        return
    cur.append({"what": what, "why": why, "when": utc_now()})
    p.write_text(json.dumps(cur, indent=1))


def set_ram_limit(gb: float) -> None:
    import resource
    b = int(gb * 1024**3)
    resource.setrlimit(resource.RLIMIT_AS, (b, b))


def env_flag(name: str, default: str = "") -> str:
    return os.environ.get(name, default)
