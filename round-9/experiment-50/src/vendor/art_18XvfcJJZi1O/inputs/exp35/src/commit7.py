#!/usr/bin/env python3
"""sha256 commitment chain (iteration-6 commit6 convention): each commit file's sha256 is appended to
commitments.log as 'UTC  name  sha256(file)  chain', chain = sha256(previous chain + file sha256).
verify() recomputes every link; a tampered file or line breaks the chain (U7)."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from cfg7 import COMMITS, PRED_DIR, ROOT, sha256_file, utc_now, write_json

GENESIS = "0" * 64


def _lines(log: Path = COMMITS) -> list[list[str]]:
    if not log.exists():
        return []
    return [l.split("  ") for l in log.read_text().splitlines() if l.strip()]


def commit(name: str, payload: dict[str, Any], log: Path = COMMITS, pred_dir: Path = PRED_DIR) -> dict[str, str]:
    p = pred_dir / f"{name}.json"
    if p.exists() and any(l[1] == name for l in _lines(log)):
        raise FileExistsError(f"commit {name} already exists; amendments need a new name")
    write_json(p, {"commit": name, "utc": utc_now(), **payload})
    h = sha256_file(p)
    prev = _lines(log)[-1][3] if _lines(log) else GENESIS
    chain = hashlib.sha256((prev + h).encode()).hexdigest()
    with open(log, "a") as fh:
        fh.write(f"{utc_now()}  {name}  {h}  {chain}\n")
    return {"name": name, "sha256": h, "chain": chain}


def verify(log: Path = COMMITS, pred_dir: Path = PRED_DIR) -> dict[str, Any]:
    prev = GENESIS
    out = {"ok": True, "n": 0, "bad": []}
    for utc, name, h, chain in _lines(log):
        p = pred_dir / f"{name}.json"
        h2 = sha256_file(p) if p.exists() else None
        c2 = hashlib.sha256((prev + h).encode()).hexdigest()
        if h2 != h or c2 != chain:
            out["ok"] = False
            out["bad"].append(name)
        prev = chain
        out["n"] += 1
    return out


def code_hashes(files: list[str]) -> dict[str, str]:
    return {f: sha256_file(ROOT / f) for f in files if (ROOT / f).exists()}


def self_test(tmp: Path) -> dict[str, Any]:
    """U7: commit, verify, tamper detection on a scratch chain."""
    tmp.mkdir(parents=True, exist_ok=True)
    log = tmp / "commitments_test.log"
    for f in tmp.glob("*.json"):
        f.unlink()
    log.unlink(missing_ok=True)
    commit("t0", {"x": 1}, log, tmp)
    commit("t1", {"y": 2}, log, tmp)
    ok = verify(log, tmp)["ok"]
    p = tmp / "t0.json"
    d = json.loads(p.read_text())
    d["x"] = 2
    p.write_text(json.dumps(d))
    tampered = verify(log, tmp)
    return {"verify_clean": ok, "tamper_detected": not tampered["ok"], "bad": tampered["bad"]}


if __name__ == "__main__":
    print(verify() if len(sys.argv) < 2 else self_test(Path(sys.argv[1])))
