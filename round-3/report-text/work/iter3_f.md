## 3.9 Comparisons across this iteration's experiments

**The same modal bench ban, drawn three times in Qwen3-8B and once in Llama.** Three Qwen3-8B artifacts sampled the modal bench bans with the five frozen templates and 20 samples each, on different engines: vLLM in bf16 (bench forecast experiment), HF in bf16 with common random numbers (bench route experiment, full ban arm) and HF with 8-bit linears (locus experiment, four bench tasks). Table 119 sets them side by side with Llama. With the wording fixed, avoidance replicates within a few points and the landing replicates in kind: the same five tasks pass the gate in both artifacts that ran all twelve, and every Qwen3-8B draw sends kth smallest to quickselect and size-k heap, two sum to brute force, find duplicate to index marking, connected components to BFS and merge intervals to a failing merge without sorting. Llama lands elsewhere on two of the shared tasks (two sum to sort and two pointers, connected components to DFS), on both of which Llama's own association answer matches its landing.

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

**One wording, everywhere.** The fourth template (`X is not allowed here`) is the weakest wording in every artifact that measured it: 197 of 240 banned programs against 85 to 135 for the other templates in the bench forecast experiment; pooled avoidance 0.19 against 0.42 to 0.62 in the bench route experiment, where it produced 29% of all ban failures; mean avoidance 0.81 against 0.93 to 0.96 in the exposure template arm; and in the locus experiment it kept the default in 20 of 20 bench samples and carried all 61 grid BFS programs under the ban, which is why every within-ban decoder there reduced to a template decoder. In Llama, dropping the fourth template alone flips the frozen branch from no family advancing to substitution. Wording is the largest measured source of variance in compliance, and any analysis that pools templates without modelling them pools different experiments.

**Signature vetoes, five times.** Every artifact that vetoed a default's distinctive n-gram found the default carried by more than its surface tokens: it survived every round on 9 of 12 bench tasks in the bench forecast experiment, Y re-emerged after three rounds for 25 of 33 shown algorithms in the exposure experiment, only one Llama default (the heap of top-k frequent) was removed, the one-shot veto's avoidance was at most 0.41 in the bench route experiment, and the token walk stalled on all six tasks of the reach experiment although the veto was exact. On both path tasks no veto variant moved the default at all, in Qwen3-8B or in Llama, while a single prompt ban moves them by 85 points. The subtraction forecast was therefore undefined on most events, and the test of whether a ban-free veto reproduces a ban's landing was undetermined everywhere it was planned.

**Three forecast contests.** Table 120 summarises the contests that decide the title claim, each under the same frozen rule. On the modal bans of either model, no family's forecast beats uniform by a decisive margin and no family advances once undefined forecasts are no longer counted as wins. On the exposure bans, where the default is still available, the ladder (that is, the default) wins: snap-back. Association is never better than the ban-free families in Qwen3-8B, and in Llama it ties them.

**Table 120.** The three forecast contests of iteration 3 (gated events; top-1 hit rates against the realised modal landing). Sources: bench forecast, exposure and Llama bench experiments.

| Contest | Gated events (disagreeing) | Frozen branch | Wins by 0.10 nats | Top-1 hit rates | Paired tests |
|-|-|-|-|-|-|
| Qwen3-8B modal bench bans | 5 (5) | SUBTRACTION/LADDER (LADDER); no family advances if undefined forecasts do not count | ladder 3 (2 as uniform), proximity 2 | ladder 1 of 5 and association 1 of 5 (both kth smallest), proximity 1 of 5 (two sum), subtraction 0 of 5 | not run (5 events); mean log score minus uniform: ladder +0.06, subtraction -0.69, proximity -1.53, association -1.78 |
| Qwen3-8B exposure bans, named | 31 (30) | SUBTRACTION/LADDER (LADDER) | ladder 7, subtraction 2, association 2, proximity 0 | ladder 0.77, proximity 0.61, association 0.45, subtraction 0.36 | ladder minus association +1.29 nats [0.10, 2.38], Holm 0.081; subtraction minus association +1.02 [0.35, 1.56], Holm 0.081 |
| Llama modal and present minor bench bans | 13 (11) | NO FAMILY ADVANCES (aimed, unresolved) | subtraction 1 (as uniform), association 1 | ladder 7 of 13, association 7 of 13 (binomial p 0.033 each), subtraction 4 of 12, proximity 3 of 13 | both ban-free families beat proximity (Holm 0.0088 and 0.0078); neither separates from association (p 0.52 and 0.77) |

[FIGURE:fig_forecast_hits]

## 3.10 What iteration 3 established, what it ruled out, and what it abandoned

Everything below is still one model per contest, at most 31 gated events per contest, and labels from labellers that passed their gates; the bench is memorised LeetCode material, and the path tasks are a screen that is never pooled.

**Established.**

1. *The likelihood substitution test of iteration 2 cannot decide the title claim.* Its gain and residual argmax hit the realised landing in 0 of 17 Qwen3-8B single bans (implied mass: 14 of 17), no row keeps three estimable survivors, the bootstrap variance of the mean gain is 2.7 times the noise term it subtracted, and a decision on mass would need about 50 programs per algorithm at the lower bound and 129 Qwen3-8B or 43 Llama events. "Not pure subtraction", "not aimed" and "no coherent ladder" are not detectable with that instrument.
2. *Shown a correct program of a non-default algorithm and told not to use it, Qwen3-8B snaps back to its default.* The default's share of attempts rises from 0.05 under the copy twin to 0.72 under the named ban and 0.82 under the unnamed one, the modal replacement is the default in 24 of 31 gated events, and the ladder forecast wins the frozen contest (7 wins; top-1 0.77). Naming the banned algorithm adds little beyond asking for something else (same modal replacement for 0.88 of Y).
3. *Where the default is not available, the landing is specific to the task and mostly unforeseen.* On the five gated Qwen3-8B modal bench bans, no ban-free or association forecast beats uniform on average, and three of five landings (index marking, BFS, a failing merge without sorting) were named by no family. In Llama the landing is predictable above chance (ladder and association 7 of 13 each), but the families do not separate.
4. *A ban's route is task dependent.* On the bench, pooled over five gated tasks, generated tokens reading the ban carry 0.74 of the effect and the prompt states 0.61, with a redundant mechanism on kth smallest and connected components, a direct one on two sum and find duplicate, and a superadditive one on merge intervals; a second draw reproduces every task. The prompt route story of the path tasks does not generalise.
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

- *The likelihood instrument (FRLP) as the decision instrument for where a ban sends the mass.* Closed by Table 82 (argmax 0 of 17 against the realised landing) and Table 84 (programs and events needed far beyond the budget).
- *Signature vetoes and the token walk as a way past the default.* Closed by the bench forecast, exposure, Llama, route and reach experiments: the default survives exact vetoes by renaming and respelling, and the walk stalled at rung 1 or 2 on all six tasks.
- *The shared prohibition direction.* Closed by Table 110.
- *Head ablation as a test of the attention heads.* Closed by the random-head control.
- *Qwen-Scope base SAEs for readouts of the ban.* They now pass a fairer transfer criterion (fraction of cross-entropy recovered 0.989 to 0.994), but their reconstructions keep only a cosine of about 0.3 of the ban displacement, and their latents never beat difference-in-means.
- *Long-form novelty instructions as a source of novel algorithms.* Closed by Table 118 and the audit (0 novel of 38 correct programs outside the catalogue).

## 3.11 What the next iteration takes from this one

The title claim of the update, that a ban removes the default and the model falls to a next rung that ban-free counterfactuals can read in advance, did not survive in that form. The part that survived is snap-back: with the default available, a ban on a shown algorithm returns the model to its default, which is subtraction in its simplest form. Where the default itself is banned, the counterfactuals meant to expose the next rung either fail to move the model (signature vetoes) or move it somewhere else (random pushes, the shared prohibition direction), and the landing is specific to the task in a way no frozen family foresaw in Qwen3-8B. Substitution by association is not supported in Qwen3-8B and is tied with the ladder in Llama. What decides the replacement under a modal ban remains open, and the run now has two concrete leads for it: the opening of the body, where the prefill sweep localises the ban to the first content token, and the template, which carries more of the variance in compliance than anything else measured.

Three things follow for the next iteration. First, the contest needs events on which the default is unavailable and the families disagree, in numbers the paired tests can use: the modal bench bans give 5 gated events in Qwen3-8B, so pooling with Llama (11) and adding bench tasks where bans take is the arithmetic, with the template entered as a random effect rather than pooled over. Second, the first body token is now a measured locus in behaviour; a decoder or patch there, in states saved at that position for each task, would ask what is decided when the ban gives way. Third, the generic perturbation rival needs a behavioural test where its runner-up and the associate differ, which the Qwen3-8B bench rarely provides; Llama's present minor events are where the named ban gained the associate +0.25 on two of six events, and that is the next place to look.

Request items still open: a same seed temperature arm with thinking on (dropped again), manifold placement of the walk landings (dropped; the walk stalled), and an SAE readout that keeps the ban displacement.

