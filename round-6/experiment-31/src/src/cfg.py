#!/usr/bin/env python3
"""Shared constants, paths and small utilities for Claim S (Gemma plan variable read and steered with Gemma Scope 2).

Iteration 6 artifact. Conventions are ported from the iteration-5 Gemma artifact exp28 (engine, prompts, labellers):
- BLOCK l = decoder block l (0-based); its output is HF hidden_states[l + 1] = resid_post of layer l, the hook point
  of the Gemma Scope 2 resid_post SAEs ('model.layers.<l>.output').
- SPEC positions S = [spec_start, spec_end): from the first token of 'Task:' to the last token of the user message.
- CRN slot = (task, template, k); uniforms PCG64(stable_seed(prefix, task, template, k)) with prefix 'iter5E' for
  slots 0-9 (reproducing exp28's twin slots) and 'iter6S' for every new slot; every coupled arm shares the stream.
- Every coupled single-prompt batch has the fixed shape B_CRN (padded with dummy rows when needed), so that a
  slot's computation is independent of its batch-mates (exp17/exp23/exp28 convention).
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
E18 = INPUTS / "exp18"
E23 = INPUTS / "exp23"
DEP1 = INPUTS / "art_j3Rm_lr2nzR6"
BENCH = E11 / "bench"
SUITE = E8 / "suite"
DATA_DIR = ROOT / "data"
CACHE_DIR = ROOT / "cache"
RESULTS_DIR = ROOT / "results"
FIG_DIR = ROOT / "figures"
LOG_DIR = ROOT / "logs"
PRED_DIR = ROOT / "predictions"
AUDIT_DIR = ROOT / "audit"
STATES_DIR = CACHE_DIR / "states"
for _d in (DATA_DIR, RESULTS_DIR, FIG_DIR, LOG_DIR, PRED_DIR, CACHE_DIR, AUDIT_DIR, STATES_DIR):
    _d.mkdir(parents=True, exist_ok=True)
COMMIT_LOG = ROOT / "commitments.log"
PATHS_LOCAL = ROOT / "paths.local.json"  # unpublished map {short name: upstream workspace} used only by stage_inputs

# ------------------------------------------------------------------------------------------------ models
IT_ID = "google/gemma-3-4b-it"
IT_REV = "093f9f388b31de276ce2de164bdc2081324b9767"
PT_ID = "google/gemma-3-4b-pt"
PT_REV = "cc012e0a6d0787b4adcc0fa2c4da74402494554d"   # pinned at preflight (huggingface_hub model_info sha)
PT_FALLBACK = ("unsloth/gemma-3-4b-pt", "52aba93981c6ad7712b030eb6dd496ece1d279d6")
MODELS = {"it": (IT_ID, IT_REV), "pt": (PT_ID, PT_REV)}
N_LAYERS = 34
D_MODEL = 2560
BAND = list(range(11, 23))             # middle third of 34 blocks
CAPTURE_BLOCKS = list(range(11, 34))   # realised displacement logged from BAND start to the last block
BOS_ID = 2
EOS_ID = 1
SOT_ID = 105                           # <start_of_turn> (asserted against the tokenizer at load)
EOT_ID = 106                           # <end_of_turn>
STOP_IDS = {"it": (EOS_ID, EOT_ID), "pt": (EOS_ID, EOT_ID, SOT_ID)}
CHAT_HEAD = "<bos><start_of_turn>user\n"
CHAT_TAIL = "<end_of_turn>\n<start_of_turn>model\n"
MAX_NEW_BENCH = 1024
MAX_NEW_PATH = 1536
MAX_NEW_PLAIN = 768
MAX_NEW_EXP23 = 640                    # exp23's cap (engine check only)
STOP_CHECK_EVERY = 16
DECODING = "T1.0_topp1.0_topk-off_inverse-CDF-CRN"
PRECISION = "bf16 (sdpa attention); logits fp32, CDF float64"

# ------------------------------------------------------------------------------------------------ tasks
PATH_TASKS = ("T1", "T2")
BENCH12 = ("T03", "T04", "T06", "T05", "T10", "R1", "T08", "R3", "T13", "R6", "T14", "T11")
BENCH_TASKS = BENCH12 + ("R2",)
ALL_TASKS = PATH_TASKS + BENCH_TASKS      # 15 tasks
EXP8_TASK = {"T1": "t1", "T2": "t2"}
# fixed cyclic order of the plan (donor of the cross-task control = next task in this order)
CYCLIC_ORDER = ("T1", "T2", "T03", "T04", "T05", "T06", "T08", "T10", "T11", "T13", "T14", "R1", "R2", "R3", "R6")
# exp23 commit #1 D_g per task: the X whose ban length the frozen twins match (twins are byte-identical to exp23's)
EXP23_TWIN_X = {"T1": "dfs", "T2": "dijkstra", "T03": "full_sort", "T04": "naive", "T06": "hash_set", "T05": "hash_map",
                "T10": "dfs", "R1": "greedy_end", "T08": "iteration", "R3": "kahn", "T13": "sort_sweep",
                "R6": "binary_search", "T14": "sort_by_count", "T11": "patience_bisect", "R2": "dfs_parent"}
TEMPLATES: dict[str, tuple[str, str]] = {  # (ban, neutral twin) -- protocol W1-W5, verbatim (ban side: length only)
    "W1": ("Do not use {X} for this task.", "Do not use {N} for this task."),
    "W2": ("Your solution must not rely on {X}.", "Your solution must not rely on {N}."),
    "W3": ("Avoid {X} entirely.", "Avoid {N} entirely."),
    "W4": ("{X} is not allowed here.", "{N} is not allowed here."),
    "W5": ("Write a correct solution that does not use {X}.", "Write a correct solution that does not use {N}."),
}
TEMPLATE_IDS = list(TEMPLATES)
PAD_FILLER = " ."
MAX_PAD = 24
NOVELTY = "Write a novel algorithm for this task, one you have not seen before."
PLAIN_STDLIB = "Use only the Python standard library."

# ------------------------------------------------------------------------------------------------ design (claim S)
SLOT_PREFIX_OLD = "iter5E"                 # slots 0-9: exp28's twin keys (engine check)
SLOT_PREFIX = "iter6S"                     # every new slot
N_OLD_SLOTS = 10
N_SPLIT_PER_T = 40                         # S3 natural split: 5 templates x 40 slots = N 200 per task
N_CELL_PER_T = 10                          # S8 generation cells: W1-W5 x slots 0-9 = N 50
B_CRN = 20                                 # fixed batch shape of every coupled single-prompt batch (16 GB GPU)
N_MASSIVE = 5
LAMBDA = 1.0
DEFAULT_SHARE = 0.6
OTHER_FLOOR = 0.02
BUDGET_MSG = "AI Inventor per-run OpenRouter budget"
OPENROUTER_CAP_USD = 1.00
NOT_COUNTED = ("invalid", "disputed")
# Gemma Scope 2 instruments (ids asserted against the Hub listing at S0)
SCOPE_REPO = "google/gemma-scope-2-4b-it"
SCOPE_REV = "3e94b68be95290aada5b7525cf431d3040f81bb1"
SAE_LAYERS = (9, 17, 22, 29)
SAE_WIDTH = "16k"
SAE_L0 = "medium"
SAE_IDS = {l: f"resid_post/layer_{l}_width_{SAE_WIDTH}_l0_{SAE_L0}" for l in SAE_LAYERS}
TC_REPO = "mwhanna/gemma-scope-2-4b-it"
TC_REV = "61cb16ec74f348f4a8643fe3a0157be9dc8a851d"
# fork resampling (S4)
FORK_POSITIONS = tuple(range(0, 61, 4))    # coarse scan t in {0, 4, ..., 60}
FORK_CONT = 8                              # continuations per (path, t)
FORK_REFINE_CONT = 16
FORK_MAX_NEW = 320                         # partial-code labeller horizon
FORK_RISE = 0.4
FORK_PERM = 1000
TOKEN_SET_HI = 0.8                         # B = fork tokens with P(BFS | tok) >= 0.8
TOKEN_SET_LO = 0.2                         # D = fork tokens with P(BFS | tok) <= 0.2
# readout (S6)
N_PERM = 1000
DELTA_R2_MIN = 0.10
BA_DELTA_MIN = 0.10
P_MAX = 0.01
SD_Y_MIN = 0.2
# clamps (S8)
K_SET = (5, 20, 50)
LAM_SET = (0.5, 1.0, 2.0)
ACTIVE_FRAC = 0.05
FEAT_DIM_PASS_FRAC = 0.8
FEAT_RANDF_DELTA = 0.20
NOUN_STOPLIST = ("queue", "stack", "line", "wave", "tree", "path", "maze", "river", "road", "map", "net", "graph",
                 "web", "chain", "ring", "layer", "depth", "breadth", "search", "walk")
FORCED_TEMPLATES = {  # positive mirrors of W1-W5
    "F1": "Use {Y} for this task.",
    "F2": "Your solution must rely on {Y}.",
    "F3": "Use {Y} throughout.",
    "F4": "{Y} is required here.",
    "F5": "Write a correct solution that uses {Y}.",
}
T1_MODES = ("bfs", "dfs", "bibfs", "iddfs", "astar_gbfs", "dijkstra")
TOP5_BANNED = ("bfs", "dfs", "iddfs", "astar_gbfs")   # exp9 TOP5 {bfs, dfs, gbfs, iddfs, astar} on the 6-mode catalogue
TOP5_SURVIVORS = ("bibfs", "dijkstra")


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
        q = int(Path("/sys/fs/cgroup/cpu/cpu.cfs_quota_us").read_text())
        p = int(Path("/sys/fs/cgroup/cpu/cpu.cfs_period_us").read_text())
        if q > 0:
            return max(1, math.ceil(q / p))
    except (FileNotFoundError, ValueError):
        pass
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


def ids_sha(ids: list[int]) -> str:
    return hashlib.sha256(json.dumps([int(i) for i in ids]).encode()).hexdigest()


def stable_seed(*parts: Any) -> int:
    """Deterministic 63-bit seed from arbitrary parts (sha256 of their '|'-joined repr) -- exp8/exp23 convention."""
    return int(hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest(), 16) % (2 ** 63)


def read_jsonl(p: Path) -> list[dict[str, Any]]:
    p = Path(p)
    if not p.exists():
        return []
    out = []
    with open(p) as fh:
        lines = fh.readlines()
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            if i == len(lines) - 1:  # a concurrently appended, not yet complete last line
                continue
            logger.warning(f"skipping malformed line {i} in {p.name}")
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


def _finite(o: Any) -> Any:
    if isinstance(o, float):
        return o if math.isfinite(o) else None
    if isinstance(o, dict):
        return {str(k): _finite(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_finite(v) for v in o]
    return o


def append_jsonl(p: Path, rows: Iterable[dict[str, Any]]) -> int:
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(p, "a") as fh:
        for r in rows:
            fh.write(json.dumps(_finite(json.loads(json.dumps(r, default=_json_default)))) + "\n")
            n += 1
        fh.flush()
    return n


def write_jsonl(p: Path, rows: Iterable[dict[str, Any]]) -> None:
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    with open(tmp, "w") as fh:
        for r in rows:
            fh.write(json.dumps(_finite(json.loads(json.dumps(r, default=_json_default)))) + "\n")
    tmp.replace(p)


def write_json(p: Path, obj: Any, indent: int | None = 1) -> None:
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(_finite(json.loads(json.dumps(obj, default=_json_default))), indent=indent))
    tmp.replace(p)


def read_json(p: Path) -> Any:
    return json.loads(Path(p).read_text())


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


def rel(p: Path | str) -> str:
    """Path relative to the artifact root (never write absolute server paths into published files)."""
    try:
        return str(Path(p).resolve().relative_to(ROOT))
    except ValueError:
        return str(p)


def model_path(model_id: str, revision: str | None) -> str:
    cache = os.environ.get("HF_HUB_CACHE")
    if cache:
        snaps = Path(cache) / ("models--" + model_id.replace("/", "--")) / "snapshots"
        if revision and (snaps / revision).exists():
            return str(snaps / revision)
    from huggingface_hub import snapshot_download

    return snapshot_download(model_id, revision=revision,
                             allow_patterns=["*.json", "*.safetensors", "tokenizer.model"])


def add_deviation(key: str, text: str) -> None:
    p = RESULTS_DIR / "deviations.json"
    d = read_json(p) if p.exists() else {}
    d[key] = text
    write_json(p, d)


def bench_paths() -> None:
    """Import paths for the frozen bench (bench.common.*) and the exp8 suite (labeller.*, tasks.*)."""
    for p in (str(SUITE), str(E11)):
        if p not in sys.path:
            sys.path.insert(0, p)


def cap_of(task: str) -> int:
    return MAX_NEW_PATH if task in PATH_TASKS else MAX_NEW_BENCH
