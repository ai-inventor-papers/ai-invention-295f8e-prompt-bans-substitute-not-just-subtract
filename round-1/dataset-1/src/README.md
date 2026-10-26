# Algorithm-choice coding bench: source data

This repository collects, checks and standardises the external data for an algorithm-choice coding bench. The bench feeds an interpretability study of which algorithm an LLM picks for a coding task (Dijkstra, BFS, quickselect, ...), and where it goes when that choice is banned. The work had two steps:

1. **Discovery.** 98 Hugging Face Hub queries returned 574 unique datasets; GitHub was searched as well. 25 candidates plus one mandatory repository were screened for size, popularity, documentation and actual content, with provenance checked by web search. 15 sources were kept and downloaded at pinned revisions. Full record: [`DATASET_SELECTION.md`](DATASET_SELECTION.md).
2. **Standardisation.** All 15 were standardised and inspected, and the best **10** were kept. [`data.py`](data.py) builds those 10 into one `exp_sel_data_out` file, one example per source row, with bench-specific annotations. The result, [`full_data_out.json`](full_data_out.json), has **61,469 examples** and is 96.2 MB as written by the format script. It passes the schema check and the QA script.

No LLM was called, so the OpenRouter spend is **$0**.

Exact rebuild instructions are in [`reproducibility.md`](reproducibility.md).

## The output: `full_data_out.json`

The file follows the `exp_sel_data_out` schema (copy in `schemas/`): `{"metadata": {...}, "datasets": [{"dataset": name, "examples": [{"input", "output", "metadata_*"}]}]}`. The top-level `metadata` holds:

- the bench task ids
- the LeetCode-to-bench map
- the algorithm-mode lexicon
- a per-dataset summary (count, size, licence, row selection, source revision, paper)
- the SHA-256 of the `data.py` that wrote it

Small companions: `mini_data_out.json` (3 examples per dataset, full strings) and `preview_data_out.json` (the mini file with strings cut to 200 characters and every list to 3 items, so only the first 3 datasets appear).

| dataset | examples | input → output | what it gives the bench build |
|---|--:|---|---|
| `leetcodedataset` | 2,869 | problem text → reference solution | Hidden-test seeds. For the 20 bench-mapped problems present, every I/O pair is parsed into `kwargs` and `expected`, with case id `leetcodedataset:<qid>:<idx>` and a status, in `metadata_test_cases_json`. The reference passes its own `check()` for all 20 (re-run in an isolated `python -I` subprocess). Also carries LeetCode answer semantics, tags and the harness prefix. |
| `mercury` | 440 | problem text → one human solution | Every human solution of the 20 bench-mapped problems Mercury has (8-30 per problem): the only source for T09 LRU (22) and T12 streaming median (22). Also runtime, structural markers (heapq/sort/bisect/OrderedDict/...) and an I/O-hack flag (4 solutions). |
| `llm_creativity` | 225 | `repo@commit:path` → judge label | The T02 external check: the repository's blind-judge `lineage_minor` for all 225 `find_path` programs, mapped to T02 modes (dijkstra 132, bellman_ford_spfa 34, bidirectional 30, other 21, dial 5, a_star 2, floyd_warshall 1), plus 11 fingerprint axes. **No program text: the repository states no licence.** |
| `thealgorithms_python` | 1,354 | code → algorithm name (file stem) | 55 hand-checked bench-mode implementations (`metadata_bench_task` / `metadata_bench_mode`), plus 1,299 other implementations as negatives for AST rules. 1,333 files parse under Python 3.12. |
| `clrs_text` | 2,910 | CLRS-30 trace prompt → trace | Execution traces of the 15 CLRS algorithms that implement a bench mode (bfs, dfs, dijkstra, bellman_ford, floyd_warshall, dag_shortest_paths, topological_sort, mst_kruskal, quickselect, naive/kmp matcher, graham_scan, jarvis_march, activity_selector, binary_search). The first 5 traces are kept for every (algorithm, length): tracer access-order tests. |
| `humanevalplus` | 164 | prompt → complete canonical function | Harness validation with the EvalPlus test code (`metadata_test`); Fibonacci-family flag. |
| `enamel` | 164 | prompt → complete expert-efficient function | Time-limit and stress calibration template: size-levelled `input_generator`, `input_levels` and `checker`. HumanEval/55 fib uses fast doubling. |
| `concreteness_norms` | 39,954 | word → mean concreteness (1-5) | Neutral-twin and context-seed noun bank. Each word carries Qwen3 token counts (with and without a leading space), Open English WordNet noun classes and a `metadata_noun_bank_candidate` flag. **718 candidates**: concrete, frequent nouns with a concrete WordNet class that are a single Qwen3 token, with programming-loaded and sensitive words excluded. `metadata_exclusion_reasons` says why each other word fails. |
| `kodcode_algorithmic` | 2,767 | question → test-verified GPT-4o solution | The Algorithm, Data_Structure and Leetcode subsets with pytest code. 253 rows name a bench mode (e.g. Dijkstra 40, binary search 40): AST-rule checks on LLM-style code. |
| `xlcost_python` | 10,622 | GeeksforGeeks title + comments → detokenised code | Human-written implementations. 209 name a bench mode, incl. 78 Fibonacci variants (fast doubling, golden ratio); 9,779 detokenised programs parse. |

Fields shared across datasets:

- `metadata_task_type`
- `metadata_row_index` (row in the source file)
- `metadata_duplicate_of`: index of the first identical (input, output) example within the dataset, or null
- `metadata_named_algorithms` / `metadata_bench_tasks_named`: a regex lexicon over names, titles or questions. These are **hints, not verified labels**. The lexicon and its exclusions (e.g. Boyer-Moore *majority vote* and regex "a*" matching are not counted) are in the top-level metadata.

Reading it:

```python
import json
doc = json.load(open("full_data_out.json"))
ds = {d["dataset"]: d["examples"] for d in doc["datasets"]}
tests = [json.loads(e["metadata_test_cases_json"]) for e in ds["leetcodedataset"] if e["metadata_bench_task"]]
```

### Why these 10

Each of the 15 standardised datasets was scored on five questions:

1. Does a component of the planned bench consume it (hidden tests, references, labeller validation, harness, stress calibration, prompt construction)?
2. Does it have real targets?
3. Is its provenance solid?
4. May it be published under its licence?
5. Does it add something the others do not?

The 10 kept cover every component. `data.py` contains only those 10. The 15-source version that was run to make the choice is archived as `scripts/selection_stage_data_all15.py`, and rerunning it reproduces `logs/qa_report_all15.json`.

Dropped:

- **NeoCoder** (1,194 denial-prompting steps): the closest prior art for ban prompts, but its bans are syntactic techniques on stdin Codeforces problems, so no bench component uses it.
- **Rosetta Code Python** (1,141): only 16 rows name a bench mode; GFDL copyleft; covered by TheAlgorithms and XLCoST.
- **Open English WordNet nouns** (30,130): its noun classes are already merged into `concreteness_norms`.
- **CreativityPrism** (773) and **NoveltyBench** (1,100): prompt-only (empty outputs) and off-bench. NoveltyBench's licence is not stated.

### Known data issues (handled, documented, never silently dropped)

- **LeetCodeDataset 1971:** 73 of 77 recorded outputs are error messages ("Error: maximum recursion depth exceeded"); **1514 and 1631** have one each. These are marked `status: expected_is_error_message`. The dataset's `check()` excludes them too.
- **LeetCodeDataset 1 (two-sum):** 8 generated cases have no solution (`expected: null`). T05's spec ("exactly one solution") must drop them. Order-free answers (210 topological order, 347 top-k, 587 hull points) need set or validity checkers; see `metadata_leetcode_answer_semantics`.
- **No LeetCodeDataset rows for 146 and 295:** the LRU and median-finder tests must be generated by an oracle; Mercury supplies the human solutions.
- **Duplicates:** XLCoST has 56 exact source duplicates and CLRS 2. They are kept and pointed to by `metadata_duplicate_of`.
- **Problem wording:** LeetCode problem text is source data only. The bench specs must be written in new wording.

## Licences and redistribution

| dataset | licence | note |
|---|---|---|
| LeetCodeDataset | Apache-2.0 | attribution: Xia et al. 2025, arXiv:2504.14655 |
| Mercury | CC-BY-NC-4.0 | non-commercial; Du et al. 2024, arXiv:2402.07844 |
| llm-creativity | none stated | only paths, the commit and judge labels are stored; programs stay in the upstream repo |
| TheAlgorithms/Python | MIT | |
| CLRS-Text | Apache-2.0 | Markeeva et al. 2024, arXiv:2406.04229 |
| HumanEval+ | Apache-2.0 | Liu et al., NeurIPS 2023 |
| ENAMEL | Apache-2.0 | Qiu et al., ICLR 2025 |
| Concreteness norms | MIT (HF mirror); original norms' licence not stated | Brysbaert, Warriner & Kuperman 2014; WordNet classes: Open English WordNet, CC-BY-4.0 |
| KodCode | CC-BY-NC-4.0 | non-commercial; arXiv:2503.02951 |
| XLCoST | CC-BY-SA-4.0 | share-alike; Zhu et al. 2022, arXiv:2206.08474 |

## Layout

| path | contents |
|---|---|
| `data.py` | uv inline script (pinned PEP 723 header): builds the 10 chosen datasets into `full_data_out.json` |
| `full_data_out.json` | final output, 10 datasets, 61,469 examples, 96.2 MB (published; under 100 MB) |
| `mini_data_out.json`, `preview_data_out.json` | 3-example and truncated versions |
| `reproducibility.md` | exact, portable rebuild instructions with expected sizes and hashes |
| `restore.sh` | recreates `.venv/` (deleted after the round) and `temp/datasets/` (not published) |
| `pyproject.toml` | all 45 packages of `.venv` pinned to exact versions (Python 3.12.14) |
| `DATASET_SELECTION.md` | search, screening, provenance and both keep/discard decisions |
| `data_sources.json` | the 15 downloaded sources: repo/url, pinned revision, licence, role, caveats, local files |
| `schemas/exp_sel_data_out.json` | the output schema (copy of the AI Inventor schema) |
| `scripts/download_all.py` | re-downloads every source at its pinned revision into `temp/datasets/` |
| `scripts/download_xlcost.py` | XLCoST Python subset from the Hub's parquet branch (the repo's loader script is unsupported) |
| `scripts/split_json.py` | splits oversized JSON arrays (aii-file-size-limit) |
| `scripts/source_fingerprints.py` | records or checks row counts, content hashes and git trees of the downloads (`logs/source_fingerprints.json`) |
| `scripts/validate_exp_sel_data_out.py` | schema validation (portable stand-in for the AI Inventor validator) |
| `scripts/format_mini_preview.py` | full/mini/preview writer (portable stand-in for the AI Inventor formatter; byte-identical output) |
| `scripts/qa_full_data_out.py` | QA: empty fields, duplicates, metadata-key consistency, bare NaN tokens, test-case status, mapping coverage |
| `scripts/selection_stage_data_all15.py` | the 15-source `data.py` used for the selection stage (writes under `temp/selection_stage/`) |
| `scripts/sanity_check.py`, `scripts/check_coverage.py`, `scripts/candidate_sizes.py` | discovery-step screening |
| `logs/qa_report.json`, `logs/qa_report_all15.json` | QA of the final file and of the 15-source build |
| `logs/source_fingerprints.json` | fingerprints of the downloads used here |
| `logs/sanity/`, `logs/coverage/`, `logs/hf_search/`, `logs/hf_preview/`, `logs/download/` | discovery evidence and download/restore logs |
| `logs/data.log`, `logs/selection_stage_data.log`, `logs/todo.md` | run logs; the step todo lists and their status |
| `temp/` | raw downloads and scratch (**not published**; restorable with `bash restore.sh`) |
| `.venv/` | uv environment for the helper scripts (**not published**; regenerable) |

## How to run

See [`reproducibility.md`](reproducibility.md). In short:

```bash
bash restore.sh                                            # .venv + pinned downloads into temp/datasets/
uv run data.py                                             # full_data_out.json (10 datasets)
.venv/bin/python scripts/format_mini_preview.py --input full_data_out.json   # then rename as in reproducibility.md
.venv/bin/python scripts/validate_exp_sel_data_out.py full_data_out.json
.venv/bin/python scripts/qa_full_data_out.py
```

## Restoring removed files

`.aii/manifest.yaml` marks one path for deletion after the round:

| deleted path | restore command |
|---|---|
| `.venv/` (regenerable) | `uv venv .venv --python=3.12 && uv pip install --python=.venv/bin/python -r pyproject.toml` (also done by `bash restore.sh`) |

Everything else stays on the run's volume. `temp/` holds only JSON text and code, so it needs no manifest decision, but it is excluded from the published repository. On a fresh clone, recreate the raw downloads with `bash restore.sh` (which runs `.venv/bin/python scripts/download_all.py`) and check them with `.venv/bin/python scripts/source_fingerprints.py --check`. A full fresh restore matched 23 of 24 recorded fingerprints; the exception is a representation-only difference in a source `full_data_out.json` does not use.

## Upload exclusions

Not published: `temp/` (third-party raw downloads, including the unlicensed llm-creativity clone, and scratch), `.venv/`, Python bytecode caches, and the agent's session files (`.repl_agent.ptylog`, `.aii_claude_session.json`). The exclusion patterns are `(^|/)temp/`, `(^|/)\.venv/`, `(^|/)__pycache__/`, `^\.repl_agent\.ptylog$` and `^\.aii_claude_session\.json$`.
