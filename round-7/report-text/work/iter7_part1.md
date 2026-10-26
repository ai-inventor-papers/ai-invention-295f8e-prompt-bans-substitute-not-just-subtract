# Iteration 7: a fitted plan subspace, the fork where the algorithm is decided, temperature through the fork, the dose unit, evolutionary search, and a circuit in Gemma

## 7.1 Why this iteration ran what it ran

**The review of the iteration-6 record.** The review was blocking. It raised five major items and seven minor ones. The first major item went to Stage A, the cleanest internal positive of the run. The record had reported the transfer counts of Stage A as counts of correct programs when they were counts of attempts labelled with the ban's substitute, so a reader could not tell how many of the transferred programs passed. The second said the post-hoc site ordering had been stated as if it held on both clauses when its condition-span clause failed. The third went to Gemma: the record had called a rank-1 DAS subspace one-dimensional without the controls that would license the word, had quoted an unstandardised SAE ridge, and had said every edit lowered the pass rate when the SAE top-five clamp did not. The fourth said the closing merged quantities measured in three models at three sites into one account. The fifth was coverage: the DAS experiment had been lost at planning, and the geometry plots that the request asks for in activation coordinates had no figure markers in the record. The minor items asked for the dose of the top-five push against the forced-prompt manifold, a correct-only version of Table 238, a fix for pseudoreplication in the NLA contrast, three executed checks that the record named but did not report, a wrap of the overlong Section 4.9, a positioning row for the fork, and the 2x2 of dose unit against direction seeds before any re-pricing of plan noise.

**Table 280.** Review items on the iteration-6 record and where this report answers them.

| Review item | What the review found | Where it is answered |
|-|-|-|
| Stage A metric | Attempts reported as correct programs; no correct column | Corrections in Sections 6.4.1 and 6.10; Section 7.2 (Tables 284 and 285) |
| Post-hoc site | The ordering overstated; the condition-span clause fails | Corrections in Sections 6.4.2 and 6.10 and in the closing; Table 254b; Section 7.2 |
| Gemma claims | One-dimensionality without controls; unstandardised SAE ridge; the claim that every edit lowered the pass rate | Corrections in Sections 6.5, 6.10 and 6.11; the controlled DAS of Section 7.8 |
| Synthesis | Quantities from three models merged | Corrections in Sections 6.9, 6.10 and 6.11; Table 279 in Section 6.9; the closing section |
| Coverage | DAS lost; no geometry figure markers | Section 7.3 (DAS); seven geometry figures placed in Sections 6.4.4, 6.5 and 6.6 |
| Minor: top-five push dose | Doses of 1 to 8 ban units overshoot the forced-prompt manifold | Corrections in Sections 6.4.4 and 6.9 and in the closing; the in-manifold push of Section 7.4.7 |
| Minor: Table 238 | Attempts only | Correct-only rows and the MIXED verdict in Section 6.3; Table 286 |
| Minor: NLA pseudoreplication | Several units per sample counted as independent | Corrections in Sections 6.6 and 6.10; Table 287 |
| Minor: executed checks | The empty-prefix resampling test at the Gemma fork, the list of what the Gemma experiment did not run, and three engine-control programs labelled other, all unreported | Corrections in Sections 6.5, 6.8 and 6.9; Table 288 |
| Minor: Section 4.9 | Unwrapped | Rewrapped in place |
| Minor: fork positioning | No row for the fork against published work | Row 66 of Table 277 in Section 6.7 |
| Minor: 2x2 | Dose unit and direction seeds confounded in iteration 5 | Verdict tags in Sections 5.7, 5.11 and 6.2.4 and in the closing; Section 7.6 |

**The hypothesis update.** The update kept the plan and added a fork. We call it the *plan-and-fork account*. While the model reads the task, the residual states at the task-specification positions carry a low-rank variable that sets which algorithm the model will write; during generation, the program opens with tokens that every algorithm shares, and the variable is realised at the first token where continuations of different algorithms part. We call that token the *fork*, a forking token in the sense of Bigelow et al. [30]. The *fork margin* is the teacher-forced log-odds, at the fork, of the default class of tokens against the off-default class. If the account holds, three things follow. A low-rank subspace fitted by DAS [110, 111] should carry the transfer of a ban or a forced instruction, under the controls that would expose a spurious fit. A random push should change the algorithm in proportion to how far it moves the fork margin. And temperature should act on the algorithm only through the fork: at temperature T, the off-default share at the fork is the softmax of the fork logits divided by T, so the account predicts each temperature's share from the logits alone, before sampling.

Ten claims were preregistered, each with a rule committed by sha256 before its first decisive sample. We call them by their content.

- *The fork claim* (primary): the teacher-forced fork margin under each of 40 equal-dose random pushes predicts which pushes change the algorithm, on connected components and shortest path.
- *The DAS claim* (primary): a DAS map of rank 16 or less at the site of Stage A recovers at least 0.8 of the full-state transfer (the transfer when every residual state at that site is exchanged, which we call the *full state exchange*) in held-out generation, beats random subspaces of the same rank, and survives a permuted-label fit and a fit on a randomly initialised network [132].
- *The routing claim*: whether an edit in the fitted subspace lands where the forced source points (categorical) or follows a margin toward the ban's usual substitute.
- *The axis claim*: the projection of a random push on a default-to-runner-up axis predicts and mediates its effect; we call *second choice* the algorithm a model ranks second on a task, the ⟦runner-up⟧ of earlier sections.
- *The temperature claim*: at mixed units, the algorithm given the fork token's class is nearly certain, the off-default share at each temperature follows the fork logits divided by T, and on the collapsed tasks the fork margin is large enough that no temperature in range reaches the alternative.
- *The manifold claim*: in the fitted subspace, bans sit outside a paraphrase null and seeds and instructions sit inside it.
- *The discreteness claim*: scaling the fitted edit from 0 to 1.5 changes the algorithm as a step, not a ramp.
- *The dose-unit claim*: the 2x2 of dose unit (the absolute unit of iteration 4 against the ⟦ban-free unit⟧ of iteration 5; we call the latter the *relative unit*, because it scales the noise to a fixed fraction of the twin's residual norm) by direction seeds (those of iteration 4 against those of iteration 5) says which explains iteration 5's weak plan noise, and plan noise is then re-priced at the unit that moves.
- *The Gemma claims*: temperature through the fork in a second family, DAS at Gemma's fork with the full set of controls, and a validated circuit for the fork margin.
- *The search claim*: an evolutionary program search with an executable evaluator writes correct out-of-catalogue programs at least 10 times as often per call as the best single-sample knob, on at least two tasks.

**The strategy.** Seven artifacts ran (Table 281). The record audit repaired the record from rows on disk and ran the checks the review asked for. A DAS experiment fitted the plan subspace on Qwen3-8B [5] and tested it in generation. A fork experiment located forks by prefix resampling and tested the fork and axis claims. A temperature experiment tested the temperature claim on the three units where the instruct twin is already mixed. A dose-unit experiment ran the 2x2 and re-priced plan noise. A search experiment ran FunSearch-style evolution [81] over a MAP-Elites archive [133]. A Gemma experiment ran temperature, DAS and a circuit at Gemma's one-token fork.

**Table 281.** The artifacts of iteration 7, the question each was asked, and its compute and spend.

| Artifact | Question | Model and compute | OpenRouter spend |
|-|-|-|-|
| Record audit [ARTIFACT:art_LzP2qPwUrANz] | Repair the iteration-6 record (54 corrections); run the checks the review named | No generation; CPU only | USD 0.077 |
| DAS experiment [ARTIFACT:art_veI9l_Rb9wDY] | Does a fitted low-rank subspace of the task-specification states carry the choice, under permuted-label, random-initialisation and dormancy controls? | Qwen3-8B bf16, thinking off; 4,500 programs; about 1.6 GPU hours | USD 0.13 |
| Fork experiment [ARTIFACT:art_pHL7LWNhpcCS] | Where is the algorithm decided in generation; does the fork margin, or an axis projection, predict which random pushes escape? | Qwen3-8B bf16; 4,220 programs and 4,560 continuations; 0.63 GPU hours | USD 0.028 |
| Temperature experiment [ARTIFACT:art_MZAfDPVhM6Ui] | Does temperature act on the algorithm only through the fork logits? | Qwen3-8B bf16; 2,290 programs and 12,676 continuations; about 0.75 GPU hours | USD 0.022 |
| Dose-unit experiment [ARTIFACT:art_8O5eaNc5gxJs] | Is iteration 5's weak plan noise the dose unit or the direction seeds; what does plan noise cost at the unit that moves? | Qwen3-8B bf16, one RTX 4090; about 0.7 GPU hours | USD 0.10 |
| Search experiment [ARTIFACT:art_VhaHGe7SxV95] | Does evolutionary search with an evaluator and a novelty critic find correct out-of-catalogue programs faster than single-sample knobs? | Qwen3-8B bf16 on vLLM 0.11.0, one RTX A4500; about 1.0 GPU hour | USD 0.89 |
| Gemma experiment [ARTIFACT:art_HY7uYZz-OjRW] | Temperature, controlled DAS and a validated circuit at Gemma's fork | gemma-3-4b-it [76] bf16, one 16 GB GPU | USD 0.044 |

## 7.2 The record audit: 54 corrections and the checks the review named

The record audit [ARTIFACT:art_LzP2qPwUrANz] read the iteration-6 report against the rows on disk and wrote 54 corrections, each a replacement, a table replacement or an insertion. All 54 apply exactly once to the report as it stood, and all of them are now in place, each marked as an iteration-7 correction with what changed and why. Of the 724 values the corrections touch, 603 match the rows, 117 are new (the correct columns of Stage A, the one-unit-per-sample NLA tests, the executed checks), one is carried from an earlier artifact, and 3 are corrected. The three corrected values are venue expectations of the plan that the live records contradict. A residual-claim lint flagged 16 sentences in the uncorrected report and none after correction. An independent re-derivation through the standard library ran 520 checks with no mismatch, and seven placebos, each a deliberately wrong input, failed as they must (Table 282).

**Table 282.** The record audit's own checks.

{{e6_checks}}

Table 283 lists every correction with the review item behind it, where it sits and the first sentence of its rationale. Corrections 27, 28, 44, 45, 48, 53 and 54 touched the closing section, which this report then rewrites in full.

**Table 283.** The 54 corrections of the iteration-6 record.

{{e6_corrections}}

**Stage A in correct programs.** The review's first item is answered by counting correct programs beside attempts (Table 284). The ban's substitute transfers into the neutral twin on shortest path as 24 attempts and 21 correct programs of 30, and on kth smallest as 17 and 16. The exchange through blocks 12 to 23 alone on shortest path gives 18 attempts but 11 correct programs, at a pass ratio of 0.73 against the twin, below the gate; the grid exchange through all blocks gives 14 attempts and 3 correct programs at a pass ratio of 0.59. Five cells fail the pass gate. A post-hoc McNemar test on correct programs against matched-norm random exchanges keeps the preregistered conclusion on the three tasks (Table 285).

**Table 284.** Stage A exchanges of iteration 6, attempts and correct programs.

{{e6_stageA}}

**Table 285.** Stage A against matched-norm random exchanges, on correct programs (post hoc) beside the preregistered attempted contrast.

{{e6_mcnemar}}

**The site, Gemma and the synthesis.** The site ordering is now stated as open: a post-hoc model at alpha 4 or less puts the read position below the task-specification site on both tasks but not the condition span, whose coefficient intervals cross zero (beta -1.70 [-3.96, 0.42] on kth smallest and -0.56 [-4.93, 2.91] on connected components). The engine half of the rule label, which withdrew the site claim as specific to 8-bit floating point, is refuted by Section 6.3, and the corrected text says so. A new Table 254b sets, for each task, the band where noise acts against the band where the exchange transfers: they agree on kth smallest (blocks 12 to 23) and disagree on connected components, where noise at blocks 0 to 11 under the iteration-4 seeds raises the log-odds of escape by 2.51 [1.39, 3.80] while the exchange transfers at blocks 12 to 23. The Gemma paragraph now quotes the standardised SAE ridge (0.15 against 0.086 for the template-plus-noun-norm control, a gain of 0.064 below the preregistered 0.10) beside the unstandardised one, and says that the edits toward BFS lowered the pass rate from 0.84 to between 0.16 and 0.58 except the SAE top-five clamp (18 BFS at pass 0.84). Table 279, inserted at the end of iteration 6, keeps each quantity with its own model and site.

**Correct programs in Table 238.** On shortest path, per-sample plan noise under the 8-bit engine (W8A8) gives 14 correct off-default programs among its 37 correct programs at alpha 2, against 9 of 31 in bf16, and 9 of 43 against 5 of 43 at alpha 1 (Table 286). The screen verdict on 8-bit rounding becomes MIXED: under W8A8, 15 of 40 directions pass the screen against 8 to 9 under the other numerics, and 17 of 40 meet the excess but fail the pass clause.

**Table 286.** Table 238 restated on correct programs (shortest path): correct off-default programs over all correct programs, per-sample plan noise at the absolute unit.

{{e6_t238}}

**The NLA contrast without pseudoreplication.** The per-unit contrast of iteration 6 (20:88 over 364 units, p 2.3e-11) counted several units from one sample. With one unit per sample, the outside reader of the visible text still beats the NLA in every version of the test (Table 287); at the level of the four tasks the contrast is 1:3 with p 0.625, and the smallest p four tasks can give is 0.0625, so the task level is uninformative by construction.

**Table 287.** The NLA against the outside reader with one unit per sample.

{{e6_nla}}

**The executed checks.** Three checks the review named were reported. The empty-prefix test of iteration 6's Gemma fork resampling (a BFS share of 0.38, 73 of 192, from the empty prefix against the natural 0.305 [0.245, 0.372]) gave an exact p of 0.028, and the Gemma experiment's own list of what it did not run (two unit tests replaced by checks built into the edit code, one figure overlay, a fork and two cross-prompt readouts on further tasks, and per-sample displacement at generated tokens) is now quoted in Sections 6.5 and 6.8. The three correct programs of the engine control labelled other are two array-scan Dijkstra programs that run in quadratic time (one of them an iteration-4 row of the 8-bit engine) and an n-round Bellman-Ford whose comment calls it Floyd-Warshall. All three pass the hidden suite (45 of 45) and the stress inputs. Three judge families were gated on ten controls of known class (Table 288). One passed with classes merged; the declared replacement for the third was rate-limited on 12 of its 39 calls. Agreement between judges was kappa 0.38 on exact classes and 0.61 merged. Every judge and the manual read called all three programs catalogue variants, so the count of novel algorithms stays 0.

**Table 288.** The judge gate for the three engine-control programs labelled other.

{{e6_judges}}

**Section 4.9 and positioning.** Section 4.9 is rewrapped without changing a value. The audit checked the venues of the five neighbours the plan named (Table 289) and ran a 14-query search for work on forks in code generation (137 hits, 136 unique). None occupies the run's question; 14 are adjacent and one is irrelevant. Row 66 of Table 277 now places the fork as adjacent-only to Forking Paths [30].

**Table 289.** Venues of the neighbours the plan named, against the live records.

{{e6_venues}}

The audit also tagged the six verdicts that rest on the ban-free unit and direction seeds of iteration 5 as pending the 2x2 of dose unit against seeds. Section 7.6 resolves that tag.

## 7.3 A fitted plan subspace in Qwen3-8B

### 7.3.1 Design

The DAS experiment [ARTIFACT:art_veI9l_Rb9wDY] asked whether the choice Stage A transfers is carried by a low-rank linear subspace of the task-specification states. DAS fits one orthonormal map R (4096 by 16, with nested ranks 1, 2, 4, 8 and 16) such that exchanging only the coordinates of R between a source prompt and the neutral twin reproduces the source's behaviour [110, 111]. The map is fitted on teacher-forced pairs: a source prompt (a ban of the default or an instruction forcing an algorithm Y) and the twin, scored on the log-likelihood of programs of Y. It is tested in held-out generation scored by hidden tests, on held-out templates, against the full-state exchange at the same site, which is the ceiling. Three tasks were used: shortest path (default Dijkstra, ban substitute Bellman-Ford/SPFA), connected components (default union find, substitute BFS or DFS) and kth smallest (default full sort, substitute quickselect or a size-k heap).

The controls follow the published objections to DAS. Random subspaces of the same rank test whether any subspace would do. A *permuted-label fit* trains the same map with the source labels permuted; if it transfers as well, the fitted subspace does not encode the label. A *random-initialisation control* fits the same map on a randomly initialised copy of the network; if the untrained network admits an equally good teacher-forced fit, fit quality says nothing about a learned variable [132]. Two dormancy checks follow Makelov et al. [122]: the share of the twin's natural cross-prompt variance that lies in the subspace, and a *projected map*, the fitted map restricted to the top 64 principal components of natural variation, whose retention of the teacher-forced effect should be high if the subspace acts through directions the model uses. A *reverse interchange* writes the twin's coordinates into the ban prompt; a variable should restore the default.

### 7.3.2 Site

A single-block full-state exchange peaks at block 18 on shortest path and at block 16 on connected components and kth smallest (Table 290). The two kinds of source behave differently in generation. A forced instruction is carried by one block: exchanging the forced prompt's states at that block alone transfers Bellman-Ford/SPFA in 30 of 30 slots on shortest path and BFS in 28 of 30 on connected components. A ban on the two core tasks is not: the same single-block exchange moves 0 of 30 slots on both, and only the band of blocks 12 to 23 transfers it (11 of 30 on shortest path, against 1 at base; 17 of 30 on connected components, against 0). The committed fallback to the band therefore fired on both. On kth smallest one block carries the ban (27 of 30, against 28 for the band and 5 at base).

**Table 290.** Site selection: the teacher-forced profile and its generation check.

{{x33_site}}

### 7.3.3 The committed objective diverged, and was amended

The committed objective was contrastive: maximise the log-likelihood of Y programs minus that of default programs. It grew without bound on validation, to 1,873 nats on shortest path, 3,868 on connected components and 177 on kth smallest, against full-state ceilings of 14 to 35 nats; the permuted-label fit reached 880 (Table 291). A generation pilot of the contrastive maps broke programs (Table 301). The first amendment replaced the objective with the likelihood of Y programs alone, which stays within the ceiling. Every result below uses the amended map unless the table says otherwise.

**Table 291.** Every DAS fit: steps, best validation gain and orthonormality.

{{x33_fits}}

### 7.3.4 Recovery in held-out generation

A rank-1 or rank-2 edit moves the algorithm about as far as the full-state exchange on all three tasks, and random subspaces of the same rank move nothing (Tables 292 to 297). On shortest path the rank-2 edit of the fifth-template ban gives 12 correct Bellman-Ford/SPFA programs of 30, against 11 for the full-state exchange, 1 at base and 1, 0 and 1 for three random rank-16 subspaces (McNemar 11:0 against random, Holm p 9.8e-4). On connected components the rank-16 edit gives 29 correct programs, more than the full-state exchange's 17, against 0 for random (61:0 against random, pooled over sources, Holm p 2.6e-18). On kth smallest the rank-1 edit gives 26 against 27 for the full state, 5 at base and 6 for random (20:0, Holm p 1.9e-6). Recovery is the ratio of the edit's transfer to the full-state transfer; pooled over sources it lies between 0.73 and 1.71 at every rank on every task, and above 1 where a trained direction moves the model further than the full exchange.

The forced sources behave differently by task. On shortest path the forced Floyd-Warshall source transfers at rank 1 in 28 of 30 slots while the full-state exchange of the same prompt manages 8 of 20; on kth smallest the forced counting sort source transfers 30 of 30 at every rank while the full-state exchange gives 0 (29 programs labelled other, read below). On connected components the forced BFS source transfers poorly at low rank (1 of 30 at rank 1, 9 at rank 16, against 17 for the full state), while the forced DFS source transfers 30 of 30 at rank 1.

**Table 292.** Shortest path: correct programs of the target algorithm (of 30) by source and rank, with pass rates.

{{x33_p1_T2}}

**Table 293.** Shortest path: pooled recovery and its controls by rank.

{{x33_pool_T2}}

**Table 294.** Connected components: correct programs of the target algorithm (of 30) by source and rank.

{{x33_p1_T10}}

**Table 295.** Connected components: pooled recovery and its controls by rank.

{{x33_pool_T10}}

**Table 296.** Kth smallest: correct programs of the target algorithm (of 30) by source and rank.

{{x33_p1_T03}}

**Table 297.** Kth smallest: pooled recovery and its controls by rank.

{{x33_pool_T03}}

### 7.3.5 The controls that make it a handle, not a variable

The DAS claim is not supported on any task. Three controls fail. The permuted-label fits transfer 0.47 on shortest path, 0.70 on connected components and 0.60 on kth smallest of the full-state effect, against a committed limit of 0.1: on connected components a permuted fit at rank 16 still gives 21 correct BFS programs of 30. The permuted fit can also write its own label: at rank 16 it turns the shortest path ban into Floyd-Warshall in 15 of 30 slots, because one training ban had been relabelled Floyd-Warshall by the permutation. With only two kept algorithms per task the permutation changed 44% of the training labels (56% on kth smallest), so the signal to leave the default survives any such shuffle, which weakens this control as a test of label content. The untrained network admits a teacher-forced fit almost as good as the trained one (13.31 nats against 14.45 on shortest path, a ratio of 0.92 against a limit of 0.5). And the dormancy checks flag two of three tasks: the reverse interchange on shortest path restores the default in 0 of 30 slots, against 21 of 30 for the full-state reverse, and on kth smallest the projected map keeps only 0.20 to 0.26 of the teacher-forced effect. The connected components reverse was not testable. The subspace is not dormant by variance: it holds 0.7% to 18% of the twin's natural cross-prompt variance against 0.03% to 0.4% for random subspaces of the same rank, at the 100th percentile of 1,000 random draws on every task and rank (Table 307).

The reading is that the fitted subspace is a strong, low-rank steering handle on the choice, and that this experiment cannot say it is the variable the model computes. A subspace that permuted labels also find, and that an untrained network also admits, is a direction along which the downstream computation is sensitive, which is what a steering vector needs and less than what a causal variable needs. The control arms behave as before: DAS and the full-state exchange at the read position, and a rank-1 difference-in-means direction and a PCA-16 subspace at the task-specification states, each transfer at most 2 of 30 (Tables 298 and 299). Under the fourth template, whose ban the model mostly ignores, the full-state exchange still transfers 4 of 10 on shortest path and 9 of 10 on connected components.

**Table 298.** Shortest path: readout, null-source and fourth-template controls.

{{x33_ctrl_T2}}

**Table 299.** Connected components: readout, null-source and fourth-template controls.

{{x33_ctrl_T10}}

### 7.3.6 Routing

The routing claim asks whether an edit lands where the forced source points or slides toward the ban's usual substitute. By the committed rule the routing is categorical on shortest path and kth smallest: the Floyd-Warshall source lands on Floyd-Warshall in 28 of 28 correct programs at rank 1, while the full-state exchange of the same prompt lands 12 programs on Bellman-Ford/SPFA and 8 on Floyd-Warshall, and the counting sort source lands on counting sort in 30 of 30 at rank 16 while the full-state exchange lands none (Table 300). Connected components is not categorical: the forced BFS source's rank-16 edit lands 21 DFS and 9 BFS. The subspace thus carries which algorithm, and on two tasks it carries it more cleanly than the whole state does.

**Table 300.** Routing: where correct off-default programs land under the full-state exchange and under DAS.

{{x33_routing}}

**Table 301.** The pilot of the committed contrastive maps in generation (base cells in parentheses).

{{x33_pilot}}

### 7.3.7 Teacher-forced evaluation on held-out pairs

Tables 302 to 306 report every edit's teacher-forced effect on the held-out pairs, under the amended likelihood objective and under the committed contrastive one. *Teacher-forced recovery* is the edit's mean gain divided by the full-state gain on the same pairs; the last two columns split the gain into the change in log-likelihood of Y programs and of default programs. The contrastive maps reach recoveries far above 1 by lowering the likelihood of default programs, which is the signature of the divergence of Section 7.3.3.

**Table 302.** Shortest path, likelihood objective: held-out teacher-forced evaluation.

{{x33_tf_eval_T2_LY}}

**Table 303.** Shortest path, committed contrastive objective: held-out teacher-forced evaluation.

{{x33_tf_eval_T2}}

**Table 304.** Connected components, likelihood objective: held-out teacher-forced evaluation.

{{x33_tf_eval_T10_LY}}

**Table 305.** Connected components, committed contrastive objective: held-out teacher-forced evaluation.

{{x33_tf_eval_T10}}

**Table 306.** Kth smallest, likelihood objective: held-out teacher-forced evaluation.

{{x33_tf_eval_T03_LY}}

**Table 307.** Dormancy checks (Makelov): natural variance share, held-out displacement share and projected-map retention by rank.

{{x33_dormant}}

### 7.3.8 The manifold in the fitted coordinates

The manifold claim placed prompts of shortest path in the rank-16 coordinates of the fitted map. The *paraphrase null* is the distribution of the distance D from the default centroid over neutral paraphrases of the twin (median 0.52, 95th percentile 1.13). All five ban templates lie outside it (D 1.73 to 2.62, at the 100th percentile), each on the runner-up side of the axis from the default centroid to the Bellman-Ford/SPFA centroid (+1.10 to +1.76). The two random seeds, the short instruction to make a new algorithm and the 2,000-word novelty instruction lie inside it (76th to 88th percentile), as predicted. The semantic seed was predicted outside and lies inside, at the 94th percentile (Table 309). Behaviour agrees with the placement: the neutral prompt, both random seeds and the short instruction write Dijkstra in every correct program, the semantic seed adds one program labelled other, and the long novelty instruction is the only prompt that reaches a named alternative (6 Bellman-Ford/SPFA programs of 28 correct; Table 308), a shift that happens while the model writes its rationale, not in the prompt states. Multidimensional scaling of the centroids has stress 0.079; centroids and implemented counts are in Table 310, and geodesic distances on neighbour graphs in Table 311. Bans that name all but one of the five algorithms (leave-one-survivor bans) are not placed near their survivor: the survivor's centroid ranks 3.10 of 5 on average by geodesic distance (random relabelling p 0.63), and every such ban sits nearest the forced Bellman-Ford/SPFA prompts. The geometry does not predict where a ban lands.

[FIGURE:fig_das_manifold_sp]

**Table 308.** Shortest path: what each seed and instruction prompt writes (30 programs each).

{{x33_mbeh}}

**Table 309.** Shortest path: placement of prompts in the rank-16 DAS coordinates against the paraphrase null.

{{x33_mplace}}

**Table 310.** Shortest path: algorithm centroids along the runner-up axis and how often each algorithm has been implemented.

{{x33_centroids}}

**Table 311.** Shortest path: geodesic distances between centroids on neighbour graphs of the fitted coordinates.

{{x33_geodesic}}

### 7.3.9 Seeds, discreteness and the full cell list

A second initialisation seed fits a different subspace (principal angles of 38 to 90 degrees to the first) with similar behaviour: no discordance between seeds reaches significance (Table 312). The subspace is therefore not unique, as in Gemma (Section 7.8). The discreteness claim fails. Scaling the rank-2 edit of the ban by lambda from 0 to 1.5 raises correct Bellman-Ford/SPFA programs from 1 of 20 (lambda 0 to 0.2) through 4 of 20 (0.4 to 0.5) to a plateau of 6 to 9 of 20 from lambda 0.6 to 1.5; the committed logistic width is 3.25 in lambda (midpoint 1.47), against 0.3 or less for a step, and the one candidate hybrid among 114 correct programs was judged a single algorithm (Table 313). Of the 38 correct programs labelled other across the experiment, 36 are catalogue variants and 2 are labeller misses; none is novel. The engine reproduced the iteration-6 twin labels in 20 of 20, 19 of 20 and 20 of 20 slots; two GPU unit tests missed their tolerance because of bf16 kernel-shape noise (packed against separate forward passes differ by up to 0.273 nats per program, cached against full forward passes by 0.160), so every compared quantity is measured within one batch shape. Table 314 lists every generation cell.

**Table 312.** A second DAS initialisation seed.

{{x33_seed2}}

**Table 313.** Discreteness: the rank-2 DAS edit of the ban scaled by lambda (shortest path, 20 slots each).

{{x33_lambda}}

**Table 314.** Every generation cell of the DAS experiment.

{{x33_cells}}

