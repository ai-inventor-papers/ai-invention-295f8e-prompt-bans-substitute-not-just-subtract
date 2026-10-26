"""Dependency paths, hashed input manifest and provenance records (plan PART 0.1-0.4)."""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Callable

WS = Path(__file__).resolve().parent.parent
# Dependencies are read in place, read-only.  In the published repository each dependency artifact is a sibling folder
# of this one, named by its artifact id: <AII_DEPS_ROOT>/<artifact_id>, with AII_DEPS_ROOT defaulting to the parent
# folder of this workspace.  A single dependency can be pointed elsewhere with AII_DEP_<artifact_id> (non-alphanumeric
# characters of the id replaced by '_', e.g. AII_DEP_art_mWn_MQEnNelg).
DEPS_ROOT = Path(os.environ.get("AII_DEPS_ROOT", str(WS.parent)))
DEP_IDS: dict[str, str] = {
    "exp23": "art_k6nzFCDLOjQP",  # held-out family (gemma-3-4b-it), iteration 4
    "exp20": "art_Cx9JOh8soBw7",  # site experiment, iteration 4
    "exp22": "art_SHaWv77P1XCI",  # plan subspace / escape fractions, iteration 4
    "exp19": "art_mWn-MQEnNelg",  # plan noise knob table, iteration 4
    "exp21": "art_Yu6GN6pLxW8f",  # same-seed temperature vs plan noise, iteration 4
    "exp5": "art_HF8nK8B_Lqyy",   # iteration-1 base-model data (run 4VFKidE1bxPG)
    "bench": "art_0ndRfWKBWclR",  # iteration-2 coding bench
    "src": "art_j3Rm_lr2nzR6",    # iteration-1 source data (run 4VFKidE1bxPG)
}


def dep_dir(art_id: str) -> Path:
    return Path(os.environ.get("AII_DEP_" + re.sub(r"\W", "_", art_id), str(DEPS_ROOT / art_id)))


DEPS: dict[str, tuple[str, Path]] = {k: (a, dep_dir(a)) for k, a in DEP_IDS.items()}
TOL = {"count": 0.0, "rate": 0.005, "stat": 0.01, "interval": 0.02}
TASKS = ["T1", "T2", "T03", "T04", "T05", "T06", "T08", "T10", "T11", "T13", "T14", "R1", "R2", "R3", "R6"]
NAMES = {"T1": "grid path", "T2": "weighted shortest path", "T03": "kth smallest", "T04": "substring search",
         "T05": "two sum", "T06": "find duplicate", "T08": "Fibonacci", "T10": "connected components",
         "T11": "longest increasing subsequence", "T13": "merge intervals", "T14": "top-k frequent",
         "R1": "non-overlapping intervals", "R2": "cycle detection", "R3": "topological order",
         "R6": "first and last position"}


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def as_bool(v: Any) -> bool:
    return v is True or v == "True" or v == "true" or v == 1


class Inputs:
    """Every dependency file read goes through here: path resolution, sha256 manifest, a 'source' string."""

    def __init__(self, log: Callable[[str], None] | None = None, forbidden: tuple[str, ...] = ()):
        self.manifest: dict[str, dict[str, Any]] = {}
        self.log = log
        self.forbidden = forbidden

    def path(self, dep: str, rel: str) -> Path:
        art, root = DEPS[dep]
        p = root / rel
        src = f"{art}:{rel}"
        for f in self.forbidden:
            if f in src:
                raise PermissionError(f"forbidden input for this script: {src}")
        if src not in self.manifest:
            if not p.exists():
                self.manifest[src] = {"exists": False, "abs_dep": dep}
                raise FileNotFoundError(src)
            self.manifest[src] = {"exists": True, "sha256": sha256_file(p), "bytes": p.stat().st_size, "dep": dep}
            if self.log:
                self.log(f"open {src}")
        return p

    def src(self, dep: str, rel: str) -> str:
        return f"{DEPS[dep][0]}:{rel}"

    def json(self, dep: str, rel: str) -> Any:
        return json.loads(self.path(dep, rel).read_text())

    def jsonl(self, dep: str, rel: str, must_contain: str | None = None) -> list[dict[str, Any]]:
        out = []
        with self.path(dep, rel).open() as fh:
            for ln in fh:
                if not ln.strip() or (must_contain is not None and must_contain not in ln):
                    continue
                out.append(json.loads(ln))
        return out


def close(a: float | None, b: float | None, kind: str) -> bool | None:
    if a is None or b is None:
        return None
    return abs(float(a) - float(b)) <= TOL[kind] + 1e-12


def val(name: str, value: Any, tag: str, source: str, record: Any = None, kind: str = "stat",
        note: str | None = None) -> dict[str, Any]:
    """One provenance record.  status: MATCH / CORRECTED (outside tolerance) / NEW (no record value) / CARRIED /
    NOT_COMPUTABLE."""
    if tag == "CARRIED":
        status = "CARRIED"
    elif tag == "NOT_COMPUTABLE" or value is None:
        status = "NOT_COMPUTABLE"
    elif record is None:
        status = "NEW"
    elif isinstance(value, (int, float)) and isinstance(record, (int, float)):
        status = "MATCH" if close(value, record, kind) else "CORRECTED"
    elif isinstance(value, (list, tuple)) and isinstance(record, (list, tuple)) and len(value) == len(record) and \
            all(isinstance(x, (int, float)) for x in list(value) + list(record)):
        status = "MATCH" if all(close(a, b, kind) for a, b in zip(value, record)) else "CORRECTED"
    else:
        status = "MATCH" if value == record else "CORRECTED"
    out = {"name": name, "record_value": record, "value": value, "tag": tag, "source": source, "status": status,
           "tolerance": kind}
    if note:
        out["note"] = note
    return out


def r(x: Any, nd: int = 3) -> Any:
    if isinstance(x, float):
        return round(x, nd)
    if isinstance(x, list):
        return [r(v, nd) for v in x]
    if isinstance(x, dict):
        return {k: r(v, nd) for k, v in x.items()}
    return x
