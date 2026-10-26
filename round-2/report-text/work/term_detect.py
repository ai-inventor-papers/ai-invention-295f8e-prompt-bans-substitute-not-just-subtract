"""List terminology-check candidates in the text added this iteration.

New text = lines of paper_draft.md that are not in the pre-iteration copy. Table rows (lines starting
with '|') are skipped. Candidates: code-like tokens (capitals followed by digits), double-quoted spans,
and spans between two straight or curly single quotes (which also catches pairs of possessives).
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
old = set((ROOT / "work" / "paper_draft_before_iter2.md").read_text(encoding="utf-8").split("\n"))
new_lines = [l for l in (ROOT / "paper_draft.md").read_text(encoding="utf-8").split("\n") if l not in old]
prose = [l for l in new_lines if l.strip() and not l.lstrip().startswith("|")]

def strip_code(s: str) -> str:
    return re.sub(r"`[^`]*`", " ", s)

codes, dq, sq = {}, {}, {}
for l in prose:
    s = strip_code(l)
    for m in re.finditer(r"\b[A-Z]+[0-9]+[A-Za-z0-9]*\b", s):
        codes[m.group(0)] = codes.get(m.group(0), 0) + 1
    for m in re.finditer(r"[\"“]([^\"“”]{1,200})[\"”]", s):
        dq[m.group(1)] = dq.get(m.group(1), 0) + 1
    for m in re.finditer(r"['‘’]([^'‘’\n]{1,200})['‘’]", s):
        sq[m.group(1)] = sq.get(m.group(1), 0) + 1

print("NEW PROSE LINES:", len(prose))
print("CODES:", codes)
print("DOUBLE-QUOTED:", len(dq))
for k, v in sorted(dq.items()):
    print("  dq|", k[:110], "|x", v)
print("SINGLE-QUOTE SPANS:", len(sq))
if "-v" in sys.argv:
    for k, v in sorted(sq.items()):
        print("  sq|", k[:110], "|x", v)
