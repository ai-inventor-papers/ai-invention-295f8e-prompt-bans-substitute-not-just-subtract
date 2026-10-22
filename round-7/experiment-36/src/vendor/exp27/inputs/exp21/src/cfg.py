#!/usr/bin/env python3
"""Shared constants, paths and small utilities for the iteration-3 internal-locus artifact.

Conventions (also stated in README.md and method_out.json):
- BLOCK l = decoder block l (0-based); its output is HF hidden_states[l + 1]. Saved 'block l' states are block-l
  outputs. exp8 c5.json and exp12 use 'layer l = hidden_states[l]' (= output of block l - 1); indices are mapped
  explicitly wherever those numbers are compared.
- SPEC positions S = [p1, spec_end): from the first token of 'Task:' to the last token of the user message
  (the chat tail '<|im_end|>\\n<|im_start|>assistant\\n<think>\\n\\n</think>\\n\\n' excluded). R = P - 1.
- Generated position k (1-based) = absolute position P + k - 1, where generated token k is the INPUT; the state
  there predicts token k + 1.
- CRN slot = (task, template, k); uniforms u_stream(task, template, k) are identical in every arm.
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
E12 = INPUTS / "exp12"
E9 = INPUTS / "exp9"
E7 = INPUTS / "exp7"
BENCH = E11 / "bench"
SUITE = E8 / "suite"
PROMPTS_DIR = ROOT / "prompts"
DATA_DIR = ROOT / "data"
TOKEN_DIR = DATA_DIR / "token_ids"
RESULTS_DIR = ROOT / "results"
FIG_DIR = ROOT / "figures"
LOG_DIR = ROOT / "logs"
DIR_DIR = ROOT / "directions"
STATES_DIR = ROOT / "states"
PRED_DIR = ROOT / "predictions"
for _d in (PROMPTS_DIR, DATA_DIR, TOKEN_DIR, RESULTS_DIR, FIG_DIR, LOG_DIR, DIR_DIR, STATES_DIR, PRED_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------------------------------------------ model
MODEL_ID = "Qwen/Qwen3-8B"
MODEL_REVISION = "b968826d9c46dd6066d109eabc6255188de91218"
BASE_MODEL_ID = "Qwen/Qwen3-8B-Base"
SAE_REPO = "Qwen/SAE-Res-Qwen3-8B-Base-W64K-L0_50"
N_LAYERS = 36
D_MODEL = 4096
N_HEADS = 32
HEAD_DIM = 128
IM_END = 151645
ENDOFTEXT = 151643
MAX_NEW_TOKENS = 1024
TEMPERATURE = 1.0
DECODING = "T1.0_topp1.0_topk-off_max1024_thinkoff"
TEMPLATE_TAIL = "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"
# Quantisation actually used (deviation F2; the 16 GB RTX 2000 Ada cannot hold the 16.4 GB of bf16 weights):
QUANT = "fp8_e4m3_w8a8_dynamic(per-output-channel weight scales, per-token activation scales; lm_head/embeddings/norms bf16)"


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


# ------------------------------------------------------------------------------------------------ tasks
PATH_TASKS = ("T1", "T2")
BENCH_TASKS = ("T03", "T04", "T06", "T05", "T10", "R1", "T08", "R3", "T13", "R6", "T14", "T11")
ALL_TASKS = PATH_TASKS + BENCH_TASKS  # 14 tasks: the direction is built from all of them
SAMPLED_TASKS = ("T2", "T1", "T03", "T04", "T06", "T05")  # sampling order (fallback F3: whole tasks in this order)
DEFAULT = {"T1": "bfs", "T2": "dijkstra", "T03": "full_sort", "T04": "naive", "T06": "hash_set", "T05": "hash_map",
           "T10": "union_find", "R1": "greedy_end", "T08": "iteration", "R3": "kahn", "T13": "sort_sweep",
           "R6": "binary_search", "T14": "sort_by_count", "T11": "quadratic_dp"}
EXP8_TASK = {"T1": "t1", "T2": "t2"}
TEMPLATES: dict[str, tuple[str, str]] = {  # (ban, neutral) -- protocol v2 W1-W5, verbatim
    "W1": ("Do not use {X} for this task.", "Do not use {N} for this task."),
    "W2": ("Your solution must not rely on {X}.", "Your solution must not rely on {N}."),
    "W3": ("Avoid {X} entirely.", "Avoid {N} entirely."),
    "W4": ("{X} is not allowed here.", "{N} is not allowed here."),
    "W5": ("Write a correct solution that does not use {X}.", "Write a correct solution that does not use {N}."),
}
TEMPLATE_IDS = list(TEMPLATES)
PAD_FILLER = " ."  # exp7 frozen padding rule: neutral segment + d x ' .' so the twin has the ban's token length

# ------------------------------------------------------------------------------------------------ design
V_BLOCKS = list(range(12, 24))          # blocks whose outputs are edited (exp8 band B2)
SAVE_BLOCKS = list(range(8, 29))        # blocks saved for diagnostics / decoders
ALPHAS_ADD = (1.0, 2.0, 0.5)
ALPHAS_RAND = (1.0, 2.0)
RAND_SEEDS = (9001, 9002, 9003)
HEAD_TARGET = [(21, 17), (26, 21), (26, 25)]
HEAD_RAND_SEEDS = (7101, 7102, 7103)
N_PER_TEMPLATE_FULL = 20                # k 0-19 x 5 templates = 100
N_PER_TEMPLATE_HALF = 10                # k 0-9 x 5 templates = 50
BATCH = 20                              # every sampled batch has exactly 20 rows (two 10-slot blocks or one 20-slot)
GEN_POSITIONS = [1, 2, 3, 4, 5, 6, 7, 8, 16]
JUDGE_CAP_USD = 0.40  # raised from the plan's 0.20 (logged deviation): T2 ban programs often leave runtime+AST unresolved
BUDGET_MSG = "AI Inventor per-run OpenRouter budget"


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
        return len(os.sched_getaffinity(0))
    except (AttributeError, OSError):
        return os.cpu_count() or 1


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def stable_seed(*parts: Any) -> int:
    """Deterministic 63-bit seed from arbitrary parts (sha256 of their '|'-joined repr) -- exp8 convention."""
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
