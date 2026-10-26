"""Shared constants, paths, logging, hashing and IO helpers for the exposure-ban experiment.

Every path is derived from the workspace root (the directory holding method.py).  The exp11 bench is read once,
by `method.py setup`, from EXP11_DIR (default: the sibling iteration-2 artifact, located relative to this
workspace) and copied into ./bench_copy/; nothing is ever written outside the workspace.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import threading
import time
from pathlib import Path

from loguru import logger

ROOT = Path(__file__).resolve().parent.parent
EXP11 = Path(os.environ.get("EXP11_DIR") or (ROOT.parents[2] / "round-2" / "." / "experiment-11/src"))
BENCH = ROOT / "bench_copy"
DATA = ROOT / "data"
PRED = ROOT / "predictions"
RESULTS = ROOT / "results"
FIGS = ROOT / "figures"
LOGS = ROOT / "logs"
COMMIT_LOG = ROOT / "commitments.log"

MODEL_ID = "Qwen/Qwen3-8B"
MODEL_REV = "b968826d9c46dd6066d109eabc6255188de91218"  # the main revision on 2026-10-20; exp8 used b968826d
DTYPE = "bfloat16"
BASE_SEED = 20261020
SHUFFLE_SEED = 20261020  # committed seed of the shown-program shuffle and the proximity reference selection

# Stage-A order of the 12 frozen tasks (exp11 commitments.log, stageA_order minus the excluded R2)
TASK_ORDER = ["T03", "T04", "T06", "T05", "T10", "R1", "T08", "R3", "T13", "R6", "T14", "T11"]

N_PER_ARM = 50
MAX_SHOWN = 5
MAX_SHOWN_TOKENS = 600
NGRAM_MAX = 6
PRESENCE_MIN = 0.8
COVETO_SHARE = 0.5
REEMERGE_MIN = 0.20
MAX_ROUNDS = 3
MIN_NONY_SUBTRACT = 20
N_BASELINE_CHECK = 20
MAX_MODEL_LEN = 2048
MAX_NEW_TOKENS = 1024
JUDGE_SOFT_CAP = 0.50  # stop new judge calls (USD); the hard cap of the plan is 0.60

NL = "\n"
INTRO = "Here is a correct solution to this task:"
WORDINGS = {
    "copy": "Write a correct solution.",
    "named": "Write a correct solution that does not use {x}.",  # = frozen template W5
    "unnamed": "Write a correct solution that uses a different algorithm from the one above.",
}
# Frozen ban templates W1-W4 of the shared protocol (round-2 prompts_v2.json); W5 is the NAMED wording above.
TEMPLATES_W1_W4 = {
    "W1": "Do not use {x} for this task.",
    "W2": "Your solution must not rely on {x}.",
    "W3": "Avoid {x} entirely.",
    "W4": "{x} is not allowed here.",
}


def setup_logging(name: str) -> None:
    LOGS.mkdir(parents=True, exist_ok=True)
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    logger.add(LOGS / f"{name}.log", rotation="30 MB", level="DEBUG")


def ensure_bench_importable() -> None:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with Path(p).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def canon_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def seed_of(key: str) -> int:
    """Seed shared by every arm of one (task, Y, shown program, sample index): common random numbers."""
    return int(sha256_text(key)[:8], 16)


def read_jsonl(p: Path) -> list[dict]:
    if not Path(p).exists():
        return []
    out = []
    with Path(p).open() as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


_write_lock = threading.Lock()


def append_jsonl(p: Path, rows: list[dict]) -> None:
    with _write_lock, Path(p).open("a") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
        f.flush()


def write_json(p: Path, obj, indent: int = 1) -> None:
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(obj, indent=indent, default=_json_default))


def _json_default(o):
    if hasattr(o, "item"):
        return o.item()
    if isinstance(o, (set, tuple)):
        return list(o)
    raise TypeError(f"not JSON serialisable: {type(o)}")


def read_json(p: Path):
    return json.loads(Path(p).read_text())


def task_dir(task: str) -> Path:
    for d in BENCH.iterdir():
        if d.is_dir() and d.name.split("_")[0] == task:
            return d
    raise FileNotFoundError(f"no bench dir for {task}")


def load_spec(task: str) -> dict:
    return read_json(task_dir(task) / "spec.json")


def fenced(code: str) -> str:
    """The exact fenced text used for n-gram tokenisation and for the shown-program prompt block."""
    return "```python" + NL + code.rstrip() + NL + "```"


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


class Timer:
    """Accumulates wall and GPU seconds per stage into results/timings.json."""

    path = RESULTS / "timings.json"

    def __init__(self, stage: str, gpu: bool = False):
        self.stage, self.gpu = stage, gpu

    def __enter__(self):
        self.t0 = time.time()
        return self

    def __exit__(self, *exc):
        dt = time.time() - self.t0
        RESULTS.mkdir(exist_ok=True)
        tm = read_json(self.path) if self.path.exists() else {}
        e = tm.setdefault(self.stage, {"wall_s": 0.0, "gpu_s": 0.0, "runs": 0})
        e["wall_s"] += dt
        e["gpu_s"] += dt if self.gpu else 0.0
        e["runs"] += 1
        e["last_end_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        write_json(self.path, tm)
        logger.info(f"[timing] {self.stage}: {dt:.1f}s ({'GPU' if self.gpu else 'CPU'})")
        return False


def load_tokenizer():
    from transformers import AutoTokenizer
    return AutoTokenizer.from_pretrained(MODEL_ID, revision=MODEL_REV)


def deviation(text: str) -> None:
    """Record a declared deviation from the plan (results/deviations.jsonl), deduplicated by text."""
    p = RESULTS / "deviations.jsonl"
    RESULTS.mkdir(exist_ok=True)
    have = {r["text"] for r in read_jsonl(p)}
    if text not in have:
        append_jsonl(p, [{"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "text": text}])
        logger.warning(f"DEVIATION: {text}")
