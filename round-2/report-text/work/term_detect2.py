"""Every quote-delimited span (double quotes, and overlapping pairs of single quotes or apostrophes
up to 12 words apart) and every code-like token in the text added this iteration, tables included."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
old = set((ROOT / "work" / "paper_draft_before_iter2.md").read_text(encoding="utf-8").split("\n"))
lines = [l for l in (ROOT / "paper_draft.md").read_text(encoding="utf-8").split("\n") if l not in old and l.strip()]

def strip_code(s):
    return re.sub(r"`[^`]*`", " ", s)

dq, sq, codes_prose = [], [], []
for l in lines:
    s = strip_code(l)
    table = l.lstrip().startswith("|")
    if not table:
        codes_prose += re.findall(r"\b[A-Z]+[0-9]+[A-Za-z0-9]*\b", s)
    dq += re.findall(r"[\"“”]([^\"“”]{1,200})[\"“”]", s)
    pos = [m.start() for m in re.finditer(r"['‘’]", s)]
    for a, b in zip(pos, pos[1:]):
        span = s[a + 1:b]
        if 1 <= len(span.split()) <= 12:
            sq.append(span)
print("codes in prose:", sorted(set(codes_prose)))
print("double-quoted spans:", len(dq))
for x in dq: print("  DQ|", x[:100])
print("single-quote/apostrophe spans (<=12 words):", len(sq))
for x in sq: print("  SQ|", x[:100])
