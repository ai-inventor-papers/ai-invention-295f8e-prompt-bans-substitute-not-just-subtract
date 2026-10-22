#!/usr/bin/env python3
"""Integrity proof (testing plan): the hash chain verifies; commit #0 precedes the first sample; the analysis-code
addendum and the enrolment hash precede the first nudge row; for every unit the per-unit commit UTC precedes its first
nudge row (ESC / PN / GTN) and no nudge row predates the enrolment hash. Writes results/commit_order.json."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from commit6 import entries, verify  # noqa: E402


def main() -> None:
    v = verify()
    es = entries()
    first = {}
    for e in es:
        first.setdefault(e["tag"], e["utc"])
    raw_v = [json.loads(l) for l in (ROOT / "data" / "raw_vllm.jsonl").read_text().splitlines() if l.strip()]
    raw_h = [json.loads(l) for l in (ROOT / "data" / "raw_hf.jsonl").read_text().splitlines() if l.strip()]
    first_sample = min(r["utc"] for r in raw_v + raw_h)
    nudges = [r for r in raw_h if r.get("family") in ("ESC", "PN", "GTN")]
    first_nudge = min(r["utc"] for r in nudges) if nudges else None
    per_unit = {}
    bad = 0
    for e in es:
        if e["tag"].startswith("unit_commit:"):
            u = e["tag"].split(":", 1)[1]
            rows = [r for r in nudges if r["unit"] == u]
            fn = min(r["utc"] for r in rows) if rows else None
            ok = fn is None or e["utc"] < fn
            bad += not ok
            per_unit[u] = {"commit_utc": e["utc"], "first_nudge_utc": fn, "commit_before_first_nudge": ok,
                           "n_nudge_rows": len(rows)}
    enr = first.get("enrolment")
    out = {"chain": v, "commit0_utc": first.get("commit0"), "first_sample_utc": first_sample,
           "commit0_before_first_sample": first.get("commit0", "z") < first_sample,
           "analysis_addendum_utc": first.get("addendum1_pre_nudge_analysis_code"), "enrolment_utc": enr,
           "first_nudge_utc": first_nudge,
           "analysis_addendum_before_first_nudge": bool(first_nudge and first.get(
               "addendum1_pre_nudge_analysis_code", "z") < first_nudge),
           "enrolment_before_first_nudge": bool(first_nudge and enr and enr < first_nudge),
           "nudge_rows_before_enrolment": sum(1 for r in nudges if enr and r["utc"] < enr),
           "units": per_unit, "n_units_with_commit_after_first_nudge": bad}
    (ROOT / "results" / "commit_order.json").write_text(json.dumps(out, indent=1))
    print({k: out[k] for k in ("commit0_before_first_sample", "analysis_addendum_before_first_nudge",
                               "enrolment_before_first_nudge", "nudge_rows_before_enrolment",
                               "n_units_with_commit_after_first_nudge")}, v["chain_breaks"])


if __name__ == "__main__":
    main()
