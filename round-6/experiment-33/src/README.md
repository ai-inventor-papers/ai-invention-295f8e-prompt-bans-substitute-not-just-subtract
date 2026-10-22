# Gemma: base runner-up vs the tuned model's own tail

This repository asks one question about `google/gemma-3-4b-it` (tuned) and `google/gemma-3-4b-pt` (base). When an
activation nudge moves the tuned model off its default algorithm on a coding task, which forecast names where the
nudged programs land? Three forecasts compete:
- the **base model's runner-up** algorithm r_u (and its distribution q_base);
- the **tuned model's own minority mode** t_u from 300 un-nudged samples per task (q_tail);
- the **tuned model's teacher-forced likelihood** of each algorithm's 48-token opening (q_lik).

It is iteration 6, step 5, of Claim L. It is the second-family **replication**: Gemma's iteration-5 landings were
already seen, and nothing here is pooled with the Qwen confirmation.

- **Setup.** Both models run bf16 (W16A16), text-only, one at a time on one 23 GB NVIDIA L4. The run produced 9,350
  generated programs and 4,836 teacher-forced passes in about 2.1 GPU-hours, plus USD 0.95 of OpenRouter judges.
- **Reuse.** exp28's engine, CRN sampler, push code, labellers and frozen twin prompts are reused. So are its 12,290
  rows, read from `inputs/exp28/`.
- **Pre-registration.** The hash chain in `commitments.log` holds three commits, all verified:
  - commit #0: protocol and frozen analysis, before any row;
  - commit #0b: a KeyError fix, before commit #1;
  - commit #1: the forecasts, at 23:50:52Z, before the first fresh push row at 23:52:40Z.
- **Corrections.** Holm is applied within this artifact. Holm across the iteration-wide family is left to the
  evaluation step.

## Results

**Bottom line.**

1. **All three forecasts usually name the landing, so the base runner-up shows no edge.** This is the pooled
   replication over 15 (unit, nudge) events, every one with a clear landing:
   - r_u hits **11 of 13** defined events (exact Poisson-binomial p = 5.8e-5 against a mean chance of 0.31). T03's
     r_u is undefined (see 4).
   - t_u hits **10 of 10** where defined (p = 7.9e-7). The 5 TAIL-EMPTY events leave t_u undefined.
   - The q_lik top-1 hits **13 of 15** (p = 3.5e-6).
   - **Where r_u and q_lik disagree, they split 2–2** (L1b sign test p = 0.69). r_u wins R6, where q_lik says
     bisect_module. q_lik wins T10, landing union_find.
   - **Where r_u and t_u disagree, t_u wins both events** (T10).
   - The unit-clustered version agrees: r_u 6/7, t_u 5/5, q_lik 7/8.
2. **L1a (the TAIL-EMPTY events) is DESCRIPTIVE.** r_u hits 5 of 5 (T05 FD, T11 FD and PN, T2 FD and PN;
   p = 0.0052, Holm 0.026). That is one event below the frozen 6-event bar. q_lik also hits all 5, so the base model
   adds nothing here that the tuned model's own likelihood lacks.
3. **The log-score contest is not robust to how the 'other' bin is handled.**
   - **Primary (frozen; each forecast's 'other' bin as defined in the plan).** q_base trails both rivals and is not
     non-inferior to q_tail:
     - q_base − q_tail = **−0.44 nats** per program, BCa 95% CI [−0.97, 0.09];
     - q_base − q_lik = **−0.39 nats** [−1.00, 0.08].
   - **Sensitivity: one fixed 0.02 'other' bin for every forecast.** The sign flips:
     - q_base − q_tail = **+0.19** [−0.07, 0.52], which is non-inferior;
     - q_base − q_lik = **+0.36** [0.07, 0.64], exact Wilcoxon p = 0.015.
   - **Sensitivity: 'other' excluded.** The same picture: +0.19 and +0.38.
   - **What drives the flip.** On T1, T2 and T10 most base attempts are broken code labelled 'other'. That gives
     q_base 0.81–0.87 of its mass on 'other'.
   - **Rivals beaten in every version.** q_base beats exp28's association forecast (+0.66 nats, p = 0.076). It also
     beats the raw-sum q_lik (+0.64), which is far too peaked.
4. **Iteration 5's 5-of-7 tally, rescored under repaired support.**
   - The repaired r_u scores 5/7, or 5/6 on the events where it is defined.
   - **T03's runner-up disappears.** The base model's 53 correct T03 programs are all the default (full_sort), so
     the frozen correct-only rule leaves r_u undefined. Iteration 5's quickselect rested on broken attempts.
   - t_u scores 5/5 where defined, and q_lik scores **6/7** (it misses only R6).
   - The tuned model's own tail and likelihood both name iteration 5's two misses: T03 → size_k_heap and
     T10 → union_find.
5. **Base support repaired, with caveats.**
   - **Support.** Few-shot plain completion lifts the base model to ≥ 20 correct programs on 9 of 15 tasks (for
     example T04 83, T05 54, T03 53, T06 51), against at most 18 in iteration 5. Its per-draw correct rate exceeds
     iteration 5's zero-shot 12% on 8 tasks. The path tasks and R1, R2, R3 stay at 0–3 correct programs, and T10
     reaches 19.
   - **Exemplar priming.** The family contrast is flagged (p < 0.01) on T1, T10, R3, T13 and R6. That makes T10's r_u
     **exemplar-sensitive**: bench exemplars give union_find, the right answer, while HumanEval+ exemplars give bfs.
     Excluding the exemplar-sensitive units T03 and T10, r_u hits 11/11.
6. **Labels.** The blind two-family audit of 225 base programs gives 0.86 (stratum-weighted, κ A–B 0.91). The r_u
   stratum gives only 0.70, so the gate fails.
   - The revision round re-judged 824 rows and relabelled 132.
   - T10 then passes (0.996). T2, R1, R3 and R2 are flagged AUDIT_FAIL; excluding them, r_u hits 9/11.
   - The it-model style re-gate agrees on 29/30.
7. **Fresh pushes are weaker than exp28's but land in the same places.**
   - **Directions.** 8 new directions at α 2 confirm escapes only on R6 and T04 (E_u 0.25) and on T05 and T11 (0.125).
   - **Plan noise.** Fresh per-sample plan noise moves R6 (0.42), T1 (0.38), T10 (0.20) and T04 (0.18).
   - **Fresh-only split** (outcomes unseen at commit #1): 11 events, with r_u 9/10, t_u 6/6 and q_lik 9/11.
8. **No new algorithm appears.**
   - **L2-G.** None of the 1,091 correct nudged off-default programs uses an algorithm absent from the base
     repertoire (rule-of-three bound 0.003).
   - **Novelty audit.** It finds 0 novel programs among 19 correct 'other' it programs (15 degenerate, 4 catalogue
     variants) and 0 among 5 base few-shot programs.

**Reading.** In Gemma, the iteration-5 lead (the base runner-up names the landing) survives as a hit rate. It does
not survive as evidence that the landing is absent from the tuned model. The tuned model's own likelihood ranks the
landing first on 13 of 15 events. Its own 300-sample tail names it whenever the tail is non-empty, including both
cases iteration 5 missed. The base model wins only where the tuned model's forecasts are silent or noisy, and there
q_lik wins as well. The log-score verdict depends on the 'other' bin, so it should be quoted with both scorings. All of
this is a replication on seen units. The LeetCode-derived tasks are memorised by both models, which is harmless for
this within-model comparison but rules out any claim of new capability.

Figures (PDF + PNG):
- `figures/fig1_pt_support.pdf`: base support per task, before and after the top-up;
- `figures/fig2_compositions.pdf`: q_base, q_tail and q_lik against the pooled landing composition per push unit;
- `figures/fig3_logscore_diffs.pdf`: per-event log-score differences, primary scoring;
- `figures/fig4_audit_agreement.pdf`: pt label-audit agreement, iteration 5 against iteration 6.

Integrity:
- **Engine check.** It matches exp28's rows on 0.99 of slots (twin 150/150), with JS 0 and byte identity 0.91.
- **Clean states.** U6 is bit-identical on 40/40.
- **Tests.** GPU tests U1–U9 and CPU tests T1–T12 pass.
- **q_lik checks.** The default ranks first on 13/15 units. The fp32 re-score of a 10% subsample flips no top-1, so
  the bf16 scores stand.
- **Re-derivation.** The stdlib-only `audit/rederive_l1.py` (system Python, no pipeline import) recomputes 36
  headline values from the raw label and teacher-forcing files with 0 mismatches. They include D_u, r_u, t_u,
  the q_lik top-1, the events, all hit counts and p values, both sign tests, both log-score scorings, the
  fresh-only split and the old tally. Placebos fail as required: a random r_u passes in 1.75% of draws, a
  random q_lik top-1 in 4.25%, and a random forecast never beats q_tail by 0.10 nats. Not re-derived: the
  bootstrap CIs, the Wilcoxon and sign-flip p values, and the judge-based audits.

## Result tables

**Primary: pooled (old exp28 + fresh) events, REPLICATION:** 15 events, 15 with a clear landing.

| Readout | Value |
|---|---|
| r_u = landing (all clear landings) | 11/13, mean chance 0.305, Poisson-binomial p = 5.8e-05 |
| t_u = landing (t_u defined) | 10/10, p = 7.9e-07 |
| q_lik top-1 = landing (defined) | 13/15, p = 3.5e-06 |
| L1a (TAIL-EMPTY events) | 5/5 hits, p = 0.0052; DESCRIPTIVE (5 tail-empty events with a clear landing < 6) |
| L1b (r_u ≠ q_lik top-1) | 4 events: base-only 2, lik-only 2, both 0, neither 0; sign p = 0.6875 |
| tail rival (r_u ≠ t_u) | 2 events: base-only 0, tail-only 2, both 0, neither 0; sign p = 1.0000 |
| log score q_base − q_tail (nats/program, mean over events) | -0.441 [BCa -0.971, 0.091; unit-cluster -1.133, 0.287], 5/15 events > 0, exact Wilcoxon p = 0.9397, unit sign-flip p = 0.7773 (8 units); non-inferior (lower bound > −0.10): no |
| log score q_base − q_lik (norm) (nats/program, mean over events) | -0.392 [BCa -0.996, 0.082; unit-cluster -1.162, 0.317], 7/15 events > 0, exact Wilcoxon p = 0.8486, unit sign-flip p = 0.7930 (8 units) |
| log score q_base − q_lik (raw) (nats/program, mean over events) | 0.641 [BCa -1.189, 4.470; unit-cluster -1.798, 4.567], 2/15 events > 0, exact Wilcoxon p = 0.9635, unit sign-flip p = 0.5000 (8 units) |
| log score q_base − q_assoc (nats/program, mean over events) | 0.655 [BCa -0.046, 1.489; unit-cluster -0.302, 1.724], 11/15 events > 0, exact Wilcoxon p = 0.0757, unit sign-flip p = 0.1055 (8 units) |
| unit-clustered (one pooled landing per unit) | r_u 6/7 (p = 0.0035), t_u 5/5, q_lik 7/8; sign-flip base−tail p = 0.7812 |
| Holm within this artifact | {"hits_all": 0.0003, "L1a": 0.026, "L1b": 1.0, "ls_base_vs_lik": 1.0, "ls_base_vs_tail": 1.0, "tail_sign": 1.0} |

| Unit | Nudge | Landing | Composition (correct off-default catalogue) | other | r_u | t_u | q_lik top-1 | TAIL-EMPTY | log q_base | log q_tail | log q_lik |
|---|---|---|---|---|---|---|---|---|---|---|---|
| R6 | FD | binary_search | {"binary_search": 441} | 55 | binary_search | binary_search | bisect_module | no | -0.604 | -0.406 | -1.491 |
| R6 | PN | binary_search | {"binary_search": 62} | 15 | binary_search | binary_search | bisect_module | no | -0.755 | -0.635 | -1.720 |
| T04 | FD | builtin | {"builtin": 101} | 0 | builtin | builtin | builtin | no | -0.095 | -0.108 | -0.727 |
| T04 | PN | builtin | {"builtin": 26} | 0 | builtin | builtin | builtin | no | -0.095 | -0.108 | -0.727 |
| T05 | FD | brute_force | {"brute_force": 50} | 0 | brute_force | – | brute_force | yes | -0.134 | -1.386 | -0.424 |
| T10 | FD | union_find | {"union_find": 28} | 0 | bfs | union_find | union_find | no | -3.006 | -0.916 | -0.600 |
| T10 | PN | union_find | {"union_find": 19} | 0 | bfs | union_find | union_find | no | -3.006 | -0.916 | -0.600 |
| T03 | FD | size_k_heap | {"size_k_heap": 10} | 0 | – | size_k_heap | size_k_heap | no | -1.792 | -1.253 | -1.135 |
| T03 | PN | size_k_heap | {"size_k_heap": 12, "heapify_pop": 1} | 0 | – | size_k_heap | size_k_heap | no | -1.792 | -1.306 | -1.165 |
| T11 | FD | quadratic_dp | {"quadratic_dp": 50} | 0 | quadratic_dp | – | quadratic_dp | yes | -0.065 | -1.099 | -0.189 |
| T11 | PN | quadratic_dp | {"quadratic_dp": 6} | 0 | quadratic_dp | – | quadratic_dp | yes | -0.065 | -1.099 | -0.189 |
| T1 | FD | bfs | {"bfs": 87} | 0 | bfs | bfs | bfs | no | -1.724 | -0.071 | -1.352 |
| T1 | PN | bfs | {"bfs": 11} | 0 | bfs | bfs | bfs | no | -1.724 | -0.071 | -1.352 |
| T2 | FD | bf_spfa | {"bf_spfa": 32} | 0 | bf_spfa | – | bf_spfa | yes | -2.175 | -1.609 | -0.825 |
| T2 | PN | bf_spfa | {"bf_spfa": 10} | 0 | bf_spfa | – | bf_spfa | yes | -2.175 | -1.609 | -0.825 |

Below the 5-program floor (no event): T05 PN (3).

**Split: fresh-only events (outcomes unseen at commit #1):** 11 events, 11 with a clear landing.

| Readout | Value |
|---|---|
| r_u = landing (all clear landings) | 9/10, mean chance 0.323, Poisson-binomial p = 0.0002 |
| t_u = landing (t_u defined) | 6/6, p = 0.0003 |
| q_lik top-1 = landing (defined) | 9/11, p = 0.0006 |
| L1a (TAIL-EMPTY events) | 5/5 hits, p = 0.0052; DESCRIPTIVE (5 tail-empty events with a clear landing < 6) |
| L1b (r_u ≠ q_lik top-1) | 3 events: base-only 2, lik-only 1, both 0, neither 0; sign p = 0.5000 |
| tail rival (r_u ≠ t_u) | 1 events: base-only 0, tail-only 1, both 0, neither 0; sign p = 1.0000 |
| log score q_base − q_tail (nats/program, mean over events) | -0.053 [BCa -0.645, 0.416; unit-cluster -0.729, 0.557], 5/11 events > 0, exact Wilcoxon p = 0.6177, unit sign-flip p = 0.6016 (7 units); non-inferior (lower bound > −0.10): no |
| log score q_base − q_lik (norm) (nats/program, mean over events) | -0.182 [BCa -0.904, 0.339; unit-cluster -1.035, 0.515], 7/11 events > 0, exact Wilcoxon p = 0.5508, unit sign-flip p = 0.7422 (7 units) |
| log score q_base − q_lik (raw) (nats/program, mean over events) | 1.675 [BCa -0.683, 6.200; unit-cluster -1.376, 6.347], 3/11 events > 0, exact Wilcoxon p = 0.7114, unit sign-flip p = 0.4375 (7 units) |
| log score q_base − q_assoc (nats/program, mean over events) | 1.018 [BCa 0.294, 1.950; unit-cluster 0.063, 2.182], 9/11 events > 0, exact Wilcoxon p = 0.0161, unit sign-flip p = 0.0391 (7 units) |
| unit-clustered (one pooled landing per unit) | r_u 5/6 (p = 0.0139), t_u 4/4, q_lik 6/7; sign-flip base−tail p = 0.6016 |
| Holm within this artifact | {"hits_all": 0.0012, "L1a": 0.026, "L1b": 1.0, "ls_base_vs_lik": 1.0, "ls_base_vs_tail": 1.0, "tail_sign": 1.0} |

| Unit | Nudge | Landing | Composition (correct off-default catalogue) | other | r_u | t_u | q_lik top-1 | TAIL-EMPTY | log q_base | log q_tail | log q_lik |
|---|---|---|---|---|---|---|---|---|---|---|---|
| R6 | FD | binary_search | {"binary_search": 61} | 12 | binary_search | binary_search | bisect_module | no | -0.700 | -0.552 | -1.637 |
| R6 | PN | binary_search | {"binary_search": 21} | 5 | binary_search | binary_search | bisect_module | no | -0.750 | -0.628 | -1.713 |
| T04 | FD | builtin | {"builtin": 44} | 0 | builtin | builtin | builtin | no | -0.095 | -0.108 | -0.727 |
| T04 | PN | builtin | {"builtin": 9} | 0 | builtin | builtin | builtin | no | -0.095 | -0.108 | -0.727 |
| T05 | FD | brute_force | {"brute_force": 11} | 0 | brute_force | – | brute_force | yes | -0.134 | -1.386 | -0.424 |
| T10 | PN | union_find | {"union_find": 10} | 0 | bfs | union_find | union_find | no | -3.006 | -0.916 | -0.600 |
| T03 | PN | size_k_heap | {"heapify_pop": 1, "size_k_heap": 6} | 0 | – | size_k_heap | size_k_heap | no | -1.792 | -1.352 | -1.190 |
| T11 | FD | quadratic_dp | {"quadratic_dp": 30} | 0 | quadratic_dp | – | quadratic_dp | yes | -0.065 | -1.099 | -0.189 |
| T11 | PN | quadratic_dp | {"quadratic_dp": 5} | 0 | quadratic_dp | – | quadratic_dp | yes | -0.065 | -1.099 | -0.189 |
| T2 | FD | bf_spfa | {"bf_spfa": 7} | 0 | bf_spfa | – | bf_spfa | yes | -2.175 | -1.609 | -0.825 |
| T2 | PN | bf_spfa | {"bf_spfa": 6} | 0 | bf_spfa | – | bf_spfa | yes | -2.175 | -1.609 | -0.825 |

Below the 5-program floor (no event): T05 PN (1), T10 FD (4), T03 FD (0), T1 FD (0), T1 PN (0).

**Split: old-only events (exp28 rows, v6 definition):** 13 events, 13 with a clear landing.

| Readout | Value |
|---|---|
| r_u = landing (all clear landings) | 9/11, mean chance 0.292, Poisson-binomial p = 0.0004 |
| t_u = landing (t_u defined) | 10/10, p = 7.9e-07 |
| q_lik top-1 = landing (defined) | 11/13, p = 2.3e-05 |
| L1a (TAIL-EMPTY events) | 3/3 hits, p = 0.0417; DESCRIPTIVE (3 tail-empty events with a clear landing < 6) |
| L1b (r_u ≠ q_lik top-1) | 4 events: base-only 2, lik-only 2, both 0, neither 0; sign p = 0.6875 |
| tail rival (r_u ≠ t_u) | 2 events: base-only 0, tail-only 2, both 0, neither 0; sign p = 1.0000 |
| log score q_base − q_tail (nats/program, mean over events) | -0.549 [BCa -1.112, 0.001; unit-cluster -1.233, 0.204], 4/13 events > 0, exact Wilcoxon p = 0.9659, unit sign-flip p = 0.7852 (8 units); non-inferior (lower bound > −0.10): no |
| log score q_base − q_lik (norm) (nats/program, mean over events) | -0.361 [BCa -1.035, 0.162; unit-cluster -1.209, 0.381], 6/13 events > 0, exact Wilcoxon p = 0.8121, unit sign-flip p = 0.7930 (8 units) |
| log score q_base − q_lik (raw) (nats/program, mean over events) | 0.796 [BCa -1.381, 5.059; unit-cluster -1.952, 5.289], 2/13 events > 0, exact Wilcoxon p = 0.9268, unit sign-flip p = 0.5000 (8 units) |
| log score q_base − q_assoc (nats/program, mean over events) | 0.797 [BCa 0.002, 1.656; unit-cluster -0.298, 1.907], 10/13 events > 0, exact Wilcoxon p = 0.0636, unit sign-flip p = 0.1055 (8 units) |
| unit-clustered (one pooled landing per unit) | r_u 6/7 (p = 0.0035), t_u 5/5, q_lik 7/8; sign-flip base−tail p = 0.7852 |
| Holm within this artifact | {"hits_all": 0.0021, "L1a": 0.2083, "L1b": 1.0, "ls_base_vs_lik": 1.0, "ls_base_vs_tail": 1.0, "tail_sign": 1.0} |

#### Per-unit forecasts (commit #1)

| Unit | D_u (share, N 300) | K | r_u (correct / valid support; flags) | t_u (tail counts) | q_lik top-1 (norm) | DISCORDANT | TAIL-EMPTY |
|---|---|---|---|---|---|---|---|
| T1 | dfs (0.74) | 6 | bfs (0 / 55; LOW_CORRECT, THIN_RU) | bfs ({"bfs": 67}) | bfs | no | no |
| T2 | dijkstra (1.00) | 5 | bf_spfa (2 / 39; LOW_CORRECT, THIN_RU, AUDIT_FAIL) | – ({}) | bf_spfa | no | yes |
| T03 | full_sort (1.00) | 6 | None (0 / 0; exemplar-sensitive) | size_k_heap ({"size_k_heap": 1}) | size_k_heap | no | no |
| T04 | naive (0.86) | 6 | builtin (49 / 75; –) | builtin ({"builtin": 43}) | builtin | no | no |
| T06 | hash_set (1.00) | 5 | sort_adjacent (12 / 22; –) | – ({}) | floyd | yes | yes |
| T05 | hash_map (1.00) | 4 | brute_force (20 / 31; –) | – ({}) | brute_force | no | yes |
| T10 | dfs (1.00) | 4 | bfs (0 / 10; LOW_CORRECT, THIN_RU, exemplar-sensitive) | union_find ({"union_find": 1}) | union_find | yes | no |
| R1 | greedy_end (1.00) | 4 | dag_longest_path (0 / 1; LOW_CORRECT, THIN_RU, AUDIT_FAIL) | – ({}) | dag_longest_path | no | yes |
| T08 | iteration (1.00) | 4 | None (0 / 0; –) | – ({}) | memo_recursion | no | yes |
| R3 | kahn (1.00) | 4 | dfs_postorder (0 / 10; LOW_CORRECT, THIN_RU, AUDIT_FAIL) | – ({}) | source_removal | yes | yes |
| T13 | sort_sweep (1.00) | 3 | None (0 / 0; –) | – ({}) | union_find | no | yes |
| R6 | linear_scan (0.84) | 4 | binary_search (5 / 154; –) | binary_search ({"binary_search": 45, "other": 2}) | bisect_module | yes | no |
| T14 | sort_by_count (1.00) | 4 | heap (1 / 4; THIN_RU) | – ({}) | heap | no | yes |
| T11 | patience_bisect (1.00) | 3 | quadratic_dp (29 / 62; –) | – ({}) | quadratic_dp | no | yes |
| R2 | dfs_parent (1.00) | 4 | edge_count (0 / 8; LOW_CORRECT, THIN_RU, AUDIT_FAIL) | – ({}) | union_find | yes | yes |

#### Iteration-5 tally rescored (7 exp28 E-A2 events)

| Unit | exp28 landing | r_u exp28 | r_u repaired | changed | t_u | q_lik top-1 | twin-silent (exp28 N 50) |
|---|---|---|---|---|---|---|---|
| T1 | bfs | bfs | bfs | no | bfs | bfs | no |
| T03 | size_k_heap | quickselect | None | yes | size_k_heap | size_k_heap | yes |
| T04 | builtin | builtin | builtin | no | builtin | builtin | no |
| T05 | brute_force | brute_force | brute_force | no | – | brute_force | yes |
| T10 | union_find | bfs | bfs | no | union_find | union_find | yes |
| R6 | binary_search | binary_search | binary_search | no | binary_search | bisect_module | no |
| T11 | quadratic_dp | quadratic_dp | quadratic_dp | no | – | quadratic_dp | yes |

All 7 — exp28 r_u: 5/7 (undefined = miss; p = 0.0252); defined-only 5/7 (p = 0.0252); repaired r_u: 5/7 (undefined = miss; p = 0.0252); defined-only 5/6 (p = 0.0119); t_u: 5/7 (undefined = miss; p = 0.0252); defined-only 5/5 (p = 0.0009); q_lik top-1: 6/7 (undefined = miss; p = 0.0030); defined-only 6/7 (p = 0.0030).
Twin-silent subset (T03, T05, T10, T11): repaired r_u 2/4 (defined-only 2/3), t_u 2/4, q_lik 4/4.

#### Sensitivities (pooled events)

| Variant | r_u hits | L1a | L1b |
|---|---|---|---|
| r_u_from_fewshot | 13/13 (p = 1.0e-07) | 5/5 | 2 vs 0 |
| r_u_from_exp28_pooled | 11/15 (p = 0.0004) | 5/5 | 2 vs 4 |
| r_u_from_F_bench | 13/13 (p = 1.0e-07) | 5/5 | 2 vs 0 |
| r_u_from_F_he | 11/15 (p = 0.0004) | 5/5 | 2 vs 4 |
| r_u_from_stageA_plus_exp28 | 11/13 (p = 5.8e-05) | 5/5 | 2 vs 2 |
| exemplar_sensitive_excluded | 11/11 (p = 9.3e-07) | 5/5 | 2 vs 0 |
| audit_fail_excluded | 9/11 (p = 0.0006) | 3/3 | – vs – |
| q_lik_from_qwen_programs | q_lik top-1 7/11 | – | 2 vs 2; base − lik -0.106 nats |
| log scores, uniform_other | base − tail 0.191 | – | base − lik 0.363 |
| log scores, other_excluded | base − tail 0.186 | – | base − lik 0.381 |

#### Base-model (pt) support

| Unit | exp28 chat correct/draws | exp28 plain correct/draws | few-shot correct/draws (valid) | pooled correct | q_base basis | r_u exp28 → repaired | priming p (few-shot vs zero-shot; F_bench vs F_he) |
|---|---|---|---|---|---|---|---|
| T1 | 0/100 | 0/50 | 0/300 (300) | 0 | valid attempts (LOW_CORRECT) | bfs → bfs | 0.0066; 1.0e-04 |
| T2 | 0/100 | 0/50 | 3/300 (300) | 3 | valid attempts (LOW_CORRECT) | bf_spfa → bf_spfa | 0.0620; 0.0919 |
| T03 | 2/100 | 12/50 | 39/100 (97) | 53 | correct | quickselect → None | 0.6221; 0.0806 |
| T04 | 1/100 | 17/50 | 65/100 (97) | 83 | correct | builtin → builtin | 0.5983; 0.0827 |
| T06 | 0/100 | 14/50 | 37/100 (98) | 51 | correct | sort_adjacent → sort_adjacent | 0.1416; 0.1212 |
| T05 | 3/100 | 10/50 | 41/100 (96) | 54 | correct | brute_force → brute_force | 0.0456; 0.0320 |
| T10 | 0/100 | 1/50 | 18/300 (271) | 19 | valid attempts (LOW_CORRECT) | bfs → bfs | 0.0685; 1.0e-04 |
| R1 | 0/100 | 0/50 | 0/100 (93) | 0 | valid attempts (LOW_CORRECT) | dag_longest_path → dag_longest_path | 0.1118; 0.0478 |
| T08 | 1/100 | 10/50 | 25/100 (98) | 36 | correct | fast_doubling → None | 0.3986; 0.9706 |
| R3 | 0/100 | 1/50 | 2/100 (83) | 3 | valid attempts (LOW_CORRECT) | dfs_postorder → dfs_postorder | 0.1565; 0.0032 |
| T13 | 0/100 | 5/50 | 23/100 (95) | 28 | correct | union_find → None | 0.1061; 0.0089 |
| R6 | 1/100 | 3/50 | 18/300 (283) | 22 | correct | binary_search → binary_search | 0.0022; 1.0e-04 |
| T14 | 1/100 | 8/50 | 16/100 (96) | 25 | correct | quickselect_counts → heap | 0.7671; 0.0280 |
| T11 | 1/100 | 4/50 | 24/100 (93) | 29 | correct | quadratic_dp → quadratic_dp | 0.8578; 0.0130 |
| R2 | 0/100 | 0/50 | 0/100 (90) | 0 | valid attempts (LOW_CORRECT) | edge_count → edge_count | 0.2137; 0.6087 |

Tasks with few-shot per-draw correct rate above exp28's zero-shot 12%: 8/15; tasks with >= 20 correct pooled: 9/15.

#### pt label audit (two judge families + tie-break)

Round 1: overall (stratum-weighted) 0.864, raw 0.818, r_u stratum 0.702 (n = 104), kappa A–B 0.909; affected tasks ['T2', 'T10', 'R1', 'R3', 'R2']; AUDIT_FAIL after the revision round: ['R1', 'R2', 'R3', 'T2'].

| Unit | n | agreement (weighted) | r_u stratum | correct | failing | kappa A–B |
|---|---|---|---|---|---|---|
| T1 | 15 | 0.836 | 1.000 | – | 0.933 | 0.587 |
| T2 | 15 | 0.931 | 0.300 | – | 0.533 | 0.595 |
| T03 | 15 | 1.000 | – | 1.000 | – | 1.000 |
| T04 | 15 | 1.000 | 1.000 | 1.000 | – | 1.000 |
| T06 | 15 | 0.953 | 0.800 | 0.867 | – | 0.889 |
| T05 | 15 | 1.000 | 1.000 | 1.000 | – | 1.000 |
| T10 | 15 | 0.930 | 0.200 | – | 0.467 | 0.828 |
| R1 | 15 | 0.413 | 0.000 | – | 0.667 | 0.000 |
| T08 | 15 | 1.000 | – | 1.000 | – | 1.000 |
| R3 | 15 | 0.762 | 0.300 | – | 0.467 | 0.541 |
| T13 | 15 | 1.000 | – | 1.000 | – | 1.000 |
| R6 | 15 | 0.824 | 1.000 | 0.800 | – | 0.595 |
| T14 | 15 | 1.000 | 1.000 | 1.000 | – | 1.000 |
| T11 | 15 | 1.000 | 1.000 | 1.000 | – | 1.000 |
| R2 | 15 | 0.807 | 0.250 | – | 0.533 | 0.478 |

Revision re-audit (fresh sample): overall 0.890, r_u stratum 0.407; per task {"T2": 0.96, "T10": 0.996, "R1": 0.319, "R3": 0.976, "R2": 0.933}.

#### Fresh pushes (alpha 2) beside exp28's directions

| Unit | twin off-default correct (T1.0) | fresh FD off-corr median / max | exp28 α2 median / max | fresh stage-1 passing | fresh E_u(α2) | fresh PN α2 off-corr | exp28 PN α2 off-corr |
|---|---|---|---|---|---|---|---|
| R6 | 0.120 | 0.100 / 1.000 | 0.300 / 0.933 | 2 | 0.250 | 0.420 | 0.380 |
| T04 | 0.140 | 0.050 / 0.967 | 0.000 / 0.767 | 2 | 0.250 | 0.180 | 0.180 |
| T05 | 0.000 | 0.000 / 0.367 | 0.000 / 1.000 | 1 | 0.125 | 0.020 | 0.040 |
| T10 | 0.005 | 0.000 / 0.200 | 0.000 / 0.433 | 0 | 0.000 | 0.200 | 0.140 |
| T03 | 0.000 | 0.000 / 0.000 | 0.000 / 0.233 | 0 | 0.000 | 0.140 | 0.060 |
| T11 | 0.000 | 0.000 / 0.967 | 0.000 / 0.633 | 1 | 0.125 | 0.100 | 0.020 |
| T1 | 0.225 | 0.050 / 0.600 | 0.267 / 0.833 | 1 | 0.000 | 0.380 | 0.180 |
| T2 | 0.000 | 0.100 / 0.133 | 0.000 / 0.600 | 1 | 0.000 | 0.120 | 0.040 |

**L2-G:** 0 of 1091 correct nudged off-default catalogue programs use an algorithm with zero valid and zero correct pt programs (rule-of-three bound 0.003).

**Novelty audit:** it model 19 correct 'other' programs, novel 0 (rule-of-three 0.158), classes {"twin6:twin_T10": {"CATALOGUE_VARIANT": 1}, "twin6:twin_T13": {"CATALOGUE_VARIANT": 1}, "push6:esc63002_a2": {"DEGENERATE": 4}, "push6:esc63008_a2": {"DEGENERATE": 7}, "push6:pn6_a2": {"DEGENERATE": 4, "CATALOGUE_VARIANT": 1}, "push6:esc63004_a2": {"CATALOGUE_VARIANT": 1}}; pt few-shot 5 correct 'other', novel 0.

## What was done

**Question (Claim L, second family, secondary).** When an activation nudge moves Gemma-3-4b-it off its default
algorithm, which forecast names where the programs land?
- **q_base / r_u**: the base model's (gemma-3-4b-pt) repertoire and its runner-up algorithm (iteration 5's lead: 5 of 7);
- **q_tail / t_u**: the tuned model's OWN minority mode, from 300 twin samples per task (the confound iteration 5's
  review raised);
- **q_lik**: the tuned model's teacher-forced likelihood of each algorithm's 48-token opening under the twin prompts.

Gemma's iteration-5 landings were already seen, so everything here is a **replication**; it is never pooled with the
Qwen confirmation.

**Repairs before any new push (all frozen in commit #1, hash-chained):**
1. **Base support.** Few-shot plain completion (two solved exemplars + the target's stub; even draws use loop-only
   bench exemplars, odd draws two HumanEval+ problems from the declared dependency) adds 100 pt draws per task (stage A)
   and up to 200 more (stages B and C) for the push units still below 20 correct programs (R6, T10, T1, T2 reached the
   300-draw cap). Pooled with exp28's 1,500 pt-chat and 750 pt-plain rows.
2. **Tuned tail.** The it twin goes from 50 to 300 samples per task (200 at T 1.0, 100 at T 1.3) on exp28's exact CRN
   slots.
3. **q_lik.** Up to 10 name-scrubbed, test-passing forced programs per catalogue algorithm, written by gemma-3-4b-it
   itself (filled from the iteration-2 Qwen programs or suite references where Gemma cannot write the algorithm),
   teacher-forced under the 5 twin prompts at batch 1.
4. **Label audit.** A blind two-family judge audit (gemini-2.5-flash, gpt-4.1-mini, deepseek tie-break) of 15 pt
   programs per task, with one revision round.

**Fresh events.** 8 never-run isotropic directions (seeds 63001-63008) at α 2 (N 10, confirmation to N 30) and fresh
per-sample plan noise (PN, α 2, N 50) on the 8 tasks that moved in iteration 5, displacement-targeted at the task-spec
positions of blocks 11-22 during the prefill (exp28's push code and outlier-excluded unit).

**Events (v6).** One event per (unit, nudge type ∈ {FD, PN}), pooling exp28's and the fresh qualifying cells (pass
≥ 0.8 × twin pass); an event needs ≥ 5 correct off-default catalogue programs; the landing is the modal label if it leads
the next by ≥ 15 points.

**Tests (frozen analysis, `predictions/analysis_L_gemma.py`).** Hits of r_u / t_u / q_lik top-1 against per-event
chance 1/(K_u − 1) (exact Poisson-binomial); L1a on TAIL-EMPTY events; L1b sign test on events where r_u ≠ q_lik top-1;
the tail rival sign test; paired per-event log scores (exact Wilcoxon, BCa and unit-cluster bootstrap,
non-inferiority to q_tail at −0.10 nats); a unit-clustered version; the iteration-5 tally rescored; L2-G; a novelty
audit.

## Layout

| Path | What it is |
|---|---|
| `method.py` | pipeline driver (stages in order; `--from <stage>` resumes; starts the background label worker) |
| `src/cfg.py` | exp28's constants + the iteration-6 block at the end (push tasks, seeds 63001-63008, slots, thresholds) |
| `src/stage_inputs6.py` | S0: bench sha256 vs ITER2 commitment, dependency (10 datasets), seed audit, labeller re-check |
| `src/protocol6.py`, `src/amend0b.py` | commit #0 (protocol + frozen analysis + hardware) and commit #0b (KeyError fix) |
| `src/analysis_L.py` → `predictions/analysis_L_gemma.py` | the FROZEN analysis (forecasts, events, tests) |
| `src/prompts6.py` | few-shot pt prompts (F_bench / F_he exemplar rules) and forced prompts on exp28's `prompts.py` |
| `src/gen6.py` | GPU runner: U-tests, engine check, U6 clean states, twin top-up, forced programs, few-shot pt, fresh pushes |
| `src/qlik6.py` | q_lik: forced-program selection, scrubbing, re-labelling, fills; teacher forcing; fp32 subsample |
| `src/audit6.py` | pt label audit (+ revision), it style re-gate, novelty audit (OpenRouter, cached, capped) |
| `src/forecasts6.py` | forecast table, rescored iteration-5 events, push plan, grep audit → commit #1 |
| `src/final6.py` | events + L1 contest + splits + sensitivities, old tally, L2-G, push descriptives, pt repertoire, L3 |
| `src/engine_check6.py`, `src/tests6.py` | engine-check evaluation; CPU tests T1-T12 |
| `src/report6.py`, `src/figures6.py`, `src/outputs6.py`, `src/bookkeeping6.py` | report tables, figures, `method_out.json`, costs/timing/deviations |
| `src/chain6.sh`, `src/chain6b.sh` | the hand-off scripts actually used between GPU stages |
| `src/engine.py`, `src/push.py`, `src/units.py`, `src/prompts.py`, `src/label_worker.py`, `src/regate_rules.py`, `src/regate.py`, `src/novelty_audit.py`, `src/commit.py`, `src/analysis_E.py`, `src/predictors.py`, `src/stage_inputs.py`, `src/tests_cpu.py` | exp28's engine, push, unit, prompts, labellers, judge client and helpers (reused; `label_worker.py` also extracts few-shot rows, `commit.py` uses the iteration-6 genesis) |
| `audit/rederive_l1.py` | independent stdlib-only re-derivation of the headline numbers + placebos |
| `predictions/` | `protocol_G6.json`, `analysis_L_gemma.py`, `hardware.json` (commit #0/#0b; `analysis_L_gemma_commit0.py` is the exact commit-#0 version, sha256-verified, kept because #0b superseded it); `forecasts_G6.json`, `old_events_rescored.json`, `push_plan_G6.json` (commit #1); `forecasts_draft.json` |
| `commitments.log` | sha256 hash chain (genesis sha256('iter6_gemma_L')) |
| `data/raw_*6.jsonl` | every iteration-6 generated row (text, token ids, CRN key, precision, checkpoint, hook sha256, realised displacement) |
| `data/labels.jsonl` | labels of every iteration-6 row; `data/labels_pt_revised.jsonl` revision-round labels (if any) |
| `data/qlik_programs.jsonl`, `data/qlik_tf.jsonl` | the scored forced programs and every teacher-forced pass |
| `data/prompts_fed.jsonl` | every model-fed prompt (grep-audit registry) |
| `data/judge_cache*.jsonl` | judge caches (exp28's, extended) |
| `results/*.json`, `results/report6.md` | all analyses (see Results); `results/commit_chain.json` and `results/integrity6.json` verify the hash chain and that each commit precedes the rows it must precede |
| `docs_head.md`, `docs_static.md`, `src/build_readme.py` | the hand-written parts of this README and the script that assembles it with `results/report6.md` and the deviations |
| `figures/` | fig1-fig4 (PDF + PNG) |
| `inputs/` | sha256-verified copies of every upstream input (`inputs/SHA256SUMS`), incl. `inputs/exp28/` (exp28's rows, labels, results, predictions, src) |
| `method_out.json` | exp_gen_sol_out output (datasets gemma_l1_events, gemma_pt_repertoire, gemma_twin_tail, gemma_qlik, gemma_push_fresh) |

## How to run

`reproducibility.md` lists the exact commands that were run, in order, with seeds and hardware.

```bash
uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml
.venv/bin/python src/download_models.py         # pinned gemma-3-4b-it / -pt snapshots (gated; HF_TOKEN)
.venv/bin/python method.py                      # full pipeline (about 2.1 GPU-hours on one 23 GB NVIDIA L4)
.venv/bin/python method.py --from final         # re-analyse the stored rows only (CPU)
.venv/bin/python audit/rederive_l1.py           # independent re-derivation of the headline numbers
```

Environment: Python 3.12, torch 2.8.0+cu128, transformers 4.57.6 (`pyproject.toml` pins every package). The HF cache
is the run's shared cache (`HF_HOME`), not this folder. `paths.local.json` (not published) maps upstream artifact names
to their folders; only the preflight stage reads it.

## Restoring removed files

Every `delete` entry of `.aii/manifest.yaml` and the command that brings it back:

| Removed path | Restore with |
|---|---|
| `.venv/` | `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml` (or `./restore.sh`) |
| `**/__pycache__/` | `.venv/bin/python -m compileall src audit inputs/exp11/bench inputs/exp8/suite` (also recreated by any run) |
| model weights (shared Hugging Face cache, outside this folder) | `.venv/bin/python src/download_models.py` (pinned revisions `093f9f388b31de276ce2de164bdc2081324b9767` / `cc012e0a6d0787b4adcc0fa2c4da74402494554d`; both in `./restore.sh`) |

Nothing heavy is kept outside text files: no activation cache is written (the U6 check reads exp28's cache in place).

## Deviations (full text in `results/deviations.json`)

| | Deviation |
|---|---|
| D1 | GPU is one NVIDIA L4 (23 GB, the same card type as exp28) instead of the planned RTX A4500 (20 GB); bf16 as planned. The engine check therefore compares like with like: per-slot label agreement 0.99 (twin 150/150, R6 alpha-2 push 8/10), byte identity 0.91, JS(old, new) = 0 (results/engine_check6.json). |
| D2 | The pinned Gemma snapshots were no longer in the run's shared HF cache (exp28's copy was cleaned); they were re-downloaded at the same pinned revisions (it@093f9f38, pt@cc012e0a); key maps and vocabularies equal exp28's recorded hashes (U5). |
| D3 | exp28's cache/hit_<task>_<W>.pt states (1.4 GB) were read in place for the U6 equality check instead of being copied into inputs/; the recomputed states are bit-identical on 40/40 (task, template) pairs. |
| D4 | Labeller re-check: 8 of the 300 re-labelled exp28 rows were 'disputed' in exp28 (judge rate limits) and are now judged; all other 292 rows reproduce their exp28 label and pass flag exactly. |
| D5 | CPU test T10: one synthetic case had a wrong expectation (the frozen stop rule ignores an incomplete last line and stops one line later); the expectation was corrected, the rule is unchanged. |
| D6 | Twin top-up rows run in exp28's multi-prompt batches (B 50 = 5 templates x 10 slots); the T 1.3 rows use the same CRN uniforms as T 1.0 slots 0-19 with a per-row temperature in the same sampler. |
| D7 | q_lik name scrubbing for the path tasks T1/T2 adds a path-alias pass after the frozen bench scrubber (whose lexicon has no A*/IDDFS/bidirectional/Dijkstra/Bellman-Ford/SPFA/Dial/Floyd aliases). |
| D8 | Priming check: a Monte-Carlo permutation test of independence with the chi-square statistic (10k permutations), the Monte-Carlo counterpart of the planned Fisher-Freeman-Halton test. |
| D9 | U7 (teacher forcing batch 1 vs batch 4 with right padding) differs by up to 0.15 nats per token in bf16; as planned, every q_lik pass is batch 1. |
| D10 | Commit #0b: the frozen analysis's unit_clustered() lacked the 'nudge' key read by hit_test() (KeyError on first use, found in a dry run on exp28 rows with the draft forecasts); fixed by adding 'nudge' = 'FD+PN' before commit #1 and before any fresh push row; no rule or threshold changed. |
| D11 | Few-shot pt batches: the first 100 T2 draws ran in multi-prompt batches of 40 (masked decode, ~160 ms/step); the job was stopped (PID-based) and resumed with single-prompt batches of 50 per exemplar family (no mask, ~85 ms/step), push units first. CRN uniforms per draw are unchanged; batch_kind is recorded per row. |
| D12 | Stages B and C of the few-shot top-up ran only for the 8 push units (the only units that can have events); the 7 non-push units got stage A (100 draws). Decided on time alone, before any stage-B row. |
| D13 | With >= 20 correct pt programs the frozen rule is correct-only, and on T03, T08 and T13 every correct pt program is the default: r_u is UNDEFINED there (q_base = add-one over zero counts = uniform). T03's iteration-5 runner-up (quickselect) rested on broken attempts; undefined forecasts are excluded from hit tests and scored as uniform in the log-score contest (defined-only results beside). |
