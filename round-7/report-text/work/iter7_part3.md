## 7.6 The dose unit, not the seeds, made iteration 5's plan noise weak (Qwen3-8B)

### 7.6.1 Design

Iteration 4 found plan noise strong under its *absolute unit*, in which each cell (block and position) receives a random direction scaled to the displacement a ban itself causes at that cell. Iteration 5 found it nearly inert under its *ban-free unit*, which scales the direction to a fixed fraction of the twin's own residual norm at each cell, and with different direction seeds. Section 6.3 showed that the 8-bit engine was not the cause. The dose-unit experiment [ARTIFACT:art_8O5eaNc5gxJs] crossed the two units with the two seed sets in bf16, on the same 50 slots per design, and committed a decision rule before the first row: the answer is the unit if the main effect of the unit is positive with its interval above zero and the effect of the seeds lies within plus or minus 0.10. Two anchors reproduce the earlier artifacts on the same slots: the absolute unit with iteration-4 seeds gives 26 of 50 attempts against 25 in the engine control (per-slot agreement 0.98), and the ban-free unit with iteration-5 seeds gives 1 of 50 against 1. Iteration 5's null is thus reproduced without its left padding, so the decoding path is not the cause either.

### 7.6.2 The 2x2

The answer is the unit (Table 341). On connected components at alpha 2, the absolute unit gives a correct off-default share of 0.50 and 0.52 under the two seed sets, and the ban-free unit 0.10 and 0.02: a unit effect of +0.45 [0.35, 0.55], a seed effect of +0.03 [-0.07, 0.14] and an interaction of -0.10 [-0.28, 0.08]. A conditional logistic regression with slot strata agrees (unit coefficient 4.34, p 1e-4; seeds 1.68, p 0.13). On shortest path, at 100 slots, the unit effect is smaller (+0.115 [0.06, 0.17]) and most attempts under the absolute unit fail the hidden tests (13 correct of 41 attempted at pass 0.66; Table 342). On 50 fresh connected components slots the unit effect replicates (+0.42 [0.32, 0.52]), and on kth smallest it is +0.27 [0.18, 0.37] with a seed effect of +0.03 (Tables 346 and 347). On kth smallest, unlike connected components, the ban-free unit does move the algorithm, at half the absolute unit's rate.

[FIGURE:fig_unit_seed]

**Table 341.** The 2x2 on connected components at alpha 2.

{{x36_2x2}}

**Table 342.** Every 2x2 cell (Y, correct off-default programs with Wilson 95% interval; A, attempted off-default).

{{x36_cells}}

### 7.6.3 Why the units differ

The two units differ in where the energy sits. The absolute unit is peaky: on connected components its top quartile of cells holds 81% of its energy, on bands of a few task tokens, and its largest cell receives about 2.1 times that cell's residual norm. The ban-free unit is flat by construction: its top quartile holds 42%, and its largest cell receives 0.25 times the residual norm. A fifth design applies the per-position profile of the ban-free unit at the per-block energy of the absolute unit; it moves 0.28 on connected components, between the two, so the profile (+0.22 [0.08, 0.36], McNemar 13:2) and the energy (+0.18 [0.06, 0.30], 10:1) each carry part of the effect.

A split of the absolute unit by cell confirms that the peaky cells matter (Tables 343 and 344). At the same total energy, the top-quartile cells alone move connected components in 29 of 50 slots, the other three quartiles in 15 (18:4, Holm p 0.01), and the same energy at shuffled positions in 4 (21:0 against the full unit). On shortest path the other three quartiles include the massive-activation cell at position 87 (the token `0`, norm about 10,290, 82% of the unit's energy there); noise on them breaks every program (pass 0.00), and the top quartile alone moves 5 of 50. Sweeping the dose of the ban-free unit shows that it comes close to the effect of the absolute unit on connected components only near alpha 4 (20 of 50 at pass 0.98, against 25 for the absolute unit at alpha 2), and that at alpha 6 the programs break (pass 0.46; Table 345). At alpha 4 it pays 1.8 times the downstream displacement of the absolute unit at the read position (423 against 240), and at a matched dose at block 12 (alpha 3, 13.6 against 13.8) it moves only 9 of 50 (McNemar 1:17 against the absolute unit). On shortest path it never moves more than 5 of 50 before the programs break.

The size of the downstream displacement does not explain the difference. At alpha 2 the realised displacement at block 35 is about the same under the two units, at the read position and at the first generated token, yet the absolute unit escapes 5 to 25 times as often. Adding the log block-35 norms to the per-sample logit leaves the unit coefficients unchanged on connected components (-2.35 to -2.54 for the ban-free unit with iteration-4 seeds, -3.31 to -3.49 with iteration-5 seeds). And the top-quartile arm has the smallest downstream displacement of all pushed arms while moving the most. An exploratory analysis of individual samples found that which samples escape is close to a coin flip for a given direction and token stream: two directions on the same common random numbers agree weakly (phi coefficient 0.16 to 0.20 on connected components, about 0 on shortest path), the same direction is not monotone in dose (escape at alpha 2 given escape at alpha 1 in 2 of 6 samples, against a marginal 0.52), and neither the size nor the direction of the block-35 displacement predicts escape within the absolute unit (cross-validated AUC 0.40 to 0.53). The unit sets the rate of escape; single outcomes behave like per-sample random variables.

**Table 343.** The absolute unit split by cell, at the full unit's total energy.

{{x36_s2}}

**Table 344.** Tests of the cell split.

{{x36_s2tests}}

**Table 345.** The ban-free unit swept in dose, beside the absolute unit.

{{x36_e1}}

**Table 346.** Connected components on 50 fresh slots (exploratory replication).

{{x36_e3a}}

**Table 347.** Kth smallest at alpha 2 (exploratory third task).

{{x36_e3b}}

### 7.6.4 Plan noise re-priced at the unit that moves

At the absolute unit with iteration-4 seeds, plan noise was priced against the five text-level knobs of iteration 5 on five tasks (Tables 348 to 351). We call the price measure the 5-point Hill-1: the Hill-1 number of distinct correct algorithms reachable within a pass cost of 5 points along the dose range of each knob. Beside it we report the pass cost of reaching Hill-1 of 1.5 and 2. Plan noise beats an intent sentence written by the base model (base intent) on kth smallest (3.22 against 1.73) and the grid (1.39 against 1.05), and loses on connected components (2.13 against 2.53), shortest path (1.21 against 1.45) and two sum (1.10 against 1.61). The committed prediction was 3 of 5 and the result is 2 of 5. Iteration 5's comparison, which plan noise had lost at the ban-free unit, is reversed in its mean (the margin of plan noise over the best text sampler moves from -0.40 to +0.12 [-0.18, 0.27]) but not in its rule: the iteration-5 rule replayed at the absolute unit is still disconfirmed, 2 of 5. Temperature 1.3 and top-k 10 reach Hill-1 of at most 1.09 on every task. The six verdicts that the record audit tagged as resting on the ban-free unit are now re-tagged: at the design that moves (the absolute unit with iteration-4 seeds at alpha 2), kth smallest (+0.58) and connected components (+0.50) are movable, and shortest path (+0.16, at pass 0.62 against the twin's 0.98), two sum (+0.02) and the grid (+0.08) are not. Five correct kth smallest programs labelled other count frequencies in a hash map and walk the sorted distinct keys by cumulative count; they are counting sort with key compression, a catalogue variant. Of the 25 pairs of task and text knob, 17 reproduced the iteration-5 labels in 10 of 10 check slots and reuse its rows, and 8 were regenerated in this engine; the 250 base-model intents were identical in text and token ids to iteration 5's. Against the exchange experiment's engine, labels and pass agreed in 15 of 16 slots on shortest path and kth smallest, 40 of 40 on connected components and two sum, and 34 of 40 on the grid (all BFS, with 6 pass flips), which the artifact logs as kernel sensitivity across GPUs.

**Table 348.** The 5-point Hill-1 of plan noise against the text-level knobs.

{{x36_prices}}

**Table 349.** The 5-point Hill-1 with bootstrap intervals and the pass cost of reaching Hill-1 of 1.5 and 2 (as a fraction of the pass rate).

{{x36_s3}}

**Table 350.** Plan noise against base intent and against the best text sampler.

{{x36_s3read}}

**Table 351.** Every pricing cell.

{{x36_s3cells}}

**Table 352.** The dose-unit experiment's committed predictions.

{{x36_pred}}

## 7.7 Evolutionary search with an evaluator (Qwen3-8B)

### 7.7.1 Design

Six iterations of single-sample generation had produced no correct novel algorithm. The search experiment [ARTIFACT:art_VhaHGe7SxV95] tested the documented alternative [81, 82]: an evolutionary program search in which the model mutates parent programs and an executable evaluator keeps the correct ones. The search uses four islands, each with a MAP-Elites archive [133] whose cells are the runtime label and a data-structure signature; each round draws two parents per prompt by a Boltzmann choice over cells, asks for four children per prompt, and resets the worst island every 500 calls. The *evaluator* runs each program in an isolated subprocess with memory and time limits through 8 quick cases, the full hidden suite and 10 maximum-size stress inputs; a program that hard-codes hidden answers fails the stress stage. A *novelty critic* compares each program, as hashed 4-gram shingles of its identifier-normalised tokens, with 18,237 known solutions from 10 datasets, and a program passes the *out-of-catalogue screen* if it is correct and either labelled other or less similar to every known solution than the 5th percentile of the forced catalogue programs (Table 353). Two levels are counted: level a, distinct screen-passing programs, and level b, programs that adjudication places outside the catalogue (a known technique outside it, or novel).

The comparison arms use the same evaluator, labeller and critic: no evolution (the same prompt with frozen seed parents, the AlphaEvolve ablation [82]), the novelty instruction with no parents, enumerate and pick, base intent, the neutral twin, and a larger mutator (qwen3-235b through OpenRouter, 500 calls). The committed prediction was that search reaches at least 10 times the level-a rate of the better of enumerate and pick and base intent, on at least two of shortest path, kth smallest and trapped rain water.

**Table 353.** The similarity threshold of the screen, per task.

{{x37_sstar}}

### 7.7.2 Results

The search claim is not met at either level (Tables 354 to 356). At level a, search beats enumerate and pick by 3.83 times on shortest path, 6.65 times on kth smallest (lower bound 4.86) and 0.91 times on trapped rain water. At level b only kth smallest produces any program: 78 distinct programs from search against 0 from enumerate and pick (lower bound 12.8), 0 from no evolution and 2 from the instruction alone. The level-b gain on kth smallest comes from evolution: against no evolution with the same prompt it is 78 to 0 (lower bound 5.1), and 66 of the 93 level-b rows sit at depth 2 or more with non-seed parents (Table 362). At level a on kth smallest most of the gain is the instruction's: the instruction alone beats enumerate and pick by 4.6 times, and search beats the instruction alone by 1.45 times.

The programs outside the catalogue are known techniques (Tables 357 and 358). On kth smallest, 103 distinct programs implement Fenwick-tree order statistics, binary search on the value range, bucket select, partial selection sort and an order-statistic treap; 540 are catalogue variants. On shortest path the 15-fold lead of search over no evolution at level a is restyled SPFA: every adjudicated program is a catalogue variant or degenerate, and two of them pass every test while being wrong in general, because they deduplicate on distance modulo a constant. On trapped rain water search loses to both no evolution and the instruction alone. No program is novel: the rule-of-three bound [67] is 7.5% over the 40 merged adjudicated clusters and 0.16% per correct search program on kth smallest.

**Table 354.** Counts per task and arm.

{{x37_counts}}

**Table 355.** The primary test: search against the better text knob (enumerate and pick on every task).

{{x37_primary}}

**Table 356.** Every level-a and level-b rate test.

{{x37_tests}}

**Table 357.** Final classes of the distinct screen-passing programs.

{{x37_classes}}

**Table 358.** The known techniques outside the catalogue (kth smallest).

{{x37_named}}

### 7.7.3 Adjudication, the larger mutator and robustness

The judge gate failed: no judge family reached 9 of 10 on the controls of known class (Table 359). Every judge called the D'Esopo-Pape control a variant of SPFA, and three of five called a decreasing-height control novel. Under the committed fallback the final class of every candidate is the executor's manual read (121 full reads and 123 structured reads). The reads were not blind to arm, so a rule-based reclassification blind to arm was run; it agrees with the manual classes on 94.4% of 816 distinct programs and reproduces the level-b contrast on kth smallest (87 of 2,500 against 2 of 1,250, lower bound 6.7). The pair of judges fixed in advance was still run as advisory votes, with kappa 0.42; all 11 of their novel calls were overturned on reading (dead-code tournaments, partial selection sort and SPFA on a lifted graph).

The larger mutator, over its 500 calls, reaches level a at 0.84 times the rate of the first 500 calls of search and level b at 2.6 times (23 against 9, lower bound 1.28; Table 360). It writes mostly quickselect (402 of 441 correct programs), while search writes counting sort, quickselect and programs labelled other in near-equal numbers. The search rate on kth smallest is stable across islands (bootstrap 0.173 to 0.227), and at matched effort no other arm approaches search's 63 idea clusters (Table 361). An arm-shuffle placebo is significant in 1% to 6% of shuffles with median rate ratio near 1.

**Table 359.** The judge gate on ten controls of known class.

{{x37_judges}}

**Table 360.** The larger mutator against the first 500 calls of search (kth smallest).

{{x37_LvS}}

*Note to Table 360.* {{x37_LvS_tests}}

**Table 361.** Matched effort: idea clusters per arm, extrapolated to search's number of calls.

{{x37_effort}}

**Table 362.** Lineage of the search programs that pass the screen.

{{x37_lineage}}

[FIGURE:fig_search_rates]

## 7.8 Gemma: temperature, a controlled DAS and a validated circuit at the fork

### 7.8.1 Engine and calibration

The Gemma experiment [ARTIFACT:art_HY7uYZz-OjRW] returned to gemma-3-4b-it's one-token fork on the grid task, where a shared 32-token opening ends at a token that decides between DFS and BFS (Section 6.5). The engine check on 50 twin slots gave 19 BFS programs (0.38), just outside iteration 6's interval for 61 of 200 (0.245 to 0.372), so the check fails as preregistered; iteration 6's own share on the same 50 slots is 0.36, so the slots, not the engine, are BFS-heavy. The empty-prefix discrepancy of iteration 6 did not reproduce: 200 continuations from the empty prefix give 65 BFS on the multi-prompt path and 72 on the single-prompt path, both consistent with the natural 61 (Fisher p 0.75 and 0.29). The two paths disagree on 9 of 200 slots (1 against 8, p 0.039), so the batch shape changes a few coupled programs; by the rule committed beforehand, the probability of BFS given each fork token comes from a calibration run on the main engine (Table 363). The fork token fixes both the algorithm and its implementation: ` visited` leads to DFS (BFS 1 of 125), and ` queue` leads to a BFS that carries whole paths and pops from the front of a list, which is BFS but too slow for the 30 by 30 hidden tests (0 of 125 pass).

**Table 363.** Calibration at the fork: the shared opening prefilled and the fork token forced (125 programs each).

{{x38_cal}}

### 7.8.2 Temperature through the fork in a second family

The temperature claim holds in Gemma (Table 364). The predicted attempted BFS share, computed from the teacher-forced fork logits divided by T and committed before any temperature sample, matches the observed share in every top-p 1 cell: 0.015 against 0.02 at T 0.3, 0.166 against 0.24 at 0.7, 0.323 against 0.34 at 1.0 and 0.450 against 0.46 at 1.3 (mean absolute error 0.026; every prediction inside its Wilson interval). The entropy of the algorithm given the fork class is 0.153 bits. Lowering T from 1.0 to 0.3 switches 16 slots from BFS to DFS and none back (p 1.5e-5), and half of all slots change their algorithm somewhere across temperature. Top-k 10 cells are identical to top-p 1 program for program. A temperature-shuffled placebo of the sweep gives an error of 0.123 and fails the 0.10 bar.

**Table 364.** Gemma: predicted against observed BFS share across temperature (same seed, N = 50 per cell).

{{x38_g3}}

### 7.8.3 DAS at the fork with the controls iteration 6 lacked

DAS at the fork was fitted on held-out templates and held-out forced sources (768 pairs). The layer was chosen by the committed rule, the argmax of rank-1 cross-validated recovery, at block 17. Swapping the whole fork state moves the held-out margin by 3.6 nats at block 17, rising to 8.2 to 9.1 nats at blocks 25 to 29; DAS at block 17 recovers 1.98, 2.36, 2.58 and 2.81 of that at ranks 1, 2, 4 and 8 (Tables 364b and 364c), because a trained direction moves the margin further than the weak full-state swap at an early block. This time the controls hold. Fifty random subspaces recover nothing (0.000). Permuting the source labels gives recovery between -0.27 and -0.30 against the true targets (one permutation of three reaches 0.17 at rank 1). A randomly initialised Gemma moves its margin at most 0.25 times as far (interchange intervention accuracy 0.50 to 0.72 against 1.00). The DAS claim's Gemma version is therefore supported at every rank, and the controls that failed for Qwen3-8B in Section 7.3 pass here.

Two limits remain. The committed wording rule does not license calling the subspace one-dimensional: rank-1 recovery passes, but the subspace coordinate tracks the natural fork log-odds of 120 twin variants at Spearman -0.50, just short of the 0.5 the rule required, and the subspace holds 0.0009 of the twin's natural cross-prompt variance, at the random 95th percentile. And the subspace is not unique: across three seeds only one direction is shared (cosine 0.50 to 0.52), and a difference-in-means direction sits at cosine 0.39 to it.

**Table 364b.** Gemma: DAS at the fork by rank, with its controls (held-out templates and held-out forced sources, 768 pairs; block 17, and block 22 for comparison). Recovery is the edit's change in the fork margin divided by that of the full-state swap at the same block; the directional effect is the change in the fork margin toward the source's class.

| Rank k | Recovery, median of 3 seeds (each seed) | Directional effect (nats) | Interchange intervention accuracy | 50 random subspaces, recovery | Permuted labels, recovery (median of 3) | Randomly initialised Gemma, directional effect (nats) | Natural variance share (random 95th percentile) | Block 22: recovery / directional effect (nats) | Block 22: random recovery |
|-|-|-|-|-|-|-|-|-|-|
| 1 | 1.98 (2.04, 1.98, 1.98) | 5.57 | 1.00 | 0.000 | -0.27 | 0.00 | 0.00093 (0.00098) | 1.08 / 6.03 | 0.000 |
| 2 | 2.36 (2.36, 2.33, 2.36) | 6.68 | 1.00 | 0.000 | -0.29 | 1.69 | 0.00116 (0.00185) | 1.32 / 7.39 | 0.000 |
| 4 | 2.58 (2.58, 2.54, 2.58) | 7.57 | 1.00 | 0.000 | -0.30 | 1.69 | 0.00187 (0.00275) | 1.51 / 8.58 | 0.000 |
| 8 | 2.81 (2.81, 2.80, 2.88) | 8.55 | 1.00 | 0.0001 | -0.28 | 1.74 | 0.00565 (0.00486) | 1.71 / 9.76 | 0.0028 |

The subspace coordinate at rank 1 tracks the natural fork log-odds of the 120 twin variants at Spearman -0.50 (permutation p 0.0005) at block 17 and -0.67 at block 22; the difference-in-means coordinate tracks it at 0.43. A rank-1 difference-in-means interchange recovers 1.01 at block 17 (directional effect 2.84 nats) and 1.06 at block 22.

**Table 364c.** Gemma: the full-state ceiling and the rank-1 layer scan by block (held-out pairs). The committed rule chose the block with the largest cross-validated rank-1 recovery; ties go to the earlier block.

| Block | Full-state swap, forced-BFS sources (nats) | Full-state swap, forced-DFS sources (nats) | Share of pairs moved by at least 1 nat | Rank-1 cross-validated recovery, median (three folds) |
|-|-|-|-|-|
| 17 | +3.62 | -1.94 | 0.97 | 2.15 (2.15, 2.26, 2.05) |
| 18 | +3.80 | -1.99 | 0.98 | not scanned |
| 19 | +4.34 | -1.89 | 0.98 | 2.07 (2.07, 2.10, 1.94) |
| 20 | +5.67 | -2.28 | 1.00 | not scanned |
| 21 | +5.36 | -2.31 | 1.00 | 1.67 (1.67, 1.80, 1.60) |
| 22 | +7.36 | -3.77 | 1.00 | 1.17 (1.17, 1.22, 1.17) |
| 23 | +6.87 | -4.16 | 1.00 | 1.20 (1.20, 1.22, 1.17) |
| 24 | +7.62 | -5.18 | 1.00 | not scanned |
| 25 | +8.19 | -5.23 | 1.00 | 1.07 (1.07, 1.07, 1.07) |
| 26 | +9.11 | -5.19 | 1.00 | not scanned |
| 27 | +8.99 | -5.65 | 1.00 | 1.09 (1.09, 1.07, 1.09) |
| 28 | +8.90 | -5.72 | 1.00 | not scanned |
| 29 | +8.81 | -5.80 | 1.00 | 1.10 (1.15, 1.10, 1.09) |

### 7.8.4 A dose dial that keeps the programs

In generation the DAS edit at block 17, applied once at the fork position with the opening prefilled, acts as a dose dial (Table 365). From the twin's 11 correct BFS programs of 50, the edit raises correct BFS to 20, 27, 31, 37, 38 and 42 as lambda rises from 0.1 to 1, at pass rates of 0.68 to 0.88; at lambda 1 it gives more correct BFS programs (42) than the explicit instruction to use BFS (35). A difference-in-means direction scaled to the same teacher-forced effect flips the algorithm just as well (up to 50 of 50 attempts) and destroys the programs (pass 0.70 down to 0.00, never significantly more correct BFS than the twin). A logit-only version of the DAS edit, which changes the fork token's distribution but not the state that persists in the cache, gives 35 correct programs: the edited fork state helps the later code. The teacher-forced prediction of the attempted share (the fork distribution times the probability of BFS given each token) matches the observed share within 0.10 in all 26 cells (mean gap 0.029). Toward DFS, the edit gives 41 to 50 correct DFS programs of 50 against the twin's 32 (Table 365b). The strong difference-in-means edit toward DFS, left unmatched by a bisection bug, keeps most programs (45 correct of 49 attempted, pass 0.90), so the class-mean edit breaks the programs when it pushes toward BFS, not toward DFS. In iteration 6, a rank-4 interchange at block 22 had produced 50 BFS attempts and 0 valid programs; a dosed edit to the class-mean coordinate at block 17 keeps them.

[FIGURE:fig_gemma_dose]

**Table 365.** Gemma: DAS against difference in means as a dose dial toward BFS (N = 50 per cell, same seed).

{{x38_dose}}

**Table 365b.** Gemma: the same edits toward DFS (N = 50 per cell, same seed; the twin writes DFS in 32 of 50). The six difference-in-means cells toward DFS were left unmatched by a bisection bug and are identical; they are reported once, as a strong reference edit.

| Cell | Attempted DFS | Correct DFS | Pass | McNemar on correct DFS against the twin (cell only : twin only) |
|-|-|-|-|-|
| twin (no edit) | 32 | 32 | 0.86 | - |
| DAS lambda 0.1 | 41 | 41 | 0.94 | 9:0 |
| DAS lambda 0.2 | 46 | 46 | 0.98 | 14:0 |
| DAS lambda 0.35 | 50 | 50 | 1.00 | 18:0 |
| DAS lambda 0.5 | 50 | 50 | 1.00 | 18:0 |
| DAS lambda 0.75 | 50 | 50 | 1.00 | 18:0 |
| DAS lambda 1 | 50 | 50 | 1.00 | 18:0 |
| difference in means toward DFS (one strong edit) | 49 | 45 | 0.90 | 14:1 |

### 7.8.5 A circuit for the fork margin

*Path patching* replaces a component's contribution along one path with its value under a contrasting input and measures the effect on the output [134, 135]; *attribution patching* (AtP) approximates the same effect for every node with one gradient pass [136]. The experiment screened 1,224 nodes (272 attention heads and 34 MLPs at four position classes: the fork position, the shared opening, the task specification and the condition sentence) by AtP on 15 contrasting pairs, patched the top 60 exactly by *noising*, which writes a node's value from the BFS-leaning run of a pair into the DFS-leaning run (AtP against exact noising: Pearson 0.65, Spearman 0.73; the reverse, denoising, has the opposite sign for every node), and path-patched edges among the top 15. Half of the exact noising effect enters at the fork position (53%) and a third at the condition sentence (36%). The top ten nodes are MLPs at the condition sentence (layers 0, 2, 6 and 14) and a stack at the fork position (MLPs at layers 17, 21, 22, 25 and 26, and head 5 of layer 22; Table 366). Kept edges, those whose path-patched effect is at least 5% of the total effect, form a chain at the fork position (MLP 17 to MLP 19, MLP 21 to MLP 22, MLP 25 to MLP 26, and head 5 of layer 22 to MLP 25), with direct paths to the margin from head 2 of layer 33 and MLPs 22, 25 and 26.

Each top node was validated in the real model against 50 random components of its position class matched on write norm (Table 367). Seven of ten nodes pass when ablated to the opposite class's mean, and eight pass when steered; the joint top-five and top-ten sets beat all 50 matched random sets. In generation, steering the top five toward BFS doubles correct BFS programs (16 of 30 against 8 for the twin, p 0.019) at pass 0.83, while a matched random five does nothing (Table 368). Ablating the same nodes to the natural BFS mean does not move generation, because the natural classes differ by only about 2 nats at the fork. The reading is a circuit hypothesis for this one fork: MLPs at the condition sentence carry the prompt's lexical cue, and the stack at the fork position turns it into the token at index 32. An *attribution graph*, the graph of direct linear effects between transcoder features from the prompt to the fork margin, built on the Gemma Scope 2 transcoders [113], would test the circuit on features; it was attempted three times and dropped: the container lacked a C compiler for Triton, and with one installed, attribution exceeded the 16 GB GPU at batch 64 and again at batch 16 (16.4 GB). No correct program among 2,325 was outside the catalogue (rule-of-three bound 0.0013).

The deviation log of the Gemma experiment records five departures that bear on these results. One unit test missed its tolerance: the single-position cache path differs from a full recompute by up to 0.27 nats on the fork margin, a bf16 kernel and batch-shape effect, so every DAS effect is measured against the base's own margin on the same path and in the same batch shape. The DAS optimiser ran at a learning rate of 2e-2 instead of the planned 2e-3, because a toy check showed that 400 steps at 2e-3 leave the subspace near random. A bisection bug left the six difference-in-means cells toward DFS unmatched, so they are reported as one strong reference edit (45 of 50 correct DFS). The mediation test of the fork subspace on random pushes was not run (dropped in order), so the DAS claim covers forced-prompt transfer only. And the transcoder graph was dropped after the three attempts described above.

**Table 366.** Gemma: the top ten nodes by exact noising effect (mean over 15 pairs).

{{x38_nodes}}

**Table 367.** Gemma: validation of each node against 50 matched random components. The effect d of a node is its oriented change in the fork margin minus the mean change under the 50 matched random components.

{{x38_valid}}

**Table 368.** Gemma: generation arms with the validated nodes (N = 30, opening prefilled).

{{x38_arms}}

## 7.9 Comparisons across this iteration's experiments

**Temperature through the fork, in two families.** The temperature claim was tested on four mixed units in two models. The fork logits predicted the temperature response within the committed error on two of them (the grid in Gemma, mean absolute error 0.026, and minimum spanning tree weight in Qwen3-8B, 0.083, where the observed drop was twice the predicted one), just outside it on trapped rain water (0.105), and not in direction on valid anagram, where the minority share did not fall at low temperature. Table 369 sets them side by side. On every unit the algorithm given the fork class was nearly certain (0.05 to 0.19 bits) and top-k 10 changed nothing. Temperature above 1 raised the minority only where the fork logits said it would: in Gemma the BFS share rose from 0.34 at T 1.0 to 0.46 at T 1.3 against a predicted rise from 0.323 to 0.450, while on the three Qwen3-8B units the predicted rise was at most 0.013 and the observed change lay between -0.02 and +0.06. On the collapsed tasks the fork margins of 4.85 to 17.04 nats explain why no temperature in iterations 1 to 4 changed the algorithm. Temperature is a dial on the fork's existing odds; it cannot create an alternative that the fork does not already weigh.

**Table 369.** The temperature claim in two model families (top-p 1, same seed).

| Model and unit | Fork token pair | Entropy of the algorithm given the fork class (bits) | Minority share at T 0.3 / 1.0 / 1.3 (observed) | Predicted | Mean absolute error | Drop T 1.0 to 0.3 (McNemar) |
|-|-|-|-|-|-|-|
| Qwen3-8B, minimum spanning tree weight | ` Kr` (Kruskal) or ` Prim` | 0.050 | 0.06 / 0.40 / 0.38 | 0.068 / 0.237 / 0.247 | 0.083 | 17:0 |
| Qwen3-8B, trapped rain water | ` n` (prefix and suffix) or ` left` (two pointers) | 0.153 | 0.10 / 0.18 / 0.20 | 0.166 / 0.311 / 0.319 | 0.105 | 7:3 |
| Qwen3-8B, valid anagram | ` return` (sort) or ` count` | 0.189 | 0.18 / 0.12 / 0.18 | 0.161 / 0.200 / 0.212 | 0.043 | 2:5 |
| gemma-3-4b-it, grid | ` visited` (DFS) or a blank line, `if`, ` queue` (BFS) | 0.153 | 0.02 / 0.34 / 0.46 | 0.015 / 0.323 / 0.450 | 0.026 | 16:0 |

**Where the choice is decided.** Three different answers came out of three tasks in one model. On connected components the decision falls at generated tokens 10 and 11, where the routine is named; forcing the name decides the algorithm in every slot. On kth smallest a ban decides it before the first generated token. On shortest path no single token decides it within 60 tokens, and the opening's likelihood predicts the outcome better the longer the opening measured. The three mixed units of the temperature experiment and Gemma's grid task each have a one-token fork right after a shared opening of 18 to 61 tokens. The fork is thus a common place for the decision to surface, not a universal one, and where it exists its margin predicts the effect of random pushes (connected components) and of temperature (within the committed error on two of the four mixed units).

**What moves the algorithm, and at what cost.** Table 370 collects the edits of this iteration that move the algorithm in generation, with their correct target programs and pass rates. In Qwen3-8B a rank-1 or rank-2 DAS edit matches the full-state exchange at the same site, plan noise at the absolute unit moves half of connected components programs at no pass cost, and the default-to-runner-up axis moves connected components only at a dose beyond the committed range. In Gemma the DAS edit at the fork beats the explicit instruction in correct BFS programs, and steering five validated circuit nodes doubles them. In Gemma the difference-in-means edit toward BFS moves the algorithm and breaks the programs (toward the default DFS a strong edit kept them), and in Qwen3-8B a rank-1 difference-in-means interchange at the DAS site transfers nothing (0 of 30 on both core tasks). In this iteration the edits fitted or validated on the model's own contrasts kept the programs; the class-mean edit toward the minority algorithm did not.

**Table 370.** Edits that moved the algorithm in generation in iteration 7.

| Model and task | Edit | Correct target programs | Twin | Pass |
|-|-|-|-|-|
| Qwen3-8B, shortest path | DAS rank 2, fifth-template ban source, blocks 12-23 | 12/30 Bellman-Ford/SPFA | 1/30 | 0.83 |
| Qwen3-8B, shortest path | DAS rank 1, forced Floyd-Warshall source | 28/30 Floyd-Warshall | 0/30 | 0.93 |
| Qwen3-8B, connected components | DAS rank 16, fifth-template ban source | 29/30 BFS or DFS | 0/30 | 1.00 |
| Qwen3-8B, connected components | Plan noise, absolute unit, alpha 2 | 25/50 | 0/50 | 0.98 |
| Qwen3-8B, connected components | Axis push at four times the forced-prompt distance | 30/30 (29 DFS, 1 BFS) | 0/30 | 1.00 |
| Qwen3-8B, connected components | Tokens 10-11 forced to ` def dfs` | 30/30 DFS | 0/30 | 1.00 |
| Qwen3-8B, kth smallest | DAS rank 1, forced counting sort source | 30/30 counting sort | 0/30 | 1.00 |
| Qwen3-8B, kth smallest | Plan noise, absolute unit, alpha 2 (pricing cell) | 30/50 | 1/50 | 0.98 |
| Qwen3-8B, three mixed units | Exchange of the forced minority prompt's task-specification states | 30/30 on each | 0 to 7/30 | 1.00 |
| gemma-3-4b-it, grid | DAS rank 4 at block 17, lambda 1 | 42/50 BFS | 11/50 | 0.88 |
| gemma-3-4b-it, grid | Explicit BFS instruction | 35/50 BFS | 11/50 | 0.70 |
| gemma-3-4b-it, grid | Difference in means, lambda 1 | 0/50 BFS | 11/50 | 0.00 |
| gemma-3-4b-it, grid | Steering the five validated nodes toward BFS | 16/30 BFS | 8/30 | 0.83 |

**Novelty.** Table 371 collects the novelty audits of this iteration. Across the seven artifacts, the only correct programs outside the catalogue are the known techniques reached on kth smallest by evolutionary search, the larger mutator and the instruction alone, and none is novel.

**Table 371.** Novelty audits of iteration 7.

| Artifact | Programs audited | Final classes | Novel |
|-|-|-|-|
| Record audit | 3 engine-control programs labelled other | catalogue variants (Dijkstra by array scan, n-round Bellman-Ford) | 0 |
| DAS experiment | 38 correct programs labelled other | 36 catalogue variants, 2 labeller misses | 0 |
| Fork experiment | 2 | 2 labeller misses | 0 |
| Temperature experiment | 2 distinct programs (40 continuations) | catalogue variant (the extra counting mode of valid anagram) | 0 |
| Dose-unit experiment | 5 kth smallest programs | catalogue variant (counting sort with key compression) | 0 |
| Search experiment | 816 distinct screen-passing programs | 707 catalogue variants, 103 known techniques outside the catalogue, 6 degenerate | 0 |
| Gemma experiment | 2,325 correct programs | none outside the catalogue | 0 |

## 7.10 What iteration 7 established, what it ruled out, and what it abandoned

**Table 372.** Verdicts of the ten claims of iteration 7.

| Claim | Committed verdict | Deciding evidence |
|-|-|-|
| Fork claim | Not supported (inconclusive) | Spearman 0.80 on connected components; 0.15 on shortest path, which has no single fork; prospective 0.60 on kth smallest |
| DAS claim (Qwen3-8B) | Not supported on any task | Recovery 0.73 to 1.71 and random subspaces null, but permuted labels transfer 0.47 to 0.70 and an untrained network fits at 0.92 of the trained fit |
| Routing claim | Categorical on shortest path and kth smallest; not on connected components | Floyd-Warshall 28/28 and counting sort 30/30 under DAS; forced BFS lands on DFS |
| Axis claim | Disconfirmed | Spearman 0.17 and 0.01; clamp removes nothing |
| Temperature claim | Partial | Test 1 passes on 3 of 3 units, test 2 on 1 of 3, test 3 on 4 of 4 tasks; holds in Gemma |
| Manifold claim | Bans outside the null, seeds and instructions inside; semantic seed missed | D 1.73 to 2.62 against a null 95th percentile of 1.13 |
| Discreteness claim | Not discrete | Logistic width 3.25 in lambda; 0 hybrids of 114 |
| Dose-unit claim | The unit, not the seeds | Unit +0.45 [0.35, 0.55]; seeds +0.03 |
| Re-priced plan noise | Ahead of base intent on 2 of 5 tasks (predicted 3) | Kth smallest 3.22 and grid 1.39; behind on connected components, shortest path and two sum |
| Gemma claims | Temperature law holds; DAS controls hold, calling it one-dimensional not licensed; 7 to 8 of 10 circuit nodes validated | Error 0.026; random-init at most 0.25 times; dose dial 42 correct BFS against 35 for the instruction |
| Search claim | Not met at levels a and b | 6.65 times on kth smallest at level a; 78 known techniques against 0 at level b on kth smallest only; 0 novel |

**Established.** In Qwen3-8B a rank-1 or rank-2 subspace of the task-specification states at blocks 12 to 23 is a steering handle on the algorithm that matches the full-state exchange, and on two tasks it routes more cleanly than the full state. The handle is not a certified variable, because permuted labels and an untrained network admit it. In Gemma the analogous subspace at the fork passes all three controls and acts as a dose dial that keeps the programs. Where a one-token fork exists, temperature acts on the algorithm through the fork logits divided by T, as predicted before sampling on one Qwen3-8B unit and on Gemma; on the collapsed tasks the fork margins put the alternative out of temperature's reach. On connected components the decision falls at the token that names the routine, and the fork margin under a random push predicts the effect of the push (Spearman 0.80), through the probability that stays on the default fork tokens rather than through which algorithm each other token leads to (a token-map placebo reaches 0.80 in 18% of permutations). The weak plan noise of iteration 5 came from its dose unit; the absolute unit's peaky profile on a few task tokens carries the effect. Evolutionary search with an evaluator reaches known techniques outside the catalogue on kth smallest at a rate no single-sample arm approaches (78 distinct programs against at most 2).

**Ruled out.** The default-to-runner-up axis as the channel of random pushes (disconfirmed and not mediating). Discreteness of the effect of the fitted edit. The seeds as the cause of the null of iteration 5. Temperature above 1 as a source of a new idea: on every unit it only reweighted the algorithms the fork already weighs. Search at ten times the best text knob's level-a rate on two tasks.

**Dead ends.** The committed contrastive DAS objective, which diverged and broke programs, was replaced by the likelihood objective. The transcoder attribution graph in Gemma was dropped after three attempts on a 16 GB GPU. The judge gate for novelty failed for every judge family in the search experiment, so its classes rest on manual and rule-based reads. A top-five push inside the forced-prompt manifold of the grid task produced no algorithm outside the five in 300 programs, which closes the push route for that question at the doses tried.

## 7.11 What the next iteration takes from this one

The next iteration takes four leads. First, the DAS handle in Qwen3-8B needs the control it failed: a fit whose permuted-label and untrained-network versions do not transfer, which may require fitting at the fork in generation, where Gemma's controls passed, rather than at the task-specification states. Second, shortest path decides late, so the fork claim needs a measure that follows the decision to where it happens (the opening LLR improved from 48 to 160 tokens). Third, the temperature claim held on two of four mixed units; the misses on trapped rain water, which has a second opening with its own split, and valid anagram, where a second decision (fixed array against hash map) follows a few tokens after the fork, call for a prediction that composes more than one fork. Fourth, evolutionary search found known techniques outside the catalogue on kth smallest at a rate no single-sample knob approaches, so a search on a task whose catalogue already covers the known techniques, where a correct program outside it would be new, is the remaining route to a novel algorithm.

