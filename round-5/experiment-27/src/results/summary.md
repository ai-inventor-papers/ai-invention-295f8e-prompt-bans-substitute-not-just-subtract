### Claim F — the literal cell (T2, thinking on, top-k 10, same seed, T ∈ {0.3, 0.7, 1.0, 1.3})

- **C_T = 0 of 20 seeds** change their final-code algorithm across temperature (Clopper-Pearson one-sided 95% upper bound 0.14); the committed prediction C_T ≤ 1 is met.
- First approach named in the thinking: 0 of 20 seeds change.

| T | completed | final labels (completed) | first approach | median think tokens | Dijkstra style |
|---|---|---|---|---|---|
| LIT_T0.3 | 20/20 | {'dijkstra': 20} | {'dijkstra': 20} | 3754.50 | {'heap': 20} |
| LIT_T0.7 | 20/20 | {'dijkstra': 20} | {'dijkstra': 20} | 3962.00 | {'heap': 20} |
| LIT_T1.0 | 20/20 | {'dijkstra': 20} | {'dijkstra': 20} | 3576.00 | {'heap': 20} |
| LIT_T1.3 | 20/20 | {'dijkstra': 20} | {'dijkstra': 20} | 4149.00 | {'heap': 20} |
| LIT_REP_T0.7 | 20/20 | {'dijkstra': 20} | {'dijkstra': 20} | 3500.00 | {'heap': 20} |

- Noise floor (T 0.7 vs its repeat, same seed): byte-identical thinking 4/20, label agreement 1.00, median common prefix 309.50 tokens.
- Paired with exp21's top-p-1 traces at the same (seed, T): label agreement 1.00 on 100 pairs; median common token prefix 34.00 tokens (top-k 10 vs top-k 0 diverge early, yet the algorithm never changes).
- Lexicon audit: judge agreement 1.00 on 19 traces.

### Claim C — plan noise vs text-level plan samplers: **DISCONFIRMED** (PN wins 1 of 5 decisive tasks; threshold 3)

| Task | H5 PN | H5 IFG | H5 PSL-lite | H5 EAP | H5 BINT | best text | PN wins | P(PN ≥ best) | flag | H5 DMD |
|---|---|---|---|---|---|---|---|---|---|---|
| T03 | 1.98 | 1.19 | 1.09 | 1.83 | 1.73 | EAP | yes | 0.58 | UNRESOLVED | 1.10 |
| T10 | 1.09 | 1.96 | 1.50 | 1.88 | 2.53 | BINT | no | 0.00 |  | 1.25 |
| T2 | 1.18 | 1.00 | 1.07 | 1.24 | 1.45 | BINT | no | 0.06 |  | 1.09 |
| T05 | 1.17 | 1.00 | 1.00 | 1.27 | 1.61 | BINT | no | 0.01 |  | 1.00 |
| T1 | 1.06 | 1.00 | 1.00 | 1.08 | 1.04 | EAP | no | 0.38 | UNRESOLVED | 1.00 |

D̄ = mean(H5_PN − best_text) = -0.40, 95% CI ['-0.70', '-0.24']; replicate win-count distribution {'1': 983, '2': 486, '0': 495, '3': 35, '4': 1} (2000 replicates).

| Sensitivity | verdict | wins | D̄ |
|---|---|---|---|
| IFG_hot_only | DISCONFIRMED | 1/5 | -0.40 |
| PN_plus | DISCONFIRMED | 2/5 | -0.40 |
| edge_restricted_hull | DISCONFIRMED | 1/5 | -0.40 |
| leftpad_arms_dropped | SUPPORTED | 4/5 | 0.07 |
| style_regate_flagged_excluded | DISCONFIRMED | 1/5 | -0.40 |
| novelty_audit_relabelled | DISCONFIRMED | 1/5 | -0.40 |

### PN vs departure-matched decoding (DMD), correct off-default share of N

| Task | α | T_dmd | K_PN | f_on | PN | DMD | TWIN | McNemar PN vs DMD (PN-only/DMD-only, p) |
|---|---|---|---|---|---|---|---|---|
| T03 | 1 | 1.46 | 0.0179 | 0.0200 | 0.08 | 0.02 | 0.02 | 3/0, p=0.25 |
| T03 | 2 | 1.64 | 0.0774 | 0.0707 | 0.28 | 0.02 | 0.02 | 13/0, p=0.000244 |
| T10 | 1 | 1.84 | 0.0096 | 0.0110 | 0.02 | 0.04 | 0.00 | 1/2, p=1 |
| T10 | 2 | 2.22 | 0.0333 | 0.0370 | 0.02 | 0.06 | 0.00 | 1/3, p=0.625 |
| T2 | 1 | 2.01 | 0.0254 | 0.0244 | 0.00 | 0.02 | 0.00 | 0/1, p=1 |
| T2 | 2 | 2.66 | 0.1113 | 0.1230 | 0.04 | 0.00 | 0.00 | 2/0, p=0.5 |
| T05 | 1 | 1.52 | 0.0036 | 0.0039 | 0.00 | 0.00 | 0.00 | 0/0, p=1 |
| T05 | 2 | 1.81 | 0.0100 | 0.0104 | 0.04 | 0.00 | 0.00 | 2/0, p=0.5 |
| T1 | 1 | 2.15 | 0.0505 | 0.0442 | 0.00 | 0.00 | 0.00 | 0/0, p=1 |
| T1 | 2 | 2.47 | 0.1554 | 0.1246 | 0.02 | 0.00 | 0.00 | 1/0, p=1 |

Pooled exact test over D5: {'1': {'PN_only': 4, 'DMD_only': 3, 'p_exact': 1.0}, '2': {'PN_only': 19, 'DMD_only': 3, 'p_exact': 0.0008554458618164062}}

### PN plain vs PN twin (same direction, same stream)

| Task | PN plain-only / PN twin-only (p) | pass plain | pass twin | Hill plain | Hill twin |
|---|---|---|---|---|---|
| T03 | 0/3 (p=0.25) | 1.00 | 0.98 | 1.09 | 1.33 |
| T10 | 0/1 (p=1) | 1.00 | 1.00 | 1.00 | 1.09 |
| T2 | 0/0 (p=1) | 1.00 | 1.00 | 1.00 | 1.00 |
| T05 | 0/0 (p=1) | 1.00 | 1.00 | 1.00 | 1.00 |
| T1 | 0/0 (p=1) | 0.86 | 0.80 | 1.00 | 1.00 |
| T04 | 0/0 (p=1) | 1.00 | 1.00 | 1.00 | 1.00 |
| T06 | 0/0 (p=1) | 1.00 | 1.00 | 1.00 | 1.00 |
| T08 | 0/0 (p=1) | 0.97 | 1.00 | 1.00 | 1.00 |
| T11 | 0/0 (p=1) | 1.00 | 1.00 | 1.00 | 1.00 |
| T13 | 0/0 (p=1) | 1.00 | 1.00 | 1.00 | 1.00 |
| T14 | 0/0 (p=1) | 0.73 | 0.80 | 1.00 | 1.00 |
| R1 | 0/0 (p=1) | 0.90 | 0.87 | 1.00 | 1.00 |
| R2 | 0/0 (p=1) | 0.80 | 0.87 | 1.00 | 1.00 |
| R3 | 0/0 (p=1) | 1.00 | 1.00 | 1.00 | 1.00 |
| R6 | 0/1 (p=1) | 0.90 | 0.87 | 1.00 | 1.17 |

### Engine check (bf16 here vs exp19's FP8 W8A8): **PRECISION-SENSITIVE**

| Cell | byte-identical | per-slot label agreement | JSD | null p95 |
|---|---|---|---|---|
| T03|NEUTRAL | 45/50 | 1.00 | 0.00 | 0.00 |
| T03|RAND9002_a1.0 | 32/50 | 0.74 | 0.03 | 0.15 |
| T2|NEUTRAL | 35/50 | 0.98 | 0.01 | 0.00 |
| T2|RAND9004_a1.0 | 10/50 | 0.86 | 0.01 | 0.01 |
| T03|T1.3 | 0/10 | 1.00 | 0.00 | – |
| T03|TOPK10 | 0/10 | 1.00 | 0.00 | – |
| T2|T1.3 | 0/10 | 0.90 | 0.05 | – |
| T2|TOPK10 | 0/10 | 0.90 | 0.05 | – |

- Novelty audit: 12 unique correct 'other' programs, classes {'LABELLER MISS': 10, 'null': 1, 'DEGENERATE': 1}; novel = 0.
- Style re-gate: 250 programs; flagged tasks ['T14']; per-task agreement {'T03': '1.00', 'T2': '1.00', 'T10': '1.00', 'T05': '1.00', 'T1': '1.00', 'T04': '1.00', 'T06': '1.00', 'T08': '0.90', 'T11': '0.90', 'T13': '1.00', 'T14': '0.80', 'R1': '1.00', 'R2': '1.00', 'R3': '1.00', 'R6': '0.90'}.
- GPU: 8576 HF rows in 1.88 GPU-hours of batch time + literal cell 15.11 min on vLLM; OpenRouter spend USD 0.12.
