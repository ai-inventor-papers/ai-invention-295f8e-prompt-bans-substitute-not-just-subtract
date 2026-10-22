## Results in more detail

### S0/S1: engine, unit tests, U6

- **Unit tests.** U1 (CRN determinism), U2 (zero edit, full interchange with source = base, DAS at lambda 0, MLP and
  head targets equal to their clean values: all bit-identical) and U4 (top-k with k = vocab equals the plain sampler)
  pass.
- **U3 fails its 1e-3 tolerance.** The single-position KV-cache path differs from a full recompute by up to 0.27 nats
  on m, with or without an edit. These are bf16 kernel and batch-shape effects; Gemma carries residual channels of
  order 1e4. Every DAS dy is therefore measured against the base's own margin on the same path and in the same fixed
  batch shape, so the offset cancels (D05). The same effect (0.37 nats) appeared in the first path-patching smoke test
  and was handled with in-batch base rows (D07).
- **Engine check (twin, natural sampling, N = 50, iteration 6's keys).** 19/50 BFS (0.38; Wilson 0.26-0.52; 11
  correct; pass rate 0.80).
  - This is just outside iteration 6's CI [0.245, 0.372] for 61/200, so the check fails as pre-registered.
  - Per-slot label agreement with iteration 6's rows for the same keys is 0.94, and 56% of programs are
    byte-identical despite a different batch shape (25 vs 20).
  - Iteration 6's own share on these 50 slots is 0.36. The subset of slots, not the engine, is BFS-heavy (D16).
- **y_v.** The 120 twin variants reproduce iteration 6 exactly: mean -0.915, SD 0.674, Spearman 1.000 with
  iteration 6's y_v over 60 variants.
- **U6 re-run with diagnosis (200 continuations from the empty prefix, same CRN slots for both paths).**
  - (a) Multi-prompt right-aligned batches (iteration 6's fork-resampling path): 65/200 BFS (0.325).
  - (b) Single-prompt fixed-shape engine: 72/200 (0.36).
  - Both agree with the natural share 61/200 (Fisher p 0.75 and 0.29), so **U6 passes on both paths**. Iteration 6's
    t0 discrepancy (0.380 vs 0.305) does not reproduce.
  - Labeller: partial and full labels agree 200/200 on (a), so the partial labeller is not the cause.
  - Batching: (a) and (b) disagree on 9/200 slots, 1 vs 8, exact McNemar p = 0.039. So batching changes CRN-coupled
    programs slightly. By the rule committed in #0, G3's P(BFS | fork token) therefore comes from G3-cal (main
    engine); the iteration-6 table is the sensitivity.
- **G3-cal (prefill c* + forced fork token, N = 125 each).**

  | Fork token | BFS | Pass |
  |---|---|---|
  | `visited` | 1/125 | 124/125 |
  | blank line | 111/125 | 85/125 |
  | `if` | 122/125 | 99/125 |
  | `queue` | 125/125 | **0/125** |

  `queue` commits the model to a path-carrying list BFS (`queue = [(start, [start])]`, `queue.pop(0)`,
  `path + [...]`). It is correct in kind but too slow for the 30x30 hidden tests. **The fork token fixes the
  algorithm and also its implementation, and with it, correctness.**

### G3: the fork-margin account of temperature (predictions committed before any temperature sample)

| Cell | Predicted attempted BFS | Observed (N = 50) | Wilson 95% | P(c*) predicted / observed | Correct BFS | Pass |
|---|---|---|---|---|---|---|
| T0.3 top-p 1 | 0.015 | 1/50 = 0.02 | 0.00-0.10 | 1.00 / 1.00 | 1 | 1.00 |
| T0.7 top-p 1 | 0.166 | 12/50 = 0.24 | 0.14-0.37 | 0.96 / 0.94 | 8 | 0.92 |
| T1.0 top-p 1 | 0.323 | 17/50 = 0.34 | 0.22-0.48 | 0.88 / 0.86 | 9 | 0.80 |
| T1.3 top-p 1 | 0.450 | 23/50 = 0.46 | 0.33-0.60 | 0.78 / 0.72 | 15 | 0.80 |

- **G3-LAW holds.** |pred - obs| <= 0.10 in every top-p-1 cell (MAE 0.026, max 0.074 at T0.7), and every
  prediction lies inside its Wilson CI.
- **G3-CONC holds.** H(label | fork class) = 0.153 bits pooled (bootstrap 0.09-0.21), so the class of the token at
  index 32 nearly determines the algorithm. By temperature: 0.00 at T0.3 and T0.7, 0.24 at T1.0, 0.31 at T1.3.
- **The T1.0 -> T0.3 drop is large and paired.** 16 slots switch BFS -> DFS and none switch back (exact McNemar,
  p = 1.5e-5). 50% of slots change their algorithm somewhere across T.
- **Top-k 10 changes nothing.** The four top-k-10 cells are identical, program for program, to top-p 1, as committed
  in #1: every B/D token, and every c* token, is in the top 10, so under shared uniforms the truncated tail is never
  drawn.
- **On the user's question 1a-c.** At tight temperature the model writes one idea (DFS) almost every time. Loosening
  T does not create new ideas. It moves probability across the one fork the model already has, at the rate the fork
  logits divided by T predict.

### G2: controlled DAS at the fork (held-out templates W4/W5 x held-out sources F4/F5, 768 pairs)

- **Full-state ceiling.** Swapping the whole fork state moves the held-out margin +3.6 nats (BFS sources) at L17,
  rising to +7.4 at L22 and +8.2 to +9.1 at L25-29. DFS sources move it -1.9 at L17, -3.8 at L22, -5.2 to -5.8 at
  L24-29.
- **Layer choice.** The committed rule (argmax of rank-1 train-CV median recovery) selects **L* = 17** (CV recovery
  2.15; L19 2.07, L21 1.67, L22-29 1.07-1.20). Recovery is above 1 because a trained direction moves the margin
  further than the weak full-state swap at an early layer (D12). Absolute effects in nats are reported beside it.
- **DAS at L17 (seed median of 3; held-out).**
  - Recovery 1.99 / 2.36 / 2.58 / 2.81 for k = 1 / 2 / 4 / 8.
  - Directional dy 5.6 / 6.7 / 7.6 / 8.6 nats.
  - IIA 1.00 at every k. The smallest sufficient rank is 1, and k* = 4 (train-CV rule).
- **RAND.** 50 Haar-random subspaces give recovery 0.000 (95th percentile <= 0.02). Paired Wilcoxon (DAS > RAND)
  gives p < 1e-100 at every k.
- **SHUF.** Source labels permuted across the 24 train sources (10-14 label flips), with held-out recovery measured
  against the TRUE targets: -0.27 / -0.29 / -0.30 / -0.28 (median of 3 permutations). One permutation (10 flips)
  reaches 0.17 at k = 1, so the max over permutations is above 0.1.
- **RINIT.** A randomly initialised Gemma (same config, HF init, seed 0) with the same map class, pairs and the
  trained model's targets moves its margin 0.00 / 1.69 / 1.69 / 1.74 nats toward the targets. That is <= 0.25x the
  trained model's effect, with IIA 0.50-0.72 against 1.00.
- **G2-DAS-REAL holds at every k.** DAS - RAND >= 0.4 with Wilcoxon p < 0.01, SHUF median <= 0.1, and RINIT < 0.5x.
- **DiM.** As a rank-1 interchange direction, DiM recovers 1.00 at L17 (dy 2.8 nats) and 1.06 at L22 (dy 5.8).
- **Natural variance (Makelov) at L17.**
  - R_1 holds 0.0009 of the twin's cross-prompt variance, at the random 95th percentile (0.0010).
  - Its coordinate tracks y_v over the 120 variants with Spearman -0.50 (permutation p = 0.0005; the sign of R_1 is
    arbitrary).
  - Not dormant by the committed rule (|rho| >= 0.2), but the variance share is at chance level.
  - At L22, R_1 holds 7.7x the random share (above the 95th percentile), with Spearman -0.67.
- **Identifiability.** Seeds agree on one direction only. At L17 (k* = 4) the first principal cosine between seeds is
  0.50-0.52 and the rest are below 0.06. At L22 (k = 1) seed directions have cosine 0.21-0.23. Many directions carry
  the forced-prompt transfer. DiM sits at cosine 0.39 to R_1 at L17.
- **Wording.** By the committed rule, "one-dimensional" is not licensed: k = 1 recovery >= 0.8 holds, but |Spearman| =
  0.497 < 0.5 at L*. The permitted statement is that **a rank-k subspace at the fork carries the forced-prompt
  transfer**, controlled by RAND, SHUF and RINIT. The subspace is not unique across seeds.

### G2 dose sweep in generation (L* = 17, k* = 4; N = 50 per cell; CRN; prompt + c* prefilled; one edit at p_f)

| Cell | Attempted BFS | Correct BFS | Pass | p (correct > twin, one-sided McNemar, Holm over 6 doses) | Teacher-forced predicted attempted share |
|---|---|---|---|---|---|
| twin (no edit) | 18 | 11 | 0.86 | - | 0.26 |
| DAS lambda 0.1 | 27 | 20 | 0.86 | 0.006 | 0.47 |
| DAS lambda 0.2 | 38 | 27 | 0.78 | 4e-4 | 0.75 |
| DAS lambda 0.35 | 46 | 31 | 0.68 | 5e-5 | 0.92 |
| DAS lambda 0.5 | 47 | 37 | 0.78 | 2e-6 | 0.96 |
| DAS lambda 0.75 | 47 | 38 | 0.80 | 1e-6 | 0.96 |
| DAS lambda 1 | 47 | **42** | **0.88** | 2e-8 | 0.96 |
| DiM 0.1 (matched dy) | 30 | 15 | 0.70 | 0.87 | 0.52 |
| DiM 0.2 | 36 | 15 | 0.58 | 0.87 | 0.78 |
| DiM 0.35 | 46 | 12 | 0.32 | 1.00 | 0.95 |
| DiM 0.5 | 48 | 11 | 0.26 | 1.00 | 0.99 |
| DiM 0.75 | 50 | 2 | 0.04 | 1.00 | 1.00 |
| DiM 1 | 50 | 0 | 0.00 | 1.00 | 1.00 |
| RAND rank-4, lambda 1 | 17 | 12 | 0.90 | 0.50 (unadjusted) | 0.25 |
| forced-BFS prompt F5 (prompting ceiling) | 50 | 35 | 0.70 | 4e-6 (unadjusted) | - |
| DAS-L lambda 1 (logit-only) | 44 | 35 | 0.76 | 2e-6 (unadjusted) | - |
| DAS-L lambda 0.5 (logit-only) | 46 | 35 | 0.76 | 2e-6 (unadjusted) | - |

- **G2-KNOB holds for DAS and fails for DiM.**
  - DAS: doses 0.1, 0.2, 0.5, 0.75 and 1 have significantly more correct BFS than the twin with pass >= 0.8 x the
    twin's (0.69). Dose 0.35 misses on pass (0.68).
  - DiM at the same teacher-forced effect flips the algorithm just as well (attempted BFS up to 50/50) but
    destroys the programs (pass 0.70 -> 0.00). No DiM dose beats the twin on correct BFS.
- **DAS beats the prompting ceiling.** At lambda 1 it gives 42 correct BFS programs against 35 for the explicit
  "Write a correct solution that uses breadth-first search (BFS)" prompt. The prompt cell samples naturally from
  index 0, and the DAS cells from index 32 after the c* prefill.
- **The persisting state is not what breaks programs here.** The logit-only interchange (G2-L), which changes only
  the token-32 distribution, gives fewer correct programs (35) than the edit that persists in the KV cache (42).
  With DAS, the edited fork state helps the later code. With DiM it does not.
- **The fork account links teacher forcing to generation.** The teacher-forced predicted attempted share (fork
  distribution x P(BFS | token)) matches the observed BFS share within 0.10 in all 26 edited and unedited cells
  (mean absolute gap 0.029; largest 0.099 for the twin), for example 0.47 vs 0.54, 0.75 vs 0.76, 0.92 vs 0.92 and
  0.96 vs 0.94 for DAS.
- **RAND is null.** The matched random rank-4 edit changes nothing (17 attempted, 12 correct).
- **Toward DFS.** DAS gives 41-50/50 correct DFS (pass 0.94-1.00) against the twin's 32. The single strong
  DiM->DFS edit (D17) gives 45/50.
- **Contrast with iteration 6.** There, a rank-4 full interchange at L22 made 50/50 BFS and 0/50 valid. A dosed
  interchange to the class-mean coordinate at L17 keeps the programs.
