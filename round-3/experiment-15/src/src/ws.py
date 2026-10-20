#!/usr/bin/env python3
"""Workspace bridge: paths, frozen constants, logging, jsonl helpers and the import path of the copied, read-only
frozen bench (inputs/exp11/bench).  Every cache the bench code writes (judge cache, spend ledger) is redirected
into this workspace; nothing under inputs/ is ever written."""

from __future__ import annotations

import hashlib
import json
import math
import os
import sys
from pathlib import Path
from typing import Any, Iterable

WS = Path(__file__).resolve().parent.parent
INPUTS = WS / "inputs"
EXP11 = INPUTS / "exp11"            # root passed to bench functions that read root/bench/...
BENCH = EXP11 / "bench"
EXP10 = INPUTS / "exp10"
DATA = WS / "data"
RESULTS = WS / "results"
PRED = WS / "predictions"
LOGS = WS / "logs"
FIGS = WS / "figures"
GEN_IDS = DATA / "gen_ids"
for _d in (DATA, RESULTS, PRED, LOGS, FIGS, GEN_IDS):
    _d.mkdir(parents=True, exist_ok=True)

# the bench package is imported as `bench.common.*` (its modules use relative imports)
if str(EXP11) not in sys.path:
    sys.path.insert(0, str(EXP11))

MODEL_ID = "meta-llama/Llama-3.1-8B-Instruct"
MODEL_REV = "0e9e39f249a16976918f6564b8830bc894c89659"
MODEL_TAG = "meta-llama/Llama-3.1-8B-Instruct@0e9e39f(bf16)"
DATE_STRING = "26 Jul 2024"
EOS_IDS = [128001, 128008, 128009]
MAX_TOKENS = 1024
ASSOC_MAX_TOKENS = 96
FILLER = " ."            # protocol v3 padding for bench twins (exp7 frozen)
MAX_PAD = 40
JUDGE_CAP_USD = 0.70
FROZEN_TASKS = ["T03", "T04", "T06", "T05", "T10", "R1", "T08", "R3", "T13", "R6", "T14", "T11"]
PUSH_LAYERS = list(range(11, 22))       # decoder layers 11..21 (hidden_states[l+1] in HF)
RANDDIR_SEEDS = [20261020, 20261021, 20261022]
TEMPLATES = {
    1: "Do not use {X} for this task.",
    2: "Your solution must not rely on {X}.",
    3: "Avoid {X} entirely.",
    4: "{X} is not allowed here.",
    5: "Write a correct solution that does not use {X}.",
}
NONCE_X = "the Zorblax method"
NOVELTY = "Write a novel algorithm for this task, one you have not seen before."
SMOOTH = {"f": 0.93, "uniform_S": 0.05, "other": 0.02}


def model_path() -> str:
    """Local snapshot (run shared HF cache; downloads if absent)."""
    from huggingface_hub import snapshot_download

    try:
        return snapshot_download(MODEL_ID, revision=MODEL_REV, local_files_only=True)
    except Exception:  # noqa: BLE001 - not cached yet
        return snapshot_download(MODEL_ID, revision=MODEL_REV, allow_patterns=["*.json", "*.safetensors", "tokenizer*"])


def request_seed(task: str, cond: str, tpl: Any, sample_id: Any) -> int:
    """exp10 rule: int(sha256('task|cond|tpl|sample_id')[:8], 16)."""
    return int(hashlib.sha256(f"{task}|{cond}|{tpl}|{sample_id}".encode()).hexdigest()[:8], 16)


def ids_sha(ids: list[int]) -> str:
    return hashlib.sha256(json.dumps(list(map(int, ids))).encode()).hexdigest()


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with Path(p).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _default(o: Any) -> Any:
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
    if isinstance(o, (set, tuple)):
        return list(o)
    if isinstance(o, Path):
        return str(o)
    raise TypeError(f"not JSON serialisable: {type(o)}")


def clean_nan(o: Any) -> Any:
    if isinstance(o, float) and not math.isfinite(o):
        return None
    if isinstance(o, dict):
        return {str(k): clean_nan(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean_nan(v) for v in o]
    return o


def read_jsonl(p: Path) -> list[dict[str, Any]]:
    p = Path(p)
    if not p.exists():
        return []
    out = []
    lines = p.read_text().splitlines()
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            if i == len(lines) - 1:  # a concurrently appended, not yet complete last line
                continue
            raise
    return out


def append_jsonl(p: Path, rows: Iterable[dict[str, Any]]) -> int:
    n = 0
    with Path(p).open("a") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False, default=_default) + "\n")
            n += 1
    return n


def write_jsonl(p: Path, rows: Iterable[dict[str, Any]]) -> int:
    n = 0
    with Path(p).open("w") as fh:
        for r in rows:
            fh.write(json.dumps(clean_nan(r), ensure_ascii=False, default=_default) + "\n")
            n += 1
    return n


def write_json(p: Path, obj: Any, indent: int | None = 1) -> None:
    Path(p).write_text(json.dumps(clean_nan(obj), indent=indent, ensure_ascii=False, default=_default))


def read_json(p: Path) -> Any:
    return json.loads(Path(p).read_text())


def setup_logging(name: str) -> None:
    from loguru import logger

    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    logger.add(str(LOGS / f"{name}.log"), rotation="30 MB", level="DEBUG")


def trunc(s: str | None, n: int = 300) -> str:
    s = s or ""
    return s if len(s) <= n else s[:n] + f"...[+{len(s) - n}]"


def set_ram_limit(gb: float) -> None:
    """Hard address-space cap so a runaway job raises MemoryError instead of OOM-killing the container."""
    import resource

    lim = int(gb * 1024**3)
    resource.setrlimit(resource.RLIMIT_AS, (lim, lim))


def detect_cpus() -> int:
    try:
        parts = Path("/sys/fs/cgroup/cpu.max").read_text().split()
        if parts[0] != "max":
            return math.ceil(int(parts[0]) / int(parts[1]))
    except (FileNotFoundError, ValueError):
        pass
    try:
        return len(os.sched_getaffinity(0))
    except (AttributeError, OSError):
        return os.cpu_count() or 1
