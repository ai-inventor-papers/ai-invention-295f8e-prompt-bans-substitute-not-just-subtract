"""Resolve candidate titles to arXiv / Semantic Scholar records (seed-verification lookups, logged as such).
Usage: python -I tools/lookup_titles_iter6.py "TITLE" [...]"""
import json
import os
import sys
import time
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import EVID, F, append_jsonl, now_utc  # noqa: E402

F.init_web_fetch()
NS = {"a": "http://www.w3.org/2005/Atom"}
key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "")
for t in sys.argv[1:]:
    q = urllib.parse.quote('ti:"' + t.replace(":", " ").replace('"', "") + '"')
    r = F._session.get(f"https://export.arxiv.org/api/query?search_query={q}&max_results=3", timeout=60)
    hits = []
    try:
        for e in ET.fromstring(r.text).findall("a:entry", NS):
            hits.append((e.findtext("a:id", namespaces=NS), " ".join(e.findtext("a:title", namespaces=NS).split())))
    except Exception as ex:
        hits.append(("arxiv-error", str(ex)))
    time.sleep(3.1)
    s2 = F._session.get("https://api.semanticscholar.org/graph/v1/paper/search/match?query=" + urllib.parse.quote(t)
                        + "&fields=title,externalIds,venue,publicationDate,url,openAccessPdf", headers={"x-api-key": key} if key else {}, timeout=60)
    s2d = (s2.json().get("data") or [{}])[0] if s2.status_code == 200 else {"status": s2.status_code}
    print(f"### {t}\n arXiv: {hits}\n S2: {json.dumps(s2d)[:600]}\n")
    append_jsonl(EVID / "search_log_iter6.jsonl", {"family": "SEED-LOOKUP", "query": t, "engine": "arXiv API ti: + S2 /paper/search/match",
                                                 "date_filter": "none", "n_results": len(hits), "status": "ok", "timestamp_utc": now_utc(),
                                                 "note": "title resolution for screening/verification, not a saturation query (not counted)"})
    time.sleep(1.1)
