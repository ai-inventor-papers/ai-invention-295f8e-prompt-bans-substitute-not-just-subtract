#!/usr/bin/env python3
"""Shared paths, logging, JSON/JSONL I/O, the hash-chained commitment log, deviations, the OpenRouter cost ledger,
the time ledger and partial status for NOV-R (iteration 10)."""
from __future__ import annotations

import fcntl
import hashlib
import json
import math
import os
import sys
import time
from pathlib import Path
from typing import Any, Iterable

from loguru import logger

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
DATA = ROOT / "data"
RESULTS = ROOT / "results"
PRED = ROOT / "predictions"
LOGS = ROOT / "logs"
FIGS = ROOT / "figures"
INPUTS = ROOT / "inputs"
COMMIT_LOG = PRED / "commitments.log"
GENESIS = hashlib.sha256(b"nov_r_iter10").hexdigest()
START_FILE = LOGS / "start_time.txt"
for _d in (DATA, RESULTS, PRED, LOGS, FIGS):
    _d.mkdir(parents=True, exist_ok=True)

BUDGET_MSG = "AI Inventor per-run OpenRouter budget"
COST_CAP_USD = float(os.environ.get("NOVR_COST_CAP", "5.0"))      # artifact hard cap (plan)
NEW_CELL_CAP_USD = 4.5                                             # no new cell starts above this


def setup_logging(name: str, level: str = "INFO") -> None:
    logger.remove()
    logger.add(sys.stdout, level=level, format="{time:HH:mm:ss}|{level:<7}|{message}")
    logger.add(LOGS / f"{name}.log", rotation="30 MB", level="DEBUG")


def utc_now() -> str:
    t = time.time()
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(t)) + f".{int((t % 1) * 1e6):06d}Z"


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with Path(p).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _json_default(o: Any) -> Any:
    try:
        import numpy as np
        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, np.floating):
            return None if not np.isfinite(o) else float(o)
        if isinstance(o, np.bool_):
            return bool(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
    except ImportError:
        pass
    if isinstance(o, (set, frozenset)):
        return sorted(o)
    if isinstance(o, Path):
        return str(o)
    if isinstance(o, bytes):
        return o.hex()
    raise TypeError(f"not JSON serialisable: {type(o)}")


def _clean(o: Any) -> Any:
    """Replace non-finite floats by None so the files are strict JSON."""
    if isinstance(o, float):
        return o if math.isfinite(o) else None
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    return o


def read_json(p: Path) -> Any:
    return json.loads(Path(p).read_text())


def write_json(p: Path, obj: Any, indent: int | None = 1) -> None:
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + f".tmp{os.getpid()}")
    tmp.write_text(json.dumps(_clean(json.loads(json.dumps(obj, default=_json_default))), indent=indent))
    tmp.replace(p)


def read_jsonl(p: Path) -> list[dict[str, Any]]:
    p = Path(p)
    if not p.exists():
        return []
    out = []
    for ln in p.read_text().splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            out.append(json.loads(ln))
        except json.JSONDecodeError:
            logger.warning(f"skipping corrupt JSONL line in {p.name}")
    return out


def append_jsonl(p: Path, row: dict[str, Any]) -> None:
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(_clean(json.loads(json.dumps(row, default=_json_default)))) + "\n"
    with p.open("a") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        fh.write(line)
        fh.flush()
        fcntl.flock(fh, fcntl.LOCK_UN)


def write_jsonl(p: Path, rows: Iterable[dict[str, Any]]) -> None:
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + f".tmp{os.getpid()}")
    with tmp.open("w") as fh:
        for r in rows:
            fh.write(json.dumps(_clean(json.loads(json.dumps(r, default=_json_default)))) + "\n")
    tmp.replace(p)


def trunc(s: Any, n: int = 300) -> str:
    s = str(s)
    return s if len(s) <= n else s[:n] + f"...[+{len(s) - n}]"


# ---------------------------------------------------------------------------------------------- commitments
def commit(payload_path: Path, label: str, note: str = "") -> dict[str, Any]:
    """Append {i, label, utc, prev_line_sha256, payload_sha256, payload_path, note} to predictions/commitments.log.
    Line 0 chains on GENESIS = sha256('nov_r_iter10'); every later line on the sha256 of the previous line's text."""
    payload_path = Path(payload_path)
    with (PRED / ".commit.lock").open("w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        lines = COMMIT_LOG.read_text().splitlines() if COMMIT_LOG.exists() else []
        if any(json.loads(ln)["label"] == label for ln in lines):
            raise RuntimeError(f"commit label {label} already used; amendments need a new label")
        prev = sha256_text(lines[-1]) if lines else GENESIS
        entry = {"i": len(lines), "label": label, "utc": utc_now(), "prev_line_sha256": prev,
                 "payload_sha256": sha256_file(payload_path), "payload_path": str(payload_path.relative_to(ROOT)),
                 "note": note}
        with COMMIT_LOG.open("a") as fh:
            fh.write(json.dumps(entry, sort_keys=True) + "\n")
        fcntl.flock(lk, fcntl.LOCK_UN)
    logger.info(f"COMMIT {label}: {entry['payload_path']} sha256={entry['payload_sha256'][:16]} line {entry['i']}")
    return entry


def verify_chain() -> tuple[bool, list[str], list[dict[str, Any]]]:
    problems: list[str] = []
    if not COMMIT_LOG.exists():
        return False, ["no commitments.log"], []
    prev = GENESIS
    entries = []
    for i, ln in enumerate(COMMIT_LOG.read_text().splitlines()):
        e = json.loads(ln)
        entries.append(e)
        if e["prev_line_sha256"] != prev:
            problems.append(f"line {i}: prev-line hash mismatch")
        p = ROOT / e["payload_path"]
        if not p.exists():
            problems.append(f"line {i}: payload missing {e['payload_path']}")
        elif sha256_file(p) != e["payload_sha256"]:
            problems.append(f"line {i}: payload hash mismatch {e['payload_path']}")
        prev = sha256_text(ln)
    return (not problems, problems, entries)


def commit_time(label: str) -> str | None:
    if not COMMIT_LOG.exists():
        return None
    for ln in COMMIT_LOG.read_text().splitlines():
        e = json.loads(ln)
        if e["label"] == label:
            return e["utc"]
    return None


# ---------------------------------------------------------------------------------------------- deviations, costs
def deviation(code: str, text: str) -> None:
    p = RESULTS / "deviations.json"
    with (RESULTS / ".dev.lock").open("w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        devs = json.loads(p.read_text()) if p.exists() else []
        if not any(d["code"] == code for d in devs):
            devs.append({"code": code, "text": text, "utc": utc_now(), "elapsed_h": round(elapsed_h(), 3)})
            write_json(p, devs)
            logger.warning(f"DEVIATION {code}: {text}")
        fcntl.flock(lk, fcntl.LOCK_UN)


COST_FILE = RESULTS / "costs.json"


def add_cost(purpose: str, usd: float, refused: bool = False, estimated: bool = False) -> float:
    """Running ledger shared by every process of this artifact (file-locked)."""
    with (RESULTS / ".cost.lock").open("w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        c = json.loads(COST_FILE.read_text()) if COST_FILE.exists() else {
            "total_usd": 0.0, "by_purpose": {}, "n_calls": 0, "budget_refusals": 0, "estimated_usd": 0.0}
        c["total_usd"] = round(c["total_usd"] + float(usd or 0.0), 7)
        c["by_purpose"][purpose] = round(c["by_purpose"].get(purpose, 0.0) + float(usd or 0.0), 7)
        c["n_calls"] += 1
        c["budget_refusals"] += int(refused)
        if estimated:
            c["estimated_usd"] = round(c.get("estimated_usd", 0.0) + float(usd or 0.0), 7)
        c["updated_utc"] = utc_now()
        write_json(COST_FILE, c)
        fcntl.flock(lk, fcntl.LOCK_UN)
        return c["total_usd"]


def total_cost() -> float:
    try:
        return float(read_json(COST_FILE)["total_usd"]) if COST_FILE.exists() else 0.0
    except (json.JSONDecodeError, KeyError):
        return 0.0


# ---------------------------------------------------------------------------------------------- time ledger
def start_epoch() -> float:
    try:
        s = START_FILE.read_text().split()[1]
        return time.mktime(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ")) - time.timezone
    except (FileNotFoundError, IndexError, ValueError):
        return time.time()


def elapsed_h() -> float:
    return (time.time() - start_epoch()) / 3600.0


def milestone(name: str, **kw: Any) -> None:
    append_jsonl(LOGS / "time_ledger.jsonl", {"milestone": name, "utc": utc_now(), "elapsed_h": round(elapsed_h(), 3),
                                              **kw})
    logger.info(f"MILESTONE {name} at {elapsed_h():.2f} h")


def partial_status(update: dict[str, Any]) -> None:
    p = RESULTS / "partial_status.json"
    with (RESULTS / ".status.lock").open("w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        st = json.loads(p.read_text()) if p.exists() else {}
        st.update(update)
        st["updated_utc"] = utc_now()
        st["elapsed_h"] = round(elapsed_h(), 3)
        write_json(p, st)
        fcntl.flock(lk, fcntl.LOCK_UN)


def timing(key: str, seconds: float, units: int, note: str = "") -> None:
    append_jsonl(RESULTS / "timing.jsonl", {"key": key, "seconds": round(seconds, 2), "units": units,
                                            "sec_per_unit": round(seconds / max(units, 1), 3), "note": note,
                                            "utc": utc_now()})


# ---------------------------------------------------------------------------------------------- hardware
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
    for p in ["/sys/fs/cgroup/memory.max", "/sys/fs/cgroup/memory/memory.limit_in_bytes"]:
        try:
            v = Path(p).read_text().strip()
            if v != "max" and int(v) < 1_000_000_000_000:
                return int(v) / 1e9
        except (FileNotFoundError, ValueError):
            pass
    return None
