#!/usr/bin/env python3
"""Hash-chained commitments (commitments.log): each line = {n, utc, label, files: {path: sha256}, prev, hash}.
hash = sha256(prev + canonical(entry without hash)). A committed file is never edited afterwards; verify() checks the
chain and that every committed file still has its committed hash (or reports which changed)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from cfg import ROOT, canonical_json, rel, sha256_file, sha256_text, utc_now

LOG = ROOT / "commitments.log"


def _entries() -> list[dict]:
    if not LOG.exists():
        return []
    return [json.loads(l) for l in LOG.read_text().splitlines() if l.strip()]


def commit(label: str, files: list[Path], note: str = "") -> dict:
    ents = _entries()
    prev = ents[-1]["hash"] if ents else "0" * 64
    e = {"n": len(ents), "utc": utc_now(), "label": label, "note": note,
         "files": {rel(f): sha256_file(f) for f in files}, "prev": prev}
    e["hash"] = sha256_text(prev + canonical_json(e))
    with LOG.open("a") as fh:
        fh.write(json.dumps(e, sort_keys=True) + "\n")
    return e


def verify() -> dict:
    ents = _entries()
    breaks = 0
    prev = "0" * 64
    changed = []
    latest: dict[str, str] = {}
    for e in ents:
        h = e.get("hash")
        body = {k: v for k, v in e.items() if k != "hash"}
        if e.get("prev") != prev or sha256_text(prev + canonical_json(body)) != h:
            breaks += 1
        prev = h
        for f, s in e["files"].items():
            latest[f] = s
    for f, s in latest.items():
        p = ROOT / f
        if not p.exists() or sha256_file(p) != s:
            changed.append(f)
    return {"n_entries": len(ents), "chain_breaks": breaks, "n_files": len(latest), "changed_since_commit": changed,
            "labels": [e["label"] for e in ents], "utc": [e["utc"] for e in ents]}


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "verify":
        print(json.dumps(verify(), indent=1))
