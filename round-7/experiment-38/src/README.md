# Circuit and dose dial at Gemma's BFS-vs-DFS fork (iteration 7)

**Question.** `google/gemma-3-4b-it` writes one of two algorithms for the same grid-path task (T1). Every program opens
with the same 32 tokens c* (```` ```python ````, `def solve(grid, start, goal):`, `rows = len(grid)`,
`cols = len(grid[0])`, indent). The next token, at response index 32, decides the algorithm: ` visited` leads to depth-first
search (DFS), while a blank line, `if`, `queue` or `q` lead to breadth-first search (BFS). This artifact asks three questions at
that fork:

- **G1.** Which components compute the fork margin m = logsumexp(z[B]) - z['visited']?
- **G2.** Does a controlled low-rank subspace (DAS) carry the choice, and is there a dose that adds correct BFS
  programs without breaking them?
- **G3.** Does the fork margin alone predict what temperature does?

It reuses iteration 6's engine, prompts, c*, fork-token table and labeller (Branch A, `inputs/iter6_gemma/`).

**Short answer (one model, one task, one natural fork; a case study, not a general circuit claim).**

1. **Temperature acts only through the fork margin (G3, pre-registered).**
   - Predictions were committed (#1) from teacher-forced logits before any temperature sample: c* probability times
     the fork distribution softmax(z / T) times P(BFS | fork token).
   - They match every top-p-1 cell (T0.3: 0.015 vs 0.02; T0.7: 0.17 vs 0.24; T1.0: 0.32 vs 0.34; T1.3: 0.45 vs
     0.46; MAE 0.026, max 0.074, all inside the Wilson CIs), so G3-LAW holds.
   - The fork-token class nearly fixes the algorithm (H(label | class) = 0.15 bits), so G3-CONC holds.
   - Lowering T from 1.0 to 0.3 switches 16/50 CRN-paired programs to DFS and none back (p = 1.5e-5).
   - Top-k 10 leaves every program unchanged at every T, as committed.
   - In the run's own terms: at tight temperature the model has one idea (DFS). Loosening T only moves mass across the
     one fork it already has. It does not add new algorithms.
2. **A controlled DAS subspace at the fork works as a dose dial; difference in means does not (G2).**
   - At layer 17 (chosen by the committed CV rule), a rank-4 subspace carries the forced-prompt transfer on held-out
     templates and sources: IIA 1.00 and directional dy 7.6 nats, which is 2.6x the full-state swap (a weak
     ceiling at that layer).
   - It passes every committed control: RAND 0.00, SHUF -0.30, a randomly initialised Gemma <= 0.25x the trained
     effect. G2-DAS-REAL holds.
   - Dosed toward the BFS class mean in generation (N = 50, CRN), it raises correct BFS programs from 11 (twin) to 20,
     27, 31, 37, 38 and 42 at lambda 0.1-1, keeping the pass rate (0.68-0.88 vs 0.86). G2-KNOB holds at 5 of 6 doses
     (Holm p down to 2e-8). At lambda 1 that is 42 correct BFS programs, against 35 for an explicit "uses BFS" prompt (sampled from
     index 0).
   - Difference in means at the same teacher-forced effect also flips the algorithm (up to 50/50 BFS) but destroys the
     programs (correct BFS 15 -> 0, pass 0.70 -> 0.00).
   - Caveats:
     - The three seeds share only one direction (principal cosine about 0.5).
     - At layer 17 the subspace holds no more of the twin's natural variance than random, although its coordinate
       tracks y_v (Spearman -0.50).
     - The claim covers forced-prompt transfer at one fork. "One-dimensional" is not licensed.
3. **A circuit for the fork margin, validated in the real model (G1).**
   - Path patching over 1,224 head/MLP x position nodes points to two parts:
     - early MLPs at the condition sentence (L0, L14), where the prompt's noun enters;
     - a fork-position stack (MLP L21/L22, head L22.H5, MLP L25/L26, with head L33.H2 writing to the margin), connected
       by kept edges.
   - Against 50 write-norm-matched random components per node, 7 of 10 nodes pass the committed node claim under
     ABLATE and 8 of 10 under STEER (Holm). The joint top-5 set beats all 50 matched random sets.
   - In generation (N = 30, CRN), steering the top-5 nodes toward the BFS-leaning class doubles correct BFS
     programs, 8 -> 16 (vs twin p = 0.019; vs 5 matched random nodes p = 0.006; pass 0.83). Ablating them to the
     class mean does not move the algorithm (12 vs 9 attempted, n.s.).
4. **Iteration 6 re-checks.**
   - The engine reproduces iteration 6 (y_v Spearman 1.000; 0.94 per-slot label agreement). The twin share 0.38 lies
     just outside iteration 6's CI because these 50 slots are BFS-heavy (iteration 6's own share on them is 0.36).
   - The failed U6 calibration does not reproduce: both paths agree with the natural share. Batching changes 9 of 200
     CRN-coupled programs (p = 0.039).
   - The fork token also fixes the implementation: forcing `queue` yields 125/125 path-carrying BFS programs, and none
     pass the hidden tests.
5. **No novel algorithm, and the transcoder graph could not run here.**
   - Of 2,325 correct programs in all arms, none was labelled 'other' (rule-of-three upper bound 0.0013).
   - The style re-gate agrees 30/30 (mistral-small-3.2) and 9/9 parsed answers (gemini-2.5-flash-lite, 21 unparsed).
   - The transcoder attribution graph (G1-T) could not run on the 16 GB GPU. The replacement model loaded and
     reproduced the margin within 0.19 nats, but attribution ran out of memory even at batch 16 with 4,096 feature
     nodes. The validated G1-P graph stands in its place (D19).

## What was run

| Part | What | Key output |
|---|---|---|
| S0 | inputs (133/133 sha256 match); labeller on the 12 T1 references (12/12); checker rejects 5/5 mutants; token ids, c*, prompt alignment; CRN; DAS toy; instrument ids; batch-shape time test (B = 25); **commit #0** | `results/s0_tests.json`, `results/das_toy.json` |
| S1 | U1 CRN determinism, U2 identity hooks (5 kinds, bit-identical), U3 single-position KV path, U4 top-k sampler | `results/tests_gpu_s1.json` |
| S1 | engine check (twin N = 50, iteration 6's keys), U6 re-run with diagnosis (200 + 200), G3-cal (4 fork tokens x 125) | `results/engine_check.json`, `results/u6.json`, `results/g3_cal.json` |
| G3 | predictions from teacher-forced logits (**commit #1**), then the same-seed sweep T in {0.3, 0.7, 1.0, 1.3} x {top-p 1, top-k 10}, N = 50 per cell | `results/g3_predictions.json`, `results/g3_sweep.json`, F6, F7 |
| yv | fork margin and fork states (all 34 blocks) for 120 twin variants, 40 forced sources, 5 twins | `results/yv.json`, `cache/states/` |
| G1-P | AtP screen of 1,224 nodes (272 heads + 34 MLPs x 4 position classes) on 15 pairs; exact noising/denoising for 60 nodes; edge path patching among the top 15; selection and matched nulls (**commit #2b**) | `results/g1_pathpatch.json`, F1 |
| G1 validation | ABLATE/STEER of the top 10 nodes on 24 prompts vs 50 matched random nodes each; joint top-5/top-10 vs 50 random sets; generation arms N = 30 | `results/g1_validation.json`, `results/g1_generation.json`, F2 |
| G2 | full-state ceiling by layer (17-29); rank-1 layer scan with 3-fold leave-one-template-out CV; nested DAS k in {1, 2, 4, 8} x 3 seeds at L* = 17 and L22; RAND (50), SHUF (3), DiM, natural variance; RINIT (random-init Gemma) | `results/g2_das.json`, `results/g2_layer_scan.json`, `results/g2_rinit.json`, `results/g2_decisions.json`, F3, F4 |
| G2 dose | **commit #3**; DAS and DiM (matched teacher-forced dy) toward BFS and DFS at 6 doses, twin, forced-BFS ceiling, RAND, logit-only DAS (G2-L); N = 50 per cell, CRN | `results/g2_dose.json`, `results/g2_dose_tf_pred.json`, F5 |
| G1-T | timed circuit-tracer attempt (nnsight backend, Gemma Scope 2 width-16k transcoders) | `results/g1t_graphs.json` |
| Audit | novelty audit and style re-gate (OpenRouter), hash chain, independent re-derivation with placebos | `results/novelty_audit.json`, `results/regate.json`, `results/verify_chain.json`, `results/rederive.json` |

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

### G1: a circuit for the fork margin (G1-P path patching, validated in the real model)

- **Pairs.** 15 clean/corrupt pairs: 10 natural pairs (DFS-leaning vs BFS-leaning twin variant of the same template,
  total effect 0.8-3.4 nats) and 5 forced pairs (forced-DFS vs forced-BFS, F1-F5, 15-19 nats). The mean total effect
  is 7.2 nats.
- **Screen.**
  - AtP covered 1,224 nodes (272 heads + 34 MLPs x FORK / CSTAR / SPEC / COND).
  - Exact patching covered 60 nodes. AtP agrees with exact noising at Pearson 0.65 and Spearman 0.73, with mean
    absolute error 0.31 nats against a mean exact effect of 0.55.
  - Where the effect enters: FORK 53%, COND 36%, SPEC 6%, CSTAR 5% (share of total exact noising effect).
  - The natural-pair and forced-pair top-20 sets overlap with Jaccard 0.38.
- **Top 10 nodes by exact noising effect** (clean DFS-leaning run, node <- BFS-leaning value; mean over 15 pairs):

  | Node | Noising effect (nats) |
  |---|---|
  | MLP L0 @ COND | +4.43 |
  | MLP L6 @ COND | +2.01 |
  | MLP L25 @ FORK | +1.96 |
  | MLP L21 @ FORK | +1.54 |
  | MLP L2 @ COND | +1.00 |
  | head L22.H5 @ FORK | +1.00 |
  | MLP L26 @ FORK | +0.97 |
  | MLP L14 @ COND | +0.93 |
  | MLP L22 @ FORK | +0.86 |
  | MLP L17 @ FORK | +0.84 |

  Every node's denoising effect has the opposite sign (-0.65 to -5.5).
- **Edges (path patching, kept if |dm| >= 5% of the total effect = 0.36 nats).**
  - Fork-position MLP chain: MLP L17 -> MLP L19 (+0.56), MLP L21 -> MLP L22 (+0.51), MLP L25 -> MLP L26 (+0.53).
  - Head L22.H5 -> MLP L25 (+0.50).
  - Direct paths to the margin: head L33.H2 (+0.88), MLP L25 (+0.62), MLP L22 (+0.57), MLP L26 (+0.42).
  - The condition-sentence MLPs (L0-L14 at COND) act through the residual stream and later attention, not through a
    single kept edge. They encode the noun or condition; the fork-position chain turns it into the token-32 choice.
- **Cross-check with iteration 6.** Iteration 6's strongest first-order SAE nodes sat at the FORK position at layers
  22 and 29. G1-P's top FORK nodes sit at layers 15-33, peaking at 21-26. The site agrees.
- **Validation in the real model (24 prompts: 10 BFS-leaning + 10 DFS-leaning variants + forced F1/F5 x BFS/DFS).**
  - Each top node was ABLATED (set to the opposite-class mean at aligned positions) or STEERED (own + 2 x (opposite
    mean - own mean)), against 50 random components of the same position class matched on write norm.
  - MLP nodes rarely had 50 MLP candidates within +/-50% of their norm, so their nulls are the 50 nearest-norm
    components of any type at that class (D09).
  - d_i = oriented dm(node) - mean dm(random nulls); exact one-sided sign-flip test over the 20 variants; Holm over
    10 nodes.

  | Node | ABLATE median d (Holm p) | STEER median d (Holm p) | Claim (ablate / steer) |
  |---|---|---|---|
  | MLP L0 @ COND | +0.28 (< 1e-4) | +0.49 (4e-4) | yes / yes |
  | MLP L6 @ COND | +0.16 (0.09) | +0.25 (0.25) | no / no |
  | MLP L25 @ FORK | +0.28 (3e-4) | +0.62 (< 1e-4) | yes / yes |
  | MLP L21 @ FORK | +0.23 (5e-4) | +0.48 (< 1e-4) | yes / yes |
  | MLP L2 @ COND | +0.07 (0.15) | +0.10 (0.13) | no / no |
  | head L22.H5 @ FORK | +0.19 (0.002) | +0.39 (< 1e-4) | yes / yes |
  | MLP L26 @ FORK | +0.15 (5e-4) | +0.61 (< 1e-4) | yes / yes |
  | MLP L14 @ COND | +0.17 (5e-4) | +0.39 (0.001) | yes / yes |
  | MLP L22 @ FORK | +0.34 (1e-4) | +0.68 (< 1e-4) | yes / yes |
  | MLP L17 @ FORK | +0.05 (0.10) | +0.17 (< 1e-4) | no / yes |

  - **NODE CLAIM holds for 7 nodes (ABLATE) and 8 nodes (STEER).** The joint top-5 set beats all 50 matched random
    sets (median oriented dm 0.98 nats ablate, 2.0 steer), and so does the top-10 set (1.47 and 3.96).
  - On the natural variants the effects are modest: the natural pairs differ by only about 2 nats in total. On the
    forced prompts they are large: ablating MLP L0 at the condition sentence to the opposite forced class moves m by
    13-17 nats, and the fork-position MLPs move it by 1.7-5.7 nats.
  - Reading: the condition-sentence MLPs (L0, L14) carry the prompt's lexical cue; the fork-position stack (MLP
    L21/L22, head L22.H5, MLP L25/L26) turns it into the token-32 decision. This is one circuit hypothesis for one
    fork, with per-prompt distributions in `results/g1_validation.json`.
- **Generation arms (N = 30; twin W1-W5 x 6 CRN slots; prompt + c* prefilled; edits in the prefill).**

  | Arm | Attempted target | Correct target | Pass | Test |
  |---|---|---|---|---|
  | twin | 9 BFS | 8 | 0.97 | - |
  | top-5 STEER toward BFS | 20 BFS | **16** | 0.83 | vs twin: correct 10 vs 2, p = 0.019; attempted 12 vs 1, p = 0.002. vs random-5 STEER: p = 0.006 (correct), 0.002 (attempted) |
  | random-5 STEER (matched) | 9 BFS | 7 | 0.93 | null |
  | top-5 ABLATE to the BFS mean | 12 BFS | 7 | 0.83 | attempted 3 vs 0, p = 0.125 |
  | random-5 ABLATE | 9 BFS | 6 | 0.90 | null |
  | top-10 ABLATE to the BFS mean | 12 BFS | 10 | 0.93 | p = 0.125 (attempted) |
  | top-5 ABLATE to the DFS mean | 22 DFS | 22 | 0.90 | vs twin 21 DFS: n.s. |

  Steering the validated nodes moves what the model writes and keeps the programs valid. Setting them to the natural
  class mean does not: the natural classes differ by only about 2 nats at the fork, so a class-mean ablation is a
  small push.

### G1-T: circuit-tracer attribution graph (timed attempt)

The plan's preferred graph (circuit-tracer, nnsight backend, `mwhanna/gemma-scope-2-4b-it`
`transcoder_all/width_16k_l0_big_affine`, custom target m_lin) was attempted three times under the time cap.

1. The replacement model loaded (11.9 GB), but every attribution failed: the container has no C compiler for Triton.
2. With a pip-installed compiler (ziglang behind a `cc` wrapper), the replacement model with error terms reproduced
   the fork margin within 0.19 nats (-0.415 vs -0.225). That misses the 0.05 sanity bar. The replacement model runs
   eager attention in its own environment; the main engine runs sdpa. Attribution then ran out of memory at batch 64.
3. With the plan's OOM ladder (CPU offload, batch 16, 4,096 feature nodes, lazy encoders; 9.0 GB after load),
   attribution still peaked at 16.4 GB on the 16 GB GPU.

The small-L0 transcoder set and fewer prompts, the next ladder steps, were not tried. **G1-T is dropped (D19).** No
replacement score or error-node share is reported. G1-P above, on raw components and validated in the real model, is
the circuit this artifact reports. The attempt records are `results/g1t_graphs*.json`.

## Audit (independent re-derivation)

- **Hash chain.** `audit/verify_chain.py` (standard library only) re-derives every chain value. The ordering checks
  pass:
  - commit #0 precedes every sample;
  - #1 precedes the first temperature sample;
  - #2b precedes the first G1 generation row;
  - #3 precedes the first dose-sweep row.

  See `results/verify_chain.json`.
- **Re-derivation.** `audit/rederive.py` (standard library only) re-derives 52 headline quantities from the raw rows
  with **0 mismatches**: engine counts, U6 counts and McNemar, every G3 cell and the MAE, the G1 arm counts and their
  McNemar p, and every G2 dose count with its Holm-adjusted p. See `results/rederive.json`.
- **Placebos.**
  - A temperature-shuffled G3 sweep gives MAE 0.123 against the real 0.026, and fails the 0.10 law.
  - Randomly sign-flipped G1 node effects give 0 significant nodes.
  - Slot-shuffled (unpaired) dose cells are reported beside the paired tests.
- **Labeller.** On the frozen exp8 T1 labeller, 12/12 references are labelled correctly and 5/5 hand-made mutants
  fail the hidden tests. Runtime and AST agree on 2,830 of 3,010 programs; the blind judge (openai/gpt-4.1-mini)
  resolved the other 180.
- **Spend.** OpenRouter USD 0.044 in total (labeller judge 0.036 over 88 calls; novelty audit and re-gate
  0.007), against the USD 0.5 cap.

## method_out.json

exp_gen_sol_out format, validated. Datasets:

| Dataset | Rows | Output | Predictions |
|---|---|---|---|
| `engine_check` | 50 | this run's label\|pass | `predict_iter6` |
| `u6_calibration` | 200 | (b) single-prompt label | (a) multi-prompt full and partial labels |
| `g3_calibration_fork_token` | 500 | forced fork token -> label\|pass | iteration 6 token-table prediction |
| `g1_nodes` | 20 | node effect (oriented dm) | `predict_random_null` |
| `g1_generation` | 30 slots | twin | one `predict_<arm>` per arm |
| `g2_teacher_forced` | 768 held-out pairs | dy_full | DAS k1-k8, RAND, SHUF, DiM |
| `g2_dose_sweep` | 50 slots | twin | one `predict_<cell>` per cell |
| `g3_temperature` | 50 slots x 2 samplers | T1.0 label | `predict_T0p3`, `predict_T0p7`, `predict_T1p3` |

`metadata.results` holds every `results/*.json`. The `full_`, `mini_` and `preview_` variants are beside it.

## Figures (`figures/`, PNG + PDF)

| Figure | What it shows |
|---|---|
| F1 `F1_g1_graph` | G1-P graph: nodes by layer x position class, kept edges |
| F2 `F2_g1_validation` | real-model ABLATE/STEER effect per prompt vs the matched random null, per top node |
| F3 `F3_g2_das` | full-state ceiling by layer, the rank-1 layer scan, and held-out recovery by rank with RAND, SHUF, DiM and RINIT |
| F4 `F4_g2_geometry` | the 120 twin variants and 40 forced sources in the (R_1, R_2) plane at L17 (actual activation coordinates), coloured by y_v, with the DAS dose path and the DiM direction |
| F5 `F5_g2_dose` | dose response (attempted, correct, pass) for DAS vs DiM toward BFS and toward DFS, with the twin, the forced-BFS ceiling and the logit-only DAS cell |
| F6/F7 `F6_F7_g3_temperature` | predicted vs observed BFS share by temperature (both samplers), and H(label \| fork class) by T |

## Deviations (full text in `results/deviations.json`)

- **D01 GPU.** RTX 2000 Ada (16 GB), not an A4500. B_CRN = 25 (time test); max_new 1024.
- **D02 RLIMIT_AS.** Set on CPU stages only (12 GB).
- **D03 Engine keys.** Iteration 6's own slot_key ('iter5E' for slots 0-9).
- **D04 DAS optimiser.** Adam lr 2e-2 (plan 2e-3: the toy shows 2e-3 x 400 steps leaves the subspace near random)
  and batch 48 (plan 64). Early stopping on a rotating held-in template.
- **D05 U3.** The single-position path differs from a full recompute by up to 0.27 nats (bf16). Every DAS dy is
  measured on one path and in one fixed batch shape.
- **D06 G1 order.** G1-P is the primary validated graph. G1-T ran last under a cap.
- **D07 Patching offsets.** The first g1p run was redone with in-batch base rows. Commit #2 is superseded by #2b,
  made before any validation or generation output.
- **D08 Position classes.** SPEC includes the chat tail. COND targets use same-template prompts.
- **D09 Random nulls.** Same type and position class, any layer, write norm +/-25% (widened when needed; logged).
- **D10 Labeller restart.** No data lost.
- **D11 Batching.** Cells of one template share fixed-shape batches.
- **D12 L* rule.** Recovery above 1 at early layers lets the committed argmax pick L17. Absolute dy is reported
  beside it.
- **D13 Toy.** The second principal cosine is 0.81, below the plan's 0.95.
- **D14 U6 horizon.** Full programs; partial labels on the first 320 tokens.
- **D15 Path-patching pairs.** F2-F4 forced pairs are added for patching only.
- **D16 Engine check.** 0.38 is just outside the CI; iteration 6's own share on the same slots is 0.36.
- **D17 DiM toward DFS.** A bisection bug left all six cells unmatched (beta = -3000). They are reported as one
  strong DiM-DFS reference.
- **D18 G2-N.** Not run (drop order). The mediation claim covers forced-prompt transfer only.
- **D19 G1-T.** Three timed attempts (missing C compiler; then out of memory at batch 64 and at batch 16 with 4,096
  feature nodes). Dropped. G1-P is the reported circuit.

## Positioning (from the dependency audit art_OUuQUYQn5voE, search dated 2026-10-22)

- Permitted wording for the DAS part: "the first interchange/DAS localization of *which algorithm* a code LLM will write
  that is validated by scoring the generated programs, with Sutter-style map-class, random-initialization and
  shuffled-label controls". Forbidden: "first causal localization of a plan", "new method", "first DAS-based steering"
  (CDAS, ICLR 2026, already validates DAS steering by generation, on refusal and a CoT backdoor).
- For temperature, "temperature is not the creativity knob" is not a new claim. What is new here is a pre-registered,
  quantitative account: the BFS share at every temperature is predicted from teacher-forced fork logits divided by T,
  before any temperature sample.
- Why Gemma when circuit-tracer ships Qwen-3 transcoders: this artifact continues iteration 6's Gemma fork (same
  model, prompts, c*, fork-token table and labeller). Gemma Scope 2 (22 Dec 2025) ships per-layer transcoders for
  gemma-3-4b-it, and a 4B model fits the 16 GB GPU used here.

## Layout

| Path | What |
|---|---|
| `method.py` | entry point, one function per stage (`--stage s0, engine, label, g3a, g3b, yv, g2smoke, g2, g2r, g2d, g2pairs, g1p, g1v, g1gen, novelty, analysis, figures, outputs`) |
| `src/cfg.py` | constants, paths, CRN keys, design parameters (B/D token ids, templates, doses, temperatures) |
| `src/engine.py`, `src/push.py`, `src/prompts.py`, `src/label_worker.py`, `src/regate_rules.py`, `src/fork.py`, `src/commit.py`, `src/novelty.py` | iteration 6's engine, prompt builders, labellers, partial-code labeller, hash chain and novelty audit (vendored; `engine.decode` gained a per-row top-k sampler) |
| `src/gen7.py` | generation runner: fixed-shape CRN batches, per-row temperature/top-k, module-level edits (resid, head z, MLP out) applied in the prefill, logit-only mode (G2-L), multi-prompt path (U6 a) |
| `src/fork7.py` | c*, B/D classes, fork margin m, the 120 twin variants, forced prompts with equal-length display names, position classes |
| `src/g1.py` | G1-P: AtP screen, exact noising/denoising patching, edge path patching, matched random nulls, real-model validation (ABLATE/STEER, sign-flip + Holm, joint sets), generation arms |
| `src/g2.py` | G2: single-position KV-cache forward, DAS (nested ranks, seeds), RAND/SHUF/DiM/natural-variance controls, RINIT, dose sweep + G2-L, per-pair export; also the U3 test and the DAS toy |
| `src/g3.py` | G3: U6 diagnosis, G3-cal table, committed predictions (COMMIT #1), temperature sweep and its analysis |
| `src/ct_graph.py`, `src/prep_ct.py` | G1-T: circuit-tracer attribution graphs (run in `.venv_ct`) and their input builder |
| `src/analysis7.py` | analyses, decision rules, figures F1-F7, `method_out.json` builder |
| `audit/verify_chain.py`, `audit/rederive.py` | standard-library audits: the hash chain and commit-before-sample ordering; re-derivation of headline counts/tests from raw rows, with placebos |
| `inputs/iter6_gemma/` | read-only copy of the iteration-6 Gemma artifact's code, results, raw T1 rows and its staged inputs (exp8 suite = T1 spec, hidden tests, references, runtime+AST labeller; dependency extracts), with `MANIFEST.sha256` |
| `predictions/`, `commitments.log` | commits #0 (design, rules), #1 (G3 predictions), #2b (G1 node list and nulls; #2 superseded, see D07), #3 (L*, k*, subspaces, doses, DiM betas) |
| `data/` | raw generations (`raw_*.jsonl`) and labels (`labels.jsonl`) of every cell; judge cache |
| `results/` | every analysis result (JSON); `deviations.json` lists all deviations |
| `figures/` | F1-F7 (PNG + PDF); geometry in actual activation coordinates |
| `cache/states/`, `cache/das_subspaces/` | fork states (all blocks) of the 120 variants, 40 sources and 5 twins; trained subspaces (kept on the run's volume) |
| `method_out.json`, `full_/mini_/preview_method_out.json` | exp_gen_sol_out output (datasets below; metadata = every results file) |
| `logs/` | stage logs, batch timings, OpenRouter spend |

## How to run

```bash
uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
.venv/bin/python method.py --stage label --follow &          # CPU label worker (frozen T1 labeller), follows data/raw_*.jsonl
for st in s0 engine yv g3a g3b g2 g2r g2d g2pairs g1p g1v g1gen; do .venv/bin/python method.py --stage $st; done
# G1-T attempt (needs a C compiler for Triton; scratch/bin/cc wraps the ziglang wheel installed in .venv_ct)
.venv/bin/python src/prep_ct.py scratch/ct_input.json && CC=$(pwd)/scratch/bin/cc timeout 720 .venv_ct/bin/python src/ct_graph.py scratch/ct_input.json results/g1t_graphs.json
for st in novelty analysis figures outputs; do .venv/bin/python method.py --stage $st; done
python3 audit/verify_chain.py && python3 audit/rederive.py
```

Hardware used: one NVIDIA RTX 2000 Ada (16 GB), 6 CPUs, 28 GB RAM. GPU time is about 2.5 hours in all. The model
(`google/gemma-3-4b-it` at revision `093f9f388b31de276ce2de164bdc2081324b9767`) and the transcoders were read from a
shared Hugging Face cache outside this folder.

## Restoring removed files

`.aii/manifest.yaml` marks these for deletion after the round; all are regenerable:

- `.venv/`: `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml`
- `.venv_ct/`: `uv venv .venv_ct --python=3.12 && uv pip install --python .venv_ct/bin/python "circuit-tracer @ git+https://github.com/safety-research/circuit-tracer@255d989e93be1299d53d67b59e9fd76a0e274b14"`
- `src/__pycache__/`: created automatically by any Python run.
- Model weights and transcoders are not stored here. Download them with
  `huggingface-cli download google/gemma-3-4b-it --revision 093f9f388b31de276ce2de164bdc2081324b9767` and
  `huggingface-cli download mwhanna/gemma-scope-2-4b-it --revision 61cb16ec74f348f4a8643fe3a0157be9dc8a851d --include "transcoder_all/width_16k_l0_big_affine/*.safetensors" "transcoder_all/width_16k_l0_big_affine/config.yaml"`.
  The code downloads them on first use.

`cache/states/` (fork states, 14-42 MB per file) and `cache/das_subspaces/` (trained subspaces, 1.8 MB) are
**kept** on the run's volume at these paths. Suggested upload-ignore patterns for the published repository are
`(^|/)cache/states/`, `(^|/)scratch/bin/` and `(^|/)paths\.local\.json$`, so the binary caches stay only on the volume.
To rebuild them, run `method.py --stage yv` (about 2 GPU-minutes), then `--stage g2` (about 47 GPU-minutes).
