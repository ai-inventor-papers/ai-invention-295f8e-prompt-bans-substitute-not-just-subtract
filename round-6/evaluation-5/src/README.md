# Iteration-6 Step 0: record repair and a second novelty check

This is a CPU-only evaluation with no model generation. It recomputes, from the rows on disk, every number that the
iteration-6 record repair of the run's report touches. Each result carries the numerics it was produced under. The
landing and movability verdicts are restated with exact small-sample statistics. The missing tables are filled in. The
14 programs that two of three judges called novel in iteration 5 get a second, blind adjudication.

Each change to the report is written as a verbatim `old_text` to `new_text` pair keyed to `current_report.md`
(`corrections.json`, marker `iteration-6 correction`). An independent standard-library re-derivation
(`audit/rederive.py`) checks the recomputed numbers, and its placebos must fail.

## Headline results

**0a. Engine and dose.**
- The two dose definitions disagree. Table 174's ratio of mean norms runs from 0.745
  (connected components) to 0.974 (kth smallest) on the decisive tasks, with find
  duplicate at 0.620. The knob experiment's mean of per-position ratios is
  0.829 to 1.394. A mean of ratios is not a ratio of
  means. The knob experiment's n counts plan-noise rows, which share one value per prompt wording, so it is not a count
  of independent measurements.
- The two artifacts' `off_default_share` fields measure different things, and the record compared them directly (grid
  0.02 against 0.24, for example):
  - bf16 knob experiment: correct programs off the default, over all samples;
  - 8-bit plan-noise experiment: valid attempts off the default, over all samples.
- Every contrast is therefore recomputed under both definitions. The decision rule was fixed before computing. The
  bracket compares the bf16 alpha-2 cell, which delivers at least 1.24 FP8 ban units under either dose definition,
  with the FP8 alpha-1 cell. Correct-only counts:

| Task | FP8 a1 | FP8 a2 | bf16 a1 | bf16 a2 | Fisher p (a2) | bracket p | tag |
|-|-|-|-|-|-|-|-|
| connected components | 6/50 | 30/50 | 1/50 | 1/50 | 7.2e-11 | 0.056 | did NOT replicate in bf16 at the population level |
| shortest path | 9/43 | 15/37 | 0/50 | 2/47 | 5.3e-05 | 0.017 | did NOT replicate in bf16 at the population level |
| kth smallest | 14/50 | 23/47 | 4/49 | 14/50 | 0.039 | 0.588 | not established |
| grid | 1/35 | 4/36 | 0/40 | 1/38 | 0.194 | 0.732 | not established |
| two sum | 0/50 | 1/50 | 0/50 | 2/50 | 1.000 | 1.000 | not established (no FP8 effect of at least 10% at alpha <= 2 to replicate) |
| find duplicate | 0/50 | 0/49 | 0/30 | 0/30 | 1.000 | 1.000 | not established (no FP8 effect of at least 10% at alpha <= 2 to replicate) |

- `engine_labels.json` has 24 rows:
  - 4 'did NOT replicate in bf16 at the population level';
  - 3 'FP8 only, untested in bf16': the site odds ratio, the same-seed contrast and the
    plan subspace;
  - 4 'bf16-conditional' verdicts.
- Like-for-like figure, Spearman with beta:
  - bf16 existing tasks 0.59 (one-sided p 0.010);
    with the 8-bit screen E instead, 0.79;
  - new units 0.15 (p 0.315);
  - pooled bf16 0.48.

**0b. Landings.**
- The base runner-up named the push landing in 17 of 21 events (Poisson-binomial p
  5.8e-07). Per set:
  - 8-bit screen: 5/5;
  - bf16 remeasure: 1/2;
  - panel A: 3/3;
  - panel B: 3/4;
  - Gemma: 5/7.
- On the held-out events where the instruct twin wrote no correct program off the default, it named
  5 of 8 (p 0.053): Qwen
  3/4, Gemma 2/4. By the frozen rule,
  5.11 item 2 moves to the descriptive results (pooled unconfounded p >= 0.05).
- The twin's own most frequent alternative is defined on 7 events. There it names the landing
  6 times, against 6 for the base runner-up (McNemar p
  1.000). Where the twin writes an alternative, the landing half is the twin's
  own minority.

**0c. Movability.**
- Over the 13 new units, Spearman is 0.15:
  - Bonett-Wright 95% [-0.44, 0.65];
  - Fieller [-0.46, 0.66];
  - bootstrap BCa [-0.50, 0.70];
  - one-sided permutation p 0.317.
- Power at a true 0.6:
  - 0.63 for the registered one-sided permutation test;
  - 0.50 two-sided (the direction's quoted 0.46 matches the two-sided figure);
  - 20 units would give 0.8.
- So beta is not a strong predictor, a moderate relation is not excluded, and the verdict is bf16-conditional.
- The pooled value leans on one unit. Count inversions has a committed beta of 0.75, taken from base attempts because
  only 15 base programs were correct, and 58 of its 87 attempts are unlabelled 'other'. On the correct-only basis
  used for the other twelve units its beta is 0.13, and the pooled Spearman falls to 0.035
  (`rho_beta_E_correct_only_basis`).
- Under one definition of each rival, only the runtime merit R6 tracks movability (Spearman
  0.71, Holm p 0.021). The paired interval for
  beta minus R6, [-1.26, 0.20],
  includes 0.

**0d / 0e. Missing tables and minor fixes.**
- Phrasing clusters at theta 0.7/0.8/0.9 rise only at T 1.3 (5/7/12), and the T 0.7 repeat gives 3/6/10.
- P15/P20 columns are added, and the spot checks match.
- The panel B knob rows are added. Three push programs on count inversions (fenwick tree) fall outside the base
  repertoire.
- Table 126c rows: Hill-1 2.87, 2.96 and 2.92.
- Plan noise against matched decoding is 19:3 at alpha 2, but 13:0 of that is kth smallest; the other four tasks give
  6:3 (p 0.508).
- Gemma: 1.50 nats with uniform fill, 1.57 on the 6 defined events.

**0f. Second blind adjudication of the 14.**
- Every program is stress-tested in a sandbox. All pass the hidden tests. One, repeated maximum selection on top-k
  frequent, times out at the maximum size.
- Judges, from model families this run never used:
  - Mistral Medium 3.1, three calls at temperature 0, Fleiss 1.00: control gate
    9/10;
  - Kimi K2: gate 9/10.
- Novel calls: 1 of 14 (Mistral) and 0 of 14 (Kimi). Final count after the
  executor's read of all 14: 0.
  - P13 (R6) was called novel. The judge names no technique, and its reason is 'Uses linear search with early termination, not a known efficient technique for sorted arrays.'. The program passes 56 of 56 hidden tests and every stress group. Final read: range guards plus a linear scan to the first match and over its run: linear search.
- Agreement with the manual verdict on the 14:
  - raw 0.86 (95% 0.57 to
    0.98);
  - AC1 0.83, kappa 0.71;
  - binary kappa is 0 by construction against a constant reference and binary AC1 is 0.92.
  - With the controls (24 items): kappa 0.80, bootstrap
    [0.57, 1.00].
- The final read corrects one manual class. Program P21 is a linear scan plus `list.count`, not a binary search.
- Across the judge passes (`audit/judge_runs_summary.json`; listed as passes 1, 2 and 3, then the final state, which
  reuses pass 3's cached calls and re-queries two empty Kimi outputs):
  - Mistral's novel calls on the 14: 0, 0, 1, 1;
  - its control gate: 9, 10, 9, 9 of 10;
  - Kimi's novel calls: 0, 0, 0, 0.
  The first two passes had run-dependent timings in their prompts. What varies is P13 and the contested control, which
  the iteration-5 manual pass itself classed as a catalogue variant. No pass produced a novel call that survived a full
  read.

**Audit.** `audit/headline_check.py` independently reproduces 7 of 7 headline numbers from the rawest files:
- per-sample labels for the engine contrast;
- per-event records for the tallies;
- compositions and per-direction cells for rho;
- raw judge responses for the adjudication.
Its placebos (permuted engine labels, landings, beta and verdicts) all fail. `audit/rederive.py` passes 277 of 277 checks, and
5 of 5 placebos fail as required. `corrections.json` holds
36 corrections (78 values MATCH, 1 CORRECTED,
18 NEW, 2 CARRIED). No two corrections overlap, and every `old_text` occurs exactly
once in the report.

## Layout

| Path | What it holds |
|-|-|
| `eval.py` | Entry point. Stages s0, 0a (engine and dose), 0b (landings), 0c (movability), 0d (missing tables), 0e (minor), 0f (second adjudication), audit and out |
| `src/common.py` | Dependency resolution by artifact id, provenance strings, input hashing, report index, value statuses, corrections ledger |
| `src/xstats.py` | Exact tests (Fisher, McNemar, Poisson-binomial, Clopper-Pearson, Katz), Spearman permutation and bootstrap (percentile, BCa), Fisher-z intervals (plain, Fieller, Bonett-Wright), Gaussian-copula power, kappa, AC1, Fleiss |
| `src/adjudicate.py` | Stage 0f: items, controls, sandboxed stress tests, Zhang-Shasha nearest solutions, blind judges, agreement |
| `src/sandbox_child.py` | Sandboxed runner for one program; per-case wall-clock limits |
| `src/outputs.py` | Builds `corrections.json` and `eval_out.json`, plus the metrics |
| `vendor/eval2_stats.py` | The run's own statistic code (`art_CcZLW-9NX00l:inputs/eval2/common/stats.py`), used for correct-only rarefied Hill-1 at depth 25 |
| `vendor/bench_checkers/` | Task checkers copied from the bench of `art_CcZLW-9NX00l` |
| `audit/rederive.py`, `audit/rederive_report.json` | Independent standard-library re-derivation with placebos |
| `audit/judge_cache.jsonl` | Every judge response, with usage and cost (kept) |
| `audit/final_read.json` | The executor's full read of the 14 disputed programs: a one-line verdict each |
| `audit/judge_runs_summary.json`, `audit/summarise_judge_runs.py` | The judge passes side by side (novel calls, control gates, spend) |
| `results/0f_run2_prompts_with_timings.json` | Stage 0f of pass 2, kept because its prompts differed (they carried run-dependent timings) |
| `src/readme_results.py`, `src/finalize.py` | Fill this README's results from the result files; strip NUL bytes and absolute paths before publishing |
| `scratch/` | Working directory of the sandbox runner, plus two small development helpers (`peek.py`, `patch.py`) |
| `inputs/report/current_report.md` | The iteration-6 report the corrections are keyed to, vendored so that the old_text checks run anywhere |
| `inputs/art_mgek9PfVBNbh/`, `inputs/art_sV0cQ3ef1ZRQ/` | The few files read from two earlier evaluations that are not declared dependencies |
| `audit/headline_check.py`, `audit/headline_check.json` | Short independent re-derivation of the headline numbers from the rawest files, with placebos |
| `eval_out.json` (+ `full_`/`mini_`/`preview_`) | Output in the `exp_eval_sol_out` format: 10 datasets and the aggregate metrics |
| `corrections.json` | Every report correction: `old_text`, `new_text`, location, values with recorded, recomputed, status and source |
| `engine_labels.json`, `tables/engine_labels.csv` | One row per internal result of iterations 2 to 5, with engine class, bf16 counterpart and status |
| `tables/*.csv` | `dose_reconciliation`, `engine_pn_contrast`, `landing_events`, `movability_units`, `rival_scores`, `phrasing_literal_cell`, `prices_p15_p20`, `panelB_knob_rows`, `table126c_rows`, `pn_vs_dmd_discordant`, `novelty_readjudication` |
| `figures/fig_beta_escape_l4l.{pdf,png}` and `_spec.json` | Base off-default share against the bf16 escape fraction, existing and new tasks like for like, with 8-bit ghost markers |
| `results/*.json` | Full per-stage results (`0a` to `0f`, `s0`) and the per-stage correction lists |
| `input_hashes.json` | sha256 of every input read, plus the report's |
| `reproducibility.md` | Environment, seeds, departures from the plan |

## How to run

```bash
uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r requirements.lock.txt
export AII_DEPS_ROOT=..            # folder holding the dependency artifacts (default: the parent folder)
uv run eval.py --stages all
uv run python audit/headline_check.py
```

The dependencies are looked up by artifact id inside `AII_DEPS_ROOT` (see `reproducibility.md`). The report and two
non-dependency evaluations ship in `inputs/`.

The full run takes about 7 minutes on 6 CPU cores. Most of it is spent on the sandboxed stress tests and the tree
edit distances. Stage 0f reads `audit/judge_cache.jsonl`, so a rerun makes no paid call. The first run cost
USD 0.29 in all, over 4 judge passes on OpenRouter.

## Restoring removed files

`.aii/manifest.yaml` marks five paths for deletion after the round. All of them are regenerable.

| Deleted path | Command that brings it back |
|-|-|
| `.venv/` (the Python environment) | `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r requirements.lock.txt` |
| `src/__pycache__/` | `uv run python -m compileall -q src` |
| `vendor/__pycache__/` | `uv run python -m compileall -q vendor` |
| `vendor/bench_checkers/__pycache__/` | `uv run python -m compileall -q vendor/bench_checkers` |
| `scratch/__pycache__/` | `uv run python -m compileall -q scratch` |

The four `__pycache__/` directories hold Python bytecode, and Python also recreates them on the next import, for
example on `uv run eval.py --stages all`.

Nothing else is deleted. The results, tables, figures, logs, `audit/judge_cache.jsonl` (the paid judge responses
that make reruns free) and the vendored `inputs/` are small text files, kept where they are. No file here reaches
100 MB, so the published repository holds everything except `.venv/`, the bytecode caches and `TODO.md`.
