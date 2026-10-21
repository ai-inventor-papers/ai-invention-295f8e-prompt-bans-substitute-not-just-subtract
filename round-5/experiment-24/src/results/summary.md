### Base repertoire and strata (COMMIT #1)

| Task | instruct default (twin S1 share) | base correct / N | beta_t [95% CI] (basis) | stratum (stability) | r_t | beta plain | base Hill-1 (d25) |
|---|---|---|---|---|---|---|---|
| T03 | full_sort (1.00) | 47/100 | 0.43 [0.33, 0.49] (CORRECT) | BASE-DIVERSE (1.00) | quickselect | 0.10 | 3.03 |
| T2 | dijkstra (1.00) | 44/200 | 0.41 [0.33, 0.55] (CORRECT) | BASE-DIVERSE (1.00) | bf_spfa | 0.32 | 2.12 |
| T05 | hash_map (1.00) | 49/100 | 0.16 [0.12, 0.21] (CORRECT) | INTERMEDIATE (0.92) | brute_force | 0.69 | 1.63 |
| T10 | union_find (1.00) | 55/200 | 0.65 [0.58, 0.76] (CORRECT) | BASE-DIVERSE (1.00) | dfs | 0.81 | 2.34 |
| T06 | hash_set (1.00) | 51/100 | 0.20 [0.10, 0.29] (CORRECT) | INTERMEDIATE (0.55) | index_marking | 0.33 | 2.34 |
| T1 | bfs (1.00) | 14/200 | 0.38 [0.32, 0.44] (ATTEMPT) | BASE-DIVERSE (1.00) | dfs | 0.21 | 1.82 |
| T04 | naive (1.00) | 52/100 | 0.12 [0.05, 0.16] (CORRECT) | INTERMEDIATE (0.99) | builtin | 0.27 | 1.42 |
| T08 | iteration (1.00) | 37/100 | 0.16 [0.09, 0.22] (CORRECT) | INTERMEDIATE (0.90) | memo_recursion | 0.08 | 1.55 |
| T11 | quadratic_dp (1.00) | 43/100 | 0.09 [0.05, 0.12] (CORRECT) | INTERMEDIATE (0.99) | patience_bisect | 0.00 | 1.36 |
| T13 | sort_sweep (1.00) | 40/100 | 0.00 [0.00, 0.00] (CORRECT) | BASE-COLLAPSED (1.00) | None | 0.00 | 1.00 |
| T14 | sort_by_count (1.00) | 31/100 | 0.35 [0.26, 0.41] (CORRECT) | BASE-DIVERSE (1.00) | heap | 0.07 | 1.91 |
| R1 | greedy_end (1.00) | 42/200 | 0.00 [0.00, 0.00] (CORRECT) | BASE-COLLAPSED (1.00) | None | 0.06 | 1.00 |
| R3 | kahn (1.00) | 40/100 | 0.03 [0.00, 0.07] (CORRECT) | BASE-COLLAPSED (0.88) | dfs_postorder | 0.39 | 1.12 |
| R6 | binary_search (0.96) | 40/100 | 0.05 [0.00, 0.12] (CORRECT) | INTERMEDIATE (0.53) | bisect_module | 0.00 | 2.17 |
| R2 | dfs_parent (1.00) | 43/200 | 0.16 [0.07, 0.23] (CORRECT) | INTERMEDIATE (0.80) | union_find | 0.15 | 1.63 |

### Stage 3 selection on S1 (pass / correct off-default share; N = 50 for T, 30 for MR and READ)

| Task | stratum | twin | T(0.25) | T(0.5) | T(1) | MR(0.25) | MR(0.5) | MR(1) | READ(1) | EARLY(1) | LATE(1) | lambda* |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| T03 | BASE-DIVERSE | 1.00 / 0.00 | 1.00 / 0.02 | 1.00 / 0.00 | 1.00 / 0.06 | 1.00 / 0.10 | 1.00 / 0.07 | 0.97 / 0.34 | 0.97 / 0.00 | 1.00 / 0.30 | 1.00 / 0.04 | 1.00 |
| T2 | BASE-DIVERSE | 0.98 / 0.00 | 1.00 / 0.00 | 0.72 / 0.06 | 0.54 / 0.04 | 0.97 / 0.03 | 0.93 / 0.07 | 0.90 / 0.00 | 0.00 / – | 0.98 / 0.00 | 0.88 / 0.02 | 0.25 |
| T05 | INTERMEDIATE | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.03 | 0.43 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 | 0.25 |
| T10 | BASE-DIVERSE | 1.00 / 0.00 | 1.00 / 0.04 | 1.00 / 0.12 | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.03 | 1.00 / 0.10 | 0.17 / 0.20 | 1.00 / 0.28 | 1.00 / 0.00 | 0.50 |
| T06 | INTERMEDIATE | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.17 | 0.37 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 | 0.25 |
| T1 | BASE-DIVERSE | 0.86 / 0.00 | 0.72 / 0.00 | 0.50 / 0.00 | 0.30 / 0.00 | 0.87 / 0.04 | 0.77 / 0.00 | 0.73 / 0.09 | 0.13 / 0.00 | 0.40 / 0.00 | 0.90 / 0.00 | 0.25 |
| T04 | INTERMEDIATE | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 | 0.25 |
| T08 | INTERMEDIATE | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 | 0.97 / 0.00 | 0.90 / 0.00 | 0.37 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 | 0.25 |
| T11 | INTERMEDIATE | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 | 0.93 / 0.04 | 0.53 / 0.06 | 1.00 / 0.00 | 1.00 / 0.00 | 0.25 |
| T13 | BASE-COLLAPSED | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 | – | – | – | 0.37 / 0.00 | – | – | – |
| T14 | BASE-DIVERSE | 0.78 / 0.00 | 0.78 / 0.00 | 0.68 / 0.00 | 0.98 / 0.47 | 0.77 / 0.00 | 0.80 / 0.08 | 0.53 / 0.19 | 0.07 / 0.00 | 0.98 / 0.00 | 0.72 / 0.00 | 1.00 |
| R1 | BASE-COLLAPSED | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 | 0.40 / 0.00 | – | – | – | 0.30 / 0.00 | – | – | – |
| R3 | BASE-COLLAPSED | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 | – | – | – | 0.13 / 0.00 | – | – | – |
| R6 | INTERMEDIATE | 0.90 / 0.00 | 0.88 / 0.00 | 0.90 / 0.00 | 0.64 / 0.00 | 0.83 / 0.00 | 0.80 / 0.00 | 0.87 / 0.00 | 0.23 / 0.00 | 0.96 / 0.00 | 0.94 / 0.00 | 0.25 |
| R2 | INTERMEDIATE | 0.94 / 0.00 | 0.98 / 0.00 | 0.98 / 0.00 | 0.90 / 0.00 | 0.90 / 0.00 | 0.77 / 0.00 | 0.43 / 0.15 | 0.17 / 0.00 | 1.00 / 0.00 | 0.96 / 0.00 | 0.25 |

### Stage 4 confirmation on fresh S2 slots (N = 50 per cell; one-sided exact McNemar on y, Holm)

| Task | lambda* | twin S2 pass | T: pass / off-share / modal | control: pass / off-share | McNemar b:c, p (Holm) | templates T > control |
|---|---|---|---|---|---|---|
| T03 | 1.00 | 1.00 | 1.00 / 0.06 / size_k_heap | MR1.0: 1.00 / 0.42 | 2:20, 1 (1) | 0/5 |
| T03 | 1.00 | 1.00 | 1.00 / 0.06 / size_k_heap | XT1.0: 1.00 / 0.00 | 3:0, 0.12 (1) | 2/5 |
| T2 | 0.25 | 1.00 | 1.00 / 0.00 / None | MR0.25: 0.98 / 0.00 | 0:0, 1 (1) | 0/5 |
| T2 | 0.25 | 1.00 | 1.00 / 0.00 / None | XT0.25: 0.98 / 0.00 | 0:0, 1 (1) | 0/5 |
| T10 | 0.50 | 1.00 | 1.00 / 0.08 / dfs | MR0.5: 1.00 / 0.02 | 3:0, 0.12 (1) | 3/5 |
| T10 | 0.50 | 1.00 | 1.00 / 0.08 / dfs | XT0.5: 1.00 / 0.02 | 3:0, 0.12 (1) | 3/5 |
| T1 | 0.25 | 0.88 | 0.76 / 0.00 / None | MR0.25: 0.94 / 0.00 | 0:0, 1 (1) | 0/5 |
| T1 | 0.25 | 0.88 | 0.76 / 0.00 / None | XT0.25: 0.86 / 0.00 | 0:0, 1 (1) | 0/5 |
| T14 | 1.00 | 0.78 | 0.98 / 0.43 / heap | MR1.0: 0.78 / 0.05 | 19:0, 1.9e-06 (1.9e-05) | 5/5 |
| T14 | 1.00 | 0.78 | 0.98 / 0.43 / heap | XT1.0: 0.88 / 0.11 | 17:1, 7.2e-05 (6.5e-04) | 5/5 |
| T14 | 1.00 | 0.78 | 0.98 / 0.43 / heap | MRP0.5: 0.76 / 0.00 | 21:0, 4.8e-07 (5.2e-06) | 5/5 |
| T05 (desc.) | 0.25 | 1.00 | 1.00 / 0.00 / None | MR0.25: 1.00 / 0.00 | 0:0, 1 (–) | 0/5 |
| T05 (desc.) | 0.25 | 1.00 | 1.00 / 0.00 / None | XT0.25: 1.00 / 0.00 | 0:0, 1 (–) | 0/5 |
| T06 (desc.) | 0.25 | 1.00 | 1.00 / 0.00 / None | MR0.25: 1.00 / 0.00 | 0:0, 1 (–) | 0/5 |
| T06 (desc.) | 0.25 | 1.00 | 1.00 / 0.00 / None | XT0.25: 1.00 / 0.00 | 0:0, 1 (–) | 0/5 |
| T04 (desc.) | 0.25 | 1.00 | 1.00 / 0.00 / None | MR0.25: 1.00 / 0.00 | 0:0, 1 (–) | 0/5 |
| T04 (desc.) | 0.25 | 1.00 | 1.00 / 0.00 / None | XT0.25: 1.00 / 0.00 | 0:0, 1 (–) | 0/5 |
| T08 (desc.) | 0.25 | 1.00 | 1.00 / 0.00 / None | MR0.25: 1.00 / 0.00 | 0:0, 1 (–) | 0/5 |
| T08 (desc.) | 0.25 | 1.00 | 1.00 / 0.00 / None | XT0.25: 1.00 / 0.00 | 0:0, 1 (–) | 0/5 |
| T11 (desc.) | 0.25 | 1.00 | 1.00 / 0.00 / None | MR0.25: 1.00 / 0.00 | 0:0, 1 (–) | 0/5 |
| T11 (desc.) | 0.25 | 1.00 | 1.00 / 0.00 / None | XT0.25: 1.00 / 0.00 | 0:0, 1 (–) | 0/5 |
| R6 (desc.) | 0.25 | 0.76 | 0.78 / 0.00 / None | MR0.25: 0.80 / 0.00 | 0:0, 1 (–) | 0/5 |
| R6 (desc.) | 0.25 | 0.76 | 0.78 / 0.00 / None | XT0.25: 0.56 / 0.00 | 0:0, 1 (–) | 0/5 |
| R2 (desc.) | 0.25 | 0.84 | 0.90 / 0.00 / None | MR0.25: 0.80 / 0.00 | 0:0, 1 (–) | 0/5 |
| R2 (desc.) | 0.25 | 0.84 | 0.90 / 0.00 / None | XT0.25: 0.86 / 0.00 | 0:0, 1 (–) | 0/5 |

**Claim B (frozen rule): DISCONFIRMED** -- PASS on 1/5 decisive tasks (needed 4); (iii) fails on 4; specificity (point estimates) no, noise-robust yes.

- T03: (i) pass yes, (ii) share >= 0.5 beta no, (iii) controls no, (iv) lands on r_t no -> PASS no
- T2: (i) pass yes, (ii) share >= 0.5 beta no, (iii) controls no, (iv) lands on r_t no -> PASS no
- T10: (i) pass yes, (ii) share >= 0.5 beta no, (iii) controls no, (iv) lands on r_t yes -> PASS no
- T1: (i) pass yes, (ii) share >= 0.5 beta no, (iii) controls no, (iv) lands on r_t no -> PASS no
- T14: (i) pass yes, (ii) share >= 0.5 beta yes, (iii) controls yes, (iv) lands on r_t yes -> PASS yes

Power extension (COMMIT3_EXT, outcome-blind, descriptive; N = 100 per decisive cell): **PARTIAL** (PASS 1/5).
- T03: T pass 1.00, off-share 0.06; vs MR1.0 4:36 p=1; vs XT1.0 6:0 p=0.016
- T2: T pass 1.00, off-share 0.00; vs MR0.25 0:0 p=1; vs XT0.25 0:0 p=1
- T10: T pass 1.00, off-share 0.08; vs MR0.5 6:2 p=0.14; vs XT0.5 7:0 p=0.0078
- T1: T pass 0.68, off-share 0.00; vs MR0.25 0:0 p=1; vs XT0.25 0:0 p=1
- T14: T pass 0.99, off-share 0.49; vs MR1.0 44:0 p=5.7e-14; vs XT1.0 35:3 p=3.3e-08; vs MRP0.5 49:0 p=1.8e-15

Sensitivities: stable_stratum_only: DISCONFIRMED; noise_robust_specificity: DISCONFIRMED; power_extension_N100_verdict: PARTIAL

### Claim D (de-sharpening push along unit(D) vs isotropic, ban-free units, N = 30)

| Task | twin pass | DS 0.5 / 1 / 2 (pass, off-share) | ISO 0.5 / 1 / 2 (pass, off-share) | a_DS | a_ISO |
|---|---|---|---|---|---|
| T03 | 1.00 | 1.00, 0.00 ; 1.00, 0.00 ; 1.00, 0.00 | 1.00, 0.00 ; 1.00, 0.13 ; 1.00, 0.27 | – | 2.00 |
| T2 | 1.00 | 1.00, 0.00 ; 1.00, 0.00 ; 0.97, 0.03 | 1.00, 0.00 ; 1.00, 0.00 ; 0.90, 0.07 | – | >2 (censored) |
| T10 | 1.00 | 1.00, 0.03 ; 1.00, 0.03 ; 0.93, 0.11 | 1.00, 0.03 ; 1.00, 0.03 ; 1.00, 0.10 | – | >2 (censored) |
| T1 | 0.87 | 0.87, 0.00 ; 0.77, 0.00 ; 0.60, 0.00 | 0.93, 0.00 ; 0.70, 0.00 ; 0.77, 0.00 | – | >2 (censored) |

**Claim D: DISCONFIRMED** (PASS 0/4).

### Reverse interchange (instruct task-spec states into the base model, blocks 12-23, N = 50)

| Task | BTWIN default share (correct / attempts) | RT(1) | BMR(1) | predicted min rise | met |
|---|---|---|---|---|---|
| T10 | 0.50 / 0.38 (n_correct 18) | 0.53 / 0.55 (n_correct 19) | 0.50 / 0.36 (n_correct 16) | 0.25 | no |
| T03 | 0.65 / 0.55 (n_correct 20) | 0.74 / 0.66 (n_correct 31) | 0.56 / 0.39 (n_correct 16) | 0.17 | no |
| T2 | 0.87 / 0.63 (n_correct 15) | 0.80 / 0.74 (n_correct 20) | 0.50 / 0.41 (n_correct 6) | 0.07 | no |
| T1 | 0.80 / 0.39 (n_correct 5) | 1.00 / 0.73 (n_correct 11) | 1.00 / 0.50 (n_correct 2) | 0.10 | yes |

### Claim A screen check (descriptive; iteration-4 escape fractions)

- beta_t vs E_t (alpha_1.0): Spearman 0.78, Kendall 0.69, one-sided permutation p 2.0e-04 (n = 15)
- beta_t vs E_t (alpha_2.0): Spearman 0.79, Kendall 0.70, one-sided permutation p 4.0e-04 (n = 15)
- beta_t vs E_t (alpha_mean): Spearman 0.79, Kendall 0.71, one-sided permutation p 4.0e-04 (n = 15)
- r_t equals the iteration-4 push top-1 landing on 5/5 movable tasks

### Size of D = h_base - h_instruct

- relative norm at S, blocks 12-23 (mean over tasks): 0.39, 0.41, 0.42, 0.44, 0.44, 0.46, 0.48, 0.49, 0.51, 0.53, 0.53, 0.52
- relative norm at R, blocks 12-23: 1.06, 1.08, 1.09, 1.07, 1.06, 1.06, 0.99, 1.10, 1.07, 1.09, 1.11, 1.12
- share of hooked (l, p) above 4 ban-free units: lambda 0.25 0.00, 0.5 0.01, 1 0.71
- cross-task cosine of the per-task mean D (blocks 12/18/23/27): 12: 0.88, 18: 0.76, 23: 0.81, 27: 0.80

### Engine check (bf16 here vs the FP8 exp17 screen rows)

- T03|EC_NEUTRAL: per-slot label agreement 1.00, JS 0.000 (template-resampling null q95 0.000), within null yes
- T03|EC_RAND9002_a1.0: per-slot label agreement 0.74, JS 0.030 (template-resampling null q95 0.075), within null yes
- T2|EC_NEUTRAL: per-slot label agreement 0.98, JS 0.010 (template-resampling null q95 0.000), within null no
- T2|EC_RAND9004_a1.0: per-slot label agreement 0.88, JS 0.005 (template-resampling null q95 0.005), within null yes

### Geometry (distance of the T(lambda*) centroid; fraction of the instruct->base twin gap)

- T03 (lambda* 1.0): S18 1.00 (stress-1 0.25); S23 1.00 (stress-1 0.25); S27 0.88 (stress-1 0.22); R18 0.18 (stress-1 0.06); R23 0.30 (stress-1 0.08)
- T2 (lambda* 0.25): S18 0.25 (stress-1 0.17); S23 0.25 (stress-1 0.22); S27 0.23 (stress-1 0.21); R18 0.05 (stress-1 0.05); R23 0.07 (stress-1 0.08)
- T10 (lambda* 0.5): S18 0.50 (stress-1 0.27); S23 0.50 (stress-1 0.27); S27 0.47 (stress-1 0.23); R18 0.09 (stress-1 0.06); R23 0.15 (stress-1 0.08)
- T1 (lambda* 0.25): S18 0.25 (stress-1 0.27); S23 0.25 (stress-1 0.26); S27 0.24 (stress-1 0.23); R18 0.05 (stress-1 0.06); R23 0.07 (stress-1 0.08)
- T14 (lambda* 1.0): S18 1.00 (stress-1 0.06); S23 1.00 (stress-1 0.06); S27 0.89 (stress-1 0.08); R18 0.18 (stress-1 0.05); R23 0.31 (stress-1 0.06)

### Novelty audit

48 unique correct non-catalogue programs (every arm, base included). Judge classes (2 of 3 judges): {'NOVEL_ALGORITHM': 14, 'DISAGREE': 10, 'DEGENERATE': 14, 'CATALOGUE_VARIANT': 10}. Manual adjudication against the nearest known solution: {'KNOWN, OUTSIDE THE CATALOGUE': 27, 'DEGENERATE': 12, 'CATALOGUE VARIANT': 9}; NOVEL = 0 (rule-of-three 95% upper bound 0.062); the judges' 14 NOVEL calls are linear scans, count loops and a threshold binary search (known techniques outside the frozen catalogue).

### Re-derivation

56 checks, 0 mismatches; arm-shuffle placebo rejection 0.012; label-shuffle placebo share keeping stratum 0.27

### Compute and spend

HF engine 10860 programs (+1420 pad rows) in 1.51 GPU-h; vLLM base 3500 programs in 0.20 GPU-h; total 1.70 GPU-h. OpenRouter USD 0.287 (cap 1.5).
