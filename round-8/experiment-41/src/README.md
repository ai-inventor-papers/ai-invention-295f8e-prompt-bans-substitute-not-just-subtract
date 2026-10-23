# The circuit behind Qwen3-8B's algorithm choice (K3)

Which components of bf16 **Qwen3-8B** (rev b968826d, thinking off) compute the odds of the token that decides which
algorithm gets written, and does steering them change the algorithm in generated, hidden-test-checked programs?
Two decision tokens are studied:

* **C1 (primary): minimum spanning tree weight (unit B3)** - after B3's 61-token canonical opening
  (`...graph[v].append((u, w))\n\n    #`), the next token is ` Kr` (Kruskal) or ` Prim`. Metric
  m = z(' Kr') - z(' Prim') at the decision position (DEC).
* **C2a (replication): connected components (T10)** - after `def solve(n, edges):\n    def`, the next token is
  ` find` (union find) or ` dfs`. m = z(' find') - z(' dfs').

The pipeline is ported from iteration 7's Gemma-3-4B G1 code so both families are measured identically:
attribution-patching screen of 4,752 nodes (36 x 32 heads + 36 MLPs at four position classes COND / SPEC / OPEN /
DEC) -> exact noising and denoising of the top nodes -> path patching among the top 15 -> faithfulness curves ->
validation of each top-10 node in the real model against **50 matched random components** (same type and position
class, matched write norm) under ABLATE and STEER, exact sign-flip tests with Holm -> top-5 steering in
**generation** (N = 30 common-random-number slots, hidden tests, exact McNemar against a matched random five and the
unedited twin) -> a committed **motif test** against Gemma.

**Why it matters for the run's question** (can an LLM be pushed to a different solution, and how is the choice made
inside it?): the choice between two algorithms is made at one token, and the circuit analysis below locates the
components that compute it. A condition-span MLP at layer 0 injects the instruction. A small stack of late
decision-position heads and MLPs (layers 23-35) turns it into the decision logit. Steering five of those
components at one position rewrites which algorithm the model then implements.

## Bottom line

* **Node level (pre-registered): supported.** 9/10 (B3) and 8/10 (T10) of the top components beat 50 norm-matched random components of the same type and position in both ablation and steering (Holm over 20 tests). The failures are components whose effect runs against the decision ("brakes").
* **Generation (pre-registered): partially supported.** Steering the top five components at the decision position rewrites the written algorithm. B3: 29/30 correct Prim programs vs 8/30 for the unedited twin. T10: 29/30 correct DFS vs 1/30. Pass rates are unchanged. At the committed dose 2, however, the matched random five also flips most programs (B3 23/30, T10 30/30), so the pre-registered TOP5-vs-RAND5 McNemar fails and both K3 verdicts are **PARTIAL**.
* **Post hoc (labelled): the circuit is far more efficient than random late components for T10, but only modestly for B3.** At dose 0.5, T10's top five give 30/30 DFS vs 6/30 for the random five (McNemar p = 1.2e-07). For B3 the counts are 25 vs 20 (p = 0.12).
* **Mechanism.** In both families, a layer-0 MLP at the instruction span carries most of the injected contrast (AtP missed it in Qwen; only the exhaustive sweep found it). A late stack of decision-position MLPs and heads turns it into the decision logit; in Qwen it sits deeper than in Gemma (normalised depth ~0.86 vs 0.69). The two algorithm decisions (Kruskal/Prim and union-find/DFS) share components: MLPs L26-L30 and heads L23 H10 and L27 H31 at the decision position.

## K3 verdicts

| unit | verdict (two-sided McNemar, primary) | verdict with one-sided McNemar | nodes passing both tests | generation criteria met (PREFILL) | McNemar TOP5 vs RAND5, two-sided / one-sided p |
|---|---|---|---|---|---|
| C1 = C1-forced (primary) | **PARTIAL** | PASS | 9 / 10 | False | 0.0703 / 0.0352 |
| C2a (replication) | **PARTIAL** | PARTIAL | 8 / 10 | False | 1.0000 / 1.0000 |

The McNemar sidedness was not written into commit #0's text. The analysis code fixed by hash at commit #0 used the
one-sided test, while the plan's power calibration (8:0 -> p = 0.0078; 7:1 -> p = 0.07) is two-sided. The two-sided
test is taken as primary because it is the more conservative of the two; both are reported.

Rule (committed in commit #0): PASS = at least 5 of the top 10 nodes pass both tests (Holm over all 20 node x test
p-values) AND the PREFILL top-5 arm adds >= 6 correct minority-algorithm programs of 30 over the twin, beats the
matched random five (exact McNemar p < 0.05) and keeps pass rate >= 0.8 x the twin's; PARTIAL = exactly one of the
two; DISCONFIRMED = no top-10 node passes either test. **C1 is C1-forced**, not C1-nat: the natural noun-variant
pairs had a mean total effect of 0.89 nats (< 1 nat), which triggered the
pre-registered fallback F2 (amendment 0a, committed before any screen row). C1-nat is screened and reported
descriptively.

## Committed predictions (commit #0)

| id | prediction | observed | outcome |
|---|---|---|---|
| P1 | >= 5 of 10 nodes pass both tests on C1 (C1-forced after F2) | 9/10 (C1-forced); C1-nat (descriptive) 5/10 | met |
| P2 | PREFILL top-5: TWIN + >= 6 correct Prim, beats RAND5 (McNemar p < 0.05), pass >= 0.8 x twin | +21; McNemar two-sided p = 0.0703 (one-sided 0.0352); pass ratio 1.00 | not met (two-sided); met one-sided |
| P3 | the same on C2a toward DFS | +28; McNemar two-sided p = 1; pass ratio 1.00 | not met (RAND5 also saturates) |
| P4 | motif: DEC share [0.38, 0.68], COND share [0.21, 0.51], DEC-stack depth [0.45, 0.80] | Qwen C1mix: DEC 0.63, COND 0.01, depth 0.86 | not met (COND_share_in_band, DEC_stack_depth_in_band) |
| P5 | top-10 Jaccard between pair sets A and B >= 0.4 | 0.25 | not met |

## Contrasts and circuits

| contrast | pairs | mean total effect (nats) | AtP-vs-exact Spearman (160 random nodes / top set) | edges kept | completeness / sufficiency of top-10 |
|---|---|---|---|---|---|
| C1forced | 10 | 9.91 | 0.29 / 0.89 | 12 | 0.90 / 1.01 |
| C2a | 15 | 19.33 | 0.25 / 0.91 | 17 | 0.94 / 0.96 |
| C1nat | 15 | 0.89 | 0.11 / 0.66 | 20 | 1.05 / 1.02 |
| C1mix | 15 | 4.00 | n/a / 0.79 | 0 | n/a / n/a |
| C1natB | 12 | 0.46 | n/a / 0.51 | 33 | 0.82 / 0.99 |

* **C1-forced**: 10 forced-Prim paraphrases ("Implement Prim's algorithm ...", corrupt) vs their ' .' padding
  twins (clean); identical length and token ids from 'Task:' on; 5 more paraphrase pairs are the 10 held-out
  validation prompts.
* **C2a**: 15 T10 twin noun variants (clean) vs the same prompts with the forced-DFS prompt's residual states
  exchanged in at the task-spec positions of all 36 blocks (corrupt). The exchange flips the teacher-forced argmax to
  ' dfs' in every pair. It is an intervention, so COND nodes have zero effect by construction (a SPEC-to-decision
  routing map).
* **C1-nat**: 24 neutral-noun variants per template W1-W5 (nouns from the art_j3Rm_lr2nzR6 concreteness norms,
  single Qwen3 tokens), k-th highest vs k-th lowest m within template. SD of m over the 120 variants:
  0.34 nats (Gemma's y_v SD: 0.67). The layer-0 MLP at the noun position alone carries the
  whole total effect (the injection confound the plan flagged).
* Top-10 C1-forced: mlp|L0|H-1|COND, head|L33|H14|DEC, mlp|L35|H-1|DEC, head|L34|H28|DEC, mlp|L27|H-1|DEC, head|L29|H6|DEC, mlp|L30|H-1|DEC, head|L23|H10|OPEN, mlp|L28|H-1|DEC, mlp|L11|H-1|SPEC
* Top-10 C2a: mlp|L27|H-1|DEC, mlp|L26|H-1|DEC, mlp|L32|H-1|DEC, mlp|L30|H-1|DEC, head|L23|H10|DEC, head|L27|H31|DEC, mlp|L28|H-1|DEC, mlp|L31|H-1|DEC, mlp|L13|H-1|SPEC, head|L11|H13|SPEC
* AtP (first order) ranks the strong nodes well (Spearman on the exact-patched top set above) but not the near-zero
  random nodes, whose exact effects sit at the bf16 noise floor (~0.06 nats); the IG-AtP fallback (F4) did not
  improve the random-node correlation and plain AtP was kept, with 120 exact-patched nodes instead of 60.
* Faithfulness: jointly noising (completeness) or restoring (sufficiency) the top-k nodes with the rest of the
  network live recovers most of the effect; freezing every non-circuit node to its corrupt value (type 1) leaves
  ~0 of the effect at every k up to 60 (see `figures/faithfulness.png`): the decision-position nodes need the
  upstream instruction processing, which is spread over many small nodes.

## Validation in the real model (matched random components)

**C1forced** (30 prompts, 10 held out): 9 of 10 nodes pass both tests (Holm over 20); ablate 9/10, steer 9/10; Gemma's within-test Holm: both 9.

| node | ablate mean d | ablate p (Holm 20) | steer mean d | steer p (Holm 20) | both |
|---|---|---|---|---|---|
| mlp|L0|H-1|COND | 5.429 | 3.8e-06 | 4.938 | 3.8e-06 | yes |
| head|L33|H14|DEC | 2.050 | 1.9e-08 | 4.251 | 1.9e-08 | yes |
| mlp|L35|H-1|DEC | -2.638 | 1 | -5.068 | 1 | no |
| head|L34|H28|DEC | 1.964 | 1.9e-08 | 3.824 | 1.9e-08 | yes |
| mlp|L27|H-1|DEC | 0.777 | 1.9e-08 | 1.896 | 1.9e-08 | yes |
| head|L29|H6|DEC | 1.403 | 1.9e-08 | 2.827 | 1.9e-08 | yes |
| mlp|L30|H-1|DEC | 0.716 | 1.9e-08 | 1.529 | 1.9e-08 | yes |
| head|L23|H10|OPEN | 0.783 | 1.9e-08 | 1.531 | 1.9e-08 | yes |
| mlp|L28|H-1|DEC | 0.414 | 3.4e-07 | 0.904 | 1.9e-08 | yes |
| mlp|L11|H-1|SPEC | 1.162 | 1.9e-08 | 1.288 | 1.9e-08 | yes |

Joint sets: top-5 beats 1.00 (ablate) / 1.00 (steer) of 50 matched random five-sets; top-10 beats 1.00 / 1.00.

**C2a** (40 prompts, 10 held out): 8 of 10 nodes pass both tests (Holm over 20); ablate 8/10, steer 9/10; Gemma's within-test Holm: both 8.

| node | ablate mean d | ablate p (Holm 20) | steer mean d | steer p (Holm 20) | both |
|---|---|---|---|---|---|
| mlp|L27|H-1|DEC | 9.596 | 1.8e-11 | 16.058 | 1.8e-11 | yes |
| mlp|L26|H-1|DEC | 5.088 | 1.8e-11 | 10.606 | 1.8e-11 | yes |
| mlp|L32|H-1|DEC | 1.924 | 3.7e-10 | 7.967 | 1.8e-11 | yes |
| mlp|L30|H-1|DEC | 0.738 | 0.0015 | 5.851 | 1.8e-11 | yes |
| head|L23|H10|DEC | 3.627 | 1.8e-11 | 7.964 | 1.8e-11 | yes |
| head|L27|H31|DEC | 3.047 | 1.8e-11 | 6.869 | 1.8e-11 | yes |
| mlp|L28|H-1|DEC | 0.485 | 0.0077 | 1.685 | 3.4e-10 | yes |
| mlp|L31|H-1|DEC | -1.527 | 1 | 0.684 | 0.0079 | no |
| mlp|L13|H-1|SPEC | 1.712 | 2.4e-06 | 2.847 | 1.3e-07 | yes |
| head|L11|H13|SPEC | -1.802 | 1 | -3.351 | 1 | no |

Joint sets: top-5 beats 1.00 (ablate) / 1.00 (steer) of 50 matched random five-sets; top-10 beats 1.00 / 1.00.

**C1nat** (20 prompts, 5 held out): 5 of 10 nodes pass both tests (Holm over 20); ablate 5/10, steer 8/10; Gemma's within-test Holm: both 6.

| node | ablate mean d | ablate p (Holm 20) | steer mean d | steer p (Holm 20) | both |
|---|---|---|---|---|---|
| mlp|L0|H-1|COND | 0.478 | 1.9e-05 | 0.523 | 1.9e-05 | yes |
| mlp|L27|H-1|DEC | 0.194 | 1.9e-05 | 0.456 | 1.9e-05 | yes |
| mlp|L20|H-1|SPEC | 0.092 | 0.014 | 0.176 | 1.9e-05 | yes |
| mlp|L12|H-1|SPEC | 0.058 | 0.21 | 0.158 | 2.3e-05 | no |
| mlp|L30|H-1|DEC | 0.110 | 8.4e-05 | 0.240 | 1.9e-05 | yes |
| mlp|L8|H-1|SPEC | 0.088 | 0.05 | 0.168 | 0.00012 | no |
| mlp|L19|H-1|SPEC | 0.064 | 0.21 | 0.138 | 0.00039 | no |
| mlp|L5|H-1|COND | -0.015 | 0.73 | 0.037 | 0.48 | no |
| head|L34|H28|DEC | 0.178 | 1.9e-05 | 0.443 | 1.9e-05 | yes |
| mlp|L16|H-1|SPEC | 0.024 | 0.51 | 0.081 | 0.087 | no |

Joint sets: top-5 beats 1.00 (ablate) / 1.00 (steer) of 50 matched random five-sets; top-10 beats 0.96 / 1.00.

C1-nat validation is descriptive: C1-nat is not a K3 unit after F2, and the committed time rule cut it to the 15
clean prompts plus 5 held-out prompts because one prompt took 112 s (its top 10 are mostly SPEC/COND MLPs, whose rows
are full forwards).

**Post-hoc sensitivity (labelled; committed before its rows):** the top decision heads are write-norm outliers, so their matched pools fell back to the 50 nearest-norm heads (smaller norms; head draws are not rescaled in the committed design). Re-running those head nulls with each draw's delta rescaled to the target's write norm gives (uncorrected one-sided sign-flip p):

| contrast | node | ablate mean d | ablate p | steer mean d | steer p |
|---|---|---|---|---|---|
| C1forced | head|L29|H6|DEC | 1.371 | 9.3e-10 | 2.761 | 9.3e-10 |
| C1forced | head|L33|H14|DEC | 1.991 | 9.3e-10 | 4.133 | 9.3e-10 |
| C1forced | head|L34|H28|DEC | 1.864 | 9.3e-10 | 3.632 | 9.3e-10 |
| C2a | head|L27|H31|DEC | 3.044 | 9.1e-13 | 6.858 | 9.1e-13 |

Gemma's G1 under both multiplicity conventions (recomputed from its p-values): within-test Holm
{"ablate": 7, "steer": 8, "both": 7}; Holm over 20 {"ablate": 7, "steer": 8, "both": 7}.

## Generation (steering the written algorithm)

Arms: TWIN (unedited), TOP5 (STEER on the five generation nodes toward the minority class: own + 2 x (minority-class
mean - default-class mean)), RAND5 (one matched random component per node, same operation, MLP deltas rescaled to the
target's write norm). N = 30 = W1-W5 x 6 CRN slots, T 1, top-p 1, no top-k. PREFILL (primary) prefills prompt +
opening for every arm; FREE applies OPEN/DEC edits only while the sampled prefix equals the opening (exactly, by
teacher-forcing the edited opening and sampling with the slot's uniforms until the first divergence). Targets: B3
correct prim_heap / prim_array; T10 correct dfs.

**C1-forced (B3)**

| condition | arm | N | correct target | attempted target | pass rate | reached decision | labels |
|---|---|---|---|---|---|---|---|
| PREFILL | TWIN | 30 | 8 | 8 | 1.00 | 30 | {"prim_heap": 8, "kruskal": 21, "disputed": 1} |
| PREFILL | TOP5 | 30 | 29 | 29 | 1.00 | 30 | {"prim_heap": 29, "disputed": 1} |
| PREFILL | RAND5 | 30 | 23 | 24 | 0.97 | 30 | {"prim_heap": 24, "disputed": 1, "kruskal": 5} |
| FREE | TWIN | 30 | 7 | 7 | 0.97 | 14 | {"prim_heap": 7, "kruskal": 22, "disputed": 1} |
| FREE | TOP5 | 30 | 16 | 16 | 0.97 | 14 | {"prim_heap": 16, "kruskal": 14} |
| FREE | RAND5 | 30 | 12 | 12 | 0.97 | 14 | {"prim_heap": 12, "disputed": 1, "kruskal": 17} |

PREFILL: TOP5 - TWIN = +21 correct target programs (threshold +6: met); TOP5 vs RAND5 discordant 7:1, exact McNemar two-sided p = 0.0703 (primary; does not beat RAND5), one-sided p = 0.0352; pass ratio TOP5/TWIN = 1.00 (>= 0.8). All criteria (two-sided): NOT MET; with the one-sided test: MET.

FREE: TOP5 - TWIN = +9 correct target programs (threshold +6: met); TOP5 vs RAND5 discordant 4:0, exact McNemar two-sided p = 0.125 (primary; does not beat RAND5), one-sided p = 0.0625; pass ratio TOP5/TWIN = 1.00 (>= 0.8). All criteria (two-sided): NOT MET; with the one-sided test: NOT MET.

**C2a (T10)**

| condition | arm | N | correct target | attempted target | pass rate | reached decision | labels |
|---|---|---|---|---|---|---|---|
| PREFILL | TWIN | 30 | 1 | 1 | 1.00 | 30 | {"union_find": 29, "dfs": 1} |
| PREFILL | TOP5 | 30 | 29 | 29 | 1.00 | 30 | {"dfs": 29, "union_find": 1} |
| PREFILL | RAND5 | 30 | 30 | 30 | 1.00 | 30 | {"dfs": 30} |
| FREE | TWIN | 30 | 0 | 0 | 1.00 | 3 | {"union_find": 30} |
| FREE | TOP5 | 30 | 3 | 3 | 1.00 | 3 | {"union_find": 27, "dfs": 3} |
| FREE | RAND5 | 30 | 3 | 3 | 1.00 | 3 | {"union_find": 27, "dfs": 3} |

PREFILL: TOP5 - TWIN = +28 correct target programs (threshold +6: met); TOP5 vs RAND5 discordant 0:1, exact McNemar two-sided p = 1 (primary; does not beat RAND5), one-sided p = 1; pass ratio TOP5/TWIN = 1.00 (>= 0.8). All criteria (two-sided): NOT MET; with the one-sided test: NOT MET.

FREE: TOP5 - TWIN = +3 correct target programs (threshold +6: not met); TOP5 vs RAND5 discordant 0:0, exact McNemar two-sided p = 1 (primary; does not beat RAND5), one-sided p = 1; pass ratio TOP5/TWIN = 1.00 (>= 0.8). All criteria (two-sided): NOT MET; with the one-sided test: NOT MET.

**Post-hoc dose sensitivity (labelled; committed before its rows).** At the committed dose 2 the matched random five also saturates the minority algorithm, which leaves the TOP5-vs-RAND5 McNemar no room. Lower doses on the same 30 CRN slots (PREFILL):

| contrast | dose | TWIN | TOP5 | RAND5 | discordant TOP5:RAND5 | McNemar two-sided p | pass TOP5 / RAND5 |
|---|---|---|---|---|---|---|---|
| C1forced | 0.5 | 8 | 25 | 20 | 6:1 | 0.125 | 30 / 30 |
| C1forced | 1.0 | 8 | 27 | 28 | 1:2 | 1 | 30 / 30 |

C1forced logit level, mean P(minority decision token) over the five twins (twin 0.263): TOP5 dose 0.25: 0.542, dose 0.5: 0.785, dose 1.0: 0.962, dose 2.0: 0.997; RAND5 dose 0.25: 0.439, dose 0.5: 0.638, dose 1.0: 0.883, dose 2.0: 0.983

| contrast | dose | TWIN | TOP5 | RAND5 | discordant TOP5:RAND5 | McNemar two-sided p | pass TOP5 / RAND5 |
|---|---|---|---|---|---|---|---|
| C2a | 0.5 | 1 | 30 | 6 | 24:0 | 1.19e-07 | 30 / 30 |
| C2a | 1.0 | 1 | 30 | 18 | 12:0 | 0.000488 | 30 / 30 |

C2a logit level, mean P(minority decision token) over the five twins (twin 0.029): TOP5 dose 0.25: 0.978, dose 0.5: 1.000, dose 1.0: 1.000, dose 2.0: 1.000; RAND5 dose 0.25: 0.089, dose 0.5: 0.194, dose 1.0: 0.695, dose 2.0: 1.000

## Motif test (committed, descriptive)

The committed function (class share of |mean noising effect| over the exact list: top 40 by |AtP| + 20 random
calibration nodes) reproduces Gemma's printed shares from `g1_pathpatch.json` first: FORK/DEC
0.531, COND 0.357 (check
passed).

| shares | COND | SPEC | OPEN | DEC | DEC-stack depth |
|---|---|---|---|---|---|
| Gemma (15 pairs) | 0.36 | 0.06 | 0.05 | 0.53 | 0.69 |
| Qwen C1nat | 0.08 | 0.46 | 0.13 | 0.34 | 0.87 |
| Qwen C1forced | 0.01 | 0.20 | 0.18 | 0.62 | 0.86 |
| Qwen C1mix | 0.01 | 0.22 | 0.14 | 0.63 | 0.86 |
| Qwen C1natB | 0.14 | 0.48 | 0.10 | 0.28 | 0.93 |
| Qwen C2a | 0.00 | 0.32 | 0.01 | 0.67 | 0.79 |
| Qwen C1nat, exhaustive sweep (top 60 by exact effect) | 0.27 | 0.39 | 0.10 | 0.24 | 0.87 |
| Qwen C1forced, exhaustive sweep (top 60 by exact effect) | 0.17 | 0.18 | 0.17 | 0.48 | 0.86 |
| Qwen C1natB, exhaustive sweep (top 60 by exact effect) | 0.23 | 0.28 | 0.06 | 0.43 | 0.96 |
| Qwen C2a, exhaustive sweep (top 60 by exact effect) | 0.00 | 0.37 | 0.02 | 0.60 | 0.79 |
| Gemma, injection-excluded | 0.23 | 0.07 | 0.06 | 0.64 | |
| Qwen C1nat, injection-excluded | 0.04 | 0.47 | 0.13 | 0.35 | |
| Qwen C1forced, injection-excluded | 0.01 | 0.20 | 0.18 | 0.62 | |
| Qwen C1mix, injection-excluded | 0.01 | 0.22 | 0.14 | 0.63 | |
| Qwen C1natB, injection-excluded | 0.14 | 0.48 | 0.10 | 0.28 | |

The committed composition (top 40 by |AtP| + 20 random) depends on the AtP screen, which missed Qwen's largest
node, the layer-0 MLP at the condition span (AtP 0.1 vs exact 7.7 nats in C1-forced; Gemma's screen kept the
corresponding layer-0 COND MLP). The exhaustive sweep therefore matters as a sensitivity. With it, Qwen's COND share
rises to the value in the sweep row, and the condition-to-decision picture (an injecting layer-0 MLP at the condition
span plus a late decision stack) matches Gemma qualitatively. The late decision stack sits deeper in Qwen
(effect-weighted depth above the committed 0.80 band edge). The injection-excluded rows drop layer 0-1 nodes at the
corrupted span, which removes the share that the corruption injects by construction.

Committed bands: DEC share in [0.38, 0.68], COND share in [0.21, 0.51], DEC-stack effect-weighted depth in
[0.45, 0.80]. Primary comparison (C1mix vs Gemma): **DIFFERENT MOTIF**
(differs on: COND_share_in_band, DEC_stack_depth_in_band). Two models and two
decision tokens cannot establish a general motif; the comparison is descriptive. Injection-excluded shares (layer 0-1
nodes at the corrupted span removed) are in `results/summary.json`.

## Stability (pair set A vs disjoint set B, C1-nat)

Top-10 Jaccard 0.25, top-15 Jaccard 0.36, Spearman of exact effects over the union of both top-60 sets 0.55 (36 nodes measured in both); edges kept in both: 4. Prediction P5 (Jaccard >= 0.4): not met. Set B has a smaller total effect (0.46 vs 0.89 nats).

## Checks

* CPU tests (positions, node keys, motif on Gemma, sign-flip vs brute force, Holm/McNemar vs statsmodels/scipy,
  random-pool ladder, labeller re-check): all pass = True.
* Labeller re-check: B3 references 4/4, T10 references 4/4, T10 gold 22/22, 30 iteration-7 B3 twin programs 30/30.
* GPU tests: U1 pi(' Kr') on the W1 twin = 0.724 (iteration 7: 0.72); U6 steering
  hook exact; U2/U3/U8 differ from their 0.05-nat targets by bf16 path noise of the same size as full-vs-full
  differences across batch shapes (mean 0.061 nats), so suffix
  forwards were kept (amendment 0a); every reported effect is measured against an unedited base row of its own batch.
* Engine check (twin CRN slots): B3 label agreement with iteration 7
  1.00 (token-identical 11/20),
  T10 1.00.
* Novelty audit: 0 correct programs labelled 'other' among 395
  correct programs; no correct program was labelled 'other': no judge call; 95% upper bound on the novel-class rate among correct programs = 3 / n_correct
* Transcoder attribution-graph extension: DROPPED at the precheck (F11, expected) -
  the per-layer transcoders (~96.5 GB) exceed both the 23 GB L4 (which already holds the 16.4 GB bf16 model) and the 57 GB container RAM, and circuit-tracer is not installed; lazy per-layer loading from network storage would need ~96 GB of reads per attribution graph, far beyond the 45-minute timebox on this machine. Iteration 7's Gemma transcoder graph failed three times on a 16 GB GPU (inputs/exp38/results/g1t_graphs_attempt*.json). No feature-level account is given; the replacement-model extension is reported as not run.
* Pre-registration: hash chain commit0 -> amend0a -> commit1 -> commit_sens_C1forced -> commit_sens_C2a -> commit2 -> commit1b -> commit_dose_C1forced -> commit_dose_C2a
  (`commitments.log`, `predictions/*.json`); no validation row before commit #1, no steered program before commit #2.
* Stdlib re-derivation with placebos: `audit/rederive.py` -> `results/rederive.json`.

## Deviations

* **metric_fp32_readout** (major): First GPU-test pass (logs/superseded/gpu_tests.json) read m from the bf16 lm_head output, which is quantised to 0.125-0.25 nats at logit magnitudes ~20-30 (every m was a multiple of 0.25; U3 and U8 failed by exactly one or two quanta). From then on m is read in fp32 as h_final . (W_a - W_b) from the bf16 final-norm hidden state (the model's forward stays bf16). The C1-nat ranking/pairing and every contrast were recomputed before any screen row. Generation keeps the iteration-6 engine (bf16 lm_head logits) for CRN parity.
* **F5_prefix_cache** (major): U3 (suffix forward with reused prefix KV vs full recompute) differs by mean 0.076 / max 0.268 nats (> 0.05). The same 20 rows run as full forwards in two batch shapes differ by mean 0.061 / max 0.194: the gap is bf16 path noise, not a cache error, so suffix forwards were kept (amendment 0a rule) instead of F5's full forwards. U2 (patch everything -> corrupt) is off by 0.117 and U8 (own-state exchange) by 0.092 nats for the same reason; every effect is measured against an unedited base row of its own batch.
* **F4_C1forced** (minor): C1forced: AtP-vs-exact Spearman 0.29 < 0.6 -> IG-AtP (5 alphas, input interpolation) and 120 exact nodes; the S19 correction was not implemented within the 30-minute timebox
* **F4_C2a** (minor): C2a: AtP-vs-exact Spearman 0.25 < 0.6 -> IG-AtP (5 alphas, input interpolation) and 120 exact nodes; the S19 correction was not implemented within the 30-minute timebox
* **F4_C1nat** (minor): C1nat: AtP-vs-exact Spearman 0.11 < 0.6 -> IG-AtP (5 alphas, input interpolation) and 120 exact nodes; the S19 correction was not implemented within the 30-minute timebox
* **F2_C1forced_primary** (major): C1-nat set A mean TE 0.893 nats < 1.0 -> F2: C1-forced is the primary C1 unit (amendment 0a, committed before any screen row). art_MZAfDPVhM6Ui has one forced-Prim wording, so 15 wordings were written here: F1-F10 are the 10 pairs, F11-F15 (and their padding twins) the 10 held-out validation prompts. C1-nat is screened, validated and reported descriptively.
* **F4b_exhaustive_sweep** (major): AtP and IG-AtP both gave Spearman < 0.4 against exact patching on 160 random nodes (those nodes sit at the bf16 noise floor), so F4's second clause applied: ranking by exact noising over ALL DEC-class nodes plus the screen's top 120; all 144 MLP nodes were added because AtP is least reliable for early MLPs. This found C1-forced's largest node, the layer-0 MLP at the condition span (7.7 of 9.9 nats; AtP estimate 0.1), which the screen had missed. Edges and faithfulness were recomputed for the new top 15; screen-only lists are kept in circuit_*.json.
* **IG_AtP_input_interpolation** (minor): IG-AtP interpolates the input difference (embedding at the differing positions; the exchanged states for C2a) with every activation live, so gradients stay total derivatives; it did not improve the random-node correlation and plain AtP was kept. The S19 (arXiv 2606.09899) HVP correction was not implemented within the timebox.
* **faithfulness_definition** (minor): Faithfulness type 1/2 freeze every non-circuit node to the corrupt run (type 1) or the corrupt-class same-template mean (type 2) on the clean input with circuit nodes live and the input embedding clean (MIB style). With the embedding also patched, as the plan wrote, no clean information can enter a frozen network and f(k) = 0 by construction. Type 1 is ~0 at every k <= 60 (the decision nodes need distributed upstream processing); completeness (top-k jointly noised) and sufficiency (top-k jointly denoised), both live, carry the faithfulness result. Type 2 is undefined for C1-forced (one prompt per wording) and C2a's corrupt run is an intervention, so C2a reports completeness/sufficiency only.
* **transcoder_extension_dropped** (minor): F11: the Qwen3-8B transcoders (~96.5 GB) exceed the 23 GB GPU and 57 GB RAM and circuit-tracer is not installed; dropped at the precheck (results/transcoder_precheck.json). No feature-level account.
* **C2b_dropped** (minor): C2b (ban vs twin on T10) was not run (first droppable item after the transcoders).
* **hardware** (minor): Ran on one NVIDIA L4 (23 GB; plan: RTX A4500 20 GB); the embedding stayed on the GPU.
* **generation_alignment_rule** (minor): C1-forced's top-10 includes the layer-0 COND MLP, whose positions (the forced instruction) have no counterpart in the B3 twin's condition sentence; by the rule committed in amendment 0a the generation TOP5 uses the five highest-ranked non-COND nodes (all at DEC) and RAND5 matches those.
* **FREE_condition_exact** (minor): FREE is implemented exactly without online hooks: the edited opening is teacher-forced and each slot samples with its own uniforms until the first divergence; rows that reproduce the whole opening continue from the edited decision position (identical to PREFILL), diverged rows continue from their own prefix with only the edits at earlier positions.
* **engine_check_reference** (minor): The T10 engine-check reference (art_pHL7LWNhpcCS) was generated on an RTX 4090 with the iteration-6 exp29 engine and different CRN keys, so T10 is compared at the label level only; B3 uses the same keys and engine family.
* **sign_flip_exact_to_40** (minor): The sign-flip test is exact up to n = 40 (meet-in-the-middle enumeration of all 2^n sign patterns) instead of exact to 25 and Monte Carlo beyond.
* **head_null_sensitivity_posthoc** (minor): POST HOC (labelled, committed before its rows): the top decision heads are write-norm outliers, so their matched pools fell back to the 50 nearest heads (smaller norms; head draws are not rescaled in the committed design); a sensitivity re-runs those nulls with each draw rescaled to the target's write norm. The primary validation is unchanged.
* **stability_screen** (minor): Pair set B (stability) ran the screen, exact patching of the top 60 + 20 calibration nodes, path patching and the F4b sweep, without the 160-node reliability check or IG; 12 of its 15 pairs have TE > 0.2.
* **C1natB_pair_dropped_W2|guy** (minor): C1natB: pair W2|guy vs W2|hair has TE 0.158 <= 0.2
* **C1natB_pair_dropped_W4|guy** (minor): C1natB: pair W4|guy vs W4|kid has TE 0.171 <= 0.2
* **C1natB_pair_dropped_W5|fire** (minor): C1natB: pair W5|fire vs W5|kid has TE 0.072 <= 0.2
* **time_rule_C1nat** (minor): validation extrapolated to 75 min > 45: V = 15 clean prompts + 5 held-out (committed time rule)
* **dose_sensitivity_posthoc** (minor): POST HOC (labelled; commit_dose_<contrast> before its rows): at the committed dose 2 the matched random five also saturates the minority algorithm, so a dose sensitivity was added: logit-level P(minority token) at doses 0.25-2 and PREFILL generation of TOP5 / RAND5 at doses 0.5 and 1 on the same 30 CRN slots. The committed K3 verdicts use dose 2 only.
* **mcnemar_sidedness** (major): Commit #0's text says 'exact McNemar TOP5 vs RAND5 p < 0.05' without sidedness; the analysis code fixed by hash at commit #0 used the one-sided test, the plan's power calibration (8:0 -> 0.0078, 7:1 -> 0.07) is two-sided. The two-sided test is primary (conservative): C1 is PARTIAL (7:1, p = 0.070); with the one-sided test C1 would be PASS (p = 0.035). Both are reported.
* **oom_restarts** (minor): Two CUDA out-of-memory stops (class means cached on the GPU; memory accumulated over many stages in one process) were fixed (CPU class means, smaller row chunks, one process per stage) and every stage resumed from its files; no row was recomputed or dropped.
* **U5_not_run** (minor): GPU test U5 (path-patching sanity against direct-logit attribution) was not run.

## Layout

| path | content |
|---|---|
| `method.py` | all GPU stages (setup, contrasts, gputests, amend0a, circuit:X, commit1, validate:X, commit2, gen:X, enginecheck) |
| `analysis.py` | validation / generation statistics, motif test, stability, verdicts, figures, `method_out.json` |
| `make_readme.py` | writes this README from `results/summary.json` |
| `run_chain3.sh` ... `run_chain7.sh`, `run_final.sh` | the stage chains as run (3b resumed 3 after a CUDA OOM; 6-7 ran one stage per process) |
| `src/deviations_final.py` | completes `results/deviations.json` |
| `src/k3cfg.py` | constants, seeds, utilities |
| `src/k3engine.py` | model loading, component edit hooks, cached forwards, AtP gradients, CRN generation |
| `src/k3prompts.py` | prompts, noun variants, forced paraphrases, position classes |
| `src/k3circuit.py` | AtP / IG-AtP screen, exact patching, path patching, faithfulness, write norms, random pools |
| `src/k3stats.py` | exact sign-flip (meet-in-the-middle), Holm, McNemar, Newcombe, Wilson |
| `src/k3motif.py` | committed motif function and bands |
| `src/label_k3.py` | frozen labellers (vendored iteration-7 label worker) |
| `src/novelty_k3.py` | novelty audit of correct 'other' programs |
| `audit/rederive.py` | stdlib re-derivation of the headlines with placebos |
| `tests/test_labeller.py` | labeller re-check (T7) |
| `inputs/` | read-only copies of the prior artifacts used (iteration 2-7 prompts, units, bench, labellers, Gemma G1 results) |
| `predictions/` | commits #0, amendment 0a, #1, #2 (hash chain in `commitments.log`), hardware |
| `results/` | `circuit_*.json` (screen, exact rows, edges, faithfulness), `selection_*.json`, `summary.json`, checks |
| `data/` | `validation_rows_*.jsonl`, `gen_raw_*.jsonl`, `gen_labels_*.jsonl`, `rows.jsonl`, engine check |
| `figures/` | circuit graphs, AtP vs exact, faithfulness, validation, generation, motif panel, stability |
| `method_out.json` | exp_gen_sol_out: one example per generation slot with predict_TWIN / predict_TOP5 / predict_RAND5 |

## How to run

```bash
uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml
.venv/bin/python src/download_model.py            # Qwen/Qwen3-8B@b968826d into the HF cache
.venv/bin/python tests/test_labeller.py           # T7 labeller re-check (CPU)
.venv/bin/python method.py --stages setup,contrasts,gputests,amend0a,circuit:C1forced,circuit:C2a,circuit:C1nat,circuit:C1mix
.venv/bin/python method.py --stages f4b:C1forced,f4b:C2a,commit1:C1forced+C2a,validate:C1forced,validate:C2a,commit2:C1forced+C2a,gen:C1forced,gen:C2a,enginecheck
.venv/bin/python method.py --stages valsens:C1forced,valsens:C2a,f4b:C1nat,commit1b:C1nat,validate:C1nat,circuitlite:C1natB,f4b:C1natB,dose:C1forced,dose:C2a
./run_final.sh                                     # deviations, novelty audit, analysis, re-derivation, README, schema check
```

Hardware used: one NVIDIA L4 (23 GB), 6 CPUs, 57 GB RAM. Every stage resumes from its files.

## Restoring removed files

* `.venv/` (deleted, regenerable): `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml`
* `cache/` (deleted, regenerable): AtP / exact arrays (`cache/*.npz`), frozen class-mean tensors (`cache/vectors/`)
  and temporary files are rebuilt by `.venv/bin/python method.py --stages circuit:C1forced,circuit:C2a,circuit:C1nat,circuit:C1mix,commit1`
  (deterministic seeds; the sha256 of every frozen class-mean tensor is in `results/selection_*.json`).
* `**/__pycache__/` (deleted, regenerable): recreated automatically when the code is imported
  (`python -m compileall src audit inputs`).
* Kept artifacts (`results/`, `data/`, `figures/`, `predictions/`, `inputs/`) stay on the run's storage volume at these
  relative paths and are all small text/figure files, so they are also in the published repository.
* The model weights live in the shared Hugging Face cache, not in this directory: `huggingface-cli download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218`
  (or `.venv/bin/python src/download_model.py`).
