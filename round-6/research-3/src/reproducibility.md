# Reproducibility: how this audit was actually conducted

This file records what was run, in order, for the iteration-6 positioning audit (Table 92e). It is generated from the logs by `tools/write_repro_iter6.py`, so the query list and the page list are the logged ones, not an idealised plan.

## 1. Tools, skill and environment

- **Skill:** aii-web-tools. Search used `aii_fast_web_search.py --mode scholarly` (engine E1, OpenAlex/Crossref). Pages were fetched with the skill's fetch core (`aii_fast_web_fetch._fetch_url`: html2text for HTML, PyMuPDF for PDF), imported by `tools/common.py`. The independent live re-match used `aii_fast_web_fetch.py grep` (fetch_grep). Every script runs with the skill's interpreter (`.claude/skills/.ability_client_venv/bin/python`, located by `tools/skill_py.sh`).
- **Structured APIs** were called through the same requests session, following the engine settings of the iteration-5 audit: arXiv export API (E3; metadata), Semantic Scholar Graph API (E4; forward/backward citations), OpenReview API v2 `notes/search` (E5; ICLR 2027 abstract records), and OpenAlex `works?filter=cites:` (one logged attempt per mandatory neighbour).
- **Built-in tools:** the Claude Code WebSearch tool ran the E6 grey-literature calls (allowed_domains lists in the log) and six venue-confirmation lookups. WebSearch returns model-written summaries, which were used only to find URLs; every quoted passage comes from a fetched page.
- **Environment variables (names only):** `SEMANTIC_SCHOLAR_API_KEY` (E4/FC/BC; sent as `x-api-key`). `SERPER_API_KEY` is the aii-web-tools paid fallback for search. Optionally set `AII_SKILLS_DIR` to point at the skills directory. No OpenRouter or other LLM API was called.
- **Protocol:** `evidence/protocol_iter6.json`, frozen before the first search call at 2026-10-21T23:34:28Z, sha256 `0e2dc2d70b0e2dac7463f631ee60327f6ee30dae8ff6e028fcca93722fda9c52`. No amendments (`evidence/protocol_amendments_iter6.jsonl`).

## 2. Timeline (UTC)

- 23:32-23:34: loaded the two dependency audits (art_kjrCpQnPaniY, art_ObxQOIlAM9MS), copied their research_out/verification/quotes/candidate files into `inherited/`, built `inherited/row_index.json`, and froze the protocol.
- 2026-10-21T23:35:20Z onward: round 1 (21 frozen strings on E1/E3/E4/E5, plus forward citations of 4 mandatory and 4 as-time-allows seeds) ran in the background (`tools/sat_search_iter6.py`). In parallel, seed metadata and full texts were fetched (`tools/arxiv_meta.py`, `tools/fetch_texts.py`) and grepped (`tools/grep_cache.py`, specs in `logs/spec_*.json`).
- ~23:40-23:44: 14 E6 WebSearch calls (logged by `tools/log_e6_iter6.py`), then retry of the one E5 HTTP 429 (`tools/retry_failed_iter6.py`).
- ~23:46: round 2 (6 queries built from included hits; `evidence/round2_queries_iter6.json`).
- ~23:53-23:56: round 3 and round 4 citation chasing (`tools/round3_citations_iter6.py`, `tools/round4_citations_iter6.py`); last logged saturation call 2026-10-21T23:56:15Z.
- 2026-10-21 23:58 - 2026-10-22 00:20: OpenReview record caching via notes/search (`tools/fetch_openreview_iter6.py`; notes?id= returned 403), venue pages, quote building, live QA, scoring, re-screen and rendering.

## 3. Every logged search call, in order

| # | UTC | Family | Engine | Query | n | Status |
|---|---|---|---|---|---|---|
| 1 | 2026-10-21T23:35:20Z | FE1 | E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/2027/Confere | activation quantization steering vector effect | 50 | ok |
| 2 | 2026-10-21T23:35:20Z | FE1 | E3 arXiv API (cs.CL/cs.LG/cs.AI, sortBy=submittedDate desc, max 50) | activation quantization steering vector effect | 27 | ok |
| 3 | 2026-10-21T23:35:21Z | FE1 | E4 Semantic Scholar API (/paper/search) | activation quantization steering vector effect | 25 | ok |
| 4 | 2026-10-21T23:35:21Z | FE1 | E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/2027/Confere | FP8 activation quantization interpretability intervention | 50 | ok |
| 5 | 2026-10-21T23:35:22Z | FE1 | E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/2027/Confere | quantized model activation patching reproducibility precision | 50 | ok |
| 6 | 2026-10-21T23:35:23Z | FE1 | E4 Semantic Scholar API (/paper/search) | FP8 activation quantization interpretability intervention | 3 | ok |
| 7 | 2026-10-21T23:35:24Z | FE1 | E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/2027/Confere | W8A8 INT8 activation steering robustness | 50 | ok |
| 8 | 2026-10-21T23:35:24Z | FE1 | E3 arXiv API (cs.CL/cs.LG/cs.AI, sortBy=submittedDate desc, max 50) | FP8 activation quantization interpretability intervention | 50 | ok |
| 9 | 2026-10-21T23:35:25Z | FE1 | E1 scholarly (OpenAlex/Crossref via aii_fast_web_search.py) | activation quantization steering vector effect | 25 | ok |
| 10 | 2026-10-21T23:35:25Z | FE1 | E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/2027/Confere | numerical precision bf16 fp32 mechanistic interpretability results differ | 50 | ok |
| 11 | 2026-10-21T23:35:25Z | FE1 | E1 scholarly (OpenAlex/Crossref via aii_fast_web_search.py) | W8A8 INT8 activation steering robustness | 12 | ok |
| 12 | 2026-10-21T23:35:25Z | FE1 | E1 scholarly (OpenAlex/Crossref via aii_fast_web_search.py) | FP8 activation quantization interpretability intervention | 25 | ok |
| 13 | 2026-10-21T23:35:25Z | FE1 | E1 scholarly (OpenAlex/Crossref via aii_fast_web_search.py) | quantized model activation patching reproducibility precision | 25 | ok |
| 14 | 2026-10-21T23:35:25Z | FE1 | E4 Semantic Scholar API (/paper/search) | quantized model activation patching reproducibility precision | 50 | ok |
| 15 | 2026-10-21T23:35:26Z | FE2 | E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/2027/Confere | batch invariance nondeterminism LLM inference precision | 50 | ok |
| 16 | 2026-10-21T23:35:27Z | FE1 | E4 Semantic Scholar API (/paper/search) | W8A8 INT8 activation steering robustness | 1 | ok |
| 17 | 2026-10-21T23:35:28Z | FE1 | E3 arXiv API (cs.CL/cs.LG/cs.AI, sortBy=submittedDate desc, max 50) | quantized model activation patching reproducibility precision | 50 | ok |
| 18 | 2026-10-21T23:35:28Z | FE2 | E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/2027/Confere | quantization changes model behaviour flips beyond accuracy | 50 | ok |
| 19 | 2026-10-21T23:35:29Z | FE1 | E4 Semantic Scholar API (/paper/search) | numerical precision bf16 fp32 mechanistic interpretability results differ | 0 | ok |
| 20 | 2026-10-21T23:35:29Z | FE2 | E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/2027/Confere | activation outliers FP8 per-token scale perturbation sensitivity | 50 | ok |
| 21 | 2026-10-21T23:35:30Z | FE1 | E1 scholarly (OpenAlex/Crossref via aii_fast_web_search.py) | numerical precision bf16 fp32 mechanistic interpretability results differ | 25 | ok |
| 22 | 2026-10-21T23:35:30Z | FL1 | E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/2027/Confere | base model predicts aligned model alternatives after perturbation | 50 | ok |
| 23 | 2026-10-21T23:35:30Z | FE2 | E1 scholarly (OpenAlex/Crossref via aii_fast_web_search.py) | batch invariance nondeterminism LLM inference precision | 25 | ok |
| 24 | 2026-10-21T23:35:30Z | FE2 | E1 scholarly (OpenAlex/Crossref via aii_fast_web_search.py) | quantization changes model behaviour flips beyond accuracy | 25 | ok |
| 25 | 2026-10-21T23:35:30Z | FE2 | E1 scholarly (OpenAlex/Crossref via aii_fast_web_search.py) | activation outliers FP8 per-token scale perturbation sensitivity | 25 | ok |
| 26 | 2026-10-21T23:35:31Z | FE1 | E3 arXiv API (cs.CL/cs.LG/cs.AI, sortBy=submittedDate desc, max 50) | W8A8 INT8 activation steering robustness | 41 | ok |
| 27 | 2026-10-21T23:35:31Z | FE2 | E4 Semantic Scholar API (/paper/search) | batch invariance nondeterminism LLM inference precision | 38 | ok |
| 28 | 2026-10-21T23:35:32Z | FL1 | E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/2027/Confere | post-training preserves base model ranking of candidates | 50 | ok |
| 29 | 2026-10-21T23:35:33Z | FL1 | E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/2027/Confere | steered or perturbed tuned model reverts to pretraining distribution | 50 | ok |
| 30 | 2026-10-21T23:35:34Z | FE2 | E4 Semantic Scholar API (/paper/search) | quantization changes model behaviour flips beyond accuracy | 50 | ok |
| 31 | 2026-10-21T23:35:34Z | FL1 | E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/2027/Confere | token-level distribution shift RL fine-tuning base top-k | 50 | ok |
| 32 | 2026-10-21T23:35:35Z | FL1 | E1 scholarly (OpenAlex/Crossref via aii_fast_web_search.py) | base model predicts aligned model alternatives after perturbation | 25 | ok |
| 33 | 2026-10-21T23:35:35Z | FL1 | E1 scholarly (OpenAlex/Crossref via aii_fast_web_search.py) | steered or perturbed tuned model reverts to pretraining distribution | 25 | ok |
| 34 | 2026-10-21T23:35:36Z | FL2 | E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/2027/Confere | power sharpening base distribution alignment typicality | 50 | ok |
| 35 | 2026-10-21T23:35:36Z | FE2 | E4 Semantic Scholar API (/paper/search) | activation outliers FP8 per-token scale perturbation sensitivity | 5 | ok |
| 36 | 2026-10-21T23:35:36Z | FL1 | E1 scholarly (OpenAlex/Crossref via aii_fast_web_search.py) | token-level distribution shift RL fine-tuning base top-k | 25 | ok |
| 37 | 2026-10-21T23:35:36Z | FL1 | E1 scholarly (OpenAlex/Crossref via aii_fast_web_search.py) | post-training preserves base model ranking of candidates | 25 | ok |
| 38 | 2026-10-21T23:35:37Z | FL2 | E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/2027/Confere | fine-tuning reweights rather than adds capabilities support | 50 | ok |
| 39 | 2026-10-21T23:35:38Z | FE1 | E3 arXiv API (cs.CL/cs.LG/cs.AI, sortBy=submittedDate desc, max 50) | numerical precision bf16 fp32 mechanistic interpretability results differ | 50 | ok |
| 40 | 2026-10-21T23:35:38Z | FS1 | E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/2027/Confere | forking tokens algorithm choice code generation | 50 | ok |
| 41 | 2026-10-21T23:35:39Z | FL1 | E4 Semantic Scholar API (/paper/search) | base model predicts aligned model alternatives after perturbation | 50 | ok |
| 42 | 2026-10-21T23:35:39Z | FL2 | E1 scholarly (OpenAlex/Crossref via aii_fast_web_search.py) | power sharpening base distribution alignment typicality | 25 | ok |
| 43 | 2026-10-21T23:35:39Z | FS1 | E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/2027/Confere | pre-generation planning state causal intervention | 50 | ok |
| 44 | 2026-10-21T23:35:41Z | FL2 | E1 scholarly (OpenAlex/Crossref via aii_fast_web_search.py) | fine-tuning reweights rather than adds capabilities support | 25 | ok |
| 45 | 2026-10-21T23:35:41Z | FS1 | E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/2027/Confere | noise injection site layer comparison LLM generation diversity | 50 | ok |
| 46 | 2026-10-21T23:35:41Z | FS1 | E1 scholarly (OpenAlex/Crossref via aii_fast_web_search.py) | forking tokens algorithm choice code generation | 25 | ok |
| 47 | 2026-10-21T23:35:41Z | FS1 | E1 scholarly (OpenAlex/Crossref via aii_fast_web_search.py) | pre-generation planning state causal intervention | 25 | ok |
| 48 | 2026-10-21T23:35:41Z | FE2 | E3 arXiv API (cs.CL/cs.LG/cs.AI, sortBy=submittedDate desc, max 50) | batch invariance nondeterminism LLM inference precision | 14 | ok |
| 49 | 2026-10-21T23:35:42Z | FS1 | E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/2027/Confere | logit margin temperature invariance sampling | 50 | ok |
| 50 | 2026-10-21T23:35:43Z | FS1 | E1 scholarly (OpenAlex/Crossref via aii_fast_web_search.py) | noise injection site layer comparison LLM generation diversity | 25 | ok |
| 51 | 2026-10-21T23:35:44Z | FK1 | E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/2027/Confere | weight interpolation base instruct model code diversity | 50 | ok |
| 52 | 2026-10-21T23:35:45Z | FL1 | E4 Semantic Scholar API (/paper/search) | post-training preserves base model ranking of candidates | 50 | ok |
| 53 | 2026-10-21T23:35:45Z | FK1 | E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/2027/Confere | base model guided decoding diversity code | 50 | ok |
| 54 | 2026-10-21T23:35:45Z | FS1 | E1 scholarly (OpenAlex/Crossref via aii_fast_web_search.py) | logit margin temperature invariance sampling | 25 | ok |
| 55 | 2026-10-21T23:35:46Z | FE2 | E3 arXiv API (cs.CL/cs.LG/cs.AI, sortBy=submittedDate desc, max 50) | quantization changes model behaviour flips beyond accuracy | 50 | ok |
| 56 | 2026-10-21T23:35:46Z | FK1 | E1 scholarly (OpenAlex/Crossref via aii_fast_web_search.py) | base model guided decoding diversity code | 25 | ok |
| 57 | 2026-10-21T23:35:46Z | FK1 | E1 scholarly (OpenAlex/Crossref via aii_fast_web_search.py) | weight interpolation base instruct model code diversity | 25 | ok |
| 58 | 2026-10-21T23:35:46Z | FK1 | E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/2027/Confere | proxy tuning emulated fine-tuning diversity | 0 | HTTP 429 |
| 59 | 2026-10-21T23:35:46Z | FK1 | E1 scholarly (OpenAlex/Crossref via aii_fast_web_search.py) | proxy tuning emulated fine-tuning diversity | 25 | ok |
| 60 | 2026-10-21T23:35:49Z | FE2 | E3 arXiv API (cs.CL/cs.LG/cs.AI, sortBy=submittedDate desc, max 50) | activation outliers FP8 per-token scale perturbation sensitivity | 20 | ok |
| 61 | 2026-10-21T23:35:50Z | FL1 | E4 Semantic Scholar API (/paper/search) | steered or perturbed tuned model reverts to pretraining distribution | 0 | ok |
| 62 | 2026-10-21T23:35:52Z | FL1 | E4 Semantic Scholar API (/paper/search) | token-level distribution shift RL fine-tuning base top-k | 12 | ok |
| 63 | 2026-10-21T23:35:53Z | FL1 | E3 arXiv API (cs.CL/cs.LG/cs.AI, sortBy=submittedDate desc, max 50) | base model predicts aligned model alternatives after perturbation | 28 | ok |
| 64 | 2026-10-21T23:35:55Z | FL2 | E4 Semantic Scholar API (/paper/search) | power sharpening base distribution alignment typicality | 50 | ok |
| 65 | 2026-10-21T23:35:56Z | FL1 | E3 arXiv API (cs.CL/cs.LG/cs.AI, sortBy=submittedDate desc, max 50) | post-training preserves base model ranking of candidates | 46 | ok |
| 66 | 2026-10-21T23:35:57Z | FL2 | E4 Semantic Scholar API (/paper/search) | fine-tuning reweights rather than adds capabilities support | 50 | ok |
| 67 | 2026-10-21T23:36:00Z | FS1 | E4 Semantic Scholar API (/paper/search) | forking tokens algorithm choice code generation | 50 | ok |
| 68 | 2026-10-21T23:36:00Z | FL1 | E3 arXiv API (cs.CL/cs.LG/cs.AI, sortBy=submittedDate desc, max 50) | steered or perturbed tuned model reverts to pretraining distribution | 0 | ok |
| 69 | 2026-10-21T23:36:03Z | FS1 | E4 Semantic Scholar API (/paper/search) | pre-generation planning state causal intervention | 50 | ok |
| 70 | 2026-10-21T23:36:06Z | FL1 | E3 arXiv API (cs.CL/cs.LG/cs.AI, sortBy=submittedDate desc, max 50) | token-level distribution shift RL fine-tuning base top-k | 17 | ok |
| 71 | 2026-10-21T23:36:08Z | FS1 | E4 Semantic Scholar API (/paper/search) | noise injection site layer comparison LLM generation diversity | 0 | ok |
| 72 | 2026-10-21T23:36:12Z | FL2 | E3 arXiv API (cs.CL/cs.LG/cs.AI, sortBy=submittedDate desc, max 50) | power sharpening base distribution alignment typicality | 46 | ok |
| 73 | 2026-10-21T23:36:13Z | FS1 | E4 Semantic Scholar API (/paper/search) | logit margin temperature invariance sampling | 2 | ok |
| 74 | 2026-10-21T23:36:15Z | FK1 | E4 Semantic Scholar API (/paper/search) | weight interpolation base instruct model code diversity | 50 | ok |
| 75 | 2026-10-21T23:36:17Z | FL2 | E3 arXiv API (cs.CL/cs.LG/cs.AI, sortBy=submittedDate desc, max 50) | fine-tuning reweights rather than adds capabilities support | 50 | ok |
| 76 | 2026-10-21T23:36:18Z | FK1 | E4 Semantic Scholar API (/paper/search) | base model guided decoding diversity code | 50 | ok |
| 77 | 2026-10-21T23:36:20Z | FK1 | E4 Semantic Scholar API (/paper/search) | proxy tuning emulated fine-tuning diversity | 50 | ok |
| 78 | 2026-10-21T23:36:21Z | FS1 | E3 arXiv API (cs.CL/cs.LG/cs.AI, sortBy=submittedDate desc, max 50) | forking tokens algorithm choice code generation | 50 | ok |
| 79 | 2026-10-21T23:36:25Z | FS1 | E3 arXiv API (cs.CL/cs.LG/cs.AI, sortBy=submittedDate desc, max 50) | pre-generation planning state causal intervention | 50 | ok |
| 80 | 2026-10-21T23:36:30Z | FS1 | E3 arXiv API (cs.CL/cs.LG/cs.AI, sortBy=submittedDate desc, max 50) | noise injection site layer comparison LLM generation diversity | 50 | ok |
| 81 | 2026-10-21T23:36:33Z | FS1 | E3 arXiv API (cs.CL/cs.LG/cs.AI, sortBy=submittedDate desc, max 50) | logit margin temperature invariance sampling | 43 | ok |
| 82 | 2026-10-21T23:36:37Z | FK1 | E3 arXiv API (cs.CL/cs.LG/cs.AI, sortBy=submittedDate desc, max 50) | weight interpolation base instruct model code diversity | 50 | ok |
| 83 | 2026-10-21T23:36:41Z | FK1 | E3 arXiv API (cs.CL/cs.LG/cs.AI, sortBy=submittedDate desc, max 50) | base model guided decoding diversity code | 50 | ok |
| 84 | 2026-10-21T23:36:45Z | FK1 | E3 arXiv API (cs.CL/cs.LG/cs.AI, sortBy=submittedDate desc, max 50) | proxy tuning emulated fine-tuning diversity | 50 | ok |
| 85 | 2026-10-21T23:36:49Z | FC | S2 /paper/arXiv:{id}/citations | forward citations of arXiv:2609.06473 (SteeringUnderCompression) | 0 | ok |
| 86 | 2026-10-21T23:36:49Z | FC | OpenAlex works?filter=cites: | forward citations of arXiv:2609.06473 (SteeringUnderCompression) | 0 | ok (openalex W7212081815) |
| 87 | 2026-10-21T23:36:55Z | FC | S2 /paper/arXiv:{id}/citations | forward citations of arXiv:2603.22446 (SparseButCritical) | 24 | ok |
| 88 | 2026-10-21T23:36:55Z | FC | OpenAlex works?filter=cites: | forward citations of arXiv:2603.22446 (SparseButCritical) | 0 | ok (openalex W7140276309) |
| 89 | 2026-10-21T23:36:57Z | FC | S2 /paper/arXiv:{id}/citations | forward citations of arXiv:2412.07961 (ForkingPaths) | 48 | ok |
| 90 | 2026-10-21T23:36:57Z | FC | OpenAlex works?filter=cites: | forward citations of arXiv:2412.07961 (ForkingPaths) | 0 | ok (openalex W4405300950) |
| 91 | 2026-10-21T23:36:59Z | FC | S2 /paper/arXiv:{id}/citations | forward citations of arXiv:2506.09501 (GiveMeFP32) | 80 | ok |
| 92 | 2026-10-21T23:37:00Z | FC | OpenAlex works?filter=cites: | forward citations of arXiv:2506.09501 (GiveMeFP32) | 3 | ok (openalex W6891883032) |
| 93 | 2026-10-21T23:37:02Z | FC | S2 /paper/arXiv:{id}/citations | forward citations of arXiv:2510.14901 (ReasoningWithSampling) | 95 | ok |
| 94 | 2026-10-21T23:37:06Z | FC | S2 /paper/arXiv:{id}/citations | forward citations of arXiv:2506.19143 (ThoughtAnchors) | 148 | ok |
| 95 | 2026-10-21T23:37:08Z | FC | S2 /paper/arXiv:{id}/citations | forward citations of arXiv:2604.09839 (NonSurjectiveSteering) | 8 | ok |
| 96 | 2026-10-21T23:37:10Z | FC | S2 /paper/search/match | resolve by title: Lost in Quantization: Activation Outliers Explain Language-Specific FP8 Sensitivity in Llama-3 | 1 | ok |
| 97 | 2026-10-21T23:37:10Z | FC | S2 /paper/arXiv:{id}/citations | forward citations of 64dcc9d3897c7452086243b7e3ed4a8ff2dc4caf (LostInQuantization) | 0 | ok |
| 98 | 2026-10-21T23:40:33Z | FE1 | E6 Claude Code built-in WebSearch (allowed_domains=lesswrong.com, alig | activation quantization steering vector effect | 9 | ok |
| 99 | 2026-10-21T23:40:33Z | FE1 | E6 Claude Code built-in WebSearch (allowed_domains=lesswrong.com, alig | FP8 activation quantization interpretability intervention | 9 | ok |
| 100 | 2026-10-21T23:40:33Z | FE1 | E6 Claude Code built-in WebSearch (allowed_domains=lesswrong.com, alig | quantized model activation patching reproducibility precision | 9 | ok |
| 101 | 2026-10-21T23:40:33Z | FE1 | E6 Claude Code built-in WebSearch (allowed_domains=lesswrong.com, alig | W8A8 INT8 activation steering robustness | 10 | ok |
| 102 | 2026-10-21T23:40:33Z | FE1 | E6 Claude Code built-in WebSearch (allowed_domains=lesswrong.com, alig | numerical precision bf16 fp32 mechanistic interpretability results differ | 8 | ok |
| 103 | 2026-10-21T23:40:33Z | FL1 | E6 Claude Code built-in WebSearch (allowed_domains=lesswrong.com, alig | base model predicts aligned model alternatives after perturbation | 6 | ok |
| 104 | 2026-10-21T23:40:33Z | FL1 | E6 Claude Code built-in WebSearch (allowed_domains=lesswrong.com, alig | post-training preserves base model ranking of candidates | 7 | ok |
| 105 | 2026-10-21T23:40:33Z | FL1 | E6 Claude Code built-in WebSearch (allowed_domains=lesswrong.com, alig | steered or perturbed tuned model reverts to pretraining distribution | 7 | ok |
| 106 | 2026-10-21T23:40:33Z | FL1 | E6 Claude Code built-in WebSearch (allowed_domains=lesswrong.com, alig | token-level distribution shift RL fine-tuning base top-k | 7 | ok |
| 107 | 2026-10-21T23:40:33Z | FE1 | E6 Claude Code built-in WebSearch (allowed_domains=github.com; domain  | activation quantization steering vector effect | 2 | ok |
| 108 | 2026-10-21T23:40:33Z | FE1 | E6 Claude Code built-in WebSearch (allowed_domains=github.com; domain  | FP8 activation quantization interpretability intervention | 5 | ok |
| 109 | 2026-10-21T23:40:33Z | FE1 | E6 Claude Code built-in WebSearch (allowed_domains=github.com; domain  | quantized model activation patching reproducibility precision | 3 | ok |
| 110 | 2026-10-21T23:40:33Z | FE1 | E6 Claude Code built-in WebSearch (allowed_domains=github.com; domain  | W8A8 INT8 activation steering robustness | 4 | ok |
| 111 | 2026-10-21T23:40:33Z | FE1 | E6 Claude Code built-in WebSearch (allowed_domains=github.com; domain  | numerical precision bf16 fp32 mechanistic interpretability results differ | 5 | ok |
| 112 | 2026-10-21T23:40:58Z | FK1 | E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/2027/Confere | proxy tuning emulated fine-tuning diversity | 50 | ok |
| 113 | 2026-10-21T23:46:07Z | SEED-LOOKUP | arXiv API ti: + S2 /paper/search/match | Stable Directions, Different Effects: Intervention Fidelity Across Model Precision | 0 | ok |
| 114 | 2026-10-21T23:46:13Z | SEED-LOOKUP | arXiv API ti: + S2 /paper/search/match | Activation Steering under Low-Bit Quantization: A Geometric Perspective on Degradation and Recovery | 0 | ok |
| 115 | 2026-10-21T23:46:18Z | SEED-LOOKUP | arXiv API ti: + S2 /paper/search/match | Float32-Induced Distortion in Activation Patching: Precision Floors and Displacement-Dependent Endpoint-Curvature Error | 0 | ok |
| 116 | 2026-10-21T23:46:23Z | SEED-LOOKUP | arXiv API ti: + S2 /paper/search/match | Quantization-Induced Decision Changes Have Regime-Dependent Intervention Spectra | 0 | ok |
| 117 | 2026-10-21T23:46:28Z | SEED-LOOKUP | arXiv API ti: + S2 /paper/search/match | Where the Answer Is Born: Causal Interventions on the Information Trajectory of a Quantized Hybrid Language Model | 0 | ok |
| 118 | 2026-10-21T23:50:10Z | R2-FE | E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/2027/Confere | steering compatibility quantized model intervention fidelity precision | 50 | ok |
| 119 | 2026-10-21T23:50:10Z | R2-FE | E3 arXiv API (cs.CL/cs.LG/cs.AI, sortBy=submittedDate desc, max 50) | steering compatibility quantized model intervention fidelity precision | 19 | ok |
| 120 | 2026-10-21T23:50:11Z | R2-FE | E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/2027/Confere | activation patching low precision FP8 circuit discovery quantization | 50 | ok |
| 121 | 2026-10-21T23:50:13Z | R2-FE | E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/2027/Confere | KV cache quantization safety alignment refusal direction steering | 50 | ok |
| 122 | 2026-10-21T23:50:14Z | R2-FE | E3 arXiv API (cs.CL/cs.LG/cs.AI, sortBy=submittedDate desc, max 50) | activation patching low precision FP8 circuit discovery quantization | 50 | ok |
| 123 | 2026-10-21T23:50:14Z | R2-FL | E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/2027/Confere | fine-tuning reversion toward base model helpful-only direction prospective forecast | 50 | ok |
| 124 | 2026-10-21T23:50:14Z | R2-FE | E4 Semantic Scholar API (/paper/search) | steering compatibility quantized model intervention fidelity precision | 6 | ok |
| 125 | 2026-10-21T23:50:15Z | R2-FE | E1 scholarly (OpenAlex/Crossref via aii_fast_web_search.py) | KV cache quantization safety alignment refusal direction steering | 25 | ok |
| 126 | 2026-10-21T23:50:15Z | R2-FE | E1 scholarly (OpenAlex/Crossref via aii_fast_web_search.py) | activation patching low precision FP8 circuit discovery quantization | 12 | ok |
| 127 | 2026-10-21T23:50:15Z | R2-FL | E1 scholarly (OpenAlex/Crossref via aii_fast_web_search.py) | fine-tuning reversion toward base model helpful-only direction prospective forecast | 24 | ok |
| 128 | 2026-10-21T23:50:15Z | R2-FE | E1 scholarly (OpenAlex/Crossref via aii_fast_web_search.py) | steering compatibility quantized model intervention fidelity precision | 25 | ok |
| 129 | 2026-10-21T23:50:15Z | R2-FL | E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/2027/Confere | aligned model rebound elasticity returns to pre-trained distribution under perturbation | 50 | ok |
| 130 | 2026-10-21T23:50:17Z | R2-FS | E5 OpenReview ICLR 2027 pool (notes/search, group=ICLR.cc/2027/Confere | top-two logit margin predicts output flip under perturbation precision temperature | 50 | ok |
| 131 | 2026-10-21T23:50:17Z | R2-FE | E3 arXiv API (cs.CL/cs.LG/cs.AI, sortBy=submittedDate desc, max 50) | KV cache quantization safety alignment refusal direction steering | 4 | ok |
| 132 | 2026-10-21T23:50:18Z | R2-FL | E1 scholarly (OpenAlex/Crossref via aii_fast_web_search.py) | aligned model rebound elasticity returns to pre-trained distribution under perturbation | 25 | ok |
| 133 | 2026-10-21T23:50:18Z | R2-FS | E1 scholarly (OpenAlex/Crossref via aii_fast_web_search.py) | top-two logit margin predicts output flip under perturbation precision temperature | 25 | ok |
| 134 | 2026-10-21T23:50:19Z | R2-FE | E4 Semantic Scholar API (/paper/search) | activation patching low precision FP8 circuit discovery quantization | 0 | ok |
| 135 | 2026-10-21T23:50:23Z | R2-FL | E3 arXiv API (cs.CL/cs.LG/cs.AI, sortBy=submittedDate desc, max 50) | fine-tuning reversion toward base model helpful-only direction prospective forecast | 50 | ok |
| 136 | 2026-10-21T23:50:25Z | R2-FE | E4 Semantic Scholar API (/paper/search) | KV cache quantization safety alignment refusal direction steering | 2 | ok |
| 137 | 2026-10-21T23:50:26Z | R2-FL | E3 arXiv API (cs.CL/cs.LG/cs.AI, sortBy=submittedDate desc, max 50) | aligned model rebound elasticity returns to pre-trained distribution under perturbation | 38 | ok |
| 138 | 2026-10-21T23:50:30Z | R2-FS | E3 arXiv API (cs.CL/cs.LG/cs.AI, sortBy=submittedDate desc, max 50) | top-two logit margin predicts output flip under perturbation precision temperature | 27 | ok |
| 139 | 2026-10-21T23:50:30Z | R2-FL | E4 Semantic Scholar API (/paper/search) | fine-tuning reversion toward base model helpful-only direction prospective forecast | 2 | ok |
| 140 | 2026-10-21T23:50:32Z | R2-FL | E4 Semantic Scholar API (/paper/search) | aligned model rebound elasticity returns to pre-trained distribution under perturbation | 0 | ok |
| 141 | 2026-10-21T23:50:34Z | R2-FS | E4 Semantic Scholar API (/paper/search) | top-two logit margin predicts output flip under perturbation precision temperature | 1 | ok |
| 142 | 2026-10-21T23:53:27Z | FC | S2 /paper/arXiv:{id}/citations | forward citations of arXiv:2510.23264 (PAHQ) | 7 | ok |
| 143 | 2026-10-21T23:53:29Z | FC | S2 /paper/arXiv:{id}/citations | forward citations of arXiv:2606.28525 (GravitationalReversion) | 0 | ok |
| 144 | 2026-10-21T23:53:31Z | FC | S2 /paper/arXiv:{id}/citations | forward citations of arXiv:2507.03662 (ReEmergentMisalignment) | 10 | ok |
| 145 | 2026-10-21T23:53:33Z | FC | S2 /paper/arXiv:{id}/citations | forward citations of arXiv:2609.26621 (GreedyNotPrecisionInvariant) | 1 | ok |
| 146 | 2026-10-21T23:53:35Z | FC | S2 /paper/arXiv:{id}/citations | forward citations of arXiv:2606.09864 (KVCacheAlignmentCollapse) | 6 | ok |
| 147 | 2026-10-21T23:53:41Z | FC | S2 /paper/arXiv:{id}/citations | forward citations of arXiv:2406.06144 (ResistAlignment) | 60 | ok |
| 148 | 2026-10-21T23:53:44Z | BC | S2 /paper/arXiv:{id}/references | backward citations of arXiv:2510.23264 (FLAG_E_2510_23264) | 47 | ok |
| 149 | 2026-10-21T23:53:50Z | BC | S2 /paper/arXiv:{id}/references | backward citations of arXiv:2609.06473 (FLAG_E_2609_06473) | 32 | ok |
| 150 | 2026-10-21T23:53:52Z | BC | S2 /paper/arXiv:{id}/references | backward citations of arXiv:2507.03662 (FLAG_L_2507_03662) | 20 | ok |
| 151 | 2026-10-21T23:53:55Z | BC | S2 /paper/arXiv:{id}/references | backward citations of arXiv:2606.28525 (FLAG_L_2606_28525) | 61 | ok |
| 152 | 2026-10-21T23:56:05Z | FC | S2 /paper/arXiv:{id}/citations | forward citations of arXiv:2610.24346 (PrecisionUpgradeAgents) | 0 | ok |
| 153 | 2026-10-21T23:56:07Z | FC | S2 /paper/arXiv:{id}/citations | forward citations of arXiv:2609.07664 (DivergenceFidelityQuant) | 1 | ok |
| 154 | 2026-10-21T23:56:13Z | FC | S2 /paper/arXiv:{id}/citations | forward citations of arXiv:2607.04510 (PersonaTransplantEM) | 0 | ok |
| 155 | 2026-10-21T23:56:15Z | BC | S2 /paper/arXiv:{id}/references | backward citations of arXiv:2610.24346 (R4_2610_24346) | 38 | ok |
| 156 | 2026-10-22T00:22:25Z | SEED-LOOKUP | Claude Code built-in WebSearch (no domain filter) | "Give Me FP32 or Give Me Death" NeurIPS 2025 oral reproducibility numerical nondeterminism | None | ok |
| 157 | 2026-10-22T00:22:25Z | SEED-LOOKUP | Claude Code built-in WebSearch (no domain filter) | "The Unlocking Spell on Base LLMs" URIAL ICLR 2024 openreview | None | ok |
| 158 | 2026-10-22T00:22:25Z | SEED-LOOKUP | Claude Code built-in WebSearch (no domain filter) | "Forking Paths in Neural Text Generation" ICLR 2025 | None | ok |
| 159 | 2026-10-22T00:22:25Z | SEED-LOOKUP | Claude Code built-in WebSearch (no domain filter) | "Thought Anchors: Which LLM Reasoning Steps Matter" accepted conference | None | ok |
| 160 | 2026-10-22T00:22:25Z | SEED-LOOKUP | Claude Code built-in WebSearch (no domain filter) | "Top-nσ" "Not All Logits Are You Need" ACL 2025 Tang | None | ok |
| 161 | 2026-10-22T00:22:25Z | SEED-LOOKUP | Claude Code built-in WebSearch (no domain filter) | "An Emulator for Fine-Tuning Large Language Models using Small Language Models" ICLR 2024 | None | ok |
| 162 | 2026-10-22T00:25:46Z | SEED-LOOKUP | Claude Code built-in WebSearch (no domain filter) | "intervention fidelity" steering quantized model precision "directions remain" aligned functional sensitivity | None | ok |
| 163 | 2026-10-22T00:25:46Z | SEED-LOOKUP | Claude Code built-in WebSearch (no domain filter) | "steering compatibility" quantized language models output distillation activation steering low-bit | None | ok |
| 164 | 2026-10-22T00:25:46Z | SEED-LOOKUP | Claude Code built-in WebSearch (no domain filter) | activation steering W8A8 FP8 quantized model steering vector effect changes behavioral (mode=extended) | None | ok |

E3 arXiv queries use the `search_query` strings stored in each log record (`arxiv_query`). The raw result lists of every call are in `cache/search_results/` (file name = family_query-tag_engine).

## 4. Pages and PDFs fetched (verification corpus)

| Cache key | URL | PDF | Retrieved (UTC) |
|---|---|---|---|
| 2209.05433v2 | https://arxiv.org/html/2209.05433v2 | False | 2026-10-21T23:35:51Z |
| 2609.06473v1 | https://arxiv.org/html/2609.06473v1 | False | 2026-10-21T23:35:51Z |
| 2211.10438v7 | https://arxiv.org/html/2211.10438v7 | False | 2026-10-21T23:35:51Z |
| 2208.07339v2 | https://arxiv.org/html/2208.07339v2 | False | 2026-10-21T23:35:51Z |
| 2402.17762v2 | https://arxiv.org/html/2402.17762v2 | False | 2026-10-21T23:35:51Z |
| 2506.09501v2 | https://arxiv.org/html/2506.09501v2 | False | 2026-10-21T23:35:51Z |
| 2407.09141v1 | https://arxiv.org/html/2407.09141v1 | False | 2026-10-21T23:35:51Z |
| 2403.15447v3 | https://arxiv.org/html/2403.15447v3 | False | 2026-10-21T23:35:51Z |
| 2609.20722v1 | https://arxiv.org/html/2609.20722v1 | False | 2026-10-21T23:35:51Z |
| 2502.15799v2 | https://arxiv.org/html/2502.15799v2 | False | 2026-10-21T23:35:51Z |
| 2603.22446v1 | https://arxiv.org/html/2603.22446v1 | False | 2026-10-21T23:35:51Z |
| 2507.03662v1 | https://arxiv.org/html/2507.03662v1 | False | 2026-10-21T23:35:51Z |
| 2510.14901v1 | https://arxiv.org/html/2510.14901v1 | False | 2026-10-21T23:35:51Z |
| 2605.18309v1 | https://arxiv.org/html/2605.18309v1 | False | 2026-10-21T23:35:51Z |
| 2401.17256v5 | https://arxiv.org/html/2401.17256v5 | False | 2026-10-21T23:35:51Z |
| 2402.12343v4 | https://arxiv.org/html/2402.12343v4 | False | 2026-10-21T23:35:51Z |
| 2406.06144v6 | https://arxiv.org/html/2406.06144v6 | False | 2026-10-21T23:35:52Z |
| 2412.07961v1 | https://arxiv.org/html/2412.07961v1 | False | 2026-10-21T23:35:52Z |
| 2410.09300v4 | https://arxiv.org/html/2410.09300v4 | False | 2026-10-21T23:35:52Z |
| 2506.19143v4 | https://arxiv.org/html/2506.19143v4 | False | 2026-10-21T23:35:52Z |
| 2608.19611v1 | https://arxiv.org/html/2608.19611v1 | False | 2026-10-21T23:35:52Z |
| 2506.01939v2 | https://arxiv.org/html/2506.01939v2 | False | 2026-10-21T23:35:52Z |
| 2411.19943v3 | https://arxiv.org/html/2411.19943v3 | False | 2026-10-21T23:35:52Z |
| 2402.05201v3 | https://arxiv.org/html/2402.05201v3 | False | 2026-10-21T23:35:52Z |
| 2411.07641v1 | https://arxiv.org/html/2411.07641v1 | False | 2026-10-21T23:35:52Z |
| 2309.06256v4 | https://arxiv.org/html/2309.06256v4 | False | 2026-10-21T23:35:52Z |
| 2604.09839v2 | https://arxiv.org/html/2604.09839v2 | False | 2026-10-21T23:35:52Z |
| 2312.01552v1 | https://arxiv.org/html/2312.01552v1 | False | 2026-10-21T23:35:52Z |
| 2109.01903v3 | https://arxiv.org/html/2109.01903v3 | False | 2026-10-21T23:35:52Z |
| tm_nondeterminism | https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/ | False | 2026-10-21T23:38:44Z |
| hf_qwen3_8b_fp8 | https://huggingface.co/Qwen/Qwen3-8B-FP8 | False | 2026-10-21T23:38:44Z |
| propor2026_108_page | https://aclanthology.org/2026.propor-1.108/ | False | 2026-10-21T23:38:44Z |
| propor2026_108_pdf | https://aclanthology.org/2026.propor-1.108.pdf | True | 2026-10-21T23:38:44Z |
| neurips2026_poster_151909 | https://neurips.cc/virtual/2026/poster/151909 | False | 2026-10-21T23:38:45Z |
| 2608.24988v2 | https://arxiv.org/html/2608.24988v2 | False | 2026-10-21T23:40:47Z |
| 2510.23264v1 | https://arxiv.org/html/2510.23264v1 | False | 2026-10-21T23:40:47Z |
| 2608.29118v1 | https://arxiv.org/html/2608.29118v1 | False | 2026-10-21T23:40:47Z |
| 2605.10781v1 | https://arxiv.org/html/2605.10781v1 | False | 2026-10-21T23:40:47Z |
| 2606.28525v2 | https://arxiv.org/html/2606.28525v2 | False | 2026-10-21T23:40:47Z |
| 2510.16167v1 | https://arxiv.org/html/2510.16167v1 | False | 2026-10-21T23:40:47Z |
| 2609.26621v1 | https://arxiv.org/pdf/2609.26621v1 | True | 2026-10-21T23:40:48Z |
| 2605.30218v1 | https://arxiv.org/html/2605.30218v1 | False | 2026-10-21T23:49:17Z |
| 2602.02427v4 | https://arxiv.org/html/2602.02427v4 | False | 2026-10-21T23:49:17Z |
| 2608.29188v1 | https://arxiv.org/html/2608.29188v1 | False | 2026-10-21T23:49:17Z |
| 2605.17026v2 | https://arxiv.org/html/2605.17026v2 | False | 2026-10-21T23:49:17Z |
| 2609.04748v2 | https://arxiv.org/html/2609.04748v2 | False | 2026-10-21T23:49:17Z |
| 2608.13756v2 | https://arxiv.org/html/2608.13756v2 | False | 2026-10-21T23:49:17Z |
| 2606.25524v3 | https://arxiv.org/html/2606.25524v3 | False | 2026-10-21T23:49:17Z |
| 2607.21356v1 | https://arxiv.org/html/2607.21356v1 | False | 2026-10-21T23:49:17Z |
| 2606.09864v2 | https://arxiv.org/pdf/2606.09864v2 | True | 2026-10-21T23:49:17Z |
| vllm_fp8_w8a8_docs | https://docs.vllm.ai/en/stable/features/quantization/llm_compressor/fp8/ | False | 2026-10-21T23:52:36Z |
| 2603.06957v2 | https://arxiv.org/html/2603.06957v2 | False | 2026-10-21T23:52:52Z |
| 2610.20808v1 | https://arxiv.org/html/2610.20808v1 | False | 2026-10-21T23:52:52Z |
| or_8iTqrW1sxY | https://api2.openreview.net/notes/search?term=Stable%20Directions%2C%20Different%20Effects%3A%20Intervention%20Fidelity%20Across%20Model%20P | False | 2026-10-21T23:54:36Z |
| or_h57duZqLOr | https://api2.openreview.net/notes/search?term=Activation%20Steering%20under%20Low-Bit%20Quantization%3A%20A%20Geometric%20Perspective%20on%2 | False | 2026-10-21T23:54:38Z |
| or_6t1egKiB0v | https://api2.openreview.net/notes/search?term=Quantization-Induced%20Decision%20Changes%20Have%20Regime-Dependent%20Intervention%20Spectra&g | False | 2026-10-21T23:54:40Z |
| or_ooV5M72O08 | https://api2.openreview.net/notes/search?term=Same%20Candidates%2C%20Stronger%20Reasoning%3A%20Rethinking%20What%20Post-Training%20Learns&gr | False | 2026-10-21T23:54:41Z |
| or_knirOusGcq | https://api2.openreview.net/notes/search?term=Before%20the%20First%20Token%3A%20A%20Shared%20Causal%20Subspace%20for%20Response-Length%20Pla | False | 2026-10-21T23:54:43Z |
| or_BEcwcRFQdu | https://api2.openreview.net/notes/search?term=Predictive%20Mechanistic%20Interpretability%20of%20Post-Training%3A%20A%20Priori%20Forecasts%2 | False | 2026-10-21T23:54:45Z |
| or_xmDdTDx241 | https://api2.openreview.net/notes/search?term=AlignRadar%3A%20Forecasting%20Emergent-Misalignment%20Risk%20Before%20Fine-Tuning&group=ICLR.c | False | 2026-10-21T23:54:47Z |
| or_GYm4mg9yGQ | https://api2.openreview.net/notes/search?term=When%20Quantization%20Helps%3A%20Corrective%20Computation%20in%20Low-Bit%20Language%20Models&g | False | 2026-10-21T23:54:48Z |
| or_MYXgOex05m | https://api2.openreview.net/notes/search?term=Should%20SFT%20Prefer%20the%20Familiar%3F%20Diversity%20Collapse%20and%20Recovery%20via%20Mode | False | 2026-10-21T23:54:50Z |
| or_5R8LqE51Hr | https://api2.openreview.net/notes/search?term=Better%20Fixed-State%20Fidelity%20Need%20Not%20Improve%20Closed-Loop%20Performance%20in%20Quan | False | 2026-10-21T23:54:52Z |
| s2_computation14090212 | https://api.semanticscholar.org/graph/v1/paper/DOI:10.3390/computation14090212?fields=title,abstract,venue,publicationDate,authors,externalI | False | 2026-10-21T23:55:43Z |
| abs_2610.07853 | https://arxiv.org/abs/2610.07853 | False | 2026-10-21T23:57:45Z |
| abs_2609.09793 | https://arxiv.org/abs/2609.09793 | False | 2026-10-21T23:57:45Z |
| abs_2610.24346 | https://arxiv.org/abs/2610.24346 | False | 2026-10-21T23:57:45Z |
| venue_eft_iclr2024 | https://proceedings.iclr.cc/paper_files/paper/2024/hash/389e161125965c0f0ba50420fee45774-Abstract-Conference.html | False | 2026-10-21T23:57:46Z |
| venue_topnsigma_acl2025 | https://aclanthology.org/2025.acl-long.528/ | False | 2026-10-21T23:57:46Z |
| venue_urial_iclr2024 | https://iclr.cc/virtual/2024/poster/17473 | False | 2026-10-21T23:57:46Z |
| venue_forkingpaths_iclr2025 | https://iclr.cc/virtual/2025/poster/30769 | False | 2026-10-21T23:57:46Z |
| venue_givemefp32_neurips2025 | https://neurips.cc/virtual/2025/oral/118170 | False | 2026-10-21T23:57:47Z |
| 2411.02355v4 | https://arxiv.org/html/2411.02355v4 | False | 2026-10-22T00:25:13Z |
| 2604.14090v1 | https://arxiv.org/html/2604.14090v1 | False | 2026-10-22T00:25:13Z |

Fetch failures, logged in `logs/` and section 6 of the report: OpenReview PDFs (8iTqrW1sxY, h57duZqLOr, 6t1egKiB0v, ooV5M72O08, knirOusGcq) returned HTTP 403; the OpenReview notes?id= endpoint returned 403 ChallengeRequiredError; mdpi.com (Computation 14(9) 212) returned 403; the vLLM `latest` FP8 docs URL returned a 73-character stub, so the `stable` URL was used.

## 5. Verification steps and outcomes

1. `tools/build_quotes_iter6.py` checks every new quote against its cached versioned text, using the inherited normalisation (whitespace, ligatures, curly quotes, dashes, PDF line-end hyphenation, markdown emphasis). Result: 84 quote records, all matched (`evidence/quotes_iter6.jsonl`; status UNVERIFIED would be written for a miss).
2. `tools/qa_second_pass_iter6.py` runs an independent live fetch_grep on each quote URL with up to 5 six-token regex windows. Result: 84/84 re-matched (`evidence/qa_second_pass_iter6.jsonl`).
3. `tools/check_passages_live_iter6.py` re-fetches every source URL and requires each supporting passage of the structured output to occur literally (whitespace-collapsed). Result: 64/64 kept (`evidence/passages_live_check_iter6.jsonl`). Three passages, taken from the table quotes, failed this literal check because of markup or JSON escapes. They were replaced by verbatim strings from the same pages (TL;DR field; backtick-quoted sentence; post-emphasis clause).
4. `tools/write_scores_iter6.py` scores hits on the frozen O/I/C rubric and writes the flags and corrections. `tools/counts_iter6.py` writes the counts and the same-agent re-screen: n = 54, observed agreement 0.981, Cohen's kappa 0.791.
5. `tools/render_report_iter6.py` renders `research_report.md` (with Table 92e) and `cache/sources_iter6.json`. The structured output's answer is the report text and its sources are that list.

## 6. How to retrace (same order)

```bash
PY=$(bash tools/skill_py.sh)            # aii-web-tools interpreter
export SEMANTIC_SCHOLAR_API_KEY=...      # optional; anonymous S2 calls are rate-limited
python3 -I tools/build_row_index_iter6.py
$PY -I tools/write_protocol_iter6.py      # refuses to overwrite the frozen protocol
$PY -I tools/sat_search_iter6.py          # round 1 (+ forward citations) -> evidence/saturation_candidates_iter6.jsonl
$PY -I tools/log_e6_iter6.py              # E6 calls (re-run them with WebSearch to refresh; results drift)
$PY -I tools/retry_failed_iter6.py
$PY -I tools/sat_search_iter6.py --round2 evidence/round2_queries_iter6.json
$PY -I tools/round3_citations_iter6.py && $PY -I tools/round4_citations_iter6.py
$PY -I tools/arxiv_meta.py <ids>  &&  $PY -I tools/fetch_texts.py <ids>   # seeds; --url KEY URL for other pages
$PY -I tools/fetch_openreview_iter6.py 8iTqrW1sxY h57duZqLOr 6t1egKiB0v ooV5M72O08 knirOusGcq BEcwcRFQdu xmDdTDx241 GYm4mg9yGQ MYXgOex05m 5R8LqE51Hr
$PY -I tools/build_quotes_iter6.py && $PY -I tools/qa_second_pass_iter6.py
$PY -I tools/write_scores_iter6.py && $PY -I tools/counts_iter6.py
$PY -I tools/render_report_iter6.py && $PY -I tools/check_passages_live_iter6.py && $PY -I tools/write_repro_iter6.py
```

Search results drift: arXiv, Semantic Scholar and OpenReview add records daily, and ICLR 2027 records may change venue status. A re-run will reproduce the method and the verified quotes, but not the exact hit counts. The cached texts in `cache/` (kept on the run volume, not published) are the exact versions the quotes were checked against.

## 7. Deviations from the plan

- **Stop rule.** The search stopped after round 4 by a logged deviation: rounds 3 and 4 still added hits scoring 1.5, all in the weight-only 'flat score hides behavioural damage' context sub-lane. The 60-minute cap was not reached (about 21 minutes of logged search time).
- **OpenReview.** OpenReview records came from notes/search because notes?id= and PDFs returned 403. The ICLR 2027 rows are therefore VERIFIED-ABSTRACT only.
- **Screening.** One agent screened everything. The re-screen is a same-agent consistency check written minutes after the first pass, so it does not measure independent agreement.
- **Claim wording.** Claim statements come from the artifact plan; the iteration-6 hypothesis text was not available to this executor.
- **Venue lookups.** Six WebSearch venue lookups and five title-resolution calls (arXiv ti: + S2 match) are logged as SEED-LOOKUP and not counted in the saturation totals.