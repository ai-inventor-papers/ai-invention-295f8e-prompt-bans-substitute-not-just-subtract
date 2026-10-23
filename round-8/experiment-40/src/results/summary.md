# Auto-generated result tables (src/digest8.py)

### T10 decision site (Qwen3-8B): teacher-forced (held-out pairs)

L* = 22, k* = 4, held-out recovery at k* = 8.43 (95% two-way cluster CI 5.94 to 11.30); mean DAS Delta 17.37 nats vs full-state 2.06 nats; OFF-MANIFOLD flag: True

| rank | recovery (seed 0) | by class: bfs | by class: dfs | by class: union_find |
|---|---|---|---|---|
| 1 | 7.67 | 15.25 | 4.20 | -0.39 |
| 2 | 8.12 | 15.36 | 4.93 | -0.16 |
| 4 | 8.43 | 15.38 | 5.47 | -0.07 |
| 8 | 9.26 | 15.70 | 6.77 | 0.08 |

| control | statistic | threshold | result |
|---|---|---|---|
| c1 random subspaces (k*) | median -0.005, p95 0.015 | median <= 0.05 | PASS |
| c2 label control pi1 | ratio to true fit 0.87 | <= 0.10 | FAIL |
| c2 label control pi2 | ratio to true fit 0.63 | <= 0.10 | FAIL |
| c2 label control prompt | ratio to true fit 0.77 | <= 0.10 | FAIL |
| c3 random-init network | ratio 0.69 (trained 17.53 vs random-init 12.08 nats) | <= 0.25 | FAIL |
| c4 reverse interchange | -2.72 (16 pairs) | >= 0.5 | FAIL |
| c5 projection on 64 twin PCs | retention 0.18 | >= 0.5 | FAIL |
| c5b (twins + forced + bans basis) | retention 0.19 | >= 0.5 | FAIL |
| c6 natural-variance share | 0.0076 vs random p95 0.0016 | > p95 | PASS |
| c7 seed principal cosine | median first cosine 0.87 (random p99 0.07) | >= 0.5 and > p99 | PASS |

### T10 task band (Qwen3-8B): teacher-forced (held-out pairs)

L* = band, k* = 2, held-out recovery at k* = 0.82 (95% two-way cluster CI 0.48 to 1.16); mean DAS Delta 14.89 nats vs full-state 18.19 nats; OFF-MANIFOLD flag: False

| rank | recovery (seed 0) | by class: bfs | by class: dfs | by class: union_find |
|---|---|---|---|---|
| 1 | 0.76 | 1.47 | 0.63 | -0.04 |
| 2 | 0.82 | 1.57 | 0.68 | -0.04 |
| 4 | 0.86 | 1.58 | 0.77 | -0.03 |
| 8 | 0.88 | 1.57 | 0.84 | -0.03 |

| control | statistic | threshold | result |
|---|---|---|---|
| c1 random subspaces (k*) | median 0.003, p95 0.008 | median <= 0.05 | PASS |
| c2 label control pi1 | ratio to true fit 0.71 | <= 0.10 | FAIL |
| c2 label control pi2 | ratio to true fit 0.79 | <= 0.10 | FAIL |
| c2 label control prompt | ratio to true fit 0.72 | <= 0.10 | FAIL |
| c3 random-init network | ratio 0.18 (trained 14.89 vs random-init 2.71 nats) | <= 0.25 | PASS |
| c4 reverse interchange | 0.77 (16 pairs) | >= 0.5 | PASS |
| c5 projection on 64 twin PCs | retention 0.43 | >= 0.5 | FAIL |
| c5b (twins + forced + bans basis) | retention 0.90 | >= 0.5 | PASS |
| c6 natural-variance share | 0.0030 vs random p95 0.0006 | > p95 | PASS |
| c7 seed principal cosine | median first cosine 0.49 (random p99 0.05) | >= 0.5 and > p99 | FAIL |

### GRID decision site (gemma-3-4b-it): teacher-forced (held-out pairs)

L* = 16, k* = 4, held-out recovery at k* = 3.07 (95% two-way cluster CI 2.85 to 3.41); mean DAS Delta 9.25 nats vs full-state 3.02 nats; OFF-MANIFOLD flag: True

| rank | recovery (seed 0) | by class: bfs |
|---|---|---|
| 1 | 2.21 | 2.21 |
| 2 | 2.72 | 2.72 |
| 4 | 3.07 | 3.07 |
| 8 | 3.25 | 3.25 |

| control | statistic | threshold | result |
|---|---|---|---|
| c1 random subspaces (k*) | median 0.013, p95 0.033 | median <= 0.05 | PASS |
| c2 label control shuffle0 | ratio to true fit 0.11 | <= 0.10 | FAIL |
| c2 label control shuffle1 | ratio to true fit 0.11 | <= 0.10 | FAIL |
| c2 label control shuffle2 | ratio to true fit 0.20 | <= 0.10 | FAIL |
| c3 random-init network | ratio 0.41 (trained 9.10 vs random-init 3.70 nats) | <= 0.25 | FAIL |
| c4 reverse interchange | 2.83 (8 pairs) | >= 0.5 | PASS |
| c5 projection on 64 twin PCs | retention 0.12 | >= 0.5 | FAIL |
| c5b (twins + forced + bans basis) | retention 0.44 | >= 0.5 | FAIL |
| c6 natural-variance share | 0.0014 vs random p95 0.0030 | > p95 | FAIL |
| c7 seed principal cosine | median first cosine 0.53 (random p99 0.09) | >= 0.5 and > p99 | PASS |

### T10 decision site at block 24 (POST HOC sensitivity): teacher-forced (held-out pairs)

L* = 24, k* = 2, held-out recovery at k* = 1.22 (95% two-way cluster CI 0.98 to 1.43); mean DAS Delta 19.82 nats vs full-state 16.24 nats; OFF-MANIFOLD flag: False

| rank | recovery (seed 0) | by class: bfs | by class: dfs | by class: union_find |
|---|---|---|---|---|
| 1 | 1.10 | 1.65 | 0.61 | 0.15 |
| 2 | 1.22 | 1.72 | 0.77 | 0.41 |
| 4 | 1.24 | 1.73 | 0.80 | 0.41 |
| 8 | 1.29 | 1.76 | 0.86 | 0.46 |

| control | statistic | threshold | result |
|---|---|---|---|
| c1 random subspaces (k*) | median 0.000, p95 0.003 | median <= 0.05 | PASS |
| c2 label control pi1 | ratio to true fit 0.61 | <= 0.10 | FAIL |
| c2 label control pi2 | ratio to true fit 0.57 | <= 0.10 | FAIL |
| c2 label control prompt | ratio to true fit 0.50 | <= 0.10 | FAIL |
| c3 random-init network | not run | <= 0.25 | n/a |
| c4 reverse interchange | 1.17 (16 pairs) | >= 0.5 | PASS |
| c5 projection on 64 twin PCs | retention 0.52 | >= 0.5 | PASS |
| c5b (twins + forced + bans basis) | retention 0.74 | >= 0.5 | PASS |
| c6 natural-variance share | 0.0075 vs random p95 0.0010 | > p95 | PASS |
| c7 seed principal cosine | median first cosine 0.62 (random p99 0.05) | >= 0.5 and > p99 | PASS |

### T10_dec: generation (CRN slots; correct = target-class label AND hidden tests pass)

Target class **bfs**: generation recovery n/a, pass ratio DAS/BASE 0.24, McNemar DAS vs RAND {'a_only': 5, 'b_only': 0, 'p_two_sided': 0.0625, 'p_one_sided_a_gt_b': 0.03125}

| arm | n | correct target | attempted target | pass rate | labels |
|---|---|---|---|---|---|
| BASE | 30 | 0 | 0 | 0.83 | {'union_find': 28, 'dfs': 2} |
| FULL | 30 | 0 | 0 | 0.77 | {'union_find': 29, 'dfs': 1} |
| DAS | 30 | 5 | 29 | 0.20 | {'bfs': 29, 'dfs': 1} |
| RAND | 30 | 0 | 0 | 0.83 | {'union_find': 28, 'dfs': 2} |
| PERM | 20 | 0 | 0 | 1.00 | {'dfs': 20} |
| REV-DAS | 20 | 12 | 18 | 0.70 | {'bfs': 18, 'dfs': 2} |
| REV-FULL | 20 | 13 | 20 | 0.65 | {'bfs': 20} |
| SRC | 20 | 14 | 20 | 0.70 | {'bfs': 20} |

Reverse (restored twin-class programs): {'restored_SRC': 0, 'restored_REV_DAS': 0, 'restored_REV_FULL': 0, 'gen_c4': None}

Target class **dfs**: generation recovery 14.50, pass ratio DAS/BASE 1.20, McNemar DAS vs RAND {'a_only': 29, 'b_only': 0, 'p_two_sided': 3.725290298461914e-09, 'p_one_sided_a_gt_b': 1.862645149230957e-09}

| arm | n | correct target | attempted target | pass rate | labels |
|---|---|---|---|---|---|
| BASE | 30 | 0 | 0 | 0.83 | {'union_find': 30} |
| FULL | 30 | 2 | 2 | 0.73 | {'union_find': 28, 'dfs': 2} |
| DAS | 30 | 29 | 29 | 1.00 | {'dfs': 29, 'union_find': 1} |
| RAND | 30 | 0 | 0 | 0.80 | {'union_find': 30} |
| PERM | 20 | 20 | 20 | 1.00 | {'dfs': 20} |
| REV-DAS | 20 | 20 | 20 | 1.00 | {'dfs': 20} |
| REV-FULL | 20 | 20 | 20 | 1.00 | {'dfs': 20} |
| SRC | 20 | 20 | 20 | 1.00 | {'dfs': 20} |
| DAS_k1 | 30 | 25 | 25 | 0.90 | {'bfs': 3, 'dfs': 25, 'union_find': 2} |
| DAS_k2 | 30 | 29 | 29 | 1.00 | {'dfs': 29, 'union_find': 1} |

Reverse (restored twin-class programs): {'restored_SRC': 0, 'restored_REV_DAS': 0, 'restored_REV_FULL': 0, 'gen_c4': None}

### T10_band: generation (CRN slots; correct = target-class label AND hidden tests pass)

Target class **bfs**: generation recovery 1.22, pass ratio DAS/BASE 0.93, McNemar DAS vs RAND {'a_only': 28, 'b_only': 0, 'p_two_sided': 7.450580596923828e-09, 'p_one_sided_a_gt_b': 3.725290298461914e-09}

| arm | n | correct target | attempted target | pass rate | labels |
|---|---|---|---|---|---|
| BASE | 30 | 0 | 0 | 1.00 | {'union_find': 30} |
| FULL | 30 | 23 | 23 | 1.00 | {'bfs': 23, 'dfs': 7} |
| DAS | 30 | 28 | 30 | 0.93 | {'bfs': 30} |
| RAND | 30 | 0 | 0 | 1.00 | {'union_find': 30} |
| PERM | 20 | 3 | 3 | 1.00 | {'bfs': 3, 'dfs': 16, 'union_find': 1} |
| REV-DAS | 20 | 20 | 20 | 1.00 | {'bfs': 20} |
| REV-FULL | 20 | 20 | 20 | 1.00 | {'bfs': 20} |
| SRC | 20 | 20 | 20 | 1.00 | {'bfs': 20} |

Reverse (restored twin-class programs): {'restored_SRC': 0, 'restored_REV_DAS': 0, 'restored_REV_FULL': 0, 'gen_c4': None}

Target class **dfs**: generation recovery 0.15, pass ratio DAS/BASE 0.70, McNemar DAS vs RAND {'a_only': 3, 'b_only': 0, 'p_two_sided': 0.25, 'p_one_sided_a_gt_b': 0.125}

| arm | n | correct target | attempted target | pass rate | labels |
|---|---|---|---|---|---|
| BASE | 30 | 0 | 0 | 1.00 | {'union_find': 30} |
| FULL | 30 | 20 | 29 | 0.70 | {'dfs': 29, 'bfs': 1} |
| DAS | 30 | 3 | 3 | 0.70 | {'bfs': 24, 'union_find': 3, 'dfs': 3} |
| RAND | 30 | 0 | 0 | 1.00 | {'union_find': 30} |
| PERM | 20 | 17 | 17 | 1.00 | {'dfs': 17, 'union_find': 3} |
| REV-DAS | 20 | 19 | 20 | 0.95 | {'dfs': 20} |
| REV-FULL | 20 | 20 | 20 | 1.00 | {'dfs': 20} |
| SRC | 20 | 13 | 20 | 0.65 | {'dfs': 20} |
| DAS_k1 | 30 | 5 | 5 | 0.73 | {'bfs': 19, 'dfs': 5, 'union_find': 6} |
| DAS_k4 | 30 | 4 | 4 | 0.73 | {'bfs': 25, 'dfs': 4, 'union_find': 1} |

Reverse (restored twin-class programs): {'restored_SRC': 0, 'restored_REV_DAS': 0, 'restored_REV_FULL': 0, 'gen_c4': None}

### GRID_dec: generation (CRN slots; correct = target-class label AND hidden tests pass)

Target class **bfs**: generation recovery 4.00, pass ratio DAS/BASE 0.81, McNemar DAS vs RAND {'a_only': 17, 'b_only': 0, 'p_two_sided': 1.52587890625e-05, 'p_one_sided_a_gt_b': 7.62939453125e-06}

| arm | n | correct target | attempted target | pass rate | labels |
|---|---|---|---|---|---|
| BASE | 30 | 6 | 8 | 0.90 | {'dfs': 21, 'bfs': 8, 'disputed': 1} |
| FULL | 30 | 10 | 24 | 0.43 | {'bfs': 24, 'disputed': 3, 'dfs': 3} |
| DAS | 30 | 22 | 27 | 0.73 | {'bfs': 27, 'disputed': 3} |
| RAND | 30 | 5 | 7 | 0.87 | {'disputed': 2, 'bfs': 7, 'dfs': 21} |
| PERM | 20 | 10 | 12 | 0.85 | {'bfs': 12, 'disputed': 1, 'dfs': 7} |
| REV-DAS | 20 | 0 | 19 | 0.00 | {'bfs': 19, 'disputed': 1} |
| REV-FULL | 20 | 0 | 20 | 0.00 | {'bfs': 20} |
| SRC | 20 | 1 | 20 | 0.05 | {'bfs': 20} |
| DAS_k1 | 30 | 22 | 27 | 0.73 | {'bfs': 27, 'disputed': 3} |
| DAS_k2 | 30 | 21 | 25 | 0.70 | {'bfs': 25, 'disputed': 5} |

Reverse (restored twin-class programs): {'restored_SRC': 0, 'restored_REV_DAS': 0, 'restored_REV_FULL': 0, 'gen_c4': None}

## Verdicts

| unit-site | verdict | V0 | failed controls | untested |
|---|---|---|---|---|
| T10-dec | NO HANDLE | FAIL | {'c2': 'map-class capacity', 'c3': 'map-class capacity', 'c4': 'dormant/off-manifold', 'c5': 'dormant/off-manifold'} | [] |
| T10-band | SUFFICIENT HANDLE | PASS | {'c2': 'map-class capacity', 'c5': 'dormant/off-manifold', 'c7': 'unstable across seeds'} | [] |
| GRID-dec | SUFFICIENT HANDLE | PASS | {'c2': 'map-class capacity', 'c3': 'map-class capacity', 'c5': 'dormant/off-manifold', 'c6': 'dormant/off-manifold'} | [] |
| T10-dec_L24_posthoc | POST HOC, TF-only (no generation): controls failed ['c2', 'c3'], untested [] | FAIL | {'c2': 'map-class capacity', 'c3': 'map-class capacity'} | [] |

K2: **DISCONFIRMED**, p_K2 = 0.0370

## Mediation (T10)

```
{'escapes_PUSH': 221, 'n_PUSH': 276, 'clamp_TASK': {'n_pairs': 270, 'escapes_push': 218, 'escapes_clamp': 221, 'removal': -0.013761467889908285, 'mcnemar_push_vs_clamp': {'a_only': 8, 'b_only': 11, 'p_two_sided': 0.6476058959960938, 'p_one_sided_a_gt_b': 0.8203582763671875}, 'pass_rate_clamp': 0.8703703703703703}, 'clamp_RAND': {'n_pairs': 270, 'escapes_push': 218, 'escapes_clamp': 213, 'removal': 0.022935779816513735, 'mcnemar_push_vs_clamp': {'a_only': 8, 'b_only': 3, 'p_two_sided': 0.2265625, 'p_one_sided_a_gt_b': 0.11328125}, 'pass_rate_clamp': 0.8222222222222222}, 'clamp_DEC': {'n_reached': 53, 'reach_rate': 0.53, 'escapes_push_reached': 44, 'escapes_clamp': 46, 'removal': -0.045454545454545414, 'mcnemar': {'a_only': 1, 'b_only': 3, 'p_two_sided': 0.625, 'p_one_sided_a_gt_b': 0.9375}}, 'not_estimable': False, 'clamp_pass': False, 'prospective': {'n_directions': 24, 'spearman': {'rho': 0.0926190114495629, 'p_one_sided': 0.32886711328867113, 'n': 24}, 'mean_escape': 0.3604166666666666}, 'retrospective': {'spearman_escape_pooled': {'rho': 0.39147708195720493, 'p_one_sided': 0.006099390060993901, 'n': 40}, 'spearman_escape_d': {'rho': 0.36136948694511073, 'p_one_sided': 0.0110988901109889, 'n': 40}, 'spearman_escape_c': {'rho': 0.3868820567844952, 'p_one_sided': 0.007099290070992901, 'n': 40}, 'partial_spearman_ctrl_normD_band': 0.41787320850946064, 'partial_spearman_ctrl_normD_block35': 0.39288328968788966, 'spearman_pi_bfs': {'rho': 0.40685687572896295, 'p_one_sided': 0.005997001499250375, 'n': 40}, 'spearman_pi_dfs': {'rho': 0.3685489231440931, 'p_one_sided': 0.01199400299850075, 'n': 40}, 'placebo_random_predictor': {'rho': 0.13907862588694142, 'p_one_sided': 0.20189905047476261, 'n': 40}}}
```