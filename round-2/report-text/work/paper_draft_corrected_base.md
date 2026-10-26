# Where a Prompt Ban Sends a Code Model, and What Else Moves Its Algorithm Choice

This report is the internal record of a study of algorithmic diversity in an open-weight instruction-tuned model. The question that started the run is how "creativity" shows up inside a language model and whether it can be influenced: if a model is asked to implement a path search algorithm, does it always write the same one, and which knobs (sampling temperature, random context seeds, instructions, prohibitions, or edits to the activations) change the algorithm rather than only its wording. The behavioural puzzle comes from the inspiration repository by Drejc Pesjak that the request names, in which a closed model wrote Dijkstra's algorithm for a weighted shortest path task in 125 of 125 programs across five prompting strategies, and cumulative bans moved it to SPFA and Bellman-Ford rather than to a spread of alternatives. The same collapse appears in controlled measurements across 15 model configurations, where a no cue prompt gives Dijkstra 94.1% of the time [1], and in broader benchmarks of algorithmic diversity among correct programs [2, 3].

The hypothesis entering the run is mechanistic. When an instruction-tuned model is told not to use its default solution, the prohibition is expected to do two things: suppress the banned algorithm and promote the alternative the model associates with it, so the output collapses again on one predictable substitute instead of spreading over the repertoire. This mirrors the suppression plus promotion account of negation on factual questions [4]. Competing accounts say the substitute is chosen by baseline typicality, by proximity on an activation space solution manifold, by a few early forking tokens during generation, by a single list versus implement commitment direction, or that the whole collapse was installed by post-training. The report records, iteration by iteration, which of these the evidence supported and which it did not. All work so far uses Qwen3-8B [5] with thinking mode off unless stated, on the request's two path search tasks. *(Note added in iteration 2: iteration 2 adds Llama-3.1-8B-Instruct [22] and a bench of 13 further coding tasks; Sections 2.7 and 2.8.)* The hypothesis reached its tested form after seven rounds of drafting and review before any experiment ran; the reviewer's overall score across the rounds was 5, 6, 6, 7, 7, 7 and 7, and the final round scored soundness 3, presentation 3, contribution 3 and fidelity 4.

# Iteration 1: a wide screen of six accounts on the two path search tasks

## 1.1 Why this iteration ran what it ran

The first iteration was planned as a screen rather than a test. The hypothesis carried four alternates that disagree with it about what decides the algorithm written after a ban, and none of them had been measured. The strategy therefore ran every account cheaply and in parallel on the same events, with one shared protocol, one per-sample output schema and a selection rule fixed before any artifact ran, and it left inference to a later confirmation on reserved tasks. The selection rule had two columns. The PREDICT column scores each account's forecast of the distribution after a ban, committed by sha256 hash before sampling, by its log score on the realised compliant samples; an account survives if its mean log score beats the next best account by at least 0.10 nats on at least 3 events where the accounts' top-1 nominations disagree. The BUY column scores each knob by the correctness conditioned Hill number it reaches while keeping at least 80% of the baseline pass rate; a knob survives if it beats the next best knob by at least 0.5 effective algorithms. *(Correction, iteration 2: as written in the strategy, the PREDICT rule scores only informative events, those with the banned mode present at 10% or more of the latent baseline, compliance of at least 50% and at least two survivors, and the BUY rule names a winner only if it leads on the pooled tasks and in direction on each task. This paragraph omitted both conditions, and Section 1.11 applied the rules without them. Sections 2.3.6 and 2.3.7 recompute both.)* A third check, the locus diagnostic, asks where the algorithm decision is made: it would move every geometric analysis from the read position (the last prompt token, Section 1.2) to generated-token states if a decoder at a forking token beat the read position decoder by 20 points over a shuffled label control. The strategy also stated in advance that nothing in this iteration would be inferential.

Seven artifacts ran: one dataset and six experiments, each owning one account (Table 1). We call each experiment by the account it screens: the association, geometry, forking token, decommitment and instruction tuning experiments, and the decoding experiment, which covers sampling temperature, random seeds and creativity instructions. The strategy asked the dataset artifact to build a reserved bench of 12 further tasks with hidden tests, labellers and forecasts frozen before any ban, so that the account that survived the screen could be confirmed out of sample in the next iteration.

**Table 1.** The seven artifacts of iteration 1, the account each was asked to screen, and the knob or predictor it contributed.

| Artifact | Account screened | Predictor (PREDICT column) | Knob (BUY column) |
|-|-|-|-|
| Dataset: source data for an algorithm-choice bench | none (reserved bench for confirmation) | none | none |
| Association experiment | substitution by association vs typicality ladder | Borda association map; latent baseline frequency | single and cumulative prompt bans |
| Geometry experiment | proximity on the read position manifold; shift decomposition | geodesic kernel; read position decoder | affine directional ablation of the modal algorithm |
| Forking token experiment | algorithm fixed at forking tokens during generation | none | temperature raised only around forking tokens |
| Decommitment experiment | one list versus implement direction controls collapse | decommitted survivor distribution | activation addition of the decommitment direction |
| Instruction tuning experiment | post-training installed the collapse | base-model survivor distribution | subtraction of the instruct minus base direction |
| Decoding experiment | temperature and random seeds change wording, not ideas | none | temperature and top-k, seeds, creativity instructions, generate then select |

## 1.2 Shared setup and the conventions used in this report

**Tasks.** Both tasks come from the request. The grid task asks for `solve(grid, start, goal)` returning any valid 4-neighbour path on a grid of free and blocked cells, or an empty list when the goal is unreachable. Its catalogue has six algorithms, that is, breadth-first search (BFS), depth-first search (DFS), bidirectional BFS, iterative-deepening DFS (IDDFS), A* or greedy best-first search with a Manhattan heuristic (A* in tables), and unit weight Dijkstra. The shortest path task asks for the shortest distance from s to t in a directed graph with nonnegative integer weights and cycles, or -1. Its catalogue has five algorithms: Dijkstra, Bellman-Ford or SPFA (counted as one algorithm), bidirectional Dijkstra, Floyd-Warshall and Dial's bucket queue. Every experiment wrote its own hidden tests (between 39 and 48 cases per task) with a time limit of ten times the slowest reference implementation and a 1 s minimum, and every catalogue reference had to pass before any model sample was scored.

**Model and decoding.** Qwen3-8B in bf16 with the chat template and thinking off, sampled at temperature 1.0 with top-p 1.0 and no top-k unless a table says otherwise. Engines differed between artifacts because the containers had no C compiler: vLLM 0.11.0 [6] in eager mode in five experiments (association [ARTIFACT:art__skdlFp_o3e9], forking token [ARTIFACT:art_1yV2vQ0EH4OY], decommitment [ARTIFACT:art_U5UKkFrOgSsE], instruction tuning [ARTIFACT:art_HF8nK8B_Lqyy] and decoding [ARTIFACT:art_UoCVh2Qe5RZ0]), and HF transformers `generate` in the geometry experiment [ARTIFACT:art_D6Z0Snf09sFL] and in the hooked steering arms. GPUs were an RTX 5090 (association and decoding experiments), an NVIDIA GPU with 23 GB of memory (geometry and instruction tuning experiments) or an RTX A4500 (forking token and decommitment experiments).

**Prompts.** Every prompt is a condition segment, then a fixed task specification of at least 50 tokens, then the assistant header. The read position is the last prompt token, so no token specific to a condition sits at or near it. The conditions shared by all experiments are the baseline (no condition segment or a neutral one), a ban (`Do not use X.`), the mention twin and the listing control. The mention twin (`X is one well-known approach to this task; implement any correct algorithm.`) puts the same name at the same place without forbidding it, because naming a forbidden item can itself prime it [7]. We call the condition that names every catalogue algorithm the listing control. Each condition segment has 10 paraphrases, and N=100 means 10 paraphrases with 10 samples each. Each experiment wrote its own paraphrases.

**Labels and correctness.** Each program is labelled with one catalogue algorithm or "other" by a runtime signature tracer (the program runs on crafted inputs with instrumented heaps, queues, stacks and grid reads) and by AST rules; disagreements go to a blind LLM judge on OpenRouter. Recursion versus iteration never counts as a separate algorithm. A program is correct when it passes the hidden tests within the limit. Intervals on proportions are Wilson score intervals [8] unless stated.

**Quantities.** We use the following names throughout. The *banned mode share* is the fraction of all coded samples labelled as the banned algorithm. A *compliant sample* is a correct program not labelled as a banned algorithm. The *realised mode* of a ban is the most common label among compliant samples if it leads the next most common label by at least 15 points; otherwise we call the event one with no clear mode. The *correctness conditioned Hill number* (Hill_cc) is the exponential of the Shannon entropy of the label distribution over correct programs, the effective number of algorithms [9]; a value of 1 means one algorithm and 2 means two equally common ones. The *log score* of a predictor on a ban event is the mean natural logarithm of the probability it assigned to the labels of the realised compliant samples, after mixing in 5% uniform mass over the surviving algorithms and a 2% floor for "other". It is a strictly proper scoring rule [10]; higher is better, and a uniform predictor over four survivors scores -1.406. Artifacts reported a quantity they called compliance in two different ways (one minus the banned mode share, or the fraction of compliant samples), so this report states the banned mode share and the number of compliant samples instead, recomputed from each artifact's per-sample rows.

**Labeller validation.** Each experiment validated its own labeller against a gold set adjudicated by two or three LLM judges, with Cohen's kappa [11] between the runtime and AST labels as the main agreement statistic. Table 2 collects the results. Four labellers passed their gates and two did not. Both failures were driven by runtime versus AST disagreement on small gold sets. The combined label (runtime, AST and judge) still agreed with the adjudicated label on 97% of gold programs in the association experiment, and on 93% (grid) and 70% (shortest path) in the decoding experiment, 92% on its correct gold programs.

**Table 2.** Labeller validation per experiment, as each artifact reported it (gold set sizes per task).

| Experiment | Gold programs (Grid / Shortest path) | Kappa runtime vs AST | Runtime vs adjudicated | Combined label vs adjudicated | References correct | Gate |
|-|-|-|-|-|-|-|
| Association | 50 / 42 (evaluation split; 92 pooled) | 0.753 pooled | 0.843 pooled | 0.966 pooled | 22/22 | failed (targets 0.8 and 0.9) |
| Geometry | 28 / 26 | 0.902 / 0.938 | 0.964 / 0.923 | not reported | 100% | passed |
| Forking token | 24 / 23 | 1.0 / 0.847 | 1.0 / 0.913 | 1.0 / 1.0 | 9/9, 8/8 (AST; Dial has no runtime signature) | passed |
| Decommitment | 10 baseline + 6 steered + references + 2 outside the catalogue per task | 1.00 / 0.82 | 1.00 / 0.92 | 1.00 / 1.00 | 12/12 | passed after two revision rounds on Shortest path |
| Instruction tuning | 25 references and mutants; 40 audit programs | 0.77 over all parseable programs | runtime never wrong on references | kappa between judges 0.93 | AST 100% | passed (reference gate) |
| Decoding | 30 / 30 | 0.337 / 0.111 on gold; 0.881 / 0.851 over all programs | not reported | 0.933 / 0.70 (0.917 / 0.923 on correct gold programs) | 9/9, 7/7 | failed (strict criteria) |

## 1.3 The dataset artifact: source data, not yet a bench

The dataset artifact [ARTIFACT:art_j3Rm_lr2nzR6] was asked for a validated 12-task bench and delivered the raw material for one. It ran 98 Hugging Face Hub queries (574 unique datasets), screened 25 candidates plus the inspiration repository, and kept ten sources at pinned revisions, 61,469 examples in total (Table 3). For the 20 bench problems that LeetCode covers it parsed every I/O pair and reran the reference solutions, which passed 20 of 20. The LRU cache and streaming median problems are absent from LeetCodeDataset, so their tests must be generated.

**Table 3.** Sources kept by the dataset artifact (counts recomputed from `full_data_out.json`).

| Source | Examples | Role in the planned bench |
|-|-|-|
| LeetCodeDataset [12] | 2,869 | problem texts, references and parsed I/O pairs for 20 bench problems |
| Mercury [13] | 440 | human solutions with runtimes for 20 bench problems, including LRU cache and median |
| inspiration repository (Drejc Pesjak) | 225 | labels of the repository's shortest path programs (Dijkstra 132, Bellman-Ford/SPFA 34, bidirectional 30, other 21, Dial 5, A* 2, Floyd-Warshall 1); code not redistributed (no licence) |
| TheAlgorithms/Python | 1,354 | MIT implementations, 55 labelled by hand by task and algorithm |
| CLRS-Text [14] | 2,910 | execution traces of 15 catalogue algorithms for tracer tests |
| HumanEval+ [15] | 164 | harness validation |
| ENAMEL [16] | 164 | efficient references with input generators for time limits |
| Concreteness norms [17, 18] | 39,954 | 718 neutral nouns for neutral twins and context seeds |
| KodCode [19] | 2,767 | tested solutions, 253 naming a catalogue algorithm |
| XLCoST [20] | 10,622 | GeeksforGeeks programs, 209 naming a catalogue algorithm |

The frozen task specifications, hidden tests filtered against the specification, labellers, gold sets and forecasts frozen before any ban were not built. The reserved bench on which the strategy meant to confirm the surviving account next iteration therefore does not exist yet, and the confirmation step has to build it first. No LLM calls were made and the spend was zero.

## 1.4 The baseline collapse, measured six times

Every experiment drew its own baseline, so the collapse was measured six times with different paraphrases, test suites and engines (Table 4; association [ARTIFACT:art__skdlFp_o3e9], geometry [ARTIFACT:art_D6Z0Snf09sFL], forking token [ARTIFACT:art_1yV2vQ0EH4OY], decommitment [ARTIFACT:art_U5UKkFrOgSsE], instruction tuning [ARTIFACT:art_HF8nK8B_Lqyy] and decoding [ARTIFACT:art_UoCVh2Qe5RZ0] experiments). Of 1,200 baseline programs on the grid task, 1,199 are BFS. Of 1,200 on the shortest path task, 1,174 are Dijkstra (97.8%), above the 94.1% no cue prior [1]. The few non-modal programs came from three experiments, and the decommitment experiment's baseline was the least collapsed. A further 200 samples per task at temperature 1.3 in the association experiment were also 100% BFS and 100% Dijkstra.

**Table 4.** Baseline label counts per experiment (all coded samples; pass = share passing the hidden tests).

| Experiment (engine) | Grid N | Grid labels | Grid pass | Shortest path N | Shortest path labels | Shortest path pass |
|-|-|-|-|-|-|-|
| Association (vLLM) | 300 | BFS 300 | 0.933 | 300 | Dijkstra 300 | 1.00 |
| Geometry (HF) | 200 | BFS 200 | 0.99 | 200 | Dijkstra 200 | 1.00 |
| Forking token (vLLM) | 200 | BFS 200 | 0.91 | 200 | Dijkstra 200 | 0.995 |
| Decommitment (vLLM) | 200 | BFS 200 | 1.00 | 200 | Dijkstra 181, Bellman-Ford/SPFA 14, Dial 4, other 1 | 0.885 |
| Instruction tuning (vLLM) | 200 | BFS 200 | 1.00 | 200 | Dijkstra 193, Bellman-Ford/SPFA 7 | 1.00 |
| Decoding (vLLM) | 100 | BFS 99, unit weight Dijkstra 1 | 0.97 | 100 | Dijkstra 100 | 0.99 |

The collapse makes one of the planned predictors uninformative before any ban runs. The typicality ladder predicts that a ban redistributes mass in proportion to each survivor's baseline frequency. Every survivor's baseline frequency was zero in the association, geometry and forking token experiments and at most 7% elsewhere (Bellman-Ford/SPFA, 14 of 200 in the decommitment experiment), so the frequency forecast is uniform wherever the baseline is fully collapsed and its top-1 nomination is a tie. The preregistered presence strata are empty for the same reason: no catalogue algorithm other than the default reached the 10% presence cut, so every non-modal single ban is a ban of an absent algorithm.

## 1.5 Association experiment: does the alternative the model names predict where a ban lands?

**Why.** This experiment screened the main hypothesis against its behavioural rival. The main hypothesis predicts the algorithm written after a ban from the model's association between algorithms; the typicality ladder predicts it from baseline frequencies restricted to the survivors. Both predictors were elicited and frozen before any ban prompt was generated, and every prediction file was chained by sha256 hash before the samples it predicts [ARTIFACT:art__skdlFp_o3e9]. The commitment audit found the chain intact and every event committed in advance (commit at 15:18:30 UTC, first ban generation at 15:20:05 UTC).

**Design.** The latent baseline was N=300 per task at temperature 1.0, plus 200 samples at temperature 1.3 and 50 without the neutral condition segment. The association map was elicited on separate queries with thinking off: for each of the 11 catalogue algorithms X, the model returned 20 sampled complete rankings of the other algorithms by the criterion `how standard an alternative to X for this task`, aggregated by Borda count (each ranking gives an alternative points according to its rank) with one extra point per algorithm. We call the normalised result the *association map* A(X); its winner is the association nomination. The *clarity* of X is the share of the 20 rankings whose alternative ranked first is the Borda winner, and Kendall's W [21] measures agreement across the 20 rankings. The model also gave 20 free-form answers to the question `what is the standard alternative to X?`, and Llama-3.1-8B-Instruct [22] repeated the whole elicitation as an external map. The ban arms were all 11 single bans at N=100, the mention twin of each at N=50, the listing control at N=100 and a greedy succession that bans the realised mode of each step cumulatively, in the manner of denial prompting [23]. Generation used vLLM on one RTX 5090 (about 6 GPU minutes); OpenRouter spend was USD 0.27 for the judge, gold set adjudication and the external elicitation.

**The association maps.** Table 5 gives the map for every catalogue algorithm. The two maps that matter are those of the defaults. For BFS, the model's rankings spread the Borda mass almost evenly over unit weight Dijkstra, bidirectional BFS and A*, with DFS ranked last; clarity was 0.20, the lowest of all 11 algorithms. Yet 19 of its 20 free-form answers named DFS. For Dijkstra, all 20 rankings put Bellman-Ford/SPFA first (clarity 1.0). The map from Llama agreed with the Borda winner of Qwen for 5 of 6 grid algorithms and 4 of 5 shortest path algorithms, and its map for BFS tied DFS and IDDFS on top.

**Table 5.** Association maps from the association experiment. Borda shares of the top alternative, clarity (share of 20 rankings whose first choice is the Borda winner), Kendall's W across the 20 rankings, the modal free-form answer (out of 20), and the external (Llama-3.1-8B) Borda winner and clarity.

| Task | X | Qwen Borda winner (share) | Clarity | Kendall's W | Qwen free-form (count/20) | Llama Borda winner | Llama clarity |
|-|-|-|-|-|-|-|-|
| Grid | BFS | unit weight Dijkstra (0.293); bidir BFS 0.283, A* 0.263, IDDFS 0.107, DFS 0.054 | 0.20 | 0.52 | DFS (19) | DFS = IDDFS (0.251) | 0.368 |
| Grid | DFS | BFS (0.395) | 1.0 | 0.577 | BFS (20) | BFS | 0.684 |
| Grid | bidirectional BFS | BFS (0.38) | 0.9 | 0.454 | A* (11) | BFS | 0.70 |
| Grid | IDDFS | BFS (0.395) | 1.0 | 0.513 | BFS (18) | BFS | 0.60 |
| Grid | A* | BFS (0.385) | 0.9 | 0.70 | BFS (20) | BFS | 0.60 |
| Grid | unit weight Dijkstra | BFS (0.395) | 1.0 | 0.589 | BFS (18) | BFS | 0.75 |
| Shortest path | Dijkstra | Bellman-Ford/SPFA (0.492); Floyd-Warshall 0.226, bidir Dijkstra 0.153, Dial 0.129 | 1.0 | 0.639 | Bellman-Ford/SPFA 8, other 8, self 4 | Bellman-Ford/SPFA | 0.65 |
| Shortest path | Bellman-Ford/SPFA | Dijkstra (0.435) | 0.65 | 0.573 | self 15, Dijkstra 5 | Dijkstra | 0.65 |
| Shortest path | bidirectional Dijkstra | Dijkstra (0.492) | 1.0 | 0.981 | Dijkstra (20) | Bellman-Ford/SPFA | 0.40 |
| Shortest path | Floyd-Warshall | Dijkstra (0.444) | 0.7 | 0.916 | Dijkstra (20) | Dijkstra | 0.55 |
| Shortest path | Dial | Dijkstra (0.492) | 1.0 | 0.841 | Dijkstra (20) | Dijkstra | 0.65 |

The Borda winners of the two models matched at a rate of 0.833 on the grid task and 0.8 on the shortest path task, with a mean Kendall tau (rank agreement between the two models' rankings) of 0.362 and 0.765. A post hoc map from gpt-4.1-mini, collected after the freeze and so not a contest predictor, showed the same split for BFS: its Borda winner was bidirectional BFS while its free-form answer was DFS. The artifact's reading is that the ranking question elicits the closest shortest path variant of BFS rather than the alternative a programmer reaches for.

**What the bans did.** Table 6 gives every condition of the experiment. The two modal bans were largely obeyed in this experiment: 10 of 100 grid programs and 9 of 100 shortest path programs still used the banned algorithm. Every compliant program landed on one substitute, DFS for the grid task (38 of 38) and Bellman-Ford/SPFA for the shortest path task (86 of 86). The low pass rate of the grid ban (0.46) comes from the DFS programs: 52 of 90 failed the hidden tests (43 wrong answers, 7 timeouts, 2 runtime errors), and forced DFS implementations passed only 3 of 10 times.

**Table 6.** Every condition in the association experiment (labels over all coded samples; Hill_cc over correct programs).

| Task | Condition | N | Labels | Pass rate | Hill_cc |
|-|-|-|-|-|-|
| Grid | baseline | 300 | BFS 300 | 0.933 | 1.0 |
| Grid | baseline, T=1.3 | 200 | BFS 200 | 0.895 | 1.0 |
| Grid | baseline, no condition segment | 50 | BFS 50 | 0.94 | 1.0 |
| Grid | ban BFS (modal) | 100 | DFS 90, BFS 10 | 0.46 | 1.587 |
| Grid | ban DFS | 100 | BFS 96, DFS 4 | 0.88 | 1.115 |
| Grid | ban bidirectional BFS | 100 | BFS 99, other 1 | 0.92 | 1.0 |
| Grid | ban IDDFS | 100 | BFS 88, DFS 12 | 0.80 | 1.220 |
| Grid | ban A* | 100 | BFS 100 | 0.72 | 1.0 |
| Grid | ban unit weight Dijkstra | 100 | BFS 92, DFS 8 | 0.71 | 1.137 |
| Grid | listing control | 100 | BFS 97, DFS 3 | 0.92 | 1.0 |
| Grid | mention BFS | 50 | BFS 50 | 1.00 | 1.0 |
| Grid | mention DFS | 50 | DFS 50 | 0.30 | 1.0 |
| Grid | mention bidirectional BFS | 50 | BFS 43, bidirectional BFS 5, other 2 | 0.72 | 1.405 |
| Grid | mention IDDFS | 50 | IDDFS 36, DFS 14 | 0.18 | 1.417 |
| Grid | mention A* | 50 | A* 28, BFS 12, unit weight Dijkstra 8, DFS 2 | 0.82 | 2.756 |
| Grid | mention unit weight Dijkstra | 50 | BFS 50 | 0.90 | 1.0 |
| Grid | succession step 2 (ban BFS and DFS) | 100 | DFS 79, BFS 15, unit weight Dijkstra 4, A* 1, IDDFS 1 | 0.53 | 2.278 |
| Shortest path | baseline | 300 | Dijkstra 300 | 1.00 | 1.0 |
| Shortest path | baseline, T=1.3 | 200 | Dijkstra 200 | 1.00 | 1.0 |
| Shortest path | baseline, no condition segment | 50 | Dijkstra 50 | 1.00 | 1.0 |
| Shortest path | ban Dijkstra (modal) | 100 | Bellman-Ford/SPFA 90, Dijkstra 9, other 1 | 0.95 | 1.368 |
| Shortest path | ban Bellman-Ford/SPFA | 100 | Dijkstra 94, Bellman-Ford/SPFA 5, other 1 | 0.93 | 1.061 |
| Shortest path | ban bidirectional Dijkstra | 100 | Dijkstra 97, Bellman-Ford/SPFA 3 | 1.00 | 1.144 |
| Shortest path | ban Dial | 100 | Dijkstra 95, Bellman-Ford/SPFA 5 | 0.97 | 1.106 |
| Shortest path | ban Floyd-Warshall | 100 | Dijkstra 77, Bellman-Ford/SPFA 23 | 0.71 | 1.191 |
| Shortest path | listing control | 100 | Dijkstra 97, Bellman-Ford/SPFA 3 | 1.00 | 1.144 |
| Shortest path | mention Dijkstra | 50 | Dijkstra 50 | 1.00 | 1.0 |
| Shortest path | mention Bellman-Ford/SPFA | 50 | Bellman-Ford/SPFA 50 | 0.84 | 1.0 |
| Shortest path | mention bidirectional Dijkstra | 50 | Dijkstra 50 | 0.30 | 1.0 |
| Shortest path | mention Dial | 50 | Dijkstra 50 | 1.00 | 1.0 |
| Shortest path | mention Floyd-Warshall | 50 | Floyd-Warshall 43, Bellman-Ford/SPFA 7 | 0.88 | 1.115 |
| Shortest path | succession step 2 (ban Dijkstra and Bellman-Ford/SPFA) | 100 | Bellman-Ford/SPFA 65, Dijkstra 35 | 0.85 | 1.960 |

*(Added in iteration 2: the caption says every condition, but the experiment also ran eleven forced implementation conditions of 10 samples each, which this table omits; they are given in Table 50, Section 2.3.10. Forced IDDFS passed 0 of 10, forced Dial 0 of 10, and forced bidirectional Dijkstra was written as plain Dijkstra 10 of 10 times.)*

**The forecast contest.** Only the two modal bans were informative events, since every other ban removed an algorithm the model never produced. Table 7 scores every predictor on them. The association map missed the grid event, where it nominated unit weight Dijkstra and ranked DFS last, and hit the shortest path event. Against the uniform frequency forecast it lost by 1.188 nats per sample on the grid event and won by 0.652 on the shortest path event, a mean of -0.268 (association wins 1 of 2). The two predictors that hit both events were not in the preregistered contest: the model's own free-form answer and what we define as the listing control distribution, the label distribution the model produces when every catalogue name is listed. Their log scores were close to zero.

**Table 7.** Forecast contest on the two informative events of the association experiment (raw log score in nats per compliant sample; top-1 nomination in brackets; chance top-1 is 1/5 and 1/4).

| Predictor | Grid ban BFS (38 compliant, all DFS) | Shortest path ban Dijkstra (86 compliant, all Bellman-Ford/SPFA) | Mean log score |
|-|-|-|-|
| Association map, Borda (preregistered) | -2.817 (unit weight Dijkstra, miss) | -0.755 (Bellman-Ford/SPFA, hit) | -1.786 |
| Association map, first rank counts | -2.474 (bidirectional BFS, miss) | -0.190 (hit) | -1.332 |
| External map, Llama-3.1-8B Borda | -1.412 (DFS/IDDFS tie) | -0.928 (hit) | -1.170 |
| Latent frequency (typicality ladder) | -1.630 (tie over all survivors) | -1.406 (tie) | -1.518 |
| Free-form answer (standard alternative question) | -0.112 (DFS, hit) | -0.058 (hit) | -0.085 |
| Listing control distribution | -0.061 (DFS, hit) | -0.058 (hit) | -0.060 |

The family test, which the hypothesis treats as its direct test of substitution against subtraction, was degenerate here. It fits a substitution family (a point mass on the association winner with a uniform leak) and a subtraction family (the baseline restricted to the survivors) on half of an event's compliant samples and scores both on the other half. Because the baseline gave zero mass to every survivor, the subtraction family was uniform: the grid event was a tie at -1.63 and the shortest path event went to substitution (-0.058 against -1.406). With one decisive event the family test says nothing about the hypothesis.

**Mention twins are recommendations.** The mention twin was meant as a placebo that carries the name without the prohibition. It is not one. Mentioning an absent algorithm moved 100 points of mass to DFS and to Bellman-Ford/SPFA, 86 points to Floyd-Warshall, 72 to IDDFS and 56 to A*, and 10 to bidirectional BFS; it moved nothing for unit weight Dijkstra on grids, Dial and bidirectional Dijkstra. Several mentioned algorithms were then implemented badly (mention DFS passed 0.30, mention IDDFS 0.18, mention bidirectional Dijkstra 0.30).

**The sham ban control.** Bans of absent algorithms were planned as a negative control that should match the mention twin. Because the mention twin recommends, the comparison inverts (Table 8): a sham ban kept the default at 77-100%, while its mention twin moved the model to the mentioned algorithm whenever the model could write it. None of the nine sham events was equivalent to its twin under the paraphrase null, whose 95th percentile was 0.003 bits. Against the baseline, sham bans moved some mass toward a related algorithm: banning Floyd-Warshall gave 23% Bellman-Ford/SPFA, banning IDDFS 12% DFS.

**Table 8.** Sham bans (bans of absent algorithms) against their mention twins. JS is the Jensen-Shannon divergence, that is, a symmetric and bounded divergence in bits between the two label distributions; the default's share is BFS on the grid task and Dijkstra on the shortest path task.

| Event | JS (ban vs mention) | Default share under ban | Default share under mention | Shift (points) | Compliant samples (realised mode) |
|-|-|-|-|-|-|
| Grid ban DFS | 0.801 | 0.96 | 0.0 | +96 | 86 (BFS) |
| Grid ban bidirectional BFS | 0.053 | 0.99 | 0.86 | +13 | 92 (BFS) |
| Grid ban IDDFS | 0.741 | 0.88 | 0.0 | +88 | 80 (BFS 76, DFS 4) |
| Grid ban A* | 0.506 | 1.0 | 0.24 | +76 | 72 (BFS) |
| Grid ban unit weight Dijkstra | 0.027 | 0.92 | 1.0 | -8 | 71 (BFS 69, DFS 2) |
| Shortest path ban Bellman-Ford/SPFA | 0.780 | 0.94 | 0.0 | +94 | 92 (Dijkstra) |
| Shortest path ban bidirectional Dijkstra | 0.007 | 0.97 | 1.0 | -3 | 100 (Dijkstra 97, Bellman-Ford/SPFA 3) |
| Shortest path ban Floyd-Warshall | 0.745 | 0.77 | 0.0 | +77 | 71 (Dijkstra 68, Bellman-Ford/SPFA 3) |
| Shortest path ban Dial | 0.015 | 0.95 | 1.0 | -5 | 97 (Dijkstra 95, Bellman-Ford/SPFA 2) |

**The succession stalled at step 2.** Banning the first substitute as well (BFS and DFS on the grid task, Dijkstra and Bellman-Ford/SPFA on the shortest path task) failed outright. 94 of 100 and 100 of 100 programs used a banned algorithm, leaving 5 and 0 compliant samples, and the preregistered stop rule (fewer than 20 compliant) ended both successions. The model reimplemented the banned mechanism under another description (Table 9). On the grid task 41 of 94 recurrent programs never named the banned algorithm and 20 called their DFS `backtracking`; on the shortest path task 58 of 100 never named it, and 19 described SPFA as `BFS with pruning`.

**Table 9.** Recurrence of banned algorithms and how often recurrent programs avoid naming them (regular expression counts over comments and identifiers).

| Event | Recurrent programs | Naming the banned algorithm | Not naming it | Most common descriptors |
|-|-|-|-|-|
| Grid ban BFS | 10 | 1 | 9 | `queue` 10 |
| Grid ban DFS (sham) | 4 | 2 | 2 | `backtracking` 2 |
| Grid succession step 2 (BFS, DFS) | 94 | 53 | 41 | `backtracking` 20, `queue` 16, `BFS` 7 |
| Shortest path ban Dijkstra | 9 | 8 | 1 | `priority queue` 9, `queue` 8 |
| Shortest path ban Bellman-Ford/SPFA (sham) | 5 | 1 | 4 | `queue` 3 |
| Shortest path succession step 2 (Dijkstra, Bellman-Ford/SPFA) | 100 | 42 | 58 | `BFS` 98, `queue` 91, `priority queue` 48, `pruning` 19 |

**The ladder limit test.** The hypothesis predicts that a ban fails more often when the banned algorithm's alternative is unclear. With four present algorithm events the relation cannot be estimated (Table 10). The grid modal ban had the lowest clarity and was obeyed; the two step-2 events had higher clarity and failed. The pooled Spearman rank correlation between recurrence and clarity was -0.2 over 4 events.

**Table 10.** Recurrence of the banned algorithm against clarity of its alternative.

| Event | Recurrence | Clarity | Clarity corrected for chance | Kendall's W |
|-|-|-|-|-|
| Grid ban BFS | 0.10 | 0.20 | 0.0 | 0.52 |
| Grid succession step 2 | 0.94 | 0.45 | 1.0 | 0.577 |
| Shortest path ban Dijkstra | 0.09 | 1.0 | 1.0 | 0.639 |
| Shortest path succession step 2 | 1.00 | 0.65 | 0.533 | 0.573 |

**What this experiment settled.** On the one event where the model's ranked association map and its free-form answer disagreed (the grid task), the free-form answer was right and the map was wrong; on the other event both were right. The ranking instrument, which the design chose because it gives full support where a free-form answer gives a point mass, does not measure the same association the model acts on. The typicality predictor built from baseline frequencies is uninformative under a full collapse, while the listing control distribution, a typicality measure taken under a prompt that names every algorithm, predicted both events. Bans naming several algorithms fail by disguise, so compliance has to be checked at the level of mechanism, not name. The labeller gate failed its runtime accuracy targets (Table 2), and every runtime and AST disagreement was resolved by the judge. Both task suites passed their acceptance checks: all 22 reference implementations passed, and every planted mutant (an off by one distance, a hop count in place of a weighted distance, a path through a wall, a diagonal step) was rejected. Resending 6 requests (64 samples) with the same request seeds reproduced 39 of 64 texts exactly, so results reproduce in distribution rather than token for token. An independent script rederived all 36 headline numbers from the raw files.

## 1.6 Geometry experiment: the read position manifold, the ban shift, and activation removal

**Why.** The hypothesis places the algorithm decision at the read position and predicts that the ban shift there, the change in the read position state that the ban causes, has a larger component toward the associated alternative than away from the banned algorithm. This experiment built the solution manifold at the read position, tested whether the read position encodes the algorithm at all, nominated the geodesically nearest survivor as a third predictor (the geodesic kernel, a forecast that weights each survivor by the exponential of minus its geodesic distance from the banned algorithm's centroid, scaled by the median distance between centroids), decomposed the ban shift, and tried to remove the modal algorithm with an activation edit instead of a prompt [ARTIFACT:art_D6Z0Snf09sFL]. It ran HF `generate` on one NVIDIA GPU with 23 GB of memory, since vLLM could not start, for about 2.2 GPU hours; OpenRouter spend was about USD 0.09.

**Design.** Forced implementation prompts (`Implement X for this task`) with 30 paraphrases per catalogue algorithm, plus a name masked set that describes X without naming it, gave a point cloud of residual stream activations at the read position for each algorithm for layers 8 to 28 of 36. A logistic linear probe from the read position state to the algorithm label was trained with one paraphrase held out at a time and compared with 20 shuffled label refits, the control-task logic of probe selectivity [24]. Two gate statistics were computed per layer: transfer accuracy from named to name masked prompts, and the Jensen-Shannon divergence, that is, a symmetric and bounded divergence, between the probe's decoded distribution on the baseline prompts and the realised label distribution of the baseline. The manifold used principal component analysis down to 95% of the variance, a k-nearest-neighbour graph with k=10, geodesic distances along the graph as in Isomap [25], two dimensional multidimensional scaling and the TwoNN intrinsic-dimension estimator [26], following the manifold-steering instrument [27].

**Manipulation check.** The model can write most catalogue algorithms when told to, but not all of them correctly (Table 11). Forced IDDFS was implemented as IDDFS every time on the grid task and never passed the tests; forced bidirectional Dijkstra and forced Dial were implemented as asked in only 33% and 37% of samples. These two shortest path algorithms were flagged, and their centroids rest on fewer valid points.

**Table 11.** Forced implementation prompts in the geometry experiment (30 samples each): share labelled as the requested algorithm, and pass rate, for named and name masked prompts.

| Task | Requested algorithm | Named: share as asked / pass | Name masked: share as asked / pass |
|-|-|-|-|
| Grid | BFS | 1.0 / 1.0 | 1.0 / 0.933 |
| Grid | DFS | 1.0 / 0.30 | 0.933 / 0.167 |
| Grid | bidirectional BFS | 0.667 / 0.233 | 0.967 / 0.067 |
| Grid | IDDFS | 1.0 / 0.0 | 0.767 / 0.0 |
| Grid | A* | 0.967 / 0.967 | 1.0 / 0.933 |
| Grid | unit weight Dijkstra | 1.0 / 0.90 | 1.0 / 0.833 |
| Shortest path | Dijkstra | 1.0 / 1.0 | 1.0 / 0.967 |
| Shortest path | Bellman-Ford/SPFA | 1.0 / 0.767 | 0.767 / 0.667 |
| Shortest path | bidirectional Dijkstra | 0.333 / 0.50 | 0.20 / 0.433 |
| Shortest path | Floyd-Warshall | 1.0 / 1.0 | 0.733 / 0.667 |
| Shortest path | Dial | 0.367 / 0.30 | 0.567 / 0.70 |

**Does the read position encode the algorithm?** Named probes reached 0.98-1.0 accuracy at every layer, which says only that the algorithm's name is in the context. The informative statistic is transfer to name masked prompts (Figure 1). It rose with depth and peaked at layer 27 on the grid task (0.672 against a shuffled label 95th percentile of 0.218) and at layer 24 on the shortest path task (0.54 against 0.307). The decoder criterion split the tasks. On the shortest path task the probe decoded the baseline state as 98% Dijkstra (JS 0.011 against a null 5th percentile of 0.030). On the grid task it decoded the baseline as DFS 0.60, unit weight Dijkstra 0.27 and BFS 0.12, while the model writes BFS every time, so the grid read position gate failed and the grid geometry below carries that flag.

[FIGURE:fig_probe_layers]

**The manifold.** The point clouds are low-dimensional: TwoNN intrinsic dimension 4.16 on the grid task and 5.24 on the shortest path task, against 11.92 and 11.58 for nulls with shuffled columns (5th-95th percentiles 10.78-13.46 and 10.64-12.71). MDS stress-1, the residual misfit of the two dimensional embedding, was 0.22 on both tasks and geodesic and Euclidean distances had Spearman correlation 0.87 and 0.90. Figure 2 draws the two maps with every condition's read position point, and Table 12 gives the geodesic distances from the default's centroid. On the grid task, BFS's two nearest centroids are DFS (41.19) and unit weight Dijkstra (58.39); A*, IDDFS and bidirectional BFS lie 71-95 away. On the shortest path task Dijkstra's nearest centroid is Floyd-Warshall (25.49), with Bellman-Ford/SPFA and bidirectional Dijkstra tied at about 42.

[FIGURE:fig_manifold]

**Table 12.** Geodesic distances between centroids at the read position (grid task, layer 27; shortest path task, layer 24), from the default algorithm's centroid.

| Task | From | To: distance |
|-|-|-|
| Grid | BFS | DFS 41.19; unit weight Dijkstra 58.39; A* 71.06; IDDFS 81.66; bidirectional BFS 94.95 |
| Shortest path | Dijkstra | Floyd-Warshall 25.49; Bellman-Ford/SPFA 42.18; bidirectional Dijkstra 42.46; Dial 54.96 |

The ban points do not sit near the centroids of the algorithms the model then wrote. Under the grid ban the read position point moved far from both BFS and DFS (from (-20.26, -58.22) for the baseline to (-24.67, 10.46)), while the mention point of BFS stayed close to the BFS centroid; the ban points of all six grid algorithms clustered together in one region of the map regardless of which algorithm was banned. This matches the decomposition below: most of the ban shift is not along the algorithm directions.

**The bans in this experiment.** Here the modal bans mostly failed (Table 13). On the grid task 62 of 100 programs were still BFS and the 18 compliant programs split into DFS 10 and unit weight Dijkstra 8, so there was no clear realised mode. On the shortest path task 72 of 100 were still Dijkstra and all 22 compliant programs were Bellman-Ford/SPFA. Compliance depended on the paraphrase: on the grid task four of the ten ban wordings gave 10 of 10 BFS while two gave 0 of 10 (Section 1.11). Some programs acknowledged the ban in a comment and used the algorithm anyway (`# Dijkstra's algorithm (but since the user said not to use Dijkstra's algorithm, this is a workaround)`). Three step-2 bans were run as exploratory events after the preregistered succession stopped. On the grid task the displaced mass landed only on BFS's two geodesic neighbours, DFS and unit weight Dijkstra, and banning one of them moved the compliant programs to the other; it never reached A*, IDDFS or bidirectional BFS. In the words of the request, mass moved to the edge of the banned region rather than to the opposite side. On the shortest path task the mass went to the second nearest centroid, Bellman-Ford/SPFA, and the nearest, Floyd-Warshall, received none. *(Correction, iteration 2: the claim that Bellman-Ford/SPFA is second nearest does not survive the sensitivity matrix of this experiment, which puts bidirectional Dijkstra (40.91) closer to Dijkstra than Bellman-Ford/SPFA (42.18) once the two flagged centroids are recomputed from correctly labelled forced samples. Under paraphrase level resampling Floyd-Warshall is nearest in every subsample, and Bellman-Ford/SPFA is second at layers 23 to 27 and third at layers 21 and 22; Section 2.3.2.)*

**Table 13.** Ban events in the geometry experiment (all coded samples; compliant = correct and not banned).

| Event | N | Labels | Compliant (labels) | Realised mode | Status |
|-|-|-|-|-|-|
| Grid ban BFS | 100 | BFS 62, DFS 29, unit weight Dijkstra 9 | 18 (DFS 10, unit weight Dijkstra 8) | no clear mode | primary |
| Grid ban BFS and DFS | 50 | BFS 29, unit weight Dijkstra 19, DFS 2 | 18 (unit weight Dijkstra 18) | unit weight Dijkstra | exploratory |
| Grid ban BFS and unit weight Dijkstra | 50 | BFS 31, DFS 17, unit weight Dijkstra 2 | 5 (DFS 5) | DFS | exploratory |
| Shortest path ban Dijkstra | 100 | Dijkstra 72, Bellman-Ford/SPFA 27, other 1 | 22 (Bellman-Ford/SPFA 22) | Bellman-Ford/SPFA | primary |
| Shortest path ban Dijkstra and Bellman-Ford/SPFA | 50 | Dijkstra 37, Bellman-Ford/SPFA 12, other 1 | 0 | no clear mode | exploratory |

The ban raised the correctness conditioned Hill number from 1.00 to 2.034 on the grid task at a pass-rate cost of 0.99 to 0.76, and from 1.00 to 1.723 on the shortest path task at 1.00 to 0.94. Most of this diversity is the banned algorithm mixed with its substitute, since banned programs that pass the tests count toward Hill_cc.

**The forecast contest.** Forecasts for 45 planned events were committed by hash (sha256 186f7182...) at 16:36:57 UTC, before any ban or removal sample. Table 14 scores them. This experiment's own association elicitation produced different maps from the association experiment's: it nominated A* for BFS (clarity 0.80, Kendall's W 0.886) and Dial for Dijkstra (clarity 0.579). Both nominations missed and the association map was the worst predictor, worse than uniform. The geodesic kernel was the best on the two primary events (mean -1.433 against -1.563 for uniform), by a margin of 0.13 nats per sample, and no predictor scored a top-1 hit on a primary event.

**Table 14.** Forecast contest in the geometry experiment (raw mean log score; top-1 nomination; the samples scored are all labels of the event other than the banned algorithm).

| Event (samples scored) | Association map | Latent frequency | Geodesic kernel | Read position decoder |
|-|-|-|-|-|
| Grid ban BFS (38) | -3.543 (A*) | -1.630 (tie) | -1.337 (DFS) | -1.287 (DFS) |
| Shortest path ban Dijkstra (28) | -1.647 (Dial) | -1.496 (tie) | -1.530 (Floyd-Warshall) | -1.587 (bidirectional Dijkstra) |
| Grid ban BFS and DFS, exploratory (19) | -0.998 (unit weight Dijkstra, hit) | -1.406 (tie) | -1.073 (unit weight Dijkstra, hit) | -4.124 (IDDFS) |
| Grid ban BFS and unit weight Dijkstra, exploratory (17) | -3.966 (A*) | -1.406 (tie) | -1.280 (A*) | -1.372 (IDDFS) |
| Shortest path ban Dijkstra and Bellman-Ford/SPFA, exploratory (1) | -3.912 | -3.912 | -3.912 | -3.912 |
| Mean, 2 primary events | -2.595 | -1.563 | -1.433 | -1.437 |
| Mean, all 5 events; top-1 hits | -2.813; 1/5 | -1.970; ties | -1.826; 1/5 | -2.456; 0/5 |

**The shift decomposition.** The ban shift is the read position state under the ban minus the state under its reference, computed against the mention twin and against the listing control. It was decomposed in a preregistered order into a component away from the banned algorithm (u_ren), toward the association winner (u_sub), toward the most frequent survivor (u_typ) and toward the geodesically nearest other survivor (u_rel), each orthogonalised against the previous ones. The preregistered share test needed the u_sub share to exceed the u_ren share and the u_ren share to exceed a split half paraphrase null under both references. Table 15 gives the shares at the gate layer. The four named components together explained 1-39% of the squared norm; the rest was residual. The u_ren share exceeded its null in only 7 of 130 cells across the layer band (Dial under the mention reference at layers 23-27, and bidirectional Dijkstra twice), never under both references, so every algorithm was inconclusive. The cosine of each shift with the banned name's input embedding and unembedding row was at most 0.034 in absolute value. A synthetic test with a planted 36/64 split recovered it, so the decomposition code works; the shifts simply do not lie along the algorithm directions.

**Table 15.** Squared norm shares of the ban shift at the gate layer (layer 27 for the grid task, layer 24 for the shortest path task); u_typ is undefined when the most frequent survivor is also the association winner or no survivor has baseline mass.

| Task | Banned X | Reference | u_ren | u_sub | u_typ | u_rel | Residual | u_ren null p95 |
|-|-|-|-|-|-|-|-|-|
| Grid | BFS | mention | 0.067 | 0.054 | 0.012 | 0.003 | 0.863 | 0.248 |
| Grid | BFS | listing control | 0.058 | 0.061 | 0.034 | 0.004 | 0.844 | 0.248 |
| Grid | DFS | mention | 0.042 | 0.038 | n/a | 0.000 | 0.920 | 0.170 |
| Grid | DFS | listing control | 0.052 | 0.017 | n/a | 0.002 | 0.929 | 0.170 |
| Grid | bidirectional BFS | mention | 0.078 | 0.020 | n/a | 0.000 | 0.901 | 0.263 |
| Grid | bidirectional BFS | listing control | 0.001 | 0.099 | n/a | 0.003 | 0.897 | 0.263 |
| Grid | IDDFS | mention | 0.090 | 0.005 | n/a | 0.029 | 0.876 | 0.274 |
| Grid | IDDFS | listing control | 0.003 | 0.034 | n/a | 0.054 | 0.909 | 0.274 |
| Grid | A* | mention | 0.086 | 0.005 | n/a | 0.014 | 0.895 | 0.134 |
| Grid | A* | listing control | 0.003 | 0.004 | n/a | 0.003 | 0.990 | 0.134 |
| Grid | unit weight Dijkstra | mention | 0.017 | 0.041 | 0.014 | 0.000 | 0.927 | 0.287 |
| Grid | unit weight Dijkstra | listing control | 0.130 | 0.076 | 0.000 | 0.011 | 0.783 | 0.287 |
| Shortest path | Dijkstra | mention | 0.004 | 0.002 | 0.041 | 0.013 | 0.940 | 0.311 |
| Shortest path | Dijkstra | listing control | 0.047 | 0.003 | 0.050 | 0.000 | 0.900 | 0.311 |
| Shortest path | Bellman-Ford/SPFA | mention | 0.000 | 0.069 | n/a | 0.021 | 0.909 | 0.298 |
| Shortest path | Bellman-Ford/SPFA | listing control | 0.104 | 0.094 | n/a | 0.005 | 0.797 | 0.298 |
| Shortest path | bidirectional Dijkstra | mention | 0.107 | 0.079 | n/a | 0.001 | 0.812 | 0.126 |
| Shortest path | bidirectional Dijkstra | listing control | 0.003 | 0.027 | n/a | 0.000 | 0.970 | 0.126 |
| Shortest path | Floyd-Warshall | mention | 0.000 | 0.019 | n/a | 0.004 | 0.976 | 0.212 |
| Shortest path | Floyd-Warshall | listing control | 0.075 | 0.005 | n/a | 0.001 | 0.919 | 0.212 |
| Shortest path | Dial | mention | 0.329 | 0.056 | n/a | 0.001 | 0.614 | 0.267 |
| Shortest path | Dial | listing control | 0.014 | 0.015 | n/a | 0.001 | 0.970 | 0.267 |

**Activation removal of the modal algorithm.** The removal used affine directional ablation [28, 29], anchored at the mean of the survivors: the component of each activation along a difference-in-means direction d_X for the modal algorithm was moved to the survivors' mean, scaled by a coefficient alpha. Neither direction check reached its 0.9 target: the held-out AUC of d_X was 0.89 and 0.79 at the read position and at best 0.66 and 0.76 at generated positions. The fallback declared in advance therefore ran. It edited the prompt suffix including the read position, over a 5-layer band on the grid task and a 7-layer band on the shortest path task, at alpha 0.5, 1 and 2, with two random directions of identical edit norm under common random numbers (the same sampling seeds for edited and unedited runs). It moved 0 of 50 samples on either task at every alpha (Table 16). Between 78% and 90% of the edited outputs were byte-identical to their alpha=0 twins, as were 80-96% of the random direction outputs. The hook tests passed on both tasks: at alpha=0 the logits were identical to the unhooked model, the remaining projection on d_X after the edit was below 1e-6 of its value before, and random and d_X edits had exactly equal norms. A post hoc full variant that also edited every generated position still left 25 of 25 programs on BFS and on Dijkstra at alpha 2; at alpha 4 the d_X edit destroyed generation (25 of 25 without code on both tasks) and the random direction broke most outputs as well. The verdict, as declared, was untestable, because the removal was unsuccessful at the tested coefficients. The comparison between prompt bans and activation removal, which the hypothesis treats as a headline, could not be made.

**Table 16.** Affine directional ablation of the modal algorithm (prompt suffix variant declared in advance unless marked full; HF engine; pass rates over all samples).

| Task | Arm | Alpha | N | Labels | Pass | Moved off the modal algorithm | Identical text to alpha=0 |
|-|-|-|-|-|-|-|-|
| Grid | hooked control | 0 | 50 | BFS 50 | 1.0 | 0/50 | 1.0 |
| Grid | d_X | 0.5 / 1.0 / 2.0 | 50 each | BFS 50 each | 1.0 each | 0/50 each | 0.80 / 0.86 / 0.78 |
| Grid | random 1 | 0.5 / 1.0 / 2.0 | 25 each | BFS 25 each | 1.0 each | 0/25 each | 0.80 / 0.80 / 0.84 |
| Grid | random 2 | 0.5 / 1.0 | 25 each | BFS 25 each | 1.0 each | 0/25 each | 0.80 / 0.84 |
| Grid | d_X, full (post hoc) | 2.0 | 25 | BFS 25 | 0.76 | 0/25 | 0.0 |
| Grid | d_X, full (post hoc) | 4.0 | 25 | no code 25 | 0.0 | 0/25 | 0.0 |
| Grid | random 1, full (post hoc) | 4.0 | 25 | BFS 18, other 6, no code 1 | 0.0 | 6/25 | 0.0 |
| Shortest path | hooked control | 0 | 50 | Dijkstra 50 | 1.0 | 0/50 | 1.0 |
| Shortest path | d_X | 0.5 / 1.0 / 2.0 | 50 each | Dijkstra 50 each | 1.0 each | 0/50 each | 0.90 / 0.86 / 0.82 |
| Shortest path | random 1 | 0.5 / 1.0 / 2.0 | 25 each | Dijkstra 25 each | 1.0 each | 0/25 each | 0.88 / 0.96 / 0.92 |
| Shortest path | random 2 | 0.5 / 1.0 | 25 each | Dijkstra 25 each | 1.0 each | 0/25 each | 0.96 / 0.92 |
| Shortest path | d_X, full (post hoc) | 2.0 | 25 | Dijkstra 25 | 1.0 | 0/25 | 0.04 |
| Shortest path | d_X, full (post hoc) | 4.0 | 25 | no code 25 | 0.0 | 0/25 | 0.0 |
| Shortest path | random 1, full (post hoc) | 4.0 | 25 | no code 20, Dijkstra 3, other 2 | 0.0 | 2/25 | 0.0 |

**What this experiment settled.** The read position holds a low-dimensional map of the catalogue, and on the grid task the mass displaced by the ban went to the geodesic neighbours of the default; the geodesic kernel was the least bad forecaster on the primary events. *(Correction, iteration 2: those neighbours, DFS and unit weight Dijkstra, are also second choices of the model, so the observation is consistent with geodesic proximity and with typicality and does not separate them; both events called primary here fail the forecast contest's compliance gate; Sections 2.3.2 and 2.3.7.)* The read position does not, however, decode the grid task's actual default, the ban shift is almost entirely orthogonal to the algorithm directions, and an activation edit of the modal algorithm did nothing until it broke the model. The labeller passed its gate on both tasks. An independent recomputation reproduced 99 headline numbers with no mismatch.

## 1.7 Forking token experiment: is the algorithm decided during generation?

**Why.** If the read position does not fix the algorithm, the decision may be made at a few high entropy tokens during generation, as forking token analyses find for other outcomes [30, 31]. The knob this account implies is a sampler that raises temperature only around those tokens, in the spirit of adaptive temperature sampling for code [32]. This experiment screened that account on its own pool of about 10,000 labelled generations [ARTIFACT:art_1yV2vQ0EH4OY], with vLLM 0.11.0 in eager mode, its own tests (40 per task, 17 reference solutions) and a judge used only on 6 disputed programs (USD 0.024).

**Design.** A resampling screen took 10 base paths per task for the baseline and for the modal ban and drew 8 continuations at every fourth generated token over the first 92 tokens. Baseline paths were screened only at tokens 4, 8, 16, 32 and 64, a fallback declared in advance because the baseline was already fixed at the read position. Change points in the series of continuation outcome distributions were detected against a permutation threshold (a PELT detector [33] run alongside found none on any path), localised to single tokens, and confirmed with 30 continuations at each candidate and at two control positions without a change point. A prompt swap cut a baseline path just before or just after its commitment token (the first token of evidence that identifies the algorithm, such as the `deque` import) and continued it under the ban prompt. The knob arm compared global temperature 0.3-1.3 with temperature 1.3 applied only in a window around detected forking tokens, which we call the forking window knob, against a random window of the same size and an anchored window at the start of the code block. A planted change sensitivity test found that the detector caught a total variation change of 0.2, 0.3 and 0.5 in 82.5%, 95% and 99% of trials, with a 6% false-positive rate at no change.

**Table 17.** Sample pools in the forking token experiment.

| Task | Pool | N | Labels | Pass | Hill_cc |
|-|-|-|-|-|-|
| Grid | baseline, T=1.0 | 200 | BFS 200 | 0.91 | 1.0 |
| Grid | ban BFS, T=1.0 | 100 | DFS 78, BFS 21, unit weight Dijkstra 1 | 0.56 | 1.945 |
| Grid | baseline, T=0.3 / 0.7 / 1.3 | 100 each | BFS 100 each | 0.91 / 0.82 / 0.96 | 1.0 |
| Shortest path | baseline, T=1.0 | 200 | Dijkstra 200 | 0.995 | 1.0 |
| Shortest path | ban Dijkstra, T=1.0 | 100 | Bellman-Ford/SPFA 80, Dijkstra 20 | 1.00 | 1.649 |
| Shortest path | baseline, T=0.3 / 0.7 / 1.3 | 100 each | Dijkstra 100 each | 1.00 each | 1.0 |

**Where the outcome is fixed.** The sample pools behind the screen (Table 17) repeat the collapse: every baseline pool at every temperature was 100% BFS or 100% Dijkstra, and the ban pools were the only ones with a second algorithm. Under the baseline prompt every base path was fixed at the read position on both tasks: all continuations from token 0 onward produced the path's own algorithm (Table 18). Under the ban, outcomes were open for longer. On the grid task 3 of 10 ban paths were fixed from the read position and 5 of 10 by token 16; on the shortest path task none was fixed at the read position and only 3 of 10 by token 64. Change points were confirmed only on the shortest path ban paths: 6 forking tokens on 5 of the 10 paths, while the 3 grid candidates failed confirmation and the 10 control positions produced no false positive.

**Table 18.** Resampling screen. We call a base path decided at the read position when its continuations from token 0 agree with its final label at least 80% of the time, and fixed by token k when at least 7 of 8 continuations agree with it at every screened position from k on; the columns give the share of base paths of each kind.

| Condition | Base paths | Decided at the read position | Fixed by token 0 / 8 / 16 / 32 / 64 | Paths not fixed | Forking token candidates | Confirmed forking tokens | Final labels |
|-|-|-|-|-|-|-|-|
| Grid baseline | 10 | 1.0 | 1.0 / 1.0 / 1.0 / 1.0 / 1.0 | 0 | 0 | 0 | BFS 10 |
| Grid ban BFS | 10 | 0.8 | 0.3 / 0.3 / 0.5 / 0.5 / 0.5 | 7 | 3 | 0 | DFS 9, BFS 1 |
| Shortest path baseline | 10 | 1.0 | 1.0 / 1.0 / 1.0 / 1.0 / 1.0 | 0 | 0 | 0 | Dijkstra 10 |
| Shortest path ban Dijkstra | 10 | 0.4 | 0.0 / 0.1 / 0.1 / 0.1 / 0.3 | 10 | 10 | 6 | Bellman-Ford/SPFA 6, Dijkstra 4 |

The confirmed forking tokens are not the punctuation tokens that studies of forking paths report on other tasks (Table 19). Two are the `import` token at position 3, where the model decides which module to import, two are algorithm names written in comments (the tokens `Bell` and `D` at position 68, each with a leading space), one is `BFS` inside the description of an SPFA queue, and one is a newline at position 7. Across confirmed forking tokens the outcome entropy fell by a mean of -0.131 bits, that is, it rose slightly, because several forking tokens moved a path from a fixed outcome to a mixed one.

**Table 19.** Confirmed forking tokens (all on shortest path ban paths). TVD is the total variation distance between continuation outcome distributions on either side.

| Base path | Position | Token | Token type | TVD | Permutation p | Outcome entropy before / after (bits) |
|-|-|-|-|-|-|-|
| Shortest path ban 0 | 3 | `import` | import | 0.80 | 0.0005 | 0.567 / 0.353 |
| Shortest path ban 1 | 3 | `import` | import | 0.767 | 0.0005 | 0.211 / 0.784 |
| Shortest path ban 1 | 77 | `BFS` (leading space) | identifier | 0.333 | 0.013 | 1.0 / 0.65 |
| Shortest path ban 3 | 68 | `Bell` (leading space) | identifier | 0.333 | 0.002 | 0.948 / 0.211 |
| Shortest path ban 4 | 68 | `D` (leading space) | identifier | 0.533 | 0.0005 | 0.0 / 1.368 |
| Shortest path ban 7 | 7 | newline | whitespace | 0.90 | 0.0005 | 0.211 / 0.353 |

**Does the commitment token lock the algorithm in?** No. The prompt swap predicted that a ban would work better on a prefix cut before the commitment token than after it. The ban effect was the same on both sides (Table 20): on the grid task 75% of continuations avoided BFS before the cut and 73.5% after it, a difference of 0.015 with a 95% interval of -0.02 to 0.055. Writing `from collections import deque` did not commit the model to BFS. On the shortest path task the ban was weak on both sides of the cut (25.5% and 27% avoided Dijkstra).

**Table 20.** Prompt swap at the commitment token (10 base paths per task; ban effect = share of continuations avoiding the banned algorithm; 95% bootstrap intervals).

| Task | Ban effect, cut before commitment | Ban effect, cut after commitment | Before minus after | Banned share after the cut (lock in) |
|-|-|-|-|-|
| Grid | 0.75 [0.545, 0.91] | 0.735 [0.54, 0.895] | 0.015 [-0.02, 0.055] | 0.265 [0.095, 0.45] |
| Shortest path | 0.255 [0.155, 0.365] | 0.27 [0.155, 0.40] | -0.015 [-0.095, 0.05] | 0.73 [0.61, 0.84] |
| Pooled | 0.5025 [0.347, 0.648] | 0.5025 [0.347, 0.642] | 0.0 [-0.045, 0.04] | 0.498 [0.343, 0.638] |

**The forking window temperature knob.** Raising temperature only around detected forking tokens changed nothing about the algorithm (Table 21): every arm on both tasks was 100% BFS or 100% Dijkstra, and the difference in Hill_cc between the forking token window and a random window was 0 with a [0, 0] interval. What temperature did change was the number of distinct phrasings. On the grid task global temperature took the number of phrasing clusters (defined in Section 1.10) at a Jaccard threshold of 0.8 from 11 at T=0.3 to 63 at T=1.3, while the forking token window gave 10, about the same as T=0.3.

**Table 21.** Temperature arms of the forking token experiment (N=100 each; all programs BFS on the grid task and Dijkstra on the shortest path task). Phrasing clusters at Jaccard thresholds 0.7 / 0.8 / 0.9 over identifier normalised AST shingles; phrasing Hill number at 0.8.

| Task | Arm | Pass | Hill_cc | Phrasing clusters (0.7 / 0.8 / 0.9) | Phrasing Hill (0.8) | Mean length (tokens) |
|-|-|-|-|-|-|-|
| Grid | global T=0.3 | 0.91 | 1.0 | 8 / 11 / 18 | 6.28 | 335.15 |
| Grid | global T=0.7 | 0.82 | 1.0 | 17 / 25 / 35 | 14.36 | 345.11 |
| Grid | global T=1.0 | 0.94 | 1.0 | 24 / 41 / 60 | 24.58 | 331.6 |
| Grid | global T=1.3 | 0.96 | 1.0 | 39 / 63 / 80 | 44.72 | 342.62 |
| Grid | forking token window | 0.83 | 1.0 | 8 / 10 / 23 | 6.06 | 346.67 |
| Grid | random window | 0.85 | 1.0 | 6 / 11 / 20 | 5.63 | 349.55 |
| Grid | anchored window | 0.85 | 1.0 | 9 / 13 / 25 | 5.85 | 337.87 |
| Shortest path | global T=0.3 | 1.00 | 1.0 | 1 / 1 / 1 | 1.0 | 191.88 |
| Shortest path | global T=0.7 | 1.00 | 1.0 | 1 / 2 / 2 | 1.10 | 192.28 |
| Shortest path | global T=1.0 | 0.99 | 1.0 | 2 / 4 / 5 | 1.47 | 193.62 |
| Shortest path | global T=1.3 | 1.00 | 1.0 | 3 / 5 / 7 | 1.84 | 195.08 |
| Shortest path | forking token window | 1.00 | 1.0 | 1 / 2 / 2 | 1.06 | 192.01 |
| Shortest path | random window | 0.99 | 1.0 | 1 / 2 / 2 | 1.10 | 192.5 |
| Shortest path | anchored window | 1.00 | 1.0 | 1 / 1 / 2 | 1.0 | 192.3 |

**Dead end: the locus probes never ran to completion.** The decisive measurement for this account was a probe from residual-stream states at the read position, at generated tokens 8, 16, 32 and 64, at the forking token and at the commitment token, to the final label. The states were extracted (300 samples per task at 8 positions and 21 layers, with read position cosine to a separate pass of at least 0.9997), but the probe stage wrote an empty `probes.json` and no probe result exists. The strategy's locus diagnostic is therefore undetermined. *(Correction, iteration 2: the cause is now recorded. `probes.json` (28 bytes, an empty summary) was written at 18:29:22, while the state log records the state phase starting at 18:31:55 and the grid and shortest path states saved at 18:34:34 and 18:34:50: the probe stage ran before its inputs existed. The states (`states/T{1,2}_part_001-005.npz`, about 790 MB, kept on the run volume) were intact, and the audit ran the probe on them in iteration 2; Section 2.3.1.)* The preregistered verdict rule returned INCONCLUSIVE: no confirmed forking token on the grid task, confirmed forking tokens on half of the shortest path ban paths, and no effect of the forking window knob.

**What this experiment settled.** Without a ban the algorithm is fixed before the first generated token on both tasks, so there is no forking token for temperature to act on. Under a ban the outcome stays open for dozens of tokens and a few forking tokens exist on the shortest path task, including the choice of import; the first token that identifies the algorithm does not lock the algorithm in. A temperature knob aimed at forking tokens adds neither ideas nor phrasings.

## 1.8 Decommitment experiment: does one list versus implement direction control the collapse?

**Why.** An alternate account holds that the bottleneck is commitment, not the choice of a particular algorithm: a model asked to list ten approaches knows many, and a model asked to implement one collapses. If a single direction separates the two framings, adding it while the model implements should spread its output over the repertoire instead of moving it to one substitute. This experiment built that direction, steered with it under random direction and prompting controls [34], and tested whether a ban moves the read position along it [ARTIFACT:art_U5UKkFrOgSsE].

**Design.** The decommitment direction is a difference-in-means direction at the read position: the mean state over 50 paraphrases of `list ten different approaches to this task`, which we call the list framing, minus the mean over 50 paraphrases of `implement one correct algorithm`, the implement framing, per layer. Held-out separation AUC was 1.00 at every layer from 9 to 28, and layer 18 was chosen by the held-out separation statistic d' (8.55). At layer 18 the direction's norm was 0.21 (grid) and 0.19 (shortest path) times the state norm, its split half cosine was 0.99, and the two tasks' directions had cosine 0.98. Its cosine was 0.53-0.55 with a breadth direction that contrasts listing approaches with naming one, -0.08 to -0.04 with a variable name placebo direction, and 0.59-0.62 with the shift produced by the enumeration prompt. It was added as c times the state norm times the unit direction at the read position and at every generated token, with c in {0.25, 0.5, 1, 1.5} plus a preregistered bisection. The correctness preserving coefficient c* was the largest c with at least 80% of the c=0 pass rate: 0.1 on the grid task and 0.25 on the shortest path task. Controls were two random directions, the placebo and breadth directions at c*, the other task's direction, the prompt we call the enumeration prompt (`list 10 approaches, then implement one`), the modal ban and its mention twin, and a two-step succession. Labels came from hidden tests (43 and 39 cases), the tracer and AST rules, with a judge on disagreements; the labeller gate passed (Table 2). An engine check compared the vLLM baseline with the hooked HF arm at c=0: identical on the grid task, total variation 0.03 on the shortest path task (Fisher p 0.40).

**Steering moved the shortest path task and never the grid task.** On the grid task every arm except the bans wrote BFS (Table 22). At c=0.25 the pass rate fell to 0.57 and every passing program was still BFS; at c=0.5 it fell to 0.03, and from c=1 all output was broken (pass 0, 28-85% of samples truncated). On the shortest path task the c*=0.25 arm moved correct programs from Dijkstra to Bellman-Ford/SPFA (Bellman-Ford/SPFA 54, Dijkstra 23, other 1, against Dijkstra 88 and Bellman-Ford/SPFA 7 at c=0), a rarefied Hill-number gain of +0.65 (paraphrase-cluster 90% interval 0.31 to 0.97) at a 17-point pass-rate cost. A random direction at the same strength did almost the same (+0.59), and the difference between the decommitment direction and that random direction was +0.07 (-0.26 to 0.39). The gain therefore is not specific to the direction, although it exceeded the second random direction (+0.70, 0.38 to 1.01) and the placebo (+0.47, 0.01 to 0.84). Per-sample flips against c=0 under common random numbers were 0.66 for the decommitment direction, 0.42 and 0.18 for the two random directions and 0.22 for the placebo. On the shortest path task the off-mode rate peaked at c=0.25 (0.55) and fell again at c=0.5 (0.12) as programs broke. A Hill number of 2 was reached at c of about 0.40 for a 34.5-point pass cost; a Hill number of 3 was not reached in the tested range.

**Table 22.** BUY table of the decommitment experiment. Delta Hill is the change in correctness conditioned Hill number, rarefied to a common sample depth, against the HF c=0 arm for steering and against the vLLM baseline for prompts, with a 90% paraphrase-cluster interval; efficiency is Delta Hill per pass-rate point lost.

| Task | Knob | Pass | Pass points lost | Labels of correct programs | Delta Hill [90% interval] | Efficiency |
|-|-|-|-|-|-|-|
| Grid | vLLM baseline (N=200) | 1.00 | n/a | BFS 200 | n/a | n/a |
| Grid | HF c=0 | 1.00 | n/a | BFS 100 | n/a | n/a |
| Grid | decommitment c=0.1 (c*) | 0.98 | 2 | BFS 98 | 0.0 [0.0, 0.0] | 0.0 |
| Grid | decommitment c=0.25 | 0.57 | 43 | BFS 57 | 0.0 | 0.0 |
| Grid | decommitment c=0.5 | 0.03 | 97 | BFS 3 | 0.0 | 0.0 |
| Grid | decommitment c=1 / 1.5 | 0.0 / 0.0 | 100 | none | n/a | n/a |
| Grid | random 1 / random 2 / placebo / breadth at c* | 0.98 / 1.00 / 1.00 / 0.99 | 2 / 0 / 0 / 1 | all BFS | 0.0 | 0.0 |
| Grid | other task's direction at c* (N=50) | 0.98 | 2 | all BFS | 0.0 | 0.0 |
| Grid | enumeration prompt | 1.00 | 0 | BFS 100 | 0.0 | n/a |
| Grid | mention BFS | 1.00 | 0 | BFS 100 | 0.0 | n/a |
| Grid | ban BFS | 0.64 | 36 | BFS 46, DFS 16, unit weight Dijkstra 2 | +0.99 [0.55, 1.34] | 0.028 |
| Grid | succession (ban BFS and DFS) | 0.88 | 12 | BFS 65, unit weight Dijkstra 13, DFS 7, A* 3 | +1.27 [0.64, 1.80] | 0.106 |
| Shortest path | vLLM baseline (N=200) | 0.89 | n/a | Dijkstra 169, Bellman-Ford/SPFA 8 | n/a | n/a |
| Shortest path | HF c=0 | 0.95 | n/a | Dijkstra 88, Bellman-Ford/SPFA 7 | n/a | n/a |
| Shortest path | decommitment c=0.25 (c*) | 0.78 | 17 | Bellman-Ford/SPFA 54, Dijkstra 23, other 1 | +0.65 [0.31, 0.97] | 0.038 |
| Shortest path | decommitment c=0.375 | 0.67 | 28 | Bellman-Ford/SPFA 47, Dijkstra 19 | +0.65 [0.29, 0.94] | 0.023 |
| Shortest path | decommitment c=0.5 | 0.37 | 58 | Dijkstra 25, Bellman-Ford/SPFA 10, other 2 | +0.87 [0.09, 1.38] | 0.015 |
| Shortest path | decommitment c=1 / 1.5 | 0.0 / 0.0 | 95 | none | n/a | n/a |
| Shortest path | random 1 at c* | 0.79 | 16 | Dijkstra 53, Bellman-Ford/SPFA 26 | +0.59 [0.21, 0.85] | 0.037 |
| Shortest path | random 2 at c* | 0.87 | 8 | Dijkstra 82, Bellman-Ford/SPFA 5 | -0.05 [-0.31, 0.20] | -0.006 |
| Shortest path | placebo at c* | 0.66 | 29 | Dijkstra 60, Dial 3, Bellman-Ford/SPFA 2 | +0.19 [-0.30, 0.70] | 0.006 |
| Shortest path | breadth direction at c* | 0.60 | 35 | Bellman-Ford/SPFA 31, Dijkstra 28, Dial 1 | +0.85 [0.46, 1.17] | 0.024 |
| Shortest path | other task's direction at c* (N=50) | 0.72 | 23 | Bellman-Ford/SPFA 28, Dijkstra 8 | +0.40 [-0.01, 0.69] | 0.018 |
| Shortest path | enumeration prompt | 0.82 | 6.5 | Dijkstra 80, Bellman-Ford/SPFA 2 | -0.08 [-0.27, 0.13] | -0.013 |
| Shortest path | mention Dijkstra | 0.94 | -5.5 | Dijkstra 92, Bellman-Ford/SPFA 2 | -0.09 [-0.29, 0.12] | n/a |
| Shortest path | ban Dijkstra | 0.87 | 1.5 | Dijkstra 49, Bellman-Ford/SPFA 38 | +0.79 [0.60, 0.90] | 0.524 |
| Shortest path | succession (ban Dijkstra and Bellman-Ford/SPFA) | 0.68 | 20.5 | Bellman-Ford/SPFA 34, Dijkstra 33, other 1 | +0.93 [0.66, 1.17] | 0.045 |

The prompting baselines decide the comparison. The enumeration prompt, which states the decommitment framing in words, produced no diversity on either task. The modal ban bought +0.79 effective algorithms on the shortest path task for 1.5 pass points, an efficiency 14 times that of steering, but most banned samples still used the banned algorithm: 46 of 64 correct grid programs were BFS and 49 of 87 correct shortest path programs were Dijkstra. The ban's Hill gain is therefore mostly a mixture of ban failures and Bellman-Ford/SPFA, not two algorithms chosen freely.

**Does a ban decommit?** The commitment test projects the ban minus mention shift at layer 18 onto the axis from the implement framing (0) to the list framing (1). The ban moved the read position toward the list framing by 0.039 on the grid task and 0.053 on the shortest path task (Table 23), outside the preregistered paraphrase split null band (plus or minus 0.024 and 0.025), so the preregistered label is that the ban decommits. An audit judged that band too narrow; exact permutation tests gave p = 0.021 and 0.007 (label permutation) and 0.025 and 0.016 (paired sign flip), with 8 of 10 paraphrase pairs positive on each task. The shift is small: the enumeration prompt, the positive control, moved the state by 0.544 and 0.582 of the same distance, and the listing control sat at 0.816 and 0.806. The share of the ban shift along the direction ranked at the 78th and 87th percentiles of a null built from the top 50 principal components.

**Table 23.** Position along the implement (0) to list (1) axis at layer 18 for each prompt condition.

| Condition | Grid | Shortest path |
|-|-|-|
| baseline | -0.054 | -0.075 |
| enumeration prompt | 0.483 | 0.495 |
| listing control | 0.816 | 0.806 |
| framing that names one approach | 0.653 | 0.650 |
| ban of the modal algorithm / its mention twin | 0.040 / 0.001 | 0.035 / -0.018 |
| ban DFS / mention DFS (Grid); ban Bellman-Ford/SPFA / mention (Shortest path) | 0.023 / -0.001 | 0.047 / -0.018 |
| ban bidirectional BFS / mention (Grid); ban bidirectional Dijkstra / mention (Shortest path) | 0.007 / -0.004 | 0.017 / 0.001 |
| ban IDDFS / mention (Grid); ban Floyd-Warshall / mention (Shortest path) | 0.036 / 0.012 | 0.030 / -0.013 |
| ban A* / mention (Grid); ban Dial / mention (Shortest path) | 0.073 / 0.004 | 0.052 / -0.002 |
| ban unit weight Dijkstra / mention (Grid) | 0.051 / 0.010 | n/a |
| Ban minus mention for the modal algorithm (null band) | 0.039 (±0.024) | 0.053 (±0.025) |
| Enumeration minus baseline, positive control (null band) | 0.544 (±0.047) | 0.582 (±0.048) |

**The forecast record.** Forecasts were committed at 16:26:17 UTC, before the ban samples. On the shortest path modal ban all 38 compliant programs were Bellman-Ford/SPFA; the decommitted survivor distribution scored -0.058 and hit, the vLLM frequency forecast -0.219 (hit), the HF frequency forecast -0.238 (hit) and the uniform forecast -1.406. On the grid modal ban (18 compliant: DFS 16, unit weight Dijkstra 2) every forecast was degenerate, because no correct program other than BFS existed before the ban, and all tied at -1.630. The succession events tied as well (16 compliant grid programs, unit weight Dijkstra 13 and A* 3; 1 compliant shortest path program).

**What this experiment settled.** The decommitment direction exists as a clean difference-in-means direction, shared across tasks, but adding it is a generic perturbation: it moves the shortest path task toward Bellman-Ford/SPFA as a random direction does and costs a sixth of the pass rate, and it never moves the grid task. Its prompt counterpart, the enumeration prompt, does nothing. A ban moves the read position measurably but slightly toward the list framing. The preregistered verdict was PARTIAL (the diversity gain held on one task, the specificity test failed). vLLM same seed determinism failed on the grid task, so vLLM arms are reproducible in distribution only, and every common random number analysis used HF arms.

## 1.9 Instruction tuning experiment: did post-training install the collapse?

**Why.** If instruction tuning installed the collapse, the base model should spread over several algorithms at matched prompts, and subtracting the instruct minus base activation difference should restore that spread inside the instruct model. Base models are reported to be more diverse than aligned ones [35], and chat formatting alone narrows output diversity [36]; this experiment separated the two causes on the two tasks [ARTIFACT:art_HF8nK8B_Lqyy].

**Design.** A two by two design crossed weights (Qwen3-8B-Base, Qwen3-8B) with format (code completion without a chat template, which we call plain completion, or the instruct chat template), all at temperature 1.0 with top-p 1.0, thinking off. Each program ran on 47 (grid) or 46 (shortest path) hidden tests and was labelled by the tracer and AST rules with Gemini 2.5 Flash Lite as judge on disagreements; a second judge agreed with the first on 95% of 40 audit programs (kappa 0.93). The runtime and AST labels agreed with kappa 0.77 over all parseable programs, but much lower on base-model output (0.20-0.50), where 217 of 292 grid programs in plain completion needed the judge. The sharpening direction is the paired difference between instruct and base read position states over the same chat-templated prompts, per layer from 8 to 28. It was subtracted at c in {0.5, 1.0, 1.5} over the whole band, at the read position only, and at layer 18 only, against two norm-matched random directions. Hardware was one NVIDIA GPU with 23 GB of memory (2.1 GPU hours); judge spend was USD 0.21.

**The collapse is sharpened by post-training, not invented by it.** Table 24 gives every arm. The instruct model in chat format is collapsed on both tasks. The base model under the same chat tokens writes mostly the same algorithm but less exclusively: BFS in 49 of 57 correct grid programs and Dijkstra in 63 of 90 correct shortest path programs, with Bellman-Ford/SPFA second (24). In plain completion the base model rarely writes a correct program (pass 0.05 and 0.08), and its correct shortest path programs are mostly Bellman-Ford/SPFA (16 of 25).

**Table 24.** Arms of the instruction tuning experiment (vLLM, T=1.0). Hill_cc with 95% cluster bootstrap interval; Hill_all over all parseable labelled programs.

| Arm | Task | N | Parse rate | Pass [95% Wilson] | Correct | Labels of correct programs | Hill_cc [95%] | Hill_all |
|-|-|-|-|-|-|-|-|-|
| base, plain completion | Grid | 300 | 0.97 | 0.05 [0.03, 0.08] | 15 | BFS 12, DFS 3 | 1.65 [1.00, 2.00] | 3.34 |
| base, plain completion | Shortest path | 300 | 0.97 | 0.08 [0.06, 0.12] | 25 | Bellman-Ford/SPFA 16, Dijkstra 8, Floyd-Warshall 1 | 2.18 [1.00, 2.73] | 3.24 |
| base, chat template | Grid | 300 | 0.58 | 0.19 [0.15, 0.24] | 57 | BFS 49, DFS 7, A* 1 | 1.58 [1.10, 2.06] | 3.13 |
| base, chat template | Shortest path | 300 | 0.66 | 0.30 [0.25, 0.35] | 90 | Dijkstra 63, Bellman-Ford/SPFA 24, Floyd-Warshall 1, other 2 | 2.09 [1.63, 2.54] | 2.67 |
| instruct, plain completion | Grid | 100 | 0.93 | 0.73 [0.64, 0.81] | 73 | BFS 73 | 1.00 [1.00, 1.00] | 1.41 |
| instruct, plain completion | Shortest path | 100 | 0.89 | 0.72 [0.63, 0.80] | 72 | Dijkstra 57, Floyd-Warshall 8, Bellman-Ford/SPFA 7 | 1.93 [1.41, 2.37] | 2.60 |
| instruct, chat template | Grid | 200 | 1.00 | 1.00 [0.98, 1.00] | 200 | BFS 200 | 1.00 [1.00, 1.00] | 1.00 |
| instruct, chat template | Shortest path | 200 | 1.00 | 1.00 [0.98, 1.00] | 200 | Dijkstra 193, Bellman-Ford/SPFA 7 | 1.16 [1.03, 1.31] | 1.16 |
| base, plain completion, ban | Grid | 100 | 0.95 | 0.01 [0.00, 0.05] | 1 | BFS 1 | 1.00 | 3.50 |
| base, plain completion, ban | Shortest path | 100 | 0.98 | 0.08 [0.04, 0.15] | 8 | Dijkstra 4, Bellman-Ford/SPFA 4 | 2.00 | 3.43 |
| instruct, chat template, ban | Grid | 100 | 1.00 | 0.70 [0.60, 0.78] | 70 | BFS 57, DFS 12, unit weight Dijkstra 1 | 1.70 [1.22, 2.25] | 2.10 |
| instruct, chat template, ban | Shortest path | 100 | 1.00 | 1.00 [0.96, 1.00] | 100 | Dijkstra 54, Bellman-Ford/SPFA 46 | 1.99 [1.65, 2.00] | 1.99 |

The labels of base-model output lean heavily on the judge, which matters for the base arms' Hill numbers (Table 24b): runtime and AST rules agreed with kappa 0.20-0.50 on base-model programs, and the judge labelled 217 of 292 grid programs in plain completion. The final labels agreed with the judge on 97-100% of programs in every arm, and a 15-program audit per arm found them correct in every arm but one (0.93 on the base chat shortest path arm).

**Table 24b.** Labeller agreement per generation arm in the instruction tuning experiment.

| Arm | Task | Parseable programs | Kappa runtime vs AST | Final label vs judge | Runtime+AST label vs judge | Labelled by the judge |
|-|-|-|-|-|-|-|
| base, plain completion | Grid | 292 | 0.45 | 0.98 | 0.91 | 217 |
| base, plain completion | Shortest path | 291 | 0.20 | 0.99 | 0.92 | 266 |
| base, chat template | Grid | 175 | 0.40 | 0.99 | 0.99 | 94 |
| base, chat template | Shortest path | 199 | 0.50 | 0.97 | 0.94 | 94 |
| base, plain completion, ban | Grid | 95 | 0.43 | 0.98 | 0.93 | 68 |
| base, plain completion, ban | Shortest path | 98 | 0.34 | 0.99 | 0.93 | 83 |
| instruct, chat template | Grid | 200 | 1.00 | 1.00 | 1.00 | 0 |
| instruct, chat template | Shortest path | 200 | 1.00 | 1.00 | 1.00 | 7 |
| instruct, plain completion | Grid | 93 | 0.71 | 1.00 | 1.00 | 17 |
| instruct, plain completion | Shortest path | 89 | 0.89 | 1.00 | 1.00 | 23 |
| instruct, chat template, ban | Grid | 100 | 0.64 | 1.00 | 1.00 | 20 |
| instruct, chat template, ban | Shortest path | 100 | 0.98 | 1.00 | 1.00 | 46 |

Table 25 gives the preregistered contrasts. The weights effect (instruct chat minus base chat) is negative on both tasks: -0.58 effective algorithms on the grid task and -0.93 on the shortest path task, with intervals excluding zero. The format effect inside the base model is near zero on both tasks, while inside the instruct model the chat format cuts the shortest path Hill number by 0.76. The preregistered verdict was INSTALLED_BY_POST_TRAINING on the shortest path task and MIXED on the grid task, where the gap in modal share of 14.0 points fell just short of the 15-point bar; under Hill_all both tasks read INSTALLED_BY_POST_TRAINING. At the originally planned N, before the base arms were extended to 300, both tasks read MIXED. The chat format also switched the base model's shortest path mode from Bellman-Ford/SPFA to Dijkstra.

**Table 25.** Collapse screen: differences in Hill numbers with paraphrase cluster bootstrap 95% intervals.

| Task | Weights effect: instruct chat minus base chat | Format effect in base: chat minus plain completion | Format effect in instruct | Interaction | Verdict (Hill_cc) | Verdict (Hill_all) |
|-|-|-|-|-|-|-|
| Grid (Hill_cc) | -0.58 [-1.01, -0.15] | -0.07 [-0.76, 0.88] | 0.00 [0.00, 0.00] | 0.07 [-0.83, 0.74] | MIXED | INSTALLED_BY_POST_TRAINING |
| Shortest path (Hill_cc) | -0.93 [-1.38, -0.46] | -0.09 [-0.79, 1.12] | -0.76 [-1.26, -0.23] | -0.67 [-1.73, 0.10] | INSTALLED_BY_POST_TRAINING | INSTALLED_BY_POST_TRAINING |
| Grid (Hill_all) | -2.13 [-2.66, -1.43] | -0.21 [-1.05, 0.55] | -0.41 [-0.66, -0.15] | -0.19 [-0.94, 0.63] | | |
| Shortest path (Hill_all) | -1.50 [-1.91, -1.06] | -0.57 [-1.04, -0.10] | -1.44 [-2.03, -0.71] | -0.87 [-1.60, 0.04] | | |

**The sharpening direction is a format direction.** The instruct minus base difference at the read position was stable (split half cosine 0.998-0.999 across the band) and largely shared between tasks (cosine between the two tasks' differences 0.84-0.93 across layers 8-28), with a relative norm of about 1.0-1.1 of the state at layer 18. The logit lens (reading an intermediate state through the model's unembedding matrix) at layer 28 showed what subtracting it promotes: `def` and `class` on the grid prompts, and `Conversation`, `Claude`, `Prompt` and `chat` on the shortest path prompts. Subtracting it over the band destroyed generation at every coefficient (0 of 100 parseable programs, Table 26); the downstream layers amplified the edit, so the gap to the base state was closed at layer 8 but overshot at layers 18 and 28 (gap closed -0.38 and -0.40 at c=1.5). Read position only subtraction turned the model into thinking style prose (73% and 95% of outputs opened like a thinking trace), and the code it still wrote named BFS and Dijkstra. Subtraction at layer 18 alone kept 94-98% of the pass rate at c=0.25 with no algorithm change. No coefficient of any variant restored diversity.

**Table 26.** Steering arms of the instruction tuning experiment (HF, coupled seeds; deltas against the hooked c=0 control).

| Task | Arm | N | Parse | Pass | Hill_cc | Delta Hill_cc | Delta pass (points) | Flip rate |
|-|-|-|-|-|-|-|-|-|
| Grid | control c=0 | 100 | 1.00 | 1.00 | 1.00 | n/a | n/a | n/a |
| Grid | random 1 | 100 | 0.96 | 0.41 | 1.00 | 0.00 | -59.0 | 0.04 |
| Grid | random 1, read position only, c=1.0 | 100 | 1.00 | 1.00 | 1.00 | 0.00 | 0.0 | 0.00 |
| Grid | random 2 | 100 | 0.98 | 0.68 | 1.00 | 0.00 | -32.0 | 0.01 |
| Grid | sharpening, band, c=0.5 / 1.0 / 1.5 | 100 each | 0.00 | 0.00 | n/a | n/a | -100.0 | n/a |
| Grid | sharpening, read position only, c=1.0 | 100 | 0.28 | 0.14 | 1.00 | 0.00 | -86.0 | 0.07 |
| Grid | same, no 512-token cutoff | 20 | 0.55 | 0.15 | 1.00 | 0.00 | -85.0 | 0.00 |
| Grid | sharpening, layer 18 only, c=0.25 / 0.5 / 1.0 | 50 each | 1.00 / 1.00 / 0.00 | 0.94 / 0.52 / 0.00 | 1.00 / 1.00 / n/a | 0.00 / 0.00 / n/a | -6.0 / -48.0 / -100.0 | 0.00 / 0.00 / n/a |
| Shortest path | control c=0 | 100 | 1.00 | 1.00 | 1.00 | n/a | n/a | n/a |
| Shortest path | random 1 | 100 | 1.00 | 0.00 | n/a | n/a | -100.0 | 0.00 |
| Shortest path | random 1, read position only, c=1.0 | 100 | 1.00 | 1.00 | 1.43 | +0.43 [0.12, 0.74] | 0.0 | 0.10 |
| Shortest path | random 2 | 100 | 1.00 | 0.33 | 1.00 | 0.00 | -67.0 | 0.36 |
| Shortest path | sharpening, band, c=0.5 / 1.0 / 1.5 | 100 each | 0.00 | 0.00 | n/a | n/a | -100.0 | n/a |
| Shortest path | sharpening, read position only, c=1.0 | 100 | 0.05 | 0.05 | 1.00 | 0.00 | -95.0 | 0.00 |
| Shortest path | same, no 512-token cutoff | 20 | 0.40 | 0.20 | 1.75 | +0.75 [0.00, 1.00] | -80.0 | 0.50 |
| Shortest path | sharpening, layer 18 only, c=0.25 / 0.5 / 1.0 | 50 each | 1.00 / 1.00 / 0.00 | 0.98 / 0.98 / 0.00 | 1.00 / 1.10 / n/a | 0.00 / +0.10 / n/a | -2.0 / -2.0 / -100.0 | 0.00 / 0.02 / n/a |

*(Correction, iteration 2: Table 26 reports Hill numbers and flip rates but not what the correct programs were, which hides a complete algorithm switch. On the shortest path task band random direction 2 turned all 33 of its correct programs into Bellman-Ford/SPFA, against Dijkstra 100 of 100 in the control, and band random direction 1 left no correct program; the read position only random edit gave Dijkstra 90, Bellman-Ford/SPFA 9 and other 1; layer-18 sharpening at c = 0.5 gave Dijkstra 48 and Bellman-Ford/SPFA 1; read position sharpening without the cutoff gave Dijkstra 3 and Bellman-Ford/SPFA 1. On the grid task every correct program in every arm was BFS (41 under band random direction 1, 68 under band random direction 2, 100 under the read position random edit). Source: audit `tables/perturbation_table.csv`; Section 2.3.5.)*

Table 26b shows why the band subtraction broke the model. The edit closed the gap between instruct and base states completely at layer 8 at c=1.0, but by layers 18 and 28 the downstream computation had erased most of the correction, and at c=1.5 it overshot past the base state.

**Table 26b.** Manipulation check at the read position: gap closed is 1 minus the ratio of two distances, from the mean steered state to the mean base state and from the mean instruct state to the mean base state, at layers 8, 18 and 28.

| Arm | Grid: layers 8 / 18 / 28 | Shortest path: layers 8 / 18 / 28 |
|-|-|-|
| sharpening, band, c=0.5 | 0.50 / 0.34 / 0.38 | 0.50 / 0.37 / 0.38 |
| sharpening, band, c=1.0 | 1.00 / 0.05 / 0.01 | 1.00 / 0.08 / 0.04 |
| sharpening, band, c=1.5 | 0.50 / -0.38 / -0.40 | 0.50 / -0.32 / -0.37 |
| random 1 | -0.12 / 0.06 / -0.07 | -0.12 / 0.05 / -0.08 |
| random 2 | -0.12 / 0.07 / -0.05 | -0.12 / 0.06 / -0.05 |
| sharpening, layer 18 only, c=0.25 / 0.5 / 1.0 | 0.00 / 0.25 / 0.04; 0.00 / 0.50 / 0.11; 0.00 / 1.00 / 0.36 | 0.00 / 0.25 / 0.06; 0.00 / 0.50 / 0.13; 0.00 / 1.00 / 0.34 |
| sharpening, read position only, c=1.0 | 1.00 / 0.05 / 0.01 | 1.00 / 0.08 / 0.04 |
| random 1, read position only, c=1.0 | -0.42 / 0.03 / -0.33 | -0.42 / 0.03 / -0.31 |

The ban prompt did better than any steering arm: on the shortest path task it raised Hill_cc from 1.16 to 1.99 with no loss of pass rate, the best price of any knob in the run (the artifact's efficiency score was 0.830), and on the grid task to 1.70 for 30 pass points. The base model, by contrast, did not obey bans: the banned share of the base model in plain completion moved from 0.46 to 0.36 on the grid task and from 0.25 to 0.27 on the shortest path task, with 0 and 4 compliant programs.

**The forecast record.** The base model's own survivor distribution, committed before the instruct ban samples, nominated DFS and Bellman-Ford/SPFA and hit both (log scores -0.470 and -0.220 against uniform -1.630 and -1.406). The base chat distribution did as well (-0.412 and -0.058), and on the shortest path task so did the instruct chat distribution (-0.058), because Bellman-Ford/SPFA was the second algorithm in every reference distribution.

**What this experiment settled.** Post-training concentrated an ordering the base model already had (BFS first, Dijkstra first in chat format, Bellman-Ford/SPFA second on the shortest path task); it did not install a new attractor. *(Correction, iteration 2: the preregistered verdicts stay as recorded above, INSTALLED_BY_POST_TRAINING on the shortest path task and MIXED on the grid task, and MIXED on both at the planned sample size; the base ordering matches the instruct ordering only under the chat template, and in plain completion the base model's shortest path mode is Bellman-Ford/SPFA, first rather than second.)* The direction that separates instruct from base states is about answer format, and subtracting it breaks the model rather than freeing it. This alternate passed its screen under the preregistered rule, but the pass rests on the shortest path task and on extended sample sizes, and the knob it implies does not work.

## 1.10 Decoding experiment: temperature, top-k, random seeds and creativity instructions

**Why.** The request asks three things directly: whether a tight temperature with top-k=10 yields one idea in many phrasings or many ideas, whether loosening temperature multiplies ideas or phrasings, and whether a random "seed" in the prompt (an entropy string or a list of unrelated words) pushes the model into a different region of its solution space. The account screened here says that temperature and random seeds change wording and leave the algorithm alone, and that only context with meaning moves it, in line with the finding that temperature correlates only weakly with novelty [37]. This experiment also produced the request's literal first figure, the BFS fraction by temperature [ARTIFACT:art_UoCVh2Qe5RZ0].

**Design.** The experiment drew 5,220 generations on one RTX 5090 with vLLM in eager mode, N=100 per cell (10 paraphrases of 10 samples). Besides the no cue baseline, a temperature grid crossed T in {0.3, 0.7, 1.0, 1.3} with top-k=10 and top-p=0.95, once with thinking off and once with thinking on (thinking capped at 2,048 tokens). Three seed conditions added an entropy seed (`seed=d32qxk4nt43`), a word seed (`seed=(horse chair roof love)`) or a semantic seed, a paragraph that implies without naming a search from both ends on the grid task and a relaxation over all edges on the shortest path task. Four instructions followed, which we call the creativity instruction (`be creative`), the new algorithm instruction (`make a new algorithm`), the novelty instruction (`make a fully novel algorithm never seen before`) and, as in Section 1.8, the enumeration prompt (`list 10 approaches, then implement one`). In the generate then select arm the model listed ten approaches and an external random draw picked the one it had to implement. For the read position analyses, forced implementations of every catalogue algorithm (20 framings each) defined the mode subspace, and three further conditions were encoded without generation: a fresh entropy seed and a fresh word seed (a different random string or word list for each paraphrase) and a neutral sentence of matched length. OpenRouter spend was USD 0.11. The labeller failed its strict gate on both tasks (Table 2), so every number here is descriptive.

**The BFS fraction does not depend on temperature or sampler.** Table 27 answers the request's BFS question. With thinking off, 797 of 800 grid programs across the eight temperature and sampler cells were BFS and every cell was at least 0.99 BFS; with thinking on, 800 of 800 were. On the shortest path task 797 of 800 were Dijkstra with thinking off and 800 of 800 with thinking on. A chart of these shares would be a flat line at 1.0, so the table stands alone.

**Table 27.** Share of programs that are BFS (grid task) or Dijkstra (shortest path task) across the temperature grid (N=100 per cell; all other labels listed; pass = share passing the hidden tests).

| Task | Thinking | Sampler | T=0.3 | T=0.7 | T=1.0 | T=1.3 |
|-|-|-|-|-|-|-|
| Grid | off | top-k=10 | BFS 100 (pass 1.00) | BFS 99, DFS 1 (0.98) | BFS 100 (0.98) | BFS 99, DFS 1 (0.95) |
| Grid | off | top-p=0.95 | BFS 100 (1.00) | BFS 100 (1.00) | BFS 100 (1.00) | BFS 99, DFS 1 (0.97) |
| Grid | on | top-k=10 | BFS 100 (1.00) | BFS 100 (1.00) | BFS 100 (0.98) | BFS 100 (1.00) |
| Grid | on | top-p=0.95 | BFS 100 (1.00) | BFS 100 (1.00) | BFS 100 (0.99) | BFS 100 (1.00) |
| Shortest path | off | top-k=10 | Dijkstra 100 (1.00) | Dijkstra 100 (0.99) | Dijkstra 99, Bellman-Ford/SPFA 1 (0.98) | Dijkstra 99, Bellman-Ford/SPFA 1 (1.00) |
| Shortest path | off | top-p=0.95 | Dijkstra 100 (1.00) | Dijkstra 100 (1.00) | Dijkstra 100 (0.97) | Dijkstra 99, Bellman-Ford/SPFA 1 (0.99) |
| Shortest path | on | top-k=10 | Dijkstra 100 (1.00) | Dijkstra 100 (1.00) | Dijkstra 100 (1.00) | Dijkstra 100 (1.00) |
| Shortest path | on | top-p=0.95 | Dijkstra 100 (1.00) | Dijkstra 100 (1.00) | Dijkstra 100 (1.00) | Dijkstra 100 (1.00) |

The no cue baseline at T=1.0 without top-k or top-p gave BFS 99 and unit weight Dijkstra 1 (pass 0.97) and Dijkstra 100 (pass 0.99).

**Ideas and phrasings.** We count ideas as distinct runtime labelled algorithms among correct programs. A *phrasing cluster* is a connected component, within one algorithm, of programs whose identifier normalised AST 4-gram shingle sets have Jaccard similarity at or above a threshold theta. Identifiers are renamed in order of appearance, and comments, docstrings and constants are dropped. Theta 0.8 is primary, 0.7 and 0.9 are sensitivity values, and complete linkage is a robustness check. The *phrasings per idea* is the rarefied number of phrasing clusters divided by the rarefied number of ideas at a depth of 25 programs. Table 28 gives the full ideas by phrasings table, which answers the request's question 1a-c. At the tightest setting (T=0.3, top-k=10, thinking off) the model wrote one idea in 4 phrasing clusters on the grid task and 1 on the shortest path task. Loosening temperature multiplied phrasings and left ideas at one or two: on the grid task the clusters at theta 0.8 rose from 4 to 36 (top-k) and from 3 to 24 (top-p) between T=0.3 and T=1.3. Output with thinking on was more varied in wording at every temperature (26 clusters at T=0.3 with top-k) but never in algorithm. The shortest path programs are shorter and more uniform (one to six clusters with thinking off). Figure 3 plots the clusters at theta 0.8 against temperature.

**Table 28.** Ideas by phrasings (correct programs only). Phrasing clusters at theta 0.7 / 0.8 / 0.9 with single linkage, at 0.8 with complete linkage, and phrasings per idea at theta 0.8.

| Task | Thinking | Sampler | T | Correct | Ideas | Clusters 0.7 / 0.8 / 0.9 | Complete linkage 0.8 | Phrasings per idea |
|-|-|-|-|-|-|-|-|-|
| Grid | off | none (baseline) | 1.0 | 97 | 2 | 15 / 21 / 32 | 29 | 7.48 |
| Grid | off | top-k=10 | 0.3 | 100 | 1 | 4 / 4 / 6 | 7 | 3.21 |
| Grid | off | top-k=10 | 0.7 | 98 | 1 | 11 / 13 / 17 | 18 | 6.20 |
| Grid | off | top-k=10 | 1.0 | 98 | 1 | 19 / 22 / 36 | 32 | 9.57 |
| Grid | off | top-k=10 | 1.3 | 95 | 2 | 31 / 36 / 54 | 50 | 10.96 |
| Grid | off | top-p=0.95 | 0.3 | 100 | 1 | 3 / 3 / 5 | 5 | 2.91 |
| Grid | off | top-p=0.95 | 0.7 | 100 | 1 | 7 / 8 / 10 | 12 | 4.73 |
| Grid | off | top-p=0.95 | 1.0 | 100 | 1 | 11 / 15 / 28 | 26 | 7.44 |
| Grid | off | top-p=0.95 | 1.3 | 97 | 1 | 21 / 24 / 41 | 36 | 9.58 |
| Grid | on | top-k=10 | 0.3 | 100 | 1 | 18 / 26 / 41 | 36 | 11.69 |
| Grid | on | top-k=10 | 0.7 | 100 | 1 | 24 / 36 / 57 | 48 | 14.36 |
| Grid | on | top-k=10 | 1.0 | 98 | 1 | 36 / 49 / 67 | 60 | 16.43 |
| Grid | on | top-k=10 | 1.3 | 100 | 1 | 39 / 55 / 73 | 68 | 17.60 |
| Grid | on | top-p=0.95 | 0.3 | 100 | 1 | 25 / 31 / 46 | 41 | 12.32 |
| Grid | on | top-p=0.95 | 0.7 | 100 | 1 | 29 / 41 / 57 | 51 | 15.21 |
| Grid | on | top-p=0.95 | 1.0 | 99 | 1 | 26 / 35 / 56 | 47 | 13.51 |
| Grid | on | top-p=0.95 | 1.3 | 100 | 1 | 41 / 53 / 78 | 66 | 17.65 |
| Shortest path | off | none (baseline) | 1.0 | 99 | 1 | 3 / 3 / 17 | 10 | 2.24 |
| Shortest path | off | top-k=10 | 0.3 | 100 | 1 | 1 / 1 / 3 | 2 | 1.00 |
| Shortest path | off | top-k=10 | 0.7 | 99 | 1 | 2 / 2 / 7 | 5 | 1.59 |
| Shortest path | off | top-k=10 | 1.0 | 98 | 2 | 3 / 3 / 14 | 10 | 1.62 |
| Shortest path | off | top-k=10 | 1.3 | 100 | 2 | 5 / 6 / 15 | 11 | 2.26 |
| Shortest path | off | top-p=0.95 | 0.3 | 100 | 1 | 2 / 2 / 3 | 2 | 1.25 |
| Shortest path | off | top-p=0.95 | 0.7 | 100 | 1 | 3 / 3 / 7 | 4 | 1.69 |
| Shortest path | off | top-p=0.95 | 1.0 | 97 | 1 | 2 / 2 / 9 | 5 | 1.70 |
| Shortest path | off | top-p=0.95 | 1.3 | 99 | 1 | 3 / 3 / 9 | 6 | 1.84 |
| Shortest path | on | top-k=10 | 0.3 | 100 | 1 | 2 / 3 / 18 | 14 | 2.25 |
| Shortest path | on | top-k=10 | 0.7 | 100 | 1 | 3 / 4 / 17 | 11 | 2.69 |
| Shortest path | on | top-k=10 | 1.0 | 100 | 1 | 4 / 7 / 24 | 19 | 3.25 |
| Shortest path | on | top-k=10 | 1.3 | 100 | 1 | 10 / 12 / 32 | 26 | 5.46 |
| Shortest path | on | top-p=0.95 | 0.3 | 100 | 1 | 3 / 3 / 13 | 9 | 2.25 |
| Shortest path | on | top-p=0.95 | 0.7 | 100 | 1 | 2 / 4 / 16 | 12 | 2.50 |
| Shortest path | on | top-p=0.95 | 1.0 | 100 | 1 | 2 / 3 / 16 | 13 | 2.25 |
| Shortest path | on | top-p=0.95 | 1.3 | 100 | 1 | 3 / 4 / 20 | 15 | 3.02 |

[FIGURE:fig_phrasings]

Table 29 gives the bootstrap slopes of log phrasings per idea in temperature. The slope was positive with a 95% interval above zero in six of eight task-sampler-thinking combinations at theta 0.8; the two exceptions were the shortest path task with top-p, thinking off (0.365, interval -0.077 to 0.759) and thinking on (0.232, interval -0.0 to 0.484). The slope of log ideas was zero everywhere except the thinking off top-k cells (0.203 on the grid task, 0.266 on the shortest path task), where single non-modal programs appeared at the highest temperatures. The preregistered criterion (positive slope at every theta and sampler, with the paired interval above zero) held on the grid task and failed on the shortest path task.

**Table 29.** Slope of log phrasings per idea against temperature (per unit T; 1,000 bootstrap draws; single linkage) at theta 0.7, 0.8 and 0.9, with 95% intervals, and the slope of log ideas (identical at every theta).

| Task | Sampler | Thinking | Theta 0.7 | Theta 0.8 | Theta 0.9 | Slope, ideas |
|-|-|-|-|-|-|-|
| Grid | top-k=10 | off | 1.138 [0.808, 1.409] | 1.265 [0.902, 1.547] | 1.440 [0.990, 1.727] | 0.203 [0.0, 0.41] |
| Grid | top-p=0.95 | off | 1.083 [0.835, 1.253] | 1.223 [0.975, 1.368] | 1.435 [1.182, 1.620] | 0.0 |
| Grid | top-k=10 | on | 0.563 [0.282, 0.784] | 0.417 [0.213, 0.567] | 0.233 [0.072, 0.321] | 0.0 |
| Grid | top-p=0.95 | on | 0.289 [0.113, 0.602] | 0.293 [0.134, 0.486] | 0.247 [0.123, 0.351] | 0.0 |
| Shortest path | top-k=10 | off | 0.693 [0.442, 1.001] | 0.758 [0.453, 1.044] | 1.295 [0.916, 1.849] | 0.266 [0.0, 0.486] |
| Shortest path | top-p=0.95 | off | 0.365 [-0.102, 0.757] | 0.365 [-0.077, 0.759] | 1.101 [0.780, 1.475] | 0.0 |
| Shortest path | top-k=10 | on | 0.752 [0.449, 0.956] | 0.846 [0.520, 1.075] | 0.408 [0.213, 0.567] | 0.0 |
| Shortest path | top-p=0.95 | on | -0.011 [-0.245, 0.222] | 0.232 [-0.0, 0.484] | 0.205 [0.017, 0.355] | 0.0 |

**Thinking traces do not explore.** Every thinking on trace hit the 2,048-token cap, so no trace completed. In the 800 grid traces the first approach named was BFS in all but one, and DFS was mentioned as a second option in 67-90% of traces depending on the cell; the implemented algorithm equalled the first approach named in 99-100% of traces. In the shortest path traces the first approach was Dijkstra in 98-100% and Bellman-Ford/SPFA was mentioned in 1-5% (Table 30). The plan-statement lexicon used to read the traces had precision 0.62 and recall 0.482 against a judge on 30 traces, so these counts are approximate.

**Table 30.** Approaches named in thinking traces (N=100 per cell; all traces truncated at 2,048 tokens).

| Task | Sampler | T | First approach named | Also considered | Mean approaches considered | First equals implemented |
|-|-|-|-|-|-|-|
| Grid | top-k=10 | 0.3 | BFS 100 | DFS 67 | 1.67 | 1.00 |
| Grid | top-k=10 | 0.7 | BFS 100 | DFS 78 | 1.78 | 1.00 |
| Grid | top-k=10 | 1.0 | BFS 100 | DFS 84, A* 1 | 1.85 | 1.00 |
| Grid | top-k=10 | 1.3 | BFS 99, DFS 1 | DFS 90 | 1.90 | 0.99 |
| Grid | top-p=0.95 | 0.3 | BFS 100 | DFS 70 | 1.70 | 1.00 |
| Grid | top-p=0.95 | 0.7 | BFS 100 | DFS 77 | 1.77 | 1.00 |
| Grid | top-p=0.95 | 1.0 | BFS 100 | DFS 84 | 1.84 | 1.00 |
| Grid | top-p=0.95 | 1.3 | BFS 100 | DFS 85, A* 1 | 1.86 | 1.00 |
| Shortest path | top-k=10 | 0.3 | Dijkstra 100 | Bellman-Ford/SPFA 2 | 1.02 | 1.00 |
| Shortest path | top-k=10 | 0.7 | Dijkstra 100 | Bellman-Ford/SPFA 2 | 1.02 | 1.00 |
| Shortest path | top-k=10 | 1.0 | Dijkstra 100 | Bellman-Ford/SPFA 3 | 1.03 | 1.00 |
| Shortest path | top-k=10 | 1.3 | Dijkstra 98, Bellman-Ford/SPFA 2 | Bellman-Ford/SPFA 4 | 1.04 | 0.98 |
| Shortest path | top-p=0.95 | 0.3 | Dijkstra 100 | Bellman-Ford/SPFA 1 | 1.01 | 1.00 |
| Shortest path | top-p=0.95 | 0.7 | Dijkstra 100 | Bellman-Ford/SPFA 3 | 1.03 | 1.00 |
| Shortest path | top-p=0.95 | 1.0 | Dijkstra 100 | Bellman-Ford/SPFA 4, Floyd-Warshall 1 | 1.05 | 1.00 |
| Shortest path | top-p=0.95 | 1.3 | Dijkstra 100 | Bellman-Ford/SPFA 3 | 1.03 | 1.00 |

**Seeds and instructions.** Random seeds did nothing to the output (Table 31): the entropy and word seeds shifted the modal share by about 1 point on the grid task and 0 on the shortest path task, with 90% intervals inside the preregistered 15-point equivalence bound. The semantic seed moved the shortest path task by 66.3 points toward Bellman-Ford/SPFA among correct programs (61 of 92 correct programs, while the Dijkstra share fell by 67.39 points; permutation p < 0.001; corrected in iteration 2 from 67 points, which is the fall in the Dijkstra share) and the grid task by 2.2 points toward bidirectional BFS (2 of 93 correct programs; permutation p = 0.078 for the shift toward the implied algorithm). Among the instructions, the creativity instruction did nothing and the new algorithm instruction moved 1-4 points. The novelty instruction moved 3.7 points on the grid task and 14.6 points on the shortest path task, toward Bellman-Ford/SPFA. The enumeration prompt moved 10.7 points on the shortest path task at a 24-point pass-rate cost.

**Table 31.** Seeds and instructions (N=100 each; labels of correct programs; shift of the default's share against the baseline, with 90% interval; cluster permutation p).

| Task | Condition | Pass | Labels of correct programs | Default share shift (points) [90%] | p |
|-|-|-|-|-|-|
| Grid | baseline (reference) | 0.97 | BFS 96, unit weight Dijkstra 1 | n/a | n/a |
| Grid | entropy seed | 1.00 | BFS 100 | +1.03 [0.0, 4.08] | 0.086 |
| Grid | word seed | 1.00 | BFS 100 | +1.03 [0.0, 4.04] | 0.096 |
| Grid | semantic seed | 0.93 | BFS 91, bidirectional BFS 2 | -1.12 [-5.47, 3.03] | 0.402 |
| Grid | creativity instruction | 1.00 | BFS 100 | +1.03 [0.0, 4.04] | 0.085 |
| Grid | new algorithm instruction | 0.94 | BFS 92, DFS 2 | -1.10 [-5.26, 3.0] | 0.329 |
| Grid | novelty instruction | 0.85 | BFS 81, unit weight Dijkstra 2, DFS 1, A* 1 | -3.68 [-9.19, 0.98] | 0.031 |
| Grid | enumeration prompt | 0.99 | BFS 99 | +1.03 [0.0, 4.0] | 0.246 |
| Shortest path | baseline (reference) | 0.99 | Dijkstra 99 | n/a | n/a |
| Shortest path | entropy seed | 1.00 | Dijkstra 100 | 0.0 [0.0, 0.0] | 1.0 |
| Shortest path | word seed | 1.00 | Dijkstra 100 | 0.0 [0.0, 0.0] | 1.0 |
| Shortest path | semantic seed | 0.92 | Bellman-Ford/SPFA 61, Dijkstra 30, Floyd-Warshall 1 | -67.39 [-87.18, -46.39] | <0.001 |
| Shortest path | creativity instruction | 0.99 | Dijkstra 99 | 0.0 [0.0, 0.0] | 1.0 |
| Shortest path | new algorithm instruction | 0.94 | Dijkstra 90, Bellman-Ford/SPFA 4 | -4.26 [-9.47, 0.0] | 0.012 |
| Shortest path | novelty instruction | 0.96 | Dijkstra 82, Bellman-Ford/SPFA 14 | -14.58 [-25.26, -5.44] | 0.001 |
| Shortest path | enumeration prompt | 0.75 | Dijkstra 67, Bellman-Ford/SPFA 8 | -10.67 [-20.38, -3.57] | 0.001 |

The generate then select arm was the only one to reach several algorithms. On the grid task its correct programs were BFS 26, A* 14, unit weight Dijkstra 9 and DFS 6 (Hill_cc 3.457) at a pass rate of 0.55; on the shortest path task Bellman-Ford/SPFA 31, Dijkstra 29 and Floyd-Warshall 15 (Hill_cc 2.87) at 0.75. The rarefied number of ideas at depth 25 was 3.977 and 2.999, against 1.258 and 1.0 for the baseline. Every one of the 100 stage-1 lists named all six grid algorithms, so the model knows the repertoire it does not use.

**Seeds at the read position.** The subspace test asks whether a condition moves the read position state along the mode subspace (the span of the forced implementation centroids, dimension 5 on the grid task and 4 on the shortest path task) more than switching between baseline paraphrases does. The statistic is the ratio of the median displacement under the condition to the median paraphrase displacement (Table 32, Figure 4). The entropy seed stayed within the paraphrase noise (0.734 and 1.165). *(Correction, iteration 2: on the shortest path task its 90% interval reaches 1.596, above the 1.5 equivalence bound, so equivalence with paraphrase noise was not shown there.)* The word seed moved the grid state 1.555 times the noise (90% interval 1.309 to 1.85), above the preregistered 1.5 bound, although a fresh word seed with a different word list per paraphrase moved it only 1.055 times and a neutral sentence of the same length 0.812 times. The semantic seed moved the state 3.4 and 3.7 times the noise, and on the grid task its displacement pointed toward the implied centroid (cosine 0.493) while the output did not follow. *(Added in iteration 2: the other half of the same result was omitted. On the shortest path task the semantic seed's displacement did not point toward the Bellman-Ford/SPFA centroid (cosine -0.087), yet the output moved 66.3 points toward it, and the fixed word seed moved the grid probe's decoded distribution 0.88 toward A* with no behavioural change. Displacement along the mode subspace predicted behavioural movement in neither direction; Section 2.3.8.)* The instructions that changed behaviour also moved the state: the novelty instruction 1.809 and 3.063, the enumeration prompt 2.757 and 2.959. A probe from the read position to the label distribution did not beat its shuffled label null on the shortest path task (mean JS 0.122 against a 5th percentile of 0.121), so the mode subspace there rests on forced prompts that the natural output never visits.

**Table 32.** Subspace test: median displacement along the mode subspace relative to the paraphrase null, with 90% interval (grid task at layer 27, subspace dimension 5; shortest path task at layer 22, dimension 4). Conditions marked * were encoded without generation.

| Condition | Grid ratio [90%] | Shortest path ratio [90%] |
|-|-|-|
| entropy seed | 0.734 [0.579, 0.875] | 1.165 [1.0, 1.596] |
| word seed | 1.555 [1.309, 1.85] | 1.012 [0.865, 1.401] |
| fresh entropy seed* | 0.664 [0.53, 0.825] | 0.968 [0.796, 1.365] |
| fresh word seed* | 1.055 [0.842, 1.314] | 0.927 [0.756, 1.252] |
| neutral sentence* | 0.812 [0.561, 1.073] | 1.288 [1.002, 1.932] |
| semantic seed | 3.417 [2.876, 4.211] | 3.70 [3.005, 4.951] |
| creativity instruction | 1.041 [0.846, 1.436] | 1.684 [1.304, 2.35] |
| new algorithm instruction | 1.302 [0.979, 1.637] | 1.017 [0.79, 1.963] |
| novelty instruction | 1.809 [1.509, 2.173] | 3.063 [2.523, 4.158] |
| enumeration prompt | 2.757 [2.251, 3.435] | 2.959 [2.382, 4.016] |

[FIGURE:fig_subspace]

The same ratios four layers before and after the analysis layer keep the ordering (Table 32b). The semantic seed and the enumeration prompt stay at two to four times the noise and the random seeds stay near 1. The exception is the shortest path task at layer 18, where the neutral sentence (1.812) and the entropy seed (1.484) also exceed 1.4.

**Table 32b.** Subspace test ratios at layers four before and four after the analysis layer (90% intervals).

| Condition | Grid layer 23 | Grid layer 31 | Shortest path layer 18 | Shortest path layer 26 |
|-|-|-|-|-|
| entropy seed | 0.846 [0.771, 1.023] | 0.777 [0.648, 0.962] | 1.484 [1.153, 1.953] | 0.953 [0.707, 1.411] |
| word seed | 1.921 [1.665, 2.170] | 1.504 [1.311, 1.897] | 1.331 [1.031, 1.786] | 1.072 [0.793, 1.508] |
| fresh entropy seed* | 0.883 [0.708, 1.079] | 0.737 [0.634, 0.942] | 1.278 [1.053, 1.687] | 0.791 [0.604, 1.187] |
| fresh word seed* | 1.294 [1.082, 1.632] | 1.067 [0.918, 1.434] | 1.238 [0.903, 1.581] | 0.871 [0.655, 1.343] |
| neutral sentence* | 0.777 [0.607, 1.044] | 0.879 [0.577, 1.203] | 1.812 [1.238, 2.674] | 0.901 [0.667, 1.348] |
| semantic seed | 3.806 [3.314, 4.437] | 3.237 [2.809, 4.270] | 3.427 [2.801, 4.364] | 4.009 [3.166, 5.873] |
| creativity instruction | 1.525 [1.301, 1.822] | 1.048 [0.894, 1.607] | 2.128 [1.672, 2.813] | 1.093 [0.843, 1.721] |
| new algorithm instruction | 1.611 [1.259, 2.062] | 1.220 [0.900, 1.687] | 1.770 [1.349, 2.274] | 0.848 [0.672, 1.698] |
| novelty instruction | 2.717 [2.234, 3.159] | 1.838 [1.590, 2.363] | 3.410 [2.647, 4.329] | 2.291 [1.675, 3.270] |
| enumeration prompt | 3.242 [2.827, 3.858] | 2.614 [2.303, 3.308] | 4.257 [3.537, 5.363] | 2.005 [1.541, 3.101] |

**Where temperature acts in the trajectory.** Over the first 64 generated tokens, the variance of the residual-stream states rose with temperature almost entirely outside the mode subspace (Table 33). On the grid task the complement variance rose from 36,267 to 46,308 between T=0.3 and T=1.3 while the share in the mode subspace estimated from generated tokens stayed at 0.061-0.062. The preregistered prediction was a nonpositive slope of the share in excess of a null matched to the data; the slope was slightly positive (0.006 and 0.015 per unit T, intervals above zero), so the prediction failed, although the excess itself stayed negative at every temperature on both tasks. In the mode subspace estimated at the read position the share was 0.004 (grid) and 0.003 (shortest path) at every temperature, and a subspace from naturally sampled programs could not be estimated because 399 of 400 programs per task were the default.

**Table 33.** Variance of trajectory states (first 64 generated tokens) inside the mode subspace estimated from generated tokens, per temperature (N=50 per cell).

| Task (layer) | T | Share in mode subspace | Excess over null matched to the data | Mode subspace variance | Complement variance |
|-|-|-|-|-|-|
| Grid (27) | 0.3 | 0.062 | -0.023 | 2,733 | 36,267 |
| Grid (27) | 0.7 | 0.062 | -0.022 | 2,970 | 39,928 |
| Grid (27) | 1.0 | 0.061 | -0.020 | 3,334 | 46,586 |
| Grid (27) | 1.3 | 0.062 | -0.016 | 3,375 | 46,308 |
| Shortest path (22) | 0.3 | 0.018 | -0.050 | 9 | 422 |
| Shortest path (22) | 0.7 | 0.035 | -0.032 | 113 | 2,808 |
| Shortest path (22) | 1.0 | 0.041 | -0.025 | 194 | 4,206 |
| Shortest path (22) | 1.3 | 0.030 | -0.037 | 205 | 5,825 |

**The forecast record.** Eight predictions were committed before generation; six hit. The two misses were the predictions that random seeds stay within 1.5 times the paraphrase null at the read position (the grid word seed exceeded it) and that the excess mode subspace share has a nonpositive slope in temperature. The preregistered verdict was MIXED.

**What this experiment settled.** Temperature and the sampler are phrasing knobs on these tasks: they never changed the algorithm from 0.3 to 1.3, with or without thinking, while the number of distinct phrasings rose severalfold. Random seeds do not change the output, and apart from the fixed grid word seed their effect on the read position state is at most that of an arbitrary sentence. Context with meaning does move the algorithm, but not reliably: the same semantic seed moved the shortest path task by 66.3 points and the grid task by 2.2 (among correct programs; corrected in iteration 2 from 67 and 2). Explicit novelty instructions move little, and generate then select reaches three to four algorithms at a 24-42-point pass-rate cost.

## 1.11 Comparisons across the six experiments

The strategy deferred the scorecard that combines all experiments to an evaluation artifact in the next iteration. The comparisons below were compiled for this report from each experiment's per-sample rows and result files; the replication table was recomputed with `work/replication.py` in this workspace.

**The same ban, five draws.** Five experiments ran the same modal ban under the shared protocol [ARTIFACT:art__skdlFp_o3e9] [ARTIFACT:art_D6Z0Snf09sFL] [ARTIFACT:art_1yV2vQ0EH4OY] [ARTIFACT:art_U5UKkFrOgSsE] [ARTIFACT:art_HF8nK8B_Lqyy], each with its own ten paraphrases of `Do not use X`, its own test suite and, in one case, its own engine. Where the ban had compliant samples, they landed on Bellman-Ford/SPFA on the shortest path task in all five draws (272 of 272 compliant programs), and on DFS on the grid task in four of five draws; in the geometry draw, sampled with HF `generate` and with the highest banned share (0.62), the 18 compliant programs split into DFS 10 and unit weight Dijkstra 8, with no clear mode (Table 34). *(Corrected in iteration 2; this sentence previously said that the compliant samples landed on the same substitute every time, DFS on the grid task with a few unit weight Dijkstra programs, which Tables 13 and 34 contradict. Section 2.3.3 gives the per draw counts.)* How often the ban was obeyed did not replicate. The banned mode share ranged from 0.10 to 0.62 on the grid task and from 0.09 to 0.72 on the shortest path task. Within each experiment it depended on the wording: on the grid task the banned counts per paraphrase ranged from 0 of 10 to 9 or 10 of 10 in four of the five experiments (Figure 5). The association experiment's paraphrases were the most effective (eight of ten grid wordings gave 0 of 10 BFS), which is why its compliance looked high. Constraints that oppose a model's default pattern are known to fail at rates between 10% and 100% [38]; here the spread occurs within one model, one task and one ban. Compliance is therefore a property of the ban sentence at least as much as of the banned algorithm, and any analysis that relates ban failure to properties of the algorithm (the ladder limit test) has to hold the wording fixed or model it.

**Table 34.** The modal ban across experiments (N=100 each; recomputed from per-sample rows; compliant = correct and not the banned algorithm).

| Experiment (engine) | Grid ban BFS: labels | Banned share | Compliant (labels) | Shortest path ban Dijkstra: labels | Banned share | Compliant (labels) |
|-|-|-|-|-|-|-|
| Association (vLLM) | DFS 90, BFS 10 | 0.10 | 38 (DFS 38) | Bellman-Ford/SPFA 90, Dijkstra 9, other 1 | 0.09 | 86 (Bellman-Ford/SPFA 86) |
| Geometry (HF) | BFS 62, DFS 29, unit weight Dijkstra 9 | 0.62 | 18 (DFS 10, unit weight Dijkstra 8) | Dijkstra 72, Bellman-Ford/SPFA 27, other 1 | 0.72 | 22 (Bellman-Ford/SPFA 22) |
| Forking token (vLLM) | DFS 78, BFS 21, unit weight Dijkstra 1 | 0.21 | 41 (DFS 40, unit weight Dijkstra 1) | Bellman-Ford/SPFA 80, Dijkstra 20 | 0.20 | 80 (Bellman-Ford/SPFA 80) |
| Decommitment (vLLM) | BFS 49, DFS 48, unit weight Dijkstra 2, other 1 | 0.49 | 18 (DFS 16, unit weight Dijkstra 2) | Dijkstra 54, Bellman-Ford/SPFA 40, other 6 | 0.54 | 38 (Bellman-Ford/SPFA 38) |
| Instruction tuning (vLLM) | BFS 62, DFS 36, unit weight Dijkstra 2 | 0.62 | 13 (DFS 12, unit weight Dijkstra 1) | Dijkstra 54, Bellman-Ford/SPFA 46 | 0.54 | 46 (Bellman-Ford/SPFA 46) |
| Pooled, five draws (row added in iteration 2) | n/a | 0.41 | 128 (DFS 116, unit weight Dijkstra 12); DFS share 0.906, Wilson [0.843, 0.946] | n/a | 0.42 | 272 (Bellman-Ford/SPFA 272); share 1.0, Wilson [0.986, 1.000] |

[FIGURE:fig_replication]

**Two elicitations of the same association map disagree.** The association [ARTIFACT:art__skdlFp_o3e9] and geometry [ARTIFACT:art_D6Z0Snf09sFL] experiments asked the same model the same question with different prompt wordings and got different maps (Table 35). For BFS one map put unit weight Dijkstra first with clarity 0.20 and the other put A* first with clarity 0.80; for Dijkstra one put Bellman-Ford/SPFA first with clarity 1.0 and the other put Dial first with clarity 0.579. The realised substitutes (DFS, Bellman-Ford/SPFA) were ranked last for BFS and third for Dijkstra in the second map. The ranking instrument is not stable under rewording, and where its two versions disagree, neither matches the free-form answer the model gives when asked directly.

**Table 35.** The association map of the two default algorithms in the two experiments that elicited it (20 sampled rankings each; 19 for Dijkstra in the geometry experiment).

| X | Elicitation | Borda shares of the alternatives | Winner | Clarity | Kendall's W |
|-|-|-|-|-|-|
| BFS | association experiment | unit weight Dijkstra 0.293, bidirectional BFS 0.283, A* 0.263, IDDFS 0.107, DFS 0.054 | unit weight Dijkstra | 0.20 | 0.52 |
| BFS | geometry experiment | A* 0.371, unit weight Dijkstra 0.288, bidirectional BFS 0.229, IDDFS 0.107, DFS 0.005 | A* | 0.80 | 0.886 |
| Dijkstra | association experiment | Bellman-Ford/SPFA 0.492, Floyd-Warshall 0.226, bidirectional Dijkstra 0.153, Dial 0.129 | Bellman-Ford/SPFA | 1.0 | 0.639 |
| Dijkstra | geometry experiment | Dial 0.424, bidirectional Dijkstra 0.314, Bellman-Ford/SPFA 0.212, Floyd-Warshall 0.051 | Dial | 0.579 | 0.581 |

**The PREDICT column.** Every forecasting family was scored by the experiment that owned it, on that experiment's own draw of the two modal ban events, and all forecasts were committed before the samples (Table 36). The selection rule needs at least three events on which the families' top-1 nominations disagree; the screen produced two shared events (the step-2 events had too few compliant samples or were exploratory), so the rule cannot name a survivor. *(Correction, iteration 2: the rule also gates events on compliance of at least 50%. Under that gate the geometry, instruction tuning and decommitment shortest path events in Table 36 are excluded, the base model, decommitted and geodesic forecasts were scored only on excluded events, and the ranking that follows rests largely on them. On gated events no family can advance; Section 2.3.7.)* Descriptively, the highest scoring forecasts on both events were those that already put most of their mass on the realised substitute before the ban: the model's free-form answer, the listing control distribution, the base model's own distribution and, on the shortest path task, the decommitted distribution. All of them rank the realised substitute second in the preferences the model shows before any ban. The preregistered association map was the worst or second worst forecast in both experiments that elicited it on the grid event. The geodesic kernel beat uniform by 0.29 nats on the grid event and lost to the uniform forecast based on frequency on the shortest path event.

**Table 36.** PREDICT column: raw log score of every committed forecast on the modal ban events (each experiment scored on its own samples; higher is better; uniform over survivors is -1.630 on the grid task and -1.406 on the shortest path task under the shared mix and floor). The geometry experiment scored every sample not labelled as the banned algorithm rather than only compliant ones.

| Forecast family (experiment) | Grid ban BFS | Shortest path ban Dijkstra |
|-|-|-|
| Association map, Borda (association) | -2.817 | -0.755 |
| Association map, first rank (association) | -2.474 | -0.190 |
| External association map, Llama-3.1-8B (association) | -1.412 | -0.928 |
| Free-form answer about the standard alternative (association, not preregistered as a contest predictor) | -0.112 | -0.058 |
| Listing control distribution (association, not preregistered as a contest predictor) | -0.061 | -0.058 |
| Latent frequency, uniform under collapse (association) | -1.630 | -1.406 |
| Association map, Borda (geometry) | -3.543 | -1.647 |
| Geodesic kernel (geometry) | -1.337 | -1.530 |
| Read position decoder (geometry) | -1.287 | -1.587 |
| Latent frequency (geometry) | -1.630 | -1.496 |
| Decommitted survivor distribution (decommitment) | -1.630, degenerate | -0.058 |
| vLLM frequency forecast (decommitment) | -1.630 | -0.219 |
| Base model, plain completion, all samples (instruction tuning, primary) | -0.470 | -0.220 |
| Base model, chat template, correct samples (instruction tuning) | -0.412 | -0.058 |
| Instruct model, chat template, correct samples (instruction tuning) | -1.630 | -0.058 |

**The BUY column.** The rule asks for the highest correctness conditioned Hill number at the strongest setting that keeps at least 80% of the baseline pass rate. Table 37 lists every knob that reached that pass-rate floor with a Hill gain, and the main ones that did not; Figure 6 plots the shortest path knobs as Hill gain against pass-rate points lost. On the grid task the cumulative ban of BFS and DFS kept 88% of its reference pass rate in the decommitment draw and produced 16 compliant programs over two algorithms (unit weight Dijkstra 13, A* 3), but it does not replicate: the geometry draw (pass 0.96 against 0.99) put all 18 of its compliant programs on unit weight Dijkstra, and the association draw (pass 0.53 against 0.933) left 5 compliant programs; the novelty instruction raised Hill_cc to 1.27. *(Corrected in iteration 2; this sentence previously said that no knob keeping 80% of the pass rate produced a second algorithm among compliant programs and that the gain of the cumulative ban came from programs that still used BFS, which the decommitment row of Table 37 contradicts. Section 2.3.4.)* On the shortest path task the prompt ban and the semantic seed reached about 2 effective algorithms at no or small pass cost, while the activation knobs (decommitment, a random direction) reached about +0.6 at 17 points. By the rule's 0.5 margin the prompt ban and the semantic seed tie, so both would advance. *(Correction, iteration 2: the BUY rule names a winner only on the pooled tasks and in direction on each task, and this comparison used the shortest path task alone, with Hill numbers from different statistics. Recomputed with one statistic, rarefied Hill-1 over compliant programs, no knob advances on either task, the prompt ban scores 1.0 on the shortest path task, and the positive target of a second correct algorithm at under 20 pass points is met on neither task; Section 2.3.6.)* The table also exposes a flaw in the metric: Hill_cc counts correct programs of the banned algorithm, so a ban that half fails scores as two algorithms. The prompt-ban rows on the shortest path task are Dijkstra mixed with Bellman-Ford/SPFA; only the semantic seed and generate then select produced diversity without a banned algorithm in the mix.

**Table 37.** BUY column: knobs on the two tasks, with pass rate relative to their own reference, and the Hill number or its change as each artifact reported it.

| Task | Knob (experiment) | Pass / reference pass | Reaches 80% floor | Hill_cc (or Delta Hill) | Correct program composition |
|-|-|-|-|-|-|
| Shortest path | prompt ban (instruction tuning) | 1.00 / 1.00 | yes | 1.99 | Dijkstra 54, Bellman-Ford/SPFA 46 |
| Shortest path | semantic seed (decoding) | 0.92 / 0.99 | yes | 1.988 | Bellman-Ford/SPFA 61, Dijkstra 30, Floyd-Warshall 1 |
| Shortest path | prompt ban (geometry) | 0.94 / 1.00 | yes | 1.723 | Dijkstra 72 correct banned plus Bellman-Ford/SPFA 22 |
| Shortest path | prompt ban (forking token) | 1.00 / 0.995 | yes | 1.649 | Bellman-Ford/SPFA 80, Dijkstra 20 |
| Shortest path | novelty instruction (decoding) | 0.96 / 0.99 | yes | 1.515 | Dijkstra 82, Bellman-Ford/SPFA 14 |
| Shortest path | prompt ban (association) | 0.95 / 1.00 | yes | 1.368 | Bellman-Ford/SPFA 86, Dijkstra 9 |
| Shortest path | prompt ban (decommitment) | 0.87 / 0.89 | yes | Delta +0.79 | Dijkstra 49, Bellman-Ford/SPFA 38 |
| Shortest path | decommitment direction, c=0.25 | 0.78 / 0.95 | yes (82%) | Delta +0.65 | Bellman-Ford/SPFA 54, Dijkstra 23, other 1 |
| Shortest path | random direction, c=0.25 (decommitment) | 0.79 / 0.95 | yes (83%) | Delta +0.59 | Dijkstra 53, Bellman-Ford/SPFA 26 |
| Shortest path | generate then select (decoding) | 0.75 / 0.99 | no (76%) | 2.87 | Bellman-Ford/SPFA 31, Dijkstra 29, Floyd-Warshall 15 |
| Shortest path | enumeration prompt (decoding) | 0.75 / 0.99 | no | 1.404 | Dijkstra 67, Bellman-Ford/SPFA 8 |
| Shortest path | temperature 1.0-1.3, top-k=10 (decoding) | 0.98-1.00 / 0.99 | yes | 1.058-1.059 | Dijkstra with one Bellman-Ford/SPFA |
| Shortest path | sharpening subtraction, any variant (instruction tuning) | 0.00-0.98 / 1.00 | only at layer 18, c of 0.5 or less | 1.00-1.10 | Dijkstra |
| Grid | cumulative ban of BFS and DFS (decommitment) | 0.88 / 1.00 | yes | Delta +1.27 | BFS 65, unit weight Dijkstra 13, DFS 7, A* 3 |
| Grid | novelty instruction (decoding) | 0.85 / 0.97 | yes | 1.27 | BFS 81, unit weight Dijkstra 2, DFS 1, A* 1 |
| Grid | prompt ban (geometry) | 0.76 / 0.99 | no (77%) | 2.034 | BFS 58 correct banned, DFS 10, unit weight Dijkstra 8 |
| Grid | prompt ban (instruction tuning) | 0.70 / 1.00 | no | 1.70 | BFS 57, DFS 12, unit weight Dijkstra 1 |
| Grid | prompt ban (association) | 0.46 / 0.933 | no | 1.587 | DFS 38, BFS 8 |
| Grid | generate then select (decoding) | 0.55 / 0.97 | no | 3.457 | BFS 26, A* 14, unit weight Dijkstra 9, DFS 6 |
| Grid | decommitment direction, any c | 0.98 at c=0.1 | yes at c=0.1 | 1.0 | BFS |
| Grid | temperature, any setting (decoding) | 0.95-1.00 | yes | 1.0-1.06 | BFS |

[FIGURE:fig_knobs]

**The locus diagnostic.** The test that would move the geometric analyses from the read position to generated tokens needed a probe at the forking token and commitment positions, and that probe produced no output. The read position evidence is split: it encodes the shortest path default and fails to decode the grid default, while the forking token screen found every baseline path fixed at the read position on both tasks. The diagnostic is undetermined.

## 1.12 What iteration 1 established, and what it abandoned

Everything below is descriptive: one model, two tasks, two informative ban events per experiment, and labellers of which two failed their strict gates.

**Established.**

1. The collapse is total and robust to decoding. Across six independent baselines, 1,199 of 1,200 grid programs were BFS and 1,174 of 1,200 shortest path programs were Dijkstra. Temperature from 0.3 to 1.3, top-k=10 or top-p=0.95, and thinking on or off changed the algorithm in at most 3 of 800 programs per task.
2. Temperature is a phrasing knob. At the tightest setting the model writes one idea in a handful of phrasings; loosening temperature multiplies phrasings (4 to 36 clusters on the grid task with top-k=10) and leaves ideas at one or two. This is the answer this run gives to the request's question 1a-c on these two tasks.
3. Random context seeds change nothing in the output. Apart from the fixed word seed on the grid task (1.56 times the paraphrase noise, against 1.06 for word seeds drawn fresh per paraphrase), they displace the read position state no more than an arbitrary sentence does. Context with meaning moves the state three to four times the paraphrase noise and can move the output, by 66.3 points on the shortest path task and by 2.2 points on the grid task (among correct programs). *(Corrected in iteration 2; the item previously gave 67 and 2 points, 67 being the fall in the Dijkstra share. It also omitted that read position displacement did not predict which algorithm the output moved to on either task: the grid semantic seed pointed at its implied algorithm and behaviour barely moved, the shortest path seed did not point at Bellman-Ford/SPFA and behaviour moved two thirds of the way; and the shortest path entropy seed's interval reaches 1.596, above the equivalence bound. Section 2.3.8.)*
4. When a prompt ban is obeyed, the compliant programs land mostly on one substitute. On the shortest path task it was Bellman-Ford/SPFA in five of five draws (272 of 272 compliant programs); on the grid task DFS was the realised mode in four of five draws (116 of 128 pooled, 0.906, Wilson [0.843, 0.946]), and the HF engine geometry draw, with the highest banned share (0.62), had no clear mode (DFS 10, unit weight Dijkstra 8). A single ban collapses the output again; a second step grid ban can spread compliant output over unit weight Dijkstra and A* (decommitment draw: 13 and 3) or put all of it on unit weight Dijkstra (geometry draw: 18). *(Corrected in iteration 2; the item previously said that the substitute replicated in five independent draws and that bans collapse the output again without spreading it, which the geometry draw and the second step bans contradict. Section 2.3.3.)* How often a ban is obeyed did not replicate (banned mode share 0.09-0.72) and depends on the wording of the ban sentence. Banning the substitute as well fails, and the model then reimplements the banned mechanism under another description.
5. The substitute is the model's second preference, visible before any ban in its free-form answer, in its output when every algorithm is listed, and in the base model's distribution. The preregistered ranked association map did not identify it on the grid task and gave different answers under two elicitation wordings. *(Note added in iteration 2: on the shortest path task random activation directions and every other perturbation that moved the model off Dijkstra also landed on Bellman-Ford/SPFA (Section 2.3.5), so there the second preference of the model cannot be told apart from wherever any perturbation lands.)*
6. The read position carries a low-dimensional map of the catalogue (intrinsic dimension 4-5 against 11-12 for shuffled nulls). On the grid task the mass displaced by bans moved to BFS's geodesic neighbours and never to the far side, which is consistent with geodesic proximity and with typicality, since those neighbours are also second choices of the model; the two are not separated on these events. *(Corrected in iteration 2: the geodesic order is unstable at layer 24 under paraphrase resampling, and on the shortest path task Floyd-Warshall, not the realised Bellman-Ford/SPFA, is the nearest survivor in every subsample. Section 2.3.2.)* The ban shift itself is almost entirely orthogonal to the algorithm directions, so the substitution versus subtraction share test was inconclusive for every algorithm.
7. No activation edit beat the prompt ban. Affine ablation of the modal algorithm did nothing at alpha up to 2 and broke generation at 4, as random directions did; the decommitment direction acted like a random direction; subtracting the instruct minus base direction destroyed generation.
8. Post training sharpened an ordering the base model already had, rather than installing a new attractor; the chat format sharpens it further on the shortest path task. *(Correction, iteration 2: this item replaced the preregistered verdicts with an interpretation. The verdicts are INSTALLED_BY_POST_TRAINING on the shortest path task and MIXED on the grid task under the correctness conditioned Hill number (INSTALLED_BY_POST_TRAINING on both under the Hill number over all programs), and MIXED on both at the planned sample size. The base ordering matches the instruct ordering only under the chat template, where the base model parsed 0.58 and 0.66 of samples and wrote 57 and 90 correct programs, labelled with runtime against AST kappa of 0.20 to 0.50 (Table 24b); in plain completion its shortest path mode is Bellman-Ford/SPFA, 16 of 25 correct programs.)*
9. Without a ban the algorithm is fixed at the read position on both tasks. Under a ban the outcome stays open for dozens of tokens, a few forking tokens exist on the shortest path task, and writing the first token that identifies the algorithm does not lock the algorithm in.

**Abandoned or failed, with the evidence.**

- *Affine directional ablation of the modal algorithm as a removal knob.* 0 of 50 samples moved at alpha 0.5, 1 and 2 on both tasks, with 78-90% of outputs byte-identical to the unedited run; at alpha 4 the edit removed all code. The direction checks had failed beforehand (AUC 0.79-0.89). The prompt-versus-removal comparison that the hypothesis treats as a headline was therefore untestable in this form.
- *Subtracting the instruct minus base direction.* 0 of 100 parseable programs at every band coefficient; the direction promotes format tokens under the logit lens.
- *Forking window temperature.* Every arm was 100% the default algorithm; its phrasing count matched T=0.3.
- *The decommitment direction as a diversity knob.* Its shortest path gain equalled a random direction's (difference +0.07, interval -0.26 to 0.39) and the grid task never moved; the enumeration prompt that states the same framing did nothing.
- *The ranked (Borda) association map as the association instrument.* It missed the grid event, ranked the realised substitute last, and changed its winner for both default algorithms under a second elicitation.
- *Baseline frequency as the typicality predictor.* Under a full collapse every survivor has zero frequency, so the forecast is uniform by construction and the discordance strata that the design defined by stability are empty.
- *The mention twin as a placebo, and the sham ban as a negative control.* Mentioning an algorithm recommends it (+56 to +100 points), so sham bans cannot be tested for equivalence with their mention twins.
- *The locus probes.* The forking token experiment extracted the states but its probe stage produced no output; this is a technical failure, not a negative result, and the measurement is still missing. *(Correction, iteration 2: the probe stage ran before the states were written (Section 1.7); the audit ran it in iteration 2 and found no decision locus among the saved positions, Section 2.3.1.)*
- *The reserved bench.* The dataset artifact delivered source data but no frozen specifications, tests, labellers or forecasts, so the planned out-of-sample confirmation cannot start until the bench is built.

**Spend.** OpenRouter: USD 0.27 (association), about 0.09 (geometry), 0.024 (forking token), 0.062 (decommitment), 0.21 (instruction tuning), 0.11 (decoding) and 0 (dataset), about USD 0.77 in total. GPU: about 6 minutes on an RTX 5090 (association), 2.2 hours on a 23 GB NVIDIA GPU (geometry), 2.1 hours on the same model of GPU (instruction tuning); the other experiments did not record GPU hours. *(Correction, iteration 2: from the union of each experiment's GPU phase log spans, an upper bound that includes waits, geometry 2.92, forking token 1.55, decommitment 3.23, instruction tuning 2.47 and decoding 3.31 GPU hours; Section 2.3.10. The answers this screen gives to the objections of the hypothesis review are recorded in Section 2.1.)*

# What we have learned so far

After one iteration the run has a clear behavioural picture on two path search tasks and no mechanism. Qwen3-8B writes BFS and Dijkstra almost without exception; sampling temperature, top-k, top-p, thinking mode and random seeds change how the code is worded but not which algorithm it implements. A prompt ban does not open the repertoire. When the model obeys it, it collapses again on one substitute (DFS, Bellman-Ford/SPFA), the same substitute in five independent draws, and a second ban fails by disguise. The substitute is the model's own second preference, legible before the ban from its free-form answer, from its output when all approaches are listed, and from the base model; the instrument the hypothesis chose to measure association, a ranking aggregated by Borda count, did not find it. Whether a ban is obeyed at all depends heavily on how it is worded.

Inside the model, the read position holds a low-dimensional map of the catalogue on which the grid ban's displaced mass went to the nearest neighbours of BFS, but the ban shift is almost orthogonal to the algorithm directions, and every activation edit tried so far either did nothing or broke the model. Post-training sharpened an existing ordering rather than creating it. The only arm that produced three or four correct algorithms was generate then select, at a large pass-rate cost.

The hypothesis's central quantitative claim is that promotion of an associated alternative is the larger share of the ban shift and is aimed where association predicts. It has not been tested in a way that could confirm or refute it. The share test was inconclusive, the forecast contest had two events and a degenerate typicality rival, and the activation removal comparison was untestable. The open questions for the next iteration follow from this. The contests need tasks whose baselines are not fully collapsed, so that the typicality predictor and the presence strata exist, and ban wording that is held fixed or modelled. The association measure has to agree with the model's free-form answer, and the diversity metric must not count a banned algorithm as a second idea. The locus probes are still missing, and so is the reserved bench that the dataset artifact did not build. Several items of the original request have not been run yet: sparse-autoencoder features, thought anchor resampling of reasoning traces, and the prohibition of the top five algorithms at once, which the succession could not reach because the model stopped complying after two bans.

# References

[1] Narula et al. The Invisible Lottery: How Subtle Cues Steer Algorithm Choice in LLM Code Generation. arXiv preprint arXiv:2606.04057. 2026.
[2] Wu et al. Generative Monoculture in Large Language Models. International Conference on Learning Representations. 2024.
[3] Jangra et al. DivAlgo: A systematic evaluation of algorithmic diversity for code generation models. 2026.
[4] Yoon et al. How Do LLMs Change Predictions Under Negation? 2026.
[5] Yang et al. Qwen3 Technical Report. 2025.
[6] Kwon et al. Efficient Memory Management for Large Language Model Serving with PagedAttention. Proceedings of the 29th Symposium on Operating Systems Principles. 2023.
[7] Rana. Semantic Gravity Wells: Why Negative Constraints Backfire. arXiv preprint arXiv:2601.08070. 2026.
[8] Wilson. Probable Inference, the Law of Succession, and Statistical Inference. Journal of the American Statistical Association. 1927.
[9] Hill. Diversity and Evenness: A Unifying Notation and Its Consequences. Ecology. 1973.
[10] Gneiting et al. Strictly Proper Scoring Rules, Prediction, and Estimation. Journal of the American Statistical Association. 2007.
[11] Cohen. A Coefficient of Agreement for Nominal Scales. Educational and Psychological Measurement. 1960.
[12] Xia et al. LeetCodeDataset: A Temporal Dataset for Robust Evaluation and Efficient Training of Code LLMs. arXiv preprint arXiv:2504.14655. 2025.
[13] Du et al. Mercury: A Code Efficiency Benchmark for Code Large Language Models. Advances in Neural Information Processing Systems 37. 2024.
[14] Markeeva et al. The CLRS-Text Algorithmic Reasoning Language Benchmark. arXiv preprint arXiv:2406.04229. 2024.
[15] Liu et al. Is Your Code Generated by ChatGPT Really Correct? Rigorous Evaluation of Large Language Models for Code Generation. Advances in Neural Information Processing Systems 36. 2023.
[16] Qiu et al. How Efficient is LLM-Generated Code? A Rigorous & High-Standard Benchmark. International Conference on Learning Representations. 2024.
[17] Brysbaert et al. Concreteness ratings for 40 thousand generally known English word lemmas. Behavior Research Methods. 2013.
[18] Brysbaert et al. Moving beyond Kučera and Francis: A critical evaluation of current word frequency norms and the introduction of a new and improved word frequency measure for American English. Behavior Research Methods. 2009.
[19] Xu et al. KodCode: A Diverse, Challenging, and Verifiable Synthetic Dataset for Coding. Annual Meeting of the Association for Computational Linguistics. 2025.
[20] Zhu et al. XLCoST: A Benchmark Dataset for Cross-lingual Code Intelligence. arXiv preprint arXiv:2206.08474. 2022.
[21] Kendall et al. The Problem of $m$ Rankings. The Annals of Mathematical Statistics. 1939.
[22] Grattafiori et al. The Llama 3 Herd of Models. 2024.
[23] Lu et al. Benchmarking Language Model Creativity: A Case Study on Code Generation. North American Chapter of the Association for Computational Linguistics. 2024.
[24] Hewitt et al. Designing and Interpreting Probes with Control Tasks. Proceedings of the 2019 Conference on Empirical Methods in Natural Language Processing and the 9th International Joint Conference on Natural Language Processing. 2019.
[25] Tenenbaum et al. A global geometric framework for nonlinear dimensionality reduction. Science. 2000.
[26] Facco et al. Estimating the intrinsic dimension of datasets by a minimal neighborhood information. Scientific Reports. 2017.
[27] Wurgaft et al. Manifold Steering Reveals the Shared Geometry of Neural Network Representation and Behavior. arXiv preprint arXiv:2605.05115. 2026.
[28] Marshall et al. Refusal in LLMs is an Affine Function. arXiv preprint arXiv:2411.09003. 2024.
[29] Arditi et al. Refusal in Language Models Is Mediated by a Single Direction. Neural Information Processing Systems. 2024.
[30] Bigelow et al. Forking Paths in Neural Text Generation. arXiv preprint arXiv:2412.07961. 2024.
[31] Bigelow et al. Forking Fast: Efficiently Estimating Uncertainty Dynamics in Text Generation. 2026.
[32] Zhu et al. Hot or Cold? Adaptive Temperature Sampling for Code Generation with Large Language Models. Proceedings of the AAAI Conference on Artificial Intelligence. 2024.
[33] Killick et al. Optimal detection of changepoints with a linear computational cost. Journal of the American Statistical Association. 2012.
[34] Wu et al. AxBench: Steering LLMs? Even Simple Baselines Outperform Sparse Autoencoders. International Conference on Machine Learning. 2025.
[35] West et al. Base Models Beat Aligned Models at Randomness and Creativity. arXiv preprint arXiv:2505.00047. 2025.
[36] Yun et al. The Price of Format: Diversity Collapse in LLMs. Conference on Empirical Methods in Natural Language Processing. 2025.
[37] Peeperkorn et al. Is Temperature the Creativity Parameter of Large Language Models? ICCC. 2024.
[38] Tang. Compact Constraint Encoding for LLM Code Generation: An Empirical Study of Token Economics and Constraint Compliance. arXiv preprint arXiv:2604.07192. 2026.
