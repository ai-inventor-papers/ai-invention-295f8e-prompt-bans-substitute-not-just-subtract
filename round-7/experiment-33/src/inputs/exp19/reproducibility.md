# Reproducing "Pricing plan noise against temperature"

This file describes what was actually run on 2026-10-21 (UTC), in the order it was run, including the restarts. Every
path is relative to this folder.

## 1. Get the artifact

This folder is one folder of a public GitHub repository. Clone the repository and `cd` into the folder that contains
this file (it holds `method.py`, `README.md`, `pyproject.toml`):

```bash
git clone <repository-url>
cd <repository>/<this-artifact-folder>
```

The folder already holds a read-only copy of every file this run read from earlier iterations, under `inputs/`, with
sha256 sums in `inputs/SHA256SUMS`:

| Folder | Earlier artifact |
|---|---|
| `inputs/exp11/bench` | the frozen 13-task bench (iteration 2, exp11) |
| `inputs/exp8` | the T1/T2 suite, frozen prompts, engine (iteration 2, exp8) |
| `inputs/exp7` | frozen templates (iteration 2, exp7) |
| `inputs/exp13` | ban units, prompt ids, reused veto rows (iteration 3, exp13) |
| `inputs/exp16` | fence stop; T1/T2 path-screen rows (iteration 3, exp16) |
| `inputs/exp17` | engine, hooks, directions, screen labels (iteration 3, exp17) |
| `inputs/exp18` | audit prompts, 472 known solutions (iteration 3, exp18) |
| `inputs/eval2` | the Step-0 `stats.py` (iteration 3, evaluation 2) |
| `inputs/exp6` | the semantic-seed prompts and phrasing metrics (iteration 1, exp6) |

Inputs from outside this folder:

- **The declared dataset dependency `art_j3Rm_lr2nzR6`.** Only `src/dep_usage.py` reads it. `src/cfg.py` looks for it
  in this order: the environment variable `ART_J3RM_DIR`, then the sibling folder `../art_j3Rm_lr2nzR6` (how the
  repository publishes it), then the run layout.
- **The exp16 source rows.** `src/screen.py` made a one-time extraction of the T1/T2 veto rows from the iteration-3
  exp16 artifact. Its result, `inputs/exp16/data/path_screen_rows.jsonl`, is already in this folder.
- **Location overrides.** The source locations can be overridden with `AII_LOOP_DIR`, `AII_ITER1_DIR`,
  `AII_ITER2_DIR` and `AII_ITER3_DIR`. They are only needed to redo the input copy.
- **User uploads.** No user-uploaded (private) file was used; the run's upload folder was empty.

## 2. System, Python and libraries

Hardware actually used:

- 1 × NVIDIA RTX 2000 Ada Generation: 16 GB VRAM, compute capability 8.9, driver 595.91, CUDA 13.2 runtime.
- 6 vCPU (cgroup quota 5.1).
- 28 GB RAM (container limit).
- Debian 12 container. Ubuntu 22.04/24.04 behaves the same.

No compiler is needed: the FP8 GEMMs are `torch._scaled_mm` from the torch wheel. An FP8-capable GPU (compute
capability ≥ 8.9) with ≥ 16 GB is required for the engine as written.

Python 3.12.14 and uv 0.6.14. All 83 packages are pinned in `pyproject.toml` to the versions installed in `.venv`
(`uv pip freeze`; the uv venv has no pip binary). Key pins: torch 2.8.0 (cu128 wheel), transformers 4.57.6,
numpy 2.2.6, scipy 1.18.1, openai 3.35.1, rapidfuzz 3.14.6, matplotlib 3.11.2.

```bash
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r pyproject.toml
```

## 3. Model, data and environment variables

Model weights. The engine quantises the pinned bf16 snapshot to FP8 W8A8 at load time, which takes about 50 s.

```bash
hf download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218   # 16.4 GB, ~1 min here
```

Environment variables, by name only:

- `HF_HUB_CACHE` / `HF_HOME`: the model cache.
- `OPENROUTER_BASE_URL`, `OPENROUTER_API_KEY`: the blind judges and audits. Their answers are cached in
  `data/judge_cache*.jsonl` and `audit/llm_cache.jsonl`, so a re-run with the caches makes no new calls for identical
  programs.
- Optional: `ART_J3RM_DIR`, `AII_*_DIR` (see above).

Do not set `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` (see restart 3 below).

## 4. Commands, in the order they were run

All times are UTC on 2026-10-21; all commands run from this folder with `.venv/bin/python` (`PY`).

| # | Time | Command | What it does | Runtime |
|---|---|---|---|---|
| 1 | 03:26 | `hf download …` and the venv install | model and environment | 2 min |
| 2 | 04:05 | `$PY src/prompts_v4.py` | 205 prompts; spec-id identity assertions; R2 alias audit (0 hits) → `data/prompts.jsonl` | 1 min |
| 3 | 04:13 | `$PY src/gpu_stage.py --deadline-utc 2026-10-21T07:50:00Z &` | **restart 1:** failed at CUDA init. A RAM cap (`RLIMIT_AS`) blocks CUDA's address reservation, so it was removed from the GPU process | — |
| 4 | 04:20 | same command (log `logs/gpu_stage.out`) | GPU unit tests U1–U6 → `results/unit_tests_gpu.json`; R2 ban-free unit → `results/unit_R2.npy`, `results/unit_r2.json`; engine-check rows T03 W1–W5, T2 W1. **Restart 2:** decoding ran at 150–450 ms/step; killed | 11 min |
| 5 | 04:31 | same command (log `logs/gpu_stage2.out`) | engine-check row T2 W2. Still slow; killed. The cause, found by profiling, was `len(tokenizer)` (~30 ms) called once per generated token while decoding text. It is now cached once (`engine_v4.vocab_len`), giving 55–60 ms/step | 5 min |
| 6 | 04:32 | `$PY src/label_worker_v4.py --raw data/engine_check_raw.jsonl --out data/engine_check_labels.jsonl --follow-until results/engine_check_generated.flag --name label_ec` | labels the engine-check rows | 23 min (idle-following) |
| 7 | 04:52 | `$PY src/gpu_stage.py --deadline-utc 2026-10-21T07:50:00Z &` (log `logs/gpu_stage3.out`) | **final GPU process.** Resumes the engine check (T2 W3–W5), then stage 10 (T03 and T2, template W1, every arm), then waits for `predictions/COMMITTED` | runs to 07:34 |
| 8 | 04:56 | `$PY src/screen.py` | `results/screen.json` (+ sha256), reconciliation; `data/reused_rows.jsonl`, `results/reused_map.json` | < 1 min |
| 9 | 05:01 | `cd src && ../$PY -m analysis.engine_check` | `results/engine_check.json`: REPRODUCED | < 1 min |
| 10 | 05:05 | `cd src && ../$PY -c "from analysis.hull import unit_tests; …"` | `results/hull_unit_tests.json` | 6 s |
| 11 | 05:05 | `$PY src/prereg.py` | `predictions/c1_rule.json`, `predictions/screen_forecast.json`, code hashes → `commitments.log` (commit1, 05:05:55); writes `predictions/COMMITTED`. The GPU process then ran stage 100 (all of T03), the time rule (`results/timing_plan.json`: no drop, N = 50 everywhere) and the full queue (P1 → P2 → P3) | 1 min |
| 12 | 05:06 | `$PY src/label_worker_v4.py --raw data/samples_raw.jsonl --out data/labels.jsonl --follow-until results/gpu_done.flag --name label_main &` | labels every sample while the GPU runs | until 07:34 |
| 13 | 05:18 | `$PY src/s0_checks.py` | `results/input_hashes.json` (0 mismatches), `results/labeller_recheck.json`, `inputs/SHA256SUMS` | 2 min |
| 14 | 05:26 | `$PY src/dep_usage.py` | uses all 10 datasets of `art_j3Rm_lr2nzR6` → `results/dependency_usage.json`, `data/known_solutions_dep.jsonl` | 1 min |
| 15 | 05:51, 06:13, 07:36, 08:03 | inline calls of `src/commit.py` | amendments A1 (speed) and A3 (seed fix); post-commit code; final results → `commitments.log`. Reasons are in `results/deviations.jsonl` | — |
| 16 | 06:44 | `cd src && ../$PY -m analysis.run_all --skip-boot`, then `$PY src/audit_llm.py novelty` | merge; novelty audit (E6 + R2 complete) | 1 min |
| 17 | 06:46 | `cd src && ../$PY -m analysis.run_all --boot-tasks T03,T05,T06,T10,T1,T2,R2 --workers 4` | 2,000-replicate primary bootstrap and the sensitivity bootstraps for E6 + R2 (cached in `results/boot_cache/`) | 14 min |
| 18 | 07:01 | `$PY method.py validity` | label-validity audit | 1 min |
| 19 | 07:36 | `./finalize.sh` (after `results/gpu_done.flag` and the labeller's last pass) | merge → novelty audit → full analysis (P3 bootstraps added; E6 from cache) → descriptive → validity → figures → `method_out.json` → `audit/rederive.py` → summary → README | 6 min |
| 20 | 07:44 | `$PY audit/placebo_full_rule.py` | full-rule placebo over 100 arm shuffles → `results/placebo_full_rule.json` | 6 min |
| 21 | 07:55 | `$PY src/outputs.py; $PY src/report_numbers.py` (README re-assembled) | outputs with the placebo | 1 min |
| 22 | 08:15 | `aii_json_format_mini_preview.py --input method_out.json` (aii-json skill) | `full_/mini_/preview_method_out.json` | 1 min |

`method.py <stage>` wraps the same steps: `prompts`, `inputs`, `screen`, `gpu`, `label`, `label_ec`, `commit`,
`audit`, `analyze`, `validity`, `report`.

GPU time: 10,100 rows in 640 batches, 2.53 h of batch time (`results/timing_summary.json`). Wall time was about 5 h,
including the restarts and the waiting for the commit.

### Seeds and keys

- CRN uniforms: `u_stream(task, w, k)` = PCG64(sha256 of `task|w|k`), shared by every arm.
- PN directions: seed = `stable_seed(task, arm, w, k)`, logged per row as `direction_seed`.
- Engine check: exp17's `rand_9002` (T03) and `rand_9004` (T2).
- Hull uniforms: `default_rng(20261021)`.
- Step-0 rarefaction: `default_rng(0)`, n_sub 1,000; its CI uses `default_rng(1)`.
- Bootstraps: seed 20261021 + per-task crc32. Sensitivities use seed + 11 / 13 / 14 / 15 / 16 / 18; the task bootstrap
  uses seed + 0…22.
- Label-validity sample: `random.Random(7)`.
- Placebos: `random.Random(0)`; bootstraps 777 + s.

## 5. What you should get

| Output | Value | Where |
|---|---|---|
| `results/c1.json` (`primary`) | **PARTIAL**: count1 2/6, count2 4/6, D̄ −0.218 (95% CI −0.893 to 0.304), p_C1 0.758 | README "Results"; the paper's C1 paragraph |
| `results/summary.md` | the per-task H5 table (T03 PN 2.72 vs novelty 1.96; T10 2.09 vs iterated veto 1.96; T06 1.00 vs 2.73; T2 1.35 vs semantic seed 1.93; …) and every sensitivity (all PARTIAL) | README "Numbers" |
| `results/engine_check.json` | REPRODUCED; per-slot agreement 1.00 on all 4 cells | README "Engine and labeller checks" |
| `results/rederive.json` | 12/12 independent checks match; hash chain unbroken | README |
| `results/placebo_full_rule.json` | 0/100 CONFIRMED under arm shuffles | README |
| `audit/novelty_audit.json` | 12 correct 'other' programs, all labeller misses; 0 novel | README |
| `figures/fig1`–`fig6` | frontiers, compositions, dose-response, ideas vs phrasings, engine check, forest plot | the paper's figures |
| `method_out.json` | exp_gen_sol_out: `knob_rows` (282) and `samples` (10,100) | downstream steps |

The judge and audit answers are cached. A re-run of the analysis on the published `data/` therefore reproduces every
number exactly: the bootstraps are seeded, and `results/boot_cache/` is keyed by a hash of the data. A full
re-generation reproduces the samples bit-exactly only on the same GPU type and library versions, because FP8 GEMM
numerics depend on the kernel.
