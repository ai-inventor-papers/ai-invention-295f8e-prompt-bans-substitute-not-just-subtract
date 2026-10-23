#!/usr/bin/env python3
"""Iteration-8 constants and utilities: one DAS protocol (linear orthonormal map, bounded KL objective, class-margin
readout) at the decision token and the task band of Qwen3-8B (T10) and at the decision token of gemma-3-4b-it (T1 grid).

Conventions (inherited from iterations 6-7, restated in README.md):
- BLOCK l = decoder block l (0-based); its OUTPUT is HF hidden_states[l + 1]. Every edit replaces a block output.
- Decision position d: the position of the last prefilled opening token; its next-token logits choose the decision
  token (T10: response token 11 after ' def'; grid: response index 32 after c*).
- Class probability P(c) = sum of softmax mass over the class token set T_c; P(other) = 1 - sum_c P(c).
- Margin = log P(c_src) - log P(c_base); Delta = margin_edit - margin_base on the SAME computation path.
- CRN: slot s of a unit uses u_stream(unit, 'iter8', s) (PCG64 of a sha256 seed); every arm of a cell shares it.
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
INPUTS = ROOT / "inputs"
DATA = ROOT / "data"
RESULTS = ROOT / "results"
FIGS = ROOT / "figures"
LOGS = ROOT / "logs"
CACHE = ROOT / "cache"
MAPS = ROOT / "das_maps"
PRED = ROOT / "predictions"
AUDIT = ROOT / "audit"
PROMPTS_DIR = ROOT / "prompts"
for _d in (DATA, RESULTS, FIGS, LOGS, CACHE, MAPS, PRED, AUDIT, PROMPTS_DIR):
    _d.mkdir(parents=True, exist_ok=True)
COMMIT_LOG = ROOT / "commitments.log"
DEVIATIONS = RESULTS / "deviations.jsonl"

# Source artifacts (read-only; only s0_inputs.py reads them). This folder sits at
# <run>/3_invention_loop/iter_8/gen_art/<artifact>; earlier iterations are found relative to it (override: AII_LOOP_DIR).
LOOP = Path(os.environ.get("AII_LOOP_DIR", ROOT.parents[2]))

# ------------------------------------------------------------------------------------------------ models
QWEN_ID = "Qwen/Qwen3-8B"
QWEN_REV = "b968826d9c46dd6066d109eabc6255188de91218"
GEMMA_ID = "google/gemma-3-4b-it"
GEMMA_REV = "093f9f388b31de276ce2de164bdc2081324b9767"
FAMILY = {
    "qwen": {"id": QWEN_ID, "rev": QWEN_REV, "n_layers": 36, "d_model": 4096, "n_kv": 8, "head_dim": 128,
             "band": tuple(range(12, 24)), "stop_ids": (151645, 151643)},
    "gemma": {"id": GEMMA_ID, "rev": GEMMA_REV, "n_layers": 34, "d_model": 2560, "n_kv": 4, "head_dim": 256,
              "band": tuple(range(11, 23)), "stop_ids": (1, 106)},
}

# ------------------------------------------------------------------------------------------------ units
# T10 (Qwen3-8B): canonical opening tokens 0..10 = '```python\ndef solve(n, edges):\n' + indent + ' def'
OPEN_T10 = [73594, 12669, 198, 750, 11625, 1445, 11, 12822, 982, 262, 707]
UNITS = {
    "T10": {"family": "qwen", "task": "T10", "default": "union_find", "classes": ["bfs", "dfs", "union_find"],
            "primary": "dfs", "max_new": 512, "fence": "bench"},
    "GRID": {"family": "gemma", "task": "T1", "default": None, "classes": ["bfs", "dfs"], "primary": "bfs",
             "max_new": 1024, "fence": "path"},
}
# display names of the forced sources (equal-structure paraphrases; template k x name j)
T10_FORCED_TEMPLATES = ("Implement {j} for this task.", "Use {j} to solve this task.", "Solve this task with {j}.",
                        "Your solution should use {j}.", "Write an implementation based on {j}.")
T10_DISPLAY = {
    "bfs": ("breadth-first search (BFS)", "BFS", "breadth-first search", "a breadth-first search"),
    "dfs": ("depth-first search (DFS)", "DFS", "depth-first search", "a depth-first search"),
    "union_find": ("union-find (disjoint set union)", "union-find", "a disjoint-set union", "a union-find structure"),
}
TRAIN_FAM = (0, 1, 2)
HELD_FAM = (3, 4)
TRAIN_W = ("W1", "W2", "W3")
HELD_W = ("W4", "W5")
NOUN_SPLIT_SEED = 8001
N_T10_NOUNS = 32                      # 12 frozen (iteration 7) + 20 single-token nouns from art_j3Rm_lr2nzR6

# ------------------------------------------------------------------------------------------------ DAS protocol
RANKS = (1, 2, 4, 8)
K_MAX = 8
FIT_STEPS = 240
SCAN_STEPS = 100
LR = 2e-2
BATCH_DEC = 48
BATCH_BAND = 8
VAL_EVERY = 20
PATIENCE = 3
N_RANDOM_SUBSPACES = 50
RANDOM_SEED0 = 7000
LABEL_CONTROL_SEEDS = (10, 11, 12)
FIT_SEEDS = (0, 1, 2)
N_BOOT = 2000
BOOT_SEED = 20261023
OFF_MANIFOLD = 1.5
TRAIN_PAIR_CAP = 2000
HELD_PAIR_CAP = 600
THRESH = {"c1_median_max": 0.05, "c2_ratio_max": 0.10, "c3_ratio_max": 0.25, "c4_min": 0.5, "c5_min": 0.5,
          "c6_pct": 95.0, "c7_cos_min": 0.5, "c7_pct": 99.0, "V0_tf": 0.5, "V0_tf_lo": 0.25, "V0_gen": 0.5,
          "V0_pass_ratio": 0.8, "V0_mcnemar_p": 0.05}
PROSPECTIVE_SEEDS = tuple(range(98001, 98025))
BUDGET_MSG = "AI Inventor per-run OpenRouter budget"
OPENROUTER_CAP_USD = 0.30


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


def u_stream(*key: Any, n: int = 1536) -> np.ndarray:
    return np.random.Generator(np.random.PCG64(stable_seed(*key))).random(n)


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
    if isinstance(o, float) and not math.isfinite(o):
        return None
    raise TypeError(f"not JSON serialisable: {type(o)}")


def _clean(o: Any) -> Any:
    if isinstance(o, float):
        return o if math.isfinite(o) else None
    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    return o


def read_json(p: Path) -> Any:
    return json.loads(Path(p).read_text())


def write_json(p: Path, obj: Any) -> None:
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(_clean(obj), indent=1, default=_json_default))
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
            fh.write(json.dumps(_clean(r), default=_json_default) + "\n")
        fh.flush()


def write_jsonl(p: Path, rows: Iterable[dict[str, Any]]) -> None:
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    with open(tmp, "w") as fh:
        for r in rows:
            fh.write(json.dumps(_clean(r), default=_json_default) + "\n")
    tmp.replace(p)


def add_deviation(key: str, text: str, **kw: Any) -> None:
    append_jsonl(DEVIATIONS, [{"key": key, "text": text, "utc": utc_now(), **kw}])
    logger.warning(f"DEVIATION {key}: {text}")


def model_path(model_id: str, revision: str) -> str:
    cache = os.environ.get("HF_HUB_CACHE")
    if cache:
        snap = Path(cache) / ("models--" + model_id.replace("/", "--")) / "snapshots" / revision
        if snap.exists():
            return str(snap)
    return model_id
