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
6. The read position carries a low-dimensional map of the catalogue (intrinsic dimension 4-5 against 11-12 for shuffled nulls). On the grid task the mass displaced by bans moved to BFS's geodesic neighbours and never to the far side, *(clause inserted in iteration 2, marked in iteration 3)* which is consistent with geodesic proximity and with typicality, since those neighbours are also second choices of the model; the two are not separated on these events. *(Corrected in iteration 2: the geodesic order is unstable at layer 24 under paraphrase resampling, and on the shortest path task Floyd-Warshall, not the realised Bellman-Ford/SPFA, is the nearest survivor in every subsample. Section 2.3.2.)* The ban shift itself is almost entirely orthogonal to the algorithm directions, so the substitution versus subtraction share test was inconclusive for every algorithm.
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

# Iteration 2: the record repaired, a likelihood instrument, the route of a ban, the top five prohibition and a second model

## 2.1 Why this iteration ran what it ran

**The review of the iteration-1 record.** The review was blocking. It scored the report 4 overall (confidence 4), with soundness 1, presentation 3 and contribution 3. The soundness score came from two places where the report's conclusions contradicted its own tables. The report claimed that the substitute a ban produces replicated in five independent draws, but on the grid task the geometry draw had no clear mode (DFS 10 and unit weight Dijkstra 8 of 18 compliant programs). It also claimed that no grid knob above the 80% pass rate floor produced a second algorithm among compliant programs, but the decommitment draw's cumulative ban of BFS and DFS produced 16 compliant programs over unit weight Dijkstra and A*. The review further found that the selection rule had been quoted without its event gate and then applied to events the gate excludes; that the iteration had added forecasting families instead of events; that the report never named the rival its own controls suggested, namely that random directions push the shortest path task to the same substitute as a ban; that the geometric claim outran its evidence; that the cause of the missing locus probe was recorded nowhere; that several items of the request were not covered; that no positive claim was set against its nearest published neighbour; that the read position evidence on seeds was reported by halves; and that the objections of the hypothesis review had not been answered. Eleven items were marked must fix and three minor. The corrections they require are made in place in the iteration-1 section, each marked with what changed and why. Table 38 maps every item to the place where it is answered.

**Table 38.** Review items on the iteration-1 record and where this report answers them.

| Review item | What the review found | Where it is answered |
|-|-|-|
| Substitute claim over five draws | Grid geometry draw had no clear mode; the few unit weight Dijkstra programs were in fact 8 of 18 | Corrections in Sections 1.11 and 1.12; per draw table in Section 2.3.3 |
| Grid knob verdict | The cumulative BFS and DFS ban produced compliant unit weight Dijkstra and A* programs | Correction in Section 1.11; three draws in Section 2.3.4; positive target per task in Section 2.3.6 |
| Selection rule | Event gate omitted; rule applied to events the gate excludes; one Hill statistic not used | Correction in Section 1.1; gated forecast scores in Section 2.3.7; one statistic knob table in Section 2.3.6 |
| Events, not predictors | Fifteen forecasting families scored on two events | Families frozen at four (this section); bench with a presence pilot in Section 2.8; Section 2.12 |
| Generic perturbation rival | Random directions land on Bellman-Ford/SPFA like the ban | Correction to Table 26 in Section 1.9; perturbation table in Section 2.3.5; external ladder profile in Sections 2.4 and 2.7 |
| Geometric overreach | Proximity and typicality confounded; stability from point resampling | Correction to Section 1.12; layer and k sweep in Section 2.3.2 |
| Locus probe dead end | Cause unrecorded; inputs exist on disk | Correction in Section 1.7; probe re-run in Section 2.3.1 |
| Request coverage | Top five ban, natural run internals, SAE, thought anchors, same seed, lenses, NLA missing | Sections 2.3.1, 2.5, 2.6 and 2.9 |
| Novelty positioning | No claim set against its nearest neighbour | Section 2.3.11 |
| Seeds half reported | Shortest path cosine, word seed probe shift and entropy seed interval omitted | Corrections in Sections 1.10 and 1.12; Section 2.3.8 |
| Objections of the hypothesis review | Sham bans, simulation of own behaviour, point resampling, missing precedent | This section, below |
| Minor: missing outputs | Executed conditions and diagnostics absent from the record | Section 2.3.10 and notes in Sections 1.5 to 1.10 |
| Minor: post training verdict | Preregistered label replaced by an interpretation | Corrections in Sections 1.9 and 1.12 |
| Minor: bookkeeping | GPU hours, source files, grid failure taxonomy | Section 2.3.10; correction to the spend line in Section 1.12 |

**What the hypothesis review asked for, and what the iteration-1 screen showed.** The review of the hypothesis before iteration 1 raised four objections that the screen can now answer. First, the review argued that if processing a negation promotes an associate [4], a ban of an algorithm the model never writes should still move mass toward a related algorithm, so the preregistered equivalence between a sham ban and its mention twin was inconsistent with the mechanism. Two of nine sham bans did move mass: banning Floyd-Warshall gave Bellman-Ford/SPFA 23% of attempted programs and banning IDDFS gave DFS 12% (Section 2.3.9). Both promoted algorithms are content neighbours of the banned one and also the second choice of the model, so this is weak and confounded evidence for promotion triggered by negation. Second, the review named simulation of its own behaviour [39] as a rival reason why the stated alternative of the model predicts its behaviour: a model can forecast what it will do without any privileged access to a decision. That is exactly the free-form predictor's success in Table 7. Such simulation fits either branch of the substitution test below, so the free-form result says nothing about mechanism. Third, the review warned that resampling points within a fixed graph would make geodesic stability uninformative. The iteration-1 stability of 0.985 came from that procedure, and resampling at the level of paraphrases changes the shortest path picture (Section 2.3.2). Fourth, the review flagged an omitted precedent on approach organised internal states [40] and an unmapped lens named in the request, which we refer to as the j lens. The precedent is positioned in Section 2.3.11, and the lens, a Jacobian lens, was tested in Section 2.9.

**The hypothesis update.** The update kept the claim and changed the instrument. The claim is that a prohibition both subtracts the banned algorithm X and substitutes: it raises particular survivors by more than renormalisation would, and which survivors it raises depends on X. We call the rival the *latent ladder*: a fixed ordering of the survivors that any perturbation of the model reveals, under which a ban only subtracts and exposes the second choice of the model. Iteration 1 could not separate the two accounts, because every substitute it observed was also the second choice of the model and because on the shortest path task random directions reached the same second choice as the ban. The update made four changes. It replaced sampled frequencies, which carry no information under a fully collapsed baseline, with a likelihood instrument read from forward passes (Section 2.2), so that every single ban, sham ban and ban list becomes a measured event. It added a causal test of where a ban acts: through the prompt states before the first generated token, or by generated tokens reading the prohibition directly. It froze the forecasting families at four (ladder, association, prime and veto, proximity), fixed the ban wording at five templates, and moved the budget from predictors to events. And it ordered the iteration-1 record to be repaired before any new generation. A second claim was added: the read position encodes how strongly a ban will be obeyed, not what replaces X.

**The strategy.** Seven artifacts ran, one audit without generation and six experiments (Table 39). The audit repaired the record and ran every diagnostic that needed no GPU, including the locus probe that had never run. The likelihood screen and the Llama replication tested substitution against the latent ladder on the two path search tasks, in Qwen3-8B [5] and in Llama-3.1-8B-Instruct [22]. The route experiment patched key and value (KV) caches between a ban prompt and its neutral twin. The ban list experiment ran the request's literal prohibition of the top five algorithms. The bench build froze a confirmation bench of 12 new tasks behind a cheap presence pilot, with no ban prompt run on it. The readout experiment looked at the ban with sparse autoencoder features, attention, thought anchors, a same seed temperature test and lenses. The strategy fixed one rule for every experiment: the screen tasks (grid and shortest path) are never pooled into confirmation statistics, so the bench stays untouched until forecasts are committed in the next iteration.

**Table 39.** The seven artifacts of iteration 2, the question each was asked, and its hardware and spend.

| Artifact | Question | Model and hardware | OpenRouter spend |
|-|-|-|-|
| Audit [ARTIFACT:art_V1MvbYs5420o] | Repair the iteration-1 record; locus probe; geometry sweep; perturbation table; one statistic knob table; gated forecasts | No generation; probes on one RTX 4090 (about 8 min) | USD 0 |
| Likelihood screen [ARTIFACT:art_6zBfl3kDjeiP] | Substitution or latent ladder in Qwen3-8B (validity gate, gain matrices, X specific share) | Qwen3-8B; one 23 GB NVIDIA GPU, 3.38 GPU hours of scoring plus about 0.24 hours of generation | USD 0.30 |
| Route experiment [ARTIFACT:art_8_ULPE8jJQc_] | Does the ban act through the prompt states or directly at generation time; does the read position know how hard a ban will be obeyed | Qwen3-8B bf16; one RTX 4090, about 1.2 GPU hours | USD 0.32 |
| Ban list experiment [ARTIFACT:art_IVZc3TWCeE9f] | Where the mass lands when four or five algorithms are banned at once; bans that leave one survivor | Qwen3-8B; one RTX 4090, about 1 GPU hour | USD 0.42 |
| Llama replication [ARTIFACT:art_-QPYRaFERCBX] | The likelihood screen and route readout in a second model family | Llama-3.1-8B-Instruct bf16; one RTX 4090, 0.64 GPU hours logged | USD 0.49 |
| Bench build [ARTIFACT:art_0ndRfWKBWclR] | A frozen 12-task confirmation bench with presence pilot, labeller gate and baseline likelihoods | Qwen3-8B, official 8-bit floating point checkpoint (and a Llama pilot); one RTX 2000 Ada (16 GB), about 1.4 GPU hours | USD 0.14 |
| Readout experiment [ARTIFACT:art_3iv5G76C3yoX] | SAE, attention and prime and veto readouts of the ban; thought anchors; same seed temperature test; Jacobian lens and NLA | Qwen3-8B bf16 states, 8-bit twin for generation; one 16 GB GPU, about 1.05 GPU hours | USD 0.04 |

## 2.2 Shared protocol v2 and the likelihood instrument

**Canonical suite and labels.** Every experiment on the path search tasks used the association experiment's task text, prompt scaffold, hidden tests (48 grid cases, 45 shortest path cases), 22 references and labeller, copied byte for byte. Each rechecked the labeller before use: the combined label agreed with the adjudicated gold set on 0.965 or 0.966 of 141 programs in four experiments and on 135 of 144 in the ban list experiment, and all 22 references were labelled correctly. Labels are at the level of mechanism: the runtime signature decides, so a renamed BFS counts as BFS.

**Templates and twins.** Ban wording was frozen at five templates (Table 40), each with a mention twin and a neutral twin. We call a ban's *neutral twin* the same sentence with the algorithm's display name replaced by frequent concrete nouns from the dataset artifact's 718-noun bank (`man`, `guy`, `house` and so on) and padded with filler tokens until the prompt has the ban prompt's exact token length; from the task text onward the two prompts have identical token ids. Two generic perturbations were also frozen: a nonce ban (`Do not use the Zorblax method`, in the five templates) and a novelty instruction (`Write a novel algorithm for this task, one you have not seen before.`). We refer to the templates by their order in Table 40, from the first to the fifth.

**Table 40.** The five frozen ban templates of shared protocol v2 (X is the algorithm's display name, N the neutral nouns).

| Template | Ban | Mention twin | Neutral twin |
|-|-|-|-|
| first | Do not use X for this task. | You could use X for this task. | Do not use N for this task. |
| second | Your solution must not rely on X. | Your solution may rely on X. | Your solution must not rely on N. |
| third | Avoid X entirely. | Consider X first. | Avoid N entirely. |
| fourth | X is not allowed here. | X is allowed here. | N is not allowed here. |
| fifth | Write a correct solution that does not use X. | Write a correct solution that may use X. | Write a correct solution that does not use N. |

**Event gate.** One definition replaces the two that iteration 1 mixed. The *avoidance* of a ban is one minus the share of all sampled programs labelled as a banned mechanism. An event enters a forecast contest only if avoidance is at least 0.5 and at least 20 attempted programs are not banned. The *landing distribution* is the label distribution of those attempted programs not banned. The compliant share (correct and not banned) is reported beside it and drives the knob table only, because most grid programs that fail do so through implementation bugs, not through the tests (Section 2.3.10).

**The likelihood instrument.** Under a fully collapsed baseline every survivor has sampled frequency zero, which made the typicality forecast uniform and the sham bans uninformative in iteration 1. We define the *forced ratio latent probability* (FRLP) of algorithm j under prompt c as an importance sampling estimate of the log probability that the model writes an algorithm j program when given c. The model first writes programs under forced prompts F_j (`Implement j for this task` and nine paraphrases). Programs labelled j are kept; names of catalogue algorithms are scrubbed from identifiers, comments and docstrings, and a scrubbed program is kept only if it passes the same tests and keeps the same runtime label. Each kept program p_m is then scored by teacher forcing under any prompt c, giving its summed log probability l(p_m | c). With the mixture of forced prompts q(p) = (1/K) Σ_k P(p | F_j^k) as the proposal, the balance heuristic of multiple importance sampling [41], and y_j the share of forced attempts labelled j,

L_j(c) = log y_j + log mean_m exp[ l(p_m | c) − log q(p_m) ].

The same program text is scored under c and under its proposal, so phrasing and length cancel. Each cell reports the Kish effective sample size (ESS) of its importance weights. The *gain* of survivor j under a ban of X with template w is G[X, j, w] = L_j(ban_w X) − L_j(neutral_w X). The mention twin splits a ban into a *prime* (mention minus neutral) and a *veto* (ban minus mention).

**The substitution test.** For each single ban row, the gains are centred over the survivors and regressed on the centred *external ladder profile* u, the mean gain over generic perturbations of matched size: the nonce ban, six random edits of the prompt states in layers 12 to 24 whose norm is pinned per layer and position to the ban's own displacement, and the novelty instruction. The fitted part is the ladder component of the row and the residual its X specific component. Summed over rows and corrected for template and program replicate noise, they give V_u and V_s, and we call SHARE = V_s / (V_s + V_u) the *X specific share*. A ladder exists on a task if the generic profiles agree with one another (mean pairwise cosine over survivors other than the default of at least 0.5). The aim of the X specific residual is its Spearman correlation with the *prime and veto profile* (the mention twin's gains over its neutral twin, with X removed), computed on disjoint program halves and different nouns, against an exact within row permutation null. The branches were fixed before data: substitution (share interval above 0.5 and aim above the null's 95th percentile), X specific but unaimed (share interval above 0.5, aim not above the null), ladder (share interval below 0.5 and a ladder exists), pure subtraction (no between survivor variance beyond replicate noise), and undetermined (any other case). A row needs at least three survivors. Both references (neutral twin primary, mention twin secondary) are reported, and a branch is called robust only if they agree.

## 2.3 The audit: the iteration-1 record repaired, without new generation

The audit [ARTIFACT:art_V1MvbYs5420o] read the six iteration-1 experiments in place, generated nothing, made no LLM calls and spent nothing on OpenRouter. It ran first because several of this iteration's analyses depended on what it found: where the algorithm can be read out, whether the geometric neighbours survive resampling, and which iteration-1 events are informative at all. Every number it produced names its source file. Its own checks recomputed 40 numbers quoted in the plan and matched 38; the two mismatches are explained below (the count of gated events and the rarefied Hill number of the semantic seed). An independent script rederived 20 headline numbers with no mismatch, a second one reran five headline tests, and every placebo failed as it should.

### 2.3.1 The locus probe that never ran

**Cause.** The forking token experiment's probe file is 28 bytes, an empty summary written at 18:29:22. Its state log records the start of the state phase at 18:31:55 and the grid and shortest path states saved at 18:34:34 and 18:34:50. The probe stage ran before its inputs existed and found an empty folder. The measurement was therefore a CPU job on files already on disk, not a missing experiment.

**Design.** The saved states hold 300 generations per task (200 baseline, 100 under the modal ban) at eight positions (the read position, generated tokens 8, 16, 32 and 64, and the tokens before, at and after the first algorithm identifying token, which we call the commit token) and at layers 8 to 28. Within one ban prompt the model wrote BFS 21 times and DFS 78 times on the grid task (one unit weight Dijkstra) and Dijkstra 20 times and Bellman-Ford/SPFA 80 times on the shortest path task. These contrasts within one ban prompt are the natural run internals the request asks for: same prompts, different algorithms written. The probes are ridge regularised logistic regression probes fitted with folds that hold out one paraphrase at a time, which is the honest test because the read position is identical within a paraphrase. Each probe is compared with 200 refits on globally shuffled labels and 200 refits on labels shuffled within paraphrase (the null for a probe that knows no more than the base rate of each paraphrase), with a familywise null over layers. A written text control fits the same probe to features of the text written so far. A batched solver was unit tested against sklearn (identical predictions; largest relative coefficient difference 3.9e-5). The preregistered rule moves the locus to the first generated position whose decoder beats the read position by at least 20 points of balanced accuracy and beats both nulls; a precommit qualifier asks whether the state carries more than the written text.

**Table 41.** Decoder of the algorithm written, within one ban prompt (grid: BFS against DFS; shortest path: Dijkstra against Bellman-Ford/SPFA), balanced accuracy at the best layer per position, with the read position accuracy at that layer, both nulls and the written text control (source: `results/locus.json`).

| Task | Position (median token) | Best layer | Balanced accuracy | Read position at that layer | Difference [95% CI] | Global null p95 | Within paraphrase null p95 | Text control | Passes rule |
|-|-|-|-|-|-|-|-|-|-|
| Grid | read position | 16 | 0.855 | n/a | n/a | n/a | n/a | 0.5 | n/a |
| Grid | before commit token (6) | 20 | 0.855 | 0.791 | +0.064 [0.0, 0.201] | 0.639 | 0.855 | 0.673 | no |
| Grid | after commit token (7) | 23 | 0.855 | 0.791 | +0.064 [0.0, 0.201] | 0.652 | 0.855 | 0.673 | no |
| Grid | token 8 | 26 | 0.855 | 0.791 | +0.064 [0.0, 0.201] | 0.659 | 0.855 | 0.673 | no |
| Grid | token 16 | 9 | 0.798 | 0.402 | +0.396 [-0.065, 0.537] | 0.658 | 0.879 | 0.673 | no |
| Grid | token 32 | 23 | 0.798 | 0.791 | +0.006 [-0.16, 0.229] | 0.653 | 0.850 | 0.542 | no |
| Grid | token 64 | 27 | 0.739 | 0.791 | -0.052 [-0.203, 0.239] | 0.657 | 0.812 | 0.598 | no |
| Shortest path | read position | 13 | 0.625 | n/a | n/a | n/a | n/a | 0.5 | n/a |
| Shortest path | before commit token (6) | 8 | 0.762 | 0.481 | +0.281 [0.145, 0.388] | 0.669 | 0.681 | 0.756 | yes (mechanical) |
| Shortest path | forking token (7) | 17 | 0.731 | 0.550 | +0.181 [0.046, 0.261] | 0.650 | 0.644 | 0.675 | no |
| Shortest path | after commit token (7) | 10 | 0.762 | 0.456 | +0.306 [0.12, 0.463] | 0.656 | 0.675 | 0.762 | yes |
| Shortest path | token 8 | 8 | 0.831 | 0.481 | +0.350 [0.182, 0.525] | 0.663 | 0.682 | 0.831 | yes |
| Shortest path | token 16 | 8 | 0.837 | 0.481 | +0.356 [0.193, 0.525] | 0.650 | 0.650 | 0.837 | yes |
| Shortest path | token 32 | 15 | 0.837 | 0.550 | +0.287 [0.122, 0.399] | 0.675 | 0.669 | 0.831 | yes |
| Shortest path | token 64 | 8 | 0.831 | 0.481 | +0.350 [0.182, 0.525] | 0.669 | 0.662 | 0.819 | yes |

[FIGURE:fig_locus_text]

**What the locus probe showed.** On the grid task no position passes the rule, so the mechanical locus stays at the read position. The read position already separates the prompts that will produce DFS from those that will produce BFS (balanced accuracy 0.855 at layer 16), but at every generated position the within paraphrase null reaches the observed accuracy: the signal is the paraphrase's base rate, not anything specific to a sample. BFS and DFS programs also share their commit token (`' deque'`; 51 of 78 DFS programs and all 21 BFS programs commit at token 6), so the commit index does not separate the classes on this task. On the shortest path task the first passing position is the token before the commit token (layer 8, +0.281 over the read position, within paraphrase p = 0.005; a second implementation with 40 sklearn refits gave p = 0.024 against a placebo p of 0.17). The written text control reaches 0.756 at the same position, so the state adds 0.006 over the text, below the preregistered 0.10 margin. The audit therefore qualified the shortest path locus as a readout after commitment. The text separates the classes from generated token 4 on: Dijkstra programs write `import heapq` and Bellman-Ford/SPFA programs write `from collections import deque`. The deciding token is generated token 3, emitted from states at tokens 1 to 3 that were never saved, and the forking token experiment had independently confirmed a forking token at that index (`import`, total variation 0.80; Table 19). The first token at which the text alone reaches 0.8 is token 8. No decision locus was found on either task.

Three further readings came out of the same states. The difference-in-means direction at the token before the commit token has held-out AUC 0.882 (grid) and 0.749 (shortest path), below the 0.9 bar that would reopen a generation time removal. Per paraphrase, the read position probe's held-out probability of the substitute tracks the share of the substitute that paraphrase produced (Spearman 0.63, exact p = 0.056, grid; 0.65, p = 0.045, shortest path; ten paraphrases each), a first sign that the read position knows how strongly a wording will be obeyed. The positive controls (baseline against ban states) were decoded at balanced accuracy close to 1.0.

### 2.3.2 Geometry under paraphrase resampling

The geometry experiment's stability figure of 0.985 came from resampling points on a fixed graph, which the hypothesis review had warned is uninformative. The audit rebuilt the principal component projection, the nearest neighbour graph and the centroids on 1,000 paraphrase level subsamples, for k in {5, 10, 15, 20} at every layer of the two gate bands (24 to 28 grid, 21 to 27 shortest path), after reproducing the committed distance matrices exactly (largest absolute difference 0.0000). Table 42 gives the k = 10 column.

**Table 42.** Nearest surviving centroid to the default algorithm under 1,000 paraphrase subsamples, k = 10 (source: `tables/geometry_stability.csv`; distances on full data).

| Task | Layer | P(DFS nearest) | P(unit weight Dijkstra nearest) | P(both are the two nearest) | Full data order | MDS stress-1 |
|-|-|-|-|-|-|-|
| Grid | 24 | 0.523 | 0.477 | 1.0 | unit weight Dijkstra > DFS > A* > IDDFS > bidirectional BFS | 0.202 |
| Grid | 25 | 0.880 | 0.120 | 1.0 | DFS > unit weight Dijkstra > A* > IDDFS > bidirectional BFS | 0.212 |
| Grid | 26 | 0.954 | 0.046 | 1.0 | same | 0.213 |
| Grid | 27 | 1.0 | 0.0 | 1.0 | same | 0.217 |
| Grid | 28 | 1.0 | 0.0 | 1.0 | same | 0.230 |

| Task | Layer | P(Floyd-Warshall nearest) | P(Bellman-Ford/SPFA nearest) | P(Bellman-Ford/SPFA nearer than bidirectional Dijkstra) | Rank of Bellman-Ford/SPFA (full data) | Full data order | MDS stress-1 |
|-|-|-|-|-|-|-|-|
| Shortest path | 21 | 1.0 | 0.0 | 0.555 | 3 | Floyd-Warshall > bidirectional Dijkstra > Bellman-Ford/SPFA > Dial | 0.205 |
| Shortest path | 22 | 1.0 | 0.0 | 0.633 | 3 | same | 0.239 |
| Shortest path | 23 | 1.0 | 0.0 | 0.829 | 2 | Floyd-Warshall > Bellman-Ford/SPFA > bidirectional Dijkstra > Dial | 0.235 |
| Shortest path | 24 | 1.0 | 0.0 | 0.820 | 2 | same | 0.224 |
| Shortest path | 25 | 1.0 | 0.0 | 0.810 | 2 | same | 0.226 |
| Shortest path | 26 | 1.0 | 0.0 | 0.897 | 2 | same | 0.227 |
| Shortest path | 27 | 1.0 | 0.0 | 0.964 | 2 | same | 0.229 |

Over all four values of k the picture is the same. On the shortest path task Floyd-Warshall is the nearest survivor to Dijkstra in 100% of subsamples at all 28 (layer, k) settings, and Bellman-Ford/SPFA, the algorithm every ban landed on, is never nearest; its full data rank is 2 in 75% of settings and 3 in 25%. The geometry experiment's sensitivity matrix, which recomputes the two flagged centroids from correctly labelled forced samples only, puts bidirectional Dijkstra (40.91) closer to Dijkstra than Bellman-Ford/SPFA (42.18), with Floyd-Warshall at 25.49 and Dial at 58.01. On the grid task DFS is nearest to BFS at layers 25 to 28 (probability 0.87 to 1.00 over k) and unit weight Dijkstra overtakes it at layer 24 (DFS 0.52 to 0.60), while DFS and unit weight Dijkstra are always the two nearest. Neighbour orders agree across k and layer with mean Kendall tau 0.933 (grid) and 0.870 (shortest path). Centroids from name masked prompts give different orders (grid top-1 stability 0.18 to 0.815). The grid ban's landing on DFS and unit weight Dijkstra is therefore consistent with geodesic proximity and with typicality, since both are also second choices of the model, and the two are not separated on these events. On the shortest path task geodesic proximity predicts the wrong substitute.

### 2.3.3 The substitute, draw by draw

The audit recomputed the modal ban substitutes from the per-sample rows of every draw (Table 43). On the shortest path task the claim survives as written: all 272 compliant programs in the five draws were Bellman-Ford/SPFA. On the grid task DFS was the realised mode in four of five draws and took 116 of 128 compliant programs; in the geometry draw, the only one sampled with HF `generate` and the one with the highest banned share, 8 of 18 compliant programs were unit weight Dijkstra and the event had no clear mode.

**Table 43.** Compliant programs under the modal ban, per draw (source: `corrections.json`; Wilson 95% intervals for the substitute's share).

| Draw (engine) | Grid: DFS / compliant | Other compliant labels | DFS share [95%] | Shortest path: Bellman-Ford/SPFA / compliant | Share [95%] |
|-|-|-|-|-|-|
| Association (vLLM) | 38 / 38 | none | 1.0 [0.908, 1.000] | 86 / 86 | 1.0 [0.957, 1.000] |
| Geometry (HF) | 10 / 18 | unit weight Dijkstra 8 | 0.556 [0.337, 0.754] | 22 / 22 | 1.0 [0.851, 1.000] |
| Forking token (vLLM) | 40 / 41 | unit weight Dijkstra 1 | 0.976 [0.874, 0.996] | 80 / 80 | 1.0 [0.954, 1.000] |
| Decommitment (vLLM) | 16 / 18 | unit weight Dijkstra 2 | 0.889 [0.672, 0.969] | 38 / 38 | 1.0 [0.908, 1.000] |
| Instruction tuning (vLLM) | 12 / 13 | unit weight Dijkstra 1 | 0.923 [0.667, 0.986] | 46 / 46 | 1.0 [0.923, 1.000] |
| Pooled | 116 / 128 | unit weight Dijkstra 12 | 0.906 [0.843, 0.946]; draw cluster bootstrap [0.75, 0.98] | 272 / 272 | 1.0 [0.986, 1.000] |

### 2.3.4 The cumulative ban of BFS and DFS does not replicate

The three draws that banned BFS and DFS together disagree on everything the knob table depends on (Table 44). The decommitment draw spread its 16 compliant programs over two algorithms, the geometry draw put all 18 on one, and in the association draw the model reimplemented a banned mechanism 94 times out of 100. The pairs the review quoted from Table 37 (0.88 / 1.00, 0.96 / 0.99, 0.53 / 0.933) are each draw's pass rate followed by its reference pass rate.

**Table 44.** The cumulative ban of BFS and DFS in three draws (source: `corrections.json#cumulative_bfs_dfs_ban`).

| Draw | N | Banned share (mechanism) | Pass rate | Compliant programs | Compliant composition |
|-|-|-|-|-|-|
| Decommitment | 100 | 0.81 | 0.88 | 16 | unit weight Dijkstra 13, A* 3 |
| Geometry | 50 | 0.62 | 0.96 | 18 | unit weight Dijkstra 18 |
| Association | 100 | 0.94 | 0.53 | 5 | unit weight Dijkstra 4, A* 1 |

### 2.3.5 Every perturbation, side by side: the generic perturbation rival

The audit assembled one table of every condition in the six draws: 249 condition rows covering 20,270 programs, each with its pass cost against its own reference (Newcombe intervals [42]), the label composition among correct and among attempted programs, and the share of the second choice with a Wilson interval (`tables/perturbation_table.csv`). Tables 45 and 46 give the rows that bear on the generic perturbation rival. On the shortest path task every nonsemantic perturbation that produced at least 10 correct programs other than Dijkstra (8 of 8 such rows) had Bellman-Ford/SPFA as their majority, random directions included, and so did 3 of 4 semantic ones. Band random direction 2 of the instruction tuning experiment turned all 33 of its correct programs into Bellman-Ford/SPFA, against Dijkstra 100 of 100 in its control. On the grid task generic perturbations almost never left BFS: random directions broke programs (pass rates 0.41 and 0.68) but every correct program stayed BFS, and only two rows other than bans with at least 10 correct programs other than the default exist, both mention twins (A* and DFS). On the shortest path task a ban and an arbitrary perturbation end in the same place; on the grid task only the ban reaches DFS at scale.

**Table 45.** Shortest path perturbations: label composition of correct programs and Bellman-Ford/SPFA share (source: `tables/perturbation_table.csv`).

| Draw | Perturbation | N | Pass (reference) | Correct programs | Bellman-Ford/SPFA share [95%] |
|-|-|-|-|-|-|
| Decommitment | random direction 1, c = 0.25 | 100 | 0.79 (0.95) | Dijkstra 53, Bellman-Ford/SPFA 26 | 0.329 [0.236, 0.439] |
| Decommitment | random direction 2, c = 0.25 | 100 | 0.87 (0.95) | Dijkstra 82, Bellman-Ford/SPFA 5 | 0.057 [0.025, 0.128] |
| Decommitment | decommitment direction, c = 0.25 | 100 | 0.78 (0.95) | Bellman-Ford/SPFA 54, Dijkstra 23, other 1 | 0.692 [0.583, 0.784] |
| Decommitment | decommitment direction, c = 0.375 | 100 | 0.67 (0.95) | Bellman-Ford/SPFA 47, Dijkstra 19, other 1 | 0.701 [0.583, 0.798] |
| Decommitment | decommitment direction, c = 0.5 | 100 | 0.37 (0.95) | Dijkstra 25, Bellman-Ford/SPFA 10, other 2 | 0.270 [0.154, 0.430] |
| Decommitment | breadth direction, c = 0.25 | 100 | 0.60 (0.95) | Bellman-Ford/SPFA 31, Dijkstra 28, Dial 1 | 0.516 [0.393, 0.638] |
| Decommitment | other task's direction, c = 0.25 | 50 | 0.72 (0.95) | Bellman-Ford/SPFA 28, Dijkstra 8 | 0.777 [0.619, 0.883] |
| Decommitment | variable name placebo, c = 0.25 | 100 | 0.66 (0.95) | Dijkstra 60, Dial 3, Bellman-Ford/SPFA 2, other 1 | 0.030 [0.008, 0.104] |
| Decommitment | enumeration prompt | 100 | 0.82 (0.885) | Dijkstra 80, Bellman-Ford/SPFA 2 | 0.024 [0.007, 0.085] |
| Instruction tuning | band random direction 1 | 100 | 0.00 (1.00) | none | n/a |
| Instruction tuning | band random direction 2 | 100 | 0.33 (1.00) | Bellman-Ford/SPFA 33 | 1.0 [0.896, 1.000] |
| Instruction tuning | random direction 1, read position only, c = 1.0 | 100 | 1.00 (1.00) | Dijkstra 90, Bellman-Ford/SPFA 9, other 1 | 0.090 [0.048, 0.162] |
| Instruction tuning | sharpening subtraction, layer 18, c = 0.5 | 50 | 0.98 (1.00) | Dijkstra 48, Bellman-Ford/SPFA 1 | 0.020 [0.004, 0.107] |
| Instruction tuning | sharpening subtraction, read position only, no cutoff | 20 | 0.20 (1.00) | Dijkstra 3, Bellman-Ford/SPFA 1 | 0.25 [0.046, 0.699] |
| Instruction tuning | base model, chat template | 300 | 0.30 (1.00) | Dijkstra 63, Bellman-Ford/SPFA 24, other 2, Floyd-Warshall 1 | 0.266 [0.186, 0.366] |
| Instruction tuning | base model, plain completion | 300 | 0.083 (1.00) | Bellman-Ford/SPFA 16, Dijkstra 8, Floyd-Warshall 1 | 0.64 [0.445, 0.798] |
| Instruction tuning | instruct model, plain completion | 100 | 0.72 (1.00) | Dijkstra 57, Floyd-Warshall 8, Bellman-Ford/SPFA 7 | 0.097 [0.048, 0.187] |
| Decoding | semantic seed | 100 | 0.92 (0.99) | Bellman-Ford/SPFA 61, Dijkstra 30, Floyd-Warshall 1 | 0.663 [0.562, 0.751] |
| Decoding | novelty instruction | 100 | 0.96 (0.99) | Dijkstra 82, Bellman-Ford/SPFA 14 | 0.145 [0.089, 0.230] |
| Decoding | new algorithm instruction | 100 | 0.94 (0.99) | Dijkstra 90, Bellman-Ford/SPFA 4 | 0.042 [0.017, 0.104] |
| Decoding | enumeration prompt | 100 | 0.75 (0.99) | Dijkstra 67, Bellman-Ford/SPFA 8 | 0.106 [0.055, 0.197] |
| Decoding | T = 1.3, top-k = 10 | 100 | 1.00 (0.98) | Dijkstra 99, Bellman-Ford/SPFA 1 | 0.010 [0.002, 0.054] |
| Association | listing control | 100 | 1.00 (1.00) | Dijkstra 97, Bellman-Ford/SPFA 3 | 0.030 [0.010, 0.085] |
| Association | sham ban of Floyd-Warshall | 100 | 0.71 (1.00) | Dijkstra 68, Bellman-Ford/SPFA 3 | 0.042 [0.014, 0.117] |
| All five draws | modal ban of Dijkstra, pooled | 500 | 0.87 to 1.00 | Bellman-Ford/SPFA 272 (compliant) | 1.0 [0.986, 1.000] |

The sham ban of Floyd-Warshall shows why compliant and attempted programs must be told apart: 23 of its 100 attempted programs were Bellman-Ford/SPFA (Table 8), but only 3 of those passed the tests.

**Table 46.** Grid perturbations: label composition of correct programs and DFS share (source: `tables/perturbation_table.csv`).

| Draw | Perturbation | N | Pass (reference) | Correct programs | DFS share [95%] |
|-|-|-|-|-|-|
| Instruction tuning | band random direction 1 | 100 | 0.41 (1.00) | BFS 41 | 0.0 [0.000, 0.086] |
| Instruction tuning | band random direction 2 | 100 | 0.68 (1.00) | BFS 68 | 0.0 [0.000, 0.053] |
| Instruction tuning | random direction 1, read position only, c = 1.0 | 100 | 1.00 (1.00) | BFS 100 | 0.0 [0.000, 0.037] |
| Decommitment | decommitment direction, c = 0.25 | 100 | 0.57 (1.00) | BFS 57 | 0.0 [0.000, 0.063] |
| Decoding | semantic seed | 100 | 0.93 (0.97) | BFS 91, bidirectional BFS 2 | 0.0 [0.000, 0.040] |
| Decoding | novelty instruction | 100 | 0.85 (0.97) | BFS 81, unit weight Dijkstra 2, DFS 1, A* 1 | 0.011 [0.002, 0.064] |
| Decoding | new algorithm instruction | 100 | 0.94 (0.97) | BFS 92, DFS 2 | 0.021 [0.006, 0.074] |
| Decoding | enumeration prompt | 100 | 0.99 (0.97) | BFS 99 | 0.0 [0.000, 0.037] |
| Decoding | T = 1.3, top-k = 10 | 100 | 0.95 (0.98) | BFS 94, DFS 1 | 0.010 [0.002, 0.057] |
| Instruction tuning | base model, chat template | 300 | 0.19 (1.00) | BFS 49, DFS 7, A* 1 | 0.122 [0.061, 0.232] |
| Instruction tuning | base model, plain completion | 300 | 0.05 (1.00) | BFS 12, DFS 3 | 0.20 [0.070, 0.452] |
| Instruction tuning | instruct model, plain completion | 100 | 0.73 (1.00) | BFS 73 | 0.0 [0.000, 0.050] |
| Association | listing control | 100 | 0.92 (0.933) | BFS 92 | 0.0 [0.000, 0.040] |
| Association | sham ban of IDDFS | 100 | 0.80 (0.933) | BFS 76, DFS 4 | 0.05 [0.020, 0.122] |
| Association | sham ban of unit weight Dijkstra | 100 | 0.71 (0.933) | BFS 69, DFS 2 | 0.028 [0.008, 0.097] |
| All five draws | modal ban of BFS, pooled | 500 | 0.46 to 0.76 | DFS 116, unit weight Dijkstra 12 (compliant) | 0.906 [0.843, 0.946] |

### 2.3.6 The knob table on one statistic

The iteration-1 knob table mixed unrarefied Hill numbers, rarefied differences, and Hill numbers that counted correct programs of the banned algorithm. The audit recomputed every knob with one statistic: the Hill number of order 1 [9] over compliant programs only (banned labels excluded), rarefied to a common depth of 25 by 1,000 draws without replacement, with a 90% interval from 1,000 paraphrase cluster bootstrap resamples times 200 rarefaction draws; cells with fewer than 25 compliant programs are marked and never extrapolated. Pass points are measured against each condition's own reference. Generate then select is a ceiling row, because its diversity comes from an external random choice among model proposed approaches, which is the mechanism of SimpleStrat [43]. Table 47 gives the rows that matter (all 183 rows are in `tables/knob_table.csv`).

**Table 47.** One statistic knob table: rarefied Hill-1 over compliant programs at depth 25 (source: `tables/knob_table.csv`).

| Task | Knob (draw) | Class | Compliant programs | Composition | Hill-1 [90% CI] | Pass points lost |
|-|-|-|-|-|-|-|
| Grid | generate then select (decoding) | ceiling | 55 | BFS 26, A* 14, unit weight Dijkstra 9, DFS 6 | 3.358 [3.315, 3.381] | 42.0 |
| Grid | mention of A* (association) | named mode cue | 41 | A* 24, BFS 11, unit weight Dijkstra 5, DFS 1 | 2.687 [1.861, 3.186] | 11.3 |
| Grid | base model, chat template (instruction tuning) | model swap | 57 | BFS 49, DFS 7, A* 1 | 1.549 [1.284, 1.814] | 81.0 |
| Grid | modal ban, five draws pooled | ban | 128 | DFS 116, unit weight Dijkstra 12 | 1.357 [1.250, 1.425] | 34.3 |
| Grid | novelty instruction (decoding) | diversity knob | 85 | BFS 81, unit weight Dijkstra 2, DFS 1, A* 1 | 1.227 [1.096, 1.346] | 12.0 |
| Grid | sham ban of IDDFS (association) | ban | 80 | BFS 76, DFS 4 | 1.205 [1.0, 1.542] | 13.3 |
| Grid | sham ban of unit weight Dijkstra (association) | ban | 71 | BFS 69, DFS 2 | 1.119 [1.0, 1.245] | 22.3 |
| Grid | modal ban (forking token) | ban | 41 | DFS 40, unit weight Dijkstra 1 | 1.111 [1.0, 1.243] | 35.0 |
| Grid | semantic seed (decoding) | diversity knob | 93 | BFS 91, bidirectional BFS 2 | 1.096 [1.0, 1.191] | 4.0 |
| Grid | new algorithm instruction (decoding) | diversity knob | 94 | BFS 92, DFS 2 | 1.093 [1.0, 1.187] | 3.0 |
| Grid | T = 1.3, top-k = 10 (decoding) | diversity knob | 95 | BFS 94, DFS 1 | 1.048 [1.0, 1.133] | 3.0 |
| Grid | modal ban (association) | ban | 38 | DFS 38 | 1.0 [1.0, 1.0] | 47.3 |
| Grid | cumulative ban of BFS and DFS (decommitment) | ban | 16 | unit weight Dijkstra 13, A* 3 | below depth (unrarefied 1.620) | 12.0 |
| Grid | cumulative ban of BFS and DFS (geometry) | ban | 18 | unit weight Dijkstra 18 | below depth (unrarefied 1.0) | 3.0 |
| Grid | cumulative ban of BFS and DFS (association) | ban | 5 | unit weight Dijkstra 4, A* 1 | below depth (unrarefied 1.649) | 40.3 |
| Grid | every steering, removal, forking window, random seed and remaining temperature arm | diversity knob | 3 to 307 | BFS only | 1.0, or below depth | 0 to 97 |
| Shortest path | generate then select (decoding) | ceiling | 75 | Bellman-Ford/SPFA 31, Dijkstra 29, Floyd-Warshall 15 | 2.802 [2.778, 2.812] | 24.0 |
| Shortest path | base model, plain completion (instruction tuning) | model swap | 25 | Bellman-Ford/SPFA 16, Dijkstra 8, Floyd-Warshall 1 | 2.179 [1.704, 2.611] | 91.7 |
| Shortest path | decommitment direction, c = 0.5 | diversity knob | 37 | Dijkstra 25, Bellman-Ford/SPFA 10, other 2 | 2.139 [1.553, 2.495] | 58.0 |
| Shortest path | breadth direction, c = 0.25 | diversity knob | 60 | Bellman-Ford/SPFA 31, Dijkstra 28, Dial 1 | 2.096 [1.920, 2.297] | 35.0 |
| Shortest path | base model, chat template | model swap | 90 | Dijkstra 63, Bellman-Ford/SPFA 24, other 2, Floyd-Warshall 1 | 2.018 [1.737, 2.262] | 70.0 |
| Shortest path | semantic seed (decoding) | diversity knob | 92 | Bellman-Ford/SPFA 61, Dijkstra 30, Floyd-Warshall 1 | 1.935 [1.534, 2.076] | 7.0 |
| Shortest path | decommitment direction, c = 0.25 | diversity knob | 78 | Bellman-Ford/SPFA 54, Dijkstra 23, other 1 | 1.911 [1.735, 2.069] | 17.0 |
| Shortest path | decommitment direction, c = 0.375 | diversity knob | 67 | Bellman-Ford/SPFA 47, Dijkstra 19, other 1 | 1.901 [1.675, 2.079] | 28.0 |
| Shortest path | random direction 1, c = 0.25 (decommitment) | diversity knob | 79 | Dijkstra 53, Bellman-Ford/SPFA 26 | 1.861 [1.657, 1.964] | 16.0 |
| Shortest path | random directions, four arms pooled | diversity knob | 199 | Dijkstra 135, Bellman-Ford/SPFA 64 | 1.851 [1.774, 1.903] | 47.75 |
| Shortest path | other task's direction, c = 0.25 | diversity knob | 36 | Bellman-Ford/SPFA 28, Dijkstra 8 | 1.688 [1.412, 1.857] | 23.0 |
| Shortest path | novelty instruction (decoding) | diversity knob | 96 | Dijkstra 82, Bellman-Ford/SPFA 14 | 1.500 [1.275, 1.692] | 3.0 |
| Shortest path | variable name placebo, c = 0.25 | diversity knob | 66 | Dijkstra 60, Dial 3, Bellman-Ford/SPFA 2, other 1 | 1.451 [1.129, 1.829] | 29.0 |
| Shortest path | random direction 1, read position only (instruction tuning) | diversity knob | 100 | Dijkstra 90, Bellman-Ford/SPFA 9, other 1 | 1.393 [1.209, 1.593] | 0.0 |
| Shortest path | enumeration prompt (decoding) | diversity knob | 75 | Dijkstra 67, Bellman-Ford/SPFA 8 | 1.382 [1.217, 1.581] | 24.0 |
| Shortest path | random direction 2, c = 0.25 (decommitment) | diversity knob | 87 | Dijkstra 82, Bellman-Ford/SPFA 5 | 1.231 [1.097, 1.371] | 8.0 |
| Shortest path | modal ban, five draws pooled | ban | 272 | Bellman-Ford/SPFA 272 | 1.0 [1.0, 1.0] | 2.4 |

**The positive target and the BUY rule.** The strategy's positive target was a knob that buys a second correct algorithm, a Hill number of at least 2 within its own compliant output, at a cost below 20 pass points. Under the single statistic no diversity knob and no ban meets it on either task. The closest is the semantic seed on the shortest path task (1.935 at 7 points). The mention of A* on the grid task reaches 2.69 at 11 points, but a mention recommends a named algorithm, so it meets only the literal reading of the target. The modal ban, the knob that iteration 1 ranked first on the shortest path task, scores exactly 1.0 there once banned programs no longer count: it replaces Dijkstra with one algorithm. The BUY rule names a best knob only when its 90% interval separates from the next; on the grid task the top rows (novelty instruction 1.227 [1.096, 1.346], sham ban of IDDFS 1.205 [1.0, 1.542]) do not separate, and on the shortest path task neither do the top five (Table 47). No knob advances. *(Correction, iteration 3: the sentences above paraphrase the target past its metric. A rarefied Hill-1 of at least 2 is an even two-algorithm split, which a 2:1 split never reaches. Stated in its own metric: no knob reaches an even split under 20 pass points; the semantic seed (Bellman-Ford/SPFA 61, Dijkstra 30 at 7 points; rebuilt Hill-1 1.940, 90% interval [1.770, 2.094], which includes 2) and the A* mention (2.69 at 11.3 points) are the two conditions that buy a second correct algorithm, and both name or describe it. The sham ban of IDDFS ranked above is a control, not a knob; the class rule is now declared in Section 3.2.5.)*

### 2.3.7 The forecast contest on gated events

The rule, quoted in full from the strategy, is that a forecasting family advances if its calibrated mean log score beats the next best family by at least 0.10 nats on at least three events where the families' top-1 nominations disagree, scored on informative events only: banned mode present at 10% or more of the latent baseline, compliance of at least 50% and at least two survivors. The hypothesis update fixed compliance in this rule to mean avoidance and added a floor of 20 attempted programs not banned. Of the 64 events with forecasts in the iteration-1 record, 24 were sampled (Table 48). Three informative events pass the gate: the association draw's two modal bans and the decommitment draw's grid modal ban, whose forecasts are all tied. The gate as written also admits the association draw's nine sham bans (12 events in all), but they land on the default by construction and their own artifact marked them uninformative. The geometry, instruction tuning and decommitment shortest path events fail the gate under either compliance definition, and the forking token draw made no family forecasts. On the gated events the families' mean log scores are: association map (Borda) -0.844 (2 events), free-form association -0.145 (2), listing control typicality -0.120 (2), sampled frequency -1.579 (3), decommitted distribution -1.674 (1) and uniform -1.674 (1). Only two gated events have disagreeing nominations, and the largest margin on them is 0.05 nats. No family can advance, so the iteration-1 ranking of forecasts in Table 36 rests largely on events the rule excludes.

**Table 48.** Every sampled iteration-1 event with forecasts, with both gates and the log scores of the main families (nats per attempted program not banned; 5% uniform mixing and a 2% floor for other labels in every family; top-1 nomination in brackets). Source: `results/tables.json#predict_gated`.

| Draw | Event | N | Attempted, not banned | Avoidance | Compliant share | Avoidance gate | Compliant gate | Log scores [top-1] |
|-|-|-|-|-|-|-|-|-|
| Association | grid ban A* (sham) | 100 | 100 | 1.0 | 0.72 | pass | pass | Borda -1.022 [BFS]; free-form -0.101 [BFS]; frequency -0.101 [BFS]; listing -0.131 [BFS] |
| Association | grid ban BFS (modal) | 100 | 90 | 0.90 | 0.38 | pass | fail | Borda -2.710 [unit weight Dijkstra]; free-form -0.152 [DFS]; frequency -1.630 [tie]; listing -0.101 [DFS] |
| Association | grid ban bidirectional BFS (sham) | 100 | 100 | 1.0 | 0.92 | pass | pass | Borda -1.063 [BFS]; free-form -1.141 [A*]; frequency -0.140 [BFS]; listing -0.169 [BFS] |
| Association | grid ban DFS (sham) | 100 | 96 | 0.96 | 0.86 | pass | pass | Borda -0.998; free-form -0.101; frequency -0.101; listing -0.101 [all BFS] |
| Association | grid ban unit weight Dijkstra (sham) | 100 | 100 | 1.0 | 0.71 | pass | pass | Borda -1.113; free-form -0.410; frequency -0.410; listing -0.368 [all BFS] |
| Association | grid ban IDDFS (sham) | 100 | 100 | 1.0 | 0.80 | pass | pass | Borda -1.114; free-form -0.511; frequency -0.564; listing -0.486 [all BFS] |
| Association | grid ban BFS and DFS | 100 | 6 | 0.06 | 0.05 | fail | fail | Borda -1.398 [bidirectional BFS]; others -1.406 [tie] |
| Association | shortest path ban Bellman-Ford/SPFA (sham) | 100 | 95 | 0.95 | 0.92 | pass | pass | Borda -0.926; free-form, frequency, listing -0.136 [all Dijkstra] |
| Association | shortest path ban bidirectional Dijkstra (sham) | 100 | 100 | 1.0 | 1.0 | pass | pass | Borda -0.791; free-form -0.205; frequency -0.205; listing -0.212 [Dijkstra] |
| Association | shortest path ban Dial (sham) | 100 | 100 | 1.0 | 0.97 | pass | pass | Borda -0.803; free-form -0.278; frequency -0.278; listing -0.269 [Dijkstra] |
| Association | shortest path ban Dijkstra (modal) | 100 | 91 | 0.91 | 0.86 | pass | pass | Borda -0.813 [Bellman-Ford/SPFA]; free-form -0.138 [Bellman-Ford/SPFA]; frequency -1.434 [tie]; listing -0.138 [Bellman-Ford/SPFA] |
| Association | shortest path ban Floyd-Warshall (sham) | 100 | 100 | 1.0 | 0.71 | pass | pass | Borda -0.911; free-form -0.933; frequency -0.933; listing -0.784 [Dijkstra] |
| Association | shortest path ban Dijkstra and Bellman-Ford/SPFA | 100 | 0 | 0.0 | 0.0 | fail | fail | not scorable |
| Geometry | grid ban BFS | 100 | 38 | 0.38 | 0.18 | fail | fail | association -3.543 [A*]; frequency -1.630 [tie]; geodesic -1.337 [DFS]; decoder -1.287 [DFS] |
| Geometry | grid ban BFS and DFS | 50 | 19 | 0.38 | 0.36 | fail | fail | association -0.998 [unit weight Dijkstra]; geodesic -1.073 [unit weight Dijkstra]; decoder -4.124 [IDDFS] |
| Geometry | grid ban BFS and unit weight Dijkstra | 50 | 17 | 0.34 | 0.10 | fail | fail | association -3.966 [A*]; geodesic -1.280 [A*]; decoder -1.372 [IDDFS] |
| Geometry | shortest path ban Dijkstra | 100 | 28 | 0.28 | 0.22 | fail | fail | association -1.647 [Dial]; frequency -1.496 [tie]; geodesic -1.530 [Floyd-Warshall]; decoder -1.587 [bidirectional Dijkstra] |
| Geometry | shortest path ban Dijkstra and Bellman-Ford/SPFA | 50 | 1 | 0.02 | 0.0 | fail | fail | all -3.912 |
| Decommitment | grid ban BFS | 100 | 51 | 0.51 | 0.18 | pass | fail | every family -1.674 [tie] |
| Decommitment | grid ban BFS and DFS | 100 | 19 | 0.19 | 0.16 | fail | fail | every family -1.538 [tie] |
| Decommitment | shortest path ban Dijkstra | 100 | 46 | 0.46 | 0.38 | fail | fail | decommitted -0.594 [Bellman-Ford/SPFA]; frequency (vLLM) -0.731 [Bellman-Ford/SPFA]; uniform -1.733 |
| Decommitment | shortest path ban Dijkstra and Bellman-Ford/SPFA | 100 | 17 | 0.17 | 0.01 | fail | fail | all -3.912 [tie] |
| Instruction tuning | grid ban BFS | 100 | 38 | 0.38 | 0.13 | fail | fail | base plain completion -0.430 [DFS]; base chat -0.304 [DFS]; instruct chat -1.630 [tie] |
| Instruction tuning | shortest path ban Dijkstra | 100 | 46 | 0.46 | 0.46 | fail | fail | base plain completion -0.255; base chat -0.096; instruct chat -0.096 [all Bellman-Ford/SPFA] |

These scores are computed over attempted programs not banned, so they differ slightly from the compliant only scores of Tables 7, 14 and 36.

### 2.3.8 Seeds at the read position: both halves of the dissociation

Iteration 1 reported that the grid semantic seed moved the read position state toward its implied algorithm while the output barely moved. The other half was in the same file and was not reported (Table 49). On the shortest path task the semantic seed's displacement did not point toward the Bellman-Ford/SPFA centroid, yet the output moved two thirds of the way to it. The word seed moved the grid probe's decoded distribution toward A* by 0.88 with no change in behaviour. The entropy seed's interval on the shortest path task reaches 1.596, above the 1.5 equivalence bound, so its equivalence with paraphrase noise was not shown. Displacement along the mode subspace built from forced prompts predicted behavioural movement in neither direction.

**Table 49.** Read position displacement against behavioural movement for the seeds (sources: decoding experiment `results/analysis.json`, audit `results/tables.json#seeds`; behaviour shifts with Newcombe 95% intervals).

| Task | Seed | Read position evidence | Behaviour among correct programs | Behaviour among attempted programs |
|-|-|-|-|-|
| Grid | semantic (implies bidirectional search) | cosine 0.493 with the bidirectional BFS centroid | bidirectional BFS +2.15 points [-1.97, 7.51]; BFS -1.12 | bidirectional BFS +5.0 points [0.33, 11.18]; BFS -4.0 |
| Shortest path | semantic (implies relaxation over all edges) | cosine -0.087 with the Bellman-Ford/SPFA centroid | Bellman-Ford/SPFA +66.30 points [55.50, 75.14]; Dijkstra -67.39 | Bellman-Ford/SPFA +61.0 points [50.53, 69.98]; Dijkstra -62.0 |
| Grid | word | ratio 1.555 [1.309, 1.85] of paraphrase noise; probe decoded shift +0.88 toward A* | BFS +1.03 points; no program other than BFS | BFS +1.0 point |
| Shortest path | entropy | ratio 1.165 [1.0, 1.596]; upper bound above the 1.5 bound | Dijkstra share unchanged | unchanged |

### 2.3.9 Sham bans as a weak test of negation triggered promotion

The audit compared each survivor's share under each of the nine bans of absent algorithms with its share in the association draw's baseline (N = 300), and called a survivor promoted if it gained at least 10 points with Fisher p below 0.05. Two promotions passed: banning IDDFS raised DFS by 12 points (p = 3.5e-8) and banning Floyd-Warshall raised Bellman-Ford/SPFA by 23 points (p = 1.7e-15). Two smaller shifts fell below the cut: banning unit weight Dijkstra raised DFS by 8 points (p = 1.2e-5) and banning Dial raised Bellman-Ford/SPFA by 5 points (p = 0.0009). In both promotions the gaining algorithm is a content neighbour of the banned one and also the second choice of the model, so the test cannot say whether the negation promoted an associate or merely disturbed the default toward the ladder's next rung. Shuffling the condition labels gave no promotion, as it should.

### 2.3.10 Executed outputs missing from the iteration-1 record, and bookkeeping

**Forced conditions of the association experiment.** Table 6 was captioned as every condition, but the experiment also ran eleven forced implementation conditions of 10 samples each (Table 50). They match the geometry experiment's manipulation check (Table 11): the model cannot write a passing IDDFS on the grid task or a Dial on the shortest path task, and asked for bidirectional Dijkstra it writes plain Dijkstra every time.

**Table 50.** Forced implementations in the association experiment (N = 10 each; labels of attempted programs; source: association experiment `data/samples.jsonl`, conditions `forced:*`).

| Task | Requested algorithm | Pass | Labels |
|-|-|-|-|
| Grid | A* | 10/10 | A* 9, unit weight Dijkstra 1 |
| Grid | BFS | 9/10 | BFS 10 |
| Grid | bidirectional BFS | 4/10 | BFS 5, bidirectional BFS 5 |
| Grid | DFS | 3/10 | DFS 10 |
| Grid | unit weight Dijkstra | 10/10 | unit weight Dijkstra 8, BFS 1, DFS 1 |
| Grid | IDDFS | 0/10 | IDDFS 10 |
| Shortest path | Bellman-Ford/SPFA | 10/10 | Bellman-Ford/SPFA 10 |
| Shortest path | bidirectional Dijkstra | 4/10 | Dijkstra 10 |
| Shortest path | Dial | 0/10 | other 5, Dial 4, Dijkstra 1 |
| Shortest path | Dijkstra | 10/10 | Dijkstra 10 |
| Shortest path | Floyd-Warshall | 10/10 | Floyd-Warshall 10 |

**Other executed outputs.** The association experiment's robustness block held an in-sample, sharpness matched sensitivity that the report omitted: with one sharpening power per family fitted on the two events, the Borda association map scored -1.386 and sampled frequency -1.475, the first rank map -0.888, the external Llama map -0.437, and the free-form answer and listing control both -0.059. These are in-sample numbers, not calibrated out-of-sample scores. In the forking token experiment, the next token entropy at the 13 forking token candidates averaged 0.527 bits (maximum 1.494) against 0.017 bits (maximum 0.130) at the 10 control positions. Its change point detector, tested on planted changes, caught a total variation change of 0.2, 0.3 and 0.5 at the right position in 82.5%, 95% and 99% of trials with a 6% false positive rate, and the grid forking token candidate on ban path 0 at token 9 confirms at a total variation threshold of 0.10 and 0.15 but not at the preregistered 0.20. Its engine test found greedy prefixes identical in only 14% of runs at 10 tokens and in all runs at 40 tokens. The decommitment experiment's arms at c = 1 in layers 14 and 22 passed 0 of 10 on both tasks. The geometry experiment's Procrustes disparity between the named and name masked centroid sets was 0.18 (grid) and 0.25 (shortest path), and it dropped two preregistered components under its drop order: the external model association elicitation and the distribution decoder that holds out one condition at a time. In the decoding experiment's enumeration arm on the shortest path task, the model wrote Bellman-Ford/SPFA 33 times but only 8 of those passed.

**GPU hours.** Iteration 1 recorded GPU time for two experiments. The audit took the first and last timestamp of every GPU phase log and summed the union of the spans (an upper bound that includes waits): geometry 2.92 GPU hours, forking token 1.55, decommitment 3.23, instruction tuning 2.47 and decoding 3.31. The association experiment has no GPU phase log; its own report gave about 6 minutes.

**Grid failure taxonomy.** Because a compliant program must be correct, low grid compliance could reflect test bias rather than broken programs. Of the 273 DFS programs in the association draw, 161 failed: 127 wrong answers, 31 timeouts and 3 runtime errors. The review's own re-run showed that reading a returned None as an empty path rescues only 2 to 3 programs per condition (under the BFS ban, DFS correct programs rise from 38 to 40); the audit could not repeat it because the stored failure fields do not hold returned values. Table 51 gives the failure kinds per grid condition for the draws that stored them.

**Table 51.** Failing grid programs by kind (source: `results/tables.json#missing_outputs.grid_failure_taxonomy`; the forking token and decommitment draws did not store failure kinds).

| Draw | Condition | Failing | Wrong answer | Timeout | Runtime error |
|-|-|-|-|-|-|
| Association | baseline | 20 | 15 | 4 | 1 |
| Association | baseline, T = 1.3 | 21 | 17 | 3 | 1 |
| Association | ban BFS | 54 | 44 | 8 | 2 |
| Association | ban DFS | 12 | 11 | 1 | 0 |
| Association | ban bidirectional BFS | 8 | 8 | 0 | 0 |
| Association | ban IDDFS | 20 | 19 | 1 | 0 |
| Association | ban A* | 28 | 23 | 4 | 1 |
| Association | ban unit weight Dijkstra | 29 | 20 | 8 | 1 |
| Association | ban BFS and DFS | 47 | 40 | 6 | 1 |
| Association | listing control | 8 | 8 | 0 | 0 |
| Association | mention DFS | 35 | 20 | 15 | 0 |
| Association | mention IDDFS | 41 | 25 | 16 | 0 |
| Association | mention bidirectional BFS | 14 | 10 | 1 | 3 |
| Association | forced DFS | 7 | 5 | 2 | 0 |
| Association | forced IDDFS | 10 | 3 | 7 | 0 |
| Geometry | ban BFS | 24 | 9 | 14 | 1 |
| Geometry | ban BFS and unit weight Dijkstra | 14 | 5 | 9 | 0 |
| Geometry | forced DFS | 21 | 3 | 18 | 0 |
| Geometry | forced IDDFS | 30 | 6 | 23 | 1 |
| Instruction tuning | instruct, chat template, ban BFS | 30 | 10 | 19 | 1 |
| Instruction tuning | base model, plain completion | 277 | 151 | 27 | 99 |
| Decoding | generate then select | 45 | 15 | 27 | 2 |
| Decoding | novelty instruction | 15 | 5 | 7 | 1 |

**Base model caveats.** The instruction tuning experiment's base arms rest on few programs and weak labels. Under the chat template the base model produced parseable code in 0.583 [0.527, 0.638] of grid samples and 0.663 [0.608, 0.714] of shortest path samples, 57 and 90 correct programs out of 300, with runtime against AST kappa of 0.417 and 0.567 on those arms. In plain completion its correct shortest path programs were Bellman-Ford/SPFA 16, Dijkstra 8 and Floyd-Warshall 1, so its mode there is Bellman-Ford/SPFA, first rather than second. The preregistered verdicts stand as recorded: on the correctness conditioned Hill number, MIXED on the grid task (modal share gap 14.04 points against a 15-point bar) and INSTALLED_BY_POST_TRAINING on the shortest path task; INSTALLED_BY_POST_TRAINING on both under the Hill number over all programs; MIXED on both at the planned sample size.

### 2.3.11 Positioning against the nearest published work

The audit checked each positive claim against its nearest neighbours on the arXiv abstract pages on 2026-10-20 and recorded what this run adds (Table 52). All eight arXiv identifiers were verified. The venues of two papers (ICLR 2025 for the paper on introspection, NAACL 2025 for denial prompting) are not shown on their abstract pages and are marked unverified there.

**Table 52.** Each positive claim, its nearest neighbours and what this run adds (source: `results/positioning.json`).

| Claim | Nearest neighbours | What this run adds, or replication |
|-|-|-|
| Temperature and the sampler change phrasing, not the algorithm | Temperature correlates weakly with novelty [37]; NoveltyBench [44]; approach level against surface level diversity in math reasoning [45], whose paper uses temperature only as a sampling setting | An executed, mechanism labelled measurement of algorithm choice in code across temperature, sampler and thinking mode: no change in algorithm beside a severalfold rise in phrasings. None of the three neighbours reports this measurement in code |
| Generate then select reaches several algorithms at a pass rate cost | SimpleStrat [43] | Replication in code algorithm space with the pass rate price; a ceiling row, not a knob |
| The substitute is predictable before the ban from the model's own answers | Verbalized Sampling attributes mode collapse to typicality bias [46]; introspection and simulation of own behaviour [39] | Forecasts of the realised substitute under prohibitions in code; descriptive, and no family advances under the rule |
| Internal states are organised by approach | Math reasoning organised by approach, not topic [40] | Code algorithms, prohibitions and a test of the generation time locus; the locus narrows to a paraphrase level signal (grid) and a readout after commitment (shortest path) |
| Bans recollapse on Bellman-Ford/SPFA | The inspiration repository (the specific recollapse statement was not found in its README); denial prompting [23] | Per draw counts across five independent draws with mechanism labels on an open model, and the generic perturbation rival on the same task |

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

**The substitution test: undetermined.** The between survivor variance of the ban gains is far above replicate noise (F between 16 and 22 under the neutral reference), so the model does not merely subtract. But the pooled X specific share is 0.55 with a 95% interval of [0.25, 0.67] under the neutral twin reference and 0.66 [0.49, 0.87] under the mention twin: both intervals straddle 0.5 and no ladder exists, so the preregistered branch is undetermined, and the same holds under effective sample size weighting (Table 56). The grid task alone reads X specific but unaimed under the mention reference and the weighted variant. Neither rival account fits. The X specific residuals are not aimed at the prime and veto profile (mean Spearman -0.10 against a null 95th percentile of 0.20, p = 0.80) or at the free-form association profile (-0.12, p = 0.77). And the eight generic perturbation profiles do not agree with one another, so there is no coherent ladder to be exposed (Table 57). *(Correction, iteration 3: the three readings above, that the gains are not pure subtraction, that the residuals are not aimed, and that the generic profiles form no coherent ladder, are not detectable with the current instrument; they are not findings. On the rows whose behaviour is known the X specific residual points away from the realised substitute (Dijkstra ban: Bellman-Ford/SPFA -1.84 against Dial +6.07 and Floyd-Warshall +3.68; BFS ban: DFS +0.83 against IDDFS +7.99), the argmax of the gain hits the realised landing in 0 of 17 sampled Qwen3-8B single bans while the argmax of the implied mass hits 14 of 17, no row keeps three survivors with at least 1% implied mass and an ESS of at least 5, and the bootstrap variance of the mean gain is a median 2.7 times the replicate noise that the frozen correction subtracts, which inflates both F and the share. Section 3.2.1.)*

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

*(Added in iteration 3: the ESS weighted grid share of 1.24 [0.57, 1.62] is impossible as a proportion. The noise corrected ladder term went negative (V_u = -35.4) once the weights shrank the ladder projection below its noise allowance, so V_s / (V_u + V_s) = 181.3 / 145.9 exceeds 1. The basic bootstrap intervals, which correct for the upward skew of these sums, are given in Section 3.2.1.)*

**Table 57.** Does a latent ladder exist? Agreement among the eight generic perturbation profiles and the aim of the X specific residual (source: `results/c1.json`).

| Task | Ladder exists (mean centred cosine at least 0.5) | Mean centred cosine | Mean raw cosine | Random edits, seed family A against B (r) | Nonce ban, half 1 against half 2 (r) | Aim at prime and veto | Aim p |
|-|-|-|-|-|-|-|-|
| Grid | no | 0.34 | 0.21 | 0.53 | 0.37 | -0.07 | 0.682 |
| Shortest path | no | -0.02 | -0.07 | -0.26 | 0.82 | -0.14 | 0.787 |

*(Added in iteration 3: Tables 56 and 57 omit the aim under the mention twin reference, -0.595 in Qwen3-8B. That aim is negative by construction: the mention twin enters the gain with a minus sign and the prime and veto profile with a plus sign, so shared noise in the mention cell drives the correlation negative. Simulated under the split half design the null has mean -0.27, and -0.595 lies below its 1st percentile. Section 3.2.1.)*

The per row decomposition (Table 58) shows where the X specific variance sits. The modal bans have large X specific residuals: under the BFS ban the largest residual belongs to IDDFS, under the Dijkstra ban to Dial. The bans of DFS, Bellman-Ford/SPFA, Floyd-Warshall and Dial are mostly close to the ladder (cosine of the row with the ladder profile 0.87 to 0.96). The penultimate column measures each ban's effect on its own label, and it carries the experiment's clearest result: banning an algorithm the model never writes raises that algorithm's likelihood, by +2.5 to +26.9 nats in 8 of the 9 bans of absent algorithms (IDDFS +23.5, Floyd-Warshall +15.4, Dial +26.9). Only the two modal bans (BFS -8.25, Dijkstra -4.95) and the ban of A* (-5.93) lower their own label. Naming an algorithm primes it, even inside a prohibition [7].

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

**Design.** Because each ban prompt and its neutral twin have the same token length and identical tokens from the task text onward, their key and value (KV) caches can be spliced position by position, an interchange intervention on cached states in the sense of activation patching [47]. One arm is the full ban and one the full neutral twin. In the *prompt route* arm, generated tokens see the neutral condition segment but the task specification and read position cache entries computed under the ban, so they can learn about the ban only through states that read it. In the *direct route* arm, generated tokens see the ban segment but task specification and read position entries computed under the neutral twin, so they can learn about the ban only by attending to it directly. Two further arms splice only the read position or only the task specification states. A placebo arm splices between two neutral nouns. Attention knockouts [48] block attention from generated tokens to the condition segment for all generated tokens, for the first 16 only or after the first 16, and in three bands of 12 layers; the same full knockout applied to the neutral prompt measures generic damage. The primary readout is the likelihood drop of the banned algorithm X, D_X(arm) = L_X(arm) - L_X(neutral twin), over 30 self written, name scrubbed programs per algorithm (323 forced programs in all). The route fractions are F_prompt = D_X(prompt route) / D_X(full ban) and F_direct = D_X(direct route) / D_X(full ban), with F_R and F_spec defined the same way for the read position only and task specification only arms, all bootstrapped over templates and programs. The decision rule was hash committed before any arm was scored: the ban acts directly if F_direct is at least 2/3 with an interval above 1/2, and is decided before writing if F_prompt meets the same bar. Behaviour was sampled 100 times per arm and task (five templates by 20) under common random numbers: one uniform stream per sample shared by every arm, inverse CDF sampling in vocabulary order and a constant batch shape.

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

**Where the substitute rises.** Under the full ban the survivors' likelihood gains on the grid task were DFS +9.46, IDDFS +18.40, bidirectional BFS -0.22, A* -0.80 and unit weight Dijkstra -3.53 nats; on the shortest path task Bellman-Ford/SPFA +2.53, bidirectional Dijkstra +30.64, Floyd-Warshall +12.64 and Dial +6.79. The prompt route arm reproduces this profile (cosine 0.94 [0.85, 0.99] grid, 0.95 [0.90, 0.99] shortest path); the direct route arm reproduces it on the shortest path task (0.98 [0.80, 1.00]) but not reliably on the grid task (0.71 [-0.18, 0.94]). The logit lens and a tuned lens [49] at the planned commitment token (the token after `from` or `import`) found no veto layer: the banned set's rank there is unchanged by the ban (0 of 59 grid and 0 of 60 shortest path programs), because the fork has already happened at the first token. The grid substitute set (DFS) rises from layer 28 (59 of 59 programs; tuned lens median 27). In substitute programs written under the full ban, the banned set is vetoed late (median layer 30 on the grid task, 36 on the shortest path task). The tuned lens beat the logit lens on held-out KL at all 11 probed layers (0.29 against 10.6 at layer 21).

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

## 2.6 Ban list experiment: the top five prohibition and bans that leave one survivor

**Why.** The request asks what happens when the top five algorithms are prohibited in one prompt: does the implemented algorithm move to the edge of the banned region, or to its opposite side? Iteration 1 could not reach that test through its greedy succession, because the model stopped complying after two bans. This experiment [ARTIFACT:art_IVZc3TWCeE9f] ran the prohibition as single prompt conditions, with a control for each reading of where the mass goes, and asked on the shortest path task whether the model can and will write each algorithm when it is the only one allowed.

**Catalogue extension.** The grid catalogue was extended toward the ten algorithms the request imagines: greedy best first search was split from A*, and IDA*, a 4-neighbour jump point search and bidirectional A* were added, with new references that both labellers got right (25 of 25) and targeted unit probes (4 of 4). The canonical labeller recheck gave 135 of 144 gold programs and 22 of 22 references. The 40-program gold gate of the extended labeller was missed: 33 of 40 at round 0 and 32 of 40 after the one allowed revision, runtime against AST kappa 0.53; unit weight Dijkstra, jump point search and bidirectional A* fell below three of four gold programs and were excluded. An algorithm was kept if at least 70% of its 40 forced programs were labelled as requested (Table 66). Only BFS, DFS, IDDFS, greedy best first and IDA* passed, so the extension failed. The model mostly writes A* as a cost only heap (unit weight Dijkstra 25 of 40), unit weight Dijkstra as BFS (18 of 40), and jump point search and bidirectional A* as BFS and A*. The analysis catalogue (seven algorithms) kept A* and bidirectional BFS, flagged, because each has at least 10 programs and passes the gold set. With seven algorithms the frozen set rule gives four name sets: TOP (the four with the highest baseline likelihood: BFS, DFS, greedy, IDDFS), ARC (four contiguous on the manifold: BFS, bidirectional BFS, A*, greedy) and SCATTER (four spread out: BFS, DFS, greedy, IDA*). The literal ban of five names, TOP5 (BFS, DFS, greedy, IDDFS, A*), was added. Six landing forecasts per set (ladder, prime and veto, proximity, likelihood under the ban, generic perturbation, corpus frequency) were hash chained before the ban lists were sampled, and the chain verifies.

**Table 66.** Keep rule for the extended catalogues: forced programs labelled as requested (source: `results/catalogue_keep.json`; 40 forced programs each).

| Task | Algorithm | Forced prompt | Labelled as requested | Of those, passing | Other labels | Kept |
|-|-|-|-|-|-|-|
| Grid | BFS | plain | 40 | 38 | none | yes |
| Grid | DFS | plain | 40 | 9 | none | yes |
| Grid | IDDFS | plain | 37 | 0 | DFS 3 | yes |
| Grid | greedy best first | plain | 35 | 25 | BFS 2, other 2, A* 1 | yes |
| Grid | IDA* | descriptive | 36 | 0 | A* 3, BFS 1 | yes |
| Grid | bidirectional BFS | plain | 21 | 5 | BFS 16, other 3 | no (kept in analysis, flagged) |
| Grid | A* | plain | 11 | 11 | unit weight Dijkstra 25, other 3, BFS 1 | no (kept in analysis, flagged) |
| Grid | unit weight Dijkstra | plain | 13 | 11 | BFS 18, other 9 | no |
| Grid | jump point search | descriptive | 7 | 0 | BFS 21, other 11, unit weight Dijkstra 1 | no |
| Grid | bidirectional A* | descriptive | 5 | 0 | A* 28, BFS 3, other 3, bidirectional BFS 1 | no |
| Shortest path | Dijkstra | plain | 40 | 40 | none | always run |
| Shortest path | Bellman-Ford/SPFA | plain | 40 | 34 | none | always run |
| Shortest path | bidirectional Dijkstra | descriptive (corrected in iteration 3 from plain; the plain prompt gave 10 programs, Dijkstra 9) | 14 | 9 | Dijkstra 22, other 4 | always run |
| Shortest path | Floyd-Warshall | plain | 40 | 40 | none | always run |
| Shortest path | Dial | descriptive (corrected in iteration 3 from plain; the plain prompt gave 10 programs) | 36 | 7 | other 4 | always run |

**Every ban list fails.** With one name banned the model complies (avoidance 0.86 on the grid task, 0.84 on the shortest path task). With four or five names it mostly writes a banned algorithm anyway (Table 67): avoidance is 0.13 for TOP, 0.37 for ARC, 0.04 for SCATTER and 0.00 for the literal ban of five names, so every ban list fails the event gate. The banned programs are BFS and DFS reimplemented, often without naming their mechanism (Table 68). We call a banned mechanism program *disguised* when its comments and identifiers never name its own mechanism; 41% to 92% of the banned programs under a ban list are disguised, DFS most often as `backtracking`. The likelihoods committed before sampling foresaw the failure for three of the four sets: the implied avoidance was below 1e-8 for TOP, SCATTER and the five name ban, against realised 0.13, 0.04 and 0.00. For ARC the implied avoidance was 0.9995 against a realised 0.37. A ban prompt raised the likelihood of the banned algorithms' own programs relative to the neutral twin (DFS gained about 10 nats under the first template of TOP), the same priming as in the likelihood screen.

**Table 67.** Grid ban lists and the single name references (N = 100 each, five templates by 20; mechanism labels of attempted programs; source: `results/landing.json`).

| Condition | Banned | Landing (attempted programs) | Avoidance [Wilson 95%] | Template cluster 95% CI | Avoidance per template (first to fifth) | Pass rate |
|-|-|-|-|-|-|-|
| Grid baseline | none | BFS 100 | n/a | n/a | n/a | 0.89 |
| Grid single ban | BFS | DFS 86, BFS 14 | 0.86 [0.78, 0.91] | [0.58, 1.00] | 1.0, 1.0, 1.0, 0.30, 1.0 | 0.41 |
| TOP | BFS, DFS, greedy, IDDFS | BFS 59, DFS 26, greedy 2, other 13 | 0.13 [0.08, 0.21] | [0.01, 0.29] | 0.15, 0.05, 0.0, 0.0, 0.45 | 0.40 |
| ARC | BFS, bidirectional BFS, A*, greedy | BFS 63, DFS 37 (DFS allowed) | 0.37 [0.28, 0.47] | [0.09, 0.68] | 0.70, 0.15, 0.15, 0.0, 0.85 | 0.60 |
| SCATTER | BFS, DFS, greedy, IDA* | BFS 69, DFS 27, A* 2, other 2 | 0.04 [0.02, 0.10] | [0.00, 0.08] | 0.0, 0.10, 0.0, 0.0, 0.10 | 0.75 |
| TOP5 (literal) | BFS, DFS, greedy, IDDFS, A* | BFS 63, DFS 36, IDDFS 1 | 0.00 [0.00, 0.04] | [0.00, 0.00] | 0.0, 0.0, 0.0, 0.0, 0.0 | 0.68 |
| Shortest path baseline | none | Dijkstra 100 | n/a | n/a | n/a | 1.00 |
| Shortest path single ban | Dijkstra | Bellman-Ford/SPFA 83, Dijkstra 16, other 1 | 0.84 [0.76, 0.90] | [0.72, 0.95] | 0.90, 0.95, 0.70, 0.65, 1.0 | 0.95 |

*(Correction, iteration 3: TOP's avoidance of 0.13 is labeller residue, not avoidance into a catalogue algorithm. Its 13 programs not banned are all labelled other: 12 failing programs that both blind judges classed as degenerate BFS or DFS variants, and 1 correct unit weight Dijkstra outside the K = 7 analysis catalogue. Avoidance into a non-banned catalogue algorithm is 0.00 for TOP, 0.37 for ARC, 0.02 for SCATTER and 0.00 for TOP5. The share labelled other is reported separately from avoidance in Section 3.2.3.)*

**Table 68.** Disguise: banned mechanism programs that never name their own mechanism (source: `results/landing.json`).

| Condition | Banned mechanism programs | Disguised | Disguise rate | By mechanism (disguised / programs) | Most frequent self descriptions |
|-|-|-|-|-|-|
| Grid single ban of BFS | 14 | 14 | 1.00 | BFS 14/14 | none named |
| Shortest path single ban of Dijkstra | 16 | 2 | 0.125 | Dijkstra 2/16 | none named |
| ARC | 63 | 58 | 0.92 | BFS 58/63 | `is_valid` 2 |
| SCATTER | 96 | 49 | 0.51 | BFS 43/69, DFS 6/27 | `backtrack` 10, `is_valid` 7, `depth-limited` 1 |
| TOP | 87 | 44 | 0.51 | BFS 37/59, DFS 6/26, greedy 1/2 | `backtrack` 10, `is_valid` 9 |
| TOP5 | 100 | 41 | 0.41 | BFS 34/63, DFS 6/36, IDDFS 1/1 | `is_valid` 10, `backtrack` 8, `find_path` 2 |

[FIGURE:fig_multiban]

**The list's content barely matters (post hoc).** Across the four ban lists the model writes the same mix of BFS and DFS: the BFS share among BFS and DFS programs is 0.69 (TOP), 0.63 (ARC), 0.72 (SCATTER) and 0.64 (TOP5), chi squared p = 0.48 and permutation p = 0.57. This holds whether DFS is on the list (TOP, SCATTER, TOP5) or allowed (ARC). Avoidance differences therefore come from whether DFS happens to be banned, not from a list specific landing. A single BFS ban moves the model to DFS 86%; a list of four or five names moves it to about one third DFS, which looks more like a generic perturbation of the default than a veto. This comparison was not preregistered.

**Landing tests are degenerate.** Only ARC (37 DFS programs) and SCATTER (2 A* programs) put any mass on a survivor. On ARC the ladder, prime and veto, likelihood, generic perturbation and corpus forecasts all named DFS (log score +1.06 nats per program over uniform), and proximity named IDA* and missed (-0.02). With three survivors the exact permutation floor is 1/6, every per set p is at least 0.33, and every pooled p is at least 0.11; the edge against opposite statistic was 0 on both sets with mass (p = 0.67). The request's literal question therefore has a behavioural answer that is neither of its two options: under a four or five name ban the model does not move to the edge or to the opposite side of the banned region, it reimplements the banned defaults. Over all programs, predicting no change from the default algorithm was right for 64% of programs under a ban list, against at most 10% for any committed survivor forecast; on single bans the highest ranked not banned algorithm predicted 85% and the default 15%; under forced prompts the requested algorithm was written 66% of the time.

**Bans that leave one survivor: can against will.** On the shortest path task each of the five algorithms was left as the only one allowed, by banning the other four (Table 69). The model writes Dijkstra when it is the survivor 95% of the time and Bellman-Ford/SPFA 51% of the time. It writes bidirectional Dijkstra, Floyd-Warshall and Dial 0% of the time, falling back to the banned Dijkstra or Bellman-Ford/SPFA instead, although when forced it writes Floyd-Warshall correctly 40 of 40 times and Dial 36 of 40 times. The likelihood gains follow the same split: banning the other four lowers Dijkstra by 3.35 nats and Bellman-Ford/SPFA by 0.21 when each is the survivor, and raises the three algorithms the model never writes by 7.6 to 24.3 nats without moving them into the sample.

**Table 69.** Shortest path bans that leave one survivor (N = 100 each; will is the share of programs implementing the survivor and can the share of 40 forced programs labelled as the survivor; source: `results/los.json`).

| Survivor (other four banned) | Will [Wilson 95%] | Banned mechanisms written | Other | Compliant share | Can (forced labelled as requested; forced pass) | Mean likelihood gain of the survivor (nats) | Disguised / banned programs |
|-|-|-|-|-|-|-|-|
| Dijkstra | 0.95 [0.89, 0.98] | Bellman-Ford/SPFA 0.05 | 0.0 | 0.95 | 1.00; 1.00 | -3.35 | 4 / 5 |
| Bellman-Ford/SPFA | 0.51 [0.41, 0.61] | Dijkstra 0.48 | 0.01 | 0.39 | 1.00; 0.85 | -0.21 | 8 / 48 |
| bidirectional Dijkstra | 0.00 [0.00, 0.04] | Dijkstra 0.52, Bellman-Ford/SPFA 0.48 | 0.0 | 0.0 | 0.35; 0.225 | +24.26 | 51 / 100 |
| Floyd-Warshall | 0.00 [0.00, 0.04] | Dijkstra 0.59, Bellman-Ford/SPFA 0.40 | 0.01 | 0.0 | 1.00; 1.00 | +7.63 | 46 / 99 |
| Dial | 0.00 [0.00, 0.04] | Dijkstra 0.52, Bellman-Ford/SPFA 0.44 | 0.04 | 0.0 | 0.90; 0.175 | +21.20 | 42 / 96 |

**Geometry and natural run internals.** In the teacher forced residual stream, centroid MDS stress-1 was 0.025 (grid) and 0.006 (shortest path). The nearest neighbours were BFS with bidirectional BFS, DFS with IDDFS, and A* with greedy best first; nearest neighbour stability was 0.70 across settings and 0.96 under a program bootstrap. Persistent homology, which tracks loops in a point cloud across distance scales, found no persistent loop on either task. *(Correction, iteration 3: this sentence originally read the result as a negative answer to the request's question about a circle. It is no evidence of a loop, at weak power, at a label-dependent position. These clouds sit at the token before the commit token, a position that depends on the label; there a planted loop is found with power 1.00, while at the label-independent generated token 16 the power is 0.04. The nearest pair at that position, BFS and bidirectional BFS (centroid distance 0.0147), does not survive at token 16: permuted labels reproduce the adjacency with p = 0.19 and the two clouds are not separable. The experiment drew 13 Isomap figures with centroids sized by implemented count, which this section did not show; they are reported with their counts in Section 3.2.2.)* Probes within one ban prompt at generated token 16, a position that does not depend on the label, were near chance on every grid condition and reached balanced accuracy 0.69 (p = 0.03) on the shortest path ban that leaves only Bellman-Ford/SPFA. Probes at the token before the commit token were confounded, because that position depends on the label. The difference-in-means direction from forced programs aligned with the natural within one ban direction at that position (cosine 0.6 to 0.95) and on the shortest path task at token 16 (0.3 to 0.99), but not for the grid BFS ban at token 16 (-0.13 to -0.01).

**Deviations and cost.** The experiment ran on an RTX 4090 in eager vLLM mode (no C compiler), replaced one duplicated forced paraphrase, missed the gold gate after its revision, and recorded bf16 scoring path noise of about 1 nat per program; the shortest path likelihoods sum to 0.17, below the 0.3 calibration floor; the second noun placebo ran after the ban lists were sampled. It used about 1 GPU hour and USD 0.42 of judge calls (857 calls).

## 2.7 Llama replication: the same protocol in a second model family

**Why.** A claim about what a ban does inside one model needs a second family. This experiment [ARTIFACT:art_-QPYRaFERCBX] ran shared protocol v2 on Llama-3.1-8B-Instruct [22] in bf16 with its default chat template, on the canonical suite, retokenising the neutral noun bank under Llama. It drew 1,780 seeded vLLM generations: baselines, modal bans, mention twins, listing controls, two bans of algorithms other than the default and two double bans per task (14 events), 880 forced programs and 220 free-form answers. It scored 248 name scrubbed forced programs in 39,768 program scores (11.3 million tokens). Nothing was tuned to agree with Qwen3-8B.

**Llama's baseline is not collapsed on the grid task.** *(Correction, iteration 3: true of attempted programs only. All 20 correct grid baseline programs are BFS, a correctness conditioned Hill number of 1.00 against 1.87 over attempts, so Llama's correct grid output is as collapsed as Qwen3-8B's; correct-only compositions of every Llama event are in Section 3.2.4.)* It writes BFS 77 times and DFS 20 times in 100, with a low pass rate (0.20). On the shortest path task it is collapsed (Dijkstra 92, pass rate 0.59). The BFS ban sends it to DFS 63 of 100; the Dijkstra ban sends it to Dijkstra 43, other labels 37 and Bellman-Ford/SPFA 18. Both double bans fail the gate (Table 70). Bidirectional Dijkstra and Dial could not be written (2 and 1 forced programs kept after up to 120 attempts), so the shortest path catalogue has three algorithms, no row there has three survivors, and the substitution test runs on the grid task only.

**Table 70.** The 14 sampled Llama events (mechanism labels of attempted programs; source: `results/events.json`).

| Task | Event | N | Labels | Banned share | Avoidance | Compliant share | Clear mode | Gate |
|-|-|-|-|-|-|-|-|-|
| Grid | baseline | 100 | BFS 77, DFS 20, other 3 | 0.0 | 1.0 | 0.20 | BFS | pass |
| Grid | ban BFS (modal) | 100 | DFS 63, BFS 29, other 6, A* 1, unit weight Dijkstra 1 | 0.29 | 0.71 | 0.08 | DFS | pass |
| Grid | mention BFS | 50 | BFS 47, other 2, DFS 1 | 0.0 | 1.0 | 0.28 | BFS | pass |
| Grid | listing control | 50 | BFS 36, other 7, DFS 6, unit weight Dijkstra 1 | 0.0 | 1.0 | 0.20 | BFS | pass |
| Grid | ban DFS | 50 | BFS 39, DFS 7, other 4 | 0.14 | 0.86 | 0.14 | BFS | pass |
| Grid | ban unit weight Dijkstra (absent) | 50 | BFS 30, DFS 18, unit weight Dijkstra 1, other 1 | 0.02 | 0.98 | 0.26 | BFS | pass |
| Grid | ban BFS and DFS | 50 | BFS 21, DFS 21, other 6, unit weight Dijkstra 2 | 0.84 | 0.16 | 0.0 | none | fail |
| Shortest path | baseline | 100 | Dijkstra 92, other 7, Bellman-Ford/SPFA 1 | 0.0 | 1.0 | 0.59 | Dijkstra | pass |
| Shortest path | ban Dijkstra (modal) | 100 | Dijkstra 43, other 37, Bellman-Ford/SPFA 18, Floyd-Warshall 2 | 0.43 | 0.57 | 0.05 | none | pass |
| Shortest path | mention Dijkstra | 50 | Dijkstra 39, other 11 | 0.0 | 1.0 | 0.46 | Dijkstra | pass |
| Shortest path | listing control | 50 | Dijkstra 19, Bellman-Ford/SPFA 15, other 14, Floyd-Warshall 2 | 0.0 | 1.0 | 0.24 | none | pass |
| Shortest path | ban Bellman-Ford/SPFA | 50 | Dijkstra 33, other 14, Bellman-Ford/SPFA 2, Floyd-Warshall 1 | 0.04 | 0.96 | 0.26 | Dijkstra | pass |
| Shortest path | ban Floyd-Warshall (absent) | 50 | Dijkstra 25, other 11, Bellman-Ford/SPFA 9, Floyd-Warshall 5 | 0.10 | 0.90 | 0.14 | Dijkstra | pass |
| Shortest path | ban Dijkstra and Bellman-Ford/SPFA | 50 | Dijkstra 22, other 21, Bellman-Ford/SPFA 6, Floyd-Warshall 1 | 0.56 | 0.44 | 0.0 | none | fail |

*(Added in iteration 3: Table 70 lists attempted programs only. Correct programs: grid baseline BFS 20; ban BFS DFS 7, other 1; mention BFS BFS 14; listing control BFS 7, DFS 3; ban DFS BFS 7; ban unit weight Dijkstra BFS 12, DFS 1; shortest path baseline Dijkstra 59; ban Dijkstra Bellman-Ford/SPFA 4, other 1; mention Dijkstra Dijkstra 22, other 1; listing control Dijkstra 9, Bellman-Ford/SPFA 3; ban Bellman-Ford/SPFA Dijkstra 13; ban Floyd-Warshall Dijkstra 6, Bellman-Ford/SPFA 1; both double bans 0. Table 89, Section 3.2.4.)*

**The validity gate fails, and the substitution test is unresolved.** Calibration fails on the grid task: the instrument implies BFS 0.43 and DFS 0.55 against a sampled BFS share of 0.77 (Wilson [0.68, 0.84]); the shortest path task passes (Dijkstra 0.97, sum 0.87). Discrimination passes at 0.59 nats per program over uniform across 13 events (1.0 to 1.6 nats on the grid ban and mention events, 0.1 to 0.8 on the shortest path ones, negative for both listing controls). The argmax matches the realised mode in 7 of 10 clear mode events, below the 0.8 bar; all three misses are on the grid task, where the instrument predicts DFS and sampling lands on BFS. The median cell ESS is 2.5 and 76% of cells are below 5. Under the neutral reference the X specific share is 0.80 with a 95% percentile interval of [0.28, 0.94], with no aim and no ladder, so the result is not resolved at this sample size; under the mention reference it reads X specific but unaimed (Table 71). The branch is not robust. Outside the frozen rule, the program level importance sampling noise dominates: the bootstrap variance of the mean gain is 5 to 11 times the replicate variance the frozen correction subtracts, the basic interval for the neutral V_u + V_s is [-15.1, 10.2] and covers zero, and the share falls to 0.41 without the five forced programs that the label audit disputed and to 0.44 with a raw mean ladder profile.

**Table 71.** Llama substitution test, grid task only (source: `results/c1.json`).

| Reference | X specific share (95% percentile CI) | V_u / V_s / V_u + V_s | Aim at prime and veto (null 95th pct; p) | Ladder exists (mean cosine) | Branch |
|-|-|-|-|-|-|
| neutral twin (primary) | 0.80 (0.28, 0.94) | 2.0 / 8.2 / 10.1 | 0.067 (0.258; p = 0.35) | no (0.14) | not resolved at this N |
| mention twin (secondary) | 0.78 (0.61, 0.91) | 7.1 / 25.5 / 32.6 | -0.28 (p = 0.96) | no | X specific but unaimed |

The association aim did not pass either (-0.08 against a null 95th percentile of 0.30).

**Llama, like Qwen3-8B, primes the banned name.** Naming an absent algorithm in a ban raised its own likelihood in 5 of 6 cases: bidirectional BFS +3.9 nats, IDDFS +7.6, unit weight Dijkstra +1.8, Bellman-Ford/SPFA +4.1 and Floyd-Warshall +4.8; A* was the exception (-1.2). The mention twin primes these algorithms by +6.7 to +14.4 nats and the ban's veto (-4.9 to -10.1) cancels only part of the prime. Bans of present algorithms do lower them: BFS -1.7, DFS -3.0 and Dijkstra -1.0. Within a ban row, the X specific residual is negatively correlated with how much a survivor's code resembles X (Spearman -0.6 to -0.9 in 5 of 6 grid rows): a ban lowers the survivors that look like the banned algorithm.

**The route, read by likelihood only.** On the two modal bans (20 cells), the ban's drop on the default (-27.2 nats summed) travels mostly by the prompt route: F_prompt 0.84 (bootstrap interval 0.62 to 1.46) and F_direct -0.21 (-1.03 to 0.09). On the grid task the prompt route arm also reproduces the full ban's redistribution over survivors (cosine 0.98); the direct route arm does not (0.20).

**Which forecast predicts the program written?** Over 743 attempted samples not banned the empirical sampled ladder predicted the realised mechanism best (Table 72). The likelihood forecast lost to it overall (difference -0.11, paired sign flip p < 1e-4) and tied it on single bans (+0.01, p = 0.71). Asked for the standard alternative, Llama answers DFS 20 of 20 times for BFS and Bellman-Ford/SPFA 19 of 20 times for Dijkstra; its top-1 answers match the OpenRouter Llama map of iteration 1 for 9 of 11 algorithms.

**Table 72.** Per-sample top-1 accuracy of each predictor against the realised mechanism label (source: `results/independent_rederivation_headlines.json`).

| Predictor | All 743 samples | Single bans (313 samples) |
|-|-|-|
| likelihood (FRLP) top-1 | 0.59 | 0.67 |
| empirical sampled ladder | 0.70 | 0.67 |
| free-form association | 0.52 | 0.67 |
| latent ladder from baseline likelihoods | 0.51 | 0.63 |

**Checks.** The canonical labeller recheck reproduced the association experiment exactly (22 of 22 references, combined against adjudicated 0.966, runtime against AST kappa 0.753). A blind audit of 50 Llama programs by a second judge agreed with the final labels at 0.78 (grid 0.74, shortest path 0.87), below 0.9 and flagged; most disputes were flawed attempts the audit judge labelled as other. HF and vLLM scores agreed within 0.003 to 0.007 nats per token. KV cache reuse failed its 0.02-nat tolerance (mean 0.16, maximum 0.40 nats per program, bf16 batch shape numerics), so an fp32 language model head was adopted. For 91% of forced prompts an algorithm's own likelihood lay in [-0.7, 0.2]; the default's likelihood matched its log sampled share within 0.11 nats on the shortest path task but was 0.59 nats off on the grid task, where the instrument under weights BFS. Independent rederivations matched 34 of 34 quantities and 63 of 63 headline numbers, and a random predictor placebo never beat the ladder. Cost: USD 0.49 of OpenRouter calls and 0.64 logged GPU hours on one RTX 4090. Table 72b lists every test the replication ran.

**Table 72b.** Tests of the Llama replication (source: the artifact's `README.md` test table and the `results/*.json` files it names).

| Test | Result |
|-|-|
| Labeller recheck and label audit | pass (22/22 references, combined against adjudicated 0.966); blind audit of 50 Llama programs 0.78, flagged |
| Prompts | pass: 71/71 task texts equal the association experiment's; one BOS token; identical task suffix; ban and neutral twins of equal length (at most 13 filler tokens, no token level insertion); sampled token ids equal scored ids for 140 conditions |
| Engine agreement | pass: HF against vLLM 0.003 to 0.007 nats per token, program sums within 0.14 to 0.49 nats; 97% of outputs a single fenced code block, 94% exact retokenisation |
| KV cache reuse | fails the 0.02-nat tolerance: mean 0.16, maximum 0.40 nats per program (bf16 batch shape numerics; fp32 language model head adopted) |
| Scrubber | pass: 244 of 248 forced programs keep pass status and label after the full scrub, 4 after the conservative scrub, 8 unparsable originals dropped; on about 1,400 external programs every residual name is an attribute name |
| Likelihood sanity | an algorithm's own likelihood under its forced prompts lies in [-0.7, 0.2] for 91% of forced prompts; the default's likelihood matches its log sampled share within 0.11 nats on the shortest path task and is 0.59 nats off on the grid task |
| Edit hooks | zero coefficient leaves states exactly unchanged; no change outside the edited span or before the layer band; displacement within 4.3% of target (bf16), not 1e-3 |
| Hybrid caches | pass (difference 0.0) |
| Analysis on synthetic data | pass: ladder, substitution and pure subtraction recovered; uniform aim p under the null; unbiased under exchangeable noise, biased under crossed noise (hence a template mean sensitivity) |
| Independent rederivation | 34 of 34 quantities match to 1e-9; placebo p uniform (KS p = 0.61) |
| Headline rederivation | 63 of 63 headline numbers match by a separate code path; the sampled ladder beats the likelihood forecast overall (-0.112, p < 1e-4) and ties it on single bans (+0.010, p = 0.71); a random predictor placebo never beats the ladder |

## 2.8 Bench build: a frozen 12-task confirmation bench behind a presence pilot

**Why.** The review's arithmetic called for events, not predictors, and the hypothesis update needed tasks with a present minor algorithm so that present minor bans and a nondegenerate typicality forecast could exist. This artifact [ARTIFACT:art_0ndRfWKBWclR] built the bench and ran a cheap baseline pilot before freezing any task. No ban prompt was rendered anywhere in it: an audit of 4,310 rendered prompts against a superset ban lexicon found no hit.

**Design.** Thirteen tasks derived from LeetCode [12] received a frozen specification in new wording on the canonical scaffold, a catalogue of three to six algorithms (54 in all), 684 hidden tests in total (parsed dataset cases filtered to the specification's bounds, plus generated edge and stress cases), order free checkers where the answer is a set, and one verified reference per algorithm. Every reference passes at no more than a quarter of the per case limit, which is the larger of 1 s and ten times the fastest reference; all 39 planted mutants fail. Each task has a runtime signature labeller backed by an AST labeller, with a blind judge only on disagreement, gated against a gold set adjudicated by two judges and a tiebreaker (Cohen's kappa of at least 0.8, all references correct, runtime against adjudicated of at least 0.90). Qwen3-8B ran from its official 8-bit floating point checkpoint through the 8-bit Marlin kernels of vLLM, because the 16 GB GPU could not hold bf16 weights; decoding was T = 1.0, top-p 1.0, thinking off. Each task received a 50-sample pilot, 20 free-form answers per algorithm to the question `What is the standard alternative to X for this task?`, and at least 40 forced, name scrubbed programs per algorithm, scored by vLLM prompt log probabilities to give baseline likelihoods (corrected for adherence: L_corr = L + log adherence). Tasks were ordered by how much the ladder, association and proximity nominations disagree (Stage A, committed before gating) and the first 12 gated tasks were frozen with sha256 commitments.

**Table 73.** The 13 candidate tasks (source: `README.md` main table, `results/gate_summary.json`, `results/pilot_stats.json`, `results/frlp_validity.json`, `results/stageA_nominations.json`).

| Task | K | Tests | Gate: kappa runtime vs AST [95% CI] / PABAK / runtime vs adjudicated | Qwen pilot: modal algorithm (share, pass) | Baseline likelihood of the modal algorithm | Best alternative (likelihood) | Sum of exp(likelihood) | Association / proximity nomination | Llama-3.1-8B pilot modal (share) | Status |
|-|-|-|-|-|-|-|-|-|-|-|
| kth smallest | 6 | 60 | 0.95 [0.84, 1.00] / 0.96 / 0.96 | full sort (1.00, 1.00) | -0.18 | quickselect (-1.5) | 1.05 | quickselect / heapify and pop | heapify and pop (0.34) | frozen |
| two sum | 4 | 44 | 0.92 [0.75, 1.00] / 0.94 / 0.95 | hash map (1.00, 1.00) | -0.40 | sort and two pointers (-15.5) | 0.67 | sort and two pointers / brute force | hash map (0.96) | frozen |
| find duplicate | 5 | 54 | 1.00 [1.00, 1.00] / 1.00 / 1.00 | hash set (1.00, 1.00) | 0.02 | sort, adjacent check (-12.4) | 1.02 | Floyd cycle detection / sort, adjacent check | hash set (0.43) | frozen |
| top-k frequent | 4 | 38 | 0.84 [0.60, 1.00] / 0.88 / 0.91 | sort by count (1.00, 0.94) | -0.10 | bucket sort (-15.4) | 0.91 | heap / heap | heap (0.64) | frozen |
| connected components | 4 | 57 | 1.00 [1.00, 1.00] / 1.00 / 1.00 | union find (1.00, 1.00) | -0.15 | DFS (-21.8) | 0.86 | DFS / label propagation | union find (0.77) | frozen |
| Fibonacci | 4 | 36 | 0.85 [0.65, 1.00] / 0.89 / 0.91 | iteration (1.00, 1.00) | -0.02 | fast doubling (-11.4) | 0.98 | matrix power / fast doubling | matrix power (0.79) | frozen |
| substring search | 6 | 58 | 0.95 [0.82, 1.00] / 0.96 / 1.00 | naive (1.00, 1.00) | 0.24 | KMP (-14.3) | 1.28 | KMP / Horspool | naive (0.53) | frozen |
| longest increasing subsequence | 3 | 57 | 1.00 [1.00, 1.00] / 1.00 / 1.00 | quadratic DP (1.00, 1.00) | -0.86 | patience sorting with bisect (-14.4) | 0.42 | patience sorting / patience sorting | quadratic DP (0.90) | frozen |
| merge intervals | 3 | 59 | 1.00 [1.00, 1.00] / 1.00 / 0.95 | sort and sweep (1.00, 1.00) | 0.74 | union find (-35.5) | 2.09 | interval tree / union find | sort and sweep (1.00) | frozen |
| nonoverlapping intervals | 4 | 53 | 0.89 [0.63, 1.00] / 0.94 / 0.91 | greedy by end (1.00, 1.00) | -0.83 | DP with bisect (-28.1) | 0.44 | DP with bisect / DAG longest path | greedy by end (0.56) | frozen |
| cycle detection | 4 | 59 | 0.92 [0.73, 1.00] / 0.94 / 0.95 | DFS with parent (1.00, 0.92) | 2.39 | union find (-14.2) | 10.9 | union find / union find | DFS with parent (0.59) | excluded (13th gated; 12-task cap) |
| topological order | 4 | 53 | 1.00 [1.00, 1.00] / 1.00 / 0.95 | Kahn (1.00, 1.00) | 2.44 | DFS postorder (-27.2) | 11.4 | DFS postorder / source removal | Kahn (0.98) | frozen |
| first and last position | 3 | 56 | 0.90 [0.61, 1.00] / 0.93 / 0.95 | binary search (0.98, 0.98) | 0.80 | bisect module (-12.6) | 2.21 | bisect module / exponential search | binary search (1.00) | frozen |

**Qwen3-8B is fully collapsed on all 13 tasks.** The modal share is 50 of 50 everywhere except first and last position (49 of 50), Wilson [0.929, 1.0], and the correctness conditioned Hill number is 1.0 on every task. No task has a minor algorithm at 10% or more, although the presence check is weak at N = 50 (a true share of 0.10 reaches 5 of 50 with probability about 0.57). The pilot pass rate is at least 0.92 on every task. The collapse is specific to the model: Llama-3.1-8B-Instruct, run with the same specifications and decoding, splits over several algorithms on kth smallest (heapify and pop 0.34, size k heap, full sort and quickselect), substring search (naive 0.53) and find duplicate (hash set 0.43), and passes far fewer tests. *(Correction, iteration 3: these Llama shares are of attempted programs. Its 10 correct kth smallest programs are full sort 6, heapify and pop 2, quickselect 1 and size k heap 1, so its correct mode equals Qwen3-8B's; correct-only diversity appears on substring search (naive 18, KMP 5, Rabin-Karp 1), connected components (union find 30, DFS 5), cycle detection (union find 7, DFS with parent 4) and top-k frequent (heap 8, sort by count 4), at small N. Rarefied to 10 correct programs, Llama is more diverse than Qwen3-8B on 9 of 13 tasks. Table 90, Section 3.2.4.)* The presence pilot therefore removes the present minor stratum for Qwen3-8B on every candidate task: confirmation on this bench must rest on likelihood matrices and on modal bans for Qwen3-8B, and Llama is where sampled present minor bans exist.

**Labeller, likelihoods and nominations.** All 13 tasks passed the labeller gate, 11 at round 0 and two (kth smallest, merge intervals) after one revision round with a fresh holdout (5 of 6 and 6 of 6). Both labellers got all 54 references right; runtime and AST labels agreed on 0.91 of 3,230 Qwen attempts, and the judge was needed on 8.4%. The baseline likelihood's argmax equals the pilot mode on 13 of 13 tasks, its log score beats uniform on every task (for example -0.06 against -1.61 on two sum), and the sum of exp(likelihood) lies in [0.3, 3] on 11 of 13 (cycle detection and topological order overshoot, an importance sampling overestimate under low ESS). Of the 54 cells, 34 have Kish ESS below 5. One cell stands out: quickselect on kth smallest has likelihood -1.5 (about 0.21 latent mass) while the pilot drew it 0 of 50 times. The free-form association answers are close to deterministic (the alternative to a full sort is quickselect 20 of 20 times); proximity nominates a different algorithm from association on 10 of 13 modal events; and under total collapse the sampled ladder ties over all survivors. The order recomputed after the likelihoods (Stage B) agrees with Stage A at Kendall tau 0.54. Forced adherence limits the exotic algorithms: 45 of 54 have adherence of at least 0.5, and the lowest are topological layering (0.04) and source removal (0.10), the interval tree (0.24), the DP variants of nonoverlapping intervals (0.28), index marking (0.28) and label propagation (0.29).

**Deviations and what was not done.** Scoring used vLLM prompt log probabilities instead of HF; single request and batched scoring disagreed by 0.62 nats on 1 of 5 checked programs (the others within 0.015). The forced proposal used five paraphrases over eight rounds instead of ten over four. Not produced: the unscrubbed scoring sensitivity that the likelihood screen recommended, Llama forced programs and likelihoods, ban, mention and neutral likelihood matrices, and any sampled ban event. Cost: about 1.4 GPU hours on one RTX 2000 Ada and USD 0.14 of judge calls (1,124 calls). *(Added in iteration 3: the frozen baseline likelihoods are therefore not commensurable with the screen's, which had to move to fp32 activations because bf16 moved per program log likelihoods by up to 2.1 nats; and the recommendation to score unscrubbed programs is validated only on baseline, mention and listing events, not on ban rows, where names left in identifiers interact with the ban's own naming. Rescored on the fp32 path in iteration 3, the bench cells moved by a median 0.88 nats with the argmax unchanged on 12 of 12 tasks; Section 3.3.)*

## 2.9 Readout experiment: the ban inside the model

**Why.** The request asks for internals read with sparse autoencoders, thought anchors and lenses, and for the literal same seed test of temperature. This experiment [ARTIFACT:art_3iv5G76C3yoX] ran those readouts on the modal bans of the two path search tasks, each beside a matched baseline on identical rows and folds. Everything in it is descriptive.

**A fresh ban pool.** Under protocol v2 (five templates by 20 samples per task), the banned share was 0.15 on the grid task (Wilson [0.09, 0.23]) and 0.13 on the shortest path task ([0.08, 0.21]); both events pass the gate. On the grid task the fourth template gave BFS 15 of 20 times and every other template 0 of 20, the third independent draw in which that one template fails (Sections 2.5 and 2.6).

**The SAE transfer test failed.** The sparse autoencoders used were Qwen-Scope's, trained on Qwen3-8B-Base and covering all 36 layers [50] (64K latents, top-k activation with k = 50 [51]). Before using them on the instruct model, the experiment spliced their reconstructions into the residual stream at layers 15, 20 and 27 and compared the increase in cross-entropy over 200 instruct model sequences with the increase on the base model; the preregistered bar was a ratio of at most 1.5. It failed at all three layers (Table 74). Reconstruction error was similar in the two models, but the instruct model's clean cross-entropy on its own code is far lower (0.030 against 0.260 nats), so the same error costs more. Every latent result below is labelled as computed on out-of-distribution activations, and the difference-in-means baselines lead.

**Table 74.** SAE transfer test: increase in cross-entropy when SAE reconstructions are spliced in (source: `results/transfer_summary.json`; ratio intervals 95%).

| Layer | Increase, instruct | Increase, base | Ratio [95% CI] | Pass (ratio at most 1.5) | Relative MSE instruct / base | Fraction of variance unexplained instruct / base | Cosine instruct / base |
|-|-|-|-|-|-|-|-|
| 15 | 0.173 | 0.053 | 3.29 [3.14, 3.45] | no | 0.196 / 0.165 | 0.366 / 0.288 | 0.896 / 0.914 |
| 20 | 0.150 | 0.077 | 1.95 [1.84, 2.06] | no | 0.230 / 0.203 | 0.094 / 0.243 | 0.877 / 0.893 |
| 27 | 0.097 | 0.061 | 1.59 [1.50, 1.67] | no | 0.229 / 0.197 | 0.153 / 0.325 | 0.877 / 0.896 |

**Readouts of the algorithm written.** On the forking token experiment's saved states, with nested selection that holds out one paraphrase at a time, 200 within paraphrase permutations and a maximum statistic null, the shortest path contrast (Dijkstra against Bellman-Ford/SPFA, same prompts) is decodable at the token before the commit token and at token 16 by every method, with within paraphrase held-out AUC 0.67 to 0.86 and permutation p at most 0.025 (Table 75). The grid contrast (BFS against DFS) is not decodable within paraphrase at the commitment point: most p values exceed 0.05, no latent passes the maximum statistic null, and only 57 within paraphrase pairs exist. SAE latents never beat the difference-in-means direction or the top raw dimensions by a margin outside the intervals, which matches AxBench [34] and the MIB benchmark [52]. The positive control was weak (within paraphrase AUC at the token after the commit token peaks at 0.75 on the grid task and 0.79 on the shortest path task), because the commit token is the ` deque` import for most programs of both classes (DFS 55 of 78, Bellman-Ford/SPFA 78 of 80), so the state at the commit token is the state at the first lexicon match, not at the algorithm decision. The read position, identical within a paraphrase, gave within paraphrase AUC of 0.37 to 0.62, as it must.

**Table 75.** Within paraphrase held-out AUC of each readout of the algorithm written (permutation p in brackets; source: `results/readout_i_discovery.json`). DiM is the difference-in-means direction on raw states.

| Task, layer, position | Top-1 SAE latent | Top-20 SAE latents (logistic) | DiM | Raw logistic probe | Top-1 neuron | Top-20 neurons (logistic) | DiM on SAE codes |
|-|-|-|-|-|-|-|-|
| Grid, 15, before commit | 0.482 (0.881) | 0.588 (0.234) | 0.614 (0.199) | 0.596 (0.184) | 0.535 (0.388) | 0.570 (0.343) | 0.596 (0.249) |
| Grid, 15, token 16 | 0.640 (0.114) | 0.693 (0.040) | 0.544 (0.308) | 0.649 (0.114) | 0.588 (0.149) | 0.518 (0.483) | 0.649 (0.075) |
| Grid, 20, before commit | 0.570 (0.284) | 0.649 (0.124) | 0.719 (0.025) | 0.544 (0.378) | 0.640 (0.060) | 0.649 (0.080) | 0.535 (0.388) |
| Grid, 20, token 16 | 0.640 (0.065) | 0.675 (0.030) | 0.456 (0.682) | 0.667 (0.060) | 0.658 (0.100) | 0.491 (0.527) | 0.518 (0.448) |
| Grid, 27, before commit | 0.535 (0.308) | 0.649 (0.090) | 0.614 (0.179) | 0.526 (0.378) | 0.535 (0.284) | 0.579 (0.244) | 0.711 (0.020) |
| Grid, 27, token 16 | 0.640 (0.124) | 0.588 (0.279) | 0.684 (0.065) | 0.579 (0.294) | 0.675 (0.070) | 0.596 (0.229) | 0.684 (0.075) |
| Shortest path, 15, before commit | 0.761 (0.005) | 0.676 (0.015) | 0.768 (0.005) | 0.778 (0.005) | 0.782 (0.005) | 0.771 (0.005) | 0.757 (0.005) |
| Shortest path, 15, forking token | 0.613 (0.030) | 0.634 (0.025) | 0.553 (0.229) | 0.609 (0.144) | 0.581 (0.119) | 0.683 (0.010) | 0.630 (0.020) |
| Shortest path, 15, token 16 | 0.856 (0.005) | 0.845 (0.005) | 0.856 (0.005) | 0.852 (0.005) | 0.863 (0.005) | 0.856 (0.005) | 0.838 (0.005) |
| Shortest path, 20, before commit | 0.732 (0.005) | 0.665 (0.025) | 0.736 (0.005) | 0.792 (0.005) | 0.810 (0.005) | 0.746 (0.005) | 0.708 (0.005) |
| Shortest path, 20, forking token | 0.697 (0.005) | 0.616 (0.095) | 0.606 (0.104) | 0.581 (0.139) | 0.581 (0.169) | 0.570 (0.219) | 0.708 (0.005) |
| Shortest path, 20, token 16 | 0.863 (0.005) | 0.845 (0.005) | 0.810 (0.005) | 0.817 (0.005) | 0.835 (0.005) | 0.845 (0.005) | 0.856 (0.005) |
| Shortest path, 27, before commit | 0.789 (0.005) | 0.725 (0.005) | 0.764 (0.005) | 0.694 (0.005) | 0.711 (0.005) | 0.789 (0.005) | 0.764 (0.005) |
| Shortest path, 27, forking token | 0.574 (0.095) | 0.560 (0.249) | 0.641 (0.025) | 0.694 (0.020) | 0.623 (0.060) | 0.697 (0.005) | 0.676 (0.005) |
| Shortest path, 27, token 16 | 0.856 (0.005) | 0.803 (0.005) | 0.810 (0.005) | 0.838 (0.005) | 0.827 (0.005) | 0.806 (0.005) | 0.824 (0.005) |

Applied without refitting to the fresh pool's states at the token before the commit token, the difference-in-means direction transferred best. On the grid task its within template AUC was 0.93, 0.97 and 1.00 at layers 15, 20 and 27, but only the fourth template produced both classes (15 BFS against 5 DFS, 75 pairs); the single top latent reached 0.27, 0.80 and 0.52. On the shortest path task the difference-in-means direction reached 0.66, 0.66 and 0.76 and the top-20-latent probe 0.65, 0.66 and 0.77. The top-20 latent lists overlapped above chance on the grid task (8 shared against 1.8 expected at layer 15) and at chance on the shortest path task, and shuffled labels gave AUC about 0.50.

**Attention to the ban.** The same three heads carry ban specific attention on both tasks: layer 21 head 17, layer 26 head 21 and layer 26 head 25. From the query at the token before the commit token, head 21.17 sends 0.207 (grid) and 0.098 (shortest path) more of its attention mass to the ban segment than to the neutral segment of the token matched twin, concentrated on the banned name's tokens (`breadth`, `-first`, `ijkstra`). On the grid task, runs that complied put more top head attention on the ban than runs that did not (0.135 against 0.105, within template permutation p = 0.0025); all noncompliant runs came from the fourth template, so this is a contrast within that template. The shortest path task shows no difference (p = 0.96). Attention weights are not a causal test, and the route experiment found the generated tokens' direct reads of the ban to matter only on the grid task.

**Prime and veto in the latents.** The preregistered pattern in which a forbidden concept is first activated so that it can be suppressed [53] appeared in none of the six task by layer configurations. The latents that fire on the banned algorithm's name were silent at the read position. At layer 27, both the name latents and the implementation latents of X were lower at the token before the commit token under the ban than under both twins for the same text (grid implementation latents 124 against 169 under the neutral twin; name latents 94 against 129 under the mention twin; implementation, ban against neutral, sign test p = 2e-24). The difference-in-means projection agreed in sign in only 2 of the 6 configurations, so most latent results here are flagged as not reproduced by the baseline.

**Thought anchors.** With thinking on and an 8,192-token cap, ten first template ban traces were sampled (five per task), and four traces per task were resampled at nine sentence boundaries with six continuations each (432 continuations), following the thought anchors method [54]. Grid traces think for 8.4k to 9.3k tokens and none completed within the cap, though 4 of 5 still emitted DFS code. In 4 of 4 resampled grid traces DFS was fixed at the first resample point (every continuation DFS from the first boundary on) and no anchor sentence exists; the traces open by restating the ban and proposing DFS within their first four sentences. Shortest path traces completed in 2.5k to 3.7k tokens (5 of 5) and showed one anchor among 32 sentences, a problem restatement. The early label detector was valid on 13 of 16 checks (0.81).

**The same seed test of temperature.** The request asked whether, with the seed held fixed, raising the temperature changes the idea or only the phrasing. Thirty seeds were run at T in {0.3, 0.7, 1.0, 1.3} with top-k = 10, for the baseline and the first template ban on both tasks (480 rows), coupling samples by inverse CDF sampling over the sorted top 10 tokens with one uniform stream per seed shared across temperatures. Under this coupling the idea never moved: the label changed against T = 0.3 in 0 of 30 seeds in 10 of 12 cells and in 1 of 30 in the other two, for same seed and different seed pairs alike (Table 76). With no idea level variation left, the same seed and different seed agreement on ideas is identical. Phrasing (identifier normalised AST 4-gram Jaccard below 0.8) changed less within a seed than across seeds, and the first token where a program diverged from its T = 0.3 twin fell at a median of 13 to 117 tokens. vLLM reproduced 5 of 8 rows byte for byte when rerun.

**Table 76.** Same seed temperature test: rate of change against T = 0.3 for the same seed and for different seeds (30 seeds per cell; phrasing at Jaccard threshold 0.8; source: `results/same_seed.json`).

| Task | Condition | T | Idea change, same seed | Idea change, different seeds | Phrasing change, same seed | Phrasing change, different seeds | Median divergence token | Identical to T = 0.3 |
|-|-|-|-|-|-|-|-|-|
| Grid | baseline (all BFS) | 0.7 | 0/30 | 0.0 | 0.60 | 0.84 | 23 | 7 |
| Grid | baseline | 1.0 | 0/30 | 0.0 | 0.77 | 0.86 | 23 | 4 |
| Grid | baseline | 1.3 | 0/30 | 0.0 | 0.83 | 0.90 | 21 | 3 |
| Grid | ban (all DFS) | 0.7 | 0/30 | 0.0 | 0.87 | 0.94 | 27 | 3 |
| Grid | ban | 1.0 | 0/30 | 0.0 | 0.93 | 0.97 | 13 | 1 |
| Grid | ban | 1.3 | 0/30 | 0.0 | 1.00 | 1.00 | 13 | 0 |
| Shortest path | baseline (all Dijkstra) | 0.7 | 0/30 | 0.0 | 0.07 | 0.06 | 117 | 21 |
| Shortest path | baseline | 1.0 | 0/30 | 0.0 | 0.13 | 0.12 | 91 | 13 |
| Shortest path | baseline | 1.3 | 0/30 | 0.0 | 0.10 | 0.16 | 28 | 7 |
| Shortest path | ban (Bellman-Ford/SPFA) | 0.7 | 0/30 | 0.0 | 0.53 | 0.63 | 74 | 5 |
| Shortest path | ban | 1.0 | 1/30 | 0.033 | 0.59 | 0.68 | 28.5 | 2 |
| Shortest path | ban | 1.3 | 1/30 | 0.033 | 0.55 | 0.76 | 25 | 1 |

Across the four temperatures, each grid baseline seed produced 1.0 distinct idea and 2.37 phrasing clusters on average (3.17 under the ban), and each shortest path seed 1.0 idea and 1.13 phrasing clusters (1.03 ideas and 2.17 clusters under the ban). Under the ban the grid pass rate per temperature was 0.23, 0.57, 0.43 and 0.43: every program was DFS.

**Lenses: NLA and the Jacobian lens.** A dated search in this experiment resolved the two unmapped terms of the request. NLA denotes natural language autoencoders, an activation verbalizer and reconstructor trained jointly with reinforcement learning; released checkpoints cover Qwen2.5-7B-Instruct, two Gemma-3 models and Llama-3.3-70B-Instruct but not Qwen3-8B as of 2026-10-20, and training one is far outside a 16 GB budget, so NLA was not run. We refer to the request's j lens as the Jacobian lens, which reads the state of a layer through the unembedding after multiplying it by the mean Jacobian of the final state with respect to that layer. A community Jacobian lens for Qwen3-8B exists and was gated against the logit lens on 2,000 positions: its top-1 agreement with the model's own next token was below the logit lens at every source layer (layer 27: 0.104 against 0.291), so it failed and its readouts are descriptive only.

**Checks and cost.** The labeller recheck gave 0.965 on 141 gold programs. An independent script rederived 69 headline numbers with no mismatch. Not run: a same seed arm with thinking on, a Gumbel coupling sensitivity, NLA, an adaptive top up and OpenRouter descriptions of latents. Cost: about 1.05 GPU hours and USD 0.04 (112 judge calls).

## 2.10 Comparisons across this iteration's experiments

**The same modal ban, three draws under fixed wording.** Three experiments sampled the modal bans with the five frozen templates and 20 samples each in Qwen3-8B [ARTIFACT:art_8_ULPE8jJQc_] [ARTIFACT:art_IVZc3TWCeE9f] [ARTIFACT:art_3iv5G76C3yoX]. With the wording fixed, the variation that iteration 1 saw across draws (banned shares from 0.09 to 0.72) disappears: the grid banned share was 0.14, 0.14 and 0.15 and the shortest path banned share 0.11, 0.16 and 0.13 (Table 77). What remains is concentrated in one template. On the grid task every surviving BFS program in all three draws came from the fourth template (`X is not allowed here`, with BFS as X), which produced BFS 43 times in 60 against 0 in 240 for the other four templates. On the shortest path task the third and fourth templates carry most of the failures (15 and 18 of 60, against 1 to 4 for the others). Every attempted grid program not banned in the three draws was DFS (257 of 257), and 255 of 260 on the shortest path task were Bellman-Ford/SPFA (5 other labels). Compliance is a property of the wording, and here of one wording in particular.

**Table 77.** Banned programs per template (of 20) under the modal ban in the three protocol v2 draws of Qwen3-8B (sources: route experiment `results/analysis.json#behaviour`, ban list experiment `results/landing.json`, readout experiment `results/fresh_pool_summary.json`).

| Task | Draw | First template | Second | Third | Fourth | Fifth | Banned share | Programs not banned | Pass rate |
|-|-|-|-|-|-|-|-|-|-|
| Grid | route experiment, arm a | 0 | 0 | 0 | 14 | 0 | 0.14 | DFS 86 | 0.41 |
| Grid | ban list experiment, single ban | 0 | 0 | 0 | 14 | 0 | 0.14 | DFS 86 | 0.41 |
| Grid | readout experiment, fresh pool | 0 | 0 | 0 | 15 | 0 | 0.15 | DFS 85 | 0.34 |
| Shortest path | route experiment, arm a | 1 | 0 | 4 | 5 | 1 | 0.11 | Bellman-Ford/SPFA 86, other 3 | 0.91 |
| Shortest path | ban list experiment, single ban | 2 | 1 | 6 | 7 | 0 | 0.16 | Bellman-Ford/SPFA 83, other 1 | 0.95 |
| Shortest path | readout experiment, fresh pool | 1 | 0 | 5 | 6 | 1 | 0.13 | Bellman-Ford/SPFA 86, other 1 | 0.96 |

**The substitution test in two models.** Neither model gave a robust branch (Table 78). In Qwen3-8B the pooled X specific share sits near 0.55 to 0.66 with intervals that straddle 0.5, and only the unscrubbed programs, which pass the validity gate, place the interval above 0.5. In Llama the point estimate is higher (0.80) but its interval is wider and the post hoc noise analysis shows the importance sampling noise has not been removed. Three things replicate across the families: the gains are far from pure subtraction, the X specific residual is not aimed at the prime and veto profile in either model, and the generic perturbations do not form a coherent ladder in either (mean cosines 0.34 and -0.02 in Qwen3-8B, 0.14 in Llama).

**Table 78.** X specific share in the two models (sources: likelihood screen `results/c1.json`, `results/sensitivity.json`; Llama replication `results/c1.json`).

| Model | Reference | Scope | X specific share | 95% CI | Branch |
|-|-|-|-|-|-|
| Qwen3-8B | neutral twin | grid | 0.63 | [0.28, 0.83] | undetermined |
| Qwen3-8B | neutral twin | shortest path | 0.41 | [0.10, 0.61] | undetermined |
| Qwen3-8B | neutral twin | pooled | 0.55 | [0.25, 0.67] | undetermined |
| Qwen3-8B | mention twin | grid | 0.66 | [0.51, 0.98] | X specific, unaimed |
| Qwen3-8B | mention twin | shortest path | 0.65 | [0.26, 0.79] | undetermined |
| Qwen3-8B | mention twin | pooled | 0.66 | [0.49, 0.87] | undetermined |
| Qwen3-8B | neutral twin, unscrubbed programs, first template | pooled | 0.69 | [0.51, 0.84] | X specific, unaimed |
| Llama-3.1-8B-Instruct | neutral twin | grid | 0.80 | [0.28, 0.94] | not resolved at this N |
| Llama-3.1-8B-Instruct | mention twin | grid | 0.78 | [0.61, 0.91] | X specific, unaimed |

[FIGURE:fig_c1share]

**Priming and the route agree across models.** A ban of an algorithm the model does not write raises that algorithm's likelihood in 8 of 9 cases in Qwen3-8B (+2.5 to +26.9 nats) and 5 of 6 in Llama (+1.8 to +7.6), and in both models the bans that lower their own label are those of algorithms the model does write, plus A*. The likelihood drop of the banned default travels by the prompt route in both models: F_prompt 0.85 [0.61, 1.20] in Qwen3-8B and 0.84 [0.62, 1.46] in Llama, with the direct route near zero (0.00 and -0.21). Only the Qwen3-8B grid behaviour shows a second, direct component. *(Correction, iteration 3: both numbers are the likelihood readout, which on the grid task is dominated by the opening fork (ESS 1 to 3 of 30), and in Llama it is the only readout, on an instrument that failed its gate there. The route is restated per task and per readout in Section 3.1, and on the bench the behavioural route is task dependent, with a pooled direct share of 0.74; Section 3.6.)*

## 2.11 What iteration 2 established, what it ruled out, and what it abandoned

Everything below is still descriptive: two screen tasks, two models, one modal ban event per task and model for the route test, and a likelihood instrument whose validity gate failed in both models in its preregistered (name scrubbed) form.

**Established.**

1. *The iteration-1 record, corrected.* On the shortest path task the ban's substitute is Bellman-Ford/SPFA in five of five draws (272 of 272 compliant programs, Wilson [0.986, 1.000]); on the grid task DFS is the realised mode in four of five draws (116 of 128, [0.843, 0.946]), with no clear mode in the HF engine geometry draw. Under fixed wording three new Qwen3-8B draws landed on DFS (257 of 257 programs not banned) and Bellman-Ford/SPFA (255 of 260). The cumulative BFS and DFS ban does not replicate. Under one statistic, no ban and no diversity knob reaches a second correct algorithm (rarefied Hill-1 of at least 2) for less than 20 pass points on either task; the semantic seed on the shortest path task comes closest (1.935 at 7 points). On gated events, no forecasting family can advance (three informative events, largest margin 0.05 nats).
2. *The generic perturbation rival holds on the shortest path task and fails on the grid task.* Every nonsemantic perturbation that left Dijkstra (8 of 8 rows) landed mostly on Bellman-Ford/SPFA, random directions included; on the grid task no nonsemantic perturbation left BFS among correct programs *(corrected in iteration 3: one did, barely; temperature 1.3 with top-k = 10 gave DFS in 1 of 95 correct programs)*, while every ban reached DFS. On the shortest path task a ban and an arbitrary push end in the same place.
3. *The ban acts through the prompt states, before the first generated token.* In cache patching the prompt route carried 0.85 [0.61, 1.20] of the banned algorithm's likelihood drop and the direct route 0.00 [-0.08, 0.12], with the task specification states, not the read position alone, carrying it. The mechanism is an opening line veto: under the grid ban 0 of 100 programs open with the default's import line against 99 of 100 under the neutral twin, and the prompt route arm reproduces this exactly. On the shortest path task behaviour follows the prompt route completely; on the grid task generated tokens also read the ban directly (hiding the ban from them restores BFS to 0.47). Llama's likelihood readout agrees (F_prompt 0.84). *(Correction, iteration 3: the heading and first sentence state the route more strongly than its evidence. Per task and per readout: on the shortest path task the prompt route carries the ban in likelihood (0.82) and in behaviour (0.98 [0.89, 1.07], direct 0.05 [0.01, 0.09]); on the grid task the likelihood readout is dominated by the opening fork (0.87), behaviour is mixed (prompt 0.50 [0.39, 0.62], direct 0.35 [0.25, 0.45]) and the natural proposal readout puts the direct route at 0.16 [0.11, 0.21], an interval that excludes 0; Llama has the likelihood readout only (0.84 [0.62, 1.46]). The direct route is not zero. Splicing the read position alone carries none of the effect (F_R about 0).)*
4. *The read position knows, in part, how hard a wording will be obeyed, and not what replaces X.* Across 110 wordings the projection on a shared ban direction correlates with the banned share at -0.41 [-0.69, -0.17] (p = 0.0003), short of the -0.5 bar; the substitute is not decodable beyond that projection. *(Added in iteration 3: splicing the read position alone carries none of the ban's effect (F_R about 0), so this site is decodable but causally inert; a causal test of a shared prohibition direction at the task specification positions was run in iteration 3 and failed, Section 3.7.)*
5. *Naming primes.* A ban of an absent algorithm raises that algorithm's likelihood in both models (8 of 9 and 5 of 6), and the mention twin raises it more. The iteration-1 sham promotions are reproduced by the shared (ladder) component of the gains and are not X specific.
6. *Ban lists fail by reimplementation.* Every four or five name grid ban failed (avoidance 0.00 to 0.37); the model wrote BFS and DFS in the same mix whatever the list contained (BFS share 0.63 to 0.72, chi squared p = 0.48), disguising 41% to 92% of the banned programs. On the shortest path task the model will not write bidirectional Dijkstra, Floyd-Warshall or Dial even when each is the only algorithm allowed, though it can write Floyd-Warshall and Dial when told to *(qualified in iteration 3: forced Floyd-Warshall is labelled as requested and correct 40 of 40 times, but forced Dial, from the descriptive prompt, is labelled as requested 36 of 40 times and passes only 7 of 40, so only Floyd-Warshall is written cleanly on request)*.
7. *No decision locus among the saved states.* On the grid task the within one ban signal is fixed per paraphrase; on the shortest path task the first state that beats the read position by 20 points is a readout of text already written (`import heapq` against `from collections import deque`, decided at generated token 3). The forking token, the opening line veto and the locus probe all point at the first three generated tokens, which no artifact has saved.
8. *Temperature does not change the algorithm even for a fixed seed.* With seeds coupled across temperatures, the algorithm changed in 0 of 30 seeds in 10 of 12 cells and 1 of 30 in the other two, while phrasing changed in 7% to 100% of seeds depending on task and temperature, and less within a seed than across seeds.
9. *Qwen3-8B is collapsed on 13 new tasks as well.* The pilot found a modal share of 1.00 on 12 tasks and 0.98 on one; Llama-3.1-8B-Instruct is more diverse on the same tasks *(qualified in iteration 3: in attempted programs; counted over correct programs and rarefied to 10, Llama is more diverse on 9 of 13 tasks, but much of its attempted diversity is failing code, Section 3.2.4)*. The confirmation bench is frozen (12 tasks, labellers gated) with no ban prompt run on it.

**Ruled out, or not supported.**

- *Geodesic proximity on the read position manifold as the predictor of the shortest path substitute.* Floyd-Warshall is the nearest survivor to Dijkstra in 100% of paraphrase subsamples at every layer and k tested, Bellman-Ford/SPFA is never nearest, and no ban landed on Floyd-Warshall. On the grid task proximity and typicality coincide and cannot be separated.
- *An aimed substitution.* In neither model is the X specific part of the ban gains aimed at the prime and veto profile (Qwen3-8B -0.10, p = 0.80; Llama 0.067, p = 0.35) or at the stated alternative. *(Correction, iteration 3: not detectable with the current instrument, rather than ruled out; Section 3.2.1.)*
- *A coherent latent ladder.* The generic perturbation profiles do not agree with each other in either model, so the rival in its preregistered form, a fixed ordering any perturbation reveals, was not found either. *(Correction, iteration 3: this item belongs among the effects that an uncalibrated instrument could not detect, not among the accounts ruled out, and it conflicts with item 2 above. Reconciled: behaviour shows a shared top rung on the shortest path task, where 8 of 8 nonsemantic perturbations that left Dijkstra landed mostly on Bellman-Ford/SPFA, and on the grid task only bans reach DFS. The order of the survivors below the top rung is unmeasured: it is unobservable in behaviour under the collapse, and the likelihood cosines that this item rests on come mostly from survivors with an ESS near 1.)*

*(Added in iteration 3: the iteration-2 preregistered predictions and their outcomes, and the outcome of the iteration-2 forecast contest of the four frozen families (NOT RUN on any new event), are listed in Section 3.1.)*
- *A veto at the signature token.* The lens found no layer at which the ban lowers the banned algorithm at the commitment token, because the fork is at the first token; the signature tokens carry 2.4% and 11.6% of the likelihood drop.
- *Activation of a forbidden concept in order to suppress it.* The prime and veto latent pattern appeared in 0 of 6 configurations; the name latents of X were lower under the ban than under both twins.

**Dead ends, with the evidence that closed them.**

- *The likelihood instrument on name scrubbed programs as a calibrated probability.* It failed calibration in Qwen3-8B (default share 0.83, DFS mass under a baseline that never samples DFS) and in Llama (implied BFS 0.43 against sampled 0.77), with effective sample sizes mostly below 5 in every experiment that used it (98% of gate cells, 858 of 1,095 route cells, 97% of ban list cells, 76% of Llama cells). Unscrubbed programs pass the Qwen3-8B gate (calibration 0.95 and 1.00, 1.18 nats, 17 of 19), so the scrubbing, not the instrument, is the closed part.
- *Extending the grid catalogue toward ten algorithms.* Only five of ten algorithms passed the keep rule; the model writes A* as unit weight Dijkstra, unit weight Dijkstra as BFS, and jump point search and bidirectional A* as BFS and A*.
- *The literal top five landing test as a test of edge against opposite side.* The model does not comply with a five name ban (avoidance 0.00), so no survivor mass exists to place on either side; the question is answered behaviourally (reimplementation of the defaults) rather than geometrically.
- *Qwen-Scope base model SAEs on the instruct model.* The spliced in cross-entropy ratio was 3.29, 1.95 and 1.59 at layers 15, 20 and 27 against a 1.5 bar; latents never beat the difference-in-means direction.
- *The community Jacobian lens for Qwen3-8B.* Its next token agreement was below the logit lens at every layer (0.104 against 0.291 at layer 27).
- *NLA.* No natural language autoencoder exists for Qwen3-8B as of 2026-10-20.
- *A presence piloted present minor stratum for Qwen3-8B.* All 13 bench tasks are fully collapsed in the pilot, so present minor bans and a sampled typicality forecast do not exist for this model on this bench.
- *The free-form association answer as evidence about mechanism.* It predicts the substitute, but simulation of its own behaviour explains that success under either branch of the substitution test.

## 2.12 What the next iteration takes from this one

The title claim is still open, and the reason has changed. Iteration 1 could not separate substitution from a latent ladder because its events were too few and its typicality forecast was degenerate. This iteration measured every single ban in two models with a likelihood instrument and found neither account clean: the gains are not pure subtraction, they are not a coherent ladder, and their X specific part is not aimed where association or prime and veto predict. *(Correction, iteration 3: none of these three is detectable with the current instrument; Section 3.2.1.)* The confirmation bench exists to settle the share with task level clusters. Its inputs are now fixed, and so are its limits. Qwen3-8B is collapsed on all 12 frozen tasks, so its confirmation must use likelihood matrices on unscrubbed programs, which the gate supports, plus modal bans; Llama supplies sampled present minor bans. The ban, mention, neutral and nonce matrices, the Llama forced programs and every sampled ban event on the bench remain to be run, with forecasts hash committed first.

The route result redirects the mechanistic work. A ban is applied by the prompt states as a veto on the default's first line, and on the grid task also by direct reads during generation. The next measurements are therefore at generated tokens 1 to 3, the states no artifact has saved: a decoder and an activation patch there would locate the decision the locus probe could not find, and would say whether the opening line veto is the whole of the algorithm choice on the shortest path task. On the grid task the direct component needs its own localisation (which layers and which tokens read the ban after `def solve`), since the three attention heads that attend to the banned name are a descriptive lead, not a causal one. The template effect must enter every analysis as a random effect; one wording, the fourth template (`X is not allowed here`), accounts for every grid failure in three draws.

Request items still open after this iteration: the activation space manifold plots with centroids coloured by implemented count at a validated locus (no locus validated yet; *corrected in iteration 3: the plots themselves exist, 13 Isomap figures drawn by the ban list experiment at layer 24 and the token before the commit token, Section 3.2.2, but not at a validated locus*), a working SAE readout (the transfer test failed; a short fine-tuning on instruct activations, or a dictionary trained on them, is the alternative), and a same seed arm with thinking on. The top five prohibition, natural BFS against DFS internals, thought anchors, the same seed test, the logit and tuned lens, and the mapping of NLA and the Jacobian lens were run here. *(Added in iteration 3: the readout experiment did not save generated tokens 1 to 3 because the artifacts of one iteration run in parallel, and its plan was frozen before the audit named those positions; its states stop at the token before the commit token and token 16.)*

# Iteration 3: ban-free forecasts on the bench, the route of a ban across twelve tasks, and how far any knob reaches

## 3.1 Why this iteration ran what it ran

**The review of the iteration-2 record.** The review raised nine major and three minor items. Five concerned evidence the record held but read too strongly. The likelihood substitution test could not settle where a ban sends the mass: on the only rows with known behaviour, its algorithm specific residual pointed away from the substitute the model actually wrote, and its noise correction was never checked on Qwen3-8B. The record also carried two verdicts on the rival account that contradicted each other (a shared second choice on the shortest path task, and the absence of a coherent ladder listed among the accounts ruled out). The closing summary stated that the direct route carried none of the ban, although two of the three readouts in the same artifact showed a direct route. The cross-model contrast rested on failing programs: Llama's correct grid programs were all BFS. The knob verdict was paraphrased past its own metric. Four items concerned work that existed but was missing from the record: the ban list experiment's 13 manifold figures with centroids coloured by implemented count, the out-of-catalogue programs that no one had inspected, positioning rows for the iteration-2 claims, and a statement that the forecast contest of the four frozen families had never been run. The remaining items were the preregistered predictions and their outcomes, the inherited bench instrument, and five factual slips. The corrections are made in place in Sections 1.12 and 2.3 to 2.12, each marked; Table 80 maps every item to where it is answered.

**The hypothesis update.** The update flipped the predicted branch to the side the evidence leaned toward and moved the decision from likelihood cells to sampled programs. Its title claim is that a prompt prohibition removes the named default and does not choose the replacement: the mass that leaves the default lands on what we call the *next rung*, the survivor that the model's own distribution puts next once the default is gone. The rival is substitution specific to X, under which the landing follows the model's stated alternative to X (association) or the survivor whose programs look most like X's (proximity). Under total collapse the next rung cannot be read from sampled frequencies, so the update introduced ban-free counterfactuals that expose it without any ban text.

- We call the *signature veto* a decoding-time mask on the default's distinctive token n-gram: the shortest n-gram (up to 6 tokens) present in at least 80% of the default's baseline programs that minimises its largest share in the other algorithms' forced programs. The one-shot form masks the completing token the first time it comes up; the persistent form masks it at every occurrence; the iterated form adds the n-grams of re-emerged default programs for up to three rounds. We call the landing of the last veto round that leaves at least 20 attempts off the default the *subtraction forecast* of the event.
- We call the nonce ban, the novelty instruction and three random directions added at the task specification positions at the ban's own displacement norm generic pushes, and the pooled landing of the generic pushes that move at least 20 attempts off the default the *ladder forecast*.
- We call the model's frozen free-form answer when asked for the standard alternative to X the *association forecast*, and the survivor whose forced programs are nearest to the default's by tree edit distance on identifier-normalised syntax trees [64] the *proximity forecast*.
- We call an *exposure ban* a prompt that shows a correct program of a non-default algorithm Y and then asks for a correct solution that does not use Y. Showing Y makes the model copy it, so Y becomes the default to ban, and association and ladder disagree wherever Y's stated alternative is not the model's context-free default.

The update also added a causal test of what we call the shared prohibition direction, the mean displacement that the bans of the other tasks cause at the task specification positions (Section 3.7 gives its construction), a locus probe at generated tokens 1 to 8, the request's top-five prohibition asked again as a cumulative token veto, and the request's own long-form novelty instruction, an instruction to invent an algorithm that asks for a design rationale of about 2,000 words before the code. The event gate stayed as in Section 2.2 (avoidance at least 0.5 and at least 20 attempts not banned). The frozen contest rule names its outcomes, and we call these outcomes branches, written as the rule prints them: SUBTRACTION/LADDER when a ban-free family (subtraction or ladder) advances, followed by the family that advanced; SUBSTITUTION when association or proximity advances; NO FAMILY ADVANCES when none does, which we call aimed but unresolved when some family's top-1 still names the landing more often than chance; and, when no family's top-1 beats chance, the branch we call X specific but unaimed, the name Section 2.2 gave the same outcome. In the n-gram code spans of this section, ␣ marks a space and \n a newline. The likelihood instrument was demoted to a descriptive forecast of mass. The two path search tasks became the screen, and the 12 frozen bench tasks in two models became the confirmation; the two are never pooled.

**The iteration-2 preregistered predictions and their outcomes.** These were not listed in the iteration-2 record; they are recorded here as the hypothesis update recorded them.

1. A gain for DFS under the BFS ban specific to X, larger than the ladder can match: failed. The largest residual of that row belongs to IDDFS (+7.99) and DFS's is +0.83.
2. The direct route at generation time carries at least two thirds of the ban: failed. The direct share was 0.00 in likelihood, 0.35 in grid behaviour and 0.05 in shortest path behaviour; the preregistered alternative, decided before writing, was met on the likelihood readout.
3. A compliance correlation at the read position of -0.5 or below: missed (-0.41 [-0.69, -0.17], p = 0.0003).
4. The validity gate of the likelihood instrument: failed in both models in its preregistered, name scrubbed form.
5. The locus rule: no position passed on the grid task, and the shortest path pass was a readout after commitment.
6. The positive knob target: not met.
7. The forecast contest of the four frozen families (ladder, association, prime and veto, proximity) under the preregistered rule: not run on any new event. Only the three gated iteration-1 events existed, with a largest margin of 0.05 nats, and the ban list landing forecasts were degenerate.

**The route, restated per task and per readout.** The closing summary of iteration 2 said the direct route carried none of the ban. Per readout, the record holds this. On the shortest path task the prompt route carries the ban in likelihood (0.82) and in behaviour (0.98 [0.89, 1.07], against a direct share of 0.05 [0.01, 0.09]). On the grid task the likelihood readout is dominated by the opening fork (0.87), while behaviour is mixed (prompt 0.50 [0.39, 0.62], direct 0.35 [0.25, 0.45]) and the natural proposal readout puts the direct route at 0.16 [0.11, 0.21]. Llama has the likelihood readout only (0.84 [0.62, 1.46]). Splicing the read position alone carries none of the effect (F_R about 0), even though the read position projection correlates with compliance across wordings. Decodable there is not actionable there [55].

**The strategy.** Seven artifacts ran (Table 79). One audit without generation repaired the record. Three experiments sampled the bench bans that decide the title claim, each committing its forecasts by sha256 hash before its own first ban sample, because artifacts of one iteration run in parallel and cannot share commitments: modal bans in Qwen3-8B [5], exposure bans in Qwen3-8B, and modal and present minor bans in Llama-3.1-8B-Instruct [22]. Three experiments asked where and how far: the behavioural route on the bench, the internal locus with the shared prohibition direction, and the reach of prompt bans and token vetoes with the novelty question. The budget went to sampled events rather than likelihood variants, as the review asked.

**Table 79.** The seven artifacts of iteration 3, the question each was asked, and its hardware and spend.

| Artifact | Question | Model and hardware | OpenRouter spend |
|-|-|-|-|
| Record audit [ARTIFACT:art_3tH2xtoZ7Gj2] | Repair the iteration-2 record; likelihood diagnostics; manifold figures; novelty audit of every correct program outside the catalogue; correct-only Llama compositions; knob table with a class rule; positioning | No generation; CPU only | USD 0.42 (blind judges) |
| Bench forecast experiment [ARTIFACT:art_1AYTO1Epb_7t] | Do ban-free forecasts, sealed before the bans, predict where the 12 modal bench bans land in Qwen3-8B? | Qwen3-8B bf16; one RTX 4090, about 45 GPU minutes | USD 0.024 |
| Exposure experiment [ARTIFACT:art_WiY4wqHLb9Gy] | Shown a correct program of Y and told not to use Y, does the model go to Y's stated alternative or back to its default? | Qwen3-8B bf16; one 23 GB NVIDIA GPU, about 1.0 GPU hour | USD 0.096 |
| Llama bench experiment [ARTIFACT:art_Q-qh-9HhPoWo] | The same forecast contest in Llama-3.1-8B-Instruct, with present minor bans and a path task screen | Llama-3.1-8B-Instruct bf16; one 23 GB NVIDIA GPU, 0.98 GPU hours of logged generation (about 1.8 hours held) | USD 0.48 |
| Bench route experiment [ARTIFACT:art__5akZ9W9iZM4] | Does a ban act through the prompt states or by generated tokens reading it, on the 12 bench tasks, in behaviour? | Qwen3-8B bf16 (HF); one 23 GB NVIDIA GPU, about 1.8 GPU hours | USD 0.105 |
| Locus experiment [ARTIFACT:art_pVlCZ272hDV7] | Is there a shared prohibition direction; is the algorithm decided at generated tokens 1 to 8; do the ban-attending heads matter; do the base model SAEs transfer under a fairer criterion? | Qwen3-8B with 8-bit floating point weight and activation linears (HF); one 16 GB RTX 2000 Ada GPU | USD 0.22 |
| Reach experiment [ARTIFACT:art_ccAbfJVcv0LO] | How far do cumulative token vetoes and bans that leave one survivor push the model; does the request's long-form novelty instruction produce a correct novel algorithm? | Qwen3-8B bf16 (path tasks) and the official 8-bit floating point checkpoint (bench tasks); one 23 GB NVIDIA GPU | USD 0.49 |

**Table 80.** Review items on the iteration-2 record and where this report answers them.

| Review item | What the review found | Where it is answered |
|-|-|-|
| Likelihood substitution test | Residuals point away from the realised substitute; tail cells dominate; noise correction unchecked on Qwen3-8B; impossible weighted share; mention aim omitted | Corrections in Sections 2.4, 2.11 and 2.12; Section 3.2.1 |
| Two verdicts on the rival | A shared second choice in behaviour against a claimed absence of any coherent ladder | Correction in Section 2.11; Section 3.2.1; the bench tests in Sections 3.3 to 3.5 |
| Missing manifold figures | 13 Isomap figures with implemented counts existed; circle result overstated | Corrections in Sections 2.6 and 2.12; Section 3.2.2 |
| Cross-model contrast on failing programs | Llama's correct grid programs are BFS 20 of 20 | Corrections in Sections 2.7, 2.8 and 2.11; Section 3.2.4 |
| Samples, not variants; forecast contest outcome | The contest of the four frozen families never ran; budget arithmetic missing | Section 3.1 (outcome NOT RUN); Section 3.2.1 (arithmetic); Sections 3.3 to 3.5 (sampled bench events) |
| Positioning of iteration-2 claims | No neighbour rows for compliance at the read position, the route, priming, ban lists or SAE transfer | Section 3.2.6 |
| Route stated too strongly | A direct route of zero claimed against two readouts with a direct route | Corrections in Sections 2.10 and 2.11; this section; Section 3.6 |
| Novelty never inspected | About 25 correct programs outside the catalogue unread; the request's 2,000-word novelty instruction never run | Section 3.2.3; Section 3.8 |
| Knob verdict past its metric | A 2:1 split cannot reach Hill-1 of 2; class rule undeclared | Correction in Section 2.3.6; Section 3.2.5 |
| Minor: preregistered predictions; tokens 1 to 3 | Failed targets not listed; why the states were not saved | This section; correction in Section 2.12 |
| Minor: bench instrument | 8-bit prompt log probabilities; unscrubbed variant unvalidated on ban rows | Correction in Section 2.8; Section 3.3 (fp32 rescoring) |
| Minor: five factual slips | Table 66 prompt labels; DFS 1 at T = 1.3; forced Dial; TOP residue; an unmarked insertion in Section 1.12 | Corrections in Sections 1.12, 2.6 and 2.11 |

## 3.2 The record audit: likelihood diagnostics, manifold figures, novelty, correct-only Llama, knob classes

The record audit [ARTIFACT:art_3tH2xtoZ7Gj2] ran first and on CPU only. It read the iteration-1 and iteration-2 artifacts in place, generated nothing, and spent USD 0.42 on blind LLM judges for the novelty audit. Every number it produced names its source file. An independent script rederived 72 of 72 headline checks from the raw files, and all 7 placebo tests failed as they should.

### 3.2.1 The likelihood substitution test cannot decide where the mass goes

The review's central objection was that the substitution test of Section 2.4 rests on cells that are behaviourally irrelevant and close to unestimable. The audit tested this directly on every sampled single ban in both models: if the likelihood instrument measured where a ban sends the mass, the survivor with the largest gain should be the one the model writes. Table 81 gives every event.

**Table 81.** Every sampled single-ban event with likelihood cells: the realised landing and the argmax of three likelihood readouts (gain against the neutral twin, its algorithm specific residual after the ladder fit, and the implied probability mass under the ban). An argmax equal to the modal landing is marked as a hit. Source: record audit `tables/c1_argmax_vs_landing.csv`.

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

The noise correction was too small. Resampling templates and then programs within algorithm halves, the bootstrap variance of the mean gain is a median 2.68 times the replicate noise term that the frozen correction subtracted (range 1.22 to 4.26 over the 11 rows; 1.59 for a one stage bootstrap that resamples programs only). The Llama ratio was 4.8 to 11.3. Because the correction under-subtracts, both the F statistic behind the reading that the gains are not pure subtraction and the X specific share are inflated. The sums are also skewed upward, which the percentile intervals of Section 2.4 hid; basic intervals (twice the point estimate minus the bootstrap quantiles), which correct for that skew, are given in Table 83. The ladder term's basic interval crosses zero on both tasks.

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

| Model | Algorithm | Cells | Median ESS now (M = 20) | Median SD of log weights | Plug-in programs needed, median | Plug-in programs needed, 90th percentile | Lognormal programs needed, median |
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

The ladder verdicts of Section 2.11 are reconciled as the review asked (correction in place there). We call a survivor that the ban and every generic perturbation reach a shared top rung. Behaviour shows a shared top rung on the shortest path task: Bellman-Ford/SPFA took 272 of 272 compliant programs in the five iteration-1 draws and 255 of 260 attempts not banned in the three iteration-2 draws, and 8 of 8 nonsemantic perturbations that left Dijkstra landed there. On the grid task only bans reach DFS (116 of 128 compliant iteration-1 programs, 257 of 257 iteration-2 attempts not banned). The order below the top rung is unmeasured, and the latent ladder of Section 2.1 moves from the accounts ruled out to the effects that an uncalibrated instrument could not detect.

### 3.2.2 The ban list manifold figures

The ban list experiment had drawn 13 Isomap figures, not the 14 its summary claimed, plus two figures of neighbour stability over k. Each figure embeds teacher forced states of forced programs at layer 24 and the token before the commit token (k = 10). Its centroids are sized and coloured by the number of programs implementing each algorithm under the condition, banned centroids are crossed out, and natural programs are overlaid. The audit recomputed the geometry from the saved states and reproduced the experiment's centroid matrix within 1e-7 and its nearest neighbour maps in 24 of 24 settings. Table 85 gives the implemented counts that the figures encode. Under the literal five name ban the counts stay on the banned BFS and DFS centroids (63 and 36 attempted, 53 and 15 correct).

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

The neighbourhood that the iteration-2 record reported (BFS next to bidirectional BFS, centroid distance 0.0147 against a within-BFS spread of 0.0154) does not survive at a position independent of the label. At generated token 16, BFS and bidirectional BFS are still the nearest pair, but permuting the algorithm labels reproduces that identity with p = 0.19, and the two clouds are not separable (centroid distance 0.96 of the within-class spread; exchangeability test p = 0.48). Table 86 gives the nearest neighbour maps at layer 24 and k = 10 for both positions. Persistent homology found no loop at either position. At the token before the commit token a planted loop of matched size is detected with power 1.00 (grid) and 0.975 (shortest path), but that position partly encodes the label; at token 16 the power is 0.035 and 0.045. The absence of a loop is therefore established with power only where the label confounds the geometry.

**Table 86.** Nearest centroid of each algorithm at layer 24, k = 10, at the label-dependent position (token before the commit token) and at generated token 16, with MDS stress-1. Source: record audit `tables/manifold_grid.csv`.

| Task | Position | Nearest neighbour map | Stress-1 | BFS and bidirectional BFS: distance / separability |
|-|-|-|-|-|
| Grid | before commit token | BFS: bidirectional BFS; DFS: IDDFS; bidirectional BFS: BFS; IDDFS: DFS; A*: greedy; greedy: A*; IDA*: greedy | 0.025 | 0.0147 / 0.954 |
| Grid | token 16 | BFS: bidirectional BFS; DFS: BFS; bidirectional BFS: BFS; IDDFS: bidirectional BFS; A*: greedy; greedy: A*; IDA*: bidirectional BFS | 0.104 | 0.0272 / 0.960 |
| Shortest path | before commit token | Dijkstra: bidirectional Dijkstra; Bellman-Ford/SPFA: bidirectional Dijkstra; bidirectional Dijkstra: Dijkstra; Floyd-Warshall: Dijkstra; Dial: Floyd-Warshall | 0.006 | n/a |
| Shortest path | token 16 | Dijkstra: bidirectional Dijkstra; Bellman-Ford/SPFA: Dial; bidirectional Dijkstra: Dijkstra; Floyd-Warshall: Dial; Dial: Floyd-Warshall | 0.005 | n/a |

**Table 86b.** The full recomputed grid behind Table 86: every layer, position and k (nearest neighbour of the default and of its realised substitute; the BFS and bidirectional BFS distance and separability on the grid task). Source: record audit `tables/manifold_grid.csv`.

| Task | Layer | Position | k | Stress-1 | Nearest to the default | Nearest to the substitute | BFS to bidirectional BFS distance | Separability |
|-|-|-|-|-|-|-|-|-|
| Grid | 20 | before commit token | 5 | 0.0273 | BFS: bidirectional BFS | DFS: IDDFS | 0.0150 | 0.978 |
| Grid | 20 | before commit token | 10 | 0.0427 | BFS: bidirectional BFS | DFS: IDDFS | 0.0143 | 0.962 |
| Grid | 20 | before commit token | 15 | 0.0360 | BFS: bidirectional BFS | DFS: IDDFS | 0.0159 | 0.972 |
| Grid | 20 | before commit token | 20 | 0.0286 | BFS: bidirectional BFS | DFS: IDDFS | 0.0146 | 0.967 |
| Grid | 20 | token 16 | 5 | 0.0649 | BFS: bidirectional BFS | DFS: A* | 0.0169 | 0.971 |
| Grid | 20 | token 16 | 10 | 0.1276 | BFS: bidirectional BFS | DFS: A* | 0.0151 | 0.938 |
| Grid | 20 | token 16 | 15 | 0.1332 | BFS: bidirectional BFS | DFS: A* | 0.0135 | 0.990 |
| Grid | 20 | token 16 | 20 | 0.1325 | BFS: bidirectional BFS | DFS: A* | 0.0096 | 0.938 |
| Grid | 24 | before commit token | 5 | 0.0908 | BFS: bidirectional BFS | DFS: IDDFS | 0.0147 | 0.974 |
| Grid | 24 | before commit token | 10 | 0.0253 | BFS: bidirectional BFS | DFS: IDDFS | 0.0147 | 0.954 |
| Grid | 24 | before commit token | 15 | 0.0178 | BFS: bidirectional BFS | DFS: IDDFS | 0.0158 | 0.959 |
| Grid | 24 | before commit token | 20 | 0.0173 | BFS: bidirectional BFS | DFS: IDDFS | 0.0144 | 0.968 |
| Grid | 24 | token 16 | 5 | 0.1040 | BFS: bidirectional BFS | DFS: A* | 0.0178 | 0.860 |
| Grid | 24 | token 16 | 10 | 0.1038 | BFS: bidirectional BFS | DFS: BFS | 0.0272 | 0.960 |
| Grid | 24 | token 16 | 15 | 0.1542 | BFS: bidirectional BFS | DFS: A* | 0.0172 | 0.997 |
| Grid | 24 | token 16 | 20 | 0.1415 | BFS: bidirectional BFS | DFS: A* | 0.0127 | 0.999 |
| Grid | 28 | before commit token | 5 | 0.0211 | BFS: bidirectional BFS | DFS: IDDFS | 0.0257 | 0.974 |
| Grid | 28 | before commit token | 10 | 0.0245 | BFS: bidirectional BFS | DFS: IDDFS | 0.0232 | 0.984 |
| Grid | 28 | before commit token | 15 | 0.0234 | BFS: bidirectional BFS | DFS: IDDFS | 0.0253 | 0.976 |
| Grid | 28 | before commit token | 20 | 0.0234 | BFS: bidirectional BFS | DFS: IDDFS | 0.0198 | 0.975 |
| Grid | 28 | token 16 | 5 | 0.0995 | BFS: bidirectional BFS | DFS: A* | 0.0211 | 0.951 |
| Grid | 28 | token 16 | 10 | 0.0598 | BFS: bidirectional BFS | DFS: IDDFS | 0.0229 | 0.992 |
| Grid | 28 | token 16 | 15 | 0.0737 | BFS: bidirectional BFS | DFS: IDDFS | 0.0223 | 0.995 |
| Grid | 28 | token 16 | 20 | 0.0774 | BFS: bidirectional BFS | DFS: IDDFS | 0.0157 | 0.956 |
| Shortest path | 20 | before commit token | 5 | 0.0047 | Dijkstra: bidirectional Dijkstra | Bellman-Ford/SPFA: bidirectional Dijkstra | n/a | n/a |
| Shortest path | 20 | before commit token | 10 | 0.0039 | Dijkstra: bidirectional Dijkstra | Bellman-Ford/SPFA: bidirectional Dijkstra | n/a | n/a |
| Shortest path | 20 | before commit token | 15 | 0.0039 | Dijkstra: bidirectional Dijkstra | Bellman-Ford/SPFA: bidirectional Dijkstra | n/a | n/a |
| Shortest path | 20 | before commit token | 20 | 0.0032 | Dijkstra: bidirectional Dijkstra | Bellman-Ford/SPFA: bidirectional Dijkstra | n/a | n/a |
| Shortest path | 20 | token 16 | 5 | 0.0066 | Dijkstra: bidirectional Dijkstra | Bellman-Ford/SPFA: bidirectional Dijkstra | n/a | n/a |
| Shortest path | 20 | token 16 | 10 | 0.0054 | Dijkstra: bidirectional Dijkstra | Bellman-Ford/SPFA: Dijkstra | n/a | n/a |
| Shortest path | 20 | token 16 | 15 | 0.0048 | Dijkstra: bidirectional Dijkstra | Bellman-Ford/SPFA: bidirectional Dijkstra | n/a | n/a |
| Shortest path | 20 | token 16 | 20 | 0.0035 | Dijkstra: bidirectional Dijkstra | Bellman-Ford/SPFA: Dijkstra | n/a | n/a |
| Shortest path | 24 | before commit token | 5 | 0.0075 | Dijkstra: bidirectional Dijkstra | Bellman-Ford/SPFA: bidirectional Dijkstra | n/a | n/a |
| Shortest path | 24 | before commit token | 10 | 0.0060 | Dijkstra: bidirectional Dijkstra | Bellman-Ford/SPFA: bidirectional Dijkstra | n/a | n/a |
| Shortest path | 24 | before commit token | 15 | 0.0056 | Dijkstra: bidirectional Dijkstra | Bellman-Ford/SPFA: bidirectional Dijkstra | n/a | n/a |
| Shortest path | 24 | before commit token | 20 | 0.0061 | Dijkstra: bidirectional Dijkstra | Bellman-Ford/SPFA: bidirectional Dijkstra | n/a | n/a |
| Shortest path | 24 | token 16 | 5 | 0.0062 | Dijkstra: bidirectional Dijkstra | Bellman-Ford/SPFA: Dial | n/a | n/a |
| Shortest path | 24 | token 16 | 10 | 0.0050 | Dijkstra: bidirectional Dijkstra | Bellman-Ford/SPFA: Dial | n/a | n/a |
| Shortest path | 24 | token 16 | 15 | 0.0050 | Dijkstra: bidirectional Dijkstra | Bellman-Ford/SPFA: bidirectional Dijkstra | n/a | n/a |
| Shortest path | 24 | token 16 | 20 | 0.0042 | Dijkstra: bidirectional Dijkstra | Bellman-Ford/SPFA: Dijkstra | n/a | n/a |
| Shortest path | 28 | before commit token | 5 | 0.0042 | Dijkstra: bidirectional Dijkstra | Bellman-Ford/SPFA: bidirectional Dijkstra | n/a | n/a |
| Shortest path | 28 | before commit token | 10 | 0.0061 | Dijkstra: bidirectional Dijkstra | Bellman-Ford/SPFA: bidirectional Dijkstra | n/a | n/a |
| Shortest path | 28 | before commit token | 15 | 0.0075 | Dijkstra: bidirectional Dijkstra | Bellman-Ford/SPFA: bidirectional Dijkstra | n/a | n/a |
| Shortest path | 28 | before commit token | 20 | 0.0073 | Dijkstra: bidirectional Dijkstra | Bellman-Ford/SPFA: bidirectional Dijkstra | n/a | n/a |
| Shortest path | 28 | token 16 | 5 | 0.0038 | Dijkstra: bidirectional Dijkstra | Bellman-Ford/SPFA: Dial | n/a | n/a |
| Shortest path | 28 | token 16 | 10 | 0.0039 | Dijkstra: bidirectional Dijkstra | Bellman-Ford/SPFA: Dial | n/a | n/a |
| Shortest path | 28 | token 16 | 15 | 0.0039 | Dijkstra: bidirectional Dijkstra | Bellman-Ford/SPFA: Dial | n/a | n/a |
| Shortest path | 28 | token 16 | 20 | 0.0034 | Dijkstra: bidirectional Dijkstra | Bellman-Ford/SPFA: Dial | n/a | n/a |

### 3.2.3 Novelty: every correct program outside the catalogue, read

The request asks whether a model can be made to give a truly novel solution. The only place such a solution could have appeared in the run's data is among programs with the label other. The audit collected every correct program labelled other across the eleven declared artifacts and the 1,200-program copy of the forking token pools: 78 unique programs (Set A). It added 138 unique failing programs labelled other and written under bans (Set B), and the 12 failing programs labelled other under the TOP ban list (the selection was hash committed before any judge call). Two blind judges from different families (gpt-4.1-mini and gemini-2.5-flash, tie-break deepseek-chat) classed each program as a novel algorithm, a variant of a catalogue algorithm, a labeller miss, or degenerate or hard-coded, and the executor read all 78 Set A programs and 112 Set B programs by hand.

None of the 78 correct programs is a novel algorithm (Table 87). Sixty-five are labeller misses (catalogue algorithms the runtime and AST labellers failed to name) and 13 are variants of catalogue algorithms; the manual pass, which read every program, agreed on the exact class for 60 of 78 and on all 78 once the catalogue variant and labeller miss classes are merged. Sixty-two of the 78 came from forced prompts and 4 from the decommitment steering arms; none came from a creativity, new algorithm or novelty instruction (Table 87b). The rule of three [67] bounds the novel rate at 3/78 = 0.038 among correct programs outside the catalogue and 0.00026 over all 11,763 unique correct programs audited. About 9,000 other programs of the forking token experiment were not audited.

**Table 87.** Final classes of the audited programs. Source: record audit `results/novelty_audit.json`.

| Set | Programs | Labeller miss | Catalogue variant | Degenerate or hard-coded | Novel algorithm |
|-|-|-|-|-|-|
| A: correct, labelled other | 78 | 65 | 13 | 0 | 0 |
| B: failing, labelled other, under bans (final) | 138 | 53 | 41 | 44 | 0 |
| B: judges only, before the tie-break and manual pass | 138 | 53 | 28 | 40 | 17 |
| TOP ban list residue | 12 | 0 | 0 | 12 | 0 |

**Table 87b.** The 78 correct programs labelled other, by model, task and condition, with their final class (Set A of Table 87). Source: record audit `tables/novelty_class_counts.csv`.

| Model | Task | Condition | Labeller miss | Catalogue variant | Novel |
|-|-|-|-|-|-|
| Qwen3-8B | kth smallest | forced prompts | 13 | 0 | 0 |
| Qwen3-8B | merge intervals | forced prompts | 0 | 1 | 0 |
| Qwen3-8B | Grid | forced A* | 21 | 0 | 0 |
| Qwen3-8B | Grid | forced bidirectional BFS | 1 | 1 | 0 |
| Qwen3-8B | Grid | forced unit weight Dijkstra | 15 | 0 | 0 |
| Qwen3-8B | Grid | forced greedy best first | 2 | 0 | 0 |
| Qwen3-8B | Grid | forced IDA* | 1 | 0 | 0 |
| Qwen3-8B | Grid | forced jump point search | 0 | 1 | 0 |
| Qwen3-8B | Grid | forced jump point search (descriptive) | 1 | 1 | 0 |
| Qwen3-8B | Grid | mention of bidirectional BFS | 1 | 0 | 0 |
| Qwen3-8B | Grid | SCATTER ban list | 2 | 0 | 0 |
| Qwen3-8B | Grid | TOP ban list | 1 | 0 | 0 |
| Llama-3.1-8B-Instruct | Grid | ban BFS, first template | 0 | 1 | 0 |
| Llama-3.1-8B-Instruct | Grid | forced A* (paraphrase 5) | 1 | 0 | 0 |
| Llama-3.1-8B-Instruct | Grid | forced A* (paraphrase 9) | 0 | 1 | 0 |
| Qwen3-8B | Shortest path | baseline | 0 | 1 | 0 |
| Qwen3-8B | Shortest path | forced bidirectional Dijkstra (descriptive) | 1 | 1 | 0 |
| Qwen3-8B | Shortest path | decommitment direction, c = 0.25 | 1 | 0 | 0 |
| Qwen3-8B | Shortest path | decommitment direction, c = 0.375 | 0 | 1 | 0 |
| Qwen3-8B | Shortest path | decommitment direction, c = 0.5 | 1 | 1 | 0 |
| Qwen3-8B | Shortest path | variable name placebo direction, c = 0.25 | 0 | 1 | 0 |
| Qwen3-8B | Shortest path | second succession step | 0 | 1 | 0 |
| Qwen3-8B-Base | Shortest path | baseline | 1 | 1 | 0 |
| Llama-3.1-8B-Instruct | Shortest path | ban Dijkstra, fourth template | 1 | 0 | 0 |
| Llama-3.1-8B-Instruct | Shortest path | mention of Dijkstra, fifth template | 1 | 0 | 0 |
| All | | | 65 | 13 | 0 |

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

Counted over correct programs and rarefied to 10, Llama is more diverse than Qwen3-8B on 9 of 13 tasks (median 1.47 against 1.00). The cross-model sentence of iteration 2 therefore becomes: Llama attempts more algorithms, but its correct grid output is as collapsed as Qwen3-8B's. Correct-only diversity appears on substring search, connected components, cycle detection and top-k frequent, at small N.

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

Four of the nine shortest path rows in Table 91 are activation edits: the decommitment direction, which iteration 1 found no better than a random direction, and three random directions. In every one of them the only catalogue algorithm besides Dijkstra is Bellman-Ford/SPFA, the same second choice the ban reaches.

### 3.2.6 Positioning of the iteration-2 claims

The audit checked each iteration-2 claim against its nearest published neighbour with verbatim quotes from the abstract pages, all 12 verified on 2026-10-20 (Table 92). Two contrasts matter for interpretation. Heo et al. found a dimension in input embedding space that predicts instruction following, is tied to prompt phrasing, and raises success when intervened on [58]; this run replicates the phrasing link for prohibitions in code but finds the read position causally inert when spliced alone. Sia, Mueller and Duh found a task recognition point after which attention to the instruction is no longer needed [59]; this run replicates that on the shortest path task and finds the opposite on the grid task. The base to chat SAE transfer study of Kissane and colleagues (an Alignment Forum post that the bibliography tool could not retrieve, so it carries no number here) is the source of the fine-tuning remedy that Section 2.12 proposed without citation.

**Table 92.** The iteration-2 claims, their nearest neighbours, and what this run adds. Source: record audit `tables/positioning.csv`.

| Claim in this run | Neighbour | Neighbour's finding (paraphrased; the audit verified each against a verbatim quote) | Relation | What this run adds |
|-|-|-|-|-|
| Compliance is decodable at the read position (-0.41 across wordings) yet splicing the read position carries nothing | Heo et al. [58] | a direction in input embedding space predicts instruction following, tracks prompt phrasing more than task difficulty, and raises success when intervened along | replication (phrasing) and contrast (decodable but inert under splicing) | a compliance-predictive direction at the read position that is causally inert; the ban travels through the task specification states |
| Attention knockouts and cache splicing place the path task ban on the prompt route | Geva et al. [48] | interventions on attention edges locate two points where information flows to the prediction | extension (method) | edge knockouts applied to a prompt-level prohibition in code, with token-matched neutral twins |
| Generated tokens stop needing the ban on the shortest path task (direct 0.05) but not on the grid task (direct 0.35) | Sia et al. [59] | after a task recognition point the task is encoded in the input representations and attention to the context is no longer needed | replication (shortest path) and contrast (grid) | the same redundancy for a prohibition on one task and its failure on another |
| Naming an absent algorithm in a ban raises its likelihood (8 of 9 in Qwen3-8B, 5 of 6 in Llama) | Rana [7] | explicitly mentioning a forbidden word activates its representation instead of suppressing it | replication | priming at the level of whole algorithms, in two model families |
| (same) | Mann et al. [53] | suppressing a concept requires activating it internally, which can prime rebound rather than avoidance | replication | rebound measured on implemented mechanisms rather than tokens |
| Ban lists fail by reimplementation, 41% to 92% disguised | Lu et al. [23] | denial prompting adds a new constraint on the previous solution at each step to push the model toward more creative solutions | extension | mechanism labels show the constraint satisfied in name only |
| Qwen-Scope base SAEs fail the cross-entropy ratio on the instruct model | Kissane et al. (blog post, not in the bibliography) | base model SAEs usually transfer to chat models, but not on Gemma v1 2B | contrast and source of the remedy | Qwen3-8B would join Gemma v1 2B as a pair where base SAEs do not transfer under that criterion; Section 3.7 reverses this under a fairer criterion |
| Decoding-time constraints as the alternative to prompt bans | Biagiola et al. [62] | an incomplete constraint at decoding time pushes the model into low-probability regions of program space, causing time-outs and up to 97% lower functional correctness | contrast | single name prompt bans are obeyed at 0.86 and 0.84; vetoes at decoding time carry the cost Biagiola et al. measure (Section 3.8) |
| A single ban suppresses the default opening and promotes one substitute | Yoon et al. [4] | negation suppresses retrieval of the original answer while promoting a favoured candidate in the same answer category | replication at program level | the promoted candidate is the shared top rung, not a substitute specific to X |
| (same) | Zhou et al. [56] | models process negation by both suppression and construction, with construction more prominent | contrast | for a prohibition on code the route is carried by task specification states; construction of the negated phrase was not tested |
| The ban is carried by task specification states and not by the read position alone | Hendel et al. [60] | functions learned in context often have a very simple structure, a task vector | contrast | a prohibition does not compress into one position's state |
| (same) | Todd et al. [61] | a few attention heads transport a compact representation of the demonstrated task, a function vector | contrast | ban-attending heads exist (layer 21 head 17, layer 26 heads 21 and 25), but the effect is spread over task specification positions; Section 3.7 tests the heads causally |

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

## 3.3 Bench forecast experiment: do ban-free forecasts predict where the modal bench bans land? (Qwen3-8B)

**Why.** This experiment [ARTIFACT:art_1AYTO1Epb_7t] was the confirmation of the title claim in Qwen3-8B. On the 12 frozen bench tasks, which had never seen a ban prompt, it built the four ban-free forecasts of where each task's modal ban would land, sealed them in a sha256 hash chain, and only then sampled the bans. If a ban only removes the default, the subtraction or ladder forecast should win; if it substitutes, association or proximity should.

**Design.** The model ran in bf16 (revision b968826d, thinking off, T = 1.0) on one RTX 4090. The bench, its labellers (runtime trace first, AST second, blind judge on disagreement) and its gold sets were copied with all 146 committed file hashes verified, and the labeller recheck matched every gate value on 12 of 12 tasks. Ban prompts used the five frozen templates with token-length matched neutral twins (identical token ids from the task text on). The ban-free arms had 600 samples each over the 12 tasks: the neutral twin, the one-shot, persistent and sham signature vetoes, the nonce ban, the novelty instruction, and up to three iterated veto rounds. Three seeded isotropic random directions were patched into the task specification states at layers 12 to 23 at the ban's own displacement norm (50 samples per task each). The vetoes used exact rejection and a masked redraw coupled to the twin samples by seed. Seventeen forecast files, the n-grams, seeds, norms and the analysis code were sealed at 18:50:57Z; the first ban request followed at 18:55:16Z. Then 1,200 ban samples (5 templates by 20 per task) were labelled, and a band patch control spliced the ban's own task specification states at layers 12 to 23 into the twin (600 samples). Every family's forecast was smoothed the same way (93% forecast, 5% uniform over survivors, 2% on other) and scored by its mean log score per attempt not banned. The frozen rule advances a family that beats the next best by at least 0.10 nats on at least 3 gated events whose top-1 nominations disagree. An undefined forecast is scored as uniform.

**Table 94.** Forecasts committed before any ban sample (top-1 survivor; a forecast marked undefined is scored as uniform). The distinctive n-gram is shown as tokenised (␣ marks a space); its source is the 8-bit pilot unless marked. Source: bench forecast experiment `README.md` and `predictions/`.

| Task | Default | Distinctive n-gram | Subtraction | Ladder | Association | Proximity | Nominations disagree |
|-|-|-|-|-|-|-|-|
| kth smallest | full sort | `␣␣␣␣nums` | undefined | quickselect | quickselect | heapify and pop | yes |
| substring search | naive | `␣needle:\n␣␣␣␣␣␣␣␣␣␣␣` | undefined | undefined | KMP | built-in find | yes |
| find duplicate | hash set | `␣set` | sort and adjacent check | undefined | Floyd cycle detection | sort and adjacent check | yes |
| two sum | hash map | `␣if␣complement` | undefined | undefined | sort and two pointers | brute force | yes |
| connected components | union find | `␣find` | DFS | undefined | DFS | label propagation | yes |
| nonoverlapping intervals | greedy by end | `␣if␣start` (rederived on bf16) | undefined | undefined | DP with bisect | DAG longest path | yes |
| Fibonacci | iteration | `(` | undefined | matrix power | matrix power | memoised recursion | yes |
| topological order | Kahn | `.p` | undefined | undefined | DFS postorder | undefined | no |
| merge intervals | sort and sweep | `␣last` | undefined | undefined | interval tree | union find | yes |
| first and last position | binary search | `_last` | undefined | undefined | bisect module | bisect module | no |
| top-k frequent | sort by count | `_counts` (rederived on bf16) | undefined | undefined | heap | heap | no |
| longest increasing subsequence | quadratic DP | `␣j` | undefined | patience sorting | patience sorting | patience sorting | no |

The subtraction forecast was undefined on 7 tasks because the default kept at least half of the attempts in every veto round, and on 3 more because no round produced 20 attempts off the default. Bans then failed on most tasks (Table 95): only 5 of 12 passed the gate. On nonoverlapping intervals, topological order, first and last position and longest increasing subsequence the model kept its default on almost every sample whatever the wording, and 88% to 100% of the programs that kept the banned mechanism named neither its alias nor its display name.

**Table 95.** What the named ban did (N = 100 per task; landing = attempted programs not using the default), against the ban-free arms. Avoidance is one minus the default's share of attempts (Wilson 95%). Source: bench forecast experiment `README.md`, `results/c1_events.jsonl`.

| Task | Ban avoidance | Gate | Ban landing | Twin default share | One-shot veto avoidance | Best ban-free push (avoidance) | Band patch avoidance | Frozen rule winner |
|-|-|-|-|-|-|-|-|-|
| kth smallest | 0.97 [0.92, 0.99] | pass | quickselect 59, size-k heap 38 | 0.96 | 0.38 | novelty 1.00 | 1.00 | ladder |
| substring search | 0.40 [0.31, 0.50] | fail | KMP 21, built-in find 16, Rabin-Karp 2, Z algorithm 1 | 1.00 | 0.00 | novelty 0.26 | 0.00 | none |
| find duplicate | 0.79 [0.70, 0.86] | pass | index marking 73, Floyd cycle detection 5, sort and adjacent check 1 | 1.00 | 0.00 | novelty 0.02 | 0.04 | ladder (undefined, scored uniform) |
| two sum | 0.86 [0.78, 0.91] | pass | brute force 86 | 1.00 | 0.00 | novelty 0.08 | 0.22 | proximity |
| connected components | 1.00 [0.96, 1.00] | pass | BFS 83, DFS 17 | 1.00 | 0.33 | random direction 3, 0.26 | 1.00 | ladder (undefined, scored uniform) |
| nonoverlapping intervals | 0.00 [0.00, 0.04] | fail | none | 1.00 | 0.00 | none (0.00) | 0.00 | none |
| Fibonacci | 0.34 [0.25, 0.44] | fail | other 33, fast doubling 1 | 1.00 | 0.00 | novelty 0.40 | 0.00 | none |
| topological order | 0.08 [0.04, 0.15] | fail | DFS postorder 8 | 1.00 | 0.00 | none (0.00) | 0.00 | none |
| merge intervals | 0.58 [0.48, 0.67] | pass | other 44, union find 14 | 1.00 | 0.00 | none (0.00) | 0.14 | proximity |
| first and last position | 0.03 [0.01, 0.08] | fail | other 2, bisect module 1 | 0.80 | 0.42 | nonce 0.36 | 0.00 | none |
| top-k frequent | 0.48 [0.38, 0.58] | fail | heap 32, quickselect on counts 15, other 1 | 0.96 | 0.04 | nonce 0.04 | 0.00 | none |
| longest increasing subsequence | 0.02 [0.01, 0.07] | fail | patience sorting 2 | 1.00 | 0.00 | novelty 0.68 | 0.00 | none |

The frozen rule returned the SUBTRACTION/LADDER branch, with the ladder advancing: on the five gated events, all with disagreeing nominations, the ladder won 3 (kth smallest, find duplicate, connected components) and proximity 2 (two sum, merge intervals). Table 96 shows why that label carries little. On find duplicate and connected components the ladder was undefined and scored as uniform, and it won because every defined forecast named the wrong survivor. Counting only wins by defined forecasts (a post hoc check, not preregistered) gives ladder 1 and proximity 2, and no family advances. Against the uniform reference over the gated events, the mean differences are ladder +0.06 (task bootstrap 95% [0.00, 0.18]), subtraction -0.69 [-1.42, 0.00], proximity -1.53 [-2.96, 0.09] and association -1.78 [-2.73, -0.73]: no family forecasts better than uniform on average, and the association forecast is worse than uniform on all five events.

**Table 96.** Mean log score per attempt not banned for each forecast (nats; higher is better; uniform over the survivors is the reference). Gated events are marked †. The 8-bit likelihood column is the frozen bench likelihood argmax, a descriptive forecast. Source: bench forecast experiment `results/c1_events.jsonl`.

| Task | Subtraction | Ladder | Association | Proximity | 8-bit likelihood | Uniform |
|-|-|-|-|-|-|-|
| kth smallest † | -1.630 | -1.326 | -1.842 | -4.605 | -1.842 | -1.630 |
| substring search | -1.630 | -1.630 | -2.220 | -2.788 | -1.630 | -1.630 |
| find duplicate † | -3.210 | -1.406 | -4.108 | -4.327 | -1.406 | -1.406 |
| two sum † | -1.119 | -1.119 | -4.094 | -0.055 | -1.119 | -1.119 |
| connected components † | -2.789 | -1.119 | -3.408 | -4.094 | -1.119 | -1.119 |
| nonoverlapping intervals | n/a | n/a | n/a | n/a | n/a | n/a |
| Fibonacci | -3.830 | -2.672 | -3.917 | -3.917 | -3.830 | -3.830 |
| topological order | -1.119 | -1.119 | -0.055 | -1.119 | -1.119 | -1.119 |
| merge intervals † | -3.140 | -3.140 | -3.858 | -2.979 | -3.140 | -3.140 |
| first and last position | -2.846 | -2.846 | -2.623 | -2.623 | -2.846 | -2.846 |
| top-k frequent | -1.177 | -1.177 | -1.398 | -1.398 | -1.177 | -1.177 |
| longest increasing subsequence | -0.713 | -2.234 | -0.046 | -0.046 | -0.713 | -0.713 |

[FIGURE:fig_bench_forecasts]

The landings were specific to the banned task and mostly unforeseen. Find duplicate went to index marking, which places each value at index value minus one: the model wrote it only once in 40 template-forced attempts in the bench build (adherence 0.28 over all forced prompts), and no family nominated it. Connected components went to BFS (83 of 100) while subtraction and association said DFS. Merge intervals went mostly to programs labelled other, a merge sweep without sorting that failed every time (0 of 44). On Fibonacci the programs labelled other used Binet's closed form, which also failed (0 of 33). Only the kth smallest landing (quickselect: ladder, association and the 8-bit likelihood) and the two sum landing (brute force: proximity) were hit by a top-1 nomination. On 3 of the 5 gated events no family's top-1 named the realised landing.

**Signature vetoes move the surface, not the algorithm.** The distinctive n-gram fired in 95% of twin samples and the redraw always avoided it, yet the default survived every persistent and iterated round on 9 of 12 tasks. The model respelled the same mechanism: on kth smallest `nums.sort()` became `return sorted(nums)[k-1]`, and on two sum the next round's distinctive token was `␣compliment`, a misspelling that dodges `␣complement`. The vetoed text reappeared under another token split in 23% of one-shot samples and 54% by round 2. Where vetoes did move off the default, most outputs were invalid. The sham veto of a shared token broke programs without moving the algorithm (for example, the model indented with non-breaking spaces after the indentation token was masked). The test of whether the one-shot veto reproduces the ban's landing was therefore undetermined: the one-shot veto never reached 0.5 avoidance on a gated task (kth smallest 0.38, connected components 0.33, others 0). Descriptively, the last iterated round was eligible on find duplicate and connected components, and both landed elsewhere than the ban: sort and adjacent check against the ban's index marking (Jensen-Shannon divergence 0.77 against a template resampling 95th percentile of 0.09), and DFS against the ban's BFS (0.58 against 0.09).

**Generic pushes rarely move this collapsed model.** Nonce bans moved nothing except on first and last position, whose twin was already noisy. The novelty instruction moved kth smallest (all 50 off the default, 45 to quickselect), longest increasing subsequence, Fibonacci, substring search and connected components. One of three random directions moved kth smallest (avoidance 0.82, mostly quickselect) and connected components a little (0.26, to DFS); the HF twin control kept the default at 0.98 and 1.00 on those tasks, so the movement is not an engine artefact. The positive control of patching the ban's own task specification states into the twin at layers 12 to 23 reproduced the ban's avoidance only on kth smallest and connected components (1.00 each), partly on two sum (0.22) and merge intervals (0.14), and nowhere else. On most tasks the ban's effect is not carried by the task specification states of that band alone, which Section 3.6 confirms behaviourally.

**Wording.** The banned share differed by template far more than by chance (Table 97), with a likelihood ratio of 374 on 4 degrees of freedom (p about 1e-79). A mixed logistic model put the template standard deviation at 2.0 logits [1.1, 3.5] and the template by task deviation at 1.25 [1.05, 1.49]; a shuffled template placebo gave p = 0.44 (0.39 in the second audit's own likelihood ratio test). Under the fourth template the default kept at least 70% of samples on 10 of 12 tasks.

**Table 97.** Banned programs per template (of 20) under each modal bench ban. Source: bench forecast experiment `results/template_effect.json`.

| Task | First | Second | Third | Fourth | Fifth |
|-|-|-|-|-|-|
| kth smallest | 0 | 0 | 0 | 3 | 0 |
| substring search | 11 | 6 | 19 | 20 | 4 |
| find duplicate | 0 | 1 | 0 | 20 | 0 |
| two sum | 0 | 0 | 0 | 14 | 0 |
| connected components | 0 | 0 | 0 | 0 | 0 |
| nonoverlapping intervals | 20 | 20 | 20 | 20 | 20 |
| Fibonacci | 20 | 6 | 15 | 20 | 5 |
| topological order | 20 | 16 | 19 | 20 | 17 |
| merge intervals | 12 | 5 | 3 | 20 | 2 |
| first and last position | 20 | 20 | 20 | 20 | 17 |
| top-k frequent | 12 | 2 | 16 | 20 | 2 |
| longest increasing subsequence | 20 | 20 | 20 | 20 | 18 |
| All tasks (of 240) | 135 | 96 | 132 | 197 | 85 |

[FIGURE:fig_bench_templates]

**The bench likelihoods on the screen's path.** Rescoring the frozen bench likelihood sets with fp32 activations, the path the likelihood screen had validated, moved the adherence corrected likelihood of a cell by a median 0.88 nats (maximum 9.0) from the 8-bit prompt log probabilities. Every shift above 2 nats sat in a cell with Kish ESS below 5, and the argmax algorithm was unchanged on 12 of 12 tasks. The rescoring code first reproduced 5 stored program scores of the likelihood screen within 0.021 nats. The 8-bit likelihood forecast was defined only on kth smallest, where it named quickselect.

**Checks.** An independent rederivation from the raw label files reproduced every headline number with no mismatch; a task shuffled placebo collapsed the family wins (mean ladder wins 0.52 against 3 observed); a template permutation test gave p = 0.002 on real data and 0.42 on shuffled data; and the hash chain verified. One file changed after the seal: absolute input paths in a configuration module were replaced by relative paths for portability, with the sealed bytes and the diff kept. GPU time was about 45 minutes, judge spend USD 0.024 over 344 calls.

## 3.4 Exposure experiment: show a solution, ban it, and see what replaces it (Qwen3-8B)

**Why.** Under total collapse, every modal ban's association and ladder nominations are close to each other, and bench bans in Qwen3-8B pass the gate on only five tasks. Exposure bans [ARTIFACT:art_WiY4wqHLb9Gy] create events where the two accounts finally disagree: the prompt shows correct programs of a non-default algorithm Y, which the model then copies, and asks for a solution that does not use Y. Subtraction predicts a return to what the model would write without Y in view, which in context is its default; substitution predicts Y's stated alternative.

**Design.** The experiment took every non-default algorithm Y of the 12 frozen bench tasks with at least one correct forced program: 33 Y. We call the 19 whose frozen associate differs from the default priority Y. The prompt shows up to 5 name-scrubbed correct programs of Y and then asks one of three things: write a correct solution, which we call the copy twin; write a correct solution that does not use Y, the named ban (the fifth template); or write a correct solution that uses a different algorithm from the one above, the unnamed ban. Each arm had 50 samples per Y, with seeds shared across arms (Qwen3-8B bf16, vLLM 0.11.0, one 23 GB NVIDIA GPU). Four forecasts were committed by hash before any ban sample: ladder (the context-free default), association (the modal frozen answer for Y), proximity (the survivor whose forced programs are nearest the shown programs by Zhang-Shasha tree edit distance [64]) and the subtraction forecast in context (the landing of an iterated persistent signature veto of Y under the copy twin prompt, with no ban text). GPU smoke tests confirmed the veto: 0 of 20 veto samples contained the vetoed n-gram against 20 of 20 copy samples, an inert veto left 20 of 20 outputs identical, and veto and copy twins diverged exactly at the vetoed position in 20 of 20. Of 10,600 programs, 7,478 were labelled by agreeing runtime and AST labellers, 1,398 by the judge, 147 by runtime alone, and 1,577 had no code block (mostly from veto rounds).

**Showing a solution makes the model copy it, and banning it sends the model home.** Under the copy twin a mean 0.93 of attempts used the shown algorithm (median 1.00; none below 0.2), and the default appeared in 0.05. Under the named ban, avoidance averaged 0.95 and the default's share of attempts rose to 0.72 (Table 98). We call this return to the context-free default *snap-back*. In 24 of the 31 gated named events the modal replacement was the default (14 of 18 for priority Y). Named and unnamed bans picked the same modal replacement for 0.88 of Y, and their landings were consistent under the Jensen-Shannon resampling null for 0.79 of Y: naming Y adds little beyond asking for a different algorithm.

**Table 98.** The default's share of attempts by arm: the mean over the 33 shown algorithms of each one's share (over 29 for the final veto round, where 4 shown algorithms had no valid attempts). Source: exposure experiment `README.md`, `results/other_reports.json`.

| Copy twin | Final veto round under the copy twin | Named ban | Unnamed ban |
|-|-|-|-|
| 0.05 | 0.10 | 0.72 | 0.82 |

[FIGURE:fig_exposure_snapback]

Table 99 gives every named exposure event. The frozen rule (at least 3 wins by 0.10 nats on gated, disagreeing events) advanced the ladder with 7 wins, against subtraction 2, association 2 and proximity 0, so the frozen branch is SUBTRACTION/LADDER, with the ladder advancing. Gating removed two events (size-k heap on kth smallest and patience sorting on longest increasing subsequence, where Y was kept), and 30 of the 31 gated events had disagreeing nominations.

**Table 99.** Every named exposure event (N = 50 per arm). The winner is the family that beats the next best by at least 0.10 nats on a gated event with disagreeing nominations (none when the top two tie; n/a when the event is ungated or its nominations do not disagree). An undefined subtraction forecast is scored as uniform. Source: exposure experiment `results/c1_events.jsonl`, `results/arm_stats.json`.

| Task | Shown algorithm Y | Priority | Default | Associate of Y | Copy: share of Y | Named: avoidance | Named landing (attempts not Y) | Default share | Gate | Subtraction top-1 | Proximity top-1 | Winner |
|-|-|-|-|-|-|-|-|-|-|-|-|-|
| kth smallest | size-k heap | yes | full sort | quickselect | 1.00 | 0.20 | full sort 10 | 0.20 | fail | undefined | heapify and pop | n/a |
| kth smallest | heapify and pop | yes | full sort | quickselect | 1.00 | 1.00 | quickselect 45, full sort 5 | 0.10 | pass | undefined | full sort | association |
| kth smallest | quickselect | yes | full sort | heapify and pop | 1.00 | 1.00 | full sort 50 | 1.00 | pass | undefined | median of medians | ladder |
| kth smallest | median of medians | yes | full sort | quickselect | 1.00 | 1.00 | quickselect 50 | 0.00 | pass | quickselect | quickselect | none |
| kth smallest | counting sort | yes | full sort | quickselect | 0.80 | 1.00 | full sort 49, quickselect 1 | 0.98 | pass | undefined | full sort | ladder |
| substring search | KMP | no | naive | naive | 1.00 | 1.00 | naive 50 | 1.00 | pass | undefined | Boyer-Moore-Horspool | none |
| substring search | Rabin-Karp | yes | naive | KMP | 1.00 | 1.00 | naive 50 | 1.00 | pass | undefined | Boyer-Moore-Horspool | ladder |
| substring search | Z algorithm | yes | naive | KMP | 1.00 | 1.00 | naive 44, KMP 6 | 0.88 | pass | undefined | Boyer-Moore-Horspool | ladder |
| substring search | Boyer-Moore-Horspool | yes | naive | KMP | 1.00 | 1.00 | naive 50 | 1.00 | pass | undefined | naive | ladder |
| substring search | built-in find | yes | naive | KMP | 1.00 | 1.00 | naive 50 | 1.00 | pass | undefined | naive | none |
| find duplicate | sort and adjacent check | yes | hash set | Floyd cycle detection | 1.00 | 1.00 | hash set 50 | 1.00 | pass | undefined | hash set | none |
| find duplicate | Floyd cycle detection | no | hash set | hash set | 1.00 | 1.00 | hash set 50 | 1.00 | pass | undefined | hash set | none |
| find duplicate | binary search on values | yes | hash set | Floyd cycle detection | 0.98 | 1.00 | hash set 50 | 1.00 | pass | undefined | hash set | ladder |
| find duplicate | index marking | yes | hash set | Floyd cycle detection | 1.00 | 1.00 | hash set 50 | 1.00 | pass | undefined | sort and adjacent check | ladder |
| two sum | sort and two pointers | no | hash map | hash map | 1.00 | 1.00 | hash map 50 | 1.00 | pass | undefined | hash map | none |
| two sum | brute force | yes | hash map | sort and two pointers | 0.36 | 1.00 | hash map 50 | 1.00 | pass | hash map | hash map | none |
| two sum | sort and binary search | yes | hash map | sort and two pointers | 1.00 | 1.00 | hash map 50 | 1.00 | pass | undefined | hash map | none |
| connected components | BFS | yes | union find | DFS | 1.00 | 1.00 | DFS 50 | 0.00 | pass | undefined | DFS | none |
| connected components | DFS | yes | union find | BFS | 1.00 | 1.00 | BFS 50 | 0.00 | pass | undefined | BFS | association |
| connected components | label propagation | yes | union find | DFS | 0.84 | 1.00 | union find 49, DFS 1 | 0.98 | pass | union find | union find | none |
| nonoverlapping intervals | memoised recursion | no | greedy by end | greedy by end | 1.00 | 1.00 | DP with bisect 41, other 7, greedy by end 2 | 0.04 | pass | undefined | greedy by end | subtraction |
| nonoverlapping intervals | DAG longest path | no | greedy by end | greedy by end | 1.00 | 0.94 | greedy by end 47 | 0.94 | pass | undefined | greedy by end | none |
| Fibonacci | memoised recursion | no | iteration | iteration | 1.00 | 1.00 | iteration 50 | 1.00 | pass | undefined | iteration | none |
| Fibonacci | matrix power | no | iteration | iteration | 1.00 | 1.00 | iteration 50 | 1.00 | pass | undefined | fast doubling | none |
| Fibonacci | fast doubling | no | iteration | iteration | 1.00 | 1.00 | other 49, iteration 1 | 0.02 | pass | undefined | iteration | none |
| merge intervals | union find | no | sort and sweep | sort and sweep | 1.00 | 1.00 | sort and sweep 50 | 1.00 | pass | undefined | sort and sweep | none |
| first and last position | bisect module | no | binary search | binary search | 1.00 | 1.00 | other 49, binary search 1 | 0.02 | pass | undefined | binary search | none |
| first and last position | exponential search | no | binary search | binary search | 0.28 | 1.00 | binary search 50 | 1.00 | pass | binary search | binary search | n/a |
| top-k frequent | heap | no | sort by count | sort by count | 1.00 | 1.00 | sort by count 50 | 1.00 | pass | undefined | sort by count | none |
| top-k frequent | bucket sort | no | sort by count | sort by count | 0.36 | 1.00 | sort by count 50 | 1.00 | pass | undefined | heap | none |
| top-k frequent | quickselect on counts | yes | sort by count | heap | 1.00 | 0.94 | sort by count 31, bucket sort 7, other 6, heap 3 | 0.62 | pass | undefined | bucket sort | none |
| longest increasing subsequence | patience sorting | no | quadratic DP | quadratic DP | 1.00 | 0.16 | quadratic DP 8 | 0.16 | fail | undefined | quadratic DP | n/a |
| longest increasing subsequence | Fenwick tree | yes | quadratic DP | patience sorting | 1.00 | 1.00 | quadratic DP 35, patience sorting 15 | 0.70 | pass | undefined | quadratic DP | subtraction |

The paired tests point the same way but none survives correction (Table 100). Over the 30 gated disagreeing named events, paired Wilcoxon signed-rank tests [65] of the per-event log score differences, Holm corrected over four comparisons, favour the ban-free families over association by about 1 nat per attempt, with task cluster bootstrap intervals above zero, but Holm adjusted p stays at 0.081. Top-1 hit rates on the gated named events were 0.77 for the ladder, 0.61 for proximity, 0.45 for association and 0.36 for subtraction. The unnamed events, which are descriptive, give the same branch, and there the ladder beats association after Holm correction (+1.42 nats, adjusted p = 0.0056).

**Table 100.** Paired log score differences over the 30 gated, disagreeing named exposure events (positive favours the first family). Source: exposure experiment `results/c1_summary.json`.

| Difference | Mean (nats) | Task cluster 95% CI | p | Holm adjusted p |
|-|-|-|-|-|
| Subtraction minus association | +1.02 | [0.35, 1.56] | 0.020 | 0.081 |
| Ladder minus association | +1.29 | [0.10, 2.38] | 0.027 | 0.081 |
| Ladder minus proximity | +0.50 | [-0.40, 1.16] | not reported | 0.159 |
| Subtraction minus proximity | +0.23 | not reported | not reported | 0.96 |

**How strong the verdict is.** The counting rule is not a significance test. In a unit test with no information, it advanced some family in 85% of 200 simulated draws, while the Holm-corrected Wilcoxon test erred in 2%; on the real events, a label permutation placebo advanced some family in 100% of draws (the ladder in 43%). The branch label is therefore weak evidence, and the paired tests are the informative part. The signature veto rarely removed Y. The subtraction forecast in context was defined for only 4 of 33 Y (median of medians to quickselect, brute force to hash map, label propagation to union find, exponential search to binary search). For 25 of 33 Y, Y still re-emerged in at least 20% of attempts after three rounds. The veto cost a mean 0.70 of pass rate, and 46% of final round outputs were invalid. Because an undefined subtraction forecast is uniform, its tied top-1 is what makes almost every event disagreeing. Every preregistered sensitivity returned the ladder with 7 to 9 wins (subtraction top-1, excluding co-vetoed survivors, priority Y only with 18 events, token distance proximity, correct-only landings, and excluding labeller-flagged tasks) except the one that drops events with an undefined subtraction forecast, which leaves 2 events and is undetermined. An exploratory comparison of ladder, association and proximity on the 21 events where those three disagree gave wins 8, 3 and 0 (ladder minus association p = 0.027, Holm over three 0.081). The secondary exposure test, whether the ban's modal survivor matches the veto's where the associate differs, had 2 qualifying events (brute force and label propagation); both agreed, but both landings are the default, so this is snap-back, not a test of substitution.

**Wording.** A template arm (first to fourth templates, 10 samples for each of the 19 priority Y; descriptive and never in the contest) gave mean avoidance 0.93, 0.94, 0.96 and 0.81: the fourth template is again the weakest. A stop token bug in the first round-2 veto run (the end-of-turn token was chosen as the n-gram) was found and fixed; the 750 affected samples are kept apart. Deduplication left 11 of 33 Y with a single shown program. GPU time was about 1.0 GPU hour, judge spend USD 0.096 over 1,229 calls, and an independent rederivation matched all 66 events.

## 3.5 Llama bench experiment: the same forecast contest in a second model family

**Why.** Llama-3.1-8B-Instruct [22] is less collapsed than Qwen3-8B on the bench pilot, so it supplies present minor bans, where a correct minor algorithm already exists and subtraction makes a non-trivial prediction. This experiment [ARTIFACT:art_Q-qh-9HhPoWo] replicated the frozen forecast contest on the 12 bench tasks in bf16 (revision 0e9e39f), with every forecast computed without ban text and hash chained before any ban prompt was rendered (a grep audit found 0 ban prompts in the 10,328 rows generated before the commit).

**Design.** The default of each task was frozen from a decision set (the 8-bit Llama pilot pooled with 600 bf16 neutral twin samples after a homogeneity test) as the modal correct label when at least 10 programs were correct, else the modal attempted label (Table 101). Present minor events required at least 10% of correct programs, at least 3 correct, and at least 10 correct programs on the task. The four forecasts were built as in the Qwen3-8B experiment. The subtraction forecast used exact one-shot, persistent and iterated signature vetoes by truncate and redraw; the ladder pooled the nonce ban, the novelty instruction and three matched-norm random directions added at the task specification positions of layers 11 to 21 during prefill; association used Llama's own frozen answers; and proximity used Zhang-Shasha distance [64]. Association and proximity took a form that transfers the default's mass, with point mass forms as sensitivities. Then 1,800 bans were sampled (12 modal and 6 present minor events, 5 templates by 20) and labelled with the bench labellers; references were recovered 50 of 50, and gold agreement was 0.959. A second blind judge audited 60 Llama programs at 0.88 agreement, below 0.85 on four tasks (nonoverlapping intervals, kth smallest, two sum, top-k frequent).

**Table 101.** Llama defaults and events, frozen before any ban (decision set: 8-bit pilot plus bf16 neutral twins). Source: Llama bench experiment `README.md`, `predictions/events.json`.

| Task | Pilot mode | Default | Default from attempts | Valid programs | Correct programs | Default share | Hill_cc |
|-|-|-|-|-|-|-|-|
| kth smallest | heapify and pop | full sort | | 94 | 18 | 0.17 | 3.80 |
| substring search | naive | naive | | 89 | 49 | 0.54 | 2.00 |
| find duplicate | hash set | hash set | | 93 | 34 | 0.44 | 1.48 |
| two sum | hash map | hash map | | 99 | 84 | 0.97 | 1.07 |
| connected components | union find | union find | | 97 | 74 | 0.75 | 1.59 |
| nonoverlapping intervals | greedy by end | greedy by end | yes | 89 | 8 | 0.63 | 2.46 |
| Fibonacci | matrix power | matrix power | | 96 | 44 | 0.76 | 1.78 |
| topological order | Kahn | Kahn | | 99 | 88 | 0.98 | 1.06 |
| merge intervals | sort and sweep | sort and sweep | | 89 | 65 | 1.00 | 1.00 |
| first and last position | binary search | binary search | | 93 | 54 | 0.99 | 1.10 |
| top-k frequent | heap | heap | | 86 | 22 | 0.62 | 1.80 |
| longest increasing subsequence | quadratic DP | quadratic DP | | 94 | 68 | 0.87 | 1.08 |

Present minor events: top-k frequent sort by count (6 of 22 correct), kth smallest heapify and pop (4 of 18), kth smallest quickselect (4 of 18), substring search KMP (9 of 49), connected components DFS (13 of 74), kth smallest size-k heap (3 of 18).

**The contest does not resolve in Llama.** Thirteen of 18 events passed the gate and 11 were gated and disagreeing, but only 2 had a winner by 0.10 nats (Table 102). One was the subtraction forecast on two sum, through its undefined forecast scored as uniform, because the ban split between sort and two pointers (42) and brute force (32). The other was association on kth smallest heapify and pop. No family advances; the preregistered branch is NO FAMILY ADVANCES, aimed but unresolved. The landing is aimed: the ladder and association each named the realised landing on 7 of 13 gated events, against a chance rate of about 0.27 (exact binomial p = 0.033 each); subtraction hit 4 of 12 (p = 0.38) and proximity 3 of 13 (p = 0.71). Five defaults resisted the ban itself (nonoverlapping intervals, topological order, merge intervals, first and last position, longest increasing subsequence; avoidance 0.04 to 0.30).

**Table 102.** Every Llama ban event (N = 100). s_X is the banned algorithm's share of attempts in the decision set before the ban; † marks a present minor event. Each family's top-1 is given with its mean log score per attempt not banned in parentheses; a forecast marked undefined is scored as uniform. Source: Llama bench experiment `README.md`, `results/c1_events.jsonl`.

| Event | s_X | Avoidance | Gate | Attempts not banned | Modal landing | Subtraction | Ladder | Association | Proximity | Renormalised baseline | Winner (margin) | Hill_cc (correct programs) | Other / invalid |
|-|-|-|-|-|-|-|-|-|-|-|-|-|-|
| kth smallest, ban full sort | 0.17 | 0.95 | pass | 87 | quickselect | heapify and pop (-1.71) | other (-1.46) | quickselect (-1.40) | size-k heap (-1.66) | -1.64 | none (0.06) | 1.00 (15) | 0.09 / 0.08 |
| substring search, ban naive | 0.54 | 0.79 | pass | 64 | KMP | Rabin-Karp (-1.20) | KMP (-1.25) | KMP (-1.18) | built-in find (-1.83) | -1.20 | none (0.02) | 1.38 (20) | 0.05 / 0.19 |
| find duplicate, ban hash set | 0.44 | 0.76 | pass | 71 | other | other (-0.98) | other (-1.00) | Floyd cycle detection (-1.53) | sort and adjacent check (-1.37) | -1.02 | none (0.02) | 3.59 (7) | 0.53 / 0.06 |
| two sum, ban hash map | 0.97 | 0.91 | pass | 86 | sort and two pointers | undefined (-1.39) | other (-1.90) | sort and two pointers (-1.94) | brute force (-2.37) | -1.39 | subtraction (0.51) | 1.63 (34) | 0.07 / 0.05 |
| connected components, ban union find | 0.75 | 0.82 | pass | 78 | DFS | DFS (-1.00) | DFS (-0.80) | DFS (-0.98) | DFS (-0.98) | -0.98 | none (0.18) | 1.68 (42) | 0.04 / 0.05 |
| nonoverlapping intervals, ban greedy by end | 0.63 | 0.29 | fail | 26 | other | other (-0.89) | other (-0.97) | DP with bisect (-1.51) | memoised recursion (-1.59) | -0.85 | none (0.08) | n/a (0) | 0.21 / 0.11 |
| Fibonacci, ban matrix power | 0.76 | 0.79 | pass | 72 | iteration | other (-1.13) | iteration (-1.10) | fast doubling (-2.31) | memoised recursion (-1.94) | -1.21 | none (0.03) | 1.72 (44) | 0.13 / 0.09 |
| topological order, ban Kahn | 0.98 | 0.18 | fail | 17 | DFS postorder | undefined (-1.39) | undefined (-1.39) | DFS postorder (-0.92) | source removal (-3.81) | -1.39 | none (0.46) | 1.00 (1) | 0.04 / 0.04 |
| merge intervals, ban sort and sweep | 1.00 | 0.30 | fail | 25 | other | undefined (-1.11) | undefined (-1.11) | union find (-3.13) | interval tree (-3.71) | -1.11 | none (0.00) | n/a (0) | 0.23 / 0.18 |
| first and last position, ban binary search | 0.99 | 0.04 | fail | 2 | other | undefined (-1.11) | undefined (-1.11) | bisect module (-3.76) | bisect module (-3.76) | -1.11 | none (0.00) | 1.00 (1) | 0.02 / 0.03 |
| top-k frequent, ban heap | 0.62 | 0.89 | pass | 84 | sort by count | sort by count (-0.74) | sort by count (-0.68) | sort by count (-0.70) | sort by count (-0.70) | -0.66 | none (0.02) | 1.31 (13) | 0.05 / 0.06 |
| longest increasing subsequence, ban quadratic DP | 0.87 | 0.23 | fail | 22 | patience sorting | undefined (-1.10) | undefined (-1.10) | Fenwick tree (-2.56) | patience sorting (-1.02) | -0.83 | none (0.08) | 1.00 (8) | 0.09 / 0.05 |
| top-k frequent, ban sort by count † | 0.36 | 0.82 | pass | 75 | quickselect on counts | heap (-1.05) | heap (-1.02) | heap (-1.06) | bucket sort (-1.34) | -1.02 | none (0.03) | 1.19 (24) | 0.09 / 0.09 |
| kth smallest, ban heapify and pop † | 0.33 | 0.88 | pass | 77 | quickselect | other (-1.54) | full sort (-1.57) | quickselect (-1.33) | size-k heap (-1.81) | -1.57 | association (0.21) | 2.57 (27) | 0.09 / 0.12 |
| kth smallest, ban quickselect † | 0.12 | 0.76 | pass | 71 | full sort | full sort (-1.65) | full sort (-1.73) | full sort (-1.56) | size-k heap (-1.79) | -1.73 | none (0.09) | 2.12 (34) | 0.10 / 0.06 |
| substring search, ban KMP † | 0.26 | 0.70 | pass | 66 | Boyer-Moore-Horspool | other (-0.99) | naive (-1.01) | Rabin-Karp (-1.22) | naive (-1.01) | -1.01 | none (0.01) | 1.14 (34) | 0.09 / 0.06 |
| connected components, ban DFS † | 0.25 | 0.89 | pass | 85 | BFS | union find (-0.35) | union find (-0.34) | union find (-0.34) | BFS (-0.47) | -0.34 | none (0.00) | 1.15 (65) | 0.02 / 0.04 |
| kth smallest, ban size-k heap † | 0.24 | 0.84 | pass | 78 | full sort | heapify and pop (-1.68) | full sort (-1.72) | quickselect (-1.70) | heapify and pop (-1.88) | -1.72 | none (0.02) | 2.23 (27) | 0.10 / 0.07 |

The exact Wilcoxon tests over the 11 gated disagreeing events, Holm corrected, separate the ban-free families from proximity but not from association. Subtraction minus proximity (+0.345 nats [0.190, 0.633], Holm 0.0088) and ladder minus proximity (+0.306 [0.204, 0.513], Holm 0.0078) are rejected; subtraction minus association (+0.172 [-0.049, 0.606], p = 0.52) and ladder minus association (+0.133 [-0.056, 0.542], p = 0.77) are not. In Llama, code proximity is the worst forecast, and association, subtraction and the ladder cannot be told apart at this N, which is below the pooled floor of 16 events.

The verdict is fragile. Of ten preregistered sensitivity rows, three return substitution with association advancing on 3 wins: rescoring on correct programs only, the bf16-only decision set, and dropping the fourth template. Excluding the task whose default came from attempts and the tasks the label audit flagged leaves 5 disagreeing gated events and reads X specific but unaimed. The point mass forms, dropping co-vetoed survivors and dropping any other single template all keep NO FAMILY ADVANCES.

**Signature vetoes rarely remove a Llama default either (Table 103).** Only the heap of top-k frequent collapsed (0.02 once `(k` and `␣heapq` were both masked). Elsewhere the default re-emerged at 0.20 to 0.96 in the last persistent round; hash map (0.89), sort and sweep (0.88), Kahn and binary search (0.96) barely moved.

**Table 103.** Share of the banned algorithm among veto attempts per round (persistent, iterated arm; weighted counts for present minor events; ␣ marks a space in the n-grams). Source: Llama bench experiment `README.md`.

| Event | Round-1 n-gram | Round 1 | Round 2 | Round 3 | Note |
|-|-|-|-|-|-|
| kth smallest, ban full sort | `,` | 0.20 | | | co-vetoes every survivor |
| substring search, ban naive | `1):\n` | 0.44 | 0.42 | 0.54 | not carried by a small set of surface tokens; co-vetoes Rabin-Karp |
| find duplicate, ban hash set | `␣nums:\n␣␣␣␣␣␣␣` | 0.38 | 0.26 | 0.26 | not carried by surface tokens |
| two sum, ban hash map | `␣i]\n` | 0.93 | 0.95 | 0.89 | not carried by surface tokens |
| connected components, ban union find | `␣def␣find` | 0.59 | 0.57 | 0.23 | not carried by surface tokens |
| nonoverlapping intervals, ban greedy by end | `.sort` | 0.60 | 0.50 | 0.36 | not carried by surface tokens; co-vetoes DP with bisect |
| Fibonacci, ban matrix power | `␣matrix` | 0.46 | 0.43 | 0.28 | not carried by surface tokens |
| topological order, ban Kahn | `␣queue` | 0.98 | 0.96 | 0.96 | not carried by surface tokens |
| merge intervals, ban sort and sweep | `\ndef␣solve` | 0.84 | 1.00 | 0.88 | not carried by surface tokens |
| first and last position, ban binary search | `␣=␣0,` | 0.98 | 0.96 | 0.96 | not carried by surface tokens |
| top-k frequent, ban heap | `(k` | 0.57 | 0.02 | | removed |
| longest increasing subsequence, ban quadratic DP | `[j]␣+` | 0.85 | 0.83 | 0.80 | not carried by surface tokens |
| top-k frequent, ban sort by count † | `␣[` | 0.37 | 0.34 | 0.35 | not carried by surface tokens; co-vetoes heap and quickselect on counts |
| kth smallest, ban heapify and pop † | `␣{}\n␣␣␣` | 0.25 | 0.15 | | |
| kth smallest, ban quickselect † | `␣quick` | 0.12 | | | |
| substring search, ban KMP † | `␣␣␣␣␣␣␣␣␣␣␣␣␣␣␣␣j` | 0.26 | 0.24 | | |
| connected components, ban DFS † | `␣dfs` | 0.17 | | | |
| kth smallest, ban size-k heap † | `.n` | 0.09 | | | |

Of the two events where the one-shot veto moved at least half of the banned algorithm's attempts, neither shared the ban's modal survivor within the template bootstrap null (0 of 2, against a preregistered bar of two thirds, quoted for reference only). The test that matters most for substitution is the present minor gain (Table 104): if a named ban only removes the minor algorithm, the associate's share under the ban should equal its share under the persistent veto of that algorithm. On two of six events the associate gains more under the named ban (kth smallest heapify and pop to quickselect, +0.25 [0.12, 0.37]; kth smallest quickselect to full sort, +0.24 [0.10, 0.36]); on substring search KMP the associate (Rabin-Karp) is less frequent under the ban (-0.08 [-0.17, -0.00]); on three it is unchanged. Naming the banned algorithm sometimes steers Llama toward its associate beyond what removing it does, but not consistently.

**Table 104.** Present minor events: the associate's share under the named ban against the persistent veto of the same algorithm (Newcombe 95% intervals [42]). Source: Llama bench experiment `README.md`.

| Event | Associate | Ban share | Veto share | Baseline share | Ban minus veto |
|-|-|-|-|-|-|
| top-k frequent, ban sort by count | heap | 0.59 | 0.63 | 0.62 | -0.04 [-0.18, 0.10] |
| kth smallest, ban heapify and pop | quickselect | 0.42 | 0.17 | 0.12 | 0.25 [0.12, 0.37] |
| kth smallest, ban quickselect | full sort | 0.44 | 0.20 | 0.17 | 0.24 [0.10, 0.36] |
| substring search, ban KMP | Rabin-Karp | 0.04 | 0.12 | 0.12 | -0.08 [-0.17, -0.00] |
| connected components, ban DFS | union find | 0.82 | 0.81 | 0.75 | 0.01 [-0.10, 0.12] |
| kth smallest, ban size-k heap | quickselect | 0.22 | 0.18 | 0.12 | 0.04 [-0.08, 0.15] |

**Pushes.** The nonce ban left the default near its baseline on most tasks. Matched-norm random directions moved the default substantially on a few tasks (Fibonacci matrix power 0.76 to 0.16 to 0.51; top-k frequent heap 0.62 to 0.39 to 0.56), and the novelty instruction lowered the default almost everywhere. The realised layer-21 displacement of the random pushes was about three times the ban's, because pushes at layers 11 to 20 propagate, so the ladder inputs are generous pushes. A second blind judge re-audited 187 ban outputs labelled other and called 8 (4%) the banned algorithm and 24 a catalogue survivor; other is never folded into avoidance.

**The path task screen (descriptive, never pooled).** On the iteration-2 Llama path tasks, the same ban-free families were scored against the Llama replication's existing ban landings, using that experiment's own prompt builders (10 of 10 prompts reproduced byte for byte) and labeller (Table 105). The vetoes fired (25 of 50 grid and 40 to 48 of 50 shortest path pass-1 samples) but BFS (0.52 to 0.58) and Dijkstra (0.78 to 0.82) re-emerged through other surface forms in every round. On the grid task all four families named DFS, the realised landing. On the shortest path task, the ban's large other share (37 of 100) was not reproduced by any veto round (8 of 50 other each); the novelty instruction came close (18 of 50 other).

**Table 105.** Path task screen in Llama. Source: Llama bench experiment `README.md`.

| Task | Ban landing (Llama replication) | Modal | Subtraction | Ladder | Association | Proximity | Winner | Veto: banned share by round |
|-|-|-|-|-|-|-|-|-|
| Grid | DFS 63, BFS 29, other 6, A* 1, unit weight Dijkstra 1 | DFS | DFS (-0.54) | DFS (-0.88) | DFS (-0.47) | DFS (-0.47) | none (0.00) | `␣queue:\n␣␣␣␣␣␣␣`: 0.56, 0.52, 0.58 |
| Shortest path | Dijkstra 43, Bellman-Ford/SPFA 18, other 37, Floyd-Warshall 2 | other | undefined (-1.59) | undefined (-1.59) | Bellman-Ford/SPFA (-1.79) | Floyd-Warshall (-2.81) | none (0.00) | `␣continue`: 0.82, 0.78, 0.80 |

**Checks.** Input integrity, hooks, prompts, sampler, scoring and veto tests passed; every committed file preceded the first ban sample; an independent rederivation matched the gate, landings, log scores, wins and branch, and a family permutation placebo advanced a family in 0.00 of 1,000 permutations; the exact Wilcoxon p values, Holm decisions and binomial tests were rederived without the project code. Not rederived: the sensitivity rows, the bootstrap intervals, the one-shot veto comparison, the present minor gain and the screen scores. GPU time was 0.98 hours of logged generation (about 1.8 hours with the GPU held), judge spend USD 0.48.

## 3.6 Bench route experiment: which internal route carries a ban, task by task (Qwen3-8B)

**Why.** Iteration 2 found on the two path tasks that the ban is carried mostly by the prompt states. The hypothesis update made that the second claim of the title account: if a ban only removes the default, the removal should be applied by the task specification states before the first generated token, with generated tokens reading the ban directly only where the one-shot veto does not suffice. This experiment [ARTIFACT:art__5akZ9W9iZM4] measured the route in behaviour on the 12 bench tasks, with the iteration-2 engine.

**Design.** Qwen3-8B ran in bf16 under HF with common random numbers (one uniform per row and step, inverse CDF sampling) and cache splicing by position class, on one 23 GB NVIDIA GPU with batches of 40 rows of one shape class. Each slot ran seven kinds of arm. The full ban (a) and the token-length matched neutral twin (b) are the endpoints. The prompt route (c) splices the twin's condition segment with the ban's task specification and read position states; the direct route (d) splices the ban's condition segment with the twin's later states. The full knockout arm removes the condition span from the cache seen by generated tokens. A one-shot veto arm applies the signature veto of the default under the twin, and prefills force the default's opening or a neutral `def` line under the ban and the twin. N was 100 slots per arm (5 templates by 20), and 13,030 samples were labelled by the frozen bench labellers. Route fractions are defined on the default's share of attempts s as F_prompt = (s_b - s_c) / (s_b - s_a), F_direct = (s_b - s_d) / (s_b - s_a), the interaction I = 1 - F_prompt - F_direct, and the knockout fraction F_knockout = (s_b - s_knockout) / (s_b - s_a), where s_knockout is the default's share under the full knockout. The decision rule (prompt route at least two thirds, with the interval above one half; disconfirmed if the direct route reaches one third) was hash committed before any ban sample.

**Only five bench bans take.** Table 106 gives the default's share in every arm for all 12 tasks. The gate passed on kth smallest (avoidance 0.99), connected components (1.00), two sum (0.83), find duplicate (0.79) and merge intervals (0.59), the same five tasks as in the bench forecast experiment. The fourth template was again the weakest (pooled avoidance 0.19 against 0.42 to 0.62 for the others) and produced 29% of all ban failures.

**Table 106.** The default's share of attempts by arm (N attempted in parentheses), and the ban's landing. Source: bench route experiment `results/shares.json`.

| Task | Full ban (a) | Twin (b) | Prompt route (c) | Direct route (d) | Full knockout | One-shot veto | Ban landing (attempts off the default) |
|-|-|-|-|-|-|-|-|
| kth smallest | 0.01 (100) | 0.95 (100) | 0.01 (100) | 0.25 (100) | 0.01 (100) | 0.59 (100) | quickselect 70, size-k heap 28, heapify and pop 1 |
| connected components | 0.00 (100) | 0.99 (100) | 0.00 (100) | 0.20 (100) | 0.00 (100) | 0.70 (20) | BFS 75, DFS 25 |
| two sum | 0.17 (100) | 1.00 (100) | 0.66 (100) | 0.20 (100) | 0.67 (100) | 1.00 (100) | brute force 83 |
| find duplicate | 0.21 (100) | 1.00 (100) | 0.97 (100) | 0.22 (100) | 0.95 (100) | 1.00 (100) | index marking 77, Floyd cycle detection 1, other 1 |
| merge intervals | 0.41 (100) | 1.00 (100) | 0.77 (100) | 0.99 (100) | 0.74 (100) | 1.00 (69) | other 44, union find 15 |
| substring search | 0.58 (100) | 1.00 (100) | 1.00 (100) | 0.89 (100) | 1.00 (50) | 1.00 (94) | KMP 18, built-in find 17, Boyer-Moore-Horspool 5, Rabin-Karp 2 |
| top-k frequent | 0.59 (100) | 0.93 (100) | 0.97 (100) | 0.77 (100) | 0.94 (50) | 0.93 (100) | heap 30, quickselect on counts 10, other 1 |
| Fibonacci | 0.69 (100) | 1.00 (100) | 0.99 (100) | 0.72 (100) | 0.96 (50) | 1.00 (100) | other 31 |
| topological order | 0.96 (100) | 1.00 (100) | 1.00 (100) | 1.00 (100) | 1.00 (50) | 1.00 (46) | DFS postorder 4 |
| longest increasing subsequence | 0.98 (100) | 1.00 (100) | 1.00 (100) | 1.00 (100) | 1.00 (50) | 1.00 (42) | other 1, patience sorting 1 |
| first and last position | 0.98 (100) | 0.76 (100) | 1.00 (100) | 0.76 (100) | 1.00 (50) | 0.61 (62) | other 1, bisect module 1 |
| nonoverlapping intervals | 1.00 (100) | 1.00 (100) | 1.00 (100) | 1.00 (100) | 1.00 (50) | 1.00 (97) | none |

**The route is task dependent, and pooled it is not the prompt route.** On the five gated tasks the mechanisms differ (Table 107). On kth smallest and connected components the information is redundant: the prompt route alone and the knockout (which removes direct reading) each reproduce the ban, and the direct route alone does most of it as well. On two sum and find duplicate the ban acts almost entirely through generated tokens reading the condition segment: the direct route arm reproduces the ban, while the prompt route and the knockout do not (find duplicate: 0 against 76 discordant slots between the full ban and the prompt route; exact McNemar p below 1e-6). On merge intervals neither route suffices alone. Pooled over the five tasks, the prompt route carries 0.61 and the direct route 0.74 (Table 108). The preregistered route claim is therefore disconfirmed under all three intervals: the direct route exceeds one third, and the prompt route falls below two thirds with a lower bound far under one half. The bootstrap probability that F_prompt is at most one half is 0.28, and that F_direct is at least one third, 0.99. Leaving one template out kept F_prompt between 0.55 and 0.66 and F_direct between 0.71 and 0.84; a Bayesian mixed logistic sensitivity gave 0.74 and 0.89.

**Table 107.** Route fractions on the gated bench tasks (template then slot bootstrap 95% intervals). Source: bench route experiment `results/route.json`.

| Task | F_prompt | F_direct | Interaction | F_knockout | Reading |
|-|-|-|-|-|-|
| kth smallest | 1.00 [1.00, 1.00] | 0.74 [0.36, 0.99] | -0.74 | 1.00 | redundant: either route suffices |
| connected components | 1.00 [1.00, 1.00] | 0.80 [0.40, 1.00] | -0.80 | 1.00 | redundant |
| two sum | 0.41 [0.03, 0.82] | 0.96 [0.80, 1.00] | -0.37 | 0.40 | mostly direct |
| find duplicate | 0.04 [0.00, 0.13] | 0.99 [0.90, 1.05] | -0.03 | 0.06 | direct only |
| merge intervals | 0.39 [0.00, 0.73] | 0.02 [0.00, 0.08] | 0.59 | 0.44 | superadditive: both needed |

**Table 108.** Pooled route fractions over the five gated tasks (ratio of sums; hierarchical task, template and slot bootstrap with 10,000 replicates; the leave-one-task-out jackknife is primary because there are only five clusters). Source: bench route experiment `results/route.json`.

| Quantity | Point | Jackknife 95% (primary) | Percentile 95% | BCa 95% [68] |
|-|-|-|-|-|
| F_prompt | 0.611 | [0.06, 1.17] | [0.23, 0.93] | [0.22, 0.93] |
| F_direct | 0.744 | [0.38, 1.11] | [0.42, 0.97] | [0.27, 0.94] |
| Interaction | -0.355 | [-0.98, 0.27] | [-0.73, 0.14] | [-0.71, 0.17] |
| F_knockout | 0.621 | [0.08, 1.16] | [0.24, 0.93] | [0.24, 0.93] |

[FIGURE:fig_bench_route]

An independent second draw with fresh uniforms (slots 20 to 39, arms a to d on the five gated tasks, N = 100 each) reproduced the picture. Pooled F_prompt was 0.64 [0.27, 0.94] and F_direct 0.74 [0.43, 0.94], per-task fractions moved by about 0.1 at most (find duplicate F_direct 0.99 then 0.93; two sum 0.96 then 0.93; merge intervals F_prompt 0.39 then 0.49), and the Spearman rank agreement between the draws was 0.89 and 0.90. The task differences are not sampling noise. A continuous companion readout (the teacher forced log probability of the default's opening up to its distinctive n-gram, under each arm) split the effect across both routes as behaviour does (pooled 0.40 prompt, 0.45 direct).

**Veto sufficiency does not predict the route.** The update predicted that the direct share would be small where the one-shot veto suffices and large where it does not. The frozen n-gram rule picked identifier or structural tokens with zero collateral (two sum `␣if␣complement`, find duplicate `␣set`, Fibonacci `(`), so the one-shot veto rarely changed the mechanism: veto avoidance V_t was 0.41 on kth smallest, 0.39 on first and last position, 0.30 on connected components and at most 0.07 elsewhere. The veto fired in 61% to 100% of rows, and the model renamed or retokenised (two sum: `if compliment in seen`) or broke the code (connected components: 80 of 100 invalid). Every task was classed in the second commit as needing a large direct route (V_t below 0.5, predicting F_direct of at least 0.25). Four of the five gated tasks hit; merge intervals missed with F_direct 0.02. The Spearman correlation between V_t and F_direct was -0.34, with a one-sided permutation p of 0.30 over five points, which fails the rule. The test is inconclusive, and the comparison of the one-shot veto's landing with the ban's had no eligible task.

**The ban is decided at the opening of the body.** Forcing the default's own opening, up to its distinctive n-gram, undid the ban completely on every gated task (the share of the ban effect undone, P_open, 0.98 to 1.00), while forcing only a neutral `def solve(...):` line undid none of it (-0.12 to 0.01). The depth sweep (Table 109) localises this: the ban holds through the whole `def` line and gives way at the first content token of the default's body, which we call the first body token. On kth smallest, forcing the `def` line and its indentation (10 tokens) leaves the ban intact, and forcing one more token, `␣nums`, undoes it. Under common random numbers, arms a, c and d leave the twin's tokens at the first body token (median token 8 to 10 on kth smallest, two sum, find duplicate and connected components; 19 to 21 on merge intervals, whose shared `if not intervals` guard comes first). Once the first tokens of the default's body are on the page, the model continues the default; the ban is applied at the opening and not re-read in the body, as Qi et al. found for safety refusals [63].

**Table 109.** Share of the ban effect undone by forcing a prefix (P_open), by prefix: a neutral `def` line, or the default's modal program forced to 25%, 50% or 75% of its tokens or up to its distinctive n-gram (forced tokens in parentheses; N = 50 per cell, under the ban and the twin). Source: bench route experiment `README.md`, `results/replication.json`.

| Task | Neutral `def` line | 25% of the program | Up to the distinctive n-gram | 50% | 75% |
|-|-|-|-|-|-|
| kth smallest | -0.01 (9 tokens) | -0.01 (5: `def solve`) | 0.98 (11: `def` line, indent, `␣nums`) | -0.01 (10: `def` line and indent) | 1.00 (16) |
| find duplicate | -0.01 (7) | 1.00 (10: `seen =`) | 1.00 (11: `seen = set`) | 1.00 (20) | 1.00 (29) |
| two sum | 0.01 (9) | 1.00 (13: `seen = {}`) | 1.00 (32) | 1.00 (26) | 1.00 (40) |
| connected components | 0.00 (9) | 1.00 (31, inside `find`) | 1.00 (20: `def find`) | 1.00 (62) | 1.00 (92) |
| merge intervals | -0.12 (8) | 1.00 (30: `intervals.sort(key`) | 1.00 (58) | 1.00 (59) | 1.00 (88) |

[FIGURE:fig_prefill_depth]

**The path task screen.** Under the iteration-2 twin prompts, every veto variant failed to move either path default: one-shot, persistent, iterated rounds with the re-emerged programs' new n-grams, and a veto of the import line itself. The share off the default was 0.00 on the grid task and at most 0.01 on the shortest path task, and the default re-emerged in 99% to 100% of attempts after each round. The committed prediction that the grid one-shot veto would not suffice hit; the prediction that the shortest path one-shot veto would suffice and land on Bellman-Ford/SPFA missed (V = 0). The iteration-2 ban landings recomputed exactly from raw rows (grid DFS 257 of 257; shortest path Bellman-Ford/SPFA 255 of 260). A ban moves these tasks; a surface veto does not.

**Controls and checks.** A placebo splice (one twin's condition segment with another twin's later states) moved the default's share by at most 0.04 on all six tasks where it ran, so splicing itself is inert; the knockout applied to the twin left the default at 1.00 on six tasks. GPU unit tests confirmed common random number determinism, splice identities (splicing a prompt with itself reproduces it in 100% of rows) and zero attention mass on the condition span under the knockout in all 36 layers. A reproduction of the iteration-2 shortest path arms gave banned shares of 0 of 20, 20 of 20, 3 of 20 and 19 of 20 for arms a to d, inside their pass bands. Two audit scripts rederived every headline from raw rows with no mismatch, and shuffling arm labels within slots collapsed the mean gap between twin and ban from 0.83 to -0.001. A worker restart briefly ran three labelling workers on the same rows; duplicates were compacted to the last row per sample, which every reader used. GPU time was about 1.8 GPU hours, judge spend USD 0.105.

## 3.7 Locus experiment: a shared prohibition direction, a locus at generated tokens 1 to 8, the ban-attending heads, and SAE transfer (Qwen3-8B)

**Why.** Four questions about where a prohibition lives inside the model were open after iteration 2. Is there a task-general direction that carries the instruction to abandon the default, and does writing it into a neutral prompt work like a named ban (the causal test of the read position correlation, moved to the positions where the route test located the effect)? Is the within-ban choice of algorithm decodable at generated tokens 1 to 8 beyond the written text? Do the three heads that attend to the banned name matter? Do the Qwen-Scope base model SAEs [50] transfer to the instruct model under a criterion that does not penalise its lower clean cross-entropy? This experiment [ARTIFACT:art_pVlCZ272hDV7] ran all four beside their controls under common random numbers, on the two path tasks and four bench tasks (kth smallest, substring search, find duplicate, two sum).

**Design.** The machine had a 16 GB RTX 2000 Ada, too small for bf16 weights, so every decoder linear layer was quantised at load time to 8-bit floating point with per-channel weight and per-token activation scales (embeddings, norms and the output head stayed bf16). A validation reproduced the iteration-2 shortest path arms (ban 2 of 20 Dijkstra, twin 20 of 20). The sampler coupled every arm exactly (identical uniforms in different rows give identical tokens at 20 rows per batch), and teacher forcing at batch 1 was bit exact. The shared prohibition direction v is the leave-one-task-out mean, over the 13 other tasks and all five templates, of the ban minus twin displacement at the task specification positions in blocks 12 to 23. The ADD arm wrote v into the neutral twin's prefill with the displacement targeted to alpha times the ban's own per-layer norm (alpha in {1, 2}, plus 0.5 on some tasks); the SUBTRACT arm projected v out of the ban prompt's prefill. Controls were three random directions with the same blocks, positions and norms, the twin, and the named ban (N = 100). In all, 5,500 samples followed the frozen design and 1,800 were exploratory. Decision rules were hash committed before sampling.

**The direction exists, but adding it is no better than a random push.** The leave-one-task-out v was reliable (split half cosine 0.95 to 0.99 across blocks 12 to 23). It was aligned with every held-out task's mean ban displacement (cosine 0.29 to 0.86 at block 18, against a 95th percentile of 0.03 for random directions), yet it carried only 2% to 6% of each position's own ban displacement. The preregistered test failed on every gated task (Table 110): ADD beat every random control on 0 of 5 gated tasks, and its avoidance was not above the maximum of the three random directions on 5 of 6 tasks. Where ADD moved behaviour it did not reproduce the ban. On kth smallest it landed on a size-k heap while the ban landed on quickselect (Jensen-Shannon divergence 0.52 against a permutation 95th percentile of 0.03; the committed forecast missed); on the shortest path task ADD and the ban both landed on Bellman-Ford/SPFA, but so did the random directions that moved it. The dose response was not monotone (shortest path avoidance 0.02, 0.35 and 0.12 at alpha 0.5, 1 and 2 over all slots), and the random edits grew more than v downstream (block 35: about 283 against 219 on the shortest path task), so a weak control does not explain the result. SUBTRACT never restored the default: pooled over the gated tasks the banned share changed by -0.026 [-0.07, 0.03] against a required +0.3, and on substring search, find duplicate and two sum removing v made the ban slightly stronger. On the path tasks neither plain nor affine subtraction exceeded a random edit of the same norm by the required 0.15, and that random edit was destructive (pass rate 0.00).

**Table 110.** The shared prohibition direction against matched random directions (avoidance; slots 0 to 9 for ADD and random arms). Source: locus experiment `results/c2d.json`.

| Task (default) | Named ban avoidance and landing | ADD, alpha 1 / 2 | Random directions, alpha 1 (three seeds) | SUBTRACT: change in banned share [95% CI] |
|-|-|-|-|-|
| Shortest path (Dijkstra) | 0.88, to Bellman-Ford/SPFA | 0.44 / 0.12 | 0.06, 0.50, 0.34 | +0.07 [-0.02, 0.17] |
| Grid (BFS) | 0.87, to DFS (all 13 BFS under the fourth template) | 0.06 / 0.04 | 0.04, 0.00, 0.02 | -0.05 [-0.11, 0.00] |
| kth smallest (full sort) | 1.00, to quickselect 79, size-k heap 21 | 0.80 / 0.70 | 0.24, 0.70, 0.36 | 0.00 (no default to restore) |
| substring search (naive) | 0.49, to KMP (fails the gate) | 0.00 / 0.00 | 0.00, 0.00, 0.00 | -0.12 [-0.22, -0.02] |
| find duplicate (hash set) | 0.74, to index marking | 0.00 / 0.00 | 0.00, 0.00, 0.00 | -0.06 [-0.11, -0.02] |
| two sum (hash map) | 0.80, to brute force | 0.00 / 0.00 | 0.00, 0.10, 0.00 | -0.09 [-0.15, -0.04] |

An exploratory run added 12 random directions (15 in all, alpha 1). On kth smallest ADD exceeded all 15 (0.80 against a maximum of 0.70 and a mean of 0.24) but landed on the wrong algorithm. On the shortest path task it sat at the 80th percentile (3 of 15 random directions moved it more; random mean 0.20), and on the grid task it was indistinguishable from random (0.06 against a mean of 0.07). Writing the shared component of the ban displacement into a neutral prompt is a direction-specific push on one task and a generic one elsewhere, and removing it is not necessary for the ban.

**No within-ban locus at generated tokens 1 to 16 (Table 111).** Decoders of default against other were fitted on batch-1 teacher forced states at blocks 8 to 28: the task specification mean, the read position, and generated tokens 1 to 8 and 16. Each was compared with 500 within-template permutations for the path tasks (200 for the bench tasks), taking the maximum over layers, and with three written text controls of matched or greater capacity (token one-hots, layer-0 embeddings reduced to 64 principal components, exact prefix match). No decoder passed the rule on any testable task. On the grid task and three bench tasks the class is set by the template: under the fourth template the model keeps the default in 20 of 20 bench samples and writes all 61 grid BFS programs, so every decoder (state, read position, text) reaches the template-only accuracy and none exceeds it. On the shortest path task the default is spread over templates (2, 0, 4, 3 and 3 of 20), and the choice is made inside the program. The first token at which the two classes diverge comes at a median of about 29 generated tokens, after the frozen window, and neither state nor text decodes the choice within tokens 1 to 16. The committed prediction of a fork at the import line (tokens 3 to 5) was wrong for this sample. At batch 1, identical prefixes gave bit-identical states (maximum difference 0 over 89 to 95 pairs per position), so a state at position k is a function of the written prefix.

**Table 111.** Within-ban decoders of the algorithm written (default against other) on batch-1 teacher forced states. BA is balanced accuracy. Source: locus experiment `results/c2e.json`.

| Task | Programs (default / other) | Largest state BA, tokens 1 to 8 | Best of read position and text controls at token 8 | Locus |
|-|-|-|-|-|
| Shortest path | 100 (12 / 88) | 0.53 rising to 0.63, never above the null 95th percentile (about 0.60 to 0.70) | 0.55 | none |
| Grid (with a fourth-template top-up) | 160 (61 / 99) | 0.904 at every k | 0.904 (template only) | none |
| substring search | 100 (51 / 49) | 0.832 at every k | 0.832 (template only) | none |
| find duplicate | 100 (26 / 74) | 0.88 at every k | 0.88 (template only) | none |
| two sum | 100 (20 / 80) | 1.00 at every k | 1.00 (template only) | none |
| kth smallest | 100 (0 / 100) | not testable (no default under the ban) | | |

A secondary test pooled the archived ban pools of the route and readout experiments (200 rows per path task): the shortest path state reached balanced accuracy 0.78 to 0.79 at tokens 4 to 8 against 0.75 for the template-only decoder, a margin of 0.03 to 0.05, below the 0.10 rule. The first run on states extracted in 20-row batches, where 8-bit matrix tiling made identical prefixes differ by 4% to 8%, gave the same verdict on every task. An exploratory extension to tokens 24 to 96 found text matching or beating the state on the grid and substring search tasks. On the shortest path task the state curve was noisy (0.57, 0.66, 0.45, 0.50 and 0.75 at tokens 24, 32, 48, 64 and 96). Only token 96 cleared both the null (0.66) and the text controls (at most 0.60), a single unreplicated point with 12 minority samples.

**The ban-attending heads are not special.** Mean ablation of layer 21 head 17 and layer 26 heads 21 and 25 at generated positions under the full ban raised the grid BFS share from 0.12 (the ban, same slots) to 0.24. Every set of three random heads in the same layers raised it to 0.18, so the difference is +0.06 (90% interval [0.02, 0.12]; exact paired p = 0.125 against each random set), short of the required 0.15. The shortest path task was unchanged (-0.03 [-0.07, 0.03]). Almost all the grid movement sat in the fourth template, which carries every BFS under the ban: BFS went from 6 of 10 to 10 of 10 under the target heads and 9 of 10 under each random set. The fourth-template ban is fragile to any small perturbation of layers 21 and 26.

**Under a fairer criterion the base SAEs pass, but they lose most of the ban displacement.** The iteration-2 transfer test compared increases in cross-entropy, which penalises the instruct model for its lower clean cross-entropy (0.030 against 0.260 nats). This experiment scored each model on its own text in a two by two design (model by text source, 100 sequences each) by the fraction of cross-entropy recovered relative to zero ablation, FR_zero (Table 112). The frozen rule, FR_zero of the instruct model on its own text at least 0.9 times the base model's, passed at layers 15, 20 and 27. As the plan had computed, the zero-ablation denominator of 12 to 15 nats makes this rule lenient. A placebo that swaps the SAE and zero-ablation cross-entropy per sequence drives FR_zero to about 0, yet still passes the 0.9 rule at layer 20; the values themselves (about 0.99, against about 0 on the placebo) carry the information. Stricter companions: the fraction recovered relative to mean ablation (FR_mean) passed the same rule at all three layers; the ratio of cross-entropy increases on own text (instruct over base) was 1.68, 1.30 and 0.76 at layers 15, 20 and 27 (iteration 2, one shared corpus in bf16: 3.29, 1.95, 1.59). The task-relevant test fails: the SAE reconstructions keep only about a third of the direction of the ban minus twin displacement at the task specification positions (cosine 0.27, 0.30 and 0.32 at layers 15, 20 and 27; norm ratio 0.65 to 0.79), so what the ban changes in the residual stream is largely lost in reconstruction error. The passing fraction recovered agrees with the finding of Kissane and colleagues that base model SAEs usually transfer to chat models; the displacement test, which measures what matters for a ban, is what fails, and latent-level claims about the ban should therefore not rest on these SAEs.

**Table 112.** Qwen-Scope SAEs spliced into each model (8-bit linears) on each text source: FR_zero / FR_mean / increase in cross-entropy (nats) / KL(clean, SAE) / fraction of variance unexplained. Source: locus experiment `results/sae_transfer.json`.

| Model / text | Clean cross-entropy | Layer 15 | Layer 20 | Layer 27 |
|-|-|-|-|-|
| instruct / own text | 0.032 | 0.9890 / 0.984 / 0.168 / 0.171 / 0.365 | 0.9903 / 0.985 / 0.169 / 0.175 / 0.096 | 0.9939 / 0.991 / 0.095 / 0.097 / 0.156 |
| base / own text | 0.926 | 0.9928 / 0.988 / 0.100 / 0.102 / 0.294 | 0.9906 / 0.986 / 0.130 / 0.134 / 0.113 | 0.9907 / 0.985 / 0.125 / 0.127 / 0.228 |
| instruct / base text | 1.861 | 1.0072 / 1.010 / -0.099 / 0.181 / 0.358 | 1.0066 / 1.010 / -0.104 / 0.220 / 0.098 | 1.0170 / 1.026 / -0.245 / 0.169 / 0.156 |
| base / instruct text | 0.251 | 0.9966 / 0.994 / 0.051 / 0.049 / 0.287 | 0.9949 / 0.992 / 0.075 / 0.075 / 0.281 | 0.9961 / 0.994 / 0.054 / 0.057 / 0.334 |

The instruct model on base text has a negative increase (the base SAE lowers its cross-entropy, most at layer 27, from 1.86 to 1.62 nats), consistent with the SAE pulling instruct activations toward base ones. Identity splices reproduced the clean cross-entropy, a zero splice at layer 15 gave 13.1 and 12.3 nats, and the instruct fraction of variance unexplained matched iteration 2 (0.365 against 0.366 at layer 15). As a readout, the latents never beat the difference-in-means direction: over 63 cells (6 tasks, 3 layers, a prohibition-present readout at the task specification mean and a default-plan readout at tokens 1 to 3), a top-1 or top-20 latent beat difference-in-means beyond its interval in 1 cell, a trivial one where every readout is at ceiling, as AxBench found [34].

**Geometry of early generated states (descriptive).** At the mean of generated tokens 1 to 3 and at token 16 (blocks 20 and 23), the k-nearest-neighbour graphs (k = 10) over all arms were fragmented (100 to 440 components for 800 to 1,100 points), because early states are fixed by shared boilerplate (the code fence and the `solve` signature) and many points coincide. No cloud had a persistent loop beyond its coordinate permutation null. These arms produced no bidirectional BFS, A* or greedy programs, so the BFS and bidirectional BFS neighbourhood of the ban list experiment could not be re-examined here.

**Table 113.** Committed predictions of the locus experiment and their outcomes. Source: locus experiment `predictions/commit1.json`, `README.md`.

| Prediction | Outcome |
|-|-|
| ADD (alpha 1 or 2) beats every random control on at least two thirds of gated tasks and lands on the ban's modal survivor | no: 0 of 5 gated tasks |
| SUBTRACT raises the banned share by at least 0.3 | no: pooled -0.026 [-0.07, 0.03] |
| No locus; state and text rise together at the first divergent token; the shortest path fork is at the import line (tokens 3 to 5) | no locus: yes; fork position: no (median about 29 tokens) |
| Head ablation raises the grid banned share by at least 0.15 over random heads; shortest path unchanged | grid no (+0.06); shortest path unchanged yes (-0.03) |
| The SAEs pass the frozen transfer rule, FR_zero about 0.98 to 0.995 for both models | pass; FR_zero instruct 0.989 to 0.994, base 0.991 to 0.993 |

**Checks.** An independent recomputation reproduced every arm share; shuffling arm labels within slots erased the ADD and head contrasts; the hash chain had no breaks and both commits preceded their first samples. A separate script with no shared code (exact McNemar by enumeration, an sklearn decoder) matched the pooled SUBTRACT change, the ADD pass count, the head deltas, FR_zero and the validation counts; its shortest path decoder at token 8 gave 0.638 against the frozen null of 0.695. Blind judge spend was USD 0.22.

## 3.8 Reach experiment: how far bans and token vetoes push, and what the long-form novelty instruction produces (Qwen3-8B)

**Why.** The update's third claim was that prompts move the model exactly one rung. This experiment [ARTIFACT:art_ccAbfJVcv0LO] asked three things. First, do cumulative token vetoes, an operation the model cannot ignore, reach algorithms that prompt bans cannot? We call this the *token walk*: veto the default's distinctive n-gram, then the next landing's, and so on, up to five algorithms. Second, does a ban that leaves exactly one survivor get that survivor written whenever the model can write it on request? We call the share of programs implementing the survivor *will*, and the share of forced programs labelled as the requested algorithm and correct *can*. Third, does the request's own long-form novelty instruction produce a correct novel algorithm? Rungs are numbered by the walk: rung 1 is the default, rung 2 is the walk's first landing (or, where the walk stalled, a flagged fallback committed in advance), and every other catalogue algorithm is at rung 3 or more. Six tasks ran: the two path tasks in bf16, and kth smallest, substring search, find duplicate and connected components on the official 8-bit checkpoint at which their iteration-2 references were made. Every mask, forecast and protocol was hash committed before the samples it governs.

**The token walk stalls at the default (Table 114).** The persistent veto, implemented as a vLLM logits processor, was exact: no banned token sequence occurred in any of 1,450 vetoed generations. The algorithm came back anyway. On the grid task `current_row` and `current_col` replaced `r, c` in 63% of re-emerged BFS programs (7% in references), and on the shortest path task `current_distinct` and `d` replaced `current_dist`. Vetoed strings also leaked through non-canonical spellings, in up to 0.86 of samples on connected components and 0.80 on find duplicate at step 2. The grid code degenerated into near-miss syntax (`queue popleft()`, 66% to 86% invalid). Imports and calls barely changed: the rerouting is lexical, not algorithmic. Only find duplicate moved one rung, to sort and adjacent check, the same single-rung move that prompt bans produce. A sham veto of an algorithm-generic n-gram of matched length and presence kept the default: grid 50 of 50 (`␣start␣==␣goal:\n`), shortest path 50 of 50 (`␣u,␣v,␣w`), substring search 49 of 50 (`␣len`) and connected components 44 of 44 valid (`␣range`). The distinctive veto cut correctness where the sham did not (shortest path pass rate 0.41 against 1.00, Newcombe difference 0.59 [0.43, 0.72]; grid 0.76 against 0.96). A fixed veto of the distinctive n-grams of BFS, DFS, IDDFS and A* at once, the request's top-five prohibition asked as an operation, left BFS 13, DFS 2 and 35 invalid programs on the grid task after two extra rounds; the prompt version gave avoidance 0.00 (Section 2.6). Neither knob reaches the rest of the catalogue.

**Table 114.** The token walk under the neutral twins (no ban text; N = 50 per round, 10 per template; ␣ marks a space in the n-grams). Source: reach experiment `results/walk.json`, `README.md`.

| Task | Step 0 (no veto) | Vetoed n-grams, by round | Final round of the last step | Status |
|-|-|-|-|-|
| Grid (bf16) | BFS 50 | `␣c,␣path␣=␣queue.p`, then `␣queue.append(start`, then `None␣for` | BFS 6, DFS 1, invalid 43 | stalled at step 1 |
| Shortest path (bf16) | Dijkstra 50 | `␣heap␣=␣[(0,␣s`, then `␣current_dist,`, then `␣dist[u]:\n` | Dijkstra 27, invalid 23 (pass 0.30) | stalled at step 1 |
| kth smallest (8-bit) | full sort 45, quickselect 5 | `␣nums.sort`, then `_sorted`, then `␣sorted(nums` | full sort 23, counting sort 10, quickselect 6, invalid 10 | stalled at step 1 |
| substring search (8-bit) | naive 50 | `+len`, then `[i:i␣+`, then a leak span | naive 50 | stalled at step 1 |
| find duplicate (8-bit) | hash set 50 | `␣set`, `␣seen` and leak spans; then, at rung 2 (sort and adjacent check, 37 of 50), `.sort` and 5 leak spans | sort and adjacent check 20, other 13, hash set 10 | stalled at step 2 |
| connected components (8-bit) | union find 47, DFS 3 | `␣parent` and 8 leak spans (`(parent`, `parents`, `.parent`, tab-indented `parent`, and others) | union find 44, DFS 6 | stalled at step 1 |

**Prompts reach further than one rung on two tasks (Tables 115 and 116).** The preregistered reach claim was that will is at most 0.10 at every rung of 3 or more where can is at least 0.7, and it is disconfirmed by a will of 0.30 or more. It was disconfirmed on connected components, where the list that leaves only BFS got BFS 50 of 50, and on kth smallest, where the list that leaves only quickselect got quickselect 50 of 50. Both cells were placed at rung 3 or more through the flagged fallback, because the walk stalled at step 1 and the fallback set the second rung (counting sort on kth smallest, DFS on connected components). A post hoc sensitivity that sets the second rung to the association answer keeps connected components disconfirming (association says DFS, so BFS stays at rung 3 or more) and moves quickselect to rung 2. On connected components the two traversals are interchangeable alternatives (BFS 50 of 50 when only BFS is allowed, DFS 49 of 50 when only DFS is), so a single chain of rungs does not describe the repertoire. The claim was confirmed on the shortest path task (Floyd-Warshall, from Section 2.6), on two kth smallest cells and on find duplicate's binary search on values; find duplicate's Floyd cycle detection reached 0.14; substring search had no rung of 3 or more with can of at least 0.7.

**Table 115.** Reach cells: rungs of 3 or more with can of at least 0.7. Source: reach experiment `results/c3.json`.

| Cell | Rung | Can | Will (N = 50) [95% CI] | Verdict |
|-|-|-|-|-|
| Shortest path, Floyd-Warshall (Section 2.6, not rerun) | 3 or more | 1.00 | 0.00 [0.00, 0.04] | confirm |
| kth smallest, quickselect | 3 or more (fallback) | 0.95 | 1.00 [0.93, 1.00] | disconfirm |
| kth smallest, size-k heap | 3 or more | 0.75 | 0.00 [0.00, 0.07] | confirm |
| kth smallest, heapify and pop | 3 or more | 0.70 | 0.00 [0.00, 0.07] | confirm |
| find duplicate, binary search on values | 3 or more | 0.78 | 0.00 [0.00, 0.07] | confirm |
| find duplicate, Floyd cycle detection | 3 or more | 0.70 | 0.14 [0.07, 0.26] | neither |
| connected components, BFS | 3 or more (fallback) | 1.00 | 1.00 [0.93, 1.00] | disconfirm |

**Table 116.** Every ban that leaves one survivor on the bench tasks (N = 50; disguise is the share of banned-mechanism programs that name none of the banned algorithms). Source: reach experiment `results/reach_events.jsonl`.

| Task | Only allowed algorithm | Labels of attempted programs | Will [95% CI] | Pass rate | Disguise rate |
|-|-|-|-|-|-|
| kth smallest | full sort | quickselect 50 | 0.00 [0.00, 0.07] | 0.94 | 0.04 |
| kth smallest | quickselect | quickselect 50 | 1.00 [0.93, 1.00] | 0.98 | n/a |
| kth smallest | size-k heap | quickselect 50 | 0.00 [0.00, 0.07] | 0.90 | 0.08 |
| kth smallest | counting sort | quickselect 44, other 6 | 0.00 [0.00, 0.07] | 1.00 | 0.09 |
| kth smallest | heapify and pop | quickselect 50 | 0.00 [0.00, 0.07] | 0.94 | 0.00 |
| substring search | naive | naive 50 | 1.00 [0.93, 1.00] | 1.00 | n/a |
| substring search | KMP | naive 37, KMP 13 | 0.26 [0.16, 0.40] | 0.98 | 1.00 |
| substring search | Rabin-Karp | naive 36, KMP 8, Rabin-Karp 5, Boyer-Moore-Horspool 1 | 0.10 [0.04, 0.21] | 0.92 | 0.76 |
| substring search | built-in find | naive 49, KMP 1 | 0.00 [0.00, 0.07] | 0.98 | 0.92 |
| substring search | Z algorithm | naive 46, KMP 3, Boyer-Moore-Horspool 1 | 0.00 [0.00, 0.07] | 0.96 | 0.92 |
| find duplicate | hash set | hash set 43, index marking 4, Floyd cycle detection 3 | 0.86 [0.74, 0.93] | 0.88 | 0.57 |
| find duplicate | binary search on values | index marking 40, hash set 10 | 0.00 [0.00, 0.07] | 0.40 | 1.00 |
| find duplicate | Floyd cycle detection | index marking 34, hash set 9, Floyd cycle detection 7 | 0.14 [0.07, 0.26] | 0.38 | 1.00 |
| find duplicate | sort and adjacent check | index marking 33, hash set 11, Floyd cycle detection 3, other 1, binary search on values 1, sort and adjacent check 1 | 0.02 [0.00, 0.10] | 0.36 | 0.96 |
| connected components | BFS | BFS 50 | 1.00 [0.93, 1.00] | 1.00 | n/a |
| connected components | DFS | DFS 49, union find 1 | 0.98 [0.90, 1.00] | 0.98 | 1.00 |
| connected components | union find | union find 47, DFS 3 | 0.94 [0.84, 0.98] | 1.00 | 0.67 |

Quickselect is kth smallest's universal answer to a ban list: every list that bans the full sort yields quickselect in 44 to 50 of 50 programs, including the lists that ban quickselect itself (only size-k heap allowed, only heapify and pop allowed: 50 of 50 quickselect, disguised in 0% to 8%). The sanity check of the list that leaves only the default gave will 1.00 on substring search, 0.86 on find duplicate and 0.94 on connected components, but 0.00 on kth smallest. There the prompt banned the size-k heap, heapify and pop, quickselect, median of medians and counting sort, and all 50 programs implemented quickselect, 48 of them in a function named `quickselect`, while full sort was 45 of 50 under the twin. This is the starkest priming by a negative constraint in the run [7, 53]. Forced can underestimates some algorithms: find duplicate's index marking has a forced adherence of 0.03, yet the model wrote it in 34 to 40 of 50 programs under lists that forbid it, always disguised. The preregistered list independence test asks whether the default's share among default and second-rung programs is the same across lists that ban both. It failed on substring search: 0.82 under the Rabin-Karp list against 0.98 under the built-in list (permutation chi-squared p = 0.033; largest difference 0.16 [0.04, 0.30]; placebos with shuffled membership gave p = 0.61, 0.56 and 0.06). It was descriptive on find duplicate and not testable on kth smallest and connected components.

**Two-step bans of the default and its second rung (N = 100) split the tasks (Table 117).** On the path tasks and substring search they failed (compliance 0.02, 0.01 and 0.14, with snap-back to the default on substring search), replicating iteration 1; on kth smallest, find duplicate and connected components they were obeyed (1.00, 0.96 and 1.00). The committed forecasts hit find duplicate (the second walk landing, index marking), kth smallest and connected components (association: quickselect and BFS) and substring search (snap-back).

**Table 117.** Two-step bans of the default and its second rung (N = 100; labels of attempted programs not banned). Source: reach experiment `results/reach_events.jsonl`, `README.md`.

| Task | Banned | Compliance | Attempted programs (banned mechanisms included) |
|-|-|-|-|
| Grid | BFS, DFS | 0.02 [0.01, 0.07] | DFS 82, BFS 16, unit weight Dijkstra 1, other 1 |
| Shortest path | Dijkstra, Bellman-Ford/SPFA | 0.01 | Bellman-Ford/SPFA 67, Dijkstra 32, other 1 |
| kth smallest | full sort, counting sort | 1.00 | quickselect 63, size-k heap 37 |
| substring search | naive, KMP | 0.14 | naive 74, Rabin-Karp 9, built-in find 2, Boyer-Moore-Horspool 2, other 1 (the rest KMP) |
| find duplicate | hash set, sort and adjacent check | 0.96 | index marking 52, Floyd cycle detection 42, other 2 (the rest banned) |
| connected components | union find, DFS | 1.00 | BFS 100 |

**The long-form novelty instruction produces claims of novelty, not new algorithms (Table 118).** The request contains two long-form novelty instructions, which we call the first long-form instruction (asking the model to make a new algorithm) and the second long-form instruction (asking for a fully novel algorithm never seen before); each asks for a design rationale of about 2,000 words before the code. They were run with thinking off (N = 25 to 50 per cell) and on (N = 10 per prompt and task, 16k thinking cap). All 100 thinking traces completed, at 4.1k to 12.4k thinking tokens. Of 574 outputs with a claim record, 484 (84%) claimed a new algorithm. Of those, 189 (39%) contained no code at all, only a rationale of 1,300 to 1,700 words, and 220 of the 295 with code (75%) were catalogue algorithms by the mechanism labeller, under names that modify a catalogue algorithm, such as a modified Bellman-Ford, a BFS with dynamic programming, or an optimised Dijkstra with early termination. The instructions do diversify the output (correct-only Hill numbers of 1.8 to 4.5 in the thinking-off cells, against a collapsed baseline), at a cost in correctness (pass rates of 0.33 to 0.44 on the grid task and 0.32 to 0.37 on find duplicate). With thinking on, the code stayed in the catalogue (grid mostly DFS, 13 of 20; shortest path Bellman-Ford/SPFA, Dijkstra and Floyd-Warshall only; kth smallest counting sort 13 of 20; substring search naive 14 of 20; find duplicate off-catalogue 11 of 20, all failing arithmetic tricks that assume one duplicate). A bf16 against 8-bit cross-check on the shortest path task under the first instruction gave a label composition Jensen-Shannon divergence of 0.033 bits against a null 95th percentile of 0.068 (p = 0.35).

**Table 118.** Long-form novelty instructions: composition of outputs per cell (first and second long-form instructions as defined above). Source: reach experiment `results/longform.json`, `README.md`.

| Cell | N | Default | Other catalogue | Off catalogue | Invalid or no code | Correct |
|-|-|-|-|-|-|-|
| kth smallest, first, thinking off (8-bit) | 50 | 3 | 17 | 12 | 18 | 25 |
| kth smallest, first, thinking on (8-bit) | 10 | 0 | 7 | 1 | 2 | 8 |
| kth smallest, second, thinking off (8-bit) | 50 | 0 | 12 | 8 | 30 | 15 |
| kth smallest, second, thinking on (8-bit) | 10 | 0 | 9 | 0 | 1 | 8 |
| substring search, first, thinking off (8-bit) | 50 | 27 | 7 | 1 | 15 | 32 |
| substring search, first, thinking on (8-bit) | 10 | 7 | 3 | 0 | 0 | 10 |
| substring search, second, thinking off (8-bit) | 50 | 10 | 8 | 4 | 28 | 13 |
| substring search, second, thinking on (8-bit) | 10 | 7 | 1 | 0 | 2 | 8 |
| find duplicate, first, thinking off (8-bit) | 50 | 5 | 13 | 17 | 15 | 13 |
| find duplicate, first, thinking on (8-bit) | 10 | 0 | 4 | 5 | 1 | 4 |
| find duplicate, second, thinking off (8-bit) | 50 | 4 | 14 | 7 | 25 | 8 |
| find duplicate, second, thinking on (8-bit) | 10 | 0 | 3 | 6 | 1 | 3 |
| Grid, first, thinking off (bf16) | 25 | 3 | 12 | 1 | 9 | 7 |
| Grid, first, thinking on (8-bit) | 10 | 0 | 8 | 0 | 2 | 3 |
| Grid, second, thinking off (bf16) | 25 | 3 | 3 | 2 | 17 | 3 |
| Grid, second, thinking on (8-bit) | 10 | 0 | 7 | 2 | 1 | 3 |
| Shortest path, first, thinking off (bf16) | 50 | 17 | 20 | 3 | 10 | 35 |
| Shortest path, first, thinking off (8-bit) | 50 | 18 | 12 | 4 | 16 | 29 |
| Shortest path, first, thinking on (8-bit) | 10 | 2 | 6 | 0 | 2 | 8 |
| Shortest path, second, thinking off (bf16) | 25 | 6 | 6 | 5 | 8 | 9 |
| Shortest path, second, thinking on (8-bit) | 10 | 6 | 4 | 0 | 0 | 9 |

**No novel algorithm in any cell.** Every correct program outside the catalogue from every arm of this experiment went through an audit: 38 correct programs (23 from the long-form cells, 10 from the walk, 5 from the lists) plus 15 seeded failing ones. Two blind judges (gemini-2.5-flash-lite and gpt-4.1-mini; each passed a 6-program control gate at 5 of 6 after a prompt fix) compared each program with its three nearest known solutions from the declared dataset's 472 human and textbook programs and its three nearest catalogue references, and the executor read each one and ran it on three extra random inputs. The 38 correct programs were 30 labeller misses (mostly counting sort on kth smallest written with a dictionary or Counter), 7 catalogue variants (counting plus binary search on cumulative counts; a last-in-first-out label correcting search on the shortest path task) and 1 degenerate quadratic brute force. Judge A called 10 programs novel and judge B none (kappa 0.27); the manual pass found 5 of those 10 degenerate (XOR or sum tricks, broken loops), 3 labeller misses and 2 catalogue variants. The exact one-sided 95% upper bound on the novel rate is 0.058 per cell of 50, 0.113 per cell of 25 and 0.26 per thinking-on cell of 10. Together with the record audit (0 of 78), the run's direct answer to the novelty question is that no instruction or knob produced a correct algorithm outside the catalogue and its known variants.

**Deviations and checks.** Distinctive n-grams had to be lexical (a veto of an indentation-tailed n-gram was bypassed by re-indenting in 20 of 20 unit tests), and shams could not be constructed for kth smallest and find duplicate. The analysis code was edited after its hash was committed (corrected compositions, a post hoc sensitivity, a claim mechanism check); an unchanged rederivation script reproduced every preregistered number from raw rows with no mismatch. Dropped: placement of the walk landings on the manifold, the thinking-on temperature sweep, and extending the path task thinking cells to N = 25. Judge spend was USD 0.49.

## 3.9 Comparisons across this iteration's experiments

**The same modal bench ban, drawn three times in Qwen3-8B and once in Llama.** Three Qwen3-8B artifacts sampled the modal bench bans with the five frozen templates and 20 samples each, on different engines: vLLM in bf16 (bench forecast experiment), HF in bf16 with common random numbers (bench route experiment, full ban arm) and HF with 8-bit linears (locus experiment, four bench tasks). Table 119 sets them side by side with Llama. With the wording fixed, avoidance replicates within a few points and the landing replicates in kind. The same five tasks pass the gate in both artifacts that ran all twelve. Every Qwen3-8B draw sends kth smallest to quickselect and size-k heap, two sum to brute force, find duplicate to index marking, connected components to BFS, and merge intervals to a failing merge without sorting. Llama lands elsewhere on two of the shared tasks (two sum to sort and two pointers, connected components to DFS), on both of which Llama's own association answer matches its landing.

**Table 119.** The modal bench bans across draws (avoidance; landing among attempts off the default). Sources: bench forecast experiment `results/c1_events.jsonl`; bench route experiment `results/shares.json`; locus experiment `README.md`; Llama bench experiment `README.md`.

| Task | Qwen3-8B, vLLM bf16 | Qwen3-8B, HF bf16 (full ban arm) | Qwen3-8B, HF 8-bit linears | Llama-3.1-8B-Instruct, vLLM bf16 |
|-|-|-|-|-|
| kth smallest | 0.97: quickselect 59, size-k heap 38 | 0.99: quickselect 70, size-k heap 28, heapify and pop 1 | 1.00: quickselect 79, size-k heap 21 | 0.95: quickselect (modal of 87) |
| two sum | 0.86: brute force 86 | 0.83: brute force 83 | 0.80: brute force | 0.91: sort and two pointers 42, brute force 32 |
| find duplicate | 0.79: index marking 73, Floyd 5, sort and adjacent check 1 | 0.79: index marking 77, Floyd 1, other 1 | 0.74: index marking | 0.76: other (0.53 of attempts) |
| connected components | 1.00: BFS 83, DFS 17 | 1.00: BFS 75, DFS 25 | not run | 0.82: DFS (modal of 78) |
| merge intervals | 0.58: other 44, union find 14 | 0.59: other 44, union find 15 | not run | 0.30 (fails the gate) |
| substring search | 0.40: KMP 21, built-in find 16, Rabin-Karp 2, Z algorithm 1 | 0.42: KMP 18, built-in find 17, Boyer-Moore-Horspool 5, Rabin-Karp 2 | 0.49: KMP | 0.79: KMP (modal of 64) |
| top-k frequent | 0.48 | 0.41 | not run | 0.89: sort by count |
| Fibonacci | 0.34 | 0.31 | not run | 0.79: iteration |
| topological order | 0.08 | 0.04 | not run | 0.18 |
| first and last position | 0.03 | 0.02 | not run | 0.04 |
| longest increasing subsequence | 0.02 | 0.02 | not run | 0.23 |
| nonoverlapping intervals | 0.00 | 0.00 | not run | 0.29 |

**One wording, everywhere.** The fourth template of Table 40, which states only that X is not allowed here, is the weakest wording in every artifact that measured it. In the bench forecast experiment it accounted for 197 of 240 banned programs, against 85 to 135 for the other templates. In the bench route experiment its pooled avoidance was 0.19, against 0.42 to 0.62, and it produced 29% of all ban failures. In the exposure template arm its mean avoidance was 0.81, against 0.93 to 0.96. In the locus experiment it kept the default in 20 of 20 bench samples and carried all 61 grid BFS programs under the ban, which is why every within-ban decoder there reduced to a template decoder. In Llama, dropping the fourth template alone flips the frozen branch from no family advancing to substitution. Wording is the largest measured source of variance in compliance, and any analysis that pools templates without modelling them pools different experiments.

**Signature vetoes, five times.** Every artifact that vetoed a default's distinctive n-gram found the default carried by more than its surface tokens. The default survived every round on 9 of 12 bench tasks in the bench forecast experiment, and Y re-emerged after three rounds for 25 of 33 shown algorithms in the exposure experiment. Only one Llama default (the heap of top-k frequent) was removed, the one-shot veto's avoidance was at most 0.41 in the bench route experiment, and the token walk stalled on all six tasks of the reach experiment although the veto was exact. On both path tasks no veto variant moved the default at all, in Qwen3-8B or in Llama, while a single prompt ban moves them by about 85 points. The subtraction forecast was therefore undefined on most events, and the test of whether a ban-free veto reproduces a ban's landing was undetermined everywhere it was planned.

**Three forecast contests.** Table 120 summarises the contests that decide the title claim, each under the same frozen rule. On the Qwen3-8B modal bans no family's forecast beats uniform by a decisive margin, and in neither model does a family advance once undefined forecasts are not counted as wins. On the exposure bans, where the default is still available, the ladder (that is, the default) wins: snap-back. Association is never better than the ban-free families in Qwen3-8B, and in Llama it ties them.

**Table 120.** The three forecast contests of iteration 3 (gated events; top-1 hit rates against the realised modal landing). Sources: bench forecast, exposure and Llama bench experiments.

| Contest | Gated events (disagreeing) | Frozen branch | Wins by 0.10 nats | Top-1 hit rates | Paired tests |
|-|-|-|-|-|-|
| Qwen3-8B modal bench bans | 5 (5) | SUBTRACTION/LADDER, ladder advancing; NO FAMILY ADVANCES if undefined forecasts do not count as wins | ladder 3 (2 as uniform), proximity 2 | ladder 1 of 5 and association 1 of 5 (both kth smallest), proximity 1 of 5 (two sum), subtraction 0 of 5 | not run (5 events); mean log score minus uniform: ladder +0.06, subtraction -0.69, proximity -1.53, association -1.78 |
| Qwen3-8B exposure bans, named | 31 (30) | SUBTRACTION/LADDER, ladder advancing | ladder 7, subtraction 2, association 2, proximity 0 | ladder 0.77, proximity 0.61, association 0.45, subtraction 0.36 | ladder minus association +1.29 nats [0.10, 2.38], Holm 0.081; subtraction minus association +1.02 [0.35, 1.56], Holm 0.081 |
| Llama modal and present minor bench bans | 13 (11) | NO FAMILY ADVANCES, aimed but unresolved | subtraction 1 (as uniform), association 1 | ladder 7 of 13, association 7 of 13 (binomial p 0.033 each), subtraction 4 of 12, proximity 3 of 13 | both ban-free families beat proximity (Holm 0.0088 and 0.0078); neither separates from association (p 0.52 and 0.77) |

[FIGURE:fig_forecast_hits]

## 3.10 What iteration 3 established, what it ruled out, and what it abandoned

Everything below is still one model per contest, at most 31 gated events per contest, and labels from labellers that passed their gates; the bench is memorised LeetCode material, and the path tasks are a screen that is never pooled.

**Established.**

1. *The likelihood substitution test of iteration 2 cannot decide the title claim.* Its gain and residual argmax hit the realised landing in 0 of 17 Qwen3-8B single bans, against 14 of 17 for the implied mass. No row keeps three estimable survivors, the bootstrap variance of the mean gain is 2.7 times the noise term it subtracted, and a decision on mass would need about 50 programs per algorithm at the lower bound and 129 Qwen3-8B or 43 Llama events. Whether the gains are pure subtraction, whether their specific part is aimed, and whether the generic profiles form a ladder are all undetectable with that instrument.
2. *Shown a correct program of a non-default algorithm and told not to use it, Qwen3-8B snaps back to its default.* The default's share of attempts rises from 0.05 under the copy twin to 0.72 under the named ban and 0.82 under the unnamed one. The modal replacement is the default in 24 of 31 gated events, and the ladder forecast wins the frozen contest (7 wins; top-1 0.77). Naming the banned algorithm adds little beyond asking for something else (same modal replacement for 0.88 of Y).
3. *Where the default is not available, the landing is specific to the task and mostly unforeseen.* On the five gated Qwen3-8B modal bench bans, no ban-free or association forecast beats uniform on average, and three of five landings (index marking, BFS, a failing merge without sorting) were named by no family. In Llama the landing is predictable above chance (ladder and association 7 of 13 each), but the families do not separate.
4. *A ban's route is task dependent.* On the bench, pooled over five gated tasks, generated tokens reading the ban carry 0.74 of the effect and the prompt states 0.61. The mechanism is redundant on kth smallest and connected components, direct on two sum and find duplicate, and superadditive on merge intervals, and a second draw reproduces every task. The prompt route story of the path tasks does not generalise.
5. *The ban is applied at the opening of the body and not re-read.* Forcing the default's first body token undoes the ban completely on every gated task, while forcing the `def` line undoes none of it.
6. *Wording dominates compliance.* The fourth template is the weakest in every artifact (template SD about 2.0 logits; likelihood ratio 374), and dropping it flips the Llama branch.
7. *The default is not carried by any small set of surface tokens.* Exact signature vetoes, one-shot, persistent, iterated or cumulative, almost never remove it; the model renames, respells or breaks the code. A single prompt ban moves the model further than any veto.
8. *Prompts reach past one rung where the alternatives are interchangeable.* Bans that leave one survivor got BFS 50 of 50 on connected components and quickselect 50 of 50 on kth smallest; on kth smallest quickselect is the answer to every ban list, including lists that ban it and the list that leaves only the default. Elsewhere (Floyd-Warshall, size-k heap, heapify and pop, binary search on values) the model will not write a survivor it can write on request.
9. *No instruction or knob produced a correct novel algorithm.* Zero of 78 correct out-of-catalogue programs in the iteration-1 and iteration-2 data and 0 of 38 in iteration 3 are novel; the request's long-form instruction makes 84% of outputs claim novelty, 39% of those contain no code, and 75% of the rest are catalogue algorithms.
10. *Llama's correct output is as collapsed as Qwen3-8B's on the grid task* (BFS 20 of 20 correct), and more diverse on 9 of 13 bench tasks counted over correct programs.

**Ruled out, or not supported.**

- *Substitution by association in Qwen3-8B.* In none of the three contests did association win; it was worse than uniform on all five gated modal bans and lost to the ladder by about 1.3 nats on exposure bans (Holm 0.081 named, 0.0056 unnamed).
- *A shared prohibition direction as the carrier of the ban.* Adding the leave-one-task-out ban displacement to a neutral prompt passed on 0 of 5 gated tasks against matched random directions, and removing it from a ban never restored the default (pooled -0.026 [-0.07, 0.03]).
- *A ban-free signature veto as the forecast of the next rung.* It was undefined on 10 of 12 Qwen3-8B modal events and 29 of 33 exposure events, and where defined on the path tasks or the bench it landed elsewhere than the ban.
- *The prompt route as the general mechanism of a ban.* Disconfirmed on the bench (pooled direct share 0.74, jackknife [0.38, 1.11]).
- *Prompts move the model exactly one rung.* Disconfirmed on connected components (BFS will 1.00 at can 1.00) and, through the fallback rung, on kth smallest.
- *The three ban-attending heads as a causal site.* Ablating them moved the grid ban by +0.06 over random heads in the same layers, inside the range of any perturbation of the fragile fourth-template ban.
- *A locus at generated tokens 1 to 16.* No decoder beat the template-only or written text controls on any testable task; on the shortest path task the choice diverges at a median of about 29 tokens.

**Dead ends, with the evidence that closed them.**

- *The forced ratio latent probability as the decision instrument for where a ban sends the mass.* Closed by Table 82 (argmax 0 of 17 against the realised landing) and Table 84 (programs and events needed far beyond the budget).
- *Signature vetoes and the token walk as a way past the default.* Closed by the bench forecast, exposure, Llama, route and reach experiments: the default survives exact vetoes by renaming and respelling, and the walk stalled at rung 1 or 2 on all six tasks.
- *The shared prohibition direction.* Closed by Table 110.
- *Head ablation as a test of the attention heads.* Closed by the random-head control.
- *Qwen-Scope base SAEs for readouts of the ban.* They now pass a fairer transfer criterion (fraction of cross-entropy recovered 0.989 to 0.994), but their reconstructions keep only a cosine of about 0.3 of the ban displacement, and their latents never beat difference-in-means.
- *Long-form novelty instructions as a source of novel algorithms.* Closed by Table 118 and the audit (0 novel of 38 correct programs outside the catalogue).

## 3.11 What the next iteration takes from this one

The title claim of the update, that a ban removes the default and the model falls to a next rung that ban-free counterfactuals can read in advance, did not survive in that form. The part that survived is snap-back: with the default available, a ban on a shown algorithm returns the model to its default, which is subtraction in its simplest form. Where the default itself is banned, the counterfactuals meant to expose the next rung either fail to move the model (signature vetoes) or move it somewhere else (random pushes, the shared prohibition direction), and the landing is specific to the task in a way no frozen family foresaw in Qwen3-8B. Substitution by association is not supported in Qwen3-8B and is tied with the ladder in Llama. What decides the replacement under a modal ban remains open, and the run now has two concrete leads for it: the opening of the body, where the prefill sweep localises the ban to the first body token, and the template, which carries more of the variance in compliance than anything else measured.

Three things follow for the next iteration. First, the contest needs events on which the default is unavailable and the families disagree, in numbers the paired tests can use: the modal bench bans give 5 gated events in Qwen3-8B, so pooling with Llama (11) and adding bench tasks where bans take is the arithmetic, with the template entered as a random effect rather than pooled over. Second, the first body token is now a measured locus in behaviour; a decoder or patch there, in states saved at that position for each task, would ask what is decided when the ban gives way. Third, the generic perturbation rival needs a behavioural test where its runner-up and the associate differ, which the Qwen3-8B bench rarely provides; Llama's present minor events are where the named ban gained the associate about 0.25 of attempts beyond the veto on two of six events, and that is the next place to look.

Request items still open: a same seed temperature arm with thinking on (dropped again), manifold placement of the walk landings (dropped; the walk stalled), and an SAE readout that keeps the ban displacement.

# What we have learned so far

After three iterations the run has a firm picture of the collapse, a measured picture of where and how a prohibition acts, and still no rule for what replaces the default when the default itself is banned. Qwen3-8B [5] writes BFS and Dijkstra almost without exception on the two path search tasks and one algorithm on each of 13 further coding tasks (modal share 1.00 on 12, 0.98 on one). Sampling temperature, top-k, top-p, thinking mode and random seeds change how the code is worded and not which algorithm it implements; with seeds coupled across temperatures the algorithm changed in at most 1 of 30 seeds per cell. Llama-3.1-8B-Instruct [22] attempts more algorithms, but its correct grid programs are BFS 20 of 20; counted over correct programs it is more diverse than Qwen3-8B on 9 of 13 bench tasks.

A single prompt ban, where the model obeys it, removes the default and the output collapses again on one replacement. On the path tasks the replacement is Bellman-Ford/SPFA (272 of 272 compliant iteration-1 programs, 255 of 260 iteration-2 attempts not banned) and DFS (116 of 128; 257 of 257). On the bench, Qwen3-8B obeys the modal ban on only 5 of 12 tasks, and where it does the landing replicates across three engines and is specific to the task: quickselect and size-k heap, brute force, index marking, BFS, and a failing merge without sorting. Shown a correct program of another algorithm and told not to use it, the model goes home: the default's share of attempts rises from 0.05 under the copy prompt to 0.72 under the ban. How often a ban is obeyed depends on its wording more than on anything else measured; the fourth template, which states only that X is not allowed here, is the weakest in every artifact, and dropping it alone changes the Llama verdict.

What decides the replacement under a modal ban is not settled, and the reasons are now specific. The likelihood instrument built in iteration 2 cannot decide it: its gains never point at the algorithm the model writes (0 of 17 events), and a decision on estimable mass would need about 50 programs per algorithm and 129 Qwen3-8B events. On sampled events, substitution by association is not supported in Qwen3-8B. Association was worse than uniform on all five gated modal bench bans and lost to the context-free default on exposure bans by about 1.3 nats per attempt; in Llama it ties the ban-free forecasts, and the landing is predictable above chance (7 of 13 hits for both). The ban-free forecasts fare no better on the modal bans: no family beats uniform on average, three of five landings were named by no family, and the signature vetoes meant to read the next rung in advance almost never remove the default, which comes back renamed or respelled. On the shortest path task every perturbation that moves the model off Dijkstra, random activation directions included, lands on the same second choice as the ban, so a shared top rung exists there; the order below it is unmeasured. The model's free-form answer predicts the path task substitutes, which may reflect simulation of its own behaviour [39]. Naming an algorithm inside a prohibition primes it, in both models, most starkly when a list that leaves only the default produced quickselect 50 of 50 times.

Where a ban acts depends on the task. On the path tasks it is carried mostly by the prompt states (likelihood readout 0.85; behaviour 0.98 on the shortest path task, mixed 0.50 and 0.35 on the grid task). On the bench, behaviourally, generated tokens reading the ban carry more of the pooled effect than the prompt states (0.74 against 0.61), with a redundant mechanism on two tasks, a direct one on two and a superadditive one on one, all reproduced by a second draw. What is common is the point of enforcement: forcing the default's first body token, the first content token after its `def` line, undoes the ban completely, while forcing the `def` line undoes none of it, much as safety refusals are enforced in the first tokens [63]. The read position predicts how strongly a wording will be obeyed (-0.41 across 110 wordings), but splicing it alone carries none of the effect. A shared prohibition direction written at the task specification positions is no better than a random push of the same norm. Ablating the three heads that attend to the banned name does no more than ablating random heads, and no within-ban locus exists at generated tokens 1 to 16, where the template sets the class. Every activation edit the run tried either did nothing, broke the model, or acted like a random direction; decodable is not the same as actionable here [55].

No knob opens the repertoire cheaply. No knob reaches an even two-algorithm split under 20 points of pass rate; the semantic seed (Bellman-Ford/SPFA 61, Dijkstra 30 at 7 points) and the A* mention are the two conditions that buy a second correct algorithm, and both name or describe it. Generate then select, which hands the choice to an external random draw [43], reaches three or four algorithms at 24 to 42 points. Ban lists fail by reimplementing the banned mechanisms, disguised in 41% to 92% of cases. Cumulative token vetoes are exact but stall at the first or second rung on all six tasks tried. Bans that leave one survivor reach interchangeable alternatives (BFS for connected components) but not algorithms the model can write on request, such as Floyd-Warshall. No instruction or knob produced a correct novel algorithm: 0 of 78 correct programs outside the catalogue in the first two iterations and 0 of 38 in the third are novel, and the request's long-form instruction makes 84% of outputs claim novelty while their code is catalogue algorithms or nothing.

Post training sharpened an ordering the base model shows under the chat template (preregistered verdicts: INSTALLED_BY_POST_TRAINING on the shortest path task, MIXED on the grid task, MIXED on both at the planned sample size), consistent with reports that post training narrows output diversity [57, 35]; in plain completion the base model's shortest path mode is Bellman-Ford/SPFA.

What remains open follows from this. The replacement rule under a modal ban needs more gated events where the families disagree than five per model, with the template modelled as a random effect; Llama's present minor events, where the named ban sometimes gained the associate, are the most informative place left. The first body token is a behavioural locus that no internal readout has yet examined. The request items not delivered are a same seed temperature arm with thinking on and an SAE readout that keeps the ban's displacement.

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
[39] Binder et al. Looking Inward: Language Models Can Learn About Themselves by Introspection. arXiv preprint arXiv:2410.13787. 2024.
[40] Goudarzi et al. Math Reasoning in LLMs is Organized by Approach, Not Topic. 2026.
[41] Veach et al. Optimally combining sampling techniques for Monte Carlo rendering. Proceedings of the 22nd annual conference on Computer graphics and interactive techniques - SIGGRAPH '95. 1995.
[42] Newcombe. Interval estimation for the difference between independent proportions: comparison of eleven methods. Statistics in Medicine. 1998.
[43] Wong et al. SimpleStrat: Diversifying Language Model Generation with Stratification. arXiv preprint arXiv:2410.09038. 2024.
[44] Zhang et al. NoveltyBench: Evaluating Language Models for Humanlike Diversity. arXiv preprint arXiv:2504.05228. 2025.
[45] Lee et al. Are We Measuring Strategy or Phrasing? The Gap Between Surface- and Approach-Level Diversity in LLM Math Reasoning. arXiv preprint arXiv:2606.29985. 2026.
[46] Zhang et al. Verbalized Sampling: How to Mitigate Mode Collapse and Unlock LLM Diversity. arXiv preprint arXiv:2510.01171. 2025.
[47] Zhang et al. Towards Best Practices of Activation Patching in Language Models: Metrics and Methods. International Conference on Learning Representations. 2023.
[48] Geva et al. Dissecting Recall of Factual Associations in Auto-Regressive Language Models. Conference on Empirical Methods in Natural Language Processing. 2023.
[49] Belrose et al. Eliciting Latent Predictions from Transformers with the Tuned Lens. arXiv preprint arXiv:2303.08112. 2023.
[50] Deng et al. Qwen-Scope: Turning Sparse Features into Development Tools for Large Language Models. arXiv preprint arXiv:2605.11887. 2026.
[51] Gao et al. Scaling and evaluating sparse autoencoders. International Conference on Learning Representations. 2024.
[52] Mueller et al. MIB: A Mechanistic Interpretability Benchmark. International Conference on Machine Learning. 2025.
[53] Mann et al. Don't Think of the White Bear: Ironic Negation in Transformer Models Under Cognitive Load. arXiv preprint arXiv:2511.12381. 2025.
[54] Bogdan et al. Thought Anchors: Which LLM Reasoning Steps Matter? arXiv preprint arXiv:2506.19143. 2025.
[55] Basu et al. Interpretability without actionability: mechanistic methods cannot correct language model errors despite near-perfect internal representations. arXiv preprint arXiv:2603.18353. 2026.
[56] Zhou et al. How Language Models Process Negation. arXiv preprint arXiv:2605.03052. 2026.
[57] Kirk et al. Understanding the Effects of RLHF on LLM Generalisation and Diversity. International Conference on Learning Representations. 2023.
[58] Heo et al. Do LLMs "know" internally when they follow instructions? International Conference on Learning Representations. 2024.
[59] Sia et al. Where does In-context Translation Happen in Large Language Models. arXiv preprint arXiv:2403.04510. 2024.
[60] Hendel et al. In-Context Learning Creates Task Vectors. Conference on Empirical Methods in Natural Language Processing. 2023.
[61] Todd et al. Function Vectors in Large Language Models. International Conference on Learning Representations. 2023.
[62] Biagiola et al. The Alignment Problem in Constrained Code Generation. arXiv preprint arXiv:2606.21619. 2026.
[63] Qi et al. Safety Alignment Should Be Made More Than Just a Few Tokens Deep. International Conference on Learning Representations. 2024.
[64] Zhang et al. Simple Fast Algorithms for the Editing Distance Between Trees and Related Problems. SIAM Journal on Computing. 1989.
[65] Wilcoxon. Individual Comparisons by Ranking Methods. Biometrics Bulletin. 1945.
[66] Vehtari et al. Pareto Smoothed Importance Sampling. Journal of Machine Learning Research. 2015.
[67] Hanley et al. If nothing goes wrong, is everything all right? Interpreting zero numerators. JAMA. 1983.
[68] Efron. Better Bootstrap Confidence Intervals. Journal of the American Statistical Association. 1987.
