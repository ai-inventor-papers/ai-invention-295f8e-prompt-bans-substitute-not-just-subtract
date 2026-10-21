# Reproducibility: how this research was actually conducted

Session date: **2026-10-21**, roughly 06:55-07:55 UTC. The executor was Claude Code (Opus 5.5). Everything was run from this workspace. Searches and fetches went through the `aii-web-tools` skill and Claude Code's built-in WebSearch:
- `scripts/aii_fast_web_search.py --mode scholarly`, which queries OpenAlex and Crossref.
- `scripts/aii_fast_web_fetch.py`, whose fetch core `_fetch_url` (html2text + PyMuPDF) was imported by `tools/common.py`, and whose `grep` CLI was used for the QA pass.
- Claude Code's built-in WebSearch (standard mode), which the skill says to prefer for general web search.

No LLM API calls and no OpenRouter spend.

## Environment variables (names only)

- `SEMANTIC_SCHOLAR_API_KEY`: sent as the `x-api-key` header to the Semantic Scholar Graph API (search and citations). Present in the environment.
- `SERPER_API_KEY`: present. It is used by the skill's search script only as a paid fallback when its free engines miss. All scholarly calls reported `[scholarly via openalex]`.

## Order of work (what was actually done)

1. Loaded the `aii-web-tools` skill and the mechanistic-interpretability handbook. `user_uploads/` was empty.
2. **Metadata.** One arXiv API `id_list` call for the 54 planned IDs (`tools/arxiv_meta.py`), and later calls for 51 more candidate IDs. One later metadata call hit HTTP 429 and was retried after the search finished. Output: `evidence/arxiv_meta.json`.
3. **Full texts.** `tools/fetch_texts.py` cached the latest version of each paper, trying `https://arxiv.org/html/<id>v<N>` first and falling back to `https://arxiv.org/pdf/<id>v<N>`. Only 2604.03380v2 and 2604.07192v2 needed the PDF. Earlier versions were fetched where version-dependent numbers or wording were at stake.
4. **Row-by-row grep.** `tools/grep_cache.py --spec cache/spec_<row>.json` ran for rows b1-b3, b4-b5, b6-b7, c1, c2, c3, c4, c5-c8, the version checks, venue pages, flags and new hits. Its windowing is the same as the skill's `fetch_grep`.
5. **Venue and policy checks.** Built-in WebSearch was used for discovery, then each venue page was fetched and grepped: ACL Anthology, iclr.cc posters and awards blog, icml.cc 2025/2026 pages, neurips.cc 2026, the ICLR 2027 Reviewer Guide and Dates pages, the ICLR 2025 FAQ, the OpenReview API, and the Nature article page.
6. **Saturation search** (`tools/sat_search.py`): 25 queries in 8 families on engines E1, E3, E4 and E5, plus forward citations.
   - E3 (export.arxiv.org) first failed with HTTP 429 (logged as `retry:ParseError`). A logged fallback to arxiv.org/search was tried and mostly returned HTTP 500/429; it was stopped. The export-API job, with 20-100 s backoff, then completed all 25 queries. One empty query (S1 q0) was re-run alone.
   - All raw responses are in `cache/search_results/`. `--aggregate` de-duplicates them into `evidence/saturation_candidates.jsonl`.
7. **E2 general web.** 28 built-in WebSearch calls (family phrasings and record lookups), logged after the fact with result counts but without exact times.
8. **Screening** (`tools/screen.py`):
   - Window rule: an arXiv ID prefix of 26xx, a 2026 date, or an ICLR 2027 submission.
   - Keyword pre-screen: 7 title/abstract keyword groups, plus an LLM-domain filter.
   - Manual title screen of the 497 domain-passing records, then a manual abstract screen of about 70 flagged records.
   - Full-text or OpenReview-abstract checks of the closest hits.
9. **Quotes** (`tools/build_quotes.py`): 112 quotes, every one matched in order against the normalised cached text. A second pass (`tools/qa_second_pass.py`) re-fetched each URL live through the skill's `fetch_grep` CLI: 111/112 matched at first, and the last one (a PDF hyphenation split) matched on a targeted span.
10. **Scoring and report** (`tools/write_evidence.py`, `tools/render_report.py`).
11. **Supporting passages (after a verification round).** The output verifier rejected 8 passages. They spanned html2text markup that appears in the fetched text: emphasis such as `_priming failure_` and `_branch_ ,`, and link syntax `[workshop name](/virtual/...)` on the icml.cc and neurips.cc pages. Passages are now the longest span of each verified quote that occurs literally, with whitespace collapsing only, in the fetched text. `tools/check_passages_live.py` then re-fetched every source URL live and kept 98/98 passages (`evidence/passages_live_check.jsonl`). The quotes in the report tables are unchanged. They were verified with the plan's normalisation rule, which strips that markup.

## Engines used (calls logged in `evidence/search_log.jsonl`)

- E3 arXiv API: 31 calls
- E2 general web: 28 calls
- E1 scholarly: 25 calls
- E4 Semantic Scholar API: 25 calls
- E3 arXiv web search: 21 calls
- E5 OpenReview ICLR 2027 pool: 11 calls
- E4 Semantic Scholar citations API: 6 calls

## Saturation queries (in the order run; each on E1, E3 and E4; E5 for S1, S3 and S4; extra E2 phrasings below)

| family | query |
|---|---|
| S1 | activation steering diversity code generation |
| S1 | hidden state noise injection solution diversity |
| S1 | residual stream noise diversity reasoning strategies |
| S1 | latent perturbation exploration pass@k |
| S3 | predict instruction compliance from hidden states |
| S3 | steerability prediction hidden states |
| S3 | negative constraint compliance internal representation |
| S3 | perturbation sensitivity predicts prompt compliance |
| S4 | algorithm choice hidden states code LLM probe |
| S4 | latent planning code generation prompt representations |
| S4 | response planning prompt hidden states |
| S2 | where to inject diversity language model layer |
| S2 | noise injection layer comparison generation diversity |
| S2 | prefill perturbation versus temperature diversity |
| S5 | temperature semantic diversity ideas not wording |
| S5 | token-level diversity paraphrases same solution |
| S5 | idea-level diversity sampling LLM |
| S6 | algorithmic diversity code LLM benchmark |
| S6 | mode collapse code solutions |
| S6 | algorithm selection bias code generation |
| S7 | negative instruction mechanism LLM alternative |
| S7 | do not use X prompt code model |
| S7 | negation suppression promotion LLM |
| S8 | LLM novel algorithm discovery evaluation |
| S8 | novel algorithm correctness novelty judge LLM |
| S5 | Gumbel counterfactual generation language models shared noise same sampling seed intervention Ravfogel |
| S5 | common random numbers coupled sampling LLM temperature same seed semantic diversity vs phrasing |
| S1 | activation steering algorithmic diversity code generation test-checked solutions 2026 arXiv |
| S2 | comparing noise injection sites layers token positions language model output diversity 2026 |
| S3 | predicting prompt instruction compliance from activation steerability or perturbation sensitivity LLM 2026 |
| S4 | probing hidden states predicts algorithm choice before code generation LLM 2026 |
| S5 | temperature sampling changes wording not ideas LLM semantic diversity code solutions 2026 |
| S6 | LLM code generation algorithmic monoculture default algorithm bias benchmark 2026 |
| S7 | "do not use" negative instruction LLM falls back to default alternative mechanism 2026 |
| S8 | do LLMs invent novel algorithms evaluation novelty of correct generated code versus known solutions 2026 |
| S3 | "Probing and Steering Prompt Injection Compliance" arXiv |
| S6 | "How Diversely Can Language Models Solve Problems" algorithmic diversity model-generated code arXiv |
| S2 | "Roll the dice" "look before you leap" seed-conditioning creative limits next-token prediction arXiv 2504.15266 |
| S8 | LLM agents creativity ML engineering H-creativity medal-winning humans lower performance arXiv 2026 |
| S1 | steering random direction versus learned direction changes which solution strategy LLM reasoning diversity 2026 arXiv |
| S7 | why LLMs fail negative constraints prohibition code generation default implementation mechanism 2026 arXiv |

Forward citations (Semantic Scholar `/paper/arXiv:<id>/citations`) were pulled for STARS 2601.22010, Noise Steering 2604.03380, ASTEER 2606.11599, 2606.10302, REI 2605.11936 and Emergent Response Planning 2502.06258. This gave 35 citing records in total.

## Pages and PDFs fetched (from `cache/index.jsonl`; UTC time on 2026-10-21)

| time | cache key | URL | type | chars |
|---|---|---|---|---|
| 06:58:13 | `2309.02772v3` | https://arxiv.org/html/2309.02772v3 | HTML/JSON | 46139 |
| 06:58:13 | `2605.07984v2` | https://arxiv.org/html/2605.07984v2 | HTML/JSON | 49131 |
| 06:58:13 | `2404.00859v2` | https://arxiv.org/html/2404.00859v2 | HTML/JSON | 81886 |
| 06:58:13 | `2502.11027v5` | https://arxiv.org/html/2502.11027v5 | HTML/JSON | 138473 |
| 06:58:14 | `2310.15916v1` | https://arxiv.org/html/2310.15916v1 | HTML/JSON | 43990 |
| 06:58:14 | `2407.09007v2` | https://arxiv.org/html/2407.09007v2 | HTML/JSON | 72839 |
| 06:58:14 | `2610.09571v2` | https://arxiv.org/html/2610.09571v2 | HTML/JSON | 158758 |
| 06:58:14 | `2606.17648v3` | https://arxiv.org/html/2606.17648v3 | HTML/JSON | 136799 |
| 06:58:14 | `2505.18949v1` | https://arxiv.org/html/2505.18949v1 | HTML/JSON | 57247 |
| 06:58:14 | `2604.03380v2` | https://arxiv.org/pdf/2604.03380v2 | PDF | 58767 |
| 06:58:14 | `2506.09659v1` | https://arxiv.org/html/2506.09659v1 | HTML/JSON | 279841 |
| 06:58:15 | `2310.11324v2` | https://arxiv.org/html/2310.11324v2 | HTML/JSON | 102407 |
| 06:58:15 | `2310.15213v2` | https://arxiv.org/html/2310.15213v2 | HTML/JSON | 140111 |
| 06:58:15 | `2407.02209v1` | https://arxiv.org/html/2407.02209v1 | HTML/JSON | 97694 |
| 06:58:15 | `2605.11936v2` | https://arxiv.org/html/2605.11936v2 | HTML/JSON | 115805 |
| 06:58:15 | `2606.11599v1` | https://arxiv.org/html/2606.11599v1 | HTML/JSON | 75889 |
| 06:58:15 | `2606.04057v1` | https://arxiv.org/html/2606.04057v1 | HTML/JSON | 78546 |
| 06:58:15 | `2601.08070v1` | https://arxiv.org/html/2601.08070v1 | HTML/JSON | 42520 |
| 06:58:15 | `2606.21619v1` | https://arxiv.org/html/2606.21619v1 | HTML/JSON | 88442 |
| 06:58:15 | `2409.03733v2` | https://arxiv.org/html/2409.03733v2 | HTML/JSON | 89951 |
| 06:58:15 | `2606.14530v3` | https://arxiv.org/html/2606.14530v3 | HTML/JSON | 25159 |
| 06:58:15 | `2609.00077v1` | https://arxiv.org/html/2609.00077v1 | HTML/JSON | 98781 |
| 06:58:16 | `2610.19157v1` | https://arxiv.org/html/2610.19157v1 | HTML/JSON | 77370 |
| 06:58:16 | `2406.05946v1` | https://arxiv.org/html/2406.05946v1 | HTML/JSON | 119373 |
| 06:58:16 | `2410.14516v5` | https://arxiv.org/html/2410.14516v5 | HTML/JSON | 77022 |
| 06:58:16 | `2607.05188v1` | https://arxiv.org/html/2607.05188v1 | HTML/JSON | 70431 |
| 06:58:16 | `2608.12321v1` | https://arxiv.org/html/2608.12321v1 | HTML/JSON | 69485 |
| 06:58:16 | `2405.21047v4` | https://arxiv.org/html/2405.21047v4 | HTML/JSON | 88202 |
| 06:58:16 | `2311.04897v1` | https://arxiv.org/html/2311.04897v1 | HTML/JSON | 49814 |
| 06:58:16 | `2404.02151v4` | https://arxiv.org/html/2404.02151v4 | HTML/JSON | 108425 |
| 06:58:16 | `2502.06258v3` | https://arxiv.org/html/2502.06258v3 | HTML/JSON | 64789 |
| 06:58:16 | `2504.05228v4` | https://arxiv.org/html/2504.05228v4 | HTML/JSON | 55730 |
| 06:58:16 | `2606.10302v1` | https://arxiv.org/html/2606.10302v1 | HTML/JSON | 90099 |
| 06:58:16 | `2405.00492v1` | https://arxiv.org/html/2405.00492v1 | HTML/JSON | 63244 |
| 06:58:17 | `2603.18353v1` | https://arxiv.org/html/2603.18353v1 | HTML/JSON | 70146 |
| 06:58:17 | `2604.27251v3` | https://arxiv.org/html/2604.27251v3 | HTML/JSON | 70669 |
| 06:58:17 | `2601.22010v1` | https://arxiv.org/html/2601.22010v1 | HTML/JSON | 125033 |
| 06:58:17 | `2605.08221v1` | https://arxiv.org/html/2605.08221v1 | HTML/JSON | 74520 |
| 06:58:17 | `2604.09839v2` | https://arxiv.org/html/2604.09839v2 | HTML/JSON | 95373 |
| 06:58:17 | `2511.08305v1` | https://arxiv.org/html/2511.08305v1 | HTML/JSON | 89752 |
| 06:58:18 | `2606.15092v1` | https://arxiv.org/html/2606.15092v1 | HTML/JSON | 119515 |
| 06:58:18 | `2604.01639v1` | https://arxiv.org/html/2604.01639v1 | HTML/JSON | 34076 |
| 06:58:18 | `2605.28664v1` | https://arxiv.org/html/2605.28664v1 | HTML/JSON | 118633 |
| 06:58:18 | `2507.13874v2` | https://arxiv.org/html/2507.13874v2 | HTML/JSON | 59065 |
| 06:58:18 | `2506.13131v1` | https://arxiv.org/html/2506.13131v1 | HTML/JSON | 152434 |
| 06:58:18 | `2602.04297v1` | https://arxiv.org/html/2602.04297v1 | HTML/JSON | 77313 |
| 06:58:18 | `2603.23629v2` | https://arxiv.org/html/2603.23629v2 | HTML/JSON | 22442 |
| 06:58:18 | `2608.07852v2` | https://arxiv.org/html/2608.07852v2 | HTML/JSON | 157154 |
| 06:58:18 | `2605.05115v1` | https://arxiv.org/html/2605.05115v1 | HTML/JSON | 136162 |
| 06:58:18 | `2605.03052v2` | https://arxiv.org/html/2605.03052v2 | HTML/JSON | 84739 |
| 06:58:18 | `2604.18389v1` | https://arxiv.org/html/2604.18389v1 | HTML/JSON | 90520 |
| 06:58:18 | `2605.30789v3` | https://arxiv.org/html/2605.30789v3 | HTML/JSON | 74581 |
| 06:58:19 | `2607.05615v2` | https://arxiv.org/html/2607.05615v2 | HTML/JSON | 65071 |
| 06:58:19 | `2604.07192v2` | https://arxiv.org/pdf/2604.07192v2 | PDF | 66745 |
| 07:01:46 | `2604.03380v1` | https://arxiv.org/html/2604.03380v1 | HTML/JSON | 64609 |
| 07:01:46 | `2606.14530v2` | https://arxiv.org/html/2606.14530v2 | HTML/JSON | 43577 |
| 07:01:47 | `2610.09571v1` | https://arxiv.org/html/2610.09571v1 | HTML/JSON | 158721 |
| 07:01:47 | `2606.14530v1` | https://arxiv.org/html/2606.14530v1 | HTML/JSON | 43833 |
| 07:01:47 | `2606.17648v2` | https://arxiv.org/html/2606.17648v2 | HTML/JSON | 132651 |
| 07:01:47 | `2605.11936v1` | https://arxiv.org/html/2605.11936v1 | HTML/JSON | 115805 |
| 07:01:47 | `2604.27251v1` | https://arxiv.org/html/2604.27251v1 | HTML/JSON | 61186 |
| 07:01:47 | `2605.07984v1` | https://arxiv.org/html/2605.07984v1 | HTML/JSON | 49255 |
| 07:01:47 | `2606.17648v1` | https://arxiv.org/html/2606.17648v1 | HTML/JSON | 227027 |
| 07:01:48 | `2604.07192v1` | https://arxiv.org/pdf/2604.07192v1 | PDF | 58044 |
| 07:01:50 | `funsearch_nature` | https://www.nature.com/articles/s41586-023-06924-6 | HTML/JSON | 123131 |
| 07:03:33 | `venue_or_noveltybench` | https://api2.openreview.net/notes/search?term=NoveltyBench&limit=10 | HTML/JSON | 66824 |
| 07:03:33 | `venue_acl_neocoder` | https://aclanthology.org/2025.naacl-long.141/ | HTML/JSON | 18790 |
| 07:03:33 | `venue_iclr25_awards` | https://blog.iclr.cc/2025/04/22/announcing-the-outstanding-paper-awards-at-iclr-2025/ | HTML/JSON | 5520 |
| 07:03:33 | `venue_iclr25_gumbel` | https://proceedings.iclr.cc/paper_files/paper/2025/hash/e15790966a4a9d85d688635c88ee6d8a-Abstract-Conference.html | HTML/JSON | 2608 |
| 07:03:33 | `policy_iclr25_faq` | https://iclr.cc/Conferences/2025/FAQ | HTML/JSON | 9109 |
| 07:03:33 | `venue_iclr25_monoculture` | https://iclr.cc/virtual/2025/poster/27717 | HTML/JSON | 4853 |
| 07:03:33 | `venue_iclr25_qi` | https://proceedings.iclr.cc/paper_files/paper/2025/hash/88be023075a5a3ff3dc3b5d26623fa22-Abstract-Conference.html | HTML/JSON | 2506 |
| 07:03:33 | `venue_icml25_ifg` | https://icml.cc/virtual/2025/51482 | HTML/JSON | 6161 |
| 07:03:33 | `venue_icml26_rei` | https://icml.cc/virtual/2026/79614 | HTML/JSON | 5745 |
| 07:03:33 | `policy_iclr27_reviewer` | https://www.iclr.cc/Conferences/2027/ReviewerGuidelines | HTML/JSON | 27154 |
| 07:03:33 | `venue_iclr25_heo` | https://iclr.cc/virtual/2025/poster/28257 | HTML/JSON | 5355 |
| 07:03:33 | `venue_iclr25_plansearch` | https://iclr.cc/virtual/2025/poster/31034 | HTML/JSON | 5280 |
| 07:03:33 | `venue_icml26_manifold` | https://icml.cc/virtual/2026/79460 | HTML/JSON | 6070 |
| 07:03:33 | `venue_icml26_lottery` | https://icml.cc/virtual/2026/poster/64782 | HTML/JSON | 6389 |
| 07:04:36 | `policy_iclr27_dates` | https://iclr.cc/Conferences/2027/Dates | HTML/JSON | 4087 |
| 07:09:51 | `venue_neurips26_injection` | https://neurips.cc/virtual/2026/168286 | HTML/JSON | 6584 |
| 07:24:47 | `new_2503.00691` | https://arxiv.org/html/2503.00691 | HTML/JSON | 74510 |
| 07:24:49 | `new_2504.15266` | https://arxiv.org/html/2504.15266 | HTML/JSON | 142322 |
| 07:24:50 | `new_2608.30047` | https://arxiv.org/html/2608.30047 | HTML/JSON | 117447 |
| 07:24:52 | `new_2507.06463` | https://arxiv.org/html/2507.06463 | HTML/JSON | 39885 |
| 07:24:55 | `new_2511.08522` | https://arxiv.org/html/2511.08522 | HTML/JSON | 45031 |
| 07:24:57 | `new_2411.07180` | https://arxiv.org/html/2411.07180 | HTML/JSON | 127729 |
| 07:25:53 | `venue_acl_lee2025` | https://aclanthology.org/2025.findings-emnlp.10/ | HTML/JSON | 19409 |
| 07:25:56 | `venue_icml25_seedcond` | https://icml.cc/virtual/2025/poster/45769 | HTML/JSON | 7497 |
| 07:32:23 | `2607.10296v1` | https://arxiv.org/html/2607.10296v1 | HTML/JSON | 47918 |
| 07:32:23 | `2609.14151v1` | https://arxiv.org/html/2609.14151v1 | HTML/JSON | 68311 |
| 07:32:23 | `2608.21595v1` | https://arxiv.org/html/2608.21595v1 | HTML/JSON | 64991 |
| 07:32:23 | `2610.02438v1` | https://arxiv.org/html/2610.02438v1 | HTML/JSON | 82606 |
| 07:32:23 | `2608.30345v1` | https://arxiv.org/html/2608.30345v1 | HTML/JSON | 67353 |
| 07:32:23 | `2606.24952v1` | https://arxiv.org/html/2606.24952v1 | HTML/JSON | 64440 |
| 07:32:23 | `2610.01382v1` | https://arxiv.org/html/2610.01382v1 | HTML/JSON | 107309 |
| 07:32:23 | `2604.24927v2` | https://arxiv.org/html/2604.24927v2 | HTML/JSON | 101553 |
| 07:32:44 | `2607.13077v3` | https://arxiv.org/pdf/2607.13077v3 | PDF | 70568 |
| 07:32:45 | `or_wJ8HkA8vGN` | https://api2.openreview.net/notes/search?term=Diversity%20Without%20Discovery%3A%20Why%20Chain%20Perturbation%20Fails%20to%20Explore%20in%20Latent%20Test-Time%20Scaling&group=ICLR.cc/2027/Conference&limit=10 | HTML/JSON | 1802 |
| 07:32:46 | `or_knirOusGcq` | https://api2.openreview.net/notes/search?term=Before%20the%20First%20Token%3A%20A%20Shared%20Causal%20Subspace%20for%20Response-Length%20Planning%20in%20LLMs&group=ICLR.cc/2027/Conference&limit=10 | HTML/JSON | 1992 |
| 07:32:46 | `or_Dl1xo5fqnj` | https://api2.openreview.net/notes/search?term=AJR%3A%20Amortized%20Jacobian%20Readouts%20for%20Prompt-Adaptive%20Steering&group=ICLR.cc/2027/Conference&limit=10 | HTML/JSON | 1521 |
| 07:32:46 | `or_oag3wgNLRh` | https://api2.openreview.net/notes/search?term=Rethinking%20Activation%20Steering%20for%20Mathematical%20Reasoning&group=ICLR.cc/2027/Conference&limit=10 | HTML/JSON | 1932 |
| 07:32:46 | `or_tZaHwMrvq2` | https://api2.openreview.net/notes/search?term=Where%20Do%20LLMs%20Decide%20to%20Break%20the%20Rules%3F%20Mechanistic%20Localization%20of%20Prompt%20Injection%20Compliance&group=ICLR.cc/2027/Conference&limit=10 | HTML/JSON | 1587 |
| 07:32:47 | `or_L09agUoh7d` | https://api2.openreview.net/notes/search?term=Silent%20Compliance%3A%20Separating%20Constraint%20Echoing%20from%20Instruction%20Following&group=ICLR.cc/2027/Conference&limit=10 | HTML/JSON | 1619 |
| 07:32:47 | `or_AnsxpIWvcZ` | https://api2.openreview.net/notes/search?term=Where%20You%20Inject%20Diversity%20Matters%3A%20A%20Unified%20Framework%20for%20Diverse%20Generation&group=ICLR.cc/2027/Conference&limit=10 | HTML/JSON | 1393 |

## How to retrace

1. Run the commands in `README.md` ("How to run") in order. Quote verification and report rendering are deterministic given the cached texts.
2. To check one quote by hand, find it in `evidence/quotes.jsonl` and fetch its `url`. Then run `aii_fast_web_fetch.py grep --url <url> --pattern '<words joined by [\W_]{1,8}>' -i`, or run `tools/qa_second_pass.py`.
3. Saturation results drift: re-running `tools/sat_search.py` on a later date gives different hits. The verdicts are dated 2026-10-21, and the raw responses used are kept in `cache/search_results/`.
4. Known limits:
   - One screener, with a keyword pre-screen before the manual title and abstract screen.
   - ICLR 2027 OpenReview submissions were read at abstract level only.
   - Semantic Scholar's citation graph returned few 2026 citers.
   - E2 timestamps were not captured.
