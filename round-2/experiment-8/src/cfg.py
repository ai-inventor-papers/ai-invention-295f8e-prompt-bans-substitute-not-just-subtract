#!/usr/bin/env python3
"""Shared constants, paths, frozen protocol text and small utilities for the ban-route experiment.

Everything frozen by the plan (display names, ban/mention/neutral templates W1-W5, forced paraphrases,
descriptive variants, signature vocabularies, thresholds) lives here so that every stage and the
pre-registration hash read one source.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import resource
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from loguru import logger

ROOT = Path(__file__).resolve().parent
# Inputs produced by other artifacts (read-only). Each is read through ONE constant that an environment variable
# overrides. The defaults follow the published repository's layout, where upstream artifacts are sibling folders
# round-1/<type>-<k>/src of this artifact's round-2/experiment-8/src. Everything this artifact needs from them is
# already snapshotted under inputs/ (with inputs/iter1/MANIFEST.sha256), so they are only needed to re-run S0.
UPSTREAM_ROOT = Path(os.environ.get("BRT_UPSTREAM_ROOT", str(ROOT.parents[2] / "round-1")))
# art_j3Rm_lr2nzR6: "Source data for an algorithm-choice coding bench" (concreteness_norms -> neutral nouns)
DATASET_DIR = Path(os.environ.get("BRT_DATASET_DIR", str(UPSTREAM_ROOT / "dataset-1" / "src")))
# Iteration-1 experiments: exp1 art__skdlFp_o3e9 (canonical suite), exp2 art_D6Z0Snf09sFL, exp3 art_1yV2vQ0EH4OY,
# exp4 art_U5UKkFrOgSsE, exp5 art_HF8nK8B_Lqyy.
UPSTREAM_IDS = {"exp1": "art__skdlFp_o3e9", "exp2": "art_D6Z0Snf09sFL", "exp3": "art_1yV2vQ0EH4OY",
                "exp4": "art_U5UKkFrOgSsE", "exp5": "art_HF8nK8B_Lqyy", "dataset": "art_j3Rm_lr2nzR6"}
ITER1_EXP_DIRS = {e: Path(os.environ.get(f"BRT_{e.upper()}_DIR", str(UPSTREAM_ROOT / f"experiment-{e[-1]}" / "src")))
                  for e in ("exp1", "exp2", "exp3", "exp4", "exp5")}
INPUTS = ROOT / "inputs"
INPUTS_ITER1 = INPUTS / "iter1"
SUITE = ROOT / "suite"  # working copy of exp1's canonical suite (tasks/, labeller/, common.py)
PROMPTS_DIR = ROOT / "prompts"
DATA_DIR = ROOT / "data"
TOKEN_LP_DIR = DATA_DIR / "token_lp"
RESULTS_DIR = ROOT / "results"
FIG_DIR = ROOT / "figures"
LOG_DIR = ROOT / "logs"
WORK_DIR = ROOT / "work"
for _d in (PROMPTS_DIR, DATA_DIR, TOKEN_LP_DIR, RESULTS_DIR, FIG_DIR, LOG_DIR, WORK_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------------------------------------------ model
MODEL_ID = "Qwen/Qwen3-8B"
MODEL_REVISION = "b968826d9c46dd6066d109eabc6255188de91218"  # the Hub snapshot every number here was produced with


def model_path() -> str:
    """BRT_MODEL_PATH (a local copy of the pinned snapshot) if set; else that snapshot inside the Hugging Face cache
    named by HF_HUB_CACHE if it is complete; else the Hub id (loaded at MODEL_REVISION, see hf_kwargs)."""
    env = os.environ.get("BRT_MODEL_PATH")
    if env:
        return env
    cache = os.environ.get("HF_HUB_CACHE")
    if cache:
        snap = Path(cache) / "models--Qwen--Qwen3-8B" / "snapshots" / MODEL_REVISION
        if all((snap / f"model-0000{i}-of-00005.safetensors").exists() for i in range(1, 6)):
            return str(snap)
    return MODEL_ID


def hf_kwargs() -> dict[str, str]:
    """Pin the Hub revision whenever the model is loaded by id."""
    return {"revision": MODEL_REVISION} if model_path() == MODEL_ID else {}


def model_revision() -> str:
    return MODEL_REVISION


N_LAYERS = 36
D_MODEL = 4096
IM_END = 151645
ENDOFTEXT = 151643
MAX_NEW_TOKENS = 1024
TEMPERATURE = 1.0
DECODING = "T1.0_topp1.0_topk-off_max1024_thinkoff"

# ------------------------------------------------------------------------------------------------ tasks
TASKS = ("t1", "t2")
X_KEY = {"t1": "bfs", "t2": "dijkstra"}
SUB_KEY = {"t1": "dfs", "t2": "bf_spfa"}  # the dominant substitute in iteration 1
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
ALGOS = {t: list(DISPLAY[t].keys()) for t in TASKS}
SURVIVORS = {t: [a for a in ALGOS[t] if a != X_KEY[t]] for t in TASKS}

# W1-W5: (ban, mention, neutral) verbatim from the shared protocol v2.
TEMPLATES: dict[str, tuple[str, str, str]] = {
    "W1": ("Do not use {X} for this task.", "You could use {X} for this task.", "Do not use {N} for this task."),
    "W2": ("Your solution must not rely on {X}.", "Your solution may rely on {X}.", "Your solution must not rely on {N}."),
    "W3": ("Avoid {X} entirely.", "Consider {X} first.", "Avoid {N} entirely."),
    "W4": ("{X} is not allowed here.", "{X} is allowed here.", "{N} is not allowed here."),
    "W5": ("Write a correct solution that does not use {X}.", "Write a correct solution that may use {X}.",
           "Write a correct solution that does not use {N}."),
}
TEMPLATE_IDS = list(TEMPLATES.keys())

FORCED_PARAPHRASES = [
    "Implement {j} for this task.",
    "Use {j} to solve this task.",
    "Solve this task with {j}.",
    "Write an implementation of {j} for this task.",
    "Your solution should use {j}.",
    "Apply {j} to this task.",
    "Base your solution on {j}.",
    "Solve the task below using {j}.",
    "Implement the task with {j}.",
    "Write the solution using {j}.",
]
DESCRIPTIVE_VARIANT: dict[str, dict[str, str]] = {
    "t1": {
        "bfs": "Implement breadth-first search (BFS): explore cells in order of distance from start with a FIFO queue "
               "and a visited set, recording parents to rebuild the path.",
        "dfs": "Implement depth-first search (DFS): follow one branch as deep as possible with an explicit stack or "
               "recursion and a visited set, backtracking when stuck.",
        "bibfs": "Implement bidirectional BFS: run one breadth-first search from start and one from goal, expanding "
                 "them alternately until the two frontiers meet, then join the two half-paths.",
        "iddfs": "Implement iterative deepening DFS (IDDFS): run depth-limited depth-first searches with limits 0, 1, "
                 "2, ... until the goal is found.",
        "astar_gbfs": "Implement A* search: a priority queue ordered by f = g + h, where g is the path length so far "
                      "and h is the Manhattan distance to the goal.",
        "dijkstra": "Implement Dijkstra's algorithm on the grid with unit edge weights: a priority queue ordered by "
                    "the distance from start only, with no heuristic toward the goal.",
    },
    "t2": {
        "dijkstra": "Implement Dijkstra's algorithm: a binary-heap priority queue of tentative distances from s, "
                    "popping the smallest distance each time.",
        "bf_spfa": "Implement Bellman-Ford: relax every edge in repeated passes, up to n - 1 rounds, stopping early "
                   "when no distance changes.",
        "bidijkstra": "Implement bidirectional Dijkstra: run Dijkstra forward from s and backward from t on the "
                      "reversed graph, alternating, and stop when the two searches meet.",
        "floyd": "Implement Floyd-Warshall: compute all-pairs shortest paths with a triple loop over k, i, j that "
                 "updates dist[i][j] = min(dist[i][j], dist[i][k] + dist[k][j]).",
        "dial": "Implement Dial's algorithm: Dijkstra with a bucket queue, a list of buckets indexed by distance and "
                "scanned in increasing order instead of a binary heap.",
    },
}

# Signature vocabularies (frozen). Used only for per-token localisation and the lens.
SIGNATURE_VOCAB: dict[str, list[str]] = {
    "bfs": ["deque", "popleft", "collections"],
    "dfs": ["stack", "pop()", "setrecursionlimit"],
    "dijkstra": ["heapq", "heappush", "heappop", "heapify"],
    "astar_gbfs": ["heapq", "heuristic", "abs("],
    "bf_spfa": ["deque", "popleft", "in_queue", "inq", "range(n - 1)"],
}
SUBSTITUTE_VOCAB_KEY = {"t1": "dfs", "t2": "bf_spfa"}

# Catalogue-name scrub regex (case-insensitive), frozen.
SCRUB_REGEX = (r"bfs|breadth|dfs|depth[-_ ]?first|dijkstra|bellman|ford|spfa|floyd|warshall|dial|bucket[-_ ]?queue|"
               r"a\*|astar|a_star|best[-_ ]?first|greedy|bidirectional|bi_?bfs|iddfs|iterative[-_ ]?deepening")

# ------------------------------------------------------------------------------------------------ arms
MAIN_ARMS = ("a", "b", "c", "d")
X_ONLY_ARMS = ("e", "f", "pl", "K0", "K1", "K2", "B1", "B2", "B3", "K0b")
KO_WINDOW = 16
LAYER_BANDS = {"B1": list(range(0, 12)), "B2": list(range(12, 24)), "B3": list(range(24, 36))}
N_PROGRAMS = 30
BEH_PER_TEMPLATE = 20
LENS_LAYERS = list(range(0, N_LAYERS + 1))
C5_LAYERS = list(range(8, 29))

THRESHOLDS = {
    "F_confirm": 2.0 / 3.0,
    "F_ci_lower": 0.5,
    "placebo_max_frac": 0.20,
    "ess_flag": 5.0,
    "c5_rho": -0.5,
    "c5_alpha": 0.05,
    "gate_avoidance": 0.5,
    "gate_min_nonbanned": 20,
    "crn_floor_min": 0.95,
    "veto_log_rank": 1.0,
}
N_BOOT = 2000
N_PERM_C5 = 10000
N_RANDOM_DIRS = 200
JUDGE_MODEL = "openai/gpt-4.1-mini"
JUDGE_CAP_USD = 0.5


# ------------------------------------------------------------------------------------------------ utils
def setup_logging(name: str) -> None:
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    logger.add(str(LOG_DIR / f"{name}.log"), rotation="30 MB", level="DEBUG")


def set_ram_limit(gb: float) -> None:
    """Hard address-space cap so a runaway allocation raises MemoryError instead of OOM-killing the container."""
    lim = int(gb * 1024 ** 3)
    try:
        resource.setrlimit(resource.RLIMIT_AS, (lim, lim))
    except (ValueError, OSError) as e:
        logger.warning(f"could not set RLIMIT_AS: {e}")


def container_ram_gb() -> float | None:
    for p in ("/sys/fs/cgroup/memory.max", "/sys/fs/cgroup/memory/memory.limit_in_bytes"):
        try:
            v = Path(p).read_text().strip()
            if v != "max" and int(v) < 1_000_000_000_000:
                return int(v) / 1e9
        except (FileNotFoundError, ValueError):
            pass
    return None


def detect_cpus() -> int:
    try:
        parts = Path("/sys/fs/cgroup/cpu.max").read_text().split()
        if parts[0] != "max":
            return math.ceil(int(parts[0]) / int(parts[1]))
    except (FileNotFoundError, ValueError):
        pass
    try:
        return len(os.sched_getaffinity(0))
    except (AttributeError, OSError):
        return os.cpu_count() or 1


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def stable_seed(*parts: Any) -> int:
    """Deterministic 63-bit seed from arbitrary parts (sha256 of their '|'-joined repr)."""
    return int(hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest(), 16) % (2 ** 63)


def read_jsonl(p: Path) -> list[dict[str, Any]]:
    if not Path(p).exists():
        return []
    out = []
    with open(p) as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def write_jsonl(p: Path, rows: Iterable[dict[str, Any]]) -> None:
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    with open(tmp, "w") as fh:
        for r in rows:
            fh.write(json.dumps(r, default=_json_default) + "\n")
    tmp.replace(p)


def append_jsonl(p: Path, rows: Iterable[dict[str, Any]]) -> None:
    with open(p, "a") as fh:
        for r in rows:
            fh.write(json.dumps(r, default=_json_default) + "\n")


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
    if isinstance(o, Path):
        return str(o)
    if isinstance(o, set):
        return sorted(o)
    raise TypeError(f"not JSON serialisable: {type(o)}")


def write_json(p: Path, obj: Any, indent: int | None = 1) -> None:
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(_finite(obj), indent=indent, default=_json_default))
    tmp.replace(p)


def _finite(o: Any) -> Any:
    """Replace NaN/inf floats with None so the JSON stays standard."""
    if isinstance(o, float):
        return o if math.isfinite(o) else None
    if isinstance(o, dict):
        return {k: _finite(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_finite(v) for v in o]
    return o


def wilson_ci(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, c - h), min(1.0, c + h))


def cap_first(s: str) -> str:
    return s[:1].upper() + s[1:] if s else s


def spec_text(task: str) -> str:
    """Canonical exp1 SPEC (DESCRIPTION + blank line + FORMAT), read from the snapshotted conditions.json."""
    p = INPUTS_ITER1 / "exp1" / "prompts" / "conditions.json"
    if not p.exists():
        p = ITER1_EXP_DIRS["exp1"] / "prompts" / "conditions.json"
    return json.loads(p.read_text())["spec"][task]


def user_prompt(segment: str, task: str) -> str:
    """exp1 rule: [condition segment, first character upper-cased] + blank line + [SPEC]."""
    return cap_first(segment) + "\n\n" + spec_text(task)


TEMPLATE_TAIL = "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"


def chat_ids(tok: Any, user_text: str) -> list[int]:
    ids = tok.apply_chat_template([{"role": "user", "content": user_text}], tokenize=True,
                                  add_generation_prompt=True, enable_thinking=False)
    if isinstance(ids, dict):
        ids = ids["input_ids"]
    return list(ids)


def chat_text(tok: Any, user_text: str) -> str:
    return tok.apply_chat_template([{"role": "user", "content": user_text}], tokenize=False,
                                   add_generation_prompt=True, enable_thinking=False)
