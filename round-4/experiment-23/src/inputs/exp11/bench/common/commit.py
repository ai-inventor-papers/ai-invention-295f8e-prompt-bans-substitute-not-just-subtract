"""sha256 hash-chain commitments: each line of commitments.log is {ts, kind, sha256, prev_line_sha256, ...}."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path


def canon_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def sha256_file(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def commit(log_path: Path, kind: str, payload_sha256: str, extra: dict | None = None) -> dict:
    lines = log_path.read_text().splitlines() if log_path.exists() else []
    prev = sha256_text(lines[-1]) if lines else "0" * 64
    rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "kind": kind, "sha256": payload_sha256,
           "prev_line_sha256": prev}
    if extra:
        rec.update(extra)
    with log_path.open("a") as f:
        f.write(canon_json(rec) + "\n")
    return rec


def verify_chain(log_path: Path) -> bool:
    lines = log_path.read_text().splitlines()
    prev = "0" * 64
    for line in lines:
        rec = json.loads(line)
        if rec["prev_line_sha256"] != prev:
            return False
        prev = sha256_text(line)
    return True
