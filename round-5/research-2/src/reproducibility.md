# Reproducibility — iteration-5 positioning audit (Table 92d)

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
  - sha256 after amendment A1 (a timestamp-only fix): `96c720df49be3307c05715625af56107698959405f96318b519a9b4688c40dba`. The original sha256 is in `evidence/protocol.sha256` and `evidence/protocol_amendments.jsonl`.

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
   - `python -I tools/build_quotes_iter5.py` checked 137 quotes against the cached normalised texts; all matched.
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

## Search calls in the order they were logged (169 calls)

| # | Family | Engine | Query | Results | Status | Logged (UTC) |
|---|---|---|---|---|---|---|
| 1 | F1 | E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/20 | base model aligned diversity collapse code algorithm | 50 | ok | 2026-10-21T14:51:23Z |
| 2 | F1 | E3 arXiv API (cs.CL/cs.LG/cs.AI, sortBy=submittedDate desc,  | base model aligned diversity collapse code algorithm | 50 | ok | 2026-10-21T14:51:23Z |
| 3 | F1 | E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/20 | instruction tuning algorithmic diversity code solutions base instruct | 50 | ok | 2026-10-21T14:51:24Z |
| 4 | F1 | E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/20 | alignment narrows output distribution base model sharpening | 50 | ok | 2026-10-21T14:51:25Z |
| 5 | F2 | E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/20 | predict mode collapse per prompt from base model | 50 | ok | 2026-10-21T14:51:27Z |
| 6 | F1 | E3 arXiv API (cs.CL/cs.LG/cs.AI, sortBy=submittedDate desc,  | instruction tuning algorithmic diversity code solutions base instruct | 50 | ok | 2026-10-21T14:51:27Z |
| 7 | F2 | E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/20 | base model likelihood predicts post-training narrowing | 50 | ok | 2026-10-21T14:51:28Z |
| 8 | F1 | E1 scholarly (OpenAlex/Crossref via aii_fast_web_search.py) | instruction tuning algorithmic diversity code solutions base instruct | 25 | ok | 2026-10-21T14:51:28Z |
| 9 | F2 | E1 scholarly (OpenAlex/Crossref via aii_fast_web_search.py) | predict mode collapse per prompt from base model | 25 | ok | 2026-10-21T14:51:29Z |
| 10 | F1 | E1 scholarly (OpenAlex/Crossref via aii_fast_web_search.py) | alignment narrows output distribution base model sharpening | 25 | ok | 2026-10-21T14:51:29Z |
| 11 | F2 | E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/20 | RLVR reasoning boundary per-problem base model pass@k | 50 | ok | 2026-10-21T14:51:29Z |
| 12 | F1 | E1 scholarly (OpenAlex/Crossref via aii_fast_web_search.py) | base model aligned diversity collapse code algorithm | 25 | ok | 2026-10-21T14:51:29Z |
| 13 | F3 | E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/20 | base aligned model collaboration diversity decoding | 50 | ok | 2026-10-21T14:51:31Z |
| 14 | F1 | E3 arXiv API (cs.CL/cs.LG/cs.AI, sortBy=submittedDate desc,  | alignment narrows output distribution base model sharpening | 50 | ok | 2026-10-21T14:51:32Z |
| 15 | F3 | E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/20 | base model guided decoding instruct diversity | 50 | ok | 2026-10-21T14:51:32Z |
| 16 | F3 | E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/20 | base model plan aligned model completes generation | 50 | ok | 2026-10-21T14:51:33Z |
| 17 | F2 | E1 scholarly (OpenAlex/Crossref via aii_fast_web_search.py) | RLVR reasoning boundary per-problem base model pass@k | 25 | ok | 2026-10-21T14:51:34Z |
| 18 | F1 | E4 Semantic Scholar API (/paper/search) | base model aligned diversity collapse code algorithm | 50 | ok | 2026-10-21T14:51:34Z |
| 19 | F3 | E1 scholarly (OpenAlex/Crossref via aii_fast_web_search.py) | base aligned model collaboration diversity decoding | 25 | ok | 2026-10-21T14:51:34Z |
| 20 | F4 | E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/20 | activation patching base model into chat model | 50 | ok | 2026-10-21T14:51:35Z |
| 21 | F2 | E1 scholarly (OpenAlex/Crossref via aii_fast_web_search.py) | base model likelihood predicts post-training narrowing | 25 | ok | 2026-10-21T14:51:35Z |
| 22 | F3 | E1 scholarly (OpenAlex/Crossref via aii_fast_web_search.py) | base model guided decoding instruct diversity | 25 | ok | 2026-10-21T14:51:35Z |
| 23 | F2 | E3 arXiv API (cs.CL/cs.LG/cs.AI, sortBy=submittedDate desc,  | predict mode collapse per prompt from base model | 28 | ok | 2026-10-21T14:51:35Z |
| 24 | F4 | E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/20 | transplant hidden states base model fine-tuned model | 50 | ok | 2026-10-21T14:51:36Z |
| 25 | F1 | E4 Semantic Scholar API (/paper/search) | instruction tuning algorithmic diversity code solutions base instruct | 15 | ok | 2026-10-21T14:51:36Z |
| 26 | F4 | E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/20 | interpolate activations base and instruct model | 50 | ok | 2026-10-21T14:51:37Z |
| 27 | F2 | E3 arXiv API (cs.CL/cs.LG/cs.AI, sortBy=submittedDate desc,  | base model likelihood predicts post-training narrowing | 13 | ok | 2026-10-21T14:51:39Z |
| 28 | F1 | E4 Semantic Scholar API (/paper/search) | alignment narrows output distribution base model sharpening | 50 | ok | 2026-10-21T14:51:39Z |
| 29 | F4 | E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/20 | steering vector derived from base model applied to instruct model | 50 | ok | 2026-10-21T14:51:39Z |
| 30 | F5 | E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/20 | restore output diversity aligned model base model activations | 50 | ok | 2026-10-21T14:51:40Z |
| 31 | F4 | E1 scholarly (OpenAlex/Crossref via aii_fast_web_search.py) | activation patching base model into chat model | 25 | ok | 2026-10-21T14:51:40Z |
| 32 | F3 | E1 scholarly (OpenAlex/Crossref via aii_fast_web_search.py) | base model plan aligned model completes generation | 25 | ok | 2026-10-21T14:51:41Z |
| 33 | F4 | E1 scholarly (OpenAlex/Crossref via aii_fast_web_search.py) | transplant hidden states base model fine-tuned model | 25 | ok | 2026-10-21T14:51:41Z |
| 34 | F5 | E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/20 | undo alignment sharpening activation steering diversity | 50 | ok | 2026-10-21T14:51:41Z |
| 35 | F2 | E4 Semantic Scholar API (/paper/search) | predict mode collapse per prompt from base model | 50 | ok | 2026-10-21T14:51:42Z |
| 36 | F4 | E1 scholarly (OpenAlex/Crossref via aii_fast_web_search.py) | interpolate activations base and instruct model | 25 | ok | 2026-10-21T14:51:42Z |
| 37 | F2 | E3 arXiv API (cs.CL/cs.LG/cs.AI, sortBy=submittedDate desc,  | RLVR reasoning boundary per-problem base model pass@k | 15 | ok | 2026-10-21T14:51:42Z |
| 38 | F5 | E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/20 | instruct minus base direction steering | 50 | ok | 2026-10-21T14:51:43Z |
| 39 | F6 | E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/20 | reverse post-training sharpening recover base distribution | 50 | ok | 2026-10-21T14:51:44Z |
| 40 | F2 | E4 Semantic Scholar API (/paper/search) | base model likelihood predicts post-training narrowing | 50 | ok | 2026-10-21T14:51:45Z |
| 41 | F6 | E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/20 | weight interpolation base instruct model diversity pass@k | 50 | ok | 2026-10-21T14:51:46Z |
| 42 | F4 | E1 scholarly (OpenAlex/Crossref via aii_fast_web_search.py) | steering vector derived from base model applied to instruct model | 25 | ok | 2026-10-21T14:51:46Z |
| 43 | F3 | E3 arXiv API (cs.CL/cs.LG/cs.AI, sortBy=submittedDate desc,  | base aligned model collaboration diversity decoding | 30 | ok | 2026-10-21T14:51:46Z |
| 44 | F5 | E1 scholarly (OpenAlex/Crossref via aii_fast_web_search.py) | undo alignment sharpening activation steering diversity | 25 | ok | 2026-10-21T14:51:47Z |
| 45 | F6 | E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/20 | extrapolate fine-tuned minus base weights diversity | 50 | ok | 2026-10-21T14:51:47Z |
| 46 | F2 | E4 Semantic Scholar API (/paper/search) | RLVR reasoning boundary per-problem base model pass@k | 31 | ok | 2026-10-21T14:51:47Z |
| 47 | F5 | E1 scholarly (OpenAlex/Crossref via aii_fast_web_search.py) | restore output diversity aligned model base model activations | 25 | ok | 2026-10-21T14:51:47Z |
| 48 | F5 | E1 scholarly (OpenAlex/Crossref via aii_fast_web_search.py) | instruct minus base direction steering | 25 | ok | 2026-10-21T14:51:47Z |
| 49 | F7 | E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/20 | model diffing base chat crosscoder | 50 | ok | 2026-10-21T14:51:48Z |
| 50 | F7 | E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/20 | activation difference base finetuned model | 0 | HTTP 429 | 2026-10-21T14:51:49Z |
| 51 | F3 | E3 arXiv API (cs.CL/cs.LG/cs.AI, sortBy=submittedDate desc,  | base model guided decoding instruct diversity | 50 | ok | 2026-10-21T14:51:50Z |
| 52 | F8 | E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/20 | intent-first generation plan sampling code diversity activation noise | 0 | HTTP 429 | 2026-10-21T14:51:51Z |
| 53 | F6 | E1 scholarly (OpenAlex/Crossref via aii_fast_web_search.py) | reverse post-training sharpening recover base distribution | 25 | ok | 2026-10-21T14:51:51Z |
| 54 | F8 | E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/20 | hidden-state noise injection diverse code solutions | 0 | HTTP 429 | 2026-10-21T14:51:52Z |
| 55 | F7 | E1 scholarly (OpenAlex/Crossref via aii_fast_web_search.py) | model diffing base chat crosscoder | 25 | ok | 2026-10-21T14:51:52Z |
| 56 | F6 | E1 scholarly (OpenAlex/Crossref via aii_fast_web_search.py) | extrapolate fine-tuned minus base weights diversity | 25 | ok | 2026-10-21T14:51:53Z |
| 57 | F9 | E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/20 | test-checked algorithmic diversity base versus instruct code models | 0 | HTTP 429 | 2026-10-21T14:51:53Z |
| 58 | F6 | E1 scholarly (OpenAlex/Crossref via aii_fast_web_search.py) | weight interpolation base instruct model diversity pass@k | 25 | ok | 2026-10-21T14:51:53Z |
| 59 | F3 | E4 Semantic Scholar API (/paper/search) | base aligned model collaboration diversity decoding | 50 | ok | 2026-10-21T14:51:53Z |
| 60 | F3 | E3 arXiv API (cs.CL/cs.LG/cs.AI, sortBy=submittedDate desc,  | base model plan aligned model completes generation | 36 | ok | 2026-10-21T14:51:54Z |
| 61 | F9 | E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/20 | functional correctness algorithm clusters base instruct code LLM | 0 | HTTP 429 | 2026-10-21T14:51:54Z |
| 62 | F7 | E1 scholarly (OpenAlex/Crossref via aii_fast_web_search.py) | activation difference base finetuned model | 25 | ok | 2026-10-21T14:51:55Z |
| 63 | F3 | E4 Semantic Scholar API (/paper/search) | base model guided decoding instruct diversity | 50 | ok | 2026-10-21T14:51:56Z |
| 64 | F4 | E3 arXiv API (cs.CL/cs.LG/cs.AI, sortBy=submittedDate desc,  | activation patching base model into chat model | 11 | ok | 2026-10-21T14:51:57Z |
| 65 | F8 | E1 scholarly (OpenAlex/Crossref via aii_fast_web_search.py) | intent-first generation plan sampling code diversity activation noise | 25 | ok | 2026-10-21T14:51:57Z |
| 66 | F8 | E1 scholarly (OpenAlex/Crossref via aii_fast_web_search.py) | hidden-state noise injection diverse code solutions | 25 | ok | 2026-10-21T14:51:58Z |
| 67 | F9 | E1 scholarly (OpenAlex/Crossref via aii_fast_web_search.py) | test-checked algorithmic diversity base versus instruct code models | 25 | ok | 2026-10-21T14:51:58Z |
| 68 | F9 | E1 scholarly (OpenAlex/Crossref via aii_fast_web_search.py) | functional correctness algorithm clusters base instruct code LLM | 25 | ok | 2026-10-21T14:51:59Z |
| 69 | F3 | E4 Semantic Scholar API (/paper/search) | base model plan aligned model completes generation | 50 | ok | 2026-10-21T14:51:59Z |
| 70 | F4 | E3 arXiv API (cs.CL/cs.LG/cs.AI, sortBy=submittedDate desc,  | transplant hidden states base model fine-tuned model | 6 | ok | 2026-10-21T14:52:01Z |
| 71 | F4 | E4 Semantic Scholar API (/paper/search) | activation patching base model into chat model | 50 | ok | 2026-10-21T14:52:02Z |
| 72 | F4 | E3 arXiv API (cs.CL/cs.LG/cs.AI, sortBy=submittedDate desc,  | interpolate activations base and instruct model | 5 | ok | 2026-10-21T14:52:04Z |
| 73 | F4 | E4 Semantic Scholar API (/paper/search) | transplant hidden states base model fine-tuned model | 50 | ok | 2026-10-21T14:52:05Z |
| 74 | F4 | E4 Semantic Scholar API (/paper/search) | interpolate activations base and instruct model | 50 | ok | 2026-10-21T14:52:07Z |
| 75 | F4 | E3 arXiv API (cs.CL/cs.LG/cs.AI, sortBy=submittedDate desc,  | steering vector derived from base model applied to instruct model | 14 | ok | 2026-10-21T14:52:08Z |
| 76 | F4 | E4 Semantic Scholar API (/paper/search) | steering vector derived from base model applied to instruct model | 5 | ok | 2026-10-21T14:52:09Z |
| 77 | F5 | E3 arXiv API (cs.CL/cs.LG/cs.AI, sortBy=submittedDate desc,  | restore output diversity aligned model base model activations | 50 | ok | 2026-10-21T14:52:12Z |
| 78 | F5 | E3 arXiv API (cs.CL/cs.LG/cs.AI, sortBy=submittedDate desc,  | undo alignment sharpening activation steering diversity | 45 | ok | 2026-10-21T14:52:16Z |
| 79 | F5 | E3 arXiv API (cs.CL/cs.LG/cs.AI, sortBy=submittedDate desc,  | instruct minus base direction steering | 7 | ok | 2026-10-21T14:52:19Z |
| 80 | F5 | E4 Semantic Scholar API (/paper/search) | restore output diversity aligned model base model activations | 50 | ok | 2026-10-21T14:52:21Z |
| 81 | F6 | E3 arXiv API (cs.CL/cs.LG/cs.AI, sortBy=submittedDate desc,  | reverse post-training sharpening recover base distribution | 13 | ok | 2026-10-21T14:52:23Z |
| 82 | F5 | E4 Semantic Scholar API (/paper/search) | undo alignment sharpening activation steering diversity | 7 | ok | 2026-10-21T14:52:23Z |
| 83 | F6 | E3 arXiv API (cs.CL/cs.LG/cs.AI, sortBy=submittedDate desc,  | weight interpolation base instruct model diversity pass@k | 4 | ok | 2026-10-21T14:52:26Z |
| 84 | F5 | E4 Semantic Scholar API (/paper/search) | instruct minus base direction steering | 10 | ok | 2026-10-21T14:52:29Z |
| 85 | F6 | E3 arXiv API (cs.CL/cs.LG/cs.AI, sortBy=submittedDate desc,  | extrapolate fine-tuned minus base weights diversity | 16 | ok | 2026-10-21T14:52:30Z |
| 86 | F6 | E4 Semantic Scholar API (/paper/search) | reverse post-training sharpening recover base distribution | 50 | ok | 2026-10-21T14:52:33Z |
| 87 | F7 | E3 arXiv API (cs.CL/cs.LG/cs.AI, sortBy=submittedDate desc,  | model diffing base chat crosscoder | 19 | ok | 2026-10-21T14:52:33Z |
| 88 | F7 | E3 arXiv API (cs.CL/cs.LG/cs.AI, sortBy=submittedDate desc,  | activation difference base finetuned model | 14 | ok | 2026-10-21T14:52:37Z |
| 89 | F8 | E3 arXiv API (cs.CL/cs.LG/cs.AI, sortBy=submittedDate desc,  | intent-first generation plan sampling code diversity activation noise | 17 | ok | 2026-10-21T14:52:40Z |
| 90 | F8 | E3 arXiv API (cs.CL/cs.LG/cs.AI, sortBy=submittedDate desc,  | hidden-state noise injection diverse code solutions | 2 | ok | 2026-10-21T14:52:44Z |
| 91 | F9 | E3 arXiv API (cs.CL/cs.LG/cs.AI, sortBy=submittedDate desc,  | test-checked algorithmic diversity base versus instruct code models | 50 | ok | 2026-10-21T14:52:48Z |
| 92 | F9 | E3 arXiv API (cs.CL/cs.LG/cs.AI, sortBy=submittedDate desc,  | functional correctness algorithm clusters base instruct code LLM | 16 | ok | 2026-10-21T14:52:52Z |
| 93 | F6 | E4 Semantic Scholar API (/paper/search) | weight interpolation base instruct model diversity pass@k | 0 | rate-limited | 2026-10-21T14:52:57Z |
| 94 | F6 | E4 Semantic Scholar API (/paper/search) | extrapolate fine-tuned minus base weights diversity | 44 | ok | 2026-10-21T14:52:59Z |
| 95 | F7 | E4 Semantic Scholar API (/paper/search) | model diffing base chat crosscoder | 6 | ok | 2026-10-21T14:53:11Z |
| 96 | F7 | E4 Semantic Scholar API (/paper/search) | activation difference base finetuned model | 50 | ok | 2026-10-21T14:53:24Z |
| 97 | F8 | E4 Semantic Scholar API (/paper/search) | intent-first generation plan sampling code diversity activation noise | 0 | ok | 2026-10-21T14:53:25Z |
| 98 | F8 | E4 Semantic Scholar API (/paper/search) | hidden-state noise injection diverse code solutions | 45 | ok | 2026-10-21T14:53:31Z |
| 99 | F9 | E4 Semantic Scholar API (/paper/search) | test-checked algorithmic diversity base versus instruct code models | 1 | ok | 2026-10-21T14:53:33Z |
| 100 | F9 | E4 Semantic Scholar API (/paper/search) | functional correctness algorithm clusters base instruct code LLM | 37 | ok | 2026-10-21T14:53:46Z |
| 101 | FC | S2 /paper/arXiv:{id}/citations | forward citations of arXiv:2511.05650 (BACo) | 0 | rate-limited | 2026-10-21T14:54:10Z |
| 102 | FC | OpenAlex works?filter=cites: | forward citations of arXiv:2511.05650 (BACo) | 0 | ok (openalex W4416156677) | 2026-10-21T14:54:11Z |
| 103 | FC | S2 /paper/arXiv:{id}/citations | forward citations of arXiv:2503.00691 (LeeAlgoDiv) | 12 | ok | 2026-10-21T14:54:12Z |
| 104 | FC | OpenAlex works?filter=cites: | forward citations of arXiv:2503.00691 (LeeAlgoDiv) | 0 | ok (openalex W4416036083) | 2026-10-21T14:54:13Z |
| 105 | FC | S2 /paper/arXiv:{id}/citations | forward citations of arXiv:2507.12638 (WardBacktracking) | 29 | ok | 2026-10-21T14:54:15Z |
| 106 | FC | OpenAlex works?filter=cites: | forward citations of arXiv:2507.12638 (WardBacktracking) | 0 | ok (openalex W4415309610) | 2026-10-21T14:54:15Z |
| 107 | FC | S2 /paper/arXiv:{id}/citations | forward citations of arXiv:2607.20543 (ZhouPassKInversion) | 3 | ok | 2026-10-21T14:54:16Z |
| 108 | FC | OpenAlex works?filter=cites: | forward citations of arXiv:2607.20543 (ZhouPassKInversion) | 0 | ok (openalex W7170567086) | 2026-10-21T14:54:17Z |
| 109 | FC | S2 /paper/arXiv:{id}/citations | forward citations of arXiv:2506.17871 (YangHoltzmanBF) | 25 | ok | 2026-10-21T14:54:22Z |
| 110 | FC | S2 /paper/arXiv:{id}/citations | forward citations of arXiv:2510.01171 (VerbalizedSampling) | 139 | ok | 2026-10-21T14:54:59Z |
| 111 | FC | S2 /paper/arXiv:{id}/citations | forward citations of arXiv:2507.20956 (ConformativeDecoding) | 0 | rate-limited | 2026-10-21T14:55:24Z |
| 112 | FC | S2 /paper/arXiv:{id}/citations | forward citations of arXiv:2504.02922 (MinderCrosscoderBatchTopK) | 34 | ok | 2026-10-21T14:55:48Z |
| 113 | F7 | E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/20 | activation difference base finetuned model | 50 | ok | 2026-10-21T14:56:55Z |
| 114 | F8 | E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/20 | intent-first generation plan sampling code diversity activation noise | 50 | ok | 2026-10-21T14:57:04Z |
| 115 | F8 | E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/20 | hidden-state noise injection diverse code solutions | 50 | ok | 2026-10-21T14:57:13Z |
| 116 | F9 | E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/20 | test-checked algorithmic diversity base versus instruct code models | 50 | ok | 2026-10-21T14:57:23Z |
| 117 | F9 | E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/20 | functional correctness algorithm clusters base instruct code LLM | 50 | ok | 2026-10-21T14:57:32Z |
| 118 | F6 | E4 Semantic Scholar API (/paper/search) | weight interpolation base instruct model diversity pass@k | 16 | ok | 2026-10-21T14:57:34Z |
| 119 | FC | S2 /paper/arXiv:{id}/citations | forward citations of arXiv:2511.05650 (BACo) | 10 | ok | 2026-10-21T14:57:44Z |
| 120 | FC | S2 /paper/arXiv:{id}/citations | forward citations of arXiv:2507.20956 (ConformativeDecoding) | 0 | HTTP 404 | 2026-10-21T14:58:12Z |
| 121 | R2 | E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/20 | cross-model patching base model upstream state into fine-tuned descendant late layers | 50 | ok | 2026-10-21T15:06:04Z |
| 122 | R2 | E3 arXiv API (cs.CL/cs.LG/cs.AI, sortBy=submittedDate desc,  | cross-model patching base model upstream state into fine-tuned descendant late layers | 1 | ok | 2026-10-21T15:06:04Z |
| 123 | R2 | E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/20 | restore layers to pretrained weights recover diversity post-trained model | 50 | ok | 2026-10-21T15:06:06Z |
| 124 | R2 | E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/20 | ablate aligned minus base residual direction during decoding | 50 | ok | 2026-10-21T15:06:07Z |
| 125 | R2 | E3 arXiv API (cs.CL/cs.LG/cs.AI, sortBy=submittedDate desc,  | restore layers to pretrained weights recover diversity post-trained model | 33 | ok | 2026-10-21T15:06:08Z |
| 126 | R2 | E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/20 | merge base and aligned model layers diversity quality trade-off | 50 | ok | 2026-10-21T15:06:08Z |
| 127 | R2 | E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/20 | fine-tuning collapses onto distribution already present in pretrained model | 50 | ok | 2026-10-21T15:06:09Z |
| 128 | R2 | E1 scholarly (OpenAlex/Crossref via aii_fast_web_search.py) | restore layers to pretrained weights recover diversity post-trained model | 25 | ok | 2026-10-21T15:06:10Z |
| 129 | R2 | E1 scholarly (OpenAlex/Crossref via aii_fast_web_search.py) | ablate aligned minus base residual direction during decoding | 25 | ok | 2026-10-21T15:06:10Z |
| 130 | R2 | E1 scholarly (OpenAlex/Crossref via aii_fast_web_search.py) | merge base and aligned model layers diversity quality trade-off | 25 | ok | 2026-10-21T15:06:10Z |
| 131 | R2 | E1 scholarly (OpenAlex/Crossref via aii_fast_web_search.py) | cross-model patching base model upstream state into fine-tuned descendant late layers | 25 | ok | 2026-10-21T15:06:10Z |
| 132 | R2 | E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/20 | predict per-problem post-training gains from base model signals | 50 | ok | 2026-10-21T15:06:11Z |
| 133 | R2 | E3 arXiv API (cs.CL/cs.LG/cs.AI, sortBy=submittedDate desc,  | ablate aligned minus base residual direction during decoding | 8 | ok | 2026-10-21T15:06:12Z |
| 134 | R2 | E1 scholarly (OpenAlex/Crossref via aii_fast_web_search.py) | fine-tuning collapses onto distribution already present in pretrained model | 25 | ok | 2026-10-21T15:06:13Z |
| 135 | R2 | E1 scholarly (OpenAlex/Crossref via aii_fast_web_search.py) | predict per-problem post-training gains from base model signals | 25 | ok | 2026-10-21T15:06:14Z |
| 136 | R2 | E3 arXiv API (cs.CL/cs.LG/cs.AI, sortBy=submittedDate desc,  | merge base and aligned model layers diversity quality trade-off | 12 | ok | 2026-10-21T15:06:15Z |
| 137 | R2 | E3 arXiv API (cs.CL/cs.LG/cs.AI, sortBy=submittedDate desc,  | fine-tuning collapses onto distribution already present in pretrained model | 26 | ok | 2026-10-21T15:06:19Z |
| 138 | R2 | E3 arXiv API (cs.CL/cs.LG/cs.AI, sortBy=submittedDate desc,  | predict per-problem post-training gains from base model signals | 24 | ok | 2026-10-21T15:06:23Z |
| 139 | R2 | E4 Semantic Scholar API (/paper/search) | cross-model patching base model upstream state into fine-tuned descendant late layers | 1 | ok | 2026-10-21T15:06:27Z |
| 140 | R2 | E4 Semantic Scholar API (/paper/search) | restore layers to pretrained weights recover diversity post-trained model | 1 | ok | 2026-10-21T15:06:38Z |
| 141 | R2 | E4 Semantic Scholar API (/paper/search) | ablate aligned minus base residual direction during decoding | 2 | ok | 2026-10-21T15:06:44Z |
| 142 | R2 | E4 Semantic Scholar API (/paper/search) | merge base and aligned model layers diversity quality trade-off | 3 | ok | 2026-10-21T15:06:46Z |
| 143 | R2 | E4 Semantic Scholar API (/paper/search) | fine-tuning collapses onto distribution already present in pretrained model | 0 | ok | 2026-10-21T15:06:47Z |
| 144 | R2 | E4 Semantic Scholar API (/paper/search) | predict per-problem post-training gains from base model signals | 50 | ok | 2026-10-21T15:06:50Z |
| 145 | FC | S2 /paper/arXiv:{id}/citations | forward citations of arXiv:2605.07284 (CrossPatching) | 0 | ok | 2026-10-21T15:09:24Z |
| 146 | FC | S2 /paper/arXiv:{id}/citations | forward citations of arXiv:2602.06665 (SLR) | 1 | ok | 2026-10-21T15:09:48Z |
| 147 | FC | S2 /paper/arXiv:{id}/citations | forward citations of arXiv:2605.30526 (PASTA) | 0 | ok | 2026-10-21T15:09:53Z |
| 148 | FC | S2 /paper/arXiv:{id}/citations | forward citations of arXiv:2610.22999 (FrankenMerging) | 0 | rate-limited | 2026-10-21T15:10:17Z |
| 149 | FC | S2 /paper/arXiv:{id}/citations | forward citations of arXiv:2610.04978 (DuanPerProblem) | 0 | ok | 2026-10-21T15:10:18Z |
| 150 | FC | S2 /paper/arXiv:{id}/citations | forward citations of arXiv:2503.04429 (OozeerTransfer) | 21 | ok | 2026-10-21T15:10:42Z |
| 151 | BC | S2 /paper/arXiv:{id}/references | backward citations of arXiv:2605.07284 (FLAG_A_2605_07284) | 22 | ok | 2026-10-21T15:10:47Z |
| 152 | BC | S2 /paper/arXiv:{id}/references | backward citations of arXiv:2602.06665 (FLAG_A_2602_06665) | 34 | ok | 2026-10-21T15:10:50Z |
| 153 | BC | S2 /paper/arXiv:{id}/references | backward citations of arXiv:2607.20543 (FLAG_B_2607_20543) | 26 | ok | 2026-10-21T15:10:52Z |
| 154 | BC | S2 /paper/arXiv:{id}/references | backward citations of arXiv:2610.04978 (FLAG_B_2610_04978) | 39 | ok | 2026-10-21T15:10:57Z |
| 155 | BC | S2 /paper/arXiv:{id}/references | backward citations of arXiv:2503.00691 (FLAG_C_2503_00691) | 46 | ok | 2026-10-21T15:11:02Z |
| 156 | BC | S2 /paper/arXiv:{id}/references | backward citations of arXiv:2605.28022 (FLAG_C_2605_28022) | 23 | ok | 2026-10-21T15:11:04Z |
| 157 | FC | S2 /paper/arXiv:{id}/citations | forward citations of arXiv:2610.22999 (FrankenMerging) | 0 | ok | 2026-10-21T15:14:53Z |
| 158 | F4 | E6 Claude Code built-in WebSearch (allowed_domains=lesswrong | activation patching base model into chat model | 8 | ok | 2026-10-21T15:20:49Z |
| 159 | F4 | E6 Claude Code built-in WebSearch (allowed_domains=lesswrong | transplant hidden states base model fine-tuned model | 8 | ok | 2026-10-21T15:20:49Z |
| 160 | F4 | E6 Claude Code built-in WebSearch (allowed_domains=lesswrong | interpolate activations base and instruct model | 7 | ok | 2026-10-21T15:20:49Z |
| 161 | F4 | E6 Claude Code built-in WebSearch (allowed_domains=lesswrong | steering vector derived from base model applied to instruct model | 9 | ok | 2026-10-21T15:20:49Z |
| 162 | F5 | E6 Claude Code built-in WebSearch (allowed_domains=lesswrong | restore output diversity aligned model base model activations | 9 | ok | 2026-10-21T15:20:49Z |
| 163 | F5 | E6 Claude Code built-in WebSearch (allowed_domains=lesswrong | undo alignment sharpening activation steering diversity | 9 | ok | 2026-10-21T15:20:49Z |
| 164 | F5 | E6 Claude Code built-in WebSearch (allowed_domains=lesswrong | instruct minus base direction steering | 8 | ok | 2026-10-21T15:20:49Z |
| 165 | F7 | E6 Claude Code built-in WebSearch (allowed_domains=lesswrong | model diffing base chat crosscoder | 9 | ok | 2026-10-21T15:20:49Z |
| 166 | F7 | E6 Claude Code built-in WebSearch (allowed_domains=lesswrong | activation difference base finetuned model | 9 | ok | 2026-10-21T15:20:49Z |
| 167 | lookup | Claude Code built-in WebSearch (general) | Hindsight Merging Veselovsky UAI 2025 interpolate fine-tuned model earlier checkpoint pass@10 coding | 3 | ok | 2026-10-21T15:20:49Z |
| 168 | lookup | Claude Code built-in WebSearch (general) | rephrase circuit instruct model attention heads patched into base model (LessWrong/AF) | 0 | ok | 2026-10-21T15:20:49Z |
| 169 | lookup | Claude Code built-in WebSearch (general) | Decan diversity metric base model per-token log-probabilities ICML 2026 | 1 | ok | 2026-10-21T15:20:49Z |

## Pages and PDFs fetched into cache/ (full texts used for quotes; with retrieval time)

| Key | URL | PDF? | Characters | Retrieved (UTC) |
|---|---|---|---|---|
| 2506.09659v1 | https://arxiv.org/html/2506.09659v1 | False | 279841 | 2026-10-21T06:58:14Z |
| 2407.02209v1 | https://arxiv.org/html/2407.02209v1 | False | 97694 | 2026-10-21T06:58:15Z |
| 2409.03733v2 | https://arxiv.org/html/2409.03733v2 | False | 89951 | 2026-10-21T06:58:15Z |
| 2610.19157v1 | https://arxiv.org/html/2610.19157v1 | False | 77370 | 2026-10-21T06:58:16Z |
| 2406.05946v1 | https://arxiv.org/html/2406.05946v1 | False | 119373 | 2026-10-21T06:58:16Z |
| 2504.05228v4 | https://arxiv.org/html/2504.05228v4 | False | 55730 | 2026-10-21T06:58:16Z |
| 2606.10302v1 | https://arxiv.org/html/2606.10302v1 | False | 90099 | 2026-10-21T06:58:16Z |
| 2510.03215v2 | https://arxiv.org/html/2510.03215v2 | False | 94658 | 2026-10-21T14:51:59Z |
| 2310.04799v3 | https://arxiv.org/html/2310.04799v3 | False | 66578 | 2026-10-21T14:51:59Z |
| 2504.10478v4 | https://arxiv.org/html/2504.10478v4 | False | 76524 | 2026-10-21T14:52:00Z |
| 2607.20543v1 | https://arxiv.org/html/2607.20543v1 | False | 52805 | 2026-10-21T14:52:00Z |
| 2309.16042v2 | https://arxiv.org/html/2309.16042v2 | False | 86726 | 2026-10-21T14:52:00Z |
| 2506.17871v4 | https://arxiv.org/html/2506.17871v4 | False | 120566 | 2026-10-21T14:52:00Z |
| 2401.08565v4 | https://arxiv.org/html/2401.08565v4 | False | 86804 | 2026-10-21T14:52:00Z |
| 2510.01171v4 | https://arxiv.org/html/2510.01171v4 | False | 262677 | 2026-10-21T14:52:00Z |
| 2310.06452v3 | https://arxiv.org/html/2310.06452v3 | False | 117891 | 2026-10-21T14:52:00Z |
| 2608.07460v1 | https://arxiv.org/html/2608.07460v1 | False | 71895 | 2026-10-21T14:52:00Z |
| 2507.12638v1 | https://arxiv.org/html/2507.12638v1 | False | 29325 | 2026-10-21T14:52:00Z |
| 2510.13900v3 | https://arxiv.org/html/2510.13900v3 | False | 319512 | 2026-10-21T14:52:00Z |
| 2511.05650v2 | https://arxiv.org/html/2511.05650v2 | False | 115629 | 2026-10-21T14:52:01Z |
| 2401.06102v4 | https://arxiv.org/html/2401.06102v4 | False | 114131 | 2026-10-21T14:52:01Z |
| 2503.04429v4 | https://arxiv.org/html/2503.04429v4 | False | 222999 | 2026-10-21T14:52:01Z |
| 2605.09995v1 | https://arxiv.org/html/2605.09995v1 | False | 79250 | 2026-10-21T14:52:01Z |
| 2311.14479v3 | https://arxiv.org/html/2311.14479v3 | False | 119067 | 2026-10-21T14:52:01Z |
| 2410.12877v2 | https://arxiv.org/html/2410.12877v2 | False | 132714 | 2026-10-21T14:52:01Z |
| 2212.04089v3 | https://arxiv.org/html/2212.04089v3 | False | 108858 | 2026-10-21T14:52:01Z |
| 2507.14843v5 | https://arxiv.org/html/2507.14843v5 | False | 94163 | 2026-10-21T14:52:01Z |
| 2410.09300v4 | https://arxiv.org/html/2410.09300v4 | False | 185174 | 2026-10-21T14:52:01Z |
| 2411.04427v3 | https://arxiv.org/html/2411.04427v3 | False | 62960 | 2026-10-21T14:52:01Z |
| 2507.20956v1 | https://arxiv.org/html/2507.20956v1 | False | 60524 | 2026-10-21T14:52:01Z |
| 2312.01552v1 | https://arxiv.org/html/2312.01552v1 | False | 98992 | 2026-10-21T14:52:01Z |
| 2406.05587v1 | https://arxiv.org/pdf/2406.05587v1 | True | 73294 | 2026-10-21T14:52:01Z |
| 2510.14901v1 | https://arxiv.org/html/2510.14901v1 | False | 70288 | 2026-10-21T14:52:01Z |
| 2404.15255v1 | https://arxiv.org/html/2404.15255v1 | False | 48938 | 2026-10-21T14:52:02Z |
| 2504.13837v5 | https://arxiv.org/html/2504.13837v5 | False | 81468 | 2026-10-21T14:52:02Z |
| 2511.19131v1 | https://arxiv.org/html/2511.19131v1 | False | 73569 | 2026-10-21T14:52:02Z |
| 2504.08775v3 | https://arxiv.org/html/2504.08775v3 | False | 67512 | 2026-10-21T14:52:02Z |
| 2310.12962v1 | https://arxiv.org/html/2310.12962v1 | False | 61756 | 2026-10-21T14:52:02Z |
| 2510.02230v1 | https://arxiv.org/html/2510.02230v1 | False | 91766 | 2026-10-21T14:52:02Z |
| 2505.00047v2 | https://arxiv.org/html/2505.00047v2 | False | 81478 | 2026-10-21T14:52:02Z |
| 2404.16792v5 | https://arxiv.org/html/2404.16792v5 | False | 74528 | 2026-10-21T14:52:02Z |
| 2510.07364v4 | https://arxiv.org/html/2510.07364v4 | False | 180360 | 2026-10-21T14:52:02Z |
| 2509.04259v1 | https://arxiv.org/html/2509.04259v1 | False | 81435 | 2026-10-21T14:52:02Z |
| 2605.30021v2 | https://arxiv.org/html/2605.30021v2 | False | 129840 | 2026-10-21T14:52:02Z |
| 2507.21509v3 | https://arxiv.org/html/2507.21509v3 | False | 186663 | 2026-10-21T14:52:03Z |
| 2412.01951v2 | https://arxiv.org/html/2412.01951v2 | False | 247986 | 2026-10-21T14:52:03Z |
| 2504.02922v4 | https://arxiv.org/html/2504.02922v4 | False | 286949 | 2026-10-21T14:52:03Z |
| 2506.17871v1 | https://arxiv.org/html/2506.17871v1 | False | 74792 | 2026-10-21T14:52:04Z |
| 2506.17871v3 | https://arxiv.org/html/2506.17871v3 | False | 89314 | 2026-10-21T14:52:04Z |
| 2410.09300v1 | https://arxiv.org/html/2410.09300v1 | False | 166509 | 2026-10-21T14:52:04Z |
| 2602.16189v1 | https://arxiv.org/html/2602.16189v1 | False | 41595 | 2026-10-21T14:55:16Z |
| 2604.02319v3 | https://arxiv.org/html/2604.02319v3 | False | 94060 | 2026-10-21T14:55:16Z |
| 2608.11426v2 | https://arxiv.org/html/2608.11426v2 | False | 77025 | 2026-10-21T14:55:16Z |
| 2510.09913v1 | https://arxiv.org/html/2510.09913v1 | False | 78525 | 2026-10-21T14:55:16Z |
| 2505.17697v1 | https://arxiv.org/html/2505.17697v1 | False | 64976 | 2026-10-21T14:55:16Z |
| 2604.13694v1 | https://arxiv.org/html/2604.13694v1 | False | 205213 | 2026-10-21T14:55:17Z |
| 2603.04426v1 | https://arxiv.org/html/2603.04426v1 | False | 80853 | 2026-10-21T14:55:17Z |
| 2605.28022v1 | https://arxiv.org/html/2605.28022v1 | False | 80202 | 2026-10-21T14:55:17Z |
| 2509.06608v4 | https://arxiv.org/html/2509.06608v4 | False | 95839 | 2026-10-21T14:55:17Z |
| 2606.01811v1 | https://arxiv.org/html/2606.01811v1 | False | 116519 | 2026-10-21T14:55:17Z |
| 2604.08169v3 | https://arxiv.org/html/2604.08169v3 | False | 110682 | 2026-10-21T14:55:17Z |
| 2602.11729v1 | https://arxiv.org/html/2602.11729v1 | False | 264158 | 2026-10-21T14:55:17Z |
| 2608.29610v1 | https://arxiv.org/html/2608.29610v1 | False | 617158 | 2026-10-21T14:55:18Z |
| tc_crosscoders_2024 | https://transformer-circuits.pub/2024/crosscoders/index.html | False | 45512 | 2026-10-21T14:55:36Z |
| tc_crosscoder_diffing_2025 | https://transformer-circuits.pub/2025/crosscoder-diffing-update/index.html | False | 16327 | 2026-10-21T14:55:38Z |
| pmlr_hindsight_merging | https://proceedings.mlr.press/v286/veselovsky25a.html | False | 6438 | 2026-10-21T14:55:39Z |
| pmlr_hindsight_merging_pdf | https://raw.githubusercontent.com/mlresearch/v286/main/assets/veselovsky25a/veselovsky25a.pdf | True | 69185 | 2026-10-21T14:55:41Z |
| af_kissane_sae_transfer | https://www.alignmentforum.org/posts/fmwk6qxrpW8d4jvbd/saes-usually-transfer-between-base-and-chat-models | False | 21090 | 2026-10-21T14:55:43Z |
| lw_diff_base_chat | https://www.lesswrong.com/posts/xmpauEXEerzYcJKNm/what-we-learned-trying-to-diff-base-and-chat-models-and-why | False | 25690 | 2026-10-21T14:55:45Z |
| lw_runtime_steering | https://www.lesswrong.com/posts/dvbRv97GpRg5gXKrf/run-time-steering-can-surpass-post-training-reasoning-task | False | 14748 | 2026-10-21T14:55:47Z |
| acl_nudging | https://aclanthology.org/2025.acl-long.623/ | False | 17526 | 2026-10-21T14:55:50Z |
| acl_lee_findings | https://aclanthology.org/2025.findings-emnlp.10/ | False | 19409 | 2026-10-21T14:55:52Z |
| 2605.07284v2 | https://arxiv.org/html/2605.07284v2 | False | 54722 | 2026-10-21T15:02:12Z |
| 2610.24663v1 | https://arxiv.org/html/2610.24663v1 | False | 97056 | 2026-10-21T15:02:13Z |
| 2610.04978v1 | https://arxiv.org/html/2610.04978v1 | False | 40855 | 2026-10-21T15:02:13Z |
| 2610.22999v1 | https://arxiv.org/html/2610.22999v1 | False | 57823 | 2026-10-21T15:02:13Z |
| 2602.04735v1 | https://arxiv.org/html/2602.04735v1 | False | 76468 | 2026-10-21T15:02:13Z |
| 2603.02787v1 | https://arxiv.org/html/2603.02787v1 | False | 82548 | 2026-10-21T15:02:13Z |
| 2607.02808v1 | https://arxiv.org/html/2607.02808v1 | False | 74271 | 2026-10-21T15:02:13Z |
| 2607.03174v1 | https://arxiv.org/html/2607.03174v1 | False | 73879 | 2026-10-21T15:02:13Z |
| 2606.15455v1 | https://arxiv.org/html/2606.15455v1 | False | 83648 | 2026-10-21T15:02:13Z |
| 2603.24124v2 | https://arxiv.org/html/2603.24124v2 | False | 120224 | 2026-10-21T15:02:13Z |
| 2607.01433v1 | https://arxiv.org/html/2607.01433v1 | False | 70504 | 2026-10-21T15:02:13Z |
| 2603.06957v2 | https://arxiv.org/html/2603.06957v2 | False | 209847 | 2026-10-21T15:02:13Z |
| 2604.00012v1 | https://arxiv.org/html/2604.00012v1 | False | 79061 | 2026-10-21T15:02:13Z |
| 2605.24583v3 | https://arxiv.org/html/2605.24583v3 | False | 48936 | 2026-10-21T15:02:13Z |
| 2608.30319v1 | https://arxiv.org/html/2608.30319v1 | False | 86076 | 2026-10-21T15:02:13Z |
| or_hu5mtofNd4 | https://api2.openreview.net/notes/search?term=Locked%20at%20the%20Entrance%2C%20Open%20Inside%3A%20Where%20RLVR%20Narrow | False | 2017 | 2026-10-21T15:02:31Z |
| or_cMasrdysrX | https://api2.openreview.net/notes/search?term=Where%20Does%20RLVR%20Act%3F%20A%20Conserved%20Token%20Ledger%20for%20What | False | 1810 | 2026-10-21T15:02:34Z |
| or_3QlKFFBcNO | https://api2.openreview.net/notes/search?term=Not%20Which%20Path%2C%20but%20What%20Happens%20Before%20You%20Would%20Stop | False | 2001 | 2026-10-21T15:02:36Z |
| or_iIw2d3AkJM | https://api2.openreview.net/notes/search?term=Base%20Models%20Can%20Reason%20by%20Taking%20a%20Cue%20from%20Their%20Trai | False | 1483 | 2026-10-21T15:02:39Z |
| or_6a4v7CpeAu | https://api2.openreview.net/notes/search?term=Catching%20RLHF%20Failures%20before%20Training&group=ICLR.cc/2027/Conferen | False | 1484 | 2026-10-21T15:02:43Z |
| or_uASUNrduuj | https://api2.openreview.net/notes/search?term=How%20Much%2C%20Not%20Where%3A%20RLVR%27s%20Capability%20Loss%20Is%20Dose- | False | 1872 | 2026-10-21T15:02:46Z |
| or_BEcwcRFQdu | https://api2.openreview.net/notes/search?term=Predictive%20Mechanistic%20Interpretability%20of%20Post-Training%3A%20A%20 | False | 2066 | 2026-10-21T15:02:48Z |
| or_vkIOGTVcJP | https://api2.openreview.net/notes/search?term=Training-Induced%20Reasoning%20Directions%3A%20Uncovering%20Reusable%20Str | False | 1687 | 2026-10-21T15:02:51Z |
| or_MYXgOex05m | https://api2.openreview.net/notes/search?term=Should%20SFT%20Prefer%20the%20Familiar%3F%20Diversity%20Collapse%20and%20R | False | 1719 | 2026-10-21T15:02:54Z |
| or_tzXBBz5tmq | https://api2.openreview.net/notes/search?term=Logit%20Grafting%3A%20The%20Post-Training%20Delta%20is%20Sparse%2C%20Porta | False | 1936 | 2026-10-21T15:02:57Z |
| or_fnMHUImLl3 | https://api2.openreview.net/notes/search?term=Judging%20RLVR%20Boundary%20Comparisons%20Against%20Their%20Own%20Measured | False | 2040 | 2026-10-21T15:03:00Z |
| or_lZQK4G4Ktp | https://api2.openreview.net/notes/search?term=RESTORING%20DIVERSITY%20IN%20DISTILLED%20IMAGE%20AND%20VIDEO%20GENERATORS% | False | 1700 | 2026-10-21T15:03:03Z |
| or_YEdSmE0OzZ | https://api2.openreview.net/notes/search?term=Divergence%20Decoding%3A%20Training-Free%20Capability%20Fusion&group=ICLR. | False | 1723 | 2026-10-21T15:03:06Z |
| 2602.06665v1 | https://arxiv.org/html/2602.06665v1 | False | 70941 | 2026-10-21T15:04:50Z |
| 2609.33936v1 | https://arxiv.org/html/2609.33936v1 | False | 150891 | 2026-10-21T15:04:50Z |
| 2606.29933v1 | https://arxiv.org/html/2606.29933v1 | False | 46337 | 2026-10-21T15:04:50Z |
| 2610.24223v1 | https://arxiv.org/html/2610.24223v1 | False | 53734 | 2026-10-21T15:04:50Z |
| 2607.12796v4 | https://arxiv.org/html/2607.12796v4 | False | 73899 | 2026-10-21T15:04:51Z |
| 2609.16454v1 | https://arxiv.org/html/2609.16454v1 | False | 134685 | 2026-10-21T15:04:51Z |
| 2605.16874v1 | https://arxiv.org/html/2605.16874v1 | False | 96555 | 2026-10-21T15:04:51Z |
| 2605.27878v2 | https://arxiv.org/html/2605.27878v2 | False | 143070 | 2026-10-21T15:04:51Z |
| 2605.30844v1 | https://arxiv.org/html/2605.30844v1 | False | 124879 | 2026-10-21T15:04:51Z |
| 2605.30526v2 | https://arxiv.org/html/2605.30526v2 | False | 165564 | 2026-10-21T15:04:51Z |
| 2402.14811v1 | https://arxiv.org/html/2402.14811v1 | False | 92078 | 2026-10-21T15:15:58Z |
| 2504.07912v2 | https://arxiv.org/html/2504.07912v2 | False | 96728 | 2026-10-21T15:15:59Z |
| 2608.09217v1 | https://arxiv.org/html/2608.09217v1 | False | 98864 | 2026-10-21T15:15:59Z |
| 2504.02904v3 | https://arxiv.org/html/2504.02904v3 | False | 104874 | 2026-10-21T15:15:59Z |
| or_ooV5M72O08 | https://api2.openreview.net/notes/search?term=Same%20Candidates%2C%20Stronger%20Reasoning%3A%20Rethinking%20What%20Post- | False | 1834 | 2026-10-21T15:16:18Z |
| neurips_rbp_2026 | https://neurips.cc/virtual/2026/poster/150680 | False | 6718 | 2026-10-21T15:23:53Z |

## Notes on drift and limits

- The engines are E1 OpenAlex/Crossref, E3 arXiv API, E4 Semantic Scholar, E5 OpenReview and E6 WebSearch. Each was queried with the frozen strings; E3 used the term lists in `evidence/protocol.json`.
- OpenAlex `cites:` returned 0 citing works for all four nearest neighbours because OpenAlex records `cited_by_count = 0` for them, so forward citations rest on Semantic Scholar alone.
- Conformative decoding (2507.20956) is not indexed in Semantic Scholar, so its forward citations could not be chased.
- ICLR 2027 submissions are abstract-only: openreview.net PDFs return HTTP 403 to scripted access.
- The 112 quotes inherited from art_kjrCpQnPaniY were not re-verified; they are cited by Table 92b/92c row id (`evidence/inherited_ids.json`).
