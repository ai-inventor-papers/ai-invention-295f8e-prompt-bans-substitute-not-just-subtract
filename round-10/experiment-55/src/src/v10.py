#!/usr/bin/env python3
"""TP-G2 shared constants: hash-chained commitments (genesis sha256('iter10_tpg2')), paths, frozen settings,
the banned / non-banned split, the model pins and block choices for this round."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DATA, RESULTS, PRED, LOGS, FIGS = ROOT / "data", ROOT / "results", ROOT / "predictions", ROOT / "logs", ROOT / "figures"
STATES_V10 = ROOT / "cache" / "states_v10"
COMMIT_LOG = ROOT / "commitments.log"
GENESIS = hashlib.sha256(b"iter10_tpg2").hexdigest()
for _d in (DATA, RESULTS, PRED, LOGS, FIGS, STATES_V10):
    _d.mkdir(parents=True, exist_ok=True)

# Prior artifacts are read through ONE relative constant: the published repository lays every artifact out as a
# sibling folder named by its artifact id (override the parent with TPG_DEPS_DIR, or one artifact with TPG_DEP_<id>).
DEPS_DIR = Path(os.environ.get("TPG_DEPS_DIR", str(ROOT.parent)))


def dep(art_id: str) -> Path:
    return Path(os.environ.get("TPG_DEP_" + art_id.replace("-", "_"), str(DEPS_DIR / art_id)))


E46 = dep("art_VVA3P0ocZNA2")                    # iteration-9 gen_art_experiment_46
E46_STATES = E46 / "cache" / "states"            # read in place (sha256 in inputs_manifest.json)
IN46 = ROOT / "inputs" / "art_VVA3P0ocZNA2"
IN45 = ROOT / "inputs" / "art_8nXdw3_lDAll"
IN44 = ROOT / "inputs" / "art_R-HSmXq2t97f"
DSET = dep("art_j3Rm_lr2nzR6")                   # declared dependency (iteration-1 dataset)

CANON = ["bfs", "dfs", "bibfs", "iddfs", "astar", "gbfs", "dijkstra_unit", "idastar", "jps", "biastar"]
BANNED_ALGS = ["bfs", "dfs", "iddfs", "astar", "gbfs"]
NONBANNED_ALGS = ["dijkstra_unit", "idastar", "bibfs", "jps", "biastar"]
BANNED_DISC = ["BFSO", "DFSO", "HEUR"]
NONBANNED_DISC = ["COST", "RELAX", "RAND"]
CLASS_FLOOR = 10
K_PRIMARY, K_SECOND = 15, 10

M8 = {"tag": "8b", "repo": "Qwen/Qwen3-8B", "revision": "b968826d9c46dd6066d109eabc6255188de91218",
      "precision": "bf16", "n_layers": 36, "n_keep": 27, "blocks": [9, 11, 13, 15, 17, 19, 21, 23, 25, 26],
      "primary_block": 17, "hidden": 4096, "engine": "HF bf16 Qwen3-8B"}
M32 = {"tag": "32b", "repo": "unsloth/Qwen3-32B-bnb-4bit", "revision": "7f721e74a6a8cc9ee352f7e49303a2c1705f9083",
       "precision": "nf4", "n_layers": 64, "n_keep": 40, "blocks": [21, 25, 29, 31, 33, 35, 37, 39],
       "primary_block": 33, "hidden": 5120, "engine": "HF nf4 unsloth/Qwen3-32B-bnb-4bit truncated"}
MODELS = {"8b": M8, "32b": M32}
READOUTS = ["R1", "R1g", "R2", "R3"]


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with Path(p).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def write_json(p: Path, obj: Any, indent: int | None = 1) -> None:
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + f".tmp{os.getpid()}")
    tmp.write_text(json.dumps(obj, indent=indent, ensure_ascii=False, default=_default))
    tmp.replace(p)


def _default(o: Any) -> Any:
    import numpy as np

    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, (set, frozenset)):
        return sorted(o)
    if isinstance(o, Path):
        return str(o)
    raise TypeError(f"not JSON serialisable: {type(o)}")


def read_json(p: Path) -> Any:
    return json.loads(Path(p).read_text())


def read_jsonl(p: Path) -> list[dict[str, Any]]:
    p = Path(p)
    if not p.exists():
        return []
    out = []
    for ln in p.read_text().splitlines():
        ln = ln.strip()
        if ln:
            try:
                out.append(json.loads(ln))
            except json.JSONDecodeError:
                continue
    return out


def append_jsonl(p: Path, row: dict[str, Any]) -> None:
    with Path(p).open("a") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        fh.write(json.dumps(row, ensure_ascii=False, default=_default) + "\n")
        fcntl.flock(fh, fcntl.LOCK_UN)


def commit(payload: Path, label: str, note: str = "") -> dict[str, Any]:
    """Append {i, label, utc, prev_line_sha256, payload_sha256, payload_path, note} to commitments.log; line 0 chains
    on GENESIS = sha256('iter10_tpg2'), every later line on the sha256 of the previous line's exact text."""
    lines = COMMIT_LOG.read_text().splitlines() if COMMIT_LOG.exists() else []
    prev = sha256_text(lines[-1]) if lines else GENESIS
    e = {"i": len(lines), "label": label, "utc": utc_now(), "prev_line_sha256": prev,
         "payload_sha256": sha256_file(payload), "payload_path": str(Path(payload).resolve().relative_to(ROOT)),
         "note": note}
    with COMMIT_LOG.open("a") as fh:
        fh.write(json.dumps(e, sort_keys=True) + "\n")
    return e


def verify_chain() -> dict[str, Any]:
    if not COMMIT_LOG.exists():
        return {"ok": False, "problems": ["no commitments.log"]}
    prev = GENESIS
    problems, labels = [], []
    for i, ln in enumerate(COMMIT_LOG.read_text().splitlines()):
        e = json.loads(ln)
        labels.append((e["label"], e["utc"]))
        if e["prev_line_sha256"] != prev:
            problems.append(f"line {i}: chain break")
        p = ROOT / e["payload_path"]
        if not p.exists():
            problems.append(f"line {i}: payload missing")
        elif sha256_file(p) != e["payload_sha256"]:
            problems.append(f"line {i}: payload changed ({e['payload_path']})")
        prev = sha256_text(ln)
    return {"ok": not problems, "problems": problems, "entries": labels}


def commit_time(label: str) -> str | None:
    if not COMMIT_LOG.exists():
        return None
    for ln in COMMIT_LOG.read_text().splitlines():
        e = json.loads(ln)
        if e["label"] == label:
            return e["utc"]
    return None


def deviation(code: str, text: str) -> None:
    p = RESULTS / "deviations.json"
    devs = read_json(p) if p.exists() else []
    if not any(d["code"] == code for d in devs):
        devs.append({"code": code, "text": text, "utc": utc_now()})
        write_json(p, devs)


def ledger(milestone: str, **kw: Any) -> None:
    append_jsonl(LOGS / "time_ledger.jsonl", {"milestone": milestone, "utc": utc_now(), **kw})
