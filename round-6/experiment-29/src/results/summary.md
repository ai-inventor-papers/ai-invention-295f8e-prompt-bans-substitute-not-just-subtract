**Verdict (EMU, frozen rule): NO PRECISION EFFECT**; pooled attribution class: **MIXED**; REAL-kernel verdict: NO PRECISION EFFECT or AMBIGUOUS.

Consequence (frozen text): The unit cross locates the iteration-5 shrinkage and the iteration-4 claims are restored as model properties.

### Primary contrast: PN alpha 2, W8A8 (EMU) vs W16A16, paired CRN slots

| Task | W8A8 | W16A16 | diff [slot-bootstrap 95% CI] | discordant (W8A8 only : W16A16 only) | exact McNemar p | REAL in place of EMU: diff, p |
|---|---|---|---|---|---|---|
| T10 | 0.58 | 0.50 | 0.08 [0.00, 0.18] | 5 : 1 | 0.22 | 0.06, 0.45 |
| T2 | 0.20 | 0.18 | 0.02 [-0.12, 0.14] | 6 : 5 | 1 | 0.04, 0.75 |

### Correct off-default share (Y_correct) per cell, N = 50 paired slots

| Task | Arm | W16A16 | W16A8 | W8A16 | W8A8 | W8A8REAL | iteration 4 (exp19) | iteration 5 (exp27, bf16) |
|---|---|---|---|---|---|---|---|---|
| T10 | TWIN | 0.00 (n 50, pass 1.00) | 0.04 (n 50, pass 1.00) | 0.00 (n 50, pass 1.00) | 0.00 (n 50, pass 1.00) | 0.00 (n 50, pass 1.00) | 0.00 | 0.00 |
| T10 | PN_a0.5 | 0.02 (n 50, pass 0.98) | 0.06 (n 50, pass 1.00) | 0.02 (n 50, pass 1.00) | 0.02 (n 50, pass 1.00) | 0.02 (n 50, pass 1.00) | 0.00 | – |
| T10 | PN_a1 | 0.12 (n 50, pass 1.00) | 0.16 (n 50, pass 1.00) | 0.20 (n 50, pass 1.00) | 0.18 (n 50, pass 1.00) | 0.16 (n 50, pass 1.00) | 0.12 | 0.02 |
| T10 | PN_a2 | 0.50 (n 50, pass 0.98) | 0.46 (n 50, pass 0.98) | 0.52 (n 50, pass 1.00) | 0.58 (n 50, pass 1.00) | 0.56 (n 50, pass 1.00) | 0.60 | 0.02 |
| T10 | POP40_a2 | 0.49 (n 400, pass 0.96) | 0.49 (n 400, pass 0.95) | 0.53 (n 400, pass 0.96) | 0.56 (n 400, pass 0.96) | – | – | – |
| T2 | TWIN | 0.00 (n 50, pass 0.98) | 0.00 (n 50, pass 0.98) | 0.00 (n 50, pass 0.98) | 0.02 (n 50, pass 0.98) | 0.00 (n 50, pass 1.00) | 0.00 | 0.00 |
| T2 | PN_a0.5 | 0.00 (n 50, pass 0.92) | 0.02 (n 50, pass 0.98) | 0.08 (n 50, pass 0.96) | 0.06 (n 50, pass 0.96) | 0.04 (n 50, pass 0.94) | 0.06 | – |
| T2 | PN_a1 | 0.12 (n 50, pass 0.84) | 0.14 (n 50, pass 0.86) | 0.14 (n 50, pass 0.84) | 0.18 (n 50, pass 0.84) | 0.12 (n 50, pass 0.84) | 0.18 | 0.00 |
| T2 | PN_a2 | 0.18 (n 50, pass 0.68) | 0.16 (n 50, pass 0.64) | 0.18 (n 50, pass 0.72) | 0.20 (n 50, pass 0.74) | 0.22 (n 50, pass 0.64) | 0.30 | 0.04 |
| T2 | POP40_a2 | 0.20 (n 400, pass 0.73) | 0.21 (n 400, pass 0.74) | 0.19 (n 400, pass 0.75) | 0.20 (n 400, pass 0.77) | – | – | – |
| T03 | TWIN | 0.00 (n 50, pass 1.00) | 0.04 (n 50, pass 1.00) | 0.00 (n 50, pass 1.00) | 0.02 (n 50, pass 1.00) | 0.00 (n 50, pass 1.00) | 0.00 | 0.02 |
| T03 | PN_a0.5 | 0.08 (n 50, pass 1.00) | 0.10 (n 50, pass 1.00) | 0.08 (n 50, pass 1.00) | 0.06 (n 50, pass 1.00) | 0.08 (n 50, pass 1.00) | 0.08 | – |
| T03 | PN_a1 | 0.36 (n 50, pass 0.98) | 0.38 (n 50, pass 1.00) | 0.28 (n 50, pass 0.96) | 0.30 (n 50, pass 0.98) | 0.22 (n 50, pass 0.98) | 0.28 | 0.08 |
| T03 | PN_a2 | 0.62 (n 50, pass 0.96) | 0.60 (n 50, pass 0.98) | 0.52 (n 50, pass 0.96) | 0.48 (n 50, pass 1.00) | 0.54 (n 50, pass 0.96) | 0.46 | 0.28 |
| T03 | POP40_a2 | – | – | – | – | – | – | – |

### Attribution (PN alpha 2; AME = activation main effect, WME = weight main effect)

| Scope | AME [95% CI] | WME [95% CI] | INT [95% CI] | verdict | MDE(AME) |
|---|---|---|---|---|---|
| T10 | 0.01 [-0.03, 0.06] | 0.07 [0.01, 0.14] | 0.10 [0.02, 0.18] | MIXED | 0.06 |
| T2 | 0.00 [-0.08, 0.07] | 0.02 [-0.09, 0.14] | 0.04 [-0.10, 0.18] | MIXED | 0.11 |
| pooled | 0.00 [-0.04, 0.05] | 0.04 [-0.02, 0.12] | 0.07 [-0.01, 0.16] | MIXED | 0.06 |

### Population check (40 fixed directions, alpha 2)

- T10: W8A8: escape 0.72 (mean share 0.56, n dirs 40); W8A16: escape 0.72 (mean share 0.53, n dirs 40); W16A16: escape 0.72 (mean share 0.49, n dirs 40); W16A8: escape 0.62 (mean share 0.49, n dirs 40)
  - W8A8 vs W16A16 per direction: mean diff 0.06, Wilcoxon p 0.002, Spearman 0.93, Jaccard of escape sets 1.00
  - population attribution: AME 0.01, WME 0.05 -> MIXED
  - W8A8 vs exp22 (iteration 4) per-direction shares: mean 0.56 vs 0.54, Spearman 0.94
- T2: W8A8: escape 0.17 (mean share 0.20, n dirs 40); W8A16: escape 0.25 (mean share 0.19, n dirs 40); W16A16: escape 0.12 (mean share 0.19, n dirs 40); W16A8: escape 0.33 (mean share 0.21, n dirs 40)
  - W8A8 vs W16A16 per direction: mean diff 0.01, Wilcoxon p 0.720, Spearman 0.69, Jaccard of escape sets 0.20
  - population attribution: AME 0.02, WME -0.01 -> MIXED
  - W8A8 vs exp22 (iteration 4) per-direction shares: mean 0.20 vs 0.21, Spearman 0.79

### Unit cross, T03 control, dither

- Unit cross T10: W8A8|ban 0.58, W8A8|banfree 0.10, W16A16|ban 0.50, W16A16|banfree 0.10. Decision: UNIT: W16A16 high at the ban unit, low at the ban-free unit
- Unit cross T2: W8A8|ban 0.20, W8A8|banfree 0.04, W16A16|ban 0.18, W16A16|banfree 0.02. Decision: MIXED: no single factor reproduces the pattern
- T03 positive control (PN alpha 2 minus twin >= 0.10): W8A8 moves, W8A16 moves, W16A8 moves, W16A16 moves, W8A8REAL moves
- Dither v1 T10: dither-PN2 0.48 vs W16A16 PN2 0.50 (p 1); dither-twin 0.00. neither: independent rounding-sized noise does not recreate W8A8's movability; deterministic re-rounding (not independent noise) or something else carries it (a dither null does NOT rule out quantisation)
- Dither v2 T10: dither-PN2 0.52 vs W16A16 PN2 0.50 (p 1); dither-twin 0.00. neither: independent rounding-sized noise does not recreate W8A8's movability; deterministic re-rounding (not independent noise) or something else carries it (a dither null does NOT rule out quantisation)
- Dither v1 T2: dither-PN2 0.20 vs W16A16 PN2 0.18 (p 1); dither-twin 0.02. neither: independent rounding-sized noise does not recreate W8A8's movability; deterministic re-rounding (not independent noise) or something else carries it (a dither null does NOT rule out quantisation)
- Dither v2 T2: dither-PN2 0.16 vs W16A16 PN2 0.18 (p 1); dither-twin 0.00. neither: independent rounding-sized noise does not recreate W8A8's movability; deterministic re-rounding (not independent noise) or something else carries it (a dither null does NOT rule out quantisation)

### Engine checks

- EMU gate (25 T2 twin slots): byte identity 0.76, label agreement 0.96 (pass = True).
- REAL (exp19 FP8Linear on the L4) vs exp19 (RTX 2000 Ada): byte identity 0.76, label agreement 1.00; all REAL rows: 0.55 byte-identical.
- W16A16 anchor vs exp27 (25 T10 twin slots): byte identity 0.80, label agreement 1.00.
- Prompt diff exp19 vs iteration 5: 15/15 twin prompts identical.

### Mechanism readouts (forward passes, batch 1, 50 PN alpha-2 slots per task)

- T10|W16A16: KL at R 0.0000, teacher-forced KL (32 tokens) 0.1708, argmax at R changed 0.00, divergence at R block 35 7.982
- T10|W16A16mm: KL at R 0.0000, teacher-forced KL (32 tokens) 0.1666, argmax at R changed 0.00, divergence at R block 35 7.972
- T10|W16A8: KL at R 0.0000, teacher-forced KL (32 tokens) 0.1847, argmax at R changed 0.00, divergence at R block 35 8.367
- T10|W8A16: KL at R 0.0000, teacher-forced KL (32 tokens) 0.1927, argmax at R changed 0.00, divergence at R block 35 7.878
- T10|W8A8: KL at R 0.0000, teacher-forced KL (32 tokens) 0.2089, argmax at R changed 0.00, divergence at R block 35 8.219
- T10|W8A8REAL: KL at R 0.0000, teacher-forced KL (32 tokens) 0.2115, argmax at R changed 0.00, divergence at R block 35 8.173
- T2|W16A16: KL at R 0.0000, teacher-forced KL (32 tokens) 0.4234, argmax at R changed 0.00, divergence at R block 35 6.494
- T2|W16A16mm: KL at R 0.0000, teacher-forced KL (32 tokens) 0.4088, argmax at R changed 0.00, divergence at R block 35 6.502
- T2|W16A8: KL at R 0.0000, teacher-forced KL (32 tokens) 0.4291, argmax at R changed 0.00, divergence at R block 35 6.730
- T2|W8A16: KL at R 0.0000, teacher-forced KL (32 tokens) 0.4053, argmax at R changed 0.00, divergence at R block 35 6.473
- T2|W8A8: KL at R 0.0000, teacher-forced KL (32 tokens) 0.4205, argmax at R changed 0.00, divergence at R block 35 6.707
- T2|W8A8REAL: KL at R 0.0000, teacher-forced KL (32 tokens) 0.3975, argmax at R changed 0.00, divergence at R block 35 6.683
- clean-vs-clean relative divergence T10|W16A16mm_vs_W16A16: b11 0.0107, b17 0.0133, b23 0.0140, b29 0.0135, b35 0.0137
- clean-vs-clean relative divergence T10|W16A8_vs_W16A16: b11 0.0383, b17 0.0463, b23 0.0478, b29 0.0454, b35 0.0438
- clean-vs-clean relative divergence T10|W8A16_vs_W16A16: b11 0.0400, b17 0.0477, b23 0.0507, b29 0.0481, b35 0.0468
- clean-vs-clean relative divergence T10|W8A8_vs_W16A16: b11 0.0542, b17 0.0654, b23 0.0675, b29 0.0637, b35 0.0623
- clean-vs-clean relative divergence T10|W8A8REAL_vs_W16A16: b11 0.0540, b17 0.0654, b23 0.0686, b29 0.0645, b35 0.0624
- clean-vs-clean relative divergence T2|W16A16mm_vs_W16A16: b11 0.0119, b17 0.0154, b23 0.0163, b29 0.0154, b35 0.0163
- clean-vs-clean relative divergence T2|W16A8_vs_W16A16: b11 0.0392, b17 0.0486, b23 0.0492, b29 0.0460, b35 0.0457
- clean-vs-clean relative divergence T2|W8A16_vs_W16A16: b11 0.0413, b17 0.0495, b23 0.0506, b29 0.0475, b35 0.0468
- clean-vs-clean relative divergence T2|W8A8_vs_W16A16: b11 0.0554, b17 0.0681, b23 0.0692, b29 0.0652, b35 0.0641
- clean-vs-clean relative divergence T2|W8A8REAL_vs_W16A16: b11 0.0554, b17 0.0671, b23 0.0678, b29 0.0636, b35 0.0627

Novelty audit: no correct novel algorithm (0 of 10; rule-of-three 95% upper bound 0.300) (spend 0.01036 USD).
Independent re-derivation: 0 mismatches over 81 checks; commit chain: {'lines': 20, 'breaks': 0, 'commit0_utc': '2026-10-21T20:32:48.457437Z', 'first_factorial_row_utc': '2026-10-21T20:38:41.497727Z', 'no_decisive_row_before_commit0': True}.
