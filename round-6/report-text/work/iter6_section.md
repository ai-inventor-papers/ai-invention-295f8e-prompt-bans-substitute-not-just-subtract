# Iteration 6: an engine control, where a ban and an instruction are carried, a one-token fork in Gemma, and the plan in words

## 6.1 Why this iteration ran what it ran

**The review of the iteration-5 record.** The review was blocking again. It raised five major items, all marked must fix, and four minor ones. The first went to the run's main internal result. Every plan-noise positive of iteration 4 had come from an 8-bit engine whose W8A8 linear layers compute in 8-bit floating point (e4m3 weights per output channel, e4m3 activations with a per-token scale), while iteration 5's bf16 knob experiment found per-sample plan noise nearly inert: connected components moved in 1 of 50 programs at alpha 2 against 30 of 50 under the 8-bit engine. The record had left the cause open, had not reported the knob experiment's own measurement of the dose it delivered, and still listed iteration-4 items 2 to 4 as established. The review asked for a decisive control: the same directions and slots at the same absolute displacement under the 8-bit engine, under 8-bit floating-point weights with bf16 activations and under bf16. The second item found the landing half of the narrowed repertoire account overstated. Its tally of 16 of 19 omitted the bf16 remeasurement made in that same iteration, and it never scored the minority algorithm of the instruct twin itself as a rival, although that rival explained half the hits. The third item asked for the power and interval behind the claim that the movability half was ruled out, and for the frozen rivals on the pooled set. The fourth listed executed outputs missing from the record: the phrasing columns of the literal cell, the prices at Hill-1 1.5 and 2, the dose file of the knob experiment, the knob rows of panel B and three Llama rows of Table 126c. The fifth said that after five iterations the record still had no internal account of how the choice manifests, which is the request's central question, and that its one internal positive rested on the 8-bit engine. The minor items asked for the per-task counts behind item 4 of Section 5.11, the fill rule for undefined Gemma forecasts, a sentence on the three new tasks whose instruct twins are already mixed, and a second blind adjudication of the 14 transplant programs that two of three judges had called novel. Table 224 maps every item to its answer.

**Table 224.** Review items on the iteration-5 record and where this report answers them.

| Review item | What the review found | Where it is answered |
|-|-|-|
| Engine | The 8-bit plan-noise effect does not replicate in bf16 at near-matched dose; the dose file unreported; iteration-4 items 2 to 4 still established; plan-sampler and movability verdicts not tagged with their engine | Corrections in Sections 4.2.6, 4.10, 5.2, 5.10, 5.11 and 5.12; Section 6.2.2; the engine control, Section 6.3 |
| Landing half | Selective tally; the twin's own minority never scored; thin base support in Gemma; two units where the instruct twin is more diverse than the base | Corrections in Sections 5.5, 5.8, 5.10, 5.11 and 5.12; Section 6.2.3; the landing contest of Section 6.4.5 |
| Movability half | Ruled out without its interval or power; the frozen rivals not computed on the pooled set | Correction in Section 5.11; Section 6.2.4 |
| Missing outputs | Literal-cell phrasing columns; prices at Hill-1 1.5 and 2; dose file; panel B knob rows; Table 126c rows | In place in Tables 206, 207b, 203b and 126c and in Section 5.2; Section 6.2.5 |
| Coverage | No representation of the choice; the internal positive rests on the 8-bit engine | Sections 6.3 to 6.6; Section 6.10 |
| Minor: matched decoding per task | Item 4 of Section 5.11 generalised from kth smallest | Correction in Section 5.11 |
| Minor: Gemma fill rule | The 1.50 nats included an undefined association forecast filled uniformly | Corrections in Sections 5.8 and 5.11 |
| Minor: mixed instruct twins | Three new units are already mixed; on two the instruct twin is more diverse than the base | Notes under Sections 5.4 and 5.5; correction in Section 5.11; the closing section |
| Minor: novelty adjudication | The zero rested on the executor's override of two judges | Section 6.2.6; corrections in Section 4.9 and the closing section |

**The hypothesis update.** The update turned from the outside of the model to its inside. Five iterations had mapped what moves the algorithm from outside: a ban, a meaningful hint, a plan sentence written by the base model, a list-then-pick step. None had located where the model holds its choice. The update proposed one concrete answer, which it called the plan-variable account. While the model reads the task, it computes a small hidden variable that says which algorithm to write. We call this variable the *plan*. On tasks where a ban acts through the prompt states (shortest path, kth smallest, connected components) the plan sits in the residual stream at the task-specification positions; on tasks where generated tokens read the ban directly (two sum, find duplicate) it sits at the first generated tokens. Exchanging a few of its dimensions between two prompts should switch the algorithm the model writes, with correct code. Random noise should change the algorithm only through the part of it that falls inside the plan, which would explain why most random directions do nothing; temperature should never touch it.

The update tested the account with the instruments the request names and the run had not yet used. An *interchange intervention* replaces a component's activations under one input with those under another and measures the change in output. *Distributed alignment search* (DAS) fits an orthonormal low-rank subspace in which such an exchange reproduces a counterfactual behaviour [110, 111]. A *natural language autoencoder* (NLA) pairs an activation verbalizer, which writes a text explanation of a residual-stream state, with an activation reconstructor, which maps text back to a state; released checkpoints exist for Qwen2.5-7B-Instruct [124] at layer 20, not for Qwen3-8B. Gemma Scope 2, released in December 2025, provides JumpReLU sparse autoencoders [114] and transcoders trained on gemma-3-4b-it itself, the successor of the Gemma Scope release for Gemma 2 [113], so no transfer test from a base model is needed.

Eleven claims were preregistered, each with a rule committed by sha256 before its first decisive sample. We call them by their content rather than by their codes: the engine claim, the localization claim, the mediation claim, the discreteness claim, the token claim, the resampling claim, the verbal readout claim, the feature claim, the site rerun, the landing contest and the novelty count.

- *The engine claim* (primary): on connected components and shortest path, the same 40 directions and common-random-number slots at the same absolute displacement under four numerics. Activation rounding is the cause if the escape fraction under bf16 weights with 8-bit floating-point activations (W16A8) exceeds bf16 by at least 0.2, the full 8-bit engine (W8A8) matches W16A8 within 0.1 and 8-bit floating-point weights with bf16 activations (W8A16) match bf16 within 0.1, on both tasks. The result is called not reproduced if W8A8 minus bf16 is below 0.1.
- *The localization claim* (primary). Stage A, with no training: exchanging the full residual states of the ban prompt into the neutral twin transfers the ban's substitute at a transfer share of at least 0.5 on at least two of shortest path, kth smallest and connected components, at a pass rate of at least 0.8 times the twin's, and at most 0.2 on two sum and find duplicate. Stage B: DAS at one layer recovers at least 0.8 of the full-state transfer at a rank of 16 or less on held-out templates.
- *The mediation claim* (primary): the energy that a random direction puts into the fitted plan subspace predicts which directions switch the algorithm (Spearman at least 0.5).
- *The discreteness claim*, *the token claim* (temperature leaves the plan coordinate flat while state noise at generated tokens beats temperature at matched per-token KL) and *the resampling claim* (resampling the plan as a diversity knob) (secondary).
- *The verbal readout claim* (secondary): the NLA names the substitute of a ban before any code is written at a rate at least 0.3 above a judge reading the visible text; editing the explanation's algorithm phrase and reconstructing transfers the algorithm by at least 0.2.
- *The feature claim* (secondary): in Gemma's natural BFS against DFS split on the grid task, Gemma Scope 2 features decode the upcoming algorithm at least 0.10 balanced accuracy above a classifier on the visible text, and steer at least as well as a difference-in-means direction at matched pass.
- *The site rerun* (secondary): the iteration-4 noise-site comparison in bf16; the prefill-site claim survives if the task-specification site beats the read position and the condition sentence at matched downstream displacement on at least one task, and is withdrawn otherwise.
- *The landing contest* (secondary): the base runner-up against the instruct twin's own teacher-forced ranking of algorithm openings, on every recorded push-landing event.
- *The novelty count* (secondary).

**The strategy.** Seven artifacts were planned (Table 225). One evaluation on CPU, which we call the record audit, repaired the record from rows on disk and ran the second novelty adjudication. An experiment we call the engine control ran the four numerics on a 16 GB RTX 2000 Ada, an Ada-generation card with the 8-bit floating-point tensor cores that the 8-bit engine needs. A bf16 experiment, which we call the exchange and site experiment, ran the Stage A exchanges, the site rerun, state noise against matched temperature, the top-five push and the landing contest. Gemma and the NLA each received their own experiment, which we call the Gemma feature experiment and the NLA experiment, and a research artifact, which we call the positioning audit, searched the literature for each claim. The seventh artifact, which was to fit the DAS subspaces of Stage B and run the mediation, discreteness, resampling and temperature-coordinate tests together with a manifold of plan coordinates, was lost before it existed: the planning agent returned no plan. Section 6.8 records it as planned and not run. Every Qwen3-8B number of this iteration except those of the engine control comes from a bf16 engine.

**Table 225.** The artifacts of iteration 6, the question each was asked, and its hardware and spend.

| Artifact | Question | Model and hardware | OpenRouter spend |
|-|-|-|-|
| Record audit [ARTIFACT:art_aRTQM6CQ0Dre] | Repair the iteration-5 record (36 corrections); re-adjudicate the 14 disputed transplant programs blind | No generation; CPU only | USD 0.29 |
| Engine control [ARTIFACT:art_lpQalcAXMGr1] | Are iteration 4's random-push escapes a property of the model or of the 8-bit floating-point W8A8 engine? | Qwen3-8B under four numerics built from one bf16 snapshot; one 16 GB RTX 2000 Ada; 6,075 generated programs plus reused iteration-4 rows; 4.1 GPU hours of generation | USD 0.085 |
| Exchange and site experiment [ARTIFACT:art_rMlbrjVB1c__] | Where is a ban carried; does the noise-site claim hold in bf16; state noise against matched temperature; the top-five push; the landing contest | Qwen3-8B bf16 with the input embedding table on CPU, one 16 GB RTX 2000 Ada; 4,320 programs and 1,220 teacher-forced passes; about 2.7 GPU hours | USD 0.055 |
| Gemma feature experiment [ARTIFACT:art_zNyBP6zieI5u] | Where does Gemma's BFS-or-DFS choice fork; do Gemma Scope 2 features read and steer it better than difference in means, random features and DAS? | gemma-3-4b-it bf16, one 16 GB RTX 2000 Ada; about 2.1 GPU hours of generation | USD 0.034 |
| NLA experiment [ARTIFACT:art_dbUtqBjT0tPf] | Does the residual stream say in words which algorithm will be written, and can a verbal edit steer it? | Qwen2.5-7B-Instruct bf16 with the released layer-20 NLA pair, one 24 GB NVIDIA Ada GPU; about 2.0 GPU hours | about USD 2.0 |
| Positioning audit [ARTIFACT:art_OUuQUYQn5voE] | Set the iteration-6 claims against published work | Web search and quote checks | none recorded |
| DAS and plan-coordinate experiment | Stage B of the localization claim; the mediation, discreteness, resampling and temperature-coordinate tests; the causal manifold | Planned for Qwen3-8B bf16; lost at planning | not run |

## 6.2 The record audit: corrections, engine tags and a second novelty adjudication

The record audit [ARTIFACT:art_aRTQM6CQ0Dre] generated no model text. It recomputed from the row files of the earlier artifacts every number the review touched, tagged each internal result with the numerics that produced it, and wrote each change as a verbatim replacement keyed to the report. Of the values behind its corrections, 78 matched the record, 18 were new, 2 were carried from earlier evaluations and 1 was corrected: the power of the movability test, recorded as 0.46, is 0.63 for the registered one-sided test and 0.50 two-sided. A standard-library re-derivation passed 277 of 277 checks, its five placebos failed as they should, and a second script reproduced 7 of 7 headline numbers from the rawest files. Judge spend was USD 0.29 over four passes.

### 6.2.1 The corrections

Twenty-nine of the 36 corrections are applied in place in Sections 4 and 5 and marked as iteration-6 corrections. The seven that target the closing section are folded into the closing section, which is rewritten at the end of this iteration. The audit ran in parallel with the engine control, so its engine tags were written before the control's result existed; where the control supersedes them, the in-place text adds a pointer to Section 6.3. Three further notes of the same kind mark the frozen screen of Section 4.2.6, the movability paragraph of Section 5.10 and the caption of Table 222. Table 226 lists every correction.

**Table 226.** The 36 corrections of the iteration-5 record (values behind each: M match, N new, C carried, X corrected). Source: record audit `corrections.json`.

| No. | Location | What changed | Values |
|-|-|-|-|
| 1 | Section 5.2, dose units | The two dose definitions (ratio of mean norms against mean of per-position ratios) reconciled per task | 14 M, 6 N |
| 2 | Table 222 caption | The two plan-noise columns put on one definition | 20 M |
| 3 | Section 5.10, movability paragraph | Shortest path counts restated per definition; dose-bracketed contrast and its tags | 2 M, 5 N |
| 4 | Section 4.10, preamble | Engine class of iteration 4 named | 1 N |
| 5 | Section 4.10, item 2 | Same-seed contrast tagged as 8-bit only | 1 C |
| 6 | Section 4.10, item 3 | Site odds ratio tagged as 8-bit only | 1 C |
| 7 | Section 4.10, item 4 | Plan-noise prices tagged with their engine and unit | 4 M |
| 8 | Closing | Internal claims that survive the engine change (folded into the new closing) | none |
| 9 | Closing | Dose bracket removes a scalar dose shortfall (folded) | none |
| 10 | Closing | Site claim tagged as 8-bit (folded) | none |
| 11 | Section 5.10, figure | The base-variety figure redrawn like for like under bf16 | 2 M |
| 12 | Section 5.11, item 2 | Landing half moved to the descriptive results; tally per set and the twin-minority rival | 7 M, 1 N |
| 13 | Section 5.11, item 2 | Gemma fill rule; defined-only mean 1.57 | 2 M, 1 N |
| 14 | Section 5.12 | Landing half restated as descriptive, with its tally | none |
| 15 | Closing | Landing tally per set (folded) | none |
| 16 | Section 5.10 | Landing tally of 16 of 19 replaced by 17 of 21 per set | 4 M |
| 17 | Table 129 | Row label made explicit: counted on all 13 events | none |
| 18 | Table 129 | Same, for the largest-excess row | none |
| 19 | Section 5.11, item 3 | Three mixed instruct twins; two units where the twin is more diverse than the base | 4 M |
| 20 | Table 203 | Base support counts per panel B event | none |
| 21 | Table 214 | Base support counts per Gemma unit | none |
| 22 | Table 217 | Base support counts per Gemma landing event | none |
| 23 | Section 5.11, movability half | Interval, power and pooled rivals; verdict restated | 1 M, 1 X, 1 N |
| 24 | Closing | Movability interval and power (folded) | none |
| 25 | Section 5.12 | The shrinkage of the movable set: what is ruled out | none |
| 26 | Section 5.11, dead end | Plan noise as a knob tagged with its design | none |
| 27 | Table 206 | Phrasing clusters per temperature in the literal cell | 4 M, 1 N |
| 28 | After Table 208 | Table 207b: prices at Hill-1 1.5 and 2 with bootstrap intervals | 5 M |
| 29 | Section 5.5 | Table 203b: panel B knob rows | 2 M, 1 N |
| 30 | Table 126c | The three Llama present-minor ban rows completed | 3 M |
| 31 | Section 5.11, item 4 | Plan noise against matched decoding restated per task | 2 M |
| 32 | Section 5.4 heading | Mixed instruct twins noted | none |
| 33 | Section 5.5 heading | Same note | none |
| 34 | Closing | Mixed instruct twins (folded) | none |
| 35 | Closing | Second novelty adjudication (folded) | 2 M, 1 N |
| 36 | Section 4.9 | Second novelty adjudication noted | none |

### 6.2.2 Engine and dose

The two artifacts that the review compared recorded off-default shares on different definitions: the bf16 knob experiment counted correct programs off the default over all samples, the 8-bit plan-noise experiment valid attempts off the default over all samples. The dose definitions differ as well. Table 174 gave the ban-free unit as a ratio of mean norms, while the knob experiment measured a mean of per-position ratios, which is larger because a mean of ratios is not a ratio of means (Table 227). On the six decisive tasks, by either definition, the bf16 alpha-2 cell of iteration 5 delivered at least 1.24 ban units, so a dose-bracketed contrast sets it against the 8-bit alpha-1 cell, which delivered 1.00. A lower bf16 share in that comparison cannot come from a shortfall of the scalar dose.

**Table 227.** The ban-free unit as a fraction of the ban unit under the two definitions, and iteration 5's bf16 doses expressed in 8-bit ban units. Source: record audit `tables/dose_reconciliation.csv`.

| Task | Ratio of mean norms (Table 174) | Mean of per-position ratios (knob experiment) | bf16 alpha 1 in ban units (two definitions) | bf16 alpha 2 in ban units (two definitions) |
|-|-|-|-|-|
| grid | 0.751 | 0.874 | 0.75 / 0.87 | 1.50 / 1.75 |
| shortest path | 0.834 | 0.889 | 0.83 / 0.89 | 1.67 / 1.78 |
| kth smallest | 0.974 | 1.394 | 0.97 / 1.39 | 1.95 / 2.79 |
| two sum | 0.777 | 0.995 | 0.78 / 0.99 | 1.55 / 1.99 |
| find duplicate | 0.620 | 0.829 | 0.62 / 0.83 | 1.24 / 1.66 |
| connected components | 0.745 | 0.990 | 0.75 / 0.99 | 1.49 / 1.98 |
| top-k frequent | 0.699 | 0.924 | 0.70 / 0.92 | 1.40 / 1.85 |
| first and last position | 0.618 | 0.887 | 0.62 / 0.89 | 1.24 / 1.77 |
| substring search | 0.296 | 0.976 | 0.30 / 0.98 | 0.59 / 1.95 |
| Fibonacci | 0.885 | 1.234 | 0.88 / 1.23 | 1.77 / 2.47 |
| longest increasing subsequence | 0.803 | 1.061 | 0.80 / 1.06 | 1.61 / 2.12 |
| merge intervals | 0.951 | 1.365 | 0.95 / 1.37 | 1.90 / 2.73 |
| nonoverlapping intervals | 0.761 | 1.089 | 0.76 / 1.09 | 1.52 / 2.18 |
| topological order | 0.864 | 1.136 | 0.86 / 1.14 | 1.73 / 2.27 |

Table 228 gives the contrast under both share definitions. The rule, fixed before computing, tags a task as not replicated when the bf16 share falls short at the matched alpha of the 8-bit engine (Fisher p) and in the dose bracket. Connected components and shortest path meet it, kth smallest and the grid task do not, and two sum and find duplicate had no 8-bit effect of at least 10% at alpha 2 or less to replicate. These tags compare the design of iteration 5 (bf16 with the ban-free unit and fresh direction seeds) with the design of iteration 4 (the 8-bit engine with the ban unit); they cannot say which of the three differences (the numerics, the dose unit, the direction seeds) is responsible. Section 6.3 separates them.

**Table 228.** Per-sample plan noise, the bf16 cells of iteration 5 against the 8-bit cells of iteration 4, on two definitions (counts off the default over N). Source: record audit `tables/engine_pn_contrast.csv`.

| Task | Definition | bf16 alpha 1 | bf16 alpha 2 | 8-bit alpha 0.5 | 8-bit alpha 1 | 8-bit alpha 2 | Fisher p, alpha 2 | Bracket p (bf16 alpha 2 against 8-bit alpha 1) | Tag |
|-|-|-|-|-|-|-|-|-|-|
| kth smallest | correct only | 4/49 | 14/50 | 4/50 | 14/50 | 23/47 | 0.039 | 0.588 | not established |
| kth smallest | all samples | 5/50 | 14/50 | 4/50 | 14/50 | 25/50 | 0.040 | 0.588 | not established |
| connected components | correct only | 1/50 | 1/50 | 0/50 | 6/50 | 30/50 | 7.2e-11 | 0.056 | did not replicate in bf16 at the population level |
| connected components | all samples | 1/50 | 1/50 | 0/50 | 6/50 | 30/50 | 7.2e-11 | 0.056 | did not replicate in bf16 at the population level |
| shortest path | correct only | 0/50 | 2/47 | 3/49 | 9/43 | 15/37 | 5.3e-05 | 0.017 | did not replicate in bf16 at the population level |
| shortest path | all samples | 0/50 | 5/50 | 4/50 | 13/50 | 27/50 | 4e-06 | 0.033 | did not replicate in bf16 at the population level |
| two sum | correct only | 0/50 | 2/50 | 0/50 | 0/50 | 1/50 | 1.000 | 1.000 | not established (no 8-bit effect to replicate) |
| two sum | all samples | 0/50 | 2/50 | 0/50 | 0/50 | 1/50 | 1.000 | 1.000 | not established (no 8-bit effect to replicate) |
| grid | correct only | 0/40 | 1/38 | 0/43 | 1/35 | 4/36 | 0.194 | 0.732 | not established |
| grid | all samples | 0/50 | 2/50 | 1/50 | 3/50 | 12/50 | 0.008 | 0.500 | not established |
| find duplicate | correct only | 0/30 | 0/30 | 0/50 | 0/50 | 0/49 | 1.000 | 1.000 | not established (no 8-bit effect to replicate) |
| find duplicate | all samples | 0/30 | 0/30 | 0/50 | 0/50 | 1/50 | 1.000 | 1.000 | not established (no 8-bit effect to replicate) |

The audit tagged 24 internal results of iterations 2 to 5 with the numerics that produced them (Table 229). Its tags were fixed before the engine control finished; the last column gives each tag's status after Section 6.3.

**Table 229.** Internal results by engine class, with the audit's tag and the status after the engine control. Source: record audit `tables/engine_labels.csv`; engine control `results/relabel_table.json`.

| No. | Result | Engine class | bf16 counterpart (audit) | Audit tag | Status after Section 6.3 |
|-|-|-|-|-|-|
| 1 | Plan-noise 5-point Hill-1 2.72 on kth smallest | 8-bit W8A8 | 1.98 at the ban-free unit | not established | not rerun (kth smallest dropped from the engine control) |
| 2 | Plan-noise 5-point Hill-1 2.09 on connected components | 8-bit W8A8 | 1.09; 1 of 50 correct off the default | did not replicate in bf16 at the population level | model property: at the absolute unit bf16 plan noise moves 25 of 50 valid attempts against 30 of 50 |
| 3 | Plan noise moves shortest path 26% at alpha 1 | 8-bit W8A8 | 0 of 50 at alpha 1, 2 of 47 at alpha 2 | did not replicate in bf16 at the population level | model property: 10 of 50 against 12 of 50 at alpha 1, 22 of 50 against 22 of 50 at alpha 2 |
| 4 | Plan noise on the grid task, 0.24 at alpha 2 | 8-bit W8A8 | 1 of 38 correct | not established | not rerun |
| 5 | Site odds ratio 5.72 | 8-bit W8A8 | none | 8-bit only, untested in bf16 | bf16 site rerun (Section 6.4.2): committed rule withdrawn; post-hoc model puts the read position below the task-specification site |
| 6 | Same-seed contrast, 17.25 of 20 seeds | 8-bit W8A8 | none | 8-bit only, untested in bf16 | not rerun; its per-sample plan noise reproduces in bf16 at the absolute unit |
| 7 | 40-direction escape fractions | 8-bit W8A8 | 8 bf16 directions at the ban-free unit: kth smallest 0.25, connected components 0.125, others 0 | did not replicate on shortest path, two sum, grid and find duplicate; replicated, smaller, on kth smallest and connected components | model property on connected components (0.65 against 0.725) and shortest path (0.15 against 0.20) at the same 40 directions and absolute unit |
| 8 | Frozen screen: six movable tasks | 8-bit W8A8 | bf16 remeasure: two movable | did not replicate (4 of 6 tasks no longer movable) | the escapes behind it reproduce in bf16 at the absolute unit on the two tasks tested; the shrinkage belongs to the ban-free unit or its seeds |
| 9 | Plan-subspace tests | 8-bit W8A8 | none | 8-bit only, untested in bf16 | untested (the DAS experiment was not run) |
| 10 | Connected components screen escape from a bf16 direction | bf16 | itself | bf16 result | unchanged |
| 11 | Pre-selected directions 9002 and 9004 move in both engines | 8-bit and bf16 | shortest path Dijkstra 31, Bellman-Ford/SPFA 19 under bf16 against 26 and 24 | replicated in bf16 | unchanged; direction 9004 also moves shortest path under every numerics (Section 6.3) |
| 12 | Plan noise against matched decoding, 19 against 3 | bf16 | itself | bf16 result | unchanged (13 of the 19 on kth smallest) |
| 13 | Transplant results | bf16 | itself | bf16 result | unchanged |
| 14 | Read-position transplant breaks output without moving the algorithm | bf16 | itself | bf16 result | unchanged |
| 15 | Route of a ban | bf16 | itself | bf16 result | extended by the exchange of Section 6.4 |
| 16 | Band patching on kth smallest and connected components | bf16 | itself | bf16 result | extended by the exchange of Section 6.4 |
| 17 | Literal cell, temperature null with thinking on | vLLM 8-bit floating-point W8A16 (weight only) | none needed | behaviour level, engine-robust | unchanged |
| 18 | Temperature changes phrasing, not the algorithm | vLLM 8-bit floating-point W8A16 | bf16 temperature 1.3 cells show no diversity | behaviour level, engine-robust | unchanged |
| 19 | Llama knob rows | vLLM bf16 | itself | bf16 result | unchanged |
| 20 | Novelty audits | sandboxed CPU scoring | not applicable | behaviour level, engine-robust | unchanged |
| 21 | Plan-sampler comparison disconfirmed | bf16 | itself | bf16-conditional | conditional on iteration 5's ban-free unit and direction seeds, not on the numerics |
| 22 | Movability half | bf16 | itself | bf16-conditional | same |
| 23 | Plan noise as the practical knob is a dead end | bf16 | itself | bf16-conditional | same |
| 24 | Six screen-movable tasks shrank to two | bf16 | itself | bf16-conditional | same |

The figure of base-model variety against movability is redrawn like for like (correction in Section 5.10): the existing tasks at their bf16 escape fraction under the ban-free unit, with the 8-bit screen values as ghost markers, against the new units under the same design. Over the 15 existing tasks Spearman is 0.59 (one-sided permutation p 0.010, Bonett-Wright 95% interval [126] from 0.06 to 0.86), against 0.79 with the 8-bit screen values; over the 13 new units it is 0.15 (p 0.315, interval from -0.44 to 0.65), 0.01 with the two reserve units; pooled over the 28 bf16 measurements it is 0.48 (p 0.005).

### 6.2.3 Landings

Table 230 restates every recorded push-landing event with its base support and the instruct twin's own composition. Per set, the base runner-up named the landing 5 of 5 times on the 8-bit screen, 1 of 2 on the bf16 remeasurement of existing tasks, 3 of 3 in panel A, 3 of 4 in panel B and 5 of 7 in Gemma, 17 of 21 in all (Poisson-binomial p 5.8e-7). On 6 of the 11 held-out hits the landing is also an algorithm the instruct twin already writes. Restricted to the 8 held-out events where the twin wrote no correct program off the default, the base runner-up named 5 (p 0.053; Qwen3-8B 3 of 4, p 0.052; Gemma 2 of 4, p 0.42). On the 7 events where the twin wrote any alternative, the twin's own most frequent alternative named the landing 6 times, as often as the base runner-up (exact McNemar p 1.0). The landing half therefore moves to the descriptive results: where the twin writes an alternative, the landing is that alternative, and the base model adds a forecast only where the twin writes none.

**Table 230.** Every recorded push-landing event: default, landing, base runner-up, the twin's correct composition, and the base support (valid attempts, correct programs, runner-up count among correct and among attempts). Source: record audit `tables/landing_events.csv`.

| Set | Task | Default | Landing | Base runner-up | Hit | Twin correct composition | Base valid / correct | Runner-up among correct / attempts | Held out, twin wrote no alternative |
|-|-|-|-|-|-|-|-|-|-|
| 8-bit screen | kth smallest | full sort | quickselect | quickselect | yes | full sort 50 | 65 / 47 | 13 / 19 | not held out |
| 8-bit screen | shortest path | Dijkstra | Bellman-Ford/SPFA | Bellman-Ford/SPFA | yes | Dijkstra 50 | 129 / 44 | 18 / 40 | not held out |
| 8-bit screen | two sum | hash map | brute force | brute force | yes | hash map 50 | 59 / 49 | 7 / 8 | not held out |
| 8-bit screen | connected components | union find | DFS | DFS | yes | union find 50 | 92 / 55 | 32 / 42 | not held out |
| 8-bit screen | grid | BFS | DFS | DFS | yes | BFS 37 | 112 / 14 | 4 / 38 | not held out |
| bf16 remeasure | kth smallest | full sort | size-k heap | quickselect | no | full sort 49, quickselect 1 | 65 / 47 | 13 / 19 | not held out (the twin writes quickselect once) |
| bf16 remeasure | connected components | union find | DFS | DFS | yes | union find 50 | 92 / 55 | 32 / 42 | not held out |
| panel A | majority element | hash count | Boyer-Moore vote | Boyer-Moore vote | yes | hash count 50 | 38 / 29 | 12 / 14 | yes |
| panel A | trapped rain water | prefix and suffix maxima | two pointers | two pointers | yes | prefix and suffix maxima 32, two pointers 18 | 37 / 22 | 5 / 6 | no |
| panel A | longest mirrored substring | expand around centre | brute force | brute force | yes | expand around centre 50 | 39 / 28 | 8 / 13 | yes |
| panel B | single number | hash count | XOR fold | XOR fold | yes | hash count 46, XOR fold 4 | 77 / 62 | 32 / 34 | no |
| panel B | minimum spanning tree weight | Kruskal | Prim with heap | Prim with heap | yes | Kruskal 33, Prim 17 | 89 / 28 | 3 / 11 | no |
| panel B | integer square root | binary search | linear scan | floating point sqrt | no | binary search 50 | 108 / 76 | 15 / 17 | yes |
| panel B | count inversions | merge sort count | sorted insertion with bisect | sorted insertion with bisect | yes | merge sort count 3 | 87 / 15 | 2 / 5 | yes |
| Gemma | grid | DFS | BFS | BFS | yes | DFS 30, BFS 10 | 73 / 0 | 0 / 4 | no |
| Gemma | kth smallest | full sort | size-k heap | quickselect | no | full sort 50 | 51 / 14 | 0 / 6 | yes |
| Gemma | substring search | naive | built-in find | built-in find | yes | naive 44, built-in find 6 | 55 / 18 | 13 / 26 | no |
| Gemma | two sum | hash map | brute force | brute force | yes | hash map 50 | 55 / 13 | 7 / 14 | yes |
| Gemma | connected components | DFS | union find | BFS | no | DFS 50 | 47 / 1 | 0 / 6 | yes |
| Gemma | first and last position | linear scan | binary search | binary search | yes | linear scan 46, binary search 4 | 48 / 4 | 0 / 12 | no |
| Gemma | longest increasing subsequence | patience sorting with bisect | quadratic DP | quadratic DP | yes | patience sorting with bisect 50 | 51 / 5 | 5 / 20 | yes |

Two units contradict the narrowing premise directly: on trapped rain water and minimum spanning tree weight the instruct twin is more diverse than the base model (twin off-default share 0.36 against a base off-default share of 0.23, and 0.34 against 0.11), and on both the landing is the twin's own minority.

### 6.2.4 Movability

The movability verdict is restated with its interval and power (correction in Section 5.11). Over the 13 new units, Spearman between the base off-default share and the escape fraction is 0.15, with a Bonett-Wright 95% interval from -0.44 to 0.65, a Fieller interval from -0.46 to 0.66, a BCa bootstrap interval from -0.50 to 0.70 and a one-sided permutation p of 0.317. At a true correlation of 0.6, the registered one-sided permutation test has power 0.63 (0.50 two-sided, the figure the record had quoted as 0.46), and 20 units would give 0.8. The data exclude a strong relation, not a moderate one. The pooled value also leans on one unit: count inversions' committed base share of 0.75 came from attempts, because only 15 base programs were correct and 58 of its 87 attempts are labelled other; on the correct-only basis of the other twelve units its share is 0.13 and the pooled Spearman falls to 0.035. Table 231 lists every unit with its share on both bases and each rival under one definition.

**Table 231.** The 15 new units under one definition of each frozen rival (base share beta; escape fraction E; opening margin; novelty-instruction excess; twin modal share; catalogue size K; runtime merit, the natural log of the runtime of the default over that of the fastest reference). Source: record audit `tables/movability_units.csv`.

| Unit | In the 13 | beta (basis) | beta, correct only | E | Opening margin | Novelty excess | Twin modal share | K | Runtime merit | Twin off-default | Other share of base attempts |
|-|-|-|-|-|-|-|-|-|-|-|-|
| majority element | yes | 0.414 (correct) | 0.414 | 0.125 | -8.72 | 0.00 | 1.00 | 7 | 2.19 | 0.00 | n/a |
| maximum block sum | yes | 0.000 (correct) | 0.000 | 0.000 | 22.52 | 0.00 | 1.00 | 4 | 0.18 | 0.00 | n/a |
| trapped rain water | yes | 0.227 (correct) | 0.227 | 0.4375 | 5.21 | -0.36 | 0.64 | 4 | 2.43 | 0.36 | n/a |
| count primes | yes | 0.806 (correct) | 0.806 | 0.000 | -0.53 | 0.00 | 1.00 | 6 | -1.68 | 0.00 | n/a |
| longest common prefix | yes | 0.300 (correct) | 0.300 | 0.000 | 12.58 | 0.27 | 1.00 | 7 | 0.08 | 0.00 | n/a |
| longest mirrored substring | yes | 0.464 (correct) | 0.464 | 0.1875 | -36.88 | 0.00 | 1.00 | 4 | 2.34 | 0.00 | n/a |
| jump game | no (reserve) | 0.474 (correct) | 0.474 | 0.000 | 3.54 | 0.00 | 1.00 | 3 | -0.98 | 0.00 | n/a |
| median of two sorted lists | no (reserve) | 0.708 (correct) | 0.708 | 0.000 | 17.77 | 0.20 | 1.00 | 4 | 0.95 | 0.00 | n/a |
| missing number | yes | 0.056 (correct) | 0.056 | 0.000 | 3.58 | 0.00 | 1.00 | 5 | -0.25 | 0.00 | 0.033 |
| single number | yes | 0.565 (correct) | 0.565 | 0.4375 | 25.37 | -0.08 | 0.92 | 4 | 0.27 | 0.08 | 0.078 |
| minimum spanning tree weight | yes | 0.107 (correct) | 0.107 | 0.125 | 26.89 | -0.07 | 0.66 | 4 | -0.26 | 0.34 | 0.247 |
| integer square root | yes | 0.368 (correct) | 0.368 | 0.125 | 13.99 | 0.00 | 1.00 | 6 | 0.35 | 0.00 | 0.083 |
| all subsets | yes | 0.370 (correct) | 0.370 | 0.000 | 18.92 | 0.00 | 1.00 | 4 | 0.09 | 0.00 | 0.020 |
| valid anagram | yes | 0.806 (correct) | 0.806 | 0.000 | -7.57 | 0.76 | 0.76 | 3 | 0.20 | 0.24 | 0.072 |
| count inversions | yes | 0.747 (attempt) | 0.133 | 0.3125 | -8.85 | 0.33 | 1.00 | 4 | 0.39 | 0.00 | 0.667 |

The preregistered rule required beta to be ahead of each rival. Computed under one definition on the 13 units, with signs fixed so that the predicted direction is positive, only runtime merit tracks movability after Holm correction (Table 232), and the paired interval for beta minus runtime merit still includes 0.

**Table 232.** The frozen rivals on the 13 new units: Spearman with the escape fraction, one-sided permutation p, the paired difference beta minus rival with its bootstrap 95% interval, and Holm p. Source: record audit `tables/rival_scores.csv`.

| Rival | Predicted sign | Spearman with E | One-sided p | beta minus rival [95% CI] | Holm p |
|-|-|-|-|-|-|
| opening margin | negative | 0.079 | 0.399 | 0.067 [-0.66, 0.88] | 1.0 |
| novelty-instruction excess | positive | -0.503 | 0.960 | 0.649 [-0.06, 1.34] | 1.0 |
| runtime merit | positive | 0.713 | 0.004 | -0.568 [-1.26, 0.20] | 0.021 |
| twin modal share | negative | 0.409 | 0.087 | -0.263 [-1.05, 0.56] | 0.347 |
| catalogue size | positive | -0.206 | 0.753 | 0.352 [-0.57, 1.24] | 1.0 |

### 6.2.5 Executed outputs added to the record

The audit added the outputs the review listed, each in place and marked: the phrasing clusters per temperature in the literal cell (Table 206: 2/4/8, 3/3/10, 2/3/9 and 5/7/12 at theta 0.7/0.8/0.9 for temperatures 0.3, 0.7, 1.0 and 1.3, and 3/6/10 for the repeat at 0.7, so at N = 20 with thinking on a rise shows only at 1.3 and is the size of the repeat noise); Table 207b, the pass cost at which each knob first reaches a correct-only Hill-1 of 1.5 and of 2, with bootstrap intervals; Table 203b, panel B's knob rows, where on minimum spanning tree weight temperature 1.3 already gives Prim 18 of 49 correct programs against 20 of 50 under plan noise, because the twin itself is mixed; and the three Llama present-minor ban rows of Table 126c (Hill-1 2.87, 2.96 and 2.92 at pass costs of -12 to -27 points). Panel B's pushes stayed inside the base repertoire on 6 of 7 units; on count inversions 3 pushed programs implemented a Fenwick tree that the base model never wrote. Per task, plan noise against matched decoding at alpha 2 is 13:0 on kth smallest and 6:3 on the other four tasks together (p 0.508), with connected components at 1:3 (Table 233).

**Table 233.** Plan noise against decoding at matched per-token KL: slots correct and off the default under one arm only. Source: record audit `tables/pn_vs_dmd_discordant.csv`.

| Task | Alpha 1: plan noise only / matched decoding only (exact p) | Alpha 2: plan noise only / matched decoding only (exact p) |
|-|-|-|
| kth smallest | 3 / 0 (0.25) | 13 / 0 (0.00024) |
| connected components | 1 / 2 (1.0) | 1 / 3 (0.625) |
| shortest path | 0 / 1 (1.0) | 2 / 0 (0.5) |
| two sum | 0 / 0 (1.0) | 2 / 0 (0.5) |
| grid | 0 / 0 (1.0) | 1 / 0 (1.0) |
| pooled | 4 / 3 (1.0) | 19 / 3 (0.00086) |

### 6.2.6 A second blind adjudication of the 14 disputed programs

In iteration 5 two of three judges had called 14 of the 48 correct transplant programs outside the catalogue novel, and the zero count rested on a manual read by the executor. The audit stress-tested each program in a sandbox at the maximum size of the specification and on adversarial cases, retrieved its three nearest known solutions by Zhang-Shasha tree edit distance [64], and had two judges from model families the run had never used classify it blind: Mistral Medium 3.1 (three calls at temperature 0, Fleiss kappa [128] 1.00 across the calls) and Kimi (kimi-k2, Moonshot AI). Ten controls of known class were mixed in, and both judges passed the control gate at 9 of 10. All 14 programs pass their hidden tests; one, a repeated maximum selection on top-k frequent, times out at the maximum size. Mistral called 1 of 14 novel and Kimi 0 of 14 (Table 234). The one program called novel, a first-and-last-position solution, is range guards plus a linear scan to the first match and over its run; it passes 56 of 56 hidden tests and every stress group, and a full read by the executor classes it as a linear search. The final count is 0 novel of 14. Agreement with the manual verdict on the 14 is 0.86 raw (95% interval 0.57 to 0.98), Gwet's AC1 [127] 0.83 and a Cohen kappa of 0.71; with the controls included (24 items) kappa is 0.80 [0.57, 1.00]. The final read corrected one manual class: one first-and-last-position program, a linear scan plus a count of each element, is degenerate rather than a catalogue variant.

**Table 234.** The 14 disputed transplant programs: task, iteration-5 manual class, the majority class of Mistral Medium 3.1 (three calls), the class given by Kimi, and the final class. Source: record audit `tables/novelty_readjudication.csv`, `audit/final_read.json`.

| Program | Task | Iteration-5 manual class | Mistral Medium 3.1 | Kimi | Final class |
|-|-|-|-|-|-|
| 1 | first and last position | known, outside the catalogue | known, outside the catalogue (linear search) | known, outside the catalogue | known, outside the catalogue |
| 2 | first and last position | degenerate | degenerate | degenerate | degenerate |
| 3 | first and last position | known, outside the catalogue | known, outside the catalogue | known, outside the catalogue | known, outside the catalogue |
| 4 | first and last position | known, outside the catalogue | known, outside the catalogue | known, outside the catalogue | known, outside the catalogue |
| 5 | first and last position | catalogue variant | degenerate | degenerate | degenerate (corrected) |
| 6 | first and last position | known, outside the catalogue | novel (3 of 3 calls) | known, outside the catalogue | known, outside the catalogue (linear search) |
| 7 | first and last position | known, outside the catalogue | known, outside the catalogue | known, outside the catalogue | known, outside the catalogue |
| 8 | first and last position | known, outside the catalogue | known, outside the catalogue | known, outside the catalogue | known, outside the catalogue |
| 9 | first and last position | known, outside the catalogue | known, outside the catalogue | known, outside the catalogue | known, outside the catalogue |
| 10 | first and last position | known, outside the catalogue | known, outside the catalogue | known, outside the catalogue | known, outside the catalogue |
| 11 | first and last position | known, outside the catalogue | known, outside the catalogue | known, outside the catalogue | known, outside the catalogue |
| 12 | connected components | catalogue variant | catalogue variant (union find) | known, outside the catalogue | catalogue variant |
| 13 | top-k frequent | catalogue variant | catalogue variant (sort by count) | catalogue variant | catalogue variant |
| 14 | top-k frequent | known, outside the catalogue | known, outside the catalogue (binary search on a frequency threshold) | known, outside the catalogue | known, outside the catalogue |

Across four judge passes the novel calls of Mistral on the 14 were 0, 0, 1 and 1, and those of Kimi 0 in every pass; the first two passes carried run-dependent timings in their prompts. No pass produced a novel call that survived a full read.


## 6.3 The engine control: are the random-push escapes a property of the model or of 8-bit rounding?

**Why.** The engine claim was the primary test of the iteration, because its answer decides which internal results of iteration 4 belong to Qwen3-8B. The review had pointed at a plausible mechanism without establishing it: a displacement changes the per-token absmax of each linear input, so under dynamic per-token 8-bit floating-point scaling it changes the rounding of every downstream activation, and the engine adds its own perturbation to the push. The 8-bit floating-point format in question is e4m3, with a maximum of 448 [115]. The engine control [ARTIFACT:art_lpQalcAXMGr1] separated weight rounding from activation rounding by running iteration 4's own design under four numerics, all built from one bf16 snapshot of Qwen3-8B (Table 235).

**Table 235.** The four numerics of the engine control.

| Engine | Weights | Activations | Role |
|-|-|-|-|
| W8A8 | e4m3, per-output-channel absmax / 448 | e4m3, per-token absmax / 448 | iteration 4's engine (native 8-bit floating-point matrix multiply) |
| W8A16 | e4m3, the same codes | bf16 | weight rounding only |
| W16A8 | bf16 | e4m3, fake-quantised per token | activation rounding only |
| bf16 | bf16 | bf16 | full-precision reference |

**Design.** Everything except the numerics was held fixed: the 40 direction files of iteration 4 (seeds 9101 to 9140, checked bitwise), the absolute displacement per block and position at blocks 12 to 23 and the task-specification positions (the bench unit of iteration 4), the twin prompts, the common-random-number slots and uniforms, the stop rule, a 1,024-token cap, one labeller version (that of iteration 4 plus the iteration-5 re-gate that reads array-based Dijkstra correctly) applied to every row, and the two-stage escape rule of iteration 4, with each engine scored against its own twin. The W8A8 engine first regenerated the rows of iteration 4 on the same GPU model, driver and library versions: 400 of 400 programs of the plan-subspace experiment and 40 of 40 per-sample plan-noise programs came out byte-identical, the realised downstream displacement had ratio 1.000, and per-slot label agreement was 1.0. Under the reuse rule committed before sampling, the rows of iteration 4 therefore stand in for the W8A8 engine on every other cell. The bf16 twins reproduce the bf16 twin composition of iteration 5 (connected components union find 50 of 50; shortest path Dijkstra 49, Bellman-Ford/SPFA 1). The direction screen ran at alpha 2 on connected components and shortest path, and per-sample plan noise at alpha 1 and 2; the alpha-1 direction arms of the two single-factor engines, a Gaussian mimic of the 8-bit noise and kth smallest were dropped by the committed drop order, and the W8A16 engine ran on a slower cast path because the fused kernel could not be compiled.

**bf16 escapes on almost the same directions.** At the same absolute displacement the bf16 engine escapes on 26 of 40 directions on connected components and 6 of 40 on shortest path, against 29 and 8 under W8A8 (Table 236). The direction-level discordance is 3:0 and 4:2 (exact McNemar p 0.25 and 0.69), the per-direction off-default shares rank alike (Spearman 0.96 and 0.87; kappa on escape 0.83 and 0.48), and permuting the pairing of directions drops kappa to about 0. The committed verdict on both tasks is the rule's outcome for a high escape fraction that 8-bit rounding does not explain: W8A8 minus bf16 is below 0.1 and bf16 is within 0.15 of iteration 4's escape fraction, so bf16 escapes too and the account specific to 8-bit rounding is not reproduced. Table 237 pairs every two engines direction by direction. The low escape fraction on shortest path is a pass-rate effect common to both engines: in each, 17 of 40 directions reach the +0.20 off-default excess but fail the pass clause, because the pushed Bellman-Ford/SPFA programs often fail the hidden tests.

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

**Per-sample plan noise reproduces in bf16 at the matched unit.** On the slots, uniforms and per-sample direction seeds that iteration 4 used, at the same absolute unit, bf16 plan noise moves connected components in 25 of 50 valid attempts at alpha 2 and shortest path in 22 of 50, against 30 and 22 under W8A8 (Table 238). The realised displacement at block 12, the first edited block, is 13.75 in the bf16 rows at alpha 2 and 13.76 in the rows of iteration 4. The bf16 plan noise of iteration 5 had moved connected components in 1 of 50 programs at alpha 1 and at alpha 2 on the same prompts and uniforms, but at the ban-free unit and with other direction seeds. The size of the push alone does not explain that null: the alpha-2 displacement of iteration 5 at block 12 (9.07) exceeds the bf16 alpha-1 displacement of this control (6.88), which still moves 7 of 50. The difference lies in the profile of the ban-free unit over positions and blocks, or in the direction seeds; which of the two matters was not tested.

**Table 238.** Per-sample plan noise per engine on the slots of iteration 4 at the absolute unit (valid attempts on a catalogue alternative to the default, over 50; programs labelled other are not counted). One labeller, including the iteration-5 re-gate of the shortest path rule, scores every engine, so the shortest path cells of iteration 4 read 12 and 22 of 50 here against 13 and 27 in the all-samples count of the audit (Table 228), which counts programs labelled other and predates the re-gate. Source: engine control `results/pn.json`, `data/samples.jsonl`.

| Task | Arm | Iteration-4 8-bit rows | W8A8 | W8A16 | W16A8 | bf16 | Paired discordance W8A8 : bf16 |
|-|-|-|-|-|-|-|-|
| connected components | alpha 1 | 6/50 (0.12) | 6/50 (0.12) | 9/50 (0.18) | 4/50 (0.08) | 7/50 (0.14) | 1:2 |
| connected components | alpha 2 | 30/50 (0.60) | 30/50 (0.60) | 27/50 (0.54) | 22/50 (0.44) | 25/50 (0.50) | 6:1 (p 0.13) |
| shortest path | alpha 1 | 12/50 (0.24) | 12/50 (0.24) | 11/50 (0.22) | 11/50 (0.22) | 10/50 (0.20) | 4:2 |
| shortest path | alpha 2 | 22/50 (0.44) | 22/50 (0.44) | 19/50 (0.38) | 18/50 (0.36) | 22/50 (0.44) | 8:8 |

[FIGURE:fig_engine_escape]

**The 8-bit engine adds a small boost on connected components, and activation rounding is not its source.** Pairing every pushed sample with the same slot (direction, template, slot index and uniforms) in the other engine, on the 400 screen slots of the first two samples of all 40 directions, W8A8 is off the default in 58.3% of slots against 53.2% under bf16 on connected components (discordant 30:10, exact McNemar p 0.0022), and 43.2% against 40.7% on shortest path (55:45, p 0.37) (Table 239). The factorial locates the boost. Activation rounding alone (W16A8) sits slightly below bf16 on connected components (49.7% against 53.2%, 9:23, p 0.02); weight rounding alone (W8A16) sits between bf16 and W8A8 (55.6%; 17:7 against bf16, p 0.06). The small boost therefore comes from the e4m3 weights, from the native kernel's reduced-precision accumulation (it matches an exact fp64 reference on 94.2% of outputs, against 99.96% for an exact emulation), or from their interaction. The landing algorithms do not change: correct off-default programs are DFS, then BFS, on connected components and Bellman-Ford/SPFA on shortest path under every engine, with compositions compatible across engines (permutation chi-squared p 0.22 and 0.94; Table 240).

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

**Table 241.** Teacher-forced divergence from bf16 on 40 iteration-4 twin programs, and the failed fidelity check (median absolute difference between the summed log probability of a program and the value recorded in iteration 4). Source: engine control `results/diagnostics_summary.json`.

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
| Iteration 5: shortest path no longer movable in bf16 | not reproduced at the absolute unit | bf16 escape fraction 6/40 confirmed escapes |
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


## 6.4 Where a ban and an instruction are carried, and where noise acts, in bf16 (Qwen3-8B)

**Why.** The localization claim predicted, from the route classes of iterations 2 and 3, where the substitute of a ban is carried: in the task-specification states on the prompt-route tasks, at the condition span on the direct-route tasks. Stage A tests that prediction without any training, by moving the states themselves. The same experiment [ARTIFACT:art_rMlbrjVB1c__] reran the iteration-4 noise-site comparison in bf16, set state noise at generated tokens against a temperature matched on per-token KL, applied the top-five plan push, and ran the landing contest. Everything ran in one bf16 engine with exact common random numbers on a 16 GB card, with the input embedding table kept in CPU memory; per-slot twin labels agreed with iteration 5's bf16 engine on 0.975 of slots for kth smallest and shortest path and 1.00 for the other tasks. Seven commitments formed an unbroken sha256 chain, and a standard-library script re-derived every headline from raw rows (295 checks, 0 mismatches) while a placebo version of each test failed.

### 6.4.1 Stage A: full-state exchange of the ban

We call a *full-state exchange* the replacement, in the forward pass of the neutral twin, of the residual states at a set of positions and blocks by the states the full ban prompt produces at the same positions; because the twin and the ban have identical token ids from the task text on, every task-specification position aligns. The exchanges covered four block bands at the task-specification positions (0 to 11, 12 to 23, 24 to 35, 0 to 35), a splice of the key-value cache of the condition span (the direct route), and the read position at all 36 blocks. The controls were the twin, a matched-norm random exchange (the state of the twin plus a fresh random direction scaled to the displacement that the ban itself causes per slot, block and position), a placebo that takes a second neutral twin as the source, and an identity exchange. The outcome is the share of correct programs implementing the substitute Y of the ban; the *transfer* of a cell is its Y share minus that of the twin, and its *recovery* is the transfer divided by that of the full ban. Each cell has N = 30 on paired slots. Tables 244 to 249 give every cell on the six tasks.

The prediction held where the route data said it should, and failed at one task where they said it should not. On shortest path, exchanging the full ban's task-specification states at all blocks into the twin turns 24 of 30 slots from Dijkstra to Bellman-Ford/SPFA (transfer 0.80, McNemar 24:0, Holm p 7e-7, pass ratio 0.90), while the condition-span splice and the read-position exchange transfer nothing. Blocks 12 to 23 alone carry 0.60 and blocks 24 to 35 alone 0.37; blocks 0 to 11 carry none. On kth smallest the same exchange transfers 0.57 to quickselect with every slot leaving the full sort, blocks 0 to 11 alone already transfer 0.40, and here the condition span also carries the ban (0.93). On connected components every slot leaves union find under the exchange at blocks 12 to 23 or 0 to 35 (off-default transfer 1.00), but only 0.37 to 0.47 land on the ban's BFS and the rest on DFS. On the grid task, whose route was carried by the prompt states in likelihood and mixed in behaviour, the exchange at all blocks transfers 0.47 toward DFS and the condition-span splice 0.33, so each carries part of the ban. On the direct-route tasks the condition-span splice alone reproduces the ban (two sum 1.00, find duplicate 0.90), as predicted, but on two sum the task-specification states also transfer brute force at 0.43, above the predicted ceiling of 0.2. The committed verdict is therefore not supported. The secondary predictions hold: the condition span carries at least 0.5 on the direct-route tasks and at most 0.2 on shortest path, the read position carries at most 0.2 everywhere (it carries 0.00 on all six tasks), the placebo moves at most 0.03, and the exchange beats the matched-norm random exchange where it transfers (shortest path 23:0, kth smallest 16:2, connected components 11:0). The ban's information, not the size of the perturbation, is what moves the algorithm.

[FIGURE:fig_exchange_transfer]

**Table 244.** Stage A on kth smallest (default full sort; Y = quickselect; route class from iterations 2 and 3: either route suffices). Twin on slots 0 to 29: Y share 0.00, off-default 0.00, pass 1.00, full sort 30. Exchange at blocks 0-35 against the matched-norm random exchange: 16:2, exact p 0.0013 (Holm 0.0020). Source: exchange and site experiment `results/stage_a.json`, `results/summary.md`.

| Cell | n | Y share [CP 95%] | Transfer | Off-default transfer | Pass ratio | Recovery | Slot interchange intervention accuracy | McNemar b:c (p, Holm) | Correct composition |
|-|-|-|-|-|-|-|-|-|-|
| full ban | 30 | 0.67 [0.47, 0.83] | 0.67 | 1.00 | 0.93 | 1.00 | 1.00 | 20:0 (1.9e-06, 1.9e-06) | quickselect 18, size-k heap 10 |
| exchange, blocks 0-11 | 30 | 0.40 [0.23, 0.59] | 0.40 | 0.53 | 1.00 | 0.60 | 0.33 | 12:0 (4.9e-04, 0.003) | full sort 14, quickselect 12, size-k heap 4 |
| exchange, blocks 12-23 | 30 | 0.57 [0.37, 0.75] | 0.57 | 1.00 | 0.93 | 0.85 | 0.90 | 17:0 (1.5e-05, 7.6e-05) | quickselect 15, size-k heap 13 |
| exchange, blocks 24-35 | 30 | 0.03 [8.4e-04, 0.17] | 0.03 | 0.03 | 1.00 | 0.05 | 0.03 | 1:0 (1.000, 1.000) | full sort 29, quickselect 1 |
| exchange, blocks 0-35 | 30 | 0.57 [0.37, 0.75] | 0.57 | 1.00 | 0.97 | 0.85 | 0.90 | 17:0 (1.5e-05, 7.6e-05) | quickselect 16, size-k heap 13 |
| condition-span splice | 30 | 0.93 [0.78, 0.99] | 0.93 | 1.00 | 0.90 | 1.40 | 0.60 | 28:0 (7.5e-09, 3.7e-08) | quickselect 25, size-k heap 2 |
| read-position exchange | 30 | 0.00 [0.00, 0.12] | 0.00 | 0.00 | 1.00 | 0.00 | 0.00 | 0:0 (1.000, 1.000) | full sort 30 |
| matched-norm random exchange, blocks 0-35 | 30 | 0.10 [0.02, 0.27] | 0.10 | 0.10 | 1.00 | 0.15 | 0.03 | 3:0 (0.250, 0.750) | full sort 27, quickselect 3 |
| matched-norm random exchange, blocks 12-23 | 30 | 0.13 [0.04, 0.31] | 0.13 | 0.13 | 1.00 | 0.20 | 0.00 | 4:0 (0.125, 0.375) | full sort 26, quickselect 4 |
| placebo twin | 30 | 0.03 [8.4e-04, 0.17] | 0.03 | 0.03 | 1.00 | 0.05 | 0.00 | 1:0 (1.000, 1.000) | full sort 29, quickselect 1 |

**Table 245.** Stage A on connected components (default union find; Y = BFS). Twin: Y share 0.00, off-default 0.00, pass 1.00, union find 30. Exchange at blocks 0-35 against the matched-norm random exchange: 11:0, exact p 9.8e-4 (Holm 0.0020).

| Cell | n | Y share [CP 95%] | Transfer | Off-default transfer | Pass ratio | Recovery | Slot interchange intervention accuracy | McNemar b:c (p, Holm) | Correct composition |
|-|-|-|-|-|-|-|-|-|-|
| full ban | 30 | 0.90 [0.73, 0.98] | 0.90 | 1.00 | 1.00 | 1.00 | 1.00 | 27:0 (1.5e-08, 3.0e-08) | BFS 27, DFS 3 |
| exchange, blocks 0-11 | 30 | 0.00 [0.00, 0.12] | 0.00 | 0.87 | 0.70 | 0.00 | 0.10 | 0:0 (1.000, 1.000) | DFS 17, union find 4 |
| exchange, blocks 12-23 | 30 | 0.47 [0.28, 0.66] | 0.47 | 1.00 | 1.00 | 0.52 | 0.43 | 14:0 (1.2e-04, 4.9e-04) | DFS 16, BFS 14 |
| exchange, blocks 24-35 | 30 | 0.00 [0.00, 0.12] | 0.00 | 0.63 | 1.00 | 0.00 | 0.10 | 0:0 (1.000, 1.000) | DFS 19, union find 11 |
| exchange, blocks 0-35 | 30 | 0.37 [0.20, 0.56] | 0.37 | 1.00 | 1.00 | 0.41 | 0.40 | 11:0 (9.8e-04, 0.002) | DFS 19, BFS 11 |
| condition-span splice | 30 | 0.10 [0.02, 0.27] | 0.10 | 1.00 | 1.00 | 0.11 | 0.20 | 3:0 (0.250, 0.500) | DFS 27, BFS 3 |
| read-position exchange | 30 | 0.00 [0.00, 0.12] | 0.00 | 0.00 | 1.00 | 0.00 | 0.00 | 0:0 (1.000, 1.000) | union find 30 |
| matched-norm random exchange, blocks 0-35 | 30 | 0.00 [0.00, 0.12] | 0.00 | 0.07 | 1.00 | 0.00 | 0.00 | 0:0 (1.000, 1.000) | union find 28, DFS 2 |
| matched-norm random exchange, blocks 12-23 | 30 | 0.00 [0.00, 0.12] | 0.00 | 0.03 | 1.00 | 0.00 | 0.00 | 0:0 (1.000, 1.000) | union find 29, DFS 1 |
| placebo twin | 30 | 0.00 [0.00, 0.12] | 0.00 | 0.03 | 1.00 | 0.00 | 0.00 | 0:0 (1.000, 1.000) | union find 29, DFS 1 |

**Table 246.** Stage A on shortest path (default Dijkstra; Y = Bellman-Ford/SPFA; prompt route). Twin: Y share 0.00, off-default 0.00, pass 1.00, Dijkstra 30. Exchange at blocks 0-35 against the matched-norm random exchange: 23:0, exact p 2.4e-7 (Holm 7.2e-7).

| Cell | n | Y share [CP 95%] | Transfer | Off-default transfer | Pass ratio | Recovery | Slot interchange intervention accuracy | McNemar b:c (p, Holm) | Correct composition |
|-|-|-|-|-|-|-|-|-|-|
| full ban | 30 | 0.97 [0.83, 1.00] | 0.97 | 0.97 | 1.00 | 1.00 | 1.00 | 29:0 (3.7e-09, 1.5e-08) | Bellman-Ford/SPFA 29, Dijkstra 1 |
| exchange, blocks 0-11 | 30 | 0.00 [0.00, 0.12] | 0.00 | 0.00 | 1.00 | 0.00 | 0.03 | 0:0 (1.000, 1.000) | Dijkstra 30 |
| exchange, blocks 12-23 | 30 | 0.60 [0.41, 0.77] | 0.60 | 0.60 | 0.73 | 0.62 | 0.63 | 18:0 (7.6e-06, 4.6e-05) | Dijkstra 11, Bellman-Ford/SPFA 11 |
| exchange, blocks 24-35 | 30 | 0.37 [0.20, 0.56] | 0.37 | 0.37 | 1.00 | 0.38 | 0.40 | 11:0 (9.8e-04, 0.006) | Dijkstra 19, Bellman-Ford/SPFA 11 |
| exchange, blocks 0-35 | 30 | 0.80 [0.61, 0.92] | 0.80 | 0.80 | 0.90 | 0.83 | 0.83 | 24:0 (1.2e-07, 7.2e-07) | Bellman-Ford/SPFA 21, Dijkstra 6 |
| condition-span splice | 30 | 0.00 [0.00, 0.12] | 0.00 | 0.00 | 1.00 | 0.00 | 0.03 | 0:0 (1.000, 1.000) | Dijkstra 30 |
| read-position exchange | 30 | 0.00 [0.00, 0.12] | 0.00 | 0.00 | 1.00 | 0.00 | 0.03 | 0:0 (1.000, 1.000) | Dijkstra 30 |
| matched-norm random exchange, blocks 0-35 | 30 | 0.03 [8.4e-04, 0.17] | 0.03 | 0.03 | 0.97 | 0.03 | 0.07 | 1:0 (1.000, 1.000) | Dijkstra 29 |
| matched-norm random exchange, blocks 12-23 | 30 | 0.03 [8.4e-04, 0.17] | 0.03 | 0.03 | 0.93 | 0.03 | 0.07 | 1:0 (1.000, 1.000) | Dijkstra 28 |
| placebo twin | 30 | 0.03 [8.4e-04, 0.17] | 0.03 | 0.03 | 1.00 | 0.03 | 0.07 | 1:0 (1.000, 1.000) | Dijkstra 29, Bellman-Ford/SPFA 1 |

**Table 247.** Stage A on two sum (default hash map; Y = brute force; direct route). Twin: Y share 0.00, pass 1.00, hash map 30.

| Cell | n | Y share [CP 95%] | Transfer | Off-default transfer | Pass ratio | Recovery | Slot interchange intervention accuracy | McNemar b:c (p, Holm) | Correct composition |
|-|-|-|-|-|-|-|-|-|-|
| full ban | 30 | 1.00 [0.88, 1.00] | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 30:0 (1.9e-09, 1.1e-08) | brute force 30 |
| exchange, blocks 0-11 | 30 | 0.00 [0.00, 0.12] | 0.00 | 0.00 | 1.00 | 0.00 | 0.00 | 0:0 (1.000, 1.000) | hash map 30 |
| exchange, blocks 12-23 | 30 | 0.43 [0.25, 0.63] | 0.43 | 0.43 | 1.00 | 0.43 | 0.43 | 13:0 (2.4e-04, 7.3e-04) | hash map 17, brute force 13 |
| exchange, blocks 24-35 | 30 | 0.00 [0.00, 0.12] | 0.00 | 0.00 | 1.00 | 0.00 | 0.00 | 0:0 (1.000, 1.000) | hash map 30 |
| exchange, blocks 0-35 | 30 | 0.43 [0.25, 0.63] | 0.43 | 0.43 | 1.00 | 0.43 | 0.43 | 13:0 (2.4e-04, 7.3e-04) | hash map 17, brute force 13 |
| condition-span splice | 30 | 1.00 [0.88, 1.00] | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 30:0 (1.9e-09, 1.1e-08) | brute force 30 |
| read-position exchange | 30 | 0.00 [0.00, 0.12] | 0.00 | 0.00 | 1.00 | 0.00 | 0.00 | 0:0 (1.000, 1.000) | hash map 30 |

**Table 248.** Stage A on find duplicate (default hash set; Y = index marking; direct route). Twin: Y share 0.00, pass 1.00, hash set 30.

| Cell | n | Y share [CP 95%] | Transfer | Off-default transfer | Pass ratio | Recovery | Slot interchange intervention accuracy | McNemar b:c (p, Holm) | Correct composition |
|-|-|-|-|-|-|-|-|-|-|
| full ban | 30 | 0.97 [0.83, 1.00] | 0.97 | 1.00 | 0.87 | 1.00 | 1.00 | 29:0 (3.7e-09, 1.5e-08) | index marking 25, Floyd cycle detection 1 |
| exchange, blocks 0-11 | 30 | 0.00 [0.00, 0.12] | 0.00 | 0.00 | 1.00 | 0.00 | 0.00 | 0:0 (1.000, 1.000) | hash set 30 |
| exchange, blocks 12-23 | 30 | 0.00 [0.00, 0.12] | 0.00 | 0.10 | 1.00 | 0.00 | 0.03 | 0:0 (1.000, 1.000) | hash set 27, Floyd cycle detection 3 |
| exchange, blocks 24-35 | 30 | 0.00 [0.00, 0.12] | 0.00 | 0.00 | 1.00 | 0.00 | 0.00 | 0:0 (1.000, 1.000) | hash set 30 |
| exchange, blocks 0-35 | 30 | 0.03 [8.4e-04, 0.17] | 0.03 | 0.13 | 1.00 | 0.03 | 0.07 | 1:0 (1.000, 1.000) | hash set 26, Floyd cycle detection 2, index marking 1, sort and adjacent check 1 |
| condition-span splice | 30 | 0.90 [0.73, 0.98] | 0.90 | 0.90 | 0.97 | 0.93 | 0.90 | 27:0 (1.5e-08, 6.0e-08) | index marking 26, hash set 3 |
| read-position exchange | 30 | 0.00 [0.00, 0.12] | 0.00 | 0.00 | 1.00 | 0.00 | 0.00 | 0:0 (1.000, 1.000) | hash set 30 |

**Table 249.** Stage A on the grid task (default BFS; Y = DFS; prompt route in likelihood, mixed in behaviour). Twin: Y share 0.00, pass 0.90, BFS 27 correct. Pass ratios above 1 occur because the twin's own pass rate is below 1.

| Cell | n | Y share [CP 95%] | Transfer | Off-default transfer | Pass ratio | Recovery | Slot interchange intervention accuracy | McNemar b:c (p, Holm) | Correct composition |
|-|-|-|-|-|-|-|-|-|-|
| full ban | 30 | 1.00 [0.88, 1.00] | 1.00 | 1.00 | 0.44 | 1.00 | 1.00 | 30:0 (1.9e-09, 1.1e-08) | DFS 12 |
| exchange, blocks 0-11 | 30 | 0.00 [0.00, 0.12] | 0.00 | 0.00 | 1.11 | 0.00 | 0.00 | 0:0 (1.000, 1.000) | BFS 30 |
| exchange, blocks 12-23 | 30 | 0.37 [0.20, 0.56] | 0.37 | 0.37 | 0.63 | 0.37 | 0.37 | 11:0 (9.8e-04, 0.002) | BFS 15, DFS 2 |
| exchange, blocks 24-35 | 30 | 0.03 [8.4e-04, 0.17] | 0.03 | 0.03 | 0.81 | 0.03 | 0.03 | 1:0 (1.000, 1.000) | BFS 22 |
| exchange, blocks 0-35 | 30 | 0.47 [0.28, 0.66] | 0.47 | 0.47 | 0.59 | 0.47 | 0.47 | 14:0 (1.2e-04, 4.9e-04) | BFS 13, DFS 3 |
| condition-span splice | 30 | 0.33 [0.17, 0.53] | 0.33 | 0.33 | 0.89 | 0.33 | 0.33 | 10:0 (0.002, 0.006) | BFS 17, DFS 7 |
| read-position exchange | 30 | 0.00 [0.00, 0.12] | 0.00 | 0.00 | 0.96 | 0.00 | 0.00 | 0:0 (1.000, 1.000) | BFS 26 |

The condition-span splice also matches the behavioural route arms of iteration 3: its recovery is 1.00 on two sum and 0.93 on find duplicate, where the direct-route fraction of iteration 3 was 0.96 and 0.99, and 1.40 on kth smallest (direct-route fraction 0.74). On connected components its recovery toward BFS is 0.11, although every slot leaves union find: either route alone removes the default and lands on DFS, as the route landings of iteration 4 had shown.

**Positive instructions are carried the same way.** As an extension, the forced prompt `Implement Bellman-Ford or SPFA for this task.` replaced the ban as the source (Table 250). Its padding twin, the same prompt with the tokens of the instruction replaced by padding, stays on Dijkstra in 29 of 30 programs; exchanging only the task-specification states of the forced prompt at all blocks into that twin gives Bellman-Ford/SPFA in 30 of 30. On connected components the states of the forced BFS prompt give BFS in 28 of 30 against union find 30 of 30 for its twin. The shortest path semantic seed, which moved that task 66 points in iteration 1, moved nothing under this frame (Dijkstra 30 of 30), and neither did its exchange (2 of 30). The fourth ban template, held out of every other cell, transfers through the exchange as the other templates do (shortest path 0.70, kth smallest 0.60 on quickselect with every slot off the full sort, connected components 0.70, N = 10 each).

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

The unit tests of Stage A passed except one: splicing the cache of the task-specification span reproduced the top token of the exchange with a logit gap of 0.5 in bf16 and 10 of 10 equal labels, but not byte for byte. The Stage A arms on trapped rain water and minimum spanning tree weight were dropped for GPU time.

### 6.4.2 Where noise acts, in bf16

The site rerun repeated iteration 4's grid on kth smallest and connected components in bf16, at the ban-free unit, with a fresh direction per sample, N = 30 per cell and alpha 1, 2, 4 and 8 (Tables 251 and 252). Noise at the task-specification positions moves the algorithm in bf16: on kth smallest blocks 12 to 23 reach a correct off-default share of 0.37 at alpha 2, and on connected components blocks 0 to 11 reach 0.33 at alpha 4. The read position, the condition span and the late blocks barely move it below alpha 8. On kth smallest the plan site (the task-specification states at blocks 12 to 23, as in iteration 4) beats the read position in paired slots 24:5 (exact p 5.5e-4) and the condition span 22:0, and a Mantel-Haenszel odds ratio [129] within quintiles of the downstream displacement is 4.6 [1.9, 11.3]. Connected components shows a weaker picture: its plan site moves only 0.07 at alpha 2 and 0.17 at alpha 4, the early blocks beat it (4:18, p 0.004), and the read position starts moving at alpha 8 (0.30).

The committed rule fitted a Firth logistic regression [125] of a correct off-default program on site indicators and the log displacements, so that sites are compared at matched downstream displacement (Tables 253 and 254). It returned the verdict withdrawn, for two reasons. The raw condition-span arm never reaches the plan site's downstream displacement, so it has no common support and its energy-matched arm stood in; and at alpha 8 every plan-site program failed (pass 0.00) while the read position began to move, which erases the read-position contrast in the preregistered model. A post-hoc sensitivity restricted to alpha of 4 or less (before breakage) puts the read position clearly below the plan site on both tasks: beta -3.76 (profile interval [-7.29, -0.47], cluster bootstrap [-8.18, -1.40]) on kth smallest and -4.98 ([-9.77, -0.89]; [-11.48, -1.53]) on connected components. The prefill-site claim is therefore withdrawn as preregistered, and its post-hoc form survives in bf16 at the ban-free unit.

**Table 251.** The bf16 site grid on kth smallest (twin correct off-default 0.00; displacements are medians in residual units at block 35). Source: exchange and site experiment `results/site_grid.json`.

| Site | Alpha | n | Correct off-default | Off-default | Pass | Median displacement at the read position, block 35 | Median displacement at generated token 1, block 35 | Correct composition |
|-|-|-|-|-|-|-|-|-|
| spec, blocks 12-23 | 1 | 30 | 0.13 | 0.13 | 1.00 | 1.708 | 1.315 | full sort 26, quickselect 3, size-k heap 1 |
| spec, blocks 12-23 | 2 | 30 | 0.37 | 0.37 | 1.00 | 3.353 | 2.478 | full sort 19, quickselect 8, size-k heap 3 |
| spec, blocks 12-23 | 4 | 30 | 0.33 | 0.40 | 0.87 | 6.293 | 4.628 | full sort 16, size-k heap 5, quickselect 5 |
| spec, blocks 12-23 | 8 | 30 | 0.00 | 0.10 | 0.00 | 12.230 | 7.135 | - |
| read position | 1 | 30 | 0.03 | 0.03 | 1.00 | 1.876 | 0.628 | full sort 29, quickselect 1 |
| read position | 2 | 30 | 0.03 | 0.03 | 1.00 | 3.591 | 1.201 | full sort 29, quickselect 1 |
| read position | 4 | 30 | 0.00 | 0.00 | 1.00 | 6.840 | 2.290 | full sort 30 |
| read position | 8 | 30 | 0.13 | 0.13 | 0.93 | 10.654 | 3.466 | full sort 24, quickselect 3, size-k heap 1 |
| read position, energy-matched | 2 | 30 | 0.07 | 0.07 | 0.77 | 16.426 | 3.870 | full sort 21, quickselect 1, size-k heap 1 |
| read position, energy-matched | 4 | 30 | 0.03 | 0.07 | 0.93 | 25.287 | 3.845 | full sort 27, heapify and pop 1 |
| condition span | 1 | 30 | 0.00 | 0.00 | 1.00 | 0.303 | 0.245 | full sort 30 |
| condition span | 2 | 30 | 0.07 | 0.07 | 1.00 | 0.415 | 0.289 | full sort 28, quickselect 2 |
| condition span | 4 | 30 | 0.03 | 0.03 | 1.00 | 0.674 | 0.424 | full sort 29, quickselect 1 |
| condition span | 8 | 30 | 0.00 | 0.00 | 1.00 | 1.056 | 0.606 | full sort 30 |
| condition span, energy-matched | 2 | 30 | 0.00 | 0.00 | 1.00 | 1.220 | 0.664 | full sort 30 |
| condition span, energy-matched | 4 | 30 | 0.00 | 0.00 | 1.00 | 1.110 | 0.646 | full sort 30 |
| generated tokens 1-32 | 1 | 30 | 0.17 | 0.17 | 1.00 | - | - | full sort 25, quickselect 5 |
| generated tokens 1-32 | 2 | 50 | 0.26 | 0.34 | 0.94 | - | - | full sort 33, quickselect 12, size-k heap 1, other 1 |
| generated tokens 1-32 | 4 | 50 | 0.18 | 0.42 | 0.50 | - | - | full sort 15, quickselect 4, heapify and pop 3, size-k heap 2 |
| generated tokens 1-32 | 8 | 30 | 0.00 | 0.00 | 0.13 | - | - | full sort 4 |
| spec, blocks 0-11 | 1 | 30 | 0.03 | 0.03 | 1.00 | 0.956 | 0.728 | full sort 29, quickselect 1 |
| spec, blocks 0-11 | 2 | 30 | 0.17 | 0.17 | 1.00 | 1.832 | 1.320 | full sort 25, quickselect 3, size-k heap 2 |
| spec, blocks 0-11 | 4 | 30 | 0.37 | 0.37 | 1.00 | 3.576 | 2.512 | full sort 19, size-k heap 9, quickselect 2 |
| spec, blocks 0-11 | 8 | 30 | 0.00 | 0.13 | 0.10 | 16.027 | 8.332 | full sort 3 |
| spec, blocks 24-35 | 1 | 30 | 0.00 | 0.00 | 1.00 | 0.909 | 0.654 | full sort 30 |
| spec, blocks 24-35 | 2 | 30 | 0.03 | 0.03 | 1.00 | 1.777 | 1.261 | full sort 29, size-k heap 1 |
| spec, blocks 24-35 | 4 | 30 | 0.03 | 0.03 | 1.00 | 3.270 | 2.307 | full sort 29, quickselect 1 |
| spec, blocks 24-35 | 8 | 30 | 0.10 | 0.10 | 1.00 | 5.119 | 3.323 | full sort 27, quickselect 3 |

**Table 252.** The bf16 site grid on connected components (twin correct off-default 0.00).

| Site | Alpha | n | Correct off-default | Off-default | Pass | Median displacement at the read position, block 35 | Median displacement at generated token 1, block 35 | Correct composition |
|-|-|-|-|-|-|-|-|-|
| spec, blocks 12-23 | 1 | 30 | 0.00 | 0.00 | 1.00 | 1.694 | 1.315 | union find 30 |
| spec, blocks 12-23 | 2 | 30 | 0.07 | 0.07 | 1.00 | 3.281 | 2.537 | union find 28, DFS 2 |
| spec, blocks 12-23 | 4 | 30 | 0.17 | 0.17 | 1.00 | 6.322 | 4.829 | union find 25, DFS 3, BFS 2 |
| spec, blocks 12-23 | 8 | 30 | 0.00 | 0.13 | 0.00 | 12.977 | 7.182 | - |
| read position | 1 | 30 | 0.00 | 0.00 | 1.00 | 1.800 | 0.606 | union find 30 |
| read position | 2 | 30 | 0.00 | 0.00 | 1.00 | 3.700 | 1.197 | union find 30 |
| read position | 4 | 30 | 0.03 | 0.03 | 1.00 | 7.200 | 2.234 | union find 29, DFS 1 |
| read position | 8 | 30 | 0.30 | 0.30 | 0.93 | 10.392 | 3.645 | union find 19, DFS 8, BFS 1 |
| read position, energy-matched | 2 | 30 | 0.03 | 0.03 | 0.77 | 15.570 | 4.091 | union find 22, DFS 1 |
| read position, energy-matched | 4 | 30 | 0.07 | 0.07 | 0.83 | 22.781 | 4.019 | union find 23, DFS 2 |
| condition span | 1 | 30 | 0.00 | 0.00 | 1.00 | 0.285 | 0.238 | union find 30 |
| condition span | 2 | 30 | 0.00 | 0.00 | 1.00 | 0.395 | 0.278 | union find 30 |
| condition span | 4 | 30 | 0.00 | 0.00 | 1.00 | 0.620 | 0.371 | union find 30 |
| condition span | 8 | 30 | 0.00 | 0.00 | 1.00 | 0.931 | 0.557 | union find 30 |
| condition span, energy-matched | 2 | 30 | 0.00 | 0.00 | 1.00 | 1.003 | 0.568 | union find 30 |
| condition span, energy-matched | 4 | 30 | 0.00 | 0.00 | 1.00 | 1.163 | 0.618 | union find 30 |
| generated tokens 1-32 | 1 | 30 | 0.00 | 0.00 | 1.00 | - | - | union find 30 |
| generated tokens 1-32 | 2 | 50 | 0.14 | 0.20 | 0.92 | - | - | union find 39, DFS 7 |
| generated tokens 1-32 | 4 | 50 | 0.16 | 0.40 | 0.38 | - | - | union find 11, DFS 6, BFS 2 |
| generated tokens 1-32 | 8 | 30 | 0.00 | 0.00 | 0.17 | - | - | union find 5 |
| spec, blocks 0-11 | 1 | 30 | 0.03 | 0.03 | 1.00 | 0.910 | 0.747 | union find 29, DFS 1 |
| spec, blocks 0-11 | 2 | 30 | 0.20 | 0.20 | 1.00 | 1.717 | 1.308 | union find 24, DFS 6 |
| spec, blocks 0-11 | 4 | 30 | 0.33 | 0.37 | 0.97 | 3.315 | 2.467 | union find 19, DFS 6, BFS 4 |
| spec, blocks 0-11 | 8 | 30 | 0.13 | 0.33 | 0.13 | 16.291 | 9.122 | BFS 3, DFS 1 |
| spec, blocks 24-35 | 1 | 30 | 0.00 | 0.00 | 1.00 | 0.930 | 0.647 | union find 30 |
| spec, blocks 24-35 | 2 | 30 | 0.00 | 0.00 | 1.00 | 1.789 | 1.225 | union find 30 |
| spec, blocks 24-35 | 4 | 30 | 0.00 | 0.00 | 1.00 | 3.267 | 2.278 | union find 30 |
| spec, blocks 24-35 | 8 | 30 | 0.03 | 0.03 | 1.00 | 5.089 | 3.429 | union find 29, DFS 1 |

**Table 253.** Firth logistic regression with site indicators on kth smallest at matched downstream displacement (n 387, 48 events, 387 of 720 rows in common support; the condition span enters through its energy-matched arm). Mantel-Haenszel odds ratio, plan site against read position, within quintiles of the log displacement at the read position: 4.61 [1.87, 11.34]. Paired flips, plan site only : other site only: read position 24:5 (p 5.5e-4), condition span 22:0 (p 4.8e-7), blocks 0-11 17:9 (p 0.169), blocks 24-35 23:3 (p 8.8e-5), generated tokens 21:18 (p 0.749).

| Term | Beta | Profile 95% CI | Cluster bootstrap 95% CI |
|-|-|-|-|
| spec, blocks 0-11 (against spec, blocks 12-23) | 0.24 | [-0.54, 1.01] | - |
| spec, blocks 24-35 | -1.52 | [-2.74, -0.51] | - |
| read position | -0.17 | [-2.64, 2.33] | [-2.58, 2.21] |
| condition span (energy-matched arm) | -0.73 | [-5.71, 1.84] | [-2.12, 1.10] |
| log displacement at the read position | -1.92 | [-4.76, 0.77] | - |
| log displacement at generated token 1 | 1.97 | [-0.99, 5.03] | - |

**Table 254.** Firth logistic regression with site indicators on connected components (n 374, 32 events, 376 of 720 rows in common support). Mantel-Haenszel odds ratio, plan site against read position: 0.82 [0.31, 2.18]. Paired flips, plan site only : other site only: read position 7:10 (p 0.629), condition span 7:0 (p 0.016), blocks 0-11 4:18 (p 0.004), blocks 24-35 7:1 (p 0.070), generated tokens 7:9 (p 0.804).

| Term | Beta | Profile 95% CI | Cluster bootstrap 95% CI |
|-|-|-|-|
| spec, blocks 0-11 (against spec, blocks 12-23) | 2.51 | [1.39, 3.80] | - |
| spec, blocks 24-35 | -0.72 | [-3.03, 0.94] | - |
| read position | 1.14 | [-1.30, 3.64] | [-1.07, 3.24] |
| condition span (energy-matched arm) | 2.38 | [-2.72, 5.40] | [0.69, 5.18] |
| log displacement at the read position | 0.02 | [-2.94, 2.92] | - |
| log displacement at generated token 1 | 1.22 | [-1.87, 4.36] | - |

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

On the grid task, iteration 4's top-five direction (from the mean of the five banned centroids toward the mean of the survivors) was applied at the plan site at alpha 1, 2, 4 and 8 (Table 256). It breaks programs before it moves the algorithm: the pass rate falls from 0.67 to 0.30, 0.03 and 0.00, with at most one correct program other than BFS per cell, so the landing test could not be computed. Projected onto the plane of the first two principal components of the ten forced-prompt centroids (36% and 25% of their variance), the push leaves the forced-prompt manifold: already at alpha 1 it moves farther along the first component than the whole spread of the ten centroids. The prompt version of the top-five ban moves the task-specification states from below the centroid cloud into it, between the banned DFS and greedy best-first centroids and the three surviving centroids (bidirectional BFS and two variants of A*), and its behaviour stays inside the banned set (BFS 25, DFS 23 of 50; avoidance 0.00).

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

The landing contest scored, on the 21 recorded push-landing events, three forecasts: the base runner-up, the most frequent algorithm other than the default in the instruct twin itself (defined on 7 events), and a teacher-forced ranking of the openings of the catalogue algorithms by the instruct twin, the log-mean-exp likelihood of the first 48 tokens of each algorithm over its reference and forced programs, which we call the opening ranking (Table 257). The base runner-up named 17 of 21 landings and the opening ranking 10. On the 9 events where they disagree the base runner-up wins 8:1 (exact one-sided sign test p 0.020), and its mean log score is higher by 1.62 nats (Wilcoxon p 0.032). Where the twin wrote an alternative, its own minority does as well as the base runner-up (6 of 7; log-score difference 0.02, p 0.69). The comparison is retrospective, because the landings were known when the rule was frozen, and the opening ranking rests on 1 to 6 programs per algorithm. The base model adds information beyond the ranking of openings by the instruct model itself; it does not add information beyond the minority algorithm of the twin where one exists.

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


## 6.5 Gemma: a one-token fork, and Gemma Scope 2 features against difference in means

**Why Gemma.** Asked one and the same grid-path prompt, gemma-3-4b-it [76] writes DFS about 70% of the time and BFS about 30%, so it offers what Qwen3-8B never does: the request's BFS-against-DFS contrast inside one prompt, with no ban or instruction to confound it. Gemma Scope 2 provides sparse autoencoders on the residual stream after each block, trained on this instruct model, so the feature claim needs no transfer test. Qwen-3 transcoders for circuit tracing exist as well [123], but they would have to study a choice Qwen3-8B does not make naturally. The experiment [ARTIFACT:art_zNyBP6zieI5u] asked where the choice forks, whether it can be read from the internals beyond what the visible text already says, and whether the SAE features steer it better than plain baselines: a difference-in-means direction, the raw residual, random features, isotropic directions, DAS and prompting. It used the residual-stream SAEs at layers 9, 17, 22 and 29 (16k latents, at the release's medium sparsity), one 16 GB card and exact common random numbers, under two hash-chained commitments.

**Natural splits.** Over 200 samples per task, the grid prompt gave DFS 139 and BFS 61 (Wilson interval for DFS 0.63 to 0.75), with DFS on 134 of 172 correct programs (Table 258). The choice depends on the template: BFS takes 6 to 18 of 40 attempts per template. Substring search (naive 173, built-in find 27) and first and last position (linear scan 170, binary search 29) split as well. Labels agreed with iteration 5's Gemma rows on 0.94 of the grid slots and 1.00 of the substring slots.

**Table 258.** Natural splits in gemma-3-4b-it (N = 200 per task; 40 per template). Source: Gemma feature experiment `results/natural_split.json`.

| Task | Attempted | Correct | Pass | Correct-only Hill-1 | Default (share of correct) | Attempted per template (first to fifth) |
|-|-|-|-|-|-|-|
| grid | DFS 139, BFS 61 | DFS 134, BFS 38 | 0.86 | 1.68 | DFS (0.78) | DFS 34 / BFS 6; DFS 22 / BFS 18; DFS 22 / BFS 18; DFS 29 / BFS 11; DFS 32 / BFS 8 |
| substring search | naive 173, built-in find 27 | same | 1.00 | 1.47 | naive (0.87) | naive 36 / built-in 4; naive 40; built-in 21 / naive 19; naive 38 / built-in 2; naive 40 |
| first and last position | linear scan 170, binary search 29, other 1 | same | 1.00 | 1.52 | linear scan (0.85) | linear 33 / binary 7; linear 28 / binary 12; linear 39 / other 1; linear 40; linear 30 / binary 10 |

**The instrument gate.** Each SAE was spliced into the forward pass on three corpora: the model's own programs, generic text and LeetCode prompts. A layer passed if its increase in cross-entropy and its fraction of variance unexplained on the model's programs were at most 1.5 times those on generic text (Table 259). Layers 22 and 29 passed; layer 9 failed the cross-entropy ratio and layer 17 the variance ratio by 0.0001, so their results are descriptive. On generic text the mean number of active latents per token was 57 to 64, slightly above the quoted medium band of 30 to 60.

**Table 259.** Gemma Scope 2 residual-stream SAEs spliced in on three corpora (the model's own programs / generic text / LeetCode prompts): mean active latents per token, fraction of variance explained, increase in cross-entropy (nats per token) and loss recovered. Source: Gemma feature experiment `results/gate.json`.

| Layer | Active latents per token | Fraction of variance explained | Increase in cross-entropy | Loss recovered | Gate |
|-|-|-|-|-|-|
| 9 | 52.2 / 57.5 / 57.3 | 0.963 / 0.974 / 0.917 | 0.065 / 0.033 / -0.010 | 0.9968 / 0.9983 / 1.0005 | fail |
| 17 | 59.9 / 64.1 / 61.4 | 0.919 / 0.946 / 0.814 | 0.097 / 0.184 / 0.119 | 0.9968 / 0.9936 / 0.9957 | fail (variance ratio, by 0.0001) |
| 22 | 60.0 / 61.7 / 62.2 | 0.809 / 0.869 / 0.750 | 0.036 / 0.259 / 0.167 | 0.9968 / 0.9789 / 0.9837 | pass |
| 29 | 64.1 / 64.1 / 69.5 | 0.637 / 0.715 / 0.635 | 0.017 / 0.212 / 0.142 | 0.9994 / 0.9932 / 0.9952 | pass |

**The plan is a single-token fork.** Prefix resampling with change-point detection, the method of forking-path analyses [30, 31], located the fork: 24 base paths, 16 prefix lengths, 8 continuations each and a refinement, 3,712 continuations in all, scored by a partial-code labeller that agreed with the full labeller on 200 of 200 programs. Every one of 12 BFS base paths had a significant change point with a rise of at least 0.4, at prefix lengths 16 to 36. In 177 of 200 programs the first 32 tokens are identical (the code fence, `def solve(grid, start, goal):`, `rows = len(grid)`, `cols = len(grid[0])` and an indent), and the next token decides (Table 260): ` visited` leads to DFS (BFS probability 0.011 over 1,409 continuations), while a blank line, `if`, `queue` or `q` lead to BFS (0.95 to 1.00). The first token that identifies the algorithm in code comes a median of 138 tokens after the fork (10th to 90th percentile 80 to 181). The fork index was chosen by the token class with the most mutual information with the outcome (0.62 bits at index 32), after the first median rule landed on a deterministic indentation token; the change was made before the second commitment.

**Table 260.** The fork token at response index 32 and the BFS probability of the continuations that follow it (all continuations; the natural samples alone in the last column). Source: Gemma feature experiment `results/fork.json`.

| Token at index 32 | Continuations | BFS | DFS | BFS probability | Natural samples (BFS / n) |
|-|-|-|-|-|-|
| ` visited` | 1,409 | 15 | 1,394 | 0.011 | 2 / 134 |
| newline | 204 | 193 | 11 | 0.946 | 19 / 21 |
| `if` | 177 | 174 | 2 | 0.989 | 16 / 17 |
| `queue` | 82 | 82 | 0 | 1.000 | 4 / 4 |
| `q` | 3 | 3 | 0 | 1.000 | 1 / 1 |

**Readable beyond the text, at the fork, but not specifically through the SAE.** Within one prompt, decodability before the first identifying token is at ceiling for every method, the visible-text control included (balanced accuracy 1.00 at all four layers), so the SAE has no advantage there; at the fork itself the test is undefined, because 185 of 200 samples share their prefix with a sample of the other class. Across prompts, the experiment built 120 neutral prompt variants by changing nouns and measured each variant's fork log-odds of BFS, which we write y (mean -0.92 nats, SD 0.67; the sampled BFS share tracks it at Spearman 0.65 over 60 variants of 10 samples). A Lasso on layer-29 SAE codes at the fork position predicts held-out y with R-squared 0.66, against 0.18 for a text-only model (difference 0.49, 95% interval 0.26 to 0.65, permutation p 0.003), above the difference-in-means readout (0.34) and a 16-component PCA of the raw residual (0.56) (Table 261). That meets the preregistered bar. Two checks outside the preregistration qualify it: a tuned ridge on the raw layer-29 residual reaches 0.72, and ridge on the same SAE codes reaches at most 0.09. The information is in the residual stream at the fork, and the SAE advantage depends on the estimator. At the task-specification positions, before any response token, the SAE codes do no better than the text (0.18).

**Table 261.** Cross-prompt readout of the fork log-odds over 120 neutral variants: R-squared with held-out nouns, Spearman with held-out nouns, and R-squared with held-out templates. Source: Gemma feature experiment `results/readout.json`.

| Readout | Site | Layer | R-squared, held-out nouns | Spearman, held-out nouns | R-squared, held-out templates |
|-|-|-|-|-|-|
| text only | n/a | n/a | 0.176 | 0.425 | 0.150 |
| template only | n/a | n/a | 0.148 | 0.272 | -0.122 |
| SAE codes (Lasso) | fork | 22 | 0.237 | 0.583 | 0.139 |
| raw PCA-16 | fork | 22 | 0.412 | 0.666 | 0.491 |
| raw PCA-64 | fork | 22 | 0.092 | 0.533 | 0.239 |
| difference in means | fork | 22 | 0.226 | 0.541 | 0.109 |
| SAE codes (Lasso) | task specification | 22 | 0.180 | 0.464 | 0.123 |
| raw PCA-16 | task specification | 22 | -0.090 | 0.354 | 0.352 |
| raw PCA-64 | task specification | 22 | 0.021 | 0.432 | 0.152 |
| difference in means | task specification | 22 | 0.063 | 0.282 | -0.570 |
| SAE codes (Lasso) | fork | 29 | 0.662 | 0.782 | 0.496 |
| raw PCA-16 | fork | 29 | 0.557 | 0.697 | 0.444 |
| raw PCA-64 | fork | 29 | 0.432 | 0.715 | 0.403 |
| difference in means | fork | 29 | 0.338 | 0.620 | 0.181 |
| SAE codes (Lasso) | task specification | 29 | -0.073 | 0.276 | 0.147 |
| raw PCA-16 | task specification | 29 | -0.602 | 0.194 | -0.062 |
| raw PCA-64 | task specification | 29 | 0.029 | 0.381 | 0.083 |
| difference in means | task specification | 29 | 0.064 | 0.302 | -0.438 |

**Steering: the features move the fork, difference in means moves it more, and every fork edit breaks programs.** We call an *SAE clamp* setting the k latents that best separate forced-BFS from forced-DFS prompts (input-selected) to their BFS-class mean at the fork position; output-scored latents are chosen instead by their attribution to the fork's logit difference, and the two sets of 20 share 2 latents. At the fork position of layer 22, edits at matched norm moved y by +4.04 nats for the difference-in-means direction, +1.78 for the SAE clamp of the top 20 input-selected latents, +0.51 for 20 random latents and +0.12 for an isotropic direction. Table 261b gives the whole dose-response sweep over the 120 prompt variants (11,280 measurements), at the fork and at the task-specification positions. In generation (N = 50 paired slots), the twin wrote BFS in 13 programs; the SAE clamp raised this to 30 (top 20 latents) and 36 (top 50), the difference-in-means edit at the same norm to 46 and 49, and random latents to 21 (Table 262). Every edit at the fork lowered the pass rate, from 0.84 for the twin to 0.58 and 0.48 for the SAE clamps and 0.32 and 0.16 for difference in means, so the preregistered outcome, correct BFS programs, shows no significant effect anywhere after Holm correction, and no feature claim is made. The preregistered feature rule (SAE target-correct count at least the difference-in-means count, at a pass rate of at least 0.8 times the twin's) is also met by random latents at k = 50 (9 against 7, pass 0.76), so it cannot discriminate here. The informative comparisons are on attempted BFS, and they are descriptive: the SAE clamp beats the twin (17:0 and 23:0 discordant slots, p 1.5e-5 and 2.4e-7) and random latents (15:0, p 6.1e-5), and difference in means beats the SAE clamp at matched norm (16:0, p 3.1e-5). At matched effect on y rather than matched norm, difference in means and the SAE clamp shift the plan equally (32 against 30 BFS, p 0.50; 34 against 36, p 0.63) and difference in means keeps slightly more programs correct (13 against 9, 14 against 10). Edits at the task-specification positions do nothing (12 to 19 BFS against 13). Steering toward DFS works cleanly for both (SAE 47 of 50, difference in means 50 of 50, against 37 for the twin; pass 0.98 to 1.00). Difference-in-means steering of a code model's choice of language and library has shown the same trade-off, with overly strong interventions reducing output quality [130]. AxBench found simple baselines ahead of SAE steering [34], and a 2026 reanalysis puts SAEs close to AxBench's reference when latents are selected and labelled by a supervised pipeline [131]; here, at comparable norms, neither the input-selected nor the output-scored clamp reached the difference-in-means edit (Table 261b).

**Table 261b.** Mean change in the fork log-odds of BFS (nats) under each edit at layer 22, by number of latents k and dose lambda; the difference-in-means, random and isotropic edits are scaled to the norm of the input-selected clamp with the same k. Source: Gemma feature experiment `results/logit_sweep_summary.json`.

| Edit | Latents (k) | Fork, lambda 0.5 | Fork, lambda 1 | Fork, lambda 2 | Task specification, lambda 0.5 | Task specification, lambda 1 | Task specification, lambda 2 |
|-|-|-|-|-|-|-|-|
| SAE clamp, input-selected | 5 | 0.52 | 0.98 | 1.97 | 0.09 | 0.11 | 0.11 |
| SAE clamp, input-selected | 20 | 0.87 | 1.78 | 3.76 | 0.12 | 0.12 | 0.22 |
| SAE clamp, input-selected | 50 | 1.09 | 2.26 | 4.47 | 0.08 | 0.10 | 0.20 |
| SAE clamp, output-scored | 5 | 0.66 | 1.33 | 2.69 | 0.16 | 0.20 | 0.28 |
| SAE clamp, output-scored | 20 | 0.74 | 1.35 | 2.65 | 0.17 | 0.22 | 0.21 |
| SAE clamp, output-scored | 50 | 1.38 | 2.94 | 6.07 | 0.23 | 0.32 | 0.37 |
| difference in means (norm of the input-selected clamp) | 5 | 1.05 | 2.04 | 4.14 | 0.09 | 0.09 | 0.08 |
| difference in means (norm of the input-selected clamp) | 20 | 1.98 | 4.04 | 7.93 | 0.41 | 0.70 | 1.29 |
| difference in means (norm of the input-selected clamp) | 50 | 3.53 | 7.08 | 12.22 | 0.44 | 0.76 | 1.35 |
| random latents (same norm) | 5 | -0.14 | -0.37 | -0.73 | 0.08 | 0.10 | 0.12 |
| random latents (same norm) | 20 | 0.26 | 0.51 | 1.26 | 0.04 | 0.01 | -0.01 |
| random latents (same norm) | 50 | 0.32 | 0.89 | 2.65 | 0.18 | 0.31 | 0.54 |
| isotropic direction (same norm) | 5 | 0.06 | 0.11 | 0.13 | 0.07 | 0.04 | 0.02 |
| isotropic direction (same norm) | 20 | 0.07 | 0.12 | 0.26 | -0.16 | -0.37 | -0.78 |
| isotropic direction (same norm) | 50 | 0.12 | 0.23 | 0.18 | -0.19 | -0.42 | -0.81 |
| SAE clamp with ban-contrast latents | 20 | n/a | 0.95 | n/a | n/a | 0.09 | n/a |
| SAE clamp, input-selected, layer 29 | 20 | n/a | 0.63 | n/a | n/a | n/a | n/a |

**Table 262.** Generation under edits at the fork (layer 22) and at the task-specification positions (N = 50 paired slots; BFS is the target). Source: Gemma feature experiment `results/clamps.json`.

| Site | Edit | Mean realised norm | Attempted BFS | Correct BFS | Pass |
|-|-|-|-|-|-|
| none | twin | 0 | 13 | 6 | 0.84 |
| fork | SAE clamp, top 5 input-selected latents | 307.9 | 18 | 10 | 0.84 |
| fork | SAE clamp, top 20 input-selected latents | 602.2 | 30 | 9 | 0.58 |
| fork | SAE clamp, top 50 input-selected latents | 1069.8 | 36 | 10 | 0.48 |
| fork | difference in means at the top-20 norm | 602.2 | 46 | 12 | 0.32 |
| fork | difference in means at the top-50 norm | 1069.8 | 49 | 7 | 0.16 |
| fork | 50 random latents at the same norm | 1069.8 | 21 | 9 | 0.76 |
| fork | SAE clamp, top 20 output-scored latents | 673.5 | 25 | 14 | 0.78 |
| fork | difference in means matched on effect, top-20 level | 270.6 | 32 | 13 | 0.62 |
| fork | difference in means matched on effect, top-50 level | 342.9 | 34 | 14 | 0.60 |
| fork | DAS rank-4 interchange | 496.0 | 50 | 0 | 0.00 |
| fork | ablation of the top 5 attribution nodes (N = 30) | 1004.7 | 29 | 0 | 0.03 |
| fork | steering with the top 5 attribution nodes (N = 30) | 115.5 | 19 | 12 | 0.73 |
| task specification | SAE clamp, top 5 | 4.1 | 14 | 6 | 0.84 |
| task specification | SAE clamp, top 20 | 92.4 | 12 | 4 | 0.82 |
| task specification | SAE clamp, top 50 | 104.9 | 15 | 5 | 0.80 |
| task specification | difference in means at the top-20 norm | 92.4 | 17 | 9 | 0.84 |
| task specification | difference in means at the top-50 norm | 104.9 | 19 | 9 | 0.80 |
| task specification | 50 random features | 104.9 | 15 | 9 | 0.88 |
| fork, toward DFS | SAE clamp, top 20 | 1170.1 | 3 (47 DFS, all correct) | n/a | 0.98 |
| fork, toward DFS | difference in means | 1170.1 | 0 (50 DFS, all correct) | n/a | 1.00 |

[FIGURE:fig_gemma_steer]

**DAS finds the choice in one direction at the fork, and forcing it breaks the program.** DAS at the fork position of layer 22, with forced-BFS prompts as sources, moved held-out y by +8.8, +9.5 and +9.8 nats at ranks 1, 2 and 4, against -0.08 to +0.05 for random subspaces of the same rank (Table 263). The shuffled-source control was uninformative as built, because every source was a forced-BFS prompt. In generation the rank-4 interchange made 50 of 50 programs BFS and 0 of 50 passed. Together with the difference-in-means result, this says that the plan is close to one direction at one position, and that pushing it hard costs correctness, as subspace interventions can when they leave the model's natural range [122].

**Table 263.** DAS at the fork (layer 22): mean change in the fork log-odds of BFS on held-out and training prompts. Source: Gemma feature experiment `results/das.json`.

| Rank | DAS, held out | DAS, train | Share of held-out prompts moved toward BFS | Random subspace, held out | Shuffled source, held out |
|-|-|-|-|-|-|
| 1 | 8.81 | 9.55 | 1.00 | -0.08 | 10.11 |
| 2 | 9.51 | 10.15 | 1.00 | 0.03 | 9.69 |
| 4 | 9.76 | 10.25 | 1.00 | 0.05 | 11.42 |

The planned transcoder attribution graph was the first item of the drop order and was not built; a first-order attribution on the residual-stream SAEs replaced it (Table 264). Ablating the two strongest nodes moved y by 4.0 and 6.3 nats, against 0.8 and 0.4 for random active latents at matched contribution; two of the other three beat random and one did not. Jointly ablating the five nodes turned 29 of 30 programs into BFS with none passing, and jointly steering with them gave 19 BFS of 30, 12 correct.

**Table 264.** First-order attribution nodes at the fork, validated by ablation and steering in the real model (mean change in y, against random active latents at matched contribution). Source: Gemma feature experiment `results/attribution.json`.

| Layer | Latent | Attribution score | Ablation | Random ablation | Steering | Random steering |
|-|-|-|-|-|-|-|
| 22 | 1774 | -4.68 | 4.01 | 0.78 | 0.55 | 0.07 |
| 29 | 15050 | -4.35 | 6.28 | 0.40 | 0.45 | 0.11 |
| 29 | 735 | 4.11 | -0.51 | 0.40 | 1.38 | 0.09 |
| 29 | 6026 | 3.95 | -0.95 | 0.51 | 0.14 | 0.09 |
| 22 | 142 | 3.79 | -1.26 | 2.10 | 0.24 | 0.09 |

**The top-five prohibition in a model that writes two algorithms.** Banning the five most common grid algorithms (BFS, DFS, IDDFS, A* and greedy best-first, which share one catalogue label here) left no program outside the banned set: avoidance 0.00, as in Qwen3-8B in iteration 2 (Table 265). The ban pushed Gemma from its default DFS to BFS (10 to 41 of 50; McNemar 32:1, p 7.9e-9) and cut the pass rate from 0.86 to 0.38. In actual activation coordinates (PCA, Isomap with k = 10 and classical MDS of layers 17 and 22, raw and SAE codes), the top-five prompt states sit next to the banned A* and greedy cluster (Table 266); among all 15 ways of splitting the six catalogue centroids into four banned and two survivors, the observed split ranks first in three of the four spaces (rank share 0.067) and third in the fourth (0.20). The prohibition lands inside the banned region, not at its edge or on the opposite side. The single-name bans of BFS and DFS left the banned algorithm in 11 and 8 of 50 programs, and the forced prompts gave BFS 50 of 50 (38 correct) and DFS 50 of 50 (45 correct).

**Table 265.** Bans and forced prompts on Gemma's grid task (N = 50). Source: Gemma feature experiment `results/top5.json`, `results/geometry.json`.

| Prompt | Attempted | Correct | Pass | Avoidance of the banned set |
|-|-|-|-|-|
| top-five twin | DFS 40, BFS 10 | DFS 40, BFS 3 | 0.86 | n/a |
| top-five ban | BFS 41, DFS 9 | BFS 10, DFS 9 | 0.38 | 0.00 |
| ban BFS | DFS 39, BFS 11 | DFS 39, BFS 2 | 0.82 | 0.78 |
| ban DFS | BFS 42, DFS 8 | BFS 15, DFS 7 | 0.44 | 0.84 |
| forced BFS | BFS 50 | BFS 38 | 0.76 | n/a |
| forced DFS | DFS 50 | DFS 45 | 0.90 | n/a |

**Table 266.** Where the top-five prompt states sit: geodesic distance from their mean to each catalogue centroid, and the rank of the observed banned-survivor split among the 15 possible splits. Source: Gemma feature experiment `results/geometry.json`.

| Space | MDS stress-1 | Nearest centroid | Geodesic distance to BFS / DFS / bidirectional BFS / IDDFS / A* and greedy / Dijkstra | Rank share of the observed split |
|-|-|-|-|-|
| raw, layer 17 | 0.371 | A* and greedy | 341.9 / 330.6 / 410.3 / 222.1 / 188.8 / 496.5 | 0.067 |
| raw, layer 22 | 0.369 | A* and greedy | 734.1 / 684.9 / 900.1 / 365.2 / 318.6 / 990.5 | 0.067 |
| SAE codes, layer 17 | 0.542 | A* and greedy | 27.5 / 28.4 / 41.1 / 32.9 / 26.1 / 47.1 | 0.067 |
| SAE codes, layer 22 | 0.569 | A* and greedy | 43.2 / 44.1 / 61.5 / 83.6 / 43.1 / 72.5 | 0.20 |

The novelty audit found 1 correct program labelled other among 1,450 correct programs, a first-and-last-position program that two of three judges called a catalogue variant: 0 novel (rule-of-three bound 0.0021). The style re-gate agreed with the labeller on 30 of 30 grid programs. The hash chain verified, a standard-library re-derivation matched 32 of 32 headline quantities, and a shuffled-class decodability placebo sat at chance (0.43). Judge spend was USD 0.034.

## 6.6 The plan in words: a natural language autoencoder on Qwen2.5-7B-Instruct

**Why.** The request names NLA as an instrument, and the release of NLA checkpoints for Qwen2.5-7B-Instruct [124] made it possible to ask, in words, whether the residual stream states before the first code token say which algorithm will be written. The experiment [ARTIFACT:art_dbUtqBjT0tPf] read layer-20 states with the released verbalizer and reconstructor pair, judged the explanations blind, and tested an edit of the explanation as a steering vector. Published verbalizers of the same kind include LatentQA [117] and SelfIE [118], and a 2026 analysis of a released Qwen-2.5-7B verbalizer found that only a small share of an explanation's specific claims are ones the reconstruction depends on [119]. Pre-registration was a sha256 chain of four commitments, each preceding its samples; the parts added after the committed nulls are marked exploratory.

**Behaviour.** Over eight tasks, Qwen2.5-7B-Instruct defaults to BFS, Dijkstra (0.88), a hash map (0.98), a hash set (0.71), DFS for connected components (0.62, where Qwen3-8B writes union find), the naive scan and binary search; kth smallest has no default (quickselect 0.40, size-k heap 0.34) and failed the style re-gate. The model mostly ignores bans (Table 267). Only two sum gave a substitute (brute force in 32 of 46 correct programs). On connected components a ban of DFS raised DFS from 29 to 43 correct programs, with 15 paired slots flipping from union find to DFS, the rebound that naming a forbidden concept can cause [7, 53]. Every one of the 70 programs written under the fourth template attempted the banned default. The shortest path semantic seed barely moved the model (Dijkstra 28, Bellman-Ford 6, against 38 and 5 for the twin). The labellers recognised 51 of 51 references, and the style re-gate passed on 7 of 8 tasks against two blind code judges.

**Table 267.** Behaviour of Qwen2.5-7B-Instruct (twin and ban N = 50, paired slots; forced prompts N = 20 per algorithm). Source: NLA experiment `results/behaviour.json`.

| Task | Default (share of correct twin programs) | Twin pass | Ban: attempts still using the default | Substitute under the ban | Forced adherence of the algorithm used in the causal arm |
|-|-|-|-|-|-|
| grid | BFS (13/13) | 0.26 | 0.68 | none (DFS 3) | none (best other 0.35) |
| shortest path | Dijkstra (38/43) | 0.86 | 0.50 | none (Bellman-Ford/SPFA 9, below 10) | none (Bellman-Ford 0.65, below 0.7) |
| kth smallest | none (quickselect 0.40) | 0.94 | n/a | n/a | excluded (re-gate 26/30) |
| two sum | hash map (49/50) | 1.00 | 0.28 | brute force (32/46) | brute force 1.00 |
| find duplicate | hash set (35/49) | 0.98 | 0.46 | none (Floyd cycle detection 7) | Floyd cycle detection 0.95 |
| connected components | DFS (29/47) | 0.94 | 0.86 | none (DFS 43, union find 2) | union find 0.95 |
| substring search | naive (50/50) | 1.00 | 0.94 | none | KMP 0.90 |
| first and last position | binary search (38/38) | 0.76 | 0.96 | none | bisect module 1.00 (not run) |

**The instrument gate.** The extraction convention that matches the training code reads the output of block 20; it reaches a fraction of variance explained of 0.695 on the reference set against 0.580 for the convention in the release's example, and 0.695 is within 0.06 of the released 0.752. Generic web text and chat give 0.78 and 0.79. Code is out of distribution for this NLA: LeetCode prompts 0.45, HumanEval+ prompts 0.39, CLRS traces 0.33. On the task states the fraction of variance explained, with the reference-set variance as denominator, is 0.512, so the gate's verdict is partial (Table 268).

**Table 268.** Fraction of variance explained of the layer-20 reconstructions on the task states, by position (reference-set denominator). Source: NLA experiment `results/gate.json`.

| Position | Read position | Task specification | Token 1 | Token 2 | Token 4 | Token 8 | Token 16 |
|-|-|-|-|-|-|-|-|
| Fraction of variance explained | 0.65 | 0.50 | 0.48 | 0.28 | 0.64 | 0.57 | 0.51 |

**The NLA never names the planned algorithm before the code.** Two blind judges from different families (Gemini 2.5 Flash Lite and Mistral Small 3.2, both scoring 1.00 on calibration; a third model resolved 1,064 disagreements) mapped each of 6,180 explanations to a catalogue algorithm or to none named (Table 269). Every preregistered readout at the end-of-prompt positions is exactly zero (Table 270). On ban prompts, explanations named the substitute in 0 of 16 states (only two sum had a substitute, so this test is underpowered); on twin prompts they named the default in 0 of 112, as did the text-only reader; on ban failures they named the default the model still writes in 0 of 96. The positive control failed too: on forced `Implement Y` prompts the explanations called Y planned in 0 of 7 tasks, while the text-only reader did so on all of them, and they mentioned the algorithm named in the prompt in 0.7% of cases. The explanations describe the local format line, such as a request for no explanation or a Python code block to follow, and confabulate the task (Fibonacci, medians, prime numbers); 4,733 of 5,700 judged explanations name no algorithm at all. At generated tokens the NLA sometimes names the realised algorithm before the visible text identifies it (up to 0.28 at token 8 under the ban), but an outside reader who sees only the prompt and prefix predicts the realised algorithm better, per sample (0.25 against 0.07; exact McNemar 20:88, p 2e-11).

**Table 269.** Agreement between the two judges by mode (EXPL: mapping an explanation; NAME: naming from the visible text; PREDICT: the outside reader's forecast). Source: NLA experiment `results/readout.json`.

| Mode | Raw agreement | Kappa | Unresolved after the third judge |
|-|-|-|-|
| explanation | 0.94 | 0.82 | 0.6% |
| visible text | 0.67 | 0.56 | 1.6% |
| outside reader | 0.77 | 0.75 | 3.9% |

**Table 270.** Preregistered readout tests. Source: NLA experiment `results/readout.json`.

| Test (units) | NLA | Comparator | b : c | p | Verdict |
|-|-|-|-|-|-|
| ban states name the substitute (two sum only; 16 states) | 0/16 | text 0/16 | 0 : 0 | 1 | fail, underpowered |
| same, against swapped, random and outside-reader controls | 0/16 | swapped 0/16, random 0/8, outside reader 0/16 | 0 : 0 | 1 | n/a |
| twin states name the default (7 tasks; 112 states) | 0/112 | text 0/112 | 0 : 0 | 1 | fail |
| forced states name the forced algorithm (7 tasks) | 0.00 on every task | text 1.00 | n/a | n/a | fail |
| ban-failure states name the default still written (6 tasks; 96) | 0/96 | outside reader 0/96, text 0/96 | 0 : 0 | 1 | null |
| per sample, mixed conditions (364 units, 120 samples) | 0.066 correct | outside reader 0.253 | 20 : 88 | 2e-11 | outside reader better |
| generated positions before the identifying token | ban token 8: 0.28; twin token 4: 0.18 | text 0 by construction | n/a | n/a | descriptive |

**The information is local and fades within a sentence (exploratory).** To tell an instrument limit from information that fades along the prompt, the same NLA and judges read states at the token that names the algorithm inside the condition sentence and at the final period of that sentence (220 states, 660 explanations; Table 271). At the name token the explanations mention the algorithm in 80% of forced and 89% of ban states, and they respect the negation: they call it planned in 48% of forced states and in 6% of ban states. Two to eight tokens later, at the end of the sentence, the mention rates fall to 27% and 6%, and about 170 tokens later, at the end of the prompt, to 0.7%. The null therefore says that the pre-code positions do not carry the algorithm choice in a form this NLA puts into words, not that the instrument is blind.

**Table 271.** Local positive control (majority of three explanations per state; 75 forced and 35 ban states at each of the first two positions). The end-of-prompt row is the committed readout and counts single explanations at the last prompt positions (the algorithm is mentioned in 8 of 1,080 forced and 3 of 420 ban explanations). Source: NLA experiment `results/local_control.json`, `README.md`.

| Position | Forced: names Y as planned | Forced: mentions Y | Ban: names the default as planned | Ban: mentions the default | Reconstruction cosine |
|-|-|-|-|-|-|
| at the algorithm's name | 0.48 | 0.80 | 0.06 | 0.89 | 0.92 |
| end of that sentence (2 to 8 tokens later) | 0.11 | 0.27 | 0.00 | 0.06 | 0.90 |
| end of the prompt (committed readout, about 170 tokens later) | 0.00 | 0.007 | 0.00 | 0.007 | 0.82 to 0.87 |

[FIGURE:fig_nla_local]

**The preregistered verbal edit fails at the prefill site.** The causal arm replaced the default's name in a twin explanation by an algorithm Y the model writes on request, reconstructed both versions, and patched the difference into the layer-20 states at the last four prompt positions at doses of 1, 2 and 4 (N = 30 paired slots per cell). It failed on all four tasks (Table 272). The edits barely move the reconstruction (cosine 0.9992 between the edited and unedited reconstructions; 0.04 of the state norm per position; Table 273), the unedited round trip at 0.8 of the norm propagates downstream but moves nothing, and all 15 prefill cells per task stay within 0 to 3 slots of the unedited control. The edit direction is nearly orthogonal to the forced-state difference in means (median cosine 0.09).

**Table 272.** The preregistered causal arm: Y share in the unedited control and the edited-minus-round-trip difference at doses 1, 2 and 4 (N = 30 paired slots). Source: NLA experiment `results/causal.json`.

| Task (default to Y) | Control Y share | Dose 1 | Dose 2 | Dose 4 | Pass |
|-|-|-|-|-|-|
| connected components (DFS to union find) | 10/30 | -0.03 (0:1) | -0.03 (0:1) | +0.03 (3:2) | no |
| two sum (hash map to brute force) | 0/30 | 0 | 0 | 0 | no |
| find duplicate (hash set to Floyd cycle detection) | 12/30 | 0 | +0.03 (2:1) | +0.10 (3:0, p 0.25) | no |
| substring search (naive to KMP) | 0/30 | 0 | 0 | 0 | no |

**Table 273.** Realised push sizes relative to the state norm at block 20. Source: NLA experiment `results/causal.json`.

| Cell | Push norm over state norm |
|-|-|
| edit, dose 1 | 0.041 |
| unrelated-word edit, dose 1 | 0.036 |
| round trip, dose 1 | 0.201 |
| round trip, dose 4 | 0.80 (0.76 at block 27) |

**At the generated-token site and large doses, the verbal edit steers two of four tasks (exploratory).** After the committed nulls, the experiment extended the doses and moved the edit to the read position plus generated tokens 1 to 64 (Tables 274 and 275). On find duplicate the edit at dose 8 (about 0.3 of the state norm at each position) raised Floyd cycle detection from 0.28 to 0.76 (25:1 over 50 paired slots), replicated on fresh slots (15 of 20, 13:0, p 2e-4), and beat a matched random push (28:1), an unrelated-word edit built the same way (12:1, p 0.003) and a norm-matched round trip (13:1, p 0.002); at dose 16 the programs broke (pass 0.37). On two sum brute force rose from 0 to 10 of 50 at dose 8 and to 23 of 30 at dose 16 with a pass rate of 0.90, while the random push never moved it. On connected components only the forced-state difference in means steered (union find 0.80 at dose 16, 15:1); on substring search nothing steered short of breaking the program. The prefill site stayed inert even at dose 16 or at the natural norm of the difference in means. Asking for the algorithm in the prompt remained the ceiling (forced adherence 0.90 to 1.00 on all four tasks), as the AxBench comparison of prompting and steering predicts [34]. The NLA paper itself reports that editing a plan explanation and steering at one token succeeds roughly half the time; this run's success on two of four tasks is of the same kind and is not a reliable control knob.

**Table 274.** Exploratory dose extension (Y share out of 30 paired slots). Source: NLA experiment `results/causal_exploratory.json`.

| Task | Control | Prefill edit, dose 16 | Prefill difference in means at natural norm, dose 2 | Generated-site edit, dose 8 | Generated-site random, dose 8 | Generated-site difference in means, dose 8 | Generated-site difference in means at natural norm |
|-|-|-|-|-|-|-|-|
| connected components (to union find) | 10 | 10 | 9 | 8 | 11 | 19 (10:1, p 0.012) | 13 |
| two sum (to brute force) | 0 | 0 | 0 | 4 (4:0, p 0.125) | 0 | 0 | 0 |
| find duplicate (to Floyd cycle detection) | 12 | 11 | 12 | 23 (12:1, p 0.003) | 8 | 2 | 6 |
| substring search (to KMP) | 0 | 0 | 0 | 0 | 0 | 2 (pass 0.83) | 0 |

**Table 275.** Exploratory follow-up at the generated-token site: dose response, controls built the same way and a replication on fresh slots (Y share; exact McNemar on paired slots). Source: NLA experiment `results/causal_exploratory_followup.json`.

| Task | Edit, dose 4 | Edit, dose 8 (N = 50) | Edit, dose 16 | Dose 8, fresh slots (N = 20) | Dose 8 against random | Dose 8 against unrelated-word edit | Dose 8 against matched round trip | Difference in means, dose 16 |
|-|-|-|-|-|-|-|-|-|
| find duplicate (to Floyd cycle detection) | 0.60 (7:1, p 0.07) | 0.76 against control 0.28 (25:1, p < 1e-6) | 0.30, pass 0.37 | 15/20 (13:0, p 2e-4) | 28:1 | 12:1, p 0.003 | 13:1, p 0.002 | 0.07, pass 0.27 |
| two sum (to brute force) | 0.00 | 0.20 against 0.00 (10:0, p 0.002) | 0.77, pass 0.90 (23:0) | 6/20 (6:0, p 0.03) | 10:0, p 0.002 | 4:0, p 0.125 | 4:0, p 0.125 | 0.37, pass 0.40 |
| connected components (to union find) | 0.33 | 0.24 against 0.36 (3:9) | 0.17 | 4/20 | 5:13 | 6:6 | 2:6 | 0.80 (15:1, p 5e-4) |
| substring search (to KMP) | 0.03 | 0.00 | 0.07, pass 0.27 | 0/20 | 0:0 | 0:0 | 0:0 | 0.03, pass 0.10 |

In activation space (exploratory), read-position states projected on the plane of the forced-prompt states show every forced algorithm in its own region, with twin and ban prompts apart from all of them. Relative to the algorithm-specific directions of the forced prompts, the ban moves the state toward the banned default's own direction on two sum (+0.13), find duplicate (+0.26) and first and last position (+0.15), as the ban sentence names the default, and toward an alternative on shortest path (Bellman-Ford +0.13), connected components (BFS +0.23), substring search and the grid task (DFS +0.18). The novelty audit found 10 correct programs labelled other in every arm: 8 labeller misses (six kth smallest counting sorts built on a counter, two boolean seen-arrays) and 2 degenerate programs, 0 novel. Spend was about USD 2.0 on OpenRouter (NLA judges with calibration, two interrupted passes, the local control and the novelty audit USD 1.82; code judges for the bench tasks USD 0.11 and for the path tasks USD 0.10) and about 2.0 GPU hours on one 24 GB NVIDIA Ada GPU (68 minutes of generation for behaviour and the committed causal arm, about 27 for the exploratory causal cells, 16 for 6,180 explanations and about 8 for reconstruction passes and the state cache).

## 6.7 Positioning against published work

The positioning audit [ARTIFACT:art_OUuQUYQn5voE], dated 2026-10-22, extended the audits of iterations 4 and 5 to this iteration's claims. A protocol frozen and stamped before the first call drove 126 logged searches over seven lanes, from 2,191 raw hits to 1,820 unique records, 1,401 in the window, and 75 claim rows scored on the occupancy rubric for 67 papers: 3 occupying, 66 adjacent and 6 irrelevant. Its 123 new quotes from 94 sources matched the cached source text and were re-matched by an independent live pass. Table 276 gives the verdict per claim, and Table 277 condenses the 65 rows of its neighbour table; the verbatim quotes are in the audit's evidence files.

**Table 276.** Lane verdicts for the iteration-6 claims as of 2026-10-22. Source: positioning audit `research_report.md`.

| Claim | Lane verdict | Deciding neighbours |
|-|-|-|
| Localization: a low-rank causal plan variable, found by interchange or DAS, decides which algorithm Qwen3-8B writes, validated by generation | partly occupied: the method is occupied, the object is open; the flag for a published localization of algorithm choice did not fire, narrowly | DAS and Boundless DAS [110, 111]; MIB [52]; CDAS, DAS steering validated by generation on refusal and a backdoor [112]; prompt cues only for algorithm choice in code [1] |
| Mediation: the plan subspace mediates which random pushes switch the algorithm | adjacent only | pre-generation planning subspaces; output-sensitive steering components |
| Discreteness under interpolation | adjacent only | categorical and multidimensional feature geometry; manifold steering [27] |
| Ideas not in the tokens, at matched KL | adjacent only | decoding matched to steering's departure; temperature and novelty [37]; forking paths [30] |
| Resampling the plan as a diversity knob | partly occupied: activation noise and latent sampling for diversity are occupied | STARS [71]; noise steering [70]; random embedding injection [84] |
| The plan in words with NLAs | occupied (method): the NLA paper edits a plan explanation and steers with the reconstruction; this run is a replication in a new setting | the NLA paper (Transformer Circuits, May 2026); LatentQA [117]; SelfIE [118]; cautions [119, 120] |
| The plan in Gemma Scope 2 features | partly occupied: SAE-feature steering of reasoning strategies beats prompt and activation baselines | SAE-Steering [121]; AxBench [34] |
| 8-bit floating-point (W8A8) activation rounding inflates perturbation effects | adjacent only in the published record; partly occupied by contemporaneous ICLR 2027 submissions at abstract level | steering under weight-only quantization [116] |

Three of the audit's flags bear on what this run may claim. No source localizes which algorithm a code model will write by interchange or DAS and validates it by scoring the generated programs, so that combination is open; the method itself is DAS. Editing an NLA explanation of a plan and steering with the reconstruction is published, so the NLA arm is a replication on a new object. Steering under quantization has been compared with full precision only for weight-only 8-bit integer and 4-bit NormalFloat quantization, with activations kept in 16-bit floating point [116]; no source found measures how dynamic per-token activation rounding changes the effect of random perturbations, which is the question the engine control answered, in the negative. The audit also recorded that community NLAs exist for Qwen3-8B at layer 24, that circuit-tracer ships Qwen-3 transcoders including 8B [123] (so the choice of Gemma for the feature claim needs its reason, which is the natural within-prompt split), and that Gemma Scope 2 dates from 22 December 2025 with instruct SAEs initialised from the pretrained ones.

**Table 277.** The positioning audit's neighbour table, condensed (row; claim; neighbour with venue and version; relation; lane verdict; what this run adds; the baseline a reviewer would ask for). The verbatim quotes behind each row are in the audit's evidence file. Source: positioning audit `research_report.md`, Section 5. The audit wrote the last two columns before the experiments finished; for the claims that were not run (Section 6.8) they state what the planned test would add.

| Row | Claim | Neighbour (venue, version) | Relation | Lane verdict | What this run adds | Reviewer baseline implied |
|-|-|-|-|-|-|-|
| 1 | localization | DAS: Geiger, Wu, Potts, Icard, Goodman, CLeaR 2024 (PMLR 236), arXiv v4, v1 2023-03-05, pub; Boundless DAS, Wu et al., NeurIPS 2023, v3 | method the claim uses | PARTLY OCCUPIED (method) | object = algorithm choice in code; validation by tests on emitted programs; Sutter-style controls | DAS with a declared rotation rank, against Boundless DAS |
| 2 | localization | MIB: Mueller et al., ICML 2025, v2, v1 2025-04-17, pub | control the claim must meet (method ordering) | n/a | n/a | report neuron and SAE-feature arms beside DAS (MIB ordering) |
| 3 | localization | CDAS: Bao et al., ICLR 2026, v2, v1 2026-02-05, pub | occupies the method+criterion pair (rubric 2.5) on a non-plan attribute (refusal, CoT backdoor) | PARTLY OCCUPIED | a plan object (algorithm choice), route-derived predictions, random/shuffled controls | a CDAS-style distribution-matching DAS arm |
| 4 | localization | Programmable Semantic Interventions, ICLR 2027 submission, c | adjacent (rubric 1.5) | n/a | generation-validated plan object | PSI-style declared-program alignment |
| 5 | localization | Finding Algorithms in Neural Networks (DAS vs transfer), ICLR 2027 submission, c | adjacent (1.5); supports declaring the map class (non-linear DAS needed in vision) | n/a | algorithm identity in a code LLM, checked by generation | linear vs non-linear map classes |
| 6 | localization | Causal Syntax Circuits in CodeLMs, Kumar et al., NeurIPS 2026 workshop, v1 2026-10-14, c4 | adjacent (1.5): a code attribute that is not the algorithm; next-token readout | n/a | algorithm (not language); low-rank DAS; generation | random-control significance test, as there |
| 7 | localization | Steering LLM Coding Behaviors with Concept Vectors, ICLR 2027 submission, c | adjacent (2.0) | n/a | algorithm-level object with matched-norm controls | a difference-in-means direction for the algorithm, with matched-norm random controls |
| 8 | localization | Before Reasoning Begins (Qwen3-8B, final prompt position, SAE targets), ICLR 2027 submission, c | adjacent (2.0): same model and site; object is reasoning, not algorithm | n/a | which algorithm (not whether reasoning happens); DAS rather than SAE suppression | layer-count-matched random null interventions |
| 9 | localization | Committed Before Reasoning, Jo, v1 2026-07-17, c4 | supports (pre-generation commitment in Qwen3-8B) | n/a | n/a | n/a |
| 10 | localization | Random Choice in LMs: linear choice state, ICLR 2027 submission, c | adjacent (2.0) | n/a | code-algorithm object | switch-vs-distribution decomposition |
| 11 | localization | Detecting and Characterizing Planning in LMs, Nainani et al., v1 2025-08-25, anchor | adjacent (1.5); contradicts in part (the same abstract reports that planning is not universal) | n/a | algorithm-level plan, not a future-token plan | a planning-vs-improvisation criterion |
| 12 | localization | Algorithmic Core Extraction, Schiffman, v2, v1 2026-02-26, pub | adjacent (1.0) | n/a | choice among algorithms, not a task core | n/a |
| 13 | localization | Invisible Lottery (algorithm choice in code moved by cues), ICML 2026: see 92c source 30 | adjacent (2.0): object occupied behaviourally | n/a | internal causal variable | prompt-cue baseline |
| 14 | localization | Sutter, Minder, Hofmann, Pimentel, NeurIPS 2025 Spotlight, v2, v1 2025-07-11, pub | control the claim must meet | n/a | declared linear map class and rank; random-init or random-rotation control | fit the same map on a randomly initialized Qwen3-8B, and with shuffled labels |
| 15 | localization | Makelov, Lange, Geiger, Nanda, ICLR 2024, v2, pub | control the claim must meet | n/a | nullspace/row-space decomposition of the patch | check that the patched subspace is not causally disconnected |
| 16 | localization | Reply: Wu, Geiger, Huang, Arora, Icard, Potts, Goodman, v1 2024-01-23 | cite with CTRL-2 | n/a | n/a | n/a |
| 17 | localization | Divergent representations: Grant et al., v5 (2026-04-22), v1 2025-11-06 | control | n/a | on-distribution check of patched states | report divergence of the intervened states |
| 18 | localization | Right Answer, Wrong Mechanism, v2, v1 2026-09-30, c4 | control (do not rely on distance checks alone) | n/a | n/a | planted-pathway or clamp test |
| 19 | localization | Curse of Multiple Mediators; Many Circuits, One Mechanism (TMLR 2026); identification-assumptions position | controls | n/a | n/a | report interaction effects, cross-condition transfer and identification assumptions |
| 20 | mediation | Before the First Token (causal response-length subspace; parallel/orthogonal decomposition of interventions), ICLR 2027 submission: see 92c source 64 | adjacent (nearest) | ADJACENT-ONLY | prediction of random-push effects on algorithm choice from projection onto the plan subspace | parallel/orthogonal decomposition of each push |
| 21 | mediation | AJR; ASTEER; decodability is not actionability | adjacent | n/a | n/a | Jacobian-readout predictor of push effects |
| 22 | mediation | DecodeShare, v1 2026-05-21, pub | adjacent (1.5) | n/a | random pushes classified by plan-subspace energy | matched-budget random-subspace control |
| 23 | mediation | What Does Activation Steering Control?, v1 2026-08-24, c4 | supports a projection account (1.0) | n/a | n/a | report the share of each push's norm inside the plan subspace |
| 24 | mediation | Jailbreak success coordinate outside the refusal subspace, ICLR 2027 submission, c | contradicts in part: the outcome-deciding coordinate can lie outside an evaluated subspace | n/a | n/a | test the orthogonal complement as well |
| 25 | mediation | Before Reasoning Begins (targeted vs random-null); Latent Planning Emerges with Scale, ICLR 2026 | adjacent / supports | n/a | n/a | random-null arm |
| 26 | mediation | On the Non-Identifiability of Steering Vectors, v4, v1 2026-02-06, pub (found by a supplementary search) | supports a subspace-level (not direction-level) account (1.0) | n/a | n/a | report plan claims at subspace level; orthogonal-perturbation control |
| 27 | mediation | Steering off Course, v1 2025-04-06, anchor; Tele-Lens (ICML 2026) | caution | n/a | n/a | per-sample effect distributions |
| 28 | discreteness | Park, Choe, Jiang, Veitch, ICLR 2025 oral, v3, anchor | supports (categorical geometry) | ADJACENT-ONLY | an interpolation sweep between plan centroids, with the emitted algorithm labelled at each step | polytope/simplex geometry of the plan centroids |
| 29 | discreteness | Engels et al., ICLR 2025, v3 (title changed in v3), anchor | adjacent (2.0): interventions along circular features | n/a | discreteness vs continuity of a code plan | a test for irreducible multi-dimensional features |
| 30 | discreteness | Manifold Steering (ICML 2026 MI-workshop spotlight): see 92c source 44 | adjacent | n/a | n/a | geodesic vs linear paths |
| 31 | discreteness | Prolepsis, Jacopin, v2, v1 2026-04-16; Random Choice switch; manifold vs linear steering (ICLR 2027 submission) | adjacent | n/a | n/a | linear vs manifold interpolation |
| 32 | ideas not in the tokens | departure-matched decoding (an ICLR 2027 submission on activation steering for mathematical reasoning): 92c source 66; Peeperkorn; AdapT; Gumbel counterfactuals; Beneath the Diff | adjacent; departure-matched decoding is the reviewer baseline | ADJACENT-ONLY | plan-level (algorithm) readout of temperature vs state noise at matched KL | decoding matched to the perturbation's departure from greedy |
| 33 | ideas not in the tokens | Forking Paths, Bigelow et al., v1 2024-12-10, anchor | adjacent (2.0) | n/a | n/a | forking-token resampling baseline |
| 34 | ideas not in the tokens | HELIX (4-bit Granite; temperature plus steering), v1 2026-02-06; Predicting Future Behaviors, ICLR 2027 submission | adjacent | n/a | n/a | n/a |
| 35 | resampling the plan | STARS (ICLR 2026), Noise Steering, REI, NC-GRPO, 2606.10302, Diversity Without Discovery: 92c sources 15, 14, 16, 52, 31, 63 | occupies the method family (activation noise for diversity) | PARTLY OCCUPIED | resampling a fitted, causally localized plan variable | matched-dose activation noise; text-level plan samplers (IFG, PlanSearch) |
| 36 | resampling the plan | Random Choice in LMs, ICLR 2027 submission, c | adjacent (2.0); closest to flag D | n/a | per-generation resampling for algorithm diversity | distribution-direction intervention |
| 37 | resampling the plan | LP-BD; PPLR; SVP (ICLR 2027 submissions, c) | adjacent (flag D partly) | n/a | a frozen LM; the variable is fitted, not trained | n/a |
| 38 | resampling the plan | Latent Plan Transformer, v4, anchor (venue not stated in the arXiv record) | adjacent | n/a | n/a | n/a |
| 39 | the plan in words (NLA) | Fraser-Taliente, Kantamneni, Ong et al., the NLA paper, Transformer Circuits, published May 7, 2026, pub | OCCUPIES the method (rubric 2.5) | OCCUPIED (method) | replication in a new setting: algorithm choice in code, Qwen2.5-7B-Instruct at layer 20, text-only judges, an unrelated-word edit, a matched-norm random displacement | the paper's own newline-only steering protocol and success rate |
| 40 | the plan in words (NLA) | same paper, Reasoning about Rewards | occupies | n/a | n/a | AR-difference steering vector, norm-matched |
| 41 | the plan in words (NLA) | same paper, Method and Limitations | control the claim must meet (confabulation) | n/a | n/a | confabulation audit of plan claims |
| 42 | the plan in words (NLA) | Released checkpoints: kitft README; HF card; nla_meta.yaml; TransformerLens issue #1884 | design facts | n/a | n/a | load nla_meta.yaml injection settings |
| 43 | the plan in words (NLA) | LatentQA, Pan, Chen, Steinhardt, ICLR 2026, v2; SelfIE, ICML 2024, PMLR 235 | occupies the similar-verbaliser clause of flag C (rubric 2.0 each) | n/a | n/a | decoder-loss steering arm |
| 44 | the plan in words (NLA) | Activation Oracles, v2; Dreaming Vectors (LessWrong) | readout kin / steering kin (grey literature) | n/a | n/a | n/a |
| 45 | the plan in words (NLA) | Sood, Substack, 2026-08-18, c4; Auditing the Auditor, ICLR 2027 submission, c | control set the readout must meet | n/a | n/a | shuffled-activation control; visible-text baseline; blinded judge |
| 46 | the plan in words (NLA) | Train the Model, Not the Reader, Dingeto, v2, v1 2026-07-22, c4 | contradicts in part: an edited claim may not move the AR output | n/a | measure the AR displacement caused by the edit before steering | claim-flip reconstruction test |
| 47 | the plan in words (NLA) | Colombian identity with NLA, v1 2026-07-23, c4 | readout replication on the same checkpoint | n/a | n/a | n/a |
| 48 | the plan in words (NLA) | Community Qwen3-8B NLAs: nanoNLA; EasyNLA | corrects the iteration-5 statement that no NLA exists for Qwen3-8B | n/a | n/a | an optional Qwen3-8B arm (unofficial; faithfulness disclaimer) |
| 49 | the plan in words (NLA) | Planning or Improvisation?, Jacopin, v1 2026-09-16, c4 | contradicts in part (no newline-resident plan in small open models) | n/a | n/a | site sweep (newline vs final prompt token) |
| 50 | the plan in words (NLA) | Measuring Activation Control; Understanding Confabulation | context | n/a | n/a | n/a |
| 51 | Gemma Scope 2 features | Gemma Scope 2: announcement 22 Dec 2025; technical report; HF card | design facts | n/a | n/a | report the IT-vs-PT dictionary used |
| 52 | Gemma Scope 2 features | circuit-tracer README; Qwen-3 transcoders (Hanna et al.) | design fact: Qwen3-8B transcoders exist, so a reviewer may ask why S uses Gemma | n/a | n/a | run S on the Qwen3-8B PLTs, or justify Gemma |
| 53 | Gemma Scope 2 features | AxBench, v3, v1 2025-01-28; rebuttal, v1 2026-05-29 | prior the claim must meet | n/a | n/a | difference-in-means and prompting arms |
| 54 | Gemma Scope 2 features | SAE-Steering, Fang et al., ACL 2026 Main, v2; Galichin et al. | OCCUPIES the method on a non-code strategy (rubric 2.5) | PARTLY OCCUPIED | algorithm choice in code; Gemma Scope 2; transcoder attribution | SAE-Steering-style logit-recall feature selection |
| 55 | Gemma Scope 2 features | Do SAEs Identify Reasoning Features? (Gemma Scope 2), ICML 2026, v7 | contradicts in part | n/a | n/a | token-injection falsification of candidate features |
| 56 | Gemma Scope 2 features | Prolepsis; Latent Planning Emerges with Scale | adjacent; counter-evidence to the AxBench prior for plans | n/a | n/a | CLT/PLT arm against residual difference-in-means |
| 57 | Gemma Scope 2 features | SAE Interventions are Unreliable; variable roles in code LMs (ICLR 2027 submission); attribution-graph caveat | cautions | n/a | n/a | probe baseline; post-intervention recovery check |
| 58 | engine (8-bit floating-point W8A8) | Steering Under Compression, Bhandari and Wade, v1 2026-09-06, c4 | adjacent (1.5); flag B partly | ADJACENT-ONLY (published) | activation quantization; random perturbations; matched bf16 control | iso-effect comparison at matched behavioural effect |
| 59 | engine (8-bit floating-point W8A8) | Stable Directions, Different Effects, ICLR 2027, desk rejected, c | partly occupies the general claim (contemporaneous) | PARTLY OCCUPIED (contemporaneous) | random pushes; 8-bit floating-point W8A8 named; noise-floor account | a first-order local-sensitivity predictor |
| 60 | engine (8-bit floating-point W8A8) | Activation Steering under Low-Bit Quantization, ICLR 2027 submission, c | adjacent (1.0) | n/a | n/a | hold layer, direction and strength fixed |
| 61 | engine (8-bit floating-point W8A8) | Quantization Modulates Batch-Context Non-Determinism, ICLR 2027 submission, c | mechanism neighbour (noise floor) | n/a | perturbation effect sizes against the 8-bit floating-point noise floor | same-batch-context repeat runs |
| 62 | engine (8-bit floating-point W8A8) | PRISM, v1 2026-10-14, c4 | adjacent (4-bit NormalFloat) | n/a | n/a | n/a |
| 63 | engine (8-bit floating-point W8A8) | Readouts under quantization: Findings ACL 2026;;; AACL 2025; TrustNLP 2026 | flag B partly (readouts, not perturbation effect sizes) | n/a | n/a | n/a |
| 64 | engine (8-bit floating-point W8A8) | Precision-induced divergence: TMLR 2026;;; | supports the mechanism (rounding flips trajectories) | n/a | n/a | a zero-norm (unperturbed) re-run under the same engine |
| 65 | engine (8-bit floating-point W8A8) | Mechanism sources: LLM.int8(); SmoothQuant; massive activations; 8-bit floating-point formats; the dynamic 8-bit floating-point scheme of llm-compressor | mechanism background | n/a | n/a | per-token-scale ablation |

## 6.8 Planned but not run

The seventh artifact of the strategy never existed. It was to fit DAS subspaces of rank 1 to 16 at one layer of the task-specification positions in bf16 Qwen3-8B on three training templates and confirm them on two held-out templates (Stage B of the localization claim), test whether a fresh random direction's energy in that subspace predicts its effect (the mediation claim), interpolate and extrapolate the plan coordinate between algorithms (the discreteness claim), measure the plan coordinate's variance across temperatures (the first half of the token claim), resample the plan per generation as a diversity knob (the resampling claim), and draw the request's manifold of algorithms in the fitted plan subspace, with the top-five prohibition placed on it. It was lost at the planning stage: the planning agent returned no plan, so no experiment ran. These claims are untested and open; nothing in this report is a result for them, null or otherwise. The only DAS result of the iteration is Gemma's, at the fork position (Section 6.5).

## 6.9 Comparisons across this iteration's experiments

**Where the choice is held, in three models.** The three internal experiments located the choice in different places, and each location fits the behaviour of that model. In Qwen3-8B the states at the task-specification positions carry a ban or an instruction: exchanging them alone reproduces the substitute of the ban on shortest path (0.80) and a forced instruction on shortest path (30 of 30) and connected components (28 of 30), while on the direct-route tasks the condition span carries it. In gemma-3-4b-it, which writes two algorithms for one prompt, the choice is made at a single generated token after a shared opening, and edits at the task-specification positions do nothing. In Qwen2.5-7B-Instruct the algorithm is verbalisable at the token that names it and not 170 tokens later, and edits work only at the generated-token site. In all three the read position is inert as a carrier: its exchange transfers nothing on six Qwen3-8B tasks, Gemma's readout there is no better than the text, and the NLA reads only the format line there. The finding of iteration 3 that a ban gives way at the opening of the program body and the fork of Gemma at response index 32 point at the same moment from two models: the first statement of the body that is specific to an algorithm, after an opening shared by every algorithm.

**The top-five prohibition in two families.** Both models answer a five-name ban by writing a banned algorithm (avoidance 0.00 in Qwen3-8B in iteration 2, in its bf16 rerun here and in Gemma). In Gemma the ban flips the model from its default DFS to its minority BFS and halves its pass rate; in activation space the ban's prompt states sit beside a banned centroid. The activation version of the prohibition breaks programs before it moves the algorithm.

**Novelty, audited again.** No artifact of this iteration found a correct novel algorithm (Table 278).

**Table 278.** Novelty audits of iteration 6. Sources: the novelty audit files of the five artifacts.

| Artifact | Pool | Correct programs outside the catalogue | Final classes | Novel |
|-|-|-|-|-|
| Record audit | the 14 transplant programs that two of three judges had called novel in iteration 5, plus 10 controls and 17 related programs | 14 disputed | known outside the catalogue 10, catalogue variant 2, degenerate 2 | 0 |
| Engine control | every correct off-default or other program, against 18,237 known solutions | up to 237 per engine and task | variants and distant programs of known algorithms (nearest-known pass only) | not judged |
| Exchange and site experiment | every correct program labelled other | 2 | catalogue variant 2 | 0 |
| Gemma feature experiment | 1,450 correct programs | 1 | catalogue variant | 0 |
| NLA experiment | every correct program labelled other, all arms | 10 | labeller miss 8, degenerate 2 | 0 |

## 6.10 What iteration 6 established, what it ruled out, and what it abandoned

Everything below is one model per claim except where a second family is named, at 4B to 8B parameters, on memorised tasks in the style of LeetCode.

**Established.**

1. *Iteration 4's random-push escapes are a property of Qwen3-8B, not of 8-bit floating-point rounding.* At the same absolute displacement, the same 40 directions and the same slots, bf16 escapes on connected components at 0.65 against 0.725 under W8A8 and on shortest path at 0.15 against 0.20, with per-direction shares ranked alike (Spearman 0.96 and 0.87), and per-sample plan noise reproduces (25 and 22 of 50 against 30 and 22). Activation rounding alone adds nothing; a 5-point per-slot boost on connected components comes from the 8-bit floating-point weights or the native kernel. Iteration 5's bf16 null belongs to its ban-free unit or its direction seeds.
2. *In Qwen3-8B the substitute of a ban and the algorithm of an instruction are carried by the residual states at the task-specification positions on the prompt-route tasks.* Exchanging those states alone transfers the ban on shortest path (0.80) and kth smallest (0.57), and a forced instruction on shortest path (30 of 30) and connected components (28 of 30); matched-norm random exchanges and a placebo twin transfer at most 0.13. The condition span carries the ban on the direct-route tasks (two sum 1.00, find duplicate 0.90). The read position carries nothing.
3. *Gemma's BFS-or-DFS choice is made at one generated token,* ` visited` against a blank line, `if` or `queue` at response index 32, about 138 tokens before any algorithm-identifying code, and is readable from the residual stream at that position across prompts (Lasso on SAE codes R-squared 0.66 against 0.18 for text, preregistered; ridge on the raw state 0.72, post hoc).
4. *Steering the fork works and costs correctness.* Difference in means moves the fork 2.3 times as far as the SAE clamp at matched norm, both move the plan equally at matched effect, and every edit toward the minority algorithm breaks programs; edits toward the default are clean.
5. *The NLA does not verbalise the planned algorithm at pre-code positions in Qwen2.5-7B-Instruct,* although it names an algorithm at the token where the prompt names it; an outside reader of the text predicts the realised algorithm better than the NLA.
6. *Record repairs.* The landing half is descriptive (17 of 21 per set, 5 of 8 where the twin wrote no alternative, p 0.053); the movability half is not a strong predictor with a moderate relation not excluded (0.15, interval -0.44 to 0.65); the 14 disputed programs are not novel.

**Ruled out, or not supported.**

- *Activation rounding as the cause of the escapes* (the engine claim's preregistered account): W16A8 escapes like bf16 or slightly less, on both tasks.
- *The Stage A rule of the localization claim* as preregistered: the task-specification states of two sum also transfer brute force at 0.43, above the predicted 0.2.
- *A feature claim for Gemma Scope 2:* the SAE clamp never beats difference in means, and the preregistered feature rule is met by random latents.
- *The verbal readout claim:* 0 of 16, 0 of 112 and 0 of 96 at the end of the prompt; the preregistered verbal edit moves nothing at the prefill site.
- *State noise against token temperature at matched KL* in bf16: 12:6 and 7:3 at alpha 2, not significant.

**Withdrawn.**

- *The prefill-site claim in its preregistered form* in bf16: no common support for the condition span, and breakage at alpha 8. Its post-hoc form (alpha 4 or less) puts the read position below the task-specification site on both tasks.

**Dead ends, with the evidence that closed them.**

- *8-bit floating-point numerics as an explanation of anything in this run's internal results:* closed by Table 237 and Table 239.
- *The read position as a carrier of the choice:* zero transfer in six Qwen3-8B tasks (Tables 244 to 249), no readout beyond text in Gemma (Table 261), only the format line in the NLA explanations.
- *The released layer-20 NLA as a readout of algorithm plans in code:* code is out of distribution for it (fraction of variance explained 0.39 to 0.45), and its pre-code explanations name no algorithm.

**Planned but not run.** DAS in Qwen3-8B (Stage B), the mediation, discreteness and resampling claims, the temperature half of the token claim, and the causal manifold (Section 6.8).

## 6.11 What the next iteration takes from this one

The plan-variable account was tested in part, and its two halves came out differently. Where the choice is held is now measured in three models: the task-specification states in Qwen3-8B for bans and instructions on the prompt-route tasks, one generated token in Gemma, and nothing verbalisable before the code in Qwen2.5-7B-Instruct. Whether the choice is a low-rank variable in Qwen3-8B, and whether random pushes act through it, is untested, because the DAS experiment was lost at planning. The engine control has removed the obstacle that made such a test look premature: random pushes at iteration 4's absolute unit move the algorithm in bf16 as they did in 8-bit floating point, so the escapes are a stable target that a fitted plan subspace can be asked to explain. The next measurements are DAS at the task-specification positions of shortest path and kth smallest, with the Stage A exchanges as the full-state ceiling, and the projection of iteration 4's 40 directions onto the fitted subspace.

Three leads come with it. The ban-free unit moves fewer programs than the ban unit at a larger scalar dose, so its per-position and per-block profile, or the direction seeds, decide movability; a controlled comparison of the two units on the same seeds would say which. Gemma's one-token fork offers a clean site where DAS already captures the choice in one direction; whether a smaller push there switches the algorithm without breaking the program is the question for a usable knob. And two sum's task-specification states carry part of a ban that iteration 3 had classed as direct, so the route classes are not all-or-none.

