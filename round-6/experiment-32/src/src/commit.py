#!/usr/bin/env python3
"""Hash-chained pre-registration: commitments.log holds one line per commit
{n, name, file, file_sha256, prev, chain, utc}; chain = sha256(prev + file_sha256), genesis = sha256('iter6_dir6')."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from cfg import GENESIS, PRED_DIR, ROOT, rel, sha256_file, utc_now, write_json

LOG = ROOT / "commitments.log"


def chain_rows() -> list[dict[str, Any]]:
    if not LOG.exists():
        return []
    return [json.loads(l) for l in LOG.read_text().splitlines() if l.strip()]


def commit(name: str, obj: dict[str, Any]) -> dict[str, Any]:
    rows = chain_rows()
    if any(r["name"] == name for r in rows):
        return next(r for r in rows if r["name"] == name)
    p = PRED_DIR / f"{name}.json"
    obj = dict(obj, committed_utc=utc_now())
    write_json(p, obj)
    fs = sha256_file(p)
    prev = rows[-1]["chain"] if rows else GENESIS
    rec = {"n": len(rows), "name": name, "file": rel(p), "file_sha256": fs, "prev": prev,
           "chain": hashlib.sha256((prev + fs).encode()).hexdigest(), "utc": utc_now()}
    with open(LOG, "a") as fh:
        fh.write(json.dumps(rec) + "\n")
    return rec


def verify() -> dict[str, Any]:
    rows = chain_rows()
    prev = GENESIS
    ok = True
    for r in rows:
        fs = sha256_file(ROOT / r["file"])
        exp = hashlib.sha256((prev + fs).encode()).hexdigest()
        ok &= (fs == r["file_sha256"]) and (exp == r["chain"]) and (r["prev"] == prev)
        prev = r["chain"]
    return {"n": len(rows), "ok": bool(ok), "head": prev}
