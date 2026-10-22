#!/usr/bin/env python3
"""Hash chain: commitments.log holds one line per committed file:
utc_iso  relative_path  sha256  chain, with chain = sha256(prev_chain + sha256 + utc + path)."""

from __future__ import annotations

from pathlib import Path

from cfg import ROOT, rel, sha256_file, sha256_text, utc_now  # exp17 commit.py, unchanged

LOG = ROOT / "commitments.log"


def last_chain() -> str:
    if not LOG.exists():
        return "0" * 64
    lines = [l for l in LOG.read_text().splitlines() if l.strip()]
    return lines[-1].split()[3] if lines else "0" * 64


def commit(paths: list[Path], tag: str) -> list[dict]:
    out = []
    with open(LOG, "a") as fh:
        for p in paths:
            h = sha256_file(p)
            utc = utc_now()
            rp = rel(p)
            chain = sha256_text(last_chain_cached(fh) + h + utc + rp)
            fh.write(f"{utc} {rp} {h} {chain} {tag}\n")
            fh.flush()
            _CACHE["chain"] = chain
            out.append({"utc": utc, "path": rp, "sha256": h, "chain": chain, "tag": tag})
    _CACHE.clear()
    return out


_CACHE: dict[str, str] = {}


def last_chain_cached(fh) -> str:
    return _CACHE.get("chain") or last_chain()


def verify() -> dict:
    prev = "0" * 64
    n = bad = 0
    first: dict[str, str] = {}
    for line in LOG.read_text().splitlines():
        if not line.strip():
            continue
        utc, rp, h, chain, tag = line.split()[:5]
        ok = sha256_text(prev + h + utc + rp) == chain
        cur = (ROOT / rp)
        same = cur.exists() and sha256_file(cur) == h
        n += 1
        bad += (not ok)
        first.setdefault(tag, utc)
        prev = chain
    return {"n_lines": n, "chain_breaks": bad, "first_utc_by_tag": first}
