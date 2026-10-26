"""Shared infrastructure: dependency resolution by artifact id, provenance strings, input hashing, report index,
value statuses and the corrections ledger. No absolute server path is written into any output file."""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any

WS = Path(__file__).resolve().parent.parent
RESULTS = WS / "results"
TABLES = WS / "tables"
FIGURES = WS / "figures"
AUDIT = WS / "audit"
LOGS = WS / "logs"
for _d in (RESULTS, TABLES, FIGURES, AUDIT, LOGS):
    _d.mkdir(parents=True, exist_ok=True)

# artifact id -> original workspace folder of the artifact (relative to AII_DEPS_ROOT in the run's own layout)
DEPS = {
    "art_ccAbfJVcv0LO": "iter_3/gen_art/gen_art_experiment_18",
    "art_mWn-MQEnNelg": "iter_4/gen_art/gen_art_experiment_19",
    "art_SHaWv77P1XCI": "iter_4/gen_art/gen_art_experiment_22",
    "art_CcZLW-9NX00l": "iter_5/gen_art/gen_art_experiment_24",
    "art_8WbrpoEFslk9": "iter_5/gen_art/gen_art_experiment_25",
    "art_9a8LrIv2lHbV": "iter_5/gen_art/gen_art_experiment_26",
    "art_jR6Pyy3W9xum": "iter_5/gen_art/gen_art_experiment_27",
    "art_hG0QPiaIPNhP": "iter_5/gen_art/gen_art_experiment_28",
    # read by absolute path as the direction instructs (evaluations cannot be declared dependencies)
    "art_mgek9PfVBNbh": "iter_5/gen_art/gen_art_evaluation_4",
    "art_sV0cQ3ef1ZRQ": "iter_4/gen_art/gen_art_evaluation_3",
}
NICK = {"D18": "art_ccAbfJVcv0LO", "D19": "art_mWn-MQEnNelg", "D22": "art_SHaWv77P1XCI",
        "D24": "art_CcZLW-9NX00l", "PA": "art_8WbrpoEFslk9", "PB": "art_9a8LrIv2lHbV",
        "D27": "art_jR6Pyy3W9xum", "GEM": "art_hG0QPiaIPNhP", "EV4": "art_mgek9PfVBNbh", "EV3": "art_sV0cQ3ef1ZRQ"}


# ONE location setting for every input another artifact produced: AII_DEPS_ROOT. By default it is the folder that
# holds this artifact in the published repository (WS.parent), where the dependencies are sibling folders. A dependency
# folder is looked up by its artifact id first, then by its original workspace name. Two small evaluations that are
# not declared dependencies (art_mgek9PfVBNbh, art_sV0cQ3ef1ZRQ) are vendored under inputs/<artifact_id>/ as a fallback.
DEPS_ROOT = Path(os.environ.get("AII_DEPS_ROOT", str(WS.parent)))
# The report the corrections are keyed to, vendored from the strategy step of iteration 6.
REPORT_PATH = Path(os.environ.get("AII_REPORT", str(WS / "inputs" / "report" / "current_report.md")))
CFG = {"aii_json_skill_dir": os.environ.get("AII_JSON_SKILL_DIR", "")}

HASHES: dict[str, str] = {}


def aid_of(nick_or_aid: str) -> str:
    return NICK.get(nick_or_aid, nick_or_aid)


def dep_dir(nick_or_aid: str) -> Path:
    aid = aid_of(nick_or_aid)
    folder = DEPS[aid]
    cands = [DEPS_ROOT / aid, DEPS_ROOT / aid.removeprefix("art_"), DEPS_ROOT / Path(folder).name, DEPS_ROOT / folder,
             WS / "inputs" / aid]
    for c in cands:
        if c.is_dir():
            return c
    return cands[0]


def dep_path(nick_or_aid: str, rel: str) -> Path:
    d = dep_dir(nick_or_aid)
    p = d / rel
    if not p.exists():
        alt = WS / "inputs" / aid_of(nick_or_aid) / rel  # vendored copy (non-dependency evaluations only)
        if alt.exists():
            return alt
    return p


def prov(nick_or_aid: str, rel: str, ptr: str | None = None) -> str:
    s = f"{aid_of(nick_or_aid)}:{rel}"
    return s + (f"#{ptr}" if ptr else "")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _record(nick: str, rel: str, p: Path) -> None:
    key = prov(nick, rel)
    if key not in HASHES and p.exists():
        HASHES[key] = sha256_file(p)


def load_json(nick: str, rel: str) -> Any:
    p = dep_path(nick, rel)
    _record(nick, rel, p)
    return json.loads(p.read_text())


def load_jsonl(nick: str, rel: str) -> list[dict]:
    p = dep_path(nick, rel)
    _record(nick, rel, p)
    out = []
    with p.open() as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def iter_jsonl(nick: str, rel: str):
    p = dep_path(nick, rel)
    _record(nick, rel, p)
    with p.open() as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def read_text(nick: str, rel: str) -> str:
    p = dep_path(nick, rel)
    _record(nick, rel, p)
    return p.read_text()


def exists(nick: str, rel: str) -> bool:
    return dep_path(nick, rel).exists()


# ------------------------------------------------------------------------------------------------ outputs
def jdump(obj: Any) -> str:
    return json.dumps(obj, indent=1, default=_default, allow_nan=False)


def _default(o: Any):
    import numpy as np
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (set, tuple)):
        return list(o)
    if isinstance(o, Path):
        return str(o.relative_to(WS)) if str(o).startswith(str(WS)) else o.name
    raise TypeError(type(o))


def clean_nan(o: Any) -> Any:
    if isinstance(o, float):
        return None if not math.isfinite(o) else o
    if isinstance(o, dict):
        return {k: clean_nan(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean_nan(v) for v in o]
    return o


def write_json(rel: str, obj: Any) -> Path:
    p = WS / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(jdump(clean_nan(obj)))
    return p


def read_result(name: str) -> Any:
    return json.loads((RESULTS / f"{name}.json").read_text())


def write_csv(rel: str, rows: list[dict], cols: list[str] | None = None) -> Path:
    import csv
    p = WS / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    cols = cols or list(dict.fromkeys(k for r in rows for k in r.keys()))
    with p.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: _csv_cell(r.get(k)) for k in cols})
    return p


def _csv_cell(v: Any) -> Any:
    if isinstance(v, float):
        return "" if not math.isfinite(v) else round(v, 6)
    if isinstance(v, (dict, list, tuple)):
        return json.dumps(clean_nan(v))
    return v


# ------------------------------------------------------------------------------------------------ statuses
TOL = {"count": 0.0, "share": 0.005, "p": 0.10, "hill": 0.02, "ratio": 0.005, "nats": 0.01, "rho": 0.005,
       "label": None, "text": None}


def status_of(recorded: Any, recomputed: Any, kind: str) -> str:
    if recorded is None:
        return "NEW"
    if recomputed is None:
        return "CARRIED"
    if kind in ("label", "text"):
        return "MATCH" if str(recorded) == str(recomputed) else "CORRECTED"
    if isinstance(recorded, (list, tuple)):
        if not isinstance(recomputed, (list, tuple)) or len(recorded) != len(recomputed):
            return "CORRECTED"
        return "MATCH" if all(status_of(a, b, kind) == "MATCH" for a, b in zip(recorded, recomputed)) \
            else "CORRECTED"
    try:
        a, b = float(recorded), float(recomputed)
    except (TypeError, ValueError):
        return "MATCH" if recorded == recomputed else "CORRECTED"
    if kind == "count":
        return "MATCH" if abs(a - b) < 1e-9 else "CORRECTED"
    if kind == "p":
        return "MATCH" if abs(a - b) <= TOL["p"] * max(abs(a), 1e-12) + 1e-12 else "CORRECTED"
    return "MATCH" if abs(a - b) <= TOL.get(kind, 0.005) + 1e-12 else "CORRECTED"


def val(name: str, recorded: Any, recomputed: Any, source: str, kind: str = "share",
        status: str | None = None, note: str | None = None) -> dict:
    s = status or status_of(recorded, recomputed, kind)
    d = {"name": name, "recorded": recorded, "recomputed": recomputed, "status": s, "source": source,
         "tolerance": kind}
    if note:
        d["note"] = note
    return d


# ------------------------------------------------------------------------------------------------ report
class Report:
    def __init__(self, path: Path):
        self.text = path.read_text()
        self.lines = self.text.split("\n")
        self.sha256 = hashlib.sha256(self.text.encode()).hexdigest()

    def line_of(self, s: str) -> int | None:
        """1-based line where s first starts (s may span lines)."""
        i = self.text.find(s)
        if i < 0:
            return None
        return self.text.count("\n", 0, i) + 1

    def count(self, s: str) -> int:
        return self.text.count(s)

    def line(self, n: int) -> str:
        return self.lines[n - 1]

    def section_of(self, n: int) -> str:
        for k in range(n - 1, -1, -1):
            if self.lines[k].startswith("#"):
                return self.lines[k].lstrip("#").strip()[:80]
        return ""

    def table_block(self, caption_prefix: str) -> tuple[int, list[str]]:
        """Return (1-based first row line, rows) of the markdown table following the caption line."""
        n = self.line_of(caption_prefix)
        if n is None:
            raise KeyError(caption_prefix)
        k = n  # 0-based index of the line after the caption
        while k < len(self.lines) and not self.lines[k].startswith("|"):
            k += 1
        start = k
        rows = []
        while k < len(self.lines) and self.lines[k].startswith("|"):
            rows.append(self.lines[k])
            k += 1
        return start + 1, rows


class Ledger:
    """Corrections keyed to exact substrings of current_report.md."""

    def __init__(self, report: Report):
        self.rep = report
        self.items: list[dict] = []

    def add(self, review_item: str, old_text: str, new_text: str, values: list[dict] | None = None,
            note: str | None = None) -> dict:
        n = self.rep.line_of(old_text)
        if n is None:
            raise ValueError(f"old_text not found in report for {review_item}: {old_text[:80]!r}")
        if self.rep.count(old_text) != 1:
            raise ValueError(f"old_text not unique ({self.rep.count(old_text)}) for {review_item}: {old_text[:80]!r}")
        item = {"id": f"C6-{len(self.items) + 1:03d}", "review_item": review_item,
                "location": {"section": self.rep.section_of(n), "report_line": n},
                "old_text": old_text, "new_text": new_text, "values": values or [],
                "marker": "iteration-6 correction"}
        if note:
            item["note"] = note
        self.items.append(item)
        return item
