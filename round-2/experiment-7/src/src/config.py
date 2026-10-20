#!/usr/bin/env python3
"""Frozen protocol constants and shared helpers for the FRLP ban screen (substitute vs ladder).

Every stage reads its names, templates, paths and thresholds from here, so the protocol has one definition.
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

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
SUITE = ROOT / "suite"            # copied exp1 suite (common.py, tasks/, labeller/, gen/prompts.py, pipeline.py)
DATA_IN = ROOT / "data_in"        # copied exp1 data, exp4 directions, DS noun bank
DATA = ROOT / "data"
RESULTS = ROOT / "results"
LOGS = ROOT / "logs"
PROMPTS = ROOT / "prompts"
SCORES = ROOT / "scores"
FROZEN = ROOT / "frozen"
FIGS = ROOT / "figures"
COMMIT_LOG = ROOT / "commitments.log"
PATHS_LOCAL = ROOT / "paths.local.json"
for _d in (DATA_IN, DATA, RESULTS, LOGS, PROMPTS, SCORES, FROZEN, FIGS):
    _d.mkdir(parents=True, exist_ok=True)

MODEL_ID = "Qwen/Qwen3-8B"
MODEL_REV = "b968826d9c46dd6066d109eabc6255188de91218"
CHAT_TAIL = "<|im_start|>assistant\n<think>\n\n</think>\n\n"
JUDGE_MODEL = "openai/gpt-4.1-mini"
JUDGE_CAP_USD = 0.5

TASKS = ("t1", "t2")
MODES: dict[str, list[str]] = {
    "t1": ["bfs", "dfs", "bibfs", "iddfs", "astar_gbfs", "dijkstra"],
    "t2": ["dijkstra", "bf_spfa", "bidijkstra", "floyd", "dial"],
}
DEFAULT_MODE = {"t1": "bfs", "t2": "dijkstra"}
OTHER = "other"
# Frozen display names (direction); NOT exp1's t1 names for astar_gbfs / dijkstra.
DISPLAY: dict[str, dict[str, str]] = {
    "t1": {
        "bfs": "breadth-first search (BFS)",
        "dfs": "depth-first search (DFS)",
        "bibfs": "bidirectional BFS",
        "iddfs": "iterative deepening DFS (IDDFS)",
        "astar_gbfs": "A* search",
        "dijkstra": "unit-weight Dijkstra",
    },
    "t2": {
        "dijkstra": "Dijkstra's algorithm",
        "bf_spfa": "Bellman-Ford or SPFA",
        "bidijkstra": "bidirectional Dijkstra",
        "floyd": "Floyd-Warshall",
        "dial": "Dial's bucket-queue algorithm",
    },
}
SHAMS: dict[str, dict[str, str]] = {
    "t1": {"jps": "jump point search", "idastar": "IDA* search"},
    "t2": {"johnson": "Johnson's algorithm", "yen": "Yen's k-shortest-paths algorithm"},
}
# Pre-declared content neighbours of each off-catalogue sham (step 7.3).
SHAM_NEIGHBOURS = {"idastar": ["iddfs", "astar_gbfs"], "jps": ["astar_gbfs"], "johnson": ["bf_spfa", "dijkstra"],
                   "yen": ["dijkstra"]}
NONCE = "the Zorblax method"
TWO_STEP = {"t1": ["bfs", "dfs"], "t2": ["dijkstra", "bf_spfa"]}
WS = ["W1", "W2", "W3", "W4", "W5"]
TEMPLATES: dict[str, dict[str, str]] = {
    "W1": {"ban": "Do not use {X} for this task.", "mention": "You could use {X} for this task.",
           "neutral": "Do not use {N} for this task."},
    "W2": {"ban": "Your solution must not rely on {X}.", "mention": "Your solution may rely on {X}.",
           "neutral": "Your solution must not rely on {N}."},
    "W3": {"ban": "Avoid {X} entirely.", "mention": "Consider {X} first.", "neutral": "Avoid {N} entirely."},
    "W4": {"ban": "{X} is not allowed here.", "mention": "{X} is allowed here.", "neutral": "{N} is not allowed here."},
    "W5": {"ban": "Write a correct solution that does not use {X}.",
           "mention": "Write a correct solution that may use {X}.",
           "neutral": "Write a correct solution that does not use {N}."},
}
NOVELTY = "Write a novel algorithm for this task, one you have not seen before."
FORCED_TEMPLATES = [
    "Implement {j} for this task.", "Use {j} to solve this task.", "Solve this task with {j}.",
    "Your solution should use {j}.", "Write an implementation based on {j}.", "Solve this task by implementing {j}.",
    "Please implement {j} for this task.", "The solution must use {j}.", "Write a solution that uses {j}.",
    "Apply {j} to this task.",
]
FREE_TEMPLATE = "What is the standard alternative to {X} for this task? Answer with the name of one algorithm only."
FILLERS = [" .", " -", " ok"]
EDIT_LAYERS = list(range(12, 25))      # decoder layers 12..24 (outputs = hidden_states[l+1])
RAND_SEEDS = {"A": [1001, 1002, 1003], "B": [2001, 2002, 2003]}
VARIANT_II_LAYER = 18
VARIANT_II_COEF = 0.25
N_FORCED_TARGET = 30
MIN_MEASURABLE = 10
SEED_SELECT = 7
SEED_HALVES = 11
SEED_BOOT = 13
N_BOOT = 2000
N_PERM = 200_000
ESS_FLAG = 5.0
GATE_A_S_RANGE = (0.3, 3.0)
GATE_A_M_MIN = 0.9
GATE_B_MIN = 0.3
GATE_C_MIN = 0.8
CLEAR_MODE_MARGIN = 0.15
LADDER_COS_MIN = 0.5
TRUNC_TOKENS = [64, 128, 256, 384]

# Name lexicon for scrubbing (step 2.2), case-insensitive, word/underscore boundaries.
SCRUB_PHRASES = [
    r"breadth[- ]first", r"depth[- ]first", r"bi[- ]?directional", r"iterative[- ]deepening", r"greedy best[- ]first",
    r"best[- ]first", r"bellman[- ]?ford", r"shortest path faster", r"uniform[- ]cost", r"jump point", r"A\*",
    r"A-star", r"IDA\*", r"BFS", r"DFS", r"IDDFS", r"astar", r"a_star", r"GBFS", r"Dijkstra'?s?", r"SPFA",
    r"Floyd", r"Warshall", r"Dial'?s?", r"UCS", r"JPS", r"Johnson'?s?", r"Yen'?s?",
]
SCRUB_STEMS = ["bfs", "dfs", "iddfs", "dijkstra", "bellman", "spfa", "floyd", "warshall", "astar", "a_star", "dial",
               "bidir", "gbfs", "jps", "johnson", "yen", "bibfs", "bidijkstra", "ucs", "idastar"]


def display(task: str, key: str) -> str:
    """Display name of a catalogue id, a sham id, 'nonce' or 'two_step'."""
    if key in DISPLAY[task]:
        return DISPLAY[task][key]
    if key in SHAMS[task]:
        return SHAMS[task][key]
    if key == "nonce":
        return NONCE
    if key == "two_step":
        return join_names_or([DISPLAY[task][m] for m in TWO_STEP[task]])
    raise KeyError(f"{task}:{key}")


def setup_logging(name: str) -> None:
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    logger.add(str(LOGS / f"{name}.log"), rotation="30 MB", level="DEBUG")


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def sha256_file(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def seed_of(key: str) -> int:
    return int(hashlib.sha256(key.encode()).hexdigest()[:8], 16)


def join_names_or(names: list[str]) -> str:
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + " or " + names[-1]


def cap_first(s: str) -> str:
    return s[:1].upper() + s[1:] if s else s


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
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    with tmp.open("w") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False, default=_json_default) + "\n")
    tmp.replace(p)


def append_jsonl(p: Path, rows: Iterable[dict[str, Any]]) -> None:
    with Path(p).open("a") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False, default=_json_default) + "\n")


def _json_default(o: Any) -> Any:
    import numpy as np

    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        v = float(o)
        return None if math.isnan(v) else v
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, (set, frozenset)):
        return sorted(o)
    if isinstance(o, Path):
        return str(o)
    raise TypeError(f"not JSON serialisable: {type(o)}")


def write_json(p: Path, obj: Any, indent: int | None = 1) -> None:
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=indent, ensure_ascii=False, default=_json_default))
    tmp.replace(p)


def read_json(p: Path) -> Any:
    return json.loads(Path(p).read_text())


def local_paths() -> dict[str, str]:
    """Absolute source locations (EXP1/EXP4/DS/model snapshot); env vars override paths.local.json."""
    out: dict[str, str] = {}
    if PATHS_LOCAL.exists():
        out.update({k: v for k, v in read_json(PATHS_LOCAL).items() if not k.startswith("_")})
    for k in ("EXP1", "EXP4", "DS"):
        if os.environ.get(f"FRLP_{k}"):
            out[k] = os.environ[f"FRLP_{k}"]
    if os.environ.get("FRLP_MODEL_SNAPSHOT"):
        out["model_snapshot"] = os.environ["FRLP_MODEL_SNAPSHOT"]
    return out


def model_path() -> str:
    """Local snapshot of Qwen/Qwen3-8B@MODEL_REV if available, else the hub id (downloaded at MODEL_REV)."""
    snap = local_paths().get("model_snapshot")
    if snap and (Path(snap) / "config.json").exists():
        return snap
    try:
        from huggingface_hub import snapshot_download

        return snapshot_download(MODEL_ID, revision=MODEL_REV)
    except Exception as e:  # noqa: BLE001 - fall back to the hub id and let the loader fail loudly
        logger.warning(f"snapshot_download failed ({e}); using hub id")
        return MODEL_ID


def commit(payload_path: Path, note: str = "") -> dict[str, Any]:
    """Hash chain: entry_hash_i = sha256(entry_hash_{i-1} + payload_sha256); one JSON line per entry."""
    payload_path = Path(payload_path)
    prev = "0" * 64
    if COMMIT_LOG.exists():
        lines = [ln for ln in COMMIT_LOG.read_text().splitlines() if ln.strip()]
        if lines:
            prev = json.loads(lines[-1])["entry_hash"]
    sha = sha256_file(payload_path)
    entry = {"utc_time": utc_now(), "file": str(payload_path.relative_to(ROOT)), "payload_sha256": sha,
             "prev_entry_hash": prev, "entry_hash": sha256_text(prev + sha), "note": note}
    with COMMIT_LOG.open("a") as fh:
        fh.write(json.dumps(entry) + "\n")
    logger.info(f"committed {entry['file']} sha={sha[:12]} entry={entry['entry_hash'][:12]} ({note})")
    return entry


def verify_chain() -> tuple[bool, list[str]]:
    problems: list[str] = []
    prev = "0" * 64
    if not COMMIT_LOG.exists():
        return True, problems
    for i, ln in enumerate([x for x in COMMIT_LOG.read_text().splitlines() if x.strip()]):
        e = json.loads(ln)
        if e["prev_entry_hash"] != prev:
            problems.append(f"entry {i}: prev mismatch")
        if sha256_text(e["prev_entry_hash"] + e["payload_sha256"]) != e["entry_hash"]:
            problems.append(f"entry {i}: hash mismatch")
        prev = e["entry_hash"]
    return (not problems), problems


def logsumexp(a, axis=None):
    import numpy as np

    a = np.asarray(a, dtype=np.float64)
    m = np.max(a, axis=axis, keepdims=True)
    m = np.where(np.isfinite(m), m, 0.0)
    out = np.log(np.sum(np.exp(a - m), axis=axis, keepdims=True)) + m
    return np.squeeze(out, axis=axis) if axis is not None else float(out.squeeze())


def add_suite_to_path() -> None:
    """Make the copied exp1 suite importable (`common`, `labeller`, `tasks`, `pipeline`)."""
    if str(SUITE) not in sys.path:
        sys.path.insert(0, str(SUITE))
