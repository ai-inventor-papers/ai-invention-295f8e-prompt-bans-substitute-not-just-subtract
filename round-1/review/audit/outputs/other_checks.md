# Checks made by hand during the audit (read-only reads of the iteration-1 artifacts)

Artifact root: the parent run's `3_invention_loop/iter_1/gen_art/` (paths below are relative to it).

## Recomputed and matching the report
- Table 3 (dataset): `gen_art_dataset_1/full_data_out.json` holds 10 datasets, 61,469 examples; the llm_creativity labels are dijkstra 132, bellman_ford_spfa 34, bidirectional_search 30, other 21, dial 5, a_star 2, floyd_warshall 1.
- Table 4 / Table 34: the report writer's `work/replication.py` output (in the gen_report_text module) matches the per-sample rows; the recomputation scripts in this folder give the same counts.
- Table 7 log scores, recomputed by hand with the shared 5% uniform mix over survivors and the 2% "other" floor:
  Borda on grid ban BFS (0.95*0.054+0.01)*0.98 -> ln = -2.81; Borda on shortest-path ban Dijkstra (0.95*0.492+0.0125)*0.98 -> -0.754;
  uniform -1.630 / -1.406; free-form (19/20 DFS) -> -0.112; listing control (3/3 DFS among survivors) -> -0.061.
- Table 14, geodesic kernel on grid ban BFS: median centroid distance 71.06 (15 pairs from `results/manifold.json`),
  kernel weights give p(DFS)=0.288, p(unit-Dijkstra)=0.226; over 29 DFS + 9 unit-Dijkstra scored samples the mean is -1.337.
- Table 32 values match `gen_art_experiment_6/results/analysis.json` (`subspace_test`): word seed T1 1.555 [1.309, 1.850].
  The artifact's summary text gives [1.27, 1.87]; the report follows the file.

## Findings used in the review
- PREDICT informative-event gate omitted by the report: `gen_strat_1` rationale says "on every informative event
  (banned mode present at >= 10% of the latent baseline, compliance >= 50%, >= 2 survivors)".
  Modal-ban compliance per draw, as 1 - banned share / as correct-and-compliant share:
  association 0.90/0.38 (grid), 0.91/0.86 (shortest path); geometry 0.38/0.18, 0.28/0.22; forking token 0.79/0.41, 0.80/0.80;
  decommitment 0.51/0.18, 0.46/0.38; instruction tuning 0.38/0.13, 0.46/0.46.
- Locus probe: `gen_art_experiment_3/probes.json` is 28 bytes (`{"summary": {}, "cells": {}}`), mtime 18:29;
  `logs/states.out` logs "T1: states (300, 8, 21, 4096) saved" at 18:34:34 and T2 at 18:34:50. `states/` holds 10 npz parts (790 MB).
- `gen_art_experiment_2/results/manipulation_sensitivity.json` (not in the report): with the flagged centroids recomputed,
  Dijkstra -> Floyd-Warshall 25.49, bidirectional Dijkstra 40.91, Bellman-Ford/SPFA 42.18, Dial 58.01
  (committed: bidirectional Dijkstra 42.46, Dial 54.96), so Bellman-Ford/SPFA becomes the third-nearest centroid.
- Geometry geodesic stability: `results/contest.json` reports only point-cloud resampling (`geodesic_share_same_nearest` 0.985); no k or layer sweep.
- `gen_art_experiment_6/results/analysis.json`: forecast_check P5 `semantic_cos_implied` T1 0.493, T2 -0.087;
  T2 semantic seed `modal_share_shift_pp` -67.39, `implied_share_change_pp` +66.30; T1 word seed `probe_shift.astar_greedy` +0.879;
  T2 entropy seed `ratio_ci90` [0.9995, 1.596].
- Instruction tuning steering (`gen_art_experiment_5/runs/samples.jsonl`): T2 `steer:random2` (band, c=0.5) correct programs = Bellman-Ford/SPFA 33 of 33
  (control: Dijkstra 100); `steer:random1_Ronly` Dijkstra 90, Bellman-Ford/SPFA 9, other 1.
- Decommitment (`gen_art_experiment_4/data/samples.jsonl`): T2 `steer:rand1:c=0.25` correct Dijkstra 53, Bellman-Ford/SPFA 26;
  T1 `succession:2` correct BFS 65, unit-Dijkstra 13, DFS 7, A* 3 (16 compliant) at pass 0.88 vs 1.00 baseline.
- Hypothesis-review scores (parent run iter_1..iter_7): 5, 6, 6, 7, 7, 7, 7; final round soundness 3, presentation 3, contribution 3, fidelity 4.
