# Reproducing "Where in the prompt the algorithm is chosen" (iteration 6)

This file describes exactly what was run for this artifact on 2026-10-22, in order, and how to rerun it on Ubuntu.
Every path below is relative to this artifact's folder.

## 1. Get the artifact

The workspace is published as one folder of a public GitHub repository:

```bash
git clone <repository URL>
cd <repository>/<this artifact's folder>     # the folder that contains this file, method.py and src/
```

Sibling folders of the same repository hold the other artifacts of the run. This artifact's declared dependency
`art_j3Rm_lr2nzR6` (the dataset) is read from the sibling folder `../art_j3Rm_lr2nzR6`, or from `$ART_J3RM_DIR`.
It is only needed to rebuild `data/dep_extract.json`, which is published here.

**Prior artifacts.** Iterations 2-5 of the earlier run (`run_aRfWvcSWjssb`) are not declared dependencies. Every file
this code reads from them is mirrored byte-for-byte in:
- `inputs/`: exp27's input copy, with sha256 in `inputs/SHA256SUMS`;
- `inputs_extra/expN/`: the rest, with sha256 in `results/inputs_available.json` and `predictions/commit0.json`.

So no outside path is needed. `$AII_PRIOR_LOOP` (the original `<run>/3_invention_loop` folder) is used only by the
STEP-0 availability gate in `src/bookkeeping6.py`. The run used no user-uploaded files.

## 2. System, Python and libraries

- **OS and GPU.** Ubuntu or Debian with an NVIDIA driver for CUDA 12.8+ (this run: driver 595.91, CUDA 13.2).
- **Python.** 3.12.14, managed by `uv` (`uv` itself from https://docs.astral.sh/uv/).
- **Libraries.** `pyproject.toml` pins every package to the exact version installed in this run's `.venv` (85 packages:
  `uv pip freeze`; the uv venv has no pip). Key versions: torch 2.8.0 (CUDA 12.8 wheels), transformers 4.57.6,
  accelerate 1.15.0, numpy 2.2.6, scipy 1.18.1, statsmodels 0.15.0, openai 3.35.1, jsonschema 4.26.0.

```bash
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r pyproject.toml
.venv/bin/python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
```

## 3. Downloads, environment variables, keys (names only)

```bash
export HF_TOKEN=...                 # gemma-3-4b-it is gated: accept its licence on Hugging Face first
.venv/bin/python src/download_models6.py
```

The download script fetches two checkpoints:
- Qwen/Qwen3-8B @ `b968826d9c46dd6066d109eabc6255188de91218` (about 16.4 GB, bf16);
- google/gemma-3-4b-it @ `093f9f388b31de276ce2de164bdc2081324b9767` (about 8.6 GB; L only).

Environment variables (names only):

| variable | needed for |
|---|---|
| `HF_TOKEN` | the gated Gemma download |
| `HF_HOME`, `HF_HUB_CACHE` | optional cache location |
| `OPENROUTER_BASE_URL`, `OPENROUTER_API_KEY` | the blind judge, called only when the runtime and AST labellers disagree, and the novelty audit. Every judge reply of this run is cached in `data/judge_cache.jsonl` and `data/judge_cache_paths.jsonl`, so relabelling the published programs needs no API call |
| `ART_J3RM_DIR`, `AII_PRIOR_LOOP` | optional input locations (see section 1) |
| `AII_JSON_SKILL` | optional: the aii-json skill folder; without it, `src/format_outputs6.py` writes the full/mini/preview files and validates them with `jsonschema` against `schemas/exp_gen_sol_out.json` |

## 4. What was run, in order (UTC times of this run)

**Hardware.**
- GPU: one NVIDIA RTX 2000 Ada Generation, 16 GB VRAM.
- CPU and RAM: 6 vCPU (AMD EPYC 7443), 28 GB RAM (container limit).
- bf16 Qwen3-8B does not fit whole on 16 GB, so `src/engine6.py` keeps the input-embedding table in CPU RAM (exact row
  gather) and runs all 36 blocks and lm_head on the GPU.
- Total GPU time about 2.7 h (`results/timing_summary.json`); wall clock about 3.8 h from setup to final outputs.

| step | command | time |
|---|---|---|
| 0. memory and throughput probe | `.venv/bin/python src/probe_gpu.py` -> `results/probe_gpu.json` (0.08 s per decode step at batch 12) | 05:05, 3 min |
| 1. prompts, positions, dependency extract | `.venv/bin/python src/prompts6.py` -> `prompts/prompts6.jsonl`, `prompts/positions.json`, `data/dep_extract.json` | 05:21, 1 min |
| 2. GPU unit tests U1-U5 | `.venv/bin/python src/gpu6.py utest` -> `results/unit_tests_gpu.json` | 05:30, 4.5 min |
| 3. label worker | `.venv/bin/python src/label6.py &`: follows `data/samples_raw.jsonl` and appends `data/labels.jsonl` until `results/gpu_all_done.flag` exists | started 05:34, ran throughout |
| 4. commit #0 | `.venv/bin/python src/prereg6.py` -> `predictions/commit0.json` + `commitments.log` | 05:35 |
| 5. main GPU queue | `bash scripts/run_gpu_main.sh 175`, i.e. `gpu6.py stageA,stcore,dmd,top5,stext --deadline-min 175` | 05:37-08:09: Stage A + twins 59 min, ST core 29 min, S3 extension + DMD 13 min, top-five push + prompt ban 18.5 min, ST extensions 31 min |
| 6. L event table, commit #1 | `.venv/bin/python src/lcontest.py events` -> `data/l_events.json` | 05:48 |
| 7. U-test labels | `.venv/bin/python src/label6.py unit_tests_raw` | 05:50 |
| 8. extensions, then L's opening ranking | `bash scripts/run_gpu_after.sh <PID of step 5> 25`: waits for step 5, then `gpu6.py ext --deadline-min 25` (forced sources, semantic seed, W4; 08:10-08:24), then `lcontest.py open` (Qwen3-8B then gemma-3-4b-it, 1,220 teacher-forced passes; 08:25-08:28) | 14 + 3 min |
| 9. analysis freeze and final analyses | `.venv/bin/python src/commit_analysis.py` (amendment 3), then `bash scripts/finalize.sh` | 08:09-08:31 |
| 10. post-hoc presentation and audit | `src/figures6.py` (F3 redesign) and `src/commit_analysis.py amendment5_presentation_code ...`, then `src/outputs6.py`, the output formatter, and `python3 -I audit/rederive.py` (extended with the raw re-derivations and placebo tests below) | 08:40-09:10 |

`scripts/finalize.sh` runs, in order:
1. `src/commit_analysis.py amendment4_analysis_code_posthoc ...`;
2. `src/analysis6.py engine,stageA,st,svt,top5`;
3. `src/lcontest.py score` (commits the forecast values as commit 1b before scoring);
4. `src/novelty6.py`, `src/bookkeeping6.py`, `python3 -I audit/rederive.py`;
5. `src/figures6.py`, `src/report6.py`, `src/outputs6.py`, then the full/mini/preview formatting and schema check.

`method.py all` runs the same stages one after another (prompts, utest, commit0, gpu, ext, lgpu, label, analysis,
novelty, figures, outputs, audit). In the actual run the label worker ran concurrently with the GPU stages instead of
after them, and the analysis-code amendments were written by `src/commit_analysis.py`. Every stage is resumable: rows
already present in `data/samples_raw.jsonl` are skipped by `sample_id`.

### Seeds and fixed settings

- **Token streams (CRN).** `u_stream(task, template, k)` = PCG64 seeded with
  `int(sha256('task|template|k'), 16) mod 2^63`. These are exp27's streams, shared by every arm of a slot.
  - Slots 0-29 map to (W1 k0-7, W2 k0-7, W3 k0-6, W5 k0-6); slots 30-49 and 50-59 (W4) are listed in `src/cfg6.py`.
  - Tokens are drawn by float64 inverse CDF in vocabulary order, at T = 1 with no truncation. DMD rows use the
    committed temperature on generated tokens 1-32.
- **Noise directions.** `dir_seed(task, site, alpha, slot) = int(sha256('iter6_dir3|task|site|alpha|slot')[:8], 16)`,
  then a PCG64 normal vector, normalised. MR directions use `dir_seed(task, 'MR_<band>', 0, slot)`, one per block and
  position.
- **Batches and caps.** Batch size 10 (bench), 8 (T2), 6 (T1), fixed per task, with filler rows keeping the shape
  constant. Max new tokens 384 / 512 / 640, plus the fence stop.
- **Statistics.** Cluster bootstrap seed 20261022 (2,000 resamples); shuffled-site placebo seed 7; landing null seed
  11; `audit/rederive.py` placebo seeds 3, 5, 11-19.
- **Determinism and its limit.** U5: the same slot run twice gives a byte-identical program. bf16 GEMM results depend
  on the GPU class and the batch shape, so a different GPU can change individual tokens (this run vs exp27's GPU: 0.975
  per-slot label agreement on T03 and T2).

## 5. What you should get

These are the numbers quoted in the README's Results section and in the appendix tables (`results/summary.md`). A
paper built on this artifact cites them from there. Every row below is recomputed from the raw files by
`audit/rederive.py`: 295 checks, 0 mismatches, in `results/rederive.json`.

| quantity | value | file |
|---|---|---|
| T2 Stage A: X_0-35 vs twin on Bellman-Ford/SPFA | 24:0, transfer 0.80, exact McNemar p 1.2e-7 (Holm 7e-7); swap placebo p 0.84 | `results/stage_a.json` |
| X_0-35 vs matched-norm random exchange | T2 23:0, T03 16:2, T10 11:0; placebos p 0.68 / 0.81 / 1.0 | `results/stage_a.json` |
| condition-span splice (COND) | T05 1.00, T06 0.90, T2 0.00; read position 0.00 on all six tasks | `results/stage_a.json` |
| committed P1 / route check / placebo / MR | NOT SUPPORTED / holds / holds / holds | `results/stage_a.json` |
| ST, T03, S0 vs S1 | paired flips 24:5 (p 5.5e-4; placebo p 0.46); MH OR 4.61 (permutation p 0.002) | `results/site_grid.json` |
| ST committed rule | WITHDRAWN (S2 arm without common support; alpha-8 breakage) | `results/site_grid.json` |
| state vs token, alpha 2 | T03 12:6 (p 0.24), T10 7:3 (p 0.34): not established | `results/state_vs_token.json` |
| top-five push | correct non-BFS programs 1 / 0 / 0 / 0 at alpha 1-8; landing test not computable | `results/top5_push.json` |
| L | BASE 17/21, OPEN 10/21, sign test 8:1 (p 0.0195); swap placebo 4:5 (p 0.75) | `results/landing_forecast.json` |
| engine check | per-slot agreement with exp27 0.975 (T03), 0.975 (T2) | `results/engine_check.json` |
| extensions | forced Bellman-Ford/SPFA exchange 30/30 (padding twin 1/30); forced BFS 28/30 | `results/summary.md` |

Further outputs:
- `method_out.json` (+ `full_`, `mini_`, `preview_` versions; exp_gen_sol_out schema): one example per (task, cell,
  slot).
- `figures/F1-F6`: F5 is the activation-space geometry.

Two parts are not independently re-derived: the Firth coefficients and their profile/bootstrap intervals (the
estimator is unit-tested in `results/tests_cpu.json`), and the DMD temperatures.

## 6. Shortcuts

- **Without a GPU,** rerun only the CPU part on the published rows: `.venv/bin/python method.py analysis novelty
  figures outputs audit`. Novelty needs the OpenRouter variables; analysis, figures, outputs and audit need none.
- **Relabelling** from scratch: delete `data/labels.jsonl`, then
  `touch results/gpu_all_done.flag && .venv/bin/python src/label6.py`.
