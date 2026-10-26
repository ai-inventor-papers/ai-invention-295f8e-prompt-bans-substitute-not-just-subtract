"""Cache full texts of papers for regex grep (plan step 0.3 source hierarchy: arXiv HTML vN -> arXiv PDF vN).

Usage:
  python -I tools/fetch_texts.py                 # every ID in evidence/arxiv_meta.json, latest version
  python -I tools/fetch_texts.py --url KEY URL   # one arbitrary page (venue PDF, proceedings page, ...)
Writes cache/<key>.txt and appends to cache/index.jsonl (key, url, is_pdf, length, retrieved_utc, from_archive).
"""
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CACHE, EVID, F, append_jsonl, cache_path, now_utc  # noqa: E402

MIN_LEN = 15000  # an arXiv "HTML not available" stub is far shorter than any paper


def fetch_one(key: str, urls: list[str], min_len: int = MIN_LEN) -> str:
    if cache_path(key).exists():
        return f"{key}: cached"
    last = ""
    for url in urls:
        r = F._fetch_url(url)
        if r.get("success") and len(r["content"]) >= min_len:
            cache_path(key).write_text(r["content"], encoding="utf-8")
            append_jsonl(CACHE / "index.jsonl", {"key": key, "url": url, "is_pdf": r["is_pdf"],
                                                 "length": len(r["content"]), "from_archive": r["from_archive"],
                                                 "retrieved_utc": now_utc()})
            return f"{key}: OK {url} ({len(r['content'])} chars, pdf={r['is_pdf']}, archive={r['from_archive']})"
        last = f"{url} -> {r.get('error') or 'short (' + str(len(r.get('content', ''))) + ' chars)'}"
    return f"{key}: FAILED {last}"


def main():
    F.init_web_fetch()
    if len(sys.argv) == 4 and sys.argv[1] == "--url":
        print(fetch_one(sys.argv[2], [sys.argv[3]], min_len=200))  # venue/policy pages can be short
        return
    meta = json.loads((EVID / "arxiv_meta.json").read_text())
    ids = sys.argv[1:] or list(meta)
    jobs = []
    for aid in ids:
        if "v" in aid.split(".")[-1]:          # explicit version requested, e.g. 2606.14530v1
            base, ver = aid.split("v")[0], "v" + aid.split("v")[1]
        else:
            base, ver = aid, meta[aid]["latest_version"]
        key = f"{base}{ver}"
        jobs.append((key, [f"https://arxiv.org/html/{key}", f"https://arxiv.org/pdf/{key}"]))
    with ThreadPoolExecutor(6) as ex:
        for line in ex.map(lambda j: fetch_one(*j), jobs):
            print(line, flush=True)


if __name__ == "__main__":
    main()
