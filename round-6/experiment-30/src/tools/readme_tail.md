
### Iteration-4 FP8 vs this bf16 run (descriptive; different engine and different unit, no test crosses them)

Each cell shows correct off-default share / pass rate. exp20 used FP8 W8A8 and the iteration-4 FP8 ban unit. This
artifact uses W16A16 and the bf16 ban-free unit. On T03 at blocks 12-23 the ban-free unit is 0.81x the ban unit
(ratio of means).

| Task | Site | FP8 α 1 | bf16 α 1 | FP8 α 2 | bf16 α 2 | FP8 α 4 | bf16 α 4 |
|---|---|---|---|---|---|---|---|
| T03 | S0 | 0.33 / 1.00 | 0.14 / 0.98 | 0.40 / 0.93 | 0.34 / 0.96 | 0.20 / 0.67 | 0.42 / 0.88 |
| T03 | S4 | 0.07 / 1.00 | 0.02 / 1.00 | 0.13 / 1.00 | 0.08 / 1.00 | 0.43 / 1.00 | 0.26 / 1.00 |
| T03 | S3 | 0.10 / 1.00 | 0.10 / 1.00 | 0.47 / 0.90 | 0.20 / 0.97 | 0.03 / 0.17 | 0.13 / 0.50 |
| T03 | S1, S2, S5 | 0.00 | 0.00-0.02 | 0.00 | 0.00-0.02 | 0.00 | 0.00-0.02 |
| T10 | S0 | 0.30 / 1.00 | 0.00 / 1.00 | 0.57 / 0.97 | 0.06 / 1.00 | 0.13 / 0.23 | 0.28 / 0.96 |
| T10 | S4 | 0.10 / 1.00 | 0.00 / 1.00 | 0.20 / 1.00 | 0.04 / 1.00 | 0.43 / 0.90 | 0.14 / 1.00 |
| T10 | S1, S2 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| T10 | S5 | 0.00 | 0.00 | 0.10 | 0.00 | 0.07 | 0.00 |
| T2 | S0 | – | – | 0.20 / 0.90 | 0.03 / 0.87 | 0.00 / 0.03 | 0.23 / 0.80 |

What replicates across precision: the task-spec sites move the algorithm and S1, S2 and S5 do not. What does not:
the dose at which movement starts and the dose at which the code breaks. FP8 is far more sensitive per unit of
nominal dose, so dose-response numbers from iteration 4 should not be carried into bf16.

### Failure mode per site (exp20's frozen classes; `results/failure_modes.json`)

| Site | T03 | T10 | T2 |
|---|---|---|---|
| S0 | moves | moves | moves |
| S4 | moves | moves | no movement |
| S5 | no movement | no movement | no movement |
| S1 | no movement | no movement | no movement |
| S2 | no movement | no movement | no movement |
| S3 | moves | weak movement | weak movement |
| S1E | no movement | weak movement | no movement |

### Novelty audit (`results/novelty_audit.json`, `audit/`)

- **Pool.** 63 correct programs carry the label 'other' (61 unique): 44 from T03 TOP3 alpha 4, 17 from TOP3 alpha 2,
  1 from S3 and 1 from S4 at alpha 8. All 61 pass 3 stress tests at the spec's maximum size.
- **Judge controls.** All three judges score 6 of 6 on the controls.
- **Judges.** google/gemini-2.5-flash-lite and openai/gpt-4.1-mini are the judges, with deepseek-chat-v3.1 as the
  tie-break. Resolved classes: 30 CATALOGUE VARIANT, 31 LABELLER MISS. Both judges name counting sort as the closest
  known algorithm.
- **Manual pass.** The executor read each program beside its three nearest known solutions (xlcost k-th-smallest
  programs, index rebuilt from art_j3Rm_lr2nzR6; 472 rows exactly as exp18, plus 42 T05). All 61 are CATALOGUE
  VARIANT: counting sort with a sorted dictionary of counts.
- **Claim.** 0 novel algorithms among 3,102 correct programs (rule-of-three 0.10%).
- **Sensitivity.** Relabelling these programs counting_sort (`results/s_d_audit_relabelled.json`) turns the T03
  top-3 push's 'other' landings into survivor landings: 19 of 50 correct at alpha 2 and 44 of 50 at alpha 4.

## Checks

- **CPU tests** (`results/unit_tests_cpu.json`, all 9 pass):
  - the batched edit equals exp20's make_prefill_edits and exp27's make_edits('RAND') exactly (max |diff| 0.0), and
    the along-u error is 6e-6;
  - exact McNemar matches the enumerated binomial and statsmodels;
  - Holm;
  - Mantel-Haenszel OR and RBG CI match statsmodels StratifiedTable to 1e-9;
  - first divergence and code start, including divergence before the fence;
  - geometry: on a half ring the geodesic is 3.13 against a Euclidean 2.00, and MDS stress-1 is 0.0004; the
    connectivity fallback works;
  - the random-survivor null matches its closed form, and exact enumeration matches Monte Carlo within 0.001;
  - the S-a selection rule, including the pass gate, ties and the selection-aware p;
  - S1E's energy matches S0's to 1e-6.
- **GPU tests** (`results/unit_tests_gpu.json`):
  - **U1.** CRN determinism across two batch compositions: T03 True, T10 True.
  - **U2.** Alpha 0 reproduces the twin byte for byte at every site (S0, S4, S5, S1, S2, S1E, and S3 with its
    shadow): True on both tasks.
  - **U5.** The block-35 edit is a no-op: True.
  - **U3.** The mean along-u displacement equals alpha x unit within 0.05% at every site. The worst position reaches
    0.87% (S4) because the edited residual is rounded to bf16 (deviation D_U3_bf16). S3 holds against its shadow
    within 0.04%.
  - **U4** (shadow vs an independent teacher-forced forward). T10 min cos 0.9998. T03 0.69, the same pattern exp20
    saw in FP8 and diagnosed as decode-path numerics.
  - **U6.** Peak 18.6 GiB of 22.0 at B = 16 with 1,024 tokens, and at B = 12 with 1,536 tokens
    (`results/batch_probe.json`).
  - **U7.** No ban prompt in the sampling queue or in any sampled row.
- **Positive control U8 and engine check U9** (`results/engine_checks.json`):
  - T03 reproduces exp25 exactly (Fisher p 1.0, JS 0.000; per-slot agreement 1.00).
  - T2 per-slot agreement is 0.98 (Fisher p 0.84).
  - The twins agree with exp27/exp25's bf16 twins on 0.98-1.00 of slots.
- **Labellers re-checked** (`results/labeller_recheck.json`):
  - bench references pass and self-label (T03 6/6, T10 4/4);
  - gold-set runtime and AST labels are reproduced (T03 28/28 and 28/28, T10 22/22 and 22/22);
  - exp8 suite references: T1 12/12, T2 10/10.
- **Units** (`units/r_Q_all.json`, `results/units_summary.json`).
  - The bf16 r_Q at blocks 12-23 is 0.952 x exp23's, inside the [0.9, 1.1] band, so it is used as frozen.
  - The used r_Q is 0.010 at block 0, 0.057 at block 11, 0.070-0.115 at blocks 12-23 and 0.092-0.104 at blocks
    24-35.
  - exp27 reported a ban-free/ban ratio of 1.39 on T03. This run measures 0.81 (ratio of means) and 1.00 (mean of
    per-position ratios) against exp20's FP8 ban unit. The two are not reconciled; the difference is logged.
- **Inputs** (`inputs/SHA256SUMS`, 572 files; `results/inputs_check.json`). The bench files check against
  `bench/commitment.json`: 146 checked, 0 mismatches.
- **Directions** (`directions/seeds.json`). The namespace ITER6_S2 is new. Its maximum |cos| with every earlier
  direction file, and with exp20's PN4 slot directions, is 0.069.
- **Banned sets** (`predictions/banned_sets.json`; `results/banned_sets_check.json`). The sets were committed from
  earlier twin, base and plan-noise rows. Adding this artifact's twin leaves all three unchanged.
- **Independent re-derivation** (`audit/rederive.py` -> `results/rederive.json`). It is stdlib/numpy code that shares
  nothing with `src/`.
  - 77 cells, every S-a contrast, the S-b OR, S-c, F1 (221/219) and F2's m are recomputed from the raw rows, with
    **0 mismatches**.
  - The placebos fail as required: S-a with site labels shuffled within (task, alpha) passes in 0 of 200 shuffles;
    the MH indicator shuffled within task excludes 1 in 2%; swapping McNemar pair members rejects in 2%.
- **Pre-registration** (`commitments.log`, `results/commitment_audit.json`). There are 3 commits and 0 chain breaks.
  - Commit #1 (rules, cells, sets, units, directions, predictions) is at 21:00:17Z. The first decisive row is at
    21:00:41Z; 0 decisive rows came earlier.
  - Commit #2 (the final analysis code) is at 22:51:37Z, before the analysis ran on the full data.
  - Commit #3 (23:27:52Z) records three bug fixes found on the first full outputs (D_POSTC2_FIXES). They touch only
    the S-d survivor count on T1, the m_fork sensitivity and an added push-progress normalisation. S-a, S-b, S-c, F1
    and the primary m are unaffected.
- **Deviations** (`results/deviations.json`, 14 entries):
  - NVIDIA L4 instead of an RTX A4500.
  - B = 16/12 from the memory probe, instead of the plan's starting 8/6.
  - U3's bf16 rounding.
  - U4 on T03.
  - F2 passes run after sampling (so m was computed after commit #1).
  - The banned sets exclude this artifact's own twin.
  - T1 masked prompts use exp8's 6-mode names.
  - U9 is computed post hoc.
  - Push progress t is unstable when the twin is off the B side of the axis, so t' is reported beside it.
  - One input file was copied after commit #1.
  - The geometry code was sped up between commits.
  - The post-commit-2 fixes.
  - F2 is undefined where the default or runner-up has fewer than 3 forced programs (R3, R6, T04, T05, T06, T08).
    The plan's generation fallback was not run.
- **Not run.** Every planned cell ran, including both outcome-blind extensions, and no time-based drop was needed
  (`results/timing_extrapolation.json`).

## Interpretation and limits

- **Scope.** Qwen3-8B in W16A16 on three memorised LeetCode-style tasks (T03, T10, T2), plus T1 for S-d. N is 30-50
  paired slots per cell.
- **What the site result is.** The claim is site-specific sensitivity to off-distribution isotropic noise. It is not
  evidence for a plan representation. Zhang and Nanda warn that noise corruptions push states out of distribution,
  and every arm here is such a push. What the design guarantees is that the comparison is random push against
  random push, at a matched per-position unit, on the same slots.
- **Dose convention.** Nominal alpha is not a convention-free dose. The ban-free unit is a smaller residual fraction
  at blocks 0-11, which is why S4 trails S0 at equal alpha but matches or beats it at equal realised ||d||/||h||.
  The dose-axis comparison is interpolated, not designed.
- **F1.** Early divergence is near-universal (the control is 0.82), so F1 constrains where label changes start, not
  why.
- **F2.**
  - The margin is length-sensitive. LP48 is a sum over at most 48 tokens, and T03's default program is about 12
    tokens long.
  - The same-seed rows that F2 explains ran in FP8 with top-k 10. Top-k only lowers p_alt, so the bound is
    conservative, but it is a cross-engine comparison.
  - At the fork token the margin is just under the bound.
- **S-d.**
  - Three settings have one survivor, or no movement at all.
  - The two computable edge tests disagree between blocks 18 and 23.
  - The centroid-difference push is dominated by the farthest survivor.
  - The manifold is built from forced prompts. MDS stress-1 is 0.06-0.17 (fair to good) at the chosen k.
- **Field norms this design answers** (mechanistic-interpretability handbook):
  - every arm has a matched random control;
  - effects are reported per sample and per dose, with paired flips, intervals and three to four doses per site;
  - collateral damage (pass and invalid rates) sits beside every share;
  - the claims were pre-registered with a power statement;
  - an independent re-derivation with placebos checks the headlines.

