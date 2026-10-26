#!/usr/bin/env python3
"""Iteration-8 claim L constants: a frozen two-decision temperature law for algorithm choice, scored on 8 units in
three model families (Qwen3-8B, gemma-3-4b-it, Llama-3.1-8B-Instruct), plus a base-vs-instruct sub-arm (Qwen3-8B-Base).

Conventions (inherited from iterations 4-7):
- CRN: every program slot draws one uniform per generated token from u_stream(key) = PCG64(seed(key)); the sampler
  (iteration-6 engine5 transform) is fp64 softmax(logits / T) -> top-k mask (keep p >= k-th largest) -> cumsum over the
  FULL vocabulary in TOKEN-ID order, normalised by the kept mass -> searchsorted(u). Generated step t uses u[t].
- FIT keys reuse the source artifacts' keys so the fit twins double as engine checks: Qwen ('iter7T', unit, w, slot)
  (art_MZAfDPVhM6Ui cfg7), Gemma ('iter5E' | 'iter6S', task, w, slot) (art_zNyBP6zieI5u cfg), Llama new
  ('iter8L-fit', ...). New namespaces: seed8(ns, model, unit, template, slot) = int(first 16 hex of sha256('|'.join)).
- Decision position d = number of generated tokens before the decision token (the decision token is generated at
  step d with u[d]); the opening O_c is the d tokens before it.
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

import numpy as np
from loguru import logger

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
INPUTS = ROOT / "inputs"
DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "results"
FIG_DIR = ROOT / "figures"
LOG_DIR = ROOT / "logs"
PRED_DIR = ROOT / "predictions"
CACHE_DIR = ROOT / "cache"
for _d in (DATA_DIR, RESULTS_DIR, FIG_DIR, LOG_DIR, PRED_DIR, CACHE_DIR):
    _d.mkdir(parents=True, exist_ok=True)

COMMITS = ROOT / "commitments.log"
SAMPLES_RAW = DATA_DIR / "samples_raw.jsonl"      # every program of every arm (fit twins, sweep, top-k shadow)
LABELS = DATA_DIR / "labels.jsonl"
CONTS = DATA_DIR / "continuations.jsonl"          # locator / refinement / forced-token continuations
CONT_LABELS = DATA_DIR / "continuation_labels.jsonl"
TIMING = RESULTS_DIR / "timing.jsonl"

# read-only prior artifacts (absolute paths on the run volume; copied into inputs/ with sha256 by vendor_inputs.py)
_RUNS = ROOT.parents[4]
RUN = ROOT.parents[3]
PREV = _RUNS / "run_aRfWvcSWjssb" / "."
ITER = RUN / "."
SRCS = {
    "exp35": ITER / "round-7" / "." / "experiment-35/src",      # art_MZAfDPVhM6Ui
    "exp34": ITER / "round-7" / "." / "experiment-34/src",      # art_pHL7LWNhpcCS
    "exp38": ITER / "round-7" / "." / "experiment-38/src",      # art_HY7uYZz-OjRW
    "exp31": ITER / "round-6" / "." / "experiment-31/src",      # art_zNyBP6zieI5u
    "exp29": ITER / "round-6" / "." / "experiment-29/src",      # art_lpQalcAXMGr1
    "exp10": PREV / "round-2" / "." / "experiment-10/src",
    "exp11": PREV / "round-2" / "." / "experiment-11/src",
    "exp8": PREV / "round-2" / "." / "experiment-8/src",
    "exp18": PREV / "round-3" / "." / "experiment-18/src",
    "exp24": PREV / "round-5" / "." / "experiment-24/src",      # art_CcZLW-9NX00l
    "exp25": PREV / "round-5" / "." / "experiment-25/src",
    "exp26": PREV / "round-5" / "." / "experiment-26/src",
    "dep": _RUNS / "run_4VFKidE1bxPG" / "." / "round-1" / "." / "dataset-1/src",
}
# the declared dataset dependency art_j3Rm_lr2nzR6 (read-only): ART_J3RM_DIR, else the published sibling folder
# ../art_j3Rm_lr2nzR6 of the repository, else the original run layout
if os.environ.get("ART_J3RM_DIR"):
    SRCS["dep"] = Path(os.environ["ART_J3RM_DIR"])
elif (ROOT.parent / "art_j3Rm_lr2nzR6").exists():
    SRCS["dep"] = ROOT.parent / "art_j3Rm_lr2nzR6"
# fresh clone: fall back to the sha256-checked copies made by src/vendor_inputs.py (inputs/src_<name>/...)
SRCS = {k: (v if v.exists() else INPUTS / f"src_{k}") for k, v in SRCS.items()}

# ------------------------------------------------------------------------------------------------ models
FAMILIES: dict[str, dict[str, Any]] = {
    "gemma": {"model_id": "google/gemma-3-4b-it", "rev": "093f9f388b31de276ce2de164bdc2081324b9767",
              "stop_ids": (1, 106), "pad_id": 106},
    "llama": {"model_id": "meta-llama/Llama-3.1-8B-Instruct", "rev": "0e9e39f249a16976918f6564b8830bc894c89659",
              "stop_ids": (128001, 128008, 128009), "pad_id": 128009},
    "qwen": {"model_id": "Qwen/Qwen3-8B", "rev": "b968826d9c46dd6066d109eabc6255188de91218",
             "stop_ids": (151645, 151643), "pad_id": 151645},
    "qwen_base": {"model_id": "Qwen/Qwen3-8B-Base", "rev": "49e3418fbbbca6ecbdf9608b4d22e5a407081db4",
                  "stop_ids": (151645, 151643), "pad_id": 151643},
}
FAMILY_ORDER = ("gemma", "llama", "qwen")          # held-out families first
PRECISION = "bf16"
U_LEN = 2048

# ------------------------------------------------------------------------------------------------ units
TEMPLATES = ("W1", "W2", "W3", "W4", "W5")
LLAMA_BENCH_ORDER = ("T03", "T06", "T04", "R1", "T14", "T10", "T08")   # ITER2 exp11 pilot, most mixed first
LLAMA_BENCH_KEEP = 2
LLAMA_MINORITY_BAR = 0.10

UNITS: dict[str, dict[str, Any]] = {
    # law-development units (Qwen3-8B; iteration-7 law units), fit keys = iteration-7 twin keys
    "A3": {"family": "qwen", "task": "A3", "lab": "a", "held_out": False, "max_new": 640, "batch": 20,
           "catalogue": ["two_pointers", "prefix_suffix_max", "monotonic_stack", "peak_split"],
           "name": "trapped rain water", "fence": "bench"},
    "B6": {"family": "qwen", "task": "B6", "lab": "b", "held_out": False, "max_new": 384, "batch": 20,
           "catalogue": ["sort_compare", "hash_count", "fixed_count_array"], "name": "valid anagram",
           "fence": "bench"},
    "B3": {"family": "qwen", "task": "B3", "lab": "b", "held_out": False, "max_new": 768, "batch": 20,
           "catalogue": ["kruskal", "prim_heap", "prim_array", "boruvka"], "name": "minimum spanning tree weight",
           "fence": "bench"},
    # held-out units (never used to develop the law or its procedure)
    "G-T04": {"family": "gemma", "task": "T04", "lab": "bench", "held_out": True, "max_new": 1024, "batch": 20,
              "catalogue": ["naive", "kmp", "rabin_karp", "z_algorithm", "bmh", "builtin"],
              "name": "substring search", "fence": "bench"},
    "G-R6": {"family": "gemma", "task": "R6", "lab": "bench", "held_out": True, "max_new": 1024, "batch": 20,
             "catalogue": ["binary_search", "bisect_module", "exponential_search", "linear_scan"],
             "name": "first and last position", "fence": "bench"},
    "L-T1": {"family": "llama", "task": "T1", "lab": "path", "held_out": True, "max_new": 1536, "batch": 10,
             "catalogue": ["bfs", "dfs", "bibfs", "astar_gbfs", "dijkstra", "iddfs"], "name": "grid path",
             "fence": "path"},
}
for _t in LLAMA_BENCH_ORDER:
    UNITS[f"L-{_t}"] = {"family": "llama", "task": _t, "lab": "bench", "held_out": True, "max_new": 1024,
                        "batch": 20, "catalogue": None, "name": f"bench {_t}", "fence": "bench", "candidate": True}
LAW_UNITS_FIXED = ("G-T04", "G-R6", "L-T1", "A3", "B6", "B3")

# ------------------------------------------------------------------------------------------------ design
TEMPS = (0.3, 0.7, 1.0, 1.3)
SAMPLERS = {"p1": 0, "k10": 10}
FIT_SLOTS = tuple(range(0, 20))       # x 5 templates = N 100 at T 1 (FIT keys)
SWEEP_SLOTS = tuple(range(0, 20))     # x 5 templates = N 100 per cell ('iter8L-sweep' keys)
NS_FIT_L = "iter8L-fit"
NS_LOC = "iter8L-loc"
NS_FORCE = "iter8L-force"
NS_SWEEP = "iter8L-sweep"
NS_REFINE = "iter8L-refine"
NS_SECOND = "iter8L-second"
N_LOC = 8                 # continuations per (path, k)
N_REFINE = 16
N_FORCE = 10              # per forced token (2 per template)
TOPN_FORCE = 20
TOPN_FORCE2 = 10
N_BASE_PATHS = 6
GRID_DENSE = tuple(range(0, 63, 2))
GRID_STEP_LATE = 4
W_MAX = 160
SECOND_SPAN = 24
BOOT_SEED = 20261023
N_BOOT = 1000
BUDGET_MSG = "AI Inventor per-run OpenRouter budget"
JUDGE_CAP_USD = 0.60

THRESH = {
    "unit_mae_pass": 0.10, "unit_H_bits_pass": 0.3, "claim_frac_pass": 0.70, "heldout_pass_min": 3,
    "heldout_scored_min": 4, "disconfirm_mae": 0.20, "disconfirm_heldout_n": 3,
    "cp_pchange": 0.9, "cp_tv": 0.25, "refine_tv": 0.25, "class_phat_min": 0.7, "class_mass_min": 0.02,
    "second_trigger_mass": 0.05, "second_trigger_H": 0.3, "cluster_cov": 0.20, "max_clusters": 4,
    "oc_agree": 0.95, "consistency_tvd": 0.10, "calib_fisher_p": 0.05, "engine_agree": 0.95, "shadow_ident": 0.95,
    "regate_agree": 0.9, "other_adjudicate": 0.20, "base_margin_gain": 2.0, "base_phrasing_dH": 0.5,
}


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
    """Iteration 4-7 seed: int(sha256('|'.join(parts))) mod 2^63 (used for every FIT key reused from a source)."""
    return int(hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest(), 16) % (2 ** 63)


def seed8(*parts: Any) -> int:
    """Iteration-8 seed: first 16 hex digits of sha256('|'.join(parts)) (new namespaces only)."""
    return int(hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()[:16], 16)


def u_from_seed(seed: int, n: int = U_LEN) -> np.ndarray:
    return np.random.Generator(np.random.PCG64(seed)).random(n)


def fit_seed(unit: str, w: str, slot: int) -> int:
    """FIT keys: the source artifact's twin keys (Qwen: iteration 7; Gemma: exp31); Llama: a new namespace."""
    u = UNITS[unit]
    fam = u["family"]
    if fam == "qwen":
        return stable_seed("iter7T", unit, w, slot)
    if fam == "gemma":
        return stable_seed("iter5E" if slot < 10 else "iter6S", u["task"], w, slot)
    return seed8(NS_FIT_L, FAMILIES[fam]["model_id"], unit, w, slot)


def sweep_seed(unit: str, w: str, slot: int) -> int:
    return seed8(NS_SWEEP, FAMILIES[UNITS[unit]["family"]]["model_id"], unit, w, slot)


def model_path(model_id: str, revision: str | None) -> str:
    cache = os.environ.get("HF_HUB_CACHE")
    if cache:
        snaps = Path(cache) / ("models--" + model_id.replace("/", "--")) / "snapshots"
        if revision and (snaps / revision).exists():
            return str(snaps / revision)
    return model_id


def _json_default(o: Any) -> Any:
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


def read_json(p: Path) -> Any:
    return json.loads(Path(p).read_text())


def write_json(p: Path, obj: Any) -> None:
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1, default=_json_default))
    tmp.replace(p)


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


def log_deviation(dev_id: str, text: str, severity: str = "minor") -> None:
    p = RESULTS_DIR / "deviations.json"
    cur = read_json(p) if p.exists() else []
    if any(d["id"] == dev_id for d in cur):
        return
    cur.append({"id": dev_id, "severity": severity, "text": text, "utc": utc_now()})
    write_json(p, cur)


def log_timing(stage: str, unit: str | None, n: int, seconds: float, **extra: Any) -> None:
    append_jsonl(TIMING, [{"utc": utc_now(), "stage": stage, "unit": unit, "n": n, "seconds": round(seconds, 2),
                           "per_item": round(seconds / max(n, 1), 4), **extra}])
