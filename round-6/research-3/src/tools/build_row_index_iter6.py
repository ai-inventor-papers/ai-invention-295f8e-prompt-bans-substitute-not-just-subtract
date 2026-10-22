"""Plan step 0.2: index every inherited table row (Tables 92b/92c of art_kjrCpQnPaniY, Table 92d of art_ObxQOIlAM9MS)
by arXiv id (version stripped), OpenReview id, DOI and normalised title, so that inherited references are cited as
'see Table 92x row R (not re-verified)'. Also indexes the two source lists, so a reference that appears only in a
sources list (no table row) is visible as such.

Writes inherited/row_index.json. Usage: python -I tools/build_row_index_iter6.py [ID ...]  (prints lookups for IDs)
"""
import json
import re
import sys
from pathlib import Path

WS = Path(__file__).resolve().parents[1]
INH = WS / "inherited"
ARX = re.compile(r"(?<![\d.])(\d{4}\.\d{4,5})(?:v\d+)?")
ORID = re.compile(r"openreview\.net/(?:forum|pdf)\?id=([A-Za-z0-9_-]{6,})")
DOI = re.compile(r"\b(10\.\d{4,9}/[^\s|;,)\]]+)")


def norm_title(t):
    return re.sub(r"[^a-z0-9]+", " ", (t or "").lower()).strip()


def table_rows(answer, table):
    rows = []
    for line in answer.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 6 or cells[0] in ("Row", "---") or set(cells[0]) <= set("-: "):
            continue
        rid = cells[0]
        if not re.match(r"^(92[bcd]-)?[A-Za-z][A-Za-z0-9-]*$", rid):
            continue
        rows.append({"table": table, "row": rid if rid.startswith("92") else f"{table}-{rid}",
                     "claim": cells[1][:160], "neighbour": cells[2][:200], "url_cell": cells[4][:300] if len(cells) > 4 else "",
                     "relation": cells[6][:120] if len(cells) > 6 else ""})
    return rows


def main():
    r4 = json.loads((INH / "iter4" / "research_out.json").read_text())
    r5 = json.loads((INH / "iter5" / "research_out.json").read_text())
    rows = []
    for t, row in [("92b/92c", r) for r in table_rows(r4["answer"], "92bc")] + [("92d", r) for r in table_rows(r5["answer"], "92d")]:
        rows.append(row)
    index = {}

    def add(key, rec):
        index.setdefault(key, [])
        if rec not in index[key]:
            index[key].append(rec)

    for r in rows:
        blob = r["neighbour"] + " " + r["url_cell"]
        rec = {"row": r["row"], "relation": r["relation"], "url_cell": r["url_cell"][:160]}
        for a in set(ARX.findall(blob)):
            add("arxiv:" + a, rec)
        for o in set(ORID.findall(blob)):
            add("openreview:" + o, rec)
        for d in set(DOI.findall(blob)):
            add("doi:" + d.lower(), rec)
    # quote files carry status per quote
    for f, tag in ((INH / "iter4" / "quotes.jsonl", "92b/92c"), (INH / "iter5" / "quotes_iter5.jsonl", "92d")):
        for line in f.read_text().splitlines():
            q = json.loads(line)
            aid = q.get("arxiv_id") or q.get("id") or ""
            key = ("arxiv:" + re.sub(r"v\d+$", "", aid)) if ARX.fullmatch(aid or "x") or re.match(r"\d{4}\.\d{4,5}", aid or "") else ""
            rec = {"quote_file": tag, "ref_key": q.get("ref_key"), "status": q.get("status"),
                   "rows": q.get("rows") or q.get("used_in"), "url": q.get("url"),
                   "title": q.get("title_at_latest_version") or q.get("title_as_printed")}
            if key:
                add(key, rec)
            for o in ORID.findall(q.get("url") or ""):
                add("openreview:" + o, rec)
            if rec["title"]:
                add("title:" + norm_title(rec["title"]), rec)
    # sources-only entries
    for r, tag in ((r4, "art_kjrCpQnPaniY sources"), (r5, "art_ObxQOIlAM9MS sources")):
        for s in r["sources"]:
            rec = {"sources_list": tag, "index": s.get("index"), "title": s.get("title"), "url": s.get("url")}
            for a in set(ARX.findall(s.get("url") or "")):
                add("arxiv:" + a, rec)
            for o in ORID.findall(s.get("url") or ""):
                add("openreview:" + o, rec)
            add("title:" + norm_title(s.get("title")), rec)
    out = {"_note": "key -> inherited table rows / quote records / sources-list entries (built by tools/build_row_index_iter6.py)",
           "n_table_rows": len(rows), "index": index}
    (INH / "row_index.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(f"table rows parsed: {len(rows)}; index keys: {len(index)}")
    for q in sys.argv[1:]:
        k = q if ":" in q else "arxiv:" + q
        hits = index.get(k, [])
        rws = sorted({h["row"] for h in hits if "row" in h})
        st = sorted({h["status"] for h in hits if h.get("status")})
        src = sorted({h["sources_list"] for h in hits if "sources_list" in h})
        print(f"{q}: rows={rws} quote_status={st} sources={src}")


if __name__ == "__main__":
    main()
