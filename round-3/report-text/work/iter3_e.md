## 3.7 Locus experiment: a shared prohibition direction, a locus at generated tokens 1 to 8, the ban-attending heads, and SAE transfer (Qwen3-8B)

**Why.** Four questions about where a prohibition lives inside the model were open after iteration 2. Is there a task-general direction that carries "leave your default", and does writing it into a neutral prompt work like a named ban (the causal test of the read position correlation, moved to the positions where the route test located the effect)? Is the within-ban choice of algorithm decodable at generated tokens 1 to 8 beyond the written text? Do the three heads that attend to the banned name matter? Do the Qwen-Scope base model SAEs [50] transfer to the instruct model under a criterion that does not penalise its lower clean cross-entropy? This experiment [ARTIFACT:art_pVlCZ272hDV7] ran all four beside their controls under common random numbers, on the two path tasks and four bench tasks (kth smallest, substring search, find duplicate, two sum).

**Design.** The machine had a 16 GB RTX 2000 Ada, too small for bf16 weights, so every decoder linear layer was quantised at load time to 8-bit floating point with per-channel weight and per-token activation scales (embeddings, norms and the output head stayed bf16). A validation reproduced the iteration-2 shortest path arms (ban 2 of 20 Dijkstra, twin 20 of 20). The sampler coupled every arm exactly (identical uniforms in different rows give identical tokens at 20 rows per batch), and teacher forcing at batch 1 was bit exact. The shared prohibition direction v was the leave-one-task-out mean, over the 13 other tasks and all five templates, of the ban minus twin displacement at the task specification positions in blocks 12 to 23. The ADD arm wrote v into the neutral twin's prefill with the displacement targeted to alpha times the ban's own per-layer norm (alpha in {1, 2}, plus 0.5 on some tasks); the SUBTRACT arm projected v out of the ban prompt's prefill. Controls were three random directions with the same blocks, positions and norms, the twin, and the named ban (N = 100). In all, 5,500 samples followed the frozen design and 1,800 were exploratory. Decision rules were hash committed before sampling.

**The direction exists, but adding it is no better than a random push.** The leave-one-task-out v was reliable (split half cosine 0.95 to 0.99 across blocks 12 to 23) and aligned with every held-out task's mean ban displacement (cosine 0.29 to 0.86 at block 18, against a 95th percentile of 0.03 for random directions), yet it carried only 2% to 6% of each position's own ban displacement. The preregistered test failed on every gated task (Table 110): ADD beat every random control on 0 of 5 gated tasks, and its avoidance was not above the maximum of the three random directions on 5 of 6 tasks. Where ADD moved behaviour it did not reproduce the ban. On kth smallest it landed on a size-k heap while the ban landed on quickselect (Jensen-Shannon divergence 0.52 against a permutation 95th percentile of 0.03; the committed forecast missed); on the shortest path task ADD and the ban both landed on Bellman-Ford/SPFA, but so did the random directions that moved it. The dose response was not monotone (shortest path avoidance 0.02, 0.35 and 0.12 at alpha 0.5, 1 and 2 over all slots), and the random edits grew more than v downstream (block 35: about 283 against 219 on the shortest path task), so a weak control does not explain the result. SUBTRACT never restored the default: pooled over the gated tasks the banned share changed by -0.026 [-0.07, 0.03] against a required +0.3, and on substring search, find duplicate and two sum removing v made the ban slightly stronger. On the path tasks neither plain nor affine subtraction exceeded a random edit of the same norm by the required 0.15, and that random edit was destructive (pass rate 0.00).

**Table 110.** The shared prohibition direction against matched random directions (avoidance; slots 0 to 9 for ADD and random arms). Source: locus experiment `results/c2d.json`.

| Task (default) | Named ban avoidance and landing | ADD, alpha 1 / 2 | Random directions, alpha 1 (three seeds) | SUBTRACT: change in banned share [95% CI] |
|-|-|-|-|-|
| Shortest path (Dijkstra) | 0.88, to Bellman-Ford/SPFA | 0.44 / 0.12 | 0.06, 0.50, 0.34 | +0.07 [-0.02, 0.17] |
| Grid (BFS) | 0.87, to DFS (all 13 BFS under the fourth template) | 0.06 / 0.04 | 0.04, 0.00, 0.02 | -0.05 [-0.11, 0.00] |
| kth smallest (full sort) | 1.00, to quickselect 79, size-k heap 21 | 0.80 / 0.70 | 0.24, 0.70, 0.36 | 0.00 (no default to restore) |
| substring search (naive) | 0.49, to KMP (fails the gate) | 0.00 / 0.00 | 0.00, 0.00, 0.00 | -0.12 [-0.22, -0.02] |
| find duplicate (hash set) | 0.74, to index marking | 0.00 / 0.00 | 0.00, 0.00, 0.00 | -0.06 [-0.11, -0.02] |
| two sum (hash map) | 0.80, to brute force | 0.00 / 0.00 | 0.00, 0.10, 0.00 | -0.09 [-0.15, -0.04] |

With 12 more random directions (15 in all, alpha 1, exploratory), ADD exceeded all 15 on kth smallest (0.80 against a maximum of 0.70 and a mean of 0.24) but landed on the wrong algorithm, sat at the 80th percentile on the shortest path task (3 of 15 random directions moved it more; random mean 0.20), and was indistinguishable from random on the grid task (0.06 against a mean of 0.07). Writing the shared component of the ban displacement into a neutral prompt is a direction-specific push on one task and a generic one elsewhere, and removing it is not necessary for the ban.

**No within-ban locus at generated tokens 1 to 16 (Table 111).** Decoders of default against other were fitted on batch-1 teacher forced states (blocks 8 to 28; the task specification mean, the read position and generated tokens 1 to 8 and 16), against 500 within-template permutations for the path tasks and 200 for the bench tasks with a maximum over layers, and against three written text controls of matched or greater capacity (token one-hots, layer-0 embeddings reduced to 64 principal components, exact prefix match). No decoder passed the rule on any testable task. On the grid task and three bench tasks the class is set by the template: under the fourth template the model keeps the default in 20 of 20 bench samples and writes all 61 grid BFS programs, so every decoder (state, read position, text) reaches the template-only accuracy and none exceeds it. On the shortest path task the default is spread over templates (2, 0, 4, 3 and 3 of 20) and the choice is made inside the program: the first token at which the two classes diverge comes at a median of about 29 generated tokens, after the frozen window, and neither state nor text decodes the choice within tokens 1 to 16. The committed prediction of a fork at the import line (tokens 3 to 5) was wrong for this sample. At batch 1, identical prefixes gave bit-identical states (maximum difference 0 over 89 to 95 pairs per position), so a state at position k is a function of the written prefix.

**Table 111.** Within-ban decoders of the algorithm written (default against other) on batch-1 teacher forced states. BA is balanced accuracy. Source: locus experiment `results/c2e.json`.

| Task | Programs (default / other) | Largest state BA, tokens 1 to 8 | Best of read position and text controls at token 8 | Locus |
|-|-|-|-|-|
| Shortest path | 100 (12 / 88) | 0.53 rising to 0.63, never above the null 95th percentile (about 0.60 to 0.70) | 0.55 | none |
| Grid (with a fourth-template top-up) | 160 (61 / 99) | 0.904 at every k | 0.904 (template only) | none |
| substring search | 100 (51 / 49) | 0.832 at every k | 0.832 (template only) | none |
| find duplicate | 100 (26 / 74) | 0.88 at every k | 0.88 (template only) | none |
| two sum | 100 (20 / 80) | 1.00 at every k | 1.00 (template only) | none |
| kth smallest | 100 (0 / 100) | not testable (no default under the ban) | | |

A secondary test pooled the archived ban pools of the route and readout experiments (200 rows per path task): the shortest path state reached balanced accuracy 0.78 to 0.79 at tokens 4 to 8 against 0.75 for the template-only decoder, a margin of 0.03 to 0.05, below the 0.10 rule. The first run on states extracted in 20-row batches, where 8-bit matrix tiling made identical prefixes differ by 4% to 8%, gave the same verdict on every task. An exploratory extension to tokens 24 to 96 found text matching or beating the state on the grid and substring search tasks; on the shortest path task the state curve was noisy (0.57, 0.66, 0.45, 0.50 and 0.75 at tokens 24, 32, 48, 64 and 96), and only token 96 cleared both the null (0.66) and the text controls (at most 0.60), a single unreplicated point with 12 minority samples.

**The ban-attending heads are not special.** Mean ablation of layer 21 head 17 and layer 26 heads 21 and 25 at generated positions under the full ban raised the grid BFS share from 0.12 (the ban, same slots) to 0.24, but every set of three random heads in the same layers raised it to 0.18: the difference is +0.06 (90% interval [0.02, 0.12]; exact paired p = 0.125 against each random set), short of the required 0.15. The shortest path task was unchanged (-0.03 [-0.07, 0.03]). Almost all the grid movement sat in the fourth template, which carries every BFS under the ban: BFS went from 6 of 10 to 10 of 10 under the target heads and 9 of 10 under each random set. The fourth-template ban is fragile to any small perturbation of layers 21 and 26.

**Under a fairer criterion the base SAEs pass, but they lose most of the ban displacement.** The iteration-2 transfer test compared increases in cross-entropy, which penalises the instruct model for its lower clean cross-entropy (0.030 against 0.260 nats). This experiment scored each model on its own text in a two by two design (model by text source, 100 sequences each) by the fraction of cross-entropy recovered relative to zero ablation, FR_zero (Table 112). The frozen rule, FR_zero of the instruct model on its own text at least 0.9 times the base model's, passed at layers 15, 20 and 27. As the plan had computed, the zero-ablation denominator of 12 to 15 nats makes this rule lenient, and a placebo that swaps the SAE and zero-ablation cross-entropy per sequence drives FR_zero to about 0 yet still passes the 0.9 rule at layer 20; the values themselves (about 0.99 against about 0 on the placebo) carry the information. Stricter companions: the fraction recovered relative to mean ablation passed the same rule at all three layers; the ratio of cross-entropy increases on own text (instruct over base) was 1.68, 1.30 and 0.76 at layers 15, 20 and 27 (iteration 2, one shared corpus in bf16: 3.29, 1.95, 1.59). The task-relevant test fails: the SAE reconstructions keep only about a third of the direction of the ban minus twin displacement at the task specification positions (cosine 0.27, 0.30 and 0.32 at layers 15, 20 and 27; norm ratio 0.65 to 0.79), so what the ban changes in the residual stream is largely lost in reconstruction error. This agrees with the transfer study of Kissane and colleagues for most model pairs, and it means that latent-level claims about the ban should not rest on these SAEs.

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

**Why.** The update's third claim was that prompts move the model exactly one rung. This experiment [ARTIFACT:art_ccAbfJVcv0LO] asked three things: whether cumulative token vetoes, an operation the model cannot ignore, reach algorithms that prompt bans cannot (we call this the *token walk*: veto the default's distinctive n-gram, then the next landing's, and so on, up to five algorithms); whether a ban that leaves exactly one survivor gets that survivor written whenever the model can write it on request (we call the share of programs implementing the survivor *will*, and the share of forced programs labelled as the requested algorithm and correct *can*); and whether the request's own long-form novelty instruction produces a correct novel algorithm. Six tasks ran: the two path tasks in bf16, and kth smallest, substring search, find duplicate and connected components on the official 8-bit checkpoint at which their iteration-2 references were made. Every mask, forecast and protocol was hash committed before the samples it governs.

**The token walk stalls at the default (Table 114).** The persistent veto, implemented as a vLLM logits processor, was exact: no banned token sequence occurred in any of 1,450 vetoed generations. The algorithm came back anyway. On the grid task `current_row` and `current_col` replaced `r, c` in 63% of re-emerged BFS programs (7% in references); on the shortest path task `current_distinct` and `d` replaced `current_dist`; vetoed strings leaked through non-canonical spellings (up to 0.86 of samples on connected components and 0.80 on find duplicate at step 2); and the grid code degenerated into near-miss syntax (`queue popleft()`, 66% to 86% invalid). Imports and calls barely changed: the rerouting is lexical, not algorithmic. Only find duplicate moved one rung, to sort and adjacent check, the same single-rung move that prompt bans produce. A sham veto of an algorithm-generic n-gram of matched length and presence kept the default (grid 50 of 50 with `' start == goal:\n'`, shortest path 50 of 50 with `' u, v, w'`, substring search 49 of 50 with `' len'`, connected components 44 of 44 valid with `' range'`), while the distinctive veto cut correctness the sham did not (shortest path pass rate 0.41 against 1.00, Newcombe difference 0.59 [0.43, 0.72]; grid 0.76 against 0.96). A fixed veto of the distinctive n-grams of BFS, DFS, IDDFS and A* at once, the request's top-five prohibition asked as an operation, left BFS 13, DFS 2 and 35 invalid programs on the grid task after two extra rounds; the prompt version gave avoidance 0.00 (Section 2.6). Neither knob reaches the rest of the catalogue.

**Table 114.** The token walk under the neutral twins (no ban text; N = 50 per round, 10 per template). Source: reach experiment `results/walk.json`, `README.md`.

| Task | Step 0 (no veto) | Vetoed n-grams, by round | Final round of the last step | Status |
|-|-|-|-|-|
| Grid (bf16) | BFS 50 | `' c, path = queue.p'`, then `' queue.append(start'`, then `'None for'` | BFS 6, DFS 1, invalid 43 | stalled at step 1 |
| Shortest path (bf16) | Dijkstra 50 | `' heap = [(0, s'`, then `' current_dist,'`, then `' dist[u]:\n'` | Dijkstra 27, invalid 23 (pass 0.30) | stalled at step 1 |
| kth smallest (8-bit) | full sort 45, quickselect 5 | `' nums.sort'`, then `'_sorted'`, then `' sorted(nums'` | full sort 23, counting sort 10, quickselect 6, invalid 10 | stalled at step 1 |
| substring search (8-bit) | naive 50 | `'+len'`, then `'[i:i +'`, then a leak span | naive 50 | stalled at step 1 |
| find duplicate (8-bit) | hash set 50 | `' set'`, `' seen'` and leak spans; then, at rung 2 (sort and adjacent check, 37 of 50), `'.sort'` and 5 leak spans | sort and adjacent check 20, other 13, hash set 10 | stalled at step 2 |
| connected components (8-bit) | union find 47, DFS 3 | `' parent'` and 8 leak spans (`(parent`, `parents`, `.parent`, tab-indented `parent`, and others) | union find 44, DFS 6 | stalled at step 1 |

**Prompts reach further than one rung on two tasks (Tables 115 and 116).** The preregistered reach claim was that will is at most 0.10 at every rung of 3 or more where can is at least 0.7, and it is disconfirmed by a will of 0.30 or more. It was disconfirmed on connected components, where the list that leaves only BFS got BFS 50 of 50, and on kth smallest, where the list that leaves only quickselect got quickselect 50 of 50. Both cells reached "rung 3 or more" through the flagged fallback, because the walk stalled at step 1 and the fallback set the second rung (counting sort on kth smallest, DFS on connected components). A post hoc sensitivity that sets the second rung to the association answer keeps connected components disconfirming (association says DFS, so BFS stays at rung 3 or more) and moves quickselect to rung 2. On connected components the two traversals are interchangeable alternatives (BFS 50 of 50 when only BFS is allowed, DFS 49 of 50 when only DFS is), so a single chain of rungs does not describe the repertoire. The claim was confirmed on the shortest path task (Floyd-Warshall, from Section 2.6), on two kth smallest cells and on find duplicate's binary search on values; find duplicate's Floyd cycle detection reached 0.14; substring search had no rung of 3 or more with can of at least 0.7.

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

Quickselect is kth smallest's universal answer to a ban list: every list that bans the full sort yields quickselect in 44 to 50 of 50 programs, including the lists that ban quickselect itself (only size-k heap allowed, only heapify and pop allowed: 50 of 50 quickselect, disguised in 0% to 8%). The sanity check of the list that leaves only the default gave will 1.00 on substring search, 0.86 on find duplicate and 0.94 on connected components, but 0.00 on kth smallest: with the prompt "Do not use a size-k heap, heapify-and-pop, quickselect, median of medians or counting sort for this task.", all 50 programs implemented quickselect, 48 of them in a function named `quickselect`, while full sort was 45 of 50 under the twin. This is the starkest priming by a negative constraint in the run [7, 53]. Forced can underestimates some algorithms: find duplicate's index marking has a forced adherence of 0.03, yet the model wrote it in 34 to 40 of 50 programs under lists that forbid it, always disguised. The preregistered list independence test (the default's share among default and second-rung programs is the same across lists that ban both) failed on substring search (0.82 under the Rabin-Karp list against 0.98 under the built-in list; permutation chi-squared p = 0.033; largest difference 0.16 [0.04, 0.30]; placebos with shuffled membership gave p = 0.61, 0.56 and 0.06), was descriptive on find duplicate, and was not testable on kth smallest and connected components.

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

**The long-form novelty instruction produces claims of novelty, not new algorithms (Table 118).** The request's two instructions ("Make a new algorithm" and "Make a fully novel algorithm never seen before", each with a design rationale of about 2,000 words before the code) were run with thinking off (N = 25 to 50 per cell) and on (N = 10 per prompt and task, 16k thinking cap; 100 of 100 traces completed, 4.1k to 12.4k thinking tokens). Of 574 outputs with a claim record, 484 (84%) claimed a new algorithm; 189 of those (39%) contained no code at all, only a rationale of 1,300 to 1,700 words; of the 295 with code, 220 (75%) were catalogue algorithms by the mechanism labeller, with names such as "Modified Bellman-Ford", "BFS with Dynamic Programming" and "Optimized Dijkstra with Early Termination". The instructions do diversify the output (correct-only Hill numbers of 1.8 to 4.5 in the thinking-off cells, against a collapsed baseline), at a cost in correctness (pass rates of 0.33 to 0.44 on the grid task and 0.32 to 0.37 on find duplicate). With thinking on, the code stayed in the catalogue (grid mostly DFS, 13 of 20; shortest path Bellman-Ford/SPFA, Dijkstra and Floyd-Warshall only; kth smallest counting sort 13 of 20; substring search naive 14 of 20; find duplicate off-catalogue 11 of 20, all failing arithmetic tricks that assume one duplicate). A bf16 against 8-bit cross-check on the shortest path task under the first instruction gave a label composition Jensen-Shannon divergence of 0.033 bits against a null 95th percentile of 0.068 (p = 0.35).

**Table 118.** Long-form novelty instructions: composition of outputs per cell (first instruction "Make a new algorithm"; second "Make a fully novel algorithm never seen before"). Source: reach experiment `results/longform.json`, `README.md`.

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

