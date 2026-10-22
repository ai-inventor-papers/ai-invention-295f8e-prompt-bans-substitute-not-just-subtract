#!/usr/bin/env python3
"""Hash-chained commitments: each record = {name, files: {rel path: sha256}, utc, prev, hash}, where
hash = sha256(prev + name + sorted file hashes + utc). verify_chain() recomputes every file hash from disk."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from cfg import COMMIT_LOG, GENESIS6, ROOT, rel, sha256_file, sha256_text, utc_now

GENESIS = sha256_text(GENESIS6)   # iteration-6 chain genesis: sha256('iter6_gemma_L')


def _records() -> list[dict[str, Any]]:
    if not COMMIT_LOG.exists():
        return []
    return [json.loads(l) for l in COMMIT_LOG.read_text().splitlines() if l.strip()]


def commit(name: str, files: list[Path], note: str = "") -> dict[str, Any]:
    recs = _records()
    prev = recs[-1]["hash"] if recs else GENESIS
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
    prev = GENESIS
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


def verify_chain_superseded() -> dict[str, Any]:
    """Chain integrity + file hashes, where a file re-committed by a later record is checked against its LATEST
    record, and its earlier hash against a preserved copy '<stem>_commit<k>.py' if one exists (commit #0b)."""
    recs = _records()
    prev = GENESIS
    bad, notes = [], []
    last = {}
    for i, r in enumerate(recs):
        for f in r["files"]:
            last[f] = i
    for i, r in enumerate(recs):
        body = prev + r["name"] + json.dumps(r["files"], sort_keys=True) + r["utc"]
        if hashlib.sha256(body.encode()).hexdigest() != r["hash"] or r["prev"] != prev:
            bad.append({"name": r["name"], "problem": "chain"})
        for f, h in r["files"].items():
            p = ROOT / f
            if last[f] == i:
                if not p.exists() or sha256_file(p) != h:
                    bad.append({"name": r["name"], "file": f, "problem": "file hash"})
            else:
                kept = p.with_name(p.stem + f"_commit{i}" + p.suffix)
                alt = p.with_name(p.stem + "_commit0" + p.suffix)
                q = kept if kept.exists() else alt
                ok = q.exists() and sha256_file(q) == h
                notes.append({"name": r["name"], "file": f, "superseded_by": recs[last[f]]["name"],
                              "preserved_copy": rel(q) if q.exists() else None, "preserved_copy_matches": ok})
                if not ok:
                    bad.append({"name": r["name"], "file": f, "problem": "superseded copy missing or different"})
        prev = r["hash"]
    return {"n_records": len(recs), "ok": not bad, "problems": bad, "superseded": notes,
            "records": [{"name": r["name"], "utc": r["utc"], "hash": r["hash"]} for r in recs]}
