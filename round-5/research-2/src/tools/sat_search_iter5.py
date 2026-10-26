"""Dated saturation search for the iteration-5 claims (plan Stage 2): the 9 query families frozen in
evidence/protocol.json, each run on E1 (OpenAlex/Crossref scholarly search via the aii-web-tools script), E3 (arXiv API,
newest first, cs.CL/cs.LG/cs.AI), E4 (Semantic Scholar API, year=2026) and E5 (OpenReview ICLR 2027 pool); plus forward
citations (Semantic Scholar for 8 seeds, OpenAlex cites: for the 4 nearest neighbours) and backward citations on demand.

Every call is logged to evidence/search_log_iter5.jsonl; raw results go to cache/search_results/; de-duplicated
candidates go to evidence/saturation_candidates_iter5.jsonl (one line per unique paper, with the families/engines that
surfaced it and whether the iteration-4 audit had already seen it).

Usage: python -I tools/sat_search_iter5.py                  # all families + forward citations
       python -I tools/sat_search_iter5.py --only-citations
       python -I tools/sat_search_iter5.py --round2 FILE.json  # extra queries [{"family":..,"q":..,"e3_terms":[..]}]
       python -I tools/sat_search_iter5.py --backward ID [ID ...]
       python -I tools/sat_search_iter5.py --aggregate
Needs SEMANTIC_SCHOLAR_API_KEY in the environment for E4/FC (anonymous calls are rate-limited and logged as such).
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
from common import CACHE, EVID, F, SKILL_PY, SKILL_SCRIPTS, WS, append_jsonl, now_utc  # noqa: E402

SEARCH_PY = str(SKILL_SCRIPTS / "aii_fast_web_search.py")
PY = SKILL_PY
RAW = CACHE / "search_results"
LOG = EVID / "search_log_iter5.jsonl"
PROTO = json.loads((EVID / "protocol.json").read_text())
LOCK = threading.Lock()
CATS = "(cat:cs.CL OR cat:cs.LG OR cat:cs.AI)"

QUERIES = [(fam["family"], q["q"], q["e3_terms"]) for fam in PROTO["query_families"] for q in fam["queries"]]
FC_BOTH = PROTO["citation_chasing"]["forward_round1_s2_and_openalex"]
FC_S2 = PROTO["citation_chasing"]["forward_round1_s2_as_time_allows"]


def log(family, query, engine, n, status, date_filter="", extra=None):
    rec = {"family": family, "query": query, "engine": engine, "date_filter": date_filter, "n_results": n,
           "status": status, "timestamp_utc": now_utc()}
    if extra:
        rec.update(extra)
    with LOCK:
        append_jsonl(LOG, rec)


def save_raw(name, items):
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / f"{name}.json").write_text(json.dumps(items, ensure_ascii=False, indent=1))


def arxiv_id_from(s):
    m = re.search(r"(?:arxiv[.:/ ]*(?:abs/|pdf/|html/)?|10\.48550/arxiv\.)(\d{4}\.\d{4,5})", s or "", re.I)
    return m.group(1) if m else ""


# ---------------- engines ----------------
def e1_scholarly(tag, fam, q):
    try:
        out = subprocess.run([PY, SEARCH_PY, "--query", q, "--mode", "scholarly", "--max-results", "25"],
                             capture_output=True, text=True, timeout=240).stdout
    except subprocess.TimeoutExpired:
        out = ""
    items = []
    for m in re.finditer(r"^\s*\d+\.\s+(.+)\n\s+(\S+)\n\s+(.*)$", out, re.M):
        title, url, meta = m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
        year = re.search(r"\b(20\d\d)\b", meta)
        items.append({"title": title, "url": url, "year": year.group(1) if year else "", "arxiv_id": arxiv_id_from(url)})
    save_raw(f"{fam}_{tag}_E1", items)
    log(fam, q, "E1 scholarly (OpenAlex/Crossref via aii_fast_web_search.py)", len(items), "ok" if items else "empty")
    return [("E1", fam, it) for it in items]


def e3_web(tag, fam, q, terms):
    """E3 fallback: arxiv.org/search (all fields, newest first), used only after the export API returned HTTP 429."""
    query = " ".join(t.strip('"') for t in terms)
    url = ("https://arxiv.org/search/?query=" + urllib.parse.quote_plus(query) +
           "&searchtype=all&order=-announced_date_first&size=50&abstracts=show")
    r = F._fetch_url(url)
    items = []
    content = r.get("content", "")
    for b in re.split(r"\n\s*\d+\.\s+\[arXiv:", content)[1:]:
        m = re.match(r"(\d{4}\.\d{4,5})", b)
        if not m:
            continue
        lines = [x.strip() for x in b.split("\n") if x.strip()]
        ab = re.search(r"Abstract:(.*?)(?:△ Less|Submitted)", b, re.S)
        v1 = re.search(r"v1 submitted (\d{1,2} \w+, \d{4})", b) or re.search(r"Submitted (\d{1,2} \w+, \d{4})", b)
        items.append({"title": lines[2] if len(lines) > 2 else "", "arxiv_id": m.group(1),
                      "v1_date_text": v1.group(1) if v1 else "", "abstract": " ".join((ab.group(1) if ab else "").split())[:1500]})
    return items, ("ok" if r.get("success") else f"error:{r.get('error')}")


def e3_arxiv(tag, fam, q, terms):
    sq = "(" + " AND ".join(f"all:{t}" for t in terms) + ") AND " + CATS
    url = ("https://export.arxiv.org/api/query?search_query=" + urllib.parse.quote(sq) +
           "&sortBy=submittedDate&sortOrder=descending&max_results=50")
    ns = {"a": "http://www.w3.org/2005/Atom"}
    items, status = [], "ok"
    for attempt in range(4):
        try:
            r = F._session.get(url, timeout=90)
            if r.status_code == 429:
                status = "HTTP429"
                time.sleep(10 * (attempt + 1))
                continue
            root = ET.fromstring(r.text)
            for e in root.findall("a:entry", ns):
                aid = e.findtext("a:id", default="", namespaces=ns).rsplit("/abs/", 1)[-1]
                items.append({"title": " ".join(e.findtext("a:title", default="", namespaces=ns).split()),
                              "arxiv_id": re.sub(r"v\d+$", "", aid),
                              "v1_date": e.findtext("a:published", default="", namespaces=ns)[:10],
                              "abstract": " ".join(e.findtext("a:summary", default="", namespaces=ns).split())[:1500]})
            status = "ok"
            break
        except Exception as ex:  # malformed/empty feed -> retry
            status = f"retry:{type(ex).__name__}"
            time.sleep(5)
    engine = "E3 arXiv API (cs.CL/cs.LG/cs.AI, sortBy=submittedDate desc, max 50)"
    if status == "HTTP429":
        items, status = e3_web(tag, fam, q, terms)
        engine = "E3 arXiv web search fallback (arxiv.org/search, newest first) after export API HTTP 429"
    save_raw(f"{fam}_{tag}_E3", items)
    log(fam, q, engine, len(items), status, date_filter="none in query; window applied at screening",
        extra={"arxiv_query": sq})
    time.sleep(3.1)
    return [("E3", fam, it) for it in items]


def s2_get(url):
    key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "")
    headers = {"x-api-key": key} if key else {}
    code = None
    for wait in (0, 3, 6, 12):
        time.sleep(wait)
        try:
            r = F._session.get(url, headers=headers, timeout=60)
            code = r.status_code
            if code == 200:
                return r.json(), "ok" + ("" if key else " (anonymous)")
        except Exception as ex:
            code = type(ex).__name__
    return None, ("rate-limited" if code == 429 else f"HTTP {code}")


def e4_s2(tag, fam, q):
    url = ("https://api.semanticscholar.org/graph/v1/paper/search?query=" + urllib.parse.quote(q) +
           "&year=2026&fields=title,externalIds,publicationDate,venue,abstract&limit=50")
    js, status = s2_get(url)
    items = []
    for p in (js or {}).get("data", []) or []:
        items.append({"title": p.get("title", ""), "arxiv_id": (p.get("externalIds") or {}).get("ArXiv", ""),
                      "pub_date": p.get("publicationDate") or "", "venue": p.get("venue") or "",
                      "abstract": (p.get("abstract") or "")[:1500]})
    save_raw(f"{fam}_{tag}_E4", items)
    log(fam, q, "E4 Semantic Scholar API (/paper/search)", len(items), status, date_filter="year=2026")
    time.sleep(1.1)
    return [("E4", fam, it) for it in items]


def e5_openreview(tag, fam, q):
    url = ("https://api2.openreview.net/notes/search?term=" + urllib.parse.quote(q) +
           "&group=ICLR.cc/2027/Conference&limit=50")
    items, status = [], "ok"
    try:
        r = F._session.get(url, timeout=60)
        js = r.json()
        for n in js.get("notes", []):
            c = n.get("content", {})
            items.append({"title": (c.get("title") or {}).get("value", ""), "openreview_id": n.get("forum") or n.get("id"),
                          "venue": (c.get("venue") or {}).get("value", ""),
                          "abstract": ((c.get("abstract") or {}).get("value", "") or "")[:1500]})
        if r.status_code != 200:
            status = f"HTTP {r.status_code}"
    except Exception as ex:
        status = f"error:{type(ex).__name__}"
    save_raw(f"{fam}_{tag}_E5", items)
    log(fam, q, "E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/2027/Conference)", len(items), status,
        date_filter="ICLR 2027 submissions")
    time.sleep(1.0)
    return [("E5", fam, it) for it in items]


def s2_citations(name, aid, kind="citations"):
    items, offset, status = [], 0, "ok"
    field = "citingPaper" if kind == "citations" else "citedPaper"
    while offset < 1000:
        url = (f"https://api.semanticscholar.org/graph/v1/paper/arXiv:{aid}/{kind}?fields=title,externalIds,"
               f"publicationDate,venue,abstract&limit=100&offset={offset}")
        js, status = s2_get(url)
        data = (js or {}).get("data", []) or []
        for d in data:
            p = d.get(field) or {}
            items.append({"title": p.get("title", "") or "", "arxiv_id": (p.get("externalIds") or {}).get("ArXiv", "") or "",
                          "pub_date": p.get("publicationDate") or "", "venue": p.get("venue") or "",
                          "abstract": (p.get("abstract") or "")[:1500], "cites": name})
        if len(data) < 100:
            break
        offset += 100
        time.sleep(1.1)
    tagname = "FC" if kind == "citations" else "BC"
    save_raw(f"{tagname}_{name}_S2", items)
    log(tagname, f"{'forward' if kind == 'citations' else 'backward'} citations of arXiv:{aid} ({name})",
        f"S2 /paper/arXiv:{{id}}/{kind}", len(items), status,
        date_filter="all; window applied at screening")
    return [(tagname, tagname, it) for it in items]


def openalex_citations(name, aid):
    items, status = [], "ok"
    try:
        r = F._session.get(f"https://api.openalex.org/works/doi:10.48550/arXiv.{aid}", timeout=60)
        if r.status_code != 200:
            raise RuntimeError(f"resolve HTTP {r.status_code}")
        oid = r.json()["id"].rsplit("/", 1)[-1]
        cursor = "*"
        while cursor:
            u = (f"https://api.openalex.org/works?filter=cites:{oid}&per-page=200&cursor={cursor}"
                 "&select=id,display_name,doi,publication_date,primary_location,ids,locations")
            r2 = F._session.get(u, timeout=60)
            js = r2.json()
            for w in js.get("results", []):
                doi = (w.get("doi") or "")
                locs = " ".join(((l or {}).get("landing_page_url") or "") for l in (w.get("locations") or []))
                items.append({"title": w.get("display_name") or "", "arxiv_id": arxiv_id_from(doi + " " + locs),
                              "pub_date": w.get("publication_date") or "",
                              "venue": (((w.get("primary_location") or {}).get("source") or {}).get("display_name") or ""),
                              "cites": name, "openalex": w.get("id")})
            cursor = (js.get("meta") or {}).get("next_cursor")
            if not js.get("results"):
                break
        status = f"ok (openalex {oid})"
    except Exception as ex:
        status = f"error:{ex}"
    save_raw(f"FC_{name}_OA", items)
    log("FC", f"forward citations of arXiv:{aid} ({name})", "OpenAlex works?filter=cites:", len(items), status,
        date_filter="all; window applied at screening")
    return [("FC", "FC", it) for it in items]


def norm_title(t):
    return re.sub(r"[^a-z0-9]+", " ", (t or "").lower()).strip()


def write_candidates():
    """Rebuild the de-duplicated candidate list from every saved raw result file (all engines + citations)."""
    hits = []
    for f in sorted(RAW.glob("*.json")):
        parts = f.stem.split("_")
        eng, fam = (parts[0], parts[0]) if parts[0] in ("FC", "BC") else (parts[-1], parts[0])
        for it in json.loads(f.read_text()):
            hits.append((eng, fam, it))
    prev_ids, prev_titles = set(), set()
    for line in (WS / "inherited" / "saturation_candidates.jsonl").read_text().splitlines():
        c = json.loads(line)
        if c.get("arxiv_id"):
            prev_ids.add(c["arxiv_id"])
        if c.get("openreview_id"):
            prev_ids.add("or:" + c["openreview_id"])
        prev_titles.add(norm_title(c.get("title")))
    cand, title_key = {}, {}
    for eng, fam, it in hits:
        nt = norm_title(it.get("title"))
        if not nt and not it.get("arxiv_id"):
            continue
        key = it.get("arxiv_id") or ("or:" + it["openreview_id"] if it.get("openreview_id") else "t:" + nt)
        key = title_key.get(nt, key) if nt else key   # same normalised title -> same record
        if nt and nt not in title_key:
            title_key[nt] = key
        c = cand.setdefault(key, {"key": key, "title": it.get("title", ""), "arxiv_id": it.get("arxiv_id", ""),
                                  "openreview_id": it.get("openreview_id", ""), "dates": set(), "venue": set(),
                                  "families": set(), "engines": set(), "cites": set(), "abstract": ""})
        if it.get("arxiv_id") and not c["arxiv_id"]:
            c["arxiv_id"] = it["arxiv_id"]
        for fld in ("v1_date", "pub_date", "year", "v1_date_text"):
            if it.get(fld):
                c["dates"].add(str(it[fld]))
        if it.get("venue"):
            c["venue"].add(it["venue"])
        if it.get("cites"):
            c["cites"].add(it["cites"])
        c["families"].add(fam)
        c["engines"].add(eng)
        if len(it.get("abstract", "") or "") > len(c["abstract"]):
            c["abstract"] = it["abstract"]
    path = EVID / "saturation_candidates_iter5.jsonl"
    path.write_text("")
    n_prev = 0
    for c in cand.values():
        for k in ("dates", "venue", "families", "engines", "cites"):
            c[k] = sorted(c[k])
        c["seen_in_iter4"] = bool((c["arxiv_id"] and c["arxiv_id"] in prev_ids) or
                                  (c["openreview_id"] and "or:" + c["openreview_id"] in prev_ids) or
                                  norm_title(c["title"]) in prev_titles)
        n_prev += c["seen_in_iter4"]
        append_jsonl(path, c)
    print(f"identified (raw hits): {len(hits)}; unique after de-duplication: {len(cand)}; "
          f"already seen in iteration-4 audit: {n_prev}")


def run_queries(queries, prefix="q"):
    tagged = [(f"{prefix}{i}", f, q, t) for i, (f, q, t) in enumerate(queries)]

    def run_e1():
        with ThreadPoolExecutor(4) as ex:
            return sum(ex.map(lambda a: e1_scholarly(a[0], a[1], a[2]), tagged), [])

    def run_e3():
        return sum((e3_arxiv(tg, f, q, t) for tg, f, q, t in tagged), [])

    def run_e4():
        return sum((e4_s2(tg, f, q) for tg, f, q, _ in tagged), [])

    def run_e5():
        return sum((e5_openreview(tg, f, q) for tg, f, q, _ in tagged), [])

    with ThreadPoolExecutor(4) as ex:
        futs = [ex.submit(fn) for fn in (run_e1, run_e3, run_e4, run_e5)]
        for fu in futs:
            fu.result()


def forward_citations():
    for name, aid in FC_BOTH.items():
        s2_citations(name, aid)
        openalex_citations(name, aid)
        time.sleep(1.0)
    for name, aid in FC_S2.items():
        s2_citations(name, aid)
        time.sleep(1.0)


def main():
    F.init_web_fetch()
    if "--aggregate" in sys.argv:
        write_candidates()
        return
    if "--backward" in sys.argv:
        for aid in sys.argv[sys.argv.index("--backward") + 1:]:
            s2_citations(aid.replace(".", "_"), aid, kind="references")
        write_candidates()
        return
    if "--round2" in sys.argv:
        extra = json.loads(Path(sys.argv[sys.argv.index("--round2") + 1]).read_text())
        run_queries([(e["family"], e["q"], e["e3_terms"]) for e in extra], prefix="r2q")
        write_candidates()
        return
    if "--only-citations" not in sys.argv:
        run_queries(QUERIES)
    forward_citations()
    write_candidates()


if __name__ == "__main__":
    main()
