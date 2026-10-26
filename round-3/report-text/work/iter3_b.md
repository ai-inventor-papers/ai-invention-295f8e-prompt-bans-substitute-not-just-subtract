## 3.2 The record audit: likelihood diagnostics, manifold figures, novelty, correct-only Llama, knob classes

The record audit [ARTIFACT:art_3tH2xtoZ7Gj2] ran first and on CPU only. It read the iteration-1 and iteration-2 artifacts in place, generated nothing, and spent USD 0.42 on blind LLM judges for the novelty audit. Every number it produced names its source file. An independent script rederived 72 of 72 headline checks from the raw files, and all 7 placebo tests failed as they should.

### 3.2.1 The likelihood substitution test cannot decide where the mass goes

The review's central objection was that the substitution test of Section 2.4 rests on cells that are behaviourally irrelevant and close to unestimable. The audit tested this directly on every sampled single ban in both models: if the likelihood instrument measured where a ban sends the mass, the survivor with the largest gain should be the one the model writes. Table 81 gives every event.

**Table 81.** Every sampled single-ban event with likelihood cells: the realised landing and the argmax of three likelihood readouts (gain against the neutral twin, its algorithm specific residual after the ladder fit, and the implied probability mass under the ban). "hit" marks an argmax equal to the modal landing. On the grid task "Dijkstra" means unit weight Dijkstra. Source: record audit `tables/c1_argmax_vs_landing.csv`.

| Model | Task | Draw | Banned | Kind | Attempted, not banned | Correct, not banned | Argmax of gain | Argmax of residual | Argmax of implied mass |
|-|-|-|-|-|-|-|-|-|-|
| Qwen3-8B | Grid | readout experiment, fresh pool | BFS | modal | DFS 85 | DFS 28 | IDDFS | IDDFS | DFS (hit) |
| Qwen3-8B | Shortest path | readout experiment, fresh pool | Dijkstra | modal | Bellman-Ford/SPFA 86, other 1 | Bellman-Ford/SPFA 83 | Dial | Dial | Bellman-Ford/SPFA (hit) |
| Qwen3-8B | Grid | association experiment | A* | absent (sham) | BFS 100 | BFS 72 | IDDFS | IDDFS | DFS |
| Qwen3-8B | Grid | association experiment | BFS | modal | DFS 90 | DFS 38 | IDDFS | IDDFS | DFS (hit) |
| Qwen3-8B | Grid | association experiment | bidirectional BFS | absent (sham) | BFS 99, other 1 | BFS 92 | IDDFS | IDDFS | BFS (hit) |
| Qwen3-8B | Grid | association experiment | DFS | absent (sham) | BFS 96 | BFS 86 | IDDFS | IDDFS | BFS (hit) |
| Qwen3-8B | Grid | association experiment | unit weight Dijkstra | absent (sham) | BFS 92, DFS 8 | BFS 69, DFS 2 | IDDFS | IDDFS | DFS |
| Qwen3-8B | Grid | association experiment | IDDFS | absent (sham) | BFS 88, DFS 12 | BFS 76, DFS 4 | bidirectional BFS | bidirectional BFS | DFS |
| Qwen3-8B | Shortest path | association experiment | Bellman-Ford/SPFA | absent (sham) | Dijkstra 94, other 1 | Dijkstra 92 | Dial | Floyd-Warshall | Dijkstra (hit) |
| Qwen3-8B | Shortest path | association experiment | bidirectional Dijkstra | absent (sham) | Dijkstra 97, Bellman-Ford/SPFA 3 | Dijkstra 97, Bellman-Ford/SPFA 3 | Dial | Dial | Dijkstra (hit) |
| Qwen3-8B | Shortest path | association experiment | Dial | absent (sham) | Dijkstra 95, Bellman-Ford/SPFA 5 | Dijkstra 95, Bellman-Ford/SPFA 2 | Bellman-Ford/SPFA | Bellman-Ford/SPFA | Dijkstra (hit) |
| Qwen3-8B | Shortest path | association experiment | Dijkstra | modal | Bellman-Ford/SPFA 90, other 1 | Bellman-Ford/SPFA 86 | Dial | Dial | Bellman-Ford/SPFA (hit) |
| Qwen3-8B | Shortest path | association experiment | Floyd-Warshall | absent (sham) | Dijkstra 77, Bellman-Ford/SPFA 23 | Dijkstra 68, Bellman-Ford/SPFA 3 | Dial | Dial | Dijkstra (hit) |
| Qwen3-8B | Grid | route experiment, full ban | BFS | modal | DFS 86 | DFS 31 | IDDFS | IDDFS | DFS (hit) |
| Qwen3-8B | Shortest path | route experiment, full ban | Dijkstra | modal | Bellman-Ford/SPFA 86, other 3 | Bellman-Ford/SPFA 80 | Dial | Dial | Bellman-Ford/SPFA (hit) |
| Qwen3-8B | Grid | ban list experiment, single ban | BFS | modal | DFS 86 | DFS 30 | IDDFS | IDDFS | DFS (hit) |
| Qwen3-8B | Shortest path | ban list experiment, single ban | Dijkstra | modal | Bellman-Ford/SPFA 83, other 1 | Bellman-Ford/SPFA 79 | Dial | Dial | Bellman-Ford/SPFA (hit) |
| Llama-3.1-8B | Grid | Llama replication | BFS | modal | DFS 63, other 6, A* 1, unit weight Dijkstra 1 | DFS 7, other 1 | A* | A* | DFS (hit) |
| Llama-3.1-8B | Grid | Llama replication | DFS | absent (sham) | BFS 39, other 4 | BFS 7 | A* | A* | BFS (hit) |
| Llama-3.1-8B | Grid | Llama replication | unit weight Dijkstra | absent (sham) | BFS 30, DFS 18, other 1 | BFS 12, DFS 1 | A* | A* | DFS |
| Llama-3.1-8B | Shortest path | Llama replication | Dijkstra | modal | other 37, Bellman-Ford/SPFA 18, Floyd-Warshall 2 | Bellman-Ford/SPFA 4, other 1 | n/a (three algorithms) | n/a | Bellman-Ford/SPFA (hit) |
| Llama-3.1-8B | Shortest path | Llama replication | Bellman-Ford/SPFA | absent (sham) | Dijkstra 33, other 14, Floyd-Warshall 1 | Dijkstra 13 | n/a | n/a | Dijkstra (hit) |
| Llama-3.1-8B | Shortest path | Llama replication | Floyd-Warshall | absent (sham) | Dijkstra 25, other 11, Bellman-Ford/SPFA 9 | Dijkstra 6, Bellman-Ford/SPFA 1 | n/a | n/a | Dijkstra (hit) |

The gains never point where the model writes (Table 82). Over the 17 Qwen3-8B events the argmax of the gain and the argmax of the residual hit the realised landing 0 times, against a chance rate of 0.22; under the BFS ban the largest residual is always IDDFS and under the Dijkstra ban always Dial. The implied mass, which weights each survivor by how much probability it has rather than by how much its log probability moved, hits 14 of 17, and 8 of 8 modal bans. The same split holds in Llama. A log gain of 18 nats on a survivor with negligible mass counts as much as the realised substitute's gain, and those tail cells are the ones with effective sample sizes near 1.

**Table 82.** Hit rate of each likelihood argmax on the realised landing (Wilson 95% intervals; chance is one over the number of survivors, averaged over events). Source: record audit `results/c1_diagnostics.json`.

| Model | Events | Gain (neutral twin) | Residual (neutral twin) | Gain (mention twin) | Residual (mention twin) | Implied mass | Chance |
|-|-|-|-|-|-|-|-|
| Qwen3-8B, all single bans | 17 | 0/17 [0.00, 0.18] | 0/17 [0.00, 0.18] | 1/17 [0.01, 0.27] | 0/17 [0.00, 0.18] | 14/17 [0.59, 0.94] | 0.22 |
| Qwen3-8B, modal bans | 8 | 0/8 [0.00, 0.32] | 0/8 [0.00, 0.32] | 0/8 | 0/8 | 8/8 [0.68, 1.00] | 0.23 |
| Llama-3.1-8B, all single bans | 6 (3 with gains) | 0/3 | 0/3 | 2/3 | 0/3 | 5/6 [0.44, 0.97] | 0.22 |
| Pooled | 23 (20 with gains) | 0/20 [0.00, 0.16] | 0/20 [0.00, 0.16] | 3/20 [0.05, 0.36] | 0/20 [0.00, 0.16] | 19/23 [0.63, 0.93] | 0.22 |

Restricting the test to estimable mass removes every row. The review asked for the test recomputed on survivors with at least 1% implied mass and an ESS of at least 5; the audit predicted before computing that few or no rows would survive, and none did (0 of 11 Qwen3-8B rows keep three such survivors). The substitution test is not decidable on estimable mass.

The noise correction was too small. Resampling templates and then programs within algorithm halves, the bootstrap variance of the mean gain is a median 2.68 times the replicate noise term that the frozen correction subtracted (range 1.22 to 4.26 over the 11 rows; 1.59 for a one stage bootstrap that resamples programs only). The Llama ratio was 4.8 to 11.3. Because the correction under-subtracts, both the F statistic for "not pure subtraction" and the X specific share are inflated. The sums are also skewed upward, which the percentile intervals of Section 2.4 hid; basic intervals, which reflect the bootstrap around the point estimate, are given in Table 83. The ladder term's basic interval crosses zero on both tasks.

**Table 83.** Qwen3-8B ladder and X specific sums of squares and the X specific share under the neutral twin reference: point estimate, bootstrap mean, and percentile and basic 95% intervals (2,000 two stage draws). Source: record audit `results/c1_diagnostics.json#intervals`.

| Scope | Quantity | Point | Bootstrap mean | Percentile 95% | Basic 95% |
|-|-|-|-|-|-|
| Grid | V_u (ladder) | 239.3 | 396.4 | [135.4, 873.0] | [-394.4, 343.1] |
| Grid | V_s (X specific) | 412.5 | 441.5 | [207.0, 729.0] | [95.9, 617.9] |
| Grid | share | 0.633 | 0.541 | [0.270, 0.781] | [0.484, 0.995] |
| Shortest path | V_u | 244.6 | 364.9 | [146.5, 769.7] | [-280.4, 342.8] |
| Shortest path | V_s | 173.1 | 162.4 | [83.8, 267.2] | [79.1, 262.4] |
| Shortest path | share | 0.414 | 0.335 | [0.121, 0.592] | [0.237, 0.708] |
| Pooled | V_u | 483.9 | 761.3 | [363.7, 1426.3] | [-458.4, 604.1] |
| Pooled | V_s | 585.6 | 603.9 | [340.2, 908.3] | [262.9, 831.0] |
| Pooled | share | 0.548 | 0.453 | [0.252, 0.659] | [0.436, 0.843] |

Two reported numbers were artefacts of construction. The aim under the mention twin reference is biased negative: the gain is the ban minus the mention cell and the prime and veto profile is the mention minus the neutral cell, so noise in the shared mention cell makes their correlation negative even when nothing is aimed. With equal cell variances the expected null correlation is -0.5; simulated under the split half design with the estimated variance components the null has mean -0.27 (SD 0.14, 5th to 95th percentile -0.49 to -0.04), and a placebo with an independent mention cell has mean 0.00. Llama's mention aim of -0.28 sits at the null's 66th percentile, so the bias explains it fully. Qwen3-8B's -0.595, omitted from Tables 56, 57 and 78, still lies below the null's 1st percentile (quantile 0.004). The ESS weighted grid share of 1.24 is impossible as a proportion: the noise corrected ladder term went negative (V_u = -35.4) when the weights shrank the ladder projection below its noise allowance, so V_s / (V_u + V_s) = 181.3 / 145.9.

**What a decision on mass would cost.** With Kish ESS approximately M / (1 + CV^2) for M proposal programs, the number of programs per algorithm needed for a median ESS of 5 is 5(1 + CV^2). The plug-in estimate of CV^2 from 20 programs cannot exceed 19, so the plug-in M is bounded by 100 and is a lower bound; a lognormal fit to the log weights gives 5 exp(sigma^2), the upper end. Pooled over algorithms, the plug-in median is 50 programs, the lognormal median about 10^31.7, and 22% of the Pareto smoothed importance sampling shape estimates [66] exceed 0.7, the value above which an importance sampling estimate is not reliable. At the plug-in lower bound one bench event costs about 1.4 GPU hours of scoring. The spread of per-event shares (SD 0.41 in Qwen3-8B, 0.23 in Llama) means that separating the share from 0.5 by 0.10 needs about 129 Qwen3-8B events or 43 Llama events (32 and 11 for a margin of 0.20), against 11 and 6 rows measured. The decision therefore moved to sampled landings on the bench (Sections 3.3 to 3.5).

**Table 84.** Programs per algorithm needed for a median Kish ESS of 5, from the observed weight dispersion of the likelihood cells. Source: record audit `tables/m_arithmetic.csv`.

| Model | Algorithm | Cells | Median ESS now (M = 20) | Median SD of log weights | Plug-in M5, median | Plug-in M5, 90th percentile | Lognormal M5, median |
|-|-|-|-|-|-|-|-|
| Qwen3-8B | A* | 202 | 1.03 | 5.99 | 55.2 | 99.9 | 1.9e16 |
| Qwen3-8B | Bellman-Ford/SPFA | 165 | 1.82 | 18.55 | 40.1 | 82.1 | 1.2e150 |
| Qwen3-8B | BFS | 202 | 4.27 | 2.43 | 15.0 | 64.1 | 1813.9 |
| Qwen3-8B | bidirectional BFS | 202 | 1.00 | 29.50 | 100.0 | 100.0 | 5.1e304 |
| Qwen3-8B | bidirectional Dijkstra | 165 | 1.01 | 26.56 | 36.8 | 55.0 | 5.1e304 |
| Qwen3-8B | DFS | 202 | 1.12 | 7.81 | 50.0 | 98.7 | 1.4e27 |
| Qwen3-8B | Dial | 165 | 1.00 | 13.36 | 73.5 | 100.0 | 1.7e78 |
| Qwen3-8B | Dijkstra and unit weight Dijkstra | 367 | 1.86 | 5.75 | 32.6 | 96.7 | 1.2e15 |
| Qwen3-8B | Floyd-Warshall | 165 | 1.07 | 7.39 | 64.3 | 98.3 | 2.5e24 |
| Qwen3-8B | IDDFS | 202 | 1.00 | 12.81 | 79.7 | 100.0 | 8.5e71 |
| Llama-3.1-8B | A* | 120 | 2.51 | 3.03 | 35.3 | 84.6 | 4.9e4 |
| Llama-3.1-8B | Bellman-Ford/SPFA | 100 | 1.02 | 5.23 | 70.0 | 144.7 | 3.7e12 |
| Llama-3.1-8B | BFS | 120 | 8.61 | 1.18 | 9.6 | 39.7 | 20.0 |
| Llama-3.1-8B | bidirectional BFS | 120 | 1.33 | 4.39 | 28.1 | 50.5 | 1.2e9 |
| Llama-3.1-8B | DFS | 120 | 3.97 | 2.09 | 22.3 | 53.3 | 390.2 |
| Llama-3.1-8B | Dijkstra and unit weight Dijkstra | 220 | 3.37 | 2.45 | 28.9 | 59.3 | 2050.0 |
| Llama-3.1-8B | Floyd-Warshall | 100 | 1.34 | 7.05 | 60.6 | 114.9 | 1.9e22 |
| Llama-3.1-8B | IDDFS | 120 | 1.57 | 6.37 | 51.0 | 94.7 | 2.2e18 |

The ladder verdicts of Section 2.11 are reconciled as the review asked (correction in place there). Behaviour shows a shared top rung on the shortest path task: Bellman-Ford/SPFA took 272 of 272 compliant programs in the five iteration-1 draws and 255 of 260 attempts not banned in the three iteration-2 draws, and 8 of 8 nonsemantic perturbations that left Dijkstra landed there. On the grid task only bans reach DFS (116 of 128 compliant iteration-1 programs, 257 of 257 iteration-2 attempts not banned). The order below the top rung is unmeasured, and "a coherent latent ladder" moves from ruled out to not detected by an uncalibrated instrument.

### 3.2.2 The ban list manifold figures

The ban list experiment had drawn 13 Isomap figures, not the 14 its summary claimed, plus two figures of neighbour stability over k: teacher forced states of forced programs at layer 24 and the token before the commit token, k = 10, with centroids sized and coloured by the number of programs implementing each algorithm under the condition, banned centroids crossed out, and natural programs overlaid. The audit recomputed the geometry from the saved states and reproduced the experiment's centroid matrix within 1e-7 and its nearest neighbour maps in 24 of 24 settings. Table 85 gives the implemented counts that the figures encode. Under the literal five name ban the counts stay on the banned BFS and DFS centroids (63 and 36 attempted, 53 and 15 correct).

**Table 85.** Implemented counts per centroid in the 13 manifold figures (attempted / correct; N = 100 per condition; banned algorithms marked †). Grid columns: BFS, DFS, bidirectional BFS, IDDFS, A*, greedy best first, IDA*, other. Shortest path columns: Dijkstra, Bellman-Ford/SPFA, bidirectional Dijkstra, Floyd-Warshall, Dial, other. Source: record audit `tables/manifold_implemented_counts.csv`.

| Condition | Banned | Counts |
|-|-|-|
| Grid baseline | none | BFS 100/89; all others 0 |
| Grid single ban | BFS | BFS† 14/11, DFS 86/30 |
| Grid TOP | BFS, DFS, greedy, IDDFS | BFS† 59/38, DFS† 26/0, greedy† 2/1, other 12/0, unit weight Dijkstra (outside the K = 7 catalogue) 1/1 |
| Grid ARC | BFS, bidirectional BFS, A*, greedy | BFS† 63/40, DFS 37/20 |
| Grid SCATTER | BFS, DFS, greedy, IDA* | BFS† 69/53, DFS† 27/18, A* 2/2, unit weight Dijkstra 2/2 |
| Grid TOP5 | BFS, DFS, greedy, IDDFS, A* | BFS† 63/53, DFS† 36/15, IDDFS† 1/0 |
| Shortest path baseline | none | Dijkstra 100/100 |
| Shortest path single ban | Dijkstra | Dijkstra† 16/16, Bellman-Ford/SPFA 83/79, other 1/0 |
| Shortest path, only Dijkstra allowed | the other four | Dijkstra 95/95, Bellman-Ford/SPFA† 5/5 |
| Shortest path, only Bellman-Ford/SPFA allowed | the other four | Dijkstra† 48/47, Bellman-Ford/SPFA 51/39, other 1/0 |
| Shortest path, only bidirectional Dijkstra allowed | the other four | Dijkstra† 52/51, Bellman-Ford/SPFA† 48/36 |
| Shortest path, only Floyd-Warshall allowed | the other four | Dijkstra† 59/59, Bellman-Ford/SPFA† 40/28, other 1/0 |
| Shortest path, only Dial allowed | the other four | Dijkstra† 52/50, Bellman-Ford/SPFA† 44/28, other 4/0 |

The neighbourhood that the iteration-2 record reported (BFS next to bidirectional BFS, centroid distance 0.0147 against a within-BFS spread of 0.0154) does not survive at a position independent of the label. At generated token 16, BFS and bidirectional BFS are still the nearest pair, but permuting the algorithm labels reproduces that identity with p = 0.19, and the two clouds are not separable (centroid distance 0.96 of the within-class spread; exchangeability test p = 0.48). Table 86 gives the nearest neighbour maps at layer 24 and k = 10 for both positions. Persistent homology found no loop at either position. At the token before the commit token a planted loop of matched size is detected with power 1.00 (grid) and 0.975 (shortest path), but that position partly encodes the label; at token 16 the power is 0.035 and 0.045. "No circle" is therefore powered only where the label confounds the geometry.

**Table 86.** Nearest centroid of each algorithm at layer 24, k = 10, at the label-dependent position (token before the commit token) and at generated token 16, with MDS stress-1. Source: record audit `tables/manifold_grid.csv`.

| Task | Position | Nearest neighbour map | Stress-1 | BFS and bidirectional BFS: distance / separability |
|-|-|-|-|-|
| Grid | before commit token | BFS: bidirectional BFS; DFS: IDDFS; bidirectional BFS: BFS; IDDFS: DFS; A*: greedy; greedy: A*; IDA*: greedy | 0.025 | 0.0147 / 0.954 |
| Grid | token 16 | BFS: bidirectional BFS; DFS: BFS; bidirectional BFS: BFS; IDDFS: bidirectional BFS; A*: greedy; greedy: A*; IDA*: bidirectional BFS | 0.104 | 0.0272 / 0.960 |
| Shortest path | before commit token | Dijkstra: bidirectional Dijkstra; Bellman-Ford/SPFA: bidirectional Dijkstra; bidirectional Dijkstra: Dijkstra; Floyd-Warshall: Dijkstra; Dial: Floyd-Warshall | 0.006 | n/a |
| Shortest path | token 16 | Dijkstra: bidirectional Dijkstra; Bellman-Ford/SPFA: Dial; bidirectional Dijkstra: Dijkstra; Floyd-Warshall: Dial; Dial: Floyd-Warshall | 0.005 | n/a |

### 3.2.3 Novelty: every correct program outside the catalogue, read

The request asks whether a model can be made to give a truly novel solution. The only place such a solution could have appeared in the run's data is among programs labelled "other". The audit collected every correct program labelled other across the eleven declared artifacts and the 1,200-program copy of the forking token pools: 78 unique programs (Set A). It added 138 unique failing "other" programs written under bans (Set B) and the 12 failing "other" programs of the TOP ban list (the selection was hash committed before any judge call). Two blind judges from different families (gpt-4.1-mini and gemini-2.5-flash, tie-break deepseek-chat) classed each program as a novel algorithm, a variant of a catalogue algorithm, a labeller miss, or degenerate or hard-coded, and the executor read all 78 Set A programs and 112 Set B programs by hand.

None of the 78 correct programs is a novel algorithm (Table 87). Sixty-five are labeller misses (catalogue algorithms the runtime and AST labellers failed to name) and 13 are variants of catalogue algorithms; the manual pass agreed with this split exactly once "variant" and "miss" are merged (78 of 78). Sixty-two of the 78 came from forced prompts, and only 4 from an instruction or steering condition. The rule of three [67] bounds the novel rate at 3/78 = 0.038 among correct programs outside the catalogue and 0.00026 over all 11,763 unique correct programs audited. About 9,000 other programs of the forking token experiment were not audited.

**Table 87.** Final classes of the audited programs. Source: record audit `results/novelty_audit.json`.

| Set | Programs | Labeller miss | Catalogue variant | Degenerate or hard-coded | Novel algorithm |
|-|-|-|-|-|-|
| A: correct, labelled other | 78 | 65 | 13 | 0 | 0 |
| B: failing, labelled other, under bans (final) | 138 | 53 | 41 | 44 | 0 |
| B: judges only, before the tie-break and manual pass | 138 | 53 | 28 | 40 | 17 |
| TOP ban list residue | 12 | 0 | 0 | 12 | 0 |

The judges agreed only fairly (Cohen's kappa 0.38 [0.31, 0.45]; 0.44 when known, novel and degenerate are collapsed), and gpt-4.1-mini called failing, broken code novel. The positive controls (catalogue references presented as unknown) failed the strict class gate at 7 of 10, but both judges named the right algorithm in 10 of 10; the negative controls passed 5 of 5, and no control was called novel.

The TOP ban list's avoidance of 0.13 is residue (Table 88): its 13 programs not banned are 12 failing degenerate BFS or DFS variants and 1 correct unit weight Dijkstra outside the K = 7 catalogue. Counted over catalogue algorithms only, avoidance is 0.00 for TOP and TOP5, 0.02 for SCATTER and 0.37 for ARC.

**Table 88.** Ban lists with the share labelled other reported separately from avoidance (N = 100 each; Wilson 95% intervals). Source: record audit `tables/multiban_avoidance_corrected.csv`.

| Ban list | Banned share | Share in a catalogue algorithm not banned | Share labelled other | Avoidance as reported | Avoidance into the catalogue |
|-|-|-|-|-|-|
| TOP | 0.87 [0.79, 0.92] | 0.00 [0.00, 0.04] | 0.13 [0.08, 0.21] | 0.13 | 0.00 |
| ARC | 0.63 [0.53, 0.72] | 0.37 [0.28, 0.47] | 0.00 | 0.37 | 0.37 |
| SCATTER | 0.96 [0.90, 0.98] | 0.02 [0.01, 0.07] | 0.02 [0.01, 0.07] | 0.04 | 0.02 |
| TOP5 | 1.00 [0.96, 1.00] | 0.00 | 0.00 | 0.00 | 0.00 |

### 3.2.4 Llama's compositions over correct programs

Every composition quoted in the review reproduced exactly. Llama's apparent diversity on the grid task is failing code: its 20 correct baseline programs are all BFS (correctness conditioned Hill number 1.00, against 1.87 over attempts). Tables 89 and 90 give every Llama event and the bench pilot with correct programs beside attempted ones.

**Table 89.** Llama-3.1-8B-Instruct path task events: correct compliant programs against attempted programs, with the correctness conditioned Hill number and the Qwen3-8B value for the matched condition. Source: record audit `tables/llama_correct_only.csv`.

| Task | Event | N | Pass rate | Correct, compliant | Attempted | Hill (attempts) | Hill_cc | Qwen3-8B Hill_cc |
|-|-|-|-|-|-|-|-|-|
| Grid | baseline | 100 | 0.20 | BFS 20 | BFS 77, DFS 20, other 3 | 1.87 | 1.00 | 1.00 |
| Grid | ban BFS | 100 | 0.12 | DFS 7, other 1 | DFS 63, BFS 29, other 6, A* 1, unit weight Dijkstra 1 | 2.49 | 1.46 (8 programs) | 1.00 |
| Grid | mention BFS | 50 | 0.28 | BFS 14 | BFS 47, other 2, DFS 1 | 1.30 | 1.00 | 1.00 |
| Grid | listing control | 50 | 0.20 | BFS 7, DFS 3 | BFS 36, other 7, DFS 6, unit weight Dijkstra 1 | 2.33 | 1.84 | 1.00 |
| Grid | ban DFS | 50 | 0.16 | BFS 7 | BFS 39, DFS 7, other 4 | 1.96 | 1.00 (7 programs) | 1.00 |
| Grid | ban unit weight Dijkstra | 50 | 0.26 | BFS 12, DFS 1 | BFS 30, DFS 18, unit weight Dijkstra 1, other 1 | 2.30 | 1.31 | 1.14 |
| Grid | ban BFS and DFS | 50 | 0.06 | none | BFS 21, DFS 21, other 6, unit weight Dijkstra 2 | 3.04 | n/a | 1.65 |
| Shortest path | baseline | 100 | 0.59 | Dijkstra 59 | Dijkstra 92, other 7, Bellman-Ford/SPFA 1 | 1.36 | 1.00 | 1.00 |
| Shortest path | ban Dijkstra | 100 | 0.25 | Bellman-Ford/SPFA 4, other 1 | Dijkstra 43, other 37, Bellman-Ford/SPFA 18, Floyd-Warshall 2 | 3.06 | 1.65 (5 programs) | 1.00 |
| Shortest path | mention Dijkstra | 50 | 0.46 | Dijkstra 22, other 1 | Dijkstra 39, other 11 | 1.69 | 1.20 | 1.00 |
| Shortest path | listing control | 50 | 0.24 | Dijkstra 9, Bellman-Ford/SPFA 3 | Dijkstra 19, Bellman-Ford/SPFA 15, other 14, Floyd-Warshall 2 | 3.37 | 1.75 | 1.14 |
| Shortest path | ban Bellman-Ford/SPFA | 50 | 0.26 | Dijkstra 13 | Dijkstra 33, other 14, Bellman-Ford/SPFA 2, Floyd-Warshall 1 | 2.31 | 1.00 | 1.00 |
| Shortest path | ban Floyd-Warshall | 50 | 0.18 | Dijkstra 6, Bellman-Ford/SPFA 1 | Dijkstra 25, other 11, Bellman-Ford/SPFA 9, Floyd-Warshall 5 | 3.38 | 1.51 (7 programs) | 1.19 |
| Shortest path | ban Dijkstra and Bellman-Ford/SPFA | 50 | 0.30 | none | Dijkstra 22, other 21, Bellman-Ford/SPFA 6, Floyd-Warshall 1 | 2.88 | n/a | n/a |

**Table 90.** Bench pilot (N = 50 per task), Llama-3.1-8B-Instruct correct programs against attempted programs; Qwen3-8B's correctness conditioned Hill number was 1.00 on every task. Source: record audit `tables/llama_correct_only.csv`.

| Task | Pass rate | Correct programs | Attempted programs | Hill (attempts) | Hill_cc | Hill_cc rarefied to 10 |
|-|-|-|-|-|-|-|
| kth smallest | 0.20 | full sort 6, heapify and pop 2, quickselect 1, size-k heap 1 | heapify and pop 16, size-k heap 11, full sort 7, other 6, quickselect 5, counting sort 2 | 5.08 | 2.97 | 2.97 |
| substring search | 0.48 | naive 18, KMP 5, Rabin-Karp 1 | naive 24, KMP 14, Rabin-Karp 6, other 1 | 2.86 | 1.96 | 1.87 |
| two sum | 0.80 | hash map 39, brute force 1 | hash map 48, other 1, brute force 1 | 1.22 | 1.12 | 1.10 |
| find duplicate | 0.34 | hash set 16, Floyd cycle detection 1 | hash set 20, other 15, Floyd 4, sort and adjacent check 3, index marking 3, binary search on values 1 | 3.97 | 1.25 | 1.23 |
| Fibonacci | 0.44 | matrix power 19, iteration 2, memoised recursion 1 | matrix power 37, iteration 4, other 4, memoised recursion 2 | 2.10 | 1.62 | 1.54 |
| connected components | 0.70 | union find 30, DFS 5 | union find 37, DFS 11 | 1.71 | 1.51 | 1.47 |
| longest increasing subsequence | 0.76 | quadratic DP 38 | quadratic DP 45, other 3, patience sorting 2 | 1.48 | 1.00 | 1.00 |
| merge intervals | 0.56 | sort and sweep 28 | sort and sweep 42 | 1.00 | 1.00 | 1.00 |
| top-k frequent | 0.24 | heap 8, sort by count 4 | heap 28, sort by count 14, other 1, quickselect on counts 1 | 2.28 | 1.89 | 1.87 |
| nonoverlapping intervals | 0.04 | DP with bisect 1, greedy by end 1 | greedy by end 23, other 14, DP with bisect 3, DAG longest path 1 | 2.65 | 2.00 (2 programs) | 2.00 |
| cycle detection | 0.22 | union find 7, DFS with parent 4 | DFS with parent 29, union find 16, other 4 | 2.41 | 1.93 | 1.92 |
| topological order | 0.82 | Kahn 41 | Kahn 48, DFS postorder 1 | 1.10 | 1.00 | 1.00 |
| first and last position | 0.56 | binary search 28 | binary search 47 | 1.00 | 1.00 | 1.00 |

Counted over correct programs and rarefied to 10, Llama is more diverse than Qwen3-8B on 9 of 13 tasks (median 1.47 against 1.00). The cross-model sentence of iteration 2 therefore becomes: Llama attempts more algorithms, but its correct grid output is as collapsed as Qwen3-8B's; correct-only diversity appears on substring search, connected components, cycle detection and top-k frequent, at small N.

### 3.2.5 The knob table under a declared class rule

The audit rebuilt the knob table with one statistic (rarefied Hill-1 over correct compliant programs at depth 25) and a class rule declared before ranking. Knobs are prompt bans, seeds, instructions, decoding settings, activation interventions and token vetoes. Controls (mention twins, sham bans of absent algorithms, forced prompts, and format or weight arms) are listed but never ranked. Generate then select is a ceiling, and baselines are references. The rebuilt table has 306 rows (276 without the instruction tuning experiment's arms), against the 249 of iteration 2, because steering arms, instruct arms and temperature cells are kept as separate units: 185 knobs, 103 controls, 16 references and 2 ceilings, with 108 rankable knob rows under 20 pass points.

No knob row under 20 pass points reaches a rarefied Hill-1 of 2 (Table 91). The best is the semantic seed on the shortest path task, 1.940 with a 90% interval of [1.770, 2.094] that includes 2. The A* mention reaches 2.69 at 11.3 points, but it is a control: it recommends a named algorithm. Stated in its own metric: no knob reaches an even two-algorithm split under 20 points; the semantic seed (Bellman-Ford/SPFA 61, Dijkstra 30 at 7 points) and the A* mention are the two conditions that buy a second correct algorithm, and both name or describe it.

**Table 91.** The twelve best knob rows under 20 pass points (rarefied Hill-1 at depth 25 over correct compliant programs, 90% interval; pass points against each row's own reference). Source: record audit `results/knob_table.json#ranking`.

| Task | Knob (experiment) | Pass rate | Correct compliant programs | Hill-1 [90%] | Pass points lost | Second algorithm (share) |
|-|-|-|-|-|-|-|
| Shortest path | semantic seed (decoding) | 0.92 | Bellman-Ford/SPFA 61, Dijkstra 30, Floyd-Warshall 1 | 1.940 [1.770, 2.094] | 7.0 | Dijkstra (0.33) |
| Shortest path | decommitment direction, c = 0.25 | 0.78 | Bellman-Ford/SPFA 54, Dijkstra 23, other 1 | 1.913 [1.705, 2.088] | 17.0 | Dijkstra (0.29) |
| Shortest path | random direction 1, c = 0.25 (decommitment) | 0.79 | Dijkstra 53, Bellman-Ford/SPFA 26 | 1.858 [1.728, 1.947] | 16.0 | Bellman-Ford/SPFA (0.33) |
| Shortest path | novelty instruction (decoding) | 0.96 | Dijkstra 82, Bellman-Ford/SPFA 14 | 1.503 [1.324, 1.649] | 3.0 | Bellman-Ford/SPFA (0.15) |
| Shortest path | random direction 1 at the read position only, c = 1.0 (instruction tuning) | 1.00 | Dijkstra 90, Bellman-Ford/SPFA 9, other 1 | 1.403 [1.210, 1.566] | 0.0 | Bellman-Ford/SPFA (0.09) |
| Shortest path | random direction 2, c = 0.25 (decommitment) | 0.87 | Dijkstra 82, Bellman-Ford/SPFA 5 | 1.229 [1.091, 1.376] | 8.0 | Bellman-Ford/SPFA (0.06) |
| Grid | novelty instruction (decoding) | 0.85 | BFS 81, unit weight Dijkstra 2, DFS 1, A* 1 | 1.228 [1.053, 1.401] | 12.0 | unit weight Dijkstra (0.02) |
| Shortest path | new algorithm instruction (decoding) | 0.94 | Dijkstra 90, Bellman-Ford/SPFA 4 | 1.178 [1.048, 1.308] | 5.0 | Bellman-Ford/SPFA (0.04) |
| Shortest path | enumeration prompt (decommitment) | 0.82 | Dijkstra 80, Bellman-Ford/SPFA 2 | 1.109 [1.000, 1.215] | 6.5 | Bellman-Ford/SPFA (0.02) |
| Shortest path | enumeration prompt, 1,024 tokens (decommitment) | 0.82 | Dijkstra 80, Bellman-Ford/SPFA 2 | 1.108 [1.000, 1.236] | 6.5 | Bellman-Ford/SPFA (0.02) |
| Grid | new algorithm instruction (decoding) | 0.94 | BFS 92, DFS 2 | 1.093 [1.000, 1.191] | 3.0 | DFS (0.02) |
| Grid | semantic seed (decoding) | 0.93 | BFS 91, bidirectional BFS 2 | 1.092 [1.000, 1.192] | 4.0 | bidirectional BFS (0.02) |

Four of the ten shortest path rows in Table 91 are activation edits: the decommitment direction, which iteration 1 found no better than a random direction, and three random directions. In every one of them the only catalogue algorithm besides Dijkstra is Bellman-Ford/SPFA, the same second choice the ban reaches.

### 3.2.6 Positioning of the iteration-2 claims

The audit checked each iteration-2 claim against its nearest published neighbour with verbatim quotes from the abstract pages, all 12 verified on 2026-10-20 (Table 92). Two contrasts matter for interpretation. Heo et al. found a dimension in input embedding space that predicts instruction following, is tied to prompt phrasing, and raises success when intervened on [58]; this run replicates the phrasing link for prohibitions in code but finds the read position causally inert when spliced alone. Sia, Mueller and Duh found a task recognition point after which attention to the instruction is no longer needed [59]; this run replicates that on the shortest path task and finds the opposite on the grid task. The base to chat SAE transfer study of Kissane and colleagues (an Alignment Forum post that the bibliography tool could not retrieve, so it carries no number here) is the source of the fine-tuning remedy that Section 2.12 proposed without citation.

**Table 92.** The iteration-2 claims, their nearest neighbours, and what this run adds. Source: record audit `tables/positioning.csv`.

| Claim in this run | Neighbour | Neighbour's finding (verbatim) | Relation | What this run adds |
|-|-|-|-|-|
| Compliance is decodable at the read position (-0.41 across wordings) yet splicing the read position carries nothing | Heo et al. [58] | "this dimension is more closely related to the phrasing of prompts rather than the inherent difficulty of the task or instructions" | replication (phrasing) and contrast (decodable but inert under splicing) | a compliance-predictive direction at the read position that is causally inert; the ban travels through the task specification states |
| Attention knockouts and cache splicing place the path task ban on the prompt route | Geva et al. [48] | "With interventions on attention edges, we first identify two critical points where information propagates to the prediction" | extension (method) | edge knockouts applied to a prompt-level prohibition in code, with token-matched neutral twins |
| Generated tokens stop needing the ban on the shortest path task (direct 0.05) but not on the grid task (direct 0.35) | Sia et al. [59] | "we demonstrate evidence of a "task recognition" point where the translation task is encoded into the input representations and attention to context is no longer necessary" | replication (shortest path) and contrast (grid) | the same redundancy for a prohibition on one task and its failure on another |
| Naming an absent algorithm in a ban raises its likelihood (8 of 9 in Qwen3-8B, 5 of 6 in Llama) | Rana [7] | "the instruction's explicit mention of the forbidden word paradoxically activates rather than suppresses the target representation" | replication | priming at the level of whole algorithms, in two model families |
| (same) | Mann et al. [53] | "suppressing a concept requires internally activating it, which may prime rebound instead of avoidance" | replication | rebound measured on implemented mechanisms rather than tokens |
| Ban lists fail by reimplementation, 41% to 92% disguised | Lu et al. [23] | "DENIAL PROMPTING which pushes LLMs to develop more creative solutions to a given problem by incrementally imposing new constraints on the previous solution" | extension | mechanism labels show the constraint satisfied in name only |
| Qwen-Scope base SAEs fail the cross-entropy ratio on the instruct model | Kissane et al. (blog post, not in the bibliography) | "We also find that they don't transfer on" (Gemma v1 2B) | contrast and source of the remedy | Qwen3-8B would join Gemma v1 2B as a pair where base SAEs do not transfer under that criterion; Section 3.7 reverses this under a fairer criterion |
| Decoding-time constraints as the alternative to prompt bans | Biagiola et al. [62] | "Incompleteness pushes the model into low-probability regions of the program space, causing the generation to frequently time out, and reducing functional correctness by up to 97%." | contrast | single name prompt bans are obeyed at 0.86 and 0.84; vetoes at decoding time carry the cost Biagiola et al. measure (Section 3.8) |
| A single ban suppresses the default opening and promotes one substitute | Yoon et al. [4] | "suppressing retrieval of the original answer (e.g., "Madrid") while (2) promoting a favored candidate within the answer category" | replication at program level | the promoted candidate is the shared top rung, not a substitute specific to X |
| (same) | Zhou et al. [56] | "models implement both mechanisms, with the "constructive" mechanism being more prominent" | contrast | for a prohibition on code the route is carried by task specification states; construction of the negated phrase was not tested |
| The ban is carried by task specification states and not by the read position alone | Hendel et al. [60] | "the functions learned by ICL often have a very simple structure" | contrast | a prohibition does not compress into one position's state |
| (same) | Todd et al. [61] | "a small number attention heads transport a compact representation of the demonstrated task, which we call a function vector (FV)" | contrast | ban-attending heads exist (layer 21 head 17, layer 26 heads 21 and 25), but the effect is spread over task specification positions; Section 3.7 tests the heads causally |

### 3.2.7 Corrections and reproduction targets

The audit wrote 12 correction items, each with its old wording, the recomputed numbers and a replacement sentence; they are applied in place in Sections 1.12 and 2.3 to 2.12 and marked. It also recomputed 19 numbers quoted in the record; 16 reproduced (Table 93). One mismatch is a difference of definition rather than of data. The audit counted DFS as the grid substitute's mode in 5 of 5 iteration-1 draws by plurality, while the record's 4 of 5 applies the realised mode rule of Section 1.2, which requires a 15-point lead; the geometry draw (DFS 10, unit weight Dijkstra 8 of 18) fails that lead. The record's count stands.

**Table 93.** Numbers quoted in the record and their recomputation. Source: record audit `corrections.json#reproduction_targets`.

| Quantity | Quoted | Recomputed | Match | Cause of a mismatch |
|-|-|-|-|-|
| Shortest path Bellman-Ford/SPFA, iteration-1 five draws | 272/272 | 272/272 | yes | |
| Grid DFS, iteration-1 five draws | 116/128 (0.906) | 116/128 | yes | |
| Grid draws with DFS as realised mode | 4 of 5 | 5 of 5 | no | plurality count; the record applies the 15-point lead of Section 1.2 |
| Iteration-2 pooled shortest path Bellman-Ford/SPFA (attempted, not banned) | 255/260 | 255/260 | yes | |
| Iteration-2 pooled grid DFS (attempted, not banned) | 257/257 | 257/257 | yes | |
| Residual of IDDFS under the BFS ban | 7.988 | 7.988 | yes | |
| Semantic seed, shortest path Hill-1 | 1.935 [1.534, 2.076] at 7 points | 1.940 [1.770, 2.094] at 7.0 points | yes | point within 0.005; the iteration-2 bootstrap scheme was not available |
| A* mention Hill-1 (control) | 2.69 at 11 points | 2.69 at 11.3 points | yes | |
| Generate then select | 3 to 4 algorithms at 24 to 42 points | grid 4 at 42; shortest path 3 at 24 | yes | |
| Knob table rows | 249 | 306 (276 without the instruction tuning arms) | no | steering arms, instruct arms and temperature cells kept as separate units |
| Ban list manifold figures | 14 | 13 | no | 13 files exist |
| TOP5 BFS / DFS attempted | 63 / 36 | 63 / 36 | yes | |
| Before the commit token, BFS within spread against BFS to bidirectional BFS distance | 0.0154 against 0.0147 | 0.0154 against 0.0147 | yes | |
| ESS weighted share | 1.24 [0.57, 1.62] | 1.24 [0.57, 1.62] | yes | |
| Qwen3-8B aim, mention reference | -0.595 | -0.595 | yes | |
| Llama aim, mention reference | -0.28 | -0.283 | yes | |
| Llama bootstrap against replicate variance | 5 to 11 times | 4.8 to 11.3 times | yes | |
| Llama grid baseline | BFS 77, DFS 20 attempted; BFS 20 of 20 correct | same | yes | |
| Gated forecast events of iteration 2 | 3 events, 0.05-nat margin | quoted, not recomputed | yes | record fact |

