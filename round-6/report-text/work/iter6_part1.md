# Iteration 6: an engine control, where a ban and an instruction are carried, a one-token fork in Gemma, and the plan in words

## 6.1 Why this iteration ran what it ran

**The review of the iteration-5 record.** The review was blocking for the fourth time. It raised five major items, all marked must fix, and four minor ones. The first went to the run's main internal result. Every plan-noise positive of iteration 4 had come from an 8-bit engine with FP8 W8A8 linear layers (e4m3 weights per output channel, e4m3 activations with a per-token scale), while iteration 5's bf16 knob experiment found per-sample plan noise nearly inert: connected components moved in 1 of 50 programs at alpha 2 against 30 of 50 under the 8-bit engine. The record had left the cause open, had not reported the knob experiment's own measurement of the dose it delivered, and still listed iteration-4 items 2 to 4 as established. The review asked for a decisive control: the same directions and slots at the same absolute displacement under the 8-bit engine, under FP8 weights with bf16 activations and under bf16. The second item found the landing half of the narrowed repertoire account overstated. Its tally of 16 of 19 omitted the iteration's own bf16 remeasurement, and it never scored the instruct twin's own minority algorithm as a rival, although that rival explained half the hits. The third item asked for the power and interval behind the claim that the movability half was ruled out, and for the frozen rivals on the pooled set. The fourth listed executed outputs missing from the record: the literal cell's phrasing columns, the prices at Hill-1 1.5 and 2, the knob experiment's dose file, panel B's knob rows and three Llama rows of Table 126c. The fifth said that after five iterations the record still had no internal account of how the choice manifests, which is the request's central question, and that its one internal positive rested on the 8-bit engine. The minor items asked for the per-task counts behind item 4 of Section 5.11, the fill rule for undefined Gemma forecasts, a sentence on the three new tasks whose instruct twins are already mixed, and a second blind adjudication of the 14 transplant programs that two of three judges had called novel. Table 224 maps every item to its answer.

**Table 224.** Review items on the iteration-5 record and where this report answers them.

| Review item | What the review found | Where it is answered |
|-|-|-|
| Engine | The 8-bit plan-noise effect does not replicate in bf16 at near-matched dose; the dose file unreported; iteration-4 items 2 to 4 still established; plan-sampler and movability verdicts not tagged with their engine | Corrections in Sections 4.2.6, 4.10, 5.2, 5.10, 5.11 and 5.12; Section 6.2.2; the four-engine control, Section 6.3 |
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

Eleven claims were preregistered, each with a rule committed by sha256 before its first decisive sample. We name them by their content rather than by their codes.

- *The engine claim* (primary): on connected components and shortest path, the same 40 directions and common-random-number slots at the same absolute displacement under four numerics. Activation rounding is the cause if the escape fraction under bf16 weights with FP8 activations (W16A8) exceeds bf16 by at least 0.2, the full 8-bit engine (W8A8) matches W16A8 within 0.1 and FP8 weights with bf16 activations (W8A16) match bf16 within 0.1, on both tasks. The result is called not reproduced if W8A8 minus bf16 is below 0.1.
- *The localization claim* (primary). Stage A, with no training: exchanging the full residual states of the ban prompt into the neutral twin transfers the ban's substitute at a transfer share of at least 0.5 on at least two of shortest path, kth smallest and connected components, at a pass rate of at least 0.8 times the twin's, and at most 0.2 on two sum and find duplicate. Stage B: DAS at one layer recovers at least 0.8 of the full-state transfer at a rank of 16 or less on held-out templates.
- *The mediation claim* (primary): the energy that a random direction puts into the fitted plan subspace predicts which directions switch the algorithm (Spearman at least 0.5).
- *The discreteness claim*, *the token claim* (temperature leaves the plan coordinate flat while state noise at generated tokens beats temperature at matched per-token KL) and *the resampling claim* (resampling the plan as a diversity knob) (secondary).
- *The verbal readout claim* (secondary): the NLA names the substitute of a ban before any code is written at a rate at least 0.3 above a judge reading the visible text; editing the explanation's algorithm phrase and reconstructing transfers the algorithm by at least 0.2.
- *The feature claim* (secondary): in Gemma's natural BFS against DFS split on the grid task, Gemma Scope 2 features decode the upcoming algorithm at least 0.10 balanced accuracy above a classifier on the visible text, and steer at least as well as a difference-in-means direction at matched pass.
- *The site rerun* (secondary): the iteration-4 noise-site comparison in bf16; the prefill-site claim survives if the task-specification site beats the read position and the condition sentence at matched downstream displacement on at least one task, and is withdrawn otherwise.
- *The landing contest* (secondary): the base runner-up against the instruct twin's own teacher-forced ranking of algorithm openings, on every recorded push-landing event.
- *The novelty count* (secondary).

**The strategy.** Seven artifacts were planned (Table 225). One evaluation on CPU repaired the record from rows on disk and ran the second novelty adjudication. The engine control ran the four numerics on a single 16 GB card, the only GPU with FP8 tensor cores available. A bf16 experiment ran the Stage A exchanges, the site rerun, state noise against matched temperature, the top-five push and the landing contest. Gemma and the NLA each received their own experiment, and a research artifact searched the literature for each claim. The seventh artifact, which was to fit the DAS subspaces of Stage B and run the mediation, discreteness, resampling and temperature-coordinate tests together with a manifold of plan coordinates, was lost before it existed: the planning agent returned no plan. Section 6.8 records it as planned and not run. Every Qwen3-8B number of this iteration except the engine control's comes from a bf16 engine.

**Table 225.** The artifacts of iteration 6, the question each was asked, and its hardware and spend.

| Artifact | Question | Model and hardware | OpenRouter spend |
|-|-|-|-|
| Record audit [ARTIFACT:art_aRTQM6CQ0Dre] | Repair the iteration-5 record (36 corrections); re-adjudicate the 14 disputed transplant programs blind | No generation; CPU only | USD 0.29 |
| Engine control [ARTIFACT:art_lpQalcAXMGr1] | Are iteration 4's random-push escapes a property of the model or of the FP8 W8A8 engine? | Qwen3-8B under four numerics built from one bf16 snapshot; one 16 GB RTX 2000 Ada; 6,075 generated programs plus reused iteration-4 rows; 4.1 GPU hours of generation | USD 0.085 |
| Exchange and site experiment [ARTIFACT:art_rMlbrjVB1c__] | Where is a ban carried; does the noise-site claim hold in bf16; state noise against matched temperature; the top-five push; the landing contest | Qwen3-8B bf16 with the input embedding table on CPU, one 16 GB RTX 2000 Ada; 4,320 programs and 1,220 teacher-forced passes; about 2.7 GPU hours | USD 0.055 |
| Gemma feature experiment [ARTIFACT:art_zNyBP6zieI5u] | Where does Gemma's BFS-or-DFS choice fork; do Gemma Scope 2 features read and steer it better than difference in means, random features and DAS? | gemma-3-4b-it bf16, one 16 GB RTX 2000 Ada; about 2.1 GPU hours of generation | USD 0.034 |
| NLA experiment [ARTIFACT:art_dbUtqBjT0tPf] | Does the residual stream say in words which algorithm will be written, and can a verbal edit steer it? | Qwen2.5-7B-Instruct bf16 with the released layer-20 NLA pair, one NVIDIA L4; about 2.0 GPU hours | about USD 2.0 |
| Positioning audit [ARTIFACT:art_OUuQUYQn5voE] | Set the iteration-6 claims against published work | Web search and quote checks | none recorded |
| DAS and plan-coordinate experiment | Stage B of the localization claim; the mediation, discreteness, resampling and temperature-coordinate tests; the causal manifold | Planned for Qwen3-8B bf16; lost at planning | not run |

## 6.2 The record audit: corrections, engine tags and a second novelty adjudication

The record audit [ARTIFACT:art_aRTQM6CQ0Dre] generated no model text. It recomputed from the row files of the earlier artifacts every number the review touched, tagged each internal result with the numerics that produced it, and wrote each change as a verbatim replacement keyed to the report. Of the values behind its corrections, 78 matched the record, 18 were new, 2 were carried from earlier evaluations and 1 was corrected: the power of the movability test, recorded as 0.46, is 0.63 for the registered one-sided test and 0.50 two-sided. A standard-library re-derivation passed 277 of 277 checks, its five placebos failed as they should, and a second script reproduced 7 of 7 headline numbers from the rawest files. Judge spend was USD 0.29 over four passes.

### 6.2.1 The corrections

Twenty-nine of the 36 corrections are applied in place in Sections 4 and 5 and marked as iteration-6 corrections. The seven that target the closing section are folded into the closing section, which is rewritten at the end of this iteration. The audit ran in parallel with the engine control, so its engine tags were written before the control's result existed; where the control supersedes them, the in-place text adds a pointer to Section 6.3. Three further notes of the same kind mark the frozen screen of Section 4.2.6, the movability paragraph of Section 5.10 and the caption of Table 222. Table 226 lists every correction.

**Table 226.** The 36 corrections of the iteration-5 record (values behind each: M match, N new, C carried, X corrected). Source: record audit `corrections.json`.

| Id | Location | What changed | Values |
|-|-|-|-|
| C6-001 | Section 5.2, dose units | The two dose definitions (ratio of mean norms against mean of per-position ratios) reconciled per task | 14 M, 6 N |
| C6-002 | Table 222 caption | The two plan-noise columns put on one definition | 20 M |
| C6-003 | Section 5.10, movability paragraph | Shortest path counts restated per definition; dose-bracketed contrast and its tags | 2 M, 5 N |
| C6-004 | Section 4.10, preamble | Engine class of iteration 4 named | 1 N |
| C6-005 | Section 4.10, item 2 | Same-seed contrast tagged as 8-bit only | 1 C |
| C6-006 | Section 4.10, item 3 | Site odds ratio tagged as 8-bit only | 1 C |
| C6-007 | Section 4.10, item 4 | Plan-noise prices tagged with their engine and unit | 4 M |
| C6-008 | Closing | Internal claims that survive the engine change (folded into the new closing) | none |
| C6-009 | Closing | Dose bracket removes a scalar dose shortfall (folded) | none |
| C6-010 | Closing | Site claim tagged as 8-bit (folded) | none |
| C6-011 | Section 5.10, figure | The base-variety figure redrawn like for like under bf16 | 2 M |
| C6-012 | Section 5.11, item 2 | Landing half moved to the descriptive results; tally per set and the twin-minority rival | 7 M, 1 N |
| C6-013 | Section 5.11, item 2 | Gemma fill rule; defined-only mean 1.57 | 2 M, 1 N |
| C6-014 | Section 5.12 | Landing half restated as descriptive, with its tally | none |
| C6-015 | Closing | Landing tally per set (folded) | none |
| C6-016 | Section 5.10 | Landing tally of 16 of 19 replaced by 17 of 21 per set | 4 M |
| C6-017 | Table 129 | Row label 'everywhere' replaced by 'on all 13 events' | none |
| C6-018 | Table 129 | Same, for the largest-excess row | none |
| C6-019 | Section 5.11, item 3 | Three mixed instruct twins; two units where the twin is more diverse than the base | 4 M |
| C6-020 | Table 203 | Base support counts per panel B event | none |
| C6-021 | Table 214 | Base support counts per Gemma unit | none |
| C6-022 | Table 217 | Base support counts per Gemma landing event | none |
| C6-023 | Section 5.11, movability half | Interval, power and pooled rivals; verdict restated | 1 M, 1 X, 1 N |
| C6-024 | Closing | Movability interval and power (folded) | none |
| C6-025 | Section 5.12 | The shrinkage of the movable set: what is ruled out | none |
| C6-026 | Section 5.11, dead end | Plan noise as a knob tagged with its design | none |
| C6-027 | Table 206 | Phrasing clusters per temperature in the literal cell | 4 M, 1 N |
| C6-028 | After Table 208 | Table 207b: prices at Hill-1 1.5 and 2 with bootstrap intervals | 5 M |
| C6-029 | Section 5.5 | Table 203b: panel B knob rows | 2 M, 1 N |
| C6-030 | Table 126c | The three Llama present-minor ban rows completed | 3 M |
| C6-031 | Section 5.11, item 4 | Plan noise against matched decoding restated per task | 2 M |
| C6-032 | Section 5.4 heading | Mixed instruct twins noted | none |
| C6-033 | Section 5.5 heading | Same note | none |
| C6-034 | Closing | Mixed instruct twins (folded) | none |
| C6-035 | Closing | Second novelty adjudication (folded) | 2 M, 1 N |
| C6-036 | Section 4.9 | Second novelty adjudication noted | none |

### 6.2.2 Engine and dose

The two artifacts that the review compared recorded off-default shares on different definitions: the bf16 knob experiment counted correct programs off the default over all samples, the 8-bit plan-noise experiment valid attempts off the default over all samples. The dose definitions differ as well. Table 174 gave the ban-free unit as a ratio of mean norms, while the knob experiment measured a mean of per-position ratios, which is larger because a mean of ratios is not a ratio of means (Table 227). By either definition the bf16 alpha-2 cell of iteration 5 delivered at least 1.24 ban units, so a dose-bracketed contrast sets it against the 8-bit alpha-1 cell, which delivered 1.00. A lower bf16 share in that comparison cannot come from a shortfall of the scalar dose.

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

Table 228 gives the contrast under both share definitions. The rule, fixed before computing, tags a task as not replicated when the bf16 share falls short at the 8-bit engine's matched alpha (Fisher p) and in the dose bracket. Connected components and shortest path meet it, kth smallest and the grid task do not, and two sum and find duplicate had no 8-bit effect of at least 10% at alpha 2 or less to replicate. These tags compare iteration 5's design (bf16 with the ban-free unit and fresh direction seeds) with iteration 4's design (the 8-bit engine with the ban unit); they cannot say which of the three differences is responsible. Section 6.3 separates them.

**Table 228.** Per-sample plan noise, iteration 5's bf16 cells against iteration 4's 8-bit cells, on two definitions (counts off the default over N). Source: record audit `tables/engine_pn_contrast.csv`.

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

**Table 229.** Internal results by engine class, with the audit's tag and the status after the four-engine control. Source: record audit `tables/engine_labels.csv`; engine control `results/relabel_table.json`.

| Id | Result | Engine class | bf16 counterpart (audit) | Audit tag | Status after Section 6.3 |
|-|-|-|-|-|-|
| E01 | Plan-noise 5-point Hill-1 2.72 on kth smallest | 8-bit W8A8 | 1.98 at the ban-free unit | not established | not rerun (kth smallest dropped from the engine control) |
| E02 | Plan-noise 5-point Hill-1 2.09 on connected components | 8-bit W8A8 | 1.09; 1 of 50 correct off the default | did not replicate in bf16 at the population level | model property: at the absolute unit bf16 plan noise moves 25 of 50 valid attempts against 30 of 50 |
| E03 | Plan noise moves shortest path 26% at alpha 1 | 8-bit W8A8 | 0 of 50 at alpha 1, 2 of 47 at alpha 2 | did not replicate in bf16 at the population level | model property: 10 of 50 against 12 of 50 at alpha 1, 22 of 50 against 22 of 50 at alpha 2 |
| E04 | Plan noise on the grid task, 0.24 at alpha 2 | 8-bit W8A8 | 1 of 38 correct | not established | not rerun |
| E05 | Site odds ratio 5.72 | 8-bit W8A8 | none | 8-bit only, untested in bf16 | bf16 site rerun (Section 6.4.2): committed rule withdrawn; post-hoc model puts the read position below the task-specification site |
| E06 | Same-seed contrast, 17.25 of 20 seeds | 8-bit W8A8 | none | 8-bit only, untested in bf16 | not rerun; its per-sample plan noise reproduces in bf16 at the absolute unit |
| E07 | 40-direction escape fractions | 8-bit W8A8 | 8 bf16 directions at the ban-free unit: kth smallest 0.25, connected components 0.125, others 0 | did not replicate on shortest path, two sum, grid and find duplicate; replicated, smaller, on kth smallest and connected components | model property on connected components (0.65 against 0.725) and shortest path (0.15 against 0.20) at the same 40 directions and absolute unit |
| E08 | Frozen screen: six movable tasks | 8-bit W8A8 | bf16 remeasure: two movable | did not replicate (4 of 6 lose 'movable') | the escapes behind it reproduce in bf16 at the absolute unit on the two tasks tested; the shrinkage belongs to the ban-free unit or its seeds |
| E09 | Plan-subspace tests | 8-bit W8A8 | none | 8-bit only, untested in bf16 | untested (the DAS experiment was not run) |
| E10 | Connected components screen escape from a bf16 direction | bf16 | itself | bf16 result | unchanged |
| E11 | Pre-selected directions 9002 and 9004 move in both engines | 8-bit and bf16 | shortest path Dijkstra 31, Bellman-Ford/SPFA 19 under bf16 against 26 and 24 | replicated in bf16 | unchanged; direction 9004 also moves shortest path under every numerics (Section 6.3) |
| E12 | Plan noise against matched decoding, 19 against 3 | bf16 | itself | bf16 result | unchanged (13 of the 19 on kth smallest) |
| E13 | Transplant results | bf16 | itself | bf16 result | unchanged |
| E14 | Read-position transplant breaks output without moving the algorithm | bf16 | itself | bf16 result | unchanged |
| E15 | Route of a ban | bf16 | itself | bf16 result | extended by the exchange of Section 6.4 |
| E16 | Band patching on kth smallest and connected components | bf16 | itself | bf16 result | extended by the exchange of Section 6.4 |
| E17 | Literal cell, temperature null with thinking on | vLLM FP8 W8A16 (weight only) | none needed | behaviour level, engine-robust | unchanged |
| E18 | Temperature changes phrasing, not the algorithm | vLLM FP8 W8A16 | bf16 temperature 1.3 cells show no diversity | behaviour level, engine-robust | unchanged |
| E19 | Llama knob rows | vLLM bf16 | itself | bf16 result | unchanged |
| E20 | Novelty audits | sandboxed CPU scoring | not applicable | behaviour level, engine-robust | unchanged |
| E21 | Plan-sampler comparison disconfirmed | bf16 | itself | bf16-conditional | conditional on iteration 5's ban-free unit and direction seeds, not on the numerics |
| E22 | Movability half | bf16 | itself | bf16-conditional | same |
| E23 | Plan noise as the practical knob is a dead end | bf16 | itself | bf16-conditional | same |
| E24 | Six screen-movable tasks shrank to two | bf16 | itself | bf16-conditional | same |

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

The movability verdict is restated with its interval and power (correction in Section 5.11). Over the 13 new units, Spearman between the base off-default share and the escape fraction is 0.15, with a Bonett-Wright 95% interval from -0.44 to 0.65, a Fieller interval from -0.46 to 0.66, a BCa bootstrap interval from -0.50 to 0.70 and a one-sided permutation p of 0.317. At a true correlation of 0.6, the registered one-sided permutation test has power 0.63 (0.50 two-sided, the figure the record had quoted as 0.46), and 20 units would give 0.8. The data exclude a strong relation, not a moderate one. The pooled value also leans on one unit: count inversions' committed base share of 0.75 came from attempts, because only 15 base programs were correct and 58 of its 87 attempts are labelled other; on the correct-only basis of the other twelve units its share is 0.13 and the pooled Spearman falls to 0.035.

**Table 231.** The 15 new units under one definition of each frozen rival (base share beta; escape fraction E; opening margin; novelty-instruction excess; twin modal share; catalogue size K; runtime merit, the natural log of the default's runtime over the fastest reference's). Source: record audit `tables/movability_units.csv`.

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

In iteration 5 two of three judges had called 14 of the 48 correct transplant programs outside the catalogue novel, and the zero count rested on the executor's manual read. The audit stress-tested each program in a sandbox at the specification's maximum size and on adversarial cases, retrieved its three nearest known solutions by Zhang-Shasha tree edit distance [64], and had two judges from model families the run had never used classify it blind: Mistral Medium 3.1 (three calls at temperature 0, Fleiss kappa [128] 1.00 across the calls) and Kimi K2. Ten controls of known class were mixed in, and both judges passed the control gate at 9 of 10. All 14 programs pass their hidden tests; one, a repeated maximum selection on top-k frequent, times out at the maximum size. Mistral called 1 of 14 novel and Kimi 0 of 14 (Table 234). The one program called novel, a first-and-last-position solution, is range guards plus a linear scan to the first match and over its run; it passes 56 of 56 hidden tests and every stress group, and the executor's full read classes it as a linear search. The final count is 0 novel of 14. Agreement with the manual verdict on the 14 is 0.86 raw (95% interval 0.57 to 0.98), Gwet's AC1 [127] 0.83 and Cohen's kappa 0.71; with the controls included (24 items) kappa is 0.80 [0.57, 1.00]. The final read corrected one manual class: program P21 is a linear scan plus a count of each element, a degenerate program rather than a catalogue variant.

**Table 234.** The 14 disputed transplant programs: task, iteration-5 manual class, the majority class of Mistral Medium 3.1 (three calls), Kimi K2's class, and the final class. Source: record audit `tables/novelty_readjudication.csv`, `audit/final_read.json`.

| Program | Task | Iteration-5 manual class | Mistral Medium 3.1 | Kimi K2 | Final class |
|-|-|-|-|-|-|
| P33 | first and last position | known, outside the catalogue | known, outside the catalogue (linear search) | known, outside the catalogue | known, outside the catalogue |
| P31 | first and last position | degenerate | degenerate | degenerate | degenerate |
| P12 | first and last position | known, outside the catalogue | known, outside the catalogue | known, outside the catalogue | known, outside the catalogue |
| P37 | first and last position | known, outside the catalogue | known, outside the catalogue | known, outside the catalogue | known, outside the catalogue |
| P21 | first and last position | catalogue variant | degenerate | degenerate | degenerate (corrected) |
| P13 | first and last position | known, outside the catalogue | novel (3 of 3 calls) | known, outside the catalogue | known, outside the catalogue (linear search) |
| P30 | first and last position | known, outside the catalogue | known, outside the catalogue | known, outside the catalogue | known, outside the catalogue |
| P09 | first and last position | known, outside the catalogue | known, outside the catalogue | known, outside the catalogue | known, outside the catalogue |
| P32 | first and last position | known, outside the catalogue | known, outside the catalogue | known, outside the catalogue | known, outside the catalogue |
| P28 | first and last position | known, outside the catalogue | known, outside the catalogue | known, outside the catalogue | known, outside the catalogue |
| P05 | first and last position | known, outside the catalogue | known, outside the catalogue | known, outside the catalogue | known, outside the catalogue |
| P38 | connected components | catalogue variant | catalogue variant (union find) | known, outside the catalogue | catalogue variant |
| P10 | top-k frequent | catalogue variant | catalogue variant (sort by count) | catalogue variant | catalogue variant |
| P06 | top-k frequent | known, outside the catalogue | known, outside the catalogue (binary search on a frequency threshold) | known, outside the catalogue | known, outside the catalogue |

Across four judge passes Mistral's novel calls on the 14 were 0, 0, 1 and 1 and Kimi's 0 in every pass; the first two passes carried run-dependent timings in their prompts. No pass produced a novel call that survived a full read.

