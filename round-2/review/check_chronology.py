"""Check that the iteration-1 section of the iteration-2 report changed only through marked corrections.

Extracts '# Iteration 1 ...' up to the next top-level section from the iteration-1 and iteration-2 report drafts,
strips the in-place correction markers of the new draft (*(Correction ...)*, *(Corrected ...)*, *(Added ...)*,
*(Note added ...)*), and prints a unified diff of what remains. Run: python3 check_chronology.py
"""
import difflib
import os
import re
import textwrap
from pathlib import Path

# Runs root: this script sits at <runs>/run_aRfWvcSWjssb/3_invention_loop/iter_2/review_report/review_report/.
RUNS = Path(os.environ.get("AII_RUNS_ROOT", Path(__file__).resolve().parents[5]))
LOOP = RUNS / "run_aRfWvcSWjssb/3_invention_loop"
OLD = LOOP / "round-1/report-text/paper_draft.md"
NEW = LOOP / "round-2/report-text/paper_draft.md"
MARKER = re.compile(r"\s?\*\((?:Correction|Corrected|Added|Note added)[^*]*?\)\*")


def section(text: str, start: str, end: str) -> str:
    i = text.index(start)
    return text[i:text.index(end, i)]


def wrapped(text: str) -> list[str]:
    out = []
    for line in text.splitlines():
        out.extend(textwrap.wrap(line, 160) or [""])
    return out


def main() -> None:
    old = section(OLD.read_text(), "# Iteration 1", "# What we have learned")
    new = section(NEW.read_text(), "# Iteration 1", "# Iteration 2")
    n_markers = len(MARKER.findall(new))
    diff = list(difflib.unified_diff(wrapped(old), wrapped(MARKER.sub("", new)), "iter1_draft", "iter2_draft_markers_stripped", n=0))
    print(f"markers stripped from the iteration-2 copy: {n_markers}")
    print("\n".join(diff) if diff else "no differences beyond marked corrections")


if __name__ == "__main__":
    main()
