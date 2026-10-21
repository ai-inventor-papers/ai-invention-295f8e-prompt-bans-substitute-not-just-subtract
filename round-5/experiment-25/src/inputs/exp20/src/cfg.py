#!/usr/bin/env python3
"""Shared constants, paths and utilities for 'Where noise must go to change the idea' (iteration 4).

Conventions (stated again in README.md and method_out.json):
- BLOCK l = decoder block l (0-based); its output is HF hidden_states[l + 1] (exp17 convention).
- Prompt layout (exp8/exp17): '<|im_start|>user\\n' + condition sentence + '\\n\\n' + task specification + chat tail.
  COND = [p0, p1) = the condition sentence (padding included; the chat header excluded; when the tokenizer merges the
  final '.' with the '\\n\\n' separator, that merged token is part of COND and is reported in results/positions.json).
  S = [p1, spec_end) from the first 'Task:' token to the last user-message token. R = P - 1 (last chat-tail token).
- Generated input position k (1-based) = absolute position P + k - 1 (generated token k is the INPUT there).
- CRN slot = (task, template, k): token uniforms u_stream(task, template, k) (exp17 key) and the random direction
  u(t, w, k) = normalise(PCG64(stable_seed('PN4', t, w, k)).standard_normal(4096)) are shared by EVERY arm.
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
E17 = INPUTS / "exp17"
E13 = INPUTS / "exp13"
E18 = INPUTS / "exp18"
E11 = INPUTS / "exp11"
E8 = INPUTS / "exp8"
E9 = INPUTS / "exp9"
E7 = INPUTS / "exp7"
BENCH = E11 / "bench"
SUITE = E8 / "suite"
DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "results"
FIG_DIR = ROOT / "figures"
LOG_DIR = ROOT / "logs"
UNITS_DIR = ROOT / "units"
DIR_DIR = ROOT / "directions"
PRED_DIR = ROOT / "predictions"
AUDIT_DIR = ROOT / "audit"
for _d in (DATA_DIR, RESULTS_DIR, FIG_DIR, LOG_DIR, UNITS_DIR, DIR_DIR, PRED_DIR, AUDIT_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# Declared dataset dependency art_j3Rm_lr2nzR6 (read in place; never written): set ART_J3RM_DIR to the folder holding
# its full_data_out.json (default: a sibling folder named art_j3Rm_lr2nzR6).
DEP_DATASET = Path(os.environ.get("ART_J3RM_DIR", str(ROOT.parent / "art_j3Rm_lr2nzR6")))

# ------------------------------------------------------------------------------------------------ model
MODEL_ID = "Qwen/Qwen3-8B"
MODEL_REVISION = "b968826d9c46dd6066d109eabc6255188de91218"
N_LAYERS = 36
D_MODEL = 4096
IM_END = 151645
ENDOFTEXT = 151643
MAX_NEW_TOKENS = 1024
TEMPERATURE = 1.0
DECODING = "T1.0_topp1.0_topk-off_max1024_thinkoff_fencestop"
TEMPLATE_TAIL = "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"
QUANT = "fp8_e4m3_w8a8_dynamic(per-output-channel weight scales, per-token activation scales; lm_head/embeddings/norms bf16)"
BATCH = 20  # fixed batch shape (exp17's U1b-verified shape on this GPU); never changes within or across tasks


def model_path(model_id: str = MODEL_ID, revision: str | None = MODEL_REVISION) -> str:
    cache = os.environ.get("HF_HUB_CACHE")
    if cache:
        snaps = Path(cache) / ("models--" + model_id.replace("/", "--")) / "snapshots"
        if revision and (snaps / revision).exists():
            return str(snaps / revision)
    return model_id


# ------------------------------------------------------------------------------------------------ tasks
TASKS = ("T03", "T05", "T06", "T10", "T1", "T2")
PATH_TASKS = ("T1", "T2")
BENCH_TASKS = ("T03", "T05", "T06", "T10")
DEFAULT = {"T1": "bfs", "T2": "dijkstra", "T03": "full_sort", "T05": "hash_map", "T06": "hash_set",
           "T10": "union_find"}
EXP8_TASK = {"T1": "t1", "T2": "t2"}
TEMPLATE_IDS = ["W1", "W2", "W3", "W4", "W5"]
TASK_ORDER_DROP = ("T10", "T06", "T05")  # fallback: whole tasks dropped in this order

# ------------------------------------------------------------------------------------------------ sites
PLAN_BLOCKS = list(range(12, 24))
LOW_BLOCKS = list(range(0, 12))
HIGH_BLOCKS = list(range(24, 36))
SITES = ("S0", "S1", "S2", "S3", "S4", "S5")
SITE_BLOCKS = {"S0": PLAN_BLOCKS, "S1": PLAN_BLOCKS, "S2": PLAN_BLOCKS, "S3": PLAN_BLOCKS, "S4": LOW_BLOCKS,
               "S5": HIGH_BLOCKS, "S1E": PLAN_BLOCKS, "S2E": PLAN_BLOCKS, "TOP5": PLAN_BLOCKS, "ENG": PLAN_BLOCKS}
SITE_POS = {"S0": "S", "S1": "R", "S2": "COND", "S3": "GEN1-32", "S4": "S", "S5": "S", "S1E": "R", "S2E": "COND",
            "TOP5": "S", "ENG": "S"}
S3_STEPS = 32  # generated input positions 1-32
NORM_BLOCKS = list(range(12, N_LAYERS))  # realised displacement at R logged at blocks 12-35
ALPHAS_GRID = (1.0, 2.0, 4.0)
ALPHA_BOUNDARY = 8.0
N_GRID_K = list(range(6))      # k 0-5 x 5 templates = N 30
N50_K = list(range(10))        # k 0-9 x 5 templates = N 50
SMOKE_K0 = 100                 # smoke slots k >= 100 are never analysed
FILL_K0 = 10                   # filler twin rows (TWIN_X) use k >= 10 (descriptive only)

JUDGE_CAP_LABEL_USD = 0.40
AUDIT_CAP_USD = 0.50
CONTROL_CAP_USD = 0.05
ARTIFACT_CAP_USD = 1.00
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


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def stable_seed(*parts: Any) -> int:
    """Deterministic 63-bit seed from arbitrary parts (sha256 of their '|'-joined str) -- exp8/exp17 convention."""
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


def canonical_json(obj: Any) -> str:
    """Sorted keys, floats rounded to 6 decimals, no whitespace (byte-stable)."""
    def rnd(o: Any) -> Any:
        if isinstance(o, float):
            return round(o, 6) if math.isfinite(o) else None
        if isinstance(o, dict):
            return {str(k): rnd(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [rnd(v) for v in o]
        return o
    return json.dumps(rnd(json.loads(json.dumps(obj, default=_json_default))), sort_keys=True,
                      separators=(",", ":"))


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


def rel(p: Path | str) -> str:
    """Path relative to the artifact root (never write absolute server paths into published files)."""
    try:
        return str(Path(p).resolve().relative_to(ROOT))
    except ValueError:
        return str(p)
