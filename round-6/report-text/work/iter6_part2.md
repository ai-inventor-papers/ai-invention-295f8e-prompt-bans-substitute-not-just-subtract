## 6.3 The engine control: are the random-push escapes a property of the model or of FP8 rounding?

**Why.** The engine claim was the primary test of the iteration, because its answer decides which internal results of iteration 4 belong to Qwen3-8B. The review had pointed at a plausible mechanism without establishing it: a displacement changes the per-token absmax of each linear input, so under dynamic per-token FP8 scaling it changes the rounding of every downstream activation, and the engine adds its own perturbation to the push. The FP8 formats in question are e4m3 values with a maximum of 448 [115]. The engine control [ARTIFACT:art_lpQalcAXMGr1] separated weight rounding from activation rounding by running iteration 4's own design under four numerics, all built from one bf16 snapshot of Qwen3-8B (Table 235).

**Table 235.** The four numerics of the engine control.

| Engine | Weights | Activations | Role |
|-|-|-|-|
| W8A8 | e4m3, per-output-channel absmax / 448 | e4m3, per-token absmax / 448 | iteration 4's engine (native FP8 matrix multiply) |
| W8A16 | e4m3, the same codes | bf16 | weight rounding only |
| W16A8 | bf16 | e4m3, fake-quantised per token | activation rounding only |
| bf16 | bf16 | bf16 | full-precision reference |

**Design.** Everything except the numerics was held fixed: iteration 4's 40 direction files (seeds 9101 to 9140, checked bitwise), the absolute displacement per block and position at blocks 12 to 23 and the task-specification positions (iteration 4's bench unit), the twin prompts, the common-random-number slots and uniforms, the stop rule, a 1,024-token cap, one labeller version (iteration 4's plus the iteration-5 re-gate that reads array-based Dijkstra correctly) applied to every row, and iteration 4's two-stage escape rule, with each engine scored against its own twin. The W8A8 engine first regenerated iteration 4's rows on the same GPU model, driver and library versions: 400 of 400 programs of the plan-subspace experiment and 40 of 40 per-sample plan-noise programs came out byte-identical, the realised downstream displacement had ratio 1.000, and per-slot label agreement was 1.0. Under the reuse rule committed before sampling, iteration 4's own rows therefore stand in for the W8A8 engine on every other cell. The bf16 twins reproduce iteration 5's bf16 twin composition (connected components union find 50 of 50; shortest path Dijkstra 49, Bellman-Ford/SPFA 1). The control ran at alpha 2 on connected components and shortest path; the alpha-1 arms of the two single-factor engines, a Gaussian mimic of the 8-bit noise and kth smallest were dropped by the committed drop order, and the W8A16 engine ran on a slower cast path because the fused kernel could not be compiled.

**bf16 escapes on almost the same directions.** At the same absolute displacement the bf16 engine escapes on 26 of 40 directions on connected components and 6 of 40 on shortest path, against 29 and 8 under W8A8 (Table 236). The direction-level discordance is 3:0 and 4:2 (exact McNemar p 0.25 and 0.69), the per-direction off-default shares rank alike (Spearman 0.96 and 0.87; kappa on escape 0.83 and 0.48), and permuting the pairing of directions drops kappa to about 0. The committed verdict is NOT_REPRODUCED_HIGH on both tasks: W8A8 minus bf16 is below 0.1, so the FP8-specific account is not reproduced. The low escape fraction on shortest path is a pass-rate effect common to both engines: in each, 17 of 40 directions reach the +0.20 off-default excess but fail the pass clause, because the pushed Bellman-Ford/SPFA programs often fail the hidden tests.

**Table 236.** Escape fraction at alpha 2 over 40 directions, each engine against its own twin (Wilson 95% intervals). Source: engine control `results/escape_by_engine.json`.

| Task | Engine | Twin off-default (k/n) | Twin pass | Screen passes | Confirmed escapes | Escape fraction [95%] | Screen-level escape fraction |
|-|-|-|-|-|-|-|-|
| connected components | W8A8 | 0/50 | 1.00 | 30/40 | 29 | 0.725 [0.57, 0.84] | 0.750 |
| connected components | W8A16 | 0/50 | 1.00 | 28/40 | 27 | incomplete (confirmation rows short of 30 for all 28 screen passers) | 0.700 |
| connected components | W16A8 | 0/50 | 1.00 | 27/40 | 24 | 0.600 [0.45, 0.74] | 0.675 |
| connected components | bf16 | 0/50 | 1.00 | 27/40 | 26 | 0.650 [0.50, 0.78] | 0.675 |
| shortest path | W8A8 | 0/50 | 1.00 | 15/40 | 8 | 0.200 [0.10, 0.35] | 0.375 |
| shortest path | W8A16 | 1/50 | 0.98 | 8/40 | 5 | 0.125 [0.05, 0.26] | 0.200 |
| shortest path | W16A8 | 1/50 | 1.00 | 8/40 | 6 | 0.150 [0.07, 0.29] | 0.200 |
| shortest path | bf16 | 1/50 | 0.98 | 9/40 | 6 | 0.150 [0.07, 0.29] | 0.225 |

**Table 237.** Direction-paired contrasts of confirmed escapes (exact McNemar, Tango 90% interval, equivalence test at a margin of 0.1, kappa, and Spearman of the first-10 off-default shares). Source: engine control `results/mcnemar.json`.

| Task | Pair | First escape fraction | Second escape fraction | Difference | Directions escaping under first only / second only | Two-sided p (Holm) | 90% CI | Equivalent within 0.1 | Kappa | Spearman of shares |
|-|-|-|-|-|-|-|-|-|-|-|
| connected components | W8A8 vs bf16 | 0.725 | 0.650 | 0.075 | 3 / 0 | 0.250 (1.000) | [0.01, 0.17] | no | 0.83 | 0.96 |
| connected components | W16A8 vs bf16 | 0.600 | 0.650 | -0.050 | 1 / 3 | 0.625 (1.000) | [-0.15, 0.04] | no | 0.79 | 0.96 |
| connected components | W8A8 vs W16A8 | 0.725 | 0.600 | 0.125 | 5 / 0 | 0.062 | [0.05, 0.24] | no | 0.73 | 0.95 |
| shortest path | W8A8 vs bf16 | 0.200 | 0.150 | 0.050 | 4 / 2 | 0.688 (1.000) | [-0.06, 0.17] | no | 0.48 | 0.87 |
| shortest path | W16A8 vs bf16 | 0.150 | 0.150 | 0.000 | 2 / 2 | 1.000 (1.000) | [-0.10, 0.10] | yes | 0.61 | 0.90 |
| shortest path | W8A16 vs bf16 | 0.125 | 0.150 | -0.025 | 0 / 1 | 1.000 (1.000) | [-0.10, 0.04] | no | 0.89 | 0.83 |
| shortest path | W8A8 vs W16A8 | 0.200 | 0.150 | 0.050 | 4 / 2 | 0.688 | [-0.06, 0.17] | no | 0.48 | 0.81 |
| shortest path | W8A8 vs W8A16 | 0.200 | 0.125 | 0.075 | 5 / 2 | 0.453 | [-0.04, 0.20] | no | 0.36 | 0.91 |

**Per-sample plan noise reproduces in bf16 at the matched unit.** On iteration 4's own slots, uniforms and per-sample direction seeds, at the same absolute unit, bf16 plan noise moves connected components in 25 of 50 valid attempts at alpha 2 and shortest path in 22 of 50, against 30 and 22 under W8A8 (Table 238). The realised displacement at block 12, the first edited block, is 13.75 in the bf16 rows at alpha 2 and 13.76 in iteration 4's rows. Iteration 5's bf16 plan noise had moved connected components in 1 of 50 programs at alpha 1 and at alpha 2 on the same prompts and uniforms, but at the ban-free unit and with other direction seeds. The size of the push alone does not explain that null: iteration 5's alpha-2 displacement at block 12 (9.07) exceeds this control's bf16 alpha-1 displacement (6.88), which still moves 7 of 50. The difference lies in the ban-free unit's profile over positions and blocks, or in the direction seeds; which of the two matters was not tested.

**Table 238.** Per-sample plan noise per engine on iteration 4's slots at the absolute unit (valid attempts off the default over 50). Source: engine control `results/pn.json`.

| Task | Arm | Iteration-4 8-bit rows | W8A8 | W8A16 | W16A8 | bf16 | Paired discordance W8A8 : bf16 |
|-|-|-|-|-|-|-|-|
| connected components | alpha 1 | 6/50 (0.12) | 6/50 (0.12) | 9/50 (0.18) | 4/50 (0.08) | 7/50 (0.14) | 1:2 |
| connected components | alpha 2 | 30/50 (0.60) | 30/50 (0.60) | 27/50 (0.54) | 22/50 (0.44) | 25/50 (0.50) | 6:1 (p 0.13) |
| shortest path | alpha 1 | 12/50 (0.24) | 12/50 (0.24) | 11/50 (0.22) | 11/50 (0.22) | 10/50 (0.20) | 4:2 |
| shortest path | alpha 2 | 22/50 (0.44) | 22/50 (0.44) | 19/50 (0.38) | 18/50 (0.36) | 22/50 (0.44) | 8:8 |

[FIGURE:fig_engine_escape]

**FP8 adds a small boost on connected components, and activation rounding is not its source.** Pairing every pushed sample with the same slot (direction, template, slot index and uniforms) in the other engine, on the 400 screen slots of the first two samples of all 40 directions, W8A8 is off the default in 58.3% of slots against 53.2% under bf16 on connected components (discordant 30:10, exact McNemar p 0.0022), and 43.2% against 40.7% on shortest path (55:45, p 0.37) (Table 239). The factorial locates the boost. Activation rounding alone (W16A8) sits slightly below bf16 on connected components (49.7% against 53.2%, 9:23, p 0.02); weight rounding alone (W8A16) sits between bf16 and W8A8 (55.6%; 17:7 against bf16, p 0.06). The small boost therefore comes from the e4m3 weights, from the native kernel's reduced-precision accumulation (it matches an exact fp64 reference on 94.2% of outputs, against 99.96% for an exact emulation), or from their interaction. The landing algorithms do not change: correct off-default programs are DFS, then BFS, on connected components and Bellman-Ford/SPFA on shortest path under every engine, with compositions compatible across engines (permutation chi-squared p 0.22 and 0.94; Table 240).

**Table 239.** Common-random-number pairs of screen slots under the alpha-2 pushes: off-default share under each engine, discordant slots and exact McNemar p. Source: engine control `results/slot_flips.json`.

| Task | Pair | Slots | Off-default, first | Off-default, second | Discordant first : second | Exact p | Same label |
|-|-|-|-|-|-|-|-|
| connected components | W8A8 vs bf16 | 400 | 0.583 | 0.532 | 30:10 | 0.0022 | 0.873 |
| connected components | W16A8 vs bf16 | 400 | 0.497 | 0.532 | 9:23 | 0.02 | 0.900 |
| connected components | W8A16 vs bf16 | 399 | 0.556 | 0.531 | 17:7 | 0.064 | 0.925 |
| connected components | W8A8 vs W16A8 | 400 | 0.583 | 0.497 | 45:11 | 5.4e-06 | 0.825 |
| connected components | W8A8 vs W8A16 | 399 | 0.581 | 0.556 | 20:10 | 0.099 | 0.895 |
| shortest path | W8A8 vs bf16 | 400 | 0.432 | 0.407 | 55:45 | 0.37 | 0.740 |
| shortest path | W16A8 vs bf16 | 400 | 0.420 | 0.407 | 35:30 | 0.62 | 0.830 |
| shortest path | W8A16 vs bf16 | 400 | 0.390 | 0.407 | 38:45 | 0.51 | 0.782 |
| shortest path | W8A8 vs W16A8 | 400 | 0.432 | 0.420 | 57:52 | 0.70 | 0.723 |
| shortest path | W8A8 vs W8A16 | 400 | 0.432 | 0.390 | 47:30 | 0.068 | 0.805 |

**Table 240.** Composition of correct off-default programs under every alpha-2 push, per engine. Source: engine control `results/landings.json`.

| Task | W8A8 | W8A16 | W16A8 | bf16 |
|-|-|-|-|-|
| connected components | DFS 502, BFS 110 | DFS 410, BFS 86 | DFS 406, BFS 67 | DFS 448, BFS 82 |
| shortest path | Bellman-Ford/SPFA 165, Floyd-Warshall 1, other 1 | Bellman-Ford/SPFA 137, Floyd-Warshall 2 | Bellman-Ford/SPFA 129, other 1 | Bellman-Ford/SPFA 120, Floyd-Warshall 1, other 1 |

**Mechanism diagnostics.** Per-token e4m3 rounding perturbs every linear input by about 2.5% RMS. Under an alpha-2 push, the push-induced difference in rounding error is 6% to 12% of the push-induced change in activation (median over blocks 13 to 35 per site, peaking at 34% at the block-14 attention input), and 70% to 100% of the rows the push moves receive a new per-token scale. Linear inputs at blocks 0 to 12 are bitwise identical in the pushed and the twin pass in every engine, as the edit site requires. The extra rounding barely changes how the push propagates: relative to bf16, the non-nominal part of the perturbation is 1.01 at the task-specification positions, 1.04 to 1.05 at the read position and 1.03 to 1.12 at generated tokens 1 to 32 under W16A8, and 0.995 to 1.006 under W8A16. Teacher-forced on 40 iteration-4 twin programs, every engine is very close to bf16 (Table 241). One preregistered fidelity check failed uninformatively: teacher forcing runs one long prefill instead of 20-row decode steps, which itself changes the numerics, so log probabilities of iteration 4's programs could not be matched closely enough to resolve engines at that level; the engine was validated instead by byte identity.

**Table 241.** Teacher-forced divergence from bf16 on 40 iteration-4 twin programs, and the failed fidelity check (median absolute difference of a program's summed log probability from iteration 4's record). Source: engine control `results/diagnostics_summary.json`.

| Engine | Task | Mean per-token KL to bf16 (nats) | Argmax disagreement with bf16 | Median absolute log-probability difference |
|-|-|-|-|-|
| W8A8 | connected components | 0.0036 | 0.0012 | 0.477 |
| W8A8 | shortest path | 0.0015 | 0.0003 | 0.450 |
| W8A16 | connected components | 0.0019 | 0.0000 | 0.315 |
| W8A16 | shortest path | 0.0005 | 0.0003 | 0.703 |
| W16A8 | connected components | 0.0017 | 0.0019 | 0.448 |
| W16A8 | shortest path | 0.0011 | 0.0021 | 0.912 |
| bf16 | connected components | n/a | n/a | 0.383 |
| bf16 | shortest path | n/a | n/a | 0.679 |

**What it changes.** Table 242 assigns each earlier internal result to the numerics class that reproduces it. The 40-direction escape fractions, the per-sample plan-noise rates and the positive-control direction 9004 of the frozen screen are model properties. Only the per-slot off-default rate on connected components carries a significant 8-bit boost, of about 5 points. Iteration 5's bf16 plan-noise null and its finding that the shortest path task stops being movable in bf16 are not reproduced at the absolute unit; they belong to that design's unit and seeds. The plan-subspace claims of iteration 4 (the projection predictor, the targeted runner-up pushes, the decomposition) and the site and same-seed claims were not rerun here.

**Table 242.** Earlier internal results and the numerics class that reproduces them. Source: engine control `results/relabel_table.json`.

| Earlier result | Class | Deciding cells |
|-|-|-|
| 40-direction escape fraction, connected components, alpha 2 (iteration 4: 0.725) | model | escape fraction W8A8 0.725, W8A16 incomplete (screen level 0.70), W16A8 0.60, bf16 0.65 |
| Per-sample plan noise, connected components, alpha 1 (iteration 4: 6/50) | model | shares 0.12, 0.18, 0.08, 0.14 |
| Per-sample plan noise, connected components, alpha 2 (iteration 4: 30/50) | model | shares 0.60, 0.54, 0.44, 0.50 |
| 40-direction escape fraction, shortest path, alpha 2 (iteration 4: 0.200) | model | escape fraction 0.200, 0.125, 0.15, 0.15 |
| Per-sample plan noise, shortest path, alpha 1 (iteration 4: 12/50) | model | shares 0.24, 0.22, 0.22, 0.20 |
| Per-sample plan noise, shortest path, alpha 2 (iteration 4: 22/50) | model | shares 0.44, 0.38, 0.36, 0.44 |
| Frozen-screen direction 9004 moves shortest path at alpha 1 | model | first-10 off-default share W8A16 0.3, W16A8 0.4, bf16 0.3 |
| Per-slot off-default rate under alpha-2 pushes, connected components | model plus a small 8-bit boost | W8A8 0.583 against bf16 0.532; discordant 30:10, p 0.0022 |
| Per-slot off-default rate under alpha-2 pushes, shortest path | model | W8A8 0.432 against bf16 0.407; 55:45, p 0.37 |
| Iteration 5's bf16 plan-noise null on connected components (1/50 at the ban-free unit; block-12 dose 0.66 of this unit) | unit and seeds, not reproduced at the absolute unit | bf16 25/50 and W8A8 30/50 at alpha 2 |
| Iteration 5: shortest path loses 'movable' in bf16 | not reproduced at the absolute unit | bf16 escape fraction 6/40 confirmed escapes |
| Site odds ratio 5.72 | untested here | not rerun in this artifact |
| Same-seed agreement 17.25 of 20 | untested here | not rerun |
| Plan-subspace projection predictor | untested here | not rerun |
| Targeted runner-up pushes | untested here | not rerun |
| Decomposition into subspace and orthogonal parts | untested here | not rerun |

**Novelty and checks.** The two-judge novelty audit was replaced by a nearest-known-solution pass over all ten datasets of the declared source data (18,237 code solutions); Table 243 classes every distinct correct off-default or other program by its largest token-shingle Jaccard to a known solution. CPU gates checked the directions bitwise, the slots and seeds, the escape code (it reproduces iteration 4's escape file exactly) and the logged displacement (within 0.074% on all 1,770 iteration-4 prefills); the relabelling with the re-gated shortest path rule changed 18 iteration-4 labels and no escape fraction. GPU unit tests confirmed bitwise e4m3 codes, a bitwise twin at alpha 0, rerun identity, batch invariance for three rows or more and an exact match of the memory-capped sampler. A stdlib re-derivation and a separate audit from raw rows matched every headline, and a placebo that swaps engine labels was not significant. Judge spend was USD 0.085.

**Table 243.** Nearest known solution of the correct off-default and other programs per engine (distinct programs; median largest Jaccard; classes by Jaccard band). Source: engine control `results/known_solutions.json`.

| Engine and task | Distinct programs | Median largest Jaccard | Variant | Distant | Known, close |
|-|-|-|-|-|-|
| W8A8, connected components | 229 | 0.297 | 162 | 64 | 3 |
| W8A8, shortest path | 237 | 0.209 | 25 | 212 | 0 |
| W8A16, connected components | 186 | 0.291 | 137 | 47 | 2 |
| W8A16, shortest path | 162 | 0.215 | 14 | 148 | 0 |
| W16A8, connected components | 159 | 0.304 | 123 | 32 | 4 |
| W16A8, shortest path | 128 | 0.214 | 16 | 112 | 0 |
| bf16, connected components | 185 | 0.302 | 136 | 46 | 3 |
| bf16, shortest path | 134 | 0.214 | 14 | 120 | 0 |

