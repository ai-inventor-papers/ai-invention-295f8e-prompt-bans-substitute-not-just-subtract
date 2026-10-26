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

**The positive target and the BUY rule.** The strategy's positive target was a knob that buys a second correct algorithm, a Hill number of at least 2 within its own compliant output, at a cost below 20 pass points. Under the single statistic no diversity knob and no ban meets it on either task. The closest is the semantic seed on the shortest path task (1.935 at 7 points). The mention of A* on the grid task reaches 2.69 at 11 points, but a mention recommends a named algorithm, so it meets only the literal reading of the target. The modal ban, the knob that iteration 1 ranked first on the shortest path task, scores exactly 1.0 there once banned programs no longer count: it replaces Dijkstra with one algorithm. The BUY rule names a best knob only when its 90% interval separates from the next; on the grid task the top rows (novelty instruction 1.227 [1.096, 1.346], sham ban of IDDFS 1.205 [1.0, 1.542]) do not separate, and on the shortest path task neither do the top five (Table 47). No knob advances.

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
| Shortest path | bidirectional Dijkstra | plain | 14 | 9 | Dijkstra 22, other 4 | always run |
| Shortest path | Floyd-Warshall | plain | 40 | 40 | none | always run |
| Shortest path | Dial | plain | 36 | 7 | other 4 | always run |

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

**Geometry and natural run internals.** In the teacher forced residual stream, centroid MDS stress-1 was 0.025 (grid) and 0.006 (shortest path). The nearest neighbours were BFS with bidirectional BFS, DFS with IDDFS, and A* with greedy best first; nearest neighbour stability was 0.70 across settings and 0.96 under a program bootstrap. Persistent homology, which tracks loops in a point cloud across distance scales, found no persistent loop on either task, which answers the request's question about a circle in the negative for these clouds. Probes within one ban prompt at generated token 16, a position that does not depend on the label, were near chance on every grid condition and reached balanced accuracy 0.69 (p = 0.03) on the shortest path ban that leaves only Bellman-Ford/SPFA. Probes at the token before the commit token were confounded, because that position depends on the label. The difference-in-means direction from forced programs aligned with the natural within one ban direction at that position (cosine 0.6 to 0.95) and on the shortest path task at token 16 (0.3 to 0.99), but not for the grid BFS ban at token 16 (-0.13 to -0.01).

**Deviations and cost.** The experiment ran on an RTX 4090 in eager vLLM mode (no C compiler), replaced one duplicated forced paraphrase, missed the gold gate after its revision, and recorded bf16 scoring path noise of about 1 nat per program; the shortest path likelihoods sum to 0.17, below the 0.3 calibration floor; the second noun placebo ran after the ban lists were sampled. It used about 1 GPU hour and USD 0.42 of judge calls (857 calls).

## 2.7 Llama replication: the same protocol in a second model family

**Why.** A claim about what a ban does inside one model needs a second family. This experiment [ARTIFACT:art_-QPYRaFERCBX] ran shared protocol v2 on Llama-3.1-8B-Instruct [22] in bf16 with its default chat template, on the canonical suite, retokenising the neutral noun bank under Llama. It drew 1,780 seeded vLLM generations: baselines, modal bans, mention twins, listing controls, two bans of algorithms other than the default and two double bans per task (14 events), 880 forced programs and 220 free-form answers. It scored 248 name scrubbed forced programs in 39,768 program scores (11.3 million tokens). Nothing was tuned to agree with Qwen3-8B.

**Llama's baseline is not collapsed on the grid task.** It writes BFS 77 times and DFS 20 times in 100, with a low pass rate (0.20). On the shortest path task it is collapsed (Dijkstra 92, pass rate 0.59). The BFS ban sends it to DFS 63 of 100; the Dijkstra ban sends it to Dijkstra 43, other labels 37 and Bellman-Ford/SPFA 18. Both double bans fail the gate (Table 70). Bidirectional Dijkstra and Dial could not be written (2 and 1 forced programs kept after up to 120 attempts), so the shortest path catalogue has three algorithms, no row there has three survivors, and the substitution test runs on the grid task only.

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

**Qwen3-8B is fully collapsed on all 13 tasks.** The modal share is 50 of 50 everywhere except first and last position (49 of 50), Wilson [0.929, 1.0], and the correctness conditioned Hill number is 1.0 on every task. No task has a minor algorithm at 10% or more, although the presence check is weak at N = 50 (a true share of 0.10 reaches 5 of 50 with probability about 0.57). The pilot pass rate is at least 0.92 on every task. The collapse is specific to the model: Llama-3.1-8B-Instruct, run with the same specifications and decoding, splits over several algorithms on kth smallest (heapify and pop 0.34, size k heap, full sort and quickselect), substring search (naive 0.53) and find duplicate (hash set 0.43), and passes far fewer tests. The presence pilot therefore removes the present minor stratum for Qwen3-8B on every candidate task: confirmation on this bench must rest on likelihood matrices and on modal bans for Qwen3-8B, and Llama is where sampled present minor bans exist.

**Labeller, likelihoods and nominations.** All 13 tasks passed the labeller gate, 11 at round 0 and two (kth smallest, merge intervals) after one revision round with a fresh holdout (5 of 6 and 6 of 6). Both labellers got all 54 references right; runtime and AST labels agreed on 0.91 of 3,230 Qwen attempts, and the judge was needed on 8.4%. The baseline likelihood's argmax equals the pilot mode on 13 of 13 tasks, its log score beats uniform on every task (for example -0.06 against -1.61 on two sum), and the sum of exp(likelihood) lies in [0.3, 3] on 11 of 13 (cycle detection and topological order overshoot, an importance sampling overestimate under low ESS). Of the 54 cells, 34 have Kish ESS below 5. One cell stands out: quickselect on kth smallest has likelihood -1.5 (about 0.21 latent mass) while the pilot drew it 0 of 50 times. The free-form association answers are close to deterministic (the alternative to a full sort is quickselect 20 of 20 times); proximity nominates a different algorithm from association on 10 of 13 modal events; and under total collapse the sampled ladder ties over all survivors. The order recomputed after the likelihoods (Stage B) agrees with Stage A at Kendall tau 0.54. Forced adherence limits the exotic algorithms: 45 of 54 have adherence of at least 0.5, and the lowest are topological layering (0.04) and source removal (0.10), the interval tree (0.24), the DP variants of nonoverlapping intervals (0.28), index marking (0.28) and label propagation (0.29).

**Deviations and what was not done.** Scoring used vLLM prompt log probabilities instead of HF; single request and batched scoring disagreed by 0.62 nats on 1 of 5 checked programs (the others within 0.015). The forced proposal used five paraphrases over eight rounds instead of ten over four. Not produced: the unscrubbed scoring sensitivity that the likelihood screen recommended, Llama forced programs and likelihoods, ban, mention and neutral likelihood matrices, and any sampled ban event. Cost: about 1.4 GPU hours on one RTX 2000 Ada and USD 0.14 of judge calls (1,124 calls).

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

**Priming and the route agree across models.** A ban of an algorithm the model does not write raises that algorithm's likelihood in 8 of 9 cases in Qwen3-8B (+2.5 to +26.9 nats) and 5 of 6 in Llama (+1.8 to +7.6), and in both models the bans that lower their own label are those of algorithms the model does write, plus A*. The likelihood drop of the banned default travels by the prompt route in both models: F_prompt 0.85 [0.61, 1.20] in Qwen3-8B and 0.84 [0.62, 1.46] in Llama, with the direct route near zero (0.00 and -0.21). Only the Qwen3-8B grid behaviour shows a second, direct component.

## 2.11 What iteration 2 established, what it ruled out, and what it abandoned

Everything below is still descriptive: two screen tasks, two models, one modal ban event per task and model for the route test, and a likelihood instrument whose validity gate failed in both models in its preregistered (name scrubbed) form.

**Established.**

1. *The iteration-1 record, corrected.* On the shortest path task the ban's substitute is Bellman-Ford/SPFA in five of five draws (272 of 272 compliant programs, Wilson [0.986, 1.000]); on the grid task DFS is the realised mode in four of five draws (116 of 128, [0.843, 0.946]), with no clear mode in the HF engine geometry draw. Under fixed wording three new Qwen3-8B draws landed on DFS (257 of 257 programs not banned) and Bellman-Ford/SPFA (255 of 260). The cumulative BFS and DFS ban does not replicate. Under one statistic, no ban and no diversity knob reaches a second correct algorithm (rarefied Hill-1 of at least 2) for less than 20 pass points on either task; the semantic seed on the shortest path task comes closest (1.935 at 7 points). On gated events, no forecasting family can advance (three informative events, largest margin 0.05 nats).
2. *The generic perturbation rival holds on the shortest path task and fails on the grid task.* Every nonsemantic perturbation that left Dijkstra (8 of 8 rows) landed mostly on Bellman-Ford/SPFA, random directions included; on the grid task no nonsemantic perturbation left BFS among correct programs, while every ban reached DFS. On the shortest path task a ban and an arbitrary push end in the same place.
3. *The ban acts through the prompt states, before the first generated token.* In cache patching the prompt route carried 0.85 [0.61, 1.20] of the banned algorithm's likelihood drop and the direct route 0.00 [-0.08, 0.12], with the task specification states, not the read position alone, carrying it. The mechanism is an opening line veto: under the grid ban 0 of 100 programs open with the default's import line against 99 of 100 under the neutral twin, and the prompt route arm reproduces this exactly. On the shortest path task behaviour follows the prompt route completely; on the grid task generated tokens also read the ban directly (hiding the ban from them restores BFS to 0.47). Llama's likelihood readout agrees (F_prompt 0.84).
4. *The read position knows, in part, how hard a wording will be obeyed, and not what replaces X.* Across 110 wordings the projection on a shared ban direction correlates with the banned share at -0.41 [-0.69, -0.17] (p = 0.0003), short of the -0.5 bar; the substitute is not decodable beyond that projection.
5. *Naming primes.* A ban of an absent algorithm raises that algorithm's likelihood in both models (8 of 9 and 5 of 6), and the mention twin raises it more. The iteration-1 sham promotions are reproduced by the shared (ladder) component of the gains and are not X specific.
6. *Ban lists fail by reimplementation.* Every four or five name grid ban failed (avoidance 0.00 to 0.37); the model wrote BFS and DFS in the same mix whatever the list contained (BFS share 0.63 to 0.72, chi squared p = 0.48), disguising 41% to 92% of the banned programs. On the shortest path task the model will not write bidirectional Dijkstra, Floyd-Warshall or Dial even when each is the only algorithm allowed, though it can write Floyd-Warshall and Dial when told to.
7. *No decision locus among the saved states.* On the grid task the within one ban signal is fixed per paraphrase; on the shortest path task the first state that beats the read position by 20 points is a readout of text already written (`import heapq` against `from collections import deque`, decided at generated token 3). The forking token, the opening line veto and the locus probe all point at the first three generated tokens, which no artifact has saved.
8. *Temperature does not change the algorithm even for a fixed seed.* With seeds coupled across temperatures, the algorithm changed in 0 of 30 seeds in 10 of 12 cells and 1 of 30 in the other two, while phrasing changed in 7% to 100% of seeds depending on task and temperature, and less within a seed than across seeds.
9. *Qwen3-8B is collapsed on 13 new tasks as well.* The pilot found a modal share of 1.00 on 12 tasks and 0.98 on one; Llama-3.1-8B-Instruct is more diverse on the same tasks. The confirmation bench is frozen (12 tasks, labellers gated) with no ban prompt run on it.

**Ruled out, or not supported.**

- *Geodesic proximity on the read position manifold as the predictor of the shortest path substitute.* Floyd-Warshall is the nearest survivor to Dijkstra in 100% of paraphrase subsamples at every layer and k tested, Bellman-Ford/SPFA is never nearest, and no ban landed on Floyd-Warshall. On the grid task proximity and typicality coincide and cannot be separated.
- *An aimed substitution.* In neither model is the X specific part of the ban gains aimed at the prime and veto profile (Qwen3-8B -0.10, p = 0.80; Llama 0.067, p = 0.35) or at the stated alternative.
- *A coherent latent ladder.* The generic perturbation profiles do not agree with each other in either model, so the rival in its preregistered form, a fixed ordering any perturbation reveals, was not found either.
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

The title claim is still open, and the reason has changed. Iteration 1 could not separate substitution from a latent ladder because its events were too few and its typicality forecast was degenerate. This iteration measured every single ban in two models with a likelihood instrument and found neither account clean: the gains are not pure subtraction, they are not a coherent ladder, and their X specific part is not aimed where association or prime and veto predict. The confirmation bench exists to settle the share with task level clusters. Its inputs are now fixed, and so are its limits. Qwen3-8B is collapsed on all 12 frozen tasks, so its confirmation must use likelihood matrices on unscrubbed programs, which the gate supports, plus modal bans; Llama supplies sampled present minor bans. The ban, mention, neutral and nonce matrices, the Llama forced programs and every sampled ban event on the bench remain to be run, with forecasts hash committed first.

The route result redirects the mechanistic work. A ban is applied by the prompt states as a veto on the default's first line, and on the grid task also by direct reads during generation. The next measurements are therefore at generated tokens 1 to 3, the states no artifact has saved: a decoder and an activation patch there would locate the decision the locus probe could not find, and would say whether the opening line veto is the whole of the algorithm choice on the shortest path task. On the grid task the direct component needs its own localisation (which layers and which tokens read the ban after `def solve`), since the three attention heads that attend to the banned name are a descriptive lead, not a causal one. The template effect must enter every analysis as a random effect; one wording, the fourth template (`X is not allowed here`), accounts for every grid failure in three draws.

Request items still open after this iteration: the activation space manifold plots with centroids coloured by implemented count at a validated locus (no locus validated yet), a working SAE readout (the transfer test failed; a short fine-tuning on instruct activations, or a dictionary trained on them, is the alternative), and a same seed arm with thinking on. The top five prohibition, natural BFS against DFS internals, thought anchors, the same seed test, the logit and tuned lens, and the mapping of NLA and the Jacobian lens were run here.

