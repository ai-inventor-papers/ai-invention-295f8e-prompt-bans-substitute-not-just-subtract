#!/usr/bin/env python3
"""Iteration-7 claim T constants: where temperature can change the chosen algorithm (bf16 Qwen3-8B, thinking off).

Conventions (inherited from iterations 4-6 and stated in README.md):
- BLOCK l = decoder block l (0-based); its output is HF hidden_states[l + 1].
- SPEC positions = [p1, spec_end): from the first 'Task:' token to the last user token (chat tail excluded).
- CRN: every program slot draws one uniform per generated token from u_stream(key) = PCG64(stable_seed(key)); the
  sampler (engine5.decode_rows, iteration 6) maps (fp64 logits / T -> top-k mask -> inverse CDF over the FULL
  vocabulary in TOKEN-ID order) -> token. Keys: ('iter7T', unit, template, slot) for every program of an arm;
  ('iter7fork', unit, base_path_id, prefix_len, j) for prefix-resampling continuations.
- Slots per template: twin 0-19 (N = 100), sweep 20-29 (N = 50 per cell, the same 50 streams in all 8 cells),
  S4(a) 0-1 (N = 10 per direction), S4(b) 0-5 (N = 30 per arm).
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
for _d in (DATA_DIR, RESULTS_DIR, FIG_DIR, LOG_DIR, PRED_DIR, CACHE_DIR):
    _d.mkdir(parents=True, exist_ok=True)

I6 = INPUTS / "iter6_exp30"
I6_SRC = I6 / "src"
E25 = INPUTS / "iter5_exp25"
E26 = INPUTS / "iter5_exp26"
E22 = INPUTS / "iter4_exp22"
COMMITS = ROOT / "commitments.log"
SAMPLES_RAW = DATA_DIR / "samples_raw.jsonl"
LABELS = DATA_DIR / "labels.jsonl"
CONTS = DATA_DIR / "continuations.jsonl"

# the declared dataset dependency art_j3Rm_lr2nzR6 (read-only): ART_J3RM_DIR, else the published sibling folder, else
# the run layout of the original server
_RUNS = ROOT.parents[4]
DEP_DIR = Path(os.environ.get("ART_J3RM_DIR") or next(
    (d for d in (ROOT.parent / "art_j3Rm_lr2nzR6",) if d.exists()),
    _RUNS / "run_4VFKidE1bxPG" / "." / "round-1" / "." / "gen_art_dataset_1"))

# ------------------------------------------------------------------------------------------------ model
MODEL_ID = "Qwen/Qwen3-8B"
MODEL_REVISION = "b968826d9c46dd6066d109eabc6255188de91218"
N_LAYERS = 36
D_MODEL = 4096
IM_END = 151645
ENDOFTEXT = 151643
TEMPLATE_TAIL = "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"
PRECISION = "bf16"
U_LEN = 1536

# ------------------------------------------------------------------------------------------------ units
TEMPLATES = ("W1", "W2", "W3", "W4", "W5")
BAN_TEMPLATES: dict[str, tuple[str, str]] = {  # (ban, neutral) protocol v2 W1-W5, verbatim
    "W1": ("Do not use {X} for this task.", "Do not use {N} for this task."),
    "W2": ("Your solution must not rely on {X}.", "Your solution must not rely on {N}."),
    "W3": ("Avoid {X} entirely.", "Avoid {N} entirely."),
    "W4": ("{X} is not allowed here.", "{N} is not allowed here."),
    "W5": ("Write a correct solution that does not use {X}.", "Write a correct solution that does not use {N}."),
}
PAD_FILLER = " ."
MIXED = ("B3", "A3", "B6")
COLLAPSED = ("T1", "T2", "T10", "T03")
UNITS: dict[str, dict[str, Any]] = {
    "B3": {"name": "minimum spanning tree weight", "default": "kruskal",
           "catalogue": ["kruskal", "prim_heap", "prim_array", "boruvka"], "a_min_plan": "prim_heap",
           "display": {"kruskal": "Kruskal's algorithm", "prim_heap": "Prim's algorithm with a heap",
                       "prim_array": "Prim's algorithm with an array scan", "boruvka": "Boruvka's algorithm"},
           "record_share": 0.34, "max_new": 768, "batch": 32, "src": "exp26"},
    "A3": {"name": "trapped rain water", "default": "prefix_suffix_max",
           "catalogue": ["two_pointers", "prefix_suffix_max", "monotonic_stack", "peak_split"],
           "a_min_plan": "two_pointers",
           "display": {"two_pointers": "two pointers", "prefix_suffix_max": "prefix and suffix maximum arrays",
                       "monotonic_stack": "a monotonic stack", "peak_split": "splitting at the highest bar"},
           "record_share": 0.36, "max_new": 640, "batch": 40, "src": "exp25"},
    "B6": {"name": "valid anagram", "default": "sort_compare",
           "catalogue": ["sort_compare", "hash_count", "fixed_count_array"], "a_min_plan": "hash_count",
           "display": {"sort_compare": "sorting both strings", "hash_count": "a hash map of letter counts",
                       "fixed_count_array": "a fixed 26-slot count array"},
           "record_share": 0.24, "max_new": 384, "batch": 50, "src": "exp26"},
}
COLLAPSED_INFO = {"T1": {"default": "bfs", "y": "dfs", "max_new": 640, "fence": "path"},
                  "T2": {"default": "dijkstra", "y": "bf_spfa", "max_new": 512, "fence": "path"},
                  "T10": {"default": "union_find", "y": "bfs", "max_new": 384, "fence": "bench"},
                  "T03": {"default": "full_sort", "y": "quickselect", "max_new": 384, "fence": "bench"}}

# ------------------------------------------------------------------------------------------------ design
TEMPS = (0.3, 0.7, 1.0, 1.3)
SAMPLERS = {"p1": 0, "k10": 10}          # sampler id -> top_k (0 = off); top-p is 1 everywhere
TWIN_SLOTS = tuple(range(0, 20))
SWEEP_SLOTS = tuple(range(20, 30))
S4A_SLOTS = (0, 1)
S4B_SLOTS = tuple(range(0, 6))
SCAN_STEP = 4
SCAN_MAX = 96
SCAN_HORIZON = 160
N_SCAN = 8
N_CONFIRM = 20
CONT_BATCH = 64
V_BLOCKS = list(range(12, 24))
DIRECTIONS = tuple(range(9101, 9109))
ALPHA_PUSH = 2.0
BOOT_SEED = 20261022
N_BOOT = 1000
BUDGET_MSG = "AI Inventor per-run OpenRouter budget"
JUDGE_CAP_USD = 0.50

# committed thresholds (Part F); frozen in commit #0
THRESH = {
    "test1_H_bits_pass": 0.3, "test1_H_bits_disconfirm": 0.5, "test1_units_needed": 2,
    "test2_drop_min": 0.15, "test2_mae_max": 0.10, "test2_13_tol": 0.10, "test2_units_needed": 2,
    "test2_mae_disconfirm": 0.2, "test3_margin_nats": 4.0, "fork_pchange": 0.9, "fork_share_jump_bp": 0.4,
    "confirm_jump": 0.5, "confirm_fisher_p": 0.01, "control_move_max": 0.2, "calib_fisher_p": 0.01,
    "oc_agree": 0.95, "oc_cover": 0.85, "onetoken_frac": 2 / 3, "secondary_bonferroni": 0.05 / 7,
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
    """Deterministic 63-bit seed from arbitrary parts (sha256 of their '|'-joined repr) -- exp8/exp17 convention."""
    return int(hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest(), 16) % (2 ** 63)


def u_stream(*key: Any, n: int = U_LEN) -> np.ndarray:
    return np.random.Generator(np.random.PCG64(stable_seed(*key))).random(n)


def model_path(model_id: str = MODEL_ID, revision: str | None = MODEL_REVISION) -> str:
    cache = os.environ.get("HF_HUB_CACHE")
    if cache:
        snaps = Path(cache) / ("models--" + model_id.replace("/", "--")) / "snapshots"
        if revision and (snaps / revision).exists():
            return str(snaps / revision)
    return model_id


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
