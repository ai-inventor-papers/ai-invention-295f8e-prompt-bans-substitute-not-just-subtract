"""Write reproducibility.md from the actual logs: every logged search call in order (evidence/search_log_iter6.jsonl), every
page cached for verification (cache/index.jsonl), the verification steps and their outcomes, and the deviations.
Usage: python -I tools/write_repro_iter6.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CACHE, EVID, WS  # noqa: E402

log = [json.loads(l) for l in (EVID / "search_log_iter6.jsonl").read_text().splitlines()]
idx = [json.loads(l) for l in (CACHE / "index.jsonl").read_text().splitlines()]
counts = json.loads((EVID / "saturation_counts_iter6.json").read_text())
kappa = json.loads((EVID / "rescreen_kappa_iter6.json").read_text())
qa = [json.loads(l) for l in (EVID / "qa_second_pass_iter6.jsonl").read_text().splitlines()]
pl = [json.loads(l) for l in (EVID / "passages_live_check_iter6.jsonl").read_text().splitlines()]
sha = (EVID / "protocol_iter6.sha256").read_text().split()[0]

L = []
A = L.append
A("# Reproducibility: how this audit was actually conducted")
A("")
A("This file records what was run, in order, for the iteration-6 positioning audit (Table 92e). It is generated from the logs by `tools/write_repro_iter6.py`, so the query list and the page list are the logged ones, not an idealised plan.")
A("")
A("## 1. Tools, skill and environment")
A("")
A("- **Skill:** aii-web-tools. Search used `aii_fast_web_search.py --mode scholarly` (engine E1, OpenAlex/Crossref). Pages were fetched with the skill's fetch core (`aii_fast_web_fetch._fetch_url`: html2text for HTML, PyMuPDF for PDF), imported by `tools/common.py`. The independent live re-match used `aii_fast_web_fetch.py grep` (fetch_grep). Every script runs with the skill's interpreter (`.claude/skills/.ability_client_venv/bin/python`, located by `tools/skill_py.sh`).")
A("- **Structured APIs** were called through the same requests session, following the engine settings of the iteration-5 audit: arXiv export API (E3; metadata), Semantic Scholar Graph API (E4; forward/backward citations), OpenReview API v2 `notes/search` (E5; ICLR 2027 abstract records), and OpenAlex `works?filter=cites:` (one logged attempt per mandatory neighbour).")
A("- **Built-in tools:** the Claude Code WebSearch tool ran the E6 grey-literature calls (allowed_domains lists in the log) and six venue-confirmation lookups. WebSearch returns model-written summaries, which were used only to find URLs; every quoted passage comes from a fetched page.")
A("- **Environment variables (names only):** `SEMANTIC_SCHOLAR_API_KEY` (E4/FC/BC; sent as `x-api-key`). `SERPER_API_KEY` is the aii-web-tools paid fallback for search. Optionally set `AII_SKILLS_DIR` to point at the skills directory. No OpenRouter or other LLM API was called.")
A(f"- **Protocol:** `evidence/protocol_iter6.json`, frozen before the first search call at 2026-10-21T23:34:28Z, sha256 `{sha}`. No amendments (`evidence/protocol_amendments_iter6.jsonl`).")
A("")
A("## 2. Timeline (UTC)")
A("")
A(f"- 23:32-23:34: loaded the two dependency audits (art_kjrCpQnPaniY, art_ObxQOIlAM9MS), copied their research_out/verification/quotes/candidate files into `inherited/`, built `inherited/row_index.json`, and froze the protocol.")
A(f"- {counts['search_window_utc'][0]} onward: round 1 (21 frozen strings on E1/E3/E4/E5, plus forward citations of 4 mandatory and 4 as-time-allows seeds) ran in the background (`tools/sat_search_iter6.py`). In parallel, seed metadata and full texts were fetched (`tools/arxiv_meta.py`, `tools/fetch_texts.py`) and grepped (`tools/grep_cache.py`, specs in `logs/spec_*.json`).")
A("- ~23:40-23:44: 14 E6 WebSearch calls (logged by `tools/log_e6_iter6.py`), then retry of the one E5 HTTP 429 (`tools/retry_failed_iter6.py`).")
A("- ~23:46: round 2 (6 queries built from included hits; `evidence/round2_queries_iter6.json`).")
A(f"- ~23:53-23:56: round 3 and round 4 citation chasing (`tools/round3_citations_iter6.py`, `tools/round4_citations_iter6.py`); last logged saturation call {counts['search_window_utc'][1]}.")
A("- 2026-10-21 23:58 - 2026-10-22 00:20: OpenReview record caching via notes/search (`tools/fetch_openreview_iter6.py`; notes?id= returned 403), venue pages, quote building, live QA, scoring, re-screen and rendering.")
A("")
A("## 3. Every logged search call, in order")
A("")
A("| # | UTC | Family | Engine | Query | n | Status |")
A("|---|---|---|---|---|---|---|")
for i, r in enumerate(log, 1):
    q = str(r.get("query", "")).replace("|", "\\|")[:150]
    e = str(r.get("engine", "")).replace("|", "\\|")[:70]
    A(f"| {i} | {r.get('timestamp_utc', '')} | {r.get('family', '')} | {e} | {q} | {r.get('n_results', '')} | {r.get('status', '')} |")
A("")
A("E3 arXiv queries use the `search_query` strings stored in each log record (`arxiv_query`). The raw result lists of every call are in `cache/search_results/` (file name = family_query-tag_engine).")
A("")
A("## 4. Pages and PDFs fetched (verification corpus)")
A("")
A("| Cache key | URL | PDF | Retrieved (UTC) |")
A("|---|---|---|---|")
for r in idx:
    A(f"| {r['key']} | {r['url'][:140]} | {r.get('is_pdf')} | {r.get('retrieved_utc', '')} |")
A("")
A("Fetch failures, logged in `logs/` and section 6 of the report: OpenReview PDFs (8iTqrW1sxY, h57duZqLOr, 6t1egKiB0v, ooV5M72O08, knirOusGcq) returned HTTP 403; the OpenReview notes?id= endpoint returned 403 ChallengeRequiredError; mdpi.com (Computation 14(9) 212) returned 403; the vLLM `latest` FP8 docs URL returned a 73-character stub, so the `stable` URL was used.")
A("")
A("## 5. Verification steps and outcomes")
A("")
A(f"1. `tools/build_quotes_iter6.py` checks every new quote against its cached versioned text, using the inherited normalisation (whitespace, ligatures, curly quotes, dashes, PDF line-end hyphenation, markdown emphasis). Result: {sum(1 for _ in open(EVID / 'quotes_iter6.jsonl'))} quote records, all matched (`evidence/quotes_iter6.jsonl`; status UNVERIFIED would be written for a miss).")
A(f"2. `tools/qa_second_pass_iter6.py` runs an independent live fetch_grep on each quote URL with up to 5 six-token regex windows. Result: {sum(r['second_pass'] == 'MATCH' for r in qa)}/{len(qa)} re-matched (`evidence/qa_second_pass_iter6.jsonl`).")
A(f"3. `tools/check_passages_live_iter6.py` re-fetches every source URL and requires each supporting passage of the structured output to occur literally (whitespace-collapsed). Result: {sum(p['literal_match'] for p in pl)}/{len(pl)} kept (`evidence/passages_live_check_iter6.jsonl`). Three passages, taken from the table quotes, failed this literal check because of markup or JSON escapes. They were replaced by verbatim strings from the same pages (TL;DR field; backtick-quoted sentence; post-emphasis clause).")
A(f"4. `tools/write_scores_iter6.py` scores hits on the frozen O/I/C rubric and writes the flags and corrections. `tools/counts_iter6.py` writes the counts and the same-agent re-screen: n = {kappa['n_rescreened']}, observed agreement {kappa['observed_agreement']}, Cohen's kappa {kappa['cohens_kappa']}.")
A("5. `tools/render_report_iter6.py` renders `research_report.md` (with Table 92e) and `cache/sources_iter6.json`. The structured output's answer is the report text and its sources are that list.")
A("")
A("## 6. How to retrace (same order)")
A("")
A("```bash")
A("PY=$(bash tools/skill_py.sh)            # aii-web-tools interpreter")
A("export SEMANTIC_SCHOLAR_API_KEY=...      # optional; anonymous S2 calls are rate-limited")
A("python3 -I tools/build_row_index_iter6.py")
A("$PY -I tools/write_protocol_iter6.py      # refuses to overwrite the frozen protocol")
A("$PY -I tools/sat_search_iter6.py          # round 1 (+ forward citations) -> evidence/saturation_candidates_iter6.jsonl")
A("$PY -I tools/log_e6_iter6.py              # E6 calls (re-run them with WebSearch to refresh; results drift)")
A("$PY -I tools/retry_failed_iter6.py")
A("$PY -I tools/sat_search_iter6.py --round2 evidence/round2_queries_iter6.json")
A("$PY -I tools/round3_citations_iter6.py && $PY -I tools/round4_citations_iter6.py")
A("$PY -I tools/arxiv_meta.py <ids>  &&  $PY -I tools/fetch_texts.py <ids>   # seeds; --url KEY URL for other pages")
A("$PY -I tools/fetch_openreview_iter6.py 8iTqrW1sxY h57duZqLOr 6t1egKiB0v ooV5M72O08 knirOusGcq BEcwcRFQdu xmDdTDx241 GYm4mg9yGQ MYXgOex05m 5R8LqE51Hr")
A("$PY -I tools/build_quotes_iter6.py && $PY -I tools/qa_second_pass_iter6.py")
A("$PY -I tools/write_scores_iter6.py && $PY -I tools/counts_iter6.py")
A("$PY -I tools/render_report_iter6.py && $PY -I tools/check_passages_live_iter6.py && $PY -I tools/write_repro_iter6.py")
A("```")
A("")
A("Search results drift: arXiv, Semantic Scholar and OpenReview add records daily, and ICLR 2027 records may change venue status. A re-run will reproduce the method and the verified quotes, but not the exact hit counts. The cached texts in `cache/` (kept on the run volume, not published) are the exact versions the quotes were checked against.")
A("")
A("## 7. Deviations from the plan")
A("")
A("- **Stop rule.** The search stopped after round 4 by a logged deviation: rounds 3 and 4 still added hits scoring 1.5, all in the weight-only 'flat score hides behavioural damage' context sub-lane. The 60-minute cap was not reached (about 21 minutes of logged search time).")
A("- **OpenReview.** OpenReview records came from notes/search because notes?id= and PDFs returned 403. The ICLR 2027 rows are therefore VERIFIED-ABSTRACT only.")
A("- **Screening.** One agent screened everything. The re-screen is a same-agent consistency check written minutes after the first pass, so it does not measure independent agreement.")
A("- **Claim wording.** Claim statements come from the artifact plan; the iteration-6 hypothesis text was not available to this executor.")
A("- **Venue lookups.** Six WebSearch venue lookups and five title-resolution calls (arXiv ti: + S2 match) are logged as SEED-LOOKUP and not counted in the saturation totals.")
(WS / "reproducibility.md").write_text("\n".join(L), encoding="utf-8")
print(f"reproducibility.md: {len(L)} lines; {len(log)} log rows; {len(idx)} cached pages")
