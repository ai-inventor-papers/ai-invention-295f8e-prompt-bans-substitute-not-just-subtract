#!/usr/bin/env python3
"""Hash chain. commitments.log holds one line per entry:
  <entry#> | sha256(prev_line) | <relative path> <file sha256> | <UTC> | <tag>
Entry #0 is results/screen.json. Never edit a committed file; corrections are new entries."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cfg4 import COMMIT_LOG, ROOT, rel, sha256_file, sha256_text, utc_now


def _lines() -> list[str]:
    if not COMMIT_LOG.exists():
        return []
    return [l for l in COMMIT_LOG.read_text().splitlines() if l.strip()]


def commit(paths: list[Path], tag: str) -> list[dict[str, Any]]:
    out = []
    for p in paths:
        lines = _lines()
        prev = sha256_text(lines[-1]) if lines else "0" * 64
        line = f"{len(lines)} | {prev} | {rel(p)} {sha256_file(p)} | {utc_now()} | {tag}"
        with open(COMMIT_LOG, "a") as fh:
            fh.write(line + "\n")
        out.append({"entry": len(lines), "path": rel(p), "line": line})
    return out


def verify() -> dict[str, Any]:
    """Chain integrity, and for every committed path whether its LATEST entry matches the file on disk (earlier
    entries of a re-committed path are superseded corrections, listed separately)."""
    lines = _lines()
    breaks = []
    prev = "0" * 64
    first_utc: dict[str, str] = {}
    latest: dict[str, tuple[int, str]] = {}
    superseded = []
    for i, line in enumerate(lines):
        parts = [x.strip() for x in line.split("|")]
        n, ph, pf, utc, tag = parts[0], parts[1], parts[2], parts[3], parts[4]
        if ph != prev:
            breaks.append(i)
        path, h = pf.rsplit(" ", 1)
        if path in latest:
            superseded.append({"path": path, "entry": latest[path][0], "superseded_by": i})
        latest[path] = (i, h)
        first_utc.setdefault(tag, utc)
        prev = sha256_text(line)
    changed = [p for p, (i, h) in latest.items() if not (ROOT / p).exists() or sha256_file(ROOT / p) != h]
    return {"n_entries": len(lines), "chain_breaks": breaks, "latest_entry_mismatches": changed,
            "superseded_entries": superseded, "first_utc_by_tag": first_utc}
