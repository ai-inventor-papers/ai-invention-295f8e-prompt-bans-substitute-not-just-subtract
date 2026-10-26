# Reproducing panel B (base-model variety vs push movability, Qwen3-8B)

This file describes what was actually run to produce this artifact, in order. Every path is relative to this folder.

## 1. Get the artifact

```bash
git clone <URL of the published repository>
cd <repository>/<this artifact's folder>     # the folder that holds this file, method.py and pyproject.toml
```

Inputs from other artifacts:

- **`art_j3Rm_lr2nzR6`** (dependency dataset; `full_data_out.json`). The repository publishes it as a sibling folder.
  It is read through ONE environment variable, `AII_DEP_ART_J3RM` (default: `../art_j3Rm_lr2nzR6`), by
  `src/extract_sources.py` and `tests/test_datasets.py`. Its extract is already in `inputs/sources.json`.
- Earlier-iteration code and data this artifact builds on (bench labellers, exp8 suite, exp17 prompts and directions,
  exp22 engine, exp23 `r_Q` table) are copied into `vendor/` with `vendor/SHA256SUMS`; nothing else is needed.
- The descriptive screen view reads a snapshot of the iteration-5 Step-1 base repertoire,
  `inputs/exp24_base_repertoire_snapshot.json` (sha256 in `results/screen_view.json`); override with
  `AII_STEP1_BASE_REPERTOIRE`.
- No user-uploaded inputs were used (the run's upload folder was empty).

## 2. System, Python and libraries

What was used:

- Debian 12 container (any recent Ubuntu works), NVIDIA driver 595.91 (CUDA runtime reported 13.2), **one NVIDIA
  GeForce RTX 4090, 24 GiB**; 14 CPU cores and 56 GB RAM (container limits).
- Python **3.12.14**, **uv 0.6.14**. No system packages beyond the NVIDIA driver; `git` for cloning.
- Environment: `uv sync` builds `.venv` from `pyproject.toml` / `uv.lock`. Every one of the 85 packages is pinned to the
  version that was installed (`uv pip freeze`), among them `torch==2.8.0` (CUDA 12.8 wheels), `transformers==4.57.6`,
  `accelerate==1.15.0`, `numpy==2.2.6`, `scipy==1.18.1`, `openai==3.35.1`, `zss==1.2.0`, `jsonschema==4.25.1`.
  What was actually run: `uv sync` with the first pyproject, then
  `uv pip install --python .venv/bin/python zss==1.2.0 jsonschema==4.25.1`; both are now in `pyproject.toml`, so
  `uv sync` alone gives the same environment.

```bash
uv sync
```

## 3. Downloads, environment variables and keys

Models (Hugging Face cache, never inside this folder):

```bash
hf download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218 --include "*.json" "*.safetensors" "*.txt"
hf download Qwen/Qwen3-8B-Base --revision 49e3418fbbbca6ecbdf9608b4d22e5a407081db4 --include "*.json" "*.safetensors" "*.txt"
```

(The base model was downloaded without `--revision`; it resolved to `49e3418f...`, which is pinned in `src/cfg5.py`.)

Environment variables, by name:

| name | needed for |
|---|---|
| `HF_HOME` / `HF_HUB_CACHE` | the model cache (`src/cfg5.py:model_path`) |
| `OPENROUTER_BASE_URL`, `OPENROUTER_API_KEY` | blind judges (`src/judge5.py`); about USD 0.19 was spent. Every judge response is cached in `data/judge_cache.jsonl` / `data/novelty_cache.jsonl`, so re-running the analysis makes no new calls |
| `AII_DEP_ART_J3RM` | the dependency dataset folder (see section 1) |
| `AII_DATA_FIG_GEN_SCRIPTS` | the `scripts/` folder of the aii-data-fig-gen skill (house style and chart generator) for `src/figures.py` |
| `AII_STEP1_BASE_REPERTOIRE` | optional, the Step-1 base repertoire for `analysis/screen_view.py` |

## 4. Commands, in the order they were run

Seeds: CRN uniforms `PCG64(stable_seed(unit, template, slot))` (`src/engine5.py:u_stream`); push directions
`PCG64(seed(unit, k)).standard_normal(4096)` with `seed(unit, k) = int(sha256('iter5|panelB|{unit}|dir|{k}')[:8], 16)`
(variants and parents use the parent's seeds); plan-noise directions `pn_seed(unit, arm, template, slot)`; hidden-test
generators `random.Random(268 / 136 / 1135 / 69 / 78 / 242 / 4242)`; analysis RNGs fixed in each script. Decoding:
T = 1.0, top-p 1, no top-k, thinking off, max 1024 new tokens, fence stop; batches of exactly 20 rows; bf16.

| # | command | what it does | time |
|---|---|---|---|
| 1 | `uv run src/extract_sources.py` | rows of the dependency dataset -> `inputs/sources.json` | 10 s |
| 2 | `uv run src/build_prompts.py` | prompts for B1-B7 (twins, novelty, association, plain) -> `data/prompts.jsonl` | 20 s |
| 3 | `uv run src/protocol0.py` | commit #0: `predictions/precision.json`, `predictions/protocol_v5_panelB.json` | 10 s |
| 4 | `uv run src/gpu_main.py --model instruct --phases tests,engine,inst1 --units B1,B2,B3,B4,B5,B6,B7 --deadline-min 120 --tag _i1` | GPU tests U1-U4, engine check, twins + gate draws, novelty, association | 6 min |
| 5 | `uv run src/gpu_main.py --model base --phases base1 --units B1,...,B7 --deadline-min 90 --tag _b1` | base chat N = 100 + plain completion N = 50 | 20 min |
| 6 | `uv run src/unitbuild.py B1` ... `B7` (run in parallel) | hidden tests, two oracles, reference timing, mutants, excluded methods, labellers on references (gate stage i) | 1 min each |
| 7 | `uv run src/label5.py` (left running in the background) | label worker (tests, runtime tracer, AST) | concurrent |
| 8 | `uv run src/gpu_main.py --model instruct --phases margins --units B1,...,B7 --tag _margins` | opening log-probs for R_margin | 1 min |
| 9 | `uv run src/judge5.py controls` (from `src/`) | judge control gate (6/6, 6/6, 5/6) | 1 min |
| 10 | `uv run src/gpu_main.py --model base --phases base1 --units B1,...,B7 --n-base 40 --n-plain 50 --tag _b2` | raises the base repertoire to N = 200 (deviation `base_n_200`) | 16 min |
| 11 | `uv run src/gate2.py B1,B2,B3,B4,B5,B6,B7` | gate stage (ii): B1, B2, B6 gated; B3, B4, B5, B7 failed narrowly | 3 min |
| 12 | rule fixes in `src/units/b3.py`, `b4.py`, `b7.py`, abstention-aware metrics in `src/gate2.py`; `uv run src/unitbuild.py B3` (and B4, B5, B7); delete those units' rows from `data/labels.jsonl` and restart the worker; then `uv run src/gate2.py B3,B4,B5,B7 --revision` | the single revision round, with a 6-program holdout | 10 min |
| 13 | `uv run tests/test_analysis.py`; `uv run src/commit_steps.py commit1` | analysis code on synthetic units; commit #1 (analysis code, gates, catalogues) | 1 min |
| 14 | `uv run src/quantities.py B1,B2,B3,B4,B5,B6` then `uv run src/quantities.py B7` | per-unit predictions + base audits + grep audit -> `predictions/units/B*.json`, hash-chained | 5 min |
| 15 | `uv run src/gpu_main.py --model instruct --phases push --units B1,...,B7 --deadline-min 150 --arms esc,pn1,pn2,t13,conf --tag _push` | escape population + confirmations, PN alpha 1 and 2, T1.3 | 14 min |
| 16 | `uv run src/units_extra.py` | disguised-variant prompts (8 parents) + parents' labellers on references | 1 min |
| 17 | `uv run src/gpu_main.py --model instruct --phases extra_inst --pairs T03,T10,T05,T06 --tag _xi` and `uv run src/gpu_main.py --model base --phases extra_base --pairs T03,T10,T05,T06 --tag _xb` | parent/variant twins and bases | 20 min |
| 18 | `uv run src/commit_steps.py commit2` | commit of the analysis addendum and the extra-arm build | 10 s |
| 19 | `uv run src/quantities_extra.py P_T03,V_T03,P_T10,V_T10,P_T05,V_T05`, later `P_T06,V_T06` | parent/variant predictions (variant judge spot-checks) | 2 min |
| 20 | `uv run src/gpu_main.py --model instruct --phases extra_inst,push --pairs T04,T08,T14,R1 --units P_T03,V_T03,P_T10,V_T10,P_T05,V_T05 --arms esc,conf --tag _xp1` | new-pair twins; escape arms of six P_/V_ units | 8 min |
| 21 | `uv run src/gpu_main.py --model base --phases extra_base --pairs T04,T08,T14,R1 --tag _xb2` | bases of the last four pairs | 19 min |
| 22 | `uv run src/quantities_extra.py P_T04,V_T04,P_T08,V_T08,P_T14,V_T14,P_R1,V_R1`; `uv run src/gpu_main.py --model instruct --phases push --units P_T06,V_T06,P_T04,V_T04,P_T08,V_T08,P_T14,V_T14,P_R1,V_R1 --arms esc,conf --tag _xp2` | last commits and escape arms | 8 min |
| 23 | `uv run method.py` (stage `final`) | adjudication, engine check, A1/A2, variants, extended views, screen view, novelty audit, re-derivation, commit order, tests, vendor check, figures, outputs | 15 min |
| 24 | `uv run audit/rederive_headlines.py`; `uv run src/readme_fill.py`; the aii-json format script on `method_out.json` | headline re-derivation with placebos; README; full/mini/preview outputs | 3 min |

Steps 4-22 together used 1.74 GPU-hours of sampling (`results/timing_summary.json`); the whole run took about 3.5 hours
of wall clock. GPU sampling is deterministic on the same GPU, driver and library versions (test U1); on another GPU the
bf16 numerics can change individual tokens (compare the engine check, bf16 here vs FP8 in iteration 4).

To re-run only the CPU analysis from the shipped rows (no GPU, no new judge calls):

```bash
export AII_DEP_ART_J3RM=../art_j3Rm_lr2nzR6 AII_DATA_FIG_GEN_SCRIPTS=<aii-data-fig-gen>/scripts
uv run method.py
uv run audit/rederive_headlines.py
```

## 5. What you should get

| file | number |
|---|---|
| `results/a1_panel.json` | A1: Spearman rho(beta_u, E_u) = 0.206, exact one-sided permutation p = 0.333 (n = 7); secondary rho(beta_u, PN excess) = 0.821, p = 0.017 |
| `results/a2_panel.json` | A2: top-1 hits 3 of 4 events (chance 1.2), exact Poisson-binomial p = 0.081; BASE minus ASSOC log score +0.68 nats |
| `results/a1_extended.json` | new units + parents rho = 0.43 (p = 0.055, n = 15); clustered rho = 0.54 (p = 0.015, n = 22) |
| `results/variants.json` | 8 pairs; escapes only for T03 (E 0.50 -> 0.75) and T10 (0.19 -> 0.31, default shift); the rest E = 0 |
| `results/screen_view.json` | descriptive cross-engine view on 15 screen tasks: rho = 0.79 |
| `results/engine_check.json` | T03 within the template-resampling null; T2 outside (bf16 precision sensitivity) |
| `results/novelty_audit.json` | 0 novel algorithms among 12 distinct correct 'other' programs (10,366 correct programs) |
| `results/rederive.json`, `results/rederive_headlines.json` | 0 mismatches; placebos fail (shuffled beta p < 0.05 in 6%, shuffled r_u mean hits 0.75, twin-as-push E = 0) |
| `method_out.json` (+ `full_`, `mini_`, `preview_`), `pooled_inputs.json`, `figures/F1-F6` | the per-unit and per-cell outputs, the pooled-input records and the figures |

These are the panel-B entries of the paper's A1/A2 results (the per-unit table, the rival comparison, the A2 events) and
its figures F1-F6; the pooled panel A + B test is run in the next round from `pooled_inputs.json`.
