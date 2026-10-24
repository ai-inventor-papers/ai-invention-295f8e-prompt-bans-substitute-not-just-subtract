#!/usr/bin/env python3
"""Shared helpers: workspace paths, logging, hashing, JSONL append, deviations, time ledger and partial status."""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from loguru import logger

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
DATA = ROOT / "data"
RESULTS = ROOT / "results"
LOGS = ROOT / "logs"
PRED = ROOT / "predictions"
FIGS = ROOT / "figures"
for _d in (DATA, RESULTS, LOGS, PRED, FIGS):
    _d.mkdir(parents=True, exist_ok=True)

# Wall-clock origin of the artifact (written once at session start; all milestones are relative to it).
T0_FILE = LOGS / "t0_utc.txt"

ENGINE_TAG = "vllm0.11.0|Qwen3-8B-FP8@220b46e|fp8-marlin-w8a16|RTX4090"
MODEL_ID = "Qwen/Qwen3-8B-FP8"
MODEL_REV = "220b46e3b2180893580a4454f21f22d3ebb187d3"
SERVED_NAME = "qwen3-8b"

ARM_IDS = {"T1.0": 0, "T1.6": 1, "DTB": 2, "RPB": 3, "IDEA": 4, "NS": 5}
CORE_ARMS = ["T1.0", "T1.6", "DTB", "RPB"]
SEEDS = [2, 3]


def setup_logging(name: str, level: str = "INFO") -> None:
    logger.remove()
    logger.add(sys.stdout, level=level, format="{time:HH:mm:ss}|{level:<7}|{message}")
    logger.add(LOGS / f"{name}.log", rotation="30 MB", level="DEBUG")


def utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def t0_epoch() -> float:
    s = T0_FILE.read_text().strip()
    return time.mktime(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ")) - time.timezone


def elapsed_h() -> float:
    return (time.time() - t0_epoch()) / 3600.0


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def append_jsonl(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(row, separators=(",", ":"), default=_json_default) + "\n"
    with open(path, "a") as f:
        f.write(line)
        f.flush()
        os.fsync(f.fileno())


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                logger.warning(f"skipping truncated JSONL line in {path.name}")
    return out


def _json_default(o: Any):
    import numpy as np
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (bytes, bytearray)):
        return o.hex()
    if isinstance(o, Path):
        return str(o)
    raise TypeError(f"not JSON serialisable: {type(o)}")


EVAL_DIR = DATA / "eval"
EVAL_PART_BYTES = 80 * 1024 * 1024  # evaluation rows are split into parts under the 100 MB publish limit


def eval_parts() -> list[Path]:
    """The evaluation-row files in order: data/eval/eval_part_001.jsonl, eval_part_002.jsonl, ..."""
    return sorted(EVAL_DIR.glob("eval_part_*.jsonl"))


def read_eval_rows() -> list[dict]:
    rows: list[dict] = []
    for p in eval_parts():
        rows.extend(read_jsonl(p))
    return rows


def eval_append_path() -> Path:
    """The part new rows are appended to: the last part, or a new one once it reaches EVAL_PART_BYTES."""
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    parts = eval_parts()
    if parts and parts[-1].stat().st_size < EVAL_PART_BYTES:
        return parts[-1]
    return EVAL_DIR / f"eval_part_{len(parts) + 1:03d}.jsonl"


def write_json(path: Path, obj: Any, indent: int | None = 1) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=indent, default=_json_default))
    tmp.replace(path)


def log_deviation(key: str, text: str, **extra) -> None:
    """Append (or update by key) a protocol departure in results/deviations.json."""
    p = RESULTS / "deviations.json"
    devs = json.loads(p.read_text()) if p.exists() else []
    devs = [d for d in devs if d.get("key") != key]
    devs.append(dict(key=key, utc=utc(), text=text, **extra))
    write_json(p, devs)


def ledger(milestone: str, planned_h: float | None = None, **extra) -> None:
    """One row per milestone: planned vs actual hours since T0."""
    append_jsonl(LOGS / "time_ledger.jsonl", dict(milestone=milestone, utc=utc(), actual_h=round(elapsed_h(), 3),
                                                  planned_h=planned_h, **extra))


def partial_status(stage: str, **fields) -> None:
    p = RESULTS / "partial_status.json"
    cur = json.loads(p.read_text()) if p.exists() else {}
    cur.update(dict(stage=stage, utc=utc(), elapsed_h=round(elapsed_h(), 3), **fields))
    write_json(p, cur)
