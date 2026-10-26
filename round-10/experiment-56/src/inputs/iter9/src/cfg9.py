#!/usr/bin/env python3
"""Iteration-9 BASE artifact (claims B1-B3) constants and utilities.

B1  base vs instruct teacher-forced at counterfactually located forks (Gemma-3-4b pt/it, Llama-3.1-8B base/instruct).
B2  cross-model activation patching (CMAP) in Qwen3-8B: base-model component outputs patched into the instruct model at
    the fork position; validated fork-stack (FSTACK) vs an exhaustive single-component sweep, 50 write-norm-matched
    random sets, the task-specification nodes and residual-stream swaps (upper bounds / localisation).
B3  rerun of iteration 8's held-out condition-node validation with an interpolating MeanCache.

Conventions:
- Fork position = the LAST input position (prompt + opening); its logits choose the decision token.
- Margin m = logsumexp(logits[D]) - logsumexp(logits[A]) in fp32 from the bf16 final-norm hidden state (D = the
  instruct model's default class tokens, A = the alternative class), i.e. log P(D) - log P(A) at T 1.
- share(X) = sum_p (m_I,p - m_X,p) / sum_p (m_I,p - m_B,p): the share of the instruct-minus-base margin gap that patching
  the base outputs of X into the instruct run closes (ratio of sums; the mean of per-prompt ratios is reported beside it).
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
VENDOR = ROOT / "vendor"
DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "results"
FIG_DIR = ROOT / "figures"
LOG_DIR = ROOT / "logs"
PRED_DIR = ROOT / "predictions"
CACHE_DIR = ROOT / "cache"
for _d in (DATA_DIR, RESULTS_DIR, FIG_DIR, LOG_DIR, PRED_DIR, CACHE_DIR):
    _d.mkdir(parents=True, exist_ok=True)
COMMITS = ROOT / "commitments.log"
GENESIS = hashlib.sha256(b"iter9_base").hexdigest()

# read-only prior artifacts on the run volume (copied into vendor/<artifact id>/ with sha256 by s0_preflight.py)
RUN = ROOT.parents[3]
ITER = RUN / "."
SRCS = {
    "art_18XvfcJJZi1O": ITER / "round-8" / "." / "experiment-41/src",
    "art_lzuosbrb34wB": ITER / "round-8" / "." / "experiment-43/src",
    "art_MZAfDPVhM6Ui": ITER / "round-7" / "." / "experiment-35/src",
    "art_pHL7LWNhpcCS": ITER / "round-7" / "." / "experiment-34/src",
    "art_vnyi0Fm5SyNH": ITER / "round-8" / "." / "experiment-39/src",
    "art_rMlbrjVB1c__": ITER / "round-6" / "." / "experiment-30/src",
    "art_zNyBP6zieI5u": ITER / "round-6" / "." / "experiment-31/src",
    "art_FJMIE9T9_PMv": ITER / "round-8" / "." / "experiment-42/src",
    "exp38": ITER / "round-7" / "." / "experiment-38/src",
    "art_j3Rm_lr2nzR6": RUN.parent / "run_4VFKidE1bxPG" / "." / "round-1" / "." / "dataset-1/src",
}
# portable resolution of every source artifact: ART_<ID>_DIR env var, else the published sibling folder ../<id>,
# else the original run layout above (only s0_preflight.py reads these; everything else reads vendor/)
for _k in list(SRCS):
    _env = os.environ.get(f"ART_{_k.upper()}_DIR")
    if _env:
        SRCS[_k] = Path(_env)
    elif (ROOT.parent / _k).exists():
        SRCS[_k] = ROOT.parent / _k
V41 = VENDOR / "art_18XvfcJJZi1O"
V43 = VENDOR / "art_lzuosbrb34wB"
V35 = VENDOR / "art_MZAfDPVhM6Ui"
V31 = VENDOR / "art_zNyBP6zieI5u"
V42 = VENDOR / "art_FJMIE9T9_PMv"
V38 = VENDOR / "exp38"

# ------------------------------------------------------------------------------------------------ models
MODELS = {
    "qwen": ("Qwen/Qwen3-8B", "b968826d9c46dd6066d109eabc6255188de91218"),
    "qwen_base": ("Qwen/Qwen3-8B-Base", "49e3418fbbbca6ecbdf9608b4d22e5a407081db4"),
    "gemma": ("google/gemma-3-4b-it", "093f9f388b31de276ce2de164bdc2081324b9767"),
    "gemma_pt": ("google/gemma-3-4b-pt", "cc012e0a6d0787b4adcc0fa2c4da74402494554d"),
    "llama": ("meta-llama/Llama-3.1-8B-Instruct", "0e9e39f249a16976918f6564b8830bc894c89659"),
    "llama_base": ("meta-llama/Llama-3.1-8B", "d04e592bb4f6aa9cfee91e2e20afa771667e1d4b"),
}
N_LAYERS = 36
N_HEADS = 32
HEAD_DIM = 128
D_MODEL = 4096
TEMPLATES = ("W1", "W2", "W3", "W4", "W5")

# ------------------------------------------------------------------------------------------------ design (commit #0)
FSTACK = ["mlp|L26", "mlp|L27", "mlp|L28", "mlp|L30", "mlp|L32",
          "head|L23|H10", "head|L27|H31", "head|L29|H6", "head|L33|H14", "head|L34|H28"]
SPEC_EMBEDDED = {"B3": ["mlp|L20", "mlp|L12", "mlp|L8", "mlp|L19", "mlp|L16"],
                 "T10": ["mlp|L13", "head|L11|H13", "mlp|L9", "head|L11|H14", "head|L14|H5"]}
RS_LAYERS = (4, 8, 12, 16, 20, 23, 26, 30)
RAND_BAND = (20, 35)
SPEC_RAND_BAND = (4, 24)
RAND_TOL = (0.70, 1.43)
RAND_TOL_WIDE = (0.5, 2.0)
N_RAND = 50
N_RAND_SPEC = 20
SEED_RAND = 90901
SEED_BOOT = 20261023
N_BOOT = 10000
Q_FORK = 0.90
NEAR_COLLAPSE = 0.85
LLAMA_CHAT_NORM_FRAC = 0.1
GEMMA_MASS_MIN = 0.01
ONPOLICY_MIN_LOGP = -5.0
NPOS = 64
TOPK = 256
ENGINE_TOL = 0.05
SELF_PATCH_TOL = 0.02
IDENTITY_TOL = 0.05
B3_TARGET_D = 8.29053352355957
B3_TOL_EXACT = 1e-3
B3_TOL_GPU = 0.05
STEER_DOSE = 2.0
STEER_DOSE_SENS = 0.5
BUDGET_MSG = "AI Inventor per-run OpenRouter budget"
OPENROUTER_CAP_USD = 0.20

THRESH = {
    "B1_P1_gain": 2.0, "B1_P2_dH": 0.5, "B1_P3_fork_vs_matched": 1.3, "B1_P3_random_vs_phrasing": 1.3,
    "B1_disconfirm_gain": 1.0,
    "B2_Q1_share": 0.5, "B2_Q2_median_random": 0.15, "B2_Q2_pctile": 95, "B2_Q3_spec": 0.15,
    "B2_disconfirm_share": 0.2, "B2_upstream_rs_prefix23": 0.5, "B2_late_rs_gap": 0.5,
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
    cache = os.environ.get("HF_HUB_CACHE")
    if cache:
        snap = Path(cache) / ("models--" + mid.replace("/", "--")) / "snapshots" / rev
        if snap.exists():
            return str(snap)
    return mid


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


def stage_time(stage: str, seconds: float, **extra: Any) -> None:
    append_jsonl(RESULTS_DIR / "stage_timing.jsonl", [{"stage": stage, "seconds": round(seconds, 1), "utc": utc_now(),
                                                       **extra}])


# ------------------------------------------------------------------------------------------------ commitment chain
def commit(name: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Write predictions/<name>.json, then append 'utc name file_sha256 link' to commitments.log where
    link = sha256(previous link + file_sha256) (genesis = sha256('iter9_base'))."""
    p = PRED_DIR / f"{name}.json"
    payload = dict(payload, commit_name=name, utc=utc_now())
    write_json(p, payload)
    fsha = sha256_file(p)
    prev = GENESIS
    if COMMITS.exists():
        lines = [ln for ln in COMMITS.read_text().splitlines() if ln.strip()]
        if lines:
            prev = lines[-1].split()[-1]
    link = sha256_text(prev + fsha)
    with open(COMMITS, "a") as fh:
        fh.write(f"{utc_now()} {name} {fsha} {link}\n")
    logger.info(f"COMMIT {name}: file sha256 {fsha[:16]}, link {link[:16]}")
    return {"name": name, "file_sha256": fsha, "link": link}


def verify_chain() -> dict[str, Any]:
    lines = [ln for ln in COMMITS.read_text().splitlines() if ln.strip()] if COMMITS.exists() else []
    prev = GENESIS
    out = {"n": len(lines), "commits": [], "all_links_ok": True, "all_hashes_ok": True}
    for ln in lines:
        utc, name, fsha, link = ln.split()
        ok_link = sha256_text(prev + fsha) == link
        p = PRED_DIR / f"{name}.json"
        ok_hash = p.exists() and sha256_file(p) == fsha
        out["commits"].append({"utc": utc, "name": name, "link_ok": ok_link, "hash_ok": ok_hash})
        out["all_links_ok"] &= ok_link
        out["all_hashes_ok"] &= ok_hash
        prev = link
    return out


def commit_utc(name: str) -> str | None:
    if not COMMITS.exists():
        return None
    for ln in COMMITS.read_text().splitlines():
        parts = ln.split()
        if len(parts) == 4 and parts[1] == name:
            return parts[0]
    return None
