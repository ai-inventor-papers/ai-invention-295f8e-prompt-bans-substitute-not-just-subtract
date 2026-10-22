# Reproducing "Where noise changes the algorithm, in bf16"

This file describes what was actually run on 2026-10-21/22 (UTC), in order, and how to repeat it. Every path is
relative to this folder (the artifact's folder in the published repository).

## 1. Get the artifact

```bash
git clone <the published repository URL>
cd <repository>/<this artifact's folder>     # the folder that holds method.py, src/, inputs/, results/
```

Two items are not in the published folder:
- **Activation caches.** Files of 100 MB or more are not published: `cache/twin_states_*.pt`, about 250-350 MB
  each. `cache/` is also excluded from the upload. Every cache file is rebuilt by steps 1 and 9 of the table in
  section 4: `prep` gives the twin, forced and push states; `score` gives the code-opening states.
- **Model weights.** These are downloaded separately (step 3).

Everything else needed is in this folder:
- `inputs/` holds copies of the earlier-artifact files, with `inputs/SHA256SUMS`.
- `data/` holds the raw rows, labels and judge caches.
- `results/` holds every analysis JSON.

## 2. System, Python and libraries

- **OS.** Ubuntu or Debian (this run used Debian 12 in a container, Linux 6.8).
- **System packages.** `git`, `curl` and `build-essential`. No CUDA toolkit is needed: the torch wheel brings
  CUDA 12.8 runtime libraries. You need an NVIDIA driver that supports CUDA 12.8 (this run: driver 595.91).
- **Python.** 3.12 (this run: CPython 3.12.14), managed by [uv](https://docs.astral.sh/uv/) (`uv venv`, `uv pip`).
  pip is not used.
- **Libraries.** These are the exact versions installed, all 83 pinned in `pyproject.toml`; `uv.lock` matches it.
  Direct dependencies: torch 2.8.0 (cu128 wheel), transformers 4.57.6, accelerate 1.15.0, numpy 2.2.6, scipy 1.18.1,
  scikit-learn 1.9.1, statsmodels 0.15.0, pandas 3.0.6, matplotlib 3.11.2, networkx 3.7, loguru 0.7.3, openai 3.35.1,
  tenacity 9.2.1, psutil 7.2.2, ijson 3.4.0.

```bash
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r pyproject.toml
.venv/bin/python -c "import torch, transformers; print(torch.__version__, transformers.__version__, torch.cuda.is_available())"
```

Every stage below can also be run as `uv run method.py <stage>`.

## 3. Downloads and environment variables (names only)

- **Model.** Qwen/Qwen3-8B at revision `b968826d9c46dd6066d109eabc6255188de91218` (bf16 safetensors, about 16.4 GB).
  Download it with
  `huggingface-cli download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218`.
  The code finds the snapshot through `HF_HUB_CACHE` (or `HF_HOME`), and otherwise downloads it by id.
  `HF_TOKEN` is optional, because the model is public.
- **Declared dataset dependency `art_j3Rm_lr2nzR6`.** Its `full_data_out.json` is read in place, only to rebuild the
  novelty audit's known-solution index (`src/audit.py index`). By default the code reads the sibling folder
  `../art_j3Rm_lr2nzR6/` of the repository. Override it with `ART_J3RM_DIR`. The rebuilt index is already in
  `data/known_solutions.jsonl` (472 rows matching exp18, plus 42 T05 rows).
- **OpenRouter.** Set `OPENROUTER_API_KEY` and `OPENROUTER_BASE_URL`. They are used only for:
  - the labelling judges, on runtime/AST disagreement only;
  - the T1 K=7 judge;
  - the novelty audit.

  Every judge answer is cached: `data/judge_cache*.jsonl`, `data/k7_judge_cache.jsonl` and
  `data/llm_cache_audit.jsonl`. A rerun therefore reads the cache and spends little or nothing. This run spent
  USD 0.14 in total.
- **Optional.**
  - `AII_DATA_FIG_GEN_SCRIPTS`: the aii-data-fig-gen `scripts/` folder, for the figure house style. Without it the
    figures use plain matplotlib.
  - `OPENBLAS_NUM_THREADS=2`, `OMP_NUM_THREADS=2` and `MKL_NUM_THREADS=2`. `method.py` sets these by default. On a
    CPU-quota container, BLAS oversubscription otherwise made one PCA take 44 s instead of 0.5 s.
- **No user-uploaded files were used.** The run's `user_uploads` folder was empty.

## 4. Commands actually run, in order (with times, hardware and seeds)

**Hardware.**
- GPU: one NVIDIA L4 (24 GB card, 22.0 GiB visible to torch, compute capability 8.9).
- CPU and RAM: 5 CPUs (cgroup quota) and 57 GB RAM.

**Precision.** W16A16: bf16 weights and activations, attention `sdpa`, TF32 disabled.

**Fixed configuration** (in `src/cfg.py`, frozen in commit #1):
- **Decoding.** T 1.0, top-p 1, no top-k, thinking off. At most 1,024 new tokens on T03/T10 and 1,536 on T2/T1.
  Fence stop.
- **Batch shape.** B = 16 on T03/T10 and 12 on T2/T1, chosen by the memory probe (`results/batch_probe.json`).
- **Seeds.**
  - Token uniforms: `u_stream(task, template, k)` = `PCG64(stable_seed(task, template, k)).random(n)`, where
    `stable_seed` = sha256 of the parts joined by '|', mod 2^63.
  - Directions: `PCG64(stable_seed('ITER6_S2', task, template, k)).standard_normal(4096)`, normalised.
  - Thinking traces: `u_stream('T2', template, 'THINK')`.
  - MDS: classical-MDS initialisation, then SMACOF with `random_state` 0.
  - Bootstraps and placebos: seeds 0 and 1, fixed in code.

Times are UTC on 2026-10-21. GPU stages run in their own process from `src/`.

| # | Command (from this folder) | What it did | Time |
|---|---|---|---|
| 0 | `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml` | environment | 3 min |
| 1 | `.venv/bin/python method.py prep` (= `cd src && python gpu_main.py --stage prep`) | positions, bf16 r_Q (ban prompts as forward passes only), twin states and ban-free units, forced-prompt states (T03 360, T10 240, T1 480), banned sets, push directions, push progress, memory probe | 26 min (of which 17 min were BLAS oversubscription in push progress) |
| 2 | `.venv/bin/python method.py gputests` | U1-U7 GPU tests, the positive control U8 (100 ENG rows), and smoke batches (k >= 100) | 9 min |
| 3 | `.venv/bin/python method.py inputs` and `.venv/bin/python method.py seeds` | `inputs/SHA256SUMS` (572 files), bench check against `commitment.json` (0 mismatches), direction seed registry | 1 min |
| 4 | `cd src && ../.venv/bin/python label_worker.py follow &` | label worker following `data/samples_raw.jsonl` until sampling ends | alongside |
| 5 | `.venv/bin/python method.py commit1` | commit #1 at 21:00:17Z | – |
| 6 | `.venv/bin/python method.py sample --deadline-unix <now + 147 min>` | decisive sampling: 245 fixed-shape batches, 3,290 decisive rows, no time-based drops | 21:00:41-22:50:14 |
| 7 | `cd src && ../.venv/bin/python label_k7.py` | exp9 K=7 / extended labels for the 360 T1 rows | 2 min |
| 8 | `.venv/bin/python method.py commit2` | commit #2 (the analysis code) at 22:51:37Z | – |
| 9 | `.venv/bin/python method.py score` | F2: 1,955 teacher-forced sequences scored twice (11 min), then 5 thinking-on T2 traces (22 min) | 33 min |
| 10 | `.venv/bin/python method.py analyse` | every analysis -> `results/*.json` | 3 min |
| 11 | `.venv/bin/python method.py audit`, then the executor's manual pass written to `audit/manual_pass.jsonl`, then `.venv/bin/python method.py audit_summary` | novelty audit: 61 unique programs, 6 judge controls x 3 judges, 2 judges + tie-break | 6 min |
| 12 | `cd src && ../.venv/bin/python -c "import analysis as A; r=A.decisive(A.read_jsonl(A.MERGED)); A.s_d(r); A.s_d_audit_relabelled(r); A.f2()"` | S-d after the post-commit-2 fixes, the audit-relabelled S-d sensitivity, and F2 once the scoring files existed | 3 min |
| 13 | `.venv/bin/python method.py figures` | `figures/*.pdf` + `.png` | 1 min |
| 14 | `.venv/bin/python method.py outputs` (runs `audit/rederive.py` after `src/outputs.py`), then `python3 audit/rederive_extra.py` and `.venv/bin/python method.py outputs` again | `method_out.json`, both independent re-derivations | 5 min |
| 15 | aii-json `aii_json_format_mini_preview.py --input method_out.json`, and its schema validator (format `exp_gen_sol_out`) | `full_` / `mini_` / `preview_method_out.json`, all four PASS | 1 min |

**What differed from a clean single pass.**
- **Step 2 ran twice.** The first run crashed on a smoke-row construction bug after U1-U8 had finished. The bug was
  fixed and the stage was rerun; the rerun only executed the smoke batches.
- **Step 9 started automatically** when step 6's process exited.
- **The labeller re-check ran as** `cd src && ../.venv/bin/python -c "from recheck import bench_recheck, suite_recheck; ..."`.
  This is `results/labeller_recheck.json`. `src/recheck.py`'s `__main__` would also rewrite `inputs/SHA256SUMS`, so
  it was not run directly.
- **CPU unit tests:** `.venv/bin/python method.py cputests`. All 9 pass (`results/unit_tests_cpu.json`).
- **Commits after #2.**
  - Commit #3 (23:27Z): bug fixes in `src/analysis.py` found on the first full outputs. These are the T1 extended
    survivor count, forks at the first code token, and an extra push-progress normalisation. They are logged as
    D_POSTC2_FIXES.
  - Commit #4: a figure tweak.
  - Commit #5: a scrub of absolute paths from `src/cfg.py` and `src/figures.py`.
  - Commit #6: the outputs carry the second re-derivation.
  - `cd src && ../.venv/bin/python commit.py verify` reports 6 commits, 0 chain breaks and 0 changed files.

**Determinism.**
- **Same hardware.** The CRN design (fixed batch shape, one uniform per row and step, finished rows fed
  `<|im_end|>`) makes every row reproducible on the same GPU type, driver and kernels. U1 shows byte identity
  across two batch compositions.
- **Other hardware.** On another GPU, bf16 kernels can differ, so expect per-slot label agreement rather than byte
  identity. For example, this run reproduced exp25's bf16 positive control with per-slot label agreement 1.00 and
  96% identical code (U8), and earlier bf16 twins with label agreement 0.98-1.00 (U9).
- **Judges.** Judge answers are nondeterministic but cached.

## 5. Outputs and the numbers a reader should get

All numbers are W16A16 on Qwen3-8B. The README's Results section prints each of them with its source file. A paper
draft does not exist yet; the README sections named below are where each number appears.

| Number | File | README place |
|---|---|---|
| S-a: PASS, robust to selection. Selected cell S0 alpha 4: T03 share 0.42 (pass 0.88), T10 0.28 (pass 0.96). Paired flips vs S1/S2/S5: T03 21:0 / 21:1 / 21:1, T10 14:0 each. Holm p <= 3.7e-4; selection-aware Holm <= 0.0022. N 30 sensitivity: PASS, not robust | `results/s_a.json` | Bottom line; S-a table |
| S-b: Mantel-Haenszel OR 22.45 [10.14, 49.72] (n 2,100); S0 only 4.78, S4 only 3.18 | `results/s_b.json` | Bottom line; S-b |
| S-c: T03 alpha 2, 6:0, p 0.016 (PASS on T03 only) | `results/s_c.json` | S-c table |
| F1: 219/221 = 0.99; label-preserving control 0.82 | `results/f1.json` | F1 |
| F2: m = 12.77 (T2), 8.56 (T03), 7.33 (T1); m_fork 5.25 / 5.49 / 5.25; m_think (T2, thinking on) 43.5 | `results/f2.json`, `results/q_lik_existing.json` | F2 table |
| S-d. T03 top-5: 49/49 quickselect at alpha 1 (avoidance 0). T03 top-3: 19:0 and 43:0 against the random control. T1: 13:1 at alpha 4, landing on unit-weight Dijkstra | `results/s_d.json`, `results/s_d_audit_relabelled.json` | S-d tables |
| Dose axis: S4 vs S0 at matched realised residual fraction | `results/dose_axis.json` | Bottom line; fig 7 |
| Novelty: 0 novel among 3,102 correct programs (61 unique 'other', all a counting-sort variant) | `results/novelty_audit.json` | Novelty audit |
| Engine: U8 T03 composition identical to exp25 (29/12/9) | `results/engine_checks.json` | Checks |
| Re-derivation: 0 mismatches. Placebos fail: S-a 0/200 shuffles, MH 2%, pair swap 2%, S-d pair swap <= 3.6%, m_fork default-vs-default about 0 | `results/rederive.json`, `results/rederive_extra.json` | Checks |

**Not independently re-derived** (computed once, in `src/analysis.py`):
- the dose-axis logistic interpolations;
- the landing binomial p-values;
- the logistic transmission coefficients;
- the geometry: MDS stress, geodesics and edge tests;
- the thinking-on margin m_think.

`method_out.json` follows the `exp_gen_sol_out` schema. It has four datasets:
- `site_grid`: 2,354 examples, one per CRN slot x site x alpha, with `predict_site_arm` and `predict_twin` =
  'label|pass';
- `top5_manifold`: 600;
- `f2_margins`: 15;
- `engine_checks`: 100.

Every analysis summary is in its `metadata`.
