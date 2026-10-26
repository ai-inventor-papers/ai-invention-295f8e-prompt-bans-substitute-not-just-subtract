#!/usr/bin/env python3
"""Shared constants, paths, frozen protocol text and small utilities for the bench route test.

Ported from exp8's cfg.py (art_8_ULPE8jJQc_) with paths re-pointed to this workspace. stable_seed() and the
u_stream() keying are byte-for-byte exp8's, so the T1/T2 screen and the engine validation reuse exp8's uniforms.
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
# Upstream artifacts (read-only). Only S0 (src/s0_inputs.py) and the dataset check in src/supplementary.py read them;
# everything used is snapshotted under inputs/ and published with this folder. ONE environment variable per artifact
# overrides the location; otherwise the run volume's layout is used when present (ROOT = <run>/3_invention_loop/iter_3/
# gen_art/<this>), else the published repository's sibling layout (ROOT = <repo>/round-3/experiment-16/src).
ARTIFACT_IDS = {"exp7": "art_6zBfl3kDjeiP", "exp8": "art_8_ULPE8jJQc_", "exp9": "art_IVZc3TWCeE9f",
                "exp11": "art_0ndRfWKBWclR", "exp12": "art_3iv5G76C3yoX", "dataset": "art_j3Rm_lr2nzR6"}


def _upstream(env: str, run_layout: Path, published_layout: Path) -> Path:
    if os.environ.get(env):
        return Path(os.environ[env])
    return run_layout if run_layout.exists() else published_layout


EXP_DIRS = {e: _upstream(f"BRT_{e.upper()}_DIR", ROOT.parents[2] / "round-2" / "." / f"gen_art_experiment_{e[3:]}",
                         ROOT.parents[2] / "round-2" / f"experiment-{e[3:]}" / "src")
            for e in ("exp7", "exp8", "exp9", "exp11", "exp12")}
# art_j3Rm_lr2nzR6 (the declared dataset dependency, produced in another run of the same study)
DATASET_DIR = _upstream("BRT_DATASET_DIR", ROOT.parents[4] / "run_4VFKidE1bxPG" / "." / "round-1" / "."
                        / "dataset-1/src", ROOT.parents[2] / "round-1" / "dataset-1" / "src")

INPUTS = ROOT / "inputs"
BENCH = INPUTS / "bench"                 # copy of exp11 bench/ (12 frozen tasks + common/)
E8 = INPUTS / "exp8"                     # copy of exp8 suite/, prompts, data, results
E7 = INPUTS / "exp7"
E9 = INPUTS / "exp9"
E12 = INPUTS / "exp12"
LABEL_ROOT = ROOT / "labelling"          # bench judge cache + spend log live here (Judge(root) layout)
PROMPTS_DIR = ROOT / "prompts"
PRED_DIR = ROOT / "predictions"
DATA_DIR = ROOT / "data"
TOKEN_LP_DIR = ROOT / "token_lp"
RESULTS_DIR = ROOT / "results"
FIG_DIR = ROOT / "figures"
LOG_DIR = ROOT / "logs"
WORK_DIR = ROOT / "work"
COMMIT_LOG = ROOT / "commitments.log"
for _d in (PROMPTS_DIR, PRED_DIR, DATA_DIR, TOKEN_LP_DIR, RESULTS_DIR, FIG_DIR, LOG_DIR, WORK_DIR,
           LABEL_ROOT / "data", LABEL_ROOT / "logs"):
    _d.mkdir(parents=True, exist_ok=True)

SAMPLES = DATA_DIR / "samples.jsonl"          # labelled rows (protocol schema)
RAW = DATA_DIR / "samples_raw.jsonl"          # raw generations (written by the GPU worker)
STATE = WORK_DIR / "gpu_state.json"

# ------------------------------------------------------------------------------------------------ model
MODEL_ID = "Qwen/Qwen3-8B"
MODEL_REVISION = "b968826d9c46dd6066d109eabc6255188de91218"


def model_path() -> str:
    env = os.environ.get("BRT_MODEL_PATH")
    if env:
        return env
    cache = os.environ.get("HF_HUB_CACHE")
    if cache:
        snap = Path(cache) / "models--Qwen--Qwen3-8B" / "snapshots" / MODEL_REVISION
        if all((snap / f"model-0000{i}-of-00005.safetensors").exists() for i in range(1, 6)):
            return str(snap)
    return MODEL_ID


def hf_kwargs() -> dict[str, str]:
    return {"revision": MODEL_REVISION} if model_path() == MODEL_ID else {}


N_LAYERS = 36
IM_END = 151645
ENDOFTEXT = 151643
MAX_NEW_TOKENS = 1024
TEMPERATURE = 1.0
DECODING = "T1.0_topp1.0_topk-off_max1024_thinkoff"
TEMPLATE_TAIL = "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"
BATCH = 20  # constant batch shape for every sampled batch (two CRN blocks of 10); see deviations

# ------------------------------------------------------------------------------------------------ bench
STAGE_A = ["T03", "T04", "T06", "T05", "T10", "R1", "T08", "R3", "T13", "R6", "T14", "T11"]
TASK_DIR = {"T03": "T03_kth_smallest", "T04": "T04_substring_search", "T06": "T06_find_duplicate",
            "T05": "T05_two_sum", "T10": "T10_connected_components", "R1": "R1_non_overlapping_intervals",
            "T08": "T08_fibonacci", "R3": "R3_topological_order", "T13": "T13_merge_intervals",
            "R6": "R6_first_last_position", "T14": "T14_top_k_frequent", "T11": "T11_longest_increasing_subsequence"}
DEFAULT = {"T03": "full_sort", "T04": "naive", "T06": "hash_set", "T05": "hash_map", "T10": "union_find",
           "R1": "greedy_end", "T08": "iteration", "R3": "kahn", "T13": "sort_sweep", "R6": "binary_search",
           "T14": "sort_by_count", "T11": "quadratic_dp"}
PATH_TASKS = ("t1", "t2")
PATH_DEFAULT = {"t1": "bfs", "t2": "dijkstra"}
PATH_SUB = {"t1": "dfs", "t2": "bf_spfa"}
ALL_TASKS = STAGE_A + list(PATH_TASKS)

# W1-W5 (ban, mention, neutral) verbatim from the shared protocol v2 (exp8 cfg.TEMPLATES).
TEMPLATES: dict[str, tuple[str, str, str]] = {
    "W1": ("Do not use {X} for this task.", "You could use {X} for this task.", "Do not use {N} for this task."),
    "W2": ("Your solution must not rely on {X}.", "Your solution may rely on {X}.", "Your solution must not rely on {N}."),
    "W3": ("Avoid {X} entirely.", "Consider {X} first.", "Avoid {N} entirely."),
    "W4": ("{X} is not allowed here.", "{X} is allowed here.", "{N} is not allowed here."),
    "W5": ("Write a correct solution that does not use {X}.", "Write a correct solution that may use {X}.",
           "Write a correct solution that does not use {N}."),
}
TEMPLATE_IDS = list(TEMPLATES.keys())
FILLER = " ."  # exp7 frozen neutral-twin padding filler
N_PER_TEMPLATE = 20
BLOCK = 10

THRESHOLDS = {
    "F_confirm": 2.0 / 3.0, "F_ci_lower": 0.5, "F_direct_disconfirm": 1.0 / 3.0,
    "gate_avoidance": 0.5, "gate_min_nondefault": 20,
    "veto_low_direct": 0.8, "veto_high_direct": 0.5, "pred_low_direct_F": 0.15, "pred_high_direct_F": 0.25,
    "veto_min_fire_rate": 0.5, "c2c_hit_fraction": 2.0 / 3.0, "c2c_disconfirm_hit": 0.5, "c2c_alpha": 0.05,
    "ngram_presence": 0.8, "coveto": 0.5, "reemerge": 0.2, "screen_min_nond": 20, "placebo_tol": 0.1,
    "c2b_eligible_V": 0.5, "c2b_task_share": 2.0 / 3.0,
}
N_BOOT = 10000
N_PERM = 100000
RNG_SEED = 20261020
JUDGE_CAP_USD = 0.15  # per judge family (bench j1 + exp8 suite judge); total <= USD 0.30
JUDGE_SOFT_USD = 0.12
EXP8_JUDGE_MODEL = "openai/gpt-4.1-mini"


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
        parts = Path("/sys/fs/cgroup/cpu.max").read_text().split()
        if parts[0] != "max":
            return math.ceil(int(parts[0]) / int(parts[1]))
    except (FileNotFoundError, ValueError):
        pass
    try:
        q = int(Path("/sys/fs/cgroup/cpu/cpu.cfs_quota_us").read_text())
        p = int(Path("/sys/fs/cgroup/cpu/cpu.cfs_period_us").read_text())
        if q > 0:
            return math.ceil(q / p)
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
    """exp8: deterministic 63-bit seed from arbitrary parts (sha256 of their '|'-joined repr)."""
    return int(hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest(), 16) % (2 ** 63)


def read_jsonl(p: Path) -> list[dict[str, Any]]:
    if not Path(p).exists():
        return []
    out = []
    with open(p) as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    logger.warning(f"skipping a corrupt line in {p}")
    return out


def write_jsonl(p: Path, rows: Iterable[dict[str, Any]]) -> None:
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    with open(tmp, "w") as fh:
        for r in rows:
            fh.write(json.dumps(r, default=_json_default) + "\n")
    tmp.replace(p)


def append_jsonl(p: Path, rows: Iterable[dict[str, Any]]) -> None:
    with open(p, "a") as fh:
        for r in rows:
            fh.write(json.dumps(r, default=_json_default) + "\n")
        fh.flush()


def _json_default(o: Any) -> Any:
    try:
        import numpy as np

        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, np.floating):
            return None if not np.isfinite(o) else float(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
        if isinstance(o, np.bool_):
            return bool(o)
    except ImportError:
        pass
    if isinstance(o, Path):
        return str(o)
    if isinstance(o, (set, frozenset)):
        return sorted(o)
    if isinstance(o, tuple):
        return list(o)
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
    tmp.write_text(json.dumps(_finite(obj), indent=indent, default=_json_default))
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


def chat_ids(tok: Any, user_text: str) -> list[int]:
    s = chat_text(tok, user_text)
    return list(tok(s, add_special_tokens=False).input_ids)


def chat_text(tok: Any, user_text: str) -> str:
    s = tok.apply_chat_template([{"role": "user", "content": user_text}], tokenize=False,
                                add_generation_prompt=True, enable_thinking=False)
    assert s.endswith(TEMPLATE_TAIL), repr(s[-80:])
    return s


def resp_ids(tok: Any, code: str) -> list[int]:
    """Frozen protocol: resp(code) = tokens of '```python\\n' + code.rstrip('\\n') + '\\n```'."""
    return list(tok("```python\n" + code.rstrip("\n") + "\n```", add_special_tokens=False).input_ids)


def default_of(task: str) -> str:
    return PATH_DEFAULT[task] if task in PATH_TASKS else DEFAULT[task]
