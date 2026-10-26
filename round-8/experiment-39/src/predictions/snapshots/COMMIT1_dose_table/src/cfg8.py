#!/usr/bin/env python3
"""Iteration-8 claim K1/HR constants: temperature applied only at located decision tokens (bf16 Qwen3-8B, thinking
off; bf16 Gemma-3-4b-it on the grid task).

Conventions (inherited from iterations 5-7, see README.md):
- A UNIT is (model, task, 5 prompt templates W1-W5, 10 CRN slots per template) = 50 slots s = 0..49 with
  template W_{s // 10 + 1} and source slot j = s % 10. Each slot owns one uniform stream (PCG64 of stable_seed(ukey))
  that every arm reuses, one uniform per generated token (the coupling that makes per-slot flips exact).
  Slot keys are the source artifacts' own keys, so Stage 0 twins re-generate exactly their T = 1 programs:
    T10/T1/T2/T03 (exp34/exp35 iteration-6 keys)      ukey = (unit, W, j)
    B3/A3/B6 (exp35 same-seed sweep streams)          ukey = ('iter7T', unit, W, 20 + j)
    G (Gemma grid, exp38 G3 sweep streams)            ukey = ('iter7GG3', 'T1', W, j)
- Sampler (Qwen, engine5 numerics): float64 softmax(logits / T) -> truncation masks -> inverse CDF over the FULL
  vocabulary in token-id order (searchsorted of the row's uniform). Gemma uses exp38's numerics (float32 softmax,
  float64 cumsum). Truncation never renormalises before the inverse CDF (the CDF is divided by the kept mass).
- A decision node n = (opening P_n, index i_n = |P_n|); the DOSE is (T_d, top-20) applied at generated index i_n
  only, T = 1 everywhere else.
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

import numpy as np
from loguru import logger

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
INPUTS = ROOT / "inputs"
DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "results"
FIG_DIR = ROOT / "figures"
LOG_DIR = ROOT / "logs"
PRED_DIR = ROOT / "predictions"
CACHE_DIR = ROOT / "cache"
PROMPTS_DIR = ROOT / "prompts"
for _d in (DATA_DIR, RESULTS_DIR, FIG_DIR, LOG_DIR, PRED_DIR, CACHE_DIR, PROMPTS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

COMMITS = ROOT / "commitments.log"
SAMPLES = DATA_DIR / "samples.jsonl"            # every generated program (all stages/arms), one row per program
LABELS = DATA_DIR / "labels.jsonl"              # one label row per program (keyed by sid)
CONTS = DATA_DIR / "continuations.jsonl"        # locator / token-map / HR continuations
CONT_LABELS = DATA_DIR / "continuation_labels.jsonl"
STEPLOG = DATA_DIR / "steplog.jsonl"            # per-row decision logits, entropies, decision positions
TIMING = RESULTS_DIR / "timing.jsonl"

I6_SRC = INPUTS / "iter6_exp30" / "src"
E35 = INPUTS / "exp35"
E34 = INPUTS / "exp34"
E38 = INPUTS / "exp38"

_RUNS = ROOT.parents[4] if len(ROOT.parents) > 4 else ROOT
DEP_DIR = Path(os.environ.get("ART_J3RM_DIR") or (
    _RUNS / "run_4VFKidE1bxPG" / "." / "round-1" / "." / "gen_art_dataset_1"))

# ------------------------------------------------------------------------------------------------ models
QWEN_ID = "Qwen/Qwen3-8B"
QWEN_REV = "b968826d9c46dd6066d109eabc6255188de91218"
GEMMA_ID = "google/gemma-3-4b-it"
GEMMA_REV = "093f9f388b31de276ce2de164bdc2081324b9767"
QWEN_IM_END = 151645
QWEN_EOT = 151643
GEMMA_EOS = 1
GEMMA_EOT = 106
U_LEN = 1536
TEMPLATES = ("W1", "W2", "W3", "W4", "W5")
N_SLOTS = 50
PRECISION = "bf16 weights/activations; fp32 logits; float64 CDF"

# ------------------------------------------------------------------------------------------------ units
# role: located (collapsed | mixed), boundary
UNITS: dict[str, dict[str, Any]] = {
    "T10": {"model": "qwen", "role": "collapsed", "task": "connected components", "default": "union_find",
            "max_new": 384, "fence": "bench", "batch": 40, "label": "C",
            "catalogue": ["union_find", "bfs", "dfs"]},
    "T1": {"model": "qwen", "role": "collapsed", "task": "grid path", "default": "bfs",
           "max_new": 640, "fence": "path", "batch": 32, "label": "C",
           "catalogue": ["bfs", "dfs", "astar", "dijkstra_unit", "bibfs", "idastar", "greedy_best_first", "jps",
                         "iddfs", "beam"]},
    "B3": {"model": "qwen", "role": "mixed", "task": "minimum spanning tree weight", "default": "kruskal",
           "a_min": "prim_heap", "max_new": 768, "fence": "bench", "batch": 32, "label": "B",
           "catalogue": ["kruskal", "prim_heap", "prim_array", "boruvka"]},
    "A3": {"model": "qwen", "role": "mixed", "task": "trapped rain water", "default": "prefix_suffix_max",
           "a_min": "two_pointers", "max_new": 640, "fence": "bench", "batch": 40, "label": "A",
           "catalogue": ["two_pointers", "prefix_suffix_max", "monotonic_stack", "peak_split"]},
    "B6": {"model": "qwen", "role": "mixed", "task": "valid anagram", "default": "sort_compare",
           "a_min": "fixed_count_array", "max_new": 384, "fence": "bench", "batch": 40, "label": "B",
           "catalogue": ["sort_compare", "hash_count", "fixed_count_array", "alphabet_count_scan"]},
    "T2": {"model": "qwen", "role": "boundary", "task": "shortest path", "default": "dijkstra",
           "max_new": 512, "fence": "path", "batch": 40, "label": "C",
           "catalogue": ["dijkstra", "bf_spfa", "bidirectional", "a_star", "dial", "floyd_warshall"]},
    "T03": {"model": "qwen", "role": "boundary", "task": "k-th smallest", "default": "full_sort",
            "max_new": 384, "fence": "bench", "batch": 40, "label": "C",
            "catalogue": ["full_sort", "quickselect", "size_k_heap", "heapify_pop", "counting_sort"]},
    "G": {"model": "gemma", "role": "mixed", "task": "grid path (Gemma-3-4b-it)", "default": "dfs", "a_min": "bfs",
          "max_new": 1024, "fence": "gemma", "batch": 25, "label": "C", "label_task": "T1",
          "catalogue": ["bfs", "dfs", "astar", "dijkstra_unit", "bibfs", "idastar", "greedy_best_first", "jps",
                        "iddfs", "beam"]},
}
LOCATED = ("T10", "T1", "B3", "A3", "B6", "G")
BOUNDARY = ("T2", "T03")
QWEN_UNITS = ("T10", "T1", "B3", "A3", "B6", "T2", "T03")


def label_task(unit: str) -> str:
    return UNITS[unit].get("label_task", unit)


def slot_template(s: int) -> str:
    return TEMPLATES[s // 10]


def slot_ukey(unit: str, s: int) -> tuple:
    w, j = slot_template(s), s % 10
    if unit in ("T10", "T1", "T2", "T03"):
        return (unit, w, j)
    if unit in ("B3", "A3", "B6"):
        return ("iter7T", unit, w, 20 + j)
    if unit == "G":
        return ("iter7GG3", "T1", w, j)
    raise KeyError(unit)


# ------------------------------------------------------------------------------------------------ design
DOSE_GRID = [1.0 + 0.25 * i for i in range(13)] + [float(x) for x in range(5, 31)] + [40.0, 60.0, 100.0]
TOPK_DOSE = 20
GLOBAL_ARMS = {"A1": 1.3, "A2": 1.6, "A3g": 2.0}       # with top-p 0.95 at every position
TOP_P_GLOBAL = 0.95
MINP = {"T": 3.0, "min_p": 0.1}
EDT = {"T_hi": 2.0, "q": 90}
ADAPT = {"T_hi": 2.0}
ENTROPY_STEPS = 96                                    # T = 1 entropy logged for generated steps 1..96
ENTROPY_WINDOW = 64                                   # entropy-max / random-window positions drawn in 1..64
WINDOW_BOUNDARY = 16
SEED_RANDOM_WINDOW = 8_800_000
SEED_CLASS_UNIFORM = 9_900_000
SEED_LOCATOR = 7_700_000
SEED_HR = 6_600_000
K_MAP = 10                                            # continuations per top-20 token in the token maps
K_HR = 5
HR_RANKS = 64
COMMITTAL = 0.8
PSEUDO = 0.5
N_BOOT = 2000
BOOT_SEED = 20261023
NOISE_DRAWS = 10_000
BUDGET_MSG = "AI Inventor per-run OpenRouter budget"
JUDGE_CAP_USD = 1.5
GPU_CAP_H = 3.3

THRESH = {
    "mae_max": 0.10, "mae_units_frac": 0.80, "hill_min": 1.8, "hill_comp_max": 1.15, "pass_cost_max": 0.05,
    "reversion_max": 0.10, "entropy_below_q90_frac": 0.90, "boundary_move_max": 0.10, "boundary_pass_min": 0.5,
    "g_pass_cost_tol": 0.10, "disconfirm_share": 0.10, "disconfirm_cost": 0.10, "disconfirm_reversion": 0.30,
    "engine_agree": 0.95, "hill_depth": 25, "mixed_hill_units": 4, "d1_target_tol": 0.10, "attempted_d1": 0.20,
    "attempted_d2": 0.40, "minority_d1": 0.5, "t1_valid_k": 5, "t1_valid_pass": 0.7, "adjudicate_other": 0.20,
}


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
    """sha256 of the '|'-joined str() of the parts, mod 2^63 (exp8/exp17/exp29/exp35 convention)."""
    return int(hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest(), 16) % (2 ** 63)


def u_stream(*key: Any, n: int = U_LEN) -> np.ndarray:
    return np.random.Generator(np.random.PCG64(stable_seed(*key))).random(n)


def model_path(model_id: str, revision: str) -> str:
    cache = os.environ.get("HF_HUB_CACHE")
    if cache:
        snap = Path(cache) / ("models--" + model_id.replace("/", "--")) / "snapshots" / revision
        if snap.exists():
            return str(snap)
    from huggingface_hub import snapshot_download
    return snapshot_download(model_id, revision=revision)


def _json_default(o: Any) -> Any:
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


def dumps(obj: Any) -> str:
    return json.dumps(obj, default=_json_default)


def read_json(p: Path) -> Any:
    return json.loads(Path(p).read_text())


def write_json(p: Path, obj: Any) -> None:
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1, default=_json_default))
    tmp.replace(p)


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


def log_deviation(dev_id: str, text: str, severity: str = "minor") -> None:
    p = RESULTS_DIR / "deviations.json"
    cur = read_json(p) if p.exists() else []
    if any(d["id"] == dev_id for d in cur):
        return
    cur.append({"id": dev_id, "severity": severity, "text": text, "utc": utc_now()})
    write_json(p, cur)
    logger.warning(f"DEVIATION {dev_id}: {text[:200]}")


def log_timing(tag: str, **kw: Any) -> None:
    append_jsonl(TIMING, [{"tag": tag, "utc": utc_now(), **kw}])
