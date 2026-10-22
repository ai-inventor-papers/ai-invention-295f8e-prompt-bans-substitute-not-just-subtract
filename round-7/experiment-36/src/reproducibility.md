# Reproducing step K: plan-noise unit × seeds crosswalk, profile split and prices

These are the steps that were actually run, in the order they were run, on 2026-10-22, with what each produced. Every
path below is relative to this artifact's folder.

## 1. Get the artifact

```bash
git clone <the run's public repository URL>
cd <repository>/<this artifact's folder>        # the folder that holds this file, method.py and src/
```

- **Inputs ship with the folder.** `inputs/` and `vendor/` hold sha256-verified copies of every earlier-artifact
  input: code, prompts, unit tensors, anchor rows, and the iteration-5 knob rows (`inputs/MANIFEST.tsv` lists source,
  size and sha256). You do not need the earlier artifacts.
- **The declared dependency.** `art_j3Rm_lr2nzR6` (dataset) is published as the sibling folder
  `../art_j3Rm_lr2nzR6`. Its files are also copied into `inputs/dep_art_j3Rm/`.
- **User uploads.** None were used; the run's user-uploads folder was empty.

## 2. System, Python and libraries

| item | what was used |
|---|---|
| OS | Debian GNU/Linux 12 container. The commands below work unchanged on Ubuntu 22.04 / 24.04. |
| GPU | 1 × NVIDIA GeForce RTX 4090, 24 GB, compute capability 8.9 |
| NVIDIA driver | 595.91.07 (any driver that runs CUDA 12.8 wheels) |
| CPU / RAM | 32 cores, 124 GB visible |
| Python | 3.12.14 |
| uv | 0.6.14 |

- **System packages:** `git`, `curl`, and a recent `uv` (`curl -LsSf https://astral.sh/uv/install.sh | sh`). No
  compiler is needed.
- **Hugging Face CLI:** the `hf` command, from the pinned `huggingface-hub==0.36.2`, either installed in `.venv` or
  through `uvx --from huggingface-hub==0.36.2 hf`.

Create the environment exactly as it was created:

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r pyproject.toml
```

- `pyproject.toml` pins all 85 installed packages to the exact versions in `.venv`. The list equals
  `uv pip freeze --python .venv/bin/python`; uv venvs have no `pip`. `uv.lock` was written by `uv run`.
- Key versions:

  | package | version |
  |---|---|
  | torch | 2.8.0 (+cu128 wheels from PyPI) |
  | transformers | 4.57.6 |
  | accelerate | 1.15.0 |
  | safetensors | 0.8.0 |
  | tokenizers | 0.22.2 |
  | huggingface-hub | 0.36.2 |
  | numpy | 2.2.6 |
  | scipy | 1.18.1 |
  | statsmodels | 0.15.0 |
  | scikit-learn | 1.9.1 |
  | pandas | 3.0.6 |
  | matplotlib | 3.11.2 |
  | openai | 3.35.1 |
  | loguru | 0.7.3 |

## 3. Models, data and environment variables

```bash
hf download Qwen/Qwen3-8B      --revision b968826d9c46dd6066d109eabc6255188de91218   # instruct, bf16, ~16 GB
hf download Qwen/Qwen3-8B-Base --revision 49e3418fbbbca6ecbdf9608b4d22e5a407081db4   # base, ~16 GB (S3 base intents)
```

**Environment variables, by name only:**

| variable | needed | purpose |
|---|---|---|
| `HF_HUB_CACHE` (or `HF_HOME`) | yes | where the snapshots live. The code finds the snapshot through `HF_HUB_CACHE`, as the vendored exp22 `cfg.model_path` does. |
| `HF_TOKEN` | optional | Hugging Face access token |
| `OPENROUTER_BASE_URL`, `OPENROUTER_API_KEY` | yes | the labeller's tie-break judges and the novelty audit (USD 0.10 in total in this run) |
| `AII_DEP_ART_J3RM` | optional | location of the dependency folder (default `../art_j3Rm_lr2nzR6`) |
| `AII_ITER6_ROOT`, `AII_ITER25_RUN` | optional | locations of the earlier run folders. Used only to re-copy inputs; the copies already ship. |

## 4. Commands, in the order they were run

The entry point `uv run method.py all` runs the same sequence. In the actual run the steps were launched as separate
processes in this order (start times are UTC on 2026-10-22).

| # | start | command | what it did | wall time |
|---|---|---|---|---|
| 1 | 13:05 | `.venv/bin/python src/setup_inputs.py` | copied the inputs; wrote `inputs/MANIFEST.tsv` (1,167 files) | 2 min |
| 2 | 13:23 | `.venv/bin/python src/gen_k.py tests s0 s1 d5 s2 s3pn` | one GPU process, see step 2 below | 28 min |
| 3 | 13:26 | `.venv/bin/python src/label_k.py` | label worker in the background for the whole session; restarted at 13:48 after AMENDMENT 1 | — |
| 4 | 13:33 | `.venv/bin/python src/make_commits.py commit1` | COMMIT #1 | — |
| 5 | 13:47 | `.venv/bin/python src/make_commits.py commit2` | COMMIT #2 | — |
| 6 | 13:49 | `.venv/bin/python src/knobs_k.py reuse` | queued exp27's 1,250 knob rows for relabelling | CPU |
| 7 | 13:52 | `.venv/bin/python src/knobs_k.py base,check,verdict,rerun` | see step 7 below | 13 min |
| 8 | 13:54 | `.venv/bin/python src/s3_prices.py g5` and `.venv/bin/python src/cpu_gates.py` | gates G1–G5, all pass | — |
| 9 | 14:05 | `.venv/bin/python src/dump_units.py` | dose units in activation coordinates → `cache/units/` | 1 min |
| 10 | 14:06 | `.venv/bin/python src/e1_sweep.py` | exploratory E1, hash-committed at 14:04 before its first row | 6 min |
| 11 | 14:10 | `.venv/bin/python src/s3_prices.py all` | S3 hulls; 2,000 bootstraps × 5 tasks on 16 spawn workers; readings and re-tag | 1.5 min |
| 12 | 14:14 | `.venv/bin/python src/novelty_k.py`, then `.venv/bin/python src/novelty_k.py --manual-only` | judges (38 calls, USD 0.03), then the manual pass | — |
| 13 | 14:15 | `.venv/bin/python src/analysis_k.py all`, `src/geometry_k.py`, `src/figures_k.py`, `src/report_k.py`, `src/outputs_k.py`, `python3 audit/rederive.py` | analyses, figures, outputs, re-derivation | — |
| 14 | 14:32 | `.venv/bin/python src/e3_replicate.py`, then `.venv/bin/python src/extensions_k.py` | exploratory E3, hash-committed at 14:31 before its first row | 7 min |
| 15 | 14:44–15:15 | AMENDMENT 3, then step 13 again, then `uv run method.py report outputs` and the aii-json mini/preview script | final pass | — |

**Step 2: the single GPU process (`src/gen_k.py`).** It ran these stages in order:

- the hardware record;
- the model load (22 s);
- the memory probe (constant B = 12);
- unit tests U1–U6, all pass;
- S0 twins;
- a wait for `predictions/commit1.json`;
- S1, with the anchors first;
- D5;
- S2;
- a wait for `predictions/commit2.json`;
- S3 plan noise at D\* = D1.

**Step 7: the knob process (`src/knobs_k.py`).** It ran exp27's code paths unchanged:

1. The base model (bf16) wrote 250 intents. All 250 match exp27's intents in text and ids.
2. The base model was unloaded and the instruct model reloaded.
3. The knob check: 250 rows.
4. The verdict: 17 of 25 (task, knob) cells reuse exp27's rows.
5. Reruns at k 2–9: 320 rows.

**Seeds and randomness.**

- Every token stream is `PCG64(stable_seed(task, template, k))`, shared by every arm of a slot.
- Directions are `S4 = PCG64(stable_seed(task, 'PN_a<α>', w, k))` and `S5 = PCG64(stable_seed(task, 'PN5', w, k))`.
- `P_shuf` uses `PCG64(stable_seed(task, 'SHUF'))`.
- The S1 bootstrap seed is 20261022. The S3 bootstrap seeds are `20261021*1000 + i + 7919*task_index`, as in exp27.
  The hull's point-estimate seed is 0.
- The sampler is exact inverse-CDF at T 1.0, with no top-k and top-p 1.

**Totals.**

- **GPU time:** about 0.66 GPU-h (`results/timing.json`). That is 2,880 instruct-runner programs at 0.3–0.8
  s/program with B = 12, plus the knob process (10 min).
- **OpenRouter spend:** USD 0.10 (`results/costs.json`).

**Determinism.**

- **Same GPU.** On one GPU the runs are bitwise reproducible (U4).
- **Batch shape.** Batch size does not change a row's tokens (U3).
- **Another GPU model or driver.** Individual programs can diverge mid-decode. The S0 engine check against exp30
  (another GPU) agrees on labels 15/16 on T2 and T03 and 40/40 on T10 and T05. So expect shares within sampling noise,
  not identical token ids.

**Resuming.** Every step resumes by row key, and the commit steps never rewrite an existing commit.

## 5. What you should get

| result | file | value |
|---|---|---|
| anchors | `results/anchors.json` | D1 (U_abs × S4) T10 α 2 attempted off-default 26/50 (exp29 25/50; per-slot agreement 0.98); D4 (U_bf × S5) correct off-default 1/50 (exp27 1/50) |
| S1 decision | `results/s1_2x2.json` | UNIT. T10 α 2 shares D1 0.50, D2 0.52, D3 0.10, D4 0.02; unit RD +0.45 [0.35, 0.55]; seed +0.03 [−0.07, 0.14]; interaction −0.10 [−0.28, 0.08]. T2 α 2 (N 100): unit +0.115 [0.06, 0.17] |
| D5 split | `results/s1_2x2.json` → `D5_split` | U_bf\* 0.28; profile at matched energy +0.22 [0.08, 0.36]; energy at the ban-free shape +0.18 [0.06, 0.30] |
| S2 | `results/s2_profile.json` | T10: P_top 29/50 vs P_rest 15/50 (McNemar 18:4, Holm p 0.009); D1 25/50 vs P_shuf 4/50 (21:0) → "pushes act where bans write" |
| S3 | `results/s3_prices.json` | D\* = D1. H5 PN\* vs base intent: T03 3.22 vs 1.73 WIN, T10 2.13 vs 2.53 LOSS, T2 1.21 vs 1.45 LOSS, T05 1.10 vs 1.61 LOSS, T1 1.39 vs 1.05 WIN (2 of 5). Iteration 5's rule replayed: 2 of 5, DISCONFIRMED; D̄ = +0.12 [−0.18, 0.27] |
| re-tag | `results/retag.json` | T03 and T10 movable at D\*; T2, T05 and T1 not |
| novelty | `results/novelty_audit.json` | 5 correct "other" programs, all catalogue variants; 0 novel |
| E1 / E2 / E3 (exploratory) | `results/e1_sweep.json`, `e2_geometry.json`, `e3_replicate.json` | U_bf needs α ≈ 4 (20/50) to approach U_abs at α 2. Escape is near-independent across directions on one stream (φ 0.16–0.20). Fresh T10 slots: unit +0.42 [0.32, 0.52]. T03: unit +0.27 [0.18, 0.37] |
| audits | `results/cpu_gates.json`, `unit_tests_gpu.json`, `rederive.json`, `commit_audit.json`, `commit_chain_verify.json` | all pass; the re-derivation has 0 mismatches and the placebos stay null |
| per-slot outputs | `method_out.json` (+ `full_`/`mini_`/`preview_`) | `exp_gen_sol_out`, 6 datasets, 1,000 examples |

Figures are in `figures/` (F1–F7, E1, E3); the README maps each one to its result. Monte-Carlo quantities (the hull
H5, bootstraps and sign-flip p) are seeded and reproduce exactly on the same software stack.
