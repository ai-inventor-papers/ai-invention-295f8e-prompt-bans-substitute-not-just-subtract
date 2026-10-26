### Labeller re-check (`results/labeller_recheck.json`)

Combined label vs adjudicated gold: **0.965** (n=141; evaluation split 0.966, exp1 reported 0.966); references 22/22 (runtime 20, AST 22).

### Forced programs (`results/yields.json`, `data/forced_selected.jsonl`)

| task | algorithm | family | attempts | labelled j | yield y_j | verified after scrub | scrub mode |
|---|---|---|---|---|---|---|---|
| t1 | bfs | plain | 40 | 40 | 1.00 | 40 | full |
| t1 | dfs | plain | 40 | 40 | 1.00 | 40 | full |
| t1 | bibfs | plain | 120 | 30 | 0.25 | 30 | full |
| t1 | iddfs | plain | 40 | 40 | 1.00 | 40 | full |
| t1 | astar_gbfs | plain | 90 | 32 | 0.36 | 32 | full |
| t1 | dijkstra | desc | 120 | 92 | 0.77 | 92 | full |
| t2 | dijkstra | plain | 40 | 40 | 1.00 | 40 | full |
| t2 | bf_spfa | plain | 40 | 40 | 1.00 | 40 | full |
| t2 | bidijkstra | desc | 120 | 14 | 0.12 | 11 | comment_only |
| t2 | floyd | plain | 40 | 40 | 1.00 | 35 | full |
| t2 | dial | desc | 120 | 106 | 0.88 | 106 | full |

Scored programs per algorithm: M = 20 (cut rule; halves of 10); bidirectional Dijkstra has 11.

### FRLP validity gate (`results/gate.json`)

Verdict: **FAIL (FRLP descriptive)**. (a) calibration: mean S = 1.02 (target [0.3, 3]), mean default-mode share m = 0.83 (target >= 0.9) -> FAIL; (b) mean d_e = 0.92 nats over uniform (target >= 0.3) -> PASS; (c) argmax hits 16/19 clear-mode events = 0.84 (target >= 0.8) -> PASS. Pooled Spearman implied vs realised 0.74; 298/303 gate cells have ESS < 5.

| event | realised mode (allowed) | FRLP argmax | hit | d_e (nats) | implied shares > 0.01 |
|---|---|---|---|---|---|
| t1|baseline | bfs | bfs | yes | 1.31 | bfs 0.66, dfs 0.34 |
| t1|ban:bfs | dfs | dfs | yes | 1.57 | dfs 1.00 |
| t1|mention:bfs | bfs | bfs | yes | 1.75 | bfs 1.00 |
| t1|mention:dfs | dfs | dfs | yes | 1.74 | dfs 1.00 |
| t1|mention:bibfs | bfs | bibfs | no | -1.83 | bibfs 1.00 |
| t1|mention:iddfs | iddfs | iddfs | yes | 1.12 | iddfs 1.00 |
| t1|mention:astar_gbfs | astar_gbfs | bfs | no | -1.75 | bfs 0.78, astar_gbfs 0.22 |
| t1|mention:dijkstra | bfs | bfs | yes | 1.64 | bfs 0.90, dfs 0.10 |
| t1|listall | bfs | bfs | yes | 1.37 | bfs 0.76, dfs 0.24 |
| t1|ban:iddfs | bfs | dfs | no | -2.42 | dfs 0.99, bfs 0.01 |
| t2|baseline | dijkstra | dijkstra | yes | 1.57 | dijkstra 1.00 |
| t2|ban:dijkstra | bf_spfa | bf_spfa | yes | 1.35 | bf_spfa 1.00 |
| t2|mention:dijkstra | dijkstra | dijkstra | yes | 1.57 | dijkstra 1.00 |
| t2|mention:bf_spfa | bf_spfa | bf_spfa | yes | 1.57 | bf_spfa 1.00 |
| t2|mention:bidijkstra | dijkstra | dijkstra | yes | 1.57 | dijkstra 1.00 |
| t2|mention:floyd | floyd | floyd | yes | 1.57 | floyd 1.00 |
| t2|mention:dial | dijkstra | dijkstra | yes | 1.57 | dijkstra 1.00 |
| t2|listall | dijkstra | dijkstra | yes | 1.57 | dijkstra 1.00 |
| t2|ban:floyd | dijkstra | dijkstra | yes | 0.64 | dijkstra 0.98, bf_spfa 0.02 |

Gate (a) per baseline paraphrase: t1 p0: S=1.55, m=0.70; t1 p1: S=2.56, m=0.44; t1 p2: S=1.23, m=0.84; t2 p0: S=0.20, m=1.00; t2 p1: S=0.36, m=1.00; t2 p2: S=0.20, m=1.00

Sensitivity variants (descriptive; the primary verdict is not re-chosen):

| variant | mean S | mean m | (a) | mean d_e | (b) | argmax rate | (c) | all |
|---|---|---|---|---|---|---|---|---|
| code_body_only | 1.02 | 0.83 | no | 0.92 | yes | 0.84 | yes | no |
| correct_only | 0.66 | 1.00 | yes | 0.76 | yes | 0.79 | no | no |
| single_proposal | 0.99 | 0.94 | yes | 0.99 | yes | 0.84 | yes | yes |
| truncated_256 | 1.06 | 0.88 | no | 0.92 | yes | 0.84 | yes | no |
| unscrubbed | 0.95 | 1.00 | yes | 1.18 | yes | 0.89 | yes | yes |
| unscrubbed_body_single | 1.01 | 1.00 | yes | 1.11 | yes | 0.89 | yes | yes |

### C1 output-space share test (`results/c1.json`)

Status: **descriptive: FRLP gate failed**; two tasks, one model, so every branch label is descriptive.

| reference | scope | rows | V_u (ladder) | V_s (X-specific) | SHARE point | SHARE 95% CI | V_u+V_s 95% CI | F | branch |
|---|---|---|---|---|---|---|---|---|---|
| neutral twin (primary) | t1 | 6 | 239.28 | 412.46 | 0.63 | [0.28, 0.83] | [501.86, 1505.29] | 15.91 | UNDETERMINED |
| neutral twin (primary) | t2 | 5 | 244.64 | 173.12 | 0.41 | [0.10, 0.61] | [316.25, 947.02] | 22.48 | UNDETERMINED |
| neutral twin (primary) | pooled | 11 | 483.93 | 585.58 | 0.55 | [0.25, 0.67] | [924.80, 2106.68] | 17.93 | UNDETERMINED |
| mention twin | t1 | 6 | 1282.94 | 2525.02 | 0.66 | [0.51, 0.98] | [2573.47, 5471.38] | 57.44 | X-SPECIFIC-UNAIMED |
| mention twin | t2 | 5 | 522.29 | 979.57 | 0.65 | [0.26, 0.79] | [1182.96, 2115.91] | 37.69 | UNDETERMINED |
| mention twin | pooled | 11 | 1805.23 | 3504.59 | 0.66 | [0.49, 0.87] | [4045.59, 7138.92] | 49.98 | UNDETERMINED |
| ESS-weighted | t1 | 6 | -35.45 | 181.32 | 1.24 | [0.57, 1.62] | [116.32, 331.51] | 15.92 | X-SPECIFIC-UNAIMED |
| ESS-weighted | t2 | 5 | 48.41 | 50.61 | 0.51 | [-1.09, 2.40] | [74.07, 220.58] | 23.24 | UNDETERMINED |
| ESS-weighted | pooled | 11 | 12.96 | 231.93 | 0.95 | [0.11, 1.70] | [218.16, 478.69] | 18.21 | UNDETERMINED |

Robust (same pooled branch under both references and the ESS-weighted variant): **yes**. AIM (prime-and-veto, disjoint halves and nouns): -0.10 (null 95th pct 0.20, p = 0.804, 11 rows); association aim -0.12 (null 95th pct 0.27, p = 0.767).

| task | ladder exists (mean centred cos >= 0.5) | mean centred cos | mean raw cos | RAND A vs B r | NONCE h1 vs h2 r | aim | aim p |
|---|---|---|---|---|---|---|---|
| t1 | no | 0.34 | 0.21 | 0.53 | 0.37 | -0.07 | 0.682 |
| t2 | no | -0.02 | -0.07 | -0.26 | 0.82 | -0.14 | 0.787 |

Per-row decomposition (primary reference):

| task | ban B | a_B^2 | N_u | ||s_B||^2 | N_s | cos(Gbar, u) | replicate SD | between-survivor SD | D_B (own-label subtraction) | rho(s, PV) | top residual |
|---|---|---|---|---|---|---|---|---|---|---|---|
| t1 | bfs | 139.75 | 2.04 | 163.48 | 6.13 | 0.68 | 4.04 | 7.79 | -8.25 | -0.25 | iddfs |
| t1 | dfs | 45.20 | 1.53 | 4.32 | 4.60 | 0.96 | 3.50 | 3.15 | 8.43 | -0.10 | iddfs |
| t1 | bibfs | 1.03 | 2.04 | 33.27 | 6.13 | -0.17 | 4.04 | 2.62 | 15.20 | 0.75 | iddfs |
| t1 | iddfs | 0.47 | 1.98 | 36.72 | 5.95 | 0.11 | 3.98 | 2.73 | 23.53 | 0.25 | bibfs |
| t1 | astar_gbfs | 24.13 | 1.97 | 130.22 | 5.92 | 0.40 | 3.97 | 5.56 | -5.93 | -0.50 | iddfs |
| t1 | dijkstra | 39.63 | 1.36 | 77.23 | 4.07 | 0.58 | 3.29 | 4.83 | 2.51 | -0.60 | iddfs |
| t2 | dijkstra | 9.02 | 0.92 | 116.45 | 1.84 | 0.27 | 2.63 | 5.60 | -4.95 | 0.00 | dial |
| t2 | bf_spfa | 119.68 | 1.42 | 27.77 | 2.84 | 0.90 | 3.26 | 6.07 | 10.59 | 0.30 | floyd |
| t2 | bidijkstra | 41.38 | 2.02 | 33.55 | 4.04 | 0.74 | 3.89 | 4.33 | 3.54 | 0.20 | dial |
| t2 | floyd | 73.89 | 1.37 | 5.98 | 2.74 | 0.96 | 3.21 | 4.47 | 15.40 | -0.60 | dial |
| t2 | dial | 7.16 | 0.75 | 2.33 | 1.51 | 0.87 | 2.38 | 1.54 | 26.88 | -0.60 | bf_spfa |

Iteration-1 sham observations under FRLP (7.1):

- t2|floyd->bf_spfa: s = -0.06 [-2.76, 3.67], largest residual: no (bootstrap prob 0.33), Gbar = 2.73 vs fitted ladder 2.79
- t1|iddfs->dfs: s = -0.77 [-7.20, 4.02], largest residual: no (bootstrap prob 0.01), Gbar = -0.45 vs fitted ladder 0.33

### Sensitivity (`results/sensitivity.json`)

| variant | pooled SHARE point | pooled SHARE CI | pooled branch | aim |
|---|---|---|---|---|
| variant:code_body_only | 0.55 | [0.25, 0.68] | UNDETERMINED | -0.10 |
| variant:correct_only | 0.42 | [0.18, 0.57] | UNDETERMINED | -0.17 |
| variant:single_proposal | 0.54 | [0.26, 0.68] | UNDETERMINED | -0.09 |
| variant:truncated_256 | 0.45 | [0.25, 0.64] | UNDETERMINED | -0.11 |
| u:with_ii | 0.55 | [0.25, 0.68] | UNDETERMINED | -0.10 |
| u:unit_normalised | 0.42 | [0.25, 0.66] | UNDETERMINED | -0.08 |
| u:only_NONCE | 0.33 | [0.24, 0.77] | UNDETERMINED | 0.10 |
| u:only_RAND | 0.64 | [0.37, 0.89] | UNDETERMINED | 0.04 |
| u:only_NOV | 0.72 | [0.30, 0.81] | UNDETERMINED | -0.09 |
| variant:unscrubbed_W1_only | 0.69 | [0.51, 0.84] | X-SPECIFIC-UNAIMED | n/a |
| variant:unscrubbed_body_single_W1_only | 0.67 | [0.51, 0.84] | X-SPECIFIC-UNAIMED | n/a |
| variant:primary_W1_only | 0.55 | [0.18, 0.78] | UNDETERMINED | -0.16 |

### Secondary (`results/secondary.json`)

- Two-step ban t1 (frozen templates): implied banned mass 1.00; landing bibfs 0.00, iddfs 0.73, astar_gbfs 0.27, dijkstra 0.00
- Two-step ban t2 (frozen templates): implied banned mass 1.00; landing bidijkstra 0.00, floyd 1.00, dial 0.00
- exp1 step-2 prompts t1|succession:2: implied banned mass 1.00 vs exp1 banned share 0.98; implied landing {'bibfs': 9.582732493607364e-17, 'iddfs': 0.43083038119154765, 'astar_gbfs': 0.32755480974967, 'dijkstra': 0.24161480905878224}
- exp1 step-2 prompts t2|succession:2: implied banned mass 1.00 vs exp1 banned share 1.00; implied landing {'bidijkstra': 0.01279583658722223, 'floyd': 0.9872041634094144, 'dial': 3.3633902239447587e-12}
- Sham t1|jps: residual order ['dijkstra', 'iddfs', 'dfs', 'bfs', 'bibfs', 'astar_gbfs'], declared neighbours ['astar_gbfs'] top-k: no
- Sham t1|idastar: not scored (Q8 dropped)
- Sham t2|johnson: not scored (Q8 dropped)
- Sham t2|yen: not scored (Q8 dropped)

### Coverage of natural programs by forced programs (`results/coverage.json`)

| task|algorithm | natural programs | share with NN Jaccard >= 0.5 | mean NN Jaccard |
|---|---|---|---|
| t1|bfs | 1102 | 0.69 | 0.66 |
| t1|dfs | 262 | 0.56 | 0.59 |
| t1|bibfs | 5 | 0.60 | 0.49 |
| t1|iddfs | 37 | 0.73 | 0.58 |
| t1|astar_gbfs | 29 | 0.48 | 0.57 |
| t1|dijkstra | 12 | 0.17 | 0.42 |
| t2|dijkstra | 1004 | 0.96 | 0.94 |
| t2|bf_spfa | 251 | 0.40 | 0.54 |
| t2|floyd | 43 | 1.00 | 0.95 |

### ESS per condition family (`results/ess_table.json`)

| task|family | half-cells | median ESS | share < 5 |
|---|---|---|---|
| t1|ban | 516 | 1.13 | 0.99 |
| t1|base0 | 12 | 1.07 | 1.00 |
| t1|edit | 72 | 1.19 | 0.99 |
| t1|exp1_gate | 228 | 1.21 | 0.98 |
| t1|forced | 120 | 5.61 | 0.43 |
| t1|mention | 360 | 1.20 | 0.96 |
| t1|neutral | 516 | 1.08 | 0.98 |
| t1|novelty | 12 | 1.10 | 1.00 |
| t2|ban | 350 | 1.17 | 0.97 |
| t2|base0 | 10 | 1.40 | 1.00 |
| t2|edit | 60 | 1.08 | 0.97 |
| t2|exp1_gate | 175 | 1.28 | 0.98 |
| t2|forced | 100 | 3.69 | 0.70 |
| t2|mention | 250 | 1.11 | 0.94 |
| t2|neutral | 350 | 1.27 | 1.00 |
| t2|novelty | 10 | 1.02 | 1.00 |

Scored units by queue: {'Q1': 110, 'Q2': 69, 'Q3': 165, 'Q4': 44, 'Q5': 55, 'Q6': 30, 'Q7': 202, 'Q8': 9}; skipped after the GPU cutoff: 57 units.
