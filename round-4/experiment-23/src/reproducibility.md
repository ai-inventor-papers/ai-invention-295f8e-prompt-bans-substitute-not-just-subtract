# Reproducing this artifact

These are the steps that were **actually run** to produce the results in `results/`, `figures/`, `predictions/` and
`method_out.json`. Every path below is relative to this artifact's folder.

## 1. Get the artifact

```bash
git clone <URL of the published repository>
cd <repository>/<this artifact's folder>     # the folder that holds this file, README.md and method.py
```

Inputs produced by other artifacts are published in the same repository as **sibling folders named by artifact id**.
They are read only by `src/stage_inputs.py`, which copies what it needs into `inputs/`. `inputs/` is already
committed with sha256 sums in `inputs/SHA256SUMS`, so the staging step is only needed to re-stage from the sibling folders.

| Sibling folder (artifact id) | Role | Staged into |
|---|---|---|
| `art_0ndRfWKBWclR` | frozen 13-task bench, labellers, gold sets, forced programs | `inputs/exp11/` |
| `art_8_ULPE8jJQc_` | T1/T2 suite (tests, references, labeller), frozen prompts | `inputs/exp8/` |
| `art_6zBfl3kDjeiP` | frozen templates, nouns, padding; prompts_v2 | `inputs/exp7/` |
| `art_pVlCZ272hDV7` | Qwen3-8B push code, T1/T2 ban norms, random directions, screen labels, Qwen twin prompt ids | `inputs/exp17/` |
| `art_1AYTO1Epb_7t` | Qwen ban-displacement norms (12 bench tasks), screen samples | `inputs/exp13/` |
| `art_Q-qh-9HhPoWo` | Llama port (template for this port) | `inputs/exp15/` |
| `art_ccAbfJVcv0LO` | known-solutions index (472), novelty-audit protocol | `inputs/exp18/` |
| `art__5akZ9W9iZM4` | prefill / opening code | `inputs/exp16/` |
| `art_j3Rm_lr2nzR6` (declared dependency) | `full_data_out.json`: noun bank, known-solution corpus, harness checks | `inputs/art_j3Rm_lr2nzR6/` (extracted subsets; the 96 MB file is not copied) |

`AII_ARTIFACTS_DIR` overrides the folder that holds these siblings (default: the parent of this folder). An optional,
unpublished `paths.local.json` (`{"exp11": "<path>", ...}`) overrides single locations. It was used on the run server,
whose folders are not named by id.

No user-uploaded material was used: the run's upload folder was empty.

## 2. System, Python and libraries

What ran:

- **System.** Debian 12 container (Ubuntu 22.04+ works the same way), NVIDIA driver 595.91 (CUDA 13.2 runtime support).
- **GPU.** One **NVIDIA RTX 2000 Ada Generation, 16 GB** (sm_89).
- **CPU and memory.** A 6-CPU cgroup quota, 28 GB RAM.
- **Python.** 3.12.
- **Packages.** `uv` for the environment; no system packages beyond `python3.12` and an NVIDIA driver.

```bash
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r pyproject.toml   # 84 packages, all pinned with ==
```

`pyproject.toml` is exactly `uv pip freeze --python .venv/bin/python`; the uv venv has no pip binary. Key versions:

- `torch==2.8.0` (CUDA 12.8 wheel from PyPI)
- `transformers==4.57.6`
- `tokenizers==0.22.2`
- `safetensors==0.8.0`
- `accelerate==1.15.0`
- `numpy==2.2.6`
- `scipy==1.18.1`
- `pandas==3.0.6`
- `matplotlib==3.11.2`
- `zss==1.2.0`
- `rapidfuzz==3.14.1`
- `openai==3.35.1`
- `loguru==0.7.3`

The frozen bench labeller runs every program in a fresh sandboxed interpreter: `python3.12 -I -S` if it is on PATH, else
the venv's interpreter. `BENCH_SANDBOX_PYTHON` overrides it.

## 3. Models, data and environment variables (names only)

| What | How |
|---|---|
| `google/gemma-3-4b-it`, revision `093f9f388b31de276ce2de164bdc2081324b9767` (gated; accept the licence on Hugging Face) | `huggingface-cli download google/gemma-3-4b-it --revision 093f9f388b31de276ce2de164bdc2081324b9767` (the sha256 of both safetensors files is recorded and checked in `predictions/commit1.json`) |
| `Qwen/Qwen3-8B`, revision `b968826d9c46dd6066d109eabc6255188de91218` (only for `src/qwen_ratio.py`) | `huggingface-cli download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218` |
| `HF_TOKEN` | Hugging Face token with Gemma access |
| `HF_HOME` / `HF_HUB_CACHE` (optional) | Hugging Face cache location |
| `OPENROUTER_BASE_URL`, `OPENROUTER_API_KEY` | blind judge on runtime/AST disagreements, label audit, novelty audit, post-hoc T2 re-audit (total spend USD 0.28) |
| `AII_ARTIFACTS_DIR` (optional) | parent folder of the upstream sibling artifacts |
| `AII_DATA_FIG_GEN_SCRIPTS` (optional) | folder of the `aii-data-fig-gen` renderer (`chart_gen.py`, `chart_style.py`); without it `src/figures.py` still writes the figure specs `figures/*.json` |

`restore.sh` recreates the venv and downloads both models.

## 4. Commands, in the order they were run

`python method.py` runs the same stages in this order. `python method.py --from <stage>` resumes, and `--only <stage>` runs a
single stage. All commands use `.venv/bin/python`.

| # | Command | What it does | Runtime (RTX 2000 Ada) |
|---|---|---|---|
| 1 | `python src/stage_inputs.py` | staging, sha256 checks against `bench/commitment.json`, labeller re-check, dependency extraction | about 3 min (CPU) |
| 2 | `python src/screen.py` | iteration-3 screen recomputed (`results/screen.json`) | under 1 min |
| 3 | `python src/qwen_ratio.py` | Qwen3-8B r_Q and r_Q,ox plus the forward positive control; bf16 with accelerate CPU offload | about 1 min after loading |
| 4 | `python src/gpu_tests.py` | U1–U4, U6 (`results/tests_gpu.json`) | about 1 min |
| 5 | `python src/unit_probe.py` | unit calibration probe (`results/unit_probe.json`) | about 1.5 min |
| 6 | `python src/label_worker.py &` | background labeller, followed every raw file until the end | — |
| 7 | `python src/banfree.py pilot`, then `python src/banfree.py commit1` | pilot (150 programs) and commit #1 | about 2 min |
| 8 | `python src/banfree.py phaseA` | Phase A: 5,400 CRN rows | 34 min |
| 9 | `python src/banfree.py all_after_A` | Phase B, association, ladder, novelty, 'can' | about 25 min |
| 10 | `python src/commit2.py` | grep audit plus pre-ban predictions and the frozen analysis hash (commit #2) | about 8 min (CPU: proximity) |
| 11 | `python src/bans.py` | 2,700 ban rows (1,500 primary) and the ban-derived unit | 17 min |
| 12 | `python src/banfree.py t16 --tasks T2,T05,T04,T1,T10,T11` | optional T 1.6 cell | 2 min |
| 13 | `python src/judge_audit.py` | label audit, disagreement rates, novelty audit | about 5 min (OpenRouter) |
| 14 | `python src/final_analysis.py` | C3a, rivals, C3b, C1, commit #3 | about 1 min |
| 15 | `python src/posthoc_t2.py` | POST HOC T2 mechanism re-audit | about 1 min (OpenRouter) |
| 16 | `python src/figures.py`, `python src/tests_cpu.py`, `python src/bookkeeping.py`, `python src/outputs.py`, `python audit/rederive.py` | figures, CPU tests, timing/deviations, outputs, re-derivation | about 4 min |
| 17 | `aii_json_format_mini_preview.py --input method_out.json` (aii-json skill) | writes `full_/mini_/preview_method_out.json` | — |

Notes on how steps 3, 4 and 10 actually ran:

- **Step 3** was run twice. The second run added the outlier-excluded ratio `r_Q_ox` (deviation D3) and was decided before
  commit #1.
- **Step 10** failed once on a missing `rapidfuzz` install (needed by the bench's association lexicon). The package was added
  to the environment and the step was re-run. No predictions had been written by the failed run.
- **The labeller** started in step 6 ran until after step 12.

Total generation: 1.28 GPU-hours (about 1.6 including model loads); wall-clock about 2.7 hours.

**Seeds and determinism.**

- **Sampling is common-random-number inverse-CDF.** Every row's uniform stream is
  `PCG64(sha256("task|template|slot") mod 2^63)` (`src/cfg.py:stable_seed`), with temperature 1 (1.3 / 1.6 in the temperature
  arms), top-p 1 and no top-k.
- **Batch shape and caps are fixed.** B = 36 rows per batch; the caps are 640 new tokens (pilot rule).
- **Directions.** The escape directions use PCG64 seeds 9001–9008. Plan-noise directions are `PCG64(stable_seed(task, 'PN', template, slot))`.
- **Analysis.** Bootstrap and permutation seeds are fixed in `src/analysis_c3.py` (frozen copy in `predictions/`).
- **What may vary.** Generations are bit-reproducible on the same GPU, driver and library stack. On a different GPU, bf16 kernels
  may flip near-tied tokens.
- **Judges.** Judge answers come from OpenRouter models and are cached (`data/judge_cache*.jsonl`). Re-running
  with the caches in place reproduces every label without new calls.

## 5. Expected outputs and numbers

| File | Expected content |
|---|---|
| `results/tests_gpu.json`, `results/tests_cpu.json` | all tests pass: U1–U4; T1, T3–T6; T2 bench part. The exp8 suite gold accuracy is 0.80 vs the gate's 0.84 (deviation D7) |
| `results/screen.json` | iteration-3 screen; reproduces the 6 stated escape counts |
| `results/qwen_ratio.json` | r_Q 0.070–0.123; r_Q,ox 0.090–0.158; positive control median relative difference 0.028 |
| `predictions/commit_preban.json` | movable = T1, T2, T04, T05, T10, T11 (E_t 0.125, 0.25, 0.25, 0.25, 0.125, 0.125); the 9 others immovable |
| `results/bans.json` | A_t: T1 0.83, T2 0.96, T03 0.63, T05 0.59, T04 0.19, T06 0.34, all others 0.00 |
| `results/c3a.json` | **BA 0.739 [0.40, 0.95], Fisher p 0.235 (table [[3,3],[1,8]]), Spearman ρ 0.537 (one-sided permutation p 0.025), Kendall τ-b 0.470 → INCONCLUSIVE** |
| `results/rivals.json` | ρ with A_t: novelty 0.774, PN α2 0.511, PN α1 0.473, can_max 0.349, T 1.3 0.336, twin modal share 0.239, opening margin −0.191 |
| `results/c3b.json` | mean log score: push-landing −0.105, proximity −1.196, association −1.773, ladder −3.657; contest INCONCLUSIVE (2 disagreeing events) |
| `results/c1_prices.json` | H5 per knob, e.g. T2: PN 1.62, temperature 1.00, novelty 1.96 (Monte-Carlo; seeds fixed) |
| `results/unit_sensitivity.json` | median n_ban / n_banfree(ox) = 1.285 |
| `results/posthoc_t2_relabel.json` | judge relabel: T2 A_t 0.11, BA 0.667, ρ 0.440; structural: T2 A_t 0.50, BA 0.739, ρ 0.456 |
| `results/label_audit.json`, `results/novelty_audit.json` | audit agreement 0.933; 0 novel algorithms among 34 correct 'other' programs |
| `results/rederive.json` | 0 mismatches; placebos fail as required |
| `commitments.log` | 3 hash-chained commits; `python -c "import sys; sys.path.insert(0,'src'); from commit import verify_chain; print(verify_chain())"` returns `ok: True` |

In the paper, these numbers are the held-out-family (Gemma) results:

- fig1: E_t vs A_t; fig2: the rival forest;
- fig3: compositions; fig4: the C1 hull; fig5: C3b; fig6: the unit diagnostics;
- tables from `results/c3a.json`, `results/rivals.json`, `results/c3b.json` and `results/c1_prices.json`.
