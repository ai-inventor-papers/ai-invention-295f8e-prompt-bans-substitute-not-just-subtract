#!/usr/bin/env python3
"""Shared I/O for the iteration-10 S0 record repair: dependency resolution, JSON helpers, checkpointing.

Published files cite inputs as '<artifact_id>:<relative path>#<key>'. Resolved absolute paths live only in the
untracked .env file (listed in .gitignore).
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from loguru import logger

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
TABLES = ROOT / "tables"
FIGURES = ROOT / "figures"
INPUTS = ROOT / "inputs"
VENDOR = ROOT / "vendor"
LOGS = ROOT / "logs"
for _d in (RESULTS, TABLES, FIGURES, INPUTS, VENDOR, LOGS):
    _d.mkdir(parents=True, exist_ok=True)

# the three declared dependencies; their roots come from $AII_DEPS_ROOT/<id>, a sibling folder named by the id, or
# the DEP_<id> lines of the untracked .env (written once by the operator; see reproducibility.md)
DEPS = ("art_8nXdw3_lDAll", "art_VVA3P0ocZNA2", "art_cDba8_DycUJd")
REPORT_ID = "report"
A_REN, A_GEO, A_BASE = "art_8nXdw3_lDAll", "art_VVA3P0ocZNA2", "art_cDba8_DycUJd"


def setup_logging(stage: str) -> None:
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|" + stage + "|{message}")
    logger.add(str(LOGS / "run.log"), rotation="30 MB", level="DEBUG",
               format="{time:YYYY-MM-DD HH:mm:ss}|{level:<7}|" + stage + "|{message}")


def env_value(key: str) -> str | None:
    """A location from the environment or the untracked .env file (never from published code)."""
    return os.environ.get(key) or _env_file().get(key)


def _env_file() -> dict[str, str]:
    p = ROOT / ".env"
    out: dict[str, str] = {}
    if p.exists():
        for line in p.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip()
    return out


def dep_root(art: str) -> Path:
    """env AII_DEPS_ROOT/<artifact_id>, then a sibling folder named by the artifact id, then the given path."""
    env = os.environ.get("AII_DEPS_ROOT") or _env_file().get("AII_DEPS_ROOT")
    cands = []
    if env:
        cands.append(Path(env) / art)
    cands.append(ROOT.parent / art)
    if _env_file().get(f"DEP_{art}"):
        cands.append(Path(_env_file()[f"DEP_{art}"]))
    for c in cands:
        if c.exists():
            return c
    raise FileNotFoundError(f"dependency {art} not found in {cands}")


def dep_path(art: str, rel: str) -> Path:
    """Copied small inputs are read from inputs/<artifact_id>/ when present; else in place from the dependency."""
    local = INPUTS / art / rel
    if local.exists():
        return local
    return dep_root(art) / rel


def ref(art: str, rel: str, key: str = "") -> str:
    return f"{art}:{rel}" + (f"#{key}" if key else "")


def read_json(p: Path | str) -> Any:
    return json.loads(Path(p).read_text())


def read_jsonl(p: Path | str) -> list[dict[str, Any]]:
    out = []
    with open(p) as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def write_json(p: Path | str, obj: Any) -> None:
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1, default=_default))
    tmp.replace(p)


def _default(o: Any) -> Any:
    try:
        import numpy as np
        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, np.floating):
            return float(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
        if isinstance(o, np.bool_):
            return bool(o)
    except ImportError:
        pass
    if isinstance(o, (set, tuple)):
        return list(o)
    return str(o)


def sha256_file(p: Path | str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_stage(name: str) -> dict[str, Any] | None:
    p = RESULTS / f"{name}.json"
    return read_json(p) if p.exists() else None


def save_stage(name: str, obj: dict[str, Any]) -> None:
    obj = {"stage": name, "utc": utc_now(), **obj}
    write_json(RESULTS / f"{name}.json", obj)
    logger.info(f"stage {name} written: results/{name}.json")
    update_status(name, obj.get("status", "DONE"))


def update_status(stage: str, status: str) -> None:
    p = ROOT / "STATUS.md"
    lines = p.read_text().splitlines() if p.exists() else ["# STATUS (rewritten after every stage)", ""]
    lines = [ln for ln in lines if not ln.startswith(f"- {stage}:")]
    lines.append(f"- {stage}: {status} ({utc_now()})")
    p.write_text("\n".join(lines) + "\n")


def r2(x: float | None) -> str:
    """Two-decimal rendering used in the report's prose (round half away from zero on the decimal value)."""
    if x is None:
        return "n/a"
    from decimal import ROUND_HALF_UP, Decimal
    return str(Decimal(repr(float(x))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def rN(x: float | None, nd: int) -> str:
    if x is None:
        return "n/a"
    from decimal import ROUND_HALF_UP, Decimal
    q = Decimal(1).scaleb(-nd)
    return str(Decimal(repr(float(x))).quantize(q, rounding=ROUND_HALF_UP))
