#!/usr/bin/env python3
"""README.md = docs_head.md (title, setup and the bottom line, written by hand from the results) + results/report6.md
(the generated tables) + docs_static.md (what was done, layout, how to run, restoring) + the deviations table."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg import RESULTS_DIR, ROOT, read_json


def main() -> None:
    head = (ROOT / "docs_head.md").read_text().rstrip() + "\n\n"
    rep = (RESULTS_DIR / "report6.md").read_text()
    rep = rep.replace("# Report (iteration 6, step 5: Gemma, Claim L replication)", "## Result tables").rstrip() + "\n\n"
    rep = rep.replace("\n### ", "\n#### ")
    static = (ROOT / "docs_static.md").read_text().rstrip() + "\n\n"
    dv = read_json(RESULTS_DIR / "deviations.json")
    keys = sorted(dv, key=lambda k: int(k[1:]) if k[1:].isdigit() else 999)
    dev = ["## Deviations (full text in `results/deviations.json`)", "", "| | Deviation |", "|---|---|"]
    dev += [f"| {k} | {dv[k]} |" for k in keys]
    (ROOT / "README.md").write_text(head + rep + static + "\n".join(dev) + "\n")
    print("README.md written")


if __name__ == "__main__":
    main()
