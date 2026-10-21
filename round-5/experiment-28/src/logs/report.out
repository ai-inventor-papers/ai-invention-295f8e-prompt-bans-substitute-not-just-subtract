### Per-unit table

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

### E-A1

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

### E-A2

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

### Transplant (pt → it task-spec states)

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

### Plan noise (descriptive)

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

### Novelty audit

56 correct 'other' programs across all arms; novel algorithms: 0; by arm: {'novelty:novelty': {'CATALOGUE_VARIANT': 5}, 'ptplain:pt_plain': {'DEGENERATE': 1}, 'push:esc52006_a2': {'CATALOGUE_VARIANT': 5, 'DEGENERATE': 4}, 'push:esc52012_a2': {'CATALOGUE_VARIANT': 4, 'DEGENERATE': 2}, 'push:esc52016_a2': {'CATALOGUE_VARIANT': 1, 'DEGENERATE': 1}, 'push:pn_a2': {'CATALOGUE_VARIANT': 2, 'DEGENERATE': 3}, 'push:esc52003_a2': {'CATALOGUE_VARIANT': 1}, 'push:esc52006_a1': {'DEGENERATE': 1}, 'push:pn_a1': {'DEGENERATE': 1, 'CATALOGUE_VARIANT': 1}, 'push:esc52002_a2': {'DEGENERATE': 1}, 'push:esc52005_a2': {'DEGENERATE': 1}, 'confirm:esc52012_a2': {'CATALOGUE_VARIANT': 5, 'DEGENERATE': 4}, 'confirm:esc52002_a2': {'CATALOGUE_VARIANT': 2}, 'confirm:esc52005_a2': {'DEGENERATE': 1, 'CATALOGUE_VARIANT': 3}, 'confirm:esc52016_a2': {'CATALOGUE_VARIANT': 1}, 'confirm:esc52002_a1': {'CATALOGUE_VARIANT': 1}, 'confirm:esc52012_a1': {'CATALOGUE_VARIANT': 2}, 'confirm:esc52015_a2': {'CATALOGUE_VARIANT': 1, 'DEGENERATE': 1}, 'transplant:RND': {'CATALOGUE_VARIANT': 1}}; rule-of-three upper bound: 0.054.

pt label audit: 225 pt programs, agreement of the combined label with the two-family adjudication 0.64.

### Re-gate

bench: κ(runtime, AST) 0.82, runtime vs adjudicated 0.60, final label vs adjudicated 0.85; suite: κ 0.75, runtime vs adjudicated 0.50, final vs adjudicated 0.75; flagged tasks ['R1'].

### Verdicts

```
{'E_A1': {'verdict': 'INCONCLUSIVE', 'why': 'criteria neither met nor disconfirmed', 'rho': 0.4206053577821779, 'p': 0.05957470212648937, 'n_units': 15, 'immovable_frac_collapsed': 0.6666666666666666}, 'E_A2': {'verdict': 'PASS', 'n_events': 7, 'hits': 5, 'p': 0.02518518518518519, 'log_score_test': 'decisive'}, 'transplant': {'verdict': 'DOES NOT SUPPORT SUFFICIENCY', 'lambda': 1.0, 'S_T': ['T03', 'T04', 'T06', 'T05', 'T10', 'R6', 'T11'], 'S_C': ['T2', 'T13', 'R1'], 'share_supporting_of_valid': 0.2857142857142857, 'collapsed_controls_within_tol': True, 'rp_within_tol': True}, 'novelty': {'n_correct_other': 56, 'novel_count': 0, 'rule_of_three_upper_95': 0.05357142857142857}, 'status': 'REPLICATION on seen tasks (never a confirmation); Holm across the secondary family is applied by the evaluation step'}
```
