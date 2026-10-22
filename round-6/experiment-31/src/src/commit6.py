#!/usr/bin/env python3
"""Hash chain (commitments.log), genesis sha256('iter6|panelI'). One line per committed file:
    utc_iso  relative_path  sha256  chain  tag
with chain = sha256(prev_chain + sha256 + utc + path). A committed file is never edited; amendments are new files.
Per-unit commit (plan S6): predictions/units/<u>.json is committed with tag 'unit_commit:<u>' BEFORE the unit's first
nudge row; the nudge sampler refuses to start for a unit without a verified entry (verify_unit_commit).
Usage: python src/commit6.py verify
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg6 import COMMIT_LOG, GENESIS, PRED_DIR, RAW_HF, ROOT, read_jsonl, rel, sha256_file, sha256_text, utc_now  # noqa

NUDGE_FAMILIES = ("ESC", "PN", "GTN", "BINT")


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
            rp = rel(p)
            chain = sha256_text(prev + h + utc + rp)
            fh.write(f"{utc} {rp} {h} {chain} {tag}\n")
            fh.flush()
            prev = chain
            out.append({"utc": utc, "path": rp, "sha256": h, "chain": chain, "tag": tag})
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
    prev = GENESIS
    n = bad = changed = 0
    first: dict[str, str] = {}
    changed_paths = []
    for e in entries():
        ok = sha256_text(prev + e["sha256"] + e["utc"] + e["path"]) == e["chain"]
        cur = ROOT / e["path"]
        same = cur.exists() and sha256_file(cur) == e["sha256"]
        n += 1
        bad += (not ok)
        if not same:
            changed += 1
            changed_paths.append(e["path"])
        first.setdefault(e["tag"], e["utc"])
        prev = e["chain"]
    return {"n_lines": n, "chain_breaks": bad, "files_changed_since_commit": changed,
            "changed_paths": changed_paths[:20], "first_utc_by_tag": first}


def verify_unit_commit(u: str) -> dict[str, Any]:
    p = PRED_DIR / "units" / f"{u}.json"
    es = [e for e in entries() if e["tag"] == f"unit_commit:{u}" and e["path"] == rel(p)]
    v = verify()
    if not es or not p.exists():
        return {"ok": False, "why": "no commit entry"}
    e = es[-1]
    same = sha256_file(p) == e["sha256"]
    rows = [r for r in read_jsonl(RAW_HF) if r["unit"] == u and r["family"] in NUDGE_FAMILIES]
    earlier = [r for r in rows if r["utc"] < e["utc"]]
    ok = same and v["chain_breaks"] == 0 and not earlier
    return {"ok": ok, "commit_utc": e["utc"], "chain_index": e["index"], "sha256": e["sha256"], "file_unchanged": same,
            "chain_breaks": v["chain_breaks"], "nudge_rows_before_commit": len(earlier)}


if __name__ == "__main__":
    import json
    print(json.dumps(verify(), indent=1))
