"""sha256 hash chain (commitments.log): one line per committed file, written BEFORE the samples it governs.

line = {utc, label, path, sha256, prev_chain, chain}, chain = sha256(prev_chain + sha256).  Committed files are
never edited; a change is a new file plus a deviation entry.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from config import COMMIT_LOG, ROOT, sha256_file, utc_now, write_json


def _last_chain() -> str:
    if not COMMIT_LOG.exists():
        return "0" * 64
    lines = [l for l in COMMIT_LOG.read_text().splitlines() if l.strip()]
    return json.loads(lines[-1])["chain"] if lines else "0" * 64


def commit_file(path: Path, label: str) -> dict[str, Any]:
    path = Path(path)
    h = sha256_file(path)
    prev = _last_chain()
    chain = hashlib.sha256((prev + h).encode()).hexdigest()
    rec = {"utc": utc_now(), "label": label, "path": str(path.relative_to(ROOT)), "sha256": h, "prev_chain": prev,
           "chain": chain}
    with COMMIT_LOG.open("a") as f:
        f.write(json.dumps(rec) + "\n")
    return rec


def commit_json(path: Path, obj: Any, label: str) -> dict[str, Any]:
    path = Path(path)
    if path.exists():
        raise FileExistsError(f"refusing to overwrite committed file {path}")
    write_json(path, obj)
    return commit_file(path, label)


def verify_chain() -> dict[str, Any]:
    prev = "0" * 64
    n, bad = 0, []
    if not COMMIT_LOG.exists():
        return {"n": 0, "ok": True, "bad": []}
    for line in COMMIT_LOG.read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        n += 1
        ok = r["prev_chain"] == prev and r["chain"] == hashlib.sha256((prev + r["sha256"]).encode()).hexdigest()
        p = ROOT / r["path"]
        file_ok = p.exists() and sha256_file(p) == r["sha256"]
        if not (ok and file_ok):
            bad.append({"label": r["label"], "path": r["path"], "chain_ok": ok, "file_ok": file_ok})
        prev = r["chain"]
    return {"n": n, "ok": not bad, "bad": bad, "head": prev}
