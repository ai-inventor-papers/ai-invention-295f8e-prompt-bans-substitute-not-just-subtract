# Reproducing this artifact (bans, token vetoes and long-form novelty on Qwen3-8B)

This file records what was **actually run** on 2026-10-20/21 (UTC), in order. That includes the launches that
failed and how each was fixed. Every path below is relative to this folder.

## 1. Get the artifact

The workspace is published as one folder of a public GitHub repository:

```bash
git clone <URL of the published repository>
cd <repository>/<folder of this artifact>      # the folder that contains method.py and this file
```

**Inputs from other artifacts.**
- Everything this artifact read from the run's iteration-2 experiments is already copied into `inputs/`, with
  `inputs/SHA256SUMS`. This covers the frozen bench (`inputs/bench/`) and the path-task suite (`inputs/suite/`). It
  also covers their data:
  - exp7: `inputs/exp7/`;
  - exp8: `inputs/exp8/`;
  - exp9: `inputs/exp9/`;
  - exp11: `inputs/exp11/`.
- You need nothing else for them. `src/phases.py s0` re-checks the bench copies against `inputs/bench/commitment.json`.
- The one declared dependency is the dataset artifact **art_j3Rm_lr2nzR6** ("Source data for an algorithm-choice
  coding bench"). The repository publishes it as the sibling folder `gen_art_dataset_1`. It is read through ONE
  constant, `DEP_DATASET` in `src/config.py`:
  - the default is `../gen_art_dataset_1`;
  - the environment variable `DEP_DATASET_DIR` overrides it.
- Only `full_data_out.json` of that dataset is read, by `src/audit.py corpus` and `src/dep_usage.py`. Their outputs
  (`inputs/known_solutions.jsonl`, `results/dependency_usage.json`) are already in this folder.
- No user-uploaded file was used: the run's upload folder was empty.

## 2. System, Python and libraries

**What was used**

| item | value |
|---|---|
| OS | Debian 12 container on Linux 6.8 (Ubuntu 22.04/24.04 works the same) |
| GPU | **1 x NVIDIA L4, 23 GB VRAM** (compute capability 8.9); driver 595.91.07 (CUDA 13.2 driver; torch uses its own cu128 runtime) |
| CPU / RAM | 6 CPUs (cgroup quota 5.1), 57 GB RAM (cgroup limit) |
| Python | **3.12.14**, both for `.venv` and for the candidate-program sandbox, which runs `python3.12 -I -S` and finds `/usr/local/bin/python3.12` or `python3.12` on `PATH`. `SANDBOX_PYTHON` overrides it for the path suite and `BENCH_SANDBOX_PYTHON` for the bench. |
| package manager | uv 0.6.14 |
| C compiler | none present. Not needed: vLLM runs eager with torch.compile off (section 4). |

**Install**

```bash
# system: an NVIDIA driver that supports CUDA 12.8 wheels, python3.12, uv (https://docs.astral.sh/uv/)
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r pyproject.toml      # ~2 min with a warm uv cache
```

- `pyproject.toml` pins all **180** installed packages exactly, for example `vllm==0.11.0`, `torch==2.8.0`,
  `transformers==4.57.6`, `numpy==2.2.6`, `scipy==1.18.1`, `rapidfuzz==3.14.6`, `ijson==3.4.0`, `openai==3.35.1`.
- It equals `requirements.lock.txt`, the output of `uv pip freeze --python .venv/bin/python`. A uv venv has no `pip`
  binary, so `.venv/bin/pip freeze` is not available; the uv equivalent was used.
- `restore.sh` runs the install and downloads both model checkpoints.

## 3. Models, keys and environment variables (names only)

| what | how |
|---|---|
| `Qwen/Qwen3-8B` (bf16), revision `b968826d9c46dd6066d109eabc6255188de91218` | `huggingface-cli download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218` |
| `Qwen/Qwen3-8B-FP8` (snapshot `220b46e3b2180893580a4454f21f22d3ebb187d3`) | `huggingface-cli download Qwen/Qwen3-8B-FP8` (took 46 s here) |
| `HF_HOME` / `HF_HUB_CACHE` | where the weights live; `src/config.py → model_dir()` looks for the snapshots there |
| `HF_TOKEN` | optional, for the download |
| `OPENROUTER_BASE_URL`, `OPENROUTER_API_KEY` | every LLM call (labeller judges, novelty-audit judges, claim extraction) goes through OpenRouter |
| `DEP_DATASET_DIR` | location of the dataset artifact art_j3Rm_lr2nzR6 (default `../gen_art_dataset_1`) |
| `TORCH_COMPILE_DISABLE=1`, `VLLM_TEST_FORCE_FP8_MARLIN=1`, `VLLM_NO_USAGE_STATS=1` | set by `src/server.py` for the vLLM server |
| `PYTHONDONTWRITEBYTECODE=1` | optional; keeps `__pycache__` out of the folder |
| `S4_PORT_BF16`, `S4_PORT_FP8` | optional server ports (defaults 8231, 8232) |

Cost:
- OpenRouter spend was **USD 0.489** over 1,159 calls (`results/costs.json`).
- Every response is cached in `data/llm_cache.jsonl`, keyed by prompt hash, so re-running the analysis spends
  nothing.
- `GET <base_url>/key` returned HTTP 403 through the proxy, so spend was tracked from `usage.cost`.

## 4. What was run, in order (UTC)

Shared settings:
- **Decoding**: T = 1.0, top_p = 1.0, top_k = -1, min_p = 0, repetition penalty 1.0, sent explicitly with every
  request. `--generation-config vllm` stops the checkpoint's defaults from applying.
- **max_tokens**: 1,024 for short programs, 4,096 for long-form, a 16,384 thinking cap plus a 4,096 answer for
  thinking-on.
- **Seeds**: base `20261021` plus per-arm offsets (`src/config.py`): walk `+2e6 + 1e4·task + 1e3·step + 1e2·round + i`;
  sham `+2.5e6`; fixed TOP5 `+2.6e6`; LOS `+3e6 + 1e4·task + 1e3·S + i`; two-step `+4e6`; long-form off `+5e6`; on
  `+6e6`; unit tests `+9e6`.
- **Task index**: T1 0, T2 1, T03 2, T04 3, T06 4, T10 5.

**vLLM servers** (`src/server.py`, PID-managed). Shared flags: `--dtype bfloat16 --gpu-memory-utilization 0.92
--enable-prefix-caching --max-num-batched-tokens 4096 --enforce-eager --seed 0 --generation-config vllm
--logits-processors veto:NGramVeto`. The veto is `src/veto.py`, loaded from `src/` on `PYTHONPATH`. Per server:
- **bf16**: `--max-model-len 4608 --max-num-seqs 32`. KV cache 33,168 tokens. Load took 355 s, mostly imports from
  network storage.
- **FP8**: `--max-model-len 20480 --max-num-seqs 96`. KV cache 77,216 tokens. Load took 230 s. Weight-only FP8 Marlin
  kernels.

```bash
export PYTHONDONTWRITEBYTECODE=1
# 20:40-20:46  bf16 server (smoke test: 40 short programs at 337 tok/s; a veto smoke test)
.venv/bin/python src/server.py bf16 start 4608 32
# 21:03        S0: bench commitment check (4/4 tasks verified), inputs/SHA256SUMS (343 files)
.venv/bin/python src/phases.py s0
# 21:12-21:14  veto unit tests u1-u4 + n-gram unit tests (results/veto_unit_tests_bf16.json; all pass, u2 17/20)
.venv/bin/python src/phases.py unit_bf16
#              -> u1 showed an indentation-tailed n-gram bypassed by re-indenting; n-gram candidates were made lexical
#                 (no whitespace-only token) and sham candidates keyword-free BEFORE any walk sample (deviations D3, D4)
# 21:27-21:38  phase A: T1/T2 walk + T1/T2 shams + fixed TOP5 (bf16); forecasts committed at 21:38
.venv/bin/python src/phases.py A
#              -> crashed when the queued two-step batch hit a client bug (asyncio semaphore bound to an old event
#                 loop; nothing of that batch was generated). Fixed in src/client.py, then:
# 21:41-21:49  T1/T2 two-step bans from the committed forecasts
.venv/bin/python src/phases.py two_step path bf16
# 21:31-21:36  long-form stage 10 (LF1-T2, bf16, concurrently with phase A): 84 tok/s -> projected 220 min for all 500
#              -> the committed 'split' branch; 21:41-22:07 the remaining bf16 cells (restarted once at concurrency 16)
.venv/bin/python src/longform.py bf16
# CPU, meanwhile: labeller re-check, known-solution corpus
.venv/bin/python src/recheck.py
DEP_DATASET_DIR=../gen_art_dataset_1 .venv/bin/python src/audit.py corpus
# 22:06-22:26  scripts/chain_phase_b.sh: bf16 server stop -> FP8 server start (20480, 96) -> FP8 unit tests
#              (u2 19/20) -> phase B (bench walk + T04/T10 shams; bench forecasts committed 22:19:56 -> 850 LOS
#              prompts; two-step forecasts 22:24:37 -> 400 two-step prompts) and, concurrently, FP8 thinking-off
#              long-form (22:13-23:06: LF1-T2 cross-check copy + T03/T04/T06 x LF1/LF2, N = 50 each)
scripts/chain_phase_b.sh
# 22:26-23:19  scripts/chain_thinking.sh: thinking-on floor, T1/T2 x LF1/LF2, N = 10 each (40/40 traces completed)
scripts/chain_thinking.sh
# 22:30-22:36  an extension process (T1/T2 to N = 25 + bench cells) was started and stopped when the KV cache
#              saturated (nothing written); 23:07-00:05 the bench cells alone (60/60 traces completed):
.venv/bin/python src/longform.py fp8_on T03:0-10,T04:0-10,T06:0-10 8
.venv/bin/python src/server.py fp8 stop
# audit and claims (OpenRouter)
.venv/bin/python src/audit.py controls     # round 0 failed (A 2/6, B 3/6): prompt context + 2 controls fixed (D13);
                                           # round 1 passed: A 5/6, B 5/6
.venv/bin/python src/audit.py pool && .venv/bin/python src/manual.py sheet && .venv/bin/python audit/apply_manual.py
.venv/bin/python src/audit.py claims       # (pool / sheet / manual rules repeated as new long-form data arrived)
.venv/bin/python src/dep_usage.py
# analysis and outputs (CPU)
.venv/bin/python src/analysis.py && .venv/bin/python src/figures.py && .venv/bin/python src/rederive.py
.venv/bin/python method.py outputs
python <aii-json skill>/scripts/aii_json_format_mini_preview.py --input method_out.json   # full_/mini_/preview_
.venv/bin/python scripts/build_readme.py && .venv/bin/python scripts/sanitize_logs.py
.venv/bin/python scripts/verify_headlines.py
```

`method.py` wraps the same steps (`method.py s0 | server | unit | phase | longform | audit | analyze | outputs`).
With no argument, `uv run method.py` rebuilds `method_out.json` from the saved per-sample data and results. It
took about 1 min, including uv's environment sync, which also writes `uv.lock`. It needs no GPU and no API key.
Every example carries `predict_*` fields:
- the baseline default (all rows);
- the committed forecast (walk and sham rows);
- the survivor and the C3 forecast (LOS rows);
- WALK2 / ASSOCIATE / SNAPBACK (two-step rows);
- judge A's code-mechanism guess and novelty-claim verdict (long-form rows);
- both judges' classes (audit rows).

**Runtime.**
- GPU wall clock was about 3 h 25 min (20:40-00:06).

| job | generations | wall clock | throughput |
|---|---|---|---|
| bf16 long-form | 125 | 31 min | 84-167 tok/s |
| FP8 thinking-off long-form | 350 | 52 min | 228 tok/s |
| thinking-on, T1/T2 | 40 | 52 min | 110 tok/s |
| thinking-on, bench | 60 | 57 min | 129 tok/s |

- Short-arm batches on FP8 reached about 860 tok/s at 96 concurrent requests.
- Labelling (5 sandbox workers) ran in about 1-2 min per 300 programs.
- Executor wall clock was about 6 h, including writing the code.

**Determinism.**
- vLLM batches are not bit-reproducible: unit test u2 gave 17/20 (bf16) and 19/20 (FP8) token-identical outputs for
  the same seeds in different batches. A re-run reproduces the distributions, not the exact token streams.
- With `data/label_cache.jsonl` and `data/llm_cache.jsonl` present, re-labelling the published programs is exact and
  free.

## 5. What you should get

| result | file | value |
|---|---|---|
| veto exactness | `results/walk.json`, `scripts/verify_headlines.py` | 0 banned-sequence occurrences in 1,450 vetoed generations |
| token walk | `results/walk.json`, `figures/fig1_token_walk` | STALLED on all 6 tasks (step 1 on T1, T2, T03, T04, T10; step 2 on T06, after rung 2 = sort+adjacent) |
| sham control | `results/walk.json → sham_vs_distinctive`, `fig5` | default kept: T1 50/50, T2 50/50, T04 49/50, T10 44/44 valid; T2 pass 50/50 vs 19/46 under the distinctive veto (Fisher p ≈ 8e-12) |
| C3 | `results/c3.json`, `fig2` | **DISCONFIRMED**: T03 quickselect will 1.00, T10 BFS 1.00; confirm T2 Floyd 0.00, T03 size-k heap 0.00, heapify-pop 0.00, T06 value bisection 0.00; T06 Floyd 0.14 neither; T04 untestable |
| T03 LOS(full sort) | `data/samples_los.jsonl` | quickselect 50/50 (priming by the ban list) |
| two-step bans | `results/reach.json → two_step` | compliance T1 0.02, T2 0.01, T04 0.14, T03 1.00, T06 0.96, T10 1.00 |
| list independence (preregistered) | `results/list_independence.json` | T04 p = 0.033: the prediction fails. The placebo with shuffled groups gives median p 0.51. |
| long-form | `results/longform.json`, `fig4` | 575 outputs; 84% claim a new algorithm; NOVEL = 0 (upper bound 0.058 per N = 50 cell) |
| novelty audit | `results/novelty_audit.json`, `results/manual_audit.json` | 53 audited (38 correct off-catalogue): 31 labeller misses, 10 catalogue variants, 12 degenerate, 0 novel; κ(A, B) = 0.27 |
| bf16 vs FP8 | `results/fp8_crosscheck.json` | JS 0.033 bits vs null p95 0.068 (p = 0.35) |
| re-derivation | `results/rederive.json`, `results/verify_headlines.json` | 0 mismatches; tests fail on placebo input as they should |

`README.md` gives these numbers with their context. No paper existed when this was written: the paper is written
downstream and should carry the values above. `method_out.json → metadata` holds every analysis, the deviation
list (D1-D17), `not_run` and the commitment chain.
