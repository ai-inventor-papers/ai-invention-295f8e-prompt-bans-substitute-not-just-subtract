# Reproducing "Where Llama goes when an algorithm is banned"

This file records what was actually run, in order, on 2026-10-20, including the restarts. All paths are relative to this folder.

## 1. Get the artifact

This folder is published as one directory of a public GitHub repository:

```bash
git clone <repository URL>
cd <repository>/<this artifact's folder>     # the folder that contains method.py and this file
```

The folder contains everything the code reads except the model weights and one optional input:

- the read-only input copies in `inputs/`;
- every raw generation, label and judge cache in `data/`;
- the committed forecasts in `predictions/` and the hash chain `commitments.log`;
- all results in `results/`.

The optional input is the dependency dataset `art_j3Rm_lr2nzR6`, used only for the inventory in `results/dependency_inventory.json`. The repository publishes it as a sibling folder named `art_j3Rm_lr2nzR6`. To point elsewhere, set `AII_DEP_DATASET_DIR`.

No user-uploaded input was used: the run's upload folder was empty.

## 2. System, Python and libraries

What was used:

- **OS:** Debian GNU/Linux 12 (bookworm) in a Docker container with a cgroup limit of 6 CPUs and 57 GB RAM. Ubuntu 22.04/24.04 works the same way.
- **GPU:** one NVIDIA L4, 23 GB VRAM, driver 595.91.07. The torch wheels are CUDA 12.8 (`torch 2.8.0+cu128`), so the driver must support CUDA ≥ 12.8.
- **No C compiler is needed, and none was present.** vLLM therefore runs with `enforce_eager=True`, and the code sets `TORCHDYNAMO_DISABLE=1` and `VLLM_ENABLE_V1_MULTIPROCESSING=0` itself, in `src/engine_vllm.py`.
- **System Python 3.12.14** at `python3.12` on `PATH`. The bench harness runs every candidate program in a fresh `python3.12 -I -S` subprocess with only the standard library. `BENCH_SANDBOX_PYTHON` overrides that interpreter.
- **uv 0.6.14.**

```bash
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r pyproject.toml
```

`pyproject.toml` pins all 170 installed packages with `==`, identical to `uv pip freeze --python .venv/bin/python`. The uv venv has no `pip` binary. The key pins are:

- `vllm==0.11.0`
- `torch==2.8.0`
- `transformers==4.57.6`
- `tokenizers==0.22.2`
- `huggingface-hub==0.36.2`
- `zss==1.2.0`
- `numpy==2.2.6`
- `scipy==1.18.1`
- `openai==3.35.1`
- `loguru==0.7.3`

`./restore.sh` runs these two commands, and with `DOWNLOAD_MODEL=1` it also fetches the weights.

## 3. Model, data downloads, environment variables (names only)

- **Model.** `meta-llama/Llama-3.1-8B-Instruct` at revision `0e9e39f249a16976918f6564b8830bc894c89659`, bf16, read through the Hugging Face cache.
  - The repo is gated and needs `HF_TOKEN`.
  - `HF_HOME` / `HF_HUB_CACHE` choose the cache location.
  - The code calls `snapshot_download(repo, revision=..., allow_patterns=['*.json','*.safetensors','tokenizer*'])`, which took 65 s.
  - `method.py setup` checks the four shard sha256s against `inputs/exp10/results/model_record.json` and writes `results/model_record.json`.
- **Judge calls (OpenRouter).** These need `OPENROUTER_BASE_URL` and `OPENROUTER_API_KEY`.
  - Models: `google/gemini-2.5-flash-lite` (j1, disagreements only) and `openai/gpt-4.1-mini` (j2: label audit, 'other' re-audit, and the canon judge of the screen).
  - Every answer is cached in `data/judge_cache.jsonl` (bench) and `screen10/canon/labeller/judge_cache.jsonl` (screen).
  - **Without these variables**, `method.py analyse` runs offline from the caches. This was verified: `results/c1_events.jsonl` came out byte-identical with both variables unset.
- **Figures.** `AII_SKILLS_DIR` must point at the folder that holds `aii-data-fig-gen/scripts/chart_gen.py`; otherwise it is found by searching upward. The JSON spec of every figure is in `figures/*.json`.
- **Inputs from earlier artifacts** of the same run were copied once into `inputs/` and made read-only (`inputs/provenance.json` lists sha256 and size per file):
  - exp11: the frozen bench `inputs/exp11/bench/` and the FP8 Llama pilot;
  - exp10: canon, data, config and results;
  - exp8: the suite;
  - exp7: frozen templates and nouns.

  A reader needs nothing else.

## 4. Commands, in the order they were run

Hardware: one L4 for every GPU stage, never two models on the GPU at once, and CPU labelling running alongside. GPU sessions held the L4 for about 1.8 h of wall time, of which 0.98 h was logged generation (`results/timings.json`). The whole run, including labelling and analysis, took about 4 h of wall time.

**Seeds:**

- Request seeds: `int(sha256(f"{task}|{cond}|{template}|{sample_id}")[:8], 16)`, in `src/ws.request_seed`.
- vLLM: `seed=0`.
- Random directions: 20261020, 20261021 and 20261022, via `torch.Generator`.
- FFH Monte Carlo and the bootstraps: seed 0.
- Proximity pair sampling: seeds `sha256(event|survivor|metric)`.

**Decoding:** T = 1.0, top-p = 1.0, top-k off, min-p 0, no penalties, max_tokens 1024 (96 for association answers), stop ids [128001, 128008, 128009], `generation_config='vllm'`.

| # | command | what it did | time |
|---|---|---|---|
| 1 | `.venv/bin/python tests/test_prompts.py` | T1: one BOS, date line, 500/500 ban/twin pairs equal in length with identical spec ids | 3 min |
| 2 | `.venv/bin/python method.py setup` | provenance, bench sha256 vs `commitment.json` (12/12), canon SHA256SUMS, shard sha256s, X0 freeze, dependency inventory | 2 min |
| 3 | `.venv/bin/python method.py gen1` | T2 sampler test, then B1 (600) and B4 (600) at `max_num_seqs=32` | 11 min |
| 3a | *(first launch of step 3 failed: a 48 GB RLIMIT_AS broke safetensors mmap and CUDA; GPU stages no longer set it)* | | |
| 4 | *(process stopped after B4)* `.venv/bin/python method.py gen1 --phases B3r1,B2,B5` | `make_llm` default raised to `max_num_seqs=64`: forced round 1 (1,000), association (1,000), nonce and novelty (1,200) | 19 min |
| 5 | `method.py label --phases pilot,B1 --no_judge`, then `--phases B1,B4 --no_judge` | bench labellers (tests + runtime tracer + AST) | 2 + 2.5 min |
| 6 | `method.py freeze` (run twice) | judge on disagreements, D, present-minor events. The second run re-tried 14 judge calls that had hit HTTP 429; no labels changed downstream | 2 × 2 min |
| 7 | commit `predictions/x0.json` and `predictions/events.json` (`src/commit.commit`) | first hash-chain entries | – |
| 8 | `method.py label --phases B3r1 --no_judge`, then `method.py assoc` | forced labels; association mapping; forced summary | 7 + 1 min |
| 9 | `method.py label --phases B5 --no_judge` | nonce and novelty labels | 4.5 min |
| 10 | `method.py hf && method.py push` | E1 ban norms + T4 HF hook tests (the first attempt needed a fix: the model is loaded on CPU and moved with `.to('cuda')`, since `accelerate` is not installed), then forced round 2 (540) and E3 pushes (3 × 600, prefill hooks, prefix caching off) | 1.5 + 18 min |
| 11 | `tests/test_scoring.py`, `tests/test_veto.py` | T7 and T3 synthetic tests | 1 min |
| 12 | `method.py label --phases B3r2 --no_judge`, `method.py assoc`, `method.py label --phases E3 --no_judge` (twice) | labels for forced round 2 and the pushes | 4 + 1 + 6 min |
| 13 | `method.py proximity --workers 3` (CPU, concurrent) | Zhang-Shasha nominations; k = 6 chosen automatically because the k = 10 ETA was > 40 min | 14 min |
| 14 | `method.py veto` | n-grams, T3 GPU checks, one-shot, persistent and iterated vetoes (3 rounds), labels between rounds | 26 min |
| 15 | `scripts/fix_veto_decoding.py`; `method.py label --phases D2,D3 --workers 5 --no_judge` | exact (no-cleanup) re-decoding of 594 veto texts and re-labelling of 590 programs, before the commit (deviation `veto_decode`); then the T3 post-hoc test | 3 min |
| 16 | `scripts/write_deviations.py`; `method.py commit` | forecasts for 18 events, hash chain, pre-commit grep audit (0 ban prompts in 10,328 rows); `predictions/*` made read-only | 1.5 min |
| 17 | `method.py ban` | G1 + G2: 1,800 ban samples | 10 min |
| 18 | `method.py label --phases G1,G2 --workers 6 --no_judge` | ban labels | 4 min |
| 19 | `scripts/run_label_audit.py` | C3: second blind judge on 60 bf16 baseline programs | 0.5 min |
| 20 | `method.py analyse`; `audit/rederive.py`; figures (`src/figures.run`); `scripts/make_readme.py`; aii-json format + validate | analysis, outputs, audit | ~5 min |
| 21 | `method.py screen` (the first launch hit the same RLIMIT issue; relaunched) | path-task screen: B6 (300), D4 vetoes (3 rounds), canon labels, forecasts committed, scored against exp10's landings | 14 min |
| 22 | `scripts/labeller_recheck.py` | A3/T0: 50/50 references, gold agreement 0.959 | 2 min |
| 23 | `method.py analyse`; `audit/rederive.py`; `python3 -I audit/rederive_tests.py`; figures; README; aii-json | final outputs and both audits | ~5 min |

To repeat only the CPU part from the published files, using the cached judges and needing no GPU or keys:

```bash
.venv/bin/python method.py analyse
.venv/bin/python audit/rederive.py
python3 -I audit/rederive_tests.py
```

A full re-run repeats steps 1–23. vLLM sampling is seeded per request but is not bit-for-bit reproducible across batch shapes: an identical-seed rerun reproduced 16/20 samples (`results/tests_sampler.json`). Regenerated samples are therefore statistically, not byte-for-byte, equivalent.

## 5. What a reader should get

`results/analysis.json`, `results/c1_events.jsonl` and `README.md`. Every number is also in `method_out.json` → `metadata`.

**Frozen defaults D** (`predictions/events.json`):

| task | D |
|---|---|
| T03 | full_sort |
| T04 | naive |
| T06 | hash_set |
| T05 | hash_map |
| T10 | union_find |
| R1 | greedy_end (D from attempts) |
| T08 | matrix_power |
| R3 | kahn |
| T13 | sort_sweep |
| R6 | binary_search |
| T14 | heap |
| T11 | quadratic_dp |

Present-minor events: T14 sort_by_count, T03 heapify_pop, T03 quickselect, T04 kmp, T10 dfs, T03 size_k_heap.

**C1 (within Llama, pre-pooling):**

- 18 events, 13 gated, 11 disagreeing and gated.
- Wins: SUBTRACT 1 (T05, its undefined→uniform fallback) and ASSOCIATE 1. No family advances, so the branch is **NO FAMILY ADVANCES (aimed, unresolved)**.
- Wilcoxon (n = 11, exact):

  | pair | mean difference | p | Holm-adjusted p | decision |
  |---|---|---|---|---|
  | SUBTRACT − PROXIMITY | +0.345 nats | 0.0029 | 0.0088 | rejected |
  | LADDER − PROXIMITY | +0.306 nats | 0.0020 | 0.0078 | rejected |
  | SUBTRACT − ASSOCIATE | +0.172 nats | 0.52 | – | not rejected |
  | LADDER − ASSOCIATE | +0.133 nats | 0.77 | – | not rejected |

- Top-1 hits on gated events: LADDER 7/13 and ASSOCIATE 7/13 (p = 0.033 vs chance ≈ 0.27), SUBTRACT 4/12, PROXIMITY 3/13.
- Sensitivities (`results/analysis.json` → `sensitivities`):
  - correct-only, bf16-only decision set and drop-W4 each give SUBSTITUTION (ASSOCIATE);
  - excluding the D-from-attempts and audit-flagged tasks gives X-SPECIFIC BUT UNAIMED.

**Tests:** `results/tests_*.json`, `results/labeller_recheck.json`, `results/independent_rederivation.json` (0 mismatches) and `results/independent_rederivation_tests.json` (all match; placebos fail as required).

**Spend:** OpenRouter USD 0.483 in total (bench judge 0.366, screen canon judge 0.117).

No paper exists yet at this step. These are the numbers a later write-up should quote, from the files above.
