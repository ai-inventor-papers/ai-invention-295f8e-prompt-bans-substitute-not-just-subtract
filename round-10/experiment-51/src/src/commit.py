#!/usr/bin/env python3
"""Hash-chained commitments: write predictions/commitN.json and append
'UTC sha256(file) file sha256(previous line)' to commitments.log. Committed files are never edited; amendments are
new commits written before the samples they govern. `verify` re-checks the whole chain and every file hash."""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "commitments.log"


def sha_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def code_hashes() -> dict:
    files = sorted(ROOT.glob("src/*.py")) + sorted(ROOT.glob("tests/*.py")) + [ROOT / "start_vllm.sh"]
    return {str(p.relative_to(ROOT)): sha_file(p) for p in files if p.exists()}


def append(path: Path) -> str:
    prev = LOG.read_text().splitlines()[-1] if LOG.exists() and LOG.read_text().strip() else "GENESIS"
    line = f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {sha_file(path)} {path.relative_to(ROOT)} " \
           f"{hashlib.sha256(prev.encode()).hexdigest()}"
    with open(LOG, "a") as fh:
        fh.write(line + "\n")
    return line


def commit(n: int, content: dict) -> str:
    p = ROOT / "predictions" / f"commit{n}.json"
    if p.exists():
        raise FileExistsError(f"{p} exists: committed files are never edited")
    content = dict(content, commit=n, utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    p.write_text(json.dumps(content, indent=1))
    return append(p)


def verify() -> dict:
    lines = LOG.read_text().splitlines()
    prev, ok, rows = "GENESIS", True, []
    for ln in lines:
        utc, h, f, ph = ln.split(" ")
        chain_ok = ph == hashlib.sha256(prev.encode()).hexdigest()
        file_ok = (ROOT / f).exists() and sha_file(ROOT / f) == h
        rows.append({"utc": utc, "file": f, "chain_ok": chain_ok, "file_ok": file_ok})
        ok &= chain_ok and file_ok
        prev = ln
    return {"ok": ok, "n": len(lines), "rows": rows}


if __name__ == "__main__":
    if sys.argv[1] == "verify":
        print(json.dumps(verify(), indent=1))
    elif sys.argv[1] == "file":
        print(append(Path(sys.argv[2]).resolve()))
