#!/usr/bin/env python3
"""Hash-chained pre-registration. commitments.log holds one JSON line per commit:
{n, utc, title, files: {path: sha256}, payload_sha256, prev, chain}; chain = sha256(prev + payload_sha256 + files),
genesis prev = sha256('iter6_dir2_engine_E'). verify() recomputes every link and every committed file hash that still
exists unchanged (files may legitimately change only through a later commit that re-lists them)."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from c6 import COMMIT_LOG, GENESIS, ROOT, sha256_file, utc_now  # noqa: E402


def _entries() -> list[dict[str, Any]]:
    if not COMMIT_LOG.exists():
        return []
    return [json.loads(l) for l in COMMIT_LOG.read_text().splitlines() if l.strip()]


def commit(title: str, payload: Any, files: list[str]) -> dict[str, Any]:
    ents = _entries()
    prev = ents[-1]["chain"] if ents else GENESIS
    fh = {f: sha256_file(ROOT / f) for f in files}
    ps = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()
    chain = hashlib.sha256((prev + ps + json.dumps(fh, sort_keys=True)).encode()).hexdigest()
    e = {"n": len(ents), "utc": utc_now(), "title": title, "files": fh, "payload_sha256": ps, "prev": prev,
         "chain": chain}
    with open(COMMIT_LOG, "a") as f:
        f.write(json.dumps(e) + "\n")
    return e


def verify() -> dict[str, Any]:
    ents = _entries()
    prev = GENESIS
    ok = True
    latest: dict[str, str] = {}
    for e in ents:
        c = hashlib.sha256((prev + e["payload_sha256"] + json.dumps(e["files"], sort_keys=True)).encode()).hexdigest()
        ok &= (e["prev"] == prev and c == e["chain"])
        prev = e["chain"]
        latest.update(e["files"])
    drift = {f: h for f, h in latest.items() if (ROOT / f).exists() and sha256_file(ROOT / f) != h}
    return {"n_commits": len(ents), "chain_ok": bool(ok), "files_changed_since_last_commit": drift}


if __name__ == "__main__":
    print(json.dumps(verify(), indent=1))
