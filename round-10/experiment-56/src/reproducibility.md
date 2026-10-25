# Reproducing BASE-W (iteration 10): which weights hold the default algorithm

This file states what was actually run, in the order it ran, on the machine it ran on. All paths are relative to this
artifact's folder.

## 1. Get the artifact

This workspace is published as one folder of a public GitHub repository.

```bash
git clone <the repository URL>
cd <repository>/<this artifact's folder>        # the folder that contains this file, method.py and README.md
```

Everything the code reads from other artifacts is vendored here with sha256 (`inputs_manifest.json`):
* `inputs/iter9/` is the iteration-9 artifact **art_cDba8_DycUJd**: units, summaries, labels, programs, its code and
  the frozen labeller tree.
* `inputs/art_j3Rm_lr2nzR6/` is the declared dependency **art_j3Rm_lr2nzR6**, the iteration-1 dataset: preview and
  mini files, and the LeetCode 323/547 subset of its `full_data_out.json`.

The code resolves each input in one place, `src/cfg10.py`, in this order:
1. the environment variable (`ART_CDBA8_DIR`, `ART_J3RM_DIR`);
2. else the sibling folder named by the artifact id (`../art_cDba8_DycUJd`, `../art_j3Rm_lr2nzR6`), which is how the
   repository publishes artifacts;
3. else the vendored copy.

No user-uploaded input was used; the run's `user_uploads` folder was empty.

## 2. System, Python and libraries

**What the run used:**
* Container: Debian GNU/Linux 12 (bookworm), Linux 6.8.
* GPU: one NVIDIA GeForce RTX 4090 (24 GB) with driver 595.91.07 (CUDA 13.2). The PyTorch wheels bundle the CUDA 12.8
  runtime.
* Limits: 14 CPUs and 56 GB RAM (cgroup).
* Python 3.12.14 and uv 0.6.14.

Any Ubuntu 22.04/24.04 machine with an NVIDIA driver that supports CUDA 12.8 and at least 24 GB of VRAM should work;
smaller GPUs need the plan's B_ot fallback.

```bash
# system: python3.12 and uv (https://docs.astral.sh/uv/); git; an NVIDIA driver supporting CUDA 12.8
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r pyproject.toml
```

* **Pinned versions.** `pyproject.toml` pins all 85 packages to the exact versions in the run's `.venv`. The check was
  `uv pip freeze --python .venv/bin/python`, saved in `logs/uv_pip_freeze.txt`; the uv venv has no pip.
* **Key versions:** torch 2.8.0 (+cu128, PyPI default wheels), transformers 4.57.6, tokenizers 0.22.2, safetensors
  0.8.0, accelerate 1.15.0, huggingface-hub 0.36.2, numpy 2.2.6, scipy 1.18.1, scikit-learn 1.9.1, matplotlib 3.11.2,
  loguru 0.7.3. `predictions/env.json` records the versions actually imported.

## 3. Models, environment variables, keys

```bash
bash scripts/download_models.sh     # hf download <repo> --revision <sha> into $HF_HUB_CACHE (or ~/.cache/huggingface/hub)
```

The pinned revisions are:
* Qwen/Qwen3-8B b968826d9c46dd6066d109eabc6255188de91218
* Qwen/Qwen3-8B-Base 49e3418fbbbca6ecbdf9608b4d22e5a407081db4
* google/gemma-3-4b-it 093f9f388b31de276ce2de164bdc2081324b9767
* google/gemma-3-4b-pt cc012e0a6d0787b4adcc0fa2c4da74402494554d

Together they take about 52 GB of disk.

Environment variables (names only; none is required to rerun from the vendored copies):
* `HF_TOKEN`: a Hugging Face token with access to the gated Gemma 3 weights.
* `HF_HUB_CACHE` / `HF_HOME`: where the weights live; the code looks up the pinned snapshot there.
* `ART_CDBA8_DIR`, `ART_J3RM_DIR`: optional input locations (section 1).
* `AII_JSON_SKILL_DIR`: optional. It lets `method.py` run the AI Inventor schema validator and the mini/preview
  generator.
* `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`: set by `method.py` for every GPU stage.

No API key was used. OpenRouter was never called (no correct 'other' program needed a judge): USD 0.

## 4. Commands, in the order they ran

One command reproduces everything:

```bash
.venv/bin/python method.py --stages all      # s_1, s0, w1tf, w1gen, ext, w2, w3, out
```

Each stage script runs in its own process, one model on the GPU at a time. PIDs go to `logs/pids.jsonl`, logs to
`logs/`, and milestones to `logs/time_ledger.jsonl`. The actual run issued the same scripts by hand, in this order.
All commands below run from `src/` with `../.venv/bin/python`.

| # | command | what it does | wall time on the RTX 4090 |
|---|---|---|---|
| 1 | `inputs10.py copy`, `inputs10.py hardware`, `inputs10.py gate` | vendor + hash the inputs; hardware/env record; labeller gate (240/240) | ~1 min |
| 2 | `protocol10.py commit0` | COMMIT #0, before any model forward | s |
| 3 | `capture10.py qwen 2` (smoke), then `capture10.py qwen all`, `capture10.py qwen_base all` | stage-0 fork states (B_ot = 40), engine check, batch sweep, residual PCA | ~2 min each incl. 23 s load |
| 4 | `w1_tf.py s0report`; `debug_s0.py qwen`; `debug_s0.py qwen_base` | reproduction table; numerics-floor sweep (debug round 1) | ~3 min |
| 5 | `w1_tf.py nulls` | 3 x 50 null row draws from the committed seeds + COMMIT #1 | ~30 s |
| 6 | `w1_tf.py score` | every W1 arm and null + COMMIT #2 (generation predictions) | ~1 min |
| 7 | `w1_gen.py gpu 2400`, `w1_gen.py label`, `w1_gen.py g5`, `w1_gen.py analyze` | W1 generation: 7 arms x 30 CRN slots x 2 units, B = 6 per batch | ~8 min + ~1 min |
| 8 | `w2_swap.py match` | Hungarian matching + COMMIT #3. The first attempt stopped on a key-name bug before writing anything; fixed and rerun. | ~1 min |
| 9 | `w2_swap.py gpu 2` (smoke; its rows were deleted), then `w2_swap.py gpu all`, `w2_swap.py summary` | in-place weight swaps, both scopes | ~1.5 + ~5 min |
| 10 | `w3_gemma.py gpu gemma`, `w3_gemma.py gpu gemma_pt`, `w3_gemma.py score` | Gemma W3 | ~2 + ~3 min |
| 11 | `w1_tf.py export_zs`, `tests_cpu10.py`, `analysis10.py delta_geometry`, `positioning10.py`, `figures10.py` | audit inputs, tests, geometry, literature verdicts, figures | ~3 min |
| 12 | `w1_dose_gen.py commit`, `w1_dose_gen.py gpu` | extension 1: dose ×2/×3 (COMMIT #4) | ~4 min |
| 13 | `w1_dose_gen.py commit_strong`, `w1_dose_gen.py gpu_strong` | extension 2: strong nulls ×3 (COMMIT #5) | ~3 min |
| 14 | `w1_dose_gen.py commit_power`, `w1_dose_gen.py gpu_power`, then `w1_gen.py label`, `w1_gen.py analyze`, `w1_dose_gen.py analyze_power` | extension 3: 60 extra CRN slots (COMMIT #7) | ~6 min |
| 15 | `depcheck10.py` | the CC programs on the declared dependency's LeetCode 323/547 I/O pairs | ~10 s |
| 16 | final code snapshots (COMMITs #8–#11), `tests_cpu10.py`, `python3 -I ../audit/rederive.py`, `analysis10.py summary`, `outputs10.py`, then the aii-json validator and `aii_json_format_mini_preview.py --input method_out.json` | audit, summary, `method_out.json` + full/mini/preview | ~3 min |
| 17 | `../.venv/bin/python ../audit/rederive_headline.py` (from `src/`) or `.venv/bin/python audit/rederive_headline.py` | independent float64 re-derivation of the headline numbers with placebos | ~1 min |

Total: about 1 GPU-hour including model loads.

**Seeds and configuration**, all in `src/cfg10.py` and committed in `predictions/commit0_protocol.json`:
* Null rows: RAND_ISO 101000, RAND_RESID 102000, DELTA_SWAP 103000, each + 100 × unit index + draw, with one
  `np.random.default_rng([seed, token id])` per row.
* Same-layer random weight deltas: torch CUDA generator seeds 104000 + 100 × draw + layer (×10 + matrix index); joint
  draws +5000.
* Generation: CRN uniforms `np.random.default_rng(9101 + slot)`. Slots 0–29 are W1–W5 × 6; the power extension uses
  slots 30–89.
* Bootstrap: 10,000 resamples, seed 20261024.
* Batch shapes: one-token B_ot = 40; generation B = 6.
* Generation lengths: MAX_NEW 1024 (CC) and 768 (MST), T = 1, top-p = 1.

**Re-running only the CPU analyses** (no GPU) uses the kept `cache/` and `results/`:

```bash
.venv/bin/python method.py --stages out
python3 -I audit/rederive.py
.venv/bin/python audit/rederive_headline.py
```

Re-running a committing stage rewrites committed files and appends new commits. bf16 numerics also depend on the GPU
model: on an L4, iteration 9's margins differed from this run's by up to 1.09 nats per prompt (README, Stage 0). Exact
margins therefore reproduce only on an RTX 4090 with the same stack. Shares computed from one run's own cached states
are internally consistent everywhere.

## 5. What you should get, and where it appears

All numbers are in `results/summary.json`, and the README tables report them. The downstream paper's tables and
figures are drawn from these files and from `figures/F1`–`F8`.

| claim | number | file |
|---|---|---|
| Stage 0 gaps (CC / MST) | 4.56 [3.58, 5.60] / 2.09 [1.98, 2.21] nats; CPU decomposition 0.842 / 0.416 | `results/stage0.json` |
| W1-TF CC, primary: base fork-class rows on the instruct residual | share 0.548 [0.440, 0.707]; RAND_ISO median 0.044, max 0.210, p = 0.020 → SUPPORTED; RAND_RESID p95 1.252 → "readout-level but not token-specific" | `results/w1_tf_summary.json`, F1–F3 |
| W1-TF breakdown | ROWS_A 0.489, ROWS_D 0.060, NORM 0.000; MST ROWS_ALL 1.249 | same |
| W1-GEN CC (30 CRN slots) | ROWS 5/30 vs TWIN 1/30 correct DFS (4:0, p = 0.125) → NOT SUPPORTED; FPD 15/30 | `results/w1_generation.json`, F4 |
| Power extension (90 pairs) | CC ROWS 21/90 vs TWIN 4/90 (17:0, p = 1.5e-5); MST 72/90 vs 17/90 | `results/w1_generation_power.json` |
| Dose extension | CC ROWS×2 21/30, ×3 30/30 vs RAND_MED×3 1/30 (29:0); RAND_RESID median×3 6/30, max×3 30/30 | `results/w1_generation.json`, F4 |
| W2 (late MLPs) | CC late joint −0.145 vs matched early joint 0.461 (diff −0.61 [−0.78, −0.48]) → rule fails | `results/w2_summary.json`, F7 |
| W3 Gemma | ROWS_ALL −0.253 [−0.41, −0.12] (rows widen the gap) | `results/w3_summary.json`, F8 |
| Audit | 425 checks, 0 mismatches; float64 re-derivation agrees to ≤ 4.4e-7; placebos fail | `results/rederive.json`, `results/rederive_headline.json` |
| Dependency check | 627/630 CC programs pass the LeetCode 323/547 pairs (agreement with the labeller 1.000) | `results/depcheck_leetcode.json` |

Generated programs and labels are in `data/gen_samples.jsonl` and `data/gen_labels.jsonl` (1,260 programs). The
per-example outputs are in `method_out.json` and its `full_`, `mini_` and `preview_` variants (exp_gen_sol_out schema).
