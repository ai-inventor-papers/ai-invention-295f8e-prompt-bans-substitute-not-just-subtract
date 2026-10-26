"""Final QA for the structured output: re-fetch every source URL live (skill fetch core: html2text / PyMuPDF / raw JSON)
and require each supporting passage to occur LITERALLY (whitespace-collapsed only) in the fetched text. Passages that
fail are removed from cache/sources.json; every check is logged to evidence/passages_live_check.jsonl.
Usage: python -I tools/check_passages_live.py
"""
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CACHE, EVID, F, now_utc  # noqa: E402


def check(src):
    if not src["supporting_passages"]:
        return src, []
    r = F._fetch_url(src["url"])
    flat = re.sub(r"\s+", " ", r.get("content", "")) if r.get("success") else ""
    logs, keep = [], []
    for p in src["supporting_passages"]:
        ok = bool(flat) and re.sub(r"\s+", " ", p["quote"]) in flat
        logs.append({"index": src["index"], "url": src["url"], "passage": p["quote"], "fetched": bool(r.get("success")),
                     "from_archive": r.get("from_archive"), "literal_match": ok, "checked_utc": now_utc()})
        if ok:
            keep.append(p)
    src = dict(src, supporting_passages=keep)
    return src, logs


def main():
    F.init_web_fetch()
    sources = json.loads((CACHE / "sources.json").read_text())
    with ThreadPoolExecutor(8) as ex:
        res = list(ex.map(check, sources))
    out, logs = [r[0] for r in res], [l for r in res for l in r[1]]
    (CACHE / "sources.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    (EVID / "passages_live_check.jsonl").write_text("".join(json.dumps(l, ensure_ascii=False) + "\n" for l in logs))
    ok = sum(l["literal_match"] for l in logs)
    print(f"live literal check: {ok}/{len(logs)} passages kept")
    for l in logs:
        if not l["literal_match"]:
            print("DROPPED:", l["index"], l["url"], "| fetched:", l["fetched"], "|", l["passage"][:80])


if __name__ == "__main__":
    main()
