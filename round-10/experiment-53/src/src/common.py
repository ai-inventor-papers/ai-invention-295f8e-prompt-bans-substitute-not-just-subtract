"""Shared paths, logging, hashing, JSONL, hardware and commitment helpers for NOV-T (iteration 10)."""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RESULTS = ROOT / "results"
LOGS = ROOT / "logs"
FIGS = ROOT / "figures"
PRED = ROOT / "predictions"
for _d in (DATA, RESULTS, LOGS, FIGS, PRED, DATA / "instances", DATA / "db"):
    _d.mkdir(parents=True, exist_ok=True)

# Every evaluator / numeric process must be single-threaded (the cgroup CPU quota is ~5 cores).
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

T0_FILE = LOGS / "t0_utc.txt"


def setup_logging(name: str = "run"):
    from loguru import logger

    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    logger.add(str(LOGS / f"{name}.log"), rotation="30 MB", level="DEBUG")
    return logger


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def elapsed_h() -> float:
    """Hours since the module start (logs/t0_utc.txt)."""
    try:
        t0 = time.mktime(time.strptime(T0_FILE.read_text().strip(), "%Y-%m-%dT%H:%M:%SZ")) - time.timezone
    except (FileNotFoundError, ValueError):
        return float("nan")
    return (time.time() - t0) / 3600.0


def ledger(milestone: str, **extra) -> None:
    """Append a milestone with UTC and elapsed hours to logs/time_ledger.jsonl."""
    append_jsonl(LOGS / "time_ledger.jsonl", {"utc": utc_now(), "elapsed_h": round(elapsed_h(), 4),
                                               "milestone": milestone, **extra})


def _json_default(o):
    import numpy as np

    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        v = float(o)
        return v if math.isfinite(v) else None
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (set, frozenset)):
        return sorted(o)
    if isinstance(o, Path):
        return str(o.relative_to(ROOT)) if str(o).startswith(str(ROOT)) else str(o)
    raise TypeError(f"not JSON serialisable: {type(o)}")


def clean_nan(o):
    """Recursively replace non-finite floats by None (strict JSON)."""
    if isinstance(o, float):
        return o if math.isfinite(o) else None
    if isinstance(o, dict):
        return {k: clean_nan(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean_nan(v) for v in o]
    return o


def write_json(p: Path, obj, indent: int | None = 2) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(clean_nan(_to_builtin(obj)), indent=indent, allow_nan=False))
    tmp.replace(p)


def _to_builtin(o):
    import numpy as np

    if isinstance(o, dict):
        return {str(k): _to_builtin(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_to_builtin(v) for v in o]
    if isinstance(o, (set, frozenset)):
        return sorted(_to_builtin(v) for v in o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.ndarray):
        return _to_builtin(o.tolist())
    if isinstance(o, Path):
        return _json_default(o)
    return o


def append_jsonl(p: Path, row: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a") as f:
        f.write(json.dumps(clean_nan(_to_builtin(row)), allow_nan=False) + "\n")


def read_jsonl(p: Path) -> list[dict]:
    if not p.exists():
        return []
    out = []
    with open(p) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue  # a torn last line after a kill; the row is re-done on resume
    return out


def detect_cpus() -> float:
    try:
        q = int(Path("/sys/fs/cgroup/cpu/cpu.cfs_quota_us").read_text())
        p = int(Path("/sys/fs/cgroup/cpu/cpu.cfs_period_us").read_text())
        if q > 0:
            return q / p
    except (FileNotFoundError, ValueError):
        pass
    try:
        parts = Path("/sys/fs/cgroup/cpu.max").read_text().split()
        if parts[0] != "max":
            return int(parts[0]) / int(parts[1])
    except (FileNotFoundError, ValueError):
        pass
    return float(len(os.sched_getaffinity(0)))


def container_ram_bytes() -> int | None:
    for p in ["/sys/fs/cgroup/memory/memory.limit_in_bytes", "/sys/fs/cgroup/memory.max"]:
        try:
            v = Path(p).read_text().strip()
            if v != "max" and int(v) < 1_000_000_000_000:
                return int(v)
        except (FileNotFoundError, ValueError):
            pass
    return None


def container_ram_used() -> int | None:
    for p in ["/sys/fs/cgroup/memory/memory.usage_in_bytes", "/sys/fs/cgroup/memory.current"]:
        try:
            return int(Path(p).read_text().strip())
        except (FileNotFoundError, ValueError):
            pass
    return None


# ------------------------------------------------------------------ hash-chained commitments
COMMIT_LOG = ROOT / "commitments.log"


def commit_files(label: str, files: list[Path]) -> list[str]:
    """Append one hash-chained line per file: UTC, label, file, sha256(file), sha256(previous line)."""
    lines = COMMIT_LOG.read_text().splitlines() if COMMIT_LOG.exists() else []
    prev = lines[-1] if lines else "GENESIS"
    new = []
    for f in files:
        rel = str(Path(f).resolve().relative_to(ROOT))
        line = f"{utc_now()}\t{label}\t{rel}\t{sha256_file(Path(f))}\t{sha256_text(prev)}"
        new.append(line)
        prev = line
    with open(COMMIT_LOG, "a") as fh:
        for line in new:
            fh.write(line + "\n")
    return new


def verify_commit_chain() -> dict:
    """Check every line's previous-line hash; report the files whose current hash differs from the commit."""
    if not COMMIT_LOG.exists():
        return {"ok": False, "reason": "no commitments.log"}
    lines = COMMIT_LOG.read_text().splitlines()
    prev, ok, changed = "GENESIS", True, []
    for line in lines:
        parts = line.split("\t")
        if len(parts) != 5 or parts[4] != sha256_text(prev):
            ok = False
        p = ROOT / parts[2]
        if p.exists() and sha256_file(p) != parts[3]:
            changed.append({"file": parts[2], "label": parts[1], "utc": parts[0]})
        prev = line
    return {"ok": ok, "n_lines": len(lines), "changed_since_commit": changed}
