# Where noise must go to change the idea (iteration 4, plan-site noise)

Isotropic random noise in Qwen3-8B's residual stream can make it write a *different correct algorithm* (exp17
screen). This artifact asks **where** that noise has to enter. It writes the same random displacement, at the same
per-position ban-unit dose, into six sites:

- S0: the task-specification states at blocks 12-23;
- S1: the read position;
- S2: the condition sentence;
- S3: generated tokens 1-32;
- S4: blocks 0-11;
- S5: blocks 24-35.

Each site is then priced on a randomisation hull of correct-only, mechanism-labelled diversity against pass rate
(**C1-site**). Every contrast is an exact paired flip, because each common-random-numbers (CRN) slot shares one
random direction and one stream of token uniforms across all arms. Two more tests run in the same pipeline. **C3c
boundary**: S0 at alpha 8, plus a novelty audit of every correct off-catalogue program from every arm. **C3d**: the
request's top-five prohibition applied *at the plan*: a push along the survivor-minus-TOP5 centroid direction on T1.

Model: Qwen3-8B (rev `b968826d`, thinking off, T = 1.0). Tasks: T03 k-th smallest, T05 two sum, T06 find duplicate,
T10 connected components, T1 grid path, T2 weighted shortest path. Engine: FP8 W8A8 on a 16 GB RTX 2000 Ada (frozen
precision rule; deviation D1). The rules and predictions were hash-committed before the first decisive sample
(`commitments.log`, `predictions/`).

## Results

**Bottom line.**

- **Only the task-specification states move the algorithm.** The noise changes which correct algorithm the model
  writes only when it is written into those states. At the middle blocks (S0), it buys mechanism-level diversity at
  almost no pass-rate cost on T03, T10 and T2, and weakly on T1. The same random displacement at the read position
  (S1) or on the condition sentence (S2) changes no algorithm at any dose: 0 off-default correct programs on all six
  tasks at alpha 1, 2 and 4. On the task spec at blocks 24-35 (S5) it is almost as inert: 6 of 521 correct
  programs go off default (5 on T10, 1 on T2). The outputs at these three sites are often byte-identical to the twin's, for example 90-100%
  at alpha 1 on T03/T05/T06 for S1 and S5.
- **The effect is site-specific, not generic transmission.** S1 drives as large a displacement at R (block 35) as S0
  does: medians 141/250/474 vs 159/272/461 at alpha 1/2/4. Yet S1 flips nothing. In the transmission model the S0
  indicator stays far above zero at matched downstream displacement: logit +2.15, 95% CI [1.79, 2.51].
- **The frozen C1-site rule nevertheless returns PARTIAL.** S0 has the best H5 on **3 of 6** tasks (T03, T1, T2;
  raw p = 0.062 under Bin(6, 1/6); it enters the iteration's secondary Holm family). Generated-token noise (S3) has
  the best H5 on T05 and T06, where nothing moves without breaking something. Early-block noise on the task spec (S4)
  is best on T10. S4's ban units are only 4.5-7.2% of the residual norm (S0: 12.7-18.3%), so S4 at alpha 4 is a
  relative dose comparable to S0 at alpha 1. This is the dose-convention confound the plan named.
- **Only T2 comes close to being resolved.** Every per-task margin is a bootstrap close call: P(S0 argmax) is 0.59
  (T03), 0.38 (T05), 0.31 (T06), 0.33 (T10), 0.67 (T1) and **0.97 (T2)**. Even on T2 the 95% CI of D_t just touches
  zero ([-0.00, 0.69]).
- **What the data support.** The site that chooses the idea is *the task-specification states at early-to-middle
  blocks*. The read-out sites, the condition sentence and the late blocks are inert. "Blocks 12-23 specifically" is
  *not* supported over blocks 0-11. This is a site-specific perturbation result, not evidence of a plan
  representation (plan departure 5).

### C1-site: prices on the randomisation hull (correct-only rarefied Hill-1, depth 25; 2,000 template-stratified bootstrap replicates with the hull maximum recomputed inside each)

| Task (default) | H5 S0 | H5 S1 | H5 S2 | H5 S3 | H5 S4 | H5 S5 | best | D_t = H5(S0) - max other [95% CI] | P(S0 argmax) |
|---|---|---|---|---|---|---|---|---|---|
| T03 (full_sort) | 2.61 | 1.00 | 1.00 | 2.24 | 2.46 | 1.00 | S0 | 0.15 [-0.75, 0.87] | 0.59 |
| T05 (hash_map) | 1.28 | 1.00 | 1.00 | 1.28 | 1.14 | 1.00 | S3 | -0.00 [-0.49, 0.32] | 0.38 |
| T06 (hash_set) | 1.16 | 1.00 | 1.00 | 1.24 | 1.00 | 1.00 | S3 | -0.08 [-0.41, 0.27] | 0.31 |
| T10 (union_find) | 2.23 | 1.00 | 1.00 | 1.24 | 2.32 | 1.38 | S4 | -0.08 [-0.78, 0.49] | 0.33 |
| T1 (bfs) | 1.29 | 1.00 | 1.00 | 1.18 | 1.13 | 1.00 | S0 | 0.11 [-0.28, 0.57] | 0.67 |
| T2 (dijkstra) | 1.66 | 1.00 | 1.00 | 1.12 | 1.22 | 1.15 | S0 | 0.44 [-0.00, 0.69] | 0.97 |

H5 = the best Hill-1 within 0.05 pass-rate cost of the twin. P15/P20 = the cheapest pass-rate cost that reaches
Hill 1.5/2.0 ('n/a' = not reached at any mixture):

| Task | P15 S0 | P15 S1 | P15 S2 | P15 S3 | P15 S4 | P15 S5 | P20 S0 | P20 S1 | P20 S2 | P20 S3 | P20 S4 | P20 S5 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| T03 | 0.00 | n/a | n/a | 0.01 | 0.00 | n/a | 0.00 | n/a | n/a | 0.04 | 0.00 | n/a |
| T05 | 0.53 | n/a | n/a | 0.12 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| T06 | 0.54 | n/a | n/a | 0.16 | n/a | n/a | 0.75 | n/a | n/a | 0.37 | n/a | n/a |
| T10 | 0.00 | n/a | n/a | 0.11 | 0.00 | n/a | 0.01 | n/a | n/a | 0.19 | 0.02 | n/a |
| T1 | 0.14 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| T2 | 0.00 | n/a | n/a | n/a | 0.25 | n/a | n/a | n/a | n/a | n/a | n/a | n/a |

- **Decision (frozen rule).** Per task, best site = argmax H5 rounded to 0.01. Ties go to the lower P15. On T05,
  S0 and S3 tie at 1.28 and S3 wins on P15 (0.12 vs 0.53). Count of tasks where S0 is best: 3, below the
  pre-registered 4, so the claim is not CONFIRMED. It is not DISCONFIRMED either: no other site reaches H5 >= H5(S0)
  on 4 tasks (S3: 2, S4: 1, S1/S2/S5: 0). Verdict: **PARTIAL**.
- **Sensitivities.** Appending alpha 8 to S0's hull, or allowing only mixtures of adjacent doses (linear
  interpolation), leaves every H5 ranking unchanged (`results/hull.json`). Within the 0.10-Hill equivalence margin,
  S0 ties the best other site on T05, T06 and T10.

**Failure mode per site (frozen rule; full numbers in `results/failure_modes.json`):**

| Site | T03 | T05 | T06 | T10 | T1 | T2 |
|---|---|---|---|---|---|---|
| S0 | moves | moves with cost | moves with cost | moves | moves with cost | moves |
| S1 | no movement | no movement | no movement | no movement | no movement | no movement |
| S2 | no movement | no movement | no movement | no movement | no movement | no movement |
| S3 | moves | moves | moves with cost | moves | breakage first | breakage first |
| S4 | moves | weak movement† | no movement | moves | breakage first | weak movement† |
| S5 | no movement | no movement | no movement | weak movement† | no movement | no movement |

† Not covered by the frozen rule (0.10 <= correct-only excess < 0.20 with pass >= 0.8 x twin); reported as 'unclassified (weak movement)' in the JSON.

- **Paired flips under CRN, alpha 2.** Each cell shows the number of the 30 shared slots that go off default only
  under S0, then only under the other site, with the exact McNemar p and that site's byte-identical rate vs the twin.
  S0 flips significantly more slots off default than S1, S2 and S5 on T03, T10, T1 and T2, and more than S4 on T03 and
  T10. S3 flips *more* than S0 on T06 (0 vs 12) and cannot be told apart from S0 on T03 (8 vs 6) or T05 (7 vs 2), but
  it pays in breakage: S3 is the only site whose invalid rate climbs to 0.67-1.00 at alpha 4.

| Site vs S0 | T03 | T05 | T06 | T10 | T1 | T2 |
|---|---|---|---|---|---|---|
| S1 | 14:0 (p=0.00012; id=0.93) | 3:0 (p=0.25; id=0.97) | 1:0 (p=1; id=0.80) | 18:0 (p=7.6e-06; id=0.33) | 6:0 (p=0.031; id=0.13) | 8:0 (p=0.0078; id=0.57) |
| S2 | 14:0 (p=0.00012; id=0.87) | 3:0 (p=0.25; id=0.70) | 1:0 (p=1; id=0.87) | 18:0 (p=7.6e-06; id=0.40) | 6:0 (p=0.031; id=0.07) | 8:1 (p=0.039; id=0.57) |
| S3 | 6:8 (p=0.79; id=0.13) | 2:7 (p=0.18; id=0.10) | 0:12 (p=0.00049; id=0.07) | 10:2 (p=0.039; id=0.00) | 5:1 (p=0.22; id=0.00) | 6:3 (p=0.51; id=0.00) |
| S4 | 11:1 (p=0.0063; id=0.63) | 3:0 (p=0.25; id=0.57) | 1:0 (p=1; id=0.40) | 13:1 (p=0.0018; id=0.27) | 5:2 (p=0.45; id=0.00) | 5:3 (p=0.73; id=0.20) |
| S5 | 14:0 (p=0.00012; id=0.97) | 3:0 (p=0.25; id=0.97) | 1:0 (p=1; id=0.93) | 16:1 (p=0.00027; id=0.33) | 7:0 (p=0.016; id=0.27) | 7:0 (p=0.016; id=0.20) |

- **Transmission** (`results/transmission.json`, fig 4). The model is a logistic regression of correct-only
  off-default on log realised displacement at R (block 35), with template and task fixed effects, over 2,769 correct
  prefill-site programs. The S0 indicator is +2.15 [1.79, 2.51] while the displacement slope is +0.88
  [0.62, 1.14], so S0's advantage persists at matched downstream dose. In the matched-dose bins (upper three quintiles
  of the displacement) S0 is off default 16-27% of the time, against 3-7% for the other prefill sites. The plan's
  first-token KL is degenerate here: 89% of rows are below 1e-6, because the first token is always the code fence
  (deviation D5). S3, analysed on its own step-wise KL (steps 1-32), goes off default more often as the KL rises
  (+0.75 per log-KL unit [0.45, 1.06]).
- **Pooled descriptive model** (Bayesian mixed logistic, random task and template effects; `results/pooled_model.json`).
  Relative to S0, the site effects are S1 -3.0, S2 -2.9, S5 -3.0, S3 -0.8 and S4 -1.1 (posterior SD 0.1-0.6). S0's
  slope on log2 alpha is +1.11.
- **Surface variation.** S3 produces the most phrasing clusters per idea: AST-shingle components at theta 0.8 number
  4.2 and 4.7 per idea at alpha 1 and 2, against 2.8 and 3.4 for S0 (fig 7). The noise at S1, S2 and S5 changes
  phrasing on T10/T1/T2 (byte-identical rates 0.1-0.6) but not the idea, except for S5's small T10 excess.
- **Energy-matched sensitivity** (S1E/S2E, alpha 1). All of S's ban energy is concentrated on R (S1E), or spread
  over the condition span (S2E). S2E stays inert. S1E moves T06 (+0.23) and T10 (+0.18) with pass ratios of
  0.87-0.93. Its realised displacement at R (median 1,002) is 6x S0's at alpha 1.

### Prediction scorecard (committed in `predictions/predictions.json` before the first decisive sample)

| Prediction | Outcome |
|---|---|
| C1-site: S0 highest H5 on >= 4 of 6 | **Missed**: 3 of 6 (PARTIAL) |
| S1 'no movement' on >= 5 of 6 | **Hit**: 6 of 6 |
| S2 below S0 on >= 4 of 6; may move T05/T06 | **Hit**: 6 of 6 below (H5 = 1.00 everywhere); it moves nothing |
| S3: more phrasing clusters per idea than S0, little idea change, breakage first by alpha 4 | Clusters **hit**; 'little idea change' **missed** (S3 moves T03/T05/T06/T10); breakage by alpha 4 **hit** (invalid 0.67-1.00) |
| S4 'breakage first' at alpha >= 2 | **Missed**: S4 'moves' on T03 and T10 at alpha 4 with pass kept |
| S5 'no movement' at alpha 1-2, breakage at 4 | No movement **hit** (5 of 6; T10 weak); breakage at 4 **missed** (pass >= 0.87) |
| S1E/S2E breakage (pass < 0.8 x twin) on >= 4 of 6 | **Missed**: 0 of 6 for both |
| Boundary: pass < 0.5 at alpha 8 on >= 4 of 6 | **Hit**: 6 of 6 (pass 0.00 everywhere) |
| Boundary: correct-only Hill peaks at alpha 2-4 | **Hit**: alpha 2 on 3 tasks, alpha 4 on 3 tasks |
| Boundary: 0 judge-confirmed novel algorithms | **Hit**: 0 of 3,555 correct programs (one correct 'other' program, judged degenerate / a known brute force) |
| C3d: TOP5 avoidance < 0.5 at alpha <= 2 | **Hit**: 0.00 at alpha 1 and 2 |
| C3d: landing at the edge (BiBFS) rather than the opposite side | **Not testable**: no survivor program at any dose |

### C3c boundary: S0 from alpha 1 to 8 (pass / invalid / correct-only Hill)

| Task | alpha: pass / invalid / Hill(correct) |
|---|---|
| T03 | 0: 1.00 / 0.00 / 1.00; 1: 1.00 / 0.00 / 2.52; 2: 0.93 / 0.00 / 2.68; 4: 0.67 / 0.00 / 2.23; 8: 0.00 / 0.94 / n/a |
| T05 | 0: 1.00 / 0.00 / 1.00; 1: 1.00 / 0.00 / 1.00; 2: 0.97 / 0.00 / 1.28; 4: 0.30 / 0.07 / 1.70; 8: 0.00 / 0.94 / n/a |
| T06 | 0: 1.00 / 0.00 / 1.00; 1: 1.00 / 0.00 / 1.00; 2: 1.00 / 0.00 / 1.15; 4: 0.17 / 0.03 / 2.59; 8: 0.00 / 0.94 / n/a |
| T10 | 0: 1.00 / 0.00 / 1.00; 1: 1.00 / 0.00 / 1.84; 2: 0.97 / 0.00 / 2.23; 4: 0.23 / 0.10 / 2.73; 8: 0.00 / 0.96 / n/a |
| T1 | 0: 0.74 / 0.00 / 1.00; 1: 0.72 / 0.00 / 1.39; 2: 0.68 / 0.00 / 1.51; 4: 0.12 / 0.06 / 1.00; 8: 0.00 / 0.82 / n/a |
| T2 | 0: 1.00 / 0.00 / 1.00; 1: 1.00 / 0.00 / 1.65; 2: 0.90 / 0.00 / 1.70; 4: 0.03 / 0.07 / 1.00; 8: 0.00 / 0.88 / n/a |

At alpha 8 the task specification is effectively erased. The model echoes the condition sentence, writes
placeholder code (`[your_answer]`, `def example_function(): pass`) or asks for clarification. Pass rate is 0.00 on
every task and the invalid rate is 0.82-0.96. Correct-only diversity peaks at alpha 2 (T03, T1, T2) or alpha 4 (T05,
T06, T10), and alpha 4 already costs 33-97% of the passes (fig 5).

**Novelty audit** (`results/novelty_audit.json`, `audit/`):

- **Pool and verdicts.** Across every arm, 3,555 analysed programs are correct; the pool also scanned the 164 correct
  filler twin rows (`TWIN_X`). Exactly one correct program carries the label 'other':
  a T06 program from S3 at alpha 2 that calls `nums.count(x)` for every element. It passes 3/3 stress tests at the
  spec's maximum size. Judge A (gemini-2.5-flash-lite) calls it a LABELLER MISS, judge B (gpt-4.1-mini) calls it
  DEGENERATE, and the tie-break (deepseek-chat-v3.1) also says DEGENERATE. The executor's manual pass, made beside its
  three nearest known solutions, calls it a CATALOGUE VARIANT (the textbook quadratic brute force).
- **Judge controls.** Before the pool, all three judges were run on the six controls: 6/6, 5/6 and 6/6 correct.
- **Index.** The known-solution index was rebuilt from the dataset dependency. It reproduces exp18's 472 rows exactly
  and adds 42 T05 (two sum) rows.
- **Claim.** **0 confirmed novel algorithms; rule-of-three upper bound 3/3,555 = 0.08% per correct program.** The
  claim "no push yields a correct algorithm outside the catalogue and its known variants" holds at a count of 0.

### C3d: the top-five prohibition at the plan site (T1)

| Arm (T1, k 0-9) | n | correct | avoidance of TOP5 [Wilson 95%] | K=7 landing (bibfs / idastar) | D_obs, p_edge / p_opp | correct composition (K=7) |
|---|---|---|---|---|---|---|
| TOP5_a1 | 50 | 30 | 0.00 [0.00, 0.11] | {} | n/a, n/a / n/a | {'bfs': 30} |
| S0_a1 | 50 | 36 | 0.03 [0.00, 0.14] | {} | n/a, n/a / n/a | {'bfs': 33, 'dfs': 2, 'other': 1} |
| TOP5_a2 | 50 | 19 | 0.00 [0.00, 0.17] | {} | n/a, n/a / n/a | {'bfs': 19} |
| S0_a2 | 50 | 34 | 0.00 [0.00, 0.10] | {} | n/a, n/a / n/a | {'bfs': 29, 'dfs': 5} |
| TOP5_a4 | 50 | 0 | n/a [n/a, n/a] | {} | n/a, n/a / n/a | {} |
| S0_a4 | 50 | 6 | 0.00 [0.00, 0.39] | {} | n/a, n/a / n/a | {'bfs': 6} |
| TWIN | 50 | 37 | 0.00 [0.00, 0.09] | {} | n/a, n/a / n/a | {'bfs': 37} |

- **Direction.** u_top5[l] = normalise(mean survivor centroid - mean TOP5 centroid), per block, from 300 forced
  prompts (30 per algorithm; nearest-centroid separability 0.83-1.00 for every algorithm, so the full version was
  used). Its cosine with the two-survivor (K=7) version is 0.66-0.87 across blocks.
- **Outcome.** Pushing the T1 plan states along it never moves the model off BFS. Correct programs are 30/30 BFS at
  alpha 1 and 19/19 BFS at alpha 2, and there are 0 correct programs at alpha 4. Avoidance of TOP5 is 0.00 [0.00,
  0.11] at alpha 1, so the push only costs passes. Fresh random plan noise at the same per-position norm (PN = S0,
  k 0-9) is no better (avoidance 0.03 and 0.00).
- **Comparison with the prompt routes.** This matches the prompt TOP5 ban (exp9: avoidance 0.00; BFS 63, DFS 36)
  and is a cleaner failure than the token veto (exp18: BFS 13, DFS 2, invalid 35).
- **Landing.** The survivor-permutation test is not computable: no survivor program appears at any dose. The plan
  geometry also leaves it little to resolve: BiBFS and IDA* sit almost equally far from the TOP5 set (geodesic 0.36
  vs 0.37; MDS stress-1 0.147; no H1 loop beyond a permutation null; `results/plan_geometry_T1.json`, fig 6).

### Engine check (positive control) and overlap with Step 1

- **Engine check.** In this artifact's engine, T03 rand_9002 and T2 rand_9004 at alpha 1 reproduce the exp17 screen
  **byte for byte**: 50/50 identical programs on each task, JS = 0.000 (null q95 0.029 / 0.025). The twin rows on the
  same slots are also identical. The bf16-vs-FP8 question did not arise, because the frozen precision rule put both
  runs on FP8 (deviation D1).
- **Overlap check** (STEP 11.10, `results/overlap_check.json`). The sibling Step-1 artifact (exp19, `PN_a4`, same
  FP8 engine) has 200 alpha-4 rows. Its alpha-4 compositions differ from this artifact's S0 alpha-4 cells beyond a
  template-stratified resampling null on T03, T05, T06 and T10, and agree on T2. At alpha 4 both are past the
  breakage point, so this artifact's alpha-4 cells should **not** stand in for the Step-1 knob table.

### Interpretation and limits

- **Scope.** This is a site claim for Qwen3-8B in FP8 on six memorised tasks.
- **Dose convention.** The units are per-position ban displacements, and a site can lose simply because its ban
  displacement is small relative to its leverage. S4 is the case in point, and the paired flips and transmission
  model are the guard against it. There is no convention-free dose; the relative units per site are in
  `results/units_summary.json`.
- **Resolution.** N = 30 per cell separates dead sites from live ones decisively (S1, S2 and S5 vs S0, McNemar
  p down to 1e-5). It cannot rank two live sites within about 0.2-0.4 Hill, which is why every per-task margin is a
  close call.
- **What it does not show.** Winning the site test would not show that the S0 states encode a plan. That is Step
  2's job.
- **Field norms this design answers** (mechanistic-interpretability handbook). Every arm is a random-perturbation
  control, matched in per-position norm, so the claim is relative to random noise rather than to no edit.
  Effects are treated as random variables: 30 fresh directions per cell, with template-stratified bootstrap
  intervals and the selection step inside the bootstrap. Results are reported per sample and per dose (exact paired
  flips, byte-identical rates, three or four doses per site), never as one mean at one coefficient. The C1-site
  claim was stated as a falsifiable hypothesis before sampling, and the table reports where it is and is not
  supported.

## Checks

- **Engine check (positive control).** T03: our composition {'quickselect': 16, 'full_sort': 15, 'size_k_heap': 19} vs screen {'quickselect': 16, 'full_sort': 15, 'size_k_heap': 19}, JS 0.000 (null q95 0.029), per-slot identical code 1.0, REPRODUCED = True; T2: our composition {'dijkstra': 26, 'bf_spfa': 24} vs screen {'dijkstra': 26, 'bf_spfa': 24}, JS 0.000 (null q95 0.025), per-slot identical code 1.0, REPRODUCED = True. The FP8 engine reproduces the exp17 screen rows byte for byte, under the same uniforms, units and direction.
- **GPU tests** (`results/unit_tests_gpu.json`). U1 CRN determinism across two batch compositions: T03 True, T1 True. U2: alpha 0 reproduces the twin byte for byte at every site, S3 with its shadow included: T03 True, T1 True. U3: the realised along-u displacement equals alpha x unit within 0.26% at every prefill site. S3 (block 23, vs shadow) matches its target within 0.01%. U6: peak 13.2 GiB at B = 20, P = 247, 1,024 new tokens. U7: the block-35-only edit is a no-op (T03 True, T1 True). U4 (shadow vs an independent teacher-forced forward) FAILS the 1e-2 rule: min cos T03 0.679, T1 0.996. The follow-up diagnostic (`results/u4_diagnostic.json`) shows that clean decode-path states (S3 alpha 0, no edit applied) diverge from a teacher-forced forward of the same tokens by the same order as the U4 shadow -> the U4 failure is a property of the FP8 decode path, not of the shadow coupling.
- **CPU tests** (`results/unit_tests_cpu.json`): T1 hook maths True (max relative error along u 2.3e-04 at the real unit scales). T2 hull True: an equal mix of two pure settings gives H5 = 1.96. T3 two-survivor permutation True. T4 screen byte-identity True. T5 binomial p(4 of 6) = 0.0087.
- **Labellers re-checked** (`results/labeller_recheck.json`). Bench references that pass and self-label: T03 6/6, T05 4/4, T06 5/5, T10 4/4. Gold-set runtime and AST labels reproduced: T03 28/28 and 28/28, T05 22/22 and 22/22, T06 25/25 and 25/25, T10 22/22 and 22/22. exp8 suite references: t1 12/12 pass, t2 10/10 pass.
- **Inputs** (`inputs/SHA256SUMS`, 493 files). Bench files against `bench/commitment.json`: 158 hashes, 0 mismatches.
- **Units cross-check** (`results/units_crosscheck.json`). Median ratio to exp17's FP8 units: T03 1.002, T05 0.993, T06 0.992, T1 1.002, T2 0.999. Ratio to exp13's units: T03 1.32, T05 1.18, T06 1.13, T10 1.14 (exp13 built different twins; deviation D10).
- **Independent re-derivation** (`audit/rederive.py` -> `results/rederive.json`). Cells checked: 146, mismatches 0. H5 re-derived with independent Monte-Carlo code: max |diff| 0.026, 0 cells beyond the 0.05 tolerance. C1 count re-derived 3 (matches: True). C3d mismatches 0. Placebos: with site labels shuffled within (task, alpha), S0 is best at rate 0.15 (null 1/6; observed 0.50). With template labels shuffled, the template spread of the off-default share is 0.060 (observed 0.058). With randomised d values, p_edge = 0.5 in 0.49 of draws.
- **Second re-derivation of the headlines** (`audit/rederive_headlines.py` -> `results/rederive_headlines.json`; raw files only, different methods). Correct off-default programs at S1 / S2 / S5: 0/526, 0/527, 6/521. The matched-dose S0 effect, recomputed as a hand-coded Mantel-Haenszel odds ratio (strata = task x quintile of displacement at R), is OR 5.72 [3.94, 8.30]. Its placebo, with S0 labels shuffled within task, gives median OR 0.98, and the CI excludes 1 in only 3.5% of 200 shuffles. Exact McNemar for S0 vs S1 at alpha 2 is reproduced by hand on every task; with pair members randomly swapped, p < 0.05 in 1.7% of 1,200 tests. Alpha-8 pass: 0.00 on every task. Correct programs: 3555, of which 1 is 'other'. TOP5 avoidance at alpha 1 / 2: 0.00 / 0.00. Engine check with an independent code-block extractor: T03 50/50 and T2 50/50 identical. C1 binomial p, by hand: 0.0623.
- **Pre-registration** (`commitments.log`, 59 lines, 0 chain breaks, 0 committed files changed since their commit). Commit #1 at 2026-10-21T03:55:02.383899Z. Decisive rows drawn before it: 0 of 4460. Only the engine check and smoke slots ran earlier.

## Design (what was run)

**Model and decoding.** Qwen3-8B, revision `b968826d9c46dd6066d109eabc6255188de91218`, thinking off, T = 1.0,
top-p 1, no top-k, at most 1,024 new tokens. A row stops at end of turn or at the closing fence of its first code
block. Precision follows the rule frozen in commit #0: on this 16 GB RTX 2000 Ada (compute 8.9) the decoder
linears run in FP8 W8A8 (exp17's engine). Embeddings, norms and lm_head stay bf16. Every arm uses the same precision.

**Prompts.** These are the neutral twins of the exp17 ban prompts. Each twin has a condition sentence, then the fixed
task specification, then the chat tail. In the condition sentence the banned name is replaced by a neutral noun,
padded with ` .` to the ban's token length. There are 5 templates (W1-W5) per task. Tasks and their defaults: T03
k-th smallest (full sort), T05 two sum (hash map), T06 find duplicate (hash set), T10 connected components
(union-find), T1 grid path (BFS), T2 weighted shortest path (Dijkstra). No ban prompt is ever sampled. Ban prompts
enter only as forward passes, to measure the units.

**Sites.** Every edit is displacement-targeted: `h <- h + (target - (h - h_twin).u) u` in fp32, cast to bf16. The
displacement from the clean twin along `u` therefore equals the target exactly at every hooked block and position.

| Site | Blocks | Positions | Per-position target (alpha x unit) |
|---|---|---|---|
| S0 | 12-23 | task spec S | alpha * n_S[l,k] |
| S1 | 12-23 | read position R = P-1 | alpha * n_R[l] |
| S2 | 12-23 | condition span COND | alpha * n_C,w[l,p] (zero on frame tokens before the noun) |
| S3 | 12-23 | generated input positions 1-32 (vs a teacher-forced shadow row) | alpha * n_G[l] |
| S4 | 0-11 | S | alpha * n_S[l,k] |
| S5 | 24-35 | S | alpha * n_S[l,k] (the block-35 edit is a no-op by construction, U7) |
| S1E / S2E | 12-23 | R / COND | S1 / S2 target x the energy-matching scalar c |
| TOP5 (T1) | 12-23 | S | per-block u_top5[l] (mean survivor centroid - mean TOP5 centroid) |

**Units** (`units/units_<task>.npz`). n = ||h_ban - h_twin|| per block and position, averaged over W1-W5 for S and
R and per template for COND. n_G[l] = mean over k of n_S[l,k]. Relative units are n / ||h_twin||.
`results/units_summary.json` reports them per site.

**Directions and common random numbers.** Slot (t, w, k) uses one random direction:
u = normalise(PCG64(stable_seed('PN4', t, w, k)).standard_normal(4096)). It is shared by every site, every dose and
the boundary arm. Slot (t, w, k) also uses the exp17 token uniforms u_stream(t, w, k). Every site contrast is
therefore an exact paired flip. Batches are fixed at 20 rows of one (task, template), and finished rows are fed
`<|im_end|>`. Under that shape a row's tokens do not depend on its batch-mates (GPU test U1).

**Cells.** Twin: N = 50 (k 0-9). S0-S5 at alpha 1, 2 and 4: N = 30 each (k 0-5). S1E and S2E at alpha 1: N = 30.
S0 at alpha 8: N = 50. TOP5 at alpha 1, 2 and 4 on T1: N = 50, with S0 topped up to N = 50 on T1 as the random
control. Engine check: T03 rand_9002 and T2 rand_9004 at alpha 1, N = 50 each. In total, 4,510 programs plus 540
shadow rows plus 150 filler twin rows (`TWIN_X`, descriptive only).

**Order of operations.** CPU tests, then GPU prep (positions, units, C3d geometry), then GPU tests U1-U7, then the
screen file, then commit #0, then the engine check, then smoke (slots k >= 100), then commit #1 (predictions, rules,
hull + decision code), then decisive sampling (priority P1-P9). The label worker runs alongside sampling. Then the
K=7 labels, commit #2 (analysis code), the analysis and the novelty audit. Last come the executor's manual pass, the
re-derivation and the outputs.

## Layout

| Path | What it is |
|---|---|
| `method.py` | Orchestrator, one sub-command per stage (`uv run method.py <stage>`; see its docstring). |
| `src/cfg.py` | Frozen constants (tasks, defaults, sites, blocks, alphas, slots), paths, JSON and hash helpers. |
| `src/engine.py` | FP8 W8A8 Qwen3-8B engine (exp17) with the CRN inverse-CDF sampler, the fence stop and the S3 decode-time site with shadow rows. |
| `src/hooks.py` | The displacement-targeted prefill edit used by every prefill site. |
| `src/prompts.py` | Prompt loading and re-render check, COND/S/R spans, forced T1 prompts and TOP5 ban segments (C3d). |
| `src/gpu_main.py` | GPU driver: hardware and precision rule, units, C3d geometry, GPU tests, engine check, staged sampling. |
| `src/schedule.py` | Cells, priorities and fixed-shape batch packing (atomic S3 hooked/shadow pairs). |
| `src/screen.py` | STEP 6 screen file (canonical JSON + sha256). |
| `src/prereg.py`, `src/predictions_spec.py`, `src/commit.py` | Commits #0/#1 and the sha256 hash chain (`commitments.log`). |
| `src/label_pipeline.py` | Frozen labellers (exp11 bench, exp8 suite) with judge on disagreement; follows the raw rows. |
| `src/label_k7.py` | exp9 extended / K=7 labeller for every T1 row (C3d). |
| `src/hull.py` | Rarefied Hill, randomisation hull (H5, P15, P20) and the C1-site decision rule (committed in #1). |
| `src/analysis.py` | STEP 11: cells, hull bootstrap, C1-site, failure modes, paired flips, transmission, pooled model, boundary, engine check, C3d scoring, units summary. |
| `src/audit.py` | STEP 12: known-solution index (+T05), stress tests, judge controls, blind judges + tie-break, summary; dependency usage. |
| `src/recheck.py` | STEP 0.1: inputs SHA256SUMS, bench vs commitment, labeller re-check on references and gold sets. |
| `src/figures.py`, `src/outputs.py`, `src/finalize.py` | Figures, `method_out.json`, deviations/timing/commit-order audit. |
| `audit/rederive.py` | Independent re-derivation of the headlines and three placebos (separate code path). |
| `audit/rederive_headlines.py` | Second re-derivation from raw files with different methods (Mantel-Haenszel, hand McNemar) and placebos. |
| `reproducibility.md` | What was actually run, in order, with hardware, seeds, runtimes and the numbers a rerun should give. |
| `audit/manual_pass.jsonl` | The executor's manual verdict on every stress-passing audit program. |
| `audit/novelty_audit_pool.json` | Audit pool with stress results, judge and tie-break verdicts and nearest known solutions. |
| `tests/test_cpu.py`, `tests/u4_diagnostic.py` | CPU unit tests T1-T5; the U4 follow-up diagnostic (GPU). |
| `tools/` | `overlap_check.py` (STEP 11.10, runnable later), `tables.py` (README tables), `manual_view.py`. |
| `inputs/` | Read-only copies of every earlier-artifact file this run reads (`inputs/SHA256SUMS`). |
| `units/`, `directions/` | Per-site units; u_top5 and the plan-site geometry (PCA-50 points, centroids). |
| `predictions/` | Commit #0 protocol, commit #1 predictions, frozen forced-prompt list. |
| `data/samples_raw.jsonl` | Every generated row (text, token ids, finish reason, realised displacement, first-token KL). |
| `data/labels.jsonl`, `data/labels_k7.jsonl` | Labels (label, passed, runtime/AST/judge labels, code); K=7/extended labels for T1. |
| `data/row_logs.jsonl` | Per-row displacement logs (R at blocks 12-35, along-u and total at the site, S3 step-wise KL/displacement). |
| `data/known_solutions.jsonl` | Known-solution index rebuilt from the dataset dependency (472 + 42 T05 rows). |
| `results/` | All analysis JSON (see the results section), timing, tests, costs, deviations. |
| `figures/` | fig1-fig7 (PDF + PNG). |
| `method_out.json`, `full_/mini_/preview_method_out.json` | Final output (exp_gen_sol_out schema, validated). |
| `pyproject.toml`, `uv.lock` | Pinned environment (Python 3.12; torch 2.8.0, transformers 4.57.6, the exp17 pins plus ijson). |
| `commitments.log` | sha256 hash chain of every pre-registered and final file (commits #0-#4). |
| `restore.sh`, `.aii/manifest.yaml` | Restore commands; the manifest marks the regenerable caches (`.venv/`, `__pycache__/`) for deletion (everything else is text or small and always kept). |

## How to run

```bash
uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml
export HF_HUB_CACHE=...            # holds Qwen/Qwen3-8B at the pinned revision
export ART_J3RM_DIR=...            # folder with the dataset dependency's full_data_out.json (audit index only)
export OPENROUTER_BASE_URL=... OPENROUTER_API_KEY=...   # labelling judge on disagreement, novelty audit
uv run method.py tests-cpu && uv run method.py screen
uv run method.py gpu &             # waits for commit #0, then for commit #1 before decisive sampling
uv run method.py commit0           # after GPU prep wrote units/ and results/hardware.json
uv run method.py commit1           # predictions + decision code
uv run method.py label &           # label worker
uv run method.py k7 && uv run method.py analysis --boot 2000 --workers 5
uv run method.py audit && uv run python tools/manual_view.py --neigh   # then write audit/manual_pass.jsonl
uv run method.py audit-summary && uv run method.py deps && uv run method.py rederive
uv run method.py u4 && uv run method.py figures && uv run method.py outputs
```

A GPU with FP8 support (compute capability >= 8.9, >= 16 GB) is required for the engine as written.

## Deviations from the plan

- **D1-precision**: FP8 W8A8 (exp17 engine) instead of the bf16 the plan expected on an RTX A4500. *Why:* the machine has a 16 GB RTX 2000 Ada (compute 8.9); the frozen precision rule (commit #0) maps Ada < 19.5 GiB to the exp17 FP8 W8A8 path; every arm uses it. *Cost:* C1-site statements are 'in FP8 W8A8'; the engine check compares like with like (FP8 vs FP8) and reproduced the screen byte for byte.
- **D2-batch**: fixed batch B = 20 rows for every task and max_new 1024 for every task (plan: B 16/12 and 1,536 for T1/T2 on a 20 GiB card). *Why:* exp17's U1b-verified shape on this GPU; keeps the screen's uniforms and shape for the engine check; U6 peak 13.2 GiB. *Cost:* rows longer than 1,024 tokens are truncated: 0 of 466 twin rows, 4 of 2,760 rows at alpha <= 2, 47 of 1,150 at alpha 4, 0 at alpha 8 (finish_reason per cell in results/cells.json).
- **D3-cond-span**: COND includes the token where the tokenizer merges the sentence's final '.' with the '\n\n' separator. *Why:* the separator cannot be excluded without also excluding the period. *Cost:* none for the S2 target (the ban-twin displacement there is measured, not assumed).
- **D4-U4**: U4 shadow fidelity vs an independent batch-1 teacher-forced forward fails the 1e-2 threshold. *Why:* see results/u4_diagnostic.json: FP8 decode-path states differ from a teacher-forced prefill of the same tokens even with no edit; the shadow is the exact clean reference WITHIN the decode path (U2: S3 at alpha 0 reproduces the twin byte for byte; U3: along-u displacement vs the shadow = target within 0.01%). *Cost:* S3's reference state is 'clean decode-path state', not 'teacher-forced state'; the contrast with the hooked row is exact.
- **D5-first-token-kl**: first-token KL is degenerate (the first generated token is always the code fence, p ~ 1 in every arm). *Why:* the prompt asks for one ```python block. *Cost:* the transmission analysis rests on the realised displacement at R (block 35); the KL model is reported as uninformative; S3 keeps its step-wise KL (steps 1-32).
- **D6-analysis-commit**: commit #1 (before the first decisive sample) holds the predictions, every decision rule and threshold, and the hull + C1 decision code (hull.py); analysis.py, outputs.py, figures.py, audit.py, label_k7.py and audit/rederive.py were written while sampling ran and committed in #2 before being run on the full data. *Why:* time budget; the GPU would otherwise have idled. *Cost:* rules for everything outside hull.py are fixed by predictions.json text, not by code hashes.
- **D7-direction-seed**: protocol v4's hash(task, arm, slot) is read with arm = the PN family ('PN4'), so one direction per slot is shared by every site, dose and boundary arm. *Why:* plan STEP 3. *Cost:* none (stated).
- **D8-top5-control**: the 'norm-matched random direction' control of the TOP5 push is a distribution of fresh per-slot directions at the same per-position norm (S0 rows, k 0-9), not one draw; u_top5 is per block while PN shares one u across blocks. *Why:* plan P6. *Cost:* none (stated).
- **D9-judge-ids**: novelty-audit judges are exp18's recorded ids (google/gemini-2.5-flash-lite, openai/gpt-4.1-mini); tie-break deepseek/deepseek-chat-v3.1 (exp9's tie-break model). *Why:* the plan names 'exp18's ids'; its parenthetical 'gemini-2.5-flash' differs from what exp18 actually used. *Cost:* none.
- **D10-exp13-units**: exp13's FP8 units differ from this artifact's by median ratio 1.12-1.32 (exp17's: 0.99-1.00). *Why:* exp13 built its own twins/padding. *Cost:* logged as unit drift; exp17 (same prompts) agrees to 0.2%.
- **D11-screen-twins**: exp13 rand1-3 rows are compared with exp13's hf_twin (same HF engine) in the screen file. *Why:* engine-matched baseline. *Cost:* none.
- **D12-judge-cache**: labelling judge caches started empty (exp17's caches were not copied). *Why:* oversight. *Cost:* a few cents of extra judge spend.
- **D13-invalid-harmonised**: 'invalid' = no code block, syntax error or no solve() for EVERY task (the bench labeller's rule; the exp8 path labeller otherwise labels non-programs such as '[your_answer]'). *Why:* the plan defines 'invalid' as its own column; at alpha 8 the model often writes placeholders. Introduced AFTER commit #2, after inspecting alpha-8 outputs, and applied to every arm; committed in #3 with the final analysis code (units summary, argmax robustness to a missing site, an explicit name for the failure-mode case the frozen rule leaves uncovered). *Cost:* attempt-level shares only; correct-only results (Hill, H5, C1-site, C3d) are unaffected because such programs never pass.
- **D14-k7-judge-cap**: exp9 K=7 labeller judge cap USD 0.10 (exp9 default 0.70). *Why:* share of the plan's labelling-judge budget. *Cost:* none: K=7 judge spend was USD 0.066 and no row fell back (labeller_source: agree 763, judge 181, no_code 22).
- **D15-budget-gate**: the stage-100 projection used by the budget gate (0.37 h; results/timing_projection.json) was computed on the first five batches, which were fast T05 batches. *Why:* alpha-4 S2/S3/S4 and S1E batches later ran to the full 1,024 tokens (~67 s each); the realised decisive sampling took 1.69 h wall time (1.74 GPU-hours of batch time including tests, engine check and smoke), still inside the plan's 2.0 h gate, so no cell was dropped. *Cost:* none; the gate's projection rule should use per-arm-type timings (logged for the next run).
- **D16-overlap-null**: the STEP 11.10 overlap check's template-resampling null was added after commit #3 (the first version reported JS without a null). *Why:* the plan specifies the null; exp19's Step-1 rows turned out to exist. *Cost:* none: the comparison is descriptive and committed in #4.

## Costs and timing

- GPU: 1.74 GPU-hours of batch time (265 batches of 20 rows) on one RTX 2000 Ada 16 GB. Per-row seconds by task: T03 0.86, T2 1.35, T1 1.60, T05 0.92, T06 0.98, T10 1.28.
- OpenRouter: USD 0.193 in total. Labelling judges: paths 0.109, bench 0.006, K=7 0.066. Novelty audit with controls: 0.012. Artifact cap: USD 1.00.

## Restoring removed files

`.aii/manifest.yaml` marks only regenerable bulk for deletion:

- `.venv/`: `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml`
- `src/__pycache__/`, `tests/__pycache__/`, `tools/__pycache__/`: Python byte-code caches, recreated automatically when any stage runs.

The model weights live in the run's shared Hugging Face cache, not in this folder: `huggingface-cli download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218`. `restore.sh` runs these commands. Everything else (data, results, units, directions, predictions, audit, figures, inputs) is kept. No file in this folder is 100 MB or larger, so the published repository is complete.
