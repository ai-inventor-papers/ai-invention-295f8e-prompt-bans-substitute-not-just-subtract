#!/usr/bin/env python3
"""Hash-chained commitments of iteration 7 (exp30 commit6 with genesis sha256('iter7_dir2')):
predictions/<name>.json + one line per commit in commitments.log; chain sha256(prev | name | utc | payload_sha256).
Later commits are amendments; a committed file is never edited (verify() reports changed files)."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from cfg import PRED_DIR, ROOT, sha256_file, utc_now, write_json
from cfg6 import COMMITS
from cfg7 import GENESIS7


def chain() -> list[dict[str, Any]]:
    if not COMMITS.exists():
        return []
    return [json.loads(l) for l in COMMITS.read_text().splitlines() if l.strip()]


def commit(name: str, payload: dict[str, Any]) -> dict[str, Any]:
    for c in chain():
        if c["name"] == name:
            return c
    p = PRED_DIR / f"{name}.json"
    utc = utc_now()
    write_json(p, {"name": name, "utc": utc, **payload})
    ps = sha256_file(p)
    prev = chain()[-1]["sha256"] if chain() else GENESIS7
    h = hashlib.sha256(f"{prev}|{name}|{utc}|{ps}".encode()).hexdigest()
    rec = {"name": name, "utc": utc, "file": str(p.relative_to(ROOT)), "file_sha256": ps, "prev": prev, "sha256": h}
    with open(COMMITS, "a") as fh:
        fh.write(json.dumps(rec) + "\n")
    return rec


def verify() -> dict[str, Any]:
    prev, breaks, changed = GENESIS7, 0, []
    for c in chain():
        h = hashlib.sha256(f"{prev}|{c['name']}|{c['utc']}|{c['file_sha256']}".encode()).hexdigest()
        breaks += int(h != c["sha256"] or c["prev"] != prev)
        if sha256_file(ROOT / c["file"]) != c["file_sha256"]:
            changed.append(c["file"])
        prev = c["sha256"]
    return {"n_commits": len(chain()), "breaks": breaks, "changed_files": changed, "genesis": GENESIS7}
