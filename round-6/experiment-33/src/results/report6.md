# Report (iteration 6, step 5: Gemma, Claim L replication)

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

### Per-unit forecasts (commit #1)

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

### Iteration-5 tally rescored (7 exp28 E-A2 events)

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

### Sensitivities (pooled events)

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

### Base-model (pt) support

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

### pt label audit (two judge families + tie-break)

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

### Fresh pushes (alpha 2) beside exp28's directions

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

