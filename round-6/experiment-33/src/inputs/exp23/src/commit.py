#!/usr/bin/env python3
"""Hash-chained commitments: each record = {name, files: {rel path: sha256}, utc, prev, hash}, where
hash = sha256(prev + name + sorted file hashes + utc). verify_chain() recomputes every file hash from disk."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from cfg import COMMIT_LOG, ROOT, rel, sha256_file, utc_now


def _records() -> list[dict[str, Any]]:
    if not COMMIT_LOG.exists():
        return []
    return [json.loads(l) for l in COMMIT_LOG.read_text().splitlines() if l.strip()]


def commit(name: str, files: list[Path], note: str = "") -> dict[str, Any]:
    recs = _records()
    prev = recs[-1]["hash"] if recs else "0" * 64
    fh = {rel(p): sha256_file(p) for p in files}
    utc = utc_now()
    body = prev + name + json.dumps(fh, sort_keys=True) + utc
    rec = {"name": name, "files": fh, "utc": utc, "prev": prev, "note": note,
           "hash": hashlib.sha256(body.encode()).hexdigest()}
    with open(COMMIT_LOG, "a") as f:
        f.write(json.dumps(rec) + "\n")
    return rec


def verify_chain() -> dict[str, Any]:
    recs = _records()
    prev = "0" * 64
    bad = []
    for r in recs:
        body = prev + r["name"] + json.dumps(r["files"], sort_keys=True) + r["utc"]
        if hashlib.sha256(body.encode()).hexdigest() != r["hash"] or r["prev"] != prev:
            bad.append({"name": r["name"], "problem": "chain"})
        for f, h in r["files"].items():
            p = ROOT / f
            if not p.exists() or sha256_file(p) != h:
                bad.append({"name": r["name"], "file": f, "problem": "file hash"})
        prev = r["hash"]
    return {"n_records": len(recs), "ok": not bad, "problems": bad}
