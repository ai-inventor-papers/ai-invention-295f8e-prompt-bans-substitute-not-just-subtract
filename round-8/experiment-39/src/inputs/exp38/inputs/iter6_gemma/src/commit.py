#!/usr/bin/env python3
"""Hash-chained commitments: predictions/<name>.json is written once, and commitments.log gets one line
'<utc> <name> sha256=<file sha> prev=<sha of the previous log line> chain=<sha(prev + file sha)>'.
audit/verify_chain.py re-derives every chain value from the files on disk."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from cfg import COMMIT_LOG, PRED_DIR, sha256_file, utc_now, write_json


def _last_chain() -> str:
    if not COMMIT_LOG.exists():
        return "0" * 64
    lines = [ln for ln in COMMIT_LOG.read_text().splitlines() if ln.strip()]
    if not lines:
        return "0" * 64
    return lines[-1].split("chain=")[-1].strip()


def commit(name: str, obj: dict[str, Any]) -> dict[str, str]:
    p = PRED_DIR / f"{name}.json"
    assert not p.exists(), f"commitment {name} already exists; commitments are write-once"
    obj = dict(obj)
    obj["committed_utc"] = utc_now()
    write_json(p, obj)
    fsha = sha256_file(p)
    prev = _last_chain()
    chain = hashlib.sha256((prev + fsha).encode()).hexdigest()
    with open(COMMIT_LOG, "a") as fh:
        fh.write(f"{obj['committed_utc']} {name} sha256={fsha} prev={prev} chain={chain}\n")
    return {"name": name, "sha256": fsha, "chain": chain, "utc": obj["committed_utc"]}


def verify_chain() -> dict[str, Any]:
    prev = "0" * 64
    rows = []
    ok = True
    for ln in COMMIT_LOG.read_text().splitlines():
        if not ln.strip():
            continue
        parts = dict(kv.split("=", 1) for kv in ln.split()[2:])
        name = ln.split()[1]
        fsha = sha256_file(PRED_DIR / f"{name}.json")
        chain = hashlib.sha256((prev + fsha).encode()).hexdigest()
        good = fsha == parts["sha256"] and prev == parts["prev"] and chain == parts["chain"]
        ok &= good
        rows.append({"name": name, "utc": ln.split()[0], "file_sha_ok": fsha == parts["sha256"],
                     "chain_ok": good})
        prev = parts["chain"]
    return {"ok": ok, "entries": rows}


if __name__ == "__main__":
    import json

    print(json.dumps(verify_chain(), indent=1))
    _ = Path
