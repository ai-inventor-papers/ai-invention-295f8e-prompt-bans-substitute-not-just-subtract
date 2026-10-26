#!/usr/bin/env python3
"""Shared constants, paths and utilities for the iteration-5 'transplanting the base model's plan' artifact.

Derived from iteration-4 exp19 src/cfg.py (vendored unchanged in src/vendor/exp19/cfg.py); ROOT is this workspace.
The vendored engine (src/engine_v4.py) and label worker (src/label_worker_v4.py) import their constants from here.

Conventions (inherited from iteration-3 exp17 / iteration-4 exp19, restated in README.md):
- BLOCK l = decoder block l (0-based); its output is HF hidden_states[l + 1].
- S = [p1, spec_end): first token of 'Task:' to the last user token (chat tail excluded); R = P - 1.
- CRN slot = (task, template W, j): token uniforms u_stream(task, W, j) shared by EVERY instruct arm of this
  artifact; the base model's own slots use the key (task, W, j, 'base'). One uniform per (row, step), inverse CDF
  in vocabulary order (exp8 sampler), prune=False, fixed batch shape B.
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
INPUTS = ROOT / "inputs"
E8 = INPUTS / "exp8"
E11 = INPUTS / "exp11"
E7 = INPUTS / "exp7"
E13 = INPUTS / "exp13"
E16 = INPUTS / "exp16"
E17 = INPUTS / "exp17"
E18 = INPUTS / "exp18"
E6 = INPUTS / "exp6"
E20 = INPUTS / "exp20"
E22 = INPUTS / "exp22"
E23 = INPUTS / "exp23"
EVAL3 = INPUTS / "eval3"
I1E5 = INPUTS / "iter1_exp5"
DEP = INPUTS / "dep_dataset"
BENCH = E11 / "bench"
SUITE = E8 / "suite"
DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "results"
FIG_DIR = ROOT / "figures"
LOG_DIR = ROOT / "logs"
PRED_DIR = ROOT / "predictions"
AUDIT_DIR = ROOT / "audit"
CACHE_DIR = ROOT / "cache"
STATES_DIR = CACHE_DIR / "states"
for _d in (DATA_DIR, RESULTS_DIR, FIG_DIR, LOG_DIR, PRED_DIR, AUDIT_DIR, STATES_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# Source artifacts (read-only; only Stage 0 reads them). This folder sits at
# <runs>/<run>/3_invention_loop/iter_5/gen_art/<artifact>; each location can be overridden by an environment variable.
def _ancestor(n: int) -> Path:
    """ROOT.parents[n], or ROOT.parent when the checkout is shallower (a cloned repository)."""
    try:
        return ROOT.parents[n]
    except IndexError:
        return ROOT.parent


RUN_ROOT = Path(os.environ.get("AII_LOOP_DIR", _ancestor(2)))  # <run>/3_invention_loop
ITER2 = Path(os.environ.get("AII_ITER2_DIR", RUN_ROOT / "round-2" / "."))
ITER3 = Path(os.environ.get("AII_ITER3_DIR", RUN_ROOT / "round-3" / "."))
ITER4 = Path(os.environ.get("AII_ITER4_DIR", RUN_ROOT / "round-4" / "."))
ITER1 = Path(os.environ.get("AII_ITER1_DIR", _ancestor(4) / "run_4VFKidE1bxPG" / "." / "round-1"
                            / "."))
DEP_DATASET_DIR = Path(os.environ.get("ART_J3RM_DIR") or next(
    (d for d in (ROOT.parent / "art_j3Rm_lr2nzR6",) if d.exists()), ITER1 / "dataset-1/src"))

# ------------------------------------------------------------------------------------------------ models
MODEL_ID = "Qwen/Qwen3-8B"
MODEL_REVISION = "b968826d9c46dd6066d109eabc6255188de91218"
BASE_ID = "Qwen/Qwen3-8B-Base"
BASE_REVISION = "49e3418fbbbca6ecbdf9608b4d22e5a407081db4"   # ITER1 exp5 reproducibility.md (pinned for comparability)
N_LAYERS = 36
D_MODEL = 4096
IM_END = 151645
IM_START = 151644
ENDOFTEXT = 151643
MAX_NEW_TOKENS = 1024          # bench tasks (and instruct path tasks: the exp17/exp19 cap)
MAX_NEW_PATH = 1024            # instruct T1/T2 (iteration-4 cap, kept for comparability)
MAX_NEW_BASE_PATH = 1536       # base model T1/T2 (plan 1.3)
TEMPLATE_TAIL = "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"
ENGINE_TAG = "hf_bf16"
QUANT = "bf16 (precision rule: GPU >= 19.5 GiB)"


def model_path(model_id: str = MODEL_ID, revision: str | None = MODEL_REVISION) -> str:
    cache = os.environ.get("HF_HUB_CACHE")
    if cache:
        snaps = Path(cache) / ("models--" + model_id.replace("/", "--")) / "snapshots"
        if revision and (snaps / revision).exists():
            return str(snaps / revision)
    return model_id


# ------------------------------------------------------------------------------------------------ tasks
PATH_TASKS = ("T1", "T2")
MOVABLE = ("T03", "T2", "T05", "T10", "T06", "T1")          # iteration-4 frozen movable set (exp22 order)
OTHER9 = ("T04", "T08", "T11", "T13", "T14", "R1", "R3", "R6", "R2")
TASKS15 = MOVABLE + OTHER9
BENCH12 = ("T03", "T04", "T06", "T05", "T10", "R1", "T08", "R3", "T13", "R6", "T14", "T11")
BENCH_TASKS = BENCH12 + ("R2",)
ALL_TASKS = PATH_TASKS + BENCH_TASKS
# iteration-4 defaults (exp19/exp22); this artifact re-derives default_t from its own S1 twin (plan 1.6)
DEFAULT = {"T1": "bfs", "T2": "dijkstra", "T03": "full_sort", "T04": "naive", "T06": "hash_set", "T05": "hash_map",
           "T10": "union_find", "R1": "greedy_end", "T08": "iteration", "R3": "kahn", "T13": "sort_sweep",
           "R6": "binary_search", "T14": "sort_by_count", "T11": "quadratic_dp", "R2": "dfs_parent"}
EXP8_TASK = {"T1": "t1", "T2": "t2"}
PATH_CATALOGUE = {"T1": ["bfs", "dfs", "bibfs", "iddfs", "astar_gbfs", "dijkstra"],
                  "T2": ["dijkstra", "bf_spfa", "bidijkstra", "floyd", "dial"]}
TEMPLATE_IDS = ["W1", "W2", "W3", "W4", "W5"]
TEMPLATES: dict[str, tuple[str, str]] = {  # (ban, neutral) -- protocol v2 W1-W5, verbatim (exp19 cfg)
    "W1": ("Do not use {X} for this task.", "Do not use {N} for this task."),
    "W2": ("Your solution must not rely on {X}.", "Your solution must not rely on {N}."),
    "W3": ("Avoid {X} entirely.", "Avoid {N} entirely."),
    "W4": ("{X} is not allowed here.", "{N} is not allowed here."),
    "W5": ("Write a correct solution that does not use {X}.", "Write a correct solution that does not use {N}."),
}
PAD_FILLER = " ."

# ------------------------------------------------------------------------------------------------ design
V_BLOCKS = list(range(12, 24))          # transplant / push band (task-spec positions, prefill only)
EARLY_BLOCKS = list(range(0, 12))
LATE_BLOCKS = list(range(24, 36))
ALL_BLOCKS = list(range(N_LAYERS))
NORM_BLOCKS = list(range(12, N_LAYERS))  # realised displacement logged at blocks 12-35 (+ R)
GEO_BLOCKS_S = (18, 23, 27)
GEO_BLOCKS_R = (18, 23)
S1_SLOTS = list(range(10))              # selection slots j = 0..9 (N = 50 per task)
S2_SLOTS_100 = list(range(10, 30))      # confirmation slots (N = 100)
S2_SLOTS_50 = list(range(10, 20))       # confirmation slots (N = 50)
DS_SLOTS = list(range(10, 16))          # Claim D slots (N = 30), paired with TWIN_S2
BASE_CHAT_N = 100                       # per task (5 templates x 20)
BASE_CHAT_N_PATH = 200                  # T1/T2 (5 x 40)
BASE_PLAIN_N = 100
TOPUP_MIN_CORRECT = 30
TOPUP_N = 100
LAMBDAS = (0.25, 0.5, 1.0)
DS_ALPHAS = (0.5, 1.0, 2.0)
BETA_DIVERSE = 0.20
BETA_COLLAPSED = 0.05
DEFAULT_SHARE_MIN = 0.6
PASS_FRAC = 0.8
DERANGEMENT_SEED = 20261021
BOOT_SEED = 20261021
N_BOOT = 2000
N_RAREFY = 1000
DEPTH = 25
JUDGE_CAP_USD = 1.5
BUDGET_MSG = "AI Inventor per-run OpenRouter budget"
BASE_KEY = "base"


# ------------------------------------------------------------------------------------------------ utils
def setup_logging(name: str) -> None:
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    logger.add(str(LOG_DIR / f"{name}.log"), rotation="30 MB", level="DEBUG")


def set_ram_limit(gb: float) -> None:
    lim = int(gb * 1024 ** 3)
    try:
        resource.setrlimit(resource.RLIMIT_AS, (lim, lim))
    except (ValueError, OSError) as e:
        logger.warning(f"could not set RLIMIT_AS: {e}")


def detect_cpus() -> int:
    try:
        q = int(Path("/sys/fs/cgroup/cpu/cpu.cfs_quota_us").read_text())
        p = int(Path("/sys/fs/cgroup/cpu/cpu.cfs_period_us").read_text())
        if q > 0:
            return max(1, math.ceil(q / p))
    except (FileNotFoundError, ValueError):
        pass
    try:
        return len(os.sched_getaffinity(0))
    except (AttributeError, OSError):
        return os.cpu_count() or 1


def container_ram_gb() -> float | None:
    for p in ["/sys/fs/cgroup/memory.max", "/sys/fs/cgroup/memory/memory.limit_in_bytes"]:
        try:
            v = Path(p).read_text().strip()
            if v != "max" and int(v) < 1_000_000_000_000:
                return int(v) / 1e9
        except (FileNotFoundError, ValueError):
            pass
    return None


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
    """Deterministic 63-bit seed from arbitrary parts (sha256 of their '|'-joined repr) -- exp8/exp17 convention."""
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
    p = RESULTS_DIR / "deviations.jsonl"
    rows = read_jsonl(p)
    if any(r.get("id") == did for r in rows):
        return
    append_jsonl(p, [{"id": did, "utc": utc_now(), "deviation": text}])
    logger.warning(f"DEVIATION {did}: {text}")


def bench_paths() -> None:
    for p in (str(SUITE), str(E11)):
        if p not in sys.path:
            sys.path.insert(0, p)


def catalogue(task: str) -> list[str]:
    """Catalogue modes of a task (bench spec.json; exp8 suite CATALOGUE for T1/T2)."""
    if task in PATH_TASKS:
        return list(PATH_CATALOGUE[task])
    d = next(x for x in BENCH.iterdir() if x.is_dir() and x.name.startswith(task + "_"))
    return [c["mode"] for c in read_json(d / "spec.json")["catalogue"]]


def bench_dir(task: str) -> Path:
    return next(x for x in BENCH.iterdir() if x.is_dir() and x.name.startswith(task + "_"))


N_HEADS = 32
HEAD_DIM = 128
