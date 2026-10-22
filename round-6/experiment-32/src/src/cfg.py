#!/usr/bin/env python3
"""Shared constants, paths and utilities for the iteration-6 artifact 'Reading the planned algorithm in words'.

Conventions (stated again in README.md):
- BLOCK l = decoder block l (0-based); its output is HF hidden_states[l + 1]. The NLA checkpoint was trained on the
  output of block 20 (= hidden_states[21]); the README snippet reads hidden_states[20]. Both are cached and the
  pre-registered convention check in S6 picks one (cfg.LAYER_CONVENTIONS).
- Positions are counted from the END of the prompt: READ = P-1 (the '\\n' after 'assistant'); SPEC-1..SPEC-3 = the
  three user-content tokens just before the user turn's '<|im_end|>' (P-6, P-7, P-8 under the Qwen2.5 tail).
- CRN slot = (task, template w, k); uniforms u_stream(task, w, k) (PCG64 of a sha256 seed) are shared by EVERY arm.
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
INPUTS = ROOT / "inputs"
E8 = INPUTS / "exp8"
E11 = INPUTS / "exp11"
E7 = INPUTS / "exp7"
E27 = INPUTS / "exp27"
E28 = INPUTS / "exp28"
E6 = INPUTS / "exp6"
E18 = INPUTS / "exp18"
BENCH = E11 / "bench"
SUITE = E8 / "suite"
DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "results"
FIG_DIR = ROOT / "figures"
LOG_DIR = ROOT / "logs"
PRED_DIR = ROOT / "predictions"
AUDIT_DIR = ROOT / "audit"
CACHE_DIR = ROOT / "cache"
for _d in (DATA_DIR, RESULTS_DIR, FIG_DIR, LOG_DIR, PRED_DIR, AUDIT_DIR, CACHE_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# the declared dataset dependency art_j3Rm_lr2nzR6 (read-only). The published repository holds it as a sibling folder
# of this artifact; the environment variable ART_J3RM_DIR points elsewhere (e.g. the run volume where it was produced).
DEP_DATASET_DIR = Path(os.environ.get("ART_J3RM_DIR", str(ROOT.parent / "art_j3Rm_lr2nzR6")))

# ------------------------------------------------------------------------------------------------ models
MODEL_ID = "Qwen/Qwen2.5-7B-Instruct"
MODEL_REVISION = "a09a35458c702b33eeacc393d103063234e8bc28"
AV_ID = "kitft/nla-qwen2.5-7b-L20-av"
AV_REVISION = "b88469162777ae6553bc14208eb0cb579336f8f4"
AR_ID = "kitft/nla-qwen2.5-7b-L20-ar"
AR_REVISION = "e2c9e57eac213d37a31612087f645ab6332c1bb6"
N_LAYERS = 28
D_MODEL = 3584
IM_END = 151645
ENDOFTEXT = 151643
EOS_IDS = (IM_END, ENDOFTEXT)
MAX_NEW_TOKENS = 1024
MAX_NEW_PATH = 1536
TEMPLATE_TAIL = "<|im_end|>\n<|im_start|>assistant\n"
ENGINE_TAG = "bf16-hf"
PRECISION = "bf16"
LAYER_CONVENTIONS = {"hs20": 20, "hs21": 21}  # hidden_states index -> hooked block = index - 1
EXTRACTION_LAYER = 20

# ------------------------------------------------------------------------------------------------ tasks
PATH_TASKS = ("T1", "T2")
BENCH_TASKS = ("T03", "T05", "T06", "T10", "T04", "R6")
TASKS = ("T1", "T2", "T03", "T05", "T06", "T10", "T04", "R6")
EXP8_TASK = {"T1": "t1", "T2": "t2"}
# the earlier family's (Qwen3-8B) defaults; used only to pick the twin's neutral noun before this model's default
# is known (protocol: the twin is token-length matched to the ban of the prior default)
PRIOR_DEFAULT = {"T1": "bfs", "T2": "dijkstra", "T03": "full_sort", "T04": "naive", "T06": "hash_set",
                 "T05": "hash_map", "T10": "union_find", "R6": "binary_search"}
TEMPLATES: dict[str, tuple[str, str]] = {  # (ban, neutral) -- protocol v2 W1-W5, verbatim
    "W1": ("Do not use {X} for this task.", "Do not use {N} for this task."),
    "W2": ("Your solution must not rely on {X}.", "Your solution must not rely on {N}."),
    "W3": ("Avoid {X} entirely.", "Avoid {N} entirely."),
    "W4": ("{X} is not allowed here.", "{N} is not allowed here."),
    "W5": ("Write a correct solution that does not use {X}.", "Write a correct solution that does not use {N}."),
}
TEMPLATE_IDS = list(TEMPLATES)
PAD_FILLER = " ."
N_FORCED_PARAPHRASES = 5

# ------------------------------------------------------------------------------------------------ design
TWIN_SLOTS = list(range(10))          # k 0-9 per template -> N = 50
EXTRA_TWIN_SLOTS = list(range(10, 20))  # NO-DEFAULT tasks: the ban's 50 samples go to twin slots 10-19
FORCED_SLOTS = list(range(4))         # 5 paraphrases x 4 slots = 20 per catalogue Y
CAUSAL_SLOTS = list(range(6))         # W1-W5 x slots 0-5 = 30 per cell
GEN_POSITIONS = (1, 2, 4, 8, 16)      # generated-token read positions g1..g16 (1-based generated index)
PREFILL_POS = ("SPEC-3", "SPEC-2", "SPEC-1", "READ")
POS_OFFSET = {"READ": 1, "SPEC-1": 6, "SPEC-2": 7, "SPEC-3": 8}  # index = P - offset
DOSES = (1.0, 2.0, 4.0)
GEN_STEPS = 64                        # GEN site: READ's delta added at READ and generated positions 1-64
DEFAULT_SHARE = 0.6
YSTAR_SHARE = 0.5
YSTAR_MIN = 10
MIXED_SHARE = 0.2
ADHERENT_MIN = 0.7
FVE_PASS = 0.60
FVE_PARTIAL = 0.50
FVE_REF_TARGET = 0.752
FVE_TRAIN_DENOM = 0.7335              # Var(v_nrm) of the training mix (examples/qwen7b_layer20_step4200.txt)
JUDGE_CAP_USD = 2.2
CODE_JUDGE_CAP_USD = 0.6
BUDGET_MSG = "AI Inventor per-run OpenRouter budget"
BOOT_SEED = 20261022
N_BOOT = 2000
DEPTH = 25
GENESIS = hashlib.sha256(b"iter6_dir6").hexdigest()


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
        q = int(Path("/sys/fs/cgroup/cpu/cpu.cfs_quota_us").read_text())
        p = int(Path("/sys/fs/cgroup/cpu/cpu.cfs_period_us").read_text())
        if q > 0:
            return max(1, math.ceil(q / p))
    except (FileNotFoundError, ValueError):
        pass
    try:
        return len(os.sched_getaffinity(0))
    except (AttributeError, OSError):
        return os.cpu_count() or 1


def model_path(model_id: str = MODEL_ID, revision: str | None = MODEL_REVISION) -> str:
    cache = os.environ.get("HF_HUB_CACHE")
    if cache:
        snaps = Path(cache) / ("models--" + model_id.replace("/", "--")) / "snapshots"
        if revision and (snaps / revision).exists():
            return str(snaps / revision)
    return model_id


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
    """Deterministic 63-bit seed from arbitrary parts (sha256 of their '|'-joined repr) -- exp8/exp17 convention."""
    return int(hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest(), 16) % (2 ** 63)


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


def append_deviation(did: str, text: str) -> None:
    p = RESULTS_DIR / "deviations.jsonl"
    rows = read_jsonl(p)
    if any(r.get("id") == did for r in rows):
        return
    append_jsonl(p, [{"id": did, "utc": utc_now(), "deviation": text}])
    logger.warning(f"DEVIATION {did}: {text}")


def bench_paths() -> None:
    """Make the copied bench (inputs/exp11: `bench.common...`), the exp8 suite (`labeller`, `tasks`) and the exp28
    re-gate rules importable."""
    for p in (str(SUITE), str(E11), str(E28 / "src")):
        if p not in sys.path:
            sys.path.insert(0, p)


def bench_dir(task: str) -> str:
    for d in BENCH.iterdir():
        if d.is_dir() and d.name.startswith(task + "_"):
            return d.name
    raise FileNotFoundError(task)
