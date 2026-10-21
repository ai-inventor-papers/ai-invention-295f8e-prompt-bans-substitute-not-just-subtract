"""Write reproducibility.md from the dated logs (search_log_iter5.jsonl, cache/index.jsonl) plus a fixed narrative.
Usage: python -I tools/write_repro_iter5.py"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CACHE, EVID, WS  # noqa: E402

LOG = [json.loads(l) for l in (EVID / "search_log_iter5.jsonl").read_text().splitlines()]
IDX = [json.loads(l) for l in (CACHE / "index.jsonl").read_text().splitlines()]
SHA = (EVID / "protocol.sha256").read_text().splitlines()

HEAD = f"""# Reproducibility — iteration-5 positioning audit (Table 92d)

This file records how the research was **actually** done on 2026-10-21 (UTC 14:45–16:30), not an idealised version.

## Tools and environment

- **Skill used:** `aii-web-tools`. Its scripts were run with the skill interpreter `.claude/skills/.ability_client_venv/bin/python` under the repository root (located by `tools/common.py`; override with `AII_SKILLS_DIR`):
  - `aii_fast_web_search.py --mode scholarly` (engine E1: OpenAlex/Crossref);
  - `aii_fast_web_fetch.py grep` (independent live second pass over every quote);
  - the skill's fetch core `aii_fast_web_fetch._fetch_url` (html2text / PyMuPDF), imported by `tools/common.py` to cache full texts.
- **Built-in Claude Code tools:** `WebSearch` (engine E6 grey literature, plus 3 lookups and 1 venue check) and `ToolSearch` (to load WebSearch/WebFetch). `WebFetch` was loaded but not used.
- **Public APIs, called directly from `tools/*.py` through the skill's HTTP session:**
  - arXiv API `https://export.arxiv.org/api/query` (id_list metadata and E3 search);
  - Semantic Scholar Graph API (E4 search; forward citations and backward references);
  - OpenReview API v2 `https://api2.openreview.net/notes/search` (E5; ICLR 2027 pool and abstract records);
  - OpenAlex `works/doi:` and `works?filter=cites:` (forward citations; returned 0, see corrections).
- **Environment variables (names only):**
  - `SEMANTIC_SCHOLAR_API_KEY`, sent as the `x-api-key` header for E4 and citations; anonymous calls are rate-limited (HTTP 429);
  - `SERPER_API_KEY`, the skill's paid fallback for search, which the free engines made unnecessary in the logged calls.
  - No LLM API key was used: USD 0 of LLM spend.
- **Protocol frozen before the first call:**
  - `evidence/protocol.json` was written at 14:50:21Z; the first logged search call was at 14:51:23Z.
  - sha256 after amendment A1 (a timestamp-only fix): `{SHA[0].split()[0]}`. The original sha256 is in `evidence/protocol.sha256` and `evidence/protocol_amendments.jsonl`.

## Order of work (what was actually run)

1. **Stage 0.**
   - Copied the dependency's evidence (quotes, 1,729 candidates, 63 scored hits, search log, corrections, arXiv meta), its `research_out.json` and `research_verification.json`, and its generic tools (`common.py`, `arxiv_meta.py`, `fetch_texts.py`, `grep_cache.py`) into `inherited/` and `tools/`.
   - Copied 8 cached full texts from the dependency into `cache/`.
   - Wrote `evidence/protocol.json` (9 families, 25 query strings, engines, window, rubric, flags, stop rule).
2. **Stage 2, round 1 (background):** `python -I tools/sat_search_iter5.py`.
   - Every query on E1, E3, E4 and E5, then forward citations: Semantic Scholar for 8 seeds, plus OpenAlex `cites:` for the 4 nearest neighbours.
   - Failed calls were retried with `tools/retry_failed_iter5.py`: 5 OpenReview HTTP 429, 1 Semantic Scholar search and 2 citation lists.
3. **Stage 1, in parallel with round 1:**
   - `tools/arxiv_meta.py` resolved versions for every seed.
   - `tools/fetch_texts.py` cached arXiv HTML vN (PDF vN for 2406.05587v1) and earlier versions (2506.17871 v1/v3, 2410.09300 v1).
   - `tools/grep_cache.py --spec cache/spec_*.json` located the target sentences; every spec file is kept in `cache/`.
4. **E6 grey literature:** 9 WebSearch calls (families F4, F5 and F7), `allowed_domains` = lesswrong.com, alignmentforum.org, transformer-circuits.pub. The tool did not strictly enforce the domain filter, so arXiv hits also came back. Three extra lookups were made: Hindsight Merging, the 'rephrase circuit' post (not found) and Decan. All are logged in `evidence/search_log_iter5.jsonl`, with a note that the built-in tool gives no timestamps of its own.
5. **Screening:** `tools/screen_iter5.py` applied the date window and keyword pre-screen. A manual title screen followed over ranked shortlists: 311 base-vs-tuned, 248 code-x-diversity and 108 activation-x-diversity in-window records. Abstracts were read for about 70 records, and full texts were fetched and grepped for every candidate scoring at least 1.5. ICLR 2027 records were cached through `tools/fetch_openreview_iter5.py`; their PDFs return 403.
6. **Round 2:** `python -I tools/sat_search_iter5.py --round2 evidence/round2_queries.json` ran 6 queries built from included-hit vocabulary, on E1, E3, E4 and E5. Of 344 new in-window titles, abstracts were read for 10. One new hit scored 1.5.
7. **Round 3:** `python -I tools/round3_citations_iter5.py` chased forward citations (Semantic Scholar) of 6 new closest hits and backward references of the two closest hits per flag. No new hit reached 1.5, so the stop rule was met. Out-of-window anchors surfaced here: Prakash et al. 2024 (CMAP), Du et al. 2025 and Echo Chamber.
8. **Quotes:**
   - `python -I tools/build_quotes_iter5.py` checked {sum(1 for _ in open(EVID / 'quotes_iter5.jsonl'))} quotes against the cached normalised texts; all matched.
   - `python -I tools/qa_second_pass_iter5.py` re-fetched every URL live and grepped a 7-word window; all re-matched after one URL fix (2406.05587v1, whose HTML is 404, now points to its PDF).
9. **Evidence and outputs:**
   - `tools/write_evidence_iter5.py` wrote the scored hits and PRISMA counts;
   - `tools/write_flags_iter5.py` wrote the flags and corrections;
   - `tools/render_report_iter5.py` rendered the report and sources;
   - `tools/check_passages_live_iter5.py` and then `tools/patch_passages_iter5.py` keep only supporting passages that occur literally on the live page;
   - `tools/write_repro_iter5.py` wrote this file.

## How to retrace

```bash
PY=$(bash tools/skill_py.sh)   # the aii-web-tools skill interpreter
$PY -I tools/arxiv_meta.py $(python3 -c "import json;print(' '.join(json.load(open('evidence/arxiv_meta.json'))))")
$PY -I tools/fetch_texts.py                       # latest versions of every id in evidence/arxiv_meta.json
$PY -I tools/build_quotes_iter5.py                # re-verify all quotes against cache/
$PY -I tools/qa_second_pass_iter5.py              # live fetch_grep second pass
$PY -I tools/sat_search_iter5.py                  # round 1 (needs network + SEMANTIC_SCHOLAR_API_KEY)
$PY -I tools/sat_search_iter5.py --round2 evidence/round2_queries.json
$PY -I tools/round3_citations_iter5.py
$PY -I tools/screen_iter5.py 200; $PY -I tools/write_evidence_iter5.py; $PY -I tools/write_flags_iter5.py
$PY -I tools/render_report_iter5.py && $PY -I tools/check_passages_live_iter5.py && $PY -I tools/patch_passages_iter5.py
```

Search indexes drift: a re-run on a later date returns different hits. The dated raw responses used here are kept in `cache/search_results/`, one JSON per engine call; `tools/sat_search_iter5.py --aggregate` rebuilds `evidence/saturation_candidates_iter5.jsonl` from them. To land on the same sources and conclusion, re-read the scored hits (`evidence/saturation_hits_iter5.jsonl`: axis scores plus decisive notes) and the flag file (`evidence/flags.json`: decisive sentences with URLs).

## Search calls in the order they were logged ({len(LOG)} calls)

| # | Family | Engine | Query | Results | Status | Logged (UTC) |
|---|---|---|---|---|---|---|
"""


def main():
    rows = []
    for i, r in enumerate(LOG, 1):
        rows.append(f"| {i} | {r['family']} | {r['engine'][:60]} | {r['query'][:110].replace('|', '/')} | {r['n_results']} | "
                    f"{r['status'][:30]} | {r['timestamp_utc']} |")
    pages = ["\n## Pages and PDFs fetched into cache/ (full texts used for quotes; with retrieval time)\n",
             "| Key | URL | PDF? | Characters | Retrieved (UTC) |", "|---|---|---|---|---|"]
    for r in IDX:
        pages.append(f"| {r['key']} | {r['url'][:120]} | {r.get('is_pdf')} | {r.get('length')} | {r.get('retrieved_utc')} |")
    tail = """

## Notes on drift and limits

- The engines are E1 OpenAlex/Crossref, E3 arXiv API, E4 Semantic Scholar, E5 OpenReview and E6 WebSearch. Each was queried with the frozen strings; E3 used the term lists in `evidence/protocol.json`.
- OpenAlex `cites:` returned 0 citing works for all four nearest neighbours because OpenAlex records `cited_by_count = 0` for them, so forward citations rest on Semantic Scholar alone.
- Conformative decoding (2507.20956) is not indexed in Semantic Scholar, so its forward citations could not be chased.
- ICLR 2027 submissions are abstract-only: openreview.net PDFs return HTTP 403 to scripted access.
- The 112 quotes inherited from art_kjrCpQnPaniY were not re-verified; they are cited by Table 92b/92c row id (`evidence/inherited_ids.json`).
"""
    (WS / "reproducibility.md").write_text(HEAD + "\n".join(rows) + "\n" + "\n".join(pages) + tail)
    print("reproducibility.md written:", len(rows), "calls,", len(IDX), "pages")


if __name__ == "__main__":
    main()
