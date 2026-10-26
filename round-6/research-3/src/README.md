# Who already found the hidden plan? A dated positioning audit (Table 92e)

This audit places the iteration-6 claims of an automated research run against the published literature: P1-P5 (a causal "plan" variable for which algorithm Qwen3-8B writes), N (reading and editing that plan with natural language autoencoders), S (Gemma Scope 2 SAEs and transcoders) and E (FP8 W8A8 activation rounding). Each claim gets its nearest published neighbour and a verbatim, versioned quote checked against the source's own text.

It follows a protocol frozen before the first search call (sha256-stamped) and runs a 3-round saturation search over 7 lanes and 5 engines. It returns verdicts on four novelty flags: **A NOT FIRED (narrowly), B PARTLY FIRED, C FIRED, D PARTLY FIRED**. It extends Tables 92b/92c (art_kjrCpQnPaniY) and 92d (art_ObxQOIlAM9MS), whose rows are cited by id.

Headline facts:
- The NLA paper (7 May 2026) already edits an explanation of a plan and steers with it, so N is a replication.
- Steering under quantization has been studied, in the arXiv record, only with weight-only quantization. Contemporaneous ICLR 2027 submissions show effects change across precision, but their abstracts do not name activation quantization.
- DAS-based steering validated by generation exists only for non-plan attributes. Algorithm choice in code has been moved only by prompt cues.
- SAE-feature steering of reasoning strategies is published (ACL 2026).

## Layout

| Path | What it is |
|---|---|
| `research_report.md` | The full report: summary, PRISMA-S method, verdict box, flags, Table 92e, permitted wording, reviewer baselines, departures, corrections, follow-ups |
| `research_out.json` | Structured output (answer = report text; 120 numbered sources with literal supporting passages); saved by the pipeline |
| `reproducibility.md` | What was actually run, in order, with timestamps, tools and env-var names |
| `evidence/protocol_iter6.json`, `protocol_iter6.sha256` | Frozen protocol (lanes, 21 strings, engines, rubric, flags, stop rule) and its stamp |
| `evidence/protocol_amendments_iter6.jsonl` | Timestamped amendments (flag-A interpretation note, tool reuse, stop-rule entries) |
| `evidence/search_log_iter6.jsonl` | Every search call: UTC time, engine, string, hit count, top-20 ids (rounds R1, R2, R3, FC, BR) |
| `evidence/round2_queries_iter6.json` | Round-2 strings with the hit that motivated each |
| `evidence/saturation_candidates_iter6.jsonl` | De-duplicated candidates (see saturation_counts_iter6.json for raw and unique counts) |
| `evidence/screening_iter6.jsonl` | Window flag, keyword lane groups and pre-screen score per candidate |
| `evidence/saturation_hits_iter6.jsonl` | O/I/C scores with decisive sentences for every scored paper (see saturation_counts_iter6.json), plus a one-line verdict for every in-window record |
| `evidence/saturation_counts_iter6.json` | PRISMA-style counts |
| `evidence/quotes_iter6.jsonl` | 123 new verified quotes (source, URL, locator, version, v1 date, venue, status, check result) |
| `evidence/qa_second_pass_iter6.jsonl` | Independent live fetch_grep re-match of every quote (123/123) |
| `evidence/passages_live_check_iter6.jsonl` | Live literal check of the supporting passages in research_out.json (114/114) |
| `evidence/flags_iter6.json` | Flag A-D verdicts, decisive sentences, quote ids, what would change them |
| `evidence/corrections_iter6.jsonl` | 24 corrections and confirmations (NLA citation and date, Qwen3-8B community NLAs, venues, titles) |
| `evidence/inherited_index.json` | Index of the 207 inherited 92b/92c/92d sources (cited by id, not re-verified) |
| `evidence/arxiv_meta.json` | arXiv API metadata (latest version, v1 date, comment and journal-ref) for every arXiv id used |
| `inherited/` | Copies of the two dependency outputs (research_out.json, research_verification.json) |
| `tools/` | All scripts (search, screening, quote building, QA, scoring, rendering); `tools/quotes_spec_iter6.py` lists every new quote |
| `cache/` | Fetched source texts, OpenReview records, raw search results, grep outputs. Text only; kept on the run's volume but excluded from the public repo (fetched copyrighted texts) |
| `logs/` | Run logs of the background jobs |

## How to run

See `reproducibility.md`. In short:

```bash
PY=${AII_SKILLS_DIR}/.ability_client_venv/bin/python
$PY -I tools/sat_search_iter6.py --round1 && $PY -I tools/sat_search_iter6.py --fc
$PY -I tools/sat_search_iter6.py --round2 evidence/round2_queries_iter6.json && $PY -I tools/round3_iter6.py
$PY -I tools/build_quotes_iter6.py && $PY -I tools/qa_second_pass_iter6.py
python3 -I tools/score_hits_iter6.py && python3 -I tools/write_flags_corrections_iter6.py
$PY -I tools/render_report_iter6.py && $PY -I tools/check_passages_live_iter6.py
```

`AII_SKILLS_DIR` is the `.claude/skills` directory of the AI Inventor checkout that holds the aii-web-tools skill and its interpreter. `tools/common.py` finds it by walking up from this directory, or reads it from the environment.

E4 calls need `SEMANTIC_SCHOLAR_API_KEY` in the environment; without it they fall back to anonymous calls and are logged as such.

## Restoring removed files

- `tools/__pycache__/` is regenerable: `python3 -m compileall -q tools`.
- `cache/` is not a manifest entry. It is text only, so it is kept automatically on the run's volume, but it is left out of the public repository (upload ignore pattern `(^|/)cache/`). To rebuild it if needed:
  - arXiv texts: `$PY -I tools/arxiv_meta.py <ids> && $PY -I tools/fetch_texts.py <ids>`, with the ids in `evidence/arxiv_meta.json`;
  - grey-literature pages: `$PY -I tools/fetch_texts.py --url <key> <url>`, with the keys and URLs in `evidence/quotes_iter6.jsonl` and `logs/fetch_urls_*.sh`;
  - OpenReview records: `$PY -I tools/fetch_openreview_iter6.py <forum ids>`;
  - raw search results: rerun the search commands above. Results drift over time.
