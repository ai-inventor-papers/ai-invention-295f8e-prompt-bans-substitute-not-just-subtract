"""Regex grep over cached full texts (same windowing as the skill's fetch_grep), whitespace-collapsed for reading.

Usage: python -I tools/grep_cache.py KEY [-i] [-m N] [-C CHARS] PATTERN [PATTERN ...]
       python -I tools/grep_cache.py --spec spec.json      # [{"key":..,"patterns":[..],"i":true,"m":4,"C":220}, ...]
Each run is also appended to cache/grep_out/<key>.txt so the extraction can be re-read later.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CACHE, load_text, now_utc  # noqa: E402


def grep(key, patterns, ci=True, m=4, C=220):
    text = load_text(key)
    flat = re.sub(r"\s+", " ", text)
    out = [f"=== {key} ({len(text)} chars) ==="]
    for p in patterns:
        rx = re.compile(p, re.I if ci else 0)
        hits = list(rx.finditer(flat))
        out.append(f"--- /{p}/ : {len(hits)} matches")
        last_end = -1
        shown = 0
        for h in hits:
            if shown >= m:
                break
            s, e = max(0, h.start() - C), min(len(flat), h.end() + C)
            if s < last_end:          # merge overlapping windows like fetch_grep
                continue
            out.append(f"  @{h.start()}: ...{flat[s:e]}...")
            last_end = e
            shown += 1
    res = "\n".join(out)
    gdir = CACHE / "grep_out"
    gdir.mkdir(exist_ok=True)
    with (gdir / f"{key}.txt").open("a", encoding="utf-8") as fh:
        fh.write(f"\n##### {now_utc()}\n{res}\n")
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("key", nargs="?")
    ap.add_argument("patterns", nargs="*")
    ap.add_argument("--spec")
    ap.add_argument("-i", action="store_true")
    ap.add_argument("-m", type=int, default=4)
    ap.add_argument("-C", type=int, default=220)
    a = ap.parse_args()
    if a.spec:
        for job in json.loads(Path(a.spec).read_text()):
            print(grep(job["key"], job["patterns"], job.get("i", True), job.get("m", 4), job.get("C", 220)))
    else:
        print(grep(a.key, a.patterns, a.i, a.m, a.C))


if __name__ == "__main__":
    main()
