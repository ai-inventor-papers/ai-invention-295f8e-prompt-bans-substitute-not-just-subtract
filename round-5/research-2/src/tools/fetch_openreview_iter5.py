"""Cache OpenReview ICLR 2027 submission records (title, abstract, venue) through the public notes/search API,
which is the URL quoted for VERIFIED-ABSTRACT rows. Usage: python -I tools/fetch_openreview_iter5.py FORUM_ID [...]"""
import json
import sys
import time
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CACHE, EVID, F, append_jsonl, now_utc  # noqa: E402

cands = {}
for line in (EVID / "saturation_candidates_iter5.jsonl").read_text().splitlines():
    c = json.loads(line)
    if c.get("openreview_id"):
        cands[c["openreview_id"]] = c
F.init_web_fetch()
for fid in sys.argv[1:]:
    title = cands[fid]["title"]
    url = ("https://api2.openreview.net/notes/search?term=" + urllib.parse.quote(title) +
           "&group=ICLR.cc/2027/Conference&limit=10")
    rec = None
    for attempt in range(4):
        r = F._session.get(url, timeout=60)
        if r.status_code == 200:
            for n in r.json().get("notes", []):
                if (n.get("forum") or n.get("id")) == fid:
                    rec = n
                    break
            break
        time.sleep(6 * (attempt + 1))
    if not rec:
        print(fid, "NOT FOUND", r.status_code)
        continue
    c = rec.get("content", {})
    txt = (f"forum: {fid}\nurl: https://openreview.net/forum?id={fid}\nvenue: {(c.get('venue') or {}).get('value', '')}\n"
           f"title: {(c.get('title') or {}).get('value', '')}\nabstract: {(c.get('abstract') or {}).get('value', '')}\n"
           f"pdf: {(c.get('pdf') or {}).get('value', '')}\ncdate: {rec.get('cdate')}\n")
    (CACHE / f"or_{fid}.txt").write_text(txt, encoding="utf-8")
    append_jsonl(CACHE / "index.jsonl", {"key": f"or_{fid}", "url": url, "is_pdf": False, "length": len(txt),
                                         "from_archive": False, "retrieved_utc": now_utc(),
                                         "forum_url": f"https://openreview.net/forum?id={fid}"})
    print(fid, "OK", (c.get('venue') or {}).get('value', ''), "| pdf:", bool((c.get('pdf') or {}).get('value')))
    time.sleep(2.5)
