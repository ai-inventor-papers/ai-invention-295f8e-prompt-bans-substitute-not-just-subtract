# Reproducing "Fix the record, freeze rival predictors"

This artifact is a CPU-only re-analysis. It trains nothing, generates nothing with a model and downloads no
weights. It reads the result and row files of eight earlier artifacts, executes small reference programs and human
LeetCode solutions on CPU, makes cheap judge calls (cached), and fetches six public web pages. All paths below are
relative to this folder.

## 1. Get the artifact and its inputs

```bash
git clone <URL of this run's published repository>
cd <repository>/<this artifact's folder>
```

The eight input artifacts are read in place and never written. The code resolves each one through one rule, in
`src/io_util.py` (and, for the stdlib audit, an independent copy of the rule in `audit/rederive.py`):

- `<AII_DEPS_ROOT>/<artifact_id>`, where `AII_DEPS_ROOT` defaults to the parent folder of this artifact. With the
  default, every input is a **sibling folder named by its artifact id**.
- `AII_DEP_<artifact_id>` overrides one input. Non-alphanumeric characters of the id become `_`, e.g.
  `AII_DEP_art_mWn_MQEnNelg`. Use it when a sibling folder has a different name.

| Artifact id | What it is | What this artifact reads from it |
|---|---|---|
| `art_k6nzFCDLOjQP` | exp23, held-out family (gemma-3-4b-it), iteration 4 | `data/samples.jsonl`, `predictions/commit_preban.json`, `results/{c3a,bans,pilot,c1_prices,posthoc_t2_relabel,c3b,qwen_ratio}.json`, `inputs/exp8/suite/` (path-task references, tests, labeller) |
| `art_Cx9JOh8soBw7` | exp20, site experiment | `data/samples.jsonl`, `results/{c1_site,paired_flips,cells,transmission,rederive_headlines,units_summary,boundary}.json` |
| `art_SHaWv77P1XCI` | exp22, plan subspace and escape fractions | `data/{labels,samples_raw}.jsonl`, `results/{c3b,escape,screen,explore,rederive_extra,units,deviations,opening_lp}.json`, `inputs/exp13/results/c1_events.jsonl`, `inputs/exp16/results/c1_events.jsonl`, `inputs/exp7/data/freeform_labelled.jsonl` |
| `art_mWn-MQEnNelg` | exp19, plan-noise knob table | `data/samples.jsonl`, `results/{plain_vs_twin,prices,alpha_sweep}.json`, `results/{deviations,knob_rows}.jsonl` |
| `art_Yu6GN6pLxW8f` | exp21, same-seed temperature vs plan noise | `results/{gpu_hours,c1seed,thinking,vllm_engine,unit_sensitivity}.json`, `data/raw_thinking.jsonl` |
| `art_HF8nK8B_Lqyy` | iteration-1 base-model data (run 4VFKidE1bxPG) | `runs/labelled_base_chat__baseline.jsonl`, `runs/labelled_base_tf__baseline.jsonl` |
| `art_0ndRfWKBWclR` | iteration-2 coding bench | `bench/<task>/{spec.json,tests.jsonl,references/*.py,ast_rules.py}`, `bench/common/{runner.py,checkers.py}`, `data/{association,samples_forced}.jsonl` |
| `art_j3Rm_lr2nzR6` | iteration-1 source data (run 4VFKidE1bxPG) | `full_data_out.json` (datasets `mercury` and `leetcodedataset`; 96.2 MB) |

`art_HF8nK8B_Lqyy` and `art_j3Rm_lr2nzR6` were produced by an earlier run (`4VFKidE1bxPG`). If they are not siblings
of this folder in your clone, point `AII_DEP_art_HF8nK8B_Lqyy` and `AII_DEP_art_j3Rm_lr2nzR6` at your copies. If
`full_data_out.json` was not published because of its size, rebuild it with that artifact's own `restore.sh` /
`data.py`.

**No user-uploaded input is used.** The run's private upload folder was empty, and nothing in this folder depends on
it.

## 2. System, Python and libraries

What was actually used:

- **OS**: Debian GNU/Linux 12 container (Linux 6.8). Any Ubuntu with Python 3.12 works. No system packages beyond
  `python3.12` and `uv`.
- **Python**: CPython **3.12.14** for `.venv`. A **stdlib-only `python3.12`** runs the sandboxed reference and
  human programs (`-I -S`). The scripts take `$SANDBOX_PYTHON` if set, else `python3.12` on `PATH`, else the venv
  interpreter.
- **uv** 0.6.14.
- **Libraries**: exactly the 28 pins in `pyproject.toml` (also in `requirements.lock.txt`). Direct dependencies:
  numpy 2.2.6, scipy 1.15.3, loguru 0.7.3, requests 2.32.4, pyyaml 6.0.2, aiohttp 3.12.13, matplotlib 3.10.3.

```bash
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r requirements.lock.txt
```

## 3. Downloads, environment variables and keys (names only)

- No model, checkpoint or dataset download.
- `OPENROUTER_API_KEY` and `OPENROUTER_BASE_URL` are needed only by `rivals/r5_human.py`, for its blind-judge calls
  (`google/gemini-2.5-flash-lite`, temperature 0). The published `rivals/judge_cache.jsonl` holds all 251 judge
  responses. A re-run therefore hits the cache only and costs USD 0. The original spend was USD 0.021.
- `quotes/verify_quotes.py` needs outbound HTTPS to `arxiv.org` and `api2.openreview.net`.
- Optional: `AII_DEPS_ROOT` and `AII_DEP_<artifact_id>` (section 1); `SANDBOX_PYTHON`; `AII_CHART_GEN` (path to
  the aii-data-fig-gen `chart_gen.py`; without it the figure is drawn with plain matplotlib).

## 4. Commands, in the order they were run

Hardware: CPU only. The container had 6 vCPU (AMD EPYC 9254) and 57 GB RAM. An NVIDIA L4 (23 GB) was attached but
not used. Seeds: `numpy.random.default_rng(20261021)` (offsets per statistic) for the 10,000-replicate bootstraps
and 200,000-draw permutation tests; `random.Random(20261021)` for the R5 audit sample and the stdlib audit's
placebos.

```bash
# (a) R6 raw input: CPU timing of all 76 catalogue references (1 warm-up + 5 timed runs, per-case median),
#     3 worker processes, about 30 s -> rivals/r6_merit_raw.json
.venv/bin/python rivals/r6_merit.py

# (b) R5 raw input: the 388 Mercury human solutions of the bench-mapped problems (344 primary, 44 alternate; 384
#     executed, 322 correct after the case filter) run in sandboxes (2 s per case), frozen
#     bench AST rules on rewritten method bodies, judge on every AST 'unknown' plus a 10-program audit per task;
#     about 1.5 min -> rivals/r5_human_raw.json, tables/human_labels.csv, rivals/judge_cache.jsonl
.venv/bin/python rivals/r5_human.py

# (c) everything else, about 1.5 min:
#     record corrections (0a)-(0h) -> rivals/compute_rivals.py (freeze) -> rivals/score_rivals.py (verify the
#     freeze, log 'targets opened', score) -> quotes/verify_quotes.py -> audit/rederive.py (run with python -I)
#     -> src/assemble.py -> eval_out.json
.venv/bin/python eval.py

# (d) optional figure -> figures/fig_rivals.{pdf,png} (spec in figures/fig_rivals_spec.json)
.venv/bin/python figures/make_fig.py

# (e) full/mini/preview variants and schema check (aii-json skill scripts, run on the server):
#     aii_json_format_mini_preview.py --format exp_eval_sol_out --input eval_out.json
#     aii_json_validate_schema.py --format exp_eval_sol_out --file eval_out.json   -> PASSED
```

Useful flags: `eval.py --skip-rivals --skip-quotes` re-runs the corrections, audit and assembly without touching the
freeze, and `eval.py --assemble` rebuilds only `eval_out.json`.

**What actually happened to the freeze** (`commitments.log`, genesis = sha256('iter5_dir1')):

1. Freeze at 11:59:44 UTC; targets first opened at 11:59:50.
2. Re-freeze at 12:06:07. A re-freeze guard was added to `compute_rivals.py`, changing its sha256. The chain line
   records `post_target_refreeze: true` and `values_identical_to_previous_freeze: true`.
3. Re-freeze at 12:26:58, for the path-portability edits (script sha256s and the path field of the timing file).
   Again `values_identical_to_previous_freeze: true`.

Every run of `score_rivals.py` appends a "targets opened" line.

Two cautions for exact reproduction:

- **Timing**: re-running `rivals/r6_merit.py` re-times the references. CPU timings vary from run to run, so R6
  values change slightly, and `compute_rivals.py` then records a flagged re-freeze. Keep the published
  `rivals/r6_merit_raw.json` to reproduce the frozen R6 values exactly.
- **Human labels**: re-running `rivals/r5_human.py` reproduces the labels from the judge cache. Test pass/fail of a
  human program near the 2 s per-case limit could in principle differ on a slower machine.

## 5. What you should get

| File | Content and key numbers |
|---|---|
| `eval_out.json` (+ `full_`, `mini_`, `preview_`) | schema `exp_eval_sol_out`, 82 metrics, datasets: corrections 35, rivals 15, direction_distributions 624, table92c 6, dependency_coverage 8 |
| `corrections.json` | 35 `old_text -> new_text` entries marked `iteration-5 correction` |
| provenance (`eval_out.json` metadata) | 187 values with a record value: 186 MATCH, 1 CORRECTED (signed progress "22 of 35" is 22 of 24 cells in the staged file); 15 NEW; 4 CARRIED; 6 quotes RE-VERIFIED |
| `audit/rederive.json` | **195 checks, 0 failed**. Placebos fail as required: BA under permuted E 0.50; S0/S1 swap OR 1.01 against 101.7 real; landing shuffle 2.35 → 0.46 nats; permuted-E rejection 0.035 / 0.048 / 0.038 |
| (0a) `tables/table160_variants.csv` | primary BA 0.739 [0.42, 0.95 with 10,000 replicates; record 0.40, 0.95], Fisher p 0.235, Spearman 0.537 → INCONCLUSIVE; default-drop BA 0.568, Fisher p 1.0, Spearman 0.391 → DISCONFIRMED; without T1/T2 BA 0.614, Spearman 0.313 (one-sided permutation p 0.144) |
| (0b) site | S1 0/526, S2 0/527, S5 6/521 correct off-default; S1E excess +0.231 (find duplicate), +0.179 (connected components); S3:S0 flips 12:0, exact McNemar p 0.000488 |
| (0c) `tables/table157_matched.csv` | on the 3 push-defined events: push −0.761, association −3.115, proximity −2.918; over 5 with uniform fill: push −1.366, association −3.462 |
| (0i) `rivals.json`, `results/rival_scores.json`, `tables/rivals_scores.csv` | Spearman with E_pool (n): R1 −0.33 (14), R2 +0.30 (13), R3 −0.16 (15), R4 +0.38 (15), R5 +0.39 (14), R6 +0.14 (15), R7 −0.16 (15), R8 +0.21 (14), K +0.46 (15); all descriptive, every Holm p = 1.0; 10 of 15 tasks at E_pool = 0 |
| dose check (`tables/dose_units.csv`) | E_pool vs ban unit / residual norm: Spearman −0.06, AUC 0.49 (post-freeze, descriptive) |
| `figures/fig_rivals.{pdf,png}` | 8 panels, rivals against E_pool |

**Where these appear in the paper.** Each entry of `corrections.json` names the report location it replaces. The
locations are in the run's iteration-4 report, as revised for iteration 5:

- Tables 92c, 122, 123, 126, 139, 147, 157, 159, 160, 162, 163 and 164.
- Sections 3.2.5, 4.2.1, 4.2.2, 4.3, 4.4, 4.5, 4.6, 4.10 and 4.11.
- The closing paragraphs and "What remains open".

The rival scores and the frozen definitions feed the Step-0 / Claim A1 rival comparison. They are screen data and
descriptive only. The confirmation on new tasks (Step 2) uses the frozen A1-transferable rivals R1, R4, R6 and R7,
plus K.
