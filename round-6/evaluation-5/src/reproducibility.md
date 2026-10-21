# Reproducing the iteration-6 Step-0 record audit

This artifact is CPU-only. It runs no model, and its only paid step is a small third-family LLM judge batch. It
recomputes the record from files of earlier artifacts. Everything below is what was actually run on 2026-10-21. All
paths are relative to this artifact's folder.

## 1. Get the artifact
```bash
git clone <URL of this run's published repository>
cd <repository>/<this artifact's folder>          # the folder holding eval.py, README.md and this file
```

## 2. System, Python and libraries
* **OS and tools.** Run on Ubuntu or Debian Linux with `uv`, which was used for every package operation; pip was never
  used. No system packages beyond a C runtime are needed, because all wheels are binary.
* **Python.** Python 3.12, exactly 3.12.14 in the original run.
* **Libraries.** Every installed package is pinned in `pyproject.toml` and `requirements.lock.txt`:
  * numpy 2.2.6, scipy 1.15.3, pandas 2.2.3, matplotlib 3.10.3, pyyaml 6.0.2, loguru 0.7.3, requests 2.32.3;
  * certifi 2026.10.19, charset-normalizer 3.5.2, contourpy 1.4.0, cycler 0.12.1, fonttools 4.67.0, idna 3.20,
    kiwisolver 1.5.1, packaging 26.3, pillow 13.0.0, pyparsing 3.3.3, python-dateutil 2.9.0.post0, pytz 2026.5,
    six 1.17.0, tzdata 2026.5, urllib3 2.8.0.

```bash
bash install.sh      # = uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r requirements.lock.txt
```
* `audit/rederive.py` uses the Python standard library only, and runs with any `python3` (3.12 recommended).
* The re-timing children (`src/time_child.py`) run under the same interpreter, with `-I`.

## 3. Inputs, downloads and environment variables
### Declared dependency artifacts
These are read in place and read-only. Each one is a sibling folder of this one, named by its artifact id:
`<AII_DEPS_ROOT>/<artifact_id>`, where `AII_DEPS_ROOT` defaults to the parent folder of this artifact.

| artifact id | what is read |
|-|-|
| `art_mWn-MQEnNelg` (iteration-4 plan noise, 8-bit) | `data/realised.jsonl`, `data/samples.jsonl`, `results/alpha_sweep.json`, `data/known_solutions_dep.jsonl` |
| `art_SHaWv77P1XCI` (iteration-4 plan subspace, 8-bit) | `results/escape.json`, `results/arms.json`, `directions/rand_9101..9140.npy`, `data/labels.jsonl`, `data/realised_disp.jsonl` |
| `art_CcZLW-9NX00l` (iteration-5 transplant) | `results/base_repertoire.json`, `results/screen_check.json`, `results/novelty_audit.json` |
| `art_8WbrpoEFslk9` (panel A) | `pooled_inputs.json`, `results/a2_assoc_corrected.json`, `results/extra_arm_a.json`, `results/margins/*.json`, `data/samples.jsonl`, `newbench/`, `inputs/exp11/bench/`, `inputs/exp8/suite/tasks/` |
| `art_9a8LrIv2lHbV` (panel B) | `pooled_inputs.json`, `results/a2_panel.json`, `results/margins.json`, `results/repertoire_check.json`, `results/unit_outcomes.json`, `data/samples.jsonl`, `units/` |
| `art_jR6Pyy3W9xum` (knob experiment, bf16) | `data/samples_raw.jsonl`, `data/realised.jsonl`, `results/unit_ratio.json`, `results/cells.json`, `results/prices.json`, `results/bootstrap.json`, `results/literal_cell.json`, `results/pn_vs_dmd.json` |
| `art_hG0QPiaIPNhP` (Gemma) | `results/e_a2.json`, `results/predictors.json` |
| `art_j3Rm_lr2nzR6` (source data, run 4VFKidE1bxPG) | `full_data_out.json` (nearest-known pool for the judge) |

* If a dependency folder has a different name or location, set `AII_DEP_<artifact_id>`. Non-word characters of the id
  become `_`, for example `AII_DEP_art_mWn_MQEnNelg`.
* Alternatively, copy `paths.local.example.json` to `paths.local.json` (never published) and fill in its `deps` map.
* `art_j3Rm_lr2nzR6` belongs to an earlier run, so it may not be a sibling in your clone; point
  `AII_DEP_art_j3Rm_lr2nzR6` at your copy. No model or checkpoint is downloaded.

### Vendored inputs (`inputs/`, with sha256 in `inputs/SOURCES.json`)
These are copies of the undeclared inputs:
* the iteration-6 report that the corrections apply to (`inputs/report/current_report.md`);
* the record audit `art_sV0cQ3ef1ZRQ`'s `screen.json` and `tables/knob_table.csv`;
* iteration 3's `gen_art_experiment_18/results/known_solutions_summary.json`.

The iteration-6 strategy script `inputs/protocol/scripts/build_strategy.py` names server paths, so it is **not
published**. Its two protocol strings are published, with the server roots redacted, in
`inputs/protocol/protocol_strings_redacted.json`, and the code falls back to that file automatically.
* The frozen `definitions_sha256` of the M-candidates clause is reproducible from the redacted copy, because the
  clause names no path.
* The sha256 of the full original strings is recorded in `frozen/m_candidates.json`. It can only be re-checked with the
  original script.

### Environment variables (names only)
* `OPENROUTER_API_KEY` and `OPENROUTER_BASE_URL`: only for `eval.py --stage judge`, and only when
  `results/judge_cache.jsonl` lacks an answer.
* `AII_DEPS_ROOT` and `AII_DEP_<artifact_id>`: dependency locations (section 3).
* `AII_ITER6_GEN_ART` (optional): the iteration-6 gen_art folder, used only to log a names-only listing at freeze time.
  When it is absent the listing is empty.

## 4. Commands, in the order they were run
Hardware: a container with 6 vCPU (AMD EPYC 9254) and 57 GB RAM. An NVIDIA L4 (23 GB) was present but unused; nothing
uses a GPU.

```bash
.venv/bin/python src/s1_retime.py            # S1: re-time 145 catalogue references of 30 units (~1 min)
.venv/bin/python eval.py --stage freeze      # S0 + S2: input hashes, report index, frozen/*.json + commitments.log (~8 s)
.venv/bin/python eval.py --stage analyse     # S3: 0a-0e analyses -> results/s3_analyses.json, tables/*.csv (~32 s)
.venv/bin/python eval.py --stage judge       # S4: third-family judge (paid; ~1 min when not cached)
.venv/bin/python eval.py --stage outputs     # S5: corrections.json, figures/, eval_out.json (~5 s)
python3 -I audit/rederive.py                 # independent stdlib audit -> audit/rederive_result.json, audit/placebos.json (~1 s)
.venv/bin/python eval.py --stage outputs     # fold the audit result into eval_out.json
```

**Re-timing (S1).** Each reference first passes once over all hidden tests (correctness), then gets 5 timed repeats of
its stress cases. Each repeat runs in a fresh `python -I` subprocess with OMP/MKL/OPENBLAS threads set to 1, using 4
worker threads. A reference gets 9 repeats when the coefficient of variation exceeds 0.2.
* Stress cases are the tests flagged `stress`. For the two path tasks, they are the largest 20% by size, with ties
  broken by a seed-6006 shuffle.
* Absolute times are machine-dependent. The values the freeze used are in `retime/raw_times.json` and
  `frozen/m_candidates.json`. On another machine the log-ratio merits move slightly, so re-freezing yields different
  hashes.

**Freeze (S2).** It writes canonical JSON (sorted keys, no whitespace) and a hash chain, where
`chain = sha256(prev + file_sha256)` and the genesis is `sha256('iter6_step0')`.
* Every re-freeze moves the old `commitments.log` to `commitments_superseded_<utc>.log`.
* S3 refuses to run unless the chain verifies, so S3 must be re-run after a re-freeze.

**Seeds.**

| Seed | Use |
|-|-|
| 6001 | F1 Spearman permutations (100,000) |
| 6002 | F1 AUC permutations |
| 6003 | L3 split-halves |
| 6004 | unit-clustered Monte Carlo |
| 6005 | ρ(β, E) permutations (200,000) |
| 6006 | 10,000-replicate unit bootstrap, and the judge's item order |
| 6007, 6008 | power simulations |
| 6009 | rival paired bootstrap |
| 6010 | rival permutations |
| 6011 | Hill-1 rarefaction |
| 6012 | audit placebos |
| 7013 | audit Monte Carlo power check |

**Judge (S4).** The primary judge is `anthropic/claude-haiku-4.5`; the fallbacks are `mistralai/mistral-medium-3.1`
and `meta-llama/llama-4-maverick`. Temperature is 0 and the hard stop is USD 0.45.
* **Paid runs.** Two pass-1 runs of 66 calls each (the first, before the response cache existed, was repeated once to
  keep per-judge labels), then one pass-2 run of 66 calls. That is USD 0.152 for 198 calls (`results/costs.json`).
* **Re-runs.** All later runs are served from `results/judge_cache.jsonl`, keyed by the sha256 of model and prompt, so
  they are free and give identical labels. Without the cache, LLM answers can differ even at temperature 0.

**Total compute** is about 3 minutes, plus about 1 minute per paid judge run.

## 5. What you should get
* **`corrections.json`**: 45 `old_text -> new_text` corrections against `inputs/report/current_report.md`. Every
  `old_text` occurs exactly once and none overlap. They carry 150 value checks: 93 MATCH, 14 CORRECTED, 43 NEW,
  0 NOT_REPRODUCIBLE. They apply to report Sections 4.2.6, 4.6, 4.9, 4.10, 5.3-5.5, 5.8 and 5.10-5.12, the closing
  "What we have learned so far", and Tables 126c, 174, 203, 205-208, 211, 214, 217, 222 and 223.
* **`eval_out.json`** (+ `full_`, `mini_`, `preview_`): schema `exp_eval_sol_out`, 368 metrics, and datasets
  corrections (45), landing_events (21), m_candidates (30) and adjudication (22).
* **Engine (0a)**, in `tables/dose_reconciliation.csv`, `engine_contrast.csv` and `dose_matched.csv`:
  * The doses reproduce: mean of per-position ratios 0.990 / 0.889 / 0.995 / 0.874 / 1.394; ratio of mean norms 0.745 /
    0.837 / 0.778 / 0.751 / 0.975. The tasks are connected components, shortest path, two sum, grid and kth smallest.
  * The weighting identity holds to 1e-6.
  * Correct-only alpha-2 drops: 20.3×, 6.2×, 3.0× and 1.6× on components, shortest path, grid and kth smallest. The
    Fisher p is 7.2e-11 on components and 9.1e-4 on shortest path.
* **Landing (0b)**, in `tables/landing_tally.csv`, `twin_rival.csv` and `landing_events_iter5.csv`:
  * 17/21 overall. New units 6/7 (p 0.0027); Gemma 5/7 (p 0.025).
  * The unconfounded subset is 5/8 (p 0.053).
  * t_u has 0 discordant pairs.
* **Movability (0c)**, in `tables/movability_ci.csv`, `power_sim.csv` and `rivals_harmonised.csv`:
  * ρ 0.146 (Bonett-Wright −0.44 to 0.65).
  * Power at n 13 and ρ 0.6 is 0.60 (copula). About 30 units are needed for power 0.8 at ρ 0.5.
  * Re-timed runtime merit gives ρ 0.59.
* **Adjudication (S4)**, in `results/adjudication.json`: frozen outcome NOT_COMPLETED, because no judge passed 6 of 8
  controls (2/8, 3/8, 3/8). All judges called 0 of 14 novel in both passes.
* **Audit**, in `audit/rederive_result.json` and `audit/placebos.json`:
  * 163 independent checks with 0 mismatches.
  * 4 of 5 placebos fail as required; P2 is uninformative at n 13.
  * The chain verifies, and the frozen files predate the S3 outputs.
* **Figures**, under `figures/`: `fig_beta_escape_bf16` (engines in separate facets), `fig_dose_reconciliation` and
  `fig_power`.
