# Todo list (copied verbatim from the step prompt; no todo-tracking tool exists in this session, so it is tracked here)

- [x] TODO 1. Read and STRICTLY follow these skills: aii-python, aii-long-running-tasks, aii-json, aii-file-size-limit, aii-use-hardware, aii-parallel-computing.
- [x] TODO 2. Read skill files for your data sources (see <available_data_sources>) and domain handbook if applicable (see <available_domain_handbooks>). Based on plan and context, decide which source(s) to use. Include everything specified in the artifact plan, but you may also collect additional relevant data beyond what's listed. Run 50 diverse searches across chosen source(s) — BROAD, GENERAL terms, not very specific. Parallelize where supported.
- [x] TODO 3. Identify the 25 most promising datasets. IMPORTANT: Only consider datasets under 300MB. Preview/inspect sample rows for each candidate. Parallelize previews.
- [x] TODO 4. Research each candidate BEFORE choosing which to download. For each, search the web (aii-web-tools skill): dataset name, papers citing it, original source/task, popularity. Red flags: no search results, no papers, anonymized features (F1, F2...), <100 downloads, no documentation. Green flags: papers using it, clear documentation, meaningful features, established benchmark. Also consider: will features/structure allow meaningful evaluation of the planned method?
- [x] TODO 5. Decide which to KEEP vs DISCARD. Look for: clear structure, relevant fields, quality examples matching requirements, confirmed provenance. Determine which 15 datasets have the most suitable data. Download and save to `temp/datasets/`. Parallelize downloads.

## Status (2026-10-19)
- TODO 1: all six skills read and applied (uv venv + loguru scripts, staged runs, aii-json formats, file-size splitting, cgroup-aware hardware check, parallel searches/previews/downloads).
- TODO 2: sources = HF Hub (aii-hf-datasets) + GitHub (alternate method); mech-interp handbook read. 98 searches (50 broad + 20 single-token broad + 28 targeted) -> 574 unique datasets (logs/hf_search/).
- TODO 3: 25 candidates (+ mandatory llm-creativity repo) previewed in parallel (logs/hf_preview/), sizes screened against 300 MB.
- TODO 4: provenance web-searched for every candidate; content coverage checked (logs/coverage/); see DATASET_SELECTION.md.
- TODO 5: 15 kept, downloaded at pinned revisions to temp/datasets/ (parallel, per-dataset output dirs), oversize files split, sanity-checked (logs/sanity/sanity_report.json); catalogue data_sources.json.

# Todo list, prompt 2 (copied verbatim from the step prompt)

- [x] TODO 1. For the top 15 datasets, create data.py (uv inline script) that: loads from temp/datasets/, standardizes to exp_sel_data_out.json schema (aii-json skill), extracts all examples per dataset, handles domain requirements, saves to full_data_out.json.

Each data ROW must be a separate example — do NOT create one example per dataset or per fold. Each data point (row, sample, instance) = one example. 500 rows → 500 examples. The output is GROUPED BY DATASET:
```json
{
  "datasets": [
    {
      "dataset": "iris",
      "examples": [
        {"input": "...", "output": "...", "metadata_fold": 2, "metadata_feature_names": [...]},
        ...
      ]
    },
    {
      "dataset": "adult_census",
      "examples": [...]
    }
  ]
}
```
Per-example required fields:
- `input`: input features/text (tabular: JSON string of feature values)
- `output`: target/label (as string)
Per-example optional metadata via `metadata_<name>` fields (flat, not nested object):
- `metadata_fold`: fold assignment (int), `metadata_feature_names`: feature name list, `metadata_task_type`: "classification"/"regression", `metadata_n_classes`: number of classes, `metadata_row_index`: original row index, etc.
Do NOT use `split`, `dataset`, or `context` as per-example fields. Dataset name goes at the group level, metadata goes in `metadata_*` fields.
- [x] TODO 2. Run 'uv run data.py' and fix errors. Validate full_data_out.json against exp_sel_data_out.json schema (aii-json skill) — fix errors. Generate preview, mini, full versions with aii-json skill's format script.
- [x] TODO 3. Read preview to inspect examples. Choose THE BEST 10 DATASETS based on domain requirements and artifact objective. Be very attentive to meticulously and exhaustively fix any errors in your code.

## Status, prompt 2 (2026-10-19)
- TODO 1: data.py (uv inline script) standardises all 15 sources into exp_sel_data_out, one example per source row (documented domain subsets for Mercury, CLRS-Text, KodCode), with bench annotations.
- TODO 2: `uv run data.py --datasets all` -> 104.6 MB in 2 parts, schema PASSED for both, mini/preview generated; final `uv run data.py` -> full_data_out.json (82.6 MB, 61,469 examples, 10 datasets), schema PASSED, QA PASSED, mini_data_out.json + preview_data_out.json generated.
- TODO 3: preview/mini inspected; best 10 chosen (README.md, DATASET_SELECTION.md section 5); errors found by inspection/QA fixed and re-verified.

# Todo list, prompt 3 (copied verbatim from the step prompt)

- [x] TODO 1. Update data.py to only include the chosen 10 datasets and generate full_data_out.json. Re-run to generate full_data_out.json. Validate output format with aii-json skill and fix any errors. Generate full, mini, and preview versions with aii-json skill's format script using `--input full_data_out.json` (creates full_full_data_out.json, mini_full_data_out.json, preview_full_data_out.json — rename to full_data_out.json, mini_data_out.json, preview_data_out.json).
- [x] TODO 2. Verify full_data_out.json, preview_data_out.json, and mini_data_out.json exist in your workspace (see <workspace>) and contain correct data.
- [x] TODO 3. Apply aii-file-size-limit skill's file size check procedure (100MB limit) to full_data_out.json.
- [x] TODO 4. Ensure a `pyproject.toml` exists in your workspace with ALL dependencies pinned to the exact versions installed in your .venv (run `.venv/bin/pip freeze` to get them). This is required for reproducibility. The [project] section must include name, version, requires-python, and a dependencies list with pinned versions (e.g. `numpy==2.0.2`, not `numpy>=2.0`).
- [x] TODO 5. Write `reproducibility.md` in your workspace with COMPLETE step-by-step instructions to reproduce your exact results on Ubuntu — describe what you ACTUALLY ran, not an idealized version. Cover: (1) getting this artifact: your workspace is published as one folder of a public GitHub repository, so start from a clone of that repository and `cd` into the folder; (2) system packages, the Python version, venv creation, and the exact library versions you actually installed, pinned (match pyproject.toml); (3) any data/model/checkpoint downloads plus env vars or API keys needed, by NAME only, never values; (4) the exact commands you ran, in order, with seeds, configs, hardware used (GPU type, VRAM) and approximate runtime; (5) which output files and numbers a reader should get, and where they appear in the paper. PORTABLE PATHS: a reader has only the published repository, never this server, so every path in this file, in `restore.sh` or any install script, and in your code must be RELATIVE to your workspace (in code, anchor it on `Path(__file__)`), never an absolute `/ai-inventor/...` path. Read an input another artifact produced through ONE relative constant or environment variable and name that artifact by its id; the repository publishes it as a sibling folder. An input the user uploaded is private and is not published: say so, and say how a reader supplies their own copy. This is a REQUIRED output file, like the others above.

## Status, prompt 3 (2026-10-19)
- TODO 1: data.py restricted to the 10 chosen datasets (15-source version archived as scripts/selection_stage_data_all15.py; inline deps and the Qwen3 tokenizer revision pinned); `uv run data.py` re-run; aii-json validation PASSED; format script run with `--input full_data_out.json` and outputs renamed to full_data_out.json / mini_data_out.json / preview_data_out.json; validation PASSED again.
- TODO 2: all three files exist; QA PASSED (10 datasets, 61,469 examples); mini = first 3 examples per dataset; preview = faithful truncation; embedded data_py_sha256 matches data.py.
- TODO 3: full_data_out.json = 96,205,300 bytes (< 100 MB): no split needed.
- TODO 4: pyproject.toml pins all 45 .venv packages (from `uv pip freeze`; the uv venv has no pip); a fresh venv from it reproduces the identical freeze.
- TODO 5: reproducibility.md written (relative paths only), with portable stand-ins for the AI Inventor tools (validator, formatter: byte-identical), restore.sh, and source fingerprints (fresh full restore: 23/24 identical).
