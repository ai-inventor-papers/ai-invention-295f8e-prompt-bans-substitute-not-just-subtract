# Reproducing "Fixing the record and auditing novel code" (iteration 3, Step 0)

This artifact is a CPU-only evaluation. It trains nothing, generates no code with the studied models and runs no GPU
scoring. Its inputs are the result files of 11 earlier artifacts. The only paid step is a set of blind LLM-judge
calls, and their responses ship in `audit/judge_cache.jsonl`, so a reader can reproduce every number without an API key.

Every path below is relative to this artifact's folder.

## 1. Get the artifact and its inputs

```bash
git clone <URL of the public repository that holds this run>
cd <repository>/<this artifact's folder>        # the folder that contains eval.py and this file
```

### Where the code looks for the inputs

The repository publishes each artifact as a sibling folder. The code reads every dependency through one function,
`common/paths.py: dep_root()`, which tries three places in order:

1. `$AII_DEPS_ROOT/<artifact_id>`, if the environment variable `AII_DEPS_ROOT` is set;
2. `../<artifact_id>`, a sibling folder named by the artifact id;
3. the AI Inventor run-volume layout, relative to this folder, which is what the published run actually used.

If your clone names the sibling folders differently, create a directory of symlinks named by artifact id and point
`AII_DEPS_ROOT` at it.

### The dependencies

| Artifact id | Role | Files read (relative to that artifact) |
|---|---|---|
| `art__skdlFp_o3e9` (exp1) | iteration-1 ban screen | `data/samples.jsonl`; `tasks/t1_grid`, `tasks/t2_wsp` (spec.txt, references/) |
| `art_D6Z0Snf09sFL` (exp2) | iteration-1 geometry screen | `data/samples_phase{A,C,D}.jsonl` |
| `art_U5UKkFrOgSsE` (exp4) | iteration-1 steering screen | `data/samples.jsonl` |
| `art_HF8nK8B_Lqyy` (exp5) | iteration-1 base vs instruct | `runs/samples.jsonl` |
| `art_UoCVh2Qe5RZ0` (exp6) | iteration-1 decoding screen | `results/samples.jsonl` |
| `art_6zBfl3kDjeiP` (exp7) | Qwen FRLP / C1 | `results/{c1,protocol,timings,sensitivity,yields}.json`, `results/frlp_cells.jsonl`, `data/forced_selected.jsonl`, `scores/units_done.jsonl`, `scores/cells/*/*.parquet`, `logs/throughput.json` |
| `art_8_ULPE8jJQc_` (exp8) | route test | `data/samples.jsonl`, `results/{analysis,natural_frlp}.json`, `inputs/iter1/exp3/generations/pools.jsonl` (the only route to exp3 programs) |
| `art_IVZc3TWCeE9f` (exp9) | multi-ban + manifold | `data/samples.jsonl`, `results/{manifold,persistence}.json`, `figures/fig_manifold_*`, `figures/fig_kstab_*`, `tasks/*/references/`, **`states/t{1,2}/base/part_*.npz`** |
| `art_-QPYRaFERCBX` (exp10) | Llama replication | `data/labelled.jsonl`, `results/{c1,events,bootstrap_diagnostics}.json`, `frlp/cells.jsonl`, `frlp/scores_t{1,2}.parquet` |
| `art_0ndRfWKBWclR` (exp11) | coding bench | `data/samples_{pilot,llama_pilot,forced}.jsonl`, `bench/*/spec.json`, `bench/*/references/`, `full_method_out.json` |
| `art_3iv5G76C3yoX` (exp12) | readout | `results/samples.jsonl`, `results/labelled_*.jsonl`, `results/e2_meta.json` |

### What a repository clone cannot rerun

- **exp9 activation states.** exp9 kept its `states/` folder (0.95 GB) on the AI Inventor run volume and did not
  publish it. With only the repository, the manifold section (0b) and checks G1–G3 of `audit/rederive.py` cannot be
  recomputed. Their results ship in `results/manifold.json`, `tables/manifold_grid.csv` and
  `audit/rederive_report.json`.
- **Large files.** Any dependency file of 100 MB or more is skipped by the publish step. None of the files above
  reaches that size.
- **Uploads.** No user-uploaded input was used; the run's upload folder was empty.

### No downloads

No model, checkpoint or dataset is downloaded.

## 2. System, Python and packages

The published run used:

- **OS:** Debian GNU/Linux 12 (bookworm) in a container. Any recent Ubuntu (22.04 or 24.04) works the same way.
- **Hardware:** CPU only. An AMD Ryzen 9 7950X, with a container quota of 14 CPUs and 56 GB of RAM. No GPU was used,
  although an RTX 4090 was present.
- **Software:** Python 3.12 and `uv`.

```bash
sudo apt-get update && sudo apt-get install -y curl git build-essential
curl -LsSf https://astral.sh/uv/install.sh | sh          # installs uv
uv venv .venv --python=3.12                              # uv fetches CPython 3.12 if it is missing
uv pip install --python .venv/bin/python -r requirements.lock.txt
# or: ./install.sh   (the same two uv commands)
```

### Pinned versions

The exact versions are pinned in three places, which agree with each other:

- `pyproject.toml`: all 51 installed packages pinned;
- `requirements.lock.txt`;
- `uv.lock`.

The main packages are:

- **numerics:** numpy 2.5.4, scipy 1.18.1, pandas 3.0.6, pyarrow 26.0.0, scikit-learn 1.9.1, statsmodels 0.15.0;
- **topology and plotting:** ripser 0.6.15, matplotlib 3.11.2;
- **utilities:** loguru 0.7.3, openai 3.35.1, jsonschema 4.26.0, psutil 7.2.2, pyyaml 6.0.3, tenacity 9.2.1.

`uv run ...` uses `pyproject.toml` and `uv.lock` directly.

## 3. Environment variables (names only)

| Variable | Needed for | Notes |
|---|---|---|
| `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL` | `--section judges` only | With the shipped `audit/judge_cache.jsonl` the judge section makes **0** calls. A fresh run (`--fresh-judges`) costs about USD 0.42. |
| `AII_DEPS_ROOT` | optional | Directory holding one folder per dependency, named by artifact id (see section 1). |
| `AII_RUNS_ROOT` | optional | Root of the AI Inventor run volume, used only by the fallback lookup. |
| `AII_DATA_FIG_GEN_SCRIPTS` | optional | `scripts/` folder of the aii-data-fig-gen skill: house style for `figures/make_figures.py` and the renderer for `figures/knob_ranking_spec.json`. Without it the figure is drawn in plain matplotlib. |

## 4. The commands that produced the published outputs, in order

The global seed is `20261020` (`common/paths.py: SEED`). Every random step derives from it:

- the bootstraps;
- the AIM null simulation;
- the label permutations;
- the Gaussian nulls and planted-loop power runs, which use a fixed set of 8 random-number streams, so the worker count
  does not change the results;
- the knob-table rarefaction.

The judge calls ran at temperature 0.

| Step | Command | What it does | Runtime (CPU) |
|---|---|---|---|
| 1 | `uv run eval.py --section judges` | Builds and hash-commits the selection (`audit/selection.jsonl`, `audit/selection_commit.txt`). Then calls the judges: openai/gpt-4.1-mini (A), google/gemini-2.5-flash with reasoning `max_tokens` 0 (B), and deepseek/deepseek-chat as tie-break (C), via OpenRouter. | 4 min and USD 0.415 the first time (599 calls); 13 s and 0 calls from the cache |
| 2 | `uv run eval.py --section no_judges` | Runs, in order: inventory, c1 (B = 2,000; 10,000 AIM-null draws), manifold (500 permutations, 200 Gaussian-null draws, 200 power runs, layers {20, 24, 28}), novelty, llama, knob, positioning, corrections, assemble. The published run passed `--n-boot 2000 --n-sim 10000 --n-perm 500 --n-null 200 --n-power 200`, which are the defaults. | about 2–3 min (manifold about 70 s, c1 about 25 s) |
| 3 | `uv run audit/rederive.py` | Independent re-derivation (no project imports) and the placebos → `audit/rederive_report.json`. | about 1 min |
| 4 | `uv run eval.py --section assemble` | Re-assembles `eval_out.json` and its full, mini and preview variants, now including the re-derivation report. | 5 s |
| 5 | `python <aii-json skill>/scripts/aii_json_format_mini_preview.py --input eval_out.json` | Regenerates `full_/mini_/preview_eval_out.json` with the pipeline's own formatter. Step 4 already writes equivalent files when the skill is not available. | 1 s |
| 6 | `AII_DATA_FIG_GEN_SCRIPTS=<skill>/scripts uv run figures/make_figures.py`; `uv run figures/make_knob_spec.py`; then `python <skill>/scripts/chart_gen.py --spec figures/knob_ranking_spec.json --out figures/knob_ranking` | Figures. | seconds |

### Inputs prepared by hand, not regenerated

- **The manual pass.** `audit/manual_pass.jsonl` was written by the executor after reading the programs (printed by
  `audit/dump_for_manual_pass.py` and `audit/dump_setB.py`), through `audit/write_manual_pass_A.py` and
  `audit/write_manual_pass_B.py`. Re-running those two scripts rewrites the same file.
- **The positioning check.** The pages were fetched once, on 2026-10-20, with the aii-web-tools fetch script into
  `results/web/`. The positioning section only re-verifies the quotes against those saved pages.

## 5. What you should get

| File | Key numbers |
|---|---|
| `eval_out.json` / `full_eval_out.json` | 72 entries in `metrics_agg`; 7 datasets (c1_events 31, novelty_audit 228, knob_table 306, llama_correct_only 27, manifold_grid 48, positioning 12, corrections 12). Valid against the exp_eval_sol_out schema. |
| `results/c1_diagnostics.json`, `tables/c1_argmax_vs_landing.csv` | **Argmax hits on Qwen's realised landing:** full-gain 0/17, residual 0/17, implied-mass 14/17 (8/8 modal bans). **Estimable-mass restriction:** 0 of 11 rows survive. **Bootstrap/replicate variance:** median 2.68 (range 1.22–4.26); one-stage 1.59. **AIM null:** mean −0.265, with observed −0.595 at quantile 0.004; Llama −0.283 at quantile 0.66. **M5:** plug-in lower bound 49.8, lognormal about 4.7e31. **PSIS k-hat:** 22% of pooled fits above 0.7. **Events needed** for a 0.10 deviation: 129 (Qwen), 43 (Llama). |
| `results/manifold.json`, `tables/manifold_grid.csv` | **Figures found:** 13 manifold, 2 k-stability. **Re-derivation:** nearest maps match exp9 in 24/24 settings per task. **BFS–BiBFS at (24, g16, k10):** separability 0.960, N1 p 0.194, N2 p 0.481, so it does not survive. **H1 planted-loop power:** g16 0.035 (T1) / 0.045 (T2); pre 1.00 / 0.975. |
| `results/novelty_audit.json`, `tables/novelty_audit.csv`, `tables/multiban_avoidance_corrected.csv` | **Novelty:** 78 unique correct out-of-catalogue programs, 0 novel; rule-of-three bound 0.038. **Judge agreement:** kappa 0.378 [0.309, 0.446]. **Controls:** 7/10 positive (strict) with 10/10 named correctly, 5/5 negative. **TOP ban:** avoidance 0.13, all of it 'other'. **Judge spend:** USD 0.415. |
| `results/llama_correct_only.json`, `tables/llama_correct_only.csv` | **Llama T1 baseline:** BFS 77, DFS 20 attempted; correct BFS 20/20 (Hill_cc 1.00, Hill_all 1.87). **Bench:** every quoted composition reproduced; Llama more diverse on 9/13 tasks at depth 10. |
| `results/knob_table.json`, `tables/knob_table.csv` | **Rows:** 306 rebuilt (276 without exp5). **Best KNOB under 20 points:** exp6 semantic seed on T2, 1.940 [90% 1.770, 2.094] at 7 points; none reaches 2. |
| `results/positioning.json`, `tables/positioning.csv` | 12/12 quotes verified. |
| `corrections.json` | 12 items (R01–R12); 16 of 19 reproduction targets match, each mismatch with its cause. |
| `audit/rederive_report.json` | 72/72 checks pass; 7/7 placebos fail as required. |

### Where these feed the paper

The paper is not yet written. These outputs are the record repair for the next report:

| Correction item | Report location |
|---|---|
| R01, R05, R10 | C1 and the pre-registered outcomes: Sections 2.4, 2.3.7, 2.11 |
| R03 | Manifold: Section 2.6 and the circle wording |
| R04 | Llama: Section 2.7, Tables 70 and 73 |
| R08 | Novelty and multi-ban avoidance: Tables 67–68 and claim 3 |
| R09 | Knob table: Section 2.3.6 |
| R06 | Positioning: Table 52 |

The two figures, `figures/argmax_vs_landing.pdf` and `figures/knob_ranking.pdf`, are intended for the C1 and knob
sections.
