#!/usr/bin/env python3
"""sha256 hash chain of commitments (commitments.log): one JSON line per commit
{n, name, files: {path: sha256}, utc, prev, chain} with chain = sha256(prev | sorted file hashes | utc | name).
A committed file is never edited; an amendment is a new commit. verify() recomputes every link and every file hash.
Usage: commit8.py commit <name> <file> [<file> ...] | verify
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg8 import COMMITS, ROOT, sha256_file, utc_now  # noqa: E402

GENESIS = "0" * 64


def _chain(prev: str, files: dict[str, str], utc: str, name: str) -> str:
    s = prev + "|" + "|".join(f"{k}:{files[k]}" for k in sorted(files)) + "|" + utc + "|" + name
    return hashlib.sha256(s.encode()).hexdigest()


def entries() -> list[dict]:
    if not COMMITS.exists():
        return []
    return [json.loads(l) for l in COMMITS.read_text().splitlines() if l.strip()]


def commit(name: str, paths: list[Path]) -> dict:
    ents = entries()
    if any(e["name"] == name for e in ents):
        raise RuntimeError(f"commit {name} exists; an amendment must be a new commit")
    prev = ents[-1]["chain"] if ents else GENESIS
    snap = ROOT / "predictions" / "snapshots" / name
    files = {}
    for p in paths:
        rel = Path(p).resolve().relative_to(ROOT)
        dst = snap / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(Path(p), dst)                       # the committed copy is what verify() checks
        files[str(rel)] = sha256_file(dst)
    utc = utc_now()
    e = {"n": len(ents), "name": name, "files": files, "utc": utc, "prev": prev, "chain": _chain(prev, files, utc, name)}
    with open(COMMITS, "a") as fh:
        fh.write(json.dumps(e) + "\n")
    return e


def verify(check_files: bool = True) -> dict:
    ents = entries()
    prev = GENESIS
    bad, edited = [], []
    for e in ents:
        if e["prev"] != prev or _chain(e["prev"], e["files"], e["utc"], e["name"]) != e["chain"]:
            bad.append({"n": e["n"], "why": "link"})
        if check_files:
            snap = ROOT / "predictions" / "snapshots" / e["name"]
            for k, h in e["files"].items():
                p = snap / k if (snap / k).exists() else ROOT / k
                if not p.exists() or sha256_file(p) != h:
                    edited.append({"n": e["n"], "file": k, "note": "live file edited after this commit (no snapshot)"})
        prev = e["chain"]
    return {"n_commits": len(ents), "ok": not bad, "problems": bad, "edited_live_files": edited,
            "names": [e["name"] for e in ents], "utc": {e["name"]: e["utc"] for e in ents}}


def tamper_test() -> bool:
    """C6: flipping one byte of a committed line's file hash breaks verification (tested on an in-memory copy)."""
    ents = entries()
    if not ents:
        return True
    e = dict(ents[0])
    k = next(iter(e["files"]))
    h = e["files"][k]
    e["files"] = {**e["files"], k: ("0" if h[0] != "0" else "1") + h[1:]}
    return _chain(e["prev"], e["files"], e["utc"], e["name"]) != e["chain"]


if __name__ == "__main__":
    if sys.argv[1] == "commit":
        print(json.dumps(commit(sys.argv[2], [Path(p) for p in sys.argv[3:]]), indent=1))
    else:
        print(json.dumps(verify(), indent=1))
