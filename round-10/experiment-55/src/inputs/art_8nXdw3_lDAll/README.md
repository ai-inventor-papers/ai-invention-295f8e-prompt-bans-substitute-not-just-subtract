# Do banned AI coders just rename BFS?

TP-B, iteration 9 of the algorithm-choice study (`gen_plan_experiment_1_idx2`).

**Question.** A prompt bans a model's whole path-search repertoire by NAME ("Do not use BFS, DFS, IDDFS, A* or greedy best-first search"). Is the ban obeyed on names but not on mechanisms? We compare three readings of the same programs:

1. **lexical** compliance: no banned alias in the code (L1, the direction's definition; L2 = self-naming only);
2. **name-level** label: the iteration-8 labeller plus gated LLM judges (which algorithm the program *is called* or *judged* to be);
3. **mechanistic** compliance: the expansion-order class of the program measured at RUNTIME on 40 probe grids, without reading any name.

Task: T1 grid path (`solve(grid, start, goal)`, 4-neighbour moves, any valid path), the frozen 48-case hidden suite plus the 41-case ITER1 suite. Everything was hash-committed before the rows it governs (`commitments.log`: commit #1a, #1b, #2 and the amendments #3 to #9; the chain verifies). Step-by-step reproduction: `reproducibility.md`.

## Bottom line

- **Bans are obeyed on names far more than on mechanisms in the retraced iteration 1-8 rows (N1).** Lexical compliance minus mechanistic compliance, pooled over 10 configurations: 0.70 with the committed (fallback) runtime label and 0.61 with the tracer; between 0.58 and 0.80 whichever instrument is trusted (post-hoc bound). Most of these programs are BFS or DFS written without the banned words. In the three thinking configurations, the reasoning of nearly every such covert re-implementation mentions a banned name (C1 1.00, C4 0.91, C6 1.00): the model is aware of the ban while it writes the banned mechanism under another name.
- **Under cumulative bans (N3), lexical compliance stays high while mechanistic compliance falls with k**, for Qwen3-32B: k=1..5 mechanistic (runtime) = 1.00, 0.84, 0.84, 0.24, 0.22; tracer = 1.00, 0.86, 0.91, 0.47, 0.67; lexical = 1.00, 1.00, 1.00, 0.96, 0.89.
- **But the correct survivors of the full five-name ban (Qwen3-32B and Qwen3-14B) are mostly NOT renamed BFS.** By the executor's reads of all 76 k=5 survivors, 0.30 are in a banned expansion class, and all of those are unit-weight Dijkstra (BFS order by construction on a unit grid). The rest are grid Bellman-Ford rounds, coordinate-key heaps, random-priority or random-choice frontiers, set.pop() order and mixed deques: known but genuinely different expansion disciplines. The reads agree with the tracer on 0.88 of these programs and with the fallback runtime label on 0.64; the runtime label reads grid Bellman-Ford rounds as iterative deepening (planted control: 6/9 for the runtime label vs 9/9 for the tracer).
- **Name-level labels are unreliable for exactly these programs:** heaps keyed by coordinates (r + c, r*cols + c) were labelled 'unit Dijkstra' or 'greedy best-first' by the judges (see 'Name-level labels vs heap keys').
- Status: the tracer failed its gold gate, so every N1-N3 number is descriptive; the scale and N3-D results are exploratory and N5 secondary.

## Status first: the tracer gate FAILED, so N1-N3 are DESCRIPTIVE

- The new expansion-order tracer v9 passed its references (14/15; bidirectional A* is the one unverified class) and classified its 9 planted controls correctly (9/9). One control, the random walk with restarts, does not itself pass the 48-case suite, so the gate's control criterion (correct class AND a passing control) is formally 8/9 (`passed_controls` false in `results/tracer_gate_round2.json`); the gate failed on gold in any case.
- It **failed on gold programs** from non-ban conditions after the two allowed revision rounds: agreement 163/249 = 0.65 (round 0), 162/248 = 0.65 (round 1), 182/260 = 0.70 (round 2), against a bar of 0.90.
- Per label (round 2): astar 18/24, bfs 39/40, biastar 7/7, bibfs 19/20, dfs 34/39, dijkstra_unit 35/39, gbfs 35/35, idastar 1/22, iddfs 0/34, jps 1/7.
  The failure is concentrated in LLM-written iterative deepening (exponential path-enumerating IDDFS / IDA*), jump point search and part of A*; BFS, bidirectional BFS, greedy best-first, unit Dijkstra and DFS agree well.
- **Committed fallback (logged before commit #1b and before any ban row was traced):** the primary mechanism label is the iteration-8 name-free runtime label (heap priorities, FIFO/LIFO evidence, restarts) mapped through the committed coarse table (`runtime_class`). The tracer v9 class is reported beside it as a second column. **N1-N3 are DESCRIPTIVE**: the numbers are measured and reported, but no inferential verdict is claimed.
- Unit tests (testing plan 1): 19/21 mutation, renaming and sandbox programs pass. The two failures are informative: renaming identifiers breaks the round-1 rule that reads two consecutive int arguments as a cell only under coordinate-like parameter names (recursive DFS and IDA* references). The tracer's recursive-call detection is therefore NOT fully name-independent. This is one more reason it is the second column here.
- CLRS-30 canonical traces (dataset `clrs_text`): BFS p_mono = 1.00 on 39 traces, DFS stack adjacency = 1.00 on 40 traces (`audit/clrs_check.py`).
- Blind order-discipline judges on 100 stratified gold programs: gated ['deepseek/deepseek-chat-v3.1']. Tracer vs judge agreement 0.48; prior label vs judge 0.87 (`results/gold_order_judges.json`).

## N1 (primary, descriptive): lexical minus mechanistic compliance on ~580 retraced ban programs

Programs: the iteration-8 five-name-ban rows C1-C8 (C6 includes its held-out confirmation), C9 = iteration-2 Qwen3-8B TOP5 and C10 = gemma-3-4b-it TOP5. B = {BFS, DFS, IDDFS, A*, greedy} -> banned coarse classes {BFS, DFS, ID, HEUR}.

| Config | n | lexical L1 | mechanistic (runtime) | gap (Newcombe paired 95%) | McNemar p | covert share | tracer gap |
|---|---|---|---|---|---|---|---|
| C1 | 30 | 0.67 | 0.00 | 0.67 (0.45 to 0.81) | 0.0000 | 0.67 | 0.27 |
| C2 | 50 | 0.96 | 0.58 | 0.38 (0.21 to 0.53) | 0.0001 | 0.42 | 0.75 |
| C3 | 50 | 0.94 | 0.00 | 0.94 (0.82 to 0.98) | 0.0000 | 0.94 | 0.78 |
| C4 | 46 | 0.89 | 0.15 | 0.74 (0.56 to 0.84) | 0.0000 | 0.76 | 0.58 |
| C5 | 49 | 0.71 | 0.14 | 0.57 (0.40 to 0.69) | 0.0000 | 0.57 | 0.51 |
| C6 | 71 | 0.89 | 0.25 | 0.63 (0.49 to 0.74) | 0.0000 | 0.66 | 0.31 |
| C7 | 50 | 1.00 | 0.00 | 1.00 (0.90 to 1.00) | 0.0000 | 1.00 | 0.94 |
| C8 | 50 | 0.94 | 0.24 | 0.70 (0.53 to 0.80) | 0.0000 | 0.70 | 0.78 |
| C9 | 100 | 0.41 | 0.01 | 0.40 (0.30 to 0.50) | 0.0000 | 0.41 | 0.24 |
| C10 | 50 | 0.94 | 0.00 | 0.94 (0.82 to 0.98) | 0.0000 | 0.94 | 0.92 |

- **Pooled (equal weight):** 0.70 (configuration-cluster bootstrap 0.57 to 0.82); program-weighted 0.67. Positive in 10/10 configurations. The bars would read 'SUPPORTED', but N1 is descriptive (gate failed).
- Tracer column: pooled 0.61 (0.45 to 0.76), positive in 10/10.
- Sensitivities (runtime label): L2 pooled 0.73; untraceable-as-compliant 0.70; untraceable-as-non-compliant 0.70. Fine-class sensitivity (tracer only): 0.57.
- 'Knowing rename' (share of lexically compliant but mechanistically banned programs whose THINKING names a banned alias): C1 1.00, C4 0.91, C6 1.00.

## N2 (primary, descriptive): what Qwen3-32B-thinking's name-level survivors actually run

Pool: 91 name-level correct survivors (iteration-8 screen + held-out, new A k=5 + held-out).

| Reading | runtime label | tracer v9 |
|---|---|---|
| (a) all survivors in a banned coarse class | 72/91 = 0.79 (0.70 to 0.86) | 39/91 = 0.43 (0.33 to 0.53) |
| (b) excluding BFS-order-by-definition identities | 30/40 = 0.75 (0.60 to 0.86) | 4/40 = 0.10 (0.04 to 0.23) |
| N2-adj: share minus the uniform-catalogue null 0.6 | 0.19 (0.10 to 0.26) | -0.17 (-0.27 to -0.07) |

- By source: iter8:ban: 14/17; iter8:confirm: 19/21; new:A_k5: 20/27; new:A_k5_ho: 19/26 (runtime label).
- Exactly FIFO BFS order: 29/91 survivors (tracer).
- Trap 1, reported in the open: unit-weight Dijkstra and FIFO SPFA are BFS order on a unit grid BY CONSTRUCTION, which is why reading (b) exists. Trap 2: under the coarse classes 3 of the 5 non-banned catalogue algorithms already fall in banned classes, so the 0.6 bar equals the uniform null and only N2-adj separates renaming from a mechanism-blind choice.

## N3 (primary, descriptive): cumulative bans k = 1..5

B_k = the first k of [BFS, DFS, IDDFS, A*, greedy]; N = 50 per k on W1/W2/W3; held-out k = 5 on W4/W5/P6/P7.

**Qwen3-32B thinking**

| k | completed | lexical L1 | mechanistic (runtime) | gap (95%) | tracer mech | named survivors | pass | truncated |
|---|---|---|---|---|---|---|---|---|
| 1 | 49/50 | 1.00 | 1.00 | 0.00 (-0.07 to 0.07) | 1.00 | 0.18 | 0.18 | 0.02 |
| 2 | 43/50 | 1.00 | 0.84 | 0.16 (0.05 to 0.30) | 0.86 | 0.76 | 0.76 | 0.14 |
| 3 | 45/50 | 1.00 | 0.84 | 0.16 (0.04 to 0.29) | 0.91 | 0.80 | 0.80 | 0.10 |
| 4 | 46/50 | 0.96 | 0.24 | 0.72 (0.54 to 0.82) | 0.47 | 0.64 | 0.66 | 0.08 |
| 5 | 46/50 | 0.89 | 0.22 | 0.67 (0.50 to 0.78) | 0.67 | 0.54 | 0.66 | 0.08 |
| 5 held-out | 48/50 | 0.94 | 0.38 | 0.56 (0.40 to 0.69) | 0.52 | 0.52 | 0.68 | 0.04 |

- Jonckheere-Terpstra (decreasing mechanistic compliance in k): J = 5905.0, Monte-Carlo exact p = 0.00001 (100,000 permutations); Cochran-Armitage one-sided p = 0.00000.
- Criteria: k1_lex_ge_0.7 = True, k1_mech_ge_0.7 = True, jt_p_lt_0.05 = True, lex_ge_0.7_every_k = True, k5_gap_ge_0.4 = True, heldout_gap_ge_0.4_lb_gt_0 = True. The bars would read: SUPPORTED + CONFIRMED (descriptive).

**Qwen3-14B thinking (replication)**

| k | completed | lexical L1 | mechanistic (runtime) | gap (95%) | tracer mech | named survivors | pass | truncated |
|---|---|---|---|---|---|---|---|---|
| 1 | 49/50 | 1.00 | 1.00 | 0.00 (-0.07 to 0.07) | 1.00 | 0.28 | 0.28 | 0.02 |
| 2 | 50/50 | 0.96 | 0.30 | 0.66 (0.49 to 0.78) | 0.76 | 0.26 | 0.34 | 0.00 |
| 3 | 49/50 | 1.00 | 0.51 | 0.49 (0.34 to 0.63) | 0.76 | 0.52 | 0.54 | 0.02 |
| 4 | 50/50 | 0.90 | 0.20 | 0.70 (0.53 to 0.80) | 0.24 | 0.18 | 0.38 | 0.00 |
| 5 | 49/50 | 0.86 | 0.10 | 0.76 (0.59 to 0.85) | 0.24 | 0.10 | 0.44 | 0.02 |
| 5 held-out | 50/50 | 0.78 | 0.10 | 0.68 (0.51 to 0.78) | 0.30 | 0.16 | 0.36 | 0.00 |

- Jonckheere-Terpstra (decreasing mechanistic compliance in k): J = 7598.0, Monte-Carlo exact p = 0.00001 (100,000 permutations); Cochran-Armitage one-sided p = 0.00000.
- Criteria: k1_lex_ge_0.7 = True, k1_mech_ge_0.7 = True, jt_p_lt_0.05 = True, lex_ge_0.7_every_k = True, k5_gap_ge_0.4 = True, heldout_gap_ge_0.4_lb_gt_0 = True. The bars would read: SUPPORTED + CONFIRMED (descriptive).

## N3-D (exploratory): a name-free described five-mechanism ban

| | described (no names) | named k = 5 | difference (Newcombe 95%) |
|---|---|---|---|
| mech_compliance | 0.80 (39/49) | 0.22 (10/46) | 0.58 (0.39 to 0.71) |
| violation | 0.20 (10/49) | 0.78 (36/46) | -0.58 (-0.71 to -0.39) |
| lexical_any_banned_name | 0.02 (1/49) | 0.11 (5/46) | -0.09 (-0.21 to 0.02) |
| named_survivors | 0.18 (9/50) | 0.54 (27/50) | -0.36 (-0.51 to -0.17) |
| mech_survivors | 0.68 (34/50) | 0.16 (8/50) | 0.52 (0.33 to 0.66) |

- Committed direction: under R6, mechanistic compliance OR violation rises (described vs named k=5). Mechanistic compliance rises: True; violation rises: False (runtime label). Tracer column: False / False.
- The two instruments disagree here because of one program family. Under the described ban the model mostly writes heaps keyed by GOAL-INDEPENDENT coordinates (heap-key audit for this cell: astar | unknown 1, dfs | unknown 1, dijkstra_unit | coordinate (goal-independent) 8, gbfs | coordinate (goal-independent) 19, gbfs | path cost (distance) 1, gbfs | unknown 6, other | unknown 1). The judges call them 'greedy best-first' or 'unit Dijkstra', the runtime label calls them OTHER and the tracer calls them HEUR-weak. Their keys (r + c, r*cols + c, (r, c)) do not depend on the goal, so by mechanism they are neither banned heuristic nor BFS order: for this cell the runtime reading is the closer one. The 11 genuine FIFO BFS programs are the real violations.

## N5 (secondary): rotated five-name sets

Set rule: terciles (the committed name distance is degenerate: most alias pairs share no term, so D_name is 1 for 72 of 100 cells and no 'type L' set exists; R4-R5 come from the any-set fallback).

| Set | banned | survivors | Dm | Dn | exact p(Dm) | exact p(Dn) |
|---|---|---|---|---|---|---|
| literal | bfs, dfs, iddfs, astar, gbfs | 27 | -0.037 | 0.600 | 0.133 | 0.000 |
| R1 | bfs, dfs, bibfs, astar, idastar | 23 | 0.023 | 0.175 | 0.800 | 0.433 |
| R2 | bfs, gbfs, dijkstra_unit, jps, biastar | 25 | 0.024 | 0.480 | 0.600 | 0.400 |
| R3 | bfs, astar, dijkstra_unit, idastar, biastar | 23 | -0.070 | 0.480 | 0.400 | 0.400 |
| R4 | bfs, astar, gbfs, idastar, jps | 18 | -0.032 | 0.600 | 0.600 | 0.400 |
| R5 | bfs, bibfs, astar, dijkstra_unit, jps | 20 | 0.063 | 0.440 | 0.800 | 0.400 |
| R6 | bfs, bibfs, astar, gbfs, biastar | 24 | 0.031 | 0.200 | 0.600 | 0.800 |

- Joint sign count (Dm < 0 and Dn > 0): 3/7 defined sets (binomial p0 = 0.25: p = 0.2436); verdict: DISCONFIRMED. Distances use the tracer (flagged: the gate failed).

## Scale check (exploratory): gpt-oss-120b

- Baseline {'bfs': 45, 'dfs': 5} (pass 1.00); own top five ['bfs', 'dfs', 'gbfs', 'iddfs', 'astar'].
- Five-name ban: lexical 0.80, mechanistic (runtime) 0.22, named survivors 0.60, mechanism-level survivors 0.06, pass 0.68, labels {'other': 24, 'dfs': 4, 'dijkstra_unit': 21, 'bfs': 1}.
- Qwen3-235B-A22B-thinking was dropped before commit #1a (deviation D-scale: only Venice serves it, at about USD 0.03 per thinking row).

## Name-level labels vs heap keys (post-hoc audit)

Heap priority keys classified from the pushed expressions (`results/heap_key_audit.json`), by name-level label, over every new cell:

- **gbfs**: goal-distance (heuristic) 81, coordinate (goal-independent) 45, unknown 8, path cost (distance) 1
- **astar**: goal-distance (heuristic) 50, unknown 1
- **dijkstra_unit**: path cost (distance) 69, coordinate (goal-independent) 27, unknown 5, random 1

A goal-independent coordinate key (r + c, r*cols + c, (r, c), r^2 + c^2) expands cells in a fixed sweep order: it is neither greedy best-first nor Dijkstra, yet the judges give it those names.

## Descriptive k-curve, Qwen3-8B (iteration-2 rows, thinking off)

| condition | k | lexical L1 | mechanistic (runtime) | mechanistic (tracer) |
|---|---|---|---|---|
| EXP9:single:bfs | 1 | 1.00 | 0.86 | 0.89 |
| EXP9:multi:TOP | 4 | 0.47 | 0.38 | 0.33 |
| EXP9:multi:ARC | 4 | 0.95 | 0.38 | 0.44 |
| EXP9:multi:SCATTER | 4 | 0.49 | 0.00 | 0.09 |
| C9 | 5 | 0.41 | 0.01 | 0.17 |

- L2 validation: recall 0.88 on 60 hand-labelled self-naming lines; its misses are bare noun-phrase comments ("# BFS to find a path"); disavowal unit cases correct 11/11. L1 recall 1.00.

- Fallback-label validation (`results/fallback_label_validation.json`): runtime label references 15/15, planted controls 6/9 (wrong on the random walk, grid Bellman-Ford and wavefront-from-goal controls), gold 0.85 (partly circular); tracer references 14/15, controls 9/9.

## Positioning (dated 2026-10-23, `results/positioning.json`)

- **Benchmarking Language Model Creativity: A Case Study on Code Generation (NeoCoder; denial prompting; NAACL 2025)** (arXiv:2407.09007), adjacent: "We introduce DENIAL PROMPTING which pushes LLMs to develop more creative solutions to a given problem by incrementally imposing new constraints on the previous solution, compelling LLMs to adopt new strategies." Relation: technique-level bans to elicit new strategies, scored behaviourally; no execution-order check of whether a banned technique returns under a new name.
- **Compact Constraint Encoding for LLM Code Generation (Tang 2026)** (arXiv:2604.07192), adjacent: "counter-intuitive constraints opposing model defaults fail at 10--100%, while conventional constraints achieve 99%+ compliance regardless of encoding." Relation: rule-based constraint compliance by constraint type (implementation priors); not mechanism-level vs name-level compliance.
- **The Invisible Lottery: How Subtle Cues Steer Algorithm Choice in LLM Code Generation** (arXiv:2606.04057), adjacent: "Incidental prompt cues, meaning contextual words or metadata outside the task specification, can steer which algorithm the model selects, even when all outputs pass the same tests." Relation: algorithm-family shifts under incidental cues; no prohibitions, no runtime expansion-order audit.
- **Semantic Gravity Wells: Why Negative Constraints Backfire** (arXiv:2601.08070), adjacent: "Negative constraints (instructions of the form "do not use word X") represent a fundamental test of instruction-following capability in large language models. Despite their apparent simplicity, these constraints fail with striking regularity" Relation: word-level negative constraints and their internal suppression; ours are algorithm-level bans where the WORD can be avoided while the mechanism returns.
- **Don't Think of the White Bear: Ironic Negation in Transformer Models Under Cognitive Load** (arXiv:2511.12381), adjacent: "suppressing a concept requires internally activating it, which may prime rebound instead of avoidance." Relation: ironic rebound of a negated concept in text; ours measures rebound of a negated ALGORITHM in executed behaviour.
- **IFEvalCode: Controlled Code Generation** (arXiv:2507.22462), adjacent: "IFEvalCode decouples evaluation into two metrics: correctness (Corr.) and instruction-following (Instr.)" Relation: programmatic checkers for code constraints incl. naming; a name checker cannot see a renamed mechanism, which is what the tracer adds.
- Occupying work found: 0. the claim 'name-blind runtime audit shows bans are obeyed on names, not mechanisms' may be worded as new ONLY if N1-N3 hold (see results/headlines.json); otherwise only the descriptive measurement is reported.

## Novelty audit

- Candidates: 73 correct programs labelled 'other' or flagged; novel by both judges: 0. Claim: no correct novel algorithm (rule-of-three 95% upper bound 0.0053 over 568 correct rows).

## Manual reads

- 76 programs read by the executor (every Qwen3-32B and Qwen3-14B k=5 and held-out survivor (name- or mechanism-level)); summary in `results/manual_reads_summary.json`, records in `data/manual_reads_v9.jsonl`.

## Re-derivation and placebos

- `audit/rederive.py` (stdlib only, separate code) recomputes the N1 2x2 tables, gaps, paired-Newcombe intervals, the pooled gap and verdict, the N3 rates and JT statistics (own permutation test), the N2 counts and the N5 sign count: **0 mismatches**.
- Placebo 1 (swap lexical and mechanistic flags at random): mean pooled gap -0.002 (observed 0.70); fails as required: True.
- Placebo 2 (q32, k labels permuted): share of JT p < 0.05 = 0.07; fails as required: True.
- Placebo 2 (q14, k labels permuted): share of JT p < 0.05 = 0.06; fails as required: True.
- Placebo 3 (random N5 survivors): mean joint count 1.80 vs chance 1.75.
- Placebo 4 (tracer on order-shuffled events): BFS-order programs 7 -> 0 after shuffling; fails as required: True.
- `audit/rederive_headlines.py` (short, stdlib only, own code; raw rows only) re-derives the headline numbers: gate gold 182/260 = 0.70, references 14/15, controls 9/9 by class (8 also passing the suite); N1 pooled gap 0.697 (runtime label) and 0.608 (tracer), positive in 10/10 and 10/10 configurations, exact McNemar p < 0.05 in 10 and 9; N2 72/91 (runtime) and 39/91 (tracer); sampling spend USD 2.096 from the per-row costs. Placebo (flags swapped at random within each program, 200 draws): pooled gap -0.003 and 0.003, McNemar-significant configurations 0.34 and 0.31 of 10 on average: the effect disappears, as required.

## Cost

- OpenRouter: USD 3.889 in total. The committed cap was 3.5; it was raised to 4.0 before the last six cells were labelled (deviation D-cap-labelling). By purpose: sampling 2.096, adjudication judges 1.439, novelty judges 0.189, gates, smoke, naming checks 0.085, labeller judge 0.080 (`results/costs.json`).
- CPU only (6 cgroup CPUs); the GPU was unused.

## Deviations

- **N-key-ua.** Implementation note, not a protocol deviation: the first Stage-0 /key call used urllib's default User-Agent, which the run's proxy refuses (HTTP 403); it was read as 'remaining 0' and logged D-budget by mistake. Fixed (explicit User-Agent) and Stage 0 re-run; D-budget does not apply (remaining 13.71).
- **D-scale.** qwen/qwen3-235b-a22b-thinking-2507 is served only by Venice at USD 3.5 per million output tokens (smoke: USD 0.0023 for 614 tokens; about USD 0.03 per thinking row, 5x the planned 0.006). Its scale cells are dropped before commit #1a; the scale check runs on gpt-oss-120b (reasoning effort medium) only, if the budget allows after E.
- **D-commit-split.** Plan COMMIT #1 is made as two hash-chained commits, each before the rows it governs: #1a (prompts, cells, seeds, N, decoding, budget, lexical rules, mappings, decision-list semantics/thresholds, predictions) before any new sample; #1b (tracer code, probes, planted controls, gate result, rotated sets, N3-D descriptions, analysis code) before the first traced ban row and before the B/C/D/F-ban samples. Reason: thinking rows take 5-7 min each at ~29 tok/s, so A/E sampling must start while the tracer is gated. New rows are not opened, labelled or traced before #1b.
- **D-gate-r1.** Tracer gate round 0 (references 14/15 with BIDIR-heuristic the one unverified class, planted controls 9/9) failed on gold (163/249 = 0.65). Diagnosis on the gold programs: implementation defects relative to the committed definitions, not class semantics. (i) Recursive searches that carry the path as an argument (dfs(depth, path, visited)) never surfaced the root, and backtracking removals (visited.remove, path.pop) were confirmed as frontier pops. (ii) p_lifo counted every re-expansion as non-LIFO, so the plan's own DFS-revisit class (exhaustive backtracking) was unreachable. Round-1 fixes: a CALL cell can come from a path argument (its last cell); int pairs count as cells only under coordinate-like parameter names; a probe with >= 3 self-recursive cell calls uses the call stream; p_lifo uses a simulated path stack (descend or backtrack-then-descend), excluding immediate reversals. References and planted controls are unchanged by the fixes (14/15, 9/9). Round 0 is kept in results/tracer_gate_round0_final.json.
- **D-gate-r2.** Tracer gate round 1 (refs 14/15, controls 9/9) left gold at 162/248 = 0.65. Round-2 (the last allowed) diagnosis on gold: (i) queue/stack items of the form (r, c, path) or (r, c, prev_dir, path) lost their cell because only trailing int pairs were read -> leading int pairs are read for non-heap items; (ii) c_f/c_h were trivially 1 whenever the open list held one cell (recursive DFS with goal-sorted neighbours read as HEUR) -> a step counts only when the open list offers >= 2 cells; (iii) exponential IDDFS/IDA* programs hitting the 2 s probe timeout were counted as crashes although their partial traces show the pass structure -> only exceptions count toward the > 20-crash rule, timed-out probes keep their flagged partial record and drop their incomplete last pass from the bound test. References and controls unchanged (14/15, 9/9).
- **D-gate-fallback.** The tracer gate FAILED after the 2 allowed revision rounds: references 14/15 (BIDIR-heuristic unverified), planted controls 9/9, gold 182/260 = 0.70 < 0.90 (per label: bfs 39/40, bibfs 19/20, gbfs 35/35, dijkstra_unit 35/39, dfs 34/39, astar 18/24, jps 1/7, iddfs 0/34, idastar 1/22). Committed fallback (plan): N1-N3 are DESCRIPTIVE; the mechanism label is the iteration-8 10-class name-free runtime label mapped through the 1.11 coarse table (runtime_class); the tracer v9 order class is reported as a second column (sensitivity) with its per-class gate rates. N5 keeps its tracer-based distances and is flagged. Decided before commit #1b and before any ban row was traced.
- **D-cap-labelling.** The committed USD 3.5 cap was budgeted as sampling plus about 0.4 of judges. The iteration-8 adjudication protocol (deepseek-chat-v3.1 + kimi-k2, mistral-medium-3.1 third) cost about USD 0.08 per labelled cell (kimi-k2 rationales), USD 1.02 for the first 13 cells, i.e. 2.5x the plan. To label ALL cells with one consistent protocol (a cheaper judge pair for the last 6 cells would confound N5 and N3-D), the artifact cap is raised from 3.5 to 4.0 at USD 3.21 spent, before labelling B_R1-R3, C_desc, D_R5, D_R6. Sampling had already finished inside 3.5; the phase pot had USD 11.9 left and the system's per-artifact ceiling is USD 10.
- **D-n-short.** 7 of 280 B/C/D rows were lost to upstream HTTP 429 rate limits after 4 retries each and were not resampled (time and cap): B_R1 49, B_R2 46, B_R3 48 rows instead of 50; every other cell has 50.
- **D-reads.** Manual reads cover every Qwen3-32B and Qwen3-14B k=5 and held-out survivor (76 programs; plan TIME-BINDS branch: 'Lower manual reads to k = 5 survivors only'); the survivors whose name-level label and order class disagree at k=1..4 and the 10% sample of other survivors were not read.
- **D-L2-validation.** L2 was validated on 60 alias-bearing code lines (comments, docstrings, identifiers) from non-ban rows instead of 60 baseline comment lines: baseline programs carry almost no comments (63/729 contain any alias). All 60 are self-naming, so only recall is estimable (0.88); L2's handling of disavowals is checked on the 11 constructed disavowal unit tests (11/11).

## Layout

| Path | What it is |
|---|---|
| `method.py` | Orchestrator; one sub-command per stage (`uv run method.py --help`) |
| `src/common.py` | Protocol copied from iteration 8 (`art_R-HSmXq2t97f`) + the v9 block (k order, models, cap, genesis hash) |
| `src/prompts_tp.py`, `src/cells_v9.py` | Iteration-8 renderer (byte-identical k = 5 prompt) and the iteration-9 cell plan / seeds |
| `src/sample_v9.py` | OpenRouter sampler (provider pins, per-row cost, budget-403 stop with in-flight cancellation) |
| `src/label_tp.py`, `src/judge_tp.py`, `src/adjudicate.py` | Iteration-8 name-level labeller, gated judges, adjudication (unchanged) |
| `src/tracer_v9.py` | Expansion-order tracer, CHILD process (stdlib only): AST-rewritten container calls, heap/queue/deque proxies, str-subclass grid rows, call events |
| `src/orderclass.py` | Tracer PARENT side: expansion record, per-probe statistics, committed decision list, DS signature |
| `src/probes_v9.py`, `probes/probes_v9.json` | The 40 committed probe grids (seed 9009) + sha256 |
| `controls/` | 9 planted controls (renamed BFS/DFS, unnamed A*, goal-sorted DFS, random priority, random walk, FIFO SPFA, grid Bellman-Ford, wavefront from goal) |
| `src/gate_v9.py` | Gate sets (references, controls, non-ban gold), blind order judges, unit tests, trace cache |
| `src/lexical.py` | L1 / L2 lexical flags and trace-name counts (30 unit tests) |
| `src/mechdist.py` | N5 D_mech / D_name and the committed rotated-set rule |
| `src/stats_v9.py` | Wilson, Newcombe unpaired and paired (method 10; checked against Newcombe 1998 Table III), McNemar, JT, Cochran-Armitage, bootstrap |
| `src/analysis_v9.py` | N1, N2, N3, N3-D, N5 analyses (mechanism field switch: runtime label vs tracer) |
| `src/figures_v9.py`, `figures/` | F1 N1 forest, F2 2x2 shares, F3 k-curves (both instruments), F4 N2 survivor classes, F5 N5 Dm vs Dn, F6 actual traced expansion orders on 3 probes, F7 gate confusion (rounds 0 and 2), F8 survivor families vs three readings (PDF + PNG) |
| `data/samples_v9.jsonl`, `data/survivors_for_tpg.jsonl` | One row per new sample (plan 4.6 fields) and every new name- or mechanism-level survivor program (for TP-G next round) |
| `results/instrument_bounds.json`, `results/heap_key_audit.json`, `results/manual_reads_summary.json`, `results/fallback_label_validation.json` | Post-hoc (not pre-registered) readings: compliance under both / either instrument, heap-key audit, executor reads vs both instruments, fallback-label validation |
| `run_final.sh`, `build_readme.py` | The final stage chain and the README renderer (every README number is read from `results/`) |
| `src/manual_reads.py`, `data/manual_reads_v9.jsonl` | Manual-read selection and the executor's reads |
| `src/novelty.py` | Iteration-8 novelty audit, reused |
| `src/outputs_v9.py`, `method_out.json` | exp_gen_sol_out output (+ full/mini/preview) |
| `audit/rederive.py`, `audit/rederive_headlines.py`, `audit/placebo_shuffled_events.py`, `audit/clrs_check.py` | Independent re-derivation and placebos |
| `predictions/commit1a.json`, `commit1b.json`, `commit2.json`, `commit3.json`, `commit4.json`, `commit5.json`, `commit6.json`, `commit7.json`, `commit8.json`, `commit9.json`, `commitments.log` | Pre-registrations and their sha256 hash chain (genesis = sha256('iter9_TP-B')) |
| `reproducibility.md`, `pyproject.toml` | Step-by-step reproduction (what was actually run) and every installed package, pinned |
| `predictions/prompts_v9_*.jsonl`, `n5_sets.json`, `n3d_descriptions.json` | Every rendered prompt (sha256), the rotated sets, the N3-D descriptions with naming rates |
| `data/raw_<cell>.jsonl`, `data/labelled_v9_<cell>.jsonl` | Raw generations (reasoning text kept) and labelled + traced rows of every new cell |
| `data/trace_cache/` | Per-probe tracer statistics of every traced program, keyed by tracer version and code sha256, stored as `<version>_part_NNN.jsonl` parts of at most about 45 MB each (read in order by `gate_v9.trace_many`) |
| `results/` | Every analysis JSON (gate rounds, unit tests, N1-N5, scale, novelty, positioning, costs, deviations, timing) |
| `inputs/` | Read-only copies of the prior-iteration inputs with `inputs/SHA256SUMS` |
| `vendor/exp9`, `vendor/exp2` | Executable copies of the iteration-2 harness + labeller and the ITER1 suite |

## How to run

```bash
uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml
export OPENROUTER_BASE_URL=... OPENROUTER_API_KEY=...
.venv/bin/python method.py stage0 && .venv/bin/python method.py smoke && .venv/bin/python method.py datasets
.venv/bin/python method.py commit1a && .venv/bin/python method.py sample A E          # background in practice
.venv/bin/python method.py tracer_gate round0   # (+ round1, round2 after the logged fixes)
.venv/bin/python method.py n5sets && .venv/bin/python method.py describe && .venv/bin/python method.py tracer_tests
.venv/bin/python method.py commit1b round2 && .venv/bin/python method.py sample B C D
.venv/bin/python method.py retrace && .venv/bin/python method.py judge_gate
.venv/bin/python method.py label A E B C D && .venv/bin/python method.py sample F_gptoss_base
.venv/bin/python method.py label F_gptoss_base && .venv/bin/python method.py commit2
.venv/bin/python method.py sample F_gptoss_ban && .venv/bin/python method.py label F_gptoss_ban
.venv/bin/python audit/placebo_shuffled_events.py
AII_JSON_SKILL=<path to the aii-json skill> ./run_final.sh   # commit3, analyses, audits, novelty, figures, outputs, README
```

Sampling is nondeterministic (quantised providers); seeds and providers are recorded per row. Every cached stage
(trace cache, judge cache, program-evaluation cache) makes a rerun cheap. Only `stage0` and `datasets` read the prior
artifacts (each from `$TP_DEP_<KEY>`, else a sibling folder named by its artifact id); every later stage reads the
sha256-verified copies in `inputs/`. Full instructions, runtimes and expected numbers: `reproducibility.md`.

## Restoring removed files

| Removed path | Restore with |
|---|---|
| `.venv/` | `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml` |
| `src/__pycache__/` | `.venv/bin/python -m compileall src` (also regenerated automatically on import) |
| `vendor/exp9/tasks/__pycache__/` | `.venv/bin/python -m compileall vendor` (also regenerated automatically on import) |
| `vendor/exp9/labeller_ext/__pycache__/` | `.venv/bin/python -m compileall vendor` (also regenerated automatically on import) |
| `data/trace_cache/` caches of the round-0 and round-1 tracer versions (deleted) | not restorable by a stage: `tracer_gate` refuses to run after commit #1b by design; the gate results themselves are kept in `results/tracer_gate_round*.json` |
| `data/trace_cache/` (current version: 179 MB in 5 parts; a cache, excluded from publication by the upload-ignore list) | refilled automatically by any stage that traces: `.venv/bin/python method.py retrace` (580 programs, 13 min on 6 CPUs), `analyse` (N5 survivors), `figures` (F6); every class it holds is also stored per row in `results/retrace.jsonl` and `data/labelled_v9_*.jsonl` |

