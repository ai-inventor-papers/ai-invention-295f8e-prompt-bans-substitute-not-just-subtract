"""Cache OpenReview ICLR 2027 submission records (title, abstract, venue, pdf field, cdate) through the public notes/search API
(forum HTML returns a browser check). The API URL is the locator quoted for VERIFIED-ABSTRACT rows.
Usage: python -I tools/fetch_openreview_iter6.py FORUM_ID [FORUM_ID ...]"""
import json
import sys
import time
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CACHE, EVID, F, append_jsonl, now_utc  # noqa: E402

cands = {}
for line in (EVID / "saturation_candidates_iter6.jsonl").read_text().splitlines():
    c = json.loads(line)
    if c.get("openreview_id"):
        cands[c["openreview_id"]] = c
F.init_web_fetch()
for fid in sys.argv[1:]:
    if (CACHE / f"or_{fid}.txt").exists():
        print(fid, "cached")
        continue
    title = cands[fid]["title"]
    url = ("https://api2.openreview.net/notes/search?term=" + urllib.parse.quote(title) +
           "&group=ICLR.cc/2027/Conference&limit=10")
    rec, code = None, None
    for attempt in range(5):
        r = F._session.get(url, timeout=60)
        code = r.status_code
        if code == 200:
            for n in r.json().get("notes", []):
                if (n.get("forum") or n.get("id")) == fid:
                    rec = n
                    break
            break
        time.sleep(6 * (attempt + 1))
    if not rec:
        print(fid, "NOT FOUND", code)
        continue
    c = rec.get("content", {})
    txt = (f"forum: {fid}\nurl: https://openreview.net/forum?id={fid}\nvenue: {(c.get('venue') or {}).get('value', '')}\n"
           f"title: {(c.get('title') or {}).get('value', '')}\nabstract: {(c.get('abstract') or {}).get('value', '')}\n"
           f"pdf: {(c.get('pdf') or {}).get('value', '')}\ncdate: {rec.get('cdate')}\n")
    (CACHE / f"or_{fid}.txt").write_text(txt, encoding="utf-8")
    append_jsonl(CACHE / "index.jsonl", {"key": f"or_{fid}", "url": url, "is_pdf": False, "length": len(txt),
                                         "from_archive": False, "retrieved_utc": now_utc(),
                                         "forum_url": f"https://openreview.net/forum?id={fid}", "via": url})
    print(fid, "OK", (c.get("venue") or {}).get("value", ""), "| pdf:", (c.get("pdf") or {}).get("value", ""), "| cdate", rec.get("cdate"))
    time.sleep(2.0)
