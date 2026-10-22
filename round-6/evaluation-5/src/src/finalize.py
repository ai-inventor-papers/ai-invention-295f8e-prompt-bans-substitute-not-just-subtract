#!/usr/bin/env python3
"""Last step before publishing: strip NUL bytes from logs (rewritten while open) and replace absolute server paths in
every text file with placeholders; then report any absolute path that is left."""
import os
import re
from pathlib import Path

WS = Path(__file__).resolve().parent.parent
_DEPS = os.environ.get("AII_DEPS_ROOT", "")
_SKILL = os.environ.get("AII_JSON_SKILL_DIR", "")
SUBS = [(_DEPS, "<AII_DEPS_ROOT>"), (str(WS), "."), (str(Path(_DEPS).parent.parent) if _DEPS else "", "<RUNS>"),
        (str(Path(_SKILL).parent) if _SKILL else "", "<SKILLS>")]
TEXT = {".json", ".jsonl", ".csv", ".md", ".log", ".txt", ".yaml", ".py", ".toml"}


def main() -> None:
    changed, left = 0, []
    for p in WS.rglob("*"):
        rel = p.relative_to(WS).as_posix()
        if not p.is_file() or rel.startswith((".venv/", ".aii/", "inputs/")) or p.suffix not in TEXT:
            continue
        s = p.read_text(errors="replace")
        s2 = s.replace("\x00", "")
        for a, b in SUBS:
            if a and len(a) > 3:
                s2 = s2.replace(a, b)
        if s2 != s:
            p.write_text(s2)
            changed += 1
        if re.search("/" + "ai-" + "inventor/|/tmp/" + "claude", s2):
            left.append(rel)
    print(f"rewrote {changed} files; files still holding an absolute path: {left}")


if __name__ == "__main__":
    main()
