## 3.3 Bench forecast experiment: do ban-free forecasts predict where the modal bench bans land? (Qwen3-8B)

**Why.** This experiment [ARTIFACT:art_1AYTO1Epb_7t] was the confirmation of the title claim in Qwen3-8B. On the 12 frozen bench tasks, which had never seen a ban prompt, it built the four ban-free forecasts of where each task's modal ban would land, sealed them in a sha256 hash chain, and only then sampled the bans. If a ban only removes the default, the subtraction or ladder forecast should win; if it substitutes, association or proximity should.

**Design.** The model ran in bf16 (revision b968826d, thinking off, T = 1.0) on one RTX 4090. The bench, its labellers (runtime trace first, AST second, blind judge on disagreement) and its gold sets were copied with all 146 committed file hashes verified, and the labeller recheck matched every gate value on 12 of 12 tasks. Ban prompts used the five frozen templates with token-length matched neutral twins (identical token ids from the task text on). The ban-free arms (600 samples each over the 12 tasks) were the neutral twin, the one-shot, persistent and sham signature vetoes, the nonce ban, the novelty instruction, up to three iterated veto rounds, and three seeded isotropic random directions patched into the task specification states at layers 12 to 23 at the ban's own displacement norm (50 samples per task each). The vetoes used exact rejection and a masked redraw coupled to the twin samples by seed. Seventeen forecast files, the n-grams, seeds, norms and the analysis code were sealed at 18:50:57Z; the first ban request followed at 18:55:16Z. Then 1,200 ban samples (5 templates by 20 per task) were labelled, and a band patch control spliced the ban's own task specification states at layers 12 to 23 into the twin (600 samples). Every family's forecast was smoothed the same way (93% forecast, 5% uniform over survivors, 2% on other) and scored by its mean log score per attempt not banned; the frozen rule advances a family that beats the next best by at least 0.10 nats on at least 3 gated events whose top-1 nominations disagree, and an undefined forecast is scored as uniform.

**Table 94.** Forecasts committed before any ban sample (top-1 survivor; "undefined" is scored as uniform). The distinctive n-gram is shown as tokenised; its source is the 8-bit pilot unless marked. Source: bench forecast experiment `README.md` and `predictions/`.

| Task | Default | Distinctive n-gram | Subtraction | Ladder | Association | Proximity | Nominations disagree |
|-|-|-|-|-|-|-|-|
| kth smallest | full sort | `'    nums'` | undefined | quickselect | quickselect | heapify and pop | yes |
| substring search | naive | `' needle:\n           '` | undefined | undefined | KMP | built-in find | yes |
| find duplicate | hash set | `' set'` | sort and adjacent check | undefined | Floyd cycle detection | sort and adjacent check | yes |
| two sum | hash map | `' if complement'` | undefined | undefined | sort and two pointers | brute force | yes |
| connected components | union find | `' find'` | DFS | undefined | DFS | label propagation | yes |
| nonoverlapping intervals | greedy by end | `' if start'` (rederived on bf16) | undefined | undefined | DP with bisect | DAG longest path | yes |
| Fibonacci | iteration | `'('` | undefined | matrix power | matrix power | memoised recursion | yes |
| topological order | Kahn | `'.p'` | undefined | undefined | DFS postorder | undefined | no |
| merge intervals | sort and sweep | `' last'` | undefined | undefined | interval tree | union find | yes |
| first and last position | binary search | `'_last'` | undefined | undefined | bisect module | bisect module | no |
| top-k frequent | sort by count | `'_counts'` (rederived on bf16) | undefined | undefined | heap | heap | no |
| longest increasing subsequence | quadratic DP | `' j'` | undefined | patience sorting | patience sorting | patience sorting | no |

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

The frozen rule returned "SUBTRACTION/LADDER (LADDER)": on the five gated events, all with disagreeing nominations, the ladder won 3 (kth smallest, find duplicate, connected components) and proximity 2 (two sum, merge intervals). Table 96 shows why that label carries little. On find duplicate and connected components the ladder was undefined and scored as uniform, and it won because every defined forecast named the wrong survivor. Counting only wins by defined forecasts (a post hoc check, not preregistered) gives ladder 1 and proximity 2, and no family advances. Against the uniform reference over the gated events, the mean differences are ladder +0.06 (task bootstrap 95% [0.00, 0.18]), subtraction -0.69 [-1.42, 0.00], proximity -1.53 [-2.96, 0.09] and association -1.78 [-2.73, -0.73]: no family forecasts better than uniform on average, and the association forecast is worse than uniform on all five events.

**Table 96.** Mean log score per attempt not banned for each forecast (nats; higher is better; uniform over the survivors is the reference). Gated events are marked †. Source: bench forecast experiment `results/c1_events.jsonl`.

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

The landings were specific to the banned task and mostly unforeseen. Find duplicate went to index marking, which places each value at index value minus one: the model wrote it only once in 40 template-forced attempts in the bench build (adherence 0.28 over all forced prompts), and no family nominated it. Connected components went to BFS (83 of 100) while subtraction and association said DFS. Merge intervals went mostly to "other", a merge sweep without sorting that failed every time (0 of 44). Fibonacci's "other" was Binet's closed form, which also failed (0 of 33). Only the kth smallest landing (quickselect: ladder, association and the 8-bit likelihood) and the two sum landing (brute force: proximity) were hit by a top-1 nomination. On 3 of the 5 gated events no family's top-1 named the realised landing.

**Signature vetoes move the surface, not the algorithm.** The distinctive n-gram fired in 95% of twin samples and the redraw always avoided it, yet the default survived every persistent and iterated round on 9 of 12 tasks. The model respelled the same mechanism: on kth smallest `nums.sort()` became `return sorted(nums)[k-1]`, and on two sum the next round's distinctive token was `' compliment'`, a misspelling that dodges `' complement'`. The vetoed text reappeared under another token split in 23% of one-shot samples and 54% by round 2. Where vetoes did move off the default, most outputs were invalid. The sham veto of a shared token broke programs without moving the algorithm (for example, the model indented with non-breaking spaces after the indentation token was masked). The test of whether the one-shot veto reproduces the ban's landing was therefore undetermined: the one-shot veto never reached 0.5 avoidance on a gated task (kth smallest 0.38, connected components 0.33, others 0). Descriptively, the last iterated round was eligible on find duplicate and connected components, and both landed elsewhere than the ban: sort and adjacent check against the ban's index marking (Jensen-Shannon divergence 0.77 against a template resampling 95th percentile of 0.09), and DFS against the ban's BFS (0.58 against 0.09).

**Generic pushes rarely move this collapsed model.** Nonce bans moved nothing except on first and last position, whose twin was already noisy. The novelty instruction moved kth smallest (all 50 off the default, 45 to quickselect), longest increasing subsequence, Fibonacci, substring search and connected components. One of three random directions moved kth smallest (avoidance 0.82, mostly quickselect) and connected components a little (0.26, to DFS); the HF twin control kept the default at 0.98 and 1.00 on those tasks, so the movement is not an engine artefact. The positive control of patching the ban's own task specification states into the twin at layers 12 to 23 reproduced the ban's avoidance only on kth smallest and connected components (1.00 each), partly on two sum (0.22) and merge intervals (0.14), and nowhere else. On most tasks the ban's effect is not carried by the task specification states of that band alone, which Section 3.6 confirms behaviourally.

**Wording.** The banned share differed by template far more than by chance (Table 97): likelihood ratio 374 on 4 degrees of freedom (p about 1e-79); a mixed logistic model put the template standard deviation at 2.0 logits [1.1, 3.5] and the template by task deviation at 1.25 [1.05, 1.49]; a shuffled template placebo gave p = 0.44 (0.39 in the second audit's own likelihood ratio test). Under the fourth template the default kept at least 70% of samples on 10 of 12 tasks.

**Table 97.** Banned programs per template (of 20) under each modal bench ban. Source: bench forecast experiment `results/template_effect.json`.

| Task | First | Second | Third | Fourth (`X is not allowed here`) | Fifth |
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

**Design.** For every non-default algorithm Y of the 12 frozen bench tasks with at least one correct forced program (33 Y; 19 "priority" Y whose frozen associate differs from the default), the prompt shows up to 5 name-scrubbed correct programs of Y and then asks one of three things: write a correct solution (the copy twin), write a correct solution that does not use Y (named, the fifth template), or write a correct solution that uses a different algorithm from the one above (unnamed). Each arm had 50 samples per Y with seeds shared across arms (Qwen3-8B bf16, vLLM 0.11.0, one NVIDIA L4). Four forecasts were committed by hash before any ban sample: ladder (the context-free default), association (the modal frozen answer for Y), proximity (the survivor whose forced programs are nearest the shown programs by Zhang-Shasha tree edit distance [64]) and the subtraction forecast in context (the landing of an iterated persistent signature veto of Y under the copy twin prompt, with no ban text). GPU smoke tests confirmed the veto: 0 of 20 veto samples contained the vetoed n-gram against 20 of 20 copy samples, an inert veto left 20 of 20 outputs identical, and veto and copy twins diverged exactly at the vetoed position in 20 of 20. Of 10,600 programs, 7,478 were labelled by agreeing runtime and AST labellers, 1,398 by the judge, 147 by runtime alone, and 1,577 had no code block (mostly from veto rounds).

**Showing a solution makes the model copy it, and banning it sends the model home.** Under the copy twin a mean 0.93 of attempts used the shown algorithm (median 1.00; none below 0.2), and the default appeared in 0.05. Under the named ban, avoidance averaged 0.95 and the default's share of attempts rose to 0.72 (Table 98). We call this return to the context-free default *snap-back*. In 24 of the 31 gated named events the modal replacement was the default (14 of 18 for priority Y). Named and unnamed bans picked the same modal replacement for 0.88 of Y, and their landings were consistent under the Jensen-Shannon resampling null for 0.79 of Y: naming Y adds little beyond "something else".

**Table 98.** The default's share of attempts by arm, pooled over the 33 shown algorithms. Source: exposure experiment `README.md`, `results/other_reports.json`.

| Copy twin | Final veto round under the copy twin | Named ban | Unnamed ban |
|-|-|-|-|
| 0.05 | 0.10 | 0.72 | 0.82 |

[FIGURE:fig_exposure_snapback]

Table 99 gives every named exposure event. The frozen rule (at least 3 wins by 0.10 nats on gated, disagreeing events) advanced the ladder with 7 wins, against subtraction 2, association 2 and proximity 0, so the frozen branch is "SUBTRACTION/LADDER (LADDER)". Gating removed two events (size-k heap on kth smallest and patience sorting on longest increasing subsequence, where Y was kept), and 30 of the 31 gated events had disagreeing nominations.

**Table 99.** Every named exposure event (N = 50 per arm). The winner is the family that beats the next best by at least 0.10 nats on a gated event with disagreeing nominations ("none" when the top two tie; "n/a" when the event is ungated or not disagreeing). An undefined subtraction forecast is scored as uniform. Source: exposure experiment `results/c1_events.jsonl`, `results/arm_stats.json`.

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

**How strong the verdict is.** The counting rule is not a significance test. In a unit test with no information, it advanced some family in 85% of 200 simulated draws, while the Holm-corrected Wilcoxon test erred in 2%; on the real events, a label permutation placebo advanced some family in 100% of draws (the ladder in 43%). The branch label is therefore weak evidence, and the paired tests are the informative part. The signature veto rarely removed Y: the subtraction forecast in context was defined for only 4 of 33 Y (median of medians to quickselect, brute force to hash map, label propagation to union find, exponential search to binary search), Y still re-emerged in at least 20% of attempts after three rounds for 25 of 33 Y, the veto cost a mean 0.70 of pass rate, and 46% of final round outputs were invalid. Because an undefined subtraction forecast is uniform, its tied top-1 is what makes almost every event disagreeing. Every preregistered sensitivity returned the ladder with 7 to 9 wins (subtraction top-1, excluding co-vetoed survivors, priority Y only with 18 events, token distance proximity, correct-only landings, and excluding labeller-flagged tasks) except "exclude undefined subtraction", which leaves 2 events and is undetermined. An exploratory comparison of ladder, association and proximity on the 21 events where those three disagree gave wins 8, 3 and 0 (ladder minus association p = 0.027, Holm over three 0.081). The secondary exposure test, whether the ban's modal survivor matches the veto's where the associate differs, had 2 qualifying events (brute force and label propagation); both agreed, but both landings are the default, so this is snap-back, not a test of substitution.

**Wording.** A template arm (first to fourth templates, 10 samples for each of the 19 priority Y; descriptive and never in the contest) gave mean avoidance 0.93, 0.94, 0.96 and 0.81: the fourth template is again the weakest. A stop token bug in the first round-2 veto run (the end-of-turn token was chosen as the n-gram) was found and fixed; the 750 affected samples are kept apart. Deduplication left 11 of 33 Y with a single shown program. GPU time was about 1.0 GPU hour on one L4, judge spend USD 0.096 over 1,229 calls, and an independent rederivation matched all 66 events.

