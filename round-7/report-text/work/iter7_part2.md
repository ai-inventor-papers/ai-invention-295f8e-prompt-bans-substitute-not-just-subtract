## 7.4 Where the algorithm is decided in generation (Qwen3-8B)

### 7.4.1 Design

The fork experiment [ARTIFACT:art_pHL7LWNhpcCS] asked whether one early generated token decides the algorithm, and whether the decision at that token explains which random pushes of iteration 4 change the algorithm. Forks were located by *prefix resampling*: from each base program (one written under the neutral twin, under a plan-noise push or under a ban), the model was restarted at positions along the program's first 128 tokens, and eight continuations were sampled and labelled at each. A *change point* is a position where the off-default share of the continuations changes significantly; a fork is a change point on the *shared opening*, the token sequence that most twin programs share before they part. Where no fork exists the committed fallback is the *opening log-likelihood ratio* (opening LLR): the teacher-forced log-likelihood ratio of the opening of the runner-up algorithm to the opening of the default over the first L tokens (48 on shortest path, 20 on kth smallest, whose programs are about 20 tokens long). The 40 random directions of iteration 4 were then scored for their fork margin under the push and compared with the correct off-default share y that each direction produced in bf16, the share of its programs that pass the hidden tests and implement a named algorithm other than the default; the fork margin under a push is written m.

### 7.4.2 Forks

Connected components has two forks, at generated tokens 10 and 11 of the opening `def solve(n, edges):`, which 94% of twin programs share (Tables 315 and 316). At token 10, a comment token leads to BFS or DFS in all 159 continuations, ` parent` leads to union find in all 130, ` def` leads off the default in 0.69 of 72, and ` from` leads off in all 11. At token 11, after ` def`, the routine's name settles it: ` dfs` leads to DFS in all 45 continuations and ` find` to union find in all 32. The entropy of the label given the token falls from 0.97 bits to 0.00 at token 11. Shortest path has no single fork: pushed programs stay undecided through token 60, and its only change point (token 92) lies off the default opening. On kth smallest a ban fixes the algorithm before the first generated token: at the first position only 0 to 2 of 8 continuations differ from the base program's class, and no change occurs in 128 tokens.

**Table 315.** Forks found by prefix resampling.

{{x34_forks}}

**Table 316.** Connected components: the tokens at the two forks and what follows them.

{{x34_t10map}}

### 7.4.3 The fork claim

On connected components the fork margin under each push predicts which of the 40 directions change the algorithm, at Spearman 0.80 (95% interval 0.62 to 0.91; Table 317). It separates iteration 4's 26 confirmed escapers from the rest with AUC 0.81; its Spearman with the attempted share is 0.82, and the 48-token opening LLR in place of the fork margin reaches 0.87. On shortest path the committed fallback fails: the 48-token opening LLR reaches 0.15 (p 0.18). The fork claim therefore fails as a two-task claim (Holm p 0.357) and is recorded as not supported, inconclusive. A binomial model calibrated on all 104 cells of both tasks predicts held-out shares with mean absolute error 0.25, against a committed 0.10. The record of each cell is in Tables 318 and 319. Two checks qualify the connected components result. A placebo that shuffles the map from fork tokens to outcomes still reaches the observed 0.80 in 18% of 200 permutations (median 0.22): with four or five mapped tokens per fork, the margin's power comes from the probability of staying on the default fork tokens, not from the exact outcome rates of the other tokens. And the resampling screen is sparse: in simulation, a jump of 0.4 in the off-default share with only three screen positions before it was detected in 54% of runs, so weak or very early forks can be missed.

On kth smallest a prospective test was committed before generation. The 20-token opening LLR of 24 fresh directions predicts their correct off-default share at Spearman 0.60 (one-sided p 0.0014), and 18 of the 24 directions move at least one program (Table 320). The failure on shortest path is a matter of where the decision falls: the Spearman of the opening LLR with the share rises from 0.15 at 48 tokens to 0.42 at 160 (p 0.0032; Table 325), as it should if shortest path decides late.

[FIGURE:fig_fork_margin]

**Table 317.** The fork claim on connected components (fork margin) and shortest path (48-token opening LLR).

{{x34_F}}

*Note to Table 317.* {{x34_Fcal}}

**Table 318.** Every non-direction cell scored for the fork claim.

{{x34_cells}}

**Table 319.** The 40 random directions of iteration 4 at alpha 2: margin and outcome.

{{x34_dirs}}

**Table 320.** Kth smallest: the prospective confirmation on 24 fresh directions.

{{x34_t03}}

*Note to Table 320.* {{x34_t03_sum}}

### 7.4.4 The axis claim

The axis claim proposed that random pushes act through a direction from the default centroid toward the runner-up centroid in the prompt states. It is disconfirmed. The projection b of each push on the axis predicts the outcome at Spearman 0.17 on connected components and 0.01 on shortest path (Holm p 0.458), and it is ahead of none of its committed competitors, which include the push's energy in the forced-prompt subspace of iteration 4 and its raw norm (Table 321). The layer profile shows no block where it would do better (Table 322). The axis is not dormant: neutral prompts vary along it 220 to 400 times more than along random directions. It is simply not the channel the random pushes use.

**Table 321.** The axis claim and its competitors.

{{x34_P2}}

**Table 322.** The axis projection's Spearman with the outcome, block by block.

{{x34_layers}}

### 7.4.5 Necessity and sufficiency of the axis

Clamping the axis component of each escaping push at blocks from the axis layer to 35 removes nothing: 105 escapes with the clamp against 104 without it and 106 with a random-direction clamp (Table 323). Pushing along the axis itself is a different matter (Table 324). Doses s are counted in units of the distance between the default and runner-up forced-prompt centroids along the axis. At the committed doses (s up to 1) nothing escapes on any task. At four times that distance, beyond the committed range, connected components switches to DFS in 29 of 30 slots and BFS in the 30th, with all 30 programs passing, while the matched random direction moves none (30:0, p 1.9e-9). The axis edit at that dose has 0.55 of the norm of the median escaping random direction. On shortest path the axis does nothing even at eight times the distance (1 of 30), and on kth smallest the axis at eight times the distance moves 5 of 30, exactly as many as the random direction. On connected components the axis is a sufficient control direction without being the path random pushes take.

**Table 323.** The mediator clamp, per direction.

{{x34_clamp}}

*Note to Table 323.* {{x34_clamp_sum}}

**Table 324.** A targeted push along the axis against a matched random direction, by dose.

{{x34_targeted}}

*Note to Table 324.* {{x34_targeted_ref}}.

### 7.4.6 Forcing the fork token

Forcing tokens under the unchanged neutral twin separates the routine's name from the fork position (Table 326). On connected components, forcing ` def dfs` at tokens 10 and 11 gives DFS in 30 of 30 slots, and ` def find` gives union find in 30. Forcing a comment token at position 10, which led off the default in every resampled continuation in which it appeared, gives union find in all 30 twin slots; forcing ` from` moves 10 of 30. The token that names the routine decides; a token that only correlates with pushed states in resampling does not decide on its own. On kth smallest a forced comment as the first body token moves 5 of 30 (p 0.0625), and on shortest path no forced token moves anything.

**Table 325.** Shortest path: Spearman of the opening LLR with the outcome, by opening length.

{{x34_llr}}

**Table 326.** Forced opening tokens under the unchanged twin.

{{x34_force}}

### 7.4.7 The top-five prohibition inside the manifold

The review asked for the top-five push at a dose that stays on the forced-prompt manifold of the grid task. The fork experiment pushed the twin's states toward the survivor-region centroid, toward a random survivor, away from the banned centroid and toward IDA*, at a quarter, a half and one times the distance between centroids (Table 327). All 300 programs implement BFS, at pass rates between 0.73 and 0.93; none implements an algorithm outside the banned five. The prompt top-five ban of iteration 6 had at least moved the model between BFS and DFS (25 and 23 of 50). On the manifold at block 18, three survivors (bidirectional BFS, unit-weight Dijkstra and IDA*) sit at its edge, and the nearest centroids to the banned region are greedy best first, BFS and A* (Table 328; Isomap stress 0.24, metric MDS stress 0.38). Moving the states toward where those survivors' forced prompts sit does not make the model write them. The engine reproduced the engine control's per-direction outcomes (Spearman 0.95 on connected components and 0.93 on shortest path; Table 329), and the two programs sent to novelty audit were labeller misses. One GPU unit test missed its tolerance: teacher-forced and cached-prefill log-probabilities differ by up to 0.25 on the top 50 tokens, with the same argmax, so every margin was computed on the teacher-forced path.

**Table 327.** The grid task: pushes inside the forced-prompt manifold toward the survivors of the top-five ban (30 slots each).

{{x34_top5}}

**Table 328.** The grid task: geometry of the forced-prompt manifold at blocks 18 and 22.

{{x34_top5geo}}

**Table 329.** The fork and axis statistics remeasured on this engine's own outcomes.

{{x34_remeasure}}

## 7.5 Temperature acts through the fork (Qwen3-8B)

### 7.5.1 Design

The temperature experiment [ARTIFACT:art_MZAfDPVhM6Ui] tested the temperature claim where it can be tested: on the three units where the instruct twin already writes two algorithms. Minimum spanning tree weight mixes Kruskal and Prim, trapped rain water mixes prefix and suffix maxima with two pointers, and valid anagram mixes sorting with counting. Iteration 5 had recorded minority shares of 0.34, 0.36 and 0.24; this experiment's twins give 0.19, 0.31 and 0.13 on byte-identical prompts (Table 330). The claim has three committed tests. Test 1: the entropy of the algorithm given the class of the token at the fork is at most 0.3 bits on at least two units. Test 2: predictions made from the teacher-forced fork logits divided by T, committed before any temperature sample, match the observed minority share (drop from T 1.0 to 0.3 of at least 0.15, mean absolute error at most 0.10, and the change from 1.0 to 1.3 within 0.10 of prediction) on at least two units. Test 3: on the four collapsed tasks the fork margin is at least 4 nats, large enough that no temperature in range reaches the alternative. Every temperature cell shares its random numbers across temperatures (same seed), at temperatures 0.3, 0.7, 1.0 and 1.3, under top-p 1 and top-k 10.

**Table 330.** The twins of the three mixed units.

{{x35_twins}}

### 7.5.2 One sampled token decides, at a predictable place

Prefix resampling finds a one-token fork on every unit, at the first token after the shared opening (Table 331). On minimum spanning tree weight it is the word after `    # ` once the adjacency list is built: ` Kr` has probability 0.72 and leads to Kruskal in every continuation, ` Prim` has 0.27 and leads to Prim in 97%. On trapped rain water, after `if not height: return 0`, ` n` leads to prefix and suffix arrays and ` left` to two pointers. On valid anagram, after the length check, ` return` leads to sorting and ` count` to counting. Test 1 passes on all three units: the entropy of the algorithm given the fork class is 0.050, 0.153 and 0.189 bits (Table 332).

**Table 331.** Fork location and the calibration of the sampler at the fork.

{{x35_forkloc}}

**Table 332.** Test 1: the algorithm given the fork token's class.

{{x35_test1}}

### 7.5.3 The fork logits predict the temperature response

Test 2 passes on minimum spanning tree weight and fails on the other two units, so the temperature claim is recorded as PARTIAL (Tables 333 and 334). On minimum spanning tree weight, lowering T from 1.0 to 0.3 removes Prim from 17 slots and adds it to none (one-sided p below 1e-4); the observed drop of 0.34 is twice the predicted 0.17, and the mean absolute error across temperatures is 0.083. On trapped rain water the mean absolute error is 0.105 and the drop 0.08 (7:3), and on valid anagram the minority share does not drop (2:5), with an error of 0.043. Pooled over the first two units the drop is 24:3 (p 2.5e-5), which survives a Bonferroni correction over the seven committed tests. Three post-hoc readings qualify the misses. The per-slot replay, which walks the opening with each slot's own random numbers and reads the class of the fork token it picks, names the algorithm of an individual program in 0.90 to 0.98 of on-opening slots in every cell (Table 333, last column). On trapped rain water the replay-implied shares of the actual 50 streams (0.08, 0.18, 0.18 and 0.16) reproduce the observed sweep (0.10, 0.18, 0.18 and 0.20), so the miss there is the gap between a cell of 50 streams and its expectation, not a failure of the mechanism. On minimum spanning tree weight the sweep's 50 streams are Prim-heavy at T 1.0 (0.40, against 0.20 for the twin's own slots, Fisher p 0.011), which is why the observed drop is twice the predicted one. On valid anagram the prediction itself had said the drop would be small: one template prefers ` count` even greedily, and about 19% of samples leave the opening at every temperature. Above T 1.0 nothing is added on any unit: the observed change from 1.0 to 1.3 is between -0.02 and +0.06, and the predicted change is at most 0.013, because what the minority gains at the fork is offset by samples that leave the canonical opening as T rises (on minimum spanning tree weight the predicted on-opening share falls from 0.72 at T 1.0 to 0.55 at 1.3). Across all temperatures the ideas stay the two or three known algorithms of each unit; only phrasings multiply (Table 340). Top-k 10 gave the same program as top-p 1 in all 600 paired slots, because every token at the fork lies in the top 10.

[FIGURE:fig_temperature_fork]

**Table 333.** Test 2: predicted against observed minority share by temperature and sampler.

{{x35_test2}}

**Table 334.** Test 2 by unit.

{{x35_test2sum}}

### 7.5.4 The collapsed tasks

Test 3 passes: on the grid, shortest path, connected components and kth smallest the fork margin of the twin is 7.46, 4.85, 17.04 and 6.10 nats (Table 335). At T 1.3 the predicted off-default rate is at most 0.02 on every task, and 100 samples at that temperature produced no off-default program on any of them; a further check of 20 samples found one off-default program on the grid and one on shortest path; the shortest path one fits its predicted rate, and the grid one is unlikely under its margin (binomial p 0.04). The record of iterations 1 to 4, 797 of 800 default programs and no same-seed flips, implies margins of about 6 nats. The temperature nulls of iterations 1 to 4 are what the fork logits predict: on the collapsed tasks the alternative lies 5 to 17 nats behind at the fork, and dividing by 1.3 does not bring it within reach.

**Table 335.** Test 3: fork margins of the collapsed tasks and the bound they imply.

{{x35_test3}}

### 7.5.5 What does move the fork

Exchanging the task-specification states of a prompt that names the minority algorithm into the twin gives that algorithm in 30 of 30 slots on all three units, against 0 to 7 under the padding twin, the forced prompt with its instruction replaced by padding tokens so that positions align (exact one-sided p of 1.2e-7 or less; Tables 336 and 337). The argmax token at the fork flips with it (` Kr` to ` Prim`), and the fork margin moves by 4.9 to 22 nats toward the minority, against 2 nats or less for a matched random exchange. Eight random pushes of the task-specification states at alpha 2 move the minority share in the direction their fork-margin change predicts (Spearman -0.69, -0.44 and -0.94 between margin change and share change; Tables 338 and 339). The committed permutation test used the upper tail, the side opposite to the predicted negative relation; the lower tail is reported beside it as a post-commit correction.

**Table 336.** Exchanging the forced minority prompt's task-specification states into the twin.

{{x35_s4b}}

**Table 337.** The exchange against the padding twin and against a matched random exchange.

{{x35_s4b_tests}}

**Table 338.** Random pushes of the task-specification states: margin change and minority share per direction.

{{x35_s4a}}

**Table 339.** Random pushes by unit.

{{x35_s4a_sum}}

### 7.5.6 Question 1a-c of the request

The request's question 1a-c asks whether, with the seed fixed and top-k 10, a tight temperature gives one idea in many phrasings or many ideas, and whether loosening it multiplies ideas or phrasings. On the mixed units a tight temperature collapses onto the default idea, and loosening it restores the second idea at its natural rate, never more, while the phrasings within each idea multiply (Table 340): Kruskal programs on minimum spanning tree weight form 3 phrasing clusters at T 0.3 and 7 at T 1.3. No third idea appears at any temperature. In Gemma, where few samples leave the opening, T 1.3 does raise the minority above its natural rate, as its fork logits predicted (Section 7.8.2). Hill-1 of the correct ideas on minimum spanning tree weight rises from 1.25 at T 0.3 to 1.95 at T 1.0 and stays at 1.92 at 1.3; ten literal trajectories at T 0.3 give 9 Kruskal and 1 Prim. The only correct programs off the catalogue are 40 continuations from one low-probability fork token on valid anagram; they form 2 distinct programs, both the catalogue's extra counting mode, and are catalogue variants.

**Table 340.** Ideas and phrasings across temperature (same seed; Hill-1 at depth 25).

{{x35_1ac}}

