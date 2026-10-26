#!/usr/bin/env python3
"""Constants, paths and small utilities for the iteration-5 panel-B artifact.

Conventions (inherited from exp17/exp22, restated in README.md):
- BLOCK l = decoder block l (0-based); its output is HF hidden_states[l + 1].
- S = [p1, spec_end): first token of the task specification to the last user token (chat tail excluded); R = P - 1.
- CRN slot = (unit, template, k): uniforms u_stream(unit, template, k), identical in every arm and in both models;
  every batch has exactly B = 20 rows of ONE (unit, prompt), prune=False, so batch shapes match across arms.
- EDIT_BLOCKS 12-23 are pushed at S during the prompt prefill only; realised displacements are logged at 12-35.
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

from loguru import logger

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
VENDOR = ROOT / "vendor"
INPUTS = ROOT / "inputs"
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
RESULTS_DIR = ROOT / "results"
PRED_DIR = ROOT / "predictions"
UNITS_DIR = ROOT / "units"
CACHE_DIR = ROOT / "cache"
FIG_DIR = ROOT / "figures"
LOG_DIR = ROOT / "logs"
ANALYSIS_DIR = ROOT / "analysis"
AUDIT_DIR = ROOT / "audit"
DIR_DIR = ROOT / "directions"
for _d in (DATA_DIR, RAW_DIR, RESULTS_DIR, PRED_DIR, UNITS_DIR, CACHE_DIR, FIG_DIR, LOG_DIR, ANALYSIS_DIR, AUDIT_DIR,
           DIR_DIR, PRED_DIR / "units"):
    _d.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------------------------------------------ models
MODEL_ID = "Qwen/Qwen3-8B"
MODEL_REVISION = "b968826d9c46dd6066d109eabc6255188de91218"
BASE_ID = "Qwen/Qwen3-8B-Base"
BASE_REVISION = "49e3418fbbbca6ecbdf9608b4d22e5a407081db4"   # newest snapshot on 2026-10-21 (pinned here, logged)
N_LAYERS = 36
D_MODEL = 4096
IM_END = 151645
ENDOFTEXT = 151643
IM_START = 151644
MAX_NEW = 1024
MAX_NEW_PATH = 1536
MAX_NEW_ASSOC = 64
TEMPLATE_TAIL = "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"
PRECISION = "bf16_hf"   # precision rule: cc >= 8.9 and VRAM < 19.5 GiB -> FP8 W8A8; else bf16 (RTX 4090, 24 GiB)
DECODING_STR = "T1.0_topp1.0_topk-off_max1024_thinkoff_fencestop"

# ------------------------------------------------------------------------------------------------ prompts
TEMPLATES: dict[str, tuple[str, str]] = {  # (ban, neutral) -- protocol v2 W1-W5, verbatim (exp17/exp22)
    "W1": ("Do not use {X} for this task.", "Do not use {N} for this task."),
    "W2": ("Your solution must not rely on {X}.", "Your solution must not rely on {N}."),
    "W3": ("Avoid {X} entirely.", "Avoid {N} entirely."),
    "W4": ("{X} is not allowed here.", "{N} is not allowed here."),
    "W5": ("Write a correct solution that does not use {X}.", "Write a correct solution that does not use {N}."),
}
TEMPLATE_IDS = list(TEMPLATES)
PAD_FILLER = " ."
NOVELTY_SEGMENT = "Write a novel algorithm for this task, one you have not seen before."
ASSOCIATION_TEMPLATE = ("What is the standard alternative to {x} for this task? "
                        "Name one algorithm and answer in one sentence.")
FORMAT_LINE = ("Use only the Python standard library. Return only one ```python code block containing the function "
               "solve and any helpers, with no example usage and no explanation.")
PROHIBITION_CUES = ("do not", "don't", "not allowed", "avoid", "without using", "never use", "must not")

# ------------------------------------------------------------------------------------------------ design
EDIT_BLOCKS = list(range(12, 24))
CAP_BLOCKS = list(range(12, 36))
B = 20
ALPHAS = (1.0, 2.0)
N_DIRS = 8
ESC_EXCESS = 0.20
ESC_PASS_FRAC = 0.8
DEFAULT_SHARE = 0.6
K = {"twin": list(range(10)), "esc1": [0, 1], "conf": [2, 3, 4, 5], "base": list(range(20)), "pilot": list(range(6)),
     "pn": list(range(10)), "t13": list(range(10)), "gate": [100, 101], "parent_base": list(range(10))}
N_NOVELTY = 30
N_ASSOC = 20
N_PLAIN = 50
BUDGET_MSG = "AI Inventor per-run OpenRouter budget"
OPENROUTER_CAP_USD = 2.00
OPENROUTER_SOFT_STOP = 1.80
EXCLUDE = ("invalid", "disputed")

RAW = DATA_DIR / "samples_raw.jsonl"
LABELS = DATA_DIR / "labels.jsonl"
REALISED = DATA_DIR / "realised_disp.jsonl"
TIMING = RESULTS_DIR / "timing.jsonl"
COMMIT_LOG = ROOT / "commitments.log"
PROMPTS = DATA_DIR / "prompts.jsonl"
COSTS = RESULTS_DIR / "costs.jsonl"
DEVIATIONS = RESULTS_DIR / "deviations.jsonl"


def model_path(model_id: str, revision: str | None) -> str:
    cache = os.environ.get("HF_HUB_CACHE")
    if cache:
        snaps = Path(cache) / ("models--" + model_id.replace("/", "--")) / "snapshots"
        if revision and (snaps / revision).exists():
            return str(snaps / revision)
    return model_id


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


def container_ram_gb() -> float | None:
    for p in ("/sys/fs/cgroup/memory.max", "/sys/fs/cgroup/memory/memory.limit_in_bytes"):
        try:
            v = Path(p).read_text().strip()
            if v != "max" and int(v) < 1_000_000_000_000:
                return int(v) / 1e9
        except (FileNotFoundError, ValueError):
            pass
    return None


def detect_cpus() -> int:
    try:
        q = int(Path("/sys/fs/cgroup/cpu/cpu.cfs_quota_us").read_text())
        p = int(Path("/sys/fs/cgroup/cpu/cpu.cfs_period_us").read_text())
        if q > 0:
            return max(1, math.floor(q / p))
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
    """Deterministic 63-bit seed from arbitrary parts (sha256 of their '|'-joined repr) -- exp8 convention."""
    return int(hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest(), 16) % (2 ** 63)


def direction_seed(unit: str, k: int) -> int:
    """Plan section 2: seed(unit, k) = int(sha256('iter5|panelB|{unit}|dir|{k}')[:8], 16). Variants V_<t> and their
    paired parent re-measures P_<t> use the PARENT's seeds (keyed on <t>)."""
    if unit[:2] in ("P_", "V_"):
        unit = unit[2:]
    return int(hashlib.sha256(f"iter5|panelB|{unit}|dir|{k}".encode()).hexdigest()[:8], 16)


def pn_seed(unit: str, arm: str, template: str, slot: int) -> int:
    return int(hashlib.sha256(f"iter5|panelB|{unit}|pn|{arm}|{template}|{slot}".encode()).hexdigest()[:8], 16)


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
    if isinstance(o, Path):
        return str(o)
    if isinstance(o, (set, frozenset)):
        return sorted(o)
    raise TypeError(f"not JSON serialisable: {type(o)}")


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


def _finite(o: Any) -> Any:
    if isinstance(o, float):
        return o if math.isfinite(o) else None
    if isinstance(o, dict):
        return {str(k): _finite(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_finite(v) for v in o]
    return o


def write_json(p: Path, obj: Any, indent: int | None = 1) -> None:
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(_finite(json.loads(json.dumps(obj, default=_json_default))), indent=indent))
    tmp.replace(p)


def read_json(p: Path) -> Any:
    return json.loads(Path(p).read_text())


def wilson_ci(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, c - h), min(1.0, c + h))


def cap_first(s: str) -> str:
    return s[:1].upper() + s[1:] if s else s


def rel(p: Path | str) -> str:
    """Path relative to the artifact root (never write absolute server paths into published files)."""
    try:
        return str(Path(p).resolve().relative_to(ROOT))
    except ValueError:
        return str(p)


def log_deviation(key: str, text: str, **meta: Any) -> None:
    rows = read_jsonl(DEVIATIONS)
    if any(r.get("key") == key for r in rows):
        return
    append_jsonl(DEVIATIONS, [{"key": key, "text": text, "utc": utc_now(), **meta}])
