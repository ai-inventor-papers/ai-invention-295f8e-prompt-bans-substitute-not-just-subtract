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

{{TABLE:c1}}

H5 = the best Hill-1 within 0.05 pass-rate cost of the twin. P15/P20 = the cheapest pass-rate cost that reaches
Hill 1.5/2.0 ('n/a' = not reached at any mixture):

{{TABLE:p15}}

- **Decision (frozen rule).** Per task, best site = argmax H5 rounded to 0.01. Ties go to the lower P15. On T05,
  S0 and S3 tie at 1.28 and S3 wins on P15 (0.12 vs 0.53). Count of tasks where S0 is best: 3, below the
  pre-registered 4, so the claim is not CONFIRMED. It is not DISCONFIRMED either: no other site reaches H5 >= H5(S0)
  on 4 tasks (S3: 2, S4: 1, S1/S2/S5: 0). Verdict: **PARTIAL**.
- **Sensitivities.** Appending alpha 8 to S0's hull, or allowing only mixtures of adjacent doses (linear
  interpolation), leaves every H5 ranking unchanged (`results/hull.json`). Within the 0.10-Hill equivalence margin,
  S0 ties the best other site on T05, T06 and T10.

**Failure mode per site (frozen rule; full numbers in `results/failure_modes.json`):**

{{TABLE:fail}}

- **Paired flips under CRN, alpha 2.** Each cell shows the number of the 30 shared slots that go off default only
  under S0, then only under the other site, with the exact McNemar p and that site's byte-identical rate vs the twin.
  S0 flips significantly more slots off default than S1, S2 and S5 on T03, T10, T1 and T2, and more than S4 on T03 and
  T10. S3 flips *more* than S0 on T06 (0 vs 12) and cannot be told apart from S0 on T03 (8 vs 6) or T05 (7 vs 2), but
  it pays in breakage: S3 is the only site whose invalid rate climbs to 0.67-1.00 at alpha 4.

{{TABLE:flips}}

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

{{TABLE:boundary}}

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

{{TABLE:c3d}}

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
