#!/usr/bin/env python3
"""Shared constants, paths and utilities for iteration-5 panel A ('can the base model forecast nudgeable tasks?').

Conventions inherited from iteration 4 (exp19 cfg.py), unchanged unless stated:
- BLOCK l = decoder block l (0-based); its output is HF hidden_states[l + 1].
- SPEC positions S = [p1, spec_end): from the first 'Task:' token to the last user token (chat tail excluded).
- CRN slot = (unit, template w, k); uniforms u_stream(unit, w, k) = PCG64(stable_seed(unit, w, k)).random(max_new) are
  shared by every arm AND by both models (base rows use the instruct twin's token ids and the same streams).
- Escape directions: rand_dir(seed) = PCG64(seed).standard_normal(4096) / norm, the same u at every block 12-23.
- PN direction of a row: stable_seed('i5A', 'PN', unit, alpha, w, k) (a fresh direction per row).
- Ban-free dose unit: n[l, p] = ||h_twin_clean[l, p]|| * r_Q(l), r_Q interpolated over relative depth (l + 1) / 36
  (exp23 units.r_at(l, 'r_Q'), results/qwen_ratio.json).
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

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
INPUTS = ROOT / "inputs"
DATA = ROOT / "data"
RAW_DIR = DATA / "raw"
LAB_DIR = DATA / "labels"
RESULTS = ROOT / "results"
PRED = ROOT / "predictions"
FIGS = ROOT / "figures"
LOGS = ROOT / "logs"
QUEUE = ROOT / "queue"
STATES = ROOT / "states"
NEWBENCH = ROOT / "newbench"
GOLD = ROOT / "gold_draws"
AUDIT = ROOT / "audit"
for _d in (DATA, RAW_DIR, LAB_DIR, RESULTS, PRED, FIGS, LOGS, QUEUE, QUEUE / "done", QUEUE / "failed", STATES,
           NEWBENCH, GOLD, AUDIT):
    _d.mkdir(parents=True, exist_ok=True)

# copied inputs (read-only copies of earlier iterations, sha256 manifest in inputs/MANIFEST.sha256)
E11 = INPUTS / "exp11"          # iteration-2 bench (13 tasks) + common toolkit
E8 = INPUTS / "exp8"            # iteration-2 path suite (T1/T2)
E13 = INPUTS / "exp13"
E17 = INPUTS / "exp17"
E19 = INPUTS / "exp19"
E22 = INPUTS / "exp22"
E23 = INPUTS / "exp23"
EVAL3 = INPUTS / "eval3"
BENCH = E11 / "bench"
SUITE = E8 / "suite"
DEP = INPUTS / "dep_dataset"
COMMIT_LOG = ROOT / "commitments.log"

# ------------------------------------------------------------------------------------------------ models
MODELS = {
    "instruct": {"id": "Qwen/Qwen3-8B", "revision": "b968826d9c46dd6066d109eabc6255188de91218"},
    "base": {"id": "Qwen/Qwen3-8B-Base", "revision": "49e3418fbbbca6ecbdf9608b4d22e5a407081db4"},
}
N_LAYERS = 36
D_MODEL = 4096
IM_END = 151645
ENDOFTEXT = 151643
IM_START = 151644
STOP_IDS = {"instruct": (IM_END, ENDOFTEXT), "base": (IM_END, ENDOFTEXT, IM_START)}
MAX_NEW_BENCH = 1024
MAX_NEW_PATH = 1536
MAX_NEW_ASSOC = 64
TEMPLATE_TAIL = "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"

# ------------------------------------------------------------------------------------------------ protocol
TEMPLATES: dict[str, tuple[str, str]] = {  # (ban, neutral) -- protocol v2 W1-W5, verbatim (exp19 cfg.py)
    "W1": ("Do not use {X} for this task.", "Do not use {N} for this task."),
    "W2": ("Your solution must not rely on {X}.", "Your solution must not rely on {N}."),
    "W3": ("Avoid {X} entirely.", "Avoid {N} entirely."),
    "W4": ("{X} is not allowed here.", "{N} is not allowed here."),
    "W5": ("Write a correct solution that does not use {X}.", "Write a correct solution that does not use {N}."),
}
TEMPLATE_IDS = list(TEMPLATES)
PAD_FILLER = " ."
NOVELTY = "Write a novel algorithm for this task, one you have not seen before."
FORMAT_LINE = ("Use only the Python standard library. Return only one ```python code block containing the function "
               "solve and any helpers, with no example usage and no explanation.")
ASSOC_TEMPLATE = ("What is the standard alternative to {x} for this task? Name one algorithm and answer in one "
                  "sentence.")
NOUN_EXCLUSIONS = {"ass", "bucket", "chain", "edge", "game", "graph", "grid", "head", "heap", "key", "line", "link",
                   "list", "map", "maze", "net", "node", "path", "point", "queue", "ring", "road", "route", "search",
                   "stack", "step", "street", "table", "track", "train", "tree", "walk", "way", "web"}  # exp13/exp19

V_BLOCKS = list(range(12, 24))            # push blocks (prefill only, spec positions)
NORM_BLOCKS = list(range(12, N_LAYERS))   # realised displacement logged at blocks 12-35 (+ read position)
ESC_SEEDS = [95101, 95102, 95103, 95104, 95105, 95106, 95107, 95108]
USED_SEEDS = list(range(9001, 9016)) + list(range(9101, 9141)) + list(range(9301, 9307))
ALPHAS = (1.0, 2.0)
K_TWIN = list(range(10))        # twin k 0-9 per template (N = 50); k 0-1 are the instruct gold rows
K_BASE = list(range(20))        # base k 0-19 per template (N = 100); k 0-5 are the base pilot rows
K_STAGE1 = [0, 1]               # escape screen: k 0-1 x W1-W5 = 10 rows per (seed, alpha)
K_TOPUP = [2, 3, 4, 5]          # confirmation top-up: + 20 rows
K_PN = list(range(10))          # PN alpha 1 / 2: N = 50 each
K_T13 = list(range(10))         # T 1.3: N = 50
N_NOVELTY = 30
N_ASSOC = 20
N_PLAIN = 50

# thresholds (frozen at commit #0)
BETA_MOVABLE = 0.05
DEFAULT_SHARE = 0.60
ESC_EXCESS = 0.20
ESC_PASS_FRAC = 0.80
P_BINOM = 0.05
MIN_CORRECT_BASE = 20
DEPTH = 25
KAPPA_GATE = 0.80
RT_ADJ_GATE = 0.90
EXCLUDE = ("invalid", "disputed")
N_BOOT = 2000
N_BOOT_RIVAL = 10000
BOOT_SEED = 20261021
JUDGE_CAP_USD = 2.00
BUDGET_MSG = "AI Inventor per-run OpenRouter budget"

# units of panel A (new) -- list order is the build order; A8/A9 are reserves under the mid-artifact rule
NEW_UNITS = ["A1", "A2", "A3", "A4", "A5", "A6", "A7"]
RESERVE_UNITS = ["A8", "A9"]
UNIT_DIRS = {"A1": "A1_majority_element", "A2": "A2_max_subarray", "A3": "A3_trapping_rain_water",
             "A4": "A4_count_primes", "A5": "A5_longest_common_prefix", "A6": "A6_number_of_islands",
             "A7": "A7_longest_palindromic_substring", "A8": "A8_jump_game", "A9": "A9_median_two_sorted"}
LEETCODE_QID = {"A1": 169, "A2": 53, "A3": 42, "A4": 204, "A5": 14, "A6": 200, "A7": 5, "A8": 55, "A9": 4}

# existing tasks (Extra arm A): order = T03, T10 (positive controls) then the 13 others
PATH_TASKS = ("T1", "T2")
EXISTING = ["T03", "T10", "T05", "T06", "T1", "T2", "T04", "T08", "T11", "T13", "T14", "R1", "R3", "R6", "R2"]
EXISTING_DEFAULT = {"T1": "bfs", "T2": "dijkstra", "T03": "full_sort", "T04": "naive", "T06": "hash_set",
                    "T05": "hash_map", "T10": "union_find", "R1": "greedy_end", "T08": "iteration", "R3": "kahn",
                    "T13": "sort_sweep", "R6": "binary_search", "T14": "sort_by_count", "T11": "quadratic_dp",
                    "R2": "dfs_parent"}
ITER4_E = {"T03": (0.30, 0.63), "T10": (0.38, 0.73), "T2": (0.18, 0.20), "T05": (0.0, 0.13), "T1": (0.05, 0.13)}


def model_path(which: str) -> str:
    m = MODELS[which]
    cache = os.environ.get("HF_HUB_CACHE")
    if cache:
        snap = Path(cache) / ("models--" + m["id"].replace("/", "--")) / "snapshots" / m["revision"]
        if snap.exists():
            return str(snap)
    return m["id"]


# ------------------------------------------------------------------------------------------------ utils
def setup_logging(name: str) -> None:
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    logger.add(str(LOGS / f"{name}.log"), rotation="30 MB", level="DEBUG")


def set_ram_limit(gb: float) -> None:
    lim = int(gb * 1024 ** 3)
    try:
        resource.setrlimit(resource.RLIMIT_AS, (lim, lim))
    except (ValueError, OSError) as e:
        logger.warning(f"could not set RLIMIT_AS: {e}")


def detect_cpus() -> int:
    try:
        parts = Path("/sys/fs/cgroup/cpu.max").read_text().split()
        if parts[0] != "max":
            return max(1, math.ceil(int(parts[0]) / int(parts[1])))
    except (FileNotFoundError, ValueError, IndexError):
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
    """Deterministic 63-bit seed from arbitrary parts (sha256 of their '|'-joined str) -- exp8/exp17/exp19."""
    return int(hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest(), 16) % (2 ** 63)


def read_jsonl(p: Path) -> list[dict[str, Any]]:
    p = Path(p)
    if not p.exists():
        return []
    out = []
    with open(p) as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    logger.warning(f"skipping malformed line in {p.name}")
    return out


def _json_default(o: Any) -> Any:
    import numpy as np

    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, Path):
        return str(o)
    if isinstance(o, (set, frozenset)):
        return sorted(o)
    raise TypeError(f"not JSON serialisable: {type(o)}")


def append_jsonl(p: Path, rows: Iterable[dict[str, Any]]) -> None:
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a") as fh:
        for r in rows:
            fh.write(json.dumps(r, default=_json_default) + "\n")
        fh.flush()


def write_jsonl(p: Path, rows: Iterable[dict[str, Any]]) -> None:
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    with open(tmp, "w") as fh:
        for r in rows:
            fh.write(json.dumps(r, default=_json_default) + "\n")
    tmp.replace(p)


def _finite(o: Any) -> Any:
    if isinstance(o, float):
        return o if math.isfinite(o) else None
    if isinstance(o, dict):
        return {str(k): _finite(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_finite(v) for v in o]
    return o


def write_json(p: Path, obj: Any, indent: int | None = 1) -> None:
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(_finite(json.loads(json.dumps(obj, default=_json_default))), indent=indent))
    tmp.replace(p)


def read_json(p: Path) -> Any:
    return json.loads(Path(p).read_text())


def cap_first(s: str) -> str:
    return s[:1].upper() + s[1:] if s else s


def rel(p: Path | str) -> str:
    """Path relative to the artifact root (never write absolute server paths into published files)."""
    try:
        return str(Path(p).resolve().relative_to(ROOT))
    except ValueError:
        return str(p)


def append_deviation(did: str, text: str) -> None:
    p = RESULTS / "deviations.jsonl"
    rows = read_jsonl(p)
    if any(r.get("id") == did for r in rows):
        return
    append_jsonl(p, [{"id": did, "utc": utc_now(), "deviation": text}])
    logger.warning(f"DEVIATION {did}: {text}")


def unit_dir(unit: str) -> Path:
    return NEWBENCH / UNIT_DIRS[unit]


def is_new(task: str) -> bool:
    return task in UNIT_DIRS
