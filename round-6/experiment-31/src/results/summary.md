### Units (forecasts committed before each unit's first nudge row)

| unit | default D_u | K | base runner-up r_u | q_lik top-1 | tail t_u | tail-empty | discordant | E_u (a=1/2/4) | HF twin pass | gate (kappa / rt-vs-adj) | flags |
|---|---|---|---|---|---|---|---|---|---|---|---|
| I1 | set_start_walk | 5 | sort_scan | sort_scan | - | yes | no | 0.00/0.00/0.00 | 1.00 | 0.92 / 0.96 (gate) | - |
| I2 | sorted_key | 4 | count_key | count_key | sort_then_group | no | no | 0.00/0.00/0.12 | 1.00 | 1.00 / 0.96 (gate) | - |
| I3 | seen_set | 4 | known_loop | floyd | - | yes | yes | 0.00/0.00/0.00 | 0.98 | 1.00 / 0.96 (gate) | - |
| I4 | sort_scan | 4 | counting_levels | counting_levels | - | yes | no | 0.00/0.00/0.00 | 1.00 | 1.00 / 0.96 (gate) | - |
| I6 | dutch_flag | 4 | counting_overwrite | builtin_sort | - | yes | yes | 0.00/0.00/0.12 | 0.98 | 1.00 / 0.96 (gate) | - |
| I7 | per_number_loop | 5 | builtin_count | dp_half | builtin_count | no | yes | 0.00/0.38/0.38 | 1.00 | 0.94 / 0.92 (gate) | - |
| I8 | hash_set_scan | 5 | sort_scan | cyclic_placement | - | yes | yes | 0.00/0.00/0.00 | 1.00 | 1.00 / 0.92 (gate) | - |
| I9 | hash_count | 4 | count_array | sort_two_index | - | yes | yes | 0.00/0.00/0.00 | 1.00 | 0.86 / 1.00 (gate) | - |
| I10 | running_min | 4 | suffix_max | suffix_max | - | yes | no | 0.00/0.00/0.00 | 1.00 | 1.00 / 1.00 (gate_revision) | - |
| I5 | two_sorted_lists | 4 | sweep_events | min_heap_ends | min_heap_ends | no | yes | 0.25/0.62/0.38 | 0.98 | 1.00 / 1.00 (gate) | - |

### Landing events (cells with pass rate >= 0.8 x twin pooled per nudge type)

| unit | nudge | n attempts | pass | correct off-default catalogue programs | other (correct) | exists | modal | lead | clear | r_u hit | q_lik hit | t_u hit |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| I1 | ESC | 160 | 0.97 | 0 | 0 | no | - | 0.00 | no | - | - | - |
| I1 | PN | 50 | 0.96 | sort_scan 1 | 0 | no | sort_scan | 1.00 | no | - | - | - |
| I1 | GTN | 0 | - | 0 | 0 | no | - | 0.00 | no | - | - | - |
| I2 | ESC | 260 | 1.00 | count_key 11 | 0 | yes | count_key | 1.00 | yes | yes | yes | no |
| I2 | PN | 100 | 0.96 | 0 | 0 | no | - | 0.00 | no | - | - | - |
| I2 | GTN | 50 | 0.98 | 0 | 0 | no | - | 0.00 | no | - | - | - |
| I3 | ESC | 240 | 0.97 | 0 | 0 | no | - | 0.00 | no | - | - | - |
| I3 | PN | 100 | 0.96 | 0 | 0 | no | - | 0.00 | no | - | - | - |
| I3 | GTN | 50 | 0.92 | 0 | 0 | no | - | 0.00 | no | - | - | - |
| I4 | ESC | 230 | 0.99 | 0 | 0 | no | - | 0.00 | no | - | - | - |
| I4 | PN | 100 | 0.94 | counting_levels 2 | 0 | no | counting_levels | 1.00 | no | - | - | - |
| I4 | GTN | 50 | 0.90 | 0 | 0 | no | - | 0.00 | no | - | - | - |
| I6 | ESC | 180 | 0.97 | counting_overwrite 7 | 0 | yes | counting_overwrite | 1.00 | yes | yes | no | no |
| I6 | PN | 50 | 0.94 | 0 | 0 | no | - | 0.00 | no | - | - | - |
| I6 | GTN | 0 | - | 0 | 0 | no | - | 0.00 | no | - | - | - |
| I7 | ESC | 320 | 0.99 | builtin_count 126 | 0 | yes | builtin_count | 1.00 | yes | yes | no | yes |
| I7 | PN | 100 | 0.99 | builtin_count 31, dp_half 1 | 0 | yes | builtin_count | 0.94 | yes | yes | no | yes |
| I7 | GTN | 50 | 0.98 | builtin_count 21 | 0 | yes | builtin_count | 1.00 | yes | yes | no | yes |
| I8 | ESC | 230 | 0.98 | 0 | 0 | no | - | 0.00 | no | - | - | - |
| I8 | PN | 50 | 0.98 | 0 | 0 | no | - | 0.00 | no | - | - | - |
| I8 | GTN | 50 | 0.82 | cyclic_placement 1 | 0 | no | cyclic_placement | 1.00 | no | - | - | - |
| I9 | ESC | 240 | 0.99 | 0 | 0 | no | - | 0.00 | no | - | - | - |
| I9 | PN | 100 | 0.99 | 0 | 0 | no | - | 0.00 | no | - | - | - |
| I9 | GTN | 50 | 1.00 | 0 | 0 | no | - | 0.00 | no | - | - | - |
| I10 | ESC | 240 | 1.00 | 0 | 0 | no | - | 0.00 | no | - | - | - |
| I10 | PN | 100 | 1.00 | 0 | 0 | no | - | 0.00 | no | - | - | - |
| I10 | GTN | 50 | 1.00 | 0 | 0 | no | - | 0.00 | no | - | - | - |
| I5 | ESC | 380 | 0.93 | min_heap_ends 147, sweep_events 29 | 0 | yes | min_heap_ends | 0.67 | yes | no | yes | yes |
| I5 | PN | 100 | 0.89 | min_heap_ends 46, sweep_events 6 | 0 | yes | min_heap_ends | 0.77 | yes | no | yes | yes |
| I5 | GTN | 0 | - | 0 | 0 | no | - | 0.00 | no | - | - | - |

### Claim L tests (pool_l1.py, frozen; panel I alone is descriptive below n = 6)

| test | scope | n | statistic | p | verdict |
|---|---|---|---|---|---|
| L1a (tail-empty events) | per event | 1 | 1 hits (chance mean 0.33) | 0.333 | DESCRIPTIVE |
| L1b (discordant events) | per event | 6 | b = 4, c = 2 | 0.344 | FAIL |
| L1a | unit-clustered | 1 | 1 hits | 0.333 | DESCRIPTIVE |
| L1b | unit-clustered | 3 | b = 2, c = 1 | 0.500 | DESCRIPTIVE |

All existing events: r_u named the modal landing in 5/7; t_u (tuned model's own minority mode) in 5/6 events where t_u is defined. Verdict note: no inferential pass.

| log-score difference D = LS_base - LS_rival | events | mean D (nats) | one-sided 95% lower bound | non-inferior (> -0.10) | defined-only n / mean D |
|---|---|---|---|---|---|
| base vs q_lik (event bootstrap) | 7 | 0.95 | 0.32 | yes | 7 / 0.95 |
| base vs q_lik (unit-cluster bootstrap) | 7 | 0.95 | 0.00 | yes | - |
| base vs q_lik_raw (event bootstrap) | 7 | 16.06 | 8.28 | yes | 7 / 16.06 |
| base vs q_lik_raw (unit-cluster bootstrap) | 7 | 16.06 | 1.80 | yes | - |
| base vs q_tail (event bootstrap) | 7 | 0.25 | -0.05 | yes | 7 / 0.25 |
| base vs q_tail (unit-cluster bootstrap) | 7 | 0.25 | -0.16 | no | - |

**L2:** 0 of 477 correct nudged off-default programs fall in a mode with 0 valid and 0 correct base programs (rule-of-three upper bound 0.006).

**L3 (held-out log score of the nudged off-default programs, mean over 10 splits; units with >= 4 programs):**

| unit | n | q_base^gamma | uniform | association | q_tail | Kendall tau(base, tail) |
|---|---|---|---|---|---|---|
| I1 | 7 | -2.13 | -1.39 | -0.80 | -1.39 | - |
| I2 | 11 | -0.00 | -1.10 | -0.51 | -1.39 | -0.82 |
| I3 | 0 | - | - | - | - | - |
| I4 | 2 | - | - | - | - | - |
| I6 | 19 | -0.03 | -1.10 | -0.11 | -1.10 | - |
| I7 | 179 | -0.06 | -1.39 | -3.15 | -0.57 | 0.77 |
| I8 | 6 | -1.44 | -1.39 | -1.27 | -1.39 | - |
| I9 | 0 | - | - | - | - | - |
| I10 | 0 | - | - | - | - | - |
| I5 | 253 | -0.93 | -1.10 | -0.56 | -0.57 | 0.00 |

Pooled Kendall tau mean -0.01; sign test over units 1 positive / 1 negative, p = 0.750.

**M (movability candidates vs E_u; one panel, descriptive):**

| candidate | direction | n | Spearman rho | one-sided p | Holm p | supported |
|---|---|---|---|---|---|---|
| beta | + | 10 | 0.71 | 0.014 | 0.070 | no |
| replacement | - | 10 | 0.46 | 0.901 | 1.000 | no |
| runtime_merit | - | 10 | 0.03 | 0.532 | 1.000 | no |
| twin_modal_share | - | 10 | -0.89 | 0.003 | 0.016 | yes |
| K | + | 10 | -0.04 | 0.581 | 1.000 | no |
| m | - | 9 | -0.08 | 0.419 | 1.000 | no |

**K (correct-only rarefied Hill-1 at depth 25; pass cost = twin pass rate minus knob pass rate, points):**

| unit | Hill-1 twin | PN a2 (cost) | PN a4 (cost) | BINT (cost) | H5 / P15 / P20 (full hull) |
|---|---|---|---|---|---|
| I1 | 1.00 | 1.10 (4) | 1.35 (24) | 1.94 (33) | 1.22 / 1.63 / 1.76 |
| I2 | 1.01 | 1.00 (0) | 1.00 (8) | 1.27 (0) | 1.29 / 1.29 / 1.29 |
| I3 | 1.00 | 1.00 (3) | 1.00 (3) | 1.27 (-1) | 1.30 / 1.30 / 1.30 |
| I4 | 1.00 | 1.00 (2) | 1.18 (10) | 1.00 (13) | 1.10 / 1.21 / 1.21 |
| I6 | 1.00 | 1.00 (2) | 1.79 (26) | 1.15 (2) | 1.26 / 1.58 / 1.72 |
| I7 | 1.04 | 1.67 (2) | 1.96 (0) | 2.38 (23) | 2.07 / 2.28 / 2.39 |
| I8 | 1.00 | 1.00 (2) | 1.24 (24) | 2.06 (10) | 1.60 / 2.15 / 2.15 |
| I9 | 1.00 | 1.00 (0) | 1.00 (2) | 1.14 (0) | 1.17 / 1.17 / 1.17 |
| I10 | 1.00 | 1.00 (0) | 1.00 (0) | 1.00 (0) | 1.00 / 1.00 / 1.00 |
| I5 | 1.31 | 1.95 (1) | 2.59 (3) | 1.79 (-2) | 2.61 / 2.61 / 2.61 |

**Novelty audit:** 1 distinct correct 'other' programs among 8936 correct programs; classes {'CATALOGUE_VARIANT': 1}; no correct novel algorithm (rule-of-three bound 0.00034 per correct program).
