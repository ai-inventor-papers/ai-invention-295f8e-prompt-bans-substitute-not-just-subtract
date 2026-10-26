# Round-one audit: when is the algorithm chosen?

An evaluation of the six iteration-1 experiments of run `run_4VFKidE1bxPG` (Qwen3-8B, two path-search coding tasks:
T1 unweighted grid path, T2 weighted shortest path). It reads their outputs in place. It generates nothing, makes no LLM
calls and spends $0 on OpenRouter. It carries out step 0 of the hypothesis in eight parts:

- **0a** the locus probe that never ran;
- **0b** geometry robustness;
- **0c** a cross-experiment perturbation table;
- **0d** record corrections: per-draw substitutes, cumulative bans, a one-statistic knob table, PREDICT on gated events, and BUY;
- **0e** seeds;
- **0f** missing outputs;
- **0g** sham-ban promotions;
- **0h** dated positioning.

Every number names its source as `expN/<relative path>[#filter]`:

| Label | Experiment | Artifact |
|---|---|---|
| exp1 | association | art__skdlFp_o3e9 |
| exp2 | geometry | art_D6Z0Snf09sFL |
| exp3 | forking token | art_1yV2vQ0EH4OY |
| exp4 | decommitment | art_U5UKkFrOgSsE |
| exp5 | instruction tuning | art_HF8nK8B_Lqyy |
| exp6 | decoding | art_UoCVh2Qe5RZ0 |

## Headline results

### 0a Locus probe

Inputs are exp3's saved states: 2 tasks × 300 rows × 8 positions × layers 8-28. The probes are leave-one-paraphrase-out
L2-logistic probes with 200 global and 200 within-paraphrase refit nulls and a layer-max family-wise null. A batched
Newton-IRLS solver in torch was unit-tested against sklearn: predictions were identical and the maximum relative
coefficient difference was 3.9e-5.

**Why it never ran.** `exp3/probes.json` is 28 bytes and was written at 18:29. The states were saved at 18:34:34 and
18:34:50. The probe stage therefore ran before its inputs existed.

**T1: mechanical verdict R.** No candidate position passes the 20-point rule.
- The R state already reads the within-ban outcome at BA 0.855 (layer 16) under leave-one-paraphrase-out.
- At every generated position the within-paraphrase null p95 is at or above the observed BA, so the signal is paraphrase-level, not sample-specific.
- The written-text control peaks at BA 0.673.
- BFS and DFS rows share the commit token `' deque'`, so the AST commit index does not separate the classes on T1.

**T2: mechanical locus k_pre, qualified as POST-COMMIT READOUT.**
- At k_pre (layer 8) BA is 0.762, +0.281 over R (95% CI [0.145, 0.388]), with within-paraphrase p = 0.005.
- The written prefix alone reaches BA 0.756 at k_pre, so state minus text is +0.006, below the 0.10 margin.
- The text separates the classes from k=4 on: Dijkstra rows write `import heapq`, BF/SPFA rows write `from collections import deque`.
- The deciding token is generated index 3. It is emitted from the unsaved states at k=1..3, and those are the extraction target for the next round.
- exp3's own fork screen independently confirmed a fork at index 3 (`import`, TVD 0.80; `exp3/forks.json`).
- The first k with BA_text ≥ 0.8 is 8.

**Other 0a results.**
- **Difference-in-means AUC:** below the 0.9 reopening bar at k_pre on both tasks (T1 0.882, T2 0.749).
- **R-compliance preview:** Spearman ρ 0.63 (exact p 0.056) on T1 and 0.65 (p 0.045) on T2.
- **Positive controls P1 and P2:** BA ≈ 1.0.

### 0b Geometry

- **Reproduction:** exp2's committed matrices and the T2 sensitivity matrix were reproduced exactly (max |diff| 0.0000).
- **T2:** Floyd-Warshall is the nearest survivor to the Dijkstra centroid in 100% of 1000 paraphrase subsamples at all 28 (layer, k) settings. BF/SPFA is never nearest; its full-data rank is 2 in 75% of settings and 3 in 25%.
- **T1:** DFS is nearest at layers 25-28 (P 0.87-1.00). At layer 24 the order flips to UNIT_DIJKSTRA first (P(DFS) 0.52-0.60).
- **Masked prompts** give different orders.
- **Wording:** *consistent with geodesic proximity and with typicality; not separated on these events.*

### 0c Perturbation table

The table has 249 condition rows covering 20,270 programs. On T2, 8/8 non-semantic and 3/4 semantic perturbation rows
with at least 10 correct non-Dijkstra programs are majority BF_SPFA, random steering directions included. On T1 only 2
non-ban rows leave BFS.

### 0d Corrections

**Per-draw substitutes.**
- T2: BF_SPFA 272/272 in 5/5 draws.
- T1: DFS 116/128 = 0.906 (Wilson [0.843, 0.946]; draw-cluster bootstrap [0.75, 0.98]). Per draw: 38/38, 10/18 (plus 8 UNIT_DIJKSTRA), 40/41, 16/18, 12/13. The realised mode is DFS in 4 of 5 draws.

**Cumulative BFS+DFS ban.** The result does not replicate across the three draws:

| Draw | Mechanism-level banned share | Compliant programs |
|---|---|---|
| decommitment | 0.81 | 16: UNIT_DIJKSTRA 13 + ASTAR 3 |
| geometry | 0.62 | 18: UNIT_DIJKSTRA 18 |
| association | 0.94 | 5: UNIT_DIJKSTRA 4 + ASTAR 1 |

The first element of each quoted pair (0.88, 0.96, 0.53) is the pass rate. The second element could not be reproduced.

**Knob table.** The statistic is compliant-only rarefied Hill-1 at depth 25.
- No diversity knob or ban reaches Hill ≥ 2 at < 20 pass points on either task.
- The closest is the T2 semantic seed: 1.935 at 7 points.
- The named-mode cue `mention:astar_gbfs` reaches 2.69 at 11 points on T1; it only meets the literal flag.
- The gen-then-select ceiling reaches 3.36 on T1 and 2.80 on T2.

**PREDICT.**
- 3 informative events pass the gate. The literal gate passes 12, because it also admits the nine bans of absent modes.
- 2 of the informative events have disagreeing top-1 nominations, and the largest margin is 0.05 nats.
- No family can advance under the rule.

**BUY.** No knob advances: the 90% CIs do not separate.

### 0e Seeds: double dissociation

| Task | Semantic-seed cosine to implied centroid | Behaviour shift among correct programs |
|---|---|---|
| T1 | 0.493 | +2.15 points |
| T2 | -0.087 | +66.3 points toward BF_SPFA |

The T1 word seed shifts the probe +0.88 toward ASTAR with no behavioural change.

### 0f Missing outputs and bookkeeping

- **GPU hours** (union of phase-log spans): exp2 2.92, exp3 1.55, exp4 3.23, exp5 2.47, exp6 3.31. Nothing was extracted for exp1.
- **exp1 DFS failures:** 161 of 273 programs fail: 127 wrong answers, 31 timeouts, 3 runtime errors.
- **Base-model caveats:**
  - parse rate 0.58 (T1) and 0.66 (T2);
  - 57 and 90 correct programs;
  - the template-free T2 run has BF_SPFA as its mode (16/25).

### 0g Sham bans

Of the nine bans of absent modes, 2 produce a promotion:
- IDDFS ban → DFS, +12 points;
- Floyd-Warshall ban → BF_SPFA, +23 points.

Both promoted survivors are content neighbours of the banned mode and also the runner-up, so the effect is confounded with the ladder.

### 0h Positioning

All eight arXiv ids were verified on 2026-10-20. Lee et al. (2606.29985) is EMNLP 2026 plus the ICML 2026 Ai4Math
workshop. Its PDF mentions temperature only as a sampling setting, so it is not cited for the temperature claim. Venues
not shown on the abstract pages (Binder et al. at ICLR 2025, Lu et al. at NAACL 2025) are marked unverified.

### Checks

- **Recompute-then-compare:** 38/40 quoted numbers match. The 2 mismatches are explained in `corrections.json#checks`.
- **Independent audit:** 20/20 re-derived numbers match, and all 3 placebos fail as they should.
- **Second audit (`audit_extra.py`):** 5/5 headline tests match their placebos' failure:
  - T2 k_pre layer-8 within-paraphrase p = 0.024 over 40 sklearn refits, against a placebo p of 0.17;
  - Floyd-Warshall nearest in 100/100 networkx draws, against 0.30 with shuffled labels;
  - 2 sham promotions, against 0 with shuffled conditions;
  - 3 gated events.

## Layout

| Path | What it is |
|---|---|
| `eval.py` | Entry point. Runs missing stages (or all with `--rerun`) and assembles `eval_out.json` (exp_eval_sol_out) and `corrections.json` |
| `common.py` | Paths (`ITER1_ROOT`), harmonisation maps, Wilson / Newcombe / Clopper-Pearson intervals, cluster bootstraps, rarefied Hill |
| `inventory.py` | G2: size, sha256, mtime, row count and distinct task/condition/arm/label of 98 input files → `inventory.json` |
| `locus.py` | 0a: batched IRLS probes, nulls, text control, text-locus curve, pre-commit qualifier, DiM, cosines, commit curve, R-compliance, PCA views → `results/locus.json`, `tables/locus_cells.csv` |
| `geometry.py` | 0b: reproduction of exp2 plus k × layer × 1000-subsample sweep and the masked sensitivity → `results/geometry.json`, `tables/geometry_stability.csv` |
| `tables.py` | G3, 0c-0g: harmonisation, perturbation table, corrections, knob table, gated PREDICT, BUY, seeds, missing outputs, sham bans → `results/tables.json`, `results/harmonise.json`, `results/reference_map.json`, `tables/perturbation_table.csv`, `tables/knob_table.csv` |
| `results/positioning.json` | 0h: dated web check (raw fetch logs in `logs/web/`) |
| `figures.py` | Figures (PDF + PNG) in `figures/`; the specs sit beside them as `.json` |
| `audit.py` | Independent re-derivation of 20 headline numbers plus 3 placebos → `results/audit.json` |
| `audit_extra.py` | Second independent audit of the headline tests (T2 k_pre within-paraphrase permutation test, FW-nearest share, sham promotions, PREDICT gate), each with a placebo that must fail → `results/audit_extra.json` |
| `full_eval_out.json`, `mini_eval_out.json`, `preview_eval_out.json` | Full / 12-example / truncated variants of `eval_out.json` (aii-json format script); all pass the schema |
| `reproducibility.md` | Exact step-by-step reproduction: environment, pins, inputs, commands, seeds, hardware, expected numbers |
| `pyproject.toml`, `requirements.txt` | All 71 packages pinned to the versions installed in `.venv` |
| `eval_out.json` | Final output. Contains `metrics_agg` (80 headline scalars), `metadata` (the ten sections plus checks and audit), and datasets: `perturbation_table` (249), `locus_cells` (903), `knob_table` (183), `geometry_grid` (56) |
| `corrections.json` | Each reviewer item with its recomputed numbers and sources |
| `results/locus_smoke.json`, `results/locus_unittest.json` | Smoke-test timing (one cell, 401 label vectors in 0.94 s) and the solver unit test |
| `logs/` | Run logs and `todo.md` |

## How to run

```bash
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r requirements.txt      # 71 exact pins, same as pyproject.toml
# inputs: a directory holding gen_art_experiment_1..6 (the six iteration-1 artifacts, see reproducibility.md)
export ITER1_ROOT=../path/to/iter1_artifacts
.venv/bin/python eval.py --rerun      # ~15 min with a GPU (locus 8 min on an RTX 4090; geometry 5 min on 6 CPUs)
```

The Qwen3-8B tokenizer is used only to decode prefixes. It is read from the sibling run's HF cache when present.

## Departures from the plan, and what they cost

- **Small n.** There are 99-100 within-ban rows per task, 20-21 in the minority class, in 10 paraphrase clusters. Only effects of roughly 15-20 BA points are detectable.
- **Scope.** One model, one draw, decodability only. Verdicts read "readable at", never "decided at".
- **k_fork.** There are no saved states for k_fork on T1 or on the baseline arms (exp3 mask), so it is a T2-ban-only position.
- **Gating.** The PREDICT gate excludes exp1's nine absent-mode bans as uninformative. The literal count (12) is reported beside the informative count (3).
- **Re-execution dropped.** The None-as-[] re-execution was dropped (item 1 of the drop order). The stored failure fields do not hold returned values.
- **Seed shares.** These are reported over three denominators (attempted, correct, classified). The plan's quoted values are shares among correct programs.

## Restoring removed files

`.aii/manifest.yaml` marks only regenerable bulk for deletion:

- `.venv/`: recreate with
  `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r requirements.txt`
- `__pycache__/`: regenerated automatically by any `.venv/bin/python eval.py` run.

Everything else (results, tables, figures, logs, code) is kept. None of it is above 10 MB.
