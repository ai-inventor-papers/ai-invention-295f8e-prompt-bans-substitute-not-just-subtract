# Where the model's algorithm choice lives (iteration 4, plan-subspace experiment)

Qwen3-8B (pinned revision `b968826d…`, thinking off, T = 1.0) writes the same algorithm for most coding tasks
almost every time (full sort for k-th smallest, Dijkstra for weighted shortest path, …). Iteration 3 found that
**random pushes** at the task-specification positions sometimes make it write a *different, correct* algorithm.
This repository asks **which** random pushes do that, and whether a "plan subspace" read from forward passes
explains it.

The plan subspace `P_t` of task t at block l (12–35) is the span of centroid differences `c_X − c_default` of the
task-spec states (S-mean over `[Task: … spec_end)`) under 30 forced "Implement X" paraphrases per algorithm X
(10 forced templates × 3 names). A name-masked twin subspace uses 30 leak-checked *descriptions* of each mechanism.
Tests, each beside its baseline under common random numbers (CRN):

| Claim | What ran | Baseline / control beside it |
|---|---|---|
| **C2a** (primary): the projection share `pi(u) = mean_l ||Q_l^T u||²` ranks which random pushes move the algorithm | 40 fresh, never-run random directions (seeds 9101–9140) × α ∈ {1, 2} × N = 10 on 6 movable tasks; passers topped up to N = 30 and confirmed | 10,000-shuffle permutation null; Haar random-subspace null (1,000 subspaces); structured wrong subspaces (other tasks' `P_t`, within-class PCs); downstream gain; whitened / outlier-free variants; the masked subspace |
| **Decomposition**: is the plan component of confirmed escaping pushes necessary / sufficient? | `u_perp` (P_t component removed), `u_P` (only the P_t component, amplified), CLAMP (realised P_t displacement held at 0), CRN slots k 0–3 | the original push and the twin on the same slots |
| **C2c**: a targeted push along default → runner-up at the predicted half-distance `b_t` | `r` axis at s = 0.25 / 0.5 / 1.0 × D, masked axis, second-runner-up axis, sweep at α 4 / 8 | a random unit direction with the **same** per-position magnitude (paired CRN, McNemar) |
| **C2b**: do knob displacements project on `P_t` in proportion to their recorded effect? | nonce ban, novelty instruction, modal bans, band patch, iteration-3 pushes | displacement norm (pi must beat ‖δ‖) |
| **9-task escape** | 8 directions × α ∈ {1, 2} on T04 T08 T11 T13 T14 R1 R3 R6 and the held-out R2 (ban-free unit) | twin N = 30 |
| **C3b** (descriptive) | push-landing and opening-ladder forecasts of where the iteration-3 bans landed | exp13 ASSOCIATE / PROXIMITY forecasts |
| **Novelty audit**, **geometry** (descriptive) | two blind judges + a third on disagreement + AST nearest known solutions; Isomap / MDS / persistent H1 at blocks 18 and 23 | permutation nulls, planted-circle power check |

Every predictor needs forward passes only and was hash-committed (`predictions/c2_commit.json`,
`commitments.log`) **before the first population sample**.

## Results (headline)

**Bottom line.** The plan subspace is real but random pushes do not act through it. The forced-algorithm centroids
of the task-specification states span a reliable, low-dimensional subspace (split-half principal-angle cosine
0.89–0.97 vs 0.02 for random subspaces), and the iteration-3 bans project strongly onto it. However:

1. **C2a is disconfirmed.** A push direction's projection share on the subspace does not rank which of 40 fresh
   random directions change the algorithm (ρ < 0.2 on all 6 tasks; pooled within-task ρ = 0.03). This is not noise:
   the ranking itself is highly reproducible (template split-half ρ = 0.76–0.90 on the four tasks with many movers).
2. **The plan component is not needed.** Removing the in-subspace part of 20 confirmed escaping pushes leaves their
   effect intact (pooled median R = 1.00). The in-subspace part alone, amplified to the same norm, also escapes for
   9 of 20. This is generic sensitivity to a push of this size, not a plan-specific channel.
3. **C2c is disconfirmed by its committed rule:** at the predicted midpoint, 5 of 6 tasks cannot be told apart from
   a random push of the same magnitude. T10 is the exception, and there the centroid geometry is causally exact.
   Half the distance to the DFS centroid, a tenth of a random push's size, yields 48% correct DFS programs, against
   0% for the matched random push. The empirical 50% crossing (s = 0.59) sits at the predicted midpoint (s = 0.5).
4. **C2b fails** (pooled ρ = 0.27). Knobs that project onto the subspace are not the ones that move the algorithm
   most.
5. **What random pushes do buy.** They yield correct algorithmic diversity on four tasks: T03, T10, T2 and T05,
   with confirmed escapes on up to 73% of directions at α = 2. They always land on the same runner-up as the
   iteration-3 screen did. They never produced a correct novel algorithm (0 of 10,651 correct push programs).

**Engine checks and inputs.** Every GPU unit test passes (`results/unit_tests_gpu.json`): decoding with 20 rows is
row-position independent (identical uniforms in different rows give identical tokens), so the CRN coupling of every
arm is exact; batch-1 prefill is bit-identical on repeat; a TARGET edit with M = 0 reproduces the twin token for
token; the realised displacement along U equals its target within 0.04% at blocks 12–23 (≤ 0.07% over all 3,480
committed prefills); CLAMP leaves ≤ 6.7e-4 of the displacement in `P_t` (criterion 1e-3). The **engine check
reproduces the iteration-3 screen exactly**: 180/180 slots of T03 RAND9002 (α 1), T2 RAND9004 (α 1) and both twins
give the identical program (same sha256) and label (`results/engine_check.json`). All 146 bench files match
`bench/commitment.json`; every bench labeller (13 tasks incl. R2) recovers 100% of its references and reproduces its
gate agreement exactly; the exp8 suite recovers 22/22 references (`results/labeller_recheck.json`). The nine CPU
tests of the analysis code pass (`results/tests_cpu.json`), including power 0.81 for a planted ρ = 0.5 at n = 40, a
uniform null (KS p = 0.15), the 8.6% screen-pass probability of a 5% mover at N = 10, exp13's Hill-1 (2.234) and log
scores (−1.3262 / −1.8417), and a planted circle detected by the persistence test.

**The plan subspace is real and reliable, but small relative to random pushes.** At block 18 the split-half
principal-angle cosine between two 15/15 halves of the paraphrases is 0.89–0.97 on all 15 tasks (random k-dim
subspaces: 0.02–0.03), and every difference vector `c_X − c_def` has split-half cosine ≥ 0.74. Named and masked
(description-only) difference vectors agree only moderately (cos 0.12–1.00 at block 18), so `P_t` carries a lexical
component. The iteration-3 ban's own displacement projects strongly on `P_t` (π = 0.02–0.77; 0.08–0.39 on the six
movable tasks), whereas a random direction has π ≈ k/4096 ≈ 0.001. The committed plausibility ratio κ (expected
in-subspace part of a random push relative to the default→runner-up distance) is 0.10–0.29 on 14 tasks and 0.51 on
T1: a linear plan account predicts that random pushes almost never cross to the runner-up through `P_t`.

**C2a (primary): DISCONFIRMED** (`results/c2a.json`, figs 1–2). The projection share π(u) does not rank which of
40 fresh random plan-site pushes move the algorithm: ρ < 0.2 on all 6 tasks (rule: ρ ≥ 0.4 with p < 0.01 on ≥ 4/6),
and the masked variant fails on all 6. The pooled within-task ρ is 0.03 (task-bootstrap 95% CI [−0.03, 0.09]).
Every ρ_π sits inside its Haar random-subspace null (q95 ≈ 0.25–0.27). Holm-adjusted p = 1.0 for every task.

| Task | dirs with y > 0 | ρ_π (p) | ρ_π,masked (p) | ρ_s (p) | ρ_s,runner-up (p) | ρ_π,real | ρ_π,wrong | ρ_π,within | ρ_gain | Haar q95 | partial ρ_π given gain | κ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| T03 | 34/40 | 0.14 (0.21) | 0.11 (0.26) | −0.22 (0.91) | −0.16 (0.84) | 0.11 | 0.03 | 0.20 | −0.10 | 0.26 | 0.12 | 0.13 |
| T2 | 37/40 | 0.09 (0.29) | −0.05 (0.62) | 0.01 (0.49) | −0.03 (0.57) | 0.15 | −0.30 | −0.05 | −0.04 | 0.25 | 0.08 | 0.20 |
| T05 | 10/40 | 0.08 (0.33) | 0.03 (0.42) | 0.09 (0.29) | 0.21 (0.10) | −0.24 | 0.05 | 0.07 | −0.16 | 0.27 | 0.05 | 0.14 |
| T10 | 36/40 | −0.05 (0.62) | −0.03 (0.57) | 0.32 (0.026) | 0.33 (0.021) | −0.14 | −0.12 | 0.37 | −0.06 | 0.26 | −0.05 | 0.14 |
| T06 | 3/40 (underpowered) | −0.01 (0.52) | −0.04 (0.60) | −0.06 (0.63) | −0.05 (0.62) | −0.02 | −0.17 | −0.11 | −0.15 | 0.25 | −0.00 | 0.21 |
| T1 | 22/40 | −0.06 (0.64) | 0.05 (0.37) | 0.18 (0.13) | 0.00 (0.49) | −0.09 | −0.07 | −0.04 | 0.25 | 0.25 | −0.01 | 0.51 |

y = off-default share over the first 10 samples of a direction, averaged over α 1 and 2; ρ_s is the signed
component along the mean non-default axis, ρ_s,runner-up along default→runner-up (committed secondaries); ρ_π,real
uses the realised displacement; π_wrong (other tasks' subspaces), π_within (within-class PCs) and gain are the
committed controls. Random pushes DO move the algorithm on most directions of T03, T2 and T10 (34–37 of 40 have
y > 0), so the null is not for lack of movers. The only predictor family with some signal is the **signed**
component toward the runner-up on T10 (ρ ≈ 0.33, p ≈ 0.02, unadjusted; also the within-class control, ρ = 0.37),
not the unsigned subspace share the hypothesis named.

**C2b: not supported** (`results/c2b.json`, fig 5). Over 270 knob points on 14 tasks (nonce bans, the novelty
instruction, modal bans, band patches, iteration-3 bans and random pushes), the pooled within-task Spearman of
π(δ_knob) with the recorded off-default share is 0.27 (rule: ≥ 0.5), and its advantage over the displacement norm
(ρ = 0.12) has a paired-bootstrap 95% CI of [−0.02, 0.31] (rule: > 0). Within task it ranges from −0.29 (T08) to
0.84 (T10). The class means show the dissociation: modal bans project strongly onto `P_t` (mean π 0.23, recorded
off-default share 0.40), nonce bans weakly (π 0.07, share 0.00), the novelty instruction in between (π 0.15,
share 0.17), while the iteration-3 random pushes barely project (π 0.015) yet move the algorithm as often as the
novelty instruction (share 0.17). Pushes change the algorithm without entering the plan subspace.

**The null is not noise: which directions move the algorithm is a stable property of the direction**
(exploratory, `results/explore.json` → `y_reliability`). Splitting each direction's first-10 samples by template
(W1/W3/W5 vs W2/W4), the two halves rank the 40 directions alike: ρ = 0.80 (T03), 0.81 (T2), 0.76 (T05), 0.90
(T10), i.e. Spearman–Brown 0.86–0.95 for the full-length y; α = 1 and α = 2 rank them alike too (ρ = 0.61–0.72).
On T06 and T1 the outcome is too sparse to be reliable (0.59 / 0.39 with 3 and 22 movers). So on the four tasks
with many movers there is a reproducible ranking of push directions, with a ceiling near 0.9 for any predictor, and
the plan-subspace share explains none of it.

**Escape: random plan-site pushes buy correct alternative algorithms on four tasks, rarely on two, never on nine**
(`results/escape.json`, fig 7). A (task, direction, α) escapes when its first 10 samples exceed the twin's
off-default share by ≥ 0.20 at ≥ 0.8 × the twin's pass rate and the pooled 30 confirm it (one-sided exact
binomial p < 0.05). Every twin writes the default 100% of the time (T14: 90%).

| Task (default) | E_t α = 1 [95% CI] | E_t α = 2 [95% CI] | push landing (excess-weighted, this run) | iteration-3 screen landing |
|---|---|---|---|---|
| T03 (full sort) | 12/40 = 0.30 [0.18, 0.45] | 25/40 = 0.63 [0.47, 0.76] | quickselect 0.66, size-k heap 0.31, heapify-pop 0.03 | quickselect 0.64, size-k heap 0.35 |
| T10 (union-find) | 15/40 = 0.38 [0.24, 0.53] | 29/40 = 0.73 [0.57, 0.84] | DFS 0.83, BFS 0.17 | DFS 1.00 |
| T2 (Dijkstra) | 7/40 = 0.18 [0.09, 0.32] | 8/40 = 0.20 [0.10, 0.35] | Bellman-Ford/SPFA 0.99 | Bellman-Ford/SPFA 1.00 |
| T05 (hash map) | 0/40 [0, 0.09] | 5/40 = 0.13 [0.05, 0.26] | brute force 1.00 | brute force 1.00 |
| T1 (BFS) | 2/40 = 0.05 [0.01, 0.17] | 5/40 = 0.13 [0.05, 0.26] | DFS 1.00 | DFS 1.00 |
| T06 (hash set) | 0/40 [0, 0.09] | 0/40 [0, 0.09] | — | sort-adjacent 0.79 (1 of 3 screen directions) |
| T04 T08 T11 T13 T14 R1 R3 R6 R2 | 0/8 each | 0/8 each (one T14 screen passer not confirmed) | — | — |

The landing of a push is task-determined, not direction-determined: on every movable task the excess-weighted
landing of 40 fresh directions reproduces the iteration-3 screen's landing (top-1 agrees on all five tasks with a
landing). T06's screen escape (1 of 3 directions) does not replicate in 40 fresh directions, so T06 is not movable
here. The held-out R2 (pushed on the ban-free unit) is not movable: the committed prediction for a future R2 ban is
"no random-push escape". Population programs stay mostly correct (pass rate over all population and top-up
programs: T03 0.98, T05 1.00, T06 0.99, T10 0.97). The path tasks are the exception (T2 0.84, T1 0.79): pushed
Bellman-Ford and DFS programs often fail the hidden tests (T2: 255 of 422 Bellman-Ford programs pass; T1: 55 of 123
DFS programs).

**Decomposition: the plan component is not needed** (`results/decomposition.json`, fig 3). The test covers up to
4 confirmed escaping directions per task (20 in all; T06 has none). They were re-sampled on the same CRN slots
(k 0–3, N = 20) in three forms:
- `u_perp`: the push with its `P_t` component removed;
- `u_P`: only that component, amplified to the push's full magnitude;
- CLAMP: the original push with the *realised* displacement's `P_t` component held at 0 at every edited block.

The effect ratio is R = (share_arm − share_twin) / (share_original − share_twin).

| Task | reading (committed rule) | median R(u_perp) [CI] | median R(u_P) | u_P escapes alone | median R(CLAMP) |
|---|---|---|---|---|---|
| T03 | P_t not needed + sufficient (amplified) | 1.00 [1.00, 1.00] | 0.77 | 4/4 | 1.00 |
| T2 | P_t not needed | 1.00 [0.74, 1.40] | 0.09 | 1/4 | 0.63 |
| T05 | P_t not needed | 0.81 [0.60, 1.25] | 0.70 | 2/4 | 1.04 |
| T10 | P_t not needed | 1.00 [0.90, 1.02] | 1.00 | 2/4 | 1.00 |
| T1 | mixed | 0.78 [0.27, 1.50] | 0.06 | 0/4 | 0.64 |
| pooled (20 directions) | **P_t not needed** | 1.00 [0.88, 1.08] | 0.32 | 9/20 | 1.00 |

On every task with clear escapes, removing a push's projection on the plan subspace leaves its effect intact. The
stronger CLAMP intervention also leaves it intact on T03, T05 and T10; on T2 and T1 it removes about a third of the
effect. So the in-subspace part is not necessary. The in-subspace part alone, scaled to the same norm, also escapes
for 9 of 20 directions, including all four on T03. On the most movable tasks, a push of this size along many
directions, inside or outside `P_t`, flips the algorithm. This is the generic-sensitivity account that the plan named
as the main confound.

**C2c: DISCONFIRMED by the committed rule, with one clean exception (T10)** (`results/c2c.json`, fig 4). A targeted
push along `r_l` (default → runner-up centroid) moves the S-mean state by s × D_l; s = 0.5 is the predicted Voronoi
midpoint b_t. In ban units this is a small push (ν(0.5) = 0.05–0.20) compared with the random pushes (α = 1–2;
median α of confirmed escapes = 2). The random control has the SAME per-position magnitude at s = 0.5.

| Task (runner-up) | off-default share at s = 0.25 / 0.5 / 1.0 | random, same magnitude (s = 0.5) | CRN flips targeted-only / random-only; Δshare [95% CI] | 50% crossing s [CI] | masked axis (s = 0.5) | sweep α = 4 / 8 (pass) |
|---|---|---|---|---|---|---|
| T10 (DFS) | 0.07 / **0.48** / 0.93 | 0.00 | 24 / 0; +0.48 [0.34, 0.62] | **0.59 [0.50, 0.70]** | 0.63 | 1.00 (0.97) / 0.40 (0.00) |
| T03 (quickselect) | 0.03 / 0.08 / 0.73 | 0.02 | 3 / 0; +0.06 [0.00, 0.12] | 0.85 [0.76, 0.95] | 0.43 | 1.00 (1.00) / 1.00 (0.00) |
| T2 (Bellman-Ford/SPFA) | 0.00 / 0.02 / 0.07 | 0.00 | 1 / 0; +0.02 [0.00, 0.06] | 1.69 [1.16, 6.7] (extrapolated) | 0.03 | 0.63 (0.00) / 0.00 (0.00) |
| T05 (brute force) | 0 / 0 / 0 | 0 | 0 / 0 | — | 0 | 1.00 (0.77) / 0.08 (0.00) |
| T06 (sort-adjacent) | 0 / 0 / 0 | 0 | 0 / 0 | — | 0 | 0.03 (0.00) / 0.20 (0.00) |
| T1 (DFS) | 0.00 / 0.04 / 0.00 | 0.00 | 2 / 0; +0.04 [0.00, 0.10] | not reached (extrapolated 5.7) | 0.03 | 1.00 (0.20) / 0.53 (0.00) |

Committed reading: Hill-1 (correct only) ≥ 1.8 within 5 pass points at s = 0.5 holds on 1 of 6 tasks (T10: Hill 2.0,
pass 1.00); the targeted-minus-random difference has a CI including 0 on 5 of 6 tasks → DISCONFIRM. Read per task,
the picture is graded, not null. On T10 the centroid geometry predicts the dose almost exactly: half the distance to
the DFS centroid (0.15 ban units, a tenth of a random push) turns 48% of programs into correct DFS, the matched random
push turns none, and the empirical crossing (0.59) sits at the predicted midpoint. On T03 the crossing is at 0.85 of
the distance, and the name-free (masked) axis is stronger than the named one at s = 0.5 (0.43 vs 0.08). On T2, T05,
T06 and T1 the midpoint dose does nothing; along the same axis a 4-ban-unit push gives 100% brute force on T05 (77%
correct), 100% DFS on T1 (20% correct) and 63% Bellman-Ford on T2 (all failing), and 8 ban units break programs
everywhere. The second-runner-up axis lands on its own target only on T03 (size-k heap, 7%); on T10 it lands on DFS
(23%).

**C3b: push landings forecast where bans land (descriptive)** (`results/c3b.json`, fig 8). The scored set is the 5
gated iteration-3 bench bans (already seen, so this is descriptive). The score is the mean ln p of the realised
non-banned attempts, using exp13's frozen smoothing.

| Forecast | events defined | mean log score (exp13 ban) | exp16 full-ban replication | top-1 hits |
|---|---|---|---|---|
| PUSH: this run's confirmed-escape landing | 3 (T03, T05, T10) | **−0.76** | −0.71 | 2/3 |
| PUSH_SCREEN: iteration-3 screen landing | 4 | −1.48 | −1.37 | 2/4 |
| LADDER_OPEN: opening ladder (teacher-forced openings under the twins) | 5 | −2.39 | −2.24 | 2/5 |
| ASSOCIATE (exp13) | 5 | −3.46 | −3.35 | 1/5 |
| PROXIMITY (exp13) | 5 | −3.21 | −3.20 | 1/5 |

Where pushes escape, their landing is the best forecast of where the ban lands: quickselect on T03 and brute force
on T05. T10 is the departure: the ban lands on BFS (83%) while pushes land on DFS. The committed departure check
reports exp16's F_direct, 0.74, which is ≥ 0.25 but pooled over its route tasks, not specific to T10. Across 14
tasks, the tasks random pushes can move are the tasks whose bans are obeyed. Spearman(E_t, exp13 ban avoidance) is
0.86: the five movable tasks have avoidance 0.86–1.00, the nine immovable ones 0.00–0.79. The opening margin
lp(default) − max lp(survivor) does not track avoidance (ρ = 0.19). The held-out R2 is not movable (0/16 cells), so
the recorded prediction for a future R2 ban is "no push escape".

**Novelty audit: no correct novel algorithm** (`results/novelty.json`). Of 10,651 correct programs from push arms,
4 carry the label `other`. Two blind judges (gemini-2.5-flash, gpt-4.1-mini) classified each, and deepseek-chat
resolved their two disagreements:
- 1 catalogue variant (a T05 hash map);
- 1 labeller miss (a T2 Dijkstra);
- 2 degenerate programs. A manual pass confirms these: a plain linear scan for R6 and a random guess-and-count loop
  for T06.

The AST nearest known solutions have Jaccard ≤ 0.22. So there are 0 NOVEL verdicts (rule-of-three 95% bound
3/10,651 = 0.03%). The pushes recombine catalogue algorithms; they do not invent new ones.

**Exploratory: the sign of the push, not its share in `P_t`, carries what predictive signal there is**
(`results/explore.json`, fig 9; written after the population was sampled, outside the committed rules). Using the
prefill-only realised displacements of all 40 directions, the Spearman correlation with y of the displacement's
**signed progress toward the runner-up centroid** (`<δ_l, r_l> / D_l`) is positive on most tasks and blocks: up to
ρ = 0.57 (T10, block 31), 0.47 (T05, block 17), 0.30 (T2, block 16), 0.26 (T03, block 25) and 0.48 (T1, block 35),
whereas the unsigned projection share of the same displacement hovers around 0 (block 18: −0.35 to 0.21) and turns
negative at blocks 24–30 on several tasks. These are 24 blocks × 6 tasks of uncorrected, descriptive correlations;
they suggest that a push helps when it happens to point toward the runner-up, a directional (signed) effect that the
committed unsigned predictor π cannot see.

**Geometry (descriptive)** (`results/geometry.json`, fig 6). At blocks 18 and 23, Isomap / metric MDS of the named
and masked forced-prompt states (PCA-50) separate the algorithms into tight clusters. Metric MDS on the geodesic distances has stress-1 0.06–0.25
(trustworthiness 0.96–0.99); Isomap has trustworthiness 0.84–0.98 but high stress-1 (0.58–0.83), because the kNN
graph is clustered. Persistent H1
exceeds its coordinate-permutation null (200 draws) only on T2 (block 18) and T05 (blocks 18 and 23); a planted
circle at matched n and noise is detected in every case, so the test has power. Out of sample, the population's
pushed states (twin + realised displacement) stay near the twins (T03) or spread partly toward the runner-up
clusters (T10), but pushes that changed the algorithm and pushes that did not are intermixed in the embedding
(fig 6, lower-left panels): the 2-D geometry of the forced-prompt states does not separate escaping from
non-escaping pushes.

## Committed predictions vs outcomes

| Committed rule (`predictions/c2_commit.json`) | Outcome |
|---|---|
| C2a PASS: ρ(π, y) ≥ 0.4 with p < 0.01 on ≥ 4/6 tasks, and the same for π_masked on ≥ 3/6 | **No**: 0/6 and 0/6 |
| C2a DISCONFIRM: ρ < 0.2 on most tasks | **Yes**: 6/6 (pooled within-task ρ = 0.03 [−0.03, 0.09]) |
| Decomposition: "P_t not needed" if median R(u_perp) ≥ 0.7 with lower bound ≥ 0.4 | **Yes** on T03, T2, T05, T10 and pooled (1.00 [0.88, 1.08]); T1 mixed; T06 not evaluable |
| Decomposition: "sufficient (amplified)" if u_P passes the escape rule at N = 20 | T03 (4/4); 9/20 directions overall |
| C2c PASS: correct-only Hill-1 ≥ 1.8 within 5 pass points at b_t on ≥ 4/6, with ν(0.5) ≤ 0.5 × median α | **No**: 1/6 (T10; ν = 0.15 ≤ 1.0) |
| C2c DISCONFIRM: targeted-minus-random CI includes 0 on ≥ 4/6 | **Yes**: 5/6 (all but T10) |
| C2b: pooled within-task ρ(π(δ), share) ≥ 0.5 and π beats ‖δ‖ | **No**: ρ = 0.27; Δρ 95% CI [−0.02, 0.31] |
| Frozen movable set {T03, T05, T06, T10, T1, T2} (E_t > 0 at α ≤ 2) | 5 of 6: **T06 is not movable** here (0/80 cells) |
| C3b departure rule: F_direct ≥ 0.25 where the ban's top-1 differs from the push top-1 | T10: exp16 pooled F_direct = 0.74 (pooled, not per task) |
| Novelty: "no correct novel algorithm" only at 0 NOVEL verdicts | 0 NOVEL among 10,651 correct push programs |

**Cost and scale.** 13,500 programs were sampled in 675 batches of 20 over 2.51 GPU-hours. 13,500 label rows were
written. The blind judge decided 752 of them; 4 are disputed (judge unavailable) and 97 invalid (no code), and
both are excluded from shares. 3,480 committed realised-displacement prefills and 4,144 prompt states were computed. The
OpenRouter spend was USD 0.20: masked descriptions 0.034, path judge 0.156, bench judge 0.011, novelty judges 0.003
(`results/costs.json`).

**Audit** (`results/rederive.json`). An independent recomputation from the raw rows reproduces every headline with
0 mismatches. This covers ρ_π per task, confirmed-escape counts per task, and the C2c shares. All three placebos
fail as they should:
- with π shuffled across directions, the mean ρ is within ±0.01 of 0;
- with another task's subspace, ρ is −0.11 to 0.02;
- with labels shuffled between arms within (task, template), confirmed escapes fall from 37 to 1 (T03), from 44
  to 2 (T10) and to 0 elsewhere.

A second, separate script (`audit/rederive_extra.py`, plain Python and numpy, `results/rederive_extra.json`)
re-derives the remaining headlines from the raw rows, each with a placebo that must fail. It reproduces:
- the decomposition medians: pooled R(u_perp) 1.00, R(u_P) 0.32, R(CLAMP) 1.00; swapping original and twin labels
  within slots collapses the escape excess from 0.76 to 0.08;
- the T10 contrast: 0.48 vs 0.00, 24 / 0 flips, exact McNemar p = 1.2e-7; with targeted and random labels swapped
  at random, p < 0.05 in 2.4% of draws;
- the pooled within-task ρ = 0.03 (−0.004 with π shuffled);
- the template split-half reliabilities (0.80 / 0.81 / 0.76 / 0.90; shuffled halves give −0.06 to 0.16);
- the novelty counts (10,651 correct push programs, 4 labelled `other`).

C2b, C3b, the C2c crossing doses, κ, the subspace reliabilities and the geometry metrics were not re-derived
independently.

The commitment chain (56 entries) has no breaks, and the latest entry of every committed file matches the file on
disk. Commit #1 (04:27:38Z) precedes the first population sample (04:30:00Z).

## Deviations from the plan (all in `results/deviations.json`)

1. **FP8 instead of bf16 (F-precision).** The machine has a 16 GB RTX 2000 Ada; the plan's own table prescribes the
   exp17 FP8 W8A8 path with B = 20 for this GPU. Benefit: the numerics are those of the iteration-3 screen, which the
   engine check reproduced slot for slot.
2. **max_new = 1024 for T1/T2** (plan: 1536 for bf16 path rows), as in the exp17 screen, to keep its engine exactly.
3. **Ban-unit scale.** The plan's unit for bench tasks (exp13 bf16 norms) is 9–16% smaller than exp17's FP8 norms
   on T03/T04/T05/T06, so the bench population pushes are ~10–16% weaker than screen pushes of the same α (the engine
   check used exp17's norms to replicate the screen).
4. **T1/T2 prompts.** Named prompts use the bench forced templates with exp7's display names plus two hand-written
   aliases (exp7 has no alias lists); masked prompts are built like the bench ones because exp7's "desc" prompts
   contain the algorithm name and fail the alias-leak check.
5. **Commit timing of analysis code.** Commit #1 (before the first population sample) holds every predictor value,
   all reading rules verbatim, the screen hash and the primary analysis code (`analysis/common.py`, `c2a.py`, the CPU
   tests). `decomp.py` and `c2c.py` were chained before their arms were sampled (addendum 1); the C2b, C3b, geometry,
   novelty and reporting code before they were run (addenda 2–4); the decomposition list was committed before its
   arms were sampled. Corrections of committed files are new chain entries. Writing all of it first would have
   idled the GPU for about an hour of a 6-hour budget.
6. **C2b inputs.** ITER1 exp6 (T1/T2 seeds and their outcomes) is no longer on disk and exp13's rand1–3 directions
   are not on record; C2b uses exp13's nonce / novelty / ban / band-patch rows and exp17's bans and pushes.
7. **Batch packing.** Arms of one (task, template) share 20-row batches; leftover rows are padded with extra twin
   slots (k ≥ 10, reported apart). Decode is row-position independent at B = 20 (U1b), so CRN coupling is unchanged.
8. **Undefined plan abbreviations.** "H5, P15 and P20 on the randomisation hull" are not defined in the inputs; the
   best dose on the hull {twin, doses} by correct-only Hill within 5 pass points is reported instead (descriptive).
9. **C3b departure rule** uses exp16's F_direct pooled over its 5 route tasks (no per-task value is published).
10. **Opening ladder** reconstructs the code fence before the forced programs' extracted code (flagged per mode).
11. **Phrasing clusters** (AST 4-gram Jaccard) are computed for arms with ≤ 120 correct programs (quadratic cost).

## Conventions

- **Block l** = decoder block l (0-based); its output is HF `hidden_states[l+1]`. Pushes edit blocks 12–23 at the
  task-spec positions S during the prompt prefill only; realised displacements are logged at blocks 12–35.
- **Push (TARGET edit)**: `h_S ← h_S + (M_l − (h_S − h_twin)·U_l) U_l`: the displacement from the clean neutral twin
  along `U_l` is exactly `M_l[p]` at every edited block (realised error ≤ 0.07%). Random pushes use
  `U_l = u`, `M = α·n[l,p]` with `n` the ban unit (per-position norm of the iteration-3 ban displacement; exp13
  bf16 norms for bench tasks, exp17 FP8 norms for T1/T2, a ban-free unit `r_l·‖h_twin‖` for R2).
- **CRN slot** = (task, template W1–W5, k); uniforms `u_stream(task, template, k)` are shared by every arm and every
  batch has exactly 20 rows of one (task, template), so arms are pairwise coupled (exact flips).
- **Shares** are catalogue-only: off-default share = #(catalogue label ≠ default) / #valid; `other`, `invalid` and
  `disputed` are never off-default, and `invalid` / `disputed` leave the denominator. Pass = hidden tests passed.
- Labels are mechanism-level (runtime tracer first, AST second, blind LLM judge only on disagreement).

## Layout

| Path | What it holds |
|---|---|
| `method.py` | orchestrator: `s0`, `prompts`, `gpu1`, `commit`, `label`, `gpu2`, `analyze`, `outputs` |
| `finalize.sh` | the post-sampling chain (GPU phase 3 → analyses → figures → audit → `method_out.json` → schema check) |
| `src/cfg4.py` | constants (tasks, defaults, seeds, doses, slots, paths) on top of `src_base/cfg.py` |
| `src/s0_setup.py`, `src/screen.py`, `src/recheck4.py` | S0: input copies + sha256 + bench verification; the screen file (commit entry #0); labeller re-check |
| `src/describe.py`, `src/prompts4.py` | masked descriptions (OpenRouter, alias-leak checked) and all 4,144 prompts |
| `src/engine4.py`, `src/hooks4.py`, `src/ctx4.py` | CRN sampler with the fence stop; TARGET / CLAMP edits; per-task context with realised-displacement logging |
| `src/gpu_phase1.py` | GPU unit tests, engine check, states, units, realised-displacement prefills |
| `src/subspace.py`, `src/make_commit.py`, `src/commit4.py` | S3 subspace + predictors; S4 commit; the hash chain |
| `src/sampling4.py`, `src/gpu_phase2.py`, `src/label4.py` | arm registry and 20-row batch packing; sampling stages A–H; the label worker |
| `src/gpu_phase3.py` | opening-ladder log-probabilities (C3b) and C2c displacement vectors (geometry) |
| `src/npz_parts.py` | row-wise part storage (< 45 MiB per file) and the loader used for every `states/` array file |
| `src/costs.py`, `src/deviations.py`, `src/extract_known.py` | spend and GPU-time summary; the deviations record; known-solution sets from the declared dependency |
| `src_base/` | the untouched iteration-3 exp17 code base (FP8 engine, labeller wrappers, utilities) |
| `analysis/` | `common.py` (statistics), `c2a.py`, `decomp.py`, `c2c.py`, `c2b.py`, `c3b.py`, `geometry.py`, `novelty.py`, `explore.py` (exploratory, uncommitted), `run_all.py`, `figures.py`, `outputs.py`, `engine_check.py`, `tests_cpu.py`, `summarise.py` |
| `audit/rederive.py`, `audit/rederive_extra.py` | two independent recomputations of the headlines from raw rows, with placebos and the hash-chain check |
| `reproducibility.md` | exact environment, commands, seeds, runtimes and expected numbers |
| `inputs/` | read-only copies of every iteration-2/3 input (bench, exp8 suite, exp13/16/17/18 files, exp7 prompts); sha256 in `results/input_hashes.json` |
| `inputs/dep_art_j3Rm/` | from the declared dependency `art_j3Rm_lr2nzR6`: its mini/preview files and `known_subset.jsonl`, 406 known solutions (mercury human solutions and LeetCode references selected by `metadata_bench_task`, read in place from its `full_data_out.json`) used with exp18's 472-solution index by the novelty audit |
| `prompts/` | `prompts4.jsonl` (4,144 prompts with ids and positions), `descriptions.json`, `prompts4_report.json` |
| `predictions/` | `c2_commit.json` (commit #1: predictors, rules, reliability, doses) and `decomp_list.json` (addendum) |
| `commitments.log` | sha256 hash chain of every committed file, in order |
| `data/samples_raw.jsonl`, `data/labels.jsonl` | every generated program (arm, slot, token ids, text) and its label row |
| `data/realised_disp.jsonl` | realised displacement records of every edited prefill used in sampling |
| `data/judge_cache*.jsonl`, `data/novelty_cache.jsonl` | blind-judge caches (labelling and novelty audit) |
| `directions/` | the random unit directions (`rand_<seed>.npy`) |
| `states/` | fp16 prompt states (`states_<task>`), realised displacements (`disp_<task>`, `disp_c2c_<task>`) and subspace files, about 3 GB. The large arrays are stored as row-wise parts `<name>.partNNN.npz` (each < 45 MiB); `src/npz_parts.py` loads either form. Kept on the run volume and excluded from the published repository by `upload_ignore_regexes`. |
| `results/` | every analysis JSON (`c2a`, `escape`, `decomposition`, `c2c`, `c2b`, `c3b`, `geometry`, `novelty`, `arms`, `engine_check`, `unit_tests_gpu`, `tests_cpu`, `labeller_recheck`, `units`, `screen`, `subspace_report`, `deviations`, `costs`, `rederive`, `summary.txt`, …) |
| `figures/` | fig1–fig9 (PNG + PDF; fig6 is one composite per movable task) |
| `logs/` | run logs of every stage |
| `method_out.json` | exp_gen_sol_out output (+ `mini_` / `preview_` variants) |

## How to run

```bash
uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml
.venv/bin/python method.py s0          # inputs, screen (commit entry #0), labeller re-check (CPU)
.venv/bin/python method.py prompts     # masked descriptions (OpenRouter) + prompts
.venv/bin/python method.py gpu1        # GPU tests, engine check, states, units, realised displacements
.venv/bin/python method.py commit      # CPU tests, plan subspace + predictors, commit #1
.venv/bin/python method.py label &     # label worker, concurrent with sampling
.venv/bin/python method.py gpu2 --deadline-min 165   # sampling stages A-H
./finalize.sh                          # GPU phase 3, analyses, figures, audit, method_out.json
```

The machine used: one 16 GB RTX 2000 Ada, 5 CPU cores (cgroup), 28 GB RAM. The OpenRouter judges need
`OPENROUTER_BASE_URL` and `OPENROUTER_API_KEY`. The model is read from the Hugging Face cache named by
`HF_HUB_CACHE`. Set `OMP_NUM_THREADS` (≤ the CPU quota) for the CPU analyses; unbounded BLAS threads oversubscribe
a container whose host has 48 cores.

## Restoring removed files

| Removed path | Restore with |
|---|---|
| `.venv/` | `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml` |
| `__pycache__/` directories | regenerated automatically by Python (`python -m compileall src src_base analysis`) |
| Qwen3-8B (shared cache, not in this folder) | `huggingface-cli download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218` |

`states/` is kept on the run's storage volume (not in the published repository; its large arrays are split into
< 45 MiB parts, see `src/npz_parts.py`). It can be regenerated with
`method.py gpu1 states units realised` (about 25 min on the GPU above). Batch-1 FP8 prefills are bit-identical on
repeat, so `src/subspace.py` then recomputes the subspace files; their committed sha256 are in `commitments.log` for
comparison (bit identity of the SVD also needs the same BLAS thread count).
