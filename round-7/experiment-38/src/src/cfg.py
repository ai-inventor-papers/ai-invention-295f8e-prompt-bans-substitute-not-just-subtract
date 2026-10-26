#!/usr/bin/env python3
"""Shared constants, paths and small utilities (iteration 7: circuit, dose dial and temperature account at the
BFS-vs-DFS fork of gemma-3-4b-it).

Conventions (ported from the iteration-6 Gemma artifact art_zNyBP6zieI5u, vendored read-only in inputs/iter6_gemma/):
- BLOCK l = decoder block l (0-based); its output is HF hidden_states[l + 1] = resid_post of layer l.
- Response index i = the i-th generated token. c* = the canonical 32-token opening (response indices 0-31).
  The FORK POSITION p_f is the position of c*[31]; the next-token logits there choose response token 32.
- Classes at the fork: B = {107 '\\n', 584 'if', 15204 'queue', 236809 'q'}, D = {53227 'visited'}, O = the rest.
  Fork margin m = logsumexp(z[B]) - z[53227] at p_f (prompt + c* teacher-forced); y_v = m of twin variant v.
- CRN: one uniform stream per slot, PCG64(stable_seed(*ukey)); reproduced iteration-6 slots use iteration 6's own
  slot_key ('iter5E' for slots 0-9); every new slot uses 'iter7G' + part name (G1, G2, G3, U6, G3cal).
- Every coupled single-prompt batch has one fixed shape B_CRN (chosen by the S0 time test, frozen in commit #0).
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
I6 = ROOT / "inputs" / "iter6_gemma"            # read-only copy of the iteration-6 Gemma artifact (MANIFEST.sha256)
INPUTS = I6 / "inputs"
E8 = INPUTS / "exp8"
E11 = INPUTS / "exp11"
E7 = INPUTS / "exp7"
E9 = INPUTS / "exp9"
E23 = INPUTS / "exp23"
DEP1 = INPUTS / "art_j3Rm_lr2nzR6"
DEP_EXTRACT = INPUTS / "dep_extract"
BENCH = E11 / "bench"
SUITE = E8 / "suite"
I6_RESULTS = I6 / "results"
I6_DATA = I6 / "data"
DATA_DIR = ROOT / "data"
CACHE_DIR = ROOT / "cache"
RESULTS_DIR = ROOT / "results"
FIG_DIR = ROOT / "figures"
LOG_DIR = ROOT / "logs"
PRED_DIR = ROOT / "predictions"
AUDIT_DIR = ROOT / "audit"
STATES_DIR = CACHE_DIR / "states"
SUBSPACE_DIR = CACHE_DIR / "das_subspaces"
for _d in (DATA_DIR, RESULTS_DIR, FIG_DIR, LOG_DIR, PRED_DIR, CACHE_DIR, AUDIT_DIR, STATES_DIR, SUBSPACE_DIR):
    _d.mkdir(parents=True, exist_ok=True)
COMMIT_LOG = ROOT / "commitments.log"

# ------------------------------------------------------------------------------------------------ models
IT_ID = "google/gemma-3-4b-it"
IT_REV = "093f9f388b31de276ce2de164bdc2081324b9767"
MODELS = {"it": (IT_ID, IT_REV)}
N_LAYERS = 34
D_MODEL = 2560
N_HEADS = 8
HEAD_DIM = 256
CAPTURE_BLOCKS = list(range(11, 34))
BOS_ID = 2
EOS_ID = 1
SOT_ID = 105
EOT_ID = 106
STOP_IDS = {"it": (EOS_ID, EOT_ID)}
CHAT_HEAD = "<bos><start_of_turn>user\n"
CHAT_TAIL = "<end_of_turn>\n<start_of_turn>model\n"
MAX_NEW = 1024                         # natural T1 programs: median 315, max 413 tokens (iteration 6, n = 200)
MAX_NEW_PATH = MAX_NEW
MAX_NEW_BENCH = MAX_NEW
STOP_CHECK_EVERY = 16
PRECISION = "bf16 (sdpa attention); logits fp32, CDF float64"
TC_REPO = "mwhanna/gemma-scope-2-4b-it"
TC_REV = "61cb16ec74f348f4a8643fe3a0157be9dc8a851d"
TC_SUB = "transcoder_all/width_16k_l0_big_affine"
TC_SUB_SMALL = "transcoder_all/width_16k_l0_small_affine"
SCOPE_REPO = "google/gemma-scope-2-4b-it"
CT_COMMIT = "255d989e93be1299d53d67b59e9fd76a0e274b14"   # safety-research/circuit-tracer HEAD on 2026-10-22

# ------------------------------------------------------------------------------------------------ tasks (T1 only)
PATH_TASKS = ("T1", "T2")
EXP8_TASK = {"T1": "t1", "T2": "t2"}
EXP23_TWIN_X = {"T1": "dfs", "T2": "dijkstra"}
TEMPLATES: dict[str, tuple[str, str]] = {
    "W1": ("Do not use {X} for this task.", "Do not use {N} for this task."),
    "W2": ("Your solution must not rely on {X}.", "Your solution must not rely on {N}."),
    "W3": ("Avoid {X} entirely.", "Avoid {N} entirely."),
    "W4": ("{X} is not allowed here.", "{N} is not allowed here."),
    "W5": ("Write a correct solution that does not use {X}.", "Write a correct solution that does not use {N}."),
}
TEMPLATE_IDS = list(TEMPLATES)
TRAIN_W = ("W1", "W2", "W3")
HELD_W = ("W4", "W5")
FORCED_TEMPLATES = {
    "F1": "Use {Y} for this task.",
    "F2": "Your solution must rely on {Y}.",
    "F3": "Use {Y} throughout.",
    "F4": "{Y} is required here.",
    "F5": "Write a correct solution that uses {Y}.",
}
TRAIN_F = ("F1", "F2", "F3")
HELD_F = ("F4", "F5")
# display-name pairs (BFS, DFS) with equal Gemma token counts within each pair (asserted at S0)
DISPLAY_PAIRS = (("BFS", "DFS"),
                 ("breadth-first search", "depth-first search"),
                 ("a breadth-first search", "a depth-first search"),
                 ("breadth-first search (BFS)", "depth-first search (DFS)"))
PAD_FILLER = " ."
MAX_PAD = 24
NOVELTY = "Write a novel algorithm for this task, one you have not seen before."
PLAIN_STDLIB = "Use only the Python standard library."
T1_MODES = ("bfs", "dfs", "bibfs", "iddfs", "astar_gbfs", "dijkstra")
NOT_COUNTED = ("invalid", "disputed")
BUDGET_MSG = "AI Inventor per-run OpenRouter budget"
OPENROUTER_CAP_USD = 0.50

# ------------------------------------------------------------------------------------------------ design (iteration 7)
SLOT_PREFIX_OLD = "iter5E"             # iteration 6's slot_key for slots 0-9 (engine check reproduces these keys)
SLOT_PREFIX_I6 = "iter6S"
SLOT_PREFIX = "iter7G"
N_OLD_SLOTS = 10
FORK_INDEX = 32
B_IDS = (107, 584, 15204, 236809)
D_IDS = (53227,)
B_STRS = ("\n", "if", "queue", "q")
D_STRS = ("visited",)
I6_NATURAL = {"k": 61, "n": 200, "ci95": (0.245, 0.372)}
DAS_LAYERS_SCAN = (17, 19, 21, 22, 23, 25, 27, 29)
DAS_LAYER_FIXED = 22
DAS_RANKS = (1, 2, 4, 8)
DAS_SEEDS = (0, 1, 2)
DAS_STEPS = 400
DAS_LR = 2e-2                          # plan: 2e-3; the toy shows 2e-3 x 400 steps does not move the subspace
DAS_BATCH = 48                         # plan: 64; 48 fits the 16 GB GPU with the base KV stacks
DOSES = (0.1, 0.2, 0.35, 0.5, 0.75, 1.0)
TEMPS = (0.3, 0.7, 1.0, 1.3)
SAMPLERS = ("topp1", "topk10")
TOPK = 10


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


def slot_key_i6(task: str, w: str, k: int) -> tuple[str, str, str, int]:
    """Iteration 6's slot_key (method.py): 'iter5E' for slots 0-9, 'iter6S' otherwise."""
    return (SLOT_PREFIX_OLD if k < N_OLD_SLOTS else SLOT_PREFIX_I6, task, w, k)


def slot_key7(part: str, w: str, k: int) -> tuple[str, str, str, int]:
    return (SLOT_PREFIX + part, "T1", w, k)


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
            if i == len(lines) - 1:
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
    for p in (str(SUITE), str(E11)):
        if p not in sys.path:
            sys.path.insert(0, p)


def cap_of(task: str) -> int:
    return MAX_NEW


def b_crn() -> int:
    """The fixed batch shape frozen in commit #0 (S0 time test)."""
    p = PRED_DIR / "commit0.json"
    if p.exists():
        return int(read_json(p)["design"]["B_CRN"])
    return 25
