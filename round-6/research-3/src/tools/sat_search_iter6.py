"""Dated saturation search (plan Step 3, round 1 + snowballing) over the frozen protocol in evidence/protocol_iter6.json.

Engines: E1 OpenAlex/Crossref (aii-web-tools scholarly search; lanes L1, L4, L6), E3 arXiv API (newest first), E4 Semantic
Scholar (year=2026), E5 OpenReview ICLR 2027 pool (notes/search API). E6 (grey literature) runs through the built-in
WebSearch tool and is logged by tools/log_e6.py. Every call is logged to evidence/search_log_iter6.jsonl with UTC time,
engine, string, hit count and the top-20 ids; raw results go to cache/search_results/; de-duplicated candidates go to
evidence/saturation_candidates_iter6.jsonl.

Usage: python -I tools/sat_search_iter6.py --round1 | --fc | --round2 FILE | --aggregate
Needs SEMANTIC_SCHOLAR_API_KEY for E4 (anonymous fallback is logged).
"""
import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.parse
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CACHE, EVID, F, SKILL_PY, SKILL_SCRIPTS, append_jsonl, now_utc  # noqa: E402

SEARCH_PY = str(SKILL_SCRIPTS / "aii_fast_web_search.py")
PY = SKILL_PY
RAW = CACHE / "search_results"
LOG = EVID / "search_log_iter6.jsonl"
LOCK = threading.Lock()
PROTO = json.loads((EVID / "protocol_iter6.json").read_text())
QUERIES = PROTO["queries"]
FC_SEEDS = {"MIB": "arXiv:2504.13151", "ERP": "arXiv:2502.06258", "SteeringUnderCompression": "arXiv:2609.06473"}
NLA_TITLE = "Natural Language Autoencoders Produce Unsupervised Explanations of LLM Activations"


def ident(it):
    return it.get("arxiv_id") or ("OR:" + it["openreview_id"] if it.get("openreview_id") else
                                  ("DOI:" + it["doi"] if it.get("doi") else it.get("title", "")[:60]))


def log(qid, lane, string, engine, items, status, rnd, extra=None):
    rec = {"round": rnd, "query_id": qid, "lane": lane, "string": string, "engine": engine, "n_results": len(items),
           "status": status, "top20_ids": [ident(i) for i in items[:20]], "timestamp_utc": now_utc()}
    if extra:
        rec.update(extra)
    with LOCK:
        append_jsonl(LOG, rec)


def save_raw(name, items):
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / f"{name}.json").write_text(json.dumps(items, ensure_ascii=False, indent=1))


def arxiv_id_from(s):
    m = re.search(r"(?:arxiv[.:/ ]*(?:abs/|html/|pdf/)?|10\.48550/arxiv\.)(\d{4}\.\d{4,5})", s or "", re.I)
    return m.group(1) if m else ""


def e1(q, rnd="R1"):
    out = subprocess.run([PY, SEARCH_PY, "--query", q["plan_string"].replace("'", ""), "--mode", "scholarly", "--max-results", "25"],
                         capture_output=True, text=True, timeout=240).stdout
    items = []
    for m in re.finditer(r"^\s*\d+\.\s+(.+)\n\s+(\S+)\n\s+(.*)$", out, re.M):
        title, url, meta = m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
        year = re.search(r"\b(20\d\d)\b", meta)
        doi = re.search(r"doi\.org/(\S+)", url)
        items.append({"title": title, "url": url, "year": year.group(1) if year else "", "arxiv_id": arxiv_id_from(url + " " + meta),
                      "doi": doi.group(1) if doi else ""})
    save_raw(f"{rnd}_{q['id']}_E1", items)
    log(q["id"], q["lane"], q["plan_string"], "E1 OpenAlex/Crossref (aii_fast_web_search.py --mode scholarly)", items,
        "ok" if items else "empty", rnd)
    return [("E1", q, it) for it in items]


def e3(q, rnd="R1"):
    sq = q["arxiv_api"]
    url = ("http://export.arxiv.org/api/query?search_query=" + urllib.parse.quote(sq) +
           "&sortBy=submittedDate&sortOrder=descending&max_results=25")
    ns = {"a": "http://www.w3.org/2005/Atom"}
    items, status = [], "ok"
    for attempt in range(5):
        try:
            r = F._session.get(url, timeout=90)
            if r.status_code == 429:
                status = "retry:HTTP429"
                time.sleep(15 * (attempt + 1))
                continue
            root = ET.fromstring(r.text)
            for e in root.findall("a:entry", ns):
                aid = e.findtext("a:id", default="", namespaces=ns).rsplit("/abs/", 1)[-1]
                items.append({"title": " ".join(e.findtext("a:title", default="", namespaces=ns).split()),
                              "arxiv_id": re.sub(r"v\d+$", "", aid), "v1_date": e.findtext("a:published", default="", namespaces=ns)[:10],
                              "abstract": " ".join(e.findtext("a:summary", default="", namespaces=ns).split())[:1500]})
            status = "ok"
            break
        except Exception as ex:
            status = f"retry:{type(ex).__name__}"
            time.sleep(5)
    save_raw(f"{rnd}_{q['id']}_E3", items)
    log(q["id"], q["lane"], q["plan_string"], "E3 arXiv API (sortBy=submittedDate desc)", items, status, rnd,
        extra={"arxiv_query": sq, "date_filter": "window 2026-01-01..2026-10-22 applied at screening"})
    time.sleep(3.2)
    return [("E3", q, it) for it in items]


def s2_get(url):
    key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "")
    headers = {"x-api-key": key} if key else {}
    code = None
    for attempt in range(6):
        r = F._session.get(url, headers=headers, timeout=60)
        code = r.status_code
        if code == 200:
            return r.json(), "ok" + ("" if key else " (anonymous)")
        time.sleep(2 + 3 * attempt)
    return None, f"HTTP {code} after backoff"


def e4(q, rnd="R1"):
    url = ("https://api.semanticscholar.org/graph/v1/paper/search?query=" + urllib.parse.quote(q["s2_openreview_term"]) +
           "&year=2026&fields=title,externalIds,publicationDate,venue,abstract&limit=25")
    js, status = s2_get(url)
    items = []
    for p in (js or {}).get("data", []) or []:
        items.append({"title": p.get("title", ""), "arxiv_id": (p.get("externalIds") or {}).get("ArXiv", ""),
                      "doi": (p.get("externalIds") or {}).get("DOI", ""), "pub_date": p.get("publicationDate") or "",
                      "venue": p.get("venue") or "", "abstract": (p.get("abstract") or "")[:1500]})
    save_raw(f"{rnd}_{q['id']}_E4", items)
    log(q["id"], q["lane"], q["s2_openreview_term"], "E4 Semantic Scholar API", items, status, rnd, extra={"date_filter": "year=2026"})
    time.sleep(1.1)
    return [("E4", q, it) for it in items]


def e5(q, rnd="R1"):
    url = ("https://api2.openreview.net/notes/search?term=" + urllib.parse.quote(q["s2_openreview_term"]) +
           "&group=ICLR.cc/2027/Conference&limit=25")
    items, status = [], "ok"
    for attempt in range(4):
        try:
            r = F._session.get(url, timeout=60)
            if r.status_code != 200:
                status = f"HTTP {r.status_code}"
                time.sleep(5 * (attempt + 1))
                continue
            for n in r.json().get("notes", []):
                c = n.get("content", {})
                items.append({"title": (c.get("title") or {}).get("value", ""), "openreview_id": n.get("forum") or n.get("id"),
                              "venue": (c.get("venue") or {}).get("value", ""),
                              "abstract": ((c.get("abstract") or {}).get("value", "") or "")[:1500]})
            status = "ok"
            break
        except Exception as ex:
            status = f"error:{type(ex).__name__}"
            time.sleep(4)
    save_raw(f"{rnd}_{q['id']}_E5", items)
    log(q["id"], q["lane"], q["s2_openreview_term"], "E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/2027/Conference)",
        items, status, rnd, extra={"date_filter": "ICLR 2027 submissions"})
    time.sleep(1.0)
    return [("E5", q, it) for it in items]


def citers(paper_ref, name, rnd="FC"):
    items, offset, status = [], 0, "ok"
    while offset < 1000:
        url = (f"https://api.semanticscholar.org/graph/v1/paper/{paper_ref}/citations?fields=title,externalIds,"
               f"publicationDate,venue,abstract&limit=100&offset={offset}")
        js, status = s2_get(url)
        data = (js or {}).get("data", []) or []
        for d in data:
            p = d.get("citingPaper") or {}
            items.append({"title": p.get("title", ""), "arxiv_id": (p.get("externalIds") or {}).get("ArXiv", ""),
                          "doi": (p.get("externalIds") or {}).get("DOI", ""), "pub_date": p.get("publicationDate") or "",
                          "venue": p.get("venue") or "", "abstract": (p.get("abstract") or "")[:1500], "cites": name})
        if len(data) < 100:
            break
        offset += 100
        time.sleep(1.1)
    save_raw(f"FC_{name}", items)
    q = {"id": f"FC-{name}", "lane": "snowball"}
    log(q["id"], "snowball", f"forward citations of {paper_ref} ({name})", "E4 Semantic Scholar citations API", items, status, rnd,
        extra={"date_filter": "all citers; window applied at screening"})
    return items


def references(paper_ref, name, rnd="BR"):
    url = (f"https://api.semanticscholar.org/graph/v1/paper/{paper_ref}/references?fields=title,externalIds,"
           f"publicationDate,venue,abstract&limit=500")
    js, status = s2_get(url)
    items = []
    for d in (js or {}).get("data", []) or []:
        p = d.get("citedPaper") or {}
        items.append({"title": p.get("title", ""), "arxiv_id": (p.get("externalIds") or {}).get("ArXiv", ""),
                      "doi": (p.get("externalIds") or {}).get("DOI", ""), "pub_date": p.get("publicationDate") or "",
                      "venue": p.get("venue") or "", "abstract": (p.get("abstract") or "")[:1500], "cites": "ref-of-" + name})
    save_raw(f"BR_{name}", items)
    log(f"BR-{name}", "snowball", f"backward references of {paper_ref} ({name})", "E4 Semantic Scholar references API", items, status, rnd)
    return items


def forward():
    out = {}
    # NLA paper: resolve by title on Semantic Scholar
    url = ("https://api.semanticscholar.org/graph/v1/paper/search?query=" + urllib.parse.quote(NLA_TITLE) +
           "&fields=title,externalIds,publicationDate,venue&limit=5")
    js, status = s2_get(url)
    hits = (js or {}).get("data", []) or []
    match = [h for h in hits if "natural language autoencoder" in (h.get("title") or "").lower()]
    log("FC-NLA-resolve", "snowball", NLA_TITLE, "E4 Semantic Scholar title search (resolve NLA paperId)",
        [{"title": h.get("title", "")} for h in hits], status, "FC", extra={"resolved": bool(match)})
    if match:
        out["NLA"] = citers(match[0]["paperId"], "NLA")
    for name, ref in FC_SEEDS.items():
        out[name] = citers(ref, name)
        time.sleep(1.1)
    if not out.get("SteeringUnderCompression"):
        references("arXiv:2609.06473", "2609.06473")
        references("arXiv:2606.03002", "2606.03002")
    for k, v in out.items():
        print(f"FC {k}: {len(v)} citers")


def norm_title(t):
    return re.sub(r"[^a-z0-9]+", " ", (t or "").lower()).strip()


def aggregate():
    cand = {}
    n_raw = 0
    for f in sorted(RAW.glob("*.json")):
        name = f.stem
        parts = name.split("_")
        if parts[0] in ("FC", "BR"):
            eng, qid, rnd = parts[0], "snowball", parts[0]
        else:
            rnd, qid, eng = parts[0], parts[1], parts[2]
        lane = next((q["lane"] for q in QUERIES if q["id"] == qid), "R2" if rnd == "R2" else "snowball")
        for it in json.loads(f.read_text()):
            n_raw += 1
            key = it.get("arxiv_id") or ("or:" + it["openreview_id"] if it.get("openreview_id") else "t:" + norm_title(it.get("title")))
            c = cand.setdefault(key, {"key": key, "title": it.get("title", ""), "arxiv_id": it.get("arxiv_id", ""),
                                      "openreview_id": it.get("openreview_id", ""), "doi": it.get("doi", ""), "dates": set(),
                                      "venue": set(), "lanes": set(), "queries": set(), "engines": set(), "rounds": set(),
                                      "cites": set(), "abstract": ""})
            for fld in ("v1_date", "pub_date", "year"):
                if it.get(fld):
                    c["dates"].add(str(it[fld]))
            if it.get("venue"):
                c["venue"].add(it["venue"])
            if it.get("cites"):
                c["cites"].add(it["cites"])
            c["lanes"].add(lane)
            c["queries"].add(qid)
            c["engines"].add(eng)
            c["rounds"].add(rnd)
            if len(it.get("abstract", "") or "") > len(c["abstract"]):
                c["abstract"] = it["abstract"]
    path = EVID / "saturation_candidates_iter6.jsonl"
    with path.open("w", encoding="utf-8") as fh:
        for c in cand.values():
            for k in ("dates", "venue", "lanes", "queries", "engines", "rounds", "cites"):
                c[k] = sorted(c[k])
            fh.write(json.dumps(c, ensure_ascii=False) + "\n")
    print(f"identified (raw hits): {n_raw}; unique after de-duplication: {len(cand)}")


def round_run(queries, rnd):
    e1_lanes = set(PROTO["round1_engine_assignment"]["L1,L4,L6"] and ["L1", "L4", "L6"])

    def run_e1():
        with ThreadPoolExecutor(3) as ex:
            return list(ex.map(lambda q: e1(q, rnd), [q for q in queries if q["lane"] in e1_lanes or rnd != "R1"]))

    def run_e3():
        return [e3(q, rnd) for q in queries]

    def run_e4():
        return [e4(q, rnd) for q in queries]

    def run_e5():
        return [e5(q, rnd) for q in queries]

    with ThreadPoolExecutor(4) as ex:
        futs = [ex.submit(fn) for fn in (run_e1, run_e3, run_e4, run_e5)]
        for fu in futs:
            fu.result()


def main():
    F.init_web_fetch()
    if "--round1" in sys.argv:
        round_run(QUERIES, "R1")
    elif "--fc" in sys.argv:
        forward()
    elif "--round2" in sys.argv:
        qs = json.loads(Path(sys.argv[sys.argv.index("--round2") + 1]).read_text())
        round_run(qs, "R2")
    aggregate()


if __name__ == "__main__":
    main()
