# Reproducing this artifact

This page describes what was **actually run** to produce the results in this folder, in order, including the crash,
the fixes and the reruns. Every path is relative to this folder.

There are two ways to reproduce it:

- **Path A, CPU only, exact.** Re-runs the analysis from the published raw files and gives the same numbers to the
  last digit.
- **Path B, full regeneration.** Needs a GPU. It reproduces the distributions; individual tokens can differ because
  bf16 numerics depend on batch composition.

## 0. Get the artifact

This folder is one folder of a public GitHub repository. Clone the repository and `cd` into this folder.

```bash
git clone <repository-url>
cd <repository>/<this-folder>
```

Inputs produced by other artifacts:

- **Dataset artifact `art_j3Rm_lr2nzR6`** ("Source data for an algorithm-choice coding bench"). The repository
  publishes it as a sibling folder. The code reads its `full_data_out.json` through **one** setting:
  - the environment variable `AII_DEP_DATASET`, or
  - the default relative path `../art_j3Rm_lr2nzR6/full_data_out.json` (`src/ws.py: DEP_DATASET_DEFAULT`).

  Only two things need it, and both outputs are already in this folder:
  - the 718-noun bank extraction (output `data/noun_bank.json`);
  - the scrubber stress test (output `results/scrub_stress.json`).
- **The canonical suite of exp1 (`art__skdlFp_o3e9`).** Its task texts, hidden tests, 22 reference implementations,
  sandbox harness, labeller, gold set and frozen prompts are **copied into `canon/`**, so no external read is needed.
  `canon/SHA256SUMS` lists the sha256 of every copied file. To check the copy against a sibling exp1 folder, run
  `cd <exp1 folder> && sha256sum -c <this folder>/canon/SHA256SUMS`. The copy was verified this way (52/52 OK) when it
  was made.

No user-uploaded material was used: the run's upload folder was empty.

## 1. System, Python and libraries

The original run used:

| item | value |
|---|---|
| Container | Debian 12 (bookworm) |
| GPU | 1 x NVIDIA RTX 4090, 24 GB; driver 595.91.07; torch wheels built for CUDA 12.8 |
| CPU | AMD Ryzen 9 7950X, 14-vCPU cgroup quota |
| RAM | 56 GB |
| C compiler | none installed |
| Python | CPython 3.12.14 at `/usr/local/bin/python3.12` |
| uv | 0.6.14 |

The steps are the same on Ubuntu 22.04/24.04 with an NVIDIA driver that supports CUDA 12.8:

```bash
sudo apt-get update && sudo apt-get install -y python3.12 python3.12-venv curl git   # or use uv's own Python 3.12
curl -LsSf https://astral.sh/uv/install.sh | sh
./restore.sh          # = uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml
```

The environment:

- `pyproject.toml` pins **all 169 packages installed in `.venv`** with `==`. The list is identical to
  `uv pip freeze --python .venv/bin/python`; a uv venv has no pip binary. Key pins:
  - `vllm==0.11.0`
  - `torch==2.8.0` (cu128)
  - `transformers==4.57.6`
  - `huggingface-hub==0.36.2`
  - `numpy==2.2.6`, `scipy==1.18.1`, `pandas==3.0.6`, `pyarrow==21.0.0`
  - `rapidfuzz==3.14.1`, `openai==3.35.1`, `loguru==0.7.3`, `matplotlib==3.11.2`
- Installing took about 4 minutes.
- **Candidate programs** (the model's code) run in a stdlib-only CPython 3.12 with `-I -S`; see
  `canon/tasks/harness.py`. It uses `/usr/local/bin/python3.12`, else `/usr/bin/python3.12`, else `python3.12` on
  PATH. Set `SANDBOX_PYTHON` to override.

## 2. Downloads, environment variables and keys (names only)

**Model.** `meta-llama/Llama-3.1-8B-Instruct` at revision `0e9e39f249a16976918f6564b8830bc894c89659`:
safetensors and configs only, about 16 GB.

- The repository is gated, so `HF_TOKEN` must belong to an account with access.
- `.venv/bin/python scripts/download_model.py` downloaded it in 25 s; the original run invoked it as `uv run`. It
  falls back to `unsloth/Llama-3.1-8B-Instruct` on a gated/401/403 error; that fallback was not needed.
- The weights go to the Hugging Face cache (`HF_HOME` / `HF_HUB_CACHE`). `src/ws.py: model_path()` resolves them from
  the repo id and commit recorded in `results/model_download.json`.
- Shard sha256s and the chat-template string are in `results/model_record.json`.

| variable | needed for |
|---|---|
| `HF_TOKEN` | model download (gated repo) |
| `OPENROUTER_BASE_URL`, `OPENROUTER_API_KEY` | the blind judge: `openai/gpt-4.1-mini` on runtime/AST disagreements, and `google/gemini-2.5-flash` for the label audit |
| `AII_DEP_DATASET` | optional; path to `art_j3Rm_lr2nzR6`'s `full_data_out.json` |
| `SANDBOX_PYTHON` | optional; the stdlib-only interpreter for candidate programs |
| `AII_SKILLS_DIR` | optional; the AI Inventor skills folder that holds `aii-data-fig-gen` |

The judge needs OpenRouter (USD 0.49 in total here). Cached judge answers are in `data/judge_cache.jsonl`, keyed by
model and code sha256, so a rerun on the same programs makes no paid calls.

`aii-data-fig-gen` is AI Inventor's figure tooling, used only by `src/figures.py`. Every figure's data is in
`results/*.json`, and the generator-made figures also have their spec in `figures/*.json`.

## 3. What was run, in order

Approximate wall-clock times are from `logs/timing.jsonl` and the stage logs; seeds follow the table. All commands
run from this folder.

### Seeds and frozen configuration

| what | seed or rule |
|---|---|
| vLLM requests | per-request `seed = int(sha256(f"{task}\|{cond}\|{tpl}\|{sample_id}")[:8], 16)` (`src/config.request_seed`); server `--seed 0` |
| vLLM sampling | T = 1.0, top-p 1.0, top-k off, min-p 0, all penalties neutral, `max_tokens` 1024 (free-form: 48), stop ids `[128001, 128008, 128009]`, `--generation-config vllm` |
| implementation halves | `random.Random(f"half\|{task}\|{j}")` |
| random-edit directions | `torch.Generator().manual_seed(0)` for k = 1-3 and `manual_seed(1)` for k = 4-6 |
| bootstrap | B = 2000, `numpy.random.default_rng(0)`; sensitivities B = 400, seed 1 |
| label audit | `random.Random(20261020)`, supplement `20261021` |
| placebos | `audit/rederive.py` seed 123; `audit/rederive_headlines.py` seed 0 |

Frozen configuration (`results/frozen_config.json`, sha in `commitments.log`):

- SHARED PROTOCOL v2 templates W1-W5;
- the v2 display names;
- the nonce phrase 'the Zorblax method';
- the novelty instruction;
- 10 forced paraphrases;
- the Llama-3.1 default chat template with `date_string='26 Jul 2024'`;
- neutral nouns 'man' (half 1) and 'guy' (half 2), all 718 bank nouns being single Llama tokens;
- padding with `' -'` tokens.

### S0: setup (CPU)

```bash
.venv/bin/python scripts/download_model.py                          # 25 s
python3 -I scripts/extract_dependency.py                            # noun bank + dataset inventory (needs AII_DEP_DATASET)
.venv/bin/python -m src.label_worker recheck                        # labeller re-check, about 1 min
#   -> results/labeller_recheck.json: 22/22 references, combined vs adjudicated 0.966, no judge calls
```

### S1: vLLM session A (GPU)

Start the server:

```bash
nohup scripts/serve_vllm.sh > logs/vllm_server_A.log 2>&1 &         # about 3.5 min to start
```

The first start crashed on the first request that asked for logprobs: Triton could not build without a C compiler.
`TORCHDYNAMO_DISABLE=1` was added to `scripts/serve_vllm.sh` together with `--enforce-eager`, and the server was
restarted. The rows from the crashed attempt were discarded.

Then generate and label:

```bash
.venv/bin/python -m src.gen_client --phase A1 --limit 10 --keep-logprobs-first 8   # stage 10 + T3 logprobs
.venv/bin/python -m src.label_worker label --phases A1              # smoke labels inspected by hand
.venv/bin/python -m src.gen_client --phase A1                       # 190 more, 45 s
.venv/bin/python -m src.gen_client --phase A2                       # forced round 1, 440, about 2.5 min
.venv/bin/python -m src.gen_client --phase A3                       # free-form, 220, 46 s
.venv/bin/python -m src.label_worker label --phases A1
.venv/bin/python -m src.gen_client --phase A4                       # modal ban, mention twin, listall; 400 in 113 s
.venv/bin/python -m src.label_worker label --phases A2,A3,A4        # about 3 min (judge)
.venv/bin/python -m src.gen_client --phase A5                       # two-step ban, 100
.venv/bin/python -m src.gen_client --phase A6                       # forced top-up round 2, 240
.venv/bin/python -m src.label_worker label --phases A5,A6
.venv/bin/python -m src.gen_client --phase A6                       # round 3; descriptive variant for biBFS, biDijkstra, Dial
.venv/bin/python -m src.label_worker label --phases A6
```

Stop the server by killing its PIDs; they are printed in its log.

### S2: forced set, scrub, validate (CPU)

```bash
.venv/bin/python -m src.forced_set                                  # about 1 min
```

This writes `data/forced_set.jsonl`, `results/forced_set_summary.json`, `results/coverage.json` and
`results/t3_token_check.json`.

### S3: HF session B (GPU)

```bash
.venv/bin/python -m src.score_session --phase B                     # about 6 min
```

This runs T3/T4, scores the proposal and the baselines, and selects the non-default bans. The first run used a bf16
LM head. T4 then showed up to 0.74 nats per program, so it was stopped, its `frlp/parts` were deleted, the head was
moved to fp32 (`src/frlp.py`), and B was rerun.

### S4: vLLM session C (GPU)

```bash
nohup scripts/serve_vllm.sh > logs/vllm_server_C.log 2>&1 &
.venv/bin/python -m src.gen_client --phase C                        # 200 programs in 56 s, then stop the server
.venv/bin/python -m src.label_worker label --phases C
.venv/bin/python -m src.label_worker audit                          # 30 programs, gemini-2.5-flash
.venv/bin/python -m src.label_worker audit2                         # supplement: 20 programs (T1 'other' + T2)
```

### Freeze, then S5: HF session D (GPU)

```bash
.venv/bin/python -m src.test_analysis_c1                            # T9 synthetic tests, about 4 min, all pass
.venv/bin/python -m src.commit "freeze: S0.9 before the first S5 score"   # 01:59 UTC; first S5 score 02:02 UTC
.venv/bin/python -m src.score_session --phase D                     # about 24 min
```

Session D scores the matrices, the ban displacement, the six random edits (T7) and the route test (T8). There were
39,768 program scores in all (11.3M tokens) across sessions B and D.

### Checks and fixes after S5 (CPU)

```bash
.venv/bin/python -m src.test_prompts                                # T2 + results/model_record.json
.venv/bin/python -m src.forced_set                                  # rerun after the unparsable-program fix
AII_DEP_DATASET=<path> .venv/bin/python scripts/scrub_stress.py     # T5b on all 10 datasets of art_j3Rm_lr2nzR6
```

The `forced_set` rerun drops 8 programs whose original code does not parse; the other 248 programs are unchanged.

### S6: analysis (CPU)

```bash
.venv/bin/python -m src.run_analysis                                # about 2 min
.venv/bin/python -m src.test_frlp_sanity                            # T6
```

`run_analysis` computes the cells, gate, C1 under both references, nulls, bootstrap, sensitivities and diagnostics.
It was rerun three times after the recorded fixes in `commitments.log`; the primary numbers were identical each time.

### Audit, figures and outputs

```bash
.venv/bin/python audit/rederive.py                                  # T11: 34/34 match; placebo KS p 0.61
.venv/bin/python audit/rederive_headlines.py                        # 63/63 headline numbers match
.venv/bin/python -m src.figures                                     # needs AII_SKILLS_DIR (aii-data-fig-gen)
.venv/bin/python -m src.deviations
.venv/bin/python method.py outputs                                  # data/samples.jsonl, method_out.json
```

`method_out.json` was then validated against the `exp_gen_sol_out` schema, and the full/mini/preview variants were
written with AI Inventor's aii-json skill.

**Total logged compute:** about 0.64 GPU-hours, of which 11 min was vLLM generation and 27 min HF scoring, plus
model loading and server starts. OpenRouter spend was USD 0.492.

## 4. Path A: exact CPU-only re-analysis

```bash
./restore.sh
.venv/bin/python -m src.run_analysis && .venv/bin/python audit/rederive.py && .venv/bin/python audit/rederive_headlines.py
.venv/bin/python method.py outputs
```

## 5. What you should get

Each number below is followed by the file that holds it.

**Labeller re-check** (`results/labeller_recheck.json`):

- 22/22 references;
- combined vs adjudicated 0.966 on the eval gold;
- κ(runtime, AST) 0.753.

**Llama label audit** (`results/llama_label_audit.json`): agreement 0.78 over 50 programs, which is flagged.

**Baselines** (`results/collapse.json`; figures `figures/fig1a`-`fig1d`):

- T1: BFS 77 / DFS 20 / other 3, pass rate 0.20.
- T2: Dijkstra 92 / BF-SPFA 1 / other 7, pass rate 0.59.

**Modal bans** (`results/events.json`):

- T1: DFS 63 / BFS 29.
- T2: Dijkstra 43 / other 37 / BF-SPFA 18.

**FRLP gate: FAIL** (`results/frlp_gate.json`; figures `fig5`, `fig7`):

- (a) T1 default mass 0.433 fails; T2 passes at 0.966.
- (b) 0.591 nats/sample, which passes.
- (c) 7/10 hits, which fails.
- Median ESS 2.45.

**C1 on T1 only** (`results/c1.json`; figures `fig2`-`fig4`, `fig6`). T2 has no row with at least 3 survivors.

- Neutral reference: SHARE 0.804 (percentile CI 0.275-0.935); AIM 0.067 against a null q95 of 0.258 (p 0.349).
  Branch: **not resolved at this N**.
- Mention reference: **X-SPECIFIC BUT UNAIMED**.
- Not robust. No ladder: the mean cosine of the generic profiles is 0.14.

**Post-hoc diagnostics** (`results/bootstrap_diagnostics.json`):

- the basic interval for the neutral V_tot is [-15.1, 10.2];
- the bootstrap variance of gbar is 5-11x the replicate Σ.

**Sensitivities** (`results/sensitivities.json`).

**Route test** (`results/c1.json` → route; figure `fig8`): F_prompt 0.84 (CI 0.62-1.46), F_direct -0.21.

**Per-sample predictors** (`method_out.json` → `metadata.predictor_comparison_per_event`):

- Top-1 accuracy over 743 samples: FRLP 0.587, sampled ladder 0.699, association 0.522, latent ladder 0.506.
- Paired permutation test (`results/independent_rederivation_headlines.json`):
  - FRLP minus sampled ladder = -0.112 over all samples, p < 1e-4.
  - On single bans: +0.010, p 0.71.

These are the numbers for the Llama-replication section of the run's paper. They are descriptive: two tasks, one
model, and a failed FRLP gate.
