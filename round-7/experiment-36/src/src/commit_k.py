#!/usr/bin/env python3
"""sha256 hash chain of pre-registered files (commitments.log).

Each line: '<chain_sha256>  <UTC>  <file sha256>  <relative path>  <note>' where chain_sha256 = sha256(previous chain
sha256 + file sha256 + path); the genesis is sha256('iter7_K_genesis'). `verify` recomputes the chain and checks that
no committed file changed after its LAST commit.

usage: .venv/bin/python src/commit_k.py add <path> [note...] | verify
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from k_cfg import COMMIT_LOG, GENESIS, ROOT, RESULTS, sha256_file, utc_now, write_json  # noqa: E402


def _lines() -> list[list[str]]:
    if not COMMIT_LOG.exists():
        return []
    return [l.split("  ") for l in COMMIT_LOG.read_text().splitlines() if l.strip()]


def add(path: str | Path, note: str = "") -> str:
    p = Path(path)
    rel = str(p.resolve().relative_to(ROOT))
    fh = sha256_file(p)
    prev = _lines()[-1][0] if _lines() else GENESIS
    ch = hashlib.sha256((prev + fh + rel).encode()).hexdigest()
    with open(COMMIT_LOG, "a") as f:
        f.write(f"{ch}  {utc_now()}  {fh}  {rel}  {note.replace('  ', ' ')}\n")
    return ch


def verify() -> dict:
    prev = GENESIS
    breaks, last = 0, {}
    entries = _lines()
    for parts in entries:
        ch, utc, fh, rel = parts[0], parts[1], parts[2], parts[3]
        exp = hashlib.sha256((prev + fh + rel).encode()).hexdigest()
        if exp != ch:
            breaks += 1
        prev = ch
        last[rel] = (fh, utc)
    changed = [rel for rel, (fh, _) in last.items() if not (ROOT / rel).exists() or sha256_file(ROOT / rel) != fh]
    res = {"entries": len(entries), "chain_breaks": breaks, "files": len(last), "changed_since_last_commit": changed,
           "utc": utc_now()}
    write_json(RESULTS / "commit_chain_verify.json", res)
    return res


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "add":
        print(add(sys.argv[2], " ".join(sys.argv[3:])))
    else:
        print(verify())
