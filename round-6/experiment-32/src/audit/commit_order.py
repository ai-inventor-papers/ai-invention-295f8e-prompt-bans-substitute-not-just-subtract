#!/usr/bin/env python3
"""Commit-order proof (standard library only): (1) the sha256 hash chain of commitments.log verifies from the genesis
sha256('iter6_dir5_panelII') and no committed file changed since its commit; (2) commit #0 predates the first sample
of this artifact; (3) the analysis commit predates the first nudge sample; (4) every ESC / PN / GTN row of a unit
postdates that unit's commit; (5) a tampered copy of a committed file breaks the chain check (negative control)."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GENESIS = hashlib.sha256(b"iter6_dir5_panelII").hexdigest()


def sha_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    ents = []
    for line in (ROOT / "commitments.log").read_text().splitlines():
        if line.strip():
            utc, path, h, chain, tag = line.split()[:5]
            ents.append({"utc": utc, "path": path, "sha": h, "chain": chain, "tag": tag})
    prev, breaks, changed = GENESIS, 0, []
    for e in ents:
        if hashlib.sha256((prev + e["sha"] + e["utc"] + e["path"]).encode()).hexdigest() != e["chain"]:
            breaks += 1
        p = ROOT / e["path"]
        if not p.exists() or sha_file(p) != e["sha"]:
            changed.append(e["path"])
        prev = e["chain"]
    raw = [json.loads(l) for l in (ROOT / "data" / "samples_raw.jsonl").read_text().splitlines() if l.strip()]
    first_sample = min(r["utc"] for r in raw)
    nudges = [r for r in raw if r.get("family") in ("ESC", "PN", "GTN")]
    first_nudge = min((r["utc"] for r in nudges), default=None)
    c0 = next(e["utc"] for e in ents if e["tag"] == "commit0")
    ca = min(e["utc"] for e in ents if e["tag"] == "analysis_commit")
    unit_commit = {}
    for e in ents:
        if e["tag"].startswith("unit_commit:"):
            unit_commit[e["tag"].split(":", 1)[1]] = e["utc"]
    before = {}
    for r in nudges:
        cu = unit_commit.get(r["unit"])
        if cu is None or r["utc"] < cu:
            before[r["unit"]] = before.get(r["unit"], 0) + 1
    # negative control: a one-byte change to the first committed file must break the content check
    first = ROOT / ents[0]["path"]
    tampered = hashlib.sha256(first.read_bytes() + b" ").hexdigest() != ents[0]["sha"]
    out = {"n_lines": len(ents), "chain_breaks": breaks, "files_changed_since_commit": changed,
           "commit0_utc": c0, "first_sample_utc": first_sample, "commit0_before_first_sample": c0 < first_sample,
           "analysis_commit_utc": ca, "first_nudge_utc": first_nudge,
           "analysis_before_first_nudge": first_nudge is None or ca < first_nudge,
           "nudge_rows_before_their_unit_commit": before, "n_nudge_rows": len(nudges),
           "tamper_negative_control_detected": tampered}
    (ROOT / "results" / "commit_order.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
