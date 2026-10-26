# Dataset selection record (search → screen → provenance → keep/discard)

Date: 2026-10-19. Every number below was measured in this step (scripts and logs named in each row).

## 1. Search

98 Hugging Face Hub queries, run in parallel with the aii-hf-datasets search script (logs: `logs/hf_search/`):

| batch | queries | kind | file |
|---|--:|---|---|
| 1 | 50 | broad terms (leetcode, code generation, algorithms, data structures, unit tests, competitive programming, code complexity, creativity, novelty, negation, ...) | `logs/hf_search/queries.txt` |
| 1 | 12 | targeted at sources named in the plan or close to it | `logs/hf_search/queries_targeted.txt` |
| 2 | 20 | single-token broad terms (the Hub search matches repo-id substrings, so 7 multi-word batch-1 queries returned nothing) | `logs/hf_search/queries_batch2.txt` |
| 3 | 16 | targeted: code-efficiency benchmarks, noun/word-norm resources | `logs/hf_search/queries_batch3.txt` |

Result: 574 unique datasets. Ten queries returned nothing or hung: `algorithm implementation`, `algorithm tags`, `constraint following`, `denial prompting`, `dynamic programming`, `mutation testing`, `neocoder`, `judge` (hung; covered by `llm judge`), `thealgorithms`, `algorithms-python`. Repositories that live on GitHub (llm-creativity, TheAlgorithms/Python, JHU-CLSP/NeoCoder, q-rz/enamel) were found through the plan and web search, and their metadata was read from the GitHub API.

## 2. Screen (size, popularity, documentation, content)

- Repo sizes, downloads, licence and loader scripts: `scripts/candidate_sizes.py` → `logs/hf_preview/candidate_sizes.json`.
- Previews (2-3 rows each): `logs/hf_preview/p_*.txt`.
- Content coverage of the bench targets and named algorithms: `scripts/check_coverage.py` → `logs/coverage/*.json`.

## 3. The 25 candidates plus the mandatory repository

Downloads are HF all-time counts on 2026-10-19; ★ = GitHub stars. "Data size" is what this step would download.

| # | candidate | source | data size | popularity | licence | provenance (verified by web search this step) | what the content check found | decision |
|--:|---|---|--:|--:|---|---|---|---|
| 1 | newfacade/LeetCodeDataset | HF | 101 MB | 12,876 dl | Apache-2.0 | Xia et al. 2025, arXiv:2504.14655; GitHub 55★ | 15 of the 17 LeetCode-matched bench problems, with 17-144 I/O pairs each; the reference completion passes 100% of the asserts for all 15; every I/O input parses as kwargs. 146 (LRU) and 295 (median finder) are absent | **KEEP** |
| 2 | Elfsong/Mercury | HF | 10.8 MB | 318 dl | CC-BY-NC-4.0 | Du et al. 2024, arXiv:2402.07844; GitHub 87★ | all 17 targets incl. 146 and 295; 8-30 deduplicated human solutions per target, 0-2 I/O hacks each; mode diversity (295: heap 8, sort 10, bisect 2; 146: OrderedDict 3, linked list 8). `generator_code` is `'None'` for the targets | **KEEP** |
| 3 | DONG19/EffiBench | HF | 50 MB | **77 dl** | none stated | EffiBench, NeurIPS 2024, arXiv:2402.02037; GitHub 63★ | test-case generators for 743, 28, 287, 509, 547, 295, 56, 347, 435 | discard: under 100 downloads and no licence. Its generators target LeetCode's constraints, not the frozen spec, and the plan builds oracle generators anyway |
| 4 | greengerong/leetcode | HF | 16 MB | 2,364 dl | MIT tag | card is the licence line only; an HF discussion reports Python solutions mismatched with problem text | all targets | discard: no documentation, known mismatches, redundant with #1-#2 |
| 5 | kaysss/leetcode-problem-detailed | HF | 44 MB | 268 dl | MIT tag | LeetCode scrape with a column-level card | tags, similar questions, constraints | discard: redundant with LeetCodeDataset tags and descriptions |
| 6 | neulab/leetcode | HF | 313 MB | 735 dl | Apache-2.0 | derived from LeetCodeDataset (constraint-filtered tests) | — | discard: over 300 MB, derivative |
| 7 | evalplus/humanevalplus | HF | 14 MB | 39,771 dl | Apache-2.0 | Liu et al., NeurIPS 2023, arXiv:2305.01210 (tests ~80x HumanEval) | 164 tasks; Fibonacci family HumanEval/39, 46, 55, 63, 130 | **KEEP** (harness validation) |
| 8 | evalplus/mbppplus | HF | 1.1 MB | 58,286 dl | Apache-2.0 | EvalPlus | no bench-task overlap | discard: HumanEval+ already covers harness validation |
| 9 | evalplus/evalperf | HF | 397 MB | 1,886 dl | none | Liu et al., COLM 2024, arXiv:2408.06450 | performance-exercising inputs | discard: over 300 MB |
| 10 | q-rz/enamel (HF + GitHub) | HF/GH | 0.1 MB + 0.7 MB | 136 dl, 17★ | Apache-2.0 | Qiu et al., ICLR 2025, arXiv:2406.06647 | expert efficient references and size-levelled input generators for 164 HumanEval tasks (HumanEval/55 fib levels 10/30/9000/10000) | **KEEP** |
| 11 | christopher/rosetta-code | HF | 37 MB parquet | 1,261 dl | GFDL | Rosetta Code crawl with a documented card | Python: Dijkstra's algorithm, Floyd-Warshall, Quickselect, Convex hull, Fibonacci sequence, LIS, Topological sort, Binary search (one variant each) | **KEEP** |
| 12 | mike-ravkine/rosettacode-parsed | HF | 12.6 MB | 140 dl | GFDL | parsed from jondurbin/rosettacode-raw | only 1 of those 8 tasks has Python | discard |
| 13 | codeparrot/xlcost-text-to-code (Python program-level) | HF | ~5 MB | 988 dl | CC-BY-SA-4.0 | Zhu et al. 2022, arXiv:2206.08474 (GeeksforGeeks) | 10,622 programs (train 9,263 / val 472 / test 887); algorithm-named titles in train: Fibonacci 69 (incl. fast doubling), LIS 12, binary search 40, DFS 6, BFS 5, quickselect/Boyer-Moore/Rabin-Karp/Bellman-Ford/Floyd-Warshall/DSU 2 each | **KEEP** |
| 14 | TheAlgorithms/Python | GitHub | 15.6 MB | 225,397★ | MIT | educational implementations repository | 48 named files mapped to catalogue modes, 47 parse under Python 3.12 | **KEEP** |
| 15 | smcleish/CLRS-Text-test (split test_1) | HF | 44 MB parquet | 109 dl | Apache-2.0 | Markeeva et al. 2024, arXiv:2406.04229 (Google DeepMind CLRS) | 100,400 traces for 30 algorithms incl. bfs, dfs, dijkstra, bellman_ford, floyd_warshall, dag_shortest_paths, quickselect, naive/kmp matcher, graham_scan, jarvis_march, activity_selector, topological_sort | **KEEP** |
| 16 | facebook/BigOBench | HF | 82 MB (time test set; repo 88 GB) | 973 dl | CC-BY-NC-4.0 | arXiv:2503.15242 (Meta FAIR, Inria) | complexity-labelled stdin programs; scaling them needs the authors' input-expansion framework | discard: ENAMEL gives size-levelled generators directly, at a tiny fraction of the size |
| 17 | codeparrot/codecomplex | HF | 14 MB | 217 dl | Apache-2.0 | Baik et al., arXiv:2401.08719 | 4,517 Codeforces programs, all **Java** | discard: the bench labellers analyse Python |
| 18 | CodeEff/ECCO | HF | 202 MB | 256 dl | none | Waghjale et al., EMNLP 2024 | slow/fast program pairs, no algorithm labels | discard |
| 19 | KodCode/KodCode-Light-RL-10K | HF | 74 MB | 8,743 dl | CC-BY-NC-4.0 | arXiv:2503.02951 (Findings of ACL 2025) | 2,767 Algorithm/Data_Structure/Leetcode rows; algorithm-named questions: Dijkstra 40, binary search 42, Fibonacci 23, BFS 17, DFS 11, merge intervals 11, Rabin-Karp 9, topological 8 | **KEEP** |
| 20 | openai/openai_humaneval | HF | 0.1 MB | 242,192 dl | MIT | HumanEval | superseded by #7 | discard |
| 21 | yimingzhang/novelty-bench (prompts) | HF | 0.1 MB (repo 1.9 GB) | 3,860 dl | not stated | Zhang et al. 2025, arXiv:2504.05228 | 100 curated + 1,000 WildChat prompts | **KEEP** |
| 22 | joeyhou/creativityprism_v1 | HF | 12.9 MB | 760 dl | other (per task) | Hou et al. 2025, arXiv:2510.20091 | AUT 63, TTCT 700, short story 10, NeoCoder 199 | **KEEP** |
| 23 | JHU-CLSP/NeoCoder | GitHub | 10.4 MB | 14★ | Apache-2.0 | Lu et al., NAACL 2025, arXiv:2407.09007 | 199 problems with progressive technique bans (for loop 194, if statement 176, while loop 124, recursion 86, hashmap 28, sorting 18, ...) | **KEEP** |
| 24 | StephanAkkerman/concreteness-ratings | HF | 1.6 MB | 251 dl | MIT tag | Brysbaert, Warriner & Kuperman 2014, Behav. Res. Methods 46:904-911 | 14,592 nouns, 1,055 concrete and frequent, 996 of them single Qwen3 tokens; "horse/chair/roof/love" are 1 token each | **KEEP** |
| 25 | jon-tow/open-english-wordnet-synset-2023 | HF | 54 MB | 519 dl | CC-BY-4.0 | Open English WordNet 2023 (McCrae et al.) | 120,135 synsets; noun lexfiles (artifact 12,151, animal 7,532, cognition 3,149, ...) | **KEEP** |
| — | DrejcPesjak/llm-creativity | GitHub | 2.2 MB | 0★ | **none** | the run's inspiration repository, named in the user request and the plan | 225 `find_path` programs (8 strategies + 1 confounded run), per-strategy blind-judge labels | **KEEP** (mandatory; evaluation only) |

Also rejected at the preview stage: g-ronimo/kaggle_english_word_frequency (42 downloads), and the data of Lee et al. (Findings of EMNLP 2025, "How Diversely Can Language Models Solve Problems?"). Their paper says code and data are public, but no repository link could be found in the arXiv text (it uses APPS). AtCoder/Codeforces-scale corpora (TACO, APPS, CodeContests, LiveCodeBench, open-r1/codeforces, Codeforces-Python-Submissions, CLRS-Text-train, effibench-x) were excluded at the 300 MB size screen.

## 4. Kept: 15 sources and what each one is for

| source | role in the artifact plan |
|---|---|
| LeetCodeDataset | STEP 4b-i hidden-test seeds for T02-T08, T10, T11, T13, T14, R1-R3, R6 |
| Mercury | STEP 5 external, mode-diverse human program pool (the only source with 146/295 solutions) |
| llm-creativity | T02 contract and external labeller check against authoritative judge labels |
| TheAlgorithms/Python | STEP 4a reference starting points; out-of-distribution AST-rule checks |
| CLRS-Text-test | STEP 5 tracer unit tests against canonical traces |
| XLCoST (Python programs) | AST-rule checks and alias mining |
| KodCode-Light-RL-10K | AST-rule checks on LLM-written forced-style implementations |
| Rosetta Code | alias lists; judge/AST sanity items |
| ENAMEL (HF + GitHub) | STEP 4c time-limit rule and stress calibration template |
| HumanEval+ | STEP 4e harness validation |
| NeoCoder | prior art for ban prompts (denial prompting) |
| CreativityPrism | cross-domain creativity inputs (AUT etc.) |
| NoveltyBench | non-code diversity prompts for the original request's temperature and seeding questions |
| concreteness ratings | STEP 2 neutral-twin and context-seed noun bank |
| Open English WordNet | semantic filtering of the noun bank |

## 5. Second stage: standardisation and the best 10

`data.py` standardised all 15 kept sources into `exp_sel_data_out`, one example per source row, with documented domain subsets for the three oversized sources:

- **Mercury:** the solutions of the bench-mapped problems only.
- **CLRS-Text:** 5 traces per (algorithm, length) for the 15 algorithms that implement a bench mode.
- **KodCode:** the Algorithm, Data_Structure and Leetcode subsets only.

The 15-dataset build (`uv run data.py --datasets all` at the time; that version of `data.py` is archived as `scripts/selection_stage_data_all15.py`, and the final `data.py` builds only the chosen 10) came to 104.6 MB, written as 2 parts. It passed schema validation and QA (`logs/qa_report_all15.json`, which rerunning the archived script reproduces). After inspecting the preview and mini files, the 10 that feed a bench component were kept:

| dataset | examples | decision | reason |
|---|--:|---|---|
| leetcodedataset | 2,869 | **keep** | hidden-test seeds; 20 bench-mapped problems with parsed cases; references pass 20/20 |
| mercury | 440 | **keep** | only human-solution pool for T09/T12; mode-diverse programs for labeller checks |
| llm_creativity | 225 | **keep** | plan's T02 external check (authoritative judge labels; paths only) |
| thealgorithms_python | 1,354 | **keep** | 55 hand-checked mode implementations + negatives (MIT) |
| clrs_text | 2,910 | **keep** | ground-truth traces for tracer access-order features |
| humanevalplus | 164 | **keep** | harness validation |
| enamel | 164 | **keep** | stress and time-limit calibration template |
| concreteness_norms | 39,954 | **keep** | neutral-twin and context-seed noun bank (718 candidates) |
| kodcode_algorithmic | 2,767 | **keep** | LLM-style named implementations with tests (253 name a bench mode) |
| xlcost_python | 10,622 | **keep** | human-written named implementations (209 name a bench mode; Fibonacci variants) |
| neocoder | 1,194 | drop | technique bans on stdin problems; no bench component uses it |
| rosetta_code_python | 1,141 | drop | 16 bench-relevant rows; GFDL; redundant |
| open_english_wordnet_nouns | 30,130 | drop | noun classes already merged into concreteness_norms |
| creativityprism | 773 | drop | prompt-only, per-task licences, off-bench |
| novelty_bench | 1,100 | drop | prompt-only, licence not stated, off-bench |

Inspection also found, and fixed, the following in `data.py` (all re-verified):

- **LeetCodeDataset error outputs:** 1971 (73/77), 1514 (1) and 1631 (1) record error messages as expected outputs. These are now an explicit case status.
- **A\* lexicon:** the pattern matched markdown bold, multiplication and regex "a*". It now requires search/algorithm context.
- **Other lexicon homonyms:** Boyer-Moore majority vote, Trabb Pardo-Knuth, cocktail-shaker "bidirectional" sort, and "repeated elements" in sorting tasks no longer match.
- **ENAMEL outputs:** they did not parse because the prompts lack a final newline. Now 164/164 parse.
- **Rosetta Code:** two rows had empty descriptions.
- **Noun bank:** programming-loaded words (python, java, bug, log, thread, ...) and alcohol terms leaked into the candidates; they are now excluded.
