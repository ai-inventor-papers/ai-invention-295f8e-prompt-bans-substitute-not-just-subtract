#!/usr/bin/env python3
"""Shared paths, constants and helpers for the evolutionary-search artifact (iteration 7, claim N).

Conventions:
- ROOT = this workspace. Every read of another artifact goes through RUNS_DIR-relative source paths (env override
  AII_RUNS_DIR), and is copied byte-for-byte into inputs/vendor/ by src/inputs.py before anything uses it.
- One call = one child program (one generated completion that should hold one ```python block).
- Arms: S (full search), NE (no-evolution ablation), I0 (instruction only), EAP / BINT (iteration-5 text knobs),
  B0 (neutral twin), CAL (forced calibration pool, non-decisive), ENG (engine check, non-decisive), L (large mutator).
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
INPUTS = ROOT / "inputs"
VENDOR = INPUTS / "vendor"
DATA = ROOT / "data"
RAW = DATA / "raw"
RESULTS = ROOT / "results"
FIGS = ROOT / "figures"
PRED = ROOT / "predictions"
AUDIT = ROOT / "audit"
LOGS = ROOT / "logs"
COMMITS = ROOT / "commitments.log"
for _d in (INPUTS, VENDOR, DATA, RAW, RESULTS, FIGS, PRED, AUDIT, LOGS):
    _d.mkdir(parents=True, exist_ok=True)

# <runs>/<run>/3_invention_loop/iter_7/gen_art/<this artifact>
RUNS_DIR = Path(os.environ.get("AII_RUNS_DIR", str(ROOT.parents[4])))
DEP_REL = "run_4VFKidE1bxPG/3_invention_loop/iter_1/gen_art/gen_art_dataset_1"  # declared dependency art_j3Rm_lr2nzR6
_DEP_SIBLING = ROOT.parent / "art_j3Rm_lr2nzR6"   # the published repository holds the dependency as a sibling folder
DEP_DIR = Path(os.environ.get("ART_J3RM_DIR") or (str(_DEP_SIBLING) if _DEP_SIBLING.exists() else str(RUNS_DIR / DEP_REL)))

# read-only sources of the non-declared items (vendored once at STEP 1; paths relative to RUNS_DIR)
VENDOR_SOURCES: dict[str, str] = {
    "bench": "run_0oWBKrKEGsmU/3_invention_loop/iter_6/gen_art/gen_art_experiment_29/vendor/exp22/inputs/exp11/bench",
    "exp8_suite": "run_0oWBKrKEGsmU/3_invention_loop/iter_6/gen_art/gen_art_experiment_30/inputs/exp8/suite",
    "exp30_src": "run_0oWBKrKEGsmU/3_invention_loop/iter_6/gen_art/gen_art_experiment_30/src",
    "newbench": "run_aRfWvcSWjssb/3_invention_loop/iter_5/gen_art/gen_art_experiment_25/newbench",
    "exp27": "run_aRfWvcSWjssb/3_invention_loop/iter_5/gen_art/gen_art_experiment_27",
    "exp29_results": "run_0oWBKrKEGsmU/3_invention_loop/iter_6/gen_art/gen_art_experiment_29/results",
    "B7": "run_aRfWvcSWjssb/3_invention_loop/iter_5/gen_art/gen_art_experiment_26/units/B7",
}

# ------------------------------------------------------------------------------------------------ model / decoding
MODEL_ID = "Qwen/Qwen3-8B"
MODEL_REV = "b968826d9c46dd6066d109eabc6255188de91218"
BASE_ID = "Qwen/Qwen3-8B-Base"
BASE_REV = "49e3418fbbbca6ecbdf9608b4d22e5a407081db4"
TEMPERATURE = 1.0
TOP_P = 1.0
MAX_TOKENS = {"T2": 1536, "T03": 1024, "A3": 1024}
VLLM_SEED = 7101
TASKS = ("T2", "T03", "A3")
BUDGET_MSG = "AI Inventor per-run OpenRouter budget"
CAP_USD = {"label_disputes": 0.5, "adjudication": 1.8, "L": 1.0, "reserve": 0.2}
CAP_TOTAL_USD = 3.5

ARMS_DECISIVE = ("S", "NE", "I0", "EAP", "BINT", "B0")


# ------------------------------------------------------------------------------------------------ logging
def setup_logging(name: str) -> None:
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    logger.add(str(LOGS / f"{name}.log"), rotation="30 MB", level="DEBUG")


def trunc(s: Any, n: int = 300) -> str:
    s = str(s)
    return s if len(s) <= n else s[:n] + f"...[+{len(s) - n}]"


# ------------------------------------------------------------------------------------------------ io
def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with Path(p).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(p: Path) -> Any:
    return json.loads(Path(p).read_text())


def write_json(p: Path, obj: Any, indent: int | None = 1) -> None:
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=indent, default=_json_default))
    tmp.replace(p)


def _json_default(o: Any) -> Any:
    try:
        import numpy as np
        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, np.floating):
            return float(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
    except ImportError:
        pass
    if isinstance(o, (set, tuple)):
        return list(o)
    if isinstance(o, Path):
        return str(o)
    raise TypeError(f"not JSON serialisable: {type(o)}")


def read_jsonl(p: Path) -> list[dict[str, Any]]:
    p = Path(p)
    if not p.exists():
        return []
    out = []
    with p.open() as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    logger.warning(f"skipping a corrupt line in {p.name}")
    return out


def append_jsonl(p: Path, rows: Iterable[dict[str, Any]]) -> None:
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a") as f:
        for r in rows:
            f.write(json.dumps(r, default=_json_default) + "\n")


def write_jsonl(p: Path, rows: Iterable[dict[str, Any]]) -> None:
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    with tmp.open("w") as f:
        for r in rows:
            f.write(json.dumps(r, default=_json_default) + "\n")
    tmp.replace(p)


def stable_seed(*parts: Any) -> int:
    """sha256(task|arm|index) mod 2^31: the per-request vLLM seed and every external RNG seed."""
    return int(hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest(), 16) % (2 ** 31)


def rel(p: Path) -> str:
    """Workspace-relative POSIX path (never an absolute server path in published files)."""
    try:
        return Path(p).resolve().relative_to(ROOT).as_posix()
    except ValueError:
        try:
            return "<runs>/" + Path(p).resolve().relative_to(RUNS_DIR.resolve()).as_posix()
        except ValueError:
            return Path(p).name


# ------------------------------------------------------------------------------------------------ hardware
def detect_cpus() -> int:
    try:
        parts = Path("/sys/fs/cgroup/cpu.max").read_text().split()
        if parts[0] != "max":
            return math.ceil(int(parts[0]) / int(parts[1]))
    except (FileNotFoundError, ValueError, IndexError):
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


def container_ram_gb() -> float | None:
    for p in ("/sys/fs/cgroup/memory.max", "/sys/fs/cgroup/memory/memory.limit_in_bytes"):
        try:
            v = Path(p).read_text().strip()
            if v != "max" and int(v) < 1_000_000_000_000:
                return int(v) / 1e9
        except (FileNotFoundError, ValueError):
            pass
    return None


def set_ram_limit(gb: float) -> None:
    """Hard address-space cap so a runaway allocation raises MemoryError instead of an OOM kill."""
    b = int(gb * 1024 ** 3)
    resource.setrlimit(resource.RLIMIT_AS, (b, b))


# ------------------------------------------------------------------------------------------------ commitments
def commit(files: list[Path], tag: str, note: str = "") -> str:
    """Hash chain: each line = sha256(file) + sha256(previous line) + UTC (+ tag, file). Returns the last line hash."""
    COMMITS.touch(exist_ok=True)
    lines = [ln for ln in COMMITS.read_text().splitlines() if ln.strip()]
    prev = sha256_text(lines[-1]) if lines else "0" * 64
    new = []
    for f in files:
        rec = {"tag": tag, "file": rel(f), "sha256": sha256_file(f), "prev": prev, "utc": utc_now(), "note": note}
        line = json.dumps(rec, sort_keys=True)
        new.append(line)
        prev = sha256_text(line)
    with COMMITS.open("a") as fh:
        for ln in new:
            fh.write(ln + "\n")
    logger.info(f"commit {tag}: {len(files)} file(s), chain head {prev[:12]}")
    return prev


def verify_chain() -> dict[str, Any]:
    lines = [ln for ln in COMMITS.read_text().splitlines() if ln.strip()] if COMMITS.exists() else []
    prev = "0" * 64
    ok = True
    bad = []
    for i, ln in enumerate(lines):
        rec = json.loads(ln)
        if rec["prev"] != prev:
            ok = False
            bad.append(i)
        prev = sha256_text(ln)
        f = ROOT / rec["file"]
        if f.exists() and sha256_file(f) != rec["sha256"]:
            # a committed file may only change through a NEW commit line (amendment); the latest line must match
            later = [json.loads(x) for x in lines[i + 1:] if json.loads(x)["file"] == rec["file"]]
            if not later:
                ok = False
                bad.append(i)
    return {"n_lines": len(lines), "ok": ok, "bad_lines": bad, "head": prev}
