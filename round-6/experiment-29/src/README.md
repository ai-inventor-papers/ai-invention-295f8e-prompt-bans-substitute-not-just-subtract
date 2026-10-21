# Did 8-bit arithmetic cause the nudge effect? (artifact E, iteration 6)

In iteration 4, per-sample **plan noise** (PN) moved Qwen3-8B off its default algorithm on two tasks:

- T10 (connected components): 60% of samples, versus 0% for the clean twin;
- T2 (weighted shortest path): 54%.

PN is one fresh isotropic direction per sample, added at the task-specification positions of decoder blocks 12–23
during the prompt prefill. Those runs used an FP8 (e4m3) W8A8 engine. In iteration 5, the same knob under bf16 was
almost inert (T10 0.02, T2 0.04). This artifact asks whether the **arithmetic precision** caused the effect.

## Design

It holds fixed everything iteration 4 used:

- exp19's prompts and per-sample PN seeds;
- exp22's 40 fixed directions;
- the logged per-position ban units n[l,p];
- exp19's hook code (`src/hooks.py`, sha256-identical);
- the inverse-CDF CRN uniform streams;
- the 1,024-token cap;
- exp19's batch shape (B = 20, exp19's pairs).

Only the precision of the 252 decoder linears varies, in a 2x2 factorial:

| cell | weights | activations | backend |
|---|---|---|---|
| **W16A16** (baseline: the iteration-5 engine) | bf16 | bf16 | HF native `nn.Linear` |
| W16A8 | bf16 | e4m3 per row | EMU |
| W8A16 | e4m3 per output channel | bf16 | EMU |
| **W8A8** (iteration 4's numerics) | e4m3 per output channel | e4m3 per row | EMU |
| W8A8REAL (sm_89 only) | e4m3 | e4m3 | exp19's `FP8Linear` (`torch._scaled_mm`) unchanged |

- **EMU** is exact e4m3 quantise-dequantise using exp19's own quantisers, applied to exact-valued bf16 operands. It
  runs `torch.mm(out_dtype=float32)` with fp32 accumulation, applies both scales in fp32 and casts to bf16 once. The
  quantisers switch on or off; the backend stays the same.
- A kernel-only floor (`W16A16mm`: the EMU GEMM path with quantisers off) is measured in the readouts.
- Tasks: T10 and T2 are decisive; T03 (k-th smallest) is the positive control.
- Arms per precision:
  - TWIN, PN alpha 0.5 / 1 / 2: N 50 each, exp19's exact slots;
  - the 40 exp22 directions at alpha 2: N 10 each;
  - a unit cross: PN seeds at the ban-free unit, W8A8 and W16A16;
  - a dither probe: W16A16 plus uniform noise matched element by element to the e4m3 rounding step, without and with
    PN alpha 2.
- Mechanism readouts use forward passes only, at batch 1:
  - FP8 scale changes and the re-rounding gain;
  - per-block divergence travel and the kernel floor;
  - KL at R and teacher-forced KL over 32 tokens.
- Outcome: **Y_correct** = passed AND label not in {default, invalid}.
- Every contrast is paired by CRN slot and tested with an exact McNemar test.
- Predictions, thresholds, the attribution rule, outcome definitions and the analysis code were sha256
  hash-chained in `commitments.log` (commit #0, 2026-10-21T20:32:48Z) before the first decisive sample.

Hardware: one NVIDIA L4 (sm_89, 23 GB), so the REAL FP8 path was available. Deviations from the plan are listed in
`results/deviations.jsonl`.

## Results

### Interpretation

1. **The 8-bit arithmetic did not cause the effect.** On identical inputs, plan noise at alpha 2 moves W16A16 (the iteration-5 bf16 engine) almost as much as W8A8. T10: 0.50 vs 0.58 (exact McNemar p 0.22). T2: 0.18 vs 0.20 (p 1). The frozen rule returns NO PRECISION EFFECT, and so does REAL (exp19's own FP8 kernel). There is no activation or weight main effect at this N: pooled AME 0.00, WME 0.04.
2. **A small, real FP8 increment on T10 only.** Over the 40 fixed directions, W8A8 sits above W16A16 by 0.06 per direction (Wilcoxon p 0.002; Spearman 0.93; identical escape sets, Jaccard 1.00). The T10 weight main effect is 0.07 with 95% CI [0.01, 0.14]. This is an order of magnitude below the iteration-4 to iteration-5 gap.
3. **The dose unit explains iteration 5's collapse.** With the same PN seeds and slots, replacing the logged ban unit n[l,p] by the ban-free unit (||h_twin|| x r_Q) drops T10 from 0.50 to 0.10 under W16A16 (McNemar 21:1, p 1.1e-05) and from 0.58 to 0.10 under W8A8. T2 drops from 0.18 to 0.02 (p 0.021); the frozen decision text labels T2 MIXED only because its ban-unit share is below the coded 0.20 'high' threshold.
   The two units have the same mean of per-position ratios (exp27 reported 0.99), but not the same dose. The ban unit concentrates displacement at a few spec positions, with a coefficient of variation of about 1 across positions against about 0.1 for the ban-free unit. Its mean realised displacement at block 12 is 13.8 against 9.1, a ratio to the residual of 0.21 against 0.14. See results/posthoc.json, unit_profile.
4. **POST-HOC: iteration 5 is reproduced exactly in this engine.** The run used exp27's PN5 seeds and its per-template ban-free unit. W16A16 gives T10 0.02, where exp27 had 0.02, with per-slot label agreement 1.00. T2 gives 0.06 against 0.04 (agreement 0.96). W8A8 at the same settings stays low: T10 0.04, T2 0.08. So iteration 5's batch path and seeds do not matter either; the unit does.
5. **Consequence (frozen rule).** The iteration-4 internal claims are restored as properties of the model under the ban-unit dose, not of the FP8 engine. Iteration 5's 'matched dose' comparison was not matched. T03 moves under every precision, every precision lands on the base runner-up (T10 dfs, T2 Bellman-Ford/SPFA, T03 quickselect), and dither neither creates nor removes movability. The dither readings in the table were written for the predicted W8A8 >> W16A16 case; here W16A16 already moves, so dither has nothing to explain.

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

### POST-HOC (not pre-registered): replicating iteration 5's PN cells in this engine

- T10 W16A16|IT5_a2: Y_correct 0.02 (N 50); exp27 on the same slots 0.02; per-slot label agreement with exp27 1.00
- T10 W8A8|IT5_a2: Y_correct 0.04 (N 50); exp27 on the same slots 0.02; per-slot label agreement with exp27 0.98
- T10 W16A16|IT5_a1: Y_correct 0.02 (N 50); exp27 on the same slots 0.02; per-slot label agreement with exp27 1.00
- T10 W16A16_PN_a2_vs_PNF_a2: 0.50 vs 0.10 (McNemar p 1.1e-05, n 50)
- T10 W16A16_PN_a2_vs_IT5_a2: 0.50 vs 0.02 (McNemar p 8e-07, n 50)
- T10 W8A8_vs_W16A16_IT5_a2: 0.04 vs 0.02 (McNemar p 1, n 50)
- T2 W16A16|IT5_a2: Y_correct 0.06 (N 50); exp27 on the same slots 0.04; per-slot label agreement with exp27 0.96
- T2 W8A8|IT5_a2: Y_correct 0.08 (N 50); exp27 on the same slots 0.04; per-slot label agreement with exp27 0.88
- T2 W16A16|IT5_a1: Y_correct 0.00 (N 50); exp27 on the same slots 0.00; per-slot label agreement with exp27 1.00
- T2 W16A16_PN_a2_vs_PNF_a2: 0.18 vs 0.02 (McNemar p 0.021, n 50)
- T2 W16A16_PN_a2_vs_IT5_a2: 0.18 vs 0.06 (McNemar p 0.15, n 50)
- T2 W8A8_vs_W16A16_IT5_a2: 0.08 vs 0.06 (McNemar p 1, n 50)

## Layout

| path | what |
|---|---|
| `method.py` | entry point; runs every stage in order (`uv run method.py --stage all`) |
| `run_gpu_pipeline.sh`, `run_posthoc.sh` | GPU generation queue, then readouts; the post-hoc iteration-5 replication cells |
| `src/cfg.py`, `engine_v4.py`, `hooks.py`, `sampling_v4.py`, `prompts_v4.py`, `label_worker_v4.py`, `commit.py` | exp19's modules copied unchanged |
| `src/cfg_e.py` | this artifact's constants and arm definitions |
| `src/qlinear.py` | e4m3 quantisers (exp19's, op for op), `QLinear` (EMU) and the family manager (W16 / W8 / REAL) |
| `src/engine_e.py` | wrapper around exp19's prefill / sample / TaskContext; one fixed batch shape; per-row precision log |
| `src/dither.py` | dither pre-hooks on the native W16A16 linears |
| `src/run_e.py` | device rule + memory probe, GPU tests, smoke run, the resumable generation queue, readouts |
| `src/tests_gpu.py`, `src/tests_cpu.py` | GPU tests U1–U8 and CPU tests 1–8 |
| `src/readouts.py` | Stage F mechanism readouts |
| `src/label_e.py` | wraps exp19's labeller; Stage A.2 labeller re-check |
| `src/stage_a.py`, `src/commit_e.py`, `src/commit0.py`, `src/commit1.py` | inputs + sha256, iteration-4 reference numbers, prompt diff; hash chain; commits #0 and #1 |
| `src/analysis_e.py` | Stage G statistics (committed before the decisive samples) |
| `src/posthoc_e.py` | POST-HOC iteration-5 replication and unit decomposition |
| `src/novelty_e.py`, `src/dep_usage_e.py` | blind two-judge novelty audit; use of dependency art_j3Rm_lr2nzR6 |
| `src/rederive_e.py` | independent re-derivation (stdlib + numpy), placebos, commit-chain and prompt audits |
| `src/figures_e.py`, `src/report_e.py`, `src/outputs_e.py`, `src/write_readme.py` | figures F1–F9, `results/summary.md`, `method_out.json`, this README |
| `data/samples_raw.jsonl` | every generated program (token ids, text) with precision, kernel, batch shape, hook sha256 |
| `data/labels.jsonl`, `data/samples.jsonl` | labels; merged per-row output (plan PER-ROW OUTPUT, no token ids) |
| `data/realised.jsonl` | realised displacement per pushed prefill |
| `results/` | every analysis JSON, tests, gate checks, timing, readout summaries (`readouts_slots.jsonl`) |
| `predictions/` | `e_inputs.json`, `e_commit.json` (commit #0), `commit1_gate.json`, `device_rule.json`, `landing_ref.json` |
| `commitments.log` | sha256 hash chain (genesis sha256('iter6_E')) |
| `figures/` | F1–F9 as PDF + PNG |
| `inputs/` | sha256-verified read-only copies of exp19, exp22, exp23, exp24, exp25, exp27, exp18 and exp19's inputs |
| `states/` | clean residual states (blocks 11/17/23/29/35, bf16) per task, template and precision (kept on the run volume, not published) |
| `method_out.json`, `full_/mini_/preview_method_out.json` | exp_gen_sol_out output (per-program predictions per precision; all analyses in `metadata`) |

## How to run

```bash
uv sync --frozen
huggingface-cli download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218
uv run method.py --stage all      # about 2.5 GPU-hours on an L4; 'post' re-runs the CPU analysis only
```

`reproducibility.md` lists every command in the order it was run, with seeds and hardware.

## Restoring removed files

Every `delete` entry of `.aii/manifest.yaml` and the command that brings it back:

| removed path | how to restore |
|---|---|
| `.venv/` | `uv sync --frozen` |
| `src/__pycache__/` | `uv run src/stage_a.py` (any script under `src/` recreates the bytecode cache) |
| `inputs/exp11/bench/__pycache__/` | `uv run src/label_e.py --recheck` (recreated when the bench labeller is imported) |
| `inputs/exp11/bench/common/__pycache__/` | `uv run src/label_e.py --recheck` |
| `inputs/exp8/suite/__pycache__/` | `uv run src/label_e.py --recheck` (recreated when the path-task labeller is imported) |
| `inputs/exp8/suite/labeller/__pycache__/` | `uv run src/label_e.py --recheck` |
| `inputs/exp8/suite/tasks/__pycache__/` | `uv run src/label_e.py --recheck` |

The model weights are not stored in this folder. They live in the shared Hugging Face cache; restore them with
`huggingface-cli download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218`.

`states/` (clean residual states from the readouts, about 7 MB per file) stays on the run's storage volume and is
not published to the repository.
