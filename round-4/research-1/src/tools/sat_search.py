"""Dated saturation search (plan step 3): 8 query families x engines E1 (OpenAlex/Crossref scholarly search via the
aii-web-tools script), E3 (arXiv API, newest first), E4 (Semantic Scholar API, year=2026), E5 (OpenReview ICLR 2027 pool),
plus forward citations (Semantic Scholar) of the nearest neighbours.

Every call is logged to evidence/search_log.jsonl; raw results go to cache/search_results/; de-duplicated candidates go to
evidence/saturation_candidates.jsonl (one line per unique paper with the families/engines that surfaced it).

Usage: python -I tools/sat_search.py [--only-citations]
Needs SEMANTIC_SCHOLAR_API_KEY in the environment for E4 (falls back to anonymous calls, logged, if absent).
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
from common import CACHE, EVID, F, append_jsonl, now_utc  # noqa: E402

SEARCH_PY = str(Path(__file__).resolve().parents[4] / "tools/aii-web-tools/scripts/aii_fast_web_search.py")
PY = "/ai-inventor/.claude/skills/.ability_client_venv/bin/python"
RAW = CACHE / "search_results"
LOG = EVID / "search_log.jsonl"
WINDOW_START = "2026-01-01"
LOCK = threading.Lock()

# family, query (as written in the plan), arXiv API term list, run E5 (ICLR 2027 pool)?
QUERIES = [
    ("S1", "activation steering diversity code generation", ['"activation steering"', "diversity"], True),
    ("S1", "hidden state noise injection solution diversity", ["noise", "injection", "hidden", "diversity"], True),
    ("S1", "residual stream noise diversity reasoning strategies", ['"residual stream"', "noise", "diversity"], True),
    ("S1", "latent perturbation exploration pass@k", ["perturbation", "latent", "exploration", "pass@k"], True),
    ("S2", "where to inject diversity language model layer", ["inject", "diversity", "layer", "language model"], False),
    ("S2", "noise injection layer comparison generation diversity", ['"noise injection"', "layer", "diversity"], False),
    ("S2", "prefill perturbation versus temperature diversity", ["perturbation", "temperature", "diversity", "activation"], False),
    ("S3", "predict instruction compliance from hidden states", ["predict", "instruction", "compliance", "hidden"], True),
    ("S3", "steerability prediction hidden states", ["steerability", "predict"], True),
    ("S3", "negative constraint compliance internal representation", ["negative", "constraint", "compliance"], True),
    ("S3", "perturbation sensitivity predicts prompt compliance", ["perturbation", "sensitivity", "compliance"], True),
    ("S4", "algorithm choice hidden states code LLM probe", ["algorithm", "probe", "code", "hidden"], True),
    ("S4", "latent planning code generation prompt representations", ["planning", "latent", "code generation"], True),
    ("S4", "response planning prompt hidden states", ['"response planning"'], True),
    ("S5", "temperature semantic diversity ideas not wording", ["temperature", "semantic", "diversity"], False),
    ("S5", "token-level diversity paraphrases same solution", ["token-level", "diversity", "semantic"], False),
    ("S5", "idea-level diversity sampling LLM", ["idea", "diversity", "sampling", "language model"], False),
    ("S6", "algorithmic diversity code LLM benchmark", ["algorithmic", "diversity", "code"], False),
    ("S6", "algorithm selection bias code generation", ["algorithm", "selection", "code generation", "bias"], False),
    ("S6", "mode collapse code solutions", ['"mode collapse"', "code"], False),
    ("S7", "negative instruction mechanism LLM alternative", ["negation", "mechanism", "language model"], False),
    ("S7", "do not use X prompt code model", ["negative", "constraint", "code generation"], False),
    ("S7", "negation suppression promotion LLM", ["negation", "suppression"], False),
    ("S8", "LLM novel algorithm discovery evaluation", ["novel", "algorithm", "discovery", "language model"], False),
    ("S8", "novel algorithm correctness novelty judge LLM", ["novelty", "algorithm", "code", "judge"], False),
]

CITATION_SEEDS = {"STARS": "2601.22010", "NoiseSteering": "2604.03380", "ASTEER": "2606.11599",
                  "DiversityInjection": "2606.10302", "RandomEmbeddingInjection": "2605.11936",
                  "EmergentResponsePlanning": "2502.06258"}


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
    m = re.search(r"(?:arxiv[.:/ ]*(?:abs/)?|10\.48550/arxiv\.)(\d{4}\.\d{4,5})", s or "", re.I)
    return m.group(1) if m else ""


# ---------------- engines ----------------
def e1_scholarly(i, fam, q):
    out = subprocess.run([PY, SEARCH_PY, "--query", q, "--mode", "scholarly", "--max-results", "25"],
                         capture_output=True, text=True, timeout=180).stdout
    items = []
    for m in re.finditer(r"^\s*\d+\.\s+(.+)\n\s+(\S+)\n\s+(.*)$", out, re.M):
        title, url, meta = m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
        year = re.search(r"\b(20\d\d)\b", meta)
        items.append({"title": title, "url": url, "year": year.group(1) if year else "", "arxiv_id": arxiv_id_from(url)})
    save_raw(f"{fam}_q{i}_E1", items)
    log(fam, q, "E1 scholarly (OpenAlex/Crossref via aii_fast_web_search.py)", len(items), "ok" if items else "empty")
    return [("E1", fam, it) for it in items]


def e3_arxiv(i, fam, q, terms):
    sq = " AND ".join(f"all:{t}" for t in terms)
    url = ("http://export.arxiv.org/api/query?search_query=" + urllib.parse.quote(sq) +
           "&sortBy=submittedDate&sortOrder=descending&max_results=25")
    ns = {"a": "http://www.w3.org/2005/Atom"}
    items, status = [], "ok"
    for attempt in range(5):
        try:
            r = F._session.get(url, timeout=90)
            if r.status_code == 429:          # arXiv rate limit: back off and retry
                status = "retry:HTTP429"
                time.sleep(20 * (attempt + 1))
                continue
            root = ET.fromstring(r.text)
            for e in root.findall("a:entry", ns):
                aid = e.findtext("a:id", default="", namespaces=ns).rsplit("/abs/", 1)[-1]
                items.append({"title": " ".join(e.findtext("a:title", default="", namespaces=ns).split()),
                              "arxiv_id": re.sub(r"v\d+$", "", aid), "v1_date": e.findtext("a:published", default="", namespaces=ns)[:10],
                              "abstract": " ".join(e.findtext("a:summary", default="", namespaces=ns).split())[:1500]})
            break
        except Exception as ex:  # malformed/empty feed -> retry
            status = f"retry:{type(ex).__name__}"
            time.sleep(5)
    save_raw(f"{fam}_q{i}_E3", items)
    log(fam, q, "E3 arXiv API (sortBy=submittedDate desc)", len(items), status if not items else "ok",
        date_filter="none in query; window 2026-01-01..2026-10-21 applied at screening", extra={"arxiv_query": sq})
    time.sleep(3.1)
    return [("E3", fam, it) for it in items]


def e3_web(i, fam, q, terms):
    """E3 fallback: arxiv.org/search (all fields, newest first). Used after the export API returned HTTP 429."""
    query = " ".join(terms)
    url = ("https://arxiv.org/search/?query=" + urllib.parse.quote_plus(query) +
           "&searchtype=all&order=-announced_date_first&size=50&abstracts=show")
    r = F._fetch_url(url)
    items, status = [], "ok" if r.get("success") else f"error:{r.get('error')}"
    content = r.get("content", "")
    blocks = re.split(r"\n\s*\d+\.\s+\[arXiv:", content)[1:]
    for b in blocks:
        m = re.match(r"(\d{4}\.\d{4,5})", b)
        if not m:
            continue
        lines = [x.strip() for x in b.split("\n") if x.strip()]
        title = lines[2] if len(lines) > 2 else ""
        ab = re.search(r"Abstract:(.*?)(?:△ Less|Submitted)", b, re.S)
        v1 = re.search(r"v1 submitted (\d{1,2} \w+, \d{4})", b) or re.search(r"Submitted (\d{1,2} \w+, \d{4})", b)
        items.append({"title": title, "arxiv_id": m.group(1), "v1_date_text": v1.group(1) if v1 else "",
                      "abstract": " ".join((ab.group(1) if ab else "").split())[:1500]})
    save_raw(f"{fam}_q{i}_E3", items)
    log(fam, q, "E3 arXiv web search (arxiv.org/search, all fields, newest first; switched from export API after HTTP 429)",
        len(items), status, date_filter="none in query; window applied at screening", extra={"arxiv_query": query})
    time.sleep(2.0)
    return [("E3", fam, it) for it in items]


def s2_get(url):
    key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "")
    headers = {"x-api-key": key} if key else {}
    for attempt in range(6):
        r = F._session.get(url, headers=headers, timeout=60)
        if r.status_code == 200:
            return r.json(), "ok" + ("" if key else " (anonymous)")
        time.sleep(2 + 3 * attempt)
    return None, f"HTTP {r.status_code}"


def e4_s2(i, fam, q):
    url = ("https://api.semanticscholar.org/graph/v1/paper/search?query=" + urllib.parse.quote(q) +
           "&year=2026&fields=title,externalIds,publicationDate,venue,abstract&limit=25")
    js, status = s2_get(url)
    items = []
    for p in (js or {}).get("data", []) or []:
        items.append({"title": p.get("title", ""), "arxiv_id": (p.get("externalIds") or {}).get("ArXiv", ""),
                      "pub_date": p.get("publicationDate") or "", "venue": p.get("venue") or "",
                      "abstract": (p.get("abstract") or "")[:1500]})
    save_raw(f"{fam}_q{i}_E4", items)
    log(fam, q, "E4 Semantic Scholar API", len(items), status, date_filter="year=2026")
    time.sleep(1.2)
    return [("E4", fam, it) for it in items]


def e5_openreview(i, fam, q):
    url = ("https://api2.openreview.net/notes/search?term=" + urllib.parse.quote(q) +
           "&group=ICLR.cc/2027/Conference&limit=25")
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
    save_raw(f"{fam}_q{i}_E5", items)
    log(fam, q, "E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/2027/Conference)", len(items), status,
        date_filter="ICLR 2027 submissions (deadline 2026-09-25)")
    time.sleep(1.0)
    return [("E5", fam, it) for it in items]


def forward_citations():
    out = []
    for name, aid in CITATION_SEEDS.items():
        items, offset, status = [], 0, "ok"
        while offset < 400:
            url = (f"https://api.semanticscholar.org/graph/v1/paper/arXiv:{aid}/citations?fields=title,externalIds,"
                   f"publicationDate,venue,abstract&limit=100&offset={offset}")
            js, status = s2_get(url)
            data = (js or {}).get("data", []) or []
            for d in data:
                p = d.get("citingPaper") or {}
                items.append({"title": p.get("title", ""), "arxiv_id": (p.get("externalIds") or {}).get("ArXiv", ""),
                              "pub_date": p.get("publicationDate") or "", "venue": p.get("venue") or "",
                              "abstract": (p.get("abstract") or "")[:1500], "cites": name})
            if len(data) < 100:
                break
            offset += 100
            time.sleep(1.2)
        save_raw(f"FC_{name}", items)
        log("FC", f"forward citations of arXiv:{aid} ({name})", "E4 Semantic Scholar citations API", len(items), status,
            date_filter="all citers; 2026 screened")
        out += [("FC", "FC", it) for it in items]
        time.sleep(1.2)
    return out


def aggregate_from_raw():
    """Rebuild the de-duplicated candidate list from every saved raw result file (all engines + citations)."""
    hits = []
    for f in sorted(RAW.glob("*.json")):
        name = f.stem
        if name.startswith("FC_"):
            eng, fam = "FC", "FC"
        else:
            fam, _, eng = name.split("_")
        for it in json.loads(f.read_text()):
            hits.append((eng, fam, it))
    write_candidates(hits)


def norm_title(t):
    return re.sub(r"[^a-z0-9]+", " ", (t or "").lower()).strip()


def main():
    F.init_web_fetch()
    hits = []
    if "--e3-web" in sys.argv:
        for i, (f, q, t, _) in enumerate(QUERIES):
            e3_web(i, f, q, [x for x in t])
        return
    if "--e3-only" in sys.argv:
        for i, (f, q, t, _) in enumerate(QUERIES):
            e3_arxiv(i, f, q, t)
        return
    if "--aggregate" in sys.argv:
        aggregate_from_raw()
        return
    if "--only-citations" not in sys.argv:
        def run_e1():
            with ThreadPoolExecutor(4) as ex:
                return sum(ex.map(lambda a: e1_scholarly(*a), [(i, f, q) for i, (f, q, _, _) in enumerate(QUERIES)]), [])

        def run_e3():
            return sum((e3_arxiv(i, f, q, t) for i, (f, q, t, _) in enumerate(QUERIES)), [])

        def run_e4():
            return sum((e4_s2(i, f, q) for i, (f, q, _, _) in enumerate(QUERIES)), [])

        def run_e5():
            return sum((e5_openreview(i, f, q) for i, (f, q, _, e5) in enumerate(QUERIES) if e5), [])

        with ThreadPoolExecutor(4) as ex:
            futs = [ex.submit(fn) for fn in (run_e1, run_e3, run_e4, run_e5)]
            for fu in futs:
                hits += fu.result()
    hits += forward_citations()
    write_candidates(hits)


def write_candidates(hits):
    # de-duplicate: arXiv id if known, else normalised title
    cand = {}
    for eng, fam, it in hits:
        key = it.get("arxiv_id") or ("or:" + it["openreview_id"] if it.get("openreview_id") else "t:" + norm_title(it["title"]))
        c = cand.setdefault(key, {"key": key, "title": it.get("title", ""), "arxiv_id": it.get("arxiv_id", ""),
                                  "openreview_id": it.get("openreview_id", ""), "dates": set(), "venue": set(),
                                  "families": set(), "engines": set(), "cites": set(), "abstract": ""})
        for f in ("v1_date", "pub_date", "year"):
            if it.get(f):
                c["dates"].add(it[f])
        if it.get("venue"):
            c["venue"].add(it["venue"])
        if it.get("cites"):
            c["cites"].add(it["cites"])
        c["families"].add(fam)
        c["engines"].add(eng)
        if len(it.get("abstract", "")) > len(c["abstract"]):
            c["abstract"] = it["abstract"]
    path = EVID / "saturation_candidates.jsonl"
    path.write_text("")
    for c in cand.values():
        for k in ("dates", "venue", "families", "engines", "cites"):
            c[k] = sorted(c[k])
        append_jsonl(path, c)
    print(f"identified (raw hits): {len(hits)}; unique after de-duplication: {len(cand)}")


if __name__ == "__main__":
    main()
