#!/usr/bin/env python3
"""Iteration-10 BASE-W artifact: constants, paths and shared utilities.

Question: where did post-training write Qwen3-8B's default at the algorithm fork, at the level of WEIGHTS?
  W1  readout rows: the fork-class unembedding rows (and the final-norm gain) of the base model swapped into the
      instruct readout of the instruct residual (exact CPU readout on cached fork states), against 3 x 50 matched
      random-row nulls; then generation with 30 common-random-number slots per arm.
  W2  late-MLP weights (layers 26-35) swapped to base in place (all-position and fork-only scopes), against
      Frobenius-matched early swaps (Hungarian matched, layers 2-13) and same-layer random deltas.
  W3  the W1 row test at Gemma-3-4b's grid fork (descriptive).

Conventions (as iteration 9):
- Fork position = the LAST input position (prompt + opening); its logits choose the decision token.
- Margin m = lse(z[D]) - lse(z[A]) in fp32 from the bf16 final-norm hidden state, D = the instruct default class
  tokens, A = the alternative class tokens (= log P(D) - log P(A) at T 1).
- share(X) = sum_p (m_I,p - m_X,p) / sum_p (m_I,p - m_B,p) (ratio of sums, primary).
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import resource
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from loguru import logger

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
INPUTS = ROOT / "inputs"
I9 = INPUTS / "iter9"                       # verbatim copy of iteration 9's artifact (results, data, vendor, src)
I9_SRC = I9 / "src"                         # vendored iteration-9 code (imported, never edited)
I9_RES = I9 / "results"
I9_VENDOR = I9 / "vendor"
V41 = I9_VENDOR / "art_18XvfcJJZi1O"        # frozen CC/MST labeller tree (label_k3.py + hidden tests)
V43 = I9_VENDOR / "art_lzuosbrb34wB"
DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "results"
FIG_DIR = ROOT / "figures"
LOG_DIR = ROOT / "logs"
PRED_DIR = ROOT / "predictions"
CACHE_DIR = ROOT / "cache"
for _d in (DATA_DIR, RESULTS_DIR, FIG_DIR, LOG_DIR, PRED_DIR, CACHE_DIR):
    _d.mkdir(parents=True, exist_ok=True)
COMMITS = ROOT / "commitments.log"
GENESIS = hashlib.sha256(b"iter10_basew").hexdigest()

# read-only source of the iteration-9 artifact (only inputs10.py reads it; everything else reads inputs/iter9)
ITER9 = Path(os.environ.get("ART_CDBA8_DIR", str(Path(__file__).resolve().parents[5] / "round-9/experiment-50/src")))
DEP_DATASET = Path(os.environ.get("ART_J3RM_DIR", str(Path(__file__).resolve().parents[5] / "round-1/dataset-1/src")))

# ------------------------------------------------------------------------------------------------ models
MODELS = {
    "qwen": ("Qwen/Qwen3-8B", "b968826d9c46dd6066d109eabc6255188de91218"),
    "qwen_base": ("Qwen/Qwen3-8B-Base", "49e3418fbbbca6ecbdf9608b4d22e5a407081db4"),
    "gemma": ("google/gemma-3-4b-it", "093f9f388b31de276ce2de164bdc2081324b9767"),
    "gemma_pt": ("google/gemma-3-4b-pt", "cc012e0a6d0787b4adcc0fa2c4da74402494554d"),
}
N_LAYERS = 36
D_MODEL = 4096
D_FF = 12288
VOCAB = 151936
RMS_EPS = 1e-6
EOS_IDS = (151645, 151643)
TEMPLATES = ("W1", "W2", "W3", "W4", "W5")

# ------------------------------------------------------------------------------------------------ design
UNITS_TF = ("T10", "B3")                    # T10 = connected components (primary), B3 = MST (beside)
UNIT_IDX = {"T10": 0, "B3": 1, "G-GRID": 2}
B_OT_CANDIDATES = (40, 24, 16, 8)           # one-token batch shapes tried in S0 (iteration 9 used 40)
CHUNK_ROWS = 8192                           # vocabulary rows per chunk for fp32 full-vocabulary readouts
DOSES = (0.25, 0.5, 0.75, 1.0, 1.25, 1.5)
SIGN_DOSE = -1.0
N_NULL = 50
NULL_TYPES = ("RAND_ISO", "DELTA_SWAP", "RAND_RESID")
NULL_SEED0 = {"RAND_ISO": 101000, "RAND_RESID": 102000, "DELTA_SWAP": 103000}
RANDDELTA_SEED0 = 104000
N_RANDDELTA = 3
RESID_PCS = 64
DELTA_SWAP_TOL_DELTA = 0.05                 # ||Delta_s|| within +-5% of ||Delta_t||
DELTA_SWAP_TOL_W = 0.10                     # ||w_I,s|| within +-10% of ||w_I,t||
DELTA_SWAP_EXCLUDE = {"T10": ("find", "dfs", "bfs", "union", "kr", "prim", "mst"),
                      "B3": ("find", "dfs", "bfs", "union", "kr", "prim", "mst", "check", "minimum", "priority",
                             "helper", "dis", "pr", "use", "to", "using", "prime"),
                      "G-GRID": ("visited", "queue", "dfs", "bfs", "stack", "find", "union", "kr", "prim", "mst")}
SEED_BOOT = 20261024
N_BOOT = 10000
SMALL_GAP = 0.5
LATE = tuple(range(26, 36))
EARLY_POOL = tuple(range(2, 14))
ITER9_W_LAYERS = (26, 27, 28, 30, 32)

# generation (iteration-9 CRN engine)
SEED0 = 9101
SLOTS_PER_T = 6
MAX_NEW = {"B3": 768, "T10": 1024}
GEN_B = 6
GEN_ARMS = ("TWIN", "ROWS", "RAND_MED", "RAND_MAX", "RAND_0", "FPD", "ROWS_ALLSTEPS", "FULL_UNEMB_FORK")
CORRECT = {"T10": {"dfs"}, "B3": {"prim_heap", "prim_array"}}
MINORITY = {"T10": {"dfs", "bfs"}, "B3": {"prim_heap", "prim_array"}}
FULL_UNEMB_TV = 0.05

THRESH = {
    "W1_rows_share": 0.50, "W1_rand_iso_median": 0.15, "W1_disconfirm": 0.20,
    "W1GEN_rows_min_correct": 10, "W1GEN_rand_max_correct": 3, "W1GEN_alpha": 0.05,
    "W2_late_minus_early": 0.15,
    "S0_mean_tol": 0.05, "S0_prompt_tol_B40": 0.05, "S0_prompt_tol_small_B": 0.10, "S0_spearman": 0.99,
    "S0_decomp_tol": 0.03, "S0_decomp_target": {"T10": 0.85, "B3": 0.43},
    "W2_bridge_tol": 0.05, "labeller_gate": 0.99, "G1_rel_err": 2e-3,
}
BUDGET_MSG = "AI Inventor per-run OpenRouter budget"
OPENROUTER_CAP_USD = 0.30


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


def container_ram_gb() -> float | None:
    for p in ("/sys/fs/cgroup/memory.max", "/sys/fs/cgroup/memory/memory.limit_in_bytes"):
        try:
            v = Path(p).read_text().strip()
            if v != "max" and int(v) < 1_000_000_000_000:
                return int(v) / 1e9
        except (FileNotFoundError, ValueError):
            pass
    return None


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
    return sha256_text(json.dumps([int(i) for i in ids]))


def model_path(key: str) -> str:
    mid, rev = MODELS[key]
    cache = os.environ.get("HF_HUB_CACHE") or (Path(os.environ.get("HF_HOME", Path.home() / ".cache/huggingface"))
                                               / "hub")
    snap = Path(cache) / ("models--" + mid.replace("/", "--")) / "snapshots" / rev
    if snap.exists():
        return str(snap)
    raise FileNotFoundError(f"{mid}@{rev} not in the HF cache; run scripts/download_models.sh")


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
    if isinstance(o, tuple):
        return list(o)
    raise TypeError(f"not JSON serialisable: {type(o)}")


def clean_nan(o: Any) -> Any:
    if isinstance(o, float):
        return o if math.isfinite(o) else None
    if isinstance(o, dict):
        return {k: clean_nan(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean_nan(v) for v in o]
    return o


def read_json(p: Path) -> Any:
    return json.loads(Path(p).read_text())


def write_json(p: Path, obj: Any) -> None:
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(clean_nan(obj), indent=1, default=_json_default))
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
            fh.write(json.dumps(clean_nan(r), default=_json_default) + "\n")
        fh.flush()


def write_jsonl(p: Path, rows: Iterable[dict[str, Any]]) -> None:
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    with open(tmp, "w") as fh:
        for r in rows:
            fh.write(json.dumps(clean_nan(r), default=_json_default) + "\n")
    tmp.replace(p)


def log_deviation(dev_id: str, text: str, severity: str = "minor") -> None:
    p = RESULTS_DIR / "deviations.json"
    cur = read_json(p) if p.exists() else []
    if any(d["id"] == dev_id for d in cur):
        return
    cur.append({"id": dev_id, "severity": severity, "text": text, "utc": utc_now()})
    write_json(p, cur)
    logger.warning(f"DEVIATION {dev_id}: {text}")


def ledger(milestone: str, **extra: Any) -> None:
    """logs/time_ledger.jsonl: one line per milestone."""
    append_jsonl(LOG_DIR / "time_ledger.jsonl", [{"milestone": milestone, "utc": utc_now(), "unix": time.time(),
                                                  **extra}])


def partial_status(stage: str, **extra: Any) -> None:
    p = RESULTS_DIR / "partial_status.json"
    cur = read_json(p) if p.exists() else {"stages": {}}
    cur["stages"][stage] = {"utc": utc_now(), **extra}
    cur["last_update"] = utc_now()
    write_json(p, cur)


# ------------------------------------------------------------------------------------------------ commitment chain
def commit(name: str, payload: dict[str, Any] | None = None, files: list[Path] | None = None) -> dict[str, Any]:
    """Hash-chained pre-registration. Writes predictions/<name>.json (if payload), then appends one line per file to
    commitments.log: 'utc | relative path | sha256(file) | link' with link = sha256(previous link + ' ' + this line's
    path and file sha) and genesis = sha256('iter10_basew')."""
    paths: list[Path] = []
    if payload is not None:
        p = PRED_DIR / f"{name}.json"
        write_json(p, dict(payload, commit_name=name, utc=utc_now()))
        paths.append(p)
    paths += [Path(f) for f in (files or [])]
    prev = GENESIS
    if COMMITS.exists():
        lines = [ln for ln in COMMITS.read_text().splitlines() if ln.strip()]
        if lines:
            prev = lines[-1].split(" | ")[-1].strip()
    out = []
    with open(COMMITS, "a") as fh:
        for p in paths:
            rel = str(Path(p).resolve().relative_to(ROOT))
            fsha = sha256_file(p)
            link = sha256_text(prev + " " + rel + " " + fsha)
            fh.write(f"{utc_now()} | {name}:{rel} | {fsha} | {link}\n")
            prev = link
            out.append({"path": rel, "sha256": fsha, "link": link})
    logger.info(f"COMMIT {name}: {len(out)} file(s), last link {prev[:16]}")
    return {"name": name, "entries": out, "last_link": prev}


def verify_chain() -> dict[str, Any]:
    lines = [ln for ln in COMMITS.read_text().splitlines() if ln.strip()] if COMMITS.exists() else []
    prev = GENESIS
    out = {"n": len(lines), "all_links_ok": True, "all_hashes_ok": True, "bad": []}
    for ln in lines:
        utc, tag, fsha, link = [x.strip() for x in ln.split(" | ")]
        rel = tag.split(":", 1)[1]
        ok_link = sha256_text(prev + " " + rel + " " + fsha) == link
        p = ROOT / rel
        ok_hash = p.exists() and sha256_file(p) == fsha
        if not (ok_link and ok_hash):
            out["bad"].append({"line": tag, "link_ok": ok_link, "hash_ok": ok_hash})
        out["all_links_ok"] &= ok_link
        out["all_hashes_ok"] &= ok_hash
        prev = link
    return out


def commit_utc(name: str) -> str | None:
    if not COMMITS.exists():
        return None
    for ln in COMMITS.read_text().splitlines():
        parts = [x.strip() for x in ln.split(" | ")]
        if len(parts) == 4 and parts[1].split(":", 1)[0] == name:
            return parts[0]
    return None


def import_iter9() -> None:
    """Put the vendored iteration-9 code (inputs/iter9/src) on sys.path; its cfg9 resolves ROOT = inputs/iter9."""
    p = str(I9_SRC)
    if p not in sys.path:
        sys.path.insert(0, p)
