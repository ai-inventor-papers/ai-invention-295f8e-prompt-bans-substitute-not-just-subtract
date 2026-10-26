# Does FP8 rounding make random pushes work?

Iteration 4 of this research run found that **fixed random directions pushed into Qwen3-8B's task-specification
states often change which algorithm the model writes** ("escapes"): 29 of 40 directions on connected components
(T10) and 8 of 40 on weighted shortest path (T2) at α = 2. All of those programs came from an **FP8 W8A8 engine**
(e4m3 weights per output channel, e4m3 activations per token). Iteration 5 then saw a bf16 null for per-sample plan
noise. This artifact asks whether the escapes are a property of **the model** or of **the FP8 numerics**.

It re-runs iteration 4's own design under four numerics, all built from one bf16 snapshot of `Qwen/Qwen3-8B`
(revision `b968826d…`):

| engine | weights | activations | role |
|---|---|---|---|
| **a** W8A8 | e4m3, per-output-channel absmax/448 | e4m3, per-token absmax/448 | iteration-4 engine (native `torch._scaled_mm`) |
| **b** W8A16 | e4m3 (same codes) | bf16 | weight rounding only |
| **c** W16A8 | bf16 | e4m3 fake-quantised per token | activation rounding only |
| **d** BF16 | bf16 | bf16 | full-precision reference (baseline) |

Everything except the numerics is held fixed:

- the 40 direction files (`rand_9101` … `rand_9140`, bitwise checked);
- the absolute displacement `n[l,p]` at blocks 12–23 and the task-spec positions (exp22 `ctx4.ban_unit`);
- the twin prompts, the CRN slots and uniforms, the fence stop and `max_new` = 1024;
- the labeller version, applied to every row of every engine, including iteration 4's;
- exp22's two-stage escape rule, with each engine scored against its own twin.

## Results

### Bottom line

- **Iteration 4's random-push escapes are mostly a property of Qwen3-8B, not of FP8 rounding.** At the same
  absolute displacement, the bf16 engine (d) escapes on almost the same directions as iteration 4's FP8 engine (a):

  | task | E(a) W8A8 | E(d) BF16 | discordant directions (a only : d only) | Spearman of per-direction shares | κ |
  |---|---|---|---|---|---|
  | T10 | 0.725 (29/40) | 0.650 (26/40) | 3 : 0 (exact McNemar p = 0.25) | 0.96 | 0.83 |
  | T2 | 0.200 (8/40) | 0.150 (6/40) | 4 : 2 (p = 0.69) | 0.87 | 0.48 |

  The committed literal verdict is **NOT_REPRODUCED_HIGH** on both tasks: E(a) − E(d) < 0.1, and E(d) ≥ the
  relabelled iteration-4 E(a) − 0.15. In words, bf16 escapes too, so the FP8-specific account is not reproduced.
  Permuting the direction pairing (placebo P2) destroys the agreement: κ falls from 0.83 to about 0.
- **FP8 adds a small boost, and only on T10.** Each pushed sample can be paired with the same CRN slot (same
  direction, template, k and uniforms) in the other engine. On the 400 screen slots (k 0–1 of all 40 directions; no
  selection):
  - T10: off-default in 58.3% of slots under W8A8, against 53.2% under bf16. Discordant slots are 30 : 10, exact
    McNemar p = 0.002.
  - T2: 43.2% against 40.7%, discordant 55 : 45, p = 0.37.
  - The direction-level discordance is near-threshold. An example is T10 direction 9133: its off-default share is
    1.0 in both engines, but bf16's first-10 pass rate (0.7) misses the 0.8 × twin clause.
- **T2's low E is a pass-rate effect, the same in both engines.** In each engine, 17 of the 40 T2 directions reach
  the +0.20 off-default excess but fail the pass clause: the pushed off-default programs often fail the hidden tests.
  The mean first-10 off-default share is 0.43 under W8A8 and 0.41 under bf16.
- **The factorial: activation rounding alone adds nothing.** All values are at α 2, each engine against its own
  twin. W16A8 is engine c, with bf16 weights and e4m3 activations rounded per token exactly as iteration 4 did.
  - **Escape fraction.** W16A8 escapes like bf16: E(c) = 0.600 (24/40) on T10 and 0.150 (6/40) on T2, against
    E(d) = 0.650 and 0.150. Discordant directions c:d are 1:3 and 2:2.
  - **Per slot.** It is slightly *below* bf16 on T10: off-default 49.7% against 53.2% of the 400 screen slots,
    discordant 9 : 23, p = 0.02.
  - **PN.** The same ordering appears: T10 α 2 gives 22/50 for c, 25/50 for d and 30/50 for a; a vs c discordance is
    9:1, p = 0.02.
  - **So the T10 boost is not activation rounding.** Within the W8A8 engine it must come from the e4m3 weights, or
    from the native kernel's reduced-precision FP8 accumulation (U1: the kernel matches an exact fp64 reference on
    only 94.2% of outputs), or from their interaction.
  - **Engine b decides between them.** W8A16 (e4m3 weights, bf16 activations) sits between bf16 and W8A8 on T10:
    - 28/40 screen passes (W8A8 30, bf16 27);
    - per-slot off-default 55.6% of the 400 screen slots (W8A8 58.3%, bf16 53.1%); b vs d is 17:7 (p = 0.06) and
      a vs b is 20:10 (p = 0.10);
    - PN at α 2: 27/50 (a 30, d 25).

    On T2 it behaves like bf16: 8/40 screen passes, per slot 39.0% against 40.7% (p = 0.51).
    E(b) on T2 is 0.125 (5/40), with complete confirmation. On T10 the time limit stopped b's confirmation short of
    the full pooled 30 rows: 15 of its 28 screen passers have 26 rows and 13 have 22. So E(b) on T10 is reported at
    the screen level (0.70, flagged incomplete in the tables). On the rows it has, 27 of the 28 already meet the
    confirmation rule.
    Weight rounding therefore carries roughly half of the small T10 boost. The rest needs W8A8's combination of
    weight and activation rounding, or the native kernel's accumulator. No single-factor engine differs from bf16 at
    the direction level: screen-level discordance b:d is 2:1 (T10) and 1:2 (T2), c:d 2:2 and 3:4.
  - **Same landing algorithms.** The correct off-default programs land on the same algorithms in every engine
    (T10: DFS, then BFS; T2: Bellman-Ford/SPFA). The a/c/d compositions are compatible with each other (permutation
    χ² p = 0.22 on T10, 0.94 on T2), so FP8 changes neither where the pushes land nor, on T2, how often.
- **Per-sample plan noise (PN) reproduces in bf16 at the matched unit, so iteration 5's bf16 PN null came from its
  design, not from bf16 numerics.** On exp19's own slots, uniforms and per-sample direction seeds, at the same
  absolute unit, bf16 matches FP8 (off-default / valid):

  | task | arm | a W8A8 (= iteration-4 FP8) | b W8A16 | c W16A8 | d BF16 | CRN-paired discordance a:d |
  |---|---|---|---|---|---|---|
  | T10 | PN α 1 | 6/50 | 9/50 | 4/50 | 7/50 | 1:2 |
  | T10 | PN α 2 | 30/50 | 27/50 | 22/50 | 25/50 | 6:1 (p = 0.13) |
  | T2 | PN α 1 | 12/50 | 11/50 | 11/50 | 10/50 | 4:2 |
  | T2 | PN α 2 | 22/50 | 19/50 | 18/50 | 22/50 | 8:8 |

  - **Same input dose.** The realised displacement at block 12 (the first edited block, where it is exactly α·n
    along u) is 13.75 in this run's bf16 PN rows at α 2 and 13.76 in exp19's FP8 rows.
  - **What differed in iteration 5.** Iteration 5's bf16 PN (exp27) was 1/50 off-default on T10 at α 1 and at α 2.
    It used the same prompts and uniforms but a different unit: the "ban-free" unit, proportional to clean-state
    norms times a per-block ratio. Its direction seeds also differed.
  - **Not the size of the push alone.** At α 2 its block-12 displacement (9.07) was larger than this run's bf16 α 1
    (6.88), which still gives 7/50. So the null is not explained by the scalar size. It is explained by the unit's
    per-position/per-block profile or the different seeds, i.e. by the design, not by bf16 numerics. Which of the two
    matters is untested here.
  - **T2 "movable".** The iteration-5 statement that T2 "loses movable" in bf16 is not reproduced at the absolute
    unit: E(d) on T2 is 6/40.
- **Mechanism diagnostics (teacher-forced, `results/diagnostics_*.json`).**
  - **Rounding size.** Per-token e4m3 rounding perturbs every linear input by about 2.5% RMS.
  - **Rounding difference caused by the push.** Under an α-2 push, the push-induced *difference* in rounding error is
    6–12% of the push-induced activation change: the median over blocks 13–35 per site, in the c and d passes. It
    peaks at 34% at block 14 (qkv input).
  - **Scale changes.** 70–100% of the rows the push moves get a new per-token scale s_x.
  - **No rounding difference before the edit.** Linear inputs at blocks 0–12 are bitwise identical in the pushed and
    the twin pass, in every engine, as the edit site requires.
  - **Propagation barely changes.** The extra rounding raises the non-nominal perturbation of the push only slightly.
    The median ratio to bf16 over blocks 13–35 is 1.01 at S, 1.04–1.05 at R and 1.03–1.12 at generated tokens
    1–32 for W16A8. The curves of all engines coincide on a log scale (`figures/induced_perturbation`).
  - **Per-token divergence.** Teacher-forced on 40 iteration-4 twin programs, every engine is very close to bf16.
    Mean per-token KL(e ‖ bf16) on T10 / T2:
    - W8A8: 0.0036 / 0.0015 nats;
    - W8A16: 0.0019 / 0.0005;
    - W16A8: 0.0017 / 0.0011.

    The argmax differs on at most 0.2% of positions. The W8A8 and W8A16 values use their top-64 tokens against
    bf16's stored top-512 and are lower bounds; the uncovered mass is 0.
  - **Which factor adds induced perturbation.** Activation rounding (a, c) adds 3–13% at generated positions. Weight
    rounding alone (b) adds nothing: its median ratio to bf16 is 0.995–1.006.
  - **The FIDELITY rule failed, and the failure is uninformative here.** The rule required the teacher-forced
    log-prob sum of exp22's own sampled programs to match exp22's `logprob_sum` under a at ≤ 0.25 × the mismatch
    under bf16. It fails: the median |diff| is 0.48 / 0.45 under a and 0.38 / 0.68 under d, ratios 1.24 and 0.66.
    The reason is that teacher forcing itself changes numerics, because it runs one long prefill instead of 20-row
    decode steps (B = 1 vs B ≥ 3, cf. U3). So the test cannot resolve engine differences at this level. It was
    designed to validate an *emulated* W8A8. Engine a here is the native kernel and is validated far more strictly
    by byte identity (400/400).
  - **Native kernel accuracy (U1).** On real linear inputs the native Ada FP8 kernel stays within 1 bf16 ulp of an
    exact fp64 evaluation of the same e4m3 products for ≥ 99.98% of non-small outputs. Its RMS relative error is
    0.18% (p99 0.74%); the exact-math emulation is exact.

### What this changes for earlier results

The relabel table below assigns each earlier result to the numerics class that reproduces it.

- **Model properties.** These hold in bf16 at the same absolute dose:
  - iteration 4's 40-direction escape fractions;
  - its per-sample plan-noise rates;
  - the exp17 positive-control direction 9004.

  They are not FP8 artifacts.
- **FP8-specific.** Only the T10 per-slot off-default rate carries a small, significant W8A8 boost (about +5 points,
  from weight rounding or the FP8 kernel; not from activation rounding).
- **Not reproduced.** Iteration 5's bf16 "plan-noise null" and its "T2 loses movable in bf16" are not reproduced at
  the absolute unit. They belong to that design's unit, not to bf16 numerics.
- **Untested here.** The plan-subspace claims of iteration 4: the π–ρ predictor, the targeted runner-up pushes and the
  u⊥/u_P decomposition. All were measured in FP8. Their direction-level inputs are the same model property, but the
  claims themselves were not re-run.

### Full result tables

These tables are generated from `results/*.json` by `src/report6.py` (also saved as `results/report_tables.md`).

<!-- TABLES -->
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
<!-- /TABLES -->

### Figures (`figures/*.pdf|png`)

| figure | content |
|---|---|
| `heatmap_directions_T10`, `heatmap_directions_T2` | first-10 off-default share of every fixed direction × engine (α 2), with confirmed escapes and screen passes marked |
| `E_by_engine` | escape fraction per engine, confirmed and screen-level, Wilson 95% |
| `per_direction_scatter` | per-direction shares: c vs a, d vs a, b vs d |
| `induced_perturbation` | non-nominal perturbation of an α-2 push per block, at S, R and generated positions 1–32, per engine |
| `rounding_by_block` | e4m3 rounding error, the push-induced rounding difference and per-token scale changes, per block and site |
| `pn_by_engine` | per-sample plan noise per engine, against iteration 4's FP8 rows |
| `landings` | which algorithms the correct off-default programs use, per engine |

### Validation: engine a is iteration 4's engine, byte for byte

- **Same programs.** Iteration 4 ran on this GPU model and driver with the same pinned torch 2.8.0 / cuBLAS
  12.8.4.1. The vendored FP8 engine regenerated exp22's programs exactly: 400 of 400 REPRO rows (T10 and T2 twins,
  k 0–9, plus directions 9101–9110 at α 2, k 0–1, plus pad rows) and 40 of 40 of exp19's per-sample-noise rows.
- **Same labels and displacement.** Per-slot label agreement is 1.0, the pooled off-default share is identical, and
  the realised downstream displacement at blocks 24–35 has ratio 1.000.
- **Reuse.** Under the reuse rule fixed in COMMIT #0, exp22's own rows (relabelled) therefore serve as engine a on
  every other cell, and exp19's rows serve as engine-a PN.
- **CPU gates (all pass).**
  - C1: the 40 directions and rand_9004 equal their PCG64 regeneration bitwise.
  - C2: 10 screen slots per cell, 20 confirmation slots per confirmed cell, prompt sha256 and CRN seeds match.
  - C3: this artifact's escape code reproduces exp22's `escape.json` exactly (T10, T2 and T03, both alphas).
  - C4: the current labeller (exp22's plus the iteration-5 re-gated T2 rule) changes 18 of iteration 4's T2 labels
    (bf_spfa → dijkstra) and no escape fraction.
  - C5: the logged displacement along u equals α·n to within 0.074% on all 1,770 logged iteration-4 POP prefills.
- **GPU unit tests.**
  - U2: the e4m3 codes and scales equal iteration 4's FP8Linear bitwise.
  - U4: α = 0 gives a bitwise twin in every engine, and α = 2 pins the displacement along u to within 1.4e-4.
  - U5: reruns are bitwise identical.
  - U3: batch-mates never change a row. Batch size changes logits only below about 3 rows.
  - U6: the KV-capped sampler draws exactly what the vendored one draws.
  - U1: exact-math emulation of `_scaled_mm` matches an fp64 reference on 99.96% of outputs. The native Ada FP8
    kernel matches on 94.2%, consistent with its reduced-precision accumulator (see `results/unit_tests_q*.json`).
- **bf16 engine check.** Engine d's twins reproduce iteration 5's bf16 twin composition: T10 union_find 50/50; T2
  dijkstra 49, bf_spfa 1.

## Design as run, and deviations from the plan

The full list with consequences is in `results/deviations.json`.

- **Hardware.**
  - The GPU is an RTX 2000 Ada (sm_89, 16 GB), not the planned 20 GB A4500, and the CPU quota is 5.1 cores.
  - Engine a runs on the native FP8 kernel (the plan's sm_89 fallback), so iteration-4 numerics hold byte for byte.
  - bf16 weights (14.1 GiB with lm_head) leave about 1.3 GiB for the KV cache. Weight set B (c, d) therefore runs at
    B = 7 with a KV buffer of 448 generated tokens. Rows longer than that continue in a full buffer (flagged; 1 row
    so far).
  - Weight set Q (a, b) runs at exp22's B = 20.
  - The planned B-sensitivity control (engine a re-run at B = 7) was dropped for time: the fused W8A16 kernel could
    not be compiled (no C compiler in the container), so engine b ran on the slower per-call-cast path. Unit tests U3
    show the logits of a row are bitwise identical across batch sizes ≥ 3 (bf16, W16A8) and ≥ 10 (FP8, W8A16), so
    the batch shape is not expected to matter. The bf16 twins also reproduce iteration 5's bf16 twin composition
    exactly.
- **Engine-a reuse.** Engine a was regenerated only on the REPRO cells and exp19's PN W1 slots. Both were
  byte-identical, so iteration 4's own rows stand in for engine a everywhere else (rule fixed in COMMIT #0).
- **Dropped by the committed drop order.**
  - S7 (T03).
  - S6 (the Gaussian mimic). Once bf16 itself escapes, a mimic of FP8 noise has no FP8-specific effect left to
    explain, apart from the small T10 slot-level boost.
  - S5 (α 1) for b and c. E_rule is therefore α 2 for every engine.
  - The α-1 follow-up for engine d (`src/gpu_b2.py`) was skipped, and its GPU time went to engine b's confirmations
    (`src/gpu_q3.py`). The half-dose point comes from bf16 PN at α 1 instead: 7/50 on T10 against FP8's 6/50.
  - Engine b's confirmations ran until the final deadline. Any screen passer left untested makes E(b) screen-level,
    flagged as such in the tables.
- **Analysis code committed late.** `src/analysis.py` / `src/rederive.py` were committed after COMMIT #0, by
  amendments #1–#3. Each amendment preceded the rows it could affect, and the verdict rules stayed COMMIT #0's text.
- **One post-hoc change.** AMENDMENT #4 is post-hoc and descriptive only. It restricts the primary per-slot
  comparison to the screen slots, because the all-slot version carries a selection effect from the confirmation
  slots; that version is kept beside it.
- **Verifying the chain.** The chain is in `commitments.log`; `.venv/bin/python src/commit6.py` verifies it.
- **Novelty audit.** The two-judge novelty audit was replaced by a zero-cost nearest-known-solution pass over all 10
  datasets of the declared dependency (`results/known_solutions.json`).
- **Memory limits.** RLIMIT_AS is not set in the CUDA processes, because it breaks CUDA's virtual-address
  reservations. VRAM is capped with `set_per_process_memory_fraction` instead, and RAM use stays far below the
  31 GB cgroup limit.

## Layout

| path | what |
|---|---|
| `method.py` | entry point; `uv run method.py <step>` runs setup, gates, commit0, label, q1, b, q2, analyse, rederive, figures, outputs, or all |
| `src/setup_inputs.py` | copies and sha256-verifies every earlier-artifact input into `vendor/` and `inputs/` |
| `src/cpu_gates.py` | gates C1–C5; relabels iteration 4's rows under the current labeller |
| `src/escape.py` | exp22's two-stage escape rule, re-implemented (gate C3 reproduces exp22's `escape.json` exactly) |
| `src/engines.py` | the four numerics: weight set Q (a, a_emul, b) and weight set B (c, d) |
| `src/w8a16_triton.py` | fused e4m3→bf16 GEMM for engine b (chosen by a committed rule; `results/w8a16_impl.json`) |
| `src/gen.py`, `src/sampler6.py` | generation runner on exp22's CRN design; KV-capacity-aware copy of the vendored sampler |
| `src/gpu_q.py`, `src/gpu_q2.py`, `src/gpu_q3.py`, `src/gpu_b.py`, `src/gpu_b2.py` | GPU processes per weight set (a single 16 GB card holds one set at a time); `gpu_q3.py` finishes engine b's confirmations; `gpu_b2.py` is the skipped α-1 follow-up |
| `src/gpu_tests6.py` | unit tests U1–U5 (U6 is in `gpu_b.py`) |
| `src/diag6.py` | teacher-forced diagnostics: KL vs bf16, FIDELITY, induced perturbation per block, rounding and scale changes |
| `src/label_worker6.py` | labeller (exp22's, vendored) plus the iteration-5 re-gated T2 rule |
| `src/rows6.py` | joins rows and labels per engine; engine-a reuse of byte-identical iteration-4 rows |
| `src/analysis.py` | E, McNemar/Tango/TOST, verdicts, PN, REPRO, B-sensitivity, landings, relabel table |
| `src/rederive.py` | independent stdlib re-derivation, with placebos |
| `src/audit_headlines.py`, `results/audit_headlines.json` | separate audit from raw rows + labels: REPRO 400/400, E(a)/E(d), T10 slot McNemar 30:10 (p = 0.0022), engine-swap placebo non-significant |
| `reproducibility.md` | step-by-step reproduction (commands, versions, hardware, runtimes, expected numbers) |
| `src/figures6.py`, `src/outputs6.py`, `src/finalize6.py` | figures, `method_out.json`, and the deviations/costs/timing bookkeeping |
| `src/known6.py` | nearest-known-solution pass over all 10 datasets of the declared dependency `art_j3Rm_lr2nzR6` |
| `src/report6.py`, `results/report_tables.md` | the README's result tables, generated from `results/*.json` |
| `finalize.sh` | the final CPU pass: analysis, nearest-known pass, re-derivation, figures, `method_out.json` and its mini/preview |
| `logs/` | logs of every GPU and CPU process, including `chain.sh` (the GPU stage chain) |
| `src/commit6.py`, `src/make_commit0.py`, `commitments.log` | hash-chained pre-registration (COMMIT #0 and amendments) |
| `predictions/` | `commit0.json` (decision rules), `slot_map.json`, `hardware.json` |
| `data/raw/raw_<engine>.jsonl` | every generated program: text, token ids, CRN slot, engine, B, realised displacement |
| `data/labels.jsonl` | one label row per program, keyed `<engine>\|<task>\|<template>\|<arm>\|<k>` |
| `data/samples.jsonl` | joined analysis rows of every engine; engine a includes the reused, relabelled iteration-4 rows |
| `data/iter4_relabelled.jsonl`, `data/realised_disp.jsonl` | iteration-4 rows under the current labeller; realised displacement of every pushed prefill |
| `results/` | every analysis table (JSON); `verdict.json` is the headline |
| `figures/` | PDF and PNG figures, drawn from `results/` only |
| `method_out.json` | `exp_gen_sol_out` output: one example per slot and cell, with `predict_<engine>` = `label\|pass` |
| `vendor/` | unchanged copies of the exp22 code, prompts, directions and inputs, the exp19 engine, and the exp28 re-gate rule (`vendor/SHA256SUMS`) |
| `inputs/` | data and result files of exp22, exp19, exp27 and exp28 (`inputs/MANIFEST.json`) |

## How to run

```bash
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -r pyproject.toml   # torch 2.8.0 / cu128
hf download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218                # into $HF_HUB_CACHE
uv run method.py all          # or step by step: setup gates commit0 q1 b q2 analyse rederive figures outputs
```

- The GPU steps need one CUDA GPU with at least 16 GB. Engine a needs sm_89+ (FP8 tensor cores); elsewhere `a_emul`
  is the exact-math emulation.
- Run `uv run method.py label` in a second shell during generation (`method.py all` starts it automatically).
- `setup` copies inputs from the earlier run's folder. Set `AII_ITER45_ROOT` (iterations 4–5) and `AII_DEP_ART_J3RM`
  (the declared dataset, for `src/known6.py`) if those folders live elsewhere. The verified copies already ship in
  `vendor/` and `inputs/`.
- The judges use OpenRouter (`OPENROUTER_BASE_URL`, `OPENROUTER_API_KEY`). They are called only when the runtime and
  AST labels disagree, capped at USD 0.40.

## Restoring removed files

`.aii/manifest.yaml` marks two paths for deletion after the round:

| path | how to restore |
|---|---|
| `.venv/` (9.8 GB) | `uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -r pyproject.toml` |
| `src/__pycache__/` | Python bytecode, rebuilt automatically on the next import (for example `.venv/bin/python src/analysis.py`) |

The model weights were never in this folder; they sit in the run's shared Hugging Face cache. Restore them with
`hf download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218`.
