#!/usr/bin/env python3
"""Instrument reading of the iteration-9 PRIMARY programs that fail the v10 suites (iteration 9 admitted them under
its tier-B rule): their measured (disc, cont) is needed only to place them in the F1 mechanism analyses."""
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import programs  # noqa: E402
from accept import measure_all  # noqa: E402
from common import read_jsonl, sha256_text, write_jsonl  # noqa: E402

if __name__ == "__main__":
    rows = read_jsonl(Path("data/primary_measured.jsonl"))
    miss = [r for r in rows if not r.get("disc")]
    for r in miss:
        r["scrubbed"], _ = programs.scrub(r["code_in"])
        r["scrubbed_sha256"] = sha256_text(r["scrubbed"])
    meas = measure_all([r["scrubbed"] for r in miss])
    for r in miss:
        m = meas[r["scrubbed_sha256"]]
        r["disc"], r["cont"], r["fine"] = m["disc"], m["cont"], m.get("fine")
        r["measured_although_suite_fail"] = True
    write_jsonl(Path("data/primary_measured.jsonl"), rows)
    print(Counter((r["algorithm"], r["disc"], r["cont"]) for r in rows))
