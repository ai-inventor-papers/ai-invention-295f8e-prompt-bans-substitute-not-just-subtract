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

