# Checking our claims against published work (positioning audit, 2026-10-21)

This module puts each positive claim of iterations 3 and 4 of the run next to its nearest published finding. Every neighbour gets a verbatim quote from the paper's own versioned text, with URL, section, version and retrieval date. The module also runs a dated saturation search for papers that might already occupy a claim. It is a web-research artifact: no GPU and no LLM API spend. Searches and fetches use the `aii-web-tools` skill scripts and fetch core, Claude Code's built-in WebSearch, and the public arXiv, Semantic Scholar and OpenReview APIs.

**Headline (as of 2026-10-21).**
- **No paper occupies any claim. FLAG A** (test-checked, algorithm-level diversity under activation perturbation) and **FLAG B** (prompt-ban compliance predicted from perturbation sensitivity or steerability) **did not fire.**
- **C3a and C3b are OPEN.**
- **C1, C1-site, C2a, C2-geometry and b6 are PARTLY OCCUPIED.** Activation noise for diversity is a saturated method lane. C1's contrast set lacks the text-level plan sampler (IFG / PlanSearch / 2606.10302 Level-2 / Gacha) and a decoding baseline matched to the perturbation's departure from greedy.
- **Venue corrections:** Manifold Steering (2605.05115) is an ICML 2026 *workshop* spotlight; IFG (2506.09659) is an ICML 2025 *workshop* poster; the Invisible Lottery (2606.04057) is confirmed as an ICML 2026 main-conference poster. Tang's "implementation priors" (2604.07192, Sec. 5.3) is verified, not a mismatch.
- **ICLR 2027 contemporaneity** is a two-month rule that exempts arXiv-only papers.

## Layout

| Path | What it is |
|---|---|
| `research_report.md` | The report: method, verdict box + flags, Table 92b (iteration-3 claims), Table 92c (iteration-4 claims), saturation search (per-claim verdicts, per-family counts, search-log summary, 63 scored hits), corrections, unverified references, follow-up questions |
| `research_out.json` | Structured output (answer + numbered sources + follow-up questions), saved by the pipeline from the final response |
| `reproducibility.md` | How the research was actually done: queries in order, engines, pages fetched, env-var names, how to retrace |
| `evidence/quotes.jsonl` | 112 quote records (74 references): ref key, arXiv id, version quoted, latest version, title, first author, venue status + evidence, URL, section, verbatim quote, regex, retrieval date, status (VERIFIED / VERIFIED-ABSTRACT) |
| `evidence/qa_second_pass.jsonl` | Independent live re-check of every quote with the skill's `fetch_grep` CLI (112/112 matched) |
| `evidence/arxiv_meta.json` | arXiv API metadata for 105 IDs (latest version, v1 date, authors, comment, journal_ref, abstract) |
| `evidence/search_log.jsonl` | Every search call: family, query, engine, date filter, n_results, status, timestamp |
| `evidence/saturation_candidates.jsonl` | 1,729 unique records from all engines (with families, engines, dates, abstracts) |
| `evidence/screening.jsonl` | Window flag, keyword-group matches and closeness score per candidate |
| `evidence/saturation_hits.jsonl` | 63 scored hits: O/I/C axis scores, verdict, v1 date, venue, contemporaneity tags, note |
| `evidence/saturation_counts.json` | PRISMA-style counts per query family |
| `evidence/corrections.jsonl` | 14 corrections and confirmations (venues, versions, wording, policy) |
| `tools/common.py` | Paths, the plan's quote-normalisation rule, quote matcher (imports the skill's fetch core) |
| `tools/arxiv_meta.py` | arXiv API metadata fetcher (id_list) |
| `tools/fetch_texts.py` | Caches full texts (arXiv HTML vN, then PDF vN; or any URL) into `cache/` |
| `tools/grep_cache.py` | Regex grep over cached texts (same windowing as fetch_grep); `--spec` batch mode |
| `tools/sat_search.py` | Saturation search driver (E1 scholarly, E3 arXiv API / arxiv.org search fallback, E4 Semantic Scholar, E5 OpenReview ICLR 2027, forward citations); `--e3-only`, `--e3-web`, `--only-citations`, `--aggregate` |
| `tools/screen.py` | Date window + keyword pre-screen + closeness ranking for manual screening |
| `tools/build_quotes.py` | All quotes with locators, verified against cached text; writes `evidence/quotes.jsonl` |
| `tools/write_evidence.py` | Scored saturation hits (rubric), per-family counts |
| `tools/qa_second_pass.py` | Independent live second pass with the skill's `aii_fast_web_fetch.py grep` |
| `tools/render_report.py` | Renders `research_report.md`, `cache/answer.md` and `cache/sources.json` from the evidence files. Each supporting passage is the longest span of a verified quote that occurs literally (whitespace-collapsed only) in the fetched page text |
| `tools/check_passages_live.py` | Re-fetches every source URL live and keeps only passages that occur literally in the fetched text (98/98 kept); log in `evidence/passages_live_check.jsonl` |
| `cache/index.jsonl` | Which URL each cached text came from, when, and whether it was a PDF |
| `cache/spec_*.json` | The grep specifications used for each table row |
| `cache/search_results/` | Raw per-query engine responses (kept; dated) |
| `cache/*.txt`, `cache/grep_out/` | Cached full texts of the cited papers and venue pages, plus grep logs. Kept on the run's volume, but excluded from the published repository because they are copies of third-party papers |

## How to run

All scripts use the skill's interpreter and must run from this directory with `-I`:

```bash
PY=/ai-inventor/.claude/skills/.ability_client_venv/bin/python
$PY -I tools/arxiv_meta.py $(python3 -c "import json;print(' '.join(json.load(open('evidence/arxiv_meta.json'))))")
$PY -I tools/fetch_texts.py                      # latest versions of every ID in evidence/arxiv_meta.json
$PY -I tools/build_quotes.py                     # verifies all 112 quotes against the cached texts
$PY -I tools/sat_search.py                       # full saturation search (needs network; SEMANTIC_SCHOLAR_API_KEY recommended)
$PY -I tools/sat_search.py --aggregate           # rebuild evidence/saturation_candidates.jsonl from cache/search_results/
$PY -I tools/screen.py 400                       # screening table
$PY -I tools/write_evidence.py                   # scored hits + counts
$PY -I tools/qa_second_pass.py                   # live second pass (fetch_grep CLI)
$PY -I tools/render_report.py                    # research_report.md
```

Re-running the search on a later date will return different hits because indexes drift. The dated raw responses used here are in `cache/search_results/`.

## Restoring removed files

`.aii/manifest.yaml` has one `delete` entry:

| Removed path | Restore with |
|---|---|
| `tools/__pycache__/` | `python3 -m compileall -q tools`. Python also recreates it automatically when the tools are imported. |

## Files kept on the run volume but not published

The cached paper texts (`cache/*.txt`) and grep logs (`cache/grep_out/`) stay in this workspace on the run's volume. The publish step skips them through `upload_ignore_regexes`, so a fork of the published repository does not contain them. To rebuild them in a fork:

| Path | Rebuild with |
|---|---|
| `cache/*.txt` | `$PY -I tools/fetch_texts.py` re-downloads every arXiv ID in `evidence/arxiv_meta.json` at its recorded latest version. For the earlier versions used in the version checks, run `$PY -I tools/fetch_texts.py 2606.14530v1 2606.14530v2 2606.17648v1 2606.17648v2 2610.09571v1 2604.03380v1 2605.11936v1 2604.07192v1 2605.07984v1 2604.27251v1`. The unversioned-HTML papers, venue and policy pages, and OpenReview records are listed with their URLs in `cache/index.jsonl`; re-fetch each with `$PY -I tools/fetch_texts.py --url KEY URL`. |
| `cache/grep_out/` | `for f in cache/spec_*.json; do $PY -I tools/grep_cache.py --spec $f; done` (after the texts are restored) |
