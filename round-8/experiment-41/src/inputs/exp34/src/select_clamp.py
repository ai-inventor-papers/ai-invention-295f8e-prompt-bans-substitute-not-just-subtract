#!/usr/bin/env python3
"""P2-N selection rule (pre-declared): on T10 and T2, the 4 confirmed engine-d escapers (exp29 two-stage rule) with
the largest y; ties broken by the smaller seed. Writes results/clamp_selection.json."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from c7 import RESULTS, read_json, utc_now, write_json  # noqa: E402

fa = read_json(RESULTS / "f_analysis.json")
sel = {}
for task in ("T10", "T2"):
    rows = [r for r in fa["cells"][task] if r["confirmed"]]
    rows.sort(key=lambda r: (-r["y"], r["seed"]))
    sel[task] = [r["seed"] for r in rows[:4]]
write_json(RESULTS / "clamp_selection.json", {"utc": utc_now(), "rule": "4 confirmed escapers with the largest y",
                                              "seeds": sel})
print(sel)
