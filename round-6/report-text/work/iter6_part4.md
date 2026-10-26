## 6.5 Gemma: a one-token fork, and Gemma Scope 2 features against difference in means

**Why Gemma.** Asked one and the same grid-path prompt, gemma-3-4b-it [76] writes DFS about 70% of the time and BFS about 30%, so it offers what Qwen3-8B never does: the request's BFS-against-DFS contrast inside one prompt, with no ban or instruction to confound it. Gemma Scope 2 provides sparse autoencoders on the residual stream after each block, trained on this instruct model, so the feature claim needs no transfer test. Qwen-3 transcoders for circuit tracing exist as well [123], but they would have to study a choice Qwen3-8B does not make naturally. The experiment [ARTIFACT:art_zNyBP6zieI5u] asked where the choice forks, whether it can be read from the internals beyond what the visible text already says, and whether the SAE features steer it better than plain baselines: a difference-in-means direction, the raw residual, random features, isotropic directions, DAS and prompting. It used the residual-stream SAEs at layers 9, 17, 22 and 29 (16k latents, medium L0), one 16 GB card and exact common random numbers, under two hash-chained commitments.

**Natural splits.** Over 200 samples per task, the grid prompt gave DFS 139 and BFS 61 (Wilson interval for DFS 0.63 to 0.75), with DFS on 134 of 172 correct programs (Table 258). The choice depends on the template: BFS takes 6 to 18 of 40 attempts per template. Substring search (naive 173, built-in find 27) and first and last position (linear scan 170, binary search 29) split as well. Labels agreed with iteration 5's Gemma rows on 0.94 of the grid slots and 1.00 of the substring slots.

**Table 258.** Natural splits in gemma-3-4b-it (N = 200 per task; 40 per template). Source: Gemma feature experiment `results/natural_split.json`.

| Task | Attempted | Correct | Pass | Correct-only Hill-1 | Default (share of correct) | Attempted per template (first to fifth) |
|-|-|-|-|-|-|-|
| grid | DFS 139, BFS 61 | DFS 134, BFS 38 | 0.86 | 1.68 | DFS (0.78) | DFS 34 / BFS 6; DFS 22 / BFS 18; DFS 22 / BFS 18; DFS 29 / BFS 11; DFS 32 / BFS 8 |
| substring search | naive 173, built-in find 27 | same | 1.00 | 1.47 | naive (0.87) | naive 36 / built-in 4; naive 40; built-in 21 / naive 19; naive 38 / built-in 2; naive 40 |
| first and last position | linear scan 170, binary search 29, other 1 | same | 1.00 | 1.52 | linear scan (0.85) | linear 33 / binary 7; linear 28 / binary 12; linear 39 / other 1; linear 40; linear 30 / binary 10 |

**The instrument gate.** Each SAE was spliced into the forward pass on three corpora: the model's own programs, generic text and LeetCode prompts. A layer passed if its increase in cross-entropy and its fraction of variance unexplained on the model's programs were at most 1.5 times those on generic text (Table 259). Layers 22 and 29 passed; layer 9 failed the cross-entropy ratio and layer 17 the variance ratio by 0.0001, so their results are descriptive. On generic text L0 was 57 to 64, slightly above the quoted medium band of 30 to 60.

**Table 259.** Gemma Scope 2 residual-stream SAEs spliced in on three corpora (the model's own programs / generic text / LeetCode prompts): L0, fraction of variance explained, increase in cross-entropy (nats per token) and loss recovered. Source: Gemma feature experiment `results/gate.json`.

| Layer | L0 | Fraction of variance explained | Increase in cross-entropy | Loss recovered | Gate |
|-|-|-|-|-|-|
| 9 | 52.2 / 57.5 / 57.3 | 0.963 / 0.974 / 0.917 | 0.065 / 0.033 / -0.010 | 0.9968 / 0.9983 / 1.0005 | fail |
| 17 | 59.9 / 64.1 / 61.4 | 0.919 / 0.946 / 0.814 | 0.097 / 0.184 / 0.119 | 0.9968 / 0.9936 / 0.9957 | fail (variance ratio, by 0.0001) |
| 22 | 60.0 / 61.7 / 62.2 | 0.809 / 0.869 / 0.750 | 0.036 / 0.259 / 0.167 | 0.9968 / 0.9789 / 0.9837 | pass |
| 29 | 64.1 / 64.1 / 69.5 | 0.637 / 0.715 / 0.635 | 0.017 / 0.212 / 0.142 | 0.9994 / 0.9932 / 0.9952 | pass |

**The plan is a single-token fork.** Prefix resampling located the fork: 24 base paths, 16 prefix lengths, 8 continuations each and a refinement, 3,712 continuations in all, scored by a partial-code labeller that agreed with the full labeller on 200 of 200 programs. Every one of 12 BFS base paths had a significant change point with a rise of at least 0.4, at prefix lengths 16 to 36. In 177 of 200 programs the first 32 tokens are identical (the code fence, `def solve(grid, start, goal):`, `rows = len(grid)`, `cols = len(grid[0])` and an indent), and the next token decides (Table 260): ` visited` leads to DFS (BFS probability 0.011 over 1,409 continuations), while a blank line, `if`, `queue` or `q` lead to BFS (0.95 to 1.00). The first token that identifies the algorithm in code comes a median of 138 tokens after the fork (10th to 90th percentile 80 to 181). The fork index was chosen by the token class with the most mutual information with the outcome (0.62 bits at index 32), after the first median rule landed on a deterministic indentation token; the change was made before the second commitment.

**Table 260.** The fork token at response index 32 and the BFS probability of the continuations that follow it (all continuations; the natural samples alone in the last column). Source: Gemma feature experiment `results/fork.json`.

| Token at index 32 | Continuations | BFS | DFS | BFS probability | Natural samples (BFS / n) |
|-|-|-|-|-|-|
| ` visited` | 1,409 | 15 | 1,394 | 0.011 | 2 / 134 |
| newline | 204 | 193 | 11 | 0.946 | 19 / 21 |
| `if` | 177 | 174 | 2 | 0.989 | 16 / 17 |
| `queue` | 82 | 82 | 0 | 1.000 | 4 / 4 |
| `q` | 3 | 3 | 0 | 1.000 | 1 / 1 |

**Readable beyond the text, at the fork, but not specifically through the SAE.** Within one prompt, decodability before the first identifying token is at ceiling for every method, the visible-text control included (balanced accuracy 1.00 at all four layers), so the SAE has no advantage there; at the fork itself the test is undefined, because 185 of 200 samples share their prefix with a sample of the other class. Across prompts, the experiment built 120 neutral prompt variants by changing nouns and measured each variant's fork log-odds of BFS, which we write y (mean -0.92 nats, SD 0.67; the sampled BFS share tracks it at Spearman 0.65 over 60 variants of 10 samples). A Lasso on layer-29 SAE codes at the fork position predicts held-out y with R-squared 0.66, against 0.18 for a text-only model (difference 0.49, 95% interval 0.26 to 0.65, permutation p 0.003), above the difference-in-means readout (0.34) and a 16-component PCA of the raw residual (0.56) (Table 261). That meets the preregistered bar. Two checks outside the preregistration qualify it: a tuned ridge on the raw layer-29 residual reaches 0.72, and ridge on the same SAE codes reaches at most 0.09. The information is in the residual stream at the fork, and the SAE advantage depends on the estimator. At the task-specification positions, before any response token, the SAE codes do no better than the text (0.18).

**Table 261.** Cross-prompt readout of the fork log-odds over 120 neutral variants: R-squared with held-out nouns, Spearman with held-out nouns, and R-squared with held-out templates. Source: Gemma feature experiment `results/readout.json`.

| Readout | Site | Layer | R-squared, held-out nouns | Spearman, held-out nouns | R-squared, held-out templates |
|-|-|-|-|-|-|
| text only | n/a | n/a | 0.176 | 0.425 | 0.150 |
| template only | n/a | n/a | 0.148 | 0.272 | -0.122 |
| SAE codes (Lasso) | fork | 22 | 0.237 | 0.583 | 0.139 |
| raw PCA-16 | fork | 22 | 0.412 | 0.666 | 0.491 |
| raw PCA-64 | fork | 22 | 0.092 | 0.533 | 0.239 |
| difference in means | fork | 22 | 0.226 | 0.541 | 0.109 |
| SAE codes (Lasso) | task specification | 22 | 0.180 | 0.464 | 0.123 |
| raw PCA-16 | task specification | 22 | -0.090 | 0.354 | 0.352 |
| raw PCA-64 | task specification | 22 | 0.021 | 0.432 | 0.152 |
| difference in means | task specification | 22 | 0.063 | 0.282 | -0.570 |
| SAE codes (Lasso) | fork | 29 | 0.662 | 0.782 | 0.496 |
| raw PCA-16 | fork | 29 | 0.557 | 0.697 | 0.444 |
| raw PCA-64 | fork | 29 | 0.432 | 0.715 | 0.403 |
| difference in means | fork | 29 | 0.338 | 0.620 | 0.181 |
| SAE codes (Lasso) | task specification | 29 | -0.073 | 0.276 | 0.147 |
| raw PCA-16 | task specification | 29 | -0.602 | 0.194 | -0.062 |
| raw PCA-64 | task specification | 29 | 0.029 | 0.381 | 0.083 |
| difference in means | task specification | 29 | 0.064 | 0.302 | -0.438 |

**Steering: the features move the fork, difference in means moves it more, and every fork edit breaks programs.** At the fork position of layer 22, edits at matched norm moved y by +4.04 nats for the difference-in-means direction, +1.78 for clamping the top 20 input-selected SAE features, +0.51 for 20 random features and +0.12 for an isotropic direction. In generation (N = 50 paired slots), the twin wrote BFS in 13 programs; the SAE clamp raised this to 30 (top 20 features) and 36 (top 50), the difference-in-means edit at the same norm to 46 and 49, and random features to 21 (Table 262). Every edit at the fork lowered the pass rate, from 0.84 for the twin to 0.58 and 0.48 for the SAE clamps and 0.32 and 0.16 for difference in means, so the preregistered outcome, correct BFS programs, shows no significant effect anywhere after Holm correction, and no feature claim is made. The preregistered feature rule (SAE target-correct count at least the difference-in-means count, at a pass rate of at least 0.8 times the twin's) is also met by random features at 50 features (9 against 7, pass 0.76), so it cannot discriminate here. The informative comparisons are on attempted BFS, and they are descriptive: the SAE clamp beats the twin (17:0 and 23:0 discordant slots, p 1.5e-5 and 2.4e-7) and random features (15:0, p 6.1e-5), and difference in means beats the SAE clamp at matched norm (16:0, p 3.1e-5). At matched effect on y rather than matched norm, difference in means and the SAE clamp shift the plan equally (32 against 30 BFS, p 0.50; 34 against 36, p 0.63) and difference in means keeps slightly more programs correct (13 against 9, 14 against 10). Edits at the task-specification positions do nothing (12 to 19 BFS against 13). Steering toward DFS works cleanly for both (SAE 47 of 50, difference in means 50 of 50, against 37 for the twin; pass 0.98 to 1.00).

**Table 262.** Generation under edits at the fork (layer 22) and at the task-specification positions (N = 50 paired slots; BFS is the target). Source: Gemma feature experiment `results/clamps.json`.

| Site | Edit | Mean realised norm | Attempted BFS | Correct BFS | Pass |
|-|-|-|-|-|-|
| none | twin | 0 | 13 | 6 | 0.84 |
| fork | SAE clamp, top 5 input features | 307.9 | 18 | 10 | 0.84 |
| fork | SAE clamp, top 20 input features | 602.2 | 30 | 9 | 0.58 |
| fork | SAE clamp, top 50 input features | 1069.8 | 36 | 10 | 0.48 |
| fork | difference in means at the top-20 norm | 602.2 | 46 | 12 | 0.32 |
| fork | difference in means at the top-50 norm | 1069.8 | 49 | 7 | 0.16 |
| fork | 50 random features at the same norm | 1069.8 | 21 | 9 | 0.76 |
| fork | SAE clamp, top 20 output-scored features | 673.5 | 25 | 14 | 0.78 |
| fork | difference in means matched on effect, top-20 level | 270.6 | 32 | 13 | 0.62 |
| fork | difference in means matched on effect, top-50 level | 342.9 | 34 | 14 | 0.60 |
| fork | DAS rank-4 interchange | 496.0 | 50 | 0 | 0.00 |
| fork | ablation of the top 5 attribution nodes (N = 30) | 1004.7 | 29 | 0 | 0.03 |
| fork | steering with the top 5 attribution nodes (N = 30) | 115.5 | 19 | 12 | 0.73 |
| task specification | SAE clamp, top 5 | 4.1 | 14 | 6 | 0.84 |
| task specification | SAE clamp, top 20 | 92.4 | 12 | 4 | 0.82 |
| task specification | SAE clamp, top 50 | 104.9 | 15 | 5 | 0.80 |
| task specification | difference in means at the top-20 norm | 92.4 | 17 | 9 | 0.84 |
| task specification | difference in means at the top-50 norm | 104.9 | 19 | 9 | 0.80 |
| task specification | 50 random features | 104.9 | 15 | 9 | 0.88 |
| fork, toward DFS | SAE clamp, top 20 | 1170.1 | 3 (47 DFS, all correct) | n/a | 0.98 |
| fork, toward DFS | difference in means | 1170.1 | 0 (50 DFS, all correct) | n/a | 1.00 |

[FIGURE:fig_gemma_steer]

**DAS finds the choice in one direction at the fork, and forcing it breaks the program.** DAS at the fork position of layer 22, with forced-BFS prompts as sources, moved held-out y by +8.8, +9.5 and +9.8 nats at ranks 1, 2 and 4, against -0.08 to +0.05 for random subspaces of the same rank (Table 263). The shuffled-source control was uninformative as built, because every source was a forced-BFS prompt. In generation the rank-4 interchange made 50 of 50 programs BFS and 0 of 50 passed. Together with the difference-in-means result, this says that the plan is close to one direction at one position, and that pushing it hard costs correctness, as subspace interventions can when they leave the model's natural range [122].

**Table 263.** DAS at the fork (layer 22): mean change in the fork log-odds of BFS on held-out and training prompts. Source: Gemma feature experiment `results/das.json`.

| Rank | DAS, held out | DAS, train | Share of held-out prompts moved toward BFS | Random subspace, held out | Shuffled source, held out |
|-|-|-|-|-|-|
| 1 | 8.81 | 9.55 | 1.00 | -0.08 | 10.11 |
| 2 | 9.51 | 10.15 | 1.00 | 0.03 | 9.69 |
| 4 | 9.76 | 10.25 | 1.00 | 0.05 | 11.42 |

The planned transcoder attribution graph was the first item of the drop order and was not built; a first-order attribution on the residual-stream SAEs replaced it (Table 264). Ablating the two strongest nodes moved y by 4.0 and 6.3 nats, against 0.8 and 0.4 for random active latents at matched contribution; two of the other three beat random and one did not. Jointly ablating the five nodes turned 29 of 30 programs into BFS with none passing, and jointly steering with them gave 19 BFS of 30, 12 correct.

**Table 264.** First-order attribution nodes at the fork, validated by ablation and steering in the real model (mean change in y, against random active latents at matched contribution). Source: Gemma feature experiment `results/attribution.json`.

| Layer | Latent | Attribution score | Ablation | Random ablation | Steering | Random steering |
|-|-|-|-|-|-|-|
| 22 | 1774 | -4.68 | 4.01 | 0.78 | 0.55 | 0.07 |
| 29 | 15050 | -4.35 | 6.28 | 0.40 | 0.45 | 0.11 |
| 29 | 735 | 4.11 | -0.51 | 0.40 | 1.38 | 0.09 |
| 29 | 6026 | 3.95 | -0.95 | 0.51 | 0.14 | 0.09 |
| 22 | 142 | 3.79 | -1.26 | 2.10 | 0.24 | 0.09 |

**The top-five prohibition in a model that writes two algorithms.** Banning the five most common grid algorithms (BFS, DFS, IDDFS, A* and greedy best-first, which share one catalogue label here) left no program outside the banned set: avoidance 0.00, as in Qwen3-8B in iteration 2 (Table 265). The ban pushed Gemma from its default DFS to BFS (10 to 41 of 50; McNemar 32:1, p 7.9e-9) and cut the pass rate from 0.86 to 0.38. In actual activation coordinates (PCA, Isomap with k = 10 and classical MDS of layers 17 and 22, raw and SAE codes), the top-five prompt states sit next to the banned A* and greedy cluster; among all 15 ways of splitting the six catalogue centroids into four banned and two survivors, the observed split ranks first in three of the four spaces (rank share 0.067) and third in the fourth (0.20). The prohibition lands inside the banned region, not at its edge or on the opposite side. The single-name bans of BFS and DFS left the banned algorithm in 11 and 8 of 50 programs, and the forced prompts gave BFS 50 of 50 (38 correct) and DFS 50 of 50 (45 correct).

**Table 265.** Bans and forced prompts on Gemma's grid task (N = 50). Source: Gemma feature experiment `results/top5.json`, `results/geometry.json`.

| Prompt | Attempted | Correct | Pass | Avoidance of the banned set |
|-|-|-|-|-|
| top-five twin | DFS 40, BFS 10 | DFS 40, BFS 3 | 0.86 | n/a |
| top-five ban | BFS 41, DFS 9 | BFS 10, DFS 9 | 0.38 | 0.00 |
| ban BFS | DFS 39, BFS 11 | DFS 39, BFS 2 | 0.82 | 0.78 |
| ban DFS | BFS 42, DFS 8 | BFS 15, DFS 7 | 0.44 | 0.84 |
| forced BFS | BFS 50 | BFS 38 | 0.76 | n/a |
| forced DFS | DFS 50 | DFS 45 | 0.90 | n/a |

**Table 266.** Where the top-five prompt states sit: geodesic distance from their mean to each catalogue centroid, and the rank of the observed banned-survivor split among the 15 possible splits. Source: Gemma feature experiment `results/geometry.json`.

| Space | MDS stress-1 | Nearest centroid | Geodesic distance to BFS / DFS / bidirectional BFS / IDDFS / A* and greedy / Dijkstra | Rank share of the observed split |
|-|-|-|-|-|
| raw, layer 17 | 0.371 | A* and greedy | 341.9 / 330.6 / 410.3 / 222.1 / 188.8 / 496.5 | 0.067 |
| raw, layer 22 | 0.369 | A* and greedy | 734.1 / 684.9 / 900.1 / 365.2 / 318.6 / 990.5 | 0.067 |
| SAE codes, layer 17 | 0.542 | A* and greedy | 27.5 / 28.4 / 41.1 / 32.9 / 26.1 / 47.1 | 0.067 |
| SAE codes, layer 22 | 0.569 | A* and greedy | 43.2 / 44.1 / 61.5 / 83.6 / 43.1 / 72.5 | 0.20 |

The novelty audit found 1 correct program labelled other among 1,450 correct programs, a first-and-last-position program that two of three judges called a catalogue variant: 0 novel (rule-of-three bound 0.0021). The style re-gate agreed with the labeller on 30 of 30 grid programs. The hash chain verified, a standard-library re-derivation matched 32 of 32 headline quantities, and a shuffled-class decodability placebo sat at chance (0.43). Judge spend was USD 0.034.

## 6.6 The plan in words: a natural language autoencoder on Qwen2.5-7B-Instruct

**Why.** The request names NLA as an instrument, and the release of NLA checkpoints for Qwen2.5-7B-Instruct [124] made it possible to ask, in words, whether the residual stream states before the first code token say which algorithm will be written. The experiment [ARTIFACT:art_dbUtqBjT0tPf] read layer-20 states with the released verbalizer and reconstructor pair, judged the explanations blind, and tested an edit of the explanation as a steering vector. Published verbalizers of the same kind include LatentQA [117] and SelfIE [118], and a 2026 analysis of a released Qwen-2.5-7B verbalizer found that only a small share of an explanation's specific claims are ones the reconstruction depends on [119]. Pre-registration was a sha256 chain of four commitments, each preceding its samples; the parts added after the committed nulls are marked exploratory.

**Behaviour.** Over eight tasks, Qwen2.5-7B-Instruct defaults to BFS, Dijkstra (0.88), a hash map (0.98), a hash set (0.71), DFS for connected components (0.62, where Qwen3-8B writes union find), the naive scan and binary search; kth smallest has no default (quickselect 0.40, size-k heap 0.34) and failed the style re-gate. The model mostly ignores bans (Table 267). Only two sum gave a substitute (brute force in 32 of 46 correct programs). On connected components a ban of DFS raised DFS from 29 to 43 correct programs, with 15 paired slots flipping from union find to DFS, the rebound that naming a forbidden concept can cause [7, 53]. Every one of the 70 programs written under the fourth template attempted the banned default. The shortest path semantic seed barely moved the model (Dijkstra 28, Bellman-Ford 6, against 38 and 5 for the twin). The labellers recognised 51 of 51 references, and the style re-gate passed on 7 of 8 tasks against two blind code judges.

**Table 267.** Behaviour of Qwen2.5-7B-Instruct (twin and ban N = 50, paired slots; forced prompts N = 20 per algorithm). Source: NLA experiment `results/behaviour.json`.

| Task | Default (share of correct twin programs) | Twin pass | Ban: attempts still using the default | Substitute under the ban | Forced adherence of the algorithm used in the causal arm |
|-|-|-|-|-|-|
| grid | BFS (13/13) | 0.26 | 0.68 | none (DFS 3) | none (best other 0.35) |
| shortest path | Dijkstra (38/43) | 0.86 | 0.50 | none (Bellman-Ford/SPFA 9, below 10) | none (Bellman-Ford 0.65, below 0.7) |
| kth smallest | none (quickselect 0.40) | 0.94 | n/a | n/a | excluded (re-gate 26/30) |
| two sum | hash map (49/50) | 1.00 | 0.28 | brute force (32/46) | brute force 1.00 |
| find duplicate | hash set (35/49) | 0.98 | 0.46 | none (Floyd cycle detection 7) | Floyd cycle detection 0.95 |
| connected components | DFS (29/47) | 0.94 | 0.86 | none (DFS 43, union find 2) | union find 0.95 |
| substring search | naive (50/50) | 1.00 | 0.94 | none | KMP 0.90 |
| first and last position | binary search (38/38) | 0.76 | 0.96 | none | bisect module 1.00 (not run) |

**The instrument gate.** The extraction convention that matches the training code reads the output of block 20; it reaches a fraction of variance explained of 0.695 on the reference set against 0.580 for the convention in the release's example, and 0.695 is within 0.06 of the released 0.752. Generic web text and chat give 0.78 and 0.79. Code is out of distribution for this NLA: LeetCode prompts 0.45, HumanEval+ prompts 0.39, CLRS traces 0.33. On the task states the fraction of variance explained, with the reference-set variance as denominator, is 0.512, so the gate is PARTIAL (Table 268).

**Table 268.** Fraction of variance explained of the layer-20 reconstructions on the task states, by position (reference-set denominator). Source: NLA experiment `results/gate.json`.

| Position | Read position | Task specification | Token 1 | Token 2 | Token 4 | Token 8 | Token 16 |
|-|-|-|-|-|-|-|-|
| Fraction of variance explained | 0.65 | 0.50 | 0.48 | 0.28 | 0.64 | 0.57 | 0.51 |

**The NLA never names the planned algorithm before the code.** Two blind judges from different families (Gemini 2.5 Flash Lite and Mistral Small 3.2, both scoring 1.00 on calibration; a third model resolved 1,064 disagreements) mapped each of 6,180 explanations to a catalogue algorithm or to none named (Table 269). Every preregistered readout at the end-of-prompt positions is exactly zero (Table 270). On ban prompts, explanations named the substitute in 0 of 16 states (only two sum had a substitute, so this test is underpowered); on twin prompts they named the default in 0 of 112, as did the text-only reader; on ban failures they named the default the model still writes in 0 of 96. The positive control failed too: on forced `Implement Y` prompts the explanations called Y planned in 0 of 7 tasks, while the text-only reader did so on all of them, and they mentioned the algorithm named in the prompt in 0.7% of cases. The explanations describe the local format line ("no explanation", "a Python code block follows") and confabulate the task (Fibonacci, medians, prime numbers); 4,733 of 5,700 judged explanations name no algorithm at all. At generated tokens the NLA sometimes names the realised algorithm before the visible text identifies it (up to 0.28 at token 8 under the ban), but an outside reader who sees only the prompt and prefix predicts the realised algorithm better, per sample (0.25 against 0.07; exact McNemar 20:88, p 2e-11).

**Table 269.** Agreement between the two judges by mode (EXPL: mapping an explanation; NAME: naming from the visible text; PREDICT: the outside reader's forecast). Source: NLA experiment `results/readout.json`.

| Mode | Raw agreement | Kappa | Unresolved after the third judge |
|-|-|-|-|
| explanation | 0.94 | 0.82 | 0.6% |
| visible text | 0.67 | 0.56 | 1.6% |
| outside reader | 0.77 | 0.75 | 3.9% |

**Table 270.** Preregistered readout tests. Source: NLA experiment `results/readout.json`.

| Test (units) | NLA | Comparator | b : c | p | Verdict |
|-|-|-|-|-|-|
| ban states name the substitute (two sum only; 16 states) | 0/16 | text 0/16 | 0 : 0 | 1 | fail, underpowered |
| same, against swapped, random and outside-reader controls | 0/16 | swapped 0/16, random 0/8, outside reader 0/16 | 0 : 0 | 1 | n/a |
| twin states name the default (7 tasks; 112 states) | 0/112 | text 0/112 | 0 : 0 | 1 | fail |
| forced states name the forced algorithm (7 tasks) | 0.00 on every task | text 1.00 | n/a | n/a | fail |
| ban-failure states name the default still written (6 tasks; 96) | 0/96 | outside reader 0/96, text 0/96 | 0 : 0 | 1 | null |
| per sample, mixed conditions (364 units, 120 samples) | 0.066 correct | outside reader 0.253 | 20 : 88 | 2e-11 | outside reader better |
| generated positions before the identifying token | ban token 8: 0.28; twin token 4: 0.18 | text 0 by construction | n/a | n/a | descriptive |

**The information is local and fades within a sentence (exploratory).** To tell an instrument limit from information that fades along the prompt, the same NLA and judges read states at the token of the algorithm's name inside the condition sentence and at that sentence's final period (220 states, 660 explanations; Table 271). At the name token the explanations mention the algorithm in 80% of forced and 89% of ban states, and they respect the negation: they call it planned in 48% of forced states and in 6% of ban states. Two to eight tokens later, at the end of the sentence, the mention rates fall to 27% and 6%, and about 170 tokens later, at the end of the prompt, to 0.7%. The null therefore says that the pre-code positions do not carry the algorithm choice in a form this NLA puts into words, not that the instrument is blind.

**Table 271.** Local positive control (majority of three explanations per state). Source: NLA experiment `results/local_control.json`.

| Position | Forced: names Y as planned | Forced: mentions Y | Ban: names the default as planned | Ban: mentions the default | Reconstruction cosine |
|-|-|-|-|-|-|
| at the algorithm's name | 0.48 | 0.80 | 0.06 | 0.89 | 0.92 |
| end of that sentence (2 to 8 tokens later) | 0.11 | 0.27 | 0.00 | 0.06 | 0.90 |
| end of the prompt (committed readout, about 170 tokens later) | 0.00 | 0.007 | 0.00 | 0.007 | 0.82 to 0.87 |

[FIGURE:fig_nla_local]

**The preregistered verbal edit fails at the prefill site.** The causal arm replaced the default's name in a twin explanation by an algorithm Y the model writes on request, reconstructed both versions, and patched the difference into the layer-20 states at the last four prompt positions at doses of 1, 2 and 4 (N = 30 paired slots per cell). It failed on all four tasks (Table 272). The edits barely move the reconstruction (cosine 0.9992 between the edited and unedited reconstructions; 0.04 of the state norm per position), the unedited round trip at 0.8 of the norm propagates downstream but moves nothing, and all 15 prefill cells per task stay within 0 to 3 slots of the unedited control. The edit direction is nearly orthogonal to the forced-state difference in means (median cosine 0.09).

**Table 272.** The preregistered causal arm: Y share in the unedited control and the edited-minus-round-trip difference at doses 1, 2 and 4 (N = 30 paired slots). Source: NLA experiment `results/causal.json`.

| Task (default to Y) | Control Y share | Dose 1 | Dose 2 | Dose 4 | Pass |
|-|-|-|-|-|-|
| connected components (DFS to union find) | 10/30 | -0.03 (0:1) | -0.03 (0:1) | +0.03 (3:2) | no |
| two sum (hash map to brute force) | 0/30 | 0 | 0 | 0 | no |
| find duplicate (hash set to Floyd cycle detection) | 12/30 | 0 | +0.03 (2:1) | +0.10 (3:0, p 0.25) | no |
| substring search (naive to KMP) | 0/30 | 0 | 0 | 0 | no |

**Table 273.** Realised push sizes relative to the state norm at block 20. Source: NLA experiment `results/causal.json`.

| Cell | Push norm over state norm |
|-|-|
| edit, dose 1 | 0.041 |
| unrelated-word edit, dose 1 | 0.036 |
| round trip, dose 1 | 0.201 |
| round trip, dose 4 | 0.80 (0.76 at block 27) |

**At the generated-token site and large doses, the verbal edit steers two of four tasks (exploratory).** After the committed nulls, the experiment extended the doses and moved the edit to the read position plus generated tokens 1 to 64 (Tables 274 and 275). On find duplicate the edit at dose 8 (about 0.3 of the state norm at each position) raised Floyd cycle detection from 0.28 to 0.76 (25:1 over 50 paired slots), replicated on fresh slots (15 of 20, 13:0, p 2e-4), and beat a matched random push (28:1), an unrelated-word edit built the same way (12:1, p 0.003) and a norm-matched round trip (13:1, p 0.002); at dose 16 the programs broke (pass 0.37). On two sum brute force rose from 0 to 10 of 50 at dose 8 and to 23 of 30 at dose 16 with a pass rate of 0.90, while the random push never moved it. On connected components only the forced-state difference in means steered (union find 0.80 at dose 16, 15:1); on substring search nothing steered short of breaking the program. The prefill site stayed inert even at dose 16 or at the natural norm of the difference in means. Asking for the algorithm in the prompt remained the ceiling (forced adherence 0.90 to 1.00 on all four tasks), as the AxBench comparison of prompting and steering predicts [34]. The NLA paper itself reports that editing a plan explanation and steering at one token succeeds roughly half the time; this run's success on two of four tasks is of the same kind and is not a reliable control knob.

**Table 274.** Exploratory dose extension (Y share out of 30 paired slots). Source: NLA experiment `results/causal_exploratory.json`.

| Task | Control | Prefill edit, dose 16 | Prefill difference in means at natural norm, dose 2 | Generated-site edit, dose 8 | Generated-site random, dose 8 | Generated-site difference in means, dose 8 | Generated-site difference in means at natural norm |
|-|-|-|-|-|-|-|-|
| connected components (to union find) | 10 | 10 | 9 | 8 | 11 | 19 (10:1, p 0.012) | 13 |
| two sum (to brute force) | 0 | 0 | 0 | 4 (4:0, p 0.125) | 0 | 0 | 0 |
| find duplicate (to Floyd cycle detection) | 12 | 11 | 12 | 23 (12:1, p 0.003) | 8 | 2 | 6 |
| substring search (to KMP) | 0 | 0 | 0 | 0 | 0 | 2 (pass 0.83) | 0 |

**Table 275.** Exploratory follow-up at the generated-token site: dose response, controls built the same way and a replication on fresh slots (Y share; exact McNemar on paired slots). Source: NLA experiment `results/causal_exploratory_followup.json`.

| Task | Edit, dose 4 | Edit, dose 8 (N = 50) | Edit, dose 16 | Dose 8, fresh slots (N = 20) | Dose 8 against random | Dose 8 against unrelated-word edit | Dose 8 against matched round trip | Difference in means, dose 16 |
|-|-|-|-|-|-|-|-|-|
| find duplicate (to Floyd cycle detection) | 0.60 (7:1, p 0.07) | 0.76 against control 0.28 (25:1, p < 1e-6) | 0.30, pass 0.37 | 15/20 (13:0, p 2e-4) | 28:1 | 12:1, p 0.003 | 13:1, p 0.002 | 0.07, pass 0.27 |
| two sum (to brute force) | 0.00 | 0.20 against 0.00 (10:0, p 0.002) | 0.77, pass 0.90 (23:0) | 6/20 (6:0, p 0.03) | 10:0, p 0.002 | 4:0, p 0.125 | 4:0, p 0.125 | 0.37, pass 0.40 |
| connected components (to union find) | 0.33 | 0.24 against 0.36 (3:9) | 0.17 | 4/20 | 5:13 | 6:6 | 2:6 | 0.80 (15:1, p 5e-4) |
| substring search (to KMP) | 0.03 | 0.00 | 0.07, pass 0.27 | 0/20 | 0:0 | 0:0 | 0:0 | 0.03, pass 0.10 |

In activation space (exploratory), read-position states projected on the plane of the forced-prompt states show every forced algorithm in its own region, with twin and ban prompts apart from all of them. Relative to the algorithm-specific directions of the forced prompts, the ban moves the state toward the banned default's own direction on two sum (+0.13), find duplicate (+0.26) and first and last position (+0.15), as the ban sentence names the default, and toward an alternative on shortest path (Bellman-Ford +0.13), connected components (BFS +0.23), substring search and the grid task (DFS +0.18). The novelty audit found 10 correct programs labelled other in every arm: 8 labeller misses (six kth smallest counting sorts built on a counter, two boolean seen-arrays) and 2 degenerate programs, 0 novel. Spend was about USD 2.0 on judges and 2.0 hours on one L4.

## 6.7 Positioning against published work

The positioning audit [ARTIFACT:art_OUuQUYQn5voE], dated 2026-10-22, extended the audits of iterations 4 and 5 to this iteration's claims. A protocol frozen and stamped before the first call drove 126 logged searches over seven lanes, from 2,191 raw hits to 1,820 unique records, 1,401 in the window, and 75 claim rows scored on the occupancy rubric for 67 papers: 3 occupying, 66 adjacent and 6 irrelevant. Its 123 new quotes from 94 sources matched the cached source text and were re-matched by an independent live pass. Table 276 gives the verdict per claim, and Table 277 condenses the 65 rows of its neighbour table; the verbatim quotes are in the audit's evidence files.

**Table 276.** Lane verdicts for the iteration-6 claims as of 2026-10-22. Source: positioning audit `research_report.md`.

| Claim | Lane verdict | Deciding neighbours |
|-|-|-|
| Localization: a low-rank causal plan variable, found by interchange or DAS, decides which algorithm Qwen3-8B writes, validated by generation | partly occupied: the method is occupied, the object is open; the flag for a published localization of algorithm choice did not fire, narrowly | DAS and Boundless DAS [110, 111]; MIB [52]; CDAS, DAS steering validated by generation on refusal and a backdoor [112]; prompt cues only for algorithm choice in code [1] |
| Mediation: the plan subspace mediates which random pushes switch the algorithm | adjacent only | pre-generation planning subspaces; output-sensitive steering components |
| Discreteness under interpolation | adjacent only | categorical and multidimensional feature geometry; manifold steering [27] |
| Ideas not in the tokens, at matched KL | adjacent only | decoding matched to steering's departure; temperature and novelty [37]; forking paths [30] |
| Resampling the plan as a diversity knob | partly occupied: activation noise and latent sampling for diversity are occupied | STARS [71]; noise steering [70]; random embedding injection [84] |
| The plan in words with NLAs | occupied (method): the NLA paper edits a plan explanation and steers with the reconstruction; this run is a replication in a new setting | the NLA paper (Transformer Circuits, May 2026); LatentQA [117]; SelfIE [118]; cautions [119, 120] |
| The plan in Gemma Scope 2 features | partly occupied: SAE-feature steering of reasoning strategies beats prompt and activation baselines | SAE-Steering [121]; AxBench [34] |
| FP8 W8A8 activation rounding inflates perturbation effects | adjacent only in the published record; partly occupied by contemporaneous ICLR 2027 submissions at abstract level | steering under weight-only quantization [116] |

Three of the audit's flags bear on what this run may claim. No source localizes which algorithm a code model will write by interchange or DAS and validates it by scoring the generated programs, so that combination is open; the method itself is DAS. Editing an NLA explanation of a plan and steering with the reconstruction is published, so the NLA arm is a replication on a new object. Steering under quantization has been compared with full precision only for weight-only INT8 and NF4 quantization, with activations kept in 16-bit floating point [116]; no source found measures how dynamic per-token activation rounding changes the effect of random perturbations, which is the question the engine control answered, in the negative. The audit also recorded that community NLAs exist for Qwen3-8B at layer 24, that circuit-tracer ships Qwen-3 transcoders including 8B [123] (so the choice of Gemma for the feature claim needs its reason, which is the natural within-prompt split), and that Gemma Scope 2 dates from 22 December 2025 with instruct SAEs initialised from the pretrained ones.

**Table 277.** The positioning audit's neighbour table, condensed (row; claim; neighbour with venue and version; relation; lane verdict; what this run adds; the baseline a reviewer would ask for). The verbatim quotes behind each row are in the audit's evidence file. Source: positioning audit `research_report.md`, Section 5.

{{table92e}}

## 6.8 Planned but not run

The seventh artifact of the strategy never existed. It was to fit DAS subspaces of rank 1 to 16 at one layer of the task-specification positions in bf16 Qwen3-8B on three training templates and confirm them on two held-out templates (Stage B of the localization claim), test whether a fresh random direction's energy in that subspace predicts its effect (the mediation claim), interpolate and extrapolate the plan coordinate between algorithms (the discreteness claim), measure the plan coordinate's variance across temperatures (the first half of the token claim), resample the plan per generation as a diversity knob (the resampling claim), and draw the request's manifold of algorithms in the fitted plan subspace, with the top-five prohibition placed on it. It was lost at the planning stage: the planning agent returned no plan, so no experiment ran. These claims are untested and open; nothing in this report is a result for them, null or otherwise. The only DAS result of the iteration is Gemma's, at the fork position (Section 6.5).

## 6.9 Comparisons across this iteration's experiments

**Where the choice is held, in three models.** The three internal experiments located the choice in different places, and each location fits that model's behaviour. In Qwen3-8B the states at the task-specification positions carry a ban or an instruction: exchanging them alone reproduces the ban's substitute on shortest path (0.80) and a forced instruction on shortest path (30 of 30) and connected components (28 of 30), while on the direct-route tasks the condition span carries it. In gemma-3-4b-it, which writes two algorithms for one prompt, the choice is made at a single generated token after a shared opening, and edits at the task-specification positions do nothing. In Qwen2.5-7B-Instruct the algorithm is verbalizable at the token that names it and not 170 tokens later, and edits work only at the generated-token site. In all three the read position is inert as a carrier: its exchange transfers nothing on six Qwen3-8B tasks, Gemma's readout there is no better than the text, and the NLA reads only the format line there. Iteration 3's finding that a ban gives way at the opening of the program body and Gemma's fork at response index 32 point at the same moment from two models: the first content token after the function signature.

**The top-five prohibition in two families.** Both models answer a five-name ban by writing a banned algorithm (avoidance 0.00 in Qwen3-8B in iteration 2, in its bf16 rerun here and in Gemma). In Gemma the ban flips the model from its default DFS to its minority BFS and halves its pass rate; in activation space the ban's prompt states sit beside a banned centroid. The activation version of the prohibition breaks programs before it moves the algorithm.

**Novelty, audited again.** No artifact of this iteration found a correct novel algorithm (Table 278).

**Table 278.** Novelty audits of iteration 6. Sources: the novelty audit files of the five artifacts.

| Artifact | Pool | Correct programs outside the catalogue | Final classes | Novel |
|-|-|-|-|-|
| Record audit | the 14 transplant programs that two of three judges had called novel in iteration 5, plus 10 controls and 17 related programs | 14 disputed | known outside the catalogue 10, catalogue variant 2, degenerate 2 | 0 |
| Engine control | every correct off-default or other program, against 18,237 known solutions | up to 237 per engine and task | variants and distant programs of known algorithms (nearest-known pass only) | not judged |
| Exchange and site experiment | every correct program labelled other | 2 | catalogue variant 2 | 0 |
| Gemma feature experiment | 1,450 correct programs | 1 | catalogue variant | 0 |
| NLA experiment | every correct program labelled other, all arms | 10 | labeller miss 8, degenerate 2 | 0 |

## 6.10 What iteration 6 established, what it ruled out, and what it abandoned

Everything below is one model per claim except where a second family is named, at 4B to 8B parameters, on memorised tasks in the style of LeetCode.

**Established.**

1. *Iteration 4's random-push escapes are a property of Qwen3-8B, not of FP8 rounding.* At the same absolute displacement, the same 40 directions and the same slots, bf16 escapes on connected components at 0.65 against 0.725 under W8A8 and on shortest path at 0.15 against 0.20, with per-direction shares ranked alike (Spearman 0.96 and 0.87), and per-sample plan noise reproduces (25 and 22 of 50 against 30 and 22). Activation rounding alone adds nothing; a 5-point per-slot boost on connected components comes from the FP8 weights or the native kernel. Iteration 5's bf16 null belongs to its ban-free unit or its direction seeds.
2. *In Qwen3-8B a ban's substitute and an instruction's algorithm are carried by the residual states at the task-specification positions on the prompt-route tasks.* Exchanging those states alone transfers the ban on shortest path (0.80) and kth smallest (0.57), and a forced instruction on shortest path (30 of 30) and connected components (28 of 30); matched-norm random exchanges and a placebo twin transfer at most 0.13. The condition span carries the ban on the direct-route tasks (two sum 1.00, find duplicate 0.90). The read position carries nothing.
3. *Gemma's BFS-or-DFS choice is made at one generated token,* ` visited` against a blank line, `if` or `queue` at response index 32, about 138 tokens before any algorithm-identifying code, and is readable from the residual stream at that position across prompts (raw ridge R-squared 0.72, SAE Lasso 0.66, text 0.18).
4. *Steering the fork works and costs correctness.* Difference in means moves the fork 2.3 times as far as the SAE clamp at matched norm, both move the plan equally at matched effect, and every edit toward the minority algorithm breaks programs; edits toward the default are clean.
5. *The NLA does not verbalise the planned algorithm at pre-code positions in Qwen2.5-7B-Instruct,* although it names an algorithm at the token where the prompt names it; an outside reader of the text predicts the realised algorithm better than the NLA.
6. *Record repairs.* The landing half is descriptive (17 of 21 per set, 5 of 8 where the twin wrote no alternative, p 0.053); the movability half is not a strong predictor with a moderate relation not excluded (0.15, interval -0.44 to 0.65); the 14 disputed programs are not novel.

**Ruled out, or not supported.**

- *Activation rounding as the cause of the escapes* (the engine claim's preregistered account): W16A8 escapes like bf16 or slightly less, on both tasks.
- *The localization claim's Stage A rule* as preregistered: two sum's task-specification states also transfer brute force at 0.43, above the predicted 0.2.
- *A feature claim for Gemma Scope 2:* the SAE clamp never beats difference in means, and the preregistered feature rule is met by random features.
- *The verbal readout claim:* 0 of 16, 0 of 112 and 0 of 96 at the end of the prompt; the preregistered verbal edit moves nothing at the prefill site.
- *State noise against token temperature at matched KL* in bf16: 12:6 and 7:3 at alpha 2, not significant.

**Withdrawn.**

- *The prefill-site claim in its preregistered form* in bf16: no common support for the condition span, and breakage at alpha 8. Its post-hoc form (alpha 4 or less) puts the read position below the task-specification site on both tasks.

**Dead ends, with the evidence that closed them.**

- *FP8 numerics as an explanation of anything in this run's internal results:* closed by Table 237 and Table 239.
- *The read position as a carrier of the choice:* zero transfer in six Qwen3-8B tasks (Tables 244 to 249), no readout beyond text in Gemma (Table 261), only the format line in the NLA explanations.
- *The released layer-20 NLA as a readout of algorithm plans in code:* code is out of distribution for it (fraction of variance explained 0.39 to 0.45), and its pre-code explanations name no algorithm.

**Planned but not run.** DAS in Qwen3-8B (Stage B), the mediation, discreteness and resampling claims, the temperature half of the token claim, and the causal manifold (Section 6.8).

## 6.11 What the next iteration takes from this one

The plan-variable account was tested in part, and its two halves came out differently. Where the choice is held is now measured in three models: the task-specification states in Qwen3-8B for bans and instructions on the prompt-route tasks, one generated token in Gemma, and nothing verbalisable before the code in Qwen2.5-7B-Instruct. Whether the choice is a low-rank variable in Qwen3-8B, and whether random pushes act through it, is untested, because the DAS experiment was lost at planning. The engine control has removed the obstacle that made such a test look premature: random pushes at iteration 4's absolute unit move the algorithm in bf16 as they did in FP8, so the escapes are a stable target that a fitted plan subspace can be asked to explain. The next measurements are DAS at the task-specification positions of shortest path and kth smallest, with the Stage A exchanges as the full-state ceiling, and the projection of iteration 4's 40 directions onto the fitted subspace.

Three leads come with it. The ban-free unit moves fewer programs than the ban unit at a larger scalar dose, so its per-position and per-block profile, or the direction seeds, decide movability; a controlled comparison of the two units on the same seeds would say which. Gemma's one-token fork offers a clean site where DAS already captures the choice in one direction; whether a smaller push there switches the algorithm without breaking the program is the question for a usable knob. And two sum's task-specification states carry part of a ban that iteration 3 had classed as direct, so the route classes are not all-or-none.
