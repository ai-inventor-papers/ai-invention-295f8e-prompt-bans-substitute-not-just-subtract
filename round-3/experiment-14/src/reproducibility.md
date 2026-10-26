# Reproducing the exposure-ban experiment

This is what was actually run, in order, on 2026-10-20. Every path below is relative to this artifact's folder.

## 1. Get the artifact

The workspace is published as one folder of a public GitHub repository. Clone that repository and `cd` into this folder:

```bash
git clone <repository-url>
cd <repository>/<this-artifact-folder>      # the folder that holds method.py
```

The frozen bench this experiment uses is **exp11** of the same run (iteration 2, `gen_art_experiment_11`). The repository publishes it as a sibling folder. `exposure/core.py` locates it through one constant:

- the environment variable `EXP11_DIR`, if set;
- otherwise `../../../round-2/experiment-11/src`, relative to this folder (the run layout).

`method.py setup` copies exp11's `bench/` into `./bench_copy/` and verifies every committed sha256 before anything else runs. It also copies exp11's `data/judge_cache.jsonl` and `results/stageA_nominations.json`. The published folder already contains `bench_copy/`, `inputs/`, `predictions/`, `data/` and `results/`, so the analysis can be re-run without exp11.

No user-uploaded file is used.

## 2. System, Python and packages

- **OS / Python.** Debian 12 container (any recent Ubuntu works), Python 3.12.14, `uv` 0.6.14.
- **No C compiler on the original machine.** Triton and torch.compile cannot build kernels, so vLLM runs with `enforce_eager=True` and `TORCH_COMPILE_DISABLE=1`. The code sets this itself; on a machine with gcc nothing changes.

```bash
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r requirements.txt
```

`requirements.txt` and `pyproject.toml` pin all 174 installed packages: exp11's 160-package environment (vllm 0.11.0, torch 2.8.0+cu128, transformers 4.57.1, scipy 1.18.1, numpy 2.2.6, rapidfuzz 3.14.6) plus zss 1.2.0, pytest 8.4.2, matplotlib 3.10.7 and pandas 2.3.3. `bash restore.sh` does the install and the model download in one step.

## 3. Model, data and keys

- **Model.** `Qwen/Qwen3-8B`, bf16, revision `b968826d9c46dd6066d109eabc6255188de91218`, downloaded into the Hugging Face cache (about 16 GB):
  `hf download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218`.
- **Hugging Face variables.** The run used a shared cache through `HF_HOME` / `HF_HUB_CACHE`; set them as you like.
- **Judge.** `OPENROUTER_BASE_URL` and `OPENROUTER_API_KEY` are needed only for the blind judge (`google/gemini-2.5-flash-lite`, temperature 0). Every judge answer is cached in `data/judge_cache.jsonl`, keyed by model, task and code hash, so re-labelling the published programs makes no paid call.
- **Spend.** USD 0.096 over 1,229 calls (both stage-1 attempts included), logged in `logs/openrouter_spend.jsonl`.

## 4. Commands, in the order they were run

Hardware: one NVIDIA L4 (23 GB VRAM), 6 CPUs (cgroup quota), 57 GB RAM (cgroup limit).

```bash
.venv/bin/python method.py setup        # ~2 min CPU: bench copy + sha256 (158 hashes), labeller re-check (320 programs),
                                        #   defaults, eligibility (33 Y / 19 priority), COMMIT #0
.venv/bin/python method.py forecasts    # ~9 min CPU: shown pools (scrub + tests + labels), n-grams, allocation,
                                        #   PROXIMITY (2,972 Zhang-Shasha pairs on 6 processes), 775 rendered prompts
.venv/bin/python -m pytest tests/       # 11 unit tests (~2 min)
.venv/bin/python method.py commit1      # re-runs the tests, tars analysis/ + tests/, COMMIT #1 hash chain
.venv/bin/python method.py stage1       # GPU: smoke tests, COPY twin + veto round 1 + bf16 baseline check, veto rounds 2-3
.venv/bin/python method.py commit2      # COMMIT #2 (SUBTRACT-IN-CONTEXT, veto rounds, copy twin, baseline check)
.venv/bin/python method.py stage2       # GPU: NAMED + UNNAMED (+ W1-W4 template arm if >= 45 min of the 2-h budget is left)
.venv/bin/python method.py analyze      # CPU: samples.jsonl, events, frozen C1, sensitivities, reports, figures, method_out.json
.venv/bin/python method.py audit        # CPU: audit/rederive.py independent re-derivation + placebos
```

Seeds:

- **Engine seed.** 20261020.
- **Sample seed.** Every sample has `seed = int(sha256("task:Y:p{i}:s{j}")[:8], 16)`. It is shared by COPY, every veto round, NAMED, UNNAMED and W1-W4 (common random numbers).
- **Baseline check.** Seed from `task:baseline:s{j}`.
- **Shown-program shuffle and proximity references.** Seed `20261020:<task>:<Y>:shown` / `20261020:<task>:<mode>:prox`.

Decoding: T = 1.0, top-p 1.0, top-k off, `max_tokens = min(1024, 2048 - prompt length)`, chat template with thinking disabled.

The stage-1 attempt was interrupted once. A bug selected the stop token `<|im_end|>` as a round-2 veto n-gram. The 750 round-2 samples drawn with that bug are kept apart in `data/discarded_round2_stop_token_bug.jsonl`, and round 2 was redrawn with the corrected rule (see `results/deviations.jsonl`). vLLM same-seed outputs are not guaranteed bit-identical across batch compositions, so a re-run reproduces the distributions, not every token.

Approximate runtimes on this machine:

| step | time |
|---|---|
| setup | 1.6 min |
| forecasts | 9.0 min |
| unit tests / commit1 | 2 min each |
| stage1 | 20 min GPU, including 59 s engine load (the first, aborted attempt took another ~26 min) |
| commit2 | < 1 min |
| stage2 | 14.5 min GPU |
| analyze | 12 s |
| audit | ~1 min |

Labelling runs concurrently with generation, on 4 threads that spawn sandboxed subprocesses.

## 5. What you should get

**Data volume.**
- `data/samples.jsonl` has 10,600 rows:
  - COPY 1,650;
  - veto rounds 1 / 2 / 3: 1,650 / 1,550 / 1,450;
  - bf16 baseline 240;
  - NAMED 1,650; UNNAMED 1,650;
  - W1–W4 760.
- `results/c1_events.jsonl` has 66 events (33 NAMED + 33 UNNAMED).

**Headline numbers** (`results/c1_summary.json`, re-derived by `audit/rederive.py` into `results/rederive.json` with 0 mismatches):

| quantity | value |
|---|---|
| copy rate (Y share under COPY), mean over 33 Y | 0.93 (median 1.00) |
| NAMED avoidance, mean | 0.95 (UNNAMED 0.996) |
| default share COPY / NAMED / UNNAMED | 0.05 / 0.72 / 0.82 |
| gated NAMED events whose modal replacement is the default | 24 / 31 |
| C1 NAMED: gated / gated disagreeing | 31 / 30 |
| advance-rule wins SUBTRACT / LADDER / ASSOCIATE / PROXIMITY | 2 / 7 / 2 / 0 |
| frozen branch | SUBTRACTION/LADDER (LADDER) |
| Wilcoxon (Holm over 4), NAMED | SUBTRACT−ASSOCIATE +1.02 nats, p_Holm 0.081; LADDER−ASSOCIATE +1.29, p_Holm 0.081; LADDER−PROXIMITY +0.50, p_Holm 0.159; SUBTRACT−PROXIMITY +0.23, p_Holm 0.96 |
| UNNAMED LADDER−ASSOCIATE | +1.42 nats, p_Holm 0.0056 |
| top-1 hit rate (gated NAMED) LADDER / PROXIMITY / ASSOCIATE / SUBTRACT | 0.77 / 0.61 / 0.45 / 0.36 |
| SUBTRACT-IN-CONTEXT defined | 4 / 33 Y; 25 / 33 not carried by surface tokens |
| label-permutation placebo: draws in which some family advances | 100% (the counting rule is not a significance test) |
| sign-flip placebo: draws with a Holm-significant test | 5.5% |
| constant-forecast placebo: wins | 0 |

**Figures.** `figures/landing_bars`, `figures/forest_logscore_differences`, `figures/copy_rate_vs_avoidance` and `figures/default_share_by_arm` (PNG + PDF).

**Paper use.**
- These numbers are the "exposure ban" results.
- `results/c1_events.jsonl` rows are the event-level evidence.
- Cross-model pooling with the Llama stratum happens in the next round.
