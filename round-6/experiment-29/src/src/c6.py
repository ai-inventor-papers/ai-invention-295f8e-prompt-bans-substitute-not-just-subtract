#!/usr/bin/env python3
"""Paths, constants and small utilities for the engine-factorial artifact (iteration 6, direction E).

The vendored iteration-4 code lives in vendor/exp22 (its cfg.ROOT resolves there, so its inputs/, prompts/ and
directions/ resolve to the verified copies). This module puts vendor/exp22/{src_base,src,analysis} and
vendor/exp28/src on sys.path; nothing in vendor/ is edited.

Engines (one bf16 snapshot of Qwen/Qwen3-8B b968826d):
  a  W8A8   e4m3 weights (per-output-channel) x e4m3 activations (per token)   -- iteration-4 engine (native kernel)
  b  W8A16  the same e4m3 weights x bf16 activations                             -- weight rounding only
  c  W16A8  bf16 weights x per-token e4m3 fake-quantised activations             -- activation rounding only
  d  BF16   bf16 weights x bf16 activations                                       -- reference
Row keys: <engine>|<task>|<template>|<arm>|<sample_id>.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
V22 = ROOT / "vendor" / "exp22"
V28 = ROOT / "vendor" / "exp28"
# appended (not prepended): this artifact's own modules always win a name lookup; the vendored modules keep their
# own names (cfg, engine, cfg4, ctx4, engine4, hooks4, prompts4, screen, label_worker, regate_rules, ...)
_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
for _p in (V22 / "src_base", V22 / "src", V22 / "analysis", V28 / "src"):
    if str(_p) not in sys.path:
        sys.path.append(str(_p))

INPUTS = ROOT / "inputs"
E22 = INPUTS / "exp22"
E19 = INPUTS / "exp19"
E27 = INPUTS / "exp27"
E28 = INPUTS / "exp28"
DATA = ROOT / "data"
RAW_DIR = DATA / "raw"
LABELS = DATA / "labels.jsonl"
REALISED = DATA / "realised_disp.jsonl"
RESULTS = ROOT / "results"
FIGS = ROOT / "figures"
PRED = ROOT / "predictions"
LOGS = ROOT / "logs"
CACHE = ROOT / "cache"
COMMIT_LOG = ROOT / "commitments.log"
for _d in (DATA, RAW_DIR, RESULTS, FIGS, PRED, LOGS, CACHE):
    _d.mkdir(parents=True, exist_ok=True)

MODEL_ID = "Qwen/Qwen3-8B"
MODEL_REVISION = "b968826d9c46dd6066d109eabc6255188de91218"
ENGINES = {"a": "W8A8", "b": "W8A16", "c": "W16A8", "d": "BF16"}
ENGINE_DESC = {
    "a": "e4m3 weights (per-output-channel absmax/448) x e4m3 activations (per-token absmax/448); torch._scaled_mm",
    "b": "e4m3 weights x bf16 activations; fp32 accumulate, x s_w, one rounding to bf16",
    "c": "bf16 weights x per-token e4m3 fake-quantised activations; fp32 accumulate, x s_x, one rounding to bf16",
    "d": "bf16 weights x bf16 activations (F.linear, cuBLAS)",
}
WEIGHT_SET = {"a": "Q", "b": "Q", "c": "B", "d": "B"}
TASKS = ("T10", "T2")
DESCRIPTIVE_TASKS = ("T03",)
SEEDS_POP = list(range(9101, 9141))
REPRO_SEEDS = list(range(9101, 9111))
POSCTRL_SEED = 9004
TEMPLATES = ["W1", "W2", "W3", "W4", "W5"]
K_TWIN = list(range(10))          # twin N = 50 (k 0-9 x W1-W5)
K_SCREEN = [0, 1]                 # screen N = 10
K_CONFIRM = [2, 3, 4, 5]          # +20 -> pooled 30
K_PN = list(range(10))            # PN N = 50 per (task, alpha)
MAX_NEW = 1024
FENCE = {"T10": "bench", "T03": "bench", "T2": "path"}
DEFAULTS = {"T10": "union_find", "T2": "dijkstra", "T03": "full_sort"}
ESC_EXCESS = 0.20
ESC_PASS_FRAC = 0.8
BUDGET_MSG = "AI Inventor per-run OpenRouter budget"
OPENROUTER_CAP_USD = 0.5
GENESIS = hashlib.sha256(b"iter6_dir2_engine_E").hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def stable_seed(*parts: Any) -> int:
    """exp8/exp17/exp19 convention: sha256 of the '|'-joined str() of the parts, mod 2^63."""
    return int(hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest(), 16) % (2 ** 63)


def read_jsonl(p: Path) -> list[dict[str, Any]]:
    p = Path(p)
    if not p.exists():
        return []
    out = []
    with open(p) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue   # a torn last line of a file still being appended
    return out


def append_jsonl(p: Path, rows: Iterable[dict[str, Any]]) -> None:
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a") as f:
        for r in rows:
            f.write(json.dumps(r, default=_json_default) + "\n")
        f.flush()
        os.fsync(f.fileno())


def _json_default(o: Any) -> Any:
    try:
        import numpy as np
        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, np.floating):
            return float(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
    except ImportError:
        pass
    return str(o)


def write_json(p: Path, obj: Any) -> None:
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1, default=_json_default))
    tmp.replace(p)


def read_json(p: Path) -> Any:
    return json.loads(Path(p).read_text())


def row_key(engine: str, r: dict[str, Any]) -> str:
    return f"{engine}|{r['task']}|{r['template']}|{r['arm']}|{r['sample_id']}"


def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, c - h), min(1.0, c + h))


def setup_logging(name: str) -> None:
    from loguru import logger

    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    logger.add(str(LOGS / f"{name}.log"), rotation="30 MB", level="DEBUG")


class Timer:
    def __init__(self) -> None:
        self.t0 = time.time()

    def __call__(self) -> float:
        return time.time() - self.t0
