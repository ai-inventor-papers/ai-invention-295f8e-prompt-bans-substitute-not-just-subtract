# Checking for a hidden algorithm switch (iteration 8): one DAS protocol, seven controls, two model families

**Question (claim K2).** When a code model picks an algorithm (BFS vs DFS vs union-find for connected components;
BFS vs DFS for a grid path), is there a **low-rank causal variable** for that choice inside the model, a linear
subspace that *is* the algorithm decision? Or is there only a **steering handle**, a direction that changes the output
without being the model's own variable?

Every site in this artifact runs **one distributed-alignment-search (DAS) protocol**, declared and hash-committed before
any GPU use (`predictions/commit0.json`, `commitments.log`):

- **map class:** linear orthonormal `R` (d_model x 8, nested ranks 1/2/4/8);
- **interchange:** `h <- h + R(Rᵀh_src − Rᵀh_base)`;
- **objective:** bounded, CDAS-style: KL from the source's own class distribution to the edited base's;
- **readout:** the class margin `log P(class_src) − log P(class_base)` at the decision position `d`.

The protocol is applied at two sites in two families:

| unit | model | decision token (canonical opening prefilled) | classes |
|---|---|---|---|
| T10 connected components | Qwen3-8B (bf16, thinking off) | response token 11 after `def solve(n, edges):` + indent + ` def` | BFS / DFS / union-find (3) |
| GRID shortest path (T1) | gemma-3-4b-it (bf16) | response index 32 after the 32-token opening c* | BFS / DFS (2; A* and IDDFS failed adherence) |
| T10 task band | Qwen3-8B | blocks 12-23 x all 145 task-spec positions, one shared R | same 3 classes |

Seven controls were committed with thresholds before any fit:

| control | what it tests | pass threshold |
|---|---|---|
| c1 | 50 random subspaces per rank | median recovery <= 0.05 |
| c2 | label-control refits (derangements; 2-class: balanced shuffles) | <= 0.10 of the true fit |
| c3 | randomly initialised network, same map class and budget | <= 0.25 of trained |
| c4 | reverse interchange | >= 0.5 of the full-state reverse |
| c5 | retention after projecting R onto the top-64 natural principal components | >= 0.5 |
| c6 | natural-variance share | above the random 95th percentile |
| c7 | seed stability (principal angles) | median first cosine >= 0.5 |

Teacher-forced (TF) results are scored on held-out pairs, where a pair needs a held-out family AND a held-out noun.
Generation results are scored by hidden tests on common-random-number (CRN) slots, so every arm of a slot shares one
random stream.

## Results

**Bottom line.** **K2 is disconfirmed.** In both families the committed protocol finds a strong, low-rank **steering
handle** at the decision token: a rank-4 linear edit that rewrites the algorithm the model writes. None of these
handles is a **certified causal variable**, for three reasons:

- **Specificity.** Maps fitted with permuted or shuffled labels (c2) still move held-out pairs toward the TRUE class
  by 11-87% of the true map's effect; the limit is 10%. Maps fitted on a randomly initialised copy of the network (c3)
  reach 41-69% of the trained effect; the limit is 25%.
- **Location.** The handle lives where the full-state exchange barely acts. DAS moves the margin 3-8 times more than
  exchanging the whole state, so the OFF-MANIFOLD flag is raised at both decision sites.
- **Natural variation.** Most of the effect is lost when the map is restricted to the directions in which the
  model's natural states vary (c5).

The task band of Qwen3-8B is the closest to a variable: its random-init control passes. It still fails c2, and in
generation it routes DFS sources to BFS.

A post-hoc rerun at T10 block 24, where the full state carries the class, clears the off-manifold controls (c4, c5,
c6, c7) but still fails c2 and c3. So the specificity failure is not an artifact of the rule-chosen block. Random
pushes from iteration 4 do not act through any fitted subspace: clamping it removes none of their escapes.

**For the run's question (can we make the model write a different algorithm, and is that a 'switch' inside it?).**

- **Steering works.** A rank-4 edit at one token is enough to move the algorithm Qwen3-8B writes: 29 of 30 correct
  DFS programs where it otherwise writes union-find. The same holds for gemma-3-4b-it: 22 of 30 correct BFS programs,
  against 6 of 30 unedited.
- **It is not a switch.** The edit does not isolate the model's own variable. It works about as well when fitted to
  wrong labels or to an untrained network, and pushing toward BFS in Qwen yields BFS programs that mostly fail the
  tests.
- **Random pushes go elsewhere.** The random pushes that also change the algorithm do not pass through these
  subspaces.
- **No new algorithms.** No edit, push or clamp produced a novel algorithm: 0 'other' among 1,857 correct programs.

| unit-site | TF recovery at k* (95% CI) | V0 (TF / generation / pass ratio / DAS > RAND) | controls passed | controls failed | verdict |
|---|---|---|---|---|---|
| T10 decision (Qwen3-8B, L* = 22, k* = 4) | **8.43** (5.94-11.30), OFF-MANIFOLD | yes / yes / **no (0.72)** / yes | c1, c6, c7 | **c2, c3**, c4, c5 | **NO HANDLE** by the pooled rule (DFS alone: V0 passes) |
| T10 band (Qwen3-8B, blocks 12-23, k* = 2) | 0.82 (0.48-1.16) | yes / yes (0.72) / yes (0.82) / yes | c1, c3, c4, c6 | **c2**, c5, c7 | **SUFFICIENT HANDLE** |
| GRID decision (gemma-3-4b-it, L* = 16, k* = 4) | **3.07** (2.85-3.41), OFF-MANIFOLD | yes / yes / yes (0.81) / yes | c1, c4, c7 | **c2, c3**, c5, c6 | **SUFFICIENT HANDLE** |

K2 rule (commit #0): confirmed iff both decision sites are CERTIFIED; disconfirmed iff a decision site fails c2 or c3
in either family. Both decision sites fail both, so the status is **DISCONFIRMED**.

p_K2 = max over sites of max(p_c2, p_c3) = **0.037**, from one-sided pair-level tests with a two-way cluster
bootstrap. It says the true and trained fits do beat their controls, but only by margins far below the committed
thresholds (c2 <= 0.10, c3 <= 0.25 of the effect).

The committed prediction ("both decision sites certified; the band passes V0 but fails c4, c5 and the clamp") was
wrong on the decision sites and wrong on band c4.

### 1. Where the decision is computed (scan, `figures/F1_scan_profile`)

- **Early blocks.** Exchanging the full block-L state at d does almost nothing up to block 14 in both models (under
  0.5 nats). The choice is not yet written into the decision position there.
- **The committed scan rule picks the first blocks where the full state starts to carry the class.**
  - Qwen: L* = 22, full-state mean Delta 1.5 nats.
  - Gemma: L* = 16, 2.7 nats.
  - A rank-1 subspace there moves the margin 7.9x (Qwen) and 2.5x (Gemma) as much as the full state. That is why the
    rule, argmax of normalised recovery, lands on them.
- **Later blocks.** From block 24 (Qwen) and block 22 (Gemma) on, the full-state exchange carries 15-25 and 7-9 nats.
  There rank-1 DAS recovers 0.6-0.9 (Qwen) and 1.2-1.4 (Gemma) of it.
- **Iteration 7 comparison.** Iteration 7's Gemma L* = 17 sat on this same weak-ceiling edge. L* is rule-chosen and is
  kept. A post-hoc block-24 fit for Qwen is reported separately (section 6).

### 2. Decision sites: a strong handle, not a variable

**Teacher forcing, held-out families and nouns (`figures/F2_recovery_by_rank`, `results/summary.md`).**

- **T10.**
  - Recovery by rank 7.67 / 8.12 / 8.43 / 9.26 (ranks 1 / 2 / 4 / 8). A rank-1-only fit gives 7.69.
  - Per source class at k*: BFS 15.4, DFS 5.5.
  - Random subspaces (c1): median -0.005, 95th percentile 0.015.
- **GRID.**
  - Recovery by rank 2.21 / 2.72 / 3.07 / 3.25.
  - Held-out pairs are all BFS sources into DFS-class twins: 111 of 120 twins pick DFS at index 32.
  - c1: median 0.013.
- **Baselines at the same site** (difference in means, DiM, and PCA):
  - T10: DiM-1 recovers 0.44-0.61 and PCA-8 0.97.
  - GRID: DiM-1 recovers 0.92 and PCA-8 1.01.
  - So the natural-variance directions reproduce the full-state effect, and only DAS overshoots it.
  - The fitted first direction is nearly orthogonal to the unembedding difference of the class tokens (logit-lens
    cosine 0.07 for Qwen, 0.03 for Gemma).

**Controls.**

- **c2, label control.**
  - T10: refits on cyclic derangements pi1 and pi2 and a prompt-level derangement, with 100% of retained targets
    changed, still move held-out pairs toward the TRUE source class at 0.87, 0.63 and 0.77 of the true fit.
  - The same maps also fit their permuted targets: pi1 reaches a train KL of 0.0002 and writes DFS for BFS sources
    in generation (PERM 20/20 DFS).
  - GRID: 2 classes (F3), so it uses balanced prompt-level shuffles with 33-58% of labels changed. They reach 0.11,
    0.11 and 0.20 of the true fit.
- **c3, random-init network.** Same config, torch seed 0, next-token entropy 11.1-12.0 nats; same pairs, map class,
  objective and budget, with the trained targets.
  - T10: mean held-out Delta 12.1 nats against 17.5 trained (ratio 0.69).
  - GRID: 3.7 against 9.1 nats (ratio 0.41).
  - The full-state exchange on the random network does little (1.2 and 0.45 nats).
  - So a linear map at the decision token can manufacture most of the effect with no trained computation behind it.
- **c4, reverse.**
  - T10: writing the padding twin's coordinates into a held-out forced prompt moves the margin the wrong way
    (recovery -2.72).
  - GRID: it moves it 2.8x the full-state reverse (8 pairs), which passes the threshold but is again an overshoot.
- **c5 / c6, natural manifold.**
  - Projected onto the top-64 principal components of 160 (Qwen) or 120 (Gemma) natural twin states, the maps keep
    only 0.18 and 0.12 of their effect.
  - The sensitivity bases, which add the forced prompts and bans, give 0.19 and 0.44.
  - Natural-variance share: Qwen 0.0076, above random (c6 passes). Gemma 0.0014, below the random 95th percentile
    (c6 fails; c6b passes).
- **c7.** The three seeds agree: first principal cosines 0.85-0.89 for Qwen and 0.52-0.54 for Gemma.

**Generation** (held-out pairs, canonical opening prefilled, CRN slots, hidden tests; `figures/F4_generation`).

| unit, target | BASE | FULL | DAS k* | RAND k* | other DAS ranks | pass rate DAS / BASE | McNemar DAS vs RAND |
|---|---|---|---|---|---|---|---|
| T10, DFS | 0/30 | 2/30 | **29/30** | 0/30 | k1 25/30, k2 29/30 | 1.00 / 0.83 | 29:0, p = 1.9e-9 |
| T10, BFS | 0/30 | 0/30 | **5/30** (29/30 write BFS) | 0/30 | n/a | **0.20** / 0.83 | 5:0, p = 0.031 |
| GRID, BFS | 6/30 | 10/30 | **22/30** (27 attempted) | 5/30 | k1 22/30, k2 21/30 | 0.73 / 0.90 | 17:0, p = 7.6e-6 |

- **Broken BFS programs.** The T10 edit toward BFS makes the model open with `def bfs(...)` and write BFS, but 24 of
  29 such programs fail the hidden tests. A typical failure: the helper returns `len(visited)` and the caller does
  `visited.update(bfs(i))`. The decision token is written, and the program the model then builds around it is
  incoherent: one more sign of an off-manifold edit.
- **No restoration.** Neither the reverse DAS edit nor the reverse full-state exchange restores the default in
  generation (0/20 restored in REV-DAS, REV-FULL and SRC), so generation c4 is not estimable. With the opening
  prefilled through ' def', a forced prompt keeps its class whatever is written at d.

### 3. The T10 task band (blocks 12-23, all spec positions, one shared R)

- **Teacher forcing.** k* = 2, recovery 0.82 (0.48-1.16). Per class: BFS 1.57, DFS 0.68. No overshoot.
- **Controls.**
  - c1: median 0.003. c3 passes: random-init ratio 0.18. c4 passes: reverse 0.77.
  - c5 fails on twins (retention 0.43) but passes on the sensitivity basis (0.90). Wording: "outside the twin's
    variation, inside the variation the model shows across instructions".
  - c6 passes (share 0.0030 against random p95 0.0006).
  - c2 fails: label refits at 0.71, 0.79 and 0.72.
  - c7 fails: 2 seeds, first cosine 0.49.
- **Identity check U4.** The band full-state exchange flips the TF class on only 58% of held-out pairs, below the
  planned 90%. Positions are verified (`tests/test_cpu_tiny.py`), so this is the model, not the code.
- **Generation** (free, from index 0):
  - BFS target: DAS 28/30 correct, FULL 23/30, RAND 0/30, BASE 0/30.
  - DFS target: the same map writes **BFS on 24/30**, DFS on 3/30 (FULL: DFS 20/30).
  - The pi1 label-control map writes DFS for both source classes (16/20 and 17/20).
  - So the rank-2 band handle encodes "leave union-find, toward the algorithm this map was fitted to favour" rather
    than the source's class. This is the generation face of the c2 failure.
- **Iteration-7 overlap.** First principal cosines with iteration 7's MAIN_LY handle are 0.12-0.17.

### 4. Mediation: do iteration 4's random pushes act through the fitted subspaces? No.

**Setup.**

- **Pushes.** Iteration 4's 40 random directions, alpha 2, absolute unit n[l,p], applied at blocks 12-23 and spec
  positions during the prefill.
- **Predictor** (committed in #3 before any outcome was read). pi_u is the projection of each push's realised
  displacement on the band subspace (k* = 2), scaled by the forced-class displacement.
- **Outcome.** Each direction's correct off-default share in art_lpQalcAXMGr1's engine-d and engine-c rows.

**Results.**

- **Retrospective association.** Spearman(pi, escape) = **0.39** (p = 0.006, n = 40); engine d alone 0.36, engine c
  alone 0.39.
  - Partial correlation controlling the push norm over the band: 0.42; at block 35: 0.39.
  - A permuted predictor gives 0.14.
  - This is below the committed 0.5 bar: a moderate association, not mediation.
- **It does not generalise.** On 24 prospective directions (seeds 98001-98024, committed in #4), the same predictor
  gives Spearman **0.09** (p = 0.33), with 208 of 240 programs run before the time cap.
- **Clamping the subspaces removes nothing.** The 10 most-escaping directions were run with 27-30 CRN slots each
  (270 paired slots). Pushes escape on 218/270.
  - Clamping the band subspace back to the twin at every band block (TASK-CLAMP) leaves 221/270 escapes: removal
    **-0.01**, McNemar 8:11.
  - An equal-rank random clamp: 213/270, removal 0.02.
  - DEC-CLAMP, writing the twin's decision-site coordinates at d at L* once generation reproduced the opening (reach
    rate 0.53): 46 escapes against 44 among the 53 reached slots.
  - The committed clamp test (TASK removal >= 0.5 and RAND <= 0.10) **fails**. As predicted for the band, random
    pushes move the algorithm through other directions than the fitted handles.


### 5. Geometry in actual activation coordinates (`figures/F3_geometry_T10`, `figures/F3_geometry_GRID`, `F3b_*`)

- **What is plotted.** Every prompt's coordinates in the fitted R_8 subspace at (L*, d), centred on the twin mean,
  embedded by metric MDS (Kruskal stress-1: 0.015 for T10, 0.027 for GRID) and by Isomap (k = 8). Beside them is a
  PCA of the raw block-L* states.
- **Centroids.** Class centroids are sized by implemented, test-passing BASE + SRC programs:
  - T10: union-find 87, DFS 35, BFS 34.
  - GRID: DFS 21, BFS 7.
- **T10.** Forced BFS, DFS and union-find prompts form three well-separated clusters. The neutral twins, the two seed
  strings, 'Make a new algorithm.' and the long novelty instruction all sit together, away from every forced cluster.
  The five union-find bans sit just outside the twin cluster, toward the forced clusters.
- **GRID.**
  - Forced A* prompts sit beside forced BFS. This matches the token map: A*'s ' open' continues as BFS under a
    neutral prompt.
  - Forced IDDFS sits close to the twin cluster, on the A*/BFS side rather than the DFS side. Its free-generation
    programs were labelled DFS 7/20 and disputed 13/20.
  - The top-five prohibition prompt and the novelty instruction stay inside the twin cluster, on neither class's
    side.
- **Titles.** They say "handle coordinates (not certified)" because no site is certified.

### 6. Post-hoc sensitivity: the same protocol at T10 block 24 (descriptive, never substituted for L*)

Block 24 is the first block where the full-state exchange carries the class: 16.2 nats, flipping 100% of held-out
pairs. Every map, pair, seed and control is the same as at L*. It was not planned and is reported as a sensitivity
analysis only.

- **Teacher forcing.** k* = 2, recovery **1.22** (0.98-1.43), below the OFF-MANIFOLD line. By rank: 1.10 / 1.22 /
  1.24 / 1.29. Per class at k = 2: BFS 1.72, DFS 0.77.
- **Controls that now pass.** c1 (median 0.0003 at k*); c4 reverse 1.17; c5 retention 0.52 (c5b 0.74); c6 (0.0075 against
  random p95 0.0010); c7 (first cosines 0.61-0.63).
- **Controls that still fail.** c2: label controls reach **0.61, 0.57 and 0.50** of the true fit (p = 0.0005 each
  for true > permuted). c3: a random-init network reaches **0.54** of the trained Delta (limit 0.25).
- **Baselines catch up.** DiM-1 recovers 0.88-0.99 and PCA-4 0.99, the same as DAS.
- **Reading.** Once the site has a real full-state ceiling, the dormancy and off-manifold failures at L* = 22 go
  away. What remains is the lack of specificity:
  - the map class can be trained toward permuted labels and still move the true class half as far;
  - a randomly initialised network admits half the effect.
  At block 24, the class information at the decision token is carried by the natural difference-in-means direction,
  which a linear map of almost any labelling partly recovers.

### 7. Novelty and labels

- **No novel programs.** Of 1,857 correct programs (1,708 T10 and 149 GRID), none is labelled 'other', so no judge was called (USD 0.00).
  The rule-of-three upper bound on the novel-program rate is 0.0016 (T10 alone 0.0018; GRID alone 0.020).
- **Unresolved grid labels.** 19 GRID programs are 'disputed': 18 with runtime IDDFS vs AST BFS, all failing the
  tests. The blind judge was not called; these count as neither class.

### Use of the declared dataset dependency (art_j3Rm_lr2nzR6)

`src/s0_inputs.py` scans all ten datasets of `full_data_out.json`. Per-dataset counts are in `inputs/dep_extract.json`.

- **concreteness_norms** (39,954 words; 718 flagged neutral-noun candidates) supplies the 20 new single-token twin
  nouns, ranked by SUBTLEX frequency. With iteration 7's 12 nouns this gives the 160 twin states of the T10
  natural-variance basis used by c5 and c6. The nouns are taken from the dependency's flagged list as is (it includes
  'ass' in its donkey sense).
- **Reference programs.** mercury (52), xlcost_python (16), kodcode_algorithmic (5) and leetcodedataset (3) supply
  the 76 connected-component reference programs used as nearest known solutions in the novelty audit.
- **Scanned, nothing used.** llm_creativity, thealgorithms_python, clrs_text, humanevalplus and enamel hold no T10 or
  grid material this experiment uses.

### 8. Departures from the plan (all logged in `results/deviations.jsonl`)

- **Hardware.** One NVIDIA L4 (23 GB, 300 GB/s) and 6 CPUs instead of the planned A4500, with about 5.5 h in total.
- **Scope cut at commit #0.** B3 and the Gemma task band were dropped.
- **GRID has 2 classes.**
  - A* had 16/20 free-generation adherence but no distinct decision token at index 32. IDDFS had 0/20.
  - The greedy best-first and bidirectional BFS fallbacks were not tried.
  - c2 on GRID therefore uses balanced prompt-level shuffles (weaker than a derangement), so the K2 statement carries
    "3-class c2 tested in Qwen only".
- **Band budget.** Band fits ran 109 steps (2.2 s per step), the same for every band fit including controls, with
  2 seeds instead of 3.
- **T10 scan.** Blocks whose full-state exchange moves under 10% of pairs by 1 nat (blocks 0-14) were recorded as
  undefined rather than fitted.
- **Crash and reruns.**
  - The first T10 scan was restarted after a NaN-ordering bug in the L* argmax was found at block 2.
  - The first GRID stage crashed in the 2-class label control and was rerun with the F3 shuffle, reusing the saved
    scan and seed maps.
  - The first mediation run hit a GPU out-of-memory error in the clamp and was rerun after the fix.
- **Not run.** The S2 engine check against iteration-6/7 per-slot labels (every contrast is within this engine) and
  the band geometry figure.
- **Labeller disagreements** were not sent to the blind judge. T10 keeps the runtime label, flagged; GRID marks them
  'disputed'.
- **predictions/hardware.json** was written after generation began.
- **Edited after commit #0.** `src/s0_inputs.py` was made portable after the run: sources now resolve by artifact
  id. Its copy logic is unchanged.
- **Time caps.** Mediation ran 270 of the 300 planned clamp slots (27-30 per direction) and 208 of 240 prospective
  programs.
- **Post hoc.** The block-24 sensitivity (section 6) and its random-init control were added after the scan was seen.
  They are descriptive, have no generation cells, and change no verdict.

### 9. Positioning (`results/positioning.json`, seven dated queries, 2026-10-23)

- **DAS** (Geiger et al.) and **Boundless DAS** (Wu et al.): same map class. We add the specificity controls
  together.
- **Makelov et al.**: dormant-pathway illusion. It predicts our OFF-MANIFOLD overshoot, the failed natural-PC
  retention and the failed reverse at the decision sites.
- **Sutter et al.**: random-init networks. Our c3 shows that even a LINEAR map at a decision token reaches 0.41-0.69
  of the trained effect on an untrained network.
- **MIB** (Mueller et al.): DAS beats DiM and PCA in teacher forcing, but MIB scores no specificity control.
- **CDAS**: the bounded objective and bi-directional test we adopted.
- **arXiv 2511.04638**: divergent representations under interventions.
- **Field handbook rules followed.**
  - The map class is declared before any fit (Sutter).
  - Every fit has an untrained-network arm and a random-subspace arm.
  - Steering is reported per sample and per class, including where it fails: the BFS edit writes the decision token
    but mostly broken programs.
  - Decodability is not taken as actionability: the clamp experiments ask whether the fitted subspace is the route a
    push actually uses, and it is not.

### 10. Verification

- **Unit tests.**
  - U1 (zero edit on the KV path) is exact.
  - U2/U3 (KV path vs full recompute): 0.25 nats on Qwen and 0.10-0.12 on Gemma in bf16. Every Delta is measured on
    one path.
  - CPU equivalence tests: the KV path and the band path equal hooked full recomputation within 0.002 nats on tiny
    Qwen3 and Gemma3 models, and the recovery estimator returns 0.599 for a true 0.6.
- **Commit chain.** 8 commits: #0; #1 per unit; #2 per unit and site; #3 mediation; #4 prospective. 0 breaks
  and no committed payload changed (`src/commit8.py verify()`).
- **Re-derivation.** `audit/rederive.py` (stdlib only, no shared code) reproduces all 38 checked headline numbers
  from the raw rows: the four TF recoveries, every generation count, the nine label-control ratios, the clamp
  removals, both mediation Spearman values, the exact McNemar p-values and the K2 status.
  - The c3 ratios are recomputed only from the stored per-site means; per-pair random-init rows were not saved.
  - Its placebos fail as they should: a coin-swap of DAS/RAND outcomes removes the 29:0 asymmetry, and a permuted
    mediation predictor gives |rho| < 0.3.


## Layout

| path | what it is |
|---|---|
| `method.py` | entry point: runs every stage in order (resumable); `--cpu-only` re-runs analysis and outputs |
| `reproducibility.md` | exact steps, commands, seeds, hardware and runtimes actually used, and the numbers to expect |
| `src/cfg8.py` | constants (models, units, protocol, thresholds), JSON/IO helpers, CRN streams |
| `src/s0_inputs.py` | S0: copies + sha256-hashes every read-only input; extracts all ten datasets of art_j3Rm_lr2nzR6 |
| `src/prompts8.py`, `src/grid_prompts.py` | S1: T10 prompt set (iteration-7 ids + display-name paraphrases + 20 new nouns) and GRID prompt set (iteration-7 Gemma code) |
| `src/commit0.py`, `src/commit8.py` | protocol commitment #0 and the sha256 hash chain (`commitments.log`, payloads in `predictions/`) |
| `src/engine8.py` | model loading (trained / random-init), hooked prefill, teacher-forced states, KV-path forward, CRN decoder with fence stop |
| `src/das8.py` | the single DAS protocol: class maps, `DecSite` (KV path, G bases x Q edits), `BandSite` (recompute path, checkpointing), fits, geometry helpers |
| `src/run_dec.py` | S3-S6 decision site per unit: token maps, adherence, commit #1, caches, unit tests U1-U3/U9, scan, fits, controls c1/c2/c4-c7, baselines (DiM, PCA, logit lens) |
| `src/run_band.py` | S7: T10 task band with U4 and controls c1/c2/c4-c7 |
| `src/run_rinit.py` | S8: random-initialisation control c3 (decision site; `--band`) |
| `src/run_gen.py`, `src/gen8.py`, `src/label8.py` | S9: generation cells (commit #2 first) and the frozen labellers |
| `src/run_med.py` | S10: mediation of iteration 4's 40 random pushes (commit #3), clamp, prospective set (commit #4) |
| `src/run_post.py` | per-pair label-control test (p_c2) for T10 from the committed maps |
| `src/analysis8.py`, `src/digest8.py`, `src/figures8.py`, `src/novelty8.py`, `src/outputs8.py` | verdicts, K2, tables (`results/summary.md`), figures, novelty audit, `method_out.json` |
| `audit/rederive.py` | stdlib-only re-derivation of the headline numbers + placebos (`results/rederive.json`) |
| `tests/test_cpu_tiny.py` | CPU equivalence tests of the KV and band paths on tiny random Qwen3/Gemma3 models (`results/unit_tests_cpu.json`) |
| `scripts/gpu_queue*.sh` | the GPU queues actually run (one model on the GPU at a time) |
| `prompts/` | every prompt with token ids, positions and splits |
| `data/` | per-sample generation rows (`samples_*.jsonl`), labels (`labels_*.jsonl`), per-pair TF rows (`tf_*.jsonl`), pair lists |
| `results/` | every stage's JSON (`dec_*.json`, `band_T10.json`, `rinit_*.json`, `mediation_T10.json`, `analysis.json`, `summary.md`, `deviations.jsonl`, ...) |
| `das_maps/` | every fitted map (kept on the run's volume and published; small) |
| `figures/` | F1-F5 (PDF + PNG): scan profiles, recovery by rank, decision-site geometry (actual R_8 activation coordinates), generation, mediation |
| `predictions/` | commitment payloads (#0, #1 per unit, #2 per unit/site, #3, #4) and `hardware.json` |
| `inputs/` | read-only copies of earlier artifacts (sha256 in `inputs/input_hashes.json`); kept on the run's volume |
| `cache/` | activation caches (states and class distributions at d; band covariance); regenerable |
| `method_out.json` (+ `full_`/`mini_`/`preview_`) | exp_gen_sol_out output: one example per generation slot, mediation slot and held-out TF pair |

## How to run

```bash
uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml
.venv/bin/python method.py              # everything (about 3.5 GPU-hours on one 23 GB L4)
.venv/bin/python method.py --cpu-only   # analysis, figures, outputs and the audit from the saved rows
.venv/bin/python tests/test_cpu_tiny.py # CPU equivalence tests (no download)
python3 audit/rederive.py               # stdlib-only re-derivation
```

Models are read from the Hugging Face cache (`HF_HOME`) at the pinned revisions `Qwen/Qwen3-8B@b968826d` and
`google/gemma-3-4b-it@093f9f38`.

## Restoring removed files

`.aii/manifest.yaml` marks three paths for deletion after the round:

- `.venv/` (regenerable): `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml`
- `cache/` (regenerable; activation caches): `.venv/bin/python src/run_dec.py --unit T10 && .venv/bin/python src/run_dec.py --unit GRID && .venv/bin/python src/run_band.py`
  (delete `results/dec_*.json` / `results/band_T10.json` first, or the stages skip as already done)
- `src/__pycache__/` (regenerable; Python bytecode): `.venv/bin/python -m compileall src` (it is also rebuilt
  automatically on import)

The models themselves live in the run's shared Hugging Face cache, not in this folder:
`hf download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218` and
`hf download google/gemma-3-4b-it --revision 093f9f388b31de276ce2de164bdc2081324b9767`.
`inputs/` is kept on the run's volume (frozen copies whose upstream folders may be purged). `das_maps/` (3.8 MB of
fitted maps) is small enough to ship with the repository as is.
