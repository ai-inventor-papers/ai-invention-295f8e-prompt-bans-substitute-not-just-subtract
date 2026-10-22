#!/usr/bin/env python3
"""Paths, constants and small utilities of iteration-7 step K (plan-noise unit x seeds crosswalk).

The vendored iteration-4 code lives in vendor/exp22 (its cfg.ROOT resolves there, so its inputs/, prompts/ and
directions/ resolve to the verified copies); vendor/exp28/src holds the iteration-5 T2 re-gate rule. This module
APPENDS those folders to sys.path (this artifact's own modules always win a name lookup); nothing in vendor/ is edited.
The exp27 code (vendor/exp27/src) has its own `cfg` module and therefore only ever runs in its own process
(src/knobs_k.py).

Designs (S1): D1 = U_abs x S4, D2 = U_abs x S5, D3 = U_bf x S4, D4 = U_bf x S5, D5 = U_bf* x S4.
Profiles (S2, S4 seeds): PTOP, PREST, PSHUF.  Arms are '<design>_a<alpha>' (e.g. 'D1_a2'); TWIN is the clean twin.
Row keys: <task>|<template>|<arm>|<sample_id>.
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
V27 = ROOT / "vendor" / "exp27"
_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
for _p in (V22 / "src_base", V22 / "src", V22 / "analysis", V28 / "src"):
    if str(_p) not in sys.path:
        sys.path.append(str(_p))

INPUTS = ROOT / "inputs"
E29 = INPUTS / "exp29"
E27 = INPUTS / "exp27"
E19 = INPUTS / "exp19"
E23 = INPUTS / "exp23"
E30 = INPUTS / "exp30"
E22 = INPUTS / "exp22"
DATA = ROOT / "data"
RAW_DIR = DATA / "raw"
RAW = RAW_DIR / "raw_k.jsonl"
LABELS = DATA / "labels.jsonl"
REALISED = DATA / "realised_disp.jsonl"
RESULTS = ROOT / "results"
FIGS = ROOT / "figures"
PRED = ROOT / "predictions"
LOGS = ROOT / "logs"
CACHE = ROOT / "cache"
AUDIT = ROOT / "audit"
COMMIT_LOG = ROOT / "commitments.log"
for _d in (DATA, RAW_DIR, RESULTS, FIGS, PRED, LOGS, CACHE, AUDIT):
    _d.mkdir(parents=True, exist_ok=True)

MODEL_ID = "Qwen/Qwen3-8B"
MODEL_REVISION = "b968826d9c46dd6066d109eabc6255188de91218"
BASE_MODEL_ID = "Qwen/Qwen3-8B-Base"
BASE_REVISION = "49e3418fbbbca6ecbdf9608b4d22e5a407081db4"
PRECISION = "BF16 weights and activations (HF transformers 4.57.6, sdpa, torch 2.8.0+cu128); engine d of exp29"
TEMPLATES = ("W1", "W2", "W3", "W4", "W5")
S1_TASKS = ("T10", "T2")
D5_TASKS = ("T03", "T10", "T2", "T05", "T1")          # S3 decisive tasks (exp27 D5)
EDIT_BLOCKS = list(range(12, 24))
ALL_BLOCKS = list(range(36))
D_MODEL = 4096
FENCE = {"T10": "bench", "T03": "bench", "T05": "bench", "T2": "path", "T1": "path"}
MAX_NEW = {"T10": 1024, "T03": 1024, "T05": 1024, "T2": 1536, "T1": 1536}
DEFAULTS = {"T10": "union_find", "T2": "dijkstra", "T03": "full_sort", "T05": "hash_map", "T1": "bfs"}
DESIGNS = ("D1", "D2", "D3", "D4", "D5")
PROFILES = ("PTOP", "PREST", "PSHUF")
DESIGN_DEF = {"D1": ("U_abs", "S4"), "D2": ("U_abs", "S5"), "D3": ("U_bf", "S4"), "D4": ("U_bf", "S5"),
              "D5": ("U_bf_star", "S4"), "PTOP": ("P_top", "S4"), "PREST": ("P_rest", "S4"),
              "PSHUF": ("P_shuf", "S4")}
K10 = list(range(10))
K20 = list(range(20))
BUDGET_MSG = "AI Inventor per-run OpenRouter budget"
OPENROUTER_CAP_USD = 0.50
GENESIS = hashlib.sha256(b"iter7_K_genesis").hexdigest()
B_CANDIDATES = (12, 10, 8, 7, 6, 4)


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


def _json_default(o: Any) -> Any:
    try:
        import numpy as np
        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, np.floating):
            return float(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
        if isinstance(o, np.bool_):
            return bool(o)
    except ImportError:
        pass
    return str(o)


def append_jsonl(p: Path, rows: Iterable[dict[str, Any]]) -> None:
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a") as f:
        for r in rows:
            f.write(json.dumps(r, default=_json_default) + "\n")
        f.flush()
        os.fsync(f.fileno())


def write_json(p: Path, obj: Any) -> None:
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1, default=_json_default))
    tmp.replace(p)


def read_json(p: Path) -> Any:
    return json.loads(Path(p).read_text())


def row_key(r: dict[str, Any]) -> str:
    return f"{r['task']}|{r['template']}|{r['arm']}|{r['sample_id']}"


def parse_arm(arm: str) -> dict[str, Any]:
    if arm == "TWIN":
        return {"family": "TWIN", "design": "TWIN", "alpha": None}
    d, a = arm.rsplit("_a", 1)
    unit, seeds = DESIGN_DEF[d]
    return {"family": "S2" if d in PROFILES else "S1", "design": d, "alpha": float(a), "unit": unit, "seeds": seeds}


def s4_arm(alpha: float) -> str:
    """exp29/exp19 PN arm string used inside the S4 seed (asserted against logged seeds in gate G3)."""
    return "PN_a1" if float(alpha) == 1.0 else "PN_a2"


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


def add_deviation(code: str, text: str, consequence: str) -> None:
    append_jsonl(RESULTS / "deviations.jsonl", [{"code": code, "deviation": text, "consequence": consequence,
                                                 "utc": utc_now()}])


class Timer:
    def __init__(self) -> None:
        self.t0 = time.time()

    def __call__(self) -> float:
        return time.time() - self.t0
