# Iteration 5: the base model's repertoire against nudge movability, a transplant of base plan states, text-level plan samplers and a second family

## 5.1 Why this iteration ran what it ran

**The review of the iteration-4 record.** The review was blocking again. It raised five major items, all marked must fix, and three minor ones, and each pointed at a place where the record said more than its own artifacts. The held-out test of the movability claim had been written up as inconclusive under every sensitivity, but one preregistered sensitivity, compliance measured as the drop in the share of the default, disconfirms it, and two of the three true positives behind the positive rank correlation were compromised: the grid task had no default (its Gemma twin wrote BFS 25 and DFS 25), and the shortest path task's compliance rested on array-based Dijkstra read as Bellman-Ford/SPFA. The site conclusions said the read position and condition sentence changed no algorithm "at any dose", although the energy-matched read position had moved two tasks, and they called the task-specification states the site of the choice, although noise in generated tokens 1 to 32 redirected it as well and beat the plan site on find duplicate. Several landing conclusions generalised from connected components alone or compared forecasts on unmatched event sets. Executed results bearing on the primary claim were missing: plan noise on the plain prompt, the edge-only hull deviation, the Llama block of the knob table, the dose unit of each experiment and one artifact's GPU hours. And the closing summary quoted maxima over directions as if they were typical effects, while the lead it chose for the next iteration, signed progress toward the runner-up, rested mostly on one task. The minor items asked for the positioning rows the iteration-4 audit had verified but not carried over, for exposure arms to be declared controls, and for the literal cell of the request (thinking on, top-k 10, same seed). Table 166 maps every item to its answer; the corrections are applied in place in Sections 3.2.5 and 4.2 to 4.11 and marked as iteration-5 corrections.

**Table 166.** Review items on the iteration-4 record and where this report answers them.

| Review item | What the review found | Where it is answered |
|-|-|-|
| Held-out verdict per compliance measure | Default-drop sensitivity disconfirms; grid task has no default; shortest path true positive rests on a mislabel | Corrections in Sections 4.7 and 4.10; Tables 169 and 170, Section 5.2; closing section |
| Site conclusions | 'At any dose' contradicted by the energy-matched read position; generated-token noise also redirects the choice; PARTIAL rule listed as established | Corrections in Sections 4.4, 4.10 and 4.11; closing section |
| Landing conclusions | Route-landing lead from one task; Gemma 4 of 4 includes two compromised events; forecasts compared on unmatched events; landing depends on the site | Corrections in Sections 4.2.2, 4.6 and 4.10; Table 171, Section 5.2 |
| Missing executed results | Plan noise on the plain prompt; hull deviation; Llama block; dose units; GPU hours | Corrections in Sections 4.1, 4.2.1, 4.3 and 4.9; Tables 126c, 139, 173 and 174 |
| Best cells and the next lead | Maxima quoted as effects; split-half on four of six tasks; signed progress concentrated on one task; alpha-4 depths | Corrections in Sections 4.2.1, 4.4, 4.10 and 4.11; Tables 175 to 178; the next budget went to new tasks (Sections 5.4 and 5.5) |
| Minor: positioning rows | NC-GRPO, Nagarajan et al., Bhushan et al., Maveli et al. and two ICLR 2027 submissions verified but not carried | Rows added to Table 92c in Section 4.8 |
| Minor: exposure arms as knobs | Exposure prompts supply the alternative's text | Class rule corrected in Section 3.2.5; Table 172 |
| Minor: the literal 1a-c cell | Thinking-on arm ran without top-k 10 | Correction in Section 4.5; cell run in Section 5.7 |

**The hypothesis update.** The update kept the plan-noise lead of iteration 4 and asked what sets its boundary. Plan noise moved the algorithm on some tasks and on no others, and where it moved it, it landed on one runner-up per task. On the two path tasks those runners-up were exactly the algorithms the untuned base model writes next to its default: under the chat template Qwen3-8B-Base wrote BFS in 49 of 57 correct grid programs and Dijkstra in 63 of 90 correct shortest path programs, with DFS and Bellman-Ford/SPFA second (Section 1.9). The update therefore proposed what it called the narrowed-repertoire account: post-training narrowed a choice that the base model makes more evenly, the narrowed choice is set while the model reads the task specification, and a nudge to those states undoes part of the narrowing, reopening the base model's alternatives and only those. A task that no nudge moves would then be one on which the base model itself writes almost one algorithm, and post-training [35, 57, 87] would have narrowed only what pretraining left open.

We use the following quantities throughout. The *base off-default share* of a task, beta, is the share of the base model's correct programs that use an algorithm other than the instruct model's default, with both models given identical chat-templated token ids; the *base runner-up* is the base model's most frequent correct algorithm other than that default. A task is *base-diverse* when beta is at least 0.2, *base-collapsed* when beta is below 0.05, and intermediate between. The instruct default comes from a twin of at least 50 samples as the modal correct label with a share of at least 0.6; a task below that has *no default* and enters no movability or landing test. One *ban-free unit* is the residual norm of the task-specification states times the median ratio, in Qwen3-8B at the same relative depth, of a ban's displacement to the residual norm; it replaces the ban's own displacement as the dose unit everywhere, so that a task's dose no longer depends on how far its ban moved it. We call the edit h ← h + lambda (h_base − h_instruct), applied during the instruct prefill at every task-specification position of blocks 12 to 23 with the base states computed on the same prompt, a *transplant of base plan states*, in the spirit of cross-model activation patching [88].

Eight claims were preregistered, each with its rule committed by sha256 before its first decisive sample.

- *The movability half: the base repertoire predicts which tasks move* (primary): across new tasks, beta ranks the escape fraction of 8 fixed random directions at Spearman of at least 0.6 with a parent-cluster permutation p below 0.01, at least 80% of base-collapsed tasks are immovable, and beta is ahead of each rival. Disconfirmed if Spearman is below 0.3 or most base-diverse tasks are immovable.
- *The landing half: landings follow the base runner-up* (primary): on movable new tasks the push landing is the base runner-up in at least 70% of events (exact test against per-event chance, p below 0.05), and the base composition beats the association forecast by at least 0.10 nats in log score.
- *The transplant claim* (primary, causal): on at least two thirds of the base-diverse tasks among the 15 existing ones, the transplant at its best lambda (with pass of at least 0.8 times the twin's) reaches a correct off-default share of at least half of beta, beats a matched-norm random displacement and a cross-task base shift (another task's base-minus-instruct direction at the same norm) on paired flips, and lands on the base runner-up; base-collapsed tasks and a read-position transplant stay within 0.05 of the twin.
- *The plan-sampler comparison* (secondary): plan noise prices at least as well as the best of four text-level plan samplers on at least 3 of the 5 tasks movable on fresh draws: intent factored generation [73], plan search [74], enumerate-and-pick (the model lists algorithms and an external random draw picks one) and a base-written intent (the base model writes a one-sentence intent and the instruct model writes the code).
- *The de-sharpening push* along the base-minus-instruct direction escapes at no more than half the norm a random push needs (secondary).
- *The Gemma replication* (secondary): both halves in gemma-3-4b-pt against gemma-3-4b-it [76], a replication on fresh samples because Gemma's iteration-4 outcomes were seen.
- *The literal cell* of the request (descriptive) and *the novelty count* (secondary).

**The strategy.** Seven artifacts ran (Table 167). One CPU-only evaluation repaired the iteration-4 record from rows on disk and froze eight rival task predictors by hash before reading any outcome. The transplant experiment measured the base repertoire of all 15 existing tasks, committed it, and only then ran the transplant with its controls. Two panels built new coding tasks, committed each task's base repertoire, and only then pushed the instruct model; they split the new tasks between them so that the pooled confirmation would have more units than either could build alone. The knob experiment ran the text-level plan samplers and departure-matched decoding (a decoding temperature set so that the output departs from the twin as much as under plan noise) on all 15 existing tasks, and the literal cell. The Gemma experiment repeated both halves and the transplant in a second family, and a research artifact searched the literature for each new claim. The 16 GB card of iteration 4 was replaced by cards of 23 to 24 GB, so every Qwen3-8B experiment of this iteration ran in bf16 rather than with 8-bit linears; this change of engine, together with the change from the ban unit to the ban-free unit, turns out to matter (Section 5.10).

**Table 167.** The seven artifacts of iteration 5, the question each was asked, and its hardware and spend.

| Artifact | Question | Model and hardware | OpenRouter spend |
|-|-|-|-|
| Record audit [ARTIFACT:art_mgek9PfVBNbh] | Repair the iteration-4 record (35 corrections); freeze eight ban-free rival task predictors | No generation; CPU only | USD 0.021 |
| Transplant experiment [ARTIFACT:art_CcZLW-9NX00l] | Base repertoire of the 15 existing tasks; does a transplant of base plan states reopen it (the transplant claim); de-sharpening push; reverse transplant | Qwen3-8B and Qwen3-8B-Base, bf16, one RTX 4090; 14,280 programs; 1.70 GPU hours | USD 0.29 |
| Panel A [ARTIFACT:art_8WbrpoEFslk9] | The movability and landing halves on new tasks (majority element to median of two sorted lists); the 15 existing tasks re-measured on the ban-free unit | Same models, bf16, one RTX 4090; 8,390 programs; 0.98 GPU hours of batch time | USD 0.357 |
| Panel B [ARTIFACT:art_9a8LrIv2lHbV] | The movability and landing halves on seven more new tasks; disguised variants of eight bench tasks | Same models, bf16, one RTX 4090; 14,600 programs; 1.74 GPU hours | USD 0.192 |
| Knob experiment [ARTIFACT:art_jR6Pyy3W9xum] | Plan noise against text-level plan samplers and departure-matched decoding (the plan-sampler comparison); the literal cell | Qwen3-8B bf16 (HF) and the official 8-bit checkpoint (vLLM, literal cell), one RTX 4090; 7,060 labelled knob rows and 100 traces; 1.88 GPU hours plus 15 minutes | USD 0.12 |
| Gemma experiment [ARTIFACT:art_hG0QPiaIPNhP] | Both halves and the transplant in gemma-3-4b-pt against gemma-3-4b-it | Both models bf16, one 23 GB NVIDIA L4; 12,290 programs; 2.16 GPU hours | USD 0.39 |
| Positioning audit [ARTIFACT:art_ObxQOIlAM9MS] | Has prior work restored base-model variety, forecast it, or transplanted base states? | Web search and full-text quote checks | none recorded |

## 5.2 The record audit: corrections from rows on disk, and frozen rival predictors

The record audit [ARTIFACT:art_mgek9PfVBNbh] generated no model text. It answered every review item by recomputing the values behind it from the row files of eight earlier artifacts, and wrote each fix as an exact replacement for the record, with every value tagged by provenance and checked against the record within fixed tolerances (counts exact, rates 0.005, Hill-1 and log scores 0.01, intervals 0.02). Of 187 values that had a record value, 186 matched and 1 was corrected: the record's "22 of 35 cells" for signed progress on connected components is 22 of 24, because the staged file holds 24 block cells per quantity. A further 15 values were new and 4 were carried from the iteration-4 record because their source was not a declared dependency (the knob table cells, the route landings, the Llama block and the iteration-3 direction counts). All six quotes behind the rows added to Table 92c were re-verified live on 2026-10-21. An independent standard-library script recomputed 195 values with no failure, and its four placebos failed as they should (balanced accuracy under permuted escape fractions 0.50; the site odds ratio 1.01 when the plan site and read position are swapped, against 101.7 real; a landing shuffle that shrinks the push advantage from 2.35 to 0.46 nats; rejection of permuted escape fractions at 3.5% to 4.8%). Table 168 lists the 35 corrections and the status of the values behind each.

**Table 168.** The 35 corrections of the iteration-4 record, their location and the values behind them (MATCH: recomputed equal to the record within tolerance; NEW: no record value; CARRIED: from the iteration-4 record). Source: record audit `corrections.json`.

{{T:corrections}}

**The held-out verdict, per compliance measure.** Table 169 restates the Gemma test of iteration 4 under every variant the audit could compute. Under the primary measure, catalogue-only avoidance, the verdict stays INCONCLUSIVE (balanced accuracy 0.74, Fisher p 0.235, Spearman 0.54). Under the preregistered default-drop sensitivity it is DISCONFIRMED (0.57, Fisher p 1.0, Spearman 0.39). Two tasks separate the measures, and Table 170 shows why. The grid twin is tied, BFS 25 and DFS 25 of 50 attempts, so the 'default' DFS came from a 10-sample pilot (correct BFS 4 and DFS 5, attempts 5 and 5) and the ban's avoidance of 0.83 is measured against a baseline that already left DFS half the time; the default share drops by only 0.33. On find duplicate, 38 failing programs labelled other count as leaving the default under the drop measure (catalogue-only avoidance 0.34, drop 0.72). Under the iteration-5 default rule the grid task is the only one with no default, and the first and last position task's rule default (linear scan, 0.86 of the twin) differs from the frozen one. Removing the grid task leaves the verdict inconclusive (0.70); removing both compromised true positives gives 0.61 and Spearman 0.31 (one-sided p 0.144).

**Table 169.** The held-out movability test under every variant (15 tasks unless stated). Source: record audit `tables/table160_variants.csv`.

{{T:gemma_variants}}

**Table 170.** The Gemma twin, the frozen default and the iteration-5 default rule per task, with both compliance measures under the modal ban. Source: record audit `tables/table159_grid.csv`.

{{T:gemma_defaults}}

**Landing forecasts on matched events.** The iteration-4 record compared the push forecast's mean over its 3 defined events with the association mean over 5. Table 171 sets every forecast on the same three event sets. On the 3 events where this run's push forecast is defined, it scores -0.76 against -3.11 for association; over all 5 gated events, with an undefined forecast scored as uniform, it scores -1.37 against -3.46. The review's -1.37 is this 5-event value, and it coincides at two decimals with a different cell, the screen push's route replication on its 4 defined events (-1.369).

**Table 171.** Mean log score of each forecast on matched event sets of the five gated iteration-3 bench bans, with top-1 hits. Source: record audit `tables/table157_matched.csv`.

{{T:matched}}

**Exposure arms as controls.** Table 172 gives the per-task verdict with exposure arms counted as controls, read from the plan noise experiment's knob rows (one engine) with the iteration-3 vetoes and the record's ban rows carried. Four task verdicts of Table 123 had rested on an exposure arm. Connected components keeps a qualifying knob (plan noise at alpha 2, 2.10 at no cost); longest increasing subsequence, nonoverlapping intervals and first and last position join the tasks on which no non-exposure knob reaches 1.5 within 20 pass points.

**Table 172.** Best non-exposure knob per task. Source: record audit `tables/table123_exposure.csv` (knob rows of the plan noise experiment).

{{T:exposure}}

**Executed results the record had omitted.** Plan noise on the plain prompt, without the prohibition frame of the twin, ran on the same slots and directions as plan noise under the twin frame (Table 173). The frame is not needed on kth smallest, connected components and the shortest path task, and on connected components the plain prompt moved more programs (0.24 against 0.12). The dose units of the experiments differ (Table 174): the ban-free unit is 0.30 to 0.97 of the ban unit across tasks, and substring search, the task that never moves, has by far the largest ban unit. A check made after the rivals were frozen found that the pooled escape fraction does not track the ratio of ban unit to residual norm (Spearman -0.06, AUC 0.49), so movability is not an artefact of the dose unit on the screen tasks.

**Table 173.** Plan noise at alpha 1 on the plain prompt and under the twin frame, same slots and directions. Source: record audit `tables/pnplain.csv`.

{{T:pnplain}}

**Table 174.** Dose units per task: the ban unit (mean norm of the ban displacement), the ratio of the ban-free unit to it, and both relative to the residual norm. Source: record audit `tables/dose_units.csv`.

{{T:dose}}

**Distributions, not best cells.** Table 175 summarises the 624 per-direction cells of the escape screens as quantiles, so that a best cell can be read beside the direction it came from. On kth smallest at alpha 1 the median direction moves 3% of programs off the default and the maximum moves all of them; on two sum 0 of 40 directions escape at alpha 1 and 5 of 40 at alpha 2, with a median of 0. Table 176 gives the template split-half reliability of the direction ranking on all six tasks; the grid task (0.39 with 22 movers) and find duplicate (0.59 with 3 movers) were missing from the record. Table 177 gives signed progress toward the runner-up per task: 22 of the 24 realised-progress cells with uncorrected p below 0.05 on connected components, but 1 on kth smallest, whose mean over the edited blocks is -0.02, and 0 on find duplicate, whose mean is -0.12. On connected components the committed signed component (0.33) was matched by the within-class control (0.37). Signed progress is closed. Table 178 gives the number of correct programs behind each cell of Table 147: the alpha-4 peaks on two sum, find duplicate and connected components rest on 9, 5 and 7 programs.

**Table 175.** Per-direction escape screens as distributions: directions run, escaping, movers, and quantiles over directions of the off-default share and of correct-only Hill-1. Source: record audit `tables/direction_quantiles.csv` (per-direction rows in `tables/direction_distributions.csv`).

{{T:dirq}}

**Table 176.** Template split-half reliability of the ranking of 40 fresh directions by off-default share, on all six tasks. Source: record audit `tables/split_half.csv`.

{{T:splithalf}}

**Table 177.** Signed progress toward the runner-up per task, over 24 block cells (blocks 12 to 35). Source: record audit `tables/signed_progress.csv`.

{{T:signed}}

**Table 178.** Correct programs behind each cell of Table 147 and the depth at which Hill-1 was rarefied. Source: record audit `tables/table147_depths.csv`.

{{T:depths}}

**Rival task predictors, frozen before any target was read.** For the movability half to mean anything, beta had to beat simpler explanations of why a task moves. The audit computed eight ban-free predictors for the 15 existing tasks and catalogue size as a covariate, wrote them to a canonical file, and froze them by sha256 in a hash chain before opening any outcome file (frozen at 11:59:44 UTC, first scored at 11:59:50; two later re-freezes left the values identical). The predictors are the twin's opening margin (the teacher-forced log-probability margin of the default's opening over the runner-up's), the forced 'can' rate, association clarity, the off-default excess under the novelty instruction, the diversity of human solutions (Mercury solutions labelled by the frozen rules with a judge on unknowns; audit agreement 0.97, kappa 0.97, 121 programs), the runtime merit gap of the runner-up's reference against the default's (76 references timed on their hidden tests), the twin modal share and the ratio of ban unit to residual norm. Five of them (the opening margin, the novelty excess, the merit gap, the twin modal share and catalogue size) can be computed on new tasks and were frozen for the confirmation panels. Scored against the pooled escape fraction of the screen, none is informative after Holm correction (every adjusted p is 1.0), and 10 of the 15 tasks are tied at an escape fraction of 0 (Tables 179 to 181). These scores are descriptive: the escape fractions generated the hypothesis, so the freeze protects only the confirmation on new tasks.

**Table 179.** The frozen rival predictors per task, with the screen's escape fraction and plan-noise excess. Source: record audit `tables/rivals_values.csv`.

{{T:rivals_values}}

**Table 180.** The rival predictors scored against the screen's pooled escape fraction (descriptive; the predicted sign is the direction the rival should take if it explains movability). Source: record audit `results/rival_scores.json`, `tables/rivals_scores.csv`.

{{T:rivals_scores}}

**Table 181.** Spearman correlations among the rival predictors over the 15 existing tasks. Source: record audit `tables/rivals_intercorr.csv`.

{{T:rivals_ic}}

Catalogue size, the number of algorithms a task's catalogue admits, tracks the screen's movability as well as any rival (+0.46), which is a reminder that a task with more alternatives has more ways to move.
