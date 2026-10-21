#!/usr/bin/env python3
"""Hash chain for artifact E (plan Stage A.1): commitments.log holds one line per committed file
    utc  relative_path  file_sha256  chain  tag
with chain = sha256(prev_chain + file_sha256 + utc) and genesis prev_chain = sha256('iter6_E')."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from cfg import rel, sha256_file, utc_now
from cfg_e import COMMIT_LOG, ROOT

GENESIS = hashlib.sha256(b"iter6_E").hexdigest()


def _sha(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def last_chain() -> str:
    if not COMMIT_LOG.exists():
        return GENESIS
    lines = [l for l in COMMIT_LOG.read_text().splitlines() if l.strip()]
    return lines[-1].split()[3] if lines else GENESIS


def commit(paths: list[Path], tag: str) -> list[dict[str, Any]]:
    out = []
    prev = last_chain()
    with open(COMMIT_LOG, "a") as fh:
        for p in paths:
            h = sha256_file(p)
            utc = utc_now()
            chain = _sha(prev + h + utc)
            fh.write(f"{utc} {rel(p)} {h} {chain} {tag}\n")
            fh.flush()
            prev = chain
            out.append({"utc": utc, "path": rel(p), "sha256": h, "chain": chain, "tag": tag})
    return out


def verify() -> dict[str, Any]:
    prev = GENESIS
    n = breaks = changed = 0
    first: dict[str, str] = {}
    if not COMMIT_LOG.exists():
        return {"n_lines": 0}
    for line in COMMIT_LOG.read_text().splitlines():
        if not line.strip():
            continue
        utc, rp, h, chain, tag = line.split()[:5]
        breaks += _sha(prev + h + utc) != chain
        cur = ROOT / rp
        changed += (not cur.exists()) or sha256_file(cur) != h
        first.setdefault(tag, utc)
        prev = chain
        n += 1
    return {"n_lines": n, "chain_breaks": breaks, "files_changed_since_commit": changed, "first_utc_by_tag": first}
