#!/usr/bin/env python3
"""Paths, constants and small utilities for iteration 7, direction 3 ("does one early token decide the algorithm?").

Vendored code (read-only copies, see vendor/SHA256SUMS):
  vendor/exp29/src            iteration-6 exp29 (engine factorial): engines.load_b (bf16 weight set, CPU embedding),
                              escape.py (exp22 two-stage escape rule), label_worker6 (frozen labeller + T2 re-gate)
  vendor/exp29/vendor/exp22   iteration-4 exp22: ctx4 (rand_dir, ban_unit, push_spec, TaskCtx), engine4 (exact
                              inverse-CDF CRN sampler with fence stop), src_base/engine.py (prefill, block hooks),
                              inputs/ (exp8 suite, exp11 bench, exp13/exp17 units, prompts4)
  vendor/exp30/src            iteration-6 exp30 (Stage A): pad_record logic, prompts6 (top5ban/ban/twin prompts)
  vendor/exp31/fork.py        iteration-6 exp31: change_points, best_segmentation, lcp, canonical_prefix
  vendor/exp9                 iteration-2 exp9: labeller_ext (10-algorithm grid labeller), frozen_prompts.json
This module only puts the vendored directories on sys.path (appended, so this artifact's modules win a name lookup);
nothing under vendor/ is edited.
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
SRC = ROOT / "src"
V29 = ROOT / "vendor" / "exp29"
V22 = V29 / "vendor" / "exp22"
V28 = V29 / "vendor" / "exp28"
V30 = ROOT / "vendor" / "exp30"
V31 = ROOT / "vendor" / "exp31"
V9 = ROOT / "vendor" / "exp9"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
for _p in (V29 / "src", V22 / "src_base", V22 / "src", V28 / "src", V31):
    if str(_p) not in sys.path:
        sys.path.append(str(_p))

INPUTS = ROOT / "inputs"
IN29 = INPUTS / "exp29"
IN30 = INPUTS / "exp30"
IN20 = INPUTS / "exp20"
DATA = ROOT / "data"
RESULTS = ROOT / "results"
FIGS = ROOT / "figures"
PRED = ROOT / "predictions"
LOGS = ROOT / "logs"
CACHE = ROOT / "cache"
STATES = CACHE / "states"
AUDIT = ROOT / "audit"
for _d in (DATA, RESULTS, FIGS, PRED, LOGS, CACHE, STATES, AUDIT):
    _d.mkdir(parents=True, exist_ok=True)

RAW = DATA / "samples_raw.jsonl"          # every new generated program (one row per CRN slot and arm)
LABELS = DATA / "labels.jsonl"            # frozen-labeller rows keyed like RAW
FORK_ROWS = DATA / "fork_continuations.jsonl"
COMMIT_LOG = ROOT / "commitments.log"
GENESIS = hashlib.sha256(b"iter7_dir3").hexdigest()

MODEL_ID = "Qwen/Qwen3-8B"
MODEL_REVISION = "b968826d9c46dd6066d109eabc6255188de91218"
TEMPLATES = ["W1", "W2", "W3", "W4", "W5"]
TASKS_P = ("T10", "T2")                   # primary F / P2 tasks
TASK_CONF = "T03"                          # prospective confirmation task
TASKS_ALL = ("T10", "T2", "T03")
DEFAULTS = {"T10": "union_find", "T2": "dijkstra", "T03": "full_sort", "T1": "bfs"}
RUNNER_UP = {"T10": "dfs", "T2": "bf_spfa", "T03": "quickselect", "T1": "dfs"}
CATALOGUE = {"T10": ["union_find", "bfs", "dfs", "label_propagation"],
             "T2": ["dijkstra", "bf_spfa", "bidijkstra", "floyd", "dial"],
             "T03": ["full_sort", "size_k_heap", "heapify_pop", "quickselect", "median_of_medians",
                     "counting_sort"]}
FENCE = {"T10": "bench", "T03": "bench", "T2": "path", "T1": "path"}
MAX_NEW = {"T10": 1024, "T03": 1024, "T2": 1536, "T1": 1536}
SEEDS40 = list(range(9101, 9141))
SEEDS_STAGE0 = list(range(9101, 9106))
SEEDS_T03 = list(range(97001, 97025))
SEED_RAND_TARGET = {"T10": 98001, "T2": 98002, "T03": 98003, "T1": 98004}
ALPHA = 2.0
EDIT_BLOCKS = list(range(12, 24))
CAP_BLOCKS = list(range(12, 36))
D_MODEL = 4096
BUDGET_MSG = "AI Inventor per-run OpenRouter budget"
OPENROUTER_CAP_USD = 0.5


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
    """exp8/exp17/exp19/exp29 convention: sha256 of the '|'-joined str() of the parts, mod 2^63."""
    return int(hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest(), 16) % (2 ** 63)


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


def write_json(p: Path, obj: Any) -> None:
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1, default=_json_default))
    tmp.replace(p)


def read_json(p: Path) -> Any:
    return json.loads(Path(p).read_text())


def setup_logging(name: str) -> None:
    from loguru import logger

    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    logger.add(str(LOGS / f"{name}.log"), rotation="30 MB", level="DEBUG")


def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, c - h), min(1.0, c + h))


def deviation(code: str, text: str, **kw: Any) -> None:
    append_jsonl(RESULTS / "deviations.jsonl", [{"code": code, "text": text, "utc": utc_now(), **kw}])


# ------------------------------------------------------------------------------------------------ hash chain
def chain_head() -> str:
    if not COMMIT_LOG.exists():
        return GENESIS
    lines = [l for l in COMMIT_LOG.read_text().splitlines() if l.strip()]
    return lines[-1].split("\t")[2] if lines else GENESIS


def commit(name: str, path: Path) -> str:
    """Append <utc> <name> <chain hash> <file sha256> to commitments.log; chain = sha256(prev_chain + file_sha)."""
    fsha = sha256_file(path)
    prev = chain_head()
    ch = hashlib.sha256((prev + fsha).encode()).hexdigest()
    with open(COMMIT_LOG, "a") as f:
        f.write(f"{utc_now()}\t{name}\t{ch}\t{fsha}\t{path.relative_to(ROOT)}\n")
    return ch


def verify_chain() -> dict[str, Any]:
    prev = GENESIS
    rows = []
    ok = True
    for line in COMMIT_LOG.read_text().splitlines() if COMMIT_LOG.exists() else []:
        if not line.strip():
            continue
        utc, name, ch, fsha, rel = line.split("\t")
        cur = sha256_file(ROOT / rel) if (ROOT / rel).exists() else None
        good = cur == fsha and hashlib.sha256((prev + fsha).encode()).hexdigest() == ch
        ok &= good
        rows.append({"utc": utc, "name": name, "file": rel, "file_sha_ok": cur == fsha, "chain_ok": good})
        prev = ch
    return {"ok": ok, "entries": rows}


# ------------------------------------------------------------------------------------------------ blindness guard
COMMIT3 = PRED / "commit3_predictors.json"


class BlindnessError(RuntimeError):
    pass


def latest(*names: str) -> Path:
    """Latest existing commit file among names (amendments listed first)."""
    for n in names:
        if (PRED / n).exists():
            return PRED / n
    return PRED / names[-1]


def c3_path() -> Path:
    return latest("commit3b_predictors.json", "commit3_predictors.json")


def forks_path() -> Path:
    return latest("commit1c_forks.json", "commit1b_forks.json", "commit1_forks.json")


def pop_rows_released() -> bool:
    return COMMIT3.exists()


def is_pop_arm(arm: str | None) -> bool:
    return bool(arm) and str(arm).startswith("POP_")


def guarded_e29_rows(path: Path, allow_pop: bool = False) -> list[dict[str, Any]]:
    """Read an exp29 row file. POP_* outcome rows (label, passed, code, text) are refused until commit #3 exists:
    before that, asking for them raises, and the default call silently skips them without parsing their content."""
    if allow_pop and not pop_rows_released():
        raise BlindnessError("exp29 POP_* outcome rows are sealed until predictions/commit3_predictors.json exists")
    out = []
    with open(path) as f:
        for line in f:
            if not line.strip():
                continue
            if not allow_pop and '"arm": "POP_' in line[:400]:
                continue          # skipped before json parsing: the content is never read
            r = json.loads(line)
            if is_pop_arm(r.get("arm")) and not allow_pop:
                continue
            out.append(r)
    return out


class Timer:
    def __init__(self) -> None:
        self.t0 = time.time()

    def __call__(self) -> float:
        return time.time() - self.t0
