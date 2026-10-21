#!/usr/bin/env python3
"""Shared paths, constants, logging and IO helpers for the ban-readout artifact.

Every stage of method.py imports this module, so the protocol constants (models, seeds, label maps, templates)
live in exactly one place. No absolute server path is written here: the iteration-1 folders are located
relative to this workspace (or through $ITER1_GEN_ART).
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import os
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Any, Iterable

from loguru import logger

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
RESULTS = ROOT / "results"
FIGS = ROOT / "figures"
LOGS = ROOT / "logs"
INPUTS = ROOT / "inputs"
PROMPTS_DIR = ROOT / "prompts"
TENSORS = RESULTS / "tensors"
for _d in (RESULTS, FIGS, LOGS, PROMPTS_DIR, TENSORS):
    _d.mkdir(parents=True, exist_ok=True)

EXP1 = INPUTS / "exp1"  # copied: prompts/, tasks/, labeller/, data/samples.jsonl, common.py
EXP3 = INPUTS / "exp3"  # copied: states/*_meta.json, labeller/, analysis/, prompts_exp3.json
EXP6 = INPUTS / "exp6"  # copied: analysis/metrics.py, phrasing.py, thinking.py
# Iteration-1 folders are read in place (the exp3 npz state parts are ~800 MB and are never copied).
RUNS_DIR = ROOT.parents[4]
ITER1 = Path(os.environ.get("ITER1_GEN_ART",
                            str(RUNS_DIR / "run_4VFKidE1bxPG" / "." / "round-1" / ".")))
EXP3_SRC = ITER1 / "gen_art_experiment_3"
DATASET_SRC = ITER1 / "gen_art_dataset_1"

# ---------------------------------------------------------------- models (see deviations.json D01)
MODEL_HF = "Qwen/Qwen3-8B"            # bf16 weights: every state / attention / CE readout
MODEL_GEN = "Qwen/Qwen3-8B-FP8"       # official block-FP8 checkpoint: every vLLM generation (16 GB GPU)
MODEL_BASE = "Qwen/Qwen3-8B-Base"     # SAE training model, for the transfer test
SAE_REPO = "Qwen/SAE-Res-Qwen3-8B-Base-W64K-L0_50"
SAE_K = 50
JLENS_REPO = "senku21x/cot-oracle-jlens"
JLENS_GIT = "https://github.com/anthropics/jacobian-lens"

TASKS = ("t1", "t2")
EXP3_TASK = {"t1": "T1", "t2": "T2"}
# exp3 label strings -> canonical exp1 catalogue ids
EXP3_LABEL_MAP = {"BFS": "bfs", "DFS": "dfs", "unit_dijkstra": "dijkstra", "dijkstra": "dijkstra",
                  "bellman_ford_spfa": "bf_spfa"}
BANNED = {"t1": "bfs", "t2": "dijkstra"}           # X: the modal approach that the ban names
SUBSTITUTE = {"t1": "dfs", "t2": "bf_spfa"}        # X': the main natural substitute under the ban
X_NAME = {"t1": "breadth-first search (BFS)", "t2": "Dijkstra" + chr(39) + "s algorithm"}
XSUB_NAME = {"t1": "depth-first search (DFS)", "t2": "Bellman-Ford or SPFA"}

# Frozen protocol-v2 templates: (ban, mention, neutral)
TEMPLATES: dict[str, tuple[str, str, str]] = {
    "W1": ("Do not use {X} for this task.", "You could use {X} for this task.", "Do not use {N} for this task."),
    "W2": ("Your solution must not rely on {X}.", "Your solution may rely on {X}.",
           "Your solution must not rely on {N}."),
    "W3": ("Avoid {X} entirely.", "Consider {X} first.", "Avoid {N} entirely."),
    "W4": ("{X} is not allowed here.", "{X} is allowed here.", "{N} is not allowed here."),
    "W5": ("Write a correct solution that does not use {X}.", "Write a correct solution that may use {X}.",
           "Write a correct solution that does not use {N}."),
}
TEMPLATE_IDS = list(TEMPLATES)

# ---------------------------------------------------------------- seeds (plan CONVENTIONS)
SEED_FRESH = 20261020        # fresh pool: 20261020 + i
SEED_TRACE = 7000            # thinking base traces: 7000 + i
SEED_CONT = 9000             # continuations: 9000 + trace*1000 + boundary*10 + j
CRN_SEEDS = list(range(50))
CRN_TEMPS = (0.3, 0.7, 1.0, 1.3)
GUMBEL_SEED_OFFSET = 10 ** 6

THINK_DECODING = dict(temperature=0.6, top_p=0.95, top_k=20)  # Qwen3 recommended thinking settings (D06)
MAIN_DECODING = dict(temperature=1.0, top_p=1.0, top_k=-1)      # protocol thinking-off decoding

OPENROUTER_CAP_USD = 0.30
BUDGET_MSG = "AI Inventor per-run OpenRouter budget"
JUDGE_MODEL = "openai/gpt-4.1-mini"  # exp1's canonical judge


def setup_logging(name: str) -> None:
    """loguru: stdout INFO + rotating DEBUG file sink per stage."""
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    logger.add(str(LOGS / f"{name}.log"), rotation="30 MB", level="DEBUG")


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def sha256_file(p: Path, chunk: int = 1 << 24) -> str:
    h = hashlib.sha256()
    with Path(p).open("rb") as fh:
        while True:
            b = fh.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


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
    if isinstance(o, (set, frozenset)):
        return sorted(o)
    if isinstance(o, Path):
        return str(o)
    raise TypeError(f"not JSON serialisable: {type(o)}")


def _clean_nan(o: Any) -> Any:
    if isinstance(o, float) and not math.isfinite(o):
        return None
    if isinstance(o, dict):
        return {k: _clean_nan(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean_nan(v) for v in o]
    return o


def write_json(p: Path, obj: Any, indent: int | None = 1) -> None:
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(_clean_nan(json.loads(json.dumps(obj, default=_json_default))), indent=indent,
                              ensure_ascii=False))
    tmp.replace(p)


def read_json(p: Path, default: Any = None) -> Any:
    p = Path(p)
    if not p.exists():
        return default
    return json.loads(p.read_text())


def read_jsonl(p: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    p = Path(p)
    if not p.exists():
        return rows
    with p.open() as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    logger.warning(f"skipping malformed jsonl line in {p.name}")
    return rows


def write_jsonl(p: Path, rows: Iterable[dict[str, Any]]) -> None:
    p = Path(p)
    tmp = p.with_suffix(p.suffix + ".tmp")
    with tmp.open("w") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False, default=_json_default) + "\n")
    tmp.replace(p)


def append_jsonl(p: Path, rows: Iterable[dict[str, Any]]) -> None:
    with Path(p).open("a") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False, default=_json_default) + "\n")


def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float | None, float | None]:
    if n <= 0:
        return (None, None)
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, c - h), min(1.0, c + h))


def cap_first(s: str) -> str:
    return s[:1].upper() + s[1:] if s else s


def load_module(name: str, path: Path) -> ModuleType:
    """Import a single iteration-1 source file under a unique module name (no sys.path pollution)."""
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def exp1_on_path() -> None:
    """exp1's labeller/ and tasks/ are packages that import exp1's common.py; put exp1 first on sys.path."""
    p = str(EXP1)
    if p not in sys.path:
        sys.path.insert(0, p)


# ---------------------------------------------------------------- deviations / timing / spend
_LOCK = threading.Lock()
DEVIATIONS = RESULTS / "deviations.json"
TIMING = RESULTS / "timing.json"
SPEND = RESULTS / "spend.json"


def add_deviation(dev_id: str, what: str, why: str, cost: str) -> None:
    with _LOCK:
        d = read_json(DEVIATIONS, {"deviations": []})
        d["deviations"] = [x for x in d["deviations"] if x["id"] != dev_id]
        d["deviations"].append({"id": dev_id, "what": what, "why": why, "cost": cost, "logged_utc": utc_now()})
        d["deviations"].sort(key=lambda x: x["id"])
        write_json(DEVIATIONS, d)


def log_timing(stage: str, seconds: float, gpu: bool, **extra: Any) -> None:
    with _LOCK:
        t = read_json(TIMING, {"stages": {}})
        rec = t["stages"].get(stage, {"runs": []})
        rec["runs"].append({"seconds": round(seconds, 1), "gpu": gpu, "utc": utc_now(), **extra})
        rec["total_seconds"] = round(sum(r["seconds"] for r in rec["runs"]), 1)
        t["stages"][stage] = rec
        t["gpu_hours_total"] = round(sum(sum(r["seconds"] for r in v["runs"] if r["gpu"])
                                         for v in t["stages"].values()) / 3600.0, 3)
        write_json(TIMING, t)


def spend_state() -> dict[str, Any]:
    return read_json(SPEND, {"cap_usd": OPENROUTER_CAP_USD, "total_usd": 0.0, "by_purpose": {}, "n_calls": 0,
                             "budget_refusals": 0})


def add_spend(purpose: str, usd: float, refused: bool = False) -> float:
    with _LOCK:
        s = spend_state()
        s["total_usd"] = round(s["total_usd"] + usd, 6)
        s["by_purpose"][purpose] = round(s["by_purpose"].get(purpose, 0.0) + usd, 6)
        s["n_calls"] += 1
        s["budget_refusals"] += int(refused)
        s["updated_utc"] = utc_now()
        write_json(SPEND, s)
        return s["total_usd"]


class Timer:
    def __init__(self, stage: str, gpu: bool, **extra: Any):
        self.stage, self.gpu, self.extra = stage, gpu, extra

    def __enter__(self) -> "Timer":
        self.t0 = time.time()
        logger.info(f"[{self.stage}] start")
        return self

    def __exit__(self, *exc: Any) -> None:
        dt = time.time() - self.t0
        log_timing(self.stage, dt, self.gpu, ok=exc[0] is None, **self.extra)
        logger.info(f"[{self.stage}] done in {dt / 60:.1f} min")
