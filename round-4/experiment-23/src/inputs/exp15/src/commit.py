#!/usr/bin/env python3
"""sha256 hash chain (commitments.log): one JSON line {file, sha256, prev_hash, utc, note, hash} per committed file,
hash = sha256(prev_hash + file + sha256 + utc + note)."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path

from src.ws import WS, sha256_file

LOG = WS / "commitments.log"


def _entries() -> list[dict]:
    if not LOG.exists():
        return []
    return [json.loads(l) for l in LOG.read_text().splitlines() if l.strip()]


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="microseconds")


def commit(path: Path, note: str = "") -> dict:
    path = Path(path)
    ents = _entries()
    prev = ents[-1]["hash"] if ents else "0" * 64
    rel = str(path.resolve().relative_to(WS))
    sha = sha256_file(path)
    utc = utc_now()
    h = hashlib.sha256((prev + rel + sha + utc + note).encode()).hexdigest()
    e = {"file": rel, "sha256": sha, "prev_hash": prev, "utc": utc, "note": note, "hash": h}
    with LOG.open("a") as fh:
        fh.write(json.dumps(e) + "\n")
    return e


def verify() -> dict:
    ents = _entries()
    prev = "0" * 64
    bad = []
    for i, e in enumerate(ents):
        h = hashlib.sha256((prev + e["file"] + e["sha256"] + e["utc"] + e.get("note", "")).encode()).hexdigest()
        if e["prev_hash"] != prev or h != e["hash"]:
            bad.append(i)
        prev = e["hash"]
    # files whose current content differs from their LAST committed sha (later re-commits supersede)
    last = {}
    for e in ents:
        last[e["file"]] = e["sha256"]
    changed = [f for f, s in last.items() if (WS / f).exists() and sha256_file(WS / f) != s]
    missing = [f for f in last if not (WS / f).exists()]
    return {"n_entries": len(ents), "chain_ok": not bad, "bad_entries": bad, "changed_since_commit": changed,
            "missing": missing}
