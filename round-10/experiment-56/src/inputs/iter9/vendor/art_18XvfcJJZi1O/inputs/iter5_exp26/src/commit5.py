#!/usr/bin/env python3
"""Hash chain (exp17/exp19 commit.py convention): commitments.log holds one line per committed file
    utc_iso  relative_path  sha256  chain  tag
with chain = sha256(prev_chain + sha256 + utc + path). A committed file is never edited; amendments are new files.

Per-unit commit (plan section 8): predictions/units/<u>.json is committed with tag 'unit_commit:<u>' BEFORE the unit's
first push sample; the push sampler refuses to start for a unit without a verified entry (verify_unit_commit).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cfg5 import COMMIT_LOG, PRED_DIR, RAW, ROOT, read_jsonl, rel, sha256_file, sha256_text, utc_now

_CACHE: dict[str, str] = {}


def last_chain() -> str:
    if not COMMIT_LOG.exists():
        return "0" * 64
    lines = [l for l in COMMIT_LOG.read_text().splitlines() if l.strip()]
    return lines[-1].split()[3] if lines else "0" * 64


def commit(paths: list[Path], tag: str) -> list[dict[str, Any]]:
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


def entries() -> list[dict[str, Any]]:
    if not COMMIT_LOG.exists():
        return []
    out = []
    for i, line in enumerate(COMMIT_LOG.read_text().splitlines()):
        if not line.strip():
            continue
        utc, rp, h, chain, tag = line.split()[:5]
        out.append({"index": i, "utc": utc, "path": rp, "sha256": h, "chain": chain, "tag": tag})
    return out


def verify() -> dict[str, Any]:
    prev = "0" * 64
    n = bad = changed = 0
    first: dict[str, str] = {}
    for e in entries():
        ok = sha256_text(prev + e["sha256"] + e["utc"] + e["path"]) == e["chain"]
        cur = ROOT / e["path"]
        same = cur.exists() and sha256_file(cur) == e["sha256"]
        n += 1
        bad += (not ok)
        changed += (not same)
        first.setdefault(e["tag"], e["utc"])
        prev = e["chain"]
    return {"n_lines": n, "chain_breaks": bad, "files_changed_since_commit": changed, "first_utc_by_tag": first}


def verify_unit_commit(u: str) -> dict[str, Any]:
    p = PRED_DIR / "units" / f"{u}.json"
    es = [e for e in entries() if e["tag"] == f"unit_commit:{u}" and e["path"] == rel(p)]
    v = verify()
    if not es or not p.exists():
        return {"ok": False, "why": "no commit entry"}
    e = es[-1]
    same = sha256_file(p) == e["sha256"]
    push_rows = [r for r in read_jsonl(RAW) if r["unit"] == u and r["family"] in ("ESC", "PN", "T13")]
    earlier = [r for r in push_rows if r["utc"] < e["utc"]]
    ok = same and v["chain_breaks"] == 0 and not earlier
    return {"ok": ok, "commit_utc": e["utc"], "chain_index": e["index"], "sha256": e["sha256"], "file_unchanged": same,
            "chain_breaks": v["chain_breaks"], "push_rows_before_commit": len(earlier)}
