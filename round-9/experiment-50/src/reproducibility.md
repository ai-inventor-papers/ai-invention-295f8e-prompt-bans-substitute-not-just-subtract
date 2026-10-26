# Reproducibility: where tuning sharpened the algorithm choice (iteration 9, claims B1-B3)

This file describes what was actually run, in order, to produce every number in `results/`, `figures/` and
`method_out.json`. All paths are relative to this folder.

## 1. Get the artifact

This folder is published as one folder of a public GitHub repository. Clone the repository and `cd` into this
folder. Everything the code reads from earlier artifacts is already copied here under `vendor/<artifact id>/`
(sha256 of every file in `vendor/inputs.json`), so no other folder is needed for the analysis. Only
`src/s0_preflight.py` (re-vendoring) reads the source artifacts themselves; it looks for them, in order, at the path in
the environment variable `ART_<ARTIFACT_ID>_DIR` (e.g. `ART_ART_18XVFCJJZI1O_DIR`), at the published sibling folder
`../<artifact id>` (e.g. `../art_18XvfcJJZi1O`), and at the original run layout. The declared dataset dependency is
`art_j3Rm_lr2nzR6` (only its preview/mini files are vendored; it served as context, the novelty audit needed no
known-solution lookup). No user-uploaded file is used.

## 2. System, Python and packages

* Ubuntu (Debian 12 container was used), NVIDIA driver with CUDA 12.x (driver 595.91.07 was used), `uv` installed.
* Python 3.12 (3.12.14 used). Create the environment exactly as pinned in `pyproject.toml` (85 packages; torch
  2.8.0+cu128 from PyPI, transformers 4.57.6, numpy 2.2.6, scipy 1.18.1, matplotlib 3.11.2, safetensors 0.8.0,
  loguru 0.7.3, ...):

```bash
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r pyproject.toml
```

## 3. Models, data and credentials

* Environment variables (names only): `HF_TOKEN` (needs access to the gated `google/gemma-3-4b-*` and
  `meta-llama/Llama-3.1-8B*` repositories); optionally `HF_HOME` / `HF_HUB_CACHE` to choose the weight cache.
  `OPENROUTER_API_KEY` / `OPENROUTER_BASE_URL` are only read if a labeller disagreement or a novelty audit needs a
  judge; none was needed in this run (USD 0 spent).
* Download the six models at the pinned revisions (about 65 GB):

```bash
.venv/bin/python src/download_models.py
```

| key | repository | revision |
|---|---|---|
| qwen | Qwen/Qwen3-8B | b968826d9c46dd6066d109eabc6255188de91218 |
| qwen_base | Qwen/Qwen3-8B-Base | 49e3418fbbbca6ecbdf9608b4d22e5a407081db4 |
| gemma | google/gemma-3-4b-it | 093f9f388b31de276ce2de164bdc2081324b9767 |
| gemma_pt | google/gemma-3-4b-pt | cc012e0a6d0787b4adcc0fa2c4da74402494554d |
| llama | meta-llama/Llama-3.1-8B-Instruct | 0e9e39f249a16976918f6564b8830bc894c89659 |
| llama_base | meta-llama/Llama-3.1-8B | d04e592bb4f6aa9cfee91e2e20afa771667e1d4b |

## 4. Commands, in the order they were run

Hardware: one NVIDIA L4 (23 GB VRAM), 6 CPU cores, 57 GB RAM (container limits). All models in bf16 with SDPA
attention; only one model on the GPU at a time. Total GPU time ≈ 1.0 h (1.03 h including the superseded v1 B2 pass; per-stage seconds in
`results/stage_timing.jsonl`).

```bash
.venv/bin/python method.py --stages preflight,units,tests,commit0   # CPU, ~5 min; COMMIT #0 after the CPU tests pass
.venv/bin/python method.py --stages cache_qwen                      # Qwen3-8B then Qwen3-8B-Base captures (+ random sets, REV arm), ~6 min
.venv/bin/python method.py --stages patch_qwen                      # B2 one-token CMAP sweep etc., ~8 min
.venv/bin/python method.py --stages b3                              # B3 (writes COMMIT B3 before the held-out rerun), ~17 min
.venv/bin/python method.py --stages b1                              # Gemma it/pt, Llama instruct/base, ~8 min
.venv/bin/python method.py --stages commit0b,analyze                # commits analysis9.py, then applies the rules
.venv/bin/python method.py --stages generate                        # COMMIT #1 then 240 programs, labels, McNemar, ~5 min
.venv/bin/python method.py --stages figures,positioning,rederive,outputs
```

Notes on what actually happened (also in `results/deviations.json`):

* The first B2 pass (variable batch shapes, full-forward caches) is archived in `results/v1_variable_batch/`; the
  primary pass reran `cache_qwen` and `patch_qwen` with fixed batch shapes (40 one-token rows / 8 full-forward rows)
  and one-token-path caches. Re-running the two stages above reproduces the primary pass.
* `positioning` writes a fixed record of the dated literature check (2026-10-23, WebSearch/WebFetch); it does not
  search again.
* Seeds: random component sets 90901 + unit index (B3 0, T10 1); SPEC random sets 90901 + 100 + unit index;
  bootstrap 20261023 (10,000 resamples); B1 random-position control 20261023 + 5; generation CRN slots seeds
  9101-9130 (one uniform per generated token, float64 inverse CDF over the vocabulary in token-id order, T 1).
* bf16 numerics depend on the GPU model and batch shapes: on an L4 the iteration-8 exp41 margins reproduce exactly
  (max |diff| 0.0 on all 40 B2 prompts); on other GPUs expect differences of up to ~0.2 nats per margin.

## 5. What you should get

| output | where | value in this run |
|---|---|---|
| B1 verdict (committed P1-P4) | `results/b1_summary.json` | PARTIAL (P1 False, P2 True, P3 False, P4 False) |
| B1 Gemma gains (chat) | `results/b1_gemma_*.json` | G-GRID@32 1.78, G-T04@31 1.75, G-R6@12 3.07, G-R6@24 1.68 nats |
| B2 verdict (committed Q1-Q3) | `results/b2_summary.json` | PARTIAL (Q1 False, Q2 False, Q3 True); localisation 'distributed' |
| B2 FSTACK share | `results/b2_summary.json` | MST 0.998 (random-set p = 0.45); CC 0.452 (p = 0.020) |
| B2 unembedding-only share | `results/b2_summary.json` (`readout_decomposition_cpu`) | MST 0.43; CC 0.85 |
| B2 generation | `results/b2_generation.json` | MST Prim: TWIN 0, FSTACK 19, RAND 19, FPD 18 of 30; CC DFS: 1, 1, 0, 18 of 30 |
| B3 held-out layer-0 COND MLP | `results/b3_summary.json` | ablate mean d 3.86 (p 0.0625); steer 3.85 (p 0.023) |
| re-derivation | `results/rederive.json` | 0 mismatches; placebos fail as required |
| commitment chain | `commitments.log`, `predictions/` | 4 commits (commit0, commitB3, commit0b, commit1_gen), all links verify |
| per-example output | `method_out.json` (+ full/mini/preview) | 370 examples in 4 datasets, schema exp_gen_sol_out |

In the paper these numbers appear in the B1 table (fork margins, JS controls; figures F1, F2), the B2 table and
figures F3-F5 and F8 (patching shares, random nulls, residual swaps, activation geometry), the generation table and
F6, and the B3 paragraph and F7.
