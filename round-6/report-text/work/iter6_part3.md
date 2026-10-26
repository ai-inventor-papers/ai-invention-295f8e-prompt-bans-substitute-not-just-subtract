## 6.4 Where a ban and an instruction are carried, and where noise acts, in bf16 (Qwen3-8B)

**Why.** The localization claim predicted, from the route classes of iterations 2 and 3, where the substitute of a ban is carried: in the task-specification states on the prompt-route tasks, at the condition span on the direct-route tasks. Stage A tests that prediction without any training, by moving the states themselves. The same experiment [ARTIFACT:art_rMlbrjVB1c__] reran the iteration-4 noise-site comparison in bf16, set state noise at generated tokens against a temperature matched on per-token KL, applied the top-five plan push, and ran the landing contest. Everything ran in one bf16 engine with exact common random numbers on a 16 GB card, with the input embedding table kept in CPU memory; per-slot twin labels agreed with iteration 5's bf16 engine on 0.975 of slots for kth smallest and shortest path and 1.00 for the other tasks. Seven commitments formed an unbroken sha256 chain, and a standard-library script re-derived every headline from raw rows (295 checks, 0 mismatches) while a placebo version of each test failed.

### 6.4.1 Stage A: full-state exchange of the ban

We call a *full-state exchange* the replacement, in the neutral twin's forward pass, of the residual states at a set of positions and blocks by the states the full ban prompt produces at the same positions; because the twin and the ban have identical token ids from the task text on, every task-specification position aligns. The exchanges covered four block bands at the task-specification positions (0 to 11, 12 to 23, 24 to 35, 0 to 35), a splice of the key-value cache of the condition span (the direct route), and the read position at all 36 blocks. The controls were the twin, a matched-norm random exchange (the twin's state plus a fresh random direction scaled to the ban's own displacement per slot, block and position), a placebo that takes a second neutral twin as the source, and an identity exchange. The outcome is the share of correct programs implementing the ban's substitute Y; the *transfer* of a cell is its Y share minus the twin's, and its *recovery* is the transfer divided by the full ban's. Each cell has N = 30 on paired slots. Tables 244 to 249 give every cell on the six tasks.

The prediction held where the route data said it should, and failed at one task where they said it should not. On shortest path, exchanging the full ban's task-specification states at all blocks into the twin turns 24 of 30 slots from Dijkstra to Bellman-Ford/SPFA (transfer 0.80, McNemar 24:0, Holm p 7e-7, pass ratio 0.90), while the condition-span splice and the read-position exchange transfer nothing. Blocks 12 to 23 alone carry 0.60 and blocks 24 to 35 alone 0.37; blocks 0 to 11 carry none. On kth smallest the same exchange transfers 0.57 to quickselect with every slot leaving the full sort, and here the condition span also carries the ban (0.93). On connected components every slot leaves union find under the exchange at blocks 12 to 23 or 0 to 35 (off-default transfer 1.00), but only 0.37 to 0.47 land on the ban's BFS and the rest on DFS. On the direct-route tasks the condition-span splice alone reproduces the ban (two sum 1.00, find duplicate 0.90), as predicted, but on two sum the task-specification states also transfer brute force at 0.43, above the predicted ceiling of 0.2. The committed verdict is therefore NOT SUPPORTED. The secondary predictions hold: the condition span carries at least 0.5 on the direct-route tasks and at most 0.2 on shortest path, the read position carries at most 0.2 everywhere (it carries 0.00 on all six tasks), the placebo moves at most 0.03, and the exchange beats the matched-norm random exchange where it transfers (shortest path 23:0, kth smallest 16:2, connected components 11:0). The ban's information, not the size of the perturbation, is what moves the algorithm.

[FIGURE:fig_stageA_transfer]

**Table 244.** Stage A on kth smallest (default full sort; Y = quickselect; route class from iterations 2 and 3: either route suffices). Twin on slots 0 to 29: Y share 0.00, off-default 0.00, pass 1.00, full sort 30. Exchange at blocks 0-35 against the matched-norm random exchange: 16:2, exact p 0.0013 (Holm 0.0020). Source: exchange and site experiment `results/stage_a.json`, `results/summary.md`.

{{stageA_T03}}

**Table 245.** Stage A on connected components (default union find; Y = BFS). Twin: Y share 0.00, off-default 0.00, pass 1.00, union find 30. Exchange at blocks 0-35 against the matched-norm random exchange: 11:0, exact p 9.8e-4 (Holm 0.0020).

{{stageA_T10}}

**Table 246.** Stage A on shortest path (default Dijkstra; Y = Bellman-Ford/SPFA; prompt route). Twin: Y share 0.00, off-default 0.00, pass 1.00, Dijkstra 30. Exchange at blocks 0-35 against the matched-norm random exchange: 23:0, exact p 2.4e-7 (Holm 7.2e-7).

{{stageA_T2}}

**Table 247.** Stage A on two sum (default hash map; Y = brute force; direct route). Twin: Y share 0.00, pass 1.00, hash map 30.

{{stageA_T05}}

**Table 248.** Stage A on find duplicate (default hash set; Y = index marking; direct route). Twin: Y share 0.00, pass 1.00, hash set 30.

{{stageA_T06}}

**Table 249.** Stage A on the grid task (default BFS; Y = DFS; prompt route in likelihood, mixed in behaviour). Twin: Y share 0.00, pass 0.90, BFS 27 correct. Pass ratios above 1 occur because the twin's own pass rate is below 1.

{{stageA_T1}}

The condition-span splice also matches iteration 3's behavioural route arms: its recovery is 1.00 on two sum and 0.93 on find duplicate, where iteration 3's direct-route fraction was 0.96 and 0.99, and 1.40 on kth smallest (direct-route fraction 0.74). On connected components its recovery toward BFS is 0.11, although every slot leaves union find: either route alone removes the default and lands on DFS, as iteration 4's route landings had shown.

**Positive instructions are carried the same way.** As an extension, the forced prompt `Implement Bellman-Ford or SPFA for this task.` replaced the ban as the source (Table 250). Its padding twin, the same prompt with the instruction's tokens replaced by padding, stays on Dijkstra in 29 of 30 programs; exchanging only the forced prompt's task-specification states at all blocks into that twin gives Bellman-Ford/SPFA in 30 of 30. On connected components the forced BFS prompt's states give BFS in 28 of 30 against union find 30 of 30 for its twin. The shortest path semantic seed, which moved that task 66 points in iteration 1, moved nothing under this frame (Dijkstra 30 of 30), and neither did its exchange (2 of 30). The fourth ban template, held out of every other cell, transfers through the exchange as the other templates do (shortest path 0.70, kth smallest 0.60 on quickselect with every slot off the full sort, connected components 0.70, N = 10 each).

**Table 250.** Extensions: forced sources, the semantic seed and the fourth template, each exchanged at blocks 0-35 into its own twin. Source: exchange and site experiment `results/summary.md`.

| Task | Cell | n | Y share (Y) / default share | Off-default share | Pass | Composition |
|-|-|-|-|-|-|-|
| kth smallest | fourth-template ban | 10 | 0.30 (quickselect) / 0.00 | 1.00 | 1.00 | size-k heap 7, quickselect 3 |
| kth smallest | fourth-template twin | 10 | 0.00 / 1.00 | 0.00 | 1.00 | full sort 10 |
| kth smallest | fourth-template exchange, blocks 0-35 | 10 | 0.60 / 0.00 | 1.00 | 0.80 | quickselect 6, size-k heap 4 |
| connected components | fourth-template ban | 10 | 0.80 (BFS) / 0.00 | 1.00 | 1.00 | BFS 8, DFS 2 |
| connected components | forced BFS | 30 | 1.00 / 0.00 | 1.00 | 1.00 | BFS 30 |
| connected components | padding twin of forced BFS | 30 | 0.00 / 1.00 | 0.00 | 1.00 | union find 30 |
| connected components | forced BFS exchange, blocks 0-35 | 30 | 0.93 / 0.00 | 1.00 | 0.87 | BFS 28, DFS 2 |
| connected components | fourth-template twin | 10 | 0.00 / 1.00 | 0.00 | 1.00 | union find 10 |
| connected components | fourth-template exchange, blocks 0-35 | 10 | 0.70 / 0.00 | 1.00 | 1.00 | BFS 7, DFS 3 |
| shortest path | fourth-template ban | 10 | 0.70 (Bellman-Ford/SPFA) / 0.30 | 0.70 | 1.00 | Bellman-Ford/SPFA 7, Dijkstra 3 |
| shortest path | forced Bellman-Ford or SPFA | 30 | 1.00 / 0.00 | 1.00 | 0.90 | Bellman-Ford/SPFA 30 |
| shortest path | padding twin of the forced prompt | 30 | 0.03 / 0.97 | 0.03 | 0.97 | Dijkstra 29, Bellman-Ford/SPFA 1 |
| shortest path | forced exchange, blocks 0-35 | 30 | 1.00 / 0.00 | 1.00 | 1.00 | Bellman-Ford/SPFA 30 |
| shortest path | semantic seed | 30 | 0.00 / 1.00 | 0.00 | 0.93 | Dijkstra 30 |
| shortest path | padding twin of the seed | 30 | 0.03 / 0.97 | 0.03 | 0.97 | Dijkstra 29, Bellman-Ford/SPFA 1 |
| shortest path | seed exchange, blocks 0-35 | 30 | 0.07 / 0.93 | 0.07 | 0.87 | Dijkstra 28, Bellman-Ford/SPFA 2 |
| shortest path | fourth-template twin | 10 | 0.00 / 1.00 | 0.00 | 1.00 | Dijkstra 10 |
| shortest path | fourth-template exchange, blocks 0-35 | 10 | 0.70 / 0.30 | 0.70 | 1.00 | Bellman-Ford/SPFA 7, Dijkstra 3 |

Stage A's own unit tests passed except one: splicing the cache of the task-specification span reproduced the exchange's top token with a logit gap of 0.5 in bf16 and 10 of 10 equal labels, but not byte for byte. The Stage A arms on trapped rain water and minimum spanning tree weight were dropped for GPU time.

### 6.4.2 Where noise acts, in bf16

The site rerun repeated iteration 4's grid on kth smallest and connected components in bf16, at the ban-free unit, with a fresh direction per sample, N = 30 per cell and alpha 1, 2, 4 and 8 (Tables 251 and 252). Noise at the task-specification positions moves the algorithm in bf16: on kth smallest blocks 12 to 23 reach a correct off-default share of 0.37 at alpha 2, and on connected components blocks 0 to 11 reach 0.33 at alpha 4. The read position, the condition span and the late blocks barely move it below alpha 8. On kth smallest the plan site beats the read position in paired slots 24:5 (exact p 5.5e-4) and the condition span 22:0, and a Mantel-Haenszel odds ratio [129] within quintiles of the downstream displacement is 4.6 [1.9, 11.3]. Connected components shows a weaker picture: its plan site moves only 0.07 at alpha 2 and 0.17 at alpha 4, the early blocks beat it (4:18, p 0.004), and the read position starts moving at alpha 8 (0.30).

The committed rule fitted a Firth-penalised logistic model [125] of a correct off-default program on site indicators and the log displacements at matched downstream displacement (Tables 253 and 254). It returned WITHDRAWN, for two reasons. The raw condition-span arm never reaches the plan site's downstream displacement, so it has no common support and its energy-matched arm stood in; and at alpha 8 every plan-site program failed (pass 0.00) while the read position began to move, which erases the read-position contrast in the preregistered model. A post-hoc sensitivity restricted to alpha of 4 or less (before breakage) puts the read position clearly below the plan site on both tasks: beta -3.76 (profile interval [-7.29, -0.47], cluster bootstrap [-8.18, -1.40]) on kth smallest and -4.98 ([-9.77, -0.89]; [-11.48, -1.53]) on connected components. The prefill-site claim is therefore withdrawn as preregistered, and its post-hoc form survives in bf16 at the ban-free unit.

**Table 251.** The bf16 site grid on kth smallest (twin correct off-default 0.00; displacements are medians in residual units at block 35). Source: exchange and site experiment `results/site_grid.json`.

{{site_T03}}

**Table 252.** The bf16 site grid on connected components (twin correct off-default 0.00).

{{site_T10}}

**Table 253.** Firth indicator model on kth smallest at matched downstream displacement (n 387, 48 events, 387 of 720 rows in common support; the condition span enters through its energy-matched arm). Mantel-Haenszel odds ratio, plan site against read position, within quintiles of the log displacement at the read position: 4.61 [1.87, 11.34]. Paired flips, plan site only : other site only: read position 24:5 (p 5.5e-4), condition span 22:0 (p 4.8e-7), blocks 0-11 17:9 (p 0.169), blocks 24-35 23:3 (p 8.8e-5), generated tokens 21:18 (p 0.749).

{{firth_T03}}

**Table 254.** Firth indicator model on connected components (n 374, 32 events, 376 of 720 rows in common support). Mantel-Haenszel odds ratio, plan site against read position: 0.82 [0.31, 2.18]. Paired flips, plan site only : other site only: read position 7:10 (p 0.629), condition span 7:0 (p 0.016), blocks 0-11 4:18 (p 0.004), blocks 24-35 7:1 (p 0.070), generated tokens 7:9 (p 0.804).

{{firth_T10}}

### 6.4.3 State noise at generated tokens against matched temperature

The token claim's second half set noise on the residual states of generated tokens 1 to 32 against a temperature applied to the same tokens and bisected to the same per-token KL, which we call decoding at matched departure (Table 255). At alpha 2 the state noise leads on discordant correct off-default flips, 12:6 on kth smallest and 7:3 on connected components, but neither is significant (p 0.24 and 0.34). At alpha 4 the lead on connected components reaches 8:1 (p 0.039), at a pass rate of 0.38 against 0.70. The rule (p below 0.05 on both tasks at alpha 2) is not met: state noise against token temperature is not established in bf16.

**Table 255.** State noise at generated tokens 1 to 32 against decoding at matched departure (N = 50 paired slots). Source: exchange and site experiment `results/state_vs_token.json`.

| Task, alpha | State-noise KL per token (nats) | Matched temperature | Share of tokens with the temperature on | State only : temperature only | Exact p | State-noise flip share | Temperature flip share | State-noise pass | Temperature pass |
|-|-|-|-|-|-|-|-|-|-|
| kth smallest, alpha 2 | 0.3883 | 2.06 | 0.3762 | 12:6 | 0.238 | 0.26 | 0.14 | 0.94 | 0.98 |
| kth smallest, alpha 4 | 2.3336 | 3.00 | 1.7734 | 8:3 | 0.227 | 0.18 | 0.08 | 0.50 | 0.82 |
| connected components, alpha 2 | 0.2315 | 2.72 | 0.2310 | 7:3 | 0.344 | 0.14 | 0.06 | 0.92 | 0.92 |
| connected components, alpha 4 | 3.0926 | 3.00 | 0.8178 | 8:1 | 0.039 | 0.16 | 0.02 | 0.38 | 0.70 |

### 6.4.4 The top-five push in bf16

On the grid task, iteration 4's top-five direction (from the mean of the five banned centroids toward the mean of the survivors) was applied at the plan site at alpha 1, 2, 4 and 8 (Table 256). It breaks programs before it moves the algorithm: the pass rate falls from 0.67 to 0.30, 0.03 and 0.00, with at most one correct program other than BFS per cell, so the landing test could not be computed. Projected onto the plane of the first two principal components of the ten forced-prompt centroids (36% and 25% of their variance), the push leaves the forced-prompt manifold: already at alpha 1 it moves farther along the first component than the whole spread of the ten centroids. The prompt version of the top-five ban moves the task-specification states from below the centroid cloud into it, between the banned DFS and greedy best-first centroids and the surviving bidirectional BFS, IDA* and bidirectional A* centroids, and its behaviour stays inside the banned set (BFS 25, DFS 23 of 50; avoidance 0.00).

**Table 256.** The top-five plan push and the prompt top-five ban on the grid task. Source: exchange and site experiment `results/top5_push.json`.

| Cell | n | Pass | BFS share | Correct programs other than BFS | Landing test |
|-|-|-|-|-|-|
| twin | 50 | 0.92 | 1.00 | 0 | n/a |
| single BFS ban | 30 | 0.40 | 0.00 | 12 (DFS 12) | n/a |
| top-five push, alpha 1 | 30 | 0.67 | 0.97 | 1 (DFS, banned) | not computable |
| top-five push, alpha 2 | 30 | 0.30 | 1.00 | 0 | not computable |
| top-five push, alpha 4 | 30 | 0.03 | 0.97 | 0 | not computable |
| top-five push, alpha 8 | 30 | 0.00 | 0.07 | 0 | not computable |
| prompt top-five ban | 50 | 0.62 | 0.50 | 10 (DFS 10, banned) | not computable |

### 6.4.5 Who forecasts the landing

The landing contest scored, on the 21 recorded push-landing events, three forecasts: the base runner-up, the instruct twin's own most frequent algorithm other than the default (defined on 7 events), and the instruct twin's teacher-forced ranking of the catalogue's openings, the log-mean-exp likelihood of each algorithm's first 48 tokens over its reference and forced programs, which we call the opening ranking (Table 257). The base runner-up named 17 of 21 landings and the opening ranking 10. On the 9 events where they disagree the base runner-up wins 8:1 (exact one-sided sign test p 0.020), and its mean log score is higher by 1.62 nats (Wilcoxon p 0.032). Where the twin wrote an alternative, its own minority does as well as the base runner-up (6 of 7; log-score difference 0.02, p 0.69). The comparison is retrospective, because the landings were known when the rule was frozen, and the opening ranking rests on 1 to 6 programs per algorithm. The base model adds information beyond the instruct model's own ranking of openings; it does not add information beyond the twin's minority where one exists.

**Table 257.** The 21 recorded push-landing events: the landing and each forecast's top-1, with log scores (base runner-up / opening ranking / twin minority). Source: exchange and site experiment `results/landing_forecast.json`.

| Event | Landing | Base runner-up | Twin minority | Opening ranking | Log score base / opening / twin |
|-|-|-|-|-|-|
| Qwen3-8B 8-bit screen, kth smallest | quickselect | quickselect (hit) | n/a | quickselect (hit) | -1.36 / -1.67 / n/a |
| Qwen3-8B 8-bit screen, connected components | DFS | DFS (hit) | n/a | DFS (hit) | -0.84 / -0.78 / n/a |
| Qwen3-8B 8-bit screen, shortest path | Bellman-Ford/SPFA | Bellman-Ford/SPFA (hit) | n/a | Floyd-Warshall (miss) | -0.96 / -4.59 / n/a |
| Qwen3-8B 8-bit screen, two sum | brute force | brute force (hit) | n/a | brute force (hit) | -0.73 / -0.05 / n/a |
| Qwen3-8B 8-bit screen, grid | DFS | DFS (hit) | n/a | bidirectional BFS (miss) | -1.14 / -1.14 / n/a |
| Qwen3-8B bf16, kth smallest | size-k heap | quickselect (miss) | quickselect (miss) | quickselect (miss) | -1.50 / -2.64 / -1.50 |
| Qwen3-8B bf16, connected components | DFS | DFS (hit) | n/a | DFS (hit) | -0.73 / -0.05 / n/a |
| panel A, majority element | Boyer-Moore vote | Boyer-Moore vote (hit) | n/a | sort and take middle (miss) | -0.38 / -4.95 / n/a |
| panel A, trapped rain water | two pointers | two pointers (hit) | two pointers (hit) | monotonic stack (miss) | -0.33 / -4.38 / -0.14 |
| panel A, longest mirrored substring | brute force | brute force (hit) | n/a | brute force (hit) | -0.69 / -0.97 / n/a |
| panel B, single number | XOR fold | XOR fold (hit) | XOR fold (hit) | set-sum identity (miss) | -0.18 / -4.39 / -0.38 |
| panel B, minimum spanning tree weight | Prim with heap | Prim with heap (hit) | Prim with heap (hit) | Prim with heap (hit) | -0.44 / -0.05 / -0.15 |
| panel B, integer square root | linear scan | floating point sqrt (miss) | n/a | linear scan (hit) | -1.13 / -0.56 / n/a |
| panel B, count inversions | sorted insertion with bisect | sorted insertion with bisect (hit) | n/a | segment tree (miss) | -0.59 / -4.37 / n/a |
| Gemma, grid | BFS | BFS (hit) | BFS (hit) | bidirectional BFS (miss) | -0.42 / -4.53 / -0.23 |
| Gemma, kth smallest | size-k heap | quickselect (miss) | n/a | quickselect (miss) | -1.70 / -4.80 / n/a |
| Gemma, substring search | built-in find | built-in find (hit) | built-in find (hit) | built-in find (hit) | -0.13 / -0.05 / -0.50 |
| Gemma, two sum | brute force | brute force (hit) | n/a | brute force (hit) | -0.48 / -0.05 / n/a |
| Gemma, connected components | union find | BFS (miss) | n/a | BFS (miss) | -0.96 / -4.39 / n/a |
| Gemma, first and last position | binary search | binary search (hit) | binary search (hit) | exponential search (miss) | -0.12 / -4.38 / -0.38 |
| Gemma, longest increasing subsequence | quadratic DP | quadratic DP (hit) | n/a | quadratic DP (hit) | -0.06 / -0.04 / n/a |

Per set the base runner-up hit 5 of 5 on the 8-bit screen, 7 of 9 on the bf16 Qwen3-8B events and 5 of 7 in Gemma; the opening ranking hit 3 of 5, 4 of 9 and 3 of 7. Two correct programs labelled other appeared in the whole experiment, both catalogue variants. Judge spend was USD 0.055.

