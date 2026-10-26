## 5.7 Plan noise against text-level plan samplers, departure-matched decoding, and the literal cell (Qwen3-8B)

**Why.** The positioning audit of iteration 4 found that the price comparison lacked its strongest competitors: text-level plan samplers, which diversify code by sampling a plan before the program [73, 74], and a decoding baseline matched to plan noise's own departure from the twin, the baseline under which an ICLR 2027 submission (OpenReview oag3wgNLRh) found activation steering no better than ordinary decoding. The review also asked for the literal cell of the request. This experiment [ARTIFACT:art_jR6Pyy3W9xum] ran both.

**The literal cell never changes the algorithm** (Table 206). On the shortest path task with thinking on, top-k 10 and the same 20 token seeds as the iteration-4 thinking arm, moving the temperature over 0.3, 0.7, 1.0 and 1.3 changed the final program's algorithm in 0 of 20 seeds (one-sided Clopper-Pearson 95% upper bound 0.14), and the first approach named in the thinking changed in 0 of 20. All 100 traces completed, every final program was heap-based Dijkstra, and every trace named Dijkstra first. Temperature changed the tokens: a repeat at temperature 0.7 was byte-identical on only 4 of 20 traces while the labels agreed on 20 of 20 (median common prefix 309.5 tokens), and paired with the top-p 1 traces of iteration 4 at the same seed and temperature the labels agreed on 100 of 100 pairs although the traces shared a median of only 34 tokens. A judge agreed with the first-approach lexicon on 19 of 19 audited traces. With this cell, question 1a-c of the request is answered under every sampler the run used: with thinking off at top-k 10 (Table 76), with thinking off and on at top-p 1 (Section 4.5), and with thinking on at top-k 10 here.

**Table 206.** The literal cell: shortest path task, thinking on, top-k 10, 20 seeds per temperature, 16k cap (vLLM, official 8-bit checkpoint). Source: knob experiment `results/literal_cell.json`.

{{T:literal}}

**Design of the knob comparison.** Every knob ran in one HF bf16 engine with exact inverse-CDF common random numbers, so all arms of a slot shared the code-stage uniform stream, on all 15 existing tasks (N = 50 per cell on the five decisive tasks, 30 on the other ten). Plan noise drew a fresh isotropic direction per sample at the task-specification positions of blocks 12 to 23, prefill only, at alpha 1 and 2 ban-free units, under the twin frame and on the plain prompt. The text-level plan samplers were frame-matched, with the twin's neutral sentence first: intent factored generation at the direction's (1.3, 0.7) and the paper's tuned (0.73, 0.60) temperatures [73]; a lite plan search (five observations, a random pair of them combined into a plan, then code) [74]; enumerate-and-pick, in which the model lists up to eight algorithms and an external random number picks one; and a base-written intent, in which Qwen3-8B-Base writes the intent sentence and the instruct model the code. Departure-matched decoding applied a temperature to generated tokens 1 to 32, bisected per task so that its mean per-token KL from the twin equalled plan noise's own at each alpha, measured on calibration-only prefixes. Prices came from a full-simplex randomisation hull with 2,000 slot bootstraps that re-select the best mixture inside every replicate. The committed rule calls the plan-sampler comparison supported if plan noise's 5-point Hill-1 is at least the best text sampler's on at least 3 of the 5 decisive tasks.

**The plan-sampler comparison is DISCONFIRMED** (Table 207). We write H5 for the 5-point Hill-1 and DMD for departure-matched decoding in the tables; the margin D_t is plan noise's H5 minus the best text sampler's. Plan noise matched or beat the best text sampler on 1 of the 5 decisive tasks, kth smallest (1.98 against 1.83 for enumerate-and-pick, P(plan noise at least best) 0.58, unresolved). On connected components, the shortest path task and two sum the base-written intent won (2.53, 1.45 and 1.61 against 1.09, 1.18 and 1.17), and on the grid task nothing moved much. The mean margin is -0.40 (95% interval -0.70 to -0.24), and only 1.8% of bootstrap replicates reach three wins. Every sensitivity keeps the verdict except one (Table 209): with the left-padded multi-stage samplers dropped, intent factored generation is the only text sampler left and plan noise beats it on 4 of 5 tasks, so the disconfirmation rests on the base-written intent and enumerate-and-pick. On the ten other tasks (Table 208) plan noise moved only cycle detection and first and last position, while text samplers moved substring search, find duplicate, Fibonacci, longest increasing subsequence, top-k frequent and first and last position. Two prompt knobs outside the text-sampler set also beat plan noise where it was strongest: the novelty instruction on kth smallest (2.03) and the semantic seed on the shortest path task (2.12).

**Table 207.** The plan-sampler comparison on the five decisive tasks: 5-point Hill-1 of plan noise (with its bootstrap interval) against each text-level plan sampler. Source: knob experiment `results/claim_c.json`.

{{T:claimC}}

**Table 208.** The same prices on the ten other tasks (descriptive; the plan search arm was not run on topological order and first and last position, the base intent arm not on first and last position). Source: knob experiment `results/claim_c.json#nd10_descriptive`.

{{T:claimC_nd}}

**Table 209.** Sensitivities of the plan-sampler rule. Source: knob experiment `results/claim_c.json#sensitivities`.

{{T:claimC_sens}}

[FIGURE:fig_knob_h5]

Table 210 shows what each arm actually wrote on the decisive tasks. Enumerate-and-pick buys the most raw diversity (Hill-1 of 2.9 to 4.7 per cell) at a cost of 16 to 62 pass points, and 40% of its grid rows are invalid. The base-written intent keeps the pass rate high on connected components (0.98) and two sum (0.88) while writing three and four algorithms. Intent factored generation at its cooler code temperature collapsed the grid pass rate to 0.12 and 0.08, with every correct program BFS. Plan noise is much weaker here than in iteration 4: on connected components it wrote union find 49 times in 50 at both alphas, where iteration 4's 8-bit engine at the ban unit had written DFS 29 times at alpha 2 (Section 4.3); Section 5.10 returns to this.

**Table 210.** Every arm on the five decisive tasks: pass rate, invalid rate, correct programs and correct-only Hill-1 (rarefied at depth 25 or at the available depth). Source: knob experiment `results/cells.json`.

{{T:c27_cells}}

**Plan noise against departure-matched decoding.** At alpha 2, plan noise moves the algorithm and the matched decoding does not (Table 211): over the decisive tasks 19 slots are correct and off the default under plan noise only and 3 under the matched decoding only (exact p 0.0009), 13 to 0 on kth smallest alone. At alpha 1 there is no difference (4 against 3). The matched decoding's 5-point Hill-1 is at most 1.25 on every decisive task. So plan noise's effect is not its token-level departure from the twin, which answers the objection of the ICLR 2027 submission for these tasks, but as a practical knob it loses to two text samplers. Plan noise on the plain prompt and under the twin frame showed no significant paired difference on any of the 15 tasks (Table 212).

**Table 211.** Plan noise against departure-matched decoding at matched per-token KL (correct off-default share of N; McNemar on slots correct and off the default under one arm only). Source: knob experiment `results/pn_vs_dmd.json`.

{{T:pn_dmd}}

**Table 212.** Plan noise on the plain prompt against plan noise under the twin frame, same direction and stream. Source: knob experiment `results/plain_vs_twin.json`.

{{T:pn_plain_twin}}

**Checks and deviations.** The engine check against the 8-bit rows of iteration 4 was precision-sensitive (Table 213): the twins agreed per slot at 0.98 to 1.00 and the pushed cells at 0.74 to 0.86, so no iteration-4 row was reused and temperature 1.3, top-k 10, the novelty instruction and the semantic seed were rerun. Twelve correct programs labelled other were 10 labeller misses, 1 degenerate and 1 unresolved; 0 novel. The style re-gate flagged only top-k frequent (agreement 0.80). An independent re-derivation reproduced the literal cell, every McNemar count and the verdict, with hull H5 within 0.08 of the committed hull and a win count of 2 rather than 1 (a near tie on the grid task), still DISCONFIRMED; relabelling plan noise rows as the twin gave margins of 0 or below on all five tasks, and arm-label shuffles centred at 1.6 wins (3 or more wins in 3 of 20 shuffles), so the five-task count rule is only weakly selective on its own. The plan's one allowed wording revision was used after the first format pilot failed (the model wrote code at once), the committed drop order fired after stage 100 and the dropped cells were restored when the queue finished early, and cells with fewer than 30 (decisive) or 15 (other) programs were excluded from hulls, a rule decided after a dry run that favours plan noise on kth smallest. Post hoc, with iteration-1 base label names harmonised, landing mass outside the base support is 0.11 for enumerate-and-pick on the grid task (bidirectional BFS) and 0 for every shortest path landing.

**Table 213.** Engine check of the bf16 knob engine against iteration 4's 8-bit rows. Source: knob experiment `results/engine_check.json`.

{{T:ec27}}

## 5.8 The second family: gemma-3-4b-pt against gemma-3-4b-it

**Why.** The Gemma replication asked whether the account replicates in a second family, with the base repertoire of gemma-3-4b-pt committed before a fresh, never-run push population was applied to gemma-3-4b-it [76]. Gemma's iteration-4 push outcomes were seen, so this experiment [ARTIFACT:art_hG0QPiaIPNhP] is a replication on fresh directions and samples, not a held-out confirmation.

**Design.** Both models ran in bf16 on one 23 GB NVIDIA L4, one at a time. A fresh it twin (N = 50 per task) fixed each task's default under the iteration-5 rule; the grid twin now gave DFS on 30 of 40 correct programs, so every one of the 15 tasks had a default. The pt model wrote 100 programs under the it chat template on the same token ids and 50 in plain completion of a `def solve(...)` stub. Under the chat template 91% of its programs had no usable code and only 10 of 1,500 passed, so the preregistered chat validity gate failed, both formats were pooled, and every unit fell under the low-correct rule: beta, the runner-up and the landing forecast come from valid attempts, not correct programs. These were committed by hash before 16 never-run isotropic directions (seeds 52001 to 52016) were applied at alpha 1 and 2 to the task-specification positions of blocks 11 to 22 on the outlier-excluded ban-free unit. A pt-to-it transplant at lambda 1 then ran on the seven base-diverse tasks with a matched-random, a cross-task and a read-position control on the same slots, and on three base-collapsed controls.

**In Gemma the movability half is inconclusive and the landing half passes** (Table 214). Spearman between beta and the escape fraction is 0.42 (one-sided permutation p 0.060, n = 15), against a bar of 0.5 at p below 0.01; 2 of 3 base-collapsed tasks are immovable against a bar of 80%; and beta is ahead of no rival, with the twin modal share (0.67) and the novelty instruction (0.64) tracking movability better (Table 215). The direction is the predicted one: 6 of 7 base-diverse tasks are movable against 2 of 8 others (one-sided Fisher p 0.032, not registered). The partial Spearman given catalogue size and the forced 'can' count is 0.41 (0.45 given catalogue size alone), and the fresh population agrees with iteration 4's movability on 13 of 15 tasks (8 movable now, 6 then). No sensitivity meets the preregistered bar (Table 216); beta from the chat template alone reaches 0.62 (p 0.0095), but that arm is 91% unusable output, and beta from correct programs only reaches 0.27. The pt runner-up equals the modal landing of confirmed escapes in 5 of 7 events (hit rate 0.71 against a mean chance of 0.30; exact Poisson-binomial p 0.025), and the pt composition beats iteration 4's association forecast by 1.50 nats per event (exact Wilcoxon p 0.023) and AST proximity by 0.51 (Table 217). The two misses are kth smallest (landing size-k heap, runner-up quickselect) and connected components (landing union find, pooled runner-up BFS; union find is the runner-up under the chat template alone).

**Table 214.** Gemma per-unit results: it default (twin share), pt beta and runner-up, escape fraction over 16 fresh directions, landing, and the rivals. Source: Gemma experiment `results/e_a1.json`, `results/e_a2.json`, `README.md`.

{{T:G_units}}

**Table 215.** Rivals against beta in Gemma (90% task-bootstrap intervals). Source: Gemma experiment `results/e_a1.json`.

{{T:G_rivals}}

**Table 216.** Sensitivities of the movability half in Gemma under the same rule. Source: Gemma experiment `results/e_a1.json`.

{{T:G_sens}}

**Table 217.** Landing events in Gemma: pt runner-up against the modal landing of confirmed escapes. Source: Gemma experiment `results/e_a2.json`.

{{T:G_a2}}

**The transplant moves two of seven base-diverse tasks** (Table 218). Every transplanted program stayed valid (pass ratio 0.98 to 1.00). Substring search moved from the naive scan to the built-in find in 40 of 50 programs (twin 6 of 50), and first and last position from the linear scan to binary search in 39 of 50 (twin 4 of 50); both land on the pt runner-up. The other five base-diverse tasks stayed at their default. The two that moved are exactly the base-diverse tasks whose it twin already writes the pt runner-up 8% to 12% of the time, so the transplant amplified an existing minority mode and did not install an absent one. The pt-minus-it difference at the task-specification positions is large (median 5.2 ban-free units, 4.7 to 5.8 across blocks), above the dose at which random noise broke programs in iteration 4, and five massive channels carry 86% of its squared norm at block 11, falling to 31% to 36% by blocks 21 and 22. Random and cross-task controls that copy the massive-channel move and match the remaining norm broke most programs (pass ratio 0.16 to 0.50 and 0 to 0.22), so the random comparison is confounded by norm and the cross-task control is itself broken: what the controls show is that the coherent pt content is benign where an equally large random or cross-task displacement is destructive. The read-position transplant and the three base-collapsed controls stayed within 0.05 of the twin (Table 219); on nonoverlapping intervals the transplant halved the pass rate without moving the algorithm.

**Table 218.** pt-to-it transplant at lambda 1 on the seven base-diverse tasks (s = correct off-default share; McNemar counts transplant only : control only). Source: Gemma experiment `results/transplant.json`.

{{T:G_transplant}}

**Table 219.** Base-collapsed controls of the transplant. Source: Gemma experiment `results/transplant.json`.

{{T:G_collapsed}}

Plan noise rarely moved the it model (Table 220); the exceptions were first and last position (correct off-default share 0.44 and 0.38 at alpha 1 and 2), the grid task (DFS to BFS) and connected components at alpha 2. Spearman between beta and the plan-noise excess is 0.45 (one-sided p 0.046).

**Table 220.** Plan noise in gemma-3-4b-it (a fresh direction per sample, N = 50 per alpha). Source: Gemma experiment `results/pn.json`.

{{T:G_pn}}

**Labels and checks.** The base labels are the weakest link: runtime labels agreed with a two-family judge adjudication on 30 of 30 it programs but on 5 of 30 pt programs (20 of 30 after the inline judge), because the pt code is mostly broken, so the style re-gate failed and its preregistered fallback, judging every runtime-AST disagreement, applied; a 225-program audit of pt labels agreed at 0.64 (0.47 to 0.93 by task). A structural audit of 92 default and runner-up programs agreed at 0.99. The re-gated shortest path rule, which reads array-based Dijkstra correctly, relabels 258 iteration-4 shortest path programs: their escape fraction falls from 0.25 to 0.125 and their ban compliance from 0.96 to 0.34, which confirms the iteration-4 mislabel. The engine check reproduced iteration-4 slots exactly; 0 novel algorithms among 56 correct programs labelled other (35 catalogue variants, 21 degenerate); the commits preceded the first push and transplant rows; two independent re-derivations found no mismatch, with placebos failing as required. Seventeen deviations are logged.

## 5.9 Positioning: base-model variety, transplants and base-aligned collaboration in published work

The positioning audit [ARTIFACT:art_ObxQOIlAM9MS], dated 2026-10-21, extended the iteration-4 audit to the new claims. It checked 137 verbatim quotes from 93 references (111 against full text, 21 against ICLR 2027 abstracts, 5 against blog posts; no mismatch, and a live second pass re-matched all 137) and ran a saturation search under a protocol frozen before the first call: 169 logged calls, 4,508 raw hits, 3,506 unique records, 49 scored on the occupancy rubric, with the stop rule met after the third round. Table 221 gives its verdict per claim.

**Table 221.** Lane verdicts for the iteration-5 claims as of 2026-10-21. Source: positioning audit `research_report.md`, `evidence/flags.json`.

| Claim | Lane verdict | Deciding neighbours |
|-|-|-|
| Premise: tuning narrowed algorithm choice on code (premise flag) | partly occupied; contradicting in part | Lee et al. compare a code base and instruct pair and find instruction tuning narrows algorithmic diversity on easy problems and widens it on others [72]; Le Bronnec et al. [107]; text-domain support [101] |
| Movability half: movability follows the base repertoire (forecast flag) | partly occupied at training time; inference-time movability open | per-prompt forecasts from the frozen base model of what reinforcement learning narrows [98, 99, 109] |
| Landing half: the landing is the base runner-up | adjacent only (stylised and retrospective support) | power-sharpening under typicality bias [46]; aligned top tokens within the base top-5 [100] |
| Transplant claim: base prefill states written into the instruct model (transplant flag) | method occupied, diversity outcome open; transplant flag not fired | cross-patching of base states into a descendant [91]; base-to-tuned activation patching [88, 89, 90]; weight-level diversity restoration [92, 93] |
| De-sharpening push | method and random-direction control occupied (style outcome) | ablation of an aligned-minus-base direction during decoding [97] |
| Plan-sampler comparison | partly occupied; base-aligned collaboration is an occupied lane | token-level base-aligned collaboration [94, 95, 96]; intent factored generation, plan search and departure-matched decoding [73, 74] |
| Gemma replication | adjacent only | a base and chat Gemma pair can diverge unusually (Kissane et al., blog); template-controlled contrasts [103] |
| Novelty boundary | unchanged from Table 92c | [81, 82, 105, 106] |

Three flags summarise the search. The transplant flag, a paper that writes base-model hidden states into its tuned descendant and reports a change in output diversity, did not fire, narrowly: cross-patching writes base upstream states into a descendant's late stack but measures a next-token margin [91], and earlier patching work measured backdoor removal [89], factual recall [90] or entity tracking [88]; the goal of restoring diversity is published at the weight level, by restoring layer intervals to pretrained weights [92] or merging aligned lower layers with base upper layers [93], and at the token level [94]. The transplant may not be called first. The forecast flag, a forecast from the base model of where post-training narrows, partly fired: training-time per-prompt forecasts exist, and one finds that base pass rate and likelihood explain only 0.30 and 0.24 of the explainable variance in post-training gains [99]; inference-time movability and the identity of the landing remain open. The premise flag partly fired: Lee et al. compared DeepSeek-Coder base and instruct models with test-checked correctness and found a mixed direction [72], so the premise row reads contradicting in part. The audit recommends further baselines for any later write-up: weight interpolation between Qwen3-8B-Base and Qwen3-8B [102], layer restoration and splicing at the transplant's block ranges [92, 93], token routing between base and aligned models [94], logit-level base and tuned arithmetic, and template control for every base-minus-instruct contrast [103]. It also lists 27 corrections to earlier citations. Table 92d condenses the paste-ready neighbour table of the audit; the verbatim quotes are in its `evidence/quotes_iter5.jsonl`.

**Table 92d.** Iteration-5 claims and their nearest published neighbours (the verbatim quote behind each row is in the positioning audit's evidence file). Source: positioning audit `research_report.md`, Section 3.

{{T:table92d}}
