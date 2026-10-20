"""Workspace and dependency locations, resolved relative to this repository (no absolute server paths).

Every dependency is read in place, read-only. A dependency is addressed as `<artifact_id>:<relative path>` in all
outputs; `src(aid, rel)` builds that citation string and `dep(aid, rel)` the readable Path.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any, Iterable

WS = Path(__file__).resolve().parent.parent
# runs root = <runs>/<run>/3_invention_loop/iter_3/gen_art/<this workspace>; overridable for a fork
RUNS = Path(os.environ.get("AII_RUNS_ROOT", str(WS.parents[4])))

DEPS: dict[str, str] = {
    "art__skdlFp_o3e9": "run_4VFKidE1bxPG/3_invention_loop/iter_1/gen_art/gen_art_experiment_1",   # exp1
    "art_D6Z0Snf09sFL": "run_4VFKidE1bxPG/3_invention_loop/iter_1/gen_art/gen_art_experiment_2",   # exp2
    "art_U5UKkFrOgSsE": "run_4VFKidE1bxPG/3_invention_loop/iter_1/gen_art/gen_art_experiment_4",   # exp4
    "art_HF8nK8B_Lqyy": "run_4VFKidE1bxPG/3_invention_loop/iter_1/gen_art/gen_art_experiment_5",   # exp5
    "art_UoCVh2Qe5RZ0": "run_4VFKidE1bxPG/3_invention_loop/iter_1/gen_art/gen_art_experiment_6",   # exp6
    "art_6zBfl3kDjeiP": "run_aRfWvcSWjssb/3_invention_loop/iter_2/gen_art/gen_art_experiment_7",   # exp7
    "art_8_ULPE8jJQc_": "run_aRfWvcSWjssb/3_invention_loop/iter_2/gen_art/gen_art_experiment_8",   # exp8
    "art_IVZc3TWCeE9f": "run_aRfWvcSWjssb/3_invention_loop/iter_2/gen_art/gen_art_experiment_9",   # exp9
    "art_-QPYRaFERCBX": "run_aRfWvcSWjssb/3_invention_loop/iter_2/gen_art/gen_art_experiment_10",  # exp10
    "art_0ndRfWKBWclR": "run_aRfWvcSWjssb/3_invention_loop/iter_2/gen_art/gen_art_experiment_11",  # exp11
    "art_3iv5G76C3yoX": "run_aRfWvcSWjssb/3_invention_loop/iter_2/gen_art/gen_art_experiment_12",  # exp12
}
EXP = {"exp1": "art__skdlFp_o3e9", "exp2": "art_D6Z0Snf09sFL", "exp4": "art_U5UKkFrOgSsE", "exp5": "art_HF8nK8B_Lqyy",
       "exp6": "art_UoCVh2Qe5RZ0", "exp7": "art_6zBfl3kDjeiP", "exp8": "art_8_ULPE8jJQc_", "exp9": "art_IVZc3TWCeE9f",
       "exp10": "art_-QPYRaFERCBX", "exp11": "art_0ndRfWKBWclR", "exp12": "art_3iv5G76C3yoX",
       "exp3": "art_8_ULPE8jJQc_"}   # exp3 programs are read only through the pools copy shipped inside exp8
REPORT_REL = "run_aRfWvcSWjssb/3_invention_loop/iter_3/gen_strat/current_report.md"  # iteration-2 report (old wording)

RESULTS = WS / "results"
TABLES = WS / "tables"
FIGS = WS / "figures"
AUDIT = WS / "audit"
LOGS = WS / "logs"
SEED = 20261020


DEPS_ROOT_ENV = "AII_DEPS_ROOT"  # optional: a directory holding one folder per dependency, named by its artifact id


def dep_root(aid: str) -> Path:
    """Folder of dependency `aid`, looked up in this order:
    1. $AII_DEPS_ROOT/<artifact_id>;
    2. ../<artifact_id> (the published repository: every artifact is a sibling folder named by its id);
    3. the AI Inventor run-volume layout, relative to this repository (RUNS / DEPS[aid])."""
    env = os.environ.get(DEPS_ROOT_ENV)
    if env:
        return Path(env) / aid
    sib = WS.parent / aid
    if sib.is_dir():
        return sib
    return RUNS / DEPS[aid]


def dep(aid_or_exp: str, rel: str = "") -> Path:
    aid = EXP.get(aid_or_exp, aid_or_exp)
    return dep_root(aid) / rel


def src(aid_or_exp: str, rel: str) -> str:
    aid = EXP.get(aid_or_exp, aid_or_exp)
    return f"{aid}:{rel}"


def read_jsonl(p: Path) -> list[dict[str, Any]]:
    out = []
    with Path(p).open() as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return out


def read_json(p: Path) -> Any:
    return json.loads(Path(p).read_text())


def _default(o: Any) -> Any:
    import numpy as np

    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        v = float(o)
        return None if not math.isfinite(v) else v
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (set, tuple)):
        return list(o)
    if isinstance(o, Path):
        return str(o)
    return str(o)


def clean(o: Any) -> Any:
    """Recursively replace non-finite floats by None so the JSON is standard."""
    import numpy as np

    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (float, np.floating)):
        v = float(o)
        return v if math.isfinite(v) else None
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.ndarray):
        return clean(o.tolist())
    if isinstance(o, np.bool_):
        return bool(o)
    return o


def write_json(p: Path, obj: Any, indent: int | None = 1) -> None:
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(clean(obj), indent=indent, default=_default))
    tmp.replace(p)


def write_jsonl(p: Path, rows: Iterable[dict[str, Any]]) -> None:
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w") as fh:
        for r in rows:
            fh.write(json.dumps(clean(r), default=_default) + "\n")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with Path(p).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def code_key(code: str) -> str:
    """De-duplication key: sha256 of the code with trailing whitespace stripped from every line and the ends."""
    norm = "\n".join(line.rstrip() for line in (code or "").strip().splitlines())
    return sha256_text(norm)
