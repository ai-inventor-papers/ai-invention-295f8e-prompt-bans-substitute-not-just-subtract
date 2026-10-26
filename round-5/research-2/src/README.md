# Has prior work restored base-model variety? Positioning audit for iteration 5 (Table 92d, 2026-10-21)

This module checks the iteration-5 claims against published work, dated 2026-10-21. The claims are: predicting movability and push landings from the base model's repertoire (A1, A2); transplanting base-model prefill states into the instruct model (B1); the de-sharpening push (B2/D); and the knobs compared head-on (C). Each claim is set against its nearest neighbours with verbatim, versioned quotes. The module also runs a dated saturation search under a protocol frozen before the first call. It is a web-research artifact: CPU only and no LLM API spend. It extends the iteration-4 audit `art_kjrCpQnPaniY` (Tables 92b/92c) and reuses that audit's rubric, toolchain and de-duplication base. The 112 inherited quotes are cited by row id and not re-verified.

**Headline (as of 2026-10-21).**
- **FLAG A — NOT FIRED (narrowly).** No paper writes base-model hidden states into the tuned model and measures output or solution diversity. Each half is published separately:
  - *method*: cross-model patching of base states into a descendant, by Zhou (Y.) 2026 (arXiv 2605.07284), Oozeer et al. (ICML 2025), Du et al. (COLM 2025) and Prakash et al. (ICLR 2024);
  - *goal at the weight level*: Selective Layer Restoration (2602.06665), aligned/base FrankenMerging (2610.22999), layer interpolation in 'Locked at the Entrance' (ICLR 2027 submission), WiSE-FT and Hindsight Merging;
  - *goal at the token level*: BACo, conformative decoding and Switch Generation.
  - B1 may not use 'first' for the transplant mechanism.
- **FLAG B — PARTLY FIRED.** Per-prompt forecasts from the frozen base model of where post-training narrows exist, but at training time and for correctness coverage: Zhou (T.) 2026 (2607.20543), Duan 2026 (2610.04978) and Lookahead (ICLR 2027 submission). Duan finds that base pass rate and likelihood explain only 0.30/0.24 of the explainable variance in gains. No paper forecasts inference-time movability or the landing identity.
- **FLAG C — PARTLY FIRED.** Lee et al. (Findings of EMNLP 2025) compare DeepSeek-Coder-6.7B Base and Instruct with test-checked code and LLM-judge algorithm clusters. The direction is mixed: diversity decreases on easy AtCoder-introductory problems and increases elsewhere. 'First base-vs-tuned algorithm-level comparison' is struck.
- **B2/D:** PASTA (2605.30526) ablates an aligned-minus-base residual direction during decoding against orthogonal random-direction controls. The outcome there is AI-like style, so B2/D is a replication in a new setting.
- **Reviewer baselines implied:**
  - Qwen3-8B Base/Instruct weight interpolation (WiSE-FT; Hindsight Merging: +20-50% pass@10 on code);
  - SLR or FrankenMerging at the B1 block ranges;
  - BACo-style token routing for the base-intent arm;
  - EFT/proxy-tuning logit deltas;
  - template-controlled base-minus-instruct contrasts.
- **Quotes and search.**
  - 137 quotes from 93 references: 111 VERIFIED, 21 VERIFIED-ABSTRACT, 5 VERIFIED-BLOG, 0 mismatches; a live fetch_grep second pass re-matched all 137.
  - 169 logged search calls returned 4,508 raw hits and 3,506 unique records; 49 hits were scored.
  - The stop rule was met after round 3.

## Layout

| Path | What it is |
|---|---|
| `research_report.md` | The report in seven sections plus sources: scope and method; verdict box, flags, permitted wording and reviewer baselines; paste-ready **Table 92d** (55 rows); saturation search (per-claim verdicts, PRISMA counts per family, search-log summary, 49 scored hits); corrections; unverified references; confidence and follow-ups |
| `research_out.json` | Structured output (answer, numbered sources with supporting passages, follow-up questions), saved by the pipeline from the final response |
| `reproducibility.md` | How the research was actually done: tools, env-var names, order of work, every logged search call in order, every page fetched with its timestamp |
| `evidence/protocol.json`, `evidence/protocol.sha256`, `evidence/protocol_amendments.jsonl` | Pre-registered protocol: lanes, 25 query strings, engines, window, rubric, flag definitions, stop rule. Hash, plus one logged timestamp-only amendment |
| `evidence/quotes_iter5.jsonl` | 137 quote records: ref key, id, version quoted, latest version, v1 date, title, first author, venue status and evidence, URL, section, verbatim quote, regex, retrieval date, status, lane, 92d rows, relation |
| `evidence/qa_second_pass_iter5.jsonl` | Independent live re-check of every quote with the skill's `fetch_grep` (137/137 matched) |
| `evidence/passages_live_check_iter5.jsonl` | Live literal check of every supporting passage published in `research_out.json` |
| `evidence/search_log_iter5.jsonl` | Every search call: family, query, engine, filters, number of results, status, timestamp |
| `evidence/saturation_candidates_iter5.jsonl` | 3,506 unique records from all engines and citation rounds, with families, engines, dates, abstracts and an iteration-4 'seen' flag |
| `evidence/screening_iter5.jsonl` | Window flag, keyword groups, lane signals and screening score per record |
| `evidence/saturation_hits_iter5.jsonl` | 49 scored hits: claim-specific O/I/C scores, verdict, v1 date, venue, contemporaneity tags, full-text flag, note |
| `evidence/saturation_counts_iter5.json` | PRISMA-style counts per query family, plus totals |
| `evidence/flags.json` | FLAG A/B/C: definition, candidates (axis scores, decisive sentence), verdict, consequence for wording |
| `evidence/corrections_iter5.jsonl` | 27 corrections and confirmations (versions, titles, venues, tool limits, citation mismatches) |
| `evidence/inherited_ids.json` | The 76 identifiers already quoted by the iteration-4 audit, with their Table 92b/92c row ids |
| `evidence/arxiv_meta.json` | arXiv API metadata for every arXiv id used: latest version, v1 date, authors, comment, journal_ref, abstract |
| `evidence/round2_queries.json` | The 6 round-2 queries built from included-hit vocabulary |
| `inherited/` | Read-only copies of the dependency's evidence (quotes, 1,729 candidates, 63 hits, logs) and its specific tools, kept for provenance |
| `tools/` | The toolchain (see "How to run") |
| `cache/*.txt`, `cache/index.jsonl`, `cache/spec_*.json`, `cache/grep_out/` | Cached full texts of the cited papers, venue pages and OpenReview records, with fetch index and grep specs and logs. Kept on the run volume; excluded from the published repository because they are copies of third-party papers |
| `cache/search_results/` | Raw dated response of every engine call (kept and published; JSON) |
| `cache/answer_iter5.md`, `cache/sources_iter5.json` | Rendered answer and sources used for the structured output |
| `logs/` | stdout logs of the background runs |

## How to run

All scripts use the skill's interpreter and run from this directory with `-I`:

```bash
PY=$(bash tools/skill_py.sh)   # the aii-web-tools skill interpreter
$PY -I tools/arxiv_meta.py $(python3 -c "import json;print(' '.join(json.load(open('evidence/arxiv_meta.json'))))")
$PY -I tools/fetch_texts.py                    # cache latest versions (HTML vN, else PDF vN)
$PY -I tools/fetch_texts.py 2506.17871v1 2506.17871v3 2410.09300v1   # earlier versions for the version checks
$PY -I tools/build_quotes_iter5.py             # verify all quotes against cache/ (137/137)
$PY -I tools/qa_second_pass_iter5.py           # live fetch_grep second pass
$PY -I tools/sat_search_iter5.py               # round 1 (network; SEMANTIC_SCHOLAR_API_KEY recommended)
$PY -I tools/retry_failed_iter5.py             # retries for rate-limited calls
$PY -I tools/sat_search_iter5.py --round2 evidence/round2_queries.json
$PY -I tools/round3_citations_iter5.py         # forward/backward snowballing (stop rule)
$PY -I tools/sat_search_iter5.py --aggregate   # rebuild candidates from cache/search_results/
$PY -I tools/screen_iter5.py 200
$PY -I tools/write_evidence_iter5.py && $PY -I tools/write_flags_iter5.py
$PY -I tools/render_report_iter5.py && $PY -I tools/check_passages_live_iter5.py && $PY -I tools/patch_passages_iter5.py
$PY -I tools/write_repro_iter5.py
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
| `cache/*.txt` | `$PY -I tools/fetch_texts.py` re-downloads every arXiv id in `evidence/arxiv_meta.json` at its recorded latest version. Run `$PY -I tools/fetch_texts.py 2506.17871v1 2506.17871v3 2410.09300v1` for the earlier versions. Venue pages, blogs and the PMLR page are listed with their URLs in `cache/index.jsonl`; re-fetch each with `$PY -I tools/fetch_texts.py --url KEY URL`. Re-fetch the OpenReview records with `$PY -I tools/fetch_openreview_iter5.py FORUM_ID ...` |
| `cache/grep_out/` | `for f in cache/spec_*.json; do $PY -I tools/grep_cache.py --spec $f; done` (after the texts are restored) |
| `inherited/tools/`, `inherited/research_verification.json` | Verbatim copies of the dependency's (art_kjrCpQnPaniY) tool scripts and pipeline verification record. They contain server paths, so they are not republished here; both are in the dependency's own published repository. |
