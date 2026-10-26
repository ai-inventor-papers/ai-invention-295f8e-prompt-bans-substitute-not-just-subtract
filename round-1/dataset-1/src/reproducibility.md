# Reproducing this artifact (`gen_art_dataset_1`)

This artifact downloads 15 public data sources, standardises 10 of them into one `exp_sel_data_out` file, and validates it. It makes no LLM or API calls: the OpenRouter spend is $0 and no API key is needed. The GPU on the machine was not used.

The commands below are the ones actually run, in order. Where a step used an internal AI Inventor tool (a "skill" script, which is not published), the portable script in this folder that reproduces it is named. Each such script was checked against the original's output; the checks are noted.

All paths are relative to this folder.

## 1. Get the artifact

The artifact is published as one folder of a public GitHub repository:

```bash
git clone <URL of the published repository>
cd <repository>/<folder of artifact gen_art_dataset_1>   # the folder that contains this file and data.py
```

The heavy folders `temp/` (raw downloads, about 840 MB) and `.venv/` are not in the repository. Section 3 recreates them.

## 2. System, Python and libraries

**What was used**

- OS and hardware: a Debian 12 (bookworm) container, Linux 6.8, AMD EPYC 9254 limited to 6 CPUs, 57 GB RAM. An NVIDIA L4 (23 GB VRAM) was present but **unused**.
- Disk: about 1.3 GB in this folder (temp/ and .venv/), plus a few hundred MB of Hugging Face cache.
- Tools: uv 0.6.14 and git 2.39.5.
- Python: 3.12.14.

**On Ubuntu 22.04 or 24.04**

```bash
sudo apt-get update && sudo apt-get install -y git curl ca-certificates
curl -LsSf https://astral.sh/uv/0.6.14/install.sh | sh     # uv 0.6.14, the version used here
uv python install 3.12.14
uv venv .venv --python=3.12.14
uv pip install --python=.venv/bin/python -r pyproject.toml
```

**What gets installed**

- `pyproject.toml` pins all 45 packages that were installed in `.venv`, at their exact versions. Among them: datasets==5.1.0, huggingface-hub==2.2.0, pandas==3.0.6, pyarrow==26.0.0, tokenizers==0.23.3, loguru==0.7.3, jsonschema==4.26.0, numpy==2.5.4.
- The pins came from `uv pip freeze --python .venv/bin/python`. A uv-created venv has no `pip`, so this is the equivalent of `pip freeze`.
- A fresh venv built from this `pyproject.toml` gave an identical freeze.
- `data.py` is a uv inline script. `uv run data.py` builds its own cached environment from the script's PEP 723 header: Python 3.12 with loguru==0.7.3, tokenizers==0.23.3 and huggingface-hub==2.2.0, the same versions as `.venv`. It does not use `.venv`.

## 3. Data, model files and environment variables

**Data sources**

All 15 sources are pinned in `data_sources.json`: 12 Hugging Face datasets at a commit SHA, and 4 GitHub repositories at a commit. To restore them:

```bash
bash restore.sh        # creates .venv if missing, then runs .venv/bin/python scripts/download_all.py
.venv/bin/python scripts/source_fingerprints.py --check   # compare your download with the one used here
```

`scripts/source_fingerprints.py --check` compares your download with `logs/source_fingerprints.json`: row counts and content hashes for every file, plus commit and tree hashes for the git repositories. A full fresh restore made here took about 6 minutes, and 23 of 24 entries matched exactly. The exception is `creativityprism_aut`, whose empty nested field `iteration_lst` is stored as the string `"{}"` by the download tool used originally and as an empty object by `download_all.py`. That source is not part of `full_data_out.json`.

**Model file**

Only `tokenizer.json` of `Qwen/Qwen3-8B` at commit `b968826d9c46dd6066d109eabc6255188de91218` (about 11 MB) is needed, for token counts in `concreteness_norms`. `data.py` fetches it through the Hugging Face cache. No model weights are needed.

**Environment variables (names only)**

| variable | needed? | purpose |
|---|---|---|
| `HF_TOKEN` | optional | Hugging Face rate limits; all datasets used are public and ungated |
| `HF_HOME`, `HF_HUB_CACHE`, `HF_DATASETS_CACHE` | optional | cache locations |
| `UV_CACHE_DIR` | optional | uv cache location |

No other keys are used.

**Other inputs**

- **Other artifacts:** none; this artifact reads nothing from other artifacts.
- **User uploads:** none; the run's private upload folder was empty, so nothing private is required.

## 4. Commands, in the order they were run (2026-10-19)

No step uses randomness, so there are no seeds. The CLRS subset is the first 5 rows per (algorithm, length) in file order. The plan's seed 20261019 belongs to later forecast steps that are not part of this artifact.

### 4a. Discovery

| # | what was run | portable equivalent / note | output | time |
|--:|---|---|---|---|
| 1 | AI Inventor hardware probe (cgroup CPU/RAM, `nvidia-smi`) | `nproc`, `free -g`, `nvidia-smi` | (none) | seconds |
| 2 | 98 Hugging Face Hub searches with the AI Inventor dataset-search tool (queries in `logs/hf_search/queries*.txt`) | `huggingface_hub.HfApi().list_datasets(search=q, sort="downloads", limit=8)`. Results and download counts change over time; the outputs seen on 2026-10-19 are in `logs/hf_search/` | 574 unique datasets | ~12 min |
| 3 | `.venv/bin/python scripts/candidate_sizes.py logs/hf_preview/candidates.txt logs/hf_preview/candidate_sizes.json` | same | repo sizes, downloads, licences | ~20 s |
| 4 | AI Inventor dataset-preview tool on 25 candidates, 2 rows each | `datasets.load_dataset(..., streaming=True)` | `logs/hf_preview/p_*.txt` | ~2 min |
| 5 | `.venv/bin/python scripts/check_coverage.py` | same | `logs/coverage/*.json` | ~1.5 min |
| 6 | web searches on each candidate's provenance | not scriptable; summarised in `DATASET_SELECTION.md` | (none) | (none) |
| 7 | AI Inventor dataset-download tool, 14 jobs in parallel (`--revision <sha> --output-dir temp/datasets/<key>`); `git clone --depth 1` ×4; `.venv/bin/python scripts/download_xlcost.py`; `.venv/bin/python scripts/split_json.py <3 files> --max-mb 90` | `bash restore.sh`, verified with `scripts/source_fingerprints.py --check` (section 3). A first parallel run without separate output folders collided on a shared temporary file and was deleted. | `temp/datasets/` | ~1 min (warm cache) |
| 8 | `.venv/bin/python scripts/sanity_check.py` | same; runs LeetCodeDataset references in `python -I` subprocesses (2 GB address-space and 60 s CPU limits) | `logs/sanity/sanity_report.json` | ~20 s |
| 9 | `.venv/bin/python scripts/download_all.py --catalog-only` | same | `data_sources.json` | seconds |

### 4b. Standardisation of all 15 sources and the selection of 10

| # | what was run | output | time |
|--:|---|---|---|
| 10 | At the time, `uv run data.py --datasets all`. That version is archived as `scripts/selection_stage_data_all15.py`; rerun it with `uv run scripts/selection_stage_data_all15.py` | `temp/selection_stage/full_data_out/full_data_out_{1,2}.json` (104.6 MB, split above 95 MB) | ~40 s |
| 11 | `.venv/bin/python scripts/qa_full_data_out.py temp/selection_stage/full_data_out/full_data_out_1.json temp/selection_stage/full_data_out/full_data_out_2.json` | identical to `logs/qa_report_all15.json` (verified) | ~10 s |
| 12 | Inspected the mini/preview files, fixed the problems found (listed in `DATASET_SELECTION.md` section 5), and chose the best 10 | `README.md`, `DATASET_SELECTION.md` | (none) |

### 4c. Final build

1. Build the output. Only the 10 chosen datasets are produced. The 20 LeetCodeDataset reference solutions are re-run in isolated subprocesses; add `--no-verify` to skip that.

   ```bash
   uv run data.py
   ```

   This writes `full_data_out.json`, compact, 82.6 MB, in about 35 s.

2. Validate. What was run was the AI Inventor JSON validator (`--format exp_sel_data_out`), which passed. The portable equivalent uses `schemas/exp_sel_data_out.json` and gives the same verdict:

   ```bash
   .venv/bin/python scripts/validate_exp_sel_data_out.py full_data_out.json
   ```

3. Make the full, mini and preview versions. What was run was the AI Inventor formatter on `full_data_out.json`, which writes `full_full_data_out.json`, `mini_full_data_out.json` and `preview_full_data_out.json`. The portable equivalent is byte-identical (verified):

   ```bash
   .venv/bin/python scripts/format_mini_preview.py --input full_data_out.json
   mv full_full_data_out.json full_data_out.json
   mv mini_full_data_out.json mini_data_out.json
   mv preview_full_data_out.json preview_data_out.json
   ```

4. Re-validate and run QA:

   ```bash
   .venv/bin/python scripts/validate_exp_sel_data_out.py full_data_out.json
   .venv/bin/python scripts/qa_full_data_out.py            # QA PASSED; writes logs/qa_report.json
   ```

5. Size check (aii-file-size-limit, 100 MB): `ls -l full_data_out.json` shows 96,205,300 bytes, under the limit, so no split was needed.

## 5. What you should get

| file | bytes | sha256 | content |
|---|--:|---|---|
| `full_data_out.json` | 96,205,300 | `079dec278b504db49dfad24cdf8713e2400ec9abbc9c49c56511a35f9f4c3038` | 10 datasets, 61,469 examples (indent=2) |
| `mini_data_out.json` | 262,028 | `05d917f00573e15b508cb137dda9dfc76b1a403a4a16ab12e0b874a9461e6721` | first 3 examples of each dataset |
| `preview_data_out.json` | 26,394 | `38d5ee1b784be2720c1163285b15ecbf215e51db292c4f456518711f1aa36db5` | mini, strings cut to 200 characters, lists to 3 items |

`metadata.data_py_sha256` inside `full_data_out.json` must equal `sha256sum data.py`, which is `ce7f0a30635886c2ea76606aab2b70bc3b86f308d3e97d5cf5871f852188f064`.

| dataset | examples | dataset | examples |
|---|--:|---|--:|
| leetcodedataset | 2,869 | humanevalplus | 164 |
| mercury | 440 | enamel | 164 |
| llm_creativity | 225 | concreteness_norms | 39,954 |
| thealgorithms_python | 1,354 | kodcode_algorithmic | 2,767 |
| clrs_text | 2,910 | xlcost_python | 10,622 |

Other numbers to check (from `logs/qa_report.json`):

- LeetCodeDataset reference checks pass 20/20.
- LeetCodeDataset 1971 has 73 of 77 expected outputs that are error messages; 1514 and 1631 have one each; two-sum has 8 cases with no solution.
- The noun bank has 718 candidates.
- Mercury has 4 solutions flagged as I/O hacks.
- XLCoST has 56 duplicates and CLRS 2.
- The llm-creativity labels map to Dijkstra 132, Bellman-Ford/SPFA 34, bidirectional 30, other 21, Dial 5, A* 2 and Floyd-Warshall 1.

**Caveats on byte-identical reproduction.** The bytes match only if your downloads match the fingerprints and you use the pinned library versions. A much slower machine could also turn a LeetCode reference re-check into a timeout, which would set `metadata_reference_passes_check` to false; the run log would show it.

**Where the numbers go in the paper.** The paper had not been written when this artifact was produced. These counts, the source table and the licences are meant for its data and bench-construction section, cited as artifact `gen_art_dataset_1`.

## 6. Cleanup and restoring

After the round, `.aii/manifest.yaml` deletes `.venv/` (regenerable). `temp/` stays on the run's volume but is excluded from the published repository. On a fresh clone, recreate both with `bash restore.sh`, then rebuild with `uv run data.py`. Everything else in the folder is published.
