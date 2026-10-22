"""Cache OpenReview ICLR 2027 submission records (title, abstract, keywords, TL;DR, venue, primary area, dates) through the
public API v2 notes/search endpoint (term = the record's title, group = ICLR.cc/2027/Conference). The notes?id= endpoint
returned HTTP 403 'ChallengeRequiredError' on 2026-10-21 ~23:58 UTC, and OpenReview PDFs return 403, so this search URL is
the URL quoted for VERIFIED-ABSTRACT rows (as in the iteration-5 audit).
Usage: python -I tools/fetch_openreview_iter6.py FORUM_ID [...]"""
import json
import sys
import time
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CACHE, EVID, F, append_jsonl, now_utc  # noqa: E402

TITLES = {}
for line in (EVID / "saturation_candidates_iter6.jsonl").read_text().splitlines():
    c = json.loads(line)
    if c.get("openreview_id"):
        TITLES[c["openreview_id"]] = c["title"]
for line in (Path(__file__).resolve().parents[1] / "inherited" / "iter5" / "saturation_candidates_iter5.jsonl").read_text().splitlines():
    c = json.loads(line)
    if c.get("openreview_id") and c["openreview_id"] not in TITLES:
        TITLES[c["openreview_id"]] = c["title"]
F.init_web_fetch()
for fid in sys.argv[1:]:
    title = TITLES.get(fid)
    if not title:
        print(fid, "no title in candidate files")
        continue
    url = ("https://api2.openreview.net/notes/search?term=" + urllib.parse.quote(title) +
           "&group=ICLR.cc/2027/Conference&limit=10")
    rec, code = None, None
    for attempt in range(3):
        r = F._session.get(url, timeout=30)
        code = r.status_code
        if code == 200:
            for n in r.json().get("notes", []):
                if (n.get("forum") or n.get("id")) == fid:
                    rec = n
            break
        time.sleep(6 * (attempt + 1))
    if not rec:
        print(fid, "NOT FOUND", code)
        continue
    c = rec.get("content", {})
    v = lambda k: (c.get(k) or {}).get("value", "")  # noqa: E731
    kw = v("keywords")
    txt = (f"forum: {fid}\nurl: https://openreview.net/forum?id={fid}\napi_url: {url}\nvenue: {v('venue')}\n"
           f"title: {v('title')}\nkeywords: {', '.join(kw) if isinstance(kw, list) else kw}\nTLDR: {v('TLDR')}\n"
           f"primary_area: {v('primary_area')}\nabstract: {v('abstract')}\ncdate: {rec.get('cdate')}\npdate: {rec.get('pdate')}\n")
    (CACHE / f"or_{fid}.txt").write_text(txt, encoding="utf-8")
    append_jsonl(CACHE / "index.jsonl", {"key": f"or_{fid}", "url": url, "is_pdf": False, "length": len(txt),
                                         "from_archive": False, "retrieved_utc": now_utc(),
                                         "forum_url": f"https://openreview.net/forum?id={fid}"})
    print(f"{fid} OK | {v('venue')} | kw: {kw} | TLDR: {v('TLDR')[:400]}")
    time.sleep(1.5)
