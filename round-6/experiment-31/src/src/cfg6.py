#!/usr/bin/env python3
"""Constants, seed rules, paths and small utilities for the iteration-6 panel-I artifact (protocol v6, Step 3).

Conventions (inherited from iteration 5, exp26 src/cfg5.py, restated so the artifact stands alone):
- BLOCK l = decoder block l (0-based); its output is HF hidden_states[l + 1].
- S = [p1, spec_end): first token of the task specification to the last user token (chat tail excluded); R = P - 1.
- CRN slot = (unit, template, k): uniforms u_stream(unit, template, k) shared by every arm of the HF engine.
- EDIT_BLOCKS 12-23 are pushed at S during the prompt prefill only (ESC, PN); GTN edits generated tokens 1..32.
- Every row: precision W16A16 (bf16), thinking off, both models read the identical (instruct-tokenizer) token ids.
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
RESULTS_DIR = ROOT / "results"
PRED_DIR = ROOT / "predictions"
UNITS_DIR = ROOT / "units"
CACHE_DIR = ROOT / "cache"
FIG_DIR = ROOT / "figures"
LOG_DIR = ROOT / "logs"
ANALYSIS_DIR = ROOT / "analysis"
AUDIT_DIR = ROOT / "audit"
DIR_DIR = ROOT / "directions"
for _d in (DATA_DIR, RESULTS_DIR, PRED_DIR, UNITS_DIR, CACHE_DIR, FIG_DIR, LOG_DIR, ANALYSIS_DIR, AUDIT_DIR, DIR_DIR,
           PRED_DIR / "units", INPUTS):
    _d.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------------------------------------------ models
MODEL_ID = "Qwen/Qwen3-8B"
MODEL_REVISION = "b968826d9c46dd6066d109eabc6255188de91218"
BASE_ID = "Qwen/Qwen3-8B-Base"
BASE_REVISION = "49e3418fbbbca6ecbdf9608b4d22e5a407081db4"
N_LAYERS = 36
D_MODEL = 4096
IM_END = 151645
ENDOFTEXT = 151643
IM_START = 151644
MAX_NEW = 1024
MAX_NEW_ASSOC = 64
MAX_NEW_INTENT = 48
TEMPLATE_TAIL = "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"
PRECISION = "W16A16_bf16"

# ------------------------------------------------------------------------------------------------ prompts
TEMPLATES: dict[str, str] = {  # neutral-noun twins W1-W5 (protocol v2, verbatim)
    "W1": "Do not use {N} for this task.",
    "W2": "Your solution must not rely on {N}.",
    "W3": "Avoid {N} entirely.",
    "W4": "{N} is not allowed here.",
    "W5": "Write a correct solution that does not use {N}.",
}
TEMPLATE_IDS = list(TEMPLATES)
PAD_FILLER = " ."
FORMAT_LINE = ("Use only the Python standard library. Return only one ```python code block containing the function "
               "solve and any helpers, with no example usage and no explanation.")
ASSOCIATION_TEMPLATE = ("What is the standard alternative to {x} for this task? "
                        "Name one algorithm and answer in one sentence.")
FORCED_WORDINGS = {  # 5 wordings of the forced 'Implement X' sentence (plan S1b)
    "F1": "Implement this using {dn} ({mech}).",
    "F2": "Solve this task with {dn} ({mech}).",
    "F3": "Your solution must be based on {dn} ({mech}).",
    "F4": "Use {dn} to solve this task ({mech}).",
    "F5": "Write the solution around {dn} ({mech}).",
}
INTENT_SUFFIX = " Before coding, state in one sentence the approach you will use."
INTENT_PREFIX = "Approach:"
BINT_SUFFIX = " Planned approach: {intent}"
PROHIBITION_CUES = ("do not", "don't", "not allowed", "avoid", "without using", "never use", "must not")

# ------------------------------------------------------------------------------------------------ design
EDIT_BLOCKS = list(range(12, 24))
CAP_BLOCKS = list(range(12, 36))
R_Q = {12: 0.06980, 13: 0.07784, 14: 0.08328, 15: 0.09221, 16: 0.09640, 17: 0.10403, 18: 0.11347, 19: 0.11531,
       20: 0.12005, 21: 0.12332, 22: 0.11886, 23: 0.11459}
ALPHAS_ESC = (1.0, 2.0, 4.0)
ALPHAS_PN = (2.0, 4.0)
ALPHA_GTN = 2.0
GTN_STEPS = 32
N_DIRS = 8
ESC_EXCESS = 0.20
ESC_PASS_FRAC = 0.8
DEFAULT_SHARE = 0.6
LANDING_MIN = 5
LANDING_LEAD = 0.15
SLOTS = {"hf_twin": list(range(10)), "esc1": [0, 1], "conf": [2, 3, 4, 5], "pn": list(range(10)),
         "gtn": list(range(10)), "bint": list(range(6)), "vllm_t10": list(range(10, 40)),
         "vllm_t13": list(range(10, 30)), "base_chat": list(range(40)), "plain": list(range(100)),
         "intent": list(range(6)), "pilot": list(range(6)), "gold_instruct": [10, 11]}
N_FORCED_SEEDS = 5
N_ASSOC = 20
N_FORCED_KEEP = 10
QLIK_TOKENS = 48
BUDGET_MSG = "AI Inventor per-run OpenRouter budget"
OPENROUTER_CAP_USD = 2.00
OPENROUTER_SOFT_STOP = 1.80
EXCLUDE = ("invalid", "disputed")

RAW = DATA_DIR / "raw_vllm.jsonl"
RAW_HF = DATA_DIR / "raw_hf.jsonl"
LABELS = DATA_DIR / "labels.jsonl"
REALISED = DATA_DIR / "realised_disp.jsonl"
TIMING = RESULTS_DIR / "timing.jsonl"
COMMIT_LOG = ROOT / "commitments.log"
PROMPTS = DATA_DIR / "prompts.jsonl"
COSTS = RESULTS_DIR / "costs.jsonl"
DEVIATIONS = RESULTS_DIR / "deviations.jsonl"
GENESIS = hashlib.sha256(b"iter6|panelI").hexdigest()

FORBIDDEN_SEEDS = set(range(9001, 9041)) | set(range(52001, 52017))


# ------------------------------------------------------------------------------------------------ seeds
def _h(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def alpha_tag(alpha: float) -> str:
    return str(int(alpha)) if float(alpha).is_integer() else str(alpha)


def direction_seed(unit: str, k: int) -> int:
    """Fixed-direction seed(unit, k) = int(sha256('iter6|panelI|'+unit+'|dir|'+k)[:8], 16), k = 0..7."""
    return int(_h(f"iter6|panelI|{unit}|dir|{k}")[:8], 16)


def pn_seed(unit: str, alpha: float, w: str, k: int) -> int:
    return int(_h(f"iter6|panelI|{unit}|PN|a{alpha_tag(alpha)}|{w}|{k}")[:8], 16)


def gtn_seed(unit: str, alpha: float, w: str, k: int) -> int:
    return int(_h(f"iter6|panelI|{unit}|GTN|a{alpha_tag(alpha)}|{w}|{k}")[:8], 16)


def crn_seed(unit: str, w: str, k: int) -> int:
    """CRN: u_stream(unit, w, k) = PCG64(int(sha256('iter6|panelI|'+unit+'|'+w+'|'+k)[:16], 16))."""
    return int(_h(f"iter6|panelI|{unit}|{w}|{k}")[:16], 16)


def vllm_seed(unit: str, w: str, k: int) -> int:
    return int(_h(f"iter6|panelI|vllm|{unit}|{w}|{k}")[:8], 16)


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


def detect_cpus() -> int:
    try:
        parts = Path("/sys/fs/cgroup/cpu.max").read_text().split()
        if parts[0] != "max":
            return max(1, math.ceil(int(parts[0]) / int(parts[1])))
    except (FileNotFoundError, ValueError, IndexError):
        pass
    try:
        return len(os.sched_getaffinity(0))
    except (AttributeError, OSError):
        return os.cpu_count() or 1


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def sha256_text(s: str) -> str:
    return _h(s)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


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
