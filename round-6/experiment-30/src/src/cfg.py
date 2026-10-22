#!/usr/bin/env python3
"""Shared constants, paths and utilities for 'Where noise changes the algorithm, in bf16' (iteration 6, Step 2).

Conventions (stated again in README.md and method_out.json):
- Precision W16A16: bf16 weights and bf16 activations (HF transformers, sdpa), edits computed in fp32 and cast to bf16.
- BLOCK l = decoder block l (0-based); its output is HF hidden_states[l + 1] (exp17/exp20 convention).
- Prompt layout (exp8/exp17): '<|im_start|>user\\n' + condition sentence + '\\n\\n' + task specification + chat tail.
  COND = condition-sentence tokens (exp20 D3: a token that merges the final '.' with '\\n\\n' belongs to COND),
  S = [p1, spec_end) task-specification tokens, R = P - 1 (last chat-tail token).
- Generated input position k (1-based) = absolute position P + k - 1 (generated token k is the INPUT there).
- CRN slot = (task, template, k): token uniforms u_stream(task, template, k) (exp17 key) and ONE random direction
  u(t, w, k) = normalise(PCG64(stable_seed('ITER6_S2', t, w, k)).standard_normal(4096)) shared by EVERY arm.
- Ban-free unit: n[l, p] = ||h_twin[l, p]|| * r_Q(l) (r_Q: exp23 frozen at blocks 12-23, bf16 recomputation by
  exp23's recipe at blocks 0-11 and 24-35).
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
E7 = INPUTS / "exp7"
E8 = INPUTS / "exp8"
E9 = INPUTS / "exp9"
E11 = INPUTS / "exp11"
E13 = INPUTS / "exp13"
E17 = INPUTS / "exp17"
E18 = INPUTS / "exp18"
E19 = INPUTS / "exp19"
E20 = INPUTS / "exp20"
E21 = INPUTS / "exp21"
E22 = INPUTS / "exp22"
E23 = INPUTS / "exp23"
E24 = INPUTS / "exp24"
E25 = INPUTS / "exp25"
E27 = INPUTS / "exp27"
BENCH = E11 / "bench"
SUITE = E8 / "suite"
DATA_DIR = ROOT / "data"
ROWLOG_DIR = DATA_DIR / "row_logs"
RESULTS_DIR = ROOT / "results"
FIG_DIR = ROOT / "figures"
LOG_DIR = ROOT / "logs"
UNITS_DIR = ROOT / "units"
DIR_DIR = ROOT / "directions"
PRED_DIR = ROOT / "predictions"
AUDIT_DIR = ROOT / "audit"
CACHE_DIR = ROOT / "cache"
for _d in (DATA_DIR, ROWLOG_DIR, RESULTS_DIR, FIG_DIR, LOG_DIR, UNITS_DIR, DIR_DIR, PRED_DIR, AUDIT_DIR, CACHE_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# Declared dataset dependency art_j3Rm_lr2nzR6 (read in place, never written, never copied: 96 MB).
DEP_DATASET = Path(os.environ.get("ART_J3RM_DIR", str(ROOT.parent / "art_j3Rm_lr2nzR6")))

# ------------------------------------------------------------------------------------------------ model
MODEL_ID = "Qwen/Qwen3-8B"
MODEL_REVISION = "b968826d9c46dd6066d109eabc6255188de91218"
N_LAYERS = 36
D_MODEL = 4096
IM_END = 151645
ENDOFTEXT = 151643
TEMPERATURE = 1.0
PRECISION = "W16A16"
PRECISION_DESC = "bf16 weights and activations (HF transformers 4.57.6, attn sdpa); edits in fp32 cast to bf16"
TEMPLATE_TAIL = "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"
DIRECTION_NS = "ITER6_S2"


def model_path(model_id: str = MODEL_ID, revision: str | None = MODEL_REVISION) -> str:
    cache = os.environ.get("HF_HUB_CACHE")
    if cache:
        snaps = Path(cache) / ("models--" + model_id.replace("/", "--")) / "snapshots"
        if revision and (snaps / revision).exists():
            return str(snaps / revision)
    return model_id


# ------------------------------------------------------------------------------------------------ tasks
TASKS = ("T03", "T10", "T2", "T1")           # sampled here
UNIT_TASKS = ("T03", "T05", "T06", "T10", "T1", "T2")  # exp20's ban prompts (forward passes only) for r_Q
PATH_TASKS = ("T1", "T2")
BENCH_TASKS = ("T03", "T10")
DEFAULT = {"T1": "bfs", "T2": "dijkstra", "T03": "full_sort", "T05": "hash_map", "T06": "hash_set",
           "T10": "union_find"}
RUNNER_UP = {"T03": "quickselect", "T10": "dfs", "T2": "bf_spfa", "T1": "dfs"}  # exp24 base r_t
EXP8_TASK = {"T1": "t1", "T2": "t2"}
TEMPLATE_IDS = ["W1", "W2", "W3", "W4", "W5"]
MAX_NEW = {"T03": 1024, "T10": 1024, "T2": 1536, "T1": 1536}
BENCH_DIRS = {"T03": "T03_kth_smallest", "T10": "T10_connected_components"}

# ------------------------------------------------------------------------------------------------ sites
PLAN_BLOCKS = list(range(12, 24))
LOW_BLOCKS = list(range(0, 12))
HIGH_BLOCKS = list(range(24, 36))
ALL_BLOCKS = list(range(N_LAYERS))
SITES = ("S0", "S4", "S5", "S1", "S2", "S3", "S1E")
SITE_BLOCKS = {"S0": PLAN_BLOCKS, "S1": PLAN_BLOCKS, "S2": PLAN_BLOCKS, "S3": PLAN_BLOCKS, "S4": LOW_BLOCKS,
               "S5": HIGH_BLOCKS, "S1E": PLAN_BLOCKS, "TOP5": PLAN_BLOCKS, "TOP3": PLAN_BLOCKS,
               "ENG": PLAN_BLOCKS}
SITE_POS = {"S0": "S", "S1": "R", "S2": "COND", "S3": "GEN1-32", "S4": "S", "S5": "S", "S1E": "R", "TOP5": "S",
            "TOP3": "S", "ENG": "S"}
PREFILL_SITES = ("S0", "S4", "S5", "S1", "S2", "S1E")
TS_SITES = ("S0", "S4")
COMPARATORS = ("S1", "S2", "S5")
S3_STEPS = 32
ALPHAS = (1.0, 2.0, 4.0)
N30_K = list(range(6))   # slots 0-5 x 5 templates = N 30
N50_K = list(range(10))  # slots 0-9 x 5 templates = N 50
TOPUP_K = [6, 7, 8, 9]
SMOKE_K0 = 100           # smoke / test slots k >= 100 are never analysed
FILL_K0 = 10             # filler twin rows (TWIN_X) use k >= 10 (descriptive only)

# fixed batch shape per task (memory probe on the NVIDIA L4, frozen before commit #1; see results/batch_probe.json)
BATCH = {"T03": 16, "T10": 16, "T2": 12, "T1": 12}

JUDGE_CAP_LABEL_USD = 0.30
AUDIT_CAP_USD = 0.15
ARTIFACT_CAP_USD = 0.50
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


def log_deviation(did: str, what: str, why: str, consequence: str) -> None:
    """Append one deviation to results/deviations.json (idempotent by id)."""
    p = RESULTS_DIR / "deviations.json"
    cur = read_json(p) if p.exists() else []
    cur = [d for d in cur if d.get("id") != did]
    cur.append({"id": did, "what": what, "why": why, "consequence": consequence, "utc": utc_now()})
    write_json(p, cur)
