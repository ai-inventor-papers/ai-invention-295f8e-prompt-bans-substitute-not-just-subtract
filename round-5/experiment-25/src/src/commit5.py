#!/usr/bin/env python3
"""Hash chain (exp17/exp19 commit.py): commitments.log holds one line per committed file:
utc_iso  relative_path  sha256  chain  tag, with chain = sha256(prev_chain + sha256 + utc + path)."""

from __future__ import annotations

from pathlib import Path

from cfg5 import COMMIT_LOG, ROOT, rel, sha256_file, sha256_text, utc_now

_CACHE: dict[str, str] = {}


def last_chain() -> str:
    if not COMMIT_LOG.exists():
        return "0" * 64
    lines = [l for l in COMMIT_LOG.read_text().splitlines() if l.strip()]
    return lines[-1].split()[3] if lines else "0" * 64


def commit(paths: list[Path], tag: str) -> list[dict]:
    out = []
    with open(COMMIT_LOG, "a") as fh:
        for p in paths:
            h = sha256_file(p)
            utc = utc_now()
            rp = rel(p)
            chain = sha256_text((_CACHE.get("chain") or last_chain()) + h + utc + rp)
            fh.write(f"{utc} {rp} {h} {chain} {tag}\n")
            fh.flush()
            _CACHE["chain"] = chain
            out.append({"utc": utc, "path": rp, "sha256": h, "chain": chain, "tag": tag})
    _CACHE.clear()
    return out


def tags() -> dict[str, str]:
    """tag -> first utc."""
    out: dict[str, str] = {}
    if not COMMIT_LOG.exists():
        return out
    for line in COMMIT_LOG.read_text().splitlines():
        parts = line.split()
        if len(parts) >= 5:
            out.setdefault(parts[4], parts[0])
    return out


def has_tag(tag: str) -> bool:
    return tag in tags()


def verify() -> dict:
    prev = "0" * 64
    n = bad = changed = 0
    first: dict[str, str] = {}
    for line in COMMIT_LOG.read_text().splitlines():
        if not line.strip():
            continue
        utc, rp, h, chain, tag = line.split()[:5]
        ok = sha256_text(prev + h + utc + rp) == chain
        cur = ROOT / rp
        same = cur.exists() and sha256_file(cur) == h
        n += 1
        bad += (not ok)
        changed += (not same)
        first.setdefault(tag, utc)
        prev = chain
    return {"n_lines": n, "chain_breaks": bad, "files_changed_since_commit": changed, "first_utc_by_tag": first}
