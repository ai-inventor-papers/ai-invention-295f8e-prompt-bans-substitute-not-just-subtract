## S0 twins (N = 100 per unit, T 1.0, top-p 1)

| unit | counts | A_min | A_min share | pass rate | iteration-5 record |
|---|---|---|---|---|---|
| B3 | {'prim_heap': 19, 'kruskal': 80, 'disputed': 1} | prim_heap | 0.19 | 0.97 | 0.34 |
| A3 | {'two_pointers': 31, 'prefix_suffix_max': 68, 'disputed': 1} | two_pointers | 0.31 | 1.00 | 0.36 |
| B6 | {'hash_count': 10, 'sort_compare': 77, 'fixed_count_array': 13} | fixed_count_array | 0.13 | 1.00 | 0.24 |

## S1 fork location

| unit | mode | |O| | coverage (clusters) | confirmed / base paths | on-O confirmed at |O|+1 | calibration (k=0 vs twin, Fisher p) |
|---|---|---|---|---|---|---|
| B3 | ONE-TOKEN | 61 | c0 61 tok 0.51, c1 61 tok 0.20 | 5/12 | 3/3 | 0.16 vs 0.19 (p 0.58, pass) |
| A3 | ONE-TOKEN | 18 | c0 18 tok 0.48, c1 19 tok 0.31 | 2/12 | 1/1 | 0.22 vs 0.31 (p 0.20, pass) |
| B6 | ONE-TOKEN | 23 | c0 23 tok 0.78 | 1/8 | 1/1 | 0.22 vs 0.13 (p 0.19, pass) |

Confirmed fork tokens:

- B3: ' Prim' at k=62 (jump 0.70); ' Prim' at k=62 (jump 0.85); ' Prim' at k=62 (jump 0.50); ' Prim' at k=62 (jump 0.65); ' Prim' at k=62 (jump 0.80)
- A3: ' left' at k=19 (jump 0.75); ' left' at k=19 (jump 0.55)
- B6: ' return' at k=24 (jump 0.75)

## Test (1): one-token concentration H(A | fork class)

| unit | H (bits) | bootstrap 95% CI | class mass | undecided-token mass | pass (<= 0.3) |
|---|---|---|---|---|---|
| B3 | 0.050 | [0.014, 0.096] | {'kruskal': 0.741, 'prim_heap': 0.259} | 0.003 | yes |
| A3 | 0.153 | [0.091, 0.203] | {'prefix_suffix_max': 0.571, 'two_pointers': 0.429, 'other': 0.0} | 0.116 | yes |
| B6 | 0.189 | [0.123, 0.239] | {'sort_compare': 0.738, 'fixed_count_array': 0.261, 'hash_count': 0.001, 'other': 0.0} | 0.000 | yes |

## Test (2): committed predictions vs the same-seed sweep (attempted A_min share, N = 50 per cell)

| unit | cell | predicted | observed [Wilson 95%] | correct A_min obs / pred | on-opening obs / pred | JS (bits) | replay acc |
|---|---|---|---|---|---|---|---|
| B3 | T0.3_p1 | 0.068 | 0.060 [0.02, 0.16] | 0.060 / 0.068 | 1.00 / 0.99 | 0.000 | 0.98 (n 50) |
| B3 | T0.3_k10 | 0.068 | 0.060 [0.02, 0.16] | 0.060 / 0.068 | 1.00 / 0.99 | 0.000 | 0.98 (n 50) |
| B3 | T0.7_p1 | 0.193 | 0.220 [0.13, 0.35] | 0.220 / 0.193 | 0.92 / 0.87 | 0.003 | 0.96 (n 47) |
| B3 | T0.7_k10 | 0.193 | 0.220 [0.13, 0.35] | 0.220 / 0.193 | 0.92 / 0.87 | 0.003 | 0.96 (n 47) |
| B3 | T1.0_p1 | 0.237 | 0.400 [0.28, 0.54] | 0.400 / 0.237 | 0.76 / 0.72 | 0.026 | 0.95 (n 37) |
| B3 | T1.0_k10 | 0.237 | 0.400 [0.28, 0.54] | 0.400 / 0.237 | 0.76 / 0.72 | 0.026 | 0.95 (n 37) |
| B3 | T1.3_p1 | 0.247 | 0.380 [0.26, 0.52] | 0.360 / 0.247 | 0.60 / 0.55 | 0.022 | 0.94 (n 32) |
| B3 | T1.3_k10 | 0.247 | 0.380 [0.26, 0.52] | 0.360 / 0.247 | 0.60 / 0.55 | 0.022 | 0.91 (n 32) |
| A3 | T0.3_p1 | 0.166 | 0.100 [0.04, 0.21] | 0.100 / 0.166 | 0.88 / 0.86 | 0.007 | 0.98 (n 45) |
| A3 | T0.3_k10 | 0.166 | 0.100 [0.04, 0.21] | 0.100 / 0.166 | 0.88 / 0.86 | 0.007 | 0.98 (n 45) |
| A3 | T0.7_p1 | 0.285 | 0.180 [0.10, 0.31] | 0.180 / 0.285 | 0.84 / 0.82 | 0.011 | 0.98 (n 41) |
| A3 | T0.7_k10 | 0.285 | 0.180 [0.10, 0.31] | 0.180 / 0.285 | 0.84 / 0.82 | 0.011 | 0.98 (n 41) |
| A3 | T1.0_p1 | 0.311 | 0.180 [0.10, 0.31] | 0.180 / 0.311 | 0.74 / 0.76 | 0.026 | 0.92 (n 38) |
| A3 | T1.0_k10 | 0.311 | 0.180 [0.10, 0.31] | 0.180 / 0.311 | 0.74 / 0.76 | 0.026 | 0.92 (n 38) |
| A3 | T1.3_p1 | 0.319 | 0.200 [0.11, 0.33] | 0.200 / 0.319 | 0.70 / 0.70 | 0.022 | 0.97 (n 35) |
| A3 | T1.3_k10 | 0.319 | 0.200 [0.11, 0.33] | 0.200 / 0.319 | 0.70 / 0.70 | 0.022 | 0.97 (n 35) |
| B6 | T0.3_p1 | 0.161 | 0.180 [0.10, 0.31] | 0.180 / 0.161 | 0.80 / 0.81 | 0.000 | 0.93 (n 40) |
| B6 | T0.3_k10 | 0.161 | 0.180 [0.10, 0.31] | 0.180 / 0.161 | 0.80 / 0.81 | 0.000 | 0.93 (n 40) |
| B6 | T0.7_p1 | 0.182 | 0.140 [0.07, 0.26] | 0.140 / 0.182 | 0.76 / 0.82 | 0.003 | 0.95 (n 39) |
| B6 | T0.7_k10 | 0.182 | 0.140 [0.07, 0.26] | 0.140 / 0.182 | 0.76 / 0.82 | 0.003 | 0.95 (n 39) |
| B6 | T1.0_p1 | 0.200 | 0.120 [0.06, 0.24] | 0.120 / 0.200 | 0.78 / 0.81 | 0.010 | 0.90 (n 39) |
| B6 | T1.0_k10 | 0.200 | 0.120 [0.06, 0.24] | 0.120 / 0.200 | 0.78 / 0.81 | 0.010 | 0.90 (n 39) |
| B6 | T1.3_p1 | 0.212 | 0.180 [0.10, 0.31] | 0.180 / 0.212 | 0.80 / 0.79 | 0.002 | 0.95 (n 39) |
| B6 | T1.3_k10 | 0.212 | 0.180 [0.10, 0.31] | 0.180 / 0.212 | 0.80 / 0.79 | 0.002 | 0.95 (n 39) |

| unit | MAE | dObs 1.0->0.3 [slot bootstrap] | dPred | McNemar b:c, one-sided p | dObs 1.0->1.3 | dPred 1.0->1.3 | slots changing idea across T (top-p 1) | pass |
|---|---|---|---|---|---|---|---|---|
| B3 | 0.083 | 0.340 [0.22, 0.48] | 0.169 | 17:0, 0.0000 | -0.020 | 0.010 | 20/50 | yes |
| A3 | 0.105 | 0.080 [-0.04, 0.22] | 0.144 | 7:3, 0.1719 | 0.020 | 0.009 | 12/50 | no |
| B6 | 0.043 | -0.060 [-0.16, 0.04] | 0.039 | 2:5, 0.9375 | 0.060 | 0.013 | 11/50 | no |

Pooled B3 + A3 exact one-sided McNemar (T 1.0 -> 0.3, top-p 1): b:c = 24:3, p = 0.00002 (unadjusted 0.05: True; Bonferroni 0.05/7: True).

## Test (3): collapsed-task margins

| task | margin (nats) | >= 4 | p_off pred T0.3 / T1.0 / T1.3 (top-p 1) | dPred 1.3-0.3 | bound check (T 1.3, n off / n vs logit) | T 1.3 check off / N | 48-token LLR |
|---|---|---|---|---|---|---|---|
| T1 | 7.46 | yes | 0.0000 / 0.0006 / 0.0021 | 0.0021 | 0/100 vs 0.0021 | 1/20 | 8.79 |
| T2 | 4.85 | yes | 0.0000 / 0.0078 / 0.0204 | 0.0204 | 0/100 vs 0.0204 | 1/20 | 5.15 |
| T10 | 17.04 | yes | 0.0000 / 0.0000 / 0.0000 | 0.0000 | 0/100 vs 0.0000 | 0/20 | 24.58 |
| T03 | 6.10 | yes | 0.0000 / 0.0022 / 0.0085 | 0.0085 | 0/100 vs 0.0085 | 0/20 | 7.55 |

## Verdict: **PARTIAL** (passes {'test1': True, 'test2': False, 'test3': True}; disconfirming branches {'test1': False, 'test2': False}; secondary raw p 0.00002)


## S4A

```json
{
 "B3": {
  "twin_slots_0_1": {
   "n": 10,
   "s_obs": 0.2,
   "pass_rate": 1.0,
   "s_pred": 0.2364466726789262
  },
  "spearman_dmargin_dshare": -0.6881023532039754,
  "perm_p_one_sided": 0.9794973544973545,
  "perm_p_one_sided_negative": 0.027116402116402115,
  "p_note": "perm_p_one_sided is the committed upper tail; perm_p_one_sided_negative is the lower tail in the predicted (negative) direction (post-commit correction, results/deviations.json)",
  "note": "Spearman over 8 directions plus the twin (0, 0); expected sign negative: a larger D margin should lower the minority share",
  "mae_s_pred": 0.14575990036334197,
  "log_score_gain_per_sample": 0.05260524091541798,
  "pass_rate_vs_twin": 0.9125
 },
 "A3": {
  "twin_slots_0_1": {
   "n": 10,
   "s_obs": 0.4,
   "pass_rate": 1.0,
   "s_pred": 0.18897008162054063
  },
  "spearman_dmargin_dshare": -0.4426533959945493,
  "perm_p_one_sided": 0.8883928571428571,
  "perm_p_one_sided_negative": 0.11610449735449735,
  "p_note": "perm_p_one_sided is the committed upper tail; perm_p_one_sided_negative is the lower tail in the predicted (negative) direction (post-commit correction, results/deviations.json)",
  "note": "Spearman over 8 directions plus the twin (0, 0); expected sign negative: a larger D margin should lower the minority share",
  "mae_s_pred": 0.1883982330239466,
  "log_score_gain_per_sample": 0.1092541588421773,
  "pass_rate_vs_twin": 0.9875
 },
 "B6": {
  "twin_slots_0_1": {
   "n": 10,
   "s_obs": 0.1,
   "pass_rate": 1.0,
   "s_pred": 0.1998990138525924
  },
  "spearman_dmargin_dshare": -0.9355777949468197,
  "perm_p_one_sided": 0.9998677248677249,
  "perm_p_one_sided_negative": 0.00026455026455026457,
  "p_note": "perm_p_one_sided is the committed upper tail; perm_p_one_sided_negative is the lower tail in the predicted (negative) direction (post-commit correction, results/deviations.json)",
  "note": "Spearman over 8 directions plus the twin (0, 0); expected sign negative: a larger D margin should lower the minority share",
  "mae_s_pred": 0.17807367334151225,
  "log_score_gain_per_sample": 0.1615345262269045,
  "pass_rate_vs_twin": 1.0
 }
}
```

## S4B

```json
{
 "B3": {
  "exchange_vs_pad": {
   "b": 23,
   "c": 0,
   "p_one_sided": 1.1920928955078125e-07
  },
  "exchange_vs_MR": {
   "b": 18,
   "c": 0,
   "p_one_sided": 3.814697265625e-06
  },
  "forced_adherence": 1.0,
  "forced_adherence_ok": true,
  "d_margin_exchange": -4.867103539220489,
  "d_margin_MR": -1.2459642664783825,
  "s_pred_exchange": 0.17242232918588898,
  "abs_err_exchange": 0.827577670814111,
  "exchange_pass_ratio_vs_pad": 1.0
 },
 "A3": {
  "exchange_vs_pad": {
   "b": 26,
   "c": 0,
   "p_one_sided": 1.4901161193847656e-08
  },
  "exchange_vs_MR": {
   "b": 26,
   "c": 0,
   "p_one_sided": 1.4901161193847656e-08
  },
  "forced_adherence": 1.0,
  "forced_adherence_ok": true,
  "d_margin_exchange": -5.499995431246151,
  "d_margin_MR": -2.0000002586176597,
  "s_pred_exchange": 0.40478556354153117,
  "abs_err_exchange": 0.5952144364584688,
  "exchange_pass_ratio_vs_pad": 1.0
 },
 "B6": {
  "exchange_vs_pad": {
   "b": 30,
   "c": 0,
   "p_one_sided": 9.313225746154785e-10
  },
  "exchange_vs_MR": {
   "b": 30,
   "c": 0,
   "p_one_sided": 9.313225746154785e-10
  },
  "forced_adherence": 1.0,
  "forced_adherence_ok": true,
  "d_margin_exchange": -22.11553422194521,
  "d_margin_MR": 0.2555518943077226,
  "s_pred_exchange": 0.7806454118428254,
  "abs_err_exchange": 0.21935458815717457,
  "exchange_pass_ratio_vs_pad": 1.0
 }
}
```

## 1a-c: ideas x phrasings per cell (correct-only Hill-1 rarefied at depth 25; phrasing clusters = identifier-normalised AST 4-gram Jaccard >= 0.8, single linkage)

| unit | cell | ideas (correct) | Hill-1@25 | phrasing clusters per idea (theta 0.8) | 10 literal trajectories: ideas | their phrasing clusters |
|---|---|---|---|---|---|---|
| B3 | T0.3_p1 | ['kruskal', 'prim_heap'] | 1.25 | {'kruskal': 3, 'prim_heap': 1} | {'kruskal': 9, 'prim_heap': 1} | {'kruskal': 3, 'prim_heap': 1} |
| B3 | T0.7_p1 | ['kruskal', 'prim_heap'] | 1.69 | {'kruskal': 4, 'prim_heap': 1} | {'kruskal': 6, 'prim_heap': 4} | {'kruskal': 2, 'prim_heap': 1} |
| B3 | T1.0_p1 | ['kruskal', 'prim_heap'] | 1.95 | {'kruskal': 4, 'prim_heap': 5} | {'kruskal': 4, 'prim_heap': 6} | {'kruskal': 2, 'prim_heap': 3} |
| B3 | T1.3_p1 | ['kruskal', 'prim_heap'] | 1.92 | {'kruskal': 7, 'prim_heap': 4} | {'kruskal': 4, 'prim_heap': 6} | {'kruskal': 3, 'prim_heap': 2} |
| B3 | T0.3_k10 | ['kruskal', 'prim_heap'] | 1.25 | {'kruskal': 3, 'prim_heap': 1} | {'kruskal': 9, 'prim_heap': 1} | {'kruskal': 3, 'prim_heap': 1} |
| B3 | T0.7_k10 | ['kruskal', 'prim_heap'] | 1.69 | {'kruskal': 4, 'prim_heap': 1} | {'kruskal': 6, 'prim_heap': 4} | {'kruskal': 2, 'prim_heap': 1} |
| B3 | T1.0_k10 | ['kruskal', 'prim_heap'] | 1.95 | {'kruskal': 4, 'prim_heap': 5} | {'kruskal': 4, 'prim_heap': 6} | {'kruskal': 2, 'prim_heap': 3} |
| B3 | T1.3_k10 | ['kruskal', 'prim_heap'] | 1.92 | {'kruskal': 7, 'prim_heap': 4} | {'kruskal': 4, 'prim_heap': 6} | {'kruskal': 3, 'prim_heap': 2} |
| B3 | per-slot idea changes across T | {'p1': {'slots_with_idea_change_across_T': 20, 'n_slots': 50}, 'k10': {'slots_with_idea_change_across_T': 20, 'n_slots': 50}} | | | | |
| A3 | T0.3_p1 | ['prefix_suffix_max', 'two_pointers'] | 1.37 | {'prefix_suffix_max': 1, 'two_pointers': 1} | {'prefix_suffix_max': 9, 'two_pointers': 1} | {'prefix_suffix_max': 1, 'two_pointers': 1} |
| A3 | T0.7_p1 | ['prefix_suffix_max', 'two_pointers'] | 1.58 | {'prefix_suffix_max': 2, 'two_pointers': 1} | {'prefix_suffix_max': 9, 'two_pointers': 1} | {'prefix_suffix_max': 1, 'two_pointers': 1} |
| A3 | T1.0_p1 | ['peak_split', 'prefix_suffix_max', 'two_pointers'] | 1.74 | {'peak_split': 1, 'prefix_suffix_max': 2, 'two_pointers': 2} | {'prefix_suffix_max': 9, 'two_pointers': 1} | {'prefix_suffix_max': 1, 'two_pointers': 1} |
| A3 | T1.3_p1 | ['peak_split', 'prefix_suffix_max', 'two_pointers'] | 1.79 | {'peak_split': 1, 'prefix_suffix_max': 3, 'two_pointers': 2} | {'prefix_suffix_max': 8, 'two_pointers': 2} | {'prefix_suffix_max': 3, 'two_pointers': 1} |
| A3 | T0.3_k10 | ['prefix_suffix_max', 'two_pointers'] | 1.37 | {'prefix_suffix_max': 1, 'two_pointers': 1} | {'prefix_suffix_max': 9, 'two_pointers': 1} | {'prefix_suffix_max': 1, 'two_pointers': 1} |
| A3 | T0.7_k10 | ['prefix_suffix_max', 'two_pointers'] | 1.58 | {'prefix_suffix_max': 2, 'two_pointers': 1} | {'prefix_suffix_max': 9, 'two_pointers': 1} | {'prefix_suffix_max': 1, 'two_pointers': 1} |
| A3 | T1.0_k10 | ['peak_split', 'prefix_suffix_max', 'two_pointers'] | 1.74 | {'peak_split': 1, 'prefix_suffix_max': 2, 'two_pointers': 2} | {'prefix_suffix_max': 9, 'two_pointers': 1} | {'prefix_suffix_max': 1, 'two_pointers': 1} |
| A3 | T1.3_k10 | ['peak_split', 'prefix_suffix_max', 'two_pointers'] | 1.79 | {'peak_split': 1, 'prefix_suffix_max': 3, 'two_pointers': 2} | {'prefix_suffix_max': 8, 'two_pointers': 2} | {'prefix_suffix_max': 3, 'two_pointers': 1} |
| A3 | per-slot idea changes across T | {'p1': {'slots_with_idea_change_across_T': 12, 'n_slots': 50}, 'k10': {'slots_with_idea_change_across_T': 12, 'n_slots': 50}} | | | | |
| B6 | T0.3_p1 | ['fixed_count_array', 'hash_count', 'sort_compare'] | 1.83 | {'fixed_count_array': 2, 'hash_count': 1, 'sort_compare': 2} | {'sort_compare': 8, 'fixed_count_array': 2} | {'sort_compare': 2, 'fixed_count_array': 1} |
| B6 | T0.7_p1 | ['fixed_count_array', 'hash_count', 'sort_compare'] | 1.72 | {'fixed_count_array': 3, 'hash_count': 1, 'sort_compare': 2} | {'sort_compare': 8, 'fixed_count_array': 2} | {'sort_compare': 2, 'fixed_count_array': 1} |
| B6 | T1.0_p1 | ['fixed_count_array', 'hash_count', 'sort_compare'] | 1.84 | {'fixed_count_array': 2, 'hash_count': 1, 'sort_compare': 2} | {'sort_compare': 8, 'fixed_count_array': 2} | {'sort_compare': 2, 'fixed_count_array': 1} |
| B6 | T1.3_p1 | ['fixed_count_array', 'hash_count', 'sort_compare'] | 1.85 | {'fixed_count_array': 5, 'hash_count': 1, 'sort_compare': 2} | {'sort_compare': 8, 'fixed_count_array': 2} | {'sort_compare': 2, 'fixed_count_array': 1} |
| B6 | T0.3_k10 | ['fixed_count_array', 'hash_count', 'sort_compare'] | 1.83 | {'fixed_count_array': 2, 'hash_count': 1, 'sort_compare': 2} | {'sort_compare': 8, 'fixed_count_array': 2} | {'sort_compare': 2, 'fixed_count_array': 1} |
| B6 | T0.7_k10 | ['fixed_count_array', 'hash_count', 'sort_compare'] | 1.72 | {'fixed_count_array': 3, 'hash_count': 1, 'sort_compare': 2} | {'sort_compare': 8, 'fixed_count_array': 2} | {'sort_compare': 2, 'fixed_count_array': 1} |
| B6 | T1.0_k10 | ['fixed_count_array', 'hash_count', 'sort_compare'] | 1.84 | {'fixed_count_array': 2, 'hash_count': 1, 'sort_compare': 2} | {'sort_compare': 8, 'fixed_count_array': 2} | {'sort_compare': 2, 'fixed_count_array': 1} |
| B6 | T1.3_k10 | ['fixed_count_array', 'hash_count', 'sort_compare'] | 1.85 | {'fixed_count_array': 5, 'hash_count': 1, 'sort_compare': 2} | {'sort_compare': 8, 'fixed_count_array': 2} | {'sort_compare': 2, 'fixed_count_array': 1} |
| B6 | per-slot idea changes across T | {'p1': {'slots_with_idea_change_across_T': 11, 'n_slots': 50}, 'k10': {'slots_with_idea_change_across_T': 11, 'n_slots': 50}} | | | | |
