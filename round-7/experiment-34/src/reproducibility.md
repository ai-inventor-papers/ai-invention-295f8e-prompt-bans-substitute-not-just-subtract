# Reproducing "Does one early token decide the algorithm?" (iteration 7, bf16 Qwen3-8B)

This file records what was actually run, in order. Every path is relative to this artifact's folder.

## 1. Get the artifact

This folder is published as one folder of a public GitHub repository:

```bash
git clone <repository URL>
cd <repository>/<this artifact's folder>     # the folder that holds this file, method.py and src/
```

Earlier artifacts that this one reads are already copied inside the folder, under `vendor/` (code) and `inputs/`
(data). Their checksums are in `predictions/commit0.json` (`inputs_sha256`). The artifact ids are:

| copy here | artifact | what is used |
|---|---|---|
| `vendor/exp29/`, `inputs/exp29/` | `art_lpQalcAXMGr1` (iteration-6 exp29) | engine-d weight set, Runner design, escape rule, labeller wrapper, the 40 directions' engine-d outcome rows, realised norms |
| `vendor/exp29/vendor/exp22/` | `art_SHaWv77P1XCI` (iteration-4 exp22) and its inputs | prompts4, ctx4 (`push_spec`, `ban_unit`, `rand_dir`), engine4 sampler, exp8 suite / exp11 bench labellers, exp13/exp17 units |
| `vendor/exp30/`, `inputs/exp30/` | `art_rMlbrjVB1c__` (iteration-6 exp30) | prompts6 (top5ban, placebo), the Stage A / BAN / FORCED / TWIN rows, T1 geometry states |
| `vendor/exp31/fork.py` | `art_zNyBP6zieI5u` (iteration-6 exp31) | change-point code |
| `vendor/exp9/` | `art_IVZc3TWCeE9f` (iteration-2 exp9) | 10-algorithm T1 labeller (AST), frozen forced prompts, catalogue_keep.json |
| `inputs/exp20/` | `art_Cx9JOh8soBw7` (iteration-4 exp20) | old u_top5 push (comparison only) |

The declared dataset dependency `art_j3Rm_lr2nzR6` (the iteration-1 dataset, `full_data_out.json`) is read once, by
`src/dep7.py`, through the environment variable `AII_DEP_ART_J3RM`. Its default is `../art_j3Rm_lr2nzR6`, the sibling
folder in the published repository. It only feeds the novelty audit's known-solution corpus. No user-uploaded input
was used (the run's upload folder was empty).

## 2. System, Python and libraries

- OS: Debian 12 / Ubuntu 22.04 or 24.04, x86-64. An NVIDIA driver with CUDA 12.8 support is needed (the run used driver
  595.91). The CUDA libraries come from the pinned wheels.
- Python 3.12.14, installed by `uv`.
- Hardware actually used: 1x NVIDIA GeForce RTX 4090 (24 GB; 23.5 GiB visible), 11 CPU cores (cgroup quota), 57 GB RAM.
  The model (16.4 GB bf16) plus a batch of 24 rows x 1,024 new tokens peaks at about 18.6 GiB.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh        # if uv is missing
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r pyproject.toml     # 83 exact pins (torch 2.8.0, transformers 4.57.6, ...)
```

`pyproject.toml` lists every installed package at its exact version (`uv pip freeze`; the venv has no `pip`).

## 3. Downloads, environment variables and keys (names only)

- Model: `Qwen/Qwen3-8B` at revision `b968826d9c46dd6066d109eabc6255188de91218` (about 16.4 GB):
  `huggingface-cli download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218`.
  The code reads the snapshot from `HF_HUB_CACHE/models--Qwen--Qwen3-8B/snapshots/<revision>`; set `HF_HUB_CACHE`
  (and `HF_HOME`) to your cache. `HF_TOKEN` is optional.
- `OPENROUTER_BASE_URL`, `OPENROUTER_API_KEY` are used only by:
  - the frozen labeller's blind judge on runtime/AST disagreements;
  - the novelty audit (`src/novelty7.py`; google/gemini-2.5-flash-lite, mistralai/mistral-small-3.2-24b-instruct, a
    deepseek resolver).

  The run spent USD 0.028 in total. Without the key, disagreements become `disputed` and the audit stays `unaudited`.
- `AII_DEP_ART_J3RM`: path to the `art_j3Rm_lr2nzR6` folder (optional; see section 1).
- `AII_EARLIER_ARTIFACT_ROOTS` (optional, `:`-separated): extra folders for the seed-disjointness scan in
  `src/axis7.py`. The committed run scanned the earlier iterations' artifact folders (4,551 direction files). By
  default the vendored copies are scanned.

## 4. Commands, in the order they were run

Run everything from this folder with `.venv/bin/python`. `python method.py --stages all` runs the same chain in the
same order and is resumable. Row keys and commit files make every stage skip finished work. The run below took
about 3 hours of wall-clock, with the GPU busy about 1.7 hours.

| # | command | what it does | time |
|---|---|---|---|
| 0 | `python src/smoke.py` | engine smoke test (one T10 and one T2 batch) | 3 min |
| 1 | `python src/make_commit0.py` | commit #0: rules, thresholds, input hashes -> `commitments.log` | <1 min |
| 2 | `python src/label7.py &` | follow-mode label worker on `data/samples_raw.jsonl` (CPU, 6 threads), left running | - |
| 3 | `python src/stage0.py` | GPU unit tests, Stage 0a twins (T2, T03, T10, T1; W1-W5 x k 0-5), Stage 0b POP 9101-9105 (sealed to `data/samples_raw_s0b.jsonl`), 0c norms | 6 min |
| 4 | `python src/forkrun.py --paths 6 --tasks T2,T10,T03 --define` | prefix-resampling screen, change points, localisation, S = 20 confirmation, fork definitions | 15 min |
| 5 | `python src/axis7.py` | difference-in-means axis, U4, P_t, natural-variance check, seed disjointness -> commit #2 | 3 min |
| 6 | `python src/make_commit0b.py` | analysis code frozen by hash (commit #0b) | <1 min |
| 7 | `python src/predict7.py --tiers 1,2,3` | predictors, margins, opening LLR for every cell -> commit #3 | 9 min |
| 8 | `python src/predict7.py --tiers 1,2,3 --tasks T10,T03 --merge` | commit #3b (fork-file and T03-LLR fixes; before any outcome row) | 6 min |
| 9 | `bash run_after_c3.sh` | label worker on the sealed rows; `src/pushrun.py t03,targeted,top5core,top5,remeasure,clamp`; `src/analysis7.py`; `src/select_clamp.py` | 25 min |
| 10 | `python src/label7.py data/samples_raw_clamp.jsonl data/labels_clamp.jsonl` | labels of the clamp rows | 1 min |
| 11 | `bash run_gpu_tail.sh` | `src/pushrun.py targeted_ext` (fallback-8 doses 2/4/8), `src/explore_llr.py` (exploratory) | 12 min |
| 12 | `python src/force_token.py` then `python src/label7.py --once data/samples_raw_force.jsonl data/labels_force.jsonl` | exploratory forced-token test | 6 min |
| 13 | `python src/fork_probs.py` | T10 fork-token probabilities for the audit | 3 min |
| 14 | `python src/tests_cpu.py`, `python src/dep7.py`, `python src/top5geo.py` | CPU tests C1-C8; dependency corpus; T1 geometry (figure F6) | 5 min |
| 15 | `python src/analysis7.py`, `python src/analysis_push.py`, `python src/analysis_force.py`, `python src/novelty7.py`, `python src/summary7.py`, `python src/figures7.py` | analyses, novelty audit, figures F1-F7 | 3 min |
| 16 | `python src/outputs7.py`, `python3 -I audit/rederive.py`, `python src/readme7.py` | `method_out.json`, independent stdlib re-derivation, README results | 3 min |
| 17 | aii-json `aii_json_format_mini_preview.py --input method_out.json`; `aii_json_validate_schema.py --format exp_gen_sol_out` | `full_`/`mini_`/`preview_method_out.json`, schema check | <1 min |

Steps 4, 7 and 8 of the committed run differed from a clean rerun in three ways, all recorded in
`results/deviations.jsonl`:

- `forkrun.py --define` was run three times. The first run wrote commit #1. The pre-declared 128-token extension and a
  fork-merge fix were then added (commit #1b). Removing the 2-token merge and adding the sequential multi-fork rule
  gave commit #1c.
- The opening-classifier rules were tightened before commit #1.
- `predict7.py` was re-run for T10/T03 (commit #3b).

A clean rerun with the final code goes straight to the final definitions.

Seeds and randomness:

- **CRN uniforms**: `u_stream(task, template, k)` = PCG64(`sha256('task|template|k') mod 2^63`), identical in every arm.
- **Directions**:
  - iteration 4's `rand_9101..9140` (PCG64 normal, normalised);
  - fresh T03 directions 97001-97024;
  - matched random targeted-push directions 98001-98004;
  - random clamp directions 98101/98102.
- **Per-sample keys**:
  - fork-continuation keys (`task`, 'fork', path id, t, i);
  - RSURV survivor draw `stable_seed('T1','RSURV',w,k)`.
- **Statistics**: bootstrap and permutation seeds are fixed in `src/stats7.py`, `src/analysis7.py` and
  `audit/rederive.py`.

bf16 kernels differ between GPUs. A rerun on another card reproduces the statistics, not the bytes. Stage 0 measured
per-slot label agreement of 0.97-1.00 for twins against the RTX 2000 Ada engine, and 0.90-0.97 for pushed rows.

## 5. What you should get

| number | value in this run | file and field |
|---|---|---|
| T10 forks (generated tokens) | 10 and 11 | `results/forks.json` -> `tasks.T10.forks` (figure F1) |
| F, T10: Spearman(m, y) over 40 directions | 0.80 (perm p 1e-4; tie ceiling 0.99) | `results/f_analysis.json` -> `F.T10` (figure F2) |
| F, T2: Spearman (48-token LLR fallback) | 0.15 (p 0.18) | `results/f_analysis.json` -> `F.T2` |
| F pooled / held-out calibration MAE | 0.48 / 0.25 | `F.pooled`, `F.calibration.mae_heldout_mean` |
| Committed verdicts (Holm p) | F NOT SUPPORTED (0.36), P2 DISCONFIRMED (0.46) | `results/f_analysis.json` -> `verdicts` |
| T03 prospective confirmation, committed margin | Spearman 0.60 (one-sided p 0.0014) | `results/t03_confirmation.json` -> `m` |
| P2 axis projection, T10 / T2 | 0.17 / 0.01 | `results/p2_analysis.json` -> `P2` (figures F3, F4) |
| Clamp escapes: push only / axis clamp / random clamp | 104 / 105 / 106 | `results/clamp.json` -> `pooled` (figure F7) |
| Targeted push, T10, s = 4: axis vs random | 29/30 DFS vs 0/30 | `results/targeted_push.json` -> `T10.arms` (figure F5) |
| T1 in-manifold pushes: non-top-five programs | 0/300 | `results/top5_landing.json`; geometry `results/top5_geometry.json` (figure F6) |
| Same-engine re-measurement: y correlation with exp29 | 0.95 (T10), 0.93 (T2) | `results/remeasure.json` |
| Forced token `def dfs` under the twin (exploratory) | 30/30 DFS | `results/force_token.json` |
| Independent audit | 199 checks, 0 mismatches; every placebo fails | `results/rederive.json` |

The paper's results section uses these numbers and figures F1-F7 (`figures/*.pdf`). `README.md` gives the full
reading, and `results/deviations.jsonl` lists every deviation from the plan.
