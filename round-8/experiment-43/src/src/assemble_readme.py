#!/usr/bin/env python3
"""README.md = README_head.md + README_results.md + README_static.md + deviations (results/deviations.json) +
README_restore.md. The parts are kept in docs/ after assembly."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def main() -> None:
    DOCS.mkdir(exist_ok=True)
    parts = []
    for name in ("README_head.md", "README_results.md", "README_static.md"):
        p = ROOT / name if (ROOT / name).exists() else DOCS / name
        parts.append(p.read_text().strip())
    devs = json.loads((ROOT / "results" / "deviations.json").read_text())
    lines = ["## Deviations from the plan", "",
             "Every deviation is recorded with its time in `results/deviations.json` (severity in brackets).", ""]
    for d in devs:
        lines.append(f"- **{d['id']}** [{d['severity']}]: {d['text']}")
    parts.append("\n".join(lines))
    p = ROOT / "README_restore.md" if (ROOT / "README_restore.md").exists() else DOCS / "README_restore.md"
    parts.append(p.read_text().strip())
    (ROOT / "README.md").write_text("\n\n".join(parts) + "\n")
    for name in ("README_head.md", "README_results.md", "README_static.md", "README_restore.md"):
        if (ROOT / name).exists():
            shutil.move(str(ROOT / name), str(DOCS / name))
    print("README.md written,", len((ROOT / "README.md").read_text()), "chars")


if __name__ == "__main__":
    main()
