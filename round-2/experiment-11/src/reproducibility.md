# Reproducing this artifact (coding-task bench with a baseline pilot)

This file lists what was **actually run** on 2026-10-20, in order, including the launches that failed and how each was fixed. Every path is relative to this folder.

## 1. Get the artifact

The workspace is published as one folder of a public GitHub repository:

```bash
git clone <URL of the published repository>
cd <repository>/<folder of this artifact>      # the folder that contains method.py and this file
```

The only input from another artifact is the dataset artifact **art_j3Rm_lr2nzR6** ("Source data for an algorithm-choice coding bench", workspace folder `gen_art_dataset_1`). The repository publishes it as a sibling folder. `bench/common/build.py` reads it through one constant, `DEP`:

- the default is `../gen_art_dataset_1`;
- the environment variable `DEP_DATASET_DIR` overrides it.

Only its `full_data_out.json` is read, by `method.py extract`. No user-uploaded file is used: the run's upload folder was empty.

The heavy folders `.venv/` (14 GB) and `.cache/` are not published. `restore.sh` recreates `.venv/` and downloads the model weights into the Hugging Face cache.

## 2. System, Python and libraries

**What was used**

- OS and hardware: Debian 12 container on Linux 6.8, 6 CPUs (cgroup quota), 28 GB RAM. One **NVIDIA RTX 2000 Ada Generation, 16 GB VRAM** (compute capability 8.9), driver 595.91 / CUDA 13.2.
- No C compiler is installed (no gcc/cc/clang), which matters for vLLM; see section 4.
- Tools: uv 0.6.14. Python **3.12.14**, both for the venv and for the sandbox interpreter that runs candidate programs (`python3.12 -I -S`).

**On Ubuntu 22.04 / 24.04**

```bash
sudo apt-get update && sudo apt-get install -y git curl ca-certificates
curl -LsSf https://astral.sh/uv/0.6.14/install.sh | sh
uv python install 3.12.14
uv venv .venv --python=3.12.14
uv pip install --python .venv/bin/python -r requirements.txt    # or: bash restore.sh
```

- `pyproject.toml` and `requirements.txt` pin all **160** installed packages at their exact versions (from `uv pip freeze`; a uv venv has no `pip`).
- The direct dependencies:

  | package | version |
  |---|---|
  | vllm | 0.11.0 |
  | torch | 2.8.0 (cu128) |
  | transformers | 4.57.1 |
  | rapidfuzz | 3.14.6 |
  | numpy | 2.2.6 |
  | scipy | 1.18.1 |
  | loguru | 0.7.3 |
  | openai | 3.35.1 |
  | jsonschema | 4.26.0 |
  | tenacity | 9.2.1 |
  | psutil | 7.2.2 |

- What was actually run: `uv pip install vllm==0.11.0 rapidfuzz numpy scipy loguru openai jsonschema tenacity psutil`. That pulled transformers 5.20.2 and a torch tree with a missing `torch/__init__.py`, a broken link from the shared uv cache. It was repaired with:

  ```bash
  uv pip install --python .venv/bin/python --link-mode=copy --reinstall-package torch "torch==2.8.0" "transformers==4.57.1"
  ```

  The pinned files reflect the repaired environment.
- The sandbox interpreter is `python3.12` from `PATH`. Override it with `BENCH_SANDBOX_PYTHON`. The candidate programs need only the standard library.

## 3. Models, data and environment variables

| what | how |
|---|---|
| Qwen3-8B | `hf download Qwen/Qwen3-8B-FP8` (snapshot `220b46e3b2180893580a4454f21f22d3ebb187d3`, about 9.4 GB). The bf16 `Qwen/Qwen3-8B` (16.4 GB) does not fit in 16 GB of VRAM; this official block-FP8 checkpoint is used for both sampling and scoring |
| Llama pilot (optional) | `hf download RedHatAI/Meta-Llama-3.1-8B-Instruct-FP8` (snapshot `870a1177ed082c0ba5dbefd62573ab8f91803f6a`) |
| tokenizer for neutral-noun token counts | from the Qwen3-8B-FP8 snapshot above |
| dependency data | `../gen_art_dataset_1/full_data_out.json` (or `$DEP_DATASET_DIR/full_data_out.json`) |

Environment variables (names only):

| variable | needed for | notes |
|---|---|---|
| `OPENROUTER_BASE_URL`, `OPENROUTER_API_KEY` | the LLM judges | not needed to re-run on the published data: every judge answer is cached in `data/judge_cache.jsonl` |
| `HF_HOME` / `HF_HUB_CACHE` | model cache location | optional |
| `HF_TOKEN` | Hugging Face downloads | optional; both checkpoints are public |
| `DEP_DATASET_DIR` | location of the dependency folder | optional |
| `BENCH_SANDBOX_PYTHON` | sandbox interpreter | optional |
| `TORCH_COMPILE_DISABLE=1` | GPU jobs | set by the code too, together with `VLLM_TEST_FORCE_FP8_MARLIN=1`, `VLLM_NO_USAGE_STATS=1` and cache directories under `.cache/` |

## 4. Commands, in the order they were run (UTC, 2026-10-20)

Use `.venv/bin/python` (written `PY` below). The seeds are fixed in code:

- base 20261020;
- pilot: `1000·task_idx + s`;
- association: `10^5 + 100·mode_idx + s`;
- forced: `10^6 + 1000·mode_idx + 10·round + k`;
- descriptive variant: slot `k = 9` of that grid;
- gold-set sampling: `20261020 + Stage-A index`;
- holdout: `20261020 + 1000·round + index`;
- tests: `20261020 + task index`.

Decoding:

- T = 1.0, top_p = 1.0, top_k = -1, min_p = 0, repetition_penalty = 1.0;
- max_tokens 1024 (association: 96);
- Qwen3 chat template with `enable_thinking=False`;
- explicit SamplingParams and `generation_config="vllm"`, so nothing is inherited from the checkpoint.

vLLM sampling is not bit-reproducible across batch compositions. A rerun of the GPU jobs gives different samples drawn from the same distribution. The published `data/*_raw.jsonl` are the samples actually used.

| # | time | command | what it does, runtime |
|---|---|---|---|
| 1 | 03:15 | `uv venv ...; uv pip install ...` (section 2) | about 9 min with the torch repair |
| 2 | 03:14 | `hf download Qwen/Qwen3-8B-FP8` | about 1 min |
| 3 | 03:34 | `PY method.py specs` | freezes spec v1 for 13 tasks into `bench/<task>/spec.json`; first `commitments.log` line (`spec_v1`) |
| 4 | 03:36-03:57 | `PY method.py gen --job A --max-num-seqs 48 --gpu-util 0.90` | **Two failed launches.** (i) Triton could not build its driver (no C compiler) → `enforce_eager=True` + `VLLM_TEST_FORCE_FP8_MARLIN=1` (weight-only FP8 Marlin kernels). (ii) vLLM's logprob-rank op is `torch.compile`d → `TORCH_COMPILE_DISABLE=1`. Logs: `logs/jobA_failed_*.out` |
| 5 | 03:57-04:11 | same command | **GPU job A**: mini-gate (10 pilot samples, 100% code extraction), then pilot 13 × 50, association 54 × 20, forced 54 modes × 5 paraphrases (ids 0-4) × 8 rounds = 2,160. 730 s of generation; KV cache 31,040 tokens |
| 6 | 04:00 | `PY method.py extract` | writes `data/extract/` from all 10 dependency datasets, about 2 s |
| 7 | 04:02-04:19 | `PY method.py build --workers 4`, then `PY method.py build --tasks T06,T13,R2,T11,T08 --workers 4` | hidden tests, references, per-case limits, mutant checks, HumanEval+ smoke, exponential brute force. Fixes before the second call: sandbox interpreter path; T13's widest stress case n=1500 → 800 (interval-tree reference had used 0.367× the limit); R2 shuffled-edge forests (a mutant survived); a T06 mutant that was actually correct replaced; HumanEval+ smoke test run with the venv interpreter (its tests import numpy) |
| 8 | 04:32-04:44 | `PY method.py score` | **GPU job B**, first try: consistency checks, then 3,100 scored pairs before a CUDA OOM in the prompt-logprob logits (`max_num_batched_tokens` 8192) |
| 9 | 04:41-04:48 | `PY method.py label --workers 5` | tests, AST, runtime trace and scrub check for 2,810 attempts (400 s). At that point the CLI ran only this labelling; the re-trace with stored features (`bench.common.retrace.retrace_all`, about 5 min) was run as a one-off call. Today `label` runs both. The runtime rules were revised from feature dumps of the references (`results/reference_traces.json`) before the first combine |
| 10 | 05:12-05:42 | `PY method.py score --gpu-util 0.75` (`max_num_batched_tokens` 2048) | job B resumed: 9,860 more pairs, 1,803 s, about 1,680 tok/s |
| 11 | 05:14 | `PY method.py label --combine-only` | judge (gemini-2.5-flash-lite) on the 209 runtime/AST disagreements; writes `data/samples_pilot.jsonl` and `data/samples_forced.jsonl` |
| 12 | 05:19-05:22 | `PY method.py order --stage A` | association map (lexicon, plus the judge on 61 answers), nominations, **Stage-A order committed** |
| 13 | 05:25-05:27 | `PY method.py gate` | gold sets plus 2 judges and a tie-break for 13 tasks. 11 pass; T03 and T13 fail round 0 |
| 14 | 05:30 | `PY method.py gate --tasks T03,T13 --revise 1` | revision round 1 (rules revised in `bench/common/rtrules.py`), 6-program holdout. Both pass |
| 15 | 05:42-05:48 | `scripts/chain_jobC.sh` → `PY method.py gen --job C` | **GPU job C**: 420 top-ups from `data/topup_plan.json` (rounds 8-11 of ids 0-4 for modes with M_j < 30; descriptive variant × 20 for modes with adherence < 0.3) |
| 16 | 05:50-06:11 | `scripts/chain_after_C.sh` | `PY method.py label --workers 4` (top-ups); `PY method.py score --gpu-util 0.75` (3,080 new pairs, 584 s); `PY method.py gen --job D --model RedHatAI/Meta-Llama-3.1-8B-Instruct-FP8 --tasks <Stage-A order> --n-pilot 50` (**GPU job D**, 650 Llama samples) |
| 17 | 05:46-05:52 | `PY method.py build --tasks T14 --workers 3`, then `PY method.py label --retest T14` | T14 hidden tests extended 25 → 38; all 230 T14 attempts re-tested (0 pass-status changes) and re-combined |
| 18 | 06:02 | `PY method.py frlp` | final FRLP sets, then cells and validity |
| 19 | 06:05 | `PY method.py order --stage B` | Stage-B order committed |
| 20 | 06:09 | `PY method.py freeze` | the first 12 gated tasks in Stage-A order frozen (`bench/commitment.json` plus a chain entry) |
| 21 | 06:19 | `PY method.py label --sources samples_llama_pilot_raw.jsonl --llama --workers 5` | Llama pilot labelled with the gated labellers |
| 22 | 06:21, 06:46 | `PY method.py report` | `method_out.json`. Re-run after the TheAlgorithms extraction fix (code was in `input`) |
| 23 | 06:21-07:20 | `PY scripts/verify_outputs.py`, `PY scripts/tracer_unit_tests.py`, `PY scripts/ast_fixture_check.py`, `PY scripts/rederive_headlines.py` | checks (section 5) |
| 24 | 06:21 | `aii_json_format_mini_preview.py --input method_out.json` | `full_` / `mini_` / `preview_method_out.json` |

Ordering matters for exact reproduction:

- The gate (steps 13-14) sampled each gold set's forced programs **before** the top-ups existed. Re-running `gate` after step 15 draws from a larger pool and gives different gold sets.
- To re-derive every number from the published samples without any GPU or API call, run: `PY method.py label --combine-only` (judge answers come from the cache), then `order --stage A`, `gate`, `gate --tasks T03,T13 --revise 1`, `frlp`, `order --stage B`, `freeze`, `report`.
  - That reproduces the frozen hashes only on a `data/` tree as published.
  - `freeze` appends a new chain entry.

Total GPU time was about 1.4 h on the RTX 2000 Ada. OpenRouter judge spend was **$0.142** over 1,124 calls, with every call logged in `logs/openrouter_spend.jsonl`.

## 5. What a reader should get

| output | expected content |
|---|---|
| `method_out.json` (schema `exp_gen_sol_out`, validated) | dataset `bench_candidates`: 13 examples, one per task, with the metadata fields listed in README.md. Dataset `frlp_baseline_cells`: 54 examples |
| `metadata_modal_share` | **1.00 for 12 tasks, 0.98 for R6** (Wilson 95% [0.929, 1.0] and [0.895, 0.996]). Every task has `collapse_flag=true` and `presence_flag=false` |
| `metadata_gate.gold` | kappa(runtime, AST) between 0.84 (T14) and 1.00. Runtime vs adjudicated ≥ 0.91. Both labellers 100% on the references |
| FRLP | L_corr of the pilot mode between −0.86 (T11) and 2.44 (R3). S in [0.3, 3] for 11/13 tasks (R2 10.9 and R3 11.4 overshoot). 34/54 cells have ESS < 5 |
| `metadata.orders` | Stage A: T03, T04, T06, T05, T10, R1, T08, R3, T13, R6, T14, T11, R2. Stage B: T08, T03, T04, T06, T14, T05, T10, T13, R3, R6, R2, R1, T11. Kendall τ = 0.54 |
| `metadata.frozen_tasks` | the first 12 in Stage-A order; R2 is `excluded` by the 12-task cap |
| `scripts/verify_outputs.py` | `"problems": []`: 13 tasks recounted, 4,310 prompts audited with 0 ban hits, 146 committed file hashes match, hash chain intact |
| `results/rederive_headlines.json` | the independent re-derivation summarised in the table below |

`results/rederive_headlines.json` contains:

| check | result |
|---|---|
| modal shares | 13/13 match |
| labeller-free regex signatures of the modal mechanism | 1.00 on 11 tasks; R6 0.98 (a real linear scan); T14 0.94 (3 buggy sort-the-counts variants the regex misses) |
| kappa | 13/13 match; with shuffled AST labels no task reaches 0.8 |
| FRLP L_corr | 54/54 cells match |
| π vs uniform log score | beats uniform on 13/13; fails on 0/13 under random-label and permuted-L_corr placebos |
| judge share | 0.084 |
| runtime-AST agreement | 0.910 |
| spend | $0.142 |
| Llama modal shares | match |
| association nominations | 13/13 |
| Kendall τ | 0.538 |

No paper exists at this step. A downstream write-up should cite these files and fields: the pilot table, the gate table, the FRLP cells and the two orders.

Not independently re-derived:

- the proximity distances (canonical-token Levenshtein; the "proximity differs from association on 10/13" count is re-derived only from the reported nominations);
- the per-case test outcomes (re-running the same sandbox would not be a different code path);
- the scrub verification flags.
