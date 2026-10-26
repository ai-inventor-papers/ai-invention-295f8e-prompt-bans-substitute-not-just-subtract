"""Assemble paper_draft.md: iteration-1 text (with its marked corrections) + the iteration-2
section + the rewritten closing section + the extended reference list.

Citations in the new text are written as {{BibKey}}. Keys already in the iteration-1 reference
list keep their numbers; new keys are numbered from 39 in order of first appearance.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "work"
DRAFT = ROOT / "paper_draft.md"
BASE = WORK / "paper_draft_corrected_base.md"  # iteration-1 text with its marked corrections
BIB = ROOT / "references.bib"

OLD = ["Narula2026", "Wu2024", "Jangra2026", "Yoon2026", "Yang2025", "Kwon2023", "Rana2026", "Wilson1927",
       "Hill1973", "Gneiting2007", "Cohen1960", "Xia2025", "Du2024", "Markeeva2024", "Liu2023", "Qiu2024",
       "Brysbaert2013", "Brysbaert2009", "Xu2025", "Zhu2022", "Kendall1939", "Grattafiori2024", "Lu2024",
       "Hewitt2019", "Tenenbaum2000", "Facco2017", "Wurgaft2026", "Marshall2024", "Arditi2024", "Bigelow2024",
       "Bigelow2026", "Zhu2024", "Killick2012", "Wu2025", "West2025", "Yun2025", "Peeperkorn2024", "Tang2026"]
PARTS = ["part1.md", "part2.md", "part3.md", "part4.md", "part5.md"]
CLOSING = "closing.md"


def parse_bib(text: str) -> dict:
    entries = {}
    for m in re.finditer(r"@(\w+)\{([^,]+),(.*?)\n\}", text, re.S):
        key, body = m.group(2).strip(), m.group(3)
        fields = {}
        for f in re.finditer(r"(\w+)\s*=\s*\{((?:[^{}]|\{[^{}]*\})*)\}", body, re.S):
            fields[f.group(1).lower()] = " ".join(f.group(2).split())
        entries[key] = fields
    return entries


def clean(s: str) -> str:
    return s.replace("{", "").replace("}", "").replace("``", '"').replace("''", '"').strip()


def first_author(author: str) -> str:
    first = clean(author).split(" and ")[0].strip()
    if "," in first:
        return first.split(",")[0].strip()
    return first.split()[-1]


def ref_line(n: int, f: dict) -> str:
    authors = clean(f.get("author", ""))
    multi = " and " in authors or "others" in authors
    name = first_author(f.get("author", "Anonymous")) + (" et al." if multi else ".")
    title = clean(f.get("title", "")).rstrip(".")
    venue = clean(f.get("journal", f.get("booktitle", "")))
    year = f.get("year", "")
    end = "" if title.endswith(("?", "!")) else "."
    parts = [f"[{n}] {name} {title}{end}"]
    if venue:
        parts.append(f"{venue}.")
    if year:
        parts.append(f"{year}.")
    return " ".join(parts)


def main() -> None:
    bib = parse_bib(BIB.read_text(encoding="utf-8"))
    numbers = {k: i + 1 for i, k in enumerate(OLD)}
    texts = [(WORK / p).read_text(encoding="utf-8") for p in PARTS]
    closing = (WORK / CLOSING).read_text(encoding="utf-8")
    new_keys = []
    for t in texts + [closing]:
        for k in re.findall(r"\{\{(\w+)\}\}", t):
            if k not in numbers:
                if k not in bib:
                    raise SystemExit(f"citation key not in references.bib: {k}")
                numbers[k] = len(numbers) + 1
                new_keys.append(k)

    def sub(t: str) -> str:
        return re.sub(r"\{\{(\w+)\}\}", lambda m: str(numbers[m.group(1)]), t)

    section = "\n".join(sub(t).rstrip() + "\n" for t in texts)
    closing = sub(closing).rstrip() + "\n"

    draft = BASE.read_text(encoding="utf-8")
    i_close = draft.index("# What we have learned so far")
    i_refs = draft.index("# References")
    head = draft[:i_close].rstrip() + "\n\n"
    refs = draft[i_refs:].rstrip() + "\n"
    new_refs = "\n".join(ref_line(numbers[k], bib[k]) for k in new_keys)
    out = head + section + "\n" + closing + "\n" + refs + new_refs + "\n"
    DRAFT.write_text(out, encoding="utf-8")
    print("new references:", [(numbers[k], k) for k in new_keys])
    print("chars:", len(out))


if __name__ == "__main__":
    main()
