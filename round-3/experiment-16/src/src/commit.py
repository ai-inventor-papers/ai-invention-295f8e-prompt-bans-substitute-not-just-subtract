#!/usr/bin/env python3
"""sha256 hash chain: one line per committed file in commitments.log:
{utc, commit, path, file_sha256, chain}, chain = sha256(prev_chain + file_sha256 + utc + path)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from loguru import logger

from cfg import COMMIT_LOG, ROOT, sha256_file, sha256_text, utc_now


def _last_chain() -> str:
    if not COMMIT_LOG.exists():
        return "0" * 64
    lines = [ln for ln in COMMIT_LOG.read_text().splitlines() if ln.strip()]
    return json.loads(lines[-1])["chain"] if lines else "0" * 64


def commit_files(name: str, paths: list[Path]) -> list[dict[str, Any]]:
    prev = _last_chain()
    out = []
    with COMMIT_LOG.open("a") as fh:
        for p in paths:
            p = Path(p)
            if not p.exists():
                logger.warning(f"commit {name}: {p} missing, skipped")
                continue
            utc = utc_now()
            rel = str(p.resolve().relative_to(ROOT))
            fs = sha256_file(p)
            chain = sha256_text(prev + fs + utc + rel)
            rec = {"utc": utc, "commit": name, "path": rel, "file_sha256": fs, "chain": chain}
            fh.write(json.dumps(rec, sort_keys=True) + "\n")
            prev = chain
            out.append(rec)
    logger.info(f"commit {name}: {len(out)} files hash-chained (head {prev[:16]})")
    return out


def verify_chain() -> dict[str, Any]:
    prev = "0" * 64
    bad = []
    recs = []
    for i, ln in enumerate(COMMIT_LOG.read_text().splitlines()):
        if not ln.strip():
            continue
        r = json.loads(ln)
        want = sha256_text(prev + r["file_sha256"] + r["utc"] + r["path"])
        if want != r["chain"]:
            bad.append(i)
        cur = sha256_file(ROOT / r["path"]) if (ROOT / r["path"]).exists() else None
        r["file_unchanged"] = cur == r["file_sha256"]
        recs.append(r)
        prev = r["chain"]
    return {"n_lines": len(recs), "chain_ok": not bad, "bad_lines": bad, "records": recs}
