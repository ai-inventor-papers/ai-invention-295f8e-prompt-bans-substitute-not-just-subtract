# Fixing the record, freezing the push screen

This is Step 0 of iteration 4 of an algorithm-choice study on Qwen3-8B, with Llama-3.1-8B as the replication model. It runs on CPU only. No model text is generated, and the only LLM calls are the blind judges of the 'other' audit (0d), which cost **USD 0.22**. Every number is recomputed from labelled rows already on disk in the 11 declared dependencies. Each number cites its source as `<artifact_id>:<relative path>`.

## Headline results

| Item | Result |
|---|---|
| 0a knob table | 1,120 cells (artifact × task × arm × dial), each priced against its own twin. 25 of 27 quoted review numbers reproduce. Two are corrected. First, "nothing reaches Hill 1.5 under 20 points on R1/R3/R6/T11/T13/T14" is false once the T14 modal ban (1.78 at 17 pts) and the exp14 exposure arms are counted. Second, the two-sum α=2 avoidance is 0.469 on the attempted denominator, against the review's 0.48 (= 1 − 26/50). |
| 0i screen | `screen.json`, sha256 `d6a2ca9711f461973c39482314a523d448d0590cb40e32432826dec1da4846e8`. Movable tasks: T03, T05, T06, T1, T10, T2, which is exactly the frozen C1 set. Movable against catalogue-only ban avoidance ≥ 0.5 gives a 6/0/0/8 table (one-sided Fisher p = 1/3003). This is descriptive: screen, not confirmation. |
| 0b route landing | All 7 recorded readings reproduce. JS divergence matches exp16 to 1e-6 on 17 of 17 arms. exp16's pooled F_prompt 0.611 [0.06, 1.17] and F_direct 0.744 [0.38, 1.11] reproduce exactly. Without T13 they are 0.648 [−0.08, 1.38] and 0.865 [0.68, 1.05]. T13 is not gated under catalogue-only avoidance (0.15). |
| 0c Llama hits | With 'other' removed as nominee and as landing: LADDER 6/13 (Poisson-binomial p = 0.100) and ASSOCIATE 7/13 (p = 0.032). Table 102 checks 3/3. Snap-back: the default takes 0.72, 0.73 and 0.93 of non-banned attempts. |
| 0d 'other' audit | 21 events and 226 unique programs, of which 6 pass. Final classes: 68 catalogue variant, 156 degenerate, 2 labeller miss, **0 novel**. Judge κ(A,B) = 0.77. Judge A falls below the 5/6 control gate and gets no weight. The manual read covers 73 programs. Residue-gated events are exp13 T13, exp16 T13:a and Llama T06. Merge intervals: 29 coverage-array, 12 unsorted-sweep and 3 other programs, all failing. |
| 0e figures | Five captioned markers (M1–M5) and a 2×2 composite in activation coordinates (MDS stress-1 0.025/0.006). At the fixed g16 position, BFS's nearest neighbour is IDA* rather than BiBFS. |
| 0g rigor | Defined-only hit rates. The exposure SUBTRACT forecast is defined for 4 of 33 shown algorithms and hits 4/4 in both arms. Table 82 per distinct row: gain 0/11, residual 0/11, implied mass 8/11 (6 of them sham rows). |
| 0h wording | Replacement sentences for Section 3.10 are in `corrections.json` and `results/wording.json`. |
| 0j rivals | Spearman ρ against catalogue-only avoidance: movable 0.86, max E_t 0.85, can 0.16, clarity −0.07, FRLP runner-up mass 0.19, nonce −0.19, novelty 0.35. These are screen values, not confirmation. |
| audit | `audit/rederive.py` is a stdlib-only reimplementation: 29 checks, 0 mismatches, and the screen sha256 matches byte for byte. `audit/rederive_extra.py` adds 12 checks (sklearn/scipy), with 0 mismatches. All 7 placebos fail to show an effect, as required. |

## Layout

| Path | What it is |
|---|---|
| `eval.py` | Single entry point with stage flags (`--stages all` or a comma list). |
| `src/paths.py` | Maps artifact ids to dependency roots (`AII_ITER1/2/3`) and builds citations. |
| `src/labels.py` | G1: catalogues (exp11 `spec.json`; T1/T2 lists), aliases, defaults. |
| `src/rows.py` | G2: unified row table, written to `data/rows.parquet`. |
| `src/stats.py` | Rarefied Hill-1, Good's coverage, Newcombe, Poisson-binomial, permutation Spearman, jackknife, kappa. |
| `src/knob.py`, `src/screen.py` | 0a knob table, direction counts, Table 110, verification targets, per-task verdicts; 0i screen. |
| `src/route.py`, `src/llama.py` | 0b route landing and route fractions; 0c Llama hit rules. |
| `src/other_audit.py`, `src/run_judges.py`, `src/other_assemble.py` | 0d pool and features, blind judges, assembly. |
| `src/figures.py`, `src/rigor.py`, `src/wording.py`, `src/rivals.py`, `src/outputs.py` | 0e, 0g, 0h and 0j, plus the output contract. |
| `screen_rule.py` | Stdlib-only screen rule. `python screen_rule.py screen_input.json out.json` reproduces `screen.json` byte for byte. |
| `screen.json`, `screen.sha256`, `screen_extras.json`, `screen_input.json` | Frozen screen core, its hash, the unhashed extras (per-direction rows, power notes, Fisher p, discrepancies) and the rule input. |
| `full_eval_out.json` (= `eval_out.json`), `mini_eval_out.json`, `preview_eval_out.json` | `exp_eval_sol_out` output. Section summaries are under `metadata.sections`, with one dataset per section. |
| `corrections.json` | Each review item (0a–0j) with replacement sentences, recomputed numbers, sources and a status. 0f is delivered by this iteration's research artifact (Table 92b). |
| `tables/` | `knob_table.csv`, `arm_dictionary.csv`, `random_direction_counts.csv`, `table110_alpha2.csv`, `verification_targets.csv`, `per_task_verdict.csv`, `route_landing.csv`, `llama_hits.csv`, `other_audit_programs.csv`, `other_audit_events.csv`, `catalogue_only_avoidance.csv`, `merge_intervals_correction.csv`, `defined_only_hits.csv`, `table82_distinct_rows.csv`, `rival_predictors.csv`, `rival_predictor_values.csv`, `knob_rows_not_recomputed.csv`. |
| `figures/` | Captioned markers `marker_M1..M5_*.{png,pdf}`, `composite_2x2_activation.{png,pdf}` and `captions.json`. |
| `audit/` | `rederive.py`/`rederive.json`, `rederive_extra.py`/`rederive_extra.json`, `placebos.py`/`placebos.json`, judge cache (`judge_cache.jsonl`), judge results, the 0d pool (`pool.parquet`, `pool_events.json`), the manual pass (`manual_pass.json`, `manual_sample_ids.json`), and the hidden-test re-run harness (`rerun/`). |
| `results/` | One JSON per section: screen summary, route, llama, other audit, figures, rigor, wording, rivals. |
| `inputs.json` | G0 inventory of every declared input file: sha256, bytes, rows, fields. |
| `tests/test_stats.py` | Unit tests on hand-computed toy cells. Run with `uv run pytest`. |
| `reproducibility.md` | Seeds, versions, deviations and departures from the plan. |

## How to run

```bash
uv sync --frozen                     # .venv with the exact versions pinned in pyproject.toml / uv.lock (Python 3.12)
# dependency artifacts are read from sibling folders named by artifact id (or original folder name) under
# AII_DEPS_DIR (default: this folder's parent); on the run server AII_ITER1/2/3 or paths.local.json are used
uv run eval.py --stages all          # about 1.5 minutes; the judge stage reuses audit/judge_cache.jsonl, so it costs nothing
uv run pytest                         # unit tests
python3 -I audit/rederive.py         # independent re-derivation (stdlib only)
uv run python audit/rederive_extra.py   # second independent re-derivation with shuffled-input placebos
```

See `reproducibility.md` for the full step-by-step record (versions, seeds, hardware, runtimes, expected numbers).

The judge stage (`src/run_judges.py`) needs `OPENROUTER_BASE_URL` and `OPENROUTER_API_KEY` only for prompts that are not already in `audit/judge_cache.jsonl`. It checks `GET <base>/key` first, stops if less than USD 3 remains in the shared pot, stops at USD 1.8 of its own spend, and cancels everything on the first budget 403.

## Publishing notes

`paths.local.json` holds the machine-specific dependency roots and is excluded from the published repository, along with `.venv/`, `__pycache__/` and `.pytest_cache/` (upload-ignore regexes: `(^|/)\.venv/`, `(^|/)__pycache__/`, `(^|/)\.pytest_cache/`, `(^|/)paths\.local\.json$`).

## Kept artifacts

Everything except the virtual environment and caches is kept on the run's volume at the paths above. All kept files are under 10 MB and are published.

## Restoring removed files

| Removed path | How to restore |
|---|---|
| `.venv/` | `uv sync --frozen` (exact pins from `pyproject.toml` / `uv.lock`) |
| `**/__pycache__/`, `.pytest_cache/` | Regenerated automatically by running `uv run eval.py --stages all` or `uv run pytest`. |
