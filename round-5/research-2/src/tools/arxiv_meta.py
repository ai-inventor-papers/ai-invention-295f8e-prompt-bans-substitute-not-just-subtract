"""Fetch authoritative arXiv metadata (latest version, v1 date, title, authors, comment, journal_ref)
for a list of IDs via the arXiv API (export.arxiv.org), and save evidence/arxiv_meta.json.

Usage: python -I tools/arxiv_meta.py ID [ID ...]   (merges into the existing file)
"""
import json
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import EVID, F, now_utc  # noqa: E402

NS = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}


def fetch_batch(ids):
    F.init_web_fetch()
    url = "https://export.arxiv.org/api/query?id_list=" + ",".join(ids) + f"&max_results={len(ids) + 5}"
    for attempt in range(4):
        r = F._session.get(url, timeout=120)
        if r.status_code == 200 and "<entry" in r.text:
            return r.text
        time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"arXiv API failed: HTTP {r.status_code}")


def parse(xml_text):
    root = ET.fromstring(xml_text)
    out = {}
    for e in root.findall("a:entry", NS):
        full_id = e.findtext("a:id", default="", namespaces=NS).rsplit("/abs/", 1)[-1]
        base, _, ver = full_id.rpartition("v")
        rec = {
            "arxiv_id": base,
            "latest_version": f"v{ver}",
            "v1_published": e.findtext("a:published", default="", namespaces=NS),
            "latest_updated": e.findtext("a:updated", default="", namespaces=NS),
            "title": " ".join(e.findtext("a:title", default="", namespaces=NS).split()),
            "authors": [a.findtext("a:name", default="", namespaces=NS) for a in e.findall("a:author", NS)],
            "comment": " ".join((e.findtext("arxiv:comment", default="", namespaces=NS) or "").split()),
            "journal_ref": " ".join((e.findtext("arxiv:journal_ref", default="", namespaces=NS) or "").split()),
            "doi": e.findtext("arxiv:doi", default="", namespaces=NS),
            "abstract": " ".join(e.findtext("a:summary", default="", namespaces=NS).split()),
            "retrieved_utc": now_utc(),
            "source": "export.arxiv.org/api/query?id_list=",
        }
        out[base] = rec
    return out


def main():
    ids = sys.argv[1:]
    path = EVID / "arxiv_meta.json"
    meta = json.loads(path.read_text()) if path.exists() else {}
    for i in range(0, len(ids), 40):
        meta.update(parse(fetch_batch(ids[i:i + 40])))
        time.sleep(3)
    path.write_text(json.dumps(meta, indent=1, ensure_ascii=False))
    for k in ids:
        m = meta.get(k)
        if not m:
            print(f"{k}\tNOT FOUND")
            continue
        print(f"{k}{m['latest_version']}\tv1={m['v1_published'][:10]}\tupd={m['latest_updated'][:10]}\t"
              f"{m['authors'][0] if m['authors'] else '?'} (+{len(m['authors']) - 1})\t{m['title'][:95]}\t"
              f"| C: {m['comment'][:150]}\t| J: {m['journal_ref'][:80]}")


if __name__ == "__main__":
    main()
