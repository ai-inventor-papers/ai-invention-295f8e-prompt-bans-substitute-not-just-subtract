# Does Gemma's base model predict nudge effects? (Claim E, second-family replication)

This repository tests whether `google/gemma-3-4b-pt` (the base model) predicts which of 15 frozen coding tasks a
ban-free activation nudge can move in `google/gemma-3-4b-it`, and where the moved programs land. It also writes the
base model's task-spec states into the tuned model (a pt→it transplant) and compares this against matched controls.

- **Setup.** Both models run in bf16, text-only, one at a time on one 23 GB NVIDIA L4: 12,290 programs, 2.16
  GPU-hours of generation, USD 0.39 of OpenRouter judges.
- **Status.** Gemma's iteration-4 push outcomes were already seen, so every result here is a **replication, never a
  held-out confirmation**.
- **Corrections.** Holm across the secondary family is left to the evaluation step; all p values below are raw.

## Results

**Bottom line.**

1. **E-A2: PASS. The pt model's runner-up algorithm predicts where nudged programs land.**
   - Seven tasks had confirmed escapes and β ≥ 0.05. In 5 of them the modal landing was the pt runner-up r_u.
   - The hit rate is 0.71 against a mean per-event chance of 0.30; the exact Poisson-binomial p is 0.025.
   - The pt-composition forecast beats iteration 4's association forecast ("name the standard alternative") by
     **1.50 nats per event** (one-sided Wilcoxon p = 0.023, decisive at 7 events). It beats AST proximity by
     0.51 nats.
2. **E-A1: INCONCLUSIVE. At this power, the share of the base repertoire that is non-default does not predict how
   movable a task is.**
   - Spearman ρ(β_u, E_u) = 0.42, one-sided permutation p = 0.060, n = 15 units. The rule needs ρ ≥ 0.5 with
     p < 0.01.
   - 2 of 3 base-collapsed tasks are immovable; the rule needs ≥ 80%.
   - β is ahead of no rival. The it model's own twin modal share (ρ = 0.67) and the novelty-instruction prompt
     (ρ = 0.64) track movability better, as in iteration 4.
   - The direction is right: 6 of 7 base-diverse tasks (β ≥ 0.2) are movable, against 2 of 8 others. A descriptive,
     non-registered one-sided Fisher test gives p = 0.032.
   - With n = 15, a true ρ of 0.5 has well under 50% power.
3. **Transplant: sufficiency on 2 of 7 base-diverse tasks.** The pt task-spec states are written into blocks 11–22
   of the it model (λ = 1; no task broke validity, so λ stayed at 1).
   - Every program stays valid (pass ratio 0.98–1.00).
   - **T04** moves from naive search to `builtin` (40/50; twin 6/50).
   - **R6** moves from a linear scan to binary search (39/50; twin 4/50). Both land on the pt runner-up.
   - The other five base-diverse tasks stay at the it default.
   - The two moved tasks are exactly the base-diverse tasks whose it twin already writes the pt runner-up 8–12% of
     the time. The transplant **amplifies an existing minority mode**; it does not install an absent one.
   - Both matched controls break most programs at the same non-massive norm (RND pass 0.16–0.50, XT 0.00–0.22).
     The pre-declared norm-confound rule therefore applies (RND confounded, XT decisive). XT is itself broken, so
     the controls show mainly that the coherent pt content is benign where an equally large random or cross-task
     displacement is destructive.
   - The read-position transplant and the three base-collapsed controls stay within 0.05 of the twin. R1's
     transplant halves its pass rate without moving its algorithm.
4. **No correct novel algorithm.** The novelty audit judged all 56 correct `other` programs from every arm: 35
   catalogue variants, 21 degenerate and 0 novel (rule-of-three bound 0.054).

### Per-unit results

| Unit | D_u (twin share) | β (pt) | class | r_u | E_u (α1, α2) | E_u max | landing | r_u = landing | PN excess | novelty off | twin modal | open. margin |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| T1 | dfs (0.75) | 0.05 | INTERMEDIATE | bfs | 0.156 (0.125, 0.188) | 0.188 | bfs | yes | 0.02 | 0.77 | 0.62 | 0.0 |
| T2 | dijkstra (1.00) | 0.03 | COLLAPSED | bf_spfa | 0.062 (0.000, 0.125) | 0.125 | bf_spfa | yes | 0.04 | 0.20 | 1.00 | 21.7 |
| T03 | full_sort (1.00) | 0.23 | DIVERSE | quickselect | 0.031 (0.000, 0.062) | 0.062 | size_k_heap | no | 0.06 | 0.67 | 1.00 | 18.6 |
| T04 | naive (0.88) | 0.51 | DIVERSE | builtin | 0.062 (0.000, 0.125) | 0.125 | builtin | yes | 0.06 | 0.70 | 0.88 | -27.0 |
| T06 | hash_set (1.00) | 0.23 | DIVERSE | sort_adjacent | 0.000 (0.000, 0.000) | 0.000 | – | – | 0.00 | 0.00 | 1.00 | 34.2 |
| T05 | hash_map (1.00) | 0.53 | DIVERSE | brute_force | 0.062 (0.000, 0.125) | 0.125 | brute_force | yes | 0.04 | 0.00 | 1.00 | 16.8 |
| T10 | dfs (1.00) | 0.28 | DIVERSE | bfs | 0.062 (0.000, 0.125) | 0.125 | union_find | no | 0.14 | 0.00 | 1.00 | -20.2 |
| R1 | greedy_end (1.00) | 0.02 | COLLAPSED | dag_longest_path | 0.000 (0.000, 0.000) | 0.000 | – | – | 0.02 | 0.00 | 1.00 | 0.0 |
| T08 | iteration (1.00) | 0.10 | INTERMEDIATE | fast_doubling | 0.000 (0.000, 0.000) | 0.000 | – | – | 0.00 | 0.00 | 1.00 | 16.6 |
| R3 | kahn (1.00) | 0.12 | INTERMEDIATE | dfs_postorder | 0.000 (0.000, 0.000) | 0.000 | – | – | 0.00 | 0.00 | 1.00 | – |
| T13 | sort_sweep (1.00) | 0.04 | COLLAPSED | union_find | 0.000 (0.000, 0.000) | 0.000 | – | – | 0.00 | 0.00 | 1.00 | 0.0 |
| R6 | linear_scan (0.92) | 0.40 | DIVERSE | binary_search | 0.531 (0.688, 0.375) | 0.688 | binary_search | yes | 0.36 | 1.00 | 0.92 | 6.0 |
| T14 | sort_by_count (1.00) | 0.12 | INTERMEDIATE | quickselect_counts | 0.000 (0.000, 0.000) | 0.000 | – | – | 0.08 | 0.57 | 1.00 | 18.9 |
| T11 | patience_bisect (1.00) | 0.41 | DIVERSE | quadratic_dp | 0.031 (0.000, 0.062) | 0.062 | quadratic_dp | yes | 0.02 | 0.00 | 1.00 | 4.4 |
| R2 | dfs_parent (1.00) | 0.11 | INTERMEDIATE | edge_count | 0.000 (0.000, 0.000) | 0.000 | – | – | 0.00 | 0.00 | 1.00 | 10.9 |

Notes on the columns:
- **D_u (twin share):** the it twin's default and its share of correct twin programs.
- **β:** the pt share of non-default catalogue algorithms (pooled pt-chat + pt-plain, valid attempts, LOW_CORRECT).
- **E_u:** the share of the 16 fresh directions whose push escapes, mean over α (per-α values in brackets).
- **landing:** the modal correct off-default catalogue label among confirmed escapes.
- **PN excess:** max over α of plan noise's correct off-default share minus the twin's.
- **novelty off:** the catalogue off-default share under the novelty instruction.
- **twin modal:** the twin's modal share over all attempts.
- **open. margin:** the teacher-forced log-probability margin of D_u's canonical opening over r_u's (tokens 1–8).

Figures:
- `figures/fig1_beta_vs_escape.pdf`: β vs E_u.
- `figures/fig2_compositions.pdf`: per-task compositions of pt, twin and landings.
- `figures/fig3_direction_heatmap.pdf`: per-direction stage-1 shares, with confirmed escapes starred.

### E-A1: β vs escape fraction

- n = 15 defaulted units; Spearman ρ(β, E_u) = 0.421, one-sided permutation p = 0.0596 (200,000 permutations); Kendall τ-b = 0.367.
- Base-collapsed units immovable: 0.67 of 3; base-diverse units with E_u = 0: 0.14 of 7; units with β ≥ 0.05: 12.
- Partial ρ given catalogue size K and exp23's forced-'can' count: 0.408 (given K only: 0.446).
- **Verdict: INCONCLUSIVE** (criteria neither met nor disconfirmed).

| Rival | sign | n | ρ(rival, E) | ρ(β,E) − ρ(rival,E) | 90% bootstrap CI | β ahead |
|---|---|---|---|---|---|---|
| twin_modal_share | -1 | 15 | 0.668 | -0.247 | [-0.755, 0.259] | no |
| novelty_off_cat | 1 | 15 | 0.640 | -0.219 | [-0.786, 0.430] | no |
| opening_margin | -1 | 14 | 0.272 | 0.147 | [-0.458, 0.725] | no |
| merit_gap_runtime | -1 | 15 | 0.381 | 0.040 | [-0.453, 0.695] | no |
| merit_gap_tokens | -1 | 15 | 0.409 | 0.011 | [-0.634, 0.656] | no |

| Sensitivity | n | ρ | p (one-sided) | verdict under the same rule |
|---|---|---|---|---|
| beta_pt_chat | 15 | 0.617 | 0.0095 | PARTIAL |
| beta_pt_plain | 15 | 0.362 | 0.0927 | INCONCLUSIVE |
| beta_pt_pooled | 15 | 0.421 | 0.0602 | INCONCLUSIVE |
| beta_excl_other | 15 | 0.388 | 0.0771 | INCONCLUSIVE |
| beta_correct_programs_only_any_n | 11 | 0.274 | 0.2097 | DISCONFIRMED |
| beta_pooled_with_rejudged_disputed_rows | 15 | 0.389 | 0.0764 | INCONCLUSIVE |
| E_off_any_exp23_definition | 15 | 0.421 | 0.0602 | INCONCLUSIVE |
| E_off_corr | 15 | 0.520 | 0.0258 | PARTIAL |
| E_u_max | 15 | 0.421 | 0.0602 | INCONCLUSIVE |
| without_regate_flagged_tasks | 14 | 0.343 | 0.1125 | INCONCLUSIVE |
| secondary_target_pn_excess | 15 | 0.454 | 0.0458 | INCONCLUSIVE |
| descriptive_beta_vs_exp23_E_t | 15 | 0.354 | 0.1000 | INCONCLUSIVE |

Fresh vs iteration-4 movability agreement: 0.87 (8 fresh movable, 6 iteration-4 movable).

Reading E-A1:
- **The movable tasks.** T1 (DFS ↔ BFS, the least collapsed it twin), R6 (E_u = 0.53, every escape lands on binary
  search) and six tasks with one or two confirmed directions. Seven tasks are immovable at both doses.
- **The rivals.** The it model's own twin modal share and the novelty-instruction ceiling predict E_u better than
  β, and β is not ahead of any rival by the paired task bootstrap.
- **Affordance check.** The partial ρ given catalogue size and exp23's forced-'can' count barely changes (0.41).
- **Sensitivities.**
  - The pt-chat-only β reaches ρ = 0.62 (p = 0.0095), but that arm is 91% unusable output.
  - The β from correct programs only (11 units with any correct pt program) gives ρ = 0.27.
  - The re-judged-disputed β gives ρ = 0.39.
  - E_u from correct programs only gives ρ = 0.52 (p = 0.026).
  - No variant meets the pre-registered bar.
- **Fresh vs iteration-4 movability.** The two agree on 13 of 15 tasks (0.87).

### E-A2: where escapes land

- Events: 7; hits 5; hit rate 0.71; mean chance 0.30; exact Poisson-binomial p = 0.0252.
- Log score base − association = 1.496 nats; base − proximity = 0.510 nats; test: decisive.
- **Verdict: PASS**.

| Event | r_u | landing | landing composition | n outcomes |
|---|---|---|---|---|
| T1 | bfs | bfs | {'bfs': 91} | 91 |
| T03 | quickselect | size_k_heap | {'size_k_heap': 7} | 7 |
| T04 | builtin | builtin | {'builtin': 44} | 44 |
| T05 | brute_force | brute_force | {'brute_force': 38} | 38 |
| T10 | bfs | union_find | {'union_find': 20} | 20 |
| R6 | binary_search | binary_search | {'binary_search': 375} | 375 |
| T11 | quadratic_dp | quadratic_dp | {'quadratic_dp': 19} | 19 |

Reading E-A2:
- **The two misses.** T03 lands on a size-k heap where the pt runner-up is quickselect. T10 lands on union-find
  where the pooled pt runner-up is BFS; union-find is the pt-chat-only runner-up for T10.
- **The log-score contest** uses one mean log score per event (q_base = pt counts + 0.5, 'other' floor 0.02).
  - R6's association forecast is undefined (iteration 4 asked about binary search) and scored as uniform.
  - Without R6, base still beats association by 1.57 nats (defined-only mean).
- **Caveat.** These are seen tasks: iteration 4's push landings were known for T1, T2, T03 and T05.

### Transplant: pt → it task-spec states (blocks 11–22, prefill)

λ = 1.0 (0 of 7 S_T tasks broke at λ = 1).

| Unit | β | twin s | T s [95% CI] | RND s | XT s | RP s | T pass ratio | RND pass ratio | McNemar T>RND (b10/b01, p) | T>XT (b10/b01, p) | T lands on r_u | JS(T,pt) < JS(twin,pt) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| T03 | 0.23 | 0.00 | 0.00 [0.00, 0.07] | 0.02 | 0.00 | 0.00 | 1.00 | 0.44 | 0/1, 1.000 | 0/0, 1.000 | no | no |
| T04 | 0.51 | 0.12 | 0.80 [0.67, 0.89] | 0.04 | 0.00 | 0.10 | 1.00 | 0.16 | 38/0, 0.000 | 40/0, 0.000 | yes | yes |
| T06 | 0.23 | 0.00 | 0.00 [0.00, 0.07] | 0.00 | 0.00 | 0.00 | 0.98 | 0.40 | 0/0, 1.000 | 0/0, 1.000 | no | no |
| T05 | 0.53 | 0.00 | 0.00 [0.00, 0.07] | 0.04 | 0.00 | 0.00 | 1.00 | 0.34 | 0/2, 1.000 | 0/0, 1.000 | no | no |
| T10 | 0.28 | 0.00 | 0.00 [0.00, 0.07] | 0.02 | 0.00 | 0.00 | 1.00 | 0.50 | 0/1, 1.000 | 0/0, 1.000 | no | no |
| R6 | 0.40 | 0.08 | 0.78 [0.65, 0.87] | 0.06 | 0.00 | 0.10 | 1.00 | 0.20 | 36/0, 0.000 | 39/0, 0.000 | yes | no |
| T11 | 0.41 | 0.00 | 0.02 [0.00, 0.10] | 0.16 | 0.00 | 0.00 | 1.00 | 0.48 | 0/7, 1.000 | 1/0, 0.500 | yes | yes |

Support share among valid S_T tasks: 0.29 (n valid = 7); collapsed controls within 0.05 of the twin: yes; read-position control within 0.05 everywhere: yes.

| Collapsed control | twin s | T s | T pass ratio |
|---|---|---|---|
| T2 | 0.00 | 0.00 | 1.00 |
| T13 | 0.00 | 0.00 | 1.00 |
| R1 | 0.00 | 0.00 | 0.52 |

Reading the transplant:
- **Size.** The pt–it difference at the task-spec positions is large: a median of 5.2 ban-free units (4.7–5.8 across
  the band blocks; `results/transplant_norms.json`, `figures/fig5_transplant_norms.pdf`). That is above the dose at which
  random noise broke programs in iteration 4.
- **Where it lives.** The 5 massive channels (M*, commit #1b) carry 86% of ||d||² at block 11, falling to 31–36% by
  blocks 21–22.
- **Content matters.** RND and XT copy the massive-channel move exactly and match the non-massive norm (U7: within
  0.2%), yet they break most programs. The transplant does not. Content, not size, separates them.
- **Sufficiency is partial.** Only T04 and R6 move, and only toward a mode the it twin already produces at 8–12%.
  T11's single quadratic-DP program is the only off-default output elsewhere.
- **Summary.** The B-style share (valid S_T tasks where s_T ≥ 0.5 β, T beats both controls after Holm and lands on
  r_u) is 2/7 = 0.29.
- **Controls.** The read-position site control is inert (within 0.05 of the twin everywhere). The base-collapsed
  controls T2, T13 and R1 do not move. R1's programs fail more often (pass ratio 0.52).
- **Figure:** `figures/fig4_transplant.pdf`.

### Plan noise (descriptive; a fresh direction per sample, N = 50 per α)

| Unit | twin pass | twin Hill-1 | PN α1 pass | PN α1 off-corr | PN α1 Hill-1 | PN α2 pass | PN α2 off-corr | PN α2 Hill-1 |
|---|---|---|---|---|---|---|---|---|
| T1 | 0.80 | 1.74 | 0.72 | 0.22 | 1.84 | 0.58 | 0.18 | 1.85 |
| T2 | 1.00 | 1.00 | 1.00 | 0.04 | 1.17 | 0.94 | 0.04 | 1.18 |
| T03 | 1.00 | 1.00 | 1.00 | 0.06 | 1.25 | 1.00 | 0.06 | 1.25 |
| T04 | 1.00 | 1.43 | 1.00 | 0.16 | 1.54 | 1.00 | 0.18 | 1.59 |
| T06 | 1.00 | 1.00 | 1.00 | 0.00 | 1.00 | 0.98 | 0.00 | 1.00 |
| T05 | 1.00 | 1.00 | 1.00 | 0.00 | 1.00 | 1.00 | 0.04 | 1.18 |
| T10 | 1.00 | 1.00 | 1.00 | 0.04 | 1.17 | 1.00 | 0.14 | 1.49 |
| R1 | 1.00 | 1.00 | 0.98 | 0.00 | 1.00 | 0.74 | 0.02 | 1.12 |
| T08 | 1.00 | 1.00 | 1.00 | 0.00 | 1.00 | 1.00 | 0.00 | 1.00 |
| R3 | 1.00 | 1.00 | 1.00 | 0.00 | 1.00 | 0.98 | 0.00 | 1.00 |
| T13 | 1.00 | 1.00 | 1.00 | 0.00 | 1.00 | 1.00 | 0.00 | 1.00 |
| R6 | 1.00 | 1.32 | 0.98 | 0.44 | 2.26 | 0.92 | 0.38 | 3.08 |
| T14 | 0.96 | 1.00 | 0.86 | 0.00 | 1.00 | 0.92 | 0.08 | 1.34 |
| T11 | 1.00 | 1.00 | 1.00 | 0.00 | 1.00 | 1.00 | 0.02 | 1.19 |
| R2 | 1.00 | 1.00 | 1.00 | 0.00 | 1.00 | 1.00 | 0.00 | 1.00 |

Plan noise rarely moves the it model. The exceptions are R6 (correct off-default share 0.44/0.38 at α 1/2), T1
(DFS ↔ BFS) and T10 (union-find at α 2). Spearman ρ(β, PN excess) = 0.45, one-sided p = 0.046 (secondary target).

### The base model, the twin and the labels

**What the base model looks like.** Gemma-3-4b-pt is a poor programmer in both formats:
- **Under the it chat template**, 91% of its 1,500 programs have no usable code. Only 10 programs (0.7%) pass the
  hidden tests. The pt-chat validity gate therefore failed: no unit had ≥ 20 correct pt-chat programs.
- **In plain completion of a `def solve(...)` stub**, 89 of 750 programs (12%) pass and 9.5% are invalid.
- **Consequence for β.** Every unit has fewer than 20 correct pooled programs (max 18), so β, r_u and q_base use
  the pre-registered LOW_CORRECT rule: catalogue labels over all valid attempts, flagged. They therefore reflect the
  algorithms the base model attempts, not the ones it gets right.
- **Re-gate.** Runtime labels agree with the two-family judge adjudication on 30 of 30 it-twin programs, but on
  only 5 of 30 pt programs. These are mostly broken code: the tracer says `unknown` and both judges say `other`.
  After the inline judge, 20 of 30 pt labels agree with the adjudication (see *Re-gate* below).

**Fresh it twin (N = 50 per task).**
- **Defaults.** Every one of the 15 tasks has a default. 12 are fully collapsed (one label on all 50 programs).
- **T1 now has a default.** It is DFS on 30 of 40 correct programs, where iteration 4's twin was tied 25/25.
- **T04** is naive (0.88). **R6** is the off-catalogue linear scan (0.92), now a named extended label.
- **Twin pass rate:** 0.98.

### Re-gate, audits and checks

- **Engine check (positive control, gates Stage 1).** It used exp23's own slot keys, direction 9003 and the
  640-token cap. Per-slot label agreement with the iteration-4 rows is 100% on the T1 twin (DFS 25 / BFS 25), the T1
  esc9003 α-1 push (BFS 29/30, as in iteration 4) and the T2 twin, so JS = 0 ≤ the null p95. Result: PASS
  (`results/engine_check.json`).
- **GPU tests.**
  - U1, U2 and U4 pass: α-0 rows are bit-identical, pre-band states identical, CRN slots independent of
    batch-mates.
  - U3: the realised push along u is within 0.18%, missing the plan's 0.1% (bf16 rounding; deviation D2).
  - U5 passes: pt and it logits differ, both continue a stub with valid Python, the key maps are identical and the
    vocabularies identical.
  - U6 passes: the transplanted state equals h_pt exactly at block 11 and non-spec positions are untouched.
  - U7 passes on the split control edit: the displacement along g is within 0.2% and the massive channels equal the
    transplant's.
  - U9: B = 42 at P = 249 plus 1,536 tokens peaks at 18.4 GB of 23.7 GB.
- **CPU tests T1–T8 all pass** (`results/tests_cpu.json`):
  - the labeller re-check (13 bench gates reproduced, 22/22 suite references);
  - the T2 rule (4 classes on the references, all 219 iteration-4 structural matches);
  - the R6 linear-scan reference (56/56 hidden tests);
  - code extraction on 20 pt-style outputs and the plain-completion stop rule;
  - the frozen-analysis self-test, the seed audit (52001–52016 unused anywhere in iterations 3–4) and the grep
    audit (0 ban frames in every fed prompt).
- **Style re-gate** (`results/regate.json`, `figures/fig6_regate.pdf`).
  - **Kappa** (runtime vs AST over all valid Stage-1 programs): 0.82 for bench, 0.75 for suite.
  - **Sample** of 60 programs judged by gemini-2.5-flash and gpt-4.1-mini with a deepseek tie-break: the it-twin
    programs agree 30/30; the pt programs agree 5/30 on the runtime label and 20/30 on the final label.
  - **The gate failed.** The cause is broken pt code: the tracer says `unknown`, both judges say `other`. The
    pre-declared fallback applies (every runtime/AST disagreement is judged). R1 is flagged (excluded in a
    sensitivity: ρ = 0.34).
- **Structural audit** (`results/structural_audit.json`): 92 default/runner-up programs of both models
  re-judged. Agreement with the final labels is 0.99, with one misread (a pt T06 program).
- **pt label audit** (`results/pt_label_audit.json`): 225 pt programs (15 per unit) re-judged. Agreement with the
  combined label is 0.64, from 0.47 (T03, R1, R6, R2) to 0.93 (T04). The base-model labels are the weakest
  link of this design.
- **Iteration-4 appendix** (`results/iter4_rescored.json`). The re-gated T2 rule changes 258 iteration-4 T2 labels:
  T2's E_t falls 0.25 → 0.125 and its ban compliance A_t falls 0.96 → 0.34. This confirms the iteration-4
  mislabel (exp23 D14).
- **Independent re-derivation** (`audit/rederive.py` → `results/rederive.json`): 0 mismatches.
  - It re-derives β, r_u, every E_u, ρ, the E-A2 hits and the transplant McNemar counts.
  - Permutation p = 0.0596 vs the reported 0.0596.
  - Placebos: β shuffled across units gives a mean ρ of 0.008; labels shuffled within CRN pairs give a McNemar
    rejection rate of 0.011.
- **Second-code-path audit** (`audit/rederive_headlines.py` → `results/rederive_headlines.json`):
  - Written from scratch, from `data/labels.jsonl`, with the standard library only, against the reported values.
  - All 9 headline values match: ρ, permutation p, E-A2 hits, Poisson-binomial p, base − association, Wilcoxon
    p, the two rival ρs and the 56 correct `other` programs. D_u, β and r_u also match, and so do the transplant
    counts (T04 40/50, R6 39/50) with their McNemar tests.
  - Placebos fail as required: β shuffled reaches p < 0.05 in 5.7% of draws; a random r_u passes the E-A2 hit
    test in 2.5%; a random forecast wins the log-score contest in 1.6%; within-pair label swaps give a McNemar
    rejection rate of 3.1%; shuffled movability gives a Fisher rejection rate of 3.2%.
  - Not re-derived by this second path: base − proximity (0.51 nats), the bootstrap CIs, the plan-noise table,
    the transplant norms and the novelty-audit classifications (judge outputs).
- **Pre-registration integrity** (`commitments.log` hash chain, which verifies):
  - commit #0: 2026-10-21T13:10:30Z, before the first engine-check row at 13:12:05Z;
  - commit #1: 2026-10-21T14:41:55Z, before the first push row at 14:43:40Z;
  - commit #1b (M amendment): 2026-10-21T14:45:48Z, before the first transplant row at 15:28:48Z.
- **Cost.**
  - Generation took 2.16 GPU-hours: pt-chat 44 min, push population 35 min, transplant 22 min, the rest 30 min.
  - OpenRouter spend was USD 0.39 against a USD 1.50 cap.

## What was done

**Question (Claim E, secondary).** In iteration 4, ban-free random pushes moved Gemma-3-4b-it off its default
algorithm on some coding tasks but not on others. The narrowed-repertoire account says instruction tuning narrowed a
repertoire the base model still has. If so, the base model's own algorithm mix should predict which tasks a nudge can
move, and where the moved programs land. This repository tests that account on a second model family
(`google/gemma-3-4b-pt` vs `google/gemma-3-4b-it`, bf16, text-only, one model on the GPU at a time). Gemma's
iteration-4 push outcomes were already seen, so this is a **replication, not a held-out confirmation**.

**Predictors (from the base model, pt).** For each of the 15 frozen tasks:
- The pt model writes programs on the **same token ids** as the it twin prompts: pt under the it chat template
  (N = 100), and plain completion of a `def solve(...)` stub (N = 50).
- The pre-registered pt-chat validity gate decides whether the primary estimate pools both arms.
- **β_u**: the pt model's share of non-default catalogue algorithms among its correct programs. With fewer
  than 20 correct programs, the pre-registered fallback uses all valid attempts (as happened for every unit).
- **r_u**: the pt runner-up algorithm.
- **q_base**: the pt landing forecast.
- The it model's default D_u comes from a fresh it twin (N = 50; share ≥ 0.6 among ≥ 10 correct programs).

**Outcome (in the it model).** A fresh, never-run push population is applied to the it model:
- 16 isotropic directions (PCG64 seeds 52001–52016) at α ∈ {1, 2}, with N = 10 per direction-dose.
- Each push is a displacement-targeted edit of the task-spec block outputs of blocks 11–22, during the prefill only.
- The dose uses the outlier-excluded ban-free unit of iteration 4.
- A direction-dose **escapes** if both hold:
  - stage 1: catalogue off-default share − twin share ≥ 0.20, and pass ≥ 0.8 × the twin's pass;
  - a 20-sample confirmation keeps both criteria and passes an exact binomial test at N = 30.
- **E_u** = the share of the 16 directions that escape, averaged over α.
- The **landing** is the modal correct off-default catalogue label among the confirmed escapes.

**Tests.**
- **E-A1:** Spearman ρ(β_u, E_u) ≥ 0.5 with permutation p < 0.01; ≥ 80% of base-collapsed units immovable; β ahead
  of every rival by paired task bootstrap.
- **E-A2:** the pt runner-up r_u equals the push landing at a hit rate ≥ 0.7 against per-event chance, plus a
  log-score contest of q_base against iteration 4's association and AST-proximity forecasts.
- **Transplant:** the pt task-spec states (blocks 11–22, λ = 1, prefill) are written into the it model on
  base-diverse tasks (β ≥ 0.2). Controls run on the same CRN slots:
  - **RND:** a matched-norm random displacement. It is matched in the non-massive subspace and copies the
    transplant's massive-channel move.
  - **XT:** a cross-task displacement from the donor task.
  - **RP:** a read-position transplant (site control).
  - **S_C:** base-collapsed negative-control tasks.

**Baselines and rivals (same engine, same CRN uniforms per (task, template, slot)).**
- The un-pushed it twin (zero dose).
- Per-sample plan noise (α 1 and 2, N = 50 each).
- The novelty instruction (the prompting ceiling), N = 30.
- The twin's modal share (how collapsed the default is).
- The teacher-forced opening margin between D_u's and r_u's canonical openings.
- The merit gap (reference runtime and token-length ratio of r_u to D_u).

**Pre-registration.** The hash chain in `commitments.log` records three commits:
- **Commit #0:** every threshold, decision rule, seed, slot scheme, the drop order and the frozen analysis code
  (`predictions/analysis_E.py`), before any generation.
- **Commit #1:** the predictor table (β, r_u, q_base, classes), the transplant sets, the massive-channel set M, the
  donor map, the opening ladder and a grep audit showing no ban frame in any fed prompt. It precedes the first push
  sample.
- **Commit #1b:** the amended massive-channel set (deviation D11), before any transplant sample.

**Labeller style re-gate (before any label was used).**
- **T2 rule.** The iteration-4 exp8-suite labeller read array-based Dijkstra as Bellman-Ford/SPFA. A
  deterministic structural rule now labels it Dijkstra, in both the runtime and the AST path. It reproduces all 219
  iteration-4 structural matches and leaves every suite reference unchanged.
- **R6 extended label.** R6's off-catalogue `linear_scan` was promoted to a named extended label, backed by a
  reference that passes the hidden tests.
- **Judge sample.** A 60-program sample, half it and half pt, was judged blind by two model families
  (gemini-2.5-flash, gpt-4.1-mini) with a deepseek tie-break.
- **Structural audit.** The audit read the defaults and runner-ups of both models.

## Layout

| Path | What it is |
|---|---|
| `method.py` | pipeline driver (stages in order; `--from <stage>` resumes; starts the label worker) |
| `src/cfg.py` | constants (models, band, caps, seeds, thresholds), paths, utilities |
| `src/stage_inputs.py` | preflight: input staging + `inputs/SHA256SUMS`, bench vs ITER2 commitment, dependency extraction (10 datasets), seed audit, labeller re-check (re-gate 5a) |
| `src/engine.py` | bf16 text-only loader for it and pt, CRN inverse-CDF sampler, per-row block-output edits (push / transplant / matched random / cross-task / read position) |
| `src/push.py`, `src/units.py`, `src/prox.py`, `src/commit.py` | iteration-4 displacement-targeted push, outlier-excluded ban-free unit, Zhang–Shasha proximity, hash chain (ported from exp23) |
| `src/prompts.py` | frozen twin prompts (byte-identical to iteration 4), novelty prompt, pt plain-completion prompt, grep audit |
| `src/gen.py` | GPU runner: tests U1–U9, engine check, stage 1 (it, pt), opening ladder, stage 2 (push + PN + confirmation), stage 3 (transplant) |
| `src/label_worker.py`, `src/regate_rules.py` | labeller (frozen bench + exp8 suite, judge on disagreement) + the re-gate T2 rule and extended labels |
| `src/regate.py` | re-gate judge sample, structural audit, iteration-4 rescoring |
| `src/predictors.py`, `src/ladder.py` | predictor table (D_u, β, r_u, q_base, rivals, S_T, S_C, M, donors) and commit #1; opening-margin rival |
| `src/analysis_E.py` → `predictions/analysis_E.py` | the FROZEN analysis (hash-committed in commit #0) |
| `src/final_analysis.py` | runs the frozen analysis on the labelled samples (escape, PN, E-A1, E-A2, transplant, verdicts) |
| `src/novelty_audit.py` | novelty audit of every correct 'other' program + pt label audit |
| `src/tests_cpu.py`, `src/engine_check_eval.py`, `src/transplant_decide.py` | CPU tests T1–T8, engine-check evaluation, transplant validity switch |
| `src/figures.py`, `src/outputs.py`, `src/bookkeeping.py` | figures F1–F6, `data/samples.jsonl` + `method_out.json`, timing/costs/deviations |
| `audit/rederive.py` | independent re-derivation of the headline numbers + placebos |
| `audit/rederive_headlines.py` | second, stdlib-only re-derivation from the raw labels (every headline number, with placebos) → `results/rederive_headlines.json` |
| `reproducibility.md` | exact reproduction steps (what was actually run, in order, with seeds, hardware and runtimes) |
| `src/commit0.py`, `src/amend_M.py` | commit #0 (protocol + frozen analysis + hardware) and commit #1b (massive-set amendment) |
| `src/rejudge_disputed.py`, `src/truncate_ptchat.py` | sensitivity re-judging of rate-limited 'disputed' rows; the one-off 640-token truncation of the first pt-chat batch |
| `src/report.py` | builds `results/report.md` (the result tables of this README) |
| `src/chain_after_pt.sh`, `src/chain_stage3.sh`, `src/chain_final.sh` | the hand-off scripts actually used to run the stages after stage 1 back to back |
| `src/download_models.py`, `src/wait_labels.py` | pinned model download; block until rows are labelled |
| `extensions/` | re-gate additions: `t2_wsp/dijkstra_array.py` (array Dijkstra reference), `R6/linear_scan.py` (extended label reference) |
| `predictions/` | `protocol_E.json`, `analysis_E.py`, `hardware.json` (commit #0); `predictors_draft.json`; `commit_E1.json` (commit #1) |
| `commitments.log` | sha256 hash chain (commit #0, commit #1, commit #1b) |
| `data/raw_*.jsonl` | every generated row (text + token ids + realised displacement) per stage |
| `data/labels.jsonl`, `data/samples.jsonl` | labels; merged per-sample table |
| `data/prompts_fed.jsonl` | every model-fed prompt (grep-audit registry) |
| `results/*.json` | all analyses (see Results) |
| `figures/` | fig1–fig6 (PDF + PNG) |
| `inputs/` | sha256-verified copies of every upstream input (`inputs/SHA256SUMS`) |
| `cache/` | clean it and pt block outputs at blocks 11–22 × task-spec positions (bf16 `.pt`, about 1.4 GB); kept on the run volume, not published |
| `method_out.json` (+ `full_`, `mini_`, `preview_`) | exp_gen_sol_out output |

## How to run

`reproducibility.md` has the exact steps that were run, in order, with seeds, hardware and runtimes.

```bash
uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml
# paths.local.json (unpublished) maps upstream artifact names to their workspaces; needed only by stage 'inputs'
.venv/bin/python method.py                    # full pipeline (about 2.5 GPU-hours on one 23 GB NVIDIA L4)
.venv/bin/python method.py --from analysis    # re-analyse the stored samples only (CPU)
.venv/bin/python audit/rederive.py            # independent re-derivation of the headline numbers
```

Environment: Python 3.12, torch 2.8.0+cu128, transformers 4.57.6 (`pyproject.toml` pins every package). The models are
`google/gemma-3-4b-it@093f9f38` and `google/gemma-3-4b-pt@cc012e0a`; their LFS sha256 are checked in
`predictions/commit_E1.json`. The HF cache is the run's shared cache (`HF_HOME`), not this folder.

## Restoring removed files

Every `delete` entry of `.aii/manifest.yaml` and the command that brings it back:

| Removed path | Restore with |
|---|---|
| `.venv/` | `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml` (or `./restore.sh`) |
| `**/__pycache__/` | `.venv/bin/python -m compileall src audit inputs/exp11/bench inputs/exp8/suite` (also recreated by any run) |
| model weights (shared Hugging Face cache, outside this folder) | `huggingface-cli download google/gemma-3-4b-it --revision 093f9f388b31de276ce2de164bdc2081324b9767` and `huggingface-cli download google/gemma-3-4b-pt --revision cc012e0a6d0787b4adcc0fa2c4da74402494554d` (both in `./restore.sh`) |

`cache/` is **kept**. It holds the activation tensors the transplant used, it stays on the run's volume only, and it
is not in the published repository. It can be regenerated with `.venv/bin/python src/gen.py stage1_it` and `stage1_pt`;
both skip generation rows that already exist and rebuild the cache files.

## Deviations (full text in `results/deviations.json`)

| | Deviation |
|---|---|
| D1 | GPU is an NVIDIA L4 (23 GB, Ada) instead of the planned RTX A4500; bf16 as planned; the engine check reproduces exp23's labels on 100% of matched slots. |
| D2 | U3: the realised push along u is within 0.18% (plan: 0.1%), a bf16-rounding floor at Gemma's activation scale; exp23's tolerance was 1%. |
| D3 | The it twin and the pt-chat arm ran in multi-prompt batches (B = 50, five templates per batch) instead of single-prompt batches; CRN uniforms per slot unchanged. |
| D4 | pt-chat cap 640 tokens (exp23's pilot cap) instead of 1,024/1,536 because pt rambles under the chat template; the first T2 batch was truncated to 640 tokens (exactly equivalent under CRN). |
| D5 | Default rule clarification: D_u needs ≥ 10 correct twin programs and a unique mode; R6's `linear_scan` promoted to a named extended label (reference passes 56/56). |
| D6 | Confirmation batches use their natural size instead of padding to B = 42. |
| D7 | The T2 rule is an AST structural check applied in both label paths (no new tracer probe). |
| D8 | exp8 suite gold re-check gives 0.804 vs the gate's 0.843 (exactly exp23's value); references 22/22. |
| D9 | Holm across the secondary family is left to the evaluation step; raw p values reported. |
| D10 | Inline judges are the frozen ones; audits use gemini-2.5-flash + gpt-4.1-mini with a deepseek tie-break. |
| D11 | Commit #1b, before any transplant sample: the literal massive-channel rule gave 488 channels; M was amended to the 5 channels most often in the per-position top-5 (99.1% of the squared residual norm). |
| D12 | The style re-gate failed on broken pt code (runtime vs adjudicated 0.60 bench, 0.50 suite; it programs 30/30); pre-declared fallback applied, R1 flagged, two sensitivities added. |
| D13 | Structural audit reads up to 3 (not 5) programs per group (92 items). |
| D14 | Programs that print a JSON-like line break the frozen bench harness; recorded as `invalid` (`harness_error`) instead of failing the chunk. |
| D15 | Every unit has < 20 correct pooled pt programs, so β, r_u and q_base use the pre-declared LOW_CORRECT rule (all valid attempts); the pt-chat validity gate failed and the pooled source is primary. |
| D16 | RND/XT re-implemented as a split edit before any transplant row (massive channels as the transplant, exact non-massive displacement along g) after the plan's single-vector edit failed U7 (non-massive part 13-18% short). |
| D17 | 104 rows left `disputed` by judge rate limits were re-judged after commit #1 for one sensitivity only; committed labels unchanged. |
