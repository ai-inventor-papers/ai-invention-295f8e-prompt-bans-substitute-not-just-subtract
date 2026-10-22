#!/usr/bin/env python3
"""Shared constants, paths and small utilities for Claim E (Gemma base-repertoire replication; iteration 5).

Conventions (ported from the iteration-4 Gemma artifact exp23 and stated again in README.md / method_out.json):
- BLOCK l = decoder block l (0-based); its output is HF hidden_states[l + 1].
- SPEC positions S = [spec_start, spec_end): from the first token of the task specification to the last token of the
  user message (the chat tail '<end_of_turn>\\n<start_of_turn>model\\n' excluded). R = P - 1 (last prompt token).
- CRN slot = (task, template, k); uniforms PCG64(stable_seed('iter5E', task, template, k)) are identical in every
  coupled arm (it twin, pushes, plan noise, transplant arms) AND in the pt-chat repertoire (same token ids).
- BAND = middle third of the decoder blocks (gemma-3-4b: blocks 11-22 of 34).
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
E18 = INPUTS / "exp18"
E23 = INPUTS / "exp23"
DEP1 = INPUTS / "art_j3Rm_lr2nzR6"
BENCH = E11 / "bench"
SUITE = E8 / "suite"
DATA_DIR = ROOT / "data"
CACHE_DIR = ROOT / "cache"
RESULTS_DIR = ROOT / "results"
FIG_DIR = ROOT / "figures"
LOG_DIR = ROOT / "logs"
PRED_DIR = ROOT / "predictions"
AUDIT_DIR = ROOT / "audit"
EXT_DIR = ROOT / "extensions"          # re-gate additions (new references, extended-catalogue labels)
for _d in (DATA_DIR, RESULTS_DIR, FIG_DIR, LOG_DIR, PRED_DIR, CACHE_DIR, AUDIT_DIR, EXT_DIR):
    _d.mkdir(parents=True, exist_ok=True)
COMMIT_LOG = ROOT / "commitments.log"
PATHS_LOCAL = ROOT / "paths.local.json"  # unpublished map {short name: upstream workspace} used only by stage_inputs

# ------------------------------------------------------------------------------------------------ models
IT_ID = "google/gemma-3-4b-it"
IT_REV = "093f9f388b31de276ce2de164bdc2081324b9767"
PT_ID = "google/gemma-3-4b-pt"
PT_REV = "cc012e0a6d0787b4adcc0fa2c4da74402494554d"   # pinned at preflight (huggingface_hub model_info sha)
PT_FALLBACK = ("unsloth/gemma-3-4b-pt", "52aba93981c6ad7712b030eb6dd496ece1d279d6")
MODELS = {"it": (IT_ID, IT_REV), "pt": (PT_ID, PT_REV)}
N_LAYERS = 34
D_MODEL = 2560
BAND = list(range(11, 23))             # middle third of 34 blocks
CAPTURE_BLOCKS = list(range(11, 34))   # realised displacement logged from BAND start to the last block
BOS_ID = 2
EOS_ID = 1
SOT_ID = 105                           # <start_of_turn> (asserted against the tokenizer at load)
EOT_ID = 106                           # <end_of_turn>
STOP_IDS = {"it": (EOS_ID, EOT_ID), "pt": (EOS_ID, EOT_ID, SOT_ID)}
CHAT_HEAD = "<bos><start_of_turn>user\n"
CHAT_TAIL = "<end_of_turn>\n<start_of_turn>model\n"
MAX_NEW_BENCH = 1024
MAX_NEW_PATH = 1536
MAX_NEW_PLAIN = 768
MAX_NEW_EXP23 = 640                    # exp23's cap (engine check only)
STOP_CHECK_EVERY = 16
DECODING = "T1.0_topp1.0_topk-off_inverse-CDF-CRN"
PRECISION = "bf16 (sdpa attention); logits fp32, CDF float64"

# ------------------------------------------------------------------------------------------------ tasks
PATH_TASKS = ("T1", "T2")
BENCH12 = ("T03", "T04", "T06", "T05", "T10", "R1", "T08", "R3", "T13", "R6", "T14", "T11")
BENCH_TASKS = BENCH12 + ("R2",)
ALL_TASKS = PATH_TASKS + BENCH_TASKS      # 15 tasks
EXP8_TASK = {"T1": "t1", "T2": "t2"}
# fixed cyclic order of the plan (donor of the cross-task control = next task in this order)
CYCLIC_ORDER = ("T1", "T2", "T03", "T04", "T05", "T06", "T08", "T10", "T11", "T13", "T14", "R1", "R2", "R3", "R6")
# exp23 commit #1 D_g per task: the X whose ban length the frozen twins match (twins are byte-identical to exp23's)
EXP23_TWIN_X = {"T1": "dfs", "T2": "dijkstra", "T03": "full_sort", "T04": "naive", "T06": "hash_set", "T05": "hash_map",
                "T10": "dfs", "R1": "greedy_end", "T08": "iteration", "R3": "kahn", "T13": "sort_sweep",
                "R6": "binary_search", "T14": "sort_by_count", "T11": "patience_bisect", "R2": "dfs_parent"}
TEMPLATES: dict[str, tuple[str, str]] = {  # (ban, neutral twin) -- protocol W1-W5, verbatim (ban side: length only)
    "W1": ("Do not use {X} for this task.", "Do not use {N} for this task."),
    "W2": ("Your solution must not rely on {X}.", "Your solution must not rely on {N}."),
    "W3": ("Avoid {X} entirely.", "Avoid {N} entirely."),
    "W4": ("{X} is not allowed here.", "{N} is not allowed here."),
    "W5": ("Write a correct solution that does not use {X}.", "Write a correct solution that does not use {N}."),
}
TEMPLATE_IDS = list(TEMPLATES)
PAD_FILLER = " ."
MAX_PAD = 24
NOVELTY = "Write a novel algorithm for this task, one you have not seen before."
PLAIN_STDLIB = "Use only the Python standard library."

# ------------------------------------------------------------------------------------------------ design (protocol E)
SLOT_PREFIX = "iter5E"
DIR_SEEDS = tuple(range(52001, 52017))     # 16 never-run isotropic directions
ALPHAS = (1.0, 2.0)
N_TWIN_PER_T = 10                          # twin slots 0-9 per template (N = 50 per task)
N_STAGE1_PER_T = 2                         # escape stage 1: slots 0-1 per template (N = 10 per direction-alpha)
STAGE2_SLOTS = (2, 3, 4, 5)                # confirmation top-up (+20 -> N = 30)
N_PN_PER_T = 10                            # plan noise: 10 per template per alpha (N = 50 per alpha)
N_PT_CHAT_PER_T = 20                       # pt under the it chat template: N = 100 per task
N_PT_PLAIN = 50                            # pt plain completion: N = 50 per task
N_NOVELTY = 30
N_TRANSPLANT_PER_T = 10                    # transplant arms on the twin's slots 0-9 (N = 50)
ESCAPE_EXCESS = 0.20
ESCAPE_PASS_FRAC = 0.80
BINOM_ALPHA = 0.05
P0_FLOOR = 0.01
DEFAULT_SHARE = 0.6
DEFAULT_MIN_CORRECT = 10
BETA_MOVABLE = 0.05
BETA_DIVERSE = 0.2
MIN_CORRECT_BASE = 20
RHO_E = 0.5
P_E = 0.01
IMMOVABLE_FRAC = 0.8
A2_HIT = 0.7
A2_NATS = 0.10
LAMBDA = 1.0
LAMBDA_FALLBACK = 0.5
N_MASSIVE = 5
OTHER_FLOOR = 0.02
B_CRN = 42                                 # fixed batch shape of every coupled single-prompt batch (memory-probed)
BUDGET_MSG = "AI Inventor per-run OpenRouter budget"
OPENROUTER_CAP_USD = 1.50
NOT_COUNTED = ("invalid", "disputed")


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
            return max(1, math.ceil(q / p))
    except (FileNotFoundError, ValueError):
        pass
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
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ids_sha(ids: list[int]) -> str:
    return hashlib.sha256(json.dumps([int(i) for i in ids]).encode()).hexdigest()


def stable_seed(*parts: Any) -> int:
    """Deterministic 63-bit seed from arbitrary parts (sha256 of their '|'-joined repr) -- exp8/exp23 convention."""
    return int(hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest(), 16) % (2 ** 63)


def read_jsonl(p: Path) -> list[dict[str, Any]]:
    p = Path(p)
    if not p.exists():
        return []
    out = []
    with open(p) as fh:
        lines = fh.readlines()
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            if i == len(lines) - 1:  # a concurrently appended, not yet complete last line
                continue
            logger.warning(f"skipping malformed line {i} in {p.name}")
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


def _finite(o: Any) -> Any:
    if isinstance(o, float):
        return o if math.isfinite(o) else None
    if isinstance(o, dict):
        return {str(k): _finite(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_finite(v) for v in o]
    return o


def append_jsonl(p: Path, rows: Iterable[dict[str, Any]]) -> int:
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(p, "a") as fh:
        for r in rows:
            fh.write(json.dumps(_finite(json.loads(json.dumps(r, default=_json_default)))) + "\n")
            n += 1
        fh.flush()
    return n


def write_jsonl(p: Path, rows: Iterable[dict[str, Any]]) -> None:
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    with open(tmp, "w") as fh:
        for r in rows:
            fh.write(json.dumps(_finite(json.loads(json.dumps(r, default=_json_default)))) + "\n")
    tmp.replace(p)


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


def model_path(model_id: str, revision: str | None) -> str:
    cache = os.environ.get("HF_HUB_CACHE")
    if cache:
        snaps = Path(cache) / ("models--" + model_id.replace("/", "--")) / "snapshots"
        if revision and (snaps / revision).exists():
            return str(snaps / revision)
    from huggingface_hub import snapshot_download

    return snapshot_download(model_id, revision=revision,
                             allow_patterns=["*.json", "*.safetensors", "tokenizer.model"])


def add_deviation(key: str, text: str) -> None:
    p = RESULTS_DIR / "deviations.json"
    d = read_json(p) if p.exists() else {}
    d[key] = text
    write_json(p, d)


def bench_paths() -> None:
    """Import paths for the frozen bench (bench.common.*) and the exp8 suite (labeller.*, tasks.*)."""
    for p in (str(SUITE), str(E11)):
        if p not in sys.path:
            sys.path.insert(0, p)


def cap_of(task: str) -> int:
    return MAX_NEW_PATH if task in PATH_TASKS else MAX_NEW_BENCH


# ================================================================================================ ITERATION 6 (Claim L, Gemma)
# Step 5 of iteration 6: base runner-up r_u vs the it model's own tail (q_tail / t_u) vs its teacher-forced likelihood
# (q_lik). Everything above this line is exp28's frozen configuration, reused unchanged (same engine, slot scheme,
# twin prompts, push unit, labellers). New rows never reuse exp28 row ids; exp28's rows are read from inputs/exp28/.
E28 = INPUTS / "exp28"
E28_DATA = E28 / "data"
E28_RESULTS = E28 / "results"
E28_PRED = E28 / "predictions"
GENESIS6 = "iter6_gemma_L"
PUSH_TASKS6 = ("R6", "T04", "T05", "T10", "T03", "T11", "T1", "T2")   # frozen order (iteration-5 movable tasks)
DIR_SEEDS6 = tuple(range(63001, 63009))                                 # 8 never-run isotropic directions
ALPHA6 = 2.0
NS_PTFS = "iter6G-ptfs"         # few-shot pt uniforms
NS_FORCED = "iter6G-forced"     # forced-program uniforms (q_lik writers)
NS_PN = "iter6G-PN"             # fresh per-sample plan-noise directions
TWIN6_T10_SLOTS = tuple(range(10, 40))   # new T 1.0 twin slots (exp28 slots 0-9 reused) -> N 200 at T 1.0
TWIN6_T13_SLOTS = tuple(range(0, 20))    # T 1.3 twin slots (same 'iter5E' uniforms as T 1.0 slots 0-19) -> N 100
T_HOT = 1.3
PN6_SLOTS = tuple(range(10, 20))         # fresh PN alpha 2: slots 10-19 x W1-W5 (N 50; CRN-paired with twin slots)
FD6_STAGE1_SLOTS = (0, 1)
FD6_CONFIRM_SLOTS = (2, 3, 4, 5)
PTFS_STAGE = 100                          # few-shot draws per stage (A, B, C)
PTFS_CAP = 300
PTFS_MIN_CORRECT = 20                     # stop when pooled correct pt programs >= 20
PTFS_B = 40                               # few-shot batch rows (prefill_multi; P ~ 600-900 + 768 new)
FORCED_N = 20                             # forced programs per algorithm (+20 if < 10 kept; cap 40)
FORCED_KEEP = 10
QLIK_WINDOW = 48
QLIK_OTHER = 0.02
EVENT_MIN_PROGRAMS = 5
LANDING_MARGIN = 0.15
L1_MIN_EVENTS = 6
NONINF_NATS = -0.10
AUDIT_PER_TASK = 15
AUDIT_GATE = 0.80
EXEMPLAR_BENCH_ORDER = ("T08", "T04", "R6", "T13")
EXEMPLAR_REF = {"T08": "iteration", "T04": "naive", "R6": "linear_scan", "T13": "sort_sweep"}
FAMILY_GROUP = {"T1": "graph", "T2": "graph", "T10": "graph", "R2": "graph", "R3": "graph",
                "T04": "search", "R6": "search",
                "T03": "order", "T13": "order", "T14": "order", "R1": "order", "T11": "order",
                "T05": "hashing", "T06": "hashing", "T08": "numeric"}
OPENROUTER_CAP6_USD = 1.50
EXTENDED_DISPLAY = {("R6", "linear_scan"): "a linear scan"}

# ------------------------------------------------------------------------------------------------ upstream artifacts
# Upstream artifacts are sibling folders of this one in the published repository, named by artifact id. ONE environment
# variable, AII_ARTIFACTS_DIR, overrides their common parent (default: the parent folder of this artifact). The optional,
# unpublished paths.local.json {short name: path} overrides individual locations (used on the original run server, whose
# folders are named by step, not by id). Only the preflight stage and the U6 clean-state check read upstream folders;
# every other stage reads the sha256-verified copies under inputs/.
ARTIFACTS_DIR = Path(os.environ.get("AII_ARTIFACTS_DIR", str(ROOT.parent)))
UPSTREAM_IDS = {
    "exp28": "art_hG0QPiaIPNhP",            # iteration-5 Gemma artifact (engine, labellers, rows, clean-state cache)
    "exp23": "art_k6nzFCDLOjQP",            # iteration-4 Gemma artifact
    "exp11": "art_0ndRfWKBWclR",            # frozen 13-task bench (bench/commitment.json for the sha256 check)
    "exp8": "art_8_ULPE8jJQc_",             # T1/T2 suite
    "exp7": "art_6zBfl3kDjeiP",             # frozen templates / nouns / forced paraphrases
    "exp18": "art_ccAbfJVcv0LO",            # known-solutions index (novelty audit)
    "eval3": "art_sV0cQ3ef1ZRQ",            # iteration-4 evaluation
    "art_j3Rm_lr2nzR6": "art_j3Rm_lr2nzR6",  # declared dependency: source data (10 datasets)
}


def upstream() -> dict[str, Path]:
    out = {k: ARTIFACTS_DIR / v for k, v in UPSTREAM_IDS.items()}
    if PATHS_LOCAL.exists():
        out.update({k: Path(v) for k, v in read_json(PATHS_LOCAL).items()})
    return out
