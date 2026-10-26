## 5.3 Transplanting the base model's plan states into the instruct model (Qwen3-8B)

**Why.** If post-training narrowed the choice at the plan site, the narrowing should be undone by giving the instruct model the base model's own task-specification states. No earlier iteration had tried this: iteration 1 subtracted an instruct-minus-base direction estimated at the read position only, which destroyed the output format (Section 1.9). This experiment [ARTIFACT:art_CcZLW-9NX00l] was the first causal test of the transplant claim, and it also measured the base repertoire that every other Qwen3-8B analysis of the iteration needed.

**Design.** Qwen3-8B and Qwen3-8B-Base (revision 49e3418f, the base revision of iteration 1) ran in bf16 on one RTX 4090 with thinking off, temperature 1.0, top-p 1 and no top-k. The base model sampled 100 programs per task under the instruct chat template on identical token ids (200 on the two path tasks, with top-ups to 200 on connected components, nonoverlapping intervals and cycle detection) and 100 in plain completion. Its labels used the iteration-4 labellers with a blind judge on disagreement, and a 15-program judge audit per task agreed at least 0.86 everywhere. The base repertoire (default, beta with a 95% interval, stratum, base runner-up) was committed by hash before any hooked sample. The transplant set the hooked states to h_instruct + lambda (h_base − h_instruct) at blocks 12 to 23 for lambda in {0.25, 0.5, 1}; the states were set, not added, so nothing compounded, and at lambda 1 the hooked blocks carried the base state exactly. The controls on the same common-random-number slots were a matched-norm random displacement (per block and position), a cross-task base shift (another task's mean base-minus-instruct direction at the same norm), and, where the random control broke the model, a pass-matched random push. Site controls transplanted at the read position, at blocks 0 to 11 and at blocks 24 to 35. Lambda was selected on one set of slots and confirmed on fresh slots, both under commits made before the samples.

**The base model is more diverse than the instruct model on most tasks** (Table 182). Under the same prompt the instruct twin wrote its default in 96% to 100% of programs on all 15 tasks, while the base model was base-diverse on 5 (kth smallest, shortest path, connected components, grid and top-k frequent), intermediate on 7 and base-collapsed on 3 (merge intervals, nonoverlapping intervals and topological order). The base model under the chat template is a poor programmer: it wrote 14 to 55 correct programs per 100 to 200 samples, and on the grid task only 14 of 200, so the grid beta rests on attempts. On connected components it writes DFS more often than union find (32 against 19 correct programs), so the instruct default is the base model's second choice there.

**Table 182.** The base repertoire of the 15 existing tasks, committed before any transplant sample. Source: transplant experiment `results/base_repertoire.json`.

{{T:base_rep}}

As a screen check, the committed beta ranks the 15 tasks almost exactly as iteration 4's random pushes could move them: Spearman 0.78 against the escape fraction at alpha 1 (one-sided permutation p 0.0002), 0.79 at alpha 2 and 0.79 on their mean, and the base runner-up equals the push's top-1 landing on 5 of 5 movable tasks. This is the observation the hypothesis was built on, measured again; it is not a test, because these tasks generated the hypothesis.

**Selection and confirmation.** Table 183 gives every arm of the selection stage. The transplant moved two tasks at an intact pass rate on the selection slots, top-k frequent at lambda 1 (0.47 of correct programs off the default, pass 0.98) and connected components at lambda 0.5 (0.12), and it broke the shortest path and grid tasks at lambda of 0.5 or more (pass 0.72 and 0.54, 0.50 and 0.30). On kth smallest the matched random displacement at lambda 1 moved more programs (0.34) than the transplant (0.06). Early-block transplants moved kth smallest (0.30) and connected components (0.28) more than the main band, the read-position transplant broke the output on 13 of 15 tasks without moving an algorithm, and late-block transplants were inert.

**Table 183.** Selection stage on the first slots: pass rate / correct off-default share per arm (N = 50 for the transplant, 30 for the controls; T is the transplant at lambda, MR the matched random displacement, READ, EARLY and LATE the site controls at lambda 1). Source: transplant experiment `results/selection.json`.

{{T:selection}}

On fresh slots (Table 184) only top-k frequent passed: the transplant wrote the base runner-up, a heap, in 21 of 49 correct programs against 0 of 39 for the twin, beat all three controls at Holm-adjusted p of 7e-4 or less, and was ahead on 5 of 5 templates. On kth smallest the matched random displacement beat the transplant (2 transplant-only against 20 random-only flips; two-sided p 1.2e-4): the base direction disturbs the plan less than an isotropic one of the same size. On connected components the transplant led both controls 3:0, short of significance, and on the shortest path and grid tasks the lambda that survives (0.25) moved nothing. The frozen rule needs a pass on at least 4 of the 5 base-diverse tasks, so the transplant claim is DISCONFIRMED; the stable-stratum and noise-robust sensitivities agree. An outcome-blind extension to N = 100 on the decisive cells (Table 185) kept top-k frequent (44:0, 35:3 and 49:0 against the three controls) and added only raw significance against the cross-task control on kth smallest (6:0, p 0.016, Holm 0.11) and connected components (7:0, p 0.0078, Holm 0.06); neither task beat the matched random control. Its verdict reads PARTIAL for a mechanical reason: at N = 100 the grid transplant's pass rate (0.68) fell below 0.8 times the twin's, which removes the precondition for DISCONFIRMED.

**Table 184.** Confirmation on fresh slots (S2; N = 50 per cell; lambda* is the selected lambda; one-sided exact McNemar on correct off-default programs, transplant only : control only, with Holm-adjusted p; rows marked desc. are descriptive tasks outside the decisive set). Source: transplant experiment `results/confirmation.json`.

{{T:confirmation}}

**Table 185.** Outcome-blind extension to N = 100 on the decisive cells. Source: transplant experiment `results/confirmation.json#power_extension_N100`.

{{T:power_ext}}

Top-k frequent is the one task on which the base state works and random noise does not: it is base-diverse (beta 0.35) and iteration 4's random pushes never moved it. Its transplant also raised the pass rate from 0.78 to 0.98, so part of what the transplant restores may be a more correct program rather than a reopened choice; the experiment did not separate the two. Base-collapsed tasks did not move under the full transplant (change 0.00). The read-position transplant shifted the off-default share by more than 0.05 on connected components and longest increasing subsequence, but only among the few programs that still passed (5 and 16 correct of 30) and never significantly, so the point-estimate specificity check fails while its noise-robust version holds.

**The de-sharpening push and the reverse transplant.** A push along the unit base-minus-instruct direction never escaped the default on any of the four tasks at doses of 0.5 to 2 ban-free units, while an isotropic push at the same doses escaped on kth smallest at alpha 2 (Table 186). The de-sharpening claim is DISCONFIRMED. The reverse interchange wrote the instruct model's task-specification states into the base model (Table 187). It raised the base model's correct program counts on all four tasks (kth smallest 20 to 31, shortest path 15 to 20, grid 5 to 11, connected components 18 to 19) and its default share among attempts, while a matched random displacement lowered the counts; the committed prediction (the default share among correct programs rises by at least half the instruct-minus-base gap) was met only on the grid task (0.80 to 1.00; one-sided p 0.033). Control is asymmetric: instruct states pull the base model toward the instruct default and toward correct code, but base states do not pull the instruct model back.

**Table 186.** De-sharpening push along unit(D) against an isotropic push at the same dose (ban-free units, N = 30; pass, correct off-default share). Source: transplant experiment `results/desharpen.json`.

{{T:claimD}}

**Table 187.** Reverse interchange: instruct task-specification states into the base model (blocks 12 to 23, N = 50). Source: transplant experiment `results/reverse.json`.

{{T:reverse}}

**What the base-minus-instruct difference is.** D = h_base − h_instruct is mostly shared across tasks and templates: the per-task mean D has cross-task cosine 0.76 to 0.88 at blocks 12 to 27 and split-half cosine 0.96 to 1.00 between template halves. It is large: at lambda 1, 71% of the hooked cells exceed 4 ban-free units, the dose at which random noise broke programs in iteration 4, and at the read position the difference is as large as the residual itself (Table 188). The transplanted state does not survive downstream: at block 27 the task-specification state stays 88% to 89% of the way to the base twin, but the read-position state moves only 18% to 31% of the way (Table 189), so blocks 24 and later pull the computation back toward the instruct model.

**Table 188.** Size of D relative to the residual norm, mean over tasks, per block. Source: transplant experiment `results/d_norms.json`.

{{T:dsize}}

**Table 189.** Geometry of the transplanted state: distance of the centroid under the transplant at the selected lambda as a fraction of the instruct-to-base twin gap, with MDS stress-1. Source: transplant experiment `results/geometry.json`.

{{T:geometry}}

**Checks.** Every bench labeller recovered all its references; the base extraction agreed with iteration-1 labels on 0.95 of 40 programs; the hash chain had no break, and every hooked row followed the commit of the base repertoire. Two independent re-derivations matched 56 of 56 and 34 of 34 checks, and the placebos failed as required (arm shuffle within slots rejects at 0.012). The engine check against the 8-bit rows of iteration 4 (Table 190) agrees slot by slot on the twins and within the resampling null on the pushed cells, except the shortest path twin, which is outside a null of zero width. The novelty audit read every one of 48 correct programs outside the catalogue, base output included: the judges called 14 of them novel, and the manual comparison with the nearest known solution found linear scans, count loops and a threshold binary search, known techniques outside the frozen catalogue; 0 novel (rule-of-three bound 0.062). Ten deviations are logged, among them base sampling and the engine check before the protocol commit (both still before every transplant sample) and the conservative 'unknown' label of the array-scan Dijkstra probe.

**Table 190.** Engine check of the bf16 engine against the 8-bit rows of iteration 4. Source: transplant experiment `results/engine_check.json`.

{{T:ec24}}

## 5.4 Panel A: does the base repertoire predict which new tasks move? (Qwen3-8B)

**Why.** The screen correlation of 0.78 was measured on the tasks that generated the hypothesis. The movability and landing halves could only be confirmed on tasks never seen, with every forecast committed from base samples before the first push. Panel A [ARTIFACT:art_8WbrpoEFslk9] built one half of those tasks.

**Design.** Nine new units derived from LeetCode problems [12] were frozen up front in new wording (a grep audit found no algorithm word or catalogue name), each with hidden tests from the dataset's input-output pairs plus seeded edge, random and stress cases, one reference per algorithm, mutants that must fail, quadratic baselines and runtime and AST labellers. A labeller passed its gate at runtime-against-AST kappa of at least 0.8, runtime-against-adjudicated agreement of at least 0.9 and 100% of references, with one revision round on a holdout. Six of the seven planned units passed; number of islands failed after its revision (holdout kappa 0.74), and the two reserves, jump game and median of two sorted lists, ran as a logged extension. Per unit, the instruct twin drew 50 programs and the base model 100 on identical ids plus 50 in plain completion, the rivals were computed, and the forecast (default, beta with its interval, base runner-up, rivals) was committed by hash; a guard in the GPU worker refused push jobs until then. Only then did 8 isotropic directions at alpha 1 and 2 (N = 10, confirmed at N = 30 by an exact binomial test), plan noise at alpha 1 and 2 (N = 50) and temperature 1.3 (N = 50) run. The 15 existing tasks were re-measured in the same engine on the ban-free unit; we call this the re-measurement arm.

**The movability half is not supported in panel A** (Table 191). Over the six preregistered units, Spearman between beta and the escape fraction is -0.03 (exact one-sided p 0.56; Kendall 0). The one base-collapsed unit, maximum block sum (beta 0), is immovable, as the movability half predicts, but 2 of the 5 base-diverse units are also immovable, among them the most diverse: count primes (beta 0.81) never escapes. A measurement-error bootstrap gives a median of -0.09 (90% interval -0.37 to 0.21). With the two extension units, both base-diverse (0.47 and 0.71) and both immovable, Spearman falls to -0.33 (p 0.80). Simple rivals tracked movability better than beta (Tables 192 and 193), and so did beta's own variants: Spearman with the escape fraction is -0.09 for beta from plain completion, -0.03 for beta that also counts correct programs labelled other as off-default (identical to beta on these units) and 0.40 for the base Hill-1 (0.16, -0.33 and 0.22 with the extension units). The three units that moved have an alternative at least twice as fast as the default (minimum runtime merit ratio 0.10 to 0.51), the three that did not have ratios of 0.86 to 4.35, and the runtime merit rival reaches -0.88; the extension unit median of two sorted lists breaks this (ratio 0.11, never escapes), and with it the rival falls to -0.66. The twin's own modal share reaches -0.70, ahead of beta by a task-bootstrap interval that excludes zero (-1.90 to -0.09).

**Table 191.** Panel A units: gate, the forecast committed before any push, and the outcome. Source: panel A `results/summary.md`.

{{T:A_units}}

**Table 192.** Rivals against beta, primary units (Spearman with the escape fraction, and the difference from beta with a 95% task-bootstrap interval). Source: panel A `results/a1.json`.

{{T:A_rivals_primary}}

**Table 193.** The same with the two extension units. Source: panel A `results/a1_with_extension.json`.

{{T:A_rivals_ext}}

**The landing half is supported in panel A.** On all three movable units (majority element, trapped rain water, longest mirrored substring) the base runner-up is the push landing (Poisson-binomial p 0.019 under chance 1/(K − 1)), and the base composition scores best (Table 194). The committed association forecast was uniform because of a mapping bug: every association answer restates the default named in the question, and the committed mapping took the earliest catalogue mention. With the mapping corrected post hoc on the same pre-commitment answers (Table 195), association names the landing on 2 of 3 events and is a strong rival, but the base composition still scores higher on all three (mean margin 0.85 nats; 1.10 against the committed uniform version). Exact Wilcoxon p is 0.25, the smallest attainable with three events. No correct plan-noise or escape program landed on an algorithm with zero correct and zero valid base programs (Table 198).

**Table 194.** Panel A landing events: base runner-up, landing and log scores with the committed association forecast. Source: panel A `results/a2.json`.

{{T:A_a2}}

**Table 195.** The association rival with the corrected mapping (post hoc, deviation D-assoc-mapping). Source: panel A `results/assoc_corrected.json`.

{{T:A_assoc_corr}}

**The existing tasks on the ban-free unit.** The re-measurement arm re-measured the 15 existing tasks with 8 fixed directions at alpha 1 and 2 on the ban-free unit in bf16 (Table 196). Only kth smallest (escape fraction 0.25) and connected components (0.125) escaped; two sum, find duplicate, the grid task and the shortest path task, which the frozen screen called movable under the 8-bit engine and the ban unit, did not move. A descriptive view that combines the six new units with the 15 existing tasks (Step 1's committed beta, this arm's escape fractions) gives Spearman 0.54 (p 0.0065), and 0.59 (p 0.0096) for the existing tasks alone, but that correlation comes from 13 of 15 existing tasks being immovable with low beta, while base-diverse tasks (the grid, shortest path and top-k frequent tasks) are still immovable, and the landing check splits (connected components hit, kth smallest miss: Step 1 runner-up quickselect, landing size-k heap).

**Table 196.** The re-measurement arm: the 15 existing tasks under the ban-free unit (8 directions, alpha 1 and 2), against iteration 4 and the frozen screen. Source: panel A `results/extra_arm_a.json`.

{{T:A_extra}}

**Table 197.** Knob rows of the panel A units: pass rate / off-default share / correct-only Hill-1 at depth 25. Source: panel A `results/knob_rows.json`.

{{T:A_knobs}}

**Table 198.** Repertoire check: does any nudge reach beyond the base repertoire? Source: panel A `results/repertoire_check.json`.

{{T:A_repertoire}}

**Checks.** The labellers recovered every reference and 35 of 35 hand-written variants; independent TheAlgorithms implementations passed 8 of 9 frozen test suites and received the intended runtime label on 7 of 9 (Table 199), the misses being an unloadable file and a Misra-Gries vote that counts candidates in a Counter. The twins reproduced the 8-bit screen rows, while the pushed cells differed under bf16 (Table 200), so every contrast of the panel is within the bf16 engine. Two correct programs labelled other appeared among 6,854 correct programs (one catalogue variant, one degenerate); 0 novel (rule-of-three bound 0.00044 per correct program). Two standard-library re-derivations matched with no mismatch, and the placebos failed (beta shuffled across units: mean Spearman 0.00; labels shuffled between twin and escape rows: escape fraction at most 0.007 on average). Eleven deviations are logged, including a re-run of the majority element test builder after its commit (identical cases, changed timing fields) and the association mapping bug.

**Table 199.** External cross-check with independent TheAlgorithms implementations (MIT). Source: panel A `results/external_reference_check.json`.

{{T:A_ext_ref}}

**Table 200.** Engine check of panel A's bf16 engine against the 8-bit screen rows. Source: panel A `results/engine_check.json`.

{{T:A_ec}}

## 5.5 Panel B: seven more new tasks and disguised variants (Qwen3-8B)

**Why.** Panel B [ARTIFACT:art_9a8LrIv2lHbV] built the other half of the confirmation units under the same protocol, and added narrative-disguised variants of eight bench tasks, each with a paired parent re-measure, to separate a task's wording from its algorithmic affordances.

**Design.** Seven units (missing number, single number, minimum spanning tree weight, integer square root, all subsets, valid anagram and count inversions) were built with wording free of algorithm words, hidden tests checked by two independent oracles, three to six references, mutants and excluded brute-force methods, and gated labellers; all seven gated, four after one revision round, and the 15-program blind audits of base labels agreed at 0.93 to 1.0. Because the base model was 46% to 61% off task under the chat template, its repertoire was raised to N = 200 per unit before any commit. Each unit's beta, base runner-up, base composition and rivals were hash-chained before its first push; then came 8 directions at alpha 1 and 2, plan noise and temperature 1.3.

**The movability half is not supported in panel B either** (Table 201). Spearman between beta and the escape fraction is 0.21 (exact one-sided p 0.33, unit-bootstrap interval -0.75 to 0.95). Four units moved (single number, count inversions, minimum spanning tree weight and integer square root) and three did not: missing number (beta 0.06), all subsets (0.37) and valid anagram (0.81), the clearest disconfirming case. No unit was base-collapsed, so the part of the movability half that says collapsed tasks are immovable is untested here. Beta ranks the graded plan-noise excess better (0.82, p 0.017), and the runtime and length merit rivals track the escape fraction more closely than beta (0.54 and 0.58; Table 202), all with wide intervals. Under the preregistered sensitivities, beta from attempts gives 0.39 (p 0.18), beta from plain completion -0.45, beta from correct programs 0.04, and excluding the uncertain class or the flagged twins gives -0.03 and 0.06; a placebo with beta shuffled 1,000 times has a mean Spearman of 0.008 and rejects at 0.048.

**Table 201.** Panel B units: default, beta under three bases, base runner-up and the escape outcome. Source: panel B `README.md`, `results/a1_panel.json`.

{{T:B_units}}

**Table 202.** Rivals against beta in panel B. Source: panel B `results/rivals.json`.

{{T:B_rivals}}

**The landing half in panel B.** The base runner-up named the push landing in 3 of 4 events (expected by chance 1.2; Poisson-binomial p 0.081), and the base composition beat association by 0.68 nats and proximity by 0.13 nats on average (Table 203). The miss is integer square root, where the base runner-up is a floating-point square root and the pushes land on a linear scan. With fewer than five events no Wilcoxon test was run.

**Table 203.** Panel B landing events. Source: panel B `results/a2_panel.json`.

{{T:B_a2}}

**Disguised variants.** Of the eight parent and variant pairs, only kth smallest and connected components moved in either form (Table 204), and connected components changed its default under disguise (union find to BFS); the sign of the change in beta and the change in escape fraction agreed in 0 of 1 pair without a default shift, and their Spearman over pairs was 0.13 (p 0.50). Descriptive views that add the re-measured parents (Spearman 0.43, p 0.055, n = 15) or the variants with a cluster-preserving permutation (0.54, p 0.015, n = 22) are positive, as is the screen view (0.79 on the 15 screen tasks), but none is the preregistered test.

**Table 204.** Within-parent comparison of disguised variants (P parent re-measure, V variant; McNemar counts on confirmed escape cells). Source: panel B `results/variants.json`.

{{T:B_parents}}

**Checks.** The engine check reproduced kth smallest within the template-resampling null (per-slot agreement 0.74) and put the shortest path cell outside it (0.64), a precision sensitivity; the twins agreed at 1.00 and 0.98. Twelve distinct correct programs labelled other appeared among 10,366 correct programs (7 catalogue variants, 5 degenerate); 0 novel. Independent re-derivations found no mismatch, the twin-as-push placebo gave an escape fraction of 0 on every unit, and no push row preceded its unit's commit. Count inversions carries three flags: its default comes from 3 correct twin programs, the twin passes only 0.06 (47 of 50 twin programs are the quadratic pair scan, which exceeds the time limit), and its base composition uses attempts (15 correct programs).

## 5.6 The two panels pooled (computed for this report)

Neither panel ran the pooled test: both wrote their raw per-unit ingredients for a pooled step in the next round. Because the pooled numbers decide how this iteration is read, we computed them here from the two panels' own result files (`work/pooled_a1a2.py`, output `work/pooled_a1a2.json`), with a Monte Carlo permutation test for Spearman and an exact Poisson-binomial tail and exact Wilcoxon signed-rank tests [65] for the landing half. This is a descriptive preview; the preregistered parent-cluster permutation was not run.

**Table 205.** The movability and landing halves over the new units of both panels (13 preregistered units; 15 with panel A's extension). Source: `work/pooled_a1a2.json`, computed from panel A `results/a1*.json`, `results/a2*.json` and panel B `results/a1_panel.json`, `results/a2_panel.json`.

| Quantity | Preregistered units (n = 13) | With the extension units (n = 15) |
|-|-|-|
| Spearman between beta and the escape fraction | 0.146 (one-sided permutation p 0.315) | 0.006 (p 0.492) |
| Base-collapsed units that are immovable | 1 of 1 | 1 of 1 |
| Base-diverse units (beta at least 0.2) that are immovable | 4 of 10 | 6 of 12 |
| Movable units | 7 of 13 | 7 of 15 |
| Landing events (movable units with beta at least 0.05) | 7: majority element, trapped rain water, longest mirrored substring, single number, minimum spanning tree weight, integer square root, count inversions | same |
| Base runner-up equals the push landing | 6 of 7 (expected by chance 2.03; Poisson-binomial p 0.0027) | same |
| Base minus association, corrected mapping (nats per event) | mean +0.75; differences +0.21, +0.09, +2.24, -0.07, -0.20, +2.18, +0.79; exact one-sided Wilcoxon p 0.055 | same |
| Base minus association, committed (uniform) mapping in panel A | mean +0.86; exact one-sided Wilcoxon p 0.039 | same |
| Base minus proximity | mean +0.50; differences +1.57, +1.07, +0.32, +0.78, +0.64, +0.46, -1.37; exact one-sided Wilcoxon p 0.109 | same |

Read against the preregistered thresholds, the movability half meets its disconfirming outcome on the pooled view (Spearman below 0.3), although not the second clause (4 of 10 base-diverse units are immovable, not most). The landing half meets its hit-rate criterion (6 of 7, 0.86, against a bar of 0.7 at p below 0.05) and its margin over association (0.75 nats against a bar of 0.10), with the paired Wilcoxon at p 0.055 against the corrected association and 0.039 against the committed one.

[FIGURE:fig_beta_escape]
