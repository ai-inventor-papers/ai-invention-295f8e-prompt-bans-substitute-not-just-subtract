## Results at a glance (Qwen3-8B, T=1.0, thinking off)

Each item below gives the file to check.

**1. The default is a total collapse.** The baselines (N=200 per task, 10 paraphrases × 20) give **T1: 200/200 BFS**
(pass rate 0.99) and **T2: 200/200 Dijkstra** (pass rate 1.00), with Hill number 1.00 on both tasks. Mentioning the
modal algorithm (`mention:X`, N=50) leaves it at 50/50. The model *can* write the other modes when asked: on T1 94%
of forced prompts are implemented as asked, on T2 74% (bidirectional Dijkstra and Dial are flagged below 50%).
Correctness of the non-default modes is low, though: forced DFS passes 30% of the time, IDDFS 0%, bidirectional BFS 23%
(`results/phaseA_summary.json`).

**2. Bans mostly fail, and what does move goes to the geodesic neighbours of the banned mode.**
* `ban:bfs` (N=100): 62 BFS, 29 DFS, 9 unit-Dijkstra. Compliance is **0.18**, so this is a pre-declared ban failure
  and the succession stopped. Compliance depends heavily on wording: 4 of the 10 paraphrases give 10/10 BFS.
* `ban:dijkstra` (N=100): 72 Dijkstra, 27 Bellman-Ford/SPFA, 1 other. Compliance is **0.22**, again a ban failure.
  Several programs say "since the user said not to use Dijkstra's algorithm, this is a workaround" and then
  implement Dijkstra.
* Exploratory step-2 bans (N=50; forecasts committed beforehand). `ban:bfs+dfs` gives 19 unit-Dijkstra and 29 BFS.
  `ban:bfs+dijkstra_unit` gives 17 DFS and 31 BFS. `ban:dijkstra+bellman_ford_spfa` gives 37 Dijkstra, 12 BF/SPFA and
  0 compliant samples.
* On the geodesic map (`figures/ban_shift_on_manifold_t1.png`), the mass that leaves BFS lands only on the two
  centroids **adjacent to BFS (DFS, unit-Dijkstra)**. It never lands on the far side (A*, IDDFS, bidirectional BFS),
  and banning the next neighbour pushes it one more step along the map. In the original request's words, the
  implemented count moves **to the edge of the banned region**, not to the opposite side.
* Ban versus baseline trade-off (BUY row, `results/buy.json`). Hill_cc rises 1.00→2.03 (T1) and 1.00→1.72 (T2), while
  the pass rate falls 0.99→0.76 and 1.00→0.94.

**3. Forecast contest (`results/contest.json`; forecasts hash-committed in `predictions/commit_log.jsonl` before any
ban or removal sample; every event's first sample is after the commit).** The primary events are ban:bfs (no clear
realised mode: compliant DFS 10 vs unit-Dijkstra 8) and ban:dijkstra (realised BF/SPFA). No predictor scored a top-1
hit on a primary event. Mean raw log score on primary events: geodesic −1.43, decoder −1.44, uniform/frequency
(tied, because every survivor has 0 baseline count) −1.56, association −2.59. Over all 5 events, including the 3
exploratory ones: geodesic 1/5 hits (mean log score −1.83), association 1/5 (−2.81), decoder 0/5 (−2.46),
uniform −1.97. The model's own stated ranking of "the most standard alternative" (association: A* for BFS, Dial
for Dijkstra) is the **worst** predictor of where a ban actually sends it, worse than uniform. The geometry of
the read-position states is the best, but only barely beats uniform. With 2 to 5 events, this is descriptive only.

**4. Read-position geometry (`results/gate.json`, `results/manifold.json`, `figures/manifold_t{1,2}.png`).**
* Probes at R, leave-one-frame-out, against 20 shuffled-label refits. Named accuracy is about 0.99 at every layer
  (the name is in context). Named→name-masked transfer peaks at **L27 on T1 (0.67 vs null p95 0.22)** and **L24 on
  T2 (0.54 vs 0.31)**.
* The baseline decoder (the named probe applied to the baseline prompts' h_R) passes on T2 (JS 0.011 vs null p5
  0.030; it predicts 98% Dijkstra). It **fails on T1**: the baseline state decodes as DFS 0.60 / unit-Dijkstra 0.27 /
  BFS 0.12, so the T1 R gate is flagged "R gate failed" and its geometry is descriptive.
* Manifold: kNN graphs are connected without MST edges. MDS stress-1 is 0.22 on both tasks. TwoNN intrinsic
  dimension is **4.2 (T1) and 5.2 (T2), against about 11.9 / 11.6 for column-shuffled nulls**. Geodesic and Euclidean
  distances have Spearman 0.87 / 0.90. On T1, BFS's geodesic neighbours are DFS (41) and unit-Dijkstra (58); A*,
  IDDFS and bidirectional BFS are 71–95 away.

**5. C3 shift decomposition (`results/c3_decomposition.json`, `figures/c3_shares_t{1,2}.png`).** At l* the
ban−mention and ban−list-all shifts at R are 80–97% residual: they are not explained by the renounce direction, the
associate or the typical survivor. The u_ren share never exceeds the split-half paraphrase null. Every X is
**inconclusive** under the pre-declared rule. Lexical cosines with the name's input embeddings and its unembedding
row are about 0 (|cos| < 0.04).

**6. C2 activation removal (`results/c2_removal.json`, `figures/removal_outcomes.png`).** Neither direction check
reached 0.9: held-out d_X AUC at R was 0.89 (T1) and 0.79 (T2), and the best generated-position AUC was 0.66 / 0.76.
So the pre-declared **R-plus-prompt** variant ran: affine ablation of the prompt suffix including R, over a
5-layer (T1) or 7-layer (T2) band. At α = 0.5, 1 and the pre-declared escalation 2.0 it moved **0/50 samples on both
tasks** with the pass rate intact. Under common random numbers, 78–90% of the outputs are byte-identical to their
α=0 twin, the same as the random-direction controls with identical edit norms (80–96%). Verdict: **"untestable
(removal unsuccessful at the tested coefficients)"**.
**Exploratory (post hoc) full variant** (`full_*` arms), which also edits every generated position: at α=2 it is
still 25/25 BFS (T1, pass 19/25) and 25/25 Dijkstra (T2). At α=4 the d_X edit destroys generation (25/25 no code on
both tasks). The random direction at α=4 keeps 18/25 BFS on T1 with 0 passing, and gives 20/25 no code on T2. The
removal never reroutes the choice: it either does nothing or breaks the model. This matches the field warning that
steering can be "indistinguishable from random perturbation".

**7. Labels are trustworthy.** Labeller gate (`results/labeller_gate.json`): runtime and AST agree on 100% of
references. κ(runtime, AST) is 0.90 / 0.94 and runtime vs adjudicated is 0.96 / 0.92 on the gold sets. Two judge
models agreed on 100% / 96% of gold items. Total OpenRouter spend for this artifact: ≈ $0.09.

**Scope.** One model (Qwen3-8B), two tasks, T=1.0, thinking off. There are 2 primary ban events, 3 exploratory ones
and 2 removal events, so every number above is descriptive (Wilson intervals in the JSON files, no p-values). Full
deviations from the plan are in `results/deviations.json`, mirrored in `method_out.json` → `metadata.deviations`.
