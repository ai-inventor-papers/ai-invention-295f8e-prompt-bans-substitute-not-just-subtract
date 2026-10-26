## 2.4 Likelihood screen: does a ban substitute, or expose a latent ladder? (Qwen3-8B)

**Why.** This experiment [ARTIFACT:art_6zBfl3kDjeiP] carried the title claim. On the two path search tasks it had to validate the likelihood instrument against events that iteration 1 had already sampled, then measure the full single ban gain matrices (6 by 5 on the grid task, 5 by 4 on the shortest path task) under the five templates and decompose them into a ladder share and an X specific share.

**Design.** The model wrote 1,170 forced programs (10 forced paraphrases per algorithm, three adaptive vLLM rounds), labelled with the canonical labeller, name scrubbed and reverified (Table 53). Scoring ran in HF transformers with bf16 weights but fp32 activations and TensorFloat-32 matrix products, because pure bf16 moved per program log likelihoods by up to 2.1 nats between equivalent computation paths; after the change the cached and full paths agreed within 0.074 nats per program. Throughput on that GPU (1,046 tokens per second) projected 242 minutes for 30 programs per algorithm against a 150-minute budget, so the preregistered cut rule fixed M = 20 programs per algorithm in two halves of 10, and the gate used three baseline paraphrases. In total 684 scoring units ran (one unit is one prompt condition scored on one program set) and 57 were skipped at the GPU deadline. Free-form association answers were sampled 20 times per algorithm; 7% (grid) and 47% (shortest path) were cut at the frozen 32-token limit, so the association profile is weak.

**Table 53.** Forced programs per algorithm (source: `results/yields.json`).

| Task | Algorithm | Forced family | Attempts | Labelled as requested | Yield | Verified after scrub | Scrub mode |
|-|-|-|-|-|-|-|-|
| Grid | BFS | plain | 40 | 40 | 1.00 | 40 | full |
| Grid | DFS | plain | 40 | 40 | 1.00 | 40 | full |
| Grid | bidirectional BFS | plain | 120 | 30 | 0.25 | 30 | full |
| Grid | IDDFS | plain | 40 | 40 | 1.00 | 40 | full |
| Grid | A* | plain | 90 | 32 | 0.36 | 32 | full |
| Grid | unit weight Dijkstra | descriptive | 120 | 92 | 0.77 | 92 | full |
| Shortest path | Dijkstra | plain | 40 | 40 | 1.00 | 40 | full |
| Shortest path | Bellman-Ford/SPFA | plain | 40 | 40 | 1.00 | 40 | full |
| Shortest path | bidirectional Dijkstra | descriptive | 120 | 14 | 0.12 | 11 | comments only (71% of full scrubs failed) |
| Shortest path | Floyd-Warshall | plain | 40 | 40 | 1.00 | 35 | full |
| Shortest path | Dial | descriptive | 120 | 106 | 0.88 | 106 | full |

**The validity gate failed on calibration.** The gate asked three things of the likelihood instrument under the association experiment's own prompts: that the implied probabilities sum to between 0.3 and 3 with at least 0.9 of the mass on the sampled default (calibration), that the implied distribution beat uniform by at least 0.3 nats per sampled program on 19 sampled events (discrimination), and that its argmax match the realised mode on at least 80% of events with a clear mode. Discrimination passed (0.92 nats) and so did the argmax (16 of 19). Calibration failed: the instrument gave DFS a large share of the grid baseline (default share 0.83 on average and 0.44 on one paraphrase) although the association experiment sampled DFS 0 times in 300. Of the 303 gate cells, 298 had an effective sample size below 5, so one or two programs dominated each estimate. The diagnosis is name scrubbing: removing `bfs` and `dfs` identifiers and comments made a forced program much less likely under its own forced prompts than under a neutral prompt, which inflated the weights of minority algorithms. Scored on the unscrubbed programs, with their own proposal denominators, the instrument passed all three criteria (Table 55). By the frozen rule the scrubbed instrument is primary, so every likelihood result of this experiment is descriptive.

**Table 54.** The 19 gate events: realised mode against the likelihood instrument's implied distribution (source: `results/gate.json`; d is the log score over uniform in nats per sampled program).

| Event | Realised mode (allowed labels) | Implied argmax | Hit | d (nats) | Implied shares above 0.01 |
|-|-|-|-|-|-|
| grid baseline | BFS | BFS | yes | 1.31 | BFS 0.66, DFS 0.34 |
| grid ban BFS | DFS | DFS | yes | 1.57 | DFS 1.00 |
| grid mention BFS | BFS | BFS | yes | 1.75 | BFS 1.00 |
| grid mention DFS | DFS | DFS | yes | 1.74 | DFS 1.00 |
| grid mention bidirectional BFS | BFS | bidirectional BFS | no | -1.83 | bidirectional BFS 1.00 |
| grid mention IDDFS | IDDFS | IDDFS | yes | 1.12 | IDDFS 1.00 |
| grid mention A* | A* | BFS | no | -1.75 | BFS 0.78, A* 0.22 |
| grid mention unit weight Dijkstra | BFS | BFS | yes | 1.64 | BFS 0.90, DFS 0.10 |
| grid listing control | BFS | BFS | yes | 1.37 | BFS 0.76, DFS 0.24 |
| grid ban IDDFS | BFS | DFS | no | -2.42 | DFS 0.99, BFS 0.01 |
| shortest path baseline | Dijkstra | Dijkstra | yes | 1.57 | Dijkstra 1.00 |
| shortest path ban Dijkstra | Bellman-Ford/SPFA | Bellman-Ford/SPFA | yes | 1.35 | Bellman-Ford/SPFA 1.00 |
| shortest path mention Dijkstra | Dijkstra | Dijkstra | yes | 1.57 | Dijkstra 1.00 |
| shortest path mention Bellman-Ford/SPFA | Bellman-Ford/SPFA | Bellman-Ford/SPFA | yes | 1.57 | Bellman-Ford/SPFA 1.00 |
| shortest path mention bidirectional Dijkstra | Dijkstra | Dijkstra | yes | 1.57 | Dijkstra 1.00 |
| shortest path mention Floyd-Warshall | Floyd-Warshall | Floyd-Warshall | yes | 1.57 | Floyd-Warshall 1.00 |
| shortest path mention Dial | Dijkstra | Dijkstra | yes | 1.57 | Dijkstra 1.00 |
| shortest path listing control | Dijkstra | Dijkstra | yes | 1.57 | Dijkstra 1.00 |
| shortest path ban Floyd-Warshall | Dijkstra | Dijkstra | yes | 0.64 | Dijkstra 0.98, Bellman-Ford/SPFA 0.02 |

Per baseline paraphrase, the calibration sum S and default share m were 1.55 and 0.70, 2.56 and 0.44, and 1.23 and 0.84 on the grid task, and 0.20 and 1.00, 0.36 and 1.00, and 0.20 and 1.00 on the shortest path task.

**Table 55.** Gate under sensitivity variants (descriptive; the primary verdict is not rechosen; source: `results/gate.json`).

| Variant | Mean S | Mean m | Calibration | Mean d (nats) | Discrimination | Argmax rate | Argmax | All three |
|-|-|-|-|-|-|-|-|-|
| primary (scrubbed, mixture proposal) | 1.02 | 0.83 | fail | 0.92 | pass | 0.84 | pass | fail |
| code body only | 1.02 | 0.83 | fail | 0.92 | pass | 0.84 | pass | fail |
| correct programs only | 0.66 | 1.00 | pass | 0.76 | pass | 0.79 | fail | fail |
| single forced prompt as proposal | 0.99 | 0.94 | pass | 0.99 | pass | 0.84 | pass | pass |
| truncated to 256 tokens | 1.06 | 0.88 | fail | 0.92 | pass | 0.84 | pass | fail |
| unscrubbed | 0.95 | 1.00 | pass | 1.18 | pass | 0.89 | pass | pass |
| unscrubbed, body only, single proposal | 1.01 | 1.00 | pass | 1.11 | pass | 0.89 | pass | pass |

**The substitution test: undetermined.** The between survivor variance of the ban gains is far above replicate noise (F between 16 and 22 under the neutral reference), so the model does not merely subtract. But the pooled X specific share is 0.55 with a 95% interval of [0.25, 0.67] under the neutral twin reference and 0.66 [0.49, 0.87] under the mention twin: both intervals straddle 0.5 and no ladder exists, so the preregistered branch is undetermined, and the same holds under effective sample size weighting (Table 56). The grid task alone reads X specific but unaimed under the mention reference and the weighted variant. Neither rival account fits. The X specific residuals are not aimed at the prime and veto profile (mean Spearman -0.10 against a null 95th percentile of 0.20, p = 0.80) or at the free-form association profile (-0.12, p = 0.77). And the eight generic perturbation profiles do not agree with one another, so there is no coherent ladder to be exposed (Table 57).

**Table 56.** Substitution test: noise corrected ladder and X specific sums of squares and the X specific share (source: `results/c1.json`; 95% intervals by bootstrap over templates, programs and random directions).

| Reference | Scope | Rows | V_u (ladder) | V_s (X specific) | Share | Share 95% CI | V_u + V_s 95% CI | F | Branch |
|-|-|-|-|-|-|-|-|-|-|
| neutral twin (primary) | grid | 6 | 239.28 | 412.46 | 0.63 | [0.28, 0.83] | [501.86, 1505.29] | 15.91 | undetermined |
| neutral twin (primary) | shortest path | 5 | 244.64 | 173.12 | 0.41 | [0.10, 0.61] | [316.25, 947.02] | 22.48 | undetermined |
| neutral twin (primary) | pooled | 11 | 483.93 | 585.58 | 0.55 | [0.25, 0.67] | [924.80, 2106.68] | 17.93 | undetermined |
| mention twin | grid | 6 | 1282.94 | 2525.02 | 0.66 | [0.51, 0.98] | [2573.47, 5471.38] | 57.44 | X specific, unaimed |
| mention twin | shortest path | 5 | 522.29 | 979.57 | 0.65 | [0.26, 0.79] | [1182.96, 2115.91] | 37.69 | undetermined |
| mention twin | pooled | 11 | 1805.23 | 3504.59 | 0.66 | [0.49, 0.87] | [4045.59, 7138.92] | 49.98 | undetermined |
| ESS weighted | grid | 6 | -35.45 | 181.32 | 1.24 | [0.57, 1.62] | [116.32, 331.51] | 15.92 | X specific, unaimed |
| ESS weighted | shortest path | 5 | 48.41 | 50.61 | 0.51 | [-1.09, 2.40] | [74.07, 220.58] | 23.24 | undetermined |
| ESS weighted | pooled | 11 | 12.96 | 231.93 | 0.95 | [0.11, 1.70] | [218.16, 478.69] | 18.21 | undetermined |

**Table 57.** Does a latent ladder exist? Agreement among the eight generic perturbation profiles and the aim of the X specific residual (source: `results/c1.json`).

| Task | Ladder exists (mean centred cosine at least 0.5) | Mean centred cosine | Mean raw cosine | Random edits, seed family A against B (r) | Nonce ban, half 1 against half 2 (r) | Aim at prime and veto | Aim p |
|-|-|-|-|-|-|-|-|
| Grid | no | 0.34 | 0.21 | 0.53 | 0.37 | -0.07 | 0.682 |
| Shortest path | no | -0.02 | -0.07 | -0.26 | 0.82 | -0.14 | 0.787 |

The per row decomposition (Table 58) shows where the X specific variance sits. The modal bans have large X specific residuals: under the BFS ban the largest residual belongs to IDDFS, under the Dijkstra ban to Dial. The bans of DFS, Bellman-Ford/SPFA, Floyd-Warshall and Dial are mostly close to the ladder (cosine of the row with the ladder profile 0.87 to 0.96). The penultimate column measures each ban's effect on its own label, and it carries the experiment's clearest result: banning an algorithm the model never writes raises that algorithm's likelihood, by +2.5 to +26.9 nats in 8 of the 9 bans of absent algorithms (IDDFS +23.5, Floyd-Warshall +15.4, Dial +26.9). Only the two modal bans (BFS -8.25, Dijkstra -4.95) and the ban of A* (-5.93) lower their own label. Naming an algorithm primes it, even inside a prohibition [{{Rana2026}}].

**Table 58.** Per row decomposition under the neutral twin reference (source: `results/c1.json`; a_B^2 is the ladder part and ||s_B||^2 the X specific part of the row, N_u and N_s their noise expectations; D_B is the ban's effect on its own label, L_B(ban) - L_B(neutral), in nats; rho(s, PV) is the row's aim).

| Task | Banned | a_B^2 | N_u | s_B^2 | N_s | cos(row, u) | Replicate SD | Between survivor SD | D_B | rho(s, PV) | Largest residual |
|-|-|-|-|-|-|-|-|-|-|-|-|
| Grid | BFS | 139.75 | 2.04 | 163.48 | 6.13 | 0.68 | 4.04 | 7.79 | -8.25 | -0.25 | IDDFS |
| Grid | DFS | 45.20 | 1.53 | 4.32 | 4.60 | 0.96 | 3.50 | 3.15 | 8.43 | -0.10 | IDDFS |
| Grid | bidirectional BFS | 1.03 | 2.04 | 33.27 | 6.13 | -0.17 | 4.04 | 2.62 | 15.20 | 0.75 | IDDFS |
| Grid | IDDFS | 0.47 | 1.98 | 36.72 | 5.95 | 0.11 | 3.98 | 2.73 | 23.53 | 0.25 | bidirectional BFS |
| Grid | A* | 24.13 | 1.97 | 130.22 | 5.92 | 0.40 | 3.97 | 5.56 | -5.93 | -0.50 | IDDFS |
| Grid | unit weight Dijkstra | 39.63 | 1.36 | 77.23 | 4.07 | 0.58 | 3.29 | 4.83 | 2.51 | -0.60 | IDDFS |
| Shortest path | Dijkstra | 9.02 | 0.92 | 116.45 | 1.84 | 0.27 | 2.63 | 5.60 | -4.95 | 0.00 | Dial |
| Shortest path | Bellman-Ford/SPFA | 119.68 | 1.42 | 27.77 | 2.84 | 0.90 | 3.26 | 6.07 | 10.59 | 0.30 | Floyd-Warshall |
| Shortest path | bidirectional Dijkstra | 41.38 | 2.02 | 33.55 | 4.04 | 0.74 | 3.89 | 4.33 | 3.54 | 0.20 | Dial |
| Shortest path | Floyd-Warshall | 73.89 | 1.37 | 5.98 | 2.74 | 0.96 | 3.21 | 4.47 | 15.40 | -0.60 | Dial |
| Shortest path | Dial | 7.16 | 0.75 | 2.33 | 1.51 | 0.87 | 2.38 | 1.54 | 26.88 | -0.60 | Bellman-Ford/SPFA |

**The iteration-1 sham observations are absorbed by the shared component.** In the Floyd-Warshall ban row the Bellman-Ford/SPFA gain (2.73 nats) equals its fitted ladder part (2.79); its X specific residual is -0.06 [-2.76, 3.67]. The IDDFS to DFS residual is -0.77 [-7.20, 4.02], with a mean gain of -0.45 against a fitted ladder part of 0.33. The two sham promotions of Section 2.3.9 therefore look like the ladder component, not like an X specific promotion.

**Sensitivity.** Every variant keeps the pooled branch undetermined except the gate passing unscrubbed programs (Table 59). Scored raw, with the first template only (the only one scored on raw programs), the pooled X specific share is 0.69 [0.51, 0.84], X specific but unaimed on the grid task and undetermined on the shortest path task; the matched scrubbed value is 0.55 [0.18, 0.78]. The aim cannot be tested in that variant, because mention twins were not scored on raw programs.

**Table 59.** Pooled X specific share under sensitivity variants (source: `results/sensitivity.json`).

| Variant | Pooled share | 95% CI | Pooled branch | Aim |
|-|-|-|-|-|
| code body only | 0.55 | [0.25, 0.68] | undetermined | -0.10 |
| correct programs only | 0.42 | [0.18, 0.57] | undetermined | -0.17 |
| single forced prompt as proposal | 0.54 | [0.26, 0.68] | undetermined | -0.09 |
| truncated to 256 tokens | 0.45 | [0.25, 0.64] | undetermined | -0.11 |
| ladder profile with the iteration-1 steering setting added | 0.55 | [0.25, 0.68] | undetermined | -0.10 |
| ladder profile, unit normalised | 0.42 | [0.25, 0.66] | undetermined | -0.08 |
| ladder profile from the nonce ban only | 0.33 | [0.24, 0.77] | undetermined | 0.10 |
| ladder profile from random edits only | 0.64 | [0.37, 0.89] | undetermined | 0.04 |
| ladder profile from the novelty instruction only | 0.72 | [0.30, 0.81] | undetermined | -0.09 |
| unscrubbed, first template only | 0.69 | [0.51, 0.84] | X specific, unaimed | n/a |
| unscrubbed, body only, single proposal, first template | 0.67 | [0.51, 0.84] | X specific, unaimed | n/a |
| primary, first template only | 0.55 | [0.18, 0.78] | undetermined | -0.16 |

**Double bans.** The instrument put essentially all mass on the banned pair under the cumulative bans: 1.00 on both tasks with the frozen templates, against the association experiment's sampled banned shares of 0.94 (grid, mechanism level) and 1.00 (shortest path). It predicted the failure the succession hit in iteration 1. It placed the remaining mass on IDDFS 0.73 and A* 0.27 (grid) and on Floyd-Warshall 1.00 (shortest path) under the frozen templates, and on IDDFS 0.43, A* 0.33 and unit weight Dijkstra 0.24 (grid) and Floyd-Warshall 0.987 (shortest path) under the association experiment's own step-2 prompts. The six not banned grid programs that experiment sampled were unit weight Dijkstra 4, A* 1 and IDDFS 1. An sham ban outside the catalogue (jump point search, three of five templates) did not single out A*, its declared neighbour, in its residual; the other shams outside the catalogue and the iteration-1 steering setting as a generic perturbation were not run before the GPU deadline, and neither was the planned extension of the gate to the other four iteration-1 draws.

**Coverage and effective sample size.** The forced programs cover the natural ones unevenly (Table 60): well for Dijkstra and Floyd-Warshall (nearest neighbour shingle Jaccard 0.94 to 0.95), poorly for Bellman-Ford/SPFA (0.54) and grid unit weight Dijkstra (0.42). Outside the forced cells, the median effective sample size of a half cell is 1.0 to 1.4 (Table 61).

**Table 60.** Coverage of naturally sampled programs by the forced programs (source: `results/coverage.json`; Jaccard over identifier normalised AST shingles).

| Task and algorithm | Natural programs | Share with nearest forced Jaccard at least 0.5 | Mean nearest Jaccard |
|-|-|-|-|
| Grid BFS | 1102 | 0.69 | 0.66 |
| Grid DFS | 262 | 0.56 | 0.59 |
| Grid bidirectional BFS | 5 | 0.60 | 0.49 |
| Grid IDDFS | 37 | 0.73 | 0.58 |
| Grid A* | 29 | 0.48 | 0.57 |
| Grid unit weight Dijkstra | 12 | 0.17 | 0.42 |
| Shortest path Dijkstra | 1004 | 0.96 | 0.94 |
| Shortest path Bellman-Ford/SPFA | 251 | 0.40 | 0.54 |
| Shortest path Floyd-Warshall | 43 | 1.00 | 0.95 |

**Table 61.** Effective sample size of the importance weights per condition family (source: `results/ess_table.json`).

| Task | Condition family | Half cells | Median ESS | Share below 5 |
|-|-|-|-|-|
| Grid | ban | 516 | 1.13 | 0.99 |
| Grid | baseline | 12 | 1.07 | 1.00 |
| Grid | random edits | 72 | 1.19 | 0.99 |
| Grid | iteration-1 gate prompts | 228 | 1.21 | 0.98 |
| Grid | forced prompts | 120 | 5.61 | 0.43 |
| Grid | mention | 360 | 1.20 | 0.96 |
| Grid | neutral | 516 | 1.08 | 0.98 |
| Grid | novelty | 12 | 1.10 | 1.00 |
| Shortest path | ban | 350 | 1.17 | 0.97 |
| Shortest path | baseline | 10 | 1.40 | 1.00 |
| Shortest path | random edits | 60 | 1.08 | 0.97 |
| Shortest path | iteration-1 gate prompts | 175 | 1.28 | 0.98 |
| Shortest path | forced prompts | 100 | 3.69 | 0.70 |
| Shortest path | mention | 250 | 1.11 | 0.94 |
| Shortest path | neutral | 350 | 1.27 | 1.00 |
| Shortest path | novelty | 10 | 1.02 | 1.00 |

**Checks and what was frozen.** Synthetic tests of the analysis code recovered a planted ladder (share 0.00), a planted X specific pattern (share 1.00), unbiased noise correction and a planted aim (p = 0.00025). An independent rederivation matched the gate, the shares, the aim and every cell to within 1e-15, and a placebo aim sat at its null (mean 0.0007, SD 0.122, against the observed -0.105). The aim profiles, the ladder profile, the templates, nouns and padding, and the code hashes were frozen in a hash chain for the confirmation bench. The experiment's own recommendation, which the Llama replication and the bench inherit, is to score unscrubbed or name matched programs.

## 2.5 Route experiment: does a ban act through the prompt states or at generation time?

**Why.** The hypothesis update predicted that the algorithm specific part of a ban travels by a direct route, with generated tokens reading the prohibition and vetoing X at its signature tokens, and that the read position carries only how strongly the ban will be obeyed. This experiment [ARTIFACT:art_8_ULPE8jJQc_] tested the route causally on the modal bans of both tasks (BFS on the grid task, Dijkstra on the shortest path task), in Qwen3-8B in bf16.

**Design.** Because each ban prompt and its neutral twin have the same token length and identical tokens from the task text onward, their key and value (KV) caches can be spliced position by position, an interchange intervention on cached states in the sense of activation patching [{{Zhang2023}}]. One arm is the full ban and one the full neutral twin. In the *prompt route* arm, generated tokens see the neutral condition segment but the task specification and read position cache entries computed under the ban, so they can learn about the ban only through states that read it. In the *direct route* arm, generated tokens see the ban segment but task specification and read position entries computed under the neutral twin, so they can learn about the ban only by attending to it directly. Two further arms splice only the read position or only the task specification states. A placebo arm splices between two neutral nouns. Attention knockouts [{{Geva2023}}] block attention from generated tokens to the condition segment for all generated tokens, for the first 16 only or after the first 16, and in three bands of 12 layers; the same full knockout applied to the neutral prompt measures generic damage. The primary readout is the likelihood drop of the banned algorithm X, D_X(arm) = L_X(arm) - L_X(neutral twin), over 30 self written, name scrubbed programs per algorithm (323 forced programs in all). The route fractions are F_prompt = D_X(prompt route) / D_X(full ban) and F_direct = D_X(direct route) / D_X(full ban), with F_R and F_spec defined the same way for the read position only and task specification only arms, all bootstrapped over templates and programs. The decision rule was hash committed before any arm was scored: the ban acts directly if F_direct is at least 2/3 with an interval above 1/2, and is decided before writing if F_prompt meets the same bar. Behaviour was sampled 100 times per arm and task (five templates by 20) under common random numbers: one uniform stream per sample shared by every arm, inverse CDF sampling in vocabulary order and a constant batch shape.

**The ban is carried by the prompt states.** Under the preregistered readout the ban is decided before writing on both tasks, and the decision is robust (Table 62). Pooled over tasks, the prompt route carries 0.85 [0.61, 1.20] of the likelihood drop and the direct route 0.00 [-0.08, 0.12]. The read position alone carries nothing (F_R about 0); the task specification states carry it (0.86 and 0.81). The placebo splice moved the banned algorithm by 1.2% (grid) and 0.7% (shortest path) of the ban effect, and the full knockout on the neutral prompt cost only -0.21 and -0.28 nats. Leaving out one template at a time kept F_prompt between 0.68 and 0.99 on the grid task and between 0.74 and 0.91 on the shortest path task, and all four preregistered sensitivity analyses gave the same branch (unweighted mean log likelihood: F_prompt 0.70 and 0.82; correct programs only; the generating paraphrase as denominator; no ESS weighting).

**Table 62.** Likelihood drop of the banned algorithm per arm, in nats, with 95% bootstrap intervals over templates and programs (source: `results/analysis.json#route_frlp`).

| Arm | Grid (ban BFS) | Shortest path (ban Dijkstra) |
|-|-|-|
| a, full ban | -12.25 [-20.9, -6.9] | -5.78 [-7.9, -3.1] |
| c, prompt route | -10.65 [-12.3, -9.6] | -4.73 [-6.2, -3.1] |
| d, direct route | -0.23 [-3.0, 0.8] | 0.22 [-0.3, 0.8] |
| e, read position only | 0.00 [-0.4, 0.2] | -0.11 [-0.3, 0.0] |
| f, task specification only | -10.48 [-12.5, -9.3] | -4.66 [-6.1, -3.2] |
| full knockout of the condition segment | -11.65 [-13.6, -9.9] | -5.42 [-6.6, -3.9] |
| knockout, first 16 generated tokens | -10.74 [-15.5, -9.5] | -5.31 [-6.7, -3.5] |
| knockout, after 16 generated tokens | -11.56 [-15.7, -6.8] | -5.91 [-7.8, -3.5] |
| knockout, layers 0 to 11 | -13.88 [-22.3, -7.7] | -5.88 [-8.0, -3.1] |
| knockout, layers 12 to 23 | -8.29 [-11.4, -4.2] | -4.93 [-6.3, -3.3] |
| knockout, layers 24 to 35 | -14.38 [-20.1, -11.5] | -5.24 [-7.3, -2.9] |
| full knockout on the neutral prompt (generic damage) | -0.21 [-0.6, 0.6] | -0.28 [-0.6, -0.0] |
| mention twin | 0.55 [-0.3, 2.1] | -0.17 [-0.7, 0.4] |
| F_prompt [95% CI] | 0.87 [0.55, 1.50] | 0.82 [0.62, 1.20] |
| F_direct [95% CI] | 0.02 [-0.10, 0.18] | -0.04 [-0.25, 0.05] |
| F_spec / F_R | 0.86 / 0.00 | 0.81 / 0.02 |
| interaction D(a) - D(c) - D(d) | -1.37 [-7.97, 3.86] | -1.27 [-2.55, -0.00] |
| Pooled (ratio of sums) | F_prompt 0.85 [0.61, 1.20]; F_direct 0.00 [-0.08, 0.12]; branch: decided before writing, robust | |

[FIGURE:fig_route]

The knockouts agree. Blocking the condition segment for every generated token restores 5% (grid) and 6% (shortest path) of the likelihood gap, with intervals that include zero. By layer band, blocking layers 12 to 23 restores 32% [16%, 56%] on the grid task and 15% on the shortest path task, layers 0 to 11 restore about nothing, and layers 24 to 35 restore -17% (interval includes zero) on the grid task and 9% [2%, 16%] on the shortest path task. Whether the veto is read early or late in generation could not be determined (first-16 minus after-16 restoration 0.07 [-0.47, 0.20] and 0.10 [-0.03, 0.18]).

**Behaviour qualifies the grid result.** On the shortest path task behaviour matches the likelihood readout exactly: the prompt route arm reproduces the ban (banned share 0.13 against 0.11) and the direct route arm is the baseline (0.95 against 0.99). On the grid task the prompt route reproduces only part of the ban (0.57 against 0.14), and the direct route also moves it (0.70). A supplementary arm that hides the condition segment from every generated token brought BFS back to 0.47 [0.38, 0.57], close to the prompt route arm (McNemar p = 0.13), so on the grid task generated tokens do read the ban directly as well. That reading is redundant over time: blocking only the first 16 generated tokens or only the rest leaves the ban intact (banned shares 0.16 and 0.19). The behavioural route fractions are 0.50 [0.39, 0.62] (prompt) and 0.35 [0.25, 0.45] (direct) on the grid task, and 0.98 [0.89, 1.07] and 0.05 [0.01, 0.09] on the shortest path task. Matched pairs are clean: no sample was banned under the ban and not banned under its neutral twin (0 of 86 and 0 of 88 discordant pairs in that direction).

**Table 63.** Behaviour per arm under common random numbers (N = 100 per arm; mechanism labels of attempted programs; banned share with Wilson 95% interval; source: `results/analysis.json#behaviour`, `results/supplementary.json`).

| Task | Arm | Banned share [95%] | Pass rate | Labels | Banned programs per template (first to fifth, 20 each) |
|-|-|-|-|-|-|
| Grid | b, neutral twin | 1.00 [0.96, 1.00] | 0.92 | BFS 100 | 20, 20, 20, 20, 20 |
| Grid | d, direct route | 0.70 | 0.81 | BFS 70, DFS 30 | 15, 12, 17, 20, 6 |
| Grid | c, prompt route | 0.57 [0.47, 0.66] | 0.61 | BFS 57, DFS 43 | 10, 15, 6, 12, 14 |
| Grid | a, full ban | 0.14 [0.09, 0.22] | 0.41 | DFS 86, BFS 14 | 0, 0, 0, 14, 0 |
| Grid | full knockout (supplementary) | 0.47 [0.38, 0.57] | n/a | BFS 47, rest not BFS | n/a |
| Grid | knockout, first 16 tokens | 0.16 | 0.46 | DFS 84, BFS 16 | 1, 0, 1, 14, 0 |
| Grid | knockout, after 16 tokens | 0.19 | 0.49 | DFS 81, BFS 19 | 1, 2, 1, 11, 4 |
| Shortest path | b, neutral twin | 0.99 | 0.99 | Dijkstra 99, Bellman-Ford/SPFA 1 | 20, 20, 20, 19, 20 |
| Shortest path | d, direct route | 0.95 | 0.99 | Dijkstra 95, Bellman-Ford/SPFA 5 | 19, 18, 20, 19, 19 |
| Shortest path | c, prompt route | 0.13 | 0.91 | Bellman-Ford/SPFA 87, Dijkstra 13 | 6, 1, 3, 1, 2 |
| Shortest path | a, full ban | 0.11 | 0.91 | Bellman-Ford/SPFA 86, Dijkstra 11, other 3 | 1, 0, 4, 5, 1 |
| Shortest path | full knockout (supplementary) | 0.06 | n/a | Dijkstra 6, rest not Dijkstra | n/a |
| Shortest path | knockout, first 16 tokens | 0.11 | 0.94 | Bellman-Ford/SPFA 88, Dijkstra 11, other 1 | 2, 1, 5, 3, 0 |
| Shortest path | knockout, after 16 tokens | 0.11 | 0.96 | Bellman-Ford/SPFA 89, Dijkstra 11 | 3, 0, 4, 3, 1 |

On the grid task, all 14 BFS programs that survived the full ban came from the fourth template (`X is not allowed here`, with BFS as X), which gave 14 of 20 BFS while the other four templates gave 0 of 20.

**Where the ban acts: the first line.** Under the neutral twin, 99% of programs open with an import line (`from collections import deque` on the grid task, `import heapq` on the shortest path task). Under the grid ban, none of 100 programs opens with an import line, including the 14 BFS programs that survive; they open with `def solve(...)` (Table 64). The prompt route arm and every knockout also open without an import, while the direct route arm still opens with one 85% of the time. On the shortest path task the Bellman-Ford/SPFA programs written under the ban mostly open with `from collections import deque`, so the share of import openings stays at 61 to 67% under the ban, the prompt route and the knockouts, and 99% under the direct route. Per-token localisation agrees. On the grid task 63% of the likelihood drop under the full ban, 90% under the prompt route and 95% under the full knockout sits in the first 16 tokens; on the shortest path task almost all of it does. The signature tokens themselves (`deque`, `heapq` and their neighbours) carry only 2.4% (grid) and 11.6% (shortest path) of it. The small direct route drop on the grid task lies later in the program (6% of it in the first 16 tokens). We call this the *opening line veto*: the prompt states suppress the default program's first line before any algorithm specific token is written. On the grid task, the algorithm chosen after `def solve` also depends on direct reads of the ban, and the likelihood readout, dominated by the opening fork, calls the grid task prompt route while its behaviour is mixed.

**Table 64.** Share of programs whose first line is an import (source: `results/supplementary.json#opening_lines`; N = 100 per arm).

| Task | b, neutral | d, direct route | c, prompt route | a, full ban | full knockout | knockout, first 16 | knockout, after 16 |
|-|-|-|-|-|-|-|-|
| Grid | 0.99 | 0.85 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| Shortest path | 0.99 | 0.99 | 0.61 | 0.62 | 0.67 | 0.67 | 0.60 |

**A supplementary readout with natural proposals.** Rescoring, under every arm, the BFS and Dijkstra programs sampled in the neutral arm (exact draws from the neutral prompt's distribution) gives the same ordering with a larger direct share: pooled F_prompt 0.57 [0.41, 0.85] and F_direct 0.16 [0.11, 0.21] (grid 0.58 and 0.18, shortest path 0.56 and 0.11), and the two routes are superadditive on both tasks. Neither likelihood readout is a calibrated probability ratio. The importance weight ESS is about 1 to 3 of 30 programs for the grid full ban arm (8 to 20 on the shortest path task), 858 of the 1,095 cells have ESS below 5, and exp(D) under the natural readout is 3e-7 on the grid task against a behavioural ratio of 0.14. The readouts measure how strongly typical banned algorithm programs, which begin with the import line, are vetoed.

**Where the substitute rises.** Under the full ban the survivors' likelihood gains on the grid task were DFS +9.46, IDDFS +18.40, bidirectional BFS -0.22, A* -0.80 and unit weight Dijkstra -3.53 nats; on the shortest path task Bellman-Ford/SPFA +2.53, bidirectional Dijkstra +30.64, Floyd-Warshall +12.64 and Dial +6.79. The prompt route arm reproduces this profile (cosine 0.94 [0.85, 0.99] grid, 0.95 [0.90, 0.99] shortest path); the direct route arm reproduces it on the shortest path task (0.98 [0.80, 1.00]) but not reliably on the grid task (0.71 [-0.18, 0.94]). The logit lens and a tuned lens [{{Belrose2023}}] at the planned commitment token (the token after `from` or `import`) found no veto layer: the banned set's rank there is unchanged by the ban (0 of 59 grid and 0 of 60 shortest path programs), because the fork has already happened at the first token. The grid substitute set (DFS) rises from layer 28 (59 of 59 programs; tuned lens median 27). In substitute programs written under the full ban, the banned set is vetoed late (median layer 30 on the grid task, 36 on the shortest path task). The tuned lens beat the logit lens on held-out KL at all 11 probed layers (0.29 against 10.6 at layer 21).

**Does the read position know how hard a ban will be obeyed?** The compliance test regressed the banned share of each wording on the projection of its read position state onto a shared ban direction, the mean ban minus neutral shift estimated leaving one experiment out. It used 110 wordings in 12 experiment by task cells: ten modal ban paraphrases from each of the five iteration-1 draws per task, plus this experiment's five templates per task. The combined within cell Spearman correlation is -0.41 [-0.69, -0.17], one sided stratified permutation p = 0.0003 (Holm adjusted over the two axes tested, 0.0006). The preregistered bar was -0.5, so the result is partial: wordings that move the read position further along the ban direction are obeyed more, but less tightly than predicted. The correlation beats 98.5% of 200 random directions (null mean -0.01), and the split half noise ceiling is about 0.77. The decommitment axis of iteration 1 carries nothing (rho 0.05, p = 0.68). The DFS share among programs not banned is not decodable beyond the projection (change in R squared below zero, permutation p = 0.74 on the grid task; not testable on the shortest path task). The recomputed read position states matched the iteration-1 caches (cosine at least 0.9994 for 40 geometry and 60 decommitment prompts).

**Table 65.** Within cell Spearman correlation between a wording's banned share and its read position projection (source: `results/c5.json`; ten wordings per cell, five for this experiment's templates).

| Cell | Shared ban direction | Decommitment axis |
|-|-|-|
| Association, grid | -0.701 | 0.234 |
| Association, shortest path | -0.811 | 0.416 |
| Geometry, grid | -0.214 | -0.082 |
| Geometry, shortest path | -0.673 | -0.132 |
| Forking token, grid | -0.437 | 0.212 |
| Forking token, shortest path | 0.271 | 0.516 |
| Decommitment, grid | -0.074 | 0.309 |
| Decommitment, shortest path | -0.605 | -0.368 |
| Instruction tuning, grid | 0.036 | 0.207 |
| Instruction tuning, shortest path | -0.171 | -0.734 |
| This experiment's templates, grid | -0.707 | 0.0 |
| This experiment's templates, shortest path | -0.667 | 0.308 |
| Combined [95% CI]; one sided p | -0.41 [-0.69, -0.17]; p = 0.0003 | 0.05 [-0.30, 0.36]; p = 0.68 |

**Checks.** Spliced caches reproduced the full ban scores bit for bit; the knockout attention with nothing blocked equalled stock attention (largest difference 0); attention to blocked columns was exactly 0. Repeated sampling was 100% identical at a fixed batch shape and only 40% when the shape changed, which is why every arm shares one shape. Two independent rederivations reproduced 49 and 59 headline numbers with no mismatch; McNemar on randomly swapped arm labels rejected 4.0 to 4.4% of the time, the likelihood ban effect's interval included zero for the placebo splice and for label shuffled data, and the compliance test rejected 0 of 40 shuffled data sets. From the declared dataset dependency, other models' other than Dijkstra choices for weighted shortest path in the inspiration repository spread over Bellman-Ford/SPFA (37%), bidirectional search (32%) and other algorithms (23%), while Qwen3-8B under the Dijkstra ban lands on Bellman-Ford/SPFA 97% of the time; an import opening is the norm in LLM written solutions that name these algorithms (KodCode: BFS 94% of 17, Dijkstra 100% of 40) but not in human library code (TheAlgorithms: 29% of 7 and 17% of 12).

