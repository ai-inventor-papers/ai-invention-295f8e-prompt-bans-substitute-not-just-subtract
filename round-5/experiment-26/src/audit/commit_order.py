#!/usr/bin/env python3
"""Commit-order audit (plan T4): from the hash chain and the row timestamps, prove that every push row (ESC, PN, T13)
of a unit is later than that unit's commit, that the analysis code was committed before the first push row of any
unit, that commit #0 precedes every sample, and that the chain verifies. Writes results/commit_order.json."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha_file(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def main() -> None:
    lines = [l.split() for l in (ROOT / "commitments.log").read_text().splitlines() if l.strip()]
    prev = "0" * 64
    breaks = 0
    for utc, rp, h, chain, tag in (l[:5] for l in lines):
        breaks += hashlib.sha256((prev + h + utc + rp).encode()).hexdigest() != chain
        prev = chain
    first = {}
    for utc, rp, h, chain, tag in (l[:5] for l in lines):
        first.setdefault(tag, utc)
    rows = [json.loads(l) for l in (ROOT / "data" / "samples_raw.jsonl").read_text().splitlines() if l.strip()]
    first_sample = min(r["utc"] for r in rows)
    push = [r for r in rows if r["family"] in ("ESC", "PN", "T13")]
    first_push = min((r["utc"] for r in push), default=None)
    per_unit = {}
    viol = 0
    for u in sorted({r["unit"] for r in push}):
        c = first.get(f"unit_commit:{u}")
        pu = [r["utc"] for r in push if r["unit"] == u]
        bad = sum(1 for t in pu if c is None or t < c)
        viol += bad
        per_unit[u] = {"commit_utc": c, "first_push_utc": min(pu), "n_push_rows": len(pu), "rows_before_commit": bad}
    changed = []
    for utc, rp, h, chain, tag in (l[:5] for l in lines):
        p = ROOT / rp
        if not p.exists() or sha_file(p) != h:
            changed.append(rp)
    out = {"chain_lines": len(lines), "chain_breaks": breaks, "commit0_utc": first.get("commit0_protocol"),
           "first_sample_utc": first_sample, "commit0_precedes_samples": first.get("commit0_protocol", "~") < first_sample,
           "analysis_code_commit_utc": first.get("commit1_analysis_code_gates"), "first_push_utc": first_push,
           "analysis_code_precedes_pushes": first_push is None or first.get("commit1_analysis_code_gates", "~") <
           first_push, "per_unit": per_unit, "push_rows_before_their_commit": viol,
           "committed_files_changed_since": sorted(set(changed))}
    (ROOT / "results" / "commit_order.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k != "per_unit"}, indent=1))


if __name__ == "__main__":
    main()
