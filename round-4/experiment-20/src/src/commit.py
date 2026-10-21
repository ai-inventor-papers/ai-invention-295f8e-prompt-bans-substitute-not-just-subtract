#!/usr/bin/env python3
"""Hash chain (exp17 commit.py): commitments.log holds one line per committed file:
utc_iso  relative_path  sha256  chain  tag, with chain = sha256(prev_chain + sha256 + utc + path)."""

from __future__ import annotations

from pathlib import Path

from cfg import ROOT, rel, sha256_file, sha256_text, utc_now

LOG = ROOT / "commitments.log"


def last_chain() -> str:
    if not LOG.exists():
        return "0" * 64
    lines = [l for l in LOG.read_text().splitlines() if l.strip()]
    return lines[-1].split()[3] if lines else "0" * 64


def commit(paths: list[Path], tag: str) -> list[dict]:
    out = []
    prev = last_chain()
    with open(LOG, "a") as fh:
        for p in paths:
            h = sha256_file(p)
            utc = utc_now()
            rp = rel(p)
            chain = sha256_text(prev + h + utc + rp)
            fh.write(f"{utc} {rp} {h} {chain} {tag}\n")
            fh.flush()
            prev = chain
            out.append({"utc": utc, "path": rp, "sha256": h, "chain": chain, "tag": tag})
    return out


def verify() -> dict:
    """Chain integrity over every line; content check against each path's LATEST commit (earlier commits of a file
    that was deliberately re-committed are counted as superseded versions, not as changes)."""
    prev = "0" * 64
    n = bad = 0
    first: dict[str, str] = {}
    latest: dict[str, str] = {}
    versions: dict[str, int] = {}
    for line in LOG.read_text().splitlines():
        if not line.strip():
            continue
        utc, rp, h, chain, tag = line.split()[:5]
        ok = sha256_text(prev + h + utc + rp) == chain
        n += 1
        bad += (not ok)
        first.setdefault(tag, utc)
        latest[rp] = h
        versions[rp] = versions.get(rp, 0) + 1
        prev = chain
    changed = [rp for rp, h in latest.items() if not ((ROOT / rp).exists() and sha256_file(ROOT / rp) == h)]
    return {"n_lines": n, "chain_breaks": bad, "n_paths": len(latest),
            "files_changed_since_commit": len(changed), "changed_paths": changed,
            "n_superseded_versions": sum(v - 1 for v in versions.values()),
            "recommitted_paths": sorted(rp for rp, v in versions.items() if v > 1), "first_utc_by_tag": first}
