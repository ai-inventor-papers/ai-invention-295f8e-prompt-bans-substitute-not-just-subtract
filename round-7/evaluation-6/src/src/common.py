"""Shared paths, IO, hashing and logging for the iteration-7 record repair (Step 0).

Every path is derived from this file's location (the workspace root) or from the AII_RUN_ROOT environment
variable, so no absolute server path is written into any published file. Inputs are read from the vendored
copies under inputs/<artifact_id>/ once src/stage_inputs.py has resolved and hashed them.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Iterable

from loguru import logger

WS = Path(__file__).resolve().parents[1]
# ONE anchor for every input another artifact produced. On the run server the artifacts sit under the invention-loop
# folder three levels above this workspace; in the published repository each artifact is a sibling folder of this one
# (looked up by its workspace folder name, then by its artifact id). Override with the environment variable
# AII_DEPS_ROOT. If no source is reachable, the sha256-verified copies vendored under inputs/ are used.
DEPS_ROOT = Path(os.environ.get("AII_DEPS_ROOT", str(WS.parents[2])))
DEP_REL = {  # artifact id -> folder under DEPS_ROOT on the run server
    "art_lpQalcAXMGr1": "iter_6/gen_art/gen_art_experiment_29",  # engine control
    "art_rMlbrjVB1c__": "iter_6/gen_art/gen_art_experiment_30",  # exchange and site experiment
    "art_zNyBP6zieI5u": "iter_6/gen_art/gen_art_experiment_31",  # Gemma
    "art_dbUtqBjT0tPf": "iter_6/gen_art/gen_art_experiment_32",  # NLA
    "art_aRTQM6CQ0Dre": "iter_6/gen_art/gen_art_evaluation_5",  # iteration-6 Step 0 (read by path)
    "art_OUuQUYQn5voE": "iter_6/gen_art/gen_art_research_3",  # iteration-6 positioning audit (read by path)
}
DEPENDENCIES = ("art_lpQalcAXMGr1", "art_rMlbrjVB1c__", "art_zNyBP6zieI5u", "art_dbUtqBjT0tPf")
REPORT_REL = "iter_7/gen_strat/current_report.md"  # the object being corrected, under DEPS_ROOT


def dep_dir(artifact: str) -> Path:
    """Server layout first, then a sibling folder named like the workspace folder, then one named by the id."""
    rel = DEP_REL[artifact]
    for cand in (DEPS_ROOT / rel, WS.parent / Path(rel).name, WS.parent / artifact):
        if cand.is_dir():
            return cand
    return DEPS_ROOT / rel


DEP_DIRS = {a: dep_dir(a) for a in DEPENDENCIES}
NONDEP_DIRS = {a: dep_dir(a) for a in DEP_REL if a not in DEPENDENCIES}
REPORT_SRC = DEPS_ROOT / REPORT_REL
SHORT = {"art_lpQalcAXMGr1": "engine", "art_rMlbrjVB1c__": "exchange", "art_zNyBP6zieI5u": "gemma",
         "art_dbUtqBjT0tPf": "nla", "art_aRTQM6CQ0Dre": "step0_iter6", "art_OUuQUYQn5voE": "positioning_iter6"}

INPUTS = WS / "inputs"
TABLES = WS / "tables"
AUDIT = WS / "audit"
LOGS = WS / "logs"
RESULTS = WS / "results"
READ_DATE = "2026-10-22"
MARK = "(iteration-7 correction)"


def setup_logging(name: str) -> None:
    LOGS.mkdir(parents=True, exist_ok=True)
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    logger.add(LOGS / f"{name}.log", rotation="30 MB", level="DEBUG")


def inp(artifact: str, rel: str) -> Path:
    """Path of a vendored input file."""
    return INPUTS / artifact / rel


def src_ref(artifact: str, rel: str, key: str | None = None) -> str:
    return f"{artifact}:{rel}" + (f"#{key}" if key else "")


def read_json(p: Path) -> Any:
    return json.loads(Path(p).read_text())


def write_json(p: Path, obj: Any, indent: int = 1) -> None:
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=indent, default=_default, ensure_ascii=False) + "\n")


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
    if isinstance(o, Path):
        return str(o)
    if isinstance(o, set):
        return sorted(o)
    raise TypeError(f"not JSON serialisable: {type(o)}")


def read_jsonl(p: Path) -> list[dict[str, Any]]:
    return [json.loads(l) for l in Path(p).read_text().splitlines() if l.strip()]


def write_jsonl(p: Path, rows: Iterable[dict[str, Any]]) -> None:
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w") as f:
        for r in rows:
            f.write(json.dumps(r, default=_default, ensure_ascii=False) + "\n")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with Path(p).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def truthy(v: Any) -> bool:
    """Label rows store booleans as bools or as 'True'/'False' strings."""
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() == "true"
    return bool(v)


def fmt(x: float | None, nd: int = 2) -> str:
    if x is None:
        return "n/a"
    return f"{x:.{nd}f}"


def fmt_p(p: float | None) -> str:
    """Report-style p value: 3 significant digits above 1e-3, scientific below."""
    if p is None:
        return "n/a"
    if p >= 0.001:
        return f"{p:.3f}" if p < 0.1 else f"{p:.2f}"
    return f"{p:.1e}"
