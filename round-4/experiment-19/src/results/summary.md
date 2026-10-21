**C1 (pre-registered rule): PARTIAL** (failed: count1>=3, CI_low>0).
count1 = #{t: H5_PN >= 1.5} = 2/6; count2 = #{t: H5_PN > H5_best} = 4/6; best NA knob beats PN on 2 tasks; D_bar = -0.218 (task bootstrap 95% CI [-0.893, 0.304], one-sided p_C1 = 0.7576); exact sign test over the 6 D_t: p = 0.3438.

| Task (default) | H5 PN | best NA knob | H5 best NA | D_t [95% CI] | P(H5_PN > H5_best) | P15 PN | P20 PN |
|---|---|---|---|---|---|---|---|
| T03 (full_sort) | 2.72 | NOVELTY | 1.96 | 0.76 [0.21, 1.16] | 1.00 | 0.0 | 0.0 |
| T05 (hash_map) | 1.29 | NOVELTY | 1.24 | 0.05 [-0.20, 0.37] | 0.67 | 11.1 | – |
| T06 (hash_set) | 1.00 | VETO_ITER | 2.73 | -1.73 [-2.06, -1.39] | 0.00 | – | – |
| T10 (union_find) | 2.09 | VETO_ITER | 1.96 | 0.13 [-0.00, 0.37] | 0.91 | 0.0 | 0.0 |
| T1 (bfs) | 1.42 | NOVELTY | 1.34 | 0.07 [-0.57, 0.41] | 0.49 | 18.0 | 49.8 |
| T2 (dijkstra) | 1.35 | SEMSEED | 1.93 | -0.58 [-0.69, -0.14] | 0.00 | 9.3 | – |

H5 per knob class on E6 (randomisation hull, cost <= 5 points; 95% bootstrap CI in results/c1.json `class_ci`):

| Task | PN | TEMP | TOPK10 | NONCE | NOVELTY | SEMSEED | VETO_1SHOT | VETO_PERSIST | VETO_ITER | MINP | VS |
|---|---|---|---|---|---|---|---|---|---|---|---|
| T03 | 2.72 | 1.09 | 1.00 | 1.00 | 1.96 | – | 1.90 | 1.88 | 1.89 | 1.16 | 1.29 |
| T05 | 1.29 | 1.00 | 1.00 | 1.00 | 1.24 | – | 1.00 | 1.00 | 1.00 | 1.00 | 1.04 |
| T06 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | – | 1.00 | 1.00 | 2.73 | 1.00 | 1.01 |
| T10 | 2.09 | 1.00 | 1.00 | 1.00 | 1.17 | – | 1.02 | 1.03 | 1.96 | 1.09 | 1.02 |
| T1 | 1.42 | 1.00 | 1.00 | 1.00 | 1.34 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| T2 | 1.35 | 1.09 | 1.00 | 1.00 | 1.24 | 1.93 | 1.00 | 1.00 | 1.00 | 1.17 | 1.00 |

Sensitivities (each re-evaluates the full rule):

| Sensitivity | verdict | count1 | count2 | D_bar [95% CI] |
|---|---|---|---|---|
| s1_twin_segment_hull | PARTIAL | 2 | 3 | -0.266 [-0.905, 0.246] |
| s2_minp_vs_added | PARTIAL | 2 | 4 | -0.218 [-0.897, 0.314] |
| s2b_minp_only_added | PARTIAL | 2 | 4 | -0.218 [-0.863, 0.305] |
| s3_dial_interpolation | PARTIAL | 2 | 4 | -0.022 [-0.710, 0.607] |
| s4_template_cluster_bootstrap | PARTIAL | 2 | 4 | -0.218 [-0.866, 0.329] |
| s5_slot_paired_bootstrap | PARTIAL | 2 | 4 | -0.218 [-0.893, 0.322] |
| s6_other_exclude | PARTIAL | 2 | 4 | -0.243 [-0.892, 0.263] |
| s6_other_one | PARTIAL | 2 | 4 | -0.219 [-0.892, 0.326] |
| s7_reused_vetoes_excluded | PARTIAL | 2 | 4 | 0.202 [-0.188, 0.600] |
| s8_step0_vertices_only | PARTIAL | 2 | 3 | -0.134 [-0.721, 0.512] |

Engine check: **REPRODUCED** — per-slot label agreement T03|NEUTRAL 1.00, T03|RAND9002_a1.0 1.00, T2|NEUTRAL 1.00, T2|RAND9004_a1.0 1.00.
Novelty audit: 12 unique correct 'other' programs, classes {'LABELLER MISS': 12}; confirmed NOVEL = 0; judges A/B agree on 8/10 (Cohen's kappa 0.00 is uninformative when one class dominates); controls 10/10; complete = True.
Label-validity audit (judge vs labeller agreement): T03|PN_alpha_le2 0.80 (n 10), T03|best_NA 0.80 (n 10), T05|PN_alpha_le2 1.00 (n 1), T05|best_NA 1.00 (n 3), T06|best_NA 1.00 (n 10), T10|PN_alpha_le2 1.00 (n 10), T10|best_NA 1.00 (n 10), T1|PN_alpha_le2 1.00 (n 5), T1|best_NA 1.00 (n 9), T2|PN_alpha_le2 1.00 (n 10), T2|best_NA 1.00 (n 10).

R2 (held out) and the 8 non-movable bench tasks (E6 H5_PN for comparison: min 1.00, median 1.38, max 2.72):

| Task | PN off-default excess (alpha <= 2) | H5 PN | H5 TEMP | H5 NONCE | H5 NOVELTY | P15 PN |
|---|---|---|---|---|---|---|
| R1 | 0.00 | 1.00 | 1.00 | 1.00 | 1.00 | – |
| R2 (held out) | 0.01 | 1.09 | 1.00 | 1.00 | 1.37 | 29.0 |
| R3 | 0.00 | 1.00 | 1.00 | 1.00 | 1.00 | – |
| R6 | -0.08 | 1.37 | 1.42 | 1.21 | 1.20 | – |
| T04 | 0.00 | 1.00 | 1.00 | 1.00 | 2.57 | – |
| T08 | 0.01 | 1.00 | 1.00 | 1.00 | 1.04 | – |
| T11 | 0.03 | 1.01 | 1.00 | 1.00 | 1.05 | – |
| T13 | 0.00 | 1.00 | 1.00 | 1.00 | 1.00 | – |
| T14 | 0.04 | 1.14 | 1.00 | 1.00 | 1.00 | – |

Independent re-derivation: 12/12 checks match; arm-shuffle placebo fires 8/100; PN-replaced-by-TWIN placebo D_t <= 0: True; hash chain breaks 0, commit precedes stage 1: True.
GPU: 10100 rows in 640 batches, 2.53 GPU-hours of batch time; 67 rows hit the 1,024-token cap.
OpenRouter spend: USD 0.227 (cap 1.00).
