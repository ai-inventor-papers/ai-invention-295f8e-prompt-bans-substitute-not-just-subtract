#!/usr/bin/env python3
"""Shared constants, paths and small utilities for the held-out-family (Gemma) ban-prediction artifact.

Conventions (also stated in README.md and method_out.json):
- BLOCK l = decoder block l (0-based); its output is HF hidden_states[l + 1].
- SPEC positions S = [spec_start, spec_end): from the first token of 'Task:' to the last token of the user message
  (the chat tail '<end_of_turn>\\n<start_of_turn>model\\n' excluded). R = P - 1 (last prompt token).
- CRN slot = (task, template, k); uniforms u_stream(task, template, k) are identical in every coupled arm
  (twin, escape pushes, plan noise, temperature 1.3, ban).
- BAND = middle third of the decoder blocks (gemma-3-4b-it: blocks 11-22 of 34).
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
E15 = INPUTS / "exp15"
E16 = INPUTS / "exp16"
E17 = INPUTS / "exp17"
E18 = INPUTS / "exp18"
DEP1 = INPUTS / "art_j3Rm_lr2nzR6"
BENCH = E11 / "bench"
SUITE = E8 / "suite"
DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "results"
FIG_DIR = ROOT / "figures"
LOG_DIR = ROOT / "logs"
PRED_DIR = ROOT / "predictions"
DIR_DIR = ROOT / "directions"
for _d in (DATA_DIR, RESULTS_DIR, FIG_DIR, LOG_DIR, PRED_DIR):
    _d.mkdir(parents=True, exist_ok=True)
COMMIT_LOG = ROOT / "commitments.log"

# ------------------------------------------------------------------------------------------------ upstream (read-only)
# Inputs produced by other artifacts are read ONLY by src/stage_inputs.py, which copies them into inputs/ (sha256 in
# inputs/SHA256SUMS); every other module reads inputs/. The published repository holds each upstream artifact as a sibling
# folder named by its artifact id; AII_ARTIFACTS_DIR overrides their common parent (default: the parent of this folder).
# An optional, unpublished paths.local.json {short name: path} overrides individual locations (used on the run server,
# whose folders are not named by id).
ARTIFACTS_DIR = Path(os.environ.get("AII_ARTIFACTS_DIR", str(ROOT.parent)))
UPSTREAM_IDS = {
    "exp11": "art_0ndRfWKBWclR",   # frozen 13-task bench (iteration 2)
    "exp8": "art_8_ULPE8jJQc_",    # T1/T2 suite, labeller, frozen prompts (iteration 2)
    "exp7": "art_6zBfl3kDjeiP",    # frozen templates / nouns / padding, prompts_v2 (iteration 2)
    "exp17": "art_pVlCZ272hDV7",   # Qwen3-8B push code, directions, screen labels (iteration 3)
    "exp13": "art_1AYTO1Epb_7t",   # Qwen ban-displacement norms, screen samples (iteration 3)
    "exp15": "art_Q-qh-9HhPoWo",   # Llama port (template for this port) (iteration 3)
    "exp18": "art_ccAbfJVcv0LO",   # known-solutions index, novelty-audit protocol (iteration 3)
    "exp16": "art__5akZ9W9iZM4",   # prefill / opening code (iteration 3)
    "art_j3Rm_lr2nzR6": "art_j3Rm_lr2nzR6",  # declared dependency: source data (iteration 1)
}
PATHS_LOCAL = ROOT / "paths.local.json"


def upstream() -> dict[str, Path]:
    out = {k: ARTIFACTS_DIR / v for k, v in UPSTREAM_IDS.items()}
    if PATHS_LOCAL.exists():
        for k, v in json.loads(PATHS_LOCAL.read_text()).items():
            if k in out:
                out[k] = Path(v)
    return out


# ------------------------------------------------------------------------------------------------ model
MODEL_ID = "google/gemma-3-4b-it"
MODEL_REVISION = "093f9f388b31de276ce2de164bdc2081324b9767"
FALLBACK_MODEL_ID = "Qwen/Qwen2.5-Coder-7B-Instruct"
QWEN_ID = "Qwen/Qwen3-8B"
QWEN_REVISION = "b968826d9c46dd6066d109eabc6255188de91218"
QWEN_LAYERS = 36
QWEN_BAND = list(range(12, 24))   # blocks whose ban displacement norms exp13/exp17 recorded
N_LAYERS = 34
D_MODEL = 2560
BAND = list(range(11, 23))        # middle third of 34 blocks
CAPTURE_BLOCKS = list(range(11, 34))  # realised displacement logged from BAND start to the last block
BOS_ID = 2
EOS_ID = 1
EOT_ID = 106                      # <end_of_turn>
STOP_IDS = (EOS_ID, EOT_ID)
PAD_ID = 0
CHAT_HEAD = "<bos><start_of_turn>user\n"
CHAT_TAIL = "<end_of_turn>\n<start_of_turn>model\n"
MAX_NEW_BENCH = 1024
MAX_NEW_PATH = 1536
MAX_NEW_ASSOC = 160
CAP_FLOOR = 640
STOP_CHECK_EVERY = 16
DECODING = "T1.0_topp1.0_topk-off_inverse-CDF-CRN"
PRECISION = "bf16 (sdpa attention); logits fp32, CDF float64"

# ------------------------------------------------------------------------------------------------ tasks
PATH_TASKS = ("T1", "T2")
BENCH12 = ("T03", "T04", "T06", "T05", "T10", "R1", "T08", "R3", "T13", "R6", "T14", "T11")
BENCH_TASKS = BENCH12 + ("R2",)
ALL_TASKS = PATH_TASKS + BENCH_TASKS      # 15 tasks
QWEN_RATIO_TASKS = PATH_TASKS + BENCH12   # the 14 tasks with Qwen ban-displacement norms (no R2)
EXP8_TASK = {"T1": "t1", "T2": "t2"}
QWEN_DEFAULT = {"T1": "bfs", "T2": "dijkstra", "T03": "full_sort", "T04": "naive", "T06": "hash_set",
                "T05": "hash_map", "T10": "union_find", "R1": "greedy_end", "T08": "iteration", "R3": "kahn",
                "T13": "sort_sweep", "R6": "binary_search", "T14": "sort_by_count", "T11": "quadratic_dp",
                "R2": "dfs_parent"}
TEMPLATES: dict[str, tuple[str, str]] = {  # (ban, neutral twin) -- protocol W1-W5, verbatim
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

# ------------------------------------------------------------------------------------------------ design
ESCAPE_SEEDS = tuple(range(9001, 9009))   # 8 fixed isotropic directions
ALPHAS = (1.0, 2.0)
T_HOT = 1.3
N_TWIN_PER_T = 10                          # twin slots 0-9 per template (N = 50 per task)
N_STAGE1_PER_T = 2                         # escape stage 1: slots 0-1 per template (N = 10 per direction-alpha)
STAGE2_SLOTS = (2, 3, 4, 5)                # confirmation top-up (N = 20 more)
N_PN_PER_T = 10
N_T13_PER_T = 10
N_BAN_PER_T = 20                           # ban slots 0-19 per template (N = 100 per task, primary)
ESCAPE_EXCESS = 0.20
ESCAPE_PASS_FRAC = 0.80
BINOM_ALPHA = 0.05
P0_FLOOR = 0.01
COMPLY_THRESH = 0.5
SMOOTH = {"f": 0.93, "uniform_S": 0.05, "other": 0.02}
BUDGET_MSG = "AI Inventor per-run OpenRouter budget"
OPENROUTER_CAP_USD = 1.00


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
            return max(1, math.floor(q / p))
    except (FileNotFoundError, ValueError):
        pass
    try:
        parts = Path("/sys/fs/cgroup/cpu.max").read_text().split()
        if parts[0] != "max":
            return max(1, math.floor(int(parts[0]) / int(parts[1])))
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
    """Deterministic 63-bit seed from arbitrary parts (sha256 of their '|'-joined repr) -- exp8 convention."""
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


def model_path(model_id: str = MODEL_ID, revision: str | None = MODEL_REVISION) -> str:
    cache = os.environ.get("HF_HUB_CACHE")
    if cache:
        snaps = Path(cache) / ("models--" + model_id.replace("/", "--")) / "snapshots"
        if revision and (snaps / revision).exists():
            return str(snaps / revision)
        if snaps.exists():
            cands = sorted(snaps.iterdir())
            if cands and revision is None:
                return str(cands[-1])
    return model_id


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
