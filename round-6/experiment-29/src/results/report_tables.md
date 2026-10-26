### Escape fraction per engine (alpha 2, 40 directions, each engine against its own twin)

| task | engine | twin off-default (k/n) | twin pass | screen passes | confirmed | E (Wilson 95%) | screen-level E | B |
|---|---|---|---|---|---|---|---|---|
| T10 | a W8A8 | 0/50 | 1.00 | 30/40 | 29 | 0.725 [0.57, 0.84] | 0.750 | 20 |
| T10 | b W8A16 | 0/50 | 1.00 | 28/40 | 27 | incomplete (28 screen passers below the full 30 pooled rows) | 0.700 | 20 |
| T10 | c W16A8 | 0/50 | 1.00 | 27/40 | 24 | 0.600 [0.45, 0.74] | 0.675 | weight-set B |
| T10 | d BF16 | 0/50 | 1.00 | 27/40 | 26 | 0.650 [0.50, 0.78] | 0.675 | weight-set B |
| T2 | a W8A8 | 0/50 | 1.00 | 15/40 | 8 | 0.200 [0.10, 0.35] | 0.375 | 20 |
| T2 | b W8A16 | 1/50 | 0.98 | 8/40 | 5 | 0.125 [0.05, 0.26] | 0.200 | 20 |
| T2 | c W16A8 | 1/50 | 1.00 | 8/40 | 6 | 0.150 [0.07, 0.29] | 0.200 | weight-set B |
| T2 | d BF16 | 1/50 | 0.98 | 9/40 | 6 | 0.150 [0.07, 0.29] | 0.225 | weight-set B |

### Direction-paired engine contrasts (confirmed escapes; exact McNemar, Tango 90% CI, TOST 0.1)

| task | pair | E_x | E_y | diff | n10/n01 | p (two-sided) | p Holm | 90% CI | TOST equiv. | kappa | Spearman share10 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| T10 | a-d | 0.725 | 0.650 | 0.075 | 3/0 | 0.250 | 1.000 | [0.01, 0.17] | False | 0.83 | 0.96 |
| T10 | c-d | 0.600 | 0.650 | -0.050 | 1/3 | 0.625 | 1.000 | [-0.15, 0.04] | False | 0.79 | 0.96 |
| T10 | a-c | 0.725 | 0.600 | 0.125 | 5/0 | 0.062 | – | [0.05, 0.24] | False | 0.73 | 0.95 |
| T2 | a-d | 0.200 | 0.150 | 0.050 | 4/2 | 0.688 | 1.000 | [-0.06, 0.17] | False | 0.48 | 0.87 |
| T2 | c-d | 0.150 | 0.150 | 0.000 | 2/2 | 1.000 | 1.000 | [-0.10, 0.10] | True | 0.61 | 0.90 |
| T2 | b-d | 0.125 | 0.150 | -0.025 | 0/1 | 1.000 | 1.000 | [-0.10, 0.04] | False | 0.89 | 0.83 |
| T2 | a-c | 0.200 | 0.150 | 0.050 | 4/2 | 0.688 | – | [-0.06, 0.17] | False | 0.48 | 0.81 |
| T2 | a-b | 0.200 | 0.125 | 0.075 | 5/2 | 0.453 | – | [-0.04, 0.20] | False | 0.36 | 0.91 |

### Verdict (COMMIT #0 table; literal reading leads)

- **T10: NOT_REPRODUCED_HIGH**. E(a, b, c, d) = {'a': 0.725, 'b': None, 'c': 0.6, 'd': 0.65}. Screen-level reading: NOT_REPRODUCED_HIGH with {'a': 0.75, 'b': 0.7, 'c': 0.675, 'd': 0.675}. Iteration-4 E(a), relabelled: 0.725.
- **T2: NOT_REPRODUCED_HIGH**. E(a, b, c, d) = {'a': 0.2, 'b': 0.125, 'c': 0.15, 'd': 0.15}. Screen-level reading: MIXED with {'a': 0.375, 'b': 0.2, 'c': 0.2, 'd': 0.225}. Iteration-4 E(a), relabelled: 0.2.
  - T2 feasibility reading: NOT_REPRODUCED_HIGH ({'c-d': False, '|a-c|<=0.1': True, '|b-d|<=0.1': True})
- Claim-level: {'literal': 'NOT_REPRODUCED_HIGH', 'activation_rounding_claim_both_tasks': False}

### Per-sample plan noise (exp19 slots, N = 50 per cell, absolute unit)

| task | arm | exp19 FP8 (iteration 4) | a | b | c | d |
|---|---|---|---|---|---|---|
| T10 | PN_a1 | 6/50 (0.12) | 6/50 (0.12) | 9/50 (0.18) | 4/50 (0.08) | 7/50 (0.14) |
| T10 | PN_a2 | 30/50 (0.60) | 30/50 (0.60) | 27/50 (0.54) | 22/50 (0.44) | 25/50 (0.50) |
| T2 | PN_a1 | 12/50 (0.24) | 12/50 (0.24) | 11/50 (0.22) | 11/50 (0.22) | 10/50 (0.20) |
| T2 | PN_a2 | 22/50 (0.44) | 22/50 (0.44) | 19/50 (0.38) | 18/50 (0.36) | 22/50 (0.44) |

### CRN-paired screen slots under the alpha-2 pushes (k 0-1 of all 40 directions; same direction, template, k and uniforms in both engines)

| task | pair | slots | off-default x | off-default y | discordant x:y | exact McNemar p | same label |
|---|---|---|---|---|---|---|---|
| T10 | a-d | 400 | 0.583 | 0.532 | 30:10 | 0.0022 | 0.873 |
| T10 | c-d | 400 | 0.497 | 0.532 | 9:23 | 0.02 | 0.900 |
| T10 | b-d | 399 | 0.556 | 0.531 | 17:7 | 0.064 | 0.925 |
| T10 | a-c | 400 | 0.583 | 0.497 | 45:11 | 5.4e-06 | 0.825 |
| T10 | a-b | 399 | 0.581 | 0.556 | 20:10 | 0.099 | 0.895 |
| T2 | a-d | 400 | 0.432 | 0.407 | 55:45 | 0.37 | 0.740 |
| T2 | c-d | 400 | 0.420 | 0.407 | 35:30 | 0.62 | 0.830 |
| T2 | b-d | 400 | 0.390 | 0.407 | 38:45 | 0.51 | 0.782 |
| T2 | a-c | 400 | 0.432 | 0.420 | 57:52 | 0.7 | 0.723 |
| T2 | a-b | 400 | 0.432 | 0.390 | 47:30 | 0.068 | 0.805 |

### Relabel table: earlier internal results -> the numerics class that reproduces them

| earlier result | class | deciding cells |
|---|---|---|
| C2a 40-direction escape fraction, T10 alpha 2 (iteration 4: 0.725) | **MODEL** | E(a,b,c,d) at alpha 2 on T10 = {'a': 0.725, 'b': None, 'c': 0.6, 'd': 0.65} |
| PN off-default share T10 PN_a1 (exp19 FP8: 6/50) | **MODEL** | PN shares {'a': 0.12, 'b': 0.18, 'c': 0.08, 'd': 0.14} |
| PN off-default share T10 PN_a2 (exp19 FP8: 30/50) | **MODEL** | PN shares {'a': 0.6, 'b': 0.54, 'c': 0.44, 'd': 0.5} |
| C2a 40-direction escape fraction, T2 alpha 2 (iteration 4: 0.200) | **MODEL** | E(a,b,c,d) at alpha 2 on T2 = {'a': 0.2, 'b': 0.125, 'c': 0.15, 'd': 0.15} |
| PN off-default share T2 PN_a1 (exp19 FP8: 12/50) | **MODEL** | PN shares {'a': 0.24, 'b': 0.22, 'c': 0.22, 'd': 0.2} |
| PN off-default share T2 PN_a2 (exp19 FP8: 22/50) | **MODEL** | PN shares {'a': 0.44, 'b': 0.38, 'c': 0.36, 'd': 0.44} |
| exp17 frozen-screen direction 9004 moves T2 (alpha 1) | **MODEL** | POSCTRL 9004 first-10 off-default share per engine {'a': None, 'b': 0.3, 'c': 0.4, 'd': 0.3} |
| per-slot off-default rate under the alpha-2 pushes, T10 (CRN-paired, FP8 a vs bf16 d) | **MODEL + FP8 BOOST** | a 0.583 vs d 0.532; discordant 30:10, exact McNemar p = 0.0022 |
| per-slot off-default rate under the alpha-2 pushes, T2 (CRN-paired, FP8 a vs bf16 d) | **MODEL** | a 0.432 vs d 0.407; discordant 55:45, exact McNemar p = 0.37 |
| iteration-5 bf16 PN null on T10 (1/50 at its ban-free unit, block-12 dose 0.66 x this unit) | **DOSE (not reproduced at the absolute unit)** | PN_a2 T10 at the absolute unit: d 25/50, a 30/50 |
| iteration-5: T2 loses 'movable' in bf16 | **NOT REPRODUCED at the absolute unit** | E(d) T2 alpha 2 = 6/40 confirmed escapes |
| site claim OR 5.72 | **UNTESTED HERE** | not re-run in this artifact |
| same-seed agreement 17.25/20 | **UNTESTED HERE** | not re-run in this artifact |
| C2a pi-rho (plan-subspace predictor) | **UNTESTED HERE** | not re-run in this artifact |
| C2c targeted runner-up pushes | **UNTESTED HERE** | not re-run in this artifact |
| decomposition u_perp / u_P | **UNTESTED HERE** | not re-run in this artifact |

### Teacher-forced diagnostics

| engine | task | mean KL(e || bf16) per token | argmax disagreement with bf16 | FIDELITY median |logprob_sum diff| vs exp22 |
|---|---|---|---|---|
| a W8A8 | T10 | 0.0036 | 0.0012 | 0.477 |
| a W8A8 | T2 | 0.0015 | 0.0003 | 0.450 |
| b W8A16 | T10 | 0.0019 | 0.0000 | 0.315 |
| b W8A16 | T2 | 0.0005 | 0.0003 | 0.703 |
| c W16A8 | T10 | 0.0017 | 0.0019 | 0.448 |
| c W16A8 | T2 | 0.0011 | 0.0021 | 0.912 |
| d BF16 | T10 | – | – | 0.383 |
| d BF16 | T2 | – | – | 0.679 |

FIDELITY rule (median under a <= 0.25 x median under d): {'T10': {'median_abs_diff_a': 0.4769960854904147, 'median_abs_diff_d': 0.38335751295574205, 'ratio': 1.2442591298464603, 'EMULATION_INFIDELITY': True}, 'T2': {'median_abs_diff_a': 0.45007940956003134, 'median_abs_diff_d': 0.6792365646956476, 'ratio': 0.6626254135209917, 'EMULATION_INFIDELITY': True}}

Induced (non-nominal) perturbation, ratio to bf16, median over blocks 13-35: {'d|T10|S': 1.0, 'd|T10|R': 1.0, 'd|T10|G': 1.0, 'd|T2|S': 1.0, 'd|T2|R': 1.0, 'd|T2|G': 1.0, 'c|T10|S': 1.008, 'c|T10|R': 1.047, 'c|T10|G': 1.118, 'c|T2|S': 1.012, 'c|T2|R': 1.043, 'c|T2|G': 1.03, 'a|T10|S': 1.006, 'a|T10|R': 1.045, 'a|T10|G': 1.13, 'a|T2|S': 1.004, 'a|T2|R': 1.048, 'a|T2|G': 1.028, 'b|T10|S': 0.999, 'b|T10|R': 0.998, 'b|T10|G': 1.006, 'b|T2|S': 0.997, 'b|T2|R': 1.001, 'b|T2|G': 0.995}

### Nearest known solution (corpus: 18237 code solutions from the declared dataset)

| engine/task | distinct correct off-default + 'other' programs | median max Jaccard | classes |
|---|---|---|---|
| a / T10 | 229 | 0.297 | {'VARIANT': 162, 'DISTANT': 64, 'KNOWN-CLOSE': 3} |
| a / T2 | 237 | 0.209 | {'DISTANT': 212, 'VARIANT': 25} |
| b / T10 | 186 | 0.291 | {'VARIANT': 137, 'DISTANT': 47, 'KNOWN-CLOSE': 2} |
| b / T2 | 162 | 0.215 | {'DISTANT': 148, 'VARIANT': 14} |
| c / T10 | 159 | 0.304 | {'DISTANT': 32, 'VARIANT': 123, 'KNOWN-CLOSE': 4} |
| c / T2 | 128 | 0.214 | {'DISTANT': 112, 'VARIANT': 16} |
| d / T10 | 185 | 0.302 | {'VARIANT': 136, 'DISTANT': 46, 'KNOWN-CLOSE': 3} |
| d / T2 | 134 | 0.214 | {'DISTANT': 120, 'VARIANT': 14} |
