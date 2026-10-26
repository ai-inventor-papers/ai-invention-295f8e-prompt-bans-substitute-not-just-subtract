"""Shared utilities: paths, logging, hashing, JSONL IO, seeds and the small statistics used everywhere."""

from __future__ import annotations

import hashlib
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from loguru import logger

ROOT = Path(__file__).resolve().parent
GEN_DIR = ROOT / "generations"
SUM_DIR = ROOT / "summaries"
LOG_DIR = ROOT / "logs"
FIG_DIR = ROOT / "figures"
STATE_DIR = ROOT / "states"
for _d in (GEN_DIR, SUM_DIR, LOG_DIR, FIG_DIR, STATE_DIR):
    _d.mkdir(parents=True, exist_ok=True)

MODEL_ID = "Qwen/Qwen3-8B"
TASKS = ("T1", "T2")
CONDITIONS = ("baseline", "ban")


def setup_logging(name: str) -> None:
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    logger.add(str(LOG_DIR / f"{name}.log"), rotation="30 MB", level="DEBUG")


def stable_seed(*parts) -> int:
    h = hashlib.sha256(repr(tuple(parts)).encode()).hexdigest()
    return int(h, 16) % (2 ** 31 - 1000)


def sha256_file(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def log_hash(name: str, path: Path) -> str:
    h = sha256_file(path)
    with open(LOG_DIR / "hashes.log", "a") as fh:
        fh.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')}\t{time.time():.3f}\t{name}\t{path.name}\t{h}\n")
    return h


def append_jsonl(path: Path, rows: list[dict]) -> None:
    with open(path, "a") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")


def read_jsonl(path: Path) -> list[dict]:
    if not Path(path).exists():
        return []
    out = []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue  # a line still being written by a concurrent appender
    return out


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float, float]:
    if n == 0:
        return (float("nan"), float("nan"), float("nan"))
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (p, max(0.0, c - h), min(1.0, c + h))


def hill1(labels: list) -> float:
    """Hill number of order 1 = exp(Shannon entropy in nats) of the label distribution."""
    if not labels:
        return float("nan")
    _, cnt = np.unique(np.asarray(labels, dtype=object).astype(str), return_counts=True)
    p = cnt / cnt.sum()
    return float(np.exp(-(p * np.log(p)).sum()))


def entropy_bits(counts) -> float:
    c = np.asarray(counts, dtype=float)
    if c.sum() <= 0:
        return float("nan")
    p = c[c > 0] / c.sum()
    return float(-(p * np.log2(p)).sum())


def tvd(p, q) -> float:
    p = np.asarray(p, dtype=float)
    q = np.asarray(q, dtype=float)
    if p.sum() == 0 or q.sum() == 0:
        return float("nan")
    return float(0.5 * np.abs(p / p.sum() - q / q.sum()).sum())


def js_div(p, q) -> float:
    p = np.asarray(p, dtype=float)
    q = np.asarray(q, dtype=float)
    p = p / p.sum()
    q = q / q.sum()
    m = 0.5 * (p + q)

    def kl(a, b):
        mask = a > 0
        return float((a[mask] * np.log2(a[mask] / b[mask])).sum())

    return 0.5 * kl(p, m) + 0.5 * kl(q, m)
