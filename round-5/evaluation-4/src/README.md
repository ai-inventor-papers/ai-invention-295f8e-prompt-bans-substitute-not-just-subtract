# Fix the record, freeze rival predictors (iteration 5, Step 0)

This repository is a CPU-only evaluation artifact. It does two things with the row and result files of eight earlier
artifacts (listed below):

1. **Record corrections (0a)–(0h).** It re-derives every number behind the iteration-4 review items and writes each
   fix as an exact `old_text -> new_text` replacement in `corrections.json`, marked `iteration-5 correction`.
2. **Rival task predictors (0i).** It computes eight ban-free rival predictors (R1–R8) and an affordance covariate
   (K) for the 15 Qwen3-8B tasks, without reading any outcome file. It freezes them by sha256 (`rivals.json`,
   `rivals.json.sha256`, hash-chained `commitments.log`) and only then scores them, descriptively, against the
   iteration-4 escape fractions.

A separate audit script (`audit/rederive.py`) recomputes the key numbers from raw rows. It uses only the standard
library and shares no code with `eval.py`. It also runs four placebos, each of which must fail.

No model was run here. The only paid calls were cheap judge calls for the human-solution labels (R5): **USD 0.021**
on OpenRouter (`google/gemini-2.5-flash-lite`, temperature 0, cached in `rivals/judge_cache.jsonl`).

## Headline results

| Item | Result |
|---|---|
| Record re-derivation | 187 values had a record value: **186 MATCH**, 1 CORRECTED (see Discrepancies); 15 more are NEW (no record value) and 4 CARRIED; 6 of 6 Table 92c quotes **RE-VERIFIED live** (2026-10-21) |
| Independent audit | **195 checks, 0 failures**; all four placebos fail as required (BA under permuted E 0.50; S0/S1 swap OR 1.01 vs 101.7 real; landing shuffle shrinks 2.35 → 0.46 nats; permuted-E rejection 3.5–4.8 %) |
| (0a) Gemma held-out verdict | primary (catalogue-only avoidance): BA 0.74, Fisher p 0.235, Spearman 0.54 → **INCONCLUSIVE**; default-drop sensitivity: BA 0.57, Fisher p 1.0, Spearman 0.39 → **DISCONFIRMED**; the two measures are separated by the grid task (twin BFS 25 / DFS 25, the only NO-DEFAULT task under the iteration-5 rule) and find duplicate (38 failing *other* programs; 0.34 vs 0.72) |
| (0b) site | S1 0/526 and S2 0/527 correct programs off the default, S5 6/521; energy-matched read position +0.23 (find duplicate, Floyd 6 of 26) and +0.18 (connected components); generated-token noise beats the plan site on find duplicate 12:0 (exact McNemar p 0.000488; 6:0 among both-correct pairs) |
| (0c) landings on matched events | push −0.761 vs association −3.115 on the 3 events where push is defined; −1.366 vs −3.462 over all 5 with uniform fill; the review's −1.37 is the 5-event value, and it coincides at two decimals with the screen-push replication cell (−1.369) |
| Dose-confound check (post-freeze, descriptive) | E_pool vs ban unit / residual norm (exp23 per-task Qwen median, 14 tasks): Spearman −0.06, AUC 0.49, so movability does not track the dose unit |
| (0i) rivals vs E_pool (descriptive) | Spearman: K +0.46, R5 +0.39, R4 +0.38, R2 +0.30, R8 +0.21, R6 +0.14, R7 −0.16, R3 −0.16, R1 −0.33; every Holm-adjusted p = 1.0; 10 of 15 tasks tied at E_pool = 0 |

Every rival score is **screen / descriptive**. The escape fractions generated the hypothesis, and the run had seen
them before this freeze, so the freeze protects the Step-2 confirmation on new units, not this screen. The
A1-transferable rivals (R1, R4, R6, R7, plus K) are the ones frozen for Step 2.

## Layout

| Path | What it holds |
|---|---|
| `eval.py` | main script: corrections (0a)–(0h), then runs the rival freeze and scoring, the quote check and the audit, then assembles `eval_out.json` |
| `src/stats_util.py` | statistics shared by eval and the rival scripts: exact rarefied Hill-1, permutation Spearman, bootstrap, exact AUC, partial Spearman, Holm |
| `src/io_util.py` | dependency paths, hashed input manifest, provenance records with tolerance status |
| `src/assemble.py` | builds `eval_out.json` (schema `exp_eval_sol_out`) |
| `rivals/r6_merit.py` | times all 76 catalogue references on their hidden tests (1 warm-up + 5 timed runs) → `rivals/r6_merit_raw.json` |
| `rivals/r5_human.py` | labels Mercury human LeetCode solutions (sandboxed tests, frozen AST rules, blind judge) → `rivals/r5_human_raw.json`, `tables/human_labels.csv` |
| `rivals/compute_rivals.py` | computes R1–R8 and K with forbidden-input guards, logs every opened path (`audit/rival_inputs.log`), freezes them |
| `rivals/score_rivals.py` | checks the freeze and hash chain, records "targets opened", then scores descriptively → `results/rival_scores.json` |
| `quotes/verify_quotes.py` | live quote re-verification for Table 92c → `quotes/quotes_verified.json`, `tables/table92c.csv` |
| `audit/rederive.py` | independent stdlib re-derivation and placebos → `audit/rederive.json` |
| `figures/make_fig.py`, `figures/fig_rivals.{pdf,png}` | optional 8-panel figure of the rivals against E_pool |
| `corrections.json` | 35 replacement entries `{item, report_location, old_text, new_text, values[], marker}` |
| `rivals.json`, `rivals.json.sha256`, `commitments.log` | the frozen rivals (canonical JSON), their hash, and the hash chain (genesis = sha256('iter5_dir1')) |
| `eval_out.json` (+ `full_`/`mini_`/`preview_`) | final output: metadata sections a–i, provenance counts, discrepancies, not-computable list, costs, metrics_agg, five datasets |
| `results/` | `corrections_metrics.json` (all section metrics), `rival_scores.json`, `input_hashes.json` (sha256 of every dependency file read) |
| `tables/` | `table159_grid.csv`, `table160_variants.csv`, `table157_matched.csv`, `table163_caveat.csv`, `table139_hull.csv`, `llama_block.csv`, `dose_units.csv`, `pnplain.csv`, `direction_distributions.csv`, `direction_quantiles.csv`, `split_half.csv`, `signed_progress.csv`, `table147_depths.csv`, `table92c.csv`, `table123_exposure.csv`, `rivals_values.csv`, `rivals_scores.csv`, `rivals_intercorr.csv`, `human_labels.csv` |
| `ids.json` | canonical task ids and every spelling used by the dependencies |
| `reproducibility.md`, `pyproject.toml`, `requirements.lock.txt` | step-by-step reproduction, and the exact pins of all 28 installed packages |
| `logs/` | run logs |

## How to run

```bash
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python numpy==2.2.6 scipy==1.15.3 loguru==0.7.3 requests==2.32.4 \
    pyyaml==6.0.2 aiohttp==3.12.13 matplotlib==3.10.3
.venv/bin/python rivals/r6_merit.py      # CPU timing of the catalogue references (about 1 min)
.venv/bin/python rivals/r5_human.py      # human-solution labels (needs OPENROUTER_API_KEY / OPENROUTER_BASE_URL; cached)
.venv/bin/python eval.py                 # corrections -> freeze -> score -> quotes -> audit -> eval_out.json
.venv/bin/python figures/make_fig.py     # optional figure
```

`eval.py --skip-rivals --skip-quotes` re-runs the corrections and the audit without touching the freeze, and
`eval.py --assemble` rebuilds only `eval_out.json`. `compute_rivals.py` appends nothing to the chain when it
re-computes an identical `rivals.json`. If the file changes after targets were opened, it records a post-target
re-freeze.

The dependency artifacts are read in place, read-only. In the published repository each one is a sibling folder of
this one, named by its artifact id. The code resolves it as `<AII_DEPS_ROOT>/<artifact_id>`, where `AII_DEPS_ROOT`
defaults to the parent folder; `AII_DEP_<artifact_id>` overrides one of them (see `reproducibility.md`). The eight
inputs are:
`art_k6nzFCDLOjQP` (exp23), `art_Cx9JOh8soBw7` (exp20), `art_SHaWv77P1XCI` (exp22), `art_mWn-MQEnNelg` (exp19),
`art_Yu6GN6pLxW8f` (exp21), `art_HF8nK8B_Lqyy` (iteration-1 base data), `art_0ndRfWKBWclR` (bench) and
`art_j3Rm_lr2nzR6` (source data). Every value cites its source as `<artifact_id>:<relative path>`.

## Provenance tags and tolerances

- **RE-DERIVED**: recomputed here from a dependency row file.
- **READ**: taken from a dependency results file, cross-checked where rows exist.
- **CARRIED**: taken from the iteration-4 record because the source artifact is not a declared dependency (eval3
  knob table, Table 127 route landings, the Llama block, the iteration-3 direction counts).
- **RE-VERIFIED**: a quote matched live today.
- **NOT_COMPUTABLE**: with the reason.

Status against the record uses these tolerances: counts exact; rates 0.005; Hill-1, log scores and correlations 0.01;
intervals 0.02.

## Discrepancies and deviations

- Signed progress on connected components: the record's "22 of 35 cells" is not reproduced. The staged
  `explore.json` holds 24 block cells per quantity, and 22 of 24 have p < 0.05.
- E_pool = 0 holds on **10** of 15 tasks (find duplicate plus the nine 8-direction tasks), not the 9 the plan expected.
- The exp20 flip counts follow exp20's own D13 rule (no function named `solve` → invalid) and its off-default
  definition (*other* counts). The record's 12:0 is the attempts table over all 30 CRN pairs.
- R6 runner-up: on the shortest-path task the modal association answer is off-catalogue (*other*, 15 of 20), so the
  most frequent catalogue answer is used (Bellman-Ford/SPFA, 5 of 20). The same rule applies to every task.
- R5 is a gate-lite label set: AST-primary labels on rewritten method bodies, with the judge on every AST *unknown*
  and a 10-program audit per task (pooled agreement 0.97, kappa 0.97, n = 121). LeetCode cases that most accepted
  human solutions fail were dropped as outside the problem's constraints (684: 22 of 76 kept; 287: 77 of 87; 435:
  106 of 107). Two-sum cases without a solution were dropped. T1 is NOT_COMPUTABLE, because LeetCode 1091 is a
  different, 8-directional problem. Mercury is a runtime-stratified sample of accepted solutions, not a random one.
- Hash chain: the rivals were frozen at 11:59:44 UTC and first scored at 11:59:50. They were re-frozen twice with
  `values_identical_to_previous_freeze: true`. At 12:06:07, a re-freeze guard added to `compute_rivals.py` changed its
  sha256. At 12:26:58, the path-portability edits changed the sha256 of the R5/R6 scripts and of the timing file's
  path field. Earlier development freezes made before any target read were not kept.
- The iteration-3 direction cells behind Table 123 (two sum: best of 9, 1 qualifies; kth smallest: max of 21, 7
  qualify) are CARRIED as "max of K" with K and the qualifying count, not as full distributions.

## Kept artifacts and storage

Nothing heavy is produced: every output is a text file under 1 MB. The only large directory is the regenerable
`.venv/`, about 550 MB, which `.aii/manifest.yaml` marks for deletion. The kept results, tables, frozen rivals and judge
cache are all small and published with the repository.

## Restoring removed files

Every `delete` entry of `.aii/manifest.yaml`, with the command that brings it back:

- `.venv/` (deleted, regenerable; about 550 MB). The exact pins of all 28 packages are in `requirements.lock.txt`
  and `pyproject.toml`:
  `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r requirements.lock.txt`
- `src/__pycache__/` (deleted, regenerable): `.venv/bin/python eval.py --assemble` (any run that imports `src/`).
- `rivals/__pycache__/` (deleted, regenerable):
  `.venv/bin/python -c "import sys; sys.path[:0] = ['src', 'rivals']; import compute_rivals"` (a full
  `.venv/bin/python eval.py` also recreates it).
- `__pycache__/` (deleted, regenerable): `.venv/bin/python -c 'import eval'`. It is the bytecode of `eval.py`, which
  appears only when `eval.py` is imported as a module, and nothing needs it.

Note on re-running `rivals/r5_human.py`: its output records the judge spend of that run, so a re-run changes the file's
sha256. `compute_rivals.py` then records a flagged re-freeze, even though the labels come from the cache and do not
change.
