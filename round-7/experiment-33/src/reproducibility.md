# Reproducing iteration 7 ("Finding the model's hidden algorithm switch")

This file describes what was actually run, in the order it ran, including the restarts and the amendments.
All paths are relative to this folder.

## 1. Get the artifact

This folder is one folder of the run's public GitHub repository:

```bash
git clone <repository-url>
cd <repository>/<this-folder>        # the folder that holds this file, method.py and src/
```

What the folder already contains:

- *Inputs.* `inputs/` and `inputs_extra/` are read-only copies of every prior-artifact file the pipeline reads:
  exp30's code, prompts, labels and samples; the exp11 bench (T03, T10) and the exp8 suite (T2) with their hidden
  tests and frozen labellers; exp13/exp7/exp6/exp17 prompt inputs; extracts of exp24, exp29 and exp9.
- *Dependency extract.* `data/dep_extract.json` is the extract of the declared dataset dependency
  `art_j3Rm_lr2nzR6`: the noun bank and known-solution corpus, built from all ten datasets.
- *Reuse.* A rerun needs nothing from the original server.
- *Optional raw dependency.* To rebuild `data/dep_extract.json` from the raw dependency, place `art_j3Rm_lr2nzR6` as
  the sibling folder `../art_j3Rm_lr2nzR6` (the repository publishes it there), or point the environment variable
  `ART_J3RM_DIR` at a copy. The single constant that reads it is `DEP_DIR` in `src/cfg6.py`.
- *No user uploads.* The run's user-upload folder was empty; nothing private is needed.

## 2. System, Python and libraries

- *System.* Ubuntu (Debian 12 container was used), an NVIDIA driver with CUDA 12.8 support, `uv` 0.4+, `git`.
- *Python.* Python 3.12.14.
- *Libraries.* Every library is pinned in `pyproject.toml` to the exact version installed: 85 packages, including
  torch 2.8.0 (CUDA 12.8 wheels), transformers 4.57.6, numpy 2.2.6, scipy 1.18.1, scikit-learn 1.9.1,
  matplotlib 3.11.2, openai 3.35.1 and loguru 0.7.3. The uv-created venv has no `pip` binary, so
  `uv pip freeze --python .venv/bin/python` was used to check the pins.

```bash
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r pyproject.toml
```

`restore.sh` does both steps and the model download.

## 3. Model, environment variables, API keys

- *Model.* `Qwen/Qwen3-8B` at revision `b968826d9c46dd6066d109eabc6255188de91218`, in bf16 (16.4 GB). Download it
  with `.venv/bin/python src/download_model7.py`, which uses the standard Hugging Face cache.
  - `src/cfg.py:model_path()` loads the snapshot from `HF_HUB_CACHE` when that revision is present. Otherwise it
    loads by repository id.
  - `HF_HOME` / `HF_HUB_CACHE` were left at the run's shared cache; they were not redirected into this folder.
- *API keys, by name.*
  - `OPENROUTER_BASE_URL` and `OPENROUTER_API_KEY` are used by the label worker's blind judges (called only on
    labeller disagreement), the novelty audit (`src/novelty6.py`) and the hybrid judge (`src/hybrid7.py`).
  - Total spend was USD 0.13 (`results/costs.json`); this artifact's cap was USD 0.5.
- *Optional path variables.* `ART_J3RM_DIR` (see above). `AII_PRIOR_LOOP` / `AII_LOOP_DIR` are read only by
  exp30's input-copy helpers, which this pipeline does not call.

## 4. Hardware and what was run, in order

- *GPU.* One NVIDIA GeForce RTX 4090 (24 GB). bf16 Qwen3-8B fully on the GPU, with the input embedding on the
  GPU as well; about 8.3 GB stays free after loading.
- *Host.* 14 CPUs (cgroup quota), 56 GB RAM.
- *Load and throughput.* Model load takes about 37 s. Generation ran at about 0.42 s per program (fixed batch 16
  per task), for 4,500 programs in total.
- *Total time.* GPU wall time was about 1.6 h; the whole session took about 3 h.

Seeds:

- *DAS init.* 7003 (T2), 7011 (T10), 7004 (T03); the T2 second seed is 8003.
- *Fixed controls and statistics.* Random subspaces 9001-9003; the permutation 7101; the random-init network 0;
  MDS 0; the bootstrap 20261022.
- *Generation streams.* Common random numbers use exp30's streams, `u_stream(task, template, k, n=1536)` keyed by
  `cfg6.SLOT_MAP[slot]`. T = 1, top-p 1, no top-k, thinking off. Caps are 512 tokens (T2) and 384 (T10, T03);
  the long-form novelty instruction cell uses 1,536.

The label worker ran in the background for the whole GPU phase. It follows `data/samples_raw.jsonl` into
`data/labels.jsonl` and stops after `results/gpu_all_done.flag` appears:

```bash
.venv/bin/python src/label7.py &
```

Commands, in the order they were run:

```bash
# 0. inputs/ and inputs_extra/ were copied from exp30 (already present in this folder); reused code was byte-copied
#    from inputs/exp30/src/ into src/ (cfg.py, cfg6.py, engine*.py, gpu6.py, hooks.py, label*.py, prompts*_v4/6.py,
#    regate_rules.py, stats6.py, novelty6.py, commit6.py, format_outputs6.py, ...)
.venv/bin/python src/download_model7.py
.venv/bin/python src/prompts7.py                              # 383 prompts + CPU tests (prompts/prompt_report7.json)
.venv/bin/python src/run_gpu7.py utest --tasks T2             # U1-U8 (results/unit_tests_gpu.json), ~1 min
.venv/bin/python src/prereg7.py                               # commit0 (predictions/commit0.json, commitments.log)
.venv/bin/python src/run_gpu7.py s0 --tasks T2,T10,T03        # Stage 0: 780 programs, ~6 min
.venv/bin/python method.py targets                            # kept Y, landing sets, target programs (run twice: the
                                                              # second run is amendment commit1_<task>_v2)
.venv/bin/python src/run_gpu7.py profile,fit,tfeval --tasks T2,T10
#    -> the profile + confirmation finished for both tasks and the committed (contrastive) fits finished for T2;
#       the process was then stopped (kill <pid>) because the committed objective diverged (README, amendment 1)
.venv/bin/python src/run_gpu7.py fitlight --tasks T10         # committed objective, MAIN only
.venv/bin/python src/run_gpu7.py fitly,tfeval,gen,genpilot --tasks T2,T10
#    -> amendment1_ly_<task> commits (LME_Y maps), held-out TF evaluation, held-out generation with MAIN_LY,
#       the 10-slot pilot of the committed map; amendment2_analysis_code was committed (inline python, see
#       predictions/amendment2_analysis_code.json) before generation was scored
bash scripts/run_gpu_after.sh
#    -> r,m --tasks T2; profile,fitlight,fitly3,genred --tasks T03; randinit --tasks T2
#       (the first randinit attempt ran out of GPU memory with the trained model resident; src/run_gpu7.py was
#       patched to skip loading the trained model for this stage, and `run_gpu7.py randinit --tasks T2` was rerun)
bash scripts/run_gpu_ext.sh                                   # mgen,seed2 --tasks T2 (extensions)
bash scripts/run_gpu_ext2.sh                                  # randinitly --tasks T2 (matched Sutter control)
.venv/bin/python src/novelty6.py                              # novelty audit of correct 'other' programs
.venv/bin/python src/hybrid7.py                               # R hybrid judge (1 candidate)
.venv/bin/python src/report7.py --tasks T2,T10,T03            # every analysis + figures
.venv/bin/python src/summary7.py                              # results/summary.md
.venv/bin/python src/bookkeeping7.py                          # deviations, costs, timing, SHA256SUMS, chain check
.venv/bin/python src/outputs7.py                              # method_out.json (+ full_/mini_/preview_)
python3 audit/rederive.py                                     # 180 checks + placebos
.venv/bin/python audit/rederive_tf.py                         # 52 checks + placebo
```

`method.py` wraps the same stages (`.venv/bin/python method.py [stage ...]`). Every GPU stage resumes: finished
sample ids, fits and site files are skipped. A rerun regenerates the committed rows bit-for-bit only on the same
GPU class and batch shapes. On another GPU the bf16 kernels differ, which the engine check measures (exp30's
labels vs this run's: 20/20, 19/20, 20/20).

## 5. What a reader should get

| output | number | where |
|---|---|---|
| `results/site_<task>.json` | site: band 12-23 on T2 and T10 (full-state at L* moves 0/30, band 11/30 and 17/30); block 16 on T03 | README "Where the choice is carried", `figures/F1_layer_profile` |
| `results/das_fits_<task>.json` | the committed contrastive objective diverges (best validation 1,873 nats T2, 3,868 nats T10) | README, `figures/F8_fit_curves` |
| `results/p1.json` | T2 ban DAS rank-2 12/30 vs full 11/30, base 1/30, random <= 1/30, McNemar 11:0 (Holm 9.8e-4); T10 ban DAS rank-16 29/30 vs full 17/30, random 0/30, 61:0 (2.6e-18); T03 ban rank-1 26/30 vs full 27/30, random 6/30, 20:0 (1.9e-6) | README P1 bullets, `figures/F2_recovery_vs_rank` |
| `results/p1.json` (clauses) | permuted-label transfer 0.47 (T2), 0.70 (T10), 0.60 (T03) -> P1 FAIL on every task; overall NOT SUPPORTED | README table |
| `results/randinit_ly_T2.json` | random network held-out TF gain 13.3 vs trained 14.5 nats (ratio 0.92) | README |
| `results/c_routing.json` | T2 forced Floyd-Warshall routed 28/28 at rank 1 (full-state 8/20); T03 counting sort 30/30 (full-state 0/30); T10 forced BFS -> DFS | `figures/F3_routing_confusion` |
| `results/dormant.json` | T2 reverse recovery 0 (DORMANT FLAG); T03 projected retention 0.20-0.26 (DORMANT FLAG) | `figures/F7_dormant_checks` |
| `results/m_manifold.json`, `results/m_behaviour.json` | bans at the 100th percentile of the paraphrase null; seeds and instructions inside; seeds keep Dijkstra 30/30; the long-form novelty instruction gives 6/30 Bellman-Ford | `figures/F4_causal_manifold`, `F5_topk_prohibition_placement` |
| `results/r_discreteness.json` | logistic width 3.25 (not discrete); plateau of 6-9/20 Bellman-Ford | `figures/F6_discreteness` |
| `results/novelty_audit.json` | 38 correct 'other' programs, 0 novel | README |
| `results/rederive.json`, `results/rederive_tf.json` | 180 + 52 checks, 0 mismatches; every placebo fails | README audit bullet |
| `method_out.json` | 1,390 examples (one per task x source group x CRN slot), `predict_<arm>` = `label|pass` | exp_gen_sol_out schema |

`results/summary.md` holds every table, and `commitments.log` verifies with 18 commits and 0 breaks
(`results/commit_chain.json`).
