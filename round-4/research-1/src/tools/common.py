"""Shared helpers: workspace paths, the plan's quote-normalisation rule, and grep over cached texts.

Fetching reuses the aii-web-tools skill's own fetch core (aii_fast_web_fetch._fetch_url), so cached
texts are byte-for-byte what the skill's fetch/fetch_grep would see.
"""
import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

WS = Path(__file__).resolve().parents[1]
CACHE = WS / "cache"
EVID = WS / "evidence"
SKILL_SCRIPTS = Path(__file__).resolve().parents[4] / "tools/aii-web-tools/scripts"
sys.path.insert(0, str(SKILL_SCRIPTS))
import aii_fast_web_fetch as F  # noqa: E402  (skill fetch core)

LIGATURES = {"ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl", "ﬃ": "ffi", "ﬄ": "ffl", "ﬅ": "st", "ﬆ": "st"}
QUOTES = {"‘": "'", "’": "'", "‚": "'", "‛": "'", "′": "'", "“": '"', "”": '"',
          "„": '"', "‟": '"', "″": '"', "–": "-", "—": "-", "‒": "-", "‐": "-",
          "‑": "-", "−": "-", " ": " ", " ": " ", " ": " ", " ": " ", " ": " "}


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def normalise(s: str) -> str:
    """Plan rule 0.6: undo PDF line-end hyphenation, map ligatures, curly quotes and dashes,
    strip markdown/html2text escapes and emphasis, collapse whitespace."""
    s = unicodedata.normalize("NFKC", s)
    for k, v in {**LIGATURES, **QUOTES}.items():
        s = s.replace(k, v)
    s = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", s)          # PDF line-end hyphenation
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)        # markdown links -> text
    s = re.sub(r"\\([\\`*_{}\[\]()#+\-.!>|~])", r"\1", s)  # html2text escapes
    s = s.replace("**", "").replace("__", "")
    s = re.sub(r"(?<!\w)_(?=\w)|(?<=\w)_(?!\w)", "", s)   # _emphasis_
    s = re.sub(r"(?<![\w*])\*(?=\S)|(?<=\S)\*(?![\w*])", "", s)
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r" ([,.;:!?)])", r"\1", s)                 # html2text leaves "word_ ," after emphasis
    return s.strip()


def quote_matches(quote: str, text_norm: str) -> bool:
    """A quote with [...] elisions matches if every segment occurs, in order, in the normalised text."""
    segs = [normalise(x) for x in re.split(r"\s*\[\.\.\.\]\s*|\s*\[…\]\s*", quote) if x.strip()]
    pos = 0
    for seg in segs:
        i = text_norm.find(seg, pos)
        if i < 0:
            # tolerate a trailing period difference at segment ends
            i = text_norm.find(seg.rstrip(".").strip(), pos)
            if i < 0:
                return False
        pos = i + len(seg)
    return True


def cache_path(key: str) -> Path:
    return CACHE / f"{key}.txt"


def load_text(key: str) -> str:
    return cache_path(key).read_text(encoding="utf-8")


def append_jsonl(path: Path, rec: dict) -> None:
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
