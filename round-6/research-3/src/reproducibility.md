# Reproducibility: how this audit was actually run (2026-10-22, UTC)

This file records what was done, in order, with the tools that were used. Every search call is in `evidence/search_log_iter6.jsonl`. Every fetched page is in `cache/index.jsonl`, which records the URL, whether it was a PDF, and the retrieval time.

## Tools and environment

- **Skill.** aii-web-tools: `aii_fast_web_search.py --mode scholarly` (OpenAlex/Crossref) and `aii_fast_web_fetch.py` (fetch and fetch_grep), run with the skill interpreter `${AII_SKILLS_DIR}/.ability_client_venv/bin/python`.
  - The skill's fetch core (`aii_fast_web_fetch._fetch_url`) cached full texts: html2text for HTML and PyMuPDF for PDF.
  - The `grep` subcommand did the independent live QA pass.
- **Built-in tools.** WebSearch did seed lookups and engine E6, restricted to the protocol's grey-literature domains. WebFetch was used once, to test an OpenReview PDF; that page was a browser check.
- **APIs called directly** (through the skill's requests session):
  - arXiv API: `export.arxiv.org/api/query`, for search and for `id_list` metadata.
  - Semantic Scholar Graph API: `/paper/search` with year=2026, `/citations` and `/references`.
  - OpenReview API v2: `api2.openreview.net/notes/search?group=ICLR.cc/2027/Conference`.
- **Environment variables (names only).**
  - `SEMANTIC_SCHOLAR_API_KEY`: E4 calls. They fall back to anonymous and are logged as such when absent.
  - The skill's ability-server key and `SERPER_API_KEY` are used by aii-web-tools for its own fallbacks.
  - No other keys are needed.
- **Python helpers in `tools/`.** Several were copied from the two prior audits (art_kjrCpQnPaniY, art_ObxQOIlAM9MS) and adapted: `common.py`, `arxiv_meta.py`, `fetch_texts.py`, `grep_cache.py`, `sat_search_iter6.py`, `screen_iter6.py`, `qa_second_pass_iter6.py`, `check_passages_live_iter6.py`. The others are new: `build_inherited_index.py`, `write_protocol_iter6.py`, `fetch_openreview_iter6.py`, `rerun_failed_iter6.py`, `log_e6.py`, `quotes_spec_iter6.py`, `build_quotes_iter6.py`, `score_hits_iter6.py`, `round3_iter6.py`, `write_flags_corrections_iter6.py`, `qa_rerun_iter6.py`, `render_report_iter6.py`, `report_template_iter6.md`.

## Order of work (actual)

1. **06:16-06:18. Inherited material.**
   - Copied `research_out.json` and `research_verification.json` of both dependencies to `inherited/`.
   - Built `evidence/inherited_index.json` (207 sources) and ran presence checks for every reference the plan named. DAS, MIB, Sutter, Makelov, NLA, Gemma Scope 2, circuit-tracer, AxBench and the quantization papers were absent. Patchscopes was present (92d [88]); "Forking Paths" was absent.
2. **06:19:27. Protocol frozen** (`evidence/protocol_iter6.json`; sha256 `88e3bab2e451d477009ac5c62d284b00e2614a50fc583f86380cc71b26f3c4bc`).
3. **06:20:40-06:29:12. Round 1** (`python -I tools/sat_search_iter6.py --round1`): 21 strings. E3, E4 and E5 for all; E1 for L1, L4 and L6. The strings are in the protocol file, q1-q21, in this order:
   - q1 'distributed alignment search' generation steering;
   - q2 'interchange intervention' strategy OR algorithm language model;
   - q3 causal variable localization code generation OR program synthesis;
   - q4 pre-generation planning subspace causal intervention language model;
   - q5 'response planning' OR 'latent plan' hidden state before generation code;
   - q6 predict which algorithm OR approach a language model will use from hidden states;
   - q7 causal abstraction alignment map expressivity random model baseline;
   - q8 'interpretability illusion' subspace patching;
   - q9 interventions off-distribution 'divergent representations' OR out-of-distribution activation patching;
   - q10 'natural language autoencoder' OR 'activation verbalizer';
   - q11 LatentQA OR 'activation oracle' OR SelfIE steering OR control;
   - q12 edit explanation reconstruct activation steering;
   - q13 sparse autoencoder steering reasoning strategy OR algorithm OR code;
   - q14 'Gemma Scope 2' OR transcoder attribution graph Gemma 3;
   - q15 difference-in-means versus sparse autoencoder steering AxBench 2026;
   - q16 quantization 'steering vectors' OR 'activation steering';
   - q17 FP8 OR W8A8 OR INT8 'activation patching' OR interpretability OR 'sparse autoencoder';
   - q18 numerical precision bf16 reproducibility LLM outputs;
   - q19 latent variable resampling output diversity language model;
   - q20 activation noise OR hidden-state perturbation diversity code generation;
   - q21 plan sampling diverse solutions latent intent.

   Three calls hit HTTP 429 (q7 E4, q12 E4, q21 E5) and were re-run by `tools/rerun_failed_iter6.py`.
4. **06:21-06:22. Snowballing** (`--fc`).
   - Forward citations on Semantic Scholar: MIB `arXiv:2504.13151` (61), ERP `arXiv:2502.06258` (20), Steering Under Compression `arXiv:2609.06473` (0).
   - Because 2609.06473 had 0 citers, the backward references of 2609.06473 and 2606.03002 were used.
   - The NLA paper did not resolve on Semantic Scholar, so it was handled by E6.
5. **06:21-06:31. Seed verification.**
   - `tools/arxiv_meta.py` fetched metadata for 37 seed arXiv ids.
   - `tools/fetch_texts.py` cached arXiv HTML for the latest version, falling back to the PDF.
   - Grey literature cached with `fetch_texts.py --url`:
     - transformer-circuits NLA page; kitft README; HF card kitft/nla-qwen2.5-7b-L20-av and its `nla_meta.yaml`;
     - HF google/gemma-scope-2 and gemma-scope-2-4b-it; circuit-tracer README;
     - arXiv abs 2506.09501v1; friendli.ai nanoNLA; PMLR SelfIE page (`chen24ao`; `chen24ae` was a wrong guess and was not used);
     - Sood Substack post; LessWrong and GreaterWrong Gemma Scope 2 announcement; anthropic.com NLA page; GreaterWrong "Can You Hide From a NLA?";
     - Gemma Scope 2 technical report PDF; HF mwhanna/qwen3-8b-transcoders; HF ceselder/nanoNLA; nanoNLA README and qwen3_8b_run.md;
     - llm-compressor FP8 README (the vLLM FP8 docs page returned a stub; the raw doc path returned 404);
     - ICLR 2024 poster 19100; PMLR v236 geiger24a; TransformerLens issue #1884; LessWrong Dreaming Vectors; EasyNLA README;
     - transformer-circuits attribution-graph methods page (no "quarter" sentence) and biology page (sentence found).
   - Exact passages were located with `tools/grep_cache.py` specs (`cache/spec_a.json` to `spec_g.json`).
6. **06:26-06:29. E6 grey literature** (built-in WebSearch, allowed_domains = transformer-circuits.pub, lesswrong.com, alignmentforum.org, huggingface.co, github.com, neuronpedia.org, substack.com).
   - Strings q10, q11, q12, q13+q14 (combined), q14, q15, q16, q17, q18, plus the NLA forward search ("natural language autoencoders" replication follow-up Qwen Gemma NLA checkpoint).
   - Logged with `tools/log_e6.py` (logging time used as the timestamp).
   - Seed lookups, not logged as saturation calls: the Sood post title; "Gemma Scope 2" technical report; "Announcing Gemma Scope 2"; the SelfIE PMLR page; the Makelov ICLR 2024 page.
7. **06:30:38-06:31:13. Round 2** (`--round2 evidence/round2_queries_iter6.json`): 6 strings, each with its motivating hit, on E1, E3, E4 and E5.
8. **06:31-06:36. Shortlist texts.** 29 more arXiv texts and 23 OpenReview API records (`tools/fetch_openreview_iter6.py`).
   - OpenReview PDFs (`openreview.net/pdf/...` and `api2.../attachment`) returned HTTP 403, and WebFetch reached only a browser check. ICLR 2027 rows are therefore abstract-only.
   - An arXiv title search for preprint versions of the flag-B submissions returned nothing.
9. **06:41-06:45. Quotes.** `tools/build_quotes_iter6.py` checked every quote in `tools/quotes_spec_iter6.py` against the cached text (normalization and [...] rule from `tools/common.py`).
   - 4 mismatches (MathML doubles and markdown emphasis) were fixed by splitting with [...] or correcting the wording.
   - Result: 121/121 MATCH.
10. **06:43-07:02. QA.** `tools/qa_second_pass_iter6.py` re-matched every quote live with the skill's `fetch_grep`, giving 119/120.
    - E-17 failed because arXiv HTML for 2609.26621 returns 404. The quote's URL was corrected to the PDF and re-run with `tools/qa_rerun_iter6.py`, together with late quote P2-7.
    - Result: 121/121. Quote S-13b (SAE-Steering baselines), added during proofreading (live re-match logged at 2026-10-22T07:07:28Z), was verified (122/122 against cache) and re-matched live by `tools/qa_rerun_iter6.py` (122/122).
11. **06:48:43-06:49:45. Round 3** (`tools/round3_iter6.py`). The stop rule fired because round 2 gave new hits scoring at least 1.5.
    - Forward and backward references of 2610.20683, 2610.20808 and 2607.20469. The OpenReview-only sbVictHY9s and eZYeqPZlFr did not resolve on Semantic Scholar.
    - No new hit scored at least 1.5, so the search stopped.
12a. **07:09-07:10. Supplementary searches** (round SUPP in the search log; general-web WebSearch outside the frozen strings).
    - Three searches looked for preprint versions of the abstract-only ICLR 2027 neighbours behind flags B and D (8iTqrW1sxY, h57duZqLOr, eZYeqPZlFr). None was found.
    - They surfaced 2602.06801 (steering-vector non-identifiability). It was added as P2-8, verified against the cache and re-matched live (123/123).
12. **Screening and scoring.** `tools/screen_iter6.py` ran the keyword pre-screen. `tools/score_hits_iter6.py` produced the O/I/C scores and a one-line verdict for every in-window record. `tools/write_flags_corrections_iter6.py` wrote the flags, corrections and amendments.
13. **Report.** `tools/render_report_iter6.py` numbered the citations and filled the counts. `tools/check_passages_live_iter6.py` re-fetched every cited URL and kept only `supporting_passages` that occur literally (whitespace-collapsed).

## How to retrace

```bash
PY=${AII_SKILLS_DIR}/.ability_client_venv/bin/python
$PY -I tools/sat_search_iter6.py --round1     # then --fc, then --round2 evidence/round2_queries_iter6.json
$PY -I tools/round3_iter6.py
python3 -I tools/screen_iter6.py 200
$PY -I tools/arxiv_meta.py <ids>; $PY -I tools/fetch_texts.py <ids>   # full texts -> cache/
$PY -I tools/build_quotes_iter6.py           # 121/121 expected while sources are unchanged
$PY -I tools/qa_second_pass_iter6.py          # live re-match
python3 -I tools/score_hits_iter6.py; python3 -I tools/write_flags_corrections_iter6.py
$PY -I tools/render_report_iter6.py; $PY -I tools/check_passages_live_iter6.py
```

Search results drift. arXiv "newest first" lists, the ICLR 2027 pool and Semantic Scholar citation counts change daily, so a later re-run will not reproduce the exact hit lists. The cached raw results in `cache/search_results/` and the logged top-20 ids preserve what was seen on 2026-10-22.
