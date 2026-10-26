## 5.10 Comparisons across this iteration's experiments

**The base repertoire against movability: screen, confirmation and second family.** The same quantity, beta against the escape fraction, was measured five ways in this iteration, and the answer depends on which tasks enter. On the 15 existing tasks, with Step 1's beta and iteration 4's escape fractions, Spearman is 0.78 to 0.79; with this iteration's own bf16 escape fractions it is 0.59; on the new tasks it is -0.03 in panel A, 0.21 in panel B and 0.15 pooled; in Gemma it is 0.42. The screen correlation is carried by many tasks with low beta that never move, while on new tasks base-diverse tasks that never move are common: count primes and valid anagram (beta 0.81 each), median of two sorted lists (0.71), jump game (0.47), all subsets (0.37) and longest common prefix (0.30). The figure plots both sets. The landing half replicates everywhere it could be measured: the base runner-up named the push landing on 5 of 5 movable existing tasks (screen), 3 of 3 in panel A, 3 of 4 in panel B and 5 of 7 in Gemma, 16 of 19 events in all.

**Movability depends on the engine and the unit.** Table 222 sets the existing tasks' movability side by side across the measurements of iterations 4 and 5. Under iteration 4's 8-bit engine and the ban unit, six tasks were movable; under this iteration's bf16 engine and the ban-free unit, only kth smallest and connected components escape with 8 fixed directions, and per-sample plan noise moves more than 10% of programs off the default only on kth smallest (0.28 at alpha 2). On the shortest path task, per-sample plan noise moved 26% of programs at alpha 1 in iteration 4 and 0% at alpha 1 here (4% at alpha 2, about 1.7 ban units). The engine checks pushed two fixed escaping directions at the ban unit in both engines and agreed within or near the resampling null (shortest path: Dijkstra 31 and Bellman-Ford/SPFA 19 in bf16 against 26 and 24 in the 8-bit engine). Those two directions therefore do not explain the difference, and its cause is not established here. Movability is therefore a property of a task under a given engine, unit and direction population, and the confirmation panels measured it under bf16 and the ban-free unit only.

**Table 222.** Movability of the 15 existing tasks across measurements (escape fraction of fixed directions at alpha 1 / alpha 2, or off-default share of per-sample plan noise at alpha 1 / alpha 2). Sources: record audit `screen.json`; panel A `results/extra_arm_a.json` (iteration-4 fresh directions and the re-measurement arm); panel B `results/variants.json` (parent re-measure, pooled over both alphas); plan noise experiment `results/alpha_sweep.json` (iteration 4); knob experiment `results/cells.json` (iteration 5).

| Task | Frozen screen (8-bit, ban unit) | Iteration 4, 40 fresh directions (8-bit, bench unit) | Iteration 5, 8 directions (bf16, ban-free unit) | Iteration 5, panel B parent (bf16, ban-free, pooled) | Iteration 4 per-sample plan noise (8-bit, ban unit) | Iteration 5 per-sample plan noise (bf16, ban-free unit) |
|-|-|-|-|-|-|-|
| kth smallest | movable | 0.30 / 0.63 | 0.125 / 0.375 | 0.500 | 0.28 / 0.50 | 0.08 / 0.28 |
| connected components | movable | 0.38 / 0.73 | 0.000 / 0.250 | 0.188 | 0.12 / 0.60 | 0.02 / 0.02 |
| shortest path | movable | 0.18 / 0.20 | 0.000 / 0.000 | not run | 0.26 / 0.54 | 0.00 / 0.04 |
| two sum | movable | 0.00 / 0.13 | 0.000 / 0.000 | 0.000 | 0.00 / 0.02 | 0.00 / 0.04 |
| grid | movable | 0.05 / 0.13 | 0.000 / 0.000 | not run | 0.06 / 0.24 | 0.00 / 0.02 |
| find duplicate | movable | 0.00 / 0.00 | 0.000 / 0.000 | 0.000 | 0.00 / 0.02 | 0.00 / 0.00 |
| substring search | immovable | 0 of 8 / 0 of 8 | 0.000 / 0.000 | 0.000 | excess 0.00 at alpha 2 or less | 0.00 / 0.00 |
| Fibonacci | immovable | 0 of 8 / 0 of 8 | 0.000 / 0.000 | 0.000 | excess 0.01 | 0.00 / 0.00 |
| top-k frequent | immovable | 0 of 8 / 0 of 8 | 0.000 / 0.000 | 0.000 | excess 0.04 | 0.00 / 0.00 |
| nonoverlapping intervals | immovable | 0 of 8 / 0 of 8 | 0.000 / 0.000 | 0.000 | excess 0.00 | 0.00 / 0.00 |
| longest increasing subsequence | immovable | 0 of 8 / 0 of 8 | 0.000 / 0.000 | not run | excess 0.03 | 0.00 / 0.00 |
| merge intervals | immovable | 0 of 8 / 0 of 8 | 0.000 / 0.000 | not run | excess 0.00 | 0.00 / 0.00 |
| topological order | immovable | 0 of 8 / 0 of 8 | 0.000 / 0.000 | not run | excess 0.00 | 0.00 / 0.00 |
| first and last position | immovable | 0 of 8 / 0 of 8 | 0.000 / 0.000 | not run | excess -0.08 | 0.03 / 0.07 |
| cycle detection | not screened | 0 of 8 / 0 of 8 | 0.000 / 0.000 | not run | excess 0.01 | 0.00 / 0.07 |

**The transplant in two families.** In Qwen3-8B the transplant passed on 1 of 5 base-diverse tasks and in Gemma it moved 2 of 7, each time onto the base runner-up. The successes share a feature: in Gemma the instruct twin already wrote the runner-up 8% to 12% of the time, and in Qwen3-8B the transplant raised the pass rate from 0.78 to 0.98 while it moved top-k frequent. Where the instruct model never wrote the base runner-up, the base states did not install it. In both families the base-minus-instruct difference at the task-specification positions was large (Qwen3-8B 0.39 to 0.53 of the residual norm, 71% of cells above 4 ban-free units at lambda 1; Gemma a median of 5.2 ban-free units), and in both an isotropic or cross-task displacement of comparable size did more damage than the coherent base content.

[FIGURE:fig_transplant]

**Novelty, audited again.** No artifact of this iteration found a correct novel algorithm (Table 223), including the base model's own output and the transplanted output.

**Table 223.** Novelty audits of iteration 5. Sources: the novelty audit files of the five experiments.

| Artifact | Correct programs in the pool | Correct programs outside the catalogue | Final classes | Novel |
|-|-|-|-|-|
| Transplant experiment | all arms, base model included | 48 | 27 known techniques outside the frozen catalogue, 12 degenerate, 9 catalogue variants (judges called 14 novel) | 0 |
| Panel A | 6,854 | 2 | 1 catalogue variant, 1 degenerate | 0 |
| Panel B | 10,366 | 12 | 7 catalogue variants, 5 degenerate | 0 |
| Knob experiment | every correct program labelled other | 12 | 10 labeller misses, 1 degenerate, 1 unresolved | 0 |
| Gemma experiment | every correct program labelled other | 56 | 35 catalogue variants, 21 degenerate | 0 |

## 5.11 What iteration 5 established, what it ruled out, and what it abandoned

Everything below is one or two model families at 4B to 8B parameters, memorised LeetCode-style tasks, and labels from gated labellers, except the base-model labels of Gemma, which agree with an adjudication at only 0.64. Every Qwen3-8B number of this iteration comes from a bf16 engine.

**Established.**

1. *Temperature does not change the algorithm, under every sampler the run used.* With thinking on, top-k 10 and the same seed, the algorithm changed in 0 of 20 seeds across four temperatures on the shortest path task, and the first approach named in the thinking never changed.
2. *Where a random nudge moves the instruct model, it lands on the base model's runner-up.* On new tasks the base runner-up named the push landing in 6 of 7 events (Poisson-binomial p 0.003), with the base composition ahead of association by 0.75 nats (exact Wilcoxon p 0.055 with the corrected association) and of proximity by 0.50. In Gemma it named 5 of 7 (p 0.025; 1.50 nats over association, p 0.023), and on the existing Qwen3-8B tasks 5 of 5. In panel A no nudged program landed outside the base repertoire.
3. *The base model is more diverse than the instruct model on most tasks under identical prompts.* The instruct twin wrote its default in 96% to 100% of programs on all 15 existing tasks, while the base model was base-diverse on 5 and intermediate on 7, and every new unit but one had beta of at least 0.05. The base model's own correct output is thin under the chat template (14 to 55 correct programs per 100 to 200 on the existing tasks).
4. *Plan noise's effect is not its token-level departure from the twin.* At alpha 2 it moved 19 slots against 3 for decoding matched to its per-token KL (exact p 0.0009).
5. *The record repairs.* The held-out movability test is inconclusive under catalogue-only avoidance and disconfirmed under the default-drop sensitivity; the read position and condition sentence are inert only at per-position doses up to 4 ban units; landing comparisons on matched events give push -0.76 against association -3.11 on 3 events and -1.37 against -3.46 on 5.

**Ruled out, or not supported.**

- *The movability half: the base repertoire predicts which tasks a nudge moves.* Spearman -0.03 in panel A, 0.21 in panel B and 0.15 pooled over 13 new units, below the disconfirming bound of 0.3; 4 of 10 base-diverse new units never moved, and in panel A the runtime merit gap and the twin modal share tracked movability better than beta. The screen correlation of 0.78 did not transfer to new tasks.
- *The transplant claim: a transplant of base plan states reopens the base repertoire.* Disconfirmed by the frozen rule (1 of 5 base-diverse tasks); on kth smallest a matched-norm random displacement moved more programs than the base states (2:20). The narrowing installed by tuning is not carried by the task-specification states of blocks 12 to 23 alone.
- *The de-sharpening push.* A push along the base-minus-instruct direction never escaped at 0.5 to 2 ban-free units, while an isotropic push did on kth smallest.
- *The plan-sampler comparison: plan noise prices at least as well as text-level plan samplers.* Disconfirmed (1 of 5 decisive tasks); a base-written intent won on connected components, the shortest path task and two sum.

**Inconclusive.**

- *The movability half in Gemma.* Spearman 0.42 (p 0.060), with the twin modal share and the novelty instruction ahead of beta; descriptively 6 of 7 base-diverse tasks moved against 2 of 8 others.
- *Top-k frequent.* The one Qwen3-8B task where the transplant reopened the base runner-up also gained 20 pass points, so restored correctness and a reopened choice are not separated.

**Dead ends, with the evidence that closed them.**

- *The base-minus-instruct direction as a knob.* Closed by Table 186: it never escapes, and the difference it encodes is mostly shared across tasks (cosine 0.76 to 0.88) and larger than the dose at which random noise breaks programs.
- *Transplanting at the read position.* The base and instruct states differ there by about the size of the residual, and the transplant broke the output on 13 of 15 tasks without moving an algorithm.
- *Plan noise as the practical knob for algorithmic diversity.* On the decisive tasks two text-level samplers price better, and under the bf16 engine and ban-free unit plan noise moves more than 10% of programs only on kth smallest.
- *Signed progress toward the runner-up as the next predictor.* Closed in the record audit (Table 177): concentrated on one task, negative on two, matched by a within-class control.

## 5.12 What the next iteration takes from this one

The narrowed-repertoire account split in two. Its landing half held in both families and on unseen tasks: when a nudge moves the instruct model, it moves it to the algorithm the base model writes next, and a forecast built from base samples, before any push, names that landing better than the model's stated alternative. Its movability half failed on unseen tasks: a base model that writes many algorithms does not mark a task the instruct model can be nudged off, and its states, written into the instruct prefill, reopen the choice on one task in five. The base repertoire marks where a nudge can lead, not whether it can lead anywhere.

The open question is therefore what makes a base-diverse task immovable. Count primes and valid anagram (beta 0.81 each) never moved, while trapped rain water (0.23) did. Two leads came out of this iteration's data. In panel A the three units that moved had an alternative at least twice as fast as the default and the three that did not had none, although median of two sorted lists broke the pattern. And in the transplant experiment early blocks 0 to 11 moved kth smallest and connected components more than the main band, which suggests the narrowing sits at least partly upstream of blocks 12 to 23. The positioning audit names the baselines a further test needs: weight interpolation between the base and instruct models, layer restoration at the transplant's block ranges, and token-level base and aligned collaboration [92, 93, 94, 102]. The base-written intent, which beat plan noise on three of five tasks, is the strongest practical knob the run has priced, and it is itself a sentence-level form of that collaboration. Finally, movability has to be measured under the engine and unit at which it will be used: the six screen-movable tasks of iteration 4 shrank to two under bf16 and the ban-free unit, for reasons this iteration did not establish.
