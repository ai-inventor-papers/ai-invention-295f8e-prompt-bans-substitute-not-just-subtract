# Reproducing "Same seed: temperature vs plan nudges" (iteration 4, C1-seed)

This file records what was actually run, in order, on 2026-10-21 (UTC). Every path below is relative to this folder.

## 1. Getting the artifact

```bash
git clone <the run's GitHub repository>
cd <repository>/<this artifact's folder>     # the folder that contains method.py and this file
```

The folder is self-contained for the analysis. `inputs/` holds sha256-verified copies of everything the experiment
read from earlier artifacts:
- the exp8 path-task suite and labellers;
- the exp11 bench (T03);
- exp13's T03 unit and screen samples;
- exp17's labels, prompts, directions and screen token ids;
- exp18's known-solution index;
- the previews of the dataset dependency.

The one external input read at run time is the dependency dataset **art_j3Rm_lr2nzR6** ("Source data for an
algorithm-choice coding bench"). Only the A9 novelty audit's pool cross-check uses it, through
`full_data_out.json`. Point the environment variable `DEP_DATASET_DIR` at that artifact's folder (the repository
publishes it as a sibling folder). The run's upload folder was empty: no user-uploaded file was used.

## 2. System, Python and libraries

| item | value used |
|---|---|
| OS | Debian 12 container on Linux 6.8 (Ubuntu 22.04/24.04 works the same) |
| GPU | 1 x NVIDIA RTX 2000 Ada Generation, 16 GB (16,380 MiB), compute capability 8.9, driver 595.91.07 |
| CPU / RAM | 5 CPUs (cgroup quota 5.1), 31 GB RAM (cgroup limit) |
| C compiler | none (gcc, cc and nvcc are absent). Not needed: vLLM runs eager with torch.compile off, and the HF FP8 path uses `torch._scaled_mm` |
| Python | 3.12.14 |
| package manager | uv 0.6.14 (no pip in the venvs; `uv pip freeze` replaces `pip freeze`) |

Two venvs are used. They are never imported together, and the two engines never share the GPU:
- `.venv_hf`: torch 2.8.0, transformers 4.57.6, numpy 2.2.6, scipy 1.18.1, openai 3.35.1, ... 82 packages, pinned in
  `env/requirements_hf.txt` (the exact freeze is in `env/freeze_hf.txt`, the same list).
- `.venv_vllm`: vllm 0.11.0, torch 2.8.0, transformers 4.57.6, ... 180 packages, pinned in
  `env/requirements_vllm.txt` (freeze in `env/freeze_vllm.txt`).

`pyproject.toml` holds both. The `.venv_hf` freeze is the main `dependencies` list, and the `.venv_vllm` freeze is
the optional group `vllm`.

```bash
uv venv .venv_hf --python=3.12
uv pip install --python .venv_hf/bin/python -r env/requirements_hf.txt        # ~2 min with a warm uv cache
uv venv .venv_vllm --python=3.12
uv pip install --python .venv_vllm/bin/python -r env/requirements_vllm.txt    # ~4 min with a warm uv cache
```

The sandboxed candidate programs run with the `python3.12` found on `PATH`, through the exp8 suite and the exp11
bench harness.

## 3. Models, environment variables, keys (names only)

| what | how |
|---|---|
| `Qwen/Qwen3-8B` (bf16; quantised to FP8 W8A8 at load), revision `b968826d9c46dd6066d109eabc6255188de91218` | `huggingface-cli download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218` |
| `Qwen/Qwen3-8B-FP8`, snapshot `220b46e3b2180893580a4454f21f22d3ebb187d3` (vLLM) | `huggingface-cli download Qwen/Qwen3-8B-FP8 --revision 220b46e3b2180893580a4454f21f22d3ebb187d3` |
| `HF_HOME`, `HF_HUB_CACHE` | where the weights live; `src/cfg.py -> model_path()` finds the snapshots there |
| `HF_TOKEN` | optional, for the download |
| `OPENROUTER_BASE_URL`, `OPENROUTER_API_KEY` | the blind label judges (only on labeller disagreement), the A7 lexicon audit and the A9 novelty audit |
| `DEP_DATASET_DIR` | folder of the dependency dataset art_j3Rm_lr2nzR6 (A9 pool cross-check only) |
| `AII_RUN_DIR` | only for `--stage setup`, which re-copies and re-verifies the inputs from the original run volume; not needed with `inputs/` present |
| set by `src/vllm_think.py` | `VLLM_USE_FLASHINFER_SAMPLER=0`, `TORCH_COMPILE_DISABLE=1`, `VLLM_TEST_FORCE_FP8_MARLIN=1`, `VLLM_NO_USAGE_STATS=1` |
| `PYTHONDONTWRITEBYTECODE=1` | optional; keeps `__pycache__` out of the folder |

## 4. What was run, in order (UTC, 2026-10-21)

Seeds:
- **token seed of a slot (task, w, k):** `stable_seed(task, w, k)`, a sha256 of the joined key.
  - HF inverse-CDF uniforms: `PCG64(stable_seed(task, w, k)).random(max_new)`.
  - HF Gumbel replicate generator: `stable_seed(task, w, k, 'gumbel')`.
  - vLLM pass-A seed: `stable_seed(task, w, k)`; pass-B (answer) seed: `stable_seed(task, w, k, 'answer')`.
- **plan-noise directions:** normalised `PCG64(s).standard_normal(4096)` for s = 46001..46006.
- **smoke tests:** the key namespace `'smoke'`, never analysed.
- **statistics:** permutation and bootstrap seeds are fixed in the code (for example 20261021 for the sign-flip test).

| time | command | what it did | runtime |
|---|---|---|---|
| 03:30 | the two `uv venv` / `uv pip install` lines above | environments | ~6 min |
| 03:38 | `huggingface-cli download Qwen/Qwen3-8B-FP8` | FP8 checkpoint into the shared cache (bf16 was already there) | 1 min |
| 04:13 | `.venv_hf/bin/python method.py --stage setup` | S0: input hashes (360/360 exp17, 14/14 T03 commitment, exp17 source byte-identical), seed collisions (none), hardware, labeller re-check (22/22, 6/6, T03 gold 0.964 = gate) | 1 min |
| 04:24 | `.venv_hf/bin/python method.py --stage screen` | S1 `results/screen.json` (+ `predictions/screen.sha256`), S2 `results/expectations.json` | 1 min |
| 04:31 | `.venv_vllm/bin/python src/vllm_think.py all` | first launch, stopped by the RAM watchdog during engine load (page cache counted; deviation D6). No sample was taken | 3 min |
| 04:53 | `.venv_hf/bin/python method.py --stage tests` | synthetic tests of `analysis/core.py`, all pass (`results/tests_cpu.json`) | 1 min |
| 04:49 | `.venv_vllm/bin/python src/vllm_think.py all` | relaunch: engine load 148 s, U6 (`results/u6_vllm.json`), then waits for commit #0 | |
| 05:02:05 | `.venv_hf/bin/python method.py --stage commit` | commit #0, 16 files hash-chained in `commitments.log` | <1 min |
| 05:02-05:59 | (same vLLM process) | G1: stage 10 (10 traces), then 90 traces (161 tok/s), then pass B, then the FP8 cross-check (50 programs) | 58 min |
| 05:23 | `.venv_hf/bin/python method.py --stage label --follow --minutes 300 &` | label worker, follows `data/samples_raw.jsonl` | to the end |
| 06:00 | `./run_gpu_chain.sh` | HF chain, first attempt, stopped during the FP8 quantisation by the same watchdog | 2 min |
| 06:10-07:10 | `./run_gpu_chain.sh` (= `method.py --stage hf_chain`) | smoke U1-U5 and U7, unit sensitivity, engine check (200 rows), the 2x2 (1,800 rows, B = 20), optional (iii) (440 rows incl. pads), (iv) (60 + pads), (ii) (40 + pads) | 60 min |
| 07:10-07:48 | `./run_t1_chain.sh` (= `.venv_vllm/bin/python src/vllm_t1.py`) | optional arm (i): T1 thinking on, 10 seeds x 4 T | 38 min |
| 07:5x | `./run_final.sh` | `analysis/llm_audits.py` (A7 + A9), `method.py --stage analyse`, `method.py --stage export`, `audit/rederive.py` | ~6 min |
| then | `aii_json_format_mini_preview.py --input method_out.json`; `aii_json_validate_schema.py --format exp_gen_sol_out` | full / mini / preview variants and schema validation | <1 min |

GPU time:
- **G1** (vLLM): 58 min.
- **HF chain:** 60 min.
- **Arm (i)** (vLLM): 38 min.
- In total, about 2.6 h of GPU wall clock, including model loads. Sampling seconds per stage are in
  `results/gpu_hours.json`, `results/timing_batches.jsonl` and `results/timing_vllm.json`.

OpenRouter spend was under USD 0.10:
- path judge: `results/openrouter_cost_paths.json`;
- bench judge: `data/judge_cache.jsonl`;
- audits: `results/costs.json`;
- total: `results/costs_summary.json`.

Responses are cached, so re-running the analysis spends nothing. `GET <base>/key` returned HTTP 403 through the
proxy, so spend is read from `usage.cost`.

**Determinism.**
- The HF FP8 path is bit-reproducible for a fixed batch shape:
  - U1 passes;
  - the filler repeats are byte-identical in 60/60;
  - the engine check matches exp17's screen in 200/200 rows.
- vLLM on CC 8.9 is not batch-invariant: the T 0.7 repeat diverged byte-wise in every trace (first divergence at token
  34-653) but kept the label in 20/20. A re-run therefore reproduces the HF rows exactly and the vLLM rows in
  distribution.

**Re-running only the analysis** (no GPU, no key needed: judge and audit responses are cached):

```bash
.venv_hf/bin/python method.py --stage analyse && .venv_hf/bin/python method.py --stage export && .venv_hf/bin/python audit/rederive.py
```

## 5. What you should get

| result | file | value |
|---|---|---|
| verdict | `results/c1seed.json -> verdict` | **PARTIAL**: H-T, H-PHR and H-CON hold; H-PN fails on T03 |
| C_T, thinking off (4 temperatures, 20 seeds) | `c1seed.json -> A1_C_T_off` | T2 0, T03 0, T1 0 (CP 95% upper rate 0.168 each) |
| C_T, thinking on (T2, vLLM) | `results/thinking.json -> C_T_completed_all_4` | 0 of 20 (all 100 traces completed; repeat change count 0) |
| C_PN (alpha 1, T 1.0) | `c1seed.json -> A2_C_PN` | T2 17.25 (range 12-20), T03 4.55 (0-7), T1 2.50 |
| x_s contrast (Holm entry C1-seed) | `c1seed.json -> A3_x_contrast.pooled` | mean 0.545 [0.41, 0.67], sign-flip p = 1.0e-5 (100,000 draws); placebo share p < 0.05 = 0.02 |
| PPI slope on T (pooled) | `c1seed.json -> A4_phrasing_pooled` | 0.64 / 0.70 / 0.81 at theta 0.7 / 0.8 / 0.9, CIs exclude 0 |
| engine check | `results/engine_check.json` | REPRODUCED, 200/200 byte-identical to exp17 |
| Gumbel replicate (iii) | `c1seed.json -> optional.iii_gumbel` | C_T 0 / 0; C_PN T2 16.05, T03 5.8; p = 1.0e-5 |
| min-p T 2.0 (iv) | `c1seed.json -> optional.iv_minp` | 1 of 20 seeds changed on T2 and T03, 0 on T1 |
| thinking-on PN (ii) | `c1seed.json -> optional.ii_thinking_pn` | first approach moved in at most 1 of 10 seeds |
| T1 thinking on (i) | `results/thinking.json -> T1_optional_i` | 40/40 completed; BFS in every final program and first approach; C_T 0 of 10 |
| re-derivation | `results/rederive.json` | 0 mismatches in 33 checks; hash chain 0 breaks; commit #0 precedes the first decisive row; within-seed permutation test p = 0.005; placebo share p < 0.05: 0.105 (200 runs, own RNG) |

No paper existed when this was written. The paper is written downstream; it should carry the values above in its
same-seed (temperature vs plan-noise) section and cite `results/c1seed.json`.
