#!/usr/bin/env python3
"""Shared constants, paths and utilities for the iteration-4 'pricing plan noise against temperature' artifact.

Conventions (inherited from iteration-3 exp17, also stated in README.md):
- BLOCK l = decoder block l (0-based); its output is HF hidden_states[l + 1].
- SPEC positions S = [p1, spec_end): from the first token of 'Task:' to the last user token (chat tail excluded).
  R = P - 1 (the read position).
- CRN slot = (task, template w, k); uniforms u_stream(task, w, k) (PCG64 of a sha256 seed) are shared by EVERY arm of
  this artifact; one uniform per (row, step), inverse-CDF in vocabulary order.
- PN direction of a row: seed_k = stable_seed(task, arm, w, k); u = x / ||x||, x ~ N(0, I_4096) from PCG64(seed_k),
  shared across blocks 12-23 and spec positions (the exp17 screen's construction, one fresh direction per sample).
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
E13 = INPUTS / "exp13"
E16 = INPUTS / "exp16"
E17 = INPUTS / "exp17"
E18 = INPUTS / "exp18"
E6 = INPUTS / "exp6"
EVAL2 = INPUTS / "eval2"
DEP = INPUTS / "dep_dataset"
BENCH = E11 / "bench"
SUITE = E8 / "suite"
DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "results"
FIG_DIR = ROOT / "figures"
LOG_DIR = ROOT / "logs"
PRED_DIR = ROOT / "predictions"
AUDIT_DIR = ROOT / "audit"
for _d in (DATA_DIR, RESULTS_DIR, FIG_DIR, LOG_DIR, PRED_DIR, AUDIT_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# Source artifacts (read-only). This folder sits at <runs>/<run>/3_invention_loop/iter_4/gen_art/<artifact>, so the
# earlier iterations are found relative to it; each location can be overridden by an environment variable. Only the
# input-copy step, src/screen.py (exp16 path rows) and src/dep_usage.py (the dataset dependency) read them.
RUN_ROOT = Path(os.environ.get("AII_LOOP_DIR", ROOT.parents[2]))  # <run>/3_invention_loop
ITER2 = Path(os.environ.get("AII_ITER2_DIR", RUN_ROOT / "round-2" / "."))
ITER3 = Path(os.environ.get("AII_ITER3_DIR", RUN_ROOT / "round-3" / "."))
# iteration 1 belongs to another run of the same pipeline (run_4VFKidE1bxPG)
ITER1 = Path(os.environ.get("AII_ITER1_DIR", ROOT.parents[4] / "run_4VFKidE1bxPG" / "." / "round-1"
                            / "."))
# the declared dataset dependency art_j3Rm_lr2nzR6: ART_J3RM_DIR, else the published sibling folder, else the run layout
DEP_DATASET_DIR = Path(os.environ.get("ART_J3RM_DIR") or next(
    (d for d in (ROOT.parent / "art_j3Rm_lr2nzR6",) if d.exists()), ITER1 / "gen_art_dataset_1"))

# ------------------------------------------------------------------------------------------------ model
MODEL_ID = "Qwen/Qwen3-8B"
MODEL_REVISION = "b968826d9c46dd6066d109eabc6255188de91218"
N_LAYERS = 36
D_MODEL = 4096
IM_END = 151645
ENDOFTEXT = 151643
MAX_NEW_TOKENS = 1024          # bench tasks and the engine check (the exp17 screen's cap)
MAX_NEW_PATH = 1024            # path tasks: the screen's cap (plan: 1,536; see deviations D-cap)
TEMPLATE_TAIL = "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"
QUANT = ("fp8_e4m3_w8a8_dynamic(per-output-channel weight scales, per-token activation scales; "
         "lm_head/embeddings/norms bf16)")
ENGINE_TAG = "hf_fp8"


def model_path(model_id: str = MODEL_ID, revision: str | None = MODEL_REVISION) -> str:
    cache = os.environ.get("HF_HUB_CACHE")
    if cache:
        snaps = Path(cache) / ("models--" + model_id.replace("/", "--")) / "snapshots"
        if revision and (snaps / revision).exists():
            return str(snaps / revision)
    return model_id


# ------------------------------------------------------------------------------------------------ tasks
PATH_TASKS = ("T1", "T2")
E6_TASKS = ("T03", "T05", "T06", "T10", "T1", "T2")            # frozen decisive event set
HELDOUT = ("R2",)
P3_TASKS = ("T04", "T08", "T11", "T13", "T14", "R1", "R3", "R6")  # the other 8 bench tasks
P3_DROP_ORDER = ("T11", "T14", "R6", "T13", "R3", "T08", "R1", "T04")  # reverse Stage-A order
BENCH12 = ("T03", "T04", "T06", "T05", "T10", "R1", "T08", "R3", "T13", "R6", "T14", "T11")
BENCH_TASKS = BENCH12 + ("R2",)
ALL_TASKS = PATH_TASKS + BENCH_TASKS
DEFAULT = {"T1": "bfs", "T2": "dijkstra", "T03": "full_sort", "T04": "naive", "T06": "hash_set", "T05": "hash_map",
           "T10": "union_find", "R1": "greedy_end", "T08": "iteration", "R3": "kahn", "T13": "sort_sweep",
           "R6": "binary_search", "T14": "sort_by_count", "T11": "quadratic_dp", "R2": "dfs_parent"}
EXP8_TASK = {"T1": "t1", "T2": "t2"}
TEMPLATES: dict[str, tuple[str, str]] = {  # (ban, neutral) -- protocol v2 W1-W5, verbatim
    "W1": ("Do not use {X} for this task.", "Do not use {N} for this task."),
    "W2": ("Your solution must not rely on {X}.", "Your solution must not rely on {N}."),
    "W3": ("Avoid {X} entirely.", "Avoid {N} entirely."),
    "W4": ("{X} is not allowed here.", "{N} is not allowed here."),
    "W5": ("Write a correct solution that does not use {X}.", "Write a correct solution that does not use {N}."),
}
TEMPLATE_IDS = list(TEMPLATES)
PAD_FILLER = " ."
NONCE_X = "the Zorblax method"
NOVELTY = "Write a novel algorithm for this task, one you have not seen before."
VS_SEGMENT = ("Before writing code, list five different algorithms that solve this task, each with the probability "
              "that you would choose it; then pick one of them at random according to those probabilities and "
              "implement only that one.")

# ------------------------------------------------------------------------------------------------ design
V_BLOCKS = list(range(12, 24))          # PN is added at the task-spec positions of blocks 12-23, prefill only
NORM_BLOCKS = list(range(12, N_LAYERS))  # realised displacement logged at blocks 12-35
SLOTS = list(range(10))                 # k 0-9 per template -> N = 50
PN_ALPHAS = (0.5, 1.0, 2.0, 4.0)
PN_EXTRA_ALPHA = 8.0
# arm -> decoding / prompt definition. prompt kinds: twin, plain, nonce, novelty, semseed, vs
ARMS: dict[str, dict[str, Any]] = {
    "TWIN": {"prompt": "twin", "T": 1.0, "top_k": 0, "min_p": 0.0, "alpha": None, "knob": "REF"},
    "PN_a0.5": {"prompt": "twin", "T": 1.0, "top_k": 0, "min_p": 0.0, "alpha": 0.5, "knob": "PN"},
    "PN_a1": {"prompt": "twin", "T": 1.0, "top_k": 0, "min_p": 0.0, "alpha": 1.0, "knob": "PN"},
    "PN_a2": {"prompt": "twin", "T": 1.0, "top_k": 0, "min_p": 0.0, "alpha": 2.0, "knob": "PN"},
    "PN_a4": {"prompt": "twin", "T": 1.0, "top_k": 0, "min_p": 0.0, "alpha": 4.0, "knob": "PN"},
    "PN_a8": {"prompt": "twin", "T": 1.0, "top_k": 0, "min_p": 0.0, "alpha": 8.0, "knob": "PN_EXTRA"},
    "T1.3": {"prompt": "twin", "T": 1.3, "top_k": 0, "min_p": 0.0, "alpha": None, "knob": "TEMP"},
    "T1.6": {"prompt": "twin", "T": 1.6, "top_k": 0, "min_p": 0.0, "alpha": None, "knob": "TEMP"},
    "TOPK10": {"prompt": "twin", "T": 1.0, "top_k": 10, "min_p": 0.0, "alpha": None, "knob": "TOPK10"},
    "MINP_T1.6": {"prompt": "twin", "T": 1.6, "top_k": 0, "min_p": 0.1, "alpha": None, "knob": "MINP"},
    "MINP_T2.0": {"prompt": "twin", "T": 2.0, "top_k": 0, "min_p": 0.1, "alpha": None, "knob": "MINP"},
    "PLAIN": {"prompt": "plain", "T": 1.0, "top_k": 0, "min_p": 0.0, "alpha": None, "knob": "REF_PLAIN"},
    "PNPLAIN_a1": {"prompt": "plain", "T": 1.0, "top_k": 0, "min_p": 0.0, "alpha": 1.0, "knob": "PNPLAIN"},
    "NONCE": {"prompt": "nonce", "T": 1.0, "top_k": 0, "min_p": 0.0, "alpha": None, "knob": "NONCE"},
    "NOVELTY": {"prompt": "novelty", "T": 1.0, "top_k": 0, "min_p": 0.0, "alpha": None, "knob": "NOVELTY"},
    "SEMSEED": {"prompt": "semseed", "T": 1.0, "top_k": 0, "min_p": 0.0, "alpha": None, "knob": "SEMSEED"},
    "VS": {"prompt": "vs", "T": 1.0, "top_k": 0, "min_p": 0.0, "alpha": None, "knob": "VS"},
}
PN_ARMS = ("PN_a0.5", "PN_a1", "PN_a2", "PN_a4")
JUDGE_CAP_USD = 1.00
BUDGET_MSG = "AI Inventor per-run OpenRouter budget"
BOOT_SEED = 20261021
N_BOOT = 2000
DEPTH = 25


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
    for p in (str(SUITE), str(E11)):
        if p not in sys.path:
            sys.path.insert(0, p)
N_HEADS = 32
HEAD_DIM = 128
